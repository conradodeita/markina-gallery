"""Somente guest QEMU descartável com marcador e hardware virtual esperado."""

import hashlib
import json
import os
import pwd
import re
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from uuid import UUID
from zipfile import ZipFile

SHARE = Path("/mnt/pyp-lab")
STATE = Path("/var/lib/pyp-acme-issuer")
REF = UUID("cce37bb5-2e2c-497b-9339-179bf573b76c")
UNIT = "pyp-wildcard-credential-lab.service"
SYNTHETIC_TOKEN = "synthetic-cloudflare-token-" + "x" * 37
PHASES = {
    "worker-entered",
    "materialized",
    "temporary-cleaned",
    "source-key-denied",
    "swap-disabled",
    "nonroot",
    "argv-read",
    "argv-clear",
    "environment-read",
    "environment-clear",
    "logs-read",
    "logs-clear",
    "artifacts-read",
    "artifacts-clear",
    "receipt-written",
}


def record_phase(name):
    if name not in PHASES:
        raise RuntimeError("invalid_lab_phase")
    phase = STATE / "proof-phase"
    phase.write_text(name)
    phase.chmod(0o600)


def command(args, **kwargs):
    return subprocess.run(args, check=True, timeout=180, **kwargs)


def guard():
    if Path("/proc/1/comm").read_text().strip() != "systemd":
        raise RuntimeError("not_systemd_guest")
    if not Path("/run/pyp-wildcard-guest-lab").exists():
        raise RuntimeError("lab_marker_missing")


def guest_identity():
    if (
        os.name != "posix"
        or os.uname().machine != "aarch64"
        or socket.gethostname() != "pyp-synthetic-systemd-lab"
        or Path("/var/lib/cloud/data/instance-id").read_text().strip()
        != "pyp-wildcard-synthetic-20261108"
    ):
        raise RuntimeError("not_synthetic_qemu_guest")


def worker():
    guard()
    sys.path[:0] = [str(SHARE), "/opt/pyp-acme-issuer/lib"]
    from scripts.wildcard_operational_custody import CredentialVault

    record_phase("worker-entered")
    credentials = Path(os.environ["CREDENTIALS_DIRECTORY"])
    vault = CredentialVault(
        STATE / "vault", Path("/run/pyp-acme-issuer"), credentials, "guest-k1"
    )
    envelope = STATE / "vault" / f"{REF}.json"
    if not envelope.exists():
        vault.store(
            REF, SYNTHETIC_TOKEN, datetime.now(timezone.utc) + timedelta(hours=2)
        )
    with vault.materialize(REF) as path:
        match = re.fullmatch(
            r"dns_cloudflare_api_token = ([A-Za-z0-9_-]{64})\n", path.read_text()
        )
        assert match is not None
        token = match.group(1)
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700
    record_phase("materialized")
    assert not path.exists()
    record_phase("temporary-cleaned")
    assert not os.access("/etc/pyp-acme-issuer/private/envelope-key", os.R_OK)
    record_phase("source-key-denied")
    assert len(Path("/proc/swaps").read_text().splitlines()) == 1
    record_phase("swap-disabled")
    assert os.getuid() != 0
    record_phase("nonroot")
    process = Path("/proc") / str(os.getpid())
    argv = (process / "cmdline").read_bytes()
    record_phase("argv-read")
    assert token.encode() not in argv
    record_phase("argv-clear")
    environment = (process / "environ").read_bytes()
    record_phase("environment-read")
    assert token.encode() not in environment
    record_phase("environment-clear")
    artifacts = [STATE, Path("/run/pyp-acme-issuer")]
    artifact_bytes = b"\n".join(
        path.read_bytes()
        for root in artifacts
        for path in root.rglob("*")
        if path.is_file()
    )
    record_phase("artifacts-read")
    assert token.encode() not in artifact_bytes
    record_phase("artifacts-clear")
    receipt_path = STATE / "receipt.json"
    count = (
        json.loads(receipt_path.read_text())["invocations"]
        if receipt_path.exists()
        else 0
    )
    receipt = {
        "invocations": count + 1,
        "uid": os.getuid(),
        "loadcredential": True,
        "source_key_read_denied": True,
        "temporary_cleaned": True,
        "swap_entries": 0,
        "credential_mode": oct((credentials / "envelope-key").stat().st_mode & 0o777),
        "argv_clear": True,
        "environment_clear": True,
        "logs_clear": False,
        "artifacts_clear": True,
    }
    receipt_path.write_text(json.dumps(receipt))
    receipt_path.chmod(0o600)
    record_phase("receipt-written")


