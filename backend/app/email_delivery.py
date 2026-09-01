"""Transporte de e-mail transacional com outbox e configuração isolada."""

from __future__ import annotations

import os
import smtplib
import ssl
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.message import EmailMessage
from hashlib import sha256
from urllib.parse import quote, urlsplit
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin_security import encrypt_sensitive_payload
from app.auth import EmailDelivery, pii_fingerprint


class EmailConfigurationError(RuntimeError):
    """Configuração incompleta, insegura ou pertencente a outro ambiente."""


class EmailDeliveryError(RuntimeError):
    """Falha sanitizada do provider com semântica de retentativa."""

    def __init__(self, message: str, *, transient: bool, ambiguous: bool = False) -> None:
        super().__init__(message)
        self.transient = transient
        self.ambiguous = ambiguous


@dataclass(frozen=True)
class EmailDeliveryResult:
    external_message_id: str
    provider_status: str = "accepted"


class EmailProvider(ABC):
    @abstractmethod
    def send(
        self,
        *,
        recipient: str,
        subject: str,
        text_body: str,
        idempotency_key: str,
    ) -> EmailDeliveryResult: ...


class SandboxEmailProvider(EmailProvider):
    """Provider determinístico que descarta todo conteúdo sem abrir rede."""

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        text_body: str,
        idempotency_key: str,
    ) -> EmailDeliveryResult:
        del recipient, subject, text_body
        fingerprint = sha256(idempotency_key.encode()).hexdigest()[:24]
        return EmailDeliveryResult(external_message_id=f"sandbox:{fingerprint}")


@dataclass(frozen=True)
class SmtpEmailProvider(EmailProvider):
    host: str
    port: int
    username: str = field(repr=False)
    password: str = field(repr=False)
    from_address: str
    timeout_seconds: float = 10.0
    implicit_tls: bool = False

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        text_body: str,
        idempotency_key: str,
    ) -> EmailDeliveryResult:
        message = EmailMessage()
        message["From"] = self.from_address
        message["To"] = recipient
        message["Subject"] = subject
        message["Message-ID"] = f"<{sha256(idempotency_key.encode()).hexdigest()}@markina.local>"
        message.set_content(text_body)
        context = ssl.create_default_context()
        accepted = False
        try:
            if self.implicit_tls:
                with smtplib.SMTP_SSL(
                    self.host, self.port, timeout=self.timeout_seconds, context=context
                ) as client:
                    client.login(self.username, self.password)
                    client.send_message(message)
                    accepted = True
            else:
                with smtplib.SMTP(self.host, self.port, timeout=self.timeout_seconds) as client:
                    client.ehlo()
                    client.starttls(context=context)
                    client.ehlo()
                    client.login(self.username, self.password)
                    client.send_message(message)
                    accepted = True
        except smtplib.SMTPResponseException as exc:
            transient = 400 <= exc.smtp_code < 500
            raise EmailDeliveryError(
                "Servidor de e-mail temporariamente indisponível."
                if transient
                else "Servidor de e-mail recusou a mensagem.",
                transient=transient,
                ambiguous=accepted,
            ) from None
        except (TimeoutError, OSError, smtplib.SMTPException):
            raise EmailDeliveryError(
                "Resultado do envio de e-mail desconhecido após interrupção.",
                transient=not accepted,
                ambiguous=accepted,
            ) from None
        return EmailDeliveryResult(
            external_message_id=message["Message-ID"].strip("<>"), provider_status="accepted"
        )


def email_provider_name() -> str:
    return os.getenv("EMAIL_PROVIDER", "sandbox").strip().lower()


def email_provider_from_environment() -> EmailProvider:
    provider = email_provider_name()
    if provider == "sandbox":
        return SandboxEmailProvider()
    if provider != "smtp":
        raise EmailConfigurationError("EMAIL_PROVIDER não suportado.")
    app_environment = os.getenv("APP_ENV", "development").strip()
    if os.getenv("EMAIL_CREDENTIAL_ENV", "").strip() != app_environment:
        raise EmailConfigurationError("As credenciais de e-mail não pertencem ao APP_ENV atual.")
    values = {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "username": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_address": os.getenv("SMTP_FROM_ADDRESS", "").strip(),
    }
    if not all(values.values()):
        raise EmailConfigurationError("A configuração SMTP está incompleta para este ambiente.")
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        timeout = float(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))
    except ValueError as exc:
        raise EmailConfigurationError("Porta ou timeout SMTP inválido.") from exc
    if not 1 <= port <= 65535 or not 1 <= timeout <= 30:
        raise EmailConfigurationError("Porta ou timeout SMTP fora do limite permitido.")
    return SmtpEmailProvider(
        **values,
        port=port,
        timeout_seconds=timeout,
        implicit_tls=os.getenv("SMTP_IMPLICIT_TLS", "false").lower() == "true",
    )


def public_app_origin() -> str:
    origin = os.getenv("PUBLIC_APP_ORIGIN", "").strip().rstrip("/")
    parsed = urlsplit(origin)
    development_local = (
        os.getenv("APP_ENV", "development") == "development"
        and parsed.scheme == "http"
        and parsed.hostname in {"localhost", "127.0.0.1"}
    )
    if (
        not origin
        or (parsed.scheme != "https" and not development_local)
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise EmailConfigurationError("PUBLIC_APP_ORIGIN não é uma origem HTTPS permitida.")
    return origin


def sensitive_link(path: str, raw_token: str) -> str:
    if not path.startswith("/") or "?" in path or "#" in path:
        raise EmailConfigurationError("Caminho de link sensível inválido.")
    return f"{public_app_origin()}{path}#token={quote(raw_token, safe='')}"


def enqueue_email(
    db: Session,
    *,
    kind: str,
    source_type: str,
    source_id: str,
    recipient: str,
    subject: str,
    text_body: str,
    idempotency_key: str,
    expires_at,
) -> EmailDelivery:
    existing = db.scalar(
        select(EmailDelivery).where(EmailDelivery.idempotency_key == idempotency_key)
    )
    if existing:
        return existing
    delivery = EmailDelivery(
        id=uuid4(),
        kind=kind,
        source_type=source_type,
        source_id=source_id,
        recipient_fingerprint=pii_fingerprint(recipient.strip().casefold()),
        idempotency_key=idempotency_key,
        expires_at=expires_at,
    )
    delivery.encrypted_payload = encrypt_sensitive_payload(
        {"recipient": recipient, "subject": subject, "text_body": text_body},
        context=f"email-delivery:{delivery.id}:{idempotency_key}",
    )
    db.add(delivery)
    db.flush()
    return delivery


def email_channel_payload() -> dict[str, str | bool | None]:
    provider = email_provider_name()
    try:
        email_provider_from_environment()
        origin = public_app_origin()
        ready = provider == "smtp"
        status = "ready" if ready else "sandbox"
        return {
            "provider": provider,
            "status": status,
            "ready": ready,
            "origin": urlsplit(origin).hostname,
            "last_error": None,
        }
    except EmailConfigurationError:
        return {
            "provider": provider,
            "status": "unavailable",
            "ready": False,
            "origin": None,
            "last_error": "Configuração transacional indisponível.",
        }
