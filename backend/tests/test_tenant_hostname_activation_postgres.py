"""Ativação concorrente de hostname em PostgreSQL sintético e isolado."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pyotp
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker

from app.auth import AdminUser, Base, PlatformAdminEvent, Tenant, password_hasher
from app.platform_console import HostnameActivationInput, activate_tenant_hostname
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema
PASSWORD = "SyntheticHostnameOwner!2026"
SECRET = "JBSWY3DPEHPK3PXP"
EVIDENCE = sha256(b"synthetic readiness report").hexdigest()


@pytest.fixture
def activation_context(postgres_schema):
    Base.metadata.create_all(postgres_schema)
    factory = sessionmaker(bind=postgres_schema, expire_on_commit=False)
    with factory.begin() as db:
        owner_tenant, target, owner, _photographer = create_accounts(db)
        owner.password_hash = password_hasher.hash(PASSWORD)
        owner.totp_secret = SECRET
        target.canonical_host = "first.pickyourpic.com.br"
        target.canonical_host_status = "reserved"
        actor = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
        target_id = target.id
    return factory, actor, target_id


def intention(hostname, *, request_id=None, code=None):
    return HostnameActivationInput(
        request_id=request_id or uuid4(), expected_hostname=hostname, expected_status="reserved",
        evidence_sha256=EVIDENCE, confirm_readiness=True, current_password=PASSWORD,
        totp_code=code or pyotp.TOTP(SECRET).now(),
    )


def test_same_intent_is_applied_once_under_concurrent_replay(activation_context):
    factory, actor, target_id = activation_context
    payload = intention("first.pickyourpic.com.br")
    gate = Barrier(2)

    def attempt(_index):
        with factory() as db:
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            gate.wait(timeout=10)
            result = activate_tenant_hostname(db, actor, target_id, payload)
            db.commit()
            return result["replayed"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (0, 1)))
    assert sorted(results) == [False, True]
    with factory() as db:
        assert db.get(Tenant, target_id).canonical_host_status == "ready"
        assert db.scalar(select(func.count()).select_from(PlatformAdminEvent)) == 1
        event = db.scalar(select(PlatformAdminEvent))
        assert event.request_id == payload.request_id and event.evidence_sha256 == EVIDENCE


def test_one_totp_step_cannot_activate_two_tenants_with_preloaded_owner(activation_context):
    factory, actor, first_id = activation_context
    with factory.begin() as db:
        second = Tenant(canonical_host="second.pickyourpic.com.br", canonical_host_status="reserved")
        db.add(second)
        db.flush()
        second_id = second.id
    code = pyotp.TOTP(SECRET).now()
    payloads = [(first_id, intention("first.pickyourpic.com.br", code=code)),
                (second_id, intention("second.pickyourpic.com.br", code=code))]
    gate = Barrier(2)

    def attempt(target):
        target_id, payload = target
        with factory() as db:
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            preloaded_owner = db.get(AdminUser, actor.subject_id)
            assert preloaded_owner.totp_last_used_step is None
            gate.wait(timeout=10)
            try:
                activate_tenant_hostname(db, actor, target_id, payload)
                db.commit()
                return 200
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, payloads))
    assert sorted(results) == [200, 403]
    with factory() as db:
        states = [db.get(Tenant, target_id).canonical_host_status for target_id in (first_id, second_id)]
        assert sorted(states) == ["ready", "reserved"]
        assert db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
            PlatformAdminEvent.action == "tenant.host_ready",
        )) == 1
        assert db.get(AdminUser, actor.subject_id).totp_last_used_step is not None
