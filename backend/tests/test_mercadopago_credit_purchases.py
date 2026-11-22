"""Contratos sintéticos das compras Orders de crédito, sem rede financeira."""

import hashlib
import hmac
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from mercadopago.webhook.validator import InvalidWebhookSignatureError, WebhookSignatureValidator
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.auth import (
    AdminUser,
    AuditEvent,
    AuthSession,
    MercadoPagoAccount,
    MercadoPagoCreditPurchaseEvent,
    MercadoPagoPayment,
    MercadoPagoWebhook,
    PaymentPreferences,
    PhotographerCreditEntry,
    PhotographerCreditPackage,
    PhotographerSignup,
    SaleOrder,
    SaleOrderItem,
    Tenant,
    TenantAdmin,
    TenantCreditWallet,
    now,
    token_hash,
)
from app.checkout import CheckoutError
from app.integration_secrets import IntegrationCipher
from app.mercadopago_credit_purchases import (
    apply_credit_order,
    financial_review_count,
    financial_review_queue,
    prepare_credit_purchase,
    process_next_mercadopago_credit_purchase,
    reconcile_credit_purchase,
    resolve_credit_purchase_review,
    submit_credit_purchase,
    tenant_has_financial_hold,
)
from app.mercadopago_webhook import process_next_mercadopago_event, receive_notification
from app.photographer_credits import reserve_photo_credit, wallet_snapshot
from app.system_monitor.models import PlatformOwner
from tests.test_photographer_credits import create_photo
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
PAYER_ADDRESS = {
    "zip_code": "01311000", "street_name": "Avenida Paulista", "street_number": "1000",
    "neighborhood": "Bela Vista", "city": "São Paulo", "state": "SP",
}


def create_purchase_context(db):
    owner_tenant, buyer_tenant = Tenant(), Tenant()
    db.add_all([owner_tenant, buyer_tenant])
    db.flush()

    owner = AdminUser(
        email="owner-credit-purchase@example.test", password_hash="synthetic",
        totp_secret="synthetic", email_verified=True,
    )
    buyer = AdminUser(
        email="buyer-credit-purchase@example.test", password_hash="synthetic",
        totp_secret="synthetic", email_verified=True,
    )
    owner.tenant_memberships.append(TenantAdmin(tenant_id=owner_tenant.id))
    buyer.tenant_memberships.append(TenantAdmin(tenant_id=buyer_tenant.id))
    db.add_all([owner, buyer])
    db.flush()
    db.add_all([
        PlatformOwner(singleton=1, admin_user_id=owner.id, authorization_reference="synthetic"),
        TenantCreditWallet(tenant_id=owner_tenant.id, mode="unmetered"),
        TenantCreditWallet(tenant_id=buyer_tenant.id, mode="finite"),
    ])
    db.flush()
    package = PhotographerCreditPackage(
        name="Pacote sintético", description="Sem cobrança real", credit_quantity=12,
        price_cents=1500, currency_code="BRL", active=True,
        created_by_admin_id=owner.id, updated_by_admin_id=owner.id,
    )
    db.add(package)
    account_id = uuid4()
    cipher = IntegrationCipher()
    db.add(MercadoPagoAccount(
        id=account_id,
        tenant_id=owner_tenant.id,
        seller_id="123456789",
        public_key="APP_USR-synthetic-public",
        access_token_envelope=cipher.encrypt(
            "APP_USR-synthetic-token", tenant_id=owner_tenant.id, credential_id=account_id,
        ).payload(),
        webhook_secret_envelope=cipher.encrypt(
            "synthetic-webhook-secret", tenant_id=owner_tenant.id, credential_id=account_id,
        ).payload(),
        test_account=True,
        status="active",
    ))
    db.flush()
    db.add(PaymentPreferences(
        tenant_id=owner_tenant.id, account_id=account_id, mercadopago_enabled=True,
    ))
    db.flush()
    return owner_tenant, buyer_tenant, owner, buyer, package, account_id


