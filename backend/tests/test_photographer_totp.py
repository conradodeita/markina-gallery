"""Enrollment HTTP real com escopo, expiração e login após ativação."""

from datetime import timedelta
from uuid import uuid4

import pyotp
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import main, photographer_totp
from app.admin_security import cleanup_admin_security_material
from app.auth import (
    AdminTotpEnrollment,
    AdminTotpRecoveryCode,
    AdminUser,
    AuthChallenge,
    AuthSession,
    Tenant,
    TenantAdmin,
    now,
)
from app.system_monitor.models import PlatformOwner
from tests.test_photographer_signup import PASSWORD, finish, start, verify
from tests.test_photographer_signup import client_db as _client_db
from tests.test_photographer_signup import proof as _proof

client_db = _client_db
proof = _proof
ROOT = "/api/admin/security/totp/enrollment"


@pytest.fixture
def enrollment(proof, client_db, monkeypatch):
    client, messages = proof
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "100")
    monkeypatch.setattr(photographer_totp, "SessionLocal", sessionmaker(bind=client_db.get_bind(), expire_on_commit=False))
    client.app.include_router(photographer_totp.router, prefix="/api")
    client.app.add_api_route("/api/auth/admin/password", main.admin_password, methods=["POST"], status_code=202)
    client.app.add_api_route("/api/auth/admin/totp", main.admin_totp, methods=["POST"])
    client.app.dependency_overrides[main.db_session] = lambda: client_db
    assert finish(client, verify(client, messages, start(client))).status_code == 200
    return client


def test_confirm_activates_factor_once_revokes_session_and_login_rejects_replay(enrollment, client_db):
    client = enrollment
    result = client.post(ROOT, json={"current_password": PASSWORD})
    assert result.status_code == 200 and "no-store" in result.headers["cache-control"]
    setup = result.json()
    assert setup["qr_data_url"].startswith("data:image/png;base64,")
    row = client_db.scalar(select(AdminTotpEnrollment))
    assert setup["secret"] not in row.secret_envelope
    assert not client_db.get(AdminUser, row.admin_user_id).totp_enabled
    client_db.commit()
    code = pyotp.TOTP(setup["secret"]).now()
    activated = client.post(ROOT + "/confirm", json={"enrollment_id": setup["enrollment_id"], "code": code})
    assert activated.status_code == 200
    assert len(set(activated.json()["codes"])) == 10
    client_db.expire_all()
    row = client_db.scalar(select(AdminTotpEnrollment))
    admin = client_db.get(AdminUser, row.admin_user_id)
    email = admin.email
    assert admin.totp_enabled and admin.totp_secret == setup["secret"]
    assert row.secret_envelope is None and row.used_at is not None
    assert all(s.revoked_at for s in client_db.scalars(select(AuthSession)))
    saved = list(client_db.scalars(select(AdminTotpRecoveryCode)))
    assert len(saved) == 10 and all(item.code_hash not in activated.json()["codes"] for item in saved)
    client_db.commit()
    assert client.get("/api/probe-admin").status_code == 403
    login = client.post("/api/auth/admin/password", json={"email": email, "password": PASSWORD})
    assert "challenge_id" in login.json() and "destination" not in login.json()
    assert client.post("/api/auth/admin/totp", json={"challenge_id": login.json()["challenge_id"], "code": code}).status_code == 401
    accepted = client.post("/api/auth/admin/totp", json={"challenge_id": login.json()["challenge_id"], "code": activated.json()["codes"][0]})
    assert accepted.status_code == 200
    assert client.post(ROOT + "/confirm", json={"enrollment_id": setup["enrollment_id"], "code": code}).status_code == 409


def test_expired_and_different_session_attempts_cannot_activate(enrollment, client_db):
    client = enrollment
    setup = client.post(ROOT, json={"current_password": PASSWORD}).json()
    row = client_db.scalar(select(AdminTotpEnrollment))
    original_session = row.session_id
    other_id = uuid4()
    client_db.add(AuthSession(id=other_id, token_hash=uuid4().hex, role="admin", subject_id=row.admin_user_id,
                             admin_subject_id=row.admin_user_id, tenant_id=row.tenant_id, expires_at=now()+timedelta(minutes=5)))
    client_db.flush()
    row.session_id = other_id
    client_db.commit()
    payload = {"enrollment_id": setup["enrollment_id"], "code": pyotp.TOTP(setup["secret"]).now()}
    assert client.post(ROOT + "/confirm", json=payload).status_code == 400
    client_db.refresh(row)
    row.session_id = original_session
    row.expires_at = now() - timedelta(seconds=1)
    client_db.commit()
    assert client.post(ROOT + "/confirm", json=payload).status_code == 400
    client_db.refresh(row)
    assert row.secret_envelope is None and row.used_at is not None
    assert not client_db.get(AdminUser, row.admin_user_id).totp_enabled


def test_wrong_password_rotation_and_attempt_limit_preserve_password_only_state(enrollment, client_db):
    client = enrollment
    assert client.post(ROOT, json={"current_password": "invalid"}).status_code == 400
    setup = client.post(ROOT, json={"current_password": PASSWORD}).json()
    replacement = client.post(ROOT, json={"current_password": PASSWORD}).json()
    assert setup["enrollment_id"] != replacement["enrollment_id"]
    assert client.post(ROOT+"/confirm", json={"enrollment_id": setup["enrollment_id"], "code": pyotp.TOTP(setup["secret"]).now()}).status_code == 400
    for _ in range(5):
        result = client.post(ROOT+"/confirm", json={"enrollment_id": replacement["enrollment_id"], "code": "not-a-totp"})
        assert result.status_code == 400
    client_db.expire_all()
    row = client_db.scalar(select(AdminTotpEnrollment))
    assert row.attempts == 5 and row.secret_envelope is None
    assert not client_db.get(AdminUser, row.admin_user_id).totp_enabled


