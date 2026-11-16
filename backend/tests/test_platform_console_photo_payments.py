"""Compra de fotos já enviada concilia mesmo após suspensão, sem novas compras."""

import hashlib
import hmac
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.auth import MercadoPagoAccount, MercadoPagoPayment, SaleOrder, SessionLocal, Tenant, now
from app.mercadopago_checkout import submit_payment
from app.mercadopago_webhook import (
    process_next_mercadopago_event,
    receive_notification,
    reconcile_next_mercadopago_payment,
)
from app.payment_availability import lock_payment_account
from app.tenancy import enable_domain_guard
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_mercadopago_checkout import commerce as _commerce
from tests.test_mercadopago_checkout import input_data, prepared
from tests.test_unified_checkout import isolated_cart_database as _isolated_cart_database

commerce = _commerce
isolated_cart_database = _isolated_cart_database


@pytest.mark.parametrize("via_webhook", [False, True])
def test_existing_photo_order_is_confirmed_and_preserved_for_suspended_tenant(commerce, via_webhook):
    client_id, _other, _galleries, network = commerce
    network.state = "pending"
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        submit_payment(db, client, payment.id, input_data())
        payment.next_check_at = now() - timedelta(seconds=1)
        db.get(Tenant, FIXTURE_TENANT_ID).status = "suspended"
        db.commit()
        payment_id = payment.id
    resource = network.resource
    resource.update(status="processed", status_detail="accredited", total_paid_amount=resource["total_amount"],
                    last_updated_date=(now() + timedelta(seconds=1)).isoformat())
    resource["transactions"]["payments"][0].update(status="processed", status_detail="accredited")
    if via_webhook:
        request_id, ts = "synthetic-suspended-photo", "1793718000"
        manifest = f"id:{resource['id']};request-id:{request_id};ts:{ts};"
        digest = hmac.new(b"synthetic-webhook-secret", manifest.encode(), hashlib.sha256).hexdigest()
        with SessionLocal() as db:
            enable_domain_guard(db)
            account = db.scalar(select(MercadoPagoAccount))
            receive_notification(db, account.id, {"data.id": resource["id"]},
                {"type": "order", "data": {"id": resource["id"]}}, f"ts={ts},v1={digest}", request_id)
        assert process_next_mercadopago_event()
    else:
        assert reconcile_next_mercadopago_payment()
    with SessionLocal() as db:
        assert db.get(MercadoPagoPayment, payment_id).state == "confirmed"
        assert db.scalar(select(func.count()).select_from(SaleOrder)) == 2
        assert set(db.scalars(select(SaleOrder.payment_status))) == {"confirmed"}
        assert db.get(Tenant, FIXTURE_TENANT_ID).status == "suspended"
        with pytest.raises(HTTPException):
            lock_payment_account(db, FIXTURE_TENANT_ID)
    assert len(network.creates) == 1
