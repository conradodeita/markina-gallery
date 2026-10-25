"""Meios efetivos da própria conta, sem consulta ou cobrança externa."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import require_active_owner
from app.auth import ParentGallery, PhotoFolder, Tenant
from app.global_pix import checkout_pix
from app.pix import PixCodeError

PAYMENT_REQUIRED_MESSAGE = (
    "Pagamento obrigatório exige um meio de pagamento configurado na sua conta. "
    "Configure PIX ou Mercado Pago em Configurações ou desmarque Pagamento obrigatório."
)


def lock_payment_account(db: Session, tenant_id: UUID) -> None:
    require_active_owner(db, tenant_id)
    db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update()
              .execution_options(populate_existing=True))


def payment_methods(db: Session, *, tenant_id: UUID, client_id: UUID | None = None) -> dict:
    require_active_owner(db, tenant_id)
    try:
        checkout_pix(db, tenant_id=tenant_id)
        pix_available = True
    except PixCodeError:
        pix_available = False
    from app.mercadopago_settings import effective_mercadopago

    card_available = effective_mercadopago(db, tenant_id, client_id=client_id) is not None
    return {
        "pix_available": pix_available,
        "card_available": card_available,
        "available": pix_available or card_available,
        "default_method": "pix" if pix_available else "mercadopago" if card_available else None,
    }


def require_payment_method(db: Session, *, tenant_id: UUID, status_code: int = 409) -> None:
    if not payment_methods(db, tenant_id=tenant_id)["available"]:
        raise HTTPException(status_code=status_code, detail=PAYMENT_REQUIRED_MESSAGE)


def can_publish_gallery(db: Session, gallery: ParentGallery) -> bool:
    return not gallery.payment_required or payment_methods(db, tenant_id=gallery.tenant_id)["available"]


def has_published_paid_gallery(db: Session, tenant_id: UUID) -> bool:
    return db.scalar(select(ParentGallery.id).where(
        ParentGallery.tenant_id == tenant_id,
        ParentGallery.lifecycle_status.in_(("active", "deleting")),
        ParentGallery.active,
        ParentGallery.payment_required,
        select(PhotoFolder.id).where(
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.parent_gallery_id == ParentGallery.id,
            PhotoFolder.purpose == "content",
            PhotoFolder.status == "released",
        ).exists(),
    ).limit(1)) is not None
