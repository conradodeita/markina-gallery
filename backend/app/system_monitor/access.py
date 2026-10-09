"""Nenhum papel antigo implica uma permissão do novo monitor."""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.auth import AdminUser
from app.system_monitor.models import PERMISSIONS, MonitorGrant, PlatformOwner


def is_owner(db, admin_id: UUID) -> bool:
    return db.scalar(select(AdminUser.id).join(PlatformOwner, PlatformOwner.admin_user_id == AdminUser.id).where(
        AdminUser.id == admin_id, AdminUser.email_verified.is_(True),
        PlatformOwner.singleton == 1,
    )) is not None


def require_owner(db, admin_id: UUID) -> None:
    if not is_owner(db, admin_id):
        raise HTTPException(403, "Acesso não autorizado ao monitor.", headers={"Cache-Control": "private, no-store"})


def permissions(db, admin_id: UUID) -> set[str]:
    if not is_owner(db, admin_id):
        return set()
    return set(db.scalars(select(MonitorGrant.permission).where(
        MonitorGrant.admin_user_id == admin_id, MonitorGrant.active.is_(True),
        MonitorGrant.permission.in_(PERMISSIONS),
    )))


def require_permission(db, admin_id: UUID, permission: str) -> None:
    if permission not in permissions(db, admin_id):
        raise HTTPException(403, "Acesso não autorizado ao monitor.")
