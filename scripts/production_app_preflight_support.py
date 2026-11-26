#!/usr/bin/env python3
"""Fixed, protected operations for app preflight support.

This program is invoked only by the protected workflow through the existing
production SSH channel. It intentionally has no user-selectable paths,
commands, repositories, services, or refs.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import posixpath
import re
import shutil
import socket
import stat
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

try:  # Linux-only host operations; the transaction coordinator is portable for local tests.
    import fcntl
    import grp
    import pwd
except ImportError:  # pragma: no cover - exercised by Windows development worktrees.
    fcntl = None  # type: ignore[assignment]
    grp = None  # type: ignore[assignment]
    pwd = None  # type: ignore[assignment]


REPOSITORY = "conradodeita/markina-gallery"
PROJECT_ROOT = Path("/opt/markina-gallery")
EXPECTED_HOST = "clearbudget-vnic"
MAIN_REF = "refs/remotes/origin/main"
BRIDGE_PATH = Path("/usr/local/sbin/markina-gallery-app-compose-bridge")
WRAPPER_PATH = Path("/usr/local/sbin/markina-gallery-preflight-ssh-wrapper")
BACKUPS_DIR = Path("/var/backups/markina-gallery")
STATE_DIR = Path("/var/lib/markina-gallery/app-compose-bridge")
LOCK_DIR = Path("/var/lib/markina-gallery/deploy-state")
LOCK_PATH = LOCK_DIR / "production-release.lock"
BACKUP_RUNTIME_DIR = Path("/opt/pyp-backup-runtime")
BACKUP_CONFIG_DIR = Path("/etc/pyp-backup")
BACKUP_STATE_DIR = Path("/var/lib/pyp-backup")
BACKUP_SYSTEMD_DIR = Path("/etc/systemd/system")
BACKUP_UNITS = ("pyp-platform-backup.service", "pyp-platform-backup.timer")
BACKUP_RETIREMENT_UNEXPECTED_ROOT_CODES = {
    "runtime": "backup_retirement_unexpected_runtime_layout",
    "config": "backup_retirement_unexpected_config_layout",
    "state": "backup_retirement_unexpected_state_layout",
}
MOUNTINFO_PATH = Path("/proc/self/mountinfo")
PICKER_CONFIG_PATH = Path("/etc/pyp-google-drive/picker-config.json")
PUBLIC_HEALTH_URLS = {
    "root": "https://markina.pickyourpic.com.br/",
    "healthz": "https://markina.pickyourpic.com.br/healthz",
    "api": "https://markina.pickyourpic.com.br/api/health",
}
TARGETS = ("bridge", "wrapper")
SAFE_DIRECTORY_STATES = {"ready", "creatable"}
SUPPORT_DIRECTORY_DIAGNOSTICS = {
    "ready", "creatable", "parent_invalid", "unavailable", "target_symlink",
    "target_type_invalid", "target_owner_invalid", "target_group_invalid", "target_mode_invalid",
}
TARGET_DIRECTORY_DIAGNOSTIC_ORDER = (
    "target_type_invalid", "target_owner_invalid", "target_group_invalid", "target_mode_invalid",
)
TARGET_PATHS = {"bridge": BRIDGE_PATH, "wrapper": WRAPPER_PATH}
TARGET_SOURCES = {
    "bridge": "scripts/production_app_compose_bridge.py",
    "wrapper": "scripts/production-preflight-ssh-wrapper.sh",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OBJECT_ID = re.compile(r"^[0-9a-f]{64}$")
VALID_MODES = {
    "support-inventory", "prepare-support", "repair-support-backups-mode",
    "restore-support-inventory", "restore-support",
    "backup-retirement-inventory", "retire-backup-runtime",
}
INTERNAL_ERROR_CODES: tuple[tuple[type[BaseException], str], ...] = (
    (UnicodeError, "support_internal_encoding_error"),
    (subprocess.SubprocessError, "support_internal_command_error"),
    (OSError, "support_internal_io_error"),
    (AssertionError, "support_internal_assertion_error"),
    (AttributeError, "support_internal_attribute_error"),
    (ImportError, "support_internal_import_error"),
    (LookupError, "support_internal_lookup_error"),
    (NameError, "support_internal_name_error"),
    (ArithmeticError, "support_internal_arithmetic_error"),
    (RuntimeError, "support_internal_runtime_error"),
    (TypeError, "support_internal_type_error"),
    (ValueError, "support_internal_value_error"),
)
ZERO_SHA = "0" * 40


class SupportError(Exception):
    """A fixed, non-sensitive operation error."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _internal_error_code(error: BaseException) -> str:
    for error_type, code in INTERNAL_ERROR_CODES:
        if isinstance(error, error_type):
            return code
    return "support_internal_error"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _file_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe_sha(value: str, pattern: re.Pattern[str], code: str) -> str:
    if not pattern.fullmatch(value):
        raise SupportError(code)
    return value


def _safe_retirement_mount_path(value: str) -> bool:
    return (
        len(value) <= 512
        and re.fullmatch(r"/[A-Za-z0-9._/-]{1,511}", value) is not None
        and "//" not in value
        and all(part not in {".", ".."} for part in value.split("/"))
    )


def _mountinfo_mountpoints_under(root: str | Path, contents: str) -> list[str]:
    """Return mountpoints at or below a fixed tree, including same-device binds."""
    target = posixpath.normpath(os.fspath(root))
    if not target.startswith("/"):
        raise ValueError("mountinfo_target_invalid")
    lines = contents.splitlines()
    if not lines:
        raise ValueError("mountinfo_empty")
    if any(not line for line in lines):
        raise ValueError("mountinfo_record_invalid")
    nested: set[str] = set()
    for line in lines:
        left, separator, right = line.partition(" - ")
        fields = left.split()
        post_fields = right.split()
        if (not separator or len(fields) < 6 or len(post_fields) < 3
                or not fields[0].isdigit() or not fields[1].isdigit()
                or re.fullmatch(r"[0-9]+:[0-9]+", fields[2]) is None):
            raise ValueError("mountinfo_record_invalid")
        encoded_mountpoint = fields[4]
        if re.search(r"\\(?!040|011|012|134)", encoded_mountpoint):
            raise ValueError("mountinfo_escape_invalid")
        decoded_escapes = {"040": " ", "011": chr(9), "012": chr(10), "134": chr(92)}
        mountpoint = re.sub(
            r"\\(040|011|012|134)",
            lambda match, escapes=decoded_escapes: escapes[match.group(1)],
            encoded_mountpoint,
        )
        if not mountpoint.startswith("/") or "\x00" in mountpoint:
            raise ValueError("mountinfo_path_invalid")
        mountpoint = posixpath.normpath(mountpoint)
        try:
            common = posixpath.commonpath((target, mountpoint))
        except ValueError:
            continue
        if common == target:
            relative = posixpath.relpath(mountpoint, target)
            nested.add("." if relative == "." else relative)
    return sorted(nested)


def _static_error(result: subprocess.CompletedProcess[bytes], code: str) -> subprocess.CompletedProcess[bytes]:
    if result.returncode != 0:
        raise SupportError(code)
    return result


