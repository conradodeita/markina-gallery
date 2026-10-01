"""Consumidores independentes com lease, TTL e falhas sanitizadas."""

import os
from datetime import UTC, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, update

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    AdminUser,
    AuthSession,
    Client,
    ClientPhone,
    DerivedGallery,
    FolderClientGrant,
    GalleryClientState,
    NotificationDelivery,
    NotificationEvent,
    NotificationSetting,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    PaymentConfirmationCorrection,
    PaymentGroup,
    PaymentNotificationOutbox,
    PhotoFolder,
    PushSubscription,
    SaleOrder,
    SessionLocal,
    Tenant,
    now,
)
from app.messaging import (
    WhatsAppConfigurationError,
    WhatsAppDeliveryError,
)
from app.order_delivery import EVENT_TYPE as ORDER_DELIVERY_EVENT
from app.order_delivery import delivery_notice_allowed
from app.private_membership import client_has_operational_membership
from app.push_subscriptions import decrypt_subscription, push_enabled
from app.tenancy import TenantContextError, require_admin_tenant
from app.web_push import PushFailure, send_push
from app.whatsapp_binding import photographer_phone, provider_for
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
    if item.channel != "whatsapp" or item.tenant_id != event.tenant_id:
        return
    projection = db.scalar(select(PaymentNotificationOutbox).where(
        PaymentNotificationOutbox.tenant_id == item.tenant_id,
        PaymentNotificationOutbox.idempotency_key == event.event_key))
    if projection:
        projection.status = "sent" if item.status == "accepted" else "queued" if item.status in {"queued", "processing"} else "failed"
        projection.attempts = item.attempts
        projection.last_error = item.last_error
        projection.updated_at = now()


def recipient_allowed(db, event, item) -> bool:
    require_active_owner(db, item.tenant_id)
    if event.tenant_id != item.tenant_id:
        return False
    owner = item.tenant_id
    if item.recipient_role == "admin":
        admin = db.get(AdminUser, item.recipient_id, populate_existing=True)
        if not admin or not admin.email_verified:
            return False
        try:
            if require_admin_tenant(db, admin.id).id != owner:
                return False
        except TenantContextError:
            return False
    elif item.recipient_id != event.client_id or not owned_record(db, Client, item.recipient_id, tenant_id=owner):
        return False
    if event.event_type == ORDER_DELIVERY_EVENT:
        return delivery_notice_allowed(db, event, item)
    if event.derived_gallery_id:
        gallery = owned_record(db, DerivedGallery, event.derived_gallery_id, tenant_id=owner)
        parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=owner) if gallery else None
        if not gallery or not gallery.access_enabled or not parent or not parent.active or parent.lifecycle_status != "active":
            return False
        if event.client_id and not client_has_operational_membership(db, gallery=gallery, client_id=event.client_id):
            return False
    elif event.parent_gallery_id and event.client_id:
        parent = owned_record(db, ParentGallery, event.parent_gallery_id, tenant_id=owner)
        registration = db.scalar(select(ParentGalleryRegistration).where(
            ParentGalleryRegistration.tenant_id == owner,
            ParentGalleryRegistration.parent_gallery_id == event.parent_gallery_id,
            ParentGalleryRegistration.client_id == event.client_id,
        ).execution_options(populate_existing=True))
        if not parent or not parent.active or parent.lifecycle_status != "active" or not registration or registration.status != "active":
            return False
    if event.event_type == "private_photos_ready" and not event.derived_gallery_id:
        try:
            key_parts = event.event_key.split(":")
            if len(key_parts) != 6:
                return False
            folder_id, grant_id = UUID(key_parts[1]), UUID(key_parts[4])
        except (ValueError, IndexError):
            return False
        folder = owned_record(db, PhotoFolder, folder_id, tenant_id=owner)
        if (not folder or folder.parent_gallery_id != event.parent_gallery_id
                or folder.audience_scope != "selected" or folder.status != "released"):
            return False
        grant = db.scalar(
            select(FolderClientGrant.id)
            .join(GalleryClientState,
                  (GalleryClientState.parent_gallery_id == FolderClientGrant.parent_gallery_id)
                  & (GalleryClientState.client_id == FolderClientGrant.client_id))
            .where(
                FolderClientGrant.tenant_id == owner, GalleryClientState.tenant_id == owner,
                FolderClientGrant.folder_id == folder_id,
                FolderClientGrant.id == grant_id,
                FolderClientGrant.parent_gallery_id == event.parent_gallery_id,
                FolderClientGrant.client_id == event.client_id,
                GalleryClientState.status == "active",
            )
        )
        if not grant:
            return False
    if event.event_type.startswith("payment_"):
        order = owned_record(db, SaleOrder, event.sale_order_id, tenant_id=owner)
        if not order or order.client_id != event.client_id:
            return False
        parts = event.event_key.split(":")
        try:
            communication = owned_record(db, PaymentCommunication, UUID(parts[1]), tenant_id=owner)
        except (ValueError, IndexError):
            return False
        if not communication or communication.client_id != order.client_id:
            return False
        if communication.sale_order_id != order.id:
            group = owned_record(db, PaymentGroup, communication.payment_group_id, tenant_id=owner) if communication.payment_group_id else None
            if not group or group.client_id != order.client_id or order.payment_group_id != group.id:
                return False
        if event.event_type != "payment_reported":
            revision = db.scalar(select(func.count(PaymentConfirmationCorrection.id)).where(
                PaymentConfirmationCorrection.tenant_id == owner,
                PaymentConfirmationCorrection.payment_communication_id == communication.id))
            if communication.status != event.event_type.removeprefix("payment_") or parts[-1] != str(revision):
                return False
    return True


