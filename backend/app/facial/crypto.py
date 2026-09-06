"""Envelope AEAD versionado e vinculado ao escopo do dado facial."""

from __future__ import annotations

import json
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENVELOPE_VERSION = 1
NONCE_BYTES = 12


class FacialCryptoError(RuntimeError):
    """Falha criptográfica sanitizada, sem revelar chave ou escopo interno."""


@dataclass(frozen=True)
class FacialEnvelope:
    ciphertext: bytes
    nonce: bytes
    key_id: str
    version: int = ENVELOPE_VERSION


@dataclass(frozen=True)
class FacialScope:
    environment: str
    gallery_id: UUID
    object_kind: Literal["photo", "request"]
    object_id: UUID
    purpose: Literal[
        "embedding", "reference_image", "reference_locator", "notification"
    ]
    model_version: str
    data_version: str

    def additional_authenticated_data(self, *, envelope_version: int) -> bytes:
        if (
            not self.environment.strip()
            or not self.model_version.strip()
            or not self.data_version.strip()
        ):
            raise FacialCryptoError("Escopo criptográfico facial inválido.")
        if self.object_kind == "photo" and self.purpose != "embedding":
            raise FacialCryptoError("Escopo criptográfico facial inválido.")
        if self.object_kind == "request" and self.purpose == "embedding":
            raise FacialCryptoError("Escopo criptográfico facial inválido.")
        payload = {
            "data_version": self.data_version,
            "environment": self.environment,
            "envelope_version": envelope_version,
            "gallery_id": str(self.gallery_id),
            "model_version": self.model_version,
            "object_id": str(self.object_id),
            "object_kind": self.object_kind,
            "purpose": self.purpose,
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


class FacialCipher:
    """Cifra envelopes com chave ativa e decifra versões ainda autorizadas."""

    def __init__(self, *, active_key_id: str, keys: Mapping[str, bytes]) -> None:
        normalized = dict(keys)
        if (
            not active_key_id
            or active_key_id not in normalized
            or any(len(key) != 32 for key in normalized.values())
        ):
            raise FacialCryptoError("Chave criptográfica facial indisponível.")
        self._active_key_id = active_key_id
        self._keys = MappingProxyType(normalized)

    @property
    def active_key_id(self) -> str:
        return self._active_key_id

    def encrypt(self, plaintext: bytes, *, scope: FacialScope) -> FacialEnvelope:
        if not plaintext:
            raise FacialCryptoError("Payload facial vazio não pode ser cifrado.")
        nonce = secrets.token_bytes(NONCE_BYTES)
        aad = scope.additional_authenticated_data(envelope_version=ENVELOPE_VERSION)
        ciphertext = AESGCM(self._keys[self._active_key_id]).encrypt(
            nonce, plaintext, aad
        )
        return FacialEnvelope(
            ciphertext=ciphertext,
            nonce=nonce,
            key_id=self._active_key_id,
        )

    def decrypt(self, envelope: FacialEnvelope, *, scope: FacialScope) -> bytes:
        if envelope.version != ENVELOPE_VERSION or len(envelope.nonce) != NONCE_BYTES:
            raise FacialCryptoError("Envelope facial inválido ou adulterado.")
        key = self._keys.get(envelope.key_id)
        if key is None:
            raise FacialCryptoError("Chave criptográfica facial indisponível.")
        try:
            return AESGCM(key).decrypt(
                envelope.nonce,
                envelope.ciphertext,
                scope.additional_authenticated_data(
                    envelope_version=envelope.version
                ),
            )
        except (InvalidTag, ValueError) as exc:
            raise FacialCryptoError("Envelope facial inválido ou adulterado.") from exc

    def rotate(self, envelope: FacialEnvelope, *, scope: FacialScope) -> FacialEnvelope:
        """Reprotege explicitamente um envelope antigo com a chave ativa."""

        plaintext = self.decrypt(envelope, scope=scope)
        if envelope.key_id == self._active_key_id:
            return envelope
        return self.encrypt(plaintext, scope=scope)
