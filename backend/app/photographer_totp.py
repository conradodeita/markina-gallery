"""Ativação voluntária do autenticador para fotógrafo originado no website."""

from __future__ import annotations

import base64
import os
from datetime import timedelta
from io import BytesIO
from typing import Annotated
from uuid import UUID, uuid4

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, SecretStr
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.admin_account import AdminAccountError, active_admin_for_session, reauthenticate_admin
from app.admin_security import invalidate_admin_security_material
from app.auth import (
    AdminTotpEnrollment,
    AdminTotpRecoveryCode,
    AdminUser,
    AuthSession,
    PhotographerSignup,
    Role,
    SessionLocal,
    Tenant,
    TenantAdmin,
    audit,
    current_session,
    enforce_rate_limit,
    expired,
    now,
    revoke_subject_sessions,
)
from app.mercadopago_api import SensitiveRoute
from app.system_monitor.models import PlatformOwner
from app.totp_crypto import TotpSecretCipher, TotpSecretError
from app.totp_recovery import create_recovery_codes, hash_recovery_code, recovery_code_selector
from app.totp_verification import matching_unused_totp_step

HEADERS = {"Cache-Control": "private, no-store", "Pragma": "no-cache"}
router = APIRouter(prefix="/admin/security/totp/enrollment", route_class=SensitiveRoute)


def database():
    with SessionLocal() as db:
        try:
            yield db
        except (TotpSecretError, SQLAlchemyError):
            db.rollback()
            raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None


Database = Annotated[Session, Depends(database)]


class StartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr


class ConfirmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enrollment_id: UUID
    code: SecretStr


def _context(request: Request, db: Session):
    from app.main import require_same_origin
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    try:
        active_admin_for_session(db, session)
    except AdminAccountError:
        raise HTTPException(403, "Acesso negado.", headers=HEADERS) from None
    signup = db.scalar(select(PhotographerSignup.id).where(
        PhotographerSignup.reserved_admin_id == session.subject_id,
        PhotographerSignup.activated_tenant_id == session.tenant_id,
        PhotographerSignup.state == "active",
    ))
    owner = db.scalar(select(PlatformOwner.admin_user_id).where(PlatformOwner.admin_user_id == session.subject_id))
    if not signup or owner:
        raise HTTPException(403, "Acesso negado.", headers=HEADERS)
    scope = "photographer_totp_confirm" if request.url.path.endswith("/confirm") else "photographer_totp_start"
    enforce_rate_limit(db, scope, str(session.subject_id),
                       request.client.host if request.client else "unknown")
    db.commit()
    tenant = db.scalar(select(Tenant).where(Tenant.id == session.tenant_id).with_for_update().execution_options(populate_existing=True))
    if not tenant or tenant.status != "active":
        raise HTTPException(403, "Acesso negado.", headers=HEADERS)
    admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id).with_for_update().execution_options(populate_existing=True))
    membership = db.scalar(select(TenantAdmin).where(
        TenantAdmin.tenant_id == session.tenant_id, TenantAdmin.admin_user_id == session.subject_id,
        TenantAdmin.active.is_(True),
    ).with_for_update())
    active_session = db.get(AuthSession, session.id, with_for_update=True, populate_existing=True)
    if not admin or not membership or not active_session or active_session.revoked_at or expired(active_session.expires_at):
        raise HTTPException(403, "Acesso negado.", headers=HEADERS)
    if admin.totp_enabled:
        raise HTTPException(409, "O autenticador já está ativo.", headers=HEADERS)
    return session, admin


def _failure():
    return HTTPException(400, "Não foi possível confirmar o autenticador. Reinicie a configuração se necessário.", headers=HEADERS)


def _enrollment_context(attempt_id, tenant_id, session_id):
    return f"photographer-enrollment:{attempt_id}:{tenant_id}:{session_id}"


