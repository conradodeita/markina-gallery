from datetime import UTC, timedelta
from io import BytesIO
from time import perf_counter
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    AuditEvent,
    AuthChallenge,
    AuthSession,
    Base,
    BrandingSettings,
    Client,
    ClientPhone,
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    GlobalPixSettings,
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
from app.client_commerce import client_carts_by_gallery_payload
from app.gallery_access import issue_gallery_capability
from app.global_pix import normalize_configuration
from app.main import app
from app.media import generate_derivatives
from app.private_derivation import ensure_private_photo_reference

VALID_PIX_A = "0002015204000053039865802BR5907MARKINA6009SAO PAULO6304BE17"
VALID_PIX_B = "0002015204000053039865802BR5908OUTRAFOT6009SAO PAULO6304FC65"


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
    set_test_global_pix()
    with TestClient(app) as test_client:
        yield test_client


def set_test_global_pix(copy_paste=VALID_PIX_A, instructions=None):
    """Configuração sintética explícita para os fluxos comerciais desta suíte."""
    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == "foto@markina.test"))
        if not admin:
            admin = AdminUser(email="foto@markina.test", email_verified=True,
                              password_hash=password_hasher.hash("senha-segura"),
                              totp_secret=pyotp.random_base32())
            db.add(admin)
            db.flush()
        settings = db.scalar(select(GlobalPixSettings))
        if not settings:
            settings = GlobalPixSettings(admin_user_id=admin.id, version=1)
            db.add(settings)
        for key, value in normalize_configuration({"copy_paste": copy_paste, "instructions": instructions}).items():
            setattr(settings, key, value)
        db.commit()


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


def test_admin_manages_and_simulates_versioned_progressive_pricing_presets(
    client: TestClient,
) -> None:
    authenticate_admin(client)
    payload = {
        "code": "01",
        "name": "Tabela escolar",
        "tiers": [
            {"minimum_quantity": 1, "maximum_quantity": 30, "unit_price_cents": 700},
            {"minimum_quantity": 31, "maximum_quantity": None, "unit_price_cents": 600},
        ],
    }

    created = client.post("/admin/pricing-presets", json=payload)
    assert created.status_code == 201
    preset_id = created.json()["id"]
    assert created.json()["label"] == "01 — Tabela escolar"
    assert created.json()["version"] == 1
    assert client.post("/admin/pricing-presets", json=payload).status_code == 409

    simulated = client.get(
        f"/admin/pricing-presets/{preset_id}/quote", params={"quantity": 60}
    )
    assert simulated.status_code == 200
    assert simulated.json()["total_cents"] == 39000
    assert simulated.json()["savings_cents"] == 3000
    assert [item["subtotal_cents"] for item in simulated.json()["parcels"]] == [
        21000,
        18000,
    ]

    payload["name"] = "Tabela escolar revisada"
    payload["tiers"][1]["unit_price_cents"] = 550
    updated = client.put(f"/admin/pricing-presets/{preset_id}", json=payload)
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["label"] == "01 — Tabela escolar revisada"

    invalid = client.put(
        f"/admin/pricing-presets/{preset_id}",
        json={
            **payload,
            "tiers": [
                {
                    "minimum_quantity": 1,
                    "maximum_quantity": 30,
                    "unit_price_cents": 600,
                },
                {
                    "minimum_quantity": 31,
                    "maximum_quantity": None,
                    "unit_price_cents": 700,
                },
            ],
        },
    )
    assert invalid.status_code == 422
    assert client.get("/admin/pricing-presets").json()["presets"][0]["version"] == 2

    deactivated = client.delete(f"/admin/pricing-presets/{preset_id}")
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False
    assert client.get("/admin/pricing-presets").json()["presets"] == []
    listed = client.get(
        "/admin/pricing-presets", params={"include_inactive": "true"}
    )
    assert listed.json()["presets"][0]["version"] == 2

    reactivated = client.post(f"/admin/pricing-presets/{preset_id}/activate")
    assert reactivated.status_code == 200
    assert reactivated.json()["active"] is True
    assert reactivated.json()["version"] == 2
    assert reactivated.json()["tiers"] == listed.json()["presets"][0]["tiers"]
    assert client.get("/admin/pricing-presets").json()["presets"][0]["id"] == preset_id

    idempotent = client.post(f"/admin/pricing-presets/{preset_id}/activate")
    assert idempotent.status_code == 200
    assert idempotent.json()["version"] == 2


def test_public_gallery_materializes_pricing_preset_and_requires_legacy_conversion(
    client: TestClient,
) -> None:
    authenticate_admin(client)
    preset = client.post(
        "/admin/pricing-presets",
        json={
            "code": "02",
            "name": "Tabela eventos",
            "tiers": [
                {
                    "minimum_quantity": 1,
                    "maximum_quantity": 30,
                    "unit_price_cents": 700,
                },
                {
                    "minimum_quantity": 31,
                    "maximum_quantity": None,
                    "unit_price_cents": 600,
                },
            ],
        },
    ).json()
    parent_id = client.post(
        "/admin/parent-galleries", json={"name": "Galeria com snapshot"}
    ).json()["id"]

    saved = client.put(
        f"/admin/parent-galleries/{parent_id}/pricing",
        json={
            "pricing_mode": "progressive",
            "progressive_pricing_preset_id": preset["id"],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["pricing_snapshot"]["preset_version"] == 1
    assert saved.json()["tiers"][1]["unit_price_cents"] == 600

    changed_payload = {
        "code": "02",
        "name": "Tabela eventos revisada",
        "tiers": [
            {"minimum_quantity": 1, "maximum_quantity": 30, "unit_price_cents": 700},
            {"minimum_quantity": 31, "maximum_quantity": None, "unit_price_cents": 500},
        ],
    }
    assert client.put(
        f"/admin/pricing-presets/{preset['id']}", json=changed_payload
    ).status_code == 200
    unchanged = client.get(f"/admin/parent-galleries/{parent_id}/pricing").json()
    assert unchanged["pricing_snapshot"]["preset_version"] == 1
    assert unchanged["tiers"][1]["unit_price_cents"] == 600

    with SessionLocal() as db:
        gallery = db.get(ParentGallery, UUID(parent_id))
        gallery.pricing_mode = "legacy_volume"
        gallery.pricing_review_required = True
        db.commit()
    blocked = client.put(
        f"/admin/parent-galleries/{parent_id}/pricing",
        json={"pricing_mode": "fixed", "fixed_unit_price_cents": 800},
    )
    assert blocked.status_code == 409
    converted = client.put(
        f"/admin/parent-galleries/{parent_id}/pricing",
        json={
            "pricing_mode": "fixed",
            "fixed_unit_price_cents": 800,
            "confirm_legacy_conversion": True,
        },
    )
    assert converted.status_code == 200
    assert converted.json()["pricing_mode"] == "fixed"
    assert converted.json()["pricing_review_required"] is False


def test_gallery_pricing_reads_global_pix_and_rejects_legacy_writes(client):
    authenticate_admin(client)
    parent_id = client.post("/admin/parent-galleries", json={"name": "Galeria PIX"}).json()["id"]
    settings = client.get(f"/admin/parent-galleries/{parent_id}/pricing").json()["pix"]
    assert settings["scope"] == "global"
    assert settings["checkout_available"] is True
    assert settings["qr_png_data_url"].startswith("data:image/png;base64,")
    assert "copy_paste" not in settings
    for legacy in ({}, {"copy_paste": VALID_PIX_A}, {"copy_paste": "invalid"}):
        response = client.put(f"/admin/parent-galleries/{parent_id}/pricing", json={
            "pricing_mode": "fixed", "fixed_unit_price_cents": 700, "pix": legacy,
        })
        assert response.status_code == 422


def test_cart_and_checkout_share_progressive_quote_and_freeze_all_terms(
    client: TestClient,
) -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Progressiva", phone_e164="+5511555554991")
        db.add(owner)
        db.commit()
        owner_id = owner.id
    gallery_id, first_photo_id = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        parent_id = gallery.parent_gallery_id
        first_photo = db.get(PhotoAsset, first_photo_id)
        second_photo = PhotoAsset(
            parent_gallery_id=parent_id,
            folder_id=first_photo.folder_id,
            filename="IMG_0002.jpg",
            storage_key="events/one/img-0002.jpg",
        )
        db.add(second_photo)
        db.flush()
        db.add(DerivedGalleryPhoto(derived_gallery_id=gallery_id, photo_asset_id=second_photo.id))
        db.add_all(
            [
                PhotoSelection(
                    derived_gallery_id=gallery_id,
                    photo_asset_id=first_photo_id,
                    client_id=owner_id,
                ),
                PhotoSelection(
                    derived_gallery_id=gallery_id,
                    photo_asset_id=second_photo.id,
                    client_id=owner_id,
                ),
            ]
        )
        db.commit()

    authenticate_admin(client)
    preset = client.post(
        "/admin/pricing-presets",
        json={
            "code": "03",
            "name": "Progressiva curta",
            "tiers": [
                {"minimum_quantity": 1, "maximum_quantity": 1, "unit_price_cents": 700},
                {"minimum_quantity": 2, "maximum_quantity": None, "unit_price_cents": 600},
            ],
        },
    ).json()
    pix_code = "0002015204000053039865802BR5907MARKINA6009SAO PAULO6304BE17"
    configured = client.put(
        f"/admin/parent-galleries/{parent_id}/pricing",
        json={
            "pricing_mode": "progressive",
            "progressive_pricing_preset_id": preset["id"],
        },
    )
    assert configured.status_code == 200

    client.cookies.clear()
    authenticate_client(client, "+5511555554991")
    cart = client.get(f"/gallery/{gallery_id}/cart")
    assert cart.status_code == 200
    assert cart.json()["total_cents"] == 1300
    assert cart.json()["savings_cents"] == 100
    assert [parcel["subtotal_cents"] for parcel in cart.json()["parcels"]] == [700, 600]

    first_checkout = client.post(
        f"/gallery/{gallery_id}/checkout",
        json={"idempotency_key": "progressive-checkout-0001"},
    )
    repeated_checkout = client.post(
        f"/gallery/{gallery_id}/checkout",
        json={"idempotency_key": "progressive-checkout-0001"},
    )
    assert first_checkout.status_code == repeated_checkout.status_code == 201
    assert first_checkout.json() == repeated_checkout.json()
    order_id = first_checkout.json()["id"]
    frozen = client.get(f"/gallery/{gallery_id}/orders/{order_id}")
    assert frozen.status_code == 200
    assert frozen.json()["price_rule"]["preset_code"] == "03"
    assert frozen.json()["price_rule"]["savings_cents"] == 100
    assert frozen.json()["price_rule"]["total_cents"] == 1300
    assert sorted(item["unit_price_cents"] for item in frozen.json()["items"]) == [600, 700]
    assert frozen.json()["pix"]["copy_paste"] == pix_code
    assert frozen.json()["pix"]["qr_png_data_url"].startswith("data:image/png;base64,")
    assert all(
        item["preview_url"]
        == f"/gallery/{gallery_id}/photos/{item['photo_id']}/preview"
        for item in frozen.json()["items"]
    )


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
        "watermark_opacity": 60,
        "watermark_position": "bottom-center",
        "watermark_shadow": False,
        "watermark_security_lines": True,
    })
    assert response.status_code == 200
    assert response.json()["watermark_text"] == "FOTÓGRAFA • PRÉVIA"
    assert response.json()["watermark_opacity"] == 60
    assert response.json()["watermark_position"] == "bottom-center"
    assert response.json()["watermark_shadow"] is False
    assert response.json()["watermark_security_lines"] is True
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
    ready: bool = False,
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
    if ready:
        mark_photo_ready(photo_id)
    return folder_id, photo_id


