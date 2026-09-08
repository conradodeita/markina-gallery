"""Idempotência, prioridade e retomada da fila facial durável."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import Base, FacialJob, ParentGallery, now
from app.facial.jobs import (
    ClaimedFacialJob,
    FacialJobDispatcher,
    FacialJobError,
    FacialJobRepository,
)


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(ParentGallery(id=uuid4(), name="Evento sintético"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


def _parent_id(db: Session):
    return db.query(ParentGallery.id).scalar()


def test_dispatch_is_idempotent_and_wakes_only_the_facial_queue(db: Session) -> None:
    calls = []

    class Notifier:
        def lpush(self, queue_name: str, value: str):
            calls.append((queue_name, value))

    dispatcher = FacialJobDispatcher(
        FacialJobRepository(),
        queue_name="markina:facial:jobs",
        notifier=Notifier(),
    )
    photo_id = uuid4()
    first, first_created = dispatcher.dispatch(
        db,
        kind="index",
        idempotency_key="index:gallery:photo:model:fingerprint",
        parent_gallery_id=_parent_id(db),
        photo_asset_id=photo_id,
        model_version="model-v1",
        quality_version="quality-v1",
        preview_fingerprint="a" * 64,
    )
    second, second_created = dispatcher.dispatch(
        db,
        kind="index",
        idempotency_key="index:gallery:photo:model:fingerprint",
        parent_gallery_id=_parent_id(db),
        photo_asset_id=photo_id,
        model_version="model-v1",
        quality_version="quality-v1",
        preview_fingerprint="a" * 64,
    )
    assert first.id == second.id
    assert (first_created, second_created) == (True, False)
    assert calls == [("markina:facial:jobs:index", str(first.id))]
    assert all("media" not in queue for queue, _ in calls)


def test_claim_respects_priority_and_does_not_double_claim(db: Session) -> None:
    repository = FacialJobRepository()
    parent_id = _parent_id(db)
    for key, priority in (("normal", 100), ("purge", 10)):
        repository.enqueue(
            db,
            kind="cleanup",
            idempotency_key=key,
            parent_gallery_id=parent_id,
            priority=priority,
        )
    db.commit()

    first = repository.claim_next(db, lease_seconds=60)
    second = repository.claim_next(db, lease_seconds=60)

    assert first is not None and second is not None and first.id != second.id
    assert db.get(FacialJob, first.id).idempotency_key == "purge"
    assert repository.claim_next(db, lease_seconds=60) is None


def test_worker_classes_claim_only_their_jobs_and_maintenance_is_not_starved(
    db: Session,
) -> None:
    repository = FacialJobRepository()
    parent_id = _parent_id(db)
    index, _ = repository.enqueue(
        db,
        kind="index",
        idempotency_key="class-index",
        parent_gallery_id=parent_id,
        photo_asset_id=uuid4(),
        model_version="model-v1",
        quality_version="quality-v1",
        preview_fingerprint="a" * 64,
    )
    search, _ = repository.enqueue(
        db,
        kind="search",
        idempotency_key="class-search",
        parent_gallery_id=parent_id,
        search_request_id=uuid4(),
    )
    cleanup, _ = repository.enqueue(
        db,
        kind="cleanup",
        idempotency_key="class-cleanup",
        parent_gallery_id=parent_id,
        priority=20,
    )
    purge, _ = repository.enqueue(
        db,
        kind="purge",
        idempotency_key="class-purge",
        parent_gallery_id=parent_id,
        priority=0,
    )
    db.commit()

    search_claim = repository.claim_next(
        db, lease_seconds=60, job_class="search"
    )
    index_claim = repository.claim_next(
        db, lease_seconds=60, job_class="index"
    )
    first_maintenance = repository.claim_next(
        db, lease_seconds=60, job_class="maintenance"
    )
    second_maintenance = repository.claim_next(
        db, lease_seconds=60, job_class="maintenance"
    )

    assert search_claim is not None and search_claim.id == search.id
    assert index_claim is not None and index_claim.id == index.id
    assert first_maintenance is not None and first_maintenance.id == purge.id
    assert second_maintenance is not None and second_maintenance.id == cleanup.id
    assert repository.claim_next(
        db, lease_seconds=60, job_class="maintenance"
    ) is None
    with pytest.raises(FacialJobError, match="Classe"):
        repository.claim_next(db, lease_seconds=60, job_class="unknown")


def test_expired_lease_is_resumed_and_stale_worker_cannot_finish(db: Session) -> None:
    repository = FacialJobRepository()
    job, _ = repository.enqueue(
        db,
        kind="cleanup",
        idempotency_key="crash-resume",
        parent_gallery_id=_parent_id(db),
    )
    db.commit()
    first = repository.claim_next(
        db, lease_seconds=60, job_class="maintenance"
    )
    assert first is not None
    job = db.get(FacialJob, job.id)
    job.lease_expires_at = now() - timedelta(seconds=1)
    db.commit()

    resumed = repository.claim_next(
        db, lease_seconds=60, job_class="maintenance"
    )

    assert resumed is not None and resumed.id == first.id
    assert resumed.lease_token != first.lease_token
    assert db.get(FacialJob, resumed.id).attempts == 2
    with pytest.raises(FacialJobError, match="Lease"):
        repository.complete(db, first)
    repository.complete(db, resumed)
    assert db.get(FacialJob, resumed.id).status == "completed"


def test_failure_is_sanitized_and_retried_until_terminal(db: Session) -> None:
    repository = FacialJobRepository()
    _job, _ = repository.enqueue(
        db,
        kind="cleanup",
        idempotency_key="retry-safe",
        parent_gallery_id=_parent_id(db),
    )
    db.commit()
    first = repository.claim_next(db, lease_seconds=60)
    assert first is not None
    failed = repository.fail(
        db,
        first,
        RuntimeError("secret=/tmp/private/customer.jpg"),
        max_attempts=2,
        retry_delay_seconds=0,
    )
    assert failed.status == "queued"
    assert failed.last_error_category == "internal_failure"
    assert "secret" not in failed.last_error_category

    second = repository.claim_next(db, lease_seconds=60)
    assert second is not None
    terminal = repository.fail(
        db,
        second,
        RuntimeError("another secret"),
        max_attempts=2,
        retry_delay_seconds=0,
    )
    assert terminal.status == "failed"


def test_progress_and_completion_require_the_current_lease(db: Session) -> None:
    repository = FacialJobRepository()
    job, _ = repository.enqueue(
        db,
        kind="cleanup",
        idempotency_key="progress",
        parent_gallery_id=_parent_id(db),
    )
    db.commit()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None
    progressed = repository.progress(
        db, claim, done=2, total=5, lease_seconds=60
    )
    assert (progressed.progress_done, progressed.progress_total) == (2, 5)
    with pytest.raises(FacialJobError, match="Progresso"):
        repository.progress(db, claim, done=6, total=5, lease_seconds=60)
    with pytest.raises(FacialJobError, match="Lease"):
        repository.complete(
            db, ClaimedFacialJob(id=job.id, lease_token="worker-incorreto")
        )
