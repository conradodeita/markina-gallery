"""Worker isolado para mídia privada e entregas transacionais."""

import logging
import os
import signal
import threading
import time
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import case, or_, select, update
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
from app.admin_security import (
    AdminSecurityConfigurationError,
    cleanup_admin_security_material,
    decrypt_sensitive_payload,
)
from app.auth import (
    AdminActionToken,
    AdminSecurityChallenge,
    AdminUser,
    AuthChallenge,
    AuthSession,
    Client,
    DerivedGallery,
    EmailDelivery,
    EmailDeliveryAttempt,
    GalleryAccessCapability,
    GalleryMembershipNotificationOutbox,
    GalleryReopeningNotificationOutbox,
    GalleryReopeningRequest,
    MediaArchiveOperation,
    MediaDerivative,
    MediaJob,
    NotificationEvent,
    ParentGallery,
    PaymentCommunication,
    PaymentGroup,
    PaymentNotificationOutbox,
    PhotoAsset,
    PhotographerSignup,
    SaleOrder,
    SessionLocal,
    Tenant,
    TenantClosureIdentityVerification,
    TenantClosureRequest,
    WhatsAppDelivery,
    WhatsAppDeliveryAttempt,
    cleanup_expired_client_otp_pii,
    expired,
    now,
    pii_fingerprint,
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
from app.media_archive_synthetic_storage import SyntheticMediaArchiveStorage
from app.membership_notifications import (
    process_next_membership_notification as process_membership_outbox,
)
from app.messaging import (
    WhatsAppConfigurationError,
    WhatsAppDeliveryError,
    payment_notification_max_attempts,
)
from app.notification_delivery import process_next_notification
from app.notification_settings import setting_for
from app.payment_templates import DEFAULT_PAYMENT_TEMPLATES, render_template
from app.private_upload_batches import process_ready_batches
from app.product_brand import PRODUCT_NAME
from app.system_monitor.telemetry import observe_work
from app.tenancy import (
    TenantContextError,
    domain_session,
    require_admin_tenant,
)
from app.whatsapp_binding import photographer_phone, provider_for
from app.whatsapp_channel import require_ready_channel
from app.whatsapp_delivery import (
    apply_delivery_status,
    decrypt_otp,
    otp_encryption_key,
)

_MEDIA_ARCHIVE_LOG = logging.getLogger("app.media_archive_worker")
_last_media_archive_discovery = 0.0
_MEDIA_ARCHIVE_DISCOVERY_INTERVAL_SECONDS = 60


@dataclass(frozen=True)
class SyntheticMediaArchiveBinding:
    """Vínculo local explícito; não provisiona identidade nem habilita Drive real."""

    storage: object
    tenant_id: UUID
    storage_tenant_id: UUID
    media_root: str
    namespace: str = "gallery-media-v1"
    purpose: str = "synthetic-media-pilot"

    def valid(self) -> bool:
        return (
            type(self.storage) is SyntheticMediaArchiveStorage
            and isinstance(self.tenant_id, UUID)
            and self.storage_tenant_id == self.tenant_id
            and isinstance(self.media_root, str)
            and self.media_root.startswith("synthetic:")
            and len(self.media_root) > len("synthetic:")
            and self.namespace == "gallery-media-v1"
            and self.purpose == "synthetic-media-pilot"
            and all(callable(getattr(self.storage, method, None)) for method in (
                "upload_object", "read_object", "download_object", "delete_object",
            ))
        )


def configure_media_archive_storage(storage) -> None:
    """Runtime fechado até existir vínculo operacional durável aprovado."""
    raise TypeError("Vínculo sintético não pode configurar o runtime de arquivo frio.")



def _media_archive_worker_enabled() -> bool:
    return os.getenv("MEDIA_ARCHIVE_WORKER_ENABLED", "false").strip().lower() == "true"


def process_next_media_archive_operation(
    *, storage=None, enabled: bool | None = None, capacity_provider=None,
) -> bool:
    """Descobre e executa um job somente com gate e adapter explícitos.

    O runtime não seleciona providers nem lê credenciais. A descoberta também
    fica fechada quando o adapter ou a configuração privada de staging faltam.
    """
    global _last_media_archive_discovery
    gate_open = _media_archive_worker_enabled() if enabled is None else enabled is True
    # O loop não tem vínculo operacional aprovado. Fixtures só entram por
    # argumento direto em ambiente local, com sessão e raízes descartáveis.
    if storage is None or os.getenv("APP_ENV", "development") == "production":
        return False
    adapter = storage
    if not gate_open or adapter is None:
        return False
    tenant_scope = None
    if isinstance(adapter, SyntheticMediaArchiveBinding):
        if not adapter.valid():
            return False
        tenant_scope = adapter.tenant_id
        adapter = adapter.storage

    from app.media_archive_staging import MediaArchiveStagingError, configured_staging_root

    try:
        staging_root = configured_staging_root()
    except MediaArchiveStagingError as exc:
        _MEDIA_ARCHIVE_LOG.warning(
            "Media archive worker não iniciado; staging inválido (%s).", exc.code,
        )
        return False

    from app.media_archive_scheduler import (
        enqueue_due_archive_window_notices,
        enqueue_eligible_archive_operations,
    )

    monotonic_now = time.monotonic()
    if monotonic_now - _last_media_archive_discovery >= _MEDIA_ARCHIVE_DISCOVERY_INTERVAL_SECONDS:
        with SessionLocal() as db:
            enqueue_due_archive_window_notices(db, tenant_id=tenant_scope)
            enqueue_eligible_archive_operations(db, tenant_id=tenant_scope)
        _last_media_archive_discovery = time.monotonic()

    from app.media_archive_executor import (
        execute_archive_operation,
        execute_delete_operation,
        execute_restore_operation,
    )
    from app.media_archive_worker import claim_next_operation

    with SessionLocal() as db:
        claim = claim_next_operation(db, tenant_id=tenant_scope)
    if claim is None:
        return False

    with SessionLocal() as db:
        operation_type = db.scalar(select(MediaArchiveOperation.operation_type).where(
            MediaArchiveOperation.id == claim.operation_id,
            MediaArchiveOperation.tenant_id == claim.tenant_id,
        ))
        if operation_type == "archive":
            execute_archive_operation(db, claim, storage=adapter)
        elif operation_type == "delete_remote":
            execute_delete_operation(db, claim, storage=adapter)
        elif operation_type == "restore":
            execute_restore_operation(
                db,
                claim,
                storage=adapter,
                staging_root=staging_root,
                capacity_provider=capacity_provider,
            )
        else:
            raise RuntimeError("A fila de arquivo frio contém operação não suportada.")
    return True


def sanitized_delivery_error(error: Exception) -> str:
    """Retorna somente categoria operacional, nunca conteúdo ou credencial."""
    if isinstance(error, WhatsAppConfigurationError):
        return "Configuração do provedor indisponível."
    if isinstance(error, WhatsAppDeliveryError):
        return str(error)
    return "Falha transitória de entrega."


def payment_notification_message(db: Session, item: PaymentNotificationOutbox) -> str:
    """Valida relação/destino e renderiza sem registrar o corpo em logs."""
    require_active_owner(db, item.tenant_id)
    communication = owned_record(db, PaymentCommunication, item.payment_communication_id, tenant_id=item.tenant_id)
    order = owned_record(db, SaleOrder, communication.sale_order_id, tenant_id=item.tenant_id) if communication else None
    client = owned_record(db, Client, communication.client_id, tenant_id=item.tenant_id) if communication else None
    gallery = owned_record(db, DerivedGallery, order.derived_gallery_id, tenant_id=item.tenant_id) if order else None
    parent = owned_record(db, ParentGallery, order.parent_gallery_id, tenant_id=item.tenant_id) if order and order.parent_gallery_id else None
    if not communication or not order or not client or not (gallery or parent):
        raise WhatsAppConfigurationError("Relação da notificação indisponível.")
    gallery_name = gallery.name if gallery else parent.name

    if item.template_kind == "photographer_reported":
        destination = photographer_phone(db, tenant_id=item.tenant_id)
        if not destination or item.recipient_phone != destination:
            raise WhatsAppConfigurationError("Destino do fotógrafo não autorizado.")
        return (
            f"Pagamento comunicado para o pedido {str(order.id)[:8]} de "
            f"{client.full_name}, galeria {gallery_name}. Revise no painel administrativo."
        )

    if item.template_kind not in DEFAULT_PAYMENT_TEMPLATES:
        raise WhatsAppConfigurationError("Tipo de template não autorizado.")
    if communication.client_id != order.client_id or item.recipient_phone != client.phone_e164:
        raise WhatsAppConfigurationError("Destino da cliente não autorizado.")
    if item.rendered_body_snapshot:
        return item.rendered_body_snapshot
    body = setting_for(db, f"payment_{item.template_kind}", tenant_id=item.tenant_id).whatsapp_body
    group = owned_record(db, PaymentGroup, communication.payment_group_id, tenant_id=item.tenant_id) if communication.payment_group_id else None
    if communication.payment_group_id and (not group or group.client_id != client.id):
        raise WhatsAppConfigurationError("Compra agrupada da notificação indisponível.")
    order_code = str(group.id if group else order.id)[:8]
    payment_context = (f"da compra {order_code}" if group else
                       f"do pedido {order_code} da galeria {order.derived_gallery_name_snapshot or gallery.name}")
    return render_template(
        body,
        cliente=order.client_name_snapshot or client.full_name,
        pedido=order_code,
        galeria="sua compra" if group else (order.derived_gallery_name_snapshot or gallery.name),
        contexto_pagamento=payment_context,
    )


def materialize_payment_delivery(db: Session, item: PaymentNotificationOutbox) -> WhatsAppDelivery:
    require_active_owner(db, item.tenant_id)
    delivery = db.scalar(
        select(WhatsAppDelivery).where(WhatsAppDelivery.tenant_id == item.tenant_id, WhatsAppDelivery.idempotency_key == item.idempotency_key)
    )
    if delivery:
        return delivery
    delivery = WhatsAppDelivery(
        tenant_id=item.tenant_id, kind="payment",
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
    item = db.scalar(select(PaymentNotificationOutbox).where(PaymentNotificationOutbox.id == item_id,
        PaymentNotificationOutbox.tenant_id == delivery.tenant_id))
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


def validate_otp_origin(db: Session, delivery: WhatsAppDelivery):
    try:
        source = UUID(delivery.source_id)
    except ValueError:
        raise WhatsAppConfigurationError("Origem OTP indisponível.") from None
    owner = delivery.tenant_id
    if delivery.source_type == "auth_challenge":
        challenge = owned_record(db, AuthChallenge, source, tenant_id=owner)
        if (not challenge or challenge.kind != "client_otp" or challenge.subject != delivery.recipient_phone
                or delivery.idempotency_key != f"otp:{challenge.id}:{challenge.resend_count}"):
            raise WhatsAppConfigurationError("Origem OTP indisponível.")
        if challenge.gallery_capability_id:
            cap = owned_record(db, GalleryAccessCapability, challenge.gallery_capability_id, tenant_id=owner)
            if not cap or cap.revoked_at or (cap.expires_at and expired(cap.expires_at)):
                raise WhatsAppConfigurationError("Origem OTP indisponível.")
        if challenge.parent_gallery_id:
            parent = owned_record(db, ParentGallery, challenge.parent_gallery_id, tenant_id=owner)
            if not parent or not parent.active or parent.lifecycle_status != "active":
                raise WhatsAppConfigurationError("Origem OTP indisponível.")
    elif delivery.source_type == "admin_security_challenge":
        challenge = owned_record(db, AdminSecurityChallenge, source, tenant_id=owner)
        if (not challenge or not challenge.admin_id
                or delivery.idempotency_key != f"admin-security-otp:{challenge.id}:{challenge.resend_count}"
                or delivery.recipient_phone != photographer_phone(db, tenant_id=owner)):
            raise WhatsAppConfigurationError("Origem OTP indisponível.")
        try:
            admin = db.get(AdminUser, challenge.admin_id, populate_existing=True)
            if not admin or not admin.email_verified or require_admin_tenant(db, admin.id).id != owner:
                raise TenantContextError("Acesso negado.")
        except TenantContextError:
            raise WhatsAppConfigurationError("Origem OTP indisponível.") from None
        if challenge.session_id:
            session = owned_record(db, AuthSession, challenge.session_id, tenant_id=owner)
            if not session or session.revoked_at or expired(session.expires_at) or session.subject_id != admin.id:
                raise WhatsAppConfigurationError("Origem OTP indisponível.")
    else:
        raise WhatsAppConfigurationError("Origem OTP indisponível.")
    if challenge.used_at or expired(challenge.expires_at) or challenge.attempts >= 5:
        raise WhatsAppConfigurationError("Origem OTP indisponível.")


def delivery_message(db: Session, delivery: WhatsAppDelivery) -> str:
    require_active_owner(db, delivery.tenant_id)
    if delivery.kind == "otp":
        validate_otp_origin(db, delivery)
        if not delivery.encrypted_payload:
            raise WhatsAppConfigurationError("Payload OTP indisponível.")
        return (
            f"Seu código de acesso {PRODUCT_NAME} é "
            f"{decrypt_otp(delivery.encrypted_payload, key=otp_encryption_key(), context=delivery.idempotency_key)}."
        )
    if delivery.kind == "payment":
        try:
            item_id = UUID(delivery.source_id)
        except ValueError as exc:
            raise WhatsAppConfigurationError("Relação da notificação indisponível.") from exc
        item = owned_record(db, PaymentNotificationOutbox, item_id, tenant_id=delivery.tenant_id)
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
            tenant_id=delivery.tenant_id, delivery_id=delivery.id,
            attempt_number=delivery.attempts,
            result=result,
            external_message_id=external_message_id,
            error_category=error_category,
        )
    )


