"""Rascunho de PIX é seleção; inventários conservam os registros completos."""

from uuid import UUID

from sqlalchemy import and_, or_, select

from app.auth import PaymentCommunication, PaymentGroup, SaleOrder


def visible_sale_order_condition(*, tenant_id: UUID):
    """Somente projeção comercial; não usar para exclusão ou reconciliação."""
    return ~and_(
        SaleOrder.payment_status == "pending", SaleOrder.frozen_at.is_(None),
        SaleOrder.confirmed_at.is_(None), SaleOrder.assets_removed_at.is_(None),
        SaleOrder.provider_payment_id.is_(None), SaleOrder.payment_group_id.is_not(None),
        SaleOrder.payment_group_id.in_(select(PaymentGroup.id).where(
            PaymentGroup.tenant_id == tenant_id, PaymentGroup.state == "draft")),
        ~select(PaymentCommunication.id).where(PaymentCommunication.tenant_id == tenant_id, or_(
            PaymentCommunication.sale_order_id == SaleOrder.id,
            PaymentCommunication.payment_group_id == SaleOrder.payment_group_id,
        )).correlate(SaleOrder).exists(),
    )
