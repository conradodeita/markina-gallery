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
    FolderClientGrant,
    GalleryClientState,
    GlobalPixSettings,
    MediaDerivative,
    NotificationEvent,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    PaymentGroup,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    PriceRule,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    engine,
    now,
    token_hash,
)
from app.canonical_selection import CanonicalSelectionUnavailable, select_canonical_photo
from app.checkout import CheckoutError
from app.main import app
from app.unified_checkout import cart_payload, finalize_selection, prepare_group, report_group
from tests.test_derived_galleries import set_test_global_pix


@pytest.fixture(autouse=True)
def isolated_cart_database():
    if engine.dialect.name == "postgresql":
        assert engine.url.host == "127.0.0.1" and engine.url.port in {55458, 55888}
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


def test_admin_access_contract_preserves_legacy_on_unrelated_patch():
    from pydantic import ValidationError

    from app.main import ParentGalleryInput as GalleryCreate
    from app.main import ParentGallerySettingsInput as GalleryUpdate

    assert GalleryCreate(name="Galeria").access_mode == "invite_only"
    for mode in ("standard", "invite_only"):
        assert GalleryCreate(name="Galeria", access_mode=mode).access_mode == mode
    for model in (GalleryCreate, GalleryUpdate):
        with pytest.raises(ValidationError):
            model(name="Galeria", access_mode="collective_protected")
    assert "access_mode" not in GalleryUpdate(name="Outro nome").model_dump(exclude_unset=True)


def test_external_selection_is_frozen_without_pix_payment_or_revenue():
    from app.order_delivery import delivery_payload, order_fulfillable, set_delivery

    owner_id, other_id, gallery_ids = setup_cart()
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_ids[0])
        parent = db.get(ParentGallery, gallery.parent_gallery_id)
        parent.payment_required = False
        parent.sales_message = "Combine o pacote com o fotógrafo.\nEscolha com calma."
        db.query(GlobalPixSettings).delete()
        db.commit()
        owner = db.get(Client, owner_id)
        group = next(item for item in cart_payload(db, owner)["groups"]
                     if item["gallery_id"] == str(gallery.id))
        assert group["total_cents"] is None
        assert group["message"] == parent.sales_message
        with pytest.raises(CheckoutError):
            finalize_selection(db, db.get(Client, other_id), gallery.id, group["revision"], "other")
        with pytest.raises(CheckoutError, match="revisão mudou"):
            finalize_selection(db, owner, gallery.id, "0" * 64, "stale")
        order = finalize_selection(db, owner, gallery.id, group["revision"], "external")
        db.commit()
        assert order.payment_status == "not_required"
        assert not order.payment_required_snapshot and order.frozen_at
        assert order.total_cents == 0 and order.payment_group_id is None
        assert db.scalar(select(func.count(PaymentCommunication.id))) == 0
        assert db.scalar(select(func.count(NotificationEvent.id))) == 0
        assert finalize_selection(db, owner, gallery.id, group["revision"], "external").id == order.id
        assert len(list(db.scalars(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id)))) == 2
        assert order_fulfillable(order) and delivery_payload(order)["can_send"]
        set_delivery(db, order, "https://photos.app.goo.gl/selection", 0, uuid4())
        parent.payment_required = True
        db.commit()
        assert order_fulfillable(order)
        assert not order_fulfillable(SaleOrder(payment_status="pending", payment_required_snapshot=True))


def test_mixed_cart_pix_excludes_external_selection():
    owner_id, _other_id, gallery_ids = setup_cart()
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_ids[0])
        parent = db.get(ParentGallery, gallery.parent_gallery_id)
        parent.payment_required = False
        db.commit()
        owner = db.get(Client, owner_id)
        cart = cart_payload(db, owner)
        assert cart["total_cents"] == 700 and cart["can_prepare"]
        group = prepare_group(db, owner)
        db.commit()
        assert group.total_cents == 700
        assert len(list(db.scalars(select(SaleOrder).where(SaleOrder.payment_group_id == group.id)))) == 1
        external = next(item for item in cart["groups"] if not item["payment_required"])
        finalize_selection(db, owner, gallery.id, external["revision"], "mixed")
        db.commit()
        report_group(db, owner, group.id, group.revision, "paid")
        db.commit()
        assert group.state == "reported"


