"""Rotas administrativas: reabertura não é confirmação PIX nem ação da cliente."""

from uuid import UUID, uuid4

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import auth, main
from app.auth import (
    AdminUser,
    AuditEvent,
    Client,
    DerivedGallery,
    GalleryClientState,
    InfinitePaySettings,
    ParentGalleryRegistration,
    PaymentCommunication,
    PaymentGroup,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    ProviderPayment,
    Role,
    SaleOrder,
    Tenant,
    TenantAdmin,
)
from app.payment_provider import SyntheticPaymentProvider
from app.provider_cart_recovery import RECOVERY_EVENT
from app.provider_checkout import issue_provider_payment
from app.provider_confirmation import apply_payment_check
from app.unified_checkout import cart_payload, prepare_group, report_group
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_provider_cart_recovery import SessionLocal, decision, preview, state
from tests.test_provider_cart_recovery import case as _case
from tests.test_provider_cart_recovery import isolated_cart_database as _isolated
from tests.test_provider_cart_recovery import synthetic_infinitepay_binding as _binding
from tests.test_provider_checkout import prepare, setup
from tests.test_provider_confirmation import verified_result

case = _case
isolated_cart_database = _isolated
synthetic_infinitepay_binding = _binding


def browser_for(subject_id, *, tenant_id=FIXTURE_TENANT_ID, role=Role.ADMIN):
    with SessionLocal() as db:
        if role == Role.ADMIN:
            db.get(AdminUser, subject_id).email_verified = True
            db.flush()
        token = auth.create_session(db, Response(), role, subject_id, tenant_id=tenant_id)
        db.commit()
    browser = TestClient(main.app)
    browser.cookies.set("markina_session", token)
    return browser


def path(case, suffix=""):
    return f"/admin/provider-payments/{case['payment']}/cart-recovery{suffix}"


def payload(plan, **overrides):
    return {"expected_revision": plan["revision"], "expected_fingerprint": plan["fingerprint"],
            "idempotency_key": str(uuid4()), "reason": "Cliente sem retorno precisa refazer a compra",
            "acknowledge_remote_checkout": True, **overrides}


def card_orders(response, case):
    assert response.status_code == 200
    return [order for group in response.json()["groups"] for order in group["orders"]
            if order.get("provider_payment_id") == str(case["payment"])]


def test_previa_e_confirmacao_http_restauram_as_mesmas_fotos_e_projetam_reabertura(case):
    browser = browser_for(case["actor"])
    buyer = browser_for(case["owner"], role=Role.CLIENT)
    assert buyer.get("/library/cart").json()["recovery_revision"] is None
    orders = card_orders(browser.get("/admin/payment-communications"), case)
    assert len(orders) == 2 and all(order["provider_cart_recovery"]["can_reopen"] for order in orders)
    before = state(case)
    response = browser.post(path(case, "/preview"), json={"expected_revision": case["revision"]})
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["restored_quantity"] == 3 and plan["quantity"] == 3
    assert state(case) == before
    body = payload(plan)
    response = browser.post(path(case), json=body)
    assert response.status_code == 200, response.text
    assert not response.json()["already_reopened"]
    after = state(case)
    assert len(after[2]) == 3 and after[4] == 1
    assert browser.post(path(case), json=body).json()["already_reopened"]
    assert state(case) == after
    orders = card_orders(browser.get("/admin/payment-communications"), case)
    assert all(order["provider_cart_recovery"]["reopened_at"]
               and not order["provider_cart_recovery"]["can_reopen"] for order in orders)
    cart = buyer.get("/library/cart").json()
    assert cart["quantity"] == 3 and cart["can_prepare"]
    assert cart["recovery_revision"] and cart["card_payment"] is None
    assert buyer.get("/library/cart").json()["recovery_revision"] == cart["recovery_revision"]
    assert browser_for(case["other"], role=Role.CLIENT).get("/library/cart").json()["recovery_revision"] is None


def test_cliente_e_visitante_nao_podem_liberar_a_propria_compra(case):
    before = state(case)
    for browser in (TestClient(main.app), browser_for(case["owner"], role=Role.CLIENT)):
        response = browser.post(path(case, "/preview"), json={"expected_revision": case["revision"]})
        assert response.status_code in {401, 403}
    assert state(case) == before


