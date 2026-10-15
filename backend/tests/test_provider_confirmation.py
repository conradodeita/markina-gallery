from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import main
from app.auth import (
    AdminUser,
    Client,
    NotificationEvent,
    ProviderPayment,
    ProviderPaymentCorrection,
    ProviderPaymentReceipt,
    SaleOrder,
)
from app.payment_provider import PaymentCheckRequest, SyntheticPaymentProvider
from app.provider_checkout import issue_provider_payment
from app.provider_confirmation import apply_payment_check, place_payment_hold
from tests.tenant_fixtures import FIXTURE_TENANT_ID, fixture_client_cookie
from tests.test_provider_checkout import SessionLocal as _SessionLocal
from tests.test_provider_checkout import isolated_cart_database as _isolated_cart_database
from tests.test_provider_checkout import prepare, setup

SessionLocal = _SessionLocal
isolated_cart_database = _isolated_cart_database


def prepare_awaiting_payment():
    owner_id, _, _, revision = setup()
    with SessionLocal() as db:
        payment = prepare(db, owner_id, revision)
        payment_id = payment.id
        db.commit()
        issue_provider_payment(db, payment_id, SyntheticPaymentProvider("accepted"))
        db.commit()
    return payment_id


def verified_result(db, payment, **overrides):
    result = SyntheticPaymentProvider(check_outcome="verified").check_payment(PaymentCheckRequest(
        payment_id=payment.id,
        tenant_id=payment.tenant_id,
        handle=payment.handle_snapshot,
        transaction_nsu=f"synthetic-{payment.id}",
        slug="synthetic-slug",
        expected_total_cents=payment.total_cents,
    ))
    # A simulação representa a fronteira pública configurada no snapshot local;
    # incompatibilidades continuam sendo exercitadas pelos overrides explícitos.
    return result.model_copy(update={"verification_profile": payment.verification_profile, **overrides})


def test_evidencia_sintetica_confirma_o_aggregate_em_uma_transacao():
    payment_id = prepare_awaiting_payment()
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, payment_id)
        result = verified_result(db, payment)
        applied = apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        assert applied.confirmed and applied.state == "confirmed" and not applied.duplicate
        db.commit()
        orders = list(db.scalars(select(SaleOrder).where(SaleOrder.provider_payment_id == payment_id)))
        assert len(orders) == 2
        assert all(order.payment_status == "confirmed" and order.confirmed_at for order in orders)
        assert sum(order.total_cents for order in orders) == payment.total_cents == 2100
        assert payment.provider_transaction_nsu == result.transaction_nsu and payment.confirmed_at
        assert db.scalar(select(func.count(ProviderPaymentReceipt.id)).where(
            ProviderPaymentReceipt.payment_id == payment_id,
            ProviderPaymentReceipt.state == "verified")) == 1
        assert db.scalar(select(func.count(NotificationEvent.id)).where(
            NotificationEvent.event_key == f"provider-payment-confirmed:{payment_id}:{payment.revision_number}")) == 1


@pytest.mark.parametrize("override", [
    {"outcome": "mismatch"},
    {"tenant_id": uuid4()},
    {"payment_id": uuid4()},
    {"handle": "other_photographer"},
    {"slug": "other-slug"},
    {"amount_cents": 2099},
    {"capture_method": "pix"},
    {"verification_profile": "other-profile"},
])
def test_evidencia_incompatível_abre_exceção_sem_confirmar_pedidos(override):
    payment_id = prepare_awaiting_payment()
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, payment_id)
        result = verified_result(db, payment, **override)
        applied = apply_payment_check(db, payment.id, requested_slug="synthetic-slug", result=result)
        assert applied.state == "exception" and not applied.confirmed
        db.commit()
        assert payment.state == "exception"
        assert db.scalar(select(func.count(SaleOrder.id)).where(
            SaleOrder.provider_payment_id == payment_id,
            SaleOrder.payment_status == "confirmed")) == 0
        assert db.scalar(select(func.count(NotificationEvent.id)).where(
            NotificationEvent.event_key.like(f"provider-payment-confirmed:{payment_id}:%"))) == 0


