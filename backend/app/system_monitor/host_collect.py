"""Coletor Linux opcional, stdlib, sem instalação/daemon/privilégios implícitos."""
import argparse
import json
import os
import re
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def counters(proc, interface=None, device=None):
    values = {}
    cpu = (proc / "stat").read_text().splitlines()[0].split()
    ticks = list(map(int, cpu[1:9]))  # guest already included in user/nice
    values["cpu_total"] = sum(ticks)
    values["cpu_idle"] = ticks[3] + ticks[4]
    if interface:
        for line in (proc / "net/dev").read_text().splitlines():
            name, separator, data = line.partition(":")
            if separator and name.strip() == interface:
                fields = data.split()
                values.update(net_in=int(fields[0]), net_out=int(fields[8]))
    if device:
        for line in (proc / "diskstats").read_text().splitlines():
            fields = line.split()
            if len(fields) >= 14 and fields[2] == device:
                values.update(io_read=int(fields[5]) * 512, io_write=int(fields[9]) * 512,
                              io_busy=int(fields[12]))
    return values


def rates(first, second, seconds):
    result = {}
    total = second["cpu_total"] - first["cpu_total"]
    idle = second["cpu_idle"] - first["cpu_idle"]
    result["cpu_percent"] = 100.0 * (total - idle) / total if total > 0 and 0 <= idle <= total else None
    for counter, field in (("net_in", "network_in_bytes_per_second"),
                           ("net_out", "network_out_bytes_per_second"),
                           ("io_read", "io_read_bytes_per_second"),
                           ("io_write", "io_write_bytes_per_second"),
                           ("io_busy", "io_busy_percent")):
        delta = second.get(counter, -1) - first.get(counter, -1)
        value = delta / seconds if counter in first and counter in second and delta >= 0 and seconds > 0 else None
        result[field] = min(100.0, value / 10) if counter == "io_busy" and value is not None else value
    return result


def collect(filesystem, scope, interface=None, device=None, *, proc=Path("/proc"), sleep=time.sleep, clock=time.monotonic):
    first = counters(proc, interface, device)
    started = clock()
    sleep(1)
    second = counters(proc, interface, device)
    result = rates(first, second, clock() - started)
    memory = {}
    for line in (proc / "meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in {"MemTotal", "MemAvailable"}:
            memory[key] = int(value.split()[0]) * 1024
    usage = shutil.disk_usage(filesystem)
    result.update(schema_version=1, source="linux_procfs", scope=scope,
                  collected_at=datetime.now(timezone.utc).isoformat(),
                  memory_total_bytes=memory.get("MemTotal"), memory_available_bytes=memory.get("MemAvailable"),
                  disk_total_bytes=usage.total, disk_free_bytes=usage.free)
    return result


def atomic_write(path, payload):
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix=".monitor-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--filesystem", required=True)
    parser.add_argument("--scope", required=True, choices=("host", "container"))
    parser.add_argument("--interface")
    parser.add_argument("--device")
    args = parser.parse_args()
    for name in (args.interface, args.device):
        if name and not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,64}", name):
            parser.error("Identificador inválido.")
    try:
        atomic_write(args.output, collect(args.filesystem, args.scope, args.interface, args.device))
    except (OSError, ValueError, IndexError):
        parser.exit(1, "Coleta indisponível; snapshot anterior preservado.\n")


if __name__ == "__main__":
    main()
