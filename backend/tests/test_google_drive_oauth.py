"""Gates locais do OAuth Drive; nenhum cliente/conta Google é acessado."""

import hashlib
import json
import os
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import google_drive_client
from app import google_drive_oauth as drive
from app import google_drive_picker as picker
from app.auth import (
    AuditEvent,
    AuthSession,
    GoogleDriveConnection,
    GoogleDriveOAuthAttempt,
    now,
)
from app.integration_secrets import IntegrationCipher, SecretEnvelope
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
PICKER_TEST_DEVELOPER_KEY = "AIza" + ("x" * 35)


def _write_oauth_client_file(monkeypatch, tmp_path, *, client_secret="synthetic-secret",
                             redirect_uri=drive.GOOGLE_DRIVE_EXPECTED_REDIRECT_URI):
    path = tmp_path / "oauth-client.json"
    path.write_text(json.dumps({"web": {
        "client_id": "synthetic-client",
        "client_secret": client_secret,
        "redirect_uris": [redirect_uri],
    }}), encoding="utf-8")
    path.chmod(0o400)
    monkeypatch.setattr(drive, "GOOGLE_DRIVE_CLIENT_CONFIG_PATH", path)
    return path


@pytest.fixture
def drive_http(client_db, monkeypatch):
    owner_tenant, tenant_b, owner, photographer_b = create_accounts(client_db)
    auth_session = AuthSession(id=uuid4(), token_hash=f"synthetic-{uuid4().hex}", role="admin",
        subject_id=owner.id, admin_subject_id=owner.id, tenant_id=owner_tenant.id,
        expires_at=now() + timedelta(hours=1))
    client_db.add(auth_session)
    client_db.commit()
    session = SimpleNamespace(id=auth_session.id, subject_id=owner.id, tenant_id=owner_tenant.id)
    session.photographer_b_id, session.tenant_b_id = photographer_b.id, tenant_b.id
    monkeypatch.setattr(drive, "SessionLocal", lambda: client_db)
    monkeypatch.setattr(picker, "SessionLocal", lambda: client_db)
    monkeypatch.setattr(drive, "current_session", lambda *_args: session)
    app = FastAPI()
    app.include_router(drive.router)
    app.include_router(picker.router)
    return TestClient(app), session


def test_external_oauth_and_revoke_are_closed_outside_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    with pytest.raises(HTTPException) as rejected:
        drive._config()
    assert rejected.value.status_code == 503
    assert "real" in rejected.value.detail


def test_callback_candidate_is_loaded_from_protected_web_client_file(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    _write_oauth_client_file(monkeypatch, tmp_path)
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "legacy-client")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "legacy-secret")
    monkeypatch.setenv("GOOGLE_DRIVE_REDIRECT_URI", "http://legacy.invalid/callback")
    assert drive._config() == (
        "synthetic-client", "synthetic-secret",
        drive.GOOGLE_DRIVE_EXPECTED_REDIRECT_URI,
    )


def test_oauth_redirect_uri_rejects_insecure_production_and_missing_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    _write_oauth_client_file(monkeypatch, tmp_path, client_secret="",
        redirect_uri="http://127.0.0.1:8000/callback")
    with pytest.raises(HTTPException) as rejected:
        drive._config()
    assert rejected.value.status_code == 503


def test_oauth_client_env_cannot_fallback_when_protected_file_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "legacy-client")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "legacy-secret")
    monkeypatch.setenv("GOOGLE_DRIVE_REDIRECT_URI", "https://legacy.invalid/callback")
    monkeypatch.setattr(drive, "GOOGLE_DRIVE_CLIENT_CONFIG_PATH", tmp_path / "missing.json")

    with pytest.raises(HTTPException) as rejected:
        drive._config()
    assert rejected.value.status_code == 503


