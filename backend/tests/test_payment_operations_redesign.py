import csv
from datetime import UTC, datetime, timedelta
from io import StringIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.auth import (
    Client,
    DerivedGallery,
    MediaDerivative,
    ParentGallery,
    PaymentCommunication,
    PhotoAsset,
    PhotoFolder,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    engine,
    now,
)
from app.main import app
from app.payment_export import HEADERS, safe_text
from tests.test_derived_galleries import (  # noqa: F401
    FIXTURE_TENANT_ID,
    authenticate_admin,
    clean_database,
    set_test_global_pix,
)


@pytest.fixture
def browser(clean_database):  # noqa: F811
    set_test_global_pix()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def orders():
    reference = datetime(2026, 10, 17, 15, 30, tzinfo=UTC)
    with SessionLocal() as db:
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name='Evento; "Ana"\n2026')
        db.add(parent)
        db.flush()
        records = []
        for i in range(15):
            client = Client(tenant_id=FIXTURE_TENANT_ID, full_name=f"Cliente {i:02d}", phone_e164=f"+5511999900{i:03d}")
            db.add(client)
            db.flush()
            gallery = DerivedGallery(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, client_id=client.id,
                                     name=f"Privada {i}")
            db.add(gallery)
            db.flush()
            status = ["pending", "confirmed", "confirmed", "pending", "cancelled"][i % 5]
            order = SaleOrder(tenant_id=FIXTURE_TENANT_ID, derived_gallery_id=gallery.id, client_id=client.id,
                              payment_status=status, total_cents=12345 + i,
                              created_at=reference + timedelta(seconds=i),
                              confirmed_at=reference if status == "confirmed" else None,
                              delivery_album_url="https://photos.app.goo.gl/Ready" if i % 5 == 2 else None)
            db.add(order)
            db.flush()
            db.add(SaleOrderItem(tenant_id=FIXTURE_TENANT_ID, sale_order_id=order.id, photo_asset_id_snapshot=uuid4(),
                                filename_snapshot=f"foto-{i}.jpg", unit_price_cents=1))
            if i % 5 == 0:
                db.add(PaymentCommunication(tenant_id=FIXTURE_TENANT_ID, sale_order_id=order.id, client_id=client.id,
                                           idempotency_key=f"synthetic-report-{i}"))
            records.append((client.id, order.id))
        db.commit()
        return parent.id, records


def csv_rows(response):
    assert response.content.startswith(b"\xef\xbb\xbf")
    return list(csv.reader(StringIO(response.content.decode("utf-8-sig")), delimiter=";"))


def test_priority_filter_and_complete_csv_share_financial_scope(browser, orders):
    assert browser.get("/admin/payment-communications/export.csv").status_code == 403
    authenticate_admin(browser)
    first = browser.get("/admin/payment-communications", params={"financial_status": "priority", "limit": 1})
    assert first.status_code == 200
    payload = first.json()
    assert len(payload["groups"]) == 1
    assert payload["page"]["next_cursor"]
    assert payload["summary"]["orders"] == 6
    assert payload["selections_without_order"] == []
    seen = list(payload["groups"])
    while payload["page"]["next_cursor"]:
        payload = browser.get("/admin/payment-communications", params={
            "financial_status": "priority", "limit": 1, "cursor": payload["page"]["next_cursor"],
        }).json()
        seen.extend(payload["groups"])
    assert len({group["client"]["id"] for group in seen}) == 6
    response = browser.get("/admin/payment-communications/export.csv", params={"financial_status": "priority"})
    rows = csv_rows(response)
    assert rows[0] == HEADERS
    assert len(rows) == 7
    assert all(len(row) == 4 for row in rows)
    assert rows[1][1] == '1 fotografias — Evento; "Ana"\n2026'
    assert rows[1][2] == "123,45"  # total do pedido; não o preço unitário de 1 centavo
    assert rows[1][3] == ""
    assert rows[-1][3] == "17/10/2026 12:30:00"
    for status, count in [("reported", 3), ("confirmed_undelivered", 3), ("confirmed", 3), (None, 15)]:
        params = {"financial_status": status} if status else {}
        assert len(csv_rows(browser.get("/admin/payment-communications/export.csv", params=params))) == count + 1


def test_export_combines_filters_preserves_grouping_and_has_bounded_queries(browser, orders):
    authenticate_admin(browser)
    parent_id, records = orders
    params = {"client_id": str(records[1][0]), "parent_gallery_id": str(parent_id),
              "financial_status": "priority", "created_from": "2026-10-17T00:00:00Z",
              "created_to": "2026-10-17T23:59:59Z"}
    assert len(csv_rows(browser.get("/admin/payment-communications/export.csv", params=params))) == 2
    params["financial_status"] = "reported"
    assert browser.get("/admin/payment-communications/export.csv", params=params).status_code == 204
    assert browser.get("/admin/payment-communications/export.csv", params={
        "created_from": "2026-10-18T00:00:00Z", "created_to": "2026-10-17T00:00:00Z",
    }).status_code == 422
    statements = []
    def collect(*args):
        statements.append(args[2])
    event.listen(engine, "before_cursor_execute", collect)
    try:
        response = browser.get("/admin/payment-communications/export.csv")
    finally:
        event.remove(engine, "before_cursor_execute", collect)
    assert response.status_code == 200
    assert len(statements) < 20  # lote de 15 clientes não gera query por pedido/foto
    assert len(csv_rows(response)) == 16


