from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select

from app.auth import (
    AuthSession,
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    engine,
    now,
    token_hash,
)
from app.commercial_projection import build_commercial_projections
from app.main import app
from tests.test_derived_galleries import (  # noqa: F401
    authenticate_admin,
    clean_database,
    set_test_global_pix,
)


@pytest.fixture
def client():
    set_test_global_pix()
    with TestClient(app) as browser:
        yield browser


def test_shortcuts_keep_all_pending_orders_first_and_isolate_client_and_gallery(client):
    authenticate_admin(client)
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento")
        other_parent = ParentGallery(name="Outro evento")
        owner = Client(full_name="Ana", phone_e164="+5511999912345")
        other = Client(full_name="Bia", phone_e164="+5511999912346")
        db.add_all([parent, other_parent, owner, other]); db.flush()
        deadline = now() + timedelta(days=3)
        gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=owner.id, name="Privada Ana", selection_expires_at=deadline)
        other_gallery = DerivedGallery(parent_gallery_id=other_parent.id, client_id=owner.id, name="Outro evento")
        db.add_all([gallery, other_gallery]); db.flush()
        db.add(DerivedGalleryMembership(parent_gallery_id=parent.id, derived_gallery_id=gallery.id, client_id=owner.id, status="active"))

        def purchase(target, buyer, status, days, count):
            order = SaleOrder(derived_gallery_id=target.id, client_id=buyer.id, total_cents=count * 700,
                              payment_status="confirmed" if status == "confirmed" else "pending",
                              frozen_at=now(), created_at=now() - timedelta(days=days))
            db.add(order); db.flush()
            for index in range(count):
                db.add(SaleOrderItem(sale_order_id=order.id, photo_asset_id_snapshot=uuid4(), filename_snapshot=f"{index}.jpg", unit_price_cents=700))
            if status:
                db.add(PaymentCommunication(sale_order_id=order.id, client_id=buyer.id, status=status,
                                           idempotency_key=str(uuid4()), created_at=order.created_at))
            db.flush()
            return str(order.id)

        oldest_pending = purchase(gallery, owner, "pending_review", 3, 1)
        newer_pending = purchase(gallery, owner, "pending_review", 2, 3)
        confirmed = purchase(gallery, owner, "confirmed", 1, 2)
        purchase(gallery, owner, None, 0, 1)
        purchase(other_gallery, owner, "pending_review", 0, 1)
        purchase(gallery, other, "pending_review", 0, 1)
        db.commit()
        gallery_id, owner_id, parent_id = gallery.id, owner.id, parent.id

    statements = []
    def count(*args):
        statements.append(args[2])
    with SessionLocal() as db:
        event.listen(engine, "before_cursor_execute", count)
        try:
            projection = build_commercial_projections(db, gallery_ids={gallery_id}, client_ids={owner_id})[(gallery_id, owner_id)]
        finally:
            event.remove(engine, "before_cursor_execute", count)
    assert len(statements) <= 5
    orders = projection.financial_orders
    assert [item["order_id"] for item in orders] == [newer_pending, oldest_pending, confirmed]
    assert [item["quantity"] for item in orders] == [3, 1, 2]
    assert [item["can_decide"] for item in orders] == [True, True, False]
    assert [item["can_correct"] for item in orders] == [False, False, True]
    public = client.get(f"/admin/parent-galleries/{parent_id}/clients").json()["clients"]
    public_card = next(item for item in public if item["client_id"] == str(owner_id))
    private_card = client.get(f"/admin/derived-galleries/{gallery_id}/members").json()["members"][0]
    assert public_card["financial_orders"] == private_card["financial_orders"] == orders
    assert public_card["selection_expires_at"] == private_card["selection_expires_at"]
    assert public_card["selection_expires_at"].startswith(deadline.date().isoformat())
    communication_id = orders[0]["id"]
    assert client.post(f"/admin/payment-communications/{communication_id}/decision", json={"decision": "confirmed"}).status_code == 200
    refreshed = client.get(f"/admin/derived-galleries/{gallery_id}/members").json()["members"][0]
    assert refreshed["financial_orders"][0]["order_id"] == oldest_pending
    assert refreshed["purchased_count"] == 5
    assert client.post(f"/admin/payment-communications/{communication_id}/correction", json={"idempotency_key": "shortcut-correction"}).status_code == 200
    corrected = client.get(f"/admin/derived-galleries/{gallery_id}/members").json()["members"][0]
    assert corrected["financial_orders"] == orders
    assert corrected["purchased_count"] == 2
    with SessionLocal() as db:
        assert db.get(DerivedGallery, gallery_id).selection_expires_at.replace(tzinfo=deadline.tzinfo) == deadline
        assert len(list(db.scalars(select(SaleOrder)))) == 6


def test_effective_deadlines_are_individual_nullable_and_read_only(client):
    authenticate_admin(client)
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento com prazos", selection_duration_days=14)
        db.add(parent); db.flush()
        dates = [now() + timedelta(days=3), now() - timedelta(days=1), None]
        ids = []
        for index, deadline in enumerate(dates):
            owner = Client(full_name=f"Pessoa {index}", phone_e164=f"+551188881234{index}")
            db.add(owner); db.flush()
            gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=owner.id, name=f"Privada {index}", selection_expires_at=deadline)
            db.add(gallery); db.flush()
            db.add_all([
                DerivedGalleryMembership(parent_gallery_id=parent.id, derived_gallery_id=gallery.id, client_id=owner.id, status="active"),
                ParentGalleryRegistration(parent_gallery_id=parent.id, client_id=owner.id, status="active"),
                AuthSession(token_hash=token_hash(f"deadline-{index}"), role="client", subject_id=owner.id, expires_at=now() + timedelta(days=1)),
            ])
            ids.append((gallery.id, owner.id))
        db.commit(); parent_id = parent.id
    public_cards = client.get(f"/admin/parent-galleries/{parent_id}/clients").json()["clients"]
    for index, (gallery_id, owner_id) in enumerate(ids):
        row = next(row for row in public_cards if row["client_id"] == str(owner_id))
        private = client.get(f"/admin/derived-galleries/{gallery_id}/members").json()["members"][0]
        assert row["selection_expires_at"] == private["selection_expires_at"]
        assert bool(row["selection_expires_at"]) == (dates[index] is not None)
    client.cookies.clear()
    for index, (gallery_id, owner_id) in enumerate(ids):
        client.cookies.set("markina_session", f"deadline-{index}")
        payload = client.get(f"/public-galleries/{parent_id}")
        assert payload.status_code == 200
        row = next(row for row in public_cards if row["client_id"] == str(owner_id))
        assert payload.json()["selection_expires_at"] == row["selection_expires_at"]
    with SessionLocal() as db:
        for index, (gallery_id, _) in enumerate(ids):
            stored = db.get(DerivedGallery, gallery_id).selection_expires_at
            assert (stored.replace(tzinfo=dates[index].tzinfo) if stored else None) == dates[index]
