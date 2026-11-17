"""Contrato HTTP de exclusão fria no console PlatformOwner."""

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pyotp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import platform_console as console
from app.auth import (
    AdminUser,
    PlatformAdminEvent,
    Tenant,
    TenantAdmin,
    TenantClosureMediaDeletionBatch,
    TenantClosureRequest,
    now,
    password_hasher,
)
from app.tenant_media_deletion import DELETION_CONFIRMATION
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


@pytest.fixture
def media_deletion_http(client_db, monkeypatch):
    owner_tenant, tenant, owner, _photographer = create_accounts(client_db)
    client_db.commit()
    session = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
    monkeypatch.setattr(console, "SessionLocal", lambda: client_db)
    monkeypatch.setattr(console, "current_session", lambda *_args, **_kwargs: session)
    monkeypatch.setattr(console, "enforce_rate_limit", lambda *_args, **_kwargs: None)
    app = FastAPI()
    app.include_router(console.router)
    return TestClient(app), tenant.id, owner.id


def test_media_deletion_http_requires_owner_reauth_and_audits_idempotent_request(
    media_deletion_http, client_db, monkeypatch,
):
    from app import main, tenant_media_deletion

    client, tenant_id, owner_id = media_deletion_http
    owner = client_db.get(AdminUser, owner_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    client_db.commit()
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    rate_limit_actions = []
    monkeypatch.setattr(
        console,
        "enforce_rate_limit",
        lambda _db, action, *_args, **_kwargs: rate_limit_actions.append(action),
    )

    batch_id = uuid4()
    body_result = {
        "eligible": False,
        "blocker": "deletion_already_requested",
        "confirmation_phrase": DELETION_CONFIRMATION,
        "review_due": True,
        "batch": {
            "batch_id": str(batch_id),
            "state": "queued",
            "object_count": 2,
            "verified_deleted_object_count": 0,
            "cycle_count": 1,
            "operations": [{"status": "queued", "error_code": None}],
            "retry_available": False,
        },
        "observed_at": now().isoformat(),
    }
    calls = []
    monkeypatch.setattr(
        tenant_media_deletion,
        "request_media_deletion",
        lambda db, **kwargs: calls.append(kwargs) or {**body_result, "replayed": False},
    )
    monkeypatch.setattr(
        tenant_media_deletion,
        "media_deletion_console_payload",
        lambda _db, **_kwargs: body_result,
    )

    request_id = uuid4()
    body = {
        "request_id": str(request_id),
        "confirm_phrase": DELETION_CONFIRMATION,
        "current_password": "SyntheticOwnerPassword!2026",
        "totp_code": pyotp.TOTP(owner.totp_secret).now(),
    }
    path = f"/admin/platform/console/tenants/{tenant_id}/closure/media-deletion"
    response = client.post(path, json=body)
    assert response.status_code == 202, response.text
    assert response.json()["batch"]["object_count"] == 2
    assert calls == [{
        "owner_id": owner_id,
        "tenant_id": tenant_id,
        "request_id": request_id,
        "confirmation": DELETION_CONFIRMATION,
    }]
    assert rate_limit_actions == ["platform_tenant_media_deletion"]
    assert {"private", "no-store"} <= set(response.headers["cache-control"].split(", "))
    assert "SyntheticOwnerPassword!2026" not in response.text
    assert body["totp_code"] not in response.text

    event = client_db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == request_id,
    ))
    assert event is not None
    assert event.action == "tenant.media_deletion_requested"
    assert event.result == "success"
    assert event.tenant_id == tenant_id and event.object_id == batch_id

    replay = client.post(path, json=body)
    assert replay.status_code == 202, replay.text
    assert replay.json()["replayed"] is True
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("route_suffix", "action", "previous_status", "next_status", "expected_status"),
    [
        ("media-deletion", "tenant.media_deletion_requested", "closed", "queued", 202),
        ("media-deletion/retry", "tenant.media_deletion_retry", "attention_required", "queued", 202),
        ("profile-reduction", "tenant.profile_reduced", "retained", "reduced", 200),
        ("reopen", "tenant.reopened", "closed", "open", 200),
    ],
)
def test_platform_console_rechecks_idempotency_after_admin_lock(
    media_deletion_http, client_db, monkeypatch,
    route_suffix, action, previous_status, next_status, expected_status,
):
    from app import main, tenant_media_deletion, tenant_profile_retention

    client, tenant_id, owner_id = media_deletion_http
    owner = client_db.get(AdminUser, owner_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    client_db.commit()
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)

    response_body = {
        "eligible": False,
        "blocker": "deletion_already_requested",
        "confirmation_phrase": DELETION_CONFIRMATION,
        "review_due": True,
        "batch": {
            "batch_id": str(uuid4()),
            "state": "queued",
            "object_count": 1,
            "verified_deleted_object_count": 0,
            "cycle_count": 1,
            "operations": [{"status": "queued", "error_code": None}],
            "retry_available": False,
        },
        "observed_at": now().isoformat(),
    }
    monkeypatch.setattr(
        tenant_media_deletion,
        "media_deletion_console_payload",
        lambda _db, **_kwargs: response_body,
    )
    monkeypatch.setattr(
        tenant_profile_retention,
        "profile_retention_payload",
        lambda _db, **_kwargs: {"state": "reduced"},
    )

    def unexpected_action(*_args, **_kwargs):
        raise AssertionError("uma repetição concorrente deve retornar o evento existente")

    monkeypatch.setattr(tenant_media_deletion, "request_media_deletion", unexpected_action)
    monkeypatch.setattr(tenant_media_deletion, "retry_media_deletion", unexpected_action)
    monkeypatch.setattr(console, "enforce_rate_limit", unexpected_action)
    monkeypatch.setattr(console, "reauthenticate_console_owner", unexpected_action)

    request_id = uuid4()
    injected = False
    scalar = client_db.scalar

    def inject_completed_request_after_admin_lock(statement, *args, **kwargs):
        nonlocal injected
        result = scalar(statement, *args, **kwargs)
        if (
            not injected
            and getattr(statement, "_for_update_arg", None) is not None
            and "admin_user" in str(statement).lower()
        ):
            client_db.add(PlatformAdminEvent(
                request_id=request_id,
                actor_admin_id=owner_id,
                object_id=uuid4(),
                tenant_id=tenant_id,
                action=action,
                previous_status=previous_status,
                next_status=next_status,
                result="success",
                created_at=now(),
            ))
            client_db.commit()
            injected = True
        return result

    monkeypatch.setattr(client_db, "scalar", inject_completed_request_after_admin_lock)
    body = {
        "request_id": str(request_id),
        "confirm_phrase": DELETION_CONFIRMATION,
        "current_password": "SyntheticOwnerPassword!2026",
        "totp_code": pyotp.TOTP(owner.totp_secret).now(),
    }
    if route_suffix == "profile-reduction":
        body["confirm_review"] = True
    elif route_suffix == "reopen":
        body.pop("confirm_phrase")
    response = client.post(
        f"/admin/platform/console/tenants/{tenant_id}/closure/{route_suffix}", json=body,
    )

    assert injected is True
    assert response.status_code == expected_status, response.text
    assert response.json()["replayed"] is True
    assert scalar(select(PlatformAdminEvent.id).where(
        PlatformAdminEvent.request_id == request_id,
    )) is not None


