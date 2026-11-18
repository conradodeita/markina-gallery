#!/usr/bin/python3 -I
"""Root-owned, allowlisted Compose bridge for the production API/web release."""
from __future__ import annotations

import argparse
import copy
import decimal
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterable
from pathlib import Path

PROJECT = "markina-gallery"
PROJECT_ROOT = Path("/opt/markina-gallery")
WORKING_DIR = PROJECT_ROOT / "docker"
STATE_DIR = Path("/var/lib/markina-gallery/deploy-state")
ENV_FILE = WORKING_DIR / ".env.homolog"
MARKINA_STATE_ROOT = Path("/var/lib/markina-gallery")
BRIDGE_STATE = MARKINA_STATE_ROOT / "app-compose-bridge"
SERVICES = ("api", "web")
PROFILES = ("facial", "preview-adjustment")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^([0-9]{8}_[0-9]{4})(?:\s+.*)?$")
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024
MAX_COMMAND_OUTPUT_BYTES = 8 * 1024 * 1024
SAFE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Every accepted Compose service field has an explicit comparison or is a
# build/orchestration field that never participates in a --no-deps recreation.
MODEL_FIELDS = frozenset({
    "image", "build", "container_name", "profiles", "depends_on", "pull_policy",
    "environment", "command", "entrypoint", "user", "working_dir", "healthcheck", "labels",
    "volumes", "networks", "expose", "ports", "restart", "stop_grace_period", "stop_signal",
    "read_only", "cap_drop", "cap_add", "security_opt", "privileged", "devices",
    "mem_limit", "mem_reservation", "cpus", "pids_limit", "init", "tmpfs", "ulimits",
    "dns", "extra_hosts", "logging", "network_mode", "ipc", "pid", "runtime",
    "stdin_open", "tty", "hostname", "domainname", "shm_size",
})


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def environment_map(values) -> dict[str, str]:
    if isinstance(values, dict):
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
            raise BridgeError("environment_contract_invalid")
        return dict(values)
    if not isinstance(values, list):
        raise BridgeError("environment_contract_invalid")
    result = {}
    for entry in values:
        if not isinstance(entry, str) or "=" not in entry:
            raise BridgeError("environment_contract_invalid")
        key, value = entry.split("=", 1)
        if not key or key in result:
            raise BridgeError("environment_contract_ambiguous")
        result[key] = value
    return result


def duration_ns(value) -> int:
    if value in (None, 0, "0"):
        return 0
    if not isinstance(value, str) or not re.fullmatch(r"(?:[0-9]+(?:\.[0-9]+)?(?:h|ms|us|ns|m|s))+", value):
        raise BridgeError("duration_contract_invalid")
    scales = {"h": 3600000000000, "m": 60000000000, "s": 1000000000,
              "ms": 1000000, "us": 1000, "ns": 1}
    return int(sum(decimal.Decimal(number) * scales[unit]
                   for number, unit in re.findall(r"([0-9]+(?:\.[0-9]+)?)(ms|us|ns|h|m|s)", value)))


def _equal(actual, expected, category: str) -> None:
    if actual != expected:
        raise BridgeError("semantic_mismatch_" + category)


