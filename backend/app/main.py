"""API de autenticação unificada da Markina Gallery."""

from __future__ import annotations

import base64
import json
import secrets
from collections import defaultdict
from datetime import datetime, timedelta
from hashlib import sha256
from io import BytesIO
from os import getenv
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

import pyotp
from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import case, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.responses import FileResponse, PlainTextResponse

from app.admin_account import (
    AdminAccountError,
    active_admin_for_session,
    challenge_target,
    change_admin_password,
    create_security_challenge,
    issue_email_verification,
    issue_password_reset_email,
    mask_email,
    normalize_admin_email,
    queue_previous_email_notice,
    reauthenticate_admin,
    resend_security_challenge,
    token_target,
    verify_security_challenge,
)
from app.admin_security import (
    consume_admin_action_token,
    invalidate_admin_security_material,
)
from app.auth import (
    AdminActionToken,
    AdminPasswordInput,
    AdminUser,
    AuditEvent,
    AuthChallenge,
    AuthSession,
    BrandingSettings,
    ChallengeResendInput,
    ChallengeVerification,
    Client,
    ClientChallengeInput,
    ClientPhone,
    CommercialHistoryMedia,
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    DerivedGalleryPhotoOrigin,
    EmailDelivery,
    GalleryAccess,
    GalleryAccessCapability,
    GalleryLifecycleOperation,
    GalleryMembershipNotificationOutbox,
    MediaDerivative,
    MediaJob,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    PaymentMessageTemplate,
    PaymentNotificationOutbox,
    PhotoAsset,
    PhotoComment,
    PhotoFavorite,
    PhotoFolder,
    PhotoSelection,
    PhotoView,
    PixCheckoutSettings,
    PriceRule,
    ProgressivePricingPreset,
    ProgressivePricingTier,
    Role,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    WhatsAppDelivery,
    audit,
    challenge_fingerprint,
    consume_challenge,
    create_challenge,
    create_session,
    current_session,
    enforce_rate_limit,
    enqueue_client_otp_delivery,
    expired,
    minimize_client_challenge_pii,
    neutral_error,
    normalize_e164,
    now,
    password_hasher,
    pii_fingerprint,
    resend_client_challenge,
    revoke_subject_sessions,
    token_hash,
    validate_admin_password,
)
from app.checkout import CheckoutError, create_pending_checkout
from app.client_identity import (
    ClientIdentityConflict,
    assert_phone_available,
    change_verified_phone,
    resolve_client_by_phone,
    verify_canonical_phone,
)
from app.commercial_removal import (
    CommercialRemovalBlocked,
    CommercialRemovalPreparationFailed,
    apply_commercial_removal_policy,
)
from app.email_delivery import EmailConfigurationError, email_channel_payload, public_app_origin
from app.gallery_access import (
    consume_gallery_capability,
    issue_gallery_capability,
    reconstruct_gallery_capability_token,
    resolve_gallery_capability,
    revoke_gallery_capability,
    rotate_gallery_capability,
    validate_gallery_capability_runtime_configuration,
)
from app.gallery_lifecycle import (
    client_unlink_inventory,
    gallery_deletion_inventory,
    gallery_operational_storage_manifest,
    retry_failed_operation,
    transition_operation,
)
from app.gallery_pricing import GalleryPricingError, quote_parent_gallery
from app.gallery_visuals import (
    TITLE_FONT_OPTIONS,
    normalize_title_font,
    validate_title_font,
)
from app.historical_media import historical_media_path
from app.media import enqueue_derivatives, safe_derivative_path, safe_source_path
from app.membership_notifications import (
    enqueue_membership_notification,
    mark_membership_notification_read,
)
from app.messaging import (
    WhatsAppConfigurationError,
    WhatsAppDeliveryError,
    configured_photographer_phone,
    payment_notification_max_attempts,
    whatsapp_provider_from_environment,
)
from app.parent_registration import link_client_to_parent
from app.payment_templates import DEFAULT_PAYMENT_TEMPLATES, validate_template
from app.pix import (
    PixCodeError,
    normalize_pix_configuration,
    normalize_pix_copy_paste,
    pix_qr_data_url,
)
from app.pricing import (
    PriceTier,
    PricingRuleError,
    has_downward_jump,
    progressive_quote,
    validate_tiers,
)
from app.private_derivation import (
    PrivateDerivationError,
    derive_admin_gallery,
    derive_client_selection,
    ensure_private_photo_reference,
)
from app.private_gallery_lifecycle import remove_client_selection_and_close_if_empty
from app.private_membership import (
    PrivateMembershipConflict,
    PrivateMembershipError,
    block_private_membership,
    client_has_operational_membership,
    ensure_private_membership,
    membership_for_client,
    operational_galleries_for_client,
    reactivate_private_membership,
    unblock_private_membership,
    unlink_private_membership,
)
from app.public_gallery_access import (
    PublicGalleryAccessDenied,
    active_capability_by_id,
    apply_public_gallery_access,
    require_public_gallery_browsing,
    safe_internal_return,
)
from app.whatsapp_channel import (
    channel_payload,
    channel_settings,
    configure_expected_phone,
    refresh_channel,
    start_channel_pairing,
)
from app.whatsapp_webhook import process_whatsapp_webhook

app = FastAPI(title="Markina Gallery API", version="0.2.0")


@app.on_event("startup")
def validate_sensitive_runtime_configuration() -> None:
    validate_gallery_capability_runtime_configuration()

BRANDING_ASSETS = {
    "logo": {
        "formats": {
            "PNG": (".png", "image/png"),
            "JPEG": (".jpg", "image/jpeg"),
            "WEBP": (".webp", "image/webp"),
        },
        "max_bytes": 2 * 1024 * 1024,
    },
    "app-icon": {
        "formats": {
            "PNG": (".png", "image/png"),
            "JPEG": (".jpg", "image/jpeg"),
            "WEBP": (".webp", "image/webp"),
            "ICO": (".ico", "image/x-icon"),
        },
        "max_bytes": 1024 * 1024,
    },
    "favicon": {
        "formats": {"PNG": (".png", "image/png"), "ICO": (".ico", "image/x-icon")},
        "max_bytes": 512 * 1024,
    },
}


def branding_root() -> Path:
    """Return the Markina-only storage root for validated branding assets."""
    return Path(getenv("BRANDING_ASSETS_ROOT", "media/branding")).resolve()


def branding_asset_path(key: str) -> Path:
    root = branding_root()
    candidate = (root / key).resolve()
    if candidate.parent != root:
        raise ValueError("Chave de ativo de marca inválida.")
    return candidate


def validate_branding_asset(asset: str, content_type: str | None, body: bytes) -> tuple[str, str]:
    rules = BRANDING_ASSETS[asset]
    if not body or len(body) > rules["max_bytes"]:
        raise HTTPException(status_code=413, detail="O arquivo excede o limite permitido.")
    try:
        with Image.open(BytesIO(body)) as image:
            image_format = image.format or ""
            width, height = image.size
            image.verify()
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Imagem de marca inválida.") from exc
    allowed = rules["formats"]
    if image_format not in allowed or not (16 <= width <= 4096 and 16 <= height <= 4096):
        raise HTTPException(status_code=422, detail="Formato ou dimensão de imagem não permitido.")
    suffix, media_type = allowed[image_format]
    if content_type and content_type.lower().split(";", 1)[0] != media_type:
        raise HTTPException(
            status_code=415, detail="O tipo informado não corresponde à imagem enviada."
        )
    return suffix, media_type


class ParentGalleryInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    event_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5_000)
    access_mode: str = Field(
        default="invite_only",
        pattern=r"^(standard|invite_only|collective_protected)$",
    )


class ParentGallerySettingsInput(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    event_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5_000)
    active: bool | None = None
    access_mode: str | None = Field(
        default=None,
        pattern=r"^(standard|invite_only|collective_protected)$",
    )
    folder_display_mode: str | None = Field(default=None, pattern=r"^(individual|sequential)$")
    cover_title_font: str | None = Field(default=None, max_length=80)
    cover_title_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    cover_title_size: int | None = Field(default=None, ge=12, le=96)
    cover_title_position: str | None = Field(
        default=None,
        pattern=r"^(top-left|top-center|top-right|middle-left|middle-center|middle-right|bottom-left|bottom-center|bottom-right)$",
    )
    sales_message: str | None = Field(default=None, max_length=5_000)
    selection_duration_days: int | None = Field(default=None, ge=1, le=3_650)
    favorites_enabled: bool | None = None
    comments_enabled: bool | None = None

    @field_validator("cover_title_font")
    @classmethod
    def require_supported_title_font(cls, value: str | None) -> str | None:
        return validate_title_font(value) if value is not None else None


class ParentGalleryCoverInput(BaseModel):
    photo_id: UUID


class ParentGalleryCoverUploadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=512)
    display_name: str | None = Field(default=None, max_length=512)
    idempotency_key: str = Field(min_length=16, max_length=160)


class ClientInput(BaseModel):
    full_name: str = Field(min_length=3, max_length=200)
    phone_e164: str = Field(min_length=8, max_length=32)


class ClientNameInput(BaseModel):
    full_name: str = Field(min_length=3, max_length=200)


class PhotoAssetInput(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    display_name: str | None = Field(default=None, max_length=512)
    storage_key: str = Field(min_length=1, max_length=1_024)


class PhotoFolderInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class PhotoFolderRenameInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class PhotoBulkDeleteInput(BaseModel):
    photo_ids: list[UUID] = Field(min_length=1, max_length=500)


class PhotoFolderReleaseInput(BaseModel):
    gallery_ids: list[UUID] = Field(default_factory=list, max_length=100)


class PhotoFolderPublishInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BrandingSettingsInput(BaseModel):
    login_title: str = Field(min_length=1, max_length=120)
    login_intro: str = Field(min_length=1, max_length=300)
    login_helper: str = Field(min_length=1, max_length=240)

    @field_validator("login_title", "login_intro", "login_helper")
    @classmethod
    def reject_markup(cls, value: str) -> str:
        """Keep configurable entry copy as plain text, never executable markup."""
        cleaned = value.strip()
        if "<" in cleaned or ">" in cleaned:
            raise ValueError("Os textos devem conter apenas texto simples")
        return cleaned


class VisualProtectionSettingsInput(BaseModel):
    watermark_text: str = Field(min_length=1, max_length=120)
    watermark_font: Literal["sans-serif", "serif", "monospace", "DejaVuSans", "DejaVuSerif"]
    watermark_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    watermark_size: int = Field(ge=10, le=96)
    watermark_direction: Literal["horizontal", "vertical", "diagonal"]

    @field_validator("watermark_text")
    @classmethod
    def require_plain_watermark(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("A marca-d’água não pode ficar vazia")
        return cleaned


class WhatsAppChannelInput(BaseModel):
    expected_phone_e164: str = Field(min_length=8, max_length=32)


class WhatsAppRetryInput(BaseModel):
    confirm_duplicate_risk: bool = False


class DerivedGalleryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_gallery_id: UUID
    client_id: UUID
    name: str = Field(min_length=1, max_length=200)
    photo_ids: list[UUID] = Field(default_factory=list)
    access_enabled: bool = True


class DerivedGallerySettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    access_enabled: bool | None = None


class DerivedGalleryMemberInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: UUID


class DerivedGalleryPhotosInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    photo_ids: list[UUID] = Field(min_length=1, max_length=500)


class GalleryRenewalInput(BaseModel):
    selection_expires_at: datetime


class ClientLinkChallengeInput(ClientChallengeInput):
    parent_gallery_id: UUID | None = None
    access_token: str | None = Field(default=None, min_length=32, max_length=256)
    return_to: str | None = Field(default=None, max_length=512)


class PublicGalleryAccessInput(BaseModel):
    access_token: str = Field(min_length=32, max_length=256)
    return_to: str | None = Field(default=None, max_length=512)


class GalleryCapabilityInput(BaseModel):
    expires_at: datetime | None = None


class CloneGalleryInput(BaseModel):
    client_id: UUID
    name: str | None = Field(default=None, min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=12, max_length=128)


class PhoneChangeInput(BaseModel):
    phone_e164: str = Field(min_length=8, max_length=32)
    challenge_id: UUID
    code: str = Field(pattern=r"^\d{6}$")


class PhotoCommentInput(BaseModel):
    body: str = Field(min_length=1, max_length=2_000)


class CheckoutInput(BaseModel):
    idempotency_key: str = Field(min_length=12, max_length=128)


class PaymentCommunicationInput(BaseModel):
    idempotency_key: str = Field(min_length=12, max_length=128)


class PaymentDecisionInput(BaseModel):
    decision: Literal["confirmed", "refused"]


class PaymentTemplateInput(BaseModel):
    body: str = Field(min_length=1, max_length=500)


class PriceTierInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_quantity: int = Field(ge=1, le=10_000)
    maximum_quantity: int | None = Field(default=None, ge=1, le=10_000)
    unit_price_cents: int = Field(ge=0, le=10_000_000)


class ProgressivePricingPresetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=120)
    tiers: list[PriceTierInput] = Field(min_length=1, max_length=20)


class PixCheckoutSettingsInput(BaseModel):
    copy_paste: str | None = Field(default=None, max_length=4_000)
    qr_code_payload: str | None = Field(default=None, max_length=8_000)
    receiver_name: str | None = Field(default=None, max_length=80)
    receiver_city: str | None = Field(default=None, max_length=80)
    instructions: str | None = Field(default=None, max_length=500)


class GalleryPricingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pricing_mode: Literal["fixed", "progressive"] | None = None
    fixed_unit_price_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    progressive_pricing_preset_id: UUID | None = None
    confirm_legacy_conversion: bool = False
    tiers: list[PriceTierInput] = Field(default_factory=list, max_length=20)
    pix: PixCheckoutSettingsInput = Field(default_factory=PixCheckoutSettingsInput)


class ParentGallerySalesInput(GalleryPricingInput):
    sales_message: str | None = Field(default=None, max_length=5_000)
    selection_duration_days: int | None = Field(default=None, ge=1, le=3_650)
    favorites_enabled: bool = False
    comments_enabled: bool = False


class AdminRecoveryRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class AdminSecurityCodeInput(BaseModel):
    challenge_id: UUID
    code: str = Field(pattern=r"^\d{6}$")


class AdminPasswordResetInput(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=1, max_length=128)


class AdminPasswordChallengeInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)


class AdminPasswordChangeInput(AdminSecurityCodeInput):
    new_password: str = Field(min_length=1, max_length=128)


class AdminEmailChallengeInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_email: str = Field(min_length=3, max_length=320)


class AdminEmailConfirmationInput(BaseModel):
    token: str = Field(min_length=32, max_length=256)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DatabaseSession = Annotated[Session, Depends(db_session)]


def require_admin(request: Request) -> None:
    current_session(request, Role.ADMIN)


def require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    try:
        expected = public_app_origin()
    except EmailConfigurationError:
        expected = str(request.base_url).rstrip("/")
    if origin.rstrip("/") != expected.rstrip("/"):
        raise HTTPException(status_code=403, detail="Origem da operação não autorizada.")


def enforce_commercial_removal_or_409(db: Session, **scope) -> None:
    try:
        apply_commercial_removal_policy(db, **scope)
    except CommercialRemovalBlocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommercialRemovalPreparationFailed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def derived_gallery_for_client(
    db: Session,
    gallery_id: UUID,
    client_id: UUID,
    *,
    require_access_enabled: bool = True,
    allow_deleted_origin: bool = False,
) -> DerivedGallery:
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery or not client_has_operational_membership(
        db,
        gallery=gallery,
        client_id=client_id,
    ):
        raise HTTPException(status_code=403, detail="Acesso negado.")
    if require_access_enabled and not gallery.access_enabled:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    if not parent:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    if parent.lifecycle_status == "deleting":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A Galeria pública está em exclusão e não aceita novas alterações.",
        )
    if parent.lifecycle_status == "deleted" and not allow_deleted_origin:
        raise HTTPException(
            status_code=409,
            detail="A Galeria pública de origem foi removida e não aceita alterações.",
        )
    return gallery


def require_parent_gallery_mutable(db: Session, parent_gallery_id: UUID) -> ParentGallery:
    """Recusa qualquer nova alteração depois que a exclusão foi iniciada."""

    parent = db.get(ParentGallery, parent_gallery_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    if parent.lifecycle_status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A Galeria pública está removida ou em exclusão e não aceita novas alterações.",
        )
    return parent


def require_derived_gallery_mutable(db: Session, gallery_id: UUID) -> DerivedGallery:
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    require_parent_gallery_mutable(db, gallery.parent_gallery_id)
    return gallery


