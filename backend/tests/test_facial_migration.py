"""Valida a migration aditiva da fundação do filtro facial."""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from subprocess import run
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text


def alembic(database_url: str, *arguments: str) -> None:
    backend = Path(__file__).resolve().parents[1]
    result = run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=backend,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_facial_foundation_migration_is_additive_disabled_and_reversible(
    tmp_path: Path,
) -> None:
    database = tmp_path / "facial-foundation.sqlite"
    database_url = f"sqlite:///{database.as_posix()}"
    alembic(database_url, "upgrade", "20260903_0042")

    engine = create_engine(database_url)
    parent_id, folder_id, photo_id = (uuid4() for _ in range(3))
    timestamp = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO parent_gallery (id, name, active, created_at) "
                "VALUES (:id, 'Evento preservado', 1, :created_at)"
            ),
            {"id": parent_id.hex, "created_at": timestamp},
        )
        connection.execute(
            text(
                "INSERT INTO photo_folder "
                "(id, parent_gallery_id, name, status, purpose, position, created_at, updated_at) "
                "VALUES (:id, :parent_id, 'Fotos', 'released', 'content', 0, "
                ":created_at, :created_at)"
            ),
            {
                "id": folder_id.hex,
                "parent_id": parent_id.hex,
                "created_at": timestamp,
            },
        )
        connection.execute(
            text(
                "INSERT INTO photo_asset "
                "(id, parent_gallery_id, folder_id, filename, storage_key, available, created_at) "
                "VALUES (:id, :parent_id, :folder_id, 'foto.jpg', 'evento/foto.jpg', 1, "
                ":created_at)"
            ),
            {
                "id": photo_id.hex,
                "parent_id": parent_id.hex,
                "folder_id": folder_id.hex,
                "created_at": timestamp,
            },
        )

    alembic(database_url, "upgrade", "head")
    inspector = inspect(engine)
    facial_tables = {
        "gallery_facial_policy",
        "photo_face_embedding",
        "facial_search_request",
        "facial_search_snapshot_item",
        "facial_search_candidate",
        "facial_job",
        "facial_search_notification_outbox",
    }
    assert facial_tables <= set(inspector.get_table_names())
    assert any(
        constraint["name"] == "uq_photo_asset_id_parent"
        and constraint["column_names"] == ["id", "parent_gallery_id"]
        for constraint in inspector.get_unique_constraints("photo_asset")
    )
    assert any(
        foreign_key["name"] == "fk_face_embedding_photo_parent"
        and foreign_key["constrained_columns"]
        == ["photo_asset_id", "parent_gallery_id"]
        for foreign_key in inspector.get_foreign_keys("photo_face_embedding")
    )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT filename FROM photo_asset WHERE id = :id"),
            {"id": photo_id.hex},
        ).scalar_one() == "foto.jpg"
        assert all(
            connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            == 0
            for table in facial_tables
        )

    alembic(database_url, "downgrade", "20260903_0042")
    inspector = inspect(engine)
    assert facial_tables.isdisjoint(inspector.get_table_names())
    assert not any(
        constraint["name"] == "uq_photo_asset_id_parent"
        for constraint in inspector.get_unique_constraints("photo_asset")
    )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT filename FROM photo_asset WHERE id = :id"),
            {"id": photo_id.hex},
        ).scalar_one() == "foto.jpg"


def test_facial_foundation_migration_upgrades_a_clean_database(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'facial-clean.sqlite').as_posix()}"
    alembic(database_url, "upgrade", "head")
    inspector = inspect(create_engine(database_url))
    assert "facial_search_request" in inspector.get_table_names()
    assert "facial_job" in inspector.get_table_names()


def test_layered_visual_protection_migration_preserves_existing_branding(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'layered-protection.sqlite').as_posix()}"
    alembic(database_url, "upgrade", "20260905_0043")
    engine = create_engine(database_url)
    branding_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO branding_settings "
                "(id, login_title, login_intro, login_helper, watermark_text, "
                "watermark_font, watermark_color, watermark_size, watermark_direction, updated_at) "
                "VALUES (:id, 'Título', 'Introdução', 'Ajuda', 'MARCA EXISTENTE', "
                "'sans-serif', '#FFFFFF', 24, 'diagonal', :updated_at)"
            ),
            {"id": branding_id.hex, "updated_at": datetime.now(UTC)},
        )

    alembic(database_url, "upgrade", "head")
    columns = {column["name"] for column in inspect(engine).get_columns("branding_settings")}
    assert {
        "watermark_opacity",
        "watermark_position",
        "watermark_shadow",
        "watermark_security_lines",
    } <= columns
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT watermark_text, watermark_opacity, watermark_position, "
                "watermark_shadow, watermark_security_lines FROM branding_settings WHERE id = :id"
            ),
            {"id": branding_id.hex},
        ).one()
    assert tuple(row) == ("MARCA EXISTENTE", 42, "middle-center", 1, 0)

    alembic(database_url, "downgrade", "20260905_0043")
    columns = {column["name"] for column in inspect(engine).get_columns("branding_settings")}
    assert "watermark_opacity" not in columns
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT watermark_text FROM branding_settings WHERE id = :id"),
            {"id": branding_id.hex},
        ).scalar_one() == "MARCA EXISTENTE"
