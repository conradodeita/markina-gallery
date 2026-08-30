import io
import json
from urllib.error import HTTPError, URLError

import pytest

from app import messaging
from app.messaging import (
    EvolutionWhatsAppProvider,
    SandboxWhatsAppProvider,
    WhatsAppConfigurationError,
    WhatsAppDeliveryError,
    configured_photographer_phone,
    payment_notification_max_attempts,
    whatsapp_provider_from_environment,
)


def test_whatsapp_defaults_to_sandbox_without_external_effects(monkeypatch) -> None:
    monkeypatch.delenv("WHATSAPP_PROVIDER", raising=False)
    provider = whatsapp_provider_from_environment()
    assert isinstance(provider, SandboxWhatsAppProvider)
    result = provider.send_transactional(
        "+5511999999999", "Mensagem sintética", idempotency_key="sandbox-0001"
    )
    assert result.recipient_phone_e164 == "+5511999999999"
    assert result.provider_status == "accepted"
    assert result.external_message_id.startswith("sandbox:")
    assert provider.connection_status().state == "sandbox"


def test_evolution_requires_credentials_from_current_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "evolution")
    monkeypatch.setenv("WHATSAPP_CREDENTIAL_ENV", "production")
    monkeypatch.setenv("WHATSAPP_API_URL", "https://evolution.invalid")
    monkeypatch.setenv("WHATSAPP_API_KEY", "segredo-nao-exibido")
    monkeypatch.setenv("WHATSAPP_INSTANCE", "markina-homolog")
    monkeypatch.setenv("WHATSAPP_WEBHOOK_URL", "http://api:8000/internal/whatsapp/webhook")
    monkeypatch.setenv("WHATSAPP_WEBHOOK_SECRET", "segredo-webhook-nao-exibido")
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


class FakeResponse(io.BytesIO):
    def __init__(self, payload, status: int = 200) -> None:
        super().__init__(json.dumps(payload).encode("utf-8"))
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def evolution_provider() -> EvolutionWhatsAppProvider:
    return EvolutionWhatsAppProvider(
        api_url="http://evolution.internal:8080",
        api_key="segredo-falso",
        instance="markina-homolog",
        webhook_url="http://api:8000/internal/whatsapp/webhook",
        webhook_secret="segredo-webhook-falso",
    )


def test_evolution_validates_send_response_and_recipient(monkeypatch) -> None:
    monkeypatch.setattr(
        messaging,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(
            {
                "key": {
                    "id": "MESSAGE-123",
                    "remoteJid": "5511999999999@s.whatsapp.net",
                },
                "status": "PENDING",
            }
        ),
    )
    result = evolution_provider().send_transactional(
        "+5511999999999", "Mensagem sintética", idempotency_key="send-1"
    )
    assert result.external_message_id == "MESSAGE-123"
    assert result.recipient_phone_e164 == "+5511999999999"
    assert result.provider_status == "pending"


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "PENDING"},
        {
            "key": {
                "id": "MESSAGE-124",
                "remoteJid": "5511888888888@s.whatsapp.net",
            }
        },
    ],
)
def test_evolution_treats_incomplete_success_as_ambiguous(monkeypatch, payload) -> None:
    monkeypatch.setattr(
        messaging, "urlopen", lambda *_args, **_kwargs: FakeResponse(payload)
    )
    with pytest.raises(WhatsAppDeliveryError) as error:
        evolution_provider().send_transactional(
            "+5511999999999", "Mensagem", idempotency_key="send-2"
        )
    assert error.value.ambiguous is True
    assert error.value.transient is False


@pytest.mark.parametrize(
    ("failure", "transient", "ambiguous"),
    [
        (HTTPError("url", 400, "bad", {}, None), False, False),
        (HTTPError("url", 429, "rate", {}, None), True, False),
        (HTTPError("url", 503, "down", {}, None), True, False),
        (URLError("timeout"), False, True),
        (TimeoutError(), False, True),
    ],
)
def test_evolution_classifies_provider_failures(
    monkeypatch, failure, transient, ambiguous
) -> None:
    def fail(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(messaging, "urlopen", fail)
    with pytest.raises(WhatsAppDeliveryError) as error:
        evolution_provider().send_transactional(
            "+5511999999999", "Mensagem", idempotency_key="send-3"
        )
    assert error.value.transient is transient
    assert error.value.ambiguous is ambiguous


def test_evolution_reads_connection_identity_and_pairing_without_exposing_key(
    monkeypatch,
) -> None:
    responses = iter(
        [
            FakeResponse({"instance": {"state": "open"}}),
            FakeResponse([{"ownerJid": "5511999999999@s.whatsapp.net"}]),
            FakeResponse([{"ownerJid": "5511999999999@s.whatsapp.net"}]),
            FakeResponse({"instance": {"state": "open"}}),
            FakeResponse([{"ownerJid": "5511999999999@s.whatsapp.net"}]),
            FakeResponse({"webhook": {"enabled": True}}),
            FakeResponse({"pairingCode": "1234-5678", "state": "connecting"}),
        ]
    )
    monkeypatch.setattr(
        messaging, "urlopen", lambda *_args, **_kwargs: next(responses)
    )
    provider = evolution_provider()
    status = provider.connection_status()
    assert status.state == "open"
    assert status.connected_phone_e164 == "+5511999999999"
    pairing = provider.start_pairing("+5511999999999")
    assert pairing.state == "connecting"
    assert pairing.pairing_code == "1234-5678"
    assert "1234-5678" not in repr(pairing)
    assert "segredo-falso" not in repr(provider)


def test_evolution_creates_missing_baileys_instance_before_pairing(monkeypatch) -> None:
    requests = []
    responses = iter(
        [
            FakeResponse([]),
            FakeResponse({"instance": {"status": "connecting"}}),
            FakeResponse({"webhook": {"enabled": True}}),
            FakeResponse({"base64": "data:image/png;base64,synthetic", "state": "connecting"}),
        ]
    )

    def respond(request, **_kwargs):
        requests.append(request)
        return next(responses)

    monkeypatch.setattr(messaging, "urlopen", respond)
    pairing = evolution_provider().start_pairing("+5511999999999")
    assert pairing.qr_base64 == "data:image/png;base64,synthetic"
    create_payload = json.loads(requests[1].data)
    assert create_payload == {
        "instanceName": "markina-homolog",
        "integration": "WHATSAPP-BAILEYS",
        "qrcode": True,
    }
    webhook_payload = json.loads(requests[2].data)
    assert webhook_payload == {
        "webhook": {
            "enabled": True,
            "url": "http://api:8000/internal/whatsapp/webhook",
            "headers": {"X-Markina-Webhook-Secret": "segredo-webhook-falso"},
            "byEvents": False,
            "base64": False,
            "events": ["MESSAGES_UPDATE", "SEND_MESSAGE_UPDATE", "CONNECTION_UPDATE"],
        }
    }
