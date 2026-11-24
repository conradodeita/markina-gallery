"""Read-only, sanitized inventory for the protected backup-runtime workflow."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import stat
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

PROJECT_ROOT = Path("/opt/markina-gallery")
INSTALL_ROOT = Path("/opt/pyp-backup-runtime")
CONFIG_ROOT = Path("/etc/pyp-backup")
PICKER_CONFIG = Path("/etc/pyp-google-drive/picker-config.json")
CONTAINER_ROLES = ("api", "web", "db")
APP_SERVICES = ("api", "web")
APP_COMPOSE_BRIDGE = "/usr/local/sbin/markina-gallery-app-compose-bridge"
CONTAINER_INSPECT = (
    "{{.Id}}|{{.Image}}|{{.State.Status}}|{{.State.Running}}|{{.State.StartedAt}}|"
    "{{index .Config.Labels \"com.docker.compose.project\"}}|"
    "{{index .Config.Labels \"com.docker.compose.service\"}}|"
    "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}"
)
CONTAINER_DIAGNOSTIC_INSPECT = (
    "{{.Id}}|{{.State.Status}}|"
    "{{index .Config.Labels \"com.docker.compose.project\"}}|"
    "{{index .Config.Labels \"com.docker.compose.service\"}}"
)
SHARED_CONTAINER_INSPECT = "{{.Id}}|{{.Image}}|{{.State.Status}}|{{.State.StartedAt}}"
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
CONTAINER_ID = re.compile(r"[0-9a-f]{64}\Z")
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
SCHEMA_REVISION = re.compile(r"[A-Za-z0-9_]{1,64}\Z")
ACTIVE_APP_PROJECT = re.compile(r"(?:markina-gallery|markina-gallery-app-[0-9a-f]{32})\Z")
CONTAINER_VALIDATION_ERROR_KINDS = frozenset({
    "container_record_missing",
    "container_record_ambiguous",
    "container_record_shape_invalid",
    "container_id_invalid",
    "container_image_id_invalid",
    "container_project_label_mismatch",
    "container_service_label_mismatch",
    "container_running_flag_invalid",
    "container_state_invalid",
    "container_health_state_invalid",
    "container_started_at_invalid",
})
CONTAINER_VALIDATION_ERROR_CODES = frozenset(
    f"{role}_{kind}" for role in CONTAINER_ROLES for kind in CONTAINER_VALIDATION_ERROR_KINDS
)
ACTIVE_COMPOSE_ERROR_KINDS = frozenset({
    "active_project_resolution_failed",
    "active_project_invalid",
    "active_container_resolution_failed",
    "active_container_id_invalid",
})
ACTIVE_COMPOSE_ERROR_CODES = frozenset(
    f"{role}_{kind}" for role in APP_SERVICES for kind in ACTIVE_COMPOSE_ERROR_KINDS
)


class InventoryError(ValueError):
    """Inventory could not establish a trustworthy fixed host snapshot."""


# Only these stable internal codes may appear in operational logs. Command output,
# exception text, paths and remote configuration contents are never forwarded.
SAFE_INVENTORY_ERROR_CODES = frozenset({
    "host_identity_unavailable", "host_identity_invalid",
    "checkout_identity_unavailable", "checkout_identity_invalid",
    "shared_container_list_failed", "shared_container_list_empty", "shared_container_list_invalid",
    "shared_container_inspect_failed", "shared_container_inventory_invalid",
    "container_service_list_failed", "container_inspect_failed", "container_inventory_invalid",
    "schema_inventory_failed", "schema_inventory_invalid",
    "disk_inventory_failed", "disk_inventory_invalid",
    "systemd_inventory_failed", "systemd_inventory_invalid",
    "installed_release_identity_invalid", "installed_release_root_unsafe",
    "installed_release_file_unavailable", "installed_release_file_unsafe",
    "installed_release_file_changed", "installed_release_current_mismatch",
    "installed_release_directory_unsafe", "installed_release_receipt_invalid",
    "installed_release_manifest_invalid", "installed_release_receipt_mismatch",
    "installed_release_rollback_unsafe", "installed_release_rollback_mismatch",
    "inventory_changed_during_scan",
    "active_compose_bridge_identity_invalid",
}) | CONTAINER_VALIDATION_ERROR_CODES | ACTIVE_COMPOSE_ERROR_CODES
SAFE_DIAGNOSTIC_ERROR_CODES = frozenset({
    "diagnostic_container_list_failed", "diagnostic_container_list_invalid",
    "diagnostic_container_inspect_failed", "diagnostic_container_inventory_invalid",
    "diagnostic_compose_list_failed", "diagnostic_compose_list_invalid",
    "diagnostic_inventory_changed",
    "inventory_error", "inventory_command_failed", "inventory_io_failed",
})


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    timeout = 60 if argv and argv[0] == APP_COMPOSE_BRIDGE else 20
    return subprocess.run(argv, capture_output=True, check=False, text=True, timeout=timeout)


def _output(result: subprocess.CompletedProcess[str], code: str) -> str:
    if result.returncode != 0:
        raise InventoryError(code)
    return result.stdout.strip()


def _container_inventory_error(role: str, kind: str) -> InventoryError:
    if role not in CONTAINER_ROLES or kind not in CONTAINER_VALIDATION_ERROR_KINDS:
        return InventoryError("container_inventory_invalid")
    return InventoryError(f"{role}_{kind}")


def _active_app_error(service: str, kind: str) -> InventoryError:
    if service not in APP_SERVICES or kind not in ACTIVE_COMPOSE_ERROR_KINDS:
        return InventoryError("container_inventory_invalid")
    return InventoryError(f"{service}_{kind}")


def _single_bridge_value(
    result: subprocess.CompletedProcess[str],
    failure_code: str,
    invalid_code: str,
) -> str:
    if result.returncode != 0:
        raise InventoryError(failure_code)
    if len(result.stdout) > 1024:
        raise InventoryError(invalid_code)
    value = result.stdout.strip()
    if not value or len(value.splitlines()) != 1:
        raise InventoryError(invalid_code)
    return value


def _active_app_identity(service: str, bridge_sha: str, runner: Runner) -> dict[str, str]:
    """Resolve one API/web identity through the installed, root-only app bridge."""
    if (service not in APP_SERVICES or not isinstance(bridge_sha, str)
            or not GIT_SHA.fullmatch(bridge_sha)):
        raise InventoryError("container_inventory_invalid")
    prefix = [APP_COMPOSE_BRIDGE, "--mode", "inventory", "--sha", bridge_sha]
    project = _single_bridge_value(
        runner([*prefix, "service-project", "--", service]),
        f"{service}_active_project_resolution_failed",
        f"{service}_active_project_invalid",
    )
    if not ACTIVE_APP_PROJECT.fullmatch(project):
        raise _active_app_error(service, "active_project_invalid")
    identifier = _single_bridge_value(
        runner([*prefix, "compose", "--", "ps", "-q", service]),
        f"{service}_active_container_resolution_failed",
        f"{service}_active_container_id_invalid",
    )
    if not CONTAINER_ID.fullmatch(identifier):
        raise _active_app_error(service, "active_container_id_invalid")
    return {"project": project, "id": identifier}


def _verify_app_compose_bridge(bridge_sha: str, runner: Runner) -> None:
    if not isinstance(bridge_sha, str) or not GIT_SHA.fullmatch(bridge_sha):
        raise InventoryError("active_compose_bridge_identity_invalid")
    metadata = _output(runner([
        "/usr/bin/stat", "--format=%F|%u|%g|%a|%h", "--", APP_COMPOSE_BRIDGE,
    ]), "active_compose_bridge_identity_invalid")
    if metadata != "regular file|0|0|755|1":
        raise InventoryError("active_compose_bridge_identity_invalid")
    expected_blob = _output(runner([
        "/usr/bin/git", "-C", str(PROJECT_ROOT), "rev-parse",
        f"{bridge_sha}:scripts/production_app_compose_bridge.py",
    ]), "active_compose_bridge_identity_invalid")
    installed_blob = _output(runner([
        "/usr/bin/git", "hash-object", "--", APP_COMPOSE_BRIDGE,
    ]), "active_compose_bridge_identity_invalid")
    if (not re.fullmatch(r"[0-9a-f]{40}", expected_blob)
            or not re.fullmatch(r"[0-9a-f]{40}", installed_blob)
            or installed_blob != expected_blob):
        raise InventoryError("active_compose_bridge_identity_invalid")


def _active_app_snapshot(bridge_sha: str, runner: Runner) -> dict[str, dict[str, str]]:
    _verify_app_compose_bridge(bridge_sha, runner)
    identities = {
        service: _active_app_identity(service, bridge_sha, runner)
        for service in APP_SERVICES
    }
    if identities["api"]["id"] == identities["web"]["id"]:
        raise _active_app_error("api", "active_container_id_invalid")
    return identities


def _container(
    service: str,
    runner: Runner,
    *,
    active_identity: dict[str, str] | None = None,
) -> dict[str, object]:
    if service not in CONTAINER_ROLES:
        raise InventoryError("container_inventory_invalid")
    if service in APP_SERVICES:
        if (not isinstance(active_identity, dict)
                or set(active_identity) != {"project", "id"}
                or not isinstance(active_identity["project"], str)
                or not ACTIVE_APP_PROJECT.fullmatch(active_identity["project"])
                or not isinstance(active_identity["id"], str)
                or not CONTAINER_ID.fullmatch(active_identity["id"])):
            raise _container_inventory_error(service, "container_inventory_invalid")
        expected_project = active_identity["project"]
        identifier = active_identity["id"]
    else:
        raw_ids = _output(runner([
            "/usr/bin/docker", "--host", "unix:///var/run/docker.sock", "container", "ls",
            "--all", "--no-trunc", "--quiet",
            "--filter", "label=com.docker.compose.project=markina-gallery",
            "--filter", f"label=com.docker.compose.service={service}",
        ]), "container_service_list_failed")
        ids = raw_ids.splitlines() if raw_ids else []
        if not ids:
            raise _container_inventory_error(service, "container_record_missing")
        if len(ids) != 1:
            raise _container_inventory_error(service, "container_record_ambiguous")
        identifier = ids[0]
        if not CONTAINER_ID.fullmatch(identifier):
            raise _container_inventory_error(service, "container_id_invalid")
        expected_project = "markina-gallery"
    raw = _output(runner([
        "/usr/bin/docker", "--host", "unix:///var/run/docker.sock", "container", "inspect",
        "--format", CONTAINER_INSPECT, identifier,
    ]), "container_inspect_failed")
    parts = raw.split("|")
    if len(parts) != 8:
        raise _container_inventory_error(service, "container_record_shape_invalid")
    inspected_identifier, image, state, running, started_at, project, actual_service, health = parts
    if not CONTAINER_ID.fullmatch(inspected_identifier) or inspected_identifier != identifier:
        raise _container_inventory_error(service, "container_id_invalid")
    if not IMAGE_ID.fullmatch(image):
        raise _container_inventory_error(service, "container_image_id_invalid")
    if project != expected_project:
        raise _container_inventory_error(service, "container_project_label_mismatch")
    if actual_service != service:
        raise _container_inventory_error(service, "container_service_label_mismatch")
    if running not in {"true", "false"}:
        raise _container_inventory_error(service, "container_running_flag_invalid")
    if state not in {"running", "exited", "created", "restarting"}:
        raise _container_inventory_error(service, "container_state_invalid")
    if health not in {"healthy", "unhealthy", "starting", "none"}:
        raise _container_inventory_error(service, "container_health_state_invalid")
    if len(started_at) > 64:
        raise _container_inventory_error(service, "container_started_at_invalid")
    return {
        "id": identifier,
        "image": image,
        "state": state,
        "running": running == "true",
        "started_at": started_at,
        "health": health,
    }


def _diagnostic_container_ids(service: str, runner: Runner, *, compose: bool) -> set[str]:
    if service not in CONTAINER_ROLES:
        raise InventoryError("diagnostic_container_inventory_invalid")
    if compose:
        command = [
            "/usr/bin/docker", "--host", "unix:///var/run/docker.sock", "compose",
            "--project-name", "markina-gallery",
            "--project-directory", "/opt/markina-gallery/docker",
            "--file", "/opt/markina-gallery/docker/docker-compose.yml",
            "ps", "--all", "--quiet", "--no-trunc", "--orphans=false", service,
        ]
        error_code = "diagnostic_compose_list_failed"
        invalid_code = "diagnostic_compose_list_invalid"
    else:
        command = [
            "/usr/bin/docker", "--host", "unix:///var/run/docker.sock", "container", "ls",
            "--all", "--no-trunc", "--quiet",
            "--filter", "label=com.docker.compose.project=markina-gallery",
            "--filter", f"label=com.docker.compose.service={service}",
        ]
        error_code = "diagnostic_container_list_failed"
        invalid_code = "diagnostic_container_list_invalid"
    raw_ids = _output(runner(command), error_code)
    if len(raw_ids) > 512 * 65:
        raise InventoryError(invalid_code)
    identifiers = raw_ids.splitlines() if raw_ids else []
    if (len(identifiers) > 512 or len(identifiers) != len(set(identifiers))
            or any(not CONTAINER_ID.fullmatch(value) for value in identifiers)):
        raise InventoryError(invalid_code)
    return set(identifiers)


def _container_diagnostic(service: str, runner: Runner) -> dict[str, int]:
    label_identifiers = _diagnostic_container_ids(service, runner, compose=False)
    compose_identifiers = _diagnostic_container_ids(service, runner, compose=True)

    counts = {"running": 0, "stopped": 0, "unknown": 0}
    if label_identifiers:
        raw = _output(runner([
            "/usr/bin/docker", "--host", "unix:///var/run/docker.sock", "container", "inspect",
            "--format", CONTAINER_DIAGNOSTIC_INSPECT, *sorted(label_identifiers),
        ]), "diagnostic_container_inspect_failed")
        rows = raw.splitlines()
        if len(rows) != len(label_identifiers):
            raise InventoryError("diagnostic_container_inventory_invalid")

        expected_ids = label_identifiers
        inspected_ids: set[str] = set()
        for row in rows:
            parts = row.split("|")
            if len(parts) != 4:
                raise InventoryError("diagnostic_container_inventory_invalid")
            identifier, state, project, actual_service = parts
            if (not CONTAINER_ID.fullmatch(identifier) or identifier not in expected_ids
                    or identifier in inspected_ids or project != "markina-gallery"
                    or actual_service != service):
                raise InventoryError("diagnostic_container_inventory_invalid")
            inspected_ids.add(identifier)
            if state == "running":
                category = "running"
            elif state in {"created", "exited", "dead"}:
                category = "stopped"
            else:
                category = "unknown"
            counts[category] += 1
        if inspected_ids != expected_ids:
            raise InventoryError("diagnostic_container_inventory_invalid")

    if (_diagnostic_container_ids(service, runner, compose=False) != label_identifiers
            or _diagnostic_container_ids(service, runner, compose=True) != compose_identifiers):
        raise InventoryError("diagnostic_inventory_changed")

    matched_ids = label_identifiers & compose_identifiers
    return {
        "label_records": len(label_identifiers),
        "compose_records": len(compose_identifiers),
        "matched_records": len(matched_ids),
        "label_only_records": len(label_identifiers - compose_identifiers),
        "compose_only_records": len(compose_identifiers - label_identifiers),
        **counts,
    }


def collect_container_diagnostics(runner: Runner = _run) -> dict[str, object]:
    """Return only fixed-role aggregate counts; never disclose container records."""
    return {
        "schema_version": 2,
        "roles": {service: _container_diagnostic(service, runner) for service in CONTAINER_ROLES},
    }


def read_systemd_unit_state(name: str, runner: Runner) -> dict[str, str]:
    """Read one unit's fixed properties without relying on output order."""
    properties = ("LoadState", "UnitFileState", "ActiveState")
    raw = _output(runner([
        "/usr/bin/systemctl", "show", "--all", f"--property={','.join(properties)}", name,
    ]), "systemd_inventory_failed")
    values: dict[str, str] = {}
    for line in raw.splitlines():
        key, separator, value = line.partition("=")
        if not separator or key not in properties or key in values:
            raise InventoryError("systemd_inventory_invalid")
        values[key] = value
    if len(values) != len(properties):
        raise InventoryError("systemd_inventory_invalid")
    load, enabled, active = (values[key] for key in properties)
    allowed_load = {"loaded", "not-found", "error"}
    allowed_enabled = {"enabled", "disabled", "static", "indirect", "masked", "generated", "transient", "unknown", ""}
    allowed_active = {"active", "inactive", "failed", "activating", "deactivating", "unknown", ""}
    if load not in allowed_load or enabled not in allowed_enabled or active not in allowed_active:
        raise InventoryError("systemd_inventory_invalid")
    return {"load": load, "enabled": enabled or "unknown", "active": active or "unknown"}


