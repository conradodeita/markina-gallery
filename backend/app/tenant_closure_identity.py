"""Confirma dados atuais para possível reabertura de conta encerrada há dez anos."""

from __future__ import annotations

import hmac
import secrets
from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.admin_account import AdminAccountError, normalize_admin_email
from app.auth import (
    AdminUser,
    PhotographerBusinessProfile,
    PhotographerSignup,
    SessionLocal,
    Tenant,
    TenantAdmin,
    TenantClosureIdentityVerification,
    TenantClosureRequest,
    audit,
    enforce_rate_limit,
    expired,
    now,
    pii_fingerprint,
)
from app.email_delivery import EmailConfigurationError, email_channel_payload, enqueue_email
from app.mercadopago_api import SensitiveRoute
from app.photographer_cpf import PhotographerCpfFingerprintError, cpf_matches_tenant, normalize_cpf
from app.private_fields import PrivateFieldError, decrypt_private_field, encrypt_private_field
from app.system_monitor.store import bounded
from app.tenant_closure_recovery import _ten_year_anniversary
from app.tenant_hosts import closed_tenant_for_host

router = APIRouter(
    prefix="/auth/photographer-closure-identity",
    route_class=SensitiveRoute,
)
HEADERS = {"Cache-Control": "private, no-store"}
NEUTRAL_START = "Se os dados puderem ser confirmados, enviaremos um código para o e-mail informado."
NEUTRAL_CONFIRM = "Se a confirmação puder prosseguir, os dados atuais serão encaminhados para análise do proprietário."
CODE_LIFETIME = timedelta(minutes=10)
MAX_ATTEMPTS = 5


def database():
    with SessionLocal() as db:
        try:
            bounded(db)
            yield db
        except (SQLAlchemyError, PhotographerCpfFingerprintError, PrivateFieldError):
            db.rollback()
            raise HTTPException(503, "Serviço temporariamente indisponível.", headers=HEADERS) from None


Database = Annotated[Session, Depends(database)]


class IdentityRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    full_name: str = Field(min_length=1, max_length=120)
    email: SecretStr = Field(min_length=3, max_length=320)
    cpf: SecretStr = Field(min_length=1, max_length=32)


class IdentityConfirmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID
    code: SecretStr = Field(min_length=6, max_length=6)


def _public_response(
    response: Response,
    message: str,
    *,
    challenge_id: UUID | None = None,
) -> dict[str, str]:
    response.headers.update(HEADERS)
    return {"message": message, "challenge_id": str(challenge_id or UUID(bytes=secrets.token_bytes(16), version=4))}


def _same_host_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(origin)
        origin_host = (parsed.hostname or "").lower().rstrip(".")
        request_host = urlsplit(f"//{request.headers.get('host', '')}").hostname or ""
        request_host = request_host.lower().rstrip(".")
        origin_port = parsed.port or (443 if parsed.scheme == "https" else 80)
        request_host_header = urlsplit(f"//{request.headers.get('host', '')}")
        request_port = request_host_header.port
    except ValueError:
        raise HTTPException(403, "Origem não autorizada.", headers=HEADERS) from None
    if (
        parsed.scheme not in {"https", "http"}
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or origin_host != request_host
        or (request_port is not None and origin_port != request_port)
    ):
        raise HTTPException(403, "Origem não autorizada.", headers=HEADERS)


def _apply_rate_limit(db: Session, scope: str, subject: str, ip_address: str) -> None:
    try:
        enforce_rate_limit(db, scope, subject, ip_address)
    except HTTPException as exc:
        exc.headers = {**(exc.headers or {}), **HEADERS}
        raise


def _current_closure(db: Session, tenant: Tenant):
    closure = db.scalar(
        select(TenantClosureRequest)
        .where(TenantClosureRequest.tenant_id == tenant.id,
               TenantClosureRequest.state == "closed")
        .order_by(TenantClosureRequest.closed_at.desc())
        .limit(1)
        .with_for_update()
    )
    if (
        tenant.lifecycle != "closed"
        or closure is None
        or closure.closed_at is None
        or now() < _ten_year_anniversary(closure.closed_at)
    ):
        return None
    return closure


