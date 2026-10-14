"""Consultas explícitas do acervo; UUID e storage key nunca escolhem uma conta."""

from pathlib import PurePosixPath
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Client, Tenant


def require_active_owner(db: Session, tenant_id: UUID) -> None:
    tenant = db.get(Tenant, tenant_id, populate_existing=True)
    if tenant is None or tenant.status != "active":
        raise HTTPException(status_code=403, detail="Acesso negado.")
    from app.tenancy import bind_domain_owner

    bind_domain_owner(db, tenant_id)


def owned_record(db: Session, model, resource_id: UUID, *, tenant_id: UUID):
    """Nenhum fallback: o chamador fornece owner autenticado antes da consulta."""
    require_active_owner(db, tenant_id)
    return db.scalar(select(model).where(
        model.id == resource_id, model.tenant_id == tenant_id,
    ).execution_options(populate_existing=True))


def client_tenant_id(db: Session, client_id: UUID) -> UUID:
    """Owner do cadastro confiável recebido pelo serviço, nunca do telefone."""
    client = db.get(Client, client_id, populate_existing=True)
    if client is None:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    require_active_owner(db, client.tenant_id)
    return client.tenant_id


def namespaced_upload_key(key: str, *, tenant_id: UUID, parent_id: UUID,
                          folder_id: UUID, gallery_id: UUID | None = None) -> str:
    """Mantém a chave lógica do uploader e cria namespace somente no servidor."""
    path = PurePosixPath(key)
    prefix = f"private/{gallery_id}/" if gallery_id else f"{parent_id}/{folder_id}/"
    if ("\\" in key or path.is_absolute() or any(part in {".", ".."} for part in key.split("/"))
            or not key.startswith(prefix) or not path.name or len(key) > 950):
        raise HTTPException(status_code=422, detail="Chave de armazenamento inválida para esta pasta.")
    if gallery_id and not key.startswith(f"{prefix}{folder_id}/"):
        raise HTTPException(status_code=422, detail="Chave de armazenamento inválida para esta pasta.")
    return f"tenants/{tenant_id}/{key}"


def logical_upload_key(key: str, tenant_id: UUID) -> str:
    prefix = f"tenants/{tenant_id}/"
    return key.removeprefix(prefix)
