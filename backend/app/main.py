"""API de autenticação unificada do Pick-your-Pic."""

from __future__ import annotations

import asyncio
import base64
import csv
import json
import logging
import re
import secrets
import unicodedata
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html import escape
from io import BytesIO, StringIO
from os import getenv
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote, urlencode
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from PIL import Image, ImageOps
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from sqlalchemy import String, and_, cast, delete, func, literal, or_, select, union_all, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
)

from app import credit_history, media_archive_billing, photographer_credits
from app.acervo_context import (
    client_tenant_id,
    namespaced_upload_key,
    owned_record,
    require_active_owner,
)
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
    AdminSecurityConfigurationError,
    consume_admin_action_token,
    invalidate_admin_security_material,
)
from app.asset_removal import (
    delete_private_records,
    enqueue_file_cleanup,
    historical_paths,
    lock_removal_clients,
    preserve_asset_history,
    process_file_cleanup,
    removed_movements_page,
    removed_movements_payload,
)
from app.auth import (
    AdminActionToken,
    AdminPasswordInput,
    AdminSecurityChallenge,
    AdminTotpRecoveryCode,
    AdminTotpRecoveryCodesInput,
    AdminTotpVerification,
    AdminUser,
    AuthChallenge,
    AuthSession,
    BrandingSettings,
    ChallengeResendInput,
    ChallengeVerification,
    Client,
    ClientChallengeInput,
    ClientDeletionReceipt,
    ClientPhone,
    CommercialHistoryMedia,
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    DerivedGalleryPhotoOrigin,
    EmailDelivery,
    FacialJob,
    FolderClientGrant,
    FolderProcessingSettings,
    GalleryAccessCapability,
    GalleryClientState,
    GalleryLifecycleOperation,
    GalleryMembershipNotificationOutbox,
    GalleryReopeningNotificationOutbox,
    GalleryReopeningRequest,
    MediaArchiveCycle,
    MediaArchiveNotice,
    MediaArchiveObject,
    MediaDerivative,
    MediaJob,
    MercadoPagoCreditPurchase,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    PaymentConfirmationCorrection,
    PaymentGroup,
    PaymentNotificationOutbox,
    PhotoAnalysis,
    PhotoAsset,
    PhotoComment,
    PhotoCreditOperation,
    PhotoFaceEmbedding,
    PhotoFavorite,
    PhotoFolder,
    PhotographerCreditEntry,
    PhotographerCreditPackage,
    PhotographerSignup,
    PhotographerTermsVersion,
    PhotoSelection,
    PhotoView,
    PlatformAdminEvent,
    PriceRule,
    PrivateUploadBatch,
    PrivateUploadBatchAsset,
    ProgressivePricingPreset,
    ProgressivePricingTier,
    ProviderPayment,
    PushSubscription,
    Role,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
    Tenant,
    TenantAdmin,
    WhatsAppDelivery,
    audit,
    challenge_fingerprint,
    client_auth_rate_limit,
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
    require_client_auth_tenant,
    resend_client_challenge,
    revoke_subject_sessions,
    token_hash,
    validate_admin_password,
)
from app.branding_context import branding_settings, branding_tenant_id, technical_branding
from app.canonical_selection import (
    CanonicalSelectionUnavailable,
    select_canonical_photo,
)
from app.capacity_observability.collector import CollectionBusy, get_capacity_snapshot
from app.capacity_observability.contracts import CapacitySnapshot
from app.checkout import (
    CheckoutError,
    client_photo_is_frozen,
    create_pending_checkout,
    freeze_pending_checkout,
    lock_client_commerce,
    remove_canonical_cart_selection,
    synchronize_editable_draft,
)
from app.client_commerce import (
    client_carts_by_gallery_payload,
    client_orders_by_gallery_payload,
    client_orders_payload,
    client_photo_states,
)
from app.client_identity import (
    ClientIdentityConflict,
    assert_phone_available,
    change_verified_phone,
    resolve_client_by_phone,
    verify_canonical_phone,
)
from app.client_lifecycle import (
    ClientDeletionBlocked,
    ClientLifecycleError,
    delete_client_operational_graph,
    deletion_inventory,
    list_client_directory,
    receipt_payload,
    remove_facial_reference_files,
)
from app.commercial_projection import build_commercial_projections, payment_capabilities
from app.commercial_removal import (
    CommercialRemovalBlocked,
    CommercialRemovalPreparationFailed,
    apply_commercial_removal_policy,
)
from app.email_delivery import (
    EmailConfigurationError,
    additional_public_app_origins,
    email_channel_payload,
    public_app_origin,
)
from app.facial.capacity import FacialSearchCapacityError
from app.facial.config import (
    FacialConfigurationError,
    facial_settings_from_environment,
)
from app.facial.indexing import (
    enqueue_gallery_backfill_page,
    reconcile_gallery_index,
)
from app.facial.jobs import FacialJobError
from app.facial.observability import (
    FACIAL_ADMISSION_COUNTER,
    collect_facial_metrics,
    evaluate_facial_alerts,
)
from app.facial.policy import (
    FacialPolicyDraft,
    FacialPolicyError,
    activate_policy,
    policy_payload,
    prepare_policy,
    read_policy,
    revoke_policy,
    suspend_policy,
)
from app.facial.purge import facial_cleanup_proof
from app.facial.reference_store import FacialReferenceError
from app.facial.rollout import (
    read_rollout,
    rollout_is_active,
    rollout_status_payload,
)
from app.facial.search import (
    FacialSearchError,
    authorize_search_candidate_selection,
    cancel_search_request,
    create_search_request,
    read_latest_search_result,
    read_search_result,
    reject_search_candidate,
    search_availability,
    search_request_payload,
    search_result_payload,
)
from app.facial.security import enforce_facial_search_rate_limit
from app.facial.status import (
    FacialStatusError,
    gallery_index_status,
    retry_all_failed_index_jobs,
    retry_failed_index_jobs,
)
from app.folder_access import (
    folder_browsing_clause,
    folder_effective_expiries_by_id,
    folder_effective_expiry,
    folder_media_access_by_id,
    folder_media_is_local,
    folder_media_state,
    folder_media_state_by_id,
    folder_media_states_by_id,
    folder_media_writes_allowed,
    folder_reopening_allowed,
    folder_selected_media_preview_allowed,
    gallery_media_writes_allowed,
    historical_folder_media_state_by_id,
    public_folder_deadline_renewable,
)
from app.folder_deadlines import validate_access_duration_days
from app.folder_processing_api import register_routes as register_folder_processing_routes
from app.gallery_access import (
    consume_gallery_capability,
    issue_gallery_capability,
    reconstruct_gallery_capability_token,
    resolve_gallery_capability,
    revoke_gallery_capability,
    rotate_gallery_capability,
    validate_gallery_capability_runtime_configuration,
)
from app.gallery_cover_readiness import gallery_cover_readiness
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
from app.global_pix import (
    apply_configuration,
    canonical_proposal,
    global_pix_settings,
    pix_payload,
    proposal_preview,
)
from app.historical_media import historical_media_path
from app.media import (
    derivatives_root,
    enqueue_derivatives,
    safe_derivative_path,
    safe_source_path,
)
from app.membership_notifications import (
    enqueue_membership_notification,
    mark_membership_notification_read,
)
from app.mercadopago_projection import (
    financial_fields as mercadopago_fields,
)
from app.mercadopago_projection import (
    financial_status as mercadopago_financial_status,
)
from app.mercadopago_projection import (
    mercadopago_for_orders,
)
from app.mercadopago_projection import (
    purchase_groups as mercadopago_purchase_groups,
)
from app.messaging import (
    WhatsAppConfigurationError,
    WhatsAppDeliveryError,
    payment_notification_max_attempts,
)
from app.notification_contract import DEFINITIONS as NOTIFICATION_DEFINITIONS
from app.notification_delivery import retry_payment_projection
from app.notification_events import (
    legacy_owned_photographer_phone,
    record_gallery_milestone,
    record_payment_event,
    record_restricted_folder_ready,
)
from app.notification_settings import (
    notification_savepoint,
    payment_template_bodies,
    payment_template_migration_sources,
    save_setting,
    setting_for,
    setting_payload,
)
from app.order_delivery import (
    delivery_payload,
    fulfillable_order_condition,
    lock_delivery_order,
    order_fulfillable,
    resend_delivery,
    set_delivery,
    validate_album_url,
)
from app.order_visibility import visible_sale_order_condition
from app.parent_registration import link_client_to_parent
from app.payment_availability import (
    PAYMENT_REQUIRED_MESSAGE,
    can_publish_gallery,
    lock_payment_account,
    payment_methods,
    require_payment_method,
)
from app.payment_templates import (
    DEFAULT_PAYMENT_TEMPLATES,
    preview_payment_template_migration,
    validate_template,
)
from app.pix import PixCodeError, pix_qr_data_url
from app.preview_adjustment.api import register_routes as register_preview_adjustment_routes
from app.preview_adjustment.service import presentation_path
from app.pricing import (
    PriceTier,
    PricingRuleError,
    has_downward_jump,
    progressive_quote,
    validate_tiers,
)
from app.private_derivation import (
    PrivateDerivationError,
    derive_client_selection,
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
from app.private_upload_batches import (
    batch_for,
    batch_payload,
    close_batch,
    close_folder_batch,
    create_batch,
    create_folder_batch,
    folder_batch_for,
)
from app.product_brand import PRODUCT_NAME
from app.provider_payment_history import cart_recovery_statuses
from app.public_gallery_access import (
    CanonicalPhotoAccessDenied,
    PublicGalleryAccessDenied,
    active_capability_by_id,
    apply_public_gallery_access,
    authorized_canonical_folders,
    authorized_canonical_photo,
    authorized_canonical_photos,
    client_otp_delivery_allowed,
    require_authorized_canonical_photo,
    require_public_gallery_browsing,
    safe_internal_return,
)
from app.public_origin import PublicOriginError
from app.public_origin import public_app_origin as validated_public_origin
from app.push_subscriptions import (
    INSTALLATION_COOKIE,
    detach_previous_identity,
    installation_key,
    push_enabled,
    revoke_installation,
    subscribe,
)
from app.push_subscriptions import (
    cipher as push_cipher,
)
from app.push_subscriptions import (
    fingerprint as push_fingerprint,
)
from app.storage_metrics import measure_owned_photo_storage
from app.tenancy import (
    TenantContextError,
    domain_session,
    require_admin_tenant,
)
from app.tenant_hosts import tenant_for_host
from app.totp_crypto import TotpSecretError
from app.totp_recovery import (
    create_recovery_codes,
    hash_recovery_code,
    recovery_code_selector,
    verify_recovery_code_hash,
)
from app.totp_verification import matching_unused_totp_step
from app.unified_checkout import (
    cart_payload,
    communication_join,
    communications_for_orders,
    finalize_selection,
    group_payload,
    lock_payment_scope,
    payment_scopes,
    prepare_group,
    report_group,
)
from app.whatsapp_binding import provider_for, webhook_owner
from app.whatsapp_channel import (
    channel_payload,
    channel_settings,
    configure_expected_phone,
    refresh_channel,
    start_channel_pairing,
)
from app.whatsapp_tenant_credentials import provision_tenant_credential
from app.whatsapp_webhook import process_whatsapp_webhook

app = FastAPI(title=f"{PRODUCT_NAME} API", version="0.2.0")
logger = logging.getLogger(__name__)


@app.exception_handler(RequestValidationError)
async def protect_credential_validation_input(request: Request, exc: RequestValidationError):
    if request.url.path.removeprefix("/api").startswith(("/admin/settings/payment-providers", "/library/mercadopago",
                                    "/mercadopago/", "/admin/platform/console", "/admin/platform/credit-grants",
                                    "/admin/platform/credit-packages", "/admin/platform/credit-purchases", "/auth/photographer-signup",
                                    "/auth/photographer-closure-identity", "/auth/photographer-access-recovery",
                                    "/admin/onboarding", "/admin/security/totp", "/admin/whatsapp/channel")):
        return JSONResponse({"detail": "Confira os dados da solicitação."}, status_code=422,
                            headers={"Cache-Control": "private, no-store"})
    return await request_validation_exception_handler(request, exc)


@app.middleware("http")
async def require_operational_tenant(request: Request, call_next):
    try:
        return await call_next(request)
    except TenantContextError:
        return JSONResponse(status_code=503, content={"detail": "Serviço indisponível."})


@app.middleware("http")
async def prevent_capacity_snapshot_caching(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/admin/capacity-observability":
        response.headers["Cache-Control"] = "no-store"
    return response


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


def branding_asset_path(key: str, *, tenant_id: UUID | None = None) -> Path:
    root = branding_root()
    if "\\" in key or ".." in Path(key).parts or Path(key).is_absolute():
        raise ValueError("Chave de ativo de marca inválida.")
    expected_parent = root
    if key.startswith("tenants/"):
        if tenant_id is None or not key.startswith(f"tenants/{tenant_id}/branding/"):
            raise ValueError("Chave de ativo de marca inválida.")
        expected_parent = root / "tenants" / str(tenant_id) / "branding"
    candidate = (root / key).resolve()
    if candidate.parent != expected_parent:
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


async def read_bounded_body(
    request: Request, *, max_bytes: int, error_detail: str
) -> bytes:
    """Lê upload em streaming sem alocar silenciosamente além do limite."""

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=413, detail=error_detail) from exc
        if declared < 0 or declared > max_bytes:
            raise HTTPException(status_code=413, detail=error_detail)
    payload = bytearray()
    async for chunk in request.stream():
        if len(payload) + len(chunk) > max_bytes:
            raise HTTPException(status_code=413, detail=error_detail)
        payload.extend(chunk)
    if not payload:
        raise HTTPException(status_code=413, detail=error_detail)
    return bytes(payload)


class ParentGalleryInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    event_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5_000)
    access_mode: str = Field(
        default="invite_only",
        pattern=r"^(standard|invite_only)$",
    )


class ParentGallerySettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    event_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5_000)
    active: bool | None = None
    access_mode: str | None = Field(
        default=None,
        pattern=r"^(standard|invite_only)$",
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
    upload_batch_id: UUID | None = None
    allow_duplicate_content: bool = False


class PhotographerCreditPackageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    credit_quantity: int = Field(ge=1, le=2_147_483_647)
    price_cents: int | None = Field(default=None, gt=0, le=2_147_483_647)
    currency_code: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    active: bool = False
    current_password: SecretStr
    totp_code: SecretStr

    @model_validator(mode="after")
    def validate_package_configuration(self):
        if (self.price_cents is None) != (self.currency_code is None):
            raise ValueError("Preço e moeda devem ser informados em conjunto.")
        if self.active and self.price_cents is None:
            raise ValueError("Pacote sem preço não pode ser ativado.")
        return self


class MediaArchiveRecoveryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration_days: Literal[7, 14, 30] = media_archive_billing.SELF_SERVICE_RECOVERY_DAYS
    idempotency_key: str = Field(min_length=1, max_length=200)


class PhotographerCreditGrantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    tenant_id: UUID
    quantity: int = Field(ge=1, le=2_147_483_647)
    idempotency_key: str = Field(min_length=1, max_length=240)
    reference: str = Field(min_length=1, max_length=240)
    current_password: SecretStr
    totp_code: SecretStr


class PhotographerCreditRevocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    tenant_id: UUID
    quantity: int = Field(ge=1, le=2_147_483_647)
    idempotency_key: str = Field(min_length=1, max_length=240)
    reference: str = Field(min_length=1, max_length=240)
    current_password: SecretStr
    totp_code: SecretStr


class PhotographerCreditReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    decision: Literal["release", "restrict"]
    reason: str = Field(min_length=1, max_length=500)
    current_password: SecretStr
    totp_code: SecretStr


FolderAccessDurationDays = Annotated[int, Field(ge=1), AfterValidator(validate_access_duration_days)]


class PhotoFolderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    access_duration_days: FolderAccessDurationDays


class PhotoFolderDeadlineInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_duration_days: FolderAccessDurationDays


class PhotoFolderRenameInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class GalleryClientAccessInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["active", "blocked"]


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
    watermark_opacity: int = Field(default=42, ge=10, le=100)
    watermark_position: Literal[
        "top-left",
        "top-center",
        "top-right",
        "middle-left",
        "middle-center",
        "middle-right",
        "bottom-left",
        "bottom-center",
        "bottom-right",
    ] = "middle-center"
    watermark_shadow: bool = True
    watermark_security_lines: bool = False

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
    create_empty_private: bool = False


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


class PhoneChangeChallengeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone_e164: str = Field(min_length=8, max_length=32)


class PhotoCommentInput(BaseModel):
    body: str = Field(min_length=1, max_length=2_000)


class CheckoutInput(BaseModel):
    idempotency_key: str = Field(min_length=12, max_length=128)


class PaymentCommunicationInput(BaseModel):
    idempotency_key: str = Field(min_length=12, max_length=128)


class PaymentDecisionInput(BaseModel):
    decision: Literal["confirmed", "refused"]
    payment_group_id: UUID | None = None


class PaymentCorrectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=12, max_length=128)
    payment_group_id: UUID | None = None


class GalleryReopeningRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=12, max_length=128)
    folder_id: UUID


class GalleryReopeningDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "refused"]
    access_duration_days: FolderAccessDurationDays | None = None

    @model_validator(mode="after")
    def require_future_expiry_for_approval(self):
        if self.decision == "approved" and self.access_duration_days is None:
            raise ValueError("Informe uma duração em dias para aprovar a reabertura.")
        if self.decision == "refused" and self.access_duration_days is not None:
            raise ValueError("A recusa não recebe um novo prazo.")
        return self


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
    model_config = ConfigDict(extra="forbid")

    copy_paste: str | None = Field(default=None, max_length=4_000, repr=False)
    qr_code_payload: str | None = Field(default=None, max_length=8_000, repr=False)
    receiver_name: str | None = Field(default=None, max_length=80, repr=False)
    receiver_city: str | None = Field(default=None, max_length=80, repr=False)
    instructions: str | None = Field(default=None, max_length=500, repr=False)


class GlobalPixChallengeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128, repr=False)
    configuration: PixCheckoutSettingsInput | None = Field(repr=False)


class GlobalPixConfirmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: UUID
    code: str = Field(pattern=r"^\d{6}$", repr=False)


class GalleryPricingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def reject_gallery_pix(cls, value):
        if isinstance(value, dict) and "pix" in value:
            raise ValueError("O PIX agora é global. Atualize a página e configure em Configurações.")
        return value

    pricing_mode: Literal["fixed", "progressive"] | None = None
    fixed_unit_price_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    progressive_pricing_preset_id: UUID | None = None
    confirm_legacy_conversion: bool = False
    tiers: list[PriceTierInput] = Field(default_factory=list, max_length=20)


class ParentGallerySalesInput(GalleryPricingInput):
    payment_required: bool = True
    sales_message: str | None = Field(default=None, max_length=5_000)
    favorites_enabled: bool = False
    comments_enabled: bool = False


class FacialPolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legal_notice_version: str = Field(min_length=1, max_length=80)
    legal_basis_reference: str = Field(min_length=1, max_length=200)
    retention_policy_version: str = Field(min_length=1, max_length=80)
    minor_policy_version: str = Field(min_length=1, max_length=80)
    model_version: str = Field(min_length=1, max_length=120)
    quality_version: str = Field(min_length=1, max_length=120)
    calibration_version: str = Field(min_length=1, max_length=120)
    similarity_threshold_milli: int = Field(ge=0, le=1000)


class FacialIndexRetryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_ids: list[UUID] = Field(min_length=1, max_length=100)


class AdminRecoveryRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class AdminSecurityCodeInput(BaseModel):
    challenge_id: UUID
    code: str = Field(pattern=r"^\d{6}$")


class AdminPasswordResetInput(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=1, max_length=128)
    second_factor_code: str | None = Field(default=None, min_length=6, max_length=64)


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
    with domain_session(SessionLocal) as db:
        yield db


DatabaseSession = Annotated[Session, Depends(db_session)]


def require_admin(request: Request) -> AuthSession:
    return current_session(request, Role.ADMIN)


def require_installation_operator(request: Request) -> None:
    from app.installation_operator import require_operator
    from app.system_monitor.access import require_owner

    session = require_admin(request)
    with SessionLocal() as db:
        require_owner(db, session.subject_id)
        require_operator(db, session.subject_id)


def directory_tenant_id(db: Session, request: Request) -> UUID:
    """Conta da sessão administrativa e vínculo atual, nunca um parâmetro externo."""
    session = require_admin(request)
    memberships = list(db.scalars(select(TenantAdmin.tenant_id).where(
        TenantAdmin.admin_user_id == session.subject_id, TenantAdmin.active.is_(True),
    ).limit(2)))
    if len(memberships) != 1 or memberships[0] != session.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    tenant = db.get(Tenant, memberships[0], populate_existing=True)
    if tenant is None or tenant.status != "active":
        raise HTTPException(status_code=403, detail="Acesso negado.")
    return tenant.id


def require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    try:
        expected = public_app_origin()
    except EmailConfigurationError:
        expected = str(request.base_url).rstrip("/")
    try:
        allowed_origins = {expected.rstrip("/"), *additional_public_app_origins()}
    except EmailConfigurationError as exc:
        raise HTTPException(status_code=403, detail="Origem da operação não autorizada.") from exc
    if origin.rstrip("/") not in allowed_origins:
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
    tenant_id: UUID,
    require_access_enabled: bool = True,
    allow_deleted_origin: bool = False,
) -> DerivedGallery:
    client = owned_record(db, Client, client_id, tenant_id=tenant_id)
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    if not client or not gallery or not client_has_operational_membership(
        db,
        gallery=gallery,
        client_id=client_id,
    ):
        raise HTTPException(status_code=403, detail="Acesso negado.")
    if require_access_enabled and not gallery.access_enabled:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
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


def require_parent_gallery_mutable(db: Session, parent_gallery_id: UUID, *, tenant_id: UUID) -> ParentGallery:
    """Recusa qualquer nova alteração depois que a exclusão foi iniciada."""

    parent = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    if parent.lifecycle_status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A Galeria pública está removida ou em exclusão e não aceita novas alterações.",
        )
    return parent


def require_derived_gallery_mutable(
    db: Session, gallery_id: UUID, *, tenant_id: UUID, allow_deleted_origin: bool = False
) -> DerivedGallery:
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    if not allow_deleted_origin:
        require_parent_gallery_mutable(db, gallery.parent_gallery_id, tenant_id=tenant_id)
    return gallery


def assigned_photo_for_gallery(
    db: Session,
    gallery_id: UUID,
    photo_id: UUID,
    *,
    tenant_id: UUID,
    client_id: UUID,
    allow_expired: bool = False,
) -> None:
    require_active_owner(db, tenant_id)
    private_owned = db.scalar(
        select(PhotoAsset.id)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(
            PhotoAsset.id == photo_id,
            PhotoAsset.tenant_id == tenant_id,
            PhotoFolder.tenant_id == tenant_id,
            PhotoAsset.derived_gallery_id == gallery_id,
            PhotoFolder.derived_gallery_id == gallery_id,
            PhotoFolder.status == "released",
            PhotoFolder.purpose == "content",
            True if allow_expired else folder_browsing_clause(client_id),
        )
    )
    if private_owned:
        return
    assigned = db.scalar(
        select(DerivedGalleryPhoto)
        .join(PhotoAsset, PhotoAsset.id == DerivedGalleryPhoto.photo_asset_id)
        .outerjoin(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(
            DerivedGalleryPhoto.derived_gallery_id == gallery_id,
            DerivedGalleryPhoto.tenant_id == tenant_id,
            PhotoAsset.tenant_id == tenant_id,
            PhotoFolder.tenant_id == tenant_id,
            DerivedGalleryPhoto.photo_asset_id == photo_id,
            PhotoFolder.status == "released",
            PhotoFolder.purpose == "content",
            True if allow_expired else folder_browsing_clause(client_id),
        )
    )
    if not assigned:
        raise HTTPException(status_code=404, detail="Foto não encontrada na galeria.")


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


def _client_journey_destination(db: Session, client_id: UUID, *, tenant_id: UUID) -> str:
    """Resolve uma única origem sem expor a privada automática como destino concorrente."""

    require_client_auth_tenant(db, tenant_id)
    if not db.scalar(select(Client.id).where(Client.id == client_id, Client.tenant_id == tenant_id)):
        raise HTTPException(status_code=403, detail="Acesso negado.")
    active_parent_ids = set(
        db.scalars(
            select(ParentGalleryRegistration.parent_gallery_id).where(
                ParentGalleryRegistration.tenant_id == tenant_id,
                ParentGalleryRegistration.client_id == client_id,
                ParentGalleryRegistration.status == "active",
            )
        )
    )
    private_by_parent = {
        gallery.parent_gallery_id: gallery
        for gallery in operational_galleries_for_client(db, client_id=client_id)
        if gallery.tenant_id == tenant_id
    }
    blocked_parent_ids = set(
        db.scalars(
            select(DerivedGalleryMembership.parent_gallery_id).where(
                DerivedGalleryMembership.tenant_id == tenant_id,
                DerivedGalleryMembership.client_id == client_id,
                DerivedGalleryMembership.status == "blocked",
            )
        )
    )
    origin_ids = active_parent_ids | set(private_by_parent) | blocked_parent_ids
    if len(origin_ids) != 1:
        return "/library"

    parent_id = next(iter(origin_ids))
    if parent_id not in blocked_parent_ids and parent_id in active_parent_ids:
        parent = db.get(ParentGallery, parent_id)
        if parent and parent.tenant_id == tenant_id and parent.active and parent.lifecycle_status == "active":
            return f"/public-galleries/{parent.id}"

    private_gallery = private_by_parent.get(parent_id)
    if private_gallery:
        return f"/gallery/{private_gallery.id}"
    return "/library"






@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.post("/internal/whatsapp/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(db_session)) -> dict[str, str]:
    provided = request.headers.get("X-Markina-Webhook-Secret", "")
    content_length = request.headers.get("content-length")
    if content_length and (not content_length.isdigit() or int(content_length) > 65_536):
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
    try:
        owner = webhook_owner(db, payload, provided)
    except WhatsAppConfigurationError:
        raise HTTPException(status_code=403, detail="Evento não autorizado.") from None
    _changed, outcome = process_whatsapp_webhook(db, payload, tenant_id=owner)
    return {"status": outcome}


def whatsapp_admin_payload(db: Session, settings) -> dict:
    payload = channel_payload(db, settings)
    payload["deliveries"] = {
        delivery_status: count
        for delivery_status, count in db.execute(
            select(WhatsAppDelivery.status, func.count())
            .where(WhatsAppDelivery.tenant_id == settings.tenant_id)
            .group_by(WhatsAppDelivery.status)
            .order_by(WhatsAppDelivery.status)
        )
    }
    return payload


@app.get("/admin/whatsapp/channel")
def admin_whatsapp_channel(request: Request, db: Session = Depends(db_session)) -> dict:
    owner = directory_tenant_id(db, request)
    try:
        provider = provider_for(db, tenant_id=owner)
        settings = refresh_channel(db, provider, tenant_id=owner)
    except (WhatsAppConfigurationError, WhatsAppDeliveryError):
        settings = channel_settings(db, tenant_id=owner)
        settings.status = "error"
        settings.last_error = "Configuração ou conexão do canal indisponível."
        settings.last_checked_at = now()
        db.commit()
    return whatsapp_admin_payload(db, settings)


@app.post("/admin/whatsapp/channel/provision")
def provision_admin_whatsapp_channel(
    payload: WhatsAppChannelInput,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
) -> dict:
    require_same_origin(request)
    session = require_admin(request)
    owner = directory_tenant_id(db, request)
    signup = db.scalar(select(PhotographerSignup.id).where(
        PhotographerSignup.reserved_admin_id == session.subject_id,
        PhotographerSignup.activated_tenant_id == owner,
        PhotographerSignup.state == "active",
    ))
    if not signup:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    try:
        credential, settings, provider = provision_tenant_credential(
            db, tenant_id=owner, expected_phone_e164=payload.expected_phone_e164,
        )
        db.commit()  # Persiste identidade idempotente antes de chamar o serviço remoto.
        db.refresh(credential)
        from app.auth import WhatsAppTenantCredential

        locked = db.scalar(select(WhatsAppTenantCredential).where(
            WhatsAppTenantCredential.id == credential.id,
            WhatsAppTenantCredential.tenant_id == owner,
        ).with_for_update())
        if locked is None:
            raise WhatsAppConfigurationError("Instância WhatsApp indisponível.")
        provider = provider_for(db, tenant_id=owner)
        provider.ensure_instance()
        settings.status = "pending_pairing"
        settings.last_error = None
        settings.last_checked_at = now()
        audit(db, "whatsapp.tenant_instance_provisioned", str(settings.id), tenant_id=owner)
        db.commit()
        response.headers["Cache-Control"] = "private, no-store"
        return whatsapp_admin_payload(db, settings)
    except (WhatsAppConfigurationError, WhatsAppDeliveryError):
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Não foi possível preparar o canal WhatsApp. Tente novamente.",
            headers={"Cache-Control": "private, no-store"},
        ) from None


@app.patch("/admin/whatsapp/channel")
def update_admin_whatsapp_channel(
    payload: WhatsAppChannelInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict:
    owner = directory_tenant_id(db, request)
    try:
        settings = configure_expected_phone(db, payload.expected_phone_e164, tenant_id=owner)
    except WhatsAppConfigurationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return whatsapp_admin_payload(db, settings)


@app.post("/admin/whatsapp/channel/refresh")
def refresh_admin_whatsapp_channel(request: Request, db: Session = Depends(db_session)) -> dict:
    owner = directory_tenant_id(db, request)
    try:
        settings = refresh_channel(db, provider_for(db, tenant_id=owner), tenant_id=owner)
    except (WhatsAppConfigurationError, WhatsAppDeliveryError):
        raise HTTPException(status_code=503, detail="Não foi possível consultar o canal.") from None
    return whatsapp_admin_payload(db, settings)


@app.post("/admin/whatsapp/channel/pairing")
def pair_admin_whatsapp_channel(
    request: Request, response: Response, db: Session = Depends(db_session)
) -> dict:
    owner = directory_tenant_id(db, request)
    response.headers["Cache-Control"] = "no-store"
    try:
        settings, pairing = start_channel_pairing(db, provider_for(db, tenant_id=owner), tenant_id=owner)
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
    owner = directory_tenant_id(db, request)
    query = select(WhatsAppDelivery).where(WhatsAppDelivery.tenant_id == owner).order_by(WhatsAppDelivery.created_at.desc()).limit(100)
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
    owner = directory_tenant_id(db, request)
    delivery = owned_record(db, WhatsAppDelivery, delivery_id, tenant_id=owner)
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
    audit(db, "whatsapp.delivery_requeued", f"{delivery.id}:{session.subject_id}", tenant_id=owner)
    db.commit()
    return {"status": "queued"}


def client_link_context(
    db: Session, request: Request, access_token: str | None,
) -> tuple[UUID, GalleryAccessCapability | None, ParentGallery | None]:
    """Somente capacidade opaca ou sessão própria define a conta cliente."""
    if not access_token:
        try:
            session = current_session(request, Role.CLIENT)
        except HTTPException as exc:
            raise neutral_error() from exc
        require_client_auth_tenant(db, session.tenant_id)
        return session.tenant_id, None, None
    capability = resolve_gallery_capability(db, access_token)
    if not capability or capability.scope not in {
        "public_gallery", "parent_invite", "private_invite",
        "private_client_invite", "private_gallery_link",
    }:
        raise neutral_error()
    return capability.tenant_id, capability, validate_client_capability_context(db, capability)


def validate_client_capability_context(
    db: Session, capability: GalleryAccessCapability,
) -> ParentGallery:
    require_client_auth_tenant(db, capability.tenant_id)
    parent = db.scalar(select(ParentGallery).where(
        ParentGallery.id == capability.parent_gallery_id,
        ParentGallery.tenant_id == capability.tenant_id,
    ))
    private = db.scalar(select(DerivedGallery).where(
        DerivedGallery.id == capability.derived_gallery_id,
        DerivedGallery.tenant_id == capability.tenant_id,
        DerivedGallery.parent_gallery_id == capability.parent_gallery_id,
    )) if capability.derived_gallery_id else None
    private_context = bool(
        capability.scope in {"private_invite", "private_client_invite", "private_gallery_link"}
        and private and private.access_enabled
        and (capability.scope == "private_gallery_link" or private.client_id == capability.client_id)
        and parent and parent.lifecycle_status in {"active", "deleted"}
    )
    if not parent or (not private_context and (
        not parent.active or parent.lifecycle_status != "active"
        or capability.scope in {"private_invite", "private_client_invite", "private_gallery_link"}
    )):
        raise neutral_error()
    return parent


def client_challenge_context(
    db: Session, request: Request, challenge_id: UUID, access_token: str | None,
    parent_gallery_id: UUID | None = None,
) -> UUID:
    if not access_token and parent_gallery_id:
        challenge = db.scalar(select(AuthChallenge).where(
            AuthChallenge.id == challenge_id,
            AuthChallenge.kind == "client_otp",
            AuthChallenge.parent_gallery_id == parent_gallery_id,
        ).with_for_update())
        if not challenge or not challenge.subject:
            raise neutral_error()
        parent = _active_client_reauthentication_parent(db, parent_gallery_id, challenge.tenant_id)
        if not _registered_client_for_gallery(db, parent, challenge.subject):
            raise neutral_error()
        return challenge.tenant_id

    if not access_token:
        challenge = db.scalar(select(AuthChallenge).where(
            AuthChallenge.id == challenge_id,
            AuthChallenge.kind == "client_otp",
        ).with_for_update())
        if challenge and _purchase_return_order_id(challenge.return_to):
            tenant = tenant_for_host(db, request.headers.get("host"))
            if (not tenant or tenant.id != challenge.tenant_id or not challenge.subject
                    or not _client_has_verified_phone(db, tenant_id=tenant.id, phone=challenge.subject)):
                raise neutral_error()
            return tenant.id

    tenant_id, presented, _parent = client_link_context(db, request, access_token)
    challenge = db.scalar(select(AuthChallenge).where(
        AuthChallenge.id == challenge_id, AuthChallenge.tenant_id == tenant_id,
        AuthChallenge.kind == "client_otp",
    ).with_for_update())
    if not challenge:
        raise neutral_error()
    if challenge.gallery_capability_id:
        original = active_capability_by_id(db, challenge.gallery_capability_id)
        if not original or original.tenant_id != tenant_id:
            raise neutral_error()
        if presented is not None and presented.id != original.id:
            raise neutral_error()
        validate_client_capability_context(db, original)
    if parent_gallery_id and challenge.parent_gallery_id != parent_gallery_id:
        raise neutral_error()
    return tenant_id


def _purchase_return_order_id(value: str | None) -> UUID | None:
    prefix = "/library/purchases#order-"
    if not isinstance(value, str) or not value.startswith(prefix):
        return None
    try:
        order_id = UUID(value.removeprefix(prefix))
    except (ValueError, AttributeError):
        return None
    return order_id if value == f"{prefix}{order_id}" else None


def _purchase_return_destination(db: Session, value: str | None, *, tenant_id: UUID,
                                 client_id: UUID) -> str:
    order_id = _purchase_return_order_id(value)
    if not order_id:
        return "/library"
    order = db.scalar(select(SaleOrder.id).where(
        SaleOrder.id == order_id,
        SaleOrder.tenant_id == tenant_id,
        SaleOrder.client_id == client_id,
    ))
    return f"/library/purchases#order-{order_id}" if order else "/library"


def _client_has_verified_phone(db: Session, *, tenant_id: UUID, phone: str) -> bool:
    return bool(db.scalar(select(ClientPhone.id).where(
        ClientPhone.tenant_id == tenant_id,
        ClientPhone.phone_e164 == phone,
        ClientPhone.active.is_(True),
        ClientPhone.verified_at.is_not(None),
    )))


def _active_client_reauthentication_parent(
    db: Session, parent_gallery_id: UUID, tenant_id: UUID | None = None,
) -> ParentGallery:
    parent = db.scalar(select(ParentGallery).where(
        ParentGallery.id == parent_gallery_id,
        ParentGallery.active.is_(True),
        ParentGallery.lifecycle_status == "active",
        ParentGallery.access_mode.in_(("standard", "invite_only")),
    ))
    if not parent or (tenant_id is not None and parent.tenant_id != tenant_id):
        raise neutral_error()
    require_client_auth_tenant(db, parent.tenant_id)
    return parent


def _registered_client_for_gallery(
    db: Session, parent: ParentGallery, phone: str,
) -> Client | None:
    try:
        client = resolve_client_by_phone(db, phone, tenant_id=parent.tenant_id)
    except ClientIdentityConflict:
        return None
    if not client:
        return None
    try:
        require_public_gallery_browsing(
            db, parent_gallery_id=parent.id, client_id=client.id,
        )
    except PublicGalleryAccessDenied:
        return None
    return client


@app.post("/auth/client/challenge", status_code=status.HTTP_202_ACCEPTED)
def client_challenge(
    payload: ClientLinkChallengeInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str | bool]:
    phone = normalize_e164(payload.phone)
    client_name = " ".join((payload.full_name or "").split())
    # Proteção global precede resolução para cobrir também links inválidos.
    ip_address = request.client.host if request.client else "unknown"
    enforce_rate_limit(db, "client_otp.entry", pii_fingerprint(phone), ip_address)
    purchase_reauthentication = (
        not payload.access_token and not payload.parent_gallery_id
        and _purchase_return_order_id(payload.return_to) is not None
    )
    if purchase_reauthentication:
        tenant = tenant_for_host(db, request.headers.get("host"))
        if not tenant:
            audit(db, "client_otp.context_rejected", "invalid")
            db.commit()
            return {"challenge_id": str(uuid4()),
                    "message": "Se os dados puderem receber acesso, enviaremos um código pelo WhatsApp."}
        tenant_id, capability, parent = tenant.id, None, None
    else:
        if len(client_name) < 3:
            raise HTTPException(status_code=422, detail="Informe o nome completo.")
    contextual_reauthentication = not payload.access_token and payload.parent_gallery_id is not None
    if purchase_reauthentication:
        pass
    elif contextual_reauthentication:
        try:
            parent = _active_client_reauthentication_parent(db, payload.parent_gallery_id)
        except HTTPException:
            audit(db, "client_otp.context_rejected", "invalid")
            db.commit()
            return {
                "challenge_id": str(uuid4()),
                "message": "Se os dados puderem receber acesso, enviaremos um código pelo WhatsApp.",
            }
        tenant_id, capability = parent.tenant_id, None
    else:
        try:
            tenant_id, capability, parent = client_link_context(db, request, payload.access_token)
            if payload.parent_gallery_id and (not parent or payload.parent_gallery_id != parent.id):
                raise neutral_error()
        except HTTPException:
            audit(db, "client_otp.context_rejected", "invalid")
            db.commit()
            raise
    client_auth_rate_limit(db, "client_otp.challenge", pii_fingerprint(phone), ip_address,
                                tenant_id=tenant_id,
                            )
    if purchase_reauthentication:
        try:
            client = resolve_client_by_phone(db, phone, tenant_id=tenant_id)
        except ClientIdentityConflict:
            client = None
        if not client or not _client_has_verified_phone(db, tenant_id=tenant_id, phone=phone):
            audit(db, "client_otp.context_rejected", "invalid", tenant_id=tenant_id)
            db.commit()
            return {"challenge_id": str(uuid4()),
                    "message": "Se os dados puderem receber acesso, enviaremos um código pelo WhatsApp."}
    if contextual_reauthentication and not _registered_client_for_gallery(db, parent, phone):
        audit(db, "client_otp.context_rejected", "invalid", tenant_id=tenant_id)
        db.commit()
        return {
            "challenge_id": str(uuid4()),
            "message": "Se os dados puderem receber acesso, enviaremos um código pelo WhatsApp.",
            "show_private_gallery_notice": parent.access_mode == "invite_only",
        }
    deliver = (True if purchase_reauthentication else
               client_otp_delivery_allowed(db, parent=parent, phone_e164=phone, capability=capability))
    challenge, code = create_challenge(
        db, "client_otp", phone, code=None if deliver else secrets.token_urlsafe(32),
        tenant_id=tenant_id, client_name=None if purchase_reauthentication else client_name,
        parent_gallery_id=parent.id if parent else None,
        gallery_capability_id=capability.id if capability else None,
        return_to=(
            f"/public-galleries/{parent.id}"
            if contextual_reauthentication and parent
            else (f"/library/purchases#order-{_purchase_return_order_id(payload.return_to)}"
                  if purchase_reauthentication else safe_internal_return(payload.return_to, "/library"))
            if payload.return_to or contextual_reauthentication else None
        ),
    )
    if deliver:
        enqueue_client_otp_delivery(db, challenge, code)
    else:
        audit(db, "client_otp.delivery_suppressed", challenge_fingerprint(challenge),
              tenant_id=tenant_id)
        db.commit()
    return {
        "challenge_id": str(challenge.id),
        "message": "Se os dados puderem receber acesso, enviaremos um código pelo WhatsApp.",
        "show_private_gallery_notice": bool(parent and parent.access_mode == "invite_only"),
    }


@app.post("/auth/client/resend", status_code=status.HTTP_202_ACCEPTED)
def client_resend(
    payload: ChallengeResendInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    try:
        tenant_id = client_challenge_context(
            db, request, payload.challenge_id, payload.access_token, payload.parent_gallery_id,
        )
    except HTTPException:
        if not payload.access_token and payload.parent_gallery_id:
            return {"message": "Se os dados puderem receber acesso, enviaremos um novo código."}
        raise
    challenge = db.get(AuthChallenge, payload.challenge_id)
    parent = db.get(ParentGallery, challenge.parent_gallery_id) if challenge.parent_gallery_id else None
    capability = active_capability_by_id(db, challenge.gallery_capability_id)
    deliver = bool(challenge.subject) and client_otp_delivery_allowed(
        db, parent=parent, phone_e164=challenge.subject, capability=capability,
    )
    resend_client_challenge(
        db, payload.challenge_id, request.client.host if request.client else "unknown",
        tenant_id=tenant_id, deliver=deliver,
    )
    return {"message": "Se os dados puderem receber acesso, enviaremos um novo código."}


@app.post("/auth/client/verify")
def client_verify(
    payload: ChallengeVerification, response: Response, request: Request,
    db: Session = Depends(db_session)
) -> dict[str, str]:
    tenant_id = client_challenge_context(
        db, request, payload.challenge_id, payload.access_token, payload.parent_gallery_id,
    )
    pending = db.get(AuthChallenge, payload.challenge_id)
    client_auth_rate_limit(db, "client_otp.verify", challenge_fingerprint(pending),
                           request.client.host if request.client else "unknown", tenant_id=tenant_id)
    challenge = consume_challenge(db, payload.challenge_id, "client_otp", payload.code,
                                        tenant_id=tenant_id,
                                    )
    phone = challenge.subject
    fingerprint = challenge_fingerprint(challenge)
    if not phone:
        audit(db, "client_otp.minimized_challenge_rejected", str(challenge.id), tenant_id=tenant_id)
        db.commit()
        raise neutral_error()
    try:
        client = resolve_client_by_phone(db, phone, tenant_id=challenge.tenant_id)
    except ClientIdentityConflict as exc:
        audit(db, "client_otp.identity_conflict", fingerprint, tenant_id=tenant_id)
        minimize_client_challenge_pii(db, challenge)
        db.commit()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    parent_gallery = (
        db.get(ParentGallery, challenge.parent_gallery_id) if challenge.parent_gallery_id else None
    )
    purchase_reauthentication = _purchase_return_order_id(challenge.return_to) is not None
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
            audit(db, "client_otp.unlinked_denied", fingerprint, tenant_id=tenant_id)
            minimize_client_challenge_pii(db, challenge)
            db.commit()
            if purchase_reauthentication:
                raise neutral_error()
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
                    tenant_id=challenge.tenant_id,
                    full_name=challenge.client_name,
                    phone_e164=phone,
                )
                db.add(client)
                db.flush()
                db.add(
                    ClientPhone(
                        tenant_id=challenge.tenant_id,
                        client_id=client.id,
                        phone_e164=phone,
                        active=True,
                        verified_at=now(),
                    )
                )
                db.flush()
        except IntegrityError:
            client = resolve_client_by_phone(db, phone, tenant_id=challenge.tenant_id)
            if not client:
                raise
        audit(db, "client.created_from_gallery_link", str(client.id), tenant_id=tenant_id)
    try:
        verify_canonical_phone(db, client, phone, tenant_id=challenge.tenant_id)
    except ClientIdentityConflict as exc:
        audit(db, "client_otp.identity_conflict", fingerprint, tenant_id=tenant_id)
        minimize_client_challenge_pii(db, challenge)
        db.commit()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
                audit(db, "client_otp.private_invite_denied", str(capability.id), tenant_id=tenant_id)
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
                    str(registration.id), tenant_id=tenant_id)
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
                            str(existing_membership.id), tenant_id=tenant_id)
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
                            str(membership_result.membership.id), tenant_id=tenant_id)
                if not destination_gallery:
                    minimize_client_challenge_pii(db, challenge)
                    db.commit()
                    raise HTTPException(status_code=403, detail="Acesso não autorizado.")
            destination = safe_internal_return(
                challenge.return_to, f"/gallery/{destination_gallery.id}"
            )
            consume_gallery_capability(capability)
            audit(db, "private_gallery.invite_verified", str(destination_gallery.id), tenant_id=tenant_id)
        else:
            if (
                not parent_context
                or not parent_context.active
                or parent_context.lifecycle_status != "active"
            ):
                audit(db, "client_otp.gallery_context_rejected", fingerprint, tenant_id=tenant_id)
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
                audit(db, "client_otp.gallery_access_denied", str(parent_context.id), tenant_id=tenant_id)
                minimize_client_challenge_pii(db, challenge)
                db.commit()
                raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
            registration = access.registration or registration
            if registration:
                audit(
                    db,
                    "parent_gallery.registration_completed",
                    str(registration.id), tenant_id=tenant_id)
            destination = access.destination
            if capability and capability.scope == "parent_invite":
                consume_gallery_capability(capability)
                audit(db, "parent_gallery.invite_verified", str(capability.id), tenant_id=tenant_id)
        enqueue_membership_notification(
            db,
            event_key=f"client_logged_in:{challenge.id}",
            event_type="client_logged_in",
            parent=parent_context,
            gallery=(
                destination_gallery
                if capability
                and capability.scope
                in {"private_invite", "private_client_invite", "private_gallery_link"}
                else None
            ),
            client=client,
        )
        audit(
            db,
            "client.gallery_login_notified",
            f"client_id:{client.id};gallery_id:{parent_context.id}", tenant_id=tenant_id)
        record_gallery_milestone(
            db, kind="first_access", parent_gallery_id=parent_context.id, client_id=client.id,
            gallery=destination_gallery if capability and capability.scope in {
                "private_invite", "private_client_invite", "private_gallery_link"
            } else None,
        )
    elif purchase_reauthentication:
        destination = _purchase_return_destination(
            db, challenge.return_to, tenant_id=tenant_id, client_id=client.id,
        )
    else:
        destination = _client_journey_destination(db, client.id, tenant_id=tenant_id)
    minimize_client_challenge_pii(db, challenge)
    create_session(db, response, Role.CLIENT, client.id, tenant_id=tenant_id)
    detach_previous_identity(db, request, "client", client.id)
    audit(db, "client.redirected", str(client.id), tenant_id=tenant_id)
    db.commit()
    return {"destination": destination}


@app.post("/auth/admin/password", status_code=status.HTTP_202_ACCEPTED)
def admin_password(
    payload: AdminPasswordInput, request: Request, response: Response,
    db: Session = Depends(db_session)
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
    try:
        tenant = require_admin_tenant(db, admin.id, platform_scope=True)
    except TenantContextError as exc:
        audit(db, "admin_password.context_rejected", str(admin.id))
        db.commit()
        raise neutral_error() from exc
    signup_account = db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.reserved_admin_id == admin.id,
        PhotographerSignup.activated_tenant_id == tenant.id,
        PhotographerSignup.state == "active",
    ))
    from app.system_monitor.models import PlatformOwner
    owner_account = db.scalar(select(PlatformOwner.admin_user_id).where(PlatformOwner.admin_user_id == admin.id))
    if signup_account and not admin.totp_enabled and owner_account is None:
        create_session(db, response, Role.ADMIN, admin.id, tenant_id=tenant.id, platform_scope=True)
        detach_previous_identity(db, request, "admin", admin.id)
        audit(db, "admin.redirected", str(admin.id))
        db.commit()
        return {"destination": "/admin"}
    challenge, _ = create_challenge(db, "admin_totp", str(admin.id), tenant_id=tenant.id)
    return {"challenge_id": str(challenge.id), "message": "Continue com o código do autenticador."}


@app.post("/auth/admin/totp")
def admin_totp(
    payload: AdminTotpVerification,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    challenge = db.scalar(select(AuthChallenge).where(AuthChallenge.id == payload.challenge_id,
        AuthChallenge.kind == "admin_totp").with_for_update())
    if not challenge or not challenge.subject or challenge.used_at or expired(challenge.expires_at) or challenge.attempts >= 5:
        raise neutral_error()
    try:
        admin_id = UUID(challenge.subject)
        tenant = require_admin_tenant(db, admin_id, platform_scope=True)
        if challenge.tenant_id != tenant.id:
            raise TenantContextError("Acesso negado.")
    except (ValueError, TenantContextError) as exc:
        audit(db, "admin_totp.context_rejected", str(challenge.id))
        db.commit()
        raise neutral_error() from exc
    try:
        admin = db.scalar(select(AdminUser).where(AdminUser.id == admin_id).with_for_update())
    except TotpSecretError:
        db.rollback()
        audit(db, "admin_totp.key_unavailable", challenge.subject, tenant_id=tenant.id)
        db.commit()
        raise neutral_error() from None
    enforce_rate_limit(
        db, "admin_totp", challenge.subject, request.client.host if request.client else "unknown"
    )
    recovery_code = None
    matched_step = None
    if admin and admin.email_verified:
        if payload.code.isdigit():
            matched_step = matching_unused_totp_step(
                admin.totp_secret, payload.code, admin.totp_last_used_step, valid_window=1
            )
        else:
            recovery_codes = list(db.scalars(select(AdminTotpRecoveryCode).where(
                AdminTotpRecoveryCode.admin_user_id == admin.id,
                AdminTotpRecoveryCode.code_selector == recovery_code_selector(payload.code),
                AdminTotpRecoveryCode.used_at.is_(None),
                AdminTotpRecoveryCode.revoked_at.is_(None),
            ).order_by(AdminTotpRecoveryCode.id).with_for_update()))
            recovery_code = next((item for item in recovery_codes
                                  if verify_recovery_code_hash(item.code_hash, payload.code)), None)
    if matched_step is None and recovery_code is None:
        challenge.attempts += 1
        audit(db, "admin_totp.failed", challenge.subject, tenant_id=tenant.id)
        db.commit()
        raise neutral_error()
    challenge.used_at = now()
    if matched_step is not None:
        admin.totp_last_used_step = matched_step
    if recovery_code is not None:
        recovery_code.used_at = now()
        audit(db, "admin_totp_recovery.used", challenge.subject, tenant_id=tenant.id)
    audit(db, "admin_totp.validated", challenge.subject, tenant_id=tenant.id)
    create_session(db, response, Role.ADMIN, admin.id, tenant_id=tenant.id, platform_scope=True)
    detach_previous_identity(db, request, "admin", admin.id)
    audit(db, "admin.redirected", str(admin.id))
    db.commit()
    return {"destination": "/admin/platform" if tenant.lifecycle == "closed" else "/admin"}


@app.post("/admin/security/totp/recovery-codes")
def issue_admin_totp_recovery_codes(
    payload: AdminTotpRecoveryCodesInput,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    try:
        active_admin_for_session(db, session)
        admin = db.scalar(select(AdminUser).where(
            AdminUser.id == session.subject_id
        ).with_for_update())
    except (AdminAccountError, TotpSecretError):
        db.rollback()
        raise HTTPException(status_code=403, detail="Acesso negado.") from None
    if not admin or not admin.email_verified:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    enforce_rate_limit(
        db, "admin_totp_recovery_issue", str(admin.id),
        request.client.host if request.client else "unknown",
    )
    try:
        reauthenticate_admin(admin, payload.current_password)
        if payload.second_factor_code.isdigit():
            matched_step = matching_unused_totp_step(
                admin.totp_secret, payload.second_factor_code,
                admin.totp_last_used_step, valid_window=1,
            )
            if matched_step is None:
                raise AdminAccountError("Não foi possível confirmar o segundo fator.")
            admin.totp_last_used_step = matched_step
        else:
            raise AdminAccountError("A regeneração exige um passo TOTP ainda não utilizado.")
    except (AdminAccountError, TotpSecretError):
        audit(db, "admin_totp_recovery.issue_rejected", str(admin.id), tenant_id=session.tenant_id)
        db.commit()
        raise neutral_error() from None

    timestamp = now()
    db.execute(update(AdminTotpRecoveryCode).where(
        AdminTotpRecoveryCode.admin_user_id == admin.id,
        AdminTotpRecoveryCode.used_at.is_(None),
        AdminTotpRecoveryCode.revoked_at.is_(None),
    ).values(revoked_at=timestamp))
    codes = create_recovery_codes()
    db.add_all([
        AdminTotpRecoveryCode(
            admin_user_id=admin.id,
            code_selector=recovery_code_selector(code),
            code_hash=hash_recovery_code(code),
        )
        for code in codes
    ])
    audit(db, "admin_totp_recovery.issued", str(admin.id), tenant_id=session.tenant_id)
    db.commit()
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"
    return {"codes": codes, "message": "Guarde estes códigos agora. Eles não serão exibidos novamente."}


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
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    enforce_rate_limit(db, "admin_recovery_reset", token_hash(payload.token),
                       request.client.host if request.client else "unknown")
    db.commit()
    item = db.scalar(
        select(AdminActionToken).where(
            AdminActionToken.token_hash == token_hash(payload.token),
            AdminActionToken.purpose == "password_reset",
        )
    )
    admin = db.get(AdminUser, item.admin_id, with_for_update=True) if item else None
    if not item or item.used_at or expired(item.expires_at) or not admin:
        raise HTTPException(status_code=400, detail="O link não está mais disponível.")
    signup_origin = db.scalar(select(PhotographerSignup.id).where(
        PhotographerSignup.reserved_admin_id == admin.id,
        PhotographerSignup.state == "active",
    ))
    matched_step = None
    recovery_code = None
    if signup_origin is not None:
        active_signup_tenant = db.scalar(select(Tenant.id).join(
            TenantAdmin, TenantAdmin.tenant_id == Tenant.id,
        ).join(PhotographerSignup, PhotographerSignup.activated_tenant_id == Tenant.id).where(
            PhotographerSignup.id == signup_origin,
            Tenant.status == "active",
            TenantAdmin.admin_user_id == admin.id,
            TenantAdmin.active.is_(True),
        ))
        if active_signup_tenant is None:
            raise neutral_error()
        from app.system_monitor.models import PlatformOwner
        owner_account = db.scalar(select(PlatformOwner.admin_user_id).where(PlatformOwner.admin_user_id == admin.id))
        has_totp = bool(admin.totp_enabled or owner_account is not None)
        if has_totp:
            factor = payload.second_factor_code or ""
            if re.fullmatch(r"\d{6}", factor):
                matched_step = matching_unused_totp_step(
                    admin.totp_secret, factor, admin.totp_last_used_step, valid_window=1,
                )
            elif re.fullmatch(r"[A-Za-z0-9_-]{24}", factor):
                candidates = db.scalars(select(AdminTotpRecoveryCode).where(
                    AdminTotpRecoveryCode.admin_user_id == admin.id,
                    AdminTotpRecoveryCode.code_selector == recovery_code_selector(factor),
                    AdminTotpRecoveryCode.used_at.is_(None),
                    AdminTotpRecoveryCode.revoked_at.is_(None),
                ).with_for_update())
                recovery_code = next((code for code in candidates
                                      if verify_recovery_code_hash(code.code_hash, factor)), None)
            if matched_step is None and recovery_code is None:
                raise neutral_error()
        elif payload.second_factor_code:
            raise neutral_error()
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
    if matched_step is not None:
        admin.totp_last_used_step = matched_step
    if recovery_code is not None:
        recovery_code.used_at = now()
        audit(db, "admin_totp_recovery.used", str(admin.id))
    change_admin_password(
        db, admin, payload.new_password, audit_event="admin_security.password_reset.completed"
    )
    db.commit()
    response.delete_cookie(getenv("SESSION_COOKIE_NAME", "markina_session"), path="/")
    return {"message": "Senha redefinida. Entre novamente com sua senha."}


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
def destination(request: Request, return_to: str | None = Query(default=None, max_length=512)) -> dict[str, str]:
    session = current_session(request, invalid_session_status=401, platform_scope=True)
    if session.role == Role.ADMIN.value:
        return {"destination": "/admin"}
    with SessionLocal() as db:
        purchase_destination = _purchase_return_destination(
            db, return_to, tenant_id=session.tenant_id, client_id=session.subject_id,
        ) if isinstance(return_to, str) and return_to else None
        if purchase_destination:
            return {"destination": purchase_destination}
        client_destination = _client_journey_destination(db, session.subject_id, tenant_id=session.tenant_id)
    return {"destination": client_destination}


@app.get("/auth/identity")
def authenticated_identity(request: Request, db: Session = Depends(db_session)) -> dict[str, str]:
    """Retorna somente a identidade própria da sessão autenticada e seu tenant."""
    session = current_session(request, invalid_session_status=401, platform_scope=True)
    if session.role == Role.ADMIN.value:
        admin = db.get(AdminUser, session.subject_id)
        if not admin or not admin.email_verified:
            raise HTTPException(status_code=401, detail="Sessão inválida")
        return {"role": "admin", "identity": admin.email}

    client = db.scalar(
        select(Client).where(
            Client.id == session.subject_id,
            Client.tenant_id == session.tenant_id,
        )
    )
    if not client:
        raise HTTPException(status_code=401, detail="Sessão inválida")
    verified_phone = db.scalar(
        select(ClientPhone.phone_e164)
        .where(
            ClientPhone.tenant_id == session.tenant_id,
            ClientPhone.client_id == client.id,
            ClientPhone.active.is_(True),
            ClientPhone.verified_at.is_not(None),
        )
        .order_by(ClientPhone.created_at.desc())
    )
    return {"role": "client", "identity": verified_phone or client.phone_e164}


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> Response:
    session = current_session(request)
    with SessionLocal() as db:
        stored = db.get(type(session), session.id)
        raw_installation = request.cookies.get(INSTALLATION_COOKIE)
        if raw_installation:
            revoke_installation(db, push_fingerprint(raw_installation), session)
        for subscription in db.scalars(select(PushSubscription).where(
            PushSubscription.tenant_id == session.tenant_id, PushSubscription.session_id == session.id, PushSubscription.active)):
            subscription.active = False
            subscription.generation += 1
        stored.revoked_at = now()
        audit(db, "session.revoked", str(session.subject_id))
        db.commit()
    response.delete_cookie("markina_session", path="/")
    response.status_code = 204
    return response


@app.post("/auth/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all(request: Request, response: Response) -> Response:
    session = current_session(request)
    with SessionLocal() as db:
        revoke_subject_sessions(db, session.role, session.subject_id)
        db.commit()
    response.delete_cookie("markina_session", path="/")
    response.status_code = 204
    return response


@app.get("/admin")
def admin_area(request: Request) -> dict[str, str]:
    require_admin(request)
    return {"status": "authorized"}


@app.get("/admin/email/channel")
def admin_email_channel(request: Request, db: Session = Depends(db_session)) -> dict[str, object]:
    session = require_admin(request)
    directory_tenant_id(db, request)
    payload: dict[str, object] = email_channel_payload()
    normalized_source_id = func.lower(func.replace(EmailDelivery.source_id, "-", ""))
    normalized_action_token_ids = select(func.lower(func.replace(
        cast(AdminActionToken.id, String), "-", ""
    ))).where(AdminActionToken.admin_id == session.subject_id)
    payload["deliveries"] = {
        delivery_status: count
        for delivery_status, count in db.execute(
            select(EmailDelivery.status, func.count())
            .where(or_(
                (EmailDelivery.source_type == "admin_user") & (EmailDelivery.source_id == str(session.subject_id)),
                (EmailDelivery.source_type == "admin_action_token") & normalized_source_id.in_(
                    normalized_action_token_ids),
            ))
            .group_by(EmailDelivery.status)
            .order_by(EmailDelivery.status)
        )
    }
    return payload


@app.get("/admin/security/summary")
def admin_security_summary(
    request: Request, response: Response, db: Session = Depends(db_session)
) -> dict[str, object]:
    session = current_session(request, Role.ADMIN)
    try:
        admin = active_admin_for_session(db, session)
    except AdminAccountError:
        raise HTTPException(status_code=403, detail="Acesso negado.") from None
    response.headers["Cache-Control"] = "private, no-store"
    whatsapp = channel_settings(db, tenant_id=directory_tenant_id(db, request))
    recovery_codes_available = db.scalar(select(func.count()).select_from(
        AdminTotpRecoveryCode
    ).where(
        AdminTotpRecoveryCode.admin_user_id == admin.id,
        AdminTotpRecoveryCode.used_at.is_(None),
        AdminTotpRecoveryCode.revoked_at.is_(None),
    )) or 0
    return {
        "email_masked": mask_email(admin.email),
        "whatsapp_status": whatsapp.status,
        "email_channel": email_channel_payload(),
        "recovery_codes_available": recovery_codes_available,
        "totp_enabled": bool(admin.totp_enabled),
    }


@app.get("/admin/settings/pix")
def admin_global_pix(request: Request, db: Session = Depends(db_session)) -> dict:
    session = current_session(request, Role.ADMIN)
    active_admin_for_session(db, session)
    return pix_payload(global_pix_settings(db, tenant_id=session.tenant_id), editable=True)


@app.post("/admin/settings/pix/challenge", status_code=status.HTTP_202_ACCEPTED)
def admin_global_pix_challenge(
    payload: GlobalPixChallengeInput, request: Request, db: Session = Depends(db_session)
) -> dict:
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    admin = active_admin_for_session(db, session)
    enforce_rate_limit(db, "admin_change_pix", str(admin.id),
                       request.client.host if request.client else "unknown")
    try:
        reauthenticate_admin(admin, payload.current_password)
    except AdminAccountError:
        audit(db, "admin_security.change_pix.reauthentication_failed", str(admin.id))
        db.commit()
        raise neutral_error() from None
    # Serializa a emissão e a confirmação para o mesmo fotógrafo.
    lock_payment_account(db, session.tenant_id)
    db.scalar(select(AdminUser).where(AdminUser.id == admin.id).with_for_update())
    settings = global_pix_settings(db, tenant_id=session.tenant_id)
    try:
        configuration = payload.configuration.model_dump() if payload.configuration else None
        if configuration and configuration.get("qr_code_payload"):
            raise PixCodeError("Use somente chave PIX ou copia e cola para gerar o QR.")
        target = canonical_proposal(configuration, settings.version if settings else 0)
    except PixCodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        challenge, _code, queued = create_security_challenge(
            db, purpose="change_pix_otp", subject_fingerprint=pii_fingerprint(str(admin.id)),
            admin=admin, session_id=session.id, target=target, tenant_id=session.tenant_id,
        )
    except (AdminSecurityConfigurationError, WhatsAppConfigurationError):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Confirmação segura temporariamente indisponível.",
        ) from None
    if not queued:
        challenge.used_at = now()
        challenge.encrypted_target = None
        db.commit()
        raise HTTPException(status_code=409, detail="Canal WhatsApp indisponível para confirmação.")
    return {"challenge_id": str(challenge.id), "expires_at": challenge.expires_at.isoformat(),
            "proposal": proposal_preview(target),
            "message": "Código de confirmação enviado ao WhatsApp administrativo."}


@app.post("/admin/settings/pix/confirm")
def admin_global_pix_confirm(
    payload: GlobalPixConfirmInput, request: Request, db: Session = Depends(db_session)
) -> dict:
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    admin = active_admin_for_session(db, session)
    lock_payment_account(db, session.tenant_id)
    db.scalar(select(AdminUser).where(AdminUser.id == admin.id).with_for_update())
    stored = db.scalar(select(AdminSecurityChallenge).where(
        AdminSecurityChallenge.id == payload.challenge_id,
        AdminSecurityChallenge.tenant_id == session.tenant_id,
    ).with_for_update())
    if not stored or stored.admin_id != admin.id:
        raise neutral_error()
    try:
        challenge = verify_security_challenge(
            db, challenge_id=payload.challenge_id, purpose="change_pix_otp",
            code=payload.code, session_id=session.id, tenant_id=session.tenant_id,
        )
        target = challenge_target(challenge)
        if challenge.target_fingerprint != pii_fingerprint(target.strip().casefold()):
            raise AdminAccountError("Proposta indisponível.")
        settings = apply_configuration(db, admin_id=admin.id, proposed=json.loads(target), tenant_id=session.tenant_id)
    except AdminAccountError:
        raise neutral_error() from None
    except PixCodeError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from None
    challenge.encrypted_target = None
    audit(db, "pix.global_updated", f"{admin.id}:{settings.id}:{settings.version}", tenant_id=session.tenant_id)
    db.commit()
    return pix_payload(settings, editable=True)


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
    settings: BrandingSettings, *, include_protection: bool = False, access_token: str | None = None
) -> dict[str, str | int | bool | None]:
    payload: dict[str, str | int | bool | None] = {
        "login_title": settings.login_title,
        "login_intro": settings.login_intro,
        "login_helper": settings.login_helper,
        "logo_url": "/branding/logo" if settings.logo_key else None,
        "app_icon_url": "/branding/app-icon" if settings.app_icon_key else None,
        "favicon_url": "/branding/favicon" if settings.favicon_key else None,
    }
    if access_token is not None:
        for field in ("logo_url", "app_icon_url", "favicon_url"):
            if payload[field]:
                payload[field] += "?" + urlencode({"access_token": access_token})
    if include_protection:
        payload.update(
            {
                "watermark_text": settings.watermark_text,
                "watermark_font": settings.watermark_font,
                "watermark_color": settings.watermark_color,
                "watermark_size": settings.watermark_size,
                "watermark_direction": settings.watermark_direction,
                "watermark_opacity": settings.watermark_opacity,
                "watermark_position": settings.watermark_position,
                "watermark_shadow": settings.watermark_shadow,
                "watermark_security_lines": settings.watermark_security_lines,
            }
        )
    return payload


@app.get("/branding")
def public_branding(request: Request, response: Response,
                    access_token: str | None = Query(default=None, max_length=600),
                    db: Session = Depends(db_session)) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    tenant_id = branding_tenant_id(db, request, access_token)
    if tenant_id is None:
        return technical_branding()
    settings = branding_settings(db, tenant_id=tenant_id)
    return _branding_payload(settings, access_token=access_token) if settings else technical_branding()


@app.get("/admin/branding")
def admin_branding(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, str | int | bool | None]:
    tenant_id = directory_tenant_id(db, request)
    settings = branding_settings(db, tenant_id=tenant_id, create=True)
    db.commit()
    return _branding_payload(settings, include_protection=True)


@app.patch("/admin/branding")
def update_admin_branding(
    payload: BrandingSettingsInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str | int | bool | None]:
    tenant_id = directory_tenant_id(db, request)
    settings = branding_settings(db, tenant_id=tenant_id, create=True)
    settings.login_title = payload.login_title.strip()
    settings.login_intro = payload.login_intro.strip()
    settings.login_helper = payload.login_helper.strip()
    audit(db, "branding.settings_updated", str(settings.id), tenant_id=tenant_id)
    db.commit()
    return _branding_payload(settings, include_protection=True)


@app.patch("/admin/branding/protection")
def update_visual_protection(
    payload: VisualProtectionSettingsInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str | int | bool | None]:
    """Persiste uma única proteção visual e reprocessa derivados sem servir originais."""
    tenant_id = directory_tenant_id(db, request)
    settings = branding_settings(db, tenant_id=tenant_id, create=True)
    for field, value in payload.model_dump().items():
        setattr(settings, field, value)
    for photo in db.scalars(select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id)).all():
        job = enqueue_derivatives(db, photo)
        job.status = "queued"
        job.last_error = None
        derivative = db.scalar(
            select(MediaDerivative).where(
                MediaDerivative.tenant_id == tenant_id,
                MediaDerivative.photo_asset_id == photo.id,
                MediaDerivative.variant == "client_preview",
            )
        )
        if derivative:
            derivative.status = "queued"
    audit(db, "branding.visual_protection_updated", str(settings.id), tenant_id=tenant_id)
    db.commit()
    return _branding_payload(settings, include_protection=True)


@app.put("/admin/branding/{asset}")
async def upload_branding_asset(
    asset: str, request: Request, db: Session = Depends(db_session)
) -> dict[str, str | None]:
    """Store one validated branding image; paths never come from the browser."""
    tenant_id = directory_tenant_id(db, request)
    if asset not in BRANDING_ASSETS:
        raise HTTPException(status_code=404, detail="Ativo de marca não encontrado.")
    body = await request.body()
    suffix, _ = validate_branding_asset(asset, request.headers.get("content-type"), body)
    key = f"tenants/{tenant_id}/branding/{asset}-{sha256(body).hexdigest()}{suffix}"
    destination = branding_asset_path(key, tenant_id=tenant_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{suffix}.uploading")
    require_active_owner(db, tenant_id)
    temporary.write_bytes(body)
    temporary.replace(destination)
    settings = branding_settings(db, tenant_id=tenant_id, create=True)
    if asset == "logo":
        settings.logo_key = key
    elif asset == "app-icon":
        settings.app_icon_key = key
    else:
        settings.favicon_key = key
    audit(db, "branding.asset_uploaded", f"{settings.id}:{asset}", tenant_id=tenant_id)
    db.commit()
    return _branding_payload(settings)


@app.get("/branding/{asset}")
def public_branding_asset(
    asset: str, request: Request, size: int | None = Query(default=None),
    access_token: str | None = Query(default=None, max_length=600), db: Session = Depends(db_session)
) -> Response:
    if asset not in BRANDING_ASSETS:
        raise HTTPException(status_code=404, detail="Ativo de marca não encontrado.")
    tenant_id = branding_tenant_id(db, request, access_token)
    if tenant_id is None:
        raise HTTPException(status_code=404, detail="Ativo de marca indisponível.")
    settings = branding_settings(db, tenant_id=tenant_id)
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
        if key.startswith("tenants/") and not key.startswith(f"tenants/{tenant_id}/"):
            raise ValueError("Ativo indisponível.")
        require_active_owner(db, tenant_id)
        path = branding_asset_path(key, tenant_id=tenant_id)
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
    if size is not None:
        if asset != "app-icon" or size not in {180, 192, 512}:
            raise HTTPException(status_code=422, detail="Tamanho de ícone não permitido.")
        try:
            with Image.open(path) as source:
                image = source.convert("RGBA")
                scale = min(size / image.width, size / image.height)
                image = image.resize(
                    (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                    Image.Resampling.LANCZOS,
                )
                canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
                output = BytesIO()
                canvas.save(output, format="PNG")
            return Response(
                output.getvalue(), media_type="image/png", headers={"Cache-Control": "private, no-store"}
            )
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=404, detail="Ícone indisponível.") from exc
    return FileResponse(
        path, media_type=media_type, headers={"Cache-Control": "private, no-store"}
    )


@app.get("/admin/validation-summary")
def admin_validation_summary(
    request: Request, response: Response, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Resumo seguro para o painel visual do fotógrafo."""
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    response.headers["Cache-Control"] = "private, no-store"
    job_states = dict(db.execute(
        select(MediaJob.status, func.count()).where(MediaJob.tenant_id == tenant_id)
        .group_by(MediaJob.status)
    ).all())
    legacy_gallery_count = db.scalar(select(func.count(DerivedGallery.id)).where(DerivedGallery.tenant_id == tenant_id)) or 0
    active_import_folders = (
        select(PhotoFolder.id.label("folder_id"))
        .join(PhotoAsset, (PhotoAsset.folder_id == PhotoFolder.id) & (PhotoAsset.tenant_id == tenant_id))
        .join(MediaJob, (MediaJob.photo_asset_id == PhotoAsset.id) & (MediaJob.tenant_id == tenant_id))
        .where(
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.purpose == "content",
            MediaJob.status.in_(("queued", "processing")),
        )
        .distinct()
        .subquery()
    )
    active_import_folder_count = db.scalar(
        select(func.count()).select_from(active_import_folders)
    ) or 0
    active_import_photo_count = db.scalar(
        select(func.count(PhotoAsset.id)).where(
            PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.folder_id.in_(select(active_import_folders.c.folder_id)),
        )
    ) or 0
    galleries = list(db.scalars(select(ParentGallery).where(ParentGallery.tenant_id == tenant_id).where(
        ParentGallery.lifecycle_status != "deleted"
    ).order_by(ParentGallery.created_at.desc()).limit(5)))
    selection_parent_id = func.coalesce(
        PhotoSelection.parent_gallery_id, DerivedGallery.parent_gallery_id
    )
    selection_scope_id = func.coalesce(
        DerivedGallery.id, PhotoSelection.parent_gallery_id
    )
    selection_scope_name = func.coalesce(
        DerivedGallery.name, ParentGallery.name, "Galeria removida"
    )
    recent_selection_rows = list(db.execute(
        select(
            selection_scope_id.label("scope_id"),
            selection_scope_name.label("scope_name"),
            ParentGallery.id.label("parent_gallery_id"),
            ParentGallery.name.label("parent_gallery_name"),
            Client.id.label("client_id"),
            Client.full_name.label("client_name"),
            func.count(PhotoSelection.id).label("selected_count"),
            GalleryClientState.selection_started_at.label("selection_started_at"),
            func.max(PhotoSelection.created_at).label("last_selected_at"),
        )
        .join(PhotoAsset, PhotoAsset.id == PhotoSelection.photo_asset_id)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .outerjoin(DerivedGallery, DerivedGallery.id == PhotoSelection.derived_gallery_id)
        .join(Client, Client.id == PhotoSelection.client_id)
        .outerjoin(ParentGallery, ParentGallery.id == selection_parent_id)
        .outerjoin(
            GalleryClientState,
            and_(
                PhotoSelection.parent_gallery_id.is_not(None),
                GalleryClientState.tenant_id == tenant_id,
                GalleryClientState.parent_gallery_id == selection_parent_id,
                GalleryClientState.client_id == PhotoSelection.client_id,
            ),
        )
        .where(
            PhotoSelection.tenant_id == tenant_id,
            PhotoAsset.tenant_id == tenant_id,
            PhotoFolder.tenant_id == tenant_id,
            Client.tenant_id == tenant_id,
            or_(DerivedGallery.id.is_(None), DerivedGallery.tenant_id == tenant_id),
            or_(ParentGallery.id.is_(None), ParentGallery.tenant_id == tenant_id),
            selection_scope_id.is_not(None),
            selection_parent_id.is_not(None),
        )
        .group_by(
            selection_scope_id,
            selection_scope_name,
            ParentGallery.id,
            ParentGallery.name,
            Client.id,
            Client.full_name,
            GalleryClientState.selection_started_at,
        )
        .order_by(
            func.max(PhotoSelection.created_at).desc(),
            selection_scope_id,
            Client.id,
        )
        .limit(5)
    ))

    def summary_timestamp(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)  # noqa: UP017 -- compatibilidade com Python 3.10
        return value.astimezone(timezone.utc).isoformat()  # noqa: UP017 -- compatibilidade com Python 3.10

    storage = measure_owned_photo_storage(db, tenant_id=tenant_id)
    return {
        "environment": getenv("APP_ENV", "development"),
        "version": getenv("APP_VERSION", "local"),
        "storage": {
            "photo_count": int(db.scalar(select(func.count()).select_from(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id)) or 0),
            "bytes": storage.bytes,
            "available": storage.available,
        },
        "counts": {
            "clients": db.scalar(select(func.count(Client.id)).where(
                Client.tenant_id == tenant_id,
            )) or 0,
            "parent_galleries": db.scalar(select(func.count(ParentGallery.id)).where(
                ParentGallery.tenant_id == tenant_id, ParentGallery.lifecycle_status != "deleted",
            )) or 0,
            "derived_galleries": legacy_gallery_count,
            "imports": dict(job_states),
            "folders_with_active_imports": active_import_folder_count,
            "photos_in_folders_with_active_imports": active_import_photo_count,
            "folders_preparing": db.scalar(select(func.count(PhotoFolder.id)).where(
                PhotoFolder.tenant_id == tenant_id, PhotoFolder.status == "preparing",
            )) or 0,
            "folders_released": db.scalar(select(func.count(PhotoFolder.id)).where(
                PhotoFolder.tenant_id == tenant_id, PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
            )) or 0,
        },
        "recent_galleries": [
            {
                "id": str(gallery.id),
                "name": gallery.name,
                "active": gallery.active,
                "event_name": gallery.event_name,
            }
            for gallery in galleries[:5]
        ],
        "recent_selections": [
            {
                "scope_id": str(row.scope_id),
                "client": {"id": str(row.client_id), "name": row.client_name},
                "gallery": {"id": str(row.scope_id), "name": row.scope_name},
                "parent_gallery": {
                    "id": str(row.parent_gallery_id), "name": row.parent_gallery_name,
                },
                "selected_count": int(row.selected_count),
                "selection_started_at": summary_timestamp(row.selection_started_at),
                "last_selected_at": summary_timestamp(row.last_selected_at),
            }
            for row in recent_selection_rows
        ],
    }


def _require_credit_owner(request: Request, db: Session, response: Response) -> AuthSession:
    from app.system_monitor.access import is_owner

    session = require_admin(request)
    response.headers["Cache-Control"] = "private, no-store"
    if not is_owner(db, session.subject_id):
        audit(db, "credit.owner_access_denied", str(session.subject_id))
        db.commit()
        raise HTTPException(403, "Acesso não autorizado.")
    return session


def _credit_owner_response(db: Session, request: Request, session: AuthSession, result: dict):
    from app.platform_console import revalidate_owner_before_commit

    # A serialização também consulta dados privados, inclusive durante replay.
    revalidate_owner_before_commit(db, request, session)
    return result


def _credit_mutation_evidence(action: str, payload, *, grant_entry_id: UUID | None = None) -> str:
    canonical = {
        "action": action,
        "tenant_id": str(payload.tenant_id),
        "quantity": payload.quantity,
        "idempotency_key": payload.idempotency_key,
        "reference": payload.reference,
        "grant_entry_id": str(grant_entry_id) if grant_entry_id else None,
    }
    return sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False).encode("utf-8")).hexdigest()


def _credit_owner_mutation(
    *, request: Request, response: Response, db: Session, payload,
    action: str, grant_entry_id: UUID | None = None,
):
    """Reautentica, serializa, audita e confirma uma mutação financeira do proprietário."""
    require_same_origin(request)
    session = _require_credit_owner(request, db, response)
    from app import platform_console

    platform_console.require_console_owner(db, session)
    admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id)
                      .with_for_update().execution_options(populate_existing=True))
    if admin is None:
        raise HTTPException(403, "Acesso não autorizado.", headers={"Cache-Control": "private, no-store"})

    evidence = _credit_mutation_evidence(action, payload, grant_entry_id=grant_entry_id)
    previous = db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == payload.request_id,
    ).with_for_update())
    if previous is not None:
        if (previous.actor_admin_id, previous.tenant_id, previous.action, previous.evidence_sha256) != (
            session.subject_id, payload.tenant_id, action, evidence,
        ):
            db.add(PlatformAdminEvent(
                actor_admin_id=session.subject_id,
                tenant_id=payload.tenant_id if db.get(Tenant, payload.tenant_id) else None,
                object_id=payload.tenant_id,
                action="console.access_denied",
                result="denied",
            ))
            db.commit()
            raise HTTPException(409, "Identificador já utilizado em outra operação.",
                                headers={"Cache-Control": "private, no-store"})
        entry = db.scalar(select(PhotographerCreditEntry).where(
            PhotographerCreditEntry.id == previous.object_id,
            PhotographerCreditEntry.tenant_id == payload.tenant_id,
            PhotographerCreditEntry.global_owner_admin_id == session.subject_id,
        ))
        if entry is None:
            raise HTTPException(409, "Operação financeira precisa de reconciliação.",
                                headers={"Cache-Control": "private, no-store"})
        return session, entry, True

    enforce_rate_limit(db, f"platform_{action.replace('.', '_')}", str(session.subject_id),
                       request.client.host if request.client else "unknown")
    try:
        step = platform_console.reauthenticate_console_owner(admin, payload)
    except AdminAccountError:
        db.add(PlatformAdminEvent(
            actor_admin_id=session.subject_id,
            tenant_id=payload.tenant_id if db.get(Tenant, payload.tenant_id) else None,
            object_id=payload.tenant_id,
            action="console.access_denied",
            result="denied",
        ))
        db.commit()
        raise HTTPException(403, "Não foi possível confirmar a operação.",
                            headers={"Cache-Control": "private, no-store"}) from None
    except TotpSecretError:
        db.rollback()
        raise HTTPException(503, "Autenticador temporariamente indisponível.",
                            headers={"Cache-Control": "private, no-store"}) from None

    try:
        if action == "credit.granted":
            entry = photographer_credits.grant_credits(
                db, session.subject_id, payload.tenant_id, payload.quantity,
                payload.idempotency_key, payload.reference,
            )
        else:
            entry = photographer_credits.revoke_grant(
                db, session.subject_id, payload.tenant_id, grant_entry_id,
                payload.quantity, payload.idempotency_key, payload.reference,
            )
    except HTTPException:
        db.rollback()
        admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id)
                          .with_for_update().execution_options(populate_existing=True))
        if admin is not None:
            admin.totp_last_used_step = step
        db.add(PlatformAdminEvent(
            actor_admin_id=session.subject_id,
            tenant_id=payload.tenant_id if db.get(Tenant, payload.tenant_id) else None,
            object_id=payload.tenant_id,
            action="console.access_denied",
            result="denied",
        ))
        db.commit()
        raise

    admin.totp_last_used_step = step
    db.add(PlatformAdminEvent(
        request_id=payload.request_id,
        actor_admin_id=session.subject_id,
        object_id=entry.id,
        tenant_id=payload.tenant_id,
        action=action,
        evidence_sha256=evidence,
        result="success",
        created_at=now(),
    ))
    db.flush()
    platform_console.revalidate_owner_before_commit(db, request, session)
    db.commit()
    return session, entry, False


def _owner_credit_catalog_mutation(
    *, request: Request, response: Response, db: Session, payload,
    tenant_id: UUID | None, action: str, evidence: str, apply, lookup,
):
    """Step-up e auditoria atômicos para catálogo e revisão financeira global."""
    require_same_origin(request)
    session = _require_credit_owner(request, db, response)
    from app import platform_console

    platform_console.require_console_owner(db, session)
    admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id)
                      .with_for_update().execution_options(populate_existing=True))
    if admin is None:
        raise HTTPException(403, "Acesso não autorizado.", headers={"Cache-Control": "private, no-store"})

    previous = db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == payload.request_id,
    ).with_for_update())
    if previous is not None:
        if (previous.actor_admin_id, previous.tenant_id, previous.action, previous.evidence_sha256) != (
            session.subject_id, tenant_id, action, evidence,
        ):
            db.add(PlatformAdminEvent(
                actor_admin_id=session.subject_id,
                tenant_id=tenant_id if tenant_id and db.get(Tenant, tenant_id) else None,
                object_id=tenant_id,
                action="console.access_denied",
                result="denied",
            ))
            db.commit()
            raise HTTPException(409, "Identificador já utilizado em outra operação.",
                                headers={"Cache-Control": "private, no-store"})
        record = lookup(db, previous.object_id)
        if record is None:
            raise HTTPException(409, "Operação precisa de reconciliação.",
                                headers={"Cache-Control": "private, no-store"})
        return session, record, True

    enforce_rate_limit(db, f"platform_{action.replace('.', '_')}", str(session.subject_id),
                       request.client.host if request.client else "unknown")
    try:
        step = platform_console.reauthenticate_console_owner(admin, payload)
    except AdminAccountError:
        db.add(PlatformAdminEvent(
            actor_admin_id=session.subject_id,
            tenant_id=tenant_id if tenant_id and db.get(Tenant, tenant_id) else None,
            object_id=tenant_id,
            action="console.access_denied",
            result="denied",
        ))
        db.commit()
        raise HTTPException(403, "Não foi possível confirmar a operação.",
                            headers={"Cache-Control": "private, no-store"}) from None
    except TotpSecretError:
        db.rollback()
        raise HTTPException(503, "Autenticador temporariamente indisponível.",
                            headers={"Cache-Control": "private, no-store"}) from None

    try:
        record = apply(db, session.subject_id)
    except (HTTPException, CheckoutError) as exc:
        db.rollback()
        admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id)
                          .with_for_update().execution_options(populate_existing=True))
        if admin is not None:
            admin.totp_last_used_step = step
        db.add(PlatformAdminEvent(
            actor_admin_id=session.subject_id,
            tenant_id=tenant_id if tenant_id and db.get(Tenant, tenant_id) else None,
            object_id=tenant_id,
            action="console.access_denied",
            result="denied",
        ))
        db.commit()
        if isinstance(exc, CheckoutError):
            raise HTTPException(409, detail=str(exc)) from None
        raise

    admin.totp_last_used_step = step
    db.add(PlatformAdminEvent(
        request_id=payload.request_id,
        actor_admin_id=session.subject_id,
        object_id=record.id,
        tenant_id=tenant_id,
        action=action,
        evidence_sha256=evidence,
        result="success",
        created_at=now(),
    ))
    db.flush()
    platform_console.revalidate_owner_before_commit(db, request, session)
    db.commit()
    return session, record, False


@app.get("/admin/credits/capabilities")
def admin_credit_capabilities(
    request: Request, response: Response, db: Session = Depends(db_session),
) -> dict[str, bool]:
    from app.system_monitor.access import is_owner

    response.headers["Cache-Control"] = "private, no-store"
    session = require_admin(request)
    return {"manage_packages": is_owner(db, session.subject_id)}


@app.get("/admin/credits/wallet")
def admin_credit_wallet(request: Request, response: Response, db: Session = Depends(db_session)):
    tenant_id = directory_tenant_id(db, request)
    response.headers["Cache-Control"] = "private, no-store"
    snapshot = photographer_credits.wallet_snapshot(db, tenant_id)
    return {"wallet": snapshot, "entries": photographer_credits.list_entries(db, tenant_id)}


@app.get("/admin/media-archive/recovery-pricing")
def admin_media_archive_recovery_pricing(
    request: Request, response: Response, db: Session = Depends(db_session),
):
    session = require_admin(request)
    tenant_id = directory_tenant_id(db, request)
    response.headers["Cache-Control"] = "private, no-store"
    return media_archive_billing.recovery_pricing_payload(db, tenant_id, session.subject_id)


@app.get("/admin/media-archive/recovery-candidates")
def admin_media_archive_recovery_candidates(
    request: Request,
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(db_session),
):
    require_admin(request)
    tenant_id = directory_tenant_id(db, request)
    response.headers["Cache-Control"] = "private, no-store"
    return {"items": media_archive_billing.list_recovery_candidates(db, tenant_id, limit=limit)}


@app.get("/admin/media-archive/recoveries")
def admin_media_archive_recoveries(
    request: Request, response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(db_session),
):
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    response.headers["Cache-Control"] = "private, no-store"
    return {"items": media_archive_billing.list_tenant_recoveries(db, tenant_id, limit=limit)}


@app.post("/admin/media-archive/cycles/{cycle_id}/recovery", status_code=202)
def admin_request_media_archive_recovery(
    cycle_id: UUID,
    payload: MediaArchiveRecoveryInput,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
):
    require_same_origin(request)
    session = require_admin(request)
    tenant_id = directory_tenant_id(db, request)
    response.headers["Cache-Control"] = "private, no-store"
    result = media_archive_billing.request_recovery(
        db,
        tenant_id=tenant_id,
        actor_admin_id=session.subject_id,
        cycle_id=cycle_id,
        duration_days=payload.duration_days,
        idempotency_key=payload.idempotency_key,
    )
    db.commit()
    return result


@app.get("/admin/credits/history")
def admin_credit_history(
    request: Request, response: Response,
    limit: int = Query(default=30, ge=1, le=30), offset: int = Query(default=0, ge=0, le=100_000),
    as_of: datetime | None = None, db: Session = Depends(db_session),
):
    tenant_id = directory_tenant_id(db, request)
    response.headers["Cache-Control"] = "private, no-store"
    return credit_history.history_page(db, tenant_id, limit=limit, offset=offset, as_of=as_of)


@app.get("/admin/credits/history/folders/{folder_id}")
def admin_credit_folder_history(
    folder_id: UUID, request: Request, response: Response,
    limit: int = Query(default=20, ge=1, le=30), offset: int = Query(default=0, ge=0, le=100_000),
    as_of: datetime | None = None, db: Session = Depends(db_session),
):
    tenant_id = directory_tenant_id(db, request)
    response.headers["Cache-Control"] = "private, no-store"
    return credit_history.folder_entry_page(db, tenant_id, folder_id, limit=limit, offset=offset, as_of=as_of)


@app.get("/admin/credits/packages")
def admin_active_credit_packages(
    request: Request, response: Response, db: Session = Depends(db_session),
):
    from app.system_monitor.access import is_owner

    response.headers["Cache-Control"] = "private, no-store"
    session = require_admin(request)
    tenant_id = directory_tenant_id(db, request)
    if is_owner(db, session.subject_id):
        raise HTTPException(status_code=403, detail="Catálogo disponível para fotógrafos ativos.")
    wallet = photographer_credits.wallet_snapshot(db, tenant_id)
    if wallet["mode"] != "finite":
        raise HTTPException(status_code=403, detail="Catálogo disponível para fotógrafos ativos.")
    return {"items": photographer_credits.list_active_packages(db)}


@app.get("/admin/photo-assets/{photo_id}/credit-operation")
def admin_photo_credit_operation(
    photo_id: UUID, request: Request, response: Response, db: Session = Depends(db_session),
):
    """Expõe ao próprio tenant o estado mínimo da operação de crédito de uma foto."""
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    response.headers["Cache-Control"] = "private, no-store"
    photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")

    folder = owned_record(db, PhotoFolder, photo.folder_id, tenant_id=tenant_id)
    is_content = bool(folder and folder.purpose == "content")
    operation = db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant_id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    )) if is_content else None
    return {
        "wallet": photographer_credits.wallet_snapshot(db, tenant_id),
        "applicable": is_content,
        "operation": None if operation is None else {
            "status": operation.status,
            "quantity": operation.quantity,
            "updated_at": operation.updated_at,
        },
    }


@app.get("/admin/credits/entries")
def admin_credit_entries(
    request: Request, response: Response, limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(db_session),
):
    tenant_id = directory_tenant_id(db, request)
    response.headers["Cache-Control"] = "private, no-store"
    return {"items": photographer_credits.list_entries(db, tenant_id, limit=limit)}


@app.get("/admin/platform/credit-packages")
def admin_credit_packages(
    request: Request, response: Response, db: Session = Depends(db_session),
):
    session = _require_credit_owner(request, db, response)
    return {"items": photographer_credits.list_packages(db, session.subject_id)}


@app.post("/admin/platform/credit-packages")
def admin_create_credit_package(
    payload: PhotographerCreditPackageInput,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
):
    values = payload.model_dump(exclude={"request_id", "current_password", "totp_code"})
    evidence = sha256(json.dumps({"action": "credit.package_created", **values},
                                 sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False).encode("utf-8")).hexdigest()
    session, package, replayed = _owner_credit_catalog_mutation(
        request=request, response=response, db=db, payload=payload, tenant_id=None,
        action="credit.package_created", evidence=evidence,
        apply=lambda session_db, owner_id: photographer_credits.create_package(
            session_db, owner_id, **values,
        ),
        lookup=lambda session_db, object_id: session_db.get(PhotographerCreditPackage, object_id),
    )
    return _credit_owner_response(db, request, session, {
        **photographer_credits.package_payload(package), "replayed": replayed,
    })


@app.put("/admin/platform/credit-packages/{package_id}")
def admin_update_credit_package(
    package_id: UUID,
    payload: PhotographerCreditPackageInput,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
):
    values = payload.model_dump(exclude={"request_id", "current_password", "totp_code"})
    evidence = sha256(json.dumps({"action": "credit.package_updated", "package_id": str(package_id),
                                 **values}, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False).encode("utf-8")).hexdigest()
    session, package, replayed = _owner_credit_catalog_mutation(
        request=request, response=response, db=db, payload=payload, tenant_id=None,
        action="credit.package_updated", evidence=evidence,
        apply=lambda session_db, owner_id: photographer_credits.update_package(
            session_db, owner_id, package_id, **values,
        ),
        lookup=lambda session_db, object_id: session_db.get(PhotographerCreditPackage, object_id),
    )
    return _credit_owner_response(db, request, session, {
        **photographer_credits.package_payload(package), "replayed": replayed,
    })


@app.get("/admin/platform/credit-tenants")
def admin_credit_tenants(
    request: Request, response: Response, db: Session = Depends(db_session),
):
    session = _require_credit_owner(request, db, response)
    return {"items": photographer_credits.list_credit_tenants(db, session.subject_id)}


@app.get("/admin/platform/credit-tenants/search")
def admin_search_credit_tenants(
    request: Request,
    response: Response,
    query: str = Query(default="", max_length=254),
    mode: Literal["all", "alphabetical", "recent"] | None = None,
    limit: int = Query(default=10, ge=1, le=20),
    offset: int = Query(default=0, ge=0, le=100_000),
    db: Session = Depends(db_session),
):
    session = _require_credit_owner(request, db, response)
    return photographer_credits.browse_credit_tenants(
        db, session.subject_id, query=query, mode=mode, limit=limit, offset=offset,
    )


@app.get("/admin/platform/credit-tenants/{tenant_id}")
def admin_credit_tenant_detail(
    tenant_id: UUID,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
):
    session = _require_credit_owner(request, db, response)
    result = photographer_credits.credit_tenant_detail(db, session.subject_id, tenant_id)
    result["media_archive_recoveries"] = media_archive_billing.list_owner_recoveries(
        db, session.subject_id, tenant_id,
    )
    return result




@app.get("/admin/platform/credit-tenants/{tenant_id}/history")
def admin_owner_credit_history(
    tenant_id: UUID, request: Request, response: Response,
    limit: int = Query(default=30, ge=1, le=30), offset: int = Query(default=0, ge=0, le=100_000),
    as_of: datetime | None = None, db: Session = Depends(db_session),
):
    _require_credit_owner(request, db, response)
    return credit_history.history_page(db, tenant_id, limit=limit, offset=offset, as_of=as_of)


@app.get("/admin/platform/credit-tenants/{tenant_id}/history/folders/{folder_id}")
def admin_owner_credit_folder_history(
    tenant_id: UUID, folder_id: UUID, request: Request, response: Response,
    limit: int = Query(default=20, ge=1, le=30), offset: int = Query(default=0, ge=0, le=100_000),
    as_of: datetime | None = None, db: Session = Depends(db_session),
):
    _require_credit_owner(request, db, response)
    return credit_history.folder_entry_page(db, tenant_id, folder_id, limit=limit, offset=offset, as_of=as_of)


@app.get("/admin/platform/credit-purchases/reviews")
def admin_credit_purchase_reviews(
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
):
    session = _require_credit_owner(request, db, response)
    from app.mercadopago_credit_purchases import financial_review_queue

    try:
        return {"items": financial_review_queue(db, session.subject_id)}
    except CheckoutError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None


@app.post("/admin/platform/credit-purchases/{purchase_id}/review")
def admin_review_credit_purchase(
    purchase_id: UUID,
    payload: PhotographerCreditReviewInput,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
):
    from app.mercadopago_credit_purchases import resolve_credit_purchase_review
    purchase = db.get(MercadoPagoCreditPurchase, purchase_id)
    tenant_id = purchase.tenant_id if purchase else None
    evidence = sha256(json.dumps({
        "action": "credit.purchase_reviewed", "purchase_id": str(purchase_id),
        "decision": payload.decision, "reason": payload.reason,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    session, purchase, replayed = _owner_credit_catalog_mutation(
        request=request, response=response, db=db, payload=payload, tenant_id=tenant_id,
        action="credit.purchase_reviewed", evidence=evidence,
        apply=lambda session_db, owner_id: resolve_credit_purchase_review(
            session_db, owner_admin_id=owner_id, purchase_id=purchase_id,
            decision=payload.decision, reason=payload.reason,
        ),
        lookup=lambda session_db, object_id: session_db.get(MercadoPagoCreditPurchase, object_id),
    )
    result = photographer_credits.credit_tenant_detail(db, session.subject_id, purchase.tenant_id)
    return _credit_owner_response(db, request, session, {**result, "replayed": replayed})


@app.post("/admin/platform/credit-grants")
def admin_grant_photographer_credits(
    payload: PhotographerCreditGrantInput,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
):
    session, entry, _replayed = _credit_owner_mutation(
        request=request, response=response, db=db, payload=payload, action="credit.granted",
    )
    return _credit_owner_response(db, request, session, {
        "entry": photographer_credits.entry_payload(entry),
        "wallet": photographer_credits.wallet_snapshot(db, payload.tenant_id),
        "replayed": _replayed,
    })


@app.post("/admin/platform/credit-grants/{grant_entry_id}/revoke")
def admin_revoke_photographer_credits(
    grant_entry_id: UUID,
    payload: PhotographerCreditRevocationInput,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
):
    session, entry, _replayed = _credit_owner_mutation(
        request=request, response=response, db=db, payload=payload, action="credit.revoked",
        grant_entry_id=grant_entry_id,
    )
    return _credit_owner_response(db, request, session, {
        "entry": photographer_credits.entry_payload(entry),
        "wallet": photographer_credits.wallet_snapshot(db, payload.tenant_id),
        "replayed": _replayed,
    })


@app.get("/admin/installation-capabilities")
def admin_installation_capabilities(request: Request, response: Response) -> dict[str, bool]:
    from app.installation_operator import operator_is_active
    from app.system_monitor.access import is_owner

    response.headers["Cache-Control"] = "private, no-store"
    session = require_admin(request)
    with SessionLocal() as db:
        return {"capacity_diagnostics": is_owner(db, session.subject_id) and operator_is_active(db, session.subject_id)}


@app.get("/admin/capacity-observability", response_model=CapacitySnapshot)
def admin_capacity_observability(
    request: Request, response: Response
) -> CapacitySnapshot:
    """Snapshot diagnóstico sob demanda, autorizado antes de consultar o cache."""
    response.headers["Cache-Control"] = "no-store"
    require_installation_operator(request)
    try:
        return get_capacity_snapshot(authorize=lambda: require_installation_operator(request))
    except CollectionBusy as exc:
        raise HTTPException(status_code=503, detail="collection_busy") from exc


@app.get("/admin/facial-observability")
def admin_facial_observability(
    request: Request,
    expected_enabled: bool | None = Query(default=None),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    """Exporta somente sinais faciais agregados para operação autenticada."""

    require_installation_operator(request)
    environment = getenv("APP_ENV", "development").strip().lower()
    try:
        settings = facial_settings_from_environment(verify_runtime_assets=False)
        enabled = settings.enabled
    except FacialConfigurationError:
        enabled = False
    metrics = collect_facial_metrics(
        db,
        environment=environment,
        enabled=enabled,
    )
    alerts = evaluate_facial_alerts(metrics, expected_enabled=expected_enabled)
    require_installation_operator(request)
    return {
        "metrics": [asdict(metric) for metric in metrics],
        "alerts": [asdict(alert) for alert in alerts],
    }


@app.get("/admin/clients")
def admin_clients(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    cursor: str | None = Query(default=None, max_length=400),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    try:
        return list_client_directory(db, tenant_id=tenant_id, query=query, cursor=cursor, limit=limit)
    except ClientLifecycleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/admin/clients", status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    phone = normalize_e164(payload.phone_e164)
    try:
        assert_phone_available(db, phone, tenant_id=tenant_id)
    except ClientIdentityConflict:
        raise HTTPException(status_code=409, detail="Já existe cliente com este WhatsApp.")
    client = Client(tenant_id=tenant_id, full_name=payload.full_name.strip(), phone_e164=phone)
    db.add(client)
    db.flush()
    db.add(
        ClientPhone(
            tenant_id=tenant_id,
            client_id=client.id,
            phone_e164=phone,
            active=True,
            verified_at=None,
        )
    )
    audit(db, "client.created_by_admin", str(client.id), tenant_id=tenant_id)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe cliente com este WhatsApp.") from exc
    return {"id": str(client.id)}


@app.patch("/admin/clients/{client_id}")
def update_client_name(
    client_id: UUID,
    payload: ClientNameInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    client = db.scalar(select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id))
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrada.")
    client.full_name = " ".join(payload.full_name.split())
    audit(db, "client.name_changed", str(client.id), tenant_id=tenant_id)
    db.commit()
    return {"id": str(client.id), "name": client.full_name, "phone": client.phone_e164}


@app.get("/admin/clients/{client_id}/deletion-inventory")
def get_client_deletion_inventory(
    client_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    client = owned_record(db, Client, client_id, tenant_id=tenant_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrada.")
    return deletion_inventory(db, client, tenant_id=tenant_id)


@app.delete("/admin/clients/{client_id}", response_model=None)
def delete_client(
    client_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object] | JSONResponse:
    tenant_id = directory_tenant_id(db, request)
    admin_session = require_admin(request)
    idempotency_key = request.headers.get("Idempotency-Key", "").strip()
    if not 12 <= len(idempotency_key) <= 128:
        raise HTTPException(
            status_code=422,
            detail="Informe uma chave idempotente entre 12 e 128 caracteres.",
        )
    try:
        payload, reference_ids = delete_client_operational_graph(
            db,
            client_id=client_id,
            actor_admin_id=admin_session.subject_id,
            idempotency_key=idempotency_key,
            tenant_id=tenant_id,
        )
    except ClientDeletionBlocked as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Este cadastro possui histórico comercial protegido. "
                    "Edite o telefone ou administre os vínculos sem apagar o histórico."
                ),
                "inventory": exc.inventory,
            },
        ) from exc
    except ClientLifecycleError as exc:
        status_code = 404 if str(exc) == "Cliente não encontrada." else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "O cadastro recebeu uma nova dependência durante a exclusão. "
                "Atualize o inventário e tente novamente."
            ),
        ) from exc
    except Exception:  # noqa: BLE001 - Fronteira sanitizada de falhas inesperadas desta operação.
        request_id = str(uuid4())
        transaction_state, receipt = _client_deletion_transaction_state(db, idempotency_key, tenant_id=tenant_id)
        status_code = 200 if receipt is not None else 500
        category = "post_commit_failure" if receipt is not None else "unexpected"
        logger.error(
            "client_lifecycle_failure request_id=%s operation=%s category=%s status_code=%s transaction_state=%s",
            request_id,
            "delete_client",
            category,
            status_code,
            transaction_state,
        )
        if receipt is not None:
            return JSONResponse(
                status_code=status_code,
                headers={"X-Request-ID": request_id},
                content={
                    **receipt_payload(receipt),
                    "status": "completed_with_pending_cleanup",
                    "diagnostics": {"request_id": request_id},
                },
            )
        return JSONResponse(
            status_code=status_code,
            headers={"X-Request-ID": request_id},
            content={
                "detail": {
                    "message": "Não foi possível confirmar a exclusão. Atualize a lista antes de tentar novamente.",
                    "request_id": request_id,
                    "outcome": "not_committed" if transaction_state == "rolled_back" else "unknown",
                }
            },
        )
    if reference_ids:
        try:
            remove_facial_reference_files(
                Path(getenv("FACIAL_REFERENCE_ROOT", "./media/facial-references")), reference_ids,
                db=db, tenant_id=tenant_id
            )
        except Exception:  # noqa: BLE001 - Falha auxiliar pós-commit não desfaz o recibo.
            request_id = str(uuid4())
            logger.error(
                "client_lifecycle_failure request_id=%s operation=%s category=%s status_code=%s transaction_state=%s",
                request_id,
                "delete_client",
                "post_commit_cleanup",
                200,
                "committed",
            )
            return JSONResponse(
                status_code=200,
                headers={"X-Request-ID": request_id},
                content={
                    **payload,
                    "status": "completed_with_pending_cleanup",
                    "diagnostics": {"request_id": request_id},
                },
            )
    return payload


def _client_deletion_transaction_state(
    db: Session, idempotency_key: str, *, tenant_id: UUID
) -> tuple[str, ClientDeletionReceipt | None]:
    """Rollback a failed attempt, then use its durable receipt to classify the outcome."""
    try:
        db.rollback()
    except Exception:  # noqa: BLE001 - Falha no rollback torna o resultado desconhecido.
        return "unknown", None
    try:
        fingerprint = sha256(idempotency_key.encode("utf-8")).hexdigest()
        receipt = db.scalar(
            select(ClientDeletionReceipt).where(ClientDeletionReceipt.tenant_id == tenant_id).where(
                ClientDeletionReceipt.idempotency_key == fingerprint
            )
        )
    except Exception:  # noqa: BLE001 - Falha na consulta do recibo não pode presumir rollback.
        return "unknown", None
    return ("committed", receipt) if receipt is not None else ("rolled_back", None)


@app.get("/admin/parent-galleries")
def admin_parent_galleries(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    galleries = db.scalars(
        select(ParentGallery).where(ParentGallery.tenant_id == tenant_id)
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

    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    search = query.casefold() if query else ""
    rows = []
    for parent in db.scalars(
        select(ParentGallery).where(ParentGallery.tenant_id == tenant_id)
        .where(ParentGallery.lifecycle_status != "deleted")
        .order_by(ParentGallery.created_at.desc())
    ):
        galleries = list(
            db.scalars(select(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id).where(DerivedGallery.parent_gallery_id == parent.id))
        )
        registrations = list(
            db.scalars(
                select(ParentGalleryRegistration).where(ParentGalleryRegistration.tenant_id == tenant_id).where(
                    ParentGalleryRegistration.parent_gallery_id == parent.id
                )
            )
        )
        owners = [owned_record(db, Client, gallery.client_id, tenant_id=tenant_id) for gallery in galleries]
        linked_clients = (
            [owned_record(db, Client, registration.client_id, tenant_id=tenant_id) for registration in registrations]
            if search else []
        )
        if search and not (
            search in parent.name.casefold()
            or (parent.event_name and search in parent.event_name.casefold())
            or any(
                owner and (search in owner.full_name.casefold() or search in owner.phone_e164)
                for owner in (*owners, *linked_clients)
            )
        ):
            continue
        frozen = sum(
            bool(gallery_operational_status(db, gallery)["frozen"])
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


def _parent_gallery_or_404(db: Session, parent_gallery_id: UUID, *, tenant_id: UUID) -> ParentGallery:
    gallery = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
    if not gallery or gallery.lifecycle_status == "deleted":
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    return gallery


def _gallery_capability_origin(request: Request) -> str:
    try:
        return validated_public_origin(
            getenv("APP_ENV", "development"), local_fallback=str(request.base_url)
        )
    except PublicOriginError as exc:
        raise HTTPException(status_code=503, detail="Origem pública indisponível.") from exc


def _gallery_capability_link(request: Request, token: str) -> str:
    """Usa origem pública confiável; a conexão interna pode ser HTTP."""
    return f"{_gallery_capability_origin(request)}/?access_token={token}"


def _active_gallery_capability(
    db: Session,
    *,
    tenant_id: UUID, parent_gallery_id: UUID,
    scope: str,
    client_id: UUID | None = None,
    derived_gallery_id: UUID | None = None,
) -> GalleryAccessCapability | None:
    query = select(GalleryAccessCapability).where(GalleryAccessCapability.tenant_id == tenant_id).where(
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
        cover = owned_record(db, PhotoAsset, gallery.cover_photo_id, tenant_id=gallery.tenant_id)
        if cover and cover.parent_gallery_id == gallery.id:
            return cover
    return db.scalar(
        select(PhotoAsset).where(PhotoAsset.tenant_id == gallery.tenant_id)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .join(MediaDerivative, MediaDerivative.photo_asset_id == PhotoAsset.id)
        .where(
            PhotoAsset.parent_gallery_id == gallery.id,
            PhotoAsset.derived_gallery_id.is_(None),
            PhotoFolder.purpose == "content",
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
        .order_by(PhotoFolder.position, PhotoAsset.created_at, PhotoAsset.filename)
        .limit(1)
    )


def _cover_preview_url(db: Session, gallery: ParentGallery) -> str | None:
    cover = _gallery_cover_photo(db, gallery)
    if not cover or not _cover_thumbnail_is_local(db, gallery, cover.id):
        return None
    ready = db.scalar(
        select(MediaDerivative.id).where(MediaDerivative.tenant_id == gallery.tenant_id).where(
            MediaDerivative.photo_asset_id == cover.id,
            MediaDerivative.variant == "admin_preview",
            MediaDerivative.status == "ready",
        )
    )
    return f"/admin/photo-assets/{cover.id}/preview" if ready else None


def _archive_object_state(
    db: Session, *, tenant_id: UUID, parent_gallery_id: UUID,
    source_ref: str, object_type: str,
) -> str:
    state = db.scalar(
        select(MediaArchiveCycle.state)
        .join(
            MediaArchiveObject,
            (MediaArchiveObject.cycle_id == MediaArchiveCycle.id)
            & (MediaArchiveObject.tenant_id == MediaArchiveCycle.tenant_id),
        )
        .where(
            MediaArchiveCycle.tenant_id == tenant_id,
            MediaArchiveCycle.parent_gallery_id == parent_gallery_id,
            MediaArchiveObject.source_ref == source_ref,
            MediaArchiveObject.object_type == object_type,
        )
        .order_by(MediaArchiveCycle.created_at.desc(), MediaArchiveCycle.id.desc())
        .limit(1)
    )
    return "available" if state in (None, "local") else str(state)


def _cover_thumbnail_state(
    db: Session, gallery: ParentGallery, photo_id: UUID,
) -> str:
    return _archive_object_state(
        db,
        tenant_id=gallery.tenant_id,
        parent_gallery_id=gallery.id,
        source_ref=f"cover:{photo_id}:admin_preview",
        object_type="cover_thumbnail",
    )


def _cover_thumbnail_is_local(
    db: Session, gallery: ParentGallery, photo_id: UUID,
) -> bool:
    return _cover_thumbnail_state(db, gallery, photo_id) in {"available", "archiving"}


def _local_cover_thumbnail_parent_ids(
    db: Session, *, tenant_id: UUID, parent_ids: set[UUID],
) -> set[UUID]:
    if not parent_ids:
        return set()
    parents = list(db.scalars(select(ParentGallery).where(
        ParentGallery.tenant_id == tenant_id,
        ParentGallery.id.in_(parent_ids),
        ParentGallery.cover_photo_id.is_not(None),
    )))
    cover_refs = {
        (parent.id, f"cover:{parent.cover_photo_id}:admin_preview")
        for parent in parents
    }
    if not cover_refs:
        return set()
    source_refs = {source_ref for _, source_ref in cover_refs}
    rows = db.execute(
        select(
            MediaArchiveCycle.parent_gallery_id,
            MediaArchiveObject.source_ref,
            MediaArchiveCycle.state,
        )
        .join(
            MediaArchiveCycle,
            (MediaArchiveCycle.id == MediaArchiveObject.cycle_id)
            & (MediaArchiveCycle.tenant_id == MediaArchiveObject.tenant_id),
        )
        .where(
            MediaArchiveObject.tenant_id == tenant_id,
            MediaArchiveObject.source_ref.in_(source_refs),
            MediaArchiveObject.object_type == "cover_thumbnail",
            MediaArchiveCycle.parent_gallery_id.in_(parent_ids),
        )
        .order_by(
            MediaArchiveCycle.parent_gallery_id,
            MediaArchiveObject.source_ref,
            MediaArchiveCycle.created_at.desc(),
            MediaArchiveCycle.id.desc(),
        )
    )
    latest_states: dict[tuple[UUID, str], str] = {}
    for parent_id, source_ref, state in rows:
        latest_states.setdefault((parent_id, source_ref), state)
    return {
        parent.id
        for parent in parents
        if latest_states.get(
            (parent.id, f"cover:{parent.cover_photo_id}:admin_preview"),
            "available",
        ) in {"available", "local", "archiving"}
    }


def _admin_photo_preview_available(
    db: Session, photo: PhotoAsset, *, allow_cover_thumbnail: bool,
) -> bool:
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == photo.folder_id,
        PhotoFolder.tenant_id == photo.tenant_id,
    ))
    if not folder:
        return False
    if folder.purpose == "content" and folder_media_is_local(db, folder):
        return True
    gallery = owned_record(db, ParentGallery, photo.parent_gallery_id, tenant_id=photo.tenant_id)
    if not gallery:
        return False
    if folder.purpose == "cover_assets":
        return _archive_object_state(
            db,
            tenant_id=photo.tenant_id,
            parent_gallery_id=gallery.id,
            source_ref=f"photo:{photo.id}:original",
            object_type="cover_asset",
        ) in {"available", "archiving"}
    if gallery.cover_photo_id != photo.id:
        return False
    if allow_cover_thumbnail:
        return _cover_thumbnail_is_local(db, gallery, photo.id)
    return False


def _cover_derivative(db: Session, photo_id: UUID, *, tenant_id: UUID) -> MediaDerivative | None:
    """Somente após resolver a capa da galeria e autorizar o acesso a ela."""
    return db.scalar(select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(
        MediaDerivative.photo_asset_id == photo_id,
        MediaDerivative.variant == "admin_preview",
        MediaDerivative.status == "ready",
    ))


def _client_preview_derivative(db: Session, photo_id: UUID, *, tenant_id: UUID) -> MediaDerivative | None:
    return db.scalar(
        select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(
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
    db.scalar(select(ParentGallery.id).where(ParentGallery.tenant_id == gallery.tenant_id).where(ParentGallery.id == gallery.id).with_for_update())
    folder = db.scalar(
        select(PhotoFolder).where(PhotoFolder.tenant_id == gallery.tenant_id).where(
            PhotoFolder.parent_gallery_id == gallery.id,
            PhotoFolder.derived_gallery_id.is_(None),
            PhotoFolder.purpose == "cover_assets",
        )
    )
    if folder:
        return folder
    minimum_position = db.scalar(
        select(func.min(PhotoFolder.position)).where(PhotoFolder.tenant_id == gallery.tenant_id).where(
            PhotoFolder.parent_gallery_id == gallery.id,
            PhotoFolder.derived_gallery_id.is_(None),
        )
    )
    folder = PhotoFolder(
        tenant_id=gallery.tenant_id,
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    folder_count = (
        db.scalar(
            select(func.count())
            .select_from(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id)
            .where(
                PhotoFolder.parent_gallery_id == gallery.id,
                PhotoFolder.derived_gallery_id.is_(None),
                PhotoFolder.purpose == "content",
                or_(PhotoFolder.audience_scope == "all", PhotoFolder.audience_scope.is_(None)),
            )
        )
        or 0
    )
    registration_count = (
        db.scalar(
            select(func.count())
            .select_from(ParentGalleryRegistration).where(ParentGalleryRegistration.tenant_id == tenant_id)
            .where(ParentGalleryRegistration.parent_gallery_id == gallery.id)
        )
        or 0
    )
    derived_count = (
        db.scalar(
            select(func.count())
            .select_from(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id)
            .where(DerivedGallery.parent_gallery_id == gallery.id)
        )
        or 0
    )
    public_capability = _active_gallery_capability(
        db, parent_gallery_id=gallery.id, scope="public_gallery",
        tenant_id=tenant_id,
    )
    cover_readiness = gallery_cover_readiness(db, gallery)
    return {
        "cover_readiness": cover_readiness,
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
                "status": "complete" if cover_readiness["status"] == "ready" else "pending",
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
        "actions": {
            "can_create_folder": gallery.active,
            "can_upload": gallery.active,
            "can_complete": cover_readiness["status"] == "ready",
        },
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/settings")
def parent_gallery_settings(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
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
        "payment_required": gallery.payment_required,
        "sales_message": gallery.sales_message or "",
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    lock_payment_account(db, tenant_id)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    if payload.active is True and not gallery.active and gallery.payment_required:
        released = db.scalar(select(PhotoFolder.id).where(
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.parent_gallery_id == gallery.id,
            PhotoFolder.purpose == "content",
            PhotoFolder.status == "released",
        ).limit(1))
        if released:
            require_payment_method(db, tenant_id=tenant_id)
    visual_fields = {"cover_title_font", "cover_title_color", "cover_title_size", "cover_title_position"}
    if visual_fields.intersection(payload.model_fields_set):
        readiness = gallery_cover_readiness(db, gallery)
        if readiness["status"] != "ready":
            raise HTTPException(status_code=409, detail=readiness["message"])
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(gallery, field, value.strip() if isinstance(value, str) else value)
    audit(db, "parent_gallery.settings_updated", str(gallery.id), tenant_id=tenant_id)
    db.commit()
    return parent_gallery_settings(parent_gallery_id, request, db)


@app.get("/admin/parent-galleries/{parent_gallery_id}/summary")
def parent_gallery_summary(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    folders = list(
        db.scalars(
            select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id).where(
                PhotoFolder.parent_gallery_id == gallery.id,
                PhotoFolder.derived_gallery_id.is_(None),
                PhotoFolder.purpose == "content",
            )
        )
    )
    photo_count = (
        db.scalar(
            select(func.count())
            .select_from(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                PhotoAsset.parent_gallery_id == gallery.id,
                PhotoAsset.derived_gallery_id.is_(None),
                PhotoFolder.purpose == "content",
            )
        )
        or 0
    )
    clients = parent_gallery_clients(parent_gallery_id, request, db)["clients"]
    public_capability = _active_gallery_capability(
        db, parent_gallery_id=gallery.id, scope="public_gallery",
        tenant_id=tenant_id,
    )
    deletion_operation = db.scalar(
        select(GalleryLifecycleOperation).where(GalleryLifecycleOperation.tenant_id == tenant_id)
        .where(
            GalleryLifecycleOperation.target_parent_gallery_id == gallery.id,
            GalleryLifecycleOperation.operation_type == "delete_parent_gallery",
        )
        .order_by(GalleryLifecycleOperation.created_at.desc(), GalleryLifecycleOperation.id.desc())
        .limit(1)
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
        "deletion_operation": lifecycle_operation_payload(deletion_operation)
        if deletion_operation and deletion_operation.status != "cancelled" else None,
    }


@app.put("/admin/parent-galleries/{parent_gallery_id}/cover")
def set_parent_gallery_cover(
    parent_gallery_id: UUID,
    payload: ParentGalleryCoverInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    gallery = db.scalar(select(ParentGallery).where(
        ParentGallery.id == gallery.id, ParentGallery.tenant_id == tenant_id,
    ).with_for_update())
    if not gallery or not gallery_media_writes_allowed(
        db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id,
    ):
        raise HTTPException(status_code=409, detail="A capa aguarda a conclusão do arquivamento da galeria.")
    photo = owned_record(db, PhotoAsset, payload.photo_id, tenant_id=tenant_id)
    if not photo or photo.parent_gallery_id != gallery.id:
        raise HTTPException(status_code=422, detail="A capa precisa pertencer a esta galeria.")
    photo_folder = owned_record(db, PhotoFolder, photo.folder_id, tenant_id=tenant_id)
    if (
        not photo_folder
        or (photo_folder.purpose == "content" and not folder_media_is_local(db, photo_folder))
        or (photo_folder.purpose == "cover_assets"
            and not folder_media_writes_allowed(db, photo_folder))
    ):
        raise HTTPException(status_code=409, detail="A foto da capa está arquivada ou indisponível.")
    dimensions = _client_preview_derivative(db, photo.id, tenant_id=tenant_id)
    if gallery.cover_photo_id != photo.id and (
        not dimensions or not dimensions.width or not dimensions.height
        or dimensions.width <= dimensions.height
    ):
        raise HTTPException(status_code=422, detail="Envie uma capa horizontal, com largura maior que a altura.")
    if not db.scalar(
        select(MediaDerivative.id).where(MediaDerivative.tenant_id == tenant_id).where(
            MediaDerivative.photo_asset_id == photo.id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
    ):
        raise HTTPException(
            status_code=409, detail="A foto ainda não possui prévia pronta para capa."
        )
    gallery.cover_photo_id = photo.id
    audit(db, "parent_gallery.cover_set", str(gallery.id), tenant_id=tenant_id)
    db.commit()
    return {"photo_id": str(photo.id), "preview_url": _cover_preview_url(db, gallery)}


@app.delete(
    "/admin/parent-galleries/{parent_gallery_id}/cover", status_code=status.HTTP_204_NO_CONTENT
)
def clear_parent_gallery_cover(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    gallery = db.scalar(select(ParentGallery).where(
        ParentGallery.id == gallery.id, ParentGallery.tenant_id == tenant_id,
    ).with_for_update())
    if not gallery or not gallery_media_writes_allowed(
        db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id,
    ):
        raise HTTPException(status_code=409, detail="A capa aguarda a conclusão do arquivamento da galeria.")
    gallery.cover_photo_id = None
    audit(db, "parent_gallery.cover_cleared", str(gallery.id), tenant_id=tenant_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/admin/parent-galleries/{parent_gallery_id}/sales")
def parent_gallery_sales(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    return {
        "available": True,
        "capabilities": [
            "pricing_tiers",
            "pix",
            "sales_message",
            "interactions",
        ],
        "payment_required": gallery.payment_required,
        "sales_message": gallery.sales_message or "",
        "payment_methods": payment_methods(db, tenant_id=tenant_id),
        "favorites_enabled": gallery.favorites_enabled,
        "comments_enabled": gallery.comments_enabled,
        **pricing_payload(db, gallery.id, tenant_id=tenant_id),
    }


@app.put("/admin/parent-galleries/{parent_gallery_id}/sales")
def update_parent_gallery_sales(
    parent_gallery_id: UUID,
    payload: ParentGallerySalesInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    lock_payment_account(db, tenant_id)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    if payload.payment_required:
        require_payment_method(db, tenant_id=tenant_id, status_code=422)
        tiers = save_parent_pricing(db, gallery.id, payload, tenant_id=tenant_id)
    else:
        tiers = []
    gallery.payment_required = payload.payment_required
    gallery.sales_message = payload.sales_message.strip() if payload.sales_message else None
    gallery.favorites_enabled = payload.favorites_enabled
    gallery.comments_enabled = payload.comments_enabled
    audit(db, "parent_gallery.sales_updated", str(gallery.id), tenant_id=tenant_id)
    db.commit()
    return {
        **parent_gallery_sales(parent_gallery_id, request, db),
        "has_downward_jump": has_downward_jump(tiers) if tiers else False,
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/details")
def parent_gallery_details(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    cover = owned_record(db, PhotoAsset, gallery.cover_photo_id, tenant_id=tenant_id) if gallery.cover_photo_id else None
    if cover and cover.parent_gallery_id != gallery.id:
        cover = None
    cover_folder = owned_record(db, PhotoFolder, cover.folder_id, tenant_id=tenant_id) if cover else None
    cover_derivative = _cover_derivative(db, cover.id, tenant_id=tenant_id) if cover else None
    cover_job = (
        db.scalar(select(MediaJob).where(MediaJob.tenant_id == tenant_id).where(MediaJob.photo_asset_id == cover.id)) if cover else None
    )
    cover_readiness = gallery_cover_readiness(db, gallery)
    cover_status = cover_readiness["status"]
    cover_options = (
        [
            {
                "id": str(cover.id),
                "name": cover.display_name or cover.filename,
                "source": cover_folder.purpose if cover_folder else "cover_assets",
                "status": cover_status,
                "preview_url": f"/admin/photo-assets/{cover.id}/preview"
                if cover_derivative and _admin_photo_preview_available(
                    db, cover, allow_cover_thumbnail=True,
                )
                else None,
                "width": cover_derivative.width if cover_derivative else None,
                "height": cover_derivative.height if cover_derivative else None,
                "error": cover_job.last_error if cover_status == "failed" and cover_job else None,
            }
        ]
        if cover
        else []
    )
    return {
        "available": True,
        "capabilities": ["cover", "title"],
        "cover_readiness": cover_readiness,
        "font_options": list(TITLE_FONT_OPTIONS),
        "cover_options": cover_options,
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

    tenant_id = directory_tenant_id(db, request)
    from app.tenant_closure import require_new_work
    require_new_work(db, tenant_id)
    admin_session = require_admin(request)
    from app.photographer_onboarding import require_upload_ready
    require_upload_ready(db, tenant_id=tenant_id, admin_id=admin_session.subject_id)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    gallery = db.scalar(select(ParentGallery).where(
        ParentGallery.id == gallery.id, ParentGallery.tenant_id == tenant_id,
    ).with_for_update())
    if not gallery or not gallery_media_writes_allowed(
        db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id,
    ):
        raise HTTPException(status_code=409, detail="A capa aguarda a conclusão do arquivamento da galeria.")
    if not gallery.active:
        raise HTTPException(status_code=409, detail="A galeria está bloqueada para novas fotos.")
    folder = _cover_assets_folder(db, gallery)
    storage_key = (
        f"tenants/{tenant_id}/covers/{gallery.id}/{sha256(payload.idempotency_key.encode('utf-8')).hexdigest()}.jpg"
    )
    asset = db.scalar(
        select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id).where(
            PhotoAsset.parent_gallery_id == gallery.id,
            PhotoAsset.derived_gallery_id.is_(None),
            PhotoAsset.storage_key == storage_key,
        )
    )
    if not asset:
        asset = PhotoAsset(
            tenant_id=gallery.tenant_id,
            parent_gallery_id=gallery.id,
            folder_id=folder.id,
            filename=payload.filename,
            display_name=payload.display_name,
            storage_key=storage_key,
            available=False,
        )
        db.add(asset)
        db.flush()
        audit(db, "parent_gallery.cover_photo_registered", str(asset.id), tenant_id=tenant_id)
    db.commit()
    return {
        "id": str(asset.id),
        "upload_url": f"/admin/photo-assets/{asset.id}/source",
    }


@app.get("/admin/parent-galleries/{parent_gallery_id}/facial-policy")
def admin_parent_gallery_facial_policy(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    try:
        settings = facial_settings_from_environment(verify_runtime_assets=False)
    except FacialConfigurationError as exc:
        raise HTTPException(
            status_code=503, detail="Configuração facial inválida."
        ) from exc
    return policy_payload(read_policy(db, parent_gallery_id, tenant_id=tenant_id), settings)


@app.put("/admin/parent-galleries/{parent_gallery_id}/facial-policy")
def prepare_parent_gallery_facial_policy(
    parent_gallery_id: UUID,
    payload: FacialPolicyInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    try:
        policy = prepare_policy(
            db,
            parent_gallery_id=parent_gallery_id,
            actor_admin_id=session.subject_id,
            draft=FacialPolicyDraft(**payload.model_dump()),
        )
        settings = facial_settings_from_environment(verify_runtime_assets=False)
        db.commit()
    except FacialPolicyError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FacialConfigurationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503, detail="Configuração facial inválida."
        ) from exc
    return policy_payload(policy, settings)


@app.post("/admin/parent-galleries/{parent_gallery_id}/facial-policy/activate")
def activate_parent_gallery_facial_policy(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    try:
        settings = facial_settings_from_environment(verify_runtime_assets=False)
        policy = activate_policy(
            db,
            parent_gallery_id=parent_gallery_id,
            actor_admin_id=session.subject_id,
            settings=settings,
        )
        cursor = None
        while True:
            page = enqueue_gallery_backfill_page(
                db,
                parent_gallery_id=parent_gallery_id,
                derivatives_root=derivatives_root(),
                cursor=cursor,
                settings=settings,
                tenant_id=tenant_id,
            )
            if page.completed:
                break
            cursor = page.next_cursor
        db.commit()
    except (FacialPolicyError, FacialConfigurationError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return policy_payload(policy, settings)


@app.post("/admin/parent-galleries/{parent_gallery_id}/facial-policy/suspend")
def suspend_parent_gallery_facial_policy(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    try:
        policy = suspend_policy(
            db,
            parent_gallery_id=parent_gallery_id,
            actor_admin_id=session.subject_id,
        )
        settings = facial_settings_from_environment(verify_runtime_assets=False)
        db.commit()
    except FacialPolicyError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return policy_payload(policy, settings)


@app.post("/admin/parent-galleries/{parent_gallery_id}/facial-policy/revoke")
def revoke_parent_gallery_facial_policy(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    try:
        policy = revoke_policy(
            db,
            parent_gallery_id=parent_gallery_id,
            actor_admin_id=session.subject_id,
        )
        settings = facial_settings_from_environment(verify_runtime_assets=False)
        db.commit()
    except FacialPolicyError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return policy_payload(policy, settings)


@app.get("/admin/parent-galleries/{parent_gallery_id}/facial-cleanup-proof")
def admin_parent_gallery_facial_cleanup_proof(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, int | bool]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    return facial_cleanup_proof(db, parent_gallery_id=parent_gallery_id, tenant_id=tenant_id)


@app.get("/admin/parent-galleries/{parent_gallery_id}/facial-index")
def admin_parent_gallery_facial_index(
    parent_gallery_id: UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    rollout = None
    try:
        try:
            settings = facial_settings_from_environment(
                verify_runtime_assets=False
            )
            rollout = read_rollout(
                db,
                environment=settings.environment,
                parent_gallery_id=parent_gallery_id,
                tenant_id=tenant_id,
            )
            processing_enabled = rollout_is_active(
                db,
                settings=settings,
                parent_gallery_id=parent_gallery_id,
                tenant_id=tenant_id,
            )
        except FacialConfigurationError:
            processing_enabled = False
        report = gallery_index_status(
            db,
            parent_gallery_id=parent_gallery_id,
            page=page,
            page_size=page_size,
            processing_enabled=processing_enabled,
            tenant_id=tenant_id,
        )
    except FacialStatusError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    from app.facial.analysis_metrics import gallery_analysis_metrics

    return {
        "state": report.state,
        "analysis": gallery_analysis_metrics(db, parent_gallery_id=parent_gallery_id, tenant_id=tenant_id),
        "rollout": rollout_status_payload(
            rollout,
            available=processing_enabled,
        ),
        "progress": {"ready": report.ready, "total": report.total},
        "queued": report.queued,
        "processing": report.processing,
        "failed": report.failed,
        "coverage": {
            "photos_with_faces": report.photos_with_faces,
            "total": report.total,
            "percent": round(
                report.photos_with_faces * 100 / report.total, 1
            ) if report.total else 0.0,
            "detected_faces": report.detected_faces,
        },
        "waiting_previews": report.waiting_previews,
        "unindexed": report.unindexed,
        "failures": list(report.failures),
        "pagination": {
            "page": report.page,
            "page_size": report.page_size,
            "total": report.failure_total,
        },
    }


@app.get("/admin/derived-galleries/{gallery_id}/facial-index")
def admin_private_gallery_facial_index(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id, allow_deleted_origin=True, tenant_id=tenant_id)
    photo_ids = list(
        db.scalars(
            select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id).where(PhotoAsset.derived_gallery_id == gallery.id)
        )
    )
    jobs = list(
        db.scalars(
            select(FacialJob)
            .where(
                FacialJob.derived_gallery_id == gallery.id,
                FacialJob.kind == "index",
            )
            .order_by(FacialJob.created_at.desc(), FacialJob.id.desc())
        )
    )
    latest: dict[UUID, FacialJob] = {}
    for job in jobs:
        if job.photo_asset_id and job.photo_asset_id not in latest:
            latest[job.photo_asset_id] = job
    photos_with_faces = (
        db.scalar(
            select(func.count(func.distinct(PhotoFaceEmbedding.photo_asset_id))).where(
                PhotoFaceEmbedding.derived_gallery_id == gallery.id
            )
        )
        or 0
    )
    detected_faces = (
        db.scalar(
            select(func.count(PhotoFaceEmbedding.id)).where(
                PhotoFaceEmbedding.derived_gallery_id == gallery.id
            )
        )
        or 0
    )
    total = len(photo_ids)
    completed = sum(job.status == "completed" for job in latest.values())
    failed = sum(job.status == "failed" for job in latest.values())
    queued = sum(job.status == "queued" for job in latest.values())
    processing = sum(job.status == "processing" for job in latest.values())
    return {
        "state": (
            "failed"
            if failed
            else "completed"
            if total and completed == total
            else "processing"
            if processing or queued
            else "waiting"
        ),
        "progress": {"ready": completed, "total": total},
        "queued": queued,
        "processing": processing,
        "failed": failed,
        "unindexed": max(0, total - len(latest)),
        "coverage": {
            "photos_with_faces": photos_with_faces,
            "total": total,
            "percent": round(photos_with_faces * 100 / total, 1) if total else 0.0,
            "detected_faces": detected_faces,
        },
    }


@app.post("/admin/parent-galleries/{parent_gallery_id}/facial-index/retry")
def retry_parent_gallery_facial_index(
    parent_gallery_id: UUID,
    payload: FacialIndexRetryInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, int]:
    tenant_id = directory_tenant_id(db, request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    require_same_origin(request)
    session = current_session(request, Role.ADMIN)
    try:
        settings = facial_settings_from_environment(verify_runtime_assets=False)
        if not rollout_is_active(
            db,
            settings=settings,
            parent_gallery_id=parent_gallery_id,
         tenant_id=tenant_id):
            raise FacialStatusError(
                "Reconhecimento facial indisponível para esta galeria."
            )
        changed = retry_failed_index_jobs(
            db,
            parent_gallery_id=parent_gallery_id,
            job_ids=set(payload.job_ids),
            tenant_id=tenant_id,
        )
    except (FacialConfigurationError, FacialStatusError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit(
        db,
        "facial.index_retry_requested",
        f"gallery_id:{parent_gallery_id};actor_id:{session.subject_id};count:{changed}",
        tenant_id=tenant_id,
    )
    db.commit()
    return {"retried": changed}


@app.post("/admin/parent-galleries/{parent_gallery_id}/facial-index/reprocess")
def reprocess_parent_gallery_facial_index(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, int]:
    tenant_id = directory_tenant_id(db, request)
    require_same_origin(request)
    current_session(request, Role.ADMIN)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    try:
        settings = facial_settings_from_environment(verify_runtime_assets=False)
        if not rollout_is_active(
            db,
            settings=settings,
            parent_gallery_id=parent_gallery_id,
         tenant_id=tenant_id):
            raise FacialStatusError(
                "Reconhecimento facial indisponível para esta galeria."
            )
        report = gallery_index_status(
            db,
            parent_gallery_id=parent_gallery_id,
            processing_enabled=True,
            tenant_id=tenant_id,
        )
        scanned = 0
        if report.unindexed:
            reconciliation = reconcile_gallery_index(
                db,
                parent_gallery_id=parent_gallery_id,
                derivatives_root=derivatives_root(),
                settings=settings,
                page_size=100,
                tenant_id=tenant_id,
            )
            scanned = reconciliation.photos_scanned
        retried = retry_all_failed_index_jobs(
            db,
            parent_gallery_id=parent_gallery_id,
            tenant_id=tenant_id,
        )
    except (FacialConfigurationError, FacialJobError, FacialStatusError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit(
        db,
        "facial.index_reprocess_requested",
        f"scope_count:1;photos_scanned:{scanned};retried:{retried}",
        tenant_id=tenant_id,
    )
    db.commit()
    return {"photos_scanned": scanned, "retried": retried}


@app.get("/admin/parent-galleries/{parent_gallery_id}/photos")
def admin_parent_gallery_photos(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    photos = db.scalars(
        select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id)
        .where(
            PhotoAsset.parent_gallery_id == parent_gallery_id,
            PhotoAsset.derived_gallery_id.is_(None),
        )
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


    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    photos = list(
        db.scalars(
            select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                PhotoAsset.parent_gallery_id == parent_gallery_id,
                PhotoAsset.derived_gallery_id.is_(None),
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
            select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id).where(
                PhotoFolder.parent_gallery_id == parent_gallery_id,
                PhotoFolder.derived_gallery_id.is_(None),
                PhotoFolder.purpose == "content",
            )
        )
    }
    media_states = folder_media_states_by_id(
        db, folder_ids=set(folders), tenant_id=tenant_id,
    )
    photos = [photo for photo in photos if media_states.get(photo.folder_id) == "available"]
    ready_derivatives = (
        {
            derivative.photo_asset_id: derivative
            for derivative in db.scalars(
                select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(
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


@app.get("/admin/parent-galleries/{parent_gallery_id}/private-folders")
def admin_parent_gallery_private_folders(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    from app.private_folder_overview import private_folder_overview

    return {"galleries": private_folder_overview(db, parent_gallery_id, tenant_id=tenant_id)}


@app.get("/admin/parent-galleries/{parent_gallery_id}/folders")
def admin_parent_gallery_folders(
    parent_gallery_id: UUID,
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
    include_restricted: bool = Query(default=False),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    folders = list(
        db.scalars(
            select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id)
            .where(
                PhotoFolder.parent_gallery_id == parent_gallery_id,
                PhotoFolder.derived_gallery_id.is_(None),
                PhotoFolder.purpose == "content",
                True if include_restricted else or_(PhotoFolder.audience_scope == "all", PhotoFolder.audience_scope.is_(None)),
            )
            .order_by(PhotoFolder.position, PhotoFolder.created_at)
        )
    )
    client_names_by_folder: dict[UUID, list[str]] = {}
    if include_restricted and folders:
        for folder_id, client_name in db.execute(
            select(FolderClientGrant.folder_id, Client.full_name)
            .join(Client, Client.id == FolderClientGrant.client_id)
            .where(
                FolderClientGrant.tenant_id == tenant_id,
                Client.tenant_id == tenant_id,
                FolderClientGrant.parent_gallery_id == parent_gallery_id,
                FolderClientGrant.folder_id.in_([folder.id for folder in folders]),
            )
            .order_by(FolderClientGrant.folder_id, Client.full_name, Client.id)
        ):
            client_names_by_folder.setdefault(folder_id, []).append(client_name)
    rows = []
    for folder in folders:
        media_state = folder_media_state(db, folder)
        count = (
            db.scalar(
                select(func.count())
                .select_from(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id)
                .where(PhotoAsset.folder_id == folder.id)
            )
            or 0
        )
        preview_photo_id = db.scalar(
            select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id)
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
                select(PhotoAsset, MediaJob, MediaDerivative).where(or_(MediaDerivative.id.is_(None), MediaDerivative.tenant_id == tenant_id), or_(MediaJob.id.is_(None), MediaJob.tenant_id == tenant_id), PhotoAsset.tenant_id == tenant_id)
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
        folder_row = {
            "id": str(folder.id),
            "name": folder.name,
            "audience_scope": folder.audience_scope or "all",
            "status": folder.status,
            "position": folder.position,
            "photo_count": count,
            "publication_counts": state_counts,
            "preview_url": f"/admin/photo-assets/{preview_photo_id}/watermarked-preview"
            if preview_photo_id and media_state in {"available", "archiving"}
            else None,
            "media_state": media_state,
            "released_at": folder.released_at.isoformat() if folder.released_at else None,
            "access_duration_days": folder.access_duration_days,
            "can_renew_deadline": public_folder_deadline_renewable(
                db, folder, media_state=media_state,
            ),
            "access_expires_at": folder.access_expires_at.isoformat()
            if folder.access_expires_at else None,
        }
        if include_restricted and folder.audience_scope == "selected":
            folder_row["client_names"] = client_names_by_folder.get(folder.id, [])
        rows.append(folder_row)
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
    tenant_id = directory_tenant_id(db, request)
    from app.tenant_closure import require_new_work
    require_new_work(db, tenant_id)
    require_admin(request)
    parent = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    if not parent.active:
        raise HTTPException(status_code=409, detail="A galeria está bloqueada para novas pastas.")
    # Serializa a criação da pasta com mudanças concorrentes na galeria.
    parent = db.scalar(select(ParentGallery).where(
        ParentGallery.id == parent_gallery_id, ParentGallery.tenant_id == tenant_id,
    ).with_for_update())
    if not parent:
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    if not parent.active or parent.lifecycle_status != "active":
        raise HTTPException(status_code=409, detail="A galeria está bloqueada para novas pastas.")
    last_position = db.scalar(
        select(func.max(PhotoFolder.position)).where(PhotoFolder.tenant_id == tenant_id).where(
            PhotoFolder.parent_gallery_id == parent_gallery_id,
            PhotoFolder.derived_gallery_id.is_(None),
            PhotoFolder.purpose == "content",
        )
    )
    position = (last_position if last_position is not None else -1) + 1
    folder = PhotoFolder(
        parent_gallery_id=parent_gallery_id,
        name=payload.name.strip(),
        access_duration_days=payload.access_duration_days,
        position=position,
        purpose="content",
        audience_scope="all",
        tenant_id=tenant_id,
    )
    db.add(folder)
    db.flush()
    from app.folder_processing import initialize_folder_processing

    initialize_folder_processing(db, folder)
    audit(db, "photo_folder.created", str(folder.id), tenant_id=tenant_id)
    db.commit()
    return {
        "id": str(folder.id), "status": folder.status, "position": folder.position,
        "access_duration_days": folder.access_duration_days,
        "access_expires_at": folder.access_expires_at.isoformat()
        if folder.access_expires_at else None,
    }


def _admin_linked_gallery_client(
    db: Session, *, tenant_id: UUID, parent_gallery_id: UUID, client_id: UUID
) -> ParentGalleryRegistration:
    registration = db.scalar(select(ParentGalleryRegistration).where(ParentGalleryRegistration.tenant_id == tenant_id).where(
        ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
        ParentGalleryRegistration.client_id == client_id,
        ParentGalleryRegistration.status.in_(("active", "pending")),
    ))
    if not registration:
        raise HTTPException(status_code=404, detail="Cliente não vinculada a esta galeria.")
    return registration


@app.get("/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/folders")
def admin_client_restricted_folders(
    parent_gallery_id: UUID, client_id: UUID, request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    _admin_linked_gallery_client(
        db, parent_gallery_id=parent_gallery_id, client_id=client_id,
        tenant_id=tenant_id,
    )
    folders = list(db.scalars(select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id)
        .join(FolderClientGrant, FolderClientGrant.folder_id == PhotoFolder.id)
        .where(
            FolderClientGrant.parent_gallery_id == parent_gallery_id,
            FolderClientGrant.client_id == client_id,
            PhotoFolder.audience_scope == "selected",
            PhotoFolder.derived_gallery_id.is_(None),
            PhotoFolder.purpose == "content",
        )
        .order_by(PhotoFolder.position, PhotoFolder.created_at)))
    assigned_by_folder: dict[UUID, list[str]] = defaultdict(list)
    if folders:
        for grant_folder_id, assigned_client_id in db.execute(select(
            FolderClientGrant.folder_id, FolderClientGrant.client_id
        ).where(FolderClientGrant.tenant_id == tenant_id).where(FolderClientGrant.folder_id.in_([folder.id for folder in folders]))):
            assigned_by_folder[grant_folder_id].append(str(assigned_client_id))
    preview_by_folder = {
        folder.id: db.scalar(select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id)
            .join(MediaDerivative, MediaDerivative.photo_asset_id == PhotoAsset.id)
            .where(PhotoAsset.folder_id == folder.id,
                   MediaDerivative.variant == "client_preview",
                   MediaDerivative.status == "ready")
            .order_by(PhotoAsset.created_at, PhotoAsset.filename)
            .limit(1))
        for folder in folders
    }
    return {"folders": [{
        "id": str(folder.id), "name": folder.name, "status": folder.status,
        "position": folder.position,
        "assigned_client_ids": assigned_by_folder[folder.id],
        "photo_count": db.scalar(select(func.count(PhotoAsset.id)).where(PhotoAsset.tenant_id == tenant_id).where(
            PhotoAsset.folder_id == folder.id
        )) or 0,
        "released_at": folder.released_at.isoformat() if folder.released_at else None,
        "access_duration_days": folder.access_duration_days,
        "access_expires_at": folder.access_expires_at.isoformat()
        if folder.access_expires_at else None,
        "media_state": folder_media_state(db, folder),
        "preview_url": f"/admin/photo-assets/{preview_by_folder[folder.id]}/watermarked-preview"
        if preview_by_folder[folder.id]
        and folder_media_state(db, folder) in {"available", "archiving"} else None,
    } for folder in folders]}


@app.post(
    "/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/folders",
    status_code=status.HTTP_201_CREATED,
)
def create_admin_client_restricted_folder(
    parent_gallery_id: UUID, client_id: UUID, payload: PhotoFolderInput,
    request: Request, db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    from app.tenant_closure import require_new_work
    require_new_work(db, tenant_id)
    require_admin(request)
    parent = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    if not parent.active:
        raise HTTPException(status_code=409, detail="A galeria está bloqueada para novas pastas.")
    _admin_linked_gallery_client(
        db, parent_gallery_id=parent_gallery_id, client_id=client_id,
        tenant_id=tenant_id,
    )
    db.scalar(select(ParentGallery.id).where(ParentGallery.tenant_id == tenant_id).where(
        ParentGallery.id == parent_gallery_id
    ).with_for_update())
    state = db.scalar(select(GalleryClientState).where(GalleryClientState.tenant_id == tenant_id).where(
        GalleryClientState.parent_gallery_id == parent_gallery_id,
        GalleryClientState.client_id == client_id,
    ).with_for_update())
    if not state:
        state = GalleryClientState(
            parent_gallery_id=parent_gallery_id, client_id=client_id, status="active",
            tenant_id=tenant_id,
        )
        db.add(state)
        db.flush()
    if state.status != "active":
        raise HTTPException(status_code=409, detail="O acesso desta cliente está bloqueado.")
    last_position = db.scalar(select(func.max(PhotoFolder.position)).where(PhotoFolder.tenant_id == tenant_id).where(
        PhotoFolder.parent_gallery_id == parent_gallery_id,
        PhotoFolder.derived_gallery_id.is_(None),
        PhotoFolder.purpose == "content",
    ))
    folder = PhotoFolder(
        parent_gallery_id=parent_gallery_id, name=payload.name.strip(),
        access_duration_days=payload.access_duration_days,
        position=(last_position if last_position is not None else -1) + 1,
        purpose="content", audience_scope="selected",
        tenant_id=tenant_id,
    )
    db.add(folder)
    db.flush()
    db.add(FolderClientGrant(
        folder_id=folder.id, parent_gallery_id=parent_gallery_id,
        client_id=client_id,
        tenant_id=tenant_id,
    ))
    from app.folder_processing import initialize_folder_processing

    initialize_folder_processing(db, folder)
    audit(db, "photo_folder.restricted_created", str(folder.id), tenant_id=tenant_id)
    db.commit()
    return {
        "id": str(folder.id), "status": folder.status, "position": folder.position,
        "access_duration_days": folder.access_duration_days,
        "access_expires_at": folder.access_expires_at.isoformat()
        if folder.access_expires_at else None,
    }


@app.post(
    "/admin/parent-galleries/{parent_gallery_id}/folders/{folder_id}/clients/{client_id}",
    status_code=status.HTTP_201_CREATED,
)
def grant_restricted_folder_client(
    parent_gallery_id: UUID, folder_id: UUID, client_id: UUID,
    request: Request, db: Session = Depends(db_session),
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    folder = db.scalar(select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id).where(
        PhotoFolder.id == folder_id,
        PhotoFolder.parent_gallery_id == parent_gallery_id,
        PhotoFolder.derived_gallery_id.is_(None),
        PhotoFolder.audience_scope == "selected",
        PhotoFolder.purpose == "content",
    ).with_for_update())
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta restrita não encontrada.")
    _admin_linked_gallery_client(
        db, parent_gallery_id=parent_gallery_id, client_id=client_id,
        tenant_id=tenant_id,
    )
    existing = db.scalar(select(FolderClientGrant).where(FolderClientGrant.tenant_id == tenant_id).where(
        FolderClientGrant.folder_id == folder_id,
        FolderClientGrant.client_id == client_id,
    ))
    if not existing:
        if db.scalar(select(FolderClientGrant.id).where(FolderClientGrant.tenant_id == tenant_id).where(
            FolderClientGrant.folder_id == folder_id
        ).limit(1)):
            raise HTTPException(
                status_code=409,
                detail="Esta pasta restrita já pertence a outra cliente.",
            )
        state = db.scalar(select(GalleryClientState).where(GalleryClientState.tenant_id == tenant_id).where(
            GalleryClientState.parent_gallery_id == parent_gallery_id,
            GalleryClientState.client_id == client_id,
        ))
        if not state:
            db.add(GalleryClientState(
                parent_gallery_id=parent_gallery_id, client_id=client_id, status="active",
                tenant_id=tenant_id,
            ))
            db.flush()
        db.add(FolderClientGrant(
            folder_id=folder_id, parent_gallery_id=parent_gallery_id,
            client_id=client_id,
            tenant_id=tenant_id,
        ))
        db.flush()
        if folder.status == "released":
            available_photo_ids = set(db.scalars(select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id).where(
                PhotoAsset.folder_id == folder.id,
                PhotoAsset.available,
            )))
            record_restricted_folder_ready(
                db, folder=folder, photo_ids=available_photo_ids,
                batch_key="grant", client_ids={client_id},
            )
        audit(db, "photo_folder.client_granted", str(folder_id), tenant_id=tenant_id)
        db.commit()
    return {"folder_id": str(folder_id), "client_id": str(client_id)}


@app.delete(
    "/admin/parent-galleries/{parent_gallery_id}/folders/{folder_id}/clients/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_restricted_folder_client(
    parent_gallery_id: UUID, folder_id: UUID, client_id: UUID,
    request: Request, db: Session = Depends(db_session),
) -> Response:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    db.scalar(select(Client.id).where(Client.tenant_id == tenant_id).where(Client.id == client_id).with_for_update())
    folder = db.scalar(select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id).where(
        PhotoFolder.id == folder_id,
        PhotoFolder.parent_gallery_id == parent_gallery_id,
        PhotoFolder.derived_gallery_id.is_(None),
        PhotoFolder.audience_scope == "selected",
        PhotoFolder.purpose == "content",
    ).with_for_update())
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta restrita não encontrada.")
    grant = db.scalar(select(FolderClientGrant).where(FolderClientGrant.tenant_id == tenant_id).where(
        FolderClientGrant.folder_id == folder_id,
        FolderClientGrant.client_id == client_id,
    ))
    if not grant:
        raise HTTPException(status_code=404, detail="Atribuição não encontrada.")
    count = db.scalar(select(func.count(FolderClientGrant.id)).where(FolderClientGrant.tenant_id == tenant_id).where(
        FolderClientGrant.folder_id == folder_id
    )) or 0
    if count <= 1:
        raise HTTPException(status_code=409, detail="A pasta restrita precisa manter uma cliente atribuída.")
    db.execute(delete(PhotoSelection).where(
        PhotoSelection.parent_gallery_id == parent_gallery_id,
        PhotoSelection.client_id == client_id,
        PhotoSelection.photo_asset_id.in_(select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id).where(
            PhotoAsset.folder_id == folder_id
        )),
    ))
    db.delete(grant)
    audit(db, "photo_folder.client_revoked", str(folder_id), tenant_id=tenant_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.patch("/admin/photo-folders/{folder_id}")
def rename_photo_folder(
    folder_id: UUID,
    payload: PhotoFolderRenameInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    folder = owned_record(db, PhotoFolder, folder_id, tenant_id=tenant_id)
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if folder.derived_gallery_id:
        require_derived_gallery_mutable(
            db, folder.derived_gallery_id, allow_deleted_origin=True,
            tenant_id=tenant_id,
        )
    else:
        require_parent_gallery_mutable(db, folder.parent_gallery_id, tenant_id=tenant_id)
    folder.name = payload.name
    audit(db, "photo_folder.renamed", str(folder.id), tenant_id=tenant_id)
    db.commit()
    return {"id": str(folder.id), "name": folder.name}


@app.patch("/admin/photo-folders/{folder_id}/renew-deadline")
def renew_public_photo_folder_deadline(
    folder_id: UUID,
    payload: PhotoFolderDeadlineInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    from app.folder_access import REOPENING_WINDOW
    from app.media_archive_notices import supersede_window_notices_for_folder
    from app.tenant_closure import require_new_work

    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    parent_id = db.scalar(select(PhotoFolder.parent_gallery_id).where(
        PhotoFolder.id == folder_id,
        PhotoFolder.tenant_id == tenant_id,
        PhotoFolder.purpose == "content",
    ))
    if parent_id is None:
        raise HTTPException(404, "Pasta não encontrada.")
    # Serializa encerramento sem bloquear KEY SHARE de FKs do arquivo frio.
    require_new_work(db, tenant_id, no_key_update=True)
    db.scalar(select(ParentGallery).where(
        ParentGallery.id == parent_id, ParentGallery.tenant_id == tenant_id,
    ).with_for_update().execution_options(populate_existing=True))
    require_parent_gallery_mutable(db, parent_id, tenant_id=tenant_id)
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == folder_id, PhotoFolder.tenant_id == tenant_id,
        PhotoFolder.parent_gallery_id == parent_id,
    ).with_for_update().execution_options(populate_existing=True))
    instant = now()
    if not folder or not public_folder_deadline_renewable(db, folder, at=instant):
        raise HTTPException(
            409, "A renovação exige pasta pública expirada há até 30 dias e mídia disponível.",
        )
    try:
        new_expiry = instant + timedelta(days=payload.access_duration_days)
        archive_deadline = new_expiry + REOPENING_WINDOW
    except OverflowError:
        raise HTTPException(422, "Informe uma duração válida em dias.") from None
    folder.access_duration_days = payload.access_duration_days
    folder.access_expires_at = new_expiry
    supersede_window_notices_for_folder(
        db, tenant_id=tenant_id, folder_id=folder.id,
        current_deadline=archive_deadline, at=instant,
    )
    audit(db, "photo_folder.deadline_renewed", str(folder.id), tenant_id=tenant_id)
    db.commit()
    return {
        "id": str(folder.id), "access_duration_days": folder.access_duration_days,
        "access_expires_at": new_expiry.isoformat(),
        "released_at": folder.released_at.isoformat(), "can_renew_deadline": False,
    }


@app.patch("/admin/photo-folders/{folder_id}/deadline")
def configure_photo_folder_deadline(
    folder_id: UUID,
    payload: PhotoFolderDeadlineInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    folder = db.scalar(
        select(PhotoFolder)
        .where(PhotoFolder.tenant_id == tenant_id, PhotoFolder.id == folder_id)
        .with_for_update()
    )
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if folder.derived_gallery_id:
        require_derived_gallery_mutable(
            db, folder.derived_gallery_id, allow_deleted_origin=True,
            tenant_id=tenant_id,
        )
    else:
        require_parent_gallery_mutable(db, folder.parent_gallery_id, tenant_id=tenant_id)
    if folder.released_at is not None:
        if folder.access_duration_days is not None or folder.access_expires_at is not None:
            raise HTTPException(
                status_code=409,
                detail="O prazo de uma pasta liberada não pode ser alterado diretamente.",
            )
        # Pastas legadas começam indeterminadas; seu primeiro prazo começa agora.
        folder.access_expires_at = now() + timedelta(days=payload.access_duration_days)
    folder.access_duration_days = payload.access_duration_days
    audit(db, "photo_folder.deadline_configured", str(folder.id), tenant_id=tenant_id)
    db.commit()
    return {
        "id": str(folder.id),
        "access_duration_days": folder.access_duration_days,
        "access_expires_at": folder.access_expires_at.isoformat()
        if folder.access_expires_at else None,
        "released_at": folder.released_at.isoformat() if folder.released_at else None,
    }


@app.delete("/admin/photo-folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo_folder(
    folder_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    context = owned_record(db, PhotoFolder, folder_id, tenant_id=tenant_id)
    if context:
        lock_removal_clients(db, context.parent_gallery_id, tenant_id=tenant_id)
    folder = db.scalar(select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id).where(PhotoFolder.id == folder_id).with_for_update())
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if not folder_media_writes_allowed(db, folder):
        raise HTTPException(status_code=409, detail="A pasta está em uma etapa de arquivo ou recuperação.")
    if folder.derived_gallery_id:
        require_derived_gallery_mutable(
            db, folder.derived_gallery_id, allow_deleted_origin=True,
            tenant_id=tenant_id,
        )
    else:
        require_parent_gallery_mutable(db, folder.parent_gallery_id, tenant_id=tenant_id)
    photos = list(db.scalars(select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id).where(
        PhotoAsset.folder_id == folder.id
    ).order_by(PhotoAsset.id).with_for_update()))
    _assert_photo_credit_operations_settled(
        db, tenant_id, [photo.id for photo in photos],
    )
    preserve_asset_history(db, folder.parent_gallery_id, photo_ids=[photo.id for photo in photos], tenant_id=tenant_id)
    paths_to_remove: list[Path] = []
    for photo in photos:
        paths_to_remove.extend(_delete_photo_records(db, photo, tenant_id=tenant_id))
    db.flush()
    audit(db, "photo_folder.deleted", str(folder.id), tenant_id=tenant_id)
    db.execute(delete(FolderProcessingSettings).where(
        FolderProcessingSettings.tenant_id == tenant_id,
        FolderProcessingSettings.folder_id == folder.id,
    ))
    db.delete(folder)
    cleanup = enqueue_file_cleanup(db, paths_to_remove, tenant_id=tenant_id)
    db.commit()
    process_file_cleanup(db, cleanup)
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"X-Asset-Cleanup": cleanup.status})


@app.get("/admin/photo-folders/{folder_id}/photos")
def admin_photo_folder_photos(
    folder_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Estado administrativo por arquivo, sem expor a origem privada."""
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    if not (folder := owned_record(db, PhotoFolder, folder_id, tenant_id=tenant_id)) or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    photos = list(
        db.scalars(
            select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id)
            .where(PhotoAsset.folder_id == folder.id)
            .order_by(PhotoAsset.filename)
        )
    )
    parent = owned_record(db, ParentGallery, folder.parent_gallery_id, tenant_id=tenant_id)
    media_state = folder_media_state(db, folder)
    media_local = media_state in {"available", "archiving"}
    rows = []
    fingerprints = {
        photo_id: source_fingerprint
        for photo_id, source_fingerprint in db.execute(
            select(PhotoAnalysis.photo_asset_id, PhotoAnalysis.source_fingerprint).where(
                PhotoAnalysis.tenant_id == tenant_id,
                PhotoAnalysis.photo_asset_id.in_([photo.id for photo in photos]),
            )
        ).all()
    } if photos else {}
    for photo in photos:
        job = db.scalar(select(MediaJob).where(MediaJob.tenant_id == tenant_id).where(MediaJob.photo_asset_id == photo.id))
        derivative = _client_preview_derivative(db, photo.id, tenant_id=tenant_id)
        rows.append(
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "content_fingerprint": (
                    photographer_credits.fingerprint_from_storage_key(photo.storage_key)
                    or fingerprints.get(photo.id)
                ),
                "preview_url": f"/admin/photo-assets/{photo.id}/watermarked-preview"
                if derivative and media_local
                else None,
                "status": job.status if job else "not_imported",
                "publication_state": _photo_publication_state(photo, job, derivative),
                "available": photo.available,
                "width": derivative.width if derivative else None,
                "height": derivative.height if derivative else None,
                "error": job.last_error if job else None,
                "can_delete": media_state == "available",
                "is_cover": bool(parent and parent.cover_photo_id == photo.id),
            }
        )
    return {
        "folder": {
            "id": str(folder.id), "status": folder.status,
            "media_state": media_state,
        },
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

    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.tenant_id == tenant_id, PhotoFolder.id == folder_id,
    ).with_for_update())
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    lock_removal_clients(db, folder.parent_gallery_id, tenant_id=tenant_id)
    photo = db.scalar(select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id).where(PhotoAsset.id == photo_id).with_for_update())
    if (
        not photo
        or photo.folder_id != folder.id
        or photo.parent_gallery_id != folder.parent_gallery_id
        or photo.derived_gallery_id != folder.derived_gallery_id
    ):
        raise HTTPException(status_code=404, detail="Foto não encontrada nesta pasta.")
    if not folder_media_writes_allowed(db, folder):
        raise HTTPException(status_code=409, detail="A pasta está em uma etapa de arquivo ou recuperação.")
    if folder.derived_gallery_id:
        require_derived_gallery_mutable(
            db, folder.derived_gallery_id, allow_deleted_origin=True,
            tenant_id=tenant_id,
        )
    else:
        require_parent_gallery_mutable(db, folder.parent_gallery_id, tenant_id=tenant_id)
    _assert_photo_credit_operations_settled(db, tenant_id, [photo.id])
    preserve_asset_history(db, folder.parent_gallery_id, photo_ids=[photo.id], tenant_id=tenant_id)
    paths_to_remove = _delete_photo_records(db, photo, tenant_id=tenant_id)
    cleanup = enqueue_file_cleanup(db, paths_to_remove, tenant_id=tenant_id)
    db.commit()
    process_file_cleanup(db, cleanup)
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"X-Asset-Cleanup": cleanup.status})


def _assert_photo_credit_operations_settled(
    db: Session, tenant_id: UUID, photo_ids: list[UUID],
) -> None:
    if not photo_ids:
        return
    pending = db.scalar(
        select(PhotoCreditOperation.id)
        .where(
            PhotoCreditOperation.tenant_id == tenant_id,
            PhotoCreditOperation.photo_asset_id_snapshot.in_(photo_ids),
            PhotoCreditOperation.status.in_(("reserved", "reconciliation_required")),
        )
        .limit(1)
        .with_for_update(of=PhotoCreditOperation)
    )
    if pending is not None:
        raise HTTPException(
            status_code=409,
            detail="A foto aguarda reconciliação do upload antes de poder ser excluída.",
        )


def _delete_photo_records(db: Session, photo: PhotoAsset, *, tenant_id: UUID) -> list[Path]:
    """Remove registros na transação do chamador; arquivos só após commit."""
    require_active_owner(db, tenant_id)
    if photo.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    _assert_photo_credit_operations_settled(db, tenant_id, [photo.id])
    from app.preview_adjustment.cleanup import photo_files

    paths_to_remove = photo_files(photo.id, tenant_id=tenant_id) + historical_paths(db, [photo.id], tenant_id=tenant_id)
    try:
        paths_to_remove.append(safe_source_path(photo))
    except ValueError:
        # Um caminho corrompido não deve impedir a limpeza dos registros, nem autorizar apagar fora do storage.
        pass
    derivatives = list(
        db.scalars(select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id, MediaDerivative.photo_asset_id == photo.id))
    )
    for derivative in derivatives:
        try:
            paths_to_remove.append(safe_derivative_path(derivative))
        except ValueError:
            continue
    parent = owned_record(db, ParentGallery, photo.parent_gallery_id, tenant_id=tenant_id)
    if not photo.derived_gallery_id and parent and parent.cover_photo_id == photo.id:
        parent.cover_photo_id = None
    db.execute(delete(PhotoComment).where(PhotoComment.tenant_id == tenant_id).where(PhotoComment.photo_asset_id == photo.id))
    db.execute(delete(PhotoFavorite).where(PhotoFavorite.tenant_id == tenant_id).where(PhotoFavorite.photo_asset_id == photo.id))
    db.execute(delete(PhotoView).where(PhotoView.tenant_id == tenant_id).where(PhotoView.photo_asset_id == photo.id))
    db.execute(delete(PhotoSelection).where(PhotoSelection.tenant_id == tenant_id).where(PhotoSelection.photo_asset_id == photo.id))
    db.execute(delete(DerivedGalleryPhotoOrigin).where(DerivedGalleryPhotoOrigin.tenant_id == tenant_id).where(
        DerivedGalleryPhotoOrigin.derived_gallery_photo_id.in_(select(DerivedGalleryPhoto.id).where(DerivedGalleryPhoto.tenant_id == tenant_id).where(
            DerivedGalleryPhoto.photo_asset_id == photo.id))))
    db.execute(update(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id).where(SaleOrderItem.photo_asset_id == photo.id).values(photo_asset_id=None))
    db.execute(delete(DerivedGalleryPhoto).where(DerivedGalleryPhoto.tenant_id == tenant_id).where(DerivedGalleryPhoto.photo_asset_id == photo.id))
    db.execute(delete(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id, MediaDerivative.photo_asset_id == photo.id))
    db.execute(delete(MediaJob).where(MediaJob.tenant_id == tenant_id, MediaJob.photo_asset_id == photo.id))
    # O ledger conserva o snapshot financeiro, mas não pode reter a foto fisicamente apagada.
    db.execute(update(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant_id,
        PhotoCreditOperation.photo_asset_id == photo.id,
    ).values(photo_asset_id=None))
    from app.facial.purge import purge_photo_records

    purge_photo_records(
        db,
        tenant_id=tenant_id,
        parent_gallery_id=photo.parent_gallery_id,
        photo_asset_id=photo.id,
    )
    db.delete(photo)
    audit(db, "photo_asset.deleted", str(photo.id), tenant_id=tenant_id)
    return paths_to_remove


def _remove_photo_files(paths_to_remove: list[Path]) -> None:
    for path in paths_to_remove:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            # A limpeza física é idempotente. Uma nova rotina de mídia poderá remover o resíduo seguro.
            continue


@app.delete("/admin/photo-folders/{folder_id}/photos")
def delete_folder_photo_assets(
    folder_id: UUID,
    payload: PhotoBulkDeleteInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, list[str]]:
    """Exclui em massa as fotos elegíveis e informa as protegidas."""

    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    folder = owned_record(db, PhotoFolder, folder_id, tenant_id=tenant_id)
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    require_parent_gallery_mutable(db, folder.parent_gallery_id, tenant_id=tenant_id)
    deleted: list[str] = []
    blocked: list[str] = []
    missing: list[str] = []
    for photo_id in dict.fromkeys(payload.photo_ids):
        photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
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

    tenant_id = directory_tenant_id(db, request)
    from app.tenant_closure import require_new_work
    require_new_work(db, tenant_id)
    admin_session = require_admin(request)
    actor_admin_id = getattr(admin_session, "subject_id", None)
    folder = db.scalar(select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id).where(PhotoFolder.id == folder_id).with_for_update())
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if not folder_media_writes_allowed(db, folder):
        raise HTTPException(status_code=409, detail="A pasta está em uma etapa de arquivo ou recuperação.")
    if folder.status not in {"preparing", "released"}:
        raise HTTPException(status_code=409, detail="A pasta não aceita novas fotos.")
    if folder.derived_gallery_id:
        gallery = require_derived_gallery_mutable(
            db, folder.derived_gallery_id, allow_deleted_origin=True,
            tenant_id=tenant_id,
        )
        if not gallery.access_enabled:
            raise HTTPException(status_code=409, detail="A galeria privada está bloqueada.")
    else:
        parent = require_parent_gallery_mutable(db, folder.parent_gallery_id, tenant_id=tenant_id)
        if not parent.active:
            raise HTTPException(status_code=409, detail="A galeria está bloqueada para novas fotos.")
    if payload.upload_batch_id:
        try:
            if folder.derived_gallery_id:
                batch_for(db, payload.upload_batch_id, folder.derived_gallery_id,
                          open_only=True, tenant_id=tenant_id)
            else:
                folder_batch_for(db, payload.upload_batch_id, folder.id,
                                 open_only=True, tenant_id=tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    existing = db.scalar(select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id,
        PhotoAsset.storage_key == payload.storage_key))
    storage_key = payload.storage_key
    if existing is None:
        storage_key = namespaced_upload_key(payload.storage_key, tenant_id=tenant_id,
            parent_id=folder.parent_gallery_id, folder_id=folder.id, gallery_id=folder.derived_gallery_id)
        existing = db.scalar(select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.storage_key == storage_key))
    from app.photographer_onboarding import require_upload_ready
    require_upload_ready(
        db, tenant_id=tenant_id, admin_id=actor_admin_id, accepted_photo=existing,
    )
    fingerprint = photographer_credits.fingerprint_from_storage_key(storage_key)
    if existing is None and fingerprint and not payload.allow_duplicate_content:
        key_prefix = storage_key.rsplit("/", 1)[0] + "/"
        analysis_match = select(PhotoAnalysis.photo_asset_id).where(
            PhotoAnalysis.tenant_id == tenant_id,
            PhotoAnalysis.photo_asset_id == PhotoAsset.id,
            PhotoAnalysis.source_fingerprint == fingerprint,
        ).exists()
        prior_identical = db.scalar(select(PhotoAsset.id).where(
            PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.folder_id == folder.id,
            or_(
                PhotoAsset.storage_key == f"{key_prefix}{fingerprint}.jpg",
                PhotoAsset.storage_key.like(f"{key_prefix}{fingerprint}-%"),
                analysis_match,
            ),
        ).limit(1))
        if prior_identical is not None:
            raise HTTPException(
                status_code=409,
                detail="Esta foto já existe nesta pasta. Confirme o envio de fotos repetidas para criar outra cópia.",
            )
    if existing:
        if existing.folder_id != folder.id or existing.derived_gallery_id != folder.derived_gallery_id:
            raise HTTPException(status_code=409, detail="Arquivo já cadastrado em outro escopo.")
        existing_batch_ids = set(
            db.scalars(
                select(PrivateUploadBatchAsset.batch_id).where(
                    PrivateUploadBatchAsset.tenant_id == tenant_id,
                    PrivateUploadBatchAsset.photo_asset_id == existing.id,
                )
            )
        )
        if payload.upload_batch_id and payload.upload_batch_id not in existing_batch_ids:
            db.add(PrivateUploadBatchAsset(
                batch_id=payload.upload_batch_id, photo_asset_id=existing.id, tenant_id=tenant_id,
            ))
        if folder.purpose == "content":
            prior_operation = db.scalar(select(PhotoCreditOperation.id).where(
                PhotoCreditOperation.tenant_id == tenant_id,
                PhotoCreditOperation.photo_asset_id_snapshot == existing.id,
            ))
            # Não aplicar cobrança retroativa a PhotoAssets legados sem operação.
            if prior_operation is not None:
                fingerprint = photographer_credits.fingerprint_from_storage_key(existing.storage_key)
                try:
                    photographer_credits.reserve_photo_credit(
                        db, tenant_id, existing.id, existing.storage_key, fingerprint,
                        actor_admin_id=actor_admin_id,
                    )
                except Exception:
                    db.rollback()
                    raise
        db.commit()
        return {"id": str(existing.id), "duplicate": "false" if payload.upload_batch_id in existing_batch_ids else "true"}
    asset = PhotoAsset(
        tenant_id=tenant_id,
        parent_gallery_id=folder.parent_gallery_id,
        derived_gallery_id=folder.derived_gallery_id,
        folder_id=folder.id,
        available=False,
        storage_key=storage_key,
        **payload.model_dump(exclude={"upload_batch_id", "storage_key", "allow_duplicate_content"}),
    )
    db.add(asset)
    db.flush()
    if payload.upload_batch_id:
        db.add(PrivateUploadBatchAsset(batch_id=payload.upload_batch_id, photo_asset_id=asset.id, tenant_id=tenant_id))
    audit(db, "photo_asset.registered_in_folder", str(asset.id), tenant_id=tenant_id)
    try:
        if folder.purpose == "content":
            fingerprint = photographer_credits.fingerprint_from_storage_key(asset.storage_key)
            photographer_credits.reserve_photo_credit(
                db, tenant_id, asset.id, asset.storage_key, fingerprint,
                actor_admin_id=actor_admin_id,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"id": str(asset.id)}


def _publish_photo_folder(
    db: Session, folder: PhotoFolder, *, commit: bool = True
) -> dict[str, object]:
    require_active_owner(db, folder.tenant_id)
    if not folder_media_writes_allowed(db, folder):
        raise HTTPException(status_code=409, detail="A pasta está em uma etapa de arquivo ou recuperação.")
    lock_payment_account(db, folder.tenant_id)
    gallery = owned_record(db, ParentGallery, folder.parent_gallery_id, tenant_id=folder.tenant_id)
    if gallery and not can_publish_gallery(db, gallery):
        raise HTTPException(status_code=409, detail=PAYMENT_REQUIRED_MESSAGE)
    if folder.purpose != "content" or folder.status not in {"preparing", "released"}:
        raise HTTPException(status_code=409, detail="A pasta não pode ser publicada.")
    if folder.audience_scope == "selected" and folder.derived_gallery_id is None and not db.scalar(
        select(FolderClientGrant.id).where(FolderClientGrant.tenant_id == folder.tenant_id).where(FolderClientGrant.folder_id == folder.id).limit(1)
    ):
        raise HTTPException(status_code=409, detail="Atribua a pasta a uma cliente antes de publicá-la.")
    photos = list(db.scalars(select(PhotoAsset).where(PhotoAsset.tenant_id == folder.tenant_id).where(PhotoAsset.folder_id == folder.id)))
    unpublished_ids = [photo.id for photo in photos if not photo.available]
    ready_ids = (
        set(
            db.scalars(
                select(MediaDerivative.photo_asset_id).where(MediaDerivative.tenant_id == folder.tenant_id).where(
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
        from app.folder_deadlines import start_folder_access_deadline

        folder.status = "released"
        start_folder_access_deadline(folder)
    for photo in photos:
        if photo.id in ready_ids:
            analysis_preview = db.scalar(select(MediaDerivative).where(
                MediaDerivative.tenant_id == folder.tenant_id,
                MediaDerivative.photo_asset_id == photo.id,
                MediaDerivative.variant == "admin_preview",
                MediaDerivative.status == "ready",
            ))
            if analysis_preview and analysis_preview.relative_path:
                from app.facial.indexing import enqueue_photo_index_if_eligible

                try:
                    enqueue_photo_index_if_eligible(
                        db, photo, analysis_preview,
                        derivative_path=safe_derivative_path(analysis_preview),
                    )
                except ValueError:
                    logger.warning("Indexação facial adiada: caminho da prévia indisponível")
    if ready_ids and folder.audience_scope == "selected" and folder.derived_gallery_id is None:
        batched_photo_ids = set(db.scalars(select(PrivateUploadBatchAsset.photo_asset_id).where(
            PrivateUploadBatchAsset.tenant_id == folder.tenant_id,
            PrivateUploadBatchAsset.photo_asset_id.in_(ready_ids),
        )))
        unbatched_ready_ids = ready_ids - batched_photo_ids
        record_restricted_folder_ready(
            db, folder=folder, photo_ids=unbatched_ready_ids, batch_key="publish"
        )
    failed_ids = (
        set(
            db.scalars(
                select(MediaJob.photo_asset_id).where(MediaJob.tenant_id == folder.tenant_id).where(
                    MediaJob.photo_asset_id.in_(unpublished_ids),
                    MediaJob.status == "failed",
                )
            )
        )
        if unpublished_ids
        else set()
    )
    audit(db, "photo_folder.published", f"{folder.id}:{len(ready_ids)}", tenant_id=folder.tenant_id)
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

    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    lock_payment_account(db, tenant_id)
    folder = owned_record(db, PhotoFolder, folder_id, tenant_id=tenant_id)
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if folder.derived_gallery_id:
        require_derived_gallery_mutable(
            db, folder.derived_gallery_id, allow_deleted_origin=True,
            tenant_id=tenant_id,
        )
    else:
        require_parent_gallery_mutable(db, folder.parent_gallery_id, tenant_id=tenant_id)
    return _publish_photo_folder(db, folder)


@app.post("/admin/parent-galleries/{parent_gallery_id}/publish-ready")
def publish_parent_gallery_ready_photos(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    """Publica a rodada pronta de todas as pastas antes de avançar no editor."""

    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    lock_payment_account(db, tenant_id)
    gallery = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    if not can_publish_gallery(db, gallery):
        raise HTTPException(status_code=409, detail=PAYMENT_REQUIRED_MESSAGE)
    folders = list(
        db.scalars(
            select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id)
            .where(
                PhotoFolder.parent_gallery_id == parent_gallery_id,
                PhotoFolder.derived_gallery_id.is_(None),
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
    audit(db, "parent_gallery.ready_photos_published", str(parent_gallery_id), tenant_id=tenant_id)
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

    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    lock_payment_account(db, tenant_id)
    if payload.gallery_ids:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "Destinos privados não são mais aceitos nesta ação. "
                "Publique a pasta e disponibilize fotos individualmente na etapa Clientes."
            ),
        )
    folder = owned_record(db, PhotoFolder, folder_id, tenant_id=tenant_id)
    if not folder or folder.purpose != "content":
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if folder.derived_gallery_id:
        require_derived_gallery_mutable(
            db, folder.derived_gallery_id, allow_deleted_origin=True,
            tenant_id=tenant_id,
        )
    else:
        require_parent_gallery_mutable(db, folder.parent_gallery_id, tenant_id=tenant_id)
    return _publish_photo_folder(db, folder)


@app.post("/admin/parent-galleries", status_code=status.HTTP_201_CREATED)
def create_parent_gallery(
    payload: ParentGalleryInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    from app.tenant_closure import require_new_work
    require_new_work(db, tenant_id)
    admin_session = current_session(request, Role.ADMIN)
    tenant = require_admin_tenant(db, admin_session.subject_id)
    _gallery_capability_origin(request)
    gallery = ParentGallery(tenant_id=tenant.id, **payload.model_dump())
    db.add(gallery)
    db.flush()
    capability, token = issue_gallery_capability(
        db,
        parent_gallery_id=gallery.id,
        scope="public_gallery",
        actor_admin_id=admin_session.subject_id,
        reconstructible=True,
        tenant_id=tenant_id,
    )
    audit(db, "parent_gallery.created", str(gallery.id), tenant_id=tenant_id)
    audit(db, "gallery_capability.public_issued", str(capability.id), tenant_id=tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    capability = _active_gallery_capability(
        db, parent_gallery_id=parent_gallery_id, scope="public_gallery",
        tenant_id=tenant_id,
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
    tenant_id = directory_tenant_id(db, request)
    admin_session = current_session(request, Role.ADMIN)
    require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    if _active_gallery_capability(db, parent_gallery_id=parent_gallery_id, scope="public_gallery", tenant_id=tenant_id):
        raise HTTPException(
            status_code=409,
            detail="Já existe um link ativo; rotacione-o para obter um novo segredo.",
        )
    _gallery_capability_origin(request)
    capability, token = issue_gallery_capability(
        db,
        parent_gallery_id=parent_gallery_id,
        scope="public_gallery",
        expires_at=_validated_capability_expiry(payload.expires_at),
        actor_admin_id=admin_session.subject_id,
        reconstructible=True,
        tenant_id=tenant_id,
    )
    audit(db, "gallery_capability.public_issued", str(capability.id), tenant_id=tenant_id)
    db.commit()
    return _capability_secret_response(request, capability, token)


@app.post("/admin/parent-galleries/{parent_gallery_id}/public-link/rotate")
def rotate_parent_gallery_public_link(
    parent_gallery_id: UUID,
    payload: GalleryCapabilityInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    admin_session = current_session(request, Role.ADMIN)
    require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    capability = _active_gallery_capability(
        db, parent_gallery_id=parent_gallery_id, scope="public_gallery",
        tenant_id=tenant_id,
    )
    if not capability:
        raise HTTPException(status_code=404, detail="Link ativo não encontrado.")
    _gallery_capability_origin(request)
    replacement, token = rotate_gallery_capability(
        db,
        capability,
        actor_admin_id=admin_session.subject_id,
        reconstructible=True,
        tenant_id=tenant_id,
    )
    if payload.expires_at is not None:
        replacement.expires_at = _validated_capability_expiry(payload.expires_at)
    audit(db, "gallery_capability.public_rotated", str(replacement.id), tenant_id=tenant_id)
    db.commit()
    return _capability_secret_response(request, replacement, token)


@app.delete(
    "/admin/parent-galleries/{parent_gallery_id}/public-link",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_parent_gallery_public_link(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    capability = _active_gallery_capability(
        db, parent_gallery_id=parent_gallery_id, scope="public_gallery",
        tenant_id=tenant_id,
    )
    if capability:
        revoke_gallery_capability(capability)
        audit(db, "gallery_capability.public_revoked", str(capability.id), tenant_id=tenant_id)
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
        tenant_id=parent.tenant_id,
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
        tenant_id=parent.tenant_id,
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
    tenant_id = directory_tenant_id(db, request)
    admin_session = current_session(request, Role.ADMIN)
    parent = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    client = owned_record(db, Client, client_id, tenant_id=tenant_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    _gallery_capability_origin(request)
    capability, token = _issue_individual_invite(
        db,
        parent=parent,
        client=client,
        actor_admin_id=admin_session.subject_id,
        expires_at=payload.expires_at,
    )
    audit(db, "gallery_capability.client_invite_issued", str(capability.id), tenant_id=tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    admin_session = current_session(request, Role.ADMIN)
    require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    capability = _active_gallery_capability(
        db,
        parent_gallery_id=parent_gallery_id,
        scope="parent_invite",
        client_id=client_id,
        tenant_id=tenant_id,
    )
    if not capability:
        raise HTTPException(status_code=404, detail="Convite ativo não encontrado.")
    _gallery_capability_origin(request)
    replacement, token = rotate_gallery_capability(
        db, capability, actor_admin_id=admin_session.subject_id,
        tenant_id=tenant_id,
    )
    if payload.expires_at is not None:
        replacement.expires_at = _validated_capability_expiry(payload.expires_at)
    audit(db, "gallery_capability.client_invite_rotated", str(replacement.id), tenant_id=tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    capability = _active_gallery_capability(
        db,
        parent_gallery_id=parent_gallery_id,
        scope="parent_invite",
        client_id=client_id,
        tenant_id=tenant_id,
    )
    if capability:
        revoke_gallery_capability(capability)
        audit(db, "gallery_capability.client_invite_revoked", str(capability.id), tenant_id=tenant_id)
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


    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    return {
        "operation_type": "delete_parent_gallery",
        "target": {"id": str(gallery.id), "name": gallery.name},
        "inventory": gallery_deletion_inventory(db, gallery.id, tenant_id=tenant_id),
        "consequences": {
            "public_gallery_removed": True,
            "public_access_revoked": True,
            "private_galleries_preserved": False,
            "private_referenced_photos_preserved": False,
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


    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    client = owned_record(db, Client, client_id, tenant_id=tenant_id)
    registration = db.scalar(
        select(ParentGalleryRegistration.id).where(ParentGalleryRegistration.tenant_id == tenant_id).where(ParentGalleryRegistration.tenant_id == tenant_id).where(
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
        "inventory": client_unlink_inventory(db, parent_gallery_id=gallery.id, client_id=client.id, tenant_id=tenant_id),
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

    tenant_id = directory_tenant_id(db, request)
    admin_session = current_session(request, Role.ADMIN)
    idempotency_key = request.headers.get("Idempotency-Key", "").strip()
    if not idempotency_key or len(idempotency_key) > 128:
        raise HTTPException(
            status_code=422,
            detail="Informe uma chave de idempotência válida.",
        )
    existing = db.scalar(
        select(GalleryLifecycleOperation).where(GalleryLifecycleOperation.tenant_id == tenant_id).where(GalleryLifecycleOperation.tenant_id == tenant_id).where(
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

    lock_removal_clients(db, parent_gallery_id, tenant_id=tenant_id)
    db.scalar(select(ParentGallery).where(ParentGallery.tenant_id == tenant_id).where(ParentGallery.tenant_id == tenant_id).where(ParentGallery.id == parent_gallery_id).with_for_update())
    gallery = _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
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
            "inventory": gallery_deletion_inventory(db, gallery.id, tenant_id=tenant_id),
            "operational_storage": gallery_operational_storage_manifest(db, gallery.id, tenant_id=tenant_id),
        },
        tenant_id=tenant_id,
    )
    gallery.lifecycle_status = "deleting"
    db.add(operation)
    db.flush()
    audit(db, "parent_gallery.deletion_queued", str(operation.id), tenant_id=tenant_id)
    db.commit()
    return lifecycle_operation_payload(operation)


@app.get("/admin/gallery-lifecycle-operations/{operation_id}")
def gallery_lifecycle_operation_status(
    operation_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    operation = owned_record(db, GalleryLifecycleOperation, operation_id, tenant_id=tenant_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operação não encontrada.")
    return lifecycle_operation_payload(operation)


@app.post("/admin/gallery-lifecycle-operations/{operation_id}/retry")
def retry_gallery_lifecycle_operation(
    operation_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Reagenda uma falha mantendo inventário e etapas já concluídas."""

    tenant_id = directory_tenant_id(db, request)
    admin_session = current_session(request, Role.ADMIN)
    operation = db.scalar(
        select(GalleryLifecycleOperation).where(GalleryLifecycleOperation.tenant_id == tenant_id)
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
        tenant_id=tenant_id,
    )
    db.commit()
    return lifecycle_operation_payload(operation)


@app.post("/admin/gallery-lifecycle-operations/{operation_id}/cancel")
def cancel_gallery_lifecycle_operation(
    operation_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    admin_session = current_session(request, Role.ADMIN)
    operation = db.scalar(
        select(GalleryLifecycleOperation).where(GalleryLifecycleOperation.tenant_id == tenant_id)
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
        gallery = owned_record(db, ParentGallery, operation.target_parent_gallery_id, tenant_id=tenant_id)
        if gallery:
            gallery.lifecycle_status = "active"
    elif operation.operation_type == "unlink_client" and operation.target_client_id:
        previous_state = (operation.manifest or {}).get("previous_state", {})
        registration = db.scalar(
            select(ParentGalleryRegistration).where(ParentGalleryRegistration.tenant_id == tenant_id).where(
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
        tenant_id=tenant_id,
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
    """Recusa a antiga clonagem administrativa de referências existentes."""

    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    require_admin(request)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "A clonagem de galerias privadas foi encerrada. Crie uma pasta restrita "
            "no Acervo da cliente da Galeria pública."
        ),
    )


@app.post("/admin/clients/{client_id}/phone/challenge", status_code=status.HTTP_202_ACCEPTED)
def challenge_client_phone(
    client_id: UUID, payload: PhoneChangeChallengeInput, request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    client = db.scalar(select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id))
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    phone = normalize_e164(payload.phone_e164)
    try:
        assert_phone_available(db, phone, tenant_id=tenant_id, client_id=client_id)
    except ClientIdentityConflict as exc:
        raise HTTPException(status_code=409, detail="Este WhatsApp já pertence a outra cliente.") from exc
    client_auth_rate_limit(db, "client_otp.phone_change", pii_fingerprint(phone),
                          request.client.host if request.client else "unknown", tenant_id=tenant_id)
    challenge, code = create_challenge(db, "client_otp", phone, tenant_id=tenant_id)
    enqueue_client_otp_delivery(db, challenge, code)
    return {"challenge_id": str(challenge.id), "message": "Código solicitado para o novo WhatsApp."}


@app.post("/admin/clients/{client_id}/phone")
def change_client_phone(
    client_id: UUID, payload: PhoneChangeInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    client = db.scalar(select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id))
    phone = normalize_e164(payload.phone_e164)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    pending = db.get(AuthChallenge, payload.challenge_id)
    if pending is None or pending.tenant_id != tenant_id:
        raise neutral_error()
    challenge = consume_challenge(db, payload.challenge_id, "client_otp", payload.code, tenant_id=tenant_id)
    if challenge.subject != phone:
        minimize_client_challenge_pii(db, challenge)
        db.commit()
        raise neutral_error()
    try:
        change_verified_phone(db, client, phone, tenant_id=tenant_id)
        revoke_subject_sessions(db, Role.CLIENT.value, client.id)
        db.flush()
    except (ClientIdentityConflict, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Este WhatsApp já pertence a outra cliente."
        ) from exc
    audit(db, "client.phone_changed", str(client_id), tenant_id=tenant_id)
    minimize_client_challenge_pii(db, challenge)
    db.commit()
    return {"id": str(client_id)}


@app.get("/admin/parent-galleries/{parent_gallery_id}/clients")
def parent_gallery_clients(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    registrations = list(
        db.scalars(
            select(ParentGalleryRegistration).where(ParentGalleryRegistration.tenant_id == tenant_id).where(
                ParentGalleryRegistration.parent_gallery_id == parent_gallery_id
            )
        )
    )
    galleries = list(
        db.scalars(
            select(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id).where(DerivedGallery.parent_gallery_id == parent_gallery_id)
        )
    )
    memberships = list(
        db.scalars(
            select(DerivedGalleryMembership).where(DerivedGalleryMembership.tenant_id == tenant_id).where(
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
    last_access_by_client = {
        client_id: last_viewed_at
        for client_id, last_viewed_at in db.execute(
            select(PhotoView.client_id, func.max(PhotoView.last_viewed_at))
            .outerjoin(DerivedGallery, DerivedGallery.id == PhotoView.derived_gallery_id)
            .where(
                PhotoView.tenant_id == tenant_id,
                PhotoView.client_id.in_(client_ids),
                or_(
                    PhotoView.parent_gallery_id == parent_gallery_id,
                    and_(
                        DerivedGallery.parent_gallery_id == parent_gallery_id,
                        DerivedGallery.tenant_id == tenant_id,
                    ),
                ),
            )
            .group_by(PhotoView.client_id)
        )
    }
    clients_by_id = {
        item.id: item for item in db.scalars(select(Client).where(Client.tenant_id == tenant_id).where(Client.id.in_(client_ids)))
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
    projections = build_commercial_projections(
        db,
        gallery_ids={gallery.id for gallery in galleries},
        client_ids=client_ids,
        parent_gallery_ids={parent_gallery_id},
        galleries_by_id=galleries_by_id,
        tenant_id=tenant_id,
    )
    canonical_states = {
        state.client_id: state for state in db.scalars(select(GalleryClientState).where(GalleryClientState.tenant_id == tenant_id).where(
            GalleryClientState.parent_gallery_id == parent_gallery_id,
            GalleryClientState.client_id.in_(client_ids),
        ))
    }
    canonical_selected = dict(db.execute(select(
        PhotoSelection.client_id, func.count(PhotoSelection.id)
    ).where(PhotoSelection.tenant_id == tenant_id).where(
        PhotoSelection.parent_gallery_id == parent_gallery_id,
        PhotoSelection.client_id.in_(client_ids),
    ).group_by(PhotoSelection.client_id)).all())
    common_available = db.scalar(select(func.count(PhotoAsset.id)).where(PhotoAsset.tenant_id == tenant_id)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(
            PhotoAsset.parent_gallery_id == parent_gallery_id,
            PhotoAsset.available,
            PhotoFolder.derived_gallery_id.is_(None),
            PhotoFolder.status == "released",
            PhotoFolder.purpose == "content",
            or_(PhotoFolder.audience_scope == "all", PhotoFolder.audience_scope.is_(None)),
        )) or 0
    restricted_available = dict(db.execute(select(
        FolderClientGrant.client_id, func.count(PhotoAsset.id)
    ).where(FolderClientGrant.tenant_id == tenant_id, PhotoAsset.tenant_id == tenant_id).join(PhotoFolder, PhotoFolder.id == FolderClientGrant.folder_id)
     .join(PhotoAsset, PhotoAsset.folder_id == PhotoFolder.id)
     .where(
         FolderClientGrant.parent_gallery_id == parent_gallery_id,
         FolderClientGrant.client_id.in_(client_ids),
         PhotoFolder.audience_scope == "selected",
         PhotoFolder.status == "released",
         PhotoAsset.available,
     ).group_by(FolderClientGrant.client_id)).all())
    canonical_purchased = dict(db.execute(select(
        SaleOrder.client_id, func.count(SaleOrderItem.id)
    ).where(SaleOrder.tenant_id == tenant_id, SaleOrderItem.tenant_id == tenant_id).join(SaleOrderItem, SaleOrderItem.sale_order_id == SaleOrder.id)
     .where(
         SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
         SaleOrder.derived_gallery_id_snapshot.is_(None),
         SaleOrder.client_id.in_(client_ids),
         SaleOrder.payment_status == "confirmed",
     ).group_by(SaleOrder.client_id)).all())
    canonical_orders = list(db.scalars(select(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(
        SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
        SaleOrder.derived_gallery_id_snapshot.is_(None),
        SaleOrder.client_id.in_(client_ids),
        or_(SaleOrder.frozen_at.is_not(None), SaleOrder.payment_status == "confirmed"),
    ).order_by(SaleOrder.created_at.desc())))
    canonical_communications = communications_for_orders(db, canonical_orders)
    canonical_item_counts = dict(db.execute(select(
        SaleOrderItem.sale_order_id, func.count(SaleOrderItem.id)
    ).where(SaleOrderItem.tenant_id == tenant_id).where(SaleOrderItem.sale_order_id.in_([order.id for order in canonical_orders]))
     .group_by(SaleOrderItem.sale_order_id)).all()) if canonical_orders else {}
    canonical_group_scopes = payment_scopes(db, {
        order.payment_group_id for order in canonical_orders if order.payment_group_id
    }, tenant_id=tenant_id)
    canonical_financial_by_client: dict[UUID, list[dict[str, object]]] = defaultdict(list)
    latest_canonical_order_by_client: dict[UUID, SaleOrder] = {}
    for order in canonical_orders:
        latest_canonical_order_by_client.setdefault(order.client_id, order)
        communication = canonical_communications.get(order.id)
        if not communication:
            continue
        capabilities = payment_capabilities(communication.status, order.payment_status)
        canonical_financial_by_client[order.client_id].append({
            "id": str(communication.id), "order_id": str(order.id),
            "gallery_name": order.parent_gallery_name_snapshot,
            "total_cents": order.total_cents,
            "quantity": canonical_item_counts.get(order.id, 0),
            "created_at": order.created_at.isoformat(),
            "status": communication.status,
            **capabilities,
            "payment_group": canonical_group_scopes.get(order.payment_group_id),
        })
    finalized_by_client: dict[UUID, list[dict[str, object]]] = defaultdict(list)
    finalized = [order for order in canonical_orders if order.payment_status == "not_required"
                 and order_fulfillable(order)]
    finalized_items: dict[UUID, list[SaleOrderItem]] = defaultdict(list)
    finalized_item_rows = list(db.scalars(select(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id).where(
        SaleOrderItem.sale_order_id.in_([order.id for order in finalized]),
    ).order_by(SaleOrderItem.filename_snapshot))) if finalized else []
    finalized_media_states = folder_media_states_by_id(
        db,
        folder_ids={item.folder_id_snapshot for item in finalized_item_rows if item.folder_id_snapshot},
        tenant_id=tenant_id,
    )
    for item in finalized_item_rows:
        finalized_items[item.sale_order_id].append(item)
    for order in finalized:
        finalized_by_client[order.client_id].append({
            "id": str(order.id), "frozen_at": order.frozen_at.isoformat(),
            "delivery": delivery_payload(order),
            "items": [{"name": item.filename_snapshot,
                       "media_state": (
                           "available" if item.folder_id_snapshot is None
                           else finalized_media_states.get(item.folder_id_snapshot, "unavailable")
                       ),
                       "preview_url": f"/admin/photo-assets/{item.photo_asset_id}/preview"
                       if item.photo_asset_id and (
                           item.folder_id_snapshot is None
                           or finalized_media_states.get(item.folder_id_snapshot) in {"available", "archiving"}
                       ) else None}
                      for item in finalized_items[order.id]],
        })
    canonical_reopening: dict[UUID, str] = {}
    for reopening in db.scalars(select(GalleryReopeningRequest).where(GalleryReopeningRequest.tenant_id == tenant_id).where(
        GalleryReopeningRequest.parent_gallery_id == parent_gallery_id,
        GalleryReopeningRequest.requested_by_client_id.in_(client_ids),
    ).order_by(GalleryReopeningRequest.created_at.desc())):
        canonical_reopening.setdefault(reopening.requested_by_client_id, reopening.status)
    rows = []
    for client_id in client_ids:
        client = clients_by_id.get(client_id)
        gallery = galleries_by_client.get(client_id)
        membership = memberships_by_client.get(client_id)
        registration = registrations_by_client.get(client_id)
        projection = projections.get((gallery.id, client_id)) if gallery else next(
            (
                item
                for (projection_gallery_id, projection_client_id), item in projections.items()
                if projection_client_id == client_id
                and projection_gallery_id is not None
                and projection_gallery_id not in galleries_by_id
            ),
            None,
        )
        state = canonical_states.get(client_id)
        selected_count = (projection.selected_count if projection else 0) + canonical_selected.get(client_id, 0)
        phone_verified = phone_verification_by_client.get(client_id, True)
        if registration and (registration.status != "active" or not phone_verified):
            gallery_status = "pending_registration"
        elif (state and state.status != "active") or (membership and membership.status == "blocked") or (
            gallery and not gallery.access_enabled
        ):
            gallery_status = "blocked"
        elif selected_count == 0:
            gallery_status = "no_selection"
        else:
            gallery_status = "active"
        latest_canonical_order = latest_canonical_order_by_client.get(client_id)
        latest_communication = canonical_communications.get(latest_canonical_order.id) \
            if latest_canonical_order else None
        commercial_status = (
            "selection_finalized" if latest_canonical_order and latest_canonical_order.payment_status == "not_required"
            else "paid" if latest_canonical_order and latest_canonical_order.payment_status == "confirmed"
            else "pending_review" if latest_communication and latest_communication.status == "pending_review"
            else "cancelled" if latest_canonical_order and latest_canonical_order.payment_status == "cancelled"
            else "awaiting_payment" if latest_canonical_order
            else projection.commercial_status if projection
            else "no_order"
        )
        last_access_at = last_access_by_client.get(client_id)
        if last_access_at is None and registration:
            last_access_at = registration.created_at
        rows.append(
            {
                "client_id": str(client_id),
                "name": client.full_name if client else "Cliente",
                "phone": client.phone_e164 if client else "",
                "phone_verified": phone_verified,
                "registration_status": registration.status if registration else None,
                "membership_status": membership.status if membership else None,
                "access_status": state.status if state else "active",
                "derived_gallery_id": str(gallery.id) if gallery else None,
                "available_count": common_available + restricted_available.get(client_id, 0)
                if state else projection.available_count if projection else common_available,
                "selected_count": selected_count,
                "purchased_count": (projection.purchased_count if projection else 0)
                + canonical_purchased.get(client_id, 0),
                "gallery_status": gallery_status,
                "commercial_status": commercial_status,
                "reopening_status": canonical_reopening.get(client_id) or (
                    projection.reopening_status if projection else None
                ),
                **({"finalized_orders": finalized_by_client[client_id]} if finalized_by_client.get(client_id) else {}),
                "financial_orders": canonical_financial_by_client.get(client_id, [])
                + (projection.financial_orders if projection else []),
                "selection_expires_at": None,
                "last_access_at": last_access_at.isoformat() if last_access_at else None,
            }
        )
    return {
        "parent_gallery_id": str(parent_gallery_id),
        "clients": sorted(
            sorted(rows, key=lambda item: (item["name"].casefold(), item["client_id"])),
            key=lambda item: item["last_access_at"] or "",
            reverse=True,
        ),
    }


@app.put("/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}")
def link_admin_client_to_parent_gallery(
    parent_gallery_id: UUID,
    client_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    parent = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    if not parent.active or not owned_record(db, Client, client_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria ou cliente não encontrado.")
    registration = link_client_to_parent(
        db,
        parent_gallery_id=parent.id,
        client_id=client_id,
        status="active",
    )
    audit(db, "parent_gallery.client_linked", str(registration.id), tenant_id=tenant_id)
    db.commit()
    return {
        "registration_id": str(registration.id),
        "parent_gallery_id": str(parent.id),
        "client_id": str(client_id),
        "status": registration.status,
        "private_gallery_id": None,
    }


@app.patch("/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/access")
def update_admin_client_gallery_access(
    parent_gallery_id: UUID,
    client_id: UUID,
    payload: GalleryClientAccessInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    require_same_origin(request)
    db.scalar(select(Client.id).where(Client.tenant_id == tenant_id).where(Client.id == client_id).with_for_update())
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    _admin_linked_gallery_client(
        db, parent_gallery_id=parent_gallery_id, client_id=client_id,
        tenant_id=tenant_id,
    )
    state = db.scalar(select(GalleryClientState).where(GalleryClientState.tenant_id == tenant_id).where(
        GalleryClientState.parent_gallery_id == parent_gallery_id,
        GalleryClientState.client_id == client_id,
    ).with_for_update())
    if not state:
        state = GalleryClientState(
            parent_gallery_id=parent_gallery_id,
            client_id=client_id,
            status=payload.status,
            tenant_id=tenant_id,
        )
        db.add(state)
    elif state.status != payload.status:
        state.status = payload.status
    else:
        return {"status": state.status}
    audit(db, f"gallery_client.access_{payload.status}", f"{parent_gallery_id}:{client_id}", tenant_id=tenant_id)
    db.commit()
    return {"status": state.status}


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


    tenant_id = directory_tenant_id(db, request)
    admin_session = current_session(request, Role.ADMIN)
    idempotency_key = request.headers.get("Idempotency-Key", "").strip()
    if not idempotency_key or len(idempotency_key) > 128:
        raise HTTPException(
            status_code=422,
            detail="Informe uma chave de idempotência válida.",
        )
    existing = db.scalar(
        select(GalleryLifecycleOperation).where(GalleryLifecycleOperation.tenant_id == tenant_id).where(GalleryLifecycleOperation.tenant_id == tenant_id).where(
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

    parent = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
    client = owned_record(db, Client, client_id, tenant_id=tenant_id)
    if not parent or parent.lifecycle_status != "active" or not client:
        raise HTTPException(status_code=404, detail="Galeria pública ou cliente não encontrado.")
    registration = db.scalar(
        select(ParentGalleryRegistration).where(ParentGalleryRegistration.tenant_id == tenant_id).where(ParentGalleryRegistration.tenant_id == tenant_id)
        .where(
            ParentGalleryRegistration.parent_gallery_id == parent.id,
            ParentGalleryRegistration.client_id == client.id,
        )
        .with_for_update()
    )
    if not registration:
        raise HTTPException(status_code=404, detail="Vínculo de cliente não encontrado.")
    conflicting = db.scalar(
        select(GalleryLifecycleOperation.id).where(GalleryLifecycleOperation.tenant_id == tenant_id).where(GalleryLifecycleOperation.tenant_id == tenant_id).where(
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
                db, parent_gallery_id=parent.id, client_id=client.id,
                tenant_id=tenant_id,
            ),
            "operational_storage": {"sources": [], "derivatives": []},
            "previous_state": {
                "registration_status": registration.status,
                "membership_status": membership.status if membership else None,
            },
        },
        tenant_id=tenant_id,
    )
    registration.status = "unlinking"
    db.add(operation)
    db.flush()
    audit(db, "parent_gallery.client_unlink_queued", str(operation.id), tenant_id=tenant_id)
    db.commit()
    return lifecycle_operation_payload(operation)


@app.get("/admin/derived-galleries/{gallery_id}/selection")
def selection_detail(
    gallery_id: UUID,
    request: Request,
    client_id: UUID | None = None,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
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
    owner = owned_record(db, Client, selected_client_id, tenant_id=tenant_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    selected = list(
        db.scalars(
            select(PhotoSelection).where(PhotoSelection.tenant_id == tenant_id).where(
                PhotoSelection.derived_gallery_id == gallery_id,
                PhotoSelection.client_id == selected_client_id,
            )
        )
    )
    orders = list(
        db.scalars(
            select(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(
                SaleOrder.derived_gallery_id == gallery_id,
                SaleOrder.client_id == selected_client_id,
            )
        )
    )
    confirmed_items = list(
        db.scalars(
            select(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id)
            .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
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
    projection = build_commercial_projections(
        db,
        gallery_ids={gallery.id},
        client_ids={selected_client_id},
        galleries_by_id={gallery.id: gallery},
        tenant_id=tenant_id,
    )[(gallery.id, selected_client_id)]
    photo_ids = {selection.photo_asset_id for selection in selected}
    photos_by_id = {
        photo.id: photo for photo in db.scalars(
            select(PhotoAsset).where(
                PhotoAsset.tenant_id == tenant_id,
                PhotoAsset.id.in_(photo_ids),
            )
        )
    } if photo_ids else {}
    media_states = folder_media_states_by_id(
        db,
        folder_ids={photo.folder_id for photo in photos_by_id.values() if photo.folder_id},
        tenant_id=tenant_id,
    )
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
    cover_thumbnail_available = bool(
        parent and parent.cover_photo_id
        and _cover_thumbnail_is_local(db, parent, parent.cover_photo_id)
    )
    photos = []
    for selection in selected:
        photo = photos_by_id.get(selection.photo_asset_id)
        if photo:
            media_state = (
                media_states.get(photo.folder_id, "unavailable")
                if photo.folder_id else "available"
            )
            preview_available = media_state in {"available", "archiving"} or (
                parent is not None
                and parent.cover_photo_id == photo.id
                and cover_thumbnail_available
            )
            photos.append(
                {
                    "id": str(photo.id),
                    "filename": photo.filename,
                    "media_state": media_state,
                    "preview_url": f"/admin/photo-assets/{photo.id}/preview" if preview_available else None,
                    "sales_count": sales_by_photo.get(photo.id, 0),
                }
            )
    return {
        "gallery": {
            "id": str(gallery.id),
            "name": gallery.name,
            "selection_expires_at": None,
        },
        "client": {"id": str(owner.id), "name": owner.full_name, "phone": owner.phone_e164}
        if owner
        else None,
        "available_count": projection.available_count,
        "selection_count": projection.selected_count,
        "purchased_count": projection.purchased_count,
        "payment_status": next((order.payment_status for order in orders), "pending"),
        "commercial_status": projection.commercial_status,
        "reopening_status": projection.reopening_status,
        "photos": photos,
    }


def _purchase_comment_excerpt(body: str) -> str:
    normalized = " ".join(body.split())
    if len(normalized) > 50:
        return normalized[:49].rstrip() + "…"
    return normalized


def _purchase_photo_interactions(
    db: Session,
    *,
    tenant_id: UUID,
    purchases: list[tuple[SaleOrder, SaleOrderItem]],
) -> dict[UUID, dict[str, object]]:
    """Busca uma anotação e favorito por foto, respeitando o snapshot do pedido."""
    scoped_purchases: list[tuple[SaleOrderItem, tuple[str, UUID, UUID, UUID]]] = []
    for order, item in purchases:
        if (
            order.tenant_id != tenant_id
            or item.tenant_id != tenant_id
            or item.sale_order_id != order.id
        ):
            continue
        if order.derived_gallery_id_snapshot:
            scope = ("derived", order.derived_gallery_id_snapshot)
        elif order.parent_gallery_id_snapshot:
            scope = ("parent", order.parent_gallery_id_snapshot)
        else:
            continue
        scoped_purchases.append(
            (item, (scope[0], scope[1], order.client_id, item.photo_asset_id_snapshot))
        )

    interactions: dict[UUID, dict[str, object]] = {}
    for start in range(0, len(scoped_purchases), 200):
        batch = scoped_purchases[start : start + 200]
        requested_keys = {key for _item, key in batch}
        photo_ids = {key[3] for key in requested_keys}
        client_ids = {key[2] for key in requested_keys}
        derived_ids = {key[1] for key in requested_keys if key[0] == "derived"}
        parent_ids = {key[1] for key in requested_keys if key[0] == "parent"}
        scope_filters = []
        if derived_ids:
            scope_filters.append(PhotoComment.derived_gallery_id.in_(derived_ids))
        if parent_ids:
            scope_filters.append(PhotoComment.parent_gallery_id.in_(parent_ids))

        latest_comments: dict[tuple[str, UUID, UUID, UUID], str] = {}
        if scope_filters:
            comments = db.scalars(
                select(PhotoComment)
                .where(
                    PhotoComment.tenant_id == tenant_id,
                    PhotoComment.client_id.in_(client_ids),
                    PhotoComment.photo_asset_id.in_(photo_ids),
                    PhotoComment.removed_at.is_(None),
                    or_(*scope_filters),
                )
                .order_by(PhotoComment.created_at.desc(), PhotoComment.id.desc())
            )
            for comment in comments:
                scope = (
                    ("derived", comment.derived_gallery_id)
                    if comment.derived_gallery_id
                    else ("parent", comment.parent_gallery_id)
                )
                key = (scope[0], scope[1], comment.client_id, comment.photo_asset_id)
                if key in requested_keys and key not in latest_comments:
                    latest_comments[key] = _purchase_comment_excerpt(comment.body)

        favorite_filters = []
        if derived_ids:
            favorite_filters.append(PhotoFavorite.derived_gallery_id.in_(derived_ids))
        if parent_ids:
            favorite_filters.append(PhotoFavorite.parent_gallery_id.in_(parent_ids))
        favorited_keys: set[tuple[str, UUID, UUID, UUID]] = set()
        if favorite_filters:
            favorites = db.scalars(
                select(PhotoFavorite).where(
                    PhotoFavorite.tenant_id == tenant_id,
                    PhotoFavorite.client_id.in_(client_ids),
                    PhotoFavorite.photo_asset_id.in_(photo_ids),
                    or_(*favorite_filters),
                )
            )
            for favorite in favorites:
                scope = (
                    ("derived", favorite.derived_gallery_id)
                    if favorite.derived_gallery_id
                    else ("parent", favorite.parent_gallery_id)
                )
                key = (scope[0], scope[1], favorite.client_id, favorite.photo_asset_id)
                if key in requested_keys:
                    favorited_keys.add(key)

        for item, key in batch:
            interactions[item.id] = {
                "comment_preview": latest_comments.get(key),
                "favorited": key in favorited_keys,
            }
    return interactions


def _purchase_photo_interaction_html(interaction: dict[str, object]) -> str:
    markup: list[str] = []
    if interaction.get("favorited"):
        markup.append(
            '<span class="interaction-favorite" aria-label="Favoritada pela cliente" '
            'title="Favoritada pela cliente">♥</span>'
        )
    comment = interaction.get("comment_preview")
    if isinstance(comment, str) and comment:
        safe_comment = escape(comment, quote=True)
        markup.append(
            f'<p class="interaction-comment" role="note" '
            f'aria-label="Comentário: {safe_comment}" title="{safe_comment}">'
            f'{escape(comment)}</p>'
        )
    return "".join(markup)


def _selection_html_preview(db: Session, item: SaleOrderItem) -> str:
    tenant_id = item.tenant_id
    require_active_owner(db, tenant_id)
    photo = owned_record(db, PhotoAsset, item.photo_asset_id, tenant_id=tenant_id) if item.photo_asset_id else None
    media_state = historical_folder_media_state_by_id(
        db,
        folder_id=item.folder_id_snapshot or (photo.folder_id if photo else None),
        tenant_id=tenant_id,
    ) if item.folder_id_snapshot or (photo and photo.folder_id) else "available"
    if media_state not in {"available", "archiving"}:
        parent = owned_record(db, ParentGallery, photo.parent_gallery_id, tenant_id=tenant_id) if photo else None
        if not (
            photo and parent and parent.cover_photo_id == photo.id
            and _cover_thumbnail_is_local(db, parent, photo.id)
        ):
            return '<div class="preview-missing">Prévia indisponível</div>'
        derivative = db.scalar(
            select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(
                MediaDerivative.photo_asset_id == photo.id,
                MediaDerivative.variant == "admin_preview",
                MediaDerivative.status == "ready",
            )
        )
        if not derivative:
            return '<div class="preview-missing">Prévia indisponível</div>'
        try:
            path = safe_derivative_path(derivative)
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        except (OSError, ValueError):
            return '<div class="preview-missing">Prévia indisponível</div>'
        return f'<img src="data:image/jpeg;base64,{encoded}" alt="Prévia de {escape(item.filename_snapshot)}">'
    historical = db.scalar(
        select(CommercialHistoryMedia).where(CommercialHistoryMedia.tenant_id == tenant_id).where(
            CommercialHistoryMedia.tenant_id == tenant_id,
            CommercialHistoryMedia.sale_order_item_id == item.id,
            CommercialHistoryMedia.status == "ready",
        )
    )
    if historical and historical.preview_storage_key:
        try:
            encoded = base64.b64encode(
                historical_media_path(historical.preview_storage_key, tenant_id=historical.tenant_id, item_id=historical.sale_order_item_id).read_bytes()
            ).decode("ascii")
            return f'<img src="data:image/jpeg;base64,{encoded}" alt="Prévia de {escape(item.filename_snapshot)}">'
        except (OSError, ValueError):
            pass
    if not item.photo_asset_id:
        return '<div class="preview-missing">Prévia indisponível</div>'
    derivative = db.scalar(
        select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(
            MediaDerivative.photo_asset_id == item.photo_asset_id,
            MediaDerivative.variant == "admin_preview",
            MediaDerivative.status == "ready",
        )
    )
    if not derivative:
        return '<div class="preview-missing">Prévia indisponível</div>'
    try:
        path = safe_derivative_path(derivative)
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except (OSError, ValueError):
        return '<div class="preview-missing">Prévia indisponível</div>'
    return f'<img src="data:image/jpeg;base64,{encoded}" alt="Prévia de {escape(item.filename_snapshot)}">'


def _purchased_photos_content_disposition(client_name: str | None) -> str:
    safe_name = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', "", client_name or "")
    safe_name = re.sub(r"\s+", " ", safe_name).strip(" .")[:120].strip(" .") or "Cliente"
    unicode_filename = f"fotos-compradas-{safe_name}.html"
    ascii_name = unicodedata.normalize("NFKD", safe_name).encode("ascii", "ignore").decode("ascii")
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_name).strip(".-_") or "Cliente"
    fallback = f"fotos-compradas-{ascii_name[:120]}.html"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(unicode_filename, safe='')}"


@app.get("/admin/derived-galleries/{gallery_id}/selection/export.{format}")
def export_selection(
    gallery_id: UUID,
    format: str,
    request: Request,
    client_id: UUID | None = None,
    db: Session = Depends(db_session),
) -> Response:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    if format not in {"txt", "csv", "html"}:
        raise HTTPException(status_code=404, detail="Formato não suportado.")
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
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
    if format == "html":
        purchased_items = list(db.scalars(
            select(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id)
            .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
            .where(
                SaleOrder.derived_gallery_id_snapshot == gallery_id,
                SaleOrder.client_id == selected_client_id,
                SaleOrder.payment_status == "confirmed",
            )
            .order_by(SaleOrder.confirmed_at, SaleOrder.id, SaleOrderItem.filename_snapshot)
        ))
        if not purchased_items:
            raise HTTPException(status_code=409, detail="Nenhuma compra confirmada para esta cliente nesta galeria.")
        owner = owned_record(db, Client, selected_client_id, tenant_id=tenant_id)
        generated_at = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y às %H:%M")
        gallery_name = escape(gallery.name)
        client_name = escape(owner.full_name if owner else "Cliente")
        cards = []
        for item in purchased_items:
            cards.append(
                f'<article class="photo"><div class="preview">{_selection_html_preview(db, item)}</div>'
                f'<div class="caption">{escape(item.filename_snapshot)}</div></article>'
            )
        content = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fotos compradas — {gallery_name} — {client_name}</title>
<style>
:root {{ color-scheme: light; font-family: Arial, sans-serif; color: #202124; background: #f5f3ef; }}
body {{ margin: 0; padding: 28px; }} main {{ max-width: 1440px; margin: 0 auto; }}
header {{ background: #fff; border: 1px solid #d9d4cc; border-radius: 14px; padding: 22px; margin-bottom: 22px; }}
h1 {{ margin: 0 0 10px; font-size: 25px; }} p {{ margin: 5px 0; color: #5f5a53; }}
.photos {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; }}
.photo {{ background: #fff; border: 1px solid #d9d4cc; border-radius: 12px; overflow: hidden; break-inside: avoid; }}
.preview {{ aspect-ratio: 4 / 3; display: grid; place-items: center; background: #ece9e4; }}
.preview img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}
.preview-missing {{ padding: 16px; color: #6d675f; text-align: center; }}
.caption {{ display: block; padding: 10px 12px 12px; font-weight: 600; overflow-wrap: anywhere; }}
@media (max-width: 1100px) {{ .photos {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} }}
@media (max-width: 620px) {{ body {{ padding: 14px; }} .photos {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }} }}
@media print {{ body {{ padding: 0; background: #fff; }} header {{ border: 0; padding: 0 0 14px; }} .photos {{ grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }} .photo {{ border-color: #bbb; }} }}
</style></head><body><main>
<header><h1>Fotos compradas</h1><p><strong>Galeria — Cliente:</strong> {gallery_name} — {client_name}</p><p><strong>Gerado em:</strong> {generated_at}</p><p><strong>Total:</strong> {len(cards)} foto(s)</p></header>
<section class="photos" aria-label="Fotos compradas">{"".join(cards)}</section>
</main></body></html>"""
        audit(db, "selection.exported", str(gallery_id), tenant_id=tenant_id)
        db.commit()
        return HTMLResponse(
            content,
            headers={"Content-Disposition": _purchased_photos_content_disposition(owner.full_name if owner else None), "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )
    rows = []
    for selection in db.scalars(
        select(PhotoSelection).where(PhotoSelection.tenant_id == tenant_id).where(
            PhotoSelection.derived_gallery_id == gallery_id,
            PhotoSelection.client_id == selected_client_id,
        )
    ):
        photo = owned_record(db, PhotoAsset, selection.photo_asset_id, tenant_id=tenant_id)
        if photo:
            rows.append((str(photo.id), photo.filename))
    separator = "\t" if format == "txt" else ","
    content = "".join(f"{identifier}{separator}{filename}\n" for identifier, filename in rows)
    audit(db, "selection.exported", str(gallery_id), tenant_id=tenant_id)
    db.commit()
    return PlainTextResponse(
        content,
        media_type="text/plain" if format == "txt" else "text/csv",
        headers={"Content-Disposition": f'attachment; filename="selecao.{format}"'},
    )


@app.get("/admin/orders/{order_id}/selection/export.{format}")
def export_finalized_order(order_id: UUID, format: str, request: Request,
                           db: Session = Depends(db_session)) -> PlainTextResponse:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    order = owned_record(db, SaleOrder, order_id, tenant_id=tenant_id)
    if format not in {"csv", "txt"} or not order or not order_fulfillable(order):
        raise HTTPException(status_code=404, detail="Seleção finalizada não encontrada.")
    items = db.scalars(select(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id).where(
        SaleOrderItem.sale_order_id == order.id,
    ).order_by(SaleOrderItem.filename_snapshot))
    output = StringIO()
    csv.writer(output, delimiter="\t" if format == "txt" else ",", lineterminator="\n").writerows(
        (str(item.photo_asset_id_snapshot), item.filename_snapshot) for item in items
    )
    audit(db, "selection.exported", str(order.id), tenant_id=tenant_id)
    db.commit()
    return PlainTextResponse(output.getvalue(), media_type="text/plain" if format == "txt" else "text/csv",
                             headers={"Content-Disposition": f'attachment; filename="selecao-{order.id}.{format}"',
                                      "Cache-Control": "private, no-store"})


@app.get("/admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/selection/export.{format}")
def export_canonical_selection(
    parent_gallery_id: UUID,
    client_id: UUID,
    format: str,
    request: Request,
    highlight: str | None = Query(default=None),
    db: Session = Depends(db_session),
) -> Response:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    if format not in {"txt", "csv", "html"}:
        raise HTTPException(status_code=404, detail="Formato não suportado.")
    parent = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
    owner = owned_record(db, Client, client_id, tenant_id=tenant_id)
    registration = db.scalar(select(ParentGalleryRegistration.id).where(ParentGalleryRegistration.tenant_id == tenant_id).where(
        ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
        ParentGalleryRegistration.client_id == client_id,
    ))
    historical_order = db.scalar(select(SaleOrder.id).where(SaleOrder.tenant_id == tenant_id).where(
        SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
        SaleOrder.client_id == client_id,
        SaleOrder.payment_status == "confirmed",
    ).limit(1)) if not registration else None
    if not parent or not owner or not (registration or historical_order):
        raise HTTPException(status_code=404, detail="Cliente não pertence a esta galeria.")

    if format == "html":
        purchased_rows = list(db.execute(
            select(SaleOrderItem, SaleOrder).where(SaleOrderItem.tenant_id == tenant_id)
            .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
            .where(
                SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
                SaleOrder.client_id == client_id,
                SaleOrder.payment_status == "confirmed",
            )
            .order_by(SaleOrder.confirmed_at, SaleOrder.id, SaleOrderItem.filename_snapshot)
        ))
        purchased_items = [item for item, _order in purchased_rows]
        if not purchased_items:
            raise HTTPException(status_code=409, detail="Nenhuma compra confirmada para esta cliente nesta galeria.")
        interactions_by_item = _purchase_photo_interactions(
            db,
            tenant_id=tenant_id,
            purchases=[(order, item) for item, order in purchased_rows],
        )
        cards_markup: list[str] = []
        for item, _order in purchased_rows:
            preview_markup = _selection_html_preview(db, item)
            interaction_markup = (
                _purchase_photo_interaction_html(interactions_by_item.get(item.id, {}))
                if preview_markup.lstrip().startswith("<img ")
                else ""
            )
            cards_markup.append(
                '<article class="photo"><div class="preview">'
                + preview_markup
                + interaction_markup
                + '</div><p>' + escape(item.filename_snapshot) + '</p></article>'
            )
        cards = "".join(cards_markup)
        accent = highlight if re.fullmatch(r"#[0-9a-fA-F]{6}", highlight or "") else "#7656d6"
        content = (
            '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Fotos compradas</title><style>'
            ':root{--highlight:' + accent + '}'
            'body{font-family:Arial,sans-serif;margin:24px;color:#202124}'
            '.photos{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}'
            '.photo{border:1px solid #ddd;border-radius:8px;overflow:hidden;break-inside:avoid}'
            '.preview{position:relative;aspect-ratio:4/3;background:#eee;display:grid;place-items:center;overflow:hidden}'
            '.preview img{width:100%;height:100%;object-fit:contain}'
            '.interaction-favorite{position:absolute;top:8px;right:8px;display:grid;place-items:center;min-width:30px;height:30px;padding:0 7px;border-radius:999px;background:var(--highlight);color:#fff;font-size:1rem;font-weight:700;box-shadow:0 1px 5px #0008}'
            '.interaction-comment{position:absolute;left:8px;right:8px;bottom:8px;margin:0;padding:6px 8px;border-left:3px solid var(--highlight);border-radius:4px;background:rgb(17 24 39 / 86%);color:#fff;font-size:clamp(.68rem,2.4vw,.82rem);line-height:1.25;overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}'
            '.photo p{padding:0 12px;overflow-wrap:anywhere}'
            '</style></head><body><main><h1>Fotos compradas</h1><p>'
            + escape(parent.name) + ' — ' + escape(owner.full_name)
            + '</p><p>Total: ' + str(len(purchased_items))
            + ' foto(s)</p><section class="photos">' + cards
            + '</section></main></body></html>'
        )
        audit(db, "selection.exported", str(parent_gallery_id), tenant_id=tenant_id)
        db.commit()
        return HTMLResponse(content, headers={
            "Content-Disposition": _purchased_photos_content_disposition(owner.full_name),
            "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        })

    allowed_photo_ids = authorized_canonical_photos(
        parent_gallery_id, client_id
    ).with_only_columns(PhotoAsset.id)
    rows = list(db.execute(
        select(PhotoAsset.id, PhotoAsset.filename).where(PhotoAsset.tenant_id == tenant_id)
        .join(PhotoSelection, PhotoSelection.photo_asset_id == PhotoAsset.id)
        .where(
            PhotoSelection.parent_gallery_id == parent_gallery_id,
            PhotoSelection.client_id == client_id,
            PhotoAsset.id.in_(allowed_photo_ids),
        )
        .order_by(PhotoAsset.filename, PhotoAsset.id)
    ))
    output = StringIO()
    writer = csv.writer(output, delimiter="\t" if format == "txt" else ",", lineterminator="\n")
    writer.writerows((str(photo_id), filename) for photo_id, filename in rows)
    audit(db, "selection.exported", str(parent_gallery_id), tenant_id=tenant_id)
    db.commit()
    return PlainTextResponse(
        output.getvalue(), media_type="text/plain" if format == "txt" else "text/csv",
        headers={"Content-Disposition": f'attachment; filename="selecao.{format}"',
                 "Cache-Control": "private, no-store"},
    )


@app.post("/admin/parent-galleries/{parent_gallery_id}/photos", status_code=status.HTTP_201_CREATED)
def register_photo_asset(
    parent_gallery_id: UUID,
    payload: PhotoAssetInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Cadastro direto descontinuado. Selecione uma pasta em preparação.",
    )


def _stored_source_matches_fingerprint(path: Path, expected_fingerprint: str) -> bool | None:
    """Retorna None quando o filesystem não permite provar a presença/ausência da fonte."""
    return photographer_credits.source_fingerprint_state(path, expected_fingerprint)


def _settle_photo_credit_after_write_failure(
    db: Session,
    *,
    tenant_id: UUID,
    photo_id: UUID,
    destination: Path,
    payload_fingerprint: str,
    operation: PhotoCreditOperation | None,
    actor_admin_id: UUID | None,
) -> None:
    if operation is None or operation.status in {"consumed", "released"}:
        return
    source_is_durable = _stored_source_matches_fingerprint(destination, payload_fingerprint)
    try:
        if source_is_durable is True:
            photographer_credits.consume_photo_credit(
                db, tenant_id, photo_id, payload_fingerprint,
                actor_admin_id=actor_admin_id,
            )
        else:
            photographer_credits.release_photo_credit(
                db,
                tenant_id,
                photo_id,
                proven_pre_durable_failure=source_is_durable is False,
                actor_admin_id=actor_admin_id,
            )
        db.commit()
    except (HTTPException, SQLAlchemyError):
        db.rollback()


@app.put("/admin/photo-assets/{photo_id}/source", status_code=status.HTTP_202_ACCEPTED)
async def import_photo_source(
    photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    """Recebe somente JPEG para processamento local, nunca para entrega web direta."""
    tenant_id = directory_tenant_id(db, request)
    from app.tenant_closure import require_new_work
    require_new_work(db, tenant_id)
    admin_session = require_admin(request)
    actor_admin_id = getattr(admin_session, "subject_id", None)
    photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    content_type = (request.headers.get("content-type") or "").lower()
    parent = db.scalar(select(ParentGallery).where(
        ParentGallery.id == photo.parent_gallery_id,
        ParentGallery.tenant_id == tenant_id,
    ).with_for_update())
    if not parent:
        raise HTTPException(status_code=409, detail="A galeria da foto não está disponível.")
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == photo.folder_id, PhotoFolder.tenant_id == tenant_id,
    ).with_for_update())
    if not folder or folder.parent_gallery_id != photo.parent_gallery_id:
        raise HTTPException(status_code=409, detail="A foto não possui uma pasta válida.")
    if not folder_media_writes_allowed(db, folder):
        raise HTTPException(status_code=409, detail="A pasta está em uma etapa de arquivo ou recuperação.")
    from app.photographer_onboarding import require_upload_ready
    require_upload_ready(
        db, tenant_id=tenant_id, admin_id=actor_admin_id,
        accepted_photo=photo if folder.purpose == "content" else None,
    )
    if photo.derived_gallery_id:
        if folder.derived_gallery_id != photo.derived_gallery_id:
            raise HTTPException(status_code=409, detail="A foto não possui escopo privado válido.")
        require_derived_gallery_mutable(
            db, photo.derived_gallery_id, allow_deleted_origin=True,
            tenant_id=tenant_id,
        )
    else:
        require_parent_gallery_mutable(db, photo.parent_gallery_id, tenant_id=tenant_id)
    accepts_upload = (
        folder.purpose == "content" and folder.status in {"preparing", "released"}
    ) or (folder.purpose == "cover_assets" and folder.status == "preparing")
    if not accepts_upload:
        raise HTTPException(status_code=409, detail="A pasta não aceita novas fotos.")
    destination = safe_source_path(photo)
    batch_asset = db.scalar(
        select(PrivateUploadBatchAsset)
        .join(PrivateUploadBatch, PrivateUploadBatch.id == PrivateUploadBatchAsset.batch_id)
        .where(
            PrivateUploadBatchAsset.tenant_id == tenant_id,
            PrivateUploadBatchAsset.photo_asset_id == photo.id,
            PrivateUploadBatch.tenant_id == tenant_id,
            PrivateUploadBatch.status == "open",
        )
        .order_by(PrivateUploadBatch.created_at.desc(), PrivateUploadBatch.id.desc())
        .limit(1)
    )
    if batch_asset:
        try:
            batch_for(db, batch_asset.batch_id, photo.derived_gallery_id, open_only=True, tenant_id=tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        existing_job = db.scalar(select(MediaJob.id).where(MediaJob.tenant_id == tenant_id).where(MediaJob.photo_asset_id == photo.id))
        if existing_job and request.headers.get("x-facial-reindex") != "true":
            return {"status": "queued"}  # retomada idempotente não sobrescreve/reprocessa
    from app.facial.lifecycle import (
        SourceCapacityError,
        admit_source,
        analysis_for,
        finalize_source,
        write_source,
    )

    credit_operation = None
    expected_fingerprint = (
        photographer_credits.fingerprint_from_storage_key(photo.storage_key)
        if folder.purpose == "content" else None
    )
    try:
        if folder.purpose == "content":
            pending_operation = db.scalar(select(PhotoCreditOperation).where(
                PhotoCreditOperation.tenant_id == tenant_id,
                PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
            ))
            if (
                pending_operation
                and pending_operation.status == "reconciliation_required"
                and pending_operation.payload_fingerprint == expected_fingerprint
            ):
                durable_state = _stored_source_matches_fingerprint(
                    destination, pending_operation.payload_fingerprint,
                )
                photographer_credits.reconcile_photo_credit(
                    db,
                    tenant_id,
                    photo.id,
                    pending_operation.payload_fingerprint,
                    source_is_durable=durable_state,
                    actor_admin_id=actor_admin_id,
                )
                db.commit()
                if durable_state is None:
                    raise HTTPException(
                        status_code=503,
                        detail="O upload aguarda reconciliação da fonte armazenada.",
                        headers={"Retry-After": "15"},
                    )
            credit_operation = photographer_credits.reserve_photo_credit(
                db,
                tenant_id,
                photo.id,
                photo.storage_key,
                expected_fingerprint,
                actor_admin_id=actor_admin_id,
            )
            photographer_credits.record_upload_attempt(
                db, credit_operation, actor_admin_id=actor_admin_id,
            )
            if credit_operation:
                # A reserva fica durável antes de a API começar a ler o JPEG.
                db.commit()
    except HTTPException:
        db.rollback()
        raise

    try:
        if not content_type.startswith("image/jpeg"):
            raise HTTPException(status_code=415, detail="Envie uma imagem JPEG.")
        body = await read_bounded_body(
            request, max_bytes=25 * 1024 * 1024,
            error_detail="A imagem excede o limite permitido.",
        )
        payload_fingerprint = sha256(body).hexdigest()
        if expected_fingerprint is not None and payload_fingerprint != expected_fingerprint:
            raise HTTPException(
                status_code=409,
                detail="A imagem não corresponde à identidade cadastrada.",
            )
        try:
            with Image.open(BytesIO(body)) as image:
                if image.format != "JPEG":
                    raise ValueError
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Imagem JPEG inválida.") from exc
        if folder.purpose == "cover_assets":
            try:
                with Image.open(BytesIO(body)) as image:
                    visual = ImageOps.exif_transpose(image)
                    visual.load()
                    horizontal = visual.width > visual.height
            except (OSError, ValueError) as exc:
                raise HTTPException(status_code=422, detail="Imagem JPEG inválida.") from exc
            if not horizontal:
                raise HTTPException(
                    status_code=422,
                    detail="Envie uma capa horizontal, com largura maior que a altura.",
                )
    except asyncio.CancelledError:
        db.rollback()
        if credit_operation:
            _settle_photo_credit_after_write_failure(
                db,
                tenant_id=tenant_id,
                photo_id=photo.id,
                destination=destination,
                payload_fingerprint=credit_operation.payload_fingerprint,
                operation=credit_operation,
                actor_admin_id=actor_admin_id,
            )
        raise
    except HTTPException:
        db.rollback()
        if credit_operation:
            _settle_photo_credit_after_write_failure(
                db,
                tenant_id=tenant_id,
                photo_id=photo.id,
                destination=destination,
                payload_fingerprint=credit_operation.payload_fingerprint,
                operation=credit_operation,
                actor_admin_id=actor_admin_id,
            )
        raise
    except Exception:
        db.rollback()
        if credit_operation:
            _settle_photo_credit_after_write_failure(
                db,
                tenant_id=tenant_id,
                photo_id=photo.id,
                destination=destination,
                payload_fingerprint=credit_operation.payload_fingerprint,
                operation=credit_operation,
                actor_admin_id=actor_admin_id,
            )
        raise

    # O lock do PhotoAsset cobre o estado de análise depois do recebimento; a
    # carteira e sua operação já foram serializadas e confirmadas antes do body.
    try:
        db.scalar(select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id).where(PhotoAsset.id == photo.id).with_for_update())
        analysis = admit_source(db, photo, body, reindex=request.headers.get("x-facial-reindex") == "true") if folder.purpose == "content" else None
        if analysis and analysis.state != "receiving":
            if credit_operation:
                _settle_photo_credit_after_write_failure(
                    db,
                    tenant_id=tenant_id,
                    photo_id=photo.id,
                    destination=destination,
                    payload_fingerprint=credit_operation.payload_fingerprint,
                    operation=credit_operation,
                    actor_admin_id=actor_admin_id,
                )
            return {"status": "queued"}  # replay não recria fonte já descartada
        if analysis:
            db.commit()
        if analysis:
            analysis = analysis_for(db, photo.id, lock=True, tenant_id=tenant_id)
            if analysis is None:
                _settle_photo_credit_after_write_failure(
                    db,
                    tenant_id=tenant_id,
                    photo_id=photo.id,
                    destination=destination,
                    payload_fingerprint=payload_fingerprint,
                    operation=credit_operation,
                    actor_admin_id=actor_admin_id,
                )
                raise HTTPException(status_code=409, detail="Foto indisponível para processamento.")
            if analysis.state != "receiving":
                _settle_photo_credit_after_write_failure(
                    db,
                    tenant_id=tenant_id,
                    photo_id=photo.id,
                    destination=destination,
                    payload_fingerprint=payload_fingerprint,
                    operation=credit_operation,
                    actor_admin_id=actor_admin_id,
                )
                return {"status": "queued"}
    except HTTPException:
        db.rollback()
        if credit_operation:
            _settle_photo_credit_after_write_failure(
                db,
                tenant_id=tenant_id,
                photo_id=photo.id,
                destination=destination,
                payload_fingerprint=credit_operation.payload_fingerprint,
                operation=credit_operation,
                actor_admin_id=actor_admin_id,
            )
        raise
    except SourceCapacityError as exc:
        db.rollback()
        if credit_operation:
            _settle_photo_credit_after_write_failure(
                db,
                tenant_id=tenant_id,
                photo_id=photo.id,
                destination=destination,
                payload_fingerprint=credit_operation.payload_fingerprint,
                operation=credit_operation,
                actor_admin_id=actor_admin_id,
            )
        raise HTTPException(status_code=503, detail=str(exc), headers={"Retry-After": "15"}) from exc
    except (ValueError, FacialConfigurationError) as exc:
        db.rollback()
        if credit_operation:
            _settle_photo_credit_after_write_failure(
                db,
                tenant_id=tenant_id,
                photo_id=photo.id,
                destination=destination,
                payload_fingerprint=credit_operation.payload_fingerprint,
                operation=credit_operation,
                actor_admin_id=actor_admin_id,
            )
        raise HTTPException(status_code=422, detail="Imagem ou processamento indisponível.") from exc

    try:
        directory_tenant_id(db, request)
        folder = db.scalar(select(PhotoFolder).where(
            PhotoFolder.id == photo.folder_id, PhotoFolder.tenant_id == tenant_id,
        ).with_for_update())
        if not folder or not folder_media_writes_allowed(db, folder):
            raise HTTPException(
                status_code=409,
                detail="A pasta entrou em uma etapa de arquivo ou recuperação durante o upload.",
            )
        write_source(destination, body, tenant_id=tenant_id, authorize=lambda: directory_tenant_id(db, request))
    except Exception as exc:
        db.rollback()
        _settle_photo_credit_after_write_failure(
            db,
            tenant_id=tenant_id,
            photo_id=photo.id,
            destination=destination,
            payload_fingerprint=payload_fingerprint,
            operation=credit_operation,
            actor_admin_id=actor_admin_id,
        )
        if isinstance(exc, HTTPException):
            raise
        if isinstance(exc, ValueError):
            raise HTTPException(status_code=422, detail="Imagem ou processamento indisponível.") from exc
        raise HTTPException(
            status_code=503,
            detail="Não foi possível concluir o armazenamento da imagem.",
            headers={"Retry-After": "15"},
        ) from exc

    if credit_operation:
        try:
            photographer_credits.consume_photo_credit(
                db, tenant_id, photo.id, payload_fingerprint,
                actor_admin_id=actor_admin_id,
            )
            # O débito é confirmado imediatamente após o rename durável, antes de derivados.
            db.commit()
        except Exception as exc:
            db.rollback()
            try:
                operation = db.scalar(select(PhotoCreditOperation).where(
                    PhotoCreditOperation.tenant_id == tenant_id,
                    PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
                ))
                if operation and operation.status in {"reserved", "reconciliation_required"}:
                    photographer_credits.release_photo_credit(
                        db,
                        tenant_id,
                        photo.id,
                        proven_pre_durable_failure=False,
                        actor_admin_id=actor_admin_id,
                    )
                    db.commit()
            except (HTTPException, SQLAlchemyError):
                db.rollback()
            raise HTTPException(
                status_code=503,
                detail="A fonte foi armazenada e aguarda confirmação dos créditos.",
                headers={"Retry-After": "15"},
            ) from exc

    if analysis:
        finalize_source(db, photo)
    if folder.purpose == "cover_assets":
        gallery = owned_record(db, ParentGallery, photo.parent_gallery_id, tenant_id=tenant_id)
        if gallery:
            gallery.cover_photo_id = photo.id
            audit(db, "parent_gallery.cover_upload_accepted", str(photo.id), tenant_id=tenant_id)
    enqueue_derivatives(db, photo)
    audit(db, "photo_asset.imported", str(photo.id), tenant_id=tenant_id)
    db.commit()
    return {"status": "queued"}


@app.get("/admin/photo-assets/{photo_id}/media-status")
def photo_media_status(
    photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    """Estado de processamento usado pela interface administrativa."""
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == photo.folder_id,
        PhotoFolder.tenant_id == tenant_id,
    ))
    archive_state = folder_media_state(db, folder) if folder else "unavailable"
    job = db.scalar(select(MediaJob).where(MediaJob.tenant_id == tenant_id).where(MediaJob.photo_asset_id == photo_id))
    if not job:
        return {"status": "not_imported", "media_state": archive_state}
    return {"status": job.status, "media_state": archive_state}


@app.get("/admin/photo-assets/{photo_id}/facial-analysis")
def admin_photo_facial_analysis(
    photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    if not owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    from app.facial.lifecycle import analysis_for

    row = analysis_for(db, photo_id, tenant_id=tenant_id)
    if not row:
        return {"pipeline": "legacy-preview-v1"}
    # Lista explícita: nenhuma caixa, vetor, caminho ou conteúdo da imagem.
    allowed = {"width", "height", "megapixels", "elapsed_ms", "passes", "reasons", "tiles",
               "budget_exhausted", "raw_detections", "deduplicated", "embedding_successes",
               "embedding_failures", "detection_failures", "faces_accepted", "faces_rejected", "rejection_reason", "config", "model", "model_version", "quality_version",
               "final_error", "attempts", "last_error", "cleanup_error"}
    return {"pipeline": row.pipeline_version, "state": row.state,
            "source_bytes": row.source_bytes, "width": row.width, "height": row.height,
            "expires_at": row.expires_at.isoformat(), "source_deleted": row.deleted_at is not None,
            "metrics": {key: value for key, value in row.metrics.items() if key in allowed}}


@app.get("/admin/photo-assets/{photo_id}/preview")
def admin_photo_preview(
    photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    """Prévia sem marca para conferência administrativa; nunca é o original."""

    tenant_id = directory_tenant_id(db, request)
    photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    if not _admin_photo_preview_available(db, photo, allow_cover_thumbnail=True):
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    derivative = db.scalar(
        select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(
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
    audit(db, "media_preview.admin_viewed", str(photo_id), tenant_id=tenant_id)
    db.commit()
    return protected_preview_response(path, f"conferencia-{photo.filename}")


@app.get("/admin/photo-assets/{photo_id}/watermarked-preview")
def admin_watermarked_photo_preview(
    photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    """Prévia marcada para organizar pastas sem expor o arquivo de origem."""

    tenant_id = directory_tenant_id(db, request)
    photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    if not _admin_photo_preview_available(db, photo, allow_cover_thumbnail=False):
        raise HTTPException(status_code=404, detail="Prévia com marca d’água indisponível.")
    derivative = db.scalar(
        select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(
            MediaDerivative.photo_asset_id == photo_id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
    )
    if not derivative:
        raise HTTPException(status_code=404, detail="Prévia com marca d’água indisponível.")
    try:
        path = presentation_path(db, derivative)
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail="Prévia com marca d’água indisponível."
        ) from exc
    audit(db, "media_preview.admin_watermarked_viewed", str(photo_id), tenant_id=tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    query = select(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(SaleOrder.payment_status == "confirmed")
    if parent_gallery_id:
        query = query.where(SaleOrder.parent_gallery_id_snapshot == parent_gallery_id)
    if client_id:
        query = query.where(SaleOrder.client_id == client_id)
    orders = list(db.scalars(query.order_by(SaleOrder.confirmed_at.desc(), SaleOrder.created_at.desc())))
    mp_payments = mercadopago_for_orders(db, orders, tenant_id=tenant_id)
    card_ids = {order.provider_payment_id for order in orders if order.provider_payment_id}
    card_payments = {
        payment.id: payment for payment in db.scalars(select(ProviderPayment).where(
            ProviderPayment.tenant_id == tenant_id,
            ProviderPayment.id.in_(card_ids),
        ))
    } if card_ids else {}
    order_ids = [order.id for order in orders]
    item_rows = list(db.scalars(
        select(SaleOrderItem).where(
            SaleOrderItem.tenant_id == tenant_id,
            SaleOrderItem.sale_order_id.in_(order_ids),
        ).order_by(SaleOrderItem.sale_order_id, SaleOrderItem.filename_snapshot)
    )) if order_ids else []
    items_by_order: dict[UUID, list[SaleOrderItem]] = defaultdict(list)
    for item in item_rows:
        items_by_order[item.sale_order_id].append(item)
    media_states = folder_media_states_by_id(
        db,
        folder_ids={item.folder_id_snapshot for item in item_rows if item.folder_id_snapshot},
        tenant_id=tenant_id,
    )
    result: list[dict[str, object]] = []
    for order in orders:
        client = owned_record(db, Client, order.client_id, tenant_id=tenant_id)
        gallery = (
            owned_record(db, DerivedGallery, order.derived_gallery_id, tenant_id=tenant_id) if order.derived_gallery_id else None
        )
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
                **({"payment_method": "credit_card" if order.provider_payment_id else "pix"}
                   if order.provider_payment_id or order.payment_group_id else {}),
                **mercadopago_fields(order, mp_payments),
                **({"provider_payment_state": card_payments[order.provider_payment_id].state}
                   if order.provider_payment_id in card_payments else {}),
                "items": [
                    {
                        "photo_id": str(item.photo_asset_id_snapshot),
                        "name": item.filename_snapshot,
                        "media_state": (
                            "available" if item.folder_id_snapshot is None
                            else media_states.get(item.folder_id_snapshot, "unavailable")
                        ),
                        "preview_url": f"/admin/photo-assets/{item.photo_asset_id}/preview"
                        if item.photo_asset_id and (
                            item.folder_id_snapshot is None
                            or media_states.get(item.folder_id_snapshot) in {"available", "archiving"}
                        )
                        else None,
                        "operational_media_available": item.photo_asset_id is not None and (
                            item.folder_id_snapshot is None
                            or media_states.get(item.folder_id_snapshot) in {"available", "archiving"}
                        ),
                    }
                    for item in items_by_order.get(order.id, [])
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
    require_active_owner(db, preset.tenant_id)
    tiers = list(
        db.scalars(
            select(ProgressivePricingTier)
            .where(ProgressivePricingTier.preset_id == preset.id, ProgressivePricingTier.tenant_id == preset.tenant_id)
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
    require_active_owner(db, preset.tenant_id)
    db.execute(
        delete(ProgressivePricingTier).where(
            ProgressivePricingTier.tenant_id == preset.tenant_id,
            ProgressivePricingTier.preset_id == preset.id
        )
    )
    db.add_all(
        [
            ProgressivePricingTier(
                tenant_id=preset.tenant_id,
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
    tenant_id = directory_tenant_id(db, request)
    statement = select(ProgressivePricingPreset).where(ProgressivePricingPreset.tenant_id == tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    tiers = _validated_price_tiers(payload.tiers)
    preset = ProgressivePricingPreset(
        tenant_id=tenant_id,
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
    )
    try:
        db.add(preset)
        db.flush()
        _replace_pricing_preset_tiers(db, preset, tiers)
        audit(db, "pricing.preset_created", str(preset.id), tenant_id=tenant_id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Já existe uma tabela com este código."
        ) from exc
    db.refresh(preset)
    return _pricing_preset_payload(db, preset)


def _pricing_preset_or_404(
    db: Session, preset_id: UUID, *, tenant_id: UUID
) -> ProgressivePricingPreset:
    preset = owned_record(db, ProgressivePricingPreset, preset_id, tenant_id=tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    tiers = _validated_price_tiers(payload.tiers)
    preset = _pricing_preset_or_404(db, preset_id, tenant_id=tenant_id)
    preset.code = payload.code.strip().upper()
    preset.name = payload.name.strip()
    preset.version += 1
    preset.updated_at = now()
    _replace_pricing_preset_tiers(db, preset, tiers)
    audit(db, "pricing.preset_updated", str(preset.id), tenant_id=tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    preset = _pricing_preset_or_404(db, preset_id, tenant_id=tenant_id)
    preset.active = False
    preset.updated_at = now()
    audit(db, "pricing.preset_deactivated", str(preset.id), tenant_id=tenant_id)
    db.commit()
    db.refresh(preset)
    return _pricing_preset_payload(db, preset)


@app.post("/admin/pricing-presets/{preset_id}/activate")
def activate_progressive_pricing_preset(
    preset_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    preset = _pricing_preset_or_404(db, preset_id, tenant_id=tenant_id)
    if not preset.active:
        preset.active = True
        preset.updated_at = now()
        audit(db, "pricing.preset_activated", str(preset.id), tenant_id=tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    preset = _pricing_preset_or_404(db, preset_id, tenant_id=tenant_id)
    stored_tiers = list(
        db.scalars(
            select(ProgressivePricingTier)
            .where(ProgressivePricingTier.preset_id == preset.id, ProgressivePricingTier.tenant_id == preset.tenant_id)
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


def pricing_payload(db: Session, parent_gallery_id: UUID, *, tenant_id: UUID) -> dict[str, object]:
    gallery = _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    rules = list(
        db.scalars(
            select(PriceRule)
            .where(PriceRule.parent_gallery_id == parent_gallery_id, PriceRule.tenant_id == tenant_id)
            .order_by(PriceRule.minimum_quantity)
        )
    )
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
        "pix": pix_payload(global_pix_settings(db, tenant_id=tenant_id)),
    }


def save_parent_pricing(
    db: Session, parent_gallery_id: UUID, payload: GalleryPricingInput, *, tenant_id: UUID
) -> list[PriceTier]:
    gallery = require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
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
                detail="Preço progressivo exige somente uma tabela ativa da sua conta.",
            )
        preset = _pricing_preset_or_404(db, payload.progressive_pricing_preset_id, tenant_id=tenant_id)
        if not preset.active:
            raise HTTPException(
                status_code=422, detail="A tabela de preços escolhida está desativada."
            )
        stored_tiers = list(
            db.scalars(
                select(ProgressivePricingTier)
                .where(ProgressivePricingTier.preset_id == preset.id, ProgressivePricingTier.tenant_id == tenant_id)
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

    if getattr(payload, "payment_required", gallery.payment_required) and any(
        tier.unit_price_cents <= 0 for tier in tiers
    ):
        raise HTTPException(status_code=422, detail="Pagamento obrigatório exige valor unitário maior que zero.")
    gallery.pricing_mode = pricing_mode
    gallery.fixed_unit_price_cents = (
        tiers[0].unit_price_cents if pricing_mode == "fixed" else None
    )
    gallery.progressive_pricing_preset_id = preset.id if preset else None
    gallery.pricing_snapshot = pricing_snapshot
    gallery.pricing_review_required = review_required
    db.execute(delete(PriceRule).where(PriceRule.parent_gallery_id == parent_gallery_id, PriceRule.tenant_id == tenant_id))
    db.add_all(
        [
            PriceRule(
                tenant_id=tenant_id,
                parent_gallery_id=parent_gallery_id,
                minimum_quantity=tier.minimum_quantity,
                maximum_quantity=tier.maximum_quantity,
                unit_price_cents=tier.unit_price_cents,
            )
            for tier in tiers
        ]
    )
    return tiers


@app.get("/admin/parent-galleries/{parent_gallery_id}/pricing")
def admin_parent_gallery_pricing(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    _parent_gallery_or_404(db, parent_gallery_id, tenant_id=tenant_id)
    return pricing_payload(db, parent_gallery_id, tenant_id=tenant_id)


@app.put("/admin/parent-galleries/{parent_gallery_id}/pricing")
def save_admin_parent_gallery_pricing(
    parent_gallery_id: UUID,
    payload: GalleryPricingInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    require_parent_gallery_mutable(db, parent_gallery_id, tenant_id=tenant_id)
    tiers = save_parent_pricing(db, parent_gallery_id, payload, tenant_id=tenant_id)
    audit(db, "pricing.settings_updated", str(parent_gallery_id), tenant_id=tenant_id)
    db.commit()
    return {
        **pricing_payload(db, parent_gallery_id, tenant_id=tenant_id),
        "has_downward_jump": has_downward_jump(tiers),
    }


@app.get("/admin/derived-galleries/{gallery_id}/pricing")
def admin_gallery_pricing(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    return {
        **pricing_payload(db, parent.id, tenant_id=tenant_id),
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    raise HTTPException(
        status_code=409,
        detail=("Preços são herdados da Galeria pública. O PIX vale para sua conta, em Configurações."),
    )


@app.get("/admin/derived-galleries/{gallery_id}/orders")
def admin_gallery_orders(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Exibe snapshots de pedidos sem executar confirmação financeira."""

    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    orders = list(
        db.scalars(
            select(SaleOrder).where(SaleOrder.tenant_id == tenant_id)
            .where(SaleOrder.derived_gallery_id_snapshot == gallery_id,
                   visible_sale_order_condition(tenant_id=tenant_id))
            .order_by(SaleOrder.created_at.desc())
        )
    )
    if not gallery and not orders:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    payment_groups = {group.id: group for group in db.scalars(select(PaymentGroup).where(PaymentGroup.tenant_id == tenant_id).where(
        PaymentGroup.id.in_({order.payment_group_id for order in orders if order.payment_group_id})))}
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
                "payment_group": ({"id": str(order.payment_group_id),
                                   "total_cents": payment_groups[order.payment_group_id].total_cents}
                                  if order.payment_group_id else None),
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
                        select(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id)
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
    """Compatibilidade do vínculo antigo; nunca cria uma nova galeria derivada."""

    tenant_id = directory_tenant_id(db, request)
    current_session(request, Role.ADMIN)
    parent = owned_record(db, ParentGallery, payload.parent_gallery_id, tenant_id=tenant_id)
    client = owned_record(db, Client, payload.client_id, tenant_id=tenant_id)
    if not parent or not client:
        raise HTTPException(status_code=404, detail="Galeria pública ou cliente não encontrado.")
    require_parent_gallery_mutable(db, parent.id, tenant_id=tenant_id)
    if payload.create_empty_private or payload.photo_ids:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="A criação de galerias privadas foi encerrada. Crie a pasta restrita no Acervo da cliente.",
        )
    registration = link_client_to_parent(
        db, parent_gallery_id=parent.id, client_id=client.id, status="active",
    )
    audit(db, "parent_gallery.client_linked_without_private", str(registration.id), tenant_id=tenant_id)
    db.commit()
    return {
        "id": None,
        "private_gallery_id": None,
        "registration_id": str(registration.id),
        "detail": "Cliente vinculada à galeria pública.",
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
        tenant_id=gallery.tenant_id,
    )


@app.get("/admin/derived-galleries/{gallery_id}/link")
def private_gallery_link_status(
    gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id, tenant_id=tenant_id)
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
        select(GalleryAccessCapability).where(GalleryAccessCapability.tenant_id == tenant_id).where(
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
    tenant_id = directory_tenant_id(db, request)
    current_session(request, Role.ADMIN)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Novos links de galeria privada foram encerrados. Use o vínculo da galeria pública.",
    )


@app.post("/admin/derived-galleries/{gallery_id}/link/rotate")
def rotate_private_gallery_link(
    gallery_id: UUID,
    payload: GalleryCapabilityInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    current_session(request, Role.ADMIN)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Novos links de galeria privada foram encerrados. Use o vínculo da galeria pública.",
    )


@app.delete(
    "/admin/derived-galleries/{gallery_id}/link",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_private_gallery_link(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    capability = _private_gallery_link_capability(db, gallery)
    if capability:
        revoke_gallery_capability(capability)
        audit(db, "gallery_capability.private_link_revoked", str(capability.id), tenant_id=tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
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
    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
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
    client = client or owned_record(db, Client, membership.client_id, tenant_id=membership.tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    filters = [DerivedGalleryMembership.derived_gallery_id == gallery.id]
    if status_filter:
        filters.append(DerivedGalleryMembership.status == status_filter)
    total = db.scalar(select(func.count()).select_from(DerivedGalleryMembership).where(DerivedGalleryMembership.tenant_id == tenant_id).where(*filters))
    rows = db.execute(
        select(DerivedGalleryMembership, Client).where(Client.tenant_id == tenant_id, DerivedGalleryMembership.tenant_id == tenant_id)
        .join(Client, Client.id == DerivedGalleryMembership.client_id)
        .where(*filters)
        .order_by(DerivedGalleryMembership.created_at, DerivedGalleryMembership.id)
        .offset(offset)
        .limit(limit)
    ).all()
    projections = build_commercial_projections(
        db,
        gallery_ids={gallery.id},
        client_ids={membership.client_id for membership, _client in rows},
        galleries_by_id={gallery.id: gallery},
        tenant_id=tenant_id,
    )
    return {
        "gallery_id": str(gallery.id),
        "total": total or 0,
        "page": {"offset": offset, "limit": limit},
        "members": [
            {
                **_private_member_payload(
                    db,
                    membership,
                    client=client,
                    selected_count=projection.selected_count,
                    purchased_count=projection.purchased_count,
                    order_count=projection.order_count,
                    confirmed_total_cents=projection.confirmed_total_cents,
                    payment_status=projection.commercial_status,
                ),
                "available_count": projection.available_count,
                "commercial_status": projection.commercial_status,
                "reopening_status": projection.reopening_status,
                "financial_orders": projection.financial_orders,
                "selection_expires_at": None,
            }
            for membership, client in rows
            for projection in [projections[(gallery.id, membership.client_id)]]
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
    tenant_id = directory_tenant_id(db, request)
    admin_session = current_session(request, Role.ADMIN)
    gallery = require_derived_gallery_mutable(db, gallery_id, tenant_id=tenant_id)
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
    client = owned_record(db, Client, payload.client_id, tenant_id=tenant_id)
    if not parent or not client:
        raise HTTPException(status_code=404, detail="Galeria pública ou cliente não encontrado.")

    if not db.scalar(
        select(DerivedGalleryMembership.id).where(DerivedGalleryMembership.tenant_id == tenant_id).where(
            DerivedGalleryMembership.derived_gallery_id == gallery.id
        )
    ):
        legacy_owner = owned_record(db, Client, gallery.client_id, tenant_id=tenant_id)
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
        tenant_id=tenant_id,
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
    tenant_id = directory_tenant_id(db, request)
    admin_session = current_session(request, Role.ADMIN)
    gallery = require_derived_gallery_mutable(db, gallery_id, tenant_id=tenant_id)
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
        tenant_id=tenant_id,
    )
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
    client = owned_record(db, Client, membership.client_id, tenant_id=tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
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
    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
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
    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
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
        "client_logged_in",
    ]
    | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    owner = directory_tenant_id(db, request)
    query = select(GalleryMembershipNotificationOutbox).where(GalleryMembershipNotificationOutbox.tenant_id == owner)
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
                "derived_name": item.derived_name_snapshot
                if item.derived_gallery_id
                else None,
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
    owner = directory_tenant_id(db, request)
    notification = mark_membership_notification_read(db, notification_id, tenant_id=owner)
    if not notification:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    db.commit()
    return {"id": str(notification.id), "status": notification.admin_status}


@app.get("/admin/media-archive/notices")
def list_admin_media_archive_notices(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)

    rows = db.execute(
        select(MediaArchiveNotice, MediaArchiveCycle)
        .join(
            MediaArchiveCycle,
            and_(
                MediaArchiveCycle.id == MediaArchiveNotice.cycle_id,
                MediaArchiveCycle.tenant_id == MediaArchiveNotice.tenant_id,
            ),
        )
        .where(MediaArchiveNotice.tenant_id == tenant_id)
        .order_by(MediaArchiveNotice.created_at.desc(), MediaArchiveNotice.id.desc())
        .limit(limit)
    ).all()
    unread_count = db.scalar(
        select(func.count()).select_from(MediaArchiveNotice).where(
            MediaArchiveNotice.tenant_id == tenant_id,
            MediaArchiveNotice.read_at.is_(None),
            MediaArchiveNotice.superseded_at.is_(None),
        )
    ) or 0
    return {
        "items": [
            {
                "id": str(notice.id),
                "notice_type": notice.notice_type,
                "title": notice.title,
                "body": notice.body,
                "cycle_id": str(cycle.id),
                "folder_id": str(cycle.folder_id),
                "parent_gallery_id": str(cycle.parent_gallery_id),
                "deadline_at": _media_archive_notice_timestamp(notice.deadline_at),
                "created_at": _media_archive_notice_timestamp(notice.created_at),
                "read_at": _media_archive_notice_timestamp(notice.read_at),
                "superseded_at": _media_archive_notice_timestamp(notice.superseded_at),
            }
            for notice, cycle in rows
        ],
        "unread_count": int(unread_count),
    }


def _media_archive_notice_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    else:
        value = value.astimezone(timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    return value.isoformat()


@app.post("/admin/media-archive/notices/{notice_id}/read")
def read_admin_media_archive_notice(
    notice_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str | None]:
    require_same_origin(request)
    tenant_id = directory_tenant_id(db, request)
    notice = db.scalar(
        select(MediaArchiveNotice)
        .where(
            MediaArchiveNotice.id == notice_id,
            MediaArchiveNotice.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if notice is None:
        raise HTTPException(status_code=404, detail="Aviso não encontrado.")
    if notice.read_at is None:
        notice.read_at = now()
        db.commit()
    return {
        "id": str(notice.id),
        "read_at": _media_archive_notice_timestamp(notice.read_at),
    }


@app.get("/admin/derived-galleries/{gallery_id}/upload-batches")
def list_private_upload_batches(gallery_id: UUID, request: Request,
                                db: Session = Depends(db_session)) -> dict:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    require_derived_gallery_mutable(db, gallery_id, allow_deleted_origin=True, tenant_id=tenant_id)
    batches = db.scalars(select(PrivateUploadBatch).where(PrivateUploadBatch.tenant_id == tenant_id).where(
        PrivateUploadBatch.derived_gallery_id == gallery_id,
        PrivateUploadBatch.status == "open",
    ).order_by(PrivateUploadBatch.created_at))
    return {"batches": [batch_payload(db, batch) for batch in batches]}


@app.post("/admin/derived-galleries/{gallery_id}/upload-batches", status_code=201)
def begin_private_upload_batch(gallery_id: UUID, request: Request,
                               db: Session = Depends(db_session)) -> dict:
    tenant_id = directory_tenant_id(db, request)
    session = require_admin(request)
    require_same_origin(request)
    from app.photographer_onboarding import require_upload_ready
    require_upload_ready(db, tenant_id=tenant_id, admin_id=session.subject_id, require_credit=True)
    gallery = require_derived_gallery_mutable(db, gallery_id, allow_deleted_origin=True, tenant_id=tenant_id)
    if not gallery.access_enabled:
        raise HTTPException(status_code=409, detail="A galeria privada está bloqueada.")
    batch = create_batch(db, gallery, session.subject_id)
    audit(db, "private_upload_batch.created", str(batch.id), tenant_id=tenant_id)
    db.commit()
    return batch_payload(db, batch)


@app.post("/admin/derived-galleries/{gallery_id}/upload-batches/{batch_id}/close")
def finish_private_upload_batch(gallery_id: UUID, batch_id: UUID, request: Request,
                                db: Session = Depends(db_session)) -> dict:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    require_same_origin(request)
    require_derived_gallery_mutable(db, gallery_id, allow_deleted_origin=True, tenant_id=tenant_id)
    try:
        batch = close_batch(db, batch_id, gallery_id, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit(db, "private_upload_batch.closed", str(batch.id), tenant_id=tenant_id)
    db.commit()
    return batch_payload(db, batch)


@app.post("/admin/photo-folders/{folder_id}/upload-batches", status_code=201)
def begin_restricted_folder_upload_batch(folder_id: UUID, request: Request,
                                         db: Session = Depends(db_session)) -> dict:
    tenant_id = directory_tenant_id(db, request)
    session = require_admin(request)
    require_same_origin(request)
    from app.photographer_onboarding import require_upload_ready
    require_upload_ready(db, tenant_id=tenant_id, admin_id=session.subject_id, require_credit=True)
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.tenant_id == tenant_id, PhotoFolder.id == folder_id,
        PhotoFolder.purpose == "content", PhotoFolder.audience_scope == "selected",
        PhotoFolder.derived_gallery_id.is_(None),
    ).with_for_update())
    if not folder or folder.status not in {"preparing", "released"}:
        raise HTTPException(status_code=404, detail="Pasta privada não encontrada ou indisponível.")
    require_parent_gallery_mutable(db, folder.parent_gallery_id, tenant_id=tenant_id)
    batch = create_folder_batch(db, folder, session.subject_id)
    audit(db, "private_folder_upload_batch.created", str(batch.id), tenant_id=tenant_id)
    db.commit()
    return batch_payload(db, batch)


@app.get("/admin/photo-folders/{folder_id}/upload-batches")
def list_restricted_folder_upload_batches(folder_id: UUID, request: Request,
                                          db: Session = Depends(db_session)) -> dict:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.tenant_id == tenant_id, PhotoFolder.id == folder_id,
        PhotoFolder.purpose == "content", PhotoFolder.audience_scope == "selected",
        PhotoFolder.derived_gallery_id.is_(None),
    ))
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta privada não encontrada.")
    batches = db.scalars(select(PrivateUploadBatch).where(
        PrivateUploadBatch.tenant_id == tenant_id,
        PrivateUploadBatch.folder_id == folder.id,
        PrivateUploadBatch.status == "open",
    ).order_by(PrivateUploadBatch.created_at))
    return {"batches": [batch_payload(db, batch) for batch in batches]}


@app.post("/admin/photo-folders/{folder_id}/upload-batches/{batch_id}/close")
def finish_restricted_folder_upload_batch(folder_id: UUID, batch_id: UUID, request: Request,
                                          db: Session = Depends(db_session)) -> dict:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    require_same_origin(request)
    try:
        batch = close_folder_batch(db, batch_id, folder_id, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit(db, "private_folder_upload_batch.closed", str(batch.id), tenant_id=tenant_id)
    db.commit()
    return batch_payload(db, batch)


@app.get("/admin/derived-galleries/{gallery_id}/folders")
def admin_private_gallery_folders(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id, allow_deleted_origin=True, tenant_id=tenant_id)
    folders = list(
        db.scalars(
            select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id)
            .where(
                PhotoFolder.derived_gallery_id == gallery.id,
                PhotoFolder.purpose == "content",
            )
            .order_by(PhotoFolder.position, PhotoFolder.created_at)
        )
    )
    counts = dict(
        db.execute(
            select(PhotoAsset.folder_id, func.count(PhotoAsset.id)).where(PhotoAsset.tenant_id == tenant_id)
            .where(PhotoAsset.derived_gallery_id == gallery.id)
            .group_by(PhotoAsset.folder_id)
        ).all()
    )
    return {
        "total": len(folders),
        "folders": [
            {
                "id": str(folder.id),
                "name": folder.name,
                "status": folder.status,
                "position": folder.position,
                "photo_count": counts.get(folder.id, 0),
                "released_at": folder.released_at.isoformat() if folder.released_at else None,
                "access_duration_days": folder.access_duration_days,
                "access_expires_at": folder.access_expires_at.isoformat()
                if folder.access_expires_at else None,
            }
            for folder in folders
        ],
    }


@app.post(
    "/admin/derived-galleries/{gallery_id}/folders",
    status_code=status.HTTP_201_CREATED,
)
def create_private_gallery_folder(
    gallery_id: UUID,
    payload: PhotoFolderInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    from app.tenant_closure import require_new_work
    require_new_work(db, tenant_id)
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id, allow_deleted_origin=True, tenant_id=tenant_id)
    last_position = db.scalar(
        select(func.max(PhotoFolder.position)).where(PhotoFolder.tenant_id == tenant_id).where(
            PhotoFolder.derived_gallery_id == gallery.id,
            PhotoFolder.purpose == "content",
        )
    )
    folder = PhotoFolder(
        parent_gallery_id=gallery.parent_gallery_id,
        derived_gallery_id=gallery.id,
        name=payload.name.strip(),
        access_duration_days=payload.access_duration_days,
        position=(last_position if last_position is not None else -1) + 1,
        purpose="content",
        tenant_id=tenant_id,
    )
    db.add(folder)
    db.flush()
    audit(db, "private_gallery.folder_created", str(folder.id), tenant_id=tenant_id)
    db.commit()
    return {
        "id": str(folder.id), "status": folder.status, "position": folder.position,
        "access_duration_days": folder.access_duration_days,
        "access_expires_at": folder.access_expires_at.isoformat()
        if folder.access_expires_at else None,
    }


@app.get("/admin/derived-galleries/{gallery_id}/photos")
def admin_private_gallery_photos(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    reference_rows = db.execute(
        select(DerivedGalleryPhoto, PhotoAsset, PhotoFolder).where(DerivedGalleryPhoto.tenant_id == tenant_id, PhotoAsset.tenant_id == tenant_id, PhotoFolder.tenant_id == tenant_id)
        .join(PhotoAsset, PhotoAsset.id == DerivedGalleryPhoto.photo_asset_id)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(DerivedGalleryPhoto.derived_gallery_id == gallery.id)
        .order_by(PhotoFolder.position, PhotoAsset.created_at, PhotoAsset.id)
    ).all()
    private_rows = db.execute(
        select(PhotoAsset, PhotoFolder).where(PhotoAsset.tenant_id == tenant_id, PhotoFolder.tenant_id == tenant_id)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(PhotoAsset.derived_gallery_id == gallery.id)
            .order_by(PhotoFolder.position, PhotoAsset.created_at, PhotoAsset.id)
    ).all()
    photo_ids = {
        photo.id for _reference, photo, _folder in reference_rows
    } | {photo.id for photo, _folder in private_rows}
    media_states = folder_media_states_by_id(
        db,
        folder_ids={folder.id for _reference, _photo, folder in reference_rows}
        | {folder.id for _photo, folder in private_rows},
        tenant_id=tenant_id,
    )
    favorites_by_photo: dict[UUID, list[dict[str, str]]] = defaultdict(list)
    comments_by_photo: dict[UUID, list[dict[str, str]]] = defaultdict(list)
    commercial_states_by_photo: dict[UUID, list[dict[str, str]]] = defaultdict(list)
    if photo_ids:
        favorite_rows = list(
            db.execute(
                select(PhotoFavorite.photo_asset_id, PhotoFavorite.client_id).where(PhotoFavorite.tenant_id == tenant_id)
                .where(
                    PhotoFavorite.derived_gallery_id == gallery.id,
                    PhotoFavorite.photo_asset_id.in_(photo_ids),
                )
                .order_by(PhotoFavorite.created_at, PhotoFavorite.id)
            )
        )
        comment_rows = list(
            db.execute(
                select(
                    PhotoComment.id,
                    PhotoComment.photo_asset_id,
                    PhotoComment.client_id,
                    PhotoComment.body,
                ).where(PhotoComment.tenant_id == tenant_id)
                .where(
                    PhotoComment.derived_gallery_id == gallery.id,
                    PhotoComment.photo_asset_id.in_(photo_ids),
                    PhotoComment.removed_at.is_(None),
                )
                .order_by(PhotoComment.created_at, PhotoComment.id)
            )
        )
        selection_rows = list(
            db.execute(
                select(PhotoSelection.photo_asset_id, PhotoSelection.client_id).where(PhotoSelection.tenant_id == tenant_id)
                .where(
                    PhotoSelection.derived_gallery_id == gallery.id,
                    PhotoSelection.photo_asset_id.in_(photo_ids),
                )
                .order_by(PhotoSelection.created_at, PhotoSelection.id)
            )
        )
        order_state_rows = list(
            db.execute(
                select(
                    SaleOrderItem.photo_asset_id_snapshot,
                    SaleOrder.client_id,
                    SaleOrder.payment_status,
                    SaleOrder.frozen_at,
                    PaymentCommunication.status,
                ).where(or_(PaymentCommunication.id.is_(None), PaymentCommunication.tenant_id == tenant_id), SaleOrder.tenant_id == tenant_id, SaleOrderItem.tenant_id == tenant_id)
                .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
                .outerjoin(
                    PaymentCommunication,
                    communication_join(),
                )
                .where(
                    SaleOrder.derived_gallery_id_snapshot == gallery.id,
                    SaleOrderItem.photo_asset_id_snapshot.in_(photo_ids),
                )
                .order_by(SaleOrder.created_at, SaleOrderItem.id)
            )
        )
        commercial_state_by_photo_client: dict[tuple[UUID, UUID], str] = {
            (photo_id, client_id): "selected" for photo_id, client_id in selection_rows
        }
        state_priority = {
            "selected": 1,
            "awaiting_payment": 2,
            "payment_reported": 3,
            "purchased": 4,
        }
        for photo_id, client_id, payment_status, frozen_at, communication_status in order_state_rows:
            if payment_status == "confirmed":
                state = "purchased"
            elif (
                payment_status == "pending"
                and frozen_at is not None
                and communication_status in {"pending_review", "confirmed"}
            ):
                state = "payment_reported"
            elif payment_status == "pending" and frozen_at is not None:
                state = "awaiting_payment"
            else:
                continue
            key = (photo_id, client_id)
            if state_priority[state] > state_priority.get(
                commercial_state_by_photo_client.get(key, ""), 0
            ):
                commercial_state_by_photo_client[key] = state
        interaction_client_ids = {
            client_id for _photo_id, client_id in favorite_rows
        } | {
            client_id for _comment_id, _photo_id, client_id, _body in comment_rows
        } | {client_id for _photo_id, client_id in commercial_state_by_photo_client}
        client_names = (
            dict(
                db.execute(
                    select(Client.id, Client.full_name).where(Client.tenant_id == tenant_id).where(Client.id.in_(interaction_client_ids))
                ).all()
            )
            if interaction_client_ids
            else {}
        )
        for photo_id, client_id in favorite_rows:
            favorites_by_photo[photo_id].append(
                {
                    "client_id": str(client_id),
                    "client_name": client_names.get(client_id, "Cliente"),
                }
            )
        for comment_id, photo_id, client_id, body in comment_rows:
            comments_by_photo[photo_id].append(
                {
                    "id": str(comment_id),
                    "client_id": str(client_id),
                    "client_name": client_names.get(client_id, "Cliente"),
                    "body": body,
                }
            )
        for (photo_id, client_id), state in commercial_state_by_photo_client.items():
            commercial_states_by_photo[photo_id].append(
                {
                    "client_id": str(client_id),
                    "client_name": client_names.get(client_id, "Cliente"),
                    "state": state,
                }
            )
    reference_ids = [reference.id for reference, _photo, _folder in reference_rows]
    origins_by_reference: dict[UUID, list[str]] = defaultdict(list)
    if reference_ids:
        for reference_id, origin in db.execute(
            select(
                DerivedGalleryPhotoOrigin.derived_gallery_photo_id,
                DerivedGalleryPhotoOrigin.origin,
            ).where(DerivedGalleryPhotoOrigin.tenant_id == tenant_id).where(
                DerivedGalleryPhotoOrigin.derived_gallery_photo_id.in_(reference_ids)
            )
        ):
            origins_by_reference[reference_id].append(origin)
    photos = [
        {
            "id": str(photo.id),
            "name": photo.display_name or photo.filename,
            "folder_id": str(folder.id),
            "folder_name": folder.name,
            "preview_url": f"/admin/photo-assets/{photo.id}/watermarked-preview"
            if media_states.get(folder.id) in {"available", "archiving"} else None,
            "media_state": media_states.get(folder.id, "unavailable"),
            "origins": sorted(origins_by_reference.get(reference.id) or [reference.origin]),
            "ownership": "public_reference",
            "favorited_by": favorites_by_photo[photo.id],
            "comments": comments_by_photo[photo.id],
            "commercial_states": commercial_states_by_photo[photo.id],
        }
        for reference, photo, folder in reference_rows
    ]
    photos.extend(
        {
            "id": str(photo.id),
            "name": photo.display_name or photo.filename,
            "folder_id": str(folder.id),
            "folder_name": folder.name,
            "preview_url": f"/admin/photo-assets/{photo.id}/watermarked-preview"
            if media_states.get(folder.id) in {"available", "archiving"} else None,
            "media_state": media_states.get(folder.id, "unavailable"),
            "origins": ["private_upload"],
            "ownership": "private",
            "favorited_by": favorites_by_photo[photo.id],
            "comments": comments_by_photo[photo.id],
            "commercial_states": commercial_states_by_photo[photo.id],
        }
        for photo, folder in private_rows
    )
    return {
        "gallery_id": str(gallery.id),
        "photos": photos,
    }


@app.post("/admin/derived-galleries/{gallery_id}/photos")
def add_admin_private_gallery_photos(
    gallery_id: UUID,
    payload: DerivedGalleryPhotosInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    require_admin(request)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "A inclusão administrativa de fotos existentes foi encerrada. Use uma pasta privada "
            "para carregar novos JPEGs do dispositivo."
        ),
    )


@app.delete("/admin/derived-galleries/{gallery_id}/photos/{photo_id}")
def remove_admin_private_gallery_photo(
    gallery_id: UUID,
    photo_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id, tenant_id=tenant_id)
    reference = db.scalar(
        select(DerivedGalleryPhoto).where(DerivedGalleryPhoto.tenant_id == tenant_id).where(
            DerivedGalleryPhoto.derived_gallery_id == gallery.id,
            DerivedGalleryPhoto.photo_asset_id == photo_id,
        )
    )
    if not reference:
        raise HTTPException(status_code=404, detail="Foto não pertence à galeria privada.")
    if db.scalar(
        select(PhotoSelection.id).where(PhotoSelection.tenant_id == tenant_id).where(
            PhotoSelection.derived_gallery_id == gallery.id,
            PhotoSelection.photo_asset_id == photo_id,
        )
    ) and not db.scalar(
        select(DerivedGalleryPhotoOrigin.id).where(DerivedGalleryPhotoOrigin.tenant_id == tenant_id).where(
            DerivedGalleryPhotoOrigin.derived_gallery_photo_id == reference.id,
            DerivedGalleryPhotoOrigin.origin == "client",
        )
    ):
        db.add(
            DerivedGalleryPhotoOrigin(
                derived_gallery_photo_id=reference.id,
                origin="client",
                tenant_id=tenant_id,
            )
        )
        db.flush()
    admin_origin = db.scalar(
        select(DerivedGalleryPhotoOrigin).where(DerivedGalleryPhotoOrigin.tenant_id == tenant_id).where(
            DerivedGalleryPhotoOrigin.derived_gallery_photo_id == reference.id,
            DerivedGalleryPhotoOrigin.origin == "admin",
        )
    )
    if admin_origin:
        db.delete(admin_origin)
        db.flush()
    remaining_origins = list(
        db.scalars(
            select(DerivedGalleryPhotoOrigin.origin).where(DerivedGalleryPhotoOrigin.tenant_id == tenant_id).where(
                DerivedGalleryPhotoOrigin.derived_gallery_photo_id == reference.id
            )
        )
    )
    reference_removed = False
    if not remaining_origins:
        db.delete(reference)
        reference_removed = True
    audit(db, "private_gallery.photo_admin_origin_removed", str(reference.id), tenant_id=tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    lock_removal_clients(db, gallery.parent_gallery_id, tenant_id=tenant_id)
    gallery = db.scalar(select(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id).where(DerivedGallery.id == gallery_id)
                        .execution_options(populate_existing=True))
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Galeria pública de origem não encontrada.")
    if parent.lifecycle_status == "deleting":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A Galeria pública está em exclusão. Aguarde a conclusão antes de excluir a privada.",
        )
    photos = list(db.scalars(select(PhotoAsset).where(
        PhotoAsset.tenant_id == tenant_id,
        PhotoAsset.derived_gallery_id == gallery.id,
    ).order_by(PhotoAsset.id).with_for_update()))
    _assert_photo_credit_operations_settled(
        db, tenant_id, [photo.id for photo in photos],
    )
    preserve_asset_history(db, gallery.parent_gallery_id, gallery_ids=[gallery.id], tenant_id=tenant_id)
    paths = historical_paths(db, gallery_ids=[gallery.id], tenant_id=tenant_id)
    for photo in photos:
        paths.extend(_delete_photo_records(db, photo, tenant_id=tenant_id))
    db.flush()
    delete_private_records(db, [gallery.id], tenant_id=tenant_id)
    cleanup = enqueue_file_cleanup(db, paths, tenant_id=tenant_id)
    audit(db, "derived_gallery.deleted", str(gallery.id), tenant_id=tenant_id)
    db.commit()
    process_file_cleanup(db, cleanup)
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"X-Asset-Cleanup": cleanup.status})



def gallery_operational_status(db: Session, gallery: DerivedGallery) -> dict[str, object]:
    selections = list(
        db.scalars(select(PhotoSelection).where(PhotoSelection.derived_gallery_id == gallery.id))
    )
    orders = list(db.scalars(select(SaleOrder).where(SaleOrder.derived_gallery_id == gallery.id)))
    referenced_photo_ids = select(DerivedGalleryPhoto.photo_asset_id).where(
        DerivedGalleryPhoto.tenant_id == gallery.tenant_id,
        DerivedGalleryPhoto.derived_gallery_id == gallery.id,
    )
    folder_ids = select(PhotoAsset.folder_id).where(
        PhotoAsset.tenant_id == gallery.tenant_id,
        (PhotoAsset.derived_gallery_id == gallery.id)
        | PhotoAsset.id.in_(referenced_photo_ids),
    )
    folders = list(db.scalars(select(PhotoFolder).where(
        PhotoFolder.tenant_id == gallery.tenant_id,
        PhotoFolder.id.in_(folder_ids),
        PhotoFolder.purpose == "content",
        PhotoFolder.status == "released",
    )))
    frozen = bool(folders) and all(
        not folder_media_is_local(db, folder)
        or (
            (deadline := folder_effective_expiry(
                db, folder, client_id=gallery.client_id
            )) is not None
            and expired(deadline)
        )
        for folder in folders
    )
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    normalized = normalize_e164(query) if query and query.startswith("+") else None
    galleries = list(db.scalars(select(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id).order_by(DerivedGallery.created_at.desc())))
    entries: list[dict[str, object]] = []
    for gallery in galleries:
        status_data = gallery_operational_status(db, gallery)
        if (tab == "frozen") != status_data["frozen"]:
            continue
        owner = owned_record(db, Client, gallery.client_id, tenant_id=tenant_id)
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
            select(DerivedGalleryPhoto.photo_asset_id).where(DerivedGalleryPhoto.tenant_id == tenant_id)
            .where(DerivedGalleryPhoto.derived_gallery_id == gallery.id)
            .limit(1)
        )
        cover_photo = owned_record(db, PhotoAsset, cover, tenant_id=tenant_id) if cover else None
        entries.append(
            {
                "id": str(gallery.id),
                "name": gallery.name,
                "parent_gallery_id": str(gallery.parent_gallery_id),
                "selection_expires_at": None,
                "cover_preview_url": (
                    f"/admin/photo-assets/{cover_photo.id}/preview"
                    if cover_photo and _admin_photo_preview_available(
                        db, cover_photo, allow_cover_thumbnail=True,
                    ) else None
                ),
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    status_data = gallery_operational_status(db, gallery)
    cover = db.scalar(
        select(DerivedGalleryPhoto.photo_asset_id).where(DerivedGalleryPhoto.tenant_id == tenant_id)
        .where(DerivedGalleryPhoto.derived_gallery_id == gallery.id)
        .limit(1)
    )
    cover_photo = owned_record(db, PhotoAsset, cover, tenant_id=tenant_id) if cover else None
    owner = owned_record(db, Client, gallery.client_id, tenant_id=tenant_id)
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Galeria pública não encontrada.")
    selected_count = (
        db.scalar(
            select(func.count())
            .select_from(PhotoSelection).where(PhotoSelection.tenant_id == tenant_id)
            .where(
                PhotoSelection.derived_gallery_id == gallery.id,
                PhotoSelection.client_id == gallery.client_id,
            )
        )
        or 0
    )
    orders = list(
        db.scalars(
            select(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(
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
        "selection_expires_at": None,
        "cover_preview_url": (
            f"/admin/photo-assets/{cover_photo.id}/preview"
            if cover_photo and _admin_photo_preview_available(
                db, cover_photo, allow_cover_thumbnail=True,
            ) else None
        ),
        "client": client_data,
        "responsible": client_data,
        "configuration_inherited": True,
        "inherited_folder_display_mode": parent.folder_display_mode,
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    gallery = require_derived_gallery_mutable(db, gallery_id, tenant_id=tenant_id)
    for field in payload.model_fields_set:
        setattr(gallery, field, getattr(payload, field))
    audit(db, "derived_gallery.updated", str(gallery.id), tenant_id=tenant_id)
    db.commit()
    return {"id": str(gallery.id)}


@app.post("/admin/derived-galleries/{gallery_id}/renew", deprecated=True)
def renew_gallery_selection(
    gallery_id: UUID,
    payload: GalleryRenewalInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    require_derived_gallery_mutable(db, gallery_id, tenant_id=tenant_id)
    raise HTTPException(
        status_code=410,
        detail="O prazo de acesso agora é configurado individualmente por pasta.",
    )


def _reopening_request_payload(
    db: Session,
    reopening: GalleryReopeningRequest,
    *,
    related_records: tuple[
        GalleryReopeningNotificationOutbox | None, PhotoFolder | None
    ] | None = None,
) -> dict[str, object]:
    if related_records is None:
        notification = db.scalar(
            select(GalleryReopeningNotificationOutbox).where(
                GalleryReopeningNotificationOutbox.tenant_id == reopening.tenant_id,
                GalleryReopeningNotificationOutbox.gallery_reopening_request_id == reopening.id
            )
        )
        folder = db.scalar(
            select(PhotoFolder).where(
                PhotoFolder.tenant_id == reopening.tenant_id,
                PhotoFolder.id == reopening.photo_folder_id,
            )
        ) if reopening.photo_folder_id else None
    else:
        notification, folder = related_records
    return {
        "id": str(reopening.id),
        "gallery_id": str(reopening.parent_gallery_id or reopening.derived_gallery_id),
        "folder_id": str(reopening.photo_folder_id) if reopening.photo_folder_id else None,
        "folder_name": folder.name if folder else None,
        "folder_access_scope": (
            "client"
            if folder and (
                folder.derived_gallery_id is not None
                or folder.audience_scope == "selected"
            )
            else "all"
            if folder
            else None
        ),
        "status": reopening.status,
        "requested_by_client_id": str(reopening.requested_by_client_id),
        "created_at": reopening.created_at.isoformat(),
        "decided_at": reopening.decided_at.isoformat() if reopening.decided_at else None,
        "approved_until": (
            reopening.approved_until.isoformat() if reopening.approved_until else None
        ),
        "approved_duration_days": reopening.approved_duration_days,
        "notification": {
            "id": str(notification.id) if notification else None,
            "status": notification.status if notification else "skipped",
            "attempts": notification.attempts if notification else 0,
            "can_retry": bool(notification and notification.status == "failed"),
        },
    }


@app.get("/admin/gallery-reopening-requests")
def list_gallery_reopening_requests(
    request: Request,
    status_filter: Literal["pending", "approved", "refused"] | None = Query(
        default=None, alias="status"
    ),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    query = select(GalleryReopeningRequest).where(GalleryReopeningRequest.tenant_id == tenant_id)
    if status_filter:
        query = query.where(GalleryReopeningRequest.status == status_filter)
    items = list(
        db.scalars(
            query.order_by(
                GalleryReopeningRequest.created_at.desc(),
                GalleryReopeningRequest.id.desc(),
            )
        )
    )
    related_records: dict[
        UUID,
        tuple[GalleryReopeningNotificationOutbox | None, PhotoFolder | None],
    ] = {}
    if items:
        request_ids = {item.id for item in items}
        notification_by_request = {
            item.gallery_reopening_request_id: item
            for item in db.scalars(
                select(GalleryReopeningNotificationOutbox).where(
                    GalleryReopeningNotificationOutbox.tenant_id == tenant_id,
                    GalleryReopeningNotificationOutbox.gallery_reopening_request_id.in_(request_ids),
                )
            )
        }
        folder_ids = {item.photo_folder_id for item in items if item.photo_folder_id}
        folder_by_id = {
            item.id: item
            for item in db.scalars(
                select(PhotoFolder).where(
                    PhotoFolder.tenant_id == tenant_id,
                    PhotoFolder.id.in_(folder_ids),
                )
            )
        } if folder_ids else {}
        related_records = {
            item.id: (
                notification_by_request.get(item.id),
                folder_by_id.get(item.photo_folder_id),
            )
            for item in items
        }
    requesters = {
        item.id: item.full_name
        for item in db.scalars(
            select(Client).where(
                Client.tenant_id == tenant_id,
                Client.id.in_({row.requested_by_client_id for row in items}),
            )
        )
    } if items else {}
    galleries = {
        gallery.id: gallery
        for gallery in db.scalars(
            select(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id).where(
                DerivedGallery.id.in_({item.derived_gallery_id for item in items})
            )
        )
    } if items else {}
    canonical_parents = {
        parent.id: parent for parent in db.scalars(select(ParentGallery).where(ParentGallery.tenant_id == tenant_id).where(
            ParentGallery.id.in_({item.parent_gallery_id for item in items if item.parent_gallery_id})
        ))
    } if items else {}
    return {
        "requests": [
            {
                **_reopening_request_payload(
                    db, item, related_records=related_records[item.id]
                ),
                "gallery_name": canonical_parents[item.parent_gallery_id].name
                if item.parent_gallery_id in canonical_parents
                else galleries[item.derived_gallery_id].name
                if item.derived_gallery_id in galleries else "Galeria removida",
                "requested_by_client_name": requesters.get(
                    item.requested_by_client_id, "Cliente indisponível"
                ),
            }
            for item in items
        ]
    }


@app.post("/admin/gallery-reopening-requests/{request_id}/decision")
def decide_gallery_reopening_request(
    request_id: UUID,
    payload: GalleryReopeningDecisionInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    session = current_session(request, Role.ADMIN)
    reopening = db.scalar(
        select(GalleryReopeningRequest).where(GalleryReopeningRequest.tenant_id == tenant_id)
        .where(GalleryReopeningRequest.id == request_id)
        .with_for_update()
    )
    if not reopening:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")
    if reopening.status != "pending":
        return _reopening_request_payload(db, reopening)
    reopened_folder = None
    if payload.decision == "approved" and reopening.photo_folder_id is None:
        raise HTTPException(
            status_code=409,
            detail="Esta solicitação antiga não identifica uma pasta. Peça uma nova solicitação para a pasta.",
        )
    if payload.decision == "approved":
        if reopening.photo_folder_id:
            folder = db.scalar(
                select(PhotoFolder).where(
                    PhotoFolder.tenant_id == tenant_id,
                    PhotoFolder.id == reopening.photo_folder_id,
                ).with_for_update()
            )
            if not folder or not folder_media_is_local(db, folder):
                raise HTTPException(
                    status_code=409,
                    detail="A mídia já está arquivada; use o fluxo de recuperação de arquivo frio.",
                )
            if not folder_reopening_allowed(
                db,
                folder,
                client_id=reopening.requested_by_client_id,
            ):
                raise HTTPException(
                    status_code=409,
                    detail="O prazo para aprovar a reabertura normal desta pasta terminou.",
                )
            if payload.access_duration_days is None:
                raise HTTPException(status_code=422, detail="Informe a duração em dias.")
            approved_at = now()
            reopened_folder = folder
            reopening.approved_duration_days = payload.access_duration_days
            reopening.approved_until = approved_at + timedelta(
                days=payload.access_duration_days
            )
        else:
            raise HTTPException(
                status_code=409,
                detail="Esta solicitação antiga não identifica uma pasta. Peça uma nova solicitação para a pasta.",
            )
    reopening.status = payload.decision
    reopening.decided_by_admin_id = session.subject_id
    reopening.decided_at = now()
    if payload.decision == "approved" and reopened_folder is not None:
        from app.folder_access import folder_archive_eligible_at
        from app.media_archive_notices import supersede_window_notices_for_folder

        current_deadline = folder_archive_eligible_at(db, reopened_folder)
        if current_deadline is not None:
            supersede_window_notices_for_folder(
                db,
                tenant_id=tenant_id,
                folder_id=reopened_folder.id,
                current_deadline=current_deadline,
                at=reopening.decided_at,
            )
    audit(db, f"gallery.reopening_{payload.decision}", str(reopening.id), tenant_id=tenant_id)
    db.commit()
    return _reopening_request_payload(db, reopening)


@app.post("/admin/gallery-reopening-notifications/{notification_id}/retry")
def retry_gallery_reopening_notification(
    notification_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    notification = db.scalar(
        select(GalleryReopeningNotificationOutbox)
        .where(GalleryReopeningNotificationOutbox.id == notification_id,
               GalleryReopeningNotificationOutbox.tenant_id == tenant_id)
        .with_for_update()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    if notification.status != "failed":
        raise HTTPException(status_code=409, detail="A notificação não pode ser reenfileirada.")
    notification.status = "queued"
    notification.last_error = None
    db.commit()
    return {"status": notification.status}




@app.get("/library")
def client_library(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, object]]]:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    registrations = list(
        db.scalars(
            select(ParentGalleryRegistration).where(ParentGalleryRegistration.tenant_id == tenant_id)
            .where(ParentGalleryRegistration.tenant_id == session.tenant_id, ParentGalleryRegistration.client_id == session.subject_id)
            .order_by(ParentGalleryRegistration.created_at.desc())
        )
    )
    registrations_by_parent = {
        registration.parent_gallery_id: registration for registration in registrations
    }
    membership_rows = list(
        db.execute(
            select(DerivedGallery, DerivedGalleryMembership.status).where(DerivedGallery.tenant_id == tenant_id, DerivedGalleryMembership.tenant_id == tenant_id)
            .join(
                DerivedGalleryMembership,
                DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id,
            )
            .where(
                DerivedGalleryMembership.tenant_id == session.tenant_id, DerivedGalleryMembership.client_id == session.subject_id,
                DerivedGalleryMembership.status.in_(("active", "blocked")),
            )
        )
    )
    any_membership = (
        select(DerivedGalleryMembership.id).where(DerivedGalleryMembership.tenant_id == tenant_id)
        .where(DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id)
        .exists()
    )
    membership_rows.extend(
        (gallery, "active")
        for gallery in db.scalars(
            select(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id).where(
                DerivedGallery.tenant_id == session.tenant_id, DerivedGallery.client_id == session.subject_id,
                ~any_membership,
            )
        )
    )
    membership_rows.sort(key=lambda row: row[0].created_at, reverse=True)
    gallery_ids = [gallery.id for gallery, _membership_status in membership_rows]
    parent_ids = {registration.parent_gallery_id for registration in registrations}
    parent_ids.update(gallery.parent_gallery_id for gallery, _status in membership_rows)
    parents_by_id = {
        parent.id: parent
        for parent in db.scalars(
            select(ParentGallery).where(ParentGallery.tenant_id == tenant_id).where(ParentGallery.tenant_id == session.tenant_id, ParentGallery.id.in_(parent_ids))
        )
    }
    canonical_states = {
        state.parent_gallery_id: state for state in db.scalars(
            select(GalleryClientState).where(GalleryClientState.tenant_id == tenant_id).where(
                GalleryClientState.tenant_id == session.tenant_id, GalleryClientState.client_id == session.subject_id,
                GalleryClientState.parent_gallery_id.in_(parent_ids),
            )
        )
    }
    public_rows: list[dict[str, object]] = []
    for registration in registrations:
        parent = parents_by_id.get(registration.parent_gallery_id)
        if not parent or not parent.active or parent.lifecycle_status != "active":
            continue
        state = canonical_states.get(parent.id)
        access_state = (
            "blocked" if state and state.status != "active"
            else "active" if registration.status == "active" else "pending_review"
        )
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

    folders_by_gallery: dict[UUID, list[PhotoFolder]] = defaultdict(list)
    if gallery_ids:
        for derived_gallery_id, folder in db.execute(
            select(DerivedGalleryPhoto.derived_gallery_id, PhotoFolder).where(DerivedGalleryPhoto.tenant_id == tenant_id, PhotoFolder.tenant_id == tenant_id)
            .join(PhotoAsset, PhotoAsset.id == DerivedGalleryPhoto.photo_asset_id)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                DerivedGalleryPhoto.tenant_id == session.tenant_id, DerivedGalleryPhoto.derived_gallery_id.in_(gallery_ids),
                PhotoFolder.tenant_id == session.tenant_id, PhotoAsset.tenant_id == session.tenant_id,
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
                folder_browsing_clause(session.subject_id),
            )
            .distinct()
            .order_by(
                DerivedGalleryPhoto.derived_gallery_id,
                PhotoFolder.position,
                PhotoFolder.created_at,
            )
        ):
            folders_by_gallery[derived_gallery_id].append(folder)

    public_folder_queries = [
        authorized_canonical_folders(parent_id, session.subject_id).with_only_columns(
            PhotoFolder.id.label("folder_id"),
            PhotoFolder.name.label("folder_name"),
            literal(parent_id).label("parent_gallery_id"),
        )
        for parent_id in {
            UUID(str(row["id"]))
            for row in public_rows
            if row["gallery_status"] == "active"
        }
    ]
    public_folder_names_by_parent: dict[UUID, dict[UUID, str]] = defaultdict(dict)
    if public_folder_queries:
        public_folder_statement = (
            union_all(*public_folder_queries)
            if len(public_folder_queries) > 1
            else public_folder_queries[0]
        )
        for folder_id, folder_name, parent_id in db.execute(public_folder_statement):
            public_folder_names_by_parent[parent_id][folder_id] = folder_name

    active_private_gallery_ids = {
        gallery.id
        for gallery, membership_status in membership_rows
        if membership_status == "active" and gallery.access_enabled
    }
    private_folder_names_by_gallery: dict[UUID, dict[UUID, str]] = defaultdict(dict)
    if active_private_gallery_ids:
        private_folder_rows = db.execute(
            select(
                DerivedGalleryPhoto.derived_gallery_id,
                PhotoFolder.id,
                PhotoFolder.name,
            )
            .join(PhotoAsset, PhotoAsset.id == DerivedGalleryPhoto.photo_asset_id)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                DerivedGalleryPhoto.tenant_id == tenant_id,
                DerivedGalleryPhoto.derived_gallery_id.in_(active_private_gallery_ids),
                PhotoAsset.tenant_id == tenant_id,
                PhotoFolder.tenant_id == tenant_id,
                PhotoFolder.parent_gallery_id == PhotoAsset.parent_gallery_id,
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
            )
            .distinct()
        )
        for gallery_id, folder_id, folder_name in private_folder_rows:
            private_folder_names_by_gallery[gallery_id][folder_id] = folder_name

    deadline_folder_ids = {
        folder_id
        for folder_names in (
            *public_folder_names_by_parent.values(),
            *private_folder_names_by_gallery.values(),
        )
        for folder_id in folder_names
    }
    effective_deadlines = folder_effective_expiries_by_id(
        db,
        folder_ids=deadline_folder_ids,
        tenant_id=tenant_id,
        client_id=session.subject_id,
    )

    def selection_deadline_payload(folder_names: dict[UUID, str]) -> list[dict[str, str]]:
        entries = [
            {
                "folder_id": str(folder_id),
                "folder_name": folder_name,
                "expires_at": expiry.isoformat(),
            }
            for folder_id, folder_name in folder_names.items()
            if (expiry := effective_deadlines.get(folder_id)) is not None
        ]
        return sorted(
            entries,
            key=lambda entry: (
                entry["expires_at"],
                entry["folder_name"].casefold(),
                entry["folder_id"],
            ),
        )

    for public_row in public_rows:
        parent_id = UUID(str(public_row["id"]))
        public_row["selection_deadlines"] = selection_deadline_payload(
            public_folder_names_by_parent.get(parent_id, {})
        )

    rows: list[dict[str, object]] = []
    galleries_by_id: dict[str, DerivedGallery] = {}
    for gallery, membership_status in membership_rows:
        parent = parents_by_id.get(gallery.parent_gallery_id)
        folders = folders_by_gallery[gallery.id]
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
            else "active"
        )
        private_row = {
            "id": str(gallery.id),
            "name": gallery.name,
            "message": (parent.sales_message or "") if parent else "",
            "selection_expires_at": None,
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
            "selection_deadlines": selection_deadline_payload(
                private_folder_names_by_gallery.get(gallery.id, {})
            ),
        }
        rows.append(private_row)
        galleries_by_id[str(gallery.id)] = gallery

    carts_by_gallery = client_carts_by_gallery_payload(
        db,
        galleries=[gallery for gallery, _membership_status in membership_rows],
        client_id=session.subject_id,
    )
    orders_by_gallery = client_orders_by_gallery_payload(
        db, gallery_ids=set(gallery_ids), client_id=session.subject_id
    )
    client = owned_record(db, Client, session.subject_id, tenant_id=tenant_id)
    canonical_cart_groups = {
        group["gallery_id"]: group for group in cart_payload(db, client)["groups"]
        if group["gallery_id"] == group["parent_gallery_id"]
    } if client else {}
    canonical_orders = list(db.scalars(select(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(
        SaleOrder.tenant_id == session.tenant_id, SaleOrder.client_id == session.subject_id,
        SaleOrder.parent_gallery_id_snapshot.in_(parent_ids),
        SaleOrder.derived_gallery_id_snapshot.is_(None),
        or_(SaleOrder.frozen_at.is_not(None), SaleOrder.payment_status == "confirmed"),
    ).order_by(SaleOrder.created_at.desc())))
    canonical_communications = communications_for_orders(db, canonical_orders)
    canonical_orders_by_parent: dict[UUID, list[dict[str, object]]] = defaultdict(list)
    for order in canonical_orders:
        communication = canonical_communications.get(order.id)
        canonical_orders_by_parent[order.parent_gallery_id_snapshot].append({
            "order_id": str(order.id),
            "commercial_state": "selection_finalized" if order.payment_status == "not_required"
            else "purchased" if order.payment_status == "confirmed"
            else "cancelled" if order.payment_status == "cancelled"
            else "payment_reported" if communication and communication.status == "pending_review"
            else "awaiting_payment",
            "total_cents": order.total_cents if order.payment_required_snapshot else None,
        })
    prepared_gallery_ids: set[UUID] = set()
    if gallery_ids:
        prepared_gallery_ids.update(
            derived_gallery_id
            for derived_gallery_id, origin in db.execute(
                select(DerivedGalleryPhoto.derived_gallery_id, DerivedGalleryPhoto.origin).where(DerivedGalleryPhoto.tenant_id == tenant_id).where(
                    DerivedGalleryPhoto.tenant_id == session.tenant_id, DerivedGalleryPhoto.derived_gallery_id.in_(gallery_ids),
                    DerivedGalleryPhoto.origin.in_(("admin", "facial")),
                )
            )
            if origin in ("admin", "facial")
        )
        prepared_gallery_ids.update(
            derived_gallery_id
            for derived_gallery_id, origin in db.execute(
                select(
                    DerivedGalleryPhoto.derived_gallery_id,
                    DerivedGalleryPhotoOrigin.origin,
                ).where(DerivedGalleryPhoto.tenant_id == tenant_id)
                .join(
                    DerivedGalleryPhotoOrigin,
                    DerivedGalleryPhotoOrigin.derived_gallery_photo_id
                    == DerivedGalleryPhoto.id,
                )
                .where(
                    DerivedGalleryPhoto.tenant_id == session.tenant_id, DerivedGalleryPhoto.derived_gallery_id.in_(gallery_ids),
                    DerivedGalleryPhotoOrigin.origin.in_(("admin", "facial")),
                )
            )
            if origin in ("admin", "facial")
        )

    public_by_parent = {str(row["id"]): row for row in public_rows}
    private_by_parent = {str(row["origin"]["id"]): row for row in rows}
    parent_order = list(public_by_parent)
    parent_order.extend(
        parent_id for parent_id in private_by_parent if parent_id not in public_by_parent
    )
    # Uma consulta para as capas configuradas, sem carregar fotos por card.
    ready_cover_parents = set(db.scalars(
        select(ParentGallery.id).where(ParentGallery.tenant_id == tenant_id)
        .join(PhotoAsset, PhotoAsset.id == ParentGallery.cover_photo_id)
        .join(MediaDerivative, MediaDerivative.photo_asset_id == PhotoAsset.id)
        .where(
            ParentGallery.tenant_id == session.tenant_id, ParentGallery.id.in_(parent_ids),
            PhotoAsset.parent_gallery_id == ParentGallery.id,
            MediaDerivative.variant == "admin_preview",
            MediaDerivative.status == "ready",
        )
    )) if parent_ids else set()
    local_cover_parents = _local_cover_thumbnail_parent_ids(
        db, tenant_id=tenant_id, parent_ids=set(parent_ids),
    )
    journeys: list[dict[str, object]] = []
    for parent_id in parent_order:
        public_row = public_by_parent.get(parent_id)
        private_row = private_by_parent.get(parent_id)
        private_gallery = (
            galleries_by_id.get(str(private_row["id"])) if private_row else None
        )
        private_status = str(private_row["gallery_status"]) if private_row else None
        membership_blocked = private_status == "blocked"
        public_url = (
            str(public_row["browse_url"])
            if public_row and public_row.get("browse_url") and not membership_blocked
            else None
        )
        private_url = (
            str(private_row["browse_url"])
            if private_row and private_row.get("browse_url")
            else None
        )
        primary_surface = "public" if public_url else "private" if private_url else "unavailable"
        primary_url = public_url or private_url
        cart = carts_by_gallery.get(
            private_gallery.id, {"quantity": 0, "items": []}
        ) if private_gallery else {"quantity": 0, "items": []}
        canonical_cart = canonical_cart_groups.get(parent_id)
        if canonical_cart:
            cart = canonical_cart
        gallery_orders = (
            orders_by_gallery.get(private_gallery.id, []) if private_gallery else []
        )
        gallery_orders = canonical_orders_by_parent.get(UUID(parent_id), []) + gallery_orders
        has_prepared_photos = bool(
            private_gallery and private_gallery.id in prepared_gallery_ids
        )
        parent = parents_by_id.get(UUID(parent_id))
        journey_status = (
            "blocked"
            if membership_blocked
            else str(public_row["gallery_status"])
            if public_url and public_row
            else private_status
            or (str(public_row["gallery_status"]) if public_row else "unavailable")
        )
        journeys.append(
            {
                "id": parent_id,
                "name": (
                    str(public_row["name"])
                    if public_row
                    else str(private_row["origin"]["name"])
                ),
                "event_name": parent.event_name if parent and parent.event_name else "",
                "status": journey_status,
                "primary_surface": primary_surface,
                "browse_url": primary_url,
                "cover_preview_url": (
                    f"{primary_url}/cover-preview"
                    if primary_url and parent and parent.id in ready_cover_parents
                    and parent.id in local_cover_parents
                    else None
                ),
                "public_gallery": public_row,
                "private_gallery": private_row,
                "selection_expires_at": None,
                "selection_deadlines": (
                    public_row.get("selection_deadlines", [])
                    if public_url and public_row
                    else private_row.get("selection_deadlines", [])
                    if private_url and private_row
                    else []
                ),
                "selection": cart,
                "orders": gallery_orders,
                "has_prepared_photos": has_prepared_photos,
                "actions": {
                    "continue_url": public_url,
                    "review_url": "/library/cart" if canonical_cart else (
                        private_url if int(cart.get("quantity", 0)) > 0 else None
                    ),
                    "orders_url": "/library/purchases" if canonical_orders_by_parent.get(UUID(parent_id)) else (
                        private_url if gallery_orders else None
                    ),
                    "prepared_url": private_url if has_prepared_photos else None,
                    "fallback_url": private_url if not public_url else None,
                },
            }
        )
    return {
        "journeys": journeys,
        "public_galleries": public_rows,
        "private_galleries": rows,
        "galleries": rows,
    }


def _commerce_client(request: Request, db: Session) -> Client:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    client = owned_record(db, Client, session.subject_id, tenant_id=tenant_id)
    if not client:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    return client


@app.get("/library/cart")
def unified_cart(request: Request, db: Session = Depends(db_session)) -> dict:
    client = _commerce_client(request, db)
    return cart_payload(db, client)


@app.post("/library/cart/prepare")
def prepare_unified_cart(request: Request, db: Session = Depends(db_session)) -> dict:
    client = _commerce_client(request, db)
    try:
        group = prepare_group(db, client)
        result = {**cart_payload(db, client), "payment": group_payload(group)}
        db.commit()
        return result
    except CheckoutError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


class ProviderCheckoutInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cart_revision: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    idempotency_key: UUID


class GroupPaymentInput(BaseModel):
    revision: str = Field(min_length=64, max_length=64)
    idempotency_key: str = Field(min_length=1, max_length=128)


@app.post("/library/cart/{gallery_id}/finalize")
def finalize_unified_selection(gallery_id: UUID, payload: GroupPaymentInput, request: Request,
                               db: Session = Depends(db_session)) -> dict:
    client = _commerce_client(request, db)
    try:
        order = finalize_selection(db, client, gallery_id, payload.revision, payload.idempotency_key)
        db.commit()
        return {"order_id": str(order.id), "status": "selection_finalized"}
    except CheckoutError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/library/payments/{group_id}/report")
def report_unified_payment(group_id: UUID, payload: GroupPaymentInput, request: Request,
                           db: Session = Depends(db_session)) -> dict:
    client = _commerce_client(request, db)
    try:
        communication = report_group(db, client, group_id, payload.revision, payload.idempotency_key)
        db.commit()
        return {"id": str(communication.id), "status": communication.status,
                "payment_group_id": str(group_id)}
    except CheckoutError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/library/cart/{gallery_id}")
def remove_unified_cart_group(gallery_id: UUID, request: Request,
                              db: Session = Depends(db_session)) -> dict:
    client = _commerce_client(request, db)
    tenant_id = client.tenant_id
    if db.scalar(select(GalleryClientState.id).where(GalleryClientState.tenant_id == tenant_id).where(
        GalleryClientState.parent_gallery_id == gallery_id,
        GalleryClientState.client_id == client.id,
    )):
        try:
            remove_canonical_cart_selection(
                db, parent_gallery_id=gallery_id, client_id=client.id
            )
        except CheckoutError as exc:
            db.rollback()
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        audit(db, "cart.group_removed", str(gallery_id), tenant_id=tenant_id)
        db.commit()
        return cart_payload(db, client)
    gallery = derived_gallery_for_client(db, gallery_id, client.id, tenant_id=client.tenant_id)
    lock_client_commerce(db, gallery_id=gallery.id, client_id=client.id)
    photo_ids = list(db.scalars(select(PhotoSelection.photo_asset_id).where(PhotoSelection.tenant_id == tenant_id).where(
        PhotoSelection.derived_gallery_id == gallery.id, PhotoSelection.client_id == client.id)))
    for photo_id in photo_ids:
        remove_client_selection_and_close_if_empty(db, gallery=gallery, client_id=client.id, photo_id=photo_id)
    audit(db, "cart.group_removed", str(gallery.id), tenant_id=tenant_id)
    db.commit()
    return cart_payload(db, client)


@app.delete("/library/cart/{gallery_id}/photos/{photo_id}")
def remove_unified_cart_photo(gallery_id: UUID, photo_id: UUID, request: Request,
                              db: Session = Depends(db_session)) -> dict:
    client = _commerce_client(request, db)
    tenant_id = client.tenant_id
    if db.scalar(select(GalleryClientState.id).where(GalleryClientState.tenant_id == tenant_id).where(
        GalleryClientState.parent_gallery_id == gallery_id,
        GalleryClientState.client_id == client.id,
    )):
        try:
            remove_canonical_cart_selection(
                db, parent_gallery_id=gallery_id, client_id=client.id,
                photo_id=photo_id,
            )
        except CheckoutError as exc:
            db.rollback()
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        audit(db, "cart.photo_removed", str(gallery_id), tenant_id=tenant_id)
        db.commit()
        return cart_payload(db, client)
    gallery = derived_gallery_for_client(db, gallery_id, client.id, tenant_id=client.tenant_id)
    lock_client_commerce(db, gallery_id=gallery.id, client_id=client.id)
    remove_client_selection_and_close_if_empty(db, gallery=gallery, client_id=client.id, photo_id=photo_id)
    audit(db, "cart.photo_removed", str(gallery.id), tenant_id=tenant_id)
    db.commit()
    return cart_payload(db, client)


@app.get("/library/purchases")
def client_purchase_history(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, object]]]:
    """Pedidos congelados da própria cliente, incluindo compras confirmadas."""
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    orders = list(
        db.scalars(
            select(SaleOrder).where(SaleOrder.tenant_id == tenant_id)
            .where(
                SaleOrder.client_id == session.subject_id,
                or_(
                    fulfillable_order_condition(),
                    SaleOrder.assets_removed_at.is_not(None),
                    SaleOrder.payment_group_id.in_(
                        select(PaymentCommunication.payment_group_id).where(PaymentCommunication.tenant_id == tenant_id).where(
                            PaymentCommunication.client_id == session.subject_id)),
                    SaleOrder.id.in_(
                        select(PaymentCommunication.sale_order_id).where(PaymentCommunication.tenant_id == tenant_id).where(
                            PaymentCommunication.client_id == session.subject_id
                        )
                    ),
                    SaleOrder.provider_payment_id.is_not(None),
                    SaleOrder.mercadopago_payment_id.is_not(None),
                ),
            )
            .order_by(SaleOrder.created_at.desc())
        )
    )
    mp_payments = mercadopago_for_orders(db, orders, tenant_id=tenant_id)
    order_ids = [order.id for order in orders]
    provider_payment_ids = {order.provider_payment_id for order in orders if order.provider_payment_id}
    provider_payments = {
        payment.id: payment for payment in db.scalars(select(ProviderPayment).where(
            ProviderPayment.tenant_id == tenant_id,
            ProviderPayment.client_id == session.subject_id,
            ProviderPayment.id.in_(provider_payment_ids),
        ))
    } if provider_payment_ids else {}
    recoveries = cart_recovery_statuses(
        db, tenant_id=tenant_id, payments=provider_payments.values()
    )
    orders = [
        order for order in orders
        if not recoveries.get(order.provider_payment_id, {}).get("historical_only")
    ]
    order_ids = [order.id for order in orders]
    item_rows = (
        list(
            db.scalars(
                select(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id)
                .where(SaleOrderItem.sale_order_id.in_(order_ids))
                .order_by(SaleOrderItem.filename_snapshot)
            )
        )
        if order_ids
        else []
    )
    items_by_order: dict[UUID, list[SaleOrderItem]] = defaultdict(list)
    for item in item_rows:
        items_by_order[item.sale_order_id].append(item)
    history_by_item = {
        historical.sale_order_item_id: historical
        for historical in db.scalars(
            select(CommercialHistoryMedia).where(CommercialHistoryMedia.tenant_id == tenant_id).where(
                CommercialHistoryMedia.sale_order_item_id.in_(
                    [item.id for item in item_rows]
                ),
                CommercialHistoryMedia.status == "ready",
            )
        )
    }
    communications_by_order = communications_for_orders(db, orders)
    operational_gallery_ids = {
        order.derived_gallery_id for order in orders if order.derived_gallery_id
    }
    operational_galleries = {
        gallery.id: gallery
        for gallery in db.scalars(
            select(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id).where(
                DerivedGallery.id.in_(operational_gallery_ids)
            )
        )
    }
    canonical_parent_ids = {
        order.parent_gallery_id for order in orders if order.parent_gallery_id
    }
    canonical_parents = {
        parent.id: parent for parent in db.scalars(
            select(ParentGallery).where(ParentGallery.tenant_id == tenant_id).where(ParentGallery.id.in_(canonical_parent_ids))
        )
    }
    media_state_by_folder = folder_media_states_by_id(
        db,
        folder_ids={item.folder_id_snapshot for item in item_rows if item.folder_id_snapshot},
        tenant_id=tenant_id,
    )
    result: list[dict[str, object]] = []
    for order in orders:
        gallery = operational_galleries.get(order.derived_gallery_id)
        canonical_parent = canonical_parents.get(order.parent_gallery_id)
        recovery = recoveries.get(order.provider_payment_id, {})
        item_payloads = []
        for item in items_by_order[order.id]:
            historical_media = history_by_item.get(item.id)
            if item.folder_id_snapshot is None:
                media_state = "available"  # itens antigos não têm escopo de pasta arquivável
            else:
                media_state = media_state_by_folder.get(item.folder_id_snapshot, "unavailable")
                if media_state == "unavailable":
                    media_state = "available"  # preserva o histórico de pastas removidas fora do arquivo frio
            media_visible = media_state in {"available", "archiving"}
            item_payloads.append(
                {
                    "item_id": str(item.id),
                    "photo_id": str(item.photo_asset_id_snapshot),
                    "name": item.filename_snapshot,
                    "media_state": media_state,
                    "preview_url": f"/library/history/items/{item.id}/preview"
                    if media_visible
                    and historical_media and historical_media.preview_storage_key
                    else (
                        f"/gallery/{order.derived_gallery_id}/photos/{item.photo_asset_id}/preview"
                        if media_visible
                        and order.derived_gallery_id and item.photo_asset_id
                        else f"/library/purchases/items/{item.id}/preview"
                        if media_visible
                        and canonical_parent and item.photo_asset_id and order_fulfillable(order)
                        else f"/public-galleries/{canonical_parent.id}/photos/{item.photo_asset_id}/preview"
                        if media_visible
                        and canonical_parent and item.photo_asset_id
                        else None
                    ),
                    "delivery_url": f"/library/history/items/{item.id}/delivery"
                    if media_visible
                    and historical_media and historical_media.delivery_storage_key
                    else None,
                    "delivery_reference_available": bool(
                        historical_media and historical_media.delivery_reference
                    ),
                }
            )
        has_cold_media = any(
            item["media_state"] not in {"available", "archiving"}
            for item in item_payloads
        )
        result.append(
            {
                "id": str(order.id),
                "payment_group_id": str(order.payment_group_id) if order.payment_group_id else None,
                "gallery_name": order.derived_gallery_name_snapshot or order.parent_gallery_name_snapshot,
                "parent_gallery_name": order.parent_gallery_name_snapshot,
                "gallery_status_label": "Galeria ativa" if gallery or canonical_parent else "Galeria removida",
                "gallery_removed": gallery is None and canonical_parent is None,
                "assets_removed": bool(order.assets_removed_at),
                "payment_status": order.payment_status,
                **({
                    "payment_method": provider_payments[order.provider_payment_id].capture_method or "credit_card",
                    "provider_payment_id": str(provider_payments[order.provider_payment_id].id),
                    "provider_payment_state": provider_payments[order.provider_payment_id].state,
                } if order.provider_payment_id in provider_payments else {}),
                **({
                    "provider_cart_reopened_at": recovery["reopened_at"],
                    "provider_requires_reconciliation": recovery["requires_reconciliation"],
                } if recovery.get("reopened_at") else {}),
                **mercadopago_fields(order, mp_payments),
                "commercial_state": (
                    "selection_finalized"
                    if order.payment_status == "not_required"
                    else "purchased"
                    if order.payment_status == "confirmed"
                    else "cancelled"
                    if order.payment_status == "cancelled"
                    else "payment_reported"
                    if communications_by_order.get(order.id)
                    and communications_by_order[order.id].status == "pending_review"
                    else "awaiting_payment"
                ),
                "communication_status": (
                    communications_by_order[order.id].status
                    if order.id in communications_by_order
                    else None
                ),
                "communicated_at": (
                    communications_by_order[order.id].created_at.isoformat()
                    if order.id in communications_by_order
                    else None
                ),
                "frozen_at": order.frozen_at.isoformat() if order.frozen_at else None,
                "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
                "total_cents": order.total_cents if order.payment_required_snapshot else None,
                **({"payment_required": False} if not order.payment_required_snapshot else {}),
                "delivery_album_url": (
                    order.delivery_album_url
                    if order_fulfillable(order) and not has_cold_media else None
                ),
                "items": item_payloads,
            }
        )
    groups = {}
    for order_payload in result:
        group_id = order_payload["payment_group_id"]
        if group_id:
            groups.setdefault(group_id, {"id": group_id, "orders": []})["orders"].append(order_payload)
    for group in groups.values():
        group["total_cents"] = sum(item["total_cents"] for item in group["orders"])
        group["commercial_state"] = group["orders"][0]["commercial_state"]
    card_groups: dict[str, dict[str, object]] = {}
    for order_payload in result:
        payment_id = order_payload.get("provider_payment_id")
        if not payment_id:
            continue
        group = card_groups.setdefault(str(payment_id), {
            "id": str(payment_id),
            "state": order_payload["provider_payment_state"],
            "capture_method": provider_payments[UUID(str(payment_id))].capture_method,
            "total_cents": 0,
            "orders": [],
        })
        recovery = recoveries.get(UUID(str(payment_id)), {})
        if recovery.get("reopened_at"):
            group["cart_reopened_at"] = recovery["reopened_at"]
            group["requires_reconciliation"] = recovery["requires_reconciliation"]
        group["orders"].append(order_payload)
        group["total_cents"] += order_payload["total_cents"]
    return {"orders": [item for item in result if not item["payment_group_id"]
                       and not item.get("provider_payment_id") and not item.get("mercadopago")],
            "payment_groups": list(groups.values()),
            **({"mercadopago_payment_groups": mercadopago_purchase_groups(result)}
               if any(item.get("mercadopago") for item in result) else {}),
            **({"provider_payment_groups": list(card_groups.values())} if card_groups else {}),
            "removed_movements": removed_movements_payload(db, tenant_id=tenant_id, client_id=session.subject_id)}


def _historical_item_for_client(
    db: Session, item_id: UUID, client_id: UUID
) -> tuple[SaleOrderItem, CommercialHistoryMedia]:
    tenant_id = client_tenant_id(db, client_id)
    item = db.scalar(
        select(SaleOrderItem)
        .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
        .where(
            SaleOrderItem.tenant_id == tenant_id,
            SaleOrder.tenant_id == tenant_id,
            SaleOrderItem.id == item_id,
            SaleOrder.client_id == client_id,
            fulfillable_order_condition(),
        )
    )
    if not item:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    historical_media = db.scalar(
        select(CommercialHistoryMedia).where(
            CommercialHistoryMedia.tenant_id == tenant_id,
            CommercialHistoryMedia.sale_order_item_id == item.id,
            CommercialHistoryMedia.status == "ready",
        )
    )
    if not historical_media:
        raise HTTPException(status_code=404, detail="Mídia histórica indisponível.")
    return item, historical_media


@app.get("/library/purchases/items/{item_id}/preview")
def client_purchased_photo_preview(
    item_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    """Preserva a prévia de uma compra confirmada após revogar a pasta da cliente."""
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    item = db.scalar(
        select(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id)
        .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
        .where(
            SaleOrderItem.id == item_id,
            SaleOrder.client_id == session.subject_id,
            fulfillable_order_condition(),
            SaleOrder.derived_gallery_id_snapshot.is_(None),
        )
    )
    if not item:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    if not item.photo_asset_id:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    order = owned_record(db, SaleOrder, item.sale_order_id, tenant_id=tenant_id)
    photo = owned_record(db, PhotoAsset, item.photo_asset_id, tenant_id=tenant_id)
    if (not order or not photo or item.photo_asset_id_snapshot != photo.id
            or photo.parent_gallery_id != order.parent_gallery_id_snapshot):
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    media_state = folder_media_state_by_id(
        db, folder_id=item.folder_id_snapshot or photo.folder_id, tenant_id=tenant_id,
    )
    if media_state not in {"available", "archiving"}:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    derivative = _client_preview_derivative(db, item.photo_asset_id, tenant_id=session.tenant_id)
    if not derivative or derivative.status != "ready":
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    try:
        path = presentation_path(db, derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Prévia indisponível.") from exc
    return protected_preview_response(path, f"compra-{item.id}.jpg")


@app.get("/library/history/items/{item_id}/preview")
def client_historical_preview(
    item_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    session = current_session(request, Role.CLIENT)
    item, historical_media = _historical_item_for_client(db, item_id, session.subject_id)
    media_state = historical_folder_media_state_by_id(
        db, folder_id=item.folder_id_snapshot, tenant_id=session.tenant_id,
    ) if item.folder_id_snapshot else "available"
    if media_state not in {"available", "archiving"}:
        raise HTTPException(status_code=404, detail="Mídia arquivada temporariamente indisponível.")
    if not historical_media.preview_storage_key:
        raise HTTPException(status_code=404, detail="Prévia histórica indisponível.")
    path = historical_media_path(historical_media.preview_storage_key, tenant_id=historical_media.tenant_id, item_id=historical_media.sale_order_item_id)
    return protected_preview_response(path, f"historico-{item.id}.jpg")


@app.get("/library/history/items/{item_id}/delivery")
def client_historical_delivery(
    item_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    session = current_session(request, Role.CLIENT)
    item, historical_media = _historical_item_for_client(db, item_id, session.subject_id)
    media_state = historical_folder_media_state_by_id(
        db, folder_id=item.folder_id_snapshot, tenant_id=session.tenant_id,
    ) if item.folder_id_snapshot else "available"
    if media_state not in {"available", "archiving"}:
        raise HTTPException(status_code=404, detail="Mídia arquivada temporariamente indisponível.")
    if not historical_media.delivery_storage_key:
        raise HTTPException(
            status_code=409,
            detail="A entrega está preservada por referência segura externa.",
        )
    path = historical_media_path(historical_media.delivery_storage_key, tenant_id=historical_media.tenant_id, item_id=historical_media.sale_order_item_id)
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
        gallery = derived_gallery_for_client(
            db, gallery_id, session.subject_id,
            require_access_enabled=False, allow_deleted_origin=True,
            tenant_id=session.tenant_id,
        )
        parent = None
        if gallery.access_enabled:
            try:
                parent = require_public_gallery_browsing(
                    db, parent_gallery_id=gallery.parent_gallery_id,
                    client_id=session.subject_id,
                )
            except PublicGalleryAccessDenied:
                pass
        if parent:
            destination = f"/public-galleries/{parent.id}"
            record_gallery_milestone(
                db, kind="first_access", parent_gallery_id=parent.id,
                client_id=session.subject_id, gallery=gallery,
            )
        else:
            destination = "/library/purchases"
        db.commit()
    return {"status": "authorized", "redirect_url": destination}


@app.get("/gallery/{gallery_id}/photos")
def gallery_photos(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, object]]]:
    """Lista somente os identificadores e nomes atribuídos à galeria privada."""
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    derived_gallery_for_client(db, gallery_id, session.subject_id, allow_deleted_origin=True, tenant_id=session.tenant_id)
    referenced_photo_ids = select(DerivedGalleryPhoto.photo_asset_id).where(DerivedGalleryPhoto.tenant_id == tenant_id).where(DerivedGalleryPhoto.tenant_id == session.tenant_id).where(
        DerivedGalleryPhoto.derived_gallery_id == gallery_id
    )
    photos = list(
        db.scalars(
            select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id).where(PhotoAsset.tenant_id == session.tenant_id)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                (PhotoAsset.derived_gallery_id == gallery_id)
                | (PhotoAsset.id.in_(referenced_photo_ids)),
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
                folder_browsing_clause(session.subject_id),
            )
            .distinct()
            .order_by(PhotoAsset.created_at, PhotoAsset.filename)
        )
    )
    derivatives = (
        {
            derivative.photo_asset_id: derivative
            for derivative in db.scalars(
                select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(MediaDerivative.tenant_id == session.tenant_id).where(
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
    tenant_id = session.tenant_id
    derived_gallery_for_client(db, gallery_id, session.subject_id, allow_deleted_origin=True, tenant_id=session.tenant_id)
    referenced_photo_ids = select(DerivedGalleryPhoto.photo_asset_id).where(DerivedGalleryPhoto.tenant_id == tenant_id).where(DerivedGalleryPhoto.tenant_id == session.tenant_id).where(
        DerivedGalleryPhoto.derived_gallery_id == gallery_id
    )
    folders = db.scalars(
        select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id).where(PhotoFolder.tenant_id == session.tenant_id)
        .join(PhotoAsset, PhotoAsset.folder_id == PhotoFolder.id)
        .where(
            (PhotoAsset.derived_gallery_id == gallery_id)
            | (PhotoAsset.id.in_(referenced_photo_ids)),
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
                select(func.count(func.distinct(PhotoAsset.id))).where(PhotoAsset.tenant_id == tenant_id).where(PhotoAsset.tenant_id == session.tenant_id)
                .select_from(PhotoAsset)
                .where(
                    (PhotoAsset.derived_gallery_id == gallery_id)
                    | (PhotoAsset.id.in_(referenced_photo_ids)),
                    PhotoAsset.folder_id == folder.id,
                )
            )
            or 0
        )
        rows.append(
            {
                **_folder_access_payload(
                    db, folder=folder, client_id=session.subject_id
                ),
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
    tenant_id = session.tenant_id
    gallery = derived_gallery_for_client(
        db, gallery_id, session.subject_id, allow_deleted_origin=True,
        tenant_id=session.tenant_id,
    )
    record_gallery_milestone(db, kind="first_access", parent_gallery_id=gallery.parent_gallery_id,
                             client_id=session.subject_id, gallery=gallery)
    db.commit()
    referenced_photo_ids = select(DerivedGalleryPhoto.photo_asset_id).where(DerivedGalleryPhoto.tenant_id == tenant_id).where(DerivedGalleryPhoto.tenant_id == session.tenant_id).where(
        DerivedGalleryPhoto.derived_gallery_id == gallery_id
    )
    photos = list(
        db.scalars(
            select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id).where(PhotoAsset.tenant_id == session.tenant_id)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                (PhotoAsset.derived_gallery_id == gallery_id)
                | (PhotoAsset.id.in_(referenced_photo_ids)),
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
                folder_browsing_clause(session.subject_id),
            )
            .distinct()
            .order_by(PhotoAsset.created_at, PhotoAsset.filename)
        )
    )
    photo_ids = {photo.id for photo in photos}
    commercial_states = client_photo_states(
        db,
        gallery_id=gallery.id,
        client_id=session.subject_id,
        photo_ids=photo_ids,
    )
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
    if not parent:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    cover = _gallery_cover_photo(db, parent)
    cover_ready = bool(cover and _cover_derivative(db, cover.id, tenant_id=session.tenant_id))
    selections = set(
        db.scalars(
            select(PhotoSelection.photo_asset_id).where(PhotoSelection.tenant_id == tenant_id).where(PhotoSelection.tenant_id == session.tenant_id).where(
                PhotoSelection.derived_gallery_id == gallery_id,
                PhotoSelection.client_id == session.subject_id,
            )
        )
    )
    favorites = set(
        db.scalars(
            select(PhotoFavorite.photo_asset_id).where(PhotoFavorite.tenant_id == tenant_id).where(PhotoFavorite.tenant_id == session.tenant_id).where(
                PhotoFavorite.derived_gallery_id == gallery_id,
                PhotoFavorite.client_id == session.subject_id,
            )
        )
    )
    viewed = set(
        db.scalars(
            select(PhotoView.photo_asset_id).where(PhotoView.tenant_id == tenant_id).where(PhotoView.tenant_id == session.tenant_id).where(
                PhotoView.derived_gallery_id == gallery_id,
                PhotoView.client_id == session.subject_id,
            )
        )
    )
    derivatives = (
        {
            derivative.photo_asset_id: derivative
            for derivative in db.scalars(
                select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(MediaDerivative.tenant_id == session.tenant_id).where(
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
            "selection_expires_at": None,
            "selection_open": True,
            "favorites_enabled": parent.favorites_enabled,
            "comments_enabled": parent.comments_enabled,
            "folder_display_mode": parent.folder_display_mode,
            "cover_title_font": normalize_title_font(parent.cover_title_font),
            "cover_title_color": parent.cover_title_color,
            "cover_title_size": parent.cover_title_size,
            "cover_title_position": parent.cover_title_position,
            "cover_preview_url": (
                f"/gallery/{gallery_id}/cover-preview"
                if cover_ready and cover and parent
                and _cover_thumbnail_is_local(db, parent, cover.id)
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
                "commercial_state": commercial_states[photo.id],
                "purchase_state": "já comprada"
                if commercial_states[photo.id] == "purchased"
                else "pagamento informado"
                if commercial_states[photo.id] == "payment_reported"
                else "aguardando pagamento"
                if commercial_states[photo.id] == "awaiting_payment"
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
    tenant_id = session.tenant_id
    gallery = derived_gallery_for_client(
        db, gallery_id, session.subject_id, allow_deleted_origin=True,
        tenant_id=session.tenant_id,
    )
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
    cover = _gallery_cover_photo(db, parent) if parent else None
    derivative = _cover_derivative(db, cover.id, tenant_id=session.tenant_id) if cover else None
    if not cover or not derivative or not parent or not _cover_thumbnail_is_local(
        db, parent, cover.id
    ):
        raise HTTPException(status_code=404, detail="Capa indisponível.")
    try:
        path = safe_derivative_path(derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Capa indisponível.") from exc
    audit(db, "media_preview.client_cover_viewed", str(gallery_id), tenant_id=session.tenant_id)
    db.commit()
    return protected_preview_response(path, f"capa-{gallery_id}.jpg")


def _client_photo_preview_is_available(
    db: Session,
    *,
    photo_id: UUID,
    folder: PhotoFolder,
    tenant_id: UUID,
    client_id: UUID,
    parent_gallery_id: UUID,
    derived_gallery_id: UUID | None,
) -> bool:
    """Preserva prévia pós-vencimento somente para seleção/pedido da própria cliente."""
    current = now()
    media_state = folder_media_state(db, folder)
    expiry = folder_effective_expiry(db, folder, client_id=client_id)
    if expiry is None or expiry > current:
        return folder_selected_media_preview_allowed(
            media_state=media_state,
            expiry=expiry,
            selected_at=None,
            at=current,
        )
    if media_state != "available":
        return False

    if derived_gallery_id is not None:
        selection_scope = and_(
            PhotoSelection.derived_gallery_id == derived_gallery_id,
            PhotoSelection.parent_gallery_id.is_(None),
        )
        order_scope = SaleOrder.derived_gallery_id_snapshot == derived_gallery_id
    else:
        selection_scope = and_(
            PhotoSelection.parent_gallery_id == parent_gallery_id,
            PhotoSelection.derived_gallery_id.is_(None),
        )
        order_scope = and_(
            SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
            SaleOrder.derived_gallery_id_snapshot.is_(None),
        )
    selection_created_at = db.scalar(
        select(PhotoSelection.created_at).where(
            PhotoSelection.tenant_id == tenant_id,
            PhotoSelection.client_id == client_id,
            PhotoSelection.photo_asset_id == photo_id,
            selection_scope,
        ).limit(1)
    )
    if folder_selected_media_preview_allowed(
        media_state=media_state,
        expiry=expiry,
        selected_at=selection_created_at,
        at=current,
    ):
        return True

    orders = db.scalars(
        select(SaleOrder)
        .join(
            SaleOrderItem,
            and_(
                SaleOrderItem.sale_order_id == SaleOrder.id,
                SaleOrderItem.tenant_id == SaleOrder.tenant_id,
            ),
        )
        .where(
            SaleOrder.tenant_id == tenant_id,
            SaleOrder.client_id == client_id,
            SaleOrderItem.tenant_id == tenant_id,
            SaleOrderItem.photo_asset_id_snapshot == photo_id,
            SaleOrder.assets_removed_at.is_(None),
            order_scope,
        )
        .order_by(SaleOrder.created_at.desc())
    )
    for order in orders:
        order_open = (
            order.payment_status == "pending" and order.frozen_at is not None
        ) or (order_fulfillable(order) and order.delivery_album_url is None)
        if folder_selected_media_preview_allowed(
            media_state=media_state,
            expiry=expiry,
            selected_at=selection_created_at,
            existing_order_created_at=order.created_at,
            existing_order_open=order_open,
            at=current,
        ):
            return True
    return False


@app.get("/gallery/{gallery_id}/photos/{photo_id}/preview")
def client_photo_preview(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    """Entrega somente o derivado com marca à cliente autorizada na galeria privada."""
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    gallery = derived_gallery_for_client(
        db, gallery_id, session.subject_id, allow_deleted_origin=True,
        tenant_id=session.tenant_id,
    )
    assigned_photo_for_gallery(
        db, gallery_id, photo_id, tenant_id=session.tenant_id,
        client_id=session.subject_id, allow_expired=True,
    )
    photo_folder = db.execute(
        select(PhotoAsset, PhotoFolder)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(
            PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.id == photo_id,
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.status == "released",
            PhotoFolder.purpose == "content",
        )
    ).first()
    if not photo_folder or not _client_photo_preview_is_available(
        db,
        photo_id=photo_id,
        folder=photo_folder[1],
        tenant_id=tenant_id,
        client_id=session.subject_id,
        parent_gallery_id=gallery.parent_gallery_id,
        derived_gallery_id=gallery.id,
    ):
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    derivative = db.scalar(
        select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(MediaDerivative.tenant_id == session.tenant_id).where(
            MediaDerivative.photo_asset_id == photo_id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
    )
    if not derivative:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    try:
        path = presentation_path(db, derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Prévia indisponível.") from exc
    viewed = db.scalar(
        select(PhotoView).where(PhotoView.tenant_id == tenant_id).where(PhotoView.tenant_id == session.tenant_id).where(
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
                derived_gallery_id=gallery_id, client_id=session.subject_id, photo_asset_id=photo_id,
                tenant_id=session.tenant_id,
            )
        )
    audit(db, "media_preview.client_viewed", str(gallery_id), tenant_id=session.tenant_id)
    db.commit()
    return protected_preview_response(path, f"previa-{photo_id}.jpg")


@app.post("/gallery/{gallery_id}/photos/{photo_id}/selection", status_code=status.HTTP_201_CREATED)
def select_photo(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id, tenant_id=session.tenant_id)
    assigned_photo_for_gallery(
        db, gallery_id, photo_id, tenant_id=session.tenant_id, client_id=session.subject_id
    )
    private_photo = db.scalar(
        select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id).where(
            PhotoAsset.id == photo_id,
            PhotoAsset.derived_gallery_id == gallery.id,
        )
    )
    if private_photo:
        lock_client_commerce(
            db, gallery_id=gallery.id, client_id=session.subject_id
        )
        if client_photo_is_frozen(
            db,
            gallery_id=gallery.id,
            client_id=session.subject_id,
            photo_id=photo_id,
        ):
            raise HTTPException(
                status_code=409, detail="Foto indisponível para seleção."
            )
        selection = db.scalar(
            select(PhotoSelection).where(PhotoSelection.tenant_id == tenant_id).where(
                PhotoSelection.derived_gallery_id == gallery.id,
                PhotoSelection.client_id == session.subject_id,
                PhotoSelection.photo_asset_id == photo_id,
            )
        )
        if not selection:
            try:
                with notification_savepoint(db):
                    db.add(PhotoSelection(derived_gallery_id=gallery.id,
                                          client_id=session.subject_id, photo_asset_id=photo_id, tenant_id=tenant_id))
                    db.flush()
            except IntegrityError:
                if not db.scalar(select(PhotoSelection.id).where(PhotoSelection.tenant_id == tenant_id).where(
                    PhotoSelection.derived_gallery_id == gallery.id,
                    PhotoSelection.client_id == session.subject_id,
                    PhotoSelection.photo_asset_id == photo_id,
                )):
                    raise
                return {"status": "selected"}
            audit(db, "photo_selection.created", str(gallery_id), tenant_id=tenant_id)
            db.flush()
            synchronize_editable_draft(
                db, gallery=gallery, client_id=session.subject_id
            )
            record_gallery_milestone(db, kind="first_selection",
                                     parent_gallery_id=gallery.parent_gallery_id,
                                     client_id=session.subject_id, gallery=gallery)
            db.commit()
        return {"status": "selected"}
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
        audit(db, "photo_selection.created", str(gallery_id), tenant_id=tenant_id)
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
        result = select_canonical_photo(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
            photo_id=photo_id,
        )
    except CanonicalSelectionUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result.selection_created:
        audit(db, "photo_selection.created_from_public_gallery", str(parent_gallery_id), tenant_id=session.tenant_id)
        record_gallery_milestone(
            db, kind="first_selection", parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    db.commit()
    return {
        "status": "selected",
        "private_gallery_id": None,
        "gallery_created": result.state_created,
        "reference_created": False,
        "selection_created": result.selection_created,
        "selection_expires_at": None,
        "cart": _canonical_cart_payload(db, parent_gallery_id, session.subject_id),
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
    tenant_id = session.tenant_id
    try:
        require_public_gallery_browsing(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    canonical_selection = db.scalar(select(PhotoSelection.id).where(PhotoSelection.tenant_id == tenant_id).where(
        PhotoSelection.parent_gallery_id == parent_gallery_id,
        PhotoSelection.client_id == session.subject_id,
        PhotoSelection.photo_asset_id == photo_id,
    ))
    if canonical_selection:
        if not authorized_canonical_photo(
            db, parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id, photo_id=photo_id,
            include_expired=True, include_unavailable=True,
        ):
            raise HTTPException(status_code=404, detail="Foto indisponível.")
        try:
            remove_canonical_cart_selection(
                db, parent_gallery_id=parent_gallery_id,
                client_id=session.subject_id, photo_id=photo_id,
            )
        except CheckoutError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        audit(db, "photo_selection.removed_from_public_gallery", str(parent_gallery_id), tenant_id=tenant_id)
        db.commit()
        return {
            "status": "unselected", "private_gallery_id": None,
            "gallery_closed": False,
            "cart": _canonical_cart_payload(db, parent_gallery_id, session.subject_id),
        }
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
    assigned_photo_for_gallery(
        db,
        gallery.id,
        photo_id,
        tenant_id=tenant_id,
        client_id=session.subject_id,
        allow_expired=True,
    )
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
        audit(db, "photo_selection.removed_from_public_gallery", str(gallery.id), tenant_id=tenant_id)
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
    capability = resolve_gallery_capability(db, payload.access_token, tenant_id=session.tenant_id)
    if not capability or capability.tenant_id != session.tenant_id:
        audit(db, "public_gallery.capability_rejected", "invalid", tenant_id=session.tenant_id)
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
        audit(db, "public_gallery.access_denied", str(capability.parent_gallery_id), tenant_id=session.tenant_id)
        db.commit()
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    audit(db, "public_gallery.accessed", str(result.parent.id), tenant_id=session.tenant_id)
    if result.state == "authorized":
        record_gallery_milestone(db, kind="first_access", parent_gallery_id=result.parent.id,
                                 client_id=session.subject_id)
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
    record_gallery_milestone(db, kind="first_access", parent_gallery_id=parent.id,
                             client_id=session.subject_id)
    db.commit()
    private_gallery = _operational_gallery_for_public_client(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=session.subject_id,
    )
    published_terms = db.scalar(select(PhotographerTermsVersion).order_by(
        PhotographerTermsVersion.version_number.desc(),
    ).limit(1))
    return {
        "id": str(parent.id),
        "name": parent.name,
        "event_name": parent.event_name,
        "description": parent.description,
        "access_mode": parent.access_mode,
        "favorites_enabled": parent.favorites_enabled,
        "comments_enabled": parent.comments_enabled,
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
        "private_gallery_id": str(private_gallery.id) if private_gallery else None,
        "selection_expires_at": None,
        "support_contact_email": published_terms.provider_contact_email if published_terms else None,
    }


@app.get("/public-galleries/{parent_gallery_id}/facial-search")
def public_gallery_facial_search_availability(
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
    try:
        settings = facial_settings_from_environment(verify_runtime_assets=False)
    except FacialConfigurationError:
        return {
            "state": "unavailable",
            "manual_selection_available": True,
            "minor_search_available": False,
        }
    try:
        availability = search_availability(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
            settings=settings,
        )
    except FacialSearchError as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    # Contexto opaco de retomada, sem autoridade de acesso ou dados pessoais.
    availability["storage_context"] = sha256(
        f"facial-storage/v2:{session.tenant_id}:{session.subject_id}:{session.id}".encode()
    ).hexdigest()
    return availability


@app.get("/public-galleries/{parent_gallery_id}/photos/{photo_id}/face-regions")
def public_photo_face_regions(parent_gallery_id: UUID, photo_id: UUID, request: Request,
                              db: Session = Depends(db_session)):
    from app.facial.config import _integer
    from app.facial.regions import photo_regions
    session = current_session(request, Role.CLIENT)
    try:
        settings = facial_settings_from_environment(verify_runtime_assets=False)
        regions = photo_regions(db, gallery_id=parent_gallery_id, client_id=session.subject_id,
                                photo_id=photo_id, settings=settings)
        return {"regions": regions, "auto_threshold": _integer("FACIAL_OVERLAY_AUTO_THRESHOLD", 4, minimum=0, maximum=20)}
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    except FacialConfigurationError:
        return {"regions": [], "auto_threshold": 4}


class FaceRegionSearchInput(BaseModel):
    model_config = {"extra": "forbid"}
    face_region_id: UUID
    # Compatibilidade de transporte; não são registrados como novo consentimento.
    consent_version: str | None = Field(default=None, max_length=120)
    subject_declaration: Literal["adult", "minor", "conditional"] | None = None
    representation_reference: str | None = Field(default=None, max_length=200)


@app.post("/public-galleries/{parent_gallery_id}/face-region-searches", status_code=202)
def public_face_region_search(parent_gallery_id: UUID, payload: FaceRegionSearchInput,
                              request: Request, db: Session = Depends(db_session)):
    require_same_origin(request)
    session = current_session(request, Role.CLIENT)
    try:
        require_public_gallery_browsing(db, parent_gallery_id=parent_gallery_id, client_id=session.subject_id)
        enforce_facial_search_rate_limit(db, client_id=session.subject_id, parent_gallery_id=parent_gallery_id,
                                        ip_address=request.client.host if request.client else "unknown")
        settings = facial_settings_from_environment(verify_runtime_assets=False)
        item = create_search_request(db, parent_gallery_id=parent_gallery_id, client_id=session.subject_id,
            consent_version=payload.consent_version, subject_declaration=payload.subject_declaration,
            representation_reference=payload.representation_reference, payload=b"", settings=settings,
            reference_region_id=payload.face_region_id)
        db.commit()
        return search_request_payload(item)
    except PublicGalleryAccessDenied as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    except FacialSearchCapacityError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc), headers={"Retry-After": str(exc.retry_after_seconds)}) from exc
    except (FacialConfigurationError, FacialSearchError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post(
    "/public-galleries/{parent_gallery_id}/facial-searches",
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_public_gallery_facial_search(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_same_origin(request)
    session = current_session(request, Role.CLIENT)
    try:
        require_public_gallery_browsing(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    if not (request.headers.get("content-type") or "").lower().startswith(
        "image/jpeg"
    ):
        raise HTTPException(status_code=415, detail="Envie uma imagem JPEG.")
    enforce_facial_search_rate_limit(
        db,
        client_id=session.subject_id,
        parent_gallery_id=parent_gallery_id,
        ip_address=request.client.host if request.client else "unknown",
    )
    consent_version = request.headers.get("x-facial-consent-version", "").strip()
    upload_attempt = request.headers.get("x-facial-upload-attempt")
    try:
        upload_request_id = UUID(upload_attempt) if upload_attempt else None
        if upload_request_id is not None and upload_request_id.version != 4:
            raise ValueError("UUID v4 required")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Identificador de tentativa inválido.") from exc
    subject_declaration = request.headers.get(
        "x-facial-subject-declaration", ""
    ).strip()
    representation_reference = request.headers.get(
        "x-facial-representation-reference"
    )
    try:
        settings = facial_settings_from_environment(verify_runtime_assets=False)
        payload = await read_bounded_body(
            request,
            max_bytes=settings.max_reference_bytes,
            error_detail="A imagem de referência excede o limite permitido.",
        )
        item = create_search_request(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
            consent_version=consent_version,
            subject_declaration=subject_declaration,
            representation_reference=representation_reference,
            payload=payload,
            settings=settings,
            consent_accepted=request.headers.get("x-facial-consent-accepted") == "true",
            request_id=upload_request_id,
        )
        db.commit()
        FACIAL_ADMISSION_COUNTER.record("accepted")
    except FacialSearchCapacityError as exc:
        db.rollback()
        FACIAL_ADMISSION_COUNTER.record("refused")
        raise HTTPException(
            status_code=503,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except (FacialConfigurationError, FacialSearchError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FacialReferenceError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return search_request_payload(item)


@app.get(
    "/public-galleries/{parent_gallery_id}/facial-searches/latest"
)
def latest_public_gallery_facial_search_result(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    try:
        item, candidates = read_latest_search_result(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    except FacialSearchError as exc:
        raise HTTPException(status_code=404, detail="Consulta facial indisponível.") from exc
    return search_result_payload(item, candidates)


@app.get(
    "/public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}"
)
def public_gallery_facial_search_result(
    parent_gallery_id: UUID,
    search_request_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    try:
        item, candidates = read_search_result(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
            request_id=search_request_id,
        )
    except FacialSearchError as exc:
        raise HTTPException(status_code=404, detail="Consulta facial indisponível.") from exc
    return search_result_payload(item, candidates)


@app.delete(
    "/public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}"
)
def cancel_public_gallery_facial_search(
    parent_gallery_id: UUID,
    search_request_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_same_origin(request)
    session = current_session(request, Role.CLIENT)
    try:
        item = cancel_search_request(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
            request_id=search_request_id,
            settings=facial_settings_from_environment(verify_runtime_assets=False),
        )
        db.commit()
    except (FacialConfigurationError, FacialReferenceError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Consulta facial indisponível.") from exc
    except FacialSearchError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Consulta facial indisponível.") from exc
    return search_request_payload(item)


@app.delete(
    "/public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}"
    "/candidates/{photo_id}"
)
def reject_public_gallery_facial_candidate(
    parent_gallery_id: UUID,
    search_request_id: UUID,
    photo_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, bool]:
    require_same_origin(request)
    session = current_session(request, Role.CLIENT)
    try:
        reject_search_candidate(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
            request_id=search_request_id,
            photo_id=photo_id,
        )
        db.commit()
    except FacialSearchError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Resultado facial indisponível.") from exc
    return {"rejected": True}


@app.post(
    "/public-galleries/{parent_gallery_id}/facial-searches/{search_request_id}"
    "/candidates/{photo_id}/selection",
    status_code=status.HTTP_201_CREATED,
)
def select_public_gallery_facial_candidate(
    parent_gallery_id: UUID,
    search_request_id: UUID,
    photo_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    require_same_origin(request)
    session = current_session(request, Role.CLIENT)
    try:
        authorize_search_candidate_selection(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
            request_id=search_request_id,
            photo_id=photo_id,
        )
        result = select_canonical_photo(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
            photo_id=photo_id,
        )
    except FacialSearchError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Resultado facial indisponível.") from exc
    except CanonicalSelectionUnavailable as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result.selection_created:
        audit(db, "photo_selection.created_from_facial_filter", str(parent_gallery_id))
        record_gallery_milestone(
            db, kind="first_selection", parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    db.commit()
    return {
        "status": "selected",
        "private_gallery_id": None,
        "gallery_created": result.state_created,
        "reference_created": False,
        "selection_created": result.selection_created,
        "selection_expires_at": None,
        "cart": _canonical_cart_payload(db, parent_gallery_id, session.subject_id),
    }


@app.get("/public-galleries/{parent_gallery_id}/photos")
def public_gallery_photos(
    parent_gallery_id: UUID,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
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
    canonical_selections = set(db.scalars(select(PhotoSelection.photo_asset_id).where(PhotoSelection.tenant_id == tenant_id).where(PhotoSelection.tenant_id == session.tenant_id).where(
        PhotoSelection.parent_gallery_id == parent_gallery_id,
        PhotoSelection.client_id == session.subject_id,
    )))
    selections = canonical_selections | (
        set(
            db.scalars(
                select(PhotoSelection.photo_asset_id).where(PhotoSelection.tenant_id == tenant_id).where(PhotoSelection.tenant_id == session.tenant_id).where(
                    PhotoSelection.derived_gallery_id == gallery.id,
                    PhotoSelection.client_id == session.subject_id,
                )
            )
        )
        if gallery
        else set()
    )
    canonical_favorites = set(db.scalars(select(PhotoFavorite.photo_asset_id).where(PhotoFavorite.tenant_id == tenant_id).where(PhotoFavorite.tenant_id == session.tenant_id).where(
        PhotoFavorite.parent_gallery_id == parent_gallery_id,
        PhotoFavorite.client_id == session.subject_id,
    )))
    favorites = canonical_favorites | (
        set(
            db.scalars(
                select(PhotoFavorite.photo_asset_id).where(PhotoFavorite.tenant_id == tenant_id).where(PhotoFavorite.tenant_id == session.tenant_id).where(
                    PhotoFavorite.derived_gallery_id == gallery.id,
                    PhotoFavorite.client_id == session.subject_id,
                )
            )
        )
        if gallery
        else set()
    )
    photos = list(
        db.scalars(
            authorized_canonical_photos(parent_gallery_id, session.subject_id)
            .order_by(PhotoFolder.position, PhotoAsset.created_at, PhotoAsset.filename)
        )
    )
    commercial_states = client_photo_states(
        db, gallery_id=gallery.id if gallery else None,
        parent_gallery_id=parent_gallery_id,
        client_id=session.subject_id,
        photo_ids={photo.id for photo in photos},
    )
    derivatives = (
        {
            derivative.photo_asset_id: derivative
            for derivative in db.scalars(
                select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(MediaDerivative.tenant_id == session.tenant_id).where(
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
            select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id).where(PhotoFolder.tenant_id == session.tenant_id).where(
                PhotoFolder.id.in_({photo.folder_id for photo in photos}),
                PhotoFolder.purpose == "content",
            )
        )
    } if photos else {}
    visible_folders = list(
        db.scalars(
            authorized_canonical_folders(parent_gallery_id, session.subject_id)
            .order_by(PhotoFolder.position, PhotoFolder.created_at, PhotoFolder.id)
        )
    )
    folder_counts = dict(db.execute(
        select(PhotoAsset.folder_id, func.count(PhotoAsset.id))
        .where(
            PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.folder_id.in_({folder.id for folder in visible_folders}),
        )
        .group_by(PhotoAsset.folder_id)
    ).all()) if visible_folders else {}
    folder_summaries = [
        {
            **_folder_access_payload(
                db, folder=folder, client_id=session.subject_id
            ),
            "photo_count": folder_counts.get(folder.id, 0),
        }
        for folder in visible_folders
    ]
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
                "favorited": photo.id in favorites,
                "commercial_state": commercial_states[photo.id],
            }
            for photo in photos
        ],
        "folders": folder_summaries,
        "private_gallery_id": str(gallery.id) if gallery else None,
        "cart": _canonical_cart_payload(db, parent_gallery_id, session.subject_id)
        if canonical_selections else (
            _client_cart_payload(db, gallery, session.subject_id)
            if gallery else {"quantity": 0, "items": []}
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
    derivative = _cover_derivative(db, cover.id, tenant_id=session.tenant_id) if cover else None
    if not cover or not derivative or not _cover_thumbnail_is_local(
        db, parent, cover.id
    ):
        raise HTTPException(status_code=404, detail="Capa indisponível.")
    try:
        path = safe_derivative_path(derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Capa indisponível.") from exc
    audit(db, "media_preview.public_gallery_cover_viewed", str(parent_gallery_id), tenant_id=session.tenant_id)
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
    tenant_id = session.tenant_id
    try:
        require_public_gallery_browsing(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    photo = authorized_canonical_photo(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=session.subject_id,
        photo_id=photo_id,
        include_expired=True,
    )
    if not photo:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    folder = db.get(PhotoFolder, photo.folder_id) if photo.folder_id else None
    if (
        not folder
        or folder.tenant_id != tenant_id
        or not _client_photo_preview_is_available(
            db,
            photo_id=photo.id,
            folder=folder,
            tenant_id=tenant_id,
            client_id=session.subject_id,
            parent_gallery_id=parent_gallery_id,
            derived_gallery_id=None,
        )
    ):
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    derivative = db.scalar(
        select(MediaDerivative).where(MediaDerivative.tenant_id == tenant_id).where(MediaDerivative.tenant_id == session.tenant_id).where(
            MediaDerivative.photo_asset_id == photo.id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
    )
    if not derivative:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    try:
        path = presentation_path(db, derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Prévia indisponível.") from exc
    audit(db, "media_preview.public_gallery_viewed", str(parent_gallery_id), tenant_id=session.tenant_id)
    db.commit()
    return protected_preview_response(path, f"previa-{photo.id}.jpg")


def _canonical_photo_interaction_context(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID, photo_id: UUID
) -> tuple[ParentGallery, PhotoAsset]:
    try:
        return require_authorized_canonical_photo(
            db, parent_gallery_id=parent_gallery_id, client_id=client_id, photo_id=photo_id
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    except CanonicalPhotoAccessDenied as exc:
        raise HTTPException(status_code=404, detail="Foto indisponível.") from exc


@app.post(
    "/public-galleries/{parent_gallery_id}/photos/{photo_id}/favorite",
    status_code=status.HTTP_201_CREATED,
)
def favorite_canonical_photo(
    parent_gallery_id: UUID, photo_id: UUID, request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    parent, _photo = _canonical_photo_interaction_context(
        db, parent_gallery_id=parent_gallery_id, client_id=session.subject_id, photo_id=photo_id
    )
    if not parent.favorites_enabled:
        raise HTTPException(status_code=403, detail="Favoritos não estão habilitados nesta galeria.")
    existing = db.scalar(select(PhotoFavorite.id).where(PhotoFavorite.tenant_id == tenant_id).where(
        PhotoFavorite.parent_gallery_id == parent_gallery_id,
        PhotoFavorite.photo_asset_id == photo_id,
        PhotoFavorite.client_id == session.subject_id,
    ))
    if not existing:
        db.add(PhotoFavorite(
            parent_gallery_id=parent_gallery_id,
            photo_asset_id=photo_id,
            client_id=session.subject_id,
            tenant_id=tenant_id,
        ))
        audit(db, "photo_favorite.created", str(parent_gallery_id), tenant_id=tenant_id)
        db.commit()
    return {"status": "favorited"}


@app.delete(
    "/public-galleries/{parent_gallery_id}/photos/{photo_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unfavorite_canonical_photo(
    parent_gallery_id: UUID, photo_id: UUID, request: Request,
    db: Session = Depends(db_session),
) -> Response:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    _canonical_photo_interaction_context(
        db, parent_gallery_id=parent_gallery_id, client_id=session.subject_id, photo_id=photo_id
    )
    favorite = db.scalar(select(PhotoFavorite).where(PhotoFavorite.tenant_id == tenant_id).where(
        PhotoFavorite.parent_gallery_id == parent_gallery_id,
        PhotoFavorite.photo_asset_id == photo_id,
        PhotoFavorite.client_id == session.subject_id,
    ))
    if favorite:
        db.delete(favorite)
        audit(db, "photo_favorite.removed", str(parent_gallery_id), tenant_id=tenant_id)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/public-galleries/{parent_gallery_id}/photos/{photo_id}/view")
def record_canonical_photo_view(
    parent_gallery_id: UUID, photo_id: UUID, request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    _canonical_photo_interaction_context(
        db, parent_gallery_id=parent_gallery_id, client_id=session.subject_id, photo_id=photo_id
    )
    view = db.scalar(select(PhotoView).where(PhotoView.tenant_id == tenant_id).where(
        PhotoView.parent_gallery_id == parent_gallery_id,
        PhotoView.client_id == session.subject_id,
        PhotoView.photo_asset_id == photo_id,
    ))
    if view:
        view.last_viewed_at = now()
    else:
        db.add(PhotoView(
            parent_gallery_id=parent_gallery_id,
            client_id=session.subject_id,
            photo_asset_id=photo_id,
            tenant_id=tenant_id,
        ))
    db.commit()
    return {"status": "viewed"}


@app.post(
    "/public-galleries/{parent_gallery_id}/photos/{photo_id}/comments",
    status_code=status.HTTP_201_CREATED,
)
def create_canonical_photo_comment(
    parent_gallery_id: UUID, photo_id: UUID, payload: PhotoCommentInput,
    request: Request, db: Session = Depends(db_session),
) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    parent, _photo = _canonical_photo_interaction_context(
        db, parent_gallery_id=parent_gallery_id, client_id=session.subject_id, photo_id=photo_id
    )
    if not parent.comments_enabled:
        raise HTTPException(status_code=403, detail="Comentários não estão habilitados nesta galeria.")
    comment = PhotoComment(
        parent_gallery_id=parent_gallery_id,
        photo_asset_id=photo_id,
        client_id=session.subject_id,
        body=payload.body.strip(),
        tenant_id=tenant_id,
    )
    db.add(comment)
    db.flush()
    audit(db, "photo_comment.created", str(comment.id), tenant_id=tenant_id)
    db.commit()
    return {"id": str(comment.id)}


@app.get("/public-galleries/{parent_gallery_id}/comments")
def canonical_client_comments(
    parent_gallery_id: UUID, request: Request,
    db: Session = Depends(db_session),
) -> dict[str, list[dict[str, str]]]:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    try:
        require_public_gallery_browsing(
            db, parent_gallery_id=parent_gallery_id, client_id=session.subject_id
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    allowed = authorized_canonical_photos(
        parent_gallery_id, session.subject_id
    ).with_only_columns(PhotoAsset.id)
    comments = db.scalars(select(PhotoComment).where(PhotoComment.tenant_id == tenant_id).where(
        PhotoComment.parent_gallery_id == parent_gallery_id,
        PhotoComment.client_id == session.subject_id,
        PhotoComment.photo_asset_id.in_(allowed),
        PhotoComment.removed_at.is_(None),
    ).order_by(PhotoComment.created_at.asc()))
    return {"comments": [
        {"id": str(comment.id), "photo_id": str(comment.photo_asset_id), "body": comment.body}
        for comment in comments
    ]}


@app.delete(
    "/public-galleries/{parent_gallery_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_canonical_comment(
    parent_gallery_id: UUID, comment_id: UUID, request: Request,
    db: Session = Depends(db_session),
) -> Response:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    comment = db.scalar(select(PhotoComment).where(PhotoComment.tenant_id == tenant_id).where(
        PhotoComment.id == comment_id,
        PhotoComment.parent_gallery_id == parent_gallery_id,
        PhotoComment.client_id == session.subject_id,
        PhotoComment.removed_at.is_(None),
    ))
    if not comment:
        raise HTTPException(status_code=404, detail="Comentário não encontrado.")
    _canonical_photo_interaction_context(
        db, parent_gallery_id=parent_gallery_id, client_id=session.subject_id,
        photo_id=comment.photo_asset_id,
    )
    comment.removed_at = now()
    audit(db, "photo_comment.removed_by_client", str(comment.id), tenant_id=tenant_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete(
    "/gallery/{gallery_id}/photos/{photo_id}/selection", status_code=status.HTTP_204_NO_CONTENT
)
def unselect_photo(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id, tenant_id=session.tenant_id)
    assigned_photo_for_gallery(
        db,
        gallery.id,
        photo_id,
        tenant_id=tenant_id,
        client_id=session.subject_id,
        allow_expired=True,
    )
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
        audit(db, "photo_selection.removed", str(gallery_id), tenant_id=tenant_id)
        if result.gallery_closed:
            audit(db, "derived_gallery.closed_without_references", str(gallery_id), tenant_id=tenant_id)
        db.commit()
    headers: dict[str, str] = {}
    if result.gallery_closed:
        headers["X-Markina-Gallery-Closed"] = "true"
        parent = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
        registration = db.scalar(
            select(ParentGalleryRegistration).where(ParentGalleryRegistration.tenant_id == tenant_id).where(
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
    return client_carts_by_gallery_payload(
        db, galleries=[gallery], client_id=client_id
    )[gallery.id]


def _canonical_cart_payload(
    db: Session, parent_gallery_id: UUID, client_id: UUID
) -> dict[str, object]:
    client = db.get(Client, client_id)
    if not client:
        return {"quantity": 0, "items": []}
    return next((group for group in cart_payload(db, client)["groups"]
                 if group["gallery_id"] == str(parent_gallery_id)),
                {"quantity": 0, "items": []})


@app.get("/gallery/{gallery_id}/cart")
def client_cart(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Carrinho privado calculado no servidor para a cliente autorizada."""
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(
        db, gallery_id, session.subject_id, allow_deleted_origin=True,
        tenant_id=session.tenant_id,
    )
    return _client_cart_payload(db, gallery, session.subject_id)


def _client_folder_for_reopening(
    db: Session,
    *,
    folder_id: UUID,
    client_id: UUID,
    parent_gallery_id: UUID,
    derived_gallery_id: UUID | None = None,
) -> PhotoFolder | None:
    if derived_gallery_id:
        private_folder = db.scalar(
            select(PhotoFolder).where(
                PhotoFolder.tenant_id == client_tenant_id(db, client_id),
                PhotoFolder.id == folder_id,
                PhotoFolder.parent_gallery_id == parent_gallery_id,
                PhotoFolder.derived_gallery_id == derived_gallery_id,
                PhotoFolder.status == "released",
                PhotoFolder.purpose == "content",
            )
        )
        if private_folder:
            return private_folder
    return db.scalar(
        authorized_canonical_folders(parent_gallery_id, client_id).where(
            PhotoFolder.id == folder_id
        )
    )


def _latest_folder_reopening_request(
    db: Session, *, tenant_id: UUID, folder_id: UUID, client_id: UUID
) -> GalleryReopeningRequest | None:
    return db.scalar(
        select(GalleryReopeningRequest)
        .where(
            GalleryReopeningRequest.tenant_id == tenant_id,
            GalleryReopeningRequest.photo_folder_id == folder_id,
            GalleryReopeningRequest.requested_by_client_id == client_id,
        )
        .order_by(
            GalleryReopeningRequest.created_at.desc(),
            GalleryReopeningRequest.id.desc(),
        )
    )


def _folder_access_payload(
    db: Session, *, folder: PhotoFolder, client_id: UUID
) -> dict[str, object]:
    expiry = folder_effective_expiry(db, folder, client_id=client_id)
    media_state = folder_media_state(db, folder)
    media_local = media_state in {"available", "archiving"}
    access_open = media_local and (expiry is None or not expired(expiry))
    reopening = _latest_folder_reopening_request(
        db,
        tenant_id=folder.tenant_id,
        folder_id=folder.id,
        client_id=client_id,
    )
    return {
        "id": str(folder.id),
        "name": folder.name,
        "position": folder.position,
        "audience_scope": folder.audience_scope or "all",
        "access_duration_days": folder.access_duration_days,
        "access_expires_at": expiry.isoformat() if expiry else None,
        "access_open": access_open,
        "media_state": media_state,
        "can_request_reopening": folder_reopening_allowed(
            db, folder, client_id=client_id
        ),
        "reopening_request": (
            _reopening_request_payload(db, reopening) if reopening else None
        ),
    }


def _create_folder_reopening_request(
    db: Session,
    *,
    folder: PhotoFolder,
    client_id: UUID,
    idempotency_key: str,
) -> GalleryReopeningRequest:
    tenant_id = folder.tenant_id
    existing = db.scalar(
        select(GalleryReopeningRequest)
        .where(
            GalleryReopeningRequest.tenant_id == tenant_id,
            GalleryReopeningRequest.photo_folder_id == folder.id,
            GalleryReopeningRequest.requested_by_client_id == client_id,
            or_(
                GalleryReopeningRequest.idempotency_key == idempotency_key,
                GalleryReopeningRequest.status == "pending",
            ),
        )
        .order_by(GalleryReopeningRequest.created_at.desc())
    )
    if existing:
        return existing
    if not folder_reopening_allowed(db, folder, client_id=client_id):
        raise HTTPException(
            status_code=409,
            detail="O prazo para solicitar a reabertura normal desta pasta terminou.",
        )

    if folder.derived_gallery_id is None:
        state = db.scalar(
            select(GalleryClientState)
            .where(
                GalleryClientState.tenant_id == tenant_id,
                GalleryClientState.parent_gallery_id == folder.parent_gallery_id,
                GalleryClientState.client_id == client_id,
            )
            .with_for_update()
        )
        if state and state.status != "active":
            raise HTTPException(status_code=403, detail="Acesso não autorizado.")
        if not state:
            state = GalleryClientState(
                tenant_id=tenant_id,
                parent_gallery_id=folder.parent_gallery_id,
                client_id=client_id,
                status="active",
            )
            db.add(state)
            db.flush()

    reopening = GalleryReopeningRequest(
        tenant_id=tenant_id,
        parent_gallery_id=folder.parent_gallery_id if folder.derived_gallery_id is None else None,
        derived_gallery_id=folder.derived_gallery_id,
        photo_folder_id=folder.id,
        requested_by_client_id=client_id,
        idempotency_key=idempotency_key,
    )
    db.add(reopening)
    db.flush()
    photographer_phone = legacy_owned_photographer_phone(db, tenant_id=tenant_id)
    db.add(GalleryReopeningNotificationOutbox(
        tenant_id=tenant_id,
        gallery_reopening_request_id=reopening.id,
        recipient_phone=photographer_phone,
        status="queued" if photographer_phone else "skipped",
    ))
    audit(db, "gallery.folder_reopening_requested", str(reopening.id), tenant_id=tenant_id)
    return reopening


@app.get("/gallery/{gallery_id}/reopening-requests")
def client_gallery_reopening_request(
    gallery_id: UUID,
    request: Request,
    folder_id: UUID = Query(...),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(
        db, gallery_id, session.subject_id, allow_deleted_origin=True,
        tenant_id=session.tenant_id,
    )
    folder = _client_folder_for_reopening(
        db,
        folder_id=folder_id,
        client_id=session.subject_id,
        parent_gallery_id=gallery.parent_gallery_id,
        derived_gallery_id=gallery.id,
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta indisponível.")
    reopening = _latest_folder_reopening_request(
        db, tenant_id=session.tenant_id, folder_id=folder.id, client_id=session.subject_id
    )
    return {"request": _reopening_request_payload(db, reopening) if reopening else None}


@app.post(
    "/gallery/{gallery_id}/reopening-requests",
    status_code=status.HTTP_201_CREATED,
)
def request_gallery_reopening(
    gallery_id: UUID,
    payload: GalleryReopeningRequestInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(
        db, gallery_id, session.subject_id, allow_deleted_origin=True,
        tenant_id=session.tenant_id,
    )
    folder = _client_folder_for_reopening(
        db,
        folder_id=payload.folder_id,
        client_id=session.subject_id,
        parent_gallery_id=gallery.parent_gallery_id,
        derived_gallery_id=gallery.id,
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta indisponível.")
    reopening = _create_folder_reopening_request(
        db,
        folder=folder,
        client_id=session.subject_id,
        idempotency_key=payload.idempotency_key,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        reopening = _latest_folder_reopening_request(
            db, tenant_id=session.tenant_id, folder_id=folder.id, client_id=session.subject_id
        )
        if not reopening:
            raise
    return _reopening_request_payload(db, reopening)


@app.get("/public-galleries/{parent_gallery_id}/reopening-requests")
def canonical_gallery_reopening_request(
    parent_gallery_id: UUID,
    request: Request,
    folder_id: UUID = Query(...),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    try:
        require_public_gallery_browsing(
            db, parent_gallery_id=parent_gallery_id, client_id=session.subject_id
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    folder = db.scalar(
        authorized_canonical_folders(parent_gallery_id, session.subject_id).where(
            PhotoFolder.id == folder_id
        )
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta indisponível.")
    reopening = _latest_folder_reopening_request(
        db, tenant_id=session.tenant_id, folder_id=folder.id, client_id=session.subject_id
    )
    return {"request": _reopening_request_payload(db, reopening) if reopening else None}


@app.post(
    "/public-galleries/{parent_gallery_id}/reopening-requests",
    status_code=status.HTTP_201_CREATED,
)
def request_canonical_gallery_reopening(
    parent_gallery_id: UUID,
    payload: GalleryReopeningRequestInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    try:
        require_public_gallery_browsing(
            db, parent_gallery_id=parent_gallery_id, client_id=session.subject_id
        )
    except PublicGalleryAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Acesso não autorizado.") from exc
    folder = db.scalar(
        authorized_canonical_folders(parent_gallery_id, session.subject_id).where(
            PhotoFolder.id == payload.folder_id
        )
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta indisponível.")
    reopening = _create_folder_reopening_request(
        db,
        folder=folder,
        client_id=session.subject_id,
        idempotency_key=payload.idempotency_key,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        reopening = _latest_folder_reopening_request(
            db, tenant_id=session.tenant_id, folder_id=folder.id, client_id=session.subject_id
        )
        if not reopening:
            raise
    return _reopening_request_payload(db, reopening)


@app.post("/gallery/{gallery_id}/checkout", status_code=status.HTTP_201_CREATED)
def checkout_gallery(
    gallery_id: UUID, payload: CheckoutInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id, tenant_id=session.tenant_id)
    client = owned_record(db, Client, session.subject_id, tenant_id=tenant_id)
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
    tenant_id = session.tenant_id
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id, tenant_id=session.tenant_id)
    order = db.scalar(
        select(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(
            SaleOrder.id == order_id,
            SaleOrder.derived_gallery_id == gallery_id,
            SaleOrder.client_id == session.subject_id,
        )
    )
    if not order or order.payment_status != "pending":
        raise HTTPException(status_code=403, detail="Acesso negado.")
    existing = db.scalar(
        select(PaymentCommunication).where(PaymentCommunication.tenant_id == tenant_id)
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
    client = owned_record(db, Client, session.subject_id, tenant_id=tenant_id)
    if not client:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    try:
        order = freeze_pending_checkout(
            db, gallery=gallery, client=client, order=order
        )
    except CheckoutError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    existing = db.scalar(
        select(PaymentCommunication).where(PaymentCommunication.tenant_id == tenant_id)
        .where(
            PaymentCommunication.sale_order_id == order.id,
            PaymentCommunication.status == "pending_review",
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
        tenant_id=tenant_id,
    )
    db.add(communication)
    db.flush()
    notification_state = "configuration_required"
    photographer_phone = legacy_owned_photographer_phone(db, tenant_id=tenant_id)
    if photographer_phone:
        notification_state = "queued"
    else:
        audit(db, "payment.notification_configuration_required", str(communication.id), tenant_id=tenant_id)
    record_payment_event(db, communication=communication, order=order, event_type="payment_reported")
    audit(db, "payment.communication_reported", str(order.id), tenant_id=tenant_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(PaymentCommunication).where(PaymentCommunication.tenant_id == tenant_id).where(
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
    tenant_id = directory_tenant_id(db, request)
    session = current_session(request, Role.ADMIN)
    try:
        communication, payment_group, scope_orders = lock_payment_scope(
            db, communication_id, payload.payment_group_id, tenant_id=tenant_id)
    except CheckoutError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if communication.status != "pending_review":
        return {"status": communication.status}
    order = owned_record(db, SaleOrder, communication.sale_order_id, tenant_id=tenant_id)
    if not order or order.payment_status != "pending":
        raise HTTPException(status_code=409, detail="Pedido indisponível para decisão.")
    communication.status = payload.decision
    communication.decided_by_admin_id = session.subject_id
    communication.decided_at = now()
    if any(item.payment_status != "pending" for item in scope_orders):
        raise HTTPException(status_code=409, detail="Pedidos indisponíveis para decisão.")
    for item in scope_orders:
        item.payment_status = "confirmed" if payload.decision == "confirmed" else "cancelled"
        item.confirmed_at = communication.decided_at if payload.decision == "confirmed" else None
    if payment_group:
        payment_group.state = payload.decision
    client = owned_record(db, Client, communication.client_id, tenant_id=tenant_id)
    if client and client.id == order.client_id:
        decision_revision = (
            db.scalar(
                select(func.count(PaymentConfirmationCorrection.id)).where(PaymentConfirmationCorrection.tenant_id == tenant_id).where(
                    PaymentConfirmationCorrection.payment_communication_id == communication.id
                )
            )
            or 0
        )
        event = record_payment_event(db, communication=communication, order=order,
                                     event_type=f"payment_{payload.decision}",
                                     decision_revision=decision_revision)
        if event:
            order.payment_message_snapshot = event.whatsapp_body
    audit(db, f"payment.communication_{payload.decision}", str(communication.id), tenant_id=tenant_id)
    db.commit()
    return {"status": communication.status}


@app.post("/admin/payment-communications/{communication_id}/correction")
def correct_payment_confirmation(
    communication_id: UUID,
    payload: PaymentCorrectionInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    tenant_id = directory_tenant_id(db, request)
    session = current_session(request, Role.ADMIN)
    try:
        communication, payment_group, scope_orders = lock_payment_scope(
            db, communication_id, payload.payment_group_id, tenant_id=tenant_id)
    except CheckoutError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    existing = db.scalar(
        select(PaymentConfirmationCorrection).where(PaymentConfirmationCorrection.tenant_id == tenant_id).where(
            PaymentConfirmationCorrection.payment_communication_id == communication_id,
            PaymentConfirmationCorrection.idempotency_key == payload.idempotency_key,
        )
    )
    if existing:
        communication = owned_record(db, PaymentCommunication, communication_id, tenant_id=tenant_id)
        return {
            "id": str(existing.id),
            "status": communication.status if communication else "pending_review",
        }
    communication = db.scalar(
        select(PaymentCommunication).where(PaymentCommunication.tenant_id == tenant_id)
        .where(PaymentCommunication.id == communication_id)
        .with_for_update()
    )
    if not communication:
        raise HTTPException(status_code=404, detail="Comunicação não encontrada.")
    order = db.scalar(
        select(SaleOrder).where(SaleOrder.tenant_id == tenant_id)
        .where(SaleOrder.id == communication.sale_order_id)
        .with_for_update()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if communication.status == "pending_review" and order.payment_status == "pending":
        previous = db.scalar(
            select(PaymentConfirmationCorrection).where(PaymentConfirmationCorrection.tenant_id == tenant_id)
            .where(
                PaymentConfirmationCorrection.payment_communication_id == communication.id
            )
            .order_by(PaymentConfirmationCorrection.created_at.desc())
        )
        if previous:
            return {"id": str(previous.id), "status": communication.status}
    expected_payment_status = {"confirmed": "confirmed", "refused": "cancelled"}.get(
        communication.status
    )
    if expected_payment_status is None or order.payment_status != expected_payment_status:
        raise HTTPException(
            status_code=409,
            detail="Somente um pagamento confirmado ou não localizado pode ser corrigido.",
        )
    if any(item.payment_status != expected_payment_status for item in scope_orders):
        raise HTTPException(status_code=409, detail="Pedidos indisponíveis para correção.")
    if payment_group and payment_group.state != communication.status:
        raise HTTPException(status_code=409, detail="Pagamento agrupado indisponível para correção.")
    previous_status = communication.status
    correction = PaymentConfirmationCorrection(
        payment_communication_id=communication.id,
        sale_order_id=order.id,
        actor_admin_id=session.subject_id,
        idempotency_key=payload.idempotency_key,
        previous_communication_status=communication.status,
        previous_order_status=order.payment_status,
        tenant_id=tenant_id,
    )
    db.add(correction)
    communication.status = "pending_review"
    communication.decided_by_admin_id = None
    communication.decided_at = None
    for item in scope_orders:
        if item.payment_status == "confirmed" and item.delivery_album_url:
            item.delivery_revision += 1
        item.payment_status = "pending"
        item.confirmed_at = None
    if payment_group:
        payment_group.state = "reported"
    audit(db, "payment.refusal_corrected" if previous_status == "refused"
          else "payment.confirmation_corrected", str(communication.id), tenant_id=tenant_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(PaymentConfirmationCorrection).where(PaymentConfirmationCorrection.tenant_id == tenant_id).where(
                PaymentConfirmationCorrection.payment_communication_id == communication_id,
                PaymentConfirmationCorrection.idempotency_key == payload.idempotency_key,
            )
        )
        if not existing:
            raise
        correction = existing
    return {"id": str(correction.id), "status": "pending_review"}


class OrderDeliveryInput(BaseModel):
    model_config = {"extra": "forbid"}
    album_url: str | None
    version: int = Field(ge=0)

    @field_validator("album_url")
    @classmethod
    def safe_album_url(cls, value):
        return validate_album_url(value)


class OrderDeliveryResendInput(BaseModel):
    model_config = {"extra": "forbid"}
    version: int = Field(ge=0)
    operation_id: UUID


@app.put("/admin/orders/{order_id}/delivery")
def update_order_delivery(order_id: UUID, payload: OrderDeliveryInput, request: Request,
                          db: Session = Depends(db_session)) -> dict:
    tenant_id = directory_tenant_id(db, request)
    session = require_admin(request)
    require_same_origin(request)
    try:
        result = set_delivery(db, lock_delivery_order(db, order_id, tenant_id=tenant_id), payload.album_url, payload.version, session.subject_id)
        db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/admin/orders/{order_id}/delivery/resend")
def resend_order_delivery(order_id: UUID, payload: OrderDeliveryResendInput, request: Request,
                          db: Session = Depends(db_session)) -> dict:
    tenant_id = directory_tenant_id(db, request)
    session = require_admin(request)
    require_same_origin(request)
    try:
        result = resend_delivery(db, lock_delivery_order(db, order_id, tenant_id=tenant_id), payload.version, payload.operation_id, session.subject_id)
        db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


class PushSubscriptionInput(BaseModel):
    model_config = {"extra": "forbid"}
    subscription: dict
    expected_identity: str | None = Field(default=None, max_length=80)


@app.get("/push/subscription")
def push_subscription_state(request: Request, response: Response,
                            db: Session = Depends(db_session)) -> dict:
    from app.web_push import push_configuration_ready
    session = current_session(request)
    installation = installation_key(request, response)
    subscription = db.scalar(select(PushSubscription).where(
        PushSubscription.tenant_id == session.tenant_id, PushSubscription.installation_fingerprint == installation,
        PushSubscription.role == session.role, PushSubscription.subject_id == session.subject_id,
        PushSubscription.active))
    available = push_enabled() and push_configuration_ready()
    try:
        push_cipher()
    except ValueError:
        available = False
    public_key = getenv("WEB_PUSH_VAPID_PUBLIC_KEY", "") if available else ""
    response.headers["Cache-Control"] = "no-store"
    return {"available": available and bool(public_key), "active": bool(subscription),
            "public_key": public_key, "identity": f"{session.role}:{session.subject_id}"}


@app.post("/push/subscription", status_code=201)
def register_push_subscription(payload: PushSubscriptionInput, request: Request, response: Response,
                                db: Session = Depends(db_session)) -> dict:
    from app.web_push import push_configuration_ready
    session = current_session(request)
    if not request.headers.get("origin"):
        raise HTTPException(status_code=403, detail="Origem da operação não autorizada.")
    require_same_origin(request)
    if payload.expected_identity is not None and payload.expected_identity != f"{session.role}:{session.subject_id}":
        raise HTTPException(status_code=409, detail="A conta mudou. Atualize a página e tente novamente.")
    enforce_rate_limit(db, "push.subscribe", str(session.subject_id),
                       request.client.host if request.client else "unknown")
    db.commit()  # falhas de validação também contam no limite
    if not push_enabled() or not push_configuration_ready():
        raise HTTPException(status_code=409, detail="Notificações push ainda não disponíveis.")
    try:
        subscribe(db, session, installation_key(request, response), payload.subscription)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A inscrição mudou. Tente novamente.") from None
    audit(db, "push.subscribed", str(session.subject_id), tenant_id=session.tenant_id)
    db.commit()
    return {"active": True}


@app.delete("/push/subscription", status_code=204)
def unregister_push_subscription(request: Request, response: Response,
                                  db: Session = Depends(db_session)) -> Response:
    session = current_session(request)
    if not request.headers.get("origin"):
        raise HTTPException(status_code=403, detail="Origem da operação não autorizada.")
    require_same_origin(request)
    expected_identity = request.headers.get("x-push-identity")
    if expected_identity is not None and expected_identity != f"{session.role}:{session.subject_id}":
        raise HTTPException(status_code=409, detail="A conta mudou. Atualize a página e tente novamente.")
    raw = request.cookies.get(INSTALLATION_COOKIE)
    if raw:
        revoke_installation(db, push_fingerprint(raw), session)
    db.commit()
    response.status_code = 204
    return response


class NotificationSettingInput(BaseModel):
    model_config = {"extra": "forbid"}
    version: int = Field(ge=1)
    whatsapp_enabled: bool
    push_enabled: bool
    whatsapp_body: str = Field(min_length=1, max_length=500)
    push_title: str = Field(min_length=1, max_length=60)
    push_body: str = Field(min_length=1, max_length=140)


@app.get("/admin/notification-settings")
def list_notification_settings(request: Request, db: Session = Depends(db_session)) -> dict:
    from app.whatsapp_channel import notification_channel_ready

    tenant_id = directory_tenant_id(db, request)
    whatsapp_editable = notification_channel_ready(db, tenant_id=tenant_id)
    settings = [setting_payload(setting_for(db, kind, tenant_id=tenant_id)) for kind in NOTIFICATION_DEFINITIONS]
    db.commit()
    return {"settings": settings, "whatsapp_editable": whatsapp_editable}


@app.put("/admin/notification-settings/{event_type}")
def update_notification_setting(event_type: str, payload: NotificationSettingInput,
                                request: Request, db: Session = Depends(db_session)) -> dict:
    session = require_admin(request)
    require_same_origin(request)
    try:
        setting = save_setting(db, event_type, payload.model_dump(), tenant_id=session.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit(db, "notification.setting_updated", f"{session.subject_id}:{event_type}:{setting.version}", tenant_id=session.tenant_id)
    db.commit()
    return setting_payload(setting)


@app.put("/admin/payment-message-templates/{kind}")
def save_payment_template(
    kind: Literal["confirmed", "refused"],
    payload: PaymentTemplateInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    session = require_admin(request)
    try:
        body = validate_template(payload.body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    save_setting(db, f"payment_{kind}", {"whatsapp_body": body}, tenant_id=session.tenant_id)
    db.commit()
    return {"kind": kind, "body": body}


@app.get("/admin/payment-message-templates")
def list_payment_templates(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    configured = payment_template_bodies(db, tenant_id=tenant_id)
    return {
        "templates": {
            kind: configured.get(kind, default)
            for kind, default in DEFAULT_PAYMENT_TEMPLATES.items()
        },
        "allowed_variables": sorted(["cliente", "pedido", "galeria", "contexto_pagamento"]),
    }


@app.get("/admin/payment-message-templates/migration-preview")
def preview_payment_template_migration_api(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    session = require_admin(request)
    return {"templates": preview_payment_template_migration(
        payment_template_migration_sources(db, tenant_id=session.tenant_id)
    )}


@app.get("/admin/removed-photo-movements")
def admin_removed_photo_movements(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    parent_gallery_id: UUID | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=50),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="O início do período deve ser anterior ao fim.")
    return removed_movements_page(db, tenant_id=tenant_id, query=query, parent_gallery_id=parent_gallery_id,
                                  created_from=created_from, created_to=created_to,
                                  offset=offset, limit=limit)


PaymentFinancialFilter = Literal[
    "priority", "reported", "confirmed", "confirmed_undelivered",
    "awaiting_payment", "selection_finalized", "not_found", "verifying", "exception", "hold", "reopened",
    "processing", "rejected", "canceled", "expired", "refunded", "partially_refunded",
    "charged_back", "duplicate_review",
]


@app.get("/admin/orders/{order_id}/items/{item_id}/preview")
def admin_order_item_preview(
    order_id: UUID, item_id: UUID, request: Request,
    size: Literal["thumbnail", "preview"] = "thumbnail",
    db: Session = Depends(db_session),
) -> FileResponse:
    require_admin(request)
    tenant_id = directory_tenant_id(db, request)
    order = db.scalar(
        select(SaleOrder).where(SaleOrder.id == order_id, SaleOrder.tenant_id == tenant_id)
    )
    item = db.scalar(select(SaleOrderItem).where(
        SaleOrderItem.id == item_id, SaleOrderItem.sale_order_id == order_id,
        SaleOrderItem.tenant_id == tenant_id,
    ))
    if not order or order.assets_removed_at or not item or not item.photo_asset_id:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    photo = db.scalar(
        select(PhotoAsset).where(
            PhotoAsset.id == item.photo_asset_id, PhotoAsset.tenant_id == tenant_id
        )
    )
    if not photo or not photo.available or photo.id != item.photo_asset_id_snapshot:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    media_state = folder_media_state_by_id(
        db, folder_id=item.folder_id_snapshot or photo.folder_id, tenant_id=tenant_id,
    )
    if media_state not in {"available", "archiving"}:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    derivative = db.scalar(select(MediaDerivative).where(
        MediaDerivative.photo_asset_id == photo.id,
        MediaDerivative.tenant_id == tenant_id,
        MediaDerivative.variant == ("thumbnail" if size == "thumbnail" else "admin_preview"),
        MediaDerivative.status == "ready",
    ))
    if not derivative:
        raise HTTPException(status_code=404, detail="Prévia indisponível.")
    try:
        path = safe_derivative_path(derivative)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Prévia indisponível.") from exc
    audit(db, "media_preview.order_item_viewed", str(item.id))
    db.commit()
    return protected_preview_response(path, f"pedido-{item.filename_snapshot}")


@app.get("/admin/payment-communications/export.csv")
def export_payment_orders(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    client_id: UUID | None = None,
    parent_gallery_id: UUID | None = None,
    financial_status: PaymentFinancialFilter | None = None,
    payment_provider: Literal["pix", "mercadopago", "infinitepay"] | None = None,
    include_financial_details: bool = False,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    db: Session = Depends(db_session),
) -> Response:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    from app.payment_export import payment_orders_csv

    data = _payment_dashboard_data(
        db, tenant_id=tenant_id, query=query, client_id=client_id, parent_gallery_id=parent_gallery_id,
        financial_status=financial_status, created_from=created_from, created_to=created_to,
        export_all=True, include_selections=False, payment_provider=payment_provider,
    )
    if not data["groups"]:
        return Response(status_code=204)
    return Response(
        payment_orders_csv(data["groups"], include_financial_details=include_financial_details),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pick-your-pic-vendas-pagamentos.csv"',
                 "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@app.get("/admin/payment-communications")
def list_payment_communications(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    client_id: UUID | None = None,
    parent_gallery_id: UUID | None = Query(default=None),
    financial_status: PaymentFinancialFilter | None = Query(default=None),
    payment_provider: Literal["pix", "mercadopago", "infinitepay"] | None = None,
    delivery_status: Literal["none", "queued", "processing", "sent", "failed"]
    | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    cursor: str | None = Query(default=None, max_length=500),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(db_session),
) -> dict[str, object]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    return _payment_dashboard_data(
        db, tenant_id=tenant_id, query=query, client_id=client_id, parent_gallery_id=parent_gallery_id,
        financial_status=financial_status, delivery_status=delivery_status,
        payment_provider=payment_provider,
        created_from=created_from, created_to=created_to, cursor=cursor, limit=limit,
    )


def _payment_dashboard_data(
    db: Session, *, tenant_id: UUID, query=None, client_id=None, parent_gallery_id=None,
    financial_status=None, delivery_status=None, created_from=None, created_to=None,
    cursor=None, limit=20, export_all=False, include_selections=True, payment_provider=None,
) -> dict[str, object]:
    if payment_provider:
        include_selections = False
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=422,
            detail="O início do período deve ser anterior ao fim.",
        )

    order_query = (
        select(SaleOrder, Client, DerivedGallery, ParentGallery).where(or_(Client.id.is_(None), Client.tenant_id == tenant_id), or_(DerivedGallery.id.is_(None), DerivedGallery.tenant_id == tenant_id), or_(ParentGallery.id.is_(None), ParentGallery.tenant_id == tenant_id), SaleOrder.tenant_id == tenant_id)
        .where(visible_sale_order_condition(tenant_id=tenant_id))
        .outerjoin(Client, Client.id == SaleOrder.client_id)
        .outerjoin(DerivedGallery, DerivedGallery.id == SaleOrder.derived_gallery_id)
        .outerjoin(ParentGallery, ParentGallery.id == SaleOrder.parent_gallery_id_snapshot)
        .order_by(SaleOrder.created_at.desc(), SaleOrder.id.desc())
    )
    normalized_query = query.strip().lower() if query else ""
    if normalized_query and not client_id:
        phone_query = "".join(character for character in normalized_query if character.isdigit())
        search_criteria = [
            func.lower(
                func.coalesce(Client.full_name, SaleOrder.client_name_snapshot, "")
            ).like(f"%{normalized_query}%")
        ]
        if phone_query:
            search_criteria.extend(
                [
                    Client.phone_e164.contains(phone_query),
                    SaleOrder.client_phone_snapshot.contains(phone_query),
                ]
            )
        order_query = order_query.where(or_(*search_criteria))
    if client_id:
        order_query = order_query.where(SaleOrder.client_id == client_id)
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
    order_entities = [row[0] for row in order_rows]
    mp_payments = mercadopago_for_orders(db, order_entities, tenant_id=tenant_id)
    card_payment_ids = {order.provider_payment_id for order in order_entities if order.provider_payment_id}
    card_payments = {
        payment.id: payment for payment in db.scalars(select(ProviderPayment).where(
            ProviderPayment.tenant_id == tenant_id,
            ProviderPayment.id.in_(card_payment_ids),
        ))
    } if card_payment_ids else {}
    recovery_statuses = cart_recovery_statuses(
        db, tenant_id=tenant_id, payments=card_payments.values()
    )
    communication_rows = list(db.scalars(select(PaymentCommunication).where(PaymentCommunication.tenant_id == tenant_id).where(or_(
        PaymentCommunication.sale_order_id.in_(order_ids),
        PaymentCommunication.payment_group_id.in_({order.payment_group_id for order in order_entities
                                                  if order.payment_group_id}),
    )).order_by(PaymentCommunication.created_at.desc())))
    communications_by_order = {order.id: [item for item in communication_rows
        if item.sale_order_id == order.id or (order.payment_group_id and
                                             item.payment_group_id == order.payment_group_id)]
        for order in order_entities}
    scopes = payment_scopes(
        db,
        {item.payment_group_id for item in communication_rows if item.payment_group_id},
        tenant_id=tenant_id,
    )
    scopes_by_communication = {item.id: scopes.get(item.payment_group_id)
                               for item in communication_rows}

    communication_ids = [communication.id for communication in communication_rows]
    correction_rows = (
        list(
            db.scalars(
                select(PaymentConfirmationCorrection).where(PaymentConfirmationCorrection.tenant_id == tenant_id)
                .where(
                    PaymentConfirmationCorrection.payment_communication_id.in_(
                        communication_ids
                    )
                )
                .order_by(PaymentConfirmationCorrection.created_at.desc())
            )
        )
        if communication_ids
        else []
    )
    corrections_by_communication: dict[UUID, list[PaymentConfirmationCorrection]] = defaultdict(
        list
    )
    for correction in correction_rows:
        corrections_by_communication[correction.payment_communication_id].append(correction)
    notification_rows = (
        list(
            db.scalars(
                select(PaymentNotificationOutbox).where(PaymentNotificationOutbox.tenant_id == tenant_id)
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

    order_items = (
        list(
            db.scalars(
                select(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id)
                .where(SaleOrderItem.sale_order_id.in_(order_ids))
                .order_by(SaleOrderItem.sale_order_id, SaleOrderItem.id)
            )
        )
        if order_ids
        else []
    )
    items_by_order: dict[UUID, list[SaleOrderItem]] = defaultdict(list)
    for item in order_items:
        items_by_order[item.sale_order_id].append(item)
    purchase_interactions = (
        {}
        if export_all
        else _purchase_photo_interactions(
            db,
            tenant_id=tenant_id,
            purchases=[
                (order, item)
                for order in order_entities
                for item in items_by_order.get(order.id, [])
            ],
        )
    )
    media_state_cache = folder_media_states_by_id(
        db,
        folder_ids={item.folder_id_snapshot for item in order_items if item.folder_id_snapshot},
        tenant_id=tenant_id,
    )
    selection_query = (
        select(PhotoSelection, PhotoAsset, PhotoFolder, DerivedGallery, Client, ParentGallery).where(Client.tenant_id == tenant_id, or_(DerivedGallery.id.is_(None), DerivedGallery.tenant_id == tenant_id), or_(ParentGallery.id.is_(None), ParentGallery.tenant_id == tenant_id), PhotoAsset.tenant_id == tenant_id, PhotoFolder.tenant_id == tenant_id, PhotoSelection.tenant_id == tenant_id)
        .join(PhotoAsset, PhotoAsset.id == PhotoSelection.photo_asset_id)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .outerjoin(DerivedGallery, DerivedGallery.id == PhotoSelection.derived_gallery_id)
        .join(Client, Client.id == PhotoSelection.client_id)
        .outerjoin(ParentGallery, ParentGallery.id == func.coalesce(
            PhotoSelection.parent_gallery_id, DerivedGallery.parent_gallery_id
        ))
        .order_by(PhotoSelection.created_at.desc())
    )
    if normalized_query and not client_id:
        phone_query = "".join(character for character in normalized_query if character.isdigit())
        search_criteria = [func.lower(Client.full_name).like(f"%{normalized_query}%")]
        if phone_query:
            search_criteria.append(Client.phone_e164.contains(phone_query))
        selection_query = selection_query.where(or_(*search_criteria))
    if client_id:
        selection_query = selection_query.where(PhotoSelection.client_id == client_id)
    if parent_gallery_id:
        selection_query = selection_query.where(
            ParentGallery.id == parent_gallery_id
        )
    if created_from:
        selection_query = selection_query.where(PhotoSelection.created_at >= created_from)
    if created_to:
        selection_query = selection_query.where(PhotoSelection.created_at <= created_to)
    include_open_selections = (
        include_selections and financial_status is None and delivery_status is None
    )
    selection_rows = list(db.execute(selection_query)) if include_open_selections else []
    selection_groups: dict[tuple[UUID, UUID], dict[str, object]] = {}
    selection_parents: dict[tuple[UUID, UUID], ParentGallery | None] = {}
    for selection, photo, folder, gallery, client, parent in selection_rows:
        scope_id = gallery.id if gallery else selection.parent_gallery_id
        if scope_id is None:
            continue
        key = (scope_id, client.id)
        selection_parents[key] = parent
        group = selection_groups.setdefault(
            key,
            {
                "client": {"id": str(client.id), "name": client.full_name},
                "gallery": {"id": str(scope_id), "name": gallery.name if gallery else (parent.name if parent else "Galeria pública removida")},
                "parent_gallery": {
                    "id": str(parent.id if parent else scope_id),
                    "name": parent.name if parent else "Galeria pública removida",
                },
                "selected_count": 0,
                "created_at": selection.created_at.isoformat(),
                "folders": {},
            },
        )
        group["selected_count"] += 1
        folder_group = group["folders"].setdefault(
            str(folder.id), {"id": str(folder.id), "name": folder.name, "items": []}
        )
        folder_group["items"].append({"id": str(photo.id), "name": photo.display_name or photo.filename})
    selection_parent_ids = {
        parent.id for parent in selection_parents.values() if parent is not None
    }
    pricing_rules = (
        list(
            db.scalars(
                select(PriceRule).where(PriceRule.tenant_id == tenant_id)
                .where(PriceRule.parent_gallery_id.in_(selection_parent_ids))
                .order_by(PriceRule.parent_gallery_id, PriceRule.minimum_quantity)
            )
        )
        if selection_parent_ids
        else []
    )
    pricing_rules_by_parent: dict[UUID, list[PriceRule]] = defaultdict(list)
    for rule in pricing_rules:
        pricing_rules_by_parent[rule.parent_gallery_id].append(rule)
    for key, group in selection_groups.items():
        parent = selection_parents[key]
        try:
            if parent is None:
                raise GalleryPricingError("Galeria pública não disponível.")
            quote = quote_parent_gallery(
                db,
                gallery=parent,
                quantity=group["selected_count"],
                rules=pricing_rules_by_parent[parent.id],
            )
        except GalleryPricingError:
            group["total_cents"] = None
            group["pricing_available"] = False
        else:
            group["total_cents"] = quote.quote.total_cents
            group["pricing_available"] = True
    configured_templates = payment_template_bodies(db, tenant_id=tenant_id)

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
        provider_payment = card_payments.get(order.provider_payment_id)
        mp_payment = mp_payments.get(order.mercadopago_payment_id)
        recovery = recovery_statuses.get(order.provider_payment_id, {})
        historical_only = bool(recovery.get("historical_only"))
        financial_state = _payment_financial_status(
            order, latest_communication, gallery, provider_payment, mp_payment)
        if payment_provider and mercadopago_fields(order, mp_payments)["payment_provider"] != payment_provider:
            continue
        if financial_status == "reopened":
            if not historical_only:
                continue
        elif historical_only:
            continue
        delivery_states = {notification.status for notification in order_notifications} or {"none"}
        if financial_status == "priority" and financial_state not in {
            "reported", "confirmed_undelivered", "partially_refunded", "charged_back", "duplicate_review"
        }:
            continue
        if financial_status and financial_status not in {"priority", "reopened"} and financial_state != financial_status:
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
                corrections=corrections_by_communication.get(communication.id, []),
                max_attempts=max_attempts,
            )
            payload["payment_group"] = scopes_by_communication.get(communication.id)
            communication_payloads.append(payload)
            flat_by_id[str(communication.id)] = payload

        folders: dict[str, dict[str, object]] = {}
        for item in items_by_order.get(order.id, []):
            interaction = purchase_interactions.get(
                item.id, {"comment_preview": None, "favorited": False}
            )
            folder_key = str(item.folder_id_snapshot) if item.folder_id_snapshot else "unknown"
            if item.folder_id_snapshot is None:
                media_state = "available"  # pedidos antigos não tinham escopo de pasta arquivável
            else:
                media_state = media_state_cache.get(item.folder_id_snapshot, "unavailable")
                if media_state == "unavailable":
                    media_state = "available"
            media_local = media_state in {"available", "archiving"}
            folder = folders.setdefault(
                folder_key,
                {
                    "id": str(item.folder_id_snapshot) if item.folder_id_snapshot else None,
                    "name": item.folder_name_snapshot or "Pasta não disponível",
                    "media_state": media_state,
                    "items": [],
                },
            )
            folder["items"].append(
                {
                    "id": str(item.id),
                    "photo_id": str(item.photo_asset_id_snapshot),
                    "name": item.filename_snapshot,
                    "unit_price_cents": item.unit_price_cents,
                    "media_state": media_state,
                    "comment_preview": interaction["comment_preview"],
                    "favorited": interaction["favorited"],
                    "thumbnail_url": (f"/admin/orders/{order.id}/items/{item.id}/preview?size=thumbnail"
                                      if item.photo_asset_id and not order.assets_removed_at and media_local else None),
                    "preview_url": (f"/admin/orders/{order.id}/items/{item.id}/preview?size=preview"
                                    if item.photo_asset_id and not order.assets_removed_at and media_local else None),
                }
            )
        prepared_orders.append(
            {
                "id": str(order.id),
                "parent_gallery": {
                    "id": str(order.parent_gallery_id_snapshot),
                    "name": order.parent_gallery_name_snapshot,
                    "removed": parent is None or parent.lifecycle_status == "deleted",
                },
                "gallery": {
                    "id": str(order.derived_gallery_id_snapshot or order.parent_gallery_id_snapshot),
                    "name": order.derived_gallery_name_snapshot or order.parent_gallery_name_snapshot,
                    "removed": gallery is None and order.derived_gallery_id_snapshot is not None,
                },
                "total_cents": order.total_cents,
                "financial_status": "reopened" if historical_only else financial_state,
                **({"payment_method": (provider_payment.capture_method or "credit_card") if provider_payment else "pix"}
                   if provider_payment or order.payment_group_id or latest_communication else {}),
                **({"provider_payment_state": provider_payment.state,
                    "provider_payment_id": str(provider_payment.id),
                    } if provider_payment else {}),
                **({"provider_cart_recovery": {
                    "reopened_at": recovery["reopened_at"],
                    "requires_reconciliation": recovery["requires_reconciliation"],
                }} if recovery.get("reopened_at") else {}),
                **mercadopago_fields(order, mp_payments),
                "confirmed_at": (order.confirmed_at.isoformat()
                                 if order.payment_status == "confirmed" and order.confirmed_at
                                 else None),
                "assets_removed": bool(order.assets_removed_at),
                "payment_status": order.payment_status,
                "created_at": order.created_at.isoformat(),
                "selection_expires_at": None,
                "communications": communication_payloads,
                "communication": communication_payloads[0] if communication_payloads else None,
                "delivery_statuses": sorted(delivery_states),
                "folders": list(folders.values()),
                "payment_message_snapshot": order.payment_message_snapshot,
                "delivery": delivery_payload(order),
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
                "totals": {
                    "orders": 0,
                    "total_cents": 0,
                    "reported_orders": 0,
                    "reported_cents": 0,
                    "confirmed_orders": 0,
                    "confirmed_cents": 0,
                },
                "orders": [],
                "financial_status": order_payload["financial_status"],
                "_sort_priority": _payment_financial_priority(order_payload["financial_status"]),
                "_sort_created_at": sort_created_at,
            },
        )
        group["orders"].append(order_payload)
        order_priority = _payment_financial_priority(order_payload["financial_status"])
        if order_priority < group["_sort_priority"]:
            group["financial_status"] = order_payload["financial_status"]
            group["_sort_priority"] = order_priority
            group["_sort_created_at"] = sort_created_at
        elif order_priority == group["_sort_priority"]:
            group["_sort_created_at"] = min(group["_sort_created_at"], sort_created_at)
        group["totals"]["orders"] += 1
        if order_payload["financial_status"] == "reported":
            group["totals"]["reported_orders"] += 1
            group["totals"]["reported_cents"] += order_payload["total_cents"]
        elif (order_payload["financial_status"] in {"confirmed", "confirmed_undelivered"}
              and not (order_payload.get("mercadopago") or {}).get("test_account")):
            group["totals"]["confirmed_orders"] += 1
            group["totals"]["confirmed_cents"] += order_payload["total_cents"]
        # Compatibilidade temporária: `total_cents` passa a representar somente
        # pedidos cujo pagamento foi comunicado e ainda aguarda conferência.
        group["totals"]["total_cents"] = group["totals"]["reported_cents"]

    all_groups = sorted(
        grouped.values(),
        key=lambda group: (
            group["_sort_priority"],
            group["_sort_created_at"].isoformat(),
            group["client"]["id"],
        ),
    )
    cursor_key = _decode_payment_cursor(cursor) if cursor else None
    if cursor_key:
        all_groups = [
            group
            for group in all_groups
            if (
                group["_sort_priority"],
                group["_sort_created_at"].isoformat(),
                group["client"]["id"],
            ) > cursor_key
        ]

    page_groups = all_groups if export_all else all_groups[:limit]
    has_next_page = not export_all and len(all_groups) > limit
    next_cursor = None
    if has_next_page and page_groups:
        last_group = page_groups[-1]
        next_cursor = _encode_payment_cursor(
            last_group["_sort_created_at"],
            last_group["client"]["id"],
            priority=last_group["_sort_priority"],
        )
    for group in page_groups:
        group.pop("_sort_created_at", None)
        group.pop("_sort_priority", None)

    financial_counts: dict[str, int] = defaultdict(int)
    delivery_counts: dict[str, int] = defaultdict(int)
    parent_counts: dict[tuple[str, str], int] = defaultdict(int)
    reported_orders = 0
    reported_cents = 0
    confirmed_orders = 0
    confirmed_cents = 0
    for order_payload in prepared_orders:
        financial_counts[order_payload["financial_status"]] += 1
        if order_payload["financial_status"] == "reported":
            reported_orders += 1
            reported_cents += order_payload["total_cents"]
        elif (order_payload["financial_status"] in {"confirmed", "confirmed_undelivered"}
              and not (order_payload.get("mercadopago") or {}).get("test_account")):
            confirmed_orders += 1
            confirmed_cents += order_payload["total_cents"]
        for state in order_payload["delivery_statuses"]:
            delivery_counts[state] += 1
        parent_gallery = order_payload["parent_gallery"]
        parent_counts[(parent_gallery["id"], parent_gallery["name"])] += 1

    selected_carts = len(selection_groups)
    selected_cents = sum(
        item["total_cents"]
        for item in selection_groups.values()
        if item["total_cents"] is not None
    )
    selected_pricing_unavailable = sum(
        1 for item in selection_groups.values() if item["total_cents"] is None
    )

    page_communication_ids = {
        communication["id"]
        for group in page_groups
        for order_payload in group["orders"]
        for communication in order_payload["communications"]
    }
    return {
        "templates": {
            kind: configured_templates.get(kind, default)
            for kind, default in DEFAULT_PAYMENT_TEMPLATES.items()
        },
        "templates_are_global": True,
        "selections_without_order": [
            {**item, "folders": list(item["folders"].values())}
            for item in selection_groups.values()
        ],
        "summary": {
            "clients": len(
                set(grouped) | {client_id for _gallery_id, client_id in selection_groups}
            ),
            "orders": len(prepared_orders),
            "total_cents": reported_cents,
            "selected_carts": selected_carts,
            "selected_cents": selected_cents,
            "selected_pricing_unavailable": selected_pricing_unavailable,
            "reported_orders": reported_orders,
            "reported_cents": reported_cents,
            "confirmed_orders": confirmed_orders,
            "confirmed_cents": confirmed_cents,
            "financial_statuses": dict(financial_counts),
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
        # Compatibilidade: a consulta paginada do histórico é explícita e separada.
        "removed_movements": [],
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
    provider_payment: ProviderPayment | None = None,
    mercadopago_payment=None,
) -> str:
    if mercadopago_payment:
        return mercadopago_financial_status(mercadopago_payment, order)
    if order.mercadopago_payment_id:
        return "verifying"
    if provider_payment:
        financial_state = {
            "creating": "awaiting_payment",
            "awaiting_payment": "awaiting_payment",
            "verification_required": "verifying",
            "confirmed": "confirmed",
            "failed_before_issue": "not_found",
            "exception": "exception",
            "hold": "hold",
        }[provider_payment.state]
        if financial_state == "confirmed" and not order.delivery_album_url:
            return "confirmed_undelivered"
        return financial_state
    if (order.payment_status == "not_required" and order.payment_required_snapshot is False
            and order.frozen_at is not None):
        return "selection_finalized"
    if order.payment_status == "confirmed":
        return "confirmed" if order.delivery_album_url else "confirmed_undelivered"
    if order.payment_status == "cancelled":
        return "not_found"
    if latest_communication and latest_communication.status == "pending_review":
        return "reported"
    return "awaiting_payment"


def _payment_financial_priority(financial_status: str) -> int:
    return {
        "reported": 0,
        "confirmed": 1,
        "confirmed_undelivered": 2,
        "awaiting_payment": 3,
        "not_found": 4,
        "verifying": 6,
        "exception": 7,
        "hold": 8,
        "selection_finalized": 9,
        "reopened": 9,
        "partially_refunded": 0, "charged_back": 0, "duplicate_review": 0,
        "processing": 6, "rejected": 7, "canceled": 8, "expired": 8, "refunded": 8,
    }.get(financial_status, 9)


def _admin_payment_communication_payload(
    item: PaymentCommunication,
    *,
    order: SaleOrder,
    client: Client | None,
    gallery: DerivedGallery | None,
    notifications: list[PaymentNotificationOutbox],
    corrections: list[PaymentConfirmationCorrection],
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
        "gallery_name": order.derived_gallery_name_snapshot or order.parent_gallery_name_snapshot,
        "gallery_removed": gallery is None and order.derived_gallery_id_snapshot is not None,
        "total_cents": order.total_cents,
        "created_at": item.created_at.isoformat(),
        "decided_at": item.decided_at.isoformat() if item.decided_at else None,
        **payment_capabilities(item.status, order.payment_status),
        "corrections": [
            {
                "id": str(correction.id),
                "created_at": correction.created_at.isoformat(),
            }
            for correction in corrections
        ],
        "photographer_notification": _delivery_payload(
            photographer_delivery, max_attempts
        ),
        "client_notification": _delivery_payload(client_delivery, max_attempts),
    }


def _encode_payment_cursor(
    created_at: datetime, client_id: str, *, priority: int = 0
 ) -> str:
    raw = json.dumps(
        {
            "priority": priority,
            "created_at": created_at.isoformat(),
            "client_id": client_id,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_payment_cursor(cursor: str) -> tuple[int, str, str]:
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding).decode("utf-8"))
        created_at = datetime.fromisoformat(payload["created_at"])
        client_id = UUID(payload["client_id"])
        priority = payload["priority"]
        if not isinstance(priority, int) or priority < 0:
            raise ValueError("Invalid priority")
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Cursor de pagamentos inválido.") from exc
    return int(payload.get("priority", 0)), created_at.isoformat(), str(client_id)


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
    tenant_id = directory_tenant_id(db, request)
    outbox = owned_record(db, PaymentNotificationOutbox, notification_id, tenant_id=tenant_id)
    if not outbox:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    if outbox.status != "failed" or outbox.attempts >= payment_notification_max_attempts():
        raise HTTPException(status_code=409, detail="Notificação indisponível para reenvio.")
    try:
        retry_payment_projection(db, outbox)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    outbox.status = "queued"
    outbox.last_error = None
    outbox.updated_at = now()
    audit(db, "payment.notification_requeued", str(outbox.id), tenant_id=tenant_id)
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
        tenant_id=session.tenant_id,
    )
    return {
        "orders": client_orders_payload(
            db, gallery_id=gallery_id, client_id=session.subject_id
        )
    }


@app.get("/gallery/{gallery_id}/orders/{order_id}")
def client_pending_order(
    gallery_id: UUID, order_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Entrega somente o snapshot PIX pendente à cliente proprietária."""
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    derived_gallery_for_client(db, gallery_id, session.subject_id, allow_deleted_origin=True, tenant_id=session.tenant_id)
    order = db.scalar(
        select(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(
            SaleOrder.id == order_id,
            SaleOrder.derived_gallery_id == gallery_id,
            SaleOrder.client_id == session.subject_id,
        )
    )
    if not order:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    if order.assets_removed_at:
        raise HTTPException(status_code=409, detail="O acervo deste pedido foi removido. Consulte seu histórico em Compras.")
    if order.payment_status != "pending":
        raise HTTPException(status_code=409, detail="Este pedido não está pendente de confirmação.")
    if order.payment_group_id:
        return {
            "id": str(order.id),
            "payment_group_id": str(order.payment_group_id),
            "total_cents": order.total_cents,
            "review_url": "/library/cart" if order.frozen_at is None else
                f"/library/purchases#payment-{order.payment_group_id}",
            "pix": None,
        }
    items = list(
        db.scalars(
            select(SaleOrderItem).where(SaleOrderItem.tenant_id == tenant_id)
            .where(SaleOrderItem.sale_order_id == order.id)
            .order_by(SaleOrderItem.filename_snapshot)
        )
    )
    selection_created_at_by_photo = {
        selection.photo_asset_id: selection.created_at
        for selection in db.scalars(
            select(PhotoSelection).where(
                PhotoSelection.tenant_id == tenant_id,
                PhotoSelection.derived_gallery_id == gallery_id,
                PhotoSelection.client_id == session.subject_id,
                PhotoSelection.photo_asset_id.in_(
                    {item.photo_asset_id_snapshot for item in items}
                ),
            )
        )
    } if items else {}
    photo_ids = {
        item.photo_asset_id
        for item in items
        if item.photo_asset_id and item.folder_id_snapshot is None
    }
    photos_by_id = {
        photo.id: photo for photo in db.scalars(
            select(PhotoAsset).where(
                PhotoAsset.tenant_id == tenant_id,
                PhotoAsset.id.in_(photo_ids),
            )
        )
    } if photo_ids else {}
    item_folder_ids = {
        item.folder_id_snapshot or (
            photos_by_id[item.photo_asset_id].folder_id
            if item.photo_asset_id in photos_by_id else None
        )
        for item in items
    }
    folder_access = folder_media_access_by_id(
        db,
        folder_ids={folder_id for folder_id in item_folder_ids if folder_id},
        tenant_id=tenant_id,
        client_id=session.subject_id,
    )
    media_states = {
        folder_id: access[0] for folder_id, access in folder_access.items()
    }
    folder_expiries = {
        folder_id: access[1] for folder_id, access in folder_access.items()
    }
    item_media_states: dict[UUID, str] = {}
    item_previews_allowed: dict[UUID, bool] = {}
    current_time = now()
    for item in items:
        photo = photos_by_id.get(item.photo_asset_id) if item.photo_asset_id else None
        folder_id = item.folder_id_snapshot or (photo.folder_id if photo else None)
        item_media_states[item.id] = (
            "available" if folder_id is None and item.folder_id_snapshot is None
            else media_states.get(folder_id, "unavailable")
        )
        expiry = folder_expiries.get(folder_id) if folder_id else None
        item_previews_allowed[item.id] = folder_selected_media_preview_allowed(
            media_state=item_media_states[item.id],
            expiry=expiry,
            selected_at=selection_created_at_by_photo.get(item.photo_asset_id_snapshot),
            existing_order_created_at=(
                order.created_at if order.frozen_at is not None else None
            ),
            existing_order_open=(
                order.payment_status == "pending" and order.frozen_at is not None
            ),
            at=current_time,
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
        "commercial_state": "draft" if order.frozen_at is None else "awaiting_payment",
        "frozen_at": order.frozen_at.isoformat() if order.frozen_at else None,
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
                "photo_id": str(item.photo_asset_id_snapshot),
                "name": item.filename_snapshot,
                "unit_price_cents": item.unit_price_cents,
                "media_state": item_media_states[item.id],
                "preview_url": (
                    f"/gallery/{gallery_id}/photos/{item.photo_asset_id_snapshot}/preview"
                    if item.photo_asset_id is not None and item_previews_allowed[item.id]
                    else None
                ),
            }
            for item in items
        ],
    }


@app.post("/gallery/{gallery_id}/photos/{photo_id}/favorite", status_code=status.HTTP_201_CREATED)
def favorite_photo(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id, tenant_id=session.tenant_id)
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
    if not parent or not parent.favorites_enabled:
        raise HTTPException(
            status_code=403, detail="Favoritos não estão habilitados nesta galeria."
        )
    assigned_photo_for_gallery(
        db, gallery_id, photo_id, tenant_id=session.tenant_id, client_id=session.subject_id
    )
    existing = db.scalar(
        select(PhotoFavorite).where(PhotoFavorite.tenant_id == tenant_id).where(
            PhotoFavorite.derived_gallery_id == gallery_id,
            PhotoFavorite.photo_asset_id == photo_id,
            PhotoFavorite.client_id == session.subject_id,
        )
    )
    if not existing:
        db.add(
            PhotoFavorite(
                derived_gallery_id=gallery_id, photo_asset_id=photo_id, client_id=session.subject_id,
                tenant_id=tenant_id,
            )
        )
        audit(db, "photo_favorite.created", str(gallery_id), tenant_id=tenant_id)
        db.commit()
    return {"status": "favorited"}


@app.delete(
    "/gallery/{gallery_id}/photos/{photo_id}/favorite", status_code=status.HTTP_204_NO_CONTENT
)
def unfavorite_photo(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    derived_gallery_for_client(db, gallery_id, session.subject_id, tenant_id=session.tenant_id)
    favorite = db.scalar(
        select(PhotoFavorite).where(PhotoFavorite.tenant_id == tenant_id).where(
            PhotoFavorite.derived_gallery_id == gallery_id,
            PhotoFavorite.photo_asset_id == photo_id,
            PhotoFavorite.client_id == session.subject_id,
        )
    )
    if favorite:
        db.delete(favorite)
        audit(db, "photo_favorite.removed", str(gallery_id), tenant_id=tenant_id)
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
    tenant_id = session.tenant_id
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id, tenant_id=session.tenant_id)
    parent = owned_record(db, ParentGallery, gallery.parent_gallery_id, tenant_id=tenant_id)
    if not parent or not parent.comments_enabled:
        raise HTTPException(
            status_code=403, detail="Comentários não estão habilitados nesta galeria."
        )
    assigned_photo_for_gallery(
        db, gallery_id, photo_id, tenant_id=session.tenant_id, client_id=session.subject_id
    )
    comment = PhotoComment(
        derived_gallery_id=gallery_id,
        photo_asset_id=photo_id,
        client_id=session.subject_id,
        body=payload.body.strip(),
        tenant_id=tenant_id,
    )
    db.add(comment)
    db.flush()
    audit(db, "photo_comment.created", str(comment.id), tenant_id=tenant_id)
    db.commit()
    return {"id": str(comment.id)}


@app.get("/gallery/{gallery_id}/comments")
def client_comments(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    session = current_session(request, Role.CLIENT)
    tenant_id = session.tenant_id
    derived_gallery_for_client(db, gallery_id, session.subject_id, allow_deleted_origin=True, tenant_id=session.tenant_id)
    comments = db.scalars(
        select(PhotoComment).where(PhotoComment.tenant_id == tenant_id)
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
    tenant_id = session.tenant_id
    derived_gallery_for_client(db, gallery_id, session.subject_id, tenant_id=session.tenant_id)
    comment = db.scalar(
        select(PhotoComment).where(PhotoComment.tenant_id == tenant_id).where(
            PhotoComment.id == comment_id,
            PhotoComment.derived_gallery_id == gallery_id,
            PhotoComment.client_id == session.subject_id,
            PhotoComment.removed_at.is_(None),
        )
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comentário não encontrado.")
    comment.removed_at = now()
    audit(db, "photo_comment.removed_by_client", str(comment.id), tenant_id=tenant_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/admin/derived-galleries/{gallery_id}/comments")
def admin_comments(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    if not owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    comments = db.scalars(
        select(PhotoComment).where(PhotoComment.tenant_id == tenant_id)
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
    tenant_id = directory_tenant_id(db, request)
    require_admin(request)
    comment = db.scalar(
        select(PhotoComment).where(PhotoComment.tenant_id == tenant_id).where(
            PhotoComment.id == comment_id,
            PhotoComment.derived_gallery_id == gallery_id,
            PhotoComment.removed_at.is_(None),
        )
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comentário não encontrado.")
    require_derived_gallery_mutable(db, gallery_id, tenant_id=tenant_id)
    comment.removed_at = now()
    audit(db, "photo_comment.removed_by_admin", str(comment.id), tenant_id=tenant_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


from app.mercadopago_api import register_mercadopago_routes

register_mercadopago_routes(
    app, db_session=db_session, require_same_origin=require_same_origin,
    commerce_client=_commerce_client, admin_tenant_context=directory_tenant_id,
)

register_preview_adjustment_routes(
    app, db_session=db_session, require_admin=require_admin,
    preview_response=protected_preview_response, tenant_context=directory_tenant_id,
)
register_folder_processing_routes(
    app, db_session=db_session, require_admin=require_admin,
    require_same_origin=require_same_origin, tenant_context=directory_tenant_id,
)

# Opt-in monitor uses the existing engine; it never creates schema or grants.
from app.google_drive_oauth import router as google_drive_oauth_router
from app.photographer_access_recovery import owner_router as access_recovery_owner_router
from app.photographer_access_recovery import public_router as access_recovery_public_router
from app.photographer_onboarding import router as photographer_onboarding_router
from app.photographer_signup import router as photographer_signup_router
from app.photographer_terms import router as photographer_terms_router
from app.photographer_totp import router as photographer_totp_router
from app.photographer_totp_support import router as photographer_totp_support_router
from app.platform_console import router as platform_console_router
from app.system_monitor.routes import router as system_monitor_router
from app.system_monitor.runtime import start_monitor, stop_monitor
from app.system_monitor.telemetry import MonitorMiddleware
from app.tenant_closure_api import router as tenant_closure_api_router
from app.tenant_closure_identity import router as tenant_closure_identity_router

app.include_router(system_monitor_router)
app.include_router(platform_console_router)
app.include_router(google_drive_oauth_router)
app.include_router(photographer_signup_router)
app.include_router(tenant_closure_identity_router)
app.include_router(tenant_closure_api_router)
app.include_router(photographer_terms_router)
app.include_router(photographer_onboarding_router)
app.include_router(photographer_totp_router)
app.include_router(photographer_totp_support_router)
app.include_router(access_recovery_owner_router)
app.include_router(access_recovery_public_router)
app.add_middleware(MonitorMiddleware)


@app.on_event("startup")
def start_system_monitor():
    start_monitor(collect_global=True)


@app.on_event("shutdown")
def stop_system_monitor():
    stop_monitor()
