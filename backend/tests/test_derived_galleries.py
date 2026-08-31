from datetime import UTC, timedelta
from io import BytesIO
from uuid import UUID

import pyotp
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth import (
    AdminUser,
    AuditEvent,
    AuthChallenge,
    Base,
    BrandingSettings,
    Client,
    DerivedGallery,
    DerivedGalleryPhoto,
    MediaDerivative,
    MediaJob,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    PaymentNotificationOutbox,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    PhotoView,
    PixCheckoutSettings,
    PriceRule,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    engine,
    now,
    password_hasher,
    token_hash,
)
from app.checkout import create_pending_checkout
from app.gallery_access import issue_gallery_capability
from app.main import app
from app.media import generate_derivatives


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


def authenticate_admin(client: TestClient) -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == "foto@markina.test"))
        if not admin:
            admin = AdminUser(
                email="foto@markina.test",
                password_hash=password_hasher.hash("senha-segura"),
                email_verified=True,
                totp_secret=pyotp.random_base32(),
            )
            db.add(admin)
            db.commit()
        secret = admin.totp_secret
    challenge = client.post(
        "/auth/admin/password", json={"email": "foto@markina.test", "password": "senha-segura"}
    ).json()["challenge_id"]
    assert client.post(
        "/auth/admin/totp", json={"challenge_id": challenge, "code": pyotp.TOTP(secret).now()}
    ).status_code == 200


def authenticate_client(client: TestClient, phone: str) -> None:
    challenge = client.post(
        "/auth/client/challenge", json={"full_name": "Cliente", "phone": phone}
    ).json()["challenge_id"]
    with SessionLocal() as db:
        stored = db.get(AuthChallenge, UUID(challenge))
        stored.secret_hash = token_hash("123456")
        db.commit()
    assert client.post(
        "/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}
    ).status_code == 200


def test_branding_public_defaults_and_admin_plain_text_update(client: TestClient) -> None:
    public = client.get("/branding")
    assert public.status_code == 200
    assert public.json()["login_title"] == "Sua galeria, do seu jeito."
    assert client.get("/admin/branding").status_code == 403

    authenticate_admin(client)
    updated = client.patch(
        "/admin/branding",
        json={
            "login_title": "Acesso da sua galeria",
            "login_intro": "Fotos selecionadas com cuidado.",
            "login_helper": "Informe seus dados para continuar.",
        },
    )
    assert updated.status_code == 200
    assert client.get("/branding").json()["login_title"] == "Acesso da sua galeria"
    rejected = client.patch(
        "/admin/branding",
        json={
            "login_title": "<script>alert(1)</script>",
            "login_intro": "Texto",
            "login_helper": "Ajuda",
        },
    )
    assert rejected.status_code == 422


def branding_image_bytes(image_format: str = "PNG", size: tuple[int, int] = (64, 64)) -> bytes:
    body = BytesIO()
    Image.new("RGB", size, color=(40, 80, 60)).save(body, format=image_format)
    return body.getvalue()


def test_branding_assets_require_admin_and_validate_storage(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("BRANDING_ASSETS_ROOT", str(tmp_path / "branding"))
    image = branding_image_bytes()
    assert client.put("/admin/branding/logo", content=image, headers={"content-type": "image/png"}).status_code == 403

    authenticate_admin(client)
    for asset in ("logo", "app-icon", "favicon"):
        response = client.put(f"/admin/branding/{asset}", content=image, headers={"content-type": "image/png"})
        assert response.status_code == 200
        assert response.json()[f"{asset.replace('-', '_')}_url"] == f"/branding/{asset}"
        public = client.get(f"/branding/{asset}")
        assert public.status_code == 200
        assert public.headers["content-type"].startswith("image/png")
        assert public.content == image

    assert client.put("/admin/branding/logo", content=image, headers={"content-type": "image/jpeg"}).status_code == 415
    assert client.put("/admin/branding/favicon", content=branding_image_bytes("JPEG"), headers={"content-type": "image/jpeg"}).status_code == 422
    assert client.put("/admin/branding/logo", content=branding_image_bytes(size=(8, 8)), headers={"content-type": "image/png"}).status_code == 422


def test_global_visual_protection_requeues_existing_derivatives(client: TestClient) -> None:
    assert client.patch("/admin/branding/protection", json={
        "watermark_text": "NÃO AUTORIZADA", "watermark_font": "serif", "watermark_color": "#112233", "watermark_size": 30, "watermark_direction": "horizontal",
    }).status_code == 403
    assert "watermark_text" not in client.get("/branding").json()
    authenticate_admin(client)
    with SessionLocal() as db:
        gallery = ParentGallery(name="Galeria protegida")
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(parent_gallery_id=gallery.id, name="Lote")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(parent_gallery_id=gallery.id, folder_id=folder.id, filename="foto.jpg", storage_key="lote/foto.jpg")
        db.add(photo)
        db.flush()
        db.add(MediaJob(photo_asset_id=photo.id, status="completed"))
        db.add(MediaDerivative(photo_asset_id=photo.id, variant="client_preview", relative_path=f"{photo.id}/client_preview.jpg", status="ready"))
        db.commit()
        photo_id = photo.id

    response = client.patch("/admin/branding/protection", json={
        "watermark_text": "FOTÓGRAFA • PRÉVIA",
        "watermark_font": "serif",
        "watermark_color": "#112233",
        "watermark_size": 30,
        "watermark_direction": "horizontal",
    })
    assert response.status_code == 200
    assert response.json()["watermark_text"] == "FOTÓGRAFA • PRÉVIA"
    with SessionLocal() as db:
        settings = db.scalar(select(BrandingSettings).limit(1))
        job = db.scalar(select(MediaJob).where(MediaJob.photo_asset_id == photo_id))
        derivative = db.scalar(select(MediaDerivative).where(MediaDerivative.photo_asset_id == photo_id, MediaDerivative.variant == "client_preview"))
        assert settings and settings.watermark_font == "serif"
        assert job and job.status == "queued"
        assert derivative and derivative.status == "queued"
    assert client.patch("/admin/branding/protection", json={
        "watermark_text": "   ", "watermark_font": "serif", "watermark_color": "#112233", "watermark_size": 30, "watermark_direction": "horizontal",
    }).status_code == 422


def test_derivative_generation_uses_global_visual_protection(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_root = tmp_path / "source"
    derivatives_root = tmp_path / "derivatives"
    source = source_root / "lote" / "foto.jpg"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (640, 480), color=(30, 60, 90)).save(source, format="JPEG")
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    observed: list[str | None] = []

    def record_settings(image: Image.Image, settings: BrandingSettings | None) -> Image.Image:
        observed.append(settings.watermark_text if settings else None)
        return image

    monkeypatch.setattr("app.media.watermark", record_settings)
    with SessionLocal() as db:
        db.add(BrandingSettings(watermark_text="PROTEÇÃO GLOBAL"))
        gallery = ParentGallery(name="Galeria", watermark_text="VALOR LOCAL LEGADO")
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(parent_gallery_id=gallery.id, name="Lote")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=gallery.id,
            folder_id=folder.id,
            filename="foto.jpg",
            storage_key="lote/foto.jpg",
        )
        db.add(photo)
        db.commit()
        generate_derivatives(db, photo)

    assert observed == ["PROTEÇÃO GLOBAL"]


def create_folder_photo(
    client: TestClient,
    parent_id: UUID,
    *,
    folder_name: str = "Rodada 1",
    filename: str = "IMG_0001.jpg",
    storage_key: str = "events/one/img-0001.jpg",
) -> tuple[UUID, UUID]:
    folder_id = UUID(
        client.post(
            f"/admin/parent-galleries/{parent_id}/folders", json={"name": folder_name}
        ).json()["id"]
    )
    photo_id = UUID(
        client.post(
            f"/admin/photo-folders/{folder_id}/photos",
            json={"filename": filename, "storage_key": storage_key},
        ).json()["id"]
    )
    return folder_id, photo_id


def create_gallery_for_client(client: TestClient, person: Client, *, expires=False) -> tuple[UUID, UUID]:
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento"}).json()["id"])
    folder_id, photo_id = create_folder_photo(client, parent_id)
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}
    ).status_code == 200
    assert client.patch(
        f"/admin/parent-galleries/{parent_id}/settings",
        json={"favorites_enabled": True, "comments_enabled": True},
    ).status_code == 200
    payload = {
        "parent_gallery_id": str(parent_id),
        "client_id": str(person.id),
        "name": "Fotos privadas",
        "photo_ids": [str(photo_id)],
    }
    gallery_id = UUID(client.post("/admin/derived-galleries", json=payload).json()["id"])
    if expires:
        with SessionLocal() as db:
            db.get(DerivedGallery, gallery_id).selection_expires_at = now() - timedelta(
                minutes=1
            )
            db.commit()
    client.cookies.clear()
    return gallery_id, photo_id


