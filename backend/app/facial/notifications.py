"""Outbox transacional neutra para conclusão de consultas faciais."""

from __future__ import annotations

import json
import os
from datetime import timedelta
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    ParentGalleryRegistration,
    now,
)
from app.facial.config import FacialSettings
from app.facial.crypto import FacialCipher, FacialEnvelope, FacialScope
from app.messaging import (
    WhatsAppConfigurationError,
    WhatsAppDeliveryError,
    WhatsAppProvider,
)
from app.whatsapp_channel import require_ready_channel


def enqueue_search_notification(
    db: Session,
    *,
    request: FacialSearchRequest,
    result_status: str,
    cipher: FacialCipher,
    settings: FacialSettings,
) -> FacialSearchNotificationOutbox | None:
    result_kind = _result_kind(result_status)
    if result_kind is None:
        return None
    idempotency_key = f"facial-search:{request.id}:{result_kind}"
    existing = db.scalar(
        select(FacialSearchNotificationOutbox).where(
            FacialSearchNotificationOutbox.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return existing
    encoded = json.dumps(
        {
            "path": f"/public-galleries/{request.parent_gallery_id}",
            "result": result_kind,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    envelope = cipher.encrypt(
        encoded,
        scope=_notification_scope(request, settings),
    )
    notification = FacialSearchNotificationOutbox(
        search_request_id=request.id,
        parent_gallery_id=request.parent_gallery_id,
        client_id=request.client_id,
        result_kind=result_kind,
        status="queued",
        idempotency_key=idempotency_key,
        payload_ciphertext=envelope.ciphertext,
        payload_nonce=envelope.nonce,
        key_id=envelope.key_id,
        available_at=now(),
    )
    try:
        with db.begin_nested():
            db.add(notification)
            db.flush()
    except IntegrityError:
        return db.scalar(
            select(FacialSearchNotificationOutbox).where(
                FacialSearchNotificationOutbox.idempotency_key == idempotency_key
            )
        )
    return notification


def process_next_search_notification(
    db: Session,
    *,
    provider: WhatsAppProvider,
    cipher: FacialCipher,
    settings: FacialSettings,
    max_attempts: int = 3,
) -> bool:
    current = now()
    recovered_interrupted = False
    for interrupted in db.scalars(
        select(FacialSearchNotificationOutbox).where(
            FacialSearchNotificationOutbox.status == "processing",
            FacialSearchNotificationOutbox.lease_expires_at <= current,
        )
    ):
        # Uma queda após o envio é ambígua; não reenviar preserva "no máximo uma".
        interrupted.status = "failed"
        interrupted.last_error_category = "ambiguous_delivery"
        interrupted.payload_ciphertext = b""
        interrupted.payload_nonce = b""
        interrupted.lease_expires_at = None
        interrupted.updated_at = current
        recovered_interrupted = True
    db.commit()

    notification = db.scalar(
        select(FacialSearchNotificationOutbox)
        .where(
            FacialSearchNotificationOutbox.status == "queued",
            FacialSearchNotificationOutbox.attempts < max_attempts,
            FacialSearchNotificationOutbox.available_at <= current,
        )
        .order_by(FacialSearchNotificationOutbox.available_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if notification is None:
        return recovered_interrupted
    notification.status = "processing"
    notification.attempts += 1
    notification.lease_expires_at = current + timedelta(minutes=2)
    notification.updated_at = current
    db.commit()

    request = db.get(FacialSearchRequest, notification.search_request_id)
    client = db.get(Client, notification.client_id)
    registration = db.scalar(
        select(ParentGalleryRegistration.id).where(
            ParentGalleryRegistration.parent_gallery_id
            == notification.parent_gallery_id,
            ParentGalleryRegistration.client_id == notification.client_id,
            ParentGalleryRegistration.status == "active",
        )
    )
    if (
        request is None
        or request.status == "cancelled"
        or request.parent_gallery_id != notification.parent_gallery_id
        or request.client_id != notification.client_id
        or client is None
        or not registration
    ):
        _cancel(notification)
        db.commit()
        return True
    try:
        message = _notification_message(
            notification,
            request=request,
            cipher=cipher,
            settings=settings,
        )
        require_ready_channel(db, provider)
        result = provider.send_transactional(
            client.phone_e164,
            message,
            idempotency_key=notification.idempotency_key,
        )
        if result.recipient_phone_e164 != client.phone_e164:
            raise WhatsAppDeliveryError(
                "Destinatário divergente na resposta do provedor.",
                transient=False,
                ambiguous=True,
            )
    except (WhatsAppConfigurationError, WhatsAppDeliveryError) as error:
        ambiguous = isinstance(error, WhatsAppDeliveryError) and error.ambiguous
        transient = isinstance(error, WhatsAppDeliveryError) and error.transient
        retryable = isinstance(error, WhatsAppConfigurationError) or transient
        if retryable and not ambiguous and notification.attempts < max_attempts:
            notification.status = "queued"
            notification.available_at = now() + timedelta(
                seconds=min(2 ** notification.attempts, 300)
            )
        else:
            notification.status = "failed"
            notification.payload_ciphertext = b""
            notification.payload_nonce = b""
        notification.last_error_category = (
            "ambiguous_delivery"
            if ambiguous
            else (
                "channel_unavailable"
                if isinstance(error, WhatsAppConfigurationError)
                else "delivery_unavailable"
            )
        )
        notification.lease_expires_at = None
        notification.updated_at = now()
        db.commit()
        return True

    notification.status = "sent"
    notification.external_message_id = result.external_message_id
    notification.sent_at = now()
    notification.last_error_category = None
    notification.payload_ciphertext = b""
    notification.payload_nonce = b""
    notification.lease_expires_at = None
    notification.updated_at = now()
    db.commit()
    return True


def cancel_pending_search_notifications(
    db: Session, *, request_id: UUID
) -> None:
    for notification in db.scalars(
        select(FacialSearchNotificationOutbox).where(
            FacialSearchNotificationOutbox.search_request_id == request_id,
            FacialSearchNotificationOutbox.status.in_(("queued", "processing")),
        )
    ):
        _cancel(notification)


def _notification_message(
    notification: FacialSearchNotificationOutbox,
    *,
    request: FacialSearchRequest,
    cipher: FacialCipher,
    settings: FacialSettings,
) -> str:
    envelope = FacialEnvelope(
        ciphertext=notification.payload_ciphertext,
        nonce=notification.payload_nonce,
        key_id=notification.key_id,
    )
    try:
        payload = json.loads(
            cipher.decrypt(
                envelope, scope=_notification_scope(request, settings)
            )
        )
    except (UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise WhatsAppConfigurationError("Payload transacional inválido.") from exc
    expected_path = f"/public-galleries/{request.parent_gallery_id}"
    if payload != {"path": expected_path, "result": notification.result_kind}:
        raise WhatsAppConfigurationError("Payload transacional inválido.")
    base_url = os.getenv("MARKINA_PUBLIC_URL", "").strip().rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
        raise WhatsAppConfigurationError("URL pública da aplicação indisponível.")
    link = f"{base_url}{expected_path}"
    if notification.result_kind == "ready":
        return f"Sua busca na galeria foi concluída. Confira as possibilidades em {link}"
    if notification.result_kind == "no_candidates":
        return f"Sua busca terminou sem possibilidades encontradas. Continue em {link}"
    return f"Não foi possível concluir sua busca. Tente novamente em {link}"


def _notification_scope(
    request: FacialSearchRequest, settings: FacialSettings
) -> FacialScope:
    return FacialScope(
        environment=settings.environment,
        gallery_id=request.parent_gallery_id,
        object_kind="request",
        object_id=request.id,
        purpose="notification",
        model_version=request.model_version,
        data_version=request.consent_version,
    )


def _result_kind(status: str) -> str | None:
    if status in {"ready", "no_candidates"}:
        return status
    if status in {"no_face", "multiple_faces", "low_quality", "index_incomplete", "failed"}:
        return "failed"
    return None


def _cancel(notification: FacialSearchNotificationOutbox) -> None:
    notification.status = "cancelled"
    notification.payload_ciphertext = b""
    notification.payload_nonce = b""
    notification.lease_expires_at = None
    notification.updated_at = now()
