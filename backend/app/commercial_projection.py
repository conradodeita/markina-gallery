"""Projeção comercial autoritativa compartilhada pelas superfícies administrativas."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    DerivedGallery,
    DerivedGalleryPhoto,
    GalleryReopeningRequest,
    PaymentCommunication,
    PhotoAsset,
    PhotoSelection,
    SaleOrder,
    SaleOrderItem,
    expired,
)


@dataclass(frozen=True)
class CommercialProjection:
    gallery_id: UUID
    client_id: UUID
    available_count: int = 0
    selected_count: int = 0
    purchased_count: int = 0
    order_count: int = 0
    confirmed_total_cents: int = 0
    commercial_status: str = "no_order"
    reopening_status: str | None = None
    financial_orders: list[dict[str, object]] = field(default_factory=list)

    def payload(self) -> dict[str, object]:
        return asdict(self)


def payment_capabilities(communication_status: str | None, payment_status: str) -> dict[str, bool]:
    """Mesmos gates para Vendas e pagamentos e atalhos, nunca pelo agregado da cliente."""
    return {
        "can_decide": communication_status == "pending_review" and payment_status == "pending",
        "can_correct": communication_status == "confirmed" and payment_status == "confirmed",
    }


def build_commercial_projections(
    db: Session,
    *,
    gallery_ids: set[UUID],
    client_ids: set[UUID],
    parent_gallery_ids: set[UUID] | None = None,
    galleries_by_id: dict[UUID, DerivedGallery] | None = None,
) -> dict[tuple[UUID, UUID], CommercialProjection]:
    """Calcula todos os agregados por galeria/cliente em consultas de lote constantes."""

    parent_gallery_ids = parent_gallery_ids or set()
    if not (gallery_ids or parent_gallery_ids) or not client_ids:
        return {}
    galleries = galleries_by_id or {
        item.id: item
        for item in db.scalars(select(DerivedGallery).where(DerivedGallery.id.in_(gallery_ids)))
    }
    available_photo_ids: dict[UUID, set[UUID]] = defaultdict(set)
    available_query = select(
        DerivedGalleryPhoto.derived_gallery_id.label("gallery_id"),
        DerivedGalleryPhoto.photo_asset_id.label("photo_id"),
    ).where(DerivedGalleryPhoto.derived_gallery_id.in_(gallery_ids)).union_all(
        select(
            PhotoAsset.derived_gallery_id.label("gallery_id"),
            PhotoAsset.id.label("photo_id"),
        ).where(PhotoAsset.derived_gallery_id.in_(gallery_ids))
    )
    for gallery_id, photo_id in db.execute(available_query):
        available_photo_ids[gallery_id].add(photo_id)
    selected_photo_ids: dict[tuple[UUID, UUID], set[UUID]] = defaultdict(set)
    for gallery_id, client_id, photo_id in db.execute(
            select(
                PhotoSelection.derived_gallery_id,
                PhotoSelection.client_id,
                PhotoSelection.photo_asset_id,
            )
            .where(
                PhotoSelection.derived_gallery_id.in_(gallery_ids),
                PhotoSelection.client_id.in_(client_ids),
            )
    ):
        selected_photo_ids[(gallery_id, client_id)].add(photo_id)
    raw_order_rows = list(
        db.execute(
            select(
                SaleOrder.id,
                SaleOrder.derived_gallery_id_snapshot,
                SaleOrder.parent_gallery_id_snapshot,
                SaleOrder.client_id,
                SaleOrder.payment_status,
                SaleOrder.frozen_at,
                SaleOrder.checkout_key,
                SaleOrder.total_cents,
                SaleOrder.created_at,
                SaleOrder.derived_gallery_name_snapshot,
                PaymentCommunication.id.label("communication_id"),
                PaymentCommunication.created_at.label("communicated_at"),
                PaymentCommunication.status.label("communication_status"),
                SaleOrderItem.id.label("item_id"),
                SaleOrderItem.photo_asset_id_snapshot,
            )
            .outerjoin(
                PaymentCommunication,
                PaymentCommunication.sale_order_id == SaleOrder.id,
            )
            .outerjoin(SaleOrderItem, SaleOrderItem.sale_order_id == SaleOrder.id)
            .where(
                (SaleOrder.derived_gallery_id_snapshot.in_(gallery_ids))
                | (SaleOrder.parent_gallery_id_snapshot.in_(parent_gallery_ids)),
                SaleOrder.client_id.in_(client_ids),
            )
            .order_by(PaymentCommunication.created_at.desc(), PaymentCommunication.id.desc())
        )
    )
    order_rows = {}
    purchased_photo_ids: dict[tuple[UUID, UUID], set[UUID]] = defaultdict(set)
    pending_review_order_ids: set[UUID] = set()
    item_ids_by_order: dict[UUID, set[UUID]] = defaultdict(set)
    for row in raw_order_rows:
        if (
            row.payment_status == "pending"
            and row.frozen_at is None
            and row.checkout_key is not None
        ):
            continue
        order_rows.setdefault(row.id, row)
        if row.item_id:
            item_ids_by_order[row.id].add(row.item_id)
        if row.communication_status == "pending_review":
            pending_review_order_ids.add(row.id)
        if row.payment_status == "confirmed" and row.photo_asset_id_snapshot:
            purchased_photo_ids[
                (row.derived_gallery_id_snapshot, row.client_id)
            ].add(row.photo_asset_id_snapshot)
        elif (
            row.payment_status == "pending"
            and row.frozen_at is not None
            and row.photo_asset_id_snapshot
        ):
            selected_photo_ids[
                (row.derived_gallery_id_snapshot, row.client_id)
            ].add(row.photo_asset_id_snapshot)
    latest_reopening: dict[UUID, GalleryReopeningRequest] = {}
    for item in db.scalars(
        select(GalleryReopeningRequest)
        .where(GalleryReopeningRequest.derived_gallery_id.in_(gallery_ids))
        .order_by(
            GalleryReopeningRequest.created_at.desc(),
            GalleryReopeningRequest.id.desc(),
        )
    ):
        latest_reopening.setdefault(item.derived_gallery_id, item)

    orders_by_key: dict[tuple[UUID, UUID], list[object]] = defaultdict(list)
    for row in order_rows.values():
        orders_by_key[(row.derived_gallery_id_snapshot, row.client_id)].append(row)
    projections: dict[tuple[UUID, UUID], CommercialProjection] = {}
    projection_gallery_ids = set(galleries) | {
        row.derived_gallery_id_snapshot for row in order_rows.values()
    }
    for gallery_id in projection_gallery_ids:
        gallery = galleries.get(gallery_id)
        available_count = len(available_photo_ids.get(gallery_id, set()))
        for client_id in client_ids:
            key = (gallery_id, client_id)
            orders = orders_by_key.get(key, [])
            statuses = {row.payment_status for row in orders}
            reported = any(row.id in pending_review_order_ids for row in orders)
            if reported:
                commercial_status = "pending_review"
            elif "pending" in statuses:
                commercial_status = "awaiting_payment"
            elif "confirmed" in statuses:
                commercial_status = "paid"
            elif gallery and gallery.selection_expires_at and expired(gallery.selection_expires_at):
                commercial_status = "overdue"
            elif "cancelled" in statuses:
                commercial_status = "cancelled"
            else:
                commercial_status = "no_order"
            reopening = latest_reopening.get(gallery_id)
            projections[key] = CommercialProjection(
                gallery_id=gallery_id,
                client_id=client_id,
                available_count=available_count,
                selected_count=len(
                    selected_photo_ids.get(key, set())
                    - purchased_photo_ids.get(key, set())
                ),
                purchased_count=len(purchased_photo_ids.get(key, set())),
                order_count=len(orders),
                confirmed_total_cents=sum(
                    row.total_cents for row in orders if row.payment_status == "confirmed"
                ),
                commercial_status=commercial_status,
                reopening_status=reopening.status if reopening else None,
                financial_orders=[
                    {
                        "order_id": str(row.id),
                        "id": str(row.communication_id),
                        "gallery_name": row.derived_gallery_name_snapshot,
                        "total_cents": row.total_cents,
                        "quantity": len(item_ids_by_order[row.id]),
                        "created_at": row.communicated_at.isoformat(),
                        "status": row.communication_status,
                        **payment_capabilities(row.communication_status, row.payment_status),
                    }
                    for row in sorted(
                        orders,
                        key=lambda row: (
                            row.communication_status == "pending_review",
                            row.created_at,
                            str(row.id),
                        ),
                        reverse=True,
                    )
                    if row.communication_id
                ],
            )
    return projections