def test_admin_creates_private_derived_gallery_without_copying_photo(client: TestClient):
    with SessionLocal() as db:
        person = Client(full_name="Cliente", phone_e164="+5511999999999")
        db.add(person)
        db.commit()
        client_id = person.id
    authenticate_admin(client)
    parent_id = UUID(
        client.post(
            "/admin/parent-galleries", json={"name": "Casamento da Ana", "event_name": "Ana e João"}
        ).json()["id"]
    )
    folder_id, photo_id = create_folder_photo(
        client, parent_id, storage_key="events/ana/img-0001.jpg"
    )
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}
    ).status_code == 200
    response = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(client_id),
            "name": "Fotos da Cliente",
            "photo_ids": [str(photo_id)],
        },
    )
    assert response.status_code == 201
    gallery_id = UUID(response.json()["id"])
    with SessionLocal() as db:
        assert db.get(DerivedGallery, gallery_id).client_id == client_id
        reference = db.scalar(
            select(DerivedGalleryPhoto).where(
                DerivedGalleryPhoto.derived_gallery_id == gallery_id
            )
        )
        assert reference.photo_asset_id == photo_id


def test_derived_gallery_rejects_photo_from_another_parent_gallery(client: TestClient):
    with SessionLocal() as db:
        person = Client(full_name="Cliente", phone_e164="+5511888888888")
        db.add(person)
        db.commit()
        client_id = person.id
    authenticate_admin(client)
    first_parent = UUID(client.post("/admin/parent-galleries", json={"name": "Evento A"}).json()["id"])
    second_parent = UUID(client.post("/admin/parent-galleries", json={"name": "Evento B"}).json()["id"])
    _, foreign_photo = create_folder_photo(
        client,
        second_parent,
        filename="IMG_0002.jpg",
        storage_key="events/b/img-0002.jpg",
    )
    response = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(first_parent),
            "client_id": str(client_id),
            "name": "Fotos privadas",
            "photo_ids": [str(foreign_photo)],
        },
    )
    assert response.status_code == 422


def test_client_library_is_limited_to_own_derived_gallery(client: TestClient):
    with SessionLocal() as db:
        person = Client(full_name="Cliente", phone_e164="+5511777777777")
        db.add(person)
        db.commit()
    response = client.post(
        "/auth/client/challenge", json={"full_name": "Cliente", "phone": "+5511777777777"}
    )
    challenge_id = UUID(response.json()["challenge_id"])
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, challenge_id)
        challenge.secret_hash = token_hash("123456")
        db.commit()
    assert client.post(
        "/auth/client/verify", json={"challenge_id": str(challenge_id), "code": "123456"}
    ).status_code == 200
    assert client.get("/library").json() == {
        "public_galleries": [],
        "private_galleries": [],
        "galleries": [],
    }


def test_admin_operational_catalog_creates_and_lists_only_authorized_data(client: TestClient):
    assert client.get("/admin/clients").status_code == 403
    authenticate_admin(client)
    created_client = client.post(
        "/admin/clients", json={"full_name": "Cliente Operacional", "phone_e164": "+55 11 98888-7777"}
    )
    assert created_client.status_code == 201
    assert client.post(
        "/admin/clients", json={"full_name": "Cliente Operacional", "phone_e164": "+5511988887777"}
    ).status_code == 409
    parent = client.post("/admin/parent-galleries", json={"name": "Acervo operacional"})
    assert parent.status_code == 201
    parent_id = parent.json()["id"]
    legacy = client.post(
        f"/admin/parent-galleries/{parent_id}/photos",
        json={"filename": "operacional.jpg", "storage_key": "operacional/foto.jpg"},
    )
    assert legacy.status_code == 410
    assert "pasta em preparação" in legacy.json()["detail"]
    _, photo_id = create_folder_photo(
        client,
        UUID(parent_id),
        filename="operacional.jpg",
        storage_key="operacional/foto.jpg",
    )
    assert client.get("/admin/clients").json()["clients"] == [
        {
            "id": created_client.json()["id"],
            "name": "Cliente Operacional",
            "phone": "+5511988887777",
        }
    ]
    assert client.get("/admin/clients?query=98888").json()["clients"][0]["name"] == (
        "Cliente Operacional"
    )
    assert client.get("/admin/parent-galleries").json()["parent_galleries"][0]["id"] == parent_id
    assert client.get(f"/admin/parent-galleries/{parent_id}/photos").json()["photos"] == [
        {"id": str(photo_id), "name": "operacional.jpg"}
    ]
    assert client.get(f"/admin/photo-assets/{photo_id}/media-status").json() == {
        "status": "not_imported"
    }


def test_admin_validation_summary_is_authorized_and_has_no_client_phone(client: TestClient):
    with SessionLocal() as db:
        db.add(Client(full_name="Cliente do resumo", phone_e164="+5511999999999"))
        db.commit()
    assert client.get("/admin/validation-summary").status_code == 403
    authenticate_admin(client)
    response = client.get("/admin/validation-summary")
    assert response.status_code == 200
    assert response.json()["counts"]["clients"] == 1
    assert "phone" not in response.text


def test_parent_gallery_editor_is_backend_driven_and_contextual(client: TestClient) -> None:
    parent_id = UUID("00000000-0000-0000-0000-000000000001")
    assert client.get(f"/admin/parent-galleries/{parent_id}/editor").status_code == 403
    authenticate_admin(client)
    parent_id = UUID(
        client.post(
            "/admin/parent-galleries",
            json={"name": "Evento escolar", "event_name": "Festa 2026"},
        ).json()["id"]
    )
    editor = client.get(f"/admin/parent-galleries/{parent_id}/editor")
    assert editor.status_code == 200
    assert [step["label"] for step in editor.json()["steps"]] == [
        "Ajustes",
        "Vendas",
        "Detalhes",
        "Imagens",
        "Clientes",
    ]
    assert editor.json()["capabilities"] == {
        "sales_configuration": True,
        "visual_customization": True,
        "folder_management": True,
        "client_links": True,
    }
    assert "storage_key" not in editor.text
    assert client.get(f"/admin/parent-galleries/{parent_id}/sales").json()["available"] is True
    details = client.get(f"/admin/parent-galleries/{parent_id}/details").json()
    assert details["available"] is True
    assert details["capabilities"] == ["cover", "title", "folder_organization"]
    assert details["settings"]["folder_display_mode"] == "individual"
    updated = client.patch(
        f"/admin/parent-galleries/{parent_id}/settings",
        json={"name": "Evento atualizado", "description": "Seleção das famílias"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Evento atualizado"
    create_folder_photo(client, parent_id)
    assert client.get(f"/admin/parent-galleries/{parent_id}/editor").json()["counts"]["folders"] == 1


def test_folder_and_photo_ownership_rejects_invalid_context(client: TestClient) -> None:
    authenticate_admin(client)
    missing = UUID("00000000-0000-0000-0000-000000000099")
    assert client.post(
        f"/admin/parent-galleries/{missing}/folders", json={"name": "Sem galeria"}
    ).status_code == 404
    first_parent = UUID(
        client.post("/admin/parent-galleries", json={"name": "Primeira"}).json()["id"]
    )
    second_parent = UUID(
        client.post("/admin/parent-galleries", json={"name": "Segunda"}).json()["id"]
    )
    folder_id, _ = create_folder_photo(client, first_parent)
    with SessionLocal() as db:
        db.add(
            PhotoAsset(
                parent_gallery_id=second_parent,
                folder_id=folder_id,
                filename="incoerente.jpg",
                storage_key="invalid/incoerente.jpg",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_folder_release_rejects_gallery_from_another_source(client: TestClient) -> None:
    authenticate_admin(client)
    owner_id = UUID(
        client.post(
            "/admin/clients",
            json={"full_name": "Responsável", "phone_e164": "+5511988877665"},
        ).json()["id"]
    )
    first_parent = UUID(
        client.post("/admin/parent-galleries", json={"name": "Primeira"}).json()["id"]
    )
    second_parent = UUID(
        client.post("/admin/parent-galleries", json={"name": "Segunda"}).json()["id"]
    )
    folder_id, _ = create_folder_photo(client, first_parent)
    second_folder_id, second_photo_id = create_folder_photo(
        client, second_parent, storage_key="events/second/img-0001.jpg"
    )
    assert client.post(
        f"/admin/photo-folders/{second_folder_id}/release",
        json={"gallery_ids": []},
    ).status_code == 200
    foreign_gallery = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(second_parent),
            "client_id": str(owner_id),
            "name": "Destino incorreto",
            "photo_ids": [str(second_photo_id)],
        },
    ).json()["id"]
    response = client.post(
        f"/admin/photo-folders/{folder_id}/release",
        json={"gallery_ids": [foreign_gallery]},
    )
    assert response.status_code == 422


def test_client_interactions_are_private_reversible_and_audited(client: TestClient):
    with SessionLocal() as db:
        person = Client(full_name="Cliente", phone_e164="+5511666666666")
        db.add(person)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, person)
    authenticate_client(client, person.phone_e164)
    review = client.get(f"/gallery/{gallery_id}/review")
    assert review.status_code == 200
    assert review.json()["gallery"]["favorites_enabled"] is True
    assert review.json()["photos"][0]["folder_id"]
    assert review.json()["photos"][0]["selected"] is False
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection").status_code == 201
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/favorite").status_code == 201
    review = client.get(f"/gallery/{gallery_id}/review")
    assert review.json()["photos"][0]["selected"] is True
    assert review.json()["photos"][0]["favorited"] is True
    comment = client.post(
        f"/gallery/{gallery_id}/photos/{photo_id}/comments", json={"body": "Prefiro esta."}
    )
    assert comment.status_code == 201
    assert client.get(f"/gallery/{gallery_id}/comments").json()["comments"][0]["body"] == "Prefiro esta."
    assert client.delete(f"/gallery/{gallery_id}/photos/{photo_id}/selection").status_code == 204
    assert client.delete(f"/gallery/{gallery_id}/photos/{photo_id}/favorite").status_code == 204
    assert client.delete(f"/gallery/{gallery_id}/comments/{comment.json()['id']}").status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(AuditEvent).where(AuditEvent.event == "photo_comment.removed_by_client"))


