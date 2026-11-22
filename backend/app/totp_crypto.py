"""Envelope TOTP separado das chaves de integração, fora do banco de dados."""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import secrets
from collections.abc import Mapping
from types import MappingProxyType
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_PREFIX = "totp:v1:"
_KEY_ID = re.compile(r"[A-Za-z0-9_-]{1,48}\Z")
_MESSAGE = "Proteção do autenticador temporariamente indisponível."


class TotpSecretError(RuntimeError):
    """Falha sanitizada de chave, envelope ou contexto TOTP."""

    def __init__(self) -> None:
        super().__init__(_MESSAGE)


def legacy_totp_dual_write_enabled() -> bool:
    """Lê a janela legada explicitamente; configuração inválida falha fechada."""
    value = os.environ.get("ADMIN_TOTP_LEGACY_DUAL_WRITE", "false")
    if value == "true":
        return True
    if value == "false":
        return False
    raise TotpSecretError()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


class TotpSecretCipher:
    """Cifra segredos com AES-GCM e AAD vinculada ao ambiente e administrador."""

    def __init__(self, *, environment: str, active_key_id: str, keys: Mapping[str, bytes]):
        if (not isinstance(environment, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", environment)
                or not isinstance(active_key_id, str) or not _KEY_ID.fullmatch(active_key_id)
                or not isinstance(keys, Mapping) or not 1 <= len(keys) <= 16):
            raise TotpSecretError()
        copied: dict[str, bytes] = {}
        try:
            for key_id, key in keys.items():
                if not isinstance(key_id, str) or not _KEY_ID.fullmatch(key_id):
                    raise ValueError()
                if not isinstance(key, bytes) or len(key) != 32:
                    raise ValueError()
                copied[key_id] = key
        except (TypeError, ValueError):
            raise TotpSecretError() from None
        if active_key_id not in copied:
            raise TotpSecretError()
        self.environment = environment
        self.active_key_id = active_key_id
        self._keys = MappingProxyType(copied)

    @classmethod
    def from_environment(cls) -> TotpSecretCipher:
        try:
            environment = os.environ.get("APP_ENV", "development").strip()
            key_environment = os.environ["ADMIN_TOTP_SECRET_ENV"]
            active_key_id = os.environ["ADMIN_TOTP_ACTIVE_KEY_ID"]
            raw = json.loads(os.environ["ADMIN_TOTP_KEYS"], object_pairs_hook=_unique_pairs)
            if not isinstance(raw, dict):
                raise TypeError()
            keys = {key_id: base64.b64decode(value, validate=True) for key_id, value in raw.items()}
            if key_environment != environment:
                raise ValueError()
            return cls(environment=environment, active_key_id=active_key_id, keys=keys)
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            raise TotpSecretError() from None

    @staticmethod
    def _aad(environment: str, admin_id: UUID, key_id: str, context: str | None = None) -> bytes:
        if not isinstance(admin_id, UUID):
            raise TotpSecretError()
        payload = {"environment": environment, "key_id": key_id, "purpose": "admin-totp", "v": 1,
                   "admin_id": str(admin_id)}
        if context is not None:
            if not isinstance(context, str) or not 1 <= len(context) <= 512:
                raise TotpSecretError()
            payload["context"] = context
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def encrypt(self, secret: str, *, admin_id: UUID, context: str | None = None) -> str:
        if not isinstance(secret, str) or not secret or len(secret) > 128:
            raise TotpSecretError()
        nonce = secrets.token_bytes(12)
        aad = self._aad(self.environment, admin_id, self.active_key_id, context)
        ciphertext = AESGCM(self._keys[self.active_key_id]).encrypt(
            nonce, secret.encode("utf-8"), aad
        )
        return ":".join((
            "totp", "v1", self.active_key_id,
            base64.urlsafe_b64encode(nonce).decode("ascii").rstrip("="),
            base64.urlsafe_b64encode(ciphertext).decode("ascii").rstrip("="),
        ))

    def decrypt(self, envelope: str, *, admin_id: UUID, context: str | None = None) -> str:
        try:
            parts = envelope.split(":")
            if len(parts) != 5 or parts[:2] != ["totp", "v1"]:
                raise ValueError()
            _, _, key_id, nonce_text, ciphertext_text = parts
            if not _KEY_ID.fullmatch(key_id) or key_id not in self._keys:
                raise ValueError()
            if (not nonce_text or not ciphertext_text
                    or re.search(r"[^A-Za-z0-9_-]", nonce_text + ciphertext_text)):
                raise ValueError()
            nonce = base64.b64decode(
                nonce_text + "=" * (-len(nonce_text) % 4), altchars=b"-_", validate=True
            )
            ciphertext = base64.b64decode(
                ciphertext_text + "=" * (-len(ciphertext_text) % 4),
                altchars=b"-_", validate=True,
            )
            if len(nonce) != 12 or not 17 <= len(ciphertext) <= 144:
                raise ValueError()
            plaintext = AESGCM(self._keys[key_id]).decrypt(
                nonce, ciphertext, self._aad(self.environment, admin_id, key_id, context)
            )
            secret = plaintext.decode("utf-8")
            if not secret or len(secret) > 128:
                raise ValueError()
            return secret
        except (InvalidTag, ValueError, TypeError, UnicodeError, IndexError, binascii.Error):
            raise TotpSecretError() from None

    def rotate(self, envelope: str, *, admin_id: UUID, context: str | None = None) -> str:
        secret = self.decrypt(envelope, admin_id=admin_id, context=context)
        if envelope.split(":")[2] == self.active_key_id:
            return envelope
        return self.encrypt(secret, admin_id=admin_id, context=context)

    @staticmethod
    def is_envelope(value: str) -> bool:
        return isinstance(value, str) and value.startswith(_PREFIX)
