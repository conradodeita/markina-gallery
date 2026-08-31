"""Política comercial única antes de qualquer remoção operacional."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuditEvent, PaymentCommunication, SaleOrder, SaleOrderItem
from app.commercial_history import CommercialHistoryGap, materialize_commercial_history
from app.historical_media import (
    HistoricalMediaConflict,
    prepare_confirmed_historical_media,
)


class CommercialRemovalBlocked(RuntimeError):
    """Pagamento comunicado exige decisão administrativa antes da remoção."""


class CommercialRemovalPreparationFailed(RuntimeError):
    """O histórico confirmado ainda não pode sustentar a remoção."""


@dataclass
class CommercialRemovalReport:
    cancelled_pending_orders: int = 0
    confirmed_orders: int = 0


def apply_commercial_removal_policy(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID | None = None,
    derived_gallery_id: UUID | None = None,
    photo_asset_id: UUID | None = None,
) -> CommercialRemovalReport:
    """Bloqueia revisão, cancela pendências e prepara compras confirmadas."""

    query = select(SaleOrder).where(
        SaleOrder.parent_gallery_id_snapshot == parent_gallery_id
    )
    if client_id:
        query = query.where(SaleOrder.client_id == client_id)
    if derived_gallery_id:
        query = query.where(
            SaleOrder.derived_gallery_id_snapshot == derived_gallery_id
        )
    if photo_asset_id:
        query = query.join(
            SaleOrderItem, SaleOrderItem.sale_order_id == SaleOrder.id
        ).where(SaleOrderItem.photo_asset_id_snapshot == photo_asset_id)
    orders = list(db.scalars(query.distinct().with_for_update()))
    order_ids = [order.id for order in orders]
    pending_review_order_ids = (
        set(
            db.scalars(
                select(PaymentCommunication.sale_order_id).where(
                    PaymentCommunication.sale_order_id.in_(order_ids),
                    PaymentCommunication.status == "pending_review",
                )
            )
        )
        if order_ids
        else set()
    )
    if pending_review_order_ids:
        raise CommercialRemovalBlocked(
            "Há pagamento comunicado aguardando decisão administrativa."
        )

    report = CommercialRemovalReport()
    for order in orders:
        if order.payment_status == "pending":
            order.payment_status = "cancelled"
            report.cancelled_pending_orders += 1
            db.add(
                AuditEvent(
                    event="sale_order.cancelled_for_operational_removal",
                    subject=f"order_id:{order.id}",
                )
            )
        elif order.payment_status == "confirmed":
            report.confirmed_orders += 1
    if report.confirmed_orders:
        try:
            materialize_commercial_history(
                db,
                parent_gallery_id=parent_gallery_id,
                client_id=client_id,
                photo_asset_id=photo_asset_id,
            )
            prepare_confirmed_historical_media(
                db,
                parent_gallery_id=parent_gallery_id,
                client_id=client_id,
                photo_asset_id=photo_asset_id,
            )
        except (CommercialHistoryGap, FileNotFoundError, HistoricalMediaConflict) as exc:
            raise CommercialRemovalPreparationFailed(
                "O histórico confirmado ainda não está pronto para remoção."
            ) from exc
    db.flush()
    return report
