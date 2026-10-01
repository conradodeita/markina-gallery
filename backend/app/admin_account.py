"""Serviços de recuperação e manutenção segura da conta administrativa."""

from __future__ import annotations

import secrets
from datetime import timedelta
from uuid import UUID, uuid4

from argon2.exceptions import VerificationError
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import require_active_owner
from app.admin_security import (
    decrypt_sensitive_payload,
    encrypt_sensitive_payload,
    invalidate_admin_security_material,
    issue_admin_action_token,
)
from app.auth import (
    AdminSecurityChallenge,
    AdminUser,
    AuthSession,
    EmailDelivery,
    WhatsAppDelivery,
    audit,
    expired,
    now,
    password_hasher,
    pii_fingerprint,
    revoke_subject_sessions,
    token_hash,
    validate_admin_password,
)
from app.email_delivery import enqueue_email, sensitive_link
from app.messaging import (
    WhatsAppConfigurationError,
)
from app.product_brand import PRODUCT_NAME
from app.tenancy import TenantContextError, require_admin_tenant
from app.whatsapp_binding import photographer_phone, resolve_binding
from app.whatsapp_delivery import encrypt_otp, otp_encryption_key


class AdminAccountError(RuntimeError):
    """Falha segura e apresentável de um fluxo administrativo."""


def require_security_owner(db: Session, admin_id: UUID | None, tenant_id: UUID | None) -> None:
    try:
        if admin_id is None or tenant_id is None or require_admin_tenant(db, admin_id).id != tenant_id:
            raise TenantContextError("Acesso negado.")
    except TenantContextError as exc:
        raise AdminAccountError("Contexto da confirmação indisponível.") from exc


def normalize_admin_email(value: str) -> str:
    email = value.strip().casefold()
    local, separator, domain = email.partition("@")
    if (
        not separator
        or not 1 <= len(local) <= 64
        or not 3 <= len(domain) <= 255
        or "." not in domain
        or any(character.isspace() for character in email)
        or len(email) > 320
    ):
        raise AdminAccountError("Informe um e-mail válido.")
    return email


def mask_email(value: str) -> str:
    local, _, domain = value.partition("@")
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}{'•' * max(3, len(local) - len(visible))}@{domain}"


def _admin_whatsapp_phone(db: Session, *, tenant_id: UUID | None) -> str | None:
    if tenant_id is None:
        return None
    try:
        return photographer_phone(db, tenant_id=tenant_id)
    except (WhatsAppConfigurationError, HTTPException):
        return None


def _queue_admin_otp(
    db: Session,
    challenge: AdminSecurityChallenge,
    code: str,
    recipient: str,
) -> WhatsAppDelivery:
    binding = resolve_binding(db, challenge.tenant_id)
    key = f"admin-security-otp:{challenge.id}:{challenge.resend_count}"
    require_active_owner(db, challenge.tenant_id)
    existing = db.scalar(select(WhatsAppDelivery).where(
        WhatsAppDelivery.tenant_id == challenge.tenant_id, WhatsAppDelivery.idempotency_key == key))
    if existing:
        return existing
    delivery = WhatsAppDelivery(
        tenant_id=challenge.tenant_id,
        kind="otp",
        source_type="admin_security_challenge",
        source_id=str(challenge.id),
        recipient_phone=recipient,
        recipient_fingerprint=pii_fingerprint(recipient),
        template_kind=challenge.purpose,
        idempotency_key=key,
        expires_at=challenge.expires_at,
    )
    try:
        delivery.encrypted_payload = encrypt_otp(
            code, key=otp_encryption_key(), context=key
        )
    except (WhatsAppConfigurationError, ValueError):
        if binding.name != "sandbox":
            raise
        delivery.status = "accepted"
        delivery.external_message_id = f"sandbox:{token_hash(key)[:24]}"
        delivery.accepted_at = now()
    db.add(delivery)
    return delivery


