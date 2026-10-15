"""Concessão offline explícita; dry-run padrão, sem endpoint de autoelevação."""
import argparse
import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.auth import AdminUser, SessionLocal, audit
from app.system_monitor.access import require_owner
from app.system_monitor.models import PERMISSIONS, MonitorGrant, PlatformOwner
from app.system_monitor.store import bounded, insert
from app.tenancy import TenantContextError, require_admin_tenant


def establish_owner(db, admin_id, confirmation_email, reference):
    if not re.fullmatch(r"[a-zA-Z0-9_.:/-]{1,120}", reference):
        raise ValueError("Referência inválida.")
    admin = db.get(AdminUser, admin_id, populate_existing=True)
    if not admin or not admin.email_verified or admin.email.lower() != confirmation_email.strip().lower():
        raise ValueError("Confirmação da conta inválida.")
    tenant = require_admin_tenant(db, admin_id)
    owner = db.get(PlatformOwner, 1, populate_existing=True)
    if owner and owner.admin_user_id != admin_id:
        raise ValueError("Transferência de propriedade requer decisão própria; recusada.")
    if not owner:
        db.add(PlatformOwner(singleton=1, admin_user_id=admin_id, authorization_reference=reference))
        audit(db, "system_monitor.owner_established", str(admin_id), tenant_id=tenant.id)
        db.flush()


def change_grants(db, admin_id, selected, reference, *, revoke=False):
    if not selected or not set(selected) <= set(PERMISSIONS) or not re.fullmatch(r"[a-zA-Z0-9_.:/-]{1,120}", reference):
        raise ValueError("Permissões ou referência inválidas.")
    admin = db.get(AdminUser, admin_id)
    if not admin or (not revoke and not admin.email_verified):
        raise ValueError("Administrador elegível não encontrado.")
    if not revoke:
        require_owner(db, admin_id)
    tenant_id = None if revoke else require_admin_tenant(db, admin_id).id
    for permission in set(selected):
        statement = insert(db, MonitorGrant).values(admin_user_id=admin_id, permission=permission,
            active=not revoke, authorization_reference=reference, updated_at=datetime.now(UTC))
        db.execute(statement.on_conflict_do_update(index_elements=["admin_user_id", "permission"],
            set_={"active": not revoke, "authorization_reference": reference, "updated_at": datetime.now(UTC)}))
    audit(db, "system_monitor.grants_revoked" if revoke else "system_monitor.grants_granted",
          str(admin_id), tenant_id=tenant_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-id", type=UUID, required=True)
    parser.add_argument("--permission", action="append", required=True, choices=PERMISSIONS)
    parser.add_argument("--authorization-reference", required=True)
    parser.add_argument("--revoke", action="store_true")
    parser.add_argument("--establish-owner-email", help="Indicação inicial explícita; recusa substituir proprietário existente")
    parser.add_argument("--apply", action="store_true", help="Persistir somente após autorização operacional explícita")
    args = parser.parse_args()
    try:
        with SessionLocal() as db:
            bounded(db)
            if args.establish_owner_email:
                if args.revoke:
                    raise ValueError("Opções incompatíveis.")
                establish_owner(db, args.admin_id, args.establish_owner_email, args.authorization_reference)
            change_grants(db, args.admin_id, args.permission, args.authorization_reference, revoke=args.revoke)
            if args.apply:
                db.commit()
            else:
                db.rollback()
        print("Concessões atualizadas." if args.apply else "Dry-run concluído; nenhuma concessão persistida.")
    except (ValueError, TenantContextError, SQLAlchemyError, HTTPException):
        parser.exit(1, "Operação recusada; verifique elegibilidade, migration e autorização.\n")


if __name__ == "__main__":
    main()
