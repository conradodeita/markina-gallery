"""Recuperação assistida sem transferência de senha, segredo ou sessão."""

from datetime import timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select, update

from app import platform_console as console
from app.admin_account import AdminAccountError, mask_email
from app.admin_security import AdminSecurityConfigurationError, invalidate_admin_security_material
from app.auth import (
    AdminTotpRecoveryCode,
    AdminUser,
    AuthChallenge,
    PhotographerSignup,
    PlatformAdminEvent,
    Role,
    Tenant,
    TenantAdmin,
    enforce_rate_limit,
    now,
    pii_fingerprint,
    revoke_subject_sessions,
)
from app.email_delivery import enqueue_email
from app.mercadopago_api import SensitiveRoute
from app.system_monitor.models import PlatformOwner
from app.totp_crypto import TotpSecretError

router = APIRouter(prefix="/admin/platform/console", route_class=SensitiveRoute)
HEADERS = console.HEADERS


class RevokeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    reason_code: Literal["lost_device", "authenticator_unavailable", "assisted_recovery"]
    expected_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_password: SecretStr
    totp_code: SecretStr


def factor_version(admin_id, envelope, legacy):
    material = envelope or legacy
    return pii_fingerprint(f"totp-support:{admin_id}:{material}") if material else None


def _eligible(db, tenant_id, admin_id=None, *, require_verified=True):
    statement = select(AdminUser.id, AdminUser.email, AdminUser.totp_enabled,
                       AdminUser._totp_secret_envelope.label("envelope"),
                       AdminUser._totp_secret_legacy.label("legacy")).join(
        TenantAdmin, TenantAdmin.admin_user_id == AdminUser.id,
    ).join(PhotographerSignup, PhotographerSignup.reserved_admin_id == AdminUser.id).where(
        TenantAdmin.tenant_id == tenant_id, TenantAdmin.active.is_(True),
        PhotographerSignup.activated_tenant_id == tenant_id, PhotographerSignup.state == "active",
        ~select(PlatformOwner.admin_user_id).where(PlatformOwner.admin_user_id == AdminUser.id).exists(),
    )
    if require_verified:
        statement = statement.where(AdminUser.email_verified.is_(True))
    if admin_id:
        statement = statement.where(AdminUser.id == admin_id)
    return db.execute(statement.limit(2)).all()


@router.get("/tenants/{tenant_id}/totp-support")
def target(tenant_id: UUID, request: Request, response: Response):
    response.headers.update(HEADERS)
    with console.authorized(request) as (db, _session):
        if db.get(Tenant, tenant_id) is None:
            raise HTTPException(404, "Conta não encontrada.", headers=HEADERS)
        rows = _eligible(db, tenant_id)
        if len(rows) != 1:
            return {"available": False}
        row = rows[0]
        version = factor_version(row.id, row.envelope, row.legacy) if row.totp_enabled else None
        return {"available": True, "admin_id": str(row.id), "email_masked": mask_email(row.email),
                "totp_enabled": row.totp_enabled, "version": version}


def _event(db, session, tenant_id, admin_id, payload, *, success):
    event = PlatformAdminEvent(
        actor_admin_id=session.subject_id, tenant_id=tenant_id, object_id=admin_id,
        action="photographer.totp_revoked" if success else "photographer.totp_revoke_denied",
        result="success" if success else "denied", request_id=payload.request_id if success else None,
        reason_code=payload.reason_code, target_version=payload.expected_version,
        previous_status="totp_active" if success else None, next_status="password_only" if success else None,
    )
    db.add(event)
    return event


