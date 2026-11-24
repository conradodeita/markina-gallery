#!/usr/bin/env python3
"""Fixed, receipt-backed preparation and restoration of app preflight support.

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
import re
import socket
import stat
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

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
VALID_MODES = {"support-inventory", "prepare-support", "restore-support-inventory", "restore-support"}
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
        if kind not in {"preparation-intent", "preparation-complete", "restoration-intent", "restoration-complete"}:
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
                    r"preflight-support-(?:preparation|restoration)-(?:intent|complete)-[0-9a-f]{32}\.json",
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
