"""Console global privado: leitura mínima, sem ampliar concessões técnicas."""

import re
from contextlib import contextmanager
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.admin_account import AdminAccountError, reauthenticate_admin
from app.auth import (
    AdminUser,
    GoogleDriveConnection,
    ParentGallery,
    PhotoAsset,
    PlatformAdminEvent,
    Role,
    SessionLocal,
    Tenant,
    TenantAdmin,
    TenantClosureMediaDeletionBatch,
    TenantClosureRecoveryBatch,
    current_session,
    enforce_rate_limit,
    now,
)
from app.global_postgresql_backup_scheduler import read_global_postgresql_backup_status
from app.mercadopago_api import SensitiveRoute
from app.system_monitor.access import is_owner
from app.system_monitor.store import bounded
from app.tenancy import TenantContextError, require_admin_tenant
from app.tenant_hosts import CanonicalHostError, normalize_canonical_host
from app.totp_crypto import TotpSecretError
from app.totp_verification import matching_unused_totp_step

router = APIRouter(prefix="/admin/platform/console", route_class=SensitiveRoute)
HEADERS = {"Cache-Control": "private, no-store"}


class TenantClosureRecoveryBatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    duration_days: Literal[7, 14, 30]
    current_password: SecretStr
    totp_code: SecretStr


class TenantClosureReopenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    current_password: SecretStr
    totp_code: SecretStr


class TenantMediaDeletionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    confirm_phrase: str = Field(min_length=10, max_length=64)
    current_password: SecretStr
    totp_code: SecretStr


class TenantProfileReductionInput(TenantMediaDeletionInput):
    confirm_review: bool


def require_console_owner(db, session):
    if not is_owner(db, session.subject_id):
        raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
    tenant = require_admin_tenant(db, session.subject_id, platform_scope=True)
    if tenant.id != session.tenant_id:
        raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)


def _prior_admin_action_event(db, *, request_id, owner_id, tenant_id, action):
    prior = db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == request_id,
    ))
    if prior is not None and (prior.actor_admin_id, prior.tenant_id, prior.action, prior.result) != (
        owner_id, tenant_id, action, "success",
    ):
        raise HTTPException(409, "Identificador já utilizado em outra operação.", headers=HEADERS)
    return prior


@contextmanager
def authorized(request, *, audit_denial=True):
    try:
        session = current_session(request, Role.ADMIN, platform_scope=True)
        with SessionLocal() as db:
            bounded(db)
            if audit_denial and not is_owner(db, session.subject_id):
                _status_event(db, session.subject_id, None, action="console.access_denied", result="denied")
                db.commit()
            require_console_owner(db, session)
            yield db, session
            renewed = current_session(request, Role.ADMIN, platform_scope=True)
            if (renewed.id, renewed.subject_id, renewed.tenant_id) != (session.id, session.subject_id, session.tenant_id):
                raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
            require_console_owner(db, renewed)
    except TenantContextError:
        raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS) from None
    except SQLAlchemyError:
        raise HTTPException(503, "Console temporariamente indisponível.", headers=HEADERS) from None
    except HTTPException as exc:
        exc.headers = {**(exc.headers or {}), **HEADERS}
        raise


def revalidate_owner_before_commit(db, request, session):
    """Revalida o mesmo proprietário e reverte a escrita se a autorização mudou."""
    try:
        renewed = current_session(request, Role.ADMIN, platform_scope=True)
        if (renewed.id, renewed.subject_id, renewed.tenant_id) != (
            session.id, session.subject_id, session.tenant_id,
        ):
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        require_console_owner(db, renewed)
    except (HTTPException, TenantContextError, SQLAlchemyError):
        db.rollback()
        raise
    return renewed


def tenant_directory(db, *, query="", mode=None, limit=10, offset=0):
    if mode not in {None, "all", "alphabetical", "recent"} or not 1 <= limit <= 20 or not 0 <= offset <= 100_000:
        raise HTTPException(422, "Parâmetros de consulta inválidos.", headers=HEADERS)
    normalized = query.strip().lower()
    if mode is None and len(normalized) < 2:
        return {"items": [], "has_more": False}
    identities = select(
        TenantAdmin.tenant_id,
        func.count(AdminUser.id).label("count"),
        func.min(AdminUser.email).label("email"),
    ).join(AdminUser, AdminUser.id == TenantAdmin.admin_user_id).where(
        TenantAdmin.active.is_(True),
    ).group_by(TenantAdmin.tenant_id).subquery()
    statement = select(Tenant.id, Tenant.status, Tenant.lifecycle, Tenant.canonical_host, Tenant.canonical_host_status,
                       Tenant.photographer_name, identities.c.count, identities.c.email).outerjoin(
        identities, identities.c.tenant_id == Tenant.id,
    )
    if normalized:
        email_match = select(TenantAdmin.id).join(
            AdminUser, AdminUser.id == TenantAdmin.admin_user_id,
        ).where(TenantAdmin.tenant_id == Tenant.id, TenantAdmin.active.is_(True),
                func.lower(AdminUser.email).contains(normalized, autoescape=True)).exists()
        statement = statement.where(or_(func.lower(Tenant.photographer_name).contains(normalized, autoescape=True), email_match))
    if mode == "all":
        statement = statement.order_by(Tenant.id)
    elif mode == "alphabetical":
        # Identidade ambígua não fornece nem ordenação por e-mail oculto.
        from sqlalchemy import case
        email = case((identities.c.count == 1, func.lower(identities.c.email)), else_=None)
        statement = statement.order_by(func.coalesce(func.lower(Tenant.photographer_name), email).asc().nulls_last(), Tenant.id)
    else:
        statement = statement.order_by(Tenant.created_at.desc(), Tenant.id)
    rows = db.execute(statement.limit(limit + 1).offset(offset)).all()
    return {"items": [
        {"tenant_id": str(identity), "status": status, "lifecycle": lifecycle,
         "canonical_host": host, "canonical_host_status": host_status,
         "photographer_name": name, "admin_email": email if count == 1 else None}
        for identity, status, lifecycle, host, host_status, name, count, email in rows[:limit]
    ], "has_more": len(rows) > limit}