def test_expired_selection_and_foreign_client_interactions_are_denied(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente", phone_e164="+5511555555555")
        outsider = Client(full_name="Outro cliente", phone_e164="+5511444444444")
        db.add_all([owner, outsider])
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner, expires=True)
    authenticate_client(client, owner.phone_e164)
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection").status_code == 403
    client.cookies.clear()
    authenticate_client(client, outsider.phone_e164)
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/favorite").status_code == 403


def test_expired_gallery_rejects_checkout_of_existing_selection(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Expirada", phone_e164="+5511555555566")
        db.add(owner)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner, expires=True)
    with SessionLocal() as db:
        parent_id = db.get(DerivedGallery, gallery_id).parent_gallery_id
        db.add_all([
            PhotoSelection(derived_gallery_id=gallery_id, photo_asset_id=photo_id, client_id=owner.id),
            PriceRule(parent_gallery_id=parent_id, minimum_quantity=1, maximum_quantity=None, unit_price_cents=500),
        ])
        db.commit()
    authenticate_client(client, owner.phone_e164)
    response = client.post(f"/gallery/{gallery_id}/checkout", json={"idempotency_key": "expired-checkout-key-0001"})
    assert response.status_code == 403


def test_private_photo_state_is_new_viewed_then_purchased(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente", phone_e164="+5511555555555")
        db.add(owner)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner)
    authenticate_client(client, owner.phone_e164)
    assert client.get(f"/gallery/{gallery_id}/review").json()["photos"][0]["purchase_state"] == "nova"
    with SessionLocal() as db:
        db.add(PhotoView(derived_gallery_id=gallery_id, client_id=owner.id, photo_asset_id=photo_id))
        db.commit()
    assert client.get(f"/gallery/{gallery_id}/review").json()["photos"][0]["purchase_state"] == "visualizada mas não comprada"
    with SessionLocal() as db:
        order = SaleOrder(derived_gallery_id=gallery_id, client_id=owner.id, payment_status="confirmed", total_cents=100, confirmed_at=now())
        db.add(order)
        db.flush()
        db.add(SaleOrderItem(sale_order_id=order.id, photo_asset_id=photo_id, filename_snapshot="IMG_0001.jpg", unit_price_cents=100))
        db.commit()
    assert client.get(f"/gallery/{gallery_id}/review").json()["photos"][0]["purchase_state"] == "já comprada"
    denied = client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection")
    assert denied.status_code == 409
    assert denied.json()["detail"] == "Foto indisponível para seleção."


def test_phone_change_preserves_gallery_owner_and_retires_old_phone(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente", phone_e164="+5511555555555")
        db.add(owner)
        db.commit()
    gallery_id, _ = create_gallery_for_client(client, owner)
    authenticate_admin(client)
    challenge = client.post("/auth/client/challenge", json={"full_name": owner.full_name, "phone": "+5511666666666"}).json()["challenge_id"]
    with SessionLocal() as db:
        db.get(AuthChallenge, UUID(challenge)).secret_hash = token_hash("123456")
        db.commit()
    assert client.post(f"/admin/clients/{owner.id}/phone", json={"phone_e164": "+5511666666666", "challenge_id": challenge, "code": "123456"}).status_code == 200
    client.cookies.clear()
    authenticate_client(client, "+5511666666666")
    assert client.get(f"/gallery/{gallery_id}/review").status_code == 200
    client.cookies.clear()
    old = client.post("/auth/client/challenge", json={"full_name": owner.full_name, "phone": owner.phone_e164}).json()["challenge_id"]
    with SessionLocal() as db:
        db.get(AuthChallenge, UUID(old)).secret_hash = token_hash("123456")
        db.commit()
    denied = client.post(
        "/auth/client/verify", json={"challenge_id": old, "code": "123456"}
    )
    assert denied.status_code == 403
    assert "link compartilhado" in denied.json()["detail"]


def test_unlisted_source_link_registers_client_without_exposing_photos(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente", phone_e164="+5511555555555")
        parent = ParentGallery(
            name="Evento coletivo", access_mode="collective_protected"
        )
        db.add_all([owner, parent])
        db.flush()
        _, access_token = issue_gallery_capability(
            db, parent_gallery_id=parent.id, scope="public_gallery"
        )
        db.commit()
    challenge = client.post(
        "/auth/client/challenge",
        json={
            "full_name": owner.full_name,
            "phone": owner.phone_e164,
            "access_token": access_token,
        },
    ).json()["challenge_id"]
    with SessionLocal() as db:
        db.get(AuthChallenge, UUID(challenge)).secret_hash = token_hash("123456")
        db.commit()
    assert client.post("/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}).json() == {"destination": "/library?access=pending"}
    with SessionLocal() as db:
        assert db.scalar(select(ParentGalleryRegistration).where(ParentGalleryRegistration.parent_gallery_id == parent.id, ParentGalleryRegistration.client_id == owner.id)).status == "pending"


def test_cloned_gallery_is_isolated_and_individually_blocked(client: TestClient):
    with SessionLocal() as db:
        mother = Client(full_name="Mãe", phone_e164="+5511555555555")
        father = Client(full_name="Pai", phone_e164="+5511444444444")
        db.add_all([mother, father])
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, mother)
    authenticate_admin(client)
    cloned = client.post(f"/admin/derived-galleries/{gallery_id}/clone", json={"client_id": str(father.id), "idempotency_key": "father-clone-key-0001"})
    assert cloned.status_code == 201
    father_gallery_id = cloned.json()["id"]
    assert client.post(f"/admin/derived-galleries/{gallery_id}/clone", json={"client_id": str(father.id), "idempotency_key": "father-clone-key-0001"}).json()["id"] == father_gallery_id
    client.cookies.clear()
    authenticate_client(client, father.phone_e164)
    assert client.post(f"/gallery/{father_gallery_id}/photos/{photo_id}/selection").status_code == 201
    client.cookies.clear()
    authenticate_client(client, mother.phone_e164)
    assert client.get(f"/gallery/{gallery_id}/review").json()["photos"][0]["selected"] is False
    client.cookies.clear()
    authenticate_admin(client)
    selection = client.get(f"/admin/derived-galleries/{father_gallery_id}/selection")
    assert selection.status_code == 200
    assert selection.json()["selection_count"] == 1
    assert selection.json()["photos"][0]["filename"] == "IMG_0001.jpg"
    exported = client.get(f"/admin/derived-galleries/{father_gallery_id}/selection/export.txt")
    assert exported.status_code == 200
    assert "IMG_0001.jpg" in exported.text
    assert client.get(f"/admin/derived-galleries/{father_gallery_id}/selection/export.csv").headers["content-type"].startswith("text/csv")
    overview = client.get("/admin/parent-galleries/overview?query=Evento")
    assert overview.status_code == 200
    assert overview.json()["parent_galleries"][0]["private_gallery_count"] == 2
    assert client.patch(f"/admin/derived-galleries/{father_gallery_id}", json={"access_enabled": False}).status_code == 200
    client.cookies.clear()
    authenticate_client(client, father.phone_e164)
    assert client.get(f"/gallery/{father_gallery_id}/review").status_code == 403
    client.cookies.clear()
    authenticate_client(client, mother.phone_e164)
    assert client.get(f"/gallery/{gallery_id}/review").status_code == 200


def test_admin_gallery_list_and_renewal_are_backend_driven(client: TestClient):
    with SessionLocal() as db:
        person = Client(full_name="Cliente", phone_e164="+5511333333333")
        db.add(person)
        db.commit()
    gallery_id, _ = create_gallery_for_client(client, person, expires=True)
    authenticate_admin(client)
    frozen = client.get("/admin/derived-galleries?tab=frozen&query=Cliente")
    assert frozen.status_code == 200
    assert frozen.json()["total"] == 1
    listed_gallery = frozen.json()["galleries"][0]
    assert listed_gallery["client_count"] == 1
    assert listed_gallery["responsible_count"] == listed_gallery["client_count"]
    detail = client.get(f"/admin/derived-galleries/{gallery_id}")
    assert detail.status_code == 200
    assert detail.json()["client"] == detail.json()["responsible"]
    assert detail.json()["client"]["name"] == "Cliente"
    assert detail.json()["link"] is None
    renewed = client.post(f"/admin/derived-galleries/{gallery_id}/renew", json={"selection_expires_at": (now() + timedelta(days=2)).isoformat()})
    assert renewed.status_code == 200
    assert client.get("/admin/derived-galleries?tab=active").json()["total"] == 1


def test_admin_statistics_filter_lists_exports_and_revenue(client: TestClient):
    with SessionLocal() as db:
        first_client = Client(full_name="Primeiro cliente", phone_e164="+5511333333333")
        second_client = Client(full_name="Segundo cliente", phone_e164="+5511222222222")
        parent = ParentGallery(name="Evento", event_name="Festa")
        db.add_all([first_client, second_client, parent])
        db.flush()
        folder = PhotoFolder(
            parent_gallery_id=parent.id, name="Importadas", status="released", released_at=now()
        )
        db.add(folder)
        db.flush()
        bought = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="comprada.jpg",
            storage_key="event/comprada.jpg",
        )
        selected = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="selecionada.jpg",
            storage_key="event/selecionada.jpg",
        )
        other = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="outra.jpg",
            storage_key="event/outra.jpg",
        )
        first_gallery = DerivedGallery(
            parent_gallery_id=parent.id, client_id=first_client.id, name="Primeira"
        )
        second_gallery = DerivedGallery(
            parent_gallery_id=parent.id, client_id=second_client.id, name="Segunda"
        )
        db.add_all([bought, selected, other, first_gallery, second_gallery])
        db.flush()
        db.add_all(
            [
                DerivedGalleryPhoto(derived_gallery_id=first_gallery.id, photo_asset_id=bought.id),
                DerivedGalleryPhoto(derived_gallery_id=first_gallery.id, photo_asset_id=selected.id),
                DerivedGalleryPhoto(derived_gallery_id=second_gallery.id, photo_asset_id=other.id),
                PhotoSelection(
                    derived_gallery_id=first_gallery.id,
                    photo_asset_id=selected.id,
                    client_id=first_client.id,
                ),
                PhotoSelection(
                    derived_gallery_id=second_gallery.id,
                    photo_asset_id=other.id,
                    client_id=second_client.id,
                ),
            ]
        )
        first_order = SaleOrder(
            derived_gallery_id=first_gallery.id,
            client_id=first_client.id,
            payment_status="confirmed",
            total_cents=1_250,
            confirmed_at=now(),
        )
        second_order = SaleOrder(
            derived_gallery_id=second_gallery.id,
            client_id=second_client.id,
            payment_status="confirmed",
            total_cents=800,
            confirmed_at=now(),
        )
        db.add_all([first_order, second_order])
        db.flush()
        db.add_all(
            [
                SaleOrderItem(
                    sale_order_id=first_order.id,
                    photo_asset_id=bought.id,
                    filename_snapshot="comprada.jpg",
                    unit_price_cents=1_250,
                ),
                SaleOrderItem(
                    sale_order_id=second_order.id,
                    photo_asset_id=other.id,
                    filename_snapshot="outra.jpg",
                    unit_price_cents=800,
                ),
            ]
        )
        db.commit()
    assert client.get("/admin/statistics").status_code == 403
    authenticate_admin(client)
    filters = client.get("/admin/statistics/filters")
    assert filters.status_code == 200
    assert filters.json()["clients"] == [
        {"id": str(first_client.id), "name": "Primeiro cliente"},
        {"id": str(second_client.id), "name": "Segundo cliente"},
    ]
    response = client.get(f"/admin/statistics?client_id={first_client.id}")
    assert response.status_code == 200
    assert response.json()["purchased_count"] == 1
    assert response.json()["selected_not_purchased_count"] == 1
    assert response.json()["revenue_cents"] == 1_250
    assert response.json()["selected_not_purchased_photos"] == [
        {"id": str(selected.id), "filename": "selecionada.jpg"}
    ]
    exported = client.get(f"/admin/statistics/selected-not-purchased.txt?client_id={first_client.id}")
    assert exported.headers["content-type"].startswith("text/plain")
    assert exported.text == f"{selected.id}\tselecionada.jpg\n"
    assert "Primeiro cliente" not in exported.text
    purchased_export = client.get(f"/admin/statistics/purchased.txt?client_id={first_client.id}")
    assert purchased_export.text == f"{bought.id}\tcomprada.jpg\n"


