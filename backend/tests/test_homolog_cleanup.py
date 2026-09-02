from pathlib import Path

import pytest

from app.auth import SessionLocal
from app.homolog_cleanup import CONFIRMATION, execute, inventory


def test_inventory_requires_homolog_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    with SessionLocal() as db, pytest.raises(RuntimeError, match="homologação"):
        inventory(db)


def test_inventory_returns_only_counts_without_pii(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(tmp_path / "history"))
    for name in ("source", "derivatives", "history"):
        (tmp_path / name).mkdir()
    with SessionLocal() as db:
        result = inventory(db)
    assert result["environment"] == "homolog"
    assert set(result) == {"environment", "database", "media"}
    assert "phone" not in str(result).lower()


def test_execute_requires_literal_confirmation_before_database_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "homologation")
    with SessionLocal() as db, pytest.raises(RuntimeError, match="Confirmação literal"):
        execute(db, "invalid")


def test_execute_rejects_non_postgresql_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    with SessionLocal() as db, pytest.raises(RuntimeError, match="PostgreSQL exclusivo"):
        execute(db, CONFIRMATION)
