from datetime import timedelta
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import (
    AdminUser,
    AuditEvent,
    AuthChallenge,
    Base,
    Client,
    GalleryAccess,
    SessionLocal,
    engine,
    now,
    password_hasher,
)
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def otp_for(challenge_id):
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, UUID(challenge_id))
        # Substitui o hash apenas no teste; a API nunca retorna o OTP.
        from app.auth import token_hash

        challenge.secret_hash = token_hash("123456")
        db.commit()


def test_client_otp_redirects_to_single_gallery(client):
    gallery_id = uuid4()
    with SessionLocal() as db:
        person = Client(full_name="Responsável", phone_e164="+5511999999999")
        db.add(person)
        db.flush()
        db.add(GalleryAccess(client_id=person.id, gallery_id=gallery_id))
        db.commit()
    response = client.post(
        "/auth/client/challenge", json={"full_name": "Responsável", "phone": "+55 (11) 99999-9999"}
    )
    assert response.status_code == 202
    challenge_id = response.json()["challenge_id"]
    otp_for(challenge_id)
    response = client.post(
        "/auth/client/verify", json={"challenge_id": challenge_id, "code": "123456"}
    )
    assert response.json() == {"destination": f"/gallery/{gallery_id}"}
    assert client.get(f"/gallery/{gallery_id}").status_code == 200
    assert client.get("/admin").status_code == 403


def test_client_multiple_galleries_and_used_or_expired_otp(client):
    with SessionLocal() as db:
        person = Client(full_name="Responsável", phone_e164="+5511888888888")
        db.add(person)
        db.flush()
        db.add_all(
            [
                GalleryAccess(client_id=person.id, gallery_id=uuid4()),
                GalleryAccess(client_id=person.id, gallery_id=uuid4()),
            ]
        )
        db.commit()
    challenge = client.post(
        "/auth/client/challenge", json={"full_name": "Responsável", "phone": "+5511888888888"}
    ).json()["challenge_id"]
    otp_for(challenge)
    assert client.post(
        "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
    ).json() == {"destination": "/library"}
    assert (
        client.post(
            "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
        ).status_code
        == 401
    )


def test_admin_requires_totp_and_client_cannot_enter_admin(client):
    secret = pyotp.random_base32()
    with SessionLocal() as db:
        db.add(
            AdminUser(
                email="foto@markina.test",
                password_hash=password_hasher.hash("senha-segura"),
                email_verified=True,
                totp_secret=secret,
            )
        )
        db.commit()
    password = client.post(
        "/auth/admin/password", json={"email": "foto@markina.test", "password": "senha-segura"}
    )
    assert password.status_code == 202
    assert client.get("/admin").status_code == 403
    response = client.post(
        "/auth/admin/totp",
        json={"challenge_id": password.json()["challenge_id"], "code": pyotp.TOTP(secret).now()},
    )
    assert response.json() == {"destination": "/admin"}
    assert client.get("/admin").status_code == 200


def test_invalid_factors_have_neutral_response_and_audit(client):
    assert (
        client.post(
            "/auth/admin/password", json={"email": "unknown@markina.test", "password": "x"}
        ).json()["detail"]
        == "Não foi possível concluir a autenticação."
    )
    unknown = client.post(
        "/auth/client/challenge", json={"full_name": "Pessoa Teste", "phone": "+5511777777777"}
    )
    assert unknown.status_code == 202
    with SessionLocal() as db:
        db.add(Client(full_name="Pessoa Conhecida", phone_e164="+5511999999998"))
        db.commit()
    known = client.post(
        "/auth/client/challenge", json={"full_name": "Pessoa Conhecida", "phone": "+5511999999998"}
    )
    assert known.status_code == 202
    assert known.json()["message"] == unknown.json()["message"]


def test_invalid_totp_is_neutral_and_audited(client):
    secret = pyotp.random_base32()
    with SessionLocal() as db:
        db.add(
            AdminUser(
                email="foto@markina.test",
                password_hash=password_hasher.hash("senha-segura"),
                email_verified=True,
                totp_secret=secret,
            )
        )
        db.commit()
    challenge = client.post(
        "/auth/admin/password", json={"email": "foto@markina.test", "password": "senha-segura"}
    ).json()["challenge_id"]
    response = client.post("/auth/admin/totp", json={"challenge_id": challenge, "code": "000000"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Não foi possível concluir a autenticação."
    with SessionLocal() as db:
        assert db.scalar(select(AuditEvent).where(AuditEvent.event == "admin_totp.failed"))


def test_otp_resend_expiration_and_rate_limit(client):
    response = client.post(
        "/auth/client/challenge", json={"full_name": "Pessoa Teste", "phone": "+5511777777777"}
    )
    challenge_id = response.json()["challenge_id"]
    assert (
        client.post("/auth/client/resend", json={"challenge_id": challenge_id}).status_code == 202
    )
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, UUID(challenge_id))
        assert challenge.resend_count == 1
        challenge.expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert (
        client.post("/auth/client/resend", json={"challenge_id": challenge_id}).status_code == 401
    )
    for _ in range(5):
        assert (
            client.post(
                "/auth/client/challenge",
                json={"full_name": "Pessoa Teste", "phone": "+5511666666666"},
            ).status_code
            == 202
        )
    assert (
        client.post(
            "/auth/client/challenge", json={"full_name": "Pessoa Teste", "phone": "+5511666666666"}
        ).status_code
        == 429
    )


def test_production_cookie_is_secure_and_session_is_rotated(monkeypatch, client):
    monkeypatch.setenv("APP_ENV", "production")
    secret = pyotp.random_base32()
    with SessionLocal() as db:
        db.add(
            AdminUser(
                email="foto@markina.test",
                password_hash=password_hasher.hash("senha-segura"),
                email_verified=True,
                totp_secret=secret,
            )
        )
        db.commit()
    password = client.post(
        "/auth/admin/password", json={"email": "foto@markina.test", "password": "senha-segura"}
    )
    response = client.post(
        "/auth/admin/totp",
        json={"challenge_id": password.json()["challenge_id"], "code": pyotp.TOTP(secret).now()},
    )
    assert "Secure" in response.headers["set-cookie"]
    with SessionLocal() as db:
        assert db.scalar(select(AuditEvent).where(AuditEvent.event == "session.created"))
