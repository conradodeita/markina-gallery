"""Validação server-side isolada do Cloudflare Turnstile no cadastro público."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
EXPECTED_ACTION = "photographer_signup"
MAX_TOKEN_LENGTH = 2048


class TurnstileConfigurationError(RuntimeError):
    """Configuração ausente ou inválida; a mensagem nunca contém valores secretos."""


class TurnstileUnavailable(RuntimeError):
    """Siteverify indisponível ou com resposta ilegível."""


@dataclass(frozen=True)
class TurnstileSettings:
    site_key: str
    secret_key: str = field(repr=False)
    expected_hostname: str = "pickyourpic.com.br"


def _hostname(value: str) -> str:
    candidate = value.strip().rstrip(".").lower()
    if not candidate or any(char in candidate for char in "/:@*?#"):
        raise TurnstileConfigurationError("Hostname do Turnstile inválido.")
    try:
        normalized = candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise TurnstileConfigurationError("Hostname do Turnstile inválido.") from exc
    if len(normalized) > 253 or not re.fullmatch(
        r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}",
        normalized,
    ):
        raise TurnstileConfigurationError("Hostname do Turnstile inválido.")
    return normalized


def settings_from_environment() -> TurnstileSettings | None:
    """Retorna None quando a integração está fechada; nunca usa modo permissivo."""
    if os.getenv("PHOTOGRAPHER_SIGNUP_TURNSTILE_ENABLED", "false").strip().lower() != "true":
        return None
    site_key = os.getenv("PHOTOGRAPHER_SIGNUP_TURNSTILE_SITE_KEY", "").strip()
    secret_key = os.getenv("PHOTOGRAPHER_SIGNUP_TURNSTILE_SECRET_KEY", "").strip()
    expected_hostname = os.getenv(
        "PHOTOGRAPHER_SIGNUP_TURNSTILE_HOSTNAME", "pickyourpic.com.br"
    )
    if (
        not site_key
        or len(site_key) > 512
        or any(ord(char) < 32 for char in site_key)
        or not secret_key
        or len(secret_key) > 4096
        or any(ord(char) < 32 for char in secret_key)
    ):
        raise TurnstileConfigurationError("Configuração do Turnstile incompleta.")
    return TurnstileSettings(
        site_key=site_key,
        secret_key=secret_key,
        expected_hostname=_hostname(expected_hostname),
    )


class TurnstileVerifier:
    def __init__(
        self,
        settings: TurnstileSettings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    def verify(self, token: str) -> bool:
        if not isinstance(token, str) or not token.strip() or len(token) > MAX_TOKEN_LENGTH:
            return False
        try:
            with httpx.Client(
                timeout=httpx.Timeout(4.0, connect=2.0),
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
            ) as client:
                response = client.post(
                    SITEVERIFY_URL,
                    json={"secret": self._settings.secret_key, "response": token},
                )
                response.raise_for_status()
                payload: Any = response.json()
        except (httpx.HTTPError, ValueError, TypeError):
            raise TurnstileUnavailable("Validação anti-bot temporariamente indisponível.") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("hostname"), str):
            raise TurnstileUnavailable("Resposta anti-bot inválida.")
        try:
            response_hostname = _hostname(payload["hostname"])
        except TurnstileConfigurationError:
            return False
        return (
            payload.get("success") is True
            and response_hostname == self._settings.expected_hostname
            and payload.get("action") == EXPECTED_ACTION
        )
