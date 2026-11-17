"""Orquestração administrativa sobre a fila existente de arquivo por pasta."""

import calendar
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    MediaArchiveCycle,
    MediaArchiveOperation,
    MediaArchiveRecoveryRequest,
    PlatformAdminEvent,
    Tenant,
    TenantClosureMediaDeletionBatch,
    TenantClosureRecoveryBatch,
    TenantClosureRecoveryItem,
    TenantClosureRequest,
    audit,
    now,
)
from app.system_monitor.access import is_owner


def _owner(db: Session, owner_id: UUID) -> None:
    if not is_owner(db, owner_id):
        raise HTTPException(403, "Acesso não autorizado.")


def bind_account_recovery(db: Session, owner_id: UUID, tenant_id: UUID) -> None:
    _owner(db, owner_id)
    tenant = db.get(Tenant, tenant_id, populate_existing=True)
    if not tenant or tenant.lifecycle != "closed":
        raise HTTPException(409, "A conta não está disponível para recuperação.")
    db.info.setdefault("tenant_archive_recovery", set()).add(tenant_id)


def _execution_proven(db: Session, operation_id: UUID, tenant_id: UUID, lease_token: str) -> bool:
    row = db.execute(select(MediaArchiveOperation.actor_admin_id).join(
        TenantClosureRecoveryItem,
        (TenantClosureRecoveryItem.operation_id == MediaArchiveOperation.id)
        & (TenantClosureRecoveryItem.tenant_id == MediaArchiveOperation.tenant_id),
    ).join(TenantClosureRecoveryBatch,
           (TenantClosureRecoveryBatch.id == TenantClosureRecoveryItem.batch_id)
           & (TenantClosureRecoveryBatch.tenant_id == TenantClosureRecoveryItem.tenant_id)).join(
        TenantClosureRequest,
        (TenantClosureRequest.id == TenantClosureRecoveryBatch.closure_request_id)
        & (TenantClosureRequest.tenant_id == TenantClosureRecoveryBatch.tenant_id),
    ).where(
        MediaArchiveOperation.id == operation_id, MediaArchiveOperation.tenant_id == tenant_id,
        MediaArchiveOperation.operation_type == "restore", MediaArchiveOperation.status == "processing",
        MediaArchiveOperation.lease_token == lease_token,
        MediaArchiveOperation.lease_expires_at > now(), MediaArchiveOperation.actor_type == "owner",
        TenantClosureRequest.state == "closed",
        TenantClosureRecoveryBatch.requested_by_owner_admin_id == MediaArchiveOperation.actor_admin_id,
    )).first()
    return row is not None and is_owner(db, row.actor_admin_id)


def archive_execution_authorized(db: Session, tenant_id: UUID) -> bool:
    scope = db.info.get("closure_archive_execution")
    return bool(scope and scope[0] == tenant_id and _execution_proven(db, scope[1], tenant_id, scope[2]))


def bind_operation_recovery(db: Session, operation: MediaArchiveOperation, lease_token: str) -> None:
    request = db.scalar(select(MediaArchiveRecoveryRequest).where(
        MediaArchiveRecoveryRequest.operation_id == operation.id,
        MediaArchiveRecoveryRequest.tenant_id == operation.tenant_id))
    if request is None or request.closure_batch_id is None:
        return
    if not _execution_proven(db, operation.id, operation.tenant_id, lease_token):
        raise HTTPException(403, "Operação de recuperação não autorizada.")
    db.info.setdefault("tenant_archive_recovery", set()).add(operation.tenant_id)
    db.info["closure_archive_execution"] = (operation.tenant_id, operation.id, lease_token)


