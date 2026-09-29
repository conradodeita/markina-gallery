"""Pastas legadas herdam e downgrade recusa perder override."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text

from tests.tenant_fixtures import LEGACY_SCHEMA_HEAD
from tests.test_gallery_client_audience_migration import _alembic


@pytest.mark.parametrize("kind", ["sqlite", "postgres"])
def test_folder_processing_migration(tmp_path, kind):
    url = f"sqlite:///{(tmp_path / 'folders.sqlite').as_posix()}" if kind == "sqlite" else os.getenv("TEST_POSTGRES_DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL descartável não configurado")
    _alembic(url, "upgrade", "20260927_0067")
    gallery_id, folder_id = uuid4().hex, uuid4().hex
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO parent_gallery (id, name, active, created_at) "
            "VALUES (:id, 'Legado', true, CURRENT_TIMESTAMP)"
        ), {"id": gallery_id})
        connection.execute(text(
            "INSERT INTO photo_folder (id, parent_gallery_id, name, status, purpose, position, created_at, updated_at) "
            "VALUES (:id, :gallery, 'Pasta', 'released', 'content', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"id": folder_id, "gallery": gallery_id})
    engine.dispose()
    _alembic(url, "upgrade", LEGACY_SCHEMA_HEAD)
    engine = create_engine(url)
    assert "folder_processing_settings" in inspect(engine).get_table_names()
    with engine.begin() as connection:
        assert connection.execute(text("SELECT count(*) FROM folder_processing_settings")).scalar() == 0
        connection.execute(text(
            "INSERT INTO folder_processing_settings (folder_id, preview_mode, facial_mode, "
            "preview_strength, preview_exposure_tenths, revision, updated_at) "
            "VALUES (:id, 'custom', 'off', 50, 5, 1, CURRENT_TIMESTAMP)"
        ), {"id": folder_id})
    engine.dispose()
    with pytest.raises(AssertionError, match="Downgrade recusado"):
        _alembic(url, "downgrade", "20260927_0067")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("UPDATE folder_processing_settings SET preview_mode='inherit', facial_mode='inherit'"))
    engine.dispose()
    _alembic(url, "downgrade", "20260927_0067")
