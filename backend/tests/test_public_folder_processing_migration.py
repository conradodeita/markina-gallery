"""A migração materializa defaults independentes sem tocar em mídia ou privadas."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


def test_public_folder_processing_migration_snapshots_existing_public_folders(tmp_path):
    url = f"sqlite:///{(tmp_path / 'public-folder-processing.sqlite').as_posix()}"
    engine = create_engine(url)
    configured_id, defaulted_id, private_id, fallback_id = (
        "configured", "defaulted", "private", "fallback",
    )
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE photo_folder (tenant_id TEXT, id TEXT, parent_gallery_id TEXT, purpose TEXT, derived_gallery_id TEXT, audience_scope TEXT)"))
        connection.execute(text("CREATE TABLE gallery_preview_settings (tenant_id TEXT, parent_gallery_id TEXT, enabled BOOLEAN, strength INTEGER, exposure_tenths INTEGER)"))
        connection.execute(text("CREATE TABLE folder_processing_settings (tenant_id TEXT, folder_id TEXT, preview_mode TEXT, facial_mode TEXT, preview_strength INTEGER, preview_exposure_tenths INTEGER, revision INTEGER, updated_at DATETIME)"))
        connection.execute(text("INSERT INTO photo_folder VALUES ('tenant', 'configured', 'gallery', 'content', NULL, 'all'), ('tenant', 'defaulted', 'gallery', 'content', NULL, NULL), ('tenant', 'private', 'gallery', 'content', NULL, 'selected'), ('tenant', 'fallback', 'gallery-without-settings', 'content', NULL, 'all')"))
        connection.execute(text("INSERT INTO gallery_preview_settings VALUES ('tenant', 'gallery', 0, 64, 6)"))
        connection.execute(text("INSERT INTO folder_processing_settings VALUES ('tenant', 'configured', 'off', 'off', 30, -4, 1, CURRENT_TIMESTAMP)"))
        migration_path = Path(__file__).resolve().parents[1] / "migrations/versions/20261013_0076_public_folder_processing.py"
        spec = importlib.util.spec_from_file_location("public_folder_processing_migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(migration)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        rows = connection.execute(text(
            "SELECT folder_id, preview_mode, facial_mode, preview_strength, preview_exposure_tenths "
            "FROM folder_processing_settings"
        )).all()
        values = {str(row.folder_id): row for row in rows}
        migrated = values[str(defaulted_id)]
        assert (migrated.preview_mode, migrated.facial_mode,
                migrated.preview_strength, migrated.preview_exposure_tenths) == ("custom", "on", 64, 6)
        assert (values[str(configured_id)].preview_mode, values[str(configured_id)].facial_mode,
                values[str(configured_id)].preview_strength, values[str(configured_id)].preview_exposure_tenths) == (
            "off", "off", 30, -4,
        )
        fallback = values[str(fallback_id)]
        assert (fallback.preview_mode, fallback.facial_mode,
                fallback.preview_strength, fallback.preview_exposure_tenths) == ("custom", "on", 50, 0)
        assert str(private_id) not in values
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert connection.execute(text(
            "SELECT count(*) FROM folder_processing_settings WHERE folder_id=:id"
        ), {"id": defaulted_id}).scalar_one() == 1
    engine.dispose()
