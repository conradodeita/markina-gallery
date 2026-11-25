"""Install a verified backup runtime bundle inertly on the fixed production host."""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Callable, Iterator, Sequence
from functools import partial
from pathlib import Path, PurePosixPath

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows local development only
    fcntl = None

from platform_backup_runtime_artifact import ArtifactError, verify_bundle
from platform_backup_runtime_inventory import (
    InventoryError,
    collect_inventory,
    install_preconditions,
    read_systemd_unit_state,
    verify_installed_release,
)

INSTALL_ROOT = Path("/opt/pyp-backup-runtime")
SYSTEMD_ROOT = Path("/etc/systemd/system")
CONFIG_ROOT = Path("/etc/pyp-backup")
DEPLOY_STATE = Path("/var/lib/markina-gallery/deploy-state")
PRODUCTION_RELEASE_LOCK = DEPLOY_STATE / "production-release.lock"
RELEASES = INSTALL_ROOT / "releases"
CURRENT = INSTALL_ROOT / "current"
UNIT_NAMES = {
    "pyp-platform-backup.service": "scripts/backup_runtime/pyp-platform-backup.service",
    "pyp-platform-backup.timer": "scripts/backup_runtime/pyp-platform-backup.timer",
}
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_STDIN_BYTES = 768 * 1024 * 1024
MAX_FILESYSTEM_BLOCK_BYTES = 1024 * 1024
MAX_WHEEL_EXPANDED_BYTES = 8 * 1024 * 1024 * 1024
CAPACITY_TRANSACTION_RESERVE_BYTES = 256 * 1024


class InstallError(ValueError):
    """Sanitized error that must not include host configuration or secrets."""


Runner = Callable[..., subprocess.CompletedProcess[str]]


@contextlib.contextmanager
def _production_release_lock(
    lock_path: Path,
    *,
    root_only: bool,
    expected_owner: tuple[int, int] | None = None,
) -> Iterator[None]:
    if fcntl is None:
        _require(not root_only, "production_release_lock_unavailable")
        yield
        return
    _require(lock_path.parent.is_dir() and not lock_path.parent.is_symlink(),
             "production_release_lock_unavailable")
    try:
        parent_info = lock_path.parent.lstat()
        info = lock_path.lstat()
    except OSError:
        raise InstallError("production_release_lock_unavailable") from None
    if expected_owner is None:
        try:
            import grp
            import pwd
            expected_owner = (pwd.getpwnam("ubuntu").pw_uid, grp.getgrnam("ubuntu").gr_gid)
        except (KeyError, ImportError):
            raise InstallError("production_release_lock_owner_unavailable") from None
    _require((parent_info.st_uid, parent_info.st_gid) == expected_owner
             and stat.S_IMODE(parent_info.st_mode) == 0o700
             and stat.S_ISDIR(parent_info.st_mode) and not stat.S_ISLNK(parent_info.st_mode),
             "production_release_lock_parent_invalid")
    _require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
             and (info.st_uid, info.st_gid) == expected_owner
             and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1,
             "production_release_lock_metadata_invalid")
    try:
        descriptor = os.open(lock_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        raise InstallError("production_release_lock_unavailable") from None
    try:
        opened = os.fstat(descriptor)
        _require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1
                 and (opened.st_uid, opened.st_gid) == expected_owner
                 and stat.S_IMODE(opened.st_mode) == 0o600,
                 "production_release_lock_metadata_invalid")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise InstallError("production_release_lock_busy") from None
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InstallError(message)


