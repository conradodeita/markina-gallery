import base64
from datetime import timedelta
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import select

from app.auth import (
    AuthSession,
    Client,
    PushSubscription,
    SessionLocal,
    now,
    revoke_subject_sessions,
    token_hash,
)
from app.push_subscriptions import (
    decrypt_subscription,
    detach_previous_identity,
    fingerprint,
    subscribe,
)
from tests.test_notification_settings import isolated_schema  # noqa: F401
from tests.test_private_upload_batches import setup_private


@pytest.fixture(autouse=True)
def push_configuration(monkeypatch):
    from py_vapid import Vapid
    monkeypatch.setenv("WEB_PUSH_ENABLED", "true")
    private = base64.urlsafe_b64encode(b"a" * 32).decode()
    public = Vapid.from_string(private).public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    monkeypatch.setenv("WEB_PUSH_VAPID_PRIVATE_KEY", private)
    monkeypatch.setenv("WEB_PUSH_VAPID_PUBLIC_KEY", base64.urlsafe_b64encode(public).decode().rstrip("="))
    monkeypatch.setenv("WEB_PUSH_VAPID_SUBJECT", "mailto:synthetic@example.invalid")
    monkeypatch.setenv("PUSH_SUBSCRIPTION_ENCRYPTION_KEY", Fernet.generate_key().decode())


def subscription(endpoint="https://fcm.googleapis.com/fcm/send/synthetic"):
    key = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    encode = lambda raw: base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return {"endpoint": endpoint, "keys": {"p256dh": encode(key), "auth": encode(b"a" * 16)}}


def test_auth_origin_encryption_state_and_logout():
    browser, _, _ = setup_private()
    path = "/push/subscription"
    payload = {"subscription": subscription()}
    assert browser.get(path).json()["active"] is False
    assert browser.post(path, json=payload).status_code == 403
    assert browser.post(path, json=payload, headers={"origin": "https://evil.invalid"}).status_code == 403
    assert browser.post(path, json={**payload, "subject_id": str(uuid4())}, headers={"origin": "http://testserver"}).status_code == 422
    result = browser.post(path, json=payload, headers={"origin": "http://testserver"})
    assert result.status_code == 201
    state = browser.get(path)
    assert state.json()["active"] and "endpoint" not in state.text
    assert state.headers["cache-control"] == "no-store"
    with SessionLocal() as db:
        item = db.scalar(select(PushSubscription))
        assert payload["subscription"]["endpoint"] not in item.encrypted_subscription
        assert decrypt_subscription(item) == payload["subscription"]
    assert browser.post("/auth/logout").status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(PushSubscription)).active is False


def test_invalid_vapid_pair_does_not_offer_activation(monkeypatch):
    browser, _, _ = setup_private()
    assert browser.get("/push/subscription").json()["available"] is True
    monkeypatch.setenv("WEB_PUSH_VAPID_PUBLIC_KEY", "incorrect-pair")
    state = browser.get("/push/subscription").json()
    assert state["available"] is False and state["public_key"] == ""
    assert browser.post("/push/subscription", json={"subscription": subscription()},
                        headers={"origin": "http://testserver"}).status_code == 409


def test_account_switch_revocation_global_and_cipher_binding():
    from starlette.requests import Request
    browser, _, _ = setup_private()
    browser.get("/push/subscription")
    payload = subscription()
    browser.post("/push/subscription", json={"subscription": payload}, headers={"origin": "http://testserver"})
    raw_cookie = browser.cookies.get("pick_push_installation")
    with SessionLocal() as db:
        owner = Client(full_name="Outra conta", phone_e164="+5511888888888")
        db.add(owner)
        db.flush()
        session = AuthSession(role="client", subject_id=owner.id, token_hash=token_hash("new-owner"),
                              expires_at=now() + timedelta(days=1))
        db.add(session)
        db.flush()
        request = Request({"type": "http", "headers": [(b"cookie", f"pick_push_installation={raw_cookie}".encode())]})
        detach_previous_identity(db, request, "client", owner.id)
        item = db.scalar(select(PushSubscription))
        assert not item.active
        previous_generation = item.generation
        item = subscribe(db, session, fingerprint(raw_cookie), payload)
        assert item.active and item.subject_id == owner.id and item.generation > previous_generation
        assert decrypt_subscription(item) == payload
        with pytest.raises(ValueError, match="outra instalação"):
            subscribe(db, session, "different-installation", payload)
        item.subject_id = uuid4()
        with pytest.raises(ValueError, match="indisponível"):
            decrypt_subscription(item)
        item.subject_id = owner.id
        revoke_subject_sessions(db, "client", owner.id)
        assert not item.active


def test_invalid_providers_and_rate_limit(monkeypatch):
    browser, _, _ = setup_private()
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "3")
    for endpoint in ("https://127.0.0.1/push", "https://fcm.googleapis.com.evil.invalid/push",
                     "https://user@fcm.googleapis.com/push"):
        response = browser.post("/push/subscription", json={"subscription": subscription(endpoint)},
                                 headers={"origin": "http://testserver"})
        assert response.status_code == 422
    assert browser.post("/push/subscription", json={"subscription": subscription()},
                         headers={"origin": "http://testserver"}).status_code == 429


def test_device_limit_and_natural_session_expiry(monkeypatch):
    import app.push_subscriptions as service
    monkeypatch.setattr(service, "MAX_DEVICES", 2)
    _, _, _ = setup_private()
    with SessionLocal() as db:
        session = db.scalar(select(AuthSession))
        first = subscribe(db, session, "one", subscription("https://fcm.googleapis.com/fcm/send/one"))
        subscribe(db, session, "two", subscription("https://fcm.googleapis.com/fcm/send/two"))
        with pytest.raises(ValueError, match="Limite"):
            subscribe(db, session, "three", subscription("https://fcm.googleapis.com/fcm/send/three"))
        session.expires_at = now() - timedelta(minutes=1)
        assert first.active  # fechar a página ou expirar cookie não cancela adesão
