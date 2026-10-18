"""Avisos privados atravessam autorização e transporte sem chamadas externas."""

from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.auth import (
    ClientPhone,
    FolderClientGrant,
    GalleryClientState,
    NotificationDelivery,
    NotificationEvent,
    NotificationSetting,
    PhotoFolder,
    SessionLocal,
    now,
)
from app.messaging import SandboxWhatsAppProvider
from app.notification_delivery import process_next_notification, recipient_allowed
from app.notification_events import record_restricted_folder_ready
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_notification_settings import isolated_schema  # noqa: F401
from tests.test_private_upload_batches import setup_restricted_folder


def queue_notice(monkeypatch, *, gate_enabled=True, batch_key=None):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv("TRANSACTIONAL_WHATSAPP_ENABLED", str(gate_enabled).lower())
    _, parent_id, client_id, folder_id = setup_restricted_folder()
    with SessionLocal() as db:
        folder = db.get(PhotoFolder, folder_id)
        folder.status = "released"
        db.add(NotificationSetting(
            tenant_id=FIXTURE_TENANT_ID, event_type="private_photos_ready",
            whatsapp_enabled=True, push_enabled=False,
            whatsapp_body="Novas fotos disponíveis.", push_title="Fotos", push_body="Fotos prontas.",
        ))
        db.add(ClientPhone(
            tenant_id=FIXTURE_TENANT_ID, client_id=client_id,
            phone_e164="+5511999999999", active=True, verified_at=now(),
        ))
        assert record_restricted_folder_ready(
            db, folder=folder, photo_ids={uuid4()}, batch_key=batch_key or str(uuid4()),
        ) == 1
        db.commit()
        event = db.scalar(select(NotificationEvent))
        delivery = db.scalar(select(NotificationDelivery))
        return event.id, delivery.id, parent_id, client_id, folder_id


class RecordingProvider(SandboxWhatsAppProvider):
    def __init__(self):
        self.calls = []

    def send_transactional(self, phone_e164, message, *, idempotency_key):
        self.calls.append((phone_e164, message))
        return super().send_transactional(phone_e164, message, idempotency_key=idempotency_key)


@pytest.mark.parametrize("batch_key", [None, "publish"])
def test_private_notice_reaches_transport_with_compact_or_legacy_key(monkeypatch, batch_key):
    event_id, delivery_id, _, _, _ = queue_notice(monkeypatch, batch_key=batch_key)
    with SessionLocal() as db:
        event = db.get(NotificationEvent, event_id)
        assert len(event.event_key) <= 192
        assert recipient_allowed(db, event, db.get(NotificationDelivery, delivery_id))
    provider = RecordingProvider()
    assert process_next_notification("whatsapp", whatsapp_provider=provider)
    assert provider.calls == [("+5511999999999", "Novas fotos disponíveis.")]
    with SessionLocal() as db:
        item = db.get(NotificationDelivery, delivery_id)
        assert (item.status, item.attempts, item.last_error) == ("accepted", 1, None)
    assert not process_next_notification("whatsapp", whatsapp_provider=provider)
    assert len(provider.calls) == 1


@pytest.mark.parametrize("change", [
    "recreated_grant", "blocked_client", "unreleased_folder", "opaque", "malformed", "other_folder",
])
def test_private_notice_revalidates_authorization_before_transport(monkeypatch, change):
    event_id, delivery_id, parent_id, client_id, folder_id = queue_notice(monkeypatch)
    with SessionLocal() as db:
        event = db.get(NotificationEvent, event_id)
        if change == "recreated_grant":
            grant = db.scalar(select(FolderClientGrant).where(FolderClientGrant.folder_id == folder_id))
            db.delete(grant)
            db.flush()
            db.add(FolderClientGrant(
                tenant_id=FIXTURE_TENANT_ID, folder_id=folder_id,
                parent_gallery_id=parent_id, client_id=client_id,
            ))
        elif change == "blocked_client":
            state = db.scalar(select(GalleryClientState).where(
                GalleryClientState.parent_gallery_id == parent_id,
                GalleryClientState.client_id == client_id,
            ))
            state.status = "blocked"
        elif change == "unreleased_folder":
            db.get(PhotoFolder, folder_id).status = "preparing"
        elif change == "opaque":
            event.event_key = f"private_photos_ready:{sha256(event.event_key.encode()).hexdigest()}"
        elif change == "malformed":
            event.event_key = f"private_photos_ready:v2:{folder_id.hex}:invalid:{'a' * 64}"
        else:
            event.event_key = event.event_key.replace(folder_id.hex, uuid4().hex)
        db.commit()
    provider = RecordingProvider()
    assert process_next_notification("whatsapp", whatsapp_provider=provider)
    assert provider.calls == []
    with SessionLocal() as db:
        item = db.get(NotificationDelivery, delivery_id)
        assert (item.status, item.attempts, item.last_error) == (
            "cancelled", 0, "recipient_not_authorized",
        )


def test_private_notice_global_gate_does_not_replay_cancelled_history(monkeypatch):
    _, delivery_id, _, _, _ = queue_notice(monkeypatch, gate_enabled=False)
    with SessionLocal() as db:
        item = db.get(NotificationDelivery, delivery_id)
        assert (item.status, item.attempts, item.last_error) == ("cancelled", 0, "transport_disabled")
    monkeypatch.setenv("TRANSACTIONAL_WHATSAPP_ENABLED", "true")
    provider = RecordingProvider()
    assert not process_next_notification("whatsapp", whatsapp_provider=provider)
    assert provider.calls == []
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(NotificationDelivery)) == 1
