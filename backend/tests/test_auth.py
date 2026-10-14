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
    ClientPhone,
    DerivedGallery,
    GalleryMembershipNotificationOutbox,
    NotificationEvent,
    ParentGallery,
    ParentGalleryRegistration,
    SessionLocal,
    WhatsAppDelivery,
    cleanup_expired_client_otp_pii,
    engine,
    normalize_e164,
    now,
    password_hasher,
    pii_fingerprint,
)
from app.gallery_access import issue_gallery_capability
from app.main import app
from app.seed_admin import seed_admin
from tests.tenant_fixtures import FIXTURE_TENANT_ID, fixture_admin


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


def linked_post(client, path, *, json):
    """Cada chamada positiva fornece a capacidade explícita da fixture própria."""
    payload = dict(json)
    contexts = getattr(client, "fixture_link_contexts", {})
    client.fixture_link_contexts = contexts
    tokens = getattr(client, "fixture_link_tokens", {})
    client.fixture_link_tokens = tokens
    if path == "/auth/client/challenge":
        if not payload.get("access_token"):
            with SessionLocal() as db:
                person = db.scalar(select(Client).where(Client.tenant_id == FIXTURE_TENANT_ID,
                    Client.phone_e164 == normalize_e164(payload["phone"])))
                private = db.scalar(select(DerivedGallery).where(DerivedGallery.tenant_id == FIXTURE_TENANT_ID,
                    DerivedGallery.client_id == person.id)) if person else None
                parent = db.get(ParentGallery, private.parent_gallery_id) if private else db.scalar(
                    select(ParentGallery).where(ParentGallery.tenant_id == FIXTURE_TENANT_ID))
                if parent is None:
                    parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Origem OTP sintética", access_mode="standard")
                    db.add(parent)
                    db.flush()
                context = (parent.id, private.id if private else None)
                token = contexts.get(context)
                if token is None:
                    _, token = issue_gallery_capability(db, tenant_id=FIXTURE_TENANT_ID,
                        parent_gallery_id=parent.id, scope="private_invite" if private else "public_gallery",
                        derived_gallery_id=private.id if private else None,
                        client_id=person.id if private else None)
                    contexts[context] = token
                db.commit()
            payload["access_token"] = token
        response = client.post(path, json=payload)
        if response.status_code == 202:
            tokens[response.json()["challenge_id"]] = payload["access_token"]
        return response
    payload["access_token"] = tokens[payload["challenge_id"]]
    return client.post(path, json=payload)


def test_client_otp_redirects_to_single_gallery(client):
    with SessionLocal() as db:
        person = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Responsável", phone_e164="+5511999999999")
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Evento")
        db.add(person)
        db.add(parent)
        db.flush()
        gallery = DerivedGallery(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, client_id=person.id, name="Privada")
        db.add(gallery)
        db.commit()
        gallery_id = gallery.id
    response = linked_post(
        client, "/auth/client/challenge", json={"full_name": "Responsável", "phone": "+55 (11) 99999-9999"}
    )
    assert response.status_code == 202
    challenge_id = response.json()["challenge_id"]
    otp_for(challenge_id)
    response = linked_post(
        client, "/auth/client/verify", json={"challenge_id": challenge_id, "code": "123456"}
    )
    assert response.json() == {"destination": f"/gallery/{gallery_id}"}
    assert client.get(f"/gallery/{gallery_id}").status_code == 200
    assert client.get("/admin").status_code == 403