def mark_photo_ready(photo_id: UUID) -> None:
    with SessionLocal() as db:
        if not db.scalar(select(MediaJob).where(MediaJob.photo_asset_id == photo_id)):
            db.add(MediaJob(photo_asset_id=photo_id, status="completed", attempts=1))
        if not db.scalar(
            select(MediaDerivative).where(
                MediaDerivative.photo_asset_id == photo_id,
                MediaDerivative.variant == "client_preview",
            )
        ):
            db.add(
                MediaDerivative(
                    photo_asset_id=photo_id,
                    variant="client_preview",
                    relative_path=f"{photo_id}/client_preview.jpg",
                    status="ready",
                    width=1200,
                    height=800,
                )
            )
        db.commit()


def create_gallery_for_client(client: TestClient, person: Client, *, expires=False) -> tuple[UUID, UUID]:
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento"}).json()["id"])
    folder_id, photo_id = create_folder_photo(client, parent_id, ready=True)
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
        "photo_ids": [],
        "create_empty_private": True,
    }
    gallery_id = UUID(client.post("/admin/derived-galleries", json=payload).json()["id"])
    with SessionLocal() as db:
        ensure_private_photo_reference(
            db, gallery_id=gallery_id, photo_id=photo_id, origin="admin"
        )
        db.commit()
    if expires:
        with SessionLocal() as db:
            db.get(DerivedGallery, gallery_id).selection_expires_at = now() - timedelta(
                minutes=1
            )
            db.commit()
    client.cookies.clear()
    return gallery_id, photo_id


def create_empty_private_gallery(
    client: TestClient,
    *,
    parent_id: UUID,
    client_id: UUID,
    name: str,
) -> UUID:
    response = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(client_id),
            "name": name,
            "photo_ids": [],
            "create_empty_private": True,
        },
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def attach_legacy_admin_reference(gallery_id: UUID, photo_id: UUID) -> None:
    """Monta somente fixtures de compatibilidade; a API não cria mais esta origem."""

    with SessionLocal() as db:
        ensure_private_photo_reference(
            db, gallery_id=gallery_id, photo_id=photo_id, origin="admin"
        )
        db.commit()


def test_admin_cannot_create_private_gallery_from_existing_public_photo(client: TestClient):
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
        client, parent_id, storage_key="events/ana/img-0001.jpg", ready=True
    )
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}
    ).status_code == 200
    rejected = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(client_id),
            "name": "Fotos da Cliente",
            "photo_ids": [str(photo_id)],
        },
    )
    assert rejected.status_code == 410
    assert "inclusão administrativa" in rejected.json()["detail"]

    response = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(client_id),
            "name": "Fotos da Cliente",
            "photo_ids": [],
            "create_empty_private": True,
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
        assert reference is None


def test_client_selection_still_creates_private_gallery_automatically(client: TestClient):
    with SessionLocal() as db:
        person = Client(full_name="Cliente", phone_e164="+5511888888888")
        db.add(person)
        db.commit()
        client_id = person.id
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento A"}).json()["id"])
    folder_id, photo_id = create_folder_photo(
        client,
        parent_id,
        filename="IMG_0002.jpg",
        storage_key="events/b/img-0002.jpg",
        ready=True,
    )
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}
    ).status_code == 200
    linked = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(client_id),
            "name": "Fotos privadas",
            "photo_ids": [],
        },
    )
    assert linked.status_code == 201
    assert linked.json()["private_gallery_id"] is None

    client.cookies.clear()
    authenticate_client(client, "+5511888888888")
    selected = client.post(
        f"/public-galleries/{parent_id}/photos/{photo_id}/selection"
    )
    assert selected.status_code == 201
    assert selected.json()["gallery_created"] is True
    assert selected.json()["reference_created"] is True
    assert selected.json()["selection_created"] is True
    with SessionLocal() as db:
        reference = db.scalar(
            select(DerivedGalleryPhoto).where(
                DerivedGalleryPhoto.derived_gallery_id
                == UUID(selected.json()["private_gallery_id"]),
                DerivedGalleryPhoto.photo_asset_id == photo_id,
            )
        )
        assert reference is not None


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
        "journeys": [],
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
            "aggregates": {
                "public_galleries": 0,
                "private_galleries": 0,
                "orders": 0,
            },
            "deletion_eligible": True,
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


def test_admin_link_pre_authorizes_but_marks_first_otp_as_pending(client: TestClient) -> None:
    authenticate_admin(client)
    created = client.post(
        "/admin/clients",
        json={"full_name": "Cliente Primeiro Acesso", "phone_e164": "+5511987654321"},
    )
    parent = client.post("/admin/parent-galleries", json={"name": "Evento autorizado"})
    client_id, parent_id = created.json()["id"], parent.json()["id"]

    linked = client.put(f"/admin/parent-galleries/{parent_id}/clients/{client_id}")
    assert linked.status_code == 200
    assert linked.json()["status"] == "active"
    before_otp = client.get(f"/admin/parent-galleries/{parent_id}/clients").json()["clients"][0]
    assert before_otp["registration_status"] == "active"
    assert before_otp["phone_verified"] is False
    assert before_otp["gallery_status"] == "pending_registration"

    with SessionLocal() as db:
        phone = db.scalar(
            select(ClientPhone).where(
                ClientPhone.client_id == UUID(client_id),
                ClientPhone.active,
            )
        )
        phone.verified_at = now()
        db.commit()

    after_otp = client.get(f"/admin/parent-galleries/{parent_id}/clients").json()["clients"][0]
    assert after_otp["phone_verified"] is True
    assert after_otp["gallery_status"] == "no_selection"


def test_admin_edits_and_deletes_client_without_dependencies(client: TestClient):
    authenticate_admin(client)
    created = client.post(
        "/admin/clients",
        json={"full_name": "Nome incorreto", "phone_e164": "+5511988887766"},
    )
    client_id = created.json()["id"]

    updated = client.patch(
        f"/admin/clients/{client_id}", json={"full_name": "Nome corrigido"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Nome corrigido"
    inventory = client.get(f"/admin/clients/{client_id}/deletion-inventory")
    assert inventory.status_code == 200
    assert inventory.json()["can_delete"] is True
    assert inventory.json()["operational_removable"]["client"] == 1
    assert inventory.json()["operational_removable"]["phone_records"] == 1

    deleted = client.delete(
        f"/admin/clients/{client_id}",
        headers={"Idempotency-Key": "delete-without-dependencies-0001"},
    )
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "completed"
    assert client.get("/admin/clients").json()["clients"] == []
    with SessionLocal() as db:
        assert db.get(Client, UUID(client_id)) is None
        events = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.event.in_(
                        {"client.name_changed", "client.deleted_without_history"}
                    )
                )
            )
        )
        assert {event.event for event in events} == {
            "client.name_changed",
            "client.deleted_without_history",
        }


def test_admin_can_delete_client_with_only_public_gallery_registration(client: TestClient):
    authenticate_admin(client)
    created = client.post(
        "/admin/clients",
        json={"full_name": "Cliente vinculada", "phone_e164": "+5511988887755"},
    )
    client_id = created.json()["id"]
    parent_id = client.post(
        "/admin/parent-galleries", json={"name": "Galeria protegida"}
    ).json()["id"]
    assert client.put(
        f"/admin/parent-galleries/{parent_id}/clients/{client_id}"
    ).status_code == 200

    inventory = client.get(f"/admin/clients/{client_id}/deletion-inventory").json()
    assert inventory["can_delete"] is True
    assert inventory["operational_removable"]["public_gallery_registrations"] == 1
    deleted = client.delete(
        f"/admin/clients/{client_id}",
        headers={"Idempotency-Key": "delete-public-registration-0001"},
    )
    assert deleted.status_code == 200
    assert client.get("/admin/clients").json()["clients"] == []
    assert client.get(f"/admin/parent-galleries/{parent_id}/editor").status_code == 200


