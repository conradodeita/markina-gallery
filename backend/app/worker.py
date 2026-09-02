"""Worker isolado para mídia privada e entregas transacionais."""

import os
import time
from datetime import timedelta
from uuid import UUID

from sqlalchemy import case, or_, select, update
from sqlalchemy.orm import Session

from app.admin_security import (
    AdminSecurityConfigurationError,
    cleanup_admin_security_material,
    decrypt_sensitive_payload,
)
from app.auth import (
    Client,
    DerivedGallery,
    EmailDelivery,
    EmailDeliveryAttempt,
    GalleryMembershipNotificationOutbox,
    MediaJob,
    PaymentCommunication,
    PaymentMessageTemplate,
    PaymentNotificationOutbox,
    PhotoAsset,
    SaleOrder,
    SessionLocal,
    WhatsAppDelivery,
    WhatsAppDeliveryAttempt,
    cleanup_expired_client_otp_pii,
    expired,
    now,
)
from app.email_delivery import (
    EmailConfigurationError,
    EmailDeliveryError,
    EmailProvider,
    email_provider_from_environment,
)
from app.gallery_cleanup import (
    prepare_lifecycle_history,
    remove_operational_records,
    remove_operational_storage,
)
from app.gallery_lifecycle import (
    LifecycleStageHandler,
    claim_next_operation,
    process_claimed_operation,
)
from app.media import generate_derivatives
from app.membership_notifications import (
    process_next_membership_notification as process_membership_outbox,
)
from app.messaging import (
    WhatsAppConfigurationError,
    WhatsAppDeliveryError,
    configured_photographer_phone,
    payment_notification_max_attempts,
    whatsapp_provider_from_environment,
)
from app.payment_templates import DEFAULT_PAYMENT_TEMPLATES, render_template
from app.whatsapp_channel import require_ready_channel
from app.whatsapp_delivery import (
    apply_delivery_status,
    decrypt_otp,
    otp_encryption_key,
)


def sanitized_delivery_error(error: Exception) -> str:
    """Retorna somente categoria operacional, nunca conteúdo ou credencial."""
    if isinstance(error, WhatsAppConfigurationError):
        return "Configuração do provedor indisponível."
    if isinstance(error, WhatsAppDeliveryError):
        return str(error)
    return "Falha transitória de entrega."


def payment_notification_message(db: Session, item: PaymentNotificationOutbox) -> str:
    """Valida relação/destino e renderiza sem registrar o corpo em logs."""
    communication = db.get(PaymentCommunication, item.payment_communication_id)
    order = db.get(SaleOrder, communication.sale_order_id) if communication else None
    client = db.get(Client, communication.client_id) if communication else None
    gallery = db.get(DerivedGallery, order.derived_gallery_id) if order else None
    if not communication or not order or not client or not gallery:
        raise WhatsAppConfigurationError("Relação da notificação indisponível.")

    if item.template_kind == "photographer_reported":
        photographer_phone = configured_photographer_phone()
        if not photographer_phone or item.recipient_phone != photographer_phone:
            raise WhatsAppConfigurationError("Destino do fotógrafo não autorizado.")
        return (
            f"Pagamento comunicado para o pedido {str(order.id)[:8]} de "
            f"{client.full_name}, galeria {gallery.name}. Revise no painel administrativo."
        )

    if item.template_kind not in DEFAULT_PAYMENT_TEMPLATES:
        raise WhatsAppConfigurationError("Tipo de template não autorizado.")
    if communication.client_id != order.client_id or item.recipient_phone != client.phone_e164:
        raise WhatsAppConfigurationError("Destino da cliente não autorizado.")
    template = db.scalar(
        select(PaymentMessageTemplate).where(PaymentMessageTemplate.kind == item.template_kind)
    )
    body = template.body if template else DEFAULT_PAYMENT_TEMPLATES[item.template_kind]
    return render_template(
        body,
        cliente=order.client_name_snapshot or client.full_name,
        pedido=str(order.id)[:8],
        galeria=gallery.name,
    )


