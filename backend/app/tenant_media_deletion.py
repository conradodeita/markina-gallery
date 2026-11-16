"""Exclusão permanente, explícita e retomável da mídia fria de um tenant."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveObject,
    MediaArchiveOperation,
    Tenant,
    TenantClosureMediaDeletionBatch,
    TenantClosureMediaDeletionItem,
    TenantClosureRequest,
    audit,
    now,
)
from app.media_archive_manifest import MediaArchiveManifestError, validate_stored_archive_manifest
from app.system_monitor.access import is_owner

DELETION_CONFIRMATION = "EXCLUIR MÍDIA PERMANENTEMENTE"
_REMOTE_ID = re.compile(r"^[A-Za-z0-9_-]{1,256}$")
_PENDING_OPERATION_STATES = ("queued", "processing", "reconciliation_required")
_RETRYABLE_OPERATION_STATES = ("failed", "reconciliation_required")


@dataclass(frozen=True)
class MediaDeletionPlan:
    closure: TenantClosureRequest | None
    cycles: tuple[MediaArchiveCycle, ...]
    objects_by_cycle: dict[UUID, tuple[MediaArchiveObject, ...]]
    inventory_sha256: str
    object_count: int
    total_bytes: int
    blocker: str | None


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)  # noqa: UP017 -- Compatibilidade com Python 3.10.
    return value.astimezone(timezone.utc)  # noqa: UP017 -- Compatibilidade com Python 3.10.


def _latest_closure(db: Session, tenant_id: UUID) -> TenantClosureRequest | None:
    return db.scalar(
        select(TenantClosureRequest)
        .where(TenantClosureRequest.tenant_id == tenant_id)
        .order_by(TenantClosureRequest.requested_at.desc(), TenantClosureRequest.id.desc())
        .limit(1)
    )


def validate_cycle_catalog_for_deletion(
    cycle: MediaArchiveCycle,
    rows: tuple[MediaArchiveObject, ...],
) -> str | None:
    # O preflight só chama para ciclos arquivados; o executor revalida após
    # a reserva mudar o ciclo para deleting.
    if cycle.state not in {"archived", "deleting"} or cycle.archived_at is None:
        return "cycle_not_archived"
    manifests = [row for row in rows if row.object_type == "manifest"]
    media = [row for row in rows if row.object_type != "manifest"]
    if len(manifests) != 1 or len(media) != cycle.object_count:
        return "catalog_incomplete"
    manifest_row = manifests[0]
    try:
        manifest, encoded = validate_stored_archive_manifest(cycle)
    except (MediaArchiveManifestError, TypeError, ValueError):
        return "manifest_invalid"
    if (
        manifest_row.mime_type != "application/json"
        or manifest_row.size_bytes != len(encoded)
        or manifest_row.sha256 != sha256(encoded).hexdigest()
        or not manifest_row.remote_object_id
        or not _REMOTE_ID.fullmatch(manifest_row.remote_object_id)
        or manifest_row.remote_deleted_at is not None
    ):
        return "manifest_catalog_mismatch"

    by_id = {str(row.id): row for row in media}
    if len(by_id) != len(media):
        return "catalog_incomplete"
    for item in manifest["objects"]:
        row = by_id.get(item["object_id"])
        if row is None or (
            row.source_ref != item["source_ref"]
            or row.object_type != item["object_type"]
            or row.mime_type != item["mime_type"]
            or row.size_bytes != item["size_bytes"]
            or row.sha256 != item["sha256"]
            or row.remote_object_id != item["remote_object_id"]
        ):
            return "manifest_catalog_mismatch"
    if len(manifest["objects"]) != len(media):
        return "manifest_catalog_mismatch"
    for row in rows:
        if (
            not row.remote_object_id
            or not _REMOTE_ID.fullmatch(row.remote_object_id)
            or row.remote_deleted_at is not None
        ):
            return "remote_identity_unavailable"
    return None


def evaluate_media_deletion_preflight(
    db: Session,
    *,
    tenant_id: UUID,
    at: datetime | None = None,
) -> MediaDeletionPlan:
    """Calcula elegibilidade e inventário sem criar jobs ou tocar no storage."""
    from app.tenant_closure_recovery import _ten_year_anniversary

    observed_at = _utc(at or now())
    tenant = db.get(Tenant, tenant_id, populate_existing=True)
    closure = _latest_closure(db, tenant_id)
    cycles = tuple(db.scalars(
        select(MediaArchiveCycle)
        .where(MediaArchiveCycle.tenant_id == tenant_id)
        .order_by(MediaArchiveCycle.cycle_number, MediaArchiveCycle.folder_id, MediaArchiveCycle.id)
    ))
    objects_by_cycle: dict[UUID, tuple[MediaArchiveObject, ...]] = {}
    inventory: list[dict[str, object]] = []
    total_bytes = 0
    object_count = 0
    blocker: str | None = None

    if tenant is None:
        blocker = "tenant_unavailable"
    elif tenant.lifecycle != "closed":
        blocker = "account_not_closed"
    elif closure is None or closure.state != "closed" or closure.closed_at is None:
        blocker = "closure_history_unavailable"
    elif observed_at < _ten_year_anniversary(_utc(closure.closed_at)):
        blocker = "review_not_due"
    elif db.scalar(select(MediaArchiveOperation.id).where(
        MediaArchiveOperation.tenant_id == tenant_id,
        MediaArchiveOperation.status.in_(_PENDING_OPERATION_STATES),
    ).limit(1)) is not None:
        blocker = "media_operation_pending"
    elif db.scalar(select(TenantClosureMediaDeletionBatch.id).where(
        TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        TenantClosureMediaDeletionBatch.closure_request_id == closure.id,
    ).limit(1)) is not None:
        blocker = "deletion_already_requested"

    # Um conjunto vazio de ciclos não prova que não havia mídia. Pode indicar
    # fechamento legado, inventário incompleto ou ciclo ausente; nesses casos
    # não se cria um recibo vazio nem se remove a impressão protegida do CPF.
    if blocker is None and not cycles:
        blocker = "archive_proof_unavailable"

    remote_ids: set[str] = set()
    if blocker is None:
        for cycle in cycles:
            if cycle.state != "archived":
                blocker = "cycle_not_archived"
                break
            archive_operation = db.scalar(
                select(MediaArchiveOperation)
                .where(
                    MediaArchiveOperation.tenant_id == tenant_id,
                    MediaArchiveOperation.cycle_id == cycle.id,
                    MediaArchiveOperation.operation_type == "archive",
                )
                .order_by(MediaArchiveOperation.created_at.desc(), MediaArchiveOperation.id.desc())
                .limit(1)
            )
            details = archive_operation.details if archive_operation else {}
            if (
                archive_operation is None
                or archive_operation.status != "completed"
                or not isinstance(details, dict)
                or details.get("readback_verified") is not True
                or details.get("manifest_readback_verified") is not True
                or details.get("local_cleanup_complete") is not True
                or details.get("verified_object_count") != cycle.object_count
            ):
                blocker = "archive_proof_unavailable"
                break
            rows = tuple(db.scalars(
                select(MediaArchiveObject)
                .where(
                    MediaArchiveObject.tenant_id == tenant_id,
                    MediaArchiveObject.cycle_id == cycle.id,
                )
                .order_by(MediaArchiveObject.id)
            ))
            cycle_blocker = validate_cycle_catalog_for_deletion(cycle, rows)
            if cycle_blocker:
                blocker = cycle_blocker
                break
            for row in rows:
                assert row.remote_object_id is not None
                if row.remote_object_id in remote_ids:
                    blocker = "duplicate_remote_identity"
                    break
                remote_ids.add(row.remote_object_id)
                inventory.append({
                    "cycle_id": str(cycle.id),
                    "object_id": str(row.id),
                    "source_ref": row.source_ref,
                    "object_type": row.object_type,
                    "mime_type": row.mime_type,
                    "size_bytes": row.size_bytes,
                    "sha256": row.sha256,
                    "remote_object_id": row.remote_object_id,
                })
                object_count += 1
                total_bytes += row.size_bytes
            if blocker:
                break
            objects_by_cycle[cycle.id] = rows

    canonical_inventory = json.dumps(
        inventory, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return MediaDeletionPlan(
        closure=closure,
        cycles=cycles,
        objects_by_cycle=objects_by_cycle,
        inventory_sha256=sha256(canonical_inventory).hexdigest(),
        object_count=object_count,
        total_bytes=total_bytes,
        blocker=blocker,
    )


def media_deletion_console_payload(db: Session, *, tenant_id: UUID) -> dict:
    """Devolve somente elegibilidade e progresso sanitizado ao console privado."""
    from app.tenant_closure_recovery import _ten_year_anniversary

    tenant = db.get(Tenant, tenant_id, populate_existing=True)
    if tenant is None:
        raise HTTPException(404, "Conta não encontrada.")
    closure = _latest_closure(db, tenant_id)
    current_closure = (
        closure if tenant.lifecycle == "closed" and closure and closure.state == "closed" else None
    )
    batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
        TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        TenantClosureMediaDeletionBatch.closure_request_id == current_closure.id,
    )) if current_closure else None
    if batch is not None:
        rows = db.execute(
            select(MediaArchiveOperation.status, MediaArchiveOperation.last_error_code)
            .join(
                TenantClosureMediaDeletionItem,
                (TenantClosureMediaDeletionItem.operation_id == MediaArchiveOperation.id)
                & (TenantClosureMediaDeletionItem.tenant_id == MediaArchiveOperation.tenant_id),
            )
            .where(
                TenantClosureMediaDeletionItem.tenant_id == tenant_id,
                TenantClosureMediaDeletionItem.batch_id == batch.id,
            )
            .order_by(MediaArchiveOperation.created_at, MediaArchiveOperation.id)
        ).all()
        pending = any(status in {"queued", "processing"} for status, _error in rows)
        retryable = any(status in _RETRYABLE_OPERATION_STATES for status, _error in rows)
        can_retry = batch.state in {"attention_required", "reconciliation_required"} and retryable and not pending
        blocker = "media_already_deleted" if batch.state == "completed" else None
        return {
            "eligible": False,
            "blocker": blocker or "deletion_already_requested",
            "confirmation_phrase": DELETION_CONFIRMATION,
            "review_due": True,
            "batch": {
                "batch_id": str(batch.id),
                "state": batch.state,
                "object_count": batch.object_count,
                "verified_deleted_object_count": batch.verified_deleted_object_count,
                "cycle_count": len({
                    cycle_id for (cycle_id,) in db.execute(select(
                        TenantClosureMediaDeletionItem.cycle_id,
                    ).where(
                        TenantClosureMediaDeletionItem.batch_id == batch.id,
                        TenantClosureMediaDeletionItem.tenant_id == tenant_id,
                    ))
                }),
                "operations": [
                    {"status": status, "error_code": _safe_error_code(error)}
                    for status, error in rows
                ],
                "retry_available": can_retry,
            },
            "observed_at": _utc(now()).isoformat(),
        }

    plan = evaluate_media_deletion_preflight(db, tenant_id=tenant_id)
    review_due = bool(
        current_closure
        and current_closure.closed_at
        and _utc(now()) >= _ten_year_anniversary(_utc(current_closure.closed_at))
    )
    return {
        "eligible": plan.blocker is None,
        "blocker": plan.blocker,
        "confirmation_phrase": DELETION_CONFIRMATION,
        "review_due": review_due,
        "batch": None,
        "observed_at": _utc(now()).isoformat(),
    }


def _safe_error_code(value: str | None) -> str | None:
    if value and re.fullmatch(r"[a-z0-9_]{1,32}", value):
        return value
    return "operation_error" if value else None


def batch_inventory_snapshot(
    db: Session,
    *,
    batch_id: UUID,
) -> tuple[str, int, int, set[UUID], bool]:
    """Recalcula o recibo sem devolver identidades remotas ao chamador."""
    cycles = list(db.scalars(
        select(MediaArchiveCycle)
        .join(
            TenantClosureMediaDeletionItem,
            (TenantClosureMediaDeletionItem.cycle_id == MediaArchiveCycle.id)
            & (TenantClosureMediaDeletionItem.tenant_id == MediaArchiveCycle.tenant_id),
        )
        .where(TenantClosureMediaDeletionItem.batch_id == batch_id)
        .order_by(MediaArchiveCycle.cycle_number, MediaArchiveCycle.folder_id, MediaArchiveCycle.id)
    ))
    inventory: list[dict[str, object]] = []
    object_count = 0
    total_bytes = 0
    all_deleted = True
    cycle_ids: set[UUID] = set()
    for cycle in cycles:
        cycle_ids.add(cycle.id)
        rows = db.scalars(select(MediaArchiveObject).where(
            MediaArchiveObject.tenant_id == cycle.tenant_id,
            MediaArchiveObject.cycle_id == cycle.id,
        ).order_by(MediaArchiveObject.id))
        for row in rows:
            inventory.append({
                "cycle_id": str(cycle.id),
                "object_id": str(row.id),
                "source_ref": row.source_ref,
                "object_type": row.object_type,
                "mime_type": row.mime_type,
                "size_bytes": row.size_bytes,
                "sha256": row.sha256,
                "remote_object_id": row.remote_object_id,
            })
            object_count += 1
            total_bytes += row.size_bytes
            all_deleted = all_deleted and row.remote_deleted_at is not None
    canonical_inventory = json.dumps(
        inventory, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return sha256(canonical_inventory).hexdigest(), object_count, total_bytes, cycle_ids, all_deleted


def request_media_deletion(
    db: Session,
    *,
    owner_id: UUID,
    tenant_id: UUID,
    request_id: UUID,
    confirmation: str,
) -> dict:
    """Registra uma única exclusão por encerramento, após preflight global."""
    if not is_owner(db, owner_id):
        raise HTTPException(403, "Acesso não autorizado.")
    if confirmation != DELETION_CONFIRMATION:
        raise HTTPException(422, "A confirmação explícita não corresponde à ação.")
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update()
                       .execution_options(populate_existing=True))
    if tenant is None:
        raise HTTPException(404, "Conta não encontrada.")

    previous = db.scalar(select(TenantClosureMediaDeletionBatch).where(
        TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        TenantClosureMediaDeletionBatch.request_id == request_id,
    ))
    if previous is not None:
        if previous.requested_by_owner_admin_id != owner_id:
            raise HTTPException(409, "Identificador já utilizado em outra operação.")
        return {**media_deletion_console_payload(db, tenant_id=tenant_id), "replayed": True}

    plan = evaluate_media_deletion_preflight(db, tenant_id=tenant_id)
    if plan.blocker:
        raise HTTPException(409, "A conta ainda não atende aos requisitos para exclusão da mídia.")
    if plan.closure is None:
        raise HTTPException(409, "Histórico atual de encerramento indisponível.")

    batch = TenantClosureMediaDeletionBatch(
        id=uuid4(),
        tenant_id=tenant_id,
        closure_request_id=plan.closure.id,
        requested_by_owner_admin_id=owner_id,
        request_id=request_id,
        state="queued",
        inventory_sha256=plan.inventory_sha256,
        object_count=plan.object_count,
        verified_deleted_object_count=0,
        total_bytes=plan.total_bytes,
        requested_at=now(),
        completed_at=None,
        updated_at=now(),
    )
    db.add(batch)
    db.flush()
    for cycle in plan.cycles:
        operation = MediaArchiveOperation(
            id=uuid4(),
            tenant_id=tenant_id,
            cycle_id=cycle.id,
            operation_type="delete_remote",
            status="queued",
            stage=None,
            idempotency_key=f"tenant-media-deletion:{plan.closure.id}:{cycle.id}",
            actor_type="owner",
            actor_admin_id=owner_id,
            details={"deletion_batch_id": str(batch.id)},
        )
        db.add(operation)
        db.flush()
        db.add(TenantClosureMediaDeletionItem(
            tenant_id=tenant_id,
            batch_id=batch.id,
            cycle_id=cycle.id,
            operation_id=operation.id,
        ))
        cycle.state = "deleting"
        cycle.updated_at = now()

    audit(db, "tenant.media_deletion_requested", str(batch.id), tenant_id=tenant_id)
    db.flush()
    return {**media_deletion_console_payload(db, tenant_id=tenant_id), "replayed": False}


def retry_media_deletion(
    db: Session,
    *,
    owner_id: UUID,
    tenant_id: UUID,
    confirmation: str,
) -> dict:
    """Reenfileira somente operações falhas, sob nova confirmação do proprietário."""
    if not is_owner(db, owner_id):
        raise HTTPException(403, "Acesso não autorizado.")
    if confirmation != DELETION_CONFIRMATION:
        raise HTTPException(422, "A confirmação explícita não corresponde à ação.")
    # Serialize queue retries with worker claims/completions before locking
    # tenant, batch, operation, or cycle rows. The worker holds this row while
    # it locks operation -> cycle -> batch, so taking it first avoids inversion.
    coordinator = db.scalar(select(MediaArchiveCoordinator).where(
        MediaArchiveCoordinator.id == 1,
    ).with_for_update())
    if coordinator is None:
        raise HTTPException(503, "Coordenador global indisponível.")
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update()
                       .execution_options(populate_existing=True))
    if tenant is None:
        raise HTTPException(404, "Conta não encontrada.")
    closure = _latest_closure(db, tenant_id)
    if tenant.lifecycle != "closed" or closure is None or closure.state != "closed":
        raise HTTPException(409, "O encerramento atual não pode ser confirmado.")
    batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
        TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        TenantClosureMediaDeletionBatch.closure_request_id == closure.id,
    ).with_for_update())
    if batch is None or batch.state == "completed":
        raise HTTPException(409, "Não há exclusão pendente que possa ser retomada.")
    operations = list(db.scalars(
        select(MediaArchiveOperation)
        .join(
            TenantClosureMediaDeletionItem,
            (TenantClosureMediaDeletionItem.operation_id == MediaArchiveOperation.id)
            & (TenantClosureMediaDeletionItem.tenant_id == MediaArchiveOperation.tenant_id),
        )
        .where(
            TenantClosureMediaDeletionItem.tenant_id == tenant_id,
            TenantClosureMediaDeletionItem.batch_id == batch.id,
        )
        .with_for_update()
    ))
    if any(operation.status in {"queued", "processing"} for operation in operations):
        raise HTTPException(409, "A exclusão ainda está em andamento.")
    retryable = [operation for operation in operations if operation.status in _RETRYABLE_OPERATION_STATES]
    if not retryable:
        raise HTTPException(409, "Não há operação falha ou pendente de reconciliação para retomar.")
    for operation in retryable:
        if operation.lease_token is not None or operation.lease_expires_at is not None:
            raise HTTPException(409, "A operação ainda mantém um lease e requer reconciliação.")
        cycle = db.scalar(select(MediaArchiveCycle).where(
            MediaArchiveCycle.id == operation.cycle_id,
            MediaArchiveCycle.tenant_id == tenant_id,
        ).with_for_update())
        if cycle is None or cycle.state != "deleting":
            raise HTTPException(409, "O ciclo não está pronto para nova tentativa.")
        operation.status = "queued"
        operation.updated_at = now()
        operation.last_error = None
        operation.last_error_code = None
    batch.state = "queued"
    batch.last_error_code = None
    batch.completed_at = None
    batch.updated_at = now()
    audit(db, "tenant.media_deletion_retry", str(batch.id), tenant_id=tenant_id)
    db.flush()
    return {**media_deletion_console_payload(db, tenant_id=tenant_id), "replayed": False}
