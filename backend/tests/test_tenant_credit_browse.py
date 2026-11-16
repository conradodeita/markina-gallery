"""Consulta owner-only paginada; dados sintéticos, sem saldos por sugestão."""

from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event

from app import photographer_credits as credits
from app.auth import (
    AdminUser,
    Client,
    InstallationOperator,
    Tenant,
    TenantAdmin,
    TenantCreditWallet,
    now,
)
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


def add_tenant(db, value, email, created_at):
    tenant = Tenant(id=UUID(int=value), created_at=created_at)
    db.add(tenant)
    db.flush()
    admin = AdminUser(email=email, password_hash="synthetic", totp_secret="synthetic", email_verified=True)
    admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
    db.add_all([admin, TenantCreditWallet(tenant_id=tenant.id, mode="finite")])
    db.flush()
    return tenant, admin


def test_browse_starts_empty_and_pages_all_without_duplicate_or_ledger_reads(client_db):
    owner_tenant, tenant, owner, _photographer = create_accounts(client_db)
    extra, _admin = add_tenant(client_db, 1234, "extra@browse.example.test", now())
    second_admin = AdminUser(email="second@browse.example.test", password_hash="synthetic", totp_secret="synthetic")
    second_admin.tenant_memberships.append(TenantAdmin(tenant_id=extra.id))
    client_db.add(second_admin)
    client_db.commit()
    owner_id = owner.id
    expected = sorted(str(item.id) for item in (owner_tenant, tenant, extra))
    assert credits.browse_credit_tenants(client_db, owner_id) == {"items": [], "has_more": False}
    assert credits.browse_credit_tenants(client_db, owner_id, query="x") == {"items": [], "has_more": False}
    statements = []

    def record(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lower())

    event.listen(client_db.bind, "before_cursor_execute", record)
    try:
        pages = [credits.browse_credit_tenants(client_db, owner_id, mode="all", limit=1, offset=offset)
                 for offset in range(4)]
    finally:
        event.remove(client_db.bind, "before_cursor_execute", record)
    assert [page["items"][0]["tenant_id"] for page in pages[:3]] == expected
    assert [page["has_more"] for page in pages] == [True, True, False, False]
    assert pages[3]["items"] == []
    assert all(set(item) == {"tenant_id", "status", "canonical_host", "photographer_name", "admin_email"}
               for page in pages for item in page["items"])
    assert next(item for page in pages for item in page["items"]
                if item["tenant_id"] == str(extra.id))["admin_email"] is None
    assert not any("photographer_credit_entry" in sql or "photo_credit_operation" in sql for sql in statements)


def test_browse_combines_modes_case_insensitive_email_and_stable_ties(client_db):
    _owner_tenant, _tenant, owner, _photographer = create_accounts(client_db)
    oldest = now() - timedelta(days=2)
    recent = now()
    first, _ = add_tenant(client_db, 100, "ZULU@browse.example.test", oldest)
    second, _ = add_tenant(client_db, 200, "Beta@browse.example.test", recent)
    third, _ = add_tenant(client_db, 300, "alpha@browse.example.test", recent)
    alternate = AdminUser(email="alpha@BROWSE.example.test", password_hash="synthetic", totp_secret="synthetic")
    alternate.tenant_memberships.append(TenantAdmin(tenant_id=first.id))
    client_db.add(alternate)
    client_db.commit()

    def identities(mode, query="BROWSE.EXAMPLE.TEST"):
        return [item["tenant_id"] for item in credits.browse_credit_tenants(
            client_db, owner.id, query=query, mode=mode,
        )["items"]]

    assert identities("all") == [str(first.id), str(second.id), str(third.id)]
    # A conta sem nome e com dois administradores não elege um e-mail oculto.
    assert identities("alphabetical") == [str(third.id), str(second.id), str(first.id)]
    alphabetic_page = credits.browse_credit_tenants(
        client_db, owner.id, query="browse.example.test", mode="alphabetical",
    )["items"]
    displayed = [item["admin_email"].lower() for item in alphabetic_page if item["admin_email"] is not None]
    assert displayed == sorted(displayed)
    assert alphabetic_page[-1]["admin_email"] is None
    assert identities("recent") == [str(second.id), str(third.id), str(first.id)]
    assert identities(None) == identities("recent")
    assert identities("alphabetical", "zul") == [str(first.id)]
    matched = credits.browse_credit_tenants(client_db, owner.id, query="ZULU")["items"][0]
    assert matched["tenant_id"] == str(first.id) and matched["admin_email"] is None
    assert len(identities("all", "a")) == 5  # filtro de um caractere com modo explícito