def _round_allocation(size: int, block_size: int) -> int:
    _require(type(size) is int and size >= 0 and type(block_size) is int and block_size > 0,
             "install_capacity_bound_invalid")
    return ((size + block_size - 1) // block_size) * block_size


def _probe_path(path: Path) -> Path:
    candidate = path
    while not candidate.exists() or candidate.is_symlink():
        parent = candidate.parent
        _require(parent != candidate, "install_capacity_path_invalid")
        candidate = parent
    return candidate


def _filesystem_block_size(path: Path) -> int:
    probe = _probe_path(path)
    try:
        statvfs = getattr(os, "statvfs", None)
        block_size = statvfs(probe).f_frsize if callable(statvfs) else os.stat(probe).st_blksize
    except OSError:
        raise InstallError("install_capacity_measurement_failed") from None
    _require(type(block_size) is int and 0 < block_size <= MAX_FILESYSTEM_BLOCK_BYTES,
             "install_capacity_measurement_invalid")
    return block_size


def _wheel_install_size_bound(files: dict[str, bytes], block_size: int) -> int:
    expanded_allocation = 0
    metadata_reserve = 0
    entry_point_count = 0
    wheel_count = 0
    total_entry_count = 0
    total_expanded_bytes = 0
    try:
        for path, data in files.items():
            if not path.startswith("wheelhouse/"):
                continue
            wheel_count += 1
            with zipfile.ZipFile(io.BytesIO(data)) as wheel:
                entries = wheel.infolist()
                _require(0 < len(entries) <= 10_000, "install_capacity_bound_invalid")
                total_entry_count += len(entries)
                _require(total_entry_count <= 10_000, "install_capacity_bound_invalid")
                names: set[str] = set()
                for entry in entries:
                    name = entry.filename
                    relative = PurePosixPath(name)
                    mode = entry.external_attr >> 16
                    _require(
                        name not in names and name and not relative.is_absolute()
                        and ".." not in relative.parts and "\\" not in name
                        and not stat.S_ISLNK(mode) and type(entry.file_size) is int and entry.file_size >= 0,
                        "install_capacity_bound_invalid",
                    )
                    names.add(name)
                    metadata_reserve += len(name.encode("utf-8")) * 4 + 16 * block_size
                    if entry.is_dir():
                        metadata_reserve += block_size
                        continue
                    total_expanded_bytes += entry.file_size
                    _require(total_expanded_bytes <= MAX_WHEEL_EXPANDED_BYTES,
                             "install_capacity_bound_invalid")
                    expanded_allocation += _round_allocation(entry.file_size, block_size)
                    if name.endswith(".dist-info/entry_points.txt"):
                        _require(entry.file_size <= 1024 * 1024,
                                 "install_capacity_bound_invalid")
                        raw = wheel.read(entry)
                        active_group = False
                        for line in raw.decode("utf-8").splitlines():
                            stripped = line.strip()
                            if stripped.startswith("[") and stripped.endswith("]"):
                                active_group = stripped[1:-1] in {"console_scripts", "gui_scripts"}
                            elif active_group and stripped and not stripped.startswith("#"):
                                _require("=" in stripped, "install_capacity_bound_invalid")
                                entry_point_count += 1
                                _require(entry_point_count <= 10_000, "install_capacity_bound_invalid")
                    with wheel.open(entry, "r") as stream:
                        actual_size = 0
                        while True:
                            chunk = stream.read(1024 * 1024)
                            if not chunk:
                                break
                            actual_size += len(chunk)
                            _require(actual_size <= entry.file_size,
                                     "install_capacity_bound_invalid")
                        _require(actual_size == entry.file_size, "install_capacity_bound_invalid")
    except (OSError, UnicodeError, zipfile.BadZipFile, RuntimeError, ValueError):
        raise InstallError("install_capacity_bound_invalid") from None
    _require(wheel_count > 0, "install_capacity_bound_invalid")
    # Three allocated copies cover installed files, generated bytecode and
    # additional wheel metadata; script wrappers receive a separate bound.
    return (3 * expanded_allocation + metadata_reserve
            + entry_point_count * 64 * 1024)


def _installation_capacity_requirements(
    files: dict[str, bytes],
    *,
    python_executable: str,
    install_block_size: int,
    systemd_block_size: int,
) -> dict[str, int]:
    try:
        python_size = Path(python_executable).stat().st_size
    except OSError:
        raise InstallError("install_capacity_measurement_failed") from None
    _require(type(python_size) is int and python_size > 0,
             "install_capacity_measurement_invalid")
    staged_bytes = 0
    staged_nodes = 0
    systemd_bytes = 0
    for path, data in files.items():
        staged_bytes += _round_allocation(len(data), install_block_size)
        staged_nodes += 1
        if path != "manifest.json" and not path.startswith("wheelhouse/"):
            staged_nodes += path.count("/")
        if path in UNIT_NAMES.values():
            systemd_bytes += _round_allocation(len(data), systemd_block_size)
    _require(systemd_bytes > 0 and staged_nodes <= 100_000,
             "install_capacity_bound_invalid")
    install_tree_reserve = staged_bytes + staged_nodes * install_block_size
    venv_reserve = (4 * python_size + 2 * 1024 * 1024
                    + _wheel_install_size_bound(files, install_block_size))
    return {
        "disk_install_root": install_tree_reserve + venv_reserve + CAPACITY_TRANSACTION_RESERVE_BYTES,
        "disk_systemd_root": systemd_bytes + 64 * 1024,
    }


def _assert_install_capacity(inventory: dict[str, object], required: dict[str, int]) -> None:
    grouped: dict[str, dict[str, int]] = {}
    for name, needed in required.items():
        _require(name in {"disk_install_root", "disk_systemd_root"}
                 and type(needed) is int and needed >= 0, "install_capacity_bound_invalid")
        disk = inventory.get(name)
        _require(type(disk) is dict
                 and isinstance(disk.get("filesystem_binding"), str)
                 and bool(SHA256.fullmatch(disk["filesystem_binding"]))
                 and all(type(disk.get(key)) is int for key in
                         ("total_kib", "used_kib", "available_kib", "use_percent"))
                 and 0 <= disk["use_percent"] < 75,
                 "install_capacity_measurement_invalid")
        binding = disk["filesystem_binding"]
        measurement = {key: disk[key] for key in ("total_kib", "used_kib", "available_kib")}
        if binding in grouped:
            _require(all(grouped[binding][key] == measurement[key]
                         for key in ("total_kib", "used_kib", "available_kib")),
                     "install_capacity_measurement_invalid")
            grouped[binding]["required_bytes"] += needed
        else:
            grouped[binding] = {**measurement, "required_bytes": needed}
    for measurement in grouped.values():
        total = measurement["total_kib"] * 1024
        used = measurement["used_kib"] * 1024
        available = measurement["available_kib"] * 1024
        required_bytes = measurement["required_bytes"]
        _require(total > 0 and used >= 0 and available >= 0 and required_bytes >= 0,
                 "install_capacity_measurement_invalid")
        _require(available >= required_bytes, "install_capacity_insufficient")
        _require(4 * (used + required_bytes) < 3 * total,
                 "install_capacity_limit_exceeded")


def _assert_capacity_filesystems_unchanged(
    approved_inventory: dict[str, object], current_inventory: dict[str, object],
) -> None:
    for name in ("disk_var_lib", "disk_install_root", "disk_systemd_root"):
        approved = approved_inventory.get(name)
        current = current_inventory.get(name)
        _require(type(approved) is dict and type(current) is dict
                 and approved.get("filesystem_binding") == current.get("filesystem_binding")
                 and approved.get("total_kib") == current.get("total_kib"),
                 "install_capacity_filesystem_changed")


def _run(argv: Sequence[str], *, env: dict[str, str] | None = None,
         cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, check=False, text=True, timeout=900, env=env, cwd=cwd)


def _read_bundle_files(bundle: bytes) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz") as archive:
        for member in archive.getmembers():
            stream = archive.extractfile(member)
            if stream is None:
                raise InstallError("bundle_entry_unreadable")
            files[member.name] = stream.read(member.size + 1)
    return files


def _destination_is_disabled(config_root: Path) -> bool:
    path = config_root / "destination.json"
    try:
        info = path.lstat()
    except FileNotFoundError:
        return True
    if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or info.st_uid != 0 or info.st_gid != 0 or stat.S_IMODE(info.st_mode) != 0o400
            or info.st_nlink != 1 or not 0 < info.st_size <= 16_384):
        return False
    try:
        def unique(items: list[tuple[str, object]]) -> dict[str, object]:
            seen: set[str] = set()
            for key, _ in items:
                if key in seen:
                    raise ValueError
                seen.add(key)
            return dict(items)
        value = json.loads(path.read_bytes(), object_pairs_hook=unique)
        return isinstance(value, dict) and value.get("enabled") is False
    except (OSError, ValueError, UnicodeError, TypeError):
        return False


