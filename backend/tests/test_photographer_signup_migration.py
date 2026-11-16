"""Upgrade real do baseline, reexecução e rollback que preserva histórico."""

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def test_0097_from_current_database_preserves_owner_audit_and_totp(postgres_schema, monkeypatch):
    engine = postgres_schema
    with engine.connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    monkeypatch.setenv("DATABASE_URL", engine.url.update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False))
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    command.upgrade(config, "20261026_0090")
    owner_id = uuid4()
    with engine.begin() as connection:
        tenant_id = connection.scalar(text("SELECT id FROM tenant"))
        connection.execute(text("INSERT INTO admin_user(id,email,password_hash,email_verified,totp_secret) VALUES (:id,'owner-signup-migration@example.test','synthetic',true,'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP')"), {"id": owner_id})
        connection.execute(text("INSERT INTO tenant_admin(id,tenant_id,admin_user_id,active,created_at) VALUES (:id,:tenant,:admin,true,CURRENT_TIMESTAMP)"), {"id": uuid4(), "tenant": tenant_id, "admin": owner_id})
        connection.execute(text("INSERT INTO platform_owner(singleton,admin_user_id,authorization_reference,established_at) VALUES (1,:admin,'synthetic',CURRENT_TIMESTAMP)"), {"admin": owner_id})
    command.upgrade(config, "20261103_0096")
    with engine.begin() as connection:
        assert "photographer_name" not in {item["name"] for item in inspect(connection).get_columns("tenant")}
        connection.execute(text("INSERT INTO audit_event(id,event,subject,created_at) VALUES (:id,'synthetic.legacy','sanitized',CURRENT_TIMESTAMP)"), {"id": uuid4()})
    for target in ("20261103_0097", "20261103_0097"):
        command.upgrade(config, target)
    command.downgrade(config, "20261103_0096")
    command.upgrade(config, "20261103_0097")
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT count(*) FROM tenant")) == 1
        assert connection.scalar(text("SELECT admin_user_id FROM platform_owner")) == owner_id
        assert connection.scalar(text("SELECT count(*) FROM audit_event")) == 1
        assert connection.scalar(text("SELECT totp_secret_envelope FROM admin_user" )).startswith("totp:v1:")
        assert connection.scalar(text("SELECT totp_secret FROM admin_user")) is None
        assert connection.scalar(text("SELECT photographer_name FROM tenant")) is None
        connection.execute(text("INSERT INTO photographer_signup(id,public_request_id,photographer_name,email,state,otp_expires_at,attempts,reserved_admin_id,reserved_tenant_id,created_at) VALUES (:id,:public,'Synthetic','candidate@example.test','email_pending',CURRENT_TIMESTAMP,0,:admin,:tenant,CURRENT_TIMESTAMP)"), {"id": uuid4(), "public": uuid4(), "admin": uuid4(), "tenant": uuid4()})
    with pytest.raises(RuntimeError, match="rollback com histórico recusado"):
        command.downgrade(config, "20261103_0096")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM photographer_signup")) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261103_0097"