def _erase_challenge(row: TenantClosureIdentityVerification, state: str) -> None:
    row.state = state
    row.current_name_envelope = None
    row.current_email_envelope = None
    row.email_fingerprint = None
    row.code_digest = None


def cleanup_expired_identity_challenges(db: Session) -> int:
    """Apaga dados transitórios cifrados quando o código perde a validade."""
    rows = list(db.scalars(select(TenantClosureIdentityVerification).where(
        TenantClosureIdentityVerification.state == "email_pending",
        TenantClosureIdentityVerification.expires_at <= now(),
    ).with_for_update(skip_locked=True)))
    for row in rows:
        _erase_challenge(row, "expired")
    if rows:
        db.commit()
    return len(rows)


def _code_digest(challenge_id: UUID, code: str) -> str:
    return pii_fingerprint(f"tenant-closure-identity:{challenge_id}:{code}")


def _matching_admin(db: Session, tenant: Tenant, email: str):
    profile = db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.tenant_id == tenant.id,
    ))
    if not profile:
        return None
    admin = db.get(AdminUser, profile.admin_user_id, populate_existing=True)
    membership = db.scalar(select(TenantAdmin).where(
        TenantAdmin.tenant_id == tenant.id,
        TenantAdmin.admin_user_id == profile.admin_user_id,
        TenantAdmin.active.is_(True),
    ))
    if not admin or not membership:
        return None
    existing_email = db.scalar(select(AdminUser.id).where(
        func.lower(AdminUser.email) == email,
        AdminUser.id != admin.id,
    ).limit(1))
    signup = db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.reserved_admin_id == admin.id,
        PhotographerSignup.activated_tenant_id == tenant.id,
        PhotographerSignup.state == "active",
    ))
    signup_statement = select(PhotographerSignup.id).where(
        func.lower(PhotographerSignup.email) == email,
    )
    if signup:
        signup_statement = signup_statement.where(PhotographerSignup.id != signup.id)
    signup_email_conflict = db.scalar(signup_statement.limit(1))
    if existing_email or signup_email_conflict:
        return None
    return admin


