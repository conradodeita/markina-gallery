"""Descoberta idempotente de pastas para o arquivo frio."""

import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app import media_archive_scheduler as scheduler
from app.auth import (
    Base,
    Client,
    GalleryClientState,
    GalleryReopeningRequest,
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveEvent,
    MediaArchiveNotice,
    MediaArchiveOperation,
    ParentGallery,
    PhotoFolder,
    SaleOrder,
    SaleOrderItem,
    Tenant,
)

_AT = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)  # noqa: UP017 -- Keep Python 3.10 test compatibility.


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value  # noqa: UP017 -- Keep Python 3.10 test compatibility.


def _engine_with_schema():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(MediaArchiveCoordinator(id=1))
        db.commit()
    return engine


def _seed_folder(
    db: Session,
    *,
    name: str = "Pasta vencida",
    expires_at: datetime | None = None,
    audience_scope: str | None = None,
) -> PhotoFolder:
    tenant = Tenant()
    db.add(tenant)
    db.flush()
    gallery = ParentGallery(tenant_id=tenant.id, name="Galeria sintética")
    db.add(gallery)
    db.flush()
    folder = PhotoFolder(
        tenant_id=tenant.id,
        parent_gallery_id=gallery.id,
        name=name,
        position=0,
        purpose="content",
        status="released",
        audience_scope=audience_scope,
        released_at=_AT - timedelta(days=90),
        access_duration_days=30,
        access_expires_at=expires_at or _AT - timedelta(days=60),
    )
    db.add(folder)
    db.flush()
    return folder


def test_due_folder_is_enqueued_once_and_repeat_scan_is_idempotent():
    engine = _engine_with_schema()
    with Session(engine, expire_on_commit=False) as db:
        folder = _seed_folder(db)
        folder_id, tenant_id = folder.id, folder.tenant_id
        assert scheduler.enqueue_eligible_archive_operations(db, at=_AT) == 1
        assert scheduler.enqueue_eligible_archive_operations(db, at=_AT + timedelta(seconds=1)) == 0

        cycles = list(db.scalars(select(MediaArchiveCycle).where(
            MediaArchiveCycle.tenant_id == tenant_id,
            MediaArchiveCycle.folder_id == folder_id,
        )))
        operations = list(db.scalars(select(MediaArchiveOperation).where(
            MediaArchiveOperation.tenant_id == tenant_id,
            MediaArchiveOperation.operation_type == "archive",
        )))
        events = list(db.scalars(select(MediaArchiveEvent).where(
            MediaArchiveEvent.tenant_id == tenant_id,
        )))
        assert len(cycles) == len(operations) == len(events) == 1
        assert cycles[0].cycle_number == 1
        assert operations[0].status == "queued"
        assert operations[0].stage is None
        assert operations[0].idempotency_key == f"archive:{cycles[0].id}"
        assert operations[0].details == {
            "trigger": "automatic_expiry",
            "automatic_attempt": 1,
        }
    engine.dispose()


def test_editable_checkout_draft_blocks_archive_discovery():
    engine = _engine_with_schema()
    with Session(engine, expire_on_commit=False) as db:
        folder = _seed_folder(db, expires_at=_AT - timedelta(days=60))
        client = Client(
            tenant_id=folder.tenant_id,
            full_name="Cliente com rascunho",
            phone_e164="+5511999990013",
        )
        db.add(client)
        db.flush()
        db.add(GalleryClientState(
            tenant_id=folder.tenant_id,
            parent_gallery_id=folder.parent_gallery_id,
            client_id=client.id,
        ))
        db.flush()
        order = SaleOrder(
            tenant_id=folder.tenant_id,
            parent_gallery_id=folder.parent_gallery_id,
            client_id=client.id,
            parent_gallery_id_snapshot=folder.parent_gallery_id,
            parent_gallery_name_snapshot="Galeria sintética",
            derived_gallery_name_snapshot="Galeria principal",
            payment_status="pending",
            total_cents=100,
            frozen_at=None,
            checkout_key=f"editable-checkout-{uuid4()}",
            created_at=_AT - timedelta(days=45),
        )
        db.add(order)
        db.flush()
        db.add(SaleOrderItem(
            tenant_id=folder.tenant_id,
            sale_order_id=order.id,
            photo_asset_id=None,
            photo_asset_id_snapshot=uuid4(),
            filename_snapshot="sintetica.jpg",
            folder_id_snapshot=folder.id,
            folder_name_snapshot=folder.name,
            unit_price_cents=100,
        ))
        db.commit()

        assert scheduler.enqueue_eligible_archive_operations(db, at=_AT) == 0
        cycle = db.scalar(select(MediaArchiveCycle).where(
            MediaArchiveCycle.tenant_id == folder.tenant_id,
            MediaArchiveCycle.folder_id == folder.id,
        ))
        assert cycle is not None
        assert _aware(cycle.next_archive_check_at) == _AT + scheduler.ARCHIVE_RECHECK_DELAY
        assert db.scalar(select(MediaArchiveOperation.id).where(
            MediaArchiveOperation.cycle_id == cycle.id,
            MediaArchiveOperation.operation_type == "archive",
        )) is None
        notice = db.scalar(select(MediaArchiveNotice).where(
            MediaArchiveNotice.cycle_id == cycle.id,
        ))
        assert notice is not None
        assert notice.notice_type == "blocked_open_order"
    engine.dispose()