def _shared_container_snapshot(runner: Runner) -> dict[str, object]:
    raw_ids = _output(runner([
        "/usr/bin/docker", "--host", "unix:///var/run/docker.sock", "container", "ls",
        "--all", "--no-trunc", "--quiet",
    ]), "shared_container_list_failed")
    ids = raw_ids.splitlines() if raw_ids else []
    if len(ids) > 512 or len(ids) != len(set(ids)) or any(not CONTAINER_ID.fullmatch(value) for value in ids):
        raise InventoryError("shared_container_list_invalid")
    if not ids:
        raise InventoryError("shared_container_list_empty")
    raw = _output(runner([
        "/usr/bin/docker", "--host", "unix:///var/run/docker.sock", "container", "inspect",
        "--format", SHARED_CONTAINER_INSPECT, *ids,
    ]), "shared_container_inspect_failed")
    rows = raw.splitlines()
    if len(rows) != len(ids):
        raise InventoryError("shared_container_inventory_invalid")
    canonical = []
    for row in rows:
        parts = row.split("|")
        if (len(parts) != 4 or not CONTAINER_ID.fullmatch(parts[0])
                or not IMAGE_ID.fullmatch(parts[1])
                or parts[2] not in {"running", "exited", "created", "restarting", "paused", "dead"}
                or len(parts[3]) > 64 or any(ord(character) < 32 for character in parts[3])):
            raise InventoryError("shared_container_inventory_invalid")
        canonical.append("|".join(parts))
    if {row.split("|", 1)[0] for row in canonical} != set(ids):
        raise InventoryError("shared_container_inventory_invalid")
    digest = hashlib.sha256("\n".join(sorted(canonical)).encode("ascii")).hexdigest()
    return {"count": len(ids), "fingerprint": digest}