def test_admin_client_deletion_reports_concurrent_dependency(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    authenticate_admin(client)
    client_id = client.post(
        "/admin/clients",
        json={"full_name": "Cliente concorrente", "phone_e164": "+5511988887744"},
    ).json()["id"]

    def fail_commit(_session: Session) -> None:
        raise IntegrityError("DELETE client", {}, Exception("foreign key race"))

    monkeypatch.setattr(Session, "commit", fail_commit)
    denied = client.delete(
        f"/admin/clients/{client_id}",
        headers={"Idempotency-Key": "delete-concurrent-dependency-0001"},
    )
    assert denied.status_code == 409
    assert "nova dependência" in denied.json()["detail"]


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
    assert details["capabilities"] == ["cover", "title"]
    assert "folder_display_mode" not in details["settings"]
    assert editor.json()["gallery"]["folder_display_mode"] == "individual"
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
    second_folder_id, _ = create_folder_photo(
        client, second_parent, storage_key="events/second/img-0001.jpg", ready=True
    )
    assert client.post(
        f"/admin/photo-folders/{second_folder_id}/release",
        json={"gallery_ids": []},
    ).status_code == 200
    foreign_gallery = create_empty_private_gallery(
        client,
        parent_id=second_parent,
        client_id=owner_id,
        name="Destino incorreto",
    )
    response = client.post(
        f"/admin/photo-folders/{folder_id}/release",
        json={"gallery_ids": [str(foreign_gallery)]},
    )
    assert response.status_code == 410
    assert response.json()["detail"] == (
        "Destinos privados não são mais aceitos nesta ação. "
        "Publique a pasta e disponibilize fotos individualmente na etapa Clientes."
    )


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


def test_expired_gallery_rejects_freezing_an_open_draft(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Prazo", phone_e164="+5511555555567")
        db.add(owner)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        db.add_all(
            [
                PhotoSelection(
                    derived_gallery_id=gallery_id,
                    photo_asset_id=photo_id,
                    client_id=owner.id,
                ),
                PriceRule(
                    parent_gallery_id=gallery.parent_gallery_id,
                    minimum_quantity=1,
                    maximum_quantity=None,
                    unit_price_cents=500,
                ),
            ]
        )
        db.commit()
    authenticate_client(client, owner.phone_e164)
    checkout = client.post(
        f"/gallery/{gallery_id}/checkout",
        json={"idempotency_key": "draft-before-expiration-0001"},
    )
    assert checkout.status_code == 201
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        gallery.selection_expires_at = now() - timedelta(minutes=1)
        db.commit()
    reported = client.post(
        f"/gallery/{gallery_id}/orders/{checkout.json()['id']}/payment-communications",
        json={"idempotency_key": "report-after-expiration-0001"},
    )
    assert reported.status_code == 403
    with SessionLocal() as db:
        order = db.get(SaleOrder, UUID(checkout.json()["id"]))
        assert order.frozen_at is None
        assert db.scalar(
            select(PhotoSelection.id).where(
                PhotoSelection.derived_gallery_id == gallery_id,
                PhotoSelection.client_id == owner.id,
            )
        )


def test_private_photo_state_is_new_viewed_then_purchased(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente", phone_e164="+5511555555555")
        db.add(owner)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner)
    authenticate_client(client, owner.phone_e164)
    initial = client.get(f"/gallery/{gallery_id}/review").json()["photos"][0]
    assert initial["purchase_state"] == "nova"
    assert initial["commercial_state"] == "available"
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
    purchased = client.get(f"/gallery/{gallery_id}/review").json()["photos"][0]
    assert purchased["purchase_state"] == "já comprada"
    assert purchased["commercial_state"] == "purchased"
    denied = client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection")
    assert denied.status_code == 409
    assert denied.json()["detail"] == "Foto indisponível para seleção."


def test_phone_change_preserves_gallery_owner_and_retires_old_phone(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente", phone_e164="+5511555555555")
        db.add(owner)
        db.commit()
    gallery_id, _ = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        stale_session = AuthSession(
            token_hash="old-phone-session",
            role="client",
            subject_id=owner.id,
            expires_at=now() + timedelta(days=1),
        )
        db.add(stale_session)
        db.commit()
        stale_session_id = stale_session.id
    authenticate_admin(client)
    challenge = client.post("/auth/client/challenge", json={"full_name": owner.full_name, "phone": "+5511666666666"}).json()["challenge_id"]
    with SessionLocal() as db:
        db.get(AuthChallenge, UUID(challenge)).secret_hash = token_hash("123456")
        db.commit()
    assert client.post(f"/admin/clients/{owner.id}/phone", json={"phone_e164": "+5511666666666", "challenge_id": challenge, "code": "123456"}).status_code == 200
    with SessionLocal() as db:
        assert db.get(DerivedGallery, gallery_id).client_id == owner.id
        assert db.get(AuthSession, stale_session_id).revoked_at is not None
        phones = list(
            db.scalars(select(ClientPhone).where(ClientPhone.client_id == owner.id))
        )
        assert {phone.phone_e164: phone.active for phone in phones} == {
            "+5511555555555": False,
            "+5511666666666": True,
        }
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


def test_legacy_clone_is_rejected_and_client_selection_remains_isolated(client: TestClient):
    with SessionLocal() as db:
        mother = Client(full_name="Mãe", phone_e164="+5511555555555")
        father = Client(full_name="Pai", phone_e164="+5511444444444")
        db.add_all([mother, father])
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, mother)
    authenticate_admin(client)
    cloned = client.post(f"/admin/derived-galleries/{gallery_id}/clone", json={"client_id": str(father.id), "idempotency_key": "father-clone-key-0001"})
    assert cloned.status_code == 410
    created = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(
                client.get(f"/admin/derived-galleries/{gallery_id}").json()["parent_gallery_id"]
            ),
            "client_id": str(father.id),
            "name": "Fotos do Pai",
            "photo_ids": [],
            "create_empty_private": True,
        },
    )
    assert created.status_code == 201
    father_gallery_id = created.json()["id"]
    client.cookies.clear()
    authenticate_client(client, father.phone_e164)
    assert client.post(f"/gallery/{father_gallery_id}/photos/{photo_id}/selection").status_code == 404
    with SessionLocal() as db:
        parent_id = db.get(DerivedGallery, UUID(father_gallery_id)).parent_gallery_id
    assert client.post(f"/public-galleries/{parent_id}/photos/{photo_id}/selection").status_code == 201
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
                    "publication_counts": {
                        "published": 0,
                        "ready_to_publish": 0,
                        "processing": 0,
                        "failed": 0,
                    },
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
            "publication_state": "processing",
            "available": False,
            "width": None,
            "height": None,
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
    ).status_code == 201
    assert client.put(
        f"/admin/photo-assets/{photo_id}/source",
        content=image.getvalue(),
        headers={"content-type": "image/jpeg"},
    ).status_code == 202


def test_folder_publish_is_idempotent_and_private_assignment_is_explicit(client: TestClient) -> None:
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
            available=False,
        )
        db.add(photo)
        db.commit()
        parent_id, owner_id = parent.id, owner.id
        gallery_id, folder_id, photo_id = private_gallery.id, folder.id, photo.id

    authenticate_admin(client)
    mark_photo_ready(photo_id)
    first = client.post(f"/admin/photo-folders/{folder_id}/publish", json={})
    assert first.status_code == 200
    assert first.json()["published_count"] == 1
    second = client.post(f"/admin/photo-folders/{folder_id}/publish", json={})
    assert second.status_code == 200
    assert second.json()["published_count"] == 0
    with SessionLocal() as db:
        assert db.scalar(
            select(DerivedGalleryPhoto).where(
                DerivedGalleryPhoto.derived_gallery_id == gallery_id
            )
        ) is None
    assigned = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(owner_id),
            "name": "Fotos da família",
            "photo_ids": [str(photo_id)],
        },
    )
    assert assigned.status_code == 410
    linked_gallery_id = create_empty_private_gallery(
        client,
        parent_id=parent_id,
        client_id=owner_id,
        name="Fotos da família",
    )
    assert linked_gallery_id == gallery_id
    attach_legacy_admin_reference(gallery_id, photo_id)

    client.cookies.clear()
    authenticate_client(client, "+5511999998888")
    visible = client.get(f"/gallery/{gallery_id}/photos")
    assert visible.status_code == 200
    assert visible.json()["photos"] == [
        {"id": str(photo_id), "name": "FILHO_001.jpg", "preview_url": f"/gallery/{gallery_id}/photos/{photo_id}/preview", "width": 1200, "height": 800}
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
        "membership_status": "active",
        "browse_url": f"/gallery/{gallery_id}",
        "origin_removed": False,
        "origin": {
                "id": str(parent_id),
                "name": "Evento público",
                "available": True,
                "browse_url": f"/public-galleries/{parent_id}",
        },
        "folders": [{"id": str(folder_id), "name": "Rodada 1"}],
    }]
    library = client.get("/library").json()
    assert [item["id"] for item in library["public_galleries"]] == [str(parent_id)]
    assert library["public_galleries"][0]["browse_url"] == f"/public-galleries/{parent_id}"
    assert library["private_galleries"] == expected_private
    assert library["galleries"] == expected_private
    assert len(library["journeys"]) == 1
    journey = library["journeys"][0]
    assert journey["id"] == str(parent_id)
    assert journey["primary_surface"] == "public"
    assert journey["browse_url"] == f"/public-galleries/{parent_id}"
    assert journey["private_gallery"]["id"] == str(gallery_id)
    assert journey["selection"]["quantity"] == 0
    assert journey["has_prepared_photos"] is True
    assert journey["actions"] == {
        "continue_url": f"/public-galleries/{parent_id}",
        "review_url": None,
        "orders_url": None,
        "prepared_url": f"/gallery/{gallery_id}",
        "fallback_url": None,
    }


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
    mark_photo_ready(photo_id)
    released = client.post(
        f"/admin/photo-folders/{first_folder_id}/release", json={"gallery_ids": []}
    )
    assert released.status_code == 200, released.json()
    derived_gallery_id = create_empty_private_gallery(
        client,
        parent_id=parent_id,
        client_id=client_id,
        name="Histórico da cliente sintética",
    )
    attach_legacy_admin_reference(derived_gallery_id, photo_id)
    folders = client.get(f"/admin/parent-galleries/{parent_id}/folders").json()["folders"]
    assert {key: value for key, value in folders[0].items() if key != "released_at"} == {
        "id": str(first_folder_id),
        "name": "Rodada 1",
        "status": "released",
        "position": 0,
        "photo_count": 1,
        "preview_url": f"/admin/photo-assets/{photo_id}/watermarked-preview",
        "publication_counts": {
            "published": 1,
            "ready_to_publish": 0,
            "processing": 0,
            "failed": 0,
        },
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
            "publication_counts": {
                "published": 0,
                "ready_to_publish": 0,
                "processing": 1,
                "failed": 0,
            },
        },
    ]

    with SessionLocal() as db:
        db.add(DerivedGalleryPhoto(derived_gallery_id=derived_gallery_id, photo_asset_id=preparing_photo_id))
        db.commit()
    assert client.put(f"/admin/parent-galleries/{parent_id}/cover", json={"photo_id": str(photo_id)}).status_code == 200

    client.cookies.clear()
    authenticate_client(client, "+5511999991234")
    assert client.get(f"/gallery/{derived_gallery_id}/photos").json()["photos"] == [
        {
            "id": str(photo_id),
                "name": "TESTE_001.jpg",
                "preview_url": f"/gallery/{derived_gallery_id}/photos/{photo_id}/preview",
                "width": 1200,
                "height": 800,
            }
    ]
    assert client.get(f"/gallery/{derived_gallery_id}/folders").json()["folders"] == [
        {"id": str(first_folder_id), "name": "Rodada 1", "position": 0, "photo_count": 1}
    ]
    review = client.get(f"/gallery/{derived_gallery_id}/review")
    assert review.status_code == 200
    assert review.json()["gallery"]["cover_preview_url"] == f"/gallery/{derived_gallery_id}/cover-preview"
    assert review.json()["gallery"]["folder_display_mode"] == "individual"
    assert review.json()["gallery"]["cover_title_font"] == "system-sans"
    assert [photo["id"] for photo in review.json()["photos"]] == [str(photo_id)]


