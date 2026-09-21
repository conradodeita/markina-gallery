from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.schema import CreateSchema

from app.auth import (
    AdminUser,
    AuthSession,
    Base,
    Client,
    DerivedGallery,
    GlobalPixSettings,
    ParentGallery,
    PaymentCommunication,
    PaymentGroup,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    PriceRule,
    SaleOrder,
    SessionLocal,
    engine,
    now,
    token_hash,
)
from app.checkout import CheckoutError
from app.main import app
from app.unified_checkout import cart_payload, prepare_group, report_group
from tests.test_derived_galleries import set_test_global_pix


@pytest.fixture(autouse=True)
def isolated_cart_database():
    if engine.dialect.name == "postgresql":
        assert engine.url.host == "127.0.0.1" and engine.url.port == 55458
        assert engine.url.database == "markina_unified_test"
        schema = "cart_" + uuid4().hex
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine.update_execution_options(schema_translate_map={None: schema})
        Base.metadata.create_all(engine)
    else:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            Base.metadata.drop_all(connection)
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
        Base.metadata.create_all(engine)
    yield


def setup_cart():
    set_test_global_pix()
    with SessionLocal() as db:
        owner = Client(full_name="Cliente", phone_e164="+5511999988000")
        other = Client(full_name="Outra", phone_e164="+5511999988001")
        db.add_all([owner, other])
        db.flush()
        gallery_ids = []
        for number, quantity in enumerate((2, 1)):
            parent = ParentGallery(name=f"Galeria {number + 1}", fixed_unit_price_cents=700)
            db.add(parent)
            db.flush()
            db.add(
                PriceRule(
                    parent_gallery_id=parent.id,
                    minimum_quantity=1,
                    maximum_quantity=None,
                    unit_price_cents=700,
                )
            )
            gallery = DerivedGallery(
                parent_gallery_id=parent.id, client_id=owner.id, name=f"Privada {number}"
            )
            db.add(gallery)
            db.flush()
            gallery_ids.append(gallery.id)
            for photo_number in range(quantity):
                folder = PhotoFolder(
                    parent_gallery_id=parent.id,
                    derived_gallery_id=gallery.id,
                    name=f"Pasta {photo_number}",
                    status="released",
                    position=photo_number,
                )
                db.add(folder)
                db.flush()
                photo = PhotoAsset(
                    parent_gallery_id=parent.id,
                    derived_gallery_id=gallery.id,
                    folder_id=folder.id,
                    filename=f"foto-{photo_number}.jpg",
                    storage_key=f"synthetic/{uuid4()}.jpg",
                )
                db.add(photo)
                db.flush()
                db.add(
                    PhotoSelection(
                        derived_gallery_id=gallery.id, client_id=owner.id, photo_asset_id=photo.id
                    )
                )
        db.add(
            AuthSession(
                subject_id=owner.id,
                role="client",
                token_hash=token_hash("cart-test"),
                expires_at=now() + timedelta(hours=1),
            )
        )
        db.commit()
        return owner.id, other.id, gallery_ids


def test_global_cart_projects_folders_prices_and_identity():
    owner_id, other_id, gallery_ids = setup_cart()
    with SessionLocal() as db:
        payload = cart_payload(db, db.get(Client, owner_id))
        assert payload["quantity"] == 3 and payload["total_cents"] == 2100
        assert sorted(group["total_cents"] for group in payload["groups"]) == [700, 1400]
        assert {item["folder_name"] for group in payload["groups"] for item in group["items"]} == {
            "Pasta 0",
            "Pasta 1",
        }
        assert cart_payload(db, db.get(Client, other_id))["groups"] == []
        db.get(DerivedGallery, gallery_ids[0]).selection_expires_at = now() - timedelta(days=1)
        db.flush()
        payload = cart_payload(db, db.get(Client, owner_id))
        assert payload["quantity"] == 3 and payload["total_cents"] is None
        assert not payload["can_prepare"]


