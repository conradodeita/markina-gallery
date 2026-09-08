"""Valida a migration aditiva da representação legal facial minimizada."""

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


def test_representation_migration_is_additive_and_reversible(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'representation-existing.sqlite').as_posix()}"
    alembic(database_url, "upgrade", "20260908_0048")
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
    assert "facial_legal_representation" in inspector.get_table_names()
    columns = {
        column["name"]
        for column in inspector.get_columns("facial_legal_representation")
    }
    assert {
        "client_id",
        "parent_gallery_id",
        "subject_scope_reference",
        "authority_kind",
        "verification_method",
        "terms_version",
        "evidence_reference",
        "verified_by_admin_id",
        "valid_from",
        "expires_at",
        "revoked_at",
    }.issubset(columns)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT name FROM parent_gallery WHERE id = :id"),
            {"id": gallery_id.hex},
        ).scalar_one() == "Evento preservado"
        assert connection.execute(
            text("SELECT COUNT(*) FROM facial_legal_representation")
        ).scalar_one() == 0

    alembic(database_url, "downgrade", "20260908_0048")
    assert "facial_legal_representation" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT name FROM parent_gallery WHERE id = :id"),
            {"id": gallery_id.hex},
        ).scalar_one() == "Evento preservado"


def test_representation_migration_upgrades_clean_database_without_backfill(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'representation-clean.sqlite').as_posix()}"
    alembic(database_url, "upgrade", "head")
    engine = create_engine(database_url)
    assert "facial_legal_representation" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM facial_legal_representation")
        ).scalar_one() == 0