class LocalSupportHost:
    """Root-side fixed-path adapter. Tests exercise the coordinator separately."""

    def __init__(self) -> None:
        self._lock_file = None

    @contextlib.contextmanager
    def lock(self) -> Iterator[None]:
        self._assert_root()
        if fcntl is None:
            raise SupportError("support_platform_unsupported")
        self._assert_directory(LOCK_DIR, owner="ubuntu", group="ubuntu", mode=0o700)
        self._assert_file(LOCK_PATH, owner="ubuntu", group="ubuntu", mode=0o600, links=1)
        for marker in ("app-in-flight.sha", "web-in-flight.sha", "app-rollback-in-flight.sha", "web-pending.identity"):
            if (LOCK_DIR / marker).exists() or (LOCK_DIR / marker).is_symlink():
                raise SupportError("support_release_in_flight")
        try:
            with LOCK_PATH.open("rb") as handle:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise SupportError("support_release_lock_busy") from None
                self._lock_file = handle
                yield
        except SupportError:
            raise
        except OSError:
            raise SupportError("support_release_lock_unavailable") from None
        finally:
            self._lock_file = None

    @staticmethod
    def _assert_root() -> None:
        if os.geteuid() != 0:
            raise SupportError("support_privilege_invalid")

    @staticmethod
    def _assert_directory(path: Path, *, owner: str, group: str, mode: int) -> None:
        if pwd is None or grp is None:
            raise SupportError("support_platform_unsupported")
        try:
            info = path.lstat()
            actual_owner = pwd.getpwuid(info.st_uid).pw_name
            actual_group = grp.getgrgid(info.st_gid).gr_name
        except (OSError, KeyError):
            raise SupportError("support_state_directory_invalid") from None
        if not stat.S_ISDIR(info.st_mode) or actual_owner != owner or actual_group != group or stat.S_IMODE(info.st_mode) != mode:
            raise SupportError("support_state_directory_invalid")

    @staticmethod
    def _assert_file(path: Path, *, owner: str, group: str, mode: int, links: int) -> os.stat_result:
        if pwd is None or grp is None:
            raise SupportError("support_platform_unsupported")
        try:
            info = path.lstat()
            actual_owner = pwd.getpwuid(info.st_uid).pw_name
            actual_group = grp.getgrgid(info.st_gid).gr_name
        except (OSError, KeyError):
            raise SupportError("support_state_file_invalid") from None
        if (not stat.S_ISREG(info.st_mode) or actual_owner != owner or actual_group != group
                or stat.S_IMODE(info.st_mode) != mode or info.st_nlink != links):
            raise SupportError("support_state_file_invalid")
        return info

    @staticmethod
    def _run(args: list[str], *, input_data: bytes | None = None, cwd: Path | None = None,
             timeout: int = 60, code: str = "support_command_failed") -> subprocess.CompletedProcess[bytes]:
        try:
            result = subprocess.run(
                args, cwd=str(cwd or PROJECT_ROOT), input=input_data,
                capture_output=True, timeout=timeout,
                check=False, env={**os.environ, "LC_ALL": "C", "LANG": "C"},
            )
        except (OSError, subprocess.TimeoutExpired):
            raise SupportError(code) from None
        return _static_error(result, code)

    def _git(self, args: list[str], *, input_data: bytes | None = None,
             allow_failure: bool = False) -> tuple[int, bytes]:
        try:
            result = subprocess.run(
                ["git", *args], cwd=str(PROJECT_ROOT), input=input_data,
                capture_output=True, timeout=60,
                check=False, env={**os.environ, "LC_ALL": "C", "LANG": "C"},
            )
        except (OSError, subprocess.TimeoutExpired):
            raise SupportError("support_git_unavailable") from None
        if result.returncode != 0 and not allow_failure:
            raise SupportError("support_git_state_invalid")
        return result.returncode, result.stdout

    def _assert_host_repository(self) -> str:
        self._assert_root()
        try:
            host = socket.gethostname().split(".", 1)[0]
            root = Path.cwd().resolve(strict=True)
        except OSError:
            raise SupportError("support_identity_unavailable") from None
        if host != EXPECTED_HOST or root != PROJECT_ROOT:
            raise SupportError("support_identity_mismatch")
        _, remote_bytes = self._git(["remote", "get-url", "origin"])
        try:
            remote = remote_bytes.decode("ascii").strip()
        except UnicodeDecodeError:
            raise SupportError("support_remote_invalid") from None
        allowed = {
            f"https://github.com/{REPOSITORY}.git",
            f"ssh://github.com/{REPOSITORY}.git",
            f"git@github.com:{REPOSITORY}.git",
        }
        if remote not in allowed:
            raise SupportError("support_remote_invalid")
        return remote

    def _remote_main_sha(self) -> str:
        _, value = self._git(["ls-remote", "origin", "refs/heads/main"])
        try:
            lines = value.decode("ascii").splitlines()
        except UnicodeDecodeError:
            raise SupportError("support_remote_main_invalid") from None
        if len(lines) != 1:
            raise SupportError("support_remote_main_invalid")
        parts = lines[0].split("\t")
        if len(parts) != 2 or parts[1] != "refs/heads/main" or not HEX40.fullmatch(parts[0]):
            raise SupportError("support_remote_main_invalid")
        return parts[0]

    def _ref_sha(self) -> str | None:
        status, value = self._git(["show-ref", "--verify", "--hash", MAIN_REF], allow_failure=True)
        if status == 1 and not value.strip():
            return None
        if status != 0:
            raise SupportError("support_local_ref_invalid")
        try:
            sha = value.decode("ascii").strip()
        except UnicodeDecodeError:
            raise SupportError("support_local_ref_invalid") from None
        if not HEX40.fullmatch(sha):
            raise SupportError("support_local_ref_invalid")
        return sha

    @staticmethod
    def _assert_parent_directory(path: Path) -> None:
        current = path.parent
        while current != current.parent:
            try:
                info = current.lstat()
            except OSError:
                raise SupportError("support_target_directory_invalid") from None
            if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_gid != 0:
                raise SupportError("support_target_directory_invalid")
            current = current.parent

    def target_state(self, name: str) -> dict[str, Any]:
        path = TARGET_PATHS[name]
        self._assert_parent_directory(path)
        try:
            before = path.lstat()
        except FileNotFoundError:
            return {"present": False}
        except OSError:
            raise SupportError("support_target_unreadable") from None
        try:
            owner = pwd.getpwuid(before.st_uid).pw_name
            group = grp.getgrgid(before.st_gid).gr_name
        except KeyError:
            raise SupportError("support_target_metadata_invalid") from None
        if (not stat.S_ISREG(before.st_mode) or owner != "root" or group != "root"
                or stat.S_IMODE(before.st_mode) != 0o755 or before.st_nlink != 1):
            raise SupportError("support_target_metadata_invalid")
        try:
            content = path.read_bytes()
            after = path.lstat()
        except OSError:
            raise SupportError("support_target_unreadable") from None
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise SupportError("support_target_changed_during_read")
        return {
            "present": True,
            "sha256": _file_digest(content),
            "uid": before.st_uid,
            "gid": before.st_gid,
            "mode": stat.S_IMODE(before.st_mode),
            "links": before.st_nlink,
        }

    def _container_digest(self) -> str:
        ids_result = self._run(["docker", "ps", "-aq", "--no-trunc"], code="support_container_inventory_failed")
        ids_bytes = ids_result.stdout
        try:
            ids = ids_bytes.decode("ascii").splitlines()
        except UnicodeDecodeError:
            raise SupportError("support_container_inventory_invalid") from None
        if any(not OBJECT_ID.fullmatch(item) for item in ids) or len(ids) != len(set(ids)):
            raise SupportError("support_container_inventory_invalid")
        rows: list[dict[str, str]] = []
        if ids:
            inspect_result = self._run(["docker", "inspect", *sorted(ids)], code="support_container_inventory_failed")
            inspected = inspect_result.stdout
            try:
                records = json.loads(inspected)
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise SupportError("support_container_inventory_invalid") from None
            if not isinstance(records, list) or len(records) != len(ids):
                raise SupportError("support_container_inventory_invalid")
            for item in records:
                try:
                    container_id = item["Id"]
                    image_id = item["Image"]
                    state = item["State"]["Status"]
                    started = item["State"]["StartedAt"]
                except (KeyError, TypeError):
                    raise SupportError("support_container_inventory_invalid") from None
                if (not isinstance(container_id, str) or not isinstance(image_id, str)
                        or not isinstance(state, str) or not isinstance(started, str)
                        or container_id not in ids or not OBJECT_ID.fullmatch(container_id)
                        or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id)
                        or state not in {"created", "running", "paused", "restarting", "removing", "exited", "dead"}
                        or not started or len(started) > 64):
                    raise SupportError("support_container_inventory_invalid")
                rows.append({"id": container_id, "image": image_id, "state": state, "started": started})
        if {row["id"] for row in rows} != set(ids):
            raise SupportError("support_container_inventory_invalid")
        rows.sort(key=lambda row: row["id"])
        return _file_digest(_canonical_json(rows))

    @staticmethod
    def _retirement_entry_metadata(path: Path, info: os.stat_result, *, kind: str,
                                   symlink_target: str | None = None) -> dict[str, Any]:
        if info.st_uid != 0 or info.st_gid != 0:
            raise SupportError("backup_retirement_target_owner_invalid")
        if kind == "directory":
            if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700:
                raise SupportError("backup_retirement_target_mode_or_type_invalid")
        elif kind == "file":
            if (not stat.S_ISREG(info.st_mode)
                    or stat.S_IMODE(info.st_mode) not in {0o400, 0o600, 0o644, 0o700}
                    or info.st_nlink != 1):
                raise SupportError("backup_retirement_target_mode_or_type_invalid")
        elif kind == "symlink":
            if not stat.S_ISLNK(info.st_mode) or info.st_nlink != 1 or symlink_target is None:
                raise SupportError("backup_retirement_target_mode_or_type_invalid")
        else:
            raise SupportError("backup_retirement_target_mode_or_type_invalid")
        return {
            "kind": kind,
            "uid": info.st_uid,
            "gid": info.st_gid,
            "mode": stat.S_IMODE(info.st_mode),
            "links": info.st_nlink,
            "size": info.st_size,
            "mtime_ns": info.st_mtime_ns,
            "device": info.st_dev,
            "inode": info.st_ino,
            **({"target": symlink_target} if symlink_target is not None else {}),
        }

    def _retirement_mountpoints(self, root: Path) -> list[str]:
        try:
            contents = MOUNTINFO_PATH.read_text(encoding="utf-8", errors="surrogateescape")
        except (OSError, UnicodeError):
            raise SupportError("backup_retirement_mount_inventory_unavailable") from None
        try:
            return _mountinfo_mountpoints_under(root, contents)
        except (TypeError, ValueError):
            raise SupportError("backup_retirement_mount_inventory_invalid") from None

    def _assert_no_nested_mounts(self, root: Path) -> None:
        if self._retirement_mountpoints(root) or os.path.ismount(root):
            raise SupportError("backup_retirement_nested_mount")

    def _retirement_tree_state(self, root: Path, *, allow_symlinks: bool = False,
                               allowed_root_names: set[str] | None = None,
                               unexpected_root_category: str | None = None) -> dict[str, Any]:
        self._assert_parent_directory(root)
        try:
            root_info = root.lstat()
        except FileNotFoundError:
            return {"present": False, "entries": [], "nested_mounts": []}
        except OSError:
            raise SupportError("backup_retirement_target_unreadable") from None
        self._assert_no_nested_mounts(root)
        root_state = self._retirement_entry_metadata(root, root_info, kind="directory")
        entries: list[dict[str, Any]] = []
        pending = [(root, "")]
        root_names: set[str] = set()
        while pending:
            directory, prefix = pending.pop()
            try:
                children = sorted(os.scandir(directory), key=lambda entry: entry.name)
            except OSError:
                raise SupportError("backup_retirement_target_unreadable") from None
            for child in children:
                relative = f"{prefix}/{child.name}" if prefix else child.name
                if not prefix:
                    root_names.add(child.name)
                path = Path(child.path)
                try:
                    info = path.lstat()
                except OSError:
                    raise SupportError("backup_retirement_target_changed") from None
                if stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode):
                    if os.path.ismount(path):
                        raise SupportError("backup_retirement_nested_mount")
                    state = self._retirement_entry_metadata(path, info, kind="directory")
                    entries.append({"path": relative, **state})
                    pending.append((path, relative))
                elif stat.S_ISREG(info.st_mode):
                    if stat.S_IMODE(info.st_mode) not in {0o400, 0o600, 0o700}:
                        raise SupportError("backup_retirement_target_mode_or_type_invalid")
                    state = self._retirement_entry_metadata(path, info, kind="file")
                    entries.append({"path": relative, **state})
                elif stat.S_ISLNK(info.st_mode) and allow_symlinks:
                    try:
                        target = os.readlink(path)
                    except OSError:
                        raise SupportError("backup_retirement_target_changed") from None
                    state = self._retirement_entry_metadata(path, info, kind="symlink", symlink_target=target)
                    if relative == "current":
                        if re.fullmatch(r"releases/[0-9a-f]{40}", target) is None:
                            raise SupportError("backup_retirement_current_link_invalid")
                        releases = root / "releases"
                        try:
                            releases_info = releases.lstat()
                        except OSError:
                            raise SupportError("backup_retirement_current_link_invalid") from None
                        self._retirement_entry_metadata(releases, releases_info, kind="directory")
                        release = root / target
                        try:
                            release_info = release.lstat()
                        except OSError:
                            raise SupportError("backup_retirement_current_link_invalid") from None
                        self._retirement_entry_metadata(release, release_info, kind="directory")
                    elif re.fullmatch(r"releases/[0-9a-f]{40}/venv/lib64", relative):
                        if target != "lib":
                            raise SupportError("backup_retirement_target_mode_or_type_invalid")
                        library = path.with_name("lib")
                        try:
                            library_info = library.lstat()
                        except OSError:
                            raise SupportError("backup_retirement_target_changed") from None
                        self._retirement_entry_metadata(library, library_info, kind="directory")
                    else:
                        raise SupportError("backup_retirement_target_mode_or_type_invalid")
                    entries.append({"path": relative, **state})
                else:
                    raise SupportError("backup_retirement_target_mode_or_type_invalid")
                try:
                    after = path.lstat()
                except OSError:
                    raise SupportError("backup_retirement_target_changed") from None
                if ((info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
                     info.st_size, info.st_mtime_ns, info.st_nlink)
                        != (after.st_dev, after.st_ino, after.st_mode, after.st_uid, after.st_gid,
                            after.st_size, after.st_mtime_ns, after.st_nlink)):
                    raise SupportError("backup_retirement_target_changed")
        if allowed_root_names is not None and not root_names.issubset(allowed_root_names):
            error_code = BACKUP_RETIREMENT_UNEXPECTED_ROOT_CODES.get(unexpected_root_category or "")
            if error_code is None:
                raise SupportError("backup_retirement_inventory_invalid")
            raise SupportError(error_code)
        entries.sort(key=lambda item: item["path"])
        try:
            root_after = root.lstat()
        except OSError:
            raise SupportError("backup_retirement_target_changed") from None
        if ((root_info.st_dev, root_info.st_ino, root_info.st_mode, root_info.st_uid, root_info.st_gid,
             root_info.st_size, root_info.st_mtime_ns)
                != (root_after.st_dev, root_after.st_ino, root_after.st_mode, root_after.st_uid, root_after.st_gid,
                    root_after.st_size, root_after.st_mtime_ns)):
            raise SupportError("backup_retirement_target_changed")
        self._assert_no_nested_mounts(root)
        return {"present": True, "root": root_state, "entries": entries, "nested_mounts": []}

    def _retirement_file_state(self, path: Path, *, expected_mode: int) -> dict[str, Any]:
        self._assert_parent_directory(path)
        try:
            before = path.lstat()
        except FileNotFoundError:
            return {"present": False}
        except OSError:
            raise SupportError("backup_retirement_target_unreadable") from None
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_gid != 0
                or stat.S_IMODE(before.st_mode) != expected_mode or before.st_nlink != 1):
            raise SupportError("backup_retirement_target_mode_or_type_invalid")
        return {"present": True, **self._retirement_entry_metadata(path, before, kind="file")}

    @staticmethod
    def _backup_state_summary(state: dict[str, Any]) -> dict[str, int]:
        if state.get("present") is False:
            return {
                "encrypted_artifacts": 0, "partial_artifacts": 0,
                "catalog_files": 0, "files": 0, "bytes": 0,
            }
        entries = state.get("entries")
        if state.get("present") is not True or not isinstance(entries, list):
            raise SupportError("backup_retirement_state_inventory_invalid")
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        catalog_pattern = re.compile(
            rf"(?:day-[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}\.json(?:\.lock)?|{uuid_pattern}\.events(?:\.lock)?)"
        )
        artifact_pattern = re.compile(rf"{uuid_pattern}\.(?:pypb|building)")
        encrypted = partial = catalog = files = total_bytes = 0
        for entry in entries:
            if not isinstance(entry, dict):
                raise SupportError("backup_retirement_state_inventory_invalid")
            path = entry.get("path")
            kind = entry.get("kind")
            if path in {"catalog", "artifacts"} and kind == "directory":
                continue
            if not isinstance(path, str) or kind != "file":
                raise SupportError("backup_retirement_state_entry_unexpected")
            size = entry.get("size")
            if type(size) is not int or size < 0 or entry.get("mode") != 0o600:
                raise SupportError("backup_retirement_state_entry_unexpected")
            if path == "service.lock":
                pass
            elif path.startswith("catalog/") and catalog_pattern.fullmatch(path.removeprefix("catalog/")):
                catalog += 1
            elif path.startswith("artifacts/"):
                name = path.removeprefix("artifacts/")
                if not artifact_pattern.fullmatch(name):
                    raise SupportError("backup_retirement_state_entry_unexpected")
                if name.endswith(".pypb"):
                    encrypted += 1
                else:
                    partial += 1
            else:
                raise SupportError("backup_retirement_state_entry_unexpected")
            files += 1
            total_bytes += size
        return {
            "encrypted_artifacts": encrypted,
            "partial_artifacts": partial,
            "catalog_files": catalog,
            "files": files,
            "bytes": total_bytes,
        }

    def _retirement_unit_state(self, name: str) -> dict[str, str]:
        path = BACKUP_SYSTEMD_DIR / name
        file_state = self._retirement_file_state(path, expected_mode=0o644)
        try:
            result = subprocess.run(
                ["/usr/bin/systemctl", "show", "--no-pager", "--property=LoadState",
                 "--property=ActiveState", "--property=UnitFileState", "--property=FragmentPath",
                 "--property=DropInPaths", name],
                capture_output=True, timeout=15, check=False,
                env={**os.environ, "LC_ALL": "C", "LANG": "C"},
            )
        except (OSError, subprocess.TimeoutExpired):
            raise SupportError("backup_retirement_unit_state_unavailable") from None
        if result.returncode != 0:
            raise SupportError("backup_retirement_unit_state_unavailable")
        try:
            values = dict(line.split("=", 1) for line in result.stdout.decode("ascii").splitlines() if "=" in line)
        except UnicodeDecodeError:
            raise SupportError("backup_retirement_unit_state_invalid") from None
        load_state = values.get("LoadState", "")
        active_state = values.get("ActiveState", "")
        unit_file_state = values.get("UnitFileState", "")
        fragment_path = values.get("FragmentPath", "")
        drop_in_paths = values.get("DropInPaths", "")
        if (load_state not in {"loaded", "not-found"}
                or active_state not in {"inactive", "failed"}
                or unit_file_state not in {"", "disabled", "static", "indirect", "not-found"}
                or (fragment_path and fragment_path != str(BACKUP_SYSTEMD_DIR / name))
                or drop_in_paths):
            raise SupportError("backup_retirement_unit_state_invalid")
        return {"file": "present" if file_state["present"] else "absent",
                "load": load_state, "active": active_state, "enabled": unit_file_state,
                "fragment": fragment_path}

    def _retirement_container_state(self) -> tuple[str, str, list[dict[str, str]]]:
        result = self._run(["docker", "ps", "-aq", "--no-trunc"], code="backup_retirement_container_inventory_failed")
        try:
            ids = result.stdout.decode("ascii").splitlines()
        except UnicodeDecodeError:
            raise SupportError("backup_retirement_container_inventory_invalid") from None
        if any(not OBJECT_ID.fullmatch(item) for item in ids) or len(ids) != len(set(ids)):
            raise SupportError("backup_retirement_container_inventory_invalid")
        if not ids:
            return _file_digest(_canonical_json([])), "absent", []
        inspected = self._run(["docker", "inspect", *sorted(ids)], code="backup_retirement_container_inventory_failed")
        try:
            records = json.loads(inspected.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SupportError("backup_retirement_container_inventory_invalid") from None
        if not isinstance(records, list) or len(records) != len(ids):
            raise SupportError("backup_retirement_container_inventory_invalid")
        config_source = str(PICKER_CONFIG_PATH)
        config_parent = str(PICKER_CONFIG_PATH.parent)
        config_target = "/run/secrets/google-drive-picker-config.json"
        rows: list[dict[str, str]] = []
        picker_mounts: list[dict[str, str]] = []
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("Mounts"), list):
                raise SupportError("backup_retirement_container_inventory_invalid")
            try:
                container_id = record["Id"]
                image_id = record["Image"]
                state = record["State"]["Status"]
                started = record["State"]["StartedAt"]
            except (KeyError, TypeError):
                raise SupportError("backup_retirement_container_inventory_invalid") from None
            if (not isinstance(container_id, str) or not isinstance(image_id, str)
                    or not isinstance(state, str) or not isinstance(started, str)
                    or container_id not in ids or not OBJECT_ID.fullmatch(container_id)
                    or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id)
                    or state not in {"created", "running", "paused", "restarting", "removing", "exited", "dead"}
                    or not started or len(started) > 64):
                raise SupportError("backup_retirement_container_inventory_invalid")
            rows.append({"id": container_id, "image": image_id, "state": state, "started": started})
            mount_rows: list[dict[str, Any]] = []
            for mount in record["Mounts"]:
                if not isinstance(mount, dict):
                    raise SupportError("backup_retirement_container_inventory_invalid")
                source = mount.get("Source")
                target = mount.get("Destination")
                mount_type = mount.get("Type")
                read_write = mount.get("RW")
                if (not isinstance(source, str) or len(source) > 4096
                        or not isinstance(target, str) or not target or len(target) > 4096
                        or not isinstance(mount_type, str)
                        or mount_type not in {"bind", "volume", "tmpfs"}
                        or type(read_write) is not bool):
                    raise SupportError("backup_retirement_container_inventory_invalid")
                mount_rows.append({
                    "type": mount_type, "source": source, "target": target, "rw": read_write,
                })
                if (source in {config_source, config_parent}
                        or source.startswith(config_parent + os.sep)
                        or target == config_target
                        or target.startswith("/run/secrets/google-drive-picker-config/")):
                    if (not _safe_retirement_mount_path(source)
                            or not _safe_retirement_mount_path(target)):
                        raise SupportError("backup_retirement_container_inventory_invalid")
                    config = record.get("Config")
                    labels = config.get("Labels") if isinstance(config, dict) else None
                    labels = labels if isinstance(labels, dict) else {}
                    service = labels.get("com.docker.compose.service")
                    config_files = labels.get("com.docker.compose.project.config_files")
                    if (not isinstance(service, str)
                            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", service)):
                        service = "unknown"
                    if (not isinstance(config_files, str)
                            or not re.fullmatch(r"[A-Za-z0-9_./,-]{1,1024}", config_files)):
                        config_files = "unknown"
                    picker_mounts.append({
                        "container": container_id[:12],
                        "source": source,
                        "target": target,
                        "service": service,
                        "compose_files": config_files,
                    })
            rows[-1]["mounts"] = _canonical_json(sorted(
                mount_rows, key=lambda item: (item["target"], item["type"], item["source"], item["rw"]),
            )).decode("utf-8")
        if {row["id"] for row in rows} != set(ids):
            raise SupportError("backup_retirement_container_inventory_invalid")
        rows.sort(key=lambda row: row["id"])
        picker_mounts.sort(key=lambda item: (item["container"], item["source"], item["target"]))
        return _file_digest(_canonical_json(rows)), "present" if picker_mounts else "absent", picker_mounts

    @staticmethod
    def _retirement_health_state() -> dict[str, str]:
        result: dict[str, str] = {}
        for name, url in PUBLIC_HEALTH_URLS.items():
            try:
                with urlopen(url, timeout=12) as response:
                    result[name] = "healthy" if 200 <= response.status < 300 else "unhealthy"
            except (OSError, URLError, TimeoutError):
                result[name] = "unavailable"
        return result

    def collect_backup_retirement_snapshot(self, support_sha: str,
                                           connection_binding: str) -> dict[str, Any]:
        _safe_sha(support_sha, HEX40, "support_sha_invalid")
        _safe_sha(connection_binding, HEX64, "support_connection_invalid")
        remote = self._assert_host_repository()
        if self._remote_main_sha() != support_sha:
            raise SupportError("support_main_changed")
        _, status = self._git(["status", "--porcelain"])
        if status.strip():
            raise SupportError("backup_retirement_checkout_dirty")
        state_directory_state, _ = self.state_directory_status()
        backup_directory_state, _ = self.backup_directory_status()
        runtime = self._retirement_tree_state(
            BACKUP_RUNTIME_DIR, allow_symlinks=True,
            allowed_root_names={"current", "releases", "rollback", "install-journal.json"},
            unexpected_root_category="runtime",
        )
        config = self._retirement_tree_state(
            BACKUP_CONFIG_DIR, allowed_root_names={"destination.json", "keyring.json"},
            unexpected_root_category="config",
        )
        state = self._retirement_tree_state(
            BACKUP_STATE_DIR, allowed_root_names={"artifacts", "catalog", "service.lock"},
            unexpected_root_category="state",
        )
        state_summary = self._backup_state_summary(state)
        units = {name: self._retirement_unit_state(name) for name in BACKUP_UNITS}
        try:
            with os.scandir(BACKUP_SYSTEMD_DIR) as entries:
                unit_related_names = {
                    entry.name for entry in entries if entry.name.startswith("pyp-platform-backup.")
                }
        except OSError:
            raise SupportError("backup_retirement_unit_inventory_unavailable") from None
        if unit_related_names - set(BACKUP_UNITS):
            raise SupportError("backup_retirement_unexpected_unit_entry")
        picker = self._retirement_file_state(PICKER_CONFIG_PATH, expected_mode=0o400)
        containers_sha256, picker_mount, picker_mount_details = self._retirement_container_state()
        return {
            "host": EXPECTED_HOST,
            "repository": remote,
            "support_sha": support_sha,
            "remote_main_sha": support_sha,
            "connection_binding": connection_binding,
            "checkout_clean": True,
            "support_state_directory": state_directory_state,
            "support_receipt_directory": backup_directory_state,
            "runtime": runtime,
            "config": config,
            "state": state,
            "state_summary": state_summary,
            "units": units,
            "picker_config": picker,
            "picker_mount": picker_mount,
            "picker_mount_details": picker_mount_details,
            "containers_sha256": containers_sha256,
            "health": self._retirement_health_state(),
            "incomplete_install": bool(
                runtime["present"] and any(
                    item["path"] == "install-journal.json"
                    or item["path"].startswith("releases/.staging-")
                    or re.fullmatch(r"\.current-[0-9a-f]{40}", item["path"]) is not None
                    for item in runtime["entries"]
                )
            ),
        }

    def remove_backup_retirement_targets(self) -> None:
        self._assert_root()
        try:
            directories = (BACKUP_CONFIG_DIR, BACKUP_STATE_DIR, BACKUP_RUNTIME_DIR)
            # Check every deletion tree before the first filesystem or unit mutation.
            for directory in directories:
                self._assert_no_nested_mounts(directory)
            # A timer remains disabled and the service remains stopped. No
            # container or database command is issued by this removal.
            for directory in directories:
                if directory.exists() and not directory.is_symlink():
                    self._assert_no_nested_mounts(directory)
                    shutil.rmtree(directory)
            for name in BACKUP_UNITS:
                (BACKUP_SYSTEMD_DIR / name).unlink(missing_ok=True)
            self._run(["/usr/bin/systemctl", "daemon-reload"], code="backup_retirement_systemd_reload_failed")
            PICKER_CONFIG_PATH.unlink(missing_ok=True)
        except SupportError:
            raise
        except OSError:
            raise SupportError("backup_retirement_partial") from None

    def collect_snapshot(self, support_sha: str, connection_binding: str) -> dict[str, Any]:
        _safe_sha(support_sha, HEX40, "support_sha_invalid")
        _safe_sha(connection_binding, HEX64, "support_connection_invalid")
        remote = self._assert_host_repository()
        remote_sha = self._remote_main_sha()
        if remote_sha != support_sha:
            raise SupportError("support_main_changed")
        state_directory_state, state_directory_diagnostics = self.state_directory_status()
        backup_directory_state, backup_directory_diagnostics = self.backup_directory_status()
        return {
            "host": EXPECTED_HOST,
            "repository": remote,
            "support_sha": support_sha,
            "remote_main_sha": remote_sha,
            "connection_binding": connection_binding,
            "origin_main_ref": self._ref_sha(),
            "bridge": self.target_state("bridge"),
            "wrapper": self.target_state("wrapper"),
            "state_directory_state": state_directory_state,
            "state_directory_diagnostics": state_directory_diagnostics,
            "backup_directory_state": backup_directory_state,
            "backup_directory_diagnostics": backup_directory_diagnostics,
            "containers_sha256": self._container_digest(),
        }

    def _refs_digest(self) -> str:
        _, data = self._git(["for-each-ref", "--format=%(refname) %(objectname)"])
        return _file_digest(data)

    def refs_digest(self) -> str:
        return self._refs_digest()

    def load_candidates(self, support_sha: str) -> dict[str, dict[str, Any]]:
        refs_before = self._refs_digest()
        remote_before = self._remote_main_sha()
        if remote_before != support_sha:
            raise SupportError("support_main_changed")
        self._git(["fetch", "--no-tags", "--no-write-fetch-head", "--refmap=", "origin", "refs/heads/main"])
        if self._refs_digest() != refs_before:
            raise SupportError("support_fetch_changed_refs")
        if self._remote_main_sha() != support_sha:
            raise SupportError("support_main_changed")
        result: dict[str, dict[str, Any]] = {}
        for name in TARGETS:
            source = TARGET_SOURCES[name]
            _, blob_value = self._git(["rev-parse", f"{support_sha}:{source}"])
            try:
                blob = blob_value.decode("ascii").strip()
            except UnicodeDecodeError:
                raise SupportError("support_candidate_invalid") from None
            if not re.fullmatch(r"[0-9a-f]{40,64}", blob):
                raise SupportError("support_candidate_invalid")
            _, content = self._git(["cat-file", "blob", f"{support_sha}:{source}"])
            _, actual_blob_value = self._git(["hash-object", "--stdin"], input_data=content)
            if actual_blob_value.decode("ascii").strip() != blob:
                raise SupportError("support_candidate_invalid")
            result[name] = {"blob": blob, "content": content, "sha256": _file_digest(content),
                            "state": {"present": True, "sha256": _file_digest(content),
                                      "uid": 0, "gid": 0, "mode": 0o755, "links": 1}}
        return result

    @staticmethod
    def _validate_wrapper_content(content: bytes) -> None:
        result = LocalSupportHost._run(["bash", "-n"], input_data=content, code="support_wrapper_syntax_invalid")
        _ = result
        try:
            smoke = subprocess.run(
                ["sudo", "-n", "-H", "-u", "ubuntu", "env", "SSH_ORIGINAL_COMMAND=id", "bash", "-s"],
                input=content, capture_output=True, timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise SupportError("support_wrapper_allowlist_check_failed") from None
        output = smoke.stdout + smoke.stderr
        if smoke.returncode == 0 or re.search(rb"\buid=\d+", output) or re.search(rb"\bgid=\d+", output):
            raise SupportError("support_wrapper_arbitrary_command_accepted")

    @staticmethod
    def _validate_bridge_content(content: bytes) -> None:
        try:
            compile(content.decode("utf-8"), "production_app_compose_bridge.py", "exec")
        except (UnicodeDecodeError, SyntaxError, ValueError):
            raise SupportError("support_bridge_syntax_invalid") from None

    def validate_candidates(self, candidates: dict[str, dict[str, Any]]) -> None:
        self._validate_bridge_content(candidates["bridge"]["content"])
        self._validate_wrapper_content(candidates["wrapper"]["content"])

    @staticmethod
    def _fixed_directory_status(path: Path, *, mode: int, parent_mode: int | None = None,
                                check_parent_chain: bool = False) -> tuple[str, list[str]]:
        parent = path.parent
        current = parent
        while True:
            try:
                info = current.lstat()
            except FileNotFoundError:
                return "parent_invalid", ["parent_invalid"]
            except OSError:
                return "unavailable", ["unavailable"]
            expected_parent_mode = parent_mode if current == parent else None
            if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                    or info.st_uid != 0 or info.st_gid != 0
                    or (expected_parent_mode is not None
                        and stat.S_IMODE(info.st_mode) != expected_parent_mode)):
                return "parent_invalid", ["parent_invalid"]
            if not check_parent_chain or current == current.parent:
                break
            current = current.parent
        try:
            target = path.lstat()
        except FileNotFoundError:
            return "creatable", ["creatable"]
        except OSError:
            return "unavailable", ["unavailable"]
        if stat.S_ISLNK(target.st_mode):
            return "directory_invalid", ["target_symlink"]
        diagnostics = []
        if not stat.S_ISDIR(target.st_mode):
            diagnostics.append("target_type_invalid")
        if target.st_uid != 0:
            diagnostics.append("target_owner_invalid")
        if target.st_gid != 0:
            diagnostics.append("target_group_invalid")
        if stat.S_IMODE(target.st_mode) != mode:
            diagnostics.append("target_mode_invalid")
        diagnostics.sort(key=TARGET_DIRECTORY_DIAGNOSTIC_ORDER.index)
        if diagnostics:
            return "directory_invalid", diagnostics
        return "ready", ["ready"]

    @staticmethod
    def _fixed_directory_state(path: Path, *, mode: int, parent_mode: int | None = None,
                               check_parent_chain: bool = False) -> str:
        state, _diagnostics = LocalSupportHost._fixed_directory_status(
            path, mode=mode, parent_mode=parent_mode, check_parent_chain=check_parent_chain,
        )
        return state

    @staticmethod
    def state_directory_status() -> tuple[str, list[str]]:
        return LocalSupportHost._fixed_directory_status(
            STATE_DIR, mode=0o700, check_parent_chain=True,
        )

    @staticmethod
    def backup_directory_status() -> tuple[str, list[str]]:
        return LocalSupportHost._fixed_directory_status(
            BACKUPS_DIR, mode=0o700, parent_mode=0o755,
        )

    @staticmethod
    def state_directory_state() -> str:
        return LocalSupportHost.state_directory_status()[0]

    @staticmethod
    def backup_directory_state() -> str:
        return LocalSupportHost.backup_directory_status()[0]

    def repair_backup_directory_mode(self) -> None:
        """Set the fixed backup directory to 0700 through a verified directory fd."""
        if (os.name != "posix" or not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW")
                or not hasattr(os, "fchmod")):
            raise SupportError("support_platform_unsupported")

        parent_fd: int | None = None
        target_fd: int | None = None
        mutation_attempted = False

        def valid_parent(info: os.stat_result) -> bool:
            return (stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                    and info.st_uid == 0 and info.st_gid == 0
                    and stat.S_IMODE(info.st_mode) == 0o755)

        def valid_target(info: os.stat_result) -> bool:
            return (stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                    and info.st_uid == 0 and info.st_gid == 0
                    and stat.S_IMODE(info.st_mode) != 0o700)

        def same_object(left: os.stat_result, right: os.stat_result) -> bool:
            return left.st_dev == right.st_dev and left.st_ino == right.st_ino

        try:
            if self.backup_directory_status() != ("directory_invalid", ["target_mode_invalid"]):
                raise SupportError("support_backup_directory_invalid")

            parent_before = BACKUPS_DIR.parent.lstat()
            if not valid_parent(parent_before):
                raise SupportError("support_backup_directory_invalid")
            parent_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            parent_fd = os.open(BACKUPS_DIR.parent, parent_flags)
            parent_open = os.fstat(parent_fd)
            if not valid_parent(parent_open) or not same_object(parent_before, parent_open):
                raise SupportError("support_backup_directory_invalid")

            target_before = os.stat(BACKUPS_DIR.name, dir_fd=parent_fd, follow_symlinks=False)
            if not valid_target(target_before):
                raise SupportError("support_backup_directory_invalid")
            target_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            target_fd = os.open(BACKUPS_DIR.name, target_flags, dir_fd=parent_fd)
            target_open = os.fstat(target_fd)
            if not valid_target(target_open) or not same_object(target_before, target_open):
                raise SupportError("support_backup_directory_invalid")

            # Revalidate both fixed names immediately before the only mutation.
            parent_current = BACKUPS_DIR.parent.lstat()
            target_current = os.stat(BACKUPS_DIR.name, dir_fd=parent_fd, follow_symlinks=False)
            if (not valid_parent(parent_current) or not same_object(parent_open, parent_current)
                    or not valid_target(target_current) or not same_object(target_open, target_current)
                    or self.backup_directory_status() != ("directory_invalid", ["target_mode_invalid"])):
                raise SupportError("support_backup_directory_invalid")

            mutation_attempted = True
            os.fchmod(target_fd, 0o700)

            parent_after = BACKUPS_DIR.parent.lstat()
            target_after = os.stat(BACKUPS_DIR.name, dir_fd=parent_fd, follow_symlinks=False)
            target_open_after = os.fstat(target_fd)
            if (not valid_parent(parent_after) or not same_object(parent_open, parent_after)
                    or not stat.S_ISDIR(target_open_after.st_mode)
                    or stat.S_ISLNK(target_open_after.st_mode)
                    or target_open_after.st_uid != 0 or target_open_after.st_gid != 0
                    or stat.S_IMODE(target_open_after.st_mode) != 0o700
                    or not same_object(target_open, target_open_after)
                    or not stat.S_ISDIR(target_after.st_mode) or stat.S_ISLNK(target_after.st_mode)
                    or target_after.st_uid != 0 or target_after.st_gid != 0
                    or stat.S_IMODE(target_after.st_mode) != 0o700
                    or not same_object(target_open, target_after)):
                raise SupportError("support_backup_mode_unverified")
        except SupportError:
            if mutation_attempted:
                raise SupportError("support_backup_mode_unverified") from None
            raise
        except BaseException:  # noqa: BLE001 - the fixed CLI must not expose host details.
            if mutation_attempted:
                raise SupportError("support_backup_mode_unverified") from None
            raise SupportError("support_backup_directory_invalid") from None
        finally:
            for descriptor in (target_fd, parent_fd):
                if descriptor is not None:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass

    def ensure_state_directories(self) -> None:
        state = self.state_directory_state()
        if state == "creatable":
            try:
                STATE_DIR.mkdir(mode=0o700)
            except FileExistsError:
                pass
            except OSError:
                raise SupportError("support_state_directory_invalid") from None
            state = self.state_directory_state()
        if state != "ready":
            raise SupportError("support_state_directory_invalid")

    def check_no_staging(self) -> None:
        paths = []
        for path in TARGET_PATHS.values():
            for phase in ("prepare", "prepare-rollback", "restore", "restore-rollback"):
                paths.append(path.parent / f".{path.name}.support-{phase}.new")
        for path in paths:
            if path.exists() or path.is_symlink():
                raise SupportError("support_staging_exists")

    def preserve_targets(self, snapshot: dict[str, Any], operation_id: str, label: str) -> dict[str, str | None]:
        self.ensure_state_directories()
        self._ensure_backups_directory()
        result: dict[str, str | None] = {}
        for name in TARGETS:
            state = snapshot[name]
            if not state["present"]:
                result[name] = None
                continue
            data = self._read_target_exact(name, state)
            filename = f"preflight-support-{label}-{operation_id}-{name}"
            destination = BACKUPS_DIR / filename
            try:
                descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
                with os.fdopen(descriptor, "wb") as handle:
                    os.fchown(handle.fileno(), 0, 0)
                    os.fchmod(handle.fileno(), 0o600)
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError:
                raise SupportError("support_backup_exists") from None
            except OSError:
                raise SupportError("support_backup_write_failed") from None
            self._fsync_directory(BACKUPS_DIR)
            self._assert_file(destination, owner="root", group="root", mode=0o600, links=1)
            if _file_digest(destination.read_bytes()) != state["sha256"]:
                raise SupportError("support_backup_verification_failed")
            result[name] = filename
        return result

    @staticmethod
    def _ensure_backups_directory(*, create: bool = True) -> None:
        state = LocalSupportHost.backup_directory_state()
        if state == "creatable" and create:
            try:
                BACKUPS_DIR.mkdir(mode=0o700)
            except FileExistsError:
                pass
            except OSError:
                raise SupportError("support_backup_directory_invalid") from None
            state = LocalSupportHost.backup_directory_state()
        if state != "ready":
            raise SupportError("support_backup_directory_invalid")

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError:
            raise SupportError("support_durability_failed") from None

    def create_receipt(self, payload: dict[str, Any]) -> str:
        self.ensure_state_directories()
        operation_id = payload.get("operation_id")
        kind = payload.get("kind")
        if not isinstance(operation_id, str) or not re.fullmatch(r"[0-9a-f]{32}", operation_id):
            raise SupportError("support_receipt_invalid")
        if kind not in {
            "preparation-intent", "preparation-complete", "restoration-intent", "restoration-complete",
            "backup-runtime-retirement-intent", "backup-runtime-retirement-complete",
            "backup-runtime-retirement-incomplete",
        }:
            raise SupportError("support_receipt_invalid")
        filename = f"preflight-support-{kind}-{operation_id}.json"
        destination = STATE_DIR / filename
        staging = STATE_DIR / f".{filename}.new"
        content = _canonical_json(payload) + b"\n"
        try:
            descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                os.fchown(handle.fileno(), 0, 0)
                os.fchmod(handle.fileno(), 0o600)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(staging, destination, follow_symlinks=False)
            os.unlink(staging)
            self._fsync_directory(STATE_DIR)
        except FileExistsError:
            raise SupportError("support_receipt_or_staging_exists") from None
        except OSError:
            raise SupportError("support_receipt_write_failed") from None
        self._assert_file(destination, owner="root", group="root", mode=0o600, links=1)
        if destination.read_bytes() != content:
            raise SupportError("support_receipt_verification_failed")
        return _file_digest(content)

    def read_receipt(self, receipt_sha256: str) -> dict[str, Any]:
        _safe_sha(receipt_sha256, HEX64, "support_receipt_invalid")
        self._assert_directory(STATE_DIR, owner="root", group="root", mode=0o700)
        matches: list[dict[str, Any]] = []
        try:
            files = list(STATE_DIR.iterdir())
        except OSError:
            raise SupportError("support_receipt_invalid") from None
        for path in files:
            if path.name.startswith(".preflight-support-"):
                raise SupportError("support_receipt_invalid")
            if not path.name.startswith("preflight-support-"):
                continue
            if not re.fullmatch(
                    r"preflight-support-(?:preparation|restoration)-(?:intent|complete)-[0-9a-f]{32}\.json"
                    r"|preflight-support-backup-runtime-retirement-(?:intent|complete|incomplete)-[0-9a-f]{32}\.json",
                    path.name):
                raise SupportError("support_receipt_invalid")
            self._assert_file(path, owner="root", group="root", mode=0o600, links=1)
            try:
                content = path.read_bytes()
                after = path.lstat()
            except OSError:
                raise SupportError("support_receipt_invalid") from None
            if after.st_size != len(content) or after.st_nlink != 1:
                raise SupportError("support_receipt_invalid")
            if _file_digest(content) == receipt_sha256:
                try:
                    value = json.loads(content)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    raise SupportError("support_receipt_invalid") from None
                if isinstance(value, dict):
                    matches.append(value)
        if len(matches) != 1:
            raise SupportError("support_receipt_missing_or_ambiguous")
        return matches[0]

    def current_ref(self) -> str | None:
        return self._ref_sha()

    def update_ref(self, expected: str | None, desired: str | None) -> None:
        if expected == desired:
            if self.current_ref() != expected:
                raise SupportError("support_ref_changed")
            return
        if self.current_ref() != expected:
            raise SupportError("support_ref_changed")
        if desired is None:
            args = ["update-ref", "-d", MAIN_REF, expected]
        else:
            args = ["update-ref", MAIN_REF, desired, expected or ZERO_SHA]
        self._git(args)
        if self.current_ref() != desired:
            raise SupportError("support_ref_verification_failed")

    def _read_target_exact(self, name: str, expected: dict[str, Any]) -> bytes:
        if not expected.get("present"):
            raise SupportError("support_target_expected_absent")
        path = TARGET_PATHS[name]
        current = self.target_state(name)
        if current != expected:
            raise SupportError("support_target_changed")
        try:
            return path.read_bytes()
        except OSError:
            raise SupportError("support_target_unreadable") from None

    def install_file(self, name: str, expected: dict[str, Any], content: bytes, phase: str) -> None:
        if self.target_state(name) != expected:
            raise SupportError("support_target_changed")
        path = TARGET_PATHS[name]
        stage = path.parent / f".{path.name}.support-{phase}.new"
        try:
            descriptor = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o755)
            with os.fdopen(descriptor, "wb") as handle:
                os.fchown(handle.fileno(), 0, 0)
                os.fchmod(handle.fileno(), 0o755)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            self._fsync_directory(path.parent)
            if self.target_state(name) != expected:
                raise SupportError("support_target_changed")
            os.replace(stage, path)
            self._fsync_directory(path.parent)
        except FileExistsError:
            raise SupportError("support_staging_exists") from None
        except SupportError:
            raise
        except OSError:
            raise SupportError("support_target_swap_failed") from None

    def restore_file(self, name: str, expected_current: dict[str, Any], desired: dict[str, Any],
                     backup_name: str | None, phase: str) -> None:
        if self.target_state(name) != expected_current:
            raise SupportError("support_target_unexpected")
        path = TARGET_PATHS[name]
        if not desired.get("present"):
            try:
                path.unlink()
                self._fsync_directory(path.parent)
            except OSError:
                raise SupportError("support_target_restore_failed") from None
            if self.target_state(name) != desired:
                raise SupportError("support_target_restore_unverified")
            return
        if not isinstance(backup_name, str) or not re.fullmatch(r"preflight-support-[a-z-]+-[0-9a-f]{32}-[a-z]+", backup_name):
            raise SupportError("support_backup_invalid")
        backup = BACKUPS_DIR / backup_name
        try:
            self._assert_file(backup, owner="root", group="root", mode=0o600, links=1)
            content = backup.read_bytes()
        except (OSError, SupportError):
            raise SupportError("support_backup_invalid") from None
        if _file_digest(content) != desired.get("sha256"):
            raise SupportError("support_backup_invalid")
        self.install_file(name, expected_current, content, phase)
        if self.target_state(name) != desired:
            raise SupportError("support_target_restore_unverified")

    def validate_installed(self, support_sha: str, expected_states: dict[str, Any],
                           containers_sha256: str) -> None:
        if self.current_ref() != support_sha:
            raise SupportError("support_ref_verification_failed")
        for name, expected in expected_states.items():
            if self.target_state(name) != expected:
                raise SupportError("support_target_verification_failed")
        if self._container_digest() != containers_sha256:
            raise SupportError("support_containers_changed")
        self._smoke_installed(support_sha)

    def _smoke_installed(self, support_sha: str) -> None:
        bridge = TARGET_PATHS["bridge"]
        result = subprocess.run(["sudo", "-n", "/usr/bin/python3.10", "-B", str(bridge),
                                 "--mode", "inventory", "--sha", support_sha, "hashes"],
                                cwd=str(PROJECT_ROOT), capture_output=True,
                                timeout=60, check=False)
        if result.returncode != 0:
            raise SupportError("support_bridge_allowlist_check_failed")
        denied = subprocess.run(["sudo", "-n", "/usr/bin/python3.10", "-B", str(bridge),
                                 "--mode", "inventory", "--sha", support_sha, "compose", "--",
                                 "exec", "-T", "api", "sh"], cwd=str(PROJECT_ROOT),
                                capture_output=True, timeout=30, check=False)
        if denied.returncode == 0 or re.search(rb"\buid=\d+", denied.stdout + denied.stderr):
            raise SupportError("support_bridge_arbitrary_command_accepted")
        self._validate_wrapper_content(TARGET_PATHS["wrapper"].read_bytes())

    def assert_state(self, expected: dict[str, Any]) -> None:
        if self.current_ref() != expected.get("origin_main_ref"):
            raise SupportError("support_state_verification_failed")
        for name in TARGETS:
            if self.target_state(name) != expected.get(name):
                raise SupportError("support_state_verification_failed")
        if self._container_digest() != expected.get("containers_sha256"):
            raise SupportError("support_containers_changed")

    def assert_previous_ref_ancestor(self, old_ref: str | None, target_sha: str) -> None:
        if old_ref is None:
            return
        status, _ = self._git(["cat-file", "-e", f"{old_ref}^{{commit}}"], allow_failure=True)
        if status != 0:
            raise SupportError("support_previous_ref_object_missing")
        status, _ = self._git(["merge-base", "--is-ancestor", old_ref, target_sha], allow_failure=True)
        if status != 0:
            raise SupportError("support_previous_ref_not_ancestor")

    def assert_previous_ref_object(self, ref_sha: str | None) -> None:
        if ref_sha is None:
            return
        if not HEX40.fullmatch(ref_sha):
            raise SupportError("support_previous_ref_invalid")
        status, _ = self._git(["cat-file", "-e", f"{ref_sha}^{{commit}}"], allow_failure=True)
        if status != 0:
            raise SupportError("support_previous_ref_object_missing")

    def validate_restored(self, desired: dict[str, Any], containers_sha256: str) -> None:
        if self.current_ref() != desired.get("origin_main_ref"):
            raise SupportError("support_restore_unverified")
        for name in TARGETS:
            state = desired.get(name)
            if self.target_state(name) != state:
                raise SupportError("support_restore_unverified")
            if state and state.get("present"):
                content = self._read_target_exact(name, state)
                if name == "bridge":
                    self._validate_bridge_content(content)
                    self._validate_bridge_allowlist(content, desired.get("origin_main_ref"))
                else:
                    self._validate_wrapper_content(content)
        if self._container_digest() != containers_sha256:
            raise SupportError("support_containers_changed")

    @staticmethod
    def _validate_bridge_allowlist(content: bytes, support_sha: str | None) -> None:
        bootstrap = b"import sys\nsource=sys.stdin.buffer.read()\nexec(compile(source, 'production_app_compose_bridge.py', 'exec'), {'__name__':'__main__'})"
        try:
            denied = subprocess.run(
                ["sudo", "-n", "/usr/bin/python3.10", "-B", "-c", bootstrap.decode("ascii"),
                 "--mode", "inventory", "--sha", support_sha or ZERO_SHA,
                 "compose", "--", "exec", "-T", "api", "sh"],
                input=content, capture_output=True, timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise SupportError("support_bridge_allowlist_check_failed") from None
        if denied.returncode == 0 or re.search(rb"\buid=\d+", denied.stdout + denied.stderr):
            raise SupportError("support_bridge_arbitrary_command_accepted")

    def assert_no_other_refs_changed(self, expected_digest: str) -> None:
        if self._refs_digest() != expected_digest:
            raise SupportError("support_other_refs_changed")

    def read_preparation(self, receipt_sha256: str) -> tuple[dict[str, Any], dict[str, Any]]:
        complete, intent = _load_preparation_receipt(self, receipt_sha256)
        self._ensure_backups_directory(create=False)
        snapshot = intent.get("snapshot")
        backups = intent.get("backup_names")
        if not isinstance(snapshot, dict) or not isinstance(backups, dict):
            raise SupportError("support_preparation_receipt_invalid")
        for name in TARGETS:
            state = snapshot.get(name)
            backup_name = backups.get(name)
            if not isinstance(state, dict) or not isinstance(state.get("present"), bool):
                raise SupportError("support_preparation_receipt_invalid")
            if not state["present"]:
                if backup_name is not None:
                    raise SupportError("support_preparation_receipt_invalid")
                continue
            if (not isinstance(backup_name, str)
                    or not re.fullmatch(r"preflight-support-prepare-[0-9a-f]{32}-[a-z]+", backup_name)):
                raise SupportError("support_preparation_receipt_invalid")
            backup = BACKUPS_DIR / backup_name
            self._assert_file(backup, owner="root", group="root", mode=0o600, links=1)
            try:
                if _file_digest(backup.read_bytes()) != state.get("sha256"):
                    raise SupportError("support_preparation_backup_invalid")
            except OSError:
                raise SupportError("support_preparation_backup_invalid") from None
        return complete, intent


class SupportCoordinator:
    """Transactional coordinator shared by the production adapter and tests."""

    def __init__(self, host: Any):
        self.host = host

    def inventory(self, support_sha: str, connection_binding: str) -> tuple[str, dict[str, Any]]:
        with self.host.lock():
            snapshot = self.host.collect_snapshot(support_sha, connection_binding)
            return _digest(snapshot), snapshot

    @staticmethod
    def _assert_backup_retirement_ready(snapshot: dict[str, Any]) -> None:
        if snapshot.get("checkout_clean") is not True:
            raise SupportError("backup_retirement_checkout_dirty")
        if (snapshot.get("support_state_directory") != "ready"
                or snapshot.get("support_receipt_directory") != "ready"):
            raise SupportError("backup_retirement_receipt_storage_unavailable")
        if snapshot.get("incomplete_install") is True:
            raise SupportError("backup_retirement_install_incomplete")
        if snapshot.get("picker_mount") != "absent":
            raise SupportError("backup_retirement_picker_mount_present")
        if snapshot.get("picker_mount_details") != []:
            raise SupportError("backup_retirement_picker_mount_present")
        state_summary = snapshot.get("state_summary")
        if (not isinstance(state_summary, dict)
                or set(state_summary) != {"encrypted_artifacts", "partial_artifacts", "catalog_files", "files", "bytes"}
                or any(type(value) is not int or value < 0 for value in state_summary.values())):
            raise SupportError("backup_retirement_state_inventory_invalid")
        if snapshot.get("health") != {name: "healthy" for name in PUBLIC_HEALTH_URLS}:
            raise SupportError("backup_retirement_application_unhealthy")
        units = snapshot.get("units")
        if not isinstance(units, dict) or set(units) != set(BACKUP_UNITS):
            raise SupportError("backup_retirement_unit_state_invalid")
        for name, state in units.items():
            if not isinstance(state, dict) or state.get("active") != "inactive":
                raise SupportError("backup_retirement_unit_active")
            if state.get("file") == "present":
                if state.get("load") != "loaded" or state.get("fragment") != str(BACKUP_SYSTEMD_DIR / name):
                    raise SupportError("backup_retirement_unit_state_invalid")
            elif state.get("load") != "not-found":
                raise SupportError("backup_retirement_unit_state_invalid")
            allowed_enabled = {"disabled", "not-found"}
            if name.endswith(".service"):
                allowed_enabled |= {"static", "indirect"}
            if state.get("enabled") not in allowed_enabled:
                raise SupportError("backup_retirement_unit_enabled")
        for target in ("runtime", "config", "state"):
            value = snapshot.get(target)
            if not isinstance(value, dict) or type(value.get("present")) is not bool:
                raise SupportError("backup_retirement_inventory_invalid")
            nested_mounts = value.get("nested_mounts")
            if not isinstance(nested_mounts, list):
                raise SupportError("backup_retirement_mount_inventory_invalid")
            if nested_mounts:
                raise SupportError("backup_retirement_nested_mount")
        config = snapshot["config"]
        config_entries = config.get("entries")
        if not isinstance(config_entries, list):
            raise SupportError("backup_retirement_inventory_invalid")
        config_files: set[str] = set()
        for entry in config_entries:
            if not isinstance(entry, dict):
                raise SupportError("backup_retirement_inventory_invalid")
            path = entry.get("path")
            if (not isinstance(path, str)
                    or path not in {"destination.json", "keyring.json"}
                    or entry.get("kind") != "file"
                    or entry.get("mode") != 0o400
                    or path in config_files):
                raise SupportError("backup_retirement_unexpected_config_entry")
            config_files.add(path)
        if config.get("present") is False and config_entries:
            raise SupportError("backup_retirement_inventory_invalid")

    def backup_retirement_inventory(self, support_sha: str,
                                    connection_binding: str) -> tuple[str, dict[str, Any]]:
        with self.host.lock():
            snapshot = self.host.collect_backup_retirement_snapshot(support_sha, connection_binding)
            return _digest(snapshot), snapshot

    def retire_backup_runtime(self, support_sha: str, connection_binding: str,
                              approval_fingerprint: str) -> str:
        _safe_sha(approval_fingerprint, HEX64, "support_fingerprint_invalid")
        with self.host.lock():
            before = self.host.collect_backup_retirement_snapshot(support_sha, connection_binding)
            if _digest(before) != approval_fingerprint:
                raise SupportError("backup_retirement_fingerprint_changed")
            self._assert_backup_retirement_ready(before)
            operation_id = uuid.uuid4().hex
            intent = {
                "schema": "pyp-backup-runtime-retirement-v1",
                "kind": "backup-runtime-retirement-intent",
                "operation_id": operation_id,
                "status": "started",
                "support_sha": support_sha,
                "fingerprint": approval_fingerprint,
            }
            self.host.create_receipt(intent)
            try:
                latest = self.host.collect_backup_retirement_snapshot(support_sha, connection_binding)
                if _digest(latest) != approval_fingerprint:
                    raise SupportError("backup_retirement_fingerprint_changed")
                self._assert_backup_retirement_ready(latest)
                self.host.remove_backup_retirement_targets()
                after = self.host.collect_backup_retirement_snapshot(support_sha, connection_binding)
                self._assert_backup_retirement_ready(after)
                if (any(after[name]["present"] for name in ("runtime", "config", "state"))
                        or any(state.get("file") != "absent" or state.get("load") != "not-found"
                               for state in after["units"].values())
                        or after["picker_config"].get("present") is True
                        or after["picker_mount"] != "absent"
                        or after["picker_mount_details"] != []
                        or after["containers_sha256"] != before["containers_sha256"]):
                    raise SupportError("backup_retirement_postcheck_failed")
                completed = {
                    "schema": "pyp-backup-runtime-retirement-v1",
                    "kind": "backup-runtime-retirement-complete",
                    "operation_id": operation_id,
                    "status": "complete",
                    "support_sha": support_sha,
                    "approved_fingerprint": approval_fingerprint,
                    "postcheck_fingerprint": _digest(after),
                    "removed": ["runtime", "config", "state", "systemd_units", "picker_config"],
                }
                return self.host.create_receipt(completed)
            except BaseException:  # noqa: BLE001 - cleanup is irreversible and uncertain state is terminal.
                try:
                    self.host.create_receipt({
                        "schema": "pyp-backup-runtime-retirement-v1",
                        "kind": "backup-runtime-retirement-incomplete",
                        "operation_id": operation_id,
                        "status": "incomplete",
                        "support_sha": support_sha,
                        "approved_fingerprint": approval_fingerprint,
                    })
                except BaseException:  # noqa: BLE001 - never disclose host exception details.
                    raise SupportError("backup_retirement_incomplete") from None
                raise SupportError("backup_retirement_incomplete") from None

    def repair_backup_directory_mode(self, support_sha: str, connection_binding: str,
                                     approval_fingerprint: str) -> None:
        _safe_sha(approval_fingerprint, HEX64, "support_fingerprint_invalid")
        with self.host.lock():
            before = self.host.collect_snapshot(support_sha, connection_binding)
            if _digest(before) != approval_fingerprint:
                raise SupportError("support_fingerprint_changed")
            if (before.get("backup_directory_state") != "directory_invalid"
                    or before.get("backup_directory_diagnostics") != ["target_mode_invalid"]):
                raise SupportError("support_backup_directory_invalid")

            self.host.repair_backup_directory_mode()
            try:
                after = self.host.collect_snapshot(support_sha, connection_binding)
                expected = dict(before)
                expected["backup_directory_state"] = "ready"
                expected["backup_directory_diagnostics"] = ["ready"]
                if after != expected:
                    raise SupportError("support_backup_mode_unverified")
            except BaseException:  # noqa: BLE001 - post-mutation uncertainty is terminal and sanitized.
                raise SupportError("support_backup_mode_unverified") from None

    def prepare(self, support_sha: str, connection_binding: str, approval_fingerprint: str) -> str:
        _safe_sha(approval_fingerprint, HEX64, "support_fingerprint_invalid")
        with self.host.lock():
            snapshot = self.host.collect_snapshot(support_sha, connection_binding)
            if _digest(snapshot) != approval_fingerprint:
                raise SupportError("support_fingerprint_changed")
            self._assert_storage_preconditions(snapshot)
            self.host.check_no_staging()
            refs_before_fetch = self.host.refs_digest()
            candidates = self.host.load_candidates(support_sha)
            self.host.assert_no_other_refs_changed(refs_before_fetch)
            self.host.validate_candidates(candidates)
            self.host.assert_previous_ref_ancestor(snapshot["origin_main_ref"], support_sha)
            operation_id = uuid.uuid4().hex
            backups = self.host.preserve_targets(snapshot, operation_id, "prepare")
            candidate_states = {name: candidates[name]["state"] for name in TARGETS}
            intent = {
                "schema": "pyp-app-preflight-support-v1", "kind": "preparation-intent",
                "operation_id": operation_id, "status": "pending", "snapshot": snapshot,
                "support_fingerprint": approval_fingerprint,
                "candidate_blobs": {name: candidates[name]["blob"] for name in TARGETS},
                "candidate_states": candidate_states, "backup_names": backups,
            }
            intent_digest = self.host.create_receipt(intent)
            mutated = False
            try:
                mutated = True
                self.host.update_ref(snapshot["origin_main_ref"], support_sha)
                self.host.install_file("bridge", snapshot["bridge"], candidates["bridge"]["content"], "prepare")
                self.host.install_file("wrapper", snapshot["wrapper"], candidates["wrapper"]["content"], "prepare")
                self.host.validate_installed(support_sha, candidate_states, snapshot["containers_sha256"])
                completed = {
                    "schema": "pyp-app-preflight-support-v1", "kind": "preparation-complete",
                    "operation_id": operation_id, "status": "complete", "intent_sha256": intent_digest,
                    "support_sha": support_sha, "connection_binding": connection_binding,
                    "prepared_state": {"origin_main_ref": support_sha, **candidate_states,
                                       "containers_sha256": snapshot["containers_sha256"]},
                }
                return self.host.create_receipt(completed)
            except BaseException:
                if not mutated:
                    raise
                try:
                    self._compensate(
                        original={"origin_main_ref": snapshot["origin_main_ref"], **{n: snapshot[n] for n in TARGETS}},
                        candidate={"origin_main_ref": support_sha, **candidate_states},
                        backups=backups,
                        operation_id=operation_id,
                        phase="prepare-rollback",
                    )
                    self.host.assert_state({"origin_main_ref": snapshot["origin_main_ref"],
                                            **{n: snapshot[n] for n in TARGETS},
                                            "containers_sha256": snapshot["containers_sha256"]})
                except BaseException:  # noqa: BLE001 - compensation must also run after cancellation signals.
                    raise SupportError("support_preparation_rollback_unverified") from None
                raise SupportError("support_preparation_failed_rolled_back") from None

    def restore_inventory(self, support_sha: str, connection_binding: str,
                          preparation_receipt_sha256: str) -> tuple[str, dict[str, Any]]:
        _safe_sha(preparation_receipt_sha256, HEX64, "support_receipt_invalid")
        with self.host.lock():
            complete, intent = self.host.read_preparation(preparation_receipt_sha256)
            self.host.assert_previous_ref_object(intent["snapshot"]["origin_main_ref"])
            snapshot = self.host.collect_snapshot(support_sha, connection_binding)
            self._assert_prepared_active(snapshot, complete)
            view = {"snapshot": snapshot, "preparation_receipt_sha256": preparation_receipt_sha256,
                    "preparation_intent_sha256": complete["intent_sha256"]}
            return _digest(view), view

    def restore(self, support_sha: str, connection_binding: str, approval_fingerprint: str,
                preparation_receipt_sha256: str) -> str:
        _safe_sha(approval_fingerprint, HEX64, "support_fingerprint_invalid")
        _safe_sha(preparation_receipt_sha256, HEX64, "support_receipt_invalid")
        with self.host.lock():
            complete, intent = self.host.read_preparation(preparation_receipt_sha256)
            self.host.assert_previous_ref_object(intent["snapshot"]["origin_main_ref"])
            snapshot = self.host.collect_snapshot(support_sha, connection_binding)
            self._assert_prepared_active(snapshot, complete)
            view = {"snapshot": snapshot, "preparation_receipt_sha256": preparation_receipt_sha256,
                    "preparation_intent_sha256": complete["intent_sha256"]}
            if _digest(view) != approval_fingerprint:
                raise SupportError("support_restore_fingerprint_changed")
            self._assert_storage_preconditions(snapshot)
            self.host.check_no_staging()
            self.host.assert_previous_ref_object(snapshot["origin_main_ref"])
            operation_id = uuid.uuid4().hex
            backups = self.host.preserve_targets(snapshot, operation_id, "restore")
            intent_restore = {
                "schema": "pyp-app-preflight-support-v1", "kind": "restoration-intent",
                "operation_id": operation_id, "status": "pending", "snapshot": snapshot,
                "support_fingerprint": approval_fingerprint,
                "preparation_receipt_sha256": preparation_receipt_sha256,
                "desired_state": {"origin_main_ref": intent["snapshot"]["origin_main_ref"],
                                  **{name: intent["snapshot"][name] for name in TARGETS}},
                "backup_names": backups,
            }
            intent_digest = self.host.create_receipt(intent_restore)
            original = {"origin_main_ref": snapshot["origin_main_ref"], **{n: snapshot[n] for n in TARGETS}}
            desired = intent_restore["desired_state"]
            mutated = False
            try:
                for name in ("wrapper", "bridge"):
                    mutated = True
                    self.host.restore_file(name, snapshot[name], desired[name],
                                           intent["backup_names"].get(name), "restore")
                mutated = True
                self.host.update_ref(snapshot["origin_main_ref"], desired["origin_main_ref"])
                self.host.validate_restored(desired, snapshot["containers_sha256"])
                completed = {
                    "schema": "pyp-app-preflight-support-v1", "kind": "restoration-complete",
                    "operation_id": operation_id, "status": "complete", "intent_sha256": intent_digest,
                    "preparation_receipt_sha256": preparation_receipt_sha256,
                    "restored_state": {**desired, "containers_sha256": snapshot["containers_sha256"]},
                }
                return self.host.create_receipt(completed)
            except BaseException:
                if not mutated:
                    raise
                try:
                    self._compensate(original=original, candidate=desired, backups=backups,
                                     operation_id=operation_id, phase="restore-rollback")
                    self.host.assert_state({**original, "containers_sha256": snapshot["containers_sha256"]})
                except BaseException:  # noqa: BLE001 - compensation must also run after cancellation signals.
                    raise SupportError("support_restore_fallback_unverified") from None
                raise SupportError("support_restore_failed_rolled_back") from None

    @staticmethod
    def _assert_storage_preconditions(snapshot: dict[str, Any]) -> None:
        if snapshot.get("state_directory_state") not in SAFE_DIRECTORY_STATES:
            raise SupportError("support_state_directory_invalid")
        if snapshot.get("backup_directory_state") not in SAFE_DIRECTORY_STATES:
            raise SupportError("support_backup_directory_invalid")

    @staticmethod
    def _assert_prepared_active(snapshot: dict[str, Any], complete: dict[str, Any]) -> None:
        expected = complete.get("prepared_state")
        if (complete.get("status") != "complete" or complete.get("kind") != "preparation-complete"
                or not isinstance(expected, dict)):
            raise SupportError("support_preparation_receipt_invalid")
        actual = {"origin_main_ref": snapshot["origin_main_ref"],
                 **{name: snapshot[name] for name in TARGETS},
                 "containers_sha256": snapshot["containers_sha256"]}
        if actual != expected:
            raise SupportError("support_prepared_state_changed")

    def _compensate(self, *, original: dict[str, Any], candidate: dict[str, Any],
                    backups: dict[str, str | None], operation_id: str, phase: str) -> None:
        # One pass in reverse mutation order; unknown states are never overwritten.
        for name in ("wrapper", "bridge", "origin_main_ref"):
            if name == "origin_main_ref":
                current = self.host.current_ref()
                old = original[name]
                attempted = candidate[name]
                if current == old:
                    continue
                if current != attempted:
                    raise SupportError("support_rollback_target_unexpected")
                self.host.update_ref(attempted, old)
                continue
            current = self.host.target_state(name)
            old = original[name]
            attempted = candidate[name]
            if current == old:
                continue
            if current != attempted:
                raise SupportError("support_rollback_target_unexpected")
            self.host.restore_file(name, attempted, old, backups.get(name), phase)


def _load_preparation_receipt(host: LocalSupportHost, digest: str) -> tuple[dict[str, Any], dict[str, Any]]:
    complete = host.read_receipt(digest)
    if (complete.get("schema") != "pyp-app-preflight-support-v1"
            or complete.get("kind") != "preparation-complete" or complete.get("status") != "complete"):
        raise SupportError("support_preparation_receipt_invalid")
    intent_digest = complete.get("intent_sha256")
    _safe_sha(intent_digest if isinstance(intent_digest, str) else "", HEX64, "support_preparation_receipt_invalid")
    intent = host.read_receipt(intent_digest)
    if (intent.get("schema") != "pyp-app-preflight-support-v1"
            or intent.get("kind") != "preparation-intent" or intent.get("status") != "pending"
            or intent.get("operation_id") != complete.get("operation_id")):
        raise SupportError("support_preparation_receipt_invalid")
    fingerprint = intent.get("support_fingerprint")
    _safe_sha(fingerprint if isinstance(fingerprint, str) else "", HEX64,
              "support_preparation_receipt_invalid")
    if _digest(intent.get("snapshot")) != fingerprint:
        raise SupportError("support_preparation_receipt_invalid")
    names = intent.get("backup_names")
    if not isinstance(names, dict) or set(names) != set(TARGETS):
        raise SupportError("support_preparation_receipt_invalid")
    for name in TARGETS:
        filename = names.get(name)
        if filename is not None and (not isinstance(filename, str)
                or not re.fullmatch(r"preflight-support-prepare-[0-9a-f]{32}-[a-z]+", filename)):
            raise SupportError("support_preparation_receipt_invalid")
    return complete, intent


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise SupportError("support_arguments_invalid")


def _validate_mode_arguments(args: argparse.Namespace) -> None:
    approval = args.approval_fingerprint
    receipt = args.receipt_sha256
    if args.mode == "support-inventory":
        if approval or receipt:
            raise SupportError("support_arguments_invalid")
        return
    if args.mode == "prepare-support":
        if not approval or receipt:
            raise SupportError("support_arguments_invalid")
        _safe_sha(approval, HEX64, "support_fingerprint_invalid")
        return
    if args.mode == "repair-support-backups-mode":
        if not approval or receipt:
            raise SupportError("support_arguments_invalid")
        _safe_sha(approval, HEX64, "support_fingerprint_invalid")
        return
    if args.mode == "restore-support-inventory":
        if approval or not receipt:
            raise SupportError("support_arguments_invalid")
        _safe_sha(receipt, HEX64, "support_receipt_invalid")
        return
    if args.mode == "restore-support":
        if not approval or not receipt:
            raise SupportError("support_arguments_invalid")
        _safe_sha(approval, HEX64, "support_fingerprint_invalid")
        _safe_sha(receipt, HEX64, "support_receipt_invalid")
        return
    if args.mode == "backup-retirement-inventory":
        if approval or receipt:
            raise SupportError("support_arguments_invalid")
        return
    if args.mode == "retire-backup-runtime":
        if not approval or receipt:
            raise SupportError("support_arguments_invalid")
        _safe_sha(approval, HEX64, "support_fingerprint_invalid")
        return
    raise SupportError("support_arguments_invalid")


def _format_directory_diagnostics(value: Any) -> str:
    if (not isinstance(value, (list, tuple)) or not value
            or any(not isinstance(item, str) or item not in SUPPORT_DIRECTORY_DIAGNOSTICS for item in value)
            or len(set(value)) != len(value)):
        raise SupportError("support_directory_diagnostics_invalid")
    return ",".join(value)


def main(argv: list[str] | None = None) -> int:
    try:
        parser = SafeArgumentParser(add_help=False, allow_abbrev=False)
        parser.add_argument("--mode", required=True, choices=sorted(VALID_MODES))
        parser.add_argument("--support-sha", required=True)
        parser.add_argument("--connection-binding", required=True)
        parser.add_argument("--approval-fingerprint", default="")
        parser.add_argument("--receipt-sha256", default="")
        args = parser.parse_args(argv)
        _safe_sha(args.support_sha, HEX40, "support_sha_invalid")
        _safe_sha(args.connection_binding, HEX64, "support_connection_invalid")
        _validate_mode_arguments(args)
        host = LocalSupportHost()
        coordinator = SupportCoordinator(host)
        if args.mode == "support-inventory":
            fingerprint, snapshot = coordinator.inventory(args.support_sha, args.connection_binding)
            state_diagnostics = _format_directory_diagnostics(snapshot["state_directory_diagnostics"])
            backup_diagnostics = _format_directory_diagnostics(snapshot["backup_directory_diagnostics"])
            print("support_inventory=success")
            print(f"support_sha={args.support_sha}")
            print(f"support_state_directory={snapshot['state_directory_state']}")
            print(f"support_state_directory_diagnostics={state_diagnostics}")
            print(f"support_backup_directory={snapshot['backup_directory_state']}")
            print(f"support_backup_directory_diagnostics={backup_diagnostics}")
            print(f"support_fingerprint={fingerprint}")
            return 0
        if args.mode == "prepare-support":
            digest = coordinator.prepare(args.support_sha, args.connection_binding, args.approval_fingerprint)
            print("support_preparation=success")
            print(f"support_receipt_sha256={digest}")
            return 0
        if args.mode == "repair-support-backups-mode":
            coordinator.repair_backup_directory_mode(
                args.support_sha, args.connection_binding, args.approval_fingerprint,
            )
            print("support_backup_mode_repair=success")
            return 0
        if args.mode == "restore-support-inventory":
            fingerprint, view = coordinator.restore_inventory(
                args.support_sha, args.connection_binding, args.receipt_sha256,
            )
            snapshot = view["snapshot"]
            state_diagnostics = _format_directory_diagnostics(snapshot["state_directory_diagnostics"])
            backup_diagnostics = _format_directory_diagnostics(snapshot["backup_directory_diagnostics"])
            print("support_restore_inventory=success")
            print(f"support_receipt_sha256={args.receipt_sha256}")
            print(f"support_state_directory={snapshot['state_directory_state']}")
            print(f"support_state_directory_diagnostics={state_diagnostics}")
            print(f"support_backup_directory={snapshot['backup_directory_state']}")
            print(f"support_backup_directory_diagnostics={backup_diagnostics}")
            print(f"support_fingerprint={fingerprint}")
            return 0
        if args.mode == "backup-retirement-inventory":
            fingerprint, snapshot = coordinator.backup_retirement_inventory(
                args.support_sha, args.connection_binding,
            )
            print("backup_retirement_inventory=success")
            for name in ("runtime", "config", "state"):
                print(f"backup_{name}={'present' if snapshot[name]['present'] else 'absent'}")
            for name, value in snapshot["state_summary"].items():
                print(f"backup_local_{name}={value}")
            for name, state in snapshot["units"].items():
                unit = "service" if name.endswith(".service") else "timer"
                print(f"backup_{unit}={state['active']},{state['enabled']}")
            print(f"backup_picker_config={'present' if snapshot['picker_config']['present'] else 'absent'}")
            print(f"backup_picker_mount={snapshot['picker_mount']}")
            for index, mount in enumerate(snapshot["picker_mount_details"], start=1):
                print(f"backup_picker_mount_{index}_container={mount['container']}")
                print(f"backup_picker_mount_{index}_source={mount['source']}")
                print(f"backup_picker_mount_{index}_target={mount['target']}")
                print(f"backup_picker_mount_{index}_service={mount['service']}")
                print(f"backup_picker_mount_{index}_compose_files={mount['compose_files']}")
            for name, state in snapshot["health"].items():
                print(f"health_{name}={state}")
            print(f"backup_install_incomplete={'yes' if snapshot['incomplete_install'] else 'no'}")
            print(f"backup_retirement_fingerprint={fingerprint}")
            return 0
        if args.mode == "retire-backup-runtime":
            digest = coordinator.retire_backup_runtime(
                args.support_sha, args.connection_binding, args.approval_fingerprint,
            )
            print("backup_retirement=success")
            print(f"backup_retirement_receipt_sha256={digest}")
            return 0
        digest = coordinator.restore(args.support_sha, args.connection_binding, args.approval_fingerprint,
                                     args.receipt_sha256)
        print("support_restore=success")
        print(f"support_restore_receipt_sha256={digest}")
        return 0
    except SupportError as exc:
        print(f"support_error={exc.code}")
        return 1
    except BaseException as exc:  # noqa: BLE001 - CLI output must never expose an unhandled exception.
        print(f"support_error={_internal_error_code(exc)}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