def test_prepare_report_preserves_selection_and_is_idempotent():
    owner_id, _, _ = setup_cart()
    browser = TestClient(app)
    browser.cookies.set("markina_session", "cart-test")
    first = browser.post("/library/cart/prepare")
    assert first.status_code == 200, first.text
    payment = first.json()["payment"]
    assert browser.post("/library/cart/prepare").json()["payment"]["id"] == payment["id"]
    assert browser.get("/library/cart").json()["quantity"] == 3
    result = browser.post(
        f"/library/payments/{payment['id']}/report",
        json={"revision": payment["revision"], "idempotency_key": "report"},
    )
    assert result.status_code == 200, result.text
    assert (
        browser.post(
            f"/library/payments/{payment['id']}/report",
            json={"revision": payment["revision"], "idempotency_key": "report"},
        ).json()
        == result.json()
    )
    assert browser.get("/library/cart").json()["quantity"] == 0
    with SessionLocal() as db:
        assert db.scalar(select(func.count(PaymentCommunication.id))) == 1
        assert db.scalar(select(func.count(PaymentGroup.id))) == 1
        orders = list(db.scalars(select(SaleOrder).where(SaleOrder.client_id == owner_id)))
        assert len(orders) == 2 and all(order.frozen_at for order in orders)
        assert sum(order.total_cents for order in orders) == 2100


def test_stale_revision_and_wrong_identity_do_not_freeze():
    owner_id, other_id, _ = setup_cart()
    with SessionLocal() as db:
        owner = db.get(Client, owner_id)
        group = prepare_group(db, owner)
        db.commit()
        with pytest.raises(CheckoutError):
            report_group(db, db.get(Client, other_id), group.id, group.revision, "wrong")
        db.rollback()
        selection = db.scalar(select(PhotoSelection).where(PhotoSelection.client_id == owner_id))
        db.delete(selection)
        db.commit()
        with pytest.raises(CheckoutError, match="carrinho mudou"):
            report_group(db, owner, group.id, group.revision, "stale")
        db.rollback()
        assert all(order.frozen_at is None for order in db.scalars(select(SaleOrder)))
        assert db.scalar(select(func.count(PhotoSelection.id))) == 2


def test_group_keeps_pix_snapshot_when_global_changes():
    owner_id, _, _ = setup_cart()
    with SessionLocal() as db:
        owner = db.get(Client, owner_id)
        group = prepare_group(db, owner)
        original = group.pix_copy_paste_snapshot
        db.commit()
        settings = db.scalar(select(GlobalPixSettings))
        settings.status = "unconfigured"
        db.commit()
        assert prepare_group(db, owner).pix_copy_paste_snapshot == original
        db.commit()
        report_group(db, owner, group.id, group.revision, "kept")
        db.commit()


