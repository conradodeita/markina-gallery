"""Map an exact canonical request Host to an active photographer tenant."""

from __future__ import annotations

import os
import re
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Tenant


class CanonicalHostError(ValueError):
    """The request or configured host is not a canonical public hostname."""


def normalize_canonical_host(value: str) -> str:
    candidate = value.strip()
    if not candidate or any(char.isspace() for char in candidate) or any(char in candidate for char in "/\\@%?#"):
        raise CanonicalHostError("Hostname canônico inválido.")
    try:
        parsed = urlsplit(f"//{candidate}")
        if parsed.hostname is None or parsed.port is not None or parsed.path or parsed.query or parsed.fragment:
            raise ValueError()
        hostname = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    except (UnicodeError, ValueError) as exc:
        raise CanonicalHostError("Hostname canônico inválido.") from exc
    if len(hostname) > 253 or "." not in hostname or re.fullmatch(r"[0-9.]+", hostname):
        raise CanonicalHostError("Hostname canônico inválido.")
    labels = hostname.split(".")
    if any(
        not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
        or not re.fullmatch(r"[a-z0-9-]+", label)
        for label in labels
    ):
        raise CanonicalHostError("Hostname canônico inválido.")
    if hostname.endswith((".localhost", ".local", ".internal", ".test", ".invalid")):
        raise CanonicalHostError("Hostname canônico inválido.")
    return hostname


def request_hostname(raw_host: str | None) -> str:
    if not raw_host:
        raise CanonicalHostError("Hostname indisponível.")
    candidate = raw_host.strip()
    try:
        parsed = urlsplit(f"//{candidate}")
        port = parsed.port
        if parsed.hostname is None or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError()
        if port not in {None, 443}:
            raise ValueError()
        return normalize_canonical_host(parsed.hostname)
    except (UnicodeError, ValueError) as exc:
        raise CanonicalHostError("Hostname indisponível.") from exc


def tenant_for_host(db: Session, host: str | None) -> Tenant | None:
    try:
        hostname = request_hostname(host)
    except CanonicalHostError:
        return None
    tenant = db.scalar(select(Tenant).where(Tenant.canonical_host == hostname).execution_options(populate_existing=True))
    if tenant:
        return tenant if tenant.status == "active" else None
    try:
        origin_hostname = configured_origin_hostname()
    except CanonicalHostError:
        return None
    if hostname != origin_hostname:
        return None
    active_tenants = db.scalars(select(Tenant).where(Tenant.status == "active")).all()
    if len(active_tenants) != 1 or active_tenants[0].canonical_host is not None:
        return None
    return active_tenants[0]


def tenant_id_for_host(db: Session, host: str | None) -> UUID | None:
    tenant = tenant_for_host(db, host)
    return tenant.id if tenant else None


def configured_origin_hostname() -> str:
    from app.public_origin import PublicOriginError, public_app_origin

    try:
        origin = public_app_origin(os.getenv("APP_ENV", "development"))
        parsed = urlsplit(origin)
        if parsed.scheme != "https" or parsed.port not in {None, 443}:
            raise ValueError()
        return normalize_canonical_host(parsed.hostname or "")
    except (PublicOriginError, ValueError, CanonicalHostError) as exc:
        raise CanonicalHostError("Origem pública HTTPS indisponível.") from exc


def canonical_host_for_tenant(db: Session, tenant: Tenant) -> str | None:
    if tenant.status != "active":
        raise CanonicalHostError("Hostname canônico indisponível.")
    if tenant.canonical_host:
        hostname = normalize_canonical_host(tenant.canonical_host)
        if hostname != tenant.canonical_host:
            raise CanonicalHostError("Hostname canônico indisponível.")
        return hostname
    active_tenants = db.scalars(select(Tenant).where(Tenant.status == "active")).all()
    if len(active_tenants) != 1 or active_tenants[0].id != tenant.id:
        raise CanonicalHostError("Hostname canônico indisponível.")
    try:
        return configured_origin_hostname()
    except CanonicalHostError:
        return None


def purchase_url_for_tenant(db: Session, tenant: Tenant, order_id: UUID) -> str:
    hostname = canonical_host_for_tenant(db, tenant)
    if not hostname:
        raise CanonicalHostError("Hostname canônico indisponível.")
    return f"https://{hostname}/library/purchases#order-{order_id}"


def public_gallery_url_for_tenant(db: Session, tenant: Tenant, parent_gallery_id: UUID) -> str:
    """Build the OTP-protected public gallery URL from the tenant's canonical host."""
    hostname = canonical_host_for_tenant(db, tenant)
    if not hostname:
        raise CanonicalHostError("Hostname canônico indisponível.")
    return f"https://{hostname}/public-galleries/{parent_gallery_id}"