def tenant_summary(db, tenant_id):
    row = db.execute(select(Tenant.id, Tenant.status, Tenant.lifecycle, Tenant.canonical_host, Tenant.canonical_host_status,
                            Tenant.photographer_name).where(Tenant.id == tenant_id)).one_or_none()
    if row is None:
        raise HTTPException(404, "Conta não encontrada.", headers=HEADERS)
    counts = db.execute(select(
        select(func.count(ParentGallery.id)).where(ParentGallery.tenant_id == tenant_id).scalar_subquery(),
        select(func.count(PhotoAsset.id)).where(PhotoAsset.tenant_id == tenant_id).scalar_subquery(),
    )).one()
    return {"tenant_id": str(row.id), "status": row.status, "lifecycle": row.lifecycle,
            "canonical_host": row.canonical_host,
            "canonical_host_status": row.canonical_host_status, "photographer_name": row.photographer_name,
            "gallery_count": counts[0], "photo_count": counts[1],
            "source": "application_database", "scope": "tenant", "observed_at": now()}


@router.get("/capabilities")
def capabilities(request: Request, response: Response):
    response.headers.update(HEADERS)
    try:
        with authorized(request, audit_denial=False):
            return {"read_console": True}
    except HTTPException as exc:
        if exc.status_code != 403:
            raise
        return {"read_console": False}


@router.get("/tenants")
def tenants(request: Request, response: Response, q: str = Query("", max_length=320),
            mode: Literal["all", "alphabetical", "recent"] | None = None,
            limit: int = Query(10, ge=1, le=20), offset: int = Query(0, ge=0, le=100_000)):
    response.headers.update(HEADERS)
    with authorized(request) as (db, _session):
        return {**tenant_directory(db, query=q, mode=mode, limit=limit, offset=offset),
                "source": "application_database", "scope": "platform", "observed_at": now()}


@router.get("/tenants/{tenant_id}")
def detail(tenant_id: UUID, request: Request, response: Response):
    response.headers.update(HEADERS)
    with authorized(request) as (db, _session):
        return tenant_summary(db, tenant_id)


@router.get("/tenants/{tenant_id}/closure")
def tenant_closure_status(tenant_id: UUID, request: Request, response: Response):
    from app import tenant_closure_recovery

    response.headers.update(HEADERS)
    with authorized(request) as (db, _session):
        return tenant_closure_recovery.closure_console_payload(db, tenant_id)


@router.post("/tenants/{tenant_id}/closure/profile-reduction")
def reduce_tenant_profile(
    tenant_id: UUID, payload: TenantProfileReductionInput, request: Request, response: Response,
):
    from app.main import require_same_origin
    from app.tenant_profile_retention import profile_retention_payload, reduce_closed_profile

    require_same_origin(request)
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        prior = _prior_admin_action_event(
            db, request_id=payload.request_id, owner_id=session.subject_id,
            tenant_id=tenant_id, action="tenant.profile_reduced",
        )
        if prior is not None:
            return {**profile_retention_payload(db, tenant_id=tenant_id), "replayed": True}
        admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id)
                          .with_for_update().execution_options(populate_existing=True))
        if admin is None:
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        prior = _prior_admin_action_event(
            db, request_id=payload.request_id, owner_id=session.subject_id,
            tenant_id=tenant_id, action="tenant.profile_reduced",
        )
        if prior is not None:
            return {**profile_retention_payload(db, tenant_id=tenant_id), "replayed": True}
        enforce_rate_limit(db, "platform_tenant_profile_reduction", str(session.subject_id),
                           request.client.host if request.client else "unknown")
        try:
            step = reauthenticate_console_owner(admin, payload)
        except AdminAccountError:
            _status_event(db, session.subject_id, tenant_id, action="console.access_denied", result="denied")
            db.commit()
            raise HTTPException(403, "Não foi possível confirmar a operação.", headers=HEADERS) from None
        except TotpSecretError:
            db.rollback()
            raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
        try:
            closure_id = reduce_closed_profile(
                db, owner_id=session.subject_id, tenant_id=tenant_id,
                confirmation=payload.confirm_phrase, confirm_review=payload.confirm_review,
            )
        except HTTPException as exc:
            db.rollback()
            if exc.status_code == 409:
                _status_event(db, session.subject_id, tenant_id, action="console.access_denied", result="denied")
                db.commit()
            raise
        admin.totp_last_used_step = step
        db.add(PlatformAdminEvent(
            request_id=payload.request_id, actor_admin_id=session.subject_id,
            object_id=closure_id, tenant_id=tenant_id, action="tenant.profile_reduced",
            previous_status="retained", next_status="reduced", result="success", created_at=now(),
        ))
        revalidate_owner_before_commit(db, request, session)
        db.commit()
        return {**profile_retention_payload(db, tenant_id=tenant_id), "replayed": False}


