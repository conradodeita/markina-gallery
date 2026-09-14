"""Consumidores independentes com lease, TTL e falhas sanitizadas."""

import os
from datetime import UTC, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, update

from app.auth import (
    AdminUser,
    Client,
    ClientPhone,
    DerivedGallery,
    NotificationDelivery,
    NotificationEvent,
    NotificationSetting,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    PaymentConfirmationCorrection,
    PaymentNotificationOutbox,
    PushSubscription,
    SaleOrder,
    SessionLocal,
    now,
)
from app.messaging import (
    WhatsAppConfigurationError,
    WhatsAppDeliveryError,
    configured_photographer_phone,
    whatsapp_provider_from_environment,
)
from app.private_membership import client_has_operational_membership
from app.push_subscriptions import decrypt_subscription, push_enabled
from app.web_push import PushFailure, send_push
from app.whatsapp_channel import require_ready_channel

MAX_ATTEMPTS = 3


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def channel_enabled(event_type: str, channel: str) -> bool:
    if channel == "push":
        return push_enabled()
    # Fluxos de pagamento já ativos permanecem; três eventos novos exigem ativação operacional.
    return event_type.startswith("payment_") or os.getenv("TRANSACTIONAL_WHATSAPP_ENABLED", "false").lower() == "true"


def mirror_payment_projection(db, event, item):
    if item.channel != "whatsapp":
        return
    projection = db.scalar(select(PaymentNotificationOutbox).where(
        PaymentNotificationOutbox.idempotency_key == event.event_key))
    if projection:
        projection.status = "sent" if item.status == "accepted" else "queued" if item.status in {"queued", "processing"} else "failed"
        projection.attempts = item.attempts
        projection.last_error = item.last_error
        projection.updated_at = now()


def recipient_allowed(db, event, item) -> bool:
    if item.recipient_role == "admin":
        admin = db.get(AdminUser, item.recipient_id)
        if not admin or not admin.email_verified:
            return False
    elif item.recipient_id != event.client_id or not db.get(Client, item.recipient_id):
        return False
    if event.derived_gallery_id:
        gallery = db.get(DerivedGallery, event.derived_gallery_id)
        if not gallery or not gallery.access_enabled:
            return False
        if event.client_id and not client_has_operational_membership(db, gallery=gallery, client_id=event.client_id):
            return False
    elif event.parent_gallery_id and event.client_id:
        parent = db.get(ParentGallery, event.parent_gallery_id)
        registration = db.scalar(select(ParentGalleryRegistration).where(
            ParentGalleryRegistration.parent_gallery_id == event.parent_gallery_id,
            ParentGalleryRegistration.client_id == event.client_id,
        ))
        if not parent or not parent.active or parent.lifecycle_status != "active" or not registration or registration.status != "active":
            return False
    if event.event_type.startswith("payment_"):
        order = db.get(SaleOrder, event.sale_order_id)
        if not order or order.client_id != event.client_id:
            return False
        parts = event.event_key.split(":")
        try:
            communication = db.get(PaymentCommunication, UUID(parts[1]))
        except (ValueError, IndexError):
            return False
        if not communication or communication.sale_order_id != order.id:
            return False
        if event.event_type != "payment_reported":
            revision = db.scalar(select(func.count(PaymentConfirmationCorrection.id)).where(
                PaymentConfirmationCorrection.payment_communication_id == communication.id))
            if communication.status != event.event_type.removeprefix("payment_") or parts[-1] != str(revision):
                return False
    return True


