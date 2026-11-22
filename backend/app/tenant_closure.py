"""Transições locais de encerramento; não executa transferência ou expurgo."""

from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    AuthSession,
    PhotographerCreditEntry,
    PhotographerTermsAcceptance,
    PushSubscription,
    Tenant,
    TenantAdmin,
    TenantClosureRequest,
    TenantCreditWallet,
    audit,
    now,
)
from app.photographer_terms import latest_published


class ClosureInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    confirm_closure: bool
    acknowledge_remaining_balance: bool
    expected_balance: int = Field(ge=0)
    terms_version: str = Field(min_length=1, max_length=80)
    terms_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def require_new_work(db: Session, tenant_id: UUID, *, no_key_update: bool = False) -> None:
    """Serializa novo trabalho antes de bytes/reserva com a solicitação de saída."""
    # Renovar prazo não altera chaves do tenant. NO KEY UPDATE ainda conflita
    # com encerramento, mas permite KEY SHARE das FKs do arquivo frio.
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id)
                       .with_for_update(key_share=no_key_update).execution_options(populate_existing=True))
    if not tenant or tenant.status != "active":
        raise HTTPException(403, "Acesso negado.")
    if tenant.lifecycle != "open":
        raise HTTPException(409, "A conta está em encerramento e não aceita novas galerias ou uploads.")


def closure_payload(row: TenantClosureRequest) -> dict:
    return {"request_id": str(row.request_id), "state": row.state,
            "requested_at": row.requested_at.isoformat(),
            "closed_at": row.closed_at.isoformat() if row.closed_at else None,
            "balance_snapshot": row.balance_snapshot}


def request_closure(db: Session, session, payload: ClosureInput) -> dict:
    if session.role != "admin":
        raise HTTPException(403, "Acesso negado.")
    tenant = db.scalar(select(Tenant).where(Tenant.id == session.tenant_id)
                       .with_for_update().execution_options(populate_existing=True))
    membership = db.scalar(select(TenantAdmin).where(
        TenantAdmin.tenant_id == session.tenant_id,
        TenantAdmin.admin_user_id == session.subject_id, TenantAdmin.active.is_(True)))
    admin = db.get(AdminUser, session.subject_id, populate_existing=True)
    if not tenant or tenant.status != "active" or not membership or not admin or not admin.email_verified:
        raise HTTPException(403, "Acesso negado.")
    prior = db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant.id,
        TenantClosureRequest.request_id == payload.request_id))
    if prior:
        if (prior.requested_by != admin.id or prior.balance_snapshot != payload.expected_balance
                or prior.terms_version != payload.terms_version
                or prior.terms_sha256 != payload.terms_sha256
                or not payload.confirm_closure or not payload.acknowledge_remaining_balance):
            raise HTTPException(409, "Solicitação incompatível com o registro existente.")
        return {**closure_payload(prior), "replayed": True}
    if tenant.lifecycle != "open":
        raise HTTPException(409, "A conta já possui uma solicitação de encerramento.")
    if not payload.confirm_closure or not payload.acknowledge_remaining_balance:
        raise HTTPException(422, "Confirme as consequências e o saldo antes de encerrar.")
    acceptance = db.scalar(select(PhotographerTermsAcceptance).where(
        PhotographerTermsAcceptance.tenant_id == tenant.id,
        PhotographerTermsAcceptance.admin_user_id == admin.id,
        PhotographerTermsAcceptance.terms_version == payload.terms_version,
        PhotographerTermsAcceptance.terms_sha256 == payload.terms_sha256))
    published = latest_published(db)
    if not acceptance or (published and published.terms_version != acceptance.terms_version):
        raise HTTPException(409, "Confira e aceite os Termos vigentes antes de continuar.")
    wallet = db.scalar(select(TenantCreditWallet).where(TenantCreditWallet.tenant_id == tenant.id)
                       .with_for_update())
    if wallet is None:
        raise HTTPException(503, "Não foi possível conferir o saldo. Tente novamente.")
    balance = int(db.scalar(select(func.coalesce(func.sum(PhotographerCreditEntry.delta), 0))
                           .where(PhotographerCreditEntry.tenant_id == tenant.id)) or 0)
    if balance < 0 or balance != payload.expected_balance:
        raise HTTPException(409, "O saldo mudou. Confira novamente antes de confirmar.")
    row = TenantClosureRequest(tenant_id=tenant.id, request_id=payload.request_id,
                               requested_by=admin.id, terms_version=acceptance.terms_version,
                               terms_sha256=acceptance.terms_sha256, balance_snapshot=balance,
                               balance_acknowledged=True)
    db.add(row)
    tenant.lifecycle = "closing"
    audit(db, "tenant.closure_requested", str(payload.request_id), tenant_id=tenant.id)
    db.flush()
    return {**closure_payload(row), "replayed": False}


def finalize_closure(db: Session, tenant_id: UUID) -> dict:
    """Revalida sob o lock também usado por checkout e novo trabalho."""
    from app.tenant_closure_obligations import evaluate_closure

    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id)
                       .with_for_update().execution_options(populate_existing=True))
    if tenant is None:
        raise HTTPException(404, "Conta indisponível.")
    row = db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant_id,
        TenantClosureRequest.state.in_(("closing", "closed")),
    ).order_by(TenantClosureRequest.requested_at.desc()).with_for_update().limit(1))
    if row is None:
        raise HTTPException(409, "Não há encerramento solicitado.")
    if row.state == "closed" and tenant.lifecycle == "closed":
        return {**closure_payload(row), "ready": True, "replayed": True, "blockers": []}
    observation = evaluate_closure(db, tenant_id)
    if not observation["ready"]:
        return {**closure_payload(row), **observation, "replayed": False}
    from app.facial.closure_cleanup import cleanup_tenant_biometrics

    if not cleanup_tenant_biometrics(db, tenant_id=tenant_id, closure=row):
        return {
            **closure_payload(row),
            "ready": False,
            "blockers": ["biometric_cleanup_pending"],
            "replayed": False,
        }
    instant = now()
    row.state, row.closed_at = "closed", instant
    tenant.lifecycle = "closed"
    db.execute(update(AuthSession).where(
        AuthSession.tenant_id == tenant_id, AuthSession.revoked_at.is_(None),
    ).values(revoked_at=instant))
    db.execute(update(PushSubscription).where(
        PushSubscription.tenant_id == tenant_id, PushSubscription.active.is_(True),
    ).values(active=False, generation=PushSubscription.generation + 1, updated_at=instant))
    audit(db, "tenant.closure_completed", str(row.request_id), tenant_id=tenant_id)
    db.info.setdefault("tenant_closure_transition", set()).add(tenant_id)
    db.flush()
    return {**closure_payload(row), **observation, "replayed": False}