def test_future_and_indefinite_folders_are_not_discovered():
    engine = _engine_with_schema()
    with Session(engine, expire_on_commit=False) as db:
        future = _seed_folder(db, name="Futura", expires_at=_AT + timedelta(days=1))
        indefinite = _seed_folder(db, name="Indeterminada", expires_at=None)
        indefinite.access_expires_at = None
        db.commit()

        assert scheduler.enqueue_eligible_archive_operations(db, at=_AT) == 0
        assert db.scalar(select(func.count()).select_from(MediaArchiveCycle)) == 0
        assert db.get(PhotoFolder, future.id).access_expires_at == _AT + timedelta(days=1)
    engine.dispose()


def test_private_folder_waits_until_latest_individual_reopening_plus_30_days():
    engine = _engine_with_schema()
    with Session(engine, expire_on_commit=False) as db:
        folder = _seed_folder(db, audience_scope="selected")
        client = Client(
            tenant_id=folder.tenant_id,
            full_name="Cliente sintética",
            phone_e164="+5511999990001",
        )
        db.add(client)
        db.flush()
        db.add(GalleryClientState(
            tenant_id=folder.tenant_id,
            parent_gallery_id=folder.parent_gallery_id,
            client_id=client.id,
        ))
        db.flush()
        reopened_until = _AT - timedelta(days=10)
        db.add(GalleryReopeningRequest(
            tenant_id=folder.tenant_id,
            parent_gallery_id=folder.parent_gallery_id,
            photo_folder_id=folder.id,
            requested_by_client_id=client.id,
            idempotency_key="synthetic-private-reopening",
            status="approved",
            approved_until=reopened_until,
            approved_duration_days=7,
            decided_at=reopened_until - timedelta(days=7),
            created_at=reopened_until - timedelta(days=8),
        ))
        db.commit()

        assert scheduler.enqueue_eligible_archive_operations(db, at=_AT) == 0
        cycle = db.scalar(select(MediaArchiveCycle).where(
            MediaArchiveCycle.folder_id == folder.id,
        ))
        assert cycle is not None
        assert _aware(cycle.next_archive_check_at) == reopened_until + timedelta(days=30)

        assert scheduler.enqueue_eligible_archive_operations(
            db, at=reopened_until + timedelta(days=30),
        ) == 1
    engine.dispose()


