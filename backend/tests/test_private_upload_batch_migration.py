"""Verifica a evolução preservadora do escopo de lotes de upload."""

import os
from uuid import uuid4

import pytest
import sqlalchemy as sa

from tests.test_tenant_migration import migrate


@pytest.fixture
def private_batch_migration_database():
    url = os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL") or os.getenv("TENANT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL sintético não configurado")
    parsed = sa.engine.make_url(url)
    assert parsed.host == "127.0.0.1"
    assert (parsed.port, parsed.database) in ((55469, "pyp_tenant_test"), (15470, "pyp_photographer_test"))
    control = sa.create_engine(parsed, isolation_level="AUTOCOMMIT")
    database = f"private_batch_migration_{uuid4().hex}"
    with control.connect() as connection:
        connection.execute(sa.text(f'CREATE DATABASE "{database}"'))
    try:
        yield parsed.set(database=database).render_as_string(hide_password=False)
    finally:
        with control.connect() as connection:
            connection.execute(sa.text(f'DROP DATABASE "{database}"'))
        control.dispose()


def test_private_upload_batch_scope_migration_preserves_legacy_schema(private_batch_migration_database: str) -> None:
    migrate(private_batch_migration_database, "upgrade", "20261014_0081")
    migrate(private_batch_migration_database, "upgrade", "20261016_0082")

    engine = sa.create_engine(private_batch_migration_database)
    with engine.connect() as connection:
        inspector = sa.inspect(connection)
        columns = {column["name"]: column for column in inspector.get_columns("private_upload_batch")}
        assert columns["derived_gallery_id"]["nullable"] is True
        assert columns["parent_gallery_id"]["nullable"] is True
        assert columns["folder_id"]["nullable"] is True
        checks = {item["name"]: item["sqltext"] for item in inspector.get_check_constraints("private_upload_batch")}
        assert "ck_private_upload_batch_scope" in checks
        foreign_keys = {item["name"] for item in inspector.get_foreign_keys("private_upload_batch")}
        assert "fk_private_upload_batch_folder_parent_tenant" in foreign_keys
        asset_uniques = inspector.get_unique_constraints("private_upload_batch_asset")
        assert not any("photo_asset_id" in item["column_names"] for item in asset_uniques)
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "20261016_0082"
    engine.dispose()