@router.post("/tenants/{tenant_id}/closure/media-deletion", status_code=202)
def request_tenant_media_deletion(
    tenant_id: UUID,
    payload: TenantMediaDeletionInput,
    request: Request,
    response: Response,
):
    from app import tenant_media_deletion
    from app.main import require_same_origin

    require_same_origin(request)
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        prior = _prior_admin_action_event(
            db, request_id=payload.request_id, owner_id=session.subject_id,
            tenant_id=tenant_id, action="tenant.media_deletion_requested",
        )
        if prior is not None:
            return {**tenant_media_deletion.media_deletion_console_payload(db, tenant_id=tenant_id),
                    "replayed": True}

        admin = db.scalar(select(AdminUser).where(
            AdminUser.id == session.subject_id,
        ).with_for_update().execution_options(populate_existing=True))
        if admin is None:
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        prior = _prior_admin_action_event(
            db, request_id=payload.request_id, owner_id=session.subject_id,
            tenant_id=tenant_id, action="tenant.media_deletion_requested",
        )
        if prior is not None:
            return {**tenant_media_deletion.media_deletion_console_payload(db, tenant_id=tenant_id),
                    "replayed": True}
        enforce_rate_limit(
            db,
            "platform_tenant_media_deletion",
            str(session.subject_id),
            request.client.host if request.client else "unknown",
        )
        try:
            step = reauthenticate_console_owner(admin, payload)
        except AdminAccountError:
            _status_event(db, session.subject_id, tenant_id,
                          action="console.access_denied", result="denied")
            db.commit()
            raise HTTPException(403, "Não foi possível confirmar a operação.", headers=HEADERS) from None
        except TotpSecretError:
            db.rollback()
            raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None

        try:
            result = tenant_media_deletion.request_media_deletion(
                db,
                owner_id=session.subject_id,
                tenant_id=tenant_id,
                request_id=payload.request_id,
                confirmation=payload.confirm_phrase,
            )
        except HTTPException as exc:
            if exc.status_code == 409:
                db.rollback()
                _status_event(db, session.subject_id, tenant_id,
                              action="console.access_denied", result="denied")
                db.commit()
            raise
        admin.totp_last_used_step = step
        batch_id = UUID(result["batch"]["batch_id"])
        next_status = result["batch"]["state"]
        db.add(PlatformAdminEvent(
            request_id=payload.request_id,
            actor_admin_id=session.subject_id,
            object_id=batch_id,
            tenant_id=tenant_id,
            action="tenant.media_deletion_requested",
            previous_status="closed",
            next_status=next_status,
            result="success",
            created_at=now(),
        ))
        revalidate_owner_before_commit(db, request, session)
        db.commit()
        return result


