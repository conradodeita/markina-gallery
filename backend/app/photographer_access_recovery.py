"""Recuperação excepcional: decisão externa do proprietário, sem documentos."""

import json
import secrets
from datetime import UTC, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool
from sqlalchemy import func, inspect, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import platform_console as console
from app.admin_account import (
    AdminAccountError,
    mask_email,
    normalize_admin_email,
    queue_previous_email_notice,
)
from app.admin_security import (
    AdminSecurityConfigurationError,
    decrypt_sensitive_payload,
    encrypt_sensitive_payload,
    invalidate_admin_security_material,
)
from app.auth import (
    AdminTotpRecoveryCode,
    AdminUser,
    AuthChallenge,
    PhotographerAccessRecovery,
    PhotographerSignup,
    Role,
    Tenant,
    TenantAdmin,
    TenantClosureRequest,
    audit,
    enforce_rate_limit,
    expired,
    now,
    password_hasher,
    pii_fingerprint,
    revoke_subject_sessions,
    token_hash,
)
from app.email_delivery import EmailConfigurationError, enqueue_email, sensitive_link
from app.mercadopago_api import SensitiveRoute
from app.photographer_signup import _lock_signup_identities
from app.photographer_totp_support import _eligible
from app.totp_crypto import TotpSecretError

owner_router = APIRouter(prefix="/admin/platform/console", route_class=SensitiveRoute)
public_router = APIRouter(prefix="/auth/photographer-access-recovery", route_class=SensitiveRoute)
HEADERS = {"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"}


def database():
    with console.SessionLocal() as db:
        try:
            from app.system_monitor.store import bounded
            bounded(db)
            yield db
        except (SQLAlchemyError, AdminSecurityConfigurationError, TotpSecretError):
            db.rollback()
            raise _error(503) from None


class StartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    expected_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    new_email: str = Field(min_length=3, max_length=320)
    identity_confirmed: StrictBool
    reason_code: Literal["lost_email", "lost_all_access"]
    reset_totp: StrictBool = False


class CommitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr
    totp_code: SecretStr


class VerifyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: SecretStr = Field(min_length=32, max_length=128)
    new_password: SecretStr = Field(min_length=1, max_length=128)


def version(admin):
    return pii_fingerprint("access-recovery:" + ":".join(map(str, (
        admin.id, admin.email, admin.password_hash, admin.totp_enabled,
        admin._totp_secret_envelope, admin._totp_secret_legacy,
    ))))


def _error(status=400):
    return HTTPException(status, "Não foi possível confirmar a recuperação. Consulte o atendimento.", headers=HEADERS)


def _target(db, tenant_id):
    tenant = db.get(Tenant, tenant_id)
    candidates = _eligible(db, tenant_id, require_verified=not (tenant and tenant.lifecycle == "closed"))
    if len(candidates) != 1:
        return None
    admin_id = candidates[0].id
    if db.scalar(select(func.count()).select_from(TenantAdmin).where(
        TenantAdmin.admin_user_id == admin_id, TenantAdmin.active.is_(True),
    )) != 1:
        return None
    return db.get(AdminUser, admin_id, populate_existing=True)


def _payload(row):
    if not row.encrypted_payload:
        raise _error()
    return decrypt_sensitive_payload(row.encrypted_payload, context=f"access-recovery:{row.id}")


def _save_payload(row, payload):
    row.encrypted_payload = encrypt_sensitive_payload(payload, context=f"access-recovery:{row.id}")


def _expire(row):
    row.state = "expired"
    row.token_hash = None
    row.encrypted_payload = None


def cleanup_expired_recoveries(db, *, tenant_id=None):
    # Compatibilidade da limpeza técnica com schemas anteriores à expansão.
    schema = (db.get_bind().get_execution_options().get("schema_translate_map") or {}).get(None)
    if not inspect(db.get_bind()).has_table("photographer_access_recovery", schema=schema):
        return 0
    statement = select(PhotographerAccessRecovery).where(
        PhotographerAccessRecovery.state.in_(("email_pending", "email_verified")),
        PhotographerAccessRecovery.expires_at <= now(),
    )
    if tenant_id is not None:
        statement = statement.where(PhotographerAccessRecovery.tenant_id == tenant_id)
    rows = list(db.scalars(statement.with_for_update(skip_locked=True)))
    for row in rows:
        _expire(row)
    return len(rows)


