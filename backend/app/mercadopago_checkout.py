"""Tentativas Orders: snapshot antes da rede e confirmação somente no servidor."""

import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import delete, select

from app.auth import (
    Client,
    DerivedGallery,
    GalleryClientState,
    MercadoPagoPayment,
    PaymentGroup,
    PhotoAsset,
    PhotoSelection,
    SaleOrder,
    SaleOrderItem,
    audit,
    expired,
    now,
)
from app.checkout import CheckoutError, _synchronize_order, client_photo_is_frozen_any
from app.integration_secrets import IntegrationSecretError
from app.mercadopago_provider import MercadoPagoError
from app.mercadopago_settings import account_for, credential_provider, effective_mercadopago
from app.payment_availability import lock_payment_account
from app.unified_checkout import _fingerprint, _valid_materials

TERMINAL_UNPAID = {"rejected", "canceled", "expired"}
FINANCIAL_REVIEW = {"partially_refunded", "charged_back", "duplicate_review"}
MINIMUM_MERCADOPAGO_TOTAL_CENTS = 100


def utc(value):
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def lock_customer(db, client):
    lock_payment_account(db, client.tenant_id)
    stored = db.scalar(select(Client).where(
        Client.id == client.id, Client.tenant_id == client.tenant_id).with_for_update())
    if not stored:
        raise CheckoutError("Compra indisponível.")


def own_payment(db, payment_id, client, *, lock=False):
    query = select(MercadoPagoPayment).where(
        MercadoPagoPayment.id == payment_id, MercadoPagoPayment.tenant_id == client.tenant_id,
        MercadoPagoPayment.client_id == client.id).execution_options(populate_existing=True)
    payment = db.scalar(query.with_for_update() if lock else query)
    if not payment:
        raise CheckoutError("Compra indisponível.")
    return payment


def active_payment(db, client):
    return db.scalar(select(MercadoPagoPayment).where(
        MercadoPagoPayment.tenant_id == client.tenant_id, MercadoPagoPayment.client_id == client.id,
        MercadoPagoPayment.active.is_(True)).execution_options(populate_existing=True))


def payment_orders(db, payment):
    return list(db.scalars(select(SaleOrder).where(
        SaleOrder.tenant_id == payment.tenant_id, SaleOrder.client_id == payment.client_id,
        SaleOrder.mercadopago_payment_id == payment.id).order_by(SaleOrder.id).with_for_update()))


def payment_payload(db, payment):
    account = account_for(db, payment.account_id, payment.tenant_id)
    orders = payment_orders(db, payment)
    items = list(db.scalars(select(SaleOrderItem).where(
        SaleOrderItem.tenant_id == payment.tenant_id,
        SaleOrderItem.sale_order_id.in_([order.id for order in orders])
    ).order_by(SaleOrderItem.filename_snapshot))) if orders else []
    qr_image = None
    if payment.method == "pix" and payment.state == "pending" and payment.pix_copy_paste:
        from app.pix import PixCodeError, pix_qr_data_url
        try:
            qr_image = pix_qr_data_url(payment.pix_copy_paste)
        except PixCodeError:
            pass  # O estado não é inferido do QR; consulta Orders permanece autoritativa.
    return {
        "id": str(payment.id), "provider": "mercadopago", "method": payment.method,
        "state": payment.state, "active": payment.active, "total_cents": payment.total_cents,
        "cart_revision": payment.cart_revision, "order_status": payment.order_status,
        "order_detail": payment.order_detail, "transaction_status": payment.transaction_status,
        "transaction_detail": payment.transaction_detail,
        "provider_order_id": payment.provider_order_id,
        "provider_payment_id": payment.provider_payment_id,
        "public_key": account.public_key if account and payment.state == "prepared" else None,
        "pix_copy_paste": payment.pix_copy_paste if payment.state == "pending" else None,
        "pix_qr_code": qr_image,
        "test_account": account.test_account if account else False,
        # Orders API permits cancellation only while the order is created or
        # action_required. In particular, processing/in_review must stay locked.
        "can_cancel": payment.active and payment.state in {"prepared", "initiated", "pending"},
        "items": [{"name": item.filename_snapshot, "unit_price_cents": item.unit_price_cents,
                   "order_id": str(item.sale_order_id)} for item in items],
    }


