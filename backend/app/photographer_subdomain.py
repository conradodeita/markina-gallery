"""Reserva inicial de hostname; não provisiona nem ativa infraestrutura externa."""

import re
import unicodedata
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import Tenant, audit
from app.tenancy import enable_domain_guard, require_admin_tenant

BASE_DOMAIN = "pickyourpic.com.br"
HEADERS = {"Cache-Control": "private, no-store"}
RESERVED_PREFIXES = frozenset({
    "markina", "www", "api", "admin", "app", "auth", "console", "platform",
    "mail", "smtp", "imap", "pop", "pop3", "support", "suporte", "status",
    "static", "cdn", "assets", "media", "files", "storage", "drive", "webhook",
    "webhooks", "billing", "payments", "pagamentos", "dev", "test", "staging",
    "homolog", "localhost",
})


class AddressInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    prefix: str = Field(min_length=1, max_length=80)


def normalize_prefix(value: str) -> str:
    candidate = value.strip()
    prefix = candidate.lower()
    if (not candidate.isascii() or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", prefix)
            or prefix.startswith("xn--")):
        raise HTTPException(422, "Use de 1 a 63 letras sem acentos, números ou hífens, sem hífen nas pontas.",
                            headers=HEADERS)
    if prefix in RESERVED_PREFIXES:
        raise HTTPException(409, "Este endereço não está disponível. Escolha outro nome.", headers=HEADERS)
    return prefix


def suggested_prefix(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    suggestion = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:63].rstrip("-")
    return "" if suggestion in RESERVED_PREFIXES else suggestion


def address_status(tenant: Tenant, name: str) -> dict:
    hostname = tenant.canonical_host
    state = "unselected" if not hostname else (
        "reserved" if tenant.canonical_host_status == "reserved" else "ready"
    )
    return {
        "base_domain": BASE_DOMAIN,
        "hostname": hostname,
        "state": state,
        "choice_complete": bool(hostname),
        "suggested_prefix": suggested_prefix(name) if not hostname else None,
        "public_url": f"https://{hostname}" if state == "ready" else None,
    }


def reserve_address(db: Session, *, tenant_id: UUID, admin_id: UUID, prefix: str, name: str) -> dict:
    prefix = normalize_prefix(prefix)
    hostname = f"{prefix}.{BASE_DOMAIN}"
    enable_domain_guard(db)
    owner = require_admin_tenant(db, admin_id)
    if owner.id != tenant_id:
        raise HTTPException(403, "Acesso negado.", headers=HEADERS)
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update()
                       .execution_options(populate_existing=True))
    if not tenant or tenant.status != "active":
        raise HTTPException(403, "Acesso negado.", headers=HEADERS)
    if tenant.canonical_host:
        if tenant.canonical_host != hostname:
            raise HTTPException(409, "Sua conta já possui um endereço escolhido.", headers=HEADERS)
        return address_status(tenant, name)
    tenant.canonical_host = hostname
    tenant.canonical_host_status = "reserved"
    audit(db, "photographer_subdomain.reserved", str(admin_id), tenant_id=tenant_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Este endereço não está disponível. Escolha outro nome.", headers=HEADERS) from None
    return address_status(tenant, name)