def create_security_challenge(
    db: Session,
    *,
    purpose: str,
    subject_fingerprint: str,
    admin: AdminUser | None,
    session_id: UUID | None = None,
    target: str | None = None,
    tenant_id: UUID | None = None,
) -> tuple[AdminSecurityChallenge, str, bool]:
    if purpose == "change_pix_otp":
        require_security_owner(db, admin.id if admin else None, tenant_id)
        resolve_binding(db, tenant_id)
    elif admin and tenant_id is None:
        try:
            tenant_id = require_admin_tenant(db, admin.id).id
        except TenantContextError:
            pass  # Recuperação técnica sem vínculo não escolhe canal comercial.
    recipient = _admin_whatsapp_phone(db, tenant_id=tenant_id) if admin else None
    if purpose == "password_recovery_otp" and not recipient:
        # Sem canal próprio, o fluxo público persiste apenas o desafio neutro.
        # Não invalida confirmações anteriores nem escolhe outro fotógrafo.
        admin = None
        tenant_id = None
    instant = now()
    if admin:
        for previous in db.scalars(
            select(AdminSecurityChallenge).where(
                AdminSecurityChallenge.admin_id == admin.id,
                AdminSecurityChallenge.purpose == purpose,
                AdminSecurityChallenge.tenant_id == tenant_id,
                AdminSecurityChallenge.used_at.is_(None),
            )
        ):
            previous.used_at = instant
            previous.encrypted_target = None
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = AdminSecurityChallenge(
        tenant_id=tenant_id,
        id=uuid4(),
        purpose=purpose,
        admin_id=admin.id if admin else None,
        session_id=session_id,
        subject_fingerprint=subject_fingerprint,
        target_fingerprint=pii_fingerprint(target.strip().casefold()) if target else None,
        secret_hash=token_hash(code),
        expires_at=instant + timedelta(minutes=10),
    )
    if target:
        challenge.encrypted_target = encrypt_sensitive_payload(
            {"target": target}, context=f"admin-challenge:{challenge.id}:{purpose}"
        )
    db.add(challenge)
    queued = bool(recipient)
    if recipient:
        _queue_admin_otp(db, challenge, code, recipient)
    audit(db, f"admin_security.{purpose}.requested", subject_fingerprint, tenant_id=tenant_id)
    db.commit()
    return challenge, code, queued


def verify_security_challenge(
    db: Session,
    *,
    challenge_id: UUID,
    purpose: str,
    code: str,
    session_id: UUID | None = None,
    tenant_id: UUID | None = None,
) -> AdminSecurityChallenge:
    challenge = db.get(AdminSecurityChallenge, challenge_id, populate_existing=True)
    if purpose == "change_pix_otp":
        if not challenge or tenant_id is None or challenge.tenant_id != tenant_id:
            raise AdminAccountError("Não foi possível confirmar o código.")
        require_security_owner(db, challenge.admin_id, tenant_id)
    if (
        not challenge
        or challenge.purpose != purpose
        or challenge.used_at
        or expired(challenge.expires_at)
        or challenge.attempts >= 5
        or (session_id is not None and challenge.session_id != session_id)
    ):
        raise AdminAccountError("Não foi possível confirmar o código.")
    if not secrets.compare_digest(challenge.secret_hash, token_hash(code)):
        challenge.attempts += 1
        if challenge.attempts >= 5:
            challenge.used_at = now()
            challenge.encrypted_target = None
        audit(db, f"admin_security.{purpose}.failed", challenge.subject_fingerprint, tenant_id=challenge.tenant_id)
        db.commit()
        raise AdminAccountError("Não foi possível confirmar o código.")
    challenge.used_at = now()
    audit(db, f"admin_security.{purpose}.validated", challenge.subject_fingerprint, tenant_id=challenge.tenant_id)
    db.flush()
    return challenge


def resend_security_challenge(
    db: Session, *, challenge_id: UUID, purpose: str, tenant_id: UUID | None = None
) -> AdminSecurityChallenge:
    challenge = db.get(AdminSecurityChallenge, challenge_id, populate_existing=True)
    if purpose == "change_pix_otp":
        if not challenge or tenant_id is None or challenge.tenant_id != tenant_id:
            raise AdminAccountError("Não foi possível reenviar o código.")
        require_security_owner(db, challenge.admin_id, tenant_id)
    if (
        not challenge
        or challenge.purpose != purpose
        or challenge.used_at
        or expired(challenge.expires_at)
        or challenge.resend_count >= 3
    ):
        raise AdminAccountError("Não foi possível reenviar o código.")
    recipient = _admin_whatsapp_phone(db, tenant_id=challenge.tenant_id) if challenge.admin_id else None
    if not recipient and purpose == "change_pix_otp":
        raise WhatsAppConfigurationError("Canal de confirmação indisponível.")
    if not recipient:
        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge.resend_count += 1
        challenge.secret_hash = token_hash(code)
        challenge.attempts = 0
        audit(db, f"admin_security.{purpose}.resend_simulated", challenge.subject_fingerprint, tenant_id=challenge.tenant_id)
        db.commit()
        return challenge
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge.resend_count += 1
    challenge.secret_hash = token_hash(code)
    challenge.attempts = 0
    _queue_admin_otp(db, challenge, code, recipient)
    audit(db, f"admin_security.{purpose}.resent", challenge.subject_fingerprint, tenant_id=challenge.tenant_id)
    db.commit()
    return challenge


def reauthenticate_admin(admin: AdminUser, current_password: str) -> None:
    try:
        valid = password_hasher.verify(admin.password_hash, current_password)
    except VerificationError:
        valid = False
    if not valid:
        raise AdminAccountError("Não foi possível confirmar a credencial atual.")