def revoke_photographer_totp(db, session, tenant_id, admin_id, payload, *, ip_address="unknown"):
    console.require_console_owner(db, session)
    try:
        owner = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id).with_for_update()
                          .execution_options(populate_existing=True))
    except TotpSecretError:
        raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
    previous = db.scalar(select(PlatformAdminEvent).where(PlatformAdminEvent.request_id == payload.request_id))
    if previous:
        if (previous.actor_admin_id, previous.tenant_id, previous.object_id, previous.action,
            previous.reason_code, previous.target_version) != (
            session.subject_id, tenant_id, admin_id, "photographer.totp_revoked", payload.reason_code, payload.expected_version,
        ):
            raise HTTPException(409, "Identificador já utilizado em outra operação.", headers=HEADERS)
        return {"completed": True, "replayed": True}
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update())
    rows = _eligible(db, tenant_id, admin_id)
    if not tenant or tenant_id == session.tenant_id or admin_id == session.subject_id or len(rows) != 1:
        _event(db, session, tenant_id if tenant else None, admin_id, payload, success=False)
        db.commit()
        raise HTTPException(409, "Conta não elegível para recuperação assistida.", headers=HEADERS)
    try:
        admin = db.scalar(select(AdminUser).where(AdminUser.id == admin_id).with_for_update()
                          .execution_options(populate_existing=True))
    except TotpSecretError:
        raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
    membership = db.scalar(select(TenantAdmin).where(
        TenantAdmin.tenant_id == tenant_id, TenantAdmin.admin_user_id == admin_id, TenantAdmin.active.is_(True),
    ).with_for_update())
    if not membership:
        raise HTTPException(409, "O vínculo da conta mudou. Consulte novamente.", headers=HEADERS)
    if not admin.totp_enabled or factor_version(admin.id, admin._totp_secret_envelope, admin._totp_secret_legacy) != payload.expected_version:
        raise HTTPException(409, "O fator da conta mudou. Consulte novamente antes de confirmar.", headers=HEADERS)
    enforce_rate_limit(db, "platform_totp_revoke", str(session.subject_id), ip_address)
    try:
        step = console.reauthenticate_console_owner(owner, payload)
    except AdminAccountError:
        _event(db, session, tenant_id, admin_id, payload, success=False)
        db.commit()
        raise HTTPException(403, "Não foi possível confirmar a operação.", headers=HEADERS) from None
    except TotpSecretError:
        db.rollback()
        raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
    console.require_console_owner(db, session)
    owner.totp_last_used_step = step
    admin.totp_enabled = False
    admin._totp_secret_envelope = None
    admin._totp_secret_legacy = None
    admin._totp_secret_value = None
    admin._totp_secret_needs_encryption = False
    admin.totp_last_used_step = None
    invalidate_admin_security_material(db, admin_id)
    db.execute(update(AdminTotpRecoveryCode).where(AdminTotpRecoveryCode.admin_user_id == admin_id,
                                                  AdminTotpRecoveryCode.revoked_at.is_(None)).values(revoked_at=now()))
    db.execute(update(AuthChallenge).where(AuthChallenge.kind == "admin_totp", AuthChallenge.subject == str(admin_id),
                                           AuthChallenge.used_at.is_(None)).values(used_at=now()))
    revoke_subject_sessions(db, "admin", admin_id)
    try:
        enqueue_email(db, kind="security_notice", source_type="admin_user", source_id=str(admin_id),
                      recipient=admin.email, subject="Autenticador revogado em atendimento · Pick-your-Pic",
                      text_body="O proprietário do Pick-your-Pic revogou seu autenticador em atendimento. Sua senha não foi alterada. "
                      "Entre novamente com sua senha; você poderá configurar outro autenticador. Se não reconhece o atendimento, contate o suporte.",
                      idempotency_key=f"email:totp-assisted-revoke:{payload.request_id}", expires_at=now()+timedelta(days=1))
    except (AdminSecurityConfigurationError, ValueError, OSError):
        db.rollback()
        raise HTTPException(503, "Não foi possível preparar o aviso. A operação não foi concluída.", headers=HEADERS) from None
    _event(db, session, tenant_id, admin_id, payload, success=True)
    db.flush()
    return {"completed": True, "replayed": False}


@router.post("/tenants/{tenant_id}/photographers/{admin_id}/revoke-totp")
def revoke(tenant_id: UUID, admin_id: UUID, payload: RevokeInput, request: Request, response: Response):
    from app.main import require_same_origin
    require_same_origin(request)
    response.headers.update(HEADERS)
    with console.authorized(request) as (db, session):
        result = revoke_photographer_totp(db, session, tenant_id, admin_id, payload,
                                         ip_address=request.client.host if request.client else "unknown")
        renewed = console.current_session(request, Role.ADMIN, platform_scope=True)
        if (renewed.id, renewed.subject_id, renewed.tenant_id) != (session.id, session.subject_id, session.tenant_id):
            db.rollback()
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        console.require_console_owner(db, renewed)
        db.commit()
        return result
