"""Webhook sem confiança no payload; consulta com snapshot da própria compra."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import main
from app.auth import NotificationEvent, ProviderPayment, SaleOrder, engine
from app.payment_provider import ProviderTransportError, SyntheticPaymentProvider
from tests.test_provider_cart_recovery import decision, preview
from tests.test_provider_cart_recovery_api import case as _case
from tests.test_provider_cart_recovery_api import isolated_cart_database as _isolated
from tests.test_provider_cart_recovery_api import synthetic_infinitepay_binding as _binding
from tests.test_provider_checkout import SessionLocal

case = _case
isolated_cart_database = _isolated
synthetic_infinitepay_binding = _binding


def candidate(case, **extra):
    return {"order_nsu": str(case["payment"]), "transaction_nsu": "synthetic-webhook",
            "invoice_slug": "synthetic-slug", "capture_method": "pix", "amount":1, **extra}


class PixProvider(SyntheticPaymentProvider):
    def __init__(self, outcome="verified", method="pix"):
        super().__init__(check_outcome=outcome)
        self.method = method

    def check_payment(self, request):
        return super().check_payment(request).model_copy(update={"capture_method":self.method, "verification_profile":"infinitepay-public-v1"})


def inject(monkeypatch, provider):
    seen = []
    monkeypatch.setattr(main, "public_app_origin", lambda: "https://synthetic.example.test")
    def factory(**values):
        seen.append({key:val for key,val in values.items() if key != "db"})
        return provider
    monkeypatch.setattr(main, "operational_provider", factory)
    return seen


@pytest.mark.parametrize("method", ["pix", "credit_card"])
def test_webhook_confirma_por_consulta_metodo_real_e_idempotencia(case, monkeypatch, method):
    provider = PixProvider(method=method)
    seen = inject(monkeypatch, provider)
    body = candidate(case, capture_method="forged", amount=1)
    browser = TestClient(main.app)
    for _ in range(2):
        response = browser.post("/infinitepay/webhook", json=body)
        assert response.status_code == 200, response.text
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        assert payment.state == "confirmed" and payment.capture_method == method
        assert all(row.payment_status == "confirmed" for row in db.scalars(select(SaleOrder).where(
            SaleOrder.provider_payment_id == payment.id)))
        assert seen[0]["tenant_id"] == payment.tenant_id
        assert seen[0]["credential_id"] == payment.credential_id
        assert provider.check_calls[0].expected_total_cents == payment.total_cents
        assert db.scalar(select(func.count(NotificationEvent.id)).where(
            NotificationEvent.event_key == f"provider-payment-confirmed:{payment.id}:{payment.revision_number}")) == 1


@pytest.mark.parametrize("outcome", ["unknown", "unpaid", "mismatch"])
def test_payload_nao_confirma_sem_consulta_verificada(case, monkeypatch, outcome):
    inject(monkeypatch, PixProvider(outcome))
    response = TestClient(main.app).post("/infinitepay/webhook", json=candidate(case))
    assert response.status_code == (200 if outcome == "mismatch" else 400)
    with SessionLocal() as db:
        assert db.get(ProviderPayment, case["payment"]).state != "confirmed"
        assert not db.scalar(select(func.count(SaleOrder.id)).where(
            SaleOrder.provider_payment_id == case["payment"], SaleOrder.payment_status == "confirmed"))


def test_erro_transitorio_permite_retry_sem_reemitir_checkout(case, monkeypatch):
    provider = PixProvider()
    original = provider.check_payment
    def fail(_request):
        raise ProviderTransportError("synthetic-hidden-secret")
    provider.check_payment = fail
    inject(monkeypatch, provider)
    browser = TestClient(main.app)
    response = browser.post("/infinitepay/webhook", json=candidate(case))
    assert response.status_code == 400 and "secret" not in response.text
    provider.check_payment = original
    assert browser.post("/infinitepay/webhook", json=candidate(case)).status_code == 200
    assert not provider.create_calls


def test_limite_preserva_tentativas_mesmo_quando_consulta_falha(case, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "2")
    calls = []
    provider = PixProvider()

    def fail(request):
        calls.append(request.payment_id)
        raise ProviderTransportError("synthetic")

    provider.check_payment = fail
    inject(monkeypatch, provider)
    browser = TestClient(main.app)
    assert [browser.post("/infinitepay/webhook", json=candidate(case)).status_code
            for _ in range(3)] == [400, 400, 429]
    assert len(calls) == 2 and not provider.create_calls
    with SessionLocal() as db:
        assert db.get(ProviderPayment, case["payment"]).state != "confirmed"


def test_schema_tamanho_e_eventos_nao_financeiros_nao_confirmam(case, monkeypatch):
    provider = PixProvider()
    inject(monkeypatch, provider)
    browser = TestClient(main.app)
    for body in ({}, candidate(case, transaction_nsu=" "), candidate(case, order_nsu="bad")):
        assert browser.post("/infinitepay/webhook", json=body).status_code == 400
    assert browser.post("/infinitepay/webhook", content=b"x"*16385).status_code == 400
    assert browser.post("/infinitepay/webhook", json=candidate(case, event="refunded")).status_code == 200
    assert not provider.check_calls
    assert browser.post("/infinitepay/webhook", json=candidate(case, order_nsu=str(uuid4()))).status_code == 200
    assert not provider.check_calls


def test_retorno_tardio_em_reaberta_nao_confirma_cancelados(case, monkeypatch):
    decision(case, preview(case))
    inject(monkeypatch, PixProvider())
    assert TestClient(main.app).post("/infinitepay/webhook", json=candidate(case)).status_code == 200
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        assert payment.state == "exception" and payment.capture_method is None
        assert all(row.payment_status == "cancelled" for row in db.scalars(select(SaleOrder).where(
            SaleOrder.provider_payment_id == payment.id)))


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Concorrência exige locks de linha PostgreSQL")
def test_webhooks_concorrentes_confirmam_uma_vez(case, monkeypatch):
    inject(monkeypatch, PixProvider())
    def send(_):
        return TestClient(main.app).post("/infinitepay/webhook", json=candidate(case)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(send, range(2))) == [200,200]
    with SessionLocal() as db:
        payment = db.get(ProviderPayment, case["payment"])
        assert payment.state == "confirmed"
        assert db.scalar(select(func.count(NotificationEvent.id)).where(
            NotificationEvent.event_key == f"provider-payment-confirmed:{payment.id}:{payment.revision_number}")) == 1


@pytest.mark.parametrize("outcome", ["verified", "unknown", "unpaid", "mismatch", "transport_error"])
def test_retorno_abre_destino_coerente_com_confirmacao(case, monkeypatch, outcome):
    provider = PixProvider(outcome if outcome != "transport_error" else "verified")
    if outcome == "transport_error":
        def fail(_request):
            raise ProviderTransportError("synthetic")
        provider.check_payment = fail
    inject(monkeypatch, provider)
    response = TestClient(main.app).get("/infinitepay/return", params={
        "order_nsu": str(case["payment"]), "transaction_nsu": "synthetic-return",
        "slug": "synthetic-slug",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == (
        f"/library/purchases#payment-{case['payment']}" if outcome in {"verified", "mismatch"}
        else "/library/cart")
    assert not provider.create_calls
