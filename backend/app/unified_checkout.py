"""Carrinho autorizado e transações de um PIX para vários pedidos. Sem commits internos."""

import hashlib
import json
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    ParentGallery,
    PaymentCommunication,
    PaymentGroup,
    PhotoFolder,
    PhotoSelection,
    SaleOrder,
    SaleOrderItem,
    audit,
    expired,
    now,
)
from app.checkout import (
    CheckoutError,
    _checkout_material,
    _synchronize_order,
    lock_client_commerce,
    selected_photos,
)
from app.global_pix import checkout_pix
from app.notification_events import record_payment_event
from app.pix import PixCodeError, normalize_pix_copy_paste, pix_qr_data_url
from app.private_membership import operational_galleries_for_client


def communication_join():
    return or_(
        PaymentCommunication.sale_order_id == SaleOrder.id,
        PaymentCommunication.payment_group_id == SaleOrder.payment_group_id,
    )


def communications_for_orders(db, orders):
    ids = [order.id for order in orders]
    group_ids = {order.payment_group_id for order in orders if order.payment_group_id}
    result = {}
    rows = db.scalars(
        select(PaymentCommunication)
        .where(
            or_(
                PaymentCommunication.sale_order_id.in_(ids),
                PaymentCommunication.payment_group_id.in_(group_ids),
            )
        )
        .order_by(PaymentCommunication.created_at)
    )
    by_group = {}
    for row in rows:
        result[row.sale_order_id] = row
        if row.payment_group_id:
            by_group[row.payment_group_id] = row
    for order in orders:
        if order.payment_group_id in by_group:
            result[order.id] = by_group[order.payment_group_id]
    return result


def _materials(db, client):
    result = []
    selected_ids = set(
        db.scalars(
            select(PhotoSelection.derived_gallery_id).where(PhotoSelection.client_id == client.id)
        )
    )
    for gallery in sorted(
        operational_galleries_for_client(db, client_id=client.id), key=lambda row: str(row.id)
    ):
        if gallery.id not in selected_ids:
            continue
        parent = db.get(ParentGallery, gallery.parent_gallery_id)
        # Não revelar seleções cujo acesso foi revogado.
        if not parent or parent.lifecycle_status != "active":
            continue
        error = None
        material = None
        try:
            material = _checkout_material(db, gallery=gallery, client=client, resolve_pix=False)
            if gallery.selection_expires_at and expired(gallery.selection_expires_at):
                error = "O prazo desta galeria expirou. Remova a seleção ou solicite reabertura."
        except CheckoutError as exc:
            error = str(exc)
        result.append((gallery, parent, material, error))
    return result


def cart_payload(db: Session, client: Client):
    groups = []
    for gallery, parent, material, error in _materials(db, client):
        items = []
        quantity = db.scalar(
            select(func.count(PhotoSelection.id)).where(
                PhotoSelection.client_id == client.id,
                PhotoSelection.derived_gallery_id == gallery.id,
            )
        )
        photos = material[1] if material else selected_photos(db, gallery=gallery, client=client)[1]
        folders = (
            material[5]
            if material
            else {
                folder.id: folder
                for folder in db.scalars(
                    select(PhotoFolder).where(
                        PhotoFolder.id.in_({photo.folder_id for photo in photos})
                    )
                )
            }
        )
        for photo in sorted(
            photos,
            key=lambda row: (folders[row.folder_id].position, str(row.folder_id), row.filename),
        ):
            folder = folders.get(photo.folder_id)
            items.append(
                {
                    "id": str(photo.id),
                    "name": photo.display_name or photo.filename,
                    "folder_name": folder.name if folder else None,
                    "preview_url": f"/gallery/{gallery.id}/photos/{photo.id}/preview",
                }
            )
        legacy = db.scalar(
            select(SaleOrder.id).where(
                SaleOrder.derived_gallery_id == gallery.id,
                SaleOrder.client_id == client.id,
                SaleOrder.frozen_at.is_(None),
                SaleOrder.assets_removed_at.is_(None),
                SaleOrder.payment_status == "pending",
                SaleOrder.checkout_key.is_not(None),
                SaleOrder.payment_group_id.is_(None),
            )
        )
        groups.append(
            {
                "gallery_id": str(gallery.id),
                "parent_gallery_id": str(parent.id),
                "legacy_review_url": f"/gallery/{gallery.id}?mode=legacy-review"
                if legacy
                else None,
                "name": parent.name,
                "private_name": gallery.name,
                "browse_url": f"/gallery/{gallery.id}",
                "quantity": quantity,
                "selection_expires_at": gallery.selection_expires_at.isoformat()
                if gallery.selection_expires_at
                else None,
                "items": items,
                "error": error,
                "total_cents": material[3].quote.total_cents if material else None,
            }
        )
    valid = bool(groups) and all(not group["error"] for group in groups)
    return {
        "groups": groups,
        "quantity": sum(group["quantity"] for group in groups),
        "total_cents": sum(group["total_cents"] for group in groups) if valid else None,
        "can_prepare": valid,
    }


