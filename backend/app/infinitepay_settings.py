"""Preparação local do recebedor; não autentica nem chama a InfinitePay."""

import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import require_active_owner
from app.admin_account import require_security_owner
from app.auth import InfinitePaySettings, now


class ConfigurationConflict(ValueError):
    pass


class ReceiverInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    handle: str = Field(min_length=1, max_length=101)

    @field_validator("handle")
    @classmethod
    def declared_handle(cls, value: str) -> str:
        value = value.strip().removeprefix("$")
        # Limite local de armazenamento, não prova de validade/titularidade remota.
        if not value or len(value) > 100 or any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError("Informe sua InfiniteTag, sem espaços.")
        if any(c in value for c in "/\\?#@:$"):
            raise ValueError("Informe somente a InfiniteTag, não um link.")
        return value


class ConfigurationChallengeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128, repr=False)
    expected_version: int = Field(ge=0, strict=True)
    configuration: ReceiverInput | None
    checkout_ready: bool = False
    card_enabled: bool = False
    api_key: SecretStr | None = Field(default=None, repr=False, max_length=512, min_length=1)

    @field_validator("api_key")
    @classmethod
    def safe_api_key(cls, value):
        if value is not None:
            raw = value.get_secret_value().strip()
            if not raw or any(not 32 <= ord(c) <= 126 for c in raw):
                raise ValueError("Informe uma API Key válida.")
            return SecretStr(raw)
        return value


class ConfigurationConfirmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID
    code: str = Field(pattern=r"^\d{6}$", repr=False)


class ConfigurationResendInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID


def load_configuration(db: Session, *, tenant_id: UUID) -> InfinitePaySettings | None:
    require_active_owner(db, tenant_id)
    return db.scalar(select(InfinitePaySettings).where(InfinitePaySettings.tenant_id == tenant_id)
                     .execution_options(populate_existing=True))


def configuration_payload(settings: InfinitePaySettings | None, *,
                          api_key_configured: bool = False) -> dict:
    ready = bool(settings and settings.status == "active"
                 and settings.verification_profile == "infinitepay-public-v1"
                 and settings.verified_at is not None and settings.handle)
    card_enabled = bool(settings and settings.card_enabled)
    available = ready and card_enabled and api_key_configured
    return {
        "status": settings.status if settings else "unconfigured",
        "version": settings.version if settings else 0,
        "handle": settings.handle if settings else None,
        "card_enabled": card_enabled,
        "api_key_configured": api_key_configured,
        "checkout_available": available,
        "ownership_verified": False,
        "message": ("Cartão habilitado para novos pedidos por autodeclaração do fotógrafo."
                    if available else "Credencial segura do servidor indisponível para esta conta."
                    if ready and card_enabled and not api_key_configured else
                    "InfinitePay está pronta, mas cartão está desabilitado para novos pedidos."
                    if ready else "Cartão indisponível até o fotógrafo habilitar uma configuração pronta."),
    }


def canonical_proposal(configuration: ReceiverInput | None, version: int, checkout_ready: bool = False,
                       card_enabled: bool = False, *, db: Session | None = None,
                       tenant_id: UUID | None = None, api_key: SecretStr | None = None) -> str:
    proposal = {"checkout_ready": bool(checkout_ready and configuration),
                       "card_enabled": bool(card_enabled and configuration),
                       "handle": configuration.handle if configuration else None, "version": version}
    if db is not None and tenant_id is not None:
        from app.infinitepay_binding import api_key_configured
        from app.infinitepay_credentials import has_unresolved_payments, prepare_secret

        settings = load_configuration(db, tenant_id=tenant_id)
        if configuration is None:
            if api_key is not None:
                raise ConfigurationConflict("Não envie API Key ao desconectar.")
            if has_unresolved_payments(db, tenant_id):
                raise ConfigurationConflict("Existem compras de cartão pendentes. Concilie-as antes de desconectar; você pode desabilitar novos cartões.")
        elif api_key is not None:
            proposal["credential"] = prepare_secret(api_key.get_secret_value(), tenant_id=tenant_id)
        elif (not api_key_configured(tenant_id, db=db)
              or settings and settings.credential_source == "managed" and settings.handle != configuration.handle):
            raise ConfigurationConflict("Informe a API Key da mesma conta ao cadastrar ou alterar a InfiniteTag.")
    return json.dumps(proposal, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def proposal_preview(target: str) -> dict:
    value = json.loads(target)
    return {key: value[key] for key in ("handle", "version", "checkout_ready", "card_enabled")}


def check_version(settings: InfinitePaySettings | None, version: int) -> None:
    if (settings.version if settings else 0) != version:
        raise ConfigurationConflict("A configuração mudou em outra sessão. Recarregue e confirme novamente.")


def apply_proposal(db: Session, *, tenant_id: UUID, admin_id: UUID, target: str) -> InfinitePaySettings:
    from app.payment_availability import (
        has_published_paid_gallery,
        lock_payment_account,
        payment_methods,
    )

    require_security_owner(db, admin_id, tenant_id)
    lock_payment_account(db, tenant_id)
    proposed = json.loads(target)
    settings = load_configuration(db, tenant_id=tenant_id)
    check_version(settings, proposed["version"])
    handle = ReceiverInput(handle=proposed["handle"]).handle if proposed["handle"] is not None else None
    checkout_ready = bool(proposed.get("checkout_ready") and handle)
    card_enabled = bool(proposed.get("card_enabled") and checkout_ready)
    if proposed.get("card_enabled") and not card_enabled:
        raise ConfigurationConflict("Confirme uma configuração InfinitePay pronta antes de habilitar cartão.")
    if (not card_enabled and not payment_methods(db, tenant_id=tenant_id)["pix_available"]
            and has_published_paid_gallery(db, tenant_id)):
        raise ConfigurationConflict(
            "Esta alteração deixaria uma galeria com pagamento obrigatório sem recebimento. "
            "Configure o PIX ou desmarque a cobrança das galerias antes de desabilitar cartão."
        )
    if settings is None:
        settings = InfinitePaySettings(tenant_id=tenant_id, admin_user_id=admin_id)
        db.add(settings)
    settings.admin_user_id = admin_id
    settings.handle = handle
    settings.version = proposed["version"] + 1
    settings.status = "active" if checkout_ready else "pending" if handle else "inactive"
    settings.card_enabled = card_enabled
    settings.verification_profile = "infinitepay-public-v1" if checkout_ready else None
    settings.verified_at = now() if checkout_ready else None
    settings.updated_at = now()
    from app.infinitepay_credentials import erase_secrets, has_unresolved_payments, install_secret

    if handle is None:
        if has_unresolved_payments(db, tenant_id):
            raise ConfigurationConflict("Existem compras de cartão pendentes. Concilie-as antes de desconectar.")
        erase_secrets(db, tenant_id=tenant_id)
        settings.credential_source, settings.credential_id = "managed", None
    elif proposed.get("credential"):
        settings.credential_id = install_secret(db, tenant_id=tenant_id, proposal=proposed["credential"])
        settings.credential_source = "managed"
    db.flush()
    return settings
