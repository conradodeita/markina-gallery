from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.auth import (
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
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
    SessionLocal,
)
from app.notification_delivery import recipient_allowed
from app.private_upload_batches import process_ready_batches
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_notification_settings import authenticated, isolated_schema  # noqa: F401


def setup_private():
    from app.auth import ParentGallery
    browser = authenticated()
    with SessionLocal() as db:
        client = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Sintético", phone_e164="+5511999999999")
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Teste")
        db.add_all([client, parent])
        db.flush()
        gallery = DerivedGallery(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, client_id=client.id, name="Privada")
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, derived_gallery_id=gallery.id, name="Fotos")
        db.add(folder)
        db.commit()
    return browser, gallery.id, folder.id


def setup_restricted_folder():
    browser, gallery_id, _ = setup_private()
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        parent = db.get(ParentGallery, gallery.parent_gallery_id)
        client_id = gallery.client_id
        state = GalleryClientState(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id,
            client_id=client_id, status="active",
        )
        registration = ParentGalleryRegistration(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id,
            client_id=client_id, status="active",
        )
        db.add_all([state, registration])
        db.flush()
        folder = PhotoFolder(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id,
            name="Pasta restrita", purpose="content", audience_scope="selected",
        )
        db.add(folder)
        db.flush()
        db.add(FolderClientGrant(
            tenant_id=FIXTURE_TENANT_ID, folder_id=folder.id,
            parent_gallery_id=parent.id, client_id=client_id,
        ))
        db.commit()
        return browser, parent.id, client_id, folder.id


def test_upload_batch_reload_partial_close_dedupe_and_scope():
    browser, gallery, folder = setup_private()
    path = f"/admin/derived-galleries/{gallery}/upload-batches"
    batch = browser.post(path).json()["id"]
    payload = {"filename": "foto.jpg", "storage_key": f"private/{gallery}/{folder}/hash.jpg",
               "upload_batch_id": batch}
    register = f"/admin/photo-folders/{folder}/photos"
    first = browser.post(register, json=payload)
    assert first.status_code == 201
    assert browser.post(register, json=payload).json()["id"] == first.json()["id"]
    reopened = browser.get(path).json()["batches"]
    assert len(reopened) == 1 and reopened[0]["count"] == 1
    assert reopened[0]["assets"][0]["status"] == "not_imported"
    assert browser.post(f"{path}/{batch}/close").json()["status"] == "closed"
    assert browser.post(f"{path}/{batch}/close").json()["status"] == "closed"
    assert browser.get(path).json()["batches"] == []
    assert browser.post(register, json=payload).status_code == 409
    next_batch = browser.post(path).json()["id"]
    duplicate = browser.post(register, json={**payload, "upload_batch_id": next_batch})
    assert duplicate.json()["duplicate"] == "true"
    assert browser.post(register, json={**payload, "upload_batch_id": str(uuid4())}).status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(func.count(PhotoAsset.id))) == 1
        assert db.scalar(select(func.count(PrivateUploadBatchAsset.batch_id))) == 2
        assert set(db.scalars(select(PrivateUploadBatchAsset.batch_id))) == {UUID(batch), UUID(next_batch)}
    browser.cookies.clear()
    assert browser.get(path).status_code == 403


