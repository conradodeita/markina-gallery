"""O lote privado deve concluir respeitando o limite real da chave do evento."""

from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    Client,
    FolderClientGrant,
    GalleryClientState,
    MediaDerivative,
    MediaJob,
    NotificationDelivery,
    NotificationEvent,
    NotificationSetting,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFolder,
    PrivateUploadBatch,
    PrivateUploadBatchAsset,
    PushSubscription,
    Tenant,
    TenantAdmin,
)
from app.notification_delivery import recipient_allowed
from app.notification_events import record_restricted_folder_ready
from app.private_upload_batches import process_ready_batches
from tests.test_tenant_migration import migrate

pytest_plugins = ("tests.test_private_upload_batch_migration",)


def test_private_notification_key_fits_postgres_preserves_retries_and_legacy_keys(
    private_batch_migration_database: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRANSACTIONAL_WHATSAPP_ENABLED", "true")
    monkeypatch.setenv("WEB_PUSH_ENABLED", "true")
    migrate(private_batch_migration_database, "upgrade", "20261017_0083")
    engine = create_engine(private_batch_migration_database)
    try:
        with Session(engine) as db:
            owner = Tenant()
            db.add(owner)
            db.flush()
            admin = AdminUser(email="private-notice@example.test", password_hash="synthetic", totp_secret="synthetic")
            client = Client(tenant_id=owner.id, full_name="Cliente sintética", phone_e164="+5511999999630")
            parent = ParentGallery(tenant_id=owner.id, name="Galeria sintética")
            db.add_all([admin, client, parent])
            db.flush()
            folder = PhotoFolder(
                tenant_id=owner.id, parent_gallery_id=parent.id, name="Pasta sintética",
                purpose="content", audience_scope="selected", status="released",
            )
            db.add_all([
                folder,
                GalleryClientState(tenant_id=owner.id, parent_gallery_id=parent.id, client_id=client.id, status="active"),
                ParentGalleryRegistration(tenant_id=owner.id, parent_gallery_id=parent.id, client_id=client.id, status="active"),
            ])
            db.flush()
            grant = FolderClientGrant(tenant_id=owner.id, folder_id=folder.id, parent_gallery_id=parent.id, client_id=client.id)
            photo = PhotoAsset(
                tenant_id=owner.id, parent_gallery_id=parent.id, folder_id=folder.id,
                filename="synthetic.jpg", storage_key="synthetic/private.jpg", available=True,
            )
            db.add_all([
                grant, photo,
                TenantAdmin(tenant_id=owner.id, admin_user_id=admin.id),
                NotificationSetting(
                    tenant_id=owner.id, event_type="private_photos_ready", push_enabled=True, whatsapp_enabled=True,
                    push_title="Novas fotos", push_body="Novas fotos disponíveis.", whatsapp_body="Novas fotos disponíveis.",
                ),
                PushSubscription(
                    tenant_id=owner.id, endpoint_fingerprint="f" * 64, encrypted_subscription="synthetic-ciphertext",
                    role="client", subject_id=client.id, client_subject_id=client.id,
                ),
            ])
            db.flush()
            batch = PrivateUploadBatch(tenant_id=owner.id, parent_gallery_id=parent.id, folder_id=folder.id,
                                       actor_admin_id=admin.id, status="closed")
            db.add_all([
                batch,
                MediaJob(tenant_id=owner.id, photo_asset_id=photo.id, status="completed"),
                MediaDerivative(tenant_id=owner.id, photo_asset_id=photo.id, variant="client_preview",
                                status="ready", relative_path="synthetic/ready.jpg"),
            ])
            db.flush()
            db.add(PrivateUploadBatchAsset(tenant_id=owner.id, batch_id=batch.id, photo_asset_id=photo.id))
            db.commit()

            assert process_ready_batches(db)
            assert batch.status == "completed" and batch.announced_at is not None
            first = db.scalar(select(NotificationEvent).where(NotificationEvent.tenant_id == owner.id))
            assert first is not None and len(first.event_key) <= 192
            assert first.client_id == client.id
            deliveries = list(db.scalars(select(NotificationDelivery).where(NotificationDelivery.event_id == first.id)))
            assert {(item.channel, item.status) for item in deliveries} == {("push", "queued"), ("whatsapp", "queued")}
            assert all(recipient_allowed(db, first, item) for item in deliveries)

            assert not process_ready_batches(db)
            record_restricted_folder_ready(db, folder=folder, photo_ids={photo.id}, batch_key=str(batch.id))
            db.commit()
            assert db.scalar(select(func.count()).select_from(NotificationEvent)) == 1
            assert db.scalar(select(func.count()).select_from(NotificationDelivery)) == 2

            # Outro lote das mesmas fotos mantém uma identidade própria.
            record_restricted_folder_ready(db, folder=folder, photo_ids={photo.id}, batch_key=str(uuid4()))
            db.commit()
            events = list(db.scalars(select(NotificationEvent)))
            assert len(events) == 2 and len({item.event_key for item in events}) == 2
            assert all(len(item.event_key) <= 192 for item in events)

            # Chaves curtas já persistidas não podem originar avisos duplicados.
            legacy = events[1]
            digest = sha256(str(photo.id).encode()).hexdigest()[:24]
            legacy.event_key = f"private_photos_ready:{folder.id}:old:{digest}:{grant.id}:{client.id}"
            db.commit()
            assert len(legacy.event_key) <= 192
            legacy_id, expected_key = legacy.id, legacy.event_key
            record_restricted_folder_ready(db, folder=folder, photo_ids={photo.id}, batch_key="old")
            db.commit()
            assert db.get(NotificationEvent, legacy_id).event_key == expected_key
            assert db.scalar(select(func.count()).select_from(NotificationEvent)) == 2
            assert db.scalar(select(func.count()).select_from(NotificationDelivery)) == 4

            # A primeira chave opaca publicada não pode ser recriada/reanunciada.
            full_key = f"private_photos_ready:{folder.id}:{batch.id}:{digest}:{grant.id}:{client.id}"
            first.event_key = f"private_photos_ready:{sha256(full_key.encode()).hexdigest()}"
            db.commit()
            record_restricted_folder_ready(db, folder=folder, photo_ids={photo.id}, batch_key=str(batch.id))
            db.commit()
            assert db.scalar(select(func.count()).select_from(NotificationEvent)) == 2
            assert db.scalar(select(func.count()).select_from(NotificationDelivery)) == 4
            assert not recipient_allowed(db, first, deliveries[0])
    finally:
        engine.dispose()
