from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import auth, main
from app.auth import AuthSession, Role, TenantAdmin
from tests.test_admin_preview_pool_concurrency import client_db as recovery_db
from tests.test_tenant_acervo import graph as recovery_graph
from tests.test_tenant_client_auth import request
from tests.test_tenant_client_navigation import cookie

client_db = recovery_db
graph = recovery_graph


@pytest.fixture
def recovery_factory(client_db, monkeypatch):
    factory = sessionmaker(bind=client_db.bind, expire_on_commit=False)
    monkeypatch.setattr(auth, "SessionLocal", factory)
    monkeypatch.setattr(main, "SessionLocal", factory)
    return factory


@pytest.mark.parametrize("role", [Role.ADMIN, Role.CLIENT])
@pytest.mark.parametrize("state", ["missing", "unknown", "expired", "revoked"])
def test_destination_distinguishes_missing_or_invalid_session(client_db, graph, recovery_factory, role, state):
    token = cookie(client_db, graph[0], role)
    if state in {"expired", "revoked"}:
        stored = client_db.scalar(select(AuthSession).where(AuthSession.token_hash == auth.token_hash(token)))
        if state == "expired":
            stored.expires_at = auth.now() - timedelta(seconds=1)
        else:
            stored.revoked_at = auth.now()
        client_db.commit()
    presented = None if state == "missing" else "unknown-session" if state == "unknown" else token
    with TestClient(main.app) as browser:
        if presented:
            browser.cookies.set("markina_session", presented)
        response = browser.get("/auth/destination")
        assert response.status_code == 401
        assert response.json() == {"detail": "Acesso negado."}
    with pytest.raises(HTTPException) as rejected:
        auth.current_session(request(presented or ""))
    assert rejected.value.status_code == 403


@pytest.mark.parametrize("state", ["suspended", "membership_revoked", "email_unverified"])
def test_destination_keeps_forbidden_context_distinct(client_db, graph, recovery_factory, state):
    account = graph[0]
    token = cookie(client_db, account, Role.ADMIN)
    if state == "suspended":
        account["tenant"].status = "suspended"
    elif state == "email_unverified":
        account["admin"].email_verified = False
    else:
        membership = client_db.scalar(select(TenantAdmin).where(TenantAdmin.tenant_id == account["tenant"].id))
        membership.active = False
    client_db.commit()
    with TestClient(main.app) as browser:
        browser.cookies.set("markina_session", token)
        response = browser.get("/auth/destination")
        assert response.status_code == 403
        assert response.json() == {"detail": "Acesso negado."}
    assert main.destination(request(cookie(client_db, graph[1], Role.ADMIN))) == {"destination": "/admin"}