def test_batch_waits_for_previews_handles_partial_failure_and_never_replays():
    browser, gallery_id, folder_id = setup_private()
    path = f"/admin/derived-galleries/{gallery_id}/upload-batches"
    batch_id = UUID(browser.post(path).json()["id"])
    photo_ids = []
    for number in range(2):
        registered = browser.post(f"/admin/photo-folders/{folder_id}/photos", json={
            "filename": f"{number}.jpg", "storage_key": f"private/{gallery_id}/{folder_id}/{number}.jpg",
            "upload_batch_id": str(batch_id),
        })
        photo_ids.append(UUID(registered.json()["id"]))
    with SessionLocal() as db:
        db.add_all([MediaJob(tenant_id=FIXTURE_TENANT_ID, photo_asset_id=photo_id) for photo_id in photo_ids])
        db.commit()
        assert not process_ready_batches(db)  # aberto, sem anúncio prematuro
    browser.post(f"{path}/{batch_id}/close")
    with SessionLocal() as db:
        assert not process_ready_batches(db)  # job pendente
        gallery = db.get(DerivedGallery, gallery_id)
        late = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Novo membro", phone_e164="+5511888888888")
        db.add(late)
        db.flush()
        db.add_all([DerivedGalleryMembership(tenant_id=FIXTURE_TENANT_ID, derived_gallery_id=gallery_id,
                    parent_gallery_id=gallery.parent_gallery_id, client_id=client_id)
                    for client_id in (gallery.client_id, late.id)])
        for job in db.scalars(select(MediaJob)):
            job.status = "completed" if job.photo_asset_id == photo_ids[0] else "failed"
        db.get(PhotoFolder, folder_id).status = "released"
        db.get(PhotoAsset, photo_ids[0]).available = True
        db.add(MediaDerivative(tenant_id=FIXTURE_TENANT_ID, photo_asset_id=photo_ids[0], variant="client_preview",
                                status="ready", relative_path="synthetic/preview.jpg"))
        db.commit()
        assert process_ready_batches(db)
        events = list(db.scalars(select(NotificationEvent)))
        assert len(events) == 1
        assert events[0].client_id == gallery.client_id  # membro posterior não recebe
        assert events[0].event_type == "private_photos_ready"
        assert db.get(PrivateUploadBatch, batch_id).status == "completed"
        assert not process_ready_batches(db)
        # Retry posterior de falha não repete anúncio.
        db.scalar(select(MediaJob).where(MediaJob.photo_asset_id == photo_ids[1])).status = "completed"
        db.commit()
        assert not process_ready_batches(db)


def test_failed_empty_or_revoked_batches_do_not_announce():
    browser, gallery_id, folder_id = setup_private()
    path = f"/admin/derived-galleries/{gallery_id}/upload-batches"
    for index in range(2):
        batch_id = browser.post(path).json()["id"]
        if index:
            registered = browser.post(f"/admin/photo-folders/{folder_id}/photos", json={
                "filename": "failed.jpg", "storage_key": f"private/{gallery_id}/{folder_id}/failed.jpg",
                "upload_batch_id": batch_id,
            })
            with SessionLocal() as db:
                photo_id = UUID(registered.json()["id"])
                db.add(MediaJob(tenant_id=FIXTURE_TENANT_ID, photo_asset_id=photo_id, status="failed"))
                db.commit()
        browser.post(f"{path}/{batch_id}/close")
        with SessionLocal() as db:
            assert process_ready_batches(db)
            assert db.scalar(select(func.count(NotificationEvent.id))) == 0


def test_ready_batch_does_not_notify_member_revoked_after_close():
    browser, gallery_id, folder_id = setup_private()
    path = f"/admin/derived-galleries/{gallery_id}/upload-batches"
    batch_id = browser.post(path).json()["id"]
    result = browser.post(f"/admin/photo-folders/{folder_id}/photos", json={
        "filename": "ready.jpg", "storage_key": f"private/{gallery_id}/{folder_id}/ready.jpg", "upload_batch_id": batch_id,
    })
    browser.post(f"{path}/{batch_id}/close")
    with SessionLocal() as db:
        photo_id = UUID(result.json()["id"])
        gallery = db.get(DerivedGallery, gallery_id)
        db.add(DerivedGalleryMembership(tenant_id=FIXTURE_TENANT_ID, derived_gallery_id=gallery_id,
                parent_gallery_id=gallery.parent_gallery_id, client_id=gallery.client_id, status="blocked"))
        db.get(PhotoFolder, folder_id).status = "released"
        db.get(PhotoAsset, photo_id).available = True
        db.add(MediaDerivative(tenant_id=FIXTURE_TENANT_ID, photo_asset_id=photo_id, variant="client_preview", status="ready",
                                relative_path="ready.jpg"))
        db.commit()
        assert process_ready_batches(db)
        assert db.scalar(select(func.count(NotificationEvent.id))) == 0