def test_browse_escapes_like_wildcards_and_enforces_limits(client_db):
    _owner_tenant, _tenant, owner, _photographer = create_accounts(client_db)
    target, _ = add_tenant(client_db, 888, "literal%_tag@browse.example.test", now())
    add_tenant(client_db, 999, "literalXXtag@browse.example.test", now())
    client_db.commit()
    result = credits.browse_credit_tenants(client_db, owner.id, mode="all", query="%_")
    assert [item["tenant_id"] for item in result["items"]] == [str(target.id)]
    for parameters in ({"limit": 0}, {"limit": 21}, {"offset": -1}, {"offset": 100_001}, {"mode": "unknown"}):
        with pytest.raises(HTTPException) as invalid:
            credits.browse_credit_tenants(client_db, owner.id, **parameters)
        assert invalid.value.status_code == 422
    assert credits.browse_credit_tenants(client_db, owner.id, mode="all", limit=20, offset=100_000) == {
        "items": [], "has_more": False,
    }


def test_every_browse_mode_rejects_photographer_client_and_technical_operator(client_db):
    _owner_tenant, tenant, _owner, photographer = create_accounts(client_db)
    operator = AdminUser(email="technical@example.test", password_hash="synthetic", totp_secret="synthetic")
    operator.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
    client_db.add(operator)
    client_db.flush()
    client_db.add(InstallationOperator(admin_user_id=operator.id, active=True,
        authorization_reference="synthetic", granted_at=now(), updated_at=now()))
    client = Client(tenant_id=tenant.id, full_name="Synthetic client", phone_e164="+5511999990001")
    client_db.add(client)
    client_db.commit()
    for identity in (photographer.id, operator.id, client.id, uuid4()):
        for mode in (None, "all", "alphabetical", "recent"):
            with pytest.raises(HTTPException) as denied:
                credits.browse_credit_tenants(client_db, identity, mode=mode)
            assert denied.value.status_code == 403


def test_browse_http_defaults_bounds_and_owner_authorization(client_db, monkeypatch):
    _owner_tenant, _tenant, owner, photographer = create_accounts(client_db)
    client_db.commit()
    from app import main

    def db_override():
        yield client_db

    main.app.dependency_overrides[main.db_session] = db_override
    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=owner.id))
    try:
        client = TestClient(main.app)
        path = "/admin/platform/credit-tenants/search"
        result = client.get(path)
        assert result.status_code == 200
        assert result.json() == {"items": [], "has_more": False}
        assert result.headers["cache-control"] == "private, no-store"
        page = client.get(path, params={"mode": "all", "limit": 1})
        assert page.status_code == 200 and len(page.json()["items"]) == 1 and page.json()["has_more"]
        for params in ({"mode": "unknown"}, {"limit": 21}, {"offset": -1}, {"offset": 100_001}):
            assert client.get(path, params=params).status_code == 422
        monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=photographer.id))
        for mode in ("all", "alphabetical", "recent"):
            denied = client.get(path, params={"mode": mode})
            assert denied.status_code == 403
            assert "items" not in denied.json()
    finally:
        main.app.dependency_overrides.pop(main.db_session, None)