@pytest.mark.parametrize("outcome", ["unpaid", "unknown"])
def test_sem_evidência_final_compra_permanece_pendente(outcome):
    payment_id = prepare_awaiting_payment()
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, payment_id)
        result = SyntheticPaymentProvider(check_outcome=outcome).check_payment(PaymentCheckRequest(
            payment_id=payment.id, tenant_id=payment.tenant_id, handle=payment.handle_snapshot,
            transaction_nsu=f"synthetic-{payment.id}", slug="synthetic-slug",
            expected_total_cents=payment.total_cents,
        ))
        applied = apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        assert applied.state == "awaiting_payment" and not applied.confirmed
        db.commit()
        assert payment.state == "awaiting_payment"
        assert db.scalar(select(func.count(SaleOrder.id)).where(
            SaleOrder.provider_payment_id == payment_id,
            SaleOrder.payment_status == "confirmed")) == 0


def test_replay_da_mesma_evidência_e_idempotente():
    payment_id = prepare_awaiting_payment()
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, payment_id)
        result = verified_result(db, payment)
        apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        db.commit()
        replay = apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        assert replay.confirmed and replay.duplicate
        db.commit()
        assert db.scalar(select(func.count(ProviderPaymentReceipt.id)).where(
            ProviderPaymentReceipt.payment_id == payment_id)) == 1
        assert db.scalar(select(func.count(NotificationEvent.id)).where(
            NotificationEvent.event_key == f"provider-payment-confirmed:{payment_id}:{payment.revision_number}")) == 1


def test_falha_ao_persistir_aviso_rollbacka_toda_confirmacao(monkeypatch):
    from app import provider_confirmation

    payment_id = prepare_awaiting_payment()
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, payment_id)
        result = verified_result(db, payment)

        def fail_outbox(*_args, **_kwargs):
            raise RuntimeError("synthetic outbox failure")

        monkeypatch.setattr(provider_confirmation, "enqueue_event", fail_outbox)
        with pytest.raises(RuntimeError, match="outbox failure"):
            apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        db.rollback()
        assert db.get(ProviderPayment, payment_id).state == "awaiting_payment"
        assert db.scalar(select(func.count(SaleOrder.id)).where(
            SaleOrder.provider_payment_id == payment_id,
            SaleOrder.payment_status == "confirmed")) == 0
        assert db.scalar(select(func.count(ProviderPaymentReceipt.id)).where(
            ProviderPaymentReceipt.payment_id == payment_id)) == 0


def test_historico_cliente_agrupa_checkout_de_cartao_e_so_exibe_url_pendente():
    payment_id = prepare_awaiting_payment()
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, payment_id)
        client = db.get(Client, payment.client_id)
        phone = client.phone_e164
        other_phone = db.scalar(select(Client.phone_e164).where(
            Client.tenant_id == payment.tenant_id, Client.id != payment.client_id))
        assert payment.tenant_id == FIXTURE_TENANT_ID
    with TestClient(main.app) as browser:
        fixture_client_cookie(browser, phone)
        response = browser.get("/library/purchases")
    assert response.status_code == 200
    assert len(response.json()["provider_payment_groups"]) == 1
    with TestClient(main.app) as browser:
        fixture_client_cookie(browser, other_phone)
        other_response = browser.get("/library/purchases")
    assert other_response.status_code == 200
    assert other_response.json().get("provider_payment_groups", []) == []

    assert response.status_code == 200
    body = response.json()
    groups = body["provider_payment_groups"]
    assert [group["id"] for group in groups] == [str(payment_id)]
    assert groups[0]["state"] == "awaiting_payment"
    assert groups[0]["total_cents"] == 2100 and len(groups[0]["orders"]) == 2
    assert groups[0]["checkout_url"].startswith("https://checkout.example.invalid/")
    assert len(body["orders"]) == 0
    assert "transaction_nsu" not in str(body)
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, payment_id)
        result = verified_result(db, payment)
        apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        db.commit()
    with TestClient(main.app) as browser:
        fixture_client_cookie(browser, phone)
        confirmed = browser.get("/library/purchases").json()["provider_payment_groups"][0]
    assert confirmed["state"] == "confirmed" and confirmed["checkout_url"] is None