def test_admin_manages_preparing_folders_without_storage_urls(client: TestClient) -> None:
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Festa escolar"}).json()["id"])

    created = client.post(
        f"/admin/parent-galleries/{parent_id}/folders", json={"name": "Entrega inicial"}
    )
    assert created.status_code == 201
    folder_id = UUID(created.json()["id"])
    assert created.json() == {"id": str(folder_id), "status": "preparing", "position": 0}

    listing = client.get(f"/admin/parent-galleries/{parent_id}/folders")
    assert listing.status_code == 200
    assert listing.json() == {
        "total": 1,
        "folders": [
            {
                "id": str(folder_id),
                "name": "Entrega inicial",
                "status": "preparing",
                    "position": 0,
                    "photo_count": 0,
                    "preview_url": None,
                    "released_at": None,
            }
        ],
    }
    assert "storage_key" not in listing.text

    renamed = client.patch(f"/admin/photo-folders/{folder_id}", json={"name": "Dia da apresentação"})
    assert renamed.status_code == 200
    assert renamed.json() == {"id": str(folder_id), "name": "Dia da apresentação"}

    with SessionLocal() as db:
        db.get(PhotoFolder, folder_id).status = "released"  # type: ignore[union-attr]
        db.commit()
    locked = client.patch(f"/admin/photo-folders/{folder_id}", json={"name": "Não pode"})
    assert locked.status_code == 409


def test_blocked_parent_gallery_rejects_new_folder_and_photo(client: TestClient) -> None:
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento bloqueado"}).json()["id"])
    client.patch(f"/admin/parent-galleries/{parent_id}/settings", json={"active": False})
    rejected_folder = client.post(
        f"/admin/parent-galleries/{parent_id}/folders", json={"name": "Nova rodada"}
    )
    assert rejected_folder.status_code == 409
    assert rejected_folder.json()["detail"] == "A galeria está bloqueada para novas pastas."

    with SessionLocal() as db:
        folder = PhotoFolder(parent_gallery_id=parent_id, name="Rodada anterior")
        db.add(folder)
        db.commit()
        folder_id = folder.id
    rejected_photo = client.post(
        f"/admin/photo-folders/{folder_id}/photos",
        json={"filename": "BLOQUEADA.jpg", "storage_key": "blocked/BLOQUEADA.jpg"},
    )
    assert rejected_photo.status_code == 409
    assert rejected_photo.json()["detail"] == "A galeria está bloqueada para novas fotos."


def test_folder_upload_accepts_only_preparing_jpeg_and_reports_file_state(
    client: TestClient, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Formatura"}).json()["id"])
    folder_id = UUID(
        client.post(f"/admin/parent-galleries/{parent_id}/folders", json={"name": "Lote 1"}).json()["id"]
    )
    photo_id = UUID(
        client.post(
            f"/admin/photo-folders/{folder_id}/photos",
            json={"filename": "IMG_001.jpg", "storage_key": "formatura/lote-1/IMG_001.jpg"},
        ).json()["id"]
    )
    rejected = client.put(
        f"/admin/photo-assets/{photo_id}/source", content=b"not-a-jpeg", headers={"content-type": "image/jpeg"}
    )
    assert rejected.status_code == 422

    image = BytesIO()
    Image.new("RGB", (16, 16), color=(10, 20, 30)).save(image, format="JPEG")
    uploaded = client.put(
        f"/admin/photo-assets/{photo_id}/source",
        content=image.getvalue(),
        headers={"content-type": "image/jpeg"},
    )
    assert uploaded.status_code == 202
    listing = client.get(f"/admin/photo-folders/{folder_id}/photos")
    assert listing.json()["photos"] == [
        {
            "id": str(photo_id),
            "name": "IMG_001.jpg",
            "preview_url": None,
            "status": "queued",
            "error": None,
            "can_delete": True,
            "is_cover": False,
        }
    ]
    assert "storage_key" not in listing.text

    with SessionLocal() as db:
        db.get(PhotoFolder, folder_id).status = "released"  # type: ignore[union-attr]
        db.commit()
    assert client.post(
        f"/admin/photo-folders/{folder_id}/photos",
        json={"filename": "IMG_002.jpg", "storage_key": "formatura/lote-1/IMG_002.jpg"},
    ).status_code == 409
    assert client.put(
        f"/admin/photo-assets/{photo_id}/source",
        content=image.getvalue(),
        headers={"content-type": "image/jpeg"},
    ).status_code == 409


def test_folder_release_is_idempotent_and_only_exposes_authorized_destination(client: TestClient) -> None:
    owner = Client(full_name="Dona da galeria", phone_e164="+5511999998888")
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento público")
        db.add_all([owner, parent])
        db.flush()
        private_gallery = DerivedGallery(
            parent_gallery_id=parent.id, client_id=owner.id, name="Fotos da família"
        )
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Rodada 1")
        db.add_all([private_gallery, folder])
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="FILHO_001.jpg",
            storage_key="event/round-1/FILHO_001.jpg",
        )
        db.add(photo)
        db.commit()
        gallery_id, folder_id, photo_id = private_gallery.id, folder.id, photo.id

    authenticate_client(client, "+5511999998888")
    assert client.get(f"/gallery/{gallery_id}/photos").json() == {"photos": []}
    client.cookies.clear()
    authenticate_admin(client)
    first = client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": [str(gallery_id)]}
    )
    assert first.status_code == 200
    assert first.json()["new_gallery_photo_links"] == 1
    second = client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": [str(gallery_id)]}
    )
    assert second.status_code == 200
    assert second.json()["new_gallery_photo_links"] == 0

    client.cookies.clear()
    authenticate_client(client, "+5511999998888")
    visible = client.get(f"/gallery/{gallery_id}/photos")
    assert visible.status_code == 200
    assert visible.json()["photos"] == [
        {"id": str(photo_id), "name": "FILHO_001.jpg", "preview_url": f"/gallery/{gallery_id}/photos/{photo_id}/preview"}
    ]
    assert client.get(f"/gallery/{gallery_id}/folders").json() == {
        "total": 1,
        "folders": [{"id": str(folder_id), "name": "Rodada 1", "position": 0, "photo_count": 1}],
    }
    expected_private = [{
        "id": str(gallery_id),
        "name": "Fotos da família",
        "message": "",
        "selection_expires_at": None,
        "gallery_status": "active",
        "origin_removed": False,
        "origin": {
            "id": str(parent.id),
            "name": "Evento público",
            "available": False,
            "browse_url": None,
        },
        "folders": [{"id": str(folder_id), "name": "Rodada 1"}],
    }]
    library = client.get("/library").json()
    assert library["public_galleries"] == []
    assert library["private_galleries"] == expected_private
    assert library["galleries"] == expected_private


