"""Cobertura da ampliação reversível das CHECK constraints de intensidade."""

import importlib

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

TABLES = (
    ("preview_adjustment_settings", "strength"),
    ("gallery_preview_settings", "strength"),
    ("folder_processing_settings", "preview_strength"),
)


@pytest.fixture
def legacy_strength_schema():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        for table, column in TABLES:
            connection.exec_driver_sql(
                f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, {column} INTEGER NOT NULL "
                f"CHECK ({column} BETWEEN 10 AND 75))"
            )
            connection.exec_driver_sql(f"INSERT INTO {table} (id, {column}) VALUES (1, 75)")
    yield engine
    engine.dispose()


def _migrate(engine, direction):
    migration = importlib.import_module(
        "migrations.versions.20261026_0090_preview_adjustment_strength_100"
    )
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        getattr(migration, direction)()


def test_upgrade_allows_100_and_preserves_existing_rows(legacy_strength_schema):
    engine = legacy_strength_schema
    _migrate(engine, "upgrade")
    inspector = sa.inspect(engine)
    for table, column in TABLES:
        checks = inspector.get_check_constraints(table)
        assert any(f"{column} BETWEEN 10 AND 100" in check["sqltext"] for check in checks)
        with engine.begin() as connection:
            assert connection.exec_driver_sql(f"SELECT {column} FROM {table} WHERE id=1").scalar_one() == 75
            connection.exec_driver_sql(f"INSERT INTO {table} (id, {column}) VALUES (2, 100)")


def test_downgrade_refuses_100_without_changing_any_constraint(legacy_strength_schema):
    engine = legacy_strength_schema
    _migrate(engine, "upgrade")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE folder_processing_settings SET preview_strength=100 WHERE id=1"
        )
    with pytest.raises(RuntimeError, match="acima de 75%"):
        _migrate(engine, "downgrade")
    for table, column in TABLES:
        checks = sa.inspect(engine).get_check_constraints(table)
        assert any(f"{column} BETWEEN 10 AND 100" in check["sqltext"] for check in checks)


def test_downgrade_restores_75_when_values_fit(legacy_strength_schema):
    engine = legacy_strength_schema
    _migrate(engine, "upgrade")
    _migrate(engine, "downgrade")
    for table, column in TABLES:
        checks = sa.inspect(engine).get_check_constraints(table)
        assert any(f"{column} BETWEEN 10 AND 75" in check["sqltext"] for check in checks)