def test_admin_scope_history_decisions_and_correction(monkeypatch):
    from app.auth import NotificationEvent
    from app.messaging import SandboxWhatsAppProvider, WhatsAppDeliveryError
    from app.notification_delivery import process_next_notification

    monkeypatch.setenv("WHATSAPP_PHOTOGRAPHER_PHONE_E164", "+5511999999999")
    _, _, _ = setup_cart()
    browser = TestClient(app)
    browser.cookies.set("markina_session", "cart-test")
    payment = browser.post("/library/cart/prepare").json()["payment"]
    communication = browser.post(
        f"/library/payments/{payment['id']}/report",
        json={"revision": payment["revision"], "idempotency_key": "report"},
    ).json()
    history = browser.get("/library/purchases").json()
    assert history["orders"] == [] and len(history["payment_groups"]) == 1
    assert len(history["payment_groups"][0]["orders"]) == 2
    assert history["payment_groups"][0]["total_cents"] == 2100
    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser))
        db.add(
            AuthSession(
                subject_id=admin.id,
                role="admin",
                token_hash=token_hash("admin-cart-test"),
                expires_at=now() + timedelta(hours=1),
            )
        )
        db.commit()
    browser.cookies.set("markina_session", "admin-cart-test")
    dashboard = browser.get("/admin/payment-communications").json()
    assert dashboard["summary"]["total_cents"] == 2100
    with SessionLocal() as db:
        orders = list(db.scalars(select(SaleOrder)))
        gallery_id = orders[0].derived_gallery_id
        parent_id = orders[0].parent_gallery_id_snapshot
        subtotal = orders[0].total_cents
    detail = browser.get(f"/admin/derived-galleries/{gallery_id}/orders").json()
    assert detail["totals"]["amount_cents"] == subtotal
    assert detail["orders"][0]["payment_group"]["total_cents"] == 2100
    filtered = browser.get(f"/admin/payment-communications?parent_gallery_id={parent_id}").json()
    assert filtered["summary"]["total_cents"] == subtotal
    scope = filtered["groups"][0]["orders"][0]["communications"][0]["payment_group"]
    assert scope["total_cents"] == 2100 and len(scope["galleries"]) == 2
    path = f"/admin/payment-communications/{communication['id']}"
    assert browser.post(path + "/decision", json={"decision": "confirmed"}).status_code == 409
    payload = {"decision": "confirmed", "payment_group_id": payment["id"]}
    assert browser.post(path + "/decision", json=payload).status_code == 200
    assert browser.post(path + "/decision", json=payload).status_code == 200
    with SessionLocal() as db:
        assert {order.payment_status for order in db.scalars(select(SaleOrder))} == {"confirmed"}
        assert db.scalar(select(func.count(NotificationEvent.id))) == 2
        event = db.scalar(
            select(NotificationEvent).where(NotificationEvent.event_type == "payment_confirmed")
        )
        assert event.target_path == f"/library/purchases#payment-{payment['id']}"

    class FailedProvider(SandboxWhatsAppProvider):
        def send_transactional(self, *_args, **_kwargs):
            raise WhatsAppDeliveryError("Falha sintética", transient=False)

    while process_next_notification("whatsapp", whatsapp_provider=FailedProvider()):
        pass
    with SessionLocal() as db:
        assert {order.payment_status for order in db.scalars(select(SaleOrder))} == {"confirmed"}
    correction = {"idempotency_key": "correct-group-test", "payment_group_id": payment["id"]}
    assert browser.post(path + "/correction", json=correction).status_code == 200
    assert browser.post(path + "/correction", json=correction).status_code == 200
    with SessionLocal() as db:
        assert {order.payment_status for order in db.scalars(select(SaleOrder))} == {"pending"}
        assert db.scalar(select(func.count(NotificationEvent.id))) == 2
    payload["decision"] = "refused"
    assert browser.post(path + "/decision", json=payload).status_code == 200
    with SessionLocal() as db:
        assert {order.payment_status for order in db.scalars(select(SaleOrder))} == {"cancelled"}
        assert db.scalar(select(func.count(NotificationEvent.id))) == 3
    browser.cookies.set("markina_session", "cart-test")
    assert (
        browser.get("/library/purchases").json()["payment_groups"][0]["commercial_state"]
        == "cancelled"
    )


def test_legacy_endpoints_cannot_change_group_and_expired_selection_can_be_removed():
    _, _, gallery_ids = setup_cart()
    browser = TestClient(app)
    browser.cookies.set("markina_session", "cart-test")
    payment = browser.post("/library/cart/prepare").json()["payment"]
    with SessionLocal() as db:
        order = db.scalar(select(SaleOrder).where(SaleOrder.derived_gallery_id == gallery_ids[0]))
        order_id = order.id
    detail = browser.get(f"/gallery/{gallery_ids[0]}/orders/{order_id}")
    assert detail.status_code == 200 and detail.json()["pix"] is None
    assert detail.json()["payment_group_id"] == payment["id"]
    assert (
        browser.post(
            f"/gallery/{gallery_ids[0]}/orders/{order_id}/payment-communications",
            json={"idempotency_key": "legacy-endpoint-attempt"},
        ).status_code
        == 409
    )
    with SessionLocal() as db:
        db.get(DerivedGallery, gallery_ids[0]).selection_expires_at = now() - timedelta(days=1)
        db.commit()
    removed = browser.delete(f"/library/cart/{gallery_ids[0]}")
    assert removed.status_code == 200, removed.text
    assert removed.json()["quantity"] == 1
    with SessionLocal() as db:
        assert db.get(SaleOrder, order_id) is None
    assert (
        browser.post(
            f"/library/payments/{payment['id']}/report",
            json={"revision": payment["revision"], "idempotency_key": "stale"},
        ).status_code
        == 409
    )
    updated = browser.post("/library/cart/prepare")
    assert updated.status_code == 200, updated.text
    assert updated.json()["payment"]["total_cents"] == 700