def _private_mkdir(path: Path, *, mode: int = 0o700, root_only: bool = True) -> None:
    if path.exists() or path.is_symlink():
        info = path.lstat()
        _require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode), "install_directory_unsafe")
        _require((not root_only or info.st_uid == 0 and info.st_gid == 0)
                 and stat.S_IMODE(info.st_mode) == mode,
                 "install_directory_permissions_invalid")
        return
    path.mkdir(mode=mode)
    info = path.lstat()
    _require(stat.S_ISDIR(info.st_mode) and (not root_only or info.st_uid == 0 and info.st_gid == 0)
             and stat.S_IMODE(info.st_mode) == mode, "install_directory_permissions_invalid")


def _write_file(path: Path, data: bytes, *, mode: int = 0o400, root_only: bool = True) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, mode)
    try:
        info = os.fstat(descriptor)
        _require(stat.S_ISREG(info.st_mode) and (not root_only or info.st_uid == 0 and info.st_gid == 0)
                 and info.st_nlink == 1, "install_file_metadata_invalid")
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = -1
            if stream.write(data) != len(data):
                raise InstallError("install_short_write")
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _write_tree(root: Path, files: dict[str, bytes], *, root_only: bool) -> None:
    for name, data in sorted(files.items()):
        if name == "manifest.json" or name.startswith("wheelhouse/"):
            continue
        relative = PurePosixPath(name)
        _require(not relative.is_absolute() and ".." not in relative.parts, "bundle_path_invalid")
        parent = root
        for component in relative.parts[:-1]:
            parent = parent / component
            if not parent.exists():
                parent.mkdir(mode=0o700)
            info = parent.lstat()
            _require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                     and (not root_only or info.st_uid == 0 and info.st_gid == 0), "install_path_unsafe")
            os.chmod(parent, 0o700)
        target = root.joinpath(*relative.parts)
        _write_file(target, data, root_only=root_only)


