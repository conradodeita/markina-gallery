"""Materialização idempotente e verificação do histórico comercial."""

from dataclasses import asdict, dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    CommercialHistoryMedia,
    DerivedGallery,
    ParentGallery,
    PhotoAsset,
    SaleOrder,
    SaleOrderItem,
)


@dataclass
class SnapshotBackfillReport:
    orders_scanned: int = 0
    orders_updated: int = 0
    items_scanned: int = 0
    items_updated: int = 0
    gaps: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class CommercialHistoryGap(RuntimeError):
    def __init__(self, report: SnapshotBackfillReport):
        self.report = report
        super().__init__("Existem lacunas que impedem preparar o histórico comercial.")


def materialize_commercial_history(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID | None = None,
    photo_asset_id: UUID | None = None,
) -> SnapshotBackfillReport:
    """Congela snapshots do alvo sem confirmar a transação da operação chamadora."""

    report = SnapshotBackfillReport()
    query = (
        select(SaleOrder)
        .where(SaleOrder.parent_gallery_id_snapshot == parent_gallery_id)
        .order_by(SaleOrder.created_at, SaleOrder.id)
        .with_for_update()
    )
    if client_id:
        query = query.where(SaleOrder.client_id == client_id)
    if photo_asset_id:
        query = query.join(
            SaleOrderItem, SaleOrderItem.sale_order_id == SaleOrder.id
        ).where(SaleOrderItem.photo_asset_id_snapshot == photo_asset_id)
    query = query.distinct()
    orders = list(db.scalars(query))
    order_ids = {order.id for order in orders}

    for order in orders:
        report.orders_scanned += 1
        before = (
            order.derived_gallery_id_snapshot,
            order.derived_gallery_name_snapshot,
            order.parent_gallery_id_snapshot,
            order.parent_gallery_name_snapshot,
            order.client_name_snapshot,
            order.client_phone_snapshot,
        )
        gallery = (
            db.get(DerivedGallery, order.derived_gallery_id)
            if order.derived_gallery_id
            else None
        )
        parent = db.get(ParentGallery, parent_gallery_id)
        client = db.get(Client, order.client_id)
        if gallery:
            order.derived_gallery_id_snapshot = (
                order.derived_gallery_id_snapshot or gallery.id
            )
            order.derived_gallery_name_snapshot = (
                order.derived_gallery_name_snapshot or gallery.name
            )
        if parent:
            order.parent_gallery_id_snapshot = (
                order.parent_gallery_id_snapshot or parent.id
            )
            order.parent_gallery_name_snapshot = (
                order.parent_gallery_name_snapshot or parent.name
            )
        if client:
            order.client_name_snapshot = order.client_name_snapshot or client.full_name
            order.client_phone_snapshot = (
                order.client_phone_snapshot or client.phone_e164
            )
        required = (
            order.derived_gallery_id_snapshot,
            order.derived_gallery_name_snapshot,
            order.parent_gallery_id_snapshot,
            order.parent_gallery_name_snapshot,
            order.client_name_snapshot,
            order.client_phone_snapshot,
        )
        if not all(required):
            _gap(
                report,
                kind="order_snapshot",
                identifier=order.id,
                reason="Entidade operacional ausente e snapshot comercial incompleto.",
            )
        if required != before:
            report.orders_updated += 1

    if order_ids:
        items = list(
            db.scalars(
                select(SaleOrderItem)
                .where(SaleOrderItem.sale_order_id.in_(order_ids))
                .order_by(SaleOrderItem.id)
                .with_for_update()
            )
        )
    else:
        items = []
    for item in items:
        report.items_scanned += 1
        before = (
            item.photo_asset_id_snapshot,
            item.filename_snapshot,
            item.checksum_sha256_snapshot,
        )
        photo = db.get(PhotoAsset, item.photo_asset_id) if item.photo_asset_id else None
        if photo:
            item.photo_asset_id_snapshot = item.photo_asset_id_snapshot or photo.id
            item.filename_snapshot = (
                item.filename_snapshot or photo.display_name or photo.filename
            )
        required = (item.photo_asset_id_snapshot, item.filename_snapshot)
        if not all(required):
            _gap(
                report,
                kind="item_snapshot",
                identifier=item.id,
                reason="Foto operacional ausente e snapshot do item incompleto.",
            )
        after = (
            item.photo_asset_id_snapshot,
            item.filename_snapshot,
            item.checksum_sha256_snapshot,
        )
        if after != before:
            report.items_updated += 1

    if report.gaps:
        raise CommercialHistoryGap(report)
    db.flush()
    return report


