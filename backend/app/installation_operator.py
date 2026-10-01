"""Autorização técnica de diagnóstico; sem selecionar ou ampliar conta comercial."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import InstallationOperator


def operator_is_active(db: Session, admin_id: UUID) -> bool:
    # Consulta escalar fresca evita autorização pelo identity map/cache do ORM.
    return bool(db.scalar(select(InstallationOperator.active).where(
        InstallationOperator.admin_user_id == admin_id,
        InstallationOperator.active.is_(True), InstallationOperator.revoked_at.is_(None),
    )))


def require_operator(db: Session, admin_id: UUID) -> None:
    if not operator_is_active(db, admin_id):
        raise HTTPException(status_code=403, detail="Acesso não autorizado.")