@router.post("/tenants/{tenant_id}/closure/media-deletion/retry", status_code=202)
def retry_tenant_media_deletion(
    tenant_id: UUID,
    payload: TenantMediaDeletionInput,
    request: Request,
    response: Response,
):
    from app import tenant_media_deletion
    from app.main import require_same_origin

    require_same_origin(request)
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        prior = _prior_admin_action_event(
            db, request_id=payload.request_id, owner_id=session.subject_id,
            tenant_id=tenant_id, action="tenant.media_deletion_retry",
        )
        if prior is not None:
            return {**tenant_media_deletion.media_deletion_console_payload(db, tenant_id=tenant_id),
                    "replayed": True}

        admin = db.scalar(select(AdminUser).where(
            AdminUser.id == session.subject_id,
        ).with_for_update().execution_options(populate_existing=True))
        if admin is None:
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        prior = _prior_admin_action_event(
            db, request_id=payload.request_id, owner_id=session.subject_id,
            tenant_id=tenant_id, action="tenant.media_deletion_retry",
        )
        if prior is not None:
            return {**tenant_media_deletion.media_deletion_console_payload(db, tenant_id=tenant_id),
                    "replayed": True}
        enforce_rate_limit(
            db,
            "platform_tenant_media_deletion_retry",
            str(session.subject_id),
            request.client.host if request.client else "unknown",
        )
        try:
            step = reauthenticate_console_owner(admin, payload)
        except AdminAccountError:
            _status_event(db, session.subject_id, tenant_id,
                          action="console.access_denied", result="denied")
            db.commit()
            raise HTTPException(403, "Não foi possível confirmar a operação.", headers=HEADERS) from None
        except TotpSecretError:
            db.rollback()
            raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None

        try:
            previous_batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
                TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
            ).order_by(TenantClosureMediaDeletionBatch.requested_at.desc()).limit(1))
            previous_batch_state = previous_batch.state if previous_batch is not None else "unknown"
            result = tenant_media_deletion.retry_media_deletion(
                db,
                owner_id=session.subject_id,
                tenant_id=tenant_id,
                confirmation=payload.confirm_phrase,
            )
        except HTTPException as exc:
            if exc.status_code == 409:
                db.rollback()
                _status_event(db, session.subject_id, tenant_id,
                              action="console.access_denied", result="denied")
                db.commit()
            raise
        admin.totp_last_used_step = step
        batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
            TenantClosureMediaDeletionBatch.id == UUID(result["batch"]["batch_id"]),
            TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        ))
        if batch is None:
            raise HTTPException(409, "A exclusão não pode ser confirmada.", headers=HEADERS)
        db.add(PlatformAdminEvent(
            request_id=payload.request_id,
            actor_admin_id=session.subject_id,
            object_id=batch.id,
            tenant_id=tenant_id,
            action="tenant.media_deletion_retry",
            previous_status=previous_batch_state,
            next_status="queued",
            result="success",
            created_at=now(),
        ))
        revalidate_owner_before_commit(db, request, session)
        db.commit()
        return result


@router.post("/tenants/{tenant_id}/closure/recovery-batches", status_code=202)
def request_tenant_closure_recovery(
    tenant_id: UUID,
    payload: TenantClosureRecoveryBatchInput,
    request: Request,
    response: Response,
):
    from app import tenant_closure_recovery
    from app.main import require_same_origin

    require_same_origin(request)
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        previous = db.scalar(select(TenantClosureRecoveryBatch).where(
            TenantClosureRecoveryBatch.tenant_id == tenant_id,
            TenantClosureRecoveryBatch.request_id == payload.request_id,
        ))
        if previous is not None:
            result = tenant_closure_recovery.request_batch(
                db,
                owner_id=session.subject_id,
                tenant_id=tenant_id,
                request_id=payload.request_id,
                duration_days=payload.duration_days,
            )
            return {**result, "replayed": True}

        admin = db.scalar(select(AdminUser).where(
            AdminUser.id == session.subject_id,
        ).with_for_update().execution_options(populate_existing=True))
        if admin is None:
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        previous = db.scalar(select(TenantClosureRecoveryBatch).where(
            TenantClosureRecoveryBatch.tenant_id == tenant_id,
            TenantClosureRecoveryBatch.request_id == payload.request_id,
        ))
        if previous is not None:
            result = tenant_closure_recovery.request_batch(
                db,
                owner_id=session.subject_id,
                tenant_id=tenant_id,
                request_id=payload.request_id,
                duration_days=payload.duration_days,
            )
            return {**result, "replayed": True}
        enforce_rate_limit(
            db,
            "platform_closure_recovery",
            str(session.subject_id),
            request.client.host if request.client else "unknown",
        )
        try:
            step = reauthenticate_console_owner(admin, payload)
        except AdminAccountError:
            _status_event(db, session.subject_id, tenant_id,
                          action="console.access_denied", result="denied")
            db.commit()
            raise HTTPException(403, "Não foi possível confirmar a operação.", headers=HEADERS) from None
        except TotpSecretError:
            db.rollback()
            raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None

        result = tenant_closure_recovery.request_batch(
            db,
            owner_id=session.subject_id,
            tenant_id=tenant_id,
            request_id=payload.request_id,
            duration_days=payload.duration_days,
        )
        admin.totp_last_used_step = step
        revalidate_owner_before_commit(db, request, session)
        db.commit()
        return result


@router.get("/tenants/{tenant_id}/closure/recovery-batches/{batch_id}")
def tenant_closure_recovery_status(
    tenant_id: UUID,
    batch_id: UUID,
    request: Request,
    response: Response,
):
    from app import tenant_closure_recovery

    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        batch = tenant_closure_recovery.require_batch(
            db, session.subject_id, tenant_id, batch_id,
        )
        return tenant_closure_recovery.batch_payload(db, batch)


