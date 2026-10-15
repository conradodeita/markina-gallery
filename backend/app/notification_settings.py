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
    Client,
    DerivedGallery,
    NotificationDelivery,
    NotificationEvent,
    NotificationSetting,
    ParentGallery,
    PaymentMessageTemplate,
    PaymentNotificationOutbox,
    PushSubscription,
    SaleOrder,
    Tenant,
    TenantAdmin,
    now,
)
from app.client_identity import require_identity_tenant
from app.notification_contract import DEFINITIONS, whatsapp_event_gate_open
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


def validate_text(event_type: str, body: str, limit: int, *, channel: str | None = None) -> str:
    if event_type not in DEFINITIONS:
        raise ValueError("Evento não permitido.")
    allowed = set(DEFINITIONS[event_type].variables)
    if channel == "whatsapp":
        allowed.update(DEFINITIONS[event_type].whatsapp_extra_variables)
    body = validate_template(body, allowed_variables=allowed)
    if limit <= 140 and re.search(r"[\x00-\x1f\x7f]", body):
        raise ValueError("Use uma única linha para a notificação push.")
    if len(body) > limit:
        raise ValueError(f"Use no máximo {limit} caracteres.")
    if not set(PLACEHOLDER.findall(body)).issubset(allowed):
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


def render_whatsapp_text(event_type: str, body: str, values: dict[str, str], limit: int) -> str:
    """Render approved text values and a server-generated purchase URL only."""
    from urllib.parse import urlsplit
    from uuid import UUID

    body = validate_text(event_type, body, limit, channel="whatsapp")
    placeholders = set(PLACEHOLDER.findall(body))
    safe = {key: re.sub(r"[^\w .’'\-]", "", str(values.get(key, "")), flags=re.UNICODE)
            for key in placeholders if key != "link_compras"}
    safe = {key: re.sub(r"(?:https?|www|data)\S*", "", value, flags=re.IGNORECASE)
            for key, value in safe.items()}
    if "link_compras" in placeholders:
        link = str(values.get("link_compras", ""))
        try:
            parsed = urlsplit(link)
            port = parsed.port
            valid_path = parsed.path == "/library/purchases"
            valid_fragment = re.fullmatch(
                r"order-[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
                parsed.fragment, re.IGNORECASE,
            )
            UUID(parsed.fragment.removeprefix("order-"))
            from app.tenant_hosts import normalize_canonical_host
            valid_host = parsed.hostname is not None and normalize_canonical_host(parsed.hostname) == parsed.hostname
        except (ValueError, TypeError):
            parsed, port, valid_host, valid_path, valid_fragment = None, None, False, False, False
        if (not parsed or parsed.scheme != "https" or not valid_host or not valid_path or not valid_fragment
                or parsed.username is not None or parsed.password is not None or port is not None or parsed.query):
            link = ""
        safe["link_compras"] = link
    rendered = PLACEHOLDER.sub(lambda match: safe[match[1]], body)
    while len(rendered) > limit:
        longest = max(safe, key=lambda key: len(safe[key]))
        value = safe[longest].rstrip("…")
        safe[longest] = value[:-2] + "…" if len(value) > 2 else ""
        rendered = PLACEHOLDER.sub(lambda match: safe[match[1]], body)
    return rendered


def setting_for(db: Session, event_type: str, *, tenant_id: UUID) -> NotificationSetting:
    require_identity_tenant(db, tenant_id)
    if event_type not in DEFINITIONS:
        raise ValueError("Evento não permitido.")
    setting = db.get(NotificationSetting, (tenant_id, event_type))
    if setting:
        return setting
    definition = DEFINITIONS[event_type]
    kind = event_type.removeprefix("payment_")
    legacy = db.scalar(select(PaymentMessageTemplate).where(
        PaymentMessageTemplate.tenant_id == tenant_id, PaymentMessageTemplate.kind == kind,
    ))
    body = legacy.body if legacy else DEFAULT_PAYMENT_TEMPLATES.get(kind, definition.whatsapp_body or definition.body)
    try:
        with notification_savepoint(db):
            setting = NotificationSetting(tenant_id=tenant_id, event_type=event_type, whatsapp_body=body,
                                          push_title=definition.title, push_body=definition.body)
            db.add(setting)
            db.flush()
    except IntegrityError:
        setting = db.get(NotificationSetting, (tenant_id, event_type))
        if setting is None:
            raise
    return setting


def payment_template_bodies(db: Session, *, tenant_id: UUID) -> dict[str, str]:
    """Leitura única, sem writes no dashboard nem consultas por template ausente."""
    require_identity_tenant(db, tenant_id)
    rows = db.execute(select(
        PaymentMessageTemplate.kind, PaymentMessageTemplate.body, literal(0).label("priority"),
    ).where(PaymentMessageTemplate.tenant_id == tenant_id).union_all(select(
        NotificationSetting.event_type, NotificationSetting.whatsapp_body, literal(1),
    ).where(NotificationSetting.tenant_id == tenant_id, NotificationSetting.event_type.in_(["payment_confirmed", "payment_refused"]))))
    result = dict(DEFAULT_PAYMENT_TEMPLATES)
    for kind, body, _ in sorted(rows, key=lambda row: row.priority):
        result[kind.removeprefix("payment_")] = body
    return result