def test_private_gallery_serves_dedicated_cover_without_exposing_it_as_content(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    derivative_root = tmp_path / "derivatives"
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivative_root))
    with SessionLocal() as db:
        owner = Client(full_name="Cliente da capa", phone_e164="+5511555554123")
        parent = ParentGallery(
            name="Evento com capa dedicada",
            folder_display_mode="sequential",
            cover_title_font="handwritten-caveat",
        )
        db.add_all([owner, parent])
        db.flush()
        content_folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Conteúdo",
            purpose="content",
            status="released",
        )
        cover_folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Ativos de capa",
            purpose="cover_assets",
            position=-1,
        )
        db.add_all([content_folder, cover_folder])
        db.flush()
        content = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=content_folder.id,
            filename="conteudo.jpg",
            storage_key="tests/conteudo-capa-dedicada.jpg",
            available=True,
        )
        cover = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=cover_folder.id,
            filename="capa.jpg",
            storage_key="tests/capa-dedicada.jpg",
            available=False,
        )
        db.add_all([content, cover])
        db.flush()
        parent.cover_photo_id = cover.id
        gallery = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada com capa",
        )
        db.add(gallery)
        db.flush()
        db.add(DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=content.id))
        for photo in (content, cover):
            relative_path = f"{photo.id}/client_preview.jpg"
            target = derivative_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"preview-protegida")
            db.add(
                MediaDerivative(
                    photo_asset_id=photo.id,
                    variant="client_preview",
                    relative_path=relative_path,
                    status="ready",
                    width=1600,
                    height=900,
                )
            )
        db.commit()
        gallery_id = gallery.id
        cover_id = cover.id

    authenticate_client(client, "+5511555554123")
    review = client.get(f"/gallery/{gallery_id}/review")
    assert review.status_code == 200
    assert review.json()["gallery"]["cover_preview_url"] == f"/gallery/{gallery_id}/cover-preview"
    assert review.json()["gallery"]["folder_display_mode"] == "sequential"
    assert review.json()["gallery"]["cover_title_font"] == "handwritten-caveat"
    assert [photo["name"] for photo in review.json()["photos"]] == ["conteudo.jpg"]
    assert client.get(f"/gallery/{gallery_id}/cover-preview").status_code == 200
    assert client.get(f"/gallery/{gallery_id}/photos/{cover_id}/preview").status_code in {403, 404}


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
        client, parent_id, storage_key="event/preservada.jpg", ready=True
    )
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}
    ).status_code == 200
    gallery_id = create_empty_private_gallery(
        client, parent_id=parent_id, client_id=owner_id, name="Sem histórico"
    )
    attach_legacy_admin_reference(gallery_id, photo_id)
    assert client.delete(f"/admin/derived-galleries/{gallery_id}").status_code == 204

    protected_gallery_id = create_empty_private_gallery(
        client, parent_id=parent_id, client_id=owner_id, name="Com histórico"
    )
    attach_legacy_admin_reference(protected_gallery_id, photo_id)
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
        "available": False,
        "publication_state": "ready_to_publish",
        "width": None,
        "height": None,
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
    first_folder, first_photo = create_folder_photo(client, parent_id, storage_key="evento/primeira.jpg", ready=True)
    second_folder, second_photo = create_folder_photo(
        client, parent_id, folder_name="Segunda", storage_key="evento/segunda.jpg"
    )
    assert client.post(
        f"/admin/photo-folders/{first_folder}/release", json={"gallery_ids": []}
    ).status_code == 200
    gallery_id = create_empty_private_gallery(
        client, parent_id=parent_id, client_id=client_id, name="Ana"
    )
    attach_legacy_admin_reference(gallery_id, first_photo)
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
    folder_id, first_photo = create_folder_photo(client, parent_id, storage_key="evento/lote-1.jpg", ready=True)
    second_photo = UUID(client.post(f"/admin/photo-folders/{folder_id}/photos", json={"filename": "lote-2.jpg", "storage_key": "evento/lote-2.jpg"}).json()["id"])
    mark_photo_ready(second_photo)
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}
    ).status_code == 200
    client_id = UUID(client.post("/admin/clients", json={"full_name": "Cliente Lote", "phone_e164": "+5511999999988"}).json()["id"])
    gallery_id = create_empty_private_gallery(
        client, parent_id=parent_id, client_id=client_id, name="Lote"
    )
    attach_legacy_admin_reference(gallery_id, second_photo)
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
            "phone_verified": False,
            "registration_status": "active",
            "membership_status": None,
            "derived_gallery_id": None,
            "available_count": 0,
            "selected_count": 0,
            "purchased_count": 0,
            "gallery_status": "pending_registration",
            "commercial_status": "no_order",
            "reopening_status": None,
        }
    ]


def test_parent_gallery_clients_aggregates_commercial_precedence_in_constant_queries(
    client: TestClient,
) -> None:
    authenticate_admin(client)
    parent_id = UUID(
        client.post("/admin/parent-galleries", json={"name": "Estados comerciais"}).json()["id"]
    )
    labels = [
        "Revisão",
        "Aguardando",
        "Pago",
        "Expirado",
        "Cancelado",
        "Sem pedido",
        "Pago sem galeria",
    ]
    client_ids = {
        label: UUID(
            client.post(
                "/admin/clients",
                json={
                    "full_name": label,
                    "phone_e164": f"+5511988000{index:04d}",
                },
            ).json()["id"]
        )
        for index, label in enumerate(labels)
    }
    for client_id in client_ids.values():
        assert client.put(
            f"/admin/parent-galleries/{parent_id}/clients/{client_id}"
        ).status_code == 200

    with SessionLocal() as db:
        for phone in db.scalars(
            select(ClientPhone).where(ClientPhone.client_id.in_(client_ids.values()))
        ):
            phone.verified_at = now()
        galleries = {
            label: DerivedGallery(
                parent_gallery_id=parent_id,
                client_id=client_ids[label],
                name=f"Privada {label}",
                selection_expires_at=(
                    now() - timedelta(days=1) if label == "Expirado" else None
                ),
            )
            for label in labels
            if label != "Sem pedido"
        }
        db.add_all(galleries.values())
        db.flush()
        db.add(
            DerivedGalleryMembership(
                derived_gallery_id=galleries["Cancelado"].id,
                parent_gallery_id=parent_id,
                client_id=client_ids["Cancelado"],
                status="blocked",
                blocked_at=now(),
            )
        )

        def order(label: str, payment_status: str) -> SaleOrder:
            return SaleOrder(
                derived_gallery_id=galleries[label].id,
                client_id=client_ids[label],
                payment_status=payment_status,
                total_cents=1000,
            )

        review_order = order("Revisão", "pending")
        db.add_all(
            [
                review_order,
                order("Revisão", "confirmed"),
                order("Aguardando", "pending"),
                order("Pago", "confirmed"),
                order("Cancelado", "cancelled"),
                order("Pago sem galeria", "confirmed"),
            ]
        )
        db.flush()
        db.add(
            PaymentCommunication(
                sale_order_id=review_order.id,
                client_id=client_ids["Revisão"],
                idempotency_key="commercial-precedence-review",
                status="pending_review",
            )
        )
        db.commit()
        db.delete(galleries["Pago sem galeria"])
        db.commit()

    statement_count = 0

    def count_statement(*_args) -> None:
        nonlocal statement_count
        statement_count += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        response = client.get(f"/admin/parent-galleries/{parent_id}/clients")
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    assert response.status_code == 200
    clients_by_name = {item["name"]: item for item in response.json()["clients"]}
    assert clients_by_name["Revisão"]["commercial_status"] == "pending_review"
    assert clients_by_name["Aguardando"]["commercial_status"] == "awaiting_payment"
    assert clients_by_name["Pago"]["commercial_status"] == "paid"
    assert clients_by_name["Expirado"]["commercial_status"] == "overdue"
    assert clients_by_name["Expirado"]["gallery_status"] == "expired"
    assert clients_by_name["Cancelado"]["commercial_status"] == "cancelled"
    assert clients_by_name["Cancelado"]["membership_status"] == "blocked"
    assert clients_by_name["Cancelado"]["gallery_status"] == "blocked"
    assert clients_by_name["Sem pedido"]["commercial_status"] == "no_order"
    assert clients_by_name["Pago sem galeria"]["commercial_status"] == "paid"
    assert clients_by_name["Pago sem galeria"]["derived_gallery_id"] is None
    assert statement_count <= 12


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
    private_payload = {"parent_gallery_id": str(parent_id), "client_id": str(client_id), "name": "Galeria da cliente", "photo_ids": [], "create_empty_private": True}
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


def test_pending_checkout_keeps_cart_editable_until_payment_is_reported(client: TestClient):
    set_test_global_pix(instructions="Confirme com o fotógrafo.")
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
        ])
        db.commit()
        order = create_pending_checkout(db, gallery=gallery, client=owner, checkout_key="checkout-test-0001")
        db.commit()
        repeated = create_pending_checkout(db, gallery=gallery, client=owner, checkout_key="checkout-test-0001")
        assert repeated.id == order.id
        assert order.total_cents == 700
        assert order.price_rule_snapshot["unit_price_cents"] == 700
        assert order.pix_copy_paste_snapshot == VALID_PIX_A
        assert order.pix_instructions_snapshot == "Confirme com o fotógrafo."
        assert order.frozen_at is None
        assert db.scalar(select(PhotoSelection).where(PhotoSelection.derived_gallery_id == gallery_id))
        assert db.scalar(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id)).unit_price_cents == 700