def prepare_payment(db, client, *, revision, key, method):
    lock_customer(db, client)
    existing = db.scalar(select(MercadoPagoPayment).where(
        MercadoPagoPayment.tenant_id == client.tenant_id, MercadoPagoPayment.client_id == client.id,
        MercadoPagoPayment.checkout_key == str(key)))
    if existing:
        if existing.cart_revision != revision or existing.method != method:
            raise CheckoutError("Esta solicitação pertence a outra revisão. Atualize o carrinho.")
        if existing.state == "prepared" and existing.total_cents < MINIMUM_MERCADOPAGO_TOTAL_CENTS:
            raise CheckoutError("Para pagar com Mercado Pago, selecione fotos que somem pelo menos R$ 1,00.")
        return existing
    active = active_payment(db, client)
    if active and active.state != "prepared":
        return active
    account = effective_mercadopago(db, client.tenant_id, client_id=client.id)
    if not account:
        raise CheckoutError("Mercado Pago indisponível. Sua seleção foi mantida.")
    materials = _valid_materials(db, client)
    if _fingerprint(materials) != revision:
        raise CheckoutError("Sua seleção mudou. Confira o carrinho antes de pagar.")
    total_cents = sum(material[3].quote.total_cents for _, _, material, _ in materials)
    if total_cents < MINIMUM_MERCADOPAGO_TOTAL_CENTS:
        raise CheckoutError("Para pagar com Mercado Pago, selecione fotos que somem pelo menos R$ 1,00.")
    if (active and active.cart_revision == revision and active.method == method
            and active.account_id == account.id):
        return active
    if active:
        active.state, active.active = "abandoned", False
        db.flush()
    payment = MercadoPagoPayment(
        tenant_id=client.tenant_id, client_id=client.id, account_id=account.id,
        checkout_key=str(key), cart_revision=revision, method=method, state="prepared",
        total_cents=total_cents)
    db.add(payment)
    db.flush()
    audit(db, "mercadopago.prepared", str(payment.id), tenant_id=payment.tenant_id)
    return payment


def freeze_orders(db, client, payment):
    materials = _valid_materials(db, client)
    if _fingerprint(materials) != payment.cart_revision:
        raise CheckoutError("Sua seleção mudou. Volte ao carrinho para conferir.")
    if sum(item[2][3].quote.total_cents for item in materials) != payment.total_cents:
        raise CheckoutError("O total mudou. Volte ao carrinho para conferir.")
    # Rascunhos PIX ainda não comunicados não são transações externas.
    drafts = list(db.scalars(select(SaleOrder).where(
        SaleOrder.tenant_id == client.tenant_id, SaleOrder.client_id == client.id,
        SaleOrder.payment_status == "pending", SaleOrder.frozen_at.is_(None),
        SaleOrder.mercadopago_payment_id.is_(None), SaleOrder.provider_payment_id.is_(None),
    ).with_for_update()))
    for draft in drafts:
        draft.payment_status = "cancelled"
        if draft.payment_group_id:
            group = db.scalar(select(PaymentGroup).where(
                PaymentGroup.tenant_id == client.tenant_id,
                PaymentGroup.id == draft.payment_group_id).with_for_update())
            if not group or group.state != "draft":
                raise CheckoutError("Retome o pagamento PIX já comunicado.")
            group.state = "unavailable"
    db.flush()
    for gallery, parent, material, _ in materials:
        order = SaleOrder(
            tenant_id=client.tenant_id, client_id=client.id,
            derived_gallery_id=None if isinstance(gallery, GalleryClientState) else gallery.id,
            parent_gallery_id=parent.id if isinstance(gallery, GalleryClientState) else None,
            derived_gallery_id_snapshot=None if isinstance(gallery, GalleryClientState) else gallery.id,
            derived_gallery_name_snapshot=parent.name if isinstance(gallery, GalleryClientState)
            else gallery.name,
            parent_gallery_id_snapshot=parent.id, parent_gallery_name_snapshot=parent.name,
            checkout_key=str(payment.id), total_cents=payment.total_cents,
            mercadopago_payment_id=payment.id,
        )
        _synchronize_order(db, order=order, gallery=gallery, client=client, material=material)
        order.price_rule_snapshot = {
            **order.price_rule_snapshot,
            "terms": {**order.price_rule_snapshot["terms"],
                      "payment_confirmation": "mercadopago_orders"},
        }
        order.frozen_at = now()
        db.execute(delete(PhotoSelection).where(
            PhotoSelection.tenant_id == client.tenant_id, PhotoSelection.client_id == client.id,
            PhotoSelection.id.in_([row.id for row in material[0]])))
    db.flush()


