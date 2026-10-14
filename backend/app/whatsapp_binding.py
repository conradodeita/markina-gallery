"""Associação de conta a configuração segura de servidor, sem fallback multitenant."""

from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import require_active_owner
from app.auth import WhatsAppChannelSettings
from app.messaging import (
    EvolutionWhatsAppProvider,
    SandboxWhatsAppProvider,
    WhatsAppConfigurationError,
    WhatsAppProvider,
    configured_photographer_phone,
    normalize_configured_phone,
    whatsapp_provider_from_environment,
    whatsapp_provider_name,
)
from app.tenancy import TenantContextError, require_single_tenant


def _invalid() -> WhatsAppConfigurationError:
    return WhatsAppConfigurationError("Associação do canal indisponível.")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _invalid()
        result[key] = value
    return result


def binding_aliases() -> dict[UUID, str]:
    try:
        value = json.loads(os.getenv("WHATSAPP_TENANT_BINDINGS", "{}"),
                           object_pairs_hook=_unique_pairs)
        if not isinstance(value, dict):
            raise _invalid()
        result = {}
        for key, alias in value.items():
            owner = UUID(key)
            if (str(owner) != key or not isinstance(alias, str)
                    or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,31}", alias)
                    or alias in result.values()):
                raise _invalid()
            result[owner] = alias
        return result
    except (ValueError, TypeError, AttributeError):
        raise _invalid() from None


@dataclass(frozen=True, repr=False)
class WhatsAppBinding:
    tenant_id: UUID
    name: str
    provider: WhatsAppProvider = field(compare=False)
    identity: tuple[str, ...] = field(repr=False)
    photographer_phone: str | None = None


def resolve_binding(db: Session, tenant_id: UUID) -> WhatsAppBinding:
    require_active_owner(db, tenant_id)
    aliases = binding_aliases()
    alias = aliases.get(tenant_id)
    if alias is None:
        try:
            if require_single_tenant(db).id != tenant_id:
                raise _invalid()
        except TenantContextError:
            raise _invalid() from None
        provider = whatsapp_provider_from_environment()
        name = whatsapp_provider_name()
        identity = tuple(os.getenv(f"WHATSAPP_{key}", "") for key in (
            "PROVIDER", "CREDENTIAL_ENV", "API_URL", "API_KEY", "INSTANCE",
            "WEBHOOK_URL", "WEBHOOK_SECRET", "TIMEOUT_SECONDS", "PHOTOGRAPHER_PHONE_E164"))
        return WhatsAppBinding(tenant_id, name, provider, identity, configured_photographer_phone())
    prefix = f"WHATSAPP_BINDING_{alias}_"
    read = lambda key, default="": os.getenv(prefix + key, default).strip()
    environment = os.getenv("APP_ENV", "development").strip()
    name = read("PROVIDER").lower()
    if read("CREDENTIAL_ENV") != environment or name not in {"sandbox", "evolution"}:
        raise _invalid()
    phone = normalize_configured_phone(read("PHOTOGRAPHER_PHONE_E164")) if read("PHOTOGRAPHER_PHONE_E164") else None
    identity = (environment, alias, name, read("CREDENTIAL_ENV"), read("API_URL"),
                read("API_KEY"), read("INSTANCE"), read("WEBHOOK_URL"), read("WEBHOOK_SECRET"),
                read("TIMEOUT_SECONDS", "10"), read("PHOTOGRAPHER_PHONE_E164"))
    if name == "sandbox":
        return WhatsAppBinding(tenant_id, name, SandboxWhatsAppProvider(), identity, phone)
    values = {key: read(key.upper()) for key in (
        "api_url", "api_key", "instance", "webhook_url", "webhook_secret")}
    if not all(values.values()):
        raise _invalid()
    # Uma credencial completa de B nunca pode selecionar a instância/secret de A.
    for other in aliases.values():
        if other == alias:
            continue
        other_prefix = f"WHATSAPP_BINDING_{other}_"
        if os.getenv(other_prefix + "PROVIDER", "").strip().lower() != "evolution":
            continue
        same_instance = (os.getenv(other_prefix + "API_URL", "").strip().rstrip("/") == values["api_url"].rstrip("/")
                         and os.getenv(other_prefix + "INSTANCE", "").strip() == values["instance"])
        same_secret = os.getenv(other_prefix + "WEBHOOK_SECRET", "").strip() == values["webhook_secret"]
        if same_instance or same_secret:
            raise _invalid()
    try:
        timeout = float(read("TIMEOUT_SECONDS", "10"))
    except ValueError:
        raise _invalid() from None
    if not 1 <= timeout <= 30:
        raise _invalid()
    return WhatsAppBinding(tenant_id, name, EvolutionWhatsAppProvider(**values, timeout_seconds=timeout), identity, phone)


