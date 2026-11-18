#!/usr/bin/env python3
"""Safely remove the retired Gemma monitor fragment from the production overlay."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import fcntl
    import pwd
except ImportError:  # Pure transformation tests also run on Windows.
    fcntl = None  # type: ignore[assignment]
    pwd = None  # type: ignore[assignment]


PROJECT_ROOT = Path("/opt/markina-gallery")
STATE_DIR = Path("/var/lib/markina-gallery/deploy-state")
OVERLAY = STATE_DIR / "system-monitor.compose.yml"
SERVICE_NAME = "face-gemma-index-worker"
EXPECTED_HOST = "clearbudget-vnic"
EXPECTED_CHECKOUT_SHA = "bfe511f850224823254b0fc9f51fa7ff60ecfba0"
EXPECTED_OVERLAY_SHA256 = "c63599b84764f6141cf9860ce1a352f6e11eae55ea4c24b75959ca277c3cd60e"
EXPECTED_OVERLAY_SIZE = 653
EXPECTED_FILE_MODE = 0o600
EXPECTED_STATE_DIR_MODE = 0o700

COMPOSE_FILES = (
    "docker/docker-compose.yml",
    "/var/lib/markina-gallery/deploy-state/branding.compose.yml",
    "docker/docker-compose.preview-adjustment.yml",
    "docker/docker-compose.system-monitor.yml",
)
COMPOSE_PROFILES = ("facial", "preview-adjustment")
RETIRED_SERVICE_HEADER = b"  face-gemma-index-worker:"


class OperationError(RuntimeError):
    """A stable, sanitized operation failure."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def remove_retired_service_block(source: bytes) -> bytes:
    """Remove only the known monitor-only service mapping, preserving other bytes."""
    lines = source.splitlines(keepends=True)
    offsets = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)

    matches = [
        index
        for index, line in enumerate(lines)
        if line.rstrip(b"\r\n").rstrip(b" \t") == RETIRED_SERVICE_HEADER
    ]
    if len(matches) != 1:
        raise OperationError("service_declaration_count_mismatch")
    header_index = matches[0]
    if not any(line.rstrip(b"\r\n") == b"services:" for line in lines[:header_index]):
        raise OperationError("service_declaration_outside_services")

    boundary = len(lines)
    for index in range(header_index + 1, len(lines)):
        line = lines[index]
        if re.match(rb"^[A-Za-z0-9_.-]+:", line) or (
            line.startswith(b"  ")
            and not line.startswith(b"    ")
            and re.match(rb"^  [A-Za-z0-9_.-]+:", line)
        ):
            boundary = index
            break

    direct_keys: list[bytes] = []
    nested_keys: list[bytes] = []
    last_content_index = header_index
    for index in range(header_index + 1, boundary):
        line = lines[index]
        if not line.strip():
            continue
        match = re.match(rb"^( *)([A-Za-z0-9_.-]+):(?:[ \t].*|[ \t]*\r?\n|$)", line)
        if match is None:
            raise OperationError("service_block_shape_mismatch")
        indent = len(match.group(1))
        key = match.group(2)
        if indent == 4:
            direct_keys.append(key)
        elif indent == 6:
            nested_keys.append(key)
        else:
            raise OperationError("service_block_indentation_mismatch")
        last_content_index = index

    if direct_keys != [b"environment"] or nested_keys != [b"SYSTEM_MONITOR_ENABLED"]:
        raise OperationError("service_block_keys_mismatch")

    end = offsets[last_content_index] + len(lines[last_content_index])
    candidate = source[: offsets[header_index]] + source[end:]
    if RETIRED_SERVICE_HEADER in candidate:
        raise OperationError("service_declaration_remains")
    return candidate


def run_capture(
    command: list[str],
    *,
    cwd: Path | None = None,
    failure_code: str = "read_only_precondition_failed",
) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            check=True,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise OperationError(failure_code) from exc
    return result.stdout.strip()