@router.post("/tenants/{tenant_id}/closure/reopen")
def reopen_tenant_account(
    tenant_id: UUID,
    payload: TenantClosureReopenInput,
    request: Request,
    response: Response,
):
    from app import tenant_closure_recovery
    from app.main import require_same_origin

    require_same_origin(request)
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        prior = _prior_admin_action_event(
            db, request_id=payload.request_id, owner_id=session.subject_id,
            tenant_id=tenant_id, action="tenant.reopened",
        )
        if prior is not None:
            result = tenant_closure_recovery.reopen_account(
                db, owner_id=session.subject_id, tenant_id=tenant_id,
                request_id=payload.request_id,
            )
            return result

        admin = db.scalar(select(AdminUser).where(
            AdminUser.id == session.subject_id,
        ).with_for_update().execution_options(populate_existing=True))
        if admin is None:
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        prior = _prior_admin_action_event(
            db, request_id=payload.request_id, owner_id=session.subject_id,
            tenant_id=tenant_id, action="tenant.reopened",
        )
        if prior is not None:
            return tenant_closure_recovery.reopen_account(
                db, owner_id=session.subject_id, tenant_id=tenant_id,
                request_id=payload.request_id,
            )
        enforce_rate_limit(
            db,
            "platform_tenant_reopen",
            str(session.subject_id),
            request.client.host if request.client else "unknown",
        )
        try:
            step = reauthenticate_console_owner(admin, payload)
        except AdminAccountError:
            _status_event(db, session.subject_id, tenant_id,
                          action="console.access_denied", result="denied")
            db.commit()
            raise HTTPException(403, "Não foi possível confirmar a operação.", headers=HEADERS) from None
        except TotpSecretError:
            db.rollback()
            raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None

        result = tenant_closure_recovery.reopen_account(
            db, owner_id=session.subject_id, tenant_id=tenant_id,
            request_id=payload.request_id,
        )
        admin.totp_last_used_step = step
        revalidate_owner_before_commit(db, request, session)
        db.commit()
        return result


def _global_backup_source(db, *, observed_at):
    source = "application_database.global_postgresql_backup_run"
    try:
        status = read_global_postgresql_backup_status(db=db)
    except SQLAlchemyError:
        db.rollback()
        return {
            "key": "backup",
            "state": "unavailable",
            "availability": "unavailable",
            "source": source,
            "scope": "platform_owner",
            "observed_at": observed_at,
            "latest_run_status": None,
            "latest_attempt_day": None,
            "last_validated_day": None,
            "last_validated_at": None,
            "snapshot_id": None,
            "dump_size_bytes": None,
            "duration_ms": None,
        }

    latest_status = status.get("status")
    if not isinstance(latest_status, str) or latest_status not in {
        "running",
        "validated",
        "failed",
        "unknown",
    }:
        latest_status = "unknown"
    receipt = status.get("last_validated")
    validated_day = None
    if (
        isinstance(receipt, dict)
        and receipt.get("status") == "validated"
        and receipt.get("verified") is True
        and isinstance(receipt.get("snapshot_id"), str)
        and re.fullmatch(r"[0-9a-f]{8,64}", receipt["snapshot_id"])
        and isinstance(receipt.get("dump_size_bytes"), int)
        and not isinstance(receipt.get("dump_size_bytes"), bool)
        and receipt["dump_size_bytes"] > 0
        and isinstance(receipt.get("duration_ms"), int)
        and not isinstance(receipt.get("duration_ms"), bool)
        and receipt["duration_ms"] >= 0
        and isinstance(receipt.get("finished_at"), str)
        and isinstance(receipt.get("scheduled_day"), str)
    ):
        try:
            validated_day = date.fromisoformat(receipt["scheduled_day"])
        except ValueError:
            validated_day = None

    state = "unknown"
    if validated_day is not None:
        if validated_day == observed_at.date():
            state = "current"
        elif validated_day < observed_at.date():
            state = "stale"

    return {
        "key": "backup",
        "state": state,
        "availability": state,
        "source": source,
        "scope": "platform_owner",
        "observed_at": observed_at,
        "latest_run_status": latest_status,
        "latest_attempt_day": status.get("scheduled_day"),
        "last_validated_day": validated_day.isoformat() if validated_day else None,
        "last_validated_at": receipt.get("finished_at") if validated_day else None,
        "snapshot_id": receipt.get("snapshot_id") if validated_day else None,
        "dump_size_bytes": receipt.get("dump_size_bytes") if validated_day else None,
        "duration_ms": receipt.get("duration_ms") if validated_day else None,
    }


