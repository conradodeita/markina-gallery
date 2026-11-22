"""Uma reserva não concede host nem links; contratos legados permanecem iguais."""

from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request

from app import auth
from app.auth import AdminUser, Client, Role, Tenant, TenantAdmin, create_session, current_session
from app.tenant_hosts import (
    CanonicalHostError,
    canonical_host_for_tenant,
    public_gallery_url_for_tenant,
    purchase_url_for_tenant,
    tenant_for_host,
)
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


def test_reserved_host_never_resolves_or_generates_links(client_db):
    tenant = Tenant(canonical_host="chosen.pickyourpic.com.br", canonical_host_status="reserved")
    client_db.add(tenant)
    client_db.commit()
    assert tenant_for_host(client_db, tenant.canonical_host) is None
    assert tenant_for_host(client_db, "unknown.pickyourpic.com.br") is None
    with pytest.raises(CanonicalHostError):
        canonical_host_for_tenant(client_db, tenant)
    for generator in (purchase_url_for_tenant, public_gallery_url_for_tenant):
        with pytest.raises(CanonicalHostError):
            generator(client_db, tenant, uuid4())


@pytest.mark.parametrize("host_state", [None, "ready"])
def test_legacy_and_ready_host_contract_is_preserved(client_db, host_state):
    tenant = Tenant(canonical_host="existing.pickyourpic.com.br", canonical_host_status=host_state)
    client_db.add(tenant)
    client_db.commit()
    assert tenant_for_host(client_db, tenant.canonical_host).id == tenant.id
    assert canonical_host_for_tenant(client_db, tenant) == tenant.canonical_host
    tenant.status = "suspended"
    client_db.commit()
    assert tenant_for_host(client_db, tenant.canonical_host) is None


def test_reservation_uses_same_unique_namespace_as_existing_hosts(client_db):
    client_db.add(Tenant(canonical_host="existing.pickyourpic.com.br"))
    client_db.commit()
    client_db.add(Tenant(canonical_host="existing.pickyourpic.com.br", canonical_host_status="reserved"))
    with pytest.raises(IntegrityError):
        client_db.commit()
    client_db.rollback()


def test_reservation_requires_host_and_known_state(client_db):
    client_db.add(Tenant(canonical_host_status="reserved"))
    with pytest.raises(IntegrityError):
        client_db.commit()
    client_db.rollback()
    client_db.add(Tenant(canonical_host="existing.pickyourpic.com.br", canonical_host_status="invented"))
    with pytest.raises(IntegrityError):
        client_db.commit()
    client_db.rollback()


def test_wildcard_host_is_exact_and_does_not_resolve_deeper_labels(client_db):
    tenant = Tenant(canonical_host="brand.pickyourpic.com.br", canonical_host_status="ready")
    client_db.add(tenant)
    client_db.commit()

    assert tenant_for_host(client_db, tenant.canonical_host).id == tenant.id
    assert tenant_for_host(client_db, "sub.brand.pickyourpic.com.br") is None
    assert tenant_for_host(client_db, "unknown.pickyourpic.com.br") is None


def test_two_ready_tenants_resolve_and_generate_links_only_on_their_hosts(client_db):
    first = Tenant(canonical_host="first.pickyourpic.com.br", canonical_host_status="ready")
    second = Tenant(canonical_host="second.pickyourpic.com.br", canonical_host_status="ready")
    client_db.add_all([first, second])
    client_db.commit()

    assert tenant_for_host(client_db, first.canonical_host).id == first.id
    assert tenant_for_host(client_db, second.canonical_host).id == second.id
    assert tenant_for_host(client_db, "unknown.pickyourpic.com.br") is None
    assert public_gallery_url_for_tenant(client_db, first, uuid4()).startswith("https://first.pickyourpic.com.br/")
    assert purchase_url_for_tenant(client_db, second, uuid4()).startswith("https://second.pickyourpic.com.br/")


def test_client_sessions_follow_only_their_exact_host_and_ignore_forwarded_host(client_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(auth, "SessionLocal", lambda: client_db)
    first = Tenant(canonical_host="first.pickyourpic.com.br", canonical_host_status="ready")
    second = Tenant(canonical_host="second.pickyourpic.com.br", canonical_host_status="ready")
    client_db.add_all([first, second])
    client_db.flush()
    first_client = Client(tenant_id=first.id, full_name="Cliente sintética A", phone_e164="+5511999991001")
    second_client = Client(tenant_id=second.id, full_name="Cliente sintética B", phone_e164="+5511999991002")
    client_db.add_all([first_client, second_client])
    client_db.commit()
    first_token = create_session(client_db, Response(), Role.CLIENT, first_client.id, tenant_id=first.id)
    second_token = create_session(client_db, Response(), Role.CLIENT, second_client.id, tenant_id=second.id)

    def request(host, token, forwarded_host=None):
        headers = [(b"host", host.encode()), (b"cookie", f"markina_session={token}".encode())]
        if forwarded_host:
            headers.append((b"x-forwarded-host", forwarded_host.encode()))
        return Request({"type": "http", "http_version": "1.1", "method": "GET", "scheme": "https",
                        "path": "/", "query_string": b"", "headers": headers,
                        "client": ("127.0.0.1", 1234), "server": (host, 443)})

    assert current_session(request(first.canonical_host, first_token, second.canonical_host), Role.CLIENT).tenant_id == first.id
    with pytest.raises(HTTPException) as cross_tenant:
        current_session(request(second.canonical_host, first_token), Role.CLIENT)
    assert getattr(cross_tenant.value, "status_code", None) == 403
    assert current_session(request(second.canonical_host, second_token), Role.CLIENT).tenant_id == second.id


def test_admin_session_cookie_remains_host_only(client_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    tenant = Tenant()
    owner = AdminUser(email="host-cookie@example.test", password_hash="synthetic", email_verified=True,
                      totp_enabled=False)
    client_db.add_all([tenant, owner])
    client_db.flush()
    client_db.add(TenantAdmin(tenant_id=tenant.id, admin_user_id=owner.id, active=True))
    client_db.commit()
    response = Response()
    create_session(client_db, response, Role.ADMIN, owner.id, tenant_id=tenant.id)
    cookie = response.headers["set-cookie"]

    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "Domain=" not in cookie