def parse_container_snapshot(output: str, expected_ids: list[str]) -> tuple[str, ...]:
    lines = output.splitlines()
    expected_set = set(expected_ids)
    if len(lines) != len(expected_ids) or len(expected_set) != len(expected_ids):
        raise OperationError("project_container_snapshot_unreadable")
    snapshot: list[str] = []
    seen_ids: set[str] = set()
    for line in lines:
        container_id, separator, state_json = line.partition(" ")
        if (
            not separator
            or not container_id
            or not state_json
            or container_id not in expected_set
            or container_id in seen_ids
        ):
            raise OperationError("project_container_snapshot_unreadable")
        try:
            state = json.loads(state_json)
        except (TypeError, ValueError) as exc:
            raise OperationError("project_container_snapshot_unreadable") from exc
        if not isinstance(state, dict):
            raise OperationError("project_container_snapshot_unreadable")
        status = state.get("Status")
        if not isinstance(status, str) or not status:
            raise OperationError("project_container_snapshot_unreadable")
        health = state.get("Health")
        if health is None:
            health_status = "none"
        elif isinstance(health, dict) and isinstance(health.get("Status"), str) and health["Status"]:
            health_status = health["Status"]
        else:
            raise OperationError("project_container_snapshot_unreadable")
        snapshot.append(f"{container_id} {status} {health_status}")
        seen_ids.add(container_id)
    if seen_ids != expected_set:
        raise OperationError("project_container_snapshot_unreadable")
    return tuple(sorted(snapshot))


def project_container_snapshot() -> tuple[str, ...]:
    command = ["docker", "ps"]
    command.append("-a")
    command.extend(
        [
            "-q",
            "--no-trunc",
            "--filter",
            "label=com.docker.compose.project=markina-gallery",
        ]
    )
    ids = run_capture(command, failure_code="project_container_snapshot_failed").splitlines()
    if not ids:
        return ()
    output = run_capture(
        [
            "docker",
            "inspect",
            "--format",
            "{{.Id}} {{json .State}}",
            *ids,
        ],
        failure_code="project_container_snapshot_failed",
    )
    return parse_container_snapshot(output, ids)


def gemma_container_ids(*, all_states: bool = False) -> tuple[str, ...]:
    command = ["docker", "ps"]
    if all_states:
        command.append("-a")
    command.extend(
        [
            "-q",
            "--filter",
            "label=com.docker.compose.project=markina-gallery",
            "--filter",
            f"label=com.docker.compose.service={SERVICE_NAME}",
        ]
    )
    output = run_capture(command)
    return tuple(sorted(line for line in output.splitlines() if line))


def active_api_version() -> str:
    ids = run_capture(
        [
            "docker",
            "ps",
            "-q",
            "--filter",
            "label=com.docker.compose.project=markina-gallery",
            "--filter",
            "label=com.docker.compose.service=api",
        ]
    ).splitlines()
    if len(ids) != 1 or not ids[0]:
        raise OperationError("active_api_identity_mismatch")
    env_json = run_capture(["docker", "inspect", "--format", "{{json .Config.Env}}", ids[0]])
    try:
        env_values = json.loads(env_json)
        versions = [value.split("=", 1)[1] for value in env_values if value.startswith("APP_VERSION=")]
    except (TypeError, ValueError, AttributeError) as exc:
        raise OperationError("active_api_version_unreadable") from exc
    if versions != [EXPECTED_CHECKOUT_SHA]:
        raise OperationError("active_api_version_mismatch")
    if "APP_ENV=production" not in env_values:
        raise OperationError("active_api_environment_not_production")
    if "FACIAL_PROCESSING_ENABLED=true" not in env_values:
        raise OperationError("facial_processing_flag_not_true")
    health = run_capture(
        [
            "docker",
            "inspect",
            "--format",
            "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
            ids[0],
        ]
    )
    if health != "healthy":
        raise OperationError("active_api_not_healthy")
    return versions[0]


