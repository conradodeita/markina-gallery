from datetime import timedelta
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
    Client,
    DerivedGallery,
    DerivedGalleryPhoto,
    MediaDerivative,
    MediaJob,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    PhotoView,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    engine,
    now,
    password_hasher,
    token_hash,
)
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
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
    payload = {
        "parent_gallery_id": str(parent_id),
        "client_id": str(person.id),
        "name": "Fotos privadas",
        "photo_ids": [],
        "favorites_enabled": True,
        "comments_enabled": True,
    }
    if expires:
        payload["selection_expires_at"] = (now() - timedelta(minutes=1)).isoformat()
    gallery_id = UUID(client.post("/admin/derived-galleries", json=payload).json()["id"])
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": [str(gallery_id)]}
    ).status_code == 200
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
    response = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(client_id),
            "name": "Fotos da Cliente",
            "photo_ids": [],
            "favorites_enabled": True,
        },
    )
    assert response.status_code == 201
    gallery_id = UUID(response.json()["id"])
    assert client.post(
        f"/admin/photo-folders/{folder_id}/release", json={"gallery_ids": [str(gallery_id)]}
    ).status_code == 200
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
    assert client.get("/library").json() == {"galleries": []}


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
        "sales_configuration": False,
        "visual_customization": False,
        "folder_management": True,
        "client_links": True,
    }
    assert "storage_key" not in editor.text
    assert client.get(f"/admin/parent-galleries/{parent_id}/sales").json()["available"] is False
    assert client.get(f"/admin/parent-galleries/{parent_id}/details").json()["available"] is False
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
    foreign_gallery = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(second_parent),
            "client_id": str(owner_id),
            "name": "Destino incorreto",
            "photo_ids": [],
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
    assert client.post("/auth/client/verify", json={"challenge_id": old, "code": "123456"}).status_code == 401


def test_unlisted_source_link_registers_client_without_exposing_photos(client: TestClient):
    with SessionLocal() as db:
        owner = Client(full_name="Cliente", phone_e164="+5511555555555")
        parent = ParentGallery(name="Evento coletivo")
        db.add_all([owner, parent])
        db.commit()
    challenge = client.post("/auth/client/challenge", json={"full_name": owner.full_name, "phone": owner.phone_e164, "parent_gallery_id": str(parent.id)}).json()["challenge_id"]
    with SessionLocal() as db:
        db.get(AuthChallenge, UUID(challenge)).secret_hash = token_hash("123456")
        db.commit()
    assert client.post("/auth/client/verify", json={"challenge_id": challenge, "code": "123456"}).json() == {"destination": "/library?registration=pending"}
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
        person = Client(full_name="Responsável", phone_e164="+5511333333333")
        db.add(person)
        db.commit()
    gallery_id, _ = create_gallery_for_client(client, person, expires=True)
    authenticate_admin(client)
    frozen = client.get("/admin/derived-galleries?tab=frozen&query=Responsável")
    assert frozen.status_code == 200
    assert frozen.json()["total"] == 1
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
    assert client.get("/library").json()["galleries"] == [{
        "id": str(gallery_id),
        "name": "Fotos da família",
        "message": "",
        "selection_expires_at": None,
        "folders": [{"id": str(folder_id), "name": "Rodada 1"}],
    }]


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
    derived_gallery_id = UUID(
        client.post(
            "/admin/derived-galleries",
            json={
                "parent_gallery_id": str(parent_id),
                "client_id": str(client_id),
                "name": "Histórico da cliente sintética",
                "photo_ids": [],
            },
        ).json()["id"]
    )
    photo_id = UUID(
        client.post(
            f"/admin/photo-folders/{first_folder_id}/photos",
            json={"filename": "TESTE_001.jpg", "storage_key": "synthetic/round-1/TESTE_001.jpg"},
        ).json()["id"]
    )
    released = client.post(
        f"/admin/photo-folders/{first_folder_id}/release", json={"gallery_ids": [str(derived_gallery_id)]}
    )
    assert released.status_code == 200
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
            "photo_count": 0,
            "preview_url": None,
            "released_at": None,
        },
    ]

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


def test_admin_can_create_empty_private_gallery_before_releasing_a_folder(client: TestClient) -> None:
    authenticate_admin(client)
    client_id = UUID(client.post("/admin/clients", json={"full_name": "Responsável", "phone_e164": "+5511999997777"}).json()["id"])
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento"}).json()["id"])
    created = client.post("/admin/derived-galleries", json={
        "parent_gallery_id": str(parent_id), "client_id": str(client_id), "name": "Histórico da família", "photo_ids": []
    })
    assert created.status_code == 201


