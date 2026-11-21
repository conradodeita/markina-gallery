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
CONTAINER_NAMES = {
    "api": "markina-gallery-api-1",
    "web": "markina-gallery-web-1",
    "db": "markina-gallery-db-1",
}
CONTAINER_INSPECT = (
    "{{.Id}}|{{.Image}}|{{.State.Status}}|{{.State.Running}}|{{.State.StartedAt}}|"
    "{{index .Config.Labels \"com.docker.compose.project\"}}|"
    "{{index .Config.Labels \"com.docker.compose.service\"}}|"
    "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}"
)
SHARED_CONTAINER_INSPECT = "{{.Id}}|{{.Image}}|{{.State.Status}}|{{.State.StartedAt}}"
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
CONTAINER_ID = re.compile(r"[0-9a-f]{64}\Z")
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
SCHEMA_REVISION = re.compile(r"[A-Za-z0-9_]{1,64}\Z")
CONTAINER_VALIDATION_ERROR_KINDS = frozenset({
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
    f"{role}_{kind}" for role in CONTAINER_NAMES for kind in CONTAINER_VALIDATION_ERROR_KINDS
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
    "container_inspect_failed", "container_inventory_invalid",
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
}) | CONTAINER_VALIDATION_ERROR_CODES


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, check=False, text=True, timeout=20)


def _output(result: subprocess.CompletedProcess[str], code: str) -> str:
    if result.returncode != 0:
        raise InventoryError(code)
    return result.stdout.strip()


def _container_inventory_error(role: str, kind: str) -> InventoryError:
    if role not in CONTAINER_NAMES or kind not in CONTAINER_VALIDATION_ERROR_KINDS:
        return InventoryError("container_inventory_invalid")
    return InventoryError(f"{role}_{kind}")


def _container(name: str, service: str, runner: Runner) -> dict[str, object]:
    raw = _output(runner([
        "/usr/bin/docker", "--host", "unix:///var/run/docker.sock", "container", "inspect",
        "--format", CONTAINER_INSPECT, name,
    ]), "container_inspect_failed")
    parts = raw.split("|")
    if len(parts) != 8:
        raise _container_inventory_error(service, "container_record_shape_invalid")
    identifier, image, state, running, started_at, project, actual_service, health = parts
    if not CONTAINER_ID.fullmatch(identifier):
        raise _container_inventory_error(service, "container_id_invalid")
    if not IMAGE_ID.fullmatch(image):
        raise _container_inventory_error(service, "container_image_id_invalid")
    if project != "markina-gallery":
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


def _unit(name: str, runner: Runner) -> dict[str, str]:
    raw = _output(runner([
        "/usr/bin/systemctl", "show", "--property=LoadState,UnitFileState,ActiveState", "--value", name,
    ]), "systemd_inventory_failed")
    parts = raw.splitlines()
    if len(parts) != 3 or any(len(value) > 32 for value in parts):
        raise InventoryError("systemd_inventory_invalid")
    load, enabled, active = parts
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


def _safe_failure_code(error: BaseException) -> str:
    """Return only a fixed category or allowlisted code, never exception details."""
    if isinstance(error, InventoryError):
        candidate = str(error)
        return candidate if candidate in SAFE_INVENTORY_ERROR_CODES else "inventory_error"
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


def collect_inventory(runner: Runner = _run, *, root: Path = Path("/")) -> dict[str, object]:
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

    shared_containers = _shared_container_snapshot(runner)
    containers = {service: _container(name, service, runner) for service, name in CONTAINER_NAMES.items()}
    schema = _output(runner([
        "/usr/bin/docker", "--host", "unix:///var/run/docker.sock", "exec", "--env",
        "PGOPTIONS=-c default_transaction_read_only=on -c lock_timeout=2000 -c statement_timeout=10000",
        CONTAINER_NAMES["db"], "sh", "-ceu",
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
        "service": _unit("pyp-platform-backup.service", runner),
        "timer": _unit("pyp-platform-backup.timer", runner),
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
    if _shared_container_snapshot(runner) != shared_containers:
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


def main() -> int:
    try:
        result = collect_inventory()
        report = json.dumps(result["inventory"], sort_keys=True, separators=(",", ":"))
        print(f"backup_runtime_inventory={report}")
        print(f"backup_runtime_fingerprint={result['fingerprint']}")
        print(f"backup_runtime_install_preconditions={'pass' if install_preconditions(result['inventory']) else 'fail'}")
        return 0
    except (InventoryError, OSError, subprocess.SubprocessError) as exc:
        print(f"platform-backup-runtime: inventory failed ({_safe_failure_code(exc)})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
