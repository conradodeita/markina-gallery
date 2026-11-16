"""DDL real de 0096 e proteção do histórico em PostgreSQL descartável."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.auth import AdminUser, AuditEvent, Base, PlatformAdminEvent, Tenant, now
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def migration(connection):
    path = Path(__file__).parents[1] / "migrations/versions/20261103_0096_platform_admin_audit.py"
    spec = importlib.util.spec_from_file_location("platform_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    return module


def test_additive_upgrade_empty_rollback_and_reupgrade_preserve_legacy_audit(postgres_schema):
    engine = postgres_schema
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.tables.values()
                                           if table.name != "platform_admin_event"])
    with Session(engine) as db:
        db.add(AuditEvent(event="synthetic.legacy", subject="no-sensitive-payload"))
        db.commit()
    with engine.begin() as connection:
        module = migration(connection)
        module.upgrade()
        assert "platform_admin_event" in inspect(connection).get_table_names()
        module.downgrade()
        module.upgrade()
        assert connection.scalar(text("SELECT count(*) FROM audit_event WHERE event='synthetic.legacy'")) == 1
    with Session(engine) as db:
        tenant = Tenant()
        admin = AdminUser(email="migration@example.test", password_hash="synthetic",
                          totp_secret="synthetic", email_verified=True)
        db.add_all([tenant, admin])
        db.flush()
        # O teste de 0096 insere somente o contrato daquela revisão histórica.
        db.execute(text(
            "INSERT INTO platform_admin_event(id,actor_admin_id,tenant_id,action,result,origin,created_at) "
            "VALUES (:id,:admin,:tenant,'tenant.suspend','success','web_console',:instant)"
        ), {"id": uuid4(), "admin": admin.id, "tenant": tenant.id, "instant": now()})
        db.commit()
    for sql in ("UPDATE platform_admin_event SET result='denied'", "DELETE FROM platform_admin_event", "TRUNCATE platform_admin_event"):
        with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
            connection.execute(text(sql))
    with pytest.raises(RuntimeError, match="rollback recusado"), engine.begin() as connection:
        migration(connection).downgrade()
    with Session(engine) as db:
        assert db.scalar(select(PlatformAdminEvent.result)) == "success"
        assert db.scalar(select(AuditEvent.event)) == "synthetic.legacy"


def test_credit_audit_action_migration_accepts_new_events_and_guards_downgrade(postgres_schema):
    engine = postgres_schema
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE platform_admin_event (action varchar(40) NOT NULL, "
            "CONSTRAINT ck_platform_admin_action CHECK (action IN "
            "('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied',"
            "'photographer.totp_revoked','photographer.totp_revoke_denied','tenant.host_ready',"
            "'tenant.host_activation_denied','media_archive.recovery_pricing_updated','tenant.reopened',"
            "'tenant.media_deletion_requested','tenant.media_deletion_retry','tenant.profile_reduced')))"
        ))
        path = Path(__file__).parents[1] / "migrations/versions/20261113_0126_audit_owner_credit_mutations.py"
        spec = importlib.util.spec_from_file_location("credit_audit_migration", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        connection.execute(text("INSERT INTO platform_admin_event(action) VALUES ('credit.granted')"))
        with pytest.raises(RuntimeError, match="Preserve auditorias de concessão/revogação"):
            module.downgrade()
        connection.execute(text("DELETE FROM platform_admin_event"))
        module.downgrade()
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(text("INSERT INTO platform_admin_event(action) VALUES ('credit.revoked')"))
