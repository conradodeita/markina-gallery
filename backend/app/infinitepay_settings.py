"""Preparação local do recebedor; não autentica nem chama a InfinitePay."""

import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
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


class ConfigurationConfirmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID
    code: str = Field(pattern=r"^\d{6}$", repr=False)


class ConfigurationResendInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID


def load_configuration(db: Session, *, tenant_id: UUID) -> InfinitePaySettings | None:
    require_active_owner(db, tenant_id)
    return db.scalar(select(InfinitePaySettings).where(InfinitePaySettings.tenant_id == tenant_id))


def configuration_payload(settings: InfinitePaySettings | None) -> dict:
    available = bool(settings and settings.status == "active"
                     and settings.verification_profile == "infinitepay-public-v1"
                     and settings.verified_at is not None and settings.handle)
    return {
        "status": settings.status if settings else "unconfigured",
        "version": settings.version if settings else 0,
        "handle": settings.handle if settings else None,
        "checkout_available": available,
        "ownership_verified": False,
        "message": ("Cartão habilitado por autodeclaração do fotógrafo; confirme o recebedor no checkout de teste."
                    if available else "Cartão indisponível até o fotógrafo confirmar sua tag e as opções do Checkout Integrado."),
    }


def canonical_proposal(configuration: ReceiverInput | None, version: int, checkout_ready: bool = False) -> str:
    return json.dumps({"checkout_ready": bool(checkout_ready and configuration),
                       "handle": configuration.handle if configuration else None, "version": version},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def check_version(settings: InfinitePaySettings | None, version: int) -> None:
    if (settings.version if settings else 0) != version:
        raise ConfigurationConflict("A configuração mudou em outra sessão. Recarregue e confirme novamente.")


def apply_proposal(db: Session, *, tenant_id: UUID, admin_id: UUID, target: str) -> InfinitePaySettings:
    require_security_owner(db, admin_id, tenant_id)
    proposed = json.loads(target)
    settings = load_configuration(db, tenant_id=tenant_id)
    check_version(settings, proposed["version"])
    handle = ReceiverInput(handle=proposed["handle"]).handle if proposed["handle"] is not None else None
    checkout_ready = bool(proposed.get("checkout_ready") and handle)
    if settings is None:
        settings = InfinitePaySettings(tenant_id=tenant_id, admin_user_id=admin_id)
        db.add(settings)
    settings.admin_user_id = admin_id
    settings.handle = handle
    settings.version = proposed["version"] + 1
    settings.status = "active" if checkout_ready else "pending" if handle else "inactive"
    settings.verification_profile = "infinitepay-public-v1" if checkout_ready else None
    settings.verified_at = now() if checkout_ready else None
    settings.updated_at = now()
    db.flush()
    return settings
