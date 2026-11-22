"""Avisos do arquivo frio são idempotentes, internos e tenant-scoped."""

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    MediaArchiveCycle,
    MediaArchiveNotice,
    MediaArchiveOperation,
    NotificationDelivery,
    NotificationEvent,
    ParentGallery,
    PhotoFolder,
    Tenant,
)
from app.media_archive_worker import _append_event

_AT = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.


def _engine():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def test_transfer_event_outbox_is_idempotent_and_has_no_external_delivery():
    engine = _engine()
    with Session(engine, expire_on_commit=False) as db:
        tenant = Tenant()
        db.add(tenant)
        db.flush()
        gallery = ParentGallery(tenant_id=tenant.id, name="Galeria sintética")
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(
            tenant_id=tenant.id,
            parent_gallery_id=gallery.id,
            name="Pasta sintética",
            position=0,
            purpose="content",
            status="released",
        )
        db.add(folder)
        db.flush()

        event_mapping = (
            ("archive", "archive_started", "archive_started"),
            ("archive", "archive_completed", "archive_completed"),
            ("archive", "operation_failed", "archive_failed"),
            ("archive", "reconciliation_required", "archive_reconciliation_required"),
            ("restore", "recovery_started", "recovery_started"),
            ("restore", "recovery_completed", "recovery_completed"),
            ("restore", "operation_failed", "recovery_failed"),
            ("restore", "reconciliation_required", "recovery_reconciliation_required"),
        )
        operations = []
        for index, (operation_type, _event_type, _notice_type) in enumerate(event_mapping, start=1):
            cycle = MediaArchiveCycle(
                tenant_id=tenant.id,
                parent_gallery_id=gallery.id,
                folder_id=folder.id,
                cycle_number=index,
                state="local",
            )
            db.add(cycle)
            db.flush()
            operation = MediaArchiveOperation(
                tenant_id=tenant.id,
                cycle_id=cycle.id,
                operation_type=operation_type,
                status="queued",
                idempotency_key=f"synthetic-operation-{index}",
                actor_type="system",
                created_at=_AT,
                updated_at=_AT,
            )
            db.add(operation)
            db.flush()
            operations.append(operation)

        for operation, (_kind, event_type, _notice_type) in zip(operations, event_mapping, strict=True):
            _append_event(db, operation=operation, event_type=event_type, at=_AT)
        _append_event(db, operation=operations[0], event_type="archive_started", at=_AT)
        db.commit()

        notices = list(db.scalars(select(MediaArchiveNotice).where(
            MediaArchiveNotice.tenant_id == tenant.id,
        )))
        assert {notice.notice_type for notice in notices} == {
            notice_type for _kind, _event_type, notice_type in event_mapping
        }
        assert len(notices) == len(event_mapping)
        assert db.scalar(select(func.count()).select_from(NotificationEvent)) == 0
        assert db.scalar(select(func.count()).select_from(NotificationDelivery)) == 0

    engine.dispose()