@observe_work("media")
def process_next_media_job() -> bool:
    """Reserva e executa um job pendente, retornando se havia trabalho."""
    with SessionLocal() as db:
        from app.auth import PhotoAnalysis
        from app.facial.lifecycle import media_can_proceed

        # Só jobs do lifecycle novo: retentativa limitada e recuperação de crash.
        recoverable = list(db.scalars(select(MediaJob).join(PhotoAnalysis,
            PhotoAnalysis.photo_asset_id == MediaJob.photo_asset_id).join(Tenant, Tenant.id == MediaJob.tenant_id).where(
                Tenant.status == "active", Tenant.lifecycle != "closed", PhotoAnalysis.tenant_id == MediaJob.tenant_id,
                MediaJob.kind == "generate_derivatives",
                or_((MediaJob.status == "processing") & (MediaJob.updated_at < now() - timedelta(minutes=10)),
                    (MediaJob.status == "failed") & (MediaJob.updated_at < now() - timedelta(seconds=30))),
                MediaJob.attempts < 3,
                PhotoAnalysis.state.in_(("ready", "failed")),
            ).with_for_update(of=MediaJob, skip_locked=True).limit(64)))
        for stale in recoverable:
            stale.status = "queued"
        db.flush()
        job = db.scalar(
            select(MediaJob).join(Tenant, Tenant.id == MediaJob.tenant_id)
            .where(Tenant.status == "active", Tenant.lifecycle != "closed")
            .where(MediaJob.kind == "generate_derivatives", MediaJob.status == "queued")
            .where(~select(PhotoAnalysis.photo_asset_id).where(
                PhotoAnalysis.tenant_id == MediaJob.tenant_id,
                PhotoAnalysis.photo_asset_id == MediaJob.photo_asset_id,
                PhotoAnalysis.state.in_(("pending", "receiving")),
            ).exists())
            .order_by(MediaJob.created_at)
            .limit(1)
            .with_for_update(of=MediaJob, skip_locked=True)
        )
        if not job:
            db.commit()
            return False
        job.status = "processing"
        job.attempts += 1
        job.updated_at = now()
        db.commit()
        db.refresh(job, with_for_update=True)

        require_active_owner(db, job.tenant_id)
        photo = owned_record(db, PhotoAsset, job.photo_asset_id, tenant_id=job.tenant_id)
        if not photo:
            job.status = "failed"
            job.last_error = "Foto de origem não encontrada."
            job.updated_at = now()
            db.commit()
            return True
        if not media_can_proceed(db, photo.id, tenant_id=job.tenant_id):
            job.status = "queued"
            db.commit()
            return False
        derivatives = {
            item.variant: item
            for item in db.scalars(
                select(MediaDerivative).where(MediaDerivative.tenant_id == job.tenant_id, MediaDerivative.photo_asset_id == photo.id)
            )
        }
        protected_only = bool(
            photo.available
            and derivatives.get("client_preview")
            and derivatives["client_preview"].status == "queued"
            and derivatives.get("thumbnail")
            and derivatives["thumbnail"].status == "ready"
            and derivatives.get("admin_preview")
            and derivatives["admin_preview"].status == "ready"
        )
        generate_derivatives(
            db,
            photo,
            job,
            variants={"client_preview"} if protected_only else None,
        )
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
        try:
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
        except TenantContextError:
            return True  # o executor já liberou somente o lease recusado
        except HTTPException as exc:
            if exc.status_code != 403:
                raise
            return True
    return True


