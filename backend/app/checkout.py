"""Criação transacional e imutável de pedidos PIX manuais."""

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    SaleOrder,
    SaleOrderItem,
    audit,
    now,
)
from app.gallery_pricing import GalleryPricingError, quote_parent_gallery
from app.global_pix import checkout_pix
from app.pix import PixCodeError


class CheckoutError(ValueError):
    pass


def lock_client_commerce(
    db: Session, *, gallery_id, client_id
) -> None:
    """Serializa seleção, checkout e congelamento sem bloquear outros membros."""

    membership = db.scalar(
        select(DerivedGalleryMembership)
        .where(
            DerivedGalleryMembership.derived_gallery_id == gallery_id,
            DerivedGalleryMembership.client_id == client_id,
        )
        .with_for_update()
    )
    if membership:
        return
    db.scalar(
        select(DerivedGallery.id)
        .where(DerivedGallery.id == gallery_id)
        .with_for_update()
    )


def client_photo_is_frozen(
    db: Session, *, gallery_id, client_id, photo_id
) -> bool:
    return bool(
        db.scalar(
            select(SaleOrderItem.id)
            .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
            .where(
                SaleOrder.derived_gallery_id_snapshot == gallery_id,
                SaleOrder.client_id == client_id,
                or_(
                    SaleOrder.payment_status == "confirmed",
                    and_(
                        SaleOrder.payment_status == "pending",
                        SaleOrder.frozen_at.is_not(None),
                    ),
                ),
                SaleOrderItem.photo_asset_id_snapshot == photo_id,
            )
        )
    )


def _checkout_material(
    db: Session, *, gallery: DerivedGallery, client: Client
):
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
    already_frozen = db.scalar(
        select(SaleOrderItem.id)
        .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
        .where(
            SaleOrder.derived_gallery_id_snapshot == gallery.id,
            SaleOrder.client_id == client.id,
            or_(
                SaleOrder.payment_status == "confirmed",
                and_(
                    SaleOrder.payment_status == "pending",
                    SaleOrder.frozen_at.is_not(None),
                ),
            ),
            SaleOrderItem.photo_asset_id_snapshot.in_(photo_ids),
        )
    )
    if already_frozen:
        raise CheckoutError("A seleção contém fotos de um pedido já congelado.")
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
    folders_by_id = {
        folder.id: folder
        for folder in db.scalars(
            select(PhotoFolder).where(
                PhotoFolder.id.in_({photo.folder_id for photo in photos})
            )
        )
    }
    return selections, photos, parent, commercial_quote, settings, folders_by_id


def _synchronize_order(
    db: Session,
    *,
    order: SaleOrder,
    gallery: DerivedGallery,
    client: Client,
    material,
) -> SaleOrder:
    _selections, photos, parent, commercial_quote, settings, folders_by_id = material
    order.derived_gallery_id = gallery.id
    order.client_id = client.id
    order.payment_status = "pending"
    order.total_cents = commercial_quote.quote.total_cents
    order.client_name_snapshot = client.full_name
    order.client_phone_snapshot = client.phone_e164
    order.price_rule_snapshot = {
        **commercial_quote.snapshot,
        "terms": {
            "payment_confirmation": "manual_by_photographer",
            "selection_expires_at": (
                gallery.selection_expires_at.isoformat()
                if gallery.selection_expires_at
                else None
            ),
        },
    }
    order.sales_message_snapshot = parent.sales_message
    order.pix_copy_paste_snapshot = settings.copy_paste
    order.pix_qr_code_snapshot = None
    order.pix_instructions_snapshot = settings.instructions
    order.pix_configuration_snapshot = {
        "configuration_id": str(settings.id),
        "version": settings.version,
        "receiver_name": settings.receiver_name,
        "receiver_city": settings.receiver_city,
    }
    db.add(order)
    db.flush()
    db.execute(delete(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id))
    unit_prices = [
        parcel.unit_price_cents
        for parcel in commercial_quote.quote.parcels
        for _ in range(parcel.quantity)
    ]
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
    db.flush()
    return order


