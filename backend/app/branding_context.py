"""Marca comercial pelo contexto autorizado; entrada genérica usa apenas o produto."""

from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
from app.auth import BrandingSettings, DerivedGallery, ParentGallery, Tenant, current_session
from app.gallery_access import resolve_gallery_capability


def branding_tenant_id(db: Session, request: Request, access_token: str | None) -> UUID | None:
    if access_token is not None:
        capability = resolve_gallery_capability(db, access_token)
        if capability is None:
            return None
        try:
            parent = owned_record(db, ParentGallery, capability.parent_gallery_id,
                                  tenant_id=capability.tenant_id)
            if not parent or not parent.active or parent.lifecycle_status != "active":
                return None
            if capability.derived_gallery_id:
                gallery = owned_record(db, DerivedGallery, capability.derived_gallery_id,
                                       tenant_id=capability.tenant_id)
                if not gallery or not gallery.access_enabled:
                    return None
        except HTTPException:
            return None
        return capability.tenant_id
    try:
        session = current_session(request)
        require_active_owner(db, session.tenant_id)
        return session.tenant_id
    except HTTPException:
        return None


def branding_settings(db: Session, *, tenant_id: UUID, create: bool = False) -> BrandingSettings | None:
    require_active_owner(db, tenant_id)
    if create:
        db.scalar(select(Tenant.id).where(Tenant.id == tenant_id).with_for_update())
        require_active_owner(db, tenant_id)
    settings = db.scalar(select(BrandingSettings).where(
        BrandingSettings.tenant_id == tenant_id,
    ).execution_options(populate_existing=True))
    if settings is None and create:
        settings = BrandingSettings(tenant_id=tenant_id)
        db.add(settings)
        db.flush()
    return settings


def technical_branding() -> dict:
    return {"login_title": "Sua galeria, do seu jeito.",
            "login_intro": "Entre para acessar fotos, seleções e entregas — ou gerenciar sua operação.",
            "login_helper": "Escolha seu tipo de acesso para continuar.",
            "logo_url": None, "app_icon_url": None, "favicon_url": None}
