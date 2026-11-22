"""Identidade tardia de conta encerrada em tenants e dados totalmente sintéticos."""

import base64
import importlib.util
import re
import secrets
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app import tenant_closure_identity as identity
from app.admin_security import decrypt_sensitive_payload
from app.auth import (
    AdminUser,
    AuthSession,
    EmailDelivery,
    PhotographerBusinessProfile,
    PhotographerSignup,
    Tenant,
    TenantClosureIdentityVerification,
    TenantClosureRequest,
    now,
)
from app.email_delivery import EmailConfigurationError
from app.main import app as main_app
from app.main import protect_credential_validation_input
from app.photographer_cpf import active_cpf_fingerprint
from app.private_fields import encrypt_private_field
from app.tenant_closure_identity import cleanup_expired_identity_challenges
from app.tenant_closure_recovery import reopen_account
from app.worker import validate_email_origin
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
ROOT = "/api/auth/photographer-closure-identity"
HOST = "recovery.pickyourpic.com.br"
CPF = "52998224725"


@pytest.fixture
def identity_flow(client_db, monkeypatch):
    monkeypatch.setenv("ADMIN_PRIVATE_FIELD_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    monkeypatch.setenv("EMAIL_PAYLOAD_ENCRYPTION_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "synthetic-only-closure-identity-fingerprint-key")
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "20")
    monkeypatch.delenv("PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON", raising=False)
    monkeypatch.delenv("PHOTOGRAPHER_CPF_FINGERPRINT_ACTIVE_KEY_VERSION", raising=False)
    monkeypatch.setattr(identity, "email_channel_payload", lambda: {"status": "ready"})
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    monkeypatch.setattr(identity, "SessionLocal", factory)

    _owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    tenant.lifecycle = "closed"
    tenant.canonical_host = HOST
    tenant.canonical_host_status = "ready"
    photographer.email_verified = False
    fingerprint_version, fingerprint, duplicate = active_cpf_fingerprint(client_db, CPF)
    assert not duplicate
    profile = PhotographerBusinessProfile(
        admin_user_id=photographer.id,
        tenant_id=tenant.id,
        full_name="Nome cadastral antigo",
        cpf_envelope=encrypt_private_field(CPF, tenant_id=tenant.id, field="photographer-cpf"),
        cpf_fingerprint=fingerprint,
        cpf_fingerprint_key_version=fingerprint_version,
    )
    signup = PhotographerSignup(
        id=uuid4(),
        photographer_name="Nome antigo",
        email=photographer.email,
        state="active",
        otp_expires_at=now() + timedelta(minutes=10),
        reserved_admin_id=photographer.id,
        reserved_tenant_id=tenant.id,
        activated_tenant_id=tenant.id,
        activated_at=now(),
    )
    closure = TenantClosureRequest(
        tenant_id=tenant.id,
        request_id=uuid4(),
        requested_by=photographer.id,
        state="closed",
        requested_at=now().replace(year=now().year - 10),
        closed_at=now().replace(year=now().year - 10),
        terms_version="synthetic-closure-v1",
        terms_sha256="a" * 64,
        balance_snapshot=4,
        balance_acknowledged=True,
    )
    client_db.add_all([profile, signup, closure])
    client_db.flush()
    client_db.commit()

    app = FastAPI()
    app.include_router(identity.router, prefix="/api")
    app.add_exception_handler(RequestValidationError, protect_credential_validation_input)
    client = TestClient(app)
    headers = {"Host": HOST, "Origin": f"https://{HOST}"}
    return client, headers, tenant, owner, photographer, profile, signup, closure


def request_data(request_id=None, *, cpf=CPF, email="current@example.test", name="Nome Atual"):
    return {
        "request_id": str(request_id or uuid4()),
        "full_name": name,
        "email": email,
        "cpf": cpf,
    }


def request_identity(client, headers, **kwargs):
    return client.post(f"{ROOT}/request", headers=headers, json=request_data(**kwargs))


def delivered_code(client_db, challenge_id):
    delivery = client_db.scalar(select(EmailDelivery).where(
        EmailDelivery.source_type == "tenant_closure_identity",
        EmailDelivery.source_id == str(challenge_id),
    ))
    assert delivery is not None
    payload = decrypt_sensitive_payload(
        delivery.encrypted_payload,
        context=f"email-delivery:{delivery.id}:{delivery.idempotency_key}",
    )
    match = re.search(r"é (\d{6})\.", payload["text_body"])
    assert match
    return delivery, match.group(1)


