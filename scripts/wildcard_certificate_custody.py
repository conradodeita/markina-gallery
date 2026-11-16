"""Protótipo POSIX exclusivamente sintético; sem CLI, rede ou executor privilegiado."""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization

from backend.app.integration_secrets import (
    IntegrationCipher,
    IntegrationSecretError,
    SecretEnvelope,
)

HOST = "*.pickyourpic.com.br"
MARKER = "pyp-wildcard-synthetic-only-v1"
NAMESPACE = UUID("ba7788ed-568c-46db-b81b-870568473901")


class CustodyError(RuntimeError):
    """Somente códigos sanitizados; nunca incluir entrada ou exceção original."""


def lab_root(root: Path) -> Path:
    if os.name != "posix" or root.is_symlink() or not root.is_absolute():
        raise CustodyError("lab_boundary")
    if root.resolve() != root or (root / ".pyp-wildcard-lab").is_symlink():
        raise CustodyError("lab_boundary")
    marker = root / ".pyp-wildcard-lab"
    if not marker.is_file() or marker.read_text() != MARKER:
        raise CustodyError("lab_boundary")
    if root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise CustodyError("lab_permissions")
    return root


def private_write(path: Path, value: bytes):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
        output.write(value)
        output.flush()
        os.fsync(output.fileno())


class SyntheticVault:
    def __init__(self, root: Path, key: bytes):
        self.root = lab_root(root)
        self.cipher = IntegrationCipher.from_explicit_context(
            environment="wildcard-dns-lab-v1", secret_environment="wildcard-dns-lab-v1",
            active_key_id="synthetic-only", keys={"synthetic-only": key},
        )

    def store(self, ref: UUID, token: str, expires: datetime):
        if not isinstance(ref, UUID) or not re.fullmatch(r"synthetic-[a-zA-Z0-9_-]{1,120}", token):
            raise CustodyError("synthetic_only")
        value = json.dumps({"token": token, "expires": expires.timestamp()})
        envelope = self.cipher.encrypt(value, tenant_id=NAMESPACE, credential_id=ref)
        private_write(self.root / f"{ref}.json", json.dumps(envelope.payload()).encode())

    @contextmanager
    def materialize(self, ref: UUID):
        try:
            lab_root(self.root)
            if not isinstance(ref, UUID):
                raise TypeError()
            source = self.root / f"{ref}.json"
            if source.is_symlink() or source.stat().st_mode & 0o077 or source.stat().st_size > 4096:
                raise ValueError()
            envelope = SecretEnvelope.from_payload(json.loads(source.read_bytes()))
            value = json.loads(self.cipher.decrypt(envelope, tenant_id=NAMESPACE, credential_id=ref))
            if value["expires"] <= datetime.now(timezone.utc).timestamp():
                raise ValueError()
            if not re.fullmatch(r"synthetic-[a-zA-Z0-9_-]{1,120}", value["token"]):
                raise ValueError()
        except (ValueError, TypeError, KeyError, OSError, IntegrationSecretError, CustodyError):
            raise CustodyError("credential_unavailable") from None
        with tempfile.TemporaryDirectory(prefix="credential-", dir=self.root) as temporary:
            os.chmod(temporary, 0o700)
            path = Path(temporary) / "cloudflare.ini"
            private_write(path, f"dns_cloudflare_api_token = {value['token']}\n".encode())
            try:
                yield path
            finally:
                path.unlink(missing_ok=True)


