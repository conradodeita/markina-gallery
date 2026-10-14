"""Outbox idempotente de notificações administrativas de galerias e acessos."""

import os
from collections.abc import Callable
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    Client,
    DerivedGallery,
    GalleryMembershipNotificationOutbox,
    ParentGallery,
    Tenant,
    now,
)
from app.client_identity import require_identity_tenant

EXTERNAL_MAX_ATTEMPTS = 3


def enqueue_membership_notification(
    db: Session,
    *,
    event_key: str,
    event_type: str,
    parent: ParentGallery,
    gallery: DerivedGallery | None,
    client: Client | None = None,
) -> tuple[GalleryMembershipNotificationOutbox, bool]:
    require_identity_tenant(db, parent.tenant_id)
    if (gallery and (gallery.tenant_id != parent.tenant_id or gallery.parent_gallery_id != parent.id)) or (client and client.tenant_id != parent.tenant_id):
        raise ValueError("Contexto de aviso incompatível.")
    existing = db.scalar(
        select(GalleryMembershipNotificationOutbox).where(
            GalleryMembershipNotificationOutbox.tenant_id == parent.tenant_id,
            GalleryMembershipNotificationOutbox.event_key == event_key
        )
    )
    if existing:
        return existing, False
    external_enabled = event_type not in {"client_logged_in", "private_created"} and (
        os.getenv("GALLERY_NOTIFICATION_EXTERNAL_ENABLED", "false").strip().lower()
        == "true"
    )
    try:
        with db.begin_nested():
            notification = GalleryMembershipNotificationOutbox(
                tenant_id=parent.tenant_id,
                event_key=event_key,
                event_type=event_type,
                parent_gallery_id=parent.id,
                derived_gallery_id=gallery.id if gallery else None,
                client_id=client.id if client else None,
                parent_name_snapshot=parent.name,
                derived_name_snapshot=gallery.name if gallery else parent.name,
                client_name_snapshot=client.full_name if client else None,
                external_status="queued" if external_enabled else "skipped",
            )
            db.add(notification)
            db.flush()
        return notification, True
    except IntegrityError:
        existing = db.scalar(
            select(GalleryMembershipNotificationOutbox).where(
                GalleryMembershipNotificationOutbox.tenant_id == parent.tenant_id,
                GalleryMembershipNotificationOutbox.event_key == event_key
            )
        )
        if not existing:
            raise
        return existing, False


def process_next_membership_notification(
    db: Session,
    sender: Callable[[GalleryMembershipNotificationOutbox], None],
) -> bool:
    instant = now()
    notification = db.scalar(
        select(GalleryMembershipNotificationOutbox).join(Tenant, Tenant.id == GalleryMembershipNotificationOutbox.tenant_id)
        .where(
            Tenant.status == "active", GalleryMembershipNotificationOutbox.external_status == "queued",
            or_(
                GalleryMembershipNotificationOutbox.next_attempt_at.is_(None),
                GalleryMembershipNotificationOutbox.next_attempt_at <= instant,
            ),
        )
        .order_by(GalleryMembershipNotificationOutbox.created_at)
        .with_for_update(of=GalleryMembershipNotificationOutbox, skip_locked=True)
    )
    if not notification:
        return False
    notification.external_status = "processing"
    notification.attempts += 1
    db.flush()
    try:
        require_active_owner(db, notification.tenant_id)
        parent = owned_record(db, ParentGallery, notification.parent_gallery_id, tenant_id=notification.tenant_id)
        if not parent or not parent.active or parent.lifecycle_status != "active":
            raise ValueError("Origem indisponível.")
        if notification.derived_gallery_id and not owned_record(db, DerivedGallery, notification.derived_gallery_id, tenant_id=notification.tenant_id):
            raise ValueError("Origem indisponível.")
        if notification.client_id and not owned_record(db, Client, notification.client_id, tenant_id=notification.tenant_id):
            raise ValueError("Destinatário indisponível.")
        sender(notification)
    except HTTPException:
        notification.external_status = "queued"
        notification.attempts -= 1
        db.commit()
        return True
    except Exception as exc:  # noqa: BLE001 - fronteira sanitizada do adaptador
        notification.last_error = type(exc).__name__[:120]
        if getattr(exc, "ambiguous", False) or notification.attempts >= EXTERNAL_MAX_ATTEMPTS:
            notification.external_status = "failed"
            notification.next_attempt_at = None
        else:
            notification.external_status = "queued"
            notification.next_attempt_at = instant + timedelta(
                minutes=2 ** (notification.attempts - 1)
            )
        db.commit()
        return True
    notification.external_status = "sent"
    notification.last_error = None
    notification.next_attempt_at = None
    db.commit()
    return True


def mark_membership_notification_read(
    db: Session,
    notification_id: UUID, *, tenant_id: UUID,
) -> GalleryMembershipNotificationOutbox | None:
    notification = owned_record(db, GalleryMembershipNotificationOutbox, notification_id, tenant_id=tenant_id)
    if notification:
        notification.admin_status = "read"
    return notification
