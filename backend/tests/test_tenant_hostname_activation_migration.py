"""Migração aditiva do hash de evidência e das ações de hostname."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from app.auth import Base, now
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def apply_migration(connection, filename):
    path = Path(__file__).parents[1] / "migrations/versions" / filename
    spec = importlib.util.spec_from_file_location(f"migration_{filename[:8]}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    module.upgrade()
    return module


def insert_event(connection, *, admin_id, tenant_id, evidence=None, previous="reserved", next_status="ready"):
    connection.execute(text(
        "INSERT INTO platform_admin_event(id,actor_admin_id,tenant_id,object_id,action,previous_status,"
        "next_status,result,origin,created_at,reason_code,target_version,evidence_sha256) "
        "VALUES (:id,:admin,:tenant,:object,'tenant.host_ready',:previous,:next,'success','web_console',:instant,NULL,NULL,:evidence)"
    ), {"id": uuid4(), "admin": admin_id, "tenant": tenant_id, "object": tenant_id,
        "previous": previous, "next": next_status, "instant": now(), "evidence": evidence})


def test_upgrade_preserves_old_audit_and_downgrade_refuses_new_hostname_evidence(postgres_schema):
    engine = postgres_schema
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.tables.values()
                                           if table.name != "platform_admin_event"])
    with engine.begin() as connection:
        apply_migration(connection, "20261103_0096_platform_admin_audit.py")
        apply_migration(connection, "20261104_0102_photographer_totp_assistance.py")
        admin_id, tenant_id = uuid4(), uuid4()
        connection.execute(text(
            "INSERT INTO admin_user(id,email,password_hash,email_verified,totp_enabled,totp_secret,totp_secret_envelope) "
            "VALUES (:id,'migration@example.test','synthetic',true,false,NULL,NULL)"
        ), {"id": admin_id})
        connection.execute(text("INSERT INTO tenant(id,status,created_at) VALUES (:id,'active',:instant)"),
                           {"id": tenant_id, "instant": now()})
        connection.execute(text(
            "INSERT INTO platform_admin_event(id,actor_admin_id,tenant_id,object_id,action,result,origin,created_at) "
            "VALUES (:id,:admin,:tenant,:object,'tenant.suspend','success','web_console',:instant)"
        ), {"id": uuid4(), "admin": admin_id, "tenant": tenant_id, "object": tenant_id, "instant": now()})
        module = apply_migration(connection, "20261107_0107_tenant_hostname_activation_audit.py")
        assert "evidence_sha256" in {column["name"] for column in inspect(connection).get_columns("platform_admin_event")}
        assert connection.scalar(text("SELECT count(*) FROM platform_admin_event WHERE action='tenant.suspend'")) == 1
        module.downgrade()
        assert "evidence_sha256" not in {column["name"] for column in inspect(connection).get_columns("platform_admin_event")}
        assert connection.scalar(text("SELECT count(*) FROM platform_admin_event WHERE action='tenant.suspend'")) == 1
        module.upgrade()
        for invalid in ({"evidence": "x" * 64}, {"evidence": None},
                        {"evidence": "a" * 64, "previous": None},
                        {"evidence": "a" * 64, "next_status": None}):
            with pytest.raises(DBAPIError), connection.begin_nested():
                insert_event(connection, admin_id=admin_id, tenant_id=tenant_id,
                             **invalid)
        connection.execute(text(
            "INSERT INTO platform_admin_event(id,actor_admin_id,tenant_id,object_id,action,result,origin,created_at) "
            "VALUES (:id,:admin,:tenant,:object,'tenant.host_activation_denied','denied','web_console',:instant)"
        ), {"id": uuid4(), "admin": admin_id, "tenant": tenant_id, "object": tenant_id, "instant": now()})
        with pytest.raises(RuntimeError, match="rollback recusado"):
            module.downgrade()
        # Hash sintético de 64 dígitos hex atende às constraints de produção.
        insert_event(connection, admin_id=admin_id, tenant_id=tenant_id,
                     evidence="a" * 64)
        for sql in ("UPDATE platform_admin_event SET result='denied' WHERE action='tenant.host_ready'",
                    "DELETE FROM platform_admin_event WHERE action='tenant.host_ready'",
                    "TRUNCATE platform_admin_event"):
            with pytest.raises(DBAPIError, match="append-only"), connection.begin_nested():
                connection.execute(text(sql))
        with pytest.raises(RuntimeError, match="rollback recusado"):
            module.downgrade()
        assert connection.scalar(text("SELECT count(*) FROM platform_admin_event WHERE action='tenant.host_ready' AND evidence_sha256=:hash"),
                                 {"hash": "a" * 64}) == 1
