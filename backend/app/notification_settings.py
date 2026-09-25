"""Configuração global e snapshots imutáveis dos eventos transacionais."""

import os
import re
from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID

from sqlalchemy import literal, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    NotificationDelivery,
    NotificationEvent,
    NotificationSetting,
    PaymentMessageTemplate,
    PaymentNotificationOutbox,
    PushSubscription,
    now,
)
from app.notification_contract import DEFINITIONS
from app.payment_templates import DEFAULT_PAYMENT_TEMPLATES, PLACEHOLDER, validate_template


@contextmanager
def notification_savepoint(db: Session):
    # sqlite3 em modo legado não inicia transação com SELECT/SAVEPOINT.
    # Sem BEGIN, RELEASE tornaria a outbox durável antes do commit do negócio.
    connection = db.connection()
    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN")
    with db.begin_nested():
        yield


def validate_text(event_type: str, body: str, limit: int) -> str:
    if event_type not in DEFINITIONS:
        raise ValueError("Evento não permitido.")
    body = validate_template(body)
    if limit <= 140 and re.search(r"[\x00-\x1f\x7f]", body):
        raise ValueError("Use uma única linha para a notificação push.")
    if len(body) > limit:
        raise ValueError(f"Use no máximo {limit} caracteres.")
    if not set(PLACEHOLDER.findall(body)).issubset(DEFINITIONS[event_type].variables):
        raise ValueError("Variável não permitida para este evento.")
    return body


def render_text(event_type: str, body: str, values: dict[str, str], limit: int) -> str:
    body = validate_text(event_type, body, limit)
    # Valores são nomes/referências, nunca HTML/URL ou instruções para o navegador.
    safe = {key: re.sub(r"[^\w .’'\-]", "", str(values.get(key, "")), flags=re.UNICODE)
            for key in set(PLACEHOLDER.findall(body))}
    safe = {key: re.sub(r"(?:https?|www|data)\S*", "", value, flags=re.IGNORECASE)
            for key, value in safe.items()}
    rendered = PLACEHOLDER.sub(lambda match: safe[match[1]], body)
    while len(rendered) > limit:
        longest = max(safe, key=lambda key: len(safe[key]))
        value = safe[longest].rstrip("…")
        safe[longest] = value[:-2] + "…" if len(value) > 2 else ""
        rendered = PLACEHOLDER.sub(lambda match: safe[match[1]], body)
    return rendered


def setting_for(db: Session, event_type: str) -> NotificationSetting:
    if event_type not in DEFINITIONS:
        raise ValueError("Evento não permitido.")
    setting = db.get(NotificationSetting, event_type)
    if setting:
        return setting
    definition = DEFINITIONS[event_type]
    kind = event_type.removeprefix("payment_")
    legacy = db.scalar(select(PaymentMessageTemplate).where(PaymentMessageTemplate.kind == kind))
    body = legacy.body if legacy else DEFAULT_PAYMENT_TEMPLATES.get(kind, definition.body)
    try:
        with notification_savepoint(db):
            setting = NotificationSetting(event_type=event_type, whatsapp_body=body,
                                          push_title=definition.title, push_body=definition.body)
            db.add(setting)
            db.flush()
    except IntegrityError:
        setting = db.get(NotificationSetting, event_type)
        if setting is None:
            raise
    return setting


def payment_template_bodies(db: Session) -> dict[str, str]:
    """Leitura única, sem writes no dashboard nem consultas por template ausente."""
    rows = db.execute(select(
        PaymentMessageTemplate.kind, PaymentMessageTemplate.body, literal(0).label("priority"),
    ).union_all(select(
        NotificationSetting.event_type, NotificationSetting.whatsapp_body, literal(1),
    ).where(NotificationSetting.event_type.in_(["payment_confirmed", "payment_refused"]))))
    result = dict(DEFAULT_PAYMENT_TEMPLATES)
    for kind, body, _ in sorted(rows, key=lambda row: row.priority):
        result[kind.removeprefix("payment_")] = body
    return result


def setting_payload(setting: NotificationSetting) -> dict:
    definition = DEFINITIONS[setting.event_type]
    return {
        "event_type": setting.event_type, "label": definition.label,
        "recipient": definition.recipient, "allowed_variables": list(definition.variables),
        "whatsapp_enabled": setting.whatsapp_enabled, "push_enabled": setting.push_enabled,
        "whatsapp_body": setting.whatsapp_body, "push_title": setting.push_title,
        "push_body": setting.push_body, "version": setting.version,
        "preview": {field: render_text(setting.event_type, getattr(setting, field),
                                      {"cliente": "Cliente", "galeria": "Galeria", "pedido": "1234abcd"},
                                      limit)
                    for field, limit in (("push_title", 60), ("push_body", 140),
                                         ("whatsapp_body", 500))},
    }


