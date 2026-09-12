from datetime import timedelta
from math import hypot

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageChops, ImageFont
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
    GalleryReopeningNotificationOutbox,
    GalleryReopeningRequest,
    MediaDerivative,
    MediaJob,
    ParentGallery,
    PaymentCommunication,
    PaymentMessageTemplate,
    PaymentNotificationOutbox,
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
from app.messaging import WhatsAppDeliveryError, WhatsAppDeliveryResult
from app.worker import (
    process_next_gallery_reopening_notification,
    process_next_media_job,
    process_next_payment_notification,
)


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


def test_watermark_applies_configurable_opacity_shadow_position_and_security_lines():
    source = Image.new("RGB", (640, 420), color=(40, 60, 80))
    plain = watermark(
        source,
        BrandingSettings(
            watermark_text="PROTEGIDA",
            watermark_opacity=35,
            watermark_position="top-left",
            watermark_shadow=False,
            watermark_security_lines=False,
        ),
    )
    layered = watermark(
        source,
        BrandingSettings(
            watermark_text="PROTEGIDA",
            watermark_opacity=80,
            watermark_position="bottom-right",
            watermark_shadow=True,
            watermark_security_lines=True,
        ),
    )

    assert plain.size == layered.size == source.size
    assert plain.tobytes() != layered.tobytes()


@pytest.mark.parametrize(
    ("direction", "size", "position"),
    [
        ("horizontal", 10, "top-left"),
        ("diagonal", 48, "middle-center"),
        ("vertical", 96, "bottom-right"),
    ],
)
def test_watermark_composes_text_once_and_keeps_security_grid_independent(
    monkeypatch, direction, size, position
):
    source = Image.new("RGB", (1200, 800), color=(40, 60, 80))
    composites: list[tuple[tuple[int, int], tuple[int, int]]] = []
    original_alpha_composite = Image.Image.alpha_composite

    def recording_alpha_composite(self, overlay, dest=(0, 0), source=(0, 0)):
        composites.append((overlay.size, tuple(dest)))
        return original_alpha_composite(self, overlay, dest, source)

    monkeypatch.setattr(Image.Image, "alpha_composite", recording_alpha_composite)
    rendered = watermark(
        source,
        BrandingSettings(
            watermark_text="MARCA ÚNICA",
            watermark_direction=direction,
            watermark_size=size,
            watermark_position=position,
            watermark_shadow=True,
            watermark_security_lines=True,
        ),
    )

    grid_composites = [item for item in composites if item[0] == source.size]
    text_composites = [item for item in composites if item[0] != source.size]
    assert rendered.size == source.size
    assert len(grid_composites) == 1
    assert len(text_composites) == 1


def _watermark_extent(
    source: Image.Image, rendered: Image.Image, direction: str
) -> float:
    bounds = ImageChops.difference(source, rendered).getbbox()
    assert bounds
    left, top, right, bottom = bounds
    if direction == "horizontal":
        return right - left
    if direction == "vertical":
        return bottom - top
    return hypot(right - left, bottom - top)


@pytest.mark.parametrize("image_size", [(1200, 800), (800, 1200), (900, 900)])
@pytest.mark.parametrize("direction", ["horizontal", "vertical", "diagonal"])
@pytest.mark.parametrize("coverage", [10, 74, 96])
def test_watermark_size_tracks_directional_photo_coverage(
    image_size, direction, coverage
):
    source = Image.new("RGB", image_size, color=(40, 60, 80))
    rendered = watermark(
        source,
        BrandingSettings(
            watermark_text="MARCA ÚNICA",
            watermark_direction=direction,
            watermark_size=coverage,
            watermark_opacity=100,
            watermark_position="middle-center",
            watermark_shadow=False,
            watermark_security_lines=False,
        ),
    )

    margin = max(12, round(min(image_size) * 0.025))
    inner_width = image_size[0] - (margin * 2)
    inner_height = image_size[1] - (margin * 2)
    axis = {
        "horizontal": inner_width,
        "vertical": inner_height,
        "diagonal": hypot(inner_width, inner_height),
    }[direction]
    actual = _watermark_extent(source, rendered, direction)
    target = axis * coverage / 100
    assert actual <= target * 1.08
    assert actual >= target * (0.58 if direction == "diagonal" else 0.88)


@pytest.mark.parametrize("direction", ["horizontal", "vertical", "diagonal"])
@pytest.mark.parametrize("position", ["top-left", "middle-center", "bottom-right"])
def test_long_watermark_stays_inside_photo(monkeypatch, direction, position):
    source = Image.new("RGB", (720, 420), color=(40, 60, 80))
    composites: list[tuple[tuple[int, int], tuple[int, int]]] = []
    original_alpha_composite = Image.Image.alpha_composite

    def recording_alpha_composite(self, overlay, dest=(0, 0), source=(0, 0)):
        composites.append((overlay.size, tuple(dest)))
        return original_alpha_composite(self, overlay, dest, source)

    monkeypatch.setattr(Image.Image, "alpha_composite", recording_alpha_composite)
    rendered = watermark(
        source,
        BrandingSettings(
            watermark_text="FOTOGRAFIA PROTEGIDA POR DIREITOS AUTORAIS",
            watermark_direction=direction,
            watermark_size=96,
            watermark_opacity=100,
            watermark_position=position,
            watermark_shadow=True,
            watermark_security_lines=False,
        ),
    )

    assert rendered.size == source.size
    assert ImageChops.difference(source, rendered).getbbox() is not None
    assert len(composites) == 1
    (layer_width, layer_height), (anchor_x, anchor_y) = composites[0]
    assert 0 <= anchor_x <= source.width - layer_width
    assert 0 <= anchor_y <= source.height - layer_height


