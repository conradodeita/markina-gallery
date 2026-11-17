import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, make_url, text

from app import schema_revision_check
from app.schema_revision_check import revisions_match


def _script(*heads: str) -> SimpleNamespace:
    return SimpleNamespace(get_heads=lambda: heads)


def test_schema_revision_check_is_read_only_at_head() -> None:
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('revision_a')"))
        connection.commit()
        connection.execute(text("PRAGMA query_only = ON"))

        assert revisions_match(connection, _script("revision_a")) == (
            True,
            "schema compatível: revision_a",
        )
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "revision_a"


def test_schema_revision_check_fails_closed_on_missing_or_old_revision() -> None:
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        connection.execute(text("PRAGMA query_only = ON"))
        assert revisions_match(connection, _script("revision_a"))[0] is False
        connection.execute(text("PRAGMA query_only = OFF"))
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('revision_a')"))
        connection.commit()
        connection.execute(text("PRAGMA query_only = ON"))
        assert revisions_match(connection, _script("revision_b"))[0] is False
        assert revisions_match(connection, _script("revision_a", "revision_b"))[0] is False
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "revision_a"


def test_default_command_checks_real_code_head_without_upgrading(tmp_path, monkeypatch, capsys) -> None:
    db_path = tmp_path / "schema.sqlite"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('revision_a')"))
    monkeypatch.setattr(schema_revision_check, "database_url", lambda: url)

    assert schema_revision_check.main() == 1
    assert "difere da head" in capsys.readouterr().out
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "revision_a"

    root = Path(schema_revision_check.__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    head = ScriptDirectory.from_config(config).get_current_head()
    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = :head"), {"head": head})
    assert schema_revision_check.main() == 0
    assert f"schema compatível: {head}" in capsys.readouterr().out
    engine.dispose()


def test_postgres_schema_revision_check_in_read_only_transaction() -> None:
    raw = os.getenv("SCHEMA_GATE_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Requer PostgreSQL local descartável exclusivo")
    url = make_url(raw)
    if (url.get_backend_name(), url.host, url.port, url.database) != (
        "postgresql",
        "127.0.0.1",
        15471,
        "pyp_schema_gate_test",
    ):
        pytest.fail("DDL permitido somente em 127.0.0.1:15471/pyp_schema_gate_test")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(text("INSERT INTO alembic_version VALUES ('revision_a')"))
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            assert revisions_match(connection, _script("revision_a"))[0] is True
            assert revisions_match(connection, _script("revision_b"))[0] is False
            connection.rollback()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "revision_a"
    finally:
        engine.dispose()