def materialize_payment_delivery(db: Session, item: PaymentNotificationOutbox) -> WhatsAppDelivery:
    delivery = db.scalar(
        select(WhatsAppDelivery).where(WhatsAppDelivery.idempotency_key == item.idempotency_key)
    )
    if delivery:
        return delivery
    delivery = WhatsAppDelivery(
        kind="payment",
        source_type="payment_notification_outbox",
        source_id=str(item.id),
        recipient_phone=item.recipient_phone,
        template_kind=item.template_kind,
        idempotency_key=item.idempotency_key,
        status="queued"
        if item.status in {"queued", "processing"}
        else ("accepted" if item.status == "sent" else "failed"),
        attempts=item.attempts,
        last_error=item.last_error,
    )
    db.add(delivery)
    db.flush()
    return delivery


def mirror_payment_delivery(db: Session, delivery: WhatsAppDelivery) -> None:
    if delivery.kind != "payment" or delivery.source_type != "payment_notification_outbox":
        return
    try:
        item_id = UUID(delivery.source_id)
    except ValueError:
        return
    item = db.get(PaymentNotificationOutbox, item_id)
    if not item:
        return
    if delivery.status in {"accepted", "delivered", "read"}:
        item.status = "sent"
    elif delivery.status in {"failed", "unknown", "expired"}:
        item.status = "failed"
    else:
        item.status = "queued"
    item.attempts = delivery.attempts
    item.last_error = delivery.last_error
    item.updated_at = now()


def delivery_message(db: Session, delivery: WhatsAppDelivery) -> str:
    if delivery.kind == "otp":
        if not delivery.encrypted_payload:
            raise WhatsAppConfigurationError("Payload OTP indisponível.")
        return (
            "Seu código de acesso Markina Gallery é "
            f"{decrypt_otp(delivery.encrypted_payload, key=otp_encryption_key(), context=delivery.idempotency_key)}."
        )
    if delivery.kind == "payment":
        try:
            item_id = UUID(delivery.source_id)
        except ValueError as exc:
            raise WhatsAppConfigurationError("Relação da notificação indisponível.") from exc
        item = db.get(PaymentNotificationOutbox, item_id)
        if not item:
            raise WhatsAppConfigurationError("Relação da notificação indisponível.")
        return payment_notification_message(db, item)
    raise WhatsAppConfigurationError("Tipo de entrega não autorizado.")


def _record_attempt(
    db: Session,
    delivery: WhatsAppDelivery,
    result: str,
    *,
    external_message_id: str | None = None,
    error_category: str | None = None,
) -> None:
    db.add(
        WhatsAppDeliveryAttempt(
            delivery_id=delivery.id,
            attempt_number=delivery.attempts,
            result=result,
            external_message_id=external_message_id,
            error_category=error_category,
        )
    )


