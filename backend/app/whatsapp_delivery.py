"""Primitivas seguras e monotônicas para entregas WhatsApp."""

from __future__ import annotations

import base64
import os
import secrets
from dataclasses import dataclass
from datetime import datetime

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.messaging import WhatsAppConfigurationError


STATUS_RANK = {
    "queued": 0,
    "processing": 1,
    "accepted": 2,
    "delivered": 3,
    "read": 4,
}
TERMINAL_STATES = {"read", "failed", "expired"}


@dataclass(frozen=True)
class DeliveryTransition:
    status: str
    changed: bool


def _decode_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise WhatsAppConfigurationError(
            "A chave de payload WhatsApp é inválida."
        ) from exc
    if len(key) != 32:
        raise WhatsAppConfigurationError(
            "A chave de payload WhatsApp deve possuir 32 bytes."
        )
    return key


def otp_encryption_key() -> bytes:
    value = os.getenv("WHATSAPP_OTP_ENCRYPTION_KEY", "").strip()
    if not value:
        raise WhatsAppConfigurationError(
            "A chave de payload WhatsApp não está configurada."
        )
    return _decode_key(value)


def encrypt_otp(code: str, *, key: bytes, context: str) -> str:
    if len(key) != 32 or not code.isdigit() or len(code) != 6:
        raise ValueError("Payload OTP ou chave inválidos.")
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, code.encode("ascii"), context.encode("utf-8"))
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_otp(token: str, *, key: bytes, context: str) -> str:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        code = AESGCM(key).decrypt(raw[:12], raw[12:], context.encode("utf-8")).decode(
            "ascii"
        )
    except (ValueError, UnicodeError, InvalidTag) as exc:
        raise WhatsAppConfigurationError("Payload OTP inválido ou adulterado.") from exc
    if not code.isdigit() or len(code) != 6:
        raise WhatsAppConfigurationError("Payload OTP inválido ou adulterado.")
    return code


def transition_status(current: str, requested: str) -> DeliveryTransition:
    if current == requested:
        return DeliveryTransition(current, False)
    if current in TERMINAL_STATES:
        return DeliveryTransition(current, False)
    if requested in {"failed", "expired", "unknown"}:
        return DeliveryTransition(requested, True)
    if current == "unknown":
        if requested in {"accepted", "delivered", "read"}:
            return DeliveryTransition(requested, True)
        return DeliveryTransition(current, False)
    if requested not in STATUS_RANK or current not in STATUS_RANK:
        return DeliveryTransition(current, False)
    if STATUS_RANK[requested] < STATUS_RANK[current]:
        return DeliveryTransition(current, False)
    return DeliveryTransition(requested, True)


def apply_delivery_status(delivery, requested: str, *, at: datetime) -> bool:
    transition = transition_status(delivery.status or "queued", requested)
    if not transition.changed:
        return False
    delivery.status = transition.status
    delivery.updated_at = at
    if requested == "accepted" and delivery.accepted_at is None:
        delivery.accepted_at = at
    elif requested == "delivered" and delivery.delivered_at is None:
        delivery.delivered_at = at
    elif requested == "read" and delivery.read_at is None:
        delivery.read_at = at
    return True
