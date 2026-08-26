from datetime import timedelta
from uuid import UUID

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import (
    AdminUser,
    AuditEvent,
    AuthChallenge,
    Base,
    Client,
    DerivedGallery,
    DerivedGalleryPhoto,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
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


def create_gallery_for_client(client: TestClient, person: Client, *, expires=False) -> tuple[UUID, UUID]:
    authenticate_admin(client)
    parent_id = UUID(client.post("/admin/parent-galleries", json={"name": "Evento"}).json()["id"])
    photo_id = UUID(
        client.post(
            f"/admin/parent-galleries/{parent_id}/photos",
            json={"filename": "IMG_0001.jpg", "storage_key": "events/one/img-0001.jpg"},
        ).json()["id"]
    )
    payload = {
        "parent_gallery_id": str(parent_id),
        "client_id": str(person.id),
        "name": "Fotos privadas",
        "photo_ids": [str(photo_id)],
        "favorites_enabled": True,
        "comments_enabled": True,
    }
    if expires:
        payload["selection_expires_at"] = (now() - timedelta(minutes=1)).isoformat()
    gallery_id = UUID(client.post("/admin/derived-galleries", json=payload).json()["id"])
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
    photo_id = UUID(
        client.post(
            f"/admin/parent-galleries/{parent_id}/photos",
            json={"filename": "IMG_0001.jpg", "storage_key": "events/ana/img-0001.jpg"},
        ).json()["id"]
    )
    response = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(client_id),
            "name": "Fotos da Cliente",
            "photo_ids": [str(photo_id)],
            "favorites_enabled": True,
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
    foreign_photo = client.post(
        f"/admin/parent-galleries/{second_parent}/photos",
        json={"filename": "IMG_0002.jpg", "storage_key": "events/b/img-0002.jpg"},
    ).json()["id"]
    response = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(first_parent),
            "client_id": str(client_id),
            "name": "Fotos privadas",
            "photo_ids": [foreign_photo],
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
    photo = client.post(
        f"/admin/parent-galleries/{parent_id}/photos",
        json={"filename": "operacional.jpg", "storage_key": "operacional/foto.jpg"},
    )
    assert photo.status_code == 201
    assert client.get("/admin/clients").json()["clients"] == [
        {"id": created_client.json()["id"], "name": "Cliente Operacional"}
    ]
    assert client.get("/admin/parent-galleries").json()["parent_galleries"][0]["id"] == parent_id
    assert client.get(f"/admin/parent-galleries/{parent_id}/photos").json()["photos"] == [
        {"id": photo.json()["id"], "name": "operacional.jpg"}
    ]
    assert client.get(f"/admin/photo-assets/{photo.json()['id']}/media-status").json() == {
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
        bought = PhotoAsset(
            parent_gallery_id=parent.id, filename="comprada.jpg", storage_key="event/comprada.jpg"
        )
        selected = PhotoAsset(
            parent_gallery_id=parent.id, filename="selecionada.jpg", storage_key="event/selecionada.jpg"
        )
        other = PhotoAsset(
            parent_gallery_id=parent.id, filename="outra.jpg", storage_key="event/outra.jpg"
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
