"""Cria a conta administrativa inicial somente por variáveis externas ao Git."""

from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.auth import AdminUser, SessionLocal, TenantAdmin, password_hasher
from app.provision_photographer import (
    existing_admin_by_email,
    existing_admin_owner,
    validate_new_credentials,
)
from app.tenancy import require_single_tenant


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"A variável {name} é obrigatória para criar o administrador inicial.")
    return value


def seed_admin() -> None:
    """Cria uma única conta verificada; nunca sobrescreve uma conta existente."""
    email = required_setting("ADMIN_SEED_EMAIL").lower()
    with SessionLocal() as db:
        existing = existing_admin_by_email(db, email)
        if existing:
            existing_admin_owner(db, existing.id)
            return
        tenant = require_single_tenant(db)
        if db.scalar(select(AdminUser.id)):
            raise RuntimeError("Já existe outro administrador; seed inicial interrompido.")
        password = required_setting("ADMIN_SEED_PASSWORD")
        totp_secret = validate_new_credentials(email, password, required_setting("ADMIN_SEED_TOTP_SECRET"))
        admin = AdminUser(
            email=email,
            password_hash=password_hasher.hash(password),
            email_verified=True,
            totp_secret=totp_secret,
        )
        admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
        db.add(admin)
        db.commit()


if __name__ == "__main__":
    try:
        seed_admin()
    except (RuntimeError, ValueError, SQLAlchemyError):
        raise SystemExit("Seed recusado; verifique vínculos e configuração externa.") from None