def _fingerprint(materials):
    values = [
        {
            "gallery": str(gallery.id),
            "items": sorted(str(photo.id) for photo in material[1]),
            "quote": material[3].snapshot,
            "total": material[3].quote.total_cents,
            "message": parent.sales_message,
            "expires": gallery.selection_expires_at.isoformat()
            if gallery.selection_expires_at
            else None,
        }
        for gallery, parent, material, _ in materials
    ]
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()


def _valid_materials(db, client):
    materials = _materials(db, client)
    if not materials:
        raise CheckoutError("O carrinho está vazio.")
    for gallery, _parent, _material, error in materials:
        lock_client_commerce(db, gallery_id=gallery.id, client_id=client.id)
        if error:
            raise CheckoutError(error)
    return materials


def _check_amount(code, total):
    try:
        code = normalize_pix_copy_paste(code)
    except PixCodeError as exc:
        raise CheckoutError(str(exc)) from exc
    if not code:
        raise CheckoutError("O PIX desta compra está indisponível. Contate o fotógrafo.")
    position = 0
    while position < len(code):
        tag, size = code[position : position + 2], int(code[position + 2 : position + 4])
        value = code[position + 4 : position + 4 + size]
        if tag == "54":
            try:
                amount = Decimal(value)
            except InvalidOperation as exc:
                raise CheckoutError("O valor do PIX é inválido. Contate o fotógrafo.") from exc
            if not amount.is_finite() or amount * 100 != total:
                raise CheckoutError(
                    "O valor fixo do PIX não corresponde ao carrinho. Contate o fotógrafo."
                )
        position += 4 + size


def prepare_group(db: Session, client: Client):
    db.scalar(select(Client.id).where(Client.id == client.id).with_for_update())
    materials = _valid_materials(db, client)
    revision = _fingerprint(materials)
    group = db.scalar(
        select(PaymentGroup)
        .where(PaymentGroup.client_id == client.id, PaymentGroup.state == "draft")
        .with_for_update()
    )
    drafts = {
        order.derived_gallery_id: order
        for order in db.scalars(
            select(SaleOrder).where(
                SaleOrder.client_id == client.id,
                SaleOrder.payment_status == "pending",
                SaleOrder.frozen_at.is_(None),
                SaleOrder.assets_removed_at.is_(None),
                SaleOrder.checkout_key.is_not(None),
            )
        )
    }
    if group is None:
        try:
            settings = checkout_pix(db)
        except PixCodeError as exc:
            raise CheckoutError(str(exc)) from exc
        group = PaymentGroup(
            client_id=client.id,
            state="draft",
            revision=revision,
            total_cents=0,
            pix_copy_paste_snapshot=settings.copy_paste,
            pix_instructions_snapshot=settings.instructions,
            pix_configuration_snapshot={
                "configuration_id": str(settings.id),
                "version": settings.version,
                "receiver_name": settings.receiver_name,
                "receiver_city": settings.receiver_city,
            },
        )
    for gallery, _parent, _material, _error in materials:
        draft = drafts.get(gallery.id)
        if (
            draft
            and draft.pix_copy_paste_snapshot
            and (
                draft.pix_copy_paste_snapshot != group.pix_copy_paste_snapshot
                or draft.pix_instructions_snapshot != group.pix_instructions_snapshot
            )
        ):
            raise CheckoutError(
                "Há um pagamento iniciado com outro PIX. Retome esse pedido na galeria antes de combinar a compra."
            )
    group.total_cents = sum(material[3].quote.total_cents for _, _, material, _ in materials)
    _check_amount(group.pix_copy_paste_snapshot, group.total_cents)
    group.revision = revision
    db.add(group)
    db.flush()
    # Um rascunho que deixou de participar não pode continuar vinculado ao total.
    current_ids = {gallery.id for gallery, _, _, _ in materials}
    for draft in drafts.values():
        if draft.payment_group_id == group.id and draft.derived_gallery_id not in current_ids:
            draft.payment_group_id = None
    for gallery, _parent, material, _error in materials:
        order = drafts.get(gallery.id) or SaleOrder(
            derived_gallery_id=gallery.id,
            client_id=client.id,
            total_cents=0,
            checkout_key=str(uuid4()),
        )
        _synchronize_order(db, order=order, gallery=gallery, client=client, material=material)
        order.payment_group_id = group.id
        if not order.pix_copy_paste_snapshot:
            order.pix_copy_paste_snapshot = group.pix_copy_paste_snapshot
            order.pix_configuration_snapshot = group.pix_configuration_snapshot
            order.pix_instructions_snapshot = group.pix_instructions_snapshot
    db.flush()
    audit(db, "payment_group.prepared", str(group.id))
    return group