def test_failure_during_report_rolls_back_all_orders(monkeypatch):
    owner_id, _, _ = setup_cart()
    with SessionLocal() as db:
        owner = db.get(Client, owner_id)
        group = prepare_group(db, owner)
        db.commit()

        def fail(*args, **kwargs):
            raise RuntimeError("synthetic event failure")

        monkeypatch.setattr("app.unified_checkout.record_payment_event", fail)
        with pytest.raises(RuntimeError, match="synthetic"):
            report_group(db, owner, group.id, group.revision, "fail")
        db.rollback()
        assert db.scalar(select(func.count(PhotoSelection.id))) == 3
        assert db.scalar(select(func.count(PaymentCommunication.id))) == 0
        assert all(order.frozen_at is None for order in db.scalars(select(SaleOrder)))


@pytest.mark.skipif(
    engine.dialect.name != "postgresql", reason="Concorrência exige PostgreSQL isolado"
)
def test_concurrent_preparation_and_report_on_postgres():
    assert engine.url.host == "127.0.0.1" and engine.url.port == 55458
    owner_id, _, _ = setup_cart()
    barrier = Barrier(2)

    def prepare():
        with SessionLocal() as db:
            owner = db.get(Client, owner_id)
            barrier.wait(timeout=15)
            group = prepare_group(db, owner)
            db.commit()
            return group.id, group.revision

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(prepare) for _ in range(2)]
        prepared = [future.result(timeout=30) for future in futures]
    assert prepared[0] == prepared[1]
    group_id, revision = prepared[0]
    barrier = Barrier(2)

    def report():
        with SessionLocal() as db:
            owner = db.get(Client, owner_id)
            barrier.wait(timeout=15)
            communication = report_group(db, owner, group_id, revision, "same-request")
            db.commit()
            return communication.id

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(report) for _ in range(2)]
        reported = [future.result(timeout=30) for future in futures]
    assert reported[0] == reported[1]
    with SessionLocal() as db:
        assert db.scalar(select(func.count(PaymentGroup.id))) == 1
        assert db.scalar(select(func.count(SaleOrder.id))) == 2
        assert db.scalar(select(func.count(PaymentCommunication.id))) == 1
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0


@pytest.mark.skipif(
    engine.dialect.name != "postgresql", reason="Concorrência exige PostgreSQL isolado"
)
def test_concurrent_selection_and_report_on_postgres():
    from app.checkout import lock_client_commerce

    assert engine.url.host == "127.0.0.1" and engine.url.port == 55458
    owner_id, _, gallery_ids = setup_cart()
    with SessionLocal() as db:
        group = prepare_group(db, db.get(Client, owner_id))
        db.commit()
        group_id, revision = group.id, group.revision
    barrier = Barrier(2)

    def remove():
        with SessionLocal() as db:
            barrier.wait(timeout=15)
            lock_client_commerce(db, gallery_id=gallery_ids[0], client_id=owner_id)
            selection = db.scalar(
                select(PhotoSelection).where(PhotoSelection.client_id == owner_id)
            )
            if selection:
                db.delete(selection)
            db.commit()

    def report():
        with SessionLocal() as db:
            barrier.wait(timeout=15)
            try:
                report_group(db, db.get(Client, owner_id), group_id, revision, "racing")
                db.commit()
                return True
            except CheckoutError:
                db.rollback()
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        removal, communication = pool.submit(remove), pool.submit(report)
        removal.result(timeout=30)
        reported = communication.result(timeout=30)
    with SessionLocal() as db:
        orders = list(db.scalars(select(SaleOrder)))
        assert all(bool(order.frozen_at) == reported for order in orders)
        assert db.scalar(select(func.count(PhotoSelection.id))) == (0 if reported else 2)


def test_invalid_price_keeps_authorized_photos_and_blocks_partial_total():
    from sqlalchemy import delete

    owner_id, _, gallery_ids = setup_cart()
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_ids[0])
        db.execute(
            delete(PriceRule).where(PriceRule.parent_gallery_id == gallery.parent_gallery_id)
        )
        db.commit()
        cart = cart_payload(db, db.get(Client, owner_id))
        assert cart["quantity"] == 3 and cart["total_cents"] is None
        assert sum(len(group["items"]) for group in cart["groups"]) == 3
        with pytest.raises(CheckoutError):
            prepare_group(db, db.get(Client, owner_id))