def create_pending_checkout(
    db: Session, *, gallery: DerivedGallery, client: Client, checkout_key: str
) -> SaleOrder:
    """Cria ou sincroniza o rascunho sem consumir o carrinho da cliente."""
    lock_client_commerce(db, gallery_id=gallery.id, client_id=client.id)
    existing = db.scalar(
        select(SaleOrder).where(
            SaleOrder.derived_gallery_id == gallery.id,
            SaleOrder.client_id == client.id,
            SaleOrder.checkout_key == checkout_key,
        )
    )
    if existing and (
        existing.frozen_at is not None or existing.payment_status != "pending"
    ):
        return existing
    if existing is None:
        existing = db.scalar(
            select(SaleOrder)
            .where(
                SaleOrder.derived_gallery_id == gallery.id,
                SaleOrder.client_id == client.id,
                SaleOrder.payment_status == "pending",
                SaleOrder.frozen_at.is_(None),
                SaleOrder.checkout_key.is_not(None),
            )
            .order_by(SaleOrder.created_at.desc())
            .with_for_update()
        )
    material = _checkout_material(db, gallery=gallery, client=client)
    created = existing is None
    order = existing or SaleOrder(
        derived_gallery_id=gallery.id,
        client_id=client.id,
        payment_status="pending",
        total_cents=0,
        checkout_key=checkout_key,
    )
    _synchronize_order(
        db, order=order, gallery=gallery, client=client, material=material
    )
    audit(
        db,
        "sale_order.draft_created" if created else "sale_order.draft_updated",
        str(order.id),
    )
    return order


def synchronize_editable_draft(
    db: Session, *, gallery: DerivedGallery, client_id
) -> SaleOrder | None:
    """Mantém o rascunho alinhado à seleção após uma mutação do carrinho."""

    lock_client_commerce(db, gallery_id=gallery.id, client_id=client_id)
    order = db.scalar(
        select(SaleOrder)
        .where(
            SaleOrder.derived_gallery_id == gallery.id,
            SaleOrder.client_id == client_id,
            SaleOrder.payment_status == "pending",
            SaleOrder.frozen_at.is_(None),
            SaleOrder.checkout_key.is_not(None),
        )
        .with_for_update()
    )
    if not order:
        return None
    client = db.get(Client, client_id)
    if not client:
        return order
    has_selection = db.scalar(
        select(PhotoSelection.id).where(
            PhotoSelection.derived_gallery_id == gallery.id,
            PhotoSelection.client_id == client_id,
        )
    )
    if not has_selection:
        db.execute(delete(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id))
        db.delete(order)
        audit(db, "sale_order.draft_discarded", str(order.id))
        db.flush()
        return None
    try:
        material = _checkout_material(db, gallery=gallery, client=client)
    except CheckoutError:
        # O carrinho continua autoritativo e o rascunho divergente deixa de ser
        # oferecido pela projeção até um novo Prosseguir válido sincronizá-lo.
        return order
    _synchronize_order(
        db, order=order, gallery=gallery, client=client, material=material
    )
    audit(db, "sale_order.draft_updated", str(order.id))
    return order


def freeze_pending_checkout(
    db: Session, *, gallery: DerivedGallery, client: Client, order: SaleOrder
) -> SaleOrder:
    """Congela o retrato corrente quando a cliente comunica o pagamento."""

    lock_client_commerce(db, gallery_id=gallery.id, client_id=client.id)
    order = db.scalar(
        select(SaleOrder)
        .where(
            SaleOrder.id == order.id,
            SaleOrder.derived_gallery_id == gallery.id,
            SaleOrder.client_id == client.id,
        )
        .with_for_update()
    )
    if not order or order.payment_status != "pending":
        raise CheckoutError("Pedido indisponível para comunicação.")
    if order.frozen_at is not None:
        return order
    material = _checkout_material(db, gallery=gallery, client=client)
    selections = material[0]
    _synchronize_order(
        db, order=order, gallery=gallery, client=client, material=material
    )
    order.frozen_at = now()
    db.execute(
        delete(PhotoSelection).where(
            PhotoSelection.id.in_([selection.id for selection in selections])
        )
    )
    audit(db, "sale_order.payment_reported_frozen", str(order.id))
    return order
