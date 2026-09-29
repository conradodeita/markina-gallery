"""Fundação de propriedade; esta versão admite uma única conta na instalação."""

from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.auth import ParentGallery, Tenant, TenantAdmin


class TenantContextError(RuntimeError):
    """Contexto ausente, suspenso ou incompatível; nunca escolher uma conta por fallback."""


def require_single_tenant(db: Session) -> Tenant:
    tenants = list(db.scalars(select(Tenant).limit(2).execution_options(populate_existing=True)))
    if len(tenants) != 1 or tenants[0].status != "active":
        raise TenantContextError("Contexto do fotógrafo indisponível.")
    return tenants[0]


def require_admin_tenant(db: Session, admin_id: UUID) -> Tenant:
    tenant = require_single_tenant(db)
    if not db.scalar(select(TenantAdmin.id).where(
        TenantAdmin.tenant_id == tenant.id,
        TenantAdmin.admin_user_id == admin_id,
        TenantAdmin.active.is_(True),
    )):
        raise TenantContextError("Acesso negado.")
    return tenant


def require_parent_tenant(db: Session, parent_id: UUID) -> UUID:
    tenant = require_single_tenant(db)
    parent = db.get(ParentGallery, parent_id, populate_existing=True)
    if parent is None or parent.tenant_id != tenant.id:
        raise TenantContextError("Contexto do acervo indisponível.")
    return tenant.id


def enable_domain_guard(db: Session) -> None:
    require_single_tenant(db)
    db.info["tenant_domain_guard"] = True


@contextmanager
def domain_session(session_factory):
    with session_factory() as db:
        enable_domain_guard(db)
        yield db


@event.listens_for(Session, "before_commit")
def _revalidate_domain_commit(db: Session) -> None:
    if db.info.get("tenant_domain_guard"):
        require_single_tenant(db)