def test_enrollment_password_reauth_is_rate_limited(enrollment, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "5")
    for _ in range(5):
        assert enrollment.post(ROOT, json={"current_password": "invalid"}).status_code == 400
    assert enrollment.post(ROOT, json={"current_password": "invalid"}).status_code == 429


def test_other_website_tenant_cannot_confirm_attempt(enrollment, proof, client_db):
    client = enrollment
    _, messages = proof
    setup = client.post(ROOT, json={"current_password": PASSWORD}).json()
    second = start(client, email="other-tenant@example.test")
    assert finish(client, verify(client, messages, second)).status_code == 200
    result = client.post(ROOT + "/confirm", json={"enrollment_id": setup["enrollment_id"], "code": pyotp.TOTP(setup["secret"]).now()})
    assert result.status_code == 400
    assert all(not admin.totp_enabled for admin in client_db.scalars(select(AdminUser)))


def test_owner_cannot_enter_optional_enrollment_even_with_signup_origin(enrollment, client_db):
    admin = client_db.scalar(select(AdminUser))
    client_db.add(PlatformOwner(singleton=1, admin_user_id=admin.id, authorization_reference="synthetic-owner-proof"))
    client_db.commit()
    assert enrollment.post(ROOT, json={"current_password": PASSWORD}).status_code == 403
    assert client_db.scalar(select(AdminTotpEnrollment)) is None
    client_db.commit()
    login = enrollment.post("/api/auth/admin/password", json={"email": admin.email, "password": PASSWORD})
    assert "challenge_id" in login.json() and "destination" not in login.json()


def test_security_cleanup_scrubs_expired_enrollment_without_activating(enrollment, client_db):
    assert enrollment.post(ROOT, json={"current_password": PASSWORD}).status_code == 200
    row = client_db.scalar(select(AdminTotpEnrollment))
    row.expires_at = now() - timedelta(seconds=1)
    client_db.commit()
    assert cleanup_admin_security_material(client_db, tenant_id=row.tenant_id) == 1
    client_db.refresh(row)
    assert row.secret_envelope is None
    assert not client_db.get(AdminUser, row.admin_user_id).totp_enabled


@pytest.mark.parametrize("invalid_context", ["suspended", "inactive_membership"])
def test_password_only_login_does_not_create_session_for_invalid_context(enrollment, client_db, invalid_context):
    admin = client_db.scalar(select(AdminUser))
    membership = client_db.scalar(select(TenantAdmin).where(TenantAdmin.admin_user_id == admin.id))
    email = admin.email
    if invalid_context == "suspended":
        client_db.get(Tenant, membership.tenant_id).status = "suspended"
    else:
        membership.active = False
    before = len(list(client_db.scalars(select(AuthSession))))
    client_db.commit()
    denied = enrollment.post("/api/auth/admin/password", json={"email": email, "password": PASSWORD})
    assert denied.status_code == 401 and "destination" not in denied.json()
    assert len(list(client_db.scalars(select(AuthSession)))) == before


def test_closed_platform_owner_login_redirects_to_platform_console(enrollment, client_db):
    admin = client_db.scalar(select(AdminUser))
    setup = enrollment.post(ROOT, json={"current_password": PASSWORD})
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    activated = enrollment.post(ROOT + "/confirm", json={
        "enrollment_id": setup.json()["enrollment_id"],
        "code": pyotp.TOTP(secret).now(),
    })
    assert activated.status_code == 200

    membership = client_db.scalar(select(TenantAdmin).where(TenantAdmin.admin_user_id == admin.id))
    tenant = client_db.get(Tenant, membership.tenant_id)
    tenant.lifecycle = "closed"
    client_db.add(PlatformOwner(
        singleton=1,
        admin_user_id=admin.id,
        authorization_reference="synthetic-owner-proof",
    ))
    client_db.commit()

    password_login = enrollment.post("/api/auth/admin/password", json={
        "email": admin.email,
        "password": PASSWORD,
    })
    assert password_login.status_code == 202
    assert "challenge_id" in password_login.json()
    totp_code = pyotp.TOTP(secret).at(now().timestamp() + 30)
    completed = enrollment.post("/api/auth/admin/totp", json={
        "challenge_id": password_login.json()["challenge_id"],
        "code": totp_code,
    })
    assert completed.status_code == 200
    assert completed.json() == {"destination": "/admin/platform"}


def test_closed_photographer_cannot_start_admin_login(enrollment, client_db):
    admin = client_db.scalar(select(AdminUser))
    membership = client_db.scalar(select(TenantAdmin).where(TenantAdmin.admin_user_id == admin.id))
    tenant = client_db.get(Tenant, membership.tenant_id)
    tenant.lifecycle = "closed"
    sessions_before = len(list(client_db.scalars(select(AuthSession))))
    challenges_before = len(list(client_db.scalars(select(AuthChallenge))))
    client_db.commit()

    denied = enrollment.post("/api/auth/admin/password", json={
        "email": admin.email,
        "password": PASSWORD,
    })
    assert denied.status_code == 401
    assert len(list(client_db.scalars(select(AuthSession)))) == sessions_before
    assert len(list(client_db.scalars(select(AuthChallenge)))) == challenges_before