def _wheel_filename(files: dict[str, bytes], package: str) -> str:
    from platform_backup_runtime_artifact import _normalize_name, _wheel_identity

    matches = [name.removeprefix("wheelhouse/") for name in files if name.startswith("wheelhouse/")
               and _normalize_name(_wheel_identity(name.removeprefix("wheelhouse/"))[0]) == package]
    _require(len(matches) == 1, "wheelhouse_package_missing")
    return matches[0]


def _install_wheels(stage: Path, files: dict[str, bytes], runner: Runner,
                    python_executable: str) -> None:
    wheelhouse = stage / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)
    for name, data in sorted(files.items()):
        if name.startswith("wheelhouse/"):
            target = wheelhouse / name.removeprefix("wheelhouse/")
            _write_file(target, data)
    venv = stage / "venv"
    result = runner([python_executable, "-m", "venv", "--without-pip", "--copies", str(venv)])
    _require(result.returncode == 0, "venv_create_failed")
    pip_wheel = _wheel_filename(files, "pip")
    pip_path = wheelhouse / pip_wheel
    env = dict(os.environ)
    env["PYTHONPATH"] = str(pip_path)
    env["PYTHONNOUSERSITE"] = "1"
    target_python = str(venv / "bin" / "python")
    result = runner([
        python_executable, "-m", "pip", "--python", target_python, "install",
        "--no-index", "--find-links", str(wheelhouse), "--no-deps", "--require-hashes",
        "-r", str(stage / "scripts/backup_runtime/requirements-py310-arm64.lock"),
    ], env=env, cwd=stage)
    _require(result.returncode == 0, "offline_dependency_install_failed")
    result = runner([
        target_python, "-B", "-c", "import app.platform_backup.production_cli; print('runtime_import_ok')",
    ], env={"PYTHONPATH": str(stage / "backend")}, cwd=stage)
    _require(result.returncode == 0 and result.stdout.strip() == "runtime_import_ok",
             "runtime_import_failed")
    shutil.rmtree(wheelhouse)


def _current_release(install_root: Path) -> str | None:
    current = install_root / "current"
    try:
        info = current.lstat()
    except FileNotFoundError:
        return None
    _require(stat.S_ISLNK(info.st_mode) and info.st_uid == 0 and info.st_gid == 0 and info.st_nlink == 1,
             "current_release_not_symlink")
    target = os.readlink(current)
    _require(re.fullmatch(r"releases/[0-9a-f]{40}", target) is not None, "current_release_target_invalid")
    release = install_root / target
    info = release.lstat()
    _require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
             and info.st_uid == 0 and info.st_gid == 0 and stat.S_IMODE(info.st_mode) == 0o700,
             "current_release_directory_invalid")
    return target


def _existing_unit(path: Path, expected_previous: bytes | None) -> bytes | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    _require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
             and info.st_uid == 0 and info.st_gid == 0 and info.st_nlink == 1
             and stat.S_IMODE(info.st_mode) == 0o644 and info.st_size <= 16_384,
             "existing_unit_metadata_invalid")
    data = path.read_bytes()
    _require(expected_previous is not None and data == expected_previous, "existing_unit_unrecognized")
    return data


