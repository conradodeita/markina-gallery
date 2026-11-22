"""API de encerramento autenticada, tenant-scoped e com dados sintéticos."""

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import auth
from app import tenant_closure_api as closure_api
from app.auth import (
    AuthSession,
    PhotographerCreditEntry,
    PhotographerTermsAcceptance,
    Tenant,
    TenantClosureRequest,
    now,
)
from app.main import protect_credential_validation_input
from app.tenant_closure_api import router
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
ROOT = "/api/admin/closure"
COOKIE = "synthetic-photographer-session"
TERMS_VERSION = "local-test-v1"
TERMS_SHA256 = "a" * 64


@pytest.fixture
def closure_http(client_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PHOTOGRAPHER_TEST_TERMS_ENABLED", "true")
    _owner_tenant, tenant, _owner, photographer = create_accounts(client_db)
    client_db.add_all([
        PhotographerTermsAcceptance(
            tenant_id=tenant.id,
            admin_user_id=photographer.id,
            terms_version=TERMS_VERSION,
            terms_text="Texto sintético de teste local.",
            terms_sha256=TERMS_SHA256,
            provider_identity="Provedor sintético",
            photographer_identity="Fotógrafo sintético",
            environment="test",
        ),
        PhotographerCreditEntry(
            tenant_id=tenant.id,
            entry_type="correction",
            delta=7,
            idempotency_key="closure-api-synthetic-credit",
        ),
        AuthSession(
            tenant_id=tenant.id,
            role="admin",
            subject_id=photographer.id,
            admin_subject_id=photographer.id,
            token_hash=auth.token_hash(COOKIE),
            expires_at=now() + timedelta(hours=1),
        ),
    ])
    client_db.commit()
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    monkeypatch.setattr(auth, "SessionLocal", factory)
    monkeypatch.setattr(closure_api, "SessionLocal", factory)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.add_exception_handler(RequestValidationError, protect_credential_validation_input)
    client = TestClient(app)
    client.cookies.set("markina_session", COOKIE)
    headers = {"Origin": "http://testserver"}
    return client, headers, tenant, photographer


def test_status_and_request_are_authenticated_idempotent_and_show_balance(closure_http, client_db):
    client, headers, tenant, _photographer = closure_http
    status = client.get(ROOT, headers=headers)
    assert status.status_code == 200
    assert status.headers["cache-control"] == "private, no-store, max-age=0"
    assert status.json()["lifecycle"] == "open"
    assert status.json()["credits_remaining"] == 7
    assert status.json()["terms"] == {
        "available": True, "accepted": True,
        "version": TERMS_VERSION, "sha256": TERMS_SHA256,
    }

    payload = {
        "request_id": str(uuid4()),
        "confirm_closure": True,
        "acknowledge_remaining_balance": True,
        "expected_balance": 7,
        "terms_version": TERMS_VERSION,
        "terms_sha256": TERMS_SHA256,
    }
    first = client.post(ROOT, headers=headers, json=payload)
    replay = client.post(ROOT, headers=headers, json=payload)
    assert first.status_code == replay.status_code == 202
    assert first.json()["replayed"] is False and replay.json()["replayed"] is True
    assert tenant.lifecycle == "closing"
    assert client_db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant.id,
    )).balance_snapshot == 7

    status_after = client.get(ROOT, headers=headers)
    assert status_after.status_code == 200
    assert status_after.json()["lifecycle"] == "closing"
    assert status_after.json()["request"]["balance_snapshot"] == 7


def test_unaccepted_terms_prevent_request_and_do_not_change_lifecycle(closure_http, client_db):
    client, headers, tenant, _photographer = closure_http
    client_db.query(PhotographerTermsAcceptance).filter_by(tenant_id=tenant.id).delete()
    client_db.commit()
    assert client.get(ROOT, headers=headers).json()["terms"]["accepted"] is False
    response = client.post(ROOT, headers=headers, json={
        "request_id": str(uuid4()),
        "confirm_closure": True,
        "acknowledge_remaining_balance": True,
        "expected_balance": 7,
        "terms_version": TERMS_VERSION,
        "terms_sha256": TERMS_SHA256,
    })
    assert response.status_code == 409
    assert "no-store" in response.headers.get("cache-control", "")
    assert tenant.lifecycle == "open"
    assert client_db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant.id,
    )) is None


def test_old_acceptance_cannot_bypass_unavailable_current_terms(closure_http, monkeypatch, client_db):
    client, headers, tenant, _photographer = closure_http
    monkeypatch.setattr(closure_api, "_terms_version", lambda _db: None)
    response = client.post(ROOT, headers=headers, json={
        "request_id": str(uuid4()),
        "confirm_closure": True,
        "acknowledge_remaining_balance": True,
        "expected_balance": 7,
        "terms_version": TERMS_VERSION,
        "terms_sha256": TERMS_SHA256,
    })
    assert response.status_code == 409
    assert tenant.lifecycle == "open"
    assert client_db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant.id,
    )) is None


def test_unauthenticated_and_cross_tenant_payloads_cannot_request_closure(closure_http, client_db):
    client, headers, tenant, _photographer = closure_http
    client.cookies.clear()
    assert client.get(ROOT, headers=headers).status_code == 403
    client.cookies.set("markina_session", COOKIE)
    other_tenant = Tenant()
    client_db.add(other_tenant)
    client_db.commit()
    response = client.post(ROOT, headers=headers, json={
        "request_id": str(uuid4()),
        "tenant_id": str(other_tenant.id),
        "confirm_closure": True,
        "acknowledge_remaining_balance": True,
        "expected_balance": 7,
        "terms_version": TERMS_VERSION,
        "terms_sha256": TERMS_SHA256,
    })
    assert response.status_code == 422
    assert tenant.lifecycle == other_tenant.lifecycle == "open"