def test_private_window_notice_uses_latest_reopening_and_supersedes_old_deadline():
    engine = _engine_with_schema()
    with Session(engine, expire_on_commit=False) as db:
        folder = _seed_folder(db, audience_scope="selected")
        client = Client(
            tenant_id=folder.tenant_id,
            full_name="Cliente sintética",
            phone_e164="+5511999990001",
        )
        db.add(client)
        db.flush()
        db.add(GalleryClientState(
            tenant_id=folder.tenant_id,
            parent_gallery_id=folder.parent_gallery_id,
            client_id=client.id,
        ))
        db.flush()
        first_expiry = _AT - timedelta(days=24)
        latest_expiry = _AT - timedelta(days=23)
        for index, expiry in enumerate((first_expiry, latest_expiry), start=1):
            db.add(GalleryReopeningRequest(
                tenant_id=folder.tenant_id,
                parent_gallery_id=folder.parent_gallery_id,
                photo_folder_id=folder.id,
                requested_by_client_id=client.id,
                idempotency_key=f"synthetic-private-reopening-{index}",
                status="approved",
                approved_until=expiry,
                approved_duration_days=7,
                decided_at=expiry - timedelta(days=7),
                created_at=expiry - timedelta(days=8),
            ))
        db.commit()

        assert scheduler.enqueue_due_archive_window_notices(db, at=_AT) == 1
        cycle = db.scalar(select(MediaArchiveCycle).where(
            MediaArchiveCycle.tenant_id == folder.tenant_id,
            MediaArchiveCycle.folder_id == folder.id,
        ))
        notice = db.scalar(select(MediaArchiveNotice).where(
            MediaArchiveNotice.tenant_id == folder.tenant_id,
        ))
        assert cycle is not None and notice is not None
        assert _aware(cycle.last_window_notice_for_expiry) == latest_expiry
        assert _aware(notice.deadline_at) == latest_expiry + timedelta(days=30)
        assert notice.notice_type == "window_7_days"
        assert scheduler.enqueue_due_archive_window_notices(db, at=_AT) == 0

        new_expiry = _AT - timedelta(days=22)
        db.add(GalleryReopeningRequest(
            tenant_id=folder.tenant_id,
            parent_gallery_id=folder.parent_gallery_id,
            photo_folder_id=folder.id,
            requested_by_client_id=client.id,
            idempotency_key="synthetic-private-reopening-new-deadline",
            status="approved",
            approved_until=new_expiry,
            approved_duration_days=7,
            decided_at=new_expiry - timedelta(days=7),
            created_at=new_expiry - timedelta(days=8),
        ))
        db.flush()
        from app.media_archive_notices import supersede_window_notices_for_folder

        supersede_window_notices_for_folder(
            db,
            tenant_id=folder.tenant_id,
            folder_id=folder.id,
            current_deadline=new_expiry + timedelta(days=30),
            at=_AT + timedelta(minutes=1),
        )
        db.commit()

        assert _aware(notice.superseded_at) == _AT + timedelta(minutes=1)
        assert scheduler.enqueue_due_archive_window_notices(
            db, at=_AT + timedelta(days=1),
        ) == 1
        notices = list(db.scalars(select(MediaArchiveNotice).where(
            MediaArchiveNotice.tenant_id == folder.tenant_id,
        ).order_by(MediaArchiveNotice.created_at)))
        assert len(notices) == 2
        assert _aware(cycle.last_window_notice_for_expiry) == new_expiry
        assert _aware(notices[1].deadline_at) == new_expiry + timedelta(days=30)
        assert scheduler.enqueue_due_archive_window_notices(
            db, at=_AT + timedelta(days=1, seconds=1),
        ) == 0
    engine.dispose()


def test_blocked_folder_is_rechecked_and_does_not_starve_next_candidate(monkeypatch):
    engine = _engine_with_schema()
    with Session(engine, expire_on_commit=False) as db:
        blocked = _seed_folder(
            db,
            name="Bloqueada",
            expires_at=_AT - timedelta(days=70),
        )
        ready = _seed_folder(
            db,
            name="Pronta",
            expires_at=_AT - timedelta(days=60),
        )
        blocked_id, ready_id = blocked.id, ready.id
        original = scheduler.archive_blocker
        monkeypatch.setattr(
            scheduler,
            "archive_blocker",
            lambda _db, folder, *, at: "open_order" if folder.id == blocked_id else original(_db, folder, at=at),
        )

        assert scheduler.enqueue_eligible_archive_operations(db, at=_AT, limit=1) == 0
        blocked_cycle = db.scalar(select(MediaArchiveCycle).where(
            MediaArchiveCycle.folder_id == blocked_id,
        ))
        blocked_notices = list(db.scalars(select(MediaArchiveNotice).where(
            MediaArchiveNotice.cycle_id == blocked_cycle.id,
        )))
        assert len(blocked_notices) == 1
        assert blocked_notices[0].notice_type == "blocked_open_order"
        assert _aware(blocked_cycle.next_archive_check_at) == _AT + scheduler.ARCHIVE_RECHECK_DELAY

        assert scheduler.enqueue_eligible_archive_operations(db, at=_AT, limit=1) == 1
        ready_cycle = db.scalar(select(MediaArchiveCycle).where(
            MediaArchiveCycle.folder_id == ready_id,
        ))
        assert ready_cycle is not None

        monkeypatch.setattr(scheduler, "archive_blocker", original)
        assert scheduler.enqueue_eligible_archive_operations(
            db, at=_AT + scheduler.ARCHIVE_RECHECK_DELAY, limit=1,
        ) == 1
        blocked_operation = db.scalar(select(MediaArchiveOperation).where(
            MediaArchiveOperation.cycle_id == blocked_cycle.id,
        ))
        assert blocked_operation is not None
        assert db.scalar(select(func.count()).select_from(MediaArchiveNotice).where(
            MediaArchiveNotice.cycle_id == blocked_cycle.id,
        )) == 1
    engine.dispose()