def amount(value):
    try:
        result = Decimal(str(value)) * 100
        if not result.is_finite() or result < 0 or result != result.to_integral_value():
            raise ValueError()
        return int(result)
    except (InvalidOperation, ValueError):
        raise CheckoutError("Resposta financeira inconsistente.") from None


def external_state(order, transaction):
    state, detail = order.get("status"), order.get("status_detail")
    tx_state, tx_detail = transaction.get("status"), transaction.get("status_detail")
    if state == "refunded" and tx_state == "refunded":
        return "refunded"
    if state == "charged_back" or tx_state == "charged_back":
        return "charged_back"
    if detail == "partially_refunded" and tx_detail == "partially_refunded":
        return "partially_refunded"
    if state == "processed" and detail == "accredited" and (
        tx_state == "processed" and tx_detail == "accredited"
    ):
        return "confirmed"
    if state in {"failed", "canceled"} and tx_state in {"failed", "canceled", "expired"}:
        return "expired" if "expired" in {detail, tx_detail, tx_state} else (
            "rejected" if state == "failed" else "canceled")
    if state == "created" and tx_state == "created":
        return "initiated"
    if state in {"processing", "in_review"} or tx_state in {"processing", "in_review"}:
        return "processing"
    if state == "action_required" or tx_state == "action_required":
        return "pending"
    return "verification_required"


def restore_selection(db, payment, orders):
    """Restaura somente material ainda existente; acesso continua validado ao consultar."""
    for order in orders:
        if order.parent_gallery_id:
            gallery = db.scalar(select(GalleryClientState).where(
                GalleryClientState.tenant_id == payment.tenant_id,
                GalleryClientState.parent_gallery_id == order.parent_gallery_id,
                GalleryClientState.client_id == payment.client_id))
        else:
            gallery = db.scalar(select(DerivedGallery).where(
                DerivedGallery.tenant_id == payment.tenant_id,
                DerivedGallery.id == order.derived_gallery_id))
        if not gallery or (gallery.selection_expires_at and expired(gallery.selection_expires_at)):
            continue
        for item in db.scalars(select(SaleOrderItem).where(
            SaleOrderItem.tenant_id == payment.tenant_id, SaleOrderItem.sale_order_id == order.id
        )):
            photo = db.scalar(select(PhotoAsset).where(
                PhotoAsset.tenant_id == payment.tenant_id, PhotoAsset.id == item.photo_asset_id,
                PhotoAsset.available.is_(True)))
            if not photo or client_photo_is_frozen_any(
                db, client_id=payment.client_id, photo_id=photo.id
            ):
                continue
            if db.scalar(select(PhotoSelection.id).where(
                PhotoSelection.tenant_id == payment.tenant_id,
                PhotoSelection.client_id == payment.client_id, PhotoSelection.photo_asset_id == photo.id
            )):
                continue
            db.add(PhotoSelection(
                tenant_id=payment.tenant_id, client_id=payment.client_id, photo_asset_id=photo.id,
                parent_gallery_id=order.parent_gallery_id,
                derived_gallery_id=order.derived_gallery_id if not order.parent_gallery_id else None))


