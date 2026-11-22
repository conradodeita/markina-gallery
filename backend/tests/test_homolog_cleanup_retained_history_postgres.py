"""A limpeza legada não alcança arquivo/encerramento nem corre com inserções."""

from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth import PhotographerCreditEntry, Tenant, TenantClosureRequest, now
from app.homolog_cleanup import CONFIRMATION, execute
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema
from tests.test_tenant_media_deletion_migration import _upgrade_with_owner

postgres_schema = _postgres_schema


@pytest.mark.parametrize("history", ["closure", "credit"])
def test_retained_history_blocks_cleanup_and_serializes_new_records(monkeypatch, postgres_schema, history):
    engine = postgres_schema
    _upgrade_with_owner(monkeypatch, engine, "head")
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setattr("app.homolog_cleanup.media_roots", lambda: pytest.fail("Não acessar mídia"))
    with engine.begin() as connection:
        owner_id = connection.scalar(text("SELECT admin_user_id FROM platform_owner"))
        tenant_id = connection.scalar(text("SELECT tenant_id FROM tenant_admin WHERE admin_user_id=:owner"),
                                      {"owner": owner_id})
    with Session(engine) as db:
        record = TenantClosureRequest(
            tenant_id=tenant_id, requested_by=owner_id, request_id=uuid4(),
            terms_version="synthetic", terms_sha256="a" * 64, balance_snapshot=0,
        ) if history == "closure" else PhotographerCreditEntry(
            tenant_id=tenant_id, entry_type="owner_grant", delta=20,
            idempotency_key="synthetic-legacy-cleanup-credit-guard",
            global_owner_admin_id=owner_id, description="Concessão sintética",
        )
        db.add(record)
        db.commit()
        record_id = record.id
        message = "histórico de arquivo e encerramento" if history == "closure" else "histórico de créditos"
        with pytest.raises(RuntimeError, match=message):
            execute(db, CONFIRMATION)
        # O erro conserva a transação/locks até o caller efetuar rollback.
        with engine.connect() as concurrent:
            with pytest.raises(OperationalError) as blocked, concurrent.begin():
                concurrent.execute(text("SET LOCAL lock_timeout = '150ms'"))
                concurrent.execute(text(
                    "INSERT INTO tenant_closure_request "
                    "(id,tenant_id,request_id,requested_by,state,requested_at,closed_at,"
                    "terms_version,terms_sha256,balance_snapshot,balance_acknowledged) "
                    "VALUES (:id,:tenant,:request,:owner,'closed',:at,:at,'synthetic',:hash,0,true)"
                ), {"id": uuid4(), "tenant": tenant_id, "request": uuid4(), "owner": owner_id,
                    "at": now(), "hash": "b" * 64})
            assert blocked.value.orig.sqlstate == "55P03"
        db.rollback()
        assert db.get(type(record), record_id) is not None
        assert db.scalar(select(Tenant.id)) == tenant_id