def batch_payload(db: Session, batch: TenantClosureRecoveryBatch) -> dict:
    rows = db.execute(select(MediaArchiveOperation.id, MediaArchiveOperation.cycle_id,
                             MediaArchiveOperation.status, MediaArchiveOperation.last_error_code)
                      .join(TenantClosureRecoveryItem,
                            (TenantClosureRecoveryItem.operation_id == MediaArchiveOperation.id)
                            & (TenantClosureRecoveryItem.tenant_id == MediaArchiveOperation.tenant_id))
                      .where(TenantClosureRecoveryItem.batch_id == batch.id,
                             TenantClosureRecoveryItem.tenant_id == batch.tenant_id)
                      .order_by(MediaArchiveOperation.id)).all()
    states = {row.status for row in rows}
    state = ("completed" if not states or states == {"completed"}
             else "attention_required" if states & {"failed", "cancelled", "reconciliation_required"}
             else "processing")
    return {"batch_id": str(batch.id), "tenant_id": str(batch.tenant_id), "state": state,
            "duration_days": batch.duration_days, "created_at": batch.created_at.isoformat(),
            "operations": [{"operation_id": str(row.id), "cycle_id": str(row.cycle_id),
                            "status": row.status, "error_code": row.last_error_code} for row in rows]}


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def closure_console_payload(db: Session, tenant_id: UUID) -> dict:
    """Status resumido para o console; nunca devolve dados cadastrais sensíveis."""
    tenant = db.get(Tenant, tenant_id, populate_existing=True)
    if tenant is None:
        raise HTTPException(404, "Conta não encontrada.")

    observed_at = _as_utc(now())
    latest = db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant_id,
    ).order_by(TenantClosureRequest.requested_at.desc(), TenantClosureRequest.id.desc()).limit(1))

    # Uma linha antiga em `closed` pode existir em estado legado. Só o último
    # ciclo pode sustentar idade, revisão ou recuperação da conta atual.
    current_closure = latest if tenant.lifecycle == "closed" and latest and latest.state == "closed" else None
    history_state = "available" if current_closure else (
        "unavailable" if tenant.lifecycle == "closed" else "not_applicable"
    )
    closed_at = _as_utc(current_closure.closed_at) if current_closure and current_closure.closed_at else None
    review_at = _ten_year_anniversary(closed_at) if closed_at else None
    days_closed = max(0, int((observed_at - closed_at).total_seconds() // 86_400)) if closed_at else None
    review_due = observed_at >= review_at if review_at else None
    from app.tenant_media_deletion import media_deletion_console_payload
    from app.tenant_profile_retention import profile_retention_payload

    media_deletion = media_deletion_console_payload(db, tenant_id=tenant_id)

    batches: list[dict] = []
    reopen_blocker: str | None = "not_closed"
    if tenant.lifecycle == "closed":
        if current_closure is None:
            reopen_blocker = "closure_history_unavailable"
        else:
            rows = db.scalars(select(TenantClosureRecoveryBatch).where(
                TenantClosureRecoveryBatch.tenant_id == tenant_id,
                TenantClosureRecoveryBatch.closure_request_id == current_closure.id,
            ).order_by(TenantClosureRecoveryBatch.created_at.desc(), TenantClosureRecoveryBatch.id.desc()).limit(20))
            for batch in rows:
                result = batch_payload(db, batch)
                batches.append({
                    "batch_id": result["batch_id"],
                    "state": result["state"],
                    "duration_days": result["duration_days"],
                    "created_at": result["created_at"],
                    "operations": [{"status": item["status"]} for item in result["operations"]],
                })

            deletion_batch = media_deletion.get("batch")
            if deletion_batch is not None and deletion_batch.get("state") == "completed":
                reopen_blocker = "media_permanently_deleted"
            elif deletion_batch is not None:
                reopen_blocker = "media_deletion_pending"
            elif not _complete_recovery_set(db, tenant_id, current_closure.id):
                reopen_blocker = "restoration_pending"
            elif review_due:
                from app.photographer_access_recovery import completed_closure_proof
                verified_identity = completed_closure_proof(db, tenant_id, current_closure.id)
                reopen_blocker = None if verified_identity else "identity_confirmation_required"
            else:
                reopen_blocker = None

    previous_cycle = None
    if tenant.lifecycle != "closed" and latest and latest.state == "reopened":
        previous_cycle = {
            "closed_at": _as_utc(latest.closed_at).isoformat() if latest.closed_at else None,
            "reopened_at": _as_utc(latest.reopened_at).isoformat() if latest.reopened_at else None,
        }

    return {
        "tenant_id": str(tenant_id),
        "lifecycle": tenant.lifecycle,
        "availability": tenant.status,
        "history_state": history_state,
        "closed_at": closed_at.isoformat() if closed_at else None,
        "days_closed": days_closed,
        "review_at": review_at.isoformat() if review_at else None,
        "review_due": review_due,
        "reopen_blocker": reopen_blocker,
        "previous_cycle": previous_cycle,
        "batches": batches,
        "media_deletion": media_deletion,
        "profile_retention": profile_retention_payload(db, tenant_id=tenant_id),
        "observed_at": observed_at.isoformat(),
    }


def require_batch(db: Session, owner_id: UUID, tenant_id: UUID, batch_id: UUID):
    _owner(db, owner_id)
    batch = db.scalar(select(TenantClosureRecoveryBatch).where(
        TenantClosureRecoveryBatch.id == batch_id, TenantClosureRecoveryBatch.tenant_id == tenant_id))
    if batch is None:
        raise HTTPException(404, "Recuperação não encontrada.")
    return batch


def request_batch(db: Session, *, owner_id: UUID, tenant_id: UUID, request_id: UUID,
                  duration_days: int) -> dict:
    from app.media_archive_billing import request_recovery

    _owner(db, owner_id)
    if type(duration_days) is not int or duration_days not in {7, 14, 30}:
        raise HTTPException(422, "Escolha um prazo de 7, 14 ou 30 dias.")
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update()
                       .execution_options(populate_existing=True))
    bind_account_recovery(db, owner_id, tenant_id)
    previous = db.scalar(select(TenantClosureRecoveryBatch).where(
        TenantClosureRecoveryBatch.tenant_id == tenant_id, TenantClosureRecoveryBatch.request_id == request_id))
    if previous:
        if previous.requested_by_owner_admin_id != owner_id or previous.duration_days != duration_days:
            raise HTTPException(409, "A solicitação já existe com outros dados.")
        return {**batch_payload(db, previous), "replayed": True}
    closure = db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant.id, TenantClosureRequest.state == "closed",
    ).order_by(TenantClosureRequest.closed_at.desc()).limit(1))
    if closure is None:
        raise HTTPException(409, "Histórico de encerramento indisponível.")
    if db.scalar(select(TenantClosureMediaDeletionBatch.id).where(
        TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        TenantClosureMediaDeletionBatch.closure_request_id == closure.id,
    ).limit(1)) is not None:
        raise HTTPException(409, "A exclusão permanente de mídia impede nova recuperação.")
    if db.scalar(select(MediaArchiveOperation.id).where(
        MediaArchiveOperation.tenant_id == tenant_id,
        MediaArchiveOperation.status.in_(("queued", "processing", "reconciliation_required")),
    ).limit(1)) is not None:
        raise HTTPException(409, "Há uma operação de mídia pendente de conclusão ou revisão.")
    all_cycles = list(db.scalars(select(MediaArchiveCycle).where(
        MediaArchiveCycle.tenant_id == tenant_id,
    ).order_by(MediaArchiveCycle.cycle_number.desc())))
    if any(cycle.state in {"deleting", "deleted"} for cycle in all_cycles):
        raise HTTPException(409, "A mídia está em exclusão permanente ou já foi excluída.")
    latest = {}
    for cycle in all_cycles:
        latest.setdefault(cycle.folder_id, cycle)
    if any(cycle.state not in {"archived", "local"} for cycle in latest.values()):
        raise HTTPException(409, "Há mídia que precisa de revisão antes da recuperação.")
    batch = TenantClosureRecoveryBatch(id=uuid4(), tenant_id=tenant_id, closure_request_id=closure.id,
                                       requested_by_owner_admin_id=owner_id, request_id=request_id,
                                       duration_days=duration_days)
    db.add(batch)
    db.flush()
    for cycle in sorted(latest.values(), key=lambda item: str(item.id)):
        if cycle.state != "archived":
            continue
        result = request_recovery(db, tenant_id=tenant_id, actor_admin_id=owner_id,
                                  cycle_id=cycle.id, duration_days=duration_days,
                                  idempotency_key=f"closure:{batch.id}:{cycle.id}", closure_batch_id=batch.id)
        db.add(TenantClosureRecoveryItem(tenant_id=tenant_id, batch_id=batch.id, cycle_id=cycle.id,
                                         operation_id=UUID(result["operation_id"])))
    audit(db, "tenant.closure_recovery_requested", str(batch.id), tenant_id=tenant_id)
    db.flush()
    return {**batch_payload(db, batch), "replayed": False}