@router.post("/request", status_code=202)
def request_identity_verification(
    payload: IdentityRequestInput,
    request: Request,
    response: Response,
    db: Database,
):
    _same_host_origin(request)
    response.headers.update(HEADERS)
    ip_address = request.client.host if request.client else "unknown"
    _apply_rate_limit(db, "closure_identity_start_ip", "public", ip_address)
    if email_channel_payload()["status"] != "ready":
        db.commit()
        raise HTTPException(503, "Verificação temporariamente indisponível.", headers=HEADERS)
    tenant = closed_tenant_for_host(db, request.headers.get("host"))
    if tenant is None:
        db.commit()
        return _public_response(response, NEUTRAL_START)

    _apply_rate_limit(db, "closure_identity_start_tenant", str(tenant.id), ip_address)
    prior = db.scalar(select(TenantClosureIdentityVerification).where(
        TenantClosureIdentityVerification.tenant_id == tenant.id,
        TenantClosureIdentityVerification.request_id == payload.request_id,
    ))
    if prior:
        db.commit()
        return _public_response(response, NEUTRAL_START, challenge_id=prior.id)

    closure = _current_closure(db, tenant)
    normalized_name = " ".join(payload.full_name.split())
    if (
        closure is None
        or len(normalized_name) < 2
        or any(ord(char) < 32 for char in normalized_name)
    ):
        audit(db, "tenant.closure_identity.requested", "public", tenant_id=tenant.id)
        db.commit()
        return _public_response(response, NEUTRAL_START)

    try:
        cpf = normalize_cpf(payload.cpf.get_secret_value())
        email = normalize_admin_email(payload.email.get_secret_value())
    except (PhotographerCpfFingerprintError, AdminAccountError):
        audit(db, "tenant.closure_identity.requested", "public", tenant_id=tenant.id)
        db.commit()
        return _public_response(response, NEUTRAL_START)

    admin = _matching_admin(db, tenant, email)
    try:
        matches = bool(admin and cpf_matches_tenant(db, tenant.id, cpf))
    except PhotographerCpfFingerprintError:
        db.rollback()
        raise HTTPException(503, "Verificação temporariamente indisponível.", headers=HEADERS) from None
    if not matches:
        audit(db, "tenant.closure_identity.requested", "public", tenant_id=tenant.id)
        db.commit()
        return _public_response(response, NEUTRAL_START)

    for previous in db.scalars(select(TenantClosureIdentityVerification).where(
        TenantClosureIdentityVerification.tenant_id == tenant.id,
        TenantClosureIdentityVerification.state == "email_pending",
    ).with_for_update()):
        _erase_challenge(previous, "superseded")

    challenge_id = UUID(bytes=secrets.token_bytes(16), version=4)
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = now() + CODE_LIFETIME
    challenge = TenantClosureIdentityVerification(
        id=challenge_id,
        tenant_id=tenant.id,
        closure_request_id=closure.id,
        admin_user_id=admin.id,
        request_id=payload.request_id,
        state="email_pending",
        current_name_envelope=encrypt_private_field(
            normalized_name, tenant_id=tenant.id, field="closure-identity-name",
        ),
        current_email_envelope=encrypt_private_field(
            email, tenant_id=tenant.id, field="closure-identity-email",
        ),
        email_fingerprint=pii_fingerprint(email.strip().casefold()),
        code_digest=_code_digest(challenge_id, code),
        expires_at=expires_at,
    )
    db.add(challenge)
    try:
        enqueue_email(
            db,
            kind="email_verification",
            source_type="tenant_closure_identity",
            source_id=str(challenge.id),
            recipient=email,
            subject="Confirme seu e-mail · Pick-your-Pic",
            text_body=(
                f"Seu código para confirmar os dados atuais da conta encerrada é {code}. "
                "Ele expira em 10 minutos, aceita até cinco tentativas e não reabre a conta. "
                "Se você não iniciou esta solicitação, ignore esta mensagem."
            ),
            idempotency_key=f"email:tenant-closure-identity:{challenge.id}",
            expires_at=expires_at,
        )
        audit(db, "tenant.closure_identity.requested", str(challenge.id), tenant_id=tenant.id)
        db.commit()
    except (EmailConfigurationError, PrivateFieldError, ValueError, SQLAlchemyError):
        db.rollback()
        raise HTTPException(503, "Verificação temporariamente indisponível.", headers=HEADERS) from None
    return _public_response(response, NEUTRAL_START, challenge_id=challenge.id)


