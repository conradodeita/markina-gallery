"""Snapshots/locks PostgreSQL e transporte HTTP externo exclusivamente sintético."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import httpx
import pytest
from fastapi import Request
from pydantic import SecretStr
from sqlalchemy import func, select

from app import auth, main
from app.auth import InfinitePaySettings, PhotoSelection, ProviderPayment, SaleOrder
from app.checkout import CheckoutError
from app.infinitepay_settings import ReceiverInput, apply_proposal, canonical_proposal
from app.payment_availability import lock_payment_account, payment_methods
from app.payment_provider import SyntheticPaymentProvider, operational_provider
from app.provider_checkout import issue_provider_payment
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_integration_secrets import secret_keyring  # noqa: F401
from tests.test_provider_checkout import (  # noqa: F401
    SessionLocal,
    isolated_cart_database,
    prepare,
    setup,
)


@pytest.fixture(autouse=True)
def legacy_binding(monkeypatch, secret_keyring):  # noqa: F811
    monkeypatch.setenv("INFINITEPAY_TENANT_BINDINGS", json.dumps({str(FIXTURE_TENANT_ID): "LEGACY"}))
    monkeypatch.setenv("INFINITEPAY_BINDING_LEGACY_CREDENTIAL_ENV", "development")
    monkeypatch.setenv("INFINITEPAY_BINDING_LEGACY_API_KEY", "synthetic-legacy-key")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://pick.example.test")


def install(db, value, handle="synthetic_handle"):
    lock_payment_account(db, FIXTURE_TENANT_ID)
    settings = db.scalar(select(InfinitePaySettings).where(InfinitePaySettings.tenant_id == FIXTURE_TENANT_ID))
    target = canonical_proposal(ReceiverInput(handle=handle), settings.version, True, True,
        db=db, tenant_id=FIXTURE_TENANT_ID, api_key=SecretStr(value))
    result = apply_proposal(db, tenant_id=FIXTURE_TENANT_ID, admin_id=settings.admin_user_id, target=target)
    identity = (result.credential_id, result.version, result.handle)
    db.commit()
    return identity


def mock_remote(monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: original(transport=httpx.MockTransport(handler)))


def callback(db, payment, *, transaction="synthetic-transaction"):
    request = Request({"type": "http", "method": "GET", "path": "/infinitepay/return", "headers": [],
                       "client": ("127.0.0.1", 1234), "query_string": b""})
    return main.infinitepay_return(request, order_nsu=str(payment.id), transaction_nsu=transaction,
                                  slug="synthetic-slug", db=db)


def test_checkout_and_confirmation_use_original_snapshot_after_replacement(monkeypatch):
    owner, _, _, revision = setup()
    seen = []

    def remote(request):
        seen.append((request.url.path, request.headers["x-api-key"], json.loads(request.content)))
        if request.url.path == "/links":
            return httpx.Response(200, json={"url": "https://checkout.infinitepay.io/synthetic/link"})
        return httpx.Response(200, json={"success": True, "paid": True, "amount": 2100,
            "paid_amount": 2100, "installments": 1, "capture_method": "credit_card"})

    mock_remote(monkeypatch, remote)
    with SessionLocal() as db:
        original, version, handle = install(db, "synthetic-old-managed")
        payment = prepare(db, owner, revision)
        payment_id = payment.id
        db.commit()
        provider = operational_provider(tenant_id=payment.tenant_id, db=db, credential_id=payment.credential_id,
                                       redirect_url="https://pick.example.test/api/infinitepay/return")
        assert provider is not None
        issue_provider_payment(db, payment_id, provider)
        provider.close()
        assert (payment.credential_id, payment.configuration_version, payment.handle_snapshot) == (original, version, handle)
        install(db, "synthetic-new-managed", "new_handle")
        response = callback(db, payment)
        assert response.status_code == 303
        db.refresh(payment)
        assert payment.state == "confirmed" and payment.credential_id == original
        assert all(order.payment_status == "confirmed" for order in db.scalars(
            select(SaleOrder).where(SaleOrder.provider_payment_id == payment_id)))
        assert callback(db, payment).status_code == 303
    assert [entry[0] for entry in seen] == ["/links", "/payment_check"]
    assert all(entry[1] == "synthetic-old-managed" and entry[2]["handle"] == "synthetic_handle" for entry in seen)


def test_legacy_purchase_does_not_switch_to_current_managed_key(monkeypatch):
    owner, _, _, revision = setup()
    seen = []

    def remote(request):
        seen.append(request.headers["x-api-key"])
        return httpx.Response(200, json={"success": True, "paid": False})

    mock_remote(monkeypatch, remote)
    with SessionLocal() as db:
        payment = prepare(db, owner, revision)
        db.commit()
        issue_provider_payment(db, payment.id, SyntheticPaymentProvider("accepted"))
        assert payment.credential_id is None
        install(db, "synthetic-new-managed")
        callback(db, payment)
        db.refresh(payment)
        assert payment.state == "awaiting_payment" and payment.credential_id is None
    assert seen == ["synthetic-legacy-key"]


def test_missing_master_blocks_new_checkout_before_reservation_and_preserves_pix(monkeypatch):
    owner, _, _, revision = setup()
    with SessionLocal() as db:
        install(db, "synthetic-managed")
        monkeypatch.delenv("INTEGRATION_SECRET_KEYS")
        methods = payment_methods(db, tenant_id=FIXTURE_TENANT_ID)
        assert methods["pix_available"] and not methods["card_available"]
        with pytest.raises(CheckoutError, match="Cartão indisponível"):
            prepare(db, owner, revision)
        db.rollback()
        assert db.scalar(select(func.count()).select_from(PhotoSelection)) == 3
        assert db.scalar(select(func.count()).select_from(ProviderPayment)) == 0


def test_credential_update_racing_checkout_freezes_one_complete_configuration():
    if auth.engine.dialect.name != "postgresql":
        pytest.skip("Lock de conta exige PostgreSQL descartável")
    owner, _, _, revision = setup()
    with SessionLocal() as db:
        old = install(db, "synthetic-old", "old_handle")
    barrier = Barrier(2)

    def checkout():
        with SessionLocal() as db:
            barrier.wait(timeout=15)
            payment = prepare(db, owner, revision)
            snapshot = (payment.credential_id, payment.configuration_version, payment.handle_snapshot)
            db.commit()
            return snapshot

    def replace():
        with SessionLocal() as db:
            barrier.wait(timeout=15)
            return install(db, "synthetic-new", "new_handle")

    with ThreadPoolExecutor(max_workers=2) as pool:
        future, replacement = pool.submit(checkout), pool.submit(replace)
        snapshot, new = future.result(timeout=30), replacement.result(timeout=30)
    assert snapshot in (old, new)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ProviderPayment)) == 1


def test_foreign_credential_reference_fails_even_with_legacy_binding():
    setup()
    with SessionLocal() as db:
        install(db, "synthetic-managed")
        assert operational_provider(tenant_id=FIXTURE_TENANT_ID, db=db, credential_id=uuid4(),
            redirect_url="https://pick.example.test/api/infinitepay/return") is None