def process_next_notification(channel: str, *, push_sender=None, whatsapp_provider=None) -> bool:
    if channel not in {"push", "whatsapp"}:
        raise ValueError("Canal inválido.")
    with SessionLocal() as db:
        instant = now()
        stale_rows = list(db.scalars(select(NotificationDelivery).join(Tenant, Tenant.id == NotificationDelivery.tenant_id).where(
            Tenant.status == "active",
            NotificationDelivery.channel == channel, NotificationDelivery.status == "processing",
            NotificationDelivery.lease_until <= instant,
        ).with_for_update(of=NotificationDelivery, skip_locked=True).limit(20)))
        for stale in stale_rows:
            stale.status = "unknown" if channel == "whatsapp" else "queued"
            stale.last_error = "interrupted_delivery"
            stale.lease_token = None
            stale.lease_until = None
            stale.next_attempt_at = instant
            event = owned_record(db, NotificationEvent, stale.event_id, tenant_id=stale.tenant_id)
            if event:
                mirror_payment_projection(db, event, stale)
        db.commit()
        item = db.scalar(select(NotificationDelivery).join(Tenant, Tenant.id == NotificationDelivery.tenant_id).where(
            Tenant.status == "active",
            NotificationDelivery.channel == channel, NotificationDelivery.status == "queued",
            NotificationDelivery.next_attempt_at <= instant,
        ).order_by(NotificationDelivery.created_at).with_for_update(of=NotificationDelivery, skip_locked=True).limit(1))
        if not item:
            return bool(stale_rows)
        item_id, lease_token, owner = item.id, uuid4(), item.tenant_id
        result = db.execute(update(NotificationDelivery).where(
            NotificationDelivery.tenant_id == owner, NotificationDelivery.id == item_id, NotificationDelivery.status == "queued",
        ).values(status="processing", lease_token=lease_token,
                 lease_until=instant + timedelta(seconds=60), updated_at=instant))
        if result.rowcount != 1:
            db.rollback()
            return bool(stale_rows)
        db.commit()
        db.expire_all()
        try:
            item = owned_record(db, NotificationDelivery, item_id, tenant_id=owner)
        except HTTPException:
            db.rollback()
            db.execute(update(NotificationDelivery).where(NotificationDelivery.id == item_id,
                NotificationDelivery.tenant_id == owner, NotificationDelivery.lease_token == lease_token).values(
                status="queued", lease_token=None, lease_until=None, last_error="owner_unavailable"))
            db.commit()
            return True
        event = owned_record(db, NotificationEvent, item.event_id, tenant_id=owner)
        setting = db.get(NotificationSetting, (event.tenant_id, event.event_type), populate_existing=True) if event else None
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
        subscription = owned_record(db, PushSubscription, item.subscription_id, tenant_id=owner) if channel == "push" else None
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
                    if not recipient_allowed(db, event, item):
                        raise ValueError("Destinatário não autorizado.")
                    subscription = owned_record(db, PushSubscription, item.subscription_id, tenant_id=owner)
                    session = owned_record(db, AuthSession, subscription.session_id, tenant_id=owner) if subscription else None
                    if (not subscription or not subscription.active or subscription.generation != item.subscription_generation
                            or not session or session.revoked_at or session.subject_id != item.recipient_id or session.role != item.recipient_role
                            or utc(session.expires_at) <= now()):
                        raise ValueError("Inscrição revogada.")
                    (push_sender or send_push)(decrypt_subscription(subscription), {
                        "id": str(event.id), "title": event.push_title,
                        "body": event.push_body, "path": event.target_path,
                    }, ttl=max(1, int((utc(event.expires_at) - now()).total_seconds())))
                else:
                    provider = provider_for(db, tenant_id=owner, adapter=whatsapp_provider)
                    require_ready_channel(db, provider, tenant_id=owner)
                    if not recipient_allowed(db, event, item):
                        raise WhatsAppConfigurationError("Destinatário não autorizado.")
                    setting = db.get(NotificationSetting, (owner, event.event_type), populate_existing=True)
                    if (not setting or not setting.whatsapp_enabled or
                            (setting.whatsapp_disabled_at and utc(event.created_at) <= utc(setting.whatsapp_disabled_at))):
                        raise WhatsAppConfigurationError("Canal desativado.")
                    if item.recipient_role == "admin":
                        phone = photographer_phone(db, tenant_id=owner)
                    else:
                        phone = db.scalar(select(ClientPhone.phone_e164).where(
                            ClientPhone.tenant_id == owner, ClientPhone.client_id == item.recipient_id, ClientPhone.active,
                            ClientPhone.verified_at.is_not(None)))
                    if not phone:
                        raise WhatsAppConfigurationError("Destino verificado indisponível.")
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
            except HTTPException:
                db.rollback()
                db.execute(update(NotificationDelivery).where(NotificationDelivery.id == item_id,
                    NotificationDelivery.tenant_id == owner, NotificationDelivery.lease_token == lease_token).values(
                    status="queued", attempts=NotificationDelivery.attempts - 1, lease_token=None, lease_until=None,
                    last_error="owner_unavailable", next_attempt_at=now()))
                db.commit()
                return True
            except Exception:  # noqa: BLE001 - fronteira externa: nunca propagar payload/segredo
                status, error = "unknown", "unexpected_transport_failure"
        # Outro worker pode ter recuperado o lease. Nunca sobrescrever sua decisão.
        current_lease = db.scalar(select(NotificationDelivery.lease_token).where(
            NotificationDelivery.tenant_id == owner, NotificationDelivery.id == item.id).with_for_update())
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
    require_active_owner(db, outbox.tenant_id)
    event = db.scalar(select(NotificationEvent).where(NotificationEvent.tenant_id == outbox.tenant_id, NotificationEvent.event_key == outbox.idempotency_key))
    if not event:
        return False
    setting = db.get(NotificationSetting, (event.tenant_id, event.event_type), populate_existing=True)
    if not setting or not setting.whatsapp_enabled or utc(event.expires_at) <= now():
        raise ValueError("Canal desativado ou aviso expirado.")
    if setting.whatsapp_disabled_at and utc(event.created_at) <= utc(setting.whatsapp_disabled_at):
        raise ValueError("Aviso cancelado; não há reenvio retroativo.")
    deliveries = list(db.scalars(select(NotificationDelivery).where(
        NotificationDelivery.tenant_id == outbox.tenant_id, NotificationDelivery.event_id == event.id, NotificationDelivery.channel == "whatsapp",
    ).with_for_update()))
    if not deliveries or any(item.status != "failed" or item.attempts >= MAX_ATTEMPTS for item in deliveries):
        raise ValueError("Aviso indisponível para retentativa.")
    for item in deliveries:
        if not recipient_allowed(db, event, item):
            raise ValueError("Destinatário não autorizado.")
        item.status, item.last_error, item.next_attempt_at = "queued", None, now()
    return True
