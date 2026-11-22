"""Resolvedores explícitos e revalidação transacional dos owners demonstrados."""

from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.auth import ParentGallery, Tenant, TenantAdmin


class TenantContextError(RuntimeError):
    """Contexto ausente, suspenso ou incompatível; nunca escolher uma conta por fallback."""


def require_single_tenant(db: Session) -> Tenant:
    tenants = list(db.scalars(select(Tenant).limit(2).execution_options(populate_existing=True)))
    if len(tenants) != 1 or tenants[0].status != "active" or tenants[0].lifecycle == "closed":
        raise TenantContextError("Contexto do fotógrafo indisponível.")
    return tenants[0]


def require_admin_tenant(db: Session, admin_id: UUID, *, platform_scope: bool = False) -> Tenant:
    memberships = list(db.scalars(select(TenantAdmin).where(
        TenantAdmin.admin_user_id == admin_id,
        TenantAdmin.active.is_(True),
    ).limit(2).execution_options(populate_existing=True)))
    if len(memberships) != 1:
        raise TenantContextError("Acesso negado.")
    tenant = db.get(Tenant, memberships[0].tenant_id, populate_existing=True)
    if tenant is None or tenant.status != "active":
        raise TenantContextError("Acesso negado.")
    if tenant.lifecycle == "closed":
        from app.system_monitor.access import is_owner

        if not platform_scope or not is_owner(db, admin_id):
            raise TenantContextError("Acesso negado.")
        db.info.setdefault("tenant_platform_identity", set()).add(tenant.id)
    bind_domain_owner(db, tenant.id)
    if db.info.get("tenant_domain_guard"):
        db.info.setdefault("tenant_domain_admins", {})[admin_id] = tenant.id
    return tenant


def require_parent_tenant(db: Session, parent_id: UUID, *, tenant_id: UUID) -> UUID:
    from app.acervo_context import owned_record

    parent = owned_record(db, ParentGallery, parent_id, tenant_id=tenant_id)
    if parent is None:
        raise TenantContextError("Contexto do acervo indisponível.")
    return tenant_id


def bind_domain_owner(db: Session, tenant_id: UUID) -> None:
    """Registrar contexto comprovado; isto não concede autorização."""
    if db.info.get("tenant_domain_guard"):
        db.info.setdefault("tenant_domain_owners", set()).add(tenant_id)


def enable_domain_guard(db: Session) -> None:
    db.info["tenant_domain_guard"] = True


def bind_financial_reconciliation(db: Session, tenant_id: UUID) -> None:
    """Exceção interna para conciliar obrigação existente, nunca novo checkout.

    Chamadores: inbox assinada e workers de pagamentos/compras já persistidos.
    Não altera os resolvedores de sessão, acervo, upload ou criação de compra.
    """
    status = db.scalar(select(Tenant.status).where(Tenant.id == tenant_id))
    if status not in {"active", "suspended"}:
        raise TenantContextError("Conta financeira indisponível.")
    db.info.setdefault("tenant_financial_reconciliation", set()).add(tenant_id)
    bind_domain_owner(db, tenant_id)


def bind_privacy_retention(db: Session, tenant_id: UUID) -> None:
    """Contexto interno para redução de dados; não concede sessão ou envio."""
    if db.get(Tenant, tenant_id, populate_existing=True) is None:
        raise TenantContextError("Contexto indisponível.")
    db.info.setdefault("tenant_privacy_retention", set()).add(tenant_id)
    bind_domain_owner(db, tenant_id)


@contextmanager
def domain_session(session_factory):
    with session_factory() as db:
        enable_domain_guard(db)
        yield db


@event.listens_for(Session, "before_flush")
def _remember_changed_owners(db: Session, _flush_context, _instances) -> None:
    if db.info.get("tenant_domain_guard"):
        for record in db.new | db.dirty | db.deleted:
            tenant_id = getattr(record, "tenant_id", None)
            if tenant_id is not None:
                bind_domain_owner(db, tenant_id)


@event.listens_for(Session, "before_commit")
def _revalidate_domain_commit(db: Session) -> None:
    if not db.info.get("tenant_domain_guard"):
        return
    # Flush conserva as mudanças na transação; qualquer recusa ainda faz rollback.
    # before_flush registra também owners de alterações flushadas anteriormente.
    db.flush()
    with db.no_autoflush:
        for tenant_id in db.info.get("tenant_domain_owners", ()):
            status = db.scalar(select(Tenant.status).where(Tenant.id == tenant_id))
            financial = tenant_id in db.info.get("tenant_financial_reconciliation", ())
            if status != "active" and not (status == "suspended" and financial):
                raise TenantContextError("Contexto do fotógrafo indisponível.")
            lifecycle = db.scalar(select(Tenant.lifecycle).where(Tenant.id == tenant_id))
            platform_identity = tenant_id in db.info.get("tenant_platform_identity", ())
            privacy_retention = tenant_id in db.info.get("tenant_privacy_retention", ())
            closure_transition = tenant_id in db.info.get("tenant_closure_transition", ())
            archive_recovery = tenant_id in db.info.get("tenant_archive_recovery", ())
            if lifecycle == "closed" and not any((financial, platform_identity, privacy_retention, closure_transition, archive_recovery)):
                raise TenantContextError("Contexto do fotógrafo indisponível.")
        for admin_id, tenant_id in db.info.get("tenant_domain_admins", {}).items():
            memberships = list(db.scalars(select(TenantAdmin.tenant_id).where(
                TenantAdmin.admin_user_id == admin_id, TenantAdmin.active.is_(True),
            ).limit(2)))
            if memberships != [tenant_id]:
                raise TenantContextError("Acesso negado.")


@event.listens_for(Session, "after_transaction_end")
def _clear_domain_context(db: Session, transaction) -> None:
    if transaction.parent is None:
        db.info.pop("tenant_domain_owners", None)
        db.info.pop("tenant_domain_admins", None)
        db.info.pop("tenant_financial_reconciliation", None)
        db.info.pop("tenant_platform_identity", None)
        db.info.pop("tenant_privacy_retention", None)
        db.info.pop("tenant_closure_transition", None)
        db.info.pop("tenant_archive_recovery", None)