@router.post("/confirm", status_code=202)
def confirm_identity_verification(
    payload: IdentityConfirmInput,
    request: Request,
    response: Response,
    db: Database,
):
    _same_host_origin(request)
    response.headers.update(HEADERS)
    ip_address = request.client.host if request.client else "unknown"
    _apply_rate_limit(
        db, "closure_identity_confirm", str(payload.challenge_id), ip_address,
    )
    request_tenant = closed_tenant_for_host(db, request.headers.get("host"))
    if request_tenant is None:
        db.commit()
        return _public_response(response, NEUTRAL_CONFIRM)
    challenge = db.scalar(select(TenantClosureIdentityVerification).where(
        TenantClosureIdentityVerification.id == payload.challenge_id,
        TenantClosureIdentityVerification.tenant_id == request_tenant.id,
    ).with_for_update())
    if not challenge:
        db.commit()
        return _public_response(response, NEUTRAL_CONFIRM)

    tenant = db.get(Tenant, challenge.tenant_id, populate_existing=True)
    closure = _current_closure(db, tenant) if tenant else None
    if (
        challenge.state != "email_pending"
        or expired(challenge.expires_at)
        or challenge.attempts >= MAX_ATTEMPTS
        or closure is None
        or closure.id != challenge.closure_request_id
        or request_tenant.id != challenge.tenant_id
    ):
        if challenge.state == "email_pending":
            _erase_challenge(challenge, "expired")
        db.commit()
        return _public_response(response, NEUTRAL_CONFIRM)

    code = payload.code.get_secret_value()
    try:
        expected = _code_digest(challenge.id, code) if len(code) == 6 and code.isascii() and code.isdigit() else ""
        valid = hmac.compare_digest(challenge.code_digest or "", expected)
    except RuntimeError:
        db.rollback()
        raise HTTPException(503, "Verificação temporariamente indisponível.", headers=HEADERS) from None
    if not valid:
        challenge.attempts += 1
        audit(db, "tenant.closure_identity.code_rejected", str(challenge.id), tenant_id=challenge.tenant_id)
        if challenge.attempts >= MAX_ATTEMPTS:
            _erase_challenge(challenge, "locked")
        db.commit()
        return _public_response(response, NEUTRAL_CONFIRM)

    try:
        full_name = decrypt_private_field(
            challenge.current_name_envelope or "",
            tenant_id=challenge.tenant_id,
            field="closure-identity-name",
        )
        email = normalize_admin_email(decrypt_private_field(
            challenge.current_email_envelope or "",
            tenant_id=challenge.tenant_id,
            field="closure-identity-email",
        ))
    except (PrivateFieldError, AdminAccountError):
        _erase_challenge(challenge, "locked")
        db.commit()
        return _public_response(response, NEUTRAL_CONFIRM)

    profile = db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.tenant_id == challenge.tenant_id,
        PhotographerBusinessProfile.admin_user_id == challenge.admin_user_id,
    ))
    admin = db.get(AdminUser, challenge.admin_user_id, populate_existing=True)
    membership = db.scalar(select(TenantAdmin).where(
        TenantAdmin.tenant_id == challenge.tenant_id,
        TenantAdmin.admin_user_id == challenge.admin_user_id,
        TenantAdmin.active.is_(True),
    ))
    signup = db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.reserved_admin_id == challenge.admin_user_id,
        PhotographerSignup.activated_tenant_id == challenge.tenant_id,
        PhotographerSignup.state == "active",
    ))
    collision = db.scalar(select(AdminUser.id).where(
        func.lower(AdminUser.email) == email,
        AdminUser.id != challenge.admin_user_id,
    ).limit(1))
    signup_collision = db.scalar(select(PhotographerSignup.id).where(
        func.lower(PhotographerSignup.email) == email,
        PhotographerSignup.reserved_admin_id != challenge.admin_user_id,
    ).limit(1))
    if not profile or not admin or not membership or collision or signup_collision:
        _erase_challenge(challenge, "locked")
        audit(db, "tenant.closure_identity.data_rejected", str(challenge.id), tenant_id=challenge.tenant_id)
        db.commit()
        return _public_response(response, NEUTRAL_CONFIRM)

    from app.photographer_access_recovery import completed_closure_proof
    proof = completed_closure_proof(db, challenge.tenant_id, closure.id, challenge.admin_user_id)
    if not proof or proof.recipient_fingerprint != pii_fingerprint(email):
        _erase_challenge(challenge, "locked")
        audit(db, "tenant.closure_identity.authorization_required", str(challenge.id), tenant_id=challenge.tenant_id)
        db.commit()
        return _public_response(response, NEUTRAL_CONFIRM)

    try:
        tenant.photographer_name = full_name
        profile.full_name = full_name
        admin.email = email
        admin.email_verified = True
        if signup:
            signup.photographer_name = full_name
            signup.email = email
        challenge.state = "verified"
        challenge.verified_at = now()
        _erase_verified_material(challenge)
        audit(db, "tenant.closure_identity.verified", str(challenge.id), tenant_id=challenge.tenant_id)
        db.flush()
        db.commit()
    except IntegrityError:
        db.rollback()
        return _public_response(response, NEUTRAL_CONFIRM)
    return _public_response(response, NEUTRAL_CONFIRM)


def _erase_verified_material(challenge: TenantClosureIdentityVerification) -> None:
    challenge.current_name_envelope = None
    challenge.current_email_envelope = None
    challenge.email_fingerprint = None
    challenge.code_digest = None