@router.get("/sources")
def sources(request: Request, response: Response):
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        observed_at = now()
        connection = db.scalar(select(GoogleDriveConnection).where(
            GoogleDriveConnection.tenant_id == session.tenant_id,
        ).execution_options(populate_existing=True))
        drive = {
            "key": "drive",
            "state": connection.state if connection else "unknown",
            "availability": ("authorization_recorded" if connection and connection.state == "connected"
                             else connection.state if connection else "unknown"),
            "source": "application_database.google_drive_connection",
            "scope": "platform_owner",
            "observed_at": observed_at,
            "connection_updated_at": connection.updated_at if connection else None,
            "quota_limit": connection.quota_limit if connection and connection.state == "connected"
            and connection.quota_observed_at else None,
            "quota_usage": connection.quota_usage if connection and connection.state == "connected"
            and connection.quota_observed_at else None,
            "quota_observed_at": connection.quota_observed_at if connection
            and connection.state == "connected" else None,
        }
        backup = _global_backup_source(db, observed_at=observed_at)
        unknown = [{"key": key, "state": "unknown", "availability": "unknown", "source": None,
                    "scope": "platform", "observed_at": None, "reason": "source_not_integrated"}
                   for key in ("archive", "restore")]
        return {"items": [backup, drive, *unknown]}


class StatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    expected_status: Literal["active", "suspended"]
    status: Literal["active", "suspended"]
    current_password: SecretStr
    totp_code: SecretStr


class HostnameActivationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    expected_hostname: str = Field(min_length=1, max_length=253)
    expected_status: Literal["reserved"]
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirm_readiness: Literal[True]
    current_password: SecretStr
    totp_code: SecretStr


class MediaArchiveRecoveryPricingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    recovery_fee_credits: int | None = Field(ge=1, le=2_147_483_647)
    current_password: SecretStr
    totp_code: SecretStr


class MediaArchiveRecoveryRetryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration_days: Literal[7, 14, 30]
    idempotency_key: str = Field(min_length=1, max_length=200)
    current_password: SecretStr
    totp_code: SecretStr


def _status_event(db, actor_id, tenant_id, *, action, result, request_id=None,
                  previous_status=None, next_status=None, object_id=None, evidence_sha256=None):
    event = PlatformAdminEvent(actor_admin_id=actor_id, tenant_id=tenant_id,
                               action=action, result=result, request_id=request_id,
                               object_id=object_id or tenant_id,
                               previous_status=previous_status, next_status=next_status,
                               evidence_sha256=evidence_sha256)
    db.add(event)
    return event


def reauthenticate_console_owner(admin, payload):
    password = payload.current_password.get_secret_value()
    code = payload.totp_code.get_secret_value()
    if not 1 <= len(password) <= 128 or len(code) != 6 or not code.isascii() or not code.isdigit():
        raise AdminAccountError("Credencial inválida.")
    reauthenticate_admin(admin, password)
    step = matching_unused_totp_step(admin.totp_secret, code, admin.totp_last_used_step)
    if step is None:
        raise AdminAccountError("Credencial inválida.")
    return step


def change_tenant_status(db, session, tenant_id, payload, *, ip_address="unknown"):
    require_console_owner(db, session)
    # Serializa reautenticação e idempotência por proprietário antes do alvo.
    admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id).with_for_update())
    action = "tenant.suspend" if payload.status == "suspended" else "tenant.activate"
    previous = db.scalar(select(PlatformAdminEvent).where(PlatformAdminEvent.request_id == payload.request_id))
    if previous:
        if (previous.actor_admin_id, previous.tenant_id, previous.action, previous.previous_status) != (
                session.subject_id, tenant_id, action, payload.expected_status):
            raise HTTPException(409, "Identificador já utilizado em outra operação.", headers=HEADERS)
        return {"tenant_id": str(tenant_id), "status": payload.status, "replayed": True}
    target = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update()
                       .execution_options(populate_existing=True))
    if target is None:
        _status_event(db, session.subject_id, None, action="tenant.status_denied", result="denied", object_id=tenant_id)
        db.commit()
        raise HTTPException(404, "Conta não encontrada.", headers=HEADERS)
    if target.id == session.tenant_id:
        _status_event(db, session.subject_id, target.id, action="tenant.status_denied", result="denied")
        db.commit()
        raise HTTPException(409, "A conta proprietária não pode ser suspensa pelo console.", headers=HEADERS)
    if target.lifecycle == "closed":
        _status_event(db, session.subject_id, target.id, action="tenant.status_denied", result="denied")
        db.commit()
        raise HTTPException(409, "Use o fluxo próprio para reabrir uma conta encerrada.", headers=HEADERS)
    if target.status != payload.expected_status:
        _status_event(db, session.subject_id, target.id, action="tenant.status_denied", result="denied")
        db.commit()
        raise HTTPException(409, "O estado da conta mudou. Consulte novamente.", headers=HEADERS)
    enforce_rate_limit(db, "platform_status", str(session.subject_id), ip_address)
    try:
        step = reauthenticate_console_owner(admin, payload)
    except AdminAccountError:
        _status_event(db, session.subject_id, target.id, action="tenant.status_denied", result="denied")
        db.commit()
        raise HTTPException(403, "Não foi possível confirmar a operação.", headers=HEADERS) from None
    except TotpSecretError:
        db.rollback()
        raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
    require_console_owner(db, session)
    previous_status = target.status
    target.status = payload.status
    admin.totp_last_used_step = step
    _status_event(db, session.subject_id, target.id, action=action, result="success", request_id=payload.request_id,
                  previous_status=previous_status, next_status=target.status)
    db.flush()
    return {"tenant_id": str(target.id), "status": target.status, "replayed": False}