def test_switch_to_external_discards_only_editable_paid_draft():
    from app.checkout import create_pending_checkout

    owner_id, _other_id, gallery_ids = setup_cart()
    with SessionLocal() as db:
        owner = db.get(Client, owner_id)
        payment = prepare_group(db, owner)
        db.commit()
        gallery = db.get(DerivedGallery, gallery_ids[0])
        parent = db.get(ParentGallery, gallery.parent_gallery_id)
        parent.payment_required = False
        db.commit()
        with pytest.raises(CheckoutError, match="sem cobrança"):
            create_pending_checkout(db, gallery=gallery, client=owner, checkout_key="legacy")
        group = next(row for row in cart_payload(db, owner)["groups"] if not row["payment_required"])
        order = finalize_selection(db, owner, gallery.id, group["revision"], "switch")
        db.commit()
        assert order.payment_status == "not_required"
        assert db.scalar(select(SaleOrder.id).where(SaleOrder.derived_gallery_id == gallery.id, SaleOrder.payment_status == "pending")) is None
        with pytest.raises(CheckoutError):
            report_group(db, owner, payment.id, payment.revision, "stale-payment")
        updated = prepare_group(db, owner)
        assert updated.total_cents == 700


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Concorrência exige PostgreSQL descartável")
def test_concurrent_external_finalization_creates_one_order():
    owner_id, _other_id, gallery_ids = setup_cart()
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_ids[0])
        db.get(ParentGallery, gallery.parent_gallery_id).payment_required = False
        db.commit()
        revision = next(row["revision"] for row in cart_payload(db, db.get(Client, owner_id))["groups"]
                        if not row["payment_required"])
    barrier = Barrier(2)

    def finalize():
        with SessionLocal() as db:
            owner = db.get(Client, owner_id)
            barrier.wait(timeout=15)
            order = finalize_selection(db, owner, gallery_ids[0], revision, "concurrent-external")
            db.commit()
            return order.id

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(finalize) for _ in range(2)]
        ids = [future.result(timeout=30) for future in futures]
    assert ids[0] == ids[1]
    with SessionLocal() as db:
        assert db.scalar(select(func.count(SaleOrder.id))) == 1
        assert db.scalar(select(func.count(SaleOrderItem.id))) == 2


def test_canonical_external_selection_api_admin_export_and_history():
    owner_id, other_id, _legacy_ids = setup_cart()
    with SessionLocal() as db:
        admin = AdminUser(email="selection-admin@test.invalid", password_hash="synthetic", email_verified=True, totp_secret="JBSWY3DPEHPK3PXP")
        parent = ParentGallery(name="Seleção externa", access_mode="collective_protected")
        db.add_all([admin, parent])
        db.flush()
        parent_id = parent.id
        db.add(ParentGalleryRegistration(parent_gallery_id=parent.id, client_id=owner_id, status="active"))
        db.add(GalleryClientState(parent_gallery_id=parent.id, client_id=owner_id))
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Comum", status="released", audience_scope="all")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(parent_gallery_id=parent.id, folder_id=folder.id, filename="externa.jpg", storage_key="synthetic/external.jpg")
        db.add(photo)
        db.flush()
        db.add(PhotoSelection(parent_gallery_id=parent.id, client_id=owner_id, photo_asset_id=photo.id))
        for subject, role, key in ((admin.id, "admin", "selection-admin"), (other_id, "client", "selection-other")):
            db.add(AuthSession(subject_id=subject, role=role, token_hash=token_hash(key), expires_at=now() + timedelta(hours=1)))
        db.commit()
    admin_browser = TestClient(app)
    admin_browser.cookies.set("markina_session", "selection-admin")
    assert admin_browser.post("/admin/parent-galleries", json={"name": "Recusar", "access_mode": "collective_protected"}).status_code == 422
    settings = f"/admin/parent-galleries/{parent_id}/settings"
    assert admin_browser.patch(settings, json={"name": "Seleção externa atualizada"}).status_code == 200
    with SessionLocal() as db:
        assert db.get(ParentGallery, parent_id).access_mode == "collective_protected"
    assert admin_browser.patch(settings, json={"access_mode": "invite_only"}).status_code == 200
    sales = f"/admin/parent-galleries/{parent_id}/sales"
    assert admin_browser.put(sales, json={"payment_required": True, "pricing_mode": "fixed", "fixed_unit_price_cents": 0}).status_code == 422
    assert admin_browser.put(sales, json={"payment_required": False, "sales_message": "Combine o pacote."}).status_code == 200
    browser = TestClient(app)
    browser.cookies.set("markina_session", "cart-test")
    assert browser.get("/library").status_code == 200
    group = next(row for row in browser.get("/library/cart").json()["groups"] if row["gallery_id"] == str(parent_id))
    payload = {"revision": group["revision"], "idempotency_key": "canonical-external"}
    other_browser = TestClient(app)
    other_browser.cookies.set("markina_session", "selection-other")
    assert other_browser.post(f"/library/cart/{parent_id}/finalize", json=payload).status_code == 409
    response = browser.post(f"/library/cart/{parent_id}/finalize", json=payload)
    assert response.status_code == 200, response.text
    order_id = response.json()["order_id"]
    assert browser.post(f"/library/cart/{parent_id}/finalize", json=payload).json()["order_id"] == order_id
    history = browser.get("/library/purchases").json()["orders"]
    order = next(row for row in history if row["id"] == order_id)
    assert order["commercial_state"] == "selection_finalized" and order["total_cents"] is None
    people = admin_browser.get(f"/admin/parent-galleries/{parent_id}/clients").json()["clients"]
    assert people[0]["finalized_orders"][0]["id"] == order_id
    exported = admin_browser.get(f"/admin/orders/{order_id}/selection/export.csv")
    assert exported.status_code == 200 and "externa.jpg" in exported.text
    assert browser.get(f"/admin/orders/{order_id}/selection/export.csv").status_code == 403
    delivered = admin_browser.put(f"/admin/orders/{order_id}/delivery", json={"album_url": "https://photos.app.goo.gl/external", "version": 0})
    assert delivered.status_code == 200, delivered.text
    assert next(row for row in browser.get("/library/purchases").json()["orders"] if row["id"] == order_id)["delivery_album_url"]