def issue_password_reset_email(db: Session, challenge: AdminSecurityChallenge) -> None:
    if not challenge.admin_id:
        raise AdminAccountError("Não foi possível concluir a recuperação.")
    admin = db.get(AdminUser, challenge.admin_id)
    if not admin or not admin.email_verified:
        raise AdminAccountError("Não foi possível concluir a recuperação.")
    token, raw_token = issue_admin_action_token(
        db, admin_id=admin.id, purpose="password_reset"
    )
    link = sensitive_link("/admin/reset-password", raw_token)
    enqueue_email(
        db,
        kind="password_recovery",
        source_type="admin_action_token",
        source_id=str(token.id),
        recipient=admin.email,
        subject=f"Redefinição de senha · {PRODUCT_NAME}",
        text_body=(
            "Foi solicitada uma redefinição de senha. Abra o link de uso único, "
            f"válido por 15 minutos: {link}\n\nSe não foi você, ignore esta mensagem."
        ),
        idempotency_key=f"email:password-reset:{token.id}",
        expires_at=token.expires_at,
    )
    audit(db, "admin_security.password_reset_link.queued", pii_fingerprint(admin.email))
    db.commit()


def challenge_target(challenge: AdminSecurityChallenge) -> str:
    if not challenge.encrypted_target:
        raise AdminAccountError("Alvo da alteração indisponível.")
    payload = decrypt_sensitive_payload(
        challenge.encrypted_target,
        context=f"admin-challenge:{challenge.id}:{challenge.purpose}",
    )
    target = payload.get("target")
    if not isinstance(target, str):
        raise AdminAccountError("Alvo da alteração indisponível.")
    return target


def token_target(token) -> str:
    if not token.encrypted_target:
        raise AdminAccountError("Alvo da alteração indisponível.")
    payload = decrypt_sensitive_payload(
        token.encrypted_target,
        context=f"admin-action:{token.id}:{token.purpose}",
    )
    target = payload.get("target")
    if not isinstance(target, str):
        raise AdminAccountError("Alvo da alteração indisponível.")
    return target


def change_admin_password(
    db: Session, admin: AdminUser, new_password: str, *, audit_event: str
) -> None:
    validate_admin_password(
        new_password,
        email=admin.email,
        current_password_hash=admin.password_hash,
    )
    admin.password_hash = password_hasher.hash(new_password)
    invalidate_admin_security_material(db, admin.id)
    revoke_subject_sessions(db, "admin", admin.id)
    audit(db, audit_event, str(admin.id))


def issue_email_verification(db: Session, admin: AdminUser, new_email: str) -> None:
    normalized = normalize_admin_email(new_email)
    if db.scalar(select(AdminUser).where(AdminUser.email == normalized)):
        raise AdminAccountError("Não foi possível usar o e-mail informado.")
    token, raw_token = issue_admin_action_token(
        db,
        admin_id=admin.id,
        purpose="verify_admin_email",
        target=normalized,
    )
    link = sensitive_link("/admin/verify-email", raw_token)
    enqueue_email(
        db,
        kind="email_verification",
        source_type="admin_action_token",
        source_id=str(token.id),
        recipient=normalized,
        subject=f"Confirme o novo e-mail · {PRODUCT_NAME}",
        text_body=f"Confirme o novo endereço pelo link de uso único: {link}",
        idempotency_key=f"email:verify-admin-email:{token.id}",
        expires_at=token.expires_at,
    )
    audit(db, "admin_security.email_verification.queued", token.target_fingerprint or "unknown")
    db.commit()


def queue_previous_email_notice(
    db: Session, *, admin_id: UUID, previous_email: str, action_token_id: UUID
) -> EmailDelivery:
    return enqueue_email(
        db,
        kind="security_notice",
        source_type="admin_user",
        source_id=str(admin_id),
        recipient=previous_email,
        subject="O e-mail administrativo foi alterado",
        text_body=(
            f"O endereço de acesso administrativo de {PRODUCT_NAME} foi alterado. "
            "Se você não reconhece esta ação, interrompa o acesso ao ambiente e revise as credenciais."
        ),
        idempotency_key=f"email:previous-address-notice:{action_token_id}",
        expires_at=now() + timedelta(days=1),
    )


def active_admin_for_session(db: Session, session: AuthSession) -> AdminUser:
    from app.tenancy import TenantContextError, require_admin_tenant

    try:
        tenant = require_admin_tenant(db, session.subject_id)
    except TenantContextError as exc:
        raise AdminAccountError("Conta administrativa indisponível.") from exc
    if session.tenant_id != tenant.id or session.admin_subject_id != session.subject_id:
        raise AdminAccountError("Conta administrativa indisponível.")
    admin = db.get(AdminUser, session.subject_id, populate_existing=True)
    if not admin or not admin.email_verified:
        raise AdminAccountError("Conta administrativa indisponível.")
    return admin