def test_missing_and_fixed_amount_pix_do_not_create_partial_drafts():
    from app.pix import _crc16_ccitt, _emv_field
    from app.unified_checkout import _check_amount

    owner_id, _, _ = setup_cart()
    with SessionLocal() as db:
        settings = db.scalar(select(GlobalPixSettings))
        original = settings.copy_paste
        prefix = original[:-8] + _emv_field("54", "21.00") + "6304"
        fixed = prefix + _crc16_ccitt(prefix)
        _check_amount(fixed, 2100)
        with pytest.raises(CheckoutError, match="valor fixo"):
            _check_amount(fixed, 700)
        prefix = original[:-8] + _emv_field("54", "NaN") + "6304"
        with pytest.raises(CheckoutError):
            _check_amount(prefix + _crc16_ccitt(prefix), 2100)
        settings.status = "unconfigured"
        db.commit()
        with pytest.raises(CheckoutError):
            prepare_group(db, db.get(Client, owner_id))
        db.rollback()
        assert db.scalar(select(func.count(SaleOrder.id))) == 0


def test_legacy_snapshot_conflict_can_be_recovered_without_rewriting_pix():
    from app.checkout import create_pending_checkout, freeze_pending_checkout
    from app.pix import build_static_pix_code

    owner_id, _, gallery_ids = setup_cart()
    with SessionLocal() as db:
        owner = db.get(Client, owner_id)
        gallery = db.get(DerivedGallery, gallery_ids[0])
        order = create_pending_checkout(db, gallery=gallery, client=owner, checkout_key="legacy")
        original = order.pix_copy_paste_snapshot
        db.commit()
        settings = db.scalar(select(GlobalPixSettings))
        original_configuration = dict(order.pix_configuration_snapshot)
        settings.instructions = "Instruções diferentes"
        db.commit()
        with pytest.raises(CheckoutError, match="outro PIX"):
            prepare_group(db, owner)
        db.rollback()
        settings.instructions = order.pix_instructions_snapshot
        compatible = prepare_group(db, owner)
        assert compatible.total_cents == 2100
        assert order.pix_configuration_snapshot == original_configuration
        db.rollback()
        settings.copy_paste = build_static_pix_code(
            "other@example.test", receiver_name="OUTRO", receiver_city="SAO PAULO"
        )
        settings.instructions = order.pix_instructions_snapshot
        db.commit()
        with pytest.raises(CheckoutError, match="outro PIX"):
            prepare_group(db, owner)
        db.rollback()
        payload = cart_payload(db, owner)
        assert any(group["legacy_review_url"] for group in payload["groups"])
        freeze_pending_checkout(db, gallery=gallery, client=owner, order=order)
        db.commit()
        assert order.pix_copy_paste_snapshot == original and order.payment_group_id is None
        assert db.scalar(select(func.count(PhotoSelection.id))) == 1
        group = prepare_group(db, owner)
        assert group.total_cents == 700


@pytest.mark.skipif(
    engine.dialect.name != "postgresql", reason="Concorrência exige PostgreSQL isolado"
)
def test_concurrent_admin_decisions_apply_one_transition_to_all_orders():
    from app.auth import NotificationEvent

    setup_cart()
    browser = TestClient(app)
    browser.cookies.set("markina_session", "cart-test")
    payment = browser.post("/library/cart/prepare").json()["payment"]
    result = browser.post(
        f"/library/payments/{payment['id']}/report",
        json={"revision": payment["revision"], "idempotency_key": "report"},
    ).json()
    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser))
        db.add(
            AuthSession(
                subject_id=admin.id,
                role="admin",
                token_hash=token_hash("race-admin"),
                expires_at=now() + timedelta(hours=1),
            )
        )
        db.commit()
    barrier = Barrier(2)

    def decide(decision):
        browser = TestClient(app)
        browser.cookies.set("markina_session", "race-admin")
        barrier.wait(timeout=15)
        response = browser.post(
            f"/admin/payment-communications/{result['id']}/decision",
            json={"decision": decision, "payment_group_id": payment["id"]},
        )
        assert response.status_code == 200, response.text
        return response.json()["status"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(decide, decision) for decision in ("confirmed", "refused")]
        states = [future.result(timeout=30) for future in futures]
    assert states[0] == states[1]
    with SessionLocal() as db:
        assert {order.payment_status for order in db.scalars(select(SaleOrder))} == (
            {"confirmed"} if states[0] == "confirmed" else {"cancelled"}
        )
        assert db.scalar(select(func.count(NotificationEvent.id))) == 2


