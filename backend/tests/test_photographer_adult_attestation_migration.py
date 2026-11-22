"""Migration aditiva da declaração de maioridade em PostgreSQL sintético."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from tests.test_photographer_onboarding_migration import _demo_helpers
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def test_0109_adds_attestation_and_refuses_to_drop_recorded_declarations(postgres_schema, monkeypatch):
    engine = postgres_schema
    with engine.connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    monkeypatch.setenv("DATABASE_URL", engine.url.update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False))
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    command.upgrade(config, "20261026_0090")
    _demo_helpers().create_synthetic_owner(
        engine.url.update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False)
    )
    command.upgrade(config, "20261107_0108")
    assert "adult_attested_at" not in {column["name"] for column in inspect(engine).get_columns("photographer_signup")}

    signup_id, request_id, admin_id, tenant_id = uuid4(), uuid4(), uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO photographer_signup(id,public_request_id,photographer_name,email,state,otp_expires_at,"
            "attempts,reserved_admin_id,reserved_tenant_id,created_at) VALUES "
            "(:id,:request,'Synthetic','adult@example.test','email_pending',CURRENT_TIMESTAMP,0,:admin,:tenant,CURRENT_TIMESTAMP)"
        ), {"id": signup_id, "request": request_id, "admin": admin_id, "tenant": tenant_id})
    command.upgrade(config, "20261107_0109")
    assert "adult_attested_at" in {column["name"] for column in inspect(engine).get_columns("photographer_signup")}
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT adult_attested_at FROM photographer_signup WHERE id=:id"), {"id": signup_id}) is None
        connection.execute(text("UPDATE photographer_signup SET adult_attested_at=:at WHERE id=:id"),
                           {"at": datetime.now(timezone.utc), "id": signup_id})  # noqa: UP017 - Python 3.10 runtime compatibility
    with pytest.raises(RuntimeError, match="Preserve declarações"):
        command.downgrade(config, "20261107_0108")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT adult_attested_at FROM photographer_signup WHERE id=:id"), {"id": signup_id}) is not None
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261107_0109"
