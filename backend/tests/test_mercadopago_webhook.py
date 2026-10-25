"""Assinatura, inbox durável, estados e confirmação tardia do contrato Orders."""
# ruff: noqa: F811

import hashlib
import hmac
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth import (
    Client,
    MercadoPagoAccount,
    MercadoPagoPayment,
    MercadoPagoWebhook,
    NotificationEvent,
    PaymentPreferences,
    PhotoSelection,
    SaleOrder,
    SessionLocal,
    Tenant,
    now,
)
from app.checkout import CheckoutError
from app.integration_secrets import IntegrationCipher
from app.main import app
from app.mercadopago_checkout import apply_order, external_state, submit_payment
from app.mercadopago_webhook import (
    process_next_mercadopago_event,
    reconcile_next_mercadopago_payment,
)
from tests.test_mercadopago_checkout import commerce, input_data, prepared  # noqa: F401
from tests.test_unified_checkout import isolated_cart_database  # noqa: F401


def send_event(browser, payment, *, request_id="request-1", signed_id="ORDSYNTHETIC1",
               body_id="ORDSYNTHETIC1", seller="123456", secret="synthetic-webhook-secret"):
    timestamp = "1792871000000"
    canonical = f"id:{signed_id.lower()};request-id:{request_id};ts:{timestamp};"
    signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    return browser.post(
        f"/mercadopago/webhooks/{payment.account_id}?data.id={signed_id}&type=order",
        headers={"x-signature": f"ts={timestamp},v1={signature}", "x-request-id": request_id},
        json={"type": "order", "user_id": seller, "data": {"id": body_id, "status": "processed"}})


def pending_payment(commerce):
    client_id, _, _, network = commerce
    network.state = "pending"
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
    return client_id, payment, network


def approve(network):
    network.resource.update(status="processed", status_detail="accredited",
                            total_paid_amount=network.resource["total_amount"],
                            last_updated_date=now().isoformat())
    network.resource["transactions"]["payments"][0].update(
        status="processed", status_detail="accredited")


def test_inbox_valida_assinatura_conta_query_e_deduplica_entrega(commerce):
    _, payment, _ = pending_payment(commerce)
    with TestClient(app) as browser:
        assert send_event(browser, payment, secret="invalid").status_code == 401
        assert send_event(browser, payment, seller="another").status_code == 401
        assert send_event(browser, payment, body_id="ORDOTHER").status_code == 401
        assert send_event(browser, payment).status_code == 200
        assert send_event(browser, payment).status_code == 200
        assert send_event(browser, payment, request_id="request-2").status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count(MercadoPagoWebhook.id))) == 2
        assert db.get(MercadoPagoPayment, payment.id).state == "pending"


def test_worker_consulta_api_e_converge_sem_repetir_confirmacao(commerce):
    _, payment, network = pending_payment(commerce)
    with TestClient(app) as browser:
        assert send_event(browser, payment).status_code == 200
        assert send_event(browser, payment, request_id="request-2").status_code == 200
    approve(network)
    assert process_next_mercadopago_event()
    assert process_next_mercadopago_event()
    assert not process_next_mercadopago_event()
    with SessionLocal() as db:
        assert db.get(MercadoPagoPayment, payment.id).state == "confirmed"
        assert db.scalar(select(func.count(NotificationEvent.id)).where(
            NotificationEvent.event_key == f"mp-confirmed:{payment.id}")) == 1
        assert set(db.scalars(select(MercadoPagoWebhook.state))) == {"done"}


def test_falha_transitoria_reprograma_e_lease_expirado_retoma(commerce):
    _, payment, network = pending_payment(commerce)
    with TestClient(app) as browser:
        assert send_event(browser, payment).status_code == 200
    network.fail = True
    assert process_next_mercadopago_event()
    with SessionLocal() as db:
        event = db.scalar(select(MercadoPagoWebhook))
        assert event.state == "queued" and event.attempts == 1
        event.state = "processing"
        event.lease_until = now() - timedelta(seconds=1)
        event.next_attempt_at = now() - timedelta(seconds=1)
        db.commit()
    network.fail = False
    approve(network)
    assert process_next_mercadopago_event()
    with SessionLocal() as db:
        assert db.get(MercadoPagoPayment, payment.id).state == "confirmed"


def test_resposta_perdida_recupera_id_por_referencia_sem_novo_post(commerce):
    _client_id, payment, network = pending_payment(commerce)
    with SessionLocal() as db:
        stored = db.get(MercadoPagoPayment, payment.id)
        stored.provider_order_id = None
        stored.state = "verification_required"
        db.commit()
    approve(network)
    with TestClient(app) as browser:
        assert send_event(browser, payment).status_code == 200
    assert process_next_mercadopago_event()
    with SessionLocal() as db:
        stored = db.get(MercadoPagoPayment, payment.id)
        assert stored.provider_order_id == "ORDSYNTHETIC1" and stored.state == "confirmed"
    assert len(network.creates) == 1