def apply_order(db, payment, resource):
    """Chamador mantém locks conta/cliente/tentativa; corpo vem apenas da API."""
    account = account_for(db, payment.account_id, payment.tenant_id)
    try:
        orders = payment_orders(db, payment)
        snapshot_items = list(db.scalars(select(SaleOrderItem).where(
            SaleOrderItem.tenant_id == payment.tenant_id,
            SaleOrderItem.sale_order_id.in_([order.id for order in orders]))))
        if (not payment.sent_at or not orders or not snapshot_items
                or sum(item.unit_price_cents for item in snapshot_items) != payment.total_cents
                or sum(order.total_cents for order in orders) != payment.total_cents):
            raise CheckoutError("Snapshot financeiro inconsistente.")
        transactions = resource.get("transactions", {}).get("payments", [])
        if (not account or resource.get("type") != "online" or len(transactions) != 1
                or resource.get("external_reference") != str(payment.id)
                or amount(resource.get("total_amount")) != payment.total_cents):
            raise CheckoutError("Resposta financeira inconsistente.")
        transaction = transactions[0]
        method = transaction.get("payment_method", {})
        expected_type = "bank_transfer" if payment.method == "pix" else "credit_card"
        if (amount(transaction.get("amount")) != payment.total_cents
                or method.get("type") != expected_type
                or (payment.method == "pix" and method.get("id") != "pix")
                or not re.fullmatch(r"PAY[A-Za-z0-9]{1,61}", str(transaction.get("id", "")))
                or not re.fullmatch(r"ORD[A-Za-z0-9]{1,61}", str(resource.get("id", "")))
                or (payment.provider_order_id and payment.provider_order_id != resource["id"])
                or ("user_id" in resource and str(resource["user_id"]) != account.seller_id)
                or ("live_mode" in resource and resource["live_mode"] != (not account.test_account))
                or ("currency_id" in resource and resource["currency_id"] != "BRL")
                or any(not isinstance(value, str) or len(value) > limit for value, limit in (
                    (resource.get("status"), 32), (resource.get("status_detail"), 64),
                    (transaction.get("status"), 32), (transaction.get("status_detail"), 64)))):
            raise CheckoutError("Resposta financeira inconsistente.")
        updated = datetime.fromisoformat(resource["last_updated_date"])
        if updated.tzinfo is None:
            raise ValueError()
        state = external_state(resource, transaction)
        if state == "confirmed" and amount(resource.get("total_paid_amount")) != payment.total_cents:
            raise CheckoutError("Valor pago divergente.")
    except (CheckoutError, KeyError, ValueError, TypeError, AttributeError):
        payment.error_category = "inconsistent_resource"
        if not payment.confirmed_at:
            payment.state = "verification_required"
        return False
    if payment.provider_updated_at and updated < utc(payment.provider_updated_at):
        return False
    if payment.state == "refunded" and state != "refunded":
        return False
    if payment.state in TERMINAL_UNPAID and state not in {
        "confirmed", "refunded", *FINANCIAL_REVIEW
    }:
        return False
    # Estados financeiros finais não regridem por resposta atrasada ou cache remoto.
    if payment.confirmed_at and state not in {"confirmed", "refunded", *FINANCIAL_REVIEW}:
        return False
    if payment.state in {"refunded", "partially_refunded", "charged_back"} and state not in {
        "refunded", *FINANCIAL_REVIEW
    }:
        return False
    previous = payment.state
    payment.provider_order_id = resource["id"]
    payment.provider_payment_id = transaction["id"]
    payment.provider_updated_at = updated
    payment.order_status = resource.get("status")
    payment.order_detail = resource.get("status_detail")
    payment.transaction_status = transaction.get("status")
    payment.transaction_detail = transaction.get("status_detail")
    payment.error_category = None
    if state == "confirmed":
        own_items = select(SaleOrderItem.photo_asset_id_snapshot).where(
            SaleOrderItem.tenant_id == payment.tenant_id,
            SaleOrderItem.sale_order_id.in_([order.id for order in orders]))
        overlap = db.scalar(select(SaleOrder.id).join(
            SaleOrderItem, SaleOrderItem.sale_order_id == SaleOrder.id).where(
            SaleOrder.tenant_id == payment.tenant_id, SaleOrder.client_id == payment.client_id,
            SaleOrder.payment_status.in_(("confirmed", "pending")),
            SaleOrder.frozen_at.is_not(None), SaleOrder.id.not_in([o.id for o in orders]),
            SaleOrderItem.photo_asset_id_snapshot.in_(own_items)))
        payment.confirmed_at = payment.confirmed_at or now()
        if overlap:
            state = "duplicate_review"
            payment.error_category = "overlapping_confirmation"
    payment.state = state
    payment.active = state in {"initiated", "pending", "processing", "verification_required"}
    for order in orders:
        order.payment_status = "confirmed" if state == "confirmed" else (
            "cancelled" if state in TERMINAL_UNPAID | {"refunded"} else "pending")
        if state == "confirmed":
            order.confirmed_at = payment.confirmed_at
        if state in {"refunded", *FINANCIAL_REVIEW} and previous != state:
            from app.order_delivery import suspend_delivery_access
            suspend_delivery_access(db, order=order)
    db.flush()
    if state in TERMINAL_UNPAID and not payment.confirmed_at:
        restore_selection(db, payment, orders)
    if state == "confirmed":
        db.execute(delete(PhotoSelection).where(
            PhotoSelection.tenant_id == payment.tenant_id,
            PhotoSelection.client_id == payment.client_id,
            PhotoSelection.photo_asset_id.in_([item.photo_asset_id_snapshot for item in snapshot_items])))
    if payment.method == "pix" and state == "pending":
        qr = method.get("qr_code")
        payment.pix_copy_paste = qr if isinstance(qr, str) and len(qr) <= 4096 else None
    if previous != state:
        audit(db, "mercadopago.state_changed", f"{payment.id}:{state}", tenant_id=payment.tenant_id)
        if state == "confirmed":
            from app.notification_settings import enqueue_event
            enqueue_event(
                db, tenant_id=payment.tenant_id, event_type="payment_confirmed",
                event_key=f"mp-confirmed:{payment.id}",
                values={"cliente": orders[0].client_name_snapshot if orders else "",
                        "galeria": "sua compra", "pedido": str(payment.id)[:8],
                        "contexto_pagamento": f"da compra {str(payment.id)[:8]}"},
                target_path=f"/library/purchases#payment-{payment.id}",
                recipients=[payment.client_id], client_id=payment.client_id,
                sale_order_id=orders[0].id if orders else None)
    payment.check_attempts = 0
    payment.next_check_at = now() + (timedelta(minutes=2) if payment.active else timedelta(days=1))
    return True


