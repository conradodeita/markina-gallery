"""Porta de pagamentos e cliente HTTP documentado da InfinitePay, ainda inativo."""

import json
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.infinitepay_binding import InfinitePayBindingError, api_key_for_tenant


class CheckoutItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    quantity: int = Field(gt=0, le=100_000, strict=True)
    price: int = Field(gt=0, le=2_147_483_647, strict=True)
    description: Literal["Fotografias digitais"] = "Fotografias digitais"


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    payment_id: UUID
    tenant_id: UUID
    handle: str = Field(min_length=1, max_length=100)
    items: tuple[CheckoutItem, ...] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def bounded_total(self):
        if self.total_cents > 2_147_483_647:
            raise ValueError("Valor excede o limite local em centavos.")
        return self

    @property
    def total_cents(self) -> int:
        return sum(item.quantity * item.price for item in self.items)

    def neutral_payload(self) -> dict:
        # O tenant interno nunca é enviado ao provedor, nem contatos/nomes/fotos.
        return {"handle": self.handle, "order_nsu": str(self.payment_id),
                "items": [item.model_dump() for item in self.items]}


class CheckoutResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    outcome: Literal["accepted", "refused", "unknown"]
    url: str | None = Field(default=None, max_length=8192)
    error_category: str | None = Field(
        default=None,
        max_length=48,
        pattern=r"^(not_created|transport_unknown|invalid_response|http_[1-5][0-9]{2}|response_(invalid_json|too_large|missing_url|invalid_url))$",
    )

    @model_validator(mode="after")
    def coherent_result(self):
        if self.outcome == "accepted" and not self.url:
            raise ValueError("Emissão aceita exige destino de checkout.")
        if self.outcome != "accepted" and self.url is not None:
            raise ValueError("Destino só é exposto após emissão aceita.")
        if self.outcome == "refused" and self.error_category != "not_created":
            raise ValueError("Recusa exige comprovação de que não houve emissão.")
        return self


class ProviderTransportError(RuntimeError):
    """Falha de transporte cujo resultado remoto não pode ser inferido."""


class PaymentCheckRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    payment_id: UUID
    tenant_id: UUID
    handle: str = Field(min_length=1, max_length=100)
    transaction_nsu: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=512)
    expected_total_cents: int = Field(gt=0, le=2_147_483_647, strict=True)


