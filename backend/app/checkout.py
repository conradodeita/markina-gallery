"""Criação transacional e imutável de pedidos PIX manuais."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    DerivedGallery,
    DerivedGalleryPhoto,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    SaleOrder,
    SaleOrderItem,
    audit,
)
from app.gallery_pricing import GalleryPricingError, quote_parent_gallery
from app.global_pix import checkout_pix
from app.pix import PixCodeError


class CheckoutError(ValueError):
    pass


def create_pending_checkout(
    db: Session, *, gallery: DerivedGallery, client: Client, checkout_key: str
) -> SaleOrder:
    """Cria um pedido pendente a partir da seleção própria dentro da transação da rota."""
    existing = db.scalar(
        select(SaleOrder).where(
            SaleOrder.derived_gallery_id == gallery.id,
            SaleOrder.client_id == client.id,
            SaleOrder.checkout_key == checkout_key,
        )
    )
    if existing:
        return existing

    selections = list(
        db.scalars(
            select(PhotoSelection)
            .where(
                PhotoSelection.derived_gallery_id == gallery.id,
                PhotoSelection.client_id == client.id,
            )
            .with_for_update()
        )
    )
    if not selections:
        raise CheckoutError("A seleção está vazia.")
    photo_ids = {selection.photo_asset_id for selection in selections}
    referenced_photo_ids = select(DerivedGalleryPhoto.photo_asset_id).where(
        DerivedGalleryPhoto.derived_gallery_id == gallery.id
    )
    photos = list(
        db.scalars(
            select(PhotoAsset)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                PhotoAsset.id.in_(photo_ids),
                (PhotoAsset.derived_gallery_id == gallery.id)
                | (PhotoAsset.id.in_(referenced_photo_ids)),
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
            )
            .distinct()
        )
    )
    if {photo.id for photo in photos} != photo_ids:
        raise CheckoutError("A seleção contém fotos indisponíveis.")
    already_confirmed = db.scalar(
        select(SaleOrderItem.id)
        .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
        .where(
            SaleOrder.derived_gallery_id == gallery.id,
            SaleOrder.client_id == client.id,
            SaleOrder.payment_status == "confirmed",
            SaleOrderItem.photo_asset_id.in_(photo_ids),
        )
    )
    if already_confirmed:
        raise CheckoutError("A seleção contém fotos já confirmadas para esta cliente.")
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    if not parent:
        raise CheckoutError("A Galeria pública desta seleção não está disponível.")
    try:
        commercial_quote = quote_parent_gallery(db, gallery=parent, quantity=len(photos))
    except GalleryPricingError as exc:
        raise CheckoutError(str(exc)) from exc
    try:
        settings = checkout_pix(db)
    except PixCodeError as exc:
        raise CheckoutError(str(exc)) from exc
    order = SaleOrder(
        derived_gallery_id=gallery.id,
        client_id=client.id,
        payment_status="pending",
        total_cents=commercial_quote.quote.total_cents,
        client_name_snapshot=client.full_name,
        client_phone_snapshot=client.phone_e164,
        checkout_key=checkout_key,
        price_rule_snapshot={
            **commercial_quote.snapshot,
            "terms": {
                "payment_confirmation": "manual_by_photographer",
                "selection_expires_at": (
                    gallery.selection_expires_at.isoformat()
                    if gallery.selection_expires_at
                    else None
                ),
            },
        },
        sales_message_snapshot=parent.sales_message,
        pix_copy_paste_snapshot=settings.copy_paste,
        pix_qr_code_snapshot=None,
        pix_instructions_snapshot=settings.instructions,
        pix_configuration_snapshot={
            "configuration_id": str(settings.id), "version": settings.version,
            "receiver_name": settings.receiver_name, "receiver_city": settings.receiver_city,
        },
    )
    db.add(order)
    db.flush()
    unit_prices = [
        parcel.unit_price_cents
        for parcel in commercial_quote.quote.parcels
        for _ in range(parcel.quantity)
    ]
    folders_by_id = {
        folder.id: folder
        for folder in db.scalars(
            select(PhotoFolder).where(
                PhotoFolder.id.in_({photo.folder_id for photo in photos})
            )
        )
    }
    for photo, unit_price_cents in zip(
        sorted(photos, key=lambda item: str(item.id)), unit_prices, strict=True
    ):
        folder = folders_by_id.get(photo.folder_id)
        db.add(
            SaleOrderItem(
                sale_order_id=order.id,
                photo_asset_id=photo.id,
                filename_snapshot=photo.display_name or photo.filename,
                folder_id_snapshot=folder.id if folder else None,
                folder_name_snapshot=folder.name if folder else None,
                unit_price_cents=unit_price_cents,
            )
        )
    db.execute(
        delete(PhotoSelection).where(
            PhotoSelection.id.in_([selection.id for selection in selections])
        )
    )
    audit(db, "sale_order.pending_created", str(order.id))
    return order
