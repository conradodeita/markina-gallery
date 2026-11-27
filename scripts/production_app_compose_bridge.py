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
import posixpath
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from collections.abc import Iterable
from contextlib import contextmanager
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
PICKER_CONFIG_SOURCE = "/etc/pyp-google-drive/picker-config.json"
PICKER_CONFIG_TARGET = "/run/secrets/google-drive-picker-config.json"
REVISION_RE = re.compile(r"^([0-9]{8}_[0-9]{4})(?:\s+.*)?$")
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024
MAX_COMMAND_OUTPUT_BYTES = 8 * 1024 * 1024
SAFE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

HANDOFF_OPERATIONS = {
    "handoff-witness-inventory": "inventory", "handoff-witness-register": "release",
    "handoff-inventory": "inventory", "handoff-prepare": "release", "handoff-apply": "release",
    "handoff-proxy": "release",
    "handoff-recovery-inventory": "rollback-inventory", "handoff-recovery-prepare": "rollback",
    "handoff-recovery-apply": "rollback",
    "handoff-legacy-recovery-inventory": "rollback-inventory",
    "handoff-legacy-recovery-prepare": "rollback", "handoff-legacy-recovery-finalize": "rollback",
    "handoff-legacy-recovery-proxy": "rollback",
}
HANDOFF_CANDIDATE_OPERATIONS = frozenset({"handoff-inventory", "handoff-prepare", "handoff-apply"})

