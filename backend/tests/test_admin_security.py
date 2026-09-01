"""Testes focados nas primitivas e fluxos de segurança administrativa."""

import re
from datetime import timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.admin_security import (
    AdminSecurityConfigurationError,
    cleanup_admin_security_material,
    consume_admin_action_token,
    decrypt_sensitive_payload,
    encrypt_sensitive_payload,
    issue_admin_action_token,
)
from app.auth import (
    AdminActionToken,
    AdminSecurityChallenge,
    AdminUser,
    AuditEvent,
    Base,
    EmailDelivery,
    EmailDeliveryAttempt,
    SessionLocal,
    WhatsAppChannelSettings,
    engine,
    now,
    password_hasher,
    validate_admin_password,
)
from app.email_delivery import (
    EmailConfigurationError,
    EmailDeliveryError,
    SandboxEmailProvider,
    email_channel_payload,
    email_provider_from_environment,
    enqueue_email,
    sensitive_link,
)
from app.main import app
from app.worker import process_next_email_delivery


@pytest.fixture(autouse=True)
def clean_database():
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(connection)
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app, base_url="http://testserver") as test_client:
        yield test_client


def create_admin(*, email: str = "admin@markina.test", password: str = "Atual-forte-2026"):
    secret = pyotp.random_base32()
    with SessionLocal() as db:
        admin = AdminUser(
            email=email,
            password_hash=password_hasher.hash(password),
            email_verified=True,
            totp_secret=secret,
        )
        db.add(admin)
        db.add(
            WhatsAppChannelSettings(
                environment="development",
                expected_phone_e164="+5511999999999",
                status="sandbox",
            )
        )
        db.commit()
        return admin.id, secret


def login_admin(client: TestClient, *, email="admin@markina.test", password="Atual-forte-2026"):
    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == email))
        secret = admin.totp_secret
    password_response = client.post(
        "/auth/admin/password", json={"email": email, "password": password}
    )
    assert password_response.status_code == 202
    response = client.post(
        "/auth/admin/totp",
        json={
            "challenge_id": password_response.json()["challenge_id"],
            "code": pyotp.TOTP(secret).now(),
        },
    )
    assert response.status_code == 200


def force_admin_otp(challenge_id: str, code: str = "123456") -> None:
    with SessionLocal() as db:
        challenge = db.get(AdminSecurityChallenge, UUID(challenge_id))
        challenge.secret_hash = sha256(code.encode()).hexdigest()
        db.commit()