def order_resource(purchase, *, state="confirmed", updated_at=None):
    order_state, order_detail = {
        "confirmed": ("processed", "accredited"),
        "initiated": ("created", "created"),
        "pending": ("action_required", "action_required"),
        "processing": ("processing", "processing"),
        "rejected": ("failed", "rejected"),
        "partially_refunded": ("processed", "partially_refunded"),
        "refunded": ("refunded", "refunded"),
        "charged_back": ("charged_back", "charged_back"),
    }[state]
    transaction_state, transaction_detail = order_state, order_detail
    total = f"{purchase.total_cents // 100}.{purchase.total_cents % 100:02d}"
    return {
        "id": f"ORD{purchase.id.hex[:20]}",
        "type": "online",
        "status": order_state,
        "status_detail": order_detail,
        "external_reference": purchase.external_reference,
        "total_amount": total,
        "total_paid_amount": total if state == "confirmed" else "0.00",
        "currency_id": "BRL",
        "user_id": "123456789",
        "live_mode": False,
        "last_updated_date": (updated_at or now()).isoformat(),
        "transactions": {"payments": [{
            "id": f"PAY{purchase.id.hex[:20]}",
            "status": transaction_state,
            "status_detail": transaction_detail,
            "amount": total,
            "payment_method": {"id": "visa", "type": "credit_card"},
        }]},
    }


def prepare(db, buyer_tenant, buyer, package, suffix):
    return prepare_credit_purchase(
        db,
        tenant_id=buyer_tenant.id,
        buyer_admin_id=buyer.id,
        package_id=package.id,
        idempotency_key=f"synthetic-credit-purchase-{suffix}",
    )


def _activate_incomplete_website_signup(db, tenant, buyer):
    row = PhotographerSignup(
        photographer_name="Fotógrafa sintética",
        email=buyer.email,
        state="active",
        otp_expires_at=now(),
        reserved_admin_id=buyer.id,
        reserved_tenant_id=tenant.id,
        activated_tenant_id=tenant.id,
        activated_at=now(),
    )
    db.add(row)
    db.flush()
    return row


def test_gate_recusa_nova_compra_e_submit_de_order_ainda_nao_iniciada(
    client_db, monkeypatch,
):
    _owner_tenant, buyer_tenant, _owner, buyer, package, _account_id = create_purchase_context(client_db)
    started = prepare(client_db, buyer_tenant, buyer, package, "started-before-onboarding")
    unsubmitted = prepare(client_db, buyer_tenant, buyer, package, "prepared-before-onboarding")
    started.method = "credit_card"
    started.state = "submitting"
    started.submitted_at = now()
    client_db.flush()
    _activate_incomplete_website_signup(client_db, buyer_tenant, buyer)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PHOTOGRAPHER_TEST_TERMS_ENABLED", "true")

    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app import auth, main

    raw_cookie = "synthetic-incomplete-onboarding-session-token"
    client_db.add(AuthSession(
        token_hash=auth.token_hash(raw_cookie), role="admin", subject_id=buyer.id,
        admin_subject_id=buyer.id, tenant_id=buyer_tenant.id,
        expires_at=now() + timedelta(hours=1),
    ))
    client_db.commit()
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    monkeypatch.setattr(auth, "SessionLocal", factory)
    monkeypatch.setattr(main, "SessionLocal", factory)

    def session_override():
        yield client_db

    main.app.dependency_overrides[main.db_session] = session_override
    try:
        client = TestClient(main.app)
        client.cookies.set("markina_session", raw_cookie)
        blocked = client.post("/admin/credits/purchases/prepare", json={
            "package_id": str(package.id),
            "idempotency_key": str(uuid4()),
        })
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "photographer_onboarding_required"
    finally:
        main.app.dependency_overrides.pop(main.db_session, None)

    # Retry de uma tentativa durável e reconciliação não são novos checkouts.
    assert prepare_credit_purchase(
        client_db,
        tenant_id=buyer_tenant.id,
        buyer_admin_id=buyer.id,
        package_id=package.id,
        idempotency_key="synthetic-credit-purchase-started-before-onboarding",
    ).id == started.id
    assert submit_credit_purchase(
        client_db,
        tenant_id=buyer_tenant.id,
        purchase_id=started.id,
        method="credit_card",
        data=SimpleNamespace(email="buyer@example.test", identification_number="12345678909",
                             payer_address=SimpleNamespace(model_dump=lambda **_kwargs: PAYER_ADDRESS)),
    ).state == "submitting"

    with pytest.raises(HTTPException) as new_purchase:
        prepare_credit_purchase(
            client_db,
            tenant_id=buyer_tenant.id,
            buyer_admin_id=buyer.id,
            package_id=package.id,
            idempotency_key="synthetic-new-purchase-before-onboarding",
        )
    assert new_purchase.value.status_code == 409
    with pytest.raises(HTTPException) as new_order:
        submit_credit_purchase(
            client_db,
            tenant_id=buyer_tenant.id,
            purchase_id=unsubmitted.id,
            method="credit_card",
            data=SimpleNamespace(email="buyer@example.test", identification_number="12345678909",
                                 payer_address=SimpleNamespace(model_dump=lambda **_kwargs: PAYER_ADDRESS)),
        )
    assert new_order.value.status_code == 409
    client_db.rollback()