def test_successful_recovery_starts_a_new_archive_cycle():
    engine = _engine_with_schema()
    with Session(engine, expire_on_commit=False) as db:
        folder = _seed_folder(db, expires_at=_AT - timedelta(days=60))
        cycle = MediaArchiveCycle(
            tenant_id=folder.tenant_id,
            parent_gallery_id=folder.parent_gallery_id,
            folder_id=folder.id,
            cycle_number=1,
            state="local",
            archived_at=_AT - timedelta(days=31),
            created_at=_AT - timedelta(days=100),
            updated_at=_AT - timedelta(days=31),
        )
        db.add(cycle)
        db.flush()
        db.add_all((
            MediaArchiveOperation(
                tenant_id=folder.tenant_id,
                cycle_id=cycle.id,
                operation_type="archive",
                status="completed",
                idempotency_key="synthetic-first-archive",
                actor_type="system",
                created_at=_AT - timedelta(days=100),
            ),
            MediaArchiveOperation(
                tenant_id=folder.tenant_id,
                cycle_id=cycle.id,
                operation_type="restore",
                status="completed",
                idempotency_key="synthetic-first-restore",
                actor_type="tenant",
                created_at=_AT - timedelta(days=31),
            ),
        ))
        db.commit()

        assert scheduler.enqueue_eligible_archive_operations(db, at=_AT) == 1
        cycles = list(db.scalars(select(MediaArchiveCycle).where(
            MediaArchiveCycle.folder_id == folder.id,
        ).order_by(MediaArchiveCycle.cycle_number)))
        assert [item.cycle_number for item in cycles] == [1, 2]
        next_operation = db.scalar(select(MediaArchiveOperation).where(
            MediaArchiveOperation.cycle_id == cycles[1].id,
        ))
        assert next_operation is not None
        assert next_operation.idempotency_key == f"archive:{cycles[1].id}"
    engine.dispose()


def test_proven_archive_failure_is_not_reenqueued():
    engine = _engine_with_schema()
    with Session(engine, expire_on_commit=False) as db:
        failed = _seed_folder(db, name="Falhou", expires_at=_AT - timedelta(days=70))
        healthy = _seed_folder(db, name="Saudável", expires_at=_AT - timedelta(days=60))
        cycle = MediaArchiveCycle(
            tenant_id=failed.tenant_id,
            parent_gallery_id=failed.parent_gallery_id,
            folder_id=failed.id,
            cycle_number=1,
            state="local",
            created_at=_AT - timedelta(days=1),
            updated_at=_AT - timedelta(days=1),
        )
        db.add(cycle)
        db.flush()
        db.add(MediaArchiveOperation(
            tenant_id=failed.tenant_id,
            cycle_id=cycle.id,
            operation_type="archive",
            status="failed",
            idempotency_key="synthetic-failed-archive",
            actor_type="system",
            created_at=_AT - timedelta(days=1),
        ))
        db.commit()

        assert scheduler.enqueue_eligible_archive_operations(db, at=_AT) == 1
        assert db.scalar(select(func.count()).select_from(MediaArchiveOperation).where(
            MediaArchiveOperation.cycle_id == cycle.id,
        )) == 1
        assert db.scalar(select(func.count()).select_from(MediaArchiveOperation).where(
            MediaArchiveOperation.cycle_id == select(MediaArchiveCycle.id).where(
                MediaArchiveCycle.folder_id == healthy.id,
            ).scalar_subquery(),
        )) == 1
    engine.dispose()


