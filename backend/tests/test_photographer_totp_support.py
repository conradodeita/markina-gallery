"""Recuperação assistida isolada com reautenticação e outbox transacional."""

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pyotp
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import main
from app import photographer_totp_support as support
from app import platform_console as console
from app.admin_security import AdminSecurityConfigurationError
from app.auth import (
    AdminActionToken,
    AdminTotpEnrollment,
    AdminTotpRecoveryCode,
    AdminUser,
    AuthChallenge,
    AuthSession,
    EmailDelivery,
    InstallationOperator,
    PhotographerSignup,
    PlatformAdminEvent,
    Tenant,
    now,
    password_hasher,
)
from app.totp_crypto import TotpSecretCipher
from app.totp_recovery import create_recovery_codes, hash_recovery_code, recovery_code_selector
from tests.test_platform_console_status import PASSWORD, SECRET, context
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
PHOTO_PASSWORD = "SyntheticPhotographer!20261104"


@pytest.fixture
def assistance(client_db):
    session, tenant_id, admin_id = context(client_db)
    admin = client_db.get(AdminUser, admin_id)
    admin.password_hash = password_hasher.hash(PHOTO_PASSWORD)
    admin.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    client_db.add(PhotographerSignup(photographer_name="Conta sintética", email=admin.email, state="active",
                                     otp_expires_at=now(), reserved_admin_id=admin_id, activated_tenant_id=tenant_id))
    target_session = AuthSession(id=uuid4(), token_hash=uuid4().hex, role="admin", subject_id=admin_id,
                                 admin_subject_id=admin_id, tenant_id=tenant_id, expires_at=now()+timedelta(minutes=5))
    client_db.add(target_session)
    client_db.flush()
    recovery = create_recovery_codes(1)[0]
    attempt_id = uuid4()
    client_db.add_all([
        AdminTotpRecoveryCode(admin_user_id=admin_id, code_selector=recovery_code_selector(recovery), code_hash=hash_recovery_code(recovery)),
        AuthChallenge(kind="admin_totp", subject=str(admin_id), tenant_id=tenant_id, secret_hash="synthetic", expires_at=now()+timedelta(minutes=5)),
        AdminActionToken(admin_id=admin_id, purpose="password_reset", token_hash=uuid4().hex, expires_at=now()+timedelta(minutes=5)),
        AdminTotpEnrollment(id=attempt_id, admin_user_id=admin_id, tenant_id=tenant_id, session_id=target_session.id,
                            secret_envelope=TotpSecretCipher.from_environment().encrypt(SECRET, admin_id=attempt_id), expires_at=now()+timedelta(minutes=5)),
    ])
    client_db.commit()
    return session, tenant_id, admin_id


def intention(db, admin_id, **changes):
    admin = db.get(AdminUser, admin_id)
    values = {"request_id": uuid4(), "reason_code": "lost_device", "current_password": PASSWORD,
              "totp_code": pyotp.TOTP(SECRET).now(),
              "expected_version": support.factor_version(admin.id, admin._totp_secret_envelope, admin._totp_secret_legacy)}
    values.update(changes)
    return support.RevokeInput(**values)


