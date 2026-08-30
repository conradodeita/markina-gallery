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
    BrandingSettings,
    Client,
    DerivedGallery,
    DerivedGalleryPhoto,
    GalleryAccess,
    MediaDerivative,
    MediaJob,
    PaymentCommunication,
    PaymentMessageTemplate,
    PaymentNotificationOutbox,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
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
from app.media import enqueue_derivatives, generate_derivatives, watermark
from app.worker import process_next_media_job, process_next_payment_notification
from app.messaging import WhatsAppDeliveryError, WhatsAppDeliveryResult


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
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Rodada 1")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="foto.jpg",
            storage_key="event/foto.jpg",
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


def test_watermark_direction_does_not_rotate_photo():
    source = Image.new("RGB", (320, 180), color=(40, 60, 80))
    settings = BrandingSettings(watermark_direction="diagonal", watermark_font="serif")
    rendered = watermark(source, settings)
    assert rendered.size == source.size
    assert rendered.mode == "RGB"


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
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Rodada 1")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="worker.jpg",
            storage_key="event/worker.jpg",
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
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Rodada 1")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="foto.jpg",
            storage_key="privado/foto.jpg",
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
        folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Rodada 1",
            status="released",
            released_at=now(),
        )
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="original.jpg",
            storage_key="raw.jpg",
        )
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


def test_worker_sends_payment_outbox_once_in_sandbox() -> None:
    with SessionLocal() as db:
        client = Client(full_name="Cliente Sandbox", phone_e164="+5511555554411")
        parent = ParentGallery(name="Evento Sandbox")
        db.add_all([client, parent])
        db.flush()
        gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=client.id, name="Galeria Sandbox")
        db.add(gallery)
        db.flush()
        order = SaleOrder(derived_gallery_id=gallery.id, client_id=client.id, payment_status="pending", total_cents=100)
        db.add(order)
        db.flush()
        communication = PaymentCommunication(sale_order_id=order.id, client_id=client.id, idempotency_key="pay-a")
        db.add(communication)
        db.flush()
        outbox = PaymentNotificationOutbox(payment_communication_id=communication.id, recipient_phone=client.phone_e164, template_kind="confirmed", idempotency_key="box-a")
        db.add(outbox)
        db.commit()
        outbox_id = outbox.id
    assert process_next_payment_notification() is True
    assert process_next_payment_notification() is False
    with SessionLocal() as db:
        delivered = db.get(PaymentNotificationOutbox, outbox_id)
        assert delivered.status == "sent"
        assert delivered.attempts == 1


def test_worker_retries_transient_payment_delivery_until_limit(monkeypatch) -> None:
    class FailingProvider:
        def send_transactional(self, phone_e164, message, *, idempotency_key):
            del phone_e164, message, idempotency_key
            raise WhatsAppDeliveryError("Provedor indisponível temporariamente.", transient=True)

    monkeypatch.setenv("WHATSAPP_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("WHATSAPP_RETRY_BASE_SECONDS", "0")
    monkeypatch.setattr("app.worker.whatsapp_provider_from_environment", lambda: FailingProvider())
    with SessionLocal() as db:
        client = Client(full_name="Cliente Retentativa", phone_e164="+5511555554422")
        parent = ParentGallery(name="Evento Retentativa")
        db.add_all([client, parent])
        db.flush()
        gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=client.id, name="Galeria Retentativa")
        db.add(gallery)
        db.flush()
        order = SaleOrder(derived_gallery_id=gallery.id, client_id=client.id, payment_status="pending", total_cents=100)
        db.add(order)
        db.flush()
        communication = PaymentCommunication(sale_order_id=order.id, client_id=client.id, idempotency_key="pay-b")
        db.add(communication)
        db.flush()
        outbox = PaymentNotificationOutbox(payment_communication_id=communication.id, recipient_phone=client.phone_e164, template_kind="confirmed", idempotency_key="box-b")
        db.add(outbox)
        db.commit()
        outbox_id = outbox.id

    assert process_next_payment_notification() is True
    with SessionLocal() as db:
        first_attempt = db.get(PaymentNotificationOutbox, outbox_id)
        assert first_attempt.status == "queued"
        assert first_attempt.attempts == 1
        assert first_attempt.last_error == "Provedor indisponível temporariamente."

    assert process_next_payment_notification() is True
    assert process_next_payment_notification() is False
    with SessionLocal() as db:
        exhausted = db.get(PaymentNotificationOutbox, outbox_id)
        assert exhausted.status == "failed"
        assert exhausted.attempts == 2