def test_completed_private_batch_queues_each_enabled_channel_but_public_upload_does_not():
    browser, gallery_id, folder_id = setup_private()
    path = f"/admin/derived-galleries/{gallery_id}/upload-batches"
    batch_id = browser.post(path).json()["id"]
    registered = browser.post(f"/admin/photo-folders/{folder_id}/photos", json={
        "filename": "private-ready.jpg",
        "storage_key": f"private/{gallery_id}/{folder_id}/private-ready.jpg",
        "upload_batch_id": batch_id,
    })
    assert registered.status_code == 201, registered.text
    browser.post(f"{path}/{batch_id}/close")

    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        private_photo_id = UUID(registered.json()["id"])
        db.add(NotificationSetting(
            tenant_id=FIXTURE_TENANT_ID,
            event_type="private_photos_ready",
            push_enabled=True,
            whatsapp_enabled=True,
            whatsapp_body="Novas fotos em {{galeria}}.",
            push_title="Novas fotos",
            push_body="Novas fotos disponíveis.",
        ))
        db.add(PushSubscription(
            tenant_id=FIXTURE_TENANT_ID,
            endpoint_fingerprint="a" * 64,
            encrypted_subscription="ciphertext",
            role="client",
            subject_id=gallery.client_id,
            client_subject_id=gallery.client_id,
        ))
        private_folder = db.get(PhotoFolder, folder_id)
        private_folder.status = "released"
        db.get(PhotoAsset, private_photo_id).available = True
        db.add(MediaJob(tenant_id=FIXTURE_TENANT_ID, photo_asset_id=private_photo_id, status="completed"))
        db.add(MediaDerivative(
            tenant_id=FIXTURE_TENANT_ID,
            photo_asset_id=private_photo_id,
            variant="client_preview",
            status="ready",
            relative_path="private-ready.jpg",
        ))

        public_folder = PhotoFolder(
            tenant_id=FIXTURE_TENANT_ID,
            parent_gallery_id=gallery.parent_gallery_id,
            name="Pasta pública",
            purpose="content",
            audience_scope="all",
            position=1,
        )
        db.add(public_folder)
        db.flush()
        public_photo = PhotoAsset(
            tenant_id=FIXTURE_TENANT_ID,
            parent_gallery_id=gallery.parent_gallery_id,
            folder_id=public_folder.id,
            filename="public-ready.jpg",
            storage_key=f"events/{gallery.parent_gallery_id}/public-ready.jpg",
            available=True,
        )
        db.add(public_photo)
        db.flush()
        db.add_all([
            MediaJob(tenant_id=FIXTURE_TENANT_ID, photo_asset_id=public_photo.id, status="completed"),
            MediaDerivative(
                tenant_id=FIXTURE_TENANT_ID,
                photo_asset_id=public_photo.id,
                variant="client_preview",
                status="ready",
                relative_path="public-ready.jpg",
            ),
        ])
        db.commit()

        assert process_ready_batches(db)
        events = list(db.scalars(select(NotificationEvent).where(
            NotificationEvent.tenant_id == FIXTURE_TENANT_ID,
        )))
        assert len(events) == 1
        assert events[0].event_type == "private_photos_ready"
        deliveries = list(db.scalars(select(NotificationDelivery).where(
            NotificationDelivery.tenant_id == FIXTURE_TENANT_ID,
            NotificationDelivery.event_id == events[0].id,
        )))
        assert {(item.channel, item.status) for item in deliveries} == {
            ("push", "queued"),
            ("whatsapp", "queued"),
        }


