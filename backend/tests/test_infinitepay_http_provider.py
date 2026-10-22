import json
from uuid import UUID

import httpx
import pytest

from app.payment_provider import (
    CheckoutRequest,
    InfinitePayHttpProvider,
    PaymentCheckRequest,
    ProviderTransportError,
    operational_provider,
)
from app.provider_checkout import _allowed_checkout_url

PAYMENT_ID = UUID("0358e8e9-51c8-462e-a0a3-90b7c45ff6a1")
TENANT_ID = UUID("78f37e04-9389-42a3-8bdf-ecaa95e47a5a")


def _provider(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return InfinitePayHttpProvider(
        redirect_url="https://pick.example.test/checkout/return",
        api_key="synthetic-infinitepay-key",
        webhook_url="https://pick.example.test/api/provider/infinitepay/webhook",
        client=client,
    )


def _checkout_request(methods=("credit_card",)):
    return CheckoutRequest(
        payment_id=PAYMENT_ID,
        tenant_id=TENANT_ID,
        handle="photo-owner", payment_methods=methods,
        items=({"quantity": 2, "price": 500},),
    )


def _check_request():
    return PaymentCheckRequest(
        payment_id=PAYMENT_ID,
        tenant_id=TENANT_ID,
        handle="photo-owner",
        transaction_nsu="provider-transaction-9",
        slug="invoice-9",
        expected_total_cents=1000,
    )


@pytest.mark.parametrize("methods", [(), ("pix",), ("pix", "credit_card"), ("credit_card", "credit_card")])
def test_recusa_meios_fora_do_contrato_sem_criar_checkout(methods):
    with pytest.raises(ValueError, match="Meios de pagamento fora do contrato"):
        _checkout_request(methods)


@pytest.mark.parametrize("methods", [("credit_card",), ("credit_card", "pix")])
@pytest.mark.parametrize("checkout_host", ["checkout.infinitepay.io", "checkout.infinitepay.com.br"])
def test_create_checkout_uses_documented_authenticated_methods_snapshot(checkout_host, methods, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    seen = {}

    def respond(request):
        seen["request"] = request
        return httpx.Response(200, json={"url": f"https://{checkout_host}/photo-owner/abc"})

    provider = _provider(respond)
    result = provider.create_checkout(_checkout_request(methods))
    request = seen["request"]
    assert result.outcome == "accepted"
    assert request.url == "https://api.checkout.infinitepay.io/links"
    assert request.headers["content-type"] == "application/json"
    assert request.headers["x-api-key"] == "synthetic-infinitepay-key"
    assert "authorization" not in request.headers
    assert provider.capabilities.operational
    assert operational_provider() is None
    monkeypatch.setenv("INFINITEPAY_TENANT_BINDINGS", json.dumps({str(TENANT_ID): "OWNER_A"}))
    monkeypatch.setenv("INFINITEPAY_BINDING_OWNER_A_CREDENTIAL_ENV", "development")
    monkeypatch.setenv("INFINITEPAY_BINDING_OWNER_A_API_KEY", "synthetic-infinitepay-key")
    configured = operational_provider(tenant_id=TENANT_ID,
        redirect_url="https://pick.example.test/api/infinitepay/return")
    assert configured is not None
    assert configured.webhook_url == "https://pick.example.test/api/infinitepay/webhook"
    configured.close()
    assert json.loads(request.content) == {
        "handle": "photo-owner",
        "order_nsu": str(PAYMENT_ID),
        "items": [{"quantity": 2, "price": 500, "description": "Fotografias digitais"}],
        "redirect_url": "https://pick.example.test/checkout/return",
        "webhook": {"url": "https://pick.example.test/api/provider/infinitepay/webhook", "events": ["paid"]},
        "options": {"payment_methods_enabled": list(methods), "single_payment": True},
    }


def test_fluxo_inicial_envia_chave_sem_webhook():
    seen = {}

    def respond(request):
        seen["request"] = request
        return httpx.Response(200, json={"url": "https://checkout.infinitepay.io/photo-owner/abc"})

    client = httpx.Client(transport=httpx.MockTransport(respond))
    provider = InfinitePayHttpProvider(redirect_url="https://pick.example.test/api/infinitepay/return",
                                       api_key="synthetic-infinitepay-key", client=client)
    assert provider.create_checkout(_checkout_request()).outcome == "accepted"
    request = seen["request"]
    payload = json.loads(request.content)
    assert payload["redirect_url"] == "https://pick.example.test/api/infinitepay/return"
    assert "webhook_url" not in payload
    assert request.headers["x-api-key"] == "synthetic-infinitepay-key"
    assert "authorization" not in request.headers


@pytest.mark.parametrize("status,body,category", [
    (502, {"url": "https://checkout.infinitepay.io/photo-owner/abc"}, "http_502"),
    (200, {"url": "http://checkout.infinitepay.io/photo-owner/abc"}, "response_invalid_url"),
    (200, {"url": "https://evil.example/checkout"}, "response_invalid_url"),
    (200, {"unexpected": True}, "response_missing_url"),
])
def test_create_checkout_never_treats_error_or_invalid_url_as_accepted(status, body, category):
    provider = _provider(lambda _request: httpx.Response(status, json=body))
    result = provider.create_checkout(_checkout_request())
    assert result.outcome == "unknown"
    assert result.url is None
    assert result.error_category == category


def test_create_checkout_records_invalid_json_without_response_body():
    provider = _provider(lambda _request: httpx.Response(200, content=b"not-json"))
    result = provider.create_checkout(_checkout_request())
    assert result.outcome == "unknown"
    assert result.url is None
    assert result.error_category == "response_invalid_json"


def test_create_checkout_timeout_is_unknown_transport_and_never_retried():
    calls = []

    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout("late response")

    provider = _provider(timeout)
    with pytest.raises(ProviderTransportError):
        provider.create_checkout(_checkout_request())
    assert len(calls) == 1


def test_payment_check_uses_snapshotted_identity_and_maps_documented_result():
    seen = {}

    def respond(request):
        seen["request"] = request
        return httpx.Response(200, json={
            "success": True, "paid": True, "amount": 1000, "paid_amount": 1010,
            "installments": 1, "capture_method": "credit_card",
        })

    result = _provider(respond).check_payment(_check_request())
    request = seen["request"]
    assert request.url == "https://api.checkout.infinitepay.io/payment_check"
    assert request.headers["x-api-key"] == "synthetic-infinitepay-key"
    assert "authorization" not in request.headers
    assert json.loads(request.content) == {
        "handle": "photo-owner", "order_nsu": str(PAYMENT_ID),
        "transaction_nsu": "provider-transaction-9", "slug": "invoice-9",
    }
    assert result.outcome == "verified"
    assert result.amount_cents == 1000
    assert result.capture_method == "credit_card"


def test_payment_check_preserves_unexpected_pix_for_domain_rejection():
    provider = _provider(lambda _request: httpx.Response(200, json={
        "success": True, "paid": True, "amount": 1000, "capture_method": "pix",
    }))
    result = provider.check_payment(_check_request())
    assert result.outcome == "verified"
    assert result.capture_method == "pix"


@pytest.mark.parametrize("body,expected", [
    ({"success": True, "paid": False}, "unpaid"),
    ({"success": False, "paid": True, "amount": 1000, "capture_method": "credit_card"}, "unknown"),
    ({"success": True, "paid": True, "amount": "1000", "capture_method": "credit_card"}, "unknown"),
    ({"success": True, "paid": True, "amount": 2_147_483_648, "capture_method": "credit_card"}, "unknown"),
    ({"success": True, "paid": True, "amount": 1000}, "unknown"),
    (["malformed"], "unknown"),
])
def test_payment_check_rejects_incomplete_or_malformed_provider_results(body, expected):
    provider = _provider(lambda _request: httpx.Response(200, json=body))
    assert provider.check_payment(_check_request()).outcome == expected


def test_oversized_response_is_unknown():
    provider = _provider(lambda _request: httpx.Response(200, content=b"{" + b" " * 32768 + b"}"))
    result = provider.create_checkout(_checkout_request())
    assert result.outcome == "unknown"
    assert result.error_category == "response_too_large"


@pytest.mark.parametrize("url,allowed", [
    ("https://checkout.infinitepay.io/photo-owner/abc", True),
    ("https://checkout.infinitepay.com.br/photo-owner?lenc=abc", True),
    ("https://sub.checkout.infinitepay.com.br/photo-owner", False),
    ("https://checkout.infinitepay.com.br.evil.test/photo-owner", False),
    ("https://user@checkout.infinitepay.com.br/photo-owner", False),
])
def test_redirect_allowlist_matches_only_documented_or_observed_provider_hosts(url, allowed):
    assert _allowed_checkout_url(url, synthetic=False) is allowed


@pytest.mark.parametrize("value", [
    "http://pick.example.test/callback",
    "https://user:pass@pick.example.test/callback",
    "https://pick.example.test:444/callback",
    "https://pick.example.test/callback#fragment",
])
def test_callbacks_must_be_trusted_https_urls(value):
    with pytest.raises(ValueError):
        InfinitePayHttpProvider(redirect_url=value, api_key="synthetic", webhook_url="https://pick.example.test/hook")