def save_setting(db: Session, event_type: str, values: dict) -> NotificationSetting:
    setting_for(db, event_type)
    setting = db.scalar(select(NotificationSetting).where(
        NotificationSetting.event_type == event_type).with_for_update())
    if "version" in values and values["version"] != setting.version:
        raise ValueError("A configuração mudou. Atualize a página antes de salvar.")
    validated = {field: validate_text(event_type, values.get(field, getattr(setting, field)), limit)
                 for field, limit in (("push_title", 60), ("push_body", 140), ("whatsapp_body", 500))}
    for field, value in validated.items():
        setattr(setting, field, value)
    for channel in ("push", "whatsapp"):
        field = f"{channel}_enabled"
        if field in values:
            setattr(setting, field, values[field])
        if not getattr(setting, field):
            setattr(setting, f"{channel}_disabled_at", now())
            # Não cancelar tentativa em voo; worker revalida antes de qualquer retry.
            db.execute(update(NotificationDelivery).where(
                NotificationDelivery.event_id.in_(select(NotificationEvent.id).where(
                    NotificationEvent.event_type == event_type)),
                NotificationDelivery.channel == channel,
                NotificationDelivery.status == "queued",
            ).values(status="cancelled", last_error="channel_disabled", updated_at=now()))
            if channel == "whatsapp":
                db.execute(update(PaymentNotificationOutbox).where(
                    PaymentNotificationOutbox.idempotency_key.in_(select(NotificationEvent.event_key).where(
                        NotificationEvent.event_type == event_type)),
                    PaymentNotificationOutbox.status == "queued",
                ).values(status="failed", last_error="channel_disabled"))
    setting.version += 1
    setting.updated_at = now()
    return setting


def enqueue_event(db: Session, *, event_type: str, event_key: str, values: dict[str, str],
                  target_path: str, recipients: list[UUID], parent_gallery_id=None,
                  derived_gallery_id=None, client_id=None, sale_order_id=None) -> NotificationEvent:
    """Só persiste na transação chamadora. Nunca envia, commita ou reproduz histórico."""
    existing = db.scalar(select(NotificationEvent).where(NotificationEvent.event_key == event_key))
    if existing:
        return existing
    setting = setting_for(db, event_type)
    definition = DEFINITIONS[event_type]
    try:
        with notification_savepoint(db):
            event = NotificationEvent(
                event_key=event_key, event_type=event_type, parent_gallery_id=parent_gallery_id,
                derived_gallery_id=derived_gallery_id, client_id=client_id,
                sale_order_id=sale_order_id, template_version=setting.version,
                push_title=render_text(event_type, setting.push_title, values, 60),
                push_body=render_text(event_type, setting.push_body, values, 140),
                whatsapp_body=render_text(event_type, setting.whatsapp_body, values, 500),
                target_path=target_path, expires_at=now() + timedelta(hours=1),
            )
            db.add(event)
            db.flush()
            for recipient in set(recipients):
                if setting.whatsapp_enabled:
                    db.add(NotificationDelivery(event_id=event.id, channel="whatsapp",
                                               recipient_role=definition.recipient,
                                               recipient_id=recipient,
                                               status="queued" if event_type.startswith("payment_") or os.getenv("TRANSACTIONAL_WHATSAPP_ENABLED", "false").lower() == "true" else "cancelled",
                                               last_error=None if event_type.startswith("payment_") or os.getenv("TRANSACTIONAL_WHATSAPP_ENABLED", "false").lower() == "true" else "transport_disabled"))
                if setting.push_enabled:
                    subscriptions = db.scalars(select(PushSubscription).where(
                        PushSubscription.subject_id == recipient,
                        PushSubscription.role == definition.recipient, PushSubscription.active,
                    ))
                    for subscription in subscriptions:
                        db.add(NotificationDelivery(
                            event_id=event.id, channel="push", recipient_role=definition.recipient,
                            recipient_id=recipient, device_key=str(subscription.id),
                            subscription_id=subscription.id,
                            subscription_generation=subscription.generation,
                            status="queued" if os.getenv("WEB_PUSH_ENABLED", "false").lower() == "true" else "cancelled",
                            last_error=None if os.getenv("WEB_PUSH_ENABLED", "false").lower() == "true" else "transport_disabled",
                        ))
            db.flush()
    except IntegrityError:
        event = db.scalar(select(NotificationEvent).where(NotificationEvent.event_key == event_key))
        if event is None:
            raise
    return event
