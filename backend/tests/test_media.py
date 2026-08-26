from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.auth import (
    AdminUser,
    AuditEvent,
    AuthSession,
    Base,
    Client,
    DerivedGallery,
    DerivedGalleryPhoto,
    GalleryAccess,
    MediaDerivative,
    MediaJob,
    ParentGallery,
    PhotoAsset,
    Role,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    engine,
    now,
    password_hasher,
    token_hash,
)
from app.main import app
from app.media import enqueue_derivatives, generate_derivatives
from app.worker import process_next_media_job


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


def test_generates_idempotent_protected_derivatives_without_exif(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    derivatives_root = tmp_path / "derivatives"
    source = source_root / "event" / "foto.jpg"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (2400, 1200), color=(60, 90, 120)).save(source, exif=b"Exif\x00\x00test")
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento")
        db.add(parent)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id, filename="foto.jpg", storage_key="event/foto.jpg"
        )
        db.add(photo)
        db.commit()
        first = generate_derivatives(db, photo)
        second = generate_derivatives(db, photo)
        assert {item.variant for item in first} == {"thumbnail", "client_preview", "admin_preview"}
        assert {item.id for item in first} == {item.id for item in second}
    client_preview = derivatives_root / str(photo.id) / "client_preview.jpg"
    admin_preview = derivatives_root / str(photo.id) / "admin_preview.jpg"
    assert client_preview.read_bytes() != admin_preview.read_bytes()
    with Image.open(client_preview) as rendered:
        assert rendered.width <= 1600
        assert not rendered.getexif()


def test_worker_processes_only_markina_media_job(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    derivatives_root = tmp_path / "derivatives"
    source = source_root / "event" / "worker.jpg"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (800, 600), color=(10, 20, 30)).save(source, format="JPEG")
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento")
        db.add(parent)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id, filename="worker.jpg", storage_key="event/worker.jpg"
        )
        db.add(photo)
        db.flush()
        job = enqueue_derivatives(db, photo)
        db.commit()
        job_id = job.id
        photo_id = photo.id
    assert process_next_media_job()
    with SessionLocal() as db:
        job = db.get(MediaJob, job_id)
        assert job.status == "completed"
        assert job.attempts == 1
    assert (derivatives_root / str(photo_id) / "thumbnail.jpg").is_file()
    assert not process_next_media_job()


def test_admin_imports_jpeg_to_private_source_and_queues_processing(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    with SessionLocal() as db:
        admin = AdminUser(
            email="foto@markina.test",
            password_hash=password_hasher.hash("senha-segura"),
            email_verified=True,
            totp_secret="test-secret",
        )
        parent = ParentGallery(name="Evento")
        db.add_all([admin, parent])
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id, filename="foto.jpg", storage_key="privado/foto.jpg"
        )
        db.add(photo)
        db.flush()
        token = "admin-session-test"
        db.add(
            AuthSession(
                token_hash=token_hash(token),
                role=Role.ADMIN.value,
                subject_id=admin.id,
                expires_at=now() + timedelta(days=1),
            )
        )
        db.commit()
        photo_id = photo.id

    image = Image.new("RGB", (100, 80), color=(11, 22, 33))
    from io import BytesIO

    body = BytesIO()
    image.save(body, format="JPEG")
    with TestClient(app) as client:
        client.cookies.set("markina_session", token)
        response = client.put(
            f"/admin/photo-assets/{photo_id}/source",
            content=body.getvalue(),
            headers={"content-type": "image/jpeg"},
        )
        assert response.status_code == 202
        assert client.get(f"/admin/photo-assets/{photo_id}/media-status").json() == {"status": "queued"}
        assert client.get("/media/source/privado/foto.jpg").status_code == 404
    assert (source_root / "privado" / "foto.jpg").is_file()
    with SessionLocal() as db:
        job = db.scalar(select(MediaJob).where(MediaJob.photo_asset_id == photo_id))
        assert job and job.status == "queued"


