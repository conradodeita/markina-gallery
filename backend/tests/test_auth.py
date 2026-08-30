from datetime import timedelta
from uuid import UUID

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import (
    AdminUser,
    AuditEvent,
    AuthChallenge,
    AuthSession,
    Base,
    Client,
    DerivedGallery,
    ParentGallery,
    ParentGalleryRegistration,
    SessionLocal,
    engine,
    now,
    password_hasher,
)
from app.main import app
from app.seed_admin import seed_admin


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
    with SessionLocal() as db:
        person = Client(full_name="Responsável", phone_e164="+5511999999999")
        parent = ParentGallery(name="Evento")
        db.add(person)
        db.add(parent)
        db.flush()
        gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=person.id, name="Privada")
        db.add(gallery)
        db.commit()
        gallery_id = gallery.id
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
        first_parent = ParentGallery(name="Evento 1")
        second_parent = ParentGallery(name="Evento 2")
        db.add(person)
        db.add_all([first_parent, second_parent])
        db.flush()
        db.add_all(
            [
                DerivedGallery(parent_gallery_id=first_parent.id, client_id=person.id, name="Privada 1"),
                DerivedGallery(parent_gallery_id=second_parent.id, client_id=person.id, name="Privada 2"),
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


def test_existing_client_without_gallery_redirects_to_empty_library(client):
    with SessionLocal() as db:
        db.add(Client(full_name="Responsável sem galeria", phone_e164="+5511987654321"))
        db.commit()
    challenge = client.post(
        "/auth/client/challenge",
        json={"full_name": "Responsável sem galeria", "phone": "+5511987654321"},
    ).json()["challenge_id"]
    otp_for(challenge)

    response = client.post(
        "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
    )

    assert response.status_code == 200
    assert response.json() == {"destination": "/library"}


def test_unknown_phone_without_gallery_link_is_not_registered(client):
    challenge = client.post(
        "/auth/client/challenge",
        json={"full_name": "Pessoa sem convite", "phone": "+5511976543210"},
    ).json()["challenge_id"]
    otp_for(challenge)

    response = client.post(
        "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Este número ainda não possui acesso. "
        "Abra o link compartilhado de uma galeria para se cadastrar."
    )
    assert "markina_session" not in response.cookies
    with SessionLocal() as db:
        stored_challenge = db.get(AuthChallenge, UUID(challenge))
        assert stored_challenge.used_at is not None
        assert stored_challenge.client_name == "Pessoa sem convite"
        assert db.scalar(select(Client).where(Client.phone_e164 == "+5511976543210")) is None
        assert db.scalar(select(AuthSession).where(AuthSession.role == "client")) is None


def test_gallery_link_registers_unknown_phone_only_after_otp_and_reuses_relation(client):
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento protegido")
        db.add(parent)
        db.commit()
        parent_id = parent.id

    payload = {
        "full_name": "  Nova   Responsável  ",
        "phone": "+5511965432109",
        "parent_gallery_id": str(parent_id),
    }
    challenge = client.post("/auth/client/challenge", json=payload).json()["challenge_id"]
    with SessionLocal() as db:
        assert db.scalar(select(Client).where(Client.phone_e164 == payload["phone"])) is None
    otp_for(challenge)

    response = client.post(
        "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
    )

    assert response.status_code == 200
    assert response.json() == {"destination": "/library?registration=pending"}
    assert client.get(f"/gallery/{parent_id}").status_code == 403
    client.cookies.clear()

    second = client.post("/auth/client/challenge", json=payload).json()["challenge_id"]
    otp_for(second)
    assert client.post(
        "/auth/client/verify", json={"challenge_id": second, "code": "123456"}
    ).json() == {"destination": "/library?registration=pending"}

    with SessionLocal() as db:
        registered = db.scalar(select(Client).where(Client.phone_e164 == payload["phone"]))
        assert registered.full_name == "Nova Responsável"
        registrations = list(
            db.scalars(
                select(ParentGalleryRegistration).where(
                    ParentGalleryRegistration.parent_gallery_id == parent_id,
                    ParentGalleryRegistration.client_id == registered.id,
                )
            )
        )
        assert len(registrations) == 1
        assert registrations[0].status == "pending"


def test_disabled_gallery_link_cannot_create_client_after_otp(client):
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento temporário")
        db.add(parent)
        db.commit()
        parent_id = parent.id
    challenge = client.post(
        "/auth/client/challenge",
        json={
            "full_name": "Pessoa convidada",
            "phone": "+5511954321098",
            "parent_gallery_id": str(parent_id),
        },
    ).json()["challenge_id"]
    otp_for(challenge)
    with SessionLocal() as db:
        db.get(ParentGallery, parent_id).active = False
        db.commit()

    response = client.post(
        "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
    )

    assert response.status_code == 403
    with SessionLocal() as db:
        assert db.scalar(select(Client).where(Client.phone_e164 == "+5511954321098")) is None
        assert db.scalar(select(ParentGalleryRegistration)) is None


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


def test_seed_admin_is_idempotent_and_requires_external_values(monkeypatch):
    monkeypatch.setenv("ADMIN_SEED_EMAIL", "admin@markina.test")
    monkeypatch.setenv("ADMIN_SEED_PASSWORD", "senha-inicial-segura")
    monkeypatch.setenv("ADMIN_SEED_TOTP_SECRET", pyotp.random_base32())
    seed_admin()
    seed_admin()
    with SessionLocal() as db:
        assert len(list(db.scalars(select(AdminUser)))) == 1