def test_synthetic_gallery_flow_keeps_the_second_folder_administrative(client: TestClient) -> None:
    """Fluxo de aceite: uma rodada liberada não torna a próxima visível."""
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento de teste"}).json()["id"])
    first_folder_id = UUID(
        client.post(f"/admin/parent-galleries/{parent_id}/folders", json={"name": "Rodada 1"}).json()["id"]
    )
    second_folder_id = UUID(
        client.post(f"/admin/parent-galleries/{parent_id}/folders", json={"name": "Rodada 2"}).json()["id"]
    )
    client_id = UUID(
        client.post(
            "/admin/clients", json={"full_name": "Cliente sintética", "phone_e164": "+5511999991234"}
        ).json()["id"]
    )
    photo_id = UUID(
        client.post(
            f"/admin/photo-folders/{first_folder_id}/photos",
            json={"filename": "TESTE_001.jpg", "storage_key": "synthetic/round-1/TESTE_001.jpg"},
        ).json()["id"]
    )
    preparing_photo_id = UUID(
        client.post(
            f"/admin/photo-folders/{second_folder_id}/photos",
            json={"filename": "AINDA_NAO_LIBERADA.jpg", "storage_key": "synthetic/round-2/AINDA_NAO_LIBERADA.jpg"},
        ).json()["id"]
    )
    released = client.post(
        f"/admin/photo-folders/{first_folder_id}/release", json={"gallery_ids": []}
    )
    assert released.status_code == 200, released.json()
    derived_gallery_id = UUID(
        client.post(
            "/admin/derived-galleries",
            json={
                "parent_gallery_id": str(parent_id),
                "client_id": str(client_id),
                "name": "Histórico da cliente sintética",
                "photo_ids": [str(photo_id)],
            },
        ).json()["id"]
    )
    folders = client.get(f"/admin/parent-galleries/{parent_id}/folders").json()["folders"]
    assert {key: value for key, value in folders[0].items() if key != "released_at"} == {
        "id": str(first_folder_id),
        "name": "Rodada 1",
        "status": "released",
        "position": 0,
        "photo_count": 1,
        "preview_url": None,
    }
    assert folders[0]["released_at"] is not None
    assert folders[1:] == [
        {
            "id": str(second_folder_id),
            "name": "Rodada 2",
            "status": "preparing",
            "position": 1,
            "photo_count": 1,
            "preview_url": None,
            "released_at": None,
        },
    ]

    with SessionLocal() as db:
        db.add(DerivedGalleryPhoto(derived_gallery_id=derived_gallery_id, photo_asset_id=preparing_photo_id))
        db.add(MediaDerivative(photo_asset_id=photo_id, variant="client_preview", relative_path=f"{photo_id}/preview.jpg", status="ready"))
        db.commit()
    assert client.put(f"/admin/parent-galleries/{parent_id}/cover", json={"photo_id": str(photo_id)}).status_code == 200

    client.cookies.clear()
    authenticate_client(client, "+5511999991234")
    assert client.get(f"/gallery/{derived_gallery_id}/photos").json()["photos"] == [
        {
            "id": str(photo_id),
            "name": "TESTE_001.jpg",
            "preview_url": f"/gallery/{derived_gallery_id}/photos/{photo_id}/preview",
        }
    ]
    assert client.get(f"/gallery/{derived_gallery_id}/folders").json()["folders"] == [
        {"id": str(first_folder_id), "name": "Rodada 1", "position": 0, "photo_count": 1}
    ]
    review = client.get(f"/gallery/{derived_gallery_id}/review")
    assert review.status_code == 200
    assert review.json()["gallery"]["cover_preview_url"] == f"/gallery/{derived_gallery_id}/photos/{photo_id}/preview"
    assert [photo["id"] for photo in review.json()["photos"]] == [str(photo_id)]


def test_admin_empty_private_request_keeps_only_public_client_link(client: TestClient) -> None:
    authenticate_admin(client)
    client_id = UUID(client.post("/admin/clients", json={"full_name": "Responsável", "phone_e164": "+5511999997777"}).json()["id"])
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento"}).json()["id"])
    created = client.post("/admin/derived-galleries", json={
        "parent_gallery_id": str(parent_id), "client_id": str(client_id), "name": "Histórico da família", "photo_ids": []
    })
    assert created.status_code == 201
    assert created.json()["private_gallery_id"] is None
    with SessionLocal() as db:
        assert db.scalar(select(DerivedGallery)) is None
        registration = db.scalar(select(ParentGalleryRegistration))
        assert registration.client_id == client_id
        assert registration.status == "active"


def test_admin_deletes_private_gallery_without_deleting_public_photo(client: TestClient) -> None:
    authenticate_admin(client)
    owner_id = UUID(client.post("/admin/clients", json={"full_name": "Responsável", "phone_e164": "+5511999996666"}).json()["id"])
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento seguro"}).json()["id"])
    empty_folder_id = UUID(client.post(f"/admin/parent-galleries/{parent_id}/folders", json={"name": "Vazia"}).json()["id"])
    assert client.delete(f"/admin/photo-folders/{empty_folder_id}").status_code == 204

    folder_id, photo_id = create_folder_photo(
        client, parent_id, storage_key="event/preservada.jpg"
    )
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}
    ).status_code == 200
    gallery_id = UUID(client.post("/admin/derived-galleries", json={"parent_gallery_id": str(parent_id), "client_id": str(owner_id), "name": "Sem histórico", "photo_ids": [str(photo_id)]}).json()["id"])
    assert client.delete(f"/admin/derived-galleries/{gallery_id}").status_code == 204

    protected_gallery_id = UUID(client.post("/admin/derived-galleries", json={"parent_gallery_id": str(parent_id), "client_id": str(owner_id), "name": "Com histórico", "photo_ids": [str(photo_id)]}).json()["id"])
    assert client.delete(f"/admin/derived-galleries/{protected_gallery_id}").status_code == 204
    with SessionLocal() as db:
        assert db.get(PhotoAsset, photo_id) is not None