def confirm_identity(client, headers, challenge_id, code):
    return client.post(
        f"{ROOT}/confirm",
        headers=headers,
        json={"challenge_id": str(challenge_id), "code": code},
    )


def test_identity_request_is_neutral_across_wrong_cpf_and_host(identity_flow, client_db, monkeypatch):
    client, headers, tenant, *_ = identity_flow
    # Exercitar a rota instalada, sem depender da representação interna dos
    # routers (que pode ser lazy em versões recentes do FastAPI).
    registered = TestClient(main_app).post(
        "/auth/photographer-closure-identity/request", headers=headers,
        json=request_data(cpf="11144477735"),
    )
    assert registered.status_code == 202
    wrong_cpf = request_identity(client, headers, cpf="11144477735")
    wrong_host = request_identity(
        client,
        {"Host": "other.pickyourpic.com.br", "Origin": "https://other.pickyourpic.com.br"},
    )
    valid = request_identity(client, headers)

    assert wrong_cpf.status_code == wrong_host.status_code == valid.status_code == 202
    assert wrong_cpf.json()["message"] == wrong_host.json()["message"] == valid.json()["message"]
    assert set(wrong_cpf.json()) == set(wrong_host.json()) == set(valid.json())
    assert wrong_cpf.json()["challenge_id"] != valid.json()["challenge_id"]
    assert client_db.scalar(select(func.count()).select_from(EmailDelivery)) == 1
    assert "52998224725" not in wrong_cpf.text
    assert "current@example.test" not in valid.text
    assert tenant.lifecycle == "closed"
    client_db.add(AdminUser(
        email="taken@example.test",
        password_hash="synthetic-only",
        email_verified=True,
        totp_enabled=False,
    ))
    client_db.commit()
    email_collision = request_identity(client, headers, email="taken@example.test")
    assert email_collision.status_code == valid.status_code
    assert email_collision.json()["message"] == valid.json()["message"]
    assert client_db.scalar(select(func.count()).select_from(EmailDelivery)) == 1
    invalid_payload = client.post(
        f"{ROOT}/request",
        headers=headers,
        json={**request_data(), "tenant_id": str(tenant.id)},
    )
    assert invalid_payload.status_code == 422
    assert "52998224725" not in invalid_payload.text
    assert "private, no-store" in invalid_payload.headers["cache-control"]

    monkeypatch.setattr(identity, "email_channel_payload", lambda: {"status": "unavailable"})
    unavailable_known = request_identity(client, headers)
    unavailable_unknown = request_identity(
        client,
        {"Host": "other.pickyourpic.com.br", "Origin": "https://other.pickyourpic.com.br"},
    )
    assert unavailable_known.status_code == unavailable_unknown.status_code == 503
    assert unavailable_known.json() == unavailable_unknown.json()


def test_identity_request_is_idempotent_and_worker_checks_pending_origin(identity_flow, client_db):
    client, headers, tenant, _owner, _photographer, _profile, _signup, closure = identity_flow
    request_id = uuid4()
    first = request_identity(client, headers, request_id=request_id)
    replay = request_identity(client, headers, request_id=request_id)
    challenge_id = first.json()["challenge_id"]
    delivery, _code = delivered_code(client_db, challenge_id)

    assert first.status_code == replay.status_code == 202
    assert replay.json()["challenge_id"] == challenge_id
    assert client_db.scalar(select(func.count()).select_from(EmailDelivery)) == 1
    assert delivery.encrypted_payload and "current@example.test" not in delivery.encrypted_payload
    assert "current@example.test" not in delivery.encrypted_payload
    validate_email_origin(client_db, delivery)
    assert client_db.scalar(select(TenantClosureIdentityVerification).where(
        TenantClosureIdentityVerification.id == UUID(challenge_id),
    )).closure_request_id == closure.id
    assert tenant.lifecycle == "closed"