def reconcile(db, client, payment_id):
    lock_customer(db, client)
    payment = own_payment(db, payment_id, client, lock=True)
    if payment.state in {"prepared", "abandoned"}:
        return payment
    account = account_for(db, payment.account_id, payment.tenant_id)
    try:
        provider = credential_provider(account)
        if payment.provider_order_id:
            resource = provider.get(payment.provider_order_id)
        else:
            result = provider.search(
                reference=str(payment.id),
                begin_date=(utc(payment.created_at) - timedelta(minutes=1)).isoformat(),
                end_date=now().isoformat())
            rows = result.get("data", [])
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise MercadoPagoError("invalid_response")
            candidates = [row for row in rows
                          if row.get("external_reference") == str(payment.id)]
            if len(candidates) != 1 or not isinstance(candidates[0].get("id"), str):
                raise MercadoPagoError("unknown_creation")
            resource = provider.get(candidates[0]["id"])
        if not apply_order(db, payment, resource):
            if payment.error_category:
                raise MercadoPagoError(payment.error_category)
            payment.next_check_at = now() + (
                timedelta(minutes=2) if payment.active else timedelta(days=1))
    except (MercadoPagoError, IntegrationSecretError) as exc:
        payment.error_category = getattr(exc, "category", "vault_unavailable")
        if isinstance(exc, MercadoPagoError) and exc.category == "unauthorized":
            account.status = "unauthorized"
        if not payment.confirmed_at and payment.active:
            payment.state = "verification_required"
        payment.check_attempts += 1
        payment.next_check_at = now() + timedelta(seconds=min(3600, 15 * 2 ** min(
            payment.check_attempts, 8)))
    return payment