def summary(row):
    def utc(value):
        return (value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)) if value else None
    state = "expired" if row.state in {"email_pending", "email_verified"} and expired(row.expires_at) else row.state
    return {"request_id": str(row.id), "state": state, "created_at": utc(row.created_at),
            "expires_at": utc(row.expires_at), "email_verified_at": utc(row.email_verified_at),
            "completed_at": utc(row.completed_at), "reset_totp": row.reset_totp,
            "reason_code": row.reason_code}


def _collision(db, email, admin_id):
    return bool(db.scalar(select(AdminUser.id).where(
        func.lower(AdminUser.email) == email, AdminUser.id != admin_id,
    ).limit(1)) or db.scalar(select(PhotographerSignup.id).where(
        func.lower(PhotographerSignup.email) == email,
        or_(PhotographerSignup.reserved_admin_id != admin_id, PhotographerSignup.reserved_admin_id.is_(None)),
    ).limit(1)))


def start_recovery(db, session, tenant_id, payload, *, ip="unknown"):
    console.require_console_owner(db, session)
    tenant = db.get(Tenant, tenant_id, with_for_update=True)
    admin = _target(db, tenant_id) if tenant else None
    if not admin or admin.id == session.subject_id or not payload.identity_confirmed:
        raise _error(409)
    try:
        email = normalize_admin_email(payload.new_email)
    except AdminAccountError:
        raise _error(422) from None
    fingerprint = pii_fingerprint(json.dumps({
        "tenant": str(tenant_id), "admin": str(admin.id), "email": email,
        "version": payload.expected_version, "reason": payload.reason_code,
        "reset_totp": payload.reset_totp, "confirmed": payload.identity_confirmed,
    }, sort_keys=True))
    prior = db.get(PhotographerAccessRecovery, payload.request_id)
    if prior:
        if prior.actor_admin_id != session.subject_id or prior.request_fingerprint != fingerprint:
            raise _error(409)
        if prior.state in {"email_pending", "email_verified"} and expired(prior.expires_at):
            _expire(prior)
        return summary(prior)
    if version(admin) != payload.expected_version:
        raise _error(409)
    _lock_signup_identities(db)
    db.refresh(admin)
    if version(admin) != payload.expected_version:
        raise _error(409)
    if _collision(db, email, admin.id):
        raise _error(409)
    for old in db.scalars(select(PhotographerAccessRecovery).where(
        PhotographerAccessRecovery.tenant_id == tenant_id,
        PhotographerAccessRecovery.state.in_(("email_pending", "email_verified")),
    ).with_for_update()):
        _expire(old)
    closure = db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant_id, TenantClosureRequest.state == "closed",
    ).order_by(TenantClosureRequest.closed_at.desc()).limit(1)) if tenant.lifecycle == "closed" else None
    raw = secrets.token_urlsafe(32)
    row = PhotographerAccessRecovery(
        id=payload.request_id, tenant_id=tenant_id, admin_user_id=admin.id,
        actor_admin_id=session.subject_id, closure_request_id=closure.id if closure else None,
        identity_confirmed=True, reason_code=payload.reason_code, reset_totp=payload.reset_totp,
        expected_version=payload.expected_version, request_fingerprint=fingerprint,
        recipient_fingerprint=pii_fingerprint(email), token_hash=token_hash(raw),
        expires_at=now() + timedelta(minutes=15), state="email_pending",
    )
    _save_payload(row, {"email": email})
    db.add(row)
    db.flush()
    link = sensitive_link("/photographer-access-recovery", raw)
    enqueue_email(db, kind="email_verification", source_type="photographer_access_recovery",
                  source_id=str(row.id), recipient=email,
                  subject="Recuperação assistida · Pick-your-Pic",
                  text_body="Confirme seu novo e-mail e defina sua senha pelo link de uso único: " + link,
                  idempotency_key=f"email:access-recovery:{row.id}", expires_at=row.expires_at)
    audit(db, "photographer.access_recovery.requested", str(row.id), tenant_id=tenant_id)
    return summary(row)


