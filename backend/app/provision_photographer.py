"""Provisionamento offline controlado; dry-run padrão e nenhum segredo em saída."""

import argparse
import binascii
import json
import os
from dataclasses import asdict, dataclass
from uuid import UUID

import pyotp
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    SessionLocal,
    Tenant,
    TenantAdmin,
    password_hasher,
    validate_admin_password,
)
from app.tenancy import TenantContextError


@dataclass(frozen=True)
class ProvisionPlan:
    tenant_id: UUID
    create_tenant: bool
    create_admin: bool
    create_membership: bool

    def public_result(self, *, applied: bool) -> dict:
        return {**asdict(self), "tenant_id": str(self.tenant_id), "applied": applied}


def existing_admin_by_email(db: Session, email: str) -> AdminUser | None:
    admins = list(db.scalars(select(AdminUser).where(func.lower(AdminUser.email) == email).limit(2)))
    if len(admins) > 1:
        raise TenantContextError("Administrador ambíguo; nenhuma alteração aplicada.")
    return admins[0] if admins else None


def existing_admin_owner(db: Session, admin_id: UUID) -> Tenant:
    memberships = list(db.scalars(select(TenantAdmin).where(
        TenantAdmin.admin_user_id == admin_id, TenantAdmin.active.is_(True),
    ).limit(2).execution_options(populate_existing=True)))
    if len(memberships) != 1:
        raise TenantContextError("Vínculo administrativo ausente ou ambíguo.")
    tenant = db.get(Tenant, memberships[0].tenant_id, populate_existing=True)
    if tenant is None or tenant.status != "active":
        raise TenantContextError("Conta administrativa indisponível.")
    return tenant


def plan_provisioning(db: Session, tenant_id: UUID, email: str, *, create_tenant=False) -> ProvisionPlan:
    email = email.strip().lower()
    if not email or "@" not in email or len(email) > 320:
        raise RuntimeError("E-mail administrativo inválido.")
    tenant = db.get(Tenant, tenant_id, populate_existing=True)
    admin = existing_admin_by_email(db, email)
    if tenant is None and not create_tenant:
        raise TenantContextError("Conta de destino ausente; criação explícita necessária.")
    if tenant is not None and tenant.status != "active":
        raise TenantContextError("Conta de destino indisponível; nenhuma reativação automática.")
    if admin:
        owner = existing_admin_owner(db, admin.id)
        if owner.id != tenant_id:
            raise TenantContextError("Administrador vinculado a outro destino; nenhuma alteração aplicada.")
        return ProvisionPlan(tenant_id, False, False, False)
    if db.scalar(select(TenantAdmin.id).where(TenantAdmin.tenant_id == tenant_id).limit(1)):
        raise TenantContextError("Destino já vinculado; não adicionar administrador automaticamente.")
    return ProvisionPlan(tenant_id, tenant is None, True, True)


def validate_new_credentials(email: str, password: str | None, totp_secret: str | None) -> str:
    if not password or not totp_secret:
        raise RuntimeError("Credenciais novas exigem ADMIN_SEED_PASSWORD e ADMIN_SEED_TOTP_SECRET externos.")
    try:
        validate_admin_password(password, email=email)
        normalized = totp_secret.replace(" ", "").upper()
        pyotp.TOTP(normalized).now()
    except (ValueError, TypeError, KeyError, binascii.Error) as exc:
        raise RuntimeError("Credenciais administrativas novas inválidas.") from exc
    return normalized


def provision_photographer(
    db: Session, tenant_id: UUID, email: str, *, create_tenant=False, apply=False,
    password: str | None = None, totp_secret: str | None = None,
) -> ProvisionPlan:
    if apply and db.bind is not None and db.bind.dialect.name == "postgresql":
        connection = db.connection()
        translation = connection.get_execution_options().get("schema_translate_map", {})
        preparer = connection.dialect.identifier_preparer
        names = []
        for table in (Tenant.__table__, AdminUser.__table__, TenantAdmin.__table__):
            schema = translation.get(table.schema, table.schema)
            prefix = f"{preparer.quote_schema(schema)}." if schema else ""
            names.append(prefix + preparer.quote(table.name))
        db.execute(text("LOCK TABLE " + ", ".join(names) + " IN SHARE ROW EXCLUSIVE MODE"))
    email = email.strip().lower()
    plan = plan_provisioning(db, tenant_id, email, create_tenant=create_tenant)
    if not apply or not plan.create_admin:
        return plan
    normalized_totp = validate_new_credentials(email, password, totp_secret)
    if plan.create_tenant:
        db.add(Tenant(id=tenant_id))
        db.flush()
    admin = AdminUser(email=email, password_hash=password_hasher.hash(password),
                      totp_secret=normalized_totp, email_verified=True)
    admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant_id))
    db.add(admin)
    db.flush()
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", type=UUID, required=True)
    parser.add_argument("--create-tenant", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-tenant", type=UUID)
    args = parser.parse_args()
    if args.apply and args.confirm_tenant != args.tenant_id:
        parser.error("--apply exige --confirm-tenant igual ao UUID de destino")
    try:
        with SessionLocal() as db:
            plan = provision_photographer(
                db, args.tenant_id, os.getenv("ADMIN_SEED_EMAIL", ""),
                create_tenant=args.create_tenant, apply=args.apply,
                password=os.getenv("ADMIN_SEED_PASSWORD"), totp_secret=os.getenv("ADMIN_SEED_TOTP_SECRET"),
            )
            if args.apply:
                db.commit()
            print(json.dumps(plan.public_result(applied=args.apply), sort_keys=True))
    except (RuntimeError, ValueError, SQLAlchemyError):
        parser.exit(1, "Provisionamento recusado; verifique destino, vínculos e configuração externa.\n")


if __name__ == "__main__":
    main()
