"""Executar no PostgreSQL dedicado de testes, nunca em banco operacional."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import AuthSession, NotificationEvent, SaleOrder, SessionLocal, engine
from app.main import app
from app.order_delivery import lock_delivery_order, resend_delivery
from tests.test_order_delivery import ALBUM, send, setup_order
from tests.test_unified_checkout import isolated_cart_database  # noqa: F401

pytestmark = pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Requer PostgreSQL dedicado para validar locks concorrentes.")


def test_delivery_races_financial_correction_without_exposing_unpaid_order():
    admin, client, orders, communication = setup_order()
    gate = Barrier(2)

    def operation(correction):
        browser = TestClient(app)
        browser.cookies.update(admin.cookies)
        gate.wait(timeout=10)
        if correction:
            return browser.post(f"/admin/payment-communications/{communication}/correction", json={"idempotency_key": "concurrent-delivery-correction"})
        return send(browser, orders[0])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(operation, (False, True)))
    assert results[0].status_code in {200, 409}
    assert results[1].status_code == 200
    assert client.get("/library/purchases").json()["orders"][0]["delivery_album_url"] is None
    with SessionLocal() as db:
        order = db.get(SaleOrder, orders[0])
        assert order.payment_status == "pending"
        if results[0].status_code == 200:
            assert order.delivery_album_url == ALBUM and order.delivery_revision == 2
        else:
            assert order.delivery_album_url is None


def test_concurrent_resends_share_one_event():
    admin, _, orders, _ = setup_order()
    assert send(admin, orders[0]).status_code == 200
    gate, operation = Barrier(2), uuid4()

    def resend(_):
        with SessionLocal() as db:
            actor = db.scalar(select(AuthSession).where(AuthSession.role == "admin")).subject_id
            gate.wait(timeout=10)
            result = resend_delivery(db, lock_delivery_order(db, orders[0]), 1, operation, actor)
            db.commit()
            return result["notification"]["event_id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(resend, range(2)))
    assert ids[0] == ids[1]
    with SessionLocal() as db:
        assert len(list(db.scalars(select(NotificationEvent).where(NotificationEvent.event_type == "order_delivery_ready")))) == 2