def test_operational_folder_photos_support_cover_and_safe_deletion(client: TestClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Festa de teste"}).json()["id"])
    folder_id, photo_id = create_folder_photo(
        client, parent_id, filename="FOTO_001.jpg", storage_key="festa/FOTO_001.jpg"
    )
    source = tmp_path / "source" / "festa" / "FOTO_001.jpg"
    preview = tmp_path / "derivatives" / str(photo_id) / "client_preview.jpg"
    source.parent.mkdir(parents=True)
    preview.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic-jpeg")
    preview.write_bytes(b"watermarked-preview")
    with SessionLocal() as db:
        db.add_all(
            [
                MediaJob(photo_asset_id=photo_id, status="completed"),
                MediaDerivative(
                    photo_asset_id=photo_id,
                    variant="client_preview",
                    relative_path=f"{photo_id}/client_preview.jpg",
                    status="ready",
                ),
            ]
        )
        db.commit()

    listing = client.get(f"/admin/photo-folders/{folder_id}/photos")
    assert listing.status_code == 200
    assert listing.json()["photos"][0] == {
        "id": str(photo_id),
        "name": "FOTO_001.jpg",
        "preview_url": f"/admin/photo-assets/{photo_id}/watermarked-preview",
        "status": "completed",
        "error": None,
        "can_delete": True,
        "is_cover": False,
    }
    assert client.put(
        f"/admin/parent-galleries/{parent_id}/cover", json={"photo_id": str(photo_id)}
    ).status_code == 200
    summary = client.get(f"/admin/parent-galleries/{parent_id}/summary").json()
    assert summary["cover_preview_url"] == f"/admin/photo-assets/{photo_id}/watermarked-preview"

    assert client.delete(f"/admin/photo-folders/{folder_id}/photos/{photo_id}").status_code == 204
    assert not source.exists()
    assert not preview.exists()
    assert client.get(f"/admin/parent-galleries/{parent_id}/summary").json()["cover_preview_url"] is None


def test_photo_deletion_rejects_other_folder_and_confirmed_purchase(client: TestClient) -> None:
    authenticate_admin(client)
    client_id = UUID(
        client.post("/admin/clients", json={"full_name": "Ana", "phone_e164": "+5511999999911"}).json()["id"]
    )
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento"}).json()["id"])
    first_folder, first_photo = create_folder_photo(client, parent_id, storage_key="evento/primeira.jpg")
    second_folder, second_photo = create_folder_photo(
        client, parent_id, folder_name="Segunda", storage_key="evento/segunda.jpg"
    )
    assert client.post(
        f"/admin/photo-folders/{first_folder}/release", json={"gallery_ids": []}
    ).status_code == 200
    gallery_id = UUID(
        client.post(
            "/admin/derived-galleries",
            json={"parent_gallery_id": str(parent_id), "client_id": str(client_id), "name": "Ana", "photo_ids": [str(first_photo)]},
        ).json()["id"]
    )
    with SessionLocal() as db:
        order = SaleOrder(
            derived_gallery_id=gallery_id,
            client_id=client_id,
            payment_status="confirmed",
            total_cents=1000,
            confirmed_at=now(),
        )
        db.add(order)
        db.flush()
        db.add(
            SaleOrderItem(
                sale_order_id=order.id,
                photo_asset_id=first_photo,
                filename_snapshot="primeira.jpg",
                unit_price_cents=1000,
            )
        )
        db.commit()

    assert client.delete(f"/admin/photo-folders/{second_folder}/photos/{first_photo}").status_code == 404
    blocked = client.delete(f"/admin/photo-folders/{first_folder}/photos/{first_photo}")
    assert blocked.status_code == 409
    assert "histórico confirmado" in blocked.json()["detail"]
    assert client.delete(f"/admin/photo-folders/{second_folder}/photos/{second_photo}").status_code == 204


def test_photo_bulk_deletion_reports_confirmed_items(client: TestClient) -> None:
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento em lote"}).json()["id"])
    folder_id, first_photo = create_folder_photo(client, parent_id, storage_key="evento/lote-1.jpg")
    second_photo = UUID(client.post(f"/admin/photo-folders/{folder_id}/photos", json={"filename": "lote-2.jpg", "storage_key": "evento/lote-2.jpg"}).json()["id"])
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}
    ).status_code == 200
    client_id = UUID(client.post("/admin/clients", json={"full_name": "Cliente Lote", "phone_e164": "+5511999999988"}).json()["id"])
    gallery_id = UUID(client.post("/admin/derived-galleries", json={"parent_gallery_id": str(parent_id), "client_id": str(client_id), "name": "Lote", "photo_ids": [str(second_photo)]}).json()["id"])
    with SessionLocal() as db:
        order = SaleOrder(derived_gallery_id=gallery_id, client_id=client_id, payment_status="confirmed", total_cents=1000, confirmed_at=now())
        db.add(order)
        db.flush()
        db.add(SaleOrderItem(sale_order_id=order.id, photo_asset_id=second_photo, filename_snapshot="lote-2.jpg", unit_price_cents=1000))
        db.commit()
    response = client.request("DELETE", f"/admin/photo-folders/{folder_id}/photos", json={"photo_ids": [str(first_photo), str(second_photo)]})
    assert response.status_code == 200
    assert response.json()["deleted_ids"] == [str(first_photo)]
    assert response.json()["blocked_ids"] == [str(second_photo)]


def test_client_binding_is_alphabetical_and_idempotent_for_same_event(client: TestClient) -> None:
    authenticate_admin(client)
    ana_id = UUID(client.post("/admin/clients", json={"full_name": "Ana", "phone_e164": "+5511999999901"}).json()["id"])
    client.post("/admin/clients", json={"full_name": "Zuleica", "phone_e164": "+5511999999902"})
    assert [item["name"] for item in client.get("/admin/clients").json()["clients"]] == ["Ana", "Zuleica"]
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Formatura"}).json()["id"])
    first = client.put(f"/admin/parent-galleries/{parent_id}/clients/{ana_id}")
    second = client.put(f"/admin/parent-galleries/{parent_id}/clients/{ana_id}")
    assert first.status_code == second.status_code == 200
    assert first.json()["registration_id"] == second.json()["registration_id"]
    summary = client.get(f"/admin/parent-galleries/{parent_id}/summary").json()
    assert summary["counts"] == {"folders": 0, "photos": 0, "clients": 1}
    assert summary["clients"] == [
        {
            "client_id": str(ana_id),
            "name": "Ana",
            "phone": "+5511999999901",
            "registration_status": "active",
            "derived_gallery_id": None,
            "available_count": 0,
            "selected_count": 0,
            "purchased_count": 0,
            "gallery_status": "no_selection",
        }
    ]


