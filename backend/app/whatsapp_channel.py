"""Estado operacional do canal WhatsApp sem exposição de credenciais."""

from __future__ import annotations

import os
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import require_active_owner
from app.auth import WhatsAppChannelSettings, audit, now
from app.messaging import (
    WhatsAppConfigurationError,
    WhatsAppDeliveryError,
    WhatsAppPairingResult,
    WhatsAppProvider,
    mask_phone,
    normalize_configured_phone,
)
from app.whatsapp_binding import OwnedWhatsAppProvider, resolve_binding


def app_environment() -> str:
    return os.getenv("APP_ENV", "development").strip()


def whatsapp_identities_match(
    expected_phone_e164: str | None, connected_phone_e164: str | None
) -> bool:
    """Compara a identidade exata, incluindo o JID brasileiro móvel legado."""
    if not expected_phone_e164 or not connected_phone_e164:
        return False
    if expected_phone_e164 == connected_phone_e164:
        return True

    longer, shorter = sorted(
        (expected_phone_e164, connected_phone_e164), key=len, reverse=True
    )
    return (
        len(longer) == 14
        and len(shorter) == 13
        and longer.startswith("+55")
        and shorter.startswith("+55")
        and longer[3:].isdigit()
        and shorter[3:].isdigit()
        and longer[5] == "9"
        and longer[:5] + longer[6:] == shorter
    )


def channel_settings(db: Session, *, tenant_id: UUID) -> WhatsAppChannelSettings:
    require_active_owner(db, tenant_id)
    environment = app_environment()
    settings = db.scalar(
        select(WhatsAppChannelSettings).where(
            WhatsAppChannelSettings.tenant_id == tenant_id,
            WhatsAppChannelSettings.environment == environment
        )
    )
    if not settings:
        try:
            provider_name = resolve_binding(db, tenant_id).name
        except WhatsAppConfigurationError:
            provider_name = "unavailable"
        settings = WhatsAppChannelSettings(
            tenant_id=tenant_id, environment=environment,
            status="sandbox"
            if provider_name == "sandbox"
            else "pending_pairing",
        )
        db.add(settings)
        db.flush()
    return settings


def refresh_channel(
    db: Session, provider: WhatsAppProvider, *, tenant_id: UUID
) -> WhatsAppChannelSettings:
    settings = channel_settings(db, tenant_id=tenant_id)
    settings.last_checked_at = now()
    settings.last_error = None
    validate_provider(provider, tenant_id)
    if provider.binding.name == "sandbox":
        settings.status = "sandbox"
        settings.connected_phone_e164 = None
        db.commit()
        return settings
    try:
        result = provider.connection_status()
    except (WhatsAppConfigurationError, WhatsAppDeliveryError):
        settings.status = "error"
        settings.connected_phone_e164 = None
        settings.last_error = "Não foi possível consultar o canal."
        db.commit()
        return settings
    provider.validate()
    settings.connected_phone_e164 = result.connected_phone_e164
    if result.state == "open":
        if not settings.expected_phone_e164:
            settings.status = "pending_pairing"
        elif whatsapp_identities_match(
            settings.expected_phone_e164, result.connected_phone_e164
        ):
            settings.status = "ready"
        else:
            settings.status = "mismatch"
            settings.last_error = "O número conectado diverge do número esperado."
    elif result.state == "connecting":
        settings.status = "connecting"
    else:
        settings.status = "disconnected"
    db.commit()
    return settings


def validate_provider(provider, tenant_id):
    if not isinstance(provider, OwnedWhatsAppProvider) or provider.tenant_id != tenant_id:
        raise WhatsAppConfigurationError("Associação do canal indisponível.")
    provider.validate()


def require_ready_channel(db: Session, provider: WhatsAppProvider, *, tenant_id: UUID) -> None:
    validate_provider(provider, tenant_id)
    if provider.binding.name == "sandbox":
        return
    settings = refresh_channel(db, provider, tenant_id=tenant_id)
    if settings.status == "mismatch":
        raise WhatsAppConfigurationError("Identidade remetente divergente.")
    if settings.status != "ready":
        raise WhatsAppDeliveryError(
            "Canal WhatsApp temporariamente indisponível.", transient=True
        )


def configure_expected_phone(
    db: Session, phone_e164: str, *, tenant_id: UUID
) -> WhatsAppChannelSettings:
    settings = channel_settings(db, tenant_id=tenant_id)
    normalized = normalize_configured_phone(phone_e164)
    if settings.expected_phone_e164 != normalized:
        settings.expected_phone_e164 = normalized
        settings.status = "pending_pairing"
        settings.connected_phone_e164 = None
        settings.last_error = None
        settings.last_checked_at = None
        audit(db, "whatsapp.expected_phone_updated", str(settings.id), tenant_id=tenant_id)
    db.commit()
    return settings


def start_channel_pairing(
    db: Session, provider: WhatsAppProvider, *, tenant_id: UUID
) -> tuple[WhatsAppChannelSettings, WhatsAppPairingResult]:
    settings = channel_settings(db, tenant_id=tenant_id)
    if not settings.expected_phone_e164:
        raise WhatsAppConfigurationError("Configure o número esperado antes do pareamento.")
    validate_provider(provider, tenant_id)
    result = provider.start_pairing(settings.expected_phone_e164)
    provider.validate()
    settings.status = "connecting" if result.state != "open" else "pending_pairing"
    settings.last_checked_at = now()
    settings.last_error = None
    audit(db, "whatsapp.pairing_started", str(settings.id), tenant_id=tenant_id)
    db.commit()
    return settings, result


def channel_payload(db: Session, settings: WhatsAppChannelSettings) -> dict[str, str | None]:
    try:
        name = resolve_binding(db, settings.tenant_id).name
    except WhatsAppConfigurationError:
        name = "unavailable"
    return {
        "provider": name,
        "environment": settings.environment,
        "expected_phone": mask_phone(settings.expected_phone_e164),
        "connected_phone": mask_phone(settings.connected_phone_e164),
        "status": settings.status,
        "last_error": settings.last_error,
        "last_checked_at": settings.last_checked_at.isoformat()
        if settings.last_checked_at
        else None,
    }