def process_next_media_job() -> bool:
    """Reserva e executa um job pendente, retornando se havia trabalho."""
    with SessionLocal() as db:
        job = db.scalar(
            select(MediaJob)
            .where(MediaJob.kind == "generate_derivatives", MediaJob.status == "queued")
            .order_by(MediaJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not job:
            return False
        job.status = "processing"
        job.attempts += 1
        job.updated_at = now()
        db.commit()

        photo = db.get(PhotoAsset, job.photo_asset_id)
        if not photo:
            job.status = "failed"
            job.last_error = "Foto de origem não encontrada."
            job.updated_at = now()
            db.commit()
            return True
        generate_derivatives(db, photo, job)
        return True


def process_next_gallery_lifecycle_operation(
    *, handlers: dict[str, LifecycleStageHandler] | None = None
) -> bool:
    """Reserva e avança uma operação; etapas ausentes falham de modo sanitizado."""

    with SessionLocal() as db:
        claim = claim_next_operation(db)
    if not claim:
        return False
    operation_id, lease_token = claim
    with SessionLocal() as db:
        process_claimed_operation(
            db,
            operation_id=operation_id,
            lease_token=lease_token,
            handlers=handlers
            or {
                "preparing_history": prepare_lifecycle_history,
                "removing_storage": remove_operational_storage,
                "removing_records": remove_operational_records,
            },
        )
    return True


def process_next_whatsapp_delivery(*, kind: str | None = None) -> bool:
    with SessionLocal() as db:
        try:
            max_attempts = payment_notification_max_attempts()
        except WhatsAppConfigurationError:
            max_attempts = 1
        instant = now()
        stale_before = instant - timedelta(
            seconds=max(30, int(os.getenv("WHATSAPP_PROCESSING_TIMEOUT_SECONDS", "120")))
        )
        recovered_stale = False
        for stale in db.scalars(
            select(WhatsAppDelivery).where(
                WhatsAppDelivery.status == "processing",
                WhatsAppDelivery.updated_at < stale_before,
            )
        ):
            stale.status = "unknown"
            stale.last_error = "Processamento interrompido; reconciliação necessária."
            stale.updated_at = instant
            mirror_payment_delivery(db, stale)
            recovered_stale = True
        db.commit()
        filters = [
            WhatsAppDelivery.status == "queued",
            WhatsAppDelivery.recipient_phone.is_not(None),
            WhatsAppDelivery.attempts < max_attempts,
            or_(
                WhatsAppDelivery.next_attempt_at.is_(None),
                WhatsAppDelivery.next_attempt_at <= instant,
            ),
        ]
        if kind:
            filters.append(WhatsAppDelivery.kind == kind)
        delivery = db.scalar(
            select(WhatsAppDelivery)
            .where(*filters)
            .order_by(
                case((WhatsAppDelivery.kind == "otp", 0), else_=1),
                WhatsAppDelivery.expires_at.asc(),
                WhatsAppDelivery.created_at,
            )
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not delivery:
            return recovered_stale
        delivery_id = delivery.id
        claimed = db.execute(
            update(WhatsAppDelivery)
            .where(
                WhatsAppDelivery.id == delivery_id,
                *filters,
            )
            .values(
                status="processing",
                attempts=WhatsAppDelivery.attempts + 1,
                next_attempt_at=None,
                updated_at=instant,
            )
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount != 1:
            db.rollback()
            return recovered_stale
        db.commit()
        db.expire_all()
        delivery = db.get(WhatsAppDelivery, delivery_id)
        if not delivery:
            return recovered_stale

        if delivery.expires_at and expired(delivery.expires_at):
            apply_delivery_status(delivery, "expired", at=instant)
            delivery.encrypted_payload = None
            delivery.last_error = "Entrega expirada antes da aceitação."
            mirror_payment_delivery(db, delivery)
            db.commit()
            return True

        try:
            provider = whatsapp_provider_from_environment()
            require_ready_channel(db, provider)
            message = delivery_message(db, delivery)
            result = provider.send_transactional(
                delivery.recipient_phone,
                message,
                idempotency_key=delivery.idempotency_key,
            )
            if result.recipient_phone_e164 != delivery.recipient_phone:
                raise WhatsAppDeliveryError(
                    "Destinatário divergente na resposta do provedor.",
                    transient=False,
                    ambiguous=True,
                )
            delivery.external_message_id = result.external_message_id
            delivery.provider_status = result.provider_status
            delivery.last_error = None
            apply_delivery_status(delivery, "accepted", at=now())
            if delivery.kind == "otp":
                delivery.encrypted_payload = None
            _record_attempt(
                db,
                delivery,
                "accepted",
                external_message_id=result.external_message_id,
            )
        except (WhatsAppConfigurationError, WhatsAppDeliveryError) as exc:
            if isinstance(exc, WhatsAppDeliveryError) and exc.ambiguous:
                apply_delivery_status(delivery, "unknown", at=now())
                attempt_result = "unknown"
            elif (
                isinstance(exc, WhatsAppDeliveryError)
                and exc.transient
                and delivery.attempts < max_attempts
            ):
                delivery.status = "queued"
                delay = max(0, int(os.getenv("WHATSAPP_RETRY_BASE_SECONDS", "2")))
                delivery.next_attempt_at = now() + timedelta(
                    seconds=min(delay * (2 ** (delivery.attempts - 1)), 300)
                )
                attempt_result = "transient_failure"
            else:
                apply_delivery_status(delivery, "failed", at=now())
                delivery.encrypted_payload = None
                attempt_result = "permanent_failure"
            delivery.last_error = sanitized_delivery_error(exc)
            _record_attempt(
                db,
                delivery,
                attempt_result,
                error_category=delivery.last_error,
            )
        mirror_payment_delivery(db, delivery)
        db.commit()
        return True


def process_next_email_delivery(*, provider: EmailProvider | None = None) -> bool:
    """Reserva uma entrega de e-mail e nunca repete resultado ambíguo."""

    with SessionLocal() as db:
        instant = now()
        stale_before = instant - timedelta(
            seconds=max(30, int(os.getenv("EMAIL_PROCESSING_TIMEOUT_SECONDS", "120")))
        )
        recovered_stale = False
        for stale in db.scalars(
            select(EmailDelivery).where(
                EmailDelivery.status == "processing",
                EmailDelivery.updated_at < stale_before,
            )
        ):
            stale.status = "unknown"
            stale.encrypted_payload = None
            stale.last_error = "Processamento interrompido; reconciliação manual necessária."
            stale.updated_at = instant
            recovered_stale = True
        db.commit()
        max_attempts = max(1, min(int(os.getenv("EMAIL_MAX_ATTEMPTS", "3")), 10))
        filters = [
            EmailDelivery.status == "queued",
            EmailDelivery.attempts < max_attempts,
            or_(EmailDelivery.next_attempt_at.is_(None), EmailDelivery.next_attempt_at <= instant),
        ]
        delivery = db.scalar(
            select(EmailDelivery)
            .where(*filters)
            .order_by(EmailDelivery.expires_at, EmailDelivery.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not delivery:
            return recovered_stale
        delivery_id = delivery.id
        claimed = db.execute(
            update(EmailDelivery)
            .where(EmailDelivery.id == delivery_id, *filters)
            .values(
                status="processing",
                attempts=EmailDelivery.attempts + 1,
                next_attempt_at=None,
                updated_at=instant,
            )
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount != 1:
            db.rollback()
            return recovered_stale
        db.commit()
        db.expire_all()
        delivery = db.get(EmailDelivery, delivery_id)
        if not delivery:
            return recovered_stale
        if expired(delivery.expires_at):
            delivery.status = "expired"
            delivery.encrypted_payload = None
            delivery.last_error = "Entrega expirada antes da aceitação."
            delivery.updated_at = instant
            db.commit()
            return True
        try:
            if not delivery.encrypted_payload:
                raise EmailConfigurationError("Payload de e-mail indisponível.")
            payload = decrypt_sensitive_payload(
                delivery.encrypted_payload,
                context=f"email-delivery:{delivery.id}:{delivery.idempotency_key}",
            )
            active_provider = provider or email_provider_from_environment()
            result = active_provider.send(
                recipient=str(payload["recipient"]),
                subject=str(payload["subject"]),
                text_body=str(payload["text_body"]),
                idempotency_key=delivery.idempotency_key,
            )
            delivery.status = "accepted"
            delivery.external_message_id = result.external_message_id
            delivery.accepted_at = now()
            delivery.encrypted_payload = None
            delivery.last_error = None
            delivery.updated_at = now()
            db.add(
                EmailDeliveryAttempt(
                    delivery_id=delivery.id,
                    attempt_number=delivery.attempts,
                    result="accepted",
                    external_message_id=result.external_message_id,
                )
            )
        except (
            AdminSecurityConfigurationError,
            EmailConfigurationError,
            EmailDeliveryError,
            KeyError,
        ) as exc:
            ambiguous = isinstance(exc, EmailDeliveryError) and exc.ambiguous
            transient = isinstance(exc, EmailDeliveryError) and exc.transient and not ambiguous
            if ambiguous:
                delivery.status = "unknown"
                attempt_result = "unknown"
            elif transient and delivery.attempts < max_attempts:
                delivery.status = "queued"
                delay = max(1, int(os.getenv("EMAIL_RETRY_BASE_SECONDS", "2")))
                delivery.next_attempt_at = now() + timedelta(
                    seconds=min(delay * (2 ** (delivery.attempts - 1)), 300)
                )
                attempt_result = "transient_failure"
            else:
                delivery.status = "failed"
                attempt_result = "permanent_failure"
            if delivery.status in {"unknown", "failed"}:
                delivery.encrypted_payload = None
            delivery.last_error = (
                "Resultado do envio requer reconciliação manual."
                if ambiguous
                else "Falha transitória de e-mail."
                if transient
                else "Configuração ou entrega de e-mail indisponível."
            )
            delivery.updated_at = now()
            db.add(
                EmailDeliveryAttempt(
                    delivery_id=delivery.id,
                    attempt_number=delivery.attempts,
                    result=attempt_result,
                    error_category=delivery.last_error,
                )
            )
        db.commit()
        return True


def materialize_next_payment_notification() -> bool:
    with SessionLocal() as db:
        item = db.scalar(
            select(PaymentNotificationOutbox)
            .where(PaymentNotificationOutbox.status == "queued")
            .order_by(PaymentNotificationOutbox.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not item:
            return False
        existing = db.scalar(
            select(WhatsAppDelivery).where(WhatsAppDelivery.idempotency_key == item.idempotency_key)
        )
        if existing:
            mirror_payment_delivery(db, existing)
            db.commit()
            return False
        delivery = materialize_payment_delivery(db, item)
        mirror_payment_delivery(db, delivery)
        db.commit()
        return True


def process_next_payment_notification() -> bool:
    materialized = materialize_next_payment_notification()
    processed = process_next_whatsapp_delivery(kind="payment")
    return materialized or processed


def process_next_gallery_membership_notification() -> bool:
    """Entrega opcional ao fotógrafo sem acoplar a transação de associação."""

    labels = {
        "private_created": "Nova galeria privada criada",
        "member_joined": "Novo cliente na galeria privada",
        "member_blocked": "Cliente bloqueado na galeria privada",
        "member_unblocked": "Cliente desbloqueado na galeria privada",
        "member_unlinked": "Cliente desvinculado da galeria privada",
    }
    with SessionLocal() as db:
        def send(notification: GalleryMembershipNotificationOutbox) -> None:
            recipient = configured_photographer_phone()
            if not recipient:
                raise WhatsAppConfigurationError("Destino do fotógrafo não configurado.")
            provider = whatsapp_provider_from_environment()
            label = labels[notification.event_type]
            client_suffix = (
                f" Cliente: {notification.client_name_snapshot}."
                if notification.client_name_snapshot
                else ""
            )
            provider.send_transactional(
                recipient,
                f"{label}: {notification.derived_name_snapshot}."
                f" Origem: {notification.parent_name_snapshot}.{client_suffix}",
            )

        return process_membership_outbox(db, send)


def reconcile_next_unknown_delivery() -> bool:
    with SessionLocal() as db:
        delivery = db.scalar(
            select(WhatsAppDelivery)
            .where(
                WhatsAppDelivery.status == "unknown",
                WhatsAppDelivery.external_message_id.is_not(None),
            )
            .order_by(WhatsAppDelivery.updated_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not delivery or not delivery.external_message_id:
            return False
        provider = whatsapp_provider_from_environment()
        result = provider.reconcile(delivery.external_message_id)
        if not result:
            return False
        delivery.provider_status = result.provider_status
        if result.provider_status.lower() in {"read", "played"}:
            apply_delivery_status(delivery, "read", at=now())
        elif result.provider_status.lower() in {"delivered", "delivery_ack"}:
            apply_delivery_status(delivery, "delivered", at=now())
        else:
            apply_delivery_status(delivery, "accepted", at=now())
        mirror_payment_delivery(db, delivery)
        db.commit()
        return True


def main() -> None:
    print("markina-gallery-worker: pronto para filas privadas", flush=True)
    while True:
        if not (
            process_next_gallery_lifecycle_operation()
            or process_next_media_job()
            or process_next_whatsapp_delivery()
            or process_next_email_delivery()
            or materialize_next_payment_notification()
            or process_next_gallery_membership_notification()
            or reconcile_next_unknown_delivery()
            or process_otp_privacy_cleanup()
            or process_admin_security_cleanup()
        ):
            time.sleep(2)


_last_otp_privacy_cleanup = 0.0


def process_otp_privacy_cleanup() -> bool:
    """Executa a limpeza periódica sem transformar o loop em consulta contínua."""

    global _last_otp_privacy_cleanup
    instant = time.monotonic()
    interval = max(5, int(os.getenv("AUTH_OTP_CLEANUP_INTERVAL_SECONDS", "60")))
    if instant - _last_otp_privacy_cleanup < interval:
        return False
    _last_otp_privacy_cleanup = instant
    with SessionLocal() as db:
        return cleanup_expired_client_otp_pii(db) > 0


_last_admin_security_cleanup = 0.0


def process_admin_security_cleanup() -> bool:
    global _last_admin_security_cleanup
    instant = time.monotonic()
    interval = max(5, int(os.getenv("ADMIN_SECURITY_CLEANUP_INTERVAL_SECONDS", "60")))
    if instant - _last_admin_security_cleanup < interval:
        return False
    _last_admin_security_cleanup = instant
    with SessionLocal() as db:
        return cleanup_admin_security_material(db) > 0


if __name__ == "__main__":
    main()
