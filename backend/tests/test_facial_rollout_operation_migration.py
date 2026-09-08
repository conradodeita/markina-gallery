"""Valida a migration aditiva do recibo protegido de rollout facial."""

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


def test_rollout_operation_migration_is_additive_empty_and_reversible(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'rollout-operation.sqlite').as_posix()}"
    alembic(database_url, "upgrade", "20260908_0050")
    alembic(database_url, "upgrade", "head")
    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert "facial_rollout_operation" in inspector.get_table_names()
    columns = {
        column["name"]
        for column in inspector.get_columns("facial_rollout_operation")
    }
    assert {
        "environment",
        "action",
        "stage",
        "deployment_sha",
        "inventory_reference",
        "backup_reference",
        "gate_set_version",
        "allowlist_digest",
        "allowlist_count",
        "approved_by_admin_id",
        "completed_at",
    }.issubset(columns)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM facial_rollout_operation")
        ).scalar_one() == 0
    alembic(database_url, "downgrade", "20260908_0050")
    assert "facial_rollout_operation" not in inspect(engine).get_table_names()
