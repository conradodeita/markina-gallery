"""Projeção financeira mínima, compartilhada por compras, dashboard e exportação."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth import MercadoPagoPayment


def mercadopago_for_orders(db, orders, *, tenant_id):
    ids = {order.mercadopago_payment_id for order in orders
           if order.tenant_id == tenant_id and order.mercadopago_payment_id}
    return {payment.id: payment for payment in db.scalars(select(MercadoPagoPayment).options(
        selectinload(MercadoPagoPayment.account)).where(
        MercadoPagoPayment.tenant_id == tenant_id, MercadoPagoPayment.id.in_(ids)))} if ids else {}


def financial_status(payment, order):
    state = payment.state
    if state == "confirmed":
        return "confirmed" if order.delivery_album_url else "confirmed_undelivered"
    return {
        "prepared": "awaiting_payment", "sending": "verifying", "initiated": "awaiting_payment",
        "pending": "awaiting_payment", "processing": "processing",
        "verification_required": "verifying", "abandoned": "canceled",
    }.get(state, state)


def financial_fields(order, payments):
    payment = payments.get(order.mercadopago_payment_id)
    if not payment:
        return {"payment_provider": "infinitepay" if order.provider_payment_id else
                "pix" if order.payment_required_snapshot else None}
    return {
        "payment_provider": "mercadopago", "payment_method": payment.method,
        "mercadopago": {
            "id": str(payment.id), "state": payment.state, "method": payment.method,
            "test_account": payment.account.test_account,
            "active": payment.active, "total_cents": payment.total_cents,
            "provider_order_id": payment.provider_order_id,
            "provider_payment_id": payment.provider_payment_id,
            "order_status": payment.order_status, "order_detail": payment.order_detail,
            "transaction_status": payment.transaction_status,
            "transaction_detail": payment.transaction_detail,
        },
    }


def purchase_groups(orders):
    groups = {}
    for order in orders:
        payment = order.get("mercadopago")
        if payment:
            group = groups.setdefault(payment["id"], {**payment, "orders": []})
            group["orders"].append(order)
    return list(groups.values())