def test_external_historical_media_uses_explicit_retention_from_finalization(tmp_path, monkeypatch):
    from app.auth import CommercialHistoryMedia
    from app.commercial_retention import apply_commercial_media_retention

    owner_id, _other_id, gallery_ids = setup_cart()
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(tmp_path))
    monkeypatch.delenv("COMMERCIAL_HISTORY_MEDIA_RETENTION_DAYS", raising=False)
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_ids[0])
        parent = db.get(ParentGallery, gallery.parent_gallery_id)
        parent.payment_required = False
        db.commit()
        owner = db.get(Client, owner_id)
        group = next(row for row in cart_payload(db, owner)["groups"] if not row["payment_required"])
        order = finalize_selection(db, owner, gallery.id, group["revision"], "retention")
        order.frozen_at = now() - timedelta(days=60)
        db.flush()
        item = db.scalar(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id))
        preview = tmp_path / "preview.jpg"
        preview.write_bytes(b"synthetic")
        db.add(CommercialHistoryMedia(sale_order_item_id=item.id, preview_storage_key="preview.jpg", status="ready"))
        db.commit()
        assert apply_commercial_media_retention(db).purged_items == 0 and preview.exists()
        monkeypatch.setenv("COMMERCIAL_HISTORY_MEDIA_RETENTION_DAYS", "30")
        assert apply_commercial_media_retention(db).purged_items == 1 and not preview.exists()
        assert order.payment_status == "not_required" and order.confirmed_at is None


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="concorrência exige PostgreSQL descartável")
def test_simultaneous_first_selections_create_one_canonical_state() -> None:
    with SessionLocal() as db:
        owner = Client(full_name="Cliente concorrente", phone_e164="+5511999988333")
        parent = ParentGallery(name="Evento concorrente")
        db.add_all([owner, parent])
        db.flush()
        db.add(ParentGalleryRegistration(
            parent_gallery_id=parent.id, client_id=owner.id, status="active"
        ))
        folder = PhotoFolder(
            parent_gallery_id=parent.id, name="Comum", status="released",
            audience_scope="all",
        )
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id, folder_id=folder.id, filename="foto.jpg",
            storage_key="synthetic/foto.jpg", available=True,
        )
        db.add(photo)
        db.commit()
        owner_id, parent_id, photo_id = owner.id, parent.id, photo.id
    barrier = Barrier(2)

    def select_once(_):
        with SessionLocal() as db:
            barrier.wait(timeout=10)
            result = select_canonical_photo(
                db, parent_gallery_id=parent_id, client_id=owner_id,
                photo_id=photo_id,
            )
            db.commit()
            return result.state_created, result.selection_created, result.quantity

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(select_once, range(2)))
    assert sorted(outcomes) == [(False, False, 1), (True, True, 1)]
    with SessionLocal() as db:
        assert db.scalar(select(func.count(GalleryClientState.id))) == 1
        assert db.scalar(select(func.count(PhotoSelection.id))) == 1
        assert db.scalar(select(func.count(DerivedGallery.id))) == 0


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


