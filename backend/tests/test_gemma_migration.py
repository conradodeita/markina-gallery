"""Migração aditiva Gemma em banco SQLite descartável."""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_gemma_shadow_migration_adds_shared_setting_and_job_kind() -> None:
    backend = Path(__file__).resolve().parents[1]
    path = backend / "migrations/versions/20261011_0073_gemma_shadow_index.py"
    spec = importlib.util.spec_from_file_location("gemma_shadow_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE admin_user (id CHAR(32) PRIMARY KEY)"))
        connection.execute(sa.text(
            "CREATE TABLE facial_job (kind VARCHAR(16), CONSTRAINT ck_facial_job_kind "
            "CHECK (kind IN ('index', 'purge', 'search', 'cleanup')))"
        ))
        connection.execute(sa.text(
            "CREATE TABLE photo_face_embedding (tenant_id CHAR(32), parent_gallery_id CHAR(32), "
            "model_id VARCHAR(120), model_version VARCHAR(120), quality_version VARCHAR(120))"
        ))
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()

        columns = {column["name"] for column in sa.inspect(connection).get_columns(
            "facial_embedding_experiment_setting"
        )}
        assert {
            "singleton", "enabled", "mode", "model_revision", "enabled_since",
            "worker_last_seen_at", "updated_by_admin_id", "updated_at",
        } <= columns
        job_sql = connection.scalar(sa.text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='facial_job'"
        ))
        assert "index_gemma" in job_sql
        indexes = {item["name"] for item in sa.inspect(connection).get_indexes("photo_face_embedding")}
        assert "ix_face_embedding_gallery_engine" in indexes
    engine.dispose()


def test_facial_search_engine_migration_pins_model_and_adds_gemma_search_job() -> None:
    backend = Path(__file__).resolve().parents[1]
    path = backend / "migrations/versions/20261011_0074_facial_search_engine.py"
    spec = importlib.util.spec_from_file_location("facial_search_engine_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(sa.text(
            "CREATE TABLE facial_search_request (id CHAR(32) PRIMARY KEY)"
        ))
        connection.execute(sa.text(
            "CREATE TABLE facial_job (kind VARCHAR(16), CONSTRAINT ck_facial_job_kind "
            "CHECK (kind IN ('index', 'index_gemma', 'purge', 'search', 'cleanup')))"
        ))
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()

        columns = {column["name"] for column in sa.inspect(connection).get_columns(
            "facial_search_request"
        )}
        assert "search_engine" in columns
        request_sql = connection.scalar(sa.text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='facial_search_request'"
        ))
        job_sql = connection.scalar(sa.text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='facial_job'"
        ))
        assert "google-embeddinggemma-2" in request_sql
        assert "search_gemma" in job_sql
    engine.dispose()