@pytest.mark.parametrize(("order_status", "order_detail", "tx_status", "tx_detail", "expected"), [
    ("created", "created", "created", "created", "initiated"),
    ("processing", "in_process", "processing", "pending_review_manual", "processing"),
    ("action_required", "waiting_payment", "action_required", "pending_challenge", "pending"),
    ("canceled", "expired", "expired", "expired", "expired"),
    ("failed", "failed", "failed", "insufficient_amount", "rejected"),
    ("canceled", "canceled", "canceled", "canceled", "canceled"),
    ("processed", "partially_refunded", "processed", "partially_refunded", "partially_refunded"),
    ("charged_back", "settled", "charged_back", "settled", "charged_back"),
    ("processed", "accredited", "processing", "in_process", "processing"),
    ("unknown", "unknown", "unknown", "unknown", "verification_required"),
])
def test_estados_de_order_e_transacao_sao_independentes(
    order_status, order_detail, tx_status, tx_detail, expected,
):
    assert external_state({"status": order_status, "status_detail": order_detail},
                          {"status": tx_status, "status_detail": tx_detail}) == expected


def test_parcial_suspende_entrega_e_nao_distribui_fotos_ou_total(commerce):
    client_id, _, _, network = commerce
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        db.commit()
        orders = list(db.scalars(select(SaleOrder).where(
            SaleOrder.mercadopago_payment_id == payment.id)))
        for order in orders:
            order.delivery_album_url = "https://photos.app.goo.gl/example"
        old = [(order.id, order.total_cents, order.delivery_album_url) for order in orders]
        partial = deepcopy(network.resource)
        partial.update(status_detail="partially_refunded", last_updated_date=now().isoformat())
        partial["transactions"]["payments"][0]["status_detail"] = "partially_refunded"
        assert apply_order(db, payment, partial)
        db.commit()
        assert payment.state == "partially_refunded"
        assert all(order.payment_status == "pending" for order in orders)
        assert [(order.id, order.total_cents, order.delivery_album_url) for order in orders] == old
        assert db.scalar(select(func.count(PhotoSelection.id))) == 0


def test_aprovacao_tardia_da_tentativa_antiga_preserva_snapshot_e_detecta_sobreposicao(commerce):
    client_id, payment, network = pending_payment(commerce)
    previous = deepcopy(network.resource)
    with SessionLocal() as db:
        client = db.get(Client, client_id)
        canceled = deepcopy(previous)
        canceled.update(status="canceled", status_detail="canceled",
                        last_updated_date=now().isoformat())
        canceled["transactions"]["payments"][0].update(status="canceled", status_detail="canceled")
        apply_order(db, db.get(MercadoPagoPayment, payment.id), canceled)
        db.commit()
        _, newer = prepared(db, client_id)
        network.resource = None
        # A nova tentativa não precisa ser enviada para demonstrar que revisão atual não é cobrada.
        approve_resource = deepcopy(previous)
        approve_resource.update(status="processed", status_detail="accredited",
                                total_paid_amount="21.00", last_updated_date=now().isoformat())
        approve_resource["transactions"]["payments"][0].update(
            status="processed", status_detail="accredited")
        original = db.get(MercadoPagoPayment, payment.id)
        assert apply_order(db, original, approve_resource)
        db.commit()
        assert original.state == "confirmed" and newer.state == "prepared"
        assert newer.total_cents == original.total_cents == 2100
        # O submit novo volta a validar o material e recusa fotos já compradas.
        with pytest.raises(CheckoutError):
            submit_payment(db, client, newer.id, input_data())


def test_polling_sem_callback_recupera_pendente(commerce):
    _, payment, network = pending_payment(commerce)
    with SessionLocal() as db:
        stored = db.get(MercadoPagoPayment, payment.id)
        stored.next_check_at = now() - timedelta(seconds=1)
        db.commit()
    approve(network)
    assert reconcile_next_mercadopago_payment()
    with SessionLocal() as db:
        assert db.get(MercadoPagoPayment, payment.id).state == "confirmed"