def assigned_photo_for_gallery(db: Session, gallery_id: UUID, photo_id: UUID) -> None:
    assigned = db.scalar(
        select(DerivedGalleryPhoto)
        .join(PhotoAsset, PhotoAsset.id == DerivedGalleryPhoto.photo_asset_id)
        .outerjoin(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(
            DerivedGalleryPhoto.derived_gallery_id == gallery_id,
            DerivedGalleryPhoto.photo_asset_id == photo_id,
            PhotoFolder.status == "released",
            PhotoFolder.purpose == "content",
        )
    )
    if not assigned:
        raise HTTPException(status_code=404, detail="Foto não encontrada na galeria.")


def require_selection_window(gallery: DerivedGallery) -> None:
    if gallery.selection_expires_at and expired(gallery.selection_expires_at):
        raise HTTPException(status_code=403, detail="O prazo para novas seleções expirou.")


def protected_preview_response(path, filename: str) -> FileResponse:
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    return FileResponse(
        path,
        media_type="image/jpeg",
        filename=filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


def statistics_data(
    db: Session,
    *,
    starts_at: datetime | None,
    ends_at: datetime | None,
    client_id: UUID | None,
    parent_gallery_id: UUID | None,
    derived_gallery_id: UUID | None,
    event_name: str | None,
) -> dict[str, object]:
    gallery_query = select(DerivedGallery.id).join(ParentGallery)
    if client_id:
        authorized_ids = {
            gallery.id
            for gallery in operational_galleries_for_client(
                db,
                client_id=client_id,
                require_access_enabled=False,
            )
        }
        if not authorized_ids:
            return {
                "purchased": [],
                "selected_not_purchased": [],
                "revenue_cents": 0,
                "revenue_by_day": [],
            }
        gallery_query = gallery_query.where(DerivedGallery.id.in_(authorized_ids))
    if parent_gallery_id:
        gallery_query = gallery_query.where(DerivedGallery.parent_gallery_id == parent_gallery_id)
    if derived_gallery_id:
        gallery_query = gallery_query.where(DerivedGallery.id == derived_gallery_id)
    if event_name:
        gallery_query = gallery_query.where(ParentGallery.event_name == event_name)
    gallery_ids = set(db.scalars(gallery_query))
    if not gallery_ids:
        return {
            "purchased": [],
            "selected_not_purchased": [],
            "revenue_cents": 0,
            "revenue_by_day": [],
        }

    orders_query = select(SaleOrder).where(
        SaleOrder.payment_status == "confirmed", SaleOrder.derived_gallery_id.in_(gallery_ids)
    )
    if starts_at:
        orders_query = orders_query.where(SaleOrder.confirmed_at >= starts_at)
    if ends_at:
        orders_query = orders_query.where(SaleOrder.confirmed_at <= ends_at)
    confirmed_orders = list(db.scalars(orders_query))
    order_ids = {order.id for order in confirmed_orders}
    purchased_by_photo: dict[UUID, str] = {}
    if order_ids:
        for item in db.scalars(
            select(SaleOrderItem).where(SaleOrderItem.sale_order_id.in_(order_ids))
        ):
            purchased_by_photo.setdefault(item.photo_asset_id, item.filename_snapshot)

    selections_query = select(PhotoSelection).where(
        PhotoSelection.derived_gallery_id.in_(gallery_ids)
    )
    if starts_at:
        selections_query = selections_query.where(PhotoSelection.created_at >= starts_at)
    if ends_at:
        selections_query = selections_query.where(PhotoSelection.created_at <= ends_at)
    selected_ids = set(
        db.scalars(selections_query.with_only_columns(PhotoSelection.photo_asset_id))
    )
    selected_not_purchased_ids = selected_ids - set(purchased_by_photo)
    selected_names: dict[UUID, str] = {}
    if selected_not_purchased_ids:
        for photo in db.scalars(
            select(PhotoAsset).where(PhotoAsset.id.in_(selected_not_purchased_ids))
        ):
            selected_names[photo.id] = photo.filename

    revenue_by_day: defaultdict[str, int] = defaultdict(int)
    for order in confirmed_orders:
        if order.confirmed_at:
            revenue_by_day[order.confirmed_at.date().isoformat()] += order.total_cents
    return {
        "purchased": [
            {"id": str(photo_id), "filename": filename}
            for photo_id, filename in sorted(purchased_by_photo.items(), key=lambda item: item[1])
        ],
        "selected_not_purchased": [
            {"id": str(photo_id), "filename": filename}
            for photo_id, filename in sorted(selected_names.items(), key=lambda item: item[1])
        ],
        "revenue_cents": sum(order.total_cents for order in confirmed_orders),
        "revenue_by_day": [
            {"date": day, "revenue_cents": cents} for day, cents in sorted(revenue_by_day.items())
        ],
    }


def statistics_txt(entries: list[dict[str, str]]) -> PlainTextResponse:
    content = "".join(f"{entry['id']}\t{entry['filename']}\n" for entry in entries)
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": 'attachment; filename="markina-gallery-lista.txt"'},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.post("/internal/whatsapp/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(db_session)) -> dict[str, str]:
    expected = getenv("WHATSAPP_WEBHOOK_SECRET", "")
    provided = request.headers.get("X-Markina-Webhook-Secret", "")
    if not expected or not provided or not secrets.compare_digest(expected, provided):
        raise HTTPException(status_code=403, detail="Evento não autorizado.")
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 65_536:
        raise HTTPException(status_code=413, detail="Evento excede o limite permitido.")
    body = await request.body()
    if len(body) > 65_536:
        raise HTTPException(status_code=413, detail="Evento excede o limite permitido.")
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Evento inválido.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Evento inválido.")
    _changed, outcome = process_whatsapp_webhook(db, payload)
    return {"status": outcome}


def whatsapp_admin_payload(db: Session, settings) -> dict:
    payload = channel_payload(settings)
    payload["deliveries"] = {
        delivery_status: count
        for delivery_status, count in db.execute(
            select(WhatsAppDelivery.status, func.count())
            .group_by(WhatsAppDelivery.status)
            .order_by(WhatsAppDelivery.status)
        )
    }
    return payload


@app.get("/admin/whatsapp/channel")
def admin_whatsapp_channel(request: Request, db: Session = Depends(db_session)) -> dict:
    current_session(request, Role.ADMIN)
    try:
        provider = whatsapp_provider_from_environment()
        settings = refresh_channel(db, provider)
    except (WhatsAppConfigurationError, WhatsAppDeliveryError):
        settings = channel_settings(db)
        settings.status = "error"
        settings.last_error = "Configuração ou conexão do canal indisponível."
        settings.last_checked_at = now()
        db.commit()
    return whatsapp_admin_payload(db, settings)


@app.patch("/admin/whatsapp/channel")
def update_admin_whatsapp_channel(
    payload: WhatsAppChannelInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict:
    current_session(request, Role.ADMIN)
    try:
        settings = configure_expected_phone(db, payload.expected_phone_e164)
    except WhatsAppConfigurationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return whatsapp_admin_payload(db, settings)


@app.post("/admin/whatsapp/channel/refresh")
def refresh_admin_whatsapp_channel(request: Request, db: Session = Depends(db_session)) -> dict:
    current_session(request, Role.ADMIN)
    try:
        settings = refresh_channel(db, whatsapp_provider_from_environment())
    except (WhatsAppConfigurationError, WhatsAppDeliveryError):
        raise HTTPException(status_code=503, detail="Não foi possível consultar o canal.") from None
    return whatsapp_admin_payload(db, settings)


@app.post("/admin/whatsapp/channel/pairing")
def pair_admin_whatsapp_channel(
    request: Request, response: Response, db: Session = Depends(db_session)
) -> dict:
    current_session(request, Role.ADMIN)
    response.headers["Cache-Control"] = "no-store"
    try:
        settings, pairing = start_channel_pairing(db, whatsapp_provider_from_environment())
    except WhatsAppConfigurationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except WhatsAppDeliveryError:
        raise HTTPException(
            status_code=503, detail="Não foi possível iniciar o pareamento."
        ) from None
    result = whatsapp_admin_payload(db, settings)
    result["pairing"] = {
        "state": pairing.state,
        "pairing_code": pairing.pairing_code,
        "qr_base64": pairing.qr_base64,
    }
    return result


@app.get("/admin/whatsapp/deliveries")
def admin_whatsapp_deliveries(
    request: Request,
    delivery_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(db_session),
) -> list[dict]:
    current_session(request, Role.ADMIN)
    query = select(WhatsAppDelivery).order_by(WhatsAppDelivery.created_at.desc()).limit(100)
    if delivery_status:
        query = query.where(WhatsAppDelivery.status == delivery_status)
    return [
        {
            "id": str(item.id),
            "kind": item.kind,
            "template_kind": item.template_kind,
            "status": item.status,
            "attempts": item.attempts,
            "provider_status": item.provider_status,
            "last_error": item.last_error,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
        for item in db.scalars(query)
    ]


@app.post("/admin/whatsapp/deliveries/{delivery_id}/retry")
def retry_admin_whatsapp_delivery(
    delivery_id: UUID,
    payload: WhatsAppRetryInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    session = current_session(request, Role.ADMIN)
    delivery = db.get(WhatsAppDelivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada.")
    try:
        max_attempts = payment_notification_max_attempts()
    except WhatsAppConfigurationError:
        max_attempts = 1
    if delivery.attempts >= max_attempts or delivery.status not in {"failed", "unknown"}:
        raise HTTPException(status_code=409, detail="A entrega não pode ser reenfileirada.")
    if delivery.expires_at and expired(delivery.expires_at):
        delivery.status = "expired"
        delivery.encrypted_payload = None
        db.commit()
        raise HTTPException(status_code=409, detail="A entrega expirou.")
    if delivery.status == "unknown":
        wait_seconds = max(60, int(getenv("WHATSAPP_AMBIGUOUS_RETRY_AFTER_SECONDS", "300")))
        updated_at = delivery.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=now().tzinfo)
        if now() < updated_at + timedelta(seconds=wait_seconds):
            raise HTTPException(
                status_code=409,
                detail="A entrega ainda aguarda reconciliação do provedor.",
            )
        if not payload.confirm_duplicate_risk:
            raise HTTPException(
                status_code=409,
                detail="Confirme explicitamente o risco de duplicidade.",
            )
    delivery.status = "queued"
    delivery.next_attempt_at = None
    delivery.last_error = None
    delivery.updated_at = now()
    audit(db, "whatsapp.delivery_requeued", f"{delivery.id}:{session.subject_id}")
    db.commit()
    return {"status": "queued"}


@app.post("/auth/client/challenge", status_code=status.HTTP_202_ACCEPTED)
def client_challenge(
    payload: ClientLinkChallengeInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    phone = normalize_e164(payload.phone)
    client_name = " ".join(payload.full_name.split())
    if len(client_name) < 3:
        raise HTTPException(status_code=422, detail="Informe o nome completo.")
    enforce_rate_limit(
        db,
        "client_otp.challenge",
        pii_fingerprint(phone),
        request.client.host if request.client else "unknown",
    )
    challenge, code = create_challenge(db, "client_otp", phone)
    challenge.client_name = client_name
    capability = (
        resolve_gallery_capability(db, payload.access_token) if payload.access_token else None
    )
    if payload.access_token and not capability:
        audit(db, "client_otp.gallery_capability_rejected", "invalid")
        minimize_client_challenge_pii(db, challenge)
        db.commit()
        raise neutral_error()
    context_parent_id = capability.parent_gallery_id if capability else payload.parent_gallery_id
    if context_parent_id:
        parent_gallery = db.get(ParentGallery, context_parent_id)
        private_invite_gallery = (
            db.get(DerivedGallery, capability.derived_gallery_id)
            if capability
            and capability.scope
            in {"private_invite", "private_client_invite", "private_gallery_link"}
            and capability.derived_gallery_id
            else None
        )
        valid_private_invite_context = bool(
            private_invite_gallery
            and private_invite_gallery.parent_gallery_id == context_parent_id
            and (
                capability.scope == "private_gallery_link"
                or private_invite_gallery.client_id == capability.client_id
            )
            and private_invite_gallery.access_enabled
            and parent_gallery
            and parent_gallery.lifecycle_status in {"active", "deleted"}
        )
        if not parent_gallery or (
            not valid_private_invite_context
            and (not parent_gallery.active or parent_gallery.lifecycle_status != "active")
        ):
            audit(db, "client_otp.gallery_context_rejected", challenge_fingerprint(challenge))
            minimize_client_challenge_pii(db, challenge)
            db.commit()
            raise neutral_error()
        challenge.parent_gallery_id = context_parent_id
        challenge.gallery_capability_id = capability.id if capability else None
        challenge.return_to = safe_internal_return(payload.return_to, "") or None
    db.commit()
    enqueue_client_otp_delivery(db, challenge, code)
    return {
        "challenge_id": str(challenge.id),
        "message": "Se os dados puderem receber acesso, enviaremos um código.",
    }


@app.post("/auth/client/resend", status_code=status.HTTP_202_ACCEPTED)
def client_resend(
    payload: ChallengeResendInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    resend_client_challenge(
        db, payload.challenge_id, request.client.host if request.client else "unknown"
    )
    return {"message": "Se os dados puderem receber acesso, enviaremos um novo código."}


@app.post("/auth/client/verify")
def client_verify(
    payload: ChallengeVerification, response: Response, db: Session = Depends(db_session)
) -> dict[str, str]:
    challenge = consume_challenge(db, payload.challenge_id, "client_otp", payload.code)
    phone = challenge.subject
    fingerprint = challenge_fingerprint(challenge)
    if not phone:
        audit(db, "client_otp.minimized_challenge_rejected", str(challenge.id))
        db.commit()
        raise neutral_error()
    try:
        client = resolve_client_by_phone(db, phone)
    except ClientIdentityConflict as exc:
        audit(db, "client_otp.identity_conflict", fingerprint)
        minimize_client_challenge_pii(db, challenge)
        db.commit()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    parent_gallery = (
        db.get(ParentGallery, challenge.parent_gallery_id) if challenge.parent_gallery_id else None
    )
    capability = active_capability_by_id(db, challenge.gallery_capability_id)
    if not client:
        can_register_from_link = bool(
            parent_gallery
            and capability
            and capability.parent_gallery_id == parent_gallery.id
            and (
                (
                    capability.scope == "public_gallery"
                    and parent_gallery.access_mode in {"standard", "collective_protected"}
                )
                or capability.scope == "private_gallery_link"
            )
        )
        if (
            not can_register_from_link
            or not parent_gallery
            or not parent_gallery.active
            or parent_gallery.lifecycle_status != "active"
            or not challenge.client_name
        ):
            audit(db, "client_otp.unlinked_denied", fingerprint)
            minimize_client_challenge_pii(db, challenge)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Este número ainda não possui acesso. "
                    "Abra o link compartilhado de uma galeria para se cadastrar."
                ),
            )
        try:
            with db.begin_nested():
                client = Client(
                    full_name=challenge.client_name,
                    phone_e164=phone,
                )
                db.add(client)
                db.flush()
                db.add(
                    ClientPhone(
                        client_id=client.id,
                        phone_e164=phone,
                        active=True,
                        verified_at=now(),
                    )
                )
                db.flush()
        except IntegrityError:
            client = resolve_client_by_phone(db, phone)
            if not client:
                raise
        audit(db, "client.created_from_gallery_link", str(client.id))
    try:
        verify_canonical_phone(db, client, phone)
    except ClientIdentityConflict as exc:
        audit(db, "client_otp.identity_conflict", fingerprint)
        minimize_client_challenge_pii(db, challenge)
        db.commit()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    gallery_ids = [
        gallery.id
        for gallery in operational_galleries_for_client(db, client_id=client.id)
    ]
    if challenge.parent_gallery_id:
        parent_context = db.get(ParentGallery, challenge.parent_gallery_id)
        if capability and capability.scope in {
            "private_invite",
            "private_client_invite",
            "private_gallery_link",
        }:
            private_gallery = (
                db.get(DerivedGallery, capability.derived_gallery_id)
                if capability.derived_gallery_id
                else None
            )
            if (
                not parent_context
                or parent_context.lifecycle_status not in {"active", "deleted"}
                or not private_gallery
                or private_gallery.parent_gallery_id != parent_context.id
                or not private_gallery.access_enabled
                or (
                    capability.scope != "private_gallery_link"
                    and (
                        capability.client_id != client.id
                        or private_gallery.client_id != client.id
                    )
                )
            ):
                audit(db, "client_otp.private_invite_denied", str(capability.id))
                minimize_client_challenge_pii(db, challenge)
                db.commit()
                raise HTTPException(status_code=403, detail="Acesso não autorizado.")
            if parent_context.lifecycle_status == "active":
                registration = link_client_to_parent(
                    db,
                    parent_gallery_id=parent_context.id,
                    client_id=client.id,
                    status="active",
                )
                audit(
                    db,
                    "parent_gallery.registration_completed",
                    str(registration.id),
                )
            destination_gallery = private_gallery
            if capability.scope == "private_gallery_link":
                existing_membership = membership_for_client(
                    db,
                    parent_gallery_id=parent_context.id,
                    client_id=client.id,
                    lock=True,
                )
                if existing_membership:
                    if existing_membership.status != "active":
                        audit(
                            db,
                            "client_otp.private_link_blocked",
                            str(existing_membership.id),
                        )
                        minimize_client_challenge_pii(db, challenge)
                        db.commit()
                        raise HTTPException(status_code=403, detail="Acesso não autorizado.")
                    destination_gallery = db.get(
                        DerivedGallery,
                        existing_membership.derived_gallery_id,
                    )
                else:
                    try:
                        membership_result = ensure_private_membership(
                            db,
                            parent=parent_context,
                            client=client,
                            gallery=private_gallery,
                        )
                    except PrivateMembershipConflict:
                        existing_membership = membership_for_client(
                            db,
                            parent_gallery_id=parent_context.id,
                            client_id=client.id,
                        )
                        destination_gallery = (
                            db.get(DerivedGallery, existing_membership.derived_gallery_id)
                            if existing_membership
                            and existing_membership.status == "active"
                            else None
                        )
                    else:
                        destination_gallery = membership_result.gallery
                        enqueue_membership_notification(
                            db,
                            event_key=f"member_joined:{membership_result.membership.id}",
                            event_type="member_joined",
                            parent=parent_context,
                            gallery=destination_gallery,
                            client=client,
                        )
                        audit(
                            db,
                            "private_gallery.member_joined",
                            str(membership_result.membership.id),
                        )
                if not destination_gallery:
                    minimize_client_challenge_pii(db, challenge)
                    db.commit()
                    raise HTTPException(status_code=403, detail="Acesso não autorizado.")
            destination = safe_internal_return(
                challenge.return_to, f"/gallery/{destination_gallery.id}"
            )
            consume_gallery_capability(capability)
            audit(db, "private_gallery.invite_verified", str(destination_gallery.id))
        else:
            if (
                not parent_context
                or not parent_context.active
                or parent_context.lifecycle_status != "active"
            ):
                audit(db, "client_otp.gallery_context_rejected", fingerprint)
                minimize_client_challenge_pii(db, challenge)
                db.commit()
                raise HTTPException(status_code=409, detail="A Galeria pública está indisponível.")
            registration = None
            if parent_context.access_mode == "collective_protected" and capability:
                registration = link_client_to_parent(
                    db,
                    parent_gallery_id=parent_context.id,
                    client_id=client.id,
                    status="pending",
                )
            try:
                access = apply_public_gallery_access(
                    db,
                    parent_gallery_id=parent_context.id,
                    client_id=client.id,
                    capability=capability,
                    return_to=challenge.return_to,
                )
            except PublicGalleryAccessDenied as exc:
                audit(db, "client_otp.gallery_access_denied", str(parent_context.id))
                minimize_client_challenge_pii(db, challenge)
                db.commit()
                raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
            registration = access.registration or registration
            if registration:
                audit(
                    db,
                    "parent_gallery.registration_completed",
                    str(registration.id),
                )
            private_gallery_id = next(
                (
                    gallery.id
                    for gallery in operational_galleries_for_client(
                        db,
                        client_id=client.id,
                    )
                    if gallery.parent_gallery_id == challenge.parent_gallery_id
                ),
                None,
            )
            destination = (
                f"/gallery/{private_gallery_id}"
                if private_gallery_id and access.state == "authorized"
                else access.destination
            )
            if capability and capability.scope == "parent_invite":
                consume_gallery_capability(capability)
                audit(db, "parent_gallery.invite_verified", str(capability.id))
    else:
        destination = f"/gallery/{gallery_ids[0]}" if len(gallery_ids) == 1 else "/library"
    minimize_client_challenge_pii(db, challenge)
    create_session(db, response, Role.CLIENT, client.id)
    audit(db, "client.redirected", str(client.id))
    db.commit()
    return {"destination": destination}


@app.post("/auth/admin/password", status_code=status.HTTP_202_ACCEPTED)
def admin_password(
    payload: AdminPasswordInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    email = payload.email.strip().lower()
    enforce_rate_limit(
        db, "admin_password", email, request.client.host if request.client else "unknown"
    )
    admin = db.scalar(select(AdminUser).where(AdminUser.email == email))
    valid = False
    if admin and admin.email_verified:
        try:
            valid = password_hasher.verify(admin.password_hash, payload.password)
        except VerificationError:
            valid = False
    if not valid:
        audit(db, "admin_password.failed", email)
        db.commit()
        raise neutral_error()
    challenge, _ = create_challenge(db, "admin_totp", str(admin.id))
    return {"challenge_id": str(challenge.id), "message": "Continue com o código do autenticador."}


@app.post("/auth/admin/totp")
def admin_totp(
    payload: ChallengeVerification,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    challenge = db.get(AuthChallenge, payload.challenge_id)
    if not challenge or challenge.kind != "admin_totp":
        raise neutral_error()
    admin = db.get(AdminUser, UUID(challenge.subject))
    enforce_rate_limit(
        db, "admin_totp", challenge.subject, request.client.host if request.client else "unknown"
    )
    if not admin or not pyotp.TOTP(admin.totp_secret).verify(payload.code, valid_window=1):
        challenge.attempts += 1
        audit(db, "admin_totp.failed", challenge.subject)
        db.commit()
        raise neutral_error()
    if challenge.used_at or expired(challenge.expires_at) or challenge.attempts >= 5:
        raise neutral_error()
    challenge.used_at = now()
    audit(db, "admin_totp.validated", challenge.subject)
    create_session(db, response, Role.ADMIN, admin.id)
    audit(db, "admin.redirected", str(admin.id))
    db.commit()
    return {"destination": "/admin"}


@app.post("/auth/admin/recovery/challenge", status_code=status.HTTP_202_ACCEPTED)
def admin_recovery_challenge(
    payload: AdminRecoveryRequest,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    try:
        email = normalize_admin_email(payload.email)
    except AdminAccountError:
        email = payload.email.strip().casefold()
    fingerprint = pii_fingerprint(email)
    enforce_rate_limit(
        db,
        "admin_recovery",
        fingerprint,
        request.client.host if request.client else "unknown",
    )
    admin = db.scalar(select(AdminUser).where(AdminUser.email == email, AdminUser.email_verified))
    channel = email_channel_payload()
    eligible = admin if channel["status"] in {"ready", "sandbox"} else None
    try:
        challenge, _code, _queued = create_security_challenge(
            db,
            purpose="password_recovery_otp",
            subject_fingerprint=fingerprint,
            admin=eligible,
        )
    except (WhatsAppConfigurationError, ValueError):
        db.rollback()
        challenge, _code, _queued = create_security_challenge(
            db,
            purpose="password_recovery_otp",
            subject_fingerprint=fingerprint,
            admin=None,
        )
    return {
        "challenge_id": str(challenge.id),
        "message": "Se a conta estiver apta, enviaremos as próximas instruções.",
    }


@app.post("/auth/admin/recovery/resend", status_code=status.HTTP_202_ACCEPTED)
def admin_recovery_resend(
    payload: ChallengeResendInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    enforce_rate_limit(
        db,
        "admin_recovery_resend",
        token_hash(str(payload.challenge_id)),
        request.client.host if request.client else "unknown",
    )
    try:
        resend_security_challenge(
            db, challenge_id=payload.challenge_id, purpose="password_recovery_otp"
        )
    except AdminAccountError:
        raise neutral_error() from None
    except (WhatsAppConfigurationError, ValueError):
        db.rollback()
    return {"message": "Se a conta estiver apta, um novo código será enviado."}


@app.post("/auth/admin/recovery/verify", status_code=status.HTTP_202_ACCEPTED)
def admin_recovery_verify(
    payload: AdminSecurityCodeInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    enforce_rate_limit(
        db,
        "admin_recovery_verify",
        token_hash(str(payload.challenge_id)),
        request.client.host if request.client else "unknown",
    )
    try:
        challenge = verify_security_challenge(
            db,
            challenge_id=payload.challenge_id,
            purpose="password_recovery_otp",
            code=payload.code,
        )
        issue_password_reset_email(db, challenge)
    except (AdminAccountError, RuntimeError, ValueError):
        raise neutral_error() from None
    return {"message": "Se a conta estiver apta, o link foi enviado ao e-mail cadastrado."}


@app.post("/auth/admin/recovery/reset")
def admin_recovery_reset(
    payload: AdminPasswordResetInput,
    response: Response,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    item = db.scalar(
        select(AdminActionToken).where(
            AdminActionToken.token_hash == token_hash(payload.token),
            AdminActionToken.purpose == "password_reset",
        )
    )
    admin = db.get(AdminUser, item.admin_id) if item else None
    if not item or item.used_at or expired(item.expires_at) or not admin:
        raise HTTPException(status_code=400, detail="O link não está mais disponível.")
    try:
        validate_admin_password(
            payload.new_password,
            email=admin.email,
            current_password_hash=admin.password_hash,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    consumed = consume_admin_action_token(db, raw_token=payload.token, purpose="password_reset")
    if not consumed:
        raise HTTPException(status_code=400, detail="O link não está mais disponível.")
    change_admin_password(
        db, admin, payload.new_password, audit_event="admin_security.password_reset.completed"
    )
    db.commit()
    response.delete_cookie(getenv("SESSION_COOKIE_NAME", "markina_session"), path="/")
    return {"message": "Senha redefinida. Entre novamente com senha e autenticador."}


@app.post("/auth/admin/email/confirm")
def confirm_admin_email(
    payload: AdminEmailConfirmationInput,
    response: Response,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    item = db.scalar(
        select(AdminActionToken).where(
            AdminActionToken.token_hash == token_hash(payload.token),
            AdminActionToken.purpose == "verify_admin_email",
        )
    )
    admin = db.get(AdminUser, item.admin_id) if item else None
    if not item or item.used_at or expired(item.expires_at) or not admin:
        raise HTTPException(status_code=400, detail="O link não está mais disponível.")
    try:
        new_email = normalize_admin_email(token_target(item))
    except AdminAccountError:
        raise HTTPException(status_code=400, detail="O link não está mais disponível.") from None
    conflict = db.scalar(
        select(AdminUser).where(AdminUser.email == new_email, AdminUser.id != admin.id)
    )
    if conflict:
        item.used_at = now()
        item.encrypted_target = None
        audit(db, "admin_security.email_change.conflict", item.target_fingerprint or "unknown")
        db.commit()
        raise HTTPException(status_code=409, detail="Não foi possível usar o e-mail informado.")
    consumed = consume_admin_action_token(db, raw_token=payload.token, purpose="verify_admin_email")
    if not consumed:
        raise HTTPException(status_code=400, detail="O link não está mais disponível.")
    previous_email = admin.email
    admin.email = new_email
    admin.email_verified = True
    queue_previous_email_notice(
        db,
        admin_id=admin.id,
        previous_email=previous_email,
        action_token_id=item.id,
    )
    invalidate_admin_security_material(db, admin.id)
    revoke_subject_sessions(db, "admin", admin.id)
    audit(db, "admin_security.email_change.completed", str(admin.id))
    db.commit()
    response.delete_cookie(getenv("SESSION_COOKIE_NAME", "markina_session"), path="/")
    return {"message": "E-mail confirmado. Entre novamente com o novo endereço."}


@app.get("/auth/destination")
def destination(request: Request) -> dict[str, str]:
    session = current_session(request)
    if session.role == Role.ADMIN.value:
        return {"destination": "/admin"}
    with SessionLocal() as db:
        galleries = operational_galleries_for_client(
            db,
            client_id=session.subject_id,
        )
    return {
        "destination": f"/gallery/{galleries[0].id}" if len(galleries) == 1 else "/library"
    }


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> Response:
    session = current_session(request)
    with SessionLocal() as db:
        stored = db.get(type(session), session.id)
        stored.revoked_at = now()
        audit(db, "session.revoked", str(session.subject_id))
        db.commit()
    response.delete_cookie("markina_session", path="/")
    return response


@app.post("/auth/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all(request: Request, response: Response) -> Response:
    session = current_session(request)
    with SessionLocal() as db:
        revoke_subject_sessions(db, session.role, session.subject_id)
        db.commit()
    response.delete_cookie("markina_session", path="/")
    return response


@app.get("/admin")
def admin_area(request: Request) -> dict[str, str]:
    require_admin(request)
    return {"status": "authorized"}


@app.get("/admin/email/channel")
def admin_email_channel(request: Request, db: Session = Depends(db_session)) -> dict[str, object]:
    require_admin(request)
    payload: dict[str, object] = email_channel_payload()
    payload["deliveries"] = {
        delivery_status: count
        for delivery_status, count in db.execute(
            select(EmailDelivery.status, func.count())
            .group_by(EmailDelivery.status)
            .order_by(EmailDelivery.status)
        )
    }
    return payload


@app.get("/admin/security/summary")
def admin_security_summary(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    session = current_session(request, Role.ADMIN)
    try:
        admin = active_admin_for_session(db, session)
    except AdminAccountError:
        raise HTTPException(status_code=403, detail="Acesso negado.") from None
    whatsapp = channel_settings(db)
    return {
        "email_masked": mask_email(admin.email),
        "whatsapp_status": whatsapp.status,
        "email_channel": email_channel_payload(),
    }


@app.post("/admin/security/password/challenge", status_code=status.HTTP_202_ACCEPTED)
def admin_password_change_challenge(
    payload: AdminPasswordChallengeInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    admin = active_admin_for_session(db, session)
    enforce_rate_limit(
        db,
        "admin_change_password",
        str(admin.id),
        request.client.host if request.client else "unknown",
    )
    try:
        reauthenticate_admin(admin, payload.current_password)
    except AdminAccountError:
        audit(db, "admin_security.change_password.reauthentication_failed", str(admin.id))
        db.commit()
        raise neutral_error() from None
    challenge, _code, queued = create_security_challenge(
        db,
        purpose="change_password_otp",
        subject_fingerprint=pii_fingerprint(str(admin.id)),
        admin=admin,
        session_id=session.id,
    )
    if not queued:
        raise HTTPException(status_code=409, detail="Canal WhatsApp indisponível para confirmação.")
    return {"challenge_id": str(challenge.id), "message": "Código de confirmação enviado."}


@app.post("/admin/security/password/confirm")
def admin_password_change_confirm(
    payload: AdminPasswordChangeInput,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    admin = active_admin_for_session(db, session)
    try:
        verify_security_challenge(
            db,
            challenge_id=payload.challenge_id,
            purpose="change_password_otp",
            code=payload.code,
            session_id=session.id,
        )
        change_admin_password(
            db,
            admin,
            payload.new_password,
            audit_event="admin_security.password_change.completed",
        )
    except AdminAccountError:
        raise neutral_error() from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    db.commit()
    response.delete_cookie(getenv("SESSION_COOKIE_NAME", "markina_session"), path="/")
    return {"message": "Senha alterada. Entre novamente."}


@app.post("/admin/security/email/challenge", status_code=status.HTTP_202_ACCEPTED)
def admin_email_change_challenge(
    payload: AdminEmailChallengeInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    admin = active_admin_for_session(db, session)
    try:
        new_email = normalize_admin_email(payload.new_email)
        reauthenticate_admin(admin, payload.current_password)
    except AdminAccountError:
        audit(db, "admin_security.change_email.reauthentication_failed", str(admin.id))
        db.commit()
        raise neutral_error() from None
    if new_email == admin.email or db.scalar(
        select(AdminUser).where(AdminUser.email == new_email, AdminUser.id != admin.id)
    ):
        raise HTTPException(status_code=409, detail="Não foi possível usar o e-mail informado.")
    enforce_rate_limit(
        db,
        "admin_change_email",
        str(admin.id),
        request.client.host if request.client else "unknown",
    )
    challenge, _code, queued = create_security_challenge(
        db,
        purpose="change_email_otp",
        subject_fingerprint=pii_fingerprint(str(admin.id)),
        admin=admin,
        session_id=session.id,
        target=new_email,
    )
    if not queued:
        raise HTTPException(status_code=409, detail="Canal WhatsApp indisponível para confirmação.")
    return {"challenge_id": str(challenge.id), "message": "Código de confirmação enviado."}


@app.post("/admin/security/email/verify-otp", status_code=status.HTTP_202_ACCEPTED)
def admin_email_change_verify_otp(
    payload: AdminSecurityCodeInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    admin = active_admin_for_session(db, session)
    try:
        challenge = verify_security_challenge(
            db,
            challenge_id=payload.challenge_id,
            purpose="change_email_otp",
            code=payload.code,
            session_id=session.id,
        )
        new_email = challenge_target(challenge)
        if challenge.target_fingerprint != pii_fingerprint(new_email.strip().casefold()):
            raise AdminAccountError("Alvo da alteração indisponível.")
        issue_email_verification(db, admin, new_email)
    except AdminAccountError:
        raise neutral_error() from None
    return {"message": "Enviamos a confirmação para o novo endereço."}


def _branding_payload(
    settings: BrandingSettings, *, include_protection: bool = False
) -> dict[str, str | int | None]:
    payload: dict[str, str | int | None] = {
        "login_title": settings.login_title,
        "login_intro": settings.login_intro,
        "login_helper": settings.login_helper,
        "logo_url": "/branding/logo" if settings.logo_key else None,
        "app_icon_url": "/branding/app-icon" if settings.app_icon_key else None,
        "favicon_url": "/branding/favicon" if settings.favicon_key else None,
    }
    if include_protection:
        payload.update(
            {
                "watermark_text": settings.watermark_text,
                "watermark_font": settings.watermark_font,
                "watermark_color": settings.watermark_color,
                "watermark_size": settings.watermark_size,
                "watermark_direction": settings.watermark_direction,
            }
        )
    return payload


@app.get("/branding")
def public_branding(db: Session = Depends(db_session)) -> dict[str, str | None]:
    settings = db.scalar(select(BrandingSettings).limit(1))
    if not settings:
        settings = BrandingSettings()
        db.add(settings)
        db.commit()
    return _branding_payload(settings)


@app.get("/admin/branding")
def admin_branding(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, str | int | None]:
    require_admin(request)
    settings = db.scalar(select(BrandingSettings).limit(1))
    if not settings:
        settings = BrandingSettings()
        db.add(settings)
        db.commit()
    return _branding_payload(settings, include_protection=True)


@app.patch("/admin/branding")
def update_admin_branding(
    payload: BrandingSettingsInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str | int | None]:
    require_admin(request)
    settings = db.scalar(select(BrandingSettings).limit(1))
    if not settings:
        settings = BrandingSettings()
        db.add(settings)
    settings.login_title = payload.login_title.strip()
    settings.login_intro = payload.login_intro.strip()
    settings.login_helper = payload.login_helper.strip()
    audit(db, "branding.settings_updated", str(settings.id))
    db.commit()
    return _branding_payload(settings, include_protection=True)


@app.patch("/admin/branding/protection")
def update_visual_protection(
    payload: VisualProtectionSettingsInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str | int | None]:
    """Persiste uma única proteção visual e reprocessa derivados sem servir originais."""
    require_admin(request)
    settings = db.scalar(select(BrandingSettings).limit(1).with_for_update())
    if not settings:
        settings = BrandingSettings()
        db.add(settings)
        db.flush()
    for field, value in payload.model_dump().items():
        setattr(settings, field, value)
    for photo in db.scalars(select(PhotoAsset)).all():
        job = enqueue_derivatives(db, photo)
        job.status = "queued"
        job.last_error = None
        derivative = db.scalar(
            select(MediaDerivative).where(
                MediaDerivative.photo_asset_id == photo.id,
                MediaDerivative.variant == "client_preview",
            )
        )
        if derivative:
            derivative.status = "queued"
    audit(db, "branding.visual_protection_updated", str(settings.id))
    db.commit()
    return _branding_payload(settings, include_protection=True)


@app.put("/admin/branding/{asset}")
async def upload_branding_asset(
    asset: str, request: Request, db: Session = Depends(db_session)
) -> dict[str, str | None]:
    """Store one validated branding image; paths never come from the browser."""
    require_admin(request)
    if asset not in BRANDING_ASSETS:
        raise HTTPException(status_code=404, detail="Ativo de marca não encontrado.")
    body = await request.body()
    suffix, _ = validate_branding_asset(asset, request.headers.get("content-type"), body)
    key = f"{asset}{suffix}"
    destination = branding_asset_path(key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{suffix}.uploading")
    temporary.write_bytes(body)
    temporary.replace(destination)
    settings = db.scalar(select(BrandingSettings).limit(1))
    if not settings:
        settings = BrandingSettings()
        db.add(settings)
    if asset == "logo":
        settings.logo_key = key
    elif asset == "app-icon":
        settings.app_icon_key = key
    else:
        settings.favicon_key = key
    audit(db, "branding.asset_uploaded", f"{settings.id}:{asset}")
    db.commit()
    return _branding_payload(settings)


@app.get("/branding/{asset}")
def public_branding_asset(asset: str, db: Session = Depends(db_session)) -> FileResponse:
    if asset not in BRANDING_ASSETS:
        raise HTTPException(status_code=404, detail="Ativo de marca não encontrado.")
    settings = db.scalar(select(BrandingSettings).limit(1))
    key = (
        None
        if not settings
        else {
            "logo": settings.logo_key,
            "app-icon": settings.app_icon_key,
            "favicon": settings.favicon_key,
        }[asset]
    )
    if not key:
        raise HTTPException(status_code=404, detail="Ativo de marca não configurado.")
    try:
        path = branding_asset_path(key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Ativo de marca indisponível.") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Ativo de marca indisponível.")
    suffix = path.suffix.lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".webp": "image/webp",
        ".ico": "image/x-icon",
    }.get(suffix)
    if not media_type:
        raise HTTPException(status_code=404, detail="Ativo de marca indisponível.")
    return FileResponse(
        path, media_type=media_type, headers={"Cache-Control": "public, max-age=300"}
    )


@app.get("/admin/validation-summary")
def admin_validation_summary(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Resumo seguro para o painel visual do fotógrafo."""
    require_admin(request)
    jobs = list(db.scalars(select(MediaJob)))
    job_states: defaultdict[str, int] = defaultdict(int)
    for job in jobs:
        job_states[job.status] += 1
    galleries = list(db.scalars(select(DerivedGallery).order_by(DerivedGallery.created_at.desc())))
    return {
        "environment": getenv("APP_ENV", "development"),
        "version": getenv("APP_VERSION", "local"),
        "counts": {
            "clients": len(list(db.scalars(select(Client.id)))),
            "parent_galleries": len(
                list(
                    db.scalars(
                        select(ParentGallery.id).where(ParentGallery.lifecycle_status != "deleted")
                    )
                )
            ),
            "derived_galleries": len(galleries),
            "imports": dict(job_states),
            "folders_preparing": len(
                list(db.scalars(select(PhotoFolder.id).where(PhotoFolder.status == "preparing")))
            ),
            "folders_released": len(
                list(
                    db.scalars(
                        select(PhotoFolder.id).where(
                            PhotoFolder.status == "released",
                            PhotoFolder.purpose == "content",
                        )
                    )
                )
            ),
        },
        "recent_galleries": [
            {
                "id": str(gallery.id),
                "name": gallery.name,
                "access_enabled": gallery.access_enabled,
                "selection_expires_at": gallery.selection_expires_at.isoformat()
                if gallery.selection_expires_at
                else None,
            }
            for gallery in galleries[:5]
        ],
    }


@app.get("/admin/clients")
def admin_clients(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    db: Session = Depends(db_session),
) -> dict[str, list[dict[str, str]]]:
    require_admin(request)
    statement = select(Client).order_by(func.lower(Client.full_name), Client.id)
    if query:
        normalized = query.strip()
        statement = statement.where(
            func.lower(Client.full_name).contains(normalized.casefold())
            | Client.phone_e164.contains(normalized)
        )
    clients = db.scalars(statement)
    return {
        "clients": [
            {"id": str(item.id), "name": item.full_name, "phone": item.phone_e164}
            for item in clients
        ]
    }


@app.post("/admin/clients", status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    require_admin(request)
    phone = normalize_e164(payload.phone_e164)
    try:
        assert_phone_available(db, phone)
    except ClientIdentityConflict:
        raise HTTPException(status_code=409, detail="Já existe cliente com este WhatsApp.")
    client = Client(full_name=payload.full_name.strip(), phone_e164=phone)
    db.add(client)
    db.flush()
    db.add(
        ClientPhone(
            client_id=client.id,
            phone_e164=phone,
            active=True,
            verified_at=None,
        )
    )
    audit(db, "client.created_by_admin", str(client.id))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe cliente com este WhatsApp.") from exc
    return {"id": str(client.id)}


def client_deletion_inventory(db: Session, client: Client) -> dict[str, object]:
    """Conta referências que impedem apagar uma identidade de cliente."""

    direct_models = {
        "gallery_accesses": GalleryAccess,
        "public_gallery_registrations": ParentGalleryRegistration,
        "private_galleries_owned": DerivedGallery,
        "private_gallery_memberships": DerivedGalleryMembership,
        "gallery_capabilities": GalleryAccessCapability,
        "selections": PhotoSelection,
        "favorites": PhotoFavorite,
        "views": PhotoView,
        "comments": PhotoComment,
        "orders": SaleOrder,
        "payment_communications": PaymentCommunication,
        "membership_notifications": GalleryMembershipNotificationOutbox,
    }
    blockers = {
        name: int(
            db.scalar(select(func.count()).select_from(model).where(model.client_id == client.id))
            or 0
        )
        for name, model in direct_models.items()
    }
    blockers["sessions"] = int(
        db.scalar(
            select(func.count())
            .select_from(AuthSession)
            .where(AuthSession.role == Role.CLIENT.value, AuthSession.subject_id == client.id)
        )
        or 0
    )
    phones = list(
        db.scalars(select(ClientPhone.phone_e164).where(ClientPhone.client_id == client.id))
    )
    fingerprints = [pii_fingerprint(phone) for phone in phones]
    blockers["otp_challenges"] = int(
        db.scalar(
            select(func.count()).select_from(AuthChallenge).where(
                AuthChallenge.kind == "client_otp",
                (AuthChallenge.subject.in_(phones) if phones else False)
                | (AuthChallenge.subject_fingerprint.in_(fingerprints) if fingerprints else False),
            )
        )
        or 0
    )
    blockers["whatsapp_deliveries"] = int(
        db.scalar(
            select(func.count()).select_from(WhatsAppDelivery).where(
                (WhatsAppDelivery.recipient_phone.in_(phones) if phones else False)
                | (
                    WhatsAppDelivery.recipient_fingerprint.in_(fingerprints)
                    if fingerprints
                    else False
                ),
            )
        )
        or 0
    )
    blocking = {name: quantity for name, quantity in blockers.items() if quantity}
    return {
        "client_id": str(client.id),
        "blockers": blockers,
        "blocking": blocking,
        "can_delete": not blocking,
        "removable": {"client": 1, "phone_records": len(phones)},
    }


@app.patch("/admin/clients/{client_id}")
def update_client_name(
    client_id: UUID,
    payload: ClientNameInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_admin(request)
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrada.")
    client.full_name = " ".join(payload.full_name.split())
    audit(db, "client.name_changed", str(client.id))
    db.commit()
    return {"id": str(client.id), "name": client.full_name, "phone": client.phone_e164}


@app.get("/admin/clients/{client_id}/deletion-inventory")
def get_client_deletion_inventory(
    client_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrada.")
    return client_deletion_inventory(db, client)


@app.delete("/admin/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    require_admin(request)
    client = db.scalar(select(Client).where(Client.id == client_id).with_for_update())
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrada.")
    inventory = client_deletion_inventory(db, client)
    if not inventory["can_delete"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Este cadastro possui vínculos ou histórico protegido. "
                    "Edite o telefone ou desvincule a cliente em vez de excluí-la."
                ),
                "blocking": inventory["blocking"],
            },
        )
    try:
        db.execute(delete(ClientPhone).where(ClientPhone.client_id == client.id))
        db.delete(client)
        audit(db, "client.deleted_without_history", str(client_id))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "O cadastro recebeu uma nova dependência durante a exclusão. "
                "Atualize o inventário e tente novamente."
            ),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/admin/parent-galleries")
def admin_parent_galleries(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    require_admin(request)
    galleries = db.scalars(
        select(ParentGallery)
        .where(ParentGallery.lifecycle_status != "deleted")
        .order_by(ParentGallery.created_at.desc())
    )
    return {
        "parent_galleries": [
            {"id": str(item.id), "name": item.name, "event_name": item.event_name or ""}
            for item in galleries
        ]
    }


@app.get("/admin/parent-galleries/overview")
def parent_gallery_overview(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    """Catálogo operacional da Galeria pública, sem servir fotos a clientes."""
    require_admin(request)
    search = query.casefold() if query else ""
    rows = []
    for parent in db.scalars(
        select(ParentGallery)
        .where(ParentGallery.lifecycle_status != "deleted")
        .order_by(ParentGallery.created_at.desc())
    ):
        galleries = list(
            db.scalars(select(DerivedGallery).where(DerivedGallery.parent_gallery_id == parent.id))
        )
        registrations = list(
            db.scalars(
                select(ParentGalleryRegistration).where(
                    ParentGalleryRegistration.parent_gallery_id == parent.id
                )
            )
        )
        owners = [db.get(Client, gallery.client_id) for gallery in galleries]
        if search and not (
            search in parent.name.casefold()
            or (parent.event_name and search in parent.event_name.casefold())
            or any(
                owner and (search in owner.full_name.casefold() or search in owner.phone_e164)
                for owner in owners
            )
        ):
            continue
        frozen = sum(
            bool(gallery.selection_expires_at and expired(gallery.selection_expires_at))
            for gallery in galleries
        )
        rows.append(
            {
                "id": str(parent.id),
                "name": parent.name,
                "event_name": parent.event_name or "",
                "active": parent.active,
                "cover_preview_url": _cover_preview_url(db, parent),
                "private_gallery_count": len(galleries),
                "registration_count": len(registrations),
                "frozen_gallery_count": frozen,
            }
        )
    return {"total": len(rows), "parent_galleries": rows[offset : offset + limit]}


def _parent_gallery_or_404(db: Session, parent_gallery_id: UUID) -> ParentGallery:
    gallery = db.get(ParentGallery, parent_gallery_id)
    if not gallery or gallery.lifecycle_status == "deleted":
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    return gallery


def _gallery_capability_link(request: Request, token: str) -> str:
    """Gera link com token opaco, respeitando o proxy TLS de homologação."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    host = (
        request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
        .split(",")[0]
        .strip()
    )
    return f"{scheme}://{host}/?access_token={token}"


def _active_gallery_capability(
    db: Session,
    *,
    parent_gallery_id: UUID,
    scope: str,
    client_id: UUID | None = None,
    derived_gallery_id: UUID | None = None,
) -> GalleryAccessCapability | None:
    query = select(GalleryAccessCapability).where(
            GalleryAccessCapability.parent_gallery_id == parent_gallery_id,
            GalleryAccessCapability.scope == scope,
            GalleryAccessCapability.status == "active",
            GalleryAccessCapability.client_id == client_id,
        )
    if derived_gallery_id:
        query = query.where(GalleryAccessCapability.derived_gallery_id == derived_gallery_id)
    capability = db.scalar(query)
    if capability and capability.expires_at and expired(capability.expires_at):
        return None
    return capability


def _gallery_cover_photo(db: Session, gallery: ParentGallery) -> PhotoAsset | None:
    if gallery.cover_photo_id:
        cover = db.get(PhotoAsset, gallery.cover_photo_id)
        if cover and cover.parent_gallery_id == gallery.id:
            return cover
    return db.scalar(
        select(PhotoAsset)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .join(MediaDerivative, MediaDerivative.photo_asset_id == PhotoAsset.id)
        .where(
            PhotoAsset.parent_gallery_id == gallery.id,
            PhotoFolder.purpose == "content",
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
        .order_by(PhotoFolder.position, PhotoAsset.created_at, PhotoAsset.filename)
        .limit(1)
    )


def _cover_preview_url(db: Session, gallery: ParentGallery) -> str | None:
    cover = _gallery_cover_photo(db, gallery)
    if not cover:
        return None
    ready = db.scalar(
        select(MediaDerivative.id).where(
            MediaDerivative.photo_asset_id == cover.id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
    )
    return f"/admin/photo-assets/{cover.id}/watermarked-preview" if ready else None


def _client_preview_derivative(db: Session, photo_id: UUID) -> MediaDerivative | None:
    return db.scalar(
        select(MediaDerivative).where(
            MediaDerivative.photo_asset_id == photo_id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
    )


def _photo_publication_state(
    photo: PhotoAsset,
    job: MediaJob | None,
    derivative: MediaDerivative | None,
) -> str:
    if photo.available:
        return "published"
    if derivative:
        return "ready_to_publish"
    if job and job.status == "failed":
        return "failed"
    return "processing"


def _cover_assets_folder(db: Session, gallery: ParentGallery) -> PhotoFolder:
    db.scalar(select(ParentGallery.id).where(ParentGallery.id == gallery.id).with_for_update())
    folder = db.scalar(
        select(PhotoFolder).where(
            PhotoFolder.parent_gallery_id == gallery.id,
            PhotoFolder.purpose == "cover_assets",
        )
    )
    if folder:
        return folder
    minimum_position = db.scalar(
        select(func.min(PhotoFolder.position)).where(PhotoFolder.parent_gallery_id == gallery.id)
    )
    folder = PhotoFolder(
        parent_gallery_id=gallery.id,
        name="Ativos de capa",
        purpose="cover_assets",
        position=min(-1, (minimum_position or 0) - 1),
    )
    db.add(folder)
    db.flush()
    return folder


@app.get("/admin/parent-galleries/{parent_gallery_id}/editor")
def parent_gallery_editor(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Resumo backend-driven das cinco etapas do editor administrativo."""
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id)
    folder_count = (
        db.scalar(
            select(func.count())
            .select_from(PhotoFolder)
            .where(
                PhotoFolder.parent_gallery_id == gallery.id,
                PhotoFolder.purpose == "content",
            )
        )
        or 0
    )
    registration_count = (
        db.scalar(
            select(func.count())
            .select_from(ParentGalleryRegistration)
            .where(ParentGalleryRegistration.parent_gallery_id == gallery.id)
        )
        or 0
    )
    derived_count = (
        db.scalar(
            select(func.count())
            .select_from(DerivedGallery)
            .where(DerivedGallery.parent_gallery_id == gallery.id)
        )
        or 0
    )
    public_capability = _active_gallery_capability(
        db, parent_gallery_id=gallery.id, scope="public_gallery"
    )
    return {
        "gallery": {
            "id": str(gallery.id),
            "name": gallery.name,
            "event_name": gallery.event_name or "",
            "description": gallery.description or "",
            "active": gallery.active,
            "access_mode": gallery.access_mode,
            "folder_display_mode": gallery.folder_display_mode,
            "cover_title_font": normalize_title_font(gallery.cover_title_font),
            "cover_title_color": gallery.cover_title_color,
            "cover_title_size": gallery.cover_title_size,
            "cover_title_position": gallery.cover_title_position,
            "unlisted_link": None,
            "public_link": {
                "status": "active" if public_capability else "unavailable",
                "capability_id": str(public_capability.id) if public_capability else None,
                "expires_at": public_capability.expires_at.isoformat()
                if public_capability and public_capability.expires_at
                else None,
                "secret_available": False,
            },
            "cover_photo_id": str(gallery.cover_photo_id) if gallery.cover_photo_id else None,
            "cover_preview_url": _cover_preview_url(db, gallery),
        },
        "steps": [
            {"id": "ajustes", "label": "Ajustes", "status": "complete", "available": True},
            {"id": "vendas", "label": "Vendas", "status": "complete", "available": True},
            {
                "id": "detalhes",
                "label": "Detalhes",
                "status": "complete" if gallery.cover_photo_id else "pending",
                "available": True,
            },
            {
                "id": "imagens",
                "label": "Imagens",
                "status": "complete" if folder_count else "pending",
                "available": True,
            },
            {
                "id": "clientes",
                "label": "Clientes",
                "status": "complete" if registration_count or derived_count else "pending",
                "available": True,
            },
        ],
        "counts": {
            "folders": folder_count,
            "registrations": registration_count,
            "derived_galleries": derived_count,
        },
        "capabilities": {
            "sales_configuration": True,
            "visual_customization": True,
            "folder_management": True,
            "client_links": True,
        },
        "actions": {"can_create_folder": gallery.active, "can_upload": gallery.active},
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/settings")
def parent_gallery_settings(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id)
    return {
        "id": str(gallery.id),
        "name": gallery.name,
        "event_name": gallery.event_name or "",
        "description": gallery.description or "",
        "active": gallery.active,
        "access_mode": gallery.access_mode,
        "folder_display_mode": gallery.folder_display_mode,
        "cover_title_font": normalize_title_font(gallery.cover_title_font),
        "cover_title_color": gallery.cover_title_color,
        "cover_title_size": gallery.cover_title_size,
        "cover_title_position": gallery.cover_title_position,
        "sales_message": gallery.sales_message or "",
        "selection_duration_days": gallery.selection_duration_days,
        "favorites_enabled": gallery.favorites_enabled,
        "comments_enabled": gallery.comments_enabled,
    }


@app.patch("/admin/parent-galleries/{parent_gallery_id}/settings")
def update_parent_gallery_settings(
    parent_gallery_id: UUID,
    payload: ParentGallerySettingsInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(gallery, field, value.strip() if isinstance(value, str) else value)
    audit(db, "parent_gallery.settings_updated", str(gallery.id))
    db.commit()
    return parent_gallery_settings(parent_gallery_id, request, db)


@app.get("/admin/parent-galleries/{parent_gallery_id}/summary")
def parent_gallery_summary(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id)
    folders = list(
        db.scalars(
            select(PhotoFolder).where(
                PhotoFolder.parent_gallery_id == gallery.id,
                PhotoFolder.purpose == "content",
            )
        )
    )
    photo_count = (
        db.scalar(
            select(func.count())
            .select_from(PhotoAsset)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                PhotoAsset.parent_gallery_id == gallery.id,
                PhotoFolder.purpose == "content",
            )
        )
        or 0
    )
    clients = parent_gallery_clients(parent_gallery_id, request, db)["clients"]
    public_capability = _active_gallery_capability(
        db, parent_gallery_id=gallery.id, scope="public_gallery"
    )
    return {
        "id": str(gallery.id),
        "name": gallery.name,
        "event_name": gallery.event_name or "",
        "active": gallery.active,
        "unlisted_link": None,
        "public_link_status": "active" if public_capability else "unavailable",
        "cover_preview_url": _cover_preview_url(db, gallery),
        "counts": {"folders": len(folders), "photos": photo_count, "clients": len(clients)},
        "clients": clients,
    }


@app.put("/admin/parent-galleries/{parent_gallery_id}/cover")
def set_parent_gallery_cover(
    parent_gallery_id: UUID,
    payload: ParentGalleryCoverInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id)
    photo = db.get(PhotoAsset, payload.photo_id)
    if not photo or photo.parent_gallery_id != gallery.id:
        raise HTTPException(status_code=422, detail="A capa precisa pertencer a esta galeria.")
    if not db.scalar(
        select(MediaDerivative.id).where(
            MediaDerivative.photo_asset_id == photo.id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
    ):
        raise HTTPException(
            status_code=409, detail="A foto ainda não possui prévia pronta para capa."
        )
    gallery.cover_photo_id = photo.id
    audit(db, "parent_gallery.cover_set", str(gallery.id))
    db.commit()
    return {"photo_id": str(photo.id), "preview_url": _cover_preview_url(db, gallery)}


@app.delete(
    "/admin/parent-galleries/{parent_gallery_id}/cover", status_code=status.HTTP_204_NO_CONTENT
)
def clear_parent_gallery_cover(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    require_admin(request)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id)
    gallery.cover_photo_id = None
    audit(db, "parent_gallery.cover_cleared", str(gallery.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/admin/parent-galleries/{parent_gallery_id}/sales")
def parent_gallery_sales(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id)
    return {
        "available": True,
        "capabilities": [
            "pricing_tiers",
            "pix",
            "sales_message",
            "interactions",
            "selection_deadline",
        ],
        "sales_message": gallery.sales_message or "",
        "selection_duration_days": gallery.selection_duration_days,
        "favorites_enabled": gallery.favorites_enabled,
        "comments_enabled": gallery.comments_enabled,
        **pricing_payload(db, gallery.id),
    }


@app.put("/admin/parent-galleries/{parent_gallery_id}/sales")
def update_parent_gallery_sales(
    parent_gallery_id: UUID,
    payload: ParentGallerySalesInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id)
    tiers = save_parent_pricing(db, gallery.id, payload)
    gallery.sales_message = payload.sales_message.strip() if payload.sales_message else None
    gallery.selection_duration_days = payload.selection_duration_days
    gallery.favorites_enabled = payload.favorites_enabled
    gallery.comments_enabled = payload.comments_enabled
    audit(db, "parent_gallery.sales_updated", str(gallery.id))
    db.commit()
    return {
        **parent_gallery_sales(parent_gallery_id, request, db),
        "has_downward_jump": has_downward_jump(tiers),
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/details")
def parent_gallery_details(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id)
    cover_rows = list(
        db.execute(
            select(PhotoAsset, PhotoFolder, MediaDerivative)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .outerjoin(
                MediaDerivative,
                (MediaDerivative.photo_asset_id == PhotoAsset.id)
                & (MediaDerivative.variant == "client_preview")
                & (MediaDerivative.status == "ready"),
            )
            .where(PhotoAsset.parent_gallery_id == gallery.id)
            .order_by(PhotoFolder.purpose, PhotoFolder.position, PhotoAsset.created_at)
        )
    )
    return {
        "available": True,
        "capabilities": ["cover", "title"],
        "font_options": list(TITLE_FONT_OPTIONS),
        "cover_options": [
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "source": folder.purpose,
                "status": "ready" if derivative else "processing",
                "preview_url": f"/admin/photo-assets/{photo.id}/watermarked-preview"
                if derivative
                else None,
                "width": derivative.width if derivative else None,
                "height": derivative.height if derivative else None,
            }
            for photo, folder, derivative in cover_rows
        ],
        "settings": {
            "cover_photo_id": str(gallery.cover_photo_id) if gallery.cover_photo_id else None,
            "cover_preview_url": _cover_preview_url(db, gallery),
            "cover_title_font": normalize_title_font(gallery.cover_title_font),
            "cover_title_color": gallery.cover_title_color,
            "cover_title_size": gallery.cover_title_size,
            "cover_title_position": gallery.cover_title_position,
        },
    }


@app.post(
    "/admin/parent-galleries/{parent_gallery_id}/cover-photos",
    status_code=status.HTTP_201_CREATED,
)
def register_parent_gallery_cover_photo(
    parent_gallery_id: UUID,
    payload: ParentGalleryCoverUploadInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    """Registra um JPEG de capa na pasta técnica sem publicá-lo como conteúdo."""
    require_admin(request)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id)
    if not gallery.active:
        raise HTTPException(status_code=409, detail="A galeria está bloqueada para novas fotos.")
    folder = _cover_assets_folder(db, gallery)
    storage_key = (
        f"covers/{gallery.id}/{sha256(payload.idempotency_key.encode('utf-8')).hexdigest()}.jpg"
    )
    asset = db.scalar(
        select(PhotoAsset).where(
            PhotoAsset.parent_gallery_id == gallery.id,
            PhotoAsset.storage_key == storage_key,
        )
    )
    if not asset:
        asset = PhotoAsset(
            parent_gallery_id=gallery.id,
            folder_id=folder.id,
            filename=payload.filename,
            display_name=payload.display_name,
            storage_key=storage_key,
            available=False,
        )
        db.add(asset)
        db.flush()
        audit(db, "parent_gallery.cover_photo_registered", str(asset.id))
    db.commit()
    return {
        "id": str(asset.id),
        "upload_url": f"/admin/photo-assets/{asset.id}/source",
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/photos")
def admin_parent_gallery_photos(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    require_admin(request)
    if not db.get(ParentGallery, parent_gallery_id):
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    photos = db.scalars(
        select(PhotoAsset)
        .where(PhotoAsset.parent_gallery_id == parent_gallery_id)
        .order_by(PhotoAsset.filename)
    )
    return {
        "photos": [
            {"id": str(item.id), "name": item.display_name or item.filename} for item in photos
        ]
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/available-photos")
def admin_parent_gallery_available_photos(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, object]]]:
    """Lista somente fotos elegíveis para criação administrativa de privada."""

    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id)
    photos = list(
        db.scalars(
            select(PhotoAsset)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                PhotoAsset.parent_gallery_id == parent_gallery_id,
                PhotoAsset.available,
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
            )
            .order_by(PhotoFolder.position, PhotoAsset.created_at, PhotoAsset.filename)
        )
    )
    folders = {
        folder.id: folder
        for folder in db.scalars(
            select(PhotoFolder).where(
                PhotoFolder.parent_gallery_id == parent_gallery_id,
                PhotoFolder.purpose == "content",
            )
        )
    }
    ready_derivatives = (
        {
            derivative.photo_asset_id: derivative
            for derivative in db.scalars(
                select(MediaDerivative).where(
                    MediaDerivative.photo_asset_id.in_([photo.id for photo in photos]),
                    MediaDerivative.variant == "client_preview",
                    MediaDerivative.status == "ready",
                )
            )
        }
        if photos
        else {}
    )
    return {
        "photos": [
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "folder_name": folders[photo.folder_id].name,
                "preview_url": f"/admin/photo-assets/{photo.id}/watermarked-preview"
                if photo.id in ready_derivatives
                else None,
                "width": ready_derivatives[photo.id].width
                if photo.id in ready_derivatives
                else None,
                "height": ready_derivatives[photo.id].height
                if photo.id in ready_derivatives
                else None,
                "publication_state": "published",
            }
            for photo in photos
        ]
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/folders")
def admin_parent_gallery_folders(
    parent_gallery_id: UUID,
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    if not db.get(ParentGallery, parent_gallery_id):
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    folders = list(
        db.scalars(
            select(PhotoFolder)
            .where(
                PhotoFolder.parent_gallery_id == parent_gallery_id,
                PhotoFolder.purpose == "content",
            )
            .order_by(PhotoFolder.position, PhotoFolder.created_at)
        )
    )
    rows = []
    for folder in folders:
        count = (
            db.scalar(
                select(func.count())
                .select_from(PhotoAsset)
                .where(PhotoAsset.folder_id == folder.id)
            )
            or 0
        )
        preview_photo_id = db.scalar(
            select(PhotoAsset.id)
            .join(MediaDerivative, MediaDerivative.photo_asset_id == PhotoAsset.id)
            .where(
                PhotoAsset.folder_id == folder.id,
                MediaDerivative.variant == "client_preview",
                MediaDerivative.status == "ready",
            )
            .order_by(PhotoAsset.created_at, PhotoAsset.filename)
            .limit(1)
        )
        state_rows = list(
            db.execute(
                select(PhotoAsset, MediaJob, MediaDerivative)
                .outerjoin(MediaJob, MediaJob.photo_asset_id == PhotoAsset.id)
                .outerjoin(
                    MediaDerivative,
                    (MediaDerivative.photo_asset_id == PhotoAsset.id)
                    & (MediaDerivative.variant == "client_preview")
                    & (MediaDerivative.status == "ready"),
                )
                .where(PhotoAsset.folder_id == folder.id)
            )
        )
        state_counts = {
            "published": 0,
            "ready_to_publish": 0,
            "processing": 0,
            "failed": 0,
        }
        for photo, job, derivative in state_rows:
            state_counts[_photo_publication_state(photo, job, derivative)] += 1
        rows.append(
            {
                "id": str(folder.id),
                "name": folder.name,
                "status": folder.status,
                "position": folder.position,
                "photo_count": count,
                "publication_counts": state_counts,
                "preview_url": f"/admin/photo-assets/{preview_photo_id}/watermarked-preview"
                if preview_photo_id
                else None,
                "released_at": folder.released_at.isoformat() if folder.released_at else None,
            }
        )
    return {"total": len(rows), "folders": rows[offset : offset + limit]}


@app.post(
    "/admin/parent-galleries/{parent_gallery_id}/folders", status_code=status.HTTP_201_CREATED
)
def create_photo_folder(
    parent_gallery_id: UUID,
    payload: PhotoFolderInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    parent = require_parent_gallery_mutable(db, parent_gallery_id)
    if not parent.active:
        raise HTTPException(status_code=409, detail="A galeria está bloqueada para novas pastas.")
    last_position = db.scalar(
        select(func.max(PhotoFolder.position)).where(
            PhotoFolder.parent_gallery_id == parent_gallery_id,
            PhotoFolder.purpose == "content",
        )
    )
    position = (last_position if last_position is not None else -1) + 1
    folder = PhotoFolder(
        parent_gallery_id=parent_gallery_id,
        name=payload.name.strip(),
        position=position,
        purpose="content",
    )
    db.add(folder)
    db.flush()
    audit(db, "photo_folder.created", str(folder.id))
    db.commit()
    return {"id": str(folder.id), "status": folder.status, "position": folder.position}


@app.patch("/admin/photo-folders/{folder_id}")
def rename_photo_folder(
    folder_id: UUID,
    payload: PhotoFolderRenameInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_admin(request)
    folder = db.get(PhotoFolder, folder_id)
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    require_parent_gallery_mutable(db, folder.parent_gallery_id)
    if folder.status == "released":
        raise HTTPException(status_code=409, detail="Uma pasta liberada não pode ser renomeada.")
    folder.name = payload.name.strip()
    audit(db, "photo_folder.renamed", str(folder.id))
    db.commit()
    return {"id": str(folder.id), "name": folder.name}


@app.delete("/admin/photo-folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo_folder(
    folder_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    require_admin(request)
    folder = db.get(PhotoFolder, folder_id)
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    require_parent_gallery_mutable(db, folder.parent_gallery_id)
    if folder.status == "released" or db.scalar(
        select(PhotoAsset.id).where(PhotoAsset.folder_id == folder.id)
    ):
        raise HTTPException(
            status_code=409, detail="Apenas pasta vazia em preparação pode ser excluída."
        )
    audit(db, "photo_folder.deleted", str(folder.id))
    db.delete(folder)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/admin/photo-folders/{folder_id}/photos")
def admin_photo_folder_photos(
    folder_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Estado administrativo por arquivo, sem expor a origem privada."""
    require_admin(request)
    if not (folder := db.get(PhotoFolder, folder_id)) or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    photos = list(
        db.scalars(
            select(PhotoAsset)
            .where(PhotoAsset.folder_id == folder.id)
            .order_by(PhotoAsset.filename)
        )
    )
    confirmed_photo_ids = (
        set(
            db.scalars(
                select(SaleOrderItem.photo_asset_id)
                .join(SaleOrder)
                .where(
                    SaleOrderItem.photo_asset_id.in_([photo.id for photo in photos]),
                    SaleOrder.payment_status == "confirmed",
                )
            )
        )
        if photos
        else set()
    )
    parent = db.get(ParentGallery, folder.parent_gallery_id)
    rows = []
    for photo in photos:
        job = db.scalar(select(MediaJob).where(MediaJob.photo_asset_id == photo.id))
        derivative = _client_preview_derivative(db, photo.id)
        rows.append(
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "preview_url": f"/admin/photo-assets/{photo.id}/watermarked-preview"
                if derivative
                else None,
                "status": job.status if job else "not_imported",
                "publication_state": _photo_publication_state(photo, job, derivative),
                "available": photo.available,
                "width": derivative.width if derivative else None,
                "height": derivative.height if derivative else None,
                "error": job.last_error if job else None,
                "can_delete": photo.id not in confirmed_photo_ids,
                "is_cover": bool(parent and parent.cover_photo_id == photo.id),
            }
        )
    return {
        "folder": {"id": str(folder.id), "status": folder.status},
        "total": len(rows),
        "photos": rows,
    }


@app.delete(
    "/admin/photo-folders/{folder_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_folder_photo_asset(
    folder_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    """Exclui foto após aplicar a política comercial comum."""
    require_admin(request)
    folder, photo = db.get(PhotoFolder, folder_id), db.get(PhotoAsset, photo_id)
    if (
        not folder
        or not photo
        or photo.folder_id != folder.id
        or photo.parent_gallery_id != folder.parent_gallery_id
    ):
        raise HTTPException(status_code=404, detail="Foto não encontrada nesta pasta.")
    require_parent_gallery_mutable(db, folder.parent_gallery_id)
    enforce_commercial_removal_or_409(
        db,
        parent_gallery_id=folder.parent_gallery_id,
        photo_asset_id=photo.id,
    )
    paths_to_remove = []
    try:
        paths_to_remove.append(safe_source_path(photo))
    except ValueError:
        # Um caminho corrompido não deve impedir a limpeza dos registros, nem autorizar apagar fora do storage.
        pass
    derivatives = list(
        db.scalars(select(MediaDerivative).where(MediaDerivative.photo_asset_id == photo.id))
    )
    for derivative in derivatives:
        try:
            paths_to_remove.append(safe_derivative_path(derivative))
        except ValueError:
            continue
    parent = db.get(ParentGallery, photo.parent_gallery_id)
    if parent and parent.cover_photo_id == photo.id:
        parent.cover_photo_id = None
    db.execute(delete(PhotoComment).where(PhotoComment.photo_asset_id == photo.id))
    db.execute(delete(PhotoFavorite).where(PhotoFavorite.photo_asset_id == photo.id))
    db.execute(delete(PhotoView).where(PhotoView.photo_asset_id == photo.id))
    db.execute(delete(PhotoSelection).where(PhotoSelection.photo_asset_id == photo.id))
    db.execute(delete(DerivedGalleryPhoto).where(DerivedGalleryPhoto.photo_asset_id == photo.id))
    db.execute(delete(MediaDerivative).where(MediaDerivative.photo_asset_id == photo.id))
    db.execute(delete(MediaJob).where(MediaJob.photo_asset_id == photo.id))
    db.delete(photo)
    audit(db, "photo_asset.deleted", str(photo_id))
    db.commit()
    for path in paths_to_remove:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            # A limpeza física é idempotente. Uma nova rotina de mídia poderá remover o resíduo seguro.
            continue
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/admin/photo-folders/{folder_id}/photos")
def delete_folder_photo_assets(
    folder_id: UUID,
    payload: PhotoBulkDeleteInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, list[str]]:
    """Exclui em massa as fotos elegíveis e informa as protegidas."""
    require_admin(request)
    folder = db.get(PhotoFolder, folder_id)
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    require_parent_gallery_mutable(db, folder.parent_gallery_id)
    deleted: list[str] = []
    blocked: list[str] = []
    missing: list[str] = []
    for photo_id in dict.fromkeys(payload.photo_ids):
        photo = db.get(PhotoAsset, photo_id)
        if not photo or photo.folder_id != folder_id:
            missing.append(str(photo_id))
            continue
        try:
            delete_folder_photo_asset(folder_id, photo_id, request, db)
            deleted.append(str(photo_id))
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
            blocked.append(str(photo_id))
    return {"deleted_ids": deleted, "blocked_ids": blocked, "missing_ids": missing}


@app.post("/admin/photo-folders/{folder_id}/photos", status_code=status.HTTP_201_CREATED)
def register_folder_photo_asset(
    folder_id: UUID,
    payload: PhotoAssetInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    """Registra uma nova foto administrativa em pasta de conteúdo."""
    require_admin(request)
    folder = db.get(PhotoFolder, folder_id)
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if folder.status not in {"preparing", "released"}:
        raise HTTPException(status_code=409, detail="A pasta não aceita novas fotos.")
    parent = require_parent_gallery_mutable(db, folder.parent_gallery_id)
    if not parent.active:
        raise HTTPException(status_code=409, detail="A galeria está bloqueada para novas fotos.")
    asset = PhotoAsset(
        parent_gallery_id=folder.parent_gallery_id,
        folder_id=folder.id,
        available=False,
        **payload.model_dump(),
    )
    db.add(asset)
    db.flush()
    audit(db, "photo_asset.registered_in_folder", str(asset.id))
    db.commit()
    return {"id": str(asset.id)}


def _publish_photo_folder(
    db: Session, folder: PhotoFolder, *, commit: bool = True
) -> dict[str, object]:
    if folder.purpose != "content" or folder.status not in {"preparing", "released"}:
        raise HTTPException(status_code=409, detail="A pasta não pode ser publicada.")
    photos = list(db.scalars(select(PhotoAsset).where(PhotoAsset.folder_id == folder.id)))
    unpublished_ids = [photo.id for photo in photos if not photo.available]
    ready_ids = (
        set(
            db.scalars(
                select(MediaDerivative.photo_asset_id).where(
                    MediaDerivative.photo_asset_id.in_(unpublished_ids),
                    MediaDerivative.variant == "client_preview",
                    MediaDerivative.status == "ready",
                )
            )
        )
        if unpublished_ids
        else set()
    )
    for photo in photos:
        if photo.id in ready_ids:
            photo.available = True
    if folder.status == "preparing" and ready_ids:
        folder.status = "released"
        folder.released_at = now()
    failed_ids = (
        set(
            db.scalars(
                select(MediaJob.photo_asset_id).where(
                    MediaJob.photo_asset_id.in_(unpublished_ids),
                    MediaJob.status == "failed",
                )
            )
        )
        if unpublished_ids
        else set()
    )
    audit(db, "photo_folder.published", f"{folder.id}:{len(ready_ids)}")
    if commit:
        db.commit()
    else:
        db.flush()
    return {
        "id": str(folder.id),
        "status": folder.status,
        "published_count": len(ready_ids),
        "pending_count": max(0, len(unpublished_ids) - len(ready_ids) - len(failed_ids)),
        "failed_count": len(failed_ids),
        "available_count": sum(1 for photo in photos if photo.available),
    }


@app.post("/admin/photo-folders/{folder_id}/publish")
def publish_photo_folder(
    folder_id: UUID,
    _payload: PhotoFolderPublishInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    """Publica somente a rodada pronta na Galeria pública, sem destinos privados."""
    require_admin(request)
    folder = db.get(PhotoFolder, folder_id)
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    require_parent_gallery_mutable(db, folder.parent_gallery_id)
    return _publish_photo_folder(db, folder)


@app.post("/admin/parent-galleries/{parent_gallery_id}/publish-ready")
def publish_parent_gallery_ready_photos(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    """Publica a rodada pronta de todas as pastas antes de avançar no editor."""

    require_admin(request)
    require_parent_gallery_mutable(db, parent_gallery_id)
    folders = list(
        db.scalars(
            select(PhotoFolder)
            .where(
                PhotoFolder.parent_gallery_id == parent_gallery_id,
                PhotoFolder.purpose == "content",
            )
            .order_by(PhotoFolder.position, PhotoFolder.id)
        )
    )
    results = [_publish_photo_folder(db, folder, commit=False) for folder in folders]
    totals = {
        key: sum(int(result[key]) for result in results)
        for key in ("published_count", "pending_count", "failed_count", "available_count")
    }
    audit(db, "parent_gallery.ready_photos_published", str(parent_gallery_id))
    db.commit()
    return {**totals, "folders": results}


@app.post("/admin/photo-folders/{folder_id}/release")
def release_photo_folder(
    folder_id: UUID,
    payload: PhotoFolderReleaseInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    """Adaptador temporário: destinos privados foram removidos da publicação."""
    require_admin(request)
    if payload.gallery_ids:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "Destinos privados não são mais aceitos nesta ação. "
                "Publique a pasta e disponibilize fotos individualmente na etapa Clientes."
            ),
        )
    folder = db.get(PhotoFolder, folder_id)
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    require_parent_gallery_mutable(db, folder.parent_gallery_id)
    return _publish_photo_folder(db, folder)


@app.post("/admin/parent-galleries", status_code=status.HTTP_201_CREATED)
def create_parent_gallery(
    payload: ParentGalleryInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    gallery = ParentGallery(**payload.model_dump())
    db.add(gallery)
    db.flush()
    capability, token = issue_gallery_capability(
        db,
        parent_gallery_id=gallery.id,
        scope="public_gallery",
        actor_admin_id=admin_session.subject_id,
        reconstructible=True,
    )
    audit(db, "parent_gallery.created", str(gallery.id))
    audit(db, "gallery_capability.public_issued", str(capability.id))
    db.commit()
    return {
        "id": str(gallery.id),
        "public_link": _gallery_capability_link(request, token),
        "access_token": token,
        "capability_id": str(capability.id),
    }


def _validated_capability_expiry(value: datetime | None) -> datetime | None:
    if value and expired(value):
        raise HTTPException(status_code=422, detail="Informe uma expiração futura.")
    return value


def _capability_secret_response(
    request: Request, capability: GalleryAccessCapability, token: str
) -> dict[str, object]:
    return {
        "capability_id": str(capability.id),
        "scope": capability.scope,
        "status": capability.status,
        "expires_at": capability.expires_at.isoformat() if capability.expires_at else None,
        "access_token": token,
        "link": _gallery_capability_link(request, token),
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/public-link")
def parent_gallery_public_link_status(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id)
    capability = _active_gallery_capability(
        db, parent_gallery_id=parent_gallery_id, scope="public_gallery"
    )
    token = None
    if capability and capability.token_mode == "signed_v1":
        token = reconstruct_gallery_capability_token(capability)
    return {
        "status": "active" if capability else "unavailable",
        "capability_id": str(capability.id) if capability else None,
        "expires_at": capability.expires_at.isoformat()
        if capability and capability.expires_at
        else None,
        "secret_available": token is not None,
        "access_token": token,
        "link": _gallery_capability_link(request, token) if token else None,
    }


@app.post(
    "/admin/parent-galleries/{parent_gallery_id}/public-link",
    status_code=status.HTTP_201_CREATED,
)
def issue_parent_gallery_public_link(
    parent_gallery_id: UUID,
    payload: GalleryCapabilityInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    require_parent_gallery_mutable(db, parent_gallery_id)
    if _active_gallery_capability(db, parent_gallery_id=parent_gallery_id, scope="public_gallery"):
        raise HTTPException(
            status_code=409,
            detail="Já existe um link ativo; rotacione-o para obter um novo segredo.",
        )
    capability, token = issue_gallery_capability(
        db,
        parent_gallery_id=parent_gallery_id,
        scope="public_gallery",
        expires_at=_validated_capability_expiry(payload.expires_at),
        actor_admin_id=admin_session.subject_id,
        reconstructible=True,
    )
    audit(db, "gallery_capability.public_issued", str(capability.id))
    db.commit()
    return _capability_secret_response(request, capability, token)


@app.post("/admin/parent-galleries/{parent_gallery_id}/public-link/rotate")
def rotate_parent_gallery_public_link(
    parent_gallery_id: UUID,
    payload: GalleryCapabilityInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    require_parent_gallery_mutable(db, parent_gallery_id)
    capability = _active_gallery_capability(
        db, parent_gallery_id=parent_gallery_id, scope="public_gallery"
    )
    if not capability:
        raise HTTPException(status_code=404, detail="Link ativo não encontrado.")
    replacement, token = rotate_gallery_capability(
        db,
        capability,
        actor_admin_id=admin_session.subject_id,
        reconstructible=True,
    )
    if payload.expires_at is not None:
        replacement.expires_at = _validated_capability_expiry(payload.expires_at)
    audit(db, "gallery_capability.public_rotated", str(replacement.id))
    db.commit()
    return _capability_secret_response(request, replacement, token)


@app.delete(
    "/admin/parent-galleries/{parent_gallery_id}/public-link",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_parent_gallery_public_link(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id)
    capability = _active_gallery_capability(
        db, parent_gallery_id=parent_gallery_id, scope="public_gallery"
    )
    if capability:
        revoke_gallery_capability(capability)
        audit(db, "gallery_capability.public_revoked", str(capability.id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _issue_individual_invite(
    db: Session,
    *,
    parent: ParentGallery,
    client: Client,
    actor_admin_id: UUID,
    expires_at: datetime | None,
) -> tuple[GalleryAccessCapability, str]:
    if _active_gallery_capability(
        db,
        parent_gallery_id=parent.id,
        scope="parent_invite",
        client_id=client.id,
    ):
        raise HTTPException(
            status_code=409,
            detail="Já existe um convite ativo; rotacione-o para obter um novo segredo.",
        )
    return issue_gallery_capability(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        scope="parent_invite",
        expires_at=_validated_capability_expiry(expires_at),
        actor_admin_id=actor_admin_id,
    )


@app.post(
    "/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite",
    status_code=status.HTTP_201_CREATED,
)
def issue_parent_gallery_client_invite(
    parent_gallery_id: UUID,
    client_id: UUID,
    payload: GalleryCapabilityInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    parent = require_parent_gallery_mutable(db, parent_gallery_id)
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    capability, token = _issue_individual_invite(
        db,
        parent=parent,
        client=client,
        actor_admin_id=admin_session.subject_id,
        expires_at=payload.expires_at,
    )
    audit(db, "gallery_capability.client_invite_issued", str(capability.id))
    db.commit()
    return _capability_secret_response(request, capability, token)


@app.post("/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite/rotate")
def rotate_parent_gallery_client_invite(
    parent_gallery_id: UUID,
    client_id: UUID,
    payload: GalleryCapabilityInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    require_parent_gallery_mutable(db, parent_gallery_id)
    capability = _active_gallery_capability(
        db,
        parent_gallery_id=parent_gallery_id,
        scope="parent_invite",
        client_id=client_id,
    )
    if not capability:
        raise HTTPException(status_code=404, detail="Convite ativo não encontrado.")
    replacement, token = rotate_gallery_capability(
        db, capability, actor_admin_id=admin_session.subject_id
    )
    if payload.expires_at is not None:
        replacement.expires_at = _validated_capability_expiry(payload.expires_at)
    audit(db, "gallery_capability.client_invite_rotated", str(replacement.id))
    db.commit()
    return _capability_secret_response(request, replacement, token)


@app.delete(
    "/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/invite",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_parent_gallery_client_invite(
    parent_gallery_id: UUID,
    client_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> Response:
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id)
    capability = _active_gallery_capability(
        db,
        parent_gallery_id=parent_gallery_id,
        scope="parent_invite",
        client_id=client_id,
    )
    if capability:
        revoke_gallery_capability(capability)
        audit(db, "gallery_capability.client_invite_revoked", str(capability.id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def lifecycle_operation_payload(operation: GalleryLifecycleOperation) -> dict[str, object]:
    manifest = operation.manifest or {}
    completed_steps = manifest.get("completed_steps", [])
    status_labels = {
        "queued": "Na fila",
        "preparing_history": "Preparando histórico",
        "removing_storage": "Removendo arquivos",
        "removing_records": "Removendo registros",
        "completed": "Concluída",
        "failed": "Falhou",
        "cancelled": "Cancelada",
    }
    active_lease = bool(
        operation.lease_token
        and operation.lease_expires_at
        and not expired(operation.lease_expires_at)
    )
    completed_count = len(set(completed_steps))
    progress_percent = (
        100 if operation.status in {"completed", "cancelled"} else min(completed_count * 25, 75)
    )
    return {
        "operation_id": str(operation.id),
        "operation_type": operation.operation_type,
        "target_parent_gallery_id": str(operation.target_parent_gallery_id),
        "target_client_id": str(operation.target_client_id) if operation.target_client_id else None,
        "status": operation.status,
        "attempts": operation.attempts,
        "inventory": manifest.get("inventory", {}),
        "completed_steps": completed_steps,
        "last_error": operation.last_error,
        "destructive_started_at": operation.destructive_started_at.isoformat()
        if operation.destructive_started_at
        else None,
        "completed_at": operation.completed_at.isoformat() if operation.completed_at else None,
        "status_url": f"/admin/gallery-lifecycle-operations/{operation.id}",
        "progress": {
            "label": status_labels[operation.status],
            "percent": progress_percent,
            "completed_steps": completed_count,
            "total_steps": 3,
            "failed_step": manifest.get("failed_step"),
        },
        "actions": {
            "can_cancel": operation.destructive_started_at is None
            and operation.status in {"queued", "preparing_history", "failed"}
            and not active_lease,
            "can_retry": operation.status == "failed",
            "should_poll": operation.status
            in {
                "queued",
                "preparing_history",
                "removing_storage",
                "removing_records",
            },
            "poll_after_ms": 1_000
            if operation.status
            in {
                "queued",
                "preparing_history",
                "removing_storage",
                "removing_records",
            }
            else None,
        },
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/deletion-inventory")
def parent_gallery_deletion_inventory(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Expõe consequências autorizadas antes da confirmação da exclusão."""

    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id)
    return {
        "operation_type": "delete_parent_gallery",
        "target": {"id": str(gallery.id), "name": gallery.name},
        "inventory": gallery_deletion_inventory(db, gallery.id),
        "consequences": {
            "public_gallery_removed": True,
            "public_access_revoked": True,
            "private_galleries_preserved": True,
            "private_referenced_photos_preserved": True,
            "clients_preserved": True,
            "commercial_history_preserved": True,
            "restoration_available_after_start": False,
        },
        "request": {
            "method": "DELETE",
            "url": f"/admin/parent-galleries/{gallery.id}",
            "requires_idempotency_key": True,
            "asynchronous": True,
        },
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/unlink-inventory")
def parent_gallery_client_unlink_inventory(
    parent_gallery_id: UUID,
    client_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    """Expõe o escopo exato da desvinculação antes da confirmação."""

    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id)
    client = db.get(Client, client_id)
    registration = db.scalar(
        select(ParentGalleryRegistration.id).where(
            ParentGalleryRegistration.parent_gallery_id == gallery.id,
            ParentGalleryRegistration.client_id == client_id,
        )
    )
    if not client or not registration:
        raise HTTPException(status_code=404, detail="Vínculo de cliente não encontrado.")
    return {
        "operation_type": "unlink_client",
        "target": {
            "parent_gallery_id": str(gallery.id),
            "parent_gallery_name": gallery.name,
            "client_id": str(client.id),
            "client_name": client.full_name,
        },
        "inventory": client_unlink_inventory(db, parent_gallery_id=gallery.id, client_id=client.id),
        "consequences": {
            "gallery_relationship_removed": True,
            "private_gallery_removed": False,
            "private_gallery_preserved_for_other_members": True,
            "client_preserved": True,
            "commercial_history_preserved": True,
            "other_gallery_relationships_preserved": True,
            "restoration_available_after_start": False,
        },
        "request": {
            "method": "DELETE",
            "url": f"/admin/parent-galleries/{gallery.id}/clients/{client.id}",
            "requires_idempotency_key": True,
            "asynchronous": True,
        },
    }


@app.delete(
    "/admin/parent-galleries/{parent_gallery_id}",
    status_code=status.HTTP_202_ACCEPTED,
)
def delete_parent_gallery(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Agenda a limpeza completa de uma Galeria pública de forma idempotente."""
    admin_session = current_session(request, Role.ADMIN)
    idempotency_key = request.headers.get("Idempotency-Key", "").strip()
    if not idempotency_key or len(idempotency_key) > 128:
        raise HTTPException(
            status_code=422,
            detail="Informe uma chave de idempotência válida.",
        )
    existing = db.scalar(
        select(GalleryLifecycleOperation).where(
            GalleryLifecycleOperation.idempotency_key == idempotency_key
        )
    )
    if existing:
        if (
            existing.operation_type != "delete_parent_gallery"
            or existing.target_parent_gallery_id != parent_gallery_id
        ):
            raise HTTPException(
                status_code=409,
                detail="A chave de idempotência já pertence a outra operação.",
            )
        return lifecycle_operation_payload(existing)

    gallery = _parent_gallery_or_404(db, parent_gallery_id)
    if gallery.lifecycle_status == "deleting":
        raise HTTPException(
            status_code=409,
            detail="A exclusão desta galeria já está em andamento.",
        )
    operation = GalleryLifecycleOperation(
        operation_type="delete_parent_gallery",
        target_parent_gallery_id=gallery.id,
        actor_admin_id=admin_session.subject_id,
        idempotency_key=idempotency_key,
        manifest={
            "inventory": gallery_deletion_inventory(db, gallery.id),
            "operational_storage": gallery_operational_storage_manifest(db, gallery.id),
        },
    )
    gallery.lifecycle_status = "deleting"
    db.add(operation)
    db.flush()
    audit(db, "parent_gallery.deletion_queued", str(operation.id))
    db.commit()
    return lifecycle_operation_payload(operation)


@app.get("/admin/gallery-lifecycle-operations/{operation_id}")
def gallery_lifecycle_operation_status(
    operation_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    operation = db.get(GalleryLifecycleOperation, operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operação não encontrada.")
    return lifecycle_operation_payload(operation)


@app.post("/admin/gallery-lifecycle-operations/{operation_id}/retry")
def retry_gallery_lifecycle_operation(
    operation_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Reagenda uma falha mantendo inventário e etapas já concluídas."""

    admin_session = current_session(request, Role.ADMIN)
    operation = db.scalar(
        select(GalleryLifecycleOperation)
        .where(GalleryLifecycleOperation.id == operation_id)
        .with_for_update()
    )
    if not operation:
        raise HTTPException(status_code=404, detail="Operação não encontrada.")
    if operation.status != "failed":
        raise HTTPException(
            status_code=409,
            detail="Somente uma operação com falha pode ser retomada.",
        )
    retry_failed_operation(db, operation)
    audit(
        db,
        "gallery_lifecycle.retry_queued",
        f"operation_id:{operation.id};actor_id:{admin_session.subject_id}",
    )
    db.commit()
    return lifecycle_operation_payload(operation)


@app.post("/admin/gallery-lifecycle-operations/{operation_id}/cancel")
def cancel_gallery_lifecycle_operation(
    operation_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    operation = db.scalar(
        select(GalleryLifecycleOperation)
        .where(GalleryLifecycleOperation.id == operation_id)
        .with_for_update()
    )
    if not operation:
        raise HTTPException(status_code=404, detail="Operação não encontrada.")
    if operation.status == "cancelled":
        return lifecycle_operation_payload(operation)
    if operation.destructive_started_at is not None or operation.status in {
        "removing_storage",
        "removing_records",
        "completed",
    }:
        raise HTTPException(
            status_code=409,
            detail=("A remoção física já começou e não pode ser cancelada nem restaurada."),
        )
    if (
        operation.lease_token
        and operation.lease_expires_at
        and not expired(operation.lease_expires_at)
    ):
        raise HTTPException(
            status_code=409,
            detail="A preparação está em processamento; tente novamente.",
        )
    transition_operation(operation, "cancelled")
    operation.lease_token = None
    operation.lease_expires_at = None
    if operation.operation_type == "delete_parent_gallery":
        gallery = db.get(ParentGallery, operation.target_parent_gallery_id)
        if gallery:
            gallery.lifecycle_status = "active"
    elif operation.operation_type == "unlink_client" and operation.target_client_id:
        previous_state = (operation.manifest or {}).get("previous_state", {})
        registration = db.scalar(
            select(ParentGalleryRegistration).where(
                ParentGalleryRegistration.parent_gallery_id == operation.target_parent_gallery_id,
                ParentGalleryRegistration.client_id == operation.target_client_id,
            )
        )
        if registration:
            registration.status = previous_state.get("registration_status", "active")
        membership = membership_for_client(
            db,
            parent_gallery_id=operation.target_parent_gallery_id,
            client_id=operation.target_client_id,
        )
        if membership and previous_state.get("membership_status") is not None:
            membership.status = previous_state["membership_status"]
    audit(
        db,
        "gallery_lifecycle.cancelled",
        f"operation_id:{operation.id};actor_id:{admin_session.subject_id}",
    )
    db.commit()
    return lifecycle_operation_payload(operation)


@app.post("/admin/derived-galleries/{gallery_id}/clone", status_code=status.HTTP_201_CREATED)
def clone_derived_gallery(
    gallery_id: UUID,
    payload: CloneGalleryInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    """Cria galeria privada independente, copiando apenas referências de fotos."""
    require_admin(request)
    source = db.get(DerivedGallery, gallery_id)
    if not source or not db.get(Client, payload.client_id):
        raise HTTPException(status_code=404, detail="Galeria ou cliente não encontrado.")
    require_parent_gallery_mutable(db, source.parent_gallery_id)
    audit_key = f"derived_gallery.clone:{sha256(f'{gallery_id}:{payload.client_id}:{payload.idempotency_key}'.encode()).hexdigest()[:48]}"
    duplicate = db.scalar(select(AuditEvent).where(AuditEvent.event == audit_key))
    if duplicate:
        return {"id": duplicate.subject}
    photo_ids = set(
        db.scalars(
            select(DerivedGalleryPhoto.photo_asset_id)
            .where(DerivedGalleryPhoto.derived_gallery_id == source.id)
            .distinct()
        )
    )
    try:
        result = derive_admin_gallery(
            db,
            parent_gallery_id=source.parent_gallery_id,
            client_id=payload.client_id,
            photo_ids=photo_ids,
            name=payload.name or source.name,
        )
    except PrivateDerivationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    gallery = result.gallery
    audit(db, audit_key, str(gallery.id))
    audit(db, "derived_gallery.cloned", str(gallery.id))
    db.commit()
    return {"id": str(gallery.id)}


@app.post("/admin/clients/{client_id}/phone")
def change_client_phone(
    client_id: UUID, payload: PhoneChangeInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    require_admin(request)
    client = db.get(Client, client_id)
    phone = normalize_e164(payload.phone_e164)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    challenge = consume_challenge(db, payload.challenge_id, "client_otp", payload.code)
    if challenge.subject != phone:
        minimize_client_challenge_pii(db, challenge)
        db.commit()
        raise neutral_error()
    try:
        change_verified_phone(db, client, phone)
        db.flush()
    except (ClientIdentityConflict, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Este WhatsApp já pertence a outra cliente."
        ) from exc
    audit(db, "client.phone_changed", str(client_id))
    minimize_client_challenge_pii(db, challenge)
    db.commit()
    return {"id": str(client_id)}


@app.get("/admin/parent-galleries/{parent_gallery_id}/clients")
def parent_gallery_clients(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id)
    registrations = list(
        db.scalars(
            select(ParentGalleryRegistration).where(
                ParentGalleryRegistration.parent_gallery_id == parent_gallery_id
            )
        )
    )
    galleries = list(
        db.scalars(
            select(DerivedGallery).where(DerivedGallery.parent_gallery_id == parent_gallery_id)
        )
    )
    memberships = list(
        db.scalars(
            select(DerivedGalleryMembership).where(
                DerivedGalleryMembership.parent_gallery_id == parent_gallery_id
            )
        )
    )
    all_memberships_by_client = {item.client_id: item for item in memberships}
    memberships_by_client = {
        item.client_id: item
        for item in memberships
        if item.status in {"active", "blocked"}
    }
    galleries_by_id = {item.id: item for item in galleries}
    legacy_gallery_client_ids = {
        item.client_id
        for item in galleries
        if item.client_id not in all_memberships_by_client
    }
    client_ids = (
        {item.client_id for item in registrations}
        | legacy_gallery_client_ids
        | set(memberships_by_client)
    )
    if not client_ids:
        return {"parent_gallery_id": str(parent_gallery_id), "clients": []}
    clients_by_id = {
        item.id: item for item in db.scalars(select(Client).where(Client.id.in_(client_ids)))
    }
    phone_verification_by_client = {
        client_id: verified_at is not None
        for client_id, verified_at in db.execute(
            select(ClientPhone.client_id, ClientPhone.verified_at).where(
                ClientPhone.client_id.in_(client_ids),
                ClientPhone.active,
            )
        )
    }
    registrations_by_client = {item.client_id: item for item in registrations}
    galleries_by_client = {
        client_id: galleries_by_id[membership.derived_gallery_id]
        for client_id, membership in memberships_by_client.items()
        if membership.derived_gallery_id in galleries_by_id
    }
    for gallery in galleries:
        if gallery.client_id not in all_memberships_by_client:
            galleries_by_client.setdefault(gallery.client_id, gallery)
    available_by_gallery = dict(
        db.execute(
            select(
                DerivedGallery.id,
                func.count(func.distinct(DerivedGalleryPhoto.photo_asset_id)),
            )
            .join(
                DerivedGalleryPhoto,
                DerivedGalleryPhoto.derived_gallery_id == DerivedGallery.id,
            )
            .where(DerivedGallery.parent_gallery_id == parent_gallery_id)
            .group_by(DerivedGallery.id)
        ).all()
    )
    available_by_client = {
        client_id: int(available_by_gallery.get(membership.derived_gallery_id, 0))
        for client_id, membership in memberships_by_client.items()
    }
    for gallery in galleries:
        if gallery.client_id not in all_memberships_by_client:
            available_by_client.setdefault(
                gallery.client_id, int(available_by_gallery.get(gallery.id, 0))
            )
    selected_by_client = dict(
        db.execute(
            select(
                PhotoSelection.client_id,
                func.count(func.distinct(PhotoSelection.photo_asset_id)),
            )
            .join(
                DerivedGallery,
                DerivedGallery.id == PhotoSelection.derived_gallery_id,
            )
            .where(DerivedGallery.parent_gallery_id == parent_gallery_id)
            .group_by(PhotoSelection.client_id)
        ).all()
    )
    purchased_by_client = dict(
        db.execute(
            select(
                SaleOrder.client_id,
                func.count(func.distinct(SaleOrderItem.photo_asset_id_snapshot)),
            )
            .join(SaleOrderItem, SaleOrderItem.sale_order_id == SaleOrder.id)
            .where(
                SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
                SaleOrder.payment_status == "confirmed",
            )
            .group_by(SaleOrder.client_id)
        ).all()
    )
    order_statuses_by_client: dict[UUID, set[str]] = defaultdict(set)
    for order_client_id, payment_status in db.execute(
        select(SaleOrder.client_id, SaleOrder.payment_status)
        .where(SaleOrder.parent_gallery_id_snapshot == parent_gallery_id)
        .distinct()
    ):
        order_statuses_by_client[order_client_id].add(payment_status)
    pending_review_clients = set(
        db.scalars(
            select(PaymentCommunication.client_id)
            .join(SaleOrder, SaleOrder.id == PaymentCommunication.sale_order_id)
            .where(
                SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
                PaymentCommunication.status == "pending_review",
            )
            .distinct()
        )
    )
    rows = []
    for client_id in client_ids:
        client = clients_by_id.get(client_id)
        gallery = galleries_by_client.get(client_id)
        membership = memberships_by_client.get(client_id)
        registration = registrations_by_client.get(client_id)
        selected_count = int(selected_by_client.get(client_id, 0))
        phone_verified = phone_verification_by_client.get(client_id, True)
        if registration and (registration.status != "active" or not phone_verified):
            gallery_status = "pending_registration"
        elif (membership and membership.status == "blocked") or (
            gallery and not gallery.access_enabled
        ):
            gallery_status = "blocked"
        elif gallery and gallery.selection_expires_at and expired(gallery.selection_expires_at):
            gallery_status = "expired"
        elif selected_count == 0:
            gallery_status = "no_selection"
        else:
            gallery_status = "active"
        order_statuses = order_statuses_by_client.get(client_id, set())
        if client_id in pending_review_clients:
            commercial_status = "pending_review"
        elif "pending" in order_statuses:
            commercial_status = "awaiting_payment"
        elif "confirmed" in order_statuses:
            commercial_status = "paid"
        elif gallery_status == "expired":
            commercial_status = "overdue"
        elif "cancelled" in order_statuses:
            commercial_status = "cancelled"
        else:
            commercial_status = "no_order"
        rows.append(
            {
                "client_id": str(client_id),
                "name": client.full_name if client else "Cliente",
                "phone": client.phone_e164 if client else "",
                "phone_verified": phone_verified,
                "registration_status": registration.status if registration else None,
                "membership_status": membership.status if membership else None,
                "derived_gallery_id": str(gallery.id) if gallery else None,
                "available_count": int(available_by_client.get(client_id, 0)),
                "selected_count": selected_count,
                "purchased_count": int(purchased_by_client.get(client_id, 0)),
                "gallery_status": gallery_status,
                "commercial_status": commercial_status,
            }
        )
    return {
        "parent_gallery_id": str(parent_gallery_id),
        "clients": sorted(rows, key=lambda item: (item["name"].casefold(), item["client_id"])),
    }


@app.put("/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}")
def link_admin_client_to_parent_gallery(
    parent_gallery_id: UUID,
    client_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    parent = require_parent_gallery_mutable(db, parent_gallery_id)
    if not parent.active or not db.get(Client, client_id):
        raise HTTPException(status_code=404, detail="Galeria ou cliente não encontrado.")
    registration = link_client_to_parent(
        db,
        parent_gallery_id=parent.id,
        client_id=client_id,
        status="active",
    )
    audit(db, "parent_gallery.client_linked", str(registration.id))
    db.commit()
    return {
        "registration_id": str(registration.id),
        "parent_gallery_id": str(parent.id),
        "client_id": str(client_id),
        "status": registration.status,
        "private_gallery_id": None,
    }


@app.delete(
    "/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}",
    status_code=status.HTTP_202_ACCEPTED,
)
def unlink_admin_client_from_parent_gallery(
    parent_gallery_id: UUID,
    client_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    """Agenda uma desvinculação restrita ao par, de forma idempotente."""

    admin_session = current_session(request, Role.ADMIN)
    idempotency_key = request.headers.get("Idempotency-Key", "").strip()
    if not idempotency_key or len(idempotency_key) > 128:
        raise HTTPException(
            status_code=422,
            detail="Informe uma chave de idempotência válida.",
        )
    existing = db.scalar(
        select(GalleryLifecycleOperation).where(
            GalleryLifecycleOperation.idempotency_key == idempotency_key
        )
    )
    if existing:
        if (
            existing.operation_type != "unlink_client"
            or existing.target_parent_gallery_id != parent_gallery_id
            or existing.target_client_id != client_id
        ):
            raise HTTPException(
                status_code=409,
                detail="A chave de idempotência já pertence a outra operação.",
            )
        return lifecycle_operation_payload(existing)

    parent = db.get(ParentGallery, parent_gallery_id)
    client = db.get(Client, client_id)
    if not parent or parent.lifecycle_status != "active" or not client:
        raise HTTPException(status_code=404, detail="Galeria pública ou cliente não encontrado.")
    registration = db.scalar(
        select(ParentGalleryRegistration)
        .where(
            ParentGalleryRegistration.parent_gallery_id == parent.id,
            ParentGalleryRegistration.client_id == client.id,
        )
        .with_for_update()
    )
    if not registration:
        raise HTTPException(status_code=404, detail="Vínculo de cliente não encontrado.")
    conflicting = db.scalar(
        select(GalleryLifecycleOperation.id).where(
            GalleryLifecycleOperation.operation_type == "unlink_client",
            GalleryLifecycleOperation.target_parent_gallery_id == parent.id,
            GalleryLifecycleOperation.target_client_id == client.id,
            GalleryLifecycleOperation.status.not_in(("completed", "cancelled")),
        )
    )
    if conflicting:
        raise HTTPException(
            status_code=409, detail="A desvinculação deste cliente já está em andamento."
        )
    membership = membership_for_client(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        lock=True,
    )
    operation = GalleryLifecycleOperation(
        operation_type="unlink_client",
        target_parent_gallery_id=parent.id,
        target_client_id=client.id,
        actor_admin_id=admin_session.subject_id,
        idempotency_key=idempotency_key,
        manifest={
            "inventory": client_unlink_inventory(
                db, parent_gallery_id=parent.id, client_id=client.id
            ),
            "operational_storage": {"sources": [], "derivatives": []},
            "previous_state": {
                "registration_status": registration.status,
                "membership_status": membership.status if membership else None,
            },
        },
    )
    registration.status = "unlinking"
    db.add(operation)
    db.flush()
    audit(db, "parent_gallery.client_unlink_queued", str(operation.id))
    db.commit()
    return lifecycle_operation_payload(operation)


@app.get("/admin/derived-galleries/{gallery_id}/selection")
def selection_detail(
    gallery_id: UUID,
    request: Request,
    client_id: UUID | None = None,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    selected_client_id = client_id or gallery.client_id
    membership = membership_for_client(
        db,
        parent_gallery_id=gallery.parent_gallery_id,
        client_id=selected_client_id,
    )
    if membership and membership.derived_gallery_id != gallery.id:
        raise HTTPException(status_code=404, detail="Cliente não pertence a esta galeria.")
    if not membership and selected_client_id != gallery.client_id:
        raise HTTPException(status_code=404, detail="Cliente não pertence a esta galeria.")
    owner = db.get(Client, selected_client_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    selected = list(
        db.scalars(
            select(PhotoSelection).where(
                PhotoSelection.derived_gallery_id == gallery_id,
                PhotoSelection.client_id == selected_client_id,
            )
        )
    )
    orders = list(
        db.scalars(
            select(SaleOrder).where(
                SaleOrder.derived_gallery_id == gallery_id,
                SaleOrder.client_id == selected_client_id,
            )
        )
    )
    confirmed_items = list(
        db.scalars(
            select(SaleOrderItem)
            .join(SaleOrder)
            .where(
                SaleOrder.derived_gallery_id == gallery_id,
                SaleOrder.client_id == selected_client_id,
                SaleOrder.payment_status == "confirmed",
            )
        )
    )
    sales_by_photo: dict[UUID, int] = {}
    for item in confirmed_items:
        sales_by_photo[item.photo_asset_id] = sales_by_photo.get(item.photo_asset_id, 0) + 1
    photos = []
    for selection in selected:
        photo = db.get(PhotoAsset, selection.photo_asset_id)
        if photo:
            photos.append(
                {
                    "id": str(photo.id),
                    "filename": photo.filename,
                    "preview_url": f"/admin/photo-assets/{photo.id}/preview",
                    "sales_count": sales_by_photo.get(photo.id, 0),
                }
            )
    return {
        "gallery": {
            "id": str(gallery.id),
            "name": gallery.name,
            "selection_expires_at": gallery.selection_expires_at.isoformat()
            if gallery.selection_expires_at
            else None,
        },
        "client": {"id": str(owner.id), "name": owner.full_name, "phone": owner.phone_e164}
        if owner
        else None,
        "selection_count": len(photos),
        "payment_status": next((order.payment_status for order in orders), "pending"),
        "photos": photos,
    }


@app.get("/admin/derived-galleries/{gallery_id}/selection/export.{format}")
def export_selection(
    gallery_id: UUID,
    format: str,
    request: Request,
    client_id: UUID | None = None,
    db: Session = Depends(db_session),
) -> PlainTextResponse:
    require_admin(request)
    if format not in {"txt", "csv"}:
        raise HTTPException(status_code=404, detail="Formato não suportado.")
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    selected_client_id = client_id or gallery.client_id
    membership = membership_for_client(
        db,
        parent_gallery_id=gallery.parent_gallery_id,
        client_id=selected_client_id,
    )
    if (membership and membership.derived_gallery_id != gallery.id) or (
        not membership and selected_client_id != gallery.client_id
    ):
        raise HTTPException(status_code=404, detail="Cliente não pertence a esta galeria.")
    rows = []
    for selection in db.scalars(
        select(PhotoSelection).where(
            PhotoSelection.derived_gallery_id == gallery_id,
            PhotoSelection.client_id == selected_client_id,
        )
    ):
        photo = db.get(PhotoAsset, selection.photo_asset_id)
        if photo:
            rows.append((str(photo.id), photo.filename))
    separator = "\t" if format == "txt" else ","
    content = "".join(f"{identifier}{separator}{filename}\n" for identifier, filename in rows)
    audit(db, "selection.exported", str(gallery_id))
    db.commit()
    return PlainTextResponse(
        content,
        media_type="text/plain" if format == "txt" else "text/csv",
        headers={"Content-Disposition": f'attachment; filename="selecao.{format}"'},
    )


@app.post("/admin/parent-galleries/{parent_gallery_id}/photos", status_code=status.HTTP_201_CREATED)
def register_photo_asset(
    parent_gallery_id: UUID,
    payload: PhotoAssetInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Cadastro direto descontinuado. Selecione uma pasta em preparação.",
    )


@app.put("/admin/photo-assets/{photo_id}/source", status_code=status.HTTP_202_ACCEPTED)
async def import_photo_source(
    photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    """Recebe somente JPEG para processamento local, nunca para entrega web direta."""
    require_admin(request)
    if not (request.headers.get("content-type") or "").lower().startswith("image/jpeg"):
        raise HTTPException(status_code=415, detail="Envie uma imagem JPEG.")
    body = await request.body()
    if not body or len(body) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="A imagem excede o limite permitido.")
    try:
        with Image.open(BytesIO(body)) as image:
            if image.format != "JPEG":
                raise ValueError
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Imagem JPEG inválida.") from exc
    photo = db.get(PhotoAsset, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    folder = db.get(PhotoFolder, photo.folder_id)
    if not folder or folder.parent_gallery_id != photo.parent_gallery_id:
        raise HTTPException(status_code=409, detail="A foto não possui uma pasta válida.")
    require_parent_gallery_mutable(db, photo.parent_gallery_id)
    accepts_upload = (
        folder.purpose == "content" and folder.status in {"preparing", "released"}
    ) or (folder.purpose == "cover_assets" and folder.status == "preparing")
    if not accepts_upload:
        raise HTTPException(status_code=409, detail="A pasta não aceita novas fotos.")
    destination = safe_source_path(photo)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(body)
    enqueue_derivatives(db, photo)
    audit(db, "photo_asset.imported", str(photo.id))
    db.commit()
    return {"status": "queued"}


@app.get("/admin/photo-assets/{photo_id}/media-status")
def photo_media_status(
    photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    """Estado de processamento usado pela interface administrativa."""
    require_admin(request)
    if not db.get(PhotoAsset, photo_id):
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    job = db.scalar(select(MediaJob).where(MediaJob.photo_asset_id == photo_id))
    if not job:
        return {"status": "not_imported"}
    return {"status": job.status}


@app.get("/admin/photo-assets/{photo_id}/preview")
def admin_photo_preview(
    photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    """Prévia sem marca para conferência administrativa; nunca é o original."""
    require_admin(request)
    photo = db.get(PhotoAsset, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    derivative = db.scalar(
        select(MediaDerivative).where(
            MediaDerivative.photo_asset_id == photo_id,
            MediaDerivative.variant == "admin_preview",
            MediaDerivative.status == "ready",
        )
    )
    if not derivative:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    try:
        path = safe_derivative_path(derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Prévia indisponível.") from exc
    audit(db, "media_preview.admin_viewed", str(photo_id))
    db.commit()
    return protected_preview_response(path, f"conferencia-{photo.filename}")


@app.get("/admin/photo-assets/{photo_id}/watermarked-preview")
def admin_watermarked_photo_preview(
    photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    """Prévia marcada para organizar pastas sem expor o arquivo de origem."""
    require_admin(request)
    photo = db.get(PhotoAsset, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    derivative = db.scalar(
        select(MediaDerivative).where(
            MediaDerivative.photo_asset_id == photo_id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
    )
    if not derivative:
        raise HTTPException(status_code=404, detail="Prévia com marca d’água indisponível.")
    try:
        path = safe_derivative_path(derivative)
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail="Prévia com marca d’água indisponível."
        ) from exc
    audit(db, "media_preview.admin_watermarked_viewed", str(photo_id))
    db.commit()
    return protected_preview_response(path, f"amostra-{photo.filename}")


@app.get("/admin/purchases")
def admin_purchase_history(
    request: Request,
    parent_gallery_id: UUID | None = None,
    client_id: UUID | None = None,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    """Histórico confirmado para conferência exclusiva do fotógrafo."""
    require_admin(request)
    query = select(SaleOrder).where(SaleOrder.payment_status == "confirmed")
    if parent_gallery_id:
        query = query.where(SaleOrder.parent_gallery_id_snapshot == parent_gallery_id)
    if client_id:
        query = query.where(SaleOrder.client_id == client_id)
    orders = db.scalars(query.order_by(SaleOrder.confirmed_at.desc(), SaleOrder.created_at.desc()))
    result: list[dict[str, object]] = []
    for order in orders:
        client = db.get(Client, order.client_id)
        gallery = (
            db.get(DerivedGallery, order.derived_gallery_id) if order.derived_gallery_id else None
        )
        items = db.scalars(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id))
        result.append(
            {
                "id": str(order.id),
                "client_name": order.client_name_snapshot
                or (client.full_name if client else "Cliente removido"),
                "gallery_name": order.derived_gallery_name_snapshot,
                "parent_gallery_name": order.parent_gallery_name_snapshot,
                "gallery_status_label": "Galeria ativa" if gallery else "Galeria removida",
                "gallery_removed": gallery is None,
                "total_cents": order.total_cents,
                "items": [
                    {
                        "photo_id": str(item.photo_asset_id_snapshot),
                        "name": item.filename_snapshot,
                        "preview_url": f"/admin/photo-assets/{item.photo_asset_id}/preview"
                        if item.photo_asset_id
                        else None,
                        "operational_media_available": item.photo_asset_id is not None,
                    }
                    for item in items
                ],
            }
        )
    return {
        "orders": result,
        "totals": {
            "orders": len(result),
            "amount_cents": sum(item["total_cents"] for item in result),
        },
    }


def _validated_price_tiers(tiers: list[PriceTierInput]) -> list[PriceTier]:
    try:
        return validate_tiers(
            [
                PriceTier(
                    tier.minimum_quantity,
                    tier.maximum_quantity,
                    tier.unit_price_cents,
                )
                for tier in tiers
            ]
        )
    except PricingRuleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _pricing_preset_payload(
    db: Session, preset: ProgressivePricingPreset
) -> dict[str, object]:
    tiers = list(
        db.scalars(
            select(ProgressivePricingTier)
            .where(ProgressivePricingTier.preset_id == preset.id)
            .order_by(ProgressivePricingTier.minimum_quantity)
        )
    )
    return {
        "id": str(preset.id),
        "code": preset.code,
        "name": preset.name,
        "label": f"{preset.code} — {preset.name}",
        "version": preset.version,
        "active": preset.active,
        "tiers": [
            {
                "minimum_quantity": tier.minimum_quantity,
                "maximum_quantity": tier.maximum_quantity,
                "unit_price_cents": tier.unit_price_cents,
            }
            for tier in tiers
        ],
        "created_at": preset.created_at.isoformat(),
        "updated_at": preset.updated_at.isoformat(),
    }


def _replace_pricing_preset_tiers(
    db: Session,
    preset: ProgressivePricingPreset,
    tiers: list[PriceTier],
) -> None:
    db.execute(
        delete(ProgressivePricingTier).where(
            ProgressivePricingTier.preset_id == preset.id
        )
    )
    db.add_all(
        [
            ProgressivePricingTier(
                preset_id=preset.id,
                minimum_quantity=tier.minimum_quantity,
                maximum_quantity=tier.maximum_quantity,
                unit_price_cents=tier.unit_price_cents,
            )
            for tier in tiers
        ]
    )


@app.get("/admin/pricing-presets")
def list_progressive_pricing_presets(
    request: Request,
    include_inactive: bool = Query(default=False),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    statement = select(ProgressivePricingPreset)
    if not include_inactive:
        statement = statement.where(ProgressivePricingPreset.active.is_(True))
    presets = list(
        db.scalars(statement.order_by(ProgressivePricingPreset.code)).all()
    )
    return {"presets": [_pricing_preset_payload(db, preset) for preset in presets]}


@app.post("/admin/pricing-presets", status_code=status.HTTP_201_CREATED)
def create_progressive_pricing_preset(
    payload: ProgressivePricingPresetInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    tiers = _validated_price_tiers(payload.tiers)
    preset = ProgressivePricingPreset(
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
    )
    try:
        db.add(preset)
        db.flush()
        _replace_pricing_preset_tiers(db, preset, tiers)
        audit(db, "pricing.preset_created", str(preset.id))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Já existe uma tabela com este código."
        ) from exc
    db.refresh(preset)
    return _pricing_preset_payload(db, preset)


def _pricing_preset_or_404(
    db: Session, preset_id: UUID
) -> ProgressivePricingPreset:
    preset = db.get(ProgressivePricingPreset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Tabela de preços não encontrada.")
    return preset


@app.put("/admin/pricing-presets/{preset_id}")
def update_progressive_pricing_preset(
    preset_id: UUID,
    payload: ProgressivePricingPresetInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    tiers = _validated_price_tiers(payload.tiers)
    preset = _pricing_preset_or_404(db, preset_id)
    preset.code = payload.code.strip().upper()
    preset.name = payload.name.strip()
    preset.version += 1
    preset.updated_at = now()
    _replace_pricing_preset_tiers(db, preset, tiers)
    audit(db, "pricing.preset_updated", str(preset.id))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Já existe uma tabela com este código."
        ) from exc
    db.refresh(preset)
    return _pricing_preset_payload(db, preset)


@app.delete("/admin/pricing-presets/{preset_id}")
def deactivate_progressive_pricing_preset(
    preset_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    preset = _pricing_preset_or_404(db, preset_id)
    preset.active = False
    preset.updated_at = now()
    audit(db, "pricing.preset_deactivated", str(preset.id))
    db.commit()
    db.refresh(preset)
    return _pricing_preset_payload(db, preset)


@app.post("/admin/pricing-presets/{preset_id}/activate")
def activate_progressive_pricing_preset(
    preset_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    preset = _pricing_preset_or_404(db, preset_id)
    if not preset.active:
        preset.active = True
        preset.updated_at = now()
        audit(db, "pricing.preset_activated", str(preset.id))
        db.commit()
        db.refresh(preset)
    return _pricing_preset_payload(db, preset)


@app.get("/admin/pricing-presets/{preset_id}/quote")
def simulate_progressive_pricing_preset(
    preset_id: UUID,
    request: Request,
    quantity: int = Query(ge=1, le=10_000),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    preset = _pricing_preset_or_404(db, preset_id)
    stored_tiers = list(
        db.scalars(
            select(ProgressivePricingTier)
            .where(ProgressivePricingTier.preset_id == preset.id)
            .order_by(ProgressivePricingTier.minimum_quantity)
        )
    )
    result = progressive_quote(
        quantity,
        [
            PriceTier(
                tier.minimum_quantity,
                tier.maximum_quantity,
                tier.unit_price_cents,
            )
            for tier in stored_tiers
        ],
    )
    return {
        "preset": {
            "id": str(preset.id),
            "code": preset.code,
            "name": preset.name,
            "label": f"{preset.code} — {preset.name}",
            "version": preset.version,
        },
        "quantity": result.quantity,
        "parcels": [
            {
                "minimum_quantity": parcel.minimum_quantity,
                "maximum_quantity": parcel.maximum_quantity,
                "quantity": parcel.quantity,
                "unit_price_cents": parcel.unit_price_cents,
                "subtotal_cents": parcel.subtotal_cents,
            }
            for parcel in result.parcels
        ],
        "base_total_cents": result.base_total_cents,
        "savings_cents": result.savings_cents,
        "total_cents": result.total_cents,
    }


def pricing_payload(db: Session, parent_gallery_id: UUID) -> dict[str, object]:
    gallery = _parent_gallery_or_404(db, parent_gallery_id)
    rules = list(
        db.scalars(
            select(PriceRule)
            .where(PriceRule.parent_gallery_id == parent_gallery_id)
            .order_by(PriceRule.minimum_quantity)
        )
    )
    settings = db.scalar(
        select(PixCheckoutSettings).where(
            PixCheckoutSettings.parent_gallery_id == parent_gallery_id
        )
    )
    qr_data_url: str | None = None
    if settings and settings.copy_paste and not settings.review_required:
        try:
            qr_data_url = pix_qr_data_url(settings.copy_paste)
        except PixCodeError:
            # Configuração anterior inválida permanece visível para correção, sem gerar QR.
            pass
    return {
        "pricing_mode": gallery.pricing_mode,
        "fixed_unit_price_cents": gallery.fixed_unit_price_cents,
        "progressive_pricing_preset_id": (
            str(gallery.progressive_pricing_preset_id)
            if gallery.progressive_pricing_preset_id
            else None
        ),
        "pricing_snapshot": gallery.pricing_snapshot,
        "pricing_review_required": gallery.pricing_review_required,
        "tiers": [
            {
                "minimum_quantity": rule.minimum_quantity,
                "maximum_quantity": rule.maximum_quantity,
                "unit_price_cents": rule.unit_price_cents,
            }
            for rule in rules
        ],
        "pix": {
            "copy_paste": (
                settings.pix_key
                if settings and settings.input_type in {"cpf", "phone", "email"}
                else settings.copy_paste if settings else None
            ),
            "input_type": settings.input_type if settings else None,
            "receiver_name": settings.receiver_name if settings else None,
            "receiver_city": settings.receiver_city if settings else None,
            "qr_code_payload": None,
            "qr_png_data_url": qr_data_url,
            "review_required": settings.review_required if settings else False,
            "instructions": settings.instructions if settings else None,
        },
    }


def save_parent_pricing(
    db: Session, parent_gallery_id: UUID, payload: GalleryPricingInput
) -> list[PriceTier]:
    gallery = require_parent_gallery_mutable(db, parent_gallery_id)
    if (
        gallery.pricing_mode == "legacy_volume"
        and payload.pricing_mode is not None
        and not payload.confirm_legacy_conversion
    ):
        raise HTTPException(
            status_code=409,
            detail="Confirme a conversão do preço por volume legado antes de salvar.",
        )

    preset: ProgressivePricingPreset | None = None
    if payload.pricing_mode == "fixed":
        if payload.fixed_unit_price_cents is None or payload.progressive_pricing_preset_id:
            raise HTTPException(
                status_code=422,
                detail="Preço fixo exige somente o valor unitário em centavos.",
            )
        tiers = [PriceTier(1, None, payload.fixed_unit_price_cents)]
        pricing_snapshot: dict[str, object] = {
            "mode": "fixed",
            "unit_price_cents": payload.fixed_unit_price_cents,
        }
        pricing_mode = "fixed"
        review_required = False
    elif payload.pricing_mode == "progressive":
        if not payload.progressive_pricing_preset_id or payload.fixed_unit_price_cents is not None:
            raise HTTPException(
                status_code=422,
                detail="Preço progressivo exige somente uma tabela global ativa.",
            )
        preset = _pricing_preset_or_404(db, payload.progressive_pricing_preset_id)
        if not preset.active:
            raise HTTPException(
                status_code=422, detail="A tabela de preços escolhida está desativada."
            )
        stored_tiers = list(
            db.scalars(
                select(ProgressivePricingTier)
                .where(ProgressivePricingTier.preset_id == preset.id)
                .order_by(ProgressivePricingTier.minimum_quantity)
            )
        )
        tiers = validate_tiers(
            [
                PriceTier(
                    tier.minimum_quantity,
                    tier.maximum_quantity,
                    tier.unit_price_cents,
                )
                for tier in stored_tiers
            ]
        )
        pricing_snapshot = {
            "mode": "progressive",
            "preset_id": str(preset.id),
            "preset_code": preset.code,
            "preset_name": preset.name,
            "preset_version": preset.version,
            "tiers": [
                {
                    "minimum_quantity": tier.minimum_quantity,
                    "maximum_quantity": tier.maximum_quantity,
                    "unit_price_cents": tier.unit_price_cents,
                }
                for tier in tiers
            ],
        }
        pricing_mode = "progressive"
        review_required = False
    elif payload.tiers:
        # Janela de compatibilidade do contrato anterior.
        tiers = _validated_price_tiers(payload.tiers)
        if len(tiers) == 1 and tiers[0].minimum_quantity == 1:
            pricing_mode = "fixed"
            pricing_snapshot = {
                "mode": "fixed",
                "unit_price_cents": tiers[0].unit_price_cents,
                "migrated_from": "legacy_api_single_tier",
            }
            review_required = False
        else:
            pricing_mode = "legacy_volume"
            pricing_snapshot = {
                "mode": "legacy_volume",
                "tiers": [
                    {
                        "minimum_quantity": tier.minimum_quantity,
                        "maximum_quantity": tier.maximum_quantity,
                        "unit_price_cents": tier.unit_price_cents,
                    }
                    for tier in tiers
                ],
            }
            review_required = True
    else:
        raise HTTPException(
            status_code=422,
            detail="Escolha preço fixo ou uma tabela progressiva.",
        )

    gallery.pricing_mode = pricing_mode
    gallery.fixed_unit_price_cents = (
        tiers[0].unit_price_cents if pricing_mode == "fixed" else None
    )
    gallery.progressive_pricing_preset_id = preset.id if preset else None
    gallery.pricing_snapshot = pricing_snapshot
    gallery.pricing_review_required = review_required
    db.execute(delete(PriceRule).where(PriceRule.parent_gallery_id == parent_gallery_id))
    db.add_all(
        [
            PriceRule(
                parent_gallery_id=parent_gallery_id,
                minimum_quantity=tier.minimum_quantity,
                maximum_quantity=tier.maximum_quantity,
                unit_price_cents=tier.unit_price_cents,
            )
            for tier in tiers
        ]
    )
    settings = db.scalar(
        select(PixCheckoutSettings).where(
            PixCheckoutSettings.parent_gallery_id == parent_gallery_id
        )
    )
    if not settings:
        settings = PixCheckoutSettings(parent_gallery_id=parent_gallery_id)
        db.add(settings)
    try:
        pix_configuration = normalize_pix_configuration(
            payload.pix.copy_paste,
            receiver_name=payload.pix.receiver_name,
            receiver_city=payload.pix.receiver_city,
        )
        legacy_qr_payload = normalize_pix_copy_paste(payload.pix.qr_code_payload)
    except PixCodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    copy_paste = pix_configuration.copy_paste if pix_configuration else None
    if copy_paste and legacy_qr_payload and copy_paste != legacy_qr_payload:
        raise HTTPException(
            status_code=422,
            detail="O QR informado diverge do PIX copia e cola; mantenha somente o copia e cola.",
        )
    settings.copy_paste = copy_paste or legacy_qr_payload
    settings.qr_code_payload = None
    settings.input_type = (
        pix_configuration.input_type
        if pix_configuration
        else "br_code" if legacy_qr_payload else None
    )
    settings.pix_key = (
        pix_configuration.input_value
        if pix_configuration and pix_configuration.input_type != "br_code"
        else None
    )
    settings.receiver_name = pix_configuration.receiver_name if pix_configuration else None
    settings.receiver_city = pix_configuration.receiver_city if pix_configuration else None
    settings.review_required = False
    settings.instructions = payload.pix.instructions.strip() if payload.pix.instructions else None
    return tiers


@app.get("/admin/parent-galleries/{parent_gallery_id}/pricing")
def admin_parent_gallery_pricing(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id)
    return pricing_payload(db, parent_gallery_id)


@app.put("/admin/parent-galleries/{parent_gallery_id}/pricing")
def save_admin_parent_gallery_pricing(
    parent_gallery_id: UUID,
    payload: GalleryPricingInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    require_parent_gallery_mutable(db, parent_gallery_id)
    tiers = save_parent_pricing(db, parent_gallery_id, payload)
    audit(db, "pricing.settings_updated", str(parent_gallery_id))
    db.commit()
    return {
        **pricing_payload(db, parent_gallery_id),
        "has_downward_jump": has_downward_jump(tiers),
    }


@app.get("/admin/derived-galleries/{gallery_id}/pricing")
def admin_gallery_pricing(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    return {
        **pricing_payload(db, parent.id),
        "inherited_from_parent_gallery_id": str(parent.id),
        "editable": False,
    }


@app.put("/admin/derived-galleries/{gallery_id}/pricing")
def save_admin_gallery_pricing(
    gallery_id: UUID,
    payload: GalleryPricingInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    if not db.get(DerivedGallery, gallery_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    raise HTTPException(
        status_code=409,
        detail=("Preço e PIX são herdados da Galeria pública; altere a configuração da origem."),
    )


@app.get("/admin/derived-galleries/{gallery_id}/orders")
def admin_gallery_orders(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Exibe snapshots de pedidos sem executar confirmação financeira."""
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    orders = list(
        db.scalars(
            select(SaleOrder)
            .where(SaleOrder.derived_gallery_id_snapshot == gallery_id)
            .order_by(SaleOrder.created_at.desc())
        )
    )
    if not gallery and not orders:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    return {
        "gallery": {
            "id": str(gallery_id),
            "name": gallery.name if gallery else orders[0].derived_gallery_name_snapshot,
            "status_label": "Galeria ativa" if gallery else "Galeria removida",
            "removed": gallery is None,
        },
        "totals": {
            "orders": len(orders),
            "amount_cents": sum(order.total_cents for order in orders),
        },
        "orders": [
            {
                "id": str(order.id),
                "payment_status": order.payment_status,
                "total_cents": order.total_cents,
                "client_name": order.client_name_snapshot,
                "created_at": order.created_at.isoformat(),
                "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
                "price_rule": order.price_rule_snapshot,
                "sales_message": order.sales_message_snapshot,
                "pix": {
                    "copy_paste": order.pix_copy_paste_snapshot,
                    "qr_code_payload": order.pix_qr_code_snapshot,
                    "instructions": order.pix_instructions_snapshot,
                },
                "items": [
                    {
                        "photo_id": str(item.photo_asset_id_snapshot),
                        "name": item.filename_snapshot,
                        "unit_price_cents": item.unit_price_cents,
                    }
                    for item in db.scalars(
                        select(SaleOrderItem)
                        .where(SaleOrderItem.sale_order_id == order.id)
                        .order_by(SaleOrderItem.filename_snapshot)
                    )
                ],
            }
            for order in orders
        ],
    }


@app.post("/admin/derived-galleries", status_code=status.HTTP_201_CREATED)
def create_derived_gallery(
    payload: DerivedGalleryInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    parent = db.get(ParentGallery, payload.parent_gallery_id)
    client = db.get(Client, payload.client_id)
    if not parent or not client:
        raise HTTPException(status_code=404, detail="Galeria pública ou cliente não encontrado.")
    require_parent_gallery_mutable(db, parent.id)
    requested_photo_ids = set(payload.photo_ids)
    if not requested_photo_ids:
        registration = link_client_to_parent(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
            status="active",
        )
        audit(db, "parent_gallery.client_linked_without_private", str(registration.id))
        db.commit()
        return {
            "id": None,
            "private_gallery_id": None,
            "registration_id": str(registration.id),
            "detail": "Cliente vinculado; selecione ao menos uma foto para criar a galeria privada.",
        }
    try:
        result = derive_admin_gallery(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
            photo_ids=requested_photo_ids,
            name=payload.name,
        )
    except PrivateDerivationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    gallery = result.gallery
    if result.gallery_created:
        gallery.access_enabled = payload.access_enabled
        enqueue_membership_notification(
            db,
            event_key=f"private_created:{gallery.id}",
            event_type="private_created",
            parent=parent,
            gallery=gallery,
            client=client,
        )
    active_invite = _active_gallery_capability(
        db,
        parent_gallery_id=parent.id,
        scope="private_gallery_link",
        derived_gallery_id=gallery.id,
    )
    invite_token = None
    if not active_invite:
        active_invite, invite_token = issue_gallery_capability(
            db,
            parent_gallery_id=parent.id,
            derived_gallery_id=gallery.id,
            scope="private_gallery_link",
            actor_admin_id=admin_session.subject_id,
            reconstructible=True,
        )
    audit(
        db,
        "derived_gallery.created" if result.gallery_created else "derived_gallery.reused",
        str(gallery.id),
    )
    db.commit()
    return {
        "id": str(gallery.id),
        "private_gallery_id": str(gallery.id),
        "gallery_created": result.gallery_created,
        "references_created": result.references_created,
        "invite_token": invite_token,
        "invite_already_active": invite_token is None,
    }


def _private_gallery_link_capability(
    db: Session,
    gallery: DerivedGallery,
) -> GalleryAccessCapability | None:
    return _active_gallery_capability(
        db,
        parent_gallery_id=gallery.parent_gallery_id,
        scope="private_gallery_link",
        derived_gallery_id=gallery.id,
    )


@app.get("/admin/derived-galleries/{gallery_id}/link")
def private_gallery_link_status(
    gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id)
    capability = _private_gallery_link_capability(db, gallery)
    if capability:
        token = reconstruct_gallery_capability_token(capability)
        return {
            "status": "active",
            "capability_id": str(capability.id),
            "expires_at": capability.expires_at.isoformat()
            if capability.expires_at
            else None,
            "secret_available": True,
            "access_token": token,
            "link": _gallery_capability_link(request, token),
        }
    legacy = db.scalar(
        select(GalleryAccessCapability).where(
            GalleryAccessCapability.derived_gallery_id == gallery.id,
            GalleryAccessCapability.scope.in_(("private_invite", "private_client_invite")),
            GalleryAccessCapability.status == "active",
        )
    )
    return {
        "status": "legacy_unrecoverable" if legacy else "unavailable",
        "capability_id": str(legacy.id) if legacy else None,
        "expires_at": legacy.expires_at.isoformat()
        if legacy and legacy.expires_at
        else None,
        "secret_available": False,
        "access_token": None,
        "link": None,
    }


@app.post(
    "/admin/derived-galleries/{gallery_id}/link",
    status_code=status.HTTP_201_CREATED,
)
def issue_private_gallery_link(
    gallery_id: UUID,
    payload: GalleryCapabilityInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    gallery = require_derived_gallery_mutable(db, gallery_id)
    if _private_gallery_link_capability(db, gallery):
        raise HTTPException(status_code=409, detail="Já existe um link privado ativo.")
    capability, token = issue_gallery_capability(
        db,
        parent_gallery_id=gallery.parent_gallery_id,
        derived_gallery_id=gallery.id,
        scope="private_gallery_link",
        expires_at=_validated_capability_expiry(payload.expires_at),
        actor_admin_id=admin_session.subject_id,
        reconstructible=True,
    )
    audit(db, "gallery_capability.private_link_issued", str(capability.id))
    db.commit()
    return _capability_secret_response(request, capability, token)


@app.post("/admin/derived-galleries/{gallery_id}/link/rotate")
def rotate_private_gallery_link(
    gallery_id: UUID,
    payload: GalleryCapabilityInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    gallery = require_derived_gallery_mutable(db, gallery_id)
    capability = _private_gallery_link_capability(db, gallery)
    if capability:
        replacement, token = rotate_gallery_capability(
            db,
            capability,
            actor_admin_id=admin_session.subject_id,
            reconstructible=True,
        )
    else:
        legacy_capabilities = list(
            db.scalars(
                select(GalleryAccessCapability).where(
                    GalleryAccessCapability.derived_gallery_id == gallery.id,
                    GalleryAccessCapability.scope.in_(
                        ("private_invite", "private_client_invite")
                    ),
                    GalleryAccessCapability.status == "active",
                )
            )
        )
        for legacy in legacy_capabilities:
            revoke_gallery_capability(legacy)
        replacement, token = issue_gallery_capability(
            db,
            parent_gallery_id=gallery.parent_gallery_id,
            derived_gallery_id=gallery.id,
            scope="private_gallery_link",
            actor_admin_id=admin_session.subject_id,
            reconstructible=True,
        )
    if payload.expires_at is not None:
        replacement.expires_at = _validated_capability_expiry(payload.expires_at)
    audit(db, "gallery_capability.private_link_rotated", str(replacement.id))
    db.commit()
    return _capability_secret_response(request, replacement, token)


@app.delete(
    "/admin/derived-galleries/{gallery_id}/link",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_private_gallery_link(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    capability = _private_gallery_link_capability(db, gallery)
    if capability:
        revoke_gallery_capability(capability)
        audit(db, "gallery_capability.private_link_revoked", str(capability.id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Compatibilidade temporária com a rota administrativa anterior.
@app.post("/admin/derived-galleries/{gallery_id}/invite/rotate")
def rotate_private_gallery_invite(
    gallery_id: UUID,
    payload: GalleryCapabilityInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    return rotate_private_gallery_link(gallery_id, payload, request, db)


@app.delete(
    "/admin/derived-galleries/{gallery_id}/invite",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_private_gallery_invite(
    gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> Response:
    return revoke_private_gallery_link(gallery_id, request, db)


def _private_member_payload(
    db: Session,
    membership,
    *,
    client: Client | None = None,
    selected_count: int = 0,
    purchased_count: int = 0,
    order_count: int = 0,
    confirmed_total_cents: int = 0,
    payment_status: str = "none",
) -> dict[str, object]:
    client = client or db.get(Client, membership.client_id)
    return {
        "membership_id": str(membership.id),
        "client_id": str(membership.client_id),
        "client_name": client.full_name if client else "Cliente indisponível",
        "phone_e164": client.phone_e164 if client else None,
        "status": membership.status,
        "blocked_at": membership.blocked_at.isoformat()
        if membership.blocked_at
        else None,
        "unlinked_at": membership.unlinked_at.isoformat()
        if membership.unlinked_at
        else None,
        "created_at": membership.created_at.isoformat(),
        "selected_count": selected_count,
        "purchased_count": purchased_count,
        "order_count": order_count,
        "confirmed_total_cents": confirmed_total_cents,
        "payment_status": payment_status,
    }


def _membership_in_gallery_or_404(
    db: Session,
    *,
    gallery: DerivedGallery,
    client_id: UUID,
):
    membership = membership_for_client(
        db,
        parent_gallery_id=gallery.parent_gallery_id,
        client_id=client_id,
        lock=True,
    )
    if not membership or membership.derived_gallery_id != gallery.id:
        raise HTTPException(status_code=404, detail="Membro não encontrado nesta galeria.")
    return membership


@app.get("/admin/derived-galleries/{gallery_id}/members")
def private_gallery_members(
    gallery_id: UUID,
    request: Request,
    status_filter: str | None = Query(
        default=None, alias="status", pattern="^(active|blocked|unlinked)$"
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    selected_counts = (
        select(
            PhotoSelection.client_id.label("client_id"),
            func.count(func.distinct(PhotoSelection.photo_asset_id)).label("selected_count"),
        )
        .where(PhotoSelection.derived_gallery_id == gallery.id)
        .group_by(PhotoSelection.client_id)
        .subquery()
    )
    order_counts = (
        select(
            SaleOrder.client_id.label("client_id"),
            func.count(SaleOrder.id).label("order_count"),
            func.coalesce(
                func.sum(
                    case(
                        (SaleOrder.payment_status == "confirmed", SaleOrder.total_cents),
                        else_=0,
                    )
                ),
                0,
            ).label("confirmed_total_cents"),
            func.max(
                case((SaleOrder.payment_status == "confirmed", 2), (SaleOrder.payment_status == "pending", 1), else_=0)
            ).label("payment_rank"),
        )
        .where(SaleOrder.derived_gallery_id_snapshot == gallery.id)
        .group_by(SaleOrder.client_id)
        .subquery()
    )
    purchased_counts = (
        select(
            SaleOrder.client_id.label("client_id"),
            func.count(func.distinct(SaleOrderItem.photo_asset_id_snapshot)).label(
                "purchased_count"
            ),
        )
        .join(SaleOrderItem, SaleOrderItem.sale_order_id == SaleOrder.id)
        .where(
            SaleOrder.derived_gallery_id_snapshot == gallery.id,
            SaleOrder.payment_status == "confirmed",
        )
        .group_by(SaleOrder.client_id)
        .subquery()
    )
    filters = [DerivedGalleryMembership.derived_gallery_id == gallery.id]
    if status_filter:
        filters.append(DerivedGalleryMembership.status == status_filter)
    total = db.scalar(select(func.count()).select_from(DerivedGalleryMembership).where(*filters))
    rows = db.execute(
        select(
            DerivedGalleryMembership,
            Client,
            func.coalesce(selected_counts.c.selected_count, 0),
            func.coalesce(purchased_counts.c.purchased_count, 0),
            func.coalesce(order_counts.c.order_count, 0),
            func.coalesce(order_counts.c.confirmed_total_cents, 0),
            func.coalesce(order_counts.c.payment_rank, 0),
        )
        .join(Client, Client.id == DerivedGalleryMembership.client_id)
        .outerjoin(selected_counts, selected_counts.c.client_id == Client.id)
        .outerjoin(purchased_counts, purchased_counts.c.client_id == Client.id)
        .outerjoin(order_counts, order_counts.c.client_id == Client.id)
        .where(*filters)
        .order_by(DerivedGalleryMembership.created_at, DerivedGalleryMembership.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "gallery_id": str(gallery.id),
        "total": total or 0,
        "page": {"offset": offset, "limit": limit},
        "members": [
            _private_member_payload(
                db,
                membership,
                client=client,
                selected_count=selected_count,
                purchased_count=purchased_count,
                order_count=order_count,
                confirmed_total_cents=confirmed_total_cents,
                payment_status={0: "none", 1: "pending", 2: "confirmed"}[payment_rank],
            )
            for (
                membership,
                client,
                selected_count,
                purchased_count,
                order_count,
                confirmed_total_cents,
                payment_rank,
            ) in rows
        ],
    }


@app.post(
    "/admin/derived-galleries/{gallery_id}/members",
    status_code=status.HTTP_201_CREATED,
)
def add_private_gallery_member(
    gallery_id: UUID,
    payload: DerivedGalleryMemberInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    gallery = require_derived_gallery_mutable(db, gallery_id)
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    client = db.get(Client, payload.client_id)
    if not parent or not client:
        raise HTTPException(status_code=404, detail="Galeria pública ou cliente não encontrado.")

    if not db.scalar(
        select(DerivedGalleryMembership.id).where(
            DerivedGalleryMembership.derived_gallery_id == gallery.id
        )
    ):
        legacy_owner = db.get(Client, gallery.client_id)
        if legacy_owner:
            ensure_private_membership(
                db,
                parent=parent,
                client=legacy_owner,
                gallery=gallery,
                actor_admin_id=admin_session.subject_id,
            )

    existing = membership_for_client(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        lock=True,
    )
    if existing and existing.derived_gallery_id != gallery.id:
        raise HTTPException(
            status_code=409,
            detail="A cliente já pertence a outra galeria privada desta origem.",
        )
    if existing and existing.status == "unlinked":
        membership = reactivate_private_membership(
            existing,
            gallery=gallery,
            actor_admin_id=admin_session.subject_id,
        )
        created = False
    elif existing:
        membership = existing
        created = False
    else:
        try:
            resolution = ensure_private_membership(
                db,
                parent=parent,
                client=client,
                gallery=gallery,
                actor_admin_id=admin_session.subject_id,
            )
        except PrivateMembershipConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        membership = resolution.membership
        created = resolution.membership_created
    registration = link_client_to_parent(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        status="active",
    )
    audit(
        db,
        "private_gallery.member_joined" if created else "private_gallery.member_reused",
        str(membership.id),
    )
    if created:
        enqueue_membership_notification(
            db,
            event_key=f"member_joined:{membership.id}",
            event_type="member_joined",
            parent=parent,
            gallery=gallery,
            client=client,
        )
    db.commit()
    return {
        **_private_member_payload(db, membership),
        "registration_id": str(registration.id),
        "created": created,
    }


def _change_private_member_status(
    *,
    gallery_id: UUID,
    client_id: UUID,
    action: Literal["block", "unblock", "unlink"],
    request: Request,
    db: Session,
) -> dict[str, object]:
    admin_session = current_session(request, Role.ADMIN)
    gallery = require_derived_gallery_mutable(db, gallery_id)
    membership = _membership_in_gallery_or_404(
        db,
        gallery=gallery,
        client_id=client_id,
    )
    previous_status = membership.status
    try:
        if action == "block":
            block_private_membership(
                membership,
                actor_admin_id=admin_session.subject_id,
            )
        elif action == "unblock":
            unblock_private_membership(
                membership,
                actor_admin_id=admin_session.subject_id,
            )
        else:
            unlink_private_membership(
                membership,
                actor_admin_id=admin_session.subject_id,
            )
    except PrivateMembershipError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit(
        db,
        {
            "block": "private_gallery.member_blocked",
            "unblock": "private_gallery.member_unblocked",
            "unlink": "private_gallery.member_unlinked",
        }[action],
        str(membership.id),
    )
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    client = db.get(Client, membership.client_id)
    if parent and client and membership.status != previous_status:
        transition_at = (
            membership.blocked_at
            if action == "block"
            else membership.unlinked_at
            if action == "unlink"
            else now()
        )
        enqueue_membership_notification(
            db,
            event_key=f"member_{action}:{membership.id}:{transition_at.isoformat()}",
            event_type={
                "block": "member_blocked",
                "unblock": "member_unblocked",
                "unlink": "member_unlinked",
            }[action],
            parent=parent,
            gallery=gallery,
            client=client,
        )
    db.commit()
    return _private_member_payload(db, membership)


@app.post("/admin/derived-galleries/{gallery_id}/members/{client_id}/block")
def block_private_gallery_member(
    gallery_id: UUID,
    client_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    return _change_private_member_status(
        gallery_id=gallery_id,
        client_id=client_id,
        action="block",
        request=request,
        db=db,
    )


@app.post("/admin/derived-galleries/{gallery_id}/members/{client_id}/unblock")
def unblock_private_gallery_member(
    gallery_id: UUID,
    client_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    return _change_private_member_status(
        gallery_id=gallery_id,
        client_id=client_id,
        action="unblock",
        request=request,
        db=db,
    )


@app.delete("/admin/derived-galleries/{gallery_id}/members/{client_id}")
def unlink_private_gallery_member(
    gallery_id: UUID,
    client_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    return _change_private_member_status(
        gallery_id=gallery_id,
        client_id=client_id,
        action="unlink",
        request=request,
        db=db,
    )


@app.get("/admin/notifications")
def admin_gallery_membership_notifications(
    request: Request,
    admin_status: Literal["unread", "read"] | None = None,
    event_type: Literal[
        "private_created",
        "member_joined",
        "member_blocked",
        "member_unblocked",
        "member_unlinked",
    ]
    | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    query = select(GalleryMembershipNotificationOutbox)
    if admin_status:
        query = query.where(
            GalleryMembershipNotificationOutbox.admin_status == admin_status
        )
    if event_type:
        query = query.where(
            GalleryMembershipNotificationOutbox.event_type == event_type
        )
    notifications = list(
        db.scalars(
            query.order_by(
                GalleryMembershipNotificationOutbox.created_at.desc(),
                GalleryMembershipNotificationOutbox.id.desc(),
            ).limit(limit)
        )
    )
    return {
        "notifications": [
            {
                "id": str(item.id),
                "event_type": item.event_type,
                "admin_status": item.admin_status,
                "external_status": item.external_status,
                "parent_gallery_id": str(item.parent_gallery_id)
                if item.parent_gallery_id
                else None,
                "derived_gallery_id": str(item.derived_gallery_id)
                if item.derived_gallery_id
                else None,
                "client_id": str(item.client_id) if item.client_id else None,
                "parent_name": item.parent_name_snapshot,
                "derived_name": item.derived_name_snapshot,
                "client_name": item.client_name_snapshot,
                "created_at": item.created_at.isoformat(),
            }
            for item in notifications
        ]
    }


@app.post("/admin/notifications/{notification_id}/read")
def read_admin_gallery_membership_notification(
    notification_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_admin(request)
    notification = mark_membership_notification_read(db, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    db.commit()
    return {"id": str(notification.id), "status": notification.admin_status}


@app.get("/admin/derived-galleries/{gallery_id}/photos")
def admin_private_gallery_photos(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    rows = db.execute(
        select(DerivedGalleryPhoto, PhotoAsset, PhotoFolder)
        .join(PhotoAsset, PhotoAsset.id == DerivedGalleryPhoto.photo_asset_id)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(DerivedGalleryPhoto.derived_gallery_id == gallery.id)
        .order_by(PhotoFolder.position, PhotoAsset.created_at, PhotoAsset.id)
    ).all()
    reference_ids = [reference.id for reference, _photo, _folder in rows]
    origins_by_reference: dict[UUID, list[str]] = defaultdict(list)
    if reference_ids:
        for reference_id, origin in db.execute(
            select(
                DerivedGalleryPhotoOrigin.derived_gallery_photo_id,
                DerivedGalleryPhotoOrigin.origin,
            ).where(
                DerivedGalleryPhotoOrigin.derived_gallery_photo_id.in_(reference_ids)
            )
        ):
            origins_by_reference[reference_id].append(origin)
    return {
        "gallery_id": str(gallery.id),
        "photos": [
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "folder_id": str(folder.id),
                "folder_name": folder.name,
                "preview_url": f"/admin/photo-assets/{photo.id}/watermarked-preview",
                "origins": sorted(origins_by_reference.get(reference.id) or [reference.origin]),
            }
            for reference, photo, folder in rows
        ],
    }


@app.post("/admin/derived-galleries/{gallery_id}/photos")
def add_admin_private_gallery_photos(
    gallery_id: UUID,
    payload: DerivedGalleryPhotosInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id)
    photo_ids = set(payload.photo_ids)
    if len(photo_ids) != len(payload.photo_ids):
        raise HTTPException(status_code=422, detail="A lista de fotos contém duplicidades.")
    photos = list(
        db.scalars(
            select(PhotoAsset).where(
                PhotoAsset.id.in_(photo_ids),
                PhotoAsset.parent_gallery_id == gallery.parent_gallery_id,
                PhotoAsset.available,
            )
        )
    )
    released_folder_ids = set(
        db.scalars(
            select(PhotoFolder.id).where(
                PhotoFolder.id.in_({photo.folder_id for photo in photos}),
                PhotoFolder.parent_gallery_id == gallery.parent_gallery_id,
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
            )
        )
    )
    if len(photos) != len(photo_ids) or released_folder_ids != {
        photo.folder_id for photo in photos
    }:
        raise HTTPException(
            status_code=422,
            detail="Todas as fotos devem estar publicadas na Galeria pública desta privada.",
        )
    created = sum(
        ensure_private_photo_reference(
            db,
            gallery_id=gallery.id,
            photo_id=photo.id,
            origin="admin",
        )
        for photo in photos
    )
    audit(db, "private_gallery.photos_added", str(gallery.id))
    db.commit()
    return {"gallery_id": str(gallery.id), "references_created": created}


@app.delete("/admin/derived-galleries/{gallery_id}/photos/{photo_id}")
def remove_admin_private_gallery_photo(
    gallery_id: UUID,
    photo_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id)
    reference = db.scalar(
        select(DerivedGalleryPhoto).where(
            DerivedGalleryPhoto.derived_gallery_id == gallery.id,
            DerivedGalleryPhoto.photo_asset_id == photo_id,
        )
    )
    if not reference:
        raise HTTPException(status_code=404, detail="Foto não pertence à galeria privada.")
    if db.scalar(
        select(PhotoSelection.id).where(
            PhotoSelection.derived_gallery_id == gallery.id,
            PhotoSelection.photo_asset_id == photo_id,
        )
    ) and not db.scalar(
        select(DerivedGalleryPhotoOrigin.id).where(
            DerivedGalleryPhotoOrigin.derived_gallery_photo_id == reference.id,
            DerivedGalleryPhotoOrigin.origin == "client",
        )
    ):
        db.add(
            DerivedGalleryPhotoOrigin(
                derived_gallery_photo_id=reference.id,
                origin="client",
            )
        )
        db.flush()
    admin_origin = db.scalar(
        select(DerivedGalleryPhotoOrigin).where(
            DerivedGalleryPhotoOrigin.derived_gallery_photo_id == reference.id,
            DerivedGalleryPhotoOrigin.origin == "admin",
        )
    )
    if admin_origin:
        db.delete(admin_origin)
        db.flush()
    remaining_origins = list(
        db.scalars(
            select(DerivedGalleryPhotoOrigin.origin).where(
                DerivedGalleryPhotoOrigin.derived_gallery_photo_id == reference.id
            )
        )
    )
    reference_removed = False
    if not remaining_origins:
        db.delete(reference)
        reference_removed = True
    audit(db, "private_gallery.photo_admin_origin_removed", str(reference.id))
    db.commit()
    return {
        "gallery_id": str(gallery.id),
        "photo_id": str(photo_id),
        "reference_removed": reference_removed,
        "retained_origins": sorted(remaining_origins),
    }


@app.delete("/admin/derived-galleries/{gallery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_derived_gallery(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Galeria pública de origem não encontrada.")
    if parent.lifecycle_status == "deleting":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A Galeria pública está em exclusão. Aguarde a conclusão antes de excluir a privada.",
        )
    member_client_ids = set(
        db.scalars(
            select(DerivedGalleryMembership.client_id).where(
                DerivedGalleryMembership.derived_gallery_id == gallery.id
            )
        )
    )
    if not member_client_ids:
        member_client_ids.add(gallery.client_id)
    for client_id in member_client_ids:
        enforce_commercial_removal_or_409(
            db,
            parent_gallery_id=gallery.parent_gallery_id,
            client_id=client_id,
            derived_gallery_id=gallery.id,
        )
    for model in (PhotoComment, PhotoFavorite, PhotoView, PhotoSelection):
        db.execute(delete(model).where(model.derived_gallery_id == gallery.id))
    reference_ids = list(
        db.scalars(
            select(DerivedGalleryPhoto.id).where(
                DerivedGalleryPhoto.derived_gallery_id == gallery.id
            )
        )
    )
    if reference_ids:
        db.execute(
            delete(DerivedGalleryPhotoOrigin).where(
                DerivedGalleryPhotoOrigin.derived_gallery_photo_id.in_(reference_ids)
            )
        )
    db.execute(
        delete(DerivedGalleryPhoto).where(DerivedGalleryPhoto.derived_gallery_id == gallery.id)
    )
    db.execute(delete(GalleryAccess).where(GalleryAccess.gallery_id == gallery.id))
    db.execute(
        delete(GalleryAccessCapability).where(
            GalleryAccessCapability.derived_gallery_id == gallery.id
        )
    )
    db.execute(
        delete(DerivedGalleryMembership).where(
            DerivedGalleryMembership.derived_gallery_id == gallery.id
        )
    )
    audit(db, "derived_gallery.deleted", str(gallery.id))
    db.delete(gallery)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def gallery_operational_status(db: Session, gallery: DerivedGallery) -> dict[str, object]:
    selections = list(
        db.scalars(select(PhotoSelection).where(PhotoSelection.derived_gallery_id == gallery.id))
    )
    orders = list(db.scalars(select(SaleOrder).where(SaleOrder.derived_gallery_id == gallery.id)))
    frozen = bool(gallery.selection_expires_at and expired(gallery.selection_expires_at))
    return {
        "frozen": frozen,
        "blocked": not gallery.access_enabled,
        "selection_in_progress": bool(selections) and not bool(orders),
        "payment_pending": any(order.payment_status == "pending" for order in orders),
        "selection_finalized": bool(orders),
    }


@app.get("/admin/derived-galleries")
def list_derived_galleries(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    tab: str = Query(default="active", pattern="^(active|frozen)$"),
    state: str | None = Query(
        default=None,
        pattern="^(selection_finalized|payment_pending|blocked|selection_in_progress)$",
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    normalized = normalize_e164(query) if query and query.startswith("+") else None
    galleries = list(db.scalars(select(DerivedGallery).order_by(DerivedGallery.created_at.desc())))
    entries: list[dict[str, object]] = []
    for gallery in galleries:
        status_data = gallery_operational_status(db, gallery)
        if (tab == "frozen") != status_data["frozen"]:
            continue
        owner = db.get(Client, gallery.client_id)
        if query:
            search = query.casefold()
            matches = gallery.name.casefold().find(search) >= 0 or bool(
                owner
                and (owner.full_name.casefold().find(search) >= 0 or owner.phone_e164 == normalized)
            )
            if not matches:
                continue
        if state and not status_data[state]:
            continue
        cover = db.scalar(
            select(DerivedGalleryPhoto.photo_asset_id)
            .where(DerivedGalleryPhoto.derived_gallery_id == gallery.id)
            .limit(1)
        )
        entries.append(
            {
                "id": str(gallery.id),
                "name": gallery.name,
                "parent_gallery_id": str(gallery.parent_gallery_id),
                "selection_expires_at": gallery.selection_expires_at.isoformat()
                if gallery.selection_expires_at
                else None,
                "cover_preview_url": f"/admin/photo-assets/{cover}/preview" if cover else None,
                "client_count": 1,
                "responsible_count": 1,
                **status_data,
            }
        )
    return {"total": len(entries), "galleries": entries[offset : offset + limit]}


@app.get("/admin/derived-galleries/{gallery_id}")
def derived_gallery_detail(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    status_data = gallery_operational_status(db, gallery)
    cover = db.scalar(
        select(DerivedGalleryPhoto.photo_asset_id)
        .where(DerivedGalleryPhoto.derived_gallery_id == gallery.id)
        .limit(1)
    )
    owner = db.get(Client, gallery.client_id)
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    selected_count = (
        db.scalar(
            select(func.count())
            .select_from(PhotoSelection)
            .where(
                PhotoSelection.derived_gallery_id == gallery.id,
                PhotoSelection.client_id == gallery.client_id,
            )
        )
        or 0
    )
    orders = list(
        db.scalars(
            select(SaleOrder).where(
                SaleOrder.derived_gallery_id == gallery.id, SaleOrder.client_id == gallery.client_id
            )
        )
    )
    client_data = (
        {
            "id": str(owner.id),
            "name": owner.full_name,
            "phone": owner.phone_e164,
            "active": gallery.access_enabled,
            "selected_count": selected_count,
            "payment_pending": any(order.payment_status == "pending" for order in orders),
            "confirmed_order_count": sum(order.payment_status == "confirmed" for order in orders),
        }
        if owner
        else None
    )
    return {
        "id": str(gallery.id),
        "parent_gallery_id": str(gallery.parent_gallery_id),
        "name": gallery.name,
        "link": None,
        "custom_message": parent.sales_message or "",
        "favorites_enabled": parent.favorites_enabled,
        "comments_enabled": parent.comments_enabled,
        "selection_expires_at": gallery.selection_expires_at.isoformat()
        if gallery.selection_expires_at
        else None,
        "cover_preview_url": f"/admin/photo-assets/{cover}/preview" if cover else None,
        "client": client_data,
        "responsible": client_data,
        "configuration_inherited": True,
        "origin_active": parent.lifecycle_status == "active",
        **status_data,
    }


@app.patch("/admin/derived-galleries/{gallery_id}")
def update_derived_gallery(
    gallery_id: UUID,
    payload: DerivedGallerySettingsInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id)
    for field in payload.model_fields_set:
        setattr(gallery, field, getattr(payload, field))
    audit(db, "derived_gallery.updated", str(gallery.id))
    db.commit()
    return {"id": str(gallery.id)}


@app.post("/admin/derived-galleries/{gallery_id}/renew")
def renew_gallery_selection(
    gallery_id: UUID,
    payload: GalleryRenewalInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id)
    if expired(payload.selection_expires_at):
        raise HTTPException(status_code=422, detail="Informe um prazo futuro.")
    gallery.selection_expires_at = payload.selection_expires_at
    audit(db, "derived_gallery.selection_renewed", str(gallery_id))
    db.commit()
    return {"id": str(gallery_id)}


@app.get("/admin/statistics")
def admin_statistics(
    request: Request,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    client_id: UUID | None = None,
    parent_gallery_id: UUID | None = None,
    derived_gallery_id: UUID | None = None,
    event_name: str | None = Query(default=None, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    data = statistics_data(
        db,
        starts_at=starts_at,
        ends_at=ends_at,
        client_id=client_id,
        parent_gallery_id=parent_gallery_id,
        derived_gallery_id=derived_gallery_id,
        event_name=event_name,
    )
    purchased = data["purchased"]
    selected_not_purchased = data["selected_not_purchased"]
    return {
        "purchased_count": len(purchased),
        "selected_not_purchased_count": len(selected_not_purchased),
        "revenue_cents": data["revenue_cents"],
        "revenue_by_day": data["revenue_by_day"],
        "purchased_photos": purchased[offset : offset + limit],
        "selected_not_purchased_photos": selected_not_purchased[offset : offset + limit],
    }


@app.get("/admin/statistics/filters")
def admin_statistics_filters(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    """Opções mínimas para os filtros operacionais, sem expor telefone de clientes."""
    require_admin(request)
    clients = list(db.scalars(select(Client).order_by(Client.full_name)))
    parents = list(
        db.scalars(
            select(ParentGallery)
            .where(ParentGallery.lifecycle_status != "deleted")
            .order_by(ParentGallery.name)
        )
    )
    galleries = list(db.scalars(select(DerivedGallery).order_by(DerivedGallery.name)))
    return {
        "clients": [{"id": str(client.id), "name": client.full_name} for client in clients],
        "parent_galleries": [
            {"id": str(gallery.id), "name": gallery.name, "event_name": gallery.event_name or ""}
            for gallery in parents
        ],
        "derived_galleries": [
            {"id": str(gallery.id), "name": gallery.name, "client_id": str(gallery.client_id)}
            for gallery in galleries
        ],
    }


@app.get("/admin/statistics/selected-not-purchased.txt", response_class=PlainTextResponse)
def export_selected_not_purchased_txt(
    request: Request,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    client_id: UUID | None = None,
    parent_gallery_id: UUID | None = None,
    derived_gallery_id: UUID | None = None,
    event_name: str | None = Query(default=None, max_length=200),
    db: Session = Depends(db_session),
) -> PlainTextResponse:
    require_admin(request)
    data = statistics_data(
        db,
        starts_at=starts_at,
        ends_at=ends_at,
        client_id=client_id,
        parent_gallery_id=parent_gallery_id,
        derived_gallery_id=derived_gallery_id,
        event_name=event_name,
    )
    return statistics_txt(data["selected_not_purchased"])


@app.get("/admin/statistics/purchased.txt", response_class=PlainTextResponse)
def export_purchased_txt(
    request: Request,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    client_id: UUID | None = None,
    parent_gallery_id: UUID | None = None,
    derived_gallery_id: UUID | None = None,
    event_name: str | None = Query(default=None, max_length=200),
    db: Session = Depends(db_session),
) -> PlainTextResponse:
    require_admin(request)
    data = statistics_data(
        db,
        starts_at=starts_at,
        ends_at=ends_at,
        client_id=client_id,
        parent_gallery_id=parent_gallery_id,
        derived_gallery_id=derived_gallery_id,
        event_name=event_name,
    )
    return statistics_txt(data["purchased"])


@app.get("/library")
def client_library(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, object]]]:
    session = current_session(request, Role.CLIENT)
    registrations = list(
        db.scalars(
            select(ParentGalleryRegistration)
            .where(ParentGalleryRegistration.client_id == session.subject_id)
            .order_by(ParentGalleryRegistration.created_at.desc())
        )
    )
    registrations_by_parent = {
        registration.parent_gallery_id: registration for registration in registrations
    }
    public_rows: list[dict[str, object]] = []
    for registration in registrations:
        parent = db.get(ParentGallery, registration.parent_gallery_id)
        if not parent or not parent.active or parent.lifecycle_status != "active":
            continue
        access_state = "active" if registration.status == "active" else "pending_review"
        public_rows.append(
            {
                "id": str(parent.id),
                "name": parent.name,
                "event_name": parent.event_name or "",
                "access_mode": parent.access_mode,
                "gallery_status": access_state,
                "browse_url": f"/public-galleries/{parent.id}"
                if access_state == "active"
                else None,
            }
        )

    membership_rows = list(
        db.execute(
            select(DerivedGallery, DerivedGalleryMembership.status)
            .join(
                DerivedGalleryMembership,
                DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id,
            )
            .where(
                DerivedGalleryMembership.client_id == session.subject_id,
                DerivedGalleryMembership.status.in_(("active", "blocked")),
            )
        )
    )
    any_membership = (
        select(DerivedGalleryMembership.id)
        .where(DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id)
        .exists()
    )
    membership_rows.extend(
        (gallery, "active")
        for gallery in db.scalars(
            select(DerivedGallery).where(
                DerivedGallery.client_id == session.subject_id,
                ~any_membership,
            )
        )
    )
    membership_rows.sort(key=lambda row: row[0].created_at, reverse=True)
    rows: list[dict[str, object]] = []
    for gallery, membership_status in membership_rows:
        parent = db.get(ParentGallery, gallery.parent_gallery_id)
        folders = list(
            db.scalars(
                select(PhotoFolder)
                .join(PhotoAsset, PhotoAsset.folder_id == PhotoFolder.id)
                .join(DerivedGalleryPhoto, DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id)
                .where(
                    DerivedGalleryPhoto.derived_gallery_id == gallery.id,
                    PhotoFolder.status == "released",
                    PhotoFolder.purpose == "content",
                )
                .distinct()
                .order_by(PhotoFolder.position, PhotoFolder.created_at)
            )
        )
        origin_removed = bool(parent and parent.lifecycle_status == "deleted")
        origin_registration = registrations_by_parent.get(gallery.parent_gallery_id)
        origin_available = bool(
            parent
            and parent.active
            and parent.lifecycle_status == "active"
            and origin_registration
            and origin_registration.status == "active"
        )
        gallery_status = (
            "blocked"
            if membership_status == "blocked" or not gallery.access_enabled
            else "origin_removed"
            if origin_removed
            else "expired"
            if gallery.selection_expires_at and expired(gallery.selection_expires_at)
            else "active"
        )
        rows.append(
            {
                "id": str(gallery.id),
                "name": gallery.name,
                "message": (parent.sales_message or "") if parent else "",
                "selection_expires_at": gallery.selection_expires_at.isoformat()
                if gallery.selection_expires_at
                else None,
                "gallery_status": gallery_status,
                "membership_status": membership_status,
                "browse_url": f"/gallery/{gallery.id}"
                if membership_status == "active" and gallery.access_enabled
                else None,
                "origin_removed": origin_removed,
                "origin": {
                    "id": str(gallery.parent_gallery_id),
                    "name": parent.name if parent else "Galeria pública removida",
                    "available": origin_available,
                    "browse_url": f"/public-galleries/{gallery.parent_gallery_id}"
                    if origin_available
                    else None,
                },
                "folders": [{"id": str(folder.id), "name": folder.name} for folder in folders],
            }
        )
    return {
        "public_galleries": public_rows,
        "private_galleries": rows,
        "galleries": rows,
    }


@app.get("/library/purchases")
def client_purchase_history(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, object]]]:
    """Histórico confirmado da própria cliente, sem variante administrativa."""
    session = current_session(request, Role.CLIENT)
    orders = db.scalars(
        select(SaleOrder)
        .where(
            SaleOrder.client_id == session.subject_id,
            SaleOrder.payment_status == "confirmed",
        )
        .order_by(SaleOrder.confirmed_at.desc(), SaleOrder.created_at.desc())
    )
    result: list[dict[str, object]] = []
    for order in orders:
        gallery = (
            db.get(DerivedGallery, order.derived_gallery_id) if order.derived_gallery_id else None
        )
        items = db.scalars(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id))
        item_payloads = []
        for item in items:
            historical_media = db.scalar(
                select(CommercialHistoryMedia).where(
                    CommercialHistoryMedia.sale_order_item_id == item.id,
                    CommercialHistoryMedia.status == "ready",
                )
            )
            item_payloads.append(
                {
                    "item_id": str(item.id),
                    "photo_id": str(item.photo_asset_id_snapshot),
                    "name": item.filename_snapshot,
                    "preview_url": f"/library/history/items/{item.id}/preview"
                    if historical_media and historical_media.preview_storage_key
                    else (
                        f"/gallery/{order.derived_gallery_id}/photos/{item.photo_asset_id}/preview"
                        if order.derived_gallery_id and item.photo_asset_id
                        else None
                    ),
                    "delivery_url": f"/library/history/items/{item.id}/delivery"
                    if historical_media and historical_media.delivery_storage_key
                    else None,
                    "delivery_reference_available": bool(
                        historical_media and historical_media.delivery_reference
                    ),
                }
            )
        result.append(
            {
                "id": str(order.id),
                "gallery_name": order.derived_gallery_name_snapshot,
                "parent_gallery_name": order.parent_gallery_name_snapshot,
                "gallery_status_label": "Galeria ativa" if gallery else "Galeria removida",
                "gallery_removed": gallery is None,
                "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
                "total_cents": order.total_cents,
                "items": item_payloads,
            }
        )
    return {"orders": result}


def _historical_item_for_client(
    db: Session, item_id: UUID, client_id: UUID
) -> tuple[SaleOrderItem, CommercialHistoryMedia]:
    item = db.scalar(
        select(SaleOrderItem)
        .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
        .where(
            SaleOrderItem.id == item_id,
            SaleOrder.client_id == client_id,
            SaleOrder.payment_status == "confirmed",
        )
    )
    if not item:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    historical_media = db.scalar(
        select(CommercialHistoryMedia).where(
            CommercialHistoryMedia.sale_order_item_id == item.id,
            CommercialHistoryMedia.status == "ready",
        )
    )
    if not historical_media:
        raise HTTPException(status_code=404, detail="Mídia histórica indisponível.")
    return item, historical_media


@app.get("/library/history/items/{item_id}/preview")
def client_historical_preview(
    item_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    session = current_session(request, Role.CLIENT)
    item, historical_media = _historical_item_for_client(db, item_id, session.subject_id)
    if not historical_media.preview_storage_key:
        raise HTTPException(status_code=404, detail="Prévia histórica indisponível.")
    path = historical_media_path(historical_media.preview_storage_key)
    return protected_preview_response(path, f"historico-{item.id}.jpg")


@app.get("/library/history/items/{item_id}/delivery")
def client_historical_delivery(
    item_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    session = current_session(request, Role.CLIENT)
    item, historical_media = _historical_item_for_client(db, item_id, session.subject_id)
    if not historical_media.delivery_storage_key:
        raise HTTPException(
            status_code=409,
            detail="A entrega está preservada por referência segura externa.",
        )
    path = historical_media_path(historical_media.delivery_storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Entrega histórica indisponível.")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=item.filename_snapshot,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/gallery/{gallery_id}")
def gallery_area(gallery_id: UUID, request: Request) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    with SessionLocal() as db:
        derived_gallery_for_client(db, gallery_id, session.subject_id, allow_deleted_origin=True)
    return {"status": "authorized"}


@app.get("/gallery/{gallery_id}/photos")
def gallery_photos(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, object]]]:
    """Lista somente os identificadores e nomes atribuídos à galeria privada."""
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id, allow_deleted_origin=True)
    photos = list(
        db.scalars(
            select(PhotoAsset)
            .join(DerivedGalleryPhoto, DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id)
            .outerjoin(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                DerivedGalleryPhoto.derived_gallery_id == gallery_id,
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
            )
            .distinct()
            .order_by(PhotoAsset.created_at, PhotoAsset.filename)
        )
    )
    derivatives = (
        {
            derivative.photo_asset_id: derivative
            for derivative in db.scalars(
                select(MediaDerivative).where(
                    MediaDerivative.photo_asset_id.in_([photo.id for photo in photos]),
                    MediaDerivative.variant == "client_preview",
                    MediaDerivative.status == "ready",
                )
            )
        }
        if photos
        else {}
    )
    return {
        "photos": [
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "preview_url": f"/gallery/{gallery_id}/photos/{photo.id}/preview",
                "width": derivatives[photo.id].width if photo.id in derivatives else None,
                "height": derivatives[photo.id].height if photo.id in derivatives else None,
            }
            for photo in photos
        ]
    }


@app.get("/gallery/{gallery_id}/folders")
def gallery_released_folders(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Lista somente os lotes liberados e vinculados à galeria privada da cliente."""
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id, allow_deleted_origin=True)
    folders = db.scalars(
        select(PhotoFolder)
        .join(PhotoAsset, PhotoAsset.folder_id == PhotoFolder.id)
        .join(DerivedGalleryPhoto, DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id)
        .where(
            DerivedGalleryPhoto.derived_gallery_id == gallery_id,
            PhotoFolder.status == "released",
            PhotoFolder.purpose == "content",
        )
        .distinct()
        .order_by(PhotoFolder.position, PhotoFolder.created_at)
    )
    rows = []
    for folder in folders:
        count = (
            db.scalar(
                select(func.count(func.distinct(PhotoAsset.id)))
                .select_from(PhotoAsset)
                .join(DerivedGalleryPhoto, DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id)
                .where(
                    DerivedGalleryPhoto.derived_gallery_id == gallery_id,
                    PhotoAsset.folder_id == folder.id,
                )
            )
            or 0
        )
        rows.append(
            {
                "id": str(folder.id),
                "name": folder.name,
                "position": folder.position,
                "photo_count": count,
            }
        )
    return {"total": len(rows), "folders": rows}


@app.get("/gallery/{gallery_id}/review")
def gallery_review(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Estado privado de revisão para cliente, incluindo permissões e interações próprias."""
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(
        db, gallery_id, session.subject_id, allow_deleted_origin=True
    )
    photos = list(
        db.scalars(
            select(PhotoAsset)
            .join(DerivedGalleryPhoto, DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                DerivedGalleryPhoto.derived_gallery_id == gallery_id,
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
            )
            .distinct()
            .order_by(PhotoAsset.created_at, PhotoAsset.filename)
        )
    )
    photo_ids = {photo.id for photo in photos}
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    if not parent:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    cover = _gallery_cover_photo(db, parent)
    cover_ready = bool(cover and _client_preview_derivative(db, cover.id))
    selections = set(
        db.scalars(
            select(PhotoSelection.photo_asset_id).where(
                PhotoSelection.derived_gallery_id == gallery_id,
                PhotoSelection.client_id == session.subject_id,
            )
        )
    )
    favorites = set(
        db.scalars(
            select(PhotoFavorite.photo_asset_id).where(
                PhotoFavorite.derived_gallery_id == gallery_id,
                PhotoFavorite.client_id == session.subject_id,
            )
        )
    )
    viewed = set(
        db.scalars(
            select(PhotoView.photo_asset_id).where(
                PhotoView.derived_gallery_id == gallery_id,
                PhotoView.client_id == session.subject_id,
            )
        )
    )
    purchased = set(
        db.scalars(
            select(SaleOrderItem.photo_asset_id)
            .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
            .where(
                SaleOrder.derived_gallery_id == gallery_id,
                SaleOrder.client_id == session.subject_id,
                SaleOrder.payment_status == "confirmed",
            )
        )
    )
    derivatives = (
        {
            derivative.photo_asset_id: derivative
            for derivative in db.scalars(
                select(MediaDerivative).where(
                    MediaDerivative.photo_asset_id.in_(photo_ids),
                    MediaDerivative.variant == "client_preview",
                    MediaDerivative.status == "ready",
                )
            )
        }
        if photo_ids
        else {}
    )
    return {
        "gallery": {
            "name": gallery.name,
            "message": parent.sales_message or "",
            "selection_expires_at": (
                gallery.selection_expires_at.isoformat() if gallery.selection_expires_at else None
            ),
            "selection_open": not gallery.selection_expires_at
            or not expired(gallery.selection_expires_at),
            "favorites_enabled": parent.favorites_enabled,
            "comments_enabled": parent.comments_enabled,
            "folder_display_mode": parent.folder_display_mode,
            "cover_title_font": normalize_title_font(parent.cover_title_font),
            "cover_title_color": parent.cover_title_color,
            "cover_title_size": parent.cover_title_size,
            "cover_title_position": parent.cover_title_position,
            "cover_preview_url": (
                f"/gallery/{gallery_id}/cover-preview"
                if cover_ready and cover
                else None
            ),
        },
        "photos": [
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "folder_id": str(photo.folder_id),
                "preview_url": f"/gallery/{gallery_id}/photos/{photo.id}/preview",
                "width": derivatives[photo.id].width if photo.id in derivatives else None,
                "height": derivatives[photo.id].height if photo.id in derivatives else None,
                "selected": photo.id in selections,
                "favorited": photo.id in favorites,
                "purchase_state": "já comprada"
                if photo.id in purchased
                else ("visualizada mas não comprada" if photo.id in viewed else "nova"),
            }
            for photo in photos
            if photo.id in photo_ids
        ],
    }


@app.get("/gallery/{gallery_id}/cover-preview")
def client_gallery_cover_preview(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    """Entrega capa dedicada ou de conteúdo sem exigir vínculo privado da própria capa."""
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(
        db, gallery_id, session.subject_id, allow_deleted_origin=True
    )
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    cover = _gallery_cover_photo(db, parent) if parent else None
    derivative = _client_preview_derivative(db, cover.id) if cover else None
    if not cover or not derivative:
        raise HTTPException(status_code=404, detail="Capa indisponível.")
    try:
        path = safe_derivative_path(derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Capa indisponível.") from exc
    audit(db, "media_preview.client_cover_viewed", str(gallery_id))
    db.commit()
    return protected_preview_response(path, f"capa-{gallery_id}.jpg")


@app.get("/gallery/{gallery_id}/photos/{photo_id}/preview")
def client_photo_preview(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    """Entrega somente o derivado com marca à cliente autorizada na galeria privada."""
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id, allow_deleted_origin=True)
    assigned_photo_for_gallery(db, gallery_id, photo_id)
    derivative = db.scalar(
        select(MediaDerivative).where(
            MediaDerivative.photo_asset_id == photo_id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
    )
    if not derivative:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    try:
        path = safe_derivative_path(derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Prévia indisponível.") from exc
    viewed = db.scalar(
        select(PhotoView).where(
            PhotoView.derived_gallery_id == gallery_id,
            PhotoView.client_id == session.subject_id,
            PhotoView.photo_asset_id == photo_id,
        )
    )
    if viewed:
        viewed.last_viewed_at = now()
    else:
        db.add(
            PhotoView(
                derived_gallery_id=gallery_id, client_id=session.subject_id, photo_asset_id=photo_id
            )
        )
    audit(db, "media_preview.client_viewed", str(gallery_id))
    db.commit()
    return protected_preview_response(path, f"previa-{photo_id}.jpg")


@app.post("/gallery/{gallery_id}/photos/{photo_id}/selection", status_code=status.HTTP_201_CREATED)
def select_photo(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id)
    require_selection_window(gallery)
    assigned_photo_for_gallery(db, gallery_id, photo_id)
    try:
        result = derive_client_selection(
            db,
            parent_gallery_id=gallery.parent_gallery_id,
            client_id=session.subject_id,
            photo_id=photo_id,
        )
    except PrivateDerivationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result.selection_created:
        audit(db, "photo_selection.created", str(gallery_id))
    db.commit()
    return {"status": "selected"}


@app.post(
    "/public-galleries/{parent_gallery_id}/photos/{photo_id}/selection",
    status_code=status.HTTP_201_CREATED,
)
def select_photo_from_public_gallery(
    parent_gallery_id: UUID,
    photo_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    try:
        result = derive_client_selection(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
            photo_id=photo_id,
        )
    except PrivateDerivationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result.selection_created:
        audit(db, "photo_selection.created_from_public_gallery", str(result.gallery.id))
    db.commit()
    return {
        "status": "selected",
        "private_gallery_id": str(result.gallery.id),
        "gallery_created": result.gallery_created,
        "reference_created": result.reference_created,
        "selection_created": result.selection_created,
        "cart": _client_cart_payload(db, result.gallery, session.subject_id),
    }


def _operational_gallery_for_public_client(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID
) -> DerivedGallery | None:
    membership = membership_for_client(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=client_id,
    )
    if membership and membership.status == "active":
        gallery = db.get(DerivedGallery, membership.derived_gallery_id)
        return gallery if gallery and gallery.access_enabled else None
    return next(
        (
            gallery
            for gallery in operational_galleries_for_client(db, client_id=client_id)
            if gallery.parent_gallery_id == parent_gallery_id
        ),
        None,
    )


@app.delete("/public-galleries/{parent_gallery_id}/photos/{photo_id}/selection")
def unselect_photo_from_public_gallery(
    parent_gallery_id: UUID,
    photo_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    try:
        require_public_gallery_browsing(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    gallery = _operational_gallery_for_public_client(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=session.subject_id,
    )
    if not gallery:
        return {
            "status": "unselected",
            "private_gallery_id": None,
            "gallery_closed": False,
            "cart": {"quantity": 0, "items": []},
        }
    try:
        result = remove_client_selection_and_close_if_empty(
            db,
            gallery=gallery,
            client_id=session.subject_id,
            photo_id=photo_id,
        )
    except CommercialRemovalBlocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommercialRemovalPreparationFailed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result.selection_removed:
        audit(db, "photo_selection.removed_from_public_gallery", str(gallery.id))
    private_gallery_id = None if result.gallery_closed else gallery.id
    db.commit()
    return {
        "status": "unselected",
        "private_gallery_id": str(private_gallery_id) if private_gallery_id else None,
        "gallery_closed": result.gallery_closed,
        "cart": (
            _client_cart_payload(db, gallery, session.subject_id)
            if private_gallery_id
            else {"quantity": 0, "items": []}
        ),
    }


@app.post("/public-gallery/access")
def access_public_gallery_with_session(
    payload: PublicGalleryAccessInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    capability = resolve_gallery_capability(db, payload.access_token)
    if not capability:
        audit(db, "public_gallery.capability_rejected", "invalid")
        db.commit()
        raise HTTPException(status_code=403, detail="Acesso não autorizado.")
    try:
        result = apply_public_gallery_access(
            db,
            parent_gallery_id=capability.parent_gallery_id,
            client_id=session.subject_id,
            capability=capability,
            return_to=payload.return_to,
        )
    except PublicGalleryAccessDenied as exc:
        audit(db, "public_gallery.access_denied", str(capability.parent_gallery_id))
        db.commit()
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    audit(db, "public_gallery.accessed", str(result.parent.id))
    if capability.scope == "parent_invite":
        consume_gallery_capability(capability)
        audit(db, "parent_gallery.invite_verified", str(capability.id))
    db.commit()
    return {
        "parent_gallery_id": str(result.parent.id),
        "access_state": result.state,
        "destination": result.destination,
        "can_browse_photos": result.state == "authorized",
    }


@app.get("/public-galleries/{parent_gallery_id}")
def public_gallery_for_client(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    try:
        parent = require_public_gallery_browsing(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    return {
        "id": str(parent.id),
        "name": parent.name,
        "event_name": parent.event_name,
        "description": parent.description,
        "access_mode": parent.access_mode,
        "folder_display_mode": parent.folder_display_mode,
        "cover_title_font": normalize_title_font(parent.cover_title_font),
        "cover_title_color": parent.cover_title_color,
        "cover_title_size": parent.cover_title_size,
        "cover_title_position": parent.cover_title_position,
        "cover_preview_url": (
            f"/public-galleries/{parent.id}/cover-preview"
            if _cover_preview_url(db, parent)
            else None
        ),
        "photos_url": f"/public-galleries/{parent.id}/photos",
    }


@app.get("/public-galleries/{parent_gallery_id}/photos")
def public_gallery_photos(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    try:
        require_public_gallery_browsing(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    gallery = _operational_gallery_for_public_client(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=session.subject_id,
    )
    selections = (
        set(
            db.scalars(
                select(PhotoSelection.photo_asset_id).where(
                    PhotoSelection.derived_gallery_id == gallery.id,
                    PhotoSelection.client_id == session.subject_id,
                )
            )
        )
        if gallery
        else set()
    )
    photos = list(
        db.scalars(
            select(PhotoAsset)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                PhotoAsset.parent_gallery_id == parent_gallery_id,
                PhotoAsset.available,
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
            )
            .order_by(PhotoFolder.position, PhotoAsset.created_at, PhotoAsset.filename)
        )
    )
    derivatives = (
        {
            derivative.photo_asset_id: derivative
            for derivative in db.scalars(
                select(MediaDerivative).where(
                    MediaDerivative.photo_asset_id.in_([photo.id for photo in photos]),
                    MediaDerivative.variant == "client_preview",
                    MediaDerivative.status == "ready",
                )
            )
        }
        if photos
        else {}
    )
    folders = {
        folder.id: folder
        for folder in db.scalars(
            select(PhotoFolder).where(
                PhotoFolder.id.in_({photo.folder_id for photo in photos}),
                PhotoFolder.purpose == "content",
            )
        )
    } if photos else {}
    return {
        "photos": [
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "folder_id": str(photo.folder_id),
                "folder_name": folders[photo.folder_id].name,
                "folder_position": folders[photo.folder_id].position,
                "preview_url": (f"/public-galleries/{parent_gallery_id}/photos/{photo.id}/preview"),
                "width": derivatives[photo.id].width if photo.id in derivatives else None,
                "height": derivatives[photo.id].height if photo.id in derivatives else None,
                "selected": photo.id in selections,
            }
            for photo in photos
        ],
        "private_gallery_id": str(gallery.id) if gallery else None,
        "cart": (
            _client_cart_payload(db, gallery, session.subject_id)
            if gallery
            else {"quantity": 0, "items": []}
        ),
    }


@app.get("/public-galleries/{parent_gallery_id}/cover-preview")
def public_gallery_cover_preview(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> FileResponse:
    session = current_session(request, Role.CLIENT)
    try:
        parent = require_public_gallery_browsing(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    cover = _gallery_cover_photo(db, parent)
    derivative = _client_preview_derivative(db, cover.id) if cover else None
    if not cover or not derivative:
        raise HTTPException(status_code=404, detail="Capa indisponível.")
    try:
        path = safe_derivative_path(derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Capa indisponível.") from exc
    audit(db, "media_preview.public_gallery_cover_viewed", str(parent_gallery_id))
    db.commit()
    return protected_preview_response(path, f"capa-{parent_gallery_id}.jpg")


@app.get("/public-galleries/{parent_gallery_id}/photos/{photo_id}/preview")
def public_gallery_photo_preview(
    parent_gallery_id: UUID,
    photo_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> FileResponse:
    session = current_session(request, Role.CLIENT)
    try:
        require_public_gallery_browsing(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    photo = db.get(PhotoAsset, photo_id)
    folder = db.get(PhotoFolder, photo.folder_id) if photo else None
    if (
        not photo
        or photo.parent_gallery_id != parent_gallery_id
        or not photo.available
        or not folder
        or folder.status != "released"
        or folder.purpose != "content"
    ):
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    derivative = db.scalar(
        select(MediaDerivative).where(
            MediaDerivative.photo_asset_id == photo.id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
    )
    if not derivative:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    try:
        path = safe_derivative_path(derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Prévia indisponível.") from exc
    audit(db, "media_preview.public_gallery_viewed", str(parent_gallery_id))
    db.commit()
    return protected_preview_response(path, f"previa-{photo.id}.jpg")


@app.delete(
    "/gallery/{gallery_id}/photos/{photo_id}/selection", status_code=status.HTTP_204_NO_CONTENT
)
def unselect_photo(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id)
    parent_gallery_id = gallery.parent_gallery_id
    try:
        result = remove_client_selection_and_close_if_empty(
            db,
            gallery=gallery,
            client_id=session.subject_id,
            photo_id=photo_id,
        )
    except CommercialRemovalBlocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommercialRemovalPreparationFailed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result.selection_removed:
        audit(db, "photo_selection.removed", str(gallery_id))
        if result.gallery_closed:
            audit(db, "derived_gallery.closed_without_references", str(gallery_id))
        db.commit()
    headers: dict[str, str] = {}
    if result.gallery_closed:
        headers["X-Markina-Gallery-Closed"] = "true"
        parent = db.get(ParentGallery, parent_gallery_id)
        registration = db.scalar(
            select(ParentGalleryRegistration).where(
                ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
                ParentGalleryRegistration.client_id == session.subject_id,
                ParentGalleryRegistration.status == "active",
            )
        )
        if (
            parent
            and parent.active
            and parent.lifecycle_status == "active"
            and parent.access_mode != "collective_protected"
            and registration
        ):
            headers["X-Markina-Public-Gallery-Url"] = f"/public-galleries/{parent_gallery_id}"
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=headers)


def _client_cart_payload(
    db: Session, gallery: DerivedGallery, client_id: UUID
) -> dict[str, object]:
    selections = list(
        db.scalars(
            select(PhotoSelection).where(
                PhotoSelection.derived_gallery_id == gallery.id,
                PhotoSelection.client_id == client_id,
            )
        )
    )
    result: dict[str, object] = {"quantity": len(selections), "items": []}
    if not selections:
        return result
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    if not parent:
        return result
    try:
        commercial_quote = quote_parent_gallery(
            db, gallery=parent, quantity=len(selections)
        )
    except GalleryPricingError as exc:
        result["pricing_error"] = str(exc)
        return result
    photos = {
        photo.id: photo
        for photo in db.scalars(
            select(PhotoAsset).where(
                PhotoAsset.id.in_([item.photo_asset_id for item in selections])
            )
        )
    }
    result.update(
        {
            "items": [
                {
                    "id": str(item.photo_asset_id),
                    "name": photos[item.photo_asset_id].display_name
                    or photos[item.photo_asset_id].filename,
                }
                for item in selections
                if item.photo_asset_id in photos
            ],
            "unit_price_cents": commercial_quote.quote.active_tier.unit_price_cents,
            "total_cents": commercial_quote.quote.total_cents,
            "base_total_cents": commercial_quote.quote.base_total_cents,
            "savings_cents": commercial_quote.quote.savings_cents,
            "parcels": commercial_quote.snapshot["parcels"],
            "pricing_mode": parent.pricing_mode,
            "tier": {
                "minimum_quantity": commercial_quote.quote.active_tier.minimum_quantity,
                "maximum_quantity": commercial_quote.quote.active_tier.maximum_quantity,
            },
        }
    )
    return result


@app.get("/gallery/{gallery_id}/cart")
def client_cart(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Carrinho privado calculado no servidor para a cliente autorizada."""
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(
        db, gallery_id, session.subject_id, allow_deleted_origin=True
    )
    return _client_cart_payload(db, gallery, session.subject_id)


@app.post("/gallery/{gallery_id}/checkout", status_code=status.HTTP_201_CREATED)
def checkout_gallery(
    gallery_id: UUID, payload: CheckoutInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id)
    require_selection_window(gallery)
    client = db.get(Client, session.subject_id)
    if not client:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    try:
        order = create_pending_checkout(
            db, gallery=gallery, client=client, checkout_key=payload.idempotency_key
        )
        db.commit()
    except CheckoutError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "id": str(order.id),
        "payment_status": order.payment_status,
        "total_cents": order.total_cents,
    }


@app.post(
    "/gallery/{gallery_id}/orders/{order_id}/payment-communications",
    status_code=status.HTTP_201_CREATED,
)
def communicate_payment(
    gallery_id: UUID,
    order_id: UUID,
    payload: PaymentCommunicationInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id)
    order = db.scalar(
        select(SaleOrder).where(
            SaleOrder.id == order_id,
            SaleOrder.derived_gallery_id == gallery_id,
            SaleOrder.client_id == session.subject_id,
        )
    )
    if not order or order.payment_status != "pending":
        raise HTTPException(status_code=403, detail="Acesso negado.")
    existing = db.scalar(
        select(PaymentCommunication)
        .where(
            PaymentCommunication.sale_order_id == order.id,
            (
                (PaymentCommunication.idempotency_key == payload.idempotency_key)
                | (PaymentCommunication.status == "pending_review")
            ),
        )
        .order_by(PaymentCommunication.created_at.desc())
    )
    if existing:
        return {
            "id": str(existing.id),
            "status": existing.status,
            "message": "Comunicação aguardando revisão do fotógrafo.",
        }
    communication = PaymentCommunication(
        sale_order_id=order.id,
        client_id=session.subject_id,
        idempotency_key=payload.idempotency_key,
    )
    db.add(communication)
    db.flush()
    notification_state = "configuration_required"
    try:
        photographer_phone = configured_photographer_phone()
    except WhatsAppConfigurationError:
        photographer_phone = None
    if photographer_phone:
        db.add(
            PaymentNotificationOutbox(
                payment_communication_id=communication.id,
                recipient_phone=photographer_phone,
                template_kind="photographer_reported",
                idempotency_key=f"payment-reported:{communication.id}",
            )
        )
        notification_state = "queued"
    else:
        audit(db, "payment.notification_configuration_required", str(communication.id))
    audit(db, "payment.communication_reported", str(order.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(PaymentCommunication).where(
                PaymentCommunication.sale_order_id == order.id,
                PaymentCommunication.idempotency_key == payload.idempotency_key,
            )
        )
        if not existing:
            raise
        communication = existing
    return {
        "id": str(communication.id),
        "status": communication.status,
        "notification_status": notification_state,
        "message": "Comunicação aguardando revisão do fotógrafo.",
    }


@app.post("/admin/payment-communications/{communication_id}/decision")
def decide_payment_communication(
    communication_id: UUID,
    payload: PaymentDecisionInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    session = current_session(request, Role.ADMIN)
    communication = db.scalar(
        select(PaymentCommunication)
        .where(PaymentCommunication.id == communication_id)
        .with_for_update()
    )
    if not communication:
        raise HTTPException(status_code=404, detail="Comunicação não encontrada.")
    if communication.status != "pending_review":
        return {"status": communication.status}
    order = db.get(SaleOrder, communication.sale_order_id)
    if not order or order.payment_status != "pending":
        raise HTTPException(status_code=409, detail="Pedido indisponível para decisão.")
    communication.status = payload.decision
    communication.decided_by_admin_id = session.subject_id
    communication.decided_at = now()
    if payload.decision == "confirmed":
        order.payment_status = "confirmed"
        order.confirmed_at = communication.decided_at
    else:
        order.payment_status = "cancelled"
    client = db.get(Client, communication.client_id)
    if client and client.id == order.client_id:
        db.add(
            PaymentNotificationOutbox(
                payment_communication_id=communication.id,
                recipient_phone=client.phone_e164,
                template_kind=payload.decision,
                idempotency_key=f"payment-decision:{communication.id}:{payload.decision}",
            )
        )
    audit(db, f"payment.communication_{payload.decision}", str(communication.id))
    db.commit()
    return {"status": communication.status}


@app.put("/admin/payment-message-templates/{kind}")
def save_payment_template(
    kind: Literal["confirmed", "refused"],
    payload: PaymentTemplateInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_admin(request)
    try:
        body = validate_template(payload.body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    template = db.scalar(select(PaymentMessageTemplate).where(PaymentMessageTemplate.kind == kind))
    if template:
        template.body = body
    else:
        db.add(PaymentMessageTemplate(kind=kind, body=body))
    db.commit()
    return {"kind": kind, "body": body}


@app.get("/admin/payment-message-templates")
def list_payment_templates(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    configured = {
        template.kind: template.body for template in db.scalars(select(PaymentMessageTemplate))
    }
    return {
        "templates": {
            kind: configured.get(kind, default)
            for kind, default in DEFAULT_PAYMENT_TEMPLATES.items()
        },
        "allowed_variables": sorted(["cliente", "pedido", "galeria"]),
    }


@app.get("/admin/payment-communications")
def list_payment_communications(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    parent_gallery_id: UUID | None = Query(default=None),
    financial_status: Literal[
        "awaiting_payment", "reported", "confirmed", "not_found", "overdue"
    ]
    | None = Query(default=None),
    delivery_status: Literal["none", "queued", "processing", "sent", "failed"]
    | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    cursor: str | None = Query(default=None, max_length=500),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_admin(request)
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=422,
            detail="O início do período deve ser anterior ao fim.",
        )

    order_query = (
        select(SaleOrder, Client, DerivedGallery, ParentGallery)
        .outerjoin(Client, Client.id == SaleOrder.client_id)
        .outerjoin(DerivedGallery, DerivedGallery.id == SaleOrder.derived_gallery_id)
        .outerjoin(ParentGallery, ParentGallery.id == SaleOrder.parent_gallery_id_snapshot)
        .order_by(SaleOrder.created_at.desc(), SaleOrder.id.desc())
    )
    normalized_query = query.strip().lower() if query else ""
    if normalized_query:
        order_query = order_query.where(
            func.lower(
                func.coalesce(Client.full_name, SaleOrder.client_name_snapshot, "")
            ).like(f"%{normalized_query}%")
        )
    if parent_gallery_id:
        order_query = order_query.where(
            SaleOrder.parent_gallery_id_snapshot == parent_gallery_id
        )
    if created_from:
        order_query = order_query.where(SaleOrder.created_at >= created_from)
    if created_to:
        order_query = order_query.where(SaleOrder.created_at <= created_to)

    order_rows = list(db.execute(order_query))
    order_ids = [order.id for order, _client, _gallery, _parent in order_rows]
    communication_rows = (
        list(
            db.scalars(
                select(PaymentCommunication)
                .where(PaymentCommunication.sale_order_id.in_(order_ids))
                .order_by(
                    PaymentCommunication.created_at.desc(),
                    PaymentCommunication.id.desc(),
                )
            )
        )
        if order_ids
        else []
    )
    communications_by_order: dict[UUID, list[PaymentCommunication]] = defaultdict(list)
    for communication in communication_rows:
        communications_by_order[communication.sale_order_id].append(communication)

    communication_ids = [communication.id for communication in communication_rows]
    notification_rows = (
        list(
            db.scalars(
                select(PaymentNotificationOutbox)
                .where(
                    PaymentNotificationOutbox.payment_communication_id.in_(communication_ids)
                )
                .order_by(PaymentNotificationOutbox.created_at.desc())
            )
        )
        if communication_ids
        else []
    )
    notifications_by_communication: dict[UUID, list[PaymentNotificationOutbox]] = defaultdict(
        list
    )
    for notification in notification_rows:
        notifications_by_communication[notification.payment_communication_id].append(
            notification
        )

    max_attempts = payment_notification_max_attempts()
    prepared_orders: list[dict[str, object]] = []
    flat_by_id: dict[str, dict[str, object]] = {}
    for order, client, gallery, parent in order_rows:
        order_communications = communications_by_order.get(order.id, [])
        latest_communication = order_communications[0] if order_communications else None
        order_notifications = [
            notification
            for communication in order_communications
            for notification in notifications_by_communication.get(communication.id, [])
        ]
        financial_state = _payment_financial_status(order, latest_communication, gallery)
        delivery_states = {notification.status for notification in order_notifications} or {"none"}
        if financial_status and financial_state != financial_status:
            continue
        if delivery_status and delivery_status not in delivery_states:
            continue

        communication_payloads: list[dict[str, object]] = []
        for communication in order_communications:
            payload = _admin_payment_communication_payload(
                communication,
                order=order,
                client=client,
                gallery=gallery,
                notifications=notifications_by_communication.get(communication.id, []),
                max_attempts=max_attempts,
            )
            communication_payloads.append(payload)
            flat_by_id[str(communication.id)] = payload

        prepared_orders.append(
            {
                "id": str(order.id),
                "parent_gallery": {
                    "id": str(order.parent_gallery_id_snapshot),
                    "name": order.parent_gallery_name_snapshot,
                    "removed": parent is None or parent.lifecycle_status == "deleted",
                },
                "gallery": {
                    "id": str(order.derived_gallery_id_snapshot),
                    "name": order.derived_gallery_name_snapshot,
                    "removed": gallery is None,
                },
                "total_cents": order.total_cents,
                "financial_status": financial_state,
                "payment_status": order.payment_status,
                "created_at": order.created_at.isoformat(),
                "selection_expires_at": (
                    gallery.selection_expires_at.isoformat()
                    if gallery and gallery.selection_expires_at
                    else None
                ),
                "communications": communication_payloads,
                "communication": communication_payloads[0] if communication_payloads else None,
                "delivery_statuses": sorted(delivery_states),
                "_client_id": order.client_id,
                "_client_name": (
                    client.full_name
                    if client
                    else order.client_name_snapshot or "Cliente indisponível"
                ),
                "_sort_created_at": order.created_at,
            }
        )

    grouped: dict[UUID, dict[str, object]] = {}
    for order_payload in prepared_orders:
        client_id = order_payload.pop("_client_id")
        client_name = order_payload.pop("_client_name")
        sort_created_at = order_payload.pop("_sort_created_at")
        group = grouped.setdefault(
            client_id,
            {
                "client": {"id": str(client_id), "name": client_name},
                "totals": {"orders": 0, "total_cents": 0},
                "orders": [],
                "_sort_created_at": sort_created_at,
            },
        )
        group["orders"].append(order_payload)
        group["totals"]["orders"] += 1
        group["totals"]["total_cents"] += order_payload["total_cents"]
        group["_sort_created_at"] = max(group["_sort_created_at"], sort_created_at)

    all_groups = sorted(
        grouped.values(),
        key=lambda group: (group["_sort_created_at"], group["client"]["id"]),
        reverse=True,
    )
    cursor_key = _decode_payment_cursor(cursor) if cursor else None
    if cursor_key:
        all_groups = [
            group
            for group in all_groups
            if (
                group["_sort_created_at"].isoformat(),
                group["client"]["id"],
            )
            < cursor_key
        ]

    page_groups = all_groups[:limit]
    has_next_page = len(all_groups) > limit
    next_cursor = None
    if has_next_page and page_groups:
        last_group = page_groups[-1]
        next_cursor = _encode_payment_cursor(
            last_group["_sort_created_at"], last_group["client"]["id"]
        )
    for group in page_groups:
        group.pop("_sort_created_at", None)

    financial_counts: dict[str, int] = defaultdict(int)
    delivery_counts: dict[str, int] = defaultdict(int)
    parent_counts: dict[tuple[str, str], int] = defaultdict(int)
    total_cents = 0
    for order_payload in prepared_orders:
        financial_counts[order_payload["financial_status"]] += 1
        total_cents += order_payload["total_cents"]
        for state in order_payload["delivery_statuses"]:
            delivery_counts[state] += 1
        parent_gallery = order_payload["parent_gallery"]
        parent_counts[(parent_gallery["id"], parent_gallery["name"])] += 1

    page_communication_ids = {
        communication["id"]
        for group in page_groups
        for order_payload in group["orders"]
        for communication in order_payload["communications"]
    }
    return {
        "summary": {
            "clients": len(grouped),
            "orders": len(prepared_orders),
            "total_cents": total_cents,
            "financial_statuses": dict(financial_counts),
            "failed_messages": delivery_counts.get("failed", 0),
        },
        "facets": {
            "parent_galleries": [
                {"id": gallery_id, "name": name, "count": count}
                for (gallery_id, name), count in sorted(
                    parent_counts.items(), key=lambda item: item[0][1].lower()
                )
            ],
            "financial_statuses": dict(financial_counts),
            "delivery_statuses": dict(delivery_counts),
        },
        "groups": page_groups,
        "page": {"next_cursor": next_cursor, "limit": limit},
        "communications": [
            flat_by_id[communication_id]
            for communication_id in flat_by_id
            if communication_id in page_communication_ids
        ],
    }


def _payment_financial_status(
    order: SaleOrder,
    latest_communication: PaymentCommunication | None,
    gallery: DerivedGallery | None,
) -> str:
    if order.payment_status == "confirmed":
        return "confirmed"
    if order.payment_status == "cancelled":
        return "not_found"
    if latest_communication and latest_communication.status == "pending_review":
        return "reported"
    if gallery and gallery.selection_expires_at and expired(gallery.selection_expires_at):
        return "overdue"
    return "awaiting_payment"


def _admin_payment_communication_payload(
    item: PaymentCommunication,
    *,
    order: SaleOrder,
    client: Client | None,
    gallery: DerivedGallery | None,
    notifications: list[PaymentNotificationOutbox],
    max_attempts: int,
) -> dict[str, object]:
    photographer_delivery = next(
        (
            outbox
            for outbox in notifications
            if outbox.template_kind == "photographer_reported"
        ),
        None,
    )
    client_delivery = next(
        (
            outbox
            for outbox in notifications
            if outbox.template_kind in {"confirmed", "refused"}
        ),
        None,
    )
    return {
        "id": str(item.id),
        "status": item.status,
        "order_id": str(item.sale_order_id),
        "client_name": (
            client.full_name
            if client
            else order.client_name_snapshot or "Cliente indisponível"
        ),
        "gallery_name": order.derived_gallery_name_snapshot,
        "gallery_removed": gallery is None,
        "total_cents": order.total_cents,
        "created_at": item.created_at.isoformat(),
        "decided_at": item.decided_at.isoformat() if item.decided_at else None,
        "can_decide": item.status == "pending_review" and order.payment_status == "pending",
        "photographer_notification": _delivery_payload(
            photographer_delivery, max_attempts
        ),
        "client_notification": _delivery_payload(client_delivery, max_attempts),
    }


def _encode_payment_cursor(created_at: datetime, client_id: str) -> str:
    raw = json.dumps(
        {"created_at": created_at.isoformat(), "client_id": client_id},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_payment_cursor(cursor: str) -> tuple[str, str]:
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding).decode("utf-8"))
        created_at = datetime.fromisoformat(payload["created_at"])
        client_id = UUID(payload["client_id"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Cursor de pagamentos inválido.") from exc
    return created_at.isoformat(), str(client_id)


def _delivery_payload(
    outbox: PaymentNotificationOutbox | None, max_attempts: int
) -> dict[str, object] | None:
    if not outbox:
        return None
    return {
        "id": str(outbox.id),
        "status": outbox.status,
        "attempts": outbox.attempts,
        "last_error": (
            "Falha temporária de entrega."
            if outbox.status == "failed" and outbox.last_error
            else None
        ),
        "can_retry": outbox.status == "failed" and outbox.attempts < max_attempts,
    }


@app.post("/admin/payment-notifications/{notification_id}/retry")
def retry_payment_notification(
    notification_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    require_admin(request)
    outbox = db.get(PaymentNotificationOutbox, notification_id)
    if not outbox:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    if outbox.status != "failed" or outbox.attempts >= payment_notification_max_attempts():
        raise HTTPException(status_code=409, detail="Notificação indisponível para reenvio.")
    outbox.status = "queued"
    outbox.last_error = None
    outbox.updated_at = now()
    audit(db, "payment.notification_requeued", str(outbox.id))
    db.commit()
    return {"status": outbox.status}


@app.get("/gallery/{gallery_id}/payment-communications")
def client_payment_communications(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, object]]]:
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(
        db,
        gallery_id,
        session.subject_id,
        require_access_enabled=False,
        allow_deleted_origin=True,
    )
    orders = list(
        db.scalars(
            select(SaleOrder)
            .where(
                SaleOrder.derived_gallery_id == gallery_id,
                SaleOrder.client_id == session.subject_id,
            )
            .order_by(SaleOrder.created_at.desc())
        )
    )
    result = []
    for order in orders:
        communication = db.scalar(
            select(PaymentCommunication)
            .where(
                PaymentCommunication.sale_order_id == order.id,
                PaymentCommunication.client_id == session.subject_id,
            )
            .order_by(PaymentCommunication.created_at.desc())
        )
        delivery = None
        if communication and communication.status in {"confirmed", "refused"}:
            delivery = db.scalar(
                select(PaymentNotificationOutbox).where(
                    PaymentNotificationOutbox.payment_communication_id == communication.id,
                    PaymentNotificationOutbox.template_kind == communication.status,
                )
            )
        result.append(
            {
                "order_id": str(order.id),
                "total_cents": order.total_cents,
                "payment_status": order.payment_status,
                "created_at": order.created_at.isoformat(),
                "communication": (
                    {
                        "id": str(communication.id),
                        "status": communication.status,
                        "created_at": communication.created_at.isoformat(),
                        "decided_at": communication.decided_at.isoformat()
                        if communication.decided_at
                        else None,
                    }
                    if communication
                    else None
                ),
                "notification": (
                    {
                        "status": delivery.status,
                        "last_error": delivery.last_error,
                    }
                    if delivery
                    else None
                ),
            }
        )
    return {"orders": result}


@app.get("/gallery/{gallery_id}/orders/{order_id}")
def client_pending_order(
    gallery_id: UUID, order_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Entrega somente o snapshot PIX pendente à cliente proprietária."""
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id, allow_deleted_origin=True)
    order = db.scalar(
        select(SaleOrder).where(
            SaleOrder.id == order_id,
            SaleOrder.derived_gallery_id == gallery_id,
            SaleOrder.client_id == session.subject_id,
        )
    )
    if not order:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    if order.payment_status != "pending":
        raise HTTPException(status_code=409, detail="Este pedido não está pendente de confirmação.")
    items = list(
        db.scalars(
            select(SaleOrderItem)
            .where(SaleOrderItem.sale_order_id == order.id)
            .order_by(SaleOrderItem.filename_snapshot)
        )
    )
    qr_data_url: str | None = None
    if order.pix_copy_paste_snapshot:
        try:
            qr_data_url = pix_qr_data_url(order.pix_copy_paste_snapshot)
        except PixCodeError:
            pass
    return {
        "id": str(order.id),
        "payment_status": order.payment_status,
        "total_cents": order.total_cents,
        "price_rule": order.price_rule_snapshot,
        "sales_message": order.sales_message_snapshot,
        "pix": {
            "copy_paste": order.pix_copy_paste_snapshot,
            "qr_code_payload": None,
            "qr_png_data_url": qr_data_url,
            "instructions": order.pix_instructions_snapshot,
            "confirmation": "A confirmação do pagamento é manual pelo fotógrafo.",
        },
        "items": [
            {
                "photo_id": str(item.photo_asset_id),
                "name": item.filename_snapshot,
                "unit_price_cents": item.unit_price_cents,
                "preview_url": f"/gallery/{gallery_id}/photos/{item.photo_asset_id}/preview",
            }
            for item in items
        ],
    }


@app.post("/gallery/{gallery_id}/photos/{photo_id}/favorite", status_code=status.HTTP_201_CREATED)
def favorite_photo(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id)
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    if not parent or not parent.favorites_enabled:
        raise HTTPException(
            status_code=403, detail="Favoritos não estão habilitados nesta galeria."
        )
    assigned_photo_for_gallery(db, gallery_id, photo_id)
    existing = db.scalar(
        select(PhotoFavorite).where(
            PhotoFavorite.derived_gallery_id == gallery_id,
            PhotoFavorite.photo_asset_id == photo_id,
            PhotoFavorite.client_id == session.subject_id,
        )
    )
    if not existing:
        db.add(
            PhotoFavorite(
                derived_gallery_id=gallery_id, photo_asset_id=photo_id, client_id=session.subject_id
            )
        )
        audit(db, "photo_favorite.created", str(gallery_id))
        db.commit()
    return {"status": "favorited"}


@app.delete(
    "/gallery/{gallery_id}/photos/{photo_id}/favorite", status_code=status.HTTP_204_NO_CONTENT
)
def unfavorite_photo(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id)
    favorite = db.scalar(
        select(PhotoFavorite).where(
            PhotoFavorite.derived_gallery_id == gallery_id,
            PhotoFavorite.photo_asset_id == photo_id,
            PhotoFavorite.client_id == session.subject_id,
        )
    )
    if favorite:
        db.delete(favorite)
        audit(db, "photo_favorite.removed", str(gallery_id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/gallery/{gallery_id}/photos/{photo_id}/comments", status_code=status.HTTP_201_CREATED)
def create_photo_comment(
    gallery_id: UUID,
    photo_id: UUID,
    payload: PhotoCommentInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id)
    parent = db.get(ParentGallery, gallery.parent_gallery_id)
    if not parent or not parent.comments_enabled:
        raise HTTPException(
            status_code=403, detail="Comentários não estão habilitados nesta galeria."
        )
    assigned_photo_for_gallery(db, gallery_id, photo_id)
    comment = PhotoComment(
        derived_gallery_id=gallery_id,
        photo_asset_id=photo_id,
        client_id=session.subject_id,
        body=payload.body.strip(),
    )
    db.add(comment)
    db.flush()
    audit(db, "photo_comment.created", str(comment.id))
    db.commit()
    return {"id": str(comment.id)}


@app.get("/gallery/{gallery_id}/comments")
def client_comments(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id, allow_deleted_origin=True)
    comments = db.scalars(
        select(PhotoComment)
        .where(
            PhotoComment.derived_gallery_id == gallery_id,
            PhotoComment.client_id == session.subject_id,
            PhotoComment.removed_at.is_(None),
        )
        .order_by(PhotoComment.created_at.asc())
    )
    return {
        "comments": [
            {"id": str(comment.id), "photo_id": str(comment.photo_asset_id), "body": comment.body}
            for comment in comments
        ]
    }


@app.delete("/gallery/{gallery_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_own_comment(
    gallery_id: UUID, comment_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id)
    comment = db.scalar(
        select(PhotoComment).where(
            PhotoComment.id == comment_id,
            PhotoComment.derived_gallery_id == gallery_id,
            PhotoComment.client_id == session.subject_id,
            PhotoComment.removed_at.is_(None),
        )
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comentário não encontrado.")
    comment.removed_at = now()
    audit(db, "photo_comment.removed_by_client", str(comment.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/admin/derived-galleries/{gallery_id}/comments")
def admin_comments(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    require_admin(request)
    if not db.get(DerivedGallery, gallery_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    comments = db.scalars(
        select(PhotoComment)
        .where(PhotoComment.derived_gallery_id == gallery_id, PhotoComment.removed_at.is_(None))
        .order_by(PhotoComment.created_at.asc())
    )
    return {
        "comments": [
            {
                "id": str(comment.id),
                "photo_id": str(comment.photo_asset_id),
                "body": comment.body,
            }
            for comment in comments
        ]
    }


@app.delete(
    "/admin/derived-galleries/{gallery_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_comment_as_admin(
    gallery_id: UUID, comment_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    require_admin(request)
    comment = db.scalar(
        select(PhotoComment).where(
            PhotoComment.id == comment_id,
            PhotoComment.derived_gallery_id == gallery_id,
            PhotoComment.removed_at.is_(None),
        )
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comentário não encontrado.")
    require_derived_gallery_mutable(db, gallery_id)
    comment.removed_at = now()
    audit(db, "photo_comment.removed_by_admin", str(comment.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