def test_reconciliacao_manual_de_compra_de_creditos_tem_rate_limit(client_db, monkeypatch):
    _owner_tenant, buyer_tenant, _owner, buyer, package, _account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "manual-reconcile-rate-limit")
    raw_cookie = "synthetic-credit-purchase-reconcile-session-token"
    client_db.add(AuthSession(
        token_hash=token_hash(raw_cookie),
        role="admin", subject_id=buyer.id, admin_subject_id=buyer.id,
        tenant_id=buyer_tenant.id, expires_at=now() + timedelta(hours=1),
    ))
    client_db.commit()

    from fastapi.testclient import TestClient

    from app import auth, main

    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "5")
    monkeypatch.setenv("AUTH_RATE_LIMIT_WINDOW_MINUTES", "15")
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    monkeypatch.setattr(auth, "SessionLocal", factory)
    monkeypatch.setattr(main, "SessionLocal", factory)

    def session_override():
        yield client_db

    main.app.dependency_overrides[main.db_session] = session_override
    try:
        client = TestClient(main.app)
        client.cookies.set("markina_session", raw_cookie)
        url = f"/admin/credits/purchases/{purchase.id}/reconcile"

        for _ in range(5):
            response = client.post(url)
            assert response.status_code == 200
            assert response.json()["id"] == str(purchase.id)

        limited = client.post(url)
        assert limited.status_code == 429
        assert client_db.scalar(select(func.count(AuditEvent.id)).where(
            AuditEvent.event == "rate_limited.request",
            AuditEvent.subject == f"mercadopago_credit_reconcile:{buyer.id}:testclient",
        )) == 5
    finally:
        main.app.dependency_overrides.pop(main.db_session, None)


@pytest.mark.parametrize("account_lifecycle", ["open", "closing", "closed"])
def test_webhook_de_order_iniciada_confirma_e_revisao_financeira_sem_onboarding(
    client_db, monkeypatch, account_lifecycle,
):
    from app.mercadopago_credit_purchases import apply_credit_order

    _owner_tenant, buyer_tenant, _owner, buyer, package, account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "webhook-incomplete-onboarding")
    purchase.method = "credit_card"
    purchase.state = "submitting"
    purchase.submitted_at = now()
    _activate_incomplete_website_signup(client_db, buyer_tenant, buyer)
    buyer_tenant.lifecycle = account_lifecycle
    client_db.commit()

    resource = order_resource(purchase)
    request_id, timestamp = "synthetic-onboarding-webhook", "1793577600"
    canonical = f"id:{resource['id']};request-id:{request_id};ts:{timestamp};"
    digest = hmac.new(b"synthetic-webhook-secret", canonical.encode(), hashlib.sha256).hexdigest()
    header = f"ts={timestamp},v1={digest}"
    body = {"type": "order", "user_id": "123456789", "data": {"id": resource["id"]}}
    receive_notification(
        client_db, account_id, {"data.id": resource["id"]}, body, header, request_id,
    )

    class SyntheticOrders:
        def get(self, order_id):
            assert order_id == resource["id"]
            return resource

    monkeypatch.setattr(
        "app.mercadopago_webhook.credential_provider",
        lambda account: SyntheticOrders() if account.tenant_id == _owner_tenant.id else None,
    )
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    assert process_next_mercadopago_event(session_factory=factory)
    client_db.expire_all()
    purchase = client_db.get(type(purchase), purchase.id)
    assert purchase.state == "confirmed"
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id)).where(
        PhotographerCreditEntry.tenant_id == buyer_tenant.id,
        PhotographerCreditEntry.entry_type == "purchase",
    )) == 1

    reconciled = []
    monkeypatch.setattr(
        "app.mercadopago_credit_purchases.credential_provider",
        lambda account: (reconciled.append(account.id) or SyntheticOrders())
        if account.tenant_id == _owner_tenant.id else None,
    )
    assert reconcile_credit_purchase(client_db, buyer_tenant.id, purchase.id).state == "confirmed"
    assert reconciled == [account_id]

    refunded = order_resource(purchase, state="refunded", updated_at=now() + timedelta(seconds=5))
    assert apply_credit_order(client_db, purchase, refunded)
    client_db.commit()
    assert financial_review_count(client_db, buyer_tenant.id) == 1
    assert len(financial_review_queue(client_db, _owner.id)) == 1