def _ten_year_anniversary(value: datetime) -> datetime:
    """Retorna o mesmo instante local no aniversário de dez anos; 29/02 limita a 28/02."""
    instant = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    year = instant.year + 10
    day = min(instant.day, calendar.monthrange(year, instant.month)[1])
    return instant.replace(year=year, day=day)


def _complete_recovery_set(db: Session, tenant_id: UUID, closure_id: UUID) -> bool:
    if db.scalar(select(MediaArchiveOperation.id).where(
        MediaArchiveOperation.tenant_id == tenant_id,
        MediaArchiveOperation.status.in_(("queued", "processing", "reconciliation_required")),
    ).limit(1)) is not None:
        return False

    all_cycles = list(db.scalars(select(MediaArchiveCycle).where(
        MediaArchiveCycle.tenant_id == tenant_id,
    ).order_by(MediaArchiveCycle.cycle_number.desc())))
    if any(cycle.state in {"deleting", "deleted"} for cycle in all_cycles):
        return False

    latest_cycles = {}
    for cycle in all_cycles:
        latest_cycles.setdefault(cycle.folder_id, cycle)

    for cycle in latest_cycles.values():
        if cycle.state != "local":
            return False
        if cycle.archived_at is None:
            continue
        verified_restore = db.scalar(select(MediaArchiveOperation.id).join(
            TenantClosureRecoveryItem,
            (TenantClosureRecoveryItem.operation_id == MediaArchiveOperation.id)
            & (TenantClosureRecoveryItem.tenant_id == MediaArchiveOperation.tenant_id),
        ).join(
            TenantClosureRecoveryBatch,
            (TenantClosureRecoveryBatch.id == TenantClosureRecoveryItem.batch_id)
            & (TenantClosureRecoveryBatch.tenant_id == TenantClosureRecoveryItem.tenant_id),
        ).where(
            TenantClosureRecoveryItem.tenant_id == tenant_id,
            TenantClosureRecoveryItem.cycle_id == cycle.id,
            TenantClosureRecoveryBatch.closure_request_id == closure_id,
            MediaArchiveOperation.operation_type == "restore",
            MediaArchiveOperation.status == "completed",
        ).limit(1))
        if verified_restore is None:
            return False
    return True