def test_checkout_reuses_and_resynchronizes_the_open_draft(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Rascunho", phone_e164="+5511555554320")
        db.add(owner)
        db.commit()
    gallery_id, first_photo_id = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        first_photo = db.get(PhotoAsset, first_photo_id)
        second_photo = PhotoAsset(
            parent_gallery_id=gallery.parent_gallery_id,
            folder_id=first_photo.folder_id,
            filename="IMG_0002.jpg",
            storage_key="events/one/img-0002.jpg",
        )
        db.add(second_photo)
        db.flush()
        ensure_private_photo_reference(
            db, gallery_id=gallery.id, photo_id=second_photo.id, origin="admin"
        )
        db.add_all(
            [
                PriceRule(
                    parent_gallery_id=gallery.parent_gallery_id,
                    minimum_quantity=1,
                    maximum_quantity=None,
                    unit_price_cents=700,
                ),
                PhotoSelection(
                    derived_gallery_id=gallery.id,
                    client_id=owner.id,
                    photo_asset_id=first_photo_id,
                ),
            ]
        )
        db.commit()
        first = create_pending_checkout(
            db, gallery=gallery, client=owner, checkout_key="draft-first-key"
        )
        db.commit()
        assert client_carts_by_gallery_payload(
            db, galleries=[gallery], client_id=owner.id
        )[gallery.id]["draft_order_id"] == str(first.id)
        db.add(
            PhotoSelection(
                derived_gallery_id=gallery.id,
                client_id=owner.id,
                photo_asset_id=second_photo.id,
            )
        )
        db.commit()
        assert client_carts_by_gallery_payload(
            db, galleries=[gallery], client_id=owner.id
        )[gallery.id]["draft_order_id"] is None
        refreshed = create_pending_checkout(
            db, gallery=gallery, client=owner, checkout_key="draft-second-key"
        )
        db.commit()
        assert refreshed.id == first.id
        assert refreshed.total_cents == 1400
        assert len(
            list(
                db.scalars(
                    select(SaleOrderItem).where(
                        SaleOrderItem.sale_order_id == refreshed.id
                    )
                )
            )
        ) == 2
        second_selection = db.scalar(
            select(PhotoSelection).where(
                PhotoSelection.derived_gallery_id == gallery.id,
                PhotoSelection.client_id == owner.id,
                PhotoSelection.photo_asset_id == second_photo.id,
            )
        )
        db.delete(second_selection)
        db.commit()
        assert client_carts_by_gallery_payload(
            db, galleries=[gallery], client_id=owner.id
        )[gallery.id]["draft_order_id"] is None
        reduced = create_pending_checkout(
            db, gallery=gallery, client=owner, checkout_key="draft-third-key"
        )
        db.commit()
        assert reduced.id == first.id
        assert client_carts_by_gallery_payload(
            db, galleries=[gallery], client_id=owner.id
        )[gallery.id]["draft_order_id"] == str(first.id)
        assert reduced.total_cents == 700
        assert len(
            list(
                db.scalars(
                    select(SaleOrderItem).where(
                        SaleOrderItem.sale_order_id == reduced.id
                    )
                )
            )
        ) == 1
        assert len(
            list(
                db.scalars(
                    select(PhotoSelection).where(
                        PhotoSelection.derived_gallery_id == gallery.id,
                        PhotoSelection.client_id == owner.id,
                    )
                )
            )
        ) == 1


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
        gallery = db.get(DerivedGallery, gallery_id)
        parent_id = gallery.parent_gallery_id
        first_photo = db.get(PhotoAsset, photo_id)
        second_photo = PhotoAsset(
            parent_gallery_id=parent_id,
            folder_id=first_photo.folder_id,
            filename="IMG_0002.jpg",
            storage_key="events/cart/img-0002.jpg",
        )
        db.add(second_photo)
        db.flush()
        ensure_private_photo_reference(
            db, gallery_id=gallery_id, photo_id=second_photo.id, origin="admin"
        )
        db.add(PriceRule(parent_gallery_id=parent_id, minimum_quantity=1, maximum_quantity=None, unit_price_cents=500))
        db.commit()
        second_photo_id = second_photo.id
    authenticate_client(client, owner.phone_e164)
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection").status_code == 201
    cart = client.get(f"/gallery/{gallery_id}/cart")
    assert cart.status_code == 200
    assert cart.json()["total_cents"] == 500
    checkout = client.post(f"/gallery/{gallery_id}/checkout", json={"idempotency_key": "client-checkout-0001"})
    assert checkout.status_code == 201
    assert checkout.json()["payment_status"] == "pending"
    assert client.post(f"/gallery/{gallery_id}/checkout", json={"idempotency_key": "client-checkout-0001"}).json()["id"] == checkout.json()["id"]
    assert client.post(
        f"/gallery/{gallery_id}/photos/{second_photo_id}/selection"
    ).status_code == 201
    updated = client.get(
        f"/gallery/{gallery_id}/orders/{checkout.json()['id']}"
    ).json()
    assert updated["total_cents"] == 1000
    assert {item["photo_id"] for item in updated["items"]} == {
        str(photo_id),
        str(second_photo_id),
    }
    assert client.delete(
        f"/gallery/{gallery_id}/photos/{second_photo_id}/selection"
    ).status_code == 204
    reduced = client.get(
        f"/gallery/{gallery_id}/orders/{checkout.json()['id']}"
    ).json()
    assert reduced["total_cents"] == 500
    assert [item["photo_id"] for item in reduced["items"]] == [str(photo_id)]


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
        ])
        db.commit()
    authenticate_client(client, owner.phone_e164)
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection").status_code == 201
    order = client.post(f"/gallery/{gallery_id}/checkout", json={"idempotency_key": "client-order-0001"}).json()
    private_order = client.get(f"/gallery/{gallery_id}/orders/{order['id']}")
    assert private_order.status_code == 200
    assert private_order.json()["pix"]["copy_paste"] == VALID_PIX_A
    assert private_order.json()["pix"]["confirmation"] == "A confirmação do pagamento é manual pelo fotógrafo."
    authenticate_client(client, other.phone_e164)
    denied = client.get(f"/gallery/{gallery_id}/orders/{order['id']}")
    assert denied.status_code == 403
    assert VALID_PIX_A not in denied.text


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
        persisted_order = db.get(SaleOrder, UUID(order["id"]))
        assert persisted_order.payment_status == "pending"
        assert persisted_order.frozen_at is not None
        assert not db.scalar(
            select(PhotoSelection).where(
                PhotoSelection.derived_gallery_id == gallery_id,
                PhotoSelection.client_id == owner.id,
            )
        )
        outboxes = list(db.scalars(select(PaymentNotificationOutbox)))
        assert len(outboxes) == 1
        assert outboxes[0].template_kind == "photographer_reported"
        assert outboxes[0].recipient_phone == "+5511555554000"
        first_item_ids = set(
            db.scalars(
                select(SaleOrderItem.photo_asset_id_snapshot).where(
                    SaleOrderItem.sale_order_id == persisted_order.id
                )
            )
        )
        first_photo = db.get(PhotoAsset, photo_id)
        complementary_photo = PhotoAsset(
            parent_gallery_id=persisted_order.parent_gallery_id_snapshot,
            folder_id=first_photo.folder_id,
            filename="IMG_COMPLEMENTAR.jpg",
            storage_key="events/one/img-complementar.jpg",
        )
        db.add(complementary_photo)
        db.commit()
        complementary_photo_id = complementary_photo.id
        parent_id = persisted_order.parent_gallery_id_snapshot
    private_status = client.get(f"/gallery/{gallery_id}/payment-communications")
    assert private_status.status_code == 200
    status_order = private_status.json()["orders"][0]
    assert status_order["communication"]["status"] == "pending_review"
    assert status_order["commercial_state"] == "payment_reported"
    assert status_order["frozen_at"] is not None
    assert status_order["items"] == [
        {
            "item_id": status_order["items"][0]["item_id"],
            "photo_id": str(photo_id),
            "name": "IMG_0001.jpg",
            "unit_price_cents": 500,
            "preview_url": f"/gallery/{gallery_id}/photos/{photo_id}/preview",
        }
    ]
    assert "+5511555554000" not in private_status.text
    review = client.get(f"/gallery/{gallery_id}/review").json()
    assert next(photo for photo in review["photos"] if photo["id"] == str(photo_id))[
        "commercial_state"
    ] == "payment_reported"
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection").status_code == 409
    selected = client.post(
        f"/public-galleries/{parent_id}/photos/{complementary_photo_id}/selection"
    )
    assert selected.status_code == 201
    assert selected.json()["cart"]["quantity"] == 1
    complementary_order = client.post(
        f"/gallery/{gallery_id}/checkout",
        json={"idempotency_key": "cart" * 3},
    )
    assert complementary_order.status_code == 201
    assert complementary_order.json()["id"] != order["id"]
    with SessionLocal() as db:
        assert set(
            db.scalars(
                select(SaleOrderItem.photo_asset_id_snapshot).where(
                    SaleOrderItem.sale_order_id == UUID(order["id"])
                )
            )
        ) == first_item_ids


def test_frozen_legacy_pending_order_remains_resumable_without_cart(
    client: TestClient, monkeypatch
):
    monkeypatch.setenv("WHATSAPP_PHOTOGRAPHER_PHONE_E164", "+5511555554000")
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Legada", phone_e164="+5511555554387")
        db.add(owner)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, owner)
    with SessionLocal() as db:
        order = SaleOrder(
            derived_gallery_id=gallery_id,
            client_id=owner.id,
            payment_status="pending",
            total_cents=500,
            checkout_key="legacy-checkout-key",
            frozen_at=now(),
        )
        db.add(order)
        db.flush()
        db.add(
            SaleOrderItem(
                sale_order_id=order.id,
                photo_asset_id=photo_id,
                unit_price_cents=500,
                filename_snapshot="IMG_LEGADA.jpg",
            )
        )
        db.commit()
        order_id = order.id
    authenticate_client(client, owner.phone_e164)

    detail = client.get(f"/gallery/{gallery_id}/orders/{order_id}")
    assert detail.status_code == 200
    assert detail.json()["items"][0]["name"] == "IMG_LEGADA.jpg"
    reported = client.post(
        f"/gallery/{gallery_id}/orders/{order_id}/payment-communications",
        json={"idempotency_key": "legacy-report-key"},
    )
    assert reported.status_code == 201
    with SessionLocal() as db:
        persisted = db.get(SaleOrder, order_id)
        assert persisted.frozen_at is not None
        assert persisted.total_cents == 500
        assert not db.scalar(
            select(PhotoSelection).where(
                PhotoSelection.derived_gallery_id == gallery_id,
                PhotoSelection.client_id == owner.id,
            )
        )


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


def test_admin_payment_dashboard_groups_orders_uses_snapshots_and_paginates_without_n_plus_one(
    client: TestClient,
):
    reference = now()
    with SessionLocal() as db:
        ana = Client(full_name="Ana Pagamentos", phone_e164="+5511555554411")
        bia = Client(full_name="Bia Histórica", phone_e164="+5511555554422")
        parent = ParentGallery(name="Evento atual")
        db.add_all([ana, bia, parent])
        db.flush()
        gallery = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=ana.id,
            name="Privada da Ana",
        )
        db.add(gallery)
        db.flush()
        reported = SaleOrder(
            derived_gallery_id=gallery.id,
            client_id=ana.id,
            payment_status="pending",
            total_cents=1200,
            created_at=reference - timedelta(minutes=10),
        )
        confirmed = SaleOrder(
            derived_gallery_id=gallery.id,
            client_id=ana.id,
            payment_status="confirmed",
            total_cents=800,
            confirmed_at=reference - timedelta(minutes=4),
            created_at=reference - timedelta(minutes=5),
        )
        removed_parent_id = uuid4()
        removed_gallery_id = uuid4()
        historical = SaleOrder(
            derived_gallery_id=None,
            derived_gallery_id_snapshot=removed_gallery_id,
            derived_gallery_name_snapshot="Galeria preservada",
            parent_gallery_id_snapshot=removed_parent_id,
            parent_gallery_name_snapshot="Evento removido",
            client_id=bia.id,
            client_name_snapshot=bia.full_name,
            payment_status="pending",
            total_cents=1500,
            created_at=reference,
        )
        db.add_all([reported, confirmed, historical])
        db.flush()
        communication = PaymentCommunication(
            sale_order_id=reported.id,
            client_id=ana.id,
            idempotency_key="dashboard-reported-0001",
        )
        db.add(communication)
        db.flush()
        db.add(
            PaymentNotificationOutbox(
                payment_communication_id=communication.id,
                recipient_phone="+5511555554000",
                template_kind="photographer_reported",
                idempotency_key="dashboard-notice-0001",
                status="failed",
                attempts=1,
                last_error="Falha temporária sanitizada.",
            )
        )
        db.commit()
        communication_id = communication.id

    authenticate_admin(client)
    statement_count = 0

    def count_statement(*_args) -> None:
        nonlocal statement_count
        statement_count += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        first_page = client.get("/admin/payment-communications", params={"limit": 1})
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    assert first_page.status_code == 200
    payload = first_page.json()
    assert payload["summary"] == {
        "clients": 2,
        "orders": 3,
        "total_cents": 3500,
        "financial_statuses": {
            "awaiting_payment": 1,
            "confirmed": 1,
            "reported": 1,
        },
        "failed_messages": 1,
    }
    assert len(payload["groups"]) == 1
    assert payload["groups"][0]["client"]["name"] == "Bia Histórica"
    assert payload["groups"][0]["orders"][0]["gallery"] == {
        "id": str(removed_gallery_id),
        "name": "Galeria preservada",
        "removed": True,
    }
    assert payload["page"]["next_cursor"]
    # O template global acrescenta uma consulta constante; o limite continua
    # independente da quantidade de clientes, pedidos, itens e comunicações.
    assert statement_count <= 8

    second_page = client.get(
        "/admin/payment-communications",
        params={"limit": 1, "cursor": payload["page"]["next_cursor"]},
    )
    assert second_page.status_code == 200
    second_payload = second_page.json()
    assert second_payload["groups"][0]["client"]["name"] == "Ana Pagamentos"
    assert len(second_payload["groups"][0]["orders"]) == 2
    assert second_payload["communications"][0]["id"] == str(communication_id)
    assert second_payload["communications"][0]["photographer_notification"]["last_error"] == "Falha temporária de entrega."
    assert "Falha temporária sanitizada" not in second_page.text