def test_prepara_por_sessao_e_congela_pacote_na_conta_orders_do_proprietario(client_db):
    _owner_tenant, buyer_tenant, owner, buyer, package, account_id = create_purchase_context(client_db)

    purchase = prepare(client_db, buyer_tenant, buyer, package, "one")
    client_db.commit()

    assert purchase.tenant_id == buyer_tenant.id
    assert purchase.buyer_admin_id == buyer.id
    assert purchase.owner_admin_id == owner.id
    assert purchase.receiver_tenant_id == _owner_tenant.id
    assert purchase.receiver_account_id == account_id
    assert purchase.package_name == "Pacote sintético"
    assert purchase.credit_quantity == 12
    assert purchase.total_cents == 1500
    assert purchase.state == "prepared"

    package.name = "Pacote alterado depois"
    package.credit_quantity = 99
    package.price_cents = 9900
    repeated = prepare(client_db, buyer_tenant, buyer, package, "one")
    assert repeated.id == purchase.id
    assert (repeated.package_name, repeated.credit_quantity, repeated.total_cents) == (
        "Pacote sintético", 12, 1500,
    )
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 0


def test_reconciliador_nao_reprocessa_checkout_ainda_preparado(client_db):
    _owner_tenant, buyer_tenant, _owner, buyer, package, _account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "prepared-not-reconciled")
    purchase.next_check_at = now() - timedelta(minutes=1)
    client_db.commit()

    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    assert not process_next_mercadopago_credit_purchase(session_factory=factory)
    client_db.expire_all()
    assert client_db.get(type(purchase), purchase.id).state == "prepared"


@pytest.mark.parametrize("financial_state", ["partially_refunded", "refunded", "charged_back"])
def test_consulta_manual_descobre_reversao_apos_confirmacao_sem_webhook(
    client_db, monkeypatch, financial_state,
):
    receiver, tenant, _owner, buyer, package, account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, tenant, buyer, package, f"manual-{financial_state}")
    purchase.method = "credit_card"
    purchase.state = "submitting"
    purchase.submitted_at = now()
    assert apply_credit_order(client_db, purchase, order_resource(purchase))
    client_db.commit()
    assert not purchase.active
    calls = []
    resource = order_resource(
        purchase, state=financial_state, updated_at=now() + timedelta(seconds=1),
    )

    class FinancialUpdate:
        def get(self, order_id):
            calls.append(order_id)
            assert order_id == purchase.provider_order_id
            return resource

    def provider_for_receiver(account):
        assert account.id == account_id
        assert account.tenant_id == receiver.id
        assert account.test_account
        return FinancialUpdate()

    monkeypatch.setattr("app.mercadopago_credit_purchases.credential_provider", provider_for_receiver)
    reconciled = reconcile_credit_purchase(client_db, tenant.id, purchase.id)
    client_db.commit()

    assert calls == [purchase.provider_order_id]
    assert reconciled.state == financial_state
    assert reconciled.review_status == "pending"
    assert tenant_has_financial_hold(client_db, tenant.id)
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1
    assert client_db.scalar(select(func.sum(PhotographerCreditEntry.delta))) == package.credit_quantity
    assert client_db.scalar(select(func.count(MercadoPagoCreditPurchaseEvent.id)).where(
        MercadoPagoCreditPurchaseEvent.event_type == financial_state,
    )) == 1
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    assert not process_next_mercadopago_credit_purchase(session_factory=factory)
    assert len(calls) == 1