def test_aprovacao_antiga_com_nova_cobranca_enviada_exige_revisao(commerce):
    client_id, old, network = pending_payment(commerce)
    previous = deepcopy(network.resource)
    with SessionLocal() as db:
        canceled = deepcopy(previous)
        canceled.update(status="canceled", status_detail="canceled", last_updated_date=now().isoformat())
        canceled["transactions"]["payments"][0].update(status="canceled", status_detail="canceled")
        assert apply_order(db, db.get(MercadoPagoPayment, old.id), canceled)
        db.commit()
        client, newer = prepared(db, client_id)
        newer = submit_payment(db, client, newer.id, input_data())
        db.commit()
        assert newer.state == "pending" and newer.provider_order_id != old.provider_order_id
        original = db.get(MercadoPagoPayment, old.id)
        previous.update(status="processed", status_detail="accredited", total_paid_amount="21.00",
                        last_updated_date=now().isoformat())
        previous["transactions"]["payments"][0].update(status="processed", status_detail="accredited")
        assert apply_order(db, original, previous)
        db.commit()
        assert original.state == "duplicate_review" and original.confirmed_at
        assert newer.state == "pending" and newer.total_cents == original.total_cents == 2100
        assert set(db.scalars(select(SaleOrder.payment_status))) == {"pending"}
        assert db.scalar(select(func.count(NotificationEvent.id)).where(
            NotificationEvent.event_key == f"mp-confirmed:{old.id}")) == 0
        assert len(network.creates) == 2


def test_worker_nao_processa_financas_de_tenant_suspenso(commerce):
    _, payment, network = pending_payment(commerce)
    with TestClient(app) as browser:
        assert send_event(browser, payment).status_code == 200
    approve(network)
    with SessionLocal() as db:
        db.get(Tenant, payment.tenant_id).status = "suspended"
        db.get(MercadoPagoPayment, payment.id).next_check_at = now() - timedelta(seconds=1)
        db.commit()
    assert not process_next_mercadopago_event()
    assert not reconcile_next_mercadopago_payment()
    with SessionLocal() as db:
        assert db.get(MercadoPagoPayment, payment.id).state == "pending"
        assert db.scalar(select(MercadoPagoWebhook.state)) == "queued"


def test_polling_apos_confirmacao_detecta_reembolso_sem_callback(commerce):
    client_id, _, _, network = commerce
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        assert not payment.active and payment.state == "confirmed"
        payment.next_check_at = now() - timedelta(seconds=1)
        db.commit()
    network.resource.update(status="refunded", status_detail="refunded",
                            last_updated_date=now().isoformat())
    network.resource["transactions"]["payments"][0].update(status="refunded", status_detail="refunded")
    assert reconcile_next_mercadopago_payment()
    with SessionLocal() as db:
        assert db.get(MercadoPagoPayment, payment.id).state == "refunded"
        assert set(db.scalars(select(SaleOrder.payment_status))) == {"cancelled"}


def test_recurso_inconsistente_nao_monopoliza_worker(commerce):
    _, payment, network = pending_payment(commerce)
    with SessionLocal() as db:
        db.get(MercadoPagoPayment, payment.id).next_check_at = now() - timedelta(seconds=1)
        db.commit()
    network.resource["total_amount"] = "0.01"
    assert reconcile_next_mercadopago_payment()
    assert not reconcile_next_mercadopago_payment()
    with SessionLocal() as db:
        stored = db.get(MercadoPagoPayment, payment.id)
        assert stored.state == "verification_required" and stored.check_attempts == 1
        assert stored.error_category == "inconsistent_resource"


@pytest.mark.parametrize("same_receiver", [True, False])
def test_webhook_apos_rotacao_preserva_recebedor_e_versao_original(commerce, same_receiver):
    client_id, _, _, network = commerce
    seller = "123456" if same_receiver else "999999"
    with SessionLocal() as db:
        client, payment = prepared(db, client_id)
        payment = submit_payment(db, client, payment.id, input_data())
        old_account = payment.account_id
        cipher, account_id = IntegrationCipher(), uuid4()
        db.add(MercadoPagoAccount(
            id=account_id, tenant_id=payment.tenant_id, seller_id=seller,
            public_key="APP_USR-new-public-synthetic", test_account=True,
            access_token_envelope=cipher.encrypt("APP_USR-new-token-synthetic",
                tenant_id=payment.tenant_id, credential_id=account_id).payload(),
            webhook_secret_envelope=cipher.encrypt("synthetic-webhook-secret",
                tenant_id=payment.tenant_id, credential_id=account_id).payload()))
        db.flush()
        db.scalar(select(PaymentPreferences)).account_id = account_id
        db.commit()
    network.resource.update(status="refunded", status_detail="refunded",
                            last_updated_date=now().isoformat())
    network.resource["transactions"]["payments"][0].update(status="refunded", status_detail="refunded")
    with TestClient(app) as browser:
        assert send_event(browser, SimpleNamespace(account_id=account_id), seller=seller).status_code == 200
    assert process_next_mercadopago_event()
    with SessionLocal() as db:
        stored = db.get(MercadoPagoPayment, payment.id)
        assert stored.account_id == old_account
        assert stored.state == ("refunded" if same_receiver else "confirmed")
        assert db.scalar(select(MercadoPagoWebhook.state)) == ("done" if same_receiver else "ignored")
