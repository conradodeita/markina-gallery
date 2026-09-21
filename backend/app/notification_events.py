"""Marcos de negócio idempotentes; nenhum transporte no ciclo HTTP."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    Client,
    DerivedGallery,
    NotificationMilestone,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentGroup,
    PaymentNotificationOutbox,
)
from app.messaging import WhatsAppConfigurationError, configured_photographer_phone
from app.notification_settings import enqueue_event, notification_savepoint, setting_for
from app.private_membership import client_has_operational_membership


def record_gallery_milestone(db: Session, *, kind: str, parent_gallery_id: UUID,
                             client_id: UUID, gallery: DerivedGallery | None = None) -> bool:
    """O chamador já autenticou por OTP; revalidar escopo antes de registrar o marco."""
    if kind not in {"first_access", "first_selection"}:
        raise ValueError("Marco não permitido.")
    parent = db.get(ParentGallery, parent_gallery_id)
    client = db.get(Client, client_id)
    if not parent or not client:
        return False
    if gallery:
        if gallery.parent_gallery_id != parent.id or not gallery.access_enabled:
            return False
        if not client_has_operational_membership(db, gallery=gallery, client_id=client.id):
            return False
    else:
        if not parent.active or parent.lifecycle_status != "active" or parent.access_mode == "collective_protected":
            return False
        registration = db.scalar(select(ParentGalleryRegistration.id).where(
            ParentGalleryRegistration.parent_gallery_id == parent.id,
            ParentGalleryRegistration.client_id == client.id,
            ParentGalleryRegistration.status == "active",
        ))
        if not registration:
            return False
    key = (parent.id, client.id, kind)
    if db.get(NotificationMilestone, key):
        return False
    try:
        with notification_savepoint(db):
            db.add(NotificationMilestone(parent_gallery_id=parent.id, client_id=client.id, kind=kind))
            db.flush()
            enqueue_event(
                db, event_type=kind, event_key=f"{kind}:{parent.id}:{client.id}",
                values={"cliente": client.full_name, "galeria": parent.name},
                target_path=f"/admin/galleries/{gallery.id}" if gallery
                else f"/admin/galleries/sources/{parent.id}/edit/imagens",
                recipients=list(db.scalars(select(AdminUser.id).where(AdminUser.email_verified))),
                parent_gallery_id=parent.id, derived_gallery_id=gallery.id if gallery else None,
                client_id=client.id,
            )
    except IntegrityError:
        if not db.get(NotificationMilestone, key):
            raise
        return False
    return True


def record_payment_event(db: Session, *, communication, order, event_type: str,
                         decision_revision: int = 0):
    client = db.get(Client, order.client_id)
    gallery = db.get(DerivedGallery, order.derived_gallery_id)
    if not client or not gallery or communication.client_id != client.id:
        return None
    reported = event_type == "payment_reported"
    group = db.get(PaymentGroup, communication.payment_group_id) if communication.payment_group_id else None
    event_key = f"payment-reported:{communication.id}" if reported else (
        f"payment-decision:{communication.id}:{communication.status}:{decision_revision}")
    recipients = list(db.scalars(select(AdminUser.id).where(AdminUser.email_verified))) \
        if reported else [client.id]
    event = enqueue_event(db, event_type=event_type, event_key=event_key,
                          values={"cliente": order.client_name_snapshot or client.full_name,
                                  "galeria": "sua compra" if group else order.derived_gallery_name_snapshot,
                                  "pedido": str(group.id if group else order.id)[:8]},
                          target_path="/admin/payments" if reported else (
                              f"/library/purchases#payment-{group.id}" if group else f"/gallery/{gallery.id}"),
                          recipients=recipients, parent_gallery_id=gallery.parent_gallery_id,
                          derived_gallery_id=gallery.id, client_id=client.id, sale_order_id=order.id)
    # Projeção técnica para os cards financeiros existentes, nunca segunda fila externa.
    # O materializador legado exclui chaves presentes na outbox transacional.
    if not db.scalar(select(PaymentNotificationOutbox.id).where(
        PaymentNotificationOutbox.idempotency_key == event_key)):
        try:
            phone = configured_photographer_phone() if reported else client.phone_e164
        except WhatsAppConfigurationError:
            phone = None
        if phone:
            db.add(PaymentNotificationOutbox(payment_communication_id=communication.id,
                   recipient_phone=phone, template_kind="photographer_reported" if reported else communication.status,
                   idempotency_key=event_key, rendered_body_snapshot=event.whatsapp_body,
                   status="queued" if setting_for(db, event_type).whatsapp_enabled else "failed",
                   last_error=None if setting_for(db, event_type).whatsapp_enabled else "channel_disabled"))
    return event