@pytest.mark.parametrize("terminal_state", ["prepared", "abandoned", "rejected"])
def test_consulta_manual_nao_consulta_checkout_sem_pagamento_finalizado(
    client_db, monkeypatch, terminal_state,
):
    _receiver, tenant, _owner, buyer, package, _account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, tenant, buyer, package, f"skip-{terminal_state}")
    purchase.state = terminal_state
    purchase.active = False
    client_db.commit()

    def no_financial_query(_account):
        pytest.fail("Checkout encerrado sem pagamento não deve consultar o provedor")

    monkeypatch.setattr("app.mercadopago_credit_purchases.credential_provider", no_financial_query)
    assert reconcile_credit_purchase(client_db, tenant.id, purchase.id).state == terminal_state


def test_submit_usa_ordem_e_conta_do_proprietario_sem_criar_pedido_de_fotografia(client_db, monkeypatch):
    owner_tenant, buyer_tenant, _owner, buyer, package, account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "submit")
    provider_requests = []

    class SyntheticOrders:
        def payment_methods(self):
            return [{
                "id": "visa",
                "payment_type_id": "credit_card",
                "status": "active",
                "min_allowed_amount": "0.50",
            }]

        def create(self, body, key):
            provider_requests.append((body, key))
            return order_resource(purchase)

    provider = SyntheticOrders()
    received_accounts = []

    def credential_provider(account):
        received_accounts.append(account)
        return provider

    monkeypatch.setattr(
        "app.mercadopago_credit_purchases.credential_provider", credential_provider,
    )
    response = submit_credit_purchase(
        client_db,
        tenant_id=buyer_tenant.id,
        purchase_id=purchase.id,
        method="credit_card",
        data=SimpleNamespace(
            email="buyer@example.test",
            identification_number="12345678909",
            payer_address=SimpleNamespace(model_dump=lambda **_kwargs: PAYER_ADDRESS),
            token=SecretStr("single-use-synthetic-token"),
            payment_method_id="visa",
        ),
    )
    client_db.commit()

    assert response.state == "confirmed"
    assert received_accounts[0].id == account_id
    assert received_accounts[0].tenant_id == owner_tenant.id
    body, idempotency_key = provider_requests[0]
    assert idempotency_key == purchase.id
    assert body["total_amount"] == "15.00"
    assert body["external_reference"] == str(purchase.id)
    assert body["payer"]["email"] == "buyer@example.test"
    assert body["payer"]["address"] == PAYER_ADDRESS
    assert body["transactions"]["payments"][0]["payment_method"]["token"] == "single-use-synthetic-token"
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id)).where(
        PhotographerCreditEntry.entry_type == "purchase_reversal",
    )) == 0


