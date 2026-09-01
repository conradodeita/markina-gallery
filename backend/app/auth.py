"""Autenticação e autorização da Markina Gallery.

O módulo mantém autorização no servidor; o browser recebe apenas um cookie opaco.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    func,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.messaging import WhatsAppConfigurationError, whatsapp_provider_name
from app.whatsapp_delivery import encrypt_otp, otp_encryption_key


def now() -> datetime:
    return datetime.now(UTC)


def expired(value: datetime) -> bool:
    """SQLite retorna timestamps sem fuso; PostgreSQL preserva UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value < now()


def database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./markina-gallery.db")


engine = create_engine(
    database_url(),
    connect_args={"check_same_thread": False} if database_url().startswith("sqlite") else {},
)


if database_url().startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
password_hasher = PasswordHasher()


class Base(DeclarativeBase):
    pass


class Role(StrEnum):
    ADMIN = "admin"
    CLIENT = "client"


class BrandingSettings(Base):
    """Configuração única e segura da marca e dos textos de entrada."""

    __tablename__ = "branding_settings"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    login_title: Mapped[str] = mapped_column(String(120), default="Sua galeria, do seu jeito.")
    login_intro: Mapped[str] = mapped_column(
        String(300),
        default="Entre para acessar fotos, seleções e entregas — ou gerenciar sua operação.",
    )
    login_helper: Mapped[str] = mapped_column(
        String(240), default="Escolha seu tipo de acesso para continuar."
    )
    logo_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    app_icon_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    favicon_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    watermark_text: Mapped[str] = mapped_column(String(120), default="MARKINA • PRÉVIA")
    watermark_font: Mapped[str] = mapped_column(String(80), default="sans-serif")
    watermark_color: Mapped[str] = mapped_column(String(7), default="#FFFFFF")
    watermark_size: Mapped[int] = mapped_column(Integer, default=24)
    watermark_direction: Mapped[str] = mapped_column(String(16), default="diagonal")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AdminUser(Base):
    __tablename__ = "admin_user"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_secret: Mapped[str] = mapped_column(String(128))


