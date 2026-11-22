"""Atendimento sintético: nenhum e-mail é enviado e nenhuma senha é compartilhada."""

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app import photographer_access_recovery as recovery
from app.admin_security import decrypt_sensitive_payload
from app.auth import (
    AdminTotpRecoveryCode,
    AdminUser,
    AuthSession,
    EmailDelivery,
    PhotographerAccessRecovery,
    PhotographerSignup,
    Tenant,
    now,
    password_hasher,
)
from app.worker import validate_email_origin
from tests.tenant_fixtures import fresh_totp_code
from tests.test_photographer_totp_support import assistance as _assistance
from tests.test_platform_console_status import PASSWORD
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
assistance = _assistance
NEW_EMAIL = "recovered-photographer@example.test"
NEW_PASSWORD = "OnlySyntheticReplacement!20261110"


@pytest.fixture(autouse=True)
def synthetic_origin(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://recovery.example.test")


def intention(db, admin_id, **changes):
    values = {"request_id": uuid4(), "expected_version": recovery.version(db.get(AdminUser, admin_id)),
              "new_email": NEW_EMAIL, "identity_confirmed": True,
              "reason_code": "lost_email", "reset_totp": False}
    values.update(changes)
    return recovery.StartInput(**values)


def link_token(db, request_id):
    delivery = db.scalar(select(EmailDelivery).where(EmailDelivery.source_id == str(request_id)))
    payload = decrypt_sensitive_payload(delivery.encrypted_payload,
                                       context=f"email-delivery:{delivery.id}:{delivery.idempotency_key}")
    assert payload["recipient"] == NEW_EMAIL
    assert "#token=" in payload["text_body"]
    return payload["text_body"].split("#token=", 1)[1], delivery


def verify(db, request_id):
    raw, _delivery = link_token(db, request_id)
    return recovery.verify_recovery(db, recovery.VerifyInput(token=raw, new_password=NEW_PASSWORD))


@pytest.mark.parametrize("reset_totp", [False, True])
@pytest.mark.parametrize("lifecycle", ["open", "closed"])
def test_owner_finishes_only_after_mail_proof_and_keeps_lifecycle(
    assistance, client_db, reset_totp, lifecycle,
):
    session, tenant_id, admin_id = assistance
    tenant = client_db.get(Tenant, tenant_id)
    tenant.lifecycle = lifecycle
    tenant.status = "suspended"
    client_db.commit()
    admin = client_db.get(AdminUser, admin_id)
    old_email, old_password = admin.email, admin.password_hash
    target_envelope = admin._totp_secret_envelope
    payload = intention(client_db, admin_id, reset_totp=reset_totp)
    result = recovery.start_recovery(client_db, session, tenant_id, payload)
    client_db.commit()
    assert result["state"] == "email_pending"
    assert admin.email == old_email and admin.password_hash == old_password
    raw, delivery = link_token(client_db, payload.request_id)
    assert raw not in str(result) and NEW_EMAIL not in str(result)
    validate_email_origin(client_db, delivery)
    verify(client_db, payload.request_id)
    client_db.commit()
    assert admin.email == old_email and admin.password_hash == old_password
    owner = client_db.get(AdminUser, session.subject_id)
    result = recovery.commit_recovery(client_db, session, tenant_id, payload.request_id,
                                     recovery.CommitInput(current_password=PASSWORD, totp_code=fresh_totp_code(owner)))
    client_db.commit()
    assert result["state"] == "completed"
    assert admin.email == NEW_EMAIL and admin.email_verified
    assert password_hasher.verify(admin.password_hash, NEW_PASSWORD)
    assert tenant.lifecycle == lifecycle and tenant.status == "suspended"
    assert admin.totp_enabled is (not reset_totp)
    if not reset_totp:
        assert admin._totp_secret_envelope == target_envelope
    assert all(row.revoked_at for row in client_db.scalars(select(AuthSession)))
    assert all(row.revoked_at for row in client_db.scalars(select(AdminTotpRecoveryCode)))
    row = client_db.get(PhotographerAccessRecovery, payload.request_id)
    assert row.encrypted_payload is None and row.token_hash is None
    assert client_db.scalar(select(PhotographerSignup.email)) == NEW_EMAIL
    with pytest.raises(HTTPException):
        recovery.verify_recovery(client_db, recovery.VerifyInput(token=raw, new_password=NEW_PASSWORD))


def test_idempotent_request_and_changed_payload(assistance, client_db):
    session, tenant_id, admin_id = assistance
    payload = intention(client_db, admin_id)
    first = recovery.start_recovery(client_db, session, tenant_id, payload)
    client_db.commit()
    assert recovery.start_recovery(client_db, session, tenant_id, payload) == first
    assert client_db.scalar(select(func.count()).select_from(EmailDelivery)) == 1
    with pytest.raises(HTTPException) as refused:
        recovery.start_recovery(client_db, session, tenant_id, payload.model_copy(update={"reset_totp": True}))
    assert refused.value.status_code == 409


@pytest.mark.parametrize("change", ["declaration", "owner", "version", "target"])
def test_start_refuses_without_authority_or_current_target(assistance, client_db, change):
    session, tenant_id, admin_id = assistance
    payload = intention(client_db, admin_id)
    if change == "declaration":
        payload.identity_confirmed = False
    elif change == "owner":
        session.subject_id = admin_id
    elif change == "version":
        payload.expected_version = "f" * 64
    else:
        tenant_id = session.tenant_id
    with pytest.raises(HTTPException):
        recovery.start_recovery(client_db, session, tenant_id, payload)
    assert client_db.scalar(select(func.count()).select_from(PhotographerAccessRecovery)) == 0


def test_expiration_clears_transient_material(assistance, client_db):
    session, tenant_id, admin_id = assistance
    payload = intention(client_db, admin_id)
    recovery.start_recovery(client_db, session, tenant_id, payload)
    raw, _delivery = link_token(client_db, payload.request_id)
    row = client_db.get(PhotographerAccessRecovery, payload.request_id)
    row.expires_at = now() - timedelta(seconds=1)
    client_db.commit()
    with pytest.raises(HTTPException):
        verify(client_db, payload.request_id)
    assert recovery.cleanup_expired_recoveries(client_db) == 1
    client_db.commit()
    assert row.state == "expired" and row.encrypted_payload is None and row.token_hash is None
    assert raw not in str(recovery.summary(row))


def test_commit_rechecks_target_version_and_owner_factor(assistance, client_db):
    session, tenant_id, admin_id = assistance
    payload = intention(client_db, admin_id)
    recovery.start_recovery(client_db, session, tenant_id, payload)
    verify(client_db, payload.request_id)
    client_db.commit()
    owner = client_db.get(AdminUser, session.subject_id)
    with pytest.raises(HTTPException) as refused:
        recovery.commit_recovery(client_db, session, tenant_id, payload.request_id,
                                 recovery.CommitInput(current_password="wrong", totp_code="000000"))
    assert refused.value.status_code == 403
    client_db.get(AdminUser, admin_id).password_hash = password_hasher.hash("ChangedSynthetic!20261110")
    client_db.commit()
    with pytest.raises(HTTPException) as stale:
        recovery.commit_recovery(client_db, session, tenant_id, payload.request_id,
                                 recovery.CommitInput(current_password=PASSWORD, totp_code=fresh_totp_code(owner)))
    assert stale.value.status_code == 409
    assert client_db.get(AdminUser, admin_id).email != NEW_EMAIL


def test_new_request_supersedes_old_and_cannot_commit_without_email(assistance, client_db):
    session, tenant_id, admin_id = assistance
    old = intention(client_db, admin_id)
    recovery.start_recovery(client_db, session, tenant_id, old)
    raw, delivery = link_token(client_db, old.request_id)
    current = intention(client_db, admin_id)
    recovery.start_recovery(client_db, session, tenant_id, current)
    client_db.commit()
    assert client_db.get(PhotographerAccessRecovery, old.request_id).state == "expired"
    with pytest.raises(HTTPException):
        recovery.verify_recovery(client_db, recovery.VerifyInput(token=raw, new_password=NEW_PASSWORD))
    with pytest.raises(Exception, match="Atendimento indisponível"):
        validate_email_origin(client_db, delivery)
    owner = client_db.get(AdminUser, session.subject_id)
    with pytest.raises(HTTPException) as refused:
        recovery.commit_recovery(client_db, session, tenant_id, current.request_id,
                                 recovery.CommitInput(current_password=PASSWORD, totp_code=fresh_totp_code(owner)))
    assert refused.value.status_code == 409
    assert client_db.get(AdminUser, admin_id).email != NEW_EMAIL


def test_late_closed_identity_requires_completed_case_and_stays_suspended(assistance, client_db):
    from app.auth import TenantClosureRequest
    from app.tenant_closure_recovery import reopen_account
    session, tenant_id, admin_id = assistance
    tenant = client_db.get(Tenant, tenant_id)
    tenant.lifecycle, tenant.status = "closed", "suspended"
    instant = now().replace(year=now().year - 10)
    closure = TenantClosureRequest(tenant_id=tenant_id, request_id=uuid4(), requested_by=admin_id,
                                   state="closed", requested_at=instant, closed_at=instant,
                                   terms_version="synthetic", terms_sha256="a" * 64,
                                   balance_snapshot=0, balance_acknowledged=True)
    client_db.add(closure)
    client_db.commit()
    # A verificação antiga pode ter sido invalidada na revisão de retenção.
    client_db.get(AdminUser, admin_id).email_verified = False
    client_db.commit()
    payload = intention(client_db, admin_id)
    recovery.start_recovery(client_db, session, tenant_id, payload)
    verify(client_db, payload.request_id)
    client_db.commit()
    assert recovery.completed_closure_proof(client_db, tenant_id, closure.id) is None
    with pytest.raises(HTTPException, match="confirmação de identidade"):
        reopen_account(client_db, owner_id=session.subject_id, tenant_id=tenant_id, request_id=uuid4())
    client_db.rollback()
    owner = client_db.get(AdminUser, session.subject_id)
    recovery.commit_recovery(client_db, session, tenant_id, payload.request_id,
                             recovery.CommitInput(current_password=PASSWORD, totp_code=fresh_totp_code(owner)))
    client_db.commit()
    assert recovery.completed_closure_proof(client_db, tenant_id, closure.id)
    assert recovery.completed_closure_proof(client_db, tenant_id, uuid4()) is None
    assert recovery.completed_closure_proof(client_db, tenant_id, closure.id, session.subject_id) is None
    assert tenant.lifecycle == "closed" and tenant.status == "suspended"
    result = reopen_account(client_db, owner_id=session.subject_id, tenant_id=tenant_id, request_id=uuid4())
    client_db.commit()
    assert result["lifecycle"] == "open" and tenant.status == "suspended"


@pytest.fixture
def http_client(assistance, client_db, monkeypatch):
    from fastapi import FastAPI
    from fastapi.exceptions import RequestValidationError
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.main import protect_credential_validation_input
    session, _tenant_id, _admin_id = assistance
    monkeypatch.setattr(recovery.console, "SessionLocal", sessionmaker(bind=client_db.get_bind(), expire_on_commit=False))
    monkeypatch.setattr(recovery.console, "current_session", lambda *_args, **_kwargs: session)
    app = FastAPI()
    app.include_router(recovery.owner_router)
    app.include_router(recovery.public_router)
    app.add_exception_handler(RequestValidationError, protect_credential_validation_input)
    return TestClient(app)


def test_http_neutral_bad_tokens_rate_limit_and_secret_redaction(http_client, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "2")
    path = "/auth/photographer-access-recovery/confirm"
    secret = "synthetic-secret-not-for-errors-123456"
    for _ in range(2):
        response = http_client.post(path, json={"token": secret, "new_password": NEW_PASSWORD})
        assert response.status_code == 400
        assert secret not in response.text and NEW_PASSWORD not in response.text
        assert "no-store" in response.headers["cache-control"]
    assert http_client.post(path, json={"token": secret, "new_password": NEW_PASSWORD}).status_code == 429
    invalid = http_client.post(path, json={"token": secret, "new_password": {"secret": NEW_PASSWORD}})
    assert invalid.status_code == 422 and NEW_PASSWORD not in invalid.text


def test_http_session_changed_rolls_back_request(http_client, assistance, client_db, monkeypatch):
    _session, tenant_id, admin_id = assistance
    payload = intention(client_db, admin_id)
    calls = 0
    original = recovery.console.current_session
    def changed(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise HTTPException(401, "Sessão encerrada")
        return original(*args, **kwargs)
    monkeypatch.setattr(recovery.console, "current_session", changed)
    response = http_client.post(f"/admin/platform/console/tenants/{tenant_id}/access-recovery",
                                json=payload.model_dump(mode="json"))
    assert response.status_code == 401
    assert client_db.get(PhotographerAccessRecovery, payload.request_id) is None
    assert client_db.scalar(select(func.count()).select_from(EmailDelivery)) == 0


def test_postgres_migration_roundtrip_and_history_preservation(assistance, client_db, monkeypatch):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text

    if client_db.bind.dialect.name != "postgresql":
        pytest.skip("DDL PostgreSQL em schema descartável")
    schema = client_db.bind.get_execution_options()["schema_translate_map"][None]
    connection = client_db.connection()
    connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    path = Path(__file__).parents[1] / "migrations/versions/20261110_0124_photographer_access_recovery.py"
    spec = __import__("importlib.util").util.spec_from_file_location("access_recovery_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
    migration.downgrade()  # Somente a tabela vazia deste schema sintético.
    migration.upgrade()
    session, tenant_id, admin_id = assistance
    payload = intention(client_db, admin_id)
    recovery.start_recovery(client_db, session, tenant_id, payload)
    client_db.flush()
    with pytest.raises(RuntimeError, match="histórico"):
        migration.downgrade()
    assert client_db.get(PhotographerAccessRecovery, payload.request_id)
    client_db.commit()


@pytest.mark.parametrize("phase", ["start", "verify", "commit"])
def test_postgres_concurrent_single_use(assistance, client_db, phase):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy.orm import Session

    if client_db.bind.dialect.name != "postgresql":
        pytest.skip("Concorrência real requer PostgreSQL descartável")
    session, tenant_id, admin_id = assistance
    payload = intention(client_db, admin_id)
    raw = None
    if phase in {"verify", "commit"}:
        recovery.start_recovery(client_db, session, tenant_id, payload)
        raw, _delivery = link_token(client_db, payload.request_id)
    owner_payload = None
    if phase == "commit":
        verify(client_db, payload.request_id)
        owner_payload = recovery.CommitInput(current_password=PASSWORD,
            totp_code=fresh_totp_code(client_db.get(AdminUser, session.subject_id)))
    client_db.commit()
    barrier = Barrier(2)
    def execute():
        with Session(client_db.bind) as db:
            barrier.wait(timeout=10)
            try:
                if phase == "start":
                    recovery.start_recovery(db, session, tenant_id, payload)
                elif phase == "verify":
                    recovery.verify_recovery(db, recovery.VerifyInput(token=raw, new_password=NEW_PASSWORD))
                else:
                    recovery.commit_recovery(db, session, tenant_id, payload.request_id, owner_payload)
                db.commit()
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(execute) for _ in range(2)]
        results = sorted(future.result(timeout=45) for future in futures)
    assert results == {"start": [200, 200], "verify": [200, 400], "commit": [200, 403]}[phase]
    assert client_db.scalar(select(func.count()).select_from(EmailDelivery)) == (2 if phase == "commit" else 1)
    assert client_db.scalar(select(func.count()).select_from(PhotographerAccessRecovery)) == 1


def test_http_notice_failure_rolls_back_credentials_and_owner_step(http_client, assistance, client_db, monkeypatch):
    from app.email_delivery import EmailConfigurationError
    session, tenant_id, admin_id = assistance
    payload = intention(client_db, admin_id)
    recovery.start_recovery(client_db, session, tenant_id, payload)
    verify(client_db, payload.request_id)
    client_db.commit()
    admin = client_db.get(AdminUser, admin_id)
    previous = (admin.email, admin.password_hash)
    owner = client_db.get(AdminUser, session.subject_id)
    owner_step = owner.totp_last_used_step
    code = fresh_totp_code(owner)
    def fail(*_args, **_kwargs):
        raise EmailConfigurationError("synthetic configuration failure")
    monkeypatch.setattr(recovery, "queue_previous_email_notice", fail)
    response = http_client.post(f"/admin/platform/console/tenants/{tenant_id}/access-recovery/{payload.request_id}/commit",
                               json={"current_password": PASSWORD, "totp_code": code})
    assert response.status_code == 503 and "synthetic configuration" not in response.text
    client_db.expire_all()
    admin = client_db.get(AdminUser, admin_id)
    assert (admin.email, admin.password_hash) == previous
    assert client_db.get(AdminUser, session.subject_id).totp_last_used_step == owner_step
    assert client_db.get(PhotographerAccessRecovery, payload.request_id).state == "email_verified"


@pytest.mark.parametrize("relation", ["target", "closure"])
def test_database_rejects_cross_tenant_recovery_binding(assistance, client_db, relation):
    from sqlalchemy.exc import IntegrityError

    from app.auth import TenantClosureRequest

    session, tenant_id, admin_id = assistance
    payload = intention(client_db, admin_id)
    recovery.start_recovery(client_db, session, tenant_id, payload)
    client_db.commit()
    row = client_db.get(PhotographerAccessRecovery, payload.request_id)
    if relation == "target":
        row.admin_user_id = session.subject_id
    else:
        closure = TenantClosureRequest(tenant_id=session.tenant_id, requested_by=session.subject_id,
            request_id=uuid4(), terms_version="synthetic", terms_sha256="a" * 64, balance_snapshot=0)
        client_db.add(closure)
        client_db.flush()
        row.closure_request_id = closure.id
    with pytest.raises(IntegrityError):
        client_db.flush()
    client_db.rollback()
    assert client_db.get(PhotographerAccessRecovery, payload.request_id).admin_user_id == admin_id


def test_security_cleanup_preserves_history_and_is_idempotent(assistance, client_db):
    from app.admin_security import cleanup_admin_security_material

    session, tenant_id, admin_id = assistance
    payload = intention(client_db, admin_id)
    recovery.start_recovery(client_db, session, tenant_id, payload)
    row = client_db.get(PhotographerAccessRecovery, payload.request_id)
    row.expires_at = now() - timedelta(seconds=1)
    client_db.commit()
    cleanup_admin_security_material(client_db)
    client_db.commit()
    row = client_db.get(PhotographerAccessRecovery, payload.request_id)
    assert row.state == "expired" and row.encrypted_payload is None and row.token_hash is None
    assert row.actor_admin_id == session.subject_id and row.identity_confirmed
    assert row.reason_code == "lost_email" and row.admin_user_id == admin_id
    assert cleanup_admin_security_material(client_db) == 0
