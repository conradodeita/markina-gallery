"""Projeção comercial única para as superfícies da cliente."""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.acervo_context import client_tenant_id, require_active_owner
from app.auth import (
    DerivedGallery,
    ParentGallery,
    PaymentCommunication,
    PaymentNotificationOutbox,
    PhotoSelection,
    PriceRule,
    SaleOrder,
    SaleOrderItem,
    now,
)
from app.folder_access import (
    folder_media_access_by_id,
    folder_selected_media_preview_allowed,
    photos_with_folder_media_access_by_id,
)
from app.gallery_pricing import GalleryPricingError, quote_loaded_gallery
from app.order_delivery import order_fulfillable
from app.unified_checkout import communication_join, communications_for_orders


def client_carts_by_gallery_payload(
    db: Session, *, galleries: list[DerivedGallery], client_id: UUID
) -> dict[UUID, dict[str, object]]:
    """Projeta carrinhos e rascunhos de várias galerias com consultas constantes."""
    tenant_id = client_tenant_id(db, client_id)

    if any(gallery.tenant_id != tenant_id for gallery in galleries):
        raise ValueError("Galeria indisponível neste contexto.")

    gallery_by_id = {gallery.id: gallery for gallery in galleries}
    result: dict[UUID, dict[str, object]] = {
        gallery_id: {"quantity": 0, "items": [], "draft_order_id": None}
        for gallery_id in gallery_by_id
    }
    if not gallery_by_id:
        return result
    gallery_ids = set(gallery_by_id)
    selections_by_gallery: dict[UUID, list[PhotoSelection]] = defaultdict(list)
    selection_rows = list(
        db.scalars(
            select(PhotoSelection).where(PhotoSelection.tenant_id == tenant_id).where(
                PhotoSelection.derived_gallery_id.in_(gallery_ids),
                PhotoSelection.client_id == client_id,
            )
        )
    )
    for selection in selection_rows:
        selections_by_gallery[selection.derived_gallery_id].append(selection)
    drafts_by_gallery = {
        draft.derived_gallery_id: draft
        for draft in db.scalars(
            select(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(
                SaleOrder.derived_gallery_id.in_(gallery_ids),
                SaleOrder.client_id == client_id,
                SaleOrder.payment_status == "pending",
                SaleOrder.frozen_at.is_(None),
                SaleOrder.assets_removed_at.is_(None),
                SaleOrder.checkout_key.is_not(None),
            )
        )
    }
    draft_items: dict[UUID, set[UUID]] = defaultdict(set)
    if drafts_by_gallery:
        for order_id, photo_id in db.execute(
            select(SaleOrderItem.sale_order_id, SaleOrderItem.photo_asset_id_snapshot).where(SaleOrderItem.tenant_id == tenant_id).where(
                SaleOrderItem.sale_order_id.in_(
                    [draft.id for draft in drafts_by_gallery.values()]
                )
            )
        ):
            draft_items[order_id].add(photo_id)

    photo_ids = {selection.photo_asset_id for selection in selection_rows}
    photos_with_access = photos_with_folder_media_access_by_id(
        db,
        photo_ids=photo_ids,
        tenant_id=tenant_id,
        client_id=client_id,
    )
    photos = {
        photo_id: access[0] for photo_id, access in photos_with_access.items()
    }
    photo_media_states = {
        photo_id: access[1] for photo_id, access in photos_with_access.items()
    }
    photo_expiries = {
        photo_id: access[2] for photo_id, access in photos_with_access.items()
    }
    parent_ids = {gallery.parent_gallery_id for gallery in galleries}
    parents = {
        parent.id: parent
        for parent in db.scalars(select(ParentGallery).where(ParentGallery.tenant_id == tenant_id).where(ParentGallery.id.in_(parent_ids)))
    }
    rules_by_parent: dict[UUID, list[PriceRule]] = defaultdict(list)
    for rule in db.scalars(
        select(PriceRule).where(PriceRule.tenant_id == tenant_id)
        .where(PriceRule.parent_gallery_id.in_(parent_ids))
        .order_by(PriceRule.parent_gallery_id, PriceRule.minimum_quantity)
    ):
        rules_by_parent[rule.parent_gallery_id].append(rule)

    for gallery_id, gallery in gallery_by_id.items():
        selections = selections_by_gallery[gallery_id]
        payload = result[gallery_id]
        payload["quantity"] = len(selections)
        selected_photo_ids = {selection.photo_asset_id for selection in selections}
        draft = drafts_by_gallery.get(gallery_id)
        if draft and selected_photo_ids and draft_items[draft.id] == selected_photo_ids:
            payload["draft_order_id"] = str(draft.id)
        payload["items"] = []
        current_time = now()
        for selection in selections:
            photo = photos.get(selection.photo_asset_id)
            if not photo:
                continue
            media_state = photo_media_states.get(photo.id, "unavailable")
            expiry = photo_expiries.get(photo.id)
            preview_available = photo.available and folder_selected_media_preview_allowed(
                media_state=media_state,
                expiry=expiry,
                selected_at=selection.created_at,
                at=current_time,
            )
            payload["items"].append(
                {
                    "id": str(selection.photo_asset_id),
                    "name": photo.display_name or photo.filename,
                    "media_state": media_state,
                    "preview_url": (
                        f"/gallery/{gallery.id}/photos/{selection.photo_asset_id}/preview"
                        if preview_available else None
                    ),
                }
            )
        if not selections:
            continue
        parent = parents.get(gallery.parent_gallery_id)
        if not parent:
            continue
        payload["payment_required"] = parent.payment_required
        if not parent.payment_required:
            continue
        try:
            commercial_quote = quote_loaded_gallery(
                gallery=parent,
                quantity=len(selections),
                rules=rules_by_parent[parent.id],
            )
        except GalleryPricingError as exc:
            payload["pricing_error"] = str(exc)
            continue
        payload.update(
            {
                "unit_price_cents": commercial_quote.quote.active_tier.unit_price_cents,
                "total_cents": commercial_quote.quote.total_cents,
                "base_total_cents": commercial_quote.quote.base_total_cents,
                "savings_cents": commercial_quote.quote.savings_cents,
                "parcels": commercial_quote.snapshot["parcels"],
                "pricing_mode": parent.pricing_mode,
                "tier": {
                    "minimum_quantity": commercial_quote.quote.active_tier.minimum_quantity,
                    "maximum_quantity": commercial_quote.quote.active_tier.maximum_quantity,
                },
            }
        )
    require_active_owner(db, tenant_id)
    return result


def client_photo_states(
    db: Session, *, gallery_id: UUID | None, client_id: UUID,
    photo_ids: set[UUID], parent_gallery_id: UUID | None = None
) -> dict[UUID, str]:
    """Resolve estados por prioridade sem consultas por foto."""
    tenant_id = client_tenant_id(db, client_id)

    states = {photo_id: "available" for photo_id in photo_ids}
    if not photo_ids:
        return states
    selected = set(
        db.scalars(
            select(PhotoSelection.photo_asset_id).where(PhotoSelection.tenant_id == tenant_id).where(
                or_(
                    PhotoSelection.derived_gallery_id == gallery_id,
                    PhotoSelection.parent_gallery_id == parent_gallery_id,
                ) if parent_gallery_id else PhotoSelection.derived_gallery_id == gallery_id,
                PhotoSelection.client_id == client_id,
                PhotoSelection.photo_asset_id.in_(photo_ids),
            )
        )
    )
    for photo_id in selected:
        states[photo_id] = "selected"

    rows = list(
        db.execute(
            select(
                SaleOrderItem.photo_asset_id_snapshot,
                SaleOrder.payment_status,
                SaleOrder.frozen_at,
                PaymentCommunication.status,
            ).where(or_(PaymentCommunication.id.is_(None), PaymentCommunication.tenant_id == tenant_id), SaleOrder.tenant_id == tenant_id, SaleOrderItem.tenant_id == tenant_id)
            .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
            .outerjoin(PaymentCommunication, communication_join())
            .where(
                or_(
                    SaleOrder.derived_gallery_id_snapshot == gallery_id,
                    SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
                ) if parent_gallery_id else SaleOrder.derived_gallery_id_snapshot == gallery_id,
                SaleOrder.client_id == client_id,
                SaleOrderItem.photo_asset_id_snapshot.in_(photo_ids),
            )
        )
    )
    for photo_id, payment_status, frozen_at, communication_status in rows:
        if payment_status == "not_required" and frozen_at:
            states[photo_id] = "selection_finalized"
        elif payment_status == "confirmed":
            states[photo_id] = "purchased"
        elif (
            payment_status == "pending"
            and frozen_at is not None
            and communication_status in {"pending_review", "confirmed"}
            and states[photo_id] != "purchased"
        ):
            states[photo_id] = "payment_reported"
        elif (
            payment_status == "pending"
            and frozen_at is not None
            and states[photo_id] not in {"purchased", "payment_reported"}
        ):
            states[photo_id] = "awaiting_payment"
    return states


def client_orders_by_gallery_payload(
    db: Session, *, gallery_ids: set[UUID], client_id: UUID
) -> dict[UUID, list[dict[str, object]]]:
    """Entrega pedidos agrupados por galeria com custo fixo de consultas."""
    tenant_id = client_tenant_id(db, client_id)

    grouped: dict[UUID, list[dict[str, object]]] = {
        gallery_id: [] for gallery_id in gallery_ids
    }
    if not gallery_ids:
        return grouped
    orders = list(
        db.scalars(
            select(SaleOrder).where(SaleOrder.tenant_id == tenant_id)
            .where(
                SaleOrder.derived_gallery_id_snapshot.in_(gallery_ids),
                SaleOrder.client_id == client_id,
                or_(
                    SaleOrder.frozen_at.is_not(None),
                    SaleOrder.payment_status == "confirmed",
                ),
            )
            .order_by(SaleOrder.created_at.desc())
        )
    )
    if not orders:
        return grouped
    order_ids = [order.id for order in orders]
    items_by_order: dict[UUID, list[SaleOrderItem]] = defaultdict(list)
    for item in db.scalars(
        select(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id)
        .where(SaleOrderItem.sale_order_id.in_(order_ids))
        .order_by(SaleOrderItem.filename_snapshot)
    ):
        items_by_order[item.sale_order_id].append(item)
    folder_access = folder_media_access_by_id(
        db,
        folder_ids={
            item.folder_id_snapshot
            for items in items_by_order.values()
            for item in items
            if item.folder_id_snapshot
        },
        tenant_id=tenant_id,
        client_id=client_id,
    )
    media_states = {
        folder_id: access[0] for folder_id, access in folder_access.items()
    }
    folder_expiries = {
        folder_id: access[1] for folder_id, access in folder_access.items()
    }
    current_time = now()
    communications = communications_for_orders(db, orders)
    communication_ids = [communication.id for communication in communications.values()]
    deliveries: dict[UUID, PaymentNotificationOutbox] = {}
    if communication_ids:
        for delivery in db.scalars(
            select(PaymentNotificationOutbox).where(PaymentNotificationOutbox.tenant_id == tenant_id)
            .where(
                PaymentNotificationOutbox.payment_communication_id.in_(communication_ids),
                PaymentNotificationOutbox.template_kind.in_(("confirmed", "refused")),
            )
            .order_by(PaymentNotificationOutbox.created_at)
        ):
            deliveries[delivery.payment_communication_id] = delivery

    for order in orders:
        communication = communications.get(order.id)
        delivery = deliveries.get(communication.id) if communication else None
        order_open = (
            order.payment_status == "pending" and order.frozen_at is not None
        ) or (order_fulfillable(order) and order.delivery_album_url is None)
        state = (
            "selection_finalized"
            if order.payment_status == "not_required"
            else "purchased"
            if order.payment_status == "confirmed"
            else "cancelled"
            if order.payment_status == "cancelled"
            else "payment_reported"
            if communication and communication.status in {"pending_review", "confirmed"}
            else "awaiting_payment"
            if order.frozen_at is not None
            else "draft"
        )
        gallery_id = order.derived_gallery_id_snapshot
        grouped[gallery_id].append(
            {
                "order_id": str(order.id),
                "payment_group_id": str(order.payment_group_id) if order.payment_group_id else None,
                "total_cents": order.total_cents if order.payment_required_snapshot else None,
                **({"payment_required": False} if not order.payment_required_snapshot else {}),
                "payment_status": order.payment_status,
                "commercial_state": state,
                "frozen_at": order.frozen_at.isoformat() if order.frozen_at else None,
                "created_at": order.created_at.isoformat(),
                "communication": (
                    {
                        "id": str(communication.id),
                        "status": communication.status,
                        "created_at": communication.created_at.isoformat(),
                        "decided_at": communication.decided_at.isoformat()
                        if communication.decided_at
                        else None,
                    }
                    if communication
                    else None
                ),
                "notification": (
                    {"status": delivery.status, "last_error": delivery.last_error}
                    if delivery
                    else None
                ),
                "items": [
                    {
                        "item_id": str(item.id),
                        "photo_id": str(item.photo_asset_id_snapshot),
                        "name": item.filename_snapshot,
                        "unit_price_cents": item.unit_price_cents if order.payment_required_snapshot else None,
                        "media_state": (
                            "available" if item.folder_id_snapshot is None
                            else media_states.get(item.folder_id_snapshot, "unavailable")
                        ),
                        "preview_url": (
                            f"/gallery/{gallery_id}/photos/{item.photo_asset_id_snapshot}/preview"
                            if item.photo_asset_id is not None and folder_selected_media_preview_allowed(
                                media_state=(
                                    "available" if item.folder_id_snapshot is None
                                    else media_states.get(item.folder_id_snapshot, "unavailable")
                                ),
                                expiry=folder_expiries.get(item.folder_id_snapshot),
                                selected_at=None,
                                existing_order_created_at=order.created_at,
                                existing_order_open=order_open,
                                at=current_time,
                            )
                            else None
                        ),
                    }
                    for item in items_by_order[order.id]
                ],
            }
        )
    return grouped


def client_orders_payload(
    db: Session, *, gallery_id: UUID, client_id: UUID
) -> list[dict[str, object]]:
    """Entrega os pedidos de uma galeria para retomada após login."""
    client_tenant_id(db, client_id)

    return client_orders_by_gallery_payload(
        db, gallery_ids={gallery_id}, client_id=client_id
    )[gallery_id]