def process_next_notification(channel: str, *, push_sender=None, whatsapp_provider=None) -> bool:
    if channel not in {"push", "whatsapp"}:
        raise ValueError("Canal inválido.")
    with SessionLocal() as db:
        instant = now()
        stale_rows = list(db.scalars(select(NotificationDelivery).where(
            NotificationDelivery.channel == channel, NotificationDelivery.status == "processing",
            NotificationDelivery.lease_until <= instant,
        ).with_for_update(skip_locked=True).limit(20)))
        for stale in stale_rows:
            stale.status = "unknown" if channel == "whatsapp" else "queued"
            stale.last_error = "interrupted_delivery"
            stale.lease_token = None
            stale.lease_until = None
            stale.next_attempt_at = instant
            event = db.get(NotificationEvent, stale.event_id)
            if event:
                mirror_payment_projection(db, event, stale)
        db.commit()
        item = db.scalar(select(NotificationDelivery).where(
            NotificationDelivery.channel == channel, NotificationDelivery.status == "queued",
            NotificationDelivery.next_attempt_at <= instant,
        ).order_by(NotificationDelivery.created_at).with_for_update(skip_locked=True).limit(1))
        if not item:
            return bool(stale_rows)
        item_id, lease_token = item.id, uuid4()
        result = db.execute(update(NotificationDelivery).where(
            NotificationDelivery.id == item_id, NotificationDelivery.status == "queued",
        ).values(status="processing", lease_token=lease_token,
                 lease_until=instant + timedelta(seconds=60), updated_at=instant))
        if result.rowcount != 1:
            db.rollback()
            return bool(stale_rows)
        db.commit()
        db.expire_all()
        item = db.get(NotificationDelivery, item_id)
        event = db.get(NotificationEvent, item.event_id)
        setting = db.get(NotificationSetting, event.event_type) if event else None
        status, error = None, None
        disabled_at = getattr(setting, f"{channel}_disabled_at", None) if setting else None
        if not event or not setting:
            status, error = "cancelled", "event_unavailable"
        elif utc(event.expires_at) <= instant:
            status, error = "expired", "delivery_expired"
        elif (not getattr(setting, f"{channel}_enabled") or not channel_enabled(event.event_type, channel)
              or (disabled_at and utc(event.created_at) <= utc(disabled_at))):
            status, error = "cancelled", "channel_disabled"
        elif item.attempts >= MAX_ATTEMPTS:
            status, error = "failed", "attempt_limit"
        elif not recipient_allowed(db, event, item):
            status, error = "cancelled", "recipient_not_authorized"
        subscription = db.get(PushSubscription, item.subscription_id) if channel == "push" else None
        if not status and channel == "push" and (
            not subscription or not subscription.active or subscription.generation != item.subscription_generation
            or subscription.role != item.recipient_role or subscription.subject_id != item.recipient_id
        ):
            status, error = "cancelled", "subscription_revoked"
        next_attempt = None
        if not status:
            item.attempts += 1
            db.commit()
            try:
                if channel == "push":
                    (push_sender or send_push)(decrypt_subscription(subscription), {
                        "id": str(event.id), "title": event.push_title,
                        "body": event.push_body, "path": event.target_path,
                    }, ttl=max(1, int((utc(event.expires_at) - now()).total_seconds())))
                else:
                    if item.recipient_role == "admin":
                        phone = configured_photographer_phone()
                    else:
                        phone = db.scalar(select(ClientPhone.phone_e164).where(
                            ClientPhone.client_id == item.recipient_id, ClientPhone.active,
                            ClientPhone.verified_at.is_not(None)))
                    if not phone:
                        raise WhatsAppConfigurationError("Destino verificado indisponível.")
                    provider = whatsapp_provider or whatsapp_provider_from_environment()
                    require_ready_channel(db, provider)
                    result = provider.send_transactional(phone, event.whatsapp_body,
                                                         idempotency_key=f"notification:{item.id}")
                    if result.recipient_phone_e164 != phone:
                        raise WhatsAppDeliveryError("Destino divergente.", transient=False, ambiguous=True)
                status = "accepted"
            except (PushFailure, WhatsAppDeliveryError, WhatsAppConfigurationError, ValueError) as exc:
                error = exc.category if isinstance(exc, PushFailure) else type(exc).__name__
                if isinstance(exc, PushFailure) and exc.status in {404, 410}:
                    subscription.active = False
                    subscription.generation += 1
                if getattr(exc, "ambiguous", False) and channel == "whatsapp":
                    status = "unknown"
                elif getattr(exc, "transient", False) and item.attempts < MAX_ATTEMPTS:
                    status = "queued"
                    next_attempt = now() + timedelta(seconds=min(30 * 2 ** (item.attempts - 1), 300))
                else:
                    status = "failed"
            except Exception:  # noqa: BLE001 - fronteira externa: nunca propagar payload/segredo
                status, error = "unknown", "unexpected_transport_failure"
        # Outro worker pode ter recuperado o lease. Nunca sobrescrever sua decisão.
        current_lease = db.scalar(select(NotificationDelivery.lease_token).where(
            NotificationDelivery.id == item.id).with_for_update())
        if current_lease != lease_token:
            db.rollback()
            return True
        item.status, item.last_error = status, error
        item.next_attempt_at = next_attempt or now()
        item.lease_until, item.lease_token = None, None
        item.updated_at = now()
        if event:
            mirror_payment_projection(db, event, item)
        db.commit()
        return True


def retry_payment_projection(db, outbox) -> bool:
    event = db.scalar(select(NotificationEvent).where(NotificationEvent.event_key == outbox.idempotency_key))
    if not event:
        return False
    setting = db.get(NotificationSetting, event.event_type)
    if not setting or not setting.whatsapp_enabled or utc(event.expires_at) <= now():
        raise ValueError("Canal desativado ou aviso expirado.")
    if setting.whatsapp_disabled_at and utc(event.created_at) <= utc(setting.whatsapp_disabled_at):
        raise ValueError("Aviso cancelado; não há reenvio retroativo.")
    deliveries = list(db.scalars(select(NotificationDelivery).where(
        NotificationDelivery.event_id == event.id, NotificationDelivery.channel == "whatsapp",
    ).with_for_update()))
    if not deliveries or any(item.status != "failed" or item.attempts >= MAX_ATTEMPTS for item in deliveries):
        raise ValueError("Aviso indisponível para retentativa.")
    for item in deliveries:
        if not recipient_allowed(db, event, item):
            raise ValueError("Destinatário não autorizado.")
        item.status, item.last_error, item.next_attempt_at = "queued", None, now()
    return True
