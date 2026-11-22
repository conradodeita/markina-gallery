"""Cofre POSIX para o emissor; sem CLI, rede, Docker ou instalação automática."""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from backend.app.integration_secrets import (
    IntegrationCipher,
    IntegrationSecretError,
    SecretEnvelope,
)
from scripts.wildcard_operational_files import (
    CredentialError,
    _directory,
    _private_directory,
    _read,
    _write,
)

CONTEXT = "pyp-wildcard-operational-v1"
NAMESPACE = UUID("2805fab3-15b4-441d-b8de-a6026987af9c")


def _token(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", value):
        raise CredentialError("credential_unavailable")
    return value


class CredentialVault:
    """Leitura da cópia privada de LoadCredential, não da chave fonte root-only.

    Caminhos são ligados pelo operador confiável na construção, não por pedidos
    remotos. O módulo não descobre credenciais lendo variáveis de ambiente.
    """

    def __init__(self, vault: Path, runtime: Path, credentials: Path, key_id: str):
        self.vault, self.runtime = vault, runtime
        try:
            vault_fd = _private_directory(vault)
            os.close(vault_fd)
            runtime_fd = _private_directory(runtime)
            os.close(runtime_fd)
            credentials_fd = _directory(credentials)
            try:
                key = _read(credentials_fd, "envelope-key", 32, credential=True)
            finally:
                os.close(credentials_fd)
            self.cipher = IntegrationCipher.from_explicit_context(
                environment=CONTEXT,
                secret_environment=CONTEXT,
                active_key_id=key_id,
                keys={key_id: key},
            )
        except (
            OSError,
            ValueError,
            TypeError,
            IntegrationSecretError,
            CredentialError,
        ):
            raise CredentialError("credential_unavailable") from None

    def store(self, ref: UUID, token: str, expires: datetime):
        try:
            if not isinstance(ref, UUID) or expires.tzinfo is None:
                raise ValueError()
            value = json.dumps({"token": _token(token), "expires": expires.timestamp()})
            envelope = self.cipher.encrypt(
                value, tenant_id=NAMESPACE, credential_id=ref
            )
            fd = _private_directory(self.vault)
            try:
                _write(fd, f"{ref}.json", json.dumps(envelope.payload()).encode())
            finally:
                os.close(fd)
        except (
            OSError,
            ValueError,
            TypeError,
            IntegrationSecretError,
            CredentialError,
        ):
            raise CredentialError("credential_unavailable") from None

    @contextmanager
    def materialize(self, ref: UUID):
        try:
            if not isinstance(ref, UUID):
                raise TypeError()
            fd = _private_directory(self.vault)
            try:
                payload = json.loads(_read(fd, f"{ref}.json", 4096))
            finally:
                os.close(fd)
            value = json.loads(
                self.cipher.decrypt(
                    SecretEnvelope.from_payload(payload),
                    tenant_id=NAMESPACE,
                    credential_id=ref,
                )
            )
            if (
                set(value) != {"token", "expires"}
                or not isinstance(value["expires"], (float, int))
                or not datetime.now(timezone.utc).timestamp()
                < value["expires"]
                < float("inf")
            ):
                raise ValueError()
            token = _token(value["token"])
            runtime_fd = _private_directory(self.runtime)
            os.close(runtime_fd)
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            IntegrationSecretError,
            CredentialError,
        ):
            raise CredentialError("credential_unavailable") from None
        with tempfile.TemporaryDirectory(
            prefix="credential-", dir=self.runtime
        ) as temporary:
            directory = Path(temporary)
            fd = _private_directory(directory)
            try:
                _write(
                    fd,
                    "cloudflare.ini",
                    f"dns_cloudflare_api_token = {token}\n".encode(),
                )
                yield directory / "cloudflare.ini"
            finally:
                try:
                    os.unlink("cloudflare.ini", dir_fd=fd)
                except FileNotFoundError:
                    pass
                finally:
                    os.close(fd)
