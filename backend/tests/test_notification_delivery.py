from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.auth import (
    AuthSession,
    NotificationDelivery,
    NotificationEvent,
    PushSubscription,
    SessionLocal,
    now,
)
from app.messaging import SandboxWhatsAppProvider, WhatsAppDeliveryError
from app.notification_delivery import process_next_notification
from app.notification_settings import enqueue_event, save_setting
from app.push_subscriptions import subscribe
from app.web_push import PushFailure
from tests.test_notification_settings import isolated_schema  # noqa: F401
from tests.test_private_upload_batches import setup_private
from tests.test_push_subscriptions import subscription


def queued(monkeypatch):
    monkeypatch.setenv("PUSH_SUBSCRIPTION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv("WHATSAPP_PHOTOGRAPHER_PHONE_E164", "+5511888888888")
    setup_private()
    with SessionLocal() as db:
        owner = db.scalar(select(AuthSession))
        subscribe(db, owner, "synthetic-installation", subscription())
        event = enqueue_event(db, event_type="first_access", event_key="synthetic-event",
                              values={"cliente": "Teste", "galeria": "Teste"}, target_path="/admin",
                              recipients=[owner.subject_id])
        db.commit()
        return event.id


def status(channel):
    with SessionLocal() as db:
        return db.scalar(select(NotificationDelivery).where(NotificationDelivery.channel == channel))


def test_channels_independent_and_claim_concurrent(monkeypatch):
    queued(monkeypatch)
    def fail(*args, **kwargs): raise PushFailure("provider_rejected", status=503, transient=True)
    assert process_next_notification("push", push_sender=fail)
    assert status("push").status == "queued" and status("push").attempts == 1
    assert process_next_notification("whatsapp", whatsapp_provider=SandboxWhatsAppProvider())
    assert status("whatsapp").status == "accepted"
    with SessionLocal() as db:
        db.get(NotificationDelivery, status("push").id).next_attempt_at = now() - timedelta(seconds=1)
        db.commit()
    calls = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: process_next_notification("push", push_sender=lambda *_a, **_k: calls.append(1)), range(2)))
    assert len(calls) == 1 and status("push").status == "accepted"


@pytest.mark.parametrize("code", [404, 410, 429, 500])
def test_provider_error_policy(monkeypatch, code):
    queued(monkeypatch)
    def fail(*_args, **_kwargs): raise PushFailure("provider_rejected", status=code, transient=code == 429 or code >= 500)
    process_next_notification("push", push_sender=fail)
    item = status("push")
    assert item.status == ("failed" if code in {404, 410} else "queued")
    assert item.attempts == 1
    with SessionLocal() as db:
        assert db.scalar(select(PushSubscription)).active == (code not in {404, 410})


def test_disabled_channel_never_replays_and_expiration(monkeypatch):
    event_id = queued(monkeypatch)
    with SessionLocal() as db:
        item = db.scalar(select(NotificationDelivery).where(NotificationDelivery.channel == "push"))
        item.status = "processing"  # interruptor muda durante uma tentativa anterior
        item.lease_until = now() - timedelta(seconds=1)
        save_setting(db, "first_access", {"push_enabled": False})
        save_setting(db, "first_access", {"push_enabled": True})
        db.commit()
    process_next_notification("push", push_sender=lambda *_a, **_k: pytest.fail("Não repetir após desligamento"))
    assert status("push").status == "cancelled"
    with SessionLocal() as db:
        db.get(NotificationEvent, event_id).expires_at = now() - timedelta(seconds=1)
        db.commit()
    process_next_notification("whatsapp", whatsapp_provider=SandboxWhatsAppProvider())
    assert status("whatsapp").status == "expired"


def test_ambiguous_whatsapp_and_crashed_worker_are_not_retried(monkeypatch):
    queued(monkeypatch)
    class Ambiguous(SandboxWhatsAppProvider):
        def send_transactional(self, *_args, **_kwargs):
            raise WhatsAppDeliveryError("Ambíguo", transient=False, ambiguous=True)
    process_next_notification("whatsapp", whatsapp_provider=Ambiguous())
    assert status("whatsapp").status == "unknown"
    assert not process_next_notification("whatsapp", whatsapp_provider=Ambiguous())
    with SessionLocal() as db:
        item = db.get(NotificationDelivery, status("whatsapp").id)
        item.status, item.lease_until = "processing", now() - timedelta(seconds=1)
        db.commit()
    process_next_notification("whatsapp", whatsapp_provider=SandboxWhatsAppProvider())
    assert status("whatsapp").status == "unknown"


def test_switched_identity_prevents_queued_push(monkeypatch):
    queued(monkeypatch)
    with SessionLocal() as db:
        db.scalar(select(PushSubscription)).generation += 1
        db.commit()
    process_next_notification("push", push_sender=lambda *_a, **_k: pytest.fail("Inscrição revogada"))
    assert status("push").status == "cancelled"


def test_attempts_exhausted_and_operational_gate_has_no_replay(monkeypatch):
    queued(monkeypatch)
    def fail(*_a, **_k): raise PushFailure("unavailable", status=503, transient=True)
    for _ in range(3):
        process_next_notification("push", push_sender=fail)
        with SessionLocal() as db:
            db.get(NotificationDelivery, status("push").id).next_attempt_at = now() - timedelta(seconds=1)
            db.commit()
    assert status("push").status == "failed" and status("push").attempts == 3
    assert not process_next_notification("push", push_sender=fail)
    monkeypatch.setenv("WEB_PUSH_ENABLED", "false")
    with SessionLocal() as db:
        owner = db.scalar(select(AuthSession))
        event = enqueue_event(db, event_type="first_access", event_key="disabled-new-event",
                              values={}, target_path="/admin", recipients=[owner.subject_id])
        db.commit()
        delivery = db.scalar(select(NotificationDelivery).where(
            NotificationDelivery.event_id == event.id, NotificationDelivery.channel == "push"))
        assert delivery.status == "cancelled"
    monkeypatch.setenv("WEB_PUSH_ENABLED", "true")
    assert not process_next_notification("push", push_sender=fail)


def test_lost_lease_does_not_overwrite_another_worker(monkeypatch):
    queued(monkeypatch)
    def recovered(*_args, **_kwargs):
        with SessionLocal() as db:
            item = db.get(NotificationDelivery, status("push").id)
            item.status, item.lease_token = "cancelled", None
            db.commit()
    process_next_notification("push", push_sender=recovered)
    assert status("push").status == "cancelled"
