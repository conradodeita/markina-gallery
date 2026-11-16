"""Provisionamento isolado do canal Evolution por tenant e ambiente."""

from __future__ import annotations

import os
import secrets
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import WhatsAppChannelSettings, WhatsAppTenantCredential
from app.integration_secrets import (
    IntegrationCipher,
    IntegrationSecretError,
    SecretEnvelope,
)
from app.messaging import (
    EvolutionWhatsAppProvider,
    WhatsAppConfigurationError,
    normalize_configured_phone,
)
from app.whatsapp_channel import app_environment, configure_expected_phone


def _cipher() -> IntegrationCipher:
    try:
        cipher = IntegrationCipher()
        return cipher.for_environment(app_environment())
    except IntegrationSecretError:
        raise WhatsAppConfigurationError(
            "Cofre de credenciais do WhatsApp indisponível."
        ) from None


def _configured_transport() -> tuple[str, str, str, float]:
    environment = app_environment()
    if (os.getenv("WHATSAPP_PROVIDER", "sandbox").strip().lower() != "evolution"
            or os.getenv("WHATSAPP_CREDENTIAL_ENV", "").strip() != environment):
        raise WhatsAppConfigurationError(
            "Provedor Evolution não configurado para este ambiente."
        )
    api_url = os.getenv("WHATSAPP_API_URL", "").strip().rstrip("/")
    api_key = os.getenv("WHATSAPP_API_KEY", "").strip()
    webhook_url = os.getenv("WHATSAPP_WEBHOOK_URL", "").strip()
    try:
        timeout = float(os.getenv("WHATSAPP_TIMEOUT_SECONDS", "10"))
    except ValueError:
        raise WhatsAppConfigurationError("Configuração do WhatsApp indisponível.") from None
    if (not api_url.startswith(("http://", "https://")) or not api_key
            or not webhook_url.startswith(("http://", "https://"))
            or not 1 <= timeout <= 30):
        raise WhatsAppConfigurationError("Configuração do WhatsApp indisponível.")
    return api_url, api_key, webhook_url, timeout


def credential_for_tenant(db: Session, *, tenant_id: UUID) -> WhatsAppTenantCredential | None:
    return db.scalar(select(WhatsAppTenantCredential).where(
        WhatsAppTenantCredential.tenant_id == tenant_id,
        WhatsAppTenantCredential.environment == app_environment(),
    ))


def provider_for_credential(
    db: Session, *, credential: WhatsAppTenantCredential
) -> EvolutionWhatsAppProvider:
    if credential.environment != app_environment():
        raise WhatsAppConfigurationError("Credencial WhatsApp de outro ambiente.")
    api_url, api_key, webhook_url, timeout = _configured_transport()
    try:
        envelope = SecretEnvelope.from_payload(credential.webhook_secret_envelope)
        webhook_secret = _cipher().decrypt(
            envelope, tenant_id=credential.tenant_id, credential_id=credential.id
        )
    except IntegrationSecretError:
        raise WhatsAppConfigurationError("Credencial WhatsApp indisponível.") from None
    return EvolutionWhatsAppProvider(
        api_url=api_url,
        api_key=api_key,
        instance=credential.instance_name,
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
        timeout_seconds=timeout,
    )


def provision_tenant_credential(
    db: Session, *, tenant_id: UUID, expected_phone_e164: str
) -> tuple[WhatsAppTenantCredential, WhatsAppChannelSettings, EvolutionWhatsAppProvider]:
    """Cria uma identidade estável antes do efeito externo; repetir é seguro."""
    _configured_transport()
    cipher = _cipher()
    environment = app_environment()
    credential = credential_for_tenant(db, tenant_id=tenant_id)
    if credential is None:
        credential_id = uuid4()
        instance = f"pyp-{tenant_id.hex}"
        webhook_secret = secrets.token_urlsafe(32)
        envelope = cipher.encrypt(
            webhook_secret, tenant_id=tenant_id, credential_id=credential_id
        ).payload()
        candidate = WhatsAppTenantCredential(
            id=credential_id,
            tenant_id=tenant_id,
            environment=environment,
            instance_name=instance,
            webhook_secret_envelope=envelope,
        )
        try:
            with db.begin_nested():
                db.add(candidate)
                db.flush()
            credential = candidate
        except IntegrityError:
            credential = None
        if credential is None:
            credential = credential_for_tenant(db, tenant_id=tenant_id)
            if credential is None:
                raise WhatsAppConfigurationError(
                    "Não foi possível reservar a instância do WhatsApp."
                ) from None

    normalized = normalize_configured_phone(expected_phone_e164)
    settings = configure_expected_phone(db, normalized, tenant_id=tenant_id)
    provider = provider_for_credential(db, credential=credential)
    return credential, settings, provider