def test_revoke_preserves_password_revokes_material_and_notifies_once(assistance, client_db):
    session, tenant_id, admin_id = assistance
    old_password = client_db.get(AdminUser, admin_id).password_hash
    request = intention(client_db, admin_id)
    assert support.revoke_photographer_totp(client_db, session, tenant_id, admin_id, request) == {"completed": True, "replayed": False}
    client_db.commit()
    admin = client_db.get(AdminUser, admin_id, populate_existing=True)
    assert not admin.totp_enabled and admin._totp_secret_envelope is None and admin._totp_secret_legacy is None
    assert admin.password_hash == old_password
    assert client_db.get(Tenant, tenant_id).status == "active"
    assert all(row.revoked_at for row in client_db.scalars(select(AuthSession)))
    assert all(row.revoked_at for row in client_db.scalars(select(AdminTotpRecoveryCode)))
    assert all(row.used_at for row in client_db.scalars(select(AuthChallenge)))
    assert all(row.used_at for row in client_db.scalars(select(AdminActionToken)))
    attempt = client_db.scalar(select(AdminTotpEnrollment))
    assert attempt.used_at and attempt.secret_envelope is None
    notice = client_db.scalar(select(EmailDelivery))
    assert notice.kind == "security_notice" and notice.status == "queued"
    assert admin.email not in notice.encrypted_payload
    audit = client_db.scalar(select(PlatformAdminEvent))
    assert (audit.actor_admin_id, audit.tenant_id, audit.object_id, audit.reason_code) == (session.subject_id, tenant_id, admin_id, "lost_device")
    assert PASSWORD not in str(audit.__dict__) and SECRET not in str(audit.__dict__)
    assert support.revoke_photographer_totp(client_db, session, tenant_id, admin_id, request)["replayed"]
    assert len(list(client_db.scalars(select(EmailDelivery)))) == 1
    assert len(list(client_db.scalars(select(PlatformAdminEvent)))) == 1
    with pytest.raises(HTTPException) as reused:
        support.revoke_photographer_totp(client_db, session, tenant_id, admin_id,
                                         request.model_copy(update={"reason_code": "assisted_recovery"}))
    assert reused.value.status_code == 409
    email = admin.email
    client_db.commit()
    app = FastAPI()
    app.add_api_route("/auth/admin/password", main.admin_password, methods=["POST"])
    app.dependency_overrides[main.db_session] = lambda: client_db
    login = TestClient(app).post("/auth/admin/password", json={"email": email, "password": PHOTO_PASSWORD})
    assert login.json() == {"destination": "/admin"}


@pytest.mark.parametrize("case", ["bad_password", "bad_factor", "stale_version", "wrong_tenant", "owner", "legacy"])
def test_invalid_support_operations_preserve_factor_and_sessions(assistance, client_db, case):
    session, tenant_id, admin_id = assistance
    changes = {}
    if case == "bad_password": changes["current_password"] = "invalid"
    if case == "bad_factor": changes["totp_code"] = "invalid"
    if case == "stale_version": changes["expected_version"] = "0"*64
    request = intention(client_db, admin_id, **changes)
    target_tenant = session.tenant_id if case in {"wrong_tenant", "owner"} else tenant_id
    target_admin = session.subject_id if case == "owner" else admin_id
    if case == "legacy":
        client_db.delete(client_db.scalar(select(PhotographerSignup)))
        client_db.commit()
    with pytest.raises(HTTPException) as denied:
        support.revoke_photographer_totp(client_db, session, target_tenant, target_admin, request)
    assert denied.value.status_code in {403, 409}
    assert client_db.get(AdminUser, admin_id, populate_existing=True).totp_enabled
    assert all(row.revoked_at is None for row in client_db.scalars(select(AuthSession)))
    assert client_db.scalar(select(EmailDelivery)) is None


def test_operator_and_photographer_cannot_revoke(assistance, client_db):
    _session, tenant_id, admin_id = assistance
    session = SimpleNamespace(subject_id=admin_id, tenant_id=tenant_id)
    request = intention(client_db, admin_id)
    for operator in (False, True):
        if operator:
            client_db.add(InstallationOperator(admin_user_id=admin_id, active=True,
                                               authorization_reference="synthetic", granted_at=now(), updated_at=now()))
            client_db.commit()
        with pytest.raises(HTTPException) as denied:
            support.revoke_photographer_totp(client_db, session, tenant_id, admin_id, request)
        assert denied.value.status_code == 403
    assert client_db.get(AdminUser, admin_id).totp_enabled


def test_notice_failure_rolls_back_factor_session_and_owner_step(assistance, client_db, monkeypatch):
    session, tenant_id, admin_id = assistance
    request = intention(client_db, admin_id)
    def fail_notice(*args, **kwargs):
        raise AdminSecurityConfigurationError("synthetic configuration failure")
    monkeypatch.setattr(support, "enqueue_email", fail_notice)
    with pytest.raises(HTTPException) as failed:
        support.revoke_photographer_totp(client_db, session, tenant_id, admin_id, request)
    assert failed.value.status_code == 503
    assert client_db.get(AdminUser, admin_id, populate_existing=True).totp_enabled
    assert client_db.get(AdminUser, session.subject_id).totp_last_used_step is None
    assert all(row.revoked_at is None for row in client_db.scalars(select(AuthSession)))
    assert client_db.scalar(select(EmailDelivery)) is None
    assert client_db.scalar(select(PlatformAdminEvent)) is None