def _file_metadata(path: Path) -> dict[str, object]:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"present": False}
    if stat.S_ISLNK(info.st_mode):
        target = os.readlink(path) if path.name == "current" else "not_disclosed"
        if path.name == "current" and not re.fullmatch(r"releases/[0-9a-f]{40}", target):
            target = "invalid"
        return {"present": True, "kind": "symlink", "target": target,
                "uid": info.st_uid, "gid": info.st_gid, "links": info.st_nlink}
    return {
        "present": True,
        "kind": "regular" if stat.S_ISREG(info.st_mode) else "directory" if stat.S_ISDIR(info.st_mode) else "other",
        "uid": info.st_uid,
        "gid": info.st_gid,
        "mode": stat.S_IMODE(info.st_mode),
        "links": info.st_nlink,
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
    }


def _path_metadata(paths: dict[str, Path]) -> dict[str, object]:
    return {name: _file_metadata(path) for name, path in paths.items()}


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_failure_code(
    error: BaseException, allowed_codes: frozenset[str] = SAFE_INVENTORY_ERROR_CODES,
) -> str:
    """Return only a fixed category or allowlisted code, never exception details."""
    if isinstance(error, InventoryError):
        candidate = str(error)
        return candidate if candidate in allowed_codes else "inventory_error"
    if isinstance(error, subprocess.SubprocessError):
        return "inventory_command_failed"
    if isinstance(error, OSError):
        return "inventory_io_failed"
    return "inventory_failed"


