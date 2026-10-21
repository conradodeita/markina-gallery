import json
from uuid import UUID

import pytest

from app.infinitepay_binding import InfinitePayBindingError, api_key_configured, api_key_for_tenant

TENANT_A = UUID("78f37e04-9389-42a3-8bdf-ecaa95e47a5a")
TENANT_B = UUID("22b48bc1-ea3c-4828-a789-c4eb6471b9c3")


def binding_env(tenant=TENANT_A, alias="PHOTO_A", secret="synthetic-key"):
    prefix = f"INFINITEPAY_BINDING_{alias}_"
    return {
        "APP_ENV": "production",
        "INFINITEPAY_TENANT_BINDINGS": json.dumps({str(tenant): alias}),
        prefix + "CREDENTIAL_ENV": "production",
        prefix + "API_KEY": secret,
    }


def test_key_is_resolved_only_for_the_explicit_tenant():
    values = binding_env()
    assert api_key_for_tenant(TENANT_A, environ=values) == "synthetic-key"
    assert api_key_for_tenant(TENANT_B, environ=values) is None


def test_incomplete_or_wrong_environment_binding_fails_closed():
    values = binding_env()
    values["INFINITEPAY_BINDING_PHOTO_A_CREDENTIAL_ENV"] = "homolog"
    with pytest.raises(InfinitePayBindingError):
        api_key_for_tenant(TENANT_A, environ=values)


def test_api_key_configured_reports_only_safe_boolean(monkeypatch):
    values = binding_env()
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    assert api_key_configured(TENANT_A)
    monkeypatch.delenv("INFINITEPAY_BINDING_PHOTO_A_API_KEY")
    assert not api_key_configured(TENANT_A)


@pytest.mark.parametrize("value", [
    "not-json",
    "[]",
    ('{"78f37e04-9389-42a3-8bdf-ecaa95e47a5a":"DUP",'
     '"22b48bc1-ea3c-4828-a789-c4eb6471b9c3":"DUP"}'),
    ('{"78f37e04-9389-42a3-8bdf-ecaa95e47a5a":"PHOTO_A",'
     '"78f37e04-9389-42a3-8bdf-ecaa95e47a5a":"PHOTO_B"}'),
])
def test_binding_invalido_recusa_sem_fallback(value):
    values = binding_env()
    values["INFINITEPAY_TENANT_BINDINGS"] = value
    with pytest.raises(InfinitePayBindingError):
        api_key_for_tenant(TENANT_A, environ=values)


@pytest.mark.parametrize("secret", ["", "synthetic\nkey"])
def test_binding_sem_segredo_valido_nao_habilita_conta(secret):
    values = binding_env(secret=secret)
    with pytest.raises(InfinitePayBindingError):
        api_key_for_tenant(TENANT_A, environ=values)
