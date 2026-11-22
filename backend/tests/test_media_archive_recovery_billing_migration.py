"""Contrato DDL da cobrança de recuperação de arquivo frio."""

import importlib.util
from io import StringIO
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _load_migration(bind):
    path = Path(__file__).parents[1] / "migrations/versions/20261109_0114_media_archive_recovery_billing.py"
    spec = importlib.util.spec_from_file_location("media_archive_recovery_billing_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(bind))
    return module


def test_migration_upgrade_renders_postgresql_billing_schema_and_guards():
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql",
        opts={"as_sql": True, "output_buffer": output},
    )
    migration = _load_migration(context.bind)
    migration.upgrade()
    ddl = output.getvalue()

    assert "CREATE TABLE media_archive_recovery_pricing" in ddl
    assert "INSERT INTO media_archive_recovery_pricing" in ddl
    assert "CREATE TABLE media_archive_recovery_request" in ddl
    assert "requested_by_tenant_admin_id" in ddl
    assert "requested_by_owner_admin_id" in ddl
    assert "CREATE TABLE media_archive_recovery_credit_reservation" in ddl
    assert "CREATE TABLE media_archive_recovery_credit_allocation_event" in ddl
    assert "archive_recovery" in ddl
    assert "uq_credit_entry_archive_operation_consumption" in ddl
    assert "CREATE FUNCTION reject_media_archive_recovery_request_change()" in ddl
    assert "CREATE TRIGGER media_archive_recovery_request_no_truncate" in ddl
    assert "CREATE FUNCTION reject_media_archive_recovery_credit_allocation_change()" in ddl
    assert "CREATE TRIGGER media_archive_recovery_credit_allocation_no_truncate" in ddl
    assert "media_archive.recovery_pricing_updated" in ddl


def test_migration_refuses_non_postgresql():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        migration = _load_migration(connection)
        with pytest.raises(RuntimeError, match="requer PostgreSQL"):
            migration.upgrade()
    engine.dispose()