def test_admin_payment_queue_identifica_metodo_sem_duplicar_receita(monkeypatch):
    from app.auth import Client

    payment_id = prepare_awaiting_payment()
    request = Request({
        "type": "http", "method": "GET", "path": "/admin/payment-communications",
        "headers": [], "query_string": b"", "scheme": "https",
        "server": ("pickyourpic.test", 443), "client": ("127.0.0.1", 50000),
    })
    monkeypatch.setattr(main, "directory_tenant_id", lambda *_args: FIXTURE_TENANT_ID)
    monkeypatch.setattr(main, "require_admin", lambda *_args: None)
    monkeypatch.setattr(main, "require_active_owner", lambda *_args: None)
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, payment_id)
        assert db.get(Client, payment.client_id).tenant_id == FIXTURE_TENANT_ID
        result = verified_result(db, payment)
        apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        db.commit()
        orders = list(db.scalars(select(SaleOrder).where(SaleOrder.provider_payment_id == payment_id)))
        expected_revenue = sum(order.total_cents for order in orders)
        result = main.list_payment_communications(
            request, query=None, parent_gallery_id=None, financial_status=None,
            delivery_status=None, created_from=None, created_to=None,
            cursor=None, limit=20, db=db,
        )
        order_payload = next(item for group in result["groups"] for item in group["orders"]
                             if item.get("provider_payment_id") == str(payment_id))
        statistics = [main.statistics_data(
            db, tenant_id=payment.tenant_id, starts_at=None, ends_at=None,
            client_id=payment.client_id, parent_gallery_id=None,
            derived_gallery_id=order.derived_gallery_id, event_name=None,
        ) for order in orders]
    assert order_payload["payment_method"] == "credit_card"
    assert order_payload["provider_payment_state"] == "confirmed"
    assert order_payload["financial_status"] == "confirmed"
    assert result["summary"]["confirmed_cents"] == expected_revenue
    assert sum(row["revenue_cents"] for row in statistics) == expected_revenue


def test_correcao_auditada_poe_em_hold_e_bloqueia_replay_antigo(monkeypatch):
    from app import notification_delivery

    payment_id = prepare_awaiting_payment()
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, payment_id)
        result = verified_result(db, payment)
        apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        db.commit()
        event = db.scalar(select(NotificationEvent).where(
            NotificationEvent.event_key == f"provider-payment-confirmed:{payment.id}:{payment.revision_number}"))
        item = SimpleNamespace(tenant_id=payment.tenant_id, recipient_role="client", recipient_id=payment.client_id)

        def owned(_db, model, record_id, *, tenant_id):
            row = db.get(model, record_id)
            return row if row is not None and row.tenant_id == tenant_id else None

        monkeypatch.setattr(notification_delivery, "require_active_owner", lambda *_args: None)
        monkeypatch.setattr(notification_delivery, "owned_record", owned)
        monkeypatch.setattr(notification_delivery, "client_has_operational_membership",
                            lambda *_args, **_kwargs: True)
        assert notification_delivery.recipient_allowed(db, event, item)
        admin = db.scalar(select(AdminUser))
        orders = list(db.scalars(select(SaleOrder).where(SaleOrder.provider_payment_id == payment_id)))
        orders[0].delivery_album_url = "https://photos.app.goo.gl/synthetic"
        orders[0].delivery_revision = 1
        held = place_payment_hold(db, payment.id, actor_admin_id=admin.id,
                                  idempotency_key="correct-1", reason="Revisão sintética")
        assert held.state == "hold" and not held.confirmed
        db.commit()
        db.refresh(payment)
        assert payment.state == "hold" and payment.provider_transaction_nsu == result.transaction_nsu
        assert orders[0].delivery_revision == 2
        assert all(order.payment_status == "pending" and order.confirmed_at is None for order in orders)
        assert not notification_delivery.recipient_allowed(db, event, item)
        assert db.scalar(select(func.count(ProviderPaymentCorrection.id)).where(
            ProviderPaymentCorrection.payment_id == payment_id)) == 1
        assert place_payment_hold(db, payment.id, actor_admin_id=admin.id,
            idempotency_key="correct-1", reason="Revisão sintética").duplicate
        replay = apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        assert replay.state == "hold" and not replay.confirmed
        db.commit()
        assert db.scalar(select(func.count(ProviderPaymentCorrection.id)).where(
            ProviderPaymentCorrection.payment_id == payment_id)) == 1


def test_admin_de_outra_conta_nao_pode_corrigir_pagamento():
    payment_id = prepare_awaiting_payment()
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, payment_id)
        result = verified_result(db, payment)
        apply_payment_check(db, payment.id, requested_slug=result.slug, result=result)
        db.commit()
        with pytest.raises(ValueError, match="administrador"):
            place_payment_hold(db, payment.id, actor_admin_id=uuid4(),
                               idempotency_key="foreign-admin", reason="Teste estrangeiro")
        db.rollback()
        assert db.get(ProviderPayment, payment_id).state == "confirmed"