def _hostname_activation_denied(db, session, tenant_id, *, object_id=None):
    _status_event(db, session.subject_id, tenant_id, action="tenant.host_activation_denied",
                  result="denied", object_id=object_id or tenant_id)


def activate_tenant_hostname(db, session, tenant_id, payload, *, ip_address="unknown"):
    require_console_owner(db, session)
    admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id).with_for_update()
                      .execution_options(populate_existing=True))
    target = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update()
                       .execution_options(populate_existing=True))
    if target is None:
        _hostname_activation_denied(db, session, None, object_id=tenant_id)
        db.commit()
        raise HTTPException(404, "Conta não encontrada.", headers=HEADERS)
    if target.id == session.tenant_id:
        _hostname_activation_denied(db, session, target.id)
        db.commit()
        raise HTTPException(409, "O endereço da conta proprietária não pode ser liberado por esta ação.", headers=HEADERS)
    previous = db.scalar(select(PlatformAdminEvent).where(PlatformAdminEvent.request_id == payload.request_id))
    try:
        expected_hostname = normalize_canonical_host(payload.expected_hostname)
        one_label_host = (expected_hostname == payload.expected_hostname
                          and expected_hostname.endswith(".pickyourpic.com.br")
                          and len(expected_hostname.split(".")) == 4)
    except CanonicalHostError:
        one_label_host = False
        expected_hostname = ""
    if previous:
        matches = (
            previous.actor_admin_id == session.subject_id
            and previous.tenant_id == target.id
            and previous.object_id == target.id
            and previous.action == "tenant.host_ready"
            and previous.result == "success"
            and previous.previous_status == payload.expected_status
            and previous.next_status == "ready"
            and previous.evidence_sha256 == payload.evidence_sha256
            and one_label_host
            and target.canonical_host == expected_hostname
        )
        if matches:
            return {"tenant_id": str(target.id), "canonical_host": expected_hostname,
                    "canonical_host_status": "ready", "replayed": True}
        _hostname_activation_denied(db, session, target.id)
        db.commit()
        raise HTTPException(409, "Identificador já utilizado ou intenção divergente.", headers=HEADERS)
    if (not one_label_host or target.status != "active" or target.canonical_host != expected_hostname
            or target.canonical_host_status != payload.expected_status):
        _hostname_activation_denied(db, session, target.id)
        db.commit()
        raise HTTPException(409, "O hostname ou estado mudou. Consulte a conta novamente.", headers=HEADERS)
    enforce_rate_limit(db, "platform_hostname_ready", str(session.subject_id), ip_address)
    try:
        step = reauthenticate_console_owner(admin, payload)
    except AdminAccountError:
        _hostname_activation_denied(db, session, target.id)
        db.commit()
        raise HTTPException(403, "Não foi possível confirmar a operação.", headers=HEADERS) from None
    except TotpSecretError:
        db.rollback()
        raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
    require_console_owner(db, session)
    target.canonical_host_status = "ready"
    admin.totp_last_used_step = step
    _status_event(db, session.subject_id, target.id, action="tenant.host_ready", result="success",
                  request_id=payload.request_id, previous_status="reserved", next_status="ready",
                  evidence_sha256=payload.evidence_sha256)
    db.flush()
    return {"tenant_id": str(target.id), "canonical_host": target.canonical_host,
            "canonical_host_status": target.canonical_host_status, "replayed": False}


@router.post("/tenants/{tenant_id}/status")
def status(tenant_id: UUID, payload: StatusInput, request: Request, response: Response):
    from app.main import require_same_origin
    require_same_origin(request)
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        result = change_tenant_status(db, session, tenant_id, payload,
                                     ip_address=request.client.host if request.client else "unknown")
        revalidate_owner_before_commit(db, request, session)
        db.commit()
        return result


@router.post("/tenants/{tenant_id}/hostname/activate")
def activate_hostname(tenant_id: UUID, payload: HostnameActivationInput, request: Request, response: Response):
    from app.main import require_same_origin
    require_same_origin(request)
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        result = activate_tenant_hostname(db, session, tenant_id, payload,
                                          ip_address=request.client.host if request.client else "unknown")
        revalidate_owner_before_commit(db, request, session)
        db.commit()
        return result


@router.get("/media-archive/recovery-pricing")
def media_archive_recovery_pricing(request: Request, response: Response):
    from app import media_archive_billing

    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        return media_archive_billing.owner_recovery_pricing(db, session.subject_id)


