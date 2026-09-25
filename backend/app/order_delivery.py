"""Entrega final por pedido: URLs externas não são consultadas no servidor."""

import re
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select

from app.auth import Client, NotificationDelivery, NotificationEvent, SaleOrder, audit, now
from app.notification_settings import enqueue_event

EVENT_TYPE = "order_delivery_ready"


def validate_album_url(value: str | None) -> str | None:
    if value is None:
        return None
    # urlsplit remove controles; validar antes de fazer parse.
    if re.search(r"[\x00-\x1f\x7f\\]", value):
        raise ValueError("Informe um link de compartilhamento HTTPS do Google Photos.")
    value = value.strip()
    if not value:
        return None
    try:
        url = urlsplit(value)
        valid_path = (
            url.hostname == "photos.app.goo.gl" and re.fullmatch(r"/[A-Za-z0-9_-]+/?", url.path)
        ) or (
            url.hostname == "photos.google.com" and re.fullmatch(r"/share/[A-Za-z0-9_-]+/?", url.path)
        )
        if (len(value) > 2048 or url.scheme != "https" or url.username is not None
                or url.password is not None or url.port not in {None, 443}
                or not valid_path or re.search(r"\s", value)):
            raise ValueError()
    except ValueError as exc:
        raise ValueError("Informe um link de compartilhamento HTTPS do Google Photos (até 2048 caracteres).") from exc
    return value


def delivery_payload(order: SaleOrder) -> dict:
    return {
        "album_url": order.delivery_album_url,
        "version": order.delivery_revision,
        "updated_at": order.delivery_updated_at.isoformat() if order.delivery_updated_at else None,
        "can_send": order.payment_status == "confirmed",
        "can_resend": order.payment_status == "confirmed" and bool(order.delivery_album_url),
    }


def lock_delivery_order(db, order_id: UUID) -> SaleOrder:
    owner = db.scalar(select(SaleOrder.client_id).where(SaleOrder.id == order_id))
    if owner is None:
        raise LookupError("Pedido não encontrado.")
    # Mesma primeira trava das decisões financeiras e da remoção de acervo.
    db.scalar(select(Client.id).where(Client.id == owner).with_for_update())
    order = db.scalar(select(SaleOrder).where(SaleOrder.id == order_id)
                      .with_for_update().execution_options(populate_existing=True))
    if order is None:
        raise LookupError("Pedido não encontrado.")
    return order


def require_confirmed(order):
    if order.payment_status != "confirmed":
        raise ValueError("Confirme o pagamento para disponibilizar as fotos.")


def record_delivery_notice(db, order, key):
    event = enqueue_event(
        db, event_type=EVENT_TYPE, event_key=key,
        values={"cliente": order.client_name_snapshot or "Cliente",
                "galeria": order.derived_gallery_name_snapshot, "pedido": str(order.id)[:8]},
        target_path=f"/library/purchases#order-{order.id}", recipients=[order.client_id],
        client_id=order.client_id, sale_order_id=order.id,
    )
    channels = sorted(set(db.scalars(select(NotificationDelivery.channel).where(
        NotificationDelivery.event_id == event.id,
        NotificationDelivery.status.in_(["queued", "processing", "accepted"]),
    ))))
    return {"event_id": str(event.id), "channels": channels}


def set_delivery(db, order, url, version, actor_id):
    url = validate_album_url(url)
    if url:
        require_confirmed(order)
    if order.delivery_album_url == url:
        return {"delivery": delivery_payload(order), "unchanged": True, "notification": None}
    if order.delivery_revision != version:
        raise ValueError("A entrega mudou. Atualize a página antes de enviar.")
    order.delivery_album_url = url
    order.delivery_revision += 1
    order.delivery_updated_at = now()
    notice = record_delivery_notice(db, order, f"order-delivery:{order.id}:{order.delivery_revision}") if url else None
    audit(db, "order.delivery_available" if url else "order.delivery_removed", f"order:{order.id}:admin:{actor_id}")
    return {"delivery": delivery_payload(order), "unchanged": False, "notification": notice}


def resend_delivery(db, order, version, operation_id, actor_id):
    require_confirmed(order)
    if not order.delivery_album_url:
        raise ValueError("Cadastre o link antes de reenviar o aviso.")
    if order.delivery_revision != version:
        raise ValueError("A entrega mudou. Atualize a página antes de reenviar.")
    key = f"order-delivery-resend:{order.id}:{version}:{operation_id}"
    existing = db.scalar(select(NotificationEvent.id).where(NotificationEvent.event_key == key))
    notice = record_delivery_notice(db, order, key)
    if not existing:
        audit(db, "order.delivery_notice_resent", f"order:{order.id}:admin:{actor_id}")
    # O registro do evento deduplicado identifica a ação, sem histórico paralelo.
    return {"delivery": delivery_payload(order), "notification": notice}


def delivery_notice_allowed(db, event, item):
    order = db.get(SaleOrder, event.sale_order_id)
    if (not order or item.recipient_role != "client" or order.client_id != item.recipient_id
            or event.client_id != order.client_id or order.payment_status != "confirmed"
            or not order.delivery_album_url):
        return False
    parts = event.event_key.split(":")
    try:
        expected_length = {"order-delivery": 3, "order-delivery-resend": 4}.get(parts[0])
        return (len(parts) == expected_length and UUID(parts[1]) == order.id
                and int(parts[2]) == order.delivery_revision)
    except (ValueError, IndexError):
        return False
