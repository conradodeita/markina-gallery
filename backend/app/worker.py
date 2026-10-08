"""Worker isolado para mídia privada e notificações transacionais."""

import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    DerivedGallery,
    MediaJob,
    PaymentCommunication,
    PaymentMessageTemplate,
    PaymentNotificationOutbox,
    PhotoAsset,
    SaleOrder,
    SessionLocal,
    now,
)
from app.media import generate_derivatives
from app.messaging import (
    WhatsAppConfigurationError,
    WhatsAppDeliveryError,
    configured_photographer_phone,
    payment_notification_max_attempts,
    whatsapp_provider_from_environment,
)
from app.payment_templates import DEFAULT_PAYMENT_TEMPLATES, render_template


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
        select(PaymentMessageTemplate).where(
            PaymentMessageTemplate.kind == item.template_kind
        )
    )
    body = template.body if template else DEFAULT_PAYMENT_TEMPLATES[item.template_kind]
    return render_template(
        body,
        cliente=order.client_name_snapshot or client.full_name,
        pedido=str(order.id)[:8],
        galeria=gallery.name,
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


def process_next_payment_notification() -> bool:
    with SessionLocal() as db:
        try:
            max_attempts = payment_notification_max_attempts()
        except WhatsAppConfigurationError:
            max_attempts = 1
        item = db.scalar(
            select(PaymentNotificationOutbox)
            .where(
                PaymentNotificationOutbox.status == "queued",
                PaymentNotificationOutbox.attempts < max_attempts,
            )
            .order_by(PaymentNotificationOutbox.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not item:
            return False
        item.status, item.attempts = "processing", item.attempts + 1
        item.updated_at = now()
        db.commit()
        try:
            provider = whatsapp_provider_from_environment()
            message = payment_notification_message(db, item)
            provider.send_transactional(
                item.recipient_phone,
                message,
                idempotency_key=item.idempotency_key,
            )
            item.status, item.last_error = "sent", None
        except (WhatsAppConfigurationError, WhatsAppDeliveryError) as exc:
            transient = isinstance(exc, WhatsAppDeliveryError) and exc.transient
            item.status = "queued" if transient and item.attempts < max_attempts else "failed"
            item.last_error = sanitized_delivery_error(exc)
        item.updated_at = now()
        db.commit()
        return True


def main() -> None:
    print("markina-gallery-worker: pronto para processar mídia privada", flush=True)
    while True:
        if not process_next_media_job() and not process_next_payment_notification():
            time.sleep(2)


if __name__ == "__main__":
    main()
