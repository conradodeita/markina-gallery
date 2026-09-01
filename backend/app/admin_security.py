"""Primitivas isoladas para recuperação e ações sensíveis administrativas."""

from __future__ import annotations

import base64
import json
import os
import secrets
from datetime import timedelta
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import (
    AdminActionToken,
    AdminSecurityChallenge,
    EmailDelivery,
    expired,
    now,
    pii_fingerprint,
    token_hash,
)


class AdminSecurityConfigurationError(RuntimeError):
    """Configuração segura ausente ou inválida."""


def _decode_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise AdminSecurityConfigurationError("Chave de payload inválida.") from exc
    if len(key) != 32:
        raise AdminSecurityConfigurationError("A chave de payload deve possuir 32 bytes.")
    return key


def sensitive_payload_key() -> bytes:
    value = os.getenv("EMAIL_PAYLOAD_ENCRYPTION_KEY", "").strip()
    if value:
        return _decode_key(value)
    if os.getenv("APP_ENV", "development") != "development":
        raise AdminSecurityConfigurationError(
            "EMAIL_PAYLOAD_ENCRYPTION_KEY é obrigatória fora de desenvolvimento."
        )
    return sha256(b"markina-development-only-email-payload-key").digest()


def encrypt_sensitive_payload(payload: dict[str, Any], *, context: str) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(sensitive_payload_key()).encrypt(nonce, raw, context.encode("utf-8"))
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_sensitive_payload(token: str, *, context: str) -> dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        decoded = AESGCM(sensitive_payload_key()).decrypt(
            raw[:12], raw[12:], context.encode("utf-8")
        )
        payload = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeError, InvalidTag, json.JSONDecodeError) as exc:
        raise AdminSecurityConfigurationError("Payload sensível inválido ou adulterado.") from exc
    if not isinstance(payload, dict):
        raise AdminSecurityConfigurationError("Payload sensível inválido ou adulterado.")
    return payload


def issue_admin_action_token(
    db: Session,
    *,
    admin_id: UUID,
    purpose: str,
    target: str | None = None,
    lifetime_minutes: int = 15,
) -> tuple[AdminActionToken, str]:
    instant = now()
    for previous in db.scalars(
        select(AdminActionToken).where(
            AdminActionToken.admin_id == admin_id,
            AdminActionToken.purpose == purpose,
            AdminActionToken.used_at.is_(None),
        )
    ):
        previous.used_at = instant
        previous.encrypted_target = None
    raw_token = secrets.token_urlsafe(32)
    item = AdminActionToken(
        id=uuid4(),
        admin_id=admin_id,
        purpose=purpose,
        token_hash=token_hash(raw_token),
        target_fingerprint=pii_fingerprint(target.strip().casefold()) if target else None,
        expires_at=instant + timedelta(minutes=max(1, min(lifetime_minutes, 30))),
    )
    if target:
        item.encrypted_target = encrypt_sensitive_payload(
            {"target": target}, context=f"admin-action:{item.id}:{purpose}"
        )
    db.add(item)
    db.flush()
    return item, raw_token


def consume_admin_action_token(
    db: Session,
    *,
    raw_token: str,
    purpose: str,
) -> AdminActionToken | None:
    item = db.scalar(
        select(AdminActionToken).where(
            AdminActionToken.token_hash == token_hash(raw_token),
            AdminActionToken.purpose == purpose,
        )
    )
    if not item or item.used_at or expired(item.expires_at):
        return None
    consumed_at = now()
    result = db.execute(
        update(AdminActionToken)
        .where(AdminActionToken.id == item.id, AdminActionToken.used_at.is_(None))
        .values(used_at=consumed_at)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        return None
    item.used_at = consumed_at
    return item


def invalidate_admin_security_material(db: Session, admin_id: UUID) -> None:
    instant = now()
    for challenge in db.scalars(
        select(AdminSecurityChallenge).where(
            AdminSecurityChallenge.admin_id == admin_id,
            AdminSecurityChallenge.used_at.is_(None),
        )
    ):
        challenge.used_at = instant
        challenge.encrypted_target = None
    for item in db.scalars(
        select(AdminActionToken).where(
            AdminActionToken.admin_id == admin_id,
            AdminActionToken.used_at.is_(None),
        )
    ):
        item.used_at = instant
        item.encrypted_target = None


def cleanup_admin_security_material(db: Session) -> int:
    """Minimiza material terminal sem apagar a trilha de auditoria."""

    changed = 0
    instant = now()
    for challenge in db.scalars(select(AdminSecurityChallenge)):
        if (challenge.used_at or expired(challenge.expires_at)) and challenge.encrypted_target:
            challenge.encrypted_target = None
            changed += 1
    for item in db.scalars(select(AdminActionToken)):
        if (item.used_at or expired(item.expires_at)) and item.encrypted_target:
            item.encrypted_target = None
            changed += 1
    for delivery in db.scalars(select(EmailDelivery)):
        if delivery.status in {"accepted", "failed", "unknown", "expired"}:
            if delivery.encrypted_payload:
                delivery.encrypted_payload = None
                changed += 1
        elif expired(delivery.expires_at):
            delivery.status = "expired"
            delivery.encrypted_payload = None
            delivery.last_error = "Entrega expirada antes da aceitação."
            delivery.updated_at = instant
            changed += 1
    if changed:
        db.commit()
    return changed