# Every accepted Compose service field has an explicit comparison or is a
# build/orchestration field that never participates in a --no-deps recreation.
MODEL_FIELDS = frozenset({
    "image", "build", "container_name", "profiles", "depends_on", "pull_policy",
    "environment", "command", "entrypoint", "user", "working_dir", "healthcheck", "labels",
    "volumes", "networks", "expose", "ports", "restart", "stop_grace_period", "stop_signal",
    "read_only", "cap_drop", "cap_add", "security_opt", "privileged", "devices",
    "mem_limit", "mem_reservation", "cpus", "pids_limit", "init", "tmpfs", "ulimits",
    "dns", "extra_hosts", "logging", "network_mode", "ipc", "pid", "runtime",
    "stdin_open", "tty", "hostname", "domainname", "shm_size", "cgroup",
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


def tmpfs_options(value: str) -> tuple:
    """Canonicalize only documented, unambiguous Linux tmpfs mount options."""
    if not isinstance(value, str):
        raise BridgeError("semantic_tmpfs_options_invalid")
    result = {}
    groups = {v: group for group, values in {"access": ("ro", "rw"), "exec": ("exec", "noexec"),
              "suid": ("suid", "nosuid"), "dev": ("dev", "nodev")}.items() for v in values}
    for option in value.split(",") if value else []:
        key, separator, raw = option.partition("=")
        group = groups.get(key, key)
        if group in result:
            raise BridgeError("semantic_tmpfs_options_ambiguous")
        if key in groups and not separator:
            result[group] = key
        elif key == "size" and separator and re.fullmatch(r"[0-9]+[kKmMgG]?", raw):
            suffix = raw[-1].lower()
            result[group] = int(raw[:-1]) * {"k": 1024, "m": 1024**2, "g": 1024**3}[suffix] if suffix.isalpha() else int(raw)
        elif key == "mode" and separator and re.fullmatch(r"0?[0-7]{3,4}", raw):
            result[group] = int(raw, 8)
        elif key in {"uid", "gid"} and separator and raw.isascii() and raw.isdecimal():
            result[group] = int(raw)
        else:
            raise BridgeError("semantic_tmpfs_option_unsupported")
    return tuple(sorted(result.items()))


def tmpfs_model(values) -> dict:
    if not isinstance(values, list):
        raise BridgeError("semantic_tmpfs_model_invalid")
    result = {}
    for value in values:
        if not isinstance(value, str):
            raise BridgeError("semantic_tmpfs_model_invalid")
        path, _, options = value.partition(":")
        if not path.startswith("/") or ".." in path.split("/") or path in result:
            raise BridgeError("semantic_tmpfs_target_invalid")
        result[path] = tmpfs_options(options)
    return result


def byte_count(value) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    if not isinstance(value, str) or not (match := re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([bkmg])?b?", value.lower())):
        raise BridgeError("semantic_byte_quantity_invalid")
    result = decimal.Decimal(match[1]) * {None: 1, "b": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[match[2]]
    if result != int(result):
        raise BridgeError("semantic_byte_quantity_invalid")
    return int(result)


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
        if field in {"user", "working_dir"}:
            actual, expected = actual or "", expected or ""
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
        expected = model.get(field, default)
        if field in {"mem_limit", "mem_reservation", "shm_size"}:
            expected = byte_count(expected)
        _equal(host.get(docker_field, default), expected, field)
    _equal(host.get("NanoCpus", 0), int(decimal.Decimal(str(model.get("cpus", 0))) * 1000000000), "cpus")
    for field, docker_field in (("cap_drop", "CapDrop"), ("cap_add", "CapAdd"),
                                ("security_opt", "SecurityOpt"), ("dns", "Dns"), ("extra_hosts", "ExtraHosts")):
        _equal(sorted(host.get(docker_field) or []), sorted(model.get(field) or []), field)
    restart = model.get("restart") or "no"
    restart_parts = restart.split(":", 1)
    _equal(host.get("RestartPolicy"), {"Name": restart_parts[0], "MaximumRetryCount": int(restart_parts[1]) if len(restart_parts) == 2 else 0}, "restart")
    if model.get("devices") or host.get("Devices") or host.get("DeviceRequests"):
        raise BridgeError("semantic_devices_unsupported")
    if model.get("ulimits") or host.get("Ulimits"):
        raise BridgeError("semantic_tmpfs_or_ulimits_unsupported")
    _equal({path: tmpfs_options(options) for path, options in (host.get("Tmpfs") or {}).items()},
           tmpfs_model(model.get("tmpfs") or []), "tmpfs")
    if model.get("cgroup", "private") not in {"private", "host"}:
        raise BridgeError("semantic_cgroup_unsupported")
    _equal(host.get("CgroupnsMode") or "private", model.get("cgroup", "private"), "cgroup")
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
                 "CgroupParent", "Cgroup", "UsernsMode", "UTSMode"):
        value = host.get(name)
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
                   "Runtime", "PidMode", "IpcMode", "NetworkMode", "PortBindings", "Dns", "ExtraHosts", "Ulimits", "Tmpfs", "LogConfig", "ShmSize", "CgroupnsMode")
    mounts = [{k: m.get(k) for k in ("Type", "Name", "Source", "Destination", "RW", "Propagation")}
              for m in item.get("Mounts", [])]
    return digest({"environment": env, "config": {k: config.get(k) for k in config_fields},
                   "labels": {k: v for k, v in (config.get("Labels") or {}).items() if not k.startswith("com.docker.compose.")},
                   "host": {k: host.get(k) for k in host_fields}, "mounts": sorted(mounts, key=lambda m: m["Destination"]),
                   "networks": sorted(item.get("NetworkSettings", {}).get("Networks") or {})})


def adoption_document(service: str, item: dict, image: dict) -> dict:
    """Translate the active runtime, never silently repair a historical source.

    Pure function: callers must separately resolve and prove the result before
    approval. Docker metadata is not accepted as an opaque Compose payload.
    """
    if service not in SERVICES or not IMAGE_ID_RE.fullmatch(item.get("Image", "")):
        raise BridgeError("adoption_identity_invalid")
    config, host = item["Config"], item["HostConfig"]
    labels = config.get("Labels") or {}
    if labels.get("com.docker.compose.project") != PROJECT or labels.get("com.docker.compose.service") != service:
        raise BridgeError("adoption_service_invalid")
    known_config = {"AttachStderr", "AttachStdin", "AttachStdout", "Cmd", "Domainname", "Entrypoint", "Env",
                    "ExposedPorts", "Healthcheck", "Hostname", "Image", "Labels", "OpenStdin", "StdinOnce",
                    "StopSignal", "StopTimeout", "Tty", "User", "Volumes", "WorkingDir"}
    if set(config) - known_config or config.get("StdinOnce") or config.get("AttachStdin"):
        raise BridgeError("adoption_config_field_unsupported")
    scalar = {"Memory": "mem_limit", "MemoryReservation": "mem_reservation", "ReadonlyRootfs": "read_only",
              "Privileged": "privileged", "PidsLimit": "pids_limit", "Init": "init", "PidMode": "pid",
              "Runtime": "runtime", "IpcMode": "ipc", "ShmSize": "shm_size", "CgroupnsMode": "cgroup"}
    lists = {"CapDrop": "cap_drop", "CapAdd": "cap_add", "SecurityOpt": "security_opt", "Dns": "dns", "ExtraHosts": "extra_hosts"}
    supported = set(scalar) | set(lists) | {"NanoCpus", "RestartPolicy", "LogConfig", "Tmpfs", "Binds", "Mounts", "NetworkMode", "PortBindings"}
    empty_only = {"AutoRemove", "BlkioDeviceReadBps", "BlkioDeviceReadIOps", "BlkioDeviceWriteBps", "BlkioDeviceWriteIOps",
                  "BlkioWeight", "BlkioWeightDevice", "Cgroup", "CgroupParent", "ContainerIDFile", "CpuCount", "CpuPercent",
                  "CpuPeriod", "CpuQuota", "CpuRealtimePeriod", "CpuRealtimeRuntime", "CpuShares", "CpusetCpus", "CpusetMems",
                  "DeviceCgroupRules", "DeviceRequests", "Devices", "DnsOptions", "DnsSearch", "GroupAdd", "IOMaximumBandwidth",
                  "IOMaximumIOps", "Isolation", "Links", "MemorySwap", "MemorySwappiness", "OomKillDisable", "OomScoreAdj",
                  "PublishAllPorts", "UTSMode", "Ulimits", "UsernsMode", "VolumeDriver", "VolumesFrom", "Sysctls"}
    if set(host) - supported - empty_only - {"ConsoleSize", "MaskedPaths", "ReadonlyPaths"}:
        raise BridgeError("adoption_host_field_unsupported")
    if any(host.get(k) not in (None, False, 0, "", [], {}) for k in empty_only):
        raise BridgeError("adoption_host_option_unsupported")
    if host.get("ConsoleSize") not in (None, [0, 0]):
        raise BridgeError("adoption_console_unsupported")
    for binding in host.get("Binds") or []:
        fields = binding.split(":")
        if len(fields) not in {2, 3} or (len(fields) == 3 and set(fields[2].split(",")) -
                {"ro", "rw", "private", "rprivate", "shared", "rshared", "slave", "rslave"}):
            raise BridgeError("adoption_bind_option_unsupported")
    for mount in host.get("Mounts") or []:
        if (set(mount) - {"Type", "Source", "Target", "ReadOnly", "Consistency", "BindOptions", "VolumeOptions"}
                or set(mount.get("BindOptions") or {}) - {"Propagation"}
                or mount.get("Consistency") not in (None, "", "consistent")):
            raise BridgeError("adoption_mount_option_unsupported")
    # Fixed Engine default policy, covered by the Linux compatibility test.
    masks = {"/proc/acpi", "/proc/asound", "/proc/interrupts", "/proc/kcore", "/proc/keys", "/proc/latency_stats",
             "/proc/sched_debug", "/proc/scsi", "/proc/timer_list", "/proc/timer_stats", "/sys/devices/virtual/powercap", "/sys/firmware"}
    readonly = {"/proc/bus", "/proc/fs", "/proc/irq", "/proc/sys", "/proc/sysrq-trigger"}
    for key, expected in (("MaskedPaths", masks), ("ReadonlyPaths", readonly)):
        if key in host and set(host[key] or []) != expected:
            raise BridgeError("adoption_system_paths_unsupported")
    model = {"image": item["Image"], "environment": environment_map(config.get("Env") or []),
             "labels": {k: v for k, v in labels.items() if not k.startswith("com.docker.compose.")}}
    for field, key in (("command", "Cmd"), ("entrypoint", "Entrypoint"), ("user", "User"), ("working_dir", "WorkingDir")):
        model[field] = copy.deepcopy(config.get(key))
        if model[field] is None:
            model[field] = [] if field in {"command", "entrypoint"} else ""
    for key, field in scalar.items():
        if host.get(key) is not None and host[key] != "":
            model[field] = host[key]
    for key, field in lists.items():
        if host.get(key):
            model[field] = copy.deepcopy(host[key])
    if host.get("NanoCpus"):
        model["cpus"] = str(decimal.Decimal(host["NanoCpus"]) / 1000000000)
    restart = host.get("RestartPolicy") or {"Name": "no", "MaximumRetryCount": 0}
    model["restart"] = restart["Name"] + (":" + str(restart["MaximumRetryCount"]) if restart.get("MaximumRetryCount") else "")
    log = host.get("LogConfig") or {"Type": "json-file", "Config": {}}
    model["logging"] = {"driver": log["Type"], "options": copy.deepcopy(log.get("Config") or {})}
    for key, field in (("OpenStdin", "stdin_open"), ("Tty", "tty"), ("Domainname", "domainname"), ("StopSignal", "stop_signal")):
        if key in config:
            model[field] = config[key]
    if "StopTimeout" in config:
        model["stop_grace_period"] = str(config["StopTimeout"]) + "s"
    if config.get("Hostname") and config["Hostname"] != item.get("Id", "")[:12]:
        model["hostname"] = config["Hostname"]
    model["expose"] = sorted(config.get("ExposedPorts") or {})
    health_fields = {"Test": "test", "Interval": "interval", "Timeout": "timeout", "StartPeriod": "start_period",
                     "StartInterval": "start_interval", "Retries": "retries"}
    health = config.get("Healthcheck") or {}
    if set(health) - set(health_fields):
        raise BridgeError("adoption_healthcheck_unsupported")
    if health:
        model["healthcheck"] = {field: copy.deepcopy(health[key]) if key in {"Test", "Retries"} else str(health[key]) + "ns"
                                for key, field in health_fields.items() if key in health}
    document = {"services": {service: model}, "networks": {}, "volumes": {}}
    model["networks"] = {}
    for index, (name, network) in enumerate(sorted((item.get("NetworkSettings", {}).get("Networks") or {}).items())):
        if network.get("IPAMConfig") or network.get("Links") or network.get("DriverOpts"):
            raise BridgeError("adoption_network_option_unsupported")
        alias = f"network_{index}"
        document["networks"][alias] = {"name": name, "external": True}
        model["networks"][alias] = {"aliases": sorted(set(network.get("Aliases") or []) - {item.get("Id", "")[:12]}),
                                   "gw_priority": network.get("GwPriority", 0)}
    model["volumes"] = []
    for index, mount in enumerate(item.get("Mounts") or []):
        entry = {"type": mount["Type"], "target": mount["Destination"], "read_only": not mount["RW"]}
        if mount["Type"] == "volume":
            alias = f"volume_{index}"
            document["volumes"][alias] = {"name": mount["Name"], "external": True}
            entry["source"] = alias
            options = next((v.get("VolumeOptions") or {} for v in host.get("Mounts") or [] if v.get("Target") == mount["Destination"]), {})
            if options.get("NoCopy"):
                entry["volume"] = {"nocopy": True}
        elif mount["Type"] == "bind":
            entry.update(source=mount["Source"], bind={"propagation": mount.get("Propagation") or "rprivate", "create_host_path": False})
        else:
            raise BridgeError("adoption_mount_type_unsupported")
        model["volumes"].append(entry)
    if host.get("Tmpfs"):
        model["tmpfs"] = [path + (":" + value if value else "") for path, value in sorted(host["Tmpfs"].items())]
    # Pure validation is necessary, but callers must ALSO resolve via Compose.
    prove_service_model(service, model, document, item, image)
    return document


def adoption_runtime_binding(containers: dict) -> dict:
    """Include identity and safety fields omitted from the release digest."""
    return {service: {"container_id": item["Id"], "image_id": item["Image"],
                      "configuration": digest({key: item.get(key) for key in
                                               ("Config", "HostConfig", "Mounts", "NetworkSettings")})}
            for service, item in containers.items()}


def _assert_adoption_runtime_unchanged(context: dict) -> None:
    records = context.get("handoff_selection_records")
    current = handoff_select(_handoff_read_items(records), records) if records is not None else _inspect_api_web()
    if adoption_runtime_binding(current) != adoption_runtime_binding(context["containers"]):
        raise BridgeError("adoption_runtime_changed")
    for item in current.values():
        if item.get("State", {}).get("Health", {}).get("Status") != "healthy":
            raise BridgeError("adoption_runtime_unhealthy")
    _assert_sources_unchanged(context)


def _prepare_adoption(context: dict, target_sha: str) -> tuple[dict, dict]:
    if _git("rev-parse", "origin/main") != target_sha:
        raise BridgeError("adoption_support_sha_mismatch")
    models = {}
    candidate = copy.copy(context)
    candidate["sources"] = copy.deepcopy(context["sources"])
    candidate["compose_paths_by_service"] = {}
    candidate["config_hashes"] = {service: None for service in SERVICES}
    for service, item in context["containers"].items():
        if item["State"].get("Health", {}).get("Status") != "healthy":
            raise BridgeError("adoption_runtime_unhealthy")
        image = json.loads(_docker(["image", "inspect", item["Image"]]))
        if len(image) != 1:
            raise BridgeError("adoption_image_invalid")
        document = adoption_document(service, item, image[0])
        destination = context["temporary_directory"] / f"adoption-{service}.json"
        _write_private_file(destination, json.dumps(_escape_compose(document), sort_keys=True).encode())
        candidate["sources"][service]["workdir"] = WORKING_DIR
        candidate["compose_paths_by_service"][service] = [destination]
    # Independent resolver + existing semantic comparator, not the generator.
    _prove_context(candidate)
    models.update(candidate["models"])
    api_env = environment_map(context["containers"]["api"]["Config"].get("Env") or [])
    version = api_env.get("APP_VERSION", "")
    if (not SHA_RE.fullmatch(version) or api_env.get("APP_ENV") != "production"
            or api_env.get("FACIAL_PROCESSING_ENABLED") != "true"):
        raise BridgeError("adoption_application_baseline_invalid")
    if context["containers"]["web"]["Config"]["Labels"].get("io.pickyourpic.release") != version:
        raise BridgeError("adoption_web_revision_unproven")
    _git("merge-base", "--is-ancestor", version, target_sha)
    schema = _execute_compose(context, "inventory", target_sha, "",
                              ["exec", "-T", "-e", "PYTHONDONTWRITEBYTECODE=1", "api", "python", "-B", "-m", "alembic", "current"]).strip()
    if schema != "20261113_0126":
        raise BridgeError("adoption_schema_mismatch")
    proof = {"version": 1, "domain": "app-runtime-adoption-v1", "target_sha": target_sha,
             "runtime": adoption_runtime_binding(context["containers"]), "models": {s: digest(m) for s, m in models.items()},
             "sources": context["digests"], "environment": context["environment_digest"], "schema": schema, "app_version": version}
    _assert_adoption_runtime_unchanged(context)
    return models, proof


def _read_base_pointer() -> dict | None:
    path = BRIDGE_STATE / "active-base.json"
    if not os.path.lexists(path):
        return None
    _validate_tree_no_symlink(BRIDGE_STATE)
    _root_metadata(BRIDGE_STATE, directory=True, mode=0o700)
    validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
    value = json.loads(_read_private_copy_source(path, snapshot_sha256(path)))
    if (not isinstance(value, dict) or set(value) != {"base", "manifest_sha256"}
            or not HASH_RE.fullmatch(value.get("base", "")) or not HASH_RE.fullmatch(value.get("manifest_sha256", ""))):
        raise BridgeError("adoption_registry_invalid")
    return value


def _read_runtime_base(pointer: dict) -> tuple[Path, dict]:
    directory = BRIDGE_STATE / ("base-" + pointer["base"])
    _root_metadata(directory, directory=True, mode=0o700)
    manifest_path = directory / "manifest.json"
    validate_snapshot_metadata(_root_metadata(manifest_path), allowed_owners={0}, root_only=True)
    manifest = json.loads(_read_private_copy_source(manifest_path, pointer["manifest_sha256"]))
    if manifest.get("version") != 1 or set(manifest.get("models", {})) != set(SERVICES):
        raise BridgeError("adoption_manifest_invalid")
    # Validate every historical copy, even though it is not the selected source.
    for index, entry in enumerate(manifest.get("historical", [])):
        path = directory / f"historical-{index:03d}.json"
        validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
        _read_private_copy_source(path, entry["sha256"])
    for service in SERVICES:
        path = directory / f"{service}.compose.json"
        validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
        _read_private_copy_source(path, manifest["models"][service])
    return directory, manifest


def _select_adopted_sources(context: dict) -> dict:
    pointer = _read_base_pointer()
    if pointer is None:
        context["base_pointer_digest"] = None
        return context
    directory, manifest = _read_runtime_base(pointer)
    if manifest.get("runtime") != adoption_runtime_binding(context["containers"]):
        raise BridgeError("adoption_registry_runtime_mismatch")
    for service in SERVICES:
        path = directory / f"{service}.compose.json"
        context["paths"].append(path)
        context["digests"][str(path)] = manifest["models"][service]
        context["sources"][service] = {"paths": [path], "workdir": WORKING_DIR, "config_hash": None}
        context["config_hashes"][service] = None
    context["adopted_base"] = pointer
    context["base_pointer_digest"] = snapshot_sha256(BRIDGE_STATE / "active-base.json")
    context["paths"].append(directory / "manifest.json")
    context["digests"][str(directory / "manifest.json")] = pointer["manifest_sha256"]
    return context


def _record_transition(context: dict, mode: str, target_sha: str, fingerprint: str, candidates: dict) -> None:
    """Write proof of intended states before the first container replacement."""
    _assert_common_lock_held()
    directory = _operation_directory(mode, target_sha, fingerprint)
    _read_manifest(directory)
    manifest_path = directory / "manifest.json"
    record = {"version": 1, "mode": mode, "target_sha": target_sha, "approval": fingerprint,
              "manifest_sha256": snapshot_sha256(manifest_path), "candidates": {}}
    for service in SERVICES:
        path = directory / f"apply-{service}.compose.json"
        validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
        content = _read_private_copy_source(path, snapshot_sha256(path))
        if _decode_compose_literals(json.loads(content)) != candidates[service]:
            raise BridgeError("transition_candidate_changed")
        record["candidates"][service] = hashlib.sha256(content).hexdigest()
    destination = directory / "transition.json"
    content = json.dumps(record, sort_keys=True).encode()
    if os.path.lexists(destination):
        validate_snapshot_metadata(_root_metadata(destination), allowed_owners={0}, root_only=True)
        if _read_private_copy_source(destination, snapshot_sha256(destination)) != content:
            raise BridgeError("transition_already_exists")
    else:
        _write_private_file(destination, content)
    pointer_path = BRIDGE_STATE / "active-transition.json"
    if os.path.lexists(pointer_path):
        validate_snapshot_metadata(_root_metadata(pointer_path), allowed_owners={0}, root_only=True)
        old = _read_private_copy_source(pointer_path, snapshot_sha256(pointer_path))
        saved = directory / "previous-transition.json"
        if not os.path.lexists(saved):
            _write_private_file(saved, old)
    pointer = {"mode": mode, "target_sha": target_sha, "approval": fingerprint,
               "sha256": snapshot_sha256(destination)}
    staging = directory / ".transition-pointer.tmp"
    _write_private_file(staging, json.dumps(pointer, sort_keys=True).encode())
    os.replace(staging, pointer_path)
    if str(pointer_path) in context["digests"]:
        context["digests"][str(pointer_path)] = snapshot_sha256(pointer_path)


def _select_recovery_sources(context: dict, mode: str, target_sha: str) -> dict:
    if mode not in {"rollback-inventory", "rollback"}:
        raise BridgeError("recovery_mode_required")
    marker_matches = any((STATE_DIR / name).exists() and _state_value(name) == target_sha
                         for name in ("app-in-flight.sha", "app-rollback-in-flight.sha"))
    if not marker_matches:
        raise BridgeError("recovery_interrupted_marker_required")
    base = _read_base_pointer()
    if base is None:
        raise BridgeError("recovery_base_required")
    _read_runtime_base(base)
    pointer_path = BRIDGE_STATE / "active-transition.json"
    validate_snapshot_metadata(_root_metadata(pointer_path), allowed_owners={0}, root_only=True)
    pointer_hash = snapshot_sha256(pointer_path)
    pointer = json.loads(_read_private_copy_source(pointer_path, pointer_hash))
    if pointer.get("target_sha") != target_sha:
        raise BridgeError("recovery_transition_sha_mismatch")
    directory = _operation_directory(pointer["mode"], target_sha, pointer["approval"])
    transition_path = directory / "transition.json"
    validate_snapshot_metadata(_root_metadata(transition_path), allowed_owners={0}, root_only=True)
    transition = json.loads(_read_private_copy_source(transition_path, pointer["sha256"]))
    if (transition.get("version") != 1 or transition.get("mode") != pointer["mode"]
            or transition.get("target_sha") != target_sha or transition.get("approval") != pointer["approval"]
            or set(transition.get("candidates", {})) != set(SERVICES)):
        raise BridgeError("recovery_transition_invalid")
    manifest_path = directory / "manifest.json"
    _read_private_copy_source(manifest_path, transition["manifest_sha256"])
    previous = _read_manifest(directory)
    chosen, states = {}, {}
    protected = {pointer_path: pointer_hash, transition_path: pointer["sha256"], manifest_path: transition["manifest_sha256"]}
    for service, item in context["containers"].items():
        path = directory / f"apply-{service}.compose.json"
        validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
        content = _read_private_copy_source(path, transition["candidates"][service])
        protected[path] = transition["candidates"][service]
        candidate = _decode_compose_literals(json.loads(content))
        image = json.loads(_docker(["image", "inspect", item["Image"]]))[0]
        for state, document in (("previous", previous["models"][service]), ("candidate", candidate)):
            if document["services"][service].get("image") != item["Image"]:
                continue
            try:
                prove_service_model(service, document["services"][service], document, item, image)
            except BridgeError:
                continue
            chosen[service], states[service] = document, state
            break
        if service not in chosen:
            raise BridgeError("recovery_runtime_outside_transition")
    for path, checksum in protected.items():
        if path not in context["paths"]:
            context["paths"].append(path)
        context["digests"][str(path)] = checksum
    context["recovery_models"] = chosen
    context["recovery_transition"] = {"sha256": pointer_hash, "states": states,
                                       "runtime": adoption_runtime_binding(context["containers"])}
    context["base_pointer_digest"] = snapshot_sha256(BRIDGE_STATE / "active-base.json")
    context["adopted_base"] = base
    context["config_hashes"] = {service: None for service in SERVICES}
    return context


def _publish_runtime_base(context: dict, models: dict, proof: dict, approval: str,
                          handoff_records: list[dict] | None = None) -> None:
    if not HASH_RE.fullmatch(approval) or (proof.get("domain") == "app-runtime-adoption-v1" and digest(proof) != approval):
        raise BridgeError("adoption_approval_mismatch")
    _assert_common_lock_held()
    _assert_adoption_runtime_unchanged(context)
    _ensure_root_bridge_directory()
    material = {"proof": proof, "approval": approval}
    identity = digest(material)
    directory = BRIDGE_STATE / ("base-" + identity)
    if os.path.lexists(directory):
        raise BridgeError("adoption_base_already_exists")
    directory.mkdir(mode=0o700)
    _root_metadata(directory, directory=True, mode=0o700)
    previous = _read_base_pointer()
    if previous is not None:
        _write_private_file(directory / "previous-base.json", json.dumps(previous, sort_keys=True).encode())
    historical = []
    for index, source in enumerate(context["paths"]):
        source_hash = context["digests"][str(source)]
        content = _read_private_copy_source(source, source_hash)
        destination = directory / f"historical-{index:03d}.json"
        _write_private_file(destination, content)
        historical.append({"source": str(source), "sha256": source_hash})
    hashes = {}
    for service in SERVICES:
        path = directory / f"{service}.compose.json"
        _write_private_file(path, json.dumps(_escape_compose(models[service]), sort_keys=True).encode())
        hashes[service] = snapshot_sha256(path)
    manifest = {"version": 1, "runtime": adoption_runtime_binding(context["containers"]), "models": hashes,
                "historical": historical, **material}
    if handoff_records is not None:
        if context.get("handoff_selection_records") != handoff_records:
            raise BridgeError("handoff_base_records_unproven")
        manifest["handoff_records"] = copy.deepcopy(handoff_records)
    manifest_path = directory / "manifest.json"
    _write_private_file(manifest_path, json.dumps(manifest, sort_keys=True).encode())
    pointer = {"base": identity, "manifest_sha256": snapshot_sha256(manifest_path)}
    # Validate the private copies before the single activation point.
    for service in SERVICES:
        _read_private_copy_source(directory / f"{service}.compose.json", hashes[service])
    for index, entry in enumerate(historical):
        _read_private_copy_source(directory / f"historical-{index:03d}.json", entry["sha256"])
    _assert_adoption_runtime_unchanged(context)
    staging = BRIDGE_STATE / (".active-base-" + identity + ".tmp")
    _write_private_file(staging, json.dumps(pointer, sort_keys=True).encode())
    os.replace(staging, BRIDGE_STATE / "active-base.json")
    descriptor = os.open(BRIDGE_STATE, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    context["base_pointer_digest"] = snapshot_sha256(BRIDGE_STATE / "active-base.json")


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
    output = _docker(["ps", "--no-trunc", "--filter", f"label=com.docker.compose.project={PROJECT}",
                      "--filter", f"label=com.docker.compose.service={service}", "--format", "{{.ID}}"],
                     max_output=65536)
    ids = [line.strip() for line in output.splitlines() if line.strip()]
    if any(not re.fullmatch(r"[0-9a-f]{12,64}", item) for item in ids):
        raise BridgeError("container_id_invalid")
    return ids


def _inspect_api_web() -> dict[str, dict]:
    records = _handoff_registered_records()
    if records is not None:
        return handoff_select(_handoff_read_items(records), records)
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


def _discover_context(*, selected: dict | None = None, expected_projects: dict | None = None) -> dict:
    if not PROJECT_ROOT.is_dir() or not WORKING_DIR.is_dir() or not STATE_DIR.is_dir():
        raise BridgeError("project_paths_unavailable")
    env_digest = _validate_env_file()
    if selected is None:
        selected = _inspect_api_web()
        records = _handoff_registered_records()
        expected_projects = ({record["service"]: record["project"] for record in records if not record["retained"]}
                             if records is not None else {service: PROJECT for service in SERVICES})
    if expected_projects is None or set(selected) != set(SERVICES) or set(expected_projects) != set(SERVICES):
        raise BridgeError("handoff_discovery_unproven")
    sources: dict[str, dict] = {}
    for service in SERVICES:
        item = selected[service]
        labels = item["Config"]["Labels"]
        if labels.get("com.docker.compose.project") != expected_projects[service]:
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
            "config_hashes": {service: sources[service]["config_hash"] for service in SERVICES},
            "projects": dict(expected_projects)}


def _compose_prefix(context: dict, service: str = "api") -> list[str]:
    command = ["/usr/bin/docker", "compose", "--project-directory", str(context["sources"][service]["workdir"]),
               "--env-file", str(context["env_path"]), "-p", context.get("projects", {}).get(service, PROJECT)]
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
    if "base_pointer_digest" in context:
        pointer = BRIDGE_STATE / "active-base.json"
        observed = snapshot_sha256(pointer) if os.path.lexists(pointer) else None
        if observed != context["base_pointer_digest"]:
            raise BridgeError("adoption_registry_changed")


def _resolved_config(context: dict, app_version: str, service: str = "api") -> dict:
    output = _run(_compose_prefix(context, service) + ["config", "--format", "json"], app_version=app_version,
                  timeout=120, max_output=MAX_COMMAND_OUTPUT_BYTES)
    _assert_sources_unchanged(context)
    try:
        config = _decode_compose_literals(json.loads(output))
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
    if context.get("adopted_base"):
        material["adopted_base"] = context["adopted_base"]
    if context.get("recovery_transition"):
        material["recovery_transition"] = context["recovery_transition"]
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
    up_release = ["up", "-d", "--no-build", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "120", "api", "web"]
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
    for service, document in context.get("recovery_models", {}).items():
        path = temporary_directory / f"recovery-{service}.json"
        _write_private_file(path, json.dumps(_escape_compose(document), sort_keys=True).encode())
        context["compose_paths_by_service"][service] = [path]
        context["sources"][service]["workdir"] = WORKING_DIR
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


def _decode_compose_literals(value):
    """Decode config's re-serializable dollar escapes, not source interpolation.

    Only call on `docker compose config` output, never on an unparsed source.
    Keys are literal per Compose's contract and must not be transformed.
    """
    if isinstance(value, str):
        return value.replace("$$", "$")
    if isinstance(value, list):
        return [_decode_compose_literals(v) for v in value]
    if isinstance(value, dict):
        return {k: _decode_compose_literals(v) for k, v in value.items()}
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



def _handoff_registered_records() -> list[dict] | None:
    pointer = _read_base_pointer()
    if pointer is None:
        return None
    _, manifest = _read_runtime_base(pointer)
    records = manifest.get("handoff_records")
    if records is not None and (not isinstance(records, list) or not records):
        raise BridgeError("handoff_registry_invalid")
    return records


def _handoff_metadata() -> list[dict]:
    result = []
    for service in SERVICES:
        output = _docker(["ps", "-a", "--no-trunc", "--filter", "label=com.docker.compose.service=" + service,
                          "--format", '{{.ID}}|{{.Names}}|{{.Label "com.docker.compose.project"}}'])
        for line in output.splitlines():
            fields = line.split("|", 2)
            if len(fields) != 3:
                raise BridgeError("handoff_metadata_invalid")
            identity, name, project = fields
            if project != PROJECT and not project.startswith(PROJECT + "-app-"):
                continue
            if not CONTAINER_ID_RE.fullmatch(identity):
                raise BridgeError("handoff_metadata_invalid")
            result.append({"id": identity, "name": name, "project": project, "service": service})
    if len({row["id"] for row in result}) != len(result):
        raise BridgeError("handoff_duplicate_observation")
    return result


def _handoff_read_items(records: list[dict] | None = None) -> list[dict]:
    metadata = _handoff_metadata()
    identities = [row["id"] for row in metadata]
    if records is not None and set(identities) != {record["id"] for record in records}:
        raise BridgeError("handoff_unregistered_or_missing_container")
    if not identities:
        return []
    items = json.loads(_docker(["inspect", *identities]))
    if not isinstance(items, list) or {item.get("Id") for item in items} != set(identities):
        raise BridgeError("handoff_inspect_invalid")
    return items


def handoff_generation(target_sha: str, bundle_sha256: str, support_sha: str, state_digest: str) -> str:
    """A namespace is derived from approved identities, never caller names."""
    if (not SHA_RE.fullmatch(target_sha) or not SHA_RE.fullmatch(support_sha)
            or not HASH_RE.fullmatch(bundle_sha256) or not HASH_RE.fullmatch(state_digest)):
        raise BridgeError("handoff_identity_invalid")
    return PROJECT + "-app-" + digest({"target": target_sha, "bundle": bundle_sha256, "support": support_sha, "state": state_digest})[:32]


def handoff_retained_name(service: str, identity: str) -> str:
    if service not in SERVICES or not CONTAINER_ID_RE.fullmatch(identity):
        raise BridgeError("handoff_identity_invalid")
    return PROJECT + "-retained-" + service + "-" + identity


def handoff_configuration(item: dict) -> str:
    # Endpoint addresses/IDs change on stop/start; actual mount/config/security
    # policy remains exact. Network names and configured aliases remain bound.
    return digest({"config": item.get("Config"), "host": item.get("HostConfig"), "mounts": item.get("Mounts"),
                   "networks": {name: {key: values.get(key) for key in ("Aliases", "IPAMConfig", "DriverOpts", "GwPriority")}
                                for name, values in (item.get("NetworkSettings", {}).get("Networks") or {}).items()}})


def handoff_record(service: str, item: dict, project: str, *, retained: bool = False) -> dict:
    identity = item.get("Id", "")
    if service not in SERVICES or not CONTAINER_ID_RE.fullmatch(identity) or not IMAGE_ID_RE.fullmatch(item.get("Image", "")):
        raise BridgeError("handoff_identity_invalid")
    if project != PROJECT and not re.fullmatch(re.escape(PROJECT) + r"-app-[0-9a-f]{32}", project):
        raise BridgeError("handoff_project_invalid")
    expected_name = handoff_retained_name(service, identity) if retained else PROJECT + "-" + service + "-1"
    labels = item.get("Config", {}).get("Labels") or {}
    if (item.get("Name") != "/" + expected_name or labels.get("com.docker.compose.project") != project
            or labels.get("com.docker.compose.service") != service):
        raise BridgeError("handoff_container_identity_mismatch")
    if retained and item.get("State", {}).get("Running") is not False:
        raise BridgeError("handoff_retained_running")
    return {"id": identity, "image": item["Image"], "name": expected_name, "service": service,
            "project": project, "retained": retained, "configuration": handoff_configuration(item)}


def handoff_witness_record(item: dict) -> dict:
    """Describe a pre-approved historical object without granting an operation."""
    identity = item.get("Id", "")
    labels = item.get("Config", {}).get("Labels") or {}
    service = labels.get("com.docker.compose.service")
    name = item.get("Name", "").lstrip("/")
    if (not CONTAINER_ID_RE.fullmatch(identity) or not IMAGE_ID_RE.fullmatch(item.get("Image", ""))
            or labels.get("com.docker.compose.project") != PROJECT or service not in SERVICES
            or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,254}", name)
            or name in {PROJECT + "-api-1", PROJECT + "-web-1"} or name.startswith(PROJECT + "-retained-")
            or item.get("State", {}).get("Running") is not False
            or item.get("State", {}).get("Status") not in {"created", "exited"}):
        raise BridgeError("handoff_witness_invalid")
    return {"id": identity, "image": item["Image"], "name": name, "service": service,
            "project": PROJECT, "retained": True, "witness": True, "configuration": handoff_configuration(item),
            "lifecycle": digest({key: item["State"].get(key) for key in ("Status", "StartedAt", "FinishedAt", "ExitCode")})}


def _handoff_match_record(record: dict, item: dict) -> dict:
    if record.get("witness") is True:
        return handoff_witness_record(item)
    return handoff_record(record["service"], item, record["project"], retained=record["retained"])


def handoff_select(items: list[dict], records: list[dict]) -> dict:
    """Select exclusively by a previously verified private registry.

    Prefix matches detect unexpected objects; they NEVER authorize selection.
    """
    expected = {}
    for record in records:
        identity = record.get("id", "")
        if not CONTAINER_ID_RE.fullmatch(identity) or identity in expected:
            raise BridgeError("handoff_registry_invalid")
        expected[identity] = record
    found, active = set(), {}
    for item in items:
        identity = item.get("Id", "")
        labels = item.get("Config", {}).get("Labels") or {}
        project = labels.get("com.docker.compose.project", "")
        if identity not in expected:
            if ((project == PROJECT or project.startswith(PROJECT + "-app-"))
                    and labels.get("com.docker.compose.service") in SERVICES):
                raise BridgeError("handoff_unregistered_container")
            continue
        if identity in found:
            raise BridgeError("handoff_duplicate_observation")
        record = expected[identity]
        if _handoff_match_record(record, item) != record:
            raise BridgeError("handoff_registry_runtime_mismatch")
        found.add(identity)
        if not record["retained"]:
            service = record["service"]
            if service in active or not item.get("State", {}).get("Running"):
                raise BridgeError("handoff_active_invalid")
            active[service] = item
    if found != set(expected) or set(active) != set(SERVICES):
        raise BridgeError("handoff_registry_incomplete")
    return active


def handoff_plan(target_sha: str, support_sha: str, bundle_sha256: str, items: list[dict],
                 active_records: list[dict], models: dict, original_models: dict,
                 source_digests: dict, environment_digest: str, checkout_sha: str) -> dict:
    if (not SHA_RE.fullmatch(checkout_sha) or not HASH_RE.fullmatch(environment_digest) or not source_digests
            or any(not isinstance(path, str) or not HASH_RE.fullmatch(value) for path, value in source_digests.items())
            or set(original_models) != set(SERVICES)):
        raise BridgeError("handoff_sources_invalid")
    active = handoff_select(items, active_records)
    project = handoff_generation(target_sha, bundle_sha256, support_sha,
                                 digest({"sources": sorted(active_records, key=lambda record: record["id"]), "models": models,
                                         "source_digests": source_digests, "environment": environment_digest}))
    if set(models) != set(SERVICES):
        raise BridgeError("handoff_models_invalid")
    candidates, services = {}, {}
    occupied = {item.get("Name", "").lstrip("/"): item.get("Id") for item in items}
    for service, item in active.items():
        if item.get("State", {}).get("Health", {}).get("Status") != "healthy":
            raise BridgeError("handoff_source_unhealthy")
        retained = handoff_retained_name(service, item["Id"])
        if retained in occupied:
            raise BridgeError("handoff_retained_name_occupied")
        document = copy.deepcopy(models[service])
        if set(document.get("services", {})) != {service}:
            raise BridgeError("handoff_models_invalid")
        for category in ("networks", "volumes"):
            for definition in (document.get(category) or {}).values():
                if not isinstance(definition, dict) or set(definition) != {"name", "external"} or definition["external"] is not True:
                    raise BridgeError("handoff_resource_not_external")
        model = document["services"][service]
        if not IMAGE_ID_RE.fullmatch(model.get("image", "")) or any(key in model for key in ("build", "depends_on", "profiles", "ports")):
            raise BridgeError("handoff_model_not_closed")
        if any(key.startswith("com.docker.compose.") for key in (model.get("labels") or {})):
            raise BridgeError("handoff_fabricated_compose_labels")
        name = PROJECT + "-" + service + "-1"
        model["container_name"] = name
        candidates[service] = document
        services[service] = {"original_id": item["Id"], "original_name": name, "retained_name": retained,
                             "candidate_image": model["image"], "candidate_model": digest(document)}
    return {"version": 1, "domain": "app-first-handoff-v1", "target_sha": target_sha,
            "support_sha": support_sha, "bundle_sha256": bundle_sha256, "project": project,
            "sources": copy.deepcopy(sorted(active_records, key=lambda record: record["id"])), "services": services, "models": candidates,
            "original_models": copy.deepcopy(original_models), "source_digests": copy.deepcopy(source_digests),
            "environment_digest": environment_digest, "checkout_sha": checkout_sha}


def handoff_witness_registry() -> dict | None:
    path = BRIDGE_STATE / "handoff-witnesses.json"
    if not os.path.lexists(path):
        return None
    _validate_tree_no_symlink(path)
    _root_metadata(BRIDGE_STATE, directory=True, mode=0o700)
    validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
    value = json.loads(_read_private_copy_source(path, snapshot_sha256(path)))
    if (value.get("version") != 1 or value.get("domain") != "app-handoff-witnesses-v1"
            or not isinstance(value.get("witnesses"), list) or not HASH_RE.fullmatch(value.get("approval", ""))):
        raise BridgeError("handoff_witness_registry_invalid")
    if digest({key: item for key, item in value.items() if key != "approval"}) != value["approval"]:
        raise BridgeError("handoff_witness_registry_changed")
    return value


def handoff_witness_inventory(support_sha: str, items: list[dict], records: list[dict],
                              source_digests: dict, environment_digest: str) -> dict:
    if not SHA_RE.fullmatch(support_sha):
        raise BridgeError("handoff_witness_support_invalid")
    registry = handoff_witness_registry()
    active_records = [r for r in records if not r.get("witness")]
    if registry is None:
        known = {r["id"] for r in active_records}
        witnesses = [handoff_witness_record(item) for item in items if item["Id"] not in known]
    else:
        witnesses = registry["witnesses"]
    handoff_select(items, active_records + witnesses)
    return {"version": 1, "domain": "app-handoff-witnesses-v1", "support_sha": support_sha,
            "active": copy.deepcopy(active_records), "witnesses": sorted(witnesses, key=lambda r: r["id"]),
            "source_digests": copy.deepcopy(source_digests), "environment_digest": environment_digest}


def handoff_witness_inventory_report(proof: dict, items: list[dict], *, registry_present: bool) -> dict:
    """Separate current API/web from retained historical records for the retirement inventory."""
    if (not isinstance(proof, dict) or proof.get("domain") != "app-handoff-witnesses-v1"
            or not isinstance(proof.get("active"), list) or not isinstance(proof.get("witnesses"), list)
            or any(not isinstance(record, dict) for record in proof["active"] + proof["witnesses"])):
        raise BridgeError("handoff_witness_inventory_invalid")
    by_id = {item.get("Id"): item for item in items if isinstance(item, dict)}
    if len(by_id) != len(items):
        raise BridgeError("handoff_witness_inventory_invalid")
    active = [record for record in proof["active"] if not record.get("retained")]
    retained = [record for record in proof["active"] if record.get("retained")]
    if (len(active) != len(SERVICES) or {record.get("service") for record in active} != set(SERVICES)
            or len({record.get("id") for record in active}) != len(SERVICES)):
        raise BridgeError("handoff_witness_inventory_active_invalid")
    witnesses = []
    for record in retained:
        item = by_id.get(record.get("id"))
        if item is None or handoff_record(record.get("service"), item, record.get("project"), retained=True) != record:
            raise BridgeError("handoff_witness_runtime_mismatch")
        witnesses.append({**record, "lifecycle": digest({
            key: item.get("State", {}).get(key)
            for key in ("Status", "StartedAt", "FinishedAt", "ExitCode")
        }), "registered": True})
    for record in proof["witnesses"]:
        witnesses.append({**record, "registered": registry_present})
    witnesses.sort(key=lambda item: item["id"])
    active_ids = [record["id"] for record in sorted(active, key=lambda item: item["id"])]
    witness_ids = [record["id"] for record in witnesses]
    if (len(witness_ids) != len(set(witness_ids)) or set(active_ids) & set(witness_ids)
            or any(not isinstance(record.get("lifecycle"), str) or not HASH_RE.fullmatch(record["lifecycle"])
                   for record in witnesses)):
        raise BridgeError("handoff_witness_inventory_invalid")
    payload = {"proof": proof, "active": active, "witnesses": witnesses,
               "witness_registry_present": registry_present}
    return {"fingerprint": digest(payload), "registered": registry_present,
            "active_ids": active_ids, "witnesses": witnesses}


def handoff_register_witnesses(proof: dict, approval: str) -> None:
    _assert_common_lock_held()
    if proof.get("domain") != "app-handoff-witnesses-v1" or digest(proof) != approval:
        raise BridgeError("handoff_witness_approval_mismatch")
    _handoff_validate_inputs(proof)
    _ensure_root_bridge_directory()
    previous = handoff_witness_registry()
    if previous is not None and previous["witnesses"] != proof["witnesses"]:
        raise BridgeError("handoff_witness_set_changed")
    content = json.dumps({**proof, "approval": approval}, sort_keys=True).encode()
    path = BRIDGE_STATE / "handoff-witnesses.json"
    if previous is not None:
        checksum = snapshot_sha256(path)
        saved = BRIDGE_STATE / ("witnesses-" + checksum + ".json")
        if not os.path.lexists(saved):
            _write_private_file(saved, _read_private_copy_source(path, checksum))
        else:
            validate_snapshot_metadata(_root_metadata(saved), allowed_owners={0}, root_only=True)
            _read_private_copy_source(saved, checksum)
    staging = BRIDGE_STATE / (".witnesses-" + approval + ".tmp")
    _write_private_file(staging, content)
    _handoff_sync_directory(BRIDGE_STATE)
    os.replace(staging, path)
    _handoff_sync_directory(BRIDGE_STATE)


HANDOFF_PHASES = ("prepared", "stop_intent", "stopped", "rename_intent", "retained", "create_intent", "created", "healthy")
HANDOFF_RECOVERY_LEGACY_PHASES = ("prepared", "candidate_stop_intent", "candidate_stopped", "candidate_rename_intent",
                                  "candidate_retained", "original_rename_intent", "original_named", "original_start_intent",
                                  "original_started", "healthy")
HANDOFF_RECOVERY_PHASES = ("prepared", "candidate_stop_intent", "candidate_stopped", "candidate_rename_intent",
                           "candidate_retained", "original_stop_intent", "original_stopped",
                           "original_rename_intent", "original_retained", "recovery_create_intent",
                           "recovery_created", "recovery_start_intent", "recovery_started", "healthy")


def _handoff_phases(plan: dict) -> tuple:
    if plan.get("domain") == "app-first-handoff-v1":
        return HANDOFF_PHASES
    if plan.get("domain") == "app-first-handoff-recovery-plan-v1":
        return (HANDOFF_RECOVERY_PHASES if "picker_free_recovery_recipe" in plan
                else HANDOFF_RECOVERY_LEGACY_PHASES)
    raise BridgeError("handoff_plan_domain_invalid")


def _handoff_journal_directory(identity: str) -> Path:
    if not HASH_RE.fullmatch(identity):
        raise BridgeError("handoff_journal_identity_invalid")
    return BRIDGE_STATE / ("handoff-" + identity)


def _handoff_sync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _handoff_activate(directory: Path, state: dict) -> str:
    content = json.dumps(state, sort_keys=True).encode()
    checksum = hashlib.sha256(content).hexdigest()
    name = "state-" + str(state["sequence"]).zfill(6) + ".json"
    destination = directory / name
    if os.path.lexists(destination):
        validate_snapshot_metadata(_root_metadata(destination), allowed_owners={0}, root_only=True)
        if _read_private_copy_source(destination, checksum) != content:
            raise BridgeError("handoff_journal_uncommitted_conflict")
    else:
        _write_private_file(destination, content)
    pointer = json.dumps({"state": name, "sha256": checksum}, sort_keys=True).encode()
    staging = directory / (".active-" + checksum + ".tmp")
    if os.path.lexists(staging):
        validate_snapshot_metadata(_root_metadata(staging), allowed_owners={0}, root_only=True)
        if _read_private_copy_source(staging, hashlib.sha256(pointer).hexdigest()) != pointer:
            raise BridgeError("handoff_journal_staging_changed")
    else:
        _write_private_file(staging, pointer)
    _handoff_sync_directory(directory)
    os.replace(staging, directory / "active.json")
    _handoff_sync_directory(directory)
    return checksum


def handoff_journal_create(plan: dict) -> tuple[str, str]:
    _assert_common_lock_held()
    if plan.get("version") != 1 or plan.get("domain") not in {"app-first-handoff-v1", "app-first-handoff-recovery-plan-v1"} or set(plan.get("services", {})) != set(SERVICES):
        raise BridgeError("handoff_plan_invalid")
    _ensure_root_bridge_directory()
    identity = digest(plan)
    directory = _handoff_journal_directory(identity)
    if os.path.lexists(directory):
        raise BridgeError("handoff_journal_already_exists")
    directory.mkdir(mode=0o700)
    _root_metadata(directory, directory=True, mode=0o700)
    _write_private_file(directory / "plan.json", json.dumps(plan, sort_keys=True).encode())
    state = _handoff_initial_state(plan, identity)
    revision = _handoff_activate(directory, state)
    _handoff_sync_directory(BRIDGE_STATE)
    return identity, revision


def _handoff_initial_state(plan: dict, identity: str) -> dict:
    return {"version": 1, "plan": identity, "sequence": 0, "previous": None,
             "phases": {service: "prepared" for service in SERVICES},
             "observations": {record["service"]: {"id": record["id"], "configuration": record["configuration"]}
                              for record in plan["sources"] if not record["retained"]}, "event": None}


def _handoff_prepare_journal(plan: dict) -> tuple[str, str]:
    """Reconcile only a fresh, fully re-proven plan with no effect intent."""
    _assert_common_lock_held()
    identity = digest(plan)
    directory = _handoff_journal_directory(identity)
    if not os.path.lexists(directory):
        return handoff_journal_create(plan)
    _validate_tree_no_symlink(directory)
    _root_metadata(directory, directory=True, mode=0o700)
    content = json.dumps(plan, sort_keys=True).encode()
    plan_path = directory / "plan.json"
    if os.path.lexists(plan_path):
        validate_snapshot_metadata(_root_metadata(plan_path), allowed_owners={0}, root_only=True)
        _read_private_copy_source(plan_path, hashlib.sha256(content).hexdigest())
    elif not list(directory.iterdir()):
        _write_private_file(plan_path, content)
    else:
        raise BridgeError("handoff_preparation_unproven")
    if os.path.lexists(directory / "active.json"):
        saved, state, revision = handoff_journal_read(identity)
        if saved != plan or state != _handoff_initial_state(plan, identity):
            raise BridgeError("handoff_preparation_has_effect_intent")
        return identity, revision
    state = _handoff_initial_state(plan, identity)
    # _handoff_activate hashes the canonical byte representation used below.
    checksum = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    allowed = {"plan.json", "state-000000.json", ".active-" + checksum + ".tmp"}
    if any(path.name not in allowed for path in directory.iterdir()):
        raise BridgeError("handoff_preparation_unproven")
    revision = _handoff_activate(directory, state)
    _handoff_sync_directory(BRIDGE_STATE)
    return identity, revision


def handoff_journal_read(identity: str) -> tuple[dict, dict, str]:
    directory = _handoff_journal_directory(identity)
    _validate_tree_no_symlink(directory)
    _root_metadata(BRIDGE_STATE, directory=True, mode=0o700)
    _root_metadata(directory, directory=True, mode=0o700)
    for name in ("plan.json", "active.json"):
        validate_snapshot_metadata(_root_metadata(directory / name), allowed_owners={0}, root_only=True)
    plan = json.loads(_read_private_copy_source(directory / "plan.json", snapshot_sha256(directory / "plan.json")))
    if digest(plan) != identity:
        raise BridgeError("handoff_journal_plan_changed")
    pointer = json.loads(_read_private_copy_source(directory / "active.json", snapshot_sha256(directory / "active.json")))
    if (set(pointer) != {"state", "sha256"} or not re.fullmatch(r"state-[0-9]{6}\.json", pointer.get("state", ""))
            or not HASH_RE.fullmatch(pointer.get("sha256", ""))):
        raise BridgeError("handoff_journal_pointer_invalid")
    path = directory / pointer["state"]
    validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
    state = json.loads(_read_private_copy_source(path, pointer["sha256"]))
    if (state.get("version") != 1 or state.get("plan") != identity
            or not isinstance(state.get("sequence"), int) or not 0 <= state["sequence"] <= 64
            or pointer["state"] != "state-" + str(state["sequence"]).zfill(6) + ".json"
            or set(state.get("phases", {})) != set(SERVICES)
            or any(phase not in _handoff_phases(plan) for phase in state["phases"].values())):
        raise BridgeError("handoff_journal_state_invalid")
    # Verify the entire append-only chain, not only the active state.
    previous = state.get("previous")
    for sequence in range(state["sequence"] - 1, -1, -1):
        if not isinstance(previous, str) or not HASH_RE.fullmatch(previous):
            raise BridgeError("handoff_journal_chain_invalid")
        path = directory / ("state-" + str(sequence).zfill(6) + ".json")
        validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
        saved = json.loads(_read_private_copy_source(path, previous))
        if saved.get("sequence") != sequence or saved.get("plan") != identity:
            raise BridgeError("handoff_journal_chain_invalid")
        previous = saved.get("previous")
    if previous is not None:
        raise BridgeError("handoff_journal_chain_invalid")
    return plan, state, pointer["sha256"]


def handoff_journal_advance(identity: str, revision: str, service: str, phase: str, observation: dict) -> str:
    _assert_common_lock_held()
    plan, state, current = handoff_journal_read(identity)
    phases = _handoff_phases(plan)
    if not HASH_RE.fullmatch(revision) or current != revision:
        raise BridgeError("handoff_journal_revision_changed")
    if service not in SERVICES or phase not in phases:
        raise BridgeError("handoff_journal_phase_invalid")
    if phases.index(phase) != phases.index(state["phases"][service]) + 1:
        raise BridgeError("handoff_journal_phase_order")
    if service == "web" and state["phases"]["api"] != "healthy":
        raise BridgeError("handoff_api_health_required")
    if (not isinstance(observation, dict) or set(observation) != {"id", "configuration"}
            or not CONTAINER_ID_RE.fullmatch(observation.get("id", ""))
            or not HASH_RE.fullmatch(observation.get("configuration", ""))):
        raise BridgeError("handoff_journal_observation_invalid")
    next_state = copy.deepcopy(state)
    next_state["previous"] = current
    next_state["sequence"] += 1
    next_state["phases"][service] = phase
    next_state["observations"][service] = copy.deepcopy(observation)
    next_state["event"] = {"service": service, "phase": phase, "observation": observation}
    return _handoff_activate(_handoff_journal_directory(identity), next_state)


def _handoff_inspect(identity: str) -> dict:
    if not (CONTAINER_ID_RE.fullmatch(identity) or identity in {PROJECT + "-api-1", PROJECT + "-web-1"}):
        raise BridgeError("handoff_inspect_identity_invalid")
    result = json.loads(_docker(["inspect", identity]))
    if not isinstance(result, list) or len(result) != 1 or not isinstance(result[0], dict):
        raise BridgeError("handoff_inspect_invalid")
    return result[0]


def _handoff_original(plan: dict, service: str, *, retained: bool, running: bool) -> dict:
    expected = next(record for record in plan["sources"] if record["service"] == service and not record["retained"])
    item = _handoff_inspect(expected["id"])
    observed = handoff_record(service, item, expected["project"], retained=retained)
    compare = dict(expected, retained=retained,
                   name=handoff_retained_name(service, expected["id"]) if retained else expected["name"])
    if observed != compare or item.get("State", {}).get("Running") is not running:
        raise BridgeError("handoff_original_changed")
    return item


def _handoff_observation(item: dict) -> dict:
    return {"id": item["Id"], "configuration": handoff_configuration(item)}


def _handoff_candidate(plan: dict, service: str, *, healthy: bool) -> dict:
    item = _handoff_inspect(PROJECT + "-" + service + "-1")
    handoff_record(service, item, plan["project"])
    document = plan["models"][service]
    model = document["services"][service]
    if item.get("Image") != plan["services"][service]["candidate_image"]:
        raise BridgeError("handoff_candidate_image_changed")
    image = json.loads(_docker(["image", "inspect", item["Image"]]))[0]
    prove_service_model(service, model, document, item, image)
    if healthy and (not item.get("State", {}).get("Running")
                    or item.get("State", {}).get("Health", {}).get("Status") != "healthy"):
        raise BridgeError("handoff_candidate_unhealthy")
    return item


def _handoff_validate_inputs(plan: dict) -> None:
    if _validate_env_file() != plan["environment_digest"]:
        raise BridgeError("handoff_environment_changed")
    for raw, checksum in plan["source_digests"].items():
        if _validate_snapshot_source(Path(raw)) != checksum:
            raise BridgeError("handoff_source_changed")


def _handoff_check_api(item: dict) -> None:
    env = environment_map(item["Config"].get("Env") or [])
    if env.get("APP_ENV") != "production" or env.get("FACIAL_PROCESSING_ENABLED") != "true":
        raise BridgeError("handoff_restored_facial_mismatch")
    schema = _docker(["exec", "-e", "PYTHONDONTWRITEBYTECODE=1", item["Id"], "python", "-B", "-m", "alembic", "current"], timeout=60)
    revisions = [match.group(1) for line in schema.splitlines() if (match := REVISION_RE.fullmatch(line.strip()))]
    if revisions != ["20261113_0126"]:
        raise BridgeError("handoff_restored_schema_mismatch")


def handoff_execute_service(identity: str, revision: str, service: str) -> str:
    """No implicit resume: an intent left by a failure requires recovery."""
    _assert_common_lock_held()
    plan, state, current = handoff_journal_read(identity)
    if current != revision or service not in SERVICES or state["phases"][service] != "prepared":
        raise BridgeError("handoff_execution_requires_prepared")
    if service == "web" and state["phases"]["api"] != "healthy":
        raise BridgeError("handoff_api_health_required")
    _handoff_validate_inputs(plan)
    document = plan["models"][service]
    if digest(document) != plan["services"][service]["candidate_model"]:
        raise BridgeError("handoff_candidate_model_changed")
    original = _handoff_original(plan, service, retained=False, running=True)
    if original.get("State", {}).get("Health", {}).get("Status") != "healthy":
        raise BridgeError("handoff_source_unhealthy")
    _handoff_assert_retained_name_free(plan["services"][service]["retained_name"])
    if service == "web":
        api = _handoff_candidate(plan, "api", healthy=True)
        if _handoff_observation(api) != state["observations"]["api"]:
            raise BridgeError("handoff_api_changed_before_web")
    # Validate candidate defaults/configuration BEFORE stopping the original.
    prospective = copy.deepcopy(original)
    prospective["Image"] = plan["services"][service]["candidate_image"]
    prospective["Config"]["Env"] = [key + "=" + value for key, value in document["services"][service]["environment"].items()]
    image = json.loads(_docker(["image", "inspect", prospective["Image"]]))[0]
    prove_service_model(service, document["services"][service], document, prospective, image)
    destination = _handoff_journal_directory(identity) / ("apply-" + service + ".json")
    _write_private_file(destination, json.dumps(_escape_compose(document), sort_keys=True).encode())
    revision = handoff_journal_advance(identity, revision, service, "stop_intent", _handoff_observation(original))
    _handoff_validate_inputs(plan)
    _docker(["stop", "--time", "30", original["Id"]], timeout=60)
    stopped = _handoff_original(plan, service, retained=False, running=False)
    revision = handoff_journal_advance(identity, revision, service, "stopped", _handoff_observation(stopped))
    revision = handoff_journal_advance(identity, revision, service, "rename_intent", _handoff_observation(stopped))
    _handoff_validate_inputs(plan)
    _docker(["rename", original["Id"], plan["services"][service]["retained_name"]])
    retained = _handoff_original(plan, service, retained=True, running=False)
    revision = handoff_journal_advance(identity, revision, service, "retained", _handoff_observation(retained))
    revision = handoff_journal_advance(identity, revision, service, "create_intent", _handoff_observation(retained))
    _handoff_validate_inputs(plan)
    _run(["/usr/bin/docker", "compose", "--project-directory", str(WORKING_DIR), "-p", plan["project"],
          "-f", str(destination), "up", "-d", "--no-deps", "--no-build", "--pull", "never", "--wait",
          "--wait-timeout", "120", service], app_version=plan["target_sha"], timeout=300)
    candidate = _handoff_candidate(plan, service, healthy=True)
    revision = handoff_journal_advance(identity, revision, service, "created", _handoff_observation(candidate))
    if service == "api":
        _handoff_check_api(candidate)
    revision = handoff_journal_advance(identity, revision, service, "healthy", _handoff_observation(candidate))
    return revision


def handoff_recovery_inventory(identity: str, items: list[dict], images: dict, schema: str | None,
                               support_sha: str | None = None) -> dict:
    """Represent an interrupted handoff without pretending unavailable schema is known."""
    plan, state, revision = handoff_journal_read(identity)
    support_sha = support_sha or plan["support_sha"]
    if not SHA_RE.fullmatch(support_sha):
        raise BridgeError("handoff_recovery_support_invalid")
    restoring = plan["domain"] == "app-first-handoff-recovery-plan-v1"
    new_recovery = restoring and "picker_free_recovery_recipe" in plan
    if new_recovery:
        _handoff_validate_picker_free_recovery_plan(plan)
    if schema is not None and schema != "20261113_0126":
        raise BridgeError("handoff_recovery_schema_mismatch")
    by_id = {item["Id"]: item for item in items}
    if len(by_id) != len(items):
        raise BridgeError("handoff_duplicate_observation")
    known, services = set(), {}
    for record in plan["sources"]:
        if record["retained"]:
            item = by_id.get(record["id"])
            if item is None or _handoff_match_record(record, item) != record:
                raise BridgeError("handoff_recovery_retained_changed")
            known.add(item["Id"])
    for service in SERVICES:
        record = next(r for r in plan["sources"] if r["service"] == service and not r["retained"])
        original = by_id.get(record["id"])
        if original is None:
            raise BridgeError("handoff_recovery_original_missing")
        original_name = plan["services"][service]["original_name"]
        retained_name = plan["services"][service]["retained_name"]
        name = original.get("Name", "").lstrip("/")
        if name not in {original_name, retained_name}:
            raise BridgeError("handoff_recovery_original_name_changed")
        parked = name == retained_name
        phase = state["phases"][service]
        running = original.get("State", {}).get("Running") is True
        if not restoring and ((phase == "prepared" and (parked or not running))
                or (phase == "stop_intent" and parked)
                or (phase == "stopped" and (parked or running))
                or (phase == "rename_intent" and running)
                or (phase in {"retained", "create_intent", "created", "healthy"} and (not parked or running))):
            raise BridgeError("handoff_recovery_phase_mismatch")
        if restoring:
            previous = plan["recovery"]["services"][service]
            if new_recovery:
                previous_parked = previous["original"]["retained"]
                previous_running = previous["original_running"]
                if phase in {"prepared", "candidate_stop_intent", "candidate_stopped", "candidate_rename_intent", "candidate_retained"}:
                    if parked != previous_parked or running != previous_running:
                        raise BridgeError("handoff_recovery_original_phase_mismatch")
                elif phase == "original_stop_intent":
                    if parked != previous_parked or (running and not previous_running):
                        raise BridgeError("handoff_recovery_original_phase_mismatch")
                elif phase == "original_stopped":
                    if parked != previous_parked or running:
                        raise BridgeError("handoff_recovery_original_phase_mismatch")
                elif phase == "original_rename_intent":
                    if running or (previous_parked and not parked):
                        raise BridgeError("handoff_recovery_original_phase_mismatch")
                elif not parked or running:
                    raise BridgeError("handoff_recovery_original_phase_mismatch")
            elif phase in {"prepared", "candidate_stop_intent", "candidate_stopped", "candidate_rename_intent", "candidate_retained"}:
                if parked != previous["original"]["retained"] or running != previous["original_running"]:
                    raise BridgeError("handoff_recovery_original_phase_mismatch")
            elif phase == "original_rename_intent":
                if running != previous["original_running"]:
                    raise BridgeError("handoff_recovery_original_phase_mismatch")
            elif (phase in {"original_named", "original_start_intent", "original_started", "healthy"}
                  and (parked or (phase in {"original_started", "healthy"} and not running))):
                raise BridgeError("handoff_recovery_original_phase_mismatch")
        observed = handoff_record(service, original, record["project"], retained=parked)
        if observed != dict(record, retained=parked, name=name):
            raise BridgeError("handoff_recovery_original_changed")
        known.add(original["Id"])
        candidates = []
        for item in items:
            if item["Id"] == original["Id"]:
                continue
            labels = item.get("Config", {}).get("Labels") or {}
            if labels.get("com.docker.compose.project") != plan["project"] or labels.get("com.docker.compose.service") != service:
                continue
            candidates.append(item)
        if len(candidates) > 1:
            raise BridgeError("handoff_recovery_candidate_ambiguous")
        candidate = candidates[0] if candidates else None
        if not restoring and ((candidate and phase not in {"create_intent", "created", "healthy"}) or (not candidate and phase in {"created", "healthy"})):
            raise BridgeError("handoff_recovery_candidate_phase_mismatch")
        if restoring:
            previous_candidate = plan["recovery"]["services"][service]["candidate"]
            if bool(candidate) != bool(previous_candidate) or (candidate and candidate["Id"] != previous_candidate["id"]):
                raise BridgeError("handoff_recovery_candidate_identity_changed")
        if candidate:
            candidate_name = candidate.get("Name", "").lstrip("/")
            parked_candidate = candidate_name == handoff_retained_name(service, candidate["Id"])
            candidate_record = handoff_record(service, candidate, plan["project"], retained=parked_candidate)
            if candidate["Image"] != plan["services"][service]["candidate_image"]:
                raise BridgeError("handoff_recovery_candidate_image_changed")
            document = plan["models"][service]
            image = images.get(candidate["Image"])
            if image is None:
                raise BridgeError("handoff_recovery_image_missing")
            prove_service_model(service, document["services"][service], document, candidate, image)
            if not restoring and state["phases"][service] in {"created", "healthy"} and candidate["Id"] != state["observations"][service]["id"]:
                raise BridgeError("handoff_recovery_candidate_identity_changed")
            known.add(candidate["Id"])
        else:
            candidate_record = None
        recovery_candidate_record = None
        recovery_candidate_running = False
        recovery_candidate_health = None
        if new_recovery:
            recovery_matches = []
            for item in items:
                labels = item.get("Config", {}).get("Labels") or {}
                if (labels.get("com.docker.compose.project") == plan["recovery_project"]
                        and labels.get("com.docker.compose.service") == service):
                    recovery_matches.append(item)
            if len(recovery_matches) > 1:
                raise BridgeError("handoff_recovery_candidate_ambiguous")
            recovery_item = recovery_matches[0] if recovery_matches else None
            previous_recovery = plan["recovery"]["services"][service].get("recovery_candidate")
            if previous_recovery and (recovery_item is None or recovery_item["Id"] != previous_recovery["id"]):
                raise BridgeError("handoff_recovery_candidate_identity_changed")
            if recovery_item and not previous_recovery and phase not in {
                    "recovery_create_intent", "recovery_created", "recovery_start_intent", "recovery_started", "healthy"}:
                raise BridgeError("handoff_recovery_candidate_phase_mismatch")
            if recovery_item:
                recipe_entry = plan["picker_free_recovery_recipe"]["services"][service]
                if recovery_item.get("Image") != recipe_entry["image_id"]:
                    raise BridgeError("handoff_recovery_candidate_image_changed")
                recovery_candidate_record = handoff_record(service, recovery_item, plan["recovery_project"])
                image = images.get(recovery_item["Image"])
                if image is None:
                    raise BridgeError("handoff_recovery_image_missing")
                document = plan["recovery_models"][service]
                prove_service_model(service, document["services"][service], document, recovery_item, image)
                if (phase in {"recovery_created", "recovery_start_intent", "recovery_started", "healthy"}
                        and recovery_item["Id"] != state["observations"][service]["id"]):
                    raise BridgeError("handoff_recovery_candidate_identity_changed")
                if phase == "recovery_started" and not recovery_item.get("State", {}).get("Running"):
                    raise BridgeError("handoff_recovery_candidate_phase_mismatch")
                if phase == "healthy" and (not recovery_item.get("State", {}).get("Running")
                        or recovery_item.get("State", {}).get("Health", {}).get("Status") != "healthy"):
                    raise BridgeError("handoff_recovery_candidate_unhealthy")
                recovery_candidate_running = bool(recovery_item.get("State", {}).get("Running"))
                recovery_candidate_health = recovery_item.get("State", {}).get("Health", {}).get("Status", "none")
                known.add(recovery_item["Id"])
            elif phase in {"recovery_created", "recovery_start_intent", "recovery_started", "healthy"}:
                raise BridgeError("handoff_recovery_candidate_missing")
        if ((original["State"].get("Running") and candidate and candidate["State"].get("Running"))
                or (original["State"].get("Running") and recovery_candidate_running)
                or (candidate and candidate["State"].get("Running") and recovery_candidate_running)):
            raise BridgeError("handoff_recovery_two_running")
        services[service] = {"original": observed, "original_running": original["State"].get("Running") is True,
                             "original_health": original["State"].get("Health", {}).get("Status", "none"),
                             "candidate": candidate_record,
                             "candidate_running": bool(candidate and candidate["State"].get("Running")),
                             "candidate_health": candidate["State"].get("Health", {}).get("Status", "none") if candidate else None,
                             "recovery_candidate": recovery_candidate_record,
                             "recovery_candidate_running": recovery_candidate_running,
                             "recovery_candidate_health": recovery_candidate_health}
    for item in items:
        if item["Id"] in known:
            continue
        labels = item.get("Config", {}).get("Labels") or {}
        project = labels.get("com.docker.compose.project", "")
        if (project == PROJECT or project.startswith(PROJECT + "-app-")) and labels.get("com.docker.compose.service") in SERVICES:
            raise BridgeError("handoff_recovery_unregistered_container")
        if item.get("Name", "").lstrip("/") in {entry["original_name"] for entry in plan["services"].values()}:
            raise BridgeError("handoff_recovery_name_occupied")
    return {"version": 1, "domain": "app-handoff-recovery-v1", "handoff": identity,
            "revision": revision, "support_sha": support_sha, "interrupted_sha": plan["target_sha"],
            "schema_status": "unavailable" if schema is None else "verified", "schema": schema,
            "services": services}


def _picker_mount_path_intersects(value: object, anchor: str) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    lowered = value.lower()
    if "picker-config.json" in lowered or "google-drive-picker-config.json" in lowered:
        return True
    if not value.startswith("/"):
        return False
    normalized = posixpath.normpath(value)
    if normalized == "/":
        return True
    anchor_prefix = anchor.rstrip("/") + "/"
    normalized_prefix = normalized.rstrip("/") + "/"
    return normalized == anchor or anchor.startswith(normalized_prefix) or normalized.startswith(anchor_prefix)


def _picker_free_recovery_model(service: str, document: dict) -> tuple[dict, bool]:
    """Remove only the canonical Picker file bind from a proven service model."""
    if (service not in SERVICES or not isinstance(document, dict)
            or not isinstance(document.get("services"), dict) or set(document["services"]) != {service}):
        raise BridgeError("handoff_recovery_recipe_model_invalid")
    model = document["services"][service]
    if (not isinstance(model, dict) or set(model) - MODEL_FIELDS
            or not isinstance(model.get("image"), str) or not IMAGE_ID_RE.fullmatch(model["image"])):
        raise BridgeError("handoff_recovery_recipe_model_invalid")
    mounts = model.get("volumes", [])
    if not isinstance(mounts, list):
        raise BridgeError("handoff_recovery_recipe_mount_model_invalid")
    exact = []
    for index, mount in enumerate(mounts):
        if (not isinstance(mount, dict)
                or set(mount) - {"type", "source", "target", "read_only", "bind", "volume", "consistency"}
                or mount.get("type") not in ("bind", "volume")):
            raise BridgeError("handoff_recovery_recipe_mount_model_invalid")
        source, target = mount.get("source"), mount.get("target")
        picker_source = _picker_mount_path_intersects(source, PICKER_CONFIG_SOURCE)
        picker_target = _picker_mount_path_intersects(target, PICKER_CONFIG_TARGET)
        if picker_source or picker_target:
            if (mount.get("type") == "bind" and source == PICKER_CONFIG_SOURCE
                    and target == PICKER_CONFIG_TARGET):
                exact.append(index)
            else:
                raise BridgeError("handoff_recovery_recipe_picker_mount_ambiguous")
    if len(exact) > 1:
        raise BridgeError("handoff_recovery_recipe_picker_mount_ambiguous")

    tmpfs = model.get("tmpfs", [])
    if not isinstance(tmpfs, list):
        raise BridgeError("handoff_recovery_recipe_mount_model_invalid")
    for entry in tmpfs:
        if not isinstance(entry, str):
            raise BridgeError("handoff_recovery_recipe_mount_model_invalid")
        target = entry.split(":", 1)[0]
        if _picker_mount_path_intersects(target, PICKER_CONFIG_TARGET):
            raise BridgeError("handoff_recovery_recipe_picker_mount_ambiguous")

    result = copy.deepcopy(document)
    if exact:
        result["services"][service]["volumes"] = [mount for index, mount in enumerate(mounts) if index != exact[0]]
    return result, bool(exact)


def _handoff_picker_free_recovery_recipe(plan: dict) -> dict:
    original_models = plan.get("original_models")
    sources = plan.get("sources")
    if (not isinstance(original_models, dict) or set(original_models) != set(SERVICES)
            or not isinstance(sources, list) or any(not isinstance(record, dict) for record in sources)):
        raise BridgeError("handoff_recovery_recipe_source_invalid")
    recipe_services = {}
    for service in SERVICES:
        records = [record for record in sources if record.get("service") == service and not record.get("retained")]
        if (len(records) != 1 or not isinstance(records[0].get("image"), str)
                or not IMAGE_ID_RE.fullmatch(records[0]["image"])):
            raise BridgeError("handoff_recovery_recipe_source_invalid")
        recipe_model, picker_bind_removed = _picker_free_recovery_model(service, original_models[service])
        image_id = recipe_model["services"][service]["image"]
        if image_id != records[0]["image"]:
            raise BridgeError("handoff_recovery_recipe_image_mismatch")
        recipe_services[service] = {"image_id": image_id, "model": recipe_model,
                                    "model_sha256": digest(recipe_model),
                                    "picker_bind_removed": picker_bind_removed}
    unsigned = {"version": 1, "domain": "app-picker-free-recovery-recipe-v1", "services": recipe_services}
    return {**unsigned, "sha256": digest(unsigned)}


def _healthy_reference_service(observation: dict, item: dict) -> dict:
    running = [observation[k] for k in ("original", "candidate", "recovery_candidate")
               if observation.get(k + "_running")]
    if (len(running) != 1 or not isinstance(running[0], dict)
            or running[0].get("retained") is not False
            or running[0].get("id") != item["Id"] or running[0].get("image") != item["Image"]
            or item.get("State", {}).get("Running") is not True
            or item["State"].get("Health", {}).get("Status") != "healthy"):
        raise BridgeError("handoff_current_reference_unproven")
    return {"original": running[0], "original_running": True, "original_health": "healthy",
            "candidate": None, "candidate_running": False, "candidate_health": None,
            "recovery_candidate": None, "recovery_candidate_running": False, "recovery_candidate_health": None}


def _handoff_current_reference(proof: dict) -> tuple[dict, dict]:
    if proof["schema_status"] != "verified":
        raise BridgeError("handoff_current_reference_schema_unverified")
    support_sha = proof["support_sha"]
    with _handoff_proven_context(support_sha) as context:
        records = _handoff_context_records(context, require_witnesses=True)
        items = _handoff_read_items(records)
        active = handoff_select(items, records)
        observations = {}
        models = copy.deepcopy(context["models"])
        for service in SERVICES:
            item = active[service]
            if item["Id"] != context["containers"][service]["Id"]:
                raise BridgeError("handoff_current_reference_unproven")
            observations[service] = _healthy_reference_service(proof["services"][service], item)
            version = environment_map(item["Config"].get("Env") or []).get("APP_VERSION", "")
            models[service] = replacement_document(
                service, models[service], item, item["Image"], version)
        sources = dict(context["digests"])
        registry = BRIDGE_STATE / "handoff-witnesses.json"
        sources[str(registry)] = snapshot_sha256(registry)
        baseline = handoff_plan(proof["interrupted_sha"], support_sha, digest(models), items, records,
                                models, models, sources, context["environment_digest"], context["checkout_sha"])
        baseline["original_web_version"] = _web_identity(context, support_sha).split()[0]
        baseline["previous_handoff"] = proof["handoff"]
        return baseline, observations


def handoff_recovery_prepare(inventory: dict, approval: str, *, current_reference: tuple[dict, dict] | None = None) -> tuple[str, str]:
    _assert_common_lock_held()
    if inventory.get("domain") != "app-handoff-recovery-v1" or digest(inventory) != approval:
        raise BridgeError("handoff_recovery_approval_mismatch")
    original, _, revision = handoff_journal_read(inventory["handoff"])
    if revision != inventory["revision"]:
        raise BridgeError("handoff_recovery_revision_changed")
    if current_reference is not None:
        original, observations = current_reference
        if (digest(original) != inventory.get("current_reference_sha256")
                or original["previous_handoff"] != inventory["handoff"]):
            raise BridgeError("handoff_current_reference_changed")
        inventory = dict(inventory, services=observations)
    picker_free_recipe = _handoff_picker_free_recovery_recipe(original)
    recovery_project = original.get("recovery_project")
    if recovery_project is None:
        recovery_project = handoff_generation(
            original["target_sha"], original["bundle_sha256"], inventory["support_sha"],
            digest({"handoff": inventory["handoff"], "recipe_sha256": picker_free_recipe["sha256"]}))
    if not isinstance(recovery_project, str) or not re.fullmatch(re.escape(PROJECT) + r"-app-[0-9a-f]{32}", recovery_project):
        raise BridgeError("handoff_recovery_project_invalid")
    recovery_models = {}
    for service in SERVICES:
        document = copy.deepcopy(picker_free_recipe["services"][service]["model"])
        model = document["services"][service]
        expected_name = PROJECT + "-" + service + "-1"
        if model.get("container_name", expected_name) != expected_name:
            raise BridgeError("handoff_recovery_model_container_name_invalid")
        model["container_name"] = expected_name
        recovery_models[service] = document
    plan = copy.deepcopy(original)
    plan["domain"] = "app-first-handoff-recovery-plan-v1"
    plan["recovery"] = copy.deepcopy(inventory)
    plan["picker_free_recovery_recipe"] = picker_free_recipe
    plan["recovery_project"] = recovery_project
    plan["recovery_models"] = recovery_models
    plan["recovery_model_sha256"] = {service: digest(document) for service, document in recovery_models.items()}
    plan["approval"] = approval
    plan["support_sha"] = inventory["support_sha"]
    _handoff_validate_picker_free_recovery_plan(plan)
    return _handoff_prepare_journal(plan)


def _handoff_validate_picker_free_recovery_plan(plan: dict) -> dict:
    recipe = plan.get("picker_free_recovery_recipe")
    recovery_models = plan.get("recovery_models")
    model_hashes = plan.get("recovery_model_sha256")
    if (not isinstance(recipe, dict) or set(recipe) != {"version", "domain", "services", "sha256"}
            or recipe.get("version") != 1 or recipe.get("domain") != "app-picker-free-recovery-recipe-v1"
            or not isinstance(recipe.get("services"), dict) or set(recipe["services"]) != set(SERVICES)
            or not isinstance(recipe.get("sha256"), str) or not HASH_RE.fullmatch(recipe["sha256"])
            or digest({key: value for key, value in recipe.items() if key != "sha256"}) != recipe["sha256"]):
        raise BridgeError("handoff_recovery_recipe_invalid")
    if _handoff_picker_free_recovery_recipe(plan) != recipe:
        raise BridgeError("handoff_recovery_recipe_changed")
    if (not isinstance(recovery_models, dict) or set(recovery_models) != set(SERVICES)
            or not isinstance(model_hashes, dict) or set(model_hashes) != set(SERVICES)
            or not isinstance(plan.get("recovery_project"), str)
            or not re.fullmatch(re.escape(PROJECT) + r"-app-[0-9a-f]{32}", plan["recovery_project"])):
        raise BridgeError("handoff_recovery_model_invalid")
    for service in SERVICES:
        entry = recipe["services"][service]
        if (not isinstance(entry, dict) or set(entry) != {"image_id", "model", "model_sha256", "picker_bind_removed"}
                or not isinstance(entry.get("image_id"), str) or not IMAGE_ID_RE.fullmatch(entry["image_id"])
                or not isinstance(entry.get("model"), dict) or not isinstance(entry.get("picker_bind_removed"), bool)
                or not isinstance(entry.get("model_sha256"), str) or not HASH_RE.fullmatch(entry["model_sha256"])
                or digest(entry["model"]) != entry["model_sha256"]):
            raise BridgeError("handoff_recovery_recipe_invalid")
        expected_model = copy.deepcopy(entry["model"])
        expected_service = expected_model["services"][service]
        expected_name = PROJECT + "-" + service + "-1"
        if expected_service.get("container_name", expected_name) != expected_name:
            raise BridgeError("handoff_recovery_model_container_name_invalid")
        expected_service["container_name"] = expected_name
        if recovery_models[service] != expected_model or model_hashes[service] != digest(expected_model):
            raise BridgeError("handoff_recovery_model_changed")
    return recovery_models


def _handoff_picker_free_expected_runtime(service: str, item: dict, picker_bind_removed: bool) -> dict:
    expected = copy.deepcopy(item)
    actual_mounts = item.get("Mounts") or []
    if not isinstance(actual_mounts, list):
        raise BridgeError("handoff_recovery_runtime_mount_invalid")
    picker_mounts = []
    for index, mount in enumerate(actual_mounts):
        if not isinstance(mount, dict):
            raise BridgeError("handoff_recovery_runtime_mount_invalid")
        source, target = mount.get("Source"), mount.get("Destination")
        relevant = (_picker_mount_path_intersects(source, PICKER_CONFIG_SOURCE)
                    or _picker_mount_path_intersects(target, PICKER_CONFIG_TARGET))
        if relevant:
            if (mount.get("Type") != "bind" or source != PICKER_CONFIG_SOURCE
                    or target != PICKER_CONFIG_TARGET):
                raise BridgeError("handoff_recovery_runtime_picker_mount_ambiguous")
            picker_mounts.append(index)
    if len(picker_mounts) != int(picker_bind_removed):
        raise BridgeError("handoff_recovery_runtime_picker_mount_mismatch")
    if picker_mounts:
        expected["Mounts"] = [mount for index, mount in enumerate(actual_mounts) if index != picker_mounts[0]]

    host = expected.get("HostConfig")
    if not isinstance(host, dict):
        raise BridgeError("handoff_recovery_runtime_mount_invalid")
    host_binds = host.get("Binds") or []
    if not isinstance(host_binds, list):
        raise BridgeError("handoff_recovery_runtime_mount_invalid")
    retained_binds, picker_bind_specs = [], 0
    for bind in host_binds:
        if not isinstance(bind, str):
            raise BridgeError("handoff_recovery_runtime_mount_invalid")
        fields = bind.split(":")
        source, target = fields[0], fields[1] if len(fields) > 1 else None
        relevant = (_picker_mount_path_intersects(source, PICKER_CONFIG_SOURCE)
                    or _picker_mount_path_intersects(target, PICKER_CONFIG_TARGET))
        if relevant:
            if (len(fields) not in {2, 3} or source != PICKER_CONFIG_SOURCE
                    or target != PICKER_CONFIG_TARGET):
                raise BridgeError("handoff_recovery_runtime_picker_mount_ambiguous")
            picker_bind_specs += 1
            continue
        retained_binds.append(bind)
    if picker_bind_specs > 1 or (picker_bind_specs and not picker_bind_removed):
        raise BridgeError("handoff_recovery_runtime_picker_mount_mismatch")
    if host_binds != retained_binds:
        host["Binds"] = retained_binds

    host_mounts = host.get("Mounts") or []
    if not isinstance(host_mounts, list):
        raise BridgeError("handoff_recovery_runtime_mount_invalid")
    retained_host_mounts, picker_mount_specs = [], 0
    for mount in host_mounts:
        if not isinstance(mount, dict):
            raise BridgeError("handoff_recovery_runtime_mount_invalid")
        source, target = mount.get("Source"), mount.get("Target")
        relevant = (_picker_mount_path_intersects(source, PICKER_CONFIG_SOURCE)
                    or _picker_mount_path_intersects(target, PICKER_CONFIG_TARGET))
        if relevant:
            if (mount.get("Type") != "bind" or source != PICKER_CONFIG_SOURCE
                    or target != PICKER_CONFIG_TARGET):
                raise BridgeError("handoff_recovery_runtime_picker_mount_ambiguous")
            picker_mount_specs += 1
            continue
        retained_host_mounts.append(mount)
    if picker_mount_specs > 1 or (picker_mount_specs and not picker_bind_removed):
        raise BridgeError("handoff_recovery_runtime_picker_mount_mismatch")
    if host_mounts != retained_host_mounts:
        host["Mounts"] = retained_host_mounts
    return expected


def _handoff_validate_picker_free_service(plan: dict, service: str, original: dict) -> dict:
    recovery_models = _handoff_validate_picker_free_recovery_plan(plan)
    recipe_entry = plan["picker_free_recovery_recipe"]["services"][service]
    expected = _handoff_picker_free_expected_runtime(service, original, recipe_entry["picker_bind_removed"])
    image_output = _docker(["image", "inspect", recipe_entry["image_id"]])
    try:
        images = json.loads(image_output)
    except (TypeError, ValueError):
        raise BridgeError("handoff_recovery_image_invalid") from None
    if not isinstance(images, list) or len(images) != 1 or images[0].get("Id") != recipe_entry["image_id"]:
        raise BridgeError("handoff_recovery_image_invalid")
    document = recovery_models[service]
    if document["services"][service]["image"] != recipe_entry["image_id"]:
        raise BridgeError("handoff_recovery_recipe_image_mismatch")
    prove_service_model(service, document["services"][service], document, expected, images[0])
    return document


def _handoff_recovery_candidate(plan: dict, service: str, *, parked: bool) -> dict | None:
    record = plan["recovery"]["services"][service]["candidate"]
    if record is None:
        return None
    item = _handoff_inspect(record["id"])
    observed = handoff_record(service, item, plan["project"], retained=parked)
    expected = dict(record, retained=parked,
                    name=handoff_retained_name(service, record["id"]) if parked else PROJECT + "-" + service + "-1")
    if observed != expected:
        raise BridgeError("handoff_recovery_candidate_changed")
    return item


def _handoff_picker_free_candidate(plan: dict, service: str, *, running: bool | None = None,
                                   healthy: bool = False) -> dict:
    models = _handoff_validate_picker_free_recovery_plan(plan)
    item = _handoff_inspect(PROJECT + "-" + service + "-1")
    handoff_record(service, item, plan["recovery_project"])
    if item.get("Image") != plan["picker_free_recovery_recipe"]["services"][service]["image_id"]:
        raise BridgeError("handoff_recovery_candidate_image_changed")
    image = json.loads(_docker(["image", "inspect", item["Image"]]))[0]
    document = models[service]
    prove_service_model(service, document["services"][service], document, item, image)
    if running is not None and item.get("State", {}).get("Running") is not running:
        raise BridgeError("handoff_recovery_candidate_state_changed")
    if healthy and (item.get("State", {}).get("Health", {}).get("Status") != "healthy"):
        raise BridgeError("handoff_recovery_candidate_unhealthy")
    return item


def _handoff_wait_picker_free_candidate(plan: dict, service: str) -> dict:
    deadline = time.monotonic() + 120
    while True:
        item = _handoff_picker_free_candidate(plan, service, running=True)
        if item.get("State", {}).get("Health", {}).get("Status") == "healthy":
            return item
        if time.monotonic() >= deadline:
            raise BridgeError("handoff_recovery_candidate_unhealthy")
        time.sleep(2)


def _handoff_wait_restored(plan: dict, service: str) -> dict:
    deadline = time.monotonic() + 120
    while True:
        item = _handoff_original(plan, service, retained=False, running=True)
        if item.get("State", {}).get("Health", {}).get("Status") == "healthy":
            return item
        if time.monotonic() >= deadline:
            raise BridgeError("handoff_restored_unhealthy")
        time.sleep(2)


def handoff_recover_service(identity: str, revision: str, service: str) -> str:
    _assert_common_lock_held()
    plan, state, current = handoff_journal_read(identity)
    if (plan["domain"] != "app-first-handoff-recovery-plan-v1" or current != revision
            or service not in SERVICES or state["phases"][service] != "prepared"):
        raise BridgeError("handoff_recovery_requires_prepared")
    if "picker_free_recovery_recipe" not in plan:
        raise BridgeError("handoff_recovery_recipe_required")
    if service == "web" and state["phases"]["api"] != "healthy":
        raise BridgeError("handoff_api_health_required")
    _handoff_validate_inputs(plan)
    recovery_models = _handoff_validate_picker_free_recovery_plan(plan)
    entry = plan["recovery"]["services"][service]
    original_parked = entry["original"]["retained"]
    original = _handoff_original(plan, service, retained=original_parked, running=entry["original_running"])
    candidate_parked = bool(entry["candidate"] and entry["candidate"]["retained"])
    candidate = _handoff_recovery_candidate(plan, service, parked=candidate_parked)
    recovery_candidate_record = entry.get("recovery_candidate")
    recovery_candidate = (_handoff_picker_free_candidate(
        plan, service, running=entry["recovery_candidate_running"])
        if recovery_candidate_record else None)
    if recovery_candidate and handoff_record(service, recovery_candidate, plan["recovery_project"]) != recovery_candidate_record:
        raise BridgeError("handoff_recovery_candidate_changed")
    if (original.get("State", {}).get("Health", {}).get("Status", "none") != entry["original_health"]
            or (candidate and (candidate.get("State", {}).get("Running") is True) != entry["candidate_running"])
            or (candidate and candidate.get("State", {}).get("Health", {}).get("Status", "none") != entry["candidate_health"])
            or (recovery_candidate and recovery_candidate.get("State", {}).get("Health", {}).get("Status", "none")
                != entry["recovery_candidate_health"])):
        raise BridgeError("handoff_recovery_runtime_changed")
    recovery_model = _handoff_validate_picker_free_service(plan, service, original)
    if recovery_model != recovery_models[service]:
        raise BridgeError("handoff_recovery_model_changed")
    if not recovery_candidate:
        existing = [item for item in _handoff_read_items()
                    if (item.get("Config", {}).get("Labels") or {}).get("com.docker.compose.project") == plan["recovery_project"]
                    and (item.get("Config", {}).get("Labels") or {}).get("com.docker.compose.service") == service]
        if existing:
            raise BridgeError("handoff_recovery_candidate_unregistered")

    observation = _handoff_observation(candidate or recovery_candidate or original)
    revision = handoff_journal_advance(identity, revision, service, "candidate_stop_intent", observation)
    if candidate and candidate.get("State", {}).get("Running"):
        _docker(["stop", "--time", "30", candidate["Id"]], timeout=60)
    candidate = _handoff_recovery_candidate(plan, service, parked=candidate_parked)
    if candidate and candidate.get("State", {}).get("Running"):
        raise BridgeError("handoff_recovery_candidate_still_running")
    observation = _handoff_observation(candidate or original)
    revision = handoff_journal_advance(identity, revision, service, "candidate_stopped", observation)
    revision = handoff_journal_advance(identity, revision, service, "candidate_rename_intent", observation)
    if candidate and not candidate_parked:
        name = handoff_retained_name(service, candidate["Id"])
        if _docker(["ps", "-a", "--filter", "name=^/" + name + "$", "--format", "{{.ID}}"]).strip():
            raise BridgeError("handoff_retained_name_occupied")
        _docker(["rename", candidate["Id"], name])
    candidate = _handoff_recovery_candidate(plan, service, parked=bool(candidate))
    revision = handoff_journal_advance(identity, revision, service, "candidate_retained", _handoff_observation(candidate or original))
    revision = handoff_journal_advance(identity, revision, service, "original_stop_intent", _handoff_observation(original))
    if original.get("State", {}).get("Running"):
        _docker(["stop", "--time", "30", original["Id"]], timeout=60)
    stopped_original = _handoff_original(plan, service, retained=original_parked, running=False)
    revision = handoff_journal_advance(identity, revision, service, "original_stopped", _handoff_observation(stopped_original))
    revision = handoff_journal_advance(identity, revision, service, "original_rename_intent", _handoff_observation(stopped_original))
    if not original_parked:
        retained_name = handoff_retained_name(service, original["Id"])
        if _docker(["ps", "-a", "--filter", "name=^/" + retained_name + "$", "--format", "{{.ID}}"]).strip():
            raise BridgeError("handoff_retained_name_occupied")
        _docker(["rename", original["Id"], retained_name])
    retained_original = _handoff_original(plan, service, retained=True, running=False)
    revision = handoff_journal_advance(identity, revision, service, "original_retained", _handoff_observation(retained_original))

    destination = _handoff_journal_directory(identity) / ("recovery-apply-" + service + ".compose.json")
    content = json.dumps(_escape_compose(recovery_model), sort_keys=True).encode()
    if os.path.lexists(destination):
        validate_snapshot_metadata(_root_metadata(destination), allowed_owners={0}, root_only=True)
        _read_private_copy_source(destination, hashlib.sha256(content).hexdigest())
    else:
        _write_private_file(destination, content)
    observation = _handoff_observation(recovery_candidate or retained_original)
    revision = handoff_journal_advance(identity, revision, service, "recovery_create_intent", observation)
    if recovery_candidate is None:
        command = ["/usr/bin/docker", "compose", "--project-directory", str(WORKING_DIR),
                   "-p", plan["recovery_project"], "-f", str(destination), "create",
                   "--no-build", "--pull", "never", "--no-recreate", service]
        _run(command, app_version=plan["checkout_sha"], timeout=300)
        recovery_candidate = _handoff_picker_free_candidate(plan, service, running=False)
    else:
        recovery_candidate = _handoff_picker_free_candidate(plan, service)
    revision = handoff_journal_advance(identity, revision, service, "recovery_created",
                                       _handoff_observation(recovery_candidate))
    _handoff_validate_inputs(plan)
    revision = handoff_journal_advance(identity, revision, service, "recovery_start_intent",
                                       _handoff_observation(recovery_candidate))
    if not recovery_candidate.get("State", {}).get("Running"):
        _docker(["start", recovery_candidate["Id"]], timeout=60)
    recovery_candidate = _handoff_picker_free_candidate(plan, service, running=True)
    revision = handoff_journal_advance(identity, revision, service, "recovery_started",
                                       _handoff_observation(recovery_candidate))
    restored = _handoff_wait_picker_free_candidate(plan, service)
    if service == "api":
        _handoff_check_api(restored)
    else:
        api = _handoff_picker_free_candidate(plan, "api", running=True, healthy=True)
        _handoff_check_api(api)
    revision = handoff_journal_advance(identity, revision, service, "healthy", _handoff_observation(restored))
    return revision


def handoff_publish_runtime(identity: str, *, restoring: bool = False) -> dict:
    _assert_common_lock_held()
    plan, state, _ = handoff_journal_read(identity)
    expected_domain = "app-first-handoff-recovery-plan-v1" if restoring else "app-first-handoff-v1"
    if plan["domain"] != expected_domain or any(phase != "healthy" for phase in state["phases"].values()):
        raise BridgeError("handoff_publish_requires_healthy")
    _handoff_validate_inputs(plan)
    if restoring:
        if "picker_free_recovery_recipe" not in plan:
            raise BridgeError("handoff_recovery_recipe_required")
        _handoff_validate_picker_free_recovery_plan(plan)
    records, selected = [], {}
    for record in plan["sources"]:
        if record["retained"]:
            records.append(copy.deepcopy(record))
            continue
        service = record["service"]
        if restoring:
            original = _handoff_original(plan, service, retained=True, running=False)
            records.append(handoff_record(service, original, record["project"], retained=True))
            item = _handoff_picker_free_candidate(plan, service, running=True, healthy=True)
            records.append(handoff_record(service, item, plan["recovery_project"]))
            selected[service] = item
            candidate = _handoff_recovery_candidate(plan, service, parked=bool(plan["recovery"]["services"][service]["candidate"]))
            if candidate is not None:
                records.append(handoff_record(service, candidate, plan["project"], retained=True))
        else:
            retained = _handoff_original(plan, service, retained=True, running=False)
            records.append(handoff_record(service, retained, record["project"], retained=True))
            item = _handoff_candidate(plan, service, healthy=True)
            records.append(handoff_record(service, item, plan["project"]))
            selected[service] = item
        if _handoff_observation(item) != state["observations"][service]:
            raise BridgeError("handoff_publish_runtime_changed")
    records.sort(key=lambda record: record["id"])
    handoff_select(_handoff_read_items(records), records)
    _handoff_check_api(selected["api"])
    web_version = (plan.get("original_web_version", selected["web"]["Config"]["Labels"].get("io.pickyourpic.release", ""))
                   if restoring else plan["target_sha"])
    if not SHA_RE.fullmatch(web_version):
        raise BridgeError("handoff_web_version_unproven")
    projects = {record["service"]: record["project"] for record in records if not record["retained"]}
    context = _discover_context(selected=selected, expected_projects=projects)
    models = plan["recovery_models"] if restoring else plan["models"]
    for service in SERVICES:
        path = _handoff_journal_directory(identity) / ("final-" + service + ".json")
        content = json.dumps(_escape_compose(models[service]), sort_keys=True).encode()
        if os.path.lexists(path):
            validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
            _read_private_copy_source(path, hashlib.sha256(content).hexdigest())
        else:
            _write_private_file(path, content)
        if path not in context["paths"]:
            context["paths"].append(path)
        context["digests"][str(path)] = snapshot_sha256(path)
        context["sources"][service] = {"paths": [path], "workdir": WORKING_DIR, "config_hash": None}
        context["config_hashes"][service] = None
    context["handoff_selection_records"] = records
    pointer = BRIDGE_STATE / "active-base.json"
    context["base_pointer_digest"] = snapshot_sha256(pointer) if os.path.lexists(pointer) else None
    with tempfile.TemporaryDirectory(prefix="markina-handoff-final-", dir="/tmp") as directory:
        context = _prepare_compose_context(context, "inventory", plan["support_sha"], "", Path(directory))
        _prove_context(context)
        proof = {"version": 1, "domain": "app-runtime-transition-v1", "handoff": identity,
                 "support_sha": plan["support_sha"], "target_sha": plan["checkout_sha"] if restoring else plan["target_sha"],
                 "mode": "rollback" if restoring else "release", "runtime": adoption_runtime_binding(selected),
                 "models": {service: digest(model) for service, model in context["models"].items()},
                 "records": digest(records), "schema": "20261113_0126"}
        approval = plan["approval"] if restoring else identity
        _publish_runtime_base(context, context["models"], proof, approval, handoff_records=records)
    return {"checkout_sha": proof["target_sha"], "api_image_id": selected["api"]["Image"],
            "web_image_id": selected["web"]["Image"], "web_semantic_hash": context["semantic_hashes"]["web"],
            "web_version": web_version,
            "api_version": environment_map(selected["api"]["Config"].get("Env") or []).get("APP_VERSION", "")}


@contextmanager
def _handoff_proven_context(support_sha: str):
    if _git("rev-parse", "origin/main") != support_sha or _git("status", "--porcelain"):
        raise BridgeError("handoff_support_checkout_invalid")
    if _read_base_pointer() is None:
        raise BridgeError("handoff_adopted_base_required")
    context = _select_adopted_sources(_discover_context())
    with tempfile.TemporaryDirectory(prefix="markina-handoff-proof-", dir="/tmp") as directory:
        context = _prepare_compose_context(context, "inventory", support_sha, "", Path(directory))
        _prove_context(context)
        _handoff_check_api(context["containers"]["api"])
        version = environment_map(context["containers"]["api"]["Config"].get("Env") or []).get("APP_VERSION", "")
        if not SHA_RE.fullmatch(version):
            raise BridgeError("handoff_source_version_invalid")
        _git("merge-base", "--is-ancestor", version, support_sha)
        context["checkout_sha"] = _git("rev-parse", "HEAD")
        if not SHA_RE.fullmatch(context["checkout_sha"]):
            raise BridgeError("handoff_checkout_invalid")
        _git("merge-base", "--is-ancestor", context["checkout_sha"], support_sha)
        yield context
        _assert_sources_unchanged(context)


def _handoff_context_records(context: dict, *, require_witnesses: bool) -> list[dict]:
    records = _handoff_registered_records()
    if records is None:
        records = [handoff_record(service, item, context["projects"][service])
                   for service, item in context["containers"].items()]
    registry = handoff_witness_registry()
    if registry is None:
        if require_witnesses:
            raise BridgeError("handoff_witness_registration_required")
        return records
    cached = [record for record in records if record.get("witness")]
    if cached and sorted(cached, key=lambda r: r["id"]) != registry["witnesses"]:
        raise BridgeError("handoff_witness_set_changed")
    return [record for record in records if not record.get("witness")] + registry["witnesses"]


def _handoff_active_id() -> str | None:
    path = BRIDGE_STATE / "active-handoff.json"
    if not os.path.lexists(path):
        return None
    _validate_tree_no_symlink(path)
    _root_metadata(BRIDGE_STATE, directory=True, mode=0o700)
    validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
    value = json.loads(_read_private_copy_source(path, snapshot_sha256(path)))
    if set(value) != {"version", "identity"} or value.get("version") != 1 or not HASH_RE.fullmatch(value.get("identity", "")):
        raise BridgeError("handoff_active_pointer_invalid")
    handoff_journal_read(value["identity"])
    return value["identity"]


def _handoff_set_active(identity: str) -> None:
    _assert_common_lock_held()
    handoff_journal_read(identity)
    path = BRIDGE_STATE / "active-handoff.json"
    if os.path.lexists(path):
        _handoff_active_id()
        old = _read_private_copy_source(path, snapshot_sha256(path))
        _write_private_file(_handoff_journal_directory(identity) / "previous-active.json", old)
    staging = BRIDGE_STATE / (".active-handoff-" + identity + ".tmp")
    _write_private_file(staging, json.dumps({"version": 1, "identity": identity}, sort_keys=True).encode())
    _handoff_sync_directory(BRIDGE_STATE)
    os.replace(staging, path)
    _handoff_sync_directory(BRIDGE_STATE)


def _handoff_candidate_plan(args) -> dict:
    for name in ("app-in-flight.sha", "app-rollback-in-flight.sha", "web-in-flight.sha", "web-pending.identity"):
        if os.path.lexists(STATE_DIR / name):
            raise BridgeError("handoff_interrupted_operation_requires_recovery")
    with _handoff_proven_context(args.sha) as context:
        records = _handoff_context_records(context, require_witnesses=True)
        items = _handoff_read_items(records)
        if context["containers"]["api"]["Image"] != args.api_base_image_id:
            raise BridgeError("handoff_artifact_base_changed")
        for service in SERVICES:
            _handoff_assert_retained_name_free(handoff_retained_name(service, context["containers"][service]["Id"]))
        models = {service: replacement_document(service, context["models"][service], context["containers"][service],
                                                args.candidate_api_id if service == "api" else args.candidate_web_id,
                                                args.sha) for service in SERVICES}
        sources = dict(context["digests"])
        sources[str(BRIDGE_STATE / "handoff-witnesses.json")] = snapshot_sha256(BRIDGE_STATE / "handoff-witnesses.json")
        plan = handoff_plan(args.sha, args.sha, args.artifact_sha256, items, records, models,
                            context["models"], sources, context["environment_digest"], context["checkout_sha"])
        plan["original_web_version"] = _web_identity(context, args.sha).split()[0]
        plan["previous_handoff"] = _handoff_active_id()
        return plan


def _handoff_assert_retained_name_free(name: str) -> None:
    if not re.fullmatch(re.escape(PROJECT) + r"-retained-(api|web)-[0-9a-f]{64}", name):
        raise BridgeError("handoff_retained_name_invalid")
    if _docker(["ps", "-a", "--filter", "name=^/" + name + "$", "--format", "{{.ID}}"]).strip():
        raise BridgeError("handoff_retained_name_occupied")


def _handoff_archive_inputs(identity: str, plan: dict) -> None:
    directory = _handoff_journal_directory(identity)
    for index, (raw, checksum) in enumerate(sorted(plan["source_digests"].items())):
        content = _read_private_copy_source(Path(raw), checksum)
        _handoff_archive_file(directory / ("historical-" + str(index).zfill(4) + ".json"), content)
    _handoff_archive_file(directory / "original.env", _read_private_copy_source(ENV_FILE, plan["environment_digest"], max_size=16 * 1024 * 1024))
    _handoff_sync_directory(directory)


def _handoff_archive_file(path: Path, content: bytes) -> None:
    if os.path.lexists(path):
        validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
        _read_private_copy_source(path, hashlib.sha256(content).hexdigest(), max_size=16 * 1024 * 1024)
    else:
        _write_private_file(path, content)


def _handoff_live_recovery_inventory(support_sha: str) -> dict:
    if _git("rev-parse", "origin/main") != support_sha or _git("status", "--porcelain"):
        raise BridgeError("handoff_support_checkout_invalid")
    identity = _handoff_active_id()
    if identity is None:
        raise BridgeError("handoff_active_journal_missing")
    plan, _, _ = handoff_journal_read(identity)
    items = _handoff_read_items()
    images = {item["Image"]: json.loads(_docker(["image", "inspect", item["Image"]]))[0] for item in items}
    schema = None
    eligible = [item for item in items if item.get("Name") == "/" + PROJECT + "-api-1"
                and item.get("State", {}).get("Running")
                and item.get("State", {}).get("Health", {}).get("Status") == "healthy"]
    if len(eligible) > 1:
        raise BridgeError("handoff_recovery_api_ambiguous")
    if eligible:
        item = eligible[0]
        permitted = {record["id"] for record in plan["sources"] if record["service"] == "api" and not record["retained"]}
        allowed_projects = {plan["project"]}
        if plan.get("recovery_project"):
            allowed_projects.add(plan["recovery_project"])
        labels = item["Config"].get("Labels") or {}
        if item["Id"] not in permitted and (labels.get("com.docker.compose.project") not in allowed_projects
                or labels.get("com.docker.compose.service") != "api"):
            raise BridgeError("handoff_recovery_api_unproven")
        _handoff_check_api(item)
        schema = "20261113_0126"
    return handoff_recovery_inventory(identity, items, images, schema, support_sha=support_sha)


def _handoff_picker_free_runtime_receipt(support_sha: str, recovery_proof: dict) -> dict:
    identity = recovery_proof.get("handoff") if isinstance(recovery_proof, dict) else None
    if not isinstance(identity, str) or not HASH_RE.fullmatch(identity):
        raise BridgeError("handoff_picker_free_receipt_missing")
    plan, state, revision = handoff_journal_read(identity)
    if (plan.get("domain") != "app-first-handoff-recovery-plan-v1"
            or plan.get("support_sha") != support_sha
            or "picker_free_recovery_recipe" not in plan
            or recovery_proof.get("schema_status") != "verified"
            or recovery_proof.get("support_sha") != support_sha
            or state.get("phases") != {service: "healthy" for service in SERVICES}
            or _handoff_active_id() != identity):
        raise BridgeError("handoff_picker_free_receipt_missing")
    _handoff_validate_picker_free_recovery_plan(plan)

    pointer = _read_base_pointer()
    if pointer is None:
        raise BridgeError("handoff_picker_free_runtime_base_missing")
    _, manifest = _read_runtime_base(pointer)
    transition = manifest.get("proof")
    records = manifest.get("handoff_records")
    if (not isinstance(transition, dict)
            or set(transition) != {"version", "domain", "handoff", "support_sha", "target_sha", "mode",
                                   "runtime", "models", "records", "schema"}
            or transition.get("version") != 1 or transition.get("domain") != "app-runtime-transition-v1"
            or transition.get("handoff") != identity or transition.get("support_sha") != support_sha
            or transition.get("target_sha") != plan["checkout_sha"] or transition.get("mode") != "rollback"
            or transition.get("schema") != "20261113_0126"
            or manifest.get("approval") != plan.get("approval")
            or not isinstance(records, list) or transition.get("records") != digest(records)
            or transition.get("runtime") != manifest.get("runtime")
            or not isinstance(manifest.get("models"), dict) or set(manifest["models"]) != set(SERVICES)):
        raise BridgeError("handoff_picker_free_runtime_receipt_mismatch")

    items = _handoff_read_items()
    images = {item["Image"]: json.loads(_docker(["image", "inspect", item["Image"]]))[0] for item in items}
    observed_proof = handoff_recovery_inventory(identity, items, images, "20261113_0126", support_sha=support_sha)
    if digest(observed_proof) != digest(recovery_proof):
        raise BridgeError("handoff_picker_free_runtime_changed")
    by_id = {item["Id"]: item for item in items}
    active_records = [record for record in records if not record.get("retained")]
    if len(active_records) != len(SERVICES) or {record.get("service") for record in active_records} != set(SERVICES):
        raise BridgeError("handoff_picker_free_runtime_receipt_mismatch")
    selected, service_receipts = {}, {}
    for service in SERVICES:
        result = recovery_proof["services"][service]
        candidate = result.get("recovery_candidate")
        if (not isinstance(candidate, dict) or result.get("recovery_candidate_running") is not True
                or result.get("recovery_candidate_health") != "healthy"):
            raise BridgeError("handoff_picker_free_runtime_unhealthy")
        item = by_id.get(candidate.get("id"))
        if item is None or item.get("Image") != candidate.get("image"):
            raise BridgeError("handoff_picker_free_runtime_changed")
        if (item.get("State", {}).get("Running") is not True
                or item.get("State", {}).get("Status") != "running"
                or item.get("State", {}).get("Health", {}).get("Status") != "healthy"):
            raise BridgeError("handoff_picker_free_runtime_unhealthy")
        actual_record = handoff_record(service, item, plan["recovery_project"])
        if candidate != actual_record:
            raise BridgeError("handoff_picker_free_runtime_changed")
        if [record for record in active_records if record.get("service") == service] != [actual_record]:
            raise BridgeError("handoff_picker_free_runtime_receipt_mismatch")
        mounts = item.get("Mounts")
        if not isinstance(mounts, list):
            raise BridgeError("handoff_picker_free_runtime_mount_invalid")
        for mount in mounts:
            if not isinstance(mount, dict):
                raise BridgeError("handoff_picker_free_runtime_mount_invalid")
            if (_picker_mount_path_intersects(mount.get("Source"), PICKER_CONFIG_SOURCE)
                    or _picker_mount_path_intersects(mount.get("Destination"), PICKER_CONFIG_TARGET)):
                raise BridgeError("handoff_picker_free_runtime_picker_mount_present")
        host = item.get("HostConfig")
        if not isinstance(host, dict):
            raise BridgeError("handoff_picker_free_runtime_mount_invalid")
        for key, target_key in (("Binds", None), ("Mounts", "Target")):
            values = host.get(key) or []
            if not isinstance(values, list):
                raise BridgeError("handoff_picker_free_runtime_mount_invalid")
            for value in values:
                if key == "Binds":
                    if not isinstance(value, str):
                        raise BridgeError("handoff_picker_free_runtime_mount_invalid")
                    fields = value.split(":")
                    source, target = fields[0], fields[1] if len(fields) > 1 else None
                else:
                    if not isinstance(value, dict):
                        raise BridgeError("handoff_picker_free_runtime_mount_invalid")
                    source, target = value.get("Source"), value.get(target_key)
                if (_picker_mount_path_intersects(source, PICKER_CONFIG_SOURCE)
                        or _picker_mount_path_intersects(target, PICKER_CONFIG_TARGET)):
                    raise BridgeError("handoff_picker_free_runtime_picker_mount_present")

        model_content = json.dumps(_escape_compose(plan["recovery_models"][service]), sort_keys=True).encode()
        model_sha256 = hashlib.sha256(model_content).hexdigest()
        if manifest["models"].get(service) != model_sha256:
            raise BridgeError("handoff_picker_free_runtime_model_mismatch")
        selected[service] = item
        service_receipts[service] = {
            "container_id": item["Id"], "image_id": item["Image"], "health": "healthy",
            "running": True, "model_sha256": plan["recovery_model_sha256"][service],
            "picker_bind_removed": plan["picker_free_recovery_recipe"]["services"][service]["picker_bind_removed"],
        }
    if transition.get("runtime") != adoption_runtime_binding(selected):
        raise BridgeError("handoff_picker_free_runtime_receipt_mismatch")
    receipt = {
        "version": 1, "domain": "app-picker-free-runtime-receipt-v1", "handoff": identity,
        "revision": revision, "support_sha": support_sha,
        "recipe_sha256": plan["picker_free_recovery_recipe"]["sha256"],
        "runtime_base": pointer["base"], "runtime_manifest_sha256": pointer["manifest_sha256"],
        "runtime_pointer_sha256": snapshot_sha256(BRIDGE_STATE / "active-base.json"),
        "transition_proof_sha256": digest(transition), "recovery_inventory_sha256": digest(recovery_proof),
        "services": service_receipts,
    }
    return {**receipt, "receipt_sha256": digest(receipt)}


def _handoff_legacy_proof(support_sha: str, *, allow_marker_absent: bool = False) -> dict:
    if _handoff_active_id() is not None:
        raise BridgeError("handoff_legacy_recovery_not_applicable")
    for name in ("app-rollback-in-flight.sha", "web-in-flight.sha", "web-pending.identity"):
        if os.path.lexists(STATE_DIR / name):
            raise BridgeError("handoff_conflicting_operation")
    pointer_path = BRIDGE_STATE / "active-transition.json"
    _validate_tree_no_symlink(pointer_path)
    validate_snapshot_metadata(_root_metadata(pointer_path), allowed_owners={0}, root_only=True)
    pointer_hash = snapshot_sha256(pointer_path)
    pointer = json.loads(_read_private_copy_source(pointer_path, pointer_hash))
    if pointer.get("mode") != "release":
        raise BridgeError("handoff_legacy_transition_invalid")
    directory = _operation_directory("release", pointer["target_sha"], pointer["approval"])
    transition_path = directory / "transition.json"
    validate_snapshot_metadata(_root_metadata(transition_path), allowed_owners={0}, root_only=True)
    transition = json.loads(_read_private_copy_source(transition_path, pointer["sha256"]))
    if (transition.get("version") != 1 or transition.get("mode") != "release"
            or transition.get("target_sha") != pointer["target_sha"] or transition.get("approval") != pointer["approval"]
            or set(transition.get("candidates", {})) != set(SERVICES)):
        raise BridgeError("handoff_legacy_transition_invalid")
    manifest_path = directory / "manifest.json"
    _read_private_copy_source(manifest_path, transition["manifest_sha256"])
    saved = _read_manifest(directory)
    if saved.get("target_sha") != pointer["target_sha"] or saved.get("fingerprint") != pointer["approval"]:
        raise BridgeError("handoff_legacy_manifest_invalid")
    marker_present = os.path.lexists(STATE_DIR / "app-in-flight.sha")
    if marker_present:
        if _state_value("app-in-flight.sha") != pointer["target_sha"]:
            raise BridgeError("handoff_legacy_marker_changed")
    elif not allow_marker_absent:
        raise BridgeError("handoff_legacy_marker_required")
    with _handoff_proven_context(support_sha) as context:
        if adoption_runtime_binding(saved["containers"]) != adoption_runtime_binding(context["containers"]):
            raise BridgeError("handoff_legacy_originals_not_intact")
        if any(item["State"].get("Health", {}).get("Status") != "healthy" for item in context["containers"].values()):
            raise BridgeError("handoff_legacy_originals_unhealthy")
        api_version = environment_map(context["containers"]["api"]["Config"].get("Env") or []).get("APP_VERSION", "")
        web_version = context["containers"]["web"]["Config"]["Labels"].get("io.pickyourpic.release", "")
        if not SHA_RE.fullmatch(api_version) or api_version != web_version:
            raise BridgeError("handoff_legacy_checkout_unproven")
        _git("merge-base", "--is-ancestor", api_version, pointer["target_sha"])
        if context["checkout_sha"] not in {pointer["target_sha"], api_version}:
            raise BridgeError("handoff_legacy_checkout_changed")
        records = _handoff_context_records(context, require_witnesses=False)
        witnesses = handoff_witness_inventory(support_sha, _handoff_read_items(), records,
                                              context["digests"], context["environment_digest"])
        sources = dict(context["digests"])
        sources.update({str(pointer_path): pointer_hash, str(transition_path): pointer["sha256"],
                        str(manifest_path): transition["manifest_sha256"]})
        for service in SERVICES:
            path = directory / ("apply-" + service + ".compose.json")
            validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
            _read_private_copy_source(path, transition["candidates"][service])
            sources[str(path)] = transition["candidates"][service]
        return {"version": 1, "domain": "app-legacy-handoff-recovery-v1", "support_sha": support_sha,
                "interrupted_sha": pointer["target_sha"], "checkout_sha": context["checkout_sha"],
                "restore_checkout": api_version, "marker_present": marker_present,
                "runtime": adoption_runtime_binding(context["containers"]), "witnesses": witnesses["witnesses"],
                "source_digests": sources, "environment_digest": context["environment_digest"],
                "schema": "20261113_0126"}


def _handoff_legacy_ticket(approval: str) -> tuple[Path, dict | None]:
    if not HASH_RE.fullmatch(approval):
        raise BridgeError("handoff_legacy_approval_invalid")
    directory = BRIDGE_STATE / ("legacy-recovery-" + approval)
    if not os.path.lexists(directory):
        return directory, None
    _validate_tree_no_symlink(directory)
    _root_metadata(directory, directory=True, mode=0o700)
    path = directory / "prepared.json"
    validate_snapshot_metadata(_root_metadata(path), allowed_owners={0}, root_only=True)
    proof = json.loads(_read_private_copy_source(path, snapshot_sha256(path)))
    if digest(proof) != approval or proof.get("domain") != "app-legacy-handoff-recovery-v1":
        raise BridgeError("handoff_legacy_ticket_changed")
    return directory, proof


def _handoff_legacy_validate_prepared(args, directory: Path, proof: dict) -> None:
    if proof["support_sha"] != args.sha:
        raise BridgeError("handoff_legacy_support_changed")
    intent = directory / "marker-clear-intent.json"
    allow_absent = False
    if os.path.lexists(intent):
        validate_snapshot_metadata(_root_metadata(intent), allowed_owners={0}, root_only=True)
        saved = json.loads(_read_private_copy_source(intent, snapshot_sha256(intent)))
        if saved != {"approval": args.approval_fingerprint, "interrupted_sha": proof["interrupted_sha"], "checkout_sha": proof["restore_checkout"]}:
            raise BridgeError("handoff_legacy_intent_changed")
        allow_absent = True
    current = _handoff_legacy_proof(args.sha, allow_marker_absent=allow_absent)
    if current["checkout_sha"] not in {proof["checkout_sha"], proof["restore_checkout"]}:
        raise BridgeError("handoff_legacy_checkout_changed")
    current["checkout_sha"] = proof["checkout_sha"]
    current["marker_present"] = proof["marker_present"]
    if current != proof:
        raise BridgeError("handoff_legacy_runtime_changed")


def _handoff_legacy_cli(args) -> int:
    if args.operation == "handoff-legacy-recovery-inventory":
        proof = _handoff_legacy_proof(args.sha)
        print("legacy_recovery_fingerprint=" + digest(proof))
        print("checkout_sha=" + proof["restore_checkout"])
        print("interrupted_sha=" + proof["interrupted_sha"])
        return 0
    _assert_common_lock_held()
    directory, proof = _handoff_legacy_ticket(args.approval_fingerprint)
    if args.operation == "handoff-legacy-recovery-prepare":
        registry = handoff_witness_registry()
        if registry is None:
            raise BridgeError("handoff_witness_registration_required")
        if proof is None:
            proof = _handoff_legacy_proof(args.sha)
            if digest(proof) != args.approval_fingerprint or registry["witnesses"] != proof["witnesses"]:
                raise BridgeError("handoff_legacy_approval_mismatch")
            _ensure_root_bridge_directory()
            directory.mkdir(mode=0o700)
            _write_private_file(directory / "prepared.json", json.dumps(proof, sort_keys=True).encode())
            _handoff_sync_directory(directory)
        else:
            _handoff_legacy_validate_prepared(args, directory, proof)
        print("checkout_sha=" + proof["restore_checkout"])
        return 0
    if args.operation not in {"handoff-legacy-recovery-finalize", "handoff-legacy-recovery-proxy"} or proof is None:
        raise BridgeError("handoff_legacy_ticket_required")
    _handoff_legacy_validate_prepared(args, directory, proof)
    if _git("rev-parse", "HEAD") != proof["restore_checkout"]:
        raise BridgeError("handoff_legacy_checkout_not_restored")
    if args.operation == "handoff-legacy-recovery-proxy":
        _handoff_nginx()
        print("nginx_status=reloaded")
        return 0
    intent = directory / "marker-clear-intent.json"
    if not os.path.lexists(intent):
        _write_private_file(intent, json.dumps({"approval": args.approval_fingerprint,
                            "interrupted_sha": proof["interrupted_sha"], "checkout_sha": proof["restore_checkout"]}, sort_keys=True).encode())
        _handoff_sync_directory(directory)
    marker = STATE_DIR / "app-in-flight.sha"
    if os.path.lexists(marker):
        if _state_value("app-in-flight.sha") != proof["interrupted_sha"]:
            raise BridgeError("handoff_legacy_marker_changed")
        descriptor = os.open(STATE_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.unlink("app-in-flight.sha", dir_fd=descriptor)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    committed = directory / "committed.json"
    if not os.path.lexists(committed):
        _write_private_file(committed, json.dumps({"approval": args.approval_fingerprint,
                            "checkout_sha": proof["restore_checkout"], "schema": "20261113_0126"}, sort_keys=True).encode())
        _handoff_sync_directory(directory)
    print("legacy_recovery_status=healthy")
    print("checkout_sha=" + proof["restore_checkout"])
    return 0


def _handoff_nginx() -> None:
    """Test/reload only the same running Markina proxy with the approved bind."""
    _assert_common_lock_held()
    ids = _list_service_ids("nginx")
    if len(ids) != 1:
        raise BridgeError("nginx_container_count_invalid")
    item = json.loads(_docker(["inspect", ids[0]]))[0]
    labels = item.get("Config", {}).get("Labels") or {}
    if (item.get("Id") != ids[0] or labels.get("com.docker.compose.project") != PROJECT
            or labels.get("com.docker.compose.service") != "nginx" or not item.get("State", {}).get("Running")
            or item.get("NetworkSettings", {}).get("Ports") != {"80/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]}):
        raise BridgeError("handoff_nginx_identity_invalid")
    _docker(["exec", ids[0], "nginx", "-t"], timeout=30, max_output=65536)
    current = json.loads(_docker(["inspect", ids[0]]))[0]
    if (handoff_configuration(current) != handoff_configuration(item)
            or current.get("State", {}).get("StartedAt") != item.get("State", {}).get("StartedAt")
            or not current.get("State", {}).get("Running")
            or current.get("NetworkSettings", {}).get("Ports") != item["NetworkSettings"]["Ports"]):
        raise BridgeError("handoff_nginx_changed")
    _docker(["exec", ids[0], "nginx", "-s", "reload"], timeout=30, max_output=65536)


def _handoff_cli(args) -> int:
    operation = args.operation
    if operation.startswith("handoff-legacy-recovery-"):
        return _handoff_legacy_cli(args)
    if operation in {"handoff-witness-register", "handoff-prepare", "handoff-apply", "handoff-proxy", "handoff-recovery-prepare", "handoff-recovery-apply"}:
        _assert_common_lock_held()
    if _git("rev-parse", "origin/main") != args.sha or _git("status", "--porcelain"):
        raise BridgeError("handoff_support_checkout_invalid")
    if operation == "handoff-proxy":
        identity = _handoff_active_id()
        if identity is None:
            raise BridgeError("handoff_active_journal_missing")
        plan, state, _ = handoff_journal_read(identity)
        recovering = plan["domain"] == "app-first-handoff-recovery-plan-v1"
        approval = plan["approval"] if recovering else identity
        checkout = plan["checkout_sha"] if recovering else plan["target_sha"]
        marker = "app-rollback-in-flight.sha" if recovering else "app-in-flight.sha"
        if (approval != args.approval_fingerprint or plan["support_sha"] != args.sha
                or state["phases"] != {service: "healthy" for service in SERVICES}
                or _git("rev-parse", "HEAD") != checkout or _state_value(marker) != plan["target_sha"]):
            raise BridgeError("handoff_proxy_context_invalid")
        with _handoff_proven_context(args.sha) as context:
            if any(_handoff_observation(context["containers"][service]) != state["observations"][service] for service in SERVICES):
                raise BridgeError("handoff_proxy_runtime_changed")
            _handoff_nginx()
        print("nginx_status=reloaded")
        return 0
    if operation in {"handoff-witness-inventory", "handoff-witness-register"}:
        registry_before = handoff_witness_registry()
        with _handoff_proven_context(args.sha) as context:
            records = _handoff_context_records(context, require_witnesses=False)
            proof = handoff_witness_inventory(args.sha, _handoff_read_items(), records, context["digests"], context["environment_digest"])
            if operation == "handoff-witness-register":
                handoff_register_witnesses(proof, args.approval_fingerprint)
                registry = handoff_witness_registry()
            else:
                registry = handoff_witness_registry()
                if registry != registry_before:
                    raise BridgeError("handoff_witness_registry_changed")
            report = handoff_witness_inventory_report(proof, _handoff_read_items(),
                                                      registry_present=registry is not None)
            print("witness_fingerprint=" + report["fingerprint"])
            print("witness_registered=" + ("true" if registry is not None else "false"))
            print("active_count=" + str(len(report["active_ids"])))
            for identity in report["active_ids"]:
                print("active_id=" + identity)
            print("witness_count=" + str(len(report["witnesses"])))
            for record in report["witnesses"]:
                print("witness=" + record["id"] + "|" + record["name"] + "|" + record["image"])
                print("witness_attestation=" + "|".join((record["id"], record["name"], record["image"],
                                                         record["service"], record["configuration"],
                                                         record["lifecycle"],
                                                         "true" if record["registered"] else "false")))
        return 0
    if operation in {"handoff-inventory", "handoff-prepare"}:
        plan = _handoff_candidate_plan(args)
        identity = digest(plan)
        if operation == "handoff-prepare":
            if identity != args.approval_fingerprint:
                raise BridgeError("handoff_approval_mismatch")
            identity, _ = _handoff_prepare_journal(plan)
            _handoff_archive_inputs(identity, plan)
            if plan["previous_handoff"] != _handoff_active_id():
                raise BridgeError("handoff_previous_operation_changed")
            _handoff_set_active(identity)
        print("handoff_fingerprint=" + identity)
        print("handoff_project=" + plan["project"])
        print("checkout_sha=" + plan["checkout_sha"])
        return 0
    if operation == "handoff-apply":
        identity = _handoff_active_id()
        if identity is None or identity != args.approval_fingerprint:
            raise BridgeError("handoff_active_approval_mismatch")
        plan, _, revision = handoff_journal_read(identity)
        if (plan["support_sha"] != args.sha or plan["target_sha"] != args.sha
                or plan["bundle_sha256"] != args.artifact_sha256
                or plan["original_models"]["api"]["services"]["api"]["image"] != args.api_base_image_id
                or plan["services"]["api"]["candidate_image"] != args.candidate_api_id
                or plan["services"]["web"]["candidate_image"] != args.candidate_web_id):
            raise BridgeError("handoff_candidate_binding_changed")
        _ensure_mutation_context("release", args.sha)
        revision = handoff_execute_service(identity, revision, "api")
        handoff_execute_service(identity, revision, "web")
        receipt = handoff_publish_runtime(identity)
    elif operation in {"handoff-recovery-inventory", "handoff-recovery-prepare"}:
        proof = _handoff_live_recovery_inventory(args.sha)
        active_plan, _, _ = handoff_journal_read(proof["handoff"])
        current_reference = None
        if "picker_free_recovery_recipe" not in active_plan:
            current_reference = _handoff_current_reference(proof)
            baseline, observations = current_reference
            proof["current_reference_sha256"] = digest(baseline)
            for service in SERVICES:
                print(f"current_reference_{service}_image=" + observations[service]["original"]["image"])
        if operation == "handoff-recovery-prepare":
            identity, _ = handoff_recovery_prepare(proof, args.approval_fingerprint, current_reference=current_reference)
            _handoff_set_active(identity)
        print("recovery_fingerprint=" + digest(proof))
        print("schema_status=" + proof["schema_status"])
        print("interrupted_sha=" + proof["interrupted_sha"])
        plan, state, _ = handoff_journal_read(proof["handoff"])
        picker_free = (plan.get("domain") == "app-first-handoff-recovery-plan-v1"
                       and "picker_free_recovery_recipe" in plan
                       and state.get("phases") == {service: "healthy" for service in SERVICES})
        print("recovery_picker_free=" + ("true" if picker_free else "false"))
        if picker_free:
            receipt = _handoff_picker_free_runtime_receipt(args.sha, proof)
            print("recovery_recipe_sha256=" + receipt["recipe_sha256"])
            print("recovery_receipt_sha256=" + receipt["receipt_sha256"])
            print("recovery_active_base_id=" + receipt["runtime_base"])
            print("recovery_active_base_manifest_sha256=" + receipt["runtime_manifest_sha256"])
            print("recovery_active_base_pointer_sha256=" + receipt["runtime_pointer_sha256"])
            for service in SERVICES:
                item = receipt["services"][service]
                print(f"recovery_phase_{service}=healthy")
                print(f"recovery_container_{service}=" + item["container_id"])
                print(f"recovery_image_{service}=" + item["image_id"])
                print(f"recovery_health_{service}=healthy")
                print(f"recovery_running_{service}=true")
                print(f"recovery_picker_bind_removed_{service}=" +
                      ("true" if item["picker_bind_removed"] else "false"))
        return 0
    elif operation == "handoff-recovery-apply":
        identity = _handoff_active_id()
        if identity is None:
            raise BridgeError("handoff_active_journal_missing")
        plan, _, revision = handoff_journal_read(identity)
        if (plan.get("approval") != args.approval_fingerprint or plan["support_sha"] != args.sha
                or plan["domain"] != "app-first-handoff-recovery-plan-v1"):
            raise BridgeError("handoff_recovery_approval_mismatch")
        revision = handoff_recover_service(identity, revision, "api")
        handoff_recover_service(identity, revision, "web")
        receipt = handoff_publish_runtime(identity, restoring=True)
    else:
        raise BridgeError("handoff_operation_not_allowed")
    for key, value in receipt.items():
        print(key + "=" + value)
    print("handoff_status=healthy")
    return 0


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
    if context.get("adopted_base"):
        _record_transition(context, mode, target_sha, fingerprint, candidates)
    for service in SERVICES:
        destination = directory / f"apply-{service}.compose.json"
        command = ["/usr/bin/docker", "compose", "--project-directory", str(WORKING_DIR), "-p", PROJECT,
                   "-f", str(destination), "up", "-d", "--no-deps", "--no-build", "--pull", "never",
                   "--force-recreate", "--wait", "--wait-timeout", "120", service]
        _run(command, app_version=app_version, timeout=300)
    if context.get("adopted_base"):
        current = _discover_context()
        for service, item in current["containers"].items():
            image = json.loads(_docker(["image", "inspect", item["Image"]]))[0]
            if item["Image"] != candidates[service]["services"][service]["image"]:
                raise BridgeError("transition_result_image_mismatch")
            prove_service_model(service, candidates[service]["services"][service], candidates[service], item, image)
        proof = {"version": 1, "domain": "app-runtime-transition-v1", "target_sha": target_sha,
                 "mode": mode, "runtime": adoption_runtime_binding(current["containers"]),
                 "models": {s: digest(m) for s, m in candidates.items()}}
        _publish_runtime_base(current, candidates, proof, fingerprint)
        context["base_pointer_digest"] = snapshot_sha256(BRIDGE_STATE / "active-base.json")
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
    parser.add_argument("--mode", required=True, choices=("inventory", "release", "rollback-inventory", "rollback", "adopt"))
    parser.add_argument("--sha", required=True)
    parser.add_argument("--app-version", default="")
    parser.add_argument("--approval-fingerprint", default="")
    parser.add_argument("--source-fingerprint", default="")
    parser.add_argument("--artifact-sha256", default="")
    parser.add_argument("--api-base-image-id", default="")
    parser.add_argument("--candidate-api-id", default="")
    parser.add_argument("--candidate-web-id", default="")
    parser.add_argument("operation", choices=("compose", "hashes", "service-hash", "service-project", "web-identity", "sources-fingerprint", "assert-facial", "snapshot", "adoption-inventory", "adopt", *HANDOFF_OPERATIONS))
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
    if parsed.mode in {"release", "rollback", "adopt"} and not HASH_RE.fullmatch(parsed.approval_fingerprint):
        raise BridgeError("approval_fingerprint_required")
    if ((parsed.mode == "adopt") != (parsed.operation == "adopt")
            or parsed.operation == "adoption-inventory" and parsed.mode != "inventory"):
        raise BridgeError("adoption_mode_invalid")
    candidate_values = (parsed.artifact_sha256, parsed.api_base_image_id, parsed.candidate_api_id, parsed.candidate_web_id)
    if parsed.operation in HANDOFF_OPERATIONS:
        if parsed.mode != HANDOFF_OPERATIONS[parsed.operation] or parsed.app_version or parsed.source_fingerprint:
            raise BridgeError("handoff_mode_invalid")
        if parsed.operation in HANDOFF_CANDIDATE_OPERATIONS:
            if (not HASH_RE.fullmatch(parsed.artifact_sha256)
                    or any(not IMAGE_ID_RE.fullmatch(value) for value in candidate_values[1:])
                    or parsed.candidate_api_id == parsed.candidate_web_id):
                raise BridgeError("handoff_artifact_identity_invalid")
        elif any(candidate_values):
            raise BridgeError("handoff_artifact_arguments_not_allowed")
    elif any(candidate_values):
        raise BridgeError("handoff_artifact_arguments_not_allowed")
    parsed.args = parsed.args[1:] if parsed.args[:1] == ["--"] else parsed.args
    if parsed.operation == "compose":
        _classify_compose_args(parsed.args, parsed.mode)
    elif parsed.operation in {"service-hash", "service-project"}:
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
        if args.operation in HANDOFF_OPERATIONS:
            return _handoff_cli(args)
        if args.mode in {"rollback-inventory", "rollback"} and _handoff_registered_records() is not None:
            raise BridgeError("handoff_recovery_interface_required")
        if args.operation == "adopt":
            _assert_common_lock_held()
        context = _discover_context()
        if args.operation not in {"adopt", "adoption-inventory"}:
            try:
                context = _select_adopted_sources(context)
            except BridgeError as exc:
                if exc.code != "adoption_registry_runtime_mismatch" or args.mode not in {"rollback-inventory", "rollback"}:
                    raise
                context = _select_recovery_sources(context, args.mode, args.sha)
        with tempfile.TemporaryDirectory(prefix="markina-app-compose-bridge-", dir="/tmp") as temporary:
            context = _prepare_compose_context(context, args.mode, args.sha, args.approval_fingerprint,
                                               Path(temporary))
            if args.operation in {"adopt", "adoption-inventory"}:
                models, proof = _prepare_adoption(context, args.sha)
                fingerprint = digest(proof)
                if args.operation == "adopt":
                    if fingerprint != args.approval_fingerprint:
                        raise BridgeError("adoption_approval_mismatch")
                    _publish_runtime_base(context, models, proof, fingerprint)
                print("adoption_status=" + ("adopted" if args.operation == "adopt" else "ready"))
                print("adoption_fingerprint=" + fingerprint)
                _assert_sources_unchanged(context)
                return 0
            _prove_context(context)
            if args.operation == "compose":
                result = _execute_compose(context, args.mode, args.sha, args.app_version, args.args, args.approval_fingerprint)
            elif args.operation == "hashes":
                result = _hashes(context, args.app_version, verify_active=True)
            elif args.operation == "service-hash":
                result = context["semantic_hashes"][args.args[0]] + "\n"
            elif args.operation == "service-project":
                result = context.get("projects", {}).get(args.args[0], PROJECT) + "\n"
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