def test_replay_and_stale_confirmation_do_not_revoke_a_new_factor(assistance, client_db):
    session, tenant_id, admin_id = assistance
    original = intention(client_db, admin_id)
    support.revoke_photographer_totp(client_db, session, tenant_id, admin_id, original)
    client_db.commit()
    admin = client_db.get(AdminUser, admin_id)
    admin.totp_enabled = True
    admin.totp_secret = pyotp.random_base32()
    client_db.commit()
    envelope = admin._totp_secret_envelope
    assert support.revoke_photographer_totp(client_db, session, tenant_id, admin_id, original)["replayed"]
    assert admin.totp_enabled and admin._totp_secret_envelope == envelope
    with pytest.raises(HTTPException) as stale:
        support.revoke_photographer_totp(client_db, session, tenant_id, admin_id,
                                         original.model_copy(update={"request_id": uuid4()}))
    assert stale.value.status_code == 409
    assert admin.totp_enabled and admin._totp_secret_envelope == envelope
    assert len(list(client_db.scalars(select(EmailDelivery)))) == 1


def test_http_support_lookup_is_minimal_owner_only_and_bound_to_tenant(assistance, client_db, monkeypatch):
    session, tenant_id, admin_id = assistance
    monkeypatch.setattr(console, "SessionLocal", lambda: client_db)
    def current(_request, _role, *, platform_scope=False):
        assert platform_scope is True
        return session
    monkeypatch.setattr(console, "current_session", current)
    app = FastAPI()
    app.include_router(support.router)
    client = TestClient(app)
    root = f"/admin/platform/console/tenants/{tenant_id}/totp-support"
    response = client.get(root)
    assert response.status_code == 200
    assert set(response.json()) == {"available", "admin_id", "email_masked", "totp_enabled", "version"}
    assert response.json()["admin_id"] == str(admin_id)
    assert SECRET not in response.text and "envelope" not in response.text
    assert "no-store" in response.headers["cache-control"]
    assert client.get(f"/admin/platform/console/tenants/{session.tenant_id}/totp-support").json() == {"available": False}
    session.subject_id, session.tenant_id = admin_id, tenant_id
    assert client.get(root).status_code == 403


@pytest.mark.parametrize("session_changed", [False, True])
def test_http_commit_rechecks_session_and_never_returns_credentials(assistance, client_db, monkeypatch, session_changed):
    session, tenant_id, admin_id = assistance
    request = intention(client_db, admin_id)
    body = request.model_dump(mode="json")
    body.update(current_password=PASSWORD, totp_code=request.totp_code.get_secret_value())
    monkeypatch.setattr(console, "SessionLocal", lambda: client_db)
    calls = 0
    def current(*args, platform_scope=False):
        nonlocal calls
        assert platform_scope is True
        calls += 1
        if session_changed and calls > 1:
            return SimpleNamespace(id=uuid4(), subject_id=session.subject_id, tenant_id=session.tenant_id)
        return session
    monkeypatch.setattr(console, "current_session", current)
    app = FastAPI()
    app.include_router(support.router)
    app.add_exception_handler(RequestValidationError, main.protect_credential_validation_input)
    client = TestClient(app)
    path = f"/admin/platform/console/tenants/{tenant_id}/photographers/{admin_id}/revoke-totp"
    response = client.post(path, json=body)
    assert PASSWORD not in response.text and SECRET not in response.text
    assert response.status_code == (403 if session_changed else 200)
    assert client_db.get(AdminUser, admin_id, populate_existing=True).totp_enabled is session_changed
    assert len(list(client_db.scalars(select(EmailDelivery)))) == (0 if session_changed else 1)
    if not session_changed:
        assert client.post(path, json=body).json() == {"completed": True, "replayed": True}
        assert len(list(client_db.scalars(select(EmailDelivery)))) == 1
        invalid = client.post(path, json={**body, "reason_code": "invalid"})
        assert invalid.status_code == 422 and PASSWORD not in invalid.text