def payment_template_migration_sources(db: Session, *, tenant_id: UUID) -> dict[str, str]:
    """Read effective payment templates without creating settings or changing versions."""
    require_identity_tenant(db, tenant_id)
    event_types = ("payment_reported", "payment_confirmed", "payment_refused")
    configured = {
        setting.event_type: setting
        for setting in db.scalars(select(NotificationSetting).where(
            NotificationSetting.tenant_id == tenant_id,
            NotificationSetting.event_type.in_(event_types)
        ))
    }
    legacy_bodies = payment_template_bodies(db, tenant_id=tenant_id)
    sources: dict[str, str] = {}
    for event_type in event_types:
        setting = configured.get(event_type)
        for field in ("whatsapp_body", "push_body", "push_title"):
            if setting:
                body = getattr(setting, field)
            elif field == "whatsapp_body" and event_type in {"payment_confirmed", "payment_refused"}:
                body = legacy_bodies[event_type.removeprefix("payment_")]
            else:
                definition = DEFINITIONS[event_type]
                body = definition.title if field == "push_title" else definition.body
            sources[f"{event_type}.{field}"] = body
    return sources


def setting_payload(setting: NotificationSetting) -> dict:
    definition = DEFINITIONS[setting.event_type]
    return {
        "event_type": setting.event_type, "label": definition.label,
        "recipient": definition.recipient, "allowed_variables": list(definition.variables),
        "whatsapp_variables": [*definition.variables, *definition.whatsapp_extra_variables],
        "whatsapp_enabled": setting.whatsapp_enabled, "push_enabled": setting.push_enabled,
        "whatsapp_body": setting.whatsapp_body, "push_title": setting.push_title,
        "push_body": setting.push_body, "version": setting.version,
        "preview": {
            "push_title": render_text(setting.event_type, setting.push_title,
                                       {"cliente": "Cliente", "galeria": "Galeria", "pedido": "1234abcd",
                                        "contexto_pagamento": "da compra 1234abcd"}, 60),
            "push_body": render_text(setting.event_type, setting.push_body,
                                      {"cliente": "Cliente", "galeria": "Galeria", "pedido": "1234abcd",
                                       "contexto_pagamento": "da compra 1234abcd"}, 140),
            "whatsapp_body": render_whatsapp_text(
                setting.event_type, setting.whatsapp_body,
                {"cliente": "Cliente", "galeria": "Galeria", "pedido": "1234abcd",
                 "contexto_pagamento": "da compra 1234abcd",
                 "link_compras": "https://fotografo.exemplo/library/purchases#order-00000000-0000-4000-8000-000000000000"}, 500),
        },
    }


def save_setting(db: Session, event_type: str, values: dict, *, tenant_id: UUID) -> NotificationSetting:
    setting_for(db, event_type, tenant_id=tenant_id)
    setting = db.scalar(select(NotificationSetting).where(
        NotificationSetting.tenant_id == tenant_id,
        NotificationSetting.event_type == event_type).with_for_update())
    if "version" in values and values["version"] != setting.version:
        raise ValueError("A configuração mudou. Atualize a página antes de salvar.")
    validated = {
        "push_title": validate_text(event_type, values.get("push_title", setting.push_title), 60),
        "push_body": validate_text(event_type, values.get("push_body", setting.push_body), 140),
        "whatsapp_body": validate_text(event_type, values.get("whatsapp_body", setting.whatsapp_body),
                                        500, channel="whatsapp"),
    }
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
                NotificationDelivery.tenant_id == tenant_id,
                NotificationDelivery.event_id.in_(select(NotificationEvent.id).where(
                    NotificationEvent.tenant_id == tenant_id,
                    NotificationEvent.event_type == event_type)),
                NotificationDelivery.channel == channel,
                NotificationDelivery.status == "queued",
            ).values(status="cancelled", last_error="channel_disabled", updated_at=now()))
            if channel == "whatsapp":
                db.execute(update(PaymentNotificationOutbox).where(
                    PaymentNotificationOutbox.tenant_id == tenant_id,
                    PaymentNotificationOutbox.idempotency_key.in_(select(NotificationEvent.event_key).where(
                        NotificationEvent.tenant_id == tenant_id,
                        NotificationEvent.event_type == event_type)),
                    PaymentNotificationOutbox.status == "queued",
                ).values(status="failed", last_error="channel_disabled"))
    setting.version += 1
    setting.updated_at = now()
    return setting