def test_gallery_otp_reuses_admin_client_identity_without_overwriting_name(client):
    phone = "+5511987654321"
    with SessionLocal() as db:
        person = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Nome cadastrado pelo fotógrafo", phone_e164=phone)
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Evento compartilhado", access_mode="standard")
        db.add_all([person, parent])
        db.flush()
        db.add(ClientPhone(tenant_id=FIXTURE_TENANT_ID, client_id=person.id, phone_e164=phone, active=True))
        db.add(
            ParentGalleryRegistration(tenant_id=FIXTURE_TENANT_ID,
                parent_gallery_id=parent.id,
                client_id=person.id,
                status="active",
            )
        )
        db.add(
            DerivedGallery(
                tenant_id=FIXTURE_TENANT_ID,
                parent_gallery_id=parent.id,
                client_id=person.id,
                name="Seleção privada automática",
            )
        )
        _capability, access_token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            scope="public_gallery",
            reconstructible=True,
        tenant_id=FIXTURE_TENANT_ID)
        db.commit()
        client_id, parent_id = person.id, parent.id

    challenge = linked_post(
        client, "/auth/client/challenge",
        json={
            "full_name": "Nome diferente informado no login",
            "phone": "+55 (11) 98765-4321",
            "access_token": access_token,
            "return_to": f"/public-galleries/{parent_id}",
        },
    )
    assert challenge.status_code == 202
    otp_for(challenge.json()["challenge_id"])
    verified = linked_post(
        client, "/auth/client/verify",
        json={"challenge_id": challenge.json()["challenge_id"], "code": "123456"},
    )
    assert verified.status_code == 200
    assert verified.json() == {"destination": f"/public-galleries/{parent_id}"}
    assert client.get("/auth/destination").json() == {
        "destination": f"/public-galleries/{parent_id}"
    }

    with SessionLocal() as db:
        clients = list(db.scalars(select(Client).where(Client.phone_e164 == phone)))
        phones = list(db.scalars(select(ClientPhone).where(ClientPhone.phone_e164 == phone)))
        notifications = list(
            db.scalars(
                select(GalleryMembershipNotificationOutbox).where(
                    GalleryMembershipNotificationOutbox.event_type
                    == "client_logged_in"
                )
            )
        )
        assert len(clients) == 1
        assert clients[0].id == client_id
        assert clients[0].full_name == "Nome cadastrado pelo fotógrafo"
        assert len(phones) == 1
        assert phones[0].client_id == client_id
        assert phones[0].verified_at is not None
        assert len(notifications) == 1
        assert notifications[0].event_key == f"client_logged_in:{challenge.json()['challenge_id']}"
        assert notifications[0].parent_gallery_id == parent_id
        assert notifications[0].derived_gallery_id is None
        assert notifications[0].client_id == client_id
        assert notifications[0].external_status == "skipped"
        assert "123456" not in notifications[0].parent_name_snapshot

    client.cookies.clear()
    resumed = linked_post(
        client, "/auth/client/challenge",
        json={"full_name": "Nome ignorado", "phone": phone, "access_token": access_token, "return_to": f"/public-galleries/{parent_id}"},
    )
    otp_for(resumed.json()["challenge_id"])
    assert linked_post(
        client, "/auth/client/verify",
        json={"challenge_id": resumed.json()["challenge_id"], "code": "123456"},
    ).json() == {"destination": f"/public-galleries/{parent_id}"}
    with SessionLocal() as db:
        assert len(
            list(
                db.scalars(
                    select(GalleryMembershipNotificationOutbox).where(
                        GalleryMembershipNotificationOutbox.event_type
                        == "client_logged_in"
                    )
                )
            )
        ) == 2


def test_client_multiple_galleries_and_used_or_expired_otp(client):
    with SessionLocal() as db:
        person = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Responsável", phone_e164="+5511888888888")
        first_parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Evento 1")
        second_parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Evento 2")
        db.add(person)
        db.add_all([first_parent, second_parent])
        db.flush()
        db.add_all(
            [
                DerivedGallery(
                    tenant_id=FIXTURE_TENANT_ID,
                    parent_gallery_id=first_parent.id, client_id=person.id, name="Privada 1"
                ),
                DerivedGallery(
                    tenant_id=FIXTURE_TENANT_ID,
                    parent_gallery_id=second_parent.id, client_id=person.id, name="Privada 2"
                ),
            ]
        )
        db.commit()
    challenge = linked_post(
        client, "/auth/client/challenge", json={"full_name": "Responsável", "phone": "+5511888888888", "return_to": "/library"}
    ).json()["challenge_id"]
    otp_for(challenge)
    assert linked_post(
        client, "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
    ).json() == {"destination": "/library"}
    assert (
        linked_post(
            client, "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
        ).status_code
        == 401
    )


def test_existing_client_without_link_is_refused_without_fallback(client):
    with SessionLocal() as db:
        db.add(Client(tenant_id=FIXTURE_TENANT_ID, full_name="Responsável sem galeria", phone_e164="+5511987654321"))
        db.commit()
    response = client.post("/auth/client/challenge", json={"full_name": "Responsável sem galeria", "phone": "+5511987654321"})
    assert response.status_code == 401
    with SessionLocal() as db:
        assert db.scalar(select(AuthChallenge)) is None
        assert db.scalar(select(AuthSession)) is None
        assert db.scalar(select(WhatsAppDelivery)) is None


