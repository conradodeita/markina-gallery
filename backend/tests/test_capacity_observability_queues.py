from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    FacialJob,
    MediaJob,
    ParentGallery,
    PhotoAnalysis,
    PhotoAsset,
    PhotoFolder,
    PreviewAdjustment,
    Tenant,
)
from app.capacity_observability.contracts import Evidence, UnavailableReason
from app.capacity_observability.queues import collect_all_queues

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    @event.listens_for(engine, "connect")
    def enable_fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return Session(engine)


def _gallery(db: Session) -> tuple[Tenant, ParentGallery]:
    tenant = Tenant(id=uuid4(), status="active")
    gallery = ParentGallery(id=uuid4(), tenant_id=tenant.id, name="Registro sintético")
    db.add(tenant)
    db.flush()
    db.add(gallery)
    db.flush()
    return tenant, gallery


def _photo(db: Session, tenant: Tenant, gallery: ParentGallery, *, position: int) -> PhotoAsset:
    folder = PhotoFolder(tenant_id=tenant.id,
        id=uuid4(), parent_gallery_id=gallery.id, name=f"Pasta sintética {position}", position=position
    )
    photo = PhotoAsset(
        id=uuid4(), tenant_id=tenant.id, parent_gallery_id=gallery.id, folder_id=folder.id,
        filename=f"synthetic-{position}.jpg", storage_key=f"synthetic/{position}.jpg",
    )
    db.add(folder)
    db.flush()
    db.add(photo)
    db.flush()
    return photo


def _facial_job(
    gallery: ParentGallery, *, kind: str, status: str, suffix: str,
    available: datetime, created: datetime, lease: datetime | None = None,
) -> FacialJob:
    return FacialJob(tenant_id=gallery.tenant_id,
        id=uuid4(), kind=kind, status=status, idempotency_key=f"synthetic-{suffix}",
        priority=10, parent_gallery_id=gallery.id, available_at=available, created_at=created,
        updated_at=created, lease_expires_at=lease,
    )


def test_queues_separate_due_scheduled_processing_and_expired_lease() -> None:
    db = _db()
    try:
        _, gallery = _gallery(db)
        old = NOW - timedelta(seconds=120)
        due = _facial_job(gallery, kind="search", status="queued", suffix="search-due",
                          available=NOW - timedelta(seconds=30), created=old)
        scheduled = _facial_job(gallery, kind="search", status="queued", suffix="search-future",
                                available=NOW + timedelta(minutes=5), created=old)
        stale = _facial_job(gallery, kind="search", status="processing", suffix="search-stale",
                            available=NOW - timedelta(seconds=30), created=old,
                            lease=NOW - timedelta(seconds=5))
        live = _facial_job(gallery, kind="search", status="processing", suffix="search-live",
                           available=NOW - timedelta(seconds=30), created=old,
                           lease=NOW + timedelta(minutes=1))
        terminal = _facial_job(gallery, kind="search", status="completed", suffix="search-done",
                               available=NOW - timedelta(seconds=30), created=old)
        db.add_all((due, scheduled, stale, live, terminal))
        db.commit()

        queues = {item.queue_class: item for item in collect_all_queues(db, instant=NOW)}
        search = queues["search"]
        assert search.queued_total.value == 2
        assert search.scheduled_total.value == 1
        assert search.claim_candidates_total.value == 1
        assert search.processing_total.value == 2
        assert search.reclaimable_total.value == 1
        assert search.oldest_record_age_seconds.value == 120
        assert search.oldest_due_age_seconds.value == 30
        assert search.wait_semantics == "available_at_age_estimate"
        assert queues["index"].queued_total.value == 0
        assert queues["maintenance"].queued_total.value == 0
    finally:
        db.close()