def raw_token_from_delivery(delivery: EmailDelivery) -> str:
    payload = decrypt_sensitive_payload(
        delivery.encrypted_payload,
        context=f"email-delivery:{delivery.id}:{delivery.idempotency_key}",
    )
    match = re.search(r"#token=([^\s]+)", payload["text_body"])
    assert match
    return match.group(1)


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("curta", "entre 12 e 128"),
        ("x" * 129, "entre 12 e 128"),
        ("senha12345678", "menos comum"),
        ("fotografo-2026-segura", "e-mail"),
    ],
)
def test_admin_password_policy_rejects_weak_values(password: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_admin_password(password, email="fotografo@markina.test")


def test_admin_password_policy_rejects_current_and_accepts_strong_value() -> None:
    current_hash = password_hasher.hash("Atual-forte-2026")
    with pytest.raises(ValueError, match="diferente"):
        validate_admin_password(
            "Atual-forte-2026",
            email="foto@markina.test",
            current_password_hash=current_hash,
        )

    validate_admin_password(
        "Nova-frase-forte-2027",
        email="foto@markina.test",
        current_password_hash=current_hash,
    )
    generated_hash = password_hasher.hash("Nova-frase-forte-2027")
    assert generated_hash.startswith("$argon2id$")
    assert password_hasher.verify(generated_hash, "Nova-frase-forte-2027")


def test_sensitive_payload_is_authenticated_and_requires_key_outside_dev(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("EMAIL_PAYLOAD_ENCRYPTION_KEY", raising=False)
    encrypted = encrypt_sensitive_payload({"email": "admin@markina.test"}, context="test")
    assert "admin@markina.test" not in encrypted
    assert decrypt_sensitive_payload(encrypted, context="test") == {
        "email": "admin@markina.test"
    }
    with pytest.raises(AdminSecurityConfigurationError, match="adulterado"):
        decrypt_sensitive_payload(encrypted[:-2] + "xx", context="test")

    monkeypatch.setenv("APP_ENV", "homolog")
    with pytest.raises(AdminSecurityConfigurationError, match="obrigatória"):
        encrypt_sensitive_payload({"value": "x"}, context="test")


def test_action_token_is_hash_only_single_use_and_new_issue_invalidates_previous() -> None:
    with SessionLocal() as db:
        admin = AdminUser(
            email="admin@markina.test",
            password_hash=password_hasher.hash("Atual-forte-2026"),
            email_verified=True,
            totp_secret="TESTSECRET",
        )
        db.add(admin)
        db.flush()
        first, first_raw = issue_admin_action_token(
            db, admin_id=admin.id, purpose="password_reset"
        )
        second, second_raw = issue_admin_action_token(
            db, admin_id=admin.id, purpose="password_reset"
        )
        email_token, _email_raw = issue_admin_action_token(
            db,
            admin_id=admin.id,
            purpose="verify_admin_email",
            target="novo@example.test",
        )
        db.commit()
        assert first.token_hash != first_raw
        assert second.token_hash != second_raw
        assert first_raw not in str(first.__dict__)
        assert first.used_at is not None
        assert email_token.target_fingerprint != sha256(b"novo@example.test").hexdigest()
        assert "novo@example.test" not in str(email_token.__dict__)
        assert consume_admin_action_token(
            db, raw_token=first_raw, purpose="password_reset"
        ) is None
        assert consume_admin_action_token(
            db, raw_token=second_raw, purpose="password_reset"
        ) is not None
        db.commit()
        assert consume_admin_action_token(
            db, raw_token=second_raw, purpose="password_reset"
        ) is None


def test_cleanup_is_idempotent_and_removes_recoverable_terminal_payloads() -> None:
    with SessionLocal() as db:
        admin = AdminUser(
            email="admin@markina.test",
            password_hash=password_hasher.hash("Atual-forte-2026"),
            email_verified=True,
            totp_secret="TESTSECRET",
        )
        db.add(admin)
        db.flush()
        challenge = AdminSecurityChallenge(
            purpose="change_email_otp",
            admin_id=admin.id,
            session_id=uuid4(),
            subject_fingerprint="a" * 64,
            target_fingerprint="b" * 64,
            encrypted_target="ciphertext",
            secret_hash="c" * 64,
            expires_at=now() - timedelta(minutes=1),
        )
        token = AdminActionToken(
            admin_id=admin.id,
            purpose="verify_admin_email",
            token_hash="d" * 64,
            target_fingerprint="e" * 64,
            encrypted_target="ciphertext",
            expires_at=now() - timedelta(minutes=1),
        )
        delivery = EmailDelivery(
            kind="email_verification",
            source_type="admin_action_token",
            source_id=str(uuid4()),
            recipient_fingerprint="f" * 64,
            idempotency_key="email:test-cleanup",
            encrypted_payload="ciphertext",
            expires_at=now() - timedelta(minutes=1),
        )
        db.add_all([challenge, token, delivery])
        db.commit()
        assert cleanup_admin_security_material(db) == 3
        assert cleanup_admin_security_material(db) == 0
        assert db.scalar(select(AdminSecurityChallenge)).encrypted_target is None
        assert db.scalar(select(AdminActionToken)).encrypted_target is None
        cleaned_delivery = db.scalar(select(EmailDelivery))
        assert cleaned_delivery.encrypted_payload is None
        assert cleaned_delivery.status == "expired"


def test_email_sandbox_has_no_external_effect_and_smtp_is_fail_closed(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("EMAIL_PROVIDER", "sandbox")
    provider = email_provider_from_environment()
    assert isinstance(provider, SandboxEmailProvider)
    result = provider.send(
        recipient="admin@markina.test",
        subject="Segurança",
        text_body="conteúdo confidencial",
        idempotency_key="email:test-sandbox",
    )
    assert result.external_message_id.startswith("sandbox:")
    assert email_channel_payload()["status"] == "unavailable"

    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    with pytest.raises(EmailConfigurationError, match="credenciais|incompleta"):
        email_provider_from_environment()
    payload = email_channel_payload()
    assert payload == {
        "provider": "smtp",
        "status": "unavailable",
        "ready": False,
        "origin": None,
        "last_error": "Configuração transacional indisponível.",
    }


def test_sensitive_link_and_email_enqueue_are_safe_and_idempotent(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "test-only-fingerprint-salt")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://markina-homolog.example")
    monkeypatch.setenv(
        "EMAIL_PAYLOAD_ENCRYPTION_KEY",
        "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
    )
    raw_token = "token-muito-secreto"
    link = sensitive_link("/admin/reset-password", raw_token)
    assert link == f"https://markina-homolog.example/admin/reset-password#token={raw_token}"
    with SessionLocal() as db:
        first = enqueue_email(
            db,
            kind="password_recovery",
            source_type="admin_action_token",
            source_id=str(uuid4()),
            recipient="admin@markina.test",
            subject="Redefina sua senha",
            text_body=f"Abra {link}",
            idempotency_key="email:test-idempotent",
            expires_at=now() + timedelta(minutes=15),
        )
        second = enqueue_email(
            db,
            kind="password_recovery",
            source_type="admin_action_token",
            source_id=str(uuid4()),
            recipient="outro@markina.test",
            subject="Ignorado",
            text_body="Ignorado",
            idempotency_key="email:test-idempotent",
            expires_at=now() + timedelta(minutes=15),
        )
        db.commit()
        assert first.id == second.id
        assert raw_token not in str(first.__dict__)
        assert "admin@markina.test" not in str(first.__dict__)

    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "http://inseguro.example")
    with pytest.raises(EmailConfigurationError, match="HTTPS"):
        sensitive_link("/admin/reset-password", raw_token)


class RecordingEmailProvider(SandboxEmailProvider):
    def __init__(self) -> None:
        self.recipients: list[str] = []

    def send(self, *, recipient, subject, text_body, idempotency_key):
        self.recipients.append(recipient)
        return super().send(
            recipient=recipient,
            subject=subject,
            text_body=text_body,
            idempotency_key=idempotency_key,
        )


class FailingEmailProvider(SandboxEmailProvider):
    def __init__(self, *, transient: bool, ambiguous: bool = False) -> None:
        self.transient = transient
        self.ambiguous = ambiguous

    def send(self, *, recipient, subject, text_body, idempotency_key):
        del recipient, subject, text_body, idempotency_key
        raise EmailDeliveryError(
            "falha sintética", transient=self.transient, ambiguous=self.ambiguous
        )


def test_email_worker_accepts_once_and_minimizes_payload(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "http://localhost:3000")
    with SessionLocal() as db:
        delivery = enqueue_email(
            db,
            kind="security_notice",
            source_type="admin_user",
            source_id=str(uuid4()),
            recipient="admin@markina.test",
            subject="Aviso de segurança",
            text_body="Sua credencial foi alterada.",
            idempotency_key="email:test-worker",
            expires_at=now() + timedelta(minutes=15),
        )
        delivery_id = delivery.id
        db.commit()
    provider = RecordingEmailProvider()
    assert process_next_email_delivery(provider=provider) is True
    assert process_next_email_delivery(provider=provider) is False
    assert provider.recipients == ["admin@markina.test"]
    with SessionLocal() as db:
        processed = db.get(EmailDelivery, delivery_id)
        assert processed.status == "accepted"
        assert processed.attempts == 1
        assert processed.encrypted_payload is None
        assert processed.external_message_id.startswith("sandbox:")


def test_email_worker_expires_without_calling_provider(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    with SessionLocal() as db:
        delivery = enqueue_email(
            db,
            kind="password_recovery",
            source_type="admin_action_token",
            source_id=str(uuid4()),
            recipient="admin@markina.test",
            subject="Expirado",
            text_body="Não deve ser enviado.",
            idempotency_key="email:test-expired",
            expires_at=now() - timedelta(seconds=1),
        )
        delivery_id = delivery.id
        db.commit()
    provider = RecordingEmailProvider()
    assert process_next_email_delivery(provider=provider) is True
    assert provider.recipients == []
    with SessionLocal() as db:
        processed = db.get(EmailDelivery, delivery_id)
        assert processed.status == "expired"
        assert processed.encrypted_payload is None


@pytest.mark.parametrize(
    ("provider", "expected_status", "expected_result", "keeps_payload"),
    [
        (FailingEmailProvider(transient=True), "queued", "transient_failure", True),
        (FailingEmailProvider(transient=False), "failed", "permanent_failure", False),
        (FailingEmailProvider(transient=False, ambiguous=True), "unknown", "unknown", False),
    ],
)
def test_email_worker_handles_failures_without_blind_retry(
    monkeypatch, provider, expected_status, expected_result, keeps_payload
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("EMAIL_RETRY_BASE_SECONDS", "30")
    with SessionLocal() as db:
        delivery = enqueue_email(
            db,
            kind="security_notice",
            source_type="admin_user",
            source_id=str(uuid4()),
            recipient="admin@markina.test",
            subject="Teste",
            text_body="Teste sintético.",
            idempotency_key=f"email:test-failure:{expected_status}",
            expires_at=now() + timedelta(minutes=15),
        )
        delivery_id = delivery.id
        db.commit()
    assert process_next_email_delivery(provider=provider) is True
    with SessionLocal() as db:
        processed = db.get(EmailDelivery, delivery_id)
        attempt = db.scalar(
            select(EmailDeliveryAttempt).where(
                EmailDeliveryAttempt.delivery_id == delivery_id
            )
        )
        assert processed.status == expected_status
        assert (processed.encrypted_payload is not None) is keeps_payload
        assert attempt.result == expected_result
        if expected_status == "queued":
            assert processed.next_attempt_at is not None
        else:
            assert process_next_email_delivery(provider=provider) is False


def test_public_recovery_is_neutral_and_resets_without_creating_session(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://testserver")
    monkeypatch.setenv("EMAIL_PROVIDER", "sandbox")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    create_admin()

    known = client.post(
        "/auth/admin/recovery/challenge", json={"email": "admin@markina.test"}
    )
    unknown = client.post(
        "/auth/admin/recovery/challenge", json={"email": "unknown@markina.test"}
    )
    assert known.status_code == unknown.status_code == 202
    assert known.json()["message"] == unknown.json()["message"]
    known_resend = client.post(
        "/auth/admin/recovery/resend",
        json={"challenge_id": known.json()["challenge_id"]},
    )
    unknown_resend = client.post(
        "/auth/admin/recovery/resend",
        json={"challenge_id": unknown.json()["challenge_id"]},
    )
    assert known_resend.status_code == unknown_resend.status_code == 202
    assert known_resend.json()["message"] == unknown_resend.json()["message"]
    assert "markina_session" not in client.cookies
    with SessionLocal() as db:
        known_challenge = db.get(
            AdminSecurityChallenge, UUID(known.json()["challenge_id"])
        )
        unknown_challenge = db.get(
            AdminSecurityChallenge, UUID(unknown.json()["challenge_id"])
        )
        assert known_challenge.admin_id is not None
        assert unknown_challenge.admin_id is None
        assert all(
            "admin@markina.test" not in event.subject
            and "unknown@markina.test" not in event.subject
            for event in db.scalars(select(AuditEvent))
        )

    force_admin_otp(known.json()["challenge_id"])
    verified = client.post(
        "/auth/admin/recovery/verify",
        json={"challenge_id": known.json()["challenge_id"], "code": "123456"},
    )
    assert verified.status_code == 202
    with SessionLocal() as db:
        delivery = db.scalar(
            select(EmailDelivery).where(EmailDelivery.kind == "password_recovery")
        )
        raw_token = raw_token_from_delivery(delivery)
        item = db.scalar(
            select(AdminActionToken).where(AdminActionToken.purpose == "password_reset")
        )
        assert item.token_hash != raw_token
        assert raw_token not in str(item.__dict__)

    weak = client.post(
        "/auth/admin/recovery/reset",
        json={"token": raw_token, "new_password": "curta"},
    )
    assert weak.status_code == 422
    with SessionLocal() as db:
        assert db.scalar(select(AdminActionToken)).used_at is None

    reset = client.post(
        "/auth/admin/recovery/reset",
        json={"token": raw_token, "new_password": "Nova-frase-forte-2027"},
    )
    assert reset.status_code == 200
    assert "markina_session" not in client.cookies
    assert client.post(
        "/auth/admin/recovery/reset",
        json={"token": raw_token, "new_password": "Outra-frase-forte-2028"},
    ).status_code == 400
    login_admin(client, password="Nova-frase-forte-2027")


def test_public_recovery_resend_is_limited_and_invalid_codes_never_queue_email(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://testserver")
    monkeypatch.setenv("EMAIL_PROVIDER", "sandbox")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    create_admin()
    created = client.post(
        "/auth/admin/recovery/challenge", json={"email": "admin@markina.test"}
    )
    challenge_id = created.json()["challenge_id"]
    invalid = client.post(
        "/auth/admin/recovery/verify",
        json={"challenge_id": challenge_id, "code": "000000"},
    )
    assert invalid.status_code == 401
    with SessionLocal() as db:
        assert db.scalar(select(EmailDelivery)) is None
    for _ in range(3):
        assert client.post(
            "/auth/admin/recovery/resend", json={"challenge_id": challenge_id}
        ).status_code == 202
    assert client.post(
        "/auth/admin/recovery/resend", json={"challenge_id": challenge_id}
    ).status_code == 401
    with SessionLocal() as db:
        challenge = db.get(AdminSecurityChallenge, UUID(challenge_id))
        challenge.expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert client.post(
        "/auth/admin/recovery/verify",
        json={"challenge_id": challenge_id, "code": "123456"},
    ).status_code in {401, 429}


def test_public_recovery_stays_neutral_when_real_whatsapp_key_is_missing(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "synthetic-homolog-salt")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://homolog.example.test")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("EMAIL_CREDENTIAL_ENV", "homolog")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_USER", "synthetic-user")
    monkeypatch.setenv("SMTP_PASSWORD", "synthetic-password")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "sender@example.test")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "evolution")
    monkeypatch.delenv("WHATSAPP_OTP_ENCRYPTION_KEY", raising=False)
    create_admin()
    with SessionLocal() as db:
        db.add(
            WhatsAppChannelSettings(
                environment="homolog",
                status="ready",
                expected_phone_e164="+5511999999999",
            )
        )
        db.commit()

    known = client.post(
        "/auth/admin/recovery/challenge", json={"email": "admin@markina.test"}
    )
    unknown = client.post(
        "/auth/admin/recovery/challenge", json={"email": "unknown@markina.test"}
    )

    assert known.status_code == unknown.status_code == 202
    assert known.json()["message"] == unknown.json()["message"]
    with SessionLocal() as db:
        known_challenge = db.get(
            AdminSecurityChallenge, UUID(known.json()["challenge_id"])
        )
        assert known_challenge.admin_id is None


def test_settings_challenge_cannot_be_reused_by_rotated_session(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://testserver")
    monkeypatch.setenv("EMAIL_PROVIDER", "sandbox")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    create_admin()
    login_admin(client)
    headers = {"Origin": "https://testserver"}
    created = client.post(
        "/admin/security/password/challenge",
        json={"current_password": "Atual-forte-2026"},
        headers=headers,
    )
    assert created.status_code == 202
    force_admin_otp(created.json()["challenge_id"])
    login_admin(client)
    rejected = client.post(
        "/admin/security/password/confirm",
        json={
            "challenge_id": created.json()["challenge_id"],
            "code": "123456",
            "new_password": "Nova-frase-forte-2027",
        },
        headers=headers,
    )
    assert rejected.status_code == 401
    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser))
        assert password_hasher.verify(admin.password_hash, "Atual-forte-2026")


def test_account_settings_change_password_and_email_with_session_bound_otp(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://testserver")
    monkeypatch.setenv("EMAIL_PROVIDER", "sandbox")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    create_admin()
    assert client.get("/admin/email/channel").status_code == 403
    login_admin(client)
    headers = {"Origin": "https://testserver"}

    summary = client.get("/admin/security/summary")
    assert summary.status_code == 200
    assert summary.json()["email_masked"] != "admin@markina.test"
    assert "admin@markina.test" not in str(summary.json())
    diagnostic = client.get("/admin/email/channel")
    assert diagnostic.status_code == 200
    assert "password" not in str(diagnostic.json()).casefold()
    assert "smtp_host" not in str(diagnostic.json()).casefold()

    cross_site = client.post(
        "/admin/security/password/challenge",
        json={"current_password": "Atual-forte-2026"},
        headers={"Origin": "https://attacker.example"},
    )
    assert cross_site.status_code == 403
    challenge_response = client.post(
        "/admin/security/password/challenge",
        json={"current_password": "Atual-forte-2026"},
        headers=headers,
    )
    assert challenge_response.status_code == 202
    force_admin_otp(challenge_response.json()["challenge_id"])
    changed = client.post(
        "/admin/security/password/confirm",
        json={
            "challenge_id": challenge_response.json()["challenge_id"],
            "code": "123456",
            "new_password": "Nova-frase-forte-2027",
        },
        headers=headers,
    )
    assert changed.status_code == 200
    assert client.get("/admin/security/summary").status_code == 403

    login_admin(client, password="Nova-frase-forte-2027")
    email_challenge = client.post(
        "/admin/security/email/challenge",
        json={
            "current_password": "Nova-frase-forte-2027",
            "new_email": "novo@markina.test",
        },
        headers=headers,
    )
    assert email_challenge.status_code == 202
    with SessionLocal() as db:
        assert db.scalar(select(AdminUser)).email == "admin@markina.test"
    force_admin_otp(email_challenge.json()["challenge_id"])
    queued = client.post(
        "/admin/security/email/verify-otp",
        json={"challenge_id": email_challenge.json()["challenge_id"], "code": "123456"},
        headers=headers,
    )
    assert queued.status_code == 202
    with SessionLocal() as db:
        verification = db.scalar(
            select(EmailDelivery).where(EmailDelivery.kind == "email_verification")
        )
        raw_token = raw_token_from_delivery(verification)
        assert db.scalar(select(AdminUser)).email == "admin@markina.test"
    confirmed = client.post("/auth/admin/email/confirm", json={"token": raw_token})
    assert confirmed.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(AdminUser)).email == "novo@markina.test"
        assert db.scalar(
            select(EmailDelivery).where(EmailDelivery.kind == "security_notice")
        )
    assert client.get("/admin/security/summary").status_code == 403
    login_admin(
        client,
        email="novo@markina.test",
        password="Nova-frase-forte-2027",
    )
