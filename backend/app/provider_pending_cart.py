"""Intenção externa no Carrinho; retirar não cancela pagamento nem libera reserva."""

from sqlalchemy import select

from app.acervo_context import client_tenant_id, require_active_owner
from app.auth import Client, ProviderPayment, SaleOrder, SaleOrderItem, audit, now
from app.checkout import CheckoutError

PENDING_STATES = frozenset(("creating", "awaiting_payment", "verification_required"))


def pending_checkout_payload(db, payment):
    orders = list(db.scalars(select(SaleOrder).where(
        SaleOrder.tenant_id==payment.tenant_id, SaleOrder.client_id==payment.client_id,
        SaleOrder.provider_payment_id==payment.id).order_by(SaleOrder.id)))
    items = list(db.scalars(select(SaleOrderItem).where(
        SaleOrderItem.tenant_id==payment.tenant_id, SaleOrderItem.sale_order_id.in_([order.id for order in orders]))
        .order_by(SaleOrderItem.filename_snapshot,SaleOrderItem.id))) if orders else []
    projected = []
    for order in orders:
        photos = []
        for item in items:
            if item.sale_order_id != order.id:
                continue
            url = None
            if item.photo_asset_id and not order.assets_removed_at:
                if order.derived_gallery_id:
                    url = f"/gallery/{order.derived_gallery_id}/photos/{item.photo_asset_id}/preview"
                elif order.parent_gallery_id:
                    url = f"/public-galleries/{order.parent_gallery_id}/photos/{item.photo_asset_id}/preview"
            photos.append({"id":str(item.id),"name":item.filename_snapshot,"preview_url":url})
        projected.append({"id":str(order.id),"name":order.derived_gallery_name_snapshot
                          or order.parent_gallery_name_snapshot,"items":photos})
    return {"id":str(payment.id),"status":payment.state,"revision":payment.revision_number,
        "checkout_url":payment.checkout_url if payment.state=="awaiting_payment" else None,
        "total_cents":payment.total_cents,"payment_methods":payment.checkout_methods_snapshot,
        "quantity":len(items),"orders":projected}


def dismiss_checkout(db, *, client, payment_id, expected_revision):
    tenant_id = client_tenant_id(db,client.id)
    require_active_owner(db,tenant_id)
    db.scalar(select(Client.id).where(Client.id==client.id,Client.tenant_id==tenant_id).with_for_update())
    payment = db.scalar(select(ProviderPayment).where(ProviderPayment.id==payment_id,
        ProviderPayment.tenant_id==tenant_id,ProviderPayment.client_id==client.id)
        .with_for_update().execution_options(populate_existing=True))
    if payment is None:
        raise LookupError("Checkout indisponível.")
    if payment.state not in PENDING_STATES or payment.confirmed_at or payment.provider_transaction_nsu:
        raise CheckoutError("O pagamento mudou. Atualize o carrinho antes de continuar.")
    if payment.cart_dismissed_at:
        return
    if payment.revision_number!=expected_revision:
        raise CheckoutError("O pagamento mudou. Atualize o carrinho antes de continuar.")
    payment.cart_dismissed_at=now()
    audit(db,"provider_payment.cart_dismissed",str(payment.id),tenant_id=tenant_id)
    db.flush()
