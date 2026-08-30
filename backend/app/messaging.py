"""Porta WhatsApp e adaptador Evolution isolado por ambiente.

Credenciais, telefones e conteúdo nunca são registrados. O sandbox permanece o
padrão explícito e oferece resultados sintéticos determinísticos para testes.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class WhatsAppConfigurationError(RuntimeError):
    """Configuração incompleta ou pertencente a outro ambiente."""


class WhatsAppDeliveryError(RuntimeError):
    """Falha sanitizada do provedor com semântica operacional explícita."""

    def __init__(
        self, message: str, *, transient: bool, ambiguous: bool = False
    ) -> None:
        super().__init__(message)
        self.transient = transient
        self.ambiguous = ambiguous


@dataclass(frozen=True)
class WhatsAppDeliveryResult:
    external_message_id: str
    recipient_phone_e164: str
    provider_status: str


@dataclass(frozen=True)
class WhatsAppConnectionStatus:
    state: str
    connected_phone_e164: str | None = None


@dataclass(frozen=True)
class WhatsAppPairingResult:
    state: str
    pairing_code: str | None = field(default=None, repr=False)
    qr_base64: str | None = field(default=None, repr=False)


class WhatsAppProvider(ABC):
    """Porta de transporte independente do fornecedor concreto."""

    @abstractmethod
    def send_transactional(
        self, phone_e164: str, message: str, *, idempotency_key: str
    ) -> WhatsAppDeliveryResult: ...

    def send_otp(
        self, phone_e164: str, code: str, *, idempotency_key: str
    ) -> WhatsAppDeliveryResult:
        return self.send_transactional(
            phone_e164,
            f"Seu código de acesso Markina Gallery é {code}.",
            idempotency_key=idempotency_key,
        )

    @abstractmethod
    def connection_status(self) -> WhatsAppConnectionStatus: ...

    @abstractmethod
    def ensure_instance(self) -> WhatsAppConnectionStatus: ...

    @abstractmethod
    def start_pairing(self, phone_e164: str) -> WhatsAppPairingResult: ...

    def reconcile(self, external_message_id: str) -> WhatsAppDeliveryResult | None:
        del external_message_id
        return None


class SandboxWhatsAppProvider(WhatsAppProvider):
    """Adaptador sintético sem efeitos externos ou logs de conteúdo."""

    def send_transactional(
        self, phone_e164: str, message: str, *, idempotency_key: str
    ) -> WhatsAppDeliveryResult:
        del message
        return WhatsAppDeliveryResult(
            external_message_id=f"sandbox:{sha256(idempotency_key.encode()).hexdigest()[:24]}",
            recipient_phone_e164=normalize_configured_phone(phone_e164),
            provider_status="accepted",
        )

    def connection_status(self) -> WhatsAppConnectionStatus:
        return WhatsAppConnectionStatus(state="sandbox")

    def ensure_instance(self) -> WhatsAppConnectionStatus:
        return self.connection_status()

    def start_pairing(self, phone_e164: str) -> WhatsAppPairingResult:
        del phone_e164
        raise WhatsAppConfigurationError("Pareamento indisponível no sandbox.")


def _normalized_remote_jid(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    digits = value.split("@", 1)[0].split(":", 1)[0]
    return f"+{digits}" if digits.isdigit() else None


def _first_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        return value[0] if value and isinstance(value[0], dict) else {}
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True)
class EvolutionWhatsAppProvider(WhatsAppProvider):
    """Adaptador HTTP validado para Evolution API 2.3.7."""

    api_url: str
    api_key: str = field(repr=False)
    instance: str
    timeout_seconds: float = 10.0
    webhook_url: str | None = None
    webhook_secret: str = field(default="", repr=False)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        sending_message: bool = False,
    ) -> dict[str, Any] | list[Any]:
        endpoint = f"{self.api_url.rstrip('/')}/{path.lstrip('/')}"
        if query:
            endpoint = f"{endpoint}?{urlencode(query)}"
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            endpoint,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "apikey": self.api_key},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
                if response.status >= 400:
                    raise WhatsAppDeliveryError(
                        "Provedor recusou a operação.",
                        transient=response.status >= 500,
                    )
        except HTTPError as exc:
            transient = exc.code in {408, 425, 429} or exc.code >= 500
            raise WhatsAppDeliveryError(
                "Provedor indisponível temporariamente."
                if transient
                else "Provedor recusou a operação.",
                transient=transient,
            ) from None
        except (TimeoutError, URLError):
            raise WhatsAppDeliveryError(
                "Resultado do provedor desconhecido após interrupção.",
                transient=not sending_message,
                ambiguous=sending_message,
            ) from None
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise WhatsAppDeliveryError(
                "Resposta inválida do provedor.",
                transient=False,
                ambiguous=sending_message,
            ) from None
        if not isinstance(decoded, (dict, list)):
            raise WhatsAppDeliveryError(
                "Resposta inválida do provedor.",
                transient=False,
                ambiguous=sending_message,
            )
        return decoded

    def send_transactional(
        self, phone_e164: str, message: str, *, idempotency_key: str
    ) -> WhatsAppDeliveryResult:
        recipient = normalize_configured_phone(phone_e164)
        response = self._request_json(
            "POST",
            f"message/sendText/{quote(self.instance, safe='')}",
            payload={
                "number": recipient.removeprefix("+"),
                "text": message,
                "options": {"delay": 0},
            },
            sending_message=True,
        )
        body = _first_mapping(response)
        key = body.get("key") if isinstance(body.get("key"), dict) else {}
        external_id = key.get("id") or body.get("messageId") or body.get("id")
        remote = _normalized_remote_jid(
            key.get("remoteJid") or key.get("remoteJidAlt") or body.get("number")
        )
        if not isinstance(external_id, str) or not external_id.strip() or remote != recipient:
            raise WhatsAppDeliveryError(
                "Resposta incompleta ou destinatário divergente.",
                transient=False,
                ambiguous=True,
            )
        status = str(body.get("status") or "accepted").lower()
        del idempotency_key
        return WhatsAppDeliveryResult(external_id.strip(), recipient, status)

    def connection_status(self) -> WhatsAppConnectionStatus:
        state_response = self._request_json(
            "GET", f"instance/connectionState/{quote(self.instance, safe='')}"
        )
        state_body = _first_mapping(state_response)
        nested = _first_mapping(state_body.get("instance"))
        state = str(nested.get("state") or state_body.get("state") or "unknown").lower()
        connected_phone = None
        if state == "open":
            instances = self._request_json(
                "GET",
                "instance/fetchInstances",
                query={"instanceName": self.instance},
            )
            instance_body = _first_mapping(instances)
            connected_phone = _normalized_remote_jid(
                instance_body.get("ownerJid")
                or instance_body.get("number")
                or _first_mapping(instance_body.get("instance")).get("ownerJid")
            )
        return WhatsAppConnectionStatus(state=state, connected_phone_e164=connected_phone)

    def ensure_instance(self) -> WhatsAppConnectionStatus:
        instances = self._request_json(
            "GET",
            "instance/fetchInstances",
            query={"instanceName": self.instance},
        )
        exists = (isinstance(instances, list) and bool(instances)) or (
            isinstance(instances, dict) and bool(instances)
        )
        if exists:
            status = self.connection_status()
        else:
            response = self._request_json(
                "POST",
                "instance/create",
                payload={
                    "instanceName": self.instance,
                    "integration": "WHATSAPP-BAILEYS",
                    "qrcode": True,
                },
            )
            body = _first_mapping(response)
            nested = _first_mapping(body.get("instance"))
            status = WhatsAppConnectionStatus(
                state=str(
                    nested.get("status") or body.get("state") or "connecting"
                ).lower()
            )
        self._configure_webhook()
        return status

    def _configure_webhook(self) -> None:
        if not self.webhook_url or not self.webhook_secret:
            raise WhatsAppConfigurationError(
                "Webhook interno do WhatsApp não configurado."
            )
        self._request_json(
            "POST",
            f"webhook/set/{quote(self.instance, safe='')}",
            payload={
                "webhook": {
                    "enabled": True,
                    "url": self.webhook_url,
                    "headers": {"X-Markina-Webhook-Secret": self.webhook_secret},
                    "byEvents": False,
                    "base64": False,
                    "events": [
                        "MESSAGES_UPDATE",
                        "SEND_MESSAGE_UPDATE",
                        "CONNECTION_UPDATE",
                    ],
                }
            },
        )

    def start_pairing(self, phone_e164: str) -> WhatsAppPairingResult:
        phone = normalize_configured_phone(phone_e164)
        self.ensure_instance()
        response = self._request_json(
            "GET",
            f"instance/connect/{quote(self.instance, safe='')}",
            query={"number": phone.removeprefix("+")},
        )
        body = _first_mapping(response)
        nested = _first_mapping(body.get("instance"))
        state = str(nested.get("state") or nested.get("status") or body.get("state") or "connecting")
        pairing_code = body.get("pairingCode") or body.get("code")
        qr = body.get("base64") or _first_mapping(body.get("qrcode")).get("base64")
        return WhatsAppPairingResult(
            state=state.lower(),
            pairing_code=pairing_code if isinstance(pairing_code, str) else None,
            qr_base64=qr if isinstance(qr, str) else None,
        )


def normalize_configured_phone(value: str) -> str:
    compact = re.sub(r"[\s().-]", "", value)
    if not re.fullmatch(r"\+[1-9]\d{7,14}", compact):
        raise WhatsAppConfigurationError(
            "O telefone transacional configurado não está em E.164."
        )
    return compact


def mask_phone(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_configured_phone(value)
    return f"{normalized[:3]}••••••{normalized[-4:]}"


def configured_photographer_phone() -> str | None:
    value = os.getenv("WHATSAPP_PHOTOGRAPHER_PHONE_E164", "").strip()
    return normalize_configured_phone(value) if value else None


def payment_notification_max_attempts() -> int:
    raw_value = os.getenv("WHATSAPP_MAX_ATTEMPTS", "3")
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise WhatsAppConfigurationError(
            "WHATSAPP_MAX_ATTEMPTS deve ser um número inteiro."
        ) from exc
    if not 1 <= value <= 10:
        raise WhatsAppConfigurationError(
            "WHATSAPP_MAX_ATTEMPTS deve estar entre 1 e 10."
        )
    return value


def whatsapp_provider_name() -> str:
    return os.getenv("WHATSAPP_PROVIDER", "sandbox").strip().lower()


def whatsapp_provider_from_environment() -> WhatsAppProvider:
    provider = whatsapp_provider_name()
    if provider == "sandbox":
        return SandboxWhatsAppProvider()
    if provider != "evolution":
        raise WhatsAppConfigurationError("WHATSAPP_PROVIDER não suportado.")

    app_environment = os.getenv("APP_ENV", "development").strip()
    credential_environment = os.getenv("WHATSAPP_CREDENTIAL_ENV", "").strip()
    if not credential_environment or credential_environment != app_environment:
        raise WhatsAppConfigurationError(
            "As credenciais WhatsApp não pertencem ao APP_ENV atual."
        )
    values = {
        "api_url": os.getenv("WHATSAPP_API_URL", "").strip(),
        "api_key": os.getenv("WHATSAPP_API_KEY", "").strip(),
        "instance": os.getenv("WHATSAPP_INSTANCE", "").strip(),
        "webhook_url": os.getenv("WHATSAPP_WEBHOOK_URL", "").strip(),
        "webhook_secret": os.getenv("WHATSAPP_WEBHOOK_SECRET", "").strip(),
    }
    if not all(values.values()):
        raise WhatsAppConfigurationError(
            "A configuração Evolution está incompleta para este ambiente."
        )
    try:
        timeout = float(os.getenv("WHATSAPP_TIMEOUT_SECONDS", "10"))
    except ValueError as exc:
        raise WhatsAppConfigurationError(
            "WHATSAPP_TIMEOUT_SECONDS deve ser numérico."
        ) from exc
    if not 1 <= timeout <= 30:
        raise WhatsAppConfigurationError(
            "WHATSAPP_TIMEOUT_SECONDS deve estar entre 1 e 30."
        )
    return EvolutionWhatsAppProvider(**values, timeout_seconds=timeout)
