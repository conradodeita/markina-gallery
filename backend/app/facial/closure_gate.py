"""Barreira tenant-scoped entre o encerramento e novas operações faciais."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Tenant, TenantClosureRequest


class FacialCleanupInProgress(RuntimeError):
    """O tenant está encerrando ou a limpeza biométrica já começou."""


def lock_facial_tenant(
    db: Session, tenant_id: UUID, *, skip_locked: bool = False
) -> Tenant | None:
    """Usa a mesma ordem de lock do fechamento: tenant antes das filas faciais."""

    query = select(Tenant).where(Tenant.id == tenant_id)
    if skip_locked:
        query = query.with_for_update(skip_locked=True)
    else:
        query = query.with_for_update()
    return db.scalar(query.execution_options(populate_existing=True))


def biometric_cleanup_started(db: Session, tenant_id: UUID) -> bool:
    return db.scalar(
        select(TenantClosureRequest.id).where(
            TenantClosureRequest.tenant_id == tenant_id,
            TenantClosureRequest.state == "closing",
            TenantClosureRequest.biometric_cleanup_started_at.is_not(None),
        ).limit(1)
    ) is not None


def require_facial_mutation_allowed(db: Session, tenant_id: UUID) -> Tenant:
    """Admite novas buscas e mudanças de política somente em tenants abertos."""

    tenant = lock_facial_tenant(db, tenant_id)
    if (
        tenant is None
        or tenant.status != "active"
        or tenant.lifecycle != "open"
        or biometric_cleanup_started(db, tenant_id)
    ):
        raise FacialCleanupInProgress("Operação facial indisponível durante o encerramento.")
    return tenant


def require_facial_queue_write_allowed(db: Session, tenant_id: UUID) -> Tenant:
    """Permite concluir/enfileirar trabalho existente até começar a limpeza."""

    tenant = lock_facial_tenant(db, tenant_id)
    if (
        tenant is None
        or tenant.status != "active"
        or tenant.lifecycle == "closed"
        or biometric_cleanup_started(db, tenant_id)
    ):
        raise FacialCleanupInProgress("Fila facial indisponível durante o encerramento.")
    return tenant
