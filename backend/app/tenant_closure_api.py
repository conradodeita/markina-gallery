"""API autenticada para solicitar e acompanhar o encerramento do fotógrafo."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    PhotographerCreditEntry,
    PhotographerTermsAcceptance,
    Role,
    SessionLocal,
    Tenant,
    TenantAdmin,
    TenantClosureRequest,
    TenantCreditWallet,
    current_session,
)
from app.mercadopago_api import SensitiveRoute
from app.photographer_onboarding import _terms_version
from app.tenant_closure import ClosureInput, closure_payload, request_closure
from app.tenant_closure_obligations import evaluate_closure

router = APIRouter(prefix="/admin/closure", route_class=SensitiveRoute)
HEADERS = {"Cache-Control": "private, no-store, max-age=0"}

_BLOCKER_MESSAGES = {
    "open_order": "Há pedidos em andamento que precisam ser concluídos.",
    "pending_payment": "Há pagamentos aguardando confirmação ou conciliação.",
    "financial_review": "Existe uma revisão financeira pendente.",
    "processing_pending": "Há trabalhos ou notificações em andamento.",
    "biometric_cleanup_pending": "O encerramento está sendo finalizado.",
    "access_window": "Algumas pastas ainda estão dentro do prazo de acesso informado aos clientes.",
    "deadline_required": "Defina um prazo de acesso para as pastas antigas que ainda não têm prazo.",
    "media_not_archived": "O tratamento das mídias ainda não foi concluído.",
    "archive_verification_pending": "A verificação de integridade de alguma pasta ainda está em andamento.",
    "account_not_closing": "O pedido de encerramento ainda não está disponível.",
    "source_unavailable": "Não foi possível conferir todas as pendências agora. Tente novamente.",
}


def database():
    with SessionLocal() as db:
        try:
            yield db
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(503, "Não foi possível consultar o encerramento agora.", headers=HEADERS) from None


Database = Annotated[Session, Depends(database)]


def _context(request: Request, db: Session):
    session = current_session(request, Role.ADMIN)
    tenant = db.scalar(select(Tenant).where(Tenant.id == session.tenant_id))
    admin = db.get(AdminUser, session.subject_id)
    membership = db.scalar(select(TenantAdmin.id).where(
        TenantAdmin.tenant_id == session.tenant_id,
        TenantAdmin.admin_user_id == session.subject_id,
        TenantAdmin.active.is_(True),
    ))
    if (
        not tenant or tenant.status != "active" or tenant.lifecycle == "closed"
        or not admin or not admin.email_verified or not membership
    ):
        raise HTTPException(403, "Acesso negado.", headers=HEADERS)
    return session, admin, tenant


def _terms_state(db: Session, *, tenant_id, admin_id) -> dict:
    configured = _terms_version(db)
    version = configured[0] if configured else None
    accepted = db.scalar(select(PhotographerTermsAcceptance).where(
        PhotographerTermsAcceptance.tenant_id == tenant_id,
        PhotographerTermsAcceptance.admin_user_id == admin_id,
        PhotographerTermsAcceptance.terms_version == (version or "__unavailable__"),
    )) if version else None
    return {
        "available": configured is not None,
        "accepted": accepted is not None,
        "version": version,
        "sha256": accepted.terms_sha256 if accepted else None,
    }


def _public_blockers(codes: list[str]) -> list[dict[str, str]]:
    return [
        {"code": code if code in _BLOCKER_MESSAGES else "other", "message": _BLOCKER_MESSAGES.get(
            code, "Ainda há uma etapa que precisa ser concluída antes do encerramento.",
        )}
        for code in codes
    ]


@router.get("")
def closure_status(request: Request, response: Response, db: Database) -> dict:
    response.headers.update(HEADERS)
    try:
        _session, admin, tenant = _context(request, db)
    except HTTPException as exc:
        exc.headers = {**(exc.headers or {}), **HEADERS}
        raise
    wallet = db.scalar(select(TenantCreditWallet).where(TenantCreditWallet.tenant_id == tenant.id))
    if wallet is None:
        raise HTTPException(503, "Não foi possível conferir o saldo agora.", headers=HEADERS)
    balance = int(db.scalar(select(func.coalesce(func.sum(PhotographerCreditEntry.delta), 0)).where(
        PhotographerCreditEntry.tenant_id == tenant.id,
    )) or 0)
    if balance < 0:
        raise HTTPException(503, "Não foi possível conferir o saldo agora.", headers=HEADERS)

    closure = db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant.id,
        TenantClosureRequest.state == "closing",
    ).order_by(TenantClosureRequest.requested_at.desc()).limit(1))
    blockers = evaluate_closure(db, tenant.id)["blockers"] if tenant.lifecycle == "closing" else []
    if (
        closure
        and closure.biometric_cleanup_started_at is not None
        and closure.biometric_cleanup_completed_at is None
        and "biometric_cleanup_pending" not in blockers
    ):
        blockers.append("biometric_cleanup_pending")
    return {
        "lifecycle": tenant.lifecycle,
        "credits_remaining": balance,
        "terms": _terms_state(db, tenant_id=tenant.id, admin_id=admin.id),
        "request": closure_payload(closure) if closure else None,
        "blockers": _public_blockers(blockers),
    }


@router.post("", status_code=202)
def submit_closure(
    payload: ClosureInput,
    request: Request,
    response: Response,
    db: Database,
) -> dict:
    from app.main import require_same_origin

    response.headers.update(HEADERS)
    try:
        require_same_origin(request)
        session, admin, tenant = _context(request, db)
        terms = _terms_state(db, tenant_id=tenant.id, admin_id=admin.id)
        if (
            not terms["available"] or not terms["accepted"]
            or terms["version"] != payload.terms_version
            or terms["sha256"] != payload.terms_sha256
        ):
            raise HTTPException(409, "Confira e aceite os Termos vigentes antes de continuar.", headers=HEADERS)
        result = request_closure(db, session, payload)
        db.commit()
        return result
    except HTTPException as exc:
        db.rollback()
        exc.headers = {**(exc.headers or {}), **HEADERS}
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, "Não foi possível registrar a solicitação agora.", headers=HEADERS) from None
