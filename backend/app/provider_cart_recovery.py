"""Reabertura manual de seleção; não confirma dinheiro nem cancela no provedor."""

import hashlib
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import require_active_owner
from app.auth import (
    AuditEvent,
    Client,
    DerivedGallery,
    GalleryClientState,
    GlobalPixSettings,
    InfinitePaySettings,
    ParentGallery,
    PaymentGroup,
    PhotoAsset,
    PhotoSelection,
    PriceRule,
    ProviderPayment,
    ProviderPaymentAttempt,
    ProviderPaymentReceipt,
    SaleOrder,
    SaleOrderItem,
    Tenant,
    audit,
    now,
)
from app.checkout import CheckoutError
from app.tenancy import require_admin_tenant
from app.unified_checkout import cart_payload

RECOVERY_EVENT = "provider_payment.cart_reopened"
RECOVERABLE_STATES = frozenset(("awaiting_payment", "verification_required"))


class CartRecoveryError(ValueError):
    """Conflito recuperável pela interface, sem efeito parcial."""


def _rows(db, model, *criteria):
    return list(db.scalars(select(model).where(*criteria).order_by(model.id)
                           .with_for_update().execution_options(populate_existing=True)))


def _records(rows):
    return [{column.name: getattr(row, column.name) for column in row.__table__.columns} for row in rows]


