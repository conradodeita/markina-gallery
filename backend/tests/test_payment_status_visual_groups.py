from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.auth import (
    Client,
    DerivedGallery,
    ParentGallery,
    PaymentCommunication,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    SaleOrder,
    SessionLocal,
    now,
)
from app.main import app
from tests.test_derived_galleries import (  # noqa: F401
    FIXTURE_TENANT_ID,
    authenticate_admin,
    clean_database,
    set_test_global_pix,
)


@pytest.fixture
def admin_browser(clean_database):  # noqa: F811
    set_test_global_pix()
    with TestClient(app) as browser:
        authenticate_admin(browser)
        yield browser


def test_financial_status_groups_use_priority_fifo_and_delivery_field(admin_browser):
    reference = now()
    with SessionLocal() as db:
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Evento")
        db.add(parent)
        db.flush()
        clients = {}

        def add_order(name, status, days_old, *, album_url=None, overdue=False):
            client = clients.get(name)
            if client is None:
                client = Client(tenant_id=FIXTURE_TENANT_ID, full_name=name, phone_e164=f"+55119999{len(clients):06d}")
                clients[name] = client
                db.add(client)
                db.flush()
            gallery_parent = parent
            if name in {"Mixada", "Compra adicional"}:
                gallery_parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name=f"Evento {name}")
                db.add(gallery_parent)
                db.flush()
            gallery = DerivedGallery(
                tenant_id=FIXTURE_TENANT_ID,
                parent_gallery_id=gallery_parent.id,
                client_id=client.id,
                name=f"Galeria {name}",
                selection_expires_at=(reference - timedelta(days=1)) if overdue else None,
            )
            db.add(gallery)
            db.flush()
            created_at = reference - timedelta(days=days_old)
            payment_status = "cancelled" if status == "not_found" else (
                "confirmed" if status in {"confirmed", "confirmed_undelivered"} else "pending"
            )
            order = SaleOrder(
                tenant_id=FIXTURE_TENANT_ID,
                derived_gallery_id=gallery.id,
                client_id=client.id,
                payment_status=payment_status,
                total_cents=700,
                created_at=created_at,
                confirmed_at=created_at if payment_status == "confirmed" else None,
                delivery_album_url=album_url,
            )
            db.add(order)
            db.flush()
            if status == "reported":
                db.add(PaymentCommunication(
                    tenant_id=FIXTURE_TENANT_ID,
                    sale_order_id=order.id,
                    client_id=client.id,
                    idempotency_key=f"reported-{uuid4()}",
                    status="pending_review",
                    created_at=created_at,
                ))
            db.flush()
            return order

        add_order("Comunicada antiga", "reported", 10)
        add_order("Comunicada recente", "reported", 2)
        add_order("Confirmada", "confirmed", 8, album_url="https://photos.app.goo.gl/Synthetic")
        add_order("Confirmada sem link", "confirmed_undelivered", 7)
        add_order("Aguardando", "awaiting_payment", 6)
        add_order("Não localizado", "not_found", 5)
        add_order("Expirada", "overdue", 4, overdue=True)
        add_order("Mixada", "confirmed", 20, album_url="https://photos.app.goo.gl/Older")
        add_order("Mixada", "reported", 3)
        db.commit()

    response = admin_browser.get("/admin/payment-communications", params={"limit": 2})
    assert response.status_code == 200, response.text
    first = response.json()
    groups = list(first["groups"])
    while first["page"]["next_cursor"]:
        response = admin_browser.get("/admin/payment-communications", params={
            "limit": 2,
            "cursor": first["page"]["next_cursor"],
        })
        assert response.status_code == 200, response.text
        first = response.json()
        groups.extend(first["groups"])

    assert [(group["client"]["name"], group["financial_status"]) for group in groups] == [
        ("Comunicada antiga", "reported"),
        ("Mixada", "reported"),
        ("Comunicada recente", "reported"),
        ("Confirmada", "confirmed"),
        ("Confirmada sem link", "confirmed_undelivered"),
        ("Aguardando", "awaiting_payment"),
        ("Não localizado", "not_found"),
        ("Expirada", "overdue"),
    ]
    mixed = next(group for group in groups if group["client"]["name"] == "Mixada")
    assert {order["financial_status"] for order in mixed["orders"]} == {"reported", "confirmed"}
    assert all(order["financial_status"] == "confirmed_undelivered" for order in groups[4]["orders"])
    assert first["summary"]["confirmed_orders"] == 3

    filtered = admin_browser.get("/admin/payment-communications", params={
        "financial_status": "confirmed_undelivered",
    })
    assert filtered.status_code == 200, filtered.text
    filtered_payload = filtered.json()
    assert [group["client"]["name"] for group in filtered_payload["groups"]] == ["Confirmada sem link"]
    assert filtered_payload["groups"][0]["orders"][0]["delivery"]["album_url"] is None


def test_open_selection_is_only_returned_when_financial_filter_is_all(admin_browser):
    with SessionLocal() as db:
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Evento Carrinho", fixed_unit_price_cents=700)
        client = Client(tenant_id=FIXTURE_TENANT_ID, full_name="No carrinho", phone_e164="+5511999876543")
        db.add_all([parent, client])
        db.flush()
        gallery = DerivedGallery(
                tenant_id=FIXTURE_TENANT_ID,
            parent_gallery_id=parent.id,
            client_id=client.id,
            name="Galeria carrinho",
        )
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(
            tenant_id=FIXTURE_TENANT_ID,
            parent_gallery_id=parent.id,
            derived_gallery_id=gallery.id,
            name="Pasta selecionada",
            status="ready",
            released_at=now(),
        )
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            tenant_id=FIXTURE_TENANT_ID,
            parent_gallery_id=parent.id,
            derived_gallery_id=gallery.id,
            folder_id=folder.id,
            filename="foto.jpg",
            storage_key="payment-status-carts/foto.jpg",
            available=True,
        )
        db.add(photo)
        db.flush()
        db.add(PhotoSelection(
            tenant_id=FIXTURE_TENANT_ID,
            derived_gallery_id=gallery.id,
            photo_asset_id=photo.id,
            client_id=client.id,
        ))
        db.commit()

    all_statuses = admin_browser.get("/admin/payment-communications")
    assert all_statuses.status_code == 200, all_statuses.text
    assert [row["client"]["name"] for row in all_statuses.json()["selections_without_order"]] == ["No carrinho"]

    awaiting_only = admin_browser.get(
        "/admin/payment-communications",
        params={"financial_status": "awaiting_payment"},
    )
    assert awaiting_only.status_code == 200, awaiting_only.text
    assert awaiting_only.json()["selections_without_order"] == []
