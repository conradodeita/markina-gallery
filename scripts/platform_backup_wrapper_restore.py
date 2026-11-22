#!/usr/bin/env python3
"""Restauracao protegida e fixa do forced command do Pick-your-Pic."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

BACKUP_DIR = Path("/var/backups/markina-gallery")
PROJECT_ROOT = Path("/opt/markina-gallery")
WRAPPER_PATH = Path("/usr/local/sbin/markina-gallery-preflight-ssh-wrapper")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
BACKUP_NAME = re.compile(
    r"^preflight-ssh-wrapper-[0-9]{8}T[0-9]{6}Z-platform-backup-[0-9a-f]{12}$"
)
ALLOWED_DIRECTORY_MODES = {0o700, 0o750, 0o755}
DEFAULT_BASH = shutil.which("bash") or "/bin/bash"
@dataclass(frozen=True)
class RestorePaths:
    backup_dir: Path = BACKUP_DIR
    wrapper: Path = WRAPPER_PATH
    project_root: Path = PROJECT_ROOT


DEFAULT_PATHS = RestorePaths()


class RestoreFailure(Exception):
    """Falha publica com codigo estatico e sanitizado."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _valid_digest(value: str, pattern: re.Pattern[str]) -> bool:
    return pattern.fullmatch(value) is not None


def _checked_stat(
    path: Path,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
    expected_mode: int | None,
    strict_mode: bool,
    directory: bool = False,
    code: str,
) -> os.stat_result:
    try:
        result = path.lstat()
    except OSError as exc:
        raise RestoreFailure(code) from exc
    if stat.S_ISLNK(result.st_mode):
        raise RestoreFailure(code)
    if directory:
        if not stat.S_ISDIR(result.st_mode):
            raise RestoreFailure(code)
    elif not stat.S_ISREG(result.st_mode) or result.st_nlink != 1:
        raise RestoreFailure(code)
    if expected_uid is not None and result.st_uid != expected_uid:
        raise RestoreFailure(code)
    if expected_gid is not None and result.st_gid != expected_gid:
        raise RestoreFailure(code)
    if strict_mode and expected_mode is not None and stat.S_IMODE(result.st_mode) != expected_mode:
        raise RestoreFailure(code)
    if directory and strict_mode and stat.S_IMODE(result.st_mode) not in ALLOWED_DIRECTORY_MODES:
        raise RestoreFailure(code)
    if directory and strict_mode and result.st_mode & 0o022:
        raise RestoreFailure(code)
    return result


def _read_secure(
    path: Path,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
    expected_mode: int,
    strict_mode: bool,
    code: str,
) -> bytes:
    before = _checked_stat(
        path,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=expected_mode,
        strict_mode=strict_mode,
        code=code,
    )
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RestoreFailure(code) from exc
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise RestoreFailure(code)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise RestoreFailure(code)
        if expected_uid is not None and opened.st_uid != expected_uid:
            raise RestoreFailure(code)
        if expected_gid is not None and opened.st_gid != expected_gid:
            raise RestoreFailure(code)
        if strict_mode and stat.S_IMODE(opened.st_mode) != expected_mode:
            raise RestoreFailure(code)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read()
    except OSError as exc:
        raise RestoreFailure(code) from exc
    finally:
        os.close(descriptor)


def _write_new_file(
    path: Path,
    content: bytes,
    *,
    mode: int,
    expected_uid: int | None,
    expected_gid: int | None,
) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags, mode)
        if expected_uid is not None and expected_gid is not None and hasattr(os, "fchown"):
            os.fchown(descriptor, expected_uid, expected_gid)
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(descriptor)
    except OSError as exc:
        raise RestoreFailure("wrapper_restore_write_failed") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(
    path: Path,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
    expected_mode: int,
    strict_mode: bool,
    code: str,
) -> str:
    return _sha256(_read_secure(
        path,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=expected_mode,
        strict_mode=strict_mode,
        code=code,
    ))


def _ensure_directory(
    path: Path,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
    strict_mode: bool,
    code: str,
) -> None:
    _checked_stat(
        path,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=None,
        strict_mode=strict_mode,
        directory=True,
        code=code,
    )


