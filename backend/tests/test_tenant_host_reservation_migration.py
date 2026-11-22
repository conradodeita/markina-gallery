"""DDL PostgreSQL isolado: legado preservado e downgrade sem perda de reservas."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def test_host_state_additive_upgrade_and_preserving_rollback(postgres_schema):
    with postgres_schema.begin() as connection:
        connection.execute(text(
            "CREATE TABLE tenant(id uuid PRIMARY KEY, canonical_host varchar(253) UNIQUE)"
        ))
        owner = uuid4()
        connection.execute(text("INSERT INTO tenant VALUES (:id, 'markina.pickyourpic.com.br')"), {"id": owner})
        path = Path(__file__).parents[1] / "migrations/versions/20261105_0105_tenant_host_reservation.py"
        spec = importlib.util.spec_from_file_location("host_state_migration", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        assert connection.scalar(text("SELECT canonical_host_status FROM tenant WHERE id=:id"), {"id": owner}) is None
        module.downgrade()
        assert "canonical_host_status" not in {column["name"] for column in inspect(connection).get_columns("tenant")}
        module.upgrade()
        assert connection.scalar(text("SELECT canonical_host FROM tenant WHERE id=:id"), {"id": owner}) == "markina.pickyourpic.com.br"
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("INSERT INTO tenant(id,canonical_host_status) VALUES (:id,'reserved')"), {"id": uuid4()})
        connection.execute(text(
            "INSERT INTO tenant(id,canonical_host,canonical_host_status) VALUES (:id,'chosen.pickyourpic.com.br','reserved')"
        ), {"id": uuid4()})
        with pytest.raises(RuntimeError, match="Preserve reservas"):
            module.downgrade()
        assert connection.scalar(text("SELECT count(*) FROM tenant WHERE canonical_host_status='reserved'")) == 1
