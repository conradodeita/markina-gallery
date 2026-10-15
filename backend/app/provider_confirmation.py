"""Aplicação financeira interna após verificação tipada; não é exposta por rota."""

import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.acervo_context import require_active_owner
from app.auth import (
    Client,
    NotificationDelivery,
    NotificationEvent,
    ProviderPayment,
    ProviderPaymentCorrection,
    ProviderPaymentReceipt,
    SaleOrder,
    SaleOrderItem,
    audit,
    now,
)
from app.notification_settings import enqueue_event
from app.payment_provider import PaymentCheckResult
from app.tenancy import TenantContextError, require_admin_tenant


@dataclass(frozen=True)
class ApplyResult:
    state: str
    confirmed: bool
    duplicate: bool = False


def apply_payment_check(
    db: Session,
    payment_id: UUID,
    *,
    requested_slug: str,
    result: PaymentCheckResult,
) -> ApplyResult:
    """Atomically retain evidence, confirm every order, and queue one client event.

    A public return route may call this only after payment_check; browser
    query values remain candidates and all financial checks are repeated here.
    """
    owner = db.scalar(select(ProviderPayment.client_id).where(ProviderPayment.id == payment_id))
    tenant_id = db.scalar(select(ProviderPayment.tenant_id).where(ProviderPayment.id == payment_id))
    if owner is None or tenant_id is None:
        raise LookupError("Compra não encontrada.")
    db.scalar(select(Client.id).where(Client.id == owner, Client.tenant_id == tenant_id).with_for_update())
    require_active_owner(db, tenant_id)
    payment = db.scalar(select(ProviderPayment).where(
        ProviderPayment.id == payment_id,
        ProviderPayment.tenant_id == tenant_id,
        ProviderPayment.client_id == owner,
    ).with_for_update().execution_options(populate_existing=True))
    if payment is None:
        raise LookupError("Compra não encontrada.")

    evidence = {
        "amount": result.amount_cents,
        "capture_method": result.capture_method,
        "handle": result.handle,
        "outcome": result.outcome,
        "payment_id": str(result.payment_id),
        "slug": result.slug,
        "tenant_id": str(result.tenant_id),
        "transaction_nsu": result.transaction_nsu,
        "verification_profile": result.verification_profile,
    }
    digest = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    receipt = db.scalar(select(ProviderPaymentReceipt).where(
        ProviderPaymentReceipt.tenant_id == payment.tenant_id,
        ProviderPaymentReceipt.payment_id == payment.id,
        ProviderPaymentReceipt.digest == digest,
    ).with_for_update())
    if receipt and receipt.state == "verified" and payment.state == "confirmed":
        return ApplyResult(state=payment.state, confirmed=True, duplicate=True)
    if receipt is None:
        receipt = ProviderPaymentReceipt(
            tenant_id=payment.tenant_id,
            client_id=payment.client_id,
            payment_id=payment.id,
            digest=digest,
            transaction_nsu=result.transaction_nsu,
            slug=result.slug,
            verification_profile=result.verification_profile,
            state="queued",
            attempts=1,
        )
        db.add(receipt)
        db.flush()
    else:
        receipt.attempts += 1

    if payment.state == "hold":
        if receipt.state != "verified":
            receipt.state = "ignored"
            receipt.processed_at = now()
        return ApplyResult(state="hold", confirmed=False)
    if payment.state == "confirmed":
        if payment.provider_transaction_nsu == result.transaction_nsu:
            receipt.state = "verified"
            receipt.processed_at = now()
            return ApplyResult(state="confirmed", confirmed=True, duplicate=True)
        receipt.state = "ignored"
        receipt.processed_at = now()
        audit(db, "provider_payment.conflicting_replay", str(payment.id), tenant_id=payment.tenant_id)
        return ApplyResult(state="confirmed", confirmed=True)
    if payment.state not in {"awaiting_payment", "verification_required"}:
        return _exception(db, payment, receipt, "provider_payment.invalid_state")

    matches = (
        result.outcome == "verified"
        and result.payment_id == payment.id
        and result.tenant_id == payment.tenant_id
        and result.handle == payment.handle_snapshot
        and result.slug == requested_slug
        and result.transaction_nsu.strip() == result.transaction_nsu
        and result.verification_profile == payment.verification_profile
        and result.amount_cents == payment.total_cents
        and result.capture_method == "credit_card"
    )
    if not matches:
        receipt.state = "ignored"
        receipt.processed_at = now()
        if result.outcome in {"mismatch"} or (result.outcome == "verified" and (
            result.payment_id != payment.id or result.tenant_id != payment.tenant_id
            or result.handle != payment.handle_snapshot or result.slug != requested_slug
            or result.verification_profile != payment.verification_profile
            or result.amount_cents != payment.total_cents
            or result.capture_method != "credit_card"
        )):
            return _exception(db, payment, receipt, "provider_payment.evidence_mismatch")
        return ApplyResult(state=payment.state, confirmed=False)

    duplicate_payment = db.scalar(select(ProviderPayment.id).where(
        ProviderPayment.provider == payment.provider,
        ProviderPayment.provider_transaction_nsu == result.transaction_nsu,
        ProviderPayment.id != payment.id,
    ).with_for_update())
    if duplicate_payment:
        return _exception(db, payment, receipt, "provider_payment.transaction_reused")
    orders = list(db.scalars(select(SaleOrder).where(
        SaleOrder.provider_payment_id == payment.id,
        SaleOrder.tenant_id == payment.tenant_id,
        SaleOrder.client_id == payment.client_id,
    ).order_by(SaleOrder.id).with_for_update().execution_options(populate_existing=True)))
    if not orders or any(
        order.payment_status != "pending" or order.frozen_at is None
        or order.assets_removed_at is not None or order.payment_group_id is not None
        or order.payment_required_snapshot is not True
        for order in orders
    ) or sum(order.total_cents for order in orders) != payment.total_cents:
        return _exception(db, payment, receipt, "provider_payment.orders_inconsistent")
    for order in orders:
        item_total = db.scalar(select(func.coalesce(func.sum(SaleOrderItem.unit_price_cents), 0)).where(
            SaleOrderItem.tenant_id == payment.tenant_id,
            SaleOrderItem.sale_order_id == order.id,
        ))
        if item_total != order.total_cents:
            return _exception(db, payment, receipt, "provider_payment.order_amount_mismatch")

    confirmed_at = now()
    payment.state = "confirmed"
    payment.provider_transaction_nsu = result.transaction_nsu
    payment.confirmed_at = confirmed_at
    payment.revision_number += 1
    payment.updated_at = confirmed_at
    for order in orders:
        order.payment_status = "confirmed"
        order.confirmed_at = confirmed_at
    receipt.state = "verified"
    receipt.processed_at = confirmed_at
    first = orders[0]
    event = enqueue_event(
        db,
        event_type="payment_confirmed",
        event_key=f"provider-payment-confirmed:{payment.id}:{payment.revision_number}",
        values={"cliente": first.client_name_snapshot or "Cliente",
                "galeria": "sua compra", "pedido": str(payment.id)[:8]},
        target_path=f"/library/purchases#payment-{payment.id}",
        recipients=[payment.client_id],
        parent_gallery_id=first.parent_gallery_id_snapshot,
        derived_gallery_id=first.derived_gallery_id,
        client_id=payment.client_id,
        sale_order_id=first.id,
        tenant_id=payment.tenant_id,
    )
    for order in orders:
        order.payment_message_snapshot = event.whatsapp_body
    audit(db, "provider_payment.confirmed", str(payment.id), tenant_id=payment.tenant_id)
    return ApplyResult(state="confirmed", confirmed=True)