_last_photo_credit_reconciliation = 0.0


def process_next_photo_credit_reconciliation() -> bool:
    """Reconcile uma reserva antiga sem competir com um upload ainda ativo."""
    global _last_photo_credit_reconciliation
    instant = time.monotonic()
    if instant - _last_photo_credit_reconciliation < 30:
        return False
    _last_photo_credit_reconciliation = instant
    from app.photographer_credits import reconcile_next_stale_photo_credit_operation

    with SessionLocal() as db:
        worked = reconcile_next_stale_photo_credit_operation(db)
        if worked:
            db.commit()
        else:
            db.rollback()
        return worked


def process_next_whatsapp_delivery(*, kind: str | None = None, adapter=None) -> bool:
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
            select(WhatsAppDelivery).join(Tenant, Tenant.id == WhatsAppDelivery.tenant_id).where(
                Tenant.status == "active", Tenant.lifecycle != "closed", WhatsAppDelivery.status == "processing",
                WhatsAppDelivery.updated_at < stale_before,
            ).with_for_update(of=(Tenant, WhatsAppDelivery), skip_locked=True)
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
            .join(Tenant, Tenant.id == WhatsAppDelivery.tenant_id)
            .where(Tenant.status == "active", Tenant.lifecycle != "closed", *filters)
            .order_by(
                case((WhatsAppDelivery.kind == "otp", 0), else_=1),
                WhatsAppDelivery.expires_at.asc(),
                WhatsAppDelivery.created_at,
            )
            .limit(1)
            .with_for_update(of=(Tenant, WhatsAppDelivery), skip_locked=True)
        )
        if not delivery:
            return recovered_stale
        delivery_id, owner = delivery.id, delivery.tenant_id
        claimed = db.execute(
            update(WhatsAppDelivery)
            .where(
                WhatsAppDelivery.tenant_id == owner, WhatsAppDelivery.id == delivery_id,
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
        delivery = db.scalar(select(WhatsAppDelivery).where(WhatsAppDelivery.id == delivery_id, WhatsAppDelivery.tenant_id == owner))
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
            provider = provider_for(db, tenant_id=owner, adapter=adapter)
            require_ready_channel(db, provider, tenant_id=owner)
            message = delivery_message(db, delivery)
            require_active_owner(db, owner)
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
        except HTTPException:
            db.rollback()
            db.execute(update(WhatsAppDelivery).where(WhatsAppDelivery.id == delivery_id,
                WhatsAppDelivery.tenant_id == owner, WhatsAppDelivery.status == "processing").values(
                status="queued", attempts=WhatsAppDelivery.attempts - 1, last_error="Conta indisponível.", updated_at=now()))
            db.commit()
            return True
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


def validate_email_origin(db: Session, delivery: EmailDelivery, *, payload=None):
    # SMTP técnico não seleciona canal comercial e não concede acesso a uma conta.
    try:
        source = UUID(delivery.source_id)
    except ValueError:
        raise EmailConfigurationError("Origem de e-mail indisponível.") from None
    expected = None
    if delivery.source_type == "admin_action_token":
        token = db.get(AdminActionToken, source, populate_existing=True)
        purpose = {"password_recovery": "password_reset", "email_verification": "verify_admin_email"}.get(delivery.kind)
        admin = db.get(AdminUser, token.admin_id, populate_existing=True) if token else None
        if not token or token.used_at or expired(token.expires_at) or token.purpose != purpose or not admin or not admin.email_verified:
            raise EmailConfigurationError("Origem de e-mail indisponível.")
        if delivery.kind == "password_recovery":
            expected = pii_fingerprint(admin.email.strip().casefold())
        else:
            expected = token.target_fingerprint
    elif delivery.source_type == "photographer_access_recovery" and delivery.kind == "email_verification":
        from app.photographer_access_recovery import validate_recovery_email
        expected = validate_recovery_email(db, delivery)
    elif delivery.source_type == "admin_user" and delivery.kind == "security_notice":
        if not db.get(AdminUser, source, populate_existing=True):
            raise EmailConfigurationError("Origem de e-mail indisponível.")
        # Destino anterior: o produtor o prova e conserva no envelope autenticado.
        expected = delivery.recipient_fingerprint
    elif (
        delivery.source_type == "photographer_signup"
        and delivery.kind == "email_verification"
    ):
        signup = db.get(PhotographerSignup, source, populate_existing=True)
        if (
            not signup
            or signup.state != "email_pending"
            or expired(signup.otp_expires_at)
            or delivery.idempotency_key
            != f"email:photographer-signup:{signup.id}:{signup.public_request_id}"
        ):
            raise EmailConfigurationError("Origem de e-mail indisponível.")
        expected = pii_fingerprint(signup.email.strip().casefold())
    elif (
        delivery.source_type == "tenant_closure_identity"
        and delivery.kind == "email_verification"
    ):
        challenge = db.get(TenantClosureIdentityVerification, source, populate_existing=True)
        closure = db.get(TenantClosureRequest, challenge.closure_request_id, populate_existing=True) if challenge else None
        tenant = db.get(Tenant, challenge.tenant_id, populate_existing=True) if challenge else None
        if (
            not challenge
            or challenge.state != "email_pending"
            or expired(challenge.expires_at)
            or challenge.email_fingerprint is None
            or delivery.idempotency_key != f"email:tenant-closure-identity:{challenge.id}"
            or not closure
            or closure.tenant_id != challenge.tenant_id
            or closure.state != "closed"
            or not tenant
            or tenant.lifecycle != "closed"
        ):
            raise EmailConfigurationError("Origem de e-mail indisponível.")
        expected = challenge.email_fingerprint
    if not expected or expected != delivery.recipient_fingerprint:
        raise EmailConfigurationError("Origem de e-mail indisponível.")
    if payload is not None and pii_fingerprint(str(payload.get("recipient", "")).strip().casefold()) != expected:
        raise EmailConfigurationError("Destino de e-mail indisponível.")


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
            validate_email_origin(db, delivery)
            payload = decrypt_sensitive_payload(
                delivery.encrypted_payload,
                context=f"email-delivery:{delivery.id}:{delivery.idempotency_key}",
            )
            active_provider = provider or email_provider_from_environment()
            validate_email_origin(db, delivery, payload=payload)
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
            select(PaymentNotificationOutbox).join(Tenant, Tenant.id == PaymentNotificationOutbox.tenant_id)
            .where(Tenant.status == "active", Tenant.lifecycle != "closed", PaymentNotificationOutbox.status == "queued",
                   ~select(NotificationEvent.id).where(
                       NotificationEvent.tenant_id == PaymentNotificationOutbox.tenant_id,
                       NotificationEvent.event_key == PaymentNotificationOutbox.idempotency_key
                   ).exists())
            .order_by(PaymentNotificationOutbox.created_at)
            .limit(1)
            .with_for_update(of=(Tenant, PaymentNotificationOutbox), skip_locked=True)
        )
        if not item:
            return False
        existing = db.scalar(
            select(WhatsAppDelivery).where(WhatsAppDelivery.tenant_id == item.tenant_id, WhatsAppDelivery.idempotency_key == item.idempotency_key)
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
    if process_next_notification("whatsapp"):
        return True
    materialized = materialize_next_payment_notification()
    processed = process_next_whatsapp_delivery(kind="payment")
    return materialized or processed


def process_next_gallery_membership_notification(*, adapter=None) -> bool:
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
            recipient = photographer_phone(db, tenant_id=notification.tenant_id)
            if not recipient:
                raise WhatsAppConfigurationError("Destino do fotógrafo não configurado.")
            provider = provider_for(db, tenant_id=notification.tenant_id, adapter=adapter)
            label = labels[notification.event_type]
            client_suffix = (
                f" Cliente: {notification.client_name_snapshot}."
                if notification.client_name_snapshot
                else ""
            )
            require_ready_channel(db, provider, tenant_id=notification.tenant_id)
            parent = owned_record(db, ParentGallery, notification.parent_gallery_id, tenant_id=notification.tenant_id)
            if not parent or not parent.active or parent.lifecycle_status != "active":
                raise WhatsAppConfigurationError("Origem indisponível.")
            recipient = photographer_phone(db, tenant_id=notification.tenant_id)
            if not recipient:
                raise WhatsAppConfigurationError("Destino indisponível.")
            provider.send_transactional(
                recipient,
                f"{label}: {notification.derived_name_snapshot}."
                f" Origem: {notification.parent_name_snapshot}.{client_suffix}",
                idempotency_key=f"membership:{notification.id}",
            )

        return process_membership_outbox(db, send)


def reopening_origin(db, item):
    owner = item.tenant_id
    source = owned_record(db, GalleryReopeningRequest, item.gallery_reopening_request_id, tenant_id=owner)
    if not source or not owned_record(db, Client, source.requested_by_client_id, tenant_id=owner):
        raise WhatsAppConfigurationError("Origem da reabertura indisponível.")
    gallery = owned_record(db, DerivedGallery, source.derived_gallery_id, tenant_id=owner) if source.derived_gallery_id else None
    parent_id = source.parent_gallery_id or (gallery.parent_gallery_id if gallery else None)
    parent = owned_record(db, ParentGallery, parent_id, tenant_id=owner) if parent_id else None
    if not parent or not parent.active or parent.lifecycle_status != "active":
        raise WhatsAppConfigurationError("Origem da reabertura indisponível.")
    return gallery or parent


def process_next_gallery_reopening_notification(*, adapter=None) -> bool:
    """Claim próprio; suspensão antes do efeito conserva o aviso para retomada."""
    with SessionLocal() as db:
        item = db.scalar(select(GalleryReopeningNotificationOutbox).join(Tenant,
            Tenant.id == GalleryReopeningNotificationOutbox.tenant_id).where(
            Tenant.status == "active", Tenant.lifecycle != "closed", GalleryReopeningNotificationOutbox.status == "queued").order_by(
            GalleryReopeningNotificationOutbox.created_at).limit(1).with_for_update(
            of=(Tenant, GalleryReopeningNotificationOutbox), skip_locked=True))
        if not item:
            return False
        item.status, item.attempts, item.updated_at = "processing", item.attempts + 1, now()
        # Mantém o lock do tenant até registrar o resultado do envio. Assim,
        # a finalização não pode aprovar o encerramento no meio do envio.
        try:
            origin = reopening_origin(db, item)
            provider = provider_for(db, tenant_id=item.tenant_id, adapter=adapter)
            require_ready_channel(db, provider, tenant_id=item.tenant_id)
            origin = reopening_origin(db, item)
            recipient = photographer_phone(db, tenant_id=item.tenant_id)
            if not recipient or item.recipient_phone != recipient:
                raise WhatsAppConfigurationError("Destino da reabertura indisponível.")
            result = provider.send_transactional(recipient,
                f"Solicitação de reabertura da galeria {origin.name}. Revise em Vendas e pagamentos.",
                idempotency_key=f"gallery-reopening:{item.id}")
            if result.recipient_phone_e164 != recipient:
                raise WhatsAppDeliveryError("Destino divergente.", transient=False, ambiguous=True)
            item.status, item.last_error = "sent", None
        except HTTPException:
            item.status, item.attempts = "queued", item.attempts - 1
        except (WhatsAppConfigurationError, WhatsAppDeliveryError) as error:
            # Nenhum retry automático após resultado ambíguo.
            item.status, item.last_error = "failed", sanitized_delivery_error(error)
        item.updated_at = now()
        db.commit()
        return True


def reconcile_next_unknown_delivery() -> bool:
    with SessionLocal() as db:
        delivery = db.scalar(
            select(WhatsAppDelivery).join(Tenant, Tenant.id == WhatsAppDelivery.tenant_id)
            .where(Tenant.status == "active", Tenant.lifecycle != "closed",
                WhatsAppDelivery.status == "unknown",
                WhatsAppDelivery.external_message_id.is_not(None),
            )
            .order_by(WhatsAppDelivery.updated_at)
            .limit(1)
            .with_for_update(of=(Tenant, WhatsAppDelivery), skip_locked=True)
        )
        if not delivery or not delivery.external_message_id:
            return False
        provider = provider_for(db, tenant_id=delivery.tenant_id)
        delivery_message(db, delivery)
        require_ready_channel(db, provider, tenant_id=delivery.tenant_id)
        result = provider.reconcile(delivery.external_message_id)
        if not result:
            return False
        if result.recipient_phone_e164 != delivery.recipient_phone:
            raise WhatsAppConfigurationError("Destino divergente.")
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


_last_closure_cursor = None


def process_next_tenant_closure() -> bool:
    """Reavalia uma solicitação, rotacionando também entre contas bloqueadas."""
    from app.auth import TenantClosureRequest
    from app.tenant_closure import finalize_closure

    global _last_closure_cursor
    with domain_session(SessionLocal) as db:
        query = select(TenantClosureRequest.tenant_id, TenantClosureRequest.id).join(
            Tenant, Tenant.id == TenantClosureRequest.tenant_id,
        ).where(TenantClosureRequest.state == "closing", Tenant.lifecycle == "closing")
        candidate = db.execute(query.where(TenantClosureRequest.id > _last_closure_cursor)
                               .order_by(TenantClosureRequest.id).limit(1)).first() if _last_closure_cursor else None
        if candidate is None:
            candidate = db.execute(query.order_by(TenantClosureRequest.id).limit(1)).first()
        if candidate is None:
            _last_closure_cursor = None
            return False
        _last_closure_cursor = candidate.id
        result = finalize_closure(db, candidate.tenant_id)
        db.commit()
        return result["ready"]


@observe_work("general")
def run_cycle() -> bool:
    from app.mercadopago_credit_purchases import process_next_mercadopago_credit_purchase
    from app.mercadopago_webhook import (
        process_next_mercadopago_event,
        reconcile_next_mercadopago_payment,
    )
    from app.photographer_signup import process_signup_expiry

    signup_expired = process_signup_expiry(session_factory=SessionLocal)
    # Avisos prontos não aguardam o esvaziamento de uma fila grande de mídia.
    with domain_session(SessionLocal) as batch_db:
        process_ready_batches(batch_db)
    process_highres_cleanup()
    process_asset_file_cleanup()
    process_next_notification("push")
    process_next_notification("whatsapp")
    event_worked = process_next_mercadopago_event()
    photo_payment_worked = reconcile_next_mercadopago_payment()
    credit_purchase_worked = process_next_mercadopago_credit_purchase()
    payment_worked = photo_payment_worked or credit_purchase_worked or event_worked
    closure_worked = process_next_tenant_closure()
    return (
        process_next_photo_credit_reconciliation()
        or process_next_gallery_lifecycle_operation()
        or process_next_media_archive_operation()
        or process_next_media_job()
        or process_next_whatsapp_delivery()
        or process_next_email_delivery()
        or materialize_next_payment_notification()
        or process_next_gallery_membership_notification()
        or process_next_gallery_reopening_notification()
        or reconcile_next_unknown_delivery()
        or process_otp_privacy_cleanup()
        or process_admin_security_cleanup()
        or payment_worked
        or closure_worked
        or signup_expired
    )


def run_worker_until_stopped(*, stop_requested=None, cycle=None, sleep=None) -> None:
    stop_requested = stop_requested or _STOP_REQUESTED
    cycle = cycle or run_cycle
    sleep = sleep or time.sleep
    while not stop_requested.is_set():
        try:
            worked = cycle()
        except TenantContextError:
            worked = False
        if not worked and not stop_requested.is_set():
            sleep(2)


_STOP_REQUESTED = threading.Event()


def _request_worker_stop(_signum, _frame) -> None:
    """Finish the current durable queue cycle before the container exits."""

    _STOP_REQUESTED.set()


def main() -> None:
    from app.system_monitor.runtime import start_monitor
    _STOP_REQUESTED.clear()
    signal.signal(signal.SIGTERM, _request_worker_stop)
    signal.signal(signal.SIGINT, _request_worker_stop)
    start_monitor()
    print("markina-gallery-worker: pronto para filas privadas", flush=True)
    run_worker_until_stopped()
    print("markina-gallery-worker: ciclo atual concluído; parada graciosa", flush=True)


_last_asset_cleanup = 0.0


def process_asset_file_cleanup() -> bool:
    global _last_asset_cleanup
    instant = time.monotonic()
    if instant - _last_asset_cleanup < 30:
        return False
    _last_asset_cleanup = instant
    from app.asset_removal import process_file_cleanup
    from app.auth import AssetFileCleanup
    with SessionLocal() as db:
        job = db.scalar(select(AssetFileCleanup).join(Tenant, Tenant.id == AssetFileCleanup.tenant_id).where(Tenant.status == "active").where(AssetFileCleanup.status.in_(("pending", "failed")))
                        .order_by(AssetFileCleanup.attempts, AssetFileCleanup.created_at).limit(1).with_for_update(skip_locked=True, of=AssetFileCleanup))
        if not job:
            return False
        try:
            from app.tenancy import bind_privacy_retention
            bind_privacy_retention(db, job.tenant_id)
            return process_file_cleanup(db, job)
        except HTTPException as exc:
            if exc.status_code != 403:
                raise
            db.rollback()
            return True


_last_highres_cleanup = 0.0


def process_highres_cleanup() -> bool:
    global _last_highres_cleanup
    instant = time.monotonic()
    if instant - _last_highres_cleanup < 30:
        return False
    _last_highres_cleanup = instant
    from app.facial.lifecycle import cleanup_sources
    with SessionLocal() as db:
        return cleanup_sources(db) > 0


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
        owners = list(db.scalars(select(Tenant.id).where(Tenant.status == "active")))
        removed = 0
        for tenant_id in owners:
            try:
                from app.tenancy import bind_privacy_retention
                bind_privacy_retention(db, tenant_id)
                removed += cleanup_expired_client_otp_pii(db, tenant_id=tenant_id)
            except HTTPException as exc:
                db.rollback()
                if exc.status_code != 403:
                    raise
        return removed > 0


_last_admin_security_cleanup = 0.0


def process_admin_security_cleanup() -> bool:
    global _last_admin_security_cleanup
    instant = time.monotonic()
    interval = max(5, int(os.getenv("ADMIN_SECURITY_CLEANUP_INTERVAL_SECONDS", "60")))
    if instant - _last_admin_security_cleanup < interval:
        return False
    _last_admin_security_cleanup = instant
    with domain_session(SessionLocal) as db:
        removed = cleanup_admin_security_material(db)
        from app.tenant_closure_identity import cleanup_expired_identity_challenges
        removed += cleanup_expired_identity_challenges(db)
    with SessionLocal() as db:
        owners = list(db.scalars(select(Tenant.id).where(Tenant.status == "active")))
    for tenant_id in owners:
        try:
            with domain_session(SessionLocal) as db:
                from app.tenancy import bind_privacy_retention
                bind_privacy_retention(db, tenant_id)
                removed += cleanup_admin_security_material(db, tenant_id=tenant_id)
        except TenantContextError:
            continue
        except HTTPException as exc:
            if exc.status_code != 403:
                raise
    return removed > 0


if __name__ == "__main__":
    main()