def _assert_existing_units_unchanged(systemd_root: Path, previous_units: dict[str, bytes | None]) -> None:
    for unit_name, expected in previous_units.items():
        _require(_existing_unit(systemd_root / unit_name, expected) == expected,
                 "systemd_unit_changed_during_install")


def _atomic_unit(path: Path, data: bytes, *, root_only: bool) -> None:
    temporary = path.with_name(path.name + ".pyp-install-tmp")
    _require(not temporary.exists() and not temporary.is_symlink(), "unit_temp_path_exists")
    created = False
    try:
        _write_file(temporary, data, mode=0o644, root_only=root_only)
        created = True
        os.replace(temporary, path)
    except BaseException:
        if created and temporary.exists() and not temporary.is_symlink():
            temporary.unlink()
        raise
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _restore_unit(path: Path, previous: bytes | None, *, expected_current: bytes,
                  root_only: bool) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        info = None
    _require(info is not None and stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
             and info.st_nlink == 1 and (not root_only or info.st_uid == 0 and info.st_gid == 0)
             and stat.S_IMODE(info.st_mode) == 0o644 and path.read_bytes() == expected_current,
             "unit_changed_during_rollback")
    if previous is None:
        path.unlink()
    else:
        temporary = path.with_name(path.name + ".pyp-rollback-tmp")
        _require(not temporary.exists() and not temporary.is_symlink(), "unit_rollback_temp_exists")
        _write_file(temporary, previous, mode=0o644, root_only=root_only)
        os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _assert_units_inert(runner: Runner, *, allow_missing: bool = False) -> None:
    for name in UNIT_NAMES:
        unit = Path(name).name
        try:
            state = read_systemd_unit_state(unit, runner)
        except InventoryError as exc:
            if str(exc) == "systemd_inventory_failed":
                raise InstallError("systemd_inert_state_unavailable") from None
            raise InstallError("systemd_inert_state_invalid") from None
        load, enabled, active = state["load"], state["enabled"], state["active"]
        loaded_inert = load == "loaded" and enabled in {"disabled", "static"} and active == "inactive"
        missing_inert = allow_missing and load == "not-found" and enabled == "unknown" and active == "inactive"
        _require(loaded_inert or missing_inert, "systemd_unit_not_inert")


def _write_receipt(path: Path, document: dict[str, object], *, root_only: bool) -> bytes:
    data = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    _write_file(path, data, mode=0o600, root_only=root_only)
    return data


def _privatize_tree(root: Path, *, root_only: bool) -> None:
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in directories:
            path = current_path / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) and path == root / "venv/lib64":
                target = path.with_name("lib")
                _require(os.readlink(path) == "lib" and info.st_nlink == 1
                         and (not root_only or (info.st_uid, info.st_gid) == (0, 0)),
                         "install_tree_unsafe")
                target_info = target.lstat()
                _require(stat.S_ISDIR(target_info.st_mode)
                         and (not root_only or (target_info.st_uid, target_info.st_gid) == (0, 0)),
                         "install_tree_unsafe")
                continue
            _require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                     and (not root_only or info.st_uid == 0 and info.st_gid == 0), "install_tree_unsafe")
            os.chmod(path, 0o700)
        for name in filenames:
            path = current_path / name
            info = path.lstat()
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                     and (not root_only or info.st_uid == 0 and info.st_gid == 0), "install_tree_unsafe")
            os.chmod(path, 0o700 if info.st_mode & 0o111 else 0o600)
    os.chmod(root, 0o700)


def _rebase_shebangs(root: Path, final_root: Path) -> None:
    old = os.fsencode(root)
    new = os.fsencode(final_root)
    bin_dir = root / "venv/bin"
    for path in bin_dir.iterdir():
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            if data.startswith(b"#!") and old in data.split(b"\n", 1)[0]:
                path.write_bytes(data.replace(old, new, 1))