def place_payment_hold(
    db: Session,
    payment_id: UUID,
    *,
    actor_admin_id: UUID,
    idempotency_key: str,
    reason: str,
) -> ApplyResult:
    """Audit an authorized correction and suspend card orders/notices atomically."""
    if not idempotency_key or len(idempotency_key) > 128 or not reason.strip() or len(reason.strip()) > 500:
        raise ValueError("Informe uma chave de operação e um motivo válidos.")
    owner = db.scalar(select(ProviderPayment.client_id).where(ProviderPayment.id == payment_id))
    tenant_id = db.scalar(select(ProviderPayment.tenant_id).where(ProviderPayment.id == payment_id))
    if owner is None or tenant_id is None:
        raise LookupError("Compra não encontrada.")
    db.scalar(select(Client.id).where(Client.id == owner, Client.tenant_id == tenant_id).with_for_update())
    require_active_owner(db, tenant_id)
    try:
        if require_admin_tenant(db, actor_admin_id).id != tenant_id:
            raise ValueError("Compra indisponível para este administrador.")
    except TenantContextError as exc:
        raise ValueError("Compra indisponível para este administrador.") from exc
    payment = db.scalar(select(ProviderPayment).where(
        ProviderPayment.id == payment_id,
        ProviderPayment.tenant_id == tenant_id,
        ProviderPayment.client_id == owner,
    ).with_for_update().execution_options(populate_existing=True))
    correction = db.scalar(select(ProviderPaymentCorrection).where(
        ProviderPaymentCorrection.tenant_id == tenant_id,
        ProviderPaymentCorrection.payment_id == payment_id,
        ProviderPaymentCorrection.idempotency_key == idempotency_key,
    ))
    if correction:
        return ApplyResult(state="hold", confirmed=False, duplicate=True)
    if payment is None or payment.state != "confirmed" or not payment.provider_transaction_nsu:
        raise ValueError("Somente uma compra confirmada pode entrar em revisão.")
    orders = list(db.scalars(select(SaleOrder).where(
        SaleOrder.provider_payment_id == payment.id,
        SaleOrder.tenant_id == tenant_id,
        SaleOrder.client_id == owner,
    ).order_by(SaleOrder.id).with_for_update().execution_options(populate_existing=True)))
    if not orders or any(order.payment_status != "confirmed" for order in orders):
        raise ValueError("Pedidos confirmados indisponíveis para revisão.")
    correction = ProviderPaymentCorrection(
        tenant_id=tenant_id,
        client_id=owner,
        payment_id=payment.id,
        actor_admin_id=actor_admin_id,
        idempotency_key=idempotency_key,
        reason=reason.strip(),
        previous_revision=payment.revision_number,
        previous_transaction_nsu=payment.provider_transaction_nsu,
    )
    db.add(correction)
    payment.state = "hold"
    payment.revision_number += 1
    payment.updated_at = now()
    for order in orders:
        order.payment_status = "pending"
        order.confirmed_at = None
        if order.delivery_album_url:
            order.delivery_revision += 1
    event_key = f"provider-payment-confirmed:{payment.id}:{correction.previous_revision}"
    event = db.scalar(select(NotificationEvent).where(
        NotificationEvent.tenant_id == tenant_id,
        NotificationEvent.event_key == event_key,
    ))
    if event:
        db.query(NotificationDelivery).filter(
            NotificationDelivery.tenant_id == tenant_id,
            NotificationDelivery.event_id == event.id,
            NotificationDelivery.status.in_(("queued", "processing")),
        ).update({"status": "cancelled", "last_error": "payment_hold",
                  "lease_token": None, "lease_until": None}, synchronize_session=False)
    audit(db, "provider_payment.hold", f"{payment.id}:{correction.id}", tenant_id=tenant_id)
    return ApplyResult(state="hold", confirmed=False)


def _exception(db: Session, payment: ProviderPayment, receipt: ProviderPaymentReceipt,
               audit_event: str) -> ApplyResult:
    receipt.state = "ignored"
    receipt.processed_at = now()
    payment.state = "exception"
    payment.revision_number += 1
    payment.updated_at = now()
    audit(db, audit_event, str(payment.id), tenant_id=payment.tenant_id)
    return ApplyResult(state="exception", confirmed=False)