def _gap(
    report: SnapshotBackfillReport,
    *,
    kind: str,
    identifier: UUID,
    reason: str,
) -> None:
    report.gaps.append({"kind": kind, "id": str(identifier), "reason": reason})


def backfill_commercial_snapshots(
    db: Session,
    *,
    block_on_confirmed_media_gap: bool = False,
) -> SnapshotBackfillReport:
    """Preenche somente campos ausentes e informa lacunas sem sobrescrever snapshots."""

    report = SnapshotBackfillReport()
    orders = list(db.scalars(select(SaleOrder).order_by(SaleOrder.created_at, SaleOrder.id)))
    orders_by_id = {order.id: order for order in orders}
    for order in orders:
        report.orders_scanned += 1
        before = (
            order.derived_gallery_id_snapshot,
            order.derived_gallery_name_snapshot,
            order.parent_gallery_id_snapshot,
            order.parent_gallery_name_snapshot,
        )
        gallery = db.get(DerivedGallery, order.derived_gallery_id) if order.derived_gallery_id else None
        parent = db.get(ParentGallery, gallery.parent_gallery_id) if gallery else None
        if gallery and parent:
            order.derived_gallery_id_snapshot = order.derived_gallery_id_snapshot or gallery.id
            order.derived_gallery_name_snapshot = (
                order.derived_gallery_name_snapshot or gallery.name
            )
            order.parent_gallery_id_snapshot = order.parent_gallery_id_snapshot or parent.id
            order.parent_gallery_name_snapshot = (
                order.parent_gallery_name_snapshot or parent.name
            )
        if not all(
            (
                order.derived_gallery_id_snapshot,
                order.derived_gallery_name_snapshot,
                order.parent_gallery_id_snapshot,
                order.parent_gallery_name_snapshot,
            )
        ):
            _gap(
                report,
                kind="order_snapshot",
                identifier=order.id,
                reason="Galeria operacional ausente e snapshot incompleto.",
            )
        after = (
            order.derived_gallery_id_snapshot,
            order.derived_gallery_name_snapshot,
            order.parent_gallery_id_snapshot,
            order.parent_gallery_name_snapshot,
        )
        if after != before:
            report.orders_updated += 1

    items = list(db.scalars(select(SaleOrderItem).order_by(SaleOrderItem.id)))
    for item in items:
        report.items_scanned += 1
        before = (item.photo_asset_id_snapshot, item.filename_snapshot)
        photo = db.get(PhotoAsset, item.photo_asset_id) if item.photo_asset_id else None
        if photo:
            item.photo_asset_id_snapshot = item.photo_asset_id_snapshot or photo.id
            item.filename_snapshot = item.filename_snapshot or photo.display_name or photo.filename
        if not item.photo_asset_id_snapshot or not item.filename_snapshot:
            _gap(
                report,
                kind="item_snapshot",
                identifier=item.id,
                reason="Foto operacional ausente e snapshot incompleto.",
            )
        after = (item.photo_asset_id_snapshot, item.filename_snapshot)
        if after != before:
            report.items_updated += 1

        order = orders_by_id.get(item.sale_order_id)
        if not order or order.payment_status != "confirmed":
            continue
        historical_media = db.scalar(
            select(CommercialHistoryMedia).where(
                CommercialHistoryMedia.sale_order_item_id == item.id,
                CommercialHistoryMedia.status == "ready",
            )
        )
        operational_media_available = bool(photo and photo.storage_key)
        if not historical_media and not operational_media_available:
            _gap(
                report,
                kind="confirmed_media",
                identifier=item.id,
                reason="Item confirmado sem mídia operacional nem manifesto histórico pronto.",
            )

    if block_on_confirmed_media_gap and any(
        gap["kind"] == "confirmed_media" for gap in report.gaps
    ):
        db.rollback()
        raise CommercialHistoryGap(report)
    db.commit()
    return report