def test_tenant_b_nao_consulta_nem_reabre_compra_a(case):
    before = state(case)
    with SessionLocal() as db:
        tenant, actor = Tenant(id=uuid4()), AdminUser(
            email=f"other-{uuid4()}@example.test", password_hash="synthetic", totp_secret="synthetic")
        db.add_all([tenant, actor])
        db.flush()
        db.add(TenantAdmin(tenant_id=tenant.id, admin_user_id=actor.id))
        db.commit()
        other_id, tenant_id = actor.id, tenant.id
    browser = browser_for(other_id, tenant_id=tenant_id)
    plan = preview(case)
    for endpoint, body in ((path(case, "/preview"), {"expected_revision": case["revision"]}),
                           (path(case), payload(plan))):
        response = browser.post(endpoint, json=body)
        assert response.status_code == 404
        assert str(case["owner"]) not in response.text
    assert state(case) == before


@pytest.mark.parametrize("field,value", [("acknowledge_remote_checkout", False),
                                         ("expected_fingerprint", "0" * 64),
                                         ("expected_revision", 999), ("reason", " ")])
def test_decisao_invalida_nao_libera_fotos(case, field, value):
    browser, plan = browser_for(case["actor"]), preview(case)
    before = state(case)
    response = browser.post(path(case), json=payload(plan, **{field: value}))
    assert response.status_code in {409, 422}
    assert state(case) == before


def test_origem_externa_e_tenant_no_body_sao_recusados(case):
    browser = browser_for(case["actor"])
    before = state(case)
    response = browser.post(path(case, "/preview"), json={"expected_revision": case["revision"]},
                            headers={"Origin": "https://untrusted.example.test"})
    assert response.status_code == 403
    response = browser.post(path(case, "/preview"),
                            json={"expected_revision": case["revision"], "tenant_id": str(uuid4())})
    assert response.status_code == 422 and state(case) == before


def test_cartao_confirmado_nao_oferece_reabertura_nem_aceita_previa_antiga(case):
    plan, browser = preview(case), browser_for(case["actor"])
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        evidence = verified_result(db, payment)
        apply_payment_check(db, payment.id, requested_slug=evidence.slug, result=evidence)
        db.commit()
    before = state(case)
    orders = card_orders(browser.get("/admin/payment-communications"), case)
    assert orders and all(not order["provider_cart_recovery"]["can_reopen"] for order in orders)
    assert browser.post(path(case), json=payload(plan)).status_code == 409
    assert state(case) == before and not before[2]


def test_pix_confirmado_nao_e_alvo_de_reabertura(case):
    decision(case, preview(case))
    with SessionLocal() as db:
        owner = db.get(Client, case["owner"])
        group = prepare_group(db, owner)
        db.flush()
        report_group(db, owner, group.id, group.revision, str(uuid4()))
        db.commit()
        group_id = group.id
        communication_id = db.scalar(select(PaymentCommunication.id).where(
            PaymentCommunication.payment_group_id == group_id))
    browser = browser_for(case["actor"])
    confirmed = browser.post(f"/admin/payment-communications/{communication_id}/decision",
        json={"decision": "confirmed", "payment_group_id": str(group_id)})
    assert confirmed.status_code == 200, confirmed.text
    with SessionLocal() as db:
        assert db.get(PaymentGroup, group_id).state == "confirmed"
        assert all(order.payment_status == "confirmed" for order in db.scalars(select(SaleOrder).where(
            SaleOrder.payment_group_id == group_id)))
    response = browser.post(f"/admin/provider-payments/{group_id}/cart-recovery/preview",
                             json={"expected_revision": 1})
    assert response.status_code == 404
    with SessionLocal() as db:
        assert db.get(PaymentGroup, group_id).state == "confirmed"


def test_projecao_reconhece_recuperacao_operacional_antiga_sem_reabrir_novamente(case):
    decision(case, preview(case))
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.event == RECOVERY_EVENT))
        event.event = "provider_payment.owner_recovery"
        event.subject = f"IP_RECOVERY_20261021_V1:{case['payment']}:{case['actor']}:awaiting_payment:2:{uuid4()}"
        db.commit()
    browser = browser_for(case["actor"])
    orders = card_orders(browser.get("/admin/payment-communications"), case)
    assert orders and all(order["provider_cart_recovery"]["reopened_at"]
                         and not order["provider_cart_recovery"]["can_reopen"] for order in orders)
    cart = browser_for(case["owner"], role=Role.CLIENT).get("/library/cart").json()
    assert cart["recovery_revision"] and cart["quantity"] == 3