def _read_root_file(path: Path, *, mode: int, max_size: int) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                             | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        raise InventoryError("installed_release_file_unavailable") from None
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_gid != 0
                or stat.S_IMODE(before.st_mode) != mode or before.st_nlink != 1
                or not 0 < before.st_size <= max_size):
            raise InventoryError("installed_release_file_unsafe")
        chunks = bytearray()
        while len(chunks) <= before.st_size:
            block = os.read(descriptor, min(4096, before.st_size + 1 - len(chunks)))
            if not block:
                break
            chunks.extend(block)
        after = os.fstat(descriptor)
        if (len(chunks) != before.st_size or
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise InventoryError("installed_release_file_changed")
        return bytes(chunks)
    finally:
        os.close(descriptor)


def verify_installed_release(source_sha: str, bundle_sha256: str,
                             install_root: Path = INSTALL_ROOT) -> dict[str, object]:
    if not GIT_SHA.fullmatch(source_sha) or not re.fullmatch(r"[0-9a-f]{64}", bundle_sha256):
        raise InventoryError("installed_release_identity_invalid")
    root_info = install_root.lstat()
    if (not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode)
            or root_info.st_uid != 0 or root_info.st_gid != 0 or stat.S_IMODE(root_info.st_mode) != 0o700):
        raise InventoryError("installed_release_root_unsafe")
    target = install_root / "current"
    target_info = target.lstat()
    if (not stat.S_ISLNK(target_info.st_mode) or target_info.st_uid != 0 or target_info.st_gid != 0
            or target_info.st_nlink != 1
            or os.readlink(target) != f"releases/{source_sha}"):
        raise InventoryError("installed_release_current_mismatch")
    release = install_root / f"releases/{source_sha}"
    release_info = release.lstat()
    if (not stat.S_ISDIR(release_info.st_mode) or stat.S_ISLNK(release_info.st_mode)
            or release_info.st_uid != 0 or release_info.st_gid != 0
            or stat.S_IMODE(release_info.st_mode) != 0o700):
        raise InventoryError("installed_release_directory_unsafe")
    try:
        manifest = json.loads(_read_root_file(release / "manifest.json", mode=0o400, max_size=2_000_000))
        receipt = json.loads(_read_root_file(release / "install-receipt.json", mode=0o600, max_size=16_384))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise InventoryError("installed_release_receipt_invalid") from None
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
            or manifest.get("source_sha") != source_sha
            or not isinstance(manifest.get("files"), list)):
        raise InventoryError("installed_release_manifest_invalid")
    expected = {
        "schema_version": 1,
        "status": "installed_inert",
        "source_sha": source_sha,
        "bundle_sha256": bundle_sha256,
        "current_release": f"releases/{source_sha}",
        "service_enabled": False,
        "service_active": False,
        "timer_enabled": False,
        "timer_active": False,
        "destination_enabled": False,
    }
    if (not isinstance(receipt, dict) or any(receipt.get(key) != value for key, value in expected.items())
            or not isinstance(receipt.get("approval_fingerprint"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", receipt["approval_fingerprint"])
            or not isinstance(receipt.get("rollback_receipt_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", receipt["rollback_receipt_sha256"])):
        raise InventoryError("installed_release_receipt_mismatch")
    previous = receipt.get("previous_release")
    if previous is not None and not re.fullmatch(r"releases/[0-9a-f]{40}", str(previous)):
        raise InventoryError("installed_release_receipt_mismatch")
    rollback_root = install_root / "rollback"
    rollback_info = rollback_root.lstat()
    if (not stat.S_ISDIR(rollback_info.st_mode) or stat.S_ISLNK(rollback_info.st_mode)
            or rollback_info.st_uid != 0 or rollback_info.st_gid != 0
            or stat.S_IMODE(rollback_info.st_mode) != 0o700):
        raise InventoryError("installed_release_rollback_unsafe")
    rollback = _read_root_file(
        rollback_root / f"{source_sha}.json", mode=0o600, max_size=16_384,
    )
    if hashlib.sha256(rollback).hexdigest() != receipt["rollback_receipt_sha256"]:
        raise InventoryError("installed_release_rollback_mismatch")
    return {"source_sha": source_sha, "bundle_sha256": bundle_sha256, "status": "installed_inert"}


def _opaque_configuration_binding(path: Path, machine_id: str) -> str:
    """Bind protected config bytes into the fingerprint without returning their hashes."""
    try:
        parent = path.parent.lstat()
    except FileNotFoundError:
        return "absent"
    if (not stat.S_ISDIR(parent.st_mode) or stat.S_ISLNK(parent.st_mode)
            or parent.st_uid != 0 or parent.st_gid != 0 or stat.S_IMODE(parent.st_mode) != 0o700):
        return "unsafe"
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                             | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return "absent"
    except OSError:
        return "unreadable"
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_gid != 0
                or stat.S_IMODE(before.st_mode) != 0o400 or before.st_nlink != 1
                or not 0 < before.st_size <= 16_384):
            return "unsafe"
        chunks = bytearray()
        while len(chunks) <= before.st_size:
            block = os.read(descriptor, min(4096, before.st_size + 1 - len(chunks)))
            if not block:
                break
            chunks.extend(block)
        after = os.fstat(descriptor)
        if (len(chunks) != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            return "changed"
        return hmac.new(machine_id.lower().encode("ascii"), bytes(chunks), hashlib.sha256).hexdigest()
    finally:
        os.close(descriptor)


def collect_inventory(
    runner: Runner = _run,
    *,
    root: Path = Path("/"),
    bridge_sha: str | None = None,
) -> dict[str, object]:
    """Observe only fixed application, backup and Picker paths; never read their contents."""
    try:
        machine_id = (root / "etc/machine-id").read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise InventoryError("host_identity_unavailable") from exc
    if not re.fullmatch(r"[0-9a-fA-F-]{16,64}", machine_id):
        raise InventoryError("host_identity_invalid")
    checkout_sha = _output(runner([
        "/usr/bin/git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD",
    ]), "checkout_identity_unavailable")
    if not GIT_SHA.fullmatch(checkout_sha):
        raise InventoryError("checkout_identity_invalid")
    bridge_sha = checkout_sha if bridge_sha is None else bridge_sha
    if not GIT_SHA.fullmatch(bridge_sha):
        raise InventoryError("active_compose_bridge_identity_invalid")

    shared_containers = _shared_container_snapshot(runner)
    active_app = _active_app_snapshot(bridge_sha, runner)
    containers = {
        service: _container(service, runner, active_identity=active_app.get(service))
        for service in CONTAINER_ROLES
    }
    schema = _output(runner([
        "/usr/bin/docker", "--host", "unix:///var/run/docker.sock", "exec", "--env",
        "PGOPTIONS=-c default_transaction_read_only=on -c lock_timeout=2000 -c statement_timeout=10000",
        str(containers["db"]["id"]), "sh", "-ceu",
        ('exec psql -X -Atq -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
         '-c "SELECT version_num FROM public.alembic_version"'),
    ]), "schema_inventory_failed")
    if not SCHEMA_REVISION.fullmatch(schema):
        raise InventoryError("schema_inventory_invalid")
    disk = _output(runner(["/usr/bin/df", "-P", "-k", "/var/lib"]), "disk_inventory_failed")
    disk_lines = disk.splitlines()
    if len(disk_lines) != 2:
        raise InventoryError("disk_inventory_invalid")
    disk_parts = disk_lines[1].split()
    if (len(disk_parts) < 6 or not all(value.isdigit() for value in disk_parts[1:4])
            or not re.fullmatch(r"[0-9]{1,3}%", disk_parts[4])):
        raise InventoryError("disk_inventory_invalid")
    disk_info = {"total_kib": int(disk_parts[1]), "used_kib": int(disk_parts[2]),
                 "available_kib": int(disk_parts[3]), "use_percent": int(disk_parts[4][:-1])}
    units = {
        "service": read_systemd_unit_state("pyp-platform-backup.service", runner),
        "timer": read_systemd_unit_state("pyp-platform-backup.timer", runner),
    }
    config_paths = {
        "config_directory": root / "etc/pyp-backup",
        "source": root / "etc/pyp-backup/source.json",
        "keyring": root / "etc/pyp-backup/keyring.json",
        "destination": root / "etc/pyp-backup/destination.json",
        "picker_config_directory": root / "etc/pyp-google-drive",
        "picker_config": root / "etc/pyp-google-drive/picker-config.json",
        "install_root": root / "opt/pyp-backup-runtime",
        "release_directory": root / "opt/pyp-backup-runtime/releases",
        "current_release": root / "opt/pyp-backup-runtime/current",
    }
    configs = _path_metadata(config_paths)
    host_binding = hashlib.sha256(machine_id.lower().encode("ascii")).hexdigest()
    sensitive_bindings = {
        name: _opaque_configuration_binding(path, machine_id)
        for name, path in config_paths.items()
        if name in {"source", "keyring", "destination", "picker_config"}
    }
    if (_active_app_snapshot(bridge_sha, runner) != active_app
            or _shared_container_snapshot(runner) != shared_containers):
        raise InventoryError("inventory_changed_during_scan")
    inventory: dict[str, object] = {
        "schema_version": 1,
        "checkout_sha": checkout_sha,
        "containers": containers,
        "shared_containers": shared_containers,
        "database_schema": schema,
        "disk_var_lib": disk_info,
        "units": units,
        "paths": configs,
    }
    runtime_hash = _digest({
        "host_binding": host_binding,
        "checkout_sha": checkout_sha,
        "containers": containers,
        "shared_containers": shared_containers,
        "database_schema": schema,
        "sensitive_configuration_bindings": sensitive_bindings,
    })
    inventory_hash = hashlib.sha256(json.dumps(
        {"host_binding": host_binding, "inventory": inventory,
         "sensitive_configuration_bindings": sensitive_bindings},
        sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    return {"inventory": inventory, "fingerprint": inventory_hash,
            "runtime_fingerprint": runtime_hash}


def install_preconditions(inventory: dict[str, object]) -> bool:
    """Return whether current state is safe for inert installation; no mutation occurs."""
    try:
        items = inventory["containers"]
        units = inventory["units"]
        paths = inventory["paths"]
        if not all(items[name]["running"] for name in ("api", "web", "db")):
            return False
        if any(items[name]["health"] != "healthy" for name in ("api", "web")):
            return False
        for state in units.values():
            if state["active"] != "inactive":
                return False
            if (state["load"] == "loaded" and state["enabled"] not in {"disabled", "static"}
                    or state["load"] == "not-found" and state["enabled"] != "unknown"
                    or state["load"] not in {"loaded", "not-found"}):
                return False
        for name in ("config_directory", "picker_config_directory"):
            info = paths[name]
            if info["present"] and (info.get("kind") != "directory" or info.get("uid") != 0
                                    or info.get("gid") != 0 or info.get("mode") != 0o700):
                return False
        for name in ("source", "keyring", "destination", "picker_config"):
            info = paths[name]
            if info["present"] and (info.get("kind") != "regular" or info.get("uid") != 0
                                    or info.get("gid") != 0 or info.get("mode") != 0o400
                                    or info.get("links") != 1):
                return False
        for name in ("install_root", "release_directory"):
            info = paths[name]
            if info["present"] and (info.get("kind") != "directory" or info.get("uid") != 0
                                    or info.get("gid") != 0 or info.get("mode") != 0o700):
                return False
        current = paths["current_release"]
        if current["present"] and (current.get("kind") != "symlink" or current.get("uid") != 0
                                    or current.get("gid") != 0 or current.get("links") != 1
                                    or not re.fullmatch(r"releases/[0-9a-f]{40}", str(current.get("target", "")))):
            return False
        return inventory["database_schema"] != ""
    except (KeyError, TypeError):
        return False


def public_inventory_summary(inventory: dict[str, object]) -> dict[str, object]:
    """Expose fixed operational facts without container or protected-file identities."""
    containers = inventory["containers"]
    units = inventory["units"]
    disk = inventory["disk_var_lib"]
    return {
        "schema_version": 1,
        "checkout_sha": inventory["checkout_sha"],
        "containers": {
            service: {
                "state": containers[service]["state"],
                "running": containers[service]["running"],
                "health": containers[service]["health"],
            }
            for service in CONTAINER_ROLES
        },
        "database_schema": inventory["database_schema"],
        "disk_var_lib": {
            "available_kib": disk["available_kib"],
            "use_percent": disk["use_percent"],
        },
        "units": {
            name: {"load": units[name]["load"], "enabled": units[name]["enabled"],
                  "active": units[name]["active"]}
            for name in ("service", "timer")
        },
    }


def diagnostic_main() -> int:
    try:
        result = collect_container_diagnostics()
        report = json.dumps(result, sort_keys=True, separators=(",", ":"))
        print(f"backup_runtime_container_diagnostics={report}")
        return 0
    except (InventoryError, OSError, subprocess.SubprocessError) as exc:
        print(f"platform-backup-runtime: container diagnostics failed "
              f"({_safe_failure_code(exc, SAFE_DIAGNOSTIC_ERROR_CODES)})")
        return 1


def main(bridge_sha: str | None = None) -> int:
    try:
        result = collect_inventory(bridge_sha=bridge_sha)
        report = json.dumps(public_inventory_summary(result["inventory"]),
                            sort_keys=True, separators=(",", ":"))
        print(f"backup_runtime_inventory_summary={report}")
        print(f"backup_runtime_fingerprint={result['fingerprint']}")
        print(f"backup_runtime_install_preconditions={'pass' if install_preconditions(result['inventory']) else 'fail'}")
        return 0
    except (InventoryError, OSError, subprocess.SubprocessError) as exc:
        print(f"platform-backup-runtime: inventory failed ({_safe_failure_code(exc)})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
