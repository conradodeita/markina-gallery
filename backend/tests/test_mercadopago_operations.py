"""Gates operacionais de teste e contrato estático do cofre, sem acesso remoto."""

import json
import re
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.mercadopago_settings import can_create
from app.mercadopago_settings import test_customer_allowed as customer_allowed


@pytest.mark.parametrize("environment", ["production", "staging", "homolog", "invalid"])
def test_conta_teste_fechada_sem_permissao_operacional(monkeypatch, environment):
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.delenv("MERCADOPAGO_TEST_CUSTOMERS", raising=False)
    account = SimpleNamespace(test_account=True, tenant_id=uuid4())
    assert not customer_allowed(account, uuid4())
    assert not customer_allowed(account, None)


@pytest.mark.parametrize("raw", ["invalid", "{}", "[]", "null", '[{"tenant_id": "x"}]',
                               '[{"tenant_id": null, "client_id": 4}]', '"' + "x" * 16385 + '"'])
def test_politica_invalida_nao_libera_teste(monkeypatch, raw):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("MERCADOPAGO_TEST_CUSTOMERS", raw)
    assert not customer_allowed(SimpleNamespace(test_account=True, tenant_id=uuid4()), uuid4())


def test_permissao_exige_o_par_tenant_cliente_e_nao_libera_conta_real(monkeypatch):
    account = SimpleNamespace(test_account=True, tenant_id=uuid4(), status="active")
    client_id = uuid4()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MERCADOPAGO_TEST_CUSTOMERS", json.dumps([
        {"tenant_id": str(account.tenant_id), "client_id": str(client_id)}]))
    assert customer_allowed(account, client_id)
    assert not customer_allowed(account, uuid4())
    assert not customer_allowed(account, None)
    assert not customer_allowed(SimpleNamespace(test_account=True, tenant_id=uuid4()), client_id)
    monkeypatch.setenv("MERCADOPAGO_ALLOW_LIVE_PAYMENTS", "false")
    assert not can_create(SimpleNamespace(test_account=False, status="active"))


def test_compose_cofre_somente_api_worker_e_emissao_fechada():
    source = (Path(__file__).parents[2] / "docker/docker-compose.yml").read_text()
    services = dict(re.findall(r"^  ([a-z][a-z0-9-]*):\n(.*?)(?=^  [a-z][a-z0-9-]*:\n|\Z)",
                               source, flags=re.MULTILINE | re.DOTALL))
    recipients = {name for name, body in services.items() if "INTEGRATION_SECRETS_ENV_FILE" in body}
    assert recipients == {"api", "worker"}
    for name in recipients:
        assert ("- path: ${INTEGRATION_SECRETS_ENV_FILE:-.env.integration-secrets}\n"
                "        required: false\n        format: raw") in services[name]
    assert "MERCADOPAGO_ALLOW_LIVE_PAYMENTS: ${MERCADOPAGO_ALLOW_LIVE_PAYMENTS:-false}" in services["api"]
    assert "MERCADOPAGO_TEST_CUSTOMERS: ${MERCADOPAGO_TEST_CUSTOMERS:-}" in services["api"]
