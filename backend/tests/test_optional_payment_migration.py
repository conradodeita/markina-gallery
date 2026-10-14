"""Upgrade aditivo preserva configurações e aceita finalização externa."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text

from tests.tenant_fixtures import LEGACY_SCHEMA_HEAD
from tests.test_gallery_client_audience_migration import _alembic


@pytest.mark.parametrize("kind", ["sqlite", "postgres"])
def test_optional_payment_upgrade(tmp_path, kind):
    url = f"sqlite:///{(tmp_path / 'optional.sqlite').as_posix()}" if kind == "sqlite" else os.getenv("TEST_POSTGRES_DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL descartável não configurado")
    _alembic(url, "upgrade", "20260927_0066")
    engine = create_engine(url)
    gallery_id = uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO parent_gallery (id, name, active, created_at) "
            "VALUES (:id, 'Legado', true, CURRENT_TIMESTAMP)"
        ), {"id": gallery_id})
    engine.dispose()
    _alembic(url, "upgrade", LEGACY_SCHEMA_HEAD)
    engine = create_engine(url)
    with engine.connect() as connection:
        assert bool(connection.execute(text(
            "SELECT payment_required FROM parent_gallery WHERE id = :id"
        ), {"id": gallery_id}).scalar())
    assert "payment_required_snapshot" in {column["name"] for column in inspect(engine).get_columns("sale_order")}
    assert any("not_required" in item["sqltext"] for item in inspect(engine).get_check_constraints("sale_order"))
    with engine.begin() as connection:
        connection.execute(text("UPDATE parent_gallery SET payment_required = false WHERE id = :id"), {"id": gallery_id})
    engine.dispose()
    with pytest.raises(AssertionError, match="downgrade com dados externos recusado"):
        _alembic(url, "downgrade", "20260927_0066")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("UPDATE parent_gallery SET payment_required = true WHERE id = :id"), {"id": gallery_id})
    engine.dispose()
    _alembic(url, "downgrade", "20260927_0066")