def test_watermark_font_fallback_preserves_proportional_rendering(monkeypatch):
    real_truetype = ImageFont.truetype

    def missing_configured_font(font, *args, **kwargs):
        if isinstance(font, str):
            raise OSError("fonte ausente")
        return real_truetype(font, *args, **kwargs)

    monkeypatch.setattr(
        ImageFont,
        "truetype",
        missing_configured_font,
    )
    source = Image.new("RGB", (900, 600), color=(40, 60, 80))
    rendered = watermark(
        source,
        BrandingSettings(
            watermark_text="FALLBACK",
            watermark_direction="horizontal",
            watermark_size=74,
            watermark_opacity=100,
            watermark_shadow=False,
        ),
    )

    assert _watermark_extent(source, rendered, "horizontal") > source.width * 0.6


def test_protection_reprocessing_does_not_rewrite_clean_analysis_preview(
    tmp_path, monkeypatch
):
    source_root = tmp_path / "source"
    derivatives_root = tmp_path / "derivatives"
    source = source_root / "event" / "protected-only.jpg"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (800, 600), color=(20, 40, 60)).save(source, format="JPEG")
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    with SessionLocal() as db:
        settings = BrandingSettings(watermark_text="PRIMEIRA MARCA")
        parent = ParentGallery(name="Evento")
        db.add_all((settings, parent))
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Fotos")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="protected-only.jpg",
            storage_key="event/protected-only.jpg",
        )
        db.add(photo)
        db.commit()
        generate_derivatives(db, photo)
        photo_id = photo.id
        admin_path = derivatives_root / str(photo_id) / "admin_preview.jpg"
        client_path = derivatives_root / str(photo_id) / "client_preview.jpg"
        clean_before = admin_path.read_bytes()
        protected_before = client_path.read_bytes()
        settings.watermark_text = "SEGUNDA MARCA"
        enqueue_derivatives(db, photo)
        client_derivative = db.scalar(
            select(MediaDerivative).where(
                MediaDerivative.photo_asset_id == photo.id,
                MediaDerivative.variant == "client_preview",
            )
        )
        assert client_derivative is not None
        client_derivative.status = "queued"
        db.commit()

    assert process_next_media_job()
    assert admin_path.read_bytes() == clean_before
    assert client_path.read_bytes() != protected_before


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
        photo = db.get(PhotoAsset, photo_id)
        folder = db.get(PhotoFolder, photo.folder_id)
        assert photo.available is True
        assert folder.status == "released"
        assert folder.released_at is not None
    assert (derivatives_root / str(photo_id) / "thumbnail.jpg").is_file()
    assert not process_next_media_job()


def test_failed_processing_does_not_publish_original(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento com falha")
        db.add(parent)
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Rodada protegida")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="ausente.jpg",
            storage_key="event/ausente.jpg",
            available=False,
        )
        db.add(photo)
        db.flush()
        job = enqueue_derivatives(db, photo)
        db.commit()
        photo_id, folder_id, job_id = photo.id, folder.id, job.id

    with pytest.raises(FileNotFoundError):
        process_next_media_job()

    with SessionLocal() as db:
        assert db.get(MediaJob, job_id).status == "failed"
        assert db.get(PhotoAsset, photo_id).available is False
        assert db.get(PhotoFolder, folder_id).status == "preparing"


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


def test_worker_sends_reopening_notice_without_changing_request(monkeypatch) -> None:
    sent: list[tuple[str, str, str]] = []

    class RecordingProvider:
        def send_transactional(self, phone_e164, message, *, idempotency_key):
            sent.append((phone_e164, message, idempotency_key))

    monkeypatch.setattr("app.worker.whatsapp_provider_from_environment", lambda: RecordingProvider())
    with SessionLocal() as db:
        client = Client(full_name="Cliente Reabertura", phone_e164="+5511555554401")
        parent = ParentGallery(name="Evento Reabertura")
        db.add_all([client, parent])
        db.flush()
        gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=client.id, name="Galeria Reabertura")
        db.add(gallery)
        db.flush()
        reopening = GalleryReopeningRequest(
            derived_gallery_id=gallery.id,
            requested_by_client_id=client.id,
            idempotency_key="reopening-worker-test",
        )
        db.add(reopening)
        db.flush()
        notice = GalleryReopeningNotificationOutbox(
            gallery_reopening_request_id=reopening.id,
            recipient_phone="+5511555554402",
            status="queued",
        )
        db.add(notice)
        db.commit()
        reopening_id, notice_id = reopening.id, notice.id

    assert process_next_gallery_reopening_notification() is True
    assert process_next_gallery_reopening_notification() is False
    assert len(sent) == 1
    assert sent[0][0] == "+5511555554402"
    assert "Galeria Reabertura" in sent[0][1]
    with SessionLocal() as db:
        assert db.get(GalleryReopeningRequest, reopening_id).status == "pending"
        assert db.get(GalleryReopeningNotificationOutbox, notice_id).status == "sent"


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