def test_fotos_canonicas_e_legadas_voltam_sem_reselecao_nem_galeria_extra():
    owner, _, galleries, _ = setup()
    with SessionLocal() as db:
        parent = db.get(DerivedGallery, galleries[0]).parent_gallery_id
        db.add_all([
            ParentGalleryRegistration(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent,
                                      client_id=owner, status="active"),
            GalleryClientState(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent, client_id=owner),
        ])
        folder = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent,
                             name="Pasta comum", status="released", audience_scope="all")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent, folder_id=folder.id,
                           filename="foto-ja-escolhida.jpg", storage_key=f"synthetic/{uuid4()}.jpg")
        db.add(photo)
        db.flush()
        db.add(PhotoSelection(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent,
                              client_id=owner, photo_asset_id=photo.id))
        db.flush()
        selected = set(db.execute(select(PhotoSelection.parent_gallery_id,
            PhotoSelection.derived_gallery_id, PhotoSelection.photo_asset_id).where(
                PhotoSelection.client_id == owner)))
        gallery_count = db.scalar(select(func.count(DerivedGallery.id)))
        payment = prepare(db, owner, cart_payload(db, db.get(Client, owner))["cart_revision"])
        db.commit()
        issue_provider_payment(db, payment.id, SyntheticPaymentProvider("accepted"))
        purchase = {"payment": payment.id, "revision": payment.revision_number,
                    "actor": db.scalar(select(InfinitePaySettings.admin_user_id))}
    browser = browser_for(purchase["actor"])
    response = browser.post(path(purchase, "/preview"), json={"expected_revision": purchase["revision"]})
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["restored_quantity"] == 4 and plan["total_cents"] == 2800
    response = browser.post(path(purchase), json=payload(plan))
    assert response.status_code == 200, response.text
    cart = browser_for(owner, role=Role.CLIENT).get("/library/cart").json()
    assert cart["can_prepare"] and cart["quantity"] == 4
    assert {item["id"] for group in cart["groups"] for item in group["items"]} == {
        str(row[2]) for row in selected}
    with SessionLocal() as db:
        assert set(db.execute(select(PhotoSelection.parent_gallery_id, PhotoSelection.derived_gallery_id,
            PhotoSelection.photo_asset_id).where(PhotoSelection.client_id == owner))) == selected
        assert db.scalar(select(func.count(DerivedGallery.id))) == gallery_count


def test_reabertura_aparece_no_historico_e_rascunho_pix_nao_parece_compra_duplicada(case):
    decision(case, preview(case))
    buyer, admin = browser_for(case["owner"], role=Role.CLIENT), browser_for(case["actor"])
    history = buyer.get("/library/purchases").json()
    original = history["provider_payment_groups"][0]
    assert browser_for(case["other"], role=Role.CLIENT).get("/library/purchases").json().get("provider_payment_groups", []) == []
    before = state(case)
    prepared = buyer.post("/library/cart/prepare")
    assert prepared.status_code == 200, prepared.text
    group_id = prepared.json()["payment"]["id"]
    with SessionLocal() as db:
        drafts = set(db.scalars(select(SaleOrder.id).where(SaleOrder.payment_group_id == group_id)))
        assert len(drafts) == 2
    dashboard = admin.get("/admin/payment-communications").json()
    visible = [order for group in dashboard["groups"] for order in group["orders"]]
    assert len(visible) == 2 and not drafts.intersection({UUID(order["id"]) for order in visible})
    assert original["cart_reopened_at"] and original["state"] == "exception"
    assert original["checkout_url"] is None
    assert all(order["provider_cart_reopened_at"] for order in original["orders"])
    assert sum(selection["selected_count"] for selection in dashboard["selections_without_order"]) == 3
    assert not buyer.get("/library/purchases").json()["payment_groups"]
    assert state(case)[:3] == before[:3] and state(case)[4] == before[4]
    reported = buyer.post(f"/library/payments/{group_id}/report", json={
        "revision": prepared.json()["payment"]["revision"], "idempotency_key": str(uuid4())})
    assert reported.status_code == 200, reported.text
    history = buyer.get("/library/purchases").json()
    assert len(history["payment_groups"]) == 1 and history["payment_groups"][0]["id"] == group_id
    dashboard = admin.get("/admin/payment-communications").json()
    assert dashboard["summary"]["orders"] == 4 and dashboard["summary"]["reported_orders"] == 2