def test_canonical_restricted_folder_upload_notifies_only_after_closed_batch_is_ready():
    browser, parent_id, client_id, folder_id = setup_restricted_folder()
    path = f"/admin/photo-folders/{folder_id}/upload-batches"
    assert browser.get(path).json()["batches"] == []
    batch_id = browser.post(path).json()["id"]
    registered = browser.post(f"/admin/photo-folders/{folder_id}/photos", json={
        "filename": "restrita.jpg", "storage_key": f"{parent_id}/{folder_id}/restrita.jpg",
        "upload_batch_id": batch_id,
    })
    assert registered.status_code == 201, registered.text
    photo_id = UUID(registered.json()["id"])
    with SessionLocal() as db:
        db.add(MediaJob(tenant_id=FIXTURE_TENANT_ID, photo_asset_id=photo_id, status="completed"))
        db.add(MediaDerivative(
            tenant_id=FIXTURE_TENANT_ID, photo_asset_id=photo_id,
            variant="client_preview", status="ready", relative_path="restricted/ready.jpg",
        ))
        db.get(PhotoAsset, photo_id).available = True
        db.get(PhotoFolder, folder_id).status = "released"
        db.add(NotificationSetting(
            tenant_id=FIXTURE_TENANT_ID, event_type="private_photos_ready",
            push_enabled=True, whatsapp_enabled=True,
            whatsapp_body="Novas fotos em {{galeria}}.",
            push_title="Novas fotos", push_body="Novas fotos disponíveis.",
        ))
        db.add(PushSubscription(
            tenant_id=FIXTURE_TENANT_ID, endpoint_fingerprint="b" * 64,
            encrypted_subscription="ciphertext", role="client", subject_id=client_id,
            client_subject_id=client_id,
        ))
        db.commit()
        assert not process_ready_batches(db)  # lote aberto não anuncia

    assert browser.post(f"{path}/{batch_id}/close").json()["status"] == "closed"
    with SessionLocal() as db:
        assert process_ready_batches(db)
        events = list(db.scalars(select(NotificationEvent).where(
            NotificationEvent.tenant_id == FIXTURE_TENANT_ID,
        )))
        assert len(events) == 1
        assert events[0].event_type == "private_photos_ready"
        assert events[0].client_id == client_id
        deliveries = list(db.scalars(select(NotificationDelivery).where(
            NotificationDelivery.tenant_id == FIXTURE_TENANT_ID,
            NotificationDelivery.event_id == events[0].id,
        )))
        assert {(item.channel, item.status) for item in deliveries} == {
            ("push", "queued"), ("whatsapp", "queued"),
        }
        db.delete(db.scalar(select(FolderClientGrant).where(
            FolderClientGrant.tenant_id == FIXTURE_TENANT_ID,
            FolderClientGrant.folder_id == folder_id,
            FolderClientGrant.client_id == client_id,
        )))
        assert not recipient_allowed(db, events[0], deliveries[0])
        assert not process_ready_batches(db)  # retomada/deduplicação
        assert db.get(PrivateUploadBatch, UUID(batch_id)).status == "completed"

    assert browser.get(f"/admin/photo-folders/{folder_id}/upload-batches").json()["batches"] == []
    with SessionLocal() as db:
        public_folder = PhotoFolder(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent_id,
            name="Pasta pública", purpose="content", audience_scope="all", position=1,
        )
        db.add(public_folder)
        db.flush()
        public_folder_id = public_folder.id
        db.commit()
    assert browser.post(f"/admin/photo-folders/{public_folder_id}/upload-batches").status_code == 404
    public_photo = browser.post(f"/admin/photo-folders/{public_folder_id}/photos", json={
        "filename": "publico.jpg", "storage_key": f"{parent_id}/{public_folder_id}/publico.jpg",
    })
    assert public_photo.status_code == 201
    with SessionLocal() as db:
        public_photo_id = UUID(public_photo.json()["id"])
        db.get(PhotoAsset, public_photo_id).available = True
        db.get(PhotoFolder, public_folder_id).status = "released"
        db.add(MediaDerivative(
            tenant_id=FIXTURE_TENANT_ID, photo_asset_id=public_photo_id,
            variant="client_preview", status="ready", relative_path="public/ready.jpg",
        ))
        db.commit()
        assert not process_ready_batches(db)
        assert db.scalar(select(func.count(NotificationEvent.id))) == 1