@router.put("/media-archive/recovery-pricing")
def update_media_archive_recovery_pricing(
    payload: MediaArchiveRecoveryPricingInput, request: Request, response: Response,
):
    from app import media_archive_billing
    from app.main import require_same_origin

    require_same_origin(request)
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        previous = db.scalar(select(PlatformAdminEvent).where(
            PlatformAdminEvent.request_id == payload.request_id,
        ).with_for_update())
        if previous is not None:
            result = media_archive_billing.update_recovery_pricing(
                db, session.subject_id, payload.recovery_fee_credits,
                request_id=payload.request_id,
            )
            return {**result, "replayed": True}

        admin = db.scalar(select(AdminUser).where(
            AdminUser.id == session.subject_id,
        ).with_for_update().execution_options(populate_existing=True))
        if admin is None:
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        enforce_rate_limit(
            db,
            "platform_archive_recovery_pricing",
            str(session.subject_id),
            request.client.host if request.client else "unknown",
        )
        try:
            step = reauthenticate_console_owner(admin, payload)
        except AdminAccountError:
            _status_event(db, session.subject_id, None, action="console.access_denied", result="denied")
            db.commit()
            raise HTTPException(403, "Não foi possível confirmar a operação.", headers=HEADERS) from None
        except TotpSecretError:
            db.rollback()
            raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
        result = media_archive_billing.update_recovery_pricing(
            db, session.subject_id, payload.recovery_fee_credits,
            request_id=payload.request_id,
        )
        admin.totp_last_used_step = step
        revalidate_owner_before_commit(db, request, session)
        db.commit()
        return {**result, "replayed": False}


@router.post("/credit-tenants/{tenant_id}/media-archive/recoveries/{operation_id}/retry", status_code=202)
def retry_media_archive_recovery(
    tenant_id: UUID,
    operation_id: UUID,
    payload: MediaArchiveRecoveryRetryInput,
    request: Request,
    response: Response,
):
    from app import media_archive_billing
    from app.auth import MediaArchiveOperation
    from app.main import require_same_origin

    require_same_origin(request)
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        cycle_id = media_archive_billing.failed_recovery_cycle_id(
            db, owner_admin_id=session.subject_id, tenant_id=tenant_id,
            failed_operation_id=operation_id,
        )
        previous = db.scalar(select(MediaArchiveOperation).where(
            MediaArchiveOperation.tenant_id == tenant_id,
            MediaArchiveOperation.idempotency_key == payload.idempotency_key,
        ))
        if previous is not None:
            result = media_archive_billing.request_recovery(
                db, tenant_id=tenant_id, actor_admin_id=session.subject_id,
                cycle_id=cycle_id, duration_days=payload.duration_days,
                idempotency_key=payload.idempotency_key,
                retry_of_operation_id=operation_id,
            )
            return {**result, "replayed": True}

        admin = db.scalar(select(AdminUser).where(
            AdminUser.id == session.subject_id,
        ).with_for_update().execution_options(populate_existing=True))
        if admin is None:
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        enforce_rate_limit(
            db,
            "platform_archive_recovery_retry",
            str(session.subject_id),
            request.client.host if request.client else "unknown",
        )
        try:
            step = reauthenticate_console_owner(admin, payload)
        except AdminAccountError:
            _status_event(db, session.subject_id, tenant_id, action="console.access_denied", result="denied")
            db.commit()
            raise HTTPException(403, "Não foi possível confirmar a operação.", headers=HEADERS) from None
        except TotpSecretError:
            db.rollback()
            raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
        result = media_archive_billing.request_recovery(
            db, tenant_id=tenant_id, actor_admin_id=session.subject_id,
            cycle_id=cycle_id, duration_days=payload.duration_days,
            idempotency_key=payload.idempotency_key,
            retry_of_operation_id=operation_id,
        )
        admin.totp_last_used_step = step
        revalidate_owner_before_commit(db, request, session)
        db.commit()
        return {**result, "replayed": False}


@router.get("/audit")
def audit_events(request: Request, response: Response, tenant_id: UUID | None = None,
                 limit: int = Query(20, ge=1, le=20), offset: int = Query(0, ge=0, le=100_000)):
    response.headers.update(HEADERS)
    with authorized(request) as (db, _session):
        statement = select(PlatformAdminEvent).order_by(PlatformAdminEvent.created_at.desc(), PlatformAdminEvent.id.desc())
        if tenant_id is not None:
            statement = statement.where(PlatformAdminEvent.tenant_id == tenant_id)
        events = db.scalars(statement.offset(offset).limit(limit + 1)).all()
        return {"items": [{"id": str(item.id), "actor_admin_id": str(item.actor_admin_id),
                           "tenant_id": str(item.tenant_id) if item.tenant_id else None,
                           "object_id": str(item.object_id) if item.object_id else None,
                           "action": item.action, "result": item.result, "origin": item.origin,
                           "previous_status": item.previous_status, "next_status": item.next_status,
                           "created_at": item.created_at,
                           **({"reason_code": item.reason_code} if item.reason_code else {}),
                           **({"evidence_sha256": item.evidence_sha256} if item.evidence_sha256 else {})} for item in events[:limit]],
                "has_more": len(events) > limit}
