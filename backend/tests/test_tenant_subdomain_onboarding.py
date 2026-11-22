"""Reserva por sessão real de signup, namespace único e disputa PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth import (
    AdminUser,
    AuditEvent,
    Client,
    PhotographerSignup,
    Role,
    Tenant,
    TenantAdmin,
    create_session,
)
from app.photographer_subdomain import RESERVED_PREFIXES, normalize_prefix
from app.system_monitor.models import PlatformOwner
from tests.test_photographer_signup import finish, start, verify
from tests.test_photographer_signup import proof as _proof
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
proof = _proof
ADDRESS = "/api/admin/onboarding/address"


def account(client, messages, suffix):
    client.cookies.clear()
    setup = verify(client, messages, start(client, name=f"Fotógrafa {suffix}", email=f"{suffix}@example.test"))
    assert finish(client, setup).status_code == 200
    return client.get("/api/probe-admin").json(), dict(client.cookies)


def test_reserve_idempotence_own_state_and_no_cross_tenant_reassignment(proof, client_db):
    client, messages = proof
    first, cookies_a = account(client, messages, "address-a")
    initial = client.get(ADDRESS)
    assert initial.status_code == 200 and "no-store" in initial.headers["cache-control"]
    assert initial.json()["state"] == "unselected"
    assert initial.json()["suggested_prefix"] == "fotografa-address-a"
    selected = client.put(ADDRESS, json={"prefix": "  Minha-Marca  "},
                          headers={"X-Forwarded-Host": "attacker.invalid"})
    assert selected.status_code == 200
    assert selected.json()["hostname"] == "minha-marca.pickyourpic.com.br"
    assert selected.json()["state"] == "reserved" and selected.json()["public_url"] is None
    assert client.put(ADDRESS, json={"prefix": "MINHA-MARCA"}).json() == selected.json()
    assert client.put(ADDRESS, json={"prefix": "different"}).status_code == 409
    second, _ = account(client, messages, "address-b")
    conflict = client.put(ADDRESS, json={"prefix": "minha-marca"})
    assert conflict.status_code == 409
    assert first["subject_id"] not in conflict.text and "address-a" not in conflict.text
    assert client.get(ADDRESS).json()["state"] == "unselected"
    assert client.put(ADDRESS, json={"prefix": "second-brand"}).status_code == 200
    client.cookies.clear()
    client.cookies.update(cookies_a)
    assert client.get(ADDRESS).json() == selected.json()
    client_db.expire_all()
    assert client_db.get(Tenant, UUID(first["tenant_id"])).canonical_host_status == "reserved"
    assert client_db.get(Tenant, UUID(second["tenant_id"])).canonical_host == "second-brand.pickyourpic.com.br"
    assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.event == "photographer_subdomain.reserved",
        AuditEvent.tenant_id == UUID(first["tenant_id"]),
    )) == 1


def test_context_csrf_validation_and_owner_preservation(proof, client_db):
    client, messages = proof
    assert client.get(ADDRESS).status_code == 403
    identity, _cookies = account(client, messages, "address-auth")
    assert client.put(ADDRESS, json={"prefix": "brand"}, headers={"Origin": "https://evil.invalid"}).status_code == 403
    for payload in ({"prefix": "brand", "tenant_id": identity["tenant_id"]},
                    {"prefix": "brand", "state": "ready"}, {"prefix": 123}):
        assert client.put(ADDRESS, json=payload).status_code == 422
    tenant = client_db.get(Tenant, UUID(identity["tenant_id"]))
    admin = client_db.get(AdminUser, UUID(identity["subject_id"]))
    admin.email_verified = False
    client_db.commit()
    assert client.get(ADDRESS).status_code == 403
    admin.email_verified = True
    tenant.status = "suspended"
    client_db.commit()
    assert client.put(ADDRESS, json={"prefix": "brand"}).status_code == 403
    tenant.status = "active"
    client_db.commit()
    membership = client_db.scalar(select(TenantAdmin).where(TenantAdmin.tenant_id == tenant.id))
    membership.active = False
    client_db.commit()
    assert client.get(ADDRESS).status_code == 403
    membership.active = True
    client_db.add(PlatformOwner(singleton=1, admin_user_id=admin.id, authorization_reference="synthetic-only"))
    client_db.commit()
    assert client.get(ADDRESS).status_code == 403
    assert client.put(ADDRESS, json={"prefix": "brand"}).status_code == 403
    assert client_db.get(Tenant, tenant.id).canonical_host is None


def test_legacy_and_existing_host_are_never_overwritten(proof, client_db):
    client, messages = proof
    identity, _ = account(client, messages, "legacy-host")
    tenant = client_db.get(Tenant, UUID(identity["tenant_id"]))
    tenant.canonical_host = "preserved.pickyourpic.com.br"
    client_db.commit()
    assert client.get(ADDRESS).json()["state"] == "ready"
    assert client.put(ADDRESS, json={"prefix": "new-name"}).status_code == 409
    signup = client_db.scalar(select(PhotographerSignup).where(PhotographerSignup.activated_tenant_id == tenant.id))
    signup.state = "expired"
    client_db.commit()
    assert client.get(ADDRESS).status_code == 403
    client_db.expire_all()
    assert client_db.get(Tenant, tenant.id).canonical_host == "preserved.pickyourpic.com.br"


def test_client_session_cannot_read_or_reserve_photographer_host(proof, client_db):
    client, messages = proof
    identity, _ = account(client, messages, "address-client")
    customer = Client(tenant_id=UUID(identity["tenant_id"]), full_name="Cliente sintética",
                      phone_e164="+5511999990001")
    client_db.add(customer)
    client_db.flush()
    token = create_session(client_db, Response(), Role.CLIENT, customer.id, tenant_id=customer.tenant_id)
    client_db.commit()
    client.cookies.clear()
    client.cookies.set("markina_session", token)
    assert client.get(ADDRESS).status_code == 403
    assert client.put(ADDRESS, json={"prefix": "cannot-reserve"}).status_code == 403
    client_db.expire_all()
    assert client_db.get(Tenant, customer.tenant_id).canonical_host is None


@pytest.mark.parametrize("prefix", ["", "a" * 64, "á", "K", "my brand", "-bad", "bad-", "a.b", "xn--brand",
                                      "a/b", "x:443", "user@host", "a_b", "https://evil.invalid"])
def test_invalid_prefix_is_rejected(prefix):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        normalize_prefix(prefix)
    assert error.value.status_code == 422


def test_infrastructure_names_are_reserved():
    from fastapi import HTTPException
    for prefix in RESERVED_PREFIXES:
        with pytest.raises(HTTPException) as error:
            normalize_prefix(prefix.upper())
        assert error.value.status_code == 409
    assert normalize_prefix(" A ") == "a"
    assert len(normalize_prefix("a" * 63)) == 63


@pytest.mark.parametrize("same_tenant", [False, True])
def test_competing_claims_have_one_winner_in_postgres(proof, client_db, same_tenant):
    if client_db.bind.dialect.name != "postgresql":
        pytest.skip("Concorrência requer PostgreSQL local sintético")
    client, messages = proof
    _first, cookies_a = account(client, messages, "race-a")
    if same_tenant:
        cookies_b = cookies_a
    else:
        _second, cookies_b = account(client, messages, "race-b")
    client_db.commit()
    barrier = Barrier(2)

    def claim(index):
        with TestClient(client.app) as parallel:
            parallel.cookies.update(cookies_a if index == 0 else cookies_b)
            barrier.wait(timeout=10)
            prefix = f"racing-{index}" if same_tenant else "racing-name"
            return parallel.put(ADDRESS, json={"prefix": prefix}).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(claim, range(2))) == [200, 409]
    client_db.expire_all()
    assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.event == "photographer_subdomain.reserved",
    )) == 1
    assert client_db.scalar(select(func.count()).select_from(Tenant).where(Tenant.canonical_host_status == "reserved")) == 1