def _select_backup(
    backup_dir: Path,
    requested_sha256: str,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
    strict_mode: bool,
) -> tuple[Path, bytes]:
    _ensure_directory(
        backup_dir,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        strict_mode=strict_mode,
        code="wrapper_restore_backup_directory_invalid",
    )
    matches: list[tuple[Path, bytes]] = []
    try:
        candidates = sorted(backup_dir.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise RestoreFailure("wrapper_restore_copy_not_found") from exc
    for candidate in candidates:
        if not BACKUP_NAME.fullmatch(candidate.name):
            continue
        _checked_stat(
            candidate,
            expected_uid=expected_uid,
            expected_gid=expected_gid,
            expected_mode=0o600,
            strict_mode=strict_mode,
            code="wrapper_restore_copy_metadata_invalid",
        )
        content = _read_secure(
            candidate,
            expected_uid=expected_uid,
            expected_gid=expected_gid,
            expected_mode=0o600,
            strict_mode=strict_mode,
            code="wrapper_restore_copy_metadata_invalid",
        )
        if _sha256(content) == requested_sha256:
            matches.append((candidate, content))
    if not matches:
        raise RestoreFailure("wrapper_restore_copy_not_found")
    if len(matches) != 1:
        raise RestoreFailure("wrapper_restore_copy_ambiguous")
    return matches[0]


def _fingerprint_from_wrapper(wrapper: Path, support_sha: str) -> str:
    original_command = f"SSH_ORIGINAL_COMMAND=MARKINA_APP_TARGET_SHA={support_sha}"
    try:
        result = subprocess.run(
            ["sudo", "-n", "-H", "-u", "ubuntu", "env", original_command,
             DEFAULT_BASH, str(wrapper)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RestoreFailure("wrapper_restore_preflight_failed") from exc
    if result.returncode != 0:
        raise RestoreFailure("wrapper_restore_preflight_failed")
    fingerprints = re.findall(r"^approval_fingerprint=([0-9a-f]{64})$", result.stdout, re.MULTILINE)
    if len(fingerprints) != 1:
        raise RestoreFailure("wrapper_restore_preflight_failed")
    return fingerprints[0]


def _container_snapshot() -> str:
    try:
        docker = ["sudo", "-n", "-H", "-u", "ubuntu", "docker"]
        listed = subprocess.run(
            [*docker, "ps", "-aq", "--no-trunc"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if listed.returncode != 0:
            raise RestoreFailure("wrapper_restore_container_inventory_failed")
        identifiers = sorted(line.strip() for line in listed.stdout.splitlines() if line.strip())
        if not identifiers or any(re.fullmatch(r"[0-9a-f]{64}", item) is None for item in identifiers):
            raise RestoreFailure("wrapper_restore_container_inventory_failed")
        inspected = subprocess.run(
            [*docker, "inspect", "--format",
             "{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.State.Status}}", *identifiers],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RestoreFailure("wrapper_restore_container_inventory_failed") from exc
    if inspected.returncode != 0:
        raise RestoreFailure("wrapper_restore_container_inventory_failed")
    records = sorted(line.strip() for line in inspected.stdout.splitlines() if line.strip())
    reported_ids = sorted(record.split("|", 1)[0] for record in records if "|" in record)
    if len(records) != len(identifiers) or reported_ids != identifiers:
        raise RestoreFailure("wrapper_restore_container_inventory_failed")
    return _sha256(("\n".join(records) + "\n").encode("utf-8"))


def _validate_wrapper(
    path: Path,
    expected_sha256: str,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
    strict_mode: bool,
    expected_mode: int = 0o755,
) -> None:
    content = _read_secure(
        path,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=expected_mode,
        strict_mode=strict_mode,
        code="wrapper_restore_wrapper_identity_invalid",
    )
    if _sha256(content) != expected_sha256:
        raise RestoreFailure("wrapper_restore_wrapper_hash_invalid")
    try:
        syntax = subprocess.run(
            [DEFAULT_BASH, "-n", str(path)],
            capture_output=True,
            check=False,
            timeout=20,
        )
        arbitrary = subprocess.run(
            [
                "sudo",
                "-n",
                "-H",
                "-u",
                "ubuntu",
                "env",
                "SSH_ORIGINAL_COMMAND=id",
                DEFAULT_BASH,
                str(path),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RestoreFailure("wrapper_restore_wrapper_validation_failed") from exc
    if syntax.returncode != 0 or arbitrary.returncode == 0:
        raise RestoreFailure("wrapper_restore_wrapper_validation_failed")


def _default_fingerprint_probe(paths: RestorePaths, support_sha: str) -> str:
    return _fingerprint_from_wrapper(paths.wrapper, support_sha)


def _default_snapshot(_: RestorePaths) -> str:
    return _container_snapshot()


def _default_validator(
    path: Path,
    expected_sha256: str,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
    strict_mode: bool,
    expected_mode: int = 0o755,
) -> None:
    _validate_wrapper(
        path,
        expected_sha256,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        strict_mode=strict_mode,
        expected_mode=expected_mode,
    )


def _copy_to_backup(
    content: bytes,
    name: str,
    paths: RestorePaths,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
    strict_mode: bool,
) -> Path:
    destination = paths.backup_dir / name
    if destination.exists() or destination.is_symlink():
        raise RestoreFailure("wrapper_restore_preserved_copy_collision")
    _write_new_file(
        destination,
        content,
        mode=0o600,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
    )
    try:
        _checked_stat(
            destination,
            expected_uid=expected_uid,
            expected_gid=expected_gid,
            expected_mode=0o600,
            strict_mode=strict_mode,
            code="wrapper_restore_preserved_copy_invalid",
        )
        if _sha256_file(
            destination,
            expected_uid=expected_uid,
            expected_gid=expected_gid,
            expected_mode=0o600,
            strict_mode=strict_mode,
            code="wrapper_restore_preserved_copy_invalid",
        ) != _sha256(content):
            raise RestoreFailure("wrapper_restore_preserved_copy_invalid")
    except Exception:
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return destination


def _create_staging(
    path: Path,
    content: bytes,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
) -> None:
    if path.exists() or path.is_symlink():
        raise RestoreFailure("wrapper_restore_staging_exists")
    _write_new_file(
        path,
        content,
        mode=0o755,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
    )


def _observed_sha256(
    path: Path,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
    strict_mode: bool,
) -> str | None:
    try:
        return _sha256_file(
            path,
            expected_uid=expected_uid,
            expected_gid=expected_gid,
            expected_mode=0o755,
            strict_mode=strict_mode,
            code="wrapper_restore_wrapper_identity_invalid",
        )
    except RestoreFailure:
        return None


def _compensate(
    active_backup: Path,
    active_sha256: str,
    rollback_stage: Path,
    paths: RestorePaths,
    *,
    expected_uid: int | None,
    expected_gid: int | None,
    strict_mode: bool,
    validator: Callable[..., None],
    snapshot: Callable[[RestorePaths], str],
    before_snapshot: str,
    replace: Callable[[Path, Path], None],
) -> None:
    active_content = _read_secure(
        active_backup,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=0o600,
        strict_mode=strict_mode,
        code="wrapper_restore_fallback_unverified",
    )
    _create_staging(
        rollback_stage,
        active_content,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
    )
    replace(rollback_stage, paths.wrapper)
    validator(
        paths.wrapper,
        active_sha256,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        strict_mode=strict_mode,
    )
    if snapshot(paths) != before_snapshot:
        raise RestoreFailure("wrapper_restore_fallback_unverified")


def restore_wrapper(
    receipt_backup_sha256: str,
    support_sha: str,
    approval_fingerprint: str,
    *,
    paths: RestorePaths = DEFAULT_PATHS,
    expected_uid: int | None = 0,
    expected_gid: int | None = 0,
    strict_mode: bool = True,
    fingerprint_probe: Callable[[RestorePaths, str], str] = _default_fingerprint_probe,
    container_snapshot: Callable[[RestorePaths], str] = _default_snapshot,
    wrapper_validator: Callable[..., None] = _default_validator,
    atomic_replace: Callable[[Path, Path], None] = os.replace,
    utc_stamp: str | None = None,
) -> tuple[str, str]:
    if not _valid_digest(receipt_backup_sha256, HEX64) or not _valid_digest(support_sha, HEX40):
        raise RestoreFailure("wrapper_restore_invalid_identity")
    if not _valid_digest(approval_fingerprint, HEX64):
        raise RestoreFailure("wrapper_restore_invalid_fingerprint")
    _ensure_directory(
        paths.wrapper.parent,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        strict_mode=strict_mode,
        code="wrapper_restore_wrapper_directory_invalid",
    )
    active_content = _read_secure(
        paths.wrapper,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=0o755,
        strict_mode=strict_mode,
        code="wrapper_restore_active_wrapper_invalid",
    )
    active_sha256 = _sha256(active_content)
    wrapper_validator(
        paths.wrapper,
        active_sha256,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        strict_mode=strict_mode,
    )
    if fingerprint_probe(paths, support_sha) != approval_fingerprint:
        raise RestoreFailure("wrapper_restore_fingerprint_mismatch")
    before_snapshot = container_snapshot(paths)
    target_path, target_content = _select_backup(
        paths.backup_dir,
        receipt_backup_sha256,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        strict_mode=strict_mode,
    )
    target_sha256 = _sha256(target_content)
    if target_sha256 == active_sha256:
        raise RestoreFailure("wrapper_restore_already_active")
    wrapper_validator(
        target_path,
        target_sha256,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        strict_mode=strict_mode,
        expected_mode=0o600,
    )

    stamp = utc_stamp or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    if re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", stamp) is None:
        raise RestoreFailure("wrapper_restore_invalid_timestamp")
    restore_key = f"{support_sha}.{receipt_backup_sha256[:12]}"
    staging = paths.wrapper.parent / f".{paths.wrapper.name}.{restore_key}.restore.new"
    rollback_stage = paths.wrapper.parent / f".{paths.wrapper.name}.{restore_key}.restore.rollback"
    if any(path.exists() or path.is_symlink() for path in (staging, rollback_stage)):
        raise RestoreFailure("wrapper_restore_staging_exists")

    active_backup_name = f"preflight-ssh-wrapper-{stamp}-platform-backup-{support_sha[:12]}"
    active_backup = _copy_to_backup(
        active_content,
        active_backup_name,
        paths,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        strict_mode=strict_mode,
    )
    _create_staging(
        staging,
        target_content,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
    )
    try:
        wrapper_validator(
            staging,
            target_sha256,
            expected_uid=expected_uid,
            expected_gid=expected_gid,
            strict_mode=strict_mode,
        )
    except Exception:
        try:
            staging.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    swap_error: Exception | None = None
    try:
        atomic_replace(staging, paths.wrapper)
    except OSError as exc:  # An atomic rename may report failure after changing the target.
        swap_error = exc
    observed = _observed_sha256(
        paths.wrapper,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        strict_mode=strict_mode,
    )
    if observed == active_sha256:
        try:
            staging.unlink(missing_ok=True)
        except OSError:
            pass
        if swap_error is not None:
            raise RestoreFailure("wrapper_restore_atomic_swap_failed") from swap_error
        raise RestoreFailure("wrapper_restore_target_not_active")
    if observed != target_sha256:
        try:
            _compensate(
                active_backup,
                active_sha256,
                rollback_stage,
                paths,
                expected_uid=expected_uid,
                expected_gid=expected_gid,
                strict_mode=strict_mode,
                validator=wrapper_validator,
                snapshot=container_snapshot,
                before_snapshot=before_snapshot,
                replace=atomic_replace,
            )
        except Exception as rollback_exc:
            raise RestoreFailure("wrapper_restore_fallback_unverified") from rollback_exc
        raise RestoreFailure("wrapper_restore_validation_failed_recovered") from swap_error

    try:
        wrapper_validator(
            paths.wrapper,
            target_sha256,
            expected_uid=expected_uid,
            expected_gid=expected_gid,
            strict_mode=strict_mode,
        )
        if container_snapshot(paths) != before_snapshot:
            raise RestoreFailure("wrapper_restore_post_swap_validation_failed")
    except Exception as exc:
        try:
            _compensate(
                active_backup,
                active_sha256,
                rollback_stage,
                paths,
                expected_uid=expected_uid,
                expected_gid=expected_gid,
                strict_mode=strict_mode,
                validator=wrapper_validator,
                snapshot=container_snapshot,
                before_snapshot=before_snapshot,
                replace=atomic_replace,
            )
        except Exception as rollback_exc:
            raise RestoreFailure("wrapper_restore_fallback_unverified") from rollback_exc
        raise RestoreFailure("wrapper_restore_validation_failed_recovered") from exc

    return target_sha256, _sha256(active_content)


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--support-sha", required=True)
    parser.add_argument("--receipt-backup-sha256", required=True)
    parser.add_argument("--approval-fingerprint", required=True)
    try:
        arguments = parser.parse_args(argv)
        restored_sha, preserved_sha = restore_wrapper(
            arguments.receipt_backup_sha256,
            arguments.support_sha,
            arguments.approval_fingerprint,
        )
    except RestoreFailure as exc:
        print(f"wrapper_restore_error={exc.code}", file=sys.stderr)
        if exc.code == "wrapper_restore_fallback_unverified":
            print("wrapper_active=unverified", file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001 - keep protected-operation diagnostics static and sanitized
        print("wrapper_restore_error=wrapper_restore_io_or_command_failed", file=sys.stderr)
        return 1
    print("wrapper_restore=success")
    print(f"wrapper_sha256={restored_sha}")
    print(f"previous_wrapper_backup_sha256={preserved_sha}")
    print("application_and_shared_containers_unchanged=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
