from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.payment_provider import (
    CheckoutItem,
    CheckoutRequest,
    CheckoutResult,
    PaymentCheckRequest,
    SyntheticPaymentProvider,
    operational_provider,
)


def request():
    return CheckoutRequest(payment_id=uuid4(), tenant_id=uuid4(), handle="synthetic",
                           items=(CheckoutItem(quantity=2, price=700), CheckoutItem(quantity=1, price=900)))


def test_payload_neutro_com_uuid_e_centavos_sem_contexto_privado():
    value = request()
    assert value.total_cents == 2300
    assert value.neutral_payload() == {"handle": "synthetic", "order_nsu": str(value.payment_id),
        "items": [{"quantity":2,"price":700,"description":"Fotografias digitais"},
                  {"quantity":1,"price":900,"description":"Fotografias digitais"}]}
    assert operational_provider() is None


@pytest.mark.parametrize("value", [0, -1, True, 10.5, "1000", 2_147_483_648])
def test_preco_exige_centavos_inteiros_positivos_e_limitados(value):
    with pytest.raises(ValidationError):
        CheckoutItem(quantity=1, price=value)


def test_campos_e_descricao_privados_recusados_e_total_limitado():
    with pytest.raises(ValidationError):
        CheckoutItem(quantity=1, price=100, description="nome de pessoa.jpg")
    with pytest.raises(ValidationError):
        CheckoutRequest(**(request().model_dump() | {"customer": {"name": "privado"}}))
    with pytest.raises(ValidationError):
        CheckoutRequest(payment_id=uuid4(), tenant_id=uuid4(), handle="synthetic",
                        items=(CheckoutItem(quantity=2, price=2_147_483_647),))


@pytest.mark.parametrize("outcome", ["accepted", "refused", "unknown"])
def test_adaptador_sintetico_sem_rede_ou_capacidade_operacional(outcome, monkeypatch):
    import socket

    monkeypatch.setattr(socket, "create_connection", lambda *_a, **_kw: pytest.fail("Rede proibida no adaptador sintético"))
    provider = SyntheticPaymentProvider(outcome)
    result = provider.create_checkout(request())
    assert result.outcome == outcome
    assert len(provider.create_calls) == 1
    assert provider.capabilities.operational is False
    assert provider.capabilities.signed_webhook is False
    assert provider.capabilities.recovery_verified is False


@pytest.mark.parametrize("outcome", ["verified", "unpaid", "unknown", "mismatch"])
def test_consulta_sintetica_distingue_evidencia_de_sinal(outcome):
    provider = SyntheticPaymentProvider(check_outcome=outcome)
    candidate = PaymentCheckRequest(payment_id=uuid4(), tenant_id=uuid4(), handle="synthetic",
        transaction_nsu="synthetic-tx", slug="synthetic-slug", expected_total_cents=1000)
    result = provider.check_payment(candidate)
    assert result.outcome == outcome and result.payment_id == candidate.payment_id
    assert result.tenant_id == candidate.tenant_id and result.amount_cents == 1000


def test_contrato_nao_trata_timeout_como_recusa():
    with pytest.raises(ValidationError):
        CheckoutResult(outcome="refused", error_category="transport_unknown")
    with pytest.raises(ValidationError):
        CheckoutResult(outcome="accepted")