def test_canonical_selection_joins_legacy_cart_without_new_derived_gallery():
    owner_id, other_id, legacy_ids = setup_cart()
    with SessionLocal() as db:
        parent = db.get(DerivedGallery, legacy_ids[0]).parent_gallery_id
        db.add(ParentGalleryRegistration(
            parent_gallery_id=parent, client_id=owner_id, status="active"
        ))
        state = GalleryClientState(parent_gallery_id=parent, client_id=owner_id)
        db.add(state)
        db.flush()
        folder = PhotoFolder(
            parent_gallery_id=parent, name="Pasta comum", status="released",
            audience_scope="all",
        )
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent, folder_id=folder.id, filename="nova.jpg",
            storage_key=f"synthetic/{uuid4()}.jpg",
        )
        db.add(photo)
        db.flush()
        db.add(PhotoSelection(
            parent_gallery_id=parent, client_id=owner_id, photo_asset_id=photo.id
        ))
        db.commit()
        canonical_id = parent
        photo_id = photo.id
        folder_id = folder.id
    with SessionLocal() as db:
        owner = db.get(Client, owner_id)
        cart = cart_payload(db, owner)
        assert cart["quantity"] == 4
        assert cart["total_cents"] == 2800
        canonical = next(group for group in cart["groups"] if group["gallery_id"] == str(canonical_id))
        assert canonical["quantity"] == 1
        assert canonical["items"][0]["preview_url"] == (
            f"/public-galleries/{canonical_id}/photos/{photo_id}/preview"
        )
        assert cart_payload(db, db.get(Client, other_id))["groups"] == []
        group = prepare_group(db, owner)
        assert prepare_group(db, owner).id == group.id
        db.commit()
        assert db.scalar(select(func.count(DerivedGallery.id))) == 2
        order = db.scalar(select(SaleOrder).where(SaleOrder.parent_gallery_id == canonical_id))
        assert order and order.derived_gallery_id is None
        first_communication = report_group(db, owner, group.id, group.revision, "mixed-cart")
        db.commit()
        assert order.frozen_at is not None
        frozen_snapshot = (order.total_cents, order.price_rule_snapshot, tuple(
            (item.filename_snapshot, item.unit_price_cents)
            for item in db.scalars(select(SaleOrderItem).where(
                SaleOrderItem.sale_order_id == order.id
            ).order_by(SaleOrderItem.id))
        ))
        assert db.scalar(select(PhotoSelection.id).where(
            PhotoSelection.parent_gallery_id == canonical_id,
            PhotoSelection.photo_asset_id == photo_id,
        )) is None
        second = PhotoAsset(
            parent_gallery_id=canonical_id, folder_id=folder_id,
            filename="compra-adicional.jpg", storage_key=f"synthetic/{uuid4()}.jpg",
        )
        db.add(second)
        db.flush()
        db.add(PhotoSelection(
            parent_gallery_id=canonical_id, client_id=owner_id,
            photo_asset_id=second.id,
        ))
        db.commit()
        next_group = prepare_group(db, owner)
        assert next_group.id != group.id
        assert next_group.total_cents == 700
        next_communication = report_group(db, owner, next_group.id, next_group.revision, "additional-cart")
        db.commit()
        assert db.scalar(select(func.count(SaleOrder.id)).where(
            SaleOrder.parent_gallery_id == canonical_id,
            SaleOrder.frozen_at.is_not(None),
        )) == 2
        assert db.scalar(select(func.count(NotificationEvent.id)).where(
            NotificationEvent.event_type == "payment_reported",
            NotificationEvent.parent_gallery_id == canonical_id,
        )) >= 1
        admin = db.scalar(select(AdminUser))
        db.add(AuthSession(
            subject_id=admin.id, role="admin", token_hash=token_hash("canonical-admin"),
            expires_at=now() + timedelta(hours=1),
        ))
        db.commit()
        first_communication_id = first_communication.id
        next_communication_id = next_communication.id
        first_order_id = order.id
        first_group_id, next_group_id = group.id, next_group.id
    admin_browser = TestClient(app)
    admin_browser.cookies.set("markina_session", "canonical-admin")
    for communication_id, payment_group_id in (
        (first_communication_id, first_group_id),
        (next_communication_id, next_group_id),
    ):
        decision = admin_browser.post(
            f"/admin/payment-communications/{communication_id}/decision",
            json={"decision": "confirmed", "payment_group_id": str(payment_group_id)},
        )
        assert decision.status_code == 200, decision.text
    delivery = admin_browser.put(
        f"/admin/orders/{first_order_id}/delivery",
        json={"album_url": "https://photos.app.goo.gl/CanonicalTest", "version": 0},
    )
    assert delivery.status_code == 200, delivery.text
    assert delivery.json()["notification"] is not None
    purchased = admin_browser.get(
        f"/admin/parent-galleries/{canonical_id}/clients/{owner_id}/selection/export.html"
    )
    assert purchased.status_code == 200, purchased.text
    assert "nova.jpg" in purchased.text and "compra-adicional.jpg" in purchased.text
    with SessionLocal() as db:
        original = db.get(SaleOrder, first_order_id)
        assert (original.total_cents, original.price_rule_snapshot, tuple(
            (item.filename_snapshot, item.unit_price_cents)
            for item in db.scalars(select(SaleOrderItem).where(
                SaleOrderItem.sale_order_id == first_order_id
            ).order_by(SaleOrderItem.id))
        )) == frozen_snapshot
    browser = TestClient(app)
    browser.cookies.set("markina_session", "cart-test")
    history = browser.get("/library/purchases")
    assert history.status_code == 200, history.text
    assert any(
        order["gallery_removed"] is False
        for payment_group in history.json()["payment_groups"]
        for order in payment_group["orders"]
        if order["parent_gallery_name"] == "Galeria 1"
    )
    with SessionLocal() as db:
        with pytest.raises(CanonicalSelectionUnavailable):
            select_canonical_photo(
                db, parent_gallery_id=canonical_id,
                client_id=owner_id, photo_id=photo_id,
            )
        third = PhotoAsset(
            parent_gallery_id=canonical_id, folder_id=folder_id,
            filename="remover.jpg", storage_key=f"synthetic/{uuid4()}.jpg",
        )
        db.add(third)
        db.flush()
        db.add(PhotoSelection(
            parent_gallery_id=canonical_id, client_id=owner_id,
            photo_asset_id=third.id,
        ))
        db.commit()
        third_id = third.id
    removed = browser.delete(f"/library/cart/{canonical_id}/photos/{third_id}")
    assert removed.status_code == 200, removed.text
    assert removed.json()["quantity"] == 0


