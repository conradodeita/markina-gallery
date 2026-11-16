"""Integridade tenant-scoped do catálogo de arquivo frio em schema sintético."""

import importlib.util
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import event
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.auth import (
    Base,
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveOperation,
    MediaArchiveSpaceReservation,
    PhotoFolder,
)
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def _engine_with_catalog_schema():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE tenant (id CHAR(32) PRIMARY KEY)"))
        connection.execute(sa.text(
            "CREATE TABLE parent_gallery ("
            "id CHAR(32) PRIMARY KEY, tenant_id CHAR(32) NOT NULL, "
            "UNIQUE (id, tenant_id), FOREIGN KEY (tenant_id) REFERENCES tenant(id))"
        ))
        connection.execute(sa.text(
            "CREATE TABLE photo_folder ("
            "id CHAR(32) PRIMARY KEY, tenant_id CHAR(32) NOT NULL, "
            "parent_gallery_id CHAR(32) NOT NULL, UNIQUE (id, tenant_id), "
            "UNIQUE (id, parent_gallery_id, tenant_id), "
            "FOREIGN KEY (tenant_id) REFERENCES tenant(id), "
            "FOREIGN KEY (parent_gallery_id) REFERENCES parent_gallery(id))"
        ))

    catalog_tables = [
        Base.metadata.tables[name]
        for name in (
            "media_archive_cycle",
            "media_archive_operation",
            "media_archive_object",
            "media_archive_event",
            "media_archive_coordinator",
            "media_archive_space_reservation",
        )
    ]
    with engine.begin() as connection:
        for table in catalog_tables:
            connection.execute(sa.schema.CreateTable(table))
        for table in catalog_tables:
            for index in sorted(table.indexes, key=lambda item: item.name or ""):
                connection.execute(sa.schema.CreateIndex(index))
    return engine


def test_catalog_enforces_tenant_pairing_idempotency_and_global_lease_shape():
    engine = _engine_with_catalog_schema()
    tenant_a, tenant_b = uuid4(), uuid4()
    parent_a, parent_b = uuid4(), uuid4()
    folder_a, folder_b = uuid4(), uuid4()
    cycle_a, operation_a = uuid4(), uuid4()

    with engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO tenant (id) VALUES (:id), (:other)"), {
            "id": tenant_a.hex, "other": tenant_b.hex,
        })
        connection.execute(sa.text(
            "INSERT INTO parent_gallery (id, tenant_id) VALUES (:id, :tenant), (:other, :other_tenant)"
        ), {
            "id": parent_a.hex, "tenant": tenant_a.hex,
            "other": parent_b.hex, "other_tenant": tenant_b.hex,
        })
        connection.execute(sa.text(
            "INSERT INTO photo_folder (id, tenant_id, parent_gallery_id) "
            "VALUES (:id, :tenant, :parent), (:other, :other_tenant, :other_parent)"
        ), {
            "id": folder_a.hex, "tenant": tenant_a.hex, "parent": parent_a.hex,
            "other": folder_b.hex, "other_tenant": tenant_b.hex, "other_parent": parent_b.hex,
        })
        connection.execute(MediaArchiveCycle.__table__.insert().values(
            id=cycle_a, tenant_id=tenant_a, parent_gallery_id=parent_a, folder_id=folder_a,
        ))

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(MediaArchiveCycle.__table__.insert().values(
            id=uuid4(), tenant_id=tenant_a, parent_gallery_id=parent_a, folder_id=folder_b,
        ))

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(MediaArchiveOperation.__table__.insert().values(
            id=uuid4(), tenant_id=tenant_b, cycle_id=cycle_a,
            operation_type="restore", idempotency_key="wrong-tenant",
        ))

    with engine.begin() as connection:
        connection.execute(MediaArchiveOperation.__table__.insert().values(
            id=operation_a, tenant_id=tenant_a, cycle_id=cycle_a,
            operation_type="archive", idempotency_key="archive-cycle-a",
        ))

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(MediaArchiveOperation.__table__.insert().values(
            id=uuid4(), tenant_id=tenant_a, cycle_id=cycle_a,
            operation_type="restore", idempotency_key="duplicate-active-cycle",
        ))

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(MediaArchiveOperation.__table__.insert().values(
            id=uuid4(), tenant_id=tenant_a, cycle_id=cycle_a,
            operation_type="restore", idempotency_key="processing-without-lease",
            status="processing",
        ))

    with engine.begin() as connection:
        connection.execute(MediaArchiveCoordinator.__table__.insert().values(id=1))
        connection.execute(MediaArchiveCoordinator.__table__.update().values(
            active_operation_id=operation_a,
            lease_token="synthetic-lease-token",
            lease_expires_at=sa.func.current_timestamp(),
        ).where(MediaArchiveCoordinator.id == 1))

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(MediaArchiveSpaceReservation.__table__.insert().values(
            id=uuid4(), tenant_id=tenant_a, operation_id=operation_a,
            volume_key="invalid", reserved_bytes=10,
        ))

    engine.dispose()


def test_catalog_indexes_and_tenant_composite_constraints_are_declared():
    cycle = Base.metadata.tables["media_archive_cycle"]
    operation = Base.metadata.tables["media_archive_operation"]
    folder = PhotoFolder.__table__

    assert "uq_owner_photo_folder_id_tenant_id" in {
        constraint.name for constraint in folder.constraints
    }
    assert "uq_owner_photo_folder_id_parent_gallery_id_tenant_id" in {
        constraint.name for constraint in folder.constraints
    }
    assert "uq_media_archive_cycle_id_tenant" in {
        constraint.name for constraint in cycle.constraints
    }
    assert "fk_media_archive_cycle_folder_tenant" in {
        constraint.name for constraint in cycle.constraints
    }
    assert "uq_media_archive_operation_idempotency" in {
        constraint.name for constraint in operation.constraints
    }
    active_cycle_index = next(
        index for index in operation.indexes
        if index.name == "uq_media_archive_operation_active_cycle"
    )
    assert active_cycle_index.unique
    assert "reconciliation_required" in str(active_cycle_index.dialect_options["sqlite"]["where"])
    assert "ix_media_archive_operation_lease_expires_at" in {
        index.name for index in operation.indexes
    }