def prepare():
    guest_identity()
    if os.getuid() != 0 or not Path("/var/lib/cloud/instance").exists():
        raise RuntimeError("not_cloud_guest")
    SHARE.mkdir(parents=True, exist_ok=True)
    command(
        [
            "mount",
            "-t",
            "9p",
            "-o",
            "trans=virtio,version=9p2000.L,ro",
            "pyp-lab",
            str(SHARE),
        ]
    )
    Path("/run/pyp-wildcard-guest-lab").touch(mode=0o600)
    guard()
    version = command(["systemd", "--version"], capture_output=True, text=True).stdout
    assert version.startswith("systemd 249 ")
    assert os.uname().machine == "aarch64"
    assert not any(
        line.split()[1] == "00000000"
        for line in Path("/proc/net/route").read_text().splitlines()[1:]
    )
    command(
        [
            "useradd",
            "--system",
            "--no-create-home",
            "--shell",
            "/usr/sbin/nologin",
            "pyp-acme",
        ]
    )
    user = pwd.getpwnam("pyp-acme")
    for path in (
        Path("/etc/pyp-acme-issuer"),
        Path("/etc/pyp-acme-issuer/private"),
        STATE,
        STATE / "vault",
        Path("/opt/pyp-acme-issuer/lib"),
    ):
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
    Path("/opt/pyp-acme-issuer").chmod(0o755)
    Path("/opt/pyp-acme-issuer/lib").chmod(0o755)
    for path in (STATE, STATE / "vault"):
        os.chown(path, user.pw_uid, user.pw_gid)
    key = Path("/etc/pyp-acme-issuer/private/envelope-key")
    key.write_bytes(os.urandom(32))
    key.chmod(0o400)
    # A prova do loader só precisa da cifra; extrair três wheels evita resolver
    # e instalar toda a árvore Certbot sob emulação. Hashes são os do lock validado.
    packages = json.loads((SHARE / "dependency-manifest.json").read_text())["packages"]
    for package in packages:
        if package["name"].lower() not in {"cryptography", "cffi", "pycparser"}:
            continue
        wheel = SHARE / "wheels" / package["url"].rsplit("/", 1)[1]
        assert hashlib.sha256(wheel.read_bytes()).hexdigest() == package["sha256"]
        with ZipFile(wheel) as archive:
            for entry in archive.infolist():
                name = PurePosixPath(entry.filename)
                assert not name.is_absolute() and ".." not in name.parts
                target = Path("/opt/pyp-acme-issuer/lib") / entry.filename
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("xb") as output:
                        output.write(archive.read(entry))
    unit = """[Unit]
Description=Pick-your-Pic synthetic LoadCredential proof
[Service]
Type=oneshot
User=pyp-acme
Group=pyp-acme
LoadCredential=envelope-key:/etc/pyp-acme-issuer/private/envelope-key
RuntimeDirectory=pyp-acme-issuer
RuntimeDirectoryMode=0700
Environment=PYTHONPATH=/mnt/pyp-lab:/opt/pyp-acme-issuer/lib
ExecStart=/usr/bin/python3 /mnt/pyp-lab/scripts/wildcard_systemd_guest.py worker
UMask=0077
LimitCORE=0
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
InaccessiblePaths=-/run/docker.sock -/var/run/docker.sock
ReadWritePaths=/var/lib/pyp-acme-issuer /run/pyp-acme-issuer
RestrictAddressFamilies=AF_UNIX
MemorySwapMax=0
"""
    Path("/etc/systemd/system/" + UNIT).write_text(unit)
    command(["systemctl", "daemon-reload"])
    try:
        command(["systemctl", "start", UNIT])
        command(["systemctl", "start", UNIT])
    except subprocess.CalledProcessError:
        phase = STATE / "proof-phase"
        value = phase.read_text().strip() if phase.is_file() else "before-worker"
        print("PYP_GUEST_WORKER_FAILED_AT=" + value, flush=True)
        raise
    verify_logs_and_mark(expected_invocations=2)
    Path("/var/lib/pyp-first-boot-id").write_text(
        Path("/proc/sys/kernel/random/boot_id").read_text()
    )
    finish = """[Unit]
Description=Finish isolated Pick-your-Pic proof after guest reboot
After=local-fs.target
ConditionPathExists=/var/lib/pyp-first-boot-id
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /var/lib/pyp-wildcard-bootstrap.py finish
[Install]
WantedBy=multi-user.target
"""
    Path("/etc/systemd/system/pyp-wildcard-finish.service").write_text(finish)
    command(["systemctl", "daemon-reload"])
    command(["systemctl", "enable", "pyp-wildcard-finish.service"])
    Path("/var/lib/pyp-wildcard-prepared").touch(mode=0o600)
    print("PYP_GUEST_READY_FOR_REBOOT", flush=True)


def finish():
    guest_identity()
    if (
        os.getuid() != 0
        or Path("/proc/sys/kernel/random/boot_id").read_text()
        == Path("/var/lib/pyp-first-boot-id").read_text()
    ):
        raise RuntimeError("reboot_not_verified")
    SHARE.mkdir(parents=True, exist_ok=True)
    command(
        [
            "mount",
            "-t",
            "9p",
            "-o",
            "trans=virtio,version=9p2000.L,ro",
            "pyp-lab",
            str(SHARE),
        ]
    )
    Path("/run/pyp-wildcard-guest-lab").touch(mode=0o600)
    command(["systemctl", "start", UNIT])
    result = verify_logs_and_mark(expected_invocations=3)
    result.update(
        {
            "result": "passed",
            "systemd": "249",
            "arch": os.uname().machine,
            "guest_reboot_verified": True,
            "external_network": False,
        }
    )
    with open("/dev/ttyAMA0", "w") as console:
        console.write("PYP_SYSTEMD_RESULT=" + json.dumps(result) + "\n")
        console.flush()
    command(["systemctl", "poweroff", "--no-block"])


def verify_logs_and_mark(expected_invocations):
    receipt_path = STATE / "receipt.json"
    result = json.loads(receipt_path.read_text())
    assert result["invocations"] == expected_invocations
    journal = command(
        ["journalctl", "--unit", UNIT, "--output=cat", "--no-pager"],
        capture_output=True,
    ).stdout
    assert SYNTHETIC_TOKEN.encode() not in journal
    result["logs_clear"] = True
    receipt_path.write_text(json.dumps(result))
    receipt_path.chmod(0o600)
    record_phase("logs-clear")
    return result


if __name__ == "__main__":
    {"prepare": prepare, "worker": worker, "finish": finish}[sys.argv[1]]()
