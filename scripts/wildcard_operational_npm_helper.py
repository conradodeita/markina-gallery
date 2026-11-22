"""Entrada fixa interna ao NPM; só instala bundle, não recebe token ou comandos."""

import hashlib
import json
import os
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wildcard_operational_files import _private_directory, _read
from scripts.wildcard_operational_protocol import MAX_REQUEST, parse_request
from scripts.wildcard_operational_runtime import load_runtime

HELPER = Path("/data/pyp-wildcard-helper")
TARGET = Path("/data/pyp-wildcard-certificates")


def run(payload):
    import resource

    if os.name != "posix" or os.getuid() != 0:
        raise RuntimeError("helper_identity_invalid")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    load_runtime(HELPER)
    import cryptography

    from scripts.wildcard_operational_installer import DurableInstaller

    if cryptography.__version__ != "50.0.0" or not Path(
        cryptography.__file__
    ).is_relative_to(HELPER / "lib"):
        raise RuntimeError("isolated_runtime_required")
    fd = _private_directory(HELPER)
    try:
        trust = _read(fd, "trust.pem", 1048576)
    finally:
        os.close(fd)
    chain, key = parse_request(payload)
    context = ssl.create_default_context(cadata=trust.decode())

    def tls(host, *, head=False, deadline=None):
        deadline = deadline if deadline is not None else time.monotonic() + 4

        def remaining():
            available = deadline - time.monotonic()
            if available <= 0:
                raise TimeoutError()
            return min(available, 1.0)

        with (
            socket.create_connection(("127.0.0.1", 443), timeout=remaining()) as raw,
            context.wrap_socket(raw, server_hostname=host) as secure,
        ):
            fingerprint = hashlib.sha256(
                secure.getpeercert(binary_form=True)
            ).hexdigest()
            if not head:
                return fingerprint, None
            secure.sendall(
                f"HEAD / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode()
            )
            response = bytearray()
            while b"\r\n" not in response and len(response) < 4096:
                secure.settimeout(remaining())
                part = secure.recv(512)
                if not part:
                    break
                response.extend(part)
            status = int(bytes(response).split(b"\r\n", 1)[0].split()[1])
            return fingerprint, status

    references = {
        host: tls(host, head=True)
        for host in ("pickyourpic.com.br", "markina.pickyourpic.com.br")
    }
    if (
        references["pickyourpic.com.br"][1] != 404
        or references["markina.pickyourpic.com.br"][1] != 200
    ):
        raise RuntimeError("reference_host_changed")

    def probe(fingerprint):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if (
                    fingerprint is not None
                    and tls("certificate-check.pickyourpic.com.br", deadline=deadline)[
                        0
                    ]
                    != fingerprint
                ):
                    raise RuntimeError("wildcard_probe_failed")
                if any(
                    tls(host, head=True, deadline=deadline) != expected
                    for host, expected in references.items()
                ):
                    raise RuntimeError("reference_host_changed")
                return
            except (OSError, RuntimeError):
                time.sleep(0.1)
        raise RuntimeError("tls_probe_failed")

    def command(args):
        subprocess.run(
            ["/usr/sbin/nginx", *args],
            check=True,
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/sbin:/usr/bin:/bin", "LANG": "C.UTF-8"},
        )

    return DurableInstaller(
        TARGET, trust, lambda: command(["-t"]), lambda: command(["-s", "reload"]), probe
    ).install(chain, key)


if __name__ == "__main__":
    try:
        print(json.dumps(run(sys.stdin.buffer.read(MAX_REQUEST + 1))))
    except Exception:  # noqa: BLE001 — entrada privilegiada: nenhum PEM/erro bruto pode sair.
        print('{"error":"installation_failed"}')
        raise SystemExit(1) from None
