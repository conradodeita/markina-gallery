"""Concessão/revogação offline com dry-run e confirmação explícita do UUID."""

import argparse
import json
import re
from dataclasses import asdict, dataclass
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import AdminUser, AuditEvent, InstallationOperator, SessionLocal, now
from app.tenancy import TenantContextError, require_admin_tenant


@dataclass(frozen=True)
class OperatorPlan:
    action: str
    changed: bool


def provision_operator(db: Session, *, admin_id: UUID, action: str,
                       authorization_reference: str, apply: bool = False) -> OperatorPlan:
    if action not in {"grant", "revoke"} or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,119}", authorization_reference):
        raise ValueError("Ação ou referência de autorização inválida.")
    if apply and db.bind.dialect.name == "postgresql":
        connection = db.connection()
        table = InstallationOperator.__table__
        translation = connection.get_execution_options().get("schema_translate_map", {})
        schema = translation.get(table.schema, table.schema)
        quote = connection.dialect.identifier_preparer
        prefix = f"{quote.quote_schema(schema)}." if schema else ""
        db.execute(text(f"LOCK TABLE {prefix}{quote.quote(table.name)} IN SHARE ROW EXCLUSIVE MODE"))
    admin = db.get(AdminUser, admin_id, populate_existing=True)
    if not admin:
        raise TenantContextError("Destino administrativo indisponível.")
    if action == "grant":
        if not admin.email_verified:
            raise TenantContextError("Identidade administrativa não verificada.")
        require_admin_tenant(db, admin_id)
    permission = db.scalar(select(InstallationOperator).where(
        InstallationOperator.admin_user_id == admin_id,
    ).execution_options(populate_existing=True))
    active = bool(permission and permission.active and permission.revoked_at is None)
    changed = active != (action == "grant")
    plan = OperatorPlan(action, changed)
    if not apply or not changed:
        return plan
    instant = now()
    if action == "grant":
        # Revalida no limite da publicação da concessão.
        require_admin_tenant(db, admin_id)
        if permission is None:
            permission = InstallationOperator(admin_user_id=admin_id)
            db.add(permission)
        permission.active = True
        permission.granted_at = instant
        permission.revoked_at = None
    else:
        permission.active = False
        permission.revoked_at = instant
    permission.authorization_reference = authorization_reference
    permission.updated_at = instant
    db.add(AuditEvent(event=f"installation_operator.{action}", subject=(
        f"admin_id:{admin_id};authorization_reference:{authorization_reference}"
    )))
    db.flush()
    return plan


def canonical_uuid(value: str) -> UUID:
    try:
        result = UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("UUID administrativo inválido.") from exc
    if str(result) != value:
        raise argparse.ArgumentTypeError("Use UUID administrativo canônico.")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-id", required=True, type=canonical_uuid)
    parser.add_argument("--action", choices=("grant", "revoke"), required=True)
    parser.add_argument("--authorization-reference", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-admin", type=canonical_uuid)
    args = parser.parse_args()
    if args.apply and args.confirm_admin != args.admin_id:
        parser.error("--apply exige --confirm-admin igual ao UUID administrativo")
    try:
        with SessionLocal() as db:
            plan = provision_operator(db, admin_id=args.admin_id, action=args.action,
                authorization_reference=args.authorization_reference, apply=args.apply)
            if args.apply:
                db.commit()
            print(json.dumps({**asdict(plan), "applied": args.apply}, sort_keys=True))
    except (ValueError, TenantContextError, SQLAlchemyError):
        parser.exit(1, "Permissão recusada; confira identidade, vínculo e referência de autorização.\n")


if __name__ == "__main__":
    main()
