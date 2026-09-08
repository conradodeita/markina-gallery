"""Valida a migration aditiva do gate de calibração de produção."""

import os
import sys
from pathlib import Path
from subprocess import run

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


def test_calibration_migration_is_additive_empty_and_reversible(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'calibration.sqlite').as_posix()}"
    alembic(database_url, "upgrade", "20260908_0049")
    alembic(database_url, "upgrade", "head")
    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert "facial_calibration_approval" in inspector.get_table_names()
    columns = {
        column["name"]
        for column in inspector.get_columns("facial_calibration_approval")
    }
    assert {
        "environment",
        "model_version",
        "quality_version",
        "calibration_version",
        "similarity_threshold_milli",
        "criteria_version",
        "corpus_reference",
        "approval_reference",
        "relevant_group_count",
        "approved_group_count",
        "approved_by_admin_id",
        "status",
    }.issubset(columns)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM facial_calibration_approval")
        ).scalar_one() == 0
    alembic(database_url, "downgrade", "20260908_0049")
    assert "facial_calibration_approval" not in inspect(engine).get_table_names()
