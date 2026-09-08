"""Valida a migration aditiva do rollout facial persistente."""

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


def test_rollout_migration_is_additive_and_reversible(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'rollout-existing.sqlite').as_posix()}"
    alembic(database_url, "upgrade", "20260907_0047")
    engine = create_engine(database_url)
    gallery_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO parent_gallery (id, name, active, created_at) "
                "VALUES (:id, 'Evento preservado', 1, :created_at)"
            ),
            {"id": gallery_id.hex, "created_at": datetime.now(UTC)},
        )

    alembic(database_url, "upgrade", "head")
    inspector = inspect(engine)
    assert "facial_rollout" in inspector.get_table_names()
    assert any(
        constraint["name"] == "uq_facial_rollout_environment_gallery"
        and constraint["column_names"] == ["environment", "parent_gallery_id"]
        for constraint in inspector.get_unique_constraints("facial_rollout")
    )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT name FROM parent_gallery WHERE id = :id"),
            {"id": gallery_id.hex},
        ).scalar_one() == "Evento preservado"
        assert connection.execute(text("SELECT COUNT(*) FROM facial_rollout")).scalar_one() == 0

    alembic(database_url, "downgrade", "20260907_0047")
    assert "facial_rollout" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT name FROM parent_gallery WHERE id = :id"),
            {"id": gallery_id.hex},
        ).scalar_one() == "Evento preservado"


def test_rollout_migration_upgrades_clean_database_without_activation(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'rollout-clean.sqlite').as_posix()}"
    alembic(database_url, "upgrade", "head")
    engine = create_engine(database_url)
    assert "facial_rollout" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM facial_rollout")).scalar_one() == 0
