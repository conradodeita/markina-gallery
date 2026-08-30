"""Processamento mínimo e idempotente de webhooks Evolution."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    WhatsAppChannelSettings,
    WhatsAppDelivery,
    WhatsAppWebhookReceipt,
    now,
)
from app.messaging import _normalized_remote_jid
from app.whatsapp_channel import app_environment
from app.whatsapp_delivery import apply_delivery_status

MESSAGE_EVENTS = {"messages.update", "send.message.update"}
CONNECTION_EVENTS = {"connection.update"}


def normalized_event(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", ".")


def webhook_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _message_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, list):
        data = data[0] if data and isinstance(data[0], dict) else {}
    return data if isinstance(data, dict) else {}


def _external_message_id(data: dict[str, Any]) -> str | None:
    key = data.get("key") if isinstance(data.get("key"), dict) else {}
    update = data.get("update") if isinstance(data.get("update"), dict) else {}
    value = key.get("id") or data.get("messageId") or data.get("id") or update.get("id")
    return value if isinstance(value, str) and value else None


def _delivery_state(data: dict[str, Any]) -> str | None:
    update = data.get("update") if isinstance(data.get("update"), dict) else {}
    raw = str(data.get("status") or update.get("status") or "").lower()
    if raw in {"read", "played", "read_ack", "4"}:
        return "read"
    if raw in {"delivered", "delivery_ack", "3"}:
        return "delivered"
    if raw in {"accepted", "pending", "server_ack", "sent", "1", "2"}:
        return "accepted"
    if raw in {"failed", "error", "-1"}:
        return "failed"
    return None


def process_whatsapp_webhook(
    db: Session, payload: dict[str, Any]
) -> tuple[bool, str]:
    fingerprint = webhook_fingerprint(payload)
    if db.scalar(
        select(WhatsAppWebhookReceipt).where(
            WhatsAppWebhookReceipt.fingerprint == fingerprint
        )
    ):
        return False, "duplicate"
    event = normalized_event(payload.get("event"))
    data = _message_data(payload)
    external_id = _external_message_id(data)
    db.add(
        WhatsAppWebhookReceipt(
            fingerprint=fingerprint,
            event_type=event or "ignored",
            external_message_id=external_id,
        )
    )

    if event in MESSAGE_EVENTS and external_id:
        delivery = db.scalar(
            select(WhatsAppDelivery).where(
                WhatsAppDelivery.external_message_id == external_id
            )
        )
        requested = _delivery_state(data)
        if delivery and requested:
            apply_delivery_status(delivery, requested, at=now())
            delivery.provider_status = str(
                data.get("status")
                or (
                    data.get("update", {}).get("status")
                    if isinstance(data.get("update"), dict)
                    else ""
                )
            )
            db.commit()
            return True, "delivery_updated"
    elif event in CONNECTION_EVENTS:
        settings = db.scalar(
            select(WhatsAppChannelSettings).where(
                WhatsAppChannelSettings.environment == app_environment()
            )
        )
        if settings:
            state = str(data.get("state") or data.get("status") or "").lower()
            connected = _normalized_remote_jid(
                data.get("ownerJid") or data.get("number")
            )
            settings.connected_phone_e164 = connected
            settings.last_checked_at = now()
            if state == "open" and connected == settings.expected_phone_e164:
                settings.status = "ready"
                settings.last_error = None
            elif state == "open":
                settings.status = "mismatch"
                settings.last_error = "O número conectado diverge do número esperado."
            elif state == "connecting":
                settings.status = "connecting"
            else:
                settings.status = "disconnected"
            db.commit()
            return True, "connection_updated"
    db.commit()
    return False, "ignored"
