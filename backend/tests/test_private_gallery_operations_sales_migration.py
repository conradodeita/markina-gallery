"""Valida a migration aditiva de operações completas da galeria privada."""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from subprocess import run
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text


def alembic(database_url: str, *arguments: str, succeeds: bool = True):
    backend = Path(__file__).resolve().parents[1]
    result = run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=backend,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
        check=False,
    )
    if succeeds:
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    else:
        assert result.returncode != 0
    return result


def test_private_operations_migration_is_additive_and_empty_downgrade_is_safe(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'private-operations.sqlite').as_posix()}"
    alembic(database_url, "upgrade", "20260908_0051")
    parent_id, folder_id, photo_id = (uuid4() for _ in range(3))
    instant = datetime.now(UTC)
    legacy_engine = create_engine(database_url)
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO parent_gallery (id, name, active, created_at) "
                "VALUES (:id, 'Evento preservado', 1, :created_at)"
            ),
            {"id": parent_id.hex, "created_at": instant},
        )
        connection.execute(
            text(
                "INSERT INTO photo_folder "
                "(id, parent_gallery_id, name, status, purpose, position, created_at, updated_at) "
                "VALUES (:id, :parent_id, 'Pública', 'released', 'content', 0, "
                ":created_at, :created_at)"
            ),
            {"id": folder_id.hex, "parent_id": parent_id.hex, "created_at": instant},
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
                "created_at": instant,
            },
        )
    alembic(database_url, "upgrade", "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert "derived_gallery_id" in {
        column["name"] for column in inspector.get_columns("photo_folder")
    }
    assert "derived_gallery_id" in {
        column["name"] for column in inspector.get_columns("photo_asset")
    }
    assert {
        "payment_confirmation_correction",
        "gallery_reopening_request",
        "gallery_reopening_notification_outbox",
    }.issubset(inspector.get_table_names())
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM payment_confirmation_correction")
        ).scalar_one() == 0
        legacy = connection.execute(
            text(
                "SELECT id, parent_gallery_id, folder_id, derived_gallery_id "
                "FROM photo_asset WHERE id = :id"
            ),
            {"id": photo_id.hex},
        ).one()
        assert legacy.id == photo_id.hex
        assert legacy.parent_gallery_id == parent_id.hex
        assert legacy.folder_id == folder_id.hex
        assert legacy.derived_gallery_id is None

    alembic(database_url, "downgrade", "20260908_0051")
    inspector = inspect(create_engine(database_url))
    assert "derived_gallery_id" not in {
        column["name"] for column in inspector.get_columns("photo_asset")
    }
    assert "gallery_reopening_request" not in inspector.get_table_names()
