"""A migration RAW integrada deve preservar o contrato e ser reversível em schema descartável."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_raw_development_migration_creates_tenant_scoped_tables_and_downgrades(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'raw-migration.sqlite').as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE tenant (id CHAR(32) PRIMARY KEY)"))
        connection.execute(text(
            "CREATE TABLE photo_asset (id CHAR(32) NOT NULL, tenant_id CHAR(32) NOT NULL, "
            "PRIMARY KEY (id), UNIQUE (id, tenant_id), "
            "FOREIGN KEY (tenant_id) REFERENCES tenant(id))"
        ))
        migration_path = Path(__file__).resolve().parents[1] / (
            "migrations/versions/20261014_0078_raw_development.py"
        )
        spec = importlib.util.spec_from_file_location("raw_development_migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(migration)
        assert migration.revision == "20261014_0078"
        assert migration.down_revision == "20261012_0077"

        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        inspector = inspect(connection)
        assert {"raw_development_settings", "raw_development_job"}.issubset(
            inspector.get_table_names()
        )
        job_fks = inspector.get_foreign_keys("raw_development_job")
        assert any(
            fk["constrained_columns"] == ["photo_asset_id", "tenant_id"]
            and fk["referred_table"] == "photo_asset"
            and fk["referred_columns"] == ["id", "tenant_id"]
            for fk in job_fks
        )

        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert "raw_development_settings" not in inspect(connection).get_table_names()
        assert "raw_development_job" not in inspect(connection).get_table_names()
        assert "photo_asset" in inspect(connection).get_table_names()
    engine.dispose()
