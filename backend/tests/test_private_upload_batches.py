from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.auth import (
    AdminUser,
    AuthSession,
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    MediaDerivative,
    MediaJob,
    NotificationEvent,
    PhotoAsset,
    PhotoFolder,
    PrivateUploadBatch,
    PrivateUploadBatchAsset,
    SessionLocal,
)
from app.private_upload_batches import process_ready_batches
from tests.test_notification_settings import authenticated, isolated_schema  # noqa: F401


def setup_private():
    from app.auth import ParentGallery
    browser = authenticated()
    with SessionLocal() as db:
        session = db.scalar(select(AuthSession))
        db.add(AdminUser(id=session.subject_id, email="synthetic@example.invalid",
                         password_hash="unused", totp_secret="unused", email_verified=True))
        client = Client(full_name="Sintético", phone_e164="+5511999999999")
        parent = ParentGallery(name="Teste")
        db.add_all([client, parent])
        db.flush()
        gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=client.id, name="Privada")
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, derived_gallery_id=gallery.id, name="Fotos")
        db.add(folder)
        db.commit()
    return browser, gallery.id, folder.id


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
        assert db.scalar(select(func.count(PrivateUploadBatchAsset.batch_id))) == 1
        assert db.scalar(select(PrivateUploadBatchAsset.batch_id)) == UUID(batch)
    browser.cookies.clear()
    assert browser.get(path).status_code == 403


def test_batch_waits_for_previews_handles_partial_failure_and_never_replays():
    browser, gallery_id, folder_id = setup_private()
    path = f"/admin/derived-galleries/{gallery_id}/upload-batches"
    batch_id = UUID(browser.post(path).json()["id"])
    photo_ids = []
    for number in range(2):
        registered = browser.post(f"/admin/photo-folders/{folder_id}/photos", json={
            "filename": f"{number}.jpg", "storage_key": f"private/{gallery_id}/{number}.jpg",
            "upload_batch_id": str(batch_id),
        })
        photo_ids.append(UUID(registered.json()["id"]))
    with SessionLocal() as db:
        db.add_all([MediaJob(photo_asset_id=photo_id) for photo_id in photo_ids])
        db.commit()
        assert not process_ready_batches(db)  # aberto, sem anúncio prematuro
    browser.post(f"{path}/{batch_id}/close")
    with SessionLocal() as db:
        assert not process_ready_batches(db)  # job pendente
        gallery = db.get(DerivedGallery, gallery_id)
        late = Client(full_name="Novo membro", phone_e164="+5511888888888")
        db.add(late)
        db.flush()
        db.add_all([DerivedGalleryMembership(derived_gallery_id=gallery_id,
                    parent_gallery_id=gallery.parent_gallery_id, client_id=client_id)
                    for client_id in (gallery.client_id, late.id)])
        for job in db.scalars(select(MediaJob)):
            job.status = "completed" if job.photo_asset_id == photo_ids[0] else "failed"
        db.get(PhotoFolder, folder_id).status = "released"
        db.get(PhotoAsset, photo_ids[0]).available = True
        db.add(MediaDerivative(photo_asset_id=photo_ids[0], variant="client_preview",
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
                "filename": "failed.jpg", "storage_key": f"private/{gallery_id}/failed.jpg",
                "upload_batch_id": batch_id,
            })
            with SessionLocal() as db:
                photo_id = UUID(registered.json()["id"])
                db.add(MediaJob(photo_asset_id=photo_id, status="failed"))
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
        "filename": "ready.jpg", "storage_key": f"private/{gallery_id}/ready.jpg", "upload_batch_id": batch_id,
    })
    browser.post(f"{path}/{batch_id}/close")
    with SessionLocal() as db:
        photo_id = UUID(result.json()["id"])
        gallery = db.get(DerivedGallery, gallery_id)
        db.add(DerivedGalleryMembership(derived_gallery_id=gallery_id,
                parent_gallery_id=gallery.parent_gallery_id, client_id=gallery.client_id, status="blocked"))
        db.get(PhotoFolder, folder_id).status = "released"
        db.get(PhotoAsset, photo_id).available = True
        db.add(MediaDerivative(photo_asset_id=photo_id, variant="client_preview", status="ready",
                                relative_path="ready.jpg"))
        db.commit()
        assert process_ready_batches(db)
        assert db.scalar(select(func.count(NotificationEvent.id))) == 0