def test_worker_renders_controlled_template_without_financial_payload(monkeypatch) -> None:
    sent: list[tuple[str, str, str]] = []

    class RecordingProvider:
        def send_transactional(self, phone_e164, message, *, idempotency_key):
            sent.append((phone_e164, message, idempotency_key))
            return WhatsAppDeliveryResult(
                external_message_id="synthetic-template-message",
                recipient_phone_e164=phone_e164,
                provider_status="accepted",
            )

    monkeypatch.setattr("app.worker.whatsapp_provider_from_environment", lambda: RecordingProvider())
    with SessionLocal() as db:
        client = Client(full_name="Cliente Template", phone_e164="+5511555554433")
        parent = ParentGallery(name="Evento Template")
        db.add_all([client, parent])
        db.flush()
        gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=client.id, name="Galeria Template")
        db.add(gallery)
        db.flush()
        order = SaleOrder(
            derived_gallery_id=gallery.id,
            client_id=client.id,
            payment_status="pending",
            total_cents=100,
            client_name_snapshot=client.full_name,
            client_phone_snapshot=client.phone_e164,
            pix_copy_paste_snapshot="dado-bancario-nao-enviar",
        )
        db.add(order)
        db.flush()
        communication = PaymentCommunication(sale_order_id=order.id, client_id=client.id, idempotency_key="pay-c")
        db.add(communication)
        db.flush()
        db.add(PaymentMessageTemplate(kind="confirmed", body="Olá {{cliente}}, pedido {{pedido}} da {{galeria}} confirmado."))
        outbox = PaymentNotificationOutbox(payment_communication_id=communication.id, recipient_phone=client.phone_e164, template_kind="confirmed", idempotency_key="box-c")
        db.add(outbox)
        db.commit()

    assert process_next_payment_notification() is True
    assert len(sent) == 1
    assert sent[0][0] == "+5511555554433"
    assert "Cliente Template" in sent[0][1]
    assert "Galeria Template" in sent[0][1]
    assert "dado-bancario-nao-enviar" not in sent[0][1]
    assert sent[0][2] == "box-c"


def test_worker_blocks_unrelated_payment_recipient_without_sending(monkeypatch, capsys) -> None:
    sent: list[str] = []

    class RecordingProvider:
        def send_transactional(self, phone_e164, message, *, idempotency_key):
            del message, idempotency_key
            sent.append(phone_e164)

    monkeypatch.setattr("app.worker.whatsapp_provider_from_environment", lambda: RecordingProvider())
    with SessionLocal() as db:
        client = Client(full_name="Cliente Destino", phone_e164="+5511555554499")
        parent = ParentGallery(name="Evento Destino")
        db.add_all([client, parent])
        db.flush()
        gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=client.id, name="Galeria Destino")
        db.add(gallery)
        db.flush()
        order = SaleOrder(derived_gallery_id=gallery.id, client_id=client.id, payment_status="pending", total_cents=100, client_phone_snapshot=client.phone_e164)
        db.add(order)
        db.flush()
        communication = PaymentCommunication(sale_order_id=order.id, client_id=client.id, idempotency_key="pay-d")
        db.add(communication)
        db.flush()
        outbox = PaymentNotificationOutbox(payment_communication_id=communication.id, recipient_phone="+5511555554500", template_kind="confirmed", idempotency_key="box-d")
        db.add(outbox)
        db.commit()
        outbox_id = outbox.id

    assert process_next_payment_notification() is True
    assert sent == []
    with SessionLocal() as db:
        blocked = db.get(PaymentNotificationOutbox, outbox_id)
        assert blocked.status == "failed"
        assert blocked.last_error == "Configuração do provedor indisponível."
    captured = capsys.readouterr()
    assert "+5511555554500" not in captured.out + captured.err
