"""Agregações compartilhadas para dashboard e relatórios comerciais."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from html import escape
from io import StringIO
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    DerivedGallery,
    GalleryClientState,
    ParentGallery,
    PaymentGroup,
    PhotoSelection,
    ProviderPayment,
    SaleOrder,
    SaleOrderItem,
)

CSV_HEADERS = (
    "pedido_id", "cliente_nome", "cliente_telefone", "data", "galeria_id",
    "galeria_nome", "pasta_id", "pasta_nome", "item_id", "fotografia_id",
    "fotografia_nome", "quantidade", "valor_unitario", "total_item",
    "forma_pagamento", "conta_destino", "categoria",
)


def _money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    value = abs(cents)
    return f"{sign}{value // 100}.{value % 100:02d}"


def _payment(db: Session, order: SaleOrder, tenant_id: UUID) -> tuple[str, str, bool, str]:
    if order.payment_group_id:
        group = db.scalar(select(PaymentGroup).where(
            PaymentGroup.id == order.payment_group_id,
            PaymentGroup.tenant_id == tenant_id,
            PaymentGroup.client_id == order.client_id,
        ))
        return "pix", "Nubank", bool(group and group.state == "confirmed"), group.state if group else "missing"
    if order.provider_payment_id:
        payment = db.scalar(select(ProviderPayment).where(
            ProviderPayment.id == order.provider_payment_id,
            ProviderPayment.tenant_id == tenant_id,
            ProviderPayment.client_id == order.client_id,
        ))
        return "credit_card", "InfinityPay", bool(payment and payment.provider == "infinitepay" and payment.state == "confirmed"), payment.state if payment else "missing"
    if not order.payment_required_snapshot and order.payment_status == "not_required":
        return "not_required", "", True, "not_required"
    return "unknown", "", order.payment_status == "confirmed", "unknown"


def commercial_report(
    db: Session,
    *,
    tenant_id: UUID,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    event_name: str | None = None,
    client_id: UUID | None = None,
    parent_gallery_id: UUID | None = None,
    derived_gallery_id: UUID | None = None,
    folder_id: UUID | None = None,
    payment_method: str | None = None,
    order_status: str | None = None,
) -> dict[str, object]:
    """Retorna uma visão única; IDs externos nunca definem tenant."""
    query = select(SaleOrder).where(SaleOrder.tenant_id == tenant_id)
    event_gallery_ids: set[UUID] | None = None
    if event_name:
        event_gallery_ids = set(db.scalars(select(ParentGallery.id).where(
            ParentGallery.tenant_id == tenant_id, ParentGallery.event_name == event_name,
        )))
        query = query.where(SaleOrder.parent_gallery_id_snapshot.in_(event_gallery_ids))
    if starts_at:
        query = query.where(or_(SaleOrder.confirmed_at >= starts_at, (SaleOrder.confirmed_at.is_(None)) & (SaleOrder.created_at >= starts_at)))
    if ends_at:
        query = query.where(or_(SaleOrder.confirmed_at <= ends_at, (SaleOrder.confirmed_at.is_(None)) & (SaleOrder.created_at <= ends_at)))
    if client_id:
        query = query.where(SaleOrder.client_id == client_id)
    if parent_gallery_id:
        query = query.where(SaleOrder.parent_gallery_id_snapshot == parent_gallery_id)
    if derived_gallery_id:
        query = query.where(SaleOrder.derived_gallery_id_snapshot == derived_gallery_id)
    orders = list(db.scalars(query.order_by(SaleOrder.confirmed_at.desc(), SaleOrder.id)))

    rows: list[dict[str, object]] = []
    order_details: list[dict[str, object]] = []
    reconciliations: list[dict[str, object]] = []
    revenue_cents = 0
    confirmed_order_count = 0
    sold_photo_count = 0
    revenue_by_day: dict[str, int] = {}
    by_folder: dict[tuple[str, str], int] = {}
    by_gallery: dict[tuple[str, str], int] = {}
    purchased_selection_keys: set[tuple[UUID, UUID, UUID]] = set()
    for order in orders:
        method, destination, financially_confirmed, payment_state = _payment(db, order, tenant_id)
        is_confirmed = order.payment_status == "confirmed" and financially_confirmed
        if payment_method and method != payment_method:
            continue
        item_query = select(SaleOrderItem).where(
            SaleOrderItem.tenant_id == tenant_id,
            SaleOrderItem.sale_order_id == order.id,
        )
        items = list(db.scalars(item_query.order_by(SaleOrderItem.id)))
        if folder_id:
            items = [item for item in items if item.folder_id_snapshot == folder_id]
            if not items:
                continue
        if payment_state == "hold" or (order.payment_status == "confirmed" and not financially_confirmed):
            status = "hold_or_corrected"
        else:
            status = order.payment_status
        if order_status and status != order_status:
            continue
        item_total = sum(item.unit_price_cents for item in items)
        all_items = list(db.scalars(select(SaleOrderItem).where(
            SaleOrderItem.tenant_id == tenant_id, SaleOrderItem.sale_order_id == order.id,
        ))) if folder_id else items
        reconciliation_total = sum(item.unit_price_cents for item in all_items)
        reconciliations.append({
            "order_id": str(order.id), "order_total_cents": order.total_cents,
            "items_total_cents": reconciliation_total, "difference_cents": order.total_cents - reconciliation_total,
        })
        if is_confirmed:
            confirmed_order_count += 1
            sold_photo_count += len(items)
            revenue_cents += item_total if folder_id else order.total_cents
            if order.confirmed_at:
                day = order.confirmed_at.date().isoformat()
                revenue_by_day[day] = revenue_by_day.get(day, 0) + (item_total if folder_id else order.total_cents)
            purchased_selection_keys.update(
                (order.client_id, order.parent_gallery_id_snapshot, item.photo_asset_id_snapshot)
                for item in items
            )
        order_details.append({
            "order_id": str(order.id), "status": status, "confirmed": is_confirmed,
            "client_name": order.client_name_snapshot or "", "client_phone": order.client_phone_snapshot or "",
            "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else "",
            "gallery_id": str(order.parent_gallery_id_snapshot), "gallery_name": order.parent_gallery_name_snapshot,
            "derived_gallery_id": str(order.derived_gallery_id_snapshot) if order.derived_gallery_id_snapshot else "",
            "derived_gallery_name": order.derived_gallery_name_snapshot,
            "payment_method": method, "destination": destination,
            "total_cents": order.total_cents, "items_total_cents": reconciliation_total,
            "items": [{"id": str(item.id), "photo_id": str(item.photo_asset_id_snapshot),
                "photo_name": item.filename_snapshot, "folder_id": str(item.folder_id_snapshot) if item.folder_id_snapshot else "",
                "folder_name": item.folder_name_snapshot or "", "unit_price_cents": item.unit_price_cents,
                "quantity": 1} for item in items],
        })
        if is_confirmed:
            for item in items:
                rows.append({
                    "pedido_id": str(order.id), "cliente_nome": order.client_name_snapshot or "",
                    "cliente_telefone": order.client_phone_snapshot or "",
                    "data": order.confirmed_at.date().isoformat() if order.confirmed_at else "",
                    "galeria_id": str(order.parent_gallery_id_snapshot), "galeria_nome": order.parent_gallery_name_snapshot,
                    "pasta_id": str(item.folder_id_snapshot) if item.folder_id_snapshot else "",
                    "pasta_nome": item.folder_name_snapshot or "", "item_id": str(item.id),
                    "fotografia_id": str(item.photo_asset_id_snapshot), "fotografia_nome": item.filename_snapshot,
                    "quantidade": 1, "valor_unitario": item.unit_price_cents,
                    "total_item": item.unit_price_cents, "forma_pagamento": method,
                    "conta_destino": destination, "categoria": "Fotografia",
                })
                gallery_key = (str(order.parent_gallery_id_snapshot), order.parent_gallery_name_snapshot)
                folder_key = (str(item.folder_id_snapshot) if item.folder_id_snapshot else "", item.folder_name_snapshot or "Sem pasta")
                by_gallery[gallery_key] = by_gallery.get(gallery_key, 0) + item.unit_price_cents
                by_folder[folder_key] = by_folder.get(folder_key, 0) + item.unit_price_cents

    abandoned: list[dict[str, object]] = []
    selected_not_purchased: list[dict[str, object]] = []
    eligible_selections = 0
    converted_selections = 0
    # A seleção resolvida é uma foto única por cliente/galeria: comprada, ou expirada sem pedido.
    selection_query = select(PhotoSelection).where(PhotoSelection.tenant_id == tenant_id)
    if client_id:
        selection_query = selection_query.where(PhotoSelection.client_id == client_id)
    selections = list(db.scalars(selection_query)) if not (folder_id or payment_method or order_status) else []
    pairs: dict[tuple[UUID, UUID], dict[UUID, PhotoSelection]] = {}
    for selection in selections:
        parent_id = selection.parent_gallery_id
        if parent_id is None and selection.derived_gallery_id:
            gallery = db.scalar(select(DerivedGallery).where(
                DerivedGallery.id == selection.derived_gallery_id, DerivedGallery.tenant_id == tenant_id,
            ))
            parent_id = gallery.parent_gallery_id if gallery else None
        if parent_id is None or (parent_gallery_id and parent_gallery_id != parent_id):
            continue
        if event_gallery_ids is not None and parent_id not in event_gallery_ids:
            continue
        if selection.derived_gallery_id and derived_gallery_id and derived_gallery_id != selection.derived_gallery_id:
            continue
        if starts_at and selection.created_at < starts_at:
            continue
        if ends_at and selection.created_at > ends_at:
            continue
        pair = pairs.setdefault((selection.client_id, parent_id), {})
        pair.setdefault(selection.photo_asset_id, selection)
    now_utc = datetime.now(UTC)
    for (selected_client_id, selected_parent_id), by_photo in pairs.items():
        selected_rows = list(by_photo.values())
        existing_order = db.scalar(select(SaleOrder.id).where(
            SaleOrder.tenant_id == tenant_id, SaleOrder.client_id == selected_client_id,
            SaleOrder.parent_gallery_id_snapshot == selected_parent_id,
        ).limit(1))
        expiry = None
        derived = next((s.derived_gallery_id for s in selected_rows if s.derived_gallery_id), None)
        if derived:
            gallery = db.scalar(select(DerivedGallery).where(DerivedGallery.id == derived, DerivedGallery.tenant_id == tenant_id))
            expiry = gallery.selection_expires_at if gallery else None
        if expiry is None:
            state = db.scalar(select(GalleryClientState).where(
                GalleryClientState.tenant_id == tenant_id,
                GalleryClientState.parent_gallery_id == selected_parent_id,
                GalleryClientState.client_id == selected_client_id,
            ))
            expiry = state.selection_expires_at if state else None
        is_expired = expiry is not None and expiry.replace(tzinfo=expiry.tzinfo or UTC) <= now_utc
        abandoned_photos = []
        for selection in selected_rows:
            key = (selected_client_id, selected_parent_id, selection.photo_asset_id)
            if key in purchased_selection_keys:
                eligible_selections += 1
                converted_selections += 1
            elif is_expired and not existing_order:
                eligible_selections += 1
                abandoned_photos.append(selection)
                selected_not_purchased.append({
                    "client_id": str(selected_client_id), "gallery_id": str(selected_parent_id),
                    "photo_id": str(selection.photo_asset_id), "selected_at": selection.created_at.isoformat(),
                    "abandoned": True,
                })
            else:
                selected_not_purchased.append({
                    "client_id": str(selected_client_id), "gallery_id": str(selected_parent_id),
                    "photo_id": str(selection.photo_asset_id), "selected_at": selection.created_at.isoformat(),
                    "abandoned": False,
                })
        if not abandoned_photos:
            continue
        client = db.scalar(select(Client).where(Client.id == selected_client_id, Client.tenant_id == tenant_id))
        gallery = db.scalar(select(ParentGallery).where(ParentGallery.id == selected_parent_id, ParentGallery.tenant_id == tenant_id))
        abandoned.append({"client_id": str(selected_client_id), "client_name": client.full_name if client else "",
            "gallery_id": str(selected_parent_id), "gallery_name": gallery.name if gallery else "",
            "photo_count": len(abandoned_photos), "potential_value_cents": None,
            "photos": [{"photo_id": str(s.photo_asset_id), "selected_at": s.created_at.isoformat()} for s in abandoned_photos]})

    return {
        "revenue_cents": revenue_cents, "confirmed_order_count": confirmed_order_count,
        "sold_photo_count": sold_photo_count,
        "average_order_cents": (
            (revenue_cents + confirmed_order_count // 2) // confirmed_order_count
            if confirmed_order_count
            else None
        ),
        "revenue_by_day": [{"date": k, "revenue_cents": v} for k, v in sorted(revenue_by_day.items())],
        "orders": order_details, "items": rows, "reconciliations": reconciliations,
        "abandoned": abandoned,
        "selected_not_purchased": selected_not_purchased,
        "selection_metrics_available": not (folder_id or payment_method or order_status),
        "eligible_selection_count": eligible_selections,
        "converted_selection_count": converted_selections,
        "conversion_rate_percent": (converted_selections * 100 / eligible_selections) if eligible_selections else None,
        "by_gallery": [{"id": k[0], "name": k[1], "total_cents": v} for k, v in by_gallery.items()],
        "by_folder": [{"id": k[0], "name": k[1], "total_cents": v} for k, v in by_folder.items()],
    }


def report_csv(rows: list[dict[str, object]]) -> str:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_HEADERS, delimiter=";", lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for row in rows:
        values = dict(row)
        for field in ("valor_unitario", "total_item"):
            cents = int(values[field])
            values[field] = f"{cents // 100}.{cents % 100:02d}"
        writer.writerow(values)
    return output.getvalue()


def report_html(report: dict[str, object]) -> str:
    orders = report["orders"]
    body = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            escape(str(order["confirmed_at"] or "—")), escape(str(order["client_name"])),
            escape(str(order["gallery_name"])), escape(str(order["status"])),
            escape(f"R$ {int(order['total_cents']) / 100:.2f}"),
        ) for order in orders
    )
    item_rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>R$ {}.{:02d}</td><td>{}</td><td>{}</td></tr>".format(
            escape(str(row["pedido_id"])), escape(str(row["cliente_nome"])), escape(str(row["galeria_nome"])),
            escape(str(row["cliente_telefone"])), escape(str(row["data"])), escape(str(row["fotografia_nome"])), escape(str(row["pasta_nome"] or "Sem pasta")),
            int(row["total_item"]) // 100, int(row["total_item"]) % 100,
            escape(str(row["forma_pagamento"])), escape(str(row["conta_destino"])),
        ) for row in report["items"]
    )
    gallery_rows = "".join(
        "<li>{}: R$ {}.{:02d}</li>".format(escape(str(row["name"])), int(row["total_cents"]) // 100, int(row["total_cents"]) % 100)
        for row in report["by_gallery"]
    )
    folder_rows = "".join(
        "<li>{}: R$ {}.{:02d}</li>".format(escape(str(row["name"])), int(row["total_cents"]) // 100, int(row["total_cents"]) % 100)
        for row in report["by_folder"]
    )
    reconciliation_rows = "".join(
        "<tr><td>{}</td><td>R$ {}</td><td>R$ {}</td><td>R$ {}</td></tr>".format(
            escape(str(row["order_id"])), _money(int(row["order_total_cents"])),
            _money(int(row["items_total_cents"])), _money(int(row["difference_cents"])),
        ) for row in report["reconciliations"] if row["difference_cents"] != 0
    ) or "<tr><td colspan='4'>Os totais conciliam.</td></tr>"
    abandoned_rows = "".join(
        "<li>{} · {} · {} fotos ({}) · valor potencial indisponível</li>".format(
            escape(str(row["client_name"])), escape(str(row["gallery_name"])), int(row["photo_count"]),
            escape(", ".join(str(photo["photo_id"]) for photo in row["photos"])),
        ) for row in report["abandoned"]
    )
    selected_rows = "".join(
        "<li>{} · {} · {}{}</li>".format(
            escape(str(row["client_id"])), escape(str(row["gallery_id"])), escape(str(row["photo_id"])),
            " · prazo vencido, sem pedido" if row["abandoned"] else " · ainda sem compra",
        ) for row in report["selected_not_purchased"]
    )
    cents = int(report["revenue_cents"])
    conversion = report["conversion_rate_percent"]
    selection_metrics_available = bool(report["selection_metrics_available"])
    styles = "<style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#17202a}table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{text-align:left;padding:.65rem;border-bottom:1px solid #ddd}th{background:#f3f5f7}.kpis{display:flex;gap:1rem;flex-wrap:wrap}.kpis article{padding:1rem;background:#f3f5f7;border-radius:.5rem}@media(max-width:700px){table{font-size:.82rem}}</style>"
    return (
        "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Relatório comercial</title>"
        + styles
        + f"<h1>Relatório comercial</h1><div class='kpis'><article>Receita confirmada: R$ {cents // 100}.{cents % 100:02d}</article><article>Pedidos confirmados: {report['confirmed_order_count']}</article><article>Fotos vendidas: {report['sold_photo_count']}</article><article>Conversão das seleções resolvidas: {'indisponível' if conversion is None else f'{conversion:.1f}%'} ({report['converted_selection_count']}/{report['eligible_selection_count']})</article></div>"
        + "<p>Receita considera apenas confirmações financeiras vigentes. O modelo não registra eventos de reembolso, frete, desconto ou taxas para calcular receita líquida; diferenças entre pedido e itens são mostradas sem ajuste automático.</p>"
        + f"<h2>Itens vendidos</h2><table><thead><tr><th>Pedido</th><th>Cliente</th><th>Galeria</th><th>Telefone</th><th>Data</th><th>Fotografia</th><th>Pasta</th><th>Total do item</th><th>Pagamento</th><th>Destino mapeado</th></tr></thead><tbody>{item_rows}</tbody></table>"
        + f"<h2>Pedidos</h2><table><thead><tr><th>Data</th><th>Cliente</th><th>Galeria</th><th>Status</th><th>Total</th></tr></thead><tbody>{body}</tbody></table>"
        + f"<h2>Totais por galeria</h2><ul>{gallery_rows}</ul><h2>Totais por pasta</h2><ul>{folder_rows}</ul>"
        + f"<h2>Conciliação de pedidos</h2><table><thead><tr><th>Pedido</th><th>Total registrado</th><th>Total dos itens</th><th>Diferença</th></tr></thead><tbody>{reconciliation_rows}</tbody></table>"
        + f"<h2>Selecionadas sem compra</h2>{'<ul>' + selected_rows + '</ul>' if selection_metrics_available else '<p>Indicador indisponível para os filtros de pasta, pagamento ou status.</p>'}<h2>Seleções abandonadas</h2><p>Somente seleções após o prazo configurado da galeria, sem pedido associado. Valor potencial indisponível sem preço congelado.</p>{'<ul>' + abandoned_rows + '</ul>' if selection_metrics_available else '<p>Indicador indisponível para os filtros de pasta, pagamento ou status.</p>'}</html>"
    )
