"""Fila global e checkpoints do worker de arquivo frio."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveEvent,
    MediaArchiveOperation,
    ParentGallery,
    PhotoFolder,
    Tenant,
)
from app.folder_access import folder_media_is_local
from app.media_archive_worker import (
    MediaArchiveTransitionError,
    begin_archive_cleanup,
    checkpoint_operation,
    claim_next_operation,
    complete_archive_operation,
    fail_operation,
)
from tests.test_photographer_onboarding_migration import _config, _demo_helpers
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema

_AT = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def _engine_with_runtime_schema():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def _seed(engine, operations):
    tenant_id, parent_id = uuid4(), uuid4()
    rows = []
    with Session(engine, expire_on_commit=False) as db:
        db.add(Tenant(id=tenant_id))
        db.flush()
        db.add(ParentGallery(
            id=parent_id, tenant_id=tenant_id, name="Galeria sintética",
        ))
        db.flush()
        for index, item in enumerate(operations):
            folder_id, cycle_id, operation_id = uuid4(), uuid4(), uuid4()
            db.add(PhotoFolder(
                id=folder_id, tenant_id=tenant_id, parent_gallery_id=parent_id,
                name=f"Pasta {index + 1}", position=index + 1,
                purpose="content", status="released",
                released_at=_AT - timedelta(days=60), access_duration_days=30,
                access_expires_at=_AT - timedelta(days=31),
            ))
            rows.append((folder_id, cycle_id, operation_id, item, index))
        db.flush()
        if db.get(MediaArchiveCoordinator, 1) is None:
            db.add(MediaArchiveCoordinator(id=1))
        for folder_id, cycle_id, operation_id, item, _index in rows:
            operation_type = item["type"]
            db.add(MediaArchiveCycle(
                id=cycle_id,
                tenant_id=tenant_id,
                parent_gallery_id=parent_id,
                folder_id=folder_id,
                cycle_number=1,
                state=("archiving" if operation_type == "archive" else
                       "deleting" if operation_type == "delete_remote" else "restoring"),
            ))
            db.add(MediaArchiveOperation(
                id=operation_id,
                tenant_id=tenant_id,
                cycle_id=cycle_id,
                operation_type=operation_type,
                status=item.get("status", "queued"),
                stage=item.get("stage"),
                idempotency_key=f"worker-test-{operation_id}",
                actor_type="system",
                attempts=item.get("attempts", 0),
                created_at=item["created_at"],
                lease_token=item.get("lease_token"),
                lease_expires_at=item.get("lease_expires_at"),
            ))
        db.commit()
    return tenant_id, rows


def test_claim_prefers_oldest_restore_then_fifo_and_holds_global_lease():
    engine = _engine_with_runtime_schema()
    _tenant, rows = _seed(engine, [
        {"type": "archive", "created_at": _AT - timedelta(minutes=10)},
        {"type": "restore", "created_at": _AT - timedelta(minutes=5)},
        {"type": "restore", "created_at": _AT - timedelta(minutes=2)},
    ])
    expected_id = rows[1][2]
    with Session(engine, expire_on_commit=False) as db:
        claim = claim_next_operation(db, at=_AT)
        assert claim and claim.operation_id == expected_id
        assert claim_next_operation(db, at=_AT + timedelta(seconds=1)) is None
    engine.dispose()


def test_claim_prioritizes_restore_then_cold_media_deletion_then_archive():
    restore_engine = _engine_with_runtime_schema()
    _tenant, rows = _seed(restore_engine, [
        {"type": "archive", "created_at": _AT - timedelta(minutes=10)},
        {"type": "delete_remote", "created_at": _AT - timedelta(minutes=5)},
        {"type": "restore", "created_at": _AT - timedelta(minutes=1)},
    ])
    with Session(restore_engine, expire_on_commit=False) as db:
        claim = claim_next_operation(db, at=_AT)
        assert claim and claim.operation_id == rows[2][2]
    restore_engine.dispose()

    deletion_engine = _engine_with_runtime_schema()
    _tenant, rows = _seed(deletion_engine, [
        {"type": "archive", "created_at": _AT - timedelta(minutes=10)},
        {"type": "delete_remote", "created_at": _AT - timedelta(minutes=5)},
    ])
    with Session(deletion_engine, expire_on_commit=False) as db:
        claim = claim_next_operation(db, at=_AT)
        assert claim and claim.operation_id == rows[1][2]
    deletion_engine.dispose()


def test_expired_global_lease_reclaims_same_operation_with_new_token():
    engine = _engine_with_runtime_schema()
    _tenant, rows = _seed(engine, [
        {"type": "archive", "created_at": _AT - timedelta(minutes=1)},
    ])
    operation_id = rows[0][2]
    with Session(engine, expire_on_commit=False) as db:
        first = claim_next_operation(db, at=_AT)
        assert first and first.operation_id == operation_id
    with Session(engine, expire_on_commit=False) as db:
        operation = db.get(MediaArchiveOperation, operation_id)
        coordinator = db.get(MediaArchiveCoordinator, 1)
        operation.lease_expires_at = _AT - timedelta(seconds=1)
        coordinator.lease_expires_at = _AT - timedelta(seconds=1)
        db.commit()
    with Session(engine, expire_on_commit=False) as db:
        reclaimed = claim_next_operation(db, at=_AT + timedelta(seconds=1))
        assert reclaimed and reclaimed.operation_id == operation_id
        assert reclaimed.lease_token != first.lease_token
        assert db.get(MediaArchiveOperation, operation_id).attempts == 2
        assert db.scalar(sa.select(sa.func.count()).select_from(MediaArchiveEvent)) == 2
    engine.dispose()


@pytest.mark.parametrize("operation_type", ["archive", "restore", "delete_remote"])
def test_suspension_preserves_queued_operation_until_reactivation(operation_type):
    engine = _engine_with_runtime_schema()
    tenant_id, rows = _seed(engine, [{"type": operation_type, "created_at": _AT}])
    operation_id = rows[0][2]
    with Session(engine, expire_on_commit=False) as db:
        db.get(Tenant, tenant_id).status = "suspended"
        db.commit()
        assert claim_next_operation(db, at=_AT) is None
        operation = db.get(MediaArchiveOperation, operation_id)
        assert (operation.status, operation.attempts, operation.lease_token) == ("queued", 0, None)
        assert db.scalar(sa.select(sa.func.count()).select_from(MediaArchiveEvent)) == 0
        db.get(Tenant, tenant_id).status = "active"
        db.commit()
        claim = claim_next_operation(db, at=_AT)
        assert claim and claim.operation_id == operation_id
    engine.dispose()


def test_suspended_restore_does_not_block_queued_archive_for_another_tenant():
    engine = _engine_with_runtime_schema()
    suspended_id, paused_rows = _seed(engine, [{"type": "restore", "created_at": _AT}])
    active_id, active_rows = _seed(engine, [{
        "type": "archive", "created_at": _AT + timedelta(seconds=1),
    }])
    with Session(engine, expire_on_commit=False) as db:
        db.get(Tenant, suspended_id).status = "suspended"
        db.commit()
        claim = claim_next_operation(db, at=_AT + timedelta(seconds=2))
        assert claim and claim.tenant_id == active_id
        assert claim.operation_id == active_rows[0][2]
        paused = db.get(MediaArchiveOperation, paused_rows[0][2])
        assert (paused.status, paused.attempts, paused.lease_token) == ("queued", 0, None)
    engine.dispose()


def test_suspension_preserves_expired_global_lease_until_reactivation():
    engine = _engine_with_runtime_schema()
    tenant_id, rows = _seed(engine, [{"type": "archive", "created_at": _AT}])
    operation_id = rows[0][2]
    with Session(engine, expire_on_commit=False) as db:
        first = claim_next_operation(db, at=_AT, lease_seconds=1)
        assert first
        operation = db.get(MediaArchiveOperation, operation_id)
        operation.stage = "uploading"
        db.get(Tenant, tenant_id).status = "suspended"
        db.commit()
        assert claim_next_operation(db, at=_AT + timedelta(seconds=2)) is None
        db.refresh(operation)
        assert (operation.attempts, operation.stage, operation.lease_token) == (
            1, "uploading", first.lease_token,
        )
        assert db.get(MediaArchiveCoordinator, 1).active_operation_id == operation_id
        db.get(Tenant, tenant_id).status = "active"
        db.commit()
        resumed = claim_next_operation(db, at=_AT + timedelta(seconds=3))
        assert resumed and resumed.operation_id == operation_id
        assert resumed.lease_token != first.lease_token
        db.refresh(operation)
        assert (operation.attempts, operation.stage) == (2, "uploading")
    engine.dispose()


def test_unknown_remote_result_enters_reconciliation_and_is_not_reclaimed():
    engine = _engine_with_runtime_schema()
    _tenant, rows = _seed(engine, [
        {"type": "archive", "created_at": _AT - timedelta(minutes=1)},
    ])
    operation_id, cycle_id = rows[0][2], rows[0][1]
    with Session(engine, expire_on_commit=False) as db:
        claim = claim_next_operation(db, at=_AT)
        assert claim
        fail_operation(
            db,
            operation_id=operation_id,
            lease_token=claim.lease_token,
            outcome="unknown",
            error_code="remote_result_unknown",
            at=_AT + timedelta(seconds=1),
        )
    with Session(engine, expire_on_commit=False) as db:
        assert db.get(MediaArchiveOperation, operation_id).status == "reconciliation_required"
        assert db.get(MediaArchiveCycle, cycle_id).state == "reconciliation_required"
        assert claim_next_operation(db, at=_AT + timedelta(seconds=2)) is None
    engine.dispose()


def test_archive_completion_requires_verified_readback_and_local_cleanup():
    engine = _engine_with_runtime_schema()
    _tenant, rows = _seed(engine, [
        {"type": "archive", "created_at": _AT - timedelta(minutes=1)},
    ])
    operation_id, cycle_id = rows[0][2], rows[0][1]
    with Session(engine, expire_on_commit=False) as db:
        claim = claim_next_operation(db, at=_AT)
        assert claim
        with pytest.raises(MediaArchiveTransitionError):
            complete_archive_operation(
                db, operation_id=operation_id, lease_token=claim.lease_token,
                at=_AT + timedelta(seconds=1),
            )
        for offset, stage in enumerate((
            "snapshot", "uploading", "reading_back", "manifest_upload",
            "manifest_readback",
        ), start=1):
            details = {
                "readback_verified": True,
                "manifest_readback_verified": True,
                "verified_object_count": 0,
            } if stage == "manifest_readback" else None
            checkpoint_operation(
                db,
                operation_id=operation_id,
                lease_token=claim.lease_token,
                stage=stage,
                details_patch=details,
                at=_AT + timedelta(seconds=offset),
            )
        folder = db.get(PhotoFolder, rows[0][0])
        assert folder_media_is_local(db, folder)
        begin_archive_cleanup(
            db, operation_id=operation_id, lease_token=claim.lease_token,
            at=_AT + timedelta(seconds=8),
        )
        assert not folder_media_is_local(db, folder)
        operation = db.get(MediaArchiveOperation, operation_id)
        operation.details = {
            **operation.details,
            "local_cleanup_complete": True,
        }
        db.commit()
        complete_archive_operation(
            db, operation_id=operation_id, lease_token=claim.lease_token,
            at=_AT + timedelta(seconds=10),
        )
        assert db.get(MediaArchiveOperation, operation_id).status == "completed"
        assert db.get(MediaArchiveCycle, cycle_id).state == "archived"
        assert db.get(MediaArchiveCoordinator, 1).active_operation_id is None
    engine.dispose()


def test_postgres_two_workers_cannot_claim_two_transfers(postgres_schema, monkeypatch):
    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, scoped_url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(scoped_url)
    command.upgrade(config, "head")
    tenant_id, parent_id, folder_id = uuid4(), uuid4(), uuid4()
    cycle_id, operation_id = uuid4(), uuid4()
    with Session(engine, expire_on_commit=False) as db:
        db.add(Tenant(id=tenant_id))
        db.flush()
        db.add(ParentGallery(id=parent_id, tenant_id=tenant_id, name="Synthetic concurrency"))
        db.flush()
        db.add(PhotoFolder(id=folder_id, tenant_id=tenant_id,
                           parent_gallery_id=parent_id, name="Synthetic folder"))
        db.flush()
        db.add_all([
            MediaArchiveCycle(
                id=cycle_id, tenant_id=tenant_id, parent_gallery_id=parent_id,
                folder_id=folder_id, state="archiving",
            ),
            MediaArchiveOperation(
                id=operation_id, tenant_id=tenant_id, cycle_id=cycle_id,
                operation_type="archive", status="queued",
                idempotency_key="postgres-worker-concurrency",
                actor_type="system", created_at=_AT,
            ),
        ])
        db.commit()

    with Session(engine, expire_on_commit=False) as suspending_db:
        tenant = suspending_db.scalar(sa.select(Tenant).where(
            Tenant.id == tenant_id,
        ).with_for_update())
        tenant.status = "suspended"
        suspending_db.flush()
        with Session(engine) as claiming_db:
            assert claim_next_operation(claiming_db, at=_AT) is None
        suspending_db.commit()
    with Session(engine) as db:
        assert claim_next_operation(db, at=_AT) is None
        db.get(Tenant, tenant_id).status = "active"
        db.commit()

    barrier = Barrier(2)

    def claim_in_independent_session():
        with Session(engine, expire_on_commit=False) as db:
            barrier.wait(timeout=5)
            return claim_next_operation(db, at=_AT)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: claim_in_independent_session(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert {result.operation_id for result in results if result} == {operation_id}

    original_claim = next(result for result in results if result)
    with Session(engine, expire_on_commit=False) as db:
        db.get(Tenant, tenant_id).status = "suspended"
        db.commit()
        assert claim_next_operation(db, at=_AT + timedelta(seconds=121)) is None
        assert db.get(MediaArchiveOperation, operation_id).lease_token == original_claim.lease_token
        db.get(Tenant, tenant_id).status = "active"
        db.commit()
        resumed = claim_next_operation(db, at=_AT + timedelta(seconds=122))
        assert resumed and resumed.operation_id == operation_id
        assert resumed.lease_token != original_claim.lease_token


@pytest.fixture(params=["sqlite", "postgresql"])
def scoped_claim_engine(request):
    if request.param == "sqlite":
        engine = _engine_with_runtime_schema()
        try:
            yield engine
        finally:
            engine.dispose()
    else:
        from tests.schema_fixtures import create_test_schema
        engine = request.getfixturevalue("postgres_schema")
        create_test_schema(engine)
        yield engine


@pytest.mark.parametrize("expired", [False, True])
def test_scoped_claim_preserves_other_tenant_global_lease(expired, scoped_claim_engine):
    engine = scoped_claim_engine
    other, rows = _seed(engine, [{"type": "archive", "created_at": _AT}])
    owner, _ = _seed(engine, [{"type": "restore", "created_at": _AT}])
    with Session(engine, expire_on_commit=False) as db:
        claim = claim_next_operation(db, tenant_id=other, at=_AT, lease_seconds=1)
        assert claim and claim.operation_id == rows[0][2]
        at = _AT + timedelta(seconds=2 if expired else 0)
        assert claim_next_operation(db, tenant_id=owner, at=at) is None
        db.expire_all()
        operation = db.get(MediaArchiveOperation, claim.operation_id)
        coordinator = db.get(MediaArchiveCoordinator, 1)
        assert operation.lease_token == claim.lease_token
        assert operation.attempts == 1
        assert coordinator.active_operation_id == claim.operation_id
        assert coordinator.lease_token == claim.lease_token
    engine.dispose()


def test_scoped_claim_selects_only_requested_tenant_and_resumes_own_lease(scoped_claim_engine):
    engine = scoped_claim_engine
    _other, other_rows = _seed(engine, [{"type": "restore", "created_at": _AT}])
    owner, owner_rows = _seed(engine, [{"type": "archive", "created_at": _AT}])
    with Session(engine, expire_on_commit=False) as db:
        claim = claim_next_operation(db, tenant_id=owner, at=_AT, lease_seconds=1)
        assert claim and claim.operation_id == owner_rows[0][2]
        assert db.get(MediaArchiveOperation, other_rows[0][2]).status == "queued"
        resumed = claim_next_operation(db, tenant_id=owner, at=_AT + timedelta(seconds=2))
        assert resumed and resumed.operation_id == claim.operation_id
        assert resumed.lease_token != claim.lease_token
        assert db.get(MediaArchiveOperation, other_rows[0][2]).attempts == 0
    engine.dispose()


def test_postgres_scoped_workers_preserve_single_global_lease(postgres_schema):
    from tests.schema_fixtures import create_test_schema
    create_test_schema(postgres_schema)
    owner, owner_rows = _seed(postgres_schema, [{"type": "archive", "created_at": _AT}])
    other, other_rows = _seed(postgres_schema, [{"type": "restore", "created_at": _AT}])
    barrier = Barrier(2)
    def scoped_claim():
        with Session(postgres_schema, expire_on_commit=False) as db:
            barrier.wait(timeout=10)
            return claim_next_operation(db, tenant_id=owner, at=_AT)
    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(lambda _: scoped_claim(), range(2)))
    assert sum(claim is not None for claim in claims) == 1
    assert {claim.operation_id for claim in claims if claim} == {owner_rows[0][2]}
    with Session(postgres_schema) as db:
        assert claim_next_operation(db, tenant_id=other, at=_AT + timedelta(seconds=121)) is None
        operation = db.get(MediaArchiveOperation, other_rows[0][2])
        assert operation.status == "queued" and operation.attempts == 0
        assert db.get(MediaArchiveCoordinator, 1).active_operation_id == owner_rows[0][2]