def validate_bundle(chain: bytes, key: bytes, trust: bytes) -> str:
    try:
        if len(chain) > 65536 or len(key) > 16384:
            raise ValueError()
        certificates = x509.load_pem_x509_certificates(chain)
        anchor = x509.load_pem_x509_certificate(trust)
        if len(certificates) != 2 or certificates[1] != anchor:
            raise ValueError()
        leaf = certificates[0]
        leaf.verify_directly_issued_by(anchor)
        anchor.verify_directly_issued_by(anchor)
        now = datetime.now(timezone.utc)
        if not anchor.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError()
        if leaf.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError()
        if not (anchor.not_valid_before_utc <= now < anchor.not_valid_after_utc):
            raise ValueError()
        if not (leaf.not_valid_before_utc <= now and leaf.not_valid_after_utc > now + timedelta(days=7)):
            raise ValueError()
        san = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        if len(san) != 1 or san.get_values_for_type(x509.DNSName) != [HOST]:
            raise ValueError()
        private_key = serialization.load_pem_private_key(key, password=None)
        encoding = (serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        if private_key.public_key().public_bytes(*encoding) != leaf.public_key().public_bytes(*encoding):
            raise ValueError()
        return sha256(leaf.public_bytes(serialization.Encoding.DER)).hexdigest()
    except (ValueError, TypeError, InvalidSignature, UnsupportedAlgorithm, x509.ExtensionNotFound):
        raise CustodyError("bundle_invalid") from None


class SyntheticInstaller:
    """Destino fixado pelo operador do laboratório; callbacks não aceitam shell/caminho."""

    def __init__(self, root: Path, trust: bytes, check_config, reload_service, probe):
        self.root = lab_root(root)
        self.trust = trust
        self.check_config, self.reload_service, self.probe = check_config, reload_service, probe

    def _target(self, name):
        link = self.root / name
        if not link.is_symlink():
            if link.exists():
                raise CustodyError("unsafe_pointer")
            return None
        target = os.readlink(link)
        if not re.fullmatch(r"release-[0-9a-f]{64}", target):
            raise CustodyError("unsafe_pointer")
        if (self.root / target).is_symlink() or not (self.root / target).is_dir():
            raise CustodyError("unsafe_pointer")
        return target

    def _point(self, name, target):
        link = self.root / name
        if target is None:
            link.unlink(missing_ok=True)
            return
        temp = self.root / f".{name}-next"
        temp.symlink_to(target)
        os.replace(temp, link)

    def install(self, chain: bytes, key: bytes):
        import fcntl

        lab_root(self.root)
        if (self.root / ".install.lock").is_symlink():
            raise CustodyError("unsafe_pointer")
        with (self.root / ".install.lock").open("a") as lock:
            os.chmod(lock.name, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            fingerprint = validate_bundle(chain, key, self.trust)
            target = f"release-{fingerprint}"
            previous = self._target("current")
            release = self.root / target
            if release.is_symlink():
                raise CustodyError("release_exists")
            if release.exists():
                for name, expected in (("fullchain.pem", chain), ("privkey.pem", key)):
                    path = release / name
                    if path.is_symlink() or path.stat().st_mode & 0o077 or path.read_bytes() != expected:
                        raise CustodyError("release_invalid")
            else:
                release.mkdir(mode=0o700)
                private_write(release / "fullchain.pem", chain)
                private_write(release / "privkey.pem", key)
            if previous == target:
                return {"fingerprint": fingerprint, "replayed": True}
            self._point("current", target)
            try:
                self.check_config()
                self.reload_service()
                self.probe(fingerprint)
            except Exception:  # noqa: BLE001 — fronteira de callback; sanitiza e restaura antes de falhar.
                self._point("current", previous)
                try:
                    if previous:
                        self.check_config()
                        self.reload_service()
                        self.probe(previous.removeprefix("release-"))
                except Exception:  # noqa: BLE001 — falha do callback de recuperação nunca expõe entrada.
                    raise CustodyError("recovery_failed") from None
                raise CustodyError("installation_failed") from None
            self._point("previous", previous)
            return {"fingerprint": fingerprint, "replayed": False}


def renew_synthetic(vault, ref, transport, installer):
    """Sem implementação de transporte real; teste injeta emissão sintética."""
    try:
        with vault.materialize(ref) as credential_path:
            chain, key = transport(credential_path)
        return installer.install(chain, key)
    except CustodyError:
        raise
    except Exception:  # noqa: BLE001 — transporte injetado não pode vazar credenciais na exceção.
        raise CustodyError("issuance_failed") from None