@pytest.fixture
def postgres_schema():
    raw = os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Requer PostgreSQL local sintético exclusivo")
    url = make_url(raw)
    expected_port_raw = os.getenv("PHOTOGRAPHER_TEST_DATABASE_PORT", "15470")
    if (
        not expected_port_raw.isdecimal()
        or url.get_backend_name() != "postgresql"
        or url.host != "127.0.0.1"
        or url.port != int(expected_port_raw)
        or url.database != "pyp_photographer_test"
    ):
        pytest.fail("DDL de teste limitado ao PostgreSQL sintético local aprovado.")
    schema = "media_archive_discovery_" + uuid4().hex
    admin = sa.create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = sa.create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_concurrent_discovery_enqueues_only_one_operation(postgres_schema):
    engine = postgres_schema
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        db.add(MediaArchiveCoordinator(id=1))
        _seed_folder(db)
        db.commit()
    barrier = Barrier(2)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def scan():
        with factory() as db:
            barrier.wait(timeout=10)
            return scheduler.enqueue_eligible_archive_operations(db, at=_AT)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: scan(), range(2)))

    with Session(engine) as db:
        assert sum(results) == 1
        assert db.scalar(select(func.count()).select_from(MediaArchiveCycle)) == 1
        assert db.scalar(select(func.count()).select_from(MediaArchiveOperation)) == 1


def test_discovery_migration_adds_recheck_index_and_refuses_to_drop_saved_state(postgres_schema):
    migration_path = (
        os.path.join(os.path.dirname(__file__), "..", "migrations", "versions",
                     "20261109_0115_media_archive_discovery.py")
    )
    spec = importlib.util.spec_from_file_location("media_archive_discovery_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    with postgres_schema.begin() as connection:
        connection.execute(text(
            "CREATE TABLE media_archive_cycle (id uuid PRIMARY KEY, state varchar(32) NOT NULL)"
        ))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        columns = sa.inspect(connection).get_columns("media_archive_cycle")
        assert "next_archive_check_at" in {column["name"] for column in columns}
        assert "ix_media_archive_cycle_state_next_check" in {
            index["name"] for index in sa.inspect(connection).get_indexes("media_archive_cycle")
        }
        connection.execute(text(
            "INSERT INTO media_archive_cycle (id, state, next_archive_check_at) "
            "VALUES (gen_random_uuid(), 'local', now())"
        ))
        with pytest.raises(RuntimeError, match="rollback recusado com dados"):
            migration.downgrade()


def test_notice_migration_adds_inbox_and_refuses_data_loss(postgres_schema):
    migration_path = (
        os.path.join(os.path.dirname(__file__), "..", "migrations", "versions",
                     "20261109_0116_media_archive_notices.py")
    )
    spec = importlib.util.spec_from_file_location("media_archive_notice_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    tenant_id, cycle_id = uuid4(), uuid4()
    with postgres_schema.begin() as connection:
        connection.execute(text("CREATE TABLE tenant (id uuid PRIMARY KEY)"))
        connection.execute(text(
            "CREATE TABLE media_archive_cycle (id uuid PRIMARY KEY, tenant_id uuid NOT NULL, "
            "state varchar(32) NOT NULL, CONSTRAINT uq_test_cycle_id_tenant UNIQUE (id, tenant_id))"
        ))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        cycle_columns = {column["name"] for column in sa.inspect(connection).get_columns("media_archive_cycle")}
        assert "last_window_notice_for_expiry" in cycle_columns
        assert {"ix_media_archive_notice_tenant_created", "ix_media_archive_notice_tenant_read_created"} <= {
            index["name"] for index in sa.inspect(connection).get_indexes("media_archive_notice")
        }
        connection.execute(text("INSERT INTO tenant (id) VALUES (:id)"), {"id": tenant_id})
        connection.execute(text(
            "INSERT INTO media_archive_cycle (id, tenant_id, state) VALUES (:id, :tenant_id, 'local')"
        ), {"id": cycle_id, "tenant_id": tenant_id})
        connection.execute(text(
            "INSERT INTO media_archive_notice (id, tenant_id, cycle_id, notice_type, idempotency_key, title, body) "
            "VALUES (:id, :tenant_id, :cycle_id, 'window_7_days', 'migration-test', 'Aviso', 'Texto')"
        ), {"id": uuid4(), "tenant_id": tenant_id, "cycle_id": cycle_id})
        with pytest.raises(RuntimeError, match="rollback recusado com dados"):
            migration.downgrade()
        connection.execute(text("DELETE FROM media_archive_notice"))
        migration.downgrade()
        assert "last_window_notice_for_expiry" not in {
            column["name"] for column in sa.inspect(connection).get_columns("media_archive_cycle")
        }
