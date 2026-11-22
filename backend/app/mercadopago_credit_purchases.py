"""Checkout Orders para pacotes de créditos, separado de vendas de fotos."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.acervo_context import require_active_owner
from app.auth import (
    MercadoPagoAccount,
    MercadoPagoCreditPurchase,
    MercadoPagoCreditPurchaseEvent,
    PaymentPreferences,
    PhotographerCreditEntry,
    PhotographerCreditPackage,
    Tenant,
    TenantAdmin,
    TenantCreditWallet,
    audit,
    now,
)
from app.checkout import CheckoutError
from app.integration_secrets import IntegrationCipher, IntegrationSecretError
from app.mercadopago_checkout import amount, external_state, utc
from app.mercadopago_provider import MercadoPagoError
from app.mercadopago_settings import account_for, can_create, credential_provider
from app.system_monitor.access import is_owner
from app.system_monitor.models import PlatformOwner

MINIMUM_TOTAL_CENTS = 100
ACTIVE_STATES = {"prepared", "submitting", "initiated", "pending", "processing", "verification_required"}
FINANCIAL_REVIEW_STATES = {"refunded", "partially_refunded", "charged_back"}
TERMINAL_UNPAID_STATES = {"rejected", "canceled", "expired"}


def tenant_has_financial_hold(db: Session, tenant_id: UUID) -> bool:
    return bool(db.scalar(select(MercadoPagoCreditPurchase.id).where(
        MercadoPagoCreditPurchase.tenant_id == tenant_id,
        MercadoPagoCreditPurchase.review_status.in_(("pending", "restricted")),
    ).limit(1)))


def financial_review_count(db: Session, tenant_id: UUID) -> int:
    return int(db.scalar(select(func.count(MercadoPagoCreditPurchase.id)).where(
        MercadoPagoCreditPurchase.tenant_id == tenant_id,
        MercadoPagoCreditPurchase.review_status.in_(("pending", "restricted")),
    )) or 0)


def financial_review_items(db: Session, tenant_id: UUID) -> list[dict]:
    purchases = db.scalars(select(MercadoPagoCreditPurchase).where(
        MercadoPagoCreditPurchase.tenant_id == tenant_id,
        or_(
            MercadoPagoCreditPurchase.review_status != "none",
            MercadoPagoCreditPurchase.state.in_(FINANCIAL_REVIEW_STATES),
        ),
    ).order_by(
        MercadoPagoCreditPurchase.created_at.desc(), MercadoPagoCreditPurchase.id.desc(),
    ).limit(50))
    return [_financial_review_payload(db, purchase) for purchase in purchases]


def _financial_review_payload(
    db: Session, purchase: MercadoPagoCreditPurchase, *, photographer_email: str | None = None,
) -> dict:
    events = db.scalars(select(MercadoPagoCreditPurchaseEvent).where(
        MercadoPagoCreditPurchaseEvent.purchase_id == purchase.id,
        MercadoPagoCreditPurchaseEvent.event_type.in_((*FINANCIAL_REVIEW_STATES, "owner_reviewed")),
    ).order_by(MercadoPagoCreditPurchaseEvent.occurred_at, MercadoPagoCreditPurchaseEvent.id))
    item = {
        "purchase_id": str(purchase.id),
        "tenant_id": str(purchase.tenant_id),
        "photographer_email": photographer_email,
        "package_name": purchase.package_name,
        "credit_quantity": purchase.credit_quantity,
        "total_cents": purchase.total_cents,
        "currency_code": purchase.currency_code,
        "payment_state": purchase.state,
        "review_status": purchase.review_status,
        "review_note": purchase.review_note,
        "reviewed_by_admin_id": str(purchase.reviewed_by_admin_id) if purchase.reviewed_by_admin_id else None,
        "created_at": purchase.created_at,
        "reviewed_at": purchase.reviewed_at,
        "events": [{
            "event_type": event.event_type,
            "occurred_at": event.occurred_at,
            "details": event.details or {},
        } for event in events],
    }
    return item


def financial_review_queue(db: Session, owner_admin_id: UUID) -> list[dict]:
    if not is_owner(db, owner_admin_id):
        raise CheckoutError("Acesso não autorizado.")
    from app.auth import AdminUser

    rows = db.execute(
        select(MercadoPagoCreditPurchase, AdminUser.email)
        .join(AdminUser, AdminUser.id == MercadoPagoCreditPurchase.buyer_admin_id)
        .where(MercadoPagoCreditPurchase.review_status.in_(("pending", "restricted")))
        .order_by(MercadoPagoCreditPurchase.created_at, MercadoPagoCreditPurchase.id)
        .limit(100)
    ).all()
    return [
        _financial_review_payload(db, purchase, photographer_email=email)
        for purchase, email in rows
    ]


def _lock_finite_wallet(db: Session, tenant_id: UUID) -> TenantCreditWallet:
    from app.payment_availability import lock_payment_account
    lock_payment_account(db, tenant_id)
    wallet = db.scalar(select(TenantCreditWallet).where(
        TenantCreditWallet.tenant_id == tenant_id,
    ).with_for_update())
    if wallet is None or wallet.mode != "finite":
        raise CheckoutError("Compra de créditos disponível somente para fotógrafos com carteira finita.")
    if tenant_has_financial_hold(db, tenant_id):
        raise CheckoutError("Novos uploads e compras estão bloqueados até revisão financeira do proprietário.")
    return wallet


def _resolve_owner_account(db: Session) -> tuple[UUID, UUID, MercadoPagoAccount]:
    owner = db.get(PlatformOwner, 1)
    if owner is None:
        raise CheckoutError("A conta recebedora do proprietário não está configurada.")
    memberships = list(db.scalars(
        select(TenantAdmin.tenant_id)
        .join(Tenant, Tenant.id == TenantAdmin.tenant_id)
        .where(
            TenantAdmin.admin_user_id == owner.admin_user_id,
            TenantAdmin.active.is_(True),
            Tenant.status == "active",
        )
        .order_by(TenantAdmin.tenant_id)
        .limit(2)
    ))
    if len(memberships) != 1:
        raise CheckoutError("A conta recebedora do proprietário não pôde ser resolvida com segurança.")
    receiver_tenant_id = memberships[0]
    require_active_owner(db, receiver_tenant_id)
    preferences = db.scalar(select(PaymentPreferences).where(
        PaymentPreferences.tenant_id == receiver_tenant_id,
    ))
    account = account_for(db, preferences.account_id, receiver_tenant_id) if preferences else None
    if not preferences or not preferences.mercadopago_enabled or not account or not can_create(account):
        raise CheckoutError("Mercado Pago do proprietário indisponível para compras de créditos.")
    if account.test_account and os.getenv("APP_ENV", "development") not in {"development", "test"}:
        raise CheckoutError("Conta Mercado Pago de teste não habilitada neste ambiente.")
    try:
        IntegrationCipher()
    except IntegrationSecretError:
        raise CheckoutError("Cofre de credenciais do Mercado Pago indisponível.") from None
    return owner.admin_user_id, receiver_tenant_id, account


def _record_event(
    db: Session,
    purchase: MercadoPagoCreditPurchase,
    event_type: str,
    event_key: str,
    details: dict | None = None,
) -> None:
    exists = db.scalar(select(MercadoPagoCreditPurchaseEvent.id).where(
        MercadoPagoCreditPurchaseEvent.purchase_id == purchase.id,
        MercadoPagoCreditPurchaseEvent.event_key == event_key,
    ))
    if exists:
        return
    db.add(MercadoPagoCreditPurchaseEvent(
        tenant_id=purchase.tenant_id,
        purchase_id=purchase.id,
        event_type=event_type,
        event_key=event_key,
        details=details,
    ))


def prepare_credit_purchase(
    db: Session,
    *,
    tenant_id: UUID,
    buyer_admin_id: UUID,
    package_id: UUID,
    idempotency_key: str,
) -> MercadoPagoCreditPurchase:
    _lock_finite_wallet(db, tenant_id)
    # The wallet row above serializes prepare calls per buyer. Keep this lookup
    # read-only: submit/reconciliation lock a purchase before they need the
    # wallet, so locking an existing purchase here would invert lock order.
    existing = db.scalar(select(MercadoPagoCreditPurchase).where(
        MercadoPagoCreditPurchase.tenant_id == tenant_id,
        MercadoPagoCreditPurchase.idempotency_key == idempotency_key,
    ))
    if existing:
        if existing.package_id != package_id:
            raise CheckoutError("Esta chave de solicitação pertence a outro pacote.")
        if existing.state == "prepared":
            from app.photographer_onboarding import require_credit_purchase_ready
            require_credit_purchase_ready(db, tenant_id=tenant_id, admin_id=existing.buyer_admin_id)
        return existing

    from app.photographer_onboarding import require_credit_purchase_ready
    require_credit_purchase_ready(db, tenant_id=tenant_id, admin_id=buyer_admin_id)

    package = db.scalar(select(PhotographerCreditPackage).where(
        PhotographerCreditPackage.id == package_id,
        PhotographerCreditPackage.active.is_(True),
    ))
    if (not package or package.price_cents is None or package.currency_code != "BRL"
            or package.price_cents < MINIMUM_TOTAL_CENTS):
        raise CheckoutError("Pacote indisponível para compra no Mercado Pago.")
    owner_admin_id, receiver_tenant_id, account = _resolve_owner_account(db)
    purchase_id = uuid4()
    purchase = MercadoPagoCreditPurchase(
        id=purchase_id,
        tenant_id=tenant_id,
        buyer_admin_id=buyer_admin_id,
        owner_admin_id=owner_admin_id,
        receiver_tenant_id=receiver_tenant_id,
        receiver_account_id=account.id,
        package_id=package.id,
        package_name=package.name,
        credit_quantity=package.credit_quantity,
        total_cents=package.price_cents,
        currency_code="BRL",
        idempotency_key=idempotency_key,
        external_reference=str(purchase_id),
        state="prepared",
        active=True,
        next_check_at=now() + timedelta(minutes=2),
    )
    db.add(purchase)
    db.flush()
    _record_event(db, purchase, "prepared", "prepared", {
        "package_id": str(package.id),
        "credit_quantity": package.credit_quantity,
        "total_cents": package.price_cents,
        "currency_code": "BRL",
    })
    audit(db, "credit_purchase.prepared", str(purchase.id), tenant_id=tenant_id)
    return purchase


def owned_credit_purchase(
    db: Session, tenant_id: UUID, purchase_id: UUID, *, lock: bool = False,
) -> MercadoPagoCreditPurchase:
    query = select(MercadoPagoCreditPurchase).where(
        MercadoPagoCreditPurchase.id == purchase_id,
        MercadoPagoCreditPurchase.tenant_id == tenant_id,
    ).execution_options(populate_existing=True)
    purchase = db.scalar(query.with_for_update() if lock else query)
    if not purchase:
        raise CheckoutError("Compra de créditos indisponível.")
    return purchase


def list_credit_purchases(db: Session, tenant_id: UUID, *, limit: int = 20) -> list[dict]:
    purchases = db.scalars(select(MercadoPagoCreditPurchase).where(
        MercadoPagoCreditPurchase.tenant_id == tenant_id,
    ).order_by(
        MercadoPagoCreditPurchase.created_at.desc(), MercadoPagoCreditPurchase.id.desc(),
    ).limit(max(1, min(limit, 100))))
    return [credit_purchase_payload(db, purchase) for purchase in purchases]


def active_credit_purchases(db: Session, tenant_id: UUID) -> list[dict]:
    purchases = db.scalars(select(MercadoPagoCreditPurchase).where(
        MercadoPagoCreditPurchase.tenant_id == tenant_id,
        MercadoPagoCreditPurchase.active.is_(True),
    ).order_by(MercadoPagoCreditPurchase.created_at.desc(), MercadoPagoCreditPurchase.id.desc()))
    return [credit_purchase_payload(db, purchase) for purchase in purchases]


def credit_purchase_payload(db: Session, purchase: MercadoPagoCreditPurchase) -> dict:
    account = account_for(db, purchase.receiver_account_id, purchase.receiver_tenant_id)
    qr_image = None
    if purchase.method == "pix" and purchase.state == "pending" and purchase.pix_copy_paste:
        from app.pix import PixCodeError, pix_qr_data_url

        try:
            qr_image = pix_qr_data_url(purchase.pix_copy_paste)
        except PixCodeError:
            pass
    return {
        "id": str(purchase.id),
        "package_id": str(purchase.package_id),
        "package_name": purchase.package_name,
        "credit_quantity": purchase.credit_quantity,
        "total_cents": purchase.total_cents,
        "currency_code": purchase.currency_code,
        "method": purchase.method,
        "state": purchase.state,
        "active": purchase.active,
        "public_key": account.public_key if account and purchase.state == "prepared" else None,
        "provider_order_id": purchase.provider_order_id,
        "provider_payment_id": purchase.provider_payment_id,
        "order_status": purchase.order_status,
        "order_detail": purchase.order_detail,
        "transaction_status": purchase.transaction_status,
        "transaction_detail": purchase.transaction_detail,
        "pix_copy_paste": purchase.pix_copy_paste if purchase.state == "pending" else None,
        "pix_qr_code": qr_image,
        "test_account": account.test_account if account else False,
        "review_status": purchase.review_status,
        "review_note": purchase.review_note,
        "created_at": purchase.created_at,
        "confirmed_at": purchase.confirmed_at,
    }


def _method_data(method: str, data) -> tuple[dict, dict]:
    email = str(getattr(data, "email", "") or "").strip()
    identification_number = str(getattr(data, "identification_number", "") or "")
    if (not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
            or not re.fullmatch(r"[0-9]{11}", identification_number)):
        raise CheckoutError("Confira o e-mail e o CPF do pagador.")
    if method == "pix":
        return {"id": "pix", "type": "bank_transfer"}, {
            "email": email,
            "identification": {"type": "CPF", "number": identification_number},
            "address": data.payer_address.model_dump(exclude_defaults=True),
        }
    token_value = getattr(data, "token", None)
    token = token_value.get_secret_value() if token_value is not None else None
    method_id = getattr(data, "payment_method_id", None)
    if not token or not method_id or not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", method_id):
        raise CheckoutError("Confira os dados do cartão no formulário seguro.")
    return {"id": method_id, "type": "credit_card", "token": token, "installments": 1}, {
        "email": email,
        "identification": {"type": "CPF", "number": identification_number},
        "address": data.payer_address.model_dump(exclude_defaults=True),
    }


def _configured_receiver_matches(db: Session, purchase: MercadoPagoCreditPurchase) -> MercadoPagoAccount:
    owner_admin_id, receiver_tenant_id, account = _resolve_owner_account(db)
    if (owner_admin_id != purchase.owner_admin_id or receiver_tenant_id != purchase.receiver_tenant_id
            or account.id != purchase.receiver_account_id):
        raise CheckoutError("A conta Mercado Pago do proprietário mudou. Prepare uma nova compra.")
    return account


def submit_credit_purchase(
    db: Session,
    *,
    tenant_id: UUID,
    purchase_id: UUID,
    method: str,
    data,
) -> MercadoPagoCreditPurchase:
    purchase = owned_credit_purchase(db, tenant_id, purchase_id, lock=True)
    if purchase.state != "prepared":
        return purchase
    from app.photographer_onboarding import require_credit_purchase_ready
    require_credit_purchase_ready(db, tenant_id=tenant_id, admin_id=purchase.buyer_admin_id)
    _lock_finite_wallet(db, tenant_id)
    if method not in {"credit_card", "pix"}:
        raise CheckoutError("Forma de pagamento indisponível.")
    account = _configured_receiver_matches(db, purchase)
    payment_method, payer = _method_data(method, data)
    provider = credential_provider(account)
    try:
        available_methods = provider.payment_methods()
    except (MercadoPagoError, IntegrationSecretError):
        raise CheckoutError("Não foi possível conferir a forma de pagamento. Tente novamente.") from None
    selected = next((item for item in available_methods if
                     item.get("id") == payment_method["id"]
                     and item.get("payment_type_id") == payment_method["type"]
                     and item.get("status") == "active"), None)
    if not selected:
        raise CheckoutError("Essa forma de pagamento está indisponível. Escolha outra e tente novamente.")
    try:
        provider_minimum = amount(selected["min_allowed_amount"])
    except (KeyError, CheckoutError):
        raise CheckoutError("Não foi possível conferir o valor mínimo do Mercado Pago.") from None
    if purchase.total_cents < max(MINIMUM_TOTAL_CENTS, provider_minimum):
        raise CheckoutError("O valor do pacote está abaixo do mínimo desta forma de pagamento.")

    cents = purchase.total_cents
    amount_text = f"{cents // 100}.{cents % 100:02d}"
    body = {
        "type": "online",
        "processing_mode": "automatic",
        "total_amount": amount_text,
        "external_reference": purchase.external_reference,
        "payer": payer,
        "transactions": {"payments": [{
            "amount": amount_text,
            "payment_method": payment_method,
        }]},
    }
    purchase.method = method
    purchase.state = "submitting"
    purchase.submitted_at = now()
    purchase.next_check_at = now() + timedelta(seconds=45)
    purchase.error_category = None
    _record_event(db, purchase, "submission_started", "submission_started", {"method": method})
    db.commit()  # Tentativa durável antes da rede; token, e-mail e CPF não são persistidos.

    try:
        response = provider.create(body, purchase.id)
    except (MercadoPagoError, IntegrationSecretError):
        response = None

    purchase = owned_credit_purchase(db, tenant_id, purchase_id, lock=True)
    if response is not None:
        resource_id = response.get("id")
        if (isinstance(resource_id, str) and re.fullmatch(r"ORD[A-Za-z0-9]{1,61}", resource_id)
                and response.get("external_reference") in (None, purchase.external_reference)):
            purchase.provider_order_id = resource_id
        apply_credit_order(db, purchase, response)
    elif purchase.state == "submitting":
        purchase.state = "verification_required"
        purchase.active = True
        purchase.error_category = "unknown_creation"
        purchase.next_check_at = now() + timedelta(seconds=45)
        _record_event(db, purchase, "verification_required", f"verify:{purchase.check_attempts}", {
            "reason": "unknown_creation",
        })
    return purchase


def _valid_order_resource(
    db: Session, purchase: MercadoPagoCreditPurchase, resource: dict,
) -> tuple[dict, object, str, object]:
    account = account_for(db, purchase.receiver_account_id, purchase.receiver_tenant_id)
    transactions = resource.get("transactions", {}).get("payments", [])
    if (not account or purchase.submitted_at is None or resource.get("type") != "online"
            or not isinstance(transactions, list) or len(transactions) != 1
            or resource.get("external_reference") != purchase.external_reference
            or amount(resource.get("total_amount")) != purchase.total_cents):
        raise CheckoutError("Resposta financeira inconsistente.")
    transaction = transactions[0]
    payment_method = transaction.get("payment_method", {})
    expected_type = "bank_transfer" if purchase.method == "pix" else "credit_card"
    if (amount(transaction.get("amount")) != purchase.total_cents
            or payment_method.get("type") != expected_type
            or (purchase.method == "pix" and payment_method.get("id") != "pix")
            or not re.fullmatch(r"PAY[A-Za-z0-9]{1,61}", str(transaction.get("id", "")))
            or not re.fullmatch(r"ORD[A-Za-z0-9]{1,61}", str(resource.get("id", "")))
            or (purchase.provider_order_id and purchase.provider_order_id != resource["id"])
            or ("user_id" in resource and str(resource["user_id"]) != account.seller_id)
            or ("live_mode" in resource and resource["live_mode"] != (not account.test_account))
            or ("currency_id" in resource and resource["currency_id"] != "BRL")
            or any(not isinstance(value, str) or len(value) > limit for value, limit in (
                (resource.get("status"), 32),
                (resource.get("status_detail"), 64),
                (transaction.get("status"), 32),
                (transaction.get("status_detail"), 64),
            ))):
        raise CheckoutError("Resposta financeira inconsistente.")
    updated_raw = resource.get("last_updated_date")
    if not isinstance(updated_raw, str):
        raise CheckoutError("Resposta financeira inconsistente.")
    updated = utc(datetime.fromisoformat(updated_raw))
    if updated is None:
        raise CheckoutError("Resposta financeira inconsistente.")
    state = external_state(resource, transaction)
    if state == "confirmed" and amount(resource.get("total_paid_amount")) != purchase.total_cents:
        raise CheckoutError("Valor pago divergente.")
    return account, transaction, state, updated


def _ensure_purchase_ledger(db: Session, purchase: MercadoPagoCreditPurchase) -> None:
    wallet = db.scalar(select(TenantCreditWallet).where(
        TenantCreditWallet.tenant_id == purchase.tenant_id,
    ).with_for_update())
    if wallet is None or wallet.mode != "finite":
        raise CheckoutError("Carteira do fotógrafo indisponível para confirmar créditos.")
    key = f"mercadopago-purchase:{purchase.id}"
    entry = db.scalar(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == purchase.tenant_id,
        PhotographerCreditEntry.idempotency_key == key,
    ).with_for_update())
    if entry is None:
        entry = PhotographerCreditEntry(
            tenant_id=purchase.tenant_id,
            entry_type="purchase",
            delta=purchase.credit_quantity,
            idempotency_key=key,
            package_id=purchase.package_id,
            actor_admin_id=purchase.buyer_admin_id,
            source_reference=str(purchase.id),
            description=f"Pacote {purchase.package_name} · Mercado Pago",
        )
        db.add(entry)
        db.flush()
    elif (entry.delta != purchase.credit_quantity or entry.package_id != purchase.package_id
          or entry.entry_type != "purchase" or entry.source_reference != str(purchase.id)):
        raise CheckoutError("Movimento de carteira divergente da compra.")
    purchase.ledger_entry_id = entry.id


def apply_credit_order(
    db: Session, purchase: MercadoPagoCreditPurchase, resource: dict,
) -> bool:
    """Aplica somente recurso Orders validado; a chamada ocorre sob lock da compra."""
    try:
        _account, transaction, state, updated = _valid_order_resource(db, purchase, resource)
    except (CheckoutError, KeyError, ValueError, TypeError, AttributeError):
        purchase.error_category = "inconsistent_resource"
        if not purchase.confirmed_at:
            purchase.state = "verification_required"
            purchase.active = True
        purchase.next_check_at = now() + timedelta(minutes=2)
        return False

    from app.tenancy import bind_financial_reconciliation
    bind_financial_reconciliation(db, purchase.tenant_id)
    previous_state = purchase.state
    previous_review = purchase.review_status
    # A webhook or reconciliation can repeat the exact provider snapshot after
    # the owner has already resolved its review. Treat equal timestamps as a
    # replay too, so it cannot reopen the same refund/chargeback review.
    if purchase.provider_updated_at and updated <= utc(purchase.provider_updated_at):
        return False
    if purchase.state == "refunded" and state != "refunded":
        return False
    if purchase.state in TERMINAL_UNPAID_STATES and state not in {
        "confirmed", *FINANCIAL_REVIEW_STATES,
    }:
        return False
    if purchase.confirmed_at and state not in {"confirmed", *FINANCIAL_REVIEW_STATES}:
        return False
    if purchase.state in {"partially_refunded", "charged_back"} and state not in FINANCIAL_REVIEW_STATES:
        return False

    purchase.provider_order_id = resource["id"]
    purchase.provider_payment_id = str(transaction["id"])
    purchase.provider_updated_at = updated
    purchase.order_status = resource["status"]
    purchase.order_detail = resource["status_detail"]
    purchase.transaction_status = transaction["status"]
    purchase.transaction_detail = transaction["status_detail"]
    purchase.error_category = None

    if state == "confirmed":
        purchase.confirmed_at = purchase.confirmed_at or now()
        _ensure_purchase_ledger(db, purchase)

    # O ledger e sua referência precisam existir antes de persistir state=confirmed,
    # pois a constraint exige que ambos sejam confirmados atomicamente.
    purchase.state = state
    purchase.active = state in ACTIVE_STATES
    purchase.next_check_at = now() + (timedelta(minutes=2) if purchase.active else timedelta(days=1))
    purchase.lease_until = None

    if state in FINANCIAL_REVIEW_STATES:
        old_rank = {"partially_refunded": 1, "refunded": 2, "charged_back": 3}.get(previous_state, 0)
        new_rank = {"partially_refunded": 1, "refunded": 2, "charged_back": 3}[state]
        if previous_review in {"none", "released", "restricted"} or new_rank > old_rank:
            purchase.review_status = "pending"
            purchase.reviewed_by_admin_id = None
            purchase.reviewed_at = None
            purchase.review_note = None

    if purchase.method == "pix" and state == "pending":
        qr = transaction.get("payment_method", {}).get("qr_code")
        purchase.pix_copy_paste = qr if isinstance(qr, str) and len(qr) <= 4096 else None
    elif state != "pending":
        purchase.pix_copy_paste = None

    if (previous_state != purchase.state or
            (state in FINANCIAL_REVIEW_STATES and previous_review != purchase.review_status)):
        event_type = purchase.state if purchase.state != "submitting" else "provider_updated"
        if event_type not in {
            "initiated", "pending", "processing", "confirmed", "rejected", "canceled", "expired",
            "refunded", "partially_refunded", "charged_back", "verification_required", "abandoned",
        }:
            event_type = "provider_updated"
        _record_event(db, purchase, event_type, f"provider:{updated.isoformat()}:{purchase.state}", {
            "state": purchase.state,
            "order_status": purchase.order_status,
            "order_detail": purchase.order_detail,
            "transaction_status": purchase.transaction_status,
            "transaction_detail": purchase.transaction_detail,
            "review_status": purchase.review_status,
        })
        audit(db, "credit_purchase.state_changed", f"{purchase.id}:{purchase.state}", tenant_id=purchase.tenant_id)
    return True


def _reconcile_locked(db: Session, purchase: MercadoPagoCreditPurchase) -> MercadoPagoCreditPurchase:
    # Compras já pagas continuam consultáveis manualmente para descobrir uma
    # reversão cujo webhook não chegou. O worker segue selecionando só ativas.
    if purchase.state in {"prepared", "abandoned"} or (not purchase.active and not purchase.confirmed_at):
        return purchase
    account = account_for(db, purchase.receiver_account_id, purchase.receiver_tenant_id)
    try:
        if not account:
            raise MercadoPagoError("receiver_account_missing")
        provider = credential_provider(account)
        if purchase.provider_order_id:
            resource = provider.get(purchase.provider_order_id)
        else:
            result = provider.search(
                reference=purchase.external_reference,
                begin_date=(utc(purchase.created_at) - timedelta(minutes=1)).isoformat(),
                end_date=now().isoformat(),
            )
            rows = result.get("data", [])
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise MercadoPagoError("invalid_response")
            candidates = [row for row in rows if row.get("external_reference") == purchase.external_reference]
            if len(candidates) != 1 or not isinstance(candidates[0].get("id"), str):
                raise MercadoPagoError("unknown_creation")
            resource = provider.get(candidates[0]["id"])
        if not apply_credit_order(db, purchase, resource) and purchase.error_category:
            raise MercadoPagoError(purchase.error_category)
    except (MercadoPagoError, IntegrationSecretError) as exc:
        purchase.error_category = getattr(exc, "category", "vault_unavailable")
        if isinstance(exc, MercadoPagoError) and exc.category == "unauthorized" and account:
            account.status = "unauthorized"
        if not purchase.confirmed_at and purchase.active:
            purchase.state = "verification_required"
        purchase.check_attempts += 1
        purchase.lease_until = None
        purchase.next_check_at = now() + timedelta(seconds=min(
            3600, 15 * 2 ** min(purchase.check_attempts, 8),
        ))
        _record_event(db, purchase, "verification_required", f"verify:{purchase.check_attempts}", {
            "reason": purchase.error_category,
        })
    return purchase


def reconcile_credit_purchase(
    db: Session, tenant_id: UUID, purchase_id: UUID,
) -> MercadoPagoCreditPurchase:
    purchase = owned_credit_purchase(db, tenant_id, purchase_id, lock=True)
    if purchase.state in {"prepared", "abandoned"}:
        return purchase
    return _reconcile_locked(db, purchase)


def process_next_mercadopago_credit_purchase(*, session_factory=None) -> bool:
    from app.auth import SessionLocal
    from app.tenancy import bind_financial_reconciliation, domain_session

    factory = session_factory or SessionLocal
    with domain_session(factory) as db:
        candidate = db.scalar(select(MercadoPagoCreditPurchase).where(
            MercadoPagoCreditPurchase.active.is_(True),
            MercadoPagoCreditPurchase.state.notin_(("prepared", "abandoned")),
            MercadoPagoCreditPurchase.next_check_at <= now(),
            or_(
                MercadoPagoCreditPurchase.lease_until.is_(None),
                MercadoPagoCreditPurchase.lease_until < now(),
            ),
            MercadoPagoCreditPurchase.receiver_tenant_id.in_(select(Tenant.id).where(Tenant.status == "active")),
        ).order_by(MercadoPagoCreditPurchase.next_check_at).with_for_update(skip_locked=True).limit(1))
        if not candidate:
            return False
        bind_financial_reconciliation(db, candidate.tenant_id)
        candidate.lease_until = now() + timedelta(seconds=90)
        purchase_id, buyer_tenant_id, claim = candidate.id, candidate.tenant_id, candidate.check_attempts
        db.commit()
    with domain_session(factory) as db:
        purchase = db.scalar(select(MercadoPagoCreditPurchase).where(
            MercadoPagoCreditPurchase.id == purchase_id,
            MercadoPagoCreditPurchase.tenant_id == buyer_tenant_id,
            MercadoPagoCreditPurchase.active.is_(True),
            MercadoPagoCreditPurchase.check_attempts == claim,
        ).with_for_update())
        if not purchase:
            return True
        bind_financial_reconciliation(db, purchase.tenant_id)
        _reconcile_locked(db, purchase)
        purchase.lease_until = None
        db.commit()
    return True


def resolve_credit_purchase_review(
    db: Session,
    *,
    owner_admin_id: UUID,
    purchase_id: UUID,
    decision: str,
    reason: str,
) -> MercadoPagoCreditPurchase:
    if not is_owner(db, owner_admin_id):
        raise CheckoutError("Acesso não autorizado.")
    normalized_reason = reason.strip()
    if decision not in {"release", "restrict"} or not normalized_reason or len(normalized_reason) > 500:
        raise CheckoutError("Informe uma decisão e justificativa válidas para a revisão.")
    purchase = db.scalar(select(MercadoPagoCreditPurchase).where(
        MercadoPagoCreditPurchase.id == purchase_id,
    ).with_for_update())
    if not purchase or purchase.review_status not in {"pending", "restricted"}:
        raise CheckoutError("Revisão financeira indisponível.")
    purchase.review_status = "released" if decision == "release" else "restricted"
    purchase.reviewed_by_admin_id = owner_admin_id
    purchase.reviewed_at = now()
    purchase.review_note = normalized_reason
    event_key = f"owner-review:{uuid4()}"
    _record_event(db, purchase, "owner_reviewed", event_key, {
        "decision": decision,
        "reason": normalized_reason,
        "actor_admin_id": str(owner_admin_id),
    })
    audit(db, "credit_purchase.owner_reviewed", f"{purchase.id}:{decision}", tenant_id=purchase.tenant_id)
    return purchase
