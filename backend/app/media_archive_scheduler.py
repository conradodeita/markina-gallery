"""Descobre pastas vencidas e enfileira ciclos de arquivo frio idempotentes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.auth import (
    GalleryReopeningRequest,
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveEvent,
    MediaArchiveOperation,
    ParentGallery,
    PhotoFolder,
    Tenant,
    now,
)
from app.folder_access import REOPENING_WINDOW, folder_archive_eligible_at
from app.media_archive_guards import (
    archive_blocker,
    isolated_closure_cover_folder,
    lock_archive_scope,
    never_released_closure_folder,
)
from app.media_archive_notices import record_open_order_block_notice, record_window_notice

ARCHIVE_RECHECK_DELAY = timedelta(minutes=5)
DEFAULT_DISCOVERY_LIMIT = 100
WINDOW_NOTICE_LEAD = timedelta(days=7)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    return value.astimezone(timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.


def _candidate_folder_ids(db: Session, *, at: datetime, limit: int, tenant_id: UUID | None = None) -> list:
    latest_cycle_id = (
        select(MediaArchiveCycle.id)
        .where(
            MediaArchiveCycle.folder_id == PhotoFolder.id,
            MediaArchiveCycle.tenant_id == PhotoFolder.tenant_id,
        )
        .order_by(MediaArchiveCycle.cycle_number.desc())
        .limit(1)
        .correlate(PhotoFolder)
        .scalar_subquery()
    )
    latest_cycle = aliased(MediaArchiveCycle)
    latest_archive_status = (
        select(MediaArchiveOperation.status)
        .where(
            MediaArchiveOperation.cycle_id == latest_cycle.id,
            MediaArchiveOperation.tenant_id == latest_cycle.tenant_id,
            MediaArchiveOperation.operation_type == "archive",
        )
        .order_by(MediaArchiveOperation.created_at.desc(), MediaArchiveOperation.id.desc())
        .limit(1)
        .correlate(latest_cycle)
        .scalar_subquery()
    )
    latest_cycle_is_discoverable = or_(
        latest_cycle.id.is_(None),
        and_(
            latest_cycle.state == "local",
            or_(
                latest_cycle.next_archive_check_at.is_(None),
                latest_cycle.next_archive_check_at <= at,
            ),
            or_(latest_archive_status.is_(None), latest_archive_status == "completed"),
        ),
    )
    stmt = (
        select(PhotoFolder.id)
        .join(Tenant, Tenant.id == PhotoFolder.tenant_id)
        .join(
            ParentGallery,
            and_(
                ParentGallery.id == PhotoFolder.parent_gallery_id,
                ParentGallery.tenant_id == PhotoFolder.tenant_id,
            ),
        )
        .outerjoin(latest_cycle, latest_cycle.id == latest_cycle_id)
        .where(
            Tenant.status == "active", Tenant.lifecycle != "closed",
            or_(ParentGallery.active.is_(True), Tenant.lifecycle == "closing"),
            ParentGallery.lifecycle_status == "active",
            or_(
                and_(PhotoFolder.purpose == "content", PhotoFolder.status == "released", PhotoFolder.access_expires_at.is_not(None),
                     PhotoFolder.access_expires_at <= at - REOPENING_WINDOW),
                and_(PhotoFolder.purpose == "content", Tenant.lifecycle == "closing", PhotoFolder.status == "preparing",
                     PhotoFolder.released_at.is_(None), PhotoFolder.audience_scope.in_(("all", "selected"))),
                and_(Tenant.lifecycle == "closing", PhotoFolder.purpose == "cover_assets",
                     ~select(PhotoFolder.id).where(
                         PhotoFolder.tenant_id == Tenant.id,
                         PhotoFolder.parent_gallery_id == ParentGallery.id,
                         PhotoFolder.purpose == "content",
                     ).correlate(Tenant, ParentGallery).exists()),
            ),
            latest_cycle_is_discoverable,
        )
        .order_by(PhotoFolder.access_expires_at, PhotoFolder.id)
        .limit(limit)
    )
    if tenant_id is not None:
        stmt = stmt.where(PhotoFolder.tenant_id == tenant_id)
    return list(db.scalars(stmt))


def _window_notice_candidate_ids(db: Session, *, at: datetime, limit: int, tenant_id: UUID | None = None) -> list:
    latest_reopening_expiry = (
        select(func.max(GalleryReopeningRequest.approved_until))
        .where(
            GalleryReopeningRequest.tenant_id == PhotoFolder.tenant_id,
            GalleryReopeningRequest.photo_folder_id == PhotoFolder.id,
            GalleryReopeningRequest.status == "approved",
            GalleryReopeningRequest.approved_until.is_not(None),
        )
        .correlate(PhotoFolder)
        .scalar_subquery()
    )
    effective_expiry = case(
        (latest_reopening_expiry > PhotoFolder.access_expires_at, latest_reopening_expiry),
        else_=PhotoFolder.access_expires_at,
    )
    latest_cycle_id = (
        select(MediaArchiveCycle.id)
        .where(
            MediaArchiveCycle.folder_id == PhotoFolder.id,
            MediaArchiveCycle.tenant_id == PhotoFolder.tenant_id,
        )
        .order_by(MediaArchiveCycle.cycle_number.desc())
        .limit(1)
        .correlate(PhotoFolder)
        .scalar_subquery()
    )
    latest_notice_expiry = (
        select(MediaArchiveCycle.last_window_notice_for_expiry)
        .where(
            MediaArchiveCycle.id == latest_cycle_id,
            MediaArchiveCycle.tenant_id == PhotoFolder.tenant_id,
        )
        .limit(1)
        .correlate(PhotoFolder)
        .scalar_subquery()
    )
    archive_warning_start = at - REOPENING_WINDOW
    archive_warning_end = at - (REOPENING_WINDOW - WINDOW_NOTICE_LEAD)
    return list(db.scalars(
        select(PhotoFolder.id)
        .join(Tenant, Tenant.id == PhotoFolder.tenant_id)
        .join(
            ParentGallery,
            and_(
                ParentGallery.id == PhotoFolder.parent_gallery_id,
                ParentGallery.tenant_id == PhotoFolder.tenant_id,
            ),
        )
        .where(
            Tenant.status == "active", Tenant.lifecycle != "closed",
            PhotoFolder.tenant_id == tenant_id if tenant_id is not None else True,
            ParentGallery.active.is_(True),
            ParentGallery.lifecycle_status == "active",
            PhotoFolder.status == "released",
            PhotoFolder.purpose == "content",
            PhotoFolder.access_expires_at.is_not(None),
            effective_expiry > archive_warning_start,
            effective_expiry <= archive_warning_end,
            or_(latest_notice_expiry.is_(None), latest_notice_expiry != effective_expiry),
        )
        .order_by(effective_expiry, PhotoFolder.id)
        .limit(limit)
    ))


def _latest_cycle_id(db: Session, folder: PhotoFolder):
    return db.scalar(
        select(MediaArchiveCycle.id)
        .where(
            MediaArchiveCycle.folder_id == folder.id,
            MediaArchiveCycle.tenant_id == folder.tenant_id,
        )
        .order_by(MediaArchiveCycle.cycle_number.desc())
        .limit(1)
    )


def _latest_cycle_for_update(
    db: Session, folder: PhotoFolder, *, cycle_id,
) -> MediaArchiveCycle | None:
    if cycle_id is None:
        return None
    return db.scalar(
        select(MediaArchiveCycle)
        .where(
            MediaArchiveCycle.id == cycle_id,
            MediaArchiveCycle.folder_id == folder.id,
            MediaArchiveCycle.tenant_id == folder.tenant_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _latest_archive_operation_for_update(
    db: Session, *, cycle_id, tenant_id,
) -> MediaArchiveOperation | None:
    if cycle_id is None:
        return None
    return db.scalar(
        select(MediaArchiveOperation)
        .where(
            MediaArchiveOperation.cycle_id == cycle_id,
            MediaArchiveOperation.tenant_id == tenant_id,
            MediaArchiveOperation.operation_type == "archive",
        )
        .order_by(MediaArchiveOperation.created_at.desc(), MediaArchiveOperation.id.desc())
        .limit(1)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _new_cycle(folder: PhotoFolder, *, cycle_number: int, at: datetime) -> MediaArchiveCycle:
    return MediaArchiveCycle(
        id=uuid4(),
        tenant_id=folder.tenant_id,
        parent_gallery_id=folder.parent_gallery_id,
        folder_id=folder.id,
        cycle_number=cycle_number,
        state="local",
        manifest_version=1,
        manifest={},
        object_count=0,
        total_bytes=0,
        created_at=at,
        updated_at=at,
    )


def enqueue_due_archive_window_notices(
    db: Session,
    *,
    at: datetime | None = None,
    limit: int = DEFAULT_DISCOVERY_LIMIT,
    tenant_id: UUID | None = None,
) -> int:
    """Cria no máximo um aviso sete dias antes da elegibilidade efetiva da pasta."""
    if type(limit) is not int or not 1 <= limit <= 10_000:
        raise ValueError("Limite de avisos de arquivo frio inválido.")
    if tenant_id is not None and not isinstance(tenant_id, UUID):
        raise ValueError("Tenant de arquivo frio inválido.")
    instant = _utc(at or now())
    folder_ids = _window_notice_candidate_ids(db, at=instant, limit=limit, tenant_id=tenant_id)
    created = 0

    for folder_id in folder_ids:
        folder = db.get(PhotoFolder, folder_id)
        if folder is None:
            db.rollback()
            continue
        coordinator = db.scalar(
            select(MediaArchiveCoordinator)
            .where(MediaArchiveCoordinator.id == 1)
            .with_for_update()
        )
        if coordinator is None:
            db.rollback()
            raise RuntimeError("Coordenador global de arquivo frio indisponível.")
        candidate_cycle_id = _latest_cycle_id(db, folder)
        previous_archive = _latest_archive_operation_for_update(
            db,
            cycle_id=candidate_cycle_id,
            tenant_id=folder.tenant_id,
        )
        cycle = _latest_cycle_for_update(db, folder, cycle_id=candidate_cycle_id)
        if candidate_cycle_id is not None and cycle is None:
            db.rollback()
            continue
        if cycle is not None and cycle.state != "local":
            db.rollback()
            continue
        if previous_archive is not None and previous_archive.status != "completed":
            db.rollback()
            continue

        locked = lock_archive_scope(db, folder)
        if locked is None:
            db.rollback()
            continue
        folder, _gallery = locked
        tenant_is_active = db.scalar(select(Tenant.status).where(Tenant.id == folder.tenant_id))
        eligible_at = folder_archive_eligible_at(db, folder)
        if (
            tenant_is_active != "active"
            or folder.purpose != "content"
            or folder.status != "released"
            or folder.access_expires_at is None
            or eligible_at is None
        ):
            db.rollback()
            continue
        eligible_at = _utc(eligible_at)
        warning_at = eligible_at - WINDOW_NOTICE_LEAD
        if not warning_at <= instant < eligible_at:
            db.rollback()
            continue
        effective_expiry = eligible_at - REOPENING_WINDOW

        if cycle is None or cycle.archived_at is not None:
            cycle_number = cycle.cycle_number + 1 if cycle is not None else 1
            cycle = _new_cycle(folder, cycle_number=cycle_number, at=instant)
            db.add(cycle)
            db.flush()
        if cycle.last_window_notice_for_expiry is not None and (
            _utc(cycle.last_window_notice_for_expiry) == effective_expiry
        ):
            db.rollback()
            continue

        record_window_notice(
            db,
            tenant_id=folder.tenant_id,
            folder_id=folder.id,
            cycle_id=cycle.id,
            effective_expiry=effective_expiry,
            eligible_at=eligible_at,
            at=instant,
        )
        cycle.last_window_notice_for_expiry = effective_expiry
        cycle.next_archive_check_at = eligible_at
        cycle.updated_at = instant
        db.commit()
        created += 1
    return created


def enqueue_eligible_archive_operations(
    db: Session,
    *,
    at: datetime | None = None,
    limit: int = DEFAULT_DISCOVERY_LIMIT,
    tenant_id: UUID | None = None,
) -> int:
    """Enfileira no máximo ``limit`` operações após revalidar cada pasta sob lock.

    Bloqueios transitórios recebem rechecagem em cinco minutos; uma reabertura
    ainda válida agenda a checagem para o fim exato do prazo. Falhas comprovadas
    de uma operação anterior exigem tratamento explícito e nunca são reenfileiradas.
    A consulta seleciona uma nova janela em toda chamada: cada candidato avaliado
    é enfileirado, recebe um horário futuro ou sai da seleção por seu estado.
    """
    if type(limit) is not int or not 1 <= limit <= 10_000:
        raise ValueError("Limite de descoberta inválido.")
    if tenant_id is not None and not isinstance(tenant_id, UUID):
        raise ValueError("Tenant de arquivo frio inválido.")
    instant = _utc(at or now())
    folder_ids = _candidate_folder_ids(db, at=instant, limit=limit, tenant_id=tenant_id)
    enqueued = 0

    for folder_id in folder_ids:
        folder = db.get(PhotoFolder, folder_id)
        if folder is None:
            db.rollback()
            continue

        # Keep the same lock order as the executor: coordinator, operation,
        # cycle, gallery, then folder. This prevents discovery from holding a
        # folder while an active worker holds the cycle and waits for that folder.
        coordinator = db.scalar(
            select(MediaArchiveCoordinator)
            .where(MediaArchiveCoordinator.id == 1)
            .with_for_update()
        )
        if coordinator is None:
            db.rollback()
            raise RuntimeError("Coordenador global de arquivo frio indisponível.")
        candidate_cycle_id = _latest_cycle_id(db, folder)
        previous_archive = _latest_archive_operation_for_update(
            db,
            cycle_id=candidate_cycle_id,
            tenant_id=folder.tenant_id,
        )
        cycle = _latest_cycle_for_update(db, folder, cycle_id=candidate_cycle_id)
        if candidate_cycle_id is not None and cycle is None:
            db.rollback()
            continue
        if cycle is not None:
            if cycle.state != "local":
                db.rollback()
                continue
            check_at = _utc(cycle.next_archive_check_at) if cycle.next_archive_check_at else None
            if check_at is not None and check_at > instant:
                db.rollback()
                continue
            if previous_archive is not None and previous_archive.status != "completed":
                # Failed/cancelled/reconciliation states need explicit handling.
                # A queued or processing operation also wins the race with a worker.
                db.rollback()
                continue

        locked = lock_archive_scope(db, folder)
        if locked is None:
            db.rollback()
            continue
        folder, _gallery = locked
        tenant_is_active = db.scalar(
            select(Tenant.status).where(Tenant.id == folder.tenant_id)
        )
        if (
            tenant_is_active != "active"
            or (not isolated_closure_cover_folder(db, folder)
                and (folder.purpose != "content"
                     or ((folder.status != "released" or folder.access_expires_at is None)
                         and not never_released_closure_folder(db, folder))))
        ):
            db.rollback()
            continue

        if cycle is None or cycle.archived_at is not None:
            cycle_number = cycle.cycle_number + 1 if cycle is not None else 1
            cycle = _new_cycle(folder, cycle_number=cycle_number, at=instant)
            db.add(cycle)
            db.flush()

        blocker = archive_blocker(db, folder, at=instant)
        if blocker:
            if blocker == "open_order":
                record_open_order_block_notice(
                    db,
                    tenant_id=folder.tenant_id,
                    cycle_id=cycle.id,
                    at=instant,
                )
            if blocker == "not_eligible":
                effective_expiry = folder_archive_eligible_at(db, folder)
                next_check = (
                    _utc(effective_expiry)
                    if effective_expiry is not None and _utc(effective_expiry) > instant
                    else instant + ARCHIVE_RECHECK_DELAY
                )
            else:
                next_check = instant + ARCHIVE_RECHECK_DELAY
            cycle.next_archive_check_at = next_check
            cycle.updated_at = instant
            db.commit()
            continue

        operation = MediaArchiveOperation(
            id=uuid4(),
            tenant_id=folder.tenant_id,
            cycle_id=cycle.id,
            operation_type="archive",
            status="queued",
            idempotency_key=f"archive:{cycle.id}",
            actor_type="system",
            details={"trigger": "automatic_expiry", "automatic_attempt": 1},
            attempts=0,
            created_at=instant,
            updated_at=instant,
        )
        db.add(operation)
        db.flush()
        db.add(MediaArchiveEvent(
            tenant_id=folder.tenant_id,
            cycle_id=cycle.id,
            operation_id=operation.id,
            actor_type="system",
            event_type="archive_queued",
            cycle_state_before="local",
            cycle_state_after="local",
            operation_status_before=None,
            operation_status_after="queued",
            details={"trigger": "automatic_expiry"},
            created_at=instant,
        ))
        cycle.next_archive_check_at = None
        cycle.updated_at = instant
        db.commit()
        enqueued += 1

    return enqueued