def test_new_login_history_legacy_and_new_cart_remain_independent():
    from app.auth import SaleOrderItem

    owner_id, other_id, gallery_ids = setup_cart()
    with SessionLocal() as db:
        legacy = SaleOrder(
            client_id=owner_id,
            derived_gallery_id=gallery_ids[0],
            total_cents=500,
            payment_status="confirmed",
            frozen_at=now(),
            confirmed_at=now(),
        )
        db.add(legacy)
        db.flush()
        db.add(
            SaleOrderItem(
                sale_order_id=legacy.id,
                photo_asset_id_snapshot=uuid4(),
                filename_snapshot="compra-anterior.jpg",
                unit_price_cents=500,
            )
        )
        db.add(
            AuthSession(
                subject_id=other_id,
                role="client",
                token_hash=token_hash("other-cart"),
                expires_at=now() + timedelta(hours=1),
            )
        )
        db.add(
            AuthSession(
                subject_id=owner_id,
                role="client",
                token_hash=token_hash("new-login"),
                expires_at=now() + timedelta(hours=1),
            )
        )
        db.commit()
    browser = TestClient(app)
    browser.cookies.set("markina_session", "new-login")
    assert browser.get("/library/cart").json()["quantity"] == 3
    history = browser.get("/library/purchases").json()
    assert len(history["orders"]) == 1 and not history["payment_groups"]
    payment = browser.post("/library/cart/prepare").json()["payment"]
    report = {"revision": payment["revision"], "idempotency_key": "reported-after-login"}
    assert browser.post(f"/library/payments/{payment['id']}/report", json=report).status_code == 200
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_ids[0])
        folder = db.scalar(select(PhotoFolder).where(PhotoFolder.derived_gallery_id == gallery.id))
        photo = PhotoAsset(
            parent_gallery_id=gallery.parent_gallery_id,
            derived_gallery_id=gallery.id,
            folder_id=folder.id,
            filename="nova-selecao.jpg",
            storage_key="synthetic/new.jpg",
        )
        db.add(photo)
        db.flush()
        db.add(
            PhotoSelection(
                client_id=owner_id, derived_gallery_id=gallery.id, photo_asset_id=photo.id
            )
        )
        db.get(DerivedGallery, gallery_ids[1]).selection_expires_at = now() - timedelta(days=1)
        db.commit()
    assert browser.post(f"/library/payments/{payment['id']}/report", json=report).status_code == 200
    assert browser.get("/library/cart").json()["quantity"] == 1
    history = browser.get("/library/purchases").json()
    assert len(history["orders"]) == 1 and len(history["payment_groups"]) == 1
    assert len(history["payment_groups"][0]["orders"]) == 2
    browser.cookies.set("markina_session", "other-cart")
    assert browser.get("/library/cart").json()["quantity"] == 0
    assert browser.get("/library/purchases").json() == {"orders": [], "payment_groups": []}
    assert browser.post(f"/library/payments/{payment['id']}/report", json=report).status_code == 409


def test_empty_cart_discards_only_unreported_group():
    setup_cart()
    browser = TestClient(app)
    browser.cookies.set("markina_session", "cart-test")
    cart = browser.post("/library/cart/prepare").json()
    payment = cart["payment"]
    for group in cart["groups"]:
        assert browser.delete(f"/library/cart/{group['gallery_id']}").status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count(PaymentGroup.id))) == 0
        assert db.scalar(select(func.count(SaleOrder.id))) == 0
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0
    assert (
        browser.post(
            f"/library/payments/{payment['id']}/report",
            json={"revision": payment["revision"], "idempotency_key": "removed-group"},
        ).status_code
        == 409
    )