def enqueue_event(db: Session, *, event_type: str, event_key: str, values: dict[str, str],
                  target_path: str, recipients: list[UUID], parent_gallery_id=None,
                  derived_gallery_id=None, client_id=None, sale_order_id=None,
                  tenant_id: UUID) -> NotificationEvent:
    """Só persiste na transação chamadora. Nunca envia, commita ou reproduz histórico."""
    require_identity_tenant(db, tenant_id)
    for model, resource_id in ((ParentGallery, parent_gallery_id), (DerivedGallery, derived_gallery_id),
                               (Client, client_id), (SaleOrder, sale_order_id)):
        if resource_id is not None and not db.scalar(select(model.id).where(
            model.id == resource_id, model.tenant_id == tenant_id,
        )):
            raise ValueError("Contexto de aviso incompatível.")
    definition = DEFINITIONS[event_type]
    for recipient in set(recipients):
        if definition.recipient == "admin":
            valid = db.scalar(select(TenantAdmin.id).where(
                TenantAdmin.tenant_id == tenant_id, TenantAdmin.admin_user_id == recipient,
                TenantAdmin.active.is_(True),
            ))
        else:
            valid = db.scalar(select(Client.id).where(Client.id == recipient, Client.tenant_id == tenant_id))
        if not valid:
            raise ValueError("Destinatário indisponível.")
    existing = db.scalar(select(NotificationEvent).where(
        NotificationEvent.tenant_id == tenant_id, NotificationEvent.event_key == event_key,
    ))
    if existing:
        return existing
    setting = setting_for(db, event_type, tenant_id=tenant_id)
    whatsapp_values = dict(values)
    whatsapp_link_required = (event_type == "order_delivery_ready"
                              and "{{link_compras}}" in setting.whatsapp_body)
    whatsapp_link_available = not whatsapp_link_required
    if whatsapp_link_required:
        from app.tenant_hosts import CanonicalHostError, purchase_url_for_tenant

        tenant = db.get(Tenant, tenant_id, populate_existing=True)
        order = db.scalar(select(SaleOrder).where(
            SaleOrder.id == sale_order_id,
            SaleOrder.tenant_id == tenant_id,
            SaleOrder.client_id == client_id,
        ).execution_options(populate_existing=True)) if sale_order_id else None
        try:
            if not tenant or not order:
                raise CanonicalHostError("Contexto de pedido indisponível.")
            whatsapp_values["link_compras"] = purchase_url_for_tenant(db, tenant, order.id)
            whatsapp_link_available = True
        except CanonicalHostError:
            # Keep the business action (album availability) committed; the
            # worker revalidates and cancels this delivery without a valid URL.
            whatsapp_values["link_compras"] = ""
    try:
        with notification_savepoint(db):
            event = NotificationEvent(
                tenant_id=tenant_id,
                event_key=event_key, event_type=event_type, parent_gallery_id=parent_gallery_id,
                derived_gallery_id=derived_gallery_id, client_id=client_id,
                sale_order_id=sale_order_id, template_version=setting.version,
                push_title=render_text(event_type, setting.push_title, values, 60),
                push_body=render_text(event_type, setting.push_body, values, 140),
                whatsapp_body=render_whatsapp_text(event_type, setting.whatsapp_body,
                                                   whatsapp_values, 500),
                target_path=target_path, expires_at=now() + timedelta(hours=1),
            )
            db.add(event)
            db.flush()
            for recipient in set(recipients):
                if setting.whatsapp_enabled:
                    global_gate_enabled = os.getenv("TRANSACTIONAL_WHATSAPP_ENABLED", "false").lower() == "true"
                    whatsapp_status = "queued" if whatsapp_event_gate_open(
                        event_type, global_gate_enabled=global_gate_enabled,
                    ) else "cancelled"
                    whatsapp_error = None if whatsapp_status == "queued" else "transport_disabled"
                    if not whatsapp_link_available:
                        whatsapp_status, whatsapp_error = "cancelled", "canonical_host_unavailable"
                    db.add(NotificationDelivery(tenant_id=tenant_id, event_id=event.id, channel="whatsapp",
                                               recipient_role=definition.recipient,
                                               recipient_id=recipient,
                                               client_recipient_id=recipient if definition.recipient == "client" else None,
                                               admin_recipient_id=recipient if definition.recipient == "admin" else None,
                                               status=whatsapp_status, last_error=whatsapp_error))
                if setting.push_enabled:
                    subscriptions = db.scalars(select(PushSubscription).where(
                        PushSubscription.tenant_id == tenant_id,
                        PushSubscription.subject_id == recipient,
                        PushSubscription.role == definition.recipient, PushSubscription.active,
                    ))
                    for subscription in subscriptions:
                        db.add(NotificationDelivery(
                            tenant_id=tenant_id,
                            event_id=event.id, channel="push", recipient_role=definition.recipient,
                            recipient_id=recipient, device_key=str(subscription.id),
                            client_recipient_id=recipient if definition.recipient == "client" else None,
                            admin_recipient_id=recipient if definition.recipient == "admin" else None,
                            subscription_id=subscription.id,
                            subscription_generation=subscription.generation,
                            status="queued" if os.getenv("WEB_PUSH_ENABLED", "false").lower() == "true" else "cancelled",
                            last_error=None if os.getenv("WEB_PUSH_ENABLED", "false").lower() == "true" else "transport_disabled",
                        ))
            db.flush()
    except IntegrityError:
        event = db.scalar(select(NotificationEvent).where(
            NotificationEvent.tenant_id == tenant_id, NotificationEvent.event_key == event_key,
        ))
        if event is None:
            raise
    return event