def test_protected_preview_requires_authorized_role_and_never_returns_original(tmp_path, monkeypatch):
    derivatives_root = tmp_path / "derivatives"
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    with SessionLocal() as db:
        admin = AdminUser(
            email="foto@markina.test",
            password_hash=password_hasher.hash("senha-segura"),
            email_verified=True,
            totp_secret="test-secret",
        )
        client_owner = Client(full_name="Cliente Autorizada", phone_e164="+5511999999999")
        client_other = Client(full_name="Outra Cliente", phone_e164="+5511888888888")
        parent = ParentGallery(name="Evento")
        db.add_all([admin, client_owner, client_other, parent])
        db.flush()
        photo = PhotoAsset(parent_gallery_id=parent.id, filename="original.jpg", storage_key="raw.jpg")
        gallery = DerivedGallery(
            parent_gallery_id=parent.id, client_id=client_owner.id, name="Galeria privada"
        )
        db.add_all([photo, gallery])
        db.flush()
        db.add_all(
            [
                GalleryAccess(client_id=client_owner.id, gallery_id=gallery.id),
                DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=photo.id),
                MediaDerivative(
                    photo_asset_id=photo.id,
                    variant="client_preview",
                    relative_path=f"{photo.id}/client_preview.jpg",
                    status="ready",
                ),
                MediaDerivative(
                    photo_asset_id=photo.id,
                    variant="admin_preview",
                    relative_path=f"{photo.id}/admin_preview.jpg",
                    status="ready",
                ),
            ]
        )
        order = SaleOrder(
            derived_gallery_id=gallery.id,
            client_id=client_owner.id,
            payment_status="confirmed",
            total_cents=2500,
        )
        db.add(order)
        db.flush()
        db.add(
            SaleOrderItem(
                sale_order_id=order.id,
                photo_asset_id=photo.id,
                filename_snapshot="original.jpg",
                unit_price_cents=2500,
            )
        )
        owner_token = "client-owner-token"
        other_token = "client-other-token"
        admin_token = "admin-token"
        for token, role, subject_id in (
            (owner_token, Role.CLIENT, client_owner.id),
            (other_token, Role.CLIENT, client_other.id),
            (admin_token, Role.ADMIN, admin.id),
        ):
            db.add(
                AuthSession(
                    token_hash=token_hash(token),
                    role=role.value,
                    subject_id=subject_id,
                    expires_at=now() + timedelta(days=1),
                )
            )
        db.commit()
        gallery_id, photo_id = gallery.id, photo.id

    client_file = derivatives_root / str(photo_id) / "client_preview.jpg"
    admin_file = derivatives_root / str(photo_id) / "admin_preview.jpg"
    client_file.parent.mkdir(parents=True)
    client_file.write_bytes(b"watermarked-client-preview")
    admin_file.write_bytes(b"admin-conference-preview")
    with TestClient(app) as client:
        client.cookies.set("markina_session", owner_token)
        response = client.get(f"/gallery/{gallery_id}/photos/{photo_id}/preview")
        assert response.status_code == 200
        assert response.content == b"watermarked-client-preview"
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["content-disposition"].startswith("inline")
        assert client.get(f"/admin/photo-assets/{photo_id}/preview").status_code == 403
        history = client.get("/library/purchases")
        assert history.status_code == 200
        assert history.json()["orders"][0]["items"][0]["preview_url"].startswith("/gallery/")

        client.cookies.set("markina_session", other_token)
        assert client.get(f"/gallery/{gallery_id}/photos/{photo_id}/preview").status_code == 403

        client.cookies.set("markina_session", admin_token)
        response = client.get(f"/admin/photo-assets/{photo_id}/preview")
        assert response.status_code == 200
        assert response.content == b"admin-conference-preview"
        history = client.get("/admin/purchases")
        assert history.status_code == 200
        assert history.json()["orders"][0]["items"][0]["preview_url"].startswith("/admin/")
    assert client_file.read_bytes() != admin_file.read_bytes()
    with SessionLocal() as db:
        events = set(db.scalars(select(AuditEvent.event)))
        assert "media_preview.client_viewed" in events
        assert "media_preview.admin_viewed" in events