def compose_config(overlay: Path, app_version: str) -> None:
    command = ["docker", "compose", "--env-file", "docker/.env.homolog", "-p", "markina-gallery"]
    for compose_file in COMPOSE_FILES:
        command.extend(["-f", compose_file])
    command.extend(["-f", str(overlay)])
    for profile in COMPOSE_PROFILES:
        command.extend(["--profile", profile])
    command.extend(["config", "--quiet"])
    env = os.environ.copy()
    env["APP_VERSION"] = app_version
    try:
        result = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError as exc:
        raise OperationError("compose_validation_unavailable") from exc
    if result.returncode != 0:
        raise OperationError("compose_validation_failed")


def atomic_write(path: Path, data: bytes, uid: int, gid: int, mode: int) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        os.fchown(fd, uid, gid)
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
        dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def create_backup(path: Path, source: bytes, uid: int, gid: int) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.pre-gemma-reconcile-{stamp}.bak")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(backup, flags, EXPECTED_FILE_MODE)
    try:
        os.fchown(fd, uid, gid)
        os.fchmod(fd, EXPECTED_FILE_MODE)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(source)
            stream.flush()
            os.fsync(stream.fileno())
        if sha256(backup.read_bytes()) != EXPECTED_OVERLAY_SHA256:
            raise OperationError("backup_checksum_mismatch")
        return backup
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            backup.unlink()
        except FileNotFoundError:
            pass
        raise


def verify_file_identity(path: Path) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise OperationError("overlay_unreadable") from exc
    if not stat.S_ISREG(info.st_mode):
        raise OperationError("overlay_not_regular_file")
    if pwd is None:
        raise OperationError("linux_required")
    account = pwd.getpwnam("ubuntu")
    if (info.st_uid, info.st_gid) != (account.pw_uid, account.pw_gid):
        raise OperationError("overlay_owner_mismatch")
    if stat.S_IMODE(info.st_mode) != EXPECTED_FILE_MODE:
        raise OperationError("overlay_mode_mismatch")
    try:
        if os.listxattr(path, follow_symlinks=False):
            raise OperationError("overlay_extended_attributes_present")
    except (OSError, NotImplementedError) as exc:
        raise OperationError("overlay_metadata_unreadable") from exc
    return info


