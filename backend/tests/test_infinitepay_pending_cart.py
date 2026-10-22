"""Pendência no Carrinho não vira PIX manual nem perde reserva ao ser retirada."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import select

from app.auth import (
    AuditEvent,
    PhotoSelection,
    ProviderPayment,
    Role,
    SaleOrder,
    SaleOrderItem,
    engine,
)
from app.provider_confirmation import apply_payment_check
from tests.test_provider_cart_recovery_api import browser_for
from tests.test_provider_cart_recovery_api import case as _case
from tests.test_provider_cart_recovery_api import isolated_cart_database as _isolated
from tests.test_provider_cart_recovery_api import synthetic_infinitepay_binding as _binding
from tests.test_provider_checkout import SessionLocal
from tests.test_provider_confirmation import verified_result

case = _case
isolated_cart_database = _isolated
synthetic_infinitepay_binding = _binding


def pending(browser):
    cart = browser.get("/library/cart")
    assert cart.status_code == 200
    return cart.json()


def path(case):
    return f"/library/cart/checkouts/{case['payment']}"


def frozen(case):
    with SessionLocal() as db:
        return (list(db.execute(select(SaleOrder.id,SaleOrder.payment_status,SaleOrder.total_cents,SaleOrder.frozen_at)
            .where(SaleOrder.provider_payment_id==case["payment"]))),
            list(db.execute(select(SaleOrderItem.id,SaleOrderItem.unit_price_cents).join(SaleOrder,SaleOrder.id==SaleOrderItem.sale_order_id)
            .where(SaleOrder.provider_payment_id==case["payment"]))),
            list(db.execute(select(PhotoSelection.id,PhotoSelection.photo_asset_id))))


def test_checkout_pendente_tem_mesmas_fotos_valor_e_url_no_carrinho_sem_compra_ativa(case):
    browser = browser_for(case["owner"], role=Role.CLIENT)
    with SessionLocal() as db:
        payment = db.get(ProviderPayment,case["payment"])
        expected = payment.checkout_url
    cart = pending(browser)
    checkout = cart["card_payment"]
    assert checkout["id"] == str(case["payment"]) and checkout["checkout_url"] == expected
    assert checkout["payment_methods"] == ["credit_card","pix"]
    assert checkout["quantity"] == 3 and sum(len(order["items"]) for order in checkout["orders"]) == 3
    assert checkout["total_cents"] == 2100
    assert not browser.get("/library/purchases").json().get("provider_payment_groups")
    other = browser_for(case["other"],role=Role.CLIENT)
    assert not pending(other)["card_payment"]
    assert other.delete(path(case),params={"expected_revision":checkout["revision"]}).status_code == 404


def test_esvaziar_pendencia_so_oculta_intencao_sem_apagar_historico_ou_liberar_fotos(case):
    browser = browser_for(case["owner"],role=Role.CLIENT)
    checkout = pending(browser)["card_payment"]
    before = frozen(case)
    params = {"expected_revision":checkout["revision"]}
    assert browser.delete(path(case),params={"expected_revision":999}).status_code == 409
    assert browser.delete(path(case),params=params).status_code == 200
    assert browser.delete(path(case),params=params).status_code == 200
    cart = pending(browser)
    assert cart["card_payment"] is None and not cart["pending_card_payments"] and cart["quantity"] == 0
    assert frozen(case) == before
    assert not browser.get("/library/purchases").json().get("provider_payment_groups")
    with SessionLocal() as db:
        payment = db.get(ProviderPayment,case["payment"])
        assert payment.state == "awaiting_payment" and payment.checkout_url == checkout["checkout_url"]
        assert payment.cart_dismissed_at is not None
        assert len(list(db.scalars(select(AuditEvent).where(AuditEvent.event=="provider_payment.cart_dismissed")))) == 1
        order, photo = db.execute(select(SaleOrder,SaleOrderItem.photo_asset_id_snapshot).join(SaleOrderItem,SaleOrderItem.sale_order_id==SaleOrder.id)
            .where(SaleOrder.provider_payment_id==payment.id)).first()
        db.add(PhotoSelection(tenant_id=payment.tenant_id,client_id=payment.client_id,
            derived_gallery_id=order.derived_gallery_id,parent_gallery_id=order.parent_gallery_id,photo_asset_id=photo))
        db.commit()
    cart = pending(browser)
    assert cart["groups"] and any(group["error"] for group in cart["groups"])
    assert not cart["can_prepare"]


def test_confirmacao_tardia_apos_desistencia_aparece_em_compras_sem_repor_selecao(case):
    browser = browser_for(case["owner"],role=Role.CLIENT)
    checkout = pending(browser)["card_payment"]
    assert browser.delete(path(case),params={"expected_revision":checkout["revision"]}).status_code == 200
    with SessionLocal() as db:
        payment = db.get(ProviderPayment,case["payment"])
        result = verified_result(db,payment,capture_method="pix")
        assert apply_payment_check(db,payment.id,requested_slug=result.slug,result=result).confirmed
        db.commit()
    assert pending(browser)["quantity"] == 0
    group = browser.get("/library/purchases").json()["provider_payment_groups"][0]
    assert group["state"]=="confirmed" and group["capture_method"]=="pix"
    assert group["checkout_url"] is None
    assert browser.delete(path(case),params={"expected_revision":checkout["revision"]}).status_code == 409


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Concorrência exige locks de linha PostgreSQL")
def test_desistencias_concorrentes_sao_idempotentes(case):
    browser = browser_for(case["owner"],role=Role.CLIENT)
    revision = pending(browser)["card_payment"]["revision"]
    def remove(_):
        return browser.delete(path(case),params={"expected_revision":revision}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(remove,range(2)))==[200,200]
    with SessionLocal() as db:
        assert len(list(db.scalars(select(AuditEvent).where(AuditEvent.event=="provider_payment.cart_dismissed"))))==1


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Concorrência exige locks de linha PostgreSQL")
def test_confirmacao_e_desistencia_concorrentes_nao_perdem_pagamento(case):
    browser = browser_for(case["owner"],role=Role.CLIENT)
    revision = pending(browser)["card_payment"]["revision"]
    barrier = Barrier(2)
    def dismiss():
        barrier.wait(timeout=15)
        return browser.delete(path(case),params={"expected_revision":revision}).status_code
    def confirm():
        with SessionLocal() as db:
            payment=db.get(ProviderPayment,case["payment"])
            evidence=verified_result(db,payment,capture_method="pix")
            barrier.wait(timeout=15)
            result=apply_payment_check(db,payment.id,requested_slug=evidence.slug,result=evidence)
            db.commit()
            return result.confirmed
    with ThreadPoolExecutor(max_workers=2) as pool:
        first,second=pool.submit(dismiss),pool.submit(confirm)
        assert first.result(timeout=30) in (200,409)
        assert second.result(timeout=30)
    with SessionLocal() as db:
        payment=db.get(ProviderPayment,case["payment"])
        assert payment.state=="confirmed" and payment.capture_method=="pix"
        assert all(order.payment_status=="confirmed" for order in db.scalars(select(SaleOrder).where(
            SaleOrder.provider_payment_id==payment.id)))
