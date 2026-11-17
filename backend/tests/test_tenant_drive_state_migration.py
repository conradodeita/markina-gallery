"""Capacidade do estado Drive e rollback preservador em PostgreSQL sintético."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def test_state_upgrade_preserves_data_and_refuses_lossy_downgrade(postgres_schema):
    path = Path(__file__).parents[1] / "migrations/versions/20261107_0108_google_drive_connection_state_capacity.py"
    spec = importlib.util.spec_from_file_location("drive_state_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with postgres_schema.begin() as connection:
        connection.execute(text(
            "CREATE TABLE google_drive_connection (id uuid PRIMARY KEY, state varchar(16) NOT NULL, "
            "refresh_token_envelope jsonb NOT NULL, "
            "CONSTRAINT ck_google_drive_connection_state CHECK "
            "(state IN ('connected','revoked','reauthorization_required')))"
        ))
        identity = uuid4()
        connection.execute(text(
            "INSERT INTO google_drive_connection VALUES (:id,'connected','{\"ciphertext\":\"synthetic\"}')"
        ), {"id": identity})
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        module.downgrade()
        module.upgrade()
        columns = {column['name']: column for column in inspect(connection).get_columns('google_drive_connection')}
        assert columns['state']['type'].length == 32
        connection.execute(text(
            "UPDATE google_drive_connection SET state='reauthorization_required' WHERE id=:id"
        ), {"id": identity})
        with pytest.raises(RuntimeError, match="rollback recusado"):
            module.downgrade()
        row = connection.execute(text("SELECT id,state,refresh_token_envelope FROM google_drive_connection")).one()
        assert row.id == identity and row.state == 'reauthorization_required'
        assert row.refresh_token_envelope == {'ciphertext': 'synthetic'}


def test_linear_chain_reaches_0108_with_synthetic_owner(monkeypatch, postgres_schema):
    from tests.test_photographer_onboarding_migration import _config, _demo_helpers

    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, scoped_url = _config(monkeypatch, postgres_schema)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(scoped_url)
    command.upgrade(config, "20261107_0108")
    with postgres_schema.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261107_0108"
        assert connection.scalar(text("SELECT count(*) FROM admin_user")) == 1
        columns = {column['name']: column for column in inspect(connection).get_columns('google_drive_connection')}
        assert columns['state']['type'].length == 32
