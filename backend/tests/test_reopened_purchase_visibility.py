"""Tentativa encerrada não é compra ativa; evidência tardia permanece visível."""

from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.auth import ProviderPayment, ProviderPaymentReceipt, Role, SaleOrder, now
from app.payment_provider import SyntheticPaymentProvider
from app.provider_checkout import issue_provider_payment
from app.provider_confirmation import apply_payment_check
from tests.test_provider_cart_recovery import decision, preview, state
from tests.test_provider_cart_recovery_api import browser_for, card_orders
from tests.test_provider_cart_recovery_api import case as _case
from tests.test_provider_cart_recovery_api import isolated_cart_database as _isolated
from tests.test_provider_cart_recovery_api import synthetic_infinitepay_binding as _binding
from tests.test_provider_checkout import SessionLocal, prepare
from tests.test_provider_confirmation import verified_result

case = _case
isolated_cart_database = _isolated
synthetic_infinitepay_binding = _binding


def test_reaberta_sai_da_compra_ativa_e_esvaziar_carrinho_preserva_historico(case):
    buyer = browser_for(case["owner"], role=Role.CLIENT)
    admin = browser_for(case["actor"])
    assert buyer.get("/library/cart").json()["card_payment"]["id"] == str(case["payment"])
    decision(case, preview(case))
    before = state(case)
    assert not buyer.get("/library/purchases").json().get("provider_payment_groups")
    dashboard = admin.get("/admin/payment-communications").json()
    assert dashboard["summary"]["orders"] == 0
    assert not dashboard["groups"]
    assert sum(item["selected_count"] for item in dashboard["selections_without_order"]) == 3
    history = admin.get("/admin/payment-communications?financial_status=reopened")
    orders = card_orders(history, case)
    assert len(orders) == 2
    assert all(not row["provider_cart_recovery"]["requires_reconciliation"] for row in orders)
    assert not browser_for(case["other"], role=Role.CLIENT).get("/library/purchases").json().get("provider_payment_groups")
    assert admin.get(f"/admin/payment-communications?financial_status=reopened&client_id={case['other']}").json()["groups"] == []
    exported = admin.get("/admin/payment-communications/export.csv?financial_status=reopened")
    assert exported.status_code == 200
    assert admin.get("/admin/payment-communications/export.csv").status_code == 204
    cart = buyer.get("/library/cart").json()
    for group in cart["groups"]:
        removed = buyer.delete(f"/library/cart/{group['gallery_id']}")
        assert removed.status_code == 200, removed.text
    assert buyer.get("/library/cart").json()["quantity"] == 0
    assert not buyer.get("/library/purchases").json().get("provider_payment_groups")
    assert len(card_orders(admin.get("/admin/payment-communications?financial_status=reopened"), case)) == 2
    after = state(case)
    assert after[:2] == before[:2] and after[3:] == before[3:]
    assert after[2] == []


@pytest.mark.parametrize("receipt_state", ["queued", "processing", "verified", "failed"])
def test_retorno_posterior_volta_para_conferencia_sem_reabrir_ou_confirmar(case, receipt_state):
    decision(case, preview(case))
    before = state(case)
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        db.add(ProviderPaymentReceipt(tenant_id=payment.tenant_id, client_id=payment.client_id,
            payment_id=payment.id, digest="a"*64, transaction_nsu="synthetic-late",
            slug="synthetic-slug", verification_profile=payment.verification_profile, state=receipt_state))
        db.commit()
    _assert_late_conference(case)
    assert state(case) == before