def verify_recovery(db, payload):
    candidate = db.scalar(select(PhotographerAccessRecovery).where(
        PhotographerAccessRecovery.token_hash == token_hash(payload.token.get_secret_value()),
    ))
    if not candidate:
        raise _error()
    db.get(Tenant, candidate.tenant_id, with_for_update=True)
    row = db.scalar(select(PhotographerAccessRecovery).where(
        PhotographerAccessRecovery.id == candidate.id,
    ).with_for_update().execution_options(populate_existing=True))
    if row.state != "email_pending" or expired(row.expires_at) or not row.token_hash:
        raise _error()
    admin = _target(db, row.tenant_id)
    if not admin or admin.id != row.admin_user_id or version(admin) != row.expected_version:
        raise _error()
    data = _payload(row)
    from app.auth import validate_admin_password
    try:
        validate_admin_password(payload.new_password.get_secret_value(), email=data["email"],
                                current_password_hash=admin.password_hash)
    except ValueError:
        raise HTTPException(422, "Escolha uma senha forte e diferente da anterior.", headers=HEADERS) from None
    data["password_hash"] = password_hasher.hash(payload.new_password.get_secret_value())
    _save_payload(row, data)
    row.token_hash = None
    row.email_verified_at = now()
    row.state = "email_verified"
    audit(db, "photographer.access_recovery.email_verified", str(row.id), tenant_id=row.tenant_id)
    return {"message": "E-mail confirmado. Aguarde o proprietário concluir o atendimento."}


def commit_recovery(db, session, tenant_id, request_id, payload, *, ip="unknown"):
    console.require_console_owner(db, session)
    db.get(Tenant, tenant_id, with_for_update=True)
    row = db.scalar(select(PhotographerAccessRecovery).where(
        PhotographerAccessRecovery.id == request_id, PhotographerAccessRecovery.tenant_id == tenant_id,
    ).with_for_update().execution_options(populate_existing=True))
    if not row or row.actor_admin_id != session.subject_id:
        raise _error(409)
    _lock_signup_identities(db)
    owner = db.get(AdminUser, session.subject_id, with_for_update=True, populate_existing=True)
    try:
        step = console.reauthenticate_console_owner(owner, payload)
    except AdminAccountError:
        raise _error(403) from None
    if row.state == "completed":
        owner.totp_last_used_step = step
        return summary(row)
    if row.state != "email_verified" or expired(row.expires_at) or not row.identity_confirmed:
        raise _error(409)
    admin = _target(db, tenant_id)
    if not admin or admin.id != row.admin_user_id or admin.id == session.subject_id or version(admin) != row.expected_version:
        raise _error(409)
    data = _payload(row)
    if _collision(db, data["email"], admin.id):
        raise _error(409)
    old_email = admin.email
    admin.email = data["email"]
    admin.email_verified = True
    admin.password_hash = data["password_hash"]
    invalidate_admin_security_material(db, admin.id)
    if row.reset_totp:
        admin.totp_enabled = False
        admin._totp_secret_envelope = None
        admin._totp_secret_legacy = None
        admin._totp_secret_value = None
        admin._totp_secret_needs_encryption = False
        admin.totp_last_used_step = None
    for code in db.scalars(select(AdminTotpRecoveryCode).where(
        AdminTotpRecoveryCode.admin_user_id == admin.id, AdminTotpRecoveryCode.revoked_at.is_(None),
    )):
        code.revoked_at = now()
    for challenge in db.scalars(select(AuthChallenge).where(
        AuthChallenge.kind == "admin_totp", AuthChallenge.subject == str(admin.id), AuthChallenge.used_at.is_(None),
    )):
        challenge.used_at = now()
    revoke_subject_sessions(db, "admin", admin.id)
    signup = db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.reserved_admin_id == admin.id, PhotographerSignup.activated_tenant_id == tenant_id,
    ))
    if signup:
        signup.email = admin.email
    queue_previous_email_notice(db, admin_id=admin.id, previous_email=old_email, action_token_id=row.id)
    owner.totp_last_used_step = step
    row.state = "completed"
    row.completed_at = now()
    row.encrypted_payload = None
    row.token_hash = None
    audit(db, "photographer.access_recovery.completed", str(row.id), tenant_id=tenant_id)
    db.flush()
    return summary(row)


def validate_recovery_email(db, delivery):
    row = db.get(PhotographerAccessRecovery, UUID(delivery.source_id), populate_existing=True)
    if not row or row.state != "email_pending" or expired(row.expires_at):
        raise EmailConfigurationError("Atendimento indisponível.")
    admin = _target(db, row.tenant_id)
    from app.system_monitor.access import is_owner
    if not admin or admin.id != row.admin_user_id or version(admin) != row.expected_version or not is_owner(db, row.actor_admin_id):
        raise EmailConfigurationError("Atendimento indisponível.")
    return row.recipient_fingerprint


