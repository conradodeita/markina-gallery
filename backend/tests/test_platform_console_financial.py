"""Conciliação financeira de suspensos sem habilitar consumo novo."""

import hashlib
import hmac
from copy import deepcopy
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.auth import MercadoPagoPayment, PhotographerCreditEntry, Tenant, now
from app.mercadopago_credit_purchases import process_next_mercadopago_credit_purchase
from app.mercadopago_webhook import process_next_mercadopago_event, receive_notification
from app.tenancy import enable_domain_guard
from tests.test_mercadopago_credit_purchases import create_purchase_context, order_resource, prepare
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


@pytest.mark.parametrize("via_webhook", [False, True])
def test_late_credit_confirmation_for_suspended_buyer_is_exactly_once(client_db, monkeypatch, via_webhook):
    _owner_tenant, buyer_tenant, _owner, buyer, package, account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "suspended-buyer")
    purchase.method, purchase.state, purchase.submitted_at = "credit_card", "submitting", now()
    purchase.next_check_at = now() - timedelta(seconds=1)
    buyer_tenant.status = "suspended"
    client_db.commit()
    resource = order_resource(purchase)

    class Provider:
        def get(self, _order_id):
            return deepcopy(resource)

        def search(self, **_):
            return {"data": [deepcopy(resource)]}

    monkeypatch.setattr("app.mercadopago_credit_purchases.credential_provider", lambda _: Provider())
    monkeypatch.setattr("app.mercadopago_webhook.credential_provider", lambda _: Provider())
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    if via_webhook:
        request_id, ts = "synthetic-suspended", "1793718000"
        manifest = f"id:{resource['id']};request-id:{request_id};ts:{ts};"
        digest = hmac.new(b"synthetic-webhook-secret", manifest.encode(), hashlib.sha256).hexdigest()
        enable_domain_guard(client_db)
        for _ in range(2):
            receive_notification(client_db, account_id, {"data.id": resource["id"]},
                {"type": "order", "data": {"id": resource["id"]}}, f"ts={ts},v1={digest}", request_id)
        assert process_next_mercadopago_event(session_factory=factory)
    else:
        assert process_next_mercadopago_credit_purchase(session_factory=factory)
    client_db.expire_all()
    assert client_db.get(type(purchase), purchase.id).state == "confirmed"
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry)) == 1
    assert client_db.scalar(select(func.count()).select_from(MercadoPagoPayment)) == 0
    assert client_db.get(Tenant, buyer_tenant.id).status == "suspended"
    with pytest.raises(HTTPException):
        prepare(client_db, buyer_tenant, buyer, package, "forbidden-new-purchase")
