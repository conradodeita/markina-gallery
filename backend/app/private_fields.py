"""Encryption for personal profile fields using a key outside the database."""

from __future__ import annotations

import base64
import os
import secrets
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PrivateFieldError(RuntimeError):
    pass


def _key() -> bytes:
    try:
        raw = base64.urlsafe_b64decode(os.environ["ADMIN_PRIVATE_FIELD_KEY"])
    except (KeyError, ValueError):
        raise PrivateFieldError("Chave de campos privados indisponível.") from None
    if len(raw) != 32:
        raise PrivateFieldError("Chave de campos privados indisponível.")
    return raw


def encrypt_private_field(value: str, *, tenant_id: UUID, field: str) -> str:
    return _encrypt_private_value(value, tenant_id=tenant_id, field=field, max_length=256)


def encrypt_private_document(value: str, *, tenant_id: UUID, field: str) -> str:
    return _encrypt_private_value(value, tenant_id=tenant_id, field=field, max_length=1024)


def _encrypt_private_value(value: str, *, tenant_id: UUID, field: str, max_length: int) -> str:
    if not value or len(value) > max_length or not field.isascii():
        raise PrivateFieldError("Campo privado inválido.")
    nonce = secrets.token_bytes(12)
    aad = f"{os.getenv('APP_ENV', 'development')}:{tenant_id}:{field}".encode()
    ciphertext = AESGCM(_key()).encrypt(nonce, value.encode("utf-8"), aad)
    return "private:v1:" + base64.urlsafe_b64encode(nonce + ciphertext).decode().rstrip("=")


def decrypt_private_field(envelope: str, *, tenant_id: UUID, field: str) -> str:
    return _decrypt_private_value(envelope, tenant_id=tenant_id, field=field, max_length=256)


def decrypt_private_document(envelope: str, *, tenant_id: UUID, field: str) -> str:
    return _decrypt_private_value(envelope, tenant_id=tenant_id, field=field, max_length=1024)


def _decrypt_private_value(envelope: str, *, tenant_id: UUID, field: str, max_length: int) -> str:
    try:
        if not envelope.startswith("private:v1:"):
            raise ValueError()
        raw = base64.urlsafe_b64decode(envelope.split(":", 2)[2] + "==")
        aad = f"{os.getenv('APP_ENV', 'development')}:{tenant_id}:{field}".encode()
        value = AESGCM(_key()).decrypt(raw[:12], raw[12:], aad).decode("utf-8")
        if not value or len(value) > max_length:
            raise ValueError()
        return value
    except (ValueError, UnicodeError, InvalidTag):
        raise PrivateFieldError("Campo privado indisponível.") from None
