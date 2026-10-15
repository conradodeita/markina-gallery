import pytest

from app.auth import Tenant
from app.tenant_hosts import (
    CanonicalHostError,
    canonical_host_for_tenant,
    normalize_canonical_host,
    purchase_url_for_tenant,
    request_hostname,
    tenant_for_host,
)
from tests.test_tenant_foundation import tenant_db as foundation_tenant_db

tenant_db = foundation_tenant_db


@pytest.mark.parametrize(("value", "expected"), [
    ("A.Fotografo.Example.com", "a.fotografo.example.com"),
    ("fótografo.example.com", "xn--ftografo-v3a.example.com"),
    ("a.fotografo.example.com.", "a.fotografo.example.com"),
])
def test_normaliza_hostname_dns_canonico(value, expected):
    assert normalize_canonical_host(value) == expected


@pytest.mark.parametrize("value", [
    "https://a.fotografo.example.com", "a.fotografo.example.com:8443",
    "a.fotografo.example.com/path", "a.fotografo.example.com@attacker.invalid",
    "127.0.0.1", "localhost", "*.example.com", "a.fotografo.example.com%2fattacker",
])
def test_recusa_origens_nao_canonicas(value):
    with pytest.raises(CanonicalHostError):
        normalize_canonical_host(value)


def test_host_da_requisicao_ignora_cabecalho_encaminhado_e_limita_porta():
    assert request_hostname("a.fotografo.example.com:443") == "a.fotografo.example.com"
    with pytest.raises(CanonicalHostError):
        request_hostname("a.fotografo.example.com:444")


def test_origem_publica_suplanta_host_apenas_para_tenant_unico(tenant_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://markina.example.com")
    tenant = Tenant(status="active")
    tenant_db.add(tenant)
    tenant_db.commit()

    assert tenant_for_host(tenant_db, "markina.example.com") == tenant
    assert canonical_host_for_tenant(tenant_db, tenant) == "markina.example.com"
    assert purchase_url_for_tenant(tenant_db, tenant, tenant.id) == (
        f"https://markina.example.com/library/purchases#order-{tenant.id}"
    )
    assert tenant_for_host(tenant_db, "attacker.example.com") is None


def test_varios_tenants_exigem_host_explicito_e_nao_usam_origem_publica(tenant_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://markina.example.com")
    unconfigured = Tenant(status="active")
    configured = Tenant(status="active", canonical_host="b.example.com")
    tenant_db.add_all([unconfigured, configured])
    tenant_db.commit()

    assert tenant_for_host(tenant_db, "markina.example.com") is None
    assert tenant_for_host(tenant_db, "b.example.com") == configured
    with pytest.raises(CanonicalHostError):
        canonical_host_for_tenant(tenant_db, unconfigured)


def test_host_de_tenant_inativo_nao_cai_no_fallback_de_outro_tenant(tenant_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "https://markina.example.com")
    inactive = Tenant(status="suspended", canonical_host="markina.example.com")
    active = Tenant(status="active")
    tenant_db.add_all([inactive, active])
    tenant_db.commit()

    assert tenant_for_host(tenant_db, "markina.example.com") is None


def test_origem_nao_usa_host_recebido_quando_configuracao_ausente(tenant_db, monkeypatch):
    monkeypatch.delenv("PUBLIC_APP_ORIGIN", raising=False)
    monkeypatch.delenv("MARKINA_PUBLIC_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")
    tenant = Tenant(status="active")
    tenant_db.add(tenant)
    tenant_db.commit()

    assert tenant_for_host(tenant_db, "attacker.example.com") is None
    assert canonical_host_for_tenant(tenant_db, tenant) is None
    with pytest.raises(CanonicalHostError):
        purchase_url_for_tenant(tenant_db, tenant, tenant.id)