@router.post("")
def begin(payload: StartInput, request: Request, response: Response, db: Database):
    session, admin = _context(request, db)
    try:
        reauthenticate_admin(admin, payload.current_password.get_secret_value())
    except AdminAccountError:
        audit(db, "photographer_totp.start_rejected", str(admin.id), tenant_id=session.tenant_id)
        db.commit()
        raise _failure() from None
    previous = db.scalar(select(AdminTotpEnrollment).where(AdminTotpEnrollment.admin_user_id == admin.id))
    if previous:
        db.delete(previous)
        db.flush()
    attempt_id = uuid4()
    secret = pyotp.random_base32()
    expiry = now() + timedelta(minutes=5)
    attempt = AdminTotpEnrollment(
        id=attempt_id, admin_user_id=admin.id, tenant_id=session.tenant_id, session_id=session.id,
        secret_envelope=TotpSecretCipher.from_environment().encrypt(
            secret, admin_id=admin.id, context=_enrollment_context(attempt_id, session.tenant_id, session.id),
        ),
        expires_at=expiry,
    )
    db.add(attempt)
    uri = pyotp.TOTP(secret).provisioning_uri(name=admin.email, issuer_name="Pick-your-Pic")
    image = BytesIO()
    qrcode.make(uri).save(image, format="PNG")
    audit(db, "photographer_totp.started", str(attempt_id), tenant_id=session.tenant_id)
    db.commit()
    response.headers.update(HEADERS)
    return {"enrollment_id": str(attempt_id), "secret": secret, "expires_at": expiry.isoformat(),
            "qr_data_url": "data:image/png;base64," + base64.b64encode(image.getvalue()).decode("ascii")}


@router.post("/confirm")
def confirm(payload: ConfirmInput, request: Request, response: Response, db: Database):
    session, admin = _context(request, db)
    attempt = db.scalar(select(AdminTotpEnrollment).where(
        AdminTotpEnrollment.id == payload.enrollment_id,
        AdminTotpEnrollment.admin_user_id == admin.id,
        AdminTotpEnrollment.tenant_id == session.tenant_id,
        AdminTotpEnrollment.session_id == session.id,
    ).with_for_update())
    if not attempt or attempt.used_at or not attempt.secret_envelope:
        raise _failure()
    if expired(attempt.expires_at) or attempt.attempts >= 5:
        attempt.secret_envelope = None
        attempt.used_at = now()
        db.commit()
        raise _failure()
    secret = TotpSecretCipher.from_environment().decrypt(
        attempt.secret_envelope, admin_id=admin.id,
        context=_enrollment_context(attempt.id, attempt.tenant_id, attempt.session_id),
    )
    step = matching_unused_totp_step(secret, payload.code.get_secret_value(), None, valid_window=1)
    if step is None:
        attempt.attempts += 1
        if attempt.attempts >= 5:
            attempt.secret_envelope = None
            attempt.used_at = now()
        audit(db, "photographer_totp.confirm_rejected", str(attempt.id), tenant_id=session.tenant_id)
        db.commit()
        raise _failure()
    admin.totp_enabled = True
    admin.totp_secret = secret
    admin.totp_last_used_step = step
    attempt.secret_envelope = None
    attempt.used_at = now()
    invalidate_admin_security_material(db, admin.id)
    db.execute(update(AdminTotpRecoveryCode).where(
        AdminTotpRecoveryCode.admin_user_id == admin.id,
        AdminTotpRecoveryCode.revoked_at.is_(None),
    ).values(revoked_at=now()))
    codes = create_recovery_codes()
    db.add_all([AdminTotpRecoveryCode(admin_user_id=admin.id, code_selector=recovery_code_selector(code),
                                    code_hash=hash_recovery_code(code)) for code in codes])
    revoke_subject_sessions(db, "admin", admin.id)
    audit(db, "photographer_totp.activated", str(attempt.id), tenant_id=session.tenant_id)
    db.commit()
    response.headers.update(HEADERS)
    response.delete_cookie(os.getenv("SESSION_COOKIE_NAME", "markina_session"), path="/")
    return {"codes": codes, "message": "Autenticador ativado. Guarde os códigos e entre novamente."}