def test_admin_queues_empty_parent_gallery_deletion(client: TestClient) -> None:
    authenticate_admin(client)
    empty_id = UUID(client.post("/admin/parent-galleries", json={"name": "Rascunho"}).json()["id"])
    response = client.delete(
        f"/admin/parent-galleries/{empty_id}",
        headers={"Idempotency-Key": "delete-empty-parent"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_complete_administrative_gallery_flow_is_contextual_and_idempotent(client: TestClient) -> None:
    """Exercita o ciclo administrativo antes de venda, WhatsApp ou biometria."""
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento completo"}).json()["id"])
    _, cover_photo = create_folder_photo(
        client, parent_id, folder_name="Lote inicial", filename="CAPA.jpg", storage_key="evento/capa.jpg"
    )
    second_folder, removable_photo = create_folder_photo(
        client, parent_id, folder_name="Lote complementar", filename="REMOVER.jpg", storage_key="evento/remover.jpg"
    )
    # A capa só pode ser escolhida quando o derivado protegido está pronto.
    with SessionLocal() as db:
        db.add(MediaJob(photo_asset_id=cover_photo, status="completed"))
        db.add(MediaDerivative(photo_asset_id=cover_photo, variant="client_preview", relative_path=f"{cover_photo}/preview.jpg", status="ready"))
        db.commit()
    assert client.put(f"/admin/parent-galleries/{parent_id}/cover", json={"photo_id": str(cover_photo)}).status_code == 200
    first_folder = client.get(f"/admin/parent-galleries/{parent_id}/folders").json()["folders"][0]["id"]
    assert client.post(
        f"/admin/photo-folders/{first_folder}/release", json={"gallery_ids": []}
    ).status_code == 200

    created = client.post("/admin/clients", json={"full_name": "Cliente Fluxo", "phone_e164": "+5511999994321"})
    assert created.status_code == 201
    client_id = UUID(created.json()["id"])
    assert client.get("/admin/clients?query=99994321").json()["clients"][0]["id"] == str(client_id)
    private_payload = {"parent_gallery_id": str(parent_id), "client_id": str(client_id), "name": "Galeria da cliente", "photo_ids": [str(cover_photo)]}
    first_link = client.post("/admin/derived-galleries", json=private_payload)
    second_link = client.post("/admin/derived-galleries", json=private_payload)
    assert first_link.status_code == second_link.status_code == 201
    assert first_link.json()["id"] == second_link.json()["id"]

    summary = client.get(f"/admin/parent-galleries/{parent_id}/summary")
    assert summary.status_code == 200
    assert summary.json()["counts"] == {"folders": 2, "photos": 2, "clients": 1}
    assert summary.json()["cover_preview_url"] == f"/admin/photo-assets/{cover_photo}/watermarked-preview"
    assert summary.json()["clients"][0]["name"] == "Cliente Fluxo"
    assert client.delete(f"/admin/photo-folders/{second_folder}/photos/{removable_photo}").status_code == 204
    assert client.get(f"/admin/parent-galleries/{parent_id}/summary").json()["counts"]["photos"] == 1
    assert client.get(f"/admin/parent-galleries/{parent_id}/folders").json()["folders"][0]["name"] == "Lote inicial"

    occupied_id = UUID(client.post("/admin/parent-galleries", json={"name": "Com pasta"}).json()["id"])
    create_folder_photo(client, occupied_id, storage_key="ocupada/foto.jpg")
    queued = client.delete(
        f"/admin/parent-galleries/{occupied_id}",
        headers={"Idempotency-Key": "delete-occupied-parent"},
    )
    assert queued.status_code == 202
    assert queued.json()["inventory"]["remove"]["photos"] == 1


def test_pending_checkout_freezes_prices_pix_and_selection(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente PIX", phone_e164="+5511555554321")
        db.add(owner)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner)
    authenticate_client(client, owner.phone_e164)
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection").status_code == 201
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        db.add_all([
            PriceRule(parent_gallery_id=gallery.parent_gallery_id, minimum_quantity=1, maximum_quantity=None, unit_price_cents=700),
            PixCheckoutSettings(parent_gallery_id=gallery.parent_gallery_id, copy_paste="pix-copia-cola", instructions="Confirme com o fotógrafo."),
        ])
        db.commit()
        order = create_pending_checkout(db, gallery=gallery, client=owner, checkout_key="checkout-test-0001")
        db.commit()
        repeated = create_pending_checkout(db, gallery=gallery, client=owner, checkout_key="checkout-test-0001")
        assert repeated.id == order.id
        assert order.total_cents == 700
        assert order.price_rule_snapshot["unit_price_cents"] == 700
        assert order.pix_copy_paste_snapshot == "pix-copia-cola"
        assert order.pix_instructions_snapshot == "Confirme com o fotógrafo."
        assert not db.scalar(select(PhotoSelection).where(PhotoSelection.derived_gallery_id == gallery_id))
        assert db.scalar(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id)).unit_price_cents == 700


def test_checkout_key_is_unique_for_the_same_client_and_gallery(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Concorrência", phone_e164="+5511555554322")
        db.add(owner)
        db.commit()
    gallery_id, _ = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        db.add(SaleOrder(
            derived_gallery_id=gallery_id,
            client_id=owner.id,
            payment_status="pending",
            total_cents=100,
            checkout_key="same-checkout-key-0001",
        ))
        db.commit()
        db.add(SaleOrder(
            derived_gallery_id=gallery_id,
            client_id=owner.id,
            payment_status="pending",
            total_cents=100,
            checkout_key="same-checkout-key-0001",
        ))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_client_cart_and_checkout_are_private(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Carrinho", phone_e164="+5511555554333")
        db.add(owner)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        parent_id = db.get(DerivedGallery, gallery_id).parent_gallery_id
        db.add(PriceRule(parent_gallery_id=parent_id, minimum_quantity=1, maximum_quantity=None, unit_price_cents=500))
        db.commit()
    authenticate_client(client, owner.phone_e164)
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection").status_code == 201
    cart = client.get(f"/gallery/{gallery_id}/cart")
    assert cart.status_code == 200
    assert cart.json()["total_cents"] == 500
    checkout = client.post(f"/gallery/{gallery_id}/checkout", json={"idempotency_key": "client-checkout-0001"})
    assert checkout.status_code == 201
    assert checkout.json()["payment_status"] == "pending"
    assert client.post(f"/gallery/{gallery_id}/checkout", json={"idempotency_key": "client-checkout-0001"}).json()["id"] == checkout.json()["id"]


def test_pending_order_is_private_and_preserves_pix_snapshot(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Pedido", phone_e164="+5511555554344")
        other = Client(full_name="Outra Cliente", phone_e164="+5511555554355")
        db.add_all([owner, other])
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        parent_id = db.get(DerivedGallery, gallery_id).parent_gallery_id
        db.add_all([
            PriceRule(parent_gallery_id=parent_id, minimum_quantity=1, maximum_quantity=None, unit_price_cents=1_200),
            PixCheckoutSettings(parent_gallery_id=parent_id, copy_paste="pix-seguro", qr_code_payload="qr-pix", instructions="Aguarde a confirmação."),
        ])
        db.commit()
    authenticate_client(client, owner.phone_e164)
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection").status_code == 201
    order = client.post(f"/gallery/{gallery_id}/checkout", json={"idempotency_key": "client-order-0001"}).json()
    private_order = client.get(f"/gallery/{gallery_id}/orders/{order['id']}")
    assert private_order.status_code == 200
    assert private_order.json()["pix"]["copy_paste"] == "pix-seguro"
    assert private_order.json()["pix"]["confirmation"] == "A confirmação do pagamento é manual pelo fotógrafo."
    authenticate_client(client, other.phone_e164)
    denied = client.get(f"/gallery/{gallery_id}/orders/{order['id']}")
    assert denied.status_code == 403
    assert "pix-seguro" not in denied.text


def test_client_reports_own_pending_payment_idempotently(client: TestClient, monkeypatch):
    monkeypatch.setenv("WHATSAPP_PHOTOGRAPHER_PHONE_E164", "+5511555554000")
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Comunica", phone_e164="+5511555554388")
        db.add(owner)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        parent_id = db.get(DerivedGallery, gallery_id).parent_gallery_id
        db.add_all([PriceRule(parent_gallery_id=parent_id, minimum_quantity=1, maximum_quantity=None, unit_price_cents=500), PhotoSelection(derived_gallery_id=gallery_id, photo_asset_id=photo_id, client_id=owner.id)])
        db.commit()
    authenticate_client(client, owner.phone_e164)
    order = client.post(f"/gallery/{gallery_id}/checkout", json={"idempotency_key": "communication-order-key-0001"}).json()
    first = client.post(f"/gallery/{gallery_id}/orders/{order['id']}/payment-communications", json={"idempotency_key": "payment-report-key-0001"})
    second = client.post(f"/gallery/{gallery_id}/orders/{order['id']}/payment-communications", json={"idempotency_key": "payment-report-key-0001"})
    third = client.post(f"/gallery/{gallery_id}/orders/{order['id']}/payment-communications", json={"idempotency_key": "payment-report-key-0002"})
    assert first.status_code == second.status_code == third.status_code == 201
    assert first.json()["id"] == second.json()["id"] == third.json()["id"]
    assert first.json()["notification_status"] == "queued"
    with SessionLocal() as db:
        assert db.get(SaleOrder, UUID(order["id"])).payment_status == "pending"
        outboxes = list(db.scalars(select(PaymentNotificationOutbox)))
        assert len(outboxes) == 1
        assert outboxes[0].template_kind == "photographer_reported"
        assert outboxes[0].recipient_phone == "+5511555554000"
    private_status = client.get(f"/gallery/{gallery_id}/payment-communications")
    assert private_status.status_code == 200
    assert private_status.json()["orders"][0]["communication"]["status"] == "pending_review"
    assert "+5511555554000" not in private_status.text


def test_admin_confirms_payment_communication_once(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Decide", phone_e164="+5511555554399")
        db.add(owner)
        db.commit()
    gallery_id, _ = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        order = SaleOrder(derived_gallery_id=gallery_id, client_id=owner.id, payment_status="pending", total_cents=500, client_phone_snapshot="+5511555554001")
        db.add(order)
        db.flush()
        communication = PaymentCommunication(sale_order_id=order.id, client_id=owner.id, idempotency_key="decision-key-0001")
        db.add(communication)
        db.commit()
        communication_id = communication.id
        order_id = order.id
    authenticate_admin(client)
    first = client.post(f"/admin/payment-communications/{communication_id}/decision", json={"decision": "confirmed"})
    second = client.post(f"/admin/payment-communications/{communication_id}/decision", json={"decision": "refused"})
    assert first.json()["status"] == second.json()["status"] == "confirmed"
    with SessionLocal() as db:
        assert db.get(SaleOrder, order_id).payment_status == "confirmed"
        assert db.scalar(select(AuditEvent).where(AuditEvent.event == "payment.communication_confirmed"))
        outboxes = list(db.scalars(select(PaymentNotificationOutbox)))
        assert len(outboxes) == 1
        assert outboxes[0].template_kind == "confirmed"
        assert outboxes[0].recipient_phone == owner.phone_e164


def test_admin_lists_and_refuses_payment_communication_without_confirming_order(client: TestClient, monkeypatch):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Recusa", phone_e164="+5511555554400")
        db.add(owner)
        db.commit()
    gallery_id, _ = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        order = SaleOrder(derived_gallery_id=gallery_id, client_id=owner.id, payment_status="pending", total_cents=500)
        db.add(order)
        db.flush()
        communication = PaymentCommunication(sale_order_id=order.id, client_id=owner.id, idempotency_key="refusal-key-0001")
        db.add(communication)
        db.commit()
        communication_id, order_id = communication.id, order.id
    authenticate_admin(client)
    listed = client.get("/admin/payment-communications")
    assert listed.status_code == 200
    assert listed.json()["communications"][0]["id"] == str(communication_id)
    assert listed.json()["communications"][0]["client_name"] == "Cliente Recusa"
    assert owner.phone_e164 not in listed.text
    assert client.post(f"/admin/payment-communications/{communication_id}/decision", json={"decision": "refused"}).json()["status"] == "refused"
    assert client.post(f"/admin/payment-communications/{communication_id}/decision", json={"decision": "confirmed"}).json()["status"] == "refused"
    with SessionLocal() as db:
        assert db.get(SaleOrder, order_id).payment_status == "cancelled"
        outboxes = list(db.scalars(select(PaymentNotificationOutbox)))
        assert len(outboxes) == 1
        assert outboxes[0].template_kind == "refused"
        outbox_id = outboxes[0].id
        outboxes[0].status = "failed"
        outboxes[0].attempts = 1
        db.commit()
    monkeypatch.setenv("WHATSAPP_MAX_ATTEMPTS", "2")
    assert client.post(f"/admin/payment-notifications/{outbox_id}/retry").json()["status"] == "queued"
    with SessionLocal() as db:
        outbox = db.get(PaymentNotificationOutbox, outbox_id)
        outbox.status = "failed"
        outbox.attempts = 2
        db.commit()
    assert client.post(f"/admin/payment-notifications/{outbox_id}/retry").status_code == 409


def test_admin_payment_templates_are_controlled_and_have_safe_defaults(client: TestClient):
    authenticate_admin(client)
    defaults = client.get("/admin/payment-message-templates")
    assert defaults.status_code == 200
    assert set(defaults.json()["templates"]) == {"confirmed", "refused"}
    assert defaults.json()["allowed_variables"] == ["cliente", "galeria", "pedido"]
    invalid = client.put(
        "/admin/payment-message-templates/confirmed",
        json={"body": "Acesse https://exemplo.invalid/{{pedido}}"},
    )
    assert invalid.status_code == 422
    saved = client.put(
        "/admin/payment-message-templates/confirmed",
        json={"body": "Olá {{cliente}}, o pedido {{pedido}} da {{galeria}} foi confirmado."},
    )
    assert saved.status_code == 200
    assert saved.json()["body"].startswith("Olá {{cliente}}")


def test_payment_communication_contracts_enforce_role_and_gallery_owner(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Autorizada", phone_e164="+5511555554477")
        other = Client(full_name="Cliente Terceira", phone_e164="+5511555554488")
        db.add_all([owner, other])
        db.commit()
    gallery_id, _ = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        order = SaleOrder(derived_gallery_id=gallery_id, client_id=owner.id, payment_status="pending", total_cents=500)
        db.add(order)
        db.commit()
        order_id = order.id

    authenticate_client(client, other.phone_e164)
    denied_status = client.get(f"/gallery/{gallery_id}/payment-communications")
    denied_report = client.post(
        f"/gallery/{gallery_id}/orders/{order_id}/payment-communications",
        json={"idempotency_key": "unauthorized-report-0001"},
    )
    denied_admin = client.get("/admin/payment-communications")
    assert denied_status.status_code == denied_report.status_code == denied_admin.status_code == 403
    assert "Cliente Autorizada" not in denied_status.text + denied_report.text + denied_admin.text


def test_admin_pricing_requires_contiguous_tiers_and_returns_jump_warning(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Preço", phone_e164="+5511555554366")
        db.add(owner)
        db.commit()
    gallery_id, _ = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        parent_id = db.get(DerivedGallery, gallery_id).parent_gallery_id
    authenticate_admin(client)
    invalid = client.put(
        f"/admin/parent-galleries/{parent_id}/pricing",
        json={"tiers": [{"minimum_quantity": 2, "maximum_quantity": None, "unit_price_cents": 500}], "pix": {}},
    )
    assert invalid.status_code == 422
    saved = client.put(
        f"/admin/parent-galleries/{parent_id}/pricing",
        json={
            "tiers": [
                {"minimum_quantity": 1, "maximum_quantity": 10, "unit_price_cents": 700},
                {"minimum_quantity": 11, "maximum_quantity": None, "unit_price_cents": 500},
            ],
            "pix": {"copy_paste": "pix-controlado", "instructions": "Confirme depois do PIX."},
        },
    )
    assert saved.status_code == 200
    assert saved.json()["has_downward_jump"] is True
    inherited = client.get(f"/admin/derived-galleries/{gallery_id}/pricing")
    assert inherited.json()["pix"]["copy_paste"] == "pix-controlado"
    assert inherited.json()["inherited_from_parent_gallery_id"] == str(parent_id)
    assert inherited.json()["editable"] is False
    assert client.put(
        f"/admin/derived-galleries/{gallery_id}/pricing",
        json={
            "tiers": [
                {
                    "minimum_quantity": 1,
                    "maximum_quantity": None,
                    "unit_price_cents": 100,
                }
            ],
            "pix": {},
        },
    ).status_code == 409


def test_private_gallery_inherits_parent_configuration_and_checkout_freezes_terms(
    client: TestClient,
):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Herança", phone_e164="+5511555554367")
        db.add(owner)
        db.commit()
        owner_id = owner.id
    authenticate_admin(client)
    parent_id = UUID(
        client.post(
            "/admin/parent-galleries", json={"name": "Galeria pública herdada"}
        ).json()["id"]
    )
    folder_id, photo_id = create_folder_photo(
        client, parent_id, storage_key="inheritance/photo.jpg"
    )
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}
    ).status_code == 200

    initial = client.put(
        f"/admin/parent-galleries/{parent_id}/sales",
        json={
            "tiers": [
                {
                    "minimum_quantity": 1,
                    "maximum_quantity": None,
                    "unit_price_cents": 700,
                }
            ],
            "pix": {"copy_paste": "pix-a", "instructions": "Instrução A"},
            "sales_message": "Mensagem A",
            "selection_duration_days": 14,
            "favorites_enabled": True,
            "comments_enabled": True,
        },
    )
    assert initial.status_code == 200
    created_at = now()
    created = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(owner_id),
            "name": "Privada herdada",
            "photo_ids": [str(photo_id)],
        },
    )
    assert created.status_code == 201
    gallery_id = UUID(created.json()["id"])
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        first_expiry = gallery.selection_expires_at
        if first_expiry.tzinfo is None:
            first_expiry = first_expiry.replace(tzinfo=UTC)
        assert created_at + timedelta(days=13) < first_expiry
        assert first_expiry < created_at + timedelta(days=15)

    rejected_override = client.patch(
        f"/admin/derived-galleries/{gallery_id}",
        json={"custom_message": "Override proibido", "favorites_enabled": False},
    )
    assert rejected_override.status_code == 422

    client.cookies.clear()
    authenticate_client(client, "+5511555554367")
    review = client.get(f"/gallery/{gallery_id}/review").json()["gallery"]
    assert review["message"] == "Mensagem A"
    assert review["favorites_enabled"] is True
    assert review["comments_enabled"] is True
    assert client.post(
        f"/gallery/{gallery_id}/photos/{photo_id}/selection"
    ).status_code == 201

    client.cookies.clear()
    authenticate_admin(client)
    changed_before_checkout = client.put(
        f"/admin/parent-galleries/{parent_id}/sales",
        json={
            "tiers": [
                {
                    "minimum_quantity": 1,
                    "maximum_quantity": None,
                    "unit_price_cents": 900,
                }
            ],
            "pix": {"copy_paste": "pix-b", "instructions": "Instrução B"},
            "sales_message": "Mensagem B",
            "selection_duration_days": 30,
            "favorites_enabled": False,
            "comments_enabled": False,
        },
    )
    assert changed_before_checkout.status_code == 200
    with SessionLocal() as db:
        persisted_expiry = db.get(DerivedGallery, gallery_id).selection_expires_at
        if persisted_expiry.tzinfo is None:
            persisted_expiry = persisted_expiry.replace(tzinfo=UTC)
        assert persisted_expiry == first_expiry

    client.cookies.clear()
    authenticate_client(client, "+5511555554367")
    review = client.get(f"/gallery/{gallery_id}/review").json()["gallery"]
    assert review["message"] == "Mensagem B"
    assert review["favorites_enabled"] is False
    order = client.post(
        f"/gallery/{gallery_id}/checkout",
        json={"idempotency_key": "inherited-checkout-0001"},
    )
    assert order.status_code == 201
    order_id = order.json()["id"]

    client.cookies.clear()
    authenticate_admin(client)
    assert client.put(
        f"/admin/parent-galleries/{parent_id}/sales",
        json={
            "tiers": [
                {
                    "minimum_quantity": 1,
                    "maximum_quantity": None,
                    "unit_price_cents": 1_100,
                }
            ],
            "pix": {"copy_paste": "pix-c", "instructions": "Instrução C"},
            "sales_message": "Mensagem C",
            "selection_duration_days": 30,
            "favorites_enabled": False,
            "comments_enabled": False,
        },
    ).status_code == 200

    client.cookies.clear()
    authenticate_client(client, "+5511555554367")
    frozen = client.get(f"/gallery/{gallery_id}/orders/{order_id}")
    assert frozen.status_code == 200
    assert frozen.json()["total_cents"] == 900
    assert frozen.json()["sales_message"] == "Mensagem B"
    assert frozen.json()["pix"]["copy_paste"] == "pix-b"
    assert frozen.json()["pix"]["instructions"] == "Instrução B"


def test_admin_sees_pending_order_snapshots_without_confirming_it(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Conferência", phone_e164="+5511555554377")
        db.add(owner)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        db.add_all([
            PriceRule(parent_gallery_id=gallery.parent_gallery_id, minimum_quantity=1, maximum_quantity=None, unit_price_cents=900),
            PixCheckoutSettings(parent_gallery_id=gallery.parent_gallery_id, copy_paste="pix-snapshot", instructions="Confirmação manual."),
            PhotoSelection(derived_gallery_id=gallery_id, photo_asset_id=photo_id, client_id=owner.id),
        ])
        db.commit()
        create_pending_checkout(db, gallery=gallery, client=owner, checkout_key="admin-order-snapshot-0001")
        db.commit()
    authenticate_admin(client)
    response = client.get(f"/admin/derived-galleries/{gallery_id}/orders")
    assert response.status_code == 200
    order = response.json()["orders"][0]
    assert order["payment_status"] == "pending"
    assert order["total_cents"] == 900
    assert order["price_rule"]["unit_price_cents"] == 900
    assert order["pix"]["copy_paste"] == "pix-snapshot"
    assert order["items"] == [{"photo_id": str(photo_id), "name": "IMG_0001.jpg", "unit_price_cents": 900}]
    with SessionLocal() as db:
        assert db.scalar(select(SaleOrder).where(SaleOrder.derived_gallery_id == gallery_id)).payment_status == "pending"