def completed_closure_proof(db, tenant_id, closure_id, admin_id=None):
    """CPF/contato novos não substituem a autorização administrativa efetivada."""
    statement = select(PhotographerAccessRecovery).where(
        PhotographerAccessRecovery.tenant_id == tenant_id,
        PhotographerAccessRecovery.closure_request_id == closure_id,
        PhotographerAccessRecovery.state == "completed",
        PhotographerAccessRecovery.identity_confirmed.is_(True),
        PhotographerAccessRecovery.email_verified_at.is_not(None),
        PhotographerAccessRecovery.completed_at.is_not(None),
    ).order_by(PhotographerAccessRecovery.completed_at.desc())
    if admin_id:
        statement = statement.where(PhotographerAccessRecovery.admin_user_id == admin_id)
    admin = _target(db, tenant_id)
    if not admin or not admin.email_verified:
        return None
    for row in db.scalars(statement):
        if row.admin_user_id == admin.id and row.recipient_fingerprint == pii_fingerprint(admin.email):
            return row
    return None


def _recheck(db, request, session):
    renewed = console.current_session(request, Role.ADMIN, platform_scope=True)
    if (renewed.id, renewed.subject_id, renewed.tenant_id) != (session.id, session.subject_id, session.tenant_id):
        raise _error(403)
    console.require_console_owner(db, renewed)


@owner_router.get("/tenants/{tenant_id}/access-recovery")
def lookup(tenant_id: UUID, request: Request, response: Response):
    response.headers.update(HEADERS)
    with console.authorized(request) as (db, _session):
        admin = _target(db, tenant_id)
        if not admin:
            return {"available": False}
        rows = list(db.scalars(select(PhotographerAccessRecovery).where(
            PhotographerAccessRecovery.tenant_id == tenant_id,
        ).order_by(PhotographerAccessRecovery.created_at.desc()).limit(10)))
        return {"available": True, "version": version(admin), "email_masked": mask_email(admin.email),
                "totp_enabled": admin.totp_enabled, "requests": [summary(row) for row in rows]}


@owner_router.post("/tenants/{tenant_id}/access-recovery")
def start(tenant_id: UUID, payload: StartInput, request: Request, response: Response):
    from app.main import require_same_origin
    require_same_origin(request)
    response.headers.update(HEADERS)
    with console.authorized(request) as (db, session):
        enforce_rate_limit(db, "owner_access_recovery_start", str(session.subject_id),
                           request.client.host if request.client else "unknown")
        db.commit()
        try:
            result = start_recovery(db, session, tenant_id, payload)
            _recheck(db, request, session)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise _error(409) from None
        except (AdminSecurityConfigurationError, EmailConfigurationError, TotpSecretError):
            db.rollback()
            raise _error(503) from None
        return result


@owner_router.post("/tenants/{tenant_id}/access-recovery/{request_id}/commit")
def commit(tenant_id: UUID, request_id: UUID, payload: CommitInput, request: Request, response: Response):
    from app.main import require_same_origin
    require_same_origin(request)
    response.headers.update(HEADERS)
    with console.authorized(request) as (db, session):
        enforce_rate_limit(db, "owner_access_recovery_commit", str(session.subject_id),
                           request.client.host if request.client else "unknown")
        db.commit()
        try:
            result = commit_recovery(db, session, tenant_id, request_id, payload,
                                     ip=request.client.host if request.client else "unknown")
            _recheck(db, request, session)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise _error(409) from None
        except (TotpSecretError, AdminSecurityConfigurationError, EmailConfigurationError):
            db.rollback()
            raise _error(503) from None
        return result


@public_router.post("/confirm")
def confirm(payload: VerifyInput, request: Request, response: Response,
            db: Annotated[Session, Depends(database)]):
    from app.main import require_same_origin
    require_same_origin(request)
    response.headers.update(HEADERS)
    enforce_rate_limit(db, "access_recovery_confirm_ip", "public", request.client.host if request.client else "unknown")
    db.commit()
    result = verify_recovery(db, payload)
    db.commit()
    return result