def group_payload(group):
    return {
        "id": str(group.id),
        "revision": group.revision,
        "state": group.state,
        "total_cents": group.total_cents,
        "pix_copy_paste": group.pix_copy_paste_snapshot,
        "pix_qr_code": pix_qr_data_url(group.pix_copy_paste_snapshot),
        "pix_instructions": group.pix_instructions_snapshot,
        "receiver_name": group.pix_configuration_snapshot.get("receiver_name"),
    }


def payment_scopes(db, group_ids):
    """Escopos completos em duas consultas, inclusive em atalhos filtrados."""
    if not group_ids:
        return {}
    result = {
        group.id: {"id": str(group.id), "total_cents": group.total_cents, "galleries": []}
        for group in db.scalars(select(PaymentGroup).where(PaymentGroup.id.in_(group_ids)))
    }
    for order in db.scalars(
        select(SaleOrder)
        .where(SaleOrder.payment_group_id.in_(group_ids))
        .order_by(SaleOrder.parent_gallery_name_snapshot, SaleOrder.id)
    ):
        result[order.payment_group_id]["galleries"].append(
            {
                "order_id": str(order.id),
                "name": order.parent_gallery_name_snapshot,
                "total_cents": order.total_cents,
            }
        )
    return result


def payment_scope(db, communication):
    if not communication.payment_group_id:
        return None
    return payment_scopes(db, {communication.payment_group_id}).get(communication.payment_group_id)


def lock_payment_scope(db, communication_id, expected_group_id=None):
    communication = db.get(PaymentCommunication, communication_id)
    if not communication:
        raise CheckoutError("Comunicação não encontrada.")
    db.scalar(select(Client.id).where(Client.id == communication.client_id).with_for_update())
    group = None
    if communication.payment_group_id:
        if expected_group_id != communication.payment_group_id:
            raise CheckoutError(
                "Confira o pagamento completo antes de decidir sobre todas as galerias."
            )
        group = db.scalar(
            select(PaymentGroup)
            .where(PaymentGroup.id == communication.payment_group_id)
            .with_for_update()
        )
    db.refresh(communication, with_for_update=True)
    orders = list(
        db.scalars(
            select(SaleOrder)
            .where(
                SaleOrder.payment_group_id == group.id
                if group
                else SaleOrder.id == communication.sale_order_id
            )
            .order_by(SaleOrder.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    if not orders or any(order.client_id != communication.client_id for order in orders):
        raise CheckoutError("Pedidos indisponíveis para decisão.")
    return communication, group, orders


def report_group(db: Session, client: Client, group_id: UUID, revision: str, key: str):
    db.scalar(select(Client.id).where(Client.id == client.id).with_for_update())
    group = db.scalar(
        select(PaymentGroup)
        .where(PaymentGroup.id == group_id, PaymentGroup.client_id == client.id)
        .with_for_update()
    )
    if not group:
        raise CheckoutError("Compra indisponível.")
    existing = db.scalar(
        select(PaymentCommunication).where(PaymentCommunication.payment_group_id == group.id)
    )
    if existing:
        if revision != group.revision:
            raise CheckoutError("A revisão informada não corresponde à compra.")
        return existing
    materials = _valid_materials(db, client)
    if group.state != "draft" or revision != group.revision or revision != _fingerprint(materials):
        raise CheckoutError(
            "O carrinho mudou. Atualize a revisão e confira o total antes de informar pagamento."
        )
    orders = list(
        db.scalars(
            select(SaleOrder)
            .where(SaleOrder.payment_group_id == group.id)
            .order_by(SaleOrder.id)
            .with_for_update()
        )
    )
    if {order.derived_gallery_id for order in orders} != {
        gallery.id for gallery, _, _, _ in materials
    }:
        raise CheckoutError("O carrinho mudou. Atualize a revisão.")
    if any(order.frozen_at or order.payment_status != "pending" for order in orders):
        raise CheckoutError("Pedido indisponível para comunicação.")
    for order in orders:
        # Itens não são recalculados: a versão apresentada é a autoridade da comunicação.
        expected = next(
            material
            for gallery, _, material, _ in materials
            if gallery.id == order.derived_gallery_id
        )
        item_ids = set(
            db.scalars(
                select(SaleOrderItem.photo_asset_id_snapshot).where(
                    SaleOrderItem.sale_order_id == order.id
                )
            )
        )
        if (
            item_ids != {photo.id for photo in expected[1]}
            or order.total_cents != expected[3].quote.total_cents
        ):
            raise CheckoutError("A revisão mudou. Confira as fotos novamente.")
        order.frozen_at = now()
        db.execute(
            delete(PhotoSelection).where(PhotoSelection.id.in_([row.id for row in expected[0]]))
        )
    group.state, group.reported_at = "reported", now()
    communication = PaymentCommunication(
        sale_order_id=orders[0].id,
        client_id=client.id,
        payment_group_id=group.id,
        idempotency_key=key,
    )
    db.add(communication)
    db.flush()
    record_payment_event(
        db, communication=communication, order=orders[0], event_type="payment_reported"
    )
    audit(db, "payment_group.reported", str(group.id))
    return communication