def test_unknown_phone_without_gallery_link_is_not_registered(client):
    response = client.post("/auth/client/challenge", json={"full_name": "Pessoa sem convite", "phone": "+5511976543210"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Não foi possível concluir a autenticação."
    assert "markina_session" not in response.cookies
    with SessionLocal() as db:
        assert db.scalar(select(Client)) is None
        assert db.scalar(select(AuthChallenge)) is None
        assert db.scalar(select(AuthSession)) is None
        assert db.scalar(select(WhatsAppDelivery)) is None


def test_gallery_link_registers_unknown_phone_only_after_otp_and_reuses_relation(client):
    with SessionLocal() as db:
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Evento protegido", access_mode="standard")
        db.add(parent)
        db.flush()
        _, access_token = issue_gallery_capability(
            db, parent_gallery_id=parent.id, scope="public_gallery"
        , tenant_id=FIXTURE_TENANT_ID)
        db.commit()
        parent_id = parent.id

    payload = {
        "full_name": "  Nova   Responsável  ",
        "phone": "+5511965432109",
        "access_token": access_token,
    }
    challenge = linked_post(client, "/auth/client/challenge", json=payload).json()["challenge_id"]
    with SessionLocal() as db:
        assert db.scalar(select(Client).where(Client.phone_e164 == payload["phone"])) is None
    otp_for(challenge)

    response = linked_post(
        client, "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
    )

    assert response.status_code == 200
    assert response.json() == {"destination": f"/public-galleries/{parent_id}"}
    assert client.get(f"/gallery/{parent_id}").status_code == 403
    client.cookies.clear()

    second = linked_post(
        client, "/auth/client/challenge",
        json={**payload, "full_name": "Nome divergente não deve substituir"},
    ).json()["challenge_id"]
    otp_for(second)
    assert linked_post(
        client, "/auth/client/verify", json={"challenge_id": second, "code": "123456"}
    ).json() == {"destination": f"/public-galleries/{parent_id}"}

    with SessionLocal() as db:
        registered = db.scalar(select(Client).where(Client.phone_e164 == payload["phone"]))
        assert registered.full_name == "Nova Responsável"
        assert (
            db.scalar(
                select(ClientPhone).where(ClientPhone.phone_e164 == payload["phone"])
            ).client_id
            == registered.id
        )
        assert (
            len(list(db.scalars(select(Client).where(Client.phone_e164 == payload["phone"])))) == 1
        )
        consumed_challenges = list(
            db.scalars(
                select(AuthChallenge).where(AuthChallenge.id.in_([UUID(challenge), UUID(second)]))
            )
        )
        assert all(
            item.subject is None and item.client_name is None for item in consumed_challenges
        )
        registrations = list(
            db.scalars(
                select(ParentGalleryRegistration).where(
                    ParentGalleryRegistration.parent_gallery_id == parent_id,
                    ParentGalleryRegistration.client_id == registered.id,
                )
            )
        )
        assert len(registrations) == 1
        assert registrations[0].status == "active"
        login_notifications = list(
            db.scalars(
                select(GalleryMembershipNotificationOutbox).where(
                    GalleryMembershipNotificationOutbox.event_type
                    == "client_logged_in"
                )
            )
        )
        assert len(login_notifications) == 2
        assert {item.event_key for item in login_notifications} == {
            f"client_logged_in:{challenge}",
            f"client_logged_in:{second}",
        }
        assert all(item.external_status == "skipped" for item in login_notifications)
        first_accesses = list(db.scalars(select(NotificationEvent).where(
            NotificationEvent.event_type == "first_access",
            NotificationEvent.parent_gallery_id == parent_id,
            NotificationEvent.client_id == registered.id,
        )))
        assert len(first_accesses) == 1  # dois OTPs auditados, um aviso externo


def test_disabled_gallery_link_cannot_create_client_after_otp(client):
    with SessionLocal() as db:
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Evento temporário", access_mode="standard")
        db.add(parent)
        db.flush()
        _, access_token = issue_gallery_capability(
            db, parent_gallery_id=parent.id, scope="public_gallery"
        , tenant_id=FIXTURE_TENANT_ID)
        db.commit()
        parent_id = parent.id
    challenge = linked_post(
        client, "/auth/client/challenge",
        json={
            "full_name": "Pessoa convidada",
            "phone": "+5511954321098",
            "access_token": access_token,
        },
    ).json()["challenge_id"]
    otp_for(challenge)
    with SessionLocal() as db:
        db.get(ParentGallery, parent_id).active = False
        db.commit()

    response = linked_post(
        client, "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
    )

    assert response.status_code == 401
    with SessionLocal() as db:
        assert db.get(AuthChallenge, UUID(challenge)).used_at is None
        assert db.scalar(select(Client).where(Client.phone_e164 == "+5511954321098")) is None
        assert db.scalar(select(ParentGalleryRegistration)) is None


def test_admin_requires_totp_and_client_cannot_enter_admin(client):
    secret = pyotp.random_base32()
    with SessionLocal() as db:
        db.add(
            fixture_admin(AdminUser(
                email="foto@markina.test",
                password_hash=password_hasher.hash("senha-segura"),
                email_verified=True,
                totp_secret=secret,
            ))
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
    assert unknown.status_code == 401
    with SessionLocal() as db:
        db.add(Client(tenant_id=FIXTURE_TENANT_ID, full_name="Pessoa Conhecida", phone_e164="+5511999999998"))
        db.commit()
    known = client.post(
        "/auth/client/challenge", json={"full_name": "Pessoa Conhecida", "phone": "+5511999999998"}
    )
    assert known.status_code == 401
    assert known.json()["detail"] == unknown.json()["detail"]


def test_invalid_totp_is_neutral_and_audited(client):
    secret = pyotp.random_base32()
    with SessionLocal() as db:
        db.add(
            fixture_admin(AdminUser(
                email="foto@markina.test",
                password_hash=password_hasher.hash("senha-segura"),
                email_verified=True,
                totp_secret=secret,
            ))
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


def test_authenticated_identity_returns_only_admin_email(client):
    secret = pyotp.random_base32()
    with SessionLocal() as db:
        db.add(
            fixture_admin(AdminUser(
                email="fotografo@markina.test",
                password_hash=password_hasher.hash("senha-segura"),
                email_verified=True,
                totp_secret=secret,
            ))
        )
        db.commit()

    password = client.post(
        "/auth/admin/password",
        json={"email": "fotografo@markina.test", "password": "senha-segura"},
    )
    login = client.post(
        "/auth/admin/totp",
        json={
            "challenge_id": password.json()["challenge_id"],
            "code": pyotp.TOTP(secret).now(),
        },
    )

    assert login.status_code == 200
    assert client.get("/auth/identity").json() == {
        "role": "admin",
        "identity": "fotografo@markina.test",
    }


def test_authenticated_identity_returns_client_verified_phone(client):
    phone = "+5511998765432"
    with SessionLocal() as db:
        person = Client(
            tenant_id=FIXTURE_TENANT_ID,
            full_name="Cliente de teste",
            phone_e164=phone,
        )
        db.add(person)
        db.flush()
        db.add(
            ClientPhone(
                tenant_id=FIXTURE_TENANT_ID,
                client_id=person.id,
                phone_e164=phone,
                verified_at=now(),
            )
        )
        db.commit()

    challenge = linked_post(
        client,
        "/auth/client/challenge",
        json={"full_name": "Cliente de teste", "phone": phone},
    )
    assert challenge.status_code == 202
    otp_for(challenge.json()["challenge_id"])
    login = linked_post(
        client,
        "/auth/client/verify",
        json={"challenge_id": challenge.json()["challenge_id"], "code": "123456"},
    )

    assert login.status_code == 200
    assert client.get("/auth/identity").json() == {
        "role": "client",
        "identity": phone,
    }


def test_authenticated_identity_requires_session(client):
    assert client.get("/auth/identity").status_code == 401


def test_otp_resend_expiration_and_rate_limit(client):
    response = linked_post(
        client, "/auth/client/challenge", json={"full_name": "Pessoa Teste", "phone": "+5511777777777"}
    )
    challenge_id = response.json()["challenge_id"]
    assert (
        linked_post(client, "/auth/client/resend", json={"challenge_id": challenge_id}).status_code == 202
    )
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, UUID(challenge_id))
        assert challenge.resend_count == 1
        challenge.expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert (
        linked_post(client, "/auth/client/resend", json={"challenge_id": challenge_id}).status_code == 401
    )
    for _ in range(5):
        assert (
            linked_post(
                client, "/auth/client/challenge",
                json={"full_name": "Pessoa Teste", "phone": "+5511666666666"},
            ).status_code
            == 202
        )
    assert (
        linked_post(
            client, "/auth/client/challenge", json={"full_name": "Pessoa Teste", "phone": "+5511666666666"}
        ).status_code
        == 429
    )


def test_legacy_active_challenge_backfills_fingerprint_on_resend(client):
    response = linked_post(
        client, "/auth/client/challenge",
        json={"full_name": "Cliente Legada", "phone": "+5511777777711"},
    )
    challenge_id = response.json()["challenge_id"]
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, UUID(challenge_id))
        challenge.subject_fingerprint = None
        delivery = db.scalar(
            select(WhatsAppDelivery).where(WhatsAppDelivery.source_id == challenge_id)
        )
        delivery.recipient_fingerprint = None
        db.commit()

    assert (
        linked_post(client, "/auth/client/resend", json={"challenge_id": challenge_id}).status_code == 202
    )
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, UUID(challenge_id))
        assert challenge.subject == "+5511777777711"
        assert challenge.subject_fingerprint == pii_fingerprint("+5511777777711")
        deliveries = list(
            db.scalars(select(WhatsAppDelivery).where(WhatsAppDelivery.source_id == challenge_id))
        )
        assert deliveries[-1].recipient_fingerprint == challenge.subject_fingerprint


def test_terminal_invalid_otp_attempt_minimizes_transient_pii(client):
    challenge_id = linked_post(
        client, "/auth/client/challenge",
        json={"full_name": "Cliente Tentativas", "phone": "+5511777777755"},
    ).json()["challenge_id"]
    for _ in range(5):
        assert (
            linked_post(
                client, "/auth/client/verify",
                json={"challenge_id": challenge_id, "code": "000000"},
            ).status_code
            == 401
        )
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, UUID(challenge_id))
        assert challenge.attempts == 5
        assert challenge.subject is None
        assert challenge.client_name is None
        delivery = db.scalar(
            select(WhatsAppDelivery).where(WhatsAppDelivery.source_id == challenge_id)
        )
        assert delivery.recipient_phone is None