def test_media_deletion_http_rejects_invalid_credentials_before_service(
    media_deletion_http, client_db, monkeypatch,
):
    from app import main, tenant_media_deletion

    client, tenant_id, owner_id = media_deletion_http
    owner = client_db.get(AdminUser, owner_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    client_db.commit()
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    service_called = False

    def request_deletion(*_args, **_kwargs):
        nonlocal service_called
        service_called = True
        raise AssertionError("serviço não deve rodar após falha de autenticação")

    monkeypatch.setattr(tenant_media_deletion, "request_media_deletion", request_deletion)
    response = client.post(
        f"/admin/platform/console/tenants/{tenant_id}/closure/media-deletion",
        json={
            "request_id": str(uuid4()),
            "confirm_phrase": DELETION_CONFIRMATION,
            "current_password": "wrong-password",
            "totp_code": pyotp.TOTP(owner.totp_secret).now(),
        },
    )
    assert response.status_code == 403
    assert service_called is False
    assert "wrong-password" not in response.text
    denied = client_db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.tenant_id == tenant_id,
        PlatformAdminEvent.action == "console.access_denied",
    ))
    assert denied is not None and denied.result == "denied"


def test_media_deletion_status_is_owner_scoped_and_reports_sanitized_blocker(
    media_deletion_http,
):
    client, tenant_id, _owner_id = media_deletion_http
    response = client.get(f"/admin/platform/console/tenants/{tenant_id}/closure")
    assert response.status_code == 200, response.text
    assert response.json()["media_deletion"]["eligible"] is False
    assert response.json()["media_deletion"]["blocker"] == "account_not_closed"
    assert "owner@example.test" not in response.text
    assert {"private", "no-store"} <= set(response.headers["cache-control"].split(", "))


def test_media_deletion_action_rejects_cross_origin_before_any_service_call(
    media_deletion_http, client_db, monkeypatch,
):
    from app import tenant_media_deletion

    client, tenant_id, _owner_id = media_deletion_http
    service_called = False

    def request_deletion(*_args, **_kwargs):
        nonlocal service_called
        service_called = True
        raise AssertionError("origem externa não deve alcançar o serviço")

    monkeypatch.setattr(tenant_media_deletion, "request_media_deletion", request_deletion)
    response = client.post(
        f"/admin/platform/console/tenants/{tenant_id}/closure/media-deletion",
        headers={"Origin": "https://attacker.example"},
        json={
            "request_id": str(uuid4()),
            "confirm_phrase": DELETION_CONFIRMATION,
            "current_password": "irrelevant",
            "totp_code": "123456",
        },
    )
    assert response.status_code == 403
    assert service_called is False
    assert client_db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.action == "tenant.media_deletion_requested",
    )) is None


