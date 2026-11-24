"""Fila durável e leases para transferências locais/sintéticas de arquivo frio.

Este módulo não descobre credenciais nem seleciona um adapter Google. O caller
injeta o transporte permitido pela etapa que executa o job.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_hex
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.auth import (
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveEvent,
    MediaArchiveObject,
    MediaArchiveOperation,
    MediaArchiveRecoveryCreditReservation,
    MediaArchiveRecoveryRequest,
    PhotoFolder,
    PhotographerBusinessProfile,
    Tenant,
    TenantClosureMediaDeletionBatch,
    TenantClosureMediaDeletionItem,
    TenantClosureRequest,
    audit,
    now,
)
from app.media_archive_billing import recovery_is_exempt
from app.media_archive_guards import archive_blocker, lock_archive_scope
from app.media_archive_staging import release_restore_space


class MediaArchiveLeaseConflict(RuntimeError):
    """A coordenação global ou o lease durável diverge do estado do job."""


class MediaArchiveTransitionError(RuntimeError):
    """Uma transição de operação/ciclo não é válida para o worker."""


class MediaArchivePreflightError(MediaArchiveTransitionError):
    """O arquivo ainda não pode começar com segurança."""

    def __init__(self, code: str):
        super().__init__("A pasta ainda não passou pelo pré-flight do arquivo.")
        self.code = code


@dataclass(frozen=True)
class MediaArchiveClaim:
    operation_id: UUID
    tenant_id: UUID
    lease_token: str
    lease_expires_at: datetime


_ARCHIVE_STAGES = (
    "snapshot",
    "uploading",
    "reading_back",
    "manifest_upload",
    "manifest_readback",
    "local_cleanup",
)
_RESTORE_STAGES = (
    "preflight",
    "downloading",
    "verifying",
    "promoting",
    "verified_promoted",
)
_DELETE_STAGES = (
    "preflight",
    "manifest_verified",
    "objects_deleting",
    "manifest_deleting",
    "objects_verified",
)


def begin_archive_copy(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    at: datetime | None = None,
) -> None:
    """Congela gravações e valida elegibilidade antes de medir o snapshot."""
    instant = _utc(at or now())
    assert instant is not None
    _coordinator, operation, cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    if operation.operation_type != "archive":
        db.rollback()
        raise MediaArchiveTransitionError("A operação não é um arquivamento.")
    if cycle.state == "archived" and operation.stage == "local_cleanup":
        db.commit()
        return
    if cycle.state not in {"local", "archiving"}:
        db.rollback()
        raise MediaArchiveTransitionError("O ciclo não pode iniciar ou retomar o arquivamento.")
    folder_row = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == cycle.folder_id, PhotoFolder.tenant_id == cycle.tenant_id,
    ))
    scope = lock_archive_scope(db, folder_row) if folder_row else None
    if scope is None:
        db.rollback()
        raise MediaArchiveTransitionError("A pasta não pode ser congelada para arquivo.")
    folder, _gallery = scope
    if cycle.state == "local":
        if operation.stage is not None:
            db.rollback()
            raise MediaArchiveTransitionError("O estágio da operação diverge do ciclo local.")
        blocker = archive_blocker(db, folder, at=instant)
        if blocker:
            db.rollback()
            raise MediaArchivePreflightError(blocker)
        previous = cycle.state
        cycle.state = "archiving"
        cycle.updated_at = instant
        _append_event(
            db,
            operation=operation,
            event_type="archive_started",
            at=instant,
            cycle_state_before=previous,
            cycle_state_after="archiving",
            operation_status_before="processing",
            operation_status_after="processing",
            details={"preflight": "passed"},
        )
    db.commit()


def begin_archive_cleanup(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    at: datetime | None = None,
) -> None:
    """Oculta a pasta atomicamente antes do primeiro unlink local."""
    instant = _utc(at or now())
    assert instant is not None
    _coordinator, operation, cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    if operation.operation_type != "archive":
        db.rollback()
        raise MediaArchiveTransitionError("A operação não é um arquivamento.")
    details = dict(operation.details or {})
    if operation.stage == "local_cleanup" and cycle.state == "archived":
        db.commit()
        return
    if (
        operation.stage != "manifest_readback"
        or cycle.state != "archiving"
        or details.get("readback_verified") is not True
        or details.get("manifest_readback_verified") is not True
        or details.get("verified_object_count") != cycle.object_count
    ):
        db.rollback()
        raise MediaArchiveTransitionError("Readback completo não foi confirmado antes do cleanup.")
    folder_row = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == cycle.folder_id, PhotoFolder.tenant_id == cycle.tenant_id,
    ))
    scope = lock_archive_scope(db, folder_row) if folder_row else None
    if scope is None:
        db.rollback()
        raise MediaArchiveTransitionError("A pasta não pode iniciar o cleanup local.")
    folder, _gallery = scope
    blocker = archive_blocker(db, folder, at=instant)
    if blocker:
        db.rollback()
        raise MediaArchivePreflightError(blocker)

    previous = cycle.state
    cycle.state = "archived"
    cycle.archived_at = instant
    cycle.updated_at = instant
    operation.stage = "local_cleanup"
    details["cleanup_started"] = True
    operation.details = details
    operation.updated_at = instant
    _append_event(
        db,
        operation=operation,
        event_type="archive_cleanup_started",
        at=instant,
        cycle_state_before=previous,
        cycle_state_after="archived",
        operation_status_before="processing",
        operation_status_after="processing",
        details={"verified_object_count": cycle.object_count},
    )
    db.commit()


def begin_restore_operation(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    at: datetime | None = None,
) -> None:
    """Oculta o ciclo antes do pré-flight e permite retomar a mesma operação."""
    instant = _utc(at or now())
    assert instant is not None
    _coordinator, operation, cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    if operation.operation_type != "restore":
        db.rollback()
        raise MediaArchiveTransitionError("A operação não é uma recuperação.")

    request = db.scalar(select(MediaArchiveRecoveryRequest).where(
        MediaArchiveRecoveryRequest.tenant_id == operation.tenant_id,
        MediaArchiveRecoveryRequest.operation_id == operation.id,
        MediaArchiveRecoveryRequest.cycle_id == cycle.id,
    ).with_for_update())
    reservation = db.scalar(select(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.tenant_id == operation.tenant_id,
        MediaArchiveRecoveryCreditReservation.operation_id == operation.id,
    ).with_for_update())
    details = dict(operation.details or {})
    if (
        request is None
        or reservation is None
        or request.duration_days not in {7, 14, 30}
        or details.get("recovery_duration_days") != request.duration_days
        or details.get("owner_exempt") is not request.owner_exempt
        or details.get("technical_cover_exempt", False) is not request.technical_cover_exempt
        or reservation.status != ("exempt" if recovery_is_exempt(request) else "reserved")
        or reservation.reserved_credits != (0 if recovery_is_exempt(request) else request.fee_credits_snapshot)
    ):
        db.rollback()
        raise MediaArchiveTransitionError("Pedido e reserva da recuperação não conferem.")

    folder_row = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == cycle.folder_id,
        PhotoFolder.tenant_id == operation.tenant_id,
        PhotoFolder.parent_gallery_id == cycle.parent_gallery_id,
        PhotoFolder.purpose.in_(("content", "cover_assets")),
    ))
    scope = lock_archive_scope(db, folder_row) if folder_row else None
    if scope is None:
        db.rollback()
        raise MediaArchiveTransitionError("A pasta não pode ser recuperada neste estado.")

    if cycle.state == "archived":
        if operation.stage is not None:
            db.rollback()
            raise MediaArchiveTransitionError("O estágio não corresponde ao ciclo arquivado.")
        previous = cycle.state
        cycle.state = "restoring"
        cycle.updated_at = instant
        operation.stage = "preflight"
        operation.updated_at = instant
        _append_event(
            db,
            operation=operation,
            event_type="recovery_started",
            at=instant,
            cycle_state_before=previous,
            cycle_state_after="restoring",
            operation_status_before="processing",
            operation_status_after="processing",
            details={
                "duration_days": request.duration_days,
                "requester_type": request.requester_type,
                "manual_retry": request.retry_of_operation_id is not None,
            },
        )
    elif cycle.state == "restoring":
        if operation.stage not in _RESTORE_STAGES:
            db.rollback()
            raise MediaArchiveTransitionError("O checkpoint não corresponde ao ciclo em recuperação.")
        expected_reservation_state = "exempt" if recovery_is_exempt(request) else "reserved"
        if details.get("restore_space_reserved") and reservation.status != expected_reservation_state:
            db.rollback()
            raise MediaArchiveTransitionError("A reserva financeira não pode retomar esta recuperação.")
    else:
        db.rollback()
        raise MediaArchiveTransitionError("O ciclo não pode iniciar ou retomar a recuperação.")
    db.commit()


def begin_delete_operation(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    at: datetime | None = None,
) -> None:
    """Inicia somente um job de exclusão ligado ao lote autorizado do proprietário."""
    instant = _utc(at or now())
    assert instant is not None
    _coordinator, operation, cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    if operation.operation_type != "delete_remote" or cycle.state != "deleting":
        db.rollback()
        raise MediaArchiveTransitionError("A operação de exclusão não corresponde ao ciclo ativo.")
    if operation.stage is None:
        operation.stage = "preflight"
    elif operation.stage not in _DELETE_STAGES:
        db.rollback()
        raise MediaArchiveTransitionError("Checkpoint de exclusão inválido.")
    batch = _deletion_batch_for_operation(db, operation)
    if batch is None or batch.state not in {
        "queued", "processing", "attention_required", "reconciliation_required",
    }:
        db.rollback()
        raise MediaArchiveTransitionError("Lote de exclusão não está pronto para execução.")
    previous = batch.state
    batch.state = "processing"
    batch.updated_at = instant
    operation.updated_at = instant
    _append_event(
        db,
        operation=operation,
        event_type="media_deletion_started",
        at=instant,
        cycle_state_before=cycle.state,
        cycle_state_after=cycle.state,
        operation_status_before="processing",
        operation_status_after="processing",
        details={"batch_state_before": previous, "stage": operation.stage},
    )
    db.commit()


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    return value.astimezone(timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.


def _append_event(
    db: Session,
    *,
    operation: MediaArchiveOperation,
    event_type: str,
    at: datetime,
    cycle_state_before: str | None = None,
    cycle_state_after: str | None = None,
    operation_status_before: str | None = None,
    operation_status_after: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(MediaArchiveEvent(
        tenant_id=operation.tenant_id,
        cycle_id=operation.cycle_id,
        operation_id=operation.id,
        actor_type=operation.actor_type,
        actor_admin_id=operation.actor_admin_id,
        event_type=event_type,
        cycle_state_before=cycle_state_before,
        cycle_state_after=cycle_state_after,
        operation_status_before=operation_status_before,
        operation_status_after=operation_status_after,
        details=details or {},
        created_at=at,
    ))
    from app.media_archive_notices import record_transfer_notice

    record_transfer_notice(
        db,
        operation=operation,
        event_type=event_type,
        at=at,
    )


def _new_claim(
    db: Session,
    *,
    coordinator: MediaArchiveCoordinator,
    operation: MediaArchiveOperation,
    at: datetime,
    lease_seconds: int,
    reclaimed: bool,
) -> MediaArchiveClaim:
    old_status = operation.status
    previous_token = operation.lease_token
    token = token_hex(24)
    expires = at + timedelta(seconds=lease_seconds)

    operation.status = "processing"
    operation.lease_token = token
    operation.lease_expires_at = expires
    operation.attempts += 1
    operation.started_at = operation.started_at or at
    operation.updated_at = at
    operation.last_error_code = None
    operation.last_error = None
    coordinator.active_operation_id = operation.id
    coordinator.lease_token = token
    coordinator.lease_expires_at = expires
    coordinator.updated_at = at

    _append_event(
        db,
        operation=operation,
        event_type="lease_reclaimed" if reclaimed else "lease_claimed",
        at=at,
        operation_status_before=old_status,
        operation_status_after="processing",
        details={"attempt": operation.attempts, "previous_lease_present": bool(previous_token)},
    )
    db.flush()
    return MediaArchiveClaim(operation.id, operation.tenant_id, token, expires)


def claim_next_operation(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    lease_seconds: int = 120,
    at: datetime | None = None,
) -> MediaArchiveClaim | None:
    """Claim atômico, global e FIFO; a sessão do worker deve estar limpa.

    A linha coordenadora serializa as réplicas. Se já houver lease vigente, ou
    se os registros do lease divergirem, nenhum segundo job é iniciado.
    """
    if tenant_id is not None and not isinstance(tenant_id, UUID):
        raise ValueError("Tenant de arquivo frio inválido.")
    if type(lease_seconds) is not int or not 1 <= lease_seconds <= 86_400:
        raise ValueError("Duração de lease inválida.")
    instant = _utc(at or now())
    assert instant is not None
    coordinator = db.scalar(
        select(MediaArchiveCoordinator)
        .where(MediaArchiveCoordinator.id == 1)
        .with_for_update()
    )
    if coordinator is None:
        db.rollback()
        raise MediaArchiveLeaseConflict("Coordenador global indisponível.")

    if coordinator.active_operation_id is not None:
        active = db.scalar(
            select(MediaArchiveOperation)
            .where(MediaArchiveOperation.id == coordinator.active_operation_id)
            .with_for_update()
        )
        if active is None:
            db.rollback()
            raise MediaArchiveLeaseConflict("Lease global aponta para operação ausente.")
        if tenant_id is not None and active.tenant_id != tenant_id:
            db.rollback()
            return None
        coordinator_expiry = _utc(coordinator.lease_expires_at)
        active_expiry = _utc(active.lease_expires_at)
        if (
            active.status == "processing"
            and active.lease_token == coordinator.lease_token
            and active_expiry == coordinator_expiry
        ):
            if coordinator_expiry is not None and coordinator_expiry > instant:
                db.rollback()
                return None
            if active_expiry is None or active_expiry > instant:
                db.rollback()
                raise MediaArchiveLeaseConflict("Expiração do lease global diverge do job.")
            active_tenant = db.scalar(select(Tenant.id).where(
                Tenant.id == active.tenant_id, Tenant.status == "active",
            ).with_for_update(skip_locked=True))
            if active_tenant is None:
                db.rollback()
                return None
            claim = _new_claim(
                db,
                coordinator=coordinator,
                operation=active,
                at=instant,
                lease_seconds=lease_seconds,
                reclaimed=True,
            )
            db.commit()
            return claim

        if active.status in {"failed", "completed", "cancelled", "reconciliation_required"}:
            coordinator.active_operation_id = None
            coordinator.lease_token = None
            coordinator.lease_expires_at = None
            coordinator.updated_at = instant
        else:
            db.rollback()
            raise MediaArchiveLeaseConflict("Estado do lease global diverge do job ativo.")

    orphaned = db.scalar(
        select(MediaArchiveOperation.id)
        .where(MediaArchiveOperation.status == "processing")
        .limit(1)
    )
    if orphaned is not None:
        db.rollback()
        raise MediaArchiveLeaseConflict("Operação em processamento sem lease global; exige reconciliação.")

    operation = db.scalar(
        select(MediaArchiveOperation)
        .join(Tenant, Tenant.id == MediaArchiveOperation.tenant_id)
        .where(
            Tenant.status == "active",
            MediaArchiveOperation.tenant_id == tenant_id if tenant_id is not None else True,
            MediaArchiveOperation.status == "queued",
            MediaArchiveOperation.operation_type.in_(("restore", "delete_remote", "archive")),
        )
        .order_by(
            case(
                (MediaArchiveOperation.operation_type == "restore", 0),
                (MediaArchiveOperation.operation_type == "delete_remote", 1),
                else_=2,
            ),
            MediaArchiveOperation.created_at,
            MediaArchiveOperation.id,
        )
        .limit(1)
        .with_for_update(skip_locked=True, of=(Tenant, MediaArchiveOperation))
    )
    if operation is None:
        db.commit()
        return None
    if operation.lease_token is not None or operation.lease_expires_at is not None:
        db.rollback()
        raise MediaArchiveLeaseConflict("Job enfileirado contém lease inesperado.")

    claim = _new_claim(
        db,
        coordinator=coordinator,
        operation=operation,
        at=instant,
        lease_seconds=lease_seconds,
        reclaimed=False,
    )
    db.commit()
    return claim


def _locked_claim(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    at: datetime,
) -> tuple[MediaArchiveCoordinator, MediaArchiveOperation, MediaArchiveCycle]:
    coordinator = db.scalar(
        select(MediaArchiveCoordinator)
        .where(MediaArchiveCoordinator.id == 1)
        .with_for_update()
    )
    operation = db.scalar(
        select(MediaArchiveOperation)
        .where(MediaArchiveOperation.id == operation_id)
        .with_for_update()
    )
    if (
        coordinator is None
        or operation is None
        or coordinator.active_operation_id != operation.id
        or coordinator.lease_token != lease_token
        or operation.lease_token != lease_token
        or operation.status != "processing"
        or _utc(coordinator.lease_expires_at) != _utc(operation.lease_expires_at)
        or _utc(operation.lease_expires_at) is None
        or _utc(operation.lease_expires_at) <= at
    ):
        db.rollback()
        raise MediaArchiveLeaseConflict("Lease global não pertence a esta execução.")
    cycle = db.scalar(
        select(MediaArchiveCycle)
        .where(
            MediaArchiveCycle.id == operation.cycle_id,
            MediaArchiveCycle.tenant_id == operation.tenant_id,
        )
        .with_for_update()
    )
    if cycle is None:
        db.rollback()
        raise MediaArchiveTransitionError("Ciclo de arquivo frio indisponível.")
    if operation.operation_type == "restore":
        from app.tenant_closure_recovery import bind_operation_recovery
        bind_operation_recovery(db, operation, lease_token)
    elif operation.operation_type == "delete_remote":
        batch = _deletion_batch_for_operation(db, operation)
        tenant = db.get(Tenant, operation.tenant_id, populate_existing=True)
        closure = db.scalar(select(TenantClosureRequest).where(
            TenantClosureRequest.id == batch.closure_request_id,
            TenantClosureRequest.tenant_id == operation.tenant_id,
        )) if batch else None
        from app.system_monitor.access import is_owner
        from app.tenant_closure_recovery import _ten_year_anniversary

        if (
            batch is None
            or batch.state not in {
                "queued", "processing", "attention_required", "reconciliation_required",
            }
            or operation.actor_type != "owner"
            or operation.actor_admin_id != batch.requested_by_owner_admin_id
            or not is_owner(db, batch.requested_by_owner_admin_id)
            or tenant is None
            or tenant.lifecycle != "closed"
            or closure is None
            or closure.state != "closed"
            or closure.closed_at is None
            or at < _utc(_ten_year_anniversary(closure.closed_at))
            or cycle.state != "deleting"
        ):
            db.rollback()
            raise MediaArchiveTransitionError("Autorização de exclusão fria não confere.")
    return coordinator, operation, cycle


def _deletion_batch_for_operation(
    db: Session,
    operation: MediaArchiveOperation,
) -> TenantClosureMediaDeletionBatch | None:
    return db.scalar(
        select(TenantClosureMediaDeletionBatch)
        .join(
            TenantClosureMediaDeletionItem,
            (TenantClosureMediaDeletionItem.batch_id == TenantClosureMediaDeletionBatch.id)
            & (TenantClosureMediaDeletionItem.tenant_id == TenantClosureMediaDeletionBatch.tenant_id),
        )
        .where(
            TenantClosureMediaDeletionItem.tenant_id == operation.tenant_id,
            TenantClosureMediaDeletionItem.operation_id == operation.id,
            TenantClosureMediaDeletionItem.cycle_id == operation.cycle_id,
        )
        .with_for_update()
    )


def renew_operation_lease(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    lease_seconds: int = 120,
    at: datetime | None = None,
) -> datetime:
    """Estende ambos os registros do lease em uma única transação curta."""
    if type(lease_seconds) is not int or not 1 <= lease_seconds <= 86_400:
        raise ValueError("Duração de lease inválida.")
    instant = _utc(at or now())
    assert instant is not None
    coordinator, operation, _cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    expiry = instant + timedelta(seconds=lease_seconds)
    operation.lease_expires_at = expiry
    operation.updated_at = instant
    coordinator.lease_expires_at = expiry
    coordinator.updated_at = instant
    db.commit()
    return expiry


def checkpoint_operation(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    stage: str,
    details_patch: dict | None = None,
    at: datetime | None = None,
) -> None:
    """Grava checkpoint não regressivo antes do worker avançar para outro passo."""
    instant = _utc(at or now())
    assert instant is not None
    _coordinator, operation, cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    stages = (
        _ARCHIVE_STAGES if operation.operation_type == "archive"
        else _RESTORE_STAGES if operation.operation_type == "restore"
        else _DELETE_STAGES
    )
    if operation.operation_type not in {"archive", "restore", "delete_remote"} or stage not in stages:
        db.rollback()
        raise MediaArchiveTransitionError("Etapa não permitida para este tipo de operação.")
    expected_cycle_state = "archived" if (
        operation.operation_type == "archive" and stage == "local_cleanup"
    ) else "archiving" if operation.operation_type == "archive" else (
        "deleting" if operation.operation_type == "delete_remote" else "restoring"
    )
    if cycle.state != expected_cycle_state:
        db.rollback()
        raise MediaArchiveTransitionError("Ciclo não está na fase correspondente ao checkpoint.")
    if stage == "local_cleanup" and (
        operation.stage != "local_cleanup"
        or (operation.details or {}).get("cleanup_started") is not True
    ):
        db.rollback()
        raise MediaArchiveTransitionError("A etapa de cleanup deve ser iniciada pela transição protegida.")
    current_index = stages.index(operation.stage) if operation.stage in stages else -1
    next_index = stages.index(stage)
    if next_index < current_index or next_index > current_index + 1:
        db.rollback()
        raise MediaArchiveTransitionError("Checkpoint não pode regredir ou saltar uma etapa.")

    operation_details = dict(operation.details or {})
    if details_patch:
        operation_details.update(details_patch)
    operation.details = operation_details
    operation.stage = stage
    operation.updated_at = instant
    _append_event(
        db,
        operation=operation,
        event_type="checkpoint_saved",
        at=instant,
        cycle_state_before=cycle.state,
        cycle_state_after=cycle.state,
        operation_status_before="processing",
        operation_status_after="processing",
        details={"stage": stage},
    )
    db.commit()


def mark_remote_object_deleted(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    object_id: UUID,
    at: datetime | None = None,
) -> None:
    """Grava o checkpoint somente após readback confirmar ausência remota."""
    instant = _utc(at or now())
    assert instant is not None
    _coordinator, operation, cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    if operation.operation_type != "delete_remote" or cycle.state != "deleting":
        db.rollback()
        raise MediaArchiveTransitionError("Checkpoint de exclusão fora da operação autorizada.")
    batch = _deletion_batch_for_operation(db, operation)
    row = db.scalar(select(MediaArchiveObject).where(
        MediaArchiveObject.id == object_id,
        MediaArchiveObject.tenant_id == operation.tenant_id,
        MediaArchiveObject.cycle_id == cycle.id,
    ).with_for_update())
    if batch is None or row is None:
        db.rollback()
        raise MediaArchiveTransitionError("Objeto do checkpoint não pertence ao lote ativo.")
    row.remote_deleted_at = row.remote_deleted_at or instant
    batch.verified_deleted_object_count = db.scalar(
        select(func.count(MediaArchiveObject.id))
        .join(
            TenantClosureMediaDeletionItem,
            (TenantClosureMediaDeletionItem.cycle_id == MediaArchiveObject.cycle_id)
            & (TenantClosureMediaDeletionItem.tenant_id == MediaArchiveObject.tenant_id),
        )
        .where(
            TenantClosureMediaDeletionItem.tenant_id == batch.tenant_id,
            TenantClosureMediaDeletionItem.batch_id == batch.id,
            MediaArchiveObject.remote_deleted_at.is_not(None),
        )
    ) or 0
    batch.updated_at = instant
    operation.updated_at = instant
    db.commit()


def _release_global_lease(
    coordinator: MediaArchiveCoordinator,
    operation: MediaArchiveOperation,
    *,
    at: datetime,
) -> None:
    coordinator.active_operation_id = None
    coordinator.lease_token = None
    coordinator.lease_expires_at = None
    coordinator.updated_at = at
    operation.lease_token = None
    operation.lease_expires_at = None
    operation.updated_at = at


def complete_archive_operation(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    at: datetime | None = None,
) -> None:
    """Confirma arquivo somente após readback verificado e cleanup local concluído."""
    instant = _utc(at or now())
    assert instant is not None
    coordinator, operation, cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    if (
        operation.operation_type != "archive"
        or operation.stage != "local_cleanup"
        or cycle.state != "archived"
        or (operation.details or {}).get("readback_verified") is not True
        or (operation.details or {}).get("local_cleanup_complete") is not True
        or (operation.details or {}).get("cleanup_started") is not True
    ):
        db.rollback()
        raise MediaArchiveTransitionError("Arquivo não passou por readback e cleanup completos.")
    previous = cycle.state
    cycle.state = "archived"
    cycle.archived_at = instant
    cycle.updated_at = instant
    operation.status = "completed"
    operation.stage = "completed"
    operation.completed_at = instant
    _release_global_lease(coordinator, operation, at=instant)
    _append_event(
        db,
        operation=operation,
        event_type="archive_completed",
        at=instant,
        cycle_state_before=previous,
        cycle_state_after="archived",
        operation_status_before="processing",
        operation_status_after="completed",
        details={"object_count": int((operation.details or {}).get("verified_object_count", 0))},
    )
    db.commit()


def complete_delete_operation(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    at: datetime | None = None,
) -> bool:
    """Conclui um ciclo e só limpa o fingerprint após fechar o inventário inteiro."""
    instant = _utc(at or now())
    assert instant is not None
    coordinator, operation, cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    batch = _deletion_batch_for_operation(db, operation)
    details = operation.details if isinstance(operation.details, dict) else {}
    rows = list(db.scalars(select(MediaArchiveObject).where(
        MediaArchiveObject.tenant_id == operation.tenant_id,
        MediaArchiveObject.cycle_id == cycle.id,
    )))
    media_count = sum(row.object_type != "manifest" for row in rows)
    manifest_count = sum(row.object_type == "manifest" for row in rows)
    if (
        batch is None
        or operation.operation_type != "delete_remote"
        or operation.stage != "objects_verified"
        or cycle.state != "deleting"
        or details.get("final_readback_verified") is not True
        or details.get("verified_deleted_object_count") != len(rows)
        or any(row.remote_deleted_at is None for row in rows)
        or media_count != cycle.object_count
        or manifest_count != 1
    ):
        db.rollback()
        raise MediaArchiveTransitionError("A exclusão não tem prova completa por objeto.")

    cycle.state = "deleted"
    cycle.updated_at = instant
    operation.status = "completed"
    operation.stage = "completed"
    operation.completed_at = instant
    _release_global_lease(coordinator, operation, at=instant)
    _append_event(
        db,
        operation=operation,
        event_type="media_deletion_cycle_completed",
        at=instant,
        cycle_state_before="deleting",
        cycle_state_after="deleted",
        operation_status_before="processing",
        operation_status_after="completed",
        details={"verified_deleted_object_count": len(rows)},
    )
    db.flush()

    verified_count = db.scalar(
        select(func.count(MediaArchiveObject.id))
        .join(
            TenantClosureMediaDeletionItem,
            (TenantClosureMediaDeletionItem.cycle_id == MediaArchiveObject.cycle_id)
            & (TenantClosureMediaDeletionItem.tenant_id == MediaArchiveObject.tenant_id),
        )
        .where(
            TenantClosureMediaDeletionItem.tenant_id == batch.tenant_id,
            TenantClosureMediaDeletionItem.batch_id == batch.id,
            MediaArchiveObject.remote_deleted_at.is_not(None),
        )
    ) or 0
    batch.verified_deleted_object_count = verified_count
    batch.updated_at = instant
    operations = list(db.scalars(
        select(MediaArchiveOperation)
        .join(
            TenantClosureMediaDeletionItem,
            (TenantClosureMediaDeletionItem.operation_id == MediaArchiveOperation.id)
            & (TenantClosureMediaDeletionItem.tenant_id == MediaArchiveOperation.tenant_id),
        )
        .where(
            TenantClosureMediaDeletionItem.tenant_id == batch.tenant_id,
            TenantClosureMediaDeletionItem.batch_id == batch.id,
        )
        .order_by(MediaArchiveOperation.id)
    ))
    operation_states = {item.status for item in operations}
    if operation_states != {"completed"}:
        if operation_states & {"queued", "processing"}:
            batch.state = "processing"
        elif "reconciliation_required" in operation_states:
            batch.state = "reconciliation_required"
        else:
            batch.state = "attention_required"
        db.commit()
        return True

    from app.tenant_media_deletion import batch_inventory_snapshot

    inventory_sha256, object_count, total_bytes, cycle_ids, all_deleted = batch_inventory_snapshot(
        db, batch_id=batch.id,
    )
    all_tenant_cycle_ids = set(db.scalars(select(MediaArchiveCycle.id).where(
        MediaArchiveCycle.tenant_id == batch.tenant_id,
    )))
    if (
        inventory_sha256 != batch.inventory_sha256
        or object_count != batch.object_count
        or total_bytes != batch.total_bytes
        or cycle_ids != all_tenant_cycle_ids
        or not all_deleted
        or verified_count != batch.object_count
    ):
        cycle.state = "deleting"
        operation.status = "failed"
        operation.completed_at = None
        operation.last_error_code = "inventory_changed"
        operation.last_error = "Inventário de mídia divergente; exclusão requer atenção."
        operation.updated_at = instant
        batch.state = "attention_required"
        batch.last_error_code = "inventory_changed"
        batch.updated_at = instant
        _append_event(
            db,
            operation=operation,
            event_type="operation_failed",
            at=instant,
            cycle_state_before="deleted",
            cycle_state_after="deleting",
            operation_status_before="completed",
            operation_status_after="failed",
            details={"stage": "inventory_verification", "error_code": "inventory_changed"},
        )
        db.commit()
        return False

    profile = db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.tenant_id == batch.tenant_id,
    ).with_for_update())
    if profile is not None:
        profile.cpf_fingerprint = None
        profile.cpf_fingerprint_key_version = None
    batch.state = "completed"
    batch.completed_at = instant
    batch.last_error_code = None
    batch.updated_at = instant
    _append_event(
        db,
        operation=operation,
        event_type="media_deletion_completed",
        at=instant,
        cycle_state_before="deleted",
        cycle_state_after="deleted",
        operation_status_before="completed",
        operation_status_after="completed",
        details={"verified_deleted_object_count": verified_count},
    )
    audit(db, "tenant.media_deletion_completed", str(batch.id), tenant_id=batch.tenant_id)
    db.commit()
    return True


def complete_restore_operation(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    at: datetime | None = None,
) -> None:
    """Ativa a pasta e cobra na mesma transação após readback e promoção completos."""
    from datetime import timedelta

    from app.media_archive_billing import consume_verified_recovery

    instant = _utc(at or now())
    assert instant is not None
    coordinator, operation, cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    details = operation.details or {}
    if (
        operation.operation_type != "restore"
        or operation.stage != "verified_promoted"
        or cycle.state != "restoring"
        or details.get("restore_readback_verified") is not True
        or details.get("restore_manifest_verified") is not True
        or details.get("restored_object_count") != cycle.object_count
        or details.get("promoted_object_count") != cycle.object_count
        or cycle.object_count < 0
    ):
        db.rollback()
        raise MediaArchiveTransitionError("Recuperação não passou por verificação integral e promoção.")

    request = db.scalar(select(MediaArchiveRecoveryRequest).where(
        MediaArchiveRecoveryRequest.tenant_id == operation.tenant_id,
        MediaArchiveRecoveryRequest.operation_id == operation.id,
    ).with_for_update())
    if request is None:
        db.rollback()
        raise MediaArchiveTransitionError("Pedido de cobrança da recuperação indisponível.")
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == cycle.folder_id,
        PhotoFolder.tenant_id == operation.tenant_id,
        PhotoFolder.parent_gallery_id == cycle.parent_gallery_id,
        PhotoFolder.purpose.in_(("content", "cover_assets")),
    ).with_for_update())
    if folder is None:
        db.rollback()
        raise MediaArchiveTransitionError("Pasta da recuperação indisponível.")

    try:
        consume_verified_recovery(db, operation=operation, at=instant)
    except Exception as exc:
        db.rollback()
        raise MediaArchiveTransitionError("Reserva financeira não pôde ser confirmada.") from exc

    previous_cycle = cycle.state
    previous_status = operation.status
    if folder.purpose == "content":
        folder.access_duration_days = request.duration_days
        folder.released_at = instant
        folder.access_expires_at = instant + timedelta(days=request.duration_days)
    folder.updated_at = instant
    cycle.state = "local"
    cycle.updated_at = instant
    operation.status = "completed"
    operation.stage = "completed"
    operation.completed_at = instant
    _release_global_lease(coordinator, operation, at=instant)
    release_restore_space(
        db, tenant_id=operation.tenant_id, operation_id=operation.id, outcome="completed",
    )
    _append_event(
        db,
        operation=operation,
        event_type="recovery_completed",
        at=instant,
        cycle_state_before=previous_cycle,
        cycle_state_after="local",
        operation_status_before=previous_status,
        operation_status_after="completed",
        details={
            "object_count": cycle.object_count,
            "duration_days": request.duration_days,
            "readback_verified": True,
            "manifest_verified": True,
        },
    )
    db.commit()


def fail_operation(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    outcome: str,
    error_code: str,
    at: datetime | None = None,
) -> None:
    """Fecha falha comprovada ou exige reconciliação sem salvar erro bruto."""
    if outcome not in {"proven_failure", "unknown"}:
        raise ValueError("Resultado de falha inválido.")
    if not error_code or len(error_code) > 32 or not error_code.replace("_", "").isalnum():
        raise ValueError("Código de erro sanitizado inválido.")
    instant = _utc(at or now())
    assert instant is not None
    coordinator, operation, cycle = _locked_claim(
        db, operation_id=operation_id, lease_token=lease_token, at=instant,
    )
    if operation.operation_type not in {"archive", "restore", "delete_remote"}:
        db.rollback()
        raise MediaArchiveTransitionError("Falha deste tipo de operação não é processada pelo worker.")
    if (
        outcome == "proven_failure"
        and operation.operation_type == "archive"
        and operation.stage == "local_cleanup"
    ):
        db.rollback()
        raise MediaArchiveTransitionError(
            "Cleanup local iniciado exige confirmação de integridade ou reconciliação."
        )
    before_cycle = cycle.state
    before_status = operation.status
    operation.last_error_code = error_code
    operation.last_error = (
        "Falha comprovada na operação; mídia preservada."
        if outcome == "proven_failure"
        else "Resultado externo incerto; reconciliação necessária."
    )
    if outcome == "unknown":
        operation.status = "reconciliation_required"
        if operation.operation_type != "delete_remote":
            cycle.state = "reconciliation_required"
    else:
        operation.status = "failed"
        if operation.operation_type == "archive" and cycle.state in {"local", "archiving"}:
            cycle.state = "local"
        elif operation.operation_type == "restore" and cycle.state == "restoring":
            cycle.state = "archived"
        elif operation.operation_type == "delete_remote" and cycle.state == "deleting":
            cycle.state = "deleting"
        else:
            db.rollback()
            raise MediaArchiveTransitionError("Estado estável anterior não confere com a operação.")
        if operation.operation_type == "restore":
            try:
                from app.media_archive_billing import release_failed_recovery

                release_failed_recovery(db, operation=operation)
            except Exception as exc:
                db.rollback()
                raise MediaArchiveTransitionError(
                    "Reserva financeira da recuperação não pôde ser liberada."
                ) from exc
            release_restore_space(
                db, tenant_id=operation.tenant_id, operation_id=operation.id,
                outcome="proven_failure",
            )
    if outcome == "unknown" and operation.operation_type == "restore":
        try:
            from app.media_archive_billing import mark_recovery_uncertain

            mark_recovery_uncertain(db, operation=operation)
        except Exception as exc:
            db.rollback()
            raise MediaArchiveTransitionError(
                "Reserva financeira da recuperação não pôde ser mantida em reconciliação."
            ) from exc
    if operation.operation_type == "delete_remote":
        batch = _deletion_batch_for_operation(db, operation)
        if batch is None:
            db.rollback()
            raise MediaArchiveTransitionError("Lote da exclusão fria indisponível para registrar falha.")
        batch.state = "reconciliation_required" if outcome == "unknown" else "attention_required"
        batch.last_error_code = error_code
        batch.updated_at = instant
    operation.updated_at = instant
    cycle.updated_at = instant
    _release_global_lease(coordinator, operation, at=instant)
    _append_event(
        db,
        operation=operation,
        event_type="operation_failed" if outcome == "proven_failure" else "reconciliation_required",
        at=instant,
        cycle_state_before=before_cycle,
        cycle_state_after=cycle.state,
        operation_status_before=before_status,
        operation_status_after=operation.status,
        details={"stage": operation.stage or "unknown", "error_code": error_code},
    )
    db.commit()
