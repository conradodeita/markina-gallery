"""Outbox idempotente de notificações administrativas de galerias privadas."""

import os
from collections.abc import Callable
from datetime import timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    DerivedGallery,
    GalleryMembershipNotificationOutbox,
    ParentGallery,
    now,
)

EXTERNAL_MAX_ATTEMPTS = 3


def enqueue_membership_notification(
    db: Session,
    *,
    event_key: str,
    event_type: str,
    parent: ParentGallery,
    gallery: DerivedGallery,
    client: Client | None = None,
) -> tuple[GalleryMembershipNotificationOutbox, bool]:
    existing = db.scalar(
        select(GalleryMembershipNotificationOutbox).where(
            GalleryMembershipNotificationOutbox.event_key == event_key
        )
    )
    if existing:
        return existing, False
    external_enabled = (
        os.getenv("GALLERY_NOTIFICATION_EXTERNAL_ENABLED", "false").strip().lower()
        == "true"
    )
    try:
        with db.begin_nested():
            notification = GalleryMembershipNotificationOutbox(
                event_key=event_key,
                event_type=event_type,
                parent_gallery_id=parent.id,
                derived_gallery_id=gallery.id,
                client_id=client.id if client else None,
                parent_name_snapshot=parent.name,
                derived_name_snapshot=gallery.name,
                client_name_snapshot=client.full_name if client else None,
                external_status="queued" if external_enabled else "skipped",
            )
            db.add(notification)
            db.flush()
        return notification, True
    except IntegrityError:
        existing = db.scalar(
            select(GalleryMembershipNotificationOutbox).where(
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
        select(GalleryMembershipNotificationOutbox)
        .where(
            GalleryMembershipNotificationOutbox.external_status == "queued",
            or_(
                GalleryMembershipNotificationOutbox.next_attempt_at.is_(None),
                GalleryMembershipNotificationOutbox.next_attempt_at <= instant,
            ),
        )
        .order_by(GalleryMembershipNotificationOutbox.created_at)
        .with_for_update(skip_locked=True)
    )
    if not notification:
        return False
    notification.external_status = "processing"
    notification.attempts += 1
    db.flush()
    try:
        sender(notification)
    except Exception as exc:  # noqa: BLE001 - fronteira sanitizada do adaptador
        notification.last_error = type(exc).__name__[:120]
        if notification.attempts >= EXTERNAL_MAX_ATTEMPTS:
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
    notification_id: UUID,
) -> GalleryMembershipNotificationOutbox | None:
    notification = db.get(GalleryMembershipNotificationOutbox, notification_id)
    if notification:
        notification.admin_status = "read"
    return notification
