"""Envelope dedicado a credenciais de integração; material mestre só no servidor."""

import base64
import json
import os
import re
import secrets
from dataclasses import dataclass, field
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MESSAGE = "Cofre de credenciais temporariamente indisponível."


class IntegrationSecretError(RuntimeError):
    pass


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


@dataclass(frozen=True)
class SecretEnvelope:
    environment: str
    key_id: str
    nonce: bytes = field(repr=False)
    ciphertext: bytes = field(repr=False)

    def payload(self) -> dict:
        return {"environment": self.environment, "key_id": self.key_id,
                "nonce": base64.b64encode(self.nonce).decode(),
                "ciphertext": base64.b64encode(self.ciphertext).decode()}

    @classmethod
    def from_payload(cls, value: dict):
        try:
            if set(value) != {"environment", "key_id", "nonce", "ciphertext"}:
                raise ValueError()
            return cls(value["environment"], value["key_id"],
                       base64.b64decode(value["nonce"], validate=True),
                       base64.b64decode(value["ciphertext"], validate=True))
        except (ValueError, TypeError, KeyError):
            raise IntegrationSecretError(MESSAGE) from None


class IntegrationCipher:
    def __init__(self):
        try:
            self.environment = os.environ.get("APP_ENV", "development").strip()
            if not self.environment or os.environ.get("INTEGRATION_SECRET_ENV") != self.environment:
                raise ValueError()
            self.active_key_id = os.environ["INTEGRATION_SECRET_ACTIVE_KEY_ID"]
            raw = json.loads(os.environ["INTEGRATION_SECRET_KEYS"], object_pairs_hook=_pairs)
            if not isinstance(raw, dict) or not 1 <= len(raw) <= 16:
                raise ValueError()
            self._keys = {}
            for key_id, value in raw.items():
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", key_id):
                    raise ValueError()
                key = base64.b64decode(value, validate=True)
                if len(key) != 32:
                    raise ValueError()
                self._keys[key_id] = key
            if self.active_key_id not in self._keys:
                raise ValueError()
        except (KeyError, ValueError, TypeError):
            raise IntegrationSecretError(MESSAGE) from None

    def _aad(self, tenant_id: UUID, credential_id: UUID, envelope: SecretEnvelope) -> bytes:
        if (not isinstance(tenant_id, UUID) or not isinstance(credential_id, UUID)
                or envelope.environment != self.environment):
            raise IntegrationSecretError(MESSAGE)
        return json.dumps({"v": 1, "purpose": "infinitepay-api-key", "tenant": str(tenant_id),
                           "credential": str(credential_id), "environment": self.environment,
                           "key_id": envelope.key_id}, sort_keys=True, separators=(",", ":")).encode()

    def encrypt(self, value: str, *, tenant_id: UUID, credential_id: UUID) -> SecretEnvelope:
        if not value or len(value) > 512 or any(not 32 <= ord(c) <= 126 for c in value):
            raise IntegrationSecretError(MESSAGE)
        envelope = SecretEnvelope(self.environment, self.active_key_id, secrets.token_bytes(12), b"")
        ciphertext = AESGCM(self._keys[self.active_key_id]).encrypt(
            envelope.nonce, value.encode(), self._aad(tenant_id, credential_id, envelope))
        return SecretEnvelope(envelope.environment, envelope.key_id, envelope.nonce, ciphertext)

    def decrypt(self, envelope: SecretEnvelope, *, tenant_id: UUID, credential_id: UUID) -> str:
        try:
            if len(envelope.nonce) != 12 or not 17 <= len(envelope.ciphertext) <= 528:
                raise ValueError()
            return AESGCM(self._keys[envelope.key_id]).decrypt(
                envelope.nonce, envelope.ciphertext,
                self._aad(tenant_id, credential_id, envelope)).decode()
        except (InvalidTag, KeyError, ValueError, UnicodeError, TypeError):
            raise IntegrationSecretError(MESSAGE) from None

    def rotate(self, envelope: SecretEnvelope, *, tenant_id: UUID, credential_id: UUID) -> SecretEnvelope:
        return self.encrypt(self.decrypt(envelope, tenant_id=tenant_id, credential_id=credential_id),
                            tenant_id=tenant_id, credential_id=credential_id)
