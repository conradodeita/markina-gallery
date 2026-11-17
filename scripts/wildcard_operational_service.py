"""Entradas de paths/ações fixas; sem instalação, registro ACME ou configuração."""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import stat
import struct
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wildcard_operational_bundle import validate_bundle
from scripts.wildcard_operational_custody import (
    CredentialVault,
    _directory,
    _private_directory,
    _read,
)
from scripts.wildcard_operational_gateway import NpmGateway
from scripts.wildcard_operational_issuer import CERT_NAME, CertbotIssuer
from scripts.wildcard_operational_protocol import MAX_REQUEST, handle_connection

CONFIG = Path("/etc/pyp-acme-issuer")
STATE = Path("/var/lib/pyp-acme-issuer")
RUNTIME = Path("/run/pyp-acme-issuer")
SOCKET = "/run/pyp-acme-installer/installer.sock"


class ServiceError(RuntimeError):
    pass


def root_public_file(name, limit=8192):
    directory = _directory(CONFIG)
    descriptor = None
    try:
        descriptor = os.open(
            name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) not in {0o400, 0o600, 0o644, 0o444}
            or not 0 < info.st_size <= limit
        ):
            raise ServiceError("approval_invalid")
        value = os.read(descriptor, limit + 1)
        if len(value) > limit:
            raise ServiceError("approval_invalid")
        return value
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)


def issuer_once():
    import grp
    import pwd

    user = pwd.getpwnam("pyp-acme")
    if os.getuid() == 0 or os.getuid() != user.pw_uid:
        raise ServiceError("issuer_identity_invalid")
    try:
        docker_group = grp.getgrnam("docker").gr_gid
    except KeyError:
        docker_group = None
    if docker_group is not None and docker_group in os.getgroups():
        raise ServiceError("issuer_privilege_invalid")
    approval = json.loads(root_public_file("issuer.json"))
    if (
        not isinstance(approval, dict)
        or set(approval) != {"reference", "key_id", "account", "trust_sha256"}
        or not re.fullmatch("[0-9a-f]{64}", approval["trust_sha256"])
    ):
        raise ServiceError("approval_invalid")
    trust = root_public_file("trust.pem", 1048576)
    if hashlib.sha256(trust).hexdigest() != approval["trust_sha256"]:
        raise ServiceError("trust_changed")
    credentials = Path(os.environ["CREDENTIALS_DIRECTORY"])
    if credentials != Path("/run/credentials/pyp-acme-issuer.service"):
        raise ServiceError("credential_source_invalid")
    vault = CredentialVault(STATE / "vault", RUNTIME, credentials, approval["key_id"])
    with vault.materialize(UUID(approval["reference"])) as credential:
        live = CertbotIssuer(STATE / "acme", RUNTIME, approval["account"]).issue(
            credential
        )
    values = []
    versions = []
    archive = (STATE / "acme/archive" / CERT_NAME).resolve(strict=True)
    for name, limit in (("fullchain", 65536), ("privkey", 16384)):
        source = (live / (name + ".pem")).resolve(strict=True)
        match = re.fullmatch(name + r"([0-9]+)\.pem", source.name)
        if source.parent != archive or match is None:
            raise ServiceError("bundle_source_invalid")
        versions.append(match[1])
        fd = _private_directory(archive)
        try:
            values.append(_read(fd, source.name, limit, public=name == "fullchain"))
        finally:
            os.close(fd)
    if versions[0] != versions[1]:
        raise ServiceError("bundle_source_invalid")
    fingerprint = validate_bundle(*values, trust)
    payload = json.dumps(
        {"v": 1, "fullchain": values[0].decode(), "private_key": values[1].decode()}
    ).encode()
    if len(payload) > MAX_REQUEST:
        raise ServiceError("bundle_size_invalid")
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(240)
        client.connect(SOCKET)
        client.sendall(struct.pack("!I", len(payload)) + payload)
        client.shutdown(socket.SHUT_WR)
        response = bytearray()
        while b"\n" not in response and len(response) < 4096:
            part = client.recv(512)
            if not part:
                break
            response.extend(part)
    receipt = json.loads(response)
    if receipt.get("ok") is not True or receipt.get("fingerprint") != fingerprint:
        raise ServiceError("installation_not_confirmed")
    return {"result": "installed", "fingerprint": fingerprint}


def helper():
    import pwd
    import resource

    if (
        os.getuid() != 0
        or os.environ.get("LISTEN_PID") != str(os.getpid())
        or os.environ.get("LISTEN_FDS") != "1"
    ):
        raise ServiceError("socket_activation_required")
    uid = pwd.getpwnam("pyp-acme").pw_uid
    if uid == 0:
        raise ServiceError("issuer_identity_invalid")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    operation = NpmGateway(json.loads(root_public_file("installer.json")))
    with socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        if listener.getsockname() != SOCKET:
            raise ServiceError("socket_source_invalid")
        while True:
            with listener.accept()[0] as connection:
                handle_connection(connection, uid, operation)


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in {"issuer", "helper"}:
            raise ServiceError("fixed_action_required")
        result = issuer_once() if sys.argv[1] == "issuer" else helper()
        if result is not None:
            print(json.dumps(result))
    except Exception:  # noqa: BLE001 — daemon/oneshot não divulga dados de exceções ou PEM.
        print('{"error":"operation_failed"}')
        raise SystemExit(1) from None