def reopen_account(
    db: Session,
    *,
    owner_id: UUID,
    tenant_id: UUID,
    request_id: UUID,
) -> dict:
    """Reabre explicitamente somente após o conjunto de mídia ser verificado."""
    _owner(db, owner_id)
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update()
                       .execution_options(populate_existing=True))
    if tenant is None:
        raise HTTPException(404, "Conta não encontrada.")

    prior = db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == request_id,
    ))
    if prior is not None:
        if (prior.action != "tenant.reopened" or prior.result != "success"
                or prior.actor_admin_id != owner_id or prior.tenant_id != tenant_id):
            raise HTTPException(409, "Identificador já utilizado em outra operação.")
        return {"tenant_id": str(tenant_id), "lifecycle": "open", "replayed": True,
                "reopened_at": prior.created_at.isoformat()}

    closure = db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant_id,
        TenantClosureRequest.state == "closed",
    ).order_by(TenantClosureRequest.closed_at.desc()).with_for_update().limit(1))
    if tenant.lifecycle != "closed" or closure is None or closure.closed_at is None:
        raise HTTPException(409, "A conta não está encerrada para reabertura.")
    if now() >= _ten_year_anniversary(closure.closed_at):
        from app.photographer_access_recovery import completed_closure_proof
        verified_identity = completed_closure_proof(db, tenant_id, closure.id)
        if not verified_identity:
            raise HTTPException(409, "A confirmação de identidade e dos dados atuais é necessária.")
    if not _complete_recovery_set(db, tenant_id, closure.id):
        raise HTTPException(409, "A recuperação completa da mídia ainda não foi verificada.")

    instant = now()
    tenant.lifecycle = "open"
    closure.state = "reopened"
    closure.reopened_at = instant
    db.add(PlatformAdminEvent(
        request_id=request_id,
        actor_admin_id=owner_id,
        object_id=closure.id,
        tenant_id=tenant_id,
        action="tenant.reopened",
        previous_status="closed",
        next_status="open",
        result="success",
        created_at=instant,
    ))
    audit(db, "tenant.reopened", str(request_id), tenant_id=tenant_id)
    db.flush()
    return {"tenant_id": str(tenant_id), "lifecycle": tenant.lifecycle,
            "availability": tenant.status, "reopened_at": instant.isoformat(), "replayed": False}