def test_admin_payment_dashboard_combines_validated_filters(client: TestClient):
    reference = now()
    with SessionLocal() as db:
        ana = Client(full_name="Ana Filtro", phone_e164="+5511555554433")
        bia = Client(full_name="Bia Filtro", phone_e164="+5511555554444")
        parent = ParentGallery(name="Evento filtrável")
        other_parent = ParentGallery(name="Outro evento")
        db.add_all([ana, bia, parent, other_parent])
        db.flush()
        ana_gallery = DerivedGallery(
            parent_gallery_id=parent.id, client_id=ana.id, name="Ana privada"
        )
        bia_gallery = DerivedGallery(
            parent_gallery_id=other_parent.id, client_id=bia.id, name="Bia privada"
        )
        db.add_all([ana_gallery, bia_gallery])
        db.flush()
        ana_order = SaleOrder(
            derived_gallery_id=ana_gallery.id,
            client_id=ana.id,
            payment_status="pending",
            total_cents=1000,
            created_at=reference,
        )
        bia_order = SaleOrder(
            derived_gallery_id=bia_gallery.id,
            client_id=bia.id,
            payment_status="confirmed",
            total_cents=2000,
            confirmed_at=reference,
            created_at=reference,
        )
        db.add_all([ana_order, bia_order])
        db.flush()
        communication = PaymentCommunication(
            sale_order_id=ana_order.id,
            client_id=ana.id,
            idempotency_key="combined-filter-0001",
        )
        db.add(communication)
        db.flush()
        db.add(
            PaymentNotificationOutbox(
                payment_communication_id=communication.id,
                recipient_phone="+5511555554000",
                template_kind="photographer_reported",
                idempotency_key="combined-filter-notice-0001",
                status="failed",
                attempts=1,
            )
        )
        db.commit()
        parent_id = parent.id

    authenticate_admin(client)
    response = client.get(
        "/admin/payment-communications",
        params={
            "query": "ana",
            "parent_gallery_id": str(parent_id),
            "financial_status": "reported",
            "delivery_status": "failed",
            "created_from": (reference - timedelta(minutes=1)).isoformat(),
            "created_to": (reference + timedelta(minutes=1)).isoformat(),
        },
    )
    assert response.status_code == 200
    assert response.json()["summary"]["orders"] == 1
    assert response.json()["groups"][0]["client"]["name"] == "Ana Filtro"
    assert response.json()["facets"]["delivery_statuses"] == {"failed": 1}
    assert client.get(
        "/admin/payment-communications",
        params={"financial_status": "invalid"},
    ).status_code == 422
    assert client.get(
        "/admin/payment-communications",
        params={"created_from": reference.isoformat(), "created_to": (reference - timedelta(days=1)).isoformat()},
    ).status_code == 422
    assert client.get(
        "/admin/payment-communications", params={"cursor": "não-é-cursor"}
    ).status_code == 422


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
        json={"tiers": [{"minimum_quantity": 2, "maximum_quantity": None, "unit_price_cents": 500}]},
    )
    assert invalid.status_code == 422
    saved = client.put(
        f"/admin/parent-galleries/{parent_id}/pricing",
        json={
            "tiers": [
                {"minimum_quantity": 1, "maximum_quantity": 10, "unit_price_cents": 700},
                {"minimum_quantity": 11, "maximum_quantity": None, "unit_price_cents": 500},
            ],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["has_downward_jump"] is False
    inherited = client.get(f"/admin/derived-galleries/{gallery_id}/pricing")
    assert inherited.json()["pix"]["scope"] == "global"
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
        client, parent_id, storage_key="inheritance/photo.jpg", ready=True
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
            "photo_ids": [],
            "create_empty_private": True,
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
        f"/public-galleries/{parent_id}/photos/{photo_id}/selection"
    ).status_code == 201

    client.cookies.clear()
    authenticate_admin(client)
    set_test_global_pix(VALID_PIX_B, "Instrução B")
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
    set_test_global_pix(VALID_PIX_A, "Instrução C")
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
    assert frozen.json()["pix"]["copy_paste"] == VALID_PIX_B
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
    assert order["pix"]["copy_paste"] == VALID_PIX_A
    assert order["items"] == [{"photo_id": str(photo_id), "name": "IMG_0001.jpg", "unit_price_cents": 900}]
    with SessionLocal() as db:
        assert db.scalar(select(SaleOrder).where(SaleOrder.derived_gallery_id == gallery_id)).payment_status == "pending"


def test_real_selection_routes_keep_public_and_private_counters_in_sync_through_payment(
    client: TestClient,
) -> None:
    """Contrato da change: uma projeção, inclusive para seleção originada do filtro facial."""
    from app.auth import (
        FacialSearchCandidate,
        FacialSearchRequest,
        GalleryFacialPolicy,
    )

    authenticate_admin(client)
    owner_id = UUID(
        client.post(
            "/admin/clients",
            json={"full_name": "Cliente Contadores", "phone_e164": "+5511555591001"},
        ).json()["id"]
    )
    parent_id = UUID(
        client.post("/admin/parent-galleries", json={"name": "Evento Contadores"}).json()["id"]
    )
    assert client.put(f"/admin/parent-galleries/{parent_id}/clients/{owner_id}").status_code == 200
    folder_id, first_photo_id = create_folder_photo(client, parent_id, ready=True)
    second_photo_id = UUID(
        client.post(
            f"/admin/photo-folders/{folder_id}/photos",
            json={
                "filename": "IMG_0002.jpg",
                "storage_key": "events/counters/img-0002.jpg",
            },
        ).json()["id"]
    )
    mark_photo_ready(second_photo_id)
    assert client.post(f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}).status_code == 200

    with SessionLocal() as db:
        owner = db.get(Client, owner_id)
        policy = GalleryFacialPolicy(
            parent_gallery_id=parent_id,
            status="active",
            legal_notice_version="test-notice",
            legal_basis_reference="test-authority",
            retention_policy_version="test-retention",
            model_version="test-model",
            quality_version="test-quality",
            actor_admin_id=db.scalar(select(AdminUser.id)),
            activated_at=now(),
        )
        db.add(policy)
        db.flush()
        search = FacialSearchRequest(
            parent_gallery_id=parent_id,
            client_id=owner_id,
            policy_id=policy.id,
            status="ready",
            consent_version="test-consent",
            legal_notice_version="test-notice",
            subject_declaration="adult",
            model_version="test-model",
            quality_version="test-quality",
            index_generation=1,
            snapshot_total=1,
            snapshot_ready=1,
            compare_total=1,
            compare_done=1,
            expires_at=now() + timedelta(hours=1),
        )
        db.add(search)
        db.flush()
        db.add(
            FacialSearchCandidate(
                search_request_id=search.id,
                parent_gallery_id=parent_id,
                client_id=owner_id,
                photo_asset_id=second_photo_id,
                rank=1,
                quality_band="best",
                expires_at=search.expires_at,
            )
        )
        db.add(
            PriceRule(
                parent_gallery_id=parent_id,
                minimum_quantity=1,
                maximum_quantity=None,
                unit_price_cents=500,
            )
        )
        db.commit()
        search_id = search.id
        owner_phone = owner.phone_e164

    client.cookies.clear()
    authenticate_client(client, owner_phone)
    first = client.post(f"/public-galleries/{parent_id}/photos/{first_photo_id}/selection")
    assert first.status_code == 201
    gallery_id = UUID(first.json()["private_gallery_id"])
    facial = client.post(
        f"/public-galleries/{parent_id}/facial-searches/{search_id}"
        f"/candidates/{second_photo_id}/selection"
    )
    assert facial.status_code == 201

    client.cookies.clear()
    authenticate_admin(client)
    public_card = client.get(f"/admin/parent-galleries/{parent_id}/clients").json()["clients"][0]
    private_member = client.get(f"/admin/derived-galleries/{gallery_id}/members").json()["members"][0]
    private_selection = client.get(
        f"/admin/derived-galleries/{gallery_id}/selection", params={"client_id": owner_id}
    ).json()
    assert public_card["selected_count"] == 2
    assert private_member["selected_count"] == 2
    assert private_selection["selection_count"] == 2
    assert public_card["purchased_count"] == private_member["purchased_count"] == 0

    client.cookies.clear()
    authenticate_client(client, owner_phone)
    order = client.post(
        f"/gallery/{gallery_id}/checkout",
        json={"idempotency_key": "counter-order-0001"},
    )
    assert order.status_code == 201
    reported = client.post(
        f"/gallery/{gallery_id}/orders/{order.json()['id']}/payment-communications",
        json={"idempotency_key": "counter-payment-0001"},
    )
    assert reported.status_code == 201

    client.cookies.clear()
    authenticate_admin(client)
    communication_id = UUID(reported.json()["id"])
    assert client.post(
        f"/admin/payment-communications/{communication_id}/decision",
        json={"decision": "confirmed"},
    ).status_code == 200
    public_confirmed = client.get(f"/admin/parent-galleries/{parent_id}/clients").json()[
        "clients"
    ][0]
    private_confirmed = client.get(f"/admin/derived-galleries/{gallery_id}/members").json()[
        "members"
    ][0]
    assert public_confirmed["purchased_count"] == private_confirmed["purchased_count"] == 2

    corrected = client.post(
        f"/admin/payment-communications/{communication_id}/correction",
        json={"idempotency_key": "counter-correction-0001"},
    )
    assert corrected.status_code == 200
    public_corrected = client.get(f"/admin/parent-galleries/{parent_id}/clients").json()[
        "clients"
    ][0]
    private_corrected = client.get(f"/admin/derived-galleries/{gallery_id}/members").json()[
        "members"
    ][0]
    assert public_corrected["purchased_count"] == private_corrected["purchased_count"] == 0