def test_oauth_client_file_rejects_invalid_json(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    path = tmp_path / "oauth-client.json"
    path.write_text("{invalid", encoding="utf-8")
    path.chmod(0o400)
    monkeypatch.setattr(drive, "GOOGLE_DRIVE_CLIENT_CONFIG_PATH", path)

    with pytest.raises(HTTPException) as rejected:
        drive._config()
    assert rejected.value.status_code == 503


@pytest.mark.skipif(os.name != "posix", reason="Permissões POSIX são validadas no runtime Linux.")
def test_oauth_client_file_rejects_permissive_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    path = _write_oauth_client_file(monkeypatch, tmp_path)
    path.chmod(0o644)

    with pytest.raises(HTTPException) as rejected:
        drive._config()
    assert rejected.value.status_code == 503


def test_oauth_client_file_rejects_unregistered_https_redirect(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    _write_oauth_client_file(monkeypatch, tmp_path, redirect_uri="https://attacker.invalid/callback")

    with pytest.raises(HTTPException) as rejected:
        drive._config()
    assert rejected.value.status_code == 503


def test_oauth_client_file_rejects_multiple_redirect_uris(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    path = _write_oauth_client_file(monkeypatch, tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["web"]["redirect_uris"].append("https://attacker.invalid/callback")
    path.chmod(0o600)
    path.write_text(json.dumps(document), encoding="utf-8")
    path.chmod(0o400)

    with pytest.raises(HTTPException) as rejected:
        drive._config()
    assert rejected.value.status_code == 503


@pytest.mark.skipif(os.name != "posix", reason="Proteção contra symlink é validada no runtime Linux.")
def test_oauth_client_file_rejects_symlink(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    target = _write_oauth_client_file(monkeypatch, tmp_path)
    link = tmp_path / "oauth-client-link.json"
    link.symlink_to(target)
    monkeypatch.setattr(drive, "GOOGLE_DRIVE_CLIENT_CONFIG_PATH", link)

    with pytest.raises(HTTPException) as rejected:
        drive._config()
    assert rejected.value.status_code == 503


def test_quota_observation_uses_synthetic_transport_and_keeps_missing_fields_unknown(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    class SyntheticTransport:
        def __init__(self):
            self.calls = []

        def post(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return SimpleNamespace(status_code=200, json=lambda: {"access_token": "synthetic-access"})

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return SimpleNamespace(status_code=200, json=lambda: {"storageQuota": {"usage": "123"}})

    synthetic = SyntheticTransport()
    assert drive.observe_storage_quota(refresh_token="synthetic-refresh", client_id="id",
                                       client_secret="secret", transport=synthetic) == (None, "123")
    assert len(synthetic.calls) == 2
    assert synthetic.calls[1][1]["params"] == {"fields": "storageQuota(limit,usage)"}
    assert "emailAddress" not in synthetic.calls[1][1]["params"]["fields"]


def test_quota_observation_helper_is_closed_outside_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    with pytest.raises(ValueError):
        drive.observe_storage_quota(refresh_token="synthetic", client_id="id", client_secret="secret")


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_quota_provider_errors_fail_closed_without_returning_provider_body(monkeypatch, status):
    monkeypatch.setenv("APP_ENV", "production")

    class SyntheticTransport:
        def post(self, _url, **_kwargs):
            return SimpleNamespace(status_code=status, json=lambda: {"error_description": "private"})

        def get(self, *_args, **_kwargs):
            raise AssertionError("quota não pode ser consultada sem token")

    with pytest.raises(ValueError):
        drive.observe_storage_quota(refresh_token="synthetic", client_id="id", client_secret="secret",
                                    transport=SyntheticTransport())


def test_quota_rejects_malformed_provider_shape(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    class SyntheticTransport:
        def post(self, _url, **_kwargs):
            return SimpleNamespace(status_code=200, json=lambda: {"access_token": "synthetic"})

        def get(self, *_args, **_kwargs):
            return SimpleNamespace(status_code=200, json=lambda: {"storageQuota": []})

    with pytest.raises(TypeError):
        drive.observe_storage_quota(refresh_token="synthetic", client_id="id", client_secret="secret",
                                    transport=SyntheticTransport())


def test_http_transport_retries_idempotent_get_once_but_never_retries_post(monkeypatch):
    adapter = drive.HttpxDriveTransport()
    responses = [SimpleNamespace(status_code=503), SimpleNamespace(status_code=200)]
    calls = []

    def request(method, url, **_kwargs):
        calls.append((method, url))
        return responses.pop(0)

    monkeypatch.setattr(adapter, "_request", request)
    monkeypatch.setattr(google_drive_client.time, "sleep", lambda _seconds: None)
    assert adapter.get("https://www.googleapis.com/drive/v3/about").status_code == 200
    assert len(calls) == 2 and all(method == "GET" for method, _ in calls)

    calls.clear()
    monkeypatch.setattr(adapter, "_request", lambda method, url, **_kwargs: calls.append((method, url)) or
                        SimpleNamespace(status_code=503))
    assert adapter.post(drive.TOKEN_ENDPOINT).status_code == 503
    assert len(calls) == 1 and calls[0][0] == "POST"


def test_status_without_connection_is_unknown_and_never_exposes_credentials(drive_http, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    client, _session = drive_http
    response = client.get("/admin/platform/drive/status")
    assert response.status_code == 200
    assert response.json() == {
        "state": "unknown", "scope": None, "connected_at": None, "quota_limit": None,
        "quota_usage": None, "quota_observed_at": None,
    }
    assert "no-store" in response.headers["cache-control"]
    assert "token" not in response.text.lower()


def test_callback_without_state_fails_closed_before_provider_access(drive_http, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    client, _session = drive_http
    response = client.get("/admin/platform/drive/oauth/callback")
    assert response.status_code == 400
    assert "no-store" in response.headers["cache-control"]
    assert "code" not in response.text.lower()


def test_connect_start_returns_only_google_authorization_url_and_keeps_redirect_compatibility(
    drive_http, client_db, monkeypatch
):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(drive, "_config", lambda: (
        "synthetic-client", "synthetic-client-secret", drive.GOOGLE_DRIVE_EXPECTED_REDIRECT_URI))
    monkeypatch.setattr(drive, "reauthenticate_admin", lambda _admin, _password: None)
    monkeypatch.setattr(drive, "matching_unused_totp_step", lambda *_args: 12345)
    client, session = drive_http

    response = client.post("/admin/platform/drive/connect/start",
        headers={"Origin": "http://testserver"},
        json={"current_password": "synthetic-password", "totp_code": "123456"})

    assert response.status_code == 200
    assert "no-store" in response.headers["cache-control"]
    assert set(response.json()) == {"authorization_url"}
    authorization_url = response.json()["authorization_url"]
    parsed = urlsplit(authorization_url)
    params = parse_qs(parsed.query)
    assert parsed.scheme == "https" and parsed.netloc == "accounts.google.com"
    assert parsed.path == "/o/oauth2/v2/auth"
    assert params["client_id"] == ["synthetic-client"]
    assert params["redirect_uri"] == [drive.GOOGLE_DRIVE_EXPECTED_REDIRECT_URI]
    assert params["scope"] == [drive.SCOPE]
    assert params["response_type"] == ["code"]
    assert params["code_challenge_method"] == ["S256"]
    assert "code_challenge" in params and "state" in params
    assert "client_secret" not in authorization_url and "synthetic-client-secret" not in authorization_url
    assert "code_verifier" not in authorization_url
    attempt = client_db.query(GoogleDriveOAuthAttempt).one()
    assert attempt.actor_admin_id == session.subject_id and attempt.auth_session_id == session.id
    assert attempt.tenant_id == session.tenant_id and attempt.consumed_at is None
    assert client_db.query(GoogleDriveConnection).count() == 0

    legacy = client.post("/admin/platform/drive/connect",
        headers={"Origin": "http://testserver"},
        json={"current_password": "synthetic-password", "totp_code": "123456"},
        follow_redirects=False)
    assert legacy.status_code == 303
    assert legacy.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")


def test_callback_consumes_state_and_persists_only_encrypted_refresh_token(drive_http, client_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(drive, "_config", lambda: (
        "synthetic-client", "synthetic-secret", "https://example.test/callback"))
    client, session = drive_http
    state, verifier, attempt_id = "synthetic-state", "synthetic-verifier", uuid4()
    cipher = IntegrationCipher()
    envelope = cipher.encrypt(verifier, tenant_id=session.tenant_id, credential_id=attempt_id).payload()
    client_db.add(GoogleDriveOAuthAttempt(id=attempt_id, actor_admin_id=session.subject_id,
        auth_session_id=session.id, tenant_id=session.tenant_id,
        state_digest=hashlib.sha256(state.encode()).hexdigest(), verifier_envelope=envelope,
        expires_at=now() + timedelta(minutes=5)))
    client_db.commit()

    class SyntheticTransport:
        def __init__(self):
            self.calls = []

        def post(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return SimpleNamespace(status_code=200, json=lambda: {
                "refresh_token": "synthetic-refresh", "access_token": "synthetic-access",
                "scope": drive.SCOPE,
            })

    synthetic = SyntheticTransport()
    monkeypatch.setattr(drive, "HttpxDriveTransport", lambda: synthetic)
    response = client.get("/admin/platform/drive/oauth/callback",
                          params={"state": state, "code": "synthetic-code"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/platform?drive=connected"
    assert len(synthetic.calls) == 1
    assert synthetic.calls[0][1]["data"]["code_verifier"] == verifier
    saved = client_db.query(GoogleDriveConnection).one()
    assert saved.state == "connected" and saved.tenant_id == session.tenant_id
    assert cipher.decrypt(SecretEnvelope.from_payload(saved.refresh_token_envelope), tenant_id=session.tenant_id,
                          credential_id=saved.id) == "synthetic-refresh"
    assert "synthetic-refresh" not in str(saved.refresh_token_envelope)
    assert "synthetic-access" not in str(saved.refresh_token_envelope)
    assert client.get("/admin/platform/drive/oauth/callback",
                      params={"state": state, "code": "synthetic-code"}).status_code == 400
    assert len(synthetic.calls) == 1


@pytest.mark.parametrize("scope_value", [
    drive.SCOPE + " https://www.googleapis.com/auth/drive",
    drive.SCOPE + " email",
    "",
])
def test_callback_rejects_missing_or_additional_granted_scope(
    drive_http, client_db, monkeypatch, scope_value
):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(drive, "_config", lambda: (
        "synthetic-client", "synthetic-secret", "https://example.test/callback"))
    client, session = drive_http
    state, attempt_id = f"scope-check-{uuid4().hex}", uuid4()
    verifier = IntegrationCipher().encrypt(
        "synthetic-verifier", tenant_id=session.tenant_id, credential_id=attempt_id,
    ).payload()
    client_db.add(GoogleDriveOAuthAttempt(
        id=attempt_id,
        actor_admin_id=session.subject_id,
        auth_session_id=session.id,
        tenant_id=session.tenant_id,
        state_digest=hashlib.sha256(state.encode()).hexdigest(),
        verifier_envelope=verifier,
        expires_at=now() + timedelta(minutes=5),
    ))
    client_db.commit()

    class SyntheticTransport:
        def post(self, _url, **_kwargs):
            return SimpleNamespace(status_code=200, json=lambda: {
                "refresh_token": "synthetic-refresh",
                "access_token": "synthetic-access",
                "scope": scope_value,
            })

    monkeypatch.setattr(drive, "HttpxDriveTransport", SyntheticTransport)
    response = client.get(
        "/admin/platform/drive/oauth/callback",
        params={"state": state, "code": "synthetic-code"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "synthetic-refresh" not in response.text
    assert client_db.query(GoogleDriveConnection).count() == 0
    assert client_db.get(GoogleDriveOAuthAttempt, attempt_id).consumed_at is not None


def test_callback_without_refresh_token_preserves_existing_connection(drive_http, client_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(drive, "_config", lambda: (
        "synthetic-client", "synthetic-secret", "https://example.test/callback"))
    client, session = drive_http
    cipher = IntegrationCipher()
    credential_id, attempt_id = uuid4(), uuid4()
    existing_envelope = cipher.encrypt("existing-synthetic-refresh", tenant_id=session.tenant_id,
                                       credential_id=credential_id).payload()
    verifier_envelope = cipher.encrypt("synthetic-verifier", tenant_id=session.tenant_id,
                                       credential_id=attempt_id).payload()
    client_db.add_all([
        GoogleDriveConnection(id=credential_id, tenant_id=session.tenant_id,
            connected_by_admin_id=session.subject_id, refresh_token_envelope=existing_envelope,
            scopes=drive.SCOPE, state="connected", connected_at=now(), updated_at=now()),
        GoogleDriveOAuthAttempt(id=attempt_id, actor_admin_id=session.subject_id,
            auth_session_id=session.id, tenant_id=session.tenant_id,
            state_digest=hashlib.sha256(b"no-refresh-state").hexdigest(),
            verifier_envelope=verifier_envelope, expires_at=now() + timedelta(minutes=5)),
    ])
    client_db.commit()

    class SyntheticTransport:
        def post(self, _url, **_kwargs):
            return SimpleNamespace(status_code=200, json=lambda: {
                "access_token": "synthetic-access", "scope": drive.SCOPE,
                "error_description": "private provider detail",
            })

    monkeypatch.setattr(drive, "HttpxDriveTransport", lambda: SyntheticTransport())
    response = client.get("/admin/platform/drive/oauth/callback",
        params={"state": "no-refresh-state", "code": "synthetic-code"})
    assert response.status_code == 400
    assert "private provider detail" not in response.text
    saved = client_db.get(GoogleDriveConnection, credential_id)
    assert saved.state == "connected" and saved.refresh_token_envelope == existing_envelope


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_callback_provider_errors_are_sanitized_and_consume_state(drive_http, client_db, monkeypatch, status):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(drive, "_config", lambda: (
        "synthetic-client", "synthetic-secret", "https://example.test/callback"))
    _client, session = drive_http
    state, attempt_id = f"provider-error-{status}", uuid4()
    verifier = IntegrationCipher().encrypt("synthetic-verifier", tenant_id=session.tenant_id,
        credential_id=attempt_id).payload()
    attempt = GoogleDriveOAuthAttempt(id=attempt_id, actor_admin_id=session.subject_id,
        auth_session_id=session.id, tenant_id=session.tenant_id,
        state_digest=hashlib.sha256(state.encode()).hexdigest(), verifier_envelope=verifier,
        expires_at=now() + timedelta(minutes=5))
    client_db.add(attempt)
    client_db.commit()

    class SyntheticTransport:
        def post(self, _url, **_kwargs):
            return SimpleNamespace(status_code=status,
                json=lambda: {"error_description": "private provider detail"})

    monkeypatch.setattr(drive, "HttpxDriveTransport", lambda: SyntheticTransport())
    request = Request({"type": "http", "method": "GET", "path": "/oauth/callback",
        "headers": [], "query_string": b"", "scheme": "http", "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345)})
    with pytest.raises(HTTPException) as rejected:
        drive.callback(request, state=state, code="synthetic-code")
    assert rejected.value.status_code == 400
    assert "private provider detail" not in rejected.value.detail
    assert client_db.get(GoogleDriveOAuthAttempt, attempt_id).consumed_at is not None
    assert not client_db.query(GoogleDriveConnection).count()


def test_owner_session_with_different_tenant_cannot_read_drive_state(drive_http):
    client, session = drive_http
    session.tenant_id = uuid4()
    response = client.get("/admin/platform/drive/status")
    assert response.status_code == 403
    assert response.json() == {"detail": "Acesso não autorizado."}


def test_photographer_tenant_b_cannot_read_owner_drive_state(drive_http):
    client, session = drive_http
    session.subject_id, session.tenant_id = session.photographer_b_id, session.tenant_b_id
    response = client.get("/admin/platform/drive/status")
    assert response.status_code == 403
    assert response.json() == {"detail": "Acesso não autorizado."}


def test_revoke_is_closed_outside_production_before_provider_access(drive_http, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    client, _session = drive_http
    response = client.post("/admin/platform/drive/revoke", headers={"Origin": "http://testserver"},
                           json={"current_password": "synthetic", "totp_code": "000000"})
    assert response.status_code == 503
    assert "no-store" in response.headers["cache-control"]


def test_revoke_synthetic_transport_revokes_and_clears_envelope(drive_http, client_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(drive, "_is_production", lambda: True)
    monkeypatch.setattr(drive, "reauthenticate_admin", lambda *_args: None)
    monkeypatch.setattr(drive, "matching_unused_totp_step", lambda *_args: 123)
    client, session = drive_http
    cipher = IntegrationCipher()
    credential_id = uuid4()
    envelope = cipher.encrypt("synthetic-refresh", tenant_id=session.tenant_id,
                              credential_id=credential_id).payload()
    client_db.add(GoogleDriveConnection(id=credential_id, tenant_id=session.tenant_id,
        connected_by_admin_id=session.subject_id, refresh_token_envelope=envelope,
        scopes=drive.SCOPE, state="connected", connected_at=now(), updated_at=now()))
    client_db.commit()

    class SyntheticTransport:
        def __init__(self):
            self.calls = []

        def post(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return SimpleNamespace(status_code=200)

    synthetic = SyntheticTransport()
    monkeypatch.setattr(drive, "HttpxDriveTransport", lambda: synthetic)
    response = client.post("/admin/platform/drive/revoke", headers={"Origin": "http://testserver"},
                           json={"current_password": "synthetic", "totp_code": "000000"})
    assert response.status_code == 200 and response.json() == {"state": "revoked"}
    assert synthetic.calls[0][0] == drive.REVOKE_ENDPOINT
    assert synthetic.calls[0][1]["data"]["token"] == "synthetic-refresh"
    persisted = client_db.get(GoogleDriveConnection, credential_id)
    assert persisted.state == "revoked" and persisted.refresh_token_envelope == {}
    assert "synthetic-refresh" not in response.text


@pytest.mark.parametrize("status", [400, 401, 403, 429, 503])
def test_revoke_provider_errors_preserve_connection_and_are_sanitized(
        drive_http, client_db, monkeypatch, status):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(drive, "_is_production", lambda: True)
    monkeypatch.setattr(drive, "reauthenticate_admin", lambda *_args: None)
    monkeypatch.setattr(drive, "matching_unused_totp_step", lambda *_args: 123)
    _client, session = drive_http
    cipher = IntegrationCipher()
    credential_id = uuid4()
    envelope = cipher.encrypt("synthetic-refresh", tenant_id=session.tenant_id,
                              credential_id=credential_id).payload()
    client_db.add(GoogleDriveConnection(id=credential_id, tenant_id=session.tenant_id,
        connected_by_admin_id=session.subject_id, refresh_token_envelope=envelope,
        scopes=drive.SCOPE, state="connected", connected_at=now(), updated_at=now()))
    client_db.commit()

    class SyntheticTransport:
        def post(self, _url, **_kwargs):
            return SimpleNamespace(status_code=status,
                json=lambda: {"error_description": "private provider detail"})

    monkeypatch.setattr(drive, "HttpxDriveTransport", lambda: SyntheticTransport())
    request = Request({"type": "http", "method": "POST", "path": "/revoke", "headers": [],
        "query_string": b"", "scheme": "http", "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345)})
    payload = drive.ConnectInput(current_password="synthetic", totp_code="000000")
    with pytest.raises(HTTPException) as rejected:
        drive.revoke(payload, request)
    assert rejected.value.status_code == 503
    assert "private provider detail" not in rejected.value.detail
    persisted = client_db.get(GoogleDriveConnection, credential_id)
    assert persisted.state == "connected" and persisted.refresh_token_envelope == envelope


def test_failed_connect_reauthentication_is_rate_limited_and_audited(drive_http, client_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(drive, "_config", lambda: (
        "synthetic-client", "synthetic-secret", "https://example.test/callback"))
    client, session = drive_http
    response = client.post("/admin/platform/drive/connect", headers={"Origin": "http://testserver"},
                           json={"current_password": "wrong", "totp_code": "000000"})
    assert response.status_code == 403
    events = client_db.scalars(select(AuditEvent).where(AuditEvent.event == "rate_limited.request")).all()
    assert len(events) == 1
    assert events[0].subject.startswith(f"google_drive_connect:{session.subject_id}:")


def _connect_workspace_for_picker(client_db, session):
    cipher = IntegrationCipher()
    connection_id = uuid4()
    envelope = cipher.encrypt("synthetic-refresh-token", tenant_id=session.tenant_id,
                              credential_id=connection_id).payload()
    row = GoogleDriveConnection(
        id=connection_id, tenant_id=session.tenant_id, connected_by_admin_id=session.subject_id,
        refresh_token_envelope=envelope, scopes=drive.SCOPE, state="connected",
        connected_at=now(), updated_at=now(),
    )
    client_db.add(row)
    client_db.commit()
    return cipher


class PickerDriveTransport:
    def __init__(self, folder=None):
        self.folder = folder
        self.patches = []
        self.token_requests = []

    def post(self, url, **kwargs):
        self.token_requests.append((url, kwargs))
        return httpx.Response(200, json={
            "access_token": "synthetic-short-access-token", "expires_in": 900,
            "token_type": "Bearer", "scope": drive.SCOPE,
        })

    def get(self, url, **kwargs):
        return httpx.Response(200, json=self.folder)

    def patch(self, url, **kwargs):
        self.patches.append((url, kwargs))
        updated = {**self.folder, "appProperties": dict(picker.DESTINATION_MARKER)}
        return httpx.Response(200, json=updated)


def _prepare_picker(monkeypatch, *, transport=None):
    from app import main

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(drive, "_is_production", lambda: True)
    monkeypatch.setattr(main, "require_same_origin", lambda *_args: None)
    monkeypatch.setattr(picker, "_picker_config", lambda: picker.PickerConfig(
        PICKER_TEST_DEVELOPER_KEY, "123456789012", "synthetic-parent"))
    monkeypatch.setattr(drive, "_config", lambda: (
        "synthetic-client", "synthetic-client-secret", drive.GOOGLE_DRIVE_EXPECTED_REDIRECT_URI))
    monkeypatch.setattr(picker, "reauthenticate_admin", lambda _admin, password:
                        (_ for _ in ()).throw(AssertionError()) if password != "synthetic-password" else None)
    monkeypatch.setattr(picker, "matching_unused_totp_step", lambda *_args: 123456)
    if transport is not None:
        monkeypatch.setattr(picker, "HttpxDriveTransport", lambda: transport)


def test_picker_session_returns_only_short_lived_drive_file_access(drive_http, client_db, monkeypatch):
    client, session = drive_http
    cipher = _connect_workspace_for_picker(client_db, session)
    transport = PickerDriveTransport()
    _prepare_picker(monkeypatch, transport=transport)
    monkeypatch.setattr(drive, "_cipher", lambda: cipher)

    response = client.post("/admin/platform/drive/picker/session",
        headers={"Origin": "http://testserver"},
        json={"current_password": "synthetic-password", "totp_code": "123456"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {
        "access_token": "synthetic-short-access-token", "scope": drive.SCOPE,
        "expires_in": 900, "developer_key": PICKER_TEST_DEVELOPER_KEY,
        "project_number": "123456789012", "expected_parent_folder_id": "synthetic-parent",
    }
    assert "no-store" in response.headers["cache-control"]
    assert "synthetic-refresh-token" not in response.text
    assert transport.token_requests[0][1]["data"]["refresh_token"] == "synthetic-refresh-token"
    assert transport.token_requests[0][1]["data"]["client_secret"] == "synthetic-client-secret"


def test_picker_authorizes_only_expected_private_app_folder_and_audits_without_token(
        drive_http, client_db, monkeypatch):
    client, session = drive_http
    cipher = _connect_workspace_for_picker(client_db, session)
    folder_id = "synthetic-global-folder"
    transport = PickerDriveTransport({
        "id": folder_id, "name": picker.GLOBAL_FOLDER_NAME,
        "mimeType": "application/vnd.google-apps.folder", "parents": ["synthetic-parent"],
        "driveId": None, "ownedByMe": True, "isAppAuthorized": True, "trashed": False,
        "capabilities": {"canAddChildren": True}, "appProperties": {},
    })
    _prepare_picker(monkeypatch, transport=transport)
    monkeypatch.setattr(drive, "_cipher", lambda: cipher)

    response = client.post("/admin/platform/drive/picker/authorize",
        headers={"Origin": "http://testserver"},
        json={"folder_id": folder_id, "current_password": "synthetic-password", "totp_code": "123456"})

    assert response.status_code == 200, response.text
    assert response.json() == {
        "state": "selected", "folder_name": picker.GLOBAL_FOLDER_NAME, "folder_id": folder_id,
    }
    assert "no-store" in response.headers["cache-control"]
    assert len(transport.patches) == 1
    assert transport.patches[0][1]["json"]["appProperties"] == dict(picker.DESTINATION_MARKER)
    event = client_db.scalars(select(AuditEvent).where(
        AuditEvent.event == "google_drive.backup_folder_selected")).one()
    assert event.subject == folder_id
    assert "synthetic-short-access-token" not in response.text


def test_picker_rejects_folder_outside_expected_root_before_marker_write(
        drive_http, client_db, monkeypatch):
    client, session = drive_http
    cipher = _connect_workspace_for_picker(client_db, session)
    transport = PickerDriveTransport({
        "id": "synthetic-global-folder", "name": picker.GLOBAL_FOLDER_NAME,
        "mimeType": "application/vnd.google-apps.folder", "parents": ["wrong-parent"],
        "driveId": None, "ownedByMe": True, "isAppAuthorized": True, "trashed": False,
        "capabilities": {"canAddChildren": True}, "appProperties": {},
    })
    _prepare_picker(monkeypatch, transport=transport)
    monkeypatch.setattr(drive, "_cipher", lambda: cipher)

    response = client.post("/admin/platform/drive/picker/authorize",
        headers={"Origin": "http://testserver"},
        json={"folder_id": "synthetic-global-folder", "current_password": "synthetic-password",
              "totp_code": "123456"})

    assert response.status_code == 409, response.text
    assert transport.patches == []
    assert client_db.scalars(select(AuditEvent).where(
        AuditEvent.event == "google_drive.backup_folder_selected")).all() == []


def test_picker_configuration_metadata_requires_root_private_single_link_file():
    regular_file = SimpleNamespace(
        st_mode=picker.stat.S_IFREG | 0o400, st_uid=0, st_gid=0, st_nlink=1, st_size=256,
    )
    assert picker._config_metadata_is_safe(regular_file, posix=True)
    assert not picker._config_metadata_is_safe(
        SimpleNamespace(**{**vars(regular_file), "st_uid": 12345}), posix=True)
    assert not picker._config_metadata_is_safe(
        SimpleNamespace(**{**vars(regular_file), "st_gid": 12345}), posix=True)
    assert not picker._config_metadata_is_safe(
        SimpleNamespace(**{**vars(regular_file), "st_mode": picker.stat.S_IFREG | 0o444}), posix=True)
    assert not picker._config_metadata_is_safe(
        SimpleNamespace(**{**vars(regular_file), "st_nlink": 2}), posix=True)
    assert not picker._config_metadata_is_safe(
        SimpleNamespace(**{**vars(regular_file), "st_size": 0}), posix=True)
    assert picker._config_metadata_is_safe(
        SimpleNamespace(**{**vars(regular_file), "st_uid": 12345, "st_mode": picker.stat.S_IFREG | 0o644}),
        posix=False,
    )


def test_picker_configuration_requires_private_exact_file(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    host_is_posix = os.name == "posix"
    path = tmp_path / "picker-config.json"
    path.write_text(json.dumps({
        "developer_key": PICKER_TEST_DEVELOPER_KEY,
        "project_number": "123456789012", "expected_parent_folder_id": "synthetic-parent",
    }), encoding="utf-8")
    path.chmod(0o400)
    monkeypatch.setattr(picker, "GOOGLE_DRIVE_PICKER_CONFIG_PATH", path)
    if host_is_posix:
        actual_fstat = os.fstat

        def root_owned_fstat(descriptor):
            metadata = actual_fstat(descriptor)
            return SimpleNamespace(
                st_mode=metadata.st_mode, st_uid=0, st_gid=0,
                st_nlink=metadata.st_nlink, st_size=metadata.st_size,
            )

        monkeypatch.setattr(picker.os, "fstat", root_owned_fstat)
    assert picker._picker_config() == picker.PickerConfig(
        PICKER_TEST_DEVELOPER_KEY, "123456789012", "synthetic-parent")

    if host_is_posix:
        path.chmod(0o444)
        with pytest.raises(HTTPException) as rejected:
            picker._picker_config()
        assert rejected.value.status_code == 503

        path.chmod(0o400)
        hardlink = tmp_path / "picker-config-hardlink.json"
        hardlink.hardlink_to(path)
        with pytest.raises(HTTPException) as linked:
            picker._picker_config()
        assert linked.value.status_code == 503
        hardlink.unlink()

        target = tmp_path / "picker-config-target.json"
        target.write_bytes(path.read_bytes())
        target.chmod(0o400)
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(HTTPException) as symlinked:
            picker._picker_config()
        assert symlinked.value.status_code == 503