@pytest.mark.parametrize("canonicalization", ["raw", "legacy_lower"])
def test_webhook_assinado_vai_pela_inbox_e_worker_credita_uma_vez(
    client_db, monkeypatch, canonicalization,
):
    owner_tenant, buyer_tenant, _owner, buyer, package, account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "signed-webhook")
    purchase.method = "credit_card"
    purchase.state = "submitting"
    purchase.submitted_at = now()
    client_db.commit()

    resource = order_resource(purchase)
    request_id = "synthetic-request-1"
    timestamp = "1793577600"
    manifest_id = resource["id"] if canonicalization == "raw" else resource["id"].lower()
    canonical = f"id:{manifest_id};request-id:{request_id};ts:{timestamp};"
    signature = hmac.new(
        b"synthetic-webhook-secret", canonical.encode(), hashlib.sha256,
    ).hexdigest()
    header = f"ts={timestamp},v1={signature}"
    # O SDK 3.6.0 é o oracle independente para a canonicalização atual.
    WebhookSignatureValidator.validate(
        header, request_id, manifest_id, "synthetic-webhook-secret",
    )
    if canonicalization == "legacy_lower":
        with pytest.raises(InvalidWebhookSignatureError):
            WebhookSignatureValidator.validate(
                header, request_id, resource["id"], "synthetic-webhook-secret",
            )
    body = {"type": "order", "user_id": "123456789", "data": {"id": resource["id"]}}

    with pytest.raises(HTTPException) as invalid:
        receive_notification(
            client_db, account_id, {"data.id": resource["id"]}, body,
            "ts=1,v1=" + "0" * 64, request_id,
        )
    assert invalid.value.status_code == 401
    assert client_db.scalar(select(func.count(MercadoPagoWebhook.id))) == 0

    receive_notification(
        client_db, account_id, {"data.id": resource["id"]}, body, header, request_id,
    )
    # Mesmo request assinado não duplica a inbox.
    receive_notification(
        client_db, account_id, {"data.id": resource["id"]}, body, header, request_id,
    )
    assert client_db.scalar(select(func.count(MercadoPagoWebhook.id))) == 1

    class SyntheticOrders:
        def get(self, order_id):
            assert order_id == resource["id"]
            return resource

    monkeypatch.setattr(
        "app.mercadopago_webhook.credential_provider",
        lambda account: SyntheticOrders() if account.tenant_id == owner_tenant.id else None,
    )
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    assert process_next_mercadopago_event(session_factory=factory)
    client_db.expire_all()
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1
    assert client_db.scalar(select(func.count(MercadoPagoPayment.id))) == 0
    assert client_db.scalar(select(func.count(SaleOrder.id))) == 0
    assert client_db.scalar(select(func.count(SaleOrderItem.id))) == 0
    persisted = client_db.get(type(purchase), purchase.id)
    assert persisted.state == "confirmed"
    event = client_db.scalar(select(MercadoPagoWebhook))
    assert event.state == "done"

    # Uma nova entrega com request-id distinto chega à inbox, mas o mesmo
    # snapshot remoto não volta a aplicar o ledger.
    request_id = "synthetic-request-2"
    canonical = f"id:{manifest_id};request-id:{request_id};ts:{timestamp};"
    signature = hmac.new(
        b"synthetic-webhook-secret", canonical.encode(), hashlib.sha256,
    ).hexdigest()
    receive_notification(
        client_db, account_id, {"data.id": resource["id"]}, body,
        f"ts={timestamp},v1={signature}", request_id,
    )
    assert process_next_mercadopago_event(session_factory=factory)
    client_db.expire_all()
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1
    assert client_db.scalar(select(func.count(MercadoPagoWebhook.id))) == 2
    assert client_db.scalar(select(func.count(MercadoPagoWebhook.id)).where(
        MercadoPagoWebhook.state == "done",
    )) == 2


@pytest.mark.parametrize("canonicalization", ["raw", "legacy_lower"])
@pytest.mark.parametrize("tampering", ["secret", "data_id", "request_id", "digest"])
def test_webhook_hmac_recusa_componentes_adulterados(
    client_db, canonicalization, tampering,
):
    _receiver, tenant, _owner, buyer, package, account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, tenant, buyer, package, "tampered-callback")
    client_db.commit()
    data_id = order_resource(purchase)["id"]
    request_id, timestamp = "synthetic-signed-request", "1793577600"
    manifest_id = data_id if canonicalization == "raw" else data_id.lower()
    signed_secret = "wrong-secret" if tampering == "secret" else "synthetic-webhook-secret"
    digest = hmac.new(
        signed_secret.encode(),
        f"id:{manifest_id};request-id:{request_id};ts:{timestamp};".encode(),
        hashlib.sha256,
    ).hexdigest()
    header = f"ts={timestamp},v1={digest}"
    if tampering == "data_id":
        data_id += "x"
    elif tampering == "request_id":
        request_id += "x"
    elif tampering == "digest":
        header = f"ts={timestamp},v1={'0' * 64}"
    body = {"type": "order", "user_id": "123456789", "data": {"id": data_id}}
    with pytest.raises(HTTPException) as rejected:
        receive_notification(
            client_db, account_id, {"data.id": data_id}, body, header, request_id,
        )
    assert rejected.value.status_code == 401
    assert client_db.scalar(select(func.count(MercadoPagoWebhook.id))) == 0
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 0