def _install_verified_bundle_under_lock(
    bundle: bytes,
    *,
    source_sha: str,
    bundle_sha256: str,
    approval_fingerprint: str,
    inventory_provider: Callable[[], dict[str, object]] = collect_inventory,
    runner: Runner = _run,
    install_root: Path = INSTALL_ROOT,
    systemd_root: Path = SYSTEMD_ROOT,
    config_root: Path = CONFIG_ROOT,
    python_executable: str = "/usr/bin/python3.10",
    require_root: bool = True,
) -> dict[str, object]:
    if require_root:
        _require(os.name == "posix" and getattr(os, "geteuid", lambda: -1)() == 0, "root_required")
    _require(bool(GIT_SHA.fullmatch(source_sha)) and bool(SHA256.fullmatch(bundle_sha256))
             and bool(SHA256.fullmatch(approval_fingerprint)), "approval_input_invalid")
    if not callable(inventory_provider):
        raise InstallError("inventory_provider_invalid")
    current_inventory = inventory_provider()
    _require(current_inventory.get("approval_fingerprint") == approval_fingerprint,
             "inventory_fingerprint_mismatch")
    runtime_fingerprint = current_inventory.get("runtime_fingerprint")
    _require(isinstance(runtime_fingerprint, str) and bool(SHA256.fullmatch(runtime_fingerprint)),
             "runtime_fingerprint_invalid")
    inventory = current_inventory.get("inventory")
    _require(isinstance(inventory, dict) and install_preconditions(inventory), "install_preconditions_failed")
    manifest = verify_bundle(bundle, source_sha, bundle_sha256)
    _require(_destination_is_disabled(config_root), "destination_not_disabled")
    files = _read_bundle_files(bundle)
    _require(manifest["source_sha"] == source_sha, "source_sha_mismatch")

    install_block_size = _filesystem_block_size(install_root)
    systemd_block_size = _filesystem_block_size(systemd_root)
    full_capacity_requirement = _installation_capacity_requirements(
        files,
        python_executable=python_executable,
        install_block_size=install_block_size,
        systemd_block_size=systemd_block_size,
    )
    before_write_inventory = inventory_provider()
    _require(before_write_inventory.get("approval_fingerprint") == approval_fingerprint,
             "inventory_fingerprint_mismatch")
    _require(before_write_inventory.get("runtime_fingerprint") == runtime_fingerprint,
             "runtime_changed_during_install")
    before_write_state = before_write_inventory.get("inventory")
    _require(isinstance(before_write_state, dict) and install_preconditions(before_write_state),
             "install_preconditions_failed")
    _assert_capacity_filesystems_unchanged(inventory, before_write_state)
    _assert_install_capacity(before_write_state, full_capacity_requirement)

    parent = install_root.parent
    _require(parent.is_dir() and not parent.is_symlink(), "install_parent_invalid")
    parent_info = parent.lstat()
    _require(stat.S_ISDIR(parent_info.st_mode) and not stat.S_ISLNK(parent_info.st_mode)
             and (not require_root or parent_info.st_uid == 0 and parent_info.st_gid == 0)
             and not stat.S_IMODE(parent_info.st_mode) & 0o022, "install_parent_permissions_invalid")
    try:
        systemd_info = systemd_root.lstat()
    except OSError:
        raise InstallError("systemd_directory_unavailable") from None
    _require(stat.S_ISDIR(systemd_info.st_mode) and not stat.S_ISLNK(systemd_info.st_mode)
             and (not require_root or systemd_info.st_uid == 0 and systemd_info.st_gid == 0)
             and not stat.S_IMODE(systemd_info.st_mode) & 0o022, "systemd_directory_permissions_invalid")
    created_install_root = not install_root.exists() and not install_root.is_symlink()
    _private_mkdir(install_root, root_only=require_root)
    release_root = install_root / "releases"
    created_release_root = not release_root.exists() and not release_root.is_symlink()
    if created_release_root:
        release_root.mkdir(mode=0o700)
    _private_mkdir(release_root, root_only=require_root)
    release_path = release_root / source_sha
    _require(not release_path.exists() and not release_path.is_symlink(), "release_already_exists")
    previous_current = _current_release(install_root)
    rollback_root = install_root / "rollback"
    created_rollback_root = not rollback_root.exists() and not rollback_root.is_symlink()
    if created_rollback_root:
        rollback_root.mkdir(mode=0o700)
    _private_mkdir(rollback_root, root_only=require_root)
    transaction_path = install_root / "install-journal.json"
    _require(not transaction_path.exists() and not transaction_path.is_symlink(), "install_reconciliation_required")

    unit_data = {name: files[path] for name, path in UNIT_NAMES.items()}
    previous_units = {}
    prior_source = install_root / previous_current / UNIT_NAMES["pyp-platform-backup.service"] if previous_current else None
    prior_timer = install_root / previous_current / UNIT_NAMES["pyp-platform-backup.timer"] if previous_current else None
    for unit_name, expected_path in (("pyp-platform-backup.service", prior_source),
                                     ("pyp-platform-backup.timer", prior_timer)):
        expected_previous = expected_path.read_bytes() if expected_path is not None and expected_path.is_file() else None
        previous_units[unit_name] = _existing_unit(systemd_root / unit_name, expected_previous)

    staging = release_root / f".staging-{source_sha}-{os.getpid()}"
    _require(not staging.exists() and not staging.is_symlink(), "staging_path_exists")
    staging.mkdir(mode=0o700)
    release_created = False
    rollback_receipt_path = rollback_root / f"{source_sha}.json"
    rollback_receipt_created = False
    try:
        _write_tree(staging, files, root_only=require_root)
        _install_wheels(staging, files, runner, python_executable)
        if (staging / "wheelhouse").exists():
            raise InstallError("wheelhouse_cleanup_failed")
        pre_mutation_inventory = inventory_provider()
        _require(pre_mutation_inventory.get("runtime_fingerprint") == runtime_fingerprint,
                 "runtime_changed_during_install")
        pre_mutation_state = pre_mutation_inventory.get("inventory")
        _require(isinstance(pre_mutation_state, dict) and install_preconditions(pre_mutation_state),
                 "pre_mutation_preconditions_failed")
        _assert_capacity_filesystems_unchanged(inventory, pre_mutation_state)
        _assert_install_capacity(pre_mutation_state, {
            "disk_install_root": CAPACITY_TRANSACTION_RESERVE_BYTES,
            "disk_systemd_root": sum(len(value) for value in unit_data.values()) + 64 * 1024,
        })
        _require(_current_release(install_root) == previous_current,
                 "current_release_changed_during_install")
        _require(_destination_is_disabled(config_root), "destination_state_changed")
        _assert_units_inert(runner, allow_missing=True)
        _assert_existing_units_unchanged(systemd_root, previous_units)
        _rebase_shebangs(staging, release_path)
        _privatize_tree(staging, root_only=require_root)
        _write_file(staging / "manifest.json", files["manifest.json"], mode=0o400, root_only=require_root)
        os.rename(staging, release_path)
        release_created = True
        release_info = release_path.lstat()
        _require(stat.S_ISDIR(release_info.st_mode)
                 and (not require_root or release_info.st_uid == 0 and release_info.st_gid == 0)
                 and stat.S_IMODE(release_info.st_mode) == 0o700, "release_directory_permissions_invalid")

        rollback_document = {
            "schema_version": 1,
            "source_sha": source_sha,
            "bundle_sha256": bundle_sha256,
            "previous_current": previous_current,
            "previous_units": {
                name: (base64.b64encode(data).decode("ascii") if data is not None else None)
                for name, data in previous_units.items()
            },
        }
        rollback_bytes = _write_receipt(rollback_receipt_path, rollback_document, root_only=require_root)
        rollback_receipt_created = True
        journal_document = {"schema_version": 1, "source_sha": source_sha, "phase": "prepared"}
        _write_receipt(transaction_path, journal_document, root_only=require_root)

        changed_units: list[str] = []
        current_changed = False
        temporary_link = install_root / f".current-{source_sha}"
        try:
            if not _destination_is_disabled(config_root):
                raise InstallError("destination_state_changed")
            _assert_units_inert(runner, allow_missing=True)
            for unit_name, data in unit_data.items():
                _atomic_unit(systemd_root / unit_name, data, root_only=require_root)
                changed_units.append(unit_name)
            before_swap_inventory = inventory_provider()
            _require(before_swap_inventory.get("runtime_fingerprint") == runtime_fingerprint,
                     "runtime_changed_during_install")
            before_swap_state = before_swap_inventory.get("inventory")
            _require(isinstance(before_swap_state, dict) and install_preconditions(before_swap_state),
                     "pre_swap_preconditions_failed")
            _assert_capacity_filesystems_unchanged(inventory, before_swap_state)
            _assert_install_capacity(before_swap_state, {
                "disk_install_root": 128 * 1024,
                "disk_systemd_root": 64 * 1024,
            })
            _require(_current_release(install_root) == previous_current,
                     "current_release_changed_during_install")
            _require(_destination_is_disabled(config_root), "destination_state_changed")
            _assert_units_inert(runner, allow_missing=True)
            _require(not temporary_link.exists() and not temporary_link.is_symlink(), "current_temp_exists")
            os.symlink(f"releases/{source_sha}", temporary_link)
            os.replace(temporary_link, install_root / "current")
            current_changed = True
            result = runner(["/usr/bin/systemctl", "daemon-reload"])
            _require(result.returncode == 0, "systemd_reload_failed")
            _assert_units_inert(runner)
            _require(_destination_is_disabled(config_root), "destination_state_changed")
            verified_inventory = inventory_provider()
            _require(verified_inventory.get("runtime_fingerprint") == runtime_fingerprint,
                     "runtime_changed_during_install")
            verified_state = verified_inventory.get("inventory")
            _require(isinstance(verified_state, dict) and install_preconditions(verified_state),
                     "post_install_preconditions_failed")
            _assert_capacity_filesystems_unchanged(inventory, verified_state)
            receipt = {
                "schema_version": 1,
                "status": "installed_inert",
                "source_sha": source_sha,
                "bundle_sha256": bundle_sha256,
                "approval_fingerprint_version": 2,
                "approval_fingerprint": approval_fingerprint,
                "current_release": f"releases/{source_sha}",
                "previous_release": previous_current,
                "rollback_receipt_sha256": hashlib.sha256(rollback_bytes).hexdigest(),
                "service_enabled": False,
                "service_active": False,
                "timer_enabled": False,
                "timer_active": False,
                "destination_enabled": False,
            }
            _write_receipt(release_path / "install-receipt.json", receipt, root_only=require_root)
            if require_root:
                verify_installed_release(source_sha, bundle_sha256, install_root=install_root)
            transaction_path.unlink()
            directory_fd = os.open(install_root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            if temporary_link.exists() or temporary_link.is_symlink():
                temporary_link.unlink()
            if current_changed:
                current_path = install_root / "current"
                current_path.unlink()
                if previous_current:
                    os.symlink(previous_current, current_path)
            for unit_name in reversed(changed_units):
                _restore_unit(systemd_root / unit_name, previous_units[unit_name],
                              expected_current=unit_data[unit_name], root_only=require_root)
            runner(["/usr/bin/systemctl", "daemon-reload"])
            raise
        return receipt
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        if release_created and not transaction_path.exists() and not transaction_path.is_symlink():
            if rollback_receipt_created:
                rollback_receipt_path.unlink(missing_ok=True)
            shutil.rmtree(release_path)
        if not transaction_path.exists() and not transaction_path.is_symlink():
            if created_rollback_root:
                rollback_root.rmdir()
            if created_release_root:
                release_root.rmdir()
            if created_install_root:
                install_root.rmdir()
        raise


def install_verified_bundle(
    bundle: bytes,
    *,
    source_sha: str,
    bundle_sha256: str,
    approval_fingerprint: str,
    inventory_provider: Callable[[], dict[str, object]] = collect_inventory,
    runner: Runner = _run,
    install_root: Path = INSTALL_ROOT,
    systemd_root: Path = SYSTEMD_ROOT,
    config_root: Path = CONFIG_ROOT,
    python_executable: str = "/usr/bin/python3.10",
    require_root: bool = True,
    lock_path: Path = PRODUCTION_RELEASE_LOCK,
    lock_owner: tuple[int, int] | None = None,
) -> dict[str, object]:
    with _production_release_lock(lock_path, root_only=require_root, expected_owner=lock_owner):
        return _install_verified_bundle_under_lock(
            bundle, source_sha=source_sha, bundle_sha256=bundle_sha256,
            approval_fingerprint=approval_fingerprint, inventory_provider=inventory_provider,
            runner=runner, install_root=install_root, systemd_root=systemd_root,
            config_root=config_root, python_executable=python_executable, require_root=require_root,
        )


def _read_stdin(limit: int = MAX_STDIN_BYTES) -> bytes:
    chunks = bytearray()
    while True:
        block = sys.stdin.buffer.read(min(1024 * 1024, limit + 1 - len(chunks)))
        if not block:
            break
        chunks.extend(block)
        if len(chunks) > limit:
            raise InstallError("bundle_size_exceeded")
    return bytes(chunks)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--bundle-sha256", required=True)
    parser.add_argument("--approval-fingerprint", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = install_verified_bundle(
            _read_stdin(), source_sha=args.sha, bundle_sha256=args.bundle_sha256,
            approval_fingerprint=args.approval_fingerprint,
            inventory_provider=partial(collect_inventory, bridge_sha=args.sha),
        )
        print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
        return 0
    except (InstallError, ArtifactError, InventoryError, OSError, subprocess.SubprocessError):
        print(json.dumps({"status": "failed", "error": "install_rejected"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