def _assert_late_conference(case):
    buyer, admin = browser_for(case["owner"], role=Role.CLIENT), browser_for(case["actor"])
    group = buyer.get("/library/purchases").json()["provider_payment_groups"][0]
    assert group["id"] == str(case["payment"])
    assert group["requires_reconciliation"] and group["checkout_url"] is None
    orders = card_orders(admin.get("/admin/payment-communications"), case)
    assert len(orders) == 2 and all(row["provider_cart_recovery"]["requires_reconciliation"] for row in orders)
    assert not admin.get("/admin/payment-communications?financial_status=reopened").json()["groups"]
    assert not browser_for(case["other"], role=Role.CLIENT).get("/library/purchases").json().get("provider_payment_groups")
    with SessionLocal() as db:
        assert all(row.payment_status == "cancelled" for row in db.scalars(select(SaleOrder).where(
            SaleOrder.provider_payment_id == case["payment"])))


def test_confirmacao_tardia_real_ignorada_pelo_guard_continua_visivel(case):
    decision(case, preview(case))
    buyer = browser_for(case["owner"], role=Role.CLIENT)
    for group in buyer.get("/library/cart").json()["groups"]:
        assert buyer.delete(f"/library/cart/{group['gallery_id']}").status_code == 200
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        result = apply_payment_check(db, payment.id, requested_slug="synthetic-slug",
                                    result=verified_result(db, payment))
        assert result.state == "exception" and not result.confirmed
        db.commit()
        assert db.scalar(select(ProviderPaymentReceipt.state)) == "ignored"
    _assert_late_conference(case)
    # O helper cria outra sessão da mesma cliente e rotaciona a anterior.
    cart = browser_for(case["owner"], role=Role.CLIENT).get("/library/cart")
    assert cart.status_code == 200
    assert cart.json()["quantity"] == 0


@pytest.mark.parametrize("provider_state", ["awaiting_payment", "verification_required", "hold"])
def test_estado_incompativel_com_reabertura_exige_conferencia_sem_url_antiga(case, provider_state):
    decision(case, preview(case))
    with SessionLocal() as db:
        db.get(ProviderPayment, case["payment"]).state = provider_state
        db.commit()
    _assert_late_conference(case)


def test_recibo_antigo_ignorado_so_reaparece_quando_reprocessado_apos_reabertura(case):
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        earlier = now() - timedelta(minutes=10)
        receipt = ProviderPaymentReceipt(tenant_id=payment.tenant_id, client_id=payment.client_id,
            payment_id=payment.id, digest="b"*64, transaction_nsu="synthetic-old",
            slug="synthetic-slug", verification_profile=payment.verification_profile,
            state="ignored", created_at=earlier, processed_at=earlier)
        db.add(receipt)
        db.commit()
        receipt_id = receipt.id
    decision(case, preview(case))
    buyer = browser_for(case["owner"], role=Role.CLIENT)
    assert not buyer.get("/library/purchases").json().get("provider_payment_groups")
    with SessionLocal() as db:
        db.get(ProviderPaymentReceipt, receipt_id).processed_at = now()
        db.commit()
    _assert_late_conference(case)


def test_nova_compra_aparece_sem_ressuscitar_tentativa_antiga(case):
    decision(case, preview(case))
    buyer = browser_for(case["owner"], role=Role.CLIENT)
    revision = buyer.get("/library/cart").json()["cart_revision"]
    with SessionLocal() as db:
        payment = prepare(db, case["owner"], revision)
        new_id = payment.id
        db.commit()
        issue_provider_payment(db, new_id, SyntheticPaymentProvider("accepted"))
        db.commit()
    assert not buyer.get("/library/purchases").json().get("provider_payment_groups")
    payment = buyer.get("/library/cart").json()["card_payment"]
    assert UUID(payment["id"]) == new_id and payment["status"] == "awaiting_payment"


def test_confirmado_sem_reabertura_continua_em_compras_e_fora_do_historico(case):
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        result = apply_payment_check(db, payment.id, requested_slug="synthetic-slug",
                                    result=verified_result(db, payment))
        assert result.confirmed
        db.commit()
    buyer, admin = browser_for(case["owner"], role=Role.CLIENT), browser_for(case["actor"])
    assert buyer.get("/library/purchases").json()["provider_payment_groups"][0]["state"] == "confirmed"
    assert not admin.get("/admin/payment-communications?financial_status=reopened").json()["groups"]