@pytest.mark.parametrize("other_host_has_closed_tenant", [False, True])
def test_wrong_host_cannot_cancel_code_and_verification_never_creates_session(identity_flow, client_db, other_host_has_closed_tenant):
    client, headers, tenant, _owner, photographer, profile, signup, _closure = identity_flow
    response = request_identity(client, headers)
    challenge_id = response.json()["challenge_id"]
    delivery, code = delivered_code(client_db, challenge_id)
    wrong_host = {"Host": "other.pickyourpic.com.br", "Origin": "https://other.pickyourpic.com.br"}
    if other_host_has_closed_tenant:
        client_db.add(Tenant(
            status="active", lifecycle="closed", canonical_host="other.pickyourpic.com.br",
            canonical_host_status="ready",
        ))
        client_db.commit()
    before = client_db.get(TenantClosureIdentityVerification, UUID(challenge_id))
    pending_material = (before.code_digest, before.current_name_envelope, before.current_email_envelope, before.attempts)
    wrong_host_result = confirm_identity(client, wrong_host, challenge_id, code)
    assert wrong_host_result.status_code == 202
    client_db.expire_all()
    challenge = client_db.get(TenantClosureIdentityVerification, UUID(challenge_id))
    assert challenge.state == "email_pending"
    assert (challenge.code_digest, challenge.current_name_envelope, challenge.current_email_envelope, challenge.attempts) == pending_material
    assert validate_email_origin(client_db, delivery) is None

    success = confirm_identity(client, headers, challenge_id, code)
    assert success.status_code == 202
    assert success.json()["message"] == wrong_host_result.json()["message"]
    client_db.expire_all()
    tenant = client_db.get(Tenant, tenant.id)
    photographer = client_db.get(AdminUser, photographer.id)
    profile = client_db.get(PhotographerBusinessProfile, profile.id)
    signup = client_db.get(PhotographerSignup, signup.id)
    challenge = client_db.get(TenantClosureIdentityVerification, UUID(challenge_id))
    assert tenant.lifecycle == "closed"
    assert photographer.email != "current@example.test" and not photographer.email_verified
    assert profile.full_name == "Nome cadastral antigo"
    assert signup.photographer_name == "Nome antigo" and signup.email != "current@example.test"
    assert challenge.state == "locked" and challenge.verified_at is None
    assert challenge.current_name_envelope is None
    assert challenge.current_email_envelope is None and challenge.code_digest is None
    assert client_db.scalar(select(func.count()).select_from(AuthSession)) == 0
    with pytest.raises(EmailConfigurationError):
        validate_email_origin(client_db, delivery)

    replay = confirm_identity(client, headers, challenge_id, code)
    assert replay.status_code == 202 and replay.json()["message"] == success.json()["message"]
    assert tenant.lifecycle == "closed"


def test_five_wrong_codes_lock_challenge_and_keep_profile_unchanged(identity_flow, client_db):
    client, headers, tenant, _owner, photographer, profile, _signup, _closure = identity_flow
    response = request_identity(client, headers)
    challenge_id = response.json()["challenge_id"]
    _delivery, correct_code = delivered_code(client_db, challenge_id)
    wrong_code = "000000" if correct_code != "000000" else "000001"

    responses = [confirm_identity(client, headers, challenge_id, wrong_code) for _ in range(5)]
    assert all(item.status_code == 202 for item in responses)
    assert len({item.json()["message"] for item in responses}) == 1
    client_db.expire_all()
    challenge = client_db.get(TenantClosureIdentityVerification, UUID(challenge_id))
    assert challenge.state == "locked" and challenge.attempts == 5
    assert challenge.current_email_envelope is None and challenge.code_digest is None
    assert client_db.get(Tenant, tenant.id).lifecycle == "closed"
    assert client_db.get(AdminUser, photographer.id).email != "current@example.test"
    assert client_db.get(PhotographerBusinessProfile, profile.id).full_name == "Nome cadastral antigo"


def test_expired_challenge_cleanup_and_owner_reopen_gate(identity_flow, client_db):
    client, headers, tenant, owner, _photographer, _profile, _signup, _closure = identity_flow
    response = request_identity(client, headers)
    challenge_id = response.json()["challenge_id"]
    _delivery, code = delivered_code(client_db, challenge_id)
    challenge = client_db.get(TenantClosureIdentityVerification, UUID(challenge_id))
    challenge.expires_at = now() - timedelta(seconds=1)
    client_db.commit()

    before_identity = confirm_identity(client, headers, challenge_id, code)
    assert before_identity.status_code == 202
    challenge = client_db.get(TenantClosureIdentityVerification, UUID(challenge_id))
    assert challenge.state == "expired" and challenge.current_email_envelope is None
    with pytest.raises(HTTPException, match="confirmação de identidade"):
        reopen_account(client_db, owner_id=owner.id, tenant_id=tenant.id, request_id=uuid4())
    assert tenant.lifecycle == "closed"
    # O caller HTTP faz rollback quando o serviço recusa a reabertura.
    # Liberar o lock desta chamada direta antes da próxima conexão HTTP.
    client_db.rollback()

    new_request = request_identity(client, headers)
    assert new_request.status_code == 202, new_request.text
    new_challenge_id = new_request.json()["challenge_id"]
    _delivery, new_code = delivered_code(client_db, new_challenge_id)
    assert confirm_identity(client, headers, new_challenge_id, new_code).status_code == 202
    assert tenant.lifecycle == "closed"
    # Mesmo CPF correto + novo contato confirmado não conferem autoridade.
    with pytest.raises(HTTPException, match="confirmação de identidade"):
        reopen_account(client_db, owner_id=owner.id, tenant_id=tenant.id, request_id=uuid4())
    assert client_db.get(Tenant, tenant.id).lifecycle == "closed"