class AdminSecurityChallenge(Base):
    """Desafio curto e finalístico para recuperação e ações sensíveis."""

    __tablename__ = "admin_security_challenge"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('password_recovery_otp', 'change_password_otp', 'change_email_otp')"
        ),
        CheckConstraint("attempts >= 0"),
        CheckConstraint("resend_count >= 0"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    purpose: Mapped[str] = mapped_column(String(40), index=True)
    admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_user.id"), nullable=True, index=True
    )
    session_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    subject_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    target_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    encrypted_target: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    resend_count: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AdminActionToken(Base):
    """Token de link: somente o hash é persistido em coluna consultável."""

    __tablename__ = "admin_action_token"
    __table_args__ = (
        CheckConstraint("purpose IN ('password_reset', 'verify_admin_email')"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    target_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    encrypted_target: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EmailDelivery(Base):
    """Outbox de e-mail; destinatário e corpo permanecem no envelope cifrado."""

    __tablename__ = "email_delivery"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        UniqueConstraint("external_message_id"),
        CheckConstraint("kind IN ('password_recovery', 'email_verification', 'security_notice')"),
        CheckConstraint(
            "status IN ('queued', 'processing', 'accepted', 'failed', 'unknown', 'expired')"
        ),
        CheckConstraint("attempts >= 0"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    source_type: Mapped[str] = mapped_column(String(48), index=True)
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    recipient_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
    encrypted_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    external_message_id: Mapped[str | None] = mapped_column(String(192), nullable=True, unique=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class EmailDeliveryAttempt(Base):
    __tablename__ = "email_delivery_attempt"
    __table_args__ = (
        CheckConstraint(
            "result IN ('accepted', 'transient_failure', 'permanent_failure', 'unknown')"
        ),
        CheckConstraint("attempt_number >= 1"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    delivery_id: Mapped[UUID] = mapped_column(ForeignKey("email_delivery.id"), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    result: Mapped[str] = mapped_column(String(24))
    external_message_id: Mapped[str | None] = mapped_column(String(192), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Client(Base):
    __tablename__ = "client"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String(200))
    phone_e164: Mapped[str] = mapped_column(String(16), unique=True, index=True)


class ClientPhone(Base):
    __tablename__ = "client_phone"
    __table_args__ = (
        Index(
            "uq_client_phone_active_verified",
            "phone_e164",
            unique=True,
            sqlite_where=text("active = 1 AND verified_at IS NOT NULL"),
            postgresql_where=text("active AND verified_at IS NOT NULL"),
        ),
        Index(
            "uq_client_phone_one_active_per_client",
            "client_id",
            unique=True,
            sqlite_where=text("active = 1"),
            postgresql_where=text("active"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    phone_e164: Mapped[str] = mapped_column(String(16), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GalleryAccess(Base):
    __tablename__ = "gallery_access"
    __table_args__ = (UniqueConstraint("client_id", "gallery_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    gallery_id: Mapped[UUID] = mapped_column(index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ParentGallery(Base):
    """Galeria pública administrada exclusivamente pelo fotógrafo."""

    __tablename__ = "parent_gallery"
    __table_args__ = (
        CheckConstraint(
            "lifecycle_status IN ('active', 'deleting', 'deleted')",
            name="ck_parent_gallery_lifecycle_status",
        ),
        CheckConstraint(
            "access_mode IN ('standard', 'invite_only', 'collective_protected')",
            name="ck_parent_gallery_access_mode",
        ),
        CheckConstraint(
            "selection_duration_days IS NULL OR selection_duration_days BETWEEN 1 AND 3650",
            name="ck_parent_gallery_selection_duration_days",
        ),
        Index(
            "ix_parent_gallery_lifecycle_created",
            "lifecycle_status",
            "created_at",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    event_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    watermark_text: Mapped[str] = mapped_column(String(120), default="MARKINA • PRÉVIA")
    watermark_font: Mapped[str] = mapped_column(String(80), default="sans-serif")
    watermark_color: Mapped[str] = mapped_column(String(7), default="#FFFFFF")
    watermark_size: Mapped[int] = mapped_column(Integer, default=24)
    watermark_direction: Mapped[str] = mapped_column(String(16), default="diagonal")
    folder_display_mode: Mapped[str] = mapped_column(String(16), default="individual")
    cover_title_font: Mapped[str] = mapped_column(String(80), default="sans-serif")
    cover_title_color: Mapped[str] = mapped_column(String(7), default="#FFFFFF")
    cover_title_size: Mapped[int] = mapped_column(Integer, default=32)
    cover_title_position: Mapped[str] = mapped_column(String(16), default="bottom-left")
    cover_photo_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("photo_asset.id", use_alter=True, name="fk_parent_gallery_cover_photo"),
        nullable=True,
    )
    sales_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    selection_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    favorites_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    comments_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    lifecycle_status: Mapped[str] = mapped_column(String(16), default="active")
    access_mode: Mapped[str] = mapped_column(String(24), default="invite_only")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ParentGalleryRegistration(Base):
    """Registro de entrada pelo link não listado; não concede leitura de fotos."""

    __tablename__ = "parent_gallery_registration"
    __table_args__ = (UniqueConstraint("parent_gallery_id", "client_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("parent_gallery.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PhotoAsset(Base):
    """Arquivo pertencente à Galeria pública; nunca é duplicado para a cliente."""

    __tablename__ = "photo_asset"
    __table_args__ = (
        ForeignKeyConstraint(
            ["folder_id", "parent_gallery_id"],
            ["photo_folder.id", "photo_folder.parent_gallery_id"],
            name="fk_photo_asset_folder_gallery",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("parent_gallery.id"), index=True)
    folder_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512))
    display_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoFolder(Base):
    """Lote de fotos preparado pelo fotógrafo antes de sua liberação."""

    __tablename__ = "photo_folder"
    __table_args__ = (
        UniqueConstraint("parent_gallery_id", "position"),
        UniqueConstraint("id", "parent_gallery_id", name="uq_photo_folder_id_parent"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("parent_gallery.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="preparing", index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class DerivedGallery(Base):
    """Galeria privada pertencente a uma única cliente."""

    __tablename__ = "derived_gallery"
    __table_args__ = (
        Index(
            "ix_derived_gallery_parent_client",
            "parent_gallery_id",
            "client_id",
            unique=True,
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("parent_gallery.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    custom_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    selection_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    favorites_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    comments_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DerivedGalleryPhoto(Base):
    """Referência de uma foto da Galeria pública atribuída à galeria privada."""

    __tablename__ = "derived_gallery_photo"
    __table_args__ = (
        UniqueConstraint(
            "derived_gallery_id",
            "photo_asset_id",
            "origin",
            name="uq_derived_gallery_photo_origin",
        ),
        CheckConstraint(
            "origin IN ('admin', 'client', 'facial')",
            name="ck_derived_gallery_photo_origin",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("derived_gallery.id"), index=True)
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    origin: Mapped[str] = mapped_column(String(16), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoSelection(Base):
    __tablename__ = "photo_selection"
    __table_args__ = (
        UniqueConstraint("derived_gallery_id", "photo_asset_id", "client_id"),
        Index("ix_photo_selection_gallery_client", "derived_gallery_id", "client_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("derived_gallery.id"), index=True)
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoFavorite(Base):
    __tablename__ = "photo_favorite"
    __table_args__ = (UniqueConstraint("derived_gallery_id", "photo_asset_id", "client_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("derived_gallery.id"), index=True)
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoView(Base):
    __tablename__ = "photo_view"
    __table_args__ = (UniqueConstraint("derived_gallery_id", "client_id", "photo_asset_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("derived_gallery.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    first_viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoComment(Base):
    __tablename__ = "photo_comment"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("derived_gallery.id"), index=True)
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SaleOrder(Base):
    __tablename__ = "sale_order"
    __table_args__ = (
        CheckConstraint("payment_status IN ('pending', 'confirmed', 'cancelled')"),
        CheckConstraint("total_cents >= 0"),
        UniqueConstraint("derived_gallery_id", "client_id", "checkout_key"),
        Index(
            "ix_sale_order_parent_payment_status",
            "parent_gallery_id_snapshot",
            "payment_status",
        ),
        Index(
            "ix_sale_order_gallery_client_payment",
            "derived_gallery_id",
            "client_id",
            "payment_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    derived_gallery_id_snapshot: Mapped[UUID] = mapped_column(index=True)
    derived_gallery_name_snapshot: Mapped[str] = mapped_column(String(200))
    parent_gallery_id_snapshot: Mapped[UUID] = mapped_column(index=True)
    parent_gallery_name_snapshot: Mapped[str] = mapped_column(String(200))
    payment_status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    total_cents: Mapped[int] = mapped_column(Integer)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_name_snapshot: Mapped[str | None] = mapped_column(String(200), nullable=True)
    client_phone_snapshot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    price_rule_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sales_message_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_copy_paste_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_qr_code_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_instructions_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    pii_minimized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checkout_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SaleOrderItem(Base):
    __tablename__ = "sale_order_item"
    __table_args__ = (
        UniqueConstraint("sale_order_id", "photo_asset_id"),
        CheckConstraint("unit_price_cents >= 0"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sale_order_id: Mapped[UUID] = mapped_column(ForeignKey("sale_order.id"), index=True)
    photo_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("photo_asset.id", ondelete="SET NULL"), nullable=True, index=True
    )
    photo_asset_id_snapshot: Mapped[UUID] = mapped_column(index=True)
    filename_snapshot: Mapped[str] = mapped_column(String(512))
    checksum_sha256_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_price_cents: Mapped[int] = mapped_column(Integer)


class GalleryLifecycleOperation(Base):
    """Operação durável e auditável sobre o ciclo de vida de uma Galeria pública."""

    __tablename__ = "gallery_lifecycle_operation"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_gallery_lifecycle_operation_idempotency"),
        CheckConstraint(
            "operation_type IN ('delete_parent_gallery', 'unlink_client')",
            name="ck_gallery_lifecycle_operation_type",
        ),
        CheckConstraint(
            "status IN ('queued', 'preparing_history', 'removing_storage', "
            "'removing_records', 'completed', 'failed', 'cancelled')",
            name="ck_gallery_lifecycle_operation_status",
        ),
        CheckConstraint(
            "(operation_type = 'delete_parent_gallery' AND target_client_id IS NULL) OR "
            "(operation_type = 'unlink_client' AND target_client_id IS NOT NULL)",
            name="ck_gallery_lifecycle_operation_target",
        ),
        CheckConstraint("attempts >= 0", name="ck_gallery_lifecycle_operation_attempts"),
        Index(
            "ix_gallery_lifecycle_operation_target_status",
            "target_parent_gallery_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    operation_type: Mapped[str] = mapped_column(String(32), index=True)
    target_parent_gallery_id: Mapped[UUID] = mapped_column(index=True)
    target_client_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    actor_admin_id: Mapped[UUID] = mapped_column(index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    destructive_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class GalleryAccessCapability(Base):
    """Capacidade opaca de acesso; somente o hash do token é persistido."""

    __tablename__ = "gallery_access_capability"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_gallery_access_capability_token_hash"),
        CheckConstraint(
            "scope IN ('public_gallery', 'parent_invite', 'private_invite')",
            name="ck_gallery_access_capability_scope",
        ),
        CheckConstraint(
            "status IN ('active', 'consumed', 'revoked', 'rotated', 'expired')",
            name="ck_gallery_access_capability_status",
        ),
        CheckConstraint(
            "length(token_hash) = 64",
            name="ck_gallery_access_capability_token_hash",
        ),
        CheckConstraint(
            "(scope = 'public_gallery' AND client_id IS NULL AND derived_gallery_id IS NULL) OR "
            "(scope = 'parent_invite' AND client_id IS NOT NULL AND derived_gallery_id IS NULL) OR "
            "(scope = 'private_invite' AND client_id IS NOT NULL AND derived_gallery_id IS NOT NULL)",
            name="ck_gallery_access_capability_target",
        ),
        Index(
            "ix_gallery_access_capability_parent_status",
            "parent_gallery_id",
            "status",
        ),
        Index(
            "uq_gallery_access_capability_active_public",
            "parent_gallery_id",
            unique=True,
            sqlite_where=text("scope = 'public_gallery' AND status = 'active'"),
            postgresql_where=text("scope = 'public_gallery' AND status = 'active'"),
        ),
        Index(
            "uq_gallery_access_capability_active_invite",
            "parent_gallery_id",
            "client_id",
            "scope",
            unique=True,
            sqlite_where=text("scope <> 'public_gallery' AND status = 'active'"),
            postgresql_where=text("scope <> 'public_gallery' AND status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id", ondelete="CASCADE"), index=True
    )
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="CASCADE"), nullable=True, index=True
    )
    client_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("client.id"), nullable=True, index=True
    )
    scope: Mapped[str] = mapped_column(String(24), index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_from_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("gallery_access_capability.id"), nullable=True, index=True
    )
    actor_admin_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CommercialHistoryMedia(Base):
    """Manifesto mínimo de mídia preservada para um item comercial."""

    __tablename__ = "commercial_history_media"
    __table_args__ = (
        UniqueConstraint("sale_order_item_id", name="uq_commercial_history_media_item"),
        CheckConstraint(
            "status IN ('pending', 'preparing', 'ready', 'failed', 'purged')",
            name="ck_commercial_history_media_status",
        ),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_commercial_history_media_size",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sale_order_item_id: Mapped[UUID] = mapped_column(ForeignKey("sale_order_item.id"), index=True)
    preview_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    delivery_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    delivery_reference: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


@event.listens_for(Session, "before_flush")
def _materialize_required_commercial_snapshots(
    session: Session, _flush_context, _instances
) -> None:
    """Garante snapshots em pedidos novos sem confiar em cada consumidor da ORM."""

    for record in session.new:
        if isinstance(record, SaleOrder):
            if record.derived_gallery_id is None:
                if not all(
                    (
                        record.derived_gallery_id_snapshot,
                        record.derived_gallery_name_snapshot,
                        record.parent_gallery_id_snapshot,
                        record.parent_gallery_name_snapshot,
                    )
                ):
                    raise ValueError("Pedido sem galeria operacional exige snapshots completos.")
                continue
            gallery = session.get(DerivedGallery, record.derived_gallery_id)
            parent = session.get(ParentGallery, gallery.parent_gallery_id) if gallery else None
            if not gallery or not parent:
                raise ValueError("Não foi possível materializar o snapshot da galeria.")
            record.derived_gallery_id_snapshot = record.derived_gallery_id_snapshot or gallery.id
            record.derived_gallery_name_snapshot = (
                record.derived_gallery_name_snapshot or gallery.name
            )
            record.parent_gallery_id_snapshot = record.parent_gallery_id_snapshot or parent.id
            record.parent_gallery_name_snapshot = record.parent_gallery_name_snapshot or parent.name
            client = session.get(Client, record.client_id)
            if client:
                record.client_name_snapshot = record.client_name_snapshot or client.full_name
                record.client_phone_snapshot = record.client_phone_snapshot or client.phone_e164
        elif isinstance(record, SaleOrderItem):
            if record.photo_asset_id is None:
                if not record.photo_asset_id_snapshot:
                    raise ValueError("Item sem foto operacional exige snapshot do identificador.")
                continue
            photo = session.get(PhotoAsset, record.photo_asset_id)
            if not photo:
                raise ValueError("Não foi possível materializar o snapshot da foto.")
            record.photo_asset_id_snapshot = record.photo_asset_id_snapshot or photo.id
            record.filename_snapshot = (
                record.filename_snapshot or photo.display_name or photo.filename
            )


class PriceRule(Base):
    __tablename__ = "price_rule"
    __table_args__ = (
        UniqueConstraint("parent_gallery_id", "minimum_quantity"),
        CheckConstraint("minimum_quantity >= 1"),
        CheckConstraint("maximum_quantity IS NULL OR maximum_quantity >= minimum_quantity"),
        CheckConstraint("unit_price_cents >= 0"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("parent_gallery.id"), index=True)
    minimum_quantity: Mapped[int] = mapped_column(Integer)
    maximum_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_price_cents: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PixCheckoutSettings(Base):
    __tablename__ = "pix_checkout_settings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id"), unique=True, index=True
    )
    copy_paste: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_code_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PaymentCommunication(Base):
    __tablename__ = "payment_communication"
    __table_args__ = (
        UniqueConstraint("sale_order_id", "idempotency_key"),
        CheckConstraint("status IN ('pending_review', 'confirmed', 'refused')"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sale_order_id: Mapped[UUID] = mapped_column(ForeignKey("sale_order.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20), default="pending_review", index=True)
    decided_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_user.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PaymentMessageTemplate(Base):
    __tablename__ = "payment_message_template"
    __table_args__ = (UniqueConstraint("kind"), CheckConstraint("kind IN ('confirmed', 'refused')"))
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(16))
    body: Mapped[str] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PaymentNotificationOutbox(Base):
    __tablename__ = "payment_notification_outbox"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        CheckConstraint("template_kind IN ('photographer_reported', 'confirmed', 'refused')"),
        CheckConstraint("status IN ('queued', 'processing', 'sent', 'failed')"),
        CheckConstraint("attempts >= 0"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_communication_id: Mapped[UUID] = mapped_column(
        ForeignKey("payment_communication.id"), index=True
    )
    recipient_phone: Mapped[str] = mapped_column(String(32))
    template_kind: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class WhatsAppChannelSettings(Base):
    """Estado operacional não secreto do canal WhatsApp por ambiente."""

    __tablename__ = "whatsapp_channel_settings"
    __table_args__ = (
        UniqueConstraint("environment"),
        CheckConstraint(
            "status IN ('sandbox', 'pending_pairing', 'connecting', 'ready', "
            "'mismatch', 'disconnected', 'error')"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    environment: Mapped[str] = mapped_column(String(32), index=True)
    expected_phone_e164: Mapped[str | None] = mapped_column(String(16), nullable=True)
    connected_phone_e164: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="sandbox", index=True)
    last_error: Mapped[str | None] = mapped_column(String(240), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class WhatsAppDelivery(Base):
    """Entrega genérica; conteúdo sensível nunca é persistido em texto puro."""

    __tablename__ = "whatsapp_delivery"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        UniqueConstraint("external_message_id"),
        CheckConstraint("kind IN ('otp', 'payment')"),
        CheckConstraint(
            "status IN ('queued', 'processing', 'accepted', 'delivered', 'read', "
            "'failed', 'unknown', 'expired')"
        ),
        CheckConstraint("attempts >= 0"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    source_type: Mapped[str] = mapped_column(String(48), index=True)
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    recipient_phone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    recipient_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    template_kind: Mapped[str] = mapped_column(String(48))
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
    encrypted_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    external_message_id: Mapped[str | None] = mapped_column(String(192), nullable=True, unique=True)
    provider_status: Mapped[str | None] = mapped_column(String(48), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(240), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class WhatsAppDeliveryAttempt(Base):
    __tablename__ = "whatsapp_delivery_attempt"
    __table_args__ = (
        CheckConstraint(
            "result IN ('accepted', 'transient_failure', 'permanent_failure', 'unknown')"
        ),
        CheckConstraint("attempt_number >= 1"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    delivery_id: Mapped[UUID] = mapped_column(ForeignKey("whatsapp_delivery.id"), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    result: Mapped[str] = mapped_column(String(24))
    external_message_id: Mapped[str | None] = mapped_column(String(192), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WhatsAppWebhookReceipt(Base):
    __tablename__ = "whatsapp_webhook_receipt"
    __table_args__ = (UniqueConstraint("fingerprint"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    event_type: Mapped[str] = mapped_column(String(64))
    external_message_id: Mapped[str | None] = mapped_column(String(192), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MediaDerivative(Base):
    """Derivado local de uma foto; paths nunca são recebidos do navegador."""

    __tablename__ = "media_derivative"
    __table_args__ = (
        UniqueConstraint("photo_asset_id", "variant"),
        CheckConstraint("variant IN ('thumbnail', 'client_preview', 'admin_preview')"),
        CheckConstraint("status IN ('queued', 'ready', 'failed')"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    variant: Mapped[str] = mapped_column(String(32))
    relative_path: Mapped[str | None] = mapped_column(String(1024), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class MediaJob(Base):
    """Job retomável para geração de derivados, isolado por foto e tipo."""

    __tablename__ = "media_job"
    __table_args__ = (
        UniqueConstraint("photo_asset_id", "kind"),
        CheckConstraint("kind IN ('generate_derivatives')"),
        CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed')"),
        CheckConstraint("attempts >= 0"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="generate_derivatives")
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AuthChallenge(Base):
    __tablename__ = "auth_challenge"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    subject: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    subject_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    secret_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    resend_count: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_gallery_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    gallery_capability_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    return_to: Mapped[str | None] = mapped_column(String(512), nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(200), nullable=True)


class AuthSession(Base):
    __tablename__ = "auth_session"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16), index=True)
    subject_id: Mapped[UUID] = mapped_column(index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_event"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event: Mapped[str] = mapped_column(String(80), index=True)
    subject: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ClientChallengeInput(BaseModel):
    full_name: str = Field(min_length=3, max_length=200)
    phone: str = Field(min_length=8, max_length=32)


class ChallengeVerification(BaseModel):
    challenge_id: UUID
    code: str = Field(pattern=r"^\d{6}$")


class ChallengeResendInput(BaseModel):
    challenge_id: UUID


class AdminPasswordInput(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=1024)


def normalize_e164(phone: str) -> str:
    compact = re.sub(r"[\s().-]", "", phone)
    if not re.fullmatch(r"\+[1-9]\d{7,14}", compact):
        raise HTTPException(status_code=422, detail="Informe um telefone internacional válido.")
    return compact


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


COMMON_ADMIN_PASSWORDS = {
    "123456789012",
    "administrador",
    "markinagallery",
    "password1234",
    "senha123456",
    "senha12345678",
}


def validate_admin_password(
    password: str,
    *,
    email: str,
    current_password_hash: str | None = None,
) -> None:
    """Aplica a mesma política antes de qualquer hash administrativo."""

    if not 12 <= len(password) <= 128:
        raise ValueError("A senha deve ter entre 12 e 128 caracteres.")
    normalized = password.strip().casefold()
    if normalized in COMMON_ADMIN_PASSWORDS:
        raise ValueError("Escolha uma senha menos comum.")
    email_local = email.strip().casefold().partition("@")[0]
    compact_password = re.sub(r"\s+", "", normalized)
    if len(email_local) >= 4 and email_local in compact_password:
        raise ValueError("A senha não pode conter o e-mail da conta.")
    if current_password_hash:
        try:
            if password_hasher.verify(current_password_hash, password):
                raise ValueError("A nova senha deve ser diferente da senha atual.")
        except VerificationError:
            pass


def pii_fingerprint(value: str) -> str:
    """Produz identificador estável não reversível usando segredo do servidor."""

    salt = os.getenv("AUTH_PII_FINGERPRINT_SALT", "").strip()
    if not salt:
        if os.getenv("APP_ENV", "development") != "development":
            raise RuntimeError("AUTH_PII_FINGERPRINT_SALT é obrigatório fora de desenvolvimento.")
        salt = "markina-development-only-pii-fingerprint"
    return hmac.new(salt.encode(), value.encode(), hashlib.sha256).hexdigest()


def challenge_fingerprint(challenge: AuthChallenge) -> str:
    if challenge.subject_fingerprint:
        return challenge.subject_fingerprint
    if challenge.subject:
        challenge.subject_fingerprint = pii_fingerprint(challenge.subject)
        return challenge.subject_fingerprint
    return token_hash(str(challenge.id))


def audit(db: Session, event: str, subject: str) -> None:
    db.add(AuditEvent(event=event, subject=subject))


def enforce_rate_limit(db: Session, scope: str, subject: str, ip_address: str) -> None:
    """Cinco ações por identidade e IP em uma janela de quinze minutos."""
    key = f"{scope}:{subject}:{ip_address}"
    since = now() - timedelta(minutes=int(os.getenv("AUTH_RATE_LIMIT_WINDOW_MINUTES", "15")))
    count = (
        db.scalar(
            select(func.count()).where(
                AuditEvent.event == "rate_limited.request",
                AuditEvent.subject == key,
                AuditEvent.created_at >= since,
            )
        )
        or 0
    )
    if count >= int(os.getenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "5")):
        audit(db, "rate_limited.rejected", key)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Tente novamente mais tarde."
        )
    audit(db, "rate_limited.request", key)


def neutral_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Não foi possível concluir a autenticação."
    )


def create_challenge(
    db: Session, kind: str, subject: str, code: str | None = None
) -> tuple[AuthChallenge, str]:
    code = code or f"{secrets.randbelow(1_000_000):06d}"
    challenge = AuthChallenge(
        kind=kind,
        subject=subject,
        subject_fingerprint=pii_fingerprint(subject) if kind == "client_otp" else None,
        secret_hash=token_hash(code),
        expires_at=now() + timedelta(minutes=10),
    )
    db.add(challenge)
    audit(
        db,
        f"{kind}.requested",
        challenge.subject_fingerprint if kind == "client_otp" else subject,
    )
    db.commit()
    return challenge, code


def enqueue_client_otp_delivery(
    db: Session, challenge: AuthChallenge, code: str
) -> WhatsAppDelivery:
    """Persiste uma entrega OTP sem depender da rede ou guardar o código aberto."""
    key = f"otp:{challenge.id}:{challenge.resend_count}"
    existing = db.scalar(select(WhatsAppDelivery).where(WhatsAppDelivery.idempotency_key == key))
    if existing:
        return existing
    delivery = WhatsAppDelivery(
        kind="otp",
        source_type="auth_challenge",
        source_id=str(challenge.id),
        recipient_phone=challenge.subject,
        recipient_fingerprint=challenge_fingerprint(challenge),
        template_kind="client_otp",
        idempotency_key=key,
        expires_at=challenge.expires_at,
    )
    try:
        cipher_key = otp_encryption_key()
        delivery.encrypted_payload = encrypt_otp(code, key=cipher_key, context=key)
    except WhatsAppConfigurationError:
        if whatsapp_provider_name() == "sandbox":
            instant = now()
            delivery.status = "accepted"
            delivery.provider_status = "accepted"
            delivery.external_message_id = (
                f"sandbox:{hashlib.sha256(key.encode()).hexdigest()[:24]}"
            )
            delivery.accepted_at = instant
            delivery.last_error = None
        else:
            delivery.status = "failed"
            delivery.last_error = "Configuração segura do OTP indisponível."
    db.add(delivery)
    audit(db, "client_otp.delivery_queued", str(challenge.id))
    db.commit()
    return delivery


def resend_client_challenge(db: Session, challenge_id: UUID, ip_address: str) -> AuthChallenge:
    challenge = db.get(AuthChallenge, challenge_id)
    if (
        not challenge
        or challenge.kind != "client_otp"
        or challenge.used_at
        or expired(challenge.expires_at)
        or challenge.resend_count >= 3
    ):
        audit(db, "client_otp.resend_rejected", str(challenge_id))
        db.commit()
        raise neutral_error()
    if not challenge.subject:
        audit(db, "client_otp.resend_rejected", str(challenge_id))
        db.commit()
        raise neutral_error()
    fingerprint = challenge_fingerprint(challenge)
    enforce_rate_limit(db, "client_otp.resend", fingerprint, ip_address)
    code = f"{secrets.randbelow(1_000_000):06d}"
    for delivery in db.scalars(
        select(WhatsAppDelivery).where(
            WhatsAppDelivery.kind == "otp",
            WhatsAppDelivery.source_id == str(challenge.id),
            WhatsAppDelivery.status.in_(("queued", "processing", "unknown")),
        )
    ):
        delivery.status = "expired"
        delivery.encrypted_payload = None
        delivery.updated_at = now()
    challenge.secret_hash = token_hash(code)
    challenge.resend_count += 1
    audit(db, "client_otp.resent", fingerprint)
    db.commit()
    enqueue_client_otp_delivery(db, challenge, code)
    return challenge


def consume_challenge(db: Session, challenge_id: UUID, kind: str, code: str) -> AuthChallenge:
    challenge = db.get(AuthChallenge, challenge_id)
    if (
        not challenge
        or challenge.kind != kind
        or challenge.used_at
        or expired(challenge.expires_at)
        or challenge.attempts >= 5
    ):
        audit(db, f"{kind}.rejected", str(challenge_id))
        db.commit()
        raise neutral_error()
    challenge.attempts += 1
    if not secrets.compare_digest(challenge.secret_hash, token_hash(code)):
        audit(
            db,
            f"{kind}.failed",
            challenge_fingerprint(challenge)
            if kind == "client_otp"
            else challenge.subject or str(challenge.id),
        )
        if kind == "client_otp" and challenge.attempts >= 5:
            minimize_client_challenge_pii(db, challenge)
        db.commit()
        raise neutral_error()
    challenge.used_at = now()
    audit(
        db,
        f"{kind}.validated",
        challenge_fingerprint(challenge)
        if kind == "client_otp"
        else challenge.subject or str(challenge.id),
    )
    return challenge


def minimize_client_challenge_pii(db: Session, challenge: AuthChallenge) -> None:
    """Apaga PII transitória depois do consumo ou de uma negação terminal."""

    fingerprint = challenge_fingerprint(challenge)
    challenge.subject = None
    challenge.client_name = None
    instant = now()
    for delivery in db.scalars(
        select(WhatsAppDelivery).where(
            WhatsAppDelivery.kind == "otp",
            WhatsAppDelivery.source_type == "auth_challenge",
            WhatsAppDelivery.source_id == str(challenge.id),
        )
    ):
        delivery.recipient_fingerprint = delivery.recipient_fingerprint or fingerprint
        delivery.recipient_phone = None
        delivery.encrypted_payload = None
        if delivery.status in {"queued", "processing", "unknown"}:
            delivery.status = "expired"
        delivery.updated_at = instant


def cleanup_expired_client_otp_pii(db: Session, *, current_time: datetime | None = None) -> int:
    """Minimiza desafios abandonados após a janela curta configurada."""

    instant = current_time or now()
    retention = timedelta(minutes=max(0, int(os.getenv("AUTH_OTP_PII_RETENTION_MINUTES", "60"))))
    cutoff = instant - retention
    challenges = list(
        db.scalars(
            select(AuthChallenge).where(
                AuthChallenge.kind == "client_otp",
                AuthChallenge.subject.is_not(None),
                AuthChallenge.expires_at <= cutoff,
            )
        )
    )
    for challenge in challenges:
        minimize_client_challenge_pii(db, challenge)
    if challenges:
        audit(db, "client_otp.pii_cleanup", f"count:{len(challenges)}")
        db.commit()
    return len(challenges)


def create_session(db: Session, response: Response, role: Role, subject_id: UUID) -> str:
    raw_token = secrets.token_urlsafe(48)
    active_sessions = db.scalars(
        select(AuthSession).where(
            AuthSession.role == role.value,
            AuthSession.subject_id == subject_id,
            AuthSession.revoked_at.is_(None),
        )
    )
    for active_session in active_sessions:
        active_session.revoked_at = now()
        audit(db, "session.rotated", str(subject_id))
    session = AuthSession(
        token_hash=token_hash(raw_token),
        role=role.value,
        subject_id=subject_id,
        expires_at=now() + timedelta(days=int(os.getenv("SESSION_DAYS", "7"))),
    )
    db.add(session)
    audit(db, "session.created", str(subject_id))
    db.commit()
    response.set_cookie(
        os.getenv("SESSION_COOKIE_NAME", "markina_session"),
        raw_token,
        httponly=True,
        secure=os.getenv("APP_ENV", "development") != "development",
        samesite="lax",
        max_age=int(os.getenv("SESSION_DAYS", "7")) * 24 * 60 * 60,
        path="/",
    )
    return raw_token


def current_session(request: Request, required_role: Role | None = None) -> AuthSession:
    token = request.cookies.get(os.getenv("SESSION_COOKIE_NAME", "markina_session"))
    if not token:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    with SessionLocal() as db:
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        if (
            not session
            or session.revoked_at
            or expired(session.expires_at)
            or (required_role and session.role != required_role.value)
        ):
            raise HTTPException(status_code=403, detail="Acesso negado.")
        db.expunge(session)
        return session


def revoke_subject_sessions(db: Session, role: str, subject_id: UUID) -> None:
    for session in db.scalars(
        select(AuthSession).where(
            AuthSession.role == role,
            AuthSession.subject_id == subject_id,
            AuthSession.revoked_at.is_(None),
        )
    ):
        session.revoked_at = now()
    audit(db, "session.revoke_all", str(subject_id))