def test_admin_deletes_only_empty_folder_and_gallery_without_history(client: TestClient) -> None:
    authenticate_admin(client)
    owner_id = UUID(client.post("/admin/clients", json={"full_name": "Responsável", "phone_e164": "+5511999996666"}).json()["id"])
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento seguro"}).json()["id"])
    empty_folder_id = UUID(client.post(f"/admin/parent-galleries/{parent_id}/folders", json={"name": "Vazia"}).json()["id"])
    assert client.delete(f"/admin/photo-folders/{empty_folder_id}").status_code == 204

    gallery_id = UUID(client.post("/admin/derived-galleries", json={"parent_gallery_id": str(parent_id), "client_id": str(owner_id), "name": "Sem histórico", "photo_ids": []}).json()["id"])
    assert client.delete(f"/admin/derived-galleries/{gallery_id}").status_code == 204

    protected_gallery_id = UUID(client.post("/admin/derived-galleries", json={"parent_gallery_id": str(parent_id), "client_id": str(owner_id), "name": "Com histórico", "photo_ids": []}).json()["id"])
    with SessionLocal() as db:
        folder = PhotoFolder(
            parent_gallery_id=parent_id,
            name="Preservadas",
            status="released",
            released_at=now(),
        )
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent_id,
            folder_id=folder.id,
            filename="preservada.jpg",
            storage_key="event/preservada.jpg",
        )
        db.add(photo)
        db.flush()
        db.add(DerivedGalleryPhoto(derived_gallery_id=protected_gallery_id, photo_asset_id=photo.id))
        db.commit()
    assert client.delete(f"/admin/derived-galleries/{protected_gallery_id}").status_code == 409


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
    gallery_id = UUID(
        client.post(
            "/admin/derived-galleries",
            json={"parent_gallery_id": str(parent_id), "client_id": str(client_id), "name": "Ana", "photo_ids": []},
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
    assert "compra confirmada" in blocked.json()["detail"]
    assert client.delete(f"/admin/photo-folders/{second_folder}/photos/{second_photo}").status_code == 204


def test_photo_bulk_deletion_reports_confirmed_items(client: TestClient) -> None:
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento em lote"}).json()["id"])
    folder_id, first_photo = create_folder_photo(client, parent_id, storage_key="evento/lote-1.jpg")
    second_photo = UUID(client.post(f"/admin/photo-folders/{folder_id}/photos", json={"filename": "lote-2.jpg", "storage_key": "evento/lote-2.jpg"}).json()["id"])
    client_id = UUID(client.post("/admin/clients", json={"full_name": "Cliente Lote", "phone_e164": "+5511999999988"}).json()["id"])
    gallery_id = UUID(client.post("/admin/derived-galleries", json={"parent_gallery_id": str(parent_id), "client_id": str(client_id), "name": "Lote", "photo_ids": []}).json()["id"])
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
    payload = {"parent_gallery_id": str(parent_id), "client_id": str(ana_id), "name": "Fotos da Ana", "photo_ids": []}
    first = client.post("/admin/derived-galleries", json=payload)
    second = client.post("/admin/derived-galleries", json=payload)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    summary = client.get(f"/admin/parent-galleries/{parent_id}/summary").json()
    assert summary["counts"] == {"folders": 0, "photos": 0, "clients": 1}
    assert summary["clients"] == [
        {"client_id": str(ana_id), "name": "Ana", "phone": "+5511999999901", "registration_status": None, "derived_gallery_id": first.json()["id"]}
    ]


def test_admin_deletes_only_empty_parent_gallery(client: TestClient) -> None:
    authenticate_admin(client)
    empty_id = UUID(client.post("/admin/parent-galleries", json={"name": "Rascunho"}).json()["id"])
    assert client.delete(f"/admin/parent-galleries/{empty_id}").status_code == 204


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

    created = client.post("/admin/clients", json={"full_name": "Cliente Fluxo", "phone_e164": "+5511999994321"})
    assert created.status_code == 201
    client_id = UUID(created.json()["id"])
    assert client.get("/admin/clients?query=99994321").json()["clients"][0]["id"] == str(client_id)
    private_payload = {"parent_gallery_id": str(parent_id), "client_id": str(client_id), "name": "Galeria da cliente", "photo_ids": []}
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
    blocked = client.delete(f"/admin/parent-galleries/{occupied_id}")
    assert blocked.status_code == 409
    assert "pastas, fotos ou responsáveis" in blocked.json()["detail"]