def _perform(db, actor_id, payment_id, *, expected_revision, expected_fingerprint=None,
             decision_id=None, reason=None, acknowledge_remote_checkout=False, preview=False):
    tenant = require_admin_tenant(db, actor_id)
    tenant_id = tenant.id
    require_active_owner(db, tenant_id)
    # Compatível com KEY SHARE da FK de um confirmador que já detém Client.
    db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update(key_share=True)
              .execution_options(populate_existing=True))
    owner = db.scalar(select(ProviderPayment.client_id).where(
        ProviderPayment.tenant_id == tenant_id, ProviderPayment.id == payment_id,
        ProviderPayment.provider == "infinitepay"))
    if owner is None:
        raise LookupError("Compra indisponível.")
    client = db.scalar(select(Client).where(Client.id == owner, Client.tenant_id == tenant_id)
                       .with_for_update().execution_options(populate_existing=True))
    payment = db.scalar(select(ProviderPayment).where(
        ProviderPayment.tenant_id == tenant_id, ProviderPayment.id == payment_id,
        ProviderPayment.client_id == owner).with_for_update().execution_options(populate_existing=True))
    if client is None or payment is None:
        raise LookupError("Compra indisponível.")
    previous = _rows(db, AuditEvent, AuditEvent.tenant_id == tenant_id,
                     AuditEvent.event == RECOVERY_EVENT,
                     AuditEvent.subject.startswith(f"{payment.id}:"))
    if not preview:
        reason = reason.strip() if isinstance(reason, str) else ""
        if (not acknowledge_remote_checkout or not isinstance(decision_id, UUID)
                or not 3 <= len(reason) <= 100
                or any(ord(character) < 32 or ord(character) == 127 for character in reason)):
            raise CartRecoveryError("Confirme a decisão e informe um motivo de 3 a 100 caracteres.")
    if previous:
        parts = previous[0].subject.split(":", 5)
        if (not preview and len(previous) == 1 and len(parts) == 6
                and parts[1] == str(decision_id) and parts[2] == str(actor_id) and parts[5] == reason):
            return {"payment_id": str(payment.id), "client_id": str(owner),
                    "already_reopened": True, "resume_path": "/library/cart"}
        raise CartRecoveryError("O carrinho desta compra já foi reaberto. Atualize o painel.")
    if payment.state not in RECOVERABLE_STATES or payment.revision_number != expected_revision:
        raise CartRecoveryError("A compra mudou ou não está disponível para reabertura. Atualize o painel.")
    attempts = _rows(db, ProviderPaymentAttempt, ProviderPaymentAttempt.tenant_id == tenant_id,
                     ProviderPaymentAttempt.payment_id == payment.id)
    receipts = _rows(db, ProviderPaymentReceipt, ProviderPaymentReceipt.tenant_id == tenant_id,
                     ProviderPaymentReceipt.payment_id == payment.id)
    orders = _rows(db, SaleOrder, SaleOrder.tenant_id == tenant_id,
                   SaleOrder.provider_payment_id == payment.id)
    items = _rows(db, SaleOrderItem, SaleOrderItem.tenant_id == tenant_id,
                  SaleOrderItem.sale_order_id.in_([order.id for order in orders]))
    if (payment.provider_transaction_nsu or payment.confirmed_at
            or any(row.state in {"queued", "processing", "verified"} for row in receipts)
            or len(attempts) != 1
            or attempts[0].state != ("accepted" if payment.state == "awaiting_payment" else "unknown")
            or not orders or not items
            or sum(order.total_cents for order in orders) != payment.total_cents
            or sum(item.unit_price_cents for item in items) != payment.total_cents
            or any(order.client_id != owner or order.payment_status != "pending"
                   or order.frozen_at is None or order.assets_removed_at is not None
                   or order.confirmed_at or order.delivery_album_url or order.payment_group_id
                   or order.payment_required_snapshot is not True for order in orders)):
        raise CartRecoveryError("Há confirmação, verificação em curso ou histórico incompatível com reabertura.")
    if any(sum(item.unit_price_cents for item in items if item.sale_order_id == order.id)
           != order.total_cents for order in orders):
        raise CartRecoveryError("Os valores da compra não correspondem ao histórico. Confira antes de reabrir.")
    wanted = {(str(order.parent_gallery_id or order.derived_gallery_id), str(item.photo_asset_id_snapshot))
              for order in orders for item in items if item.sale_order_id == order.id}
    if len(wanted) != len(items):
        raise CartRecoveryError("O histórico de fotos exige conferência antes da reabertura.")
    selections = _rows(db, PhotoSelection, PhotoSelection.tenant_id == tenant_id,
                       PhotoSelection.client_id == owner)
    groups = _rows(db, PaymentGroup, PaymentGroup.tenant_id == tenant_id,
                  PaymentGroup.client_id == owner, PaymentGroup.state == "draft")
    gallery_ids = {row.derived_gallery_id for row in [*orders, *selections] if row.derived_gallery_id}
    galleries = _rows(db, DerivedGallery, DerivedGallery.tenant_id == tenant_id,
                      DerivedGallery.id.in_(gallery_ids))
    parent_ids = {row.parent_gallery_id for row in [*orders, *selections, *galleries] if row.parent_gallery_id}
    parents = _rows(db, ParentGallery, ParentGallery.tenant_id == tenant_id, ParentGallery.id.in_(parent_ids))
    states = _rows(db, GalleryClientState, GalleryClientState.tenant_id == tenant_id,
                   GalleryClientState.client_id == owner)
    photo_ids = {row.photo_asset_id_snapshot for row in items} | {row.photo_asset_id for row in selections}
    assets = _rows(db, PhotoAsset, PhotoAsset.tenant_id == tenant_id, PhotoAsset.id.in_(photo_ids))
    configs = [*_rows(db, GlobalPixSettings, GlobalPixSettings.tenant_id == tenant_id),
               *_rows(db, InfinitePaySettings, InfinitePaySettings.tenant_id == tenant_id),
               *_rows(db, PriceRule, PriceRule.tenant_id == tenant_id)]
    before = [_records(rows) for rows in
              ([payment], attempts, receipts, orders, items, selections, groups, galleries, parents, states, assets, configs)]
    old_state, old_revision = payment.state, payment.revision_number
    payment.state = "exception"
    payment.revision_number += 1
    payment.updated_at = now()
    for order in orders:
        order.payment_status = "cancelled"
        for item in (item for item in items if item.sale_order_id == order.id):
            if not any(row.photo_asset_id == item.photo_asset_id_snapshot
                       and row.parent_gallery_id == order.parent_gallery_id
                       and row.derived_gallery_id == order.derived_gallery_id for row in selections):
                selection = PhotoSelection(tenant_id=tenant_id, client_id=owner,
                    parent_gallery_id=order.parent_gallery_id, derived_gallery_id=order.derived_gallery_id,
                    photo_asset_id=item.photo_asset_id_snapshot)
                db.add(selection)
                selections.append(selection)
    db.flush()
    try:
        cart = cart_payload(db, client)
    except CheckoutError as exc:
        raise CartRecoveryError("O carrinho não pode ser recuperado integralmente. Confira acesso, prazo e preços.") from exc
    visible = {(group["gallery_id"], item["id"]) for group in cart["groups"] for item in group["items"]}
    if not wanted.issubset(visible) or not cart["can_prepare"] or cart["card_payment"]:
        raise CartRecoveryError("As fotos ou os meios de pagamento não estão todos disponíveis. Nenhuma foto foi liberada.")
    fingerprint = hashlib.sha256(json.dumps({"before": before, "cart": {
        key: cart[key] for key in ("cart_revision", "quantity", "total_cents", "card_available", "pix_available")
    }}, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
    if not preview and fingerprint != expected_fingerprint:
        raise CartRecoveryError("O carrinho ou a configuração mudou. Confira uma nova prévia.")
    if not preview:
        audit(db, RECOVERY_EVENT,
              f"{payment.id}:{decision_id}:{actor_id}:{old_state}:{old_revision}:{reason}", tenant_id=tenant_id)
        db.flush()
    return {"payment_id": str(payment.id), "client_id": str(owner), "already_reopened": False,
            "revision": old_revision, "fingerprint": fingerprint, "restored_quantity": len(wanted),
            "quantity": cart["quantity"], "total_cents": cart["total_cents"],
            "previous_total_cents": payment.total_cents, "card_available": cart["card_available"],
            "pix_available": cart["pix_available"], "resume_path": "/library/cart"}


def preview_cart_recovery(db: Session, actor_id: UUID, payment_id: UUID, *, expected_revision: int):
    """A prévia nunca persiste restauração nem auditoria; o chamador detém a sessão."""
    with db.begin_nested() as transaction:
        result = _perform(db, actor_id, payment_id, expected_revision=expected_revision, preview=True)
        transaction.rollback()
    db.expire_all()
    return result


def reopen_payment_cart(db: Session, actor_id: UUID, payment_id: UUID, *, expected_revision: int,
                        expected_fingerprint: str, decision_id: UUID, reason: str,
                        acknowledge_remote_checkout: bool):
    """Um único commit pertence à rota; erros revertem inclusive efeitos tentativos."""
    try:
        return _perform(db, actor_id, payment_id, expected_revision=expected_revision,
                        expected_fingerprint=expected_fingerprint, decision_id=decision_id,
                        reason=reason, acknowledge_remote_checkout=acknowledge_remote_checkout)
    except Exception:
        db.rollback()
        raise