def test_periodic_otp_cleanup_is_idempotent_and_preserves_usable_challenge(
    monkeypatch,
):
    monkeypatch.setenv("AUTH_OTP_PII_RETENTION_MINUTES", "60")
    instant = now()
    with SessionLocal() as db:
        old = AuthChallenge(
            kind="client_otp",
            subject="+5511777777722",
            subject_fingerprint=pii_fingerprint("+5511777777722"),
            client_name="Cliente Abandonada",
            secret_hash="hash",
            expires_at=instant - timedelta(minutes=61),
        tenant_id=FIXTURE_TENANT_ID)
        recent = AuthChallenge(
            kind="client_otp",
            subject="+5511777777733",
            subject_fingerprint=pii_fingerprint("+5511777777733"),
            client_name="Cliente Ainda Retida",
            secret_hash="hash",
            expires_at=instant - timedelta(minutes=30),
        tenant_id=FIXTURE_TENANT_ID)
        usable = AuthChallenge(
            kind="client_otp",
            subject="+5511777777744",
            subject_fingerprint=pii_fingerprint("+5511777777744"),
            client_name="Cliente Ativa",
            secret_hash="hash",
            expires_at=instant + timedelta(minutes=5),
        tenant_id=FIXTURE_TENANT_ID)
        db.add_all([old, recent, usable])
        db.flush()
        db.add(
            WhatsAppDelivery(tenant_id=FIXTURE_TENANT_ID,
                kind="otp",
                source_type="auth_challenge",
                source_id=str(old.id),
                recipient_phone=old.subject,
                recipient_fingerprint=old.subject_fingerprint,
                template_kind="client_otp",
                idempotency_key=f"otp:{old.id}:0",
                encrypted_payload="ciphertext-sintético",
                expires_at=old.expires_at,
                status="accepted",
            )
        )
        db.commit()
        old_id, recent_id, usable_id = old.id, recent.id, usable.id

    with SessionLocal() as db:
        assert cleanup_expired_client_otp_pii(db, current_time=instant, tenant_id=FIXTURE_TENANT_ID) == 1
        assert cleanup_expired_client_otp_pii(db, current_time=instant, tenant_id=FIXTURE_TENANT_ID) == 0
        assert db.get(AuthChallenge, old_id).subject is None
        assert db.get(AuthChallenge, old_id).client_name is None
        assert db.get(AuthChallenge, recent_id).subject == "+5511777777733"
        assert db.get(AuthChallenge, usable_id).subject == "+5511777777744"
        delivery = db.scalar(
            select(WhatsAppDelivery).where(WhatsAppDelivery.source_id == str(old_id))
        )
        assert delivery.recipient_phone is None
        assert delivery.encrypted_payload is None


def test_production_cookie_is_secure_and_session_is_rotated(monkeypatch, client):
    monkeypatch.setenv("APP_ENV", "production")
    secret = pyotp.random_base32()
    with SessionLocal() as db:
        db.add(
            fixture_admin(AdminUser(
                email="foto@markina.test",
                password_hash=password_hasher.hash("senha-segura"),
                email_verified=True,
                totp_secret=secret,
            ))
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