@pytest.mark.parametrize("text", ["=HYPERLINK(1)", " +1", "-1", "@SUM(A1)", "\ttexto", "\ntexto"])
def test_csv_protects_untrusted_formula_text(text):
    assert safe_text(text) == "'" + text


def test_order_previews_require_admin_and_match_item_without_original_fallback(browser, orders, tmp_path, monkeypatch):
    from PIL import Image
    from sqlalchemy import select

    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path))
    parent_id, records = orders
    with SessionLocal() as db:
        order = db.get(SaleOrder, records[0][1])
        item = db.scalar(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id))
        folder = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent_id, name="Pasta", status="released")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent_id, folder_id=folder.id, filename="foto.jpg",
                           storage_key="original-not-present.jpg", available=True)
        db.add(photo)
        db.flush()
        item.photo_asset_id = photo.id
        item.photo_asset_id_snapshot = photo.id
        for variant, filename, color in [("thumbnail", "thumb.jpg", "red"), ("admin_preview", "admin.jpg", "blue")]:
            Image.new("RGB", (64, 48), color).save(tmp_path / filename)
            db.add(MediaDerivative(tenant_id=FIXTURE_TENANT_ID, photo_asset_id=photo.id, variant=variant, status="ready", relative_path=filename))
        order_id, item_id = order.id, item.id
        db.commit()
    url = f"/admin/orders/{order_id}/items/{item_id}/preview"
    assert browser.get(url).status_code == 403
    authenticate_admin(browser)
    small = browser.get(url)
    large = browser.get(url, params={"size": "preview"})
    assert small.content == (tmp_path / "thumb.jpg").read_bytes()
    assert large.content == (tmp_path / "admin.jpg").read_bytes()
    assert small.headers["cache-control"] == "private, no-store"
    assert small.headers["x-content-type-options"] == "nosniff"
    assert browser.get(f"/admin/orders/{records[1][1]}/items/{item_id}/preview").status_code == 404
    assert browser.get(url, params={"size": "original"}).status_code == 422
    (tmp_path / "thumb.jpg").unlink()
    assert browser.get(url).status_code == 404
    with SessionLocal() as db:
        db.get(SaleOrder, order_id).assets_removed_at = now()
        db.commit()
    assert browser.get(url, params={"size": "preview"}).status_code == 404
    data = browser.get("/admin/payment-communications", params={"client_id": str(records[0][0])}).json()
    result = data["groups"][0]["orders"][0]["folders"][0]["items"][0]
    assert result["thumbnail_url"] is None and result["preview_url"] is None


def test_retired_statistics_endpoints_are_not_available(browser):
    authenticate_admin(browser)
    for path in ["/admin/statistics", "/admin/statistics/filters", "/admin/statistics/purchased.txt",
                 "/admin/statistics/selected-not-purchased.txt"]:
        assert browser.get(path).status_code == 404
    assert browser.get("/admin/payment-communications").status_code == 200


def test_csv_keeps_multiple_orders_consecutive_and_sanitizes_client_name(browser, orders):
    from sqlalchemy import select

    authenticate_admin(browser)
    _, records = orders
    with SessionLocal() as db:
        client = db.get(Client, records[0][0])
        client.full_name = '=HYPERLINK("malicioso")'
        previous = db.get(SaleOrder, records[0][1])
        second = SaleOrder(tenant_id=FIXTURE_TENANT_ID, derived_gallery_id=previous.derived_gallery_id, client_id=client.id,
                           payment_status="confirmed", total_cents=987,
                           confirmed_at=datetime(2026, 10, 17, 18, tzinfo=UTC))
        db.add(second)
        db.flush()
        original_item = db.scalar(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == previous.id))
        db.add(SaleOrderItem(tenant_id=FIXTURE_TENANT_ID, sale_order_id=second.id, photo_asset_id_snapshot=uuid4(),
                            filename_snapshot=original_item.filename_snapshot, unit_price_cents=987))
        db.commit()
    rows = csv_rows(browser.get("/admin/payment-communications/export.csv"))[1:]
    matching = [i for i, row in enumerate(rows) if row[0].startswith("'=HYPERLINK")]
    assert len(matching) == 2 and matching[1] == matching[0] + 1
    pair = [rows[i] for i in matching]
    assert {row[2] for row in pair} == {"9,87", "123,45"}
    assert {row[3] for row in pair} == {"", "17/10/2026 15:00:00"}