def submit_payment(db, client, payment_id, data):
    lock_customer(db, client)
    payment = own_payment(db, payment_id, client, lock=True)
    if payment.state != "prepared":
        return payment
    account = effective_mercadopago(db, client.tenant_id, client_id=client.id)
    if not account or account.id != payment.account_id:
        raise CheckoutError("A configuração mudou. Confira o carrinho novamente.")
    cents = payment.total_cents
    if cents < MINIMUM_MERCADOPAGO_TOTAL_CENTS:
        raise CheckoutError("Para pagar com Mercado Pago, selecione fotos que somem pelo menos R$ 1,00.")
    method = {"id": "pix", "type": "bank_transfer"} if payment.method == "pix" else {
        "id": data.payment_method_id, "type": "credit_card",
        "token": data.token.get_secret_value() if data.token else None, "installments": 1}
    if payment.method == "credit_card" and (not method["token"] or not method["id"]):
        raise CheckoutError("Confira os dados do cartão no formulário seguro.")
    provider = credential_provider(account)
    try:
        available_methods = provider.payment_methods()
    except (MercadoPagoError, IntegrationSecretError):
        raise CheckoutError("Não foi possível conferir o valor mínimo do Mercado Pago. Tente novamente.") from None
    selected_method = next((item for item in available_methods if
                            item.get("id") == method["id"] and
                            item.get("payment_type_id") == method["type"] and
                            item.get("status") == "active"), None)
    if not selected_method:
        raise CheckoutError("Essa forma de pagamento está indisponível. Escolha outra e tente novamente.")
    try:
        provider_minimum_cents = amount(selected_method["min_allowed_amount"])
    except (KeyError, CheckoutError):
        raise CheckoutError("Não foi possível conferir o valor mínimo do Mercado Pago. Tente novamente.") from None
    if cents < max(MINIMUM_MERCADOPAGO_TOTAL_CENTS, provider_minimum_cents):
        minimum = max(MINIMUM_MERCADOPAGO_TOTAL_CENTS, provider_minimum_cents)
        minimum_text = f"R$ {minimum // 100},{minimum % 100:02d}"
        raise CheckoutError(
            f"Essa forma de pagamento aceita compras a partir de {minimum_text}. "
            "Ajuste sua seleção e tente novamente."
        )
    freeze_orders(db, client, payment)
    body = {
        "type": "online", "processing_mode": "automatic",
        "total_amount": f"{cents // 100}.{cents % 100:02d}",
        "external_reference": str(payment.id),
        "payer": {"email": data.email,
                  "identification": {"type": "CPF", "number": data.identification_number}},
        "transactions": {"payments": [{
            "amount": f"{cents // 100}.{cents % 100:02d}", "payment_method": method}]},
    }
    payment.state, payment.sent_at = "sending", now()
    payment.next_check_at = now() + timedelta(seconds=45)
    db.commit()  # Tentativa/reservas duráveis ANTES da rede; token nunca é persistido.
    try:
        response = provider.create(body, payment.id)
    except (MercadoPagoError, IntegrationSecretError):
        response = None
    lock_customer(db, client)
    payment = own_payment(db, payment_id, client, lock=True)
    if response:
        # A resposta de criação pode ser assíncrona e não trazer transação completa.
        resource_id = response.get("id")
        if (not payment.provider_order_id and isinstance(resource_id, str)
                and re.fullmatch(r"ORD[A-Za-z0-9]{1,61}", resource_id)
                and response.get("external_reference") in (None, str(payment.id))):
            payment.provider_order_id = resource_id
        apply_order(db, payment, response)
    elif payment.state == "sending":
        payment.state, payment.error_category = "verification_required", "unknown_creation"
    return payment


def cancel_payment(db, client, payment_id):
    lock_customer(db, client)
    payment = own_payment(db, payment_id, client, lock=True)
    if payment.state == "prepared":
        payment.active, payment.state = False, "abandoned"
        return payment
    if not payment.active:
        return payment
    payment = reconcile(db, client, payment.id)
    if not payment.active or not payment.provider_order_id:
        return payment
    # Reconciliation may have advanced the order since the UI rendered. Never
    # call cancel for processing/unknown states; the Orders API rejects them.
    if payment.state not in {"initiated", "pending"}:
        return payment
    try:
        account = account_for(db, payment.account_id, payment.tenant_id)
        provider = credential_provider(account)
        provider.cancel(payment.provider_order_id, f"cancel-{payment.id}")
        apply_order(db, payment, provider.get(payment.provider_order_id))
    except (MercadoPagoError, IntegrationSecretError):
        payment.error_category = "cancellation_unconfirmed"
    return payment