def test_media_deletion_rejects_owner_session_bound_to_another_tenant(
    media_deletion_http, client_db, monkeypatch,
):
    from app import tenant_media_deletion

    client, tenant_id, owner_id = media_deletion_http
    owner_tenant_id = client_db.scalar(select(TenantAdmin.tenant_id).where(
        TenantAdmin.admin_user_id == owner_id,
    ))
    assert owner_tenant_id is not None and owner_tenant_id != tenant_id
    monkeypatch.setattr(console, "current_session", lambda *_args, **_kwargs: SimpleNamespace(
        id=uuid4(), subject_id=owner_id, tenant_id=tenant_id,
    ))
    service_called = False

    def request_deletion(*_args, **_kwargs):
        nonlocal service_called
        service_called = True
        raise AssertionError("sessão tenant-divergente não deve alcançar o serviço")

    monkeypatch.setattr(tenant_media_deletion, "request_media_deletion", request_deletion)
    response = client.post(
        f"/admin/platform/console/tenants/{tenant_id}/closure/media-deletion",
        json={
            "request_id": str(uuid4()),
            "confirm_phrase": DELETION_CONFIRMATION,
            "current_password": "irrelevant",
            "totp_code": "123456",
        },
    )
    assert response.status_code == 403
    assert service_called is False


def test_media_deletion_retry_requires_reauth_and_audits_the_retry(
    media_deletion_http, client_db, monkeypatch,
):
    from app import main, tenant_media_deletion

    client, tenant_id, owner_id = media_deletion_http
    owner = client_db.get(AdminUser, owner_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    client_db.get(Tenant, tenant_id).lifecycle = "closed"
    photographer_id = client_db.scalar(select(TenantAdmin.admin_user_id).where(
        TenantAdmin.tenant_id == tenant_id,
    ))
    assert photographer_id is not None
    closed_at = now() - timedelta(days=4000)
    closure = TenantClosureRequest(
        tenant_id=tenant_id,
        request_id=uuid4(),
        requested_by=photographer_id,
        state="closed",
        requested_at=closed_at - timedelta(days=1),
        closed_at=closed_at,
        terms_version="synthetic-terms-v1",
        terms_sha256="a" * 64,
        balance_snapshot=0,
        balance_acknowledged=True,
    )
    client_db.add(closure)
    client_db.flush()
    batch_id = uuid4()
    batch = TenantClosureMediaDeletionBatch(
        id=batch_id,
        tenant_id=tenant_id,
        closure_request_id=closure.id,
        requested_by_owner_admin_id=owner_id,
        request_id=uuid4(),
        state="attention_required",
        inventory_sha256="a" * 64,
        object_count=2,
        verified_deleted_object_count=1,
        total_bytes=20,
    )
    client_db.add(batch)
    client_db.commit()
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    rate_limit_actions = []
    monkeypatch.setattr(
        console,
        "enforce_rate_limit",
        lambda _db, action, *_args, **_kwargs: rate_limit_actions.append(action),
    )

    response_body = {
        "eligible": False,
        "blocker": "deletion_already_requested",
        "confirmation_phrase": DELETION_CONFIRMATION,
        "review_due": True,
        "batch": {
            "batch_id": str(batch_id),
            "state": "queued",
            "object_count": 2,
            "verified_deleted_object_count": 1,
            "cycle_count": 1,
            "operations": [{"status": "queued", "error_code": None}],
            "retry_available": False,
        },
        "observed_at": now().isoformat(),
    }
    calls = []

    def retry(db, **kwargs):
        calls.append(kwargs)
        current = db.get(TenantClosureMediaDeletionBatch, batch_id)
        current.state = "queued"
        return {**response_body, "replayed": False}

    monkeypatch.setattr(tenant_media_deletion, "retry_media_deletion", retry)
    monkeypatch.setattr(
        tenant_media_deletion,
        "media_deletion_console_payload",
        lambda _db, **_kwargs: response_body,
    )
    request_id = uuid4()
    body = {
        "request_id": str(request_id),
        "confirm_phrase": DELETION_CONFIRMATION,
        "current_password": "SyntheticOwnerPassword!2026",
        "totp_code": pyotp.TOTP(owner.totp_secret).now(),
    }
    path = f"/admin/platform/console/tenants/{tenant_id}/closure/media-deletion/retry"
    response = client.post(path, json=body)
    assert response.status_code == 202, response.text
    assert calls == [{
        "owner_id": owner_id,
        "tenant_id": tenant_id,
        "confirmation": DELETION_CONFIRMATION,
    }]
    assert rate_limit_actions == ["platform_tenant_media_deletion_retry"]
    event = client_db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == request_id,
    ))
    assert event is not None
    assert (event.action, event.previous_status, event.next_status, event.result) == (
        "tenant.media_deletion_retry", "attention_required", "queued", "success",
    )
    replay = client.post(path, json=body)
    assert replay.status_code == 202, replay.text
    assert replay.json()["replayed"] is True
    assert len(calls) == 1