def test_confirmed_canonical_preview_survives_folder_revocation(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path))
    with SessionLocal() as db:
        owner = Client(full_name="Compradora", phone_e164="+5511999988111")
        other = Client(full_name="Outra", phone_e164="+5511999988222")
        parent = ParentGallery(name="Evento")
        db.add_all([owner, other, parent])
        db.flush()
        db.add(ParentGalleryRegistration(
            parent_gallery_id=parent.id, client_id=owner.id, status="active"
        ))
        db.add(GalleryClientState(parent_gallery_id=parent.id, client_id=owner.id))
        folder = PhotoFolder(
            parent_gallery_id=parent.id, name="Acervo", status="released",
            audience_scope="selected",
        )
        db.add(folder)
        db.flush()
        grant = FolderClientGrant(
            folder_id=folder.id, parent_gallery_id=parent.id, client_id=owner.id
        )
        photo = PhotoAsset(
            parent_gallery_id=parent.id, folder_id=folder.id,
            filename="foto.jpg", storage_key="synthetic/foto.jpg", available=True,
        )
        db.add_all([grant, photo])
        db.flush()
        preview_path = tmp_path / str(photo.id) / "client_preview.jpg"
        preview_path.parent.mkdir(parents=True)
        preview_path.write_bytes(b"synthetic-preview")
        db.add(MediaDerivative(
            photo_asset_id=photo.id, variant="client_preview", status="ready",
            relative_path=f"{photo.id}/client_preview.jpg", width=10, height=10,
        ))
        order = SaleOrder(
            parent_gallery_id=parent.id, client_id=owner.id,
            payment_status="confirmed", total_cents=700, confirmed_at=now(),
        )
        db.add(order)
        db.flush()
        item = SaleOrderItem(
            sale_order_id=order.id, photo_asset_id=photo.id,
            filename_snapshot=photo.filename, unit_price_cents=700,
        )
        db.add(item)
        pending = SaleOrder(
            parent_gallery_id=parent.id, client_id=owner.id,
            payment_status="pending", total_cents=700,
        )
        db.add(pending)
        db.flush()
        pending_item = SaleOrderItem(
            sale_order_id=pending.id, photo_asset_id=photo.id,
            filename_snapshot=photo.filename, unit_price_cents=700,
        )
        db.add(pending_item)
        db.add_all([
            AuthSession(subject_id=owner.id, role="client", token_hash=token_hash("buyer"),
                        expires_at=now() + timedelta(hours=1)),
            AuthSession(subject_id=other.id, role="client", token_hash=token_hash("stranger"),
                        expires_at=now() + timedelta(hours=1)),
        ])
        db.commit()
        parent_id, photo_id, item_id, pending_item_id = (
            parent.id, photo.id, item.id, pending_item.id
        )
        db.delete(grant)
        db.commit()
    browser = TestClient(app)
    browser.cookies.set("markina_session", "buyer")
    assert browser.get(f"/public-galleries/{parent_id}/photos/{photo_id}/preview").status_code == 404
    history = browser.get("/library/purchases").json()
    assert history["orders"][0]["items"][0]["preview_url"] == (
        f"/library/purchases/items/{item_id}/preview"
    )
    preview = browser.get(f"/library/purchases/items/{item_id}/preview")
    assert preview.status_code == 200 and preview.content == b"synthetic-preview"
    assert browser.get(f"/library/purchases/items/{pending_item_id}/preview").status_code == 403
    browser.cookies.set("markina_session", "stranger")
    assert browser.get(f"/library/purchases/items/{item_id}/preview").status_code == 403


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
    refused_correction = {"idempotency_key": "correct-refusal", "payment_group_id": payment["id"]}
    assert browser.post(path + "/correction", json=refused_correction).status_code == 403
    browser.cookies.set("markina_session", "admin-cart-test")
    assert browser.post(path + "/correction", json={"idempotency_key": "without-scope"}).status_code == 409
    with SessionLocal() as db:
        inconsistent = db.scalar(select(SaleOrder).order_by(SaleOrder.id))
        inconsistent.payment_status = "confirmed"
        inconsistent_id = inconsistent.id
        db.commit()
    assert browser.post(path + "/correction", json=refused_correction).status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(PaymentCommunication)).status == "refused"
        db.get(SaleOrder, inconsistent_id).payment_status = "cancelled"
        db.commit()
    assert browser.post(path + "/correction", json=refused_correction).status_code == 200
    assert browser.post(path + "/correction", json=refused_correction).status_code == 200
    with SessionLocal() as db:
        from app.auth import PaymentConfirmationCorrection
        assert {order.payment_status for order in db.scalars(select(SaleOrder))} == {"pending"}
        assert db.scalar(select(PaymentGroup)).state == "reported"
        assert db.scalar(select(func.count(NotificationEvent.id))) == 3
        assert db.scalar(select(func.count(PaymentConfirmationCorrection.id))) == 2
    payload["decision"] = "confirmed"
    assert browser.post(path + "/decision", json=payload).status_code == 200
    assert browser.post(path + "/decision", json=payload).status_code == 200
    with SessionLocal() as db:
        assert {order.payment_status for order in db.scalars(select(SaleOrder))} == {"confirmed"}
        assert db.scalar(select(PaymentGroup)).state == "confirmed"
        assert db.scalar(select(func.count(NotificationEvent.id))) == 4


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
    assert browser.get("/library/purchases").json() == {"orders": [], "payment_groups": [], "removed_movements": []}
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