def test_hold_bloqueia_reserva_de_novo_upload(client_db):
    _owner_tenant, buyer_tenant, _owner, buyer, package, _account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "upload-hold")
    purchase.method = "credit_card"
    purchase.state = "submitting"
    purchase.submitted_at = now()
    assert apply_credit_order(client_db, purchase, order_resource(purchase))
    assert apply_credit_order(
        client_db, purchase,
        order_resource(purchase, state="refunded", updated_at=now() + timedelta(seconds=1)),
    )
    photo = create_photo(client_db, buyer_tenant.id)

    with pytest.raises(HTTPException) as error:
        reserve_photo_credit(
            client_db,
            buyer_tenant.id,
            photo.id,
            photo.storage_key,
            "a" * 64,
            actor_admin_id=buyer.id,
        )
    assert error.value.status_code == 409
    assert "bloqueados" in error.value.detail


def test_pendencia_recusa_aprovacao_tardia_e_snapshot_antigo_nao_criam_credito_duplicado(client_db):
    _owner_tenant, buyer_tenant, _owner, buyer, package, _account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "late-approval")
    purchase.method = "credit_card"
    purchase.state = "submitting"
    purchase.submitted_at = now()
    first_update = now()

    pending = order_resource(purchase, state="pending", updated_at=first_update)
    assert apply_credit_order(client_db, purchase, pending)
    assert purchase.state == "pending"
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 0

    stale_rejection = order_resource(
        purchase, state="rejected", updated_at=first_update - timedelta(seconds=1),
    )
    assert not apply_credit_order(client_db, purchase, stale_rejection)
    assert purchase.state == "pending"

    approval = order_resource(
        purchase, updated_at=first_update + timedelta(seconds=1),
    )
    assert apply_credit_order(client_db, purchase, approval)
    assert purchase.state == "confirmed"
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1
    assert not apply_credit_order(client_db, purchase, pending)
    assert purchase.state == "confirmed"
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1

    rejected = prepare(client_db, buyer_tenant, buyer, package, "rejected")
    rejected.method = "credit_card"
    rejected.state = "submitting"
    rejected.submitted_at = now()
    assert apply_credit_order(client_db, rejected, order_resource(rejected, state="rejected"))
    assert rejected.state == "rejected"
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1


def test_confirmacao_reembolso_e_revisao_nao_regridem_ledger_nem_liberam_outro_hold(client_db):
    _owner_tenant, buyer_tenant, owner, buyer, package, _account_id = create_purchase_context(client_db)
    purchases = [prepare(client_db, buyer_tenant, buyer, package, suffix) for suffix in ("a", "b")]
    for purchase in purchases:
        purchase.method = "credit_card"
        purchase.state = "submitting"
        purchase.submitted_at = now()
    client_db.flush()

    for purchase in purchases:
        snapshot = order_resource(purchase)
        assert apply_credit_order(client_db, purchase, snapshot)
        assert not apply_credit_order(client_db, purchase, snapshot)
    client_db.commit()
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 2
    assert client_db.scalar(select(func.sum(PhotographerCreditEntry.delta))) == 24
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id)).where(
        PhotographerCreditEntry.entry_type == "purchase_reversal",
    )) == 0

    first, second = purchases
    assert apply_credit_order(
        client_db, first,
        order_resource(first, state="partially_refunded", updated_at=now() + timedelta(seconds=1)),
    )
    assert apply_credit_order(
        client_db, second,
        order_resource(second, state="charged_back", updated_at=now() + timedelta(seconds=2)),
    )
    client_db.commit()

    assert financial_review_count(client_db, buyer_tenant.id) == 2
    assert len(financial_review_queue(client_db, owner.id)) == 2
    wallet = wallet_snapshot(client_db, buyer_tenant.id)
    assert wallet["available_credits"] == 24
    assert wallet["financial_review_hold"] is True
    assert wallet["can_upload_content"] is False
    with pytest.raises(CheckoutError, match="bloqueados"):
        prepare(client_db, buyer_tenant, buyer, package, "blocked")

    with pytest.raises(CheckoutError, match="Acesso não autorizado"):
        resolve_credit_purchase_review(
            client_db, owner_admin_id=buyer.id, purchase_id=first.id,
            decision="release", reason="Tentativa sem autoridade",
        )

    resolve_credit_purchase_review(
        client_db, owner_admin_id=owner.id, purchase_id=first.id,
        decision="release", reason="Estorno revisado pelo proprietário",
    )
    assert tenant_has_financial_hold(client_db, buyer_tenant.id)
    resolve_credit_purchase_review(
        client_db, owner_admin_id=owner.id, purchase_id=second.id,
        decision="restrict", reason="Chargeback mantido após revisão",
    )
    assert tenant_has_financial_hold(client_db, buyer_tenant.id)
    resolve_credit_purchase_review(
        client_db, owner_admin_id=owner.id, purchase_id=second.id,
        decision="release", reason="Documentação revisada; acesso liberado",
    )
    client_db.commit()

    assert not tenant_has_financial_hold(client_db, buyer_tenant.id)
    assert financial_review_count(client_db, buyer_tenant.id) == 0
    assert len(financial_review_queue(client_db, owner.id)) == 0
    assert wallet_snapshot(client_db, buyer_tenant.id)["can_upload_content"] is True
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 2
    assert client_db.scalar(select(func.count(MercadoPagoCreditPurchaseEvent.id)).where(
        MercadoPagoCreditPurchaseEvent.event_type == "owner_reviewed",
    )) == 3


