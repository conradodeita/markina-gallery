"""Exceção autorizada pelo titular em 21/10/2026; não cancela links remotos.

Executar no runtime API existente, por stdin ou PYTHONPATH=backend. O padrão é
simular com rollback. Nenhuma rota do produto importa esta ferramenta.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

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
    SessionLocal,
    Tenant,
    audit,
    now,
)
from app.checkout import CheckoutError
from app.tenancy import TenantContextError, require_admin_tenant
from app.unified_checkout import cart_payload, prepare_group

TENANT_ID = UUID("1531dbaa-215c-4583-b1f0-77d185ad7f07")
TARGETS = {
    UUID("eae11005-d1f2-46f4-861e-90a3ff3a923d"): (
        15400, "awaiting_payment", 22, UUID("8581cfe2-f13d-41d1-864d-1b002df10e28")),
    UUID("e2194ce5-8fd2-47bc-a6da-53d182b3687a"): (
        5, "verification_required", 1, UUID("7c1869e8-8ccf-46bc-a235-527dcbcb4e64")),
    UUID("11f18369-3b0a-4337-8549-685e5b2ce195"): (
        5, "verification_required", 1, UUID("2ccc9211-6857-42b2-953e-8f2b494142c9")),
}
OPERATION = "IP_RECOVERY_20261021_V1"
EVENT = "provider_payment.owner_recovery"
BASE_SHA = "5446cf4d7328ef6283ebfab50b5d1976d561fc8d"


class RecoveryError(ValueError):
    pass


def _rows(db, model, *criteria):
    return list(db.scalars(select(model).where(*criteria).order_by(model.id)
                           .with_for_update().execution_options(populate_existing=True)))


def _record(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str,
                                    separators=(",", ":")).encode()).hexdigest()


def _before_file(path, before, *, apply):
    """Pré-imagem minimizada, sem URLs, PIX, contato ou nomes de fotos."""
    if path is None:
        return
    path = Path(path)
    if path.is_symlink():
        raise RecoveryError("Arquivo de pré-imagem inválido.")
    if path.exists():
        if os.name != "nt" and (path.stat().st_mode & 0o777 != 0o600
                                or path.stat().st_uid != os.geteuid()):
            raise RecoveryError("Pré-imagem exige proprietário atual e permissão 0600.")
        if json.loads(path.read_text(encoding="utf-8")) != before:
            raise RecoveryError("Pré-imagem diverge; refaça a simulação em outro arquivo.")
    elif apply:
        raise RecoveryError("Pré-imagem da simulação ausente.")
    else:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(before, stream, sort_keys=True, ensure_ascii=False)


def _recover(db, actor_admin_id, *, apply, expected_fingerprint, before_path):
    require_active_owner(db, TENANT_ID)
    # NO KEY UPDATE serializa preparações, mas permite o KEY SHARE da FK de
    # um recibo cujo confirmador já detém o lock do cliente. FOR UPDATE aqui
    # criaria um ciclo tenant -> cliente -> FK tenant durante a confirmação.
    db.scalar(select(Tenant).where(Tenant.id == TENANT_ID).with_for_update(key_share=True)
              .execution_options(populate_existing=True))
    if require_admin_tenant(db, actor_admin_id).id != TENANT_ID:
        raise RecoveryError("Administrador não pertence à conta autorizada.")
    if len(TARGETS) != 3:
        raise RecoveryError("Inventário exige exatamente três alvos.")
    previous = _rows(db, AuditEvent, AuditEvent.tenant_id == TENANT_ID,
                     AuditEvent.event == EVENT,
                     AuditEvent.subject.startswith(f"{OPERATION}:"))
    if previous:
        if len(previous) != 3 or {row.subject.split(":")[1] for row in previous} != {str(key) for key in TARGETS}:
            raise RecoveryError("Auditoria parcial ou divergente exige conferência.")
        return {"operation": OPERATION, "already_applied": True,
                "payments": sorted(str(key) for key in TARGETS), "mutated": False}

    client_ids = sorted(set(db.scalars(select(ProviderPayment.client_id).where(
        ProviderPayment.tenant_id == TENANT_ID, ProviderPayment.id.in_(TARGETS)))), key=str)
    clients = _rows(db, Client, Client.tenant_id == TENANT_ID, Client.id.in_(client_ids))
    if len(clients) != len(client_ids):
        raise RecoveryError("Clientes indisponíveis.")
    payments = _rows(db, ProviderPayment, ProviderPayment.tenant_id == TENANT_ID,
                     ProviderPayment.id.in_(TARGETS))
    if {row.id for row in payments} != set(TARGETS):
        raise RecoveryError("Alvos ausentes ou de outra conta.")
    attempts = _rows(db, ProviderPaymentAttempt, ProviderPaymentAttempt.tenant_id == TENANT_ID,
                     ProviderPaymentAttempt.payment_id.in_(TARGETS))
    receipts = _rows(db, ProviderPaymentReceipt, ProviderPaymentReceipt.tenant_id == TENANT_ID,
                     ProviderPaymentReceipt.payment_id.in_(TARGETS))
    orders = _rows(db, SaleOrder, SaleOrder.tenant_id == TENANT_ID,
                   SaleOrder.provider_payment_id.in_(TARGETS))
    items = _rows(db, SaleOrderItem, SaleOrderItem.tenant_id == TENANT_ID,
                  SaleOrderItem.sale_order_id.in_([row.id for row in orders]))
    selections = _rows(db, PhotoSelection, PhotoSelection.tenant_id == TENANT_ID,
                       PhotoSelection.client_id.in_(client_ids))
    groups = _rows(db, PaymentGroup, PaymentGroup.tenant_id == TENANT_ID,
                  PaymentGroup.client_id.in_(client_ids), PaymentGroup.state == "draft")
    gallery_ids = {row.derived_gallery_id for row in [*orders, *selections] if row.derived_gallery_id}
    galleries = _rows(db, DerivedGallery, DerivedGallery.tenant_id == TENANT_ID,
                      DerivedGallery.id.in_(gallery_ids))
    parent_ids = {row.parent_gallery_id for row in [*orders, *selections, *galleries] if row.parent_gallery_id}
    parents = _rows(db, ParentGallery, ParentGallery.tenant_id == TENANT_ID, ParentGallery.id.in_(parent_ids))
    client_states = _rows(db, GalleryClientState, GalleryClientState.tenant_id == TENANT_ID,
                          GalleryClientState.client_id.in_(client_ids))
    photo_ids = {row.photo_asset_id_snapshot for row in items} | {row.photo_asset_id for row in selections}
    assets = _rows(db, PhotoAsset, PhotoAsset.tenant_id == TENANT_ID, PhotoAsset.id.in_(photo_ids))
    configs = [*_rows(db, GlobalPixSettings, GlobalPixSettings.tenant_id == TENANT_ID),
               *_rows(db, InfinitePaySettings, InfinitePaySettings.tenant_id == TENANT_ID),
               *_rows(db, PriceRule, PriceRule.tenant_id == TENANT_ID)]
    for payment in payments:
        expected_amount, expected_state, expected_count, expected_client = TARGETS[payment.id]
        related = [order for order in orders if order.provider_payment_id == payment.id]
        related_items = [item for item in items if item.sale_order_id in {o.id for o in related}]
        attempt = [row for row in attempts if row.payment_id == payment.id]
        if (payment.state != expected_state or payment.total_cents != expected_amount
                or payment.client_id != expected_client or len(related_items) != expected_count
                or payment.provider_transaction_nsu or payment.confirmed_at
                or any(row.state == "verified" for row in receipts if row.payment_id == payment.id)
                or len(attempt) != 1
                or attempt[0].state != ("accepted" if expected_state == "awaiting_payment" else "unknown")
                or not related or not related_items
                or sum(row.total_cents for row in related) != expected_amount
                or sum(row.unit_price_cents for row in related_items) != expected_amount
                or any(order.client_id != payment.client_id or order.payment_status != "pending"
                       or order.frozen_at is None or order.assets_removed_at is not None
                       or order.confirmed_at or order.delivery_album_url or order.payment_group_id
                       for order in related)):
            raise RecoveryError("Estado financeiro ou snapshot diverge do lote autorizado.")

    fingerprint = _hash([[_record(row) for row in rows] for rows in
                         (payments, attempts, receipts, orders, items, selections, groups, configs,
                          galleries, parents, client_states, assets)])
    if apply and expected_fingerprint != fingerprint:
        raise RecoveryError("Fingerprint obsoleto; refaça a simulação.")
    before = {"operation": OPERATION, "tenant_id": str(TENANT_ID),
              "actor_admin_id": str(actor_admin_id), "fingerprint": fingerprint,
              "payments": [{"id": str(p.id), "state": p.state, "revision": p.revision_number,
                            "total_cents": p.total_cents} for p in payments],
              "orders": [{"id": str(o.id), "payment_status": o.payment_status} for o in orders],
              "selection_ids": [str(row.id) for row in selections]}
    _before_file(before_path, before, apply=apply)
    previous_states = {p.id: (p.state, p.revision_number) for p in payments}
    for payment in payments:
        payment.state = "exception"
        payment.revision_number += 1
        payment.updated_at = now()
    for order in orders:
        order.payment_status = "cancelled"
        for item in (item for item in items if item.sale_order_id == order.id):
            exists = any(row.client_id == order.client_id
                         and row.photo_asset_id == item.photo_asset_id_snapshot
                         and row.parent_gallery_id == order.parent_gallery_id
                         and row.derived_gallery_id == order.derived_gallery_id for row in selections)
            if not exists:
                selection = PhotoSelection(tenant_id=TENANT_ID, client_id=order.client_id,
                    parent_gallery_id=order.parent_gallery_id, derived_gallery_id=order.derived_gallery_id,
                    photo_asset_id=item.photo_asset_id_snapshot)
                db.add(selection)
                selections.append(selection)
    db.flush()
    new_groups = {}
    carts = []
    for client in clients:
        try:
            group = prepare_group(db, client)
            cart = cart_payload(db, client)
        except CheckoutError as exc:
            raise RecoveryError("Seleção ou PIX inelegível; lote revertido.") from exc
        expected_photos = {item.photo_asset_id_snapshot for order in orders if order.client_id == client.id
                           for item in items if item.sale_order_id == order.id}
        displayed = {UUID(item["id"]) for row in cart["groups"] for item in row["items"]}
        if (not expected_photos.issubset(displayed) or not cart["can_prepare"]
                or not cart["pix_available"] or cart["card_payment"]):
            raise RecoveryError("Carrinho não recuperável por completo; lote revertido.")
        new_groups[client.id] = group.id
        carts.append({"client_id": str(client.id), "quantity": cart["quantity"],
                      "restored_quantity": len(expected_photos), "total_cents": cart["total_cents"],
                      "pix_available": cart["pix_available"], "card_available": cart["card_available"],
                      "pix_group_id": str(group.id), "resume_path": "/library/cart"})
    for payment in payments:
        previous_state, revision = previous_states[payment.id]
        subject = (f"{OPERATION}:{payment.id}:{actor_admin_id}:{previous_state}:"
                   f"{revision}:{new_groups[payment.client_id]}")
        audit(db, EVENT, subject, tenant_id=TENANT_ID)
    db.flush()
    return {"operation": OPERATION, "already_applied": False, "fingerprint": fingerprint,
            "remote_checkout_state": "unknown", "before": before, "carts": carts}


def execute(db, actor_admin_id, *, apply=False, expected_fingerprint=None, before_path=None):
    """Dona da transação: simulação e qualquer erro sempre fazem rollback."""
    try:
        result = _recover(db, actor_admin_id, apply=apply,
                          expected_fingerprint=expected_fingerprint, before_path=before_path)
        if apply and not result["already_applied"]:
            db.commit()
        else:
            db.rollback()
        result["mode"] = "apply" if apply else "dry-run"
        return result
    except Exception:
        db.rollback()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    parser.add_argument("--actor-admin-id", type=UUID, required=True)
    parser.add_argument("--before-file", type=Path, required=True)
    parser.add_argument("--expected-fingerprint")
    parser.add_argument("--acknowledge-remote-link-may-remain-payable", action="store_true")
    args = parser.parse_args()
    if args.mode == "apply" and (not args.expected_fingerprint
                               or not args.acknowledge_remote_link_may_remain_payable):
        parser.error("Aplicação exige fingerprint e reconhecimento do risco do link remoto.")
    if os.getenv("APP_VERSION") not in {BASE_SHA, BASE_SHA[:8]}:
        parser.error("Runtime diverge da base inventariada; recuse a operação.")
    try:
        with SessionLocal() as db:
            result = execute(db, args.actor_admin_id, apply=args.mode == "apply",
                             expected_fingerprint=args.expected_fingerprint,
                             before_path=args.before_file)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    except (ValueError, SQLAlchemyError, TenantContextError, OSError) as exc:
        message = str(exc) if isinstance(exc, RecoveryError) else "Operação revertida; diagnóstico protegido necessário."
        print(json.dumps({"success": False, "error": type(exc).__name__, "message": message}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