def test_same_client_commercial_journey_stays_isolated_across_two_galleries_and_folders(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pedidos, decisões e falhas de mensagem não atravessam a fronteira da Galeria pública."""
    from app.messaging import WhatsAppDeliveryError
    from app.worker import process_next_payment_notification

    class FailingProvider:
        def send_transactional(self, phone_e164, message, *, idempotency_key):
            del phone_e164, message, idempotency_key
            raise WhatsAppDeliveryError("Provedor temporariamente indisponível.", transient=False)

    monkeypatch.setenv("WHATSAPP_MAX_ATTEMPTS", "1")
    monkeypatch.setattr("app.worker.whatsapp_provider_from_environment", lambda: FailingProvider())
    authenticate_admin(client)
    owner_id = UUID(
        client.post(
            "/admin/clients",
            json={"full_name": "Cliente Duas Galerias", "phone_e164": "+5511555591099"},
        ).json()["id"]
    )
    first_parent_id = UUID(
        client.post("/admin/parent-galleries", json={"name": "Evento A"}).json()["id"]
    )
    second_parent_id = UUID(
        client.post("/admin/parent-galleries", json={"name": "Evento B"}).json()["id"]
    )
    for parent_id in (first_parent_id, second_parent_id):
        assert client.put(f"/admin/parent-galleries/{parent_id}/clients/{owner_id}").status_code == 200

    first_folder_id, first_photo_id = create_folder_photo(
        client,
        first_parent_id,
        folder_name="Cerimônia",
        storage_key="events/journey-a/cerimonia.jpg",
        ready=True,
    )
    second_folder_id, second_photo_id = create_folder_photo(
        client,
        first_parent_id,
        folder_name="Confraternização",
        storage_key="events/journey-a/confraternizacao.jpg",
        ready=True,
    )
    third_folder_id, third_photo_id = create_folder_photo(
        client,
        second_parent_id,
        folder_name="Retratos",
        storage_key="events/journey-b/retrato.jpg",
        ready=True,
    )
    for folder_id in (first_folder_id, second_folder_id, third_folder_id):
        assert client.post(f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": []}).status_code == 200
    with SessionLocal() as db:
        db.add_all(
            [
                PriceRule(
                    parent_gallery_id=first_parent_id,
                    minimum_quantity=1,
                    maximum_quantity=None,
                    unit_price_cents=500,
                ),
                PriceRule(
                    parent_gallery_id=second_parent_id,
                    minimum_quantity=1,
                    maximum_quantity=None,
                    unit_price_cents=700,
                ),
            ]
        )
        owner_phone = db.get(Client, owner_id).phone_e164
        db.commit()

    client.cookies.clear()
    authenticate_client(client, owner_phone)
    first_selection = client.post(
        f"/public-galleries/{first_parent_id}/photos/{first_photo_id}/selection"
    )
    second_selection = client.post(
        f"/public-galleries/{first_parent_id}/photos/{second_photo_id}/selection"
    )
    third_selection = client.post(
        f"/public-galleries/{second_parent_id}/photos/{third_photo_id}/selection"
    )
    assert first_selection.status_code == second_selection.status_code == third_selection.status_code == 201
    first_gallery_id = UUID(first_selection.json()["private_gallery_id"])
    second_gallery_id = UUID(third_selection.json()["private_gallery_id"])
    assert UUID(second_selection.json()["private_gallery_id"]) == first_gallery_id
    assert first_gallery_id != second_gallery_id

    client.cookies.clear()
    authenticate_admin(client)
    assert client.get(f"/admin/parent-galleries/{first_parent_id}/clients").json()["clients"][0][
        "selected_count"
    ] == 2
    assert client.get(f"/admin/parent-galleries/{second_parent_id}/clients").json()["clients"][0][
        "selected_count"
    ] == 1
    client.cookies.clear()
    authenticate_client(client, owner_phone)

    first_order = client.post(
        f"/gallery/{first_gallery_id}/checkout",
        json={"idempotency_key": "two-gallery-order-a"},
    )
    second_order = client.post(
        f"/gallery/{second_gallery_id}/checkout",
        json={"idempotency_key": "two-gallery-order-b"},
    )
    assert first_order.status_code == second_order.status_code == 201
    assert first_order.json()["total_cents"] == 1_000
    assert second_order.json()["total_cents"] == 700
    first_report = client.post(
        f"/gallery/{first_gallery_id}/orders/{first_order.json()['id']}/payment-communications",
        json={"idempotency_key": "two-gallery-payment-a"},
    )
    second_report = client.post(
        f"/gallery/{second_gallery_id}/orders/{second_order.json()['id']}/payment-communications",
        json={"idempotency_key": "two-gallery-payment-b"},
    )
    assert first_report.status_code == second_report.status_code == 201

    client.cookies.clear()
    authenticate_admin(client)
    first_communication_id = UUID(first_report.json()["id"])
    second_communication_id = UUID(second_report.json()["id"])
    with SessionLocal() as db:
        for notification in db.scalars(
            select(PaymentNotificationOutbox).where(
                PaymentNotificationOutbox.template_kind == "photographer_reported"
            )
        ):
            notification.status = "sent"
        db.commit()

    assert client.post(
        f"/admin/payment-communications/{first_communication_id}/decision",
        json={"decision": "confirmed"},
    ).status_code == 200
    assert process_next_payment_notification() is True
    with SessionLocal() as db:
        first_order_row = db.get(SaleOrder, UUID(first_order.json()["id"]))
        failed_notice = db.scalar(
            select(PaymentNotificationOutbox).where(
                PaymentNotificationOutbox.payment_communication_id == first_communication_id,
                PaymentNotificationOutbox.template_kind == "confirmed",
            )
        )
        assert first_order_row.payment_status == "confirmed"
        assert failed_notice.status == "failed"

    assert client.post(
        f"/admin/payment-communications/{second_communication_id}/decision",
        json={"decision": "confirmed"},
    ).status_code == 200
    with SessionLocal() as db:
        notices_before_correction = list(
            db.scalars(
                select(PaymentNotificationOutbox).where(
                    PaymentNotificationOutbox.payment_communication_id == first_communication_id
                )
            )
        )
    corrected = client.post(
        f"/admin/payment-communications/{first_communication_id}/correction",
        json={"idempotency_key": "two-gallery-correction-a"},
    )
    assert corrected.status_code == 200
    with SessionLocal() as db:
        assert db.get(SaleOrder, UUID(first_order.json()["id"])).payment_status == "pending"
        assert db.get(SaleOrder, UUID(second_order.json()["id"])).payment_status == "confirmed"
        assert len(
            list(
                db.scalars(
                    select(PaymentNotificationOutbox).where(
                        PaymentNotificationOutbox.payment_communication_id == first_communication_id
                    )
                )
            )
        ) == len(notices_before_correction)

    assert client.post(
        f"/admin/payment-communications/{first_communication_id}/decision",
        json={"decision": "confirmed"},
    ).status_code == 200
    with SessionLocal() as db:
        assert db.get(SaleOrder, UUID(first_order.json()["id"])).payment_status == "confirmed"
        first_decision_notices = list(
            db.scalars(
                select(PaymentNotificationOutbox).where(
                    PaymentNotificationOutbox.payment_communication_id == first_communication_id,
                    PaymentNotificationOutbox.template_kind == "confirmed",
                )
            )
        )
        assert len(first_decision_notices) == 2
        assert len({notice.idempotency_key for notice in first_decision_notices}) == 2

    first_card = client.get(f"/admin/parent-galleries/{first_parent_id}/clients").json()["clients"][0]
    second_card = client.get(f"/admin/parent-galleries/{second_parent_id}/clients").json()["clients"][0]
    assert (first_card["selected_count"], first_card["purchased_count"]) == (0, 2)
    assert (second_card["selected_count"], second_card["purchased_count"]) == (0, 1)

    dashboard = client.get("/admin/payment-communications").json()
    gallery_groups = {
        order["parent_gallery"]["id"]: order
        for group in dashboard["groups"]
        for order in group["orders"]
    }
    assert set(gallery_groups) == {str(first_parent_id), str(second_parent_id)}
    assert {folder["name"] for folder in gallery_groups[str(first_parent_id)]["folders"]} == {
        "Cerimônia",
        "Confraternização",
    }


def test_client_cart_projection_is_batched_and_isolated_between_members() -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Cliente do carrinho", phone_e164="+5511777777711")
        other = Client(full_name="Outra cliente", phone_e164="+5511777777722")
        db.add_all([owner, other])
        db.flush()
        galleries: list[DerivedGallery] = []
        for position in range(5):
            parent = ParentGallery(name=f"Evento {position}")
            db.add(parent)
            db.flush()
            db.add(
                PriceRule(
                    parent_gallery_id=parent.id,
                    minimum_quantity=1,
                    maximum_quantity=None,
                    unit_price_cents=500 + position,
                )
            )
            folder = PhotoFolder(
                parent_gallery_id=parent.id,
                name="Fotos",
                status="released",
            )
            gallery = DerivedGallery(
                parent_gallery_id=parent.id,
                client_id=owner.id,
                name=f"Privada {position}",
            )
            db.add_all([folder, gallery])
            db.flush()
            photo = PhotoAsset(
                parent_gallery_id=parent.id,
                folder_id=folder.id,
                filename=f"IMG_{position}.jpg",
                storage_key=f"batched/{position}.jpg",
            )
            db.add(photo)
            db.flush()
            db.add_all(
                [
                    PhotoSelection(
                        derived_gallery_id=gallery.id,
                        photo_asset_id=photo.id,
                        client_id=owner.id,
                    ),
                    PhotoSelection(
                        derived_gallery_id=gallery.id,
                        photo_asset_id=photo.id,
                        client_id=other.id,
                    ),
                ]
            )
            galleries.append(gallery)
        db.commit()

        statement_count = 0

        def count_statement(*_args) -> None:
            nonlocal statement_count
            statement_count += 1

        event.listen(engine, "before_cursor_execute", count_statement)
        try:
            payload = client_carts_by_gallery_payload(
                db, galleries=galleries, client_id=owner.id
            )
        finally:
            event.remove(engine, "before_cursor_execute", count_statement)

        assert statement_count <= 6
        assert len(payload) == 5
        assert all(cart["quantity"] == 1 for cart in payload.values())
        assert {
            item["name"]
            for cart in payload.values()
            for item in cart["items"]
        } == {f"IMG_{position}.jpg" for position in range(5)}


def test_client_library_and_purchase_history_queries_remain_batched(
    client: TestClient,
) -> None:
    phone = "+5511777777733"
    with SessionLocal() as db:
        owner = Client(full_name="Cliente", phone_e164=phone)
        db.add(owner)
        db.commit()
        owner_id = owner.id

    def add_gallery(position: int) -> None:
        with SessionLocal() as db:
            parent = ParentGallery(
                name=f"Evento da biblioteca {position}",
                event_name=f"Evento {position}",
            )
            db.add(parent)
            db.flush()
            folder = PhotoFolder(
                parent_gallery_id=parent.id,
                name="Fotos",
                status="released",
                purpose="content",
            )
            gallery = DerivedGallery(
                parent_gallery_id=parent.id,
                client_id=owner_id,
                name=f"Privada {position}",
            )
            db.add_all(
                [
                    folder,
                    gallery,
                    ParentGalleryRegistration(
                        parent_gallery_id=parent.id,
                        client_id=owner_id,
                        status="active",
                    ),
                ]
            )
            db.flush()
            photo = PhotoAsset(
                parent_gallery_id=parent.id,
                folder_id=folder.id,
                filename=f"IMG_{position:04d}.jpg",
                storage_key=f"library-batched/{position}.jpg",
            )
            db.add(photo)
            db.flush()
            db.add(
                DerivedGalleryPhoto(
                    derived_gallery_id=gallery.id,
                    photo_asset_id=photo.id,
                    origin="client",
                )
            )
            order = SaleOrder(
                derived_gallery_id=gallery.id,
                derived_gallery_id_snapshot=gallery.id,
                derived_gallery_name_snapshot=gallery.name,
                parent_gallery_id_snapshot=parent.id,
                parent_gallery_name_snapshot=parent.name,
                client_id=owner_id,
                client_name_snapshot="Cliente",
                payment_status="pending",
                total_cents=700,
                frozen_at=now(),
            )
            db.add(order)
            db.flush()
            db.add(
                SaleOrderItem(
                    sale_order_id=order.id,
                    photo_asset_id=photo.id,
                    photo_asset_id_snapshot=photo.id,
                    filename_snapshot=photo.filename,
                    folder_id_snapshot=folder.id,
                    folder_name_snapshot=folder.name,
                    unit_price_cents=700,
                )
            )
            db.commit()

    def measure(path: str) -> tuple[int, float, dict]:
        statement_count = 0

        def count_statement(*_args) -> None:
            nonlocal statement_count
            statement_count += 1

        event.listen(engine, "before_cursor_execute", count_statement)
        started_at = perf_counter()
        try:
            response = client.get(path)
        finally:
            elapsed = perf_counter() - started_at
            event.remove(engine, "before_cursor_execute", count_statement)
        assert response.status_code == 200
        return statement_count, elapsed, response.json()

    add_gallery(0)
    authenticate_client(client, phone)
    base_library_queries, base_library_seconds, base_library = measure("/library")
    base_history_queries, base_history_seconds, base_history = measure("/library/purchases")

    for position in range(1, 5):
        add_gallery(position)

    expanded_library_queries, expanded_library_seconds, expanded_library = measure("/library")
    expanded_history_queries, expanded_history_seconds, expanded_history = measure(
        "/library/purchases"
    )

    assert len(base_library["journeys"]) == len(base_history["orders"]) == 1
    assert len(expanded_library["journeys"]) == len(expanded_history["orders"]) == 5
    assert expanded_library_queries <= base_library_queries + 1
    assert expanded_history_queries <= base_history_queries + 1
    print(
        "library batching diagnostic:",
        {
            "library": {
                "one": [base_library_queries, round(base_library_seconds, 4)],
                "five": [expanded_library_queries, round(expanded_library_seconds, 4)],
            },
            "purchases": {
                "one": [base_history_queries, round(base_history_seconds, 4)],
                "five": [expanded_history_queries, round(expanded_history_seconds, 4)],
            },
        },
    )


def test_private_media_payment_correction_and_reopening_contracts_start_missing(
    client: TestClient,
) -> None:
    """Contratos HTTP ausentes antes da implementação não dependem de fixtures implícitas."""
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Operações", phone_e164="+5511555591002")
        db.add(owner)
        db.commit()
        owner_id = owner.id
        owner_phone = owner.phone_e164

    gallery_id, _ = create_gallery_for_client(client, owner)
    authenticate_admin(client)
    created_folder = client.post(
        f"/admin/derived-galleries/{gallery_id}/folders", json={"name": "Ensaio privado"}
    )
    assert created_folder.status_code == 201
    private_folder_id = UUID(created_folder.json()["id"])
    assert client.get(f"/admin/derived-galleries/{gallery_id}/folders").status_code == 200
    assert (
        client.post(
            f"/admin/photo-folders/{private_folder_id}/photos",
            json={
                "filename": "PRIVADA_0001.jpg",
                "storage_key": f"private/{gallery_id}/private-0001.jpg",
            },
        ).status_code
        == 201
    )

    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        gallery.selection_expires_at = now() - timedelta(minutes=1)
        order = SaleOrder(
            derived_gallery_id=gallery_id,
            client_id=owner_id,
            payment_status="confirmed",
            total_cents=500,
            confirmed_at=now(),
        )
        db.add(order)
        db.flush()
        communication = PaymentCommunication(
            sale_order_id=order.id,
            client_id=owner_id,
            idempotency_key="operations-correction-source",
            status="confirmed",
            decided_by_admin_id=db.scalar(select(AdminUser.id)),
            decided_at=now(),
        )
        db.add(communication)
        db.commit()
        communication_id = communication.id

    corrected = client.post(
        f"/admin/payment-communications/{communication_id}/correction",
        json={"idempotency_key": "operations-correction-0001"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["status"] == "pending_review"

    client.cookies.clear()
    authenticate_client(client, owner_phone)
    requested = client.post(
        f"/gallery/{gallery_id}/reopening-requests",
        json={"idempotency_key": "operations-reopening-0001"},
    )
    repeated = client.post(
        f"/gallery/{gallery_id}/reopening-requests",
        json={"idempotency_key": "operations-reopening-0002"},
    )
    assert requested.status_code == repeated.status_code == 201
    assert requested.json()["id"] == repeated.json()["id"]
    reopening_id = requested.json()["id"]
    client.cookies.clear()
    authenticate_admin(client)
    listed = client.get("/admin/gallery-reopening-requests", params={"status": "pending"})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["requests"]] == [reopening_id]
    future = now() + timedelta(days=3)
    approved = client.post(
        f"/admin/gallery-reopening-requests/{reopening_id}/decision",
        json={"decision": "approved", "selection_expires_at": future.isoformat()},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    with SessionLocal() as db:
        persisted_deadline = db.get(DerivedGallery, gallery_id).selection_expires_at
        assert persisted_deadline.replace(tzinfo=UTC) == future

    client.cookies.clear()
    authenticate_client(client, owner_phone)
    assert client.post(
        f"/gallery/{gallery_id}/reopening-requests",
        json={"idempotency_key": "operations-reopening-after-approval"},
    ).status_code == 409


def test_private_media_scope_constraints_reject_cross_gallery_ownership() -> None:
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento Escopo")
        first_client = Client(full_name="Primeira", phone_e164="+5511555591011")
        second_client = Client(full_name="Segunda", phone_e164="+5511555591012")
        db.add_all([parent, first_client, second_client])
        db.flush()
        first_gallery = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=first_client.id,
            name="Privada A",
        )
        second_gallery = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=second_client.id,
            name="Privada B",
        )
        db.add_all([first_gallery, second_gallery])
        db.flush()
        public_folder = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Pública",
            position=0,
        )
        first_folder = PhotoFolder(
            parent_gallery_id=parent.id,
            derived_gallery_id=first_gallery.id,
            name="Privada A",
            position=0,
        )
        second_folder = PhotoFolder(
            parent_gallery_id=parent.id,
            derived_gallery_id=second_gallery.id,
            name="Privada B",
            position=0,
        )
        db.add_all([public_folder, first_folder, second_folder])
        db.flush()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(
                PhotoAsset(
                    parent_gallery_id=parent.id,
                    derived_gallery_id=second_gallery.id,
                    folder_id=first_folder.id,
                    filename="cross.jpg",
                    storage_key="private/cross.jpg",
                )
            )
            db.flush()


def test_financial_correction_and_reopening_constraints_are_idempotent() -> None:
    from app.auth import GalleryReopeningRequest, PaymentConfirmationCorrection

    with SessionLocal() as db:
        admin = AdminUser(
            email="constraints@markina.test",
            password_hash="synthetic",
            email_verified=True,
            totp_secret="synthetic",
        )
        owner = Client(full_name="Cliente Constraints", phone_e164="+5511555591013")
        parent = ParentGallery(name="Evento Constraints")
        db.add_all([admin, owner, parent])
        db.flush()
        gallery = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada Constraints",
            selection_expires_at=now() - timedelta(minutes=1),
        )
        db.add(gallery)
        db.flush()
        order = SaleOrder(
            derived_gallery_id=gallery.id,
            client_id=owner.id,
            payment_status="confirmed",
            total_cents=500,
        )
        db.add(order)
        db.flush()
        communication = PaymentCommunication(
            sale_order_id=order.id,
            client_id=owner.id,
            idempotency_key="constraints-source",
            status="confirmed",
        )
        db.add(communication)
        db.flush()
        db.add(
            PaymentConfirmationCorrection(
                payment_communication_id=communication.id,
                sale_order_id=order.id,
                actor_admin_id=admin.id,
                idempotency_key="constraints-correction",
                previous_communication_status="confirmed",
                previous_order_status="confirmed",
            )
        )
        db.add(
            GalleryReopeningRequest(
                derived_gallery_id=gallery.id,
                requested_by_client_id=owner.id,
                idempotency_key="constraints-reopening-a",
            )
        )
        db.flush()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(
                GalleryReopeningRequest(
                    derived_gallery_id=gallery.id,
                    requested_by_client_id=owner.id,
                    idempotency_key="constraints-reopening-b",
                )
            )
            db.flush()


def test_private_upload_reuses_media_pipeline_without_entering_public_facial_scope(
    client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    with SessionLocal() as db:
        owner = Client(full_name="Cliente Mídia Privada", phone_e164="+5511555591014")
        db.add(owner)
        db.commit()
        owner_phone = owner.phone_e164
    gallery_id, public_photo_id = create_gallery_for_client(client, owner)
    authenticate_admin(client)
    private_folder_id = UUID(
        client.post(
            f"/admin/derived-galleries/{gallery_id}/folders",
            json={"name": "Arquivos do dispositivo"},
        ).json()["id"]
    )
    private_photo_id = UUID(
        client.post(
            f"/admin/photo-folders/{private_folder_id}/photos",
            json={
                "filename": "PRIVADA_0002.jpg",
                "storage_key": f"private/{gallery_id}/private-0002.jpg",
            },
        ).json()["id"]
    )
    image = BytesIO()
    Image.new("RGB", (48, 32), color=(40, 80, 120)).save(image, format="JPEG")
    assert client.put(
        f"/admin/photo-assets/{private_photo_id}/source",
        content=image.getvalue(),
        headers={"content-type": "image/jpeg"},
    ).status_code == 202
    with SessionLocal() as db:
        generate_derivatives(db, db.get(PhotoAsset, private_photo_id))
    published = client.post(f"/admin/photo-folders/{private_folder_id}/publish", json={})
    assert published.status_code == 200
    assert published.json()["available_count"] == 1
    assert published.json()["status"] == "released"

    private_listing = client.get(f"/admin/derived-galleries/{gallery_id}/photos").json()
    assert {item["id"] for item in private_listing["photos"]} == {
        str(public_photo_id),
        str(private_photo_id),
    }
    private_item = next(
        item for item in private_listing["photos"] if item["id"] == str(private_photo_id)
    )
    assert private_item["ownership"] == "private"
    with SessionLocal() as db:
        parent_id = db.get(DerivedGallery, gallery_id).parent_gallery_id
    public_catalog = client.get(
        f"/admin/parent-galleries/{parent_id}/available-photos"
    ).json()
    assert {item["id"] for item in public_catalog["photos"]} == {str(public_photo_id)}
    assert client.get(f"/admin/parent-galleries/{parent_id}/facial-index").json()[
        "progress"
    ]["total"] == 1
    assert client.get(f"/admin/derived-galleries/{gallery_id}/facial-index").json()[
        "progress"
    ]["total"] == 1

    client.cookies.clear()
    authenticate_client(client, owner_phone)
    client_photos = client.get(f"/gallery/{gallery_id}/photos").json()["photos"]
    assert {item["id"] for item in client_photos} == {
        str(public_photo_id),
        str(private_photo_id),
    }
    assert client.post(
        f"/gallery/{gallery_id}/photos/{private_photo_id}/selection"
    ).status_code == 201
