import pytest

from app.messaging import (
    EvolutionWhatsAppProvider,
    SandboxWhatsAppProvider,
    WhatsAppConfigurationError,
    configured_photographer_phone,
    payment_notification_max_attempts,
    whatsapp_provider_from_environment,
)


def test_whatsapp_defaults_to_sandbox_without_external_effects(monkeypatch) -> None:
    monkeypatch.delenv("WHATSAPP_PROVIDER", raising=False)
    provider = whatsapp_provider_from_environment()
    assert isinstance(provider, SandboxWhatsAppProvider)
    provider.send_transactional(
        "+5511999999999", "Mensagem sintética", idempotency_key="sandbox-0001"
    )


def test_evolution_requires_credentials_from_current_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "evolution")
    monkeypatch.setenv("WHATSAPP_CREDENTIAL_ENV", "production")
    monkeypatch.setenv("WHATSAPP_API_URL", "https://evolution.invalid")
    monkeypatch.setenv("WHATSAPP_API_KEY", "segredo-nao-exibido")
    monkeypatch.setenv("WHATSAPP_INSTANCE", "markina-homolog")
    with pytest.raises(WhatsAppConfigurationError, match="APP_ENV"):
        whatsapp_provider_from_environment()

    monkeypatch.setenv("WHATSAPP_CREDENTIAL_ENV", "homolog")
    provider = whatsapp_provider_from_environment()
    assert isinstance(provider, EvolutionWhatsAppProvider)
    assert "segredo-nao-exibido" not in repr(provider)


def test_transactional_limits_and_phone_are_validated(monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("WHATSAPP_PHOTOGRAPHER_PHONE_E164", "+55 11 99999-9999")
    assert payment_notification_max_attempts() == 4
    assert configured_photographer_phone() == "+5511999999999"

    monkeypatch.setenv("WHATSAPP_MAX_ATTEMPTS", "0")
    with pytest.raises(WhatsAppConfigurationError):
        payment_notification_max_attempts()
    monkeypatch.setenv("WHATSAPP_PHOTOGRAPHER_PHONE_E164", "11999999999")
    with pytest.raises(WhatsAppConfigurationError):
        configured_photographer_phone()
