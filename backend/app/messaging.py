"""Porta WhatsApp e configuração isolada por ambiente.

O módulo nunca registra credenciais, telefone ou corpo da mensagem. O adaptador
sandbox é o padrão explícito; o Evolution só é criado quando todas as
configurações pertencem ao mesmo ambiente da aplicação.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class WhatsAppConfigurationError(RuntimeError):
    """Configuração incompleta ou pertencente a outro ambiente."""


class WhatsAppDeliveryError(RuntimeError):
    """Falha sanitizada do provedor, classificada para retentativa."""

    def __init__(self, message: str, *, transient: bool) -> None:
        super().__init__(message)
        self.transient = transient


class WhatsAppProvider(ABC):
    """Porta mínima para OTP e mensagens transacionais."""

    @abstractmethod
    def send_otp(self, phone_e164: str, code: str) -> None: ...

    @abstractmethod
    def send_transactional(
        self, phone_e164: str, message: str, *, idempotency_key: str
    ) -> None: ...


class SandboxWhatsAppProvider(WhatsAppProvider):
    """Adaptador sintético sem efeitos externos e sem logs de conteúdo."""

    def send_otp(self, phone_e164: str, code: str) -> None:
        del phone_e164, code

    def send_transactional(
        self, phone_e164: str, message: str, *, idempotency_key: str
    ) -> None:
        del phone_e164, message, idempotency_key


@dataclass(frozen=True)
class EvolutionWhatsAppProvider(WhatsAppProvider):
    """Adaptador HTTP para o endpoint controlado do Evolution API."""

    api_url: str
    api_key: str = field(repr=False)
    instance: str
    timeout_seconds: float = 10.0

    def send_otp(self, phone_e164: str, code: str) -> None:
        self.send_transactional(
            phone_e164,
            f"Seu código de acesso Markina Gallery é {code}.",
            idempotency_key=f"otp:{phone_e164}:{code}",
        )

    def send_transactional(
        self, phone_e164: str, message: str, *, idempotency_key: str
    ) -> None:
        endpoint = (
            f"{self.api_url.rstrip('/')}/message/sendText/{quote(self.instance, safe='')}"
        )
        payload = json.dumps(
            {"number": phone_e164.removeprefix("+"), "text": message},
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "apikey": self.api_key,
                "Idempotency-Key": idempotency_key,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status >= 400:
                    raise WhatsAppDeliveryError(
                        "Provedor recusou a entrega.", transient=response.status >= 500
                    )
        except HTTPError as exc:
            raise WhatsAppDeliveryError(
                "Provedor indisponível temporariamente."
                if exc.code in {408, 425, 429} or exc.code >= 500
                else "Provedor recusou a entrega.",
                transient=exc.code in {408, 425, 429} or exc.code >= 500,
            ) from None
        except (TimeoutError, URLError):
            raise WhatsAppDeliveryError(
                "Provedor indisponível temporariamente.", transient=True
            ) from None


def normalize_configured_phone(value: str) -> str:
    compact = re.sub(r"[\s().-]", "", value)
    if not re.fullmatch(r"\+[1-9]\d{7,14}", compact):
        raise WhatsAppConfigurationError(
            "O telefone transacional configurado não está em E.164."
        )
    return compact


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


def whatsapp_provider_from_environment() -> WhatsAppProvider:
    provider = os.getenv("WHATSAPP_PROVIDER", "sandbox").strip().lower()
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