def test_replay_do_mesmo_chargeback_apos_liberacao_nao_reabre_revisao(client_db):
    _owner_tenant, buyer_tenant, owner, buyer, package, _account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "replayed-chargeback")
    purchase.method = "credit_card"
    purchase.state = "submitting"
    purchase.submitted_at = now()
    assert apply_credit_order(client_db, purchase, order_resource(purchase))

    chargeback = order_resource(
        purchase, state="charged_back", updated_at=now() + timedelta(seconds=1),
    )
    assert apply_credit_order(client_db, purchase, chargeback)
    client_db.commit()
    resolve_credit_purchase_review(
        client_db, owner_admin_id=owner.id, purchase_id=purchase.id,
        decision="release", reason="Chargeback analisado manualmente",
    )
    client_db.commit()
    assert not tenant_has_financial_hold(client_db, buyer_tenant.id)

    assert not apply_credit_order(client_db, purchase, chargeback)
    client_db.commit()
    assert purchase.review_status == "released"
    assert not tenant_has_financial_hold(client_db, buyer_tenant.id)
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1
    assert client_db.scalar(select(func.count(MercadoPagoCreditPurchaseEvent.id)).where(
        MercadoPagoCreditPurchaseEvent.event_type == "owner_reviewed",
    )) == 1


def test_estorno_adicional_apos_liberacao_reabre_revisao_financeira(client_db):
    _owner_tenant, buyer_tenant, owner, buyer, package, _account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "reopened-review")
    purchase.method = "credit_card"
    purchase.state = "submitting"
    purchase.submitted_at = now()
    first_update = now()
    assert apply_credit_order(client_db, purchase, order_resource(purchase, updated_at=first_update))
    assert apply_credit_order(
        client_db, purchase,
        order_resource(
            purchase, state="partially_refunded", updated_at=first_update + timedelta(seconds=1),
        ),
    )
    client_db.commit()
    resolve_credit_purchase_review(
        client_db, owner_admin_id=owner.id, purchase_id=purchase.id,
        decision="release", reason="Reembolso parcial analisado",
    )
    client_db.commit()
    assert not tenant_has_financial_hold(client_db, buyer_tenant.id)

    assert apply_credit_order(
        client_db, purchase,
        order_resource(purchase, state="refunded", updated_at=first_update + timedelta(seconds=2)),
    )
    client_db.commit()
    assert purchase.review_status == "pending"
    assert tenant_has_financial_hold(client_db, buyer_tenant.id)
    assert client_db.scalar(select(func.count(PhotographerCreditEntry.id))) == 1