def _load_catalog_migration(connection):
    path = Path(__file__).parents[1] / "migrations/versions/20261108_0112_media_archive_catalog.py"
    spec = importlib.util.spec_from_file_location("media_archive_catalog_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    return module


def test_postgresql_catalog_migration_generates_expected_offline_ddl():
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql",
        opts={"as_sql": True, "output_buffer": output},
    )
    migration = _load_catalog_migration(context.bind)
    migration.upgrade()
    ddl = output.getvalue()

    assert "CREATE TABLE media_archive_cycle" in ddl
    assert "FOREIGN KEY(folder_id, parent_gallery_id, tenant_id)" in ddl
    assert "uq_media_archive_cycle_folder_number" in ddl
    assert "uq_media_archive_object_cycle_source" in ddl
    assert "media_archive_coordinator" in ddl
    assert "CREATE FUNCTION reject_media_archive_event_change()" in ddl
    assert "CREATE TRIGGER media_archive_event_no_truncate" in ddl


def _create_pre_catalog_schema(connection):
    connection.execute(sa.text("CREATE TABLE tenant (id uuid PRIMARY KEY)"))
    connection.execute(sa.text(
        "CREATE TABLE parent_gallery ("
        "id uuid PRIMARY KEY, tenant_id uuid NOT NULL, UNIQUE (id, tenant_id), "
        "FOREIGN KEY (tenant_id) REFERENCES tenant(id))"
    ))
    connection.execute(sa.text(
        "CREATE TABLE photo_folder ("
        "id uuid PRIMARY KEY, tenant_id uuid NOT NULL, parent_gallery_id uuid NOT NULL, "
        "derived_gallery_id uuid NULL, UNIQUE (id, parent_gallery_id), "
        "UNIQUE (id, parent_gallery_id, tenant_id), "
        "UNIQUE (id, parent_gallery_id, derived_gallery_id), "
        "FOREIGN KEY (tenant_id) REFERENCES tenant(id), "
        "FOREIGN KEY (parent_gallery_id) REFERENCES parent_gallery(id))"
    ))


def test_postgres_catalog_migration_enforces_audit_and_refuses_data_loss(postgres_schema):
    engine = postgres_schema
    tenant_id, parent_id, folder_id = uuid4(), uuid4(), uuid4()
    cycle_id, operation_id, event_id = uuid4(), uuid4(), uuid4()

    with engine.begin() as connection:
        _create_pre_catalog_schema(connection)
        migration = _load_catalog_migration(connection)
        migration.upgrade()
        connection.execute(sa.text("INSERT INTO tenant (id) VALUES (:id)"), {"id": tenant_id})
        connection.execute(sa.text(
            "INSERT INTO parent_gallery (id, tenant_id) VALUES (:id, :tenant)"
        ), {"id": parent_id, "tenant": tenant_id})
        connection.execute(sa.text(
            "INSERT INTO photo_folder (id, tenant_id, parent_gallery_id) "
            "VALUES (:id, :tenant, :parent)"
        ), {"id": folder_id, "tenant": tenant_id, "parent": parent_id})
        connection.execute(sa.text(
            "INSERT INTO media_archive_cycle (id, tenant_id, parent_gallery_id, folder_id) "
            "VALUES (:id, :tenant, :parent, :folder)"
        ), {"id": cycle_id, "tenant": tenant_id, "parent": parent_id, "folder": folder_id})
        connection.execute(sa.text(
            "INSERT INTO media_archive_operation "
            "(id, tenant_id, cycle_id, operation_type, idempotency_key) "
            "VALUES (:id, :tenant, :cycle, 'archive', 'archive-once')"
        ), {"id": operation_id, "tenant": tenant_id, "cycle": cycle_id})
        connection.execute(sa.text(
            "INSERT INTO media_archive_event "
            "(id, tenant_id, cycle_id, operation_id, actor_type, event_type) "
            "VALUES (:id, :tenant, :cycle, :operation, 'system', 'queued')"
        ), {"id": event_id, "tenant": tenant_id, "cycle": cycle_id, "operation": operation_id})

    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(sa.text(
            "UPDATE media_archive_event SET event_type='rewritten' WHERE id=:id"
        ), {"id": event_id})

    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(sa.text("TRUNCATE media_archive_event"))

    with engine.begin() as connection:
        migration = _load_catalog_migration(connection)
        with pytest.raises(RuntimeError, match="rollback recusado com dados"):
            migration.downgrade()
        assert "media_archive_event" in sa.inspect(connection).get_table_names()


def test_postgres_catalog_empty_downgrade_drops_triggers_before_event_table(postgres_schema):
    engine = postgres_schema
    with engine.begin() as connection:
        _create_pre_catalog_schema(connection)
        migration = _load_catalog_migration(connection)
        migration.upgrade()
        migration.downgrade()
        table_names = set(sa.inspect(connection).get_table_names())
        assert "media_archive_cycle" not in table_names
        assert "media_archive_event" not in table_names
        constraints = sa.inspect(connection).get_unique_constraints("photo_folder")
        assert any(
            set(constraint["column_names"]) == {"id", "parent_gallery_id", "tenant_id"}
            for constraint in constraints
        )
