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
    GalleryAccess,
    ParentGallery,
    PhotoAsset,
    PhotoSelection,
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
    secret = pyotp.random_base32()
    with SessionLocal() as db:
        db.add(
            AdminUser(
                email="foto@markina.test",
                password_hash=password_hasher.hash("senha-segura"),
                email_verified=True,
                totp_secret=secret,
            )
        )
        db.commit()
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
        assert db.scalar(
            select(GalleryAccess).where(
                GalleryAccess.gallery_id == gallery_id, GalleryAccess.client_id == client_id
            )
        )
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
        db.flush()
        gallery_access = GalleryAccess(client_id=person.id, gallery_id=UUID("00000000-0000-0000-0000-000000000001"))
        db.add(gallery_access)
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


def test_client_interactions_are_private_reversible_and_audited(client: TestClient):
    with SessionLocal() as db:
        person = Client(full_name="Cliente", phone_e164="+5511666666666")
        db.add(person)
        db.commit()
    gallery_id, photo_id = create_gallery_for_client(client, person)
    authenticate_client(client, person.phone_e164)
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/selection").status_code == 201
    assert client.post(f"/gallery/{gallery_id}/photos/{photo_id}/favorite").status_code == 201
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