def test_media_counts_blocked_dependency_without_counting_processing_or_terminal() -> None:
    db = _db()
    try:
        tenant, gallery = _gallery(db)
        blocked_photo = _photo(db, tenant, gallery, position=0)
        ready_photo = _photo(db, tenant, gallery, position=1)
        processing_photo = _photo(db, tenant, gallery, position=2)
        missing_photo = _photo(db, tenant, gallery, position=3)
        old = NOW - timedelta(seconds=180)
        db.add_all((
            PhotoAnalysis(tenant_id=tenant.id, photo_asset_id=blocked_photo.id, source_fingerprint="a" * 64,
                         source_bytes=1, width=1, height=1, expires_at=NOW + timedelta(hours=1),
                         state="pending"),
            PhotoAnalysis(tenant_id=tenant.id, photo_asset_id=ready_photo.id, source_fingerprint="b" * 64,
                         source_bytes=1, width=1, height=1, expires_at=NOW + timedelta(hours=1),
                         state="ready"),
            MediaJob(tenant_id=tenant.id, photo_asset_id=blocked_photo.id, status="queued", attempts=1, created_at=old),
            MediaJob(tenant_id=tenant.id, photo_asset_id=ready_photo.id, status="queued", attempts=2, created_at=old),
            MediaJob(tenant_id=tenant.id, photo_asset_id=processing_photo.id, status="processing", attempts=1,
                     created_at=old),
            MediaJob(tenant_id=tenant.id, photo_asset_id=missing_photo.id, status="failed", attempts=3, created_at=old),
        ))
        db.commit()

        media = {item.queue_class: item for item in collect_all_queues(db, instant=NOW)}["media"]
        assert media.queued_total.value == 2
        assert media.blocked_dependency_total.value == 1
        assert media.claim_candidates_total.value == 1
        assert media.processing_total.value == 1
        assert media.oldest_record_age_seconds.value == 180
        assert media.oldest_record_age_seconds.evidence is Evidence.CALCULATED
    finally:
        db.close()


def test_adjustment_uses_update_age_and_keeps_exact_eligibility_unavailable() -> None:
    db = _db()
    try:
        tenant, gallery = _gallery(db)
        queued_photo = _photo(db, tenant, gallery, position=0)
        processing_photo = _photo(db, tenant, gallery, position=1)
        failed_photo = _photo(db, tenant, gallery, position=2)
        db.add_all((
            PreviewAdjustment(tenant_id=tenant.id, photo_asset_id=queued_photo.id, generation=1,
                              fingerprint="a" * 64, status="queued", updated_at=NOW - timedelta(seconds=45)),
            PreviewAdjustment(tenant_id=tenant.id, photo_asset_id=processing_photo.id, generation=1,
                              fingerprint="b" * 64, status="processing", updated_at=NOW - timedelta(minutes=2)),
            PreviewAdjustment(tenant_id=tenant.id, photo_asset_id=failed_photo.id, generation=1,
                              fingerprint="c" * 64, status="failed", updated_at=NOW - timedelta(minutes=3)),
        ))
        db.commit()

        adjustment = {
            item.queue_class: item for item in collect_all_queues(db, instant=NOW)
        }["preview_adjustment"]
        assert adjustment.queued_total.value == 1
        assert adjustment.processing_total.value == 1
        assert adjustment.claim_candidates_total.value is None
        assert adjustment.claim_candidates_total.reason is UnavailableReason.FIELD_UNAVAILABLE
        assert adjustment.oldest_updated_age_seconds.value == 45
        assert adjustment.oldest_updated_age_seconds.evidence is Evidence.ESTIMATED
        assert adjustment.oldest_record_age_seconds.reason is UnavailableReason.EMPTY_QUEUE
    finally:
        db.close()


def test_no_queue_age_is_zero_count_with_empty_queue_age_unavailable() -> None:
    db = _db()
    try:
        queues = collect_all_queues(db, instant=NOW)
        assert len(queues) == 5
        assert all(queue.queued_total.value == 0 for queue in queues)
        assert all(queue.oldest_due_age_seconds.reason is UnavailableReason.EMPTY_QUEUE
                   for queue in queues)
    finally:
        db.close()


def test_future_record_timestamp_never_becomes_negative_wait() -> None:
    db = _db()
    try:
        _, gallery = _gallery(db)
        db.add(_facial_job(gallery, kind="index", status="queued", suffix="future-created",
                           available=NOW - timedelta(seconds=1), created=NOW + timedelta(seconds=1)))
        db.commit()
        index = {queue.queue_class: queue for queue in collect_all_queues(db, instant=NOW)}["index"]
        assert index.queued_total.value == 1
        assert index.oldest_record_age_seconds.reason is UnavailableReason.INCONSISTENT_TIMESTAMP
        assert index.oldest_due_age_seconds.value == 1
    finally:
        db.close()