def test_expiration_cleanup_erases_transient_name_email_and_code(identity_flow, client_db):
    client, headers, _tenant, _owner, _photographer, _profile, _signup, _closure = identity_flow
    response = request_identity(client, headers)
    challenge = client_db.get(TenantClosureIdentityVerification, UUID(response.json()["challenge_id"]))
    challenge.expires_at = now() - timedelta(seconds=1)
    client_db.commit()

    assert cleanup_expired_identity_challenges(client_db) == 1
    client_db.expire_all()
    challenge = client_db.get(TenantClosureIdentityVerification, challenge.id)
    assert challenge.state == "expired"
    assert challenge.current_name_envelope is None
    assert challenge.current_email_envelope is None
    assert challenge.email_fingerprint is None and challenge.code_digest is None


def test_identity_migration_adds_table_and_refuses_sqlite_downgrade(tmp_path):
    migration_path = Path(__file__).parents[1] / "migrations" / "versions" / (
        "20261110_0121_tenant_closure_identity_verification.py"
    )
    spec = importlib.util.spec_from_file_location("closure_identity_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine(f"sqlite:///{tmp_path / 'closure-identity-migration.sqlite'}")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE tenant (id CHAR(32) PRIMARY KEY)"))
            connection.execute(text(
                "CREATE TABLE tenant_closure_request (id CHAR(32) NOT NULL, tenant_id CHAR(32) NOT NULL, "
                "UNIQUE(id, tenant_id))"
            ))
            connection.execute(text(
                "CREATE TABLE admin_user (id CHAR(32) PRIMARY KEY)"
            ))
            connection.execute(text(
                "CREATE TABLE tenant_admin (tenant_id CHAR(32) NOT NULL, admin_user_id CHAR(32) NOT NULL, "
                "UNIQUE(tenant_id, admin_user_id))"
            ))
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
        with engine.begin() as connection:
            migration.op = Operations(MigrationContext.configure(connection))
            tenant_id, admin_id, closure_id = str(uuid4()), str(uuid4()), str(uuid4())
            connection.execute(text("INSERT INTO tenant (id) VALUES (:id)"), {"id": tenant_id})
            connection.execute(text(
                "INSERT INTO tenant_closure_request (id, tenant_id) VALUES (:id, :tenant)"
            ), {"id": closure_id, "tenant": tenant_id})
            connection.execute(text(
                "INSERT INTO admin_user (id) VALUES (:id)"
            ), {"id": admin_id})
            connection.execute(text(
                "INSERT INTO tenant_admin (tenant_id, admin_user_id) VALUES (:tenant, :admin)"
            ), {"tenant": tenant_id, "admin": admin_id})
            connection.execute(text(
                "INSERT INTO tenant_closure_identity_verification "
                "(id,tenant_id,closure_request_id,admin_user_id,request_id,state,"
                "current_name_envelope,current_email_envelope,email_fingerprint,code_digest,"
                "attempts,expires_at,verified_at,created_at) VALUES "
                "(:id,:tenant,:closure,:admin,:request,'email_pending','private-name','private-email',"
                ":email,:code,0,CURRENT_TIMESTAMP,NULL,CURRENT_TIMESTAMP)"
            ), {"id": str(uuid4()), "tenant": tenant_id, "closure": closure_id,
                "admin": admin_id, "request": str(uuid4()), "email": "a" * 64,
                "code": "b" * 64})
            with pytest.raises(RuntimeError, match="Verificação de identidade requer PostgreSQL"):
                migration.downgrade()
            assert connection.scalar(text(
                "SELECT count(*) FROM tenant_closure_identity_verification"
            )) == 1
    finally:
        engine.dispose()
