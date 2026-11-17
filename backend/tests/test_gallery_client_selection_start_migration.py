"""A migration aditiva preserva clientes antigos e protege horários novos."""

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def _migration(connection):
    path = Path(__file__).parents[1] / "migrations/versions/20261105_0106_gallery_client_selection_start.py"
    spec = importlib.util.spec_from_file_location("gallery_client_selection_start", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    return module


def test_selection_start_upgrade_preserves_old_rows_and_sqlite_downgrade_fails_closed():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE gallery_client_state (id INTEGER PRIMARY KEY, selection_expires_at DATETIME)"
        ))
        connection.execute(text(
            "INSERT INTO gallery_client_state (id, selection_expires_at) VALUES (1, NULL)"
        ))
        migration = _migration(connection)
        migration.upgrade()
        assert connection.scalar(text(
            "SELECT selection_started_at FROM gallery_client_state WHERE id = 1"
        )) is None

        connection.execute(text(
            "UPDATE gallery_client_state SET selection_started_at = '2026-11-05 12:00:00' WHERE id = 1"
        ))
        with pytest.raises(RuntimeError, match="PostgreSQL"):
            migration.downgrade()
        assert "selection_started_at" in {
            column["name"] for column in inspect(connection).get_columns("gallery_client_state")
        }
        assert connection.scalar(text(
            "SELECT selection_started_at FROM gallery_client_state WHERE id = 1"
        )) == "2026-11-05 12:00:00"
    engine.dispose()