class PaymentCheckResult(BaseModel):
    """Resultado do domínio; não é parser da resposta JSON da InfinitePay."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    outcome: Literal["verified", "unpaid", "unknown", "mismatch"]
    payment_id: UUID
    tenant_id: UUID
    handle: str
    slug: str = Field(min_length=1, max_length=512)
    transaction_nsu: str = Field(min_length=1, max_length=200)
    amount_cents: int = Field(ge=0, le=2_147_483_647, strict=True)
    capture_method: Literal["credit_card", "pix", "unknown"]
    verification_profile: str = Field(min_length=1, max_length=100)


@dataclass(frozen=True)
class ProviderCapabilities:
    profile: str
    operational: bool = False
    credit_only: bool = False
    payment_binding_verified: bool = False
    signed_webhook: bool = False
    recovery_verified: bool = False


class PaymentProvider(Protocol):
    capabilities: ProviderCapabilities

    def create_checkout(self, request: CheckoutRequest) -> CheckoutResult: ...

    def check_payment(self, request: PaymentCheckRequest) -> PaymentCheckResult: ...


class SyntheticPaymentProvider:
    """Somente ensaios locais por injeção explícita; nenhuma rota o seleciona."""

    capabilities = ProviderCapabilities(profile="synthetic-only")

    def __init__(self, outcome: Literal["accepted", "refused", "unknown"] = "accepted",
                 check_outcome: Literal["verified", "unpaid", "unknown", "mismatch"] = "unpaid",
                 transport_error: bool = False):
        self.outcome = outcome
        self.check_outcome = check_outcome
        self.create_calls: list[CheckoutRequest] = []
        self.check_calls: list[PaymentCheckRequest] = []
        self.transport_error = transport_error

    def create_checkout(self, request: CheckoutRequest) -> CheckoutResult:
        self.create_calls.append(request)
        if self.transport_error:
            raise ProviderTransportError("synthetic transport timeout")
        if self.outcome == "accepted":
            return CheckoutResult(outcome="accepted", url=f"https://checkout.example.invalid/{request.payment_id}")
        return CheckoutResult(outcome=self.outcome,
                              error_category="not_created" if self.outcome == "refused" else "transport_unknown")

    def check_payment(self, request: PaymentCheckRequest) -> PaymentCheckResult:
        self.check_calls.append(request)
        return PaymentCheckResult(outcome=self.check_outcome, payment_id=request.payment_id,
            tenant_id=request.tenant_id, handle=request.handle, slug=request.slug,
            transaction_nsu=request.transaction_nsu, amount_cents=request.expected_total_cents,
            capture_method="credit_card", verification_profile="synthetic-only")


class InfinitePayHttpProvider:
    """Cliente server-side autenticado: criar link e verificar no retorno.

    Parâmetros do redirect são candidatos. A confirmação sempre depende do
    `payment_check` servidor-a-servidor e da aplicação financeira local.
    """

    API_BASE = "https://api.checkout.infinitepay.io"
    PROFILE = "infinitepay-public-v1"
    MAX_RESPONSE_BYTES = 32 * 1024

    # Este perfil usa payment_check depois do retorno e não depende de webhook.
    # A chave identifica a conta e habilita options.credit_card/single_payment.
    # Timeouts permanecem em verificação e nunca geram nova emissão automática.
    capabilities = ProviderCapabilities(
        profile=PROFILE, operational=True, credit_only=True,
        payment_binding_verified=True, signed_webhook=False, recovery_verified=False,
    )

    def __init__(self, *, redirect_url: str, api_key: str, webhook_url: str | None = None,
                 client: httpx.Client | None = None, timeout_seconds: float = 10.0):
        api_key = api_key.strip() if isinstance(api_key, str) else ""
        if not api_key or len(api_key) > 512:
            raise ValueError("Binding autenticado InfinitePay indisponível.")
        self._api_key = api_key
        self.redirect_url = _trusted_callback_url(redirect_url)
        if urlsplit(self.redirect_url).query:
            raise ValueError("A URL base de retorno não pode conter parâmetros.")
        self.webhook_url = _trusted_callback_url(webhook_url) if webhook_url else None
        if not 0.1 <= timeout_seconds <= 30:
            raise ValueError("Timeout fora dos limites do cliente InfinitePay.")
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    def create_checkout(self, request: CheckoutRequest) -> CheckoutResult:
        payload = request.neutral_payload()
        payload["redirect_url"] = self.redirect_url
        payload["options"] = {
            "payment_methods_enabled": ["credit_card"],
            "single_payment": True,
        }
        if self.webhook_url:
            payload["webhook_url"] = self.webhook_url
        try:
            response = self._post_json(f"{self.API_BASE}/links", payload)
        except (httpx.HTTPError, ProviderTransportError):
            raise ProviderTransportError("InfinitePay checkout transport is uncertain") from None
        if response is None:
            return CheckoutResult(outcome="unknown", error_category="response_too_large")
        status, data = response
        if not 200 <= status < 300:
            # A resposta HTTP não documenta que a cobrança não foi criada.
            return CheckoutResult(outcome="unknown", error_category=f"http_{status}")
        if data is None:
            return CheckoutResult(outcome="unknown", error_category="response_invalid_json")
        if not isinstance(data, dict):
            return CheckoutResult(outcome="unknown", error_category="invalid_response")
        url = data.get("url")
        if not isinstance(url, str) or not url.strip():
            return CheckoutResult(outcome="unknown", error_category="response_missing_url")
        if not _valid_infinitepay_checkout_url(url):
            return CheckoutResult(outcome="unknown", error_category="response_invalid_url")
        return CheckoutResult(outcome="accepted", url=url)

    def check_payment(self, request: PaymentCheckRequest) -> PaymentCheckResult:
        payload = {
            "handle": request.handle,
            "order_nsu": str(request.payment_id),
            "transaction_nsu": request.transaction_nsu,
            "slug": request.slug,
        }
        try:
            response = self._post_json(f"{self.API_BASE}/payment_check", payload)
        except (httpx.HTTPError, ProviderTransportError):
            raise ProviderTransportError("InfinitePay payment check transport is uncertain") from None

        base = {
            "payment_id": request.payment_id,
            "tenant_id": request.tenant_id,
            "handle": request.handle,
            "slug": request.slug,
            "transaction_nsu": request.transaction_nsu,
            "verification_profile": self.PROFILE,
        }
        if response is None or not 200 <= response[0] < 300:
            return PaymentCheckResult(outcome="unknown", amount_cents=0,
                                      capture_method="unknown", **base)
        data = response[1]
        if not isinstance(data, dict):
            return PaymentCheckResult(outcome="unknown", amount_cents=0,
                                      capture_method="unknown", **base)

        success = data.get("success")
        paid = data.get("paid")
        if success is True and paid is False:
            return PaymentCheckResult(outcome="unpaid", amount_cents=0,
                                      capture_method="unknown", **base)
        amount = data.get("amount")
        method = data.get("capture_method")
        if (success is not True or paid is not True or type(amount) is not int
                or amount < 0 or amount > 2_147_483_647
                or method not in ("credit_card", "pix")):
            return PaymentCheckResult(outcome="unknown", amount_cents=0,
                                      capture_method="unknown", **base)
        # `paid_amount` pode incluir encargos. O domínio compara `amount` ao
        # snapshot e exige `credit_card` antes de qualquer confirmação.
        return PaymentCheckResult(outcome="verified", amount_cents=amount,
                                  capture_method=method, **base)

    def _post_json(self, url: str, payload: dict) -> tuple[int, dict | list | None] | None:
        with self._client.stream(
            "POST", url, json=payload,
            headers={"X-Api-Key": self._api_key},
        ) as response:
            body = bytearray()
            for chunk in response.iter_bytes():
                if len(body) + len(chunk) > self.MAX_RESPONSE_BYTES:
                    return None
                body.extend(chunk)
            try:
                decoded = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                decoded = None
            return response.status_code, decoded

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _trusted_callback_url(value: str) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Callback InfinitePay inválido.")
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.port not in (None, 443)
                or parsed.fragment):
            raise ValueError
    except ValueError:
        raise ValueError("Callback InfinitePay deve ser uma URL HTTPS confiável.") from None
    return value


def _valid_infinitepay_checkout_url(value: str) -> bool:
    if len(value) > 8192:
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https"
                and parsed.hostname in {"checkout.infinitepay.io", "checkout.infinitepay.com.br"}
                and parsed.username is None and parsed.password is None
                and parsed.port in (None, 443))
    except ValueError:
        return False


def operational_provider(*, tenant_id: UUID | None = None,
                         redirect_url: str | None = None) -> PaymentProvider | None:
    """Crie cliente autenticado com binding do tenant e retorno HTTPS do servidor."""
    if not redirect_url or tenant_id is None:
        return None
    try:
        api_key = api_key_for_tenant(tenant_id)
    except InfinitePayBindingError:
        return None
    if api_key is None:
        return None
    return InfinitePayHttpProvider(redirect_url=redirect_url, api_key=api_key)
