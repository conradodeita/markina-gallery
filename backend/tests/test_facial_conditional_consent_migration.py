"""Migração aditiva do recibo de consentimento condicional."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

from tests.tenant_fixtures import LEGACY_SCHEMA_HEAD


def test_conditional_consent_migration_preserves_existing_declarations(tmp_path):
    root = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{(tmp_path / 'conditional-consent.db').as_posix()}"
    env = {**os.environ, "DATABASE_URL": database_url}

    def migrate(revision):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=root, env=env, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout

    migrate(LEGACY_SCHEMA_HEAD)
    migrate("20261016_0082")
    engine = create_engine(database_url)
    constraints = inspect(engine).get_check_constraints("facial_search_request")
    declaration = next(item for item in constraints if item["name"] == "ck_facial_search_subject_declaration")
    assert "adult" in declaration["sqltext"]
    assert "minor" in declaration["sqltext"]
    assert "conditional" in declaration["sqltext"]
    engine.dispose()