def verify_runtime_and_repository(expected_main_sha: str, lock_fd: int) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    if fcntl is None or pwd is None or not hasattr(os, "uname"):
        raise OperationError("linux_required")
    if os.uname().nodename != EXPECTED_HOST:
        raise OperationError("host_mismatch")
    if Path.cwd().resolve() != PROJECT_ROOT:
        raise OperationError("project_root_mismatch")
    if PROJECT_ROOT.is_symlink() or STATE_DIR.is_symlink() or not STATE_DIR.is_dir():
        raise OperationError("state_directory_mismatch")
    state_info = STATE_DIR.lstat()
    account = pwd.getpwnam("ubuntu")
    if (state_info.st_uid, state_info.st_gid) != (account.pw_uid, account.pw_gid):
        raise OperationError("state_directory_owner_mismatch")
    if stat.S_IMODE(state_info.st_mode) != EXPECTED_STATE_DIR_MODE:
        raise OperationError("state_directory_mode_mismatch")

    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    if not re.fullmatch(r"[0-9a-f]{40}", expected_main_sha):
        raise OperationError("target_sha_invalid")
    checkout_sha = run_capture(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT)
    if checkout_sha != EXPECTED_CHECKOUT_SHA:
        raise OperationError("checkout_sha_mismatch")
    if run_capture(["git", "status", "--porcelain"], cwd=PROJECT_ROOT):
        raise OperationError("checkout_dirty")
    origin = run_capture(["git", "remote", "get-url", "origin"], cwd=PROJECT_ROOT)
    if origin not in {
        "https://github.com/conradodeita/markina-gallery",
        "https://github.com/conradodeita/markina-gallery.git",
        "git@github.com:conradodeita/markina-gallery.git",
    }:
        raise OperationError("repository_origin_mismatch")
    remote_line = run_capture(["git", "ls-remote", "origin", "refs/heads/main"], cwd=PROJECT_ROOT)
    remote_sha = remote_line.split()[0] if remote_line else ""
    if remote_sha != expected_main_sha:
        raise OperationError("remote_main_ref_mismatch")
    run_capture(
        ["git", "fetch", "--no-tags", "origin", "refs/heads/main:refs/remotes/origin/main"],
        cwd=PROJECT_ROOT,
    )
    if run_capture(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT) != checkout_sha:
        raise OperationError("checkout_changed_during_ref_prep")
    if run_capture(["git", "status", "--porcelain"], cwd=PROJECT_ROOT):
        raise OperationError("checkout_dirty_after_ref_prep")
    if run_capture(["git", "rev-parse", "origin/main"], cwd=PROJECT_ROOT) != expected_main_sha:
        raise OperationError("local_main_ref_mismatch")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", checkout_sha, expected_main_sha],
        cwd=str(PROJECT_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    markers = (
        "app-in-flight.sha",
        "app-rollback-in-flight.sha",
        "web-in-flight.sha",
        "web-pending.identity",
    )
    if any((STATE_DIR / marker).exists() for marker in markers):
        raise OperationError("release_marker_present")
    if not os.path.isfile(STATE_DIR / "production-release.lock") or os.path.islink(
        STATE_DIR / "production-release.lock"
    ):
        raise OperationError("release_lock_missing")
    project_ids = project_container_snapshot()
    gemma_running = gemma_container_ids()
    gemma_all_states = gemma_container_ids(all_states=True)
    if gemma_running or len(gemma_all_states) != 1:
        raise OperationError("retired_worker_runtime_changed")
    api_version = active_api_version()
    return api_version, project_ids, gemma_all_states


def apply_reconciliation(expected_main_sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_main_sha):
        raise OperationError("target_sha_invalid")
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    os.environ["GIT_NO_LAZY_FETCH"] = "1"
    os.chdir(PROJECT_ROOT)
    lock_path = STATE_DIR / "production-release.lock"
    if lock_path.is_symlink() or not lock_path.is_file():
        raise OperationError("release_lock_missing")
    lock_fd = os.open(lock_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    backup: Path | None = None
    temp_candidate: Path | None = None
    original: bytes | None = None
    original_stat: os.stat_result | None = None
    try:
        app_version, project_before, gemma_all_before = verify_runtime_and_repository(
            expected_main_sha, lock_fd
        )
        original_stat = verify_file_identity(OVERLAY)
        if original_stat.st_size != EXPECTED_OVERLAY_SIZE:
            raise OperationError("overlay_size_mismatch")
        original = OVERLAY.read_bytes()
        if sha256(original) != EXPECTED_OVERLAY_SHA256:
            raise OperationError("overlay_checksum_mismatch")
        candidate = remove_retired_service_block(original)
        updated_sha = sha256(candidate)

        fd, temp_name = tempfile.mkstemp(
            prefix=f".{OVERLAY.stem}.candidate.", suffix=".yml", dir=str(STATE_DIR)
        )
        temp_candidate = Path(temp_name)
        try:
            os.fchown(fd, original_stat.st_uid, original_stat.st_gid)
            os.fchmod(fd, EXPECTED_FILE_MODE)
            with os.fdopen(fd, "wb", closefd=True) as stream:
                stream.write(candidate)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise

        compose_config(temp_candidate, app_version)
        if project_container_snapshot() != project_before:
            raise OperationError("runtime_changed_during_validation")
        if gemma_container_ids() or gemma_container_ids(all_states=True) != gemma_all_before:
            raise OperationError("retired_worker_runtime_changed")
        current_info = verify_file_identity(OVERLAY)
        if sha256(OVERLAY.read_bytes()) != EXPECTED_OVERLAY_SHA256:
            raise OperationError("overlay_changed_before_replace")
        if (current_info.st_uid, current_info.st_gid, stat.S_IMODE(current_info.st_mode)) != (
            original_stat.st_uid,
            original_stat.st_gid,
            EXPECTED_FILE_MODE,
        ):
            raise OperationError("overlay_metadata_changed_before_replace")

        backup = create_backup(OVERLAY, original, original_stat.st_uid, original_stat.st_gid)
        if sha256(backup.read_bytes()) != EXPECTED_OVERLAY_SHA256:
            raise OperationError("backup_checksum_mismatch")
        backup_info = verify_file_identity(backup)
        if stat.S_IMODE(backup_info.st_mode) != EXPECTED_FILE_MODE:
            raise OperationError("backup_mode_mismatch")
        dir_fd = os.open(STATE_DIR, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

        installed = False
        try:
            os.replace(temp_candidate, OVERLAY)
            temp_candidate = None
            installed = True
            dir_fd = os.open(STATE_DIR, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
            new_info = verify_file_identity(OVERLAY)
            if sha256(OVERLAY.read_bytes()) != updated_sha:
                raise OperationError("updated_overlay_checksum_mismatch")
            if new_info.st_size != EXPECTED_OVERLAY_SIZE - (len(original) - len(candidate)):
                raise OperationError("updated_overlay_size_mismatch")
            compose_config(OVERLAY, app_version)
            if project_container_snapshot() != project_before:
                raise OperationError("runtime_changed_after_replace")
            if gemma_container_ids() or gemma_container_ids(all_states=True) != gemma_all_before:
                raise OperationError("retired_worker_runtime_changed")
        except BaseException:
            if installed:
                atomic_write(OVERLAY, original, original_stat.st_uid, original_stat.st_gid, EXPECTED_FILE_MODE)
                if sha256(OVERLAY.read_bytes()) != EXPECTED_OVERLAY_SHA256:
                    raise OperationError("automatic_restore_failed")
            raise

        print("reconciliation=passed")
        print(f"overlay_backup={backup.name}")
        print(f"overlay_original_sha256={EXPECTED_OVERLAY_SHA256}")
        print(f"overlay_backup_sha256={sha256(backup.read_bytes())}")
        print(f"overlay_updated_sha256={updated_sha}")
        print("overlay_owner=ubuntu:ubuntu mode=600")
        print("compose_candidate_validation=passed compose_canonical_validation=passed")
        print("project_containers_all_states=unchanged gemma_running=0 gemma_all_states=1")
    finally:
        if temp_candidate is not None:
            try:
                temp_candidate.unlink()
            except FileNotFoundError:
                pass
        if fcntl is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


class TransformTests(unittest.TestCase):
    def test_container_snapshot_supports_containers_with_and_without_healthchecks(self) -> None:
        output = (
            'bbbb {"Status":"exited","ExitCode":130}\n'
            'aaaa {"Status":"running","Health":{"Status":"healthy"}}\n'
        )
        self.assertEqual(
            parse_container_snapshot(output, ["aaaa", "bbbb"]),
            ("aaaa running healthy", "bbbb exited none"),
        )

    def test_container_snapshot_rejects_invalid_state(self) -> None:
        for output in (
            "container-id not-json",
            'container-id {"ExitCode":0}',
            'container-id {"Status":"running","Health":{}}',
        ):
            with self.subTest(output=output), self.assertRaises(OperationError):
                parse_container_snapshot(output, ["container-id"])

    def test_container_snapshot_rejects_id_mismatch(self) -> None:
        with self.assertRaises(OperationError):
            parse_container_snapshot('other-id {"Status":"running"}', ["expected-id"])

    def test_removes_only_monitor_block_and_preserves_other_bytes(self) -> None:
        source = (
            b"services:\n"
            b"  api:\n    image: api:current\n"
            b"  face-gemma-index-worker:\n"
            b"    environment:\n      SYSTEM_MONITOR_ENABLED: ${MONITOR:-false}\n"
            b"\n  web:\n    image: web:current\n"
        )
        expected = b"services:\n  api:\n    image: api:current\n\n  web:\n    image: web:current\n"
        self.assertEqual(remove_retired_service_block(source), expected)

    def test_rejects_service_with_image_or_build(self) -> None:
        for extra in (b"    image: example\n", b"    build: .\n"):
            with self.subTest(extra=extra), self.assertRaises(OperationError):
                remove_retired_service_block(
                    b"services:\n  face-gemma-index-worker:\n"
                    b"    environment:\n      SYSTEM_MONITOR_ENABLED: true\n"
                    + extra
                )

    def test_rejects_unexpected_monitor_keys(self) -> None:
        source = (
            b"services:\n  face-gemma-index-worker:\n"
            b"    environment:\n      OTHER_SETTING: value\n"
        )
        with self.assertRaises(OperationError):
            remove_retired_service_block(source)

    def test_preserves_later_top_level_compose_sections(self) -> None:
        source = (
            b"services:\n  face-gemma-index-worker:\n"
            b"    environment:\n      SYSTEM_MONITOR_ENABLED: false\n"
            b"\nnetworks:\n  internal: {}\n"
        )
        expected = b"services:\n\nnetworks:\n  internal: {}\n"
        self.assertEqual(remove_retired_service_block(source), expected)

    def test_rejects_missing_or_duplicate_service(self) -> None:
        with self.assertRaises(OperationError):
            remove_retired_service_block(b"services:\n  api:\n    image: api\n")
        duplicate = (
            b"services:\n  face-gemma-index-worker:\n    environment:\n"
            b"      SYSTEM_MONITOR_ENABLED: true\n  face-gemma-index-worker:\n"
            b"    environment:\n      SYSTEM_MONITOR_ENABLED: false\n"
        )
        with self.assertRaises(OperationError):
            remove_retired_service_block(duplicate)

    @unittest.skipUnless(hasattr(os, "fchown"), "requires POSIX ownership operations")
    def test_backup_is_exclusive_private_and_verifiable(self) -> None:
        original = b"synthetic overlay bytes\n"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "overlay.yml"
            target.write_bytes(original)
            info = target.stat()
            fixed_time = dt.datetime(2026, 11, 18, tzinfo=dt.timezone.utc)

            class FixedDateTime(dt.datetime):
                @classmethod
                def now(cls, tz: dt.tzinfo | None = None) -> dt.datetime:
                    return fixed_time

            with patch(__name__ + ".EXPECTED_OVERLAY_SHA256", sha256(original)), patch(
                __name__ + ".dt.datetime", FixedDateTime
            ):
                backup = create_backup(target, original, info.st_uid, info.st_gid)
                with self.assertRaises(FileExistsError):
                    create_backup(target, b"different bytes\n", info.st_uid, info.st_gid)
            backup_info = backup.stat()
            self.assertEqual(backup.read_bytes(), original)
            self.assertEqual(stat.S_IMODE(backup_info.st_mode), 0o600)
            self.assertEqual((backup_info.st_uid, backup_info.st_gid), (info.st_uid, info.st_gid))

    @unittest.skipUnless(hasattr(os, "fchown"), "requires POSIX ownership operations")
    def test_atomic_write_preserves_owner_mode_and_replaces_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "overlay.yml"
            target.write_bytes(b"old\n")
            os.chmod(target, 0o600)
            info = target.stat()
            atomic_write(target, b"new\n", info.st_uid, info.st_gid, 0o600)
            updated = target.stat()
            self.assertEqual(target.read_bytes(), b"new\n")
            self.assertEqual(stat.S_IMODE(updated.st_mode), 0o600)
            self.assertEqual((updated.st_uid, updated.st_gid), (info.st_uid, info.st_gid))
            self.assertEqual(sorted(path.name for path in Path(directory).iterdir()), ["overlay.yml"])


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--self-test", action="store_true")
    action.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-main-sha", default="")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TransformTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    try:
        apply_reconciliation(args.expected_main_sha)
        return 0
    except (OperationError, OSError, subprocess.CalledProcessError) as exc:
        category = str(exc) if isinstance(exc, OperationError) else "operation_failed"
        print(f"reconciliation_failed={category}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