class OwnedWhatsAppProvider(WhatsAppProvider):
    """Toda chamada revalida o vínculo, inclusive depois de consultar o canal."""

    def __init__(self, db: Session, binding: WhatsAppBinding, adapter=None):
        self.db, self.binding = db, binding
        self.adapter = adapter or binding.provider

    @property
    def tenant_id(self):
        return self.binding.tenant_id

    def validate(self):
        if resolve_binding(self.db, self.tenant_id).identity != self.binding.identity:
            raise _invalid()

    def send_transactional(self, phone_e164, message, *, idempotency_key):
        self.validate()
        return self.adapter.send_transactional(phone_e164, message,
            idempotency_key=f"tenant:{self.tenant_id}:{idempotency_key}")

    def connection_status(self):
        self.validate()
        return self.adapter.connection_status()

    def ensure_instance(self):
        self.validate()
        return self.adapter.ensure_instance()

    def start_pairing(self, phone_e164):
        self.validate()
        return self.adapter.start_pairing(phone_e164)

    def reconcile(self, external_message_id):
        self.validate()
        return self.adapter.reconcile(external_message_id)


def provider_for(db: Session, *, tenant_id: UUID, adapter=None) -> OwnedWhatsAppProvider:
    binding = resolve_binding(db, tenant_id)
    if isinstance(adapter, OwnedWhatsAppProvider):
        if adapter.tenant_id != tenant_id:
            raise _invalid()
        adapter.validate()
        adapter = adapter.adapter
    return OwnedWhatsAppProvider(db, binding, adapter)


def photographer_phone(db: Session, *, tenant_id: UUID) -> str | None:
    binding = resolve_binding(db, tenant_id)
    settings = db.scalar(select(WhatsAppChannelSettings).where(
        WhatsAppChannelSettings.tenant_id == tenant_id,
        WhatsAppChannelSettings.environment == os.getenv("APP_ENV", "development").strip(),
    ).execution_options(populate_existing=True))
    if binding.name == "sandbox":
        return (settings.expected_phone_e164 if settings else None) or binding.photographer_phone
    return settings.expected_phone_e164 if settings and settings.status == "ready" else None


def webhook_owner(db: Session, payload: dict, provided: str) -> UUID:
    """Instância + segredo de servidor; conteúdo do evento nunca escolhe UUID."""
    instance = payload.get("instance")
    if not provided or not isinstance(instance, str) or not instance:
        raise HTTPException(status_code=403, detail="Evento não autorizado.")
    aliases = binding_aliases()
    if aliases:
        owners = aliases.keys()
    else:
        try:
            owners = [require_single_tenant(db).id]
        except TenantContextError:
            owners = []
    matches = []
    for owner in owners:
        try:
            binding = resolve_binding(db, owner)
        except (WhatsAppConfigurationError, HTTPException):
            continue
        provider = binding.provider
        if (isinstance(provider, EvolutionWhatsAppProvider) and provider.instance == instance
                and secrets.compare_digest(provider.webhook_secret, provided)):
            matches.append(owner)
    if len(matches) != 1:
        raise HTTPException(status_code=403, detail="Evento não autorizado.")
    return matches[0]