def prove_service_model(service: str, model: dict, document: dict, item: dict, image: dict) -> str:
    """Fail closed on an unexplained effective Docker/Compose difference.

    Values remain in root memory. Only stable category codes and a digest leave.
    This digest is a semantic identity, never a fabricated Compose config-hash.
    """
    if service not in SERVICES or not isinstance(model, dict) or set(model) - MODEL_FIELDS:
        raise BridgeError("semantic_service_field_unsupported")
    config, host = item.get("Config", {}), item.get("HostConfig", {})
    defaults = image.get("Config", {})
    _equal(image.get("Id"), item.get("Image"), "image")
    expected_env = {**environment_map(defaults.get("Env") or []),
                    **environment_map(model.get("environment") or {})}
    _equal(environment_map(config.get("Env") or []), expected_env, "environment")
    for field, docker_field in (("command", "Cmd"), ("entrypoint", "Entrypoint"),
                                ("user", "User"), ("working_dir", "WorkingDir")):
        expected = model.get(field, defaults.get(docker_field))
        if field in {"command", "entrypoint"} and isinstance(expected, str):
            raise BridgeError("semantic_command_string_unsupported")
        if expected == [] and field in {"command", "entrypoint"}:
            expected = None
        actual = config.get(docker_field)
        if actual == [] and field in {"command", "entrypoint"}:
            actual = None
        _equal(actual, expected, field)
    expected_labels = {**(defaults.get("Labels") or {}), **(model.get("labels") or {})}
    application_labels = lambda values: {k: v for k, v in values.items() if not k.startswith("com.docker.compose.")}
    _equal(application_labels(config.get("Labels") or {}), application_labels(expected_labels), "labels")
    health = dict(defaults.get("Healthcheck") or {})
    spec_health = model.get("healthcheck") or {}
    if set(spec_health) - {"test", "interval", "timeout", "retries", "start_period", "start_interval", "disable"}:
        raise BridgeError("semantic_healthcheck_field_unsupported")
    for field, docker_field in (("test", "Test"), ("interval", "Interval"), ("timeout", "Timeout"),
                                ("start_period", "StartPeriod"), ("start_interval", "StartInterval"),
                                ("retries", "Retries")):
        if field in spec_health:
            health[docker_field] = duration_ns(spec_health[field]) if field not in {"test", "retries"} else spec_health[field]
    if spec_health.get("disable"):
        health = {"Test": ["NONE"]}
    normalized_health = lambda values: {k: v for k, v in (values or {}).items() if v not in (None, 0)}
    _equal(normalized_health(config.get("Healthcheck")), normalized_health(health), "healthcheck")

    expected_mounts = []
    for mount in model.get("volumes") or []:
        if not isinstance(mount, dict) or set(mount) - {"type", "source", "target", "read_only", "bind", "volume", "consistency"}:
            raise BridgeError("semantic_mount_field_unsupported")
        kind, source, target = mount.get("type"), mount.get("source"), mount.get("target")
        bind_options, volume_options = mount.get("bind") or {}, mount.get("volume") or {}
        if (set(bind_options) - {"propagation", "create_host_path"} or set(volume_options) - {"nocopy"}
                or mount.get("consistency") not in (None, "", "consistent")):
            raise BridgeError("semantic_mount_option_unsupported")
        if kind == "volume":
            definition = (document.get("volumes") or {}).get(source)
            if not isinstance(definition, dict) or not isinstance(definition.get("name"), str):
                raise BridgeError("semantic_volume_name_unproven")
            source = definition["name"]
            actual_options = next((entry.get("VolumeOptions") or {} for entry in host.get("Mounts") or []
                                   if entry.get("Target") == target), {})
            if set(actual_options) - {"NoCopy", "Labels", "DriverConfig"} or actual_options.get("Labels") or actual_options.get("DriverConfig"):
                raise BridgeError("semantic_volume_option_unsupported")
            _equal(bool(actual_options.get("NoCopy")), bool(volume_options.get("nocopy")), "volume_nocopy")
        elif kind != "bind":
            raise BridgeError("semantic_mount_type_unsupported")
        expected_mounts.append((kind, source, target, not bool(mount.get("read_only")),
                                (mount.get("bind") or {}).get("propagation", "rprivate") if kind == "bind" else ""))
    actual_mounts = [(m.get("Type"), m.get("Name") if m.get("Type") == "volume" else m.get("Source"),
                      m.get("Destination"), m.get("RW"), m.get("Propagation", "")) for m in item.get("Mounts", [])]
    _equal(sorted(actual_mounts), sorted(expected_mounts), "mounts")
    expected_networks = {}
    for name, options in (model.get("networks") or {}).items():
        definition = (document.get("networks") or {}).get(name)
        if not isinstance(definition, dict) or not isinstance(definition.get("name"), str):
            raise BridgeError("semantic_network_name_unproven")
        if options and set(options) - {"aliases", "priority", "gw_priority"}:
            raise BridgeError("semantic_network_option_unsupported")
        expected_networks[definition["name"]] = options or {}
    actual_networks = item.get("NetworkSettings", {}).get("Networks") or {}
    _equal(set(actual_networks), set(expected_networks), "networks")
    for name, options in expected_networks.items():
        if not set(options.get("aliases") or []).issubset(set(actual_networks[name].get("Aliases") or [])):
            raise BridgeError("semantic_mismatch_network_aliases")
        allowed_aliases = set(options.get("aliases") or []) | {service, item.get("Id", "")[:12],
                           config.get("Hostname", ""), item.get("Name", "").lstrip("/")}
        if set(actual_networks[name].get("Aliases") or []) - allowed_aliases:
            raise BridgeError("semantic_unexplained_network_alias")
        _equal(actual_networks[name].get("GwPriority", 0), options.get("gw_priority", 0), "network_gateway_priority")

    # Defaults reflect the Docker Engine contract; explicit values remain exact.
    for field, docker_field, default in (
        ("mem_limit", "Memory", 0), ("mem_reservation", "MemoryReservation", 0),
        ("read_only", "ReadonlyRootfs", False), ("privileged", "Privileged", False),
        ("pids_limit", "PidsLimit", None), ("init", "Init", None),
        ("pid", "PidMode", ""), ("runtime", "Runtime", "runc"), ("ipc", "IpcMode", "private"),
        ("shm_size", "ShmSize", 67108864)):
        _equal(host.get(docker_field, default), model.get(field, default), field)
    _equal(host.get("NanoCpus", 0), int(decimal.Decimal(str(model.get("cpus", 0))) * 1000000000), "cpus")
    for field, docker_field in (("cap_drop", "CapDrop"), ("cap_add", "CapAdd"),
                                ("security_opt", "SecurityOpt"), ("dns", "Dns"), ("extra_hosts", "ExtraHosts")):
        _equal(sorted(host.get(docker_field) or []), sorted(model.get(field) or []), field)
    restart = model.get("restart") or "no"
    restart_parts = restart.split(":", 1)
    _equal(host.get("RestartPolicy"), {"Name": restart_parts[0], "MaximumRetryCount": int(restart_parts[1]) if len(restart_parts) == 2 else 0}, "restart")
    if model.get("devices") or host.get("Devices") or host.get("DeviceRequests"):
        raise BridgeError("semantic_devices_unsupported")
    if model.get("tmpfs") or host.get("Tmpfs") or model.get("ulimits") or host.get("Ulimits"):
        raise BridgeError("semantic_tmpfs_or_ulimits_unsupported")
    if model.get("ports") or any((host.get("PortBindings") or {}).values()):
        raise BridgeError("semantic_published_ports_not_allowed")
    if model.get("network_mode") or host.get("NetworkMode") not in expected_networks:
        raise BridgeError("semantic_network_mode_unproven")
    if model.get("logging"):
        log = model["logging"]
        _equal(host.get("LogConfig"), {"Type": log.get("driver", "json-file"), "Config": log.get("options") or {}}, "logging")
    elif host.get("LogConfig") != {"Type": "json-file", "Config": {}}:
        raise BridgeError("semantic_logging_default_unproven")
    for name in ("OomKillDisable", "AutoRemove", "VolumesFrom", "Links", "Sysctls", "GroupAdd",
                 "CpuQuota", "CpuPeriod", "CpuShares", "CpusetCpus", "CpusetMems", "BlkioWeight",
                 "CgroupParent", "Cgroup", "CgroupnsMode", "UsernsMode", "UTSMode"):
        value = host.get(name)
        if name == "CgroupnsMode" and value == "private":
            continue
        if value not in (None, False, 0, "", [], {}):
            raise BridgeError("semantic_host_field_unsupported")
    for field, docker_field, default in (("stdin_open", "OpenStdin", False), ("tty", "Tty", False),
                                       ("domainname", "Domainname", "")):
        _equal(config.get(docker_field, default), model.get(field, default), field)
    if "hostname" in model:
        _equal(config.get("Hostname"), model["hostname"], "hostname")
    else:
        _equal(config.get("Hostname"), item.get("Id", "")[:12], "hostname_default")
    expected_exposed = set(defaults.get("ExposedPorts") or {})
    expected_exposed.update(str(port) if "/" in str(port) else str(port) + "/tcp" for port in model.get("expose") or [])
    _equal(set(config.get("ExposedPorts") or {}), expected_exposed, "exposed_ports")
    _equal(config.get("StopSignal", "SIGTERM"), model.get("stop_signal", defaults.get("StopSignal", "SIGTERM")), "stop_signal")
    _equal(config.get("StopTimeout", 10), duration_ns(model["stop_grace_period"]) // 1000000000 if "stop_grace_period" in model else 10, "stop_timeout")
    return digest({"service": service, "model": model, "image": image["Id"]})


def runtime_semantic_identity(item: dict) -> str:
    config, host = item["Config"], item["HostConfig"]
    env = environment_map(config.get("Env") or [])
    env.pop("APP_VERSION", None)
    config_fields = ("Cmd", "Entrypoint", "User", "WorkingDir", "Healthcheck", "ExposedPorts",
                     "StopSignal", "StopTimeout", "OpenStdin", "Tty", "Domainname")
    host_fields = ("RestartPolicy", "Memory", "MemoryReservation", "NanoCpus", "PidsLimit", "Init",
                   "ReadonlyRootfs", "CapDrop", "CapAdd", "SecurityOpt", "Privileged", "Devices", "DeviceRequests",
                   "Runtime", "PidMode", "IpcMode", "NetworkMode", "PortBindings", "Dns", "ExtraHosts", "Ulimits", "Tmpfs", "LogConfig", "ShmSize")
    mounts = [{k: m.get(k) for k in ("Type", "Name", "Source", "Destination", "RW", "Propagation")}
              for m in item.get("Mounts", [])]
    return digest({"environment": env, "config": {k: config.get(k) for k in config_fields},
                   "labels": {k: v for k, v in (config.get("Labels") or {}).items() if not k.startswith("com.docker.compose.")},
                   "host": {k: host.get(k) for k in host_fields}, "mounts": sorted(mounts, key=lambda m: m["Destination"]),
                   "networks": sorted(item.get("NetworkSettings", {}).get("Networks") or {})})


class BridgeError(RuntimeError):
    """A stable, value-free failure that is safe to print to a workflow log."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def require_root(uid: int | None = None, gid: int | None = None) -> None:
    if uid is None:
        uid = getattr(os, "geteuid", lambda: -1)()
    if gid is None:
        gid = getattr(os, "getegid", lambda: -1)()
    if uid != 0 or gid != 0:
        raise BridgeError("root_identity_required")


def validate_snapshot_path(raw_path: str | Path, allowed_roots: Iterable[str | Path]) -> Path:
    text = str(raw_path)
    path = Path(text)
    if not path.is_absolute() or ".." in path.parts or "\x00" in text:
        raise BridgeError("snapshot_path_invalid")
    try:
        cursor = Path(path.anchor)
        for component in path.parts[1:]:
            cursor = cursor / component
            if stat.S_ISLNK(cursor.lstat().st_mode):
                raise BridgeError("snapshot_symlink")
        resolved = path.resolve(strict=True)
        roots = [Path(root).resolve(strict=True) for root in allowed_roots]
    except BridgeError:
        raise
    except (OSError, RuntimeError):
        raise BridgeError("snapshot_path_unavailable") from None
    matching = [root for root in roots if root != resolved and root in resolved.parents]
    if len(matching) != 1:
        raise BridgeError("snapshot_path_outside_roots")
    try:
        metadata = resolved.lstat()
    except OSError:
        raise BridgeError("snapshot_path_unavailable") from None
    if not stat.S_ISREG(metadata.st_mode):
        raise BridgeError("snapshot_file_not_regular")
    return resolved


def parse_compose_file_paths(label_value: str, allowed_roots: Iterable[str | Path]) -> list[Path]:
    if not isinstance(label_value, str) or not label_value or len(label_value) > 8192:
        raise BridgeError("compose_files_label_invalid")
    raw_paths = label_value.split(",")
    if not 1 <= len(raw_paths) <= 16 or any(not value for value in raw_paths):
        raise BridgeError("compose_files_label_ambiguous")
    paths = [validate_snapshot_path(raw, allowed_roots) for raw in raw_paths]
    if len(paths) != len(set(paths)):
        raise BridgeError("compose_files_label_ambiguous")
    return paths


def validate_snapshot_metadata(metadata, *, allowed_owners: set[int], root_only: bool = False,
                               max_size: int = MAX_SNAPSHOT_BYTES) -> None:
    permissions = stat.S_IMODE(metadata.st_mode)
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > max_size):
        raise BridgeError("snapshot_file_metadata_invalid")
    if metadata.st_uid not in allowed_owners or permissions & 0o022:
        raise BridgeError("snapshot_file_permissions_invalid")
    if root_only and (metadata.st_uid != 0 or permissions & 0o077):
        raise BridgeError("snapshot_not_root_only")


def validate_private_snapshot_directory_metadata(metadata, *, allowed_owners: set[int]) -> None:
    permissions = stat.S_IMODE(metadata.st_mode)
    if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid not in allowed_owners
            or permissions & 0o077 or not permissions & 0o100):
        raise BridgeError("snapshot_parent_permissions_invalid")


def validate_private_snapshot_file_metadata(metadata, *, allowed_owners: set[int],
                                            max_size: int = MAX_SNAPSHOT_BYTES) -> None:
    validate_snapshot_metadata(metadata, allowed_owners=allowed_owners, max_size=max_size)
    permissions = stat.S_IMODE(metadata.st_mode)
    if permissions & 0o077 or permissions & 0o111 or not permissions & 0o400:
        raise BridgeError("snapshot_file_permissions_invalid")


def snapshot_sha256(path: str | Path, *, max_size: int = MAX_SNAPSHOT_BYTES) -> str:
    try:
        file_path = Path(path)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(file_path, flags)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > max_size:
                raise BridgeError("snapshot_file_metadata_invalid")
            digest = hashlib.sha256()
            size = 0
            with os.fdopen(descriptor, "rb", closefd=False) as source:
                while chunk := source.read(65536):
                    size += len(chunk)
                    if size > max_size:
                        raise BridgeError("snapshot_file_too_large")
                    digest.update(chunk)
            return digest.hexdigest()
        finally:
            os.close(descriptor)
    except BridgeError:
        raise
    except OSError:
        raise BridgeError("snapshot_read_failed") from None


def select_api_web(containers: Iterable[dict], project: str = PROJECT) -> dict[str, dict]:
    selected: dict[str, list[dict]] = {service: [] for service in SERVICES}
    for item in containers:
        if not isinstance(item, dict):
            raise BridgeError("container_snapshot_invalid")
        config = item.get("Config")
        labels = config.get("Labels") if isinstance(config, dict) else None
        if not isinstance(labels, dict):
            raise BridgeError("container_labels_invalid")
        if labels.get("com.docker.compose.project") != project:
            continue
        service = labels.get("com.docker.compose.service")
        if service not in selected:
            continue
        identity = item.get("Id")
        state = item.get("State")
        if not isinstance(identity, str) or not CONTAINER_ID_RE.fullmatch(identity):
            raise BridgeError("container_id_invalid")
        if not isinstance(state, dict) or state.get("Status") != "running":
            raise BridgeError("container_not_running")
        health = state.get("Health")
        health_status = health.get("Status") if isinstance(health, dict) else "none"
        if health_status not in {"healthy", "unhealthy", "starting", "none"}:
            raise BridgeError("container_health_invalid")
        selected[service].append(item)
    if any(len(selected[service]) != 1 for service in SERVICES):
        raise BridgeError("api_web_container_count_invalid")
    return {service: selected[service][0] for service in SERVICES}


def resolve_profile_set(profiles: Iterable[str] = PROFILES) -> tuple[str, ...]:
    selected = tuple(profiles)
    if selected != PROFILES:
        raise BridgeError("compose_profile_set_not_allowed")
    return selected


def allowlisted_environment(values) -> dict[str, str]:
    if isinstance(values, dict):
        pairs = values.items()
    elif isinstance(values, list):
        pairs = (entry.split("=", 1) for entry in values if isinstance(entry, str) and "=" in entry)
    else:
        raise BridgeError("container_environment_invalid")
    raw = {key: value for key, value in pairs if isinstance(key, str) and isinstance(value, str)}
    result: dict[str, str] = {}
    if SHA_RE.fullmatch(raw.get("APP_VERSION", "")):
        result["APP_VERSION"] = raw["APP_VERSION"]
    for key in ("APP_ENV", "FACIAL_PROCESSING_ENABLED"):
        value = raw.get(key)
        if value in {"production", "true", "false"}:
            result[key] = value
    return result


def minimized_service_record(service: str, item: dict) -> dict[str, str]:
    if service not in SERVICES:
        raise BridgeError("service_not_allowed")
    config = item.get("Config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    state = item.get("State")
    identity = item.get("Id")
    image = item.get("Image")
    compose_hash = labels.get("com.docker.compose.config-hash") if isinstance(labels, dict) else None
    if not isinstance(identity, str) or not CONTAINER_ID_RE.fullmatch(identity):
        raise BridgeError("container_id_invalid")
    if not isinstance(image, str) or not IMAGE_ID_RE.fullmatch(image):
        raise BridgeError("image_id_invalid")
    if compose_hash is not None and (not isinstance(compose_hash, str) or not HASH_RE.fullmatch(compose_hash)):
        raise BridgeError("compose_hash_invalid")
    health = state.get("Health") if isinstance(state, dict) else None
    health_status = health.get("Status") if isinstance(health, dict) else "none"
    if health_status not in {"healthy", "unhealthy", "starting", "none"}:
        raise BridgeError("container_health_invalid")
    result = {"service": service, "container_id": identity, "image_id": image,
              "compose_hash": compose_hash or "absent", "health": health_status}
    env = allowlisted_environment(config.get("Env", []))
    if service == "api":
        result["app_version"] = env.get("APP_VERSION", "invalid")
        result["app_env"] = env.get("APP_ENV", "invalid")
        result["facial_processing_enabled"] = env.get("FACIAL_PROCESSING_ENABLED", "invalid")
    elif "APP_VERSION" in env:
        result["app_version"] = env["APP_VERSION"]
    return result


def _safe_env(app_version: str) -> dict[str, str]:
    return {"PATH": SAFE_PATH, "HOME": "/root", "APP_VERSION": app_version,
            "BUILDKIT_PROGRESS": "quiet", "PYTHONDONTWRITEBYTECODE": "1"}


def _run(argv: list[str], *, cwd: Path = PROJECT_ROOT, app_version: str = "",
         input_text: str | None = None, timeout: int = 120, max_output: int = MAX_COMMAND_OUTPUT_BYTES) -> str:
    try:
        process_options = {"input": input_text} if input_text is not None else {"stdin": subprocess.DEVNULL}
        result = subprocess.run(argv, cwd=cwd, env=_safe_env(app_version), **process_options,
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise BridgeError("protected_command_failed") from None
    if len(result.stdout.encode("utf-8")) > max_output or len(result.stderr.encode("utf-8")) > max_output:
        raise BridgeError("protected_command_output_too_large")
    if result.returncode != 0:
        raise BridgeError("protected_command_failed")
    return result.stdout


def _git(*args: str) -> str:
    return _run(["/usr/bin/git", "-c", f"safe.directory={PROJECT_ROOT}", "-C", str(PROJECT_ROOT), *args],
                timeout=30, max_output=65536).strip()


def _root_metadata(path: Path, *, directory: bool = False, mode: int | None = None) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError:
        raise BridgeError("protected_path_unavailable") from None
    if stat.S_ISLNK(metadata.st_mode):
        raise BridgeError("protected_path_symlink")
    if directory and not stat.S_ISDIR(metadata.st_mode):
        raise BridgeError("protected_path_type_invalid")
    if not directory and not stat.S_ISREG(metadata.st_mode):
        raise BridgeError("protected_path_type_invalid")
    if metadata.st_uid != 0 or metadata.st_gid != 0:
        raise BridgeError("protected_path_owner_invalid")
    permissions = stat.S_IMODE(metadata.st_mode)
    if mode is not None and permissions != mode:
        raise BridgeError("protected_path_mode_invalid")
    if not directory and metadata.st_nlink != 1:
        raise BridgeError("protected_path_links_invalid")
    return metadata


def _validate_tree_no_symlink(path: Path) -> None:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current = current / component
        try:
            metadata = current.lstat()
        except OSError:
            raise BridgeError("protected_path_unavailable") from None
        if stat.S_ISLNK(metadata.st_mode):
            raise BridgeError("protected_path_symlink")


def _validate_snapshot_source(path: Path) -> str:
    project_root = PROJECT_ROOT.resolve(strict=True)
    state_root = STATE_DIR.resolve(strict=True)
    bridge_root = BRIDGE_STATE.resolve(strict=True)
    allowed = (project_root, state_root, bridge_root)
    checked = validate_snapshot_path(path, allowed)
    metadata = checked.lstat()
    if bridge_root in checked.parents:
        _root_metadata(bridge_root, directory=True, mode=0o700)
        _root_metadata(checked.parent, directory=True, mode=0o700)
        validate_snapshot_metadata(metadata, allowed_owners={0}, root_only=True)
        return snapshot_sha256(checked)
    if project_root == checked or project_root not in checked.parents:
        if state_root not in checked.parents:
            raise BridgeError("snapshot_path_outside_roots")
        state_metadata = state_root.lstat()
        private_owners = {0, project_root.stat().st_uid}
        validate_private_snapshot_directory_metadata(state_metadata, allowed_owners=private_owners)
        validate_private_snapshot_file_metadata(metadata, allowed_owners=private_owners)
        for parent in checked.parents:
            if parent == state_root:
                break
            if state_root not in parent.parents:
                raise BridgeError("snapshot_path_outside_roots")
            validate_private_snapshot_directory_metadata(parent.lstat(), allowed_owners=private_owners)
    else:
        repository_owner = project_root.stat().st_uid
        validate_snapshot_metadata(metadata, allowed_owners={0, repository_owner})
        relative = checked.relative_to(project_root).as_posix()
        blob = _git("rev-parse", f"HEAD:{relative}")
        actual = _git("hash-object", "--", str(checked))
        if not SHA_RE.fullmatch(blob) or actual != blob:
            raise BridgeError("tracked_snapshot_differs_from_checkout")
    return snapshot_sha256(checked)


def _validate_env_file() -> str:
    _validate_tree_no_symlink(ENV_FILE)
    root = PROJECT_ROOT.resolve(strict=True)
    env_path = validate_snapshot_path(ENV_FILE, (root,))
    repo_owner = root.stat().st_uid
    metadata = env_path.lstat()
    validate_snapshot_metadata(metadata, allowed_owners={0, repo_owner}, max_size=16 * 1024 * 1024)
    return snapshot_sha256(env_path, max_size=16 * 1024 * 1024)


def _docker(args: list[str], *, input_text: str | None = None, timeout: int = 120,
            max_output: int = MAX_COMMAND_OUTPUT_BYTES) -> str:
    return _run(["/usr/bin/docker", *args], input_text=input_text, timeout=timeout, max_output=max_output)


def _list_service_ids(service: str) -> list[str]:
    output = _docker(["ps", "--filter", f"label=com.docker.compose.project={PROJECT}",
                      "--filter", f"label=com.docker.compose.service={service}", "--format", "{{.ID}}"],
                     max_output=65536)
    ids = [line.strip() for line in output.splitlines() if line.strip()]
    if any(not re.fullmatch(r"[0-9a-f]{12,64}", item) for item in ids):
        raise BridgeError("container_id_invalid")
    return ids


def _inspect_api_web() -> dict[str, dict]:
    found: list[dict] = []
    for service in SERVICES:
        ids = _list_service_ids(service)
        if len(ids) != 1:
            raise BridgeError("api_web_container_count_invalid")
        raw = _docker(["inspect", ids[0]], max_output=MAX_COMMAND_OUTPUT_BYTES)
        try:
            decoded = json.loads(raw)
        except (TypeError, ValueError):
            raise BridgeError("container_snapshot_invalid") from None
        if not isinstance(decoded, list) or len(decoded) != 1 or not isinstance(decoded[0], dict):
            raise BridgeError("container_snapshot_invalid")
        found.extend(decoded)
    return select_api_web(found)


def _discover_context() -> dict:
    if not PROJECT_ROOT.is_dir() or not WORKING_DIR.is_dir() or not STATE_DIR.is_dir():
        raise BridgeError("project_paths_unavailable")
    env_digest = _validate_env_file()
    selected = _inspect_api_web()
    sources: dict[str, dict] = {}
    for service in SERVICES:
        item = selected[service]
        labels = item["Config"]["Labels"]
        if labels.get("com.docker.compose.project") != PROJECT:
            raise BridgeError("container_project_invalid")
        if labels.get("com.docker.compose.service") != service:
            raise BridgeError("container_service_invalid")
        raw_workdir = labels.get("com.docker.compose.project.working_dir")
        if not isinstance(raw_workdir, str) or ".." in Path(raw_workdir).parts:
            raise BridgeError("compose_working_directory_invalid")
        workdir = Path(raw_workdir)
        _validate_tree_no_symlink(workdir)
        if not workdir.is_dir() or not any(root == workdir or root in workdir.parents
                                            for root in (PROJECT_ROOT, STATE_DIR, BRIDGE_STATE)):
            raise BridgeError("compose_working_directory_invalid")
        raw_files = labels.get("com.docker.compose.project.config_files")
        paths = parse_compose_file_paths(raw_files, (PROJECT_ROOT, STATE_DIR, BRIDGE_STATE))
        config_hash = labels.get("com.docker.compose.config-hash")
        if config_hash is not None and (not isinstance(config_hash, str) or not HASH_RE.fullmatch(config_hash)):
            raise BridgeError("compose_hash_invalid")
        for path in paths:
            _validate_snapshot_source(path)
        sources[service] = {"paths": paths, "workdir": workdir, "config_hash": config_hash}
    all_paths = list(dict.fromkeys(path for service in SERVICES for path in sources[service]["paths"]))
    return {"containers": selected, "paths": all_paths, "sources": sources,
            "digests": {str(path): _validate_snapshot_source(path) for path in all_paths},
            "environment_digest": env_digest,
            "config_hashes": {service: sources[service]["config_hash"] for service in SERVICES}}


def _compose_prefix(context: dict, service: str = "api") -> list[str]:
    command = ["/usr/bin/docker", "compose", "--project-directory", str(context["sources"][service]["workdir"]),
               "--env-file", str(context["env_path"]), "-p", PROJECT]
    for path in context["compose_paths_by_service"][service]:
        command.extend(("-f", str(path)))
    for profile in resolve_profile_set():
        command.extend(("--profile", profile))
    return command


def _assert_sources_unchanged(context: dict) -> None:
    for path in context["paths"]:
        if _validate_snapshot_source(path) != context["digests"][str(path)]:
            raise BridgeError("snapshot_changed_during_operation")
    if _validate_env_file() != context["environment_digest"]:
        raise BridgeError("environment_changed_during_operation")


def _resolved_config(context: dict, app_version: str, service: str = "api") -> dict:
    output = _run(_compose_prefix(context, service) + ["config", "--format", "json"], app_version=app_version,
                  timeout=120, max_output=MAX_COMMAND_OUTPUT_BYTES)
    _assert_sources_unchanged(context)
    try:
        config = json.loads(output)
    except (TypeError, ValueError):
        raise BridgeError("compose_config_invalid") from None
    if not isinstance(config, dict) or not isinstance(config.get("services"), dict):
        raise BridgeError("compose_config_invalid")
    return config


def _prove_context(context: dict) -> None:
    models, identities = {}, {}
    for service in SERVICES:
        item = context["containers"][service]
        active_version = environment_map(item["Config"].get("Env") or []).get("APP_VERSION", "")
        document = _resolved_config(context, active_version, service)
        model = document["services"].get(service)
        image_info = json.loads(_docker(["image", "inspect", item["Image"]]))
        if not isinstance(image_info, list) or len(image_info) != 1:
            raise BridgeError("image_identity_unproven")
        prove_service_model(service, model, document, item, image_info[0])
        label_hash = context["config_hashes"][service]
        if label_hash is not None:
            fields = _run(_compose_prefix(context, service) + ["config", "--hash", service],
                          app_version=active_version, timeout=60, max_output=65536).split()
            if fields != [service, label_hash]:
                raise BridgeError("active_compose_hash_mismatch")
        reference = model.get("image")
        if not isinstance(reference, str):
            raise BridgeError("snapshot_image_missing")
        # A preserved source must name the actual image; a stale tag cannot
        # provide proof. Builds never retag this immutable source reference.
        reference_info = json.loads(_docker(["image", "inspect", reference]))
        if len(reference_info) != 1 or reference_info[0].get("Id") != item["Image"]:
            raise BridgeError("snapshot_image_differs_from_runtime")
        models[service] = document
        identities[service] = runtime_semantic_identity(item)
    context["models"] = models
    context["semantic_hashes"] = identities


def _hashes(context: dict, app_version: str, *, verify_active: bool) -> str:
    return "".join(f"{service} {context['semantic_hashes'][service]}\n" for service in SERVICES)


def _sources_fingerprint(context: dict) -> str:
    material = {"compose": {service: {"files": [context["digests"][str(path)] for path in context["sources"][service]["paths"]],
                                      "workdir": str(context["sources"][service]["workdir"])} for service in SERVICES},
                "environment": context["environment_digest"], "semantic": context.get("semantic_hashes", {})}
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _check_facial_config(context: dict, app_version: str) -> None:
    config = context["models"]["api"]
    api = config["services"].get("api")
    environment = api.get("environment") if isinstance(api, dict) else None
    if not isinstance(environment, dict):
        raise BridgeError("api_environment_invalid")
    if environment.get("APP_ENV") != "production":
        raise BridgeError("app_environment_must_remain_production")
    if environment.get("FACIAL_PROCESSING_ENABLED") != "true":
        raise BridgeError("facial_processing_must_remain_enabled")


def _web_identity(context: dict, target_sha: str) -> str:
    web = context["containers"]["web"]
    image, identity = web["Image"], context["semantic_hashes"]["web"]
    if (STATE_DIR / "web-current.identity").exists():
        fields = _state_value("web-current.identity").split()
        if (len(fields) == 4 and SHA_RE.fullmatch(fields[0]) and SHA_RE.fullmatch(fields[3])
                and fields[1:3] == [image, identity]):
            _git("merge-base", "--is-ancestor", fields[0], target_sha)
            return " ".join(fields) + "\n"
    revision = web["Config"]["Labels"].get("io.pickyourpic.release", "")
    if not SHA_RE.fullmatch(revision) or revision != _git("rev-parse", "HEAD"):
        raise BridgeError("web_release_revision_unproven")
    # This is a read-only bootstrap from proven runtime metadata; a stale
    # legacy receipt is preserved and never rewritten by inventory.
    _git("merge-base", "--is-ancestor", revision, target_sha)
    return f"{revision} {image} {identity} {revision}\n"


def _classify_compose_args(args: list[str], mode: str) -> str:
    if args in (["ps", "-q", "api"], ["ps", "-q", "web"], ["ps", "-q", "nginx"]):
        return "ps"
    if args == ["config", "--quiet"]:
        return "quiet-config"
    if args == ["exec", "-T", "-e", "PYTHONDONTWRITEBYTECODE=1", "api", "python", "-B", "-m", "alembic", "current"]:
        return "database-revision"
    if args == ["exec", "-T", "nginx", "nginx", "-t"]:
        if mode not in {"release", "rollback"}:
            raise BridgeError("compose_command_not_allowed")
        return "nginx-test"
    if args == ["exec", "-T", "nginx", "nginx", "-s", "reload"]:
        if mode not in {"release", "rollback"}:
            raise BridgeError("compose_command_not_allowed")
        return "nginx-reload"
    if args and args[0] == "build" and mode == "release":
        services = args[1:]
        if services in (["web"], ["api", "web"]):
            return "build"
    up_release = ["up", "-d", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "120", "api", "web"]
    up_rollback = ["up", "-d", "--no-build", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "120", "api", "web"]
    if mode == "release" and args == up_release:
        return "up"
    if mode == "rollback" and args == up_rollback:
        return "up"
    raise BridgeError("compose_command_not_allowed")


def _state_value(name: str) -> str:
    if not re.fullmatch(r"[a-z0-9.-]+", name):
        raise BridgeError("state_name_invalid")
    path = STATE_DIR / name
    _validate_tree_no_symlink(path)
    try:
        metadata = path.lstat()
        validate_snapshot_metadata(metadata, allowed_owners={0, PROJECT_ROOT.stat().st_uid})
        value = path.read_text(encoding="utf-8").strip()
    except BridgeError:
        raise
    except (OSError, UnicodeError):
        raise BridgeError("protected_state_unavailable") from None
    if not value or len(value) > 256:
        raise BridgeError("protected_state_invalid")
    return value


def _ensure_mutation_context(mode: str, target_sha: str) -> None:
    head = _git("rev-parse", "HEAD")
    if mode == "release":
        if _state_value("app-in-flight.sha") != target_sha or head != target_sha:
            raise BridgeError("release_marker_or_checkout_mismatch")
    elif mode == "rollback":
        rollback_sha = _state_value("app-previous.sha")
        if (_state_value("app-rollback-in-flight.sha") != target_sha or not SHA_RE.fullmatch(rollback_sha)
                or head != rollback_sha):
            raise BridgeError("rollback_marker_or_checkout_mismatch")
    else:
        raise BridgeError("mutating_mode_not_allowed")


def _ensure_root_bridge_directory() -> None:
    _validate_tree_no_symlink(MARKINA_STATE_ROOT)
    parent = MARKINA_STATE_ROOT.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0
            or stat.S_IMODE(parent.st_mode) & 0o022):
        raise BridgeError("protected_state_directory_permissions_invalid")
    try:
        BRIDGE_STATE.mkdir(mode=0o700)
    except FileExistsError:
        pass
    except OSError:
        raise BridgeError("bridge_state_create_failed") from None
    _root_metadata(BRIDGE_STATE, directory=True, mode=0o700)


def _read_private_copy_source(path: Path, expected_digest: str, *, max_size: int = MAX_SNAPSHOT_BYTES) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        try:
            metadata = os.fstat(descriptor)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                    or metadata.st_size > max_size):
                raise BridgeError("snapshot_file_metadata_invalid")
            chunks = bytearray()
            while chunk := os.read(descriptor, 65536):
                chunks.extend(chunk)
                if len(chunks) > max_size:
                    raise BridgeError("snapshot_file_too_large")
        finally:
            os.close(descriptor)
    except BridgeError:
        raise
    except OSError:
        raise BridgeError("snapshot_read_failed") from None
    data = bytes(chunks)
    if hashlib.sha256(data).hexdigest() != expected_digest:
        raise BridgeError("snapshot_changed_during_operation")
    return data


def _load_persistent_snapshot(context: dict, mode: str, target_sha: str, fingerprint: str) -> list[Path] | None:
    if mode not in {"release", "rollback"} or not HASH_RE.fullmatch(fingerprint):
        return None
    operation_id = f"{mode}-{target_sha}-{fingerprint[:16]}"
    destination = BRIDGE_STATE / operation_id
    if not destination.exists():
        return None
    _root_metadata(BRIDGE_STATE, directory=True, mode=0o700)
    _root_metadata(destination, directory=True, mode=0o700)
    manifest_path = destination / "manifest.json"
    manifest_metadata = _root_metadata(manifest_path)
    validate_snapshot_metadata(manifest_metadata, allowed_owners={0}, root_only=True)
    if manifest_metadata.st_size > MAX_SNAPSHOT_BYTES:
        raise BridgeError("snapshot_manifest_invalid")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BridgeError("snapshot_manifest_invalid") from None
    if (manifest.get("target_sha") != target_sha or manifest.get("fingerprint") != fingerprint
            or manifest.get("source_fingerprint") != _sources_fingerprint(context)):
        raise BridgeError("snapshot_manifest_mismatch")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != len(context["paths"]):
        raise BridgeError("snapshot_manifest_invalid")
    result: list[Path] = []
    for source, entry in zip(context["paths"], entries, strict=True):
        if not isinstance(entry, dict) or entry.get("source") != str(source):
            raise BridgeError("snapshot_manifest_invalid")
        saved_name = entry.get("saved_name")
        if (not isinstance(saved_name, str) or Path(saved_name).name != saved_name
                or not re.fullmatch(r"compose-[0-9]{2}-[0-9a-f]{16}\.yml", saved_name)):
            raise BridgeError("snapshot_manifest_invalid")
        saved_path = destination / saved_name
        saved_metadata = _root_metadata(saved_path)
        validate_snapshot_metadata(saved_metadata, allowed_owners={0}, root_only=True)
        source_hash = context["digests"][str(source)]
        if entry.get("sha256") != source_hash or snapshot_sha256(saved_path) != source_hash:
            raise BridgeError("snapshot_copy_hash_mismatch")
        result.append(saved_path)
    return result


def _prepare_compose_context(context: dict, mode: str, target_sha: str, fingerprint: str,
                             temporary_directory: Path) -> dict:
    _root_metadata(temporary_directory, directory=True, mode=0o700)
    copied = {}
    for index, source in enumerate(context["paths"]):
        source_digest = context["digests"][str(source)]
        content = _read_private_copy_source(source, source_digest)
        private_path = temporary_directory / f"compose-{index:02d}.yml"
        _write_private_file(private_path, content)
        copied[source] = private_path
    env_content = _read_private_copy_source(ENV_FILE, context["environment_digest"], max_size=16 * 1024 * 1024)
    env_path = temporary_directory / "app.env"
    _write_private_file(env_path, env_content)
    context["compose_paths_by_service"] = {service: [copied[path] for path in context["sources"][service]["paths"]]
                                            for service in SERVICES}
    context["env_path"] = env_path
    context["temporary_directory"] = temporary_directory
    return context


def _write_private_file(path: Path, value: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(value)
            destination.flush()
            os.fsync(destination.fileno())
    except OSError:
        raise BridgeError("private_snapshot_write_failed") from None


def _snapshot_sources(context: dict, mode: str, target_sha: str, fingerprint: str,
                      source_fingerprint: str) -> None:
    if mode not in {"release", "rollback"} or not HASH_RE.fullmatch(fingerprint):
        raise BridgeError("snapshot_operation_not_allowed")
    if not HASH_RE.fullmatch(source_fingerprint) or _sources_fingerprint(context) != source_fingerprint:
        raise BridgeError("snapshot_source_fingerprint_mismatch")
    _assert_common_lock_held()
    marker = "app-in-flight.sha" if mode == "release" else "app-rollback-in-flight.sha"
    if _state_value(marker) != target_sha:
        raise BridgeError("release_marker_or_checkout_mismatch")
    _ensure_root_bridge_directory()
    operation_id = f"{mode}-{target_sha}-{fingerprint[:16]}"
    destination = BRIDGE_STATE / operation_id
    try:
        destination.mkdir(mode=0o700)
    except FileExistsError:
        if _load_persistent_snapshot(context, mode, target_sha, fingerprint) is None:
            raise BridgeError("snapshot_operation_conflict")
        return
    except OSError:
        raise BridgeError("snapshot_operation_create_failed") from None

    entries: list[dict[str, str]] = []
    for index, source in enumerate(context["paths"]):
        source_hash = context["digests"][str(source)]
        content = _read_private_copy_source(source, source_hash)
        saved_name = f"compose-{index:02d}-{source_hash[:16]}.yml"
        saved_path = destination / saved_name
        _write_private_file(saved_path, content)
        saved_metadata = _root_metadata(saved_path)
        validate_snapshot_metadata(saved_metadata, allowed_owners={0}, root_only=True)
        if snapshot_sha256(saved_path) != source_hash:
            raise BridgeError("snapshot_copy_hash_mismatch")
        entries.append({"source": str(source), "saved_name": saved_name, "sha256": source_hash})
    manifest = {
        "version": 1,
        "mode": mode,
        "target_sha": target_sha,
        "fingerprint": fingerprint,
        "source_fingerprint": source_fingerprint,
        "services": {service: minimized_service_record(service, context["containers"][service])
                     for service in SERVICES},
        "files": entries,
        "models": context["models"],
        "containers": context["containers"],
    }
    _write_private_file(destination / "manifest.json", json.dumps(manifest, sort_keys=True).encode("utf-8"))
    _root_metadata(destination / "manifest.json")


def _operation_directory(mode: str, target_sha: str, fingerprint: str) -> Path:
    if mode not in {"release", "rollback"} or not SHA_RE.fullmatch(target_sha) or not HASH_RE.fullmatch(fingerprint):
        raise BridgeError("operation_identity_invalid")
    return BRIDGE_STATE / f"{mode}-{target_sha}-{fingerprint[:16]}"


def _read_manifest(directory: Path) -> dict:
    _root_metadata(BRIDGE_STATE, directory=True, mode=0o700)
    _root_metadata(directory, directory=True, mode=0o700)
    path = directory / "manifest.json"
    info = _root_metadata(path)
    validate_snapshot_metadata(info, allowed_owners={0}, root_only=True)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BridgeError("snapshot_manifest_invalid") from None
    if not isinstance(value, dict) or value.get("version") != 1 or set(value.get("models", {})) != set(SERVICES):
        raise BridgeError("snapshot_manifest_invalid")
    for entry in value.get("files", []):
        name = entry.get("saved_name") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not re.fullmatch(r"compose-[0-9]{2}-[0-9a-f]{16}\.yml", name):
            raise BridgeError("snapshot_manifest_invalid")
        saved = directory / name
        validate_snapshot_metadata(_root_metadata(saved), allowed_owners={0}, root_only=True)
        if snapshot_sha256(saved) != entry.get("sha256"):
            raise BridgeError("snapshot_copy_hash_mismatch")
    return value


def _escape_compose(value):
    if isinstance(value, str):
        return value.replace("$", "$$")
    if isinstance(value, list):
        return [_escape_compose(v) for v in value]
    if isinstance(value, dict):
        return {k: _escape_compose(v) for k, v in value.items()}
    return value


def replacement_document(service: str, document: dict, original: dict, image_id: str,
                         app_version: str) -> dict:
    """Clone a proven model; pin inherited defaults so the image cannot alter them."""
    result = copy.deepcopy(document)
    model = copy.deepcopy(document["services"][service])
    config = original["Config"]
    model["image"] = image_id
    for field in ("build", "depends_on", "profiles", "pull_policy"):
        model.pop(field, None)
    model["environment"] = environment_map(config.get("Env") or [])
    if service == "api":
        model["environment"]["APP_VERSION"] = app_version
    for field, key in (("command", "Cmd"), ("entrypoint", "Entrypoint"), ("user", "User"), ("working_dir", "WorkingDir")):
        model[field] = config.get(key) if config.get(key) is not None else []
        if field in {"user", "working_dir"} and not isinstance(model[field], str):
            model[field] = ""
    model["labels"] = {k: v for k, v in (config.get("Labels") or {}).items()
                       if not k.startswith("com.docker.compose.")}
    result["services"] = {service: model}
    # Do not create resources on the shared host. Every named network/volume
    # must already exist; Compose external declarations enforce that boundary.
    for category in ("networks", "volumes"):
        definitions = result.get(category) or {}
        result[category] = {name: {"name": value["name"], "external": True}
                            for name, value in definitions.items()}
    return result


def _assert_common_lock_held() -> None:
    import fcntl
    lock = STATE_DIR / "production-release.lock"
    _validate_tree_no_symlink(lock)
    try:
        descriptor = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            raise BridgeError("outer_release_lock_required")
        finally:
            os.close(descriptor)
    except BridgeError:
        raise
    except OSError:
        raise BridgeError("outer_release_lock_unavailable") from None


def _apply_models(context: dict, mode: str, target_sha: str, app_version: str, fingerprint: str) -> None:
    _assert_common_lock_held()
    directory = _operation_directory(mode, target_sha, fingerprint)
    manifest = _read_manifest(directory)
    if manifest.get("fingerprint") != fingerprint or manifest.get("target_sha") != target_sha:
        raise BridgeError("snapshot_approval_mismatch")
    if mode == "rollback":
        pointer = BRIDGE_STATE / "previous-release.json"
        validate_snapshot_metadata(_root_metadata(pointer), allowed_owners={0}, root_only=True)
        previous = json.loads(pointer.read_text(encoding="utf-8"))
        previous_directory = _operation_directory(previous.get("mode", "release"), previous["target_sha"], previous["fingerprint"])
        restore = _read_manifest(previous_directory)
    else:
        restore = manifest
    candidates = {}
    for service in SERVICES:
        original = restore["containers"][service]
        image_id = original["Image"] if mode == "rollback" else _docker([
            "image", "inspect", "--format", "{{.Id}}", PROJECT + "-" + service]).strip()
        if not IMAGE_ID_RE.fullmatch(image_id):
            raise BridgeError("target_image_identity_invalid")
        document = replacement_document(service, restore["models"][service], original, image_id,
                                        app_version if mode == "release" else environment_map(original["Config"].get("Env") or []).get("APP_VERSION", ""))
        # Prove the prospective effective config against the old runtime with
        # only the approved image/version difference before any recreation.
        expected = copy.deepcopy(original)
        expected["Image"] = image_id
        if service == "api" and mode == "release":
            expected["Config"]["Env"] = [f"{k}={v}" for k, v in document["services"][service]["environment"].items()]
        image_info = json.loads(_docker(["image", "inspect", image_id]))[0]
        prove_service_model(service, document["services"][service], document, expected, image_info)
        candidates[service] = document
    _assert_sources_unchanged(context)
    if mode == "release":
        _write_previous_pointer(mode, target_sha, fingerprint)
    for service in SERVICES:
        destination = directory / f"apply-{service}.compose.json"
        content = json.dumps(_escape_compose(candidates[service]), sort_keys=True).encode()
        if destination.exists():
            validate_snapshot_metadata(_root_metadata(destination), allowed_owners={0}, root_only=True)
            if destination.read_bytes() != content:
                raise BridgeError("prepared_target_changed")
        else:
            _write_private_file(destination, content)
    for service in SERVICES:
        destination = directory / f"apply-{service}.compose.json"
        command = ["/usr/bin/docker", "compose", "--project-directory", str(WORKING_DIR), "-p", PROJECT,
                   "-f", str(destination), "up", "-d", "--no-deps", "--no-build", "--pull", "never",
                   "--force-recreate", "--wait", "--wait-timeout", "120", service]
        _run(command, app_version=app_version, timeout=300)
    if mode == "rollback":
        _write_previous_pointer(mode, target_sha, fingerprint)


def _write_previous_pointer(mode: str, target_sha: str, fingerprint: str) -> None:
    _operation_directory(mode, target_sha, fingerprint)
    pointer = BRIDGE_STATE / "previous-release.json"
    if pointer.exists():
        validate_snapshot_metadata(_root_metadata(pointer), allowed_owners={0}, root_only=True)
    temporary = BRIDGE_STATE / (".previous-release-" + fingerprint + ".tmp")
    _write_private_file(temporary, json.dumps({"mode": mode, "target_sha": target_sha, "fingerprint": fingerprint}).encode())
    os.replace(temporary, pointer)


def _build_images(context: dict, target_sha: str, services: list[str]) -> None:
    _assert_common_lock_held()
    if _git("rev-parse", "HEAD") != target_sha or _git("status", "--porcelain"):
        raise BridgeError("build_checkout_not_approved")
    for service in services:
        if service == "api":
            # Preserve the installed facial runtime and all distributions.
            # The shell scope gate excludes dependencies and migrations.
            baseline = environment_map(context["containers"]["api"]["Config"].get("Env") or []).get("APP_VERSION", "")
            if not SHA_RE.fullmatch(baseline):
                raise BridgeError("api_baseline_version_invalid")
            _git("diff", "--exit-code", baseline, target_sha, "--", "backend/requirements.txt",
                 "backend/requirements-push.txt", "backend/face-requirements.txt", "backend/Dockerfile", "backend/migrations")
            source = context["containers"]["api"]["Image"]
            try:
                archive = subprocess.run(["/usr/bin/git", "-c", f"safe.directory={PROJECT_ROOT}", "-C", str(PROJECT_ROOT),
                                          "archive", target_sha, "backend/app"], env=_safe_env(""), stdin=subprocess.DEVNULL,
                                         capture_output=True, timeout=60, check=False)
            except (OSError, subprocess.TimeoutExpired):
                raise BridgeError("source_archive_failed") from None
            if archive.returncode or len(archive.stdout) > 64 * 1024 * 1024:
                raise BridgeError("source_archive_invalid")
            build_root = context["temporary_directory"] / "api-build"
            build_root.mkdir(mode=0o700)
            extract_app_archive(archive.stdout, build_root)
            dockerfile = f"FROM {source}\nCOPY backend/app /app/app\n"
            _run(["/usr/bin/docker", "build", "--quiet", "--pull=false", "-t", PROJECT + "-api", "-f", "-", str(build_root)],
                 input_text=dockerfile, timeout=3600)
        elif service == "web":
            _run(["/usr/bin/docker", "build", "--quiet", "-t", PROJECT + "-web", str(PROJECT_ROOT / "frontend")], timeout=3600)
        else:
            raise BridgeError("build_service_not_allowed")


def extract_app_archive(data: bytes, destination: Path) -> None:
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for member in archive:
            path = Path(member.name)
            if (path.is_absolute() or ".." in path.parts or "\\" in member.name
                    or not (member.name == "backend" or member.name == "backend/app"
                            or member.name.startswith("backend/app/"))):
                raise BridgeError("source_archive_path_invalid")
            if member.isdir():
                continue
            if not member.isfile() or member.size > MAX_SNAPSHOT_BYTES:
                raise BridgeError("source_archive_type_invalid")
            total += member.size
            if total > 64 * 1024 * 1024:
                raise BridgeError("source_archive_too_large")
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            source = archive.extractfile(member)
            if source is None:
                raise BridgeError("source_archive_invalid")
            with source:
                _write_private_file(target, source.read())


def _execute_compose(context: dict, mode: str, target_sha: str, app_version: str,
                     args: list[str], fingerprint: str = "") -> str:
    operation = _classify_compose_args(args, mode)
    if operation in {"build", "up", "nginx-test", "nginx-reload"}:
        _ensure_mutation_context(mode, target_sha)
        _assert_common_lock_held()
        manifest = _read_manifest(_operation_directory(mode, target_sha, fingerprint))
        if manifest.get("fingerprint") != fingerprint or manifest.get("target_sha") != target_sha:
            raise BridgeError("snapshot_approval_mismatch")
    if operation == "ps":
        service = args[-1]
        if service in SERVICES:
            return context["containers"][service]["Id"] + "\n"
        ids = _list_service_ids("nginx")
        if len(ids) != 1:
            raise BridgeError("nginx_container_count_invalid")
        return ids[0] + "\n"
    if operation == "build":
        _build_images(context, target_sha, args[1:])
        return ""
    if operation == "up":
        _apply_models(context, mode, target_sha, app_version, fingerprint)
        return ""
    if operation == "quiet-config":
        return ""
    if operation == "database-revision":
        output = _docker(["exec", "-e", "PYTHONDONTWRITEBYTECODE=1", context["containers"]["api"]["Id"],
                          "python", "-B", "-m", "alembic", "current"], timeout=60, max_output=65536)
        revisions = [match.group(1) for line in output.splitlines()
                     if (match := REVISION_RE.fullmatch(line.strip()))]
        if len(revisions) != 1:
            raise BridgeError("database_revision_invalid")
        return revisions[0] + "\n"
    if operation in {"nginx-test", "nginx-reload"}:
        ids = _list_service_ids("nginx")
        if len(ids) != 1:
            raise BridgeError("nginx_container_count_invalid")
        _docker(["exec", ids[0], "nginx", "-t"] if operation == "nginx-test" else
                ["exec", ids[0], "nginx", "-s", "reload"], timeout=30, max_output=65536)
        return ""
    raise BridgeError("compose_command_not_allowed")


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise BridgeError("arguments_invalid")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = SafeParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--mode", required=True, choices=("inventory", "release", "rollback-inventory", "rollback"))
    parser.add_argument("--sha", required=True)
    parser.add_argument("--app-version", default="")
    parser.add_argument("--approval-fingerprint", default="")
    parser.add_argument("--source-fingerprint", default="")
    parser.add_argument("operation", choices=("compose", "hashes", "service-hash", "web-identity", "sources-fingerprint", "assert-facial", "snapshot"))
    parser.add_argument("args", nargs=argparse.REMAINDER)
    try:
        parsed = parser.parse_args(argv)
    except SystemExit:
        raise BridgeError("arguments_invalid") from None
    if not SHA_RE.fullmatch(parsed.sha):
        raise BridgeError("target_sha_invalid")
    if parsed.app_version and not SHA_RE.fullmatch(parsed.app_version):
        raise BridgeError("app_version_invalid")
    if parsed.approval_fingerprint and not HASH_RE.fullmatch(parsed.approval_fingerprint):
        raise BridgeError("approval_fingerprint_invalid")
    if parsed.source_fingerprint and not HASH_RE.fullmatch(parsed.source_fingerprint):
        raise BridgeError("source_fingerprint_invalid")
    if parsed.mode in {"release", "rollback"} and not HASH_RE.fullmatch(parsed.approval_fingerprint):
        raise BridgeError("approval_fingerprint_required")
    parsed.args = parsed.args[1:] if parsed.args[:1] == ["--"] else parsed.args
    if parsed.operation == "compose":
        _classify_compose_args(parsed.args, parsed.mode)
    elif parsed.operation == "service-hash":
        if parsed.args not in (["api"], ["web"]):
            raise BridgeError("service_not_allowed")
    elif parsed.args:
        raise BridgeError("arguments_not_allowed")
    if parsed.operation == "snapshot" and parsed.mode not in {"release", "rollback"}:
        raise BridgeError("snapshot_operation_not_allowed")
    return parsed


def main(argv: list[str] | None = None) -> int:
    try:
        require_root()
        args = _parse_args(list(sys.argv[1:] if argv is None else argv))
        context = _discover_context()
        with tempfile.TemporaryDirectory(prefix="markina-app-compose-bridge-", dir="/tmp") as temporary:
            context = _prepare_compose_context(context, args.mode, args.sha, args.approval_fingerprint,
                                               Path(temporary))
            _prove_context(context)
            if args.operation == "compose":
                result = _execute_compose(context, args.mode, args.sha, args.app_version, args.args, args.approval_fingerprint)
            elif args.operation == "hashes":
                result = _hashes(context, args.app_version, verify_active=True)
            elif args.operation == "service-hash":
                result = context["semantic_hashes"][args.args[0]] + "\n"
            elif args.operation == "web-identity":
                result = _web_identity(context, args.sha)
            elif args.operation == "sources-fingerprint":
                result = _sources_fingerprint(context) + "\n"
            elif args.operation == "assert-facial":
                _check_facial_config(context, args.app_version)
                result = "facial_processing_enabled=true app_env=production\n"
            elif args.operation == "snapshot":
                _snapshot_sources(context, args.mode, args.sha, args.approval_fingerprint, args.source_fingerprint)
                result = "snapshot=preserved\n"
            else:
                raise BridgeError("operation_not_allowed")
            _assert_sources_unchanged(context)
            sys.stdout.write(result)
        return 0
    except BridgeError as exc:
        print(f"app-compose-bridge: {exc.code}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, decimal.InvalidOperation):
        print("app-compose-bridge: protected_contract_invalid", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
