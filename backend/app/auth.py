"""Autenticação e autorização do Pick-your-Pic.

O módulo mantém autorização no servidor; o browser recebe apenas um cookie opaco.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    func,
    select,
    text,
)
from sqlalchemy import (
    inspect as sa_inspect,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.orm.attributes import flag_modified

from app.messaging import WhatsAppConfigurationError
from app.ownership_schema import apply_ownership_constraints
from app.product_brand import DEFAULT_WATERMARK_TEXT
from app.system_monitor.pool import MonitoredQueuePool
from app.totp_crypto import (
    TotpSecretCipher,
    TotpSecretError,
    legacy_totp_dual_write_enabled,
)
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
    **({"poolclass": MonitoredQueuePool} if database_url().startswith("postgresql") else {}),
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
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint(
            "watermark_opacity BETWEEN 10 AND 100",
            name="ck_branding_watermark_opacity",
        ),
        CheckConstraint(
            "watermark_position IN ('top-left', 'top-center', 'top-right', "
            "'middle-left', 'middle-center', 'middle-right', "
            "'bottom-left', 'bottom-center', 'bottom-right')",
            name="ck_branding_watermark_position",
        ),
    )
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
    watermark_text: Mapped[str] = mapped_column(String(120), default=DEFAULT_WATERMARK_TEXT)
    watermark_font: Mapped[str] = mapped_column(String(80), default="sans-serif")
    watermark_color: Mapped[str] = mapped_column(String(7), default="#FFFFFF")
    watermark_size: Mapped[int] = mapped_column(Integer, default=24)
    watermark_direction: Mapped[str] = mapped_column(String(16), default="diagonal")
    watermark_opacity: Mapped[int] = mapped_column(Integer, default=42)
    watermark_position: Mapped[str] = mapped_column(String(24), default="middle-center")
    watermark_shadow: Mapped[bool] = mapped_column(Boolean, default=True)
    watermark_security_lines: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AdminUser(Base):
    __tablename__ = "admin_user"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    _totp_secret_legacy: Mapped[str | None] = mapped_column(
        "totp_secret", String(128), nullable=True
    )
    _totp_secret_envelope: Mapped[str | None] = mapped_column(
        "totp_secret_envelope", String(768), nullable=True
    )
    totp_last_used_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tenant_memberships: Mapped[list[TenantAdmin]] = relationship(cascade="all, delete-orphan")

    @property
    def totp_secret(self) -> str:
        if "_totp_secret_envelope" in sa_inspect(self).expired_attributes:
            _ = self._totp_secret_envelope
        value = getattr(self, "_totp_secret_value", None)
        if not value:
            raise TotpSecretError()
        if (sa_inspect(self).persistent
                and getattr(self, "_totp_secret_needs_encryption", False)):
            flag_modified(self, "_totp_secret_envelope")
        return value

    @totp_secret.setter
    def totp_secret(self, value: str) -> None:
        self._totp_secret_value = value
        self._totp_secret_needs_encryption = True
        self._totp_secret_envelope = "pending-encryption"


class AdminTotpEnrollment(Base):
    """Material temporário cifrado, vinculado à sessão que inicia o fator."""
    __tablename__ = "admin_totp_enrollment"
    __table_args__ = (
        CheckConstraint("attempts >= 0 AND attempts <= 5"),
        UniqueConstraint("id", "tenant_id"),
        UniqueConstraint("tenant_id", "admin_user_id"),
        ForeignKeyConstraint(["admin_user_id", "tenant_id"], ["tenant_admin.admin_user_id", "tenant_admin.tenant_id"]),
        ForeignKeyConstraint(["session_id", "tenant_id"], ["auth_session.id", "auth_session.tenant_id"], ondelete="CASCADE"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"))
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    session_id: Mapped[UUID] = mapped_column()
    secret_envelope: Mapped[str | None] = mapped_column(String(768), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminTotpRecoveryCode(Base):
    __tablename__ = "admin_totp_recovery_code"
    __table_args__ = (
        UniqueConstraint("admin_user_id", "code_selector", name="uq_admin_totp_recovery_selector"),
        Index("ix_admin_totp_recovery_active", "admin_user_id", "used_at", "revoked_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id", ondelete="CASCADE"))
    code_selector: Mapped[str] = mapped_column(String(4), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _decode_persisted_totp(admin: AdminUser) -> None:
    legacy = admin._totp_secret_legacy
    envelope = admin._totp_secret_envelope
    if not admin.totp_enabled and legacy is None and envelope is None:
        admin._totp_secret_value = None
        admin._totp_secret_needs_encryption = False
        return
    dual_write = legacy_totp_dual_write_enabled()

    if envelope is not None and not TotpSecretCipher.is_envelope(envelope):
        raise TotpSecretError()

    if dual_write and isinstance(legacy, str) and legacy and len(legacy) <= 128:
        needs_encryption = True
        if envelope is not None:
            current = TotpSecretCipher.from_environment().decrypt(
                envelope, admin_id=admin.id
            )
            needs_encryption = current != legacy
        admin._totp_secret_value = legacy
        admin._totp_secret_needs_encryption = needs_encryption
        if needs_encryption:
            flag_modified(admin, "_totp_secret_envelope")
        return

    if envelope is not None:
        admin._totp_secret_value = TotpSecretCipher.from_environment().decrypt(
            envelope, admin_id=admin.id
        )
        admin._totp_secret_needs_encryption = False
        return

    # Uma linha recém-escrita por binário legado durante a expansão ainda pode
    # não ter envelope; ao ler, a aplicação nova cifra antes do próximo flush.
    if isinstance(legacy, str) and legacy and len(legacy) <= 128:
        admin._totp_secret_value = legacy
        admin._totp_secret_needs_encryption = True
        flag_modified(admin, "_totp_secret_envelope")
        return

    raise TotpSecretError()


@event.listens_for(AdminUser, "load")
def _decrypt_admin_totp_on_load(admin: AdminUser, _context) -> None:
    _decode_persisted_totp(admin)


@event.listens_for(AdminUser, "refresh")
def _decrypt_admin_totp_on_refresh(admin: AdminUser, _context, attrs) -> None:
    if (attrs is None or "_totp_secret_envelope" in attrs
            or "_totp_secret_legacy" in attrs or "totp_secret" in attrs
            or "totp_secret_envelope" in attrs):
        _decode_persisted_totp(admin)


class InstallationOperator(Base):
    """Privilégio técnico explícito; nenhum acesso comercial adicional."""
    __tablename__ = "installation_operator"
    __table_args__ = (
        CheckConstraint("length(authorization_reference) BETWEEN 1 AND 120", name="ck_operator_reference"),
        CheckConstraint("NOT active OR revoked_at IS NULL", name="ck_operator_active_revocation"),
    )
    admin_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean)
    authorization_reference: Mapped[str] = mapped_column(String(120))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FacialEmbeddingExperimentSetting(Base):
    """Metadado Gemma histórico mapeado para compatibilidade com o schema publicado."""

    __tablename__ = "facial_embedding_experiment_setting"
    __table_args__ = (
        CheckConstraint("singleton = 1", name="ck_facial_embedding_experiment_singleton"),
        CheckConstraint("mode = 'shadow'", name="ck_facial_embedding_experiment_mode"),
    )

    singleton: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    mode: Mapped[str] = mapped_column(String(16), default="shadow", server_default="shadow")
    model_revision: Mapped[str] = mapped_column(
        String(64), default="914f7f89142e33e77833254d9c9b90c3cef7303b",
        server_default="914f7f89142e33e77833254d9c9b90c3cef7303b",
    )
    updated_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_user.id"), nullable=True,
    )
    worker_last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    enabled_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Tenant(Base):
    __tablename__ = "tenant"
    __table_args__ = (
        UniqueConstraint("canonical_host", name="uq_tenant_canonical_host"),
        CheckConstraint(
            "canonical_host_status IS NULL OR (canonical_host IS NOT NULL "
            "AND canonical_host_status IN ('reserved', 'ready'))",
            name="ck_tenant_canonical_host_status",
        ),
        CheckConstraint("status IN ('active', 'suspended')", name="ck_tenant_status"),
        CheckConstraint("lifecycle IN ('open', 'closing', 'closed')", name="ck_tenant_lifecycle"),
        CheckConstraint(
            "canonical_host IS NULL OR (canonical_host = lower(canonical_host) "
            "AND length(canonical_host) BETWEEN 1 AND 253 "
            "AND canonical_host NOT LIKE '%/%' AND canonical_host NOT LIKE '%:%')",
            name="ck_tenant_canonical_host",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(String(16), default="active")
    lifecycle: Mapped[str] = mapped_column(String(16), default="open", server_default="open")
    photographer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    canonical_host: Mapped[str | None] = mapped_column(String(253), nullable=True)
    canonical_host_status: Mapped[str | None] = mapped_column(String(12), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TenantClosureRequest(Base):
    """Histórico por ciclo; encerramento não altera suspensão nem saldo."""

    __tablename__ = "tenant_closure_request"
    __table_args__ = (
        UniqueConstraint("tenant_id", "request_id", name="uq_tenant_closure_request_key"),
        UniqueConstraint("id", "tenant_id", name="uq_tenant_closure_request_owner"),
        CheckConstraint("state IN ('closing', 'closed', 'reopened')", name="ck_tenant_closure_state"),
        CheckConstraint("balance_snapshot >= 0", name="ck_tenant_closure_balance"),
        CheckConstraint("state = 'closing' OR closed_at IS NOT NULL", name="ck_tenant_closure_closed_at"),
        CheckConstraint("state != 'reopened' OR reopened_at IS NOT NULL", name="ck_tenant_closure_reopened_at"),
        CheckConstraint(
            "biometric_cleanup_completed_at IS NULL OR biometric_cleanup_started_at IS NOT NULL",
            name="ck_tenant_closure_biometric_cleanup_order",
        ),
        Index("uq_tenant_closure_pending", "tenant_id", unique=True,
              postgresql_where=text("state = 'closing'"), sqlite_where=text("state = 'closing'")),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    request_id: Mapped[UUID] = mapped_column()
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"))
    state: Mapped[str] = mapped_column(String(16), default="closing")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terms_version: Mapped[str] = mapped_column(String(80))
    terms_sha256: Mapped[str] = mapped_column(String(64))
    balance_snapshot: Mapped[int] = mapped_column(BigInteger)
    balance_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    biometric_cleanup_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    biometric_cleanup_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )


class TenantClosureRecoveryBatch(Base):
    __tablename__ = "tenant_closure_recovery_batch"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_closure_recovery_batch_owner"),
        UniqueConstraint("tenant_id", "request_id", name="uq_closure_recovery_batch_key"),
        ForeignKeyConstraint(["closure_request_id", "tenant_id"],
                             ["tenant_closure_request.id", "tenant_closure_request.tenant_id"],
                             name="fk_closure_recovery_batch_closure"),
        CheckConstraint("duration_days IN (7, 14, 30)", name="ck_closure_recovery_batch_duration"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    closure_request_id: Mapped[UUID] = mapped_column()
    requested_by_owner_admin_id: Mapped[UUID] = mapped_column(ForeignKey("platform_owner.admin_user_id"))
    request_id: Mapped[UUID] = mapped_column()
    duration_days: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TenantClosureRecoveryItem(Base):
    __tablename__ = "tenant_closure_recovery_item"
    __table_args__ = (
        UniqueConstraint("batch_id", "cycle_id", name="uq_closure_recovery_item_cycle"),
        ForeignKeyConstraint(["batch_id", "tenant_id"],
                             ["tenant_closure_recovery_batch.id", "tenant_closure_recovery_batch.tenant_id"],
                             name="fk_closure_recovery_item_batch"),
        ForeignKeyConstraint(["operation_id", "cycle_id", "tenant_id"],
                             ["media_archive_operation.id", "media_archive_operation.cycle_id", "media_archive_operation.tenant_id"],
                             name="fk_closure_recovery_item_operation"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    batch_id: Mapped[UUID] = mapped_column(index=True)
    cycle_id: Mapped[UUID] = mapped_column()
    operation_id: Mapped[UUID] = mapped_column()


class TenantClosureMediaDeletionBatch(Base):
    """Recibo agregado da exclusão explícita da mídia fria de um encerramento."""

    __tablename__ = "tenant_closure_media_deletion_batch"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_closure_media_deletion_batch_owner"),
        UniqueConstraint("tenant_id", "request_id", name="uq_closure_media_deletion_batch_key"),
        UniqueConstraint("closure_request_id", name="uq_closure_media_deletion_batch_closure"),
        ForeignKeyConstraint(
            ["closure_request_id", "tenant_id"],
            ["tenant_closure_request.id", "tenant_closure_request.tenant_id"],
            name="fk_closure_media_deletion_batch_closure",
        ),
        CheckConstraint(
            "state IN ('queued', 'processing', 'attention_required', "
            "'reconciliation_required', 'completed')",
            name="ck_closure_media_deletion_batch_state",
        ),
        CheckConstraint("object_count >= 0", name="ck_closure_media_deletion_batch_objects"),
        CheckConstraint(
            "verified_deleted_object_count >= 0 "
            "AND verified_deleted_object_count <= object_count",
            name="ck_closure_media_deletion_batch_deleted_objects",
        ),
        CheckConstraint("total_bytes >= 0", name="ck_closure_media_deletion_batch_bytes"),
        CheckConstraint(
            "length(inventory_sha256) = 64",
            name="ck_closure_media_deletion_batch_inventory_sha256",
        ),
        Index(
            "ix_closure_media_deletion_batch_tenant_state",
            "tenant_id", "state", "requested_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    closure_request_id: Mapped[UUID] = mapped_column()
    requested_by_owner_admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_owner.admin_user_id"),
    )
    request_id: Mapped[UUID] = mapped_column()
    state: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    inventory_sha256: Mapped[str] = mapped_column(String(64))
    object_count: Mapped[int] = mapped_column(Integer, default=0)
    verified_deleted_object_count: Mapped[int] = mapped_column(Integer, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class TenantClosureMediaDeletionItem(Base):
    """Vínculo tenant-scoped entre lote, ciclo e operação delete_remote."""

    __tablename__ = "tenant_closure_media_deletion_item"
    __table_args__ = (
        UniqueConstraint("batch_id", "cycle_id", name="uq_closure_media_deletion_item_cycle"),
        UniqueConstraint("operation_id", name="uq_closure_media_deletion_item_operation"),
        ForeignKeyConstraint(
            ["batch_id", "tenant_id"],
            ["tenant_closure_media_deletion_batch.id", "tenant_closure_media_deletion_batch.tenant_id"],
            name="fk_closure_media_deletion_item_batch",
        ),
        ForeignKeyConstraint(
            ["operation_id", "cycle_id", "tenant_id"],
            ["media_archive_operation.id", "media_archive_operation.cycle_id", "media_archive_operation.tenant_id"],
            name="fk_closure_media_deletion_item_operation",
        ),
        Index("ix_closure_media_deletion_item_batch", "tenant_id", "batch_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    batch_id: Mapped[UUID] = mapped_column(index=True)
    cycle_id: Mapped[UUID] = mapped_column()
    operation_id: Mapped[UUID] = mapped_column()


class PhotographerSignup(Base):
    """Candidatura separada: ainda não é identidade administrativa ou tenant."""
    __tablename__ = "photographer_signup"
    __table_args__ = (
        CheckConstraint("state IN ('email_pending','credentials_pending','active','expired','cancelled')", name="ck_photographer_signup_state"),
        CheckConstraint("attempts >= 0 AND attempts <= 5", name="ck_photographer_signup_attempts"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    public_request_id: Mapped[UUID] = mapped_column(unique=True, default=uuid4)
    photographer_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    state: Mapped[str] = mapped_column(String(24), default="email_pending")
    otp_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    otp_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    reserved_admin_id: Mapped[UUID] = mapped_column(default=uuid4)
    reserved_tenant_id: Mapped[UUID] = mapped_column(default=uuid4)
    setup_digest: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    setup_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    totp_envelope: Mapped[str | None] = mapped_column(String(512), nullable=True)
    adult_attested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_tenant_id: Mapped[UUID | None] = mapped_column(ForeignKey("tenant.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PhotographerBusinessProfile(Base):
    """Identificação contratual protegida, separada dos dados do checkout."""
    __tablename__ = "photographer_business_profile"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_photographer_business_profile_tenant"),
        CheckConstraint("length(full_name) >= 2", name="ck_photographer_profile_name"),
        CheckConstraint(
            "(cpf_fingerprint IS NULL AND cpf_fingerprint_key_version IS NULL) OR "
            "(cpf_fingerprint IS NOT NULL AND cpf_fingerprint_key_version IS NOT NULL "
            "AND length(cpf_fingerprint_key_version) BETWEEN 1 AND 40)",
            name="ck_photographer_profile_fingerprint_key_version",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), unique=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    cpf_envelope: Mapped[str | None] = mapped_column(String(768), nullable=True)
    cpf_fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    cpf_fingerprint_key_version: Mapped[str | None] = mapped_column(
        String(40), default="legacy-v0", server_default="legacy-v0", nullable=True,
    )
    address_envelope: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PhotographerTermsAcceptance(Base):
    """Protocolo de aceite de teste/operacional; append-only."""
    __tablename__ = "photographer_terms_acceptance"
    __table_args__ = (
        UniqueConstraint("tenant_id", "terms_version", name="uq_photographer_terms_version"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), index=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    terms_version: Mapped[str] = mapped_column(String(80))
    terms_text: Mapped[str] = mapped_column(Text)
    terms_sha256: Mapped[str] = mapped_column(String(64))
    provider_identity: Mapped[str] = mapped_column(String(520))
    photographer_identity: Mapped[str] = mapped_column(String(600))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    environment: Mapped[str] = mapped_column(String(32))


class PhotographerTermsDraft(Base):
    """Rascunho global editável pelo proprietário; não se torna vigente ao salvar."""
    __tablename__ = "photographer_terms_draft"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_photographer_terms_draft_singleton"),
        CheckConstraint("length(template_text) BETWEEN 1 AND 50000", name="ck_photographer_terms_draft_length"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    revision: Mapped[UUID] = mapped_column(default=uuid4)
    template_text: Mapped[str] = mapped_column(Text)
    provider_legal_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    updated_by_admin_id: Mapped[UUID | None] = mapped_column(ForeignKey("admin_user.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PhotographerTermsVersion(Base):
    """Versões publicadas dos Termos são append-only no banco."""
    __tablename__ = "photographer_terms_version"
    __table_args__ = (
        UniqueConstraint("terms_version", name="uq_photographer_terms_published_version"),
        CheckConstraint("length(template_sha256) = 64", name="ck_photographer_terms_template_sha256"),
        CheckConstraint("length(template_text) BETWEEN 1 AND 50000", name="ck_photographer_terms_template_length"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version_number: Mapped[int] = mapped_column(Integer, unique=True)
    terms_version: Mapped[str] = mapped_column(String(80))
    template_text: Mapped[str] = mapped_column(Text)
    template_sha256: Mapped[str] = mapped_column(String(64))
    provider_legal_name: Mapped[str] = mapped_column(String(160))
    provider_contact_email: Mapped[str] = mapped_column(String(320))
    published_by_admin_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GoogleDriveOAuthAttempt(Base):
    """Tentativa curta de OAuth, ligada à identidade owner e ao PKCE cifrado."""
    __tablename__ = "google_drive_oauth_attempt"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_admin_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), index=True)
    auth_session_id: Mapped[UUID] = mapped_column(ForeignKey("auth_session.id"), index=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    state_digest: Mapped[str] = mapped_column(String(64), unique=True)
    verifier_envelope: Mapped[dict] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GoogleDriveConnection(Base):
    """Conexão global do proprietário; refresh token cifrado fora de tabelas comuns."""
    __tablename__ = "google_drive_connection"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), unique=True)
    connected_by_admin_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"))
    refresh_token_envelope: Mapped[dict] = mapped_column(JSON)
    scopes: Mapped[str] = mapped_column(String(256), default="https://www.googleapis.com/auth/drive.file")
    state: Mapped[str] = mapped_column(String(32), default="connected")
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quota_limit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    quota_usage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    quota_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (CheckConstraint("state IN ('connected','revoked','reauthorization_required')",
                                      name="ck_google_drive_connection_state"),)


class TenantAdmin(Base):
    __tablename__ = "tenant_admin"
    __table_args__ = (UniqueConstraint("tenant_id", "admin_user_id", name="uq_tenant_admin"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    admin_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TenantClosureIdentityVerification(Base):
    """Desafio temporário de identidade para reabertura tardia de tenant encerrado."""

    __tablename__ = "tenant_closure_identity_verification"
    __table_args__ = (
        UniqueConstraint("tenant_id", "request_id", name="uq_closure_identity_request"),
        ForeignKeyConstraint(
            ["closure_request_id", "tenant_id"],
            ["tenant_closure_request.id", "tenant_closure_request.tenant_id"],
            name="fk_closure_identity_closure",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "admin_user_id"],
            ["tenant_admin.tenant_id", "tenant_admin.admin_user_id"],
            name="fk_closure_identity_membership",
        ),
        CheckConstraint(
            "state IN ('email_pending', 'verified', 'locked', 'expired', 'superseded')",
            name="ck_closure_identity_state",
        ),
        CheckConstraint("attempts BETWEEN 0 AND 5", name="ck_closure_identity_attempts"),
        CheckConstraint(
            "(state = 'verified' AND verified_at IS NOT NULL) OR "
            "(state != 'verified' AND verified_at IS NULL)",
            name="ck_closure_identity_verified_at",
        ),
        CheckConstraint(
            "(state = 'email_pending' AND current_name_envelope IS NOT NULL "
            "AND current_email_envelope IS NOT NULL AND email_fingerprint IS NOT NULL "
            "AND code_digest IS NOT NULL) OR "
            "(state != 'email_pending' AND current_name_envelope IS NULL "
            "AND current_email_envelope IS NULL AND email_fingerprint IS NULL "
            "AND code_digest IS NULL)",
            name="ck_closure_identity_pending_material",
        ),
        Index(
            "uq_closure_identity_pending_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=text("state = 'email_pending'"),
            sqlite_where=text("state = 'email_pending'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    closure_request_id: Mapped[UUID] = mapped_column()
    admin_user_id: Mapped[UUID] = mapped_column()
    request_id: Mapped[UUID] = mapped_column()
    state: Mapped[str] = mapped_column(String(16), default="email_pending")
    current_name_envelope: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_email_envelope: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AdminSecurityChallenge(Base):
    """Desafio curto e finalístico para recuperação e ações sensíveis."""

    __tablename__ = "admin_security_challenge"
    tenant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True,
    )
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('password_recovery_otp', 'change_password_otp', 'change_email_otp', "
            "'change_pix_otp', 'change_payment_otp')",
            name="ck_admin_security_purpose",
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
    __table_args__ = (CheckConstraint("purpose IN ('password_reset', 'verify_admin_email')"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    target_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    encrypted_target: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotographerAccessRecovery(Base):
    """Atendimento do proprietário; material transitório cifrado, sem documentos."""

    __tablename__ = "photographer_access_recovery"
    __table_args__ = (
        ForeignKeyConstraint(
            ["admin_user_id", "tenant_id"], ["tenant_admin.admin_user_id", "tenant_admin.tenant_id"],
            name="fk_access_recovery_target_membership",
        ),
        ForeignKeyConstraint(
            ["closure_request_id", "tenant_id"], ["tenant_closure_request.id", "tenant_closure_request.tenant_id"],
            name="fk_access_recovery_closure",
        ),
        CheckConstraint("state IN ('email_pending','email_verified','completed','expired')",
                        name="ck_access_recovery_state"),
        CheckConstraint("reason_code IN ('lost_email','lost_all_access')", name="ck_access_recovery_reason"),
        CheckConstraint("identity_confirmed", name="ck_access_recovery_identity_confirmed"),
        CheckConstraint("length(expected_version) = 64 AND length(request_fingerprint) = 64",
                        name="ck_access_recovery_versions"),
        CheckConstraint("state NOT IN ('email_pending','email_verified') OR encrypted_payload IS NOT NULL",
                        name="ck_access_recovery_pending_payload"),
        CheckConstraint("state != 'email_pending' OR token_hash IS NOT NULL",
                        name="ck_access_recovery_pending_token"),
        CheckConstraint("state NOT IN ('email_verified','completed') OR email_verified_at IS NOT NULL",
                        name="ck_access_recovery_email_verified"),
        CheckConstraint("state != 'completed' OR (completed_at IS NOT NULL AND token_hash IS NULL "
                        "AND encrypted_payload IS NULL)", name="ck_access_recovery_completed"),
        CheckConstraint("state != 'expired' OR (token_hash IS NULL AND encrypted_payload IS NULL)",
                        name="ck_access_recovery_expired"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    admin_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), index=True)
    actor_admin_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"))
    closure_request_id: Mapped[UUID | None] = mapped_column(nullable=True)
    identity_confirmed: Mapped[bool] = mapped_column(Boolean)
    reason_code: Mapped[str] = mapped_column(String(24))
    reset_totp: Mapped[bool] = mapped_column(Boolean, default=False)
    expected_version: Mapped[str] = mapped_column(String(64))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    recipient_fingerprint: Mapped[str] = mapped_column(String(64))
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    encrypted_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(24), default="email_pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_client_id_tenant"),
        UniqueConstraint("tenant_id", "phone_e164", name="uq_client_tenant_phone"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    phone_e164: Mapped[str] = mapped_column(String(16), index=True)


class ClientPhone(Base):
    __tablename__ = "client_phone"
    __table_args__ = (
        ForeignKeyConstraint(
            ["client_id", "tenant_id"], ["client.id", "client.tenant_id"],
            name="fk_client_phone_client_tenant",
        ),
        Index(
            "uq_client_phone_active_reserved",
            "tenant_id", "phone_e164", unique=True,
            sqlite_where=text("active = 1"), postgresql_where=text("active"),
        ),
        Index(
            "uq_client_phone_active_verified",
            "tenant_id",
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
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    phone_e164: Mapped[str] = mapped_column(String(16), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClientDeletionReceipt(Base):
    """Resultado mínimo e reaplicável de uma exclusão global de cliente."""

    __tablename__ = "client_deletion_receipt"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_client_deletion_receipt_idempotency"),
        CheckConstraint(
            "status IN ('completed')", name="ck_client_deletion_receipt_status"
        ),
        CheckConstraint(
            "length(inventory_fingerprint) = 64",
            name="ck_client_deletion_receipt_fingerprint",
        ),
        CheckConstraint(
            "length(idempotency_key) = 64",
            name="ck_client_deletion_receipt_idempotency_fingerprint",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    target_client_id: Mapped[UUID] = mapped_column(index=True)
    actor_admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("admin_user.id"), nullable=False, index=True
    )
    inventory_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="completed")
    removed_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GalleryAccess(Base):
    __tablename__ = "gallery_access"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("client_id", "gallery_id"),
        CheckConstraint(
            "(parent_gallery_id IS NOT NULL AND derived_gallery_id IS NULL "
            "AND gallery_id = parent_gallery_id) OR "
            "(derived_gallery_id IS NOT NULL AND parent_gallery_id IS NULL "
            "AND gallery_id = derived_gallery_id)", name="ck_gallery_access_typed_target",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    gallery_id: Mapped[UUID] = mapped_column(index=True)
    parent_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parent_gallery.id"), nullable=True,
    )
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id"), nullable=True,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ParentGallery(Base):
    """Galeria pública administrada exclusivamente pelo fotógrafo."""

    __tablename__ = "parent_gallery"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_parent_gallery_id_tenant"),
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
        CheckConstraint(
            "pricing_mode IN ('fixed', 'progressive', 'legacy_volume')",
            name="ck_parent_gallery_pricing_mode",
        ),
        CheckConstraint(
            "fixed_unit_price_cents IS NULL OR fixed_unit_price_cents >= 0",
            name="ck_parent_gallery_fixed_unit_price",
        ),
        Index(
            "ix_parent_gallery_lifecycle_created",
            "lifecycle_status",
            "created_at",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    event_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    watermark_text: Mapped[str] = mapped_column(String(120), default=DEFAULT_WATERMARK_TEXT)
    watermark_font: Mapped[str] = mapped_column(String(80), default="sans-serif")
    watermark_color: Mapped[str] = mapped_column(String(7), default="#FFFFFF")
    watermark_size: Mapped[int] = mapped_column(Integer, default=24)
    watermark_direction: Mapped[str] = mapped_column(String(16), default="diagonal")
    folder_display_mode: Mapped[str] = mapped_column(String(16), default="individual")
    cover_title_font: Mapped[str] = mapped_column(String(80), default="system-sans")
    cover_title_color: Mapped[str] = mapped_column(String(7), default="#FFFFFF")
    cover_title_size: Mapped[int] = mapped_column(Integer, default=32)
    cover_title_position: Mapped[str] = mapped_column(String(16), default="bottom-left")
    cover_photo_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("photo_asset.id", use_alter=True, name="fk_parent_gallery_cover_photo"),
        nullable=True,
    )
    payment_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sales_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    selection_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    favorites_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    comments_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    pricing_mode: Mapped[str] = mapped_column(String(24), default="fixed")
    fixed_unit_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progressive_pricing_preset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("progressive_pricing_preset.id", use_alter=True),
        nullable=True,
        index=True,
    )
    pricing_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pricing_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    lifecycle_status: Mapped[str] = mapped_column(String(16), default="active")
    access_mode: Mapped[str] = mapped_column(String(24), default="invite_only")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ParentGalleryRegistration(Base):
    """Registro de entrada pelo link não listado; não concede leitura de fotos."""

    __tablename__ = "parent_gallery_registration"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (UniqueConstraint("parent_gallery_id", "client_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("parent_gallery.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PhotoAsset(Base):
    """Arquivo público ou pertencente exclusivamente a uma galeria privada."""

    __tablename__ = "photo_asset"
    __table_args__ = (
        ForeignKeyConstraint(
            ["parent_gallery_id", "tenant_id"],
            ["parent_gallery.id", "parent_gallery.tenant_id"],
            name="fk_photo_asset_parent_tenant",
        ),
        ForeignKeyConstraint(
            ["derived_gallery_id", "parent_gallery_id", "tenant_id"],
            ["derived_gallery.id", "derived_gallery.parent_gallery_id", "derived_gallery.tenant_id"],
            name="fk_photo_asset_private_tenant",
        ),
        UniqueConstraint("id", "parent_gallery_id", name="uq_photo_asset_id_parent"),
        UniqueConstraint("id", "tenant_id", name="uq_owner_photo_asset_id_tenant_id"),
        ForeignKeyConstraint(
            ["folder_id", "parent_gallery_id"],
            ["photo_folder.id", "photo_folder.parent_gallery_id"],
            name="fk_photo_asset_folder_gallery",
        ),
        ForeignKeyConstraint(
            ["folder_id", "parent_gallery_id", "derived_gallery_id"],
            [
                "photo_folder.id",
                "photo_folder.parent_gallery_id",
                "photo_folder.derived_gallery_id",
            ],
            name="fk_photo_asset_folder_scope",
        ),
        Index("ix_photo_asset_private_scope", "derived_gallery_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    parent_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("parent_gallery.id"), index=True)
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="CASCADE"), nullable=True, index=True
    )
    folder_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512))
    display_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RawDevelopmentSettings(Base):
    """ConfiguraÃ§Ã£o RAW isolada por fotÃ³grafo/tenant."""

    __tablename__ = "raw_development_settings"
    __table_args__ = (
        CheckConstraint("id = 1"),
        CheckConstraint("selected_engine IN ('rawtherapee', 'lightcraft')"),
        CheckConstraint("release_check_status IN ('unknown', 'ok', 'unavailable')"),
    )
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    selected_engine: Mapped[str] = mapped_column(String(16), default="lightcraft")
    lightcraft_latest_stable_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lightcraft_latest_stable_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    lightcraft_latest_stable_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_release_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_check_status: Mapped[str] = mapped_column(String(16), default="unknown", server_default="unknown")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class RawDevelopmentJob(Base):
    """Estado e proveniÃªncia mÃ­nima de uma conversÃ£o transitÃ³ria por tenant."""

    __tablename__ = "raw_development_job"
    __table_args__ = (
        CheckConstraint("status IN ('receiving', 'queued', 'processing', 'ready', 'failed', 'reupload_required')"),
        CheckConstraint("engine IN ('rawtherapee', 'lightcraft')"),
        CheckConstraint("attempts >= 0"),
        CheckConstraint("input_bytes > 0"),
        CheckConstraint("width IS NULL OR width > 0"),
        CheckConstraint("height IS NULL OR height > 0"),
        ForeignKeyConstraint(["photo_asset_id", "tenant_id"], ["photo_asset.id", "photo_asset.tenant_id"],
                             ondelete="CASCADE", name="fk_raw_development_photo_tenant"),
        Index("ix_raw_development_queue", "tenant_id", "status", "updated_at"),
    )
    photo_asset_id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), primary_key=True)
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    input_bytes: Mapped[int] = mapped_column(Integer)
    source_format: Mapped[str] = mapped_column(String(8))
    camera_make: Mapped[str | None] = mapped_column(String(64), nullable=True)
    camera_model: Mapped[str | None] = mapped_column(String(96), nullable=True)
    staging_key: Mapped[str] = mapped_column(String(96), unique=True)
    engine: Mapped[str] = mapped_column(String(16))
    engine_version: Mapped[str] = mapped_column(String(64))
    profile_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PhotoFolder(Base):
    """Lote público ou privado preparado pelo fotógrafo."""

    __tablename__ = "photo_folder"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("id", "parent_gallery_id", name="uq_photo_folder_id_parent"),
        UniqueConstraint(
            "id",
            "parent_gallery_id",
            "derived_gallery_id",
            name="uq_photo_folder_id_parent_private",
        ),
        CheckConstraint("purpose IN ('content', 'cover_assets')", name="ck_photo_folder_purpose"),
        CheckConstraint(
            "purpose != 'cover_assets' OR derived_gallery_id IS NULL",
            name="ck_photo_folder_private_content_only",
        ),
        CheckConstraint(
            "access_duration_days IS NULL OR access_duration_days >= 1",
            name="ck_photo_folder_access_duration_days",
        ),
        CheckConstraint(
            "audience_scope IS NULL OR audience_scope IN ('all', 'selected')",
            name="ck_photo_folder_audience_scope",
        ),
        Index(
            "uq_photo_folder_public_position",
            "parent_gallery_id",
            "position",
            unique=True,
            sqlite_where=text("derived_gallery_id IS NULL"),
            postgresql_where=text("derived_gallery_id IS NULL"),
        ),
        Index(
            "uq_photo_folder_private_position",
            "derived_gallery_id",
            "position",
            unique=True,
            sqlite_where=text("derived_gallery_id IS NOT NULL"),
            postgresql_where=text("derived_gallery_id IS NOT NULL"),
        ),
        Index(
            "uq_photo_folder_cover_assets_parent",
            "parent_gallery_id",
            unique=True,
            sqlite_where=text("purpose = 'cover_assets'"),
            postgresql_where=text("purpose = 'cover_assets'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("parent_gallery.id"), index=True)
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="preparing", index=True)
    purpose: Mapped[str] = mapped_column(String(24), default="content", server_default="content")
    audience_scope: Mapped[str | None] = mapped_column(String(16), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class GalleryClientState(Base):
    """Estado individual da cliente na galeria canônica, sem galeria derivada."""

    __tablename__ = "gallery_client_state"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("parent_gallery_id", "client_id", name="uq_gallery_client_state_pair"),
        CheckConstraint(
            "status IN ('active', 'blocked', 'unlinked')",
            name="ck_gallery_client_state_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("parent_gallery.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    selection_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    selection_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class FolderClientGrant(Base):
    """Atribuição de uma pasta restrita a uma cliente da mesma galeria."""

    __tablename__ = "folder_client_grant"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["folder_id", "parent_gallery_id"],
            ["photo_folder.id", "photo_folder.parent_gallery_id"],
            name="fk_folder_client_grant_folder_parent",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["parent_gallery_id", "client_id"],
            ["gallery_client_state.parent_gallery_id", "gallery_client_state.client_id"],
            name="fk_folder_client_grant_client_state",
        ),
        UniqueConstraint("folder_id", "client_id", name="uq_folder_client_grant_pair"),
        Index("ix_folder_client_grant_audience", "parent_gallery_id", "client_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    folder_id: Mapped[UUID] = mapped_column(index=True)
    parent_gallery_id: Mapped[UUID] = mapped_column(index=True)
    client_id: Mapped[UUID] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DerivedGallery(Base):
    """Galeria privada com proprietária legada durante a migração multiusuário."""

    __tablename__ = "derived_gallery"
    __table_args__ = (
        UniqueConstraint("id", "parent_gallery_id", "tenant_id", name="uq_derived_gallery_tenant"),
        ForeignKeyConstraint(
            ["parent_gallery_id", "tenant_id"],
            ["parent_gallery.id", "parent_gallery.tenant_id"],
            name="fk_derived_gallery_parent_tenant",
        ),
        UniqueConstraint(
            "id",
            "parent_gallery_id",
            name="uq_derived_gallery_id_parent",
        ),
        Index(
            "ix_derived_gallery_parent_client",
            "parent_gallery_id",
            "client_id",
            unique=True,
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
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


class DerivedGalleryMembership(Base):
    """Associação autorizável de uma cliente ao acervo privado compartilhado."""

    __tablename__ = "derived_gallery_membership"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["derived_gallery_id", "parent_gallery_id"],
            ["derived_gallery.id", "derived_gallery.parent_gallery_id"],
            name="fk_membership_gallery_parent",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "parent_gallery_id",
            "client_id",
            name="uq_membership_parent_client",
        ),
        CheckConstraint(
            "status IN ('active', 'blocked', 'unlinked')",
            name="ck_derived_gallery_membership_status",
        ),
        Index(
            "ix_membership_gallery_status",
            "derived_gallery_id",
            "status",
        ),
        Index(
            "ix_membership_client_status",
            "client_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID] = mapped_column(index=True)
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id"), index=True
    )
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_user.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class DerivedGalleryPhoto(Base):
    """Referência de uma foto da Galeria pública atribuída à galeria privada."""

    __tablename__ = "derived_gallery_photo"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint(
            "derived_gallery_id",
            "photo_asset_id",
            name="uq_derived_gallery_photo_asset",
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


class DerivedGalleryPhotoOrigin(Base):
    """Justificativa independente que mantém uma foto no acervo privado comum."""

    __tablename__ = "derived_gallery_photo_origin"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint(
            "derived_gallery_photo_id",
            "origin",
            name="uq_derived_gallery_photo_origin_reason",
        ),
        CheckConstraint(
            "origin IN ('admin', 'client', 'facial')",
            name="ck_derived_gallery_photo_origin_reason",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_photo_id: Mapped[UUID] = mapped_column(
        ForeignKey("derived_gallery_photo.id"),
        index=True,
    )
    origin: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoSelection(Base):
    __tablename__ = "photo_selection"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("derived_gallery_id", "photo_asset_id", "client_id"),
        Index("ix_photo_selection_gallery_client", "derived_gallery_id", "client_id"),
        CheckConstraint(
            "(parent_gallery_id IS NULL AND derived_gallery_id IS NOT NULL) OR "
            "(parent_gallery_id IS NOT NULL AND derived_gallery_id IS NULL)",
            name="ck_photo_selection_gallery_scope",
        ),
        Index(
            "uq_photo_selection_canonical",
            "parent_gallery_id", "photo_asset_id", "client_id",
            unique=True,
            sqlite_where=text("derived_gallery_id IS NULL"),
            postgresql_where=text("derived_gallery_id IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id"), nullable=True, index=True
    )
    parent_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parent_gallery.id"), nullable=True, index=True
    )
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoFavorite(Base):
    __tablename__ = "photo_favorite"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("derived_gallery_id", "photo_asset_id", "client_id"),
        CheckConstraint(
            "(parent_gallery_id IS NULL AND derived_gallery_id IS NOT NULL) OR "
            "(parent_gallery_id IS NOT NULL AND derived_gallery_id IS NULL)",
            name="ck_photo_favorite_gallery_scope",
        ),
        Index(
            "uq_photo_favorite_canonical",
            "parent_gallery_id", "photo_asset_id", "client_id",
            unique=True,
            sqlite_where=text("derived_gallery_id IS NULL"),
            postgresql_where=text("derived_gallery_id IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id"), nullable=True, index=True
    )
    parent_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parent_gallery.id"), nullable=True, index=True
    )
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoView(Base):
    __tablename__ = "photo_view"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("derived_gallery_id", "client_id", "photo_asset_id"),
        CheckConstraint(
            "(parent_gallery_id IS NULL AND derived_gallery_id IS NOT NULL) OR "
            "(parent_gallery_id IS NOT NULL AND derived_gallery_id IS NULL)",
            name="ck_photo_view_gallery_scope",
        ),
        Index(
            "uq_photo_view_canonical",
            "parent_gallery_id", "client_id", "photo_asset_id",
            unique=True,
            sqlite_where=text("derived_gallery_id IS NULL"),
            postgresql_where=text("derived_gallery_id IS NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id"), nullable=True, index=True
    )
    parent_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parent_gallery.id"), nullable=True, index=True
    )
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    first_viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoComment(Base):
    __tablename__ = "photo_comment"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint(
            "(parent_gallery_id IS NULL AND derived_gallery_id IS NOT NULL) OR "
            "(parent_gallery_id IS NOT NULL AND derived_gallery_id IS NULL)",
            name="ck_photo_comment_gallery_scope",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id"), nullable=True, index=True
    )
    parent_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parent_gallery.id"), nullable=True, index=True
    )
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PaymentGroup(Base):
    """Um PIX da cliente, com pedidos operacionais independentes por galeria."""

    __tablename__ = "payment_group"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("id", "client_id", name="uq_payment_group_owner"),
        CheckConstraint("state IN ('draft', 'reported', 'confirmed', 'refused', 'unavailable')",
                        name="ck_payment_group_state"),
        CheckConstraint("total_cents >= 0", name="ck_payment_group_total"),
        Index("uq_payment_group_draft", "client_id", unique=True,
              sqlite_where=text("state = 'draft'"),
              postgresql_where=text("state = 'draft'")),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    revision: Mapped[str] = mapped_column(String(64))
    total_cents: Mapped[int] = mapped_column(Integer)
    pix_copy_paste_snapshot: Mapped[str] = mapped_column(Text)
    pix_instructions_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_configuration_snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProviderPayment(Base):
    """Registro legado de compra InfinitePay, preservado para consulta financeira."""

    __tablename__ = "provider_payment"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", "client_id", name="uq_provider_payment_owner"),
        UniqueConstraint("tenant_id", "client_id", "checkout_key", name="uq_provider_payment_checkout"),
        UniqueConstraint("provider", "provider_transaction_nsu", name="uq_provider_payment_transaction"),
        CheckConstraint("capture_method IS NULL OR capture_method IN ('credit_card', 'pix')",
                        name="ck_provider_payment_capture_method"),
        CheckConstraint("provider = 'infinitepay'", name="ck_provider_payment_provider"),
        CheckConstraint("total_cents > 0 AND configuration_version > 0 AND revision_number >= 0",
                        name="ck_provider_payment_amount_version"),
        CheckConstraint("state IN ('creating', 'awaiting_payment', 'verification_required', 'confirmed', "
                        "'failed_before_issue', 'exception', 'hold')", name="ck_provider_payment_state"),
        CheckConstraint("state != 'confirmed' OR (provider_transaction_nsu IS NOT NULL "
                        "AND confirmed_at IS NOT NULL)", name="ck_provider_payment_confirmed"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    provider: Mapped[str] = mapped_column(String(24), default="infinitepay")
    checkout_key: Mapped[str] = mapped_column(String(128))
    cart_revision: Mapped[str] = mapped_column(String(64))
    total_cents: Mapped[int] = mapped_column(Integer)
    handle_snapshot: Mapped[str] = mapped_column(String(100))
    checkout_methods_snapshot: Mapped[list] = mapped_column(JSON, default=lambda: ["credit_card"],
                                                          server_default='["credit_card"]')
    capture_method: Mapped[str | None] = mapped_column(String(24), nullable=True)
    cart_dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    configuration_version: Mapped[int] = mapped_column(Integer)
    verification_profile: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(32), default="creating", index=True)
    revision_number: Mapped[int] = mapped_column(Integer, default=0)
    provider_transaction_nsu: Mapped[str | None] = mapped_column(String(200), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProviderPaymentAttempt(Base):
    """Uma emissão durável, sem reenvio automático de resultado incerto."""

    __tablename__ = "provider_payment_attempt"
    __table_args__ = (
        ForeignKeyConstraint(["payment_id", "tenant_id", "client_id"],
                             ["provider_payment.id", "provider_payment.tenant_id", "provider_payment.client_id"],
                             name="fk_provider_attempt_payment_owner"),
        UniqueConstraint("tenant_id", "payment_id", name="uq_provider_attempt_payment"),
        CheckConstraint("state IN ('started', 'accepted', 'refused', 'unknown')",
                        name="ck_provider_attempt_state"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    payment_id: Mapped[UUID] = mapped_column(index=True)
    state: Mapped[str] = mapped_column(String(16), default="started")
    error_category: Mapped[str | None] = mapped_column(String(48), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProviderPaymentReceipt(Base):
    """Candidato mínimo durável; não guarda corpo bruto nem comprova pagamento."""

    __tablename__ = "provider_payment_receipt"
    __table_args__ = (
        ForeignKeyConstraint(["payment_id", "tenant_id", "client_id"],
                             ["provider_payment.id", "provider_payment.tenant_id", "provider_payment.client_id"],
                             name="fk_provider_receipt_payment_owner"),
        UniqueConstraint("tenant_id", "payment_id", "digest", name="uq_provider_receipt_digest"),
        CheckConstraint("state IN ('queued', 'processing', 'verified', 'ignored', 'failed')",
                        name="ck_provider_receipt_state"),
        CheckConstraint("attempts >= 0", name="ck_provider_receipt_attempts"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    payment_id: Mapped[UUID] = mapped_column(index=True)
    digest: Mapped[str] = mapped_column(String(64))
    transaction_nsu: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(512))
    verification_profile: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProviderPaymentCorrection(Base):
    """Histórico append-only quando uma confirmação de cartão entra em hold."""

    __tablename__ = "provider_payment_correction"
    __table_args__ = (
        ForeignKeyConstraint(["payment_id", "tenant_id", "client_id"],
                             ["provider_payment.id", "provider_payment.tenant_id", "provider_payment.client_id"],
                             name="fk_provider_correction_payment_owner"),
        UniqueConstraint("tenant_id", "payment_id", "idempotency_key",
                         name="uq_provider_correction_idempotency"),
        CheckConstraint("previous_revision >= 1", name="ck_provider_correction_revision"),
        CheckConstraint("previous_transaction_nsu <> ''", name="ck_provider_correction_transaction"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    payment_id: Mapped[UUID] = mapped_column(index=True)
    actor_admin_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    reason: Mapped[str] = mapped_column(String(500))
    previous_revision: Mapped[int] = mapped_column(Integer)
    previous_transaction_nsu: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MercadoPagoAccount(Base):
    """Versão imutável da conta; envelopes em tabela dedicada ao cofre."""

    __tablename__ = "mercadopago_account"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    seller_id: Mapped[str] = mapped_column(String(32))
    public_key: Mapped[str] = mapped_column(String(200))
    access_token_envelope: Mapped[dict] = mapped_column(JSON)
    webhook_secret_envelope: Mapped[dict] = mapped_column(JSON)
    test_account: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(24), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        # A migração 0088 já criou essa chave composta para que registros
        # financeiros referenciem a conta junto ao tenant proprietário.
        UniqueConstraint("id", "tenant_id", name="uq_owner_mercadopago_account_id_tenant_id"),
        CheckConstraint("status IN ('active', 'unauthorized')", name="ck_mp_account_status"),
    )


class PaymentPreferences(Base):
    __tablename__ = "payment_preferences"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), unique=True)
    account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("mercadopago_account.id"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    pix_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    mercadopago_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false")
    __table_args__ = (
        CheckConstraint("version >= 0", name="ck_payment_preferences_version"),
        CheckConstraint("NOT mercadopago_enabled OR account_id IS NOT NULL",
                        name="ck_payment_preferences_account"),
    )


class MercadoPagoPayment(Base):
    """Uma tentativa de cobrança com seus pedidos e referência imutáveis."""

    __tablename__ = "mercadopago_payment"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("mercadopago_account.id"))
    account: Mapped[MercadoPagoAccount] = relationship(
        primaryjoin=(account_id == MercadoPagoAccount.id) & (tenant_id == MercadoPagoAccount.tenant_id),
        viewonly=True)
    checkout_key: Mapped[str] = mapped_column(String(36))
    cart_revision: Mapped[str] = mapped_column(String(64))
    total_cents: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(24))
    state: Mapped[str] = mapped_column(String(32), default="prepared")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    provider_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    order_detail: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transaction_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transaction_detail: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    pix_copy_paste: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(48), nullable=True)
    check_attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_check_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", "client_id", name="uq_mp_payment_owner"),
        UniqueConstraint("tenant_id", "client_id", "checkout_key", name="uq_mp_checkout_key"),
        UniqueConstraint("account_id", "provider_order_id", name="uq_mp_provider_order"),
        CheckConstraint("total_cents > 0", name="ck_mp_total"),
        CheckConstraint("method IN ('credit_card', 'pix')", name="ck_mp_method"),
        CheckConstraint("state IN ('prepared', 'sending', 'initiated', 'pending', 'processing', "
                        "'confirmed', 'rejected', 'canceled', 'expired', 'refunded', "
                        "'partially_refunded', 'charged_back', 'verification_required', "
                        "'duplicate_review', 'abandoned')", name="ck_mp_state"),
        CheckConstraint("state != 'confirmed' OR (provider_order_id IS NOT NULL "
                        "AND provider_payment_id IS NOT NULL AND confirmed_at IS NOT NULL)",
                        name="ck_mp_confirmed"),
        Index("uq_mp_active_client_revision", "tenant_id", "client_id", "cart_revision", unique=True,
              sqlite_where=text("active = true"), postgresql_where=text("active = true")),
    )


class MercadoPagoWebhook(Base):
    """Inbox mínima durável; eventos diferentes de uma order não são descartados."""

    __tablename__ = "mercadopago_webhook"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("mercadopago_account.id"))
    provider_order_id: Mapped[str] = mapped_column(String(64))
    digest: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("account_id", "digest", name="uq_mp_webhook_digest"),
        CheckConstraint("state IN ('queued', 'processing', 'done', 'ignored', 'failed')",
                        name="ck_mp_webhook_state"),
        CheckConstraint("attempts >= 0", name="ck_mp_webhook_attempts"),
        Index("ix_mp_webhook_queue", "state", "next_attempt_at"),
    )


class SaleOrder(Base):
    __tablename__ = "sale_order"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint("payment_status IN ('pending', 'confirmed', 'cancelled', 'not_required')"),
        CheckConstraint("total_cents >= 0"),
        UniqueConstraint("derived_gallery_id", "client_id", "checkout_key"),
        UniqueConstraint(
            "parent_gallery_id", "client_id", "checkout_key",
            name="uq_sale_order_canonical_checkout_key",
        ),
        ForeignKeyConstraint(
            ["parent_gallery_id", "client_id"],
            ["gallery_client_state.parent_gallery_id", "gallery_client_state.client_id"],
            name="fk_sale_order_canonical_state",
        ),
        ForeignKeyConstraint(["payment_group_id", "client_id"],
                             ["payment_group.id", "payment_group.client_id"],
                             name="fk_sale_order_payment_group_owner"),
        ForeignKeyConstraint(["provider_payment_id", "tenant_id", "client_id"],
                             ["provider_payment.id", "provider_payment.tenant_id", "provider_payment.client_id"],
                             name="fk_sale_order_provider_payment_owner"),
        CheckConstraint("payment_group_id IS NULL OR provider_payment_id IS NULL",
                        name="ck_sale_order_single_payment_method"),
        ForeignKeyConstraint(["mercadopago_payment_id", "tenant_id", "client_id"],
                             ["mercadopago_payment.id", "mercadopago_payment.tenant_id",
                              "mercadopago_payment.client_id"], name="fk_sale_order_mp_owner"),
        CheckConstraint("mercadopago_payment_id IS NULL OR "
                        "(payment_group_id IS NULL AND provider_payment_id IS NULL)",
                        name="ck_sale_order_mp_exclusive"),
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
        Index(
            "uq_sale_order_editable_draft",
            "derived_gallery_id",
            "client_id",
            unique=True,
            sqlite_where=text(
                "frozen_at IS NULL AND payment_status = 'pending' "
                "AND checkout_key IS NOT NULL AND assets_removed_at IS NULL"
            ),
            postgresql_where=text(
                "frozen_at IS NULL AND payment_status = 'pending' "
                "AND checkout_key IS NOT NULL AND assets_removed_at IS NULL"
            ),
        ),
        Index(
            "uq_sale_order_canonical_editable_draft",
            "parent_gallery_id", "client_id",
            unique=True,
            sqlite_where=text(
                "parent_gallery_id IS NOT NULL AND frozen_at IS NULL AND "
                "payment_status = 'pending' AND checkout_key IS NOT NULL "
                "AND assets_removed_at IS NULL"
            ),
            postgresql_where=text(
                "parent_gallery_id IS NOT NULL AND frozen_at IS NULL AND "
                "payment_status = 'pending' AND checkout_key IS NOT NULL "
                "AND assets_removed_at IS NULL"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="SET NULL"), nullable=True, index=True
    )
    parent_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parent_gallery.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    derived_gallery_id_snapshot: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    derived_gallery_name_snapshot: Mapped[str] = mapped_column(String(200))
    parent_gallery_id_snapshot: Mapped[UUID] = mapped_column(index=True)
    parent_gallery_name_snapshot: Mapped[str] = mapped_column(String(200))
    payment_status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    total_cents: Mapped[int] = mapped_column(Integer)
    frozen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_name_snapshot: Mapped[str | None] = mapped_column(String(200), nullable=True)
    client_phone_snapshot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    price_rule_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payment_required_snapshot: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sales_message_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_message_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_album_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    delivery_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    pix_copy_paste_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_qr_code_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_instructions_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_configuration_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pii_minimized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checkout_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    assets_removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_group_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    provider_payment_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    mercadopago_payment_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SaleOrderItem(Base):
    __tablename__ = "sale_order_item"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
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
    folder_id_snapshot: Mapped[UUID | None] = mapped_column(nullable=True)
    folder_name_snapshot: Mapped[str | None] = mapped_column(String(200), nullable=True)
    checksum_sha256_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_price_cents: Mapped[int] = mapped_column(Integer)


class RemovedPhotoMovement(Base):
    """Referência textual autorizada; nenhuma FK para o acervo removível."""

    __tablename__ = "removed_photo_movement"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (UniqueConstraint("kind", "source_id", name="uq_removed_photo_movement_source"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column()
    kind: Mapped[str] = mapped_column(String(20))
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    parent_gallery_id: Mapped[UUID] = mapped_column(index=True)
    derived_gallery_id: Mapped[UUID] = mapped_column(index=True)
    photo_id: Mapped[UUID] = mapped_column(index=True)
    parent_gallery_name: Mapped[str] = mapped_column(String(200))
    gallery_name: Mapped[str] = mapped_column(String(200))
    folder_name: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(512))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    removed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AssetFileCleanup(Base):
    """Outbox de caminhos relativos confinados, persistida antes de apagar arquivos."""

    __tablename__ = "asset_file_cleanup"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    paths: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GalleryLifecycleOperation(Base):
    """Operação durável e auditável sobre o ciclo de vida de uma Galeria pública."""

    __tablename__ = "gallery_lifecycle_operation"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
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


class MediaArchiveCycle(Base):
    """Catálogo tenant-scoped de um ciclo de arquivo frio por pasta."""

    __tablename__ = "media_archive_cycle"
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_media_archive_cycle_id_tenant"),
        UniqueConstraint(
            "folder_id", "cycle_number", name="uq_media_archive_cycle_folder_number",
        ),
        ForeignKeyConstraint(
            ["folder_id", "parent_gallery_id", "tenant_id"],
            ["photo_folder.id", "photo_folder.parent_gallery_id", "photo_folder.tenant_id"],
            name="fk_media_archive_cycle_folder_tenant",
        ),
        ForeignKeyConstraint(
            ["parent_gallery_id", "tenant_id"], ["parent_gallery.id", "parent_gallery.tenant_id"],
            name="fk_media_archive_cycle_parent_tenant",
        ),
        CheckConstraint(
            "state IN ('local', 'archiving', 'archived', 'restoring', 'reconciliation_required', 'deleting', 'deleted')",
            name="ck_media_archive_cycle_state",
        ),
        CheckConstraint("cycle_number >= 1", name="ck_media_archive_cycle_number"),
        CheckConstraint("object_count >= 0", name="ck_media_archive_cycle_object_count"),
        CheckConstraint("total_bytes >= 0", name="ck_media_archive_cycle_total_bytes"),
        CheckConstraint(
            "manifest_sha256 IS NULL OR length(manifest_sha256) = 64",
            name="ck_media_archive_cycle_manifest_sha256",
        ),
        CheckConstraint("manifest_version >= 1", name="ck_media_archive_cycle_manifest_version"),
        Index("ix_media_archive_cycle_tenant_folder_state", "tenant_id", "folder_id", "state"),
        Index("ix_media_archive_cycle_state_next_check", "state", "next_archive_check_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(index=True)
    folder_id: Mapped[UUID] = mapped_column(index=True)
    cycle_number: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(32), default="local", index=True)
    manifest_version: Mapped[int] = mapped_column(Integer, default=1)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    manifest_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    object_count: Mapped[int] = mapped_column(Integer, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_archive_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_window_notice_for_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class MediaArchiveOperation(Base):
    """Job durável de arquivo, recuperação ou exclusão fria explícita."""

    __tablename__ = "media_archive_operation"
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_media_archive_operation_id_tenant"),
        UniqueConstraint(
            "id", "cycle_id", "tenant_id",
            name="uq_media_archive_operation_id_cycle_tenant",
        ),
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_media_archive_operation_idempotency",
        ),
        ForeignKeyConstraint(
            ["cycle_id", "tenant_id"], ["media_archive_cycle.id", "media_archive_cycle.tenant_id"],
            name="fk_media_archive_operation_cycle_tenant",
        ),
        CheckConstraint(
            "operation_type IN ('archive', 'restore', 'delete_remote')",
            name="ck_media_archive_operation_type",
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'failed', 'reconciliation_required', 'completed', 'cancelled')",
            name="ck_media_archive_operation_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_media_archive_operation_attempts"),
        CheckConstraint(
            "actor_type IN ('tenant', 'owner', 'system')", name="ck_media_archive_operation_actor",
        ),
        CheckConstraint(
            "length(idempotency_key) BETWEEN 1 AND 200",
            name="ck_media_archive_operation_idempotency_key",
        ),
        CheckConstraint(
            "status != 'processing' OR (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)",
            name="ck_media_archive_operation_processing_lease",
        ),
        Index("ix_media_archive_operation_queue", "status", "operation_type", "created_at"),
        Index("ix_media_archive_operation_lease_expires_at", "lease_expires_at"),
        Index(
            "uq_media_archive_operation_active_cycle", "tenant_id", "cycle_id", unique=True,
            sqlite_where=text("status IN ('queued', 'processing', 'reconciliation_required')"),
            postgresql_where=text("status IN ('queued', 'processing', 'reconciliation_required')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cycle_id: Mapped[UUID] = mapped_column(index=True)
    operation_type: Mapped[str] = mapped_column(String(24), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    stage: Mapped[str | None] = mapped_column(String(48), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    actor_type: Mapped[str] = mapped_column(String(16), default="system")
    actor_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    last_error_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class MediaArchiveRecoveryPricing(Base):
    """Taxa global configurável; NULL significa que o preço ainda não foi definido."""

    __tablename__ = "media_archive_recovery_pricing"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_media_archive_recovery_pricing_singleton"),
        CheckConstraint(
            "recovery_fee_credits IS NULL OR recovery_fee_credits > 0",
            name="ck_media_archive_recovery_fee_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    recovery_fee_credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "platform_owner.admin_user_id",
            name="fk_media_archive_recovery_pricing_updated_by_owner",
        ), nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class MediaArchiveRecoveryRequest(Base):
    """Prazo e preço congelados quando o tenant pede recuperação."""

    __tablename__ = "media_archive_recovery_request"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id", name="fk_media_archive_recovery_request_tenant"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_media_archive_recovery_request_id_tenant"),
        UniqueConstraint("tenant_id", "operation_id", name="uq_media_archive_recovery_request_operation"),
        ForeignKeyConstraint(
            ["operation_id", "cycle_id", "tenant_id"],
            [
                "media_archive_operation.id", "media_archive_operation.cycle_id",
                "media_archive_operation.tenant_id",
            ],
            name="fk_media_archive_recovery_request_operation_scope",
        ),
        ForeignKeyConstraint(
            ["cycle_id", "tenant_id"],
            ["media_archive_cycle.id", "media_archive_cycle.tenant_id"],
            name="fk_media_archive_recovery_request_cycle_tenant",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "requested_by_tenant_admin_id"],
            ["tenant_admin.tenant_id", "tenant_admin.admin_user_id"],
            name="fk_media_archive_recovery_request_actor_membership",
        ),
        ForeignKeyConstraint(
            ["retry_of_operation_id", "tenant_id"],
            ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_recovery_request_retry_operation_tenant",
        ),
        ForeignKeyConstraint(
            ["requested_by_owner_admin_id"], ["platform_owner.admin_user_id"],
            name="fk_media_archive_recovery_request_actor_owner",
        ),
        ForeignKeyConstraint(["closure_batch_id", "tenant_id"],
                             ["tenant_closure_recovery_batch.id", "tenant_closure_recovery_batch.tenant_id"],
                             name="fk_archive_recovery_closure_batch"),
        CheckConstraint(
            "(requester_type = 'tenant' AND requested_by_tenant_admin_id = requested_by_admin_id "
            "AND requested_by_owner_admin_id IS NULL AND retry_of_operation_id IS NULL AND closure_batch_id IS NULL) OR "
            "(requester_type = 'owner' AND requested_by_tenant_admin_id IS NULL "
            "AND requested_by_owner_admin_id = requested_by_admin_id "
            "AND (retry_of_operation_id IS NOT NULL OR closure_batch_id IS NOT NULL))",
            name="ck_media_archive_recovery_request_actor_shape",
        ),
        CheckConstraint("duration_days IN (7, 14, 30)", name="ck_media_archive_recovery_duration"),
        CheckConstraint(
            "fee_credits_snapshot IS NULL OR fee_credits_snapshot > 0",
            name="ck_media_archive_recovery_fee_snapshot",
        ),
        CheckConstraint(
            "((owner_exempt OR technical_cover_exempt) AND fee_credits_snapshot IS NULL) OR "
            "(NOT owner_exempt AND NOT technical_cover_exempt AND fee_credits_snapshot IS NOT NULL)",
            name="ck_media_archive_recovery_fee_shape",
        ),
        CheckConstraint("NOT technical_cover_exempt OR (closure_batch_id IS NOT NULL AND NOT owner_exempt)",
                        name="ck_archive_recovery_cover_exemption"),
        Index("ix_media_archive_recovery_request_tenant_created", "tenant_id", "created_at"),
        Index("ix_media_archive_recovery_request_cycle", "tenant_id", "cycle_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    operation_id: Mapped[UUID] = mapped_column(index=True)
    cycle_id: Mapped[UUID] = mapped_column(index=True)
    requester_type: Mapped[str] = mapped_column(
        String(16), default="tenant", server_default=text("'tenant'"),
    )
    requested_by_admin_id: Mapped[UUID] = mapped_column(nullable=False)
    requested_by_tenant_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    requested_by_owner_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    retry_of_operation_id: Mapped[UUID | None] = mapped_column(nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer)
    fee_credits_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_exempt: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    technical_cover_exempt: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    closure_batch_id: Mapped[UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MediaArchiveRecoveryCreditReservation(Base):
    """Reserva temporária que só vira débito após recuperação integral verificada."""

    __tablename__ = "media_archive_recovery_credit_reservation"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id", name="fk_media_archive_recovery_reservation_tenant"), index=True,
    )
    __table_args__ = (
        UniqueConstraint(
            "id", "tenant_id", name="uq_media_archive_recovery_credit_reservation_id_tenant",
        ),
        UniqueConstraint(
            "tenant_id", "operation_id", name="uq_media_archive_recovery_credit_reservation_operation",
        ),
        ForeignKeyConstraint(
            ["operation_id", "tenant_id"],
            ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_recovery_credit_reservation_operation_tenant",
        ),
        CheckConstraint("reserved_credits >= 0", name="ck_media_archive_recovery_reserved_credits"),
        CheckConstraint(
            "status IN ('reserved', 'reconciliation_required', 'consumed', 'released', 'exempt')",
            name="ck_media_archive_recovery_reservation_status",
        ),
        CheckConstraint(
            "(status = 'exempt' AND reserved_credits = 0) OR "
            "(status != 'exempt' AND reserved_credits > 0)",
            name="ck_media_archive_recovery_reservation_amount",
        ),
        Index("ix_media_archive_recovery_credit_pending", "tenant_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    operation_id: Mapped[UUID] = mapped_column(index=True)
    reserved_credits: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="reserved", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class MediaArchiveObject(Base):
    """Objeto binário descrito por referência lógica, nunca por caminho local."""

    __tablename__ = "media_archive_object"
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_media_archive_object_id_tenant"),
        UniqueConstraint("cycle_id", "source_ref", name="uq_media_archive_object_cycle_source"),
        ForeignKeyConstraint(
            ["cycle_id", "tenant_id"], ["media_archive_cycle.id", "media_archive_cycle.tenant_id"],
            name="fk_media_archive_object_cycle_tenant",
        ),
        CheckConstraint(
            "object_type IN ('source', 'derivative', 'commercial_media', 'cover_asset', 'cover_thumbnail', 'manifest')",
            name="ck_media_archive_object_type",
        ),
        CheckConstraint("size_bytes > 0", name="ck_media_archive_object_size"),
        CheckConstraint("length(sha256) = 64", name="ck_media_archive_object_sha256"),
        CheckConstraint("length(source_ref) BETWEEN 1 AND 255", name="ck_media_archive_object_source_ref"),
        CheckConstraint("length(mime_type) BETWEEN 1 AND 127", name="ck_media_archive_object_mime_type"),
        Index("ix_media_archive_object_cycle", "tenant_id", "cycle_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cycle_id: Mapped[UUID] = mapped_column(index=True)
    source_ref: Mapped[str] = mapped_column(String(255))
    object_type: Mapped[str] = mapped_column(String(32))
    mime_type: Mapped[str] = mapped_column(String(127))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    remote_object_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    remote_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MediaArchiveEvent(Base):
    """Transição append-only e sanitizada de um ciclo/operação de arquivo frio."""

    __tablename__ = "media_archive_event"
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["cycle_id", "tenant_id"], ["media_archive_cycle.id", "media_archive_cycle.tenant_id"],
            name="fk_media_archive_event_cycle_tenant",
        ),
        ForeignKeyConstraint(
            ["operation_id", "tenant_id"], ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_event_operation_tenant",
        ),
        CheckConstraint("actor_type IN ('tenant', 'owner', 'system')", name="ck_media_archive_event_actor"),
        Index("ix_media_archive_event_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cycle_id: Mapped[UUID] = mapped_column(index=True)
    operation_id: Mapped[UUID] = mapped_column(index=True)
    actor_type: Mapped[str] = mapped_column(String(16))
    actor_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    event_type: Mapped[str] = mapped_column(String(48))
    cycle_state_before: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cycle_state_after: Mapped[str | None] = mapped_column(String(32), nullable=True)
    operation_status_before: Mapped[str | None] = mapped_column(String(32), nullable=True)
    operation_status_after: Mapped[str | None] = mapped_column(String(32), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MediaArchiveNotice(Base):
    """Aviso interno tenant-scoped para o fotógrafo, sem entrega externa."""

    __tablename__ = "media_archive_notice"
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_media_archive_notice_idempotency",
        ),
        ForeignKeyConstraint(
            ["cycle_id", "tenant_id"],
            ["media_archive_cycle.id", "media_archive_cycle.tenant_id"],
            name="fk_media_archive_notice_cycle_tenant",
        ),
        CheckConstraint(
            "notice_type IN ('window_7_days', 'blocked_open_order', 'archive_started', "
            "'archive_completed', 'archive_failed', 'archive_reconciliation_required', "
            "'recovery_started', 'recovery_completed', 'recovery_failed', "
            "'recovery_reconciliation_required')",
            name="ck_media_archive_notice_type",
        ),
        Index("ix_media_archive_notice_tenant_created", "tenant_id", "created_at"),
        Index("ix_media_archive_notice_tenant_read_created", "tenant_id", "read_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cycle_id: Mapped[UUID] = mapped_column(index=True)
    notice_type: Mapped[str] = mapped_column(String(40))
    idempotency_key: Mapped[str] = mapped_column(String(192))
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(String(400))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MediaArchiveCoordinator(Base):
    """Lease singleton que serializa transferências em todas as réplicas."""

    __tablename__ = "media_archive_coordinator"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_media_archive_coordinator_singleton"),
        CheckConstraint(
            "(active_operation_id IS NULL AND lease_token IS NULL AND lease_expires_at IS NULL) OR "
            "(active_operation_id IS NOT NULL AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)",
            name="ck_media_archive_coordinator_lease_shape",
        ),
        ForeignKeyConstraint(
            ["active_operation_id"], ["media_archive_operation.id"],
            name="fk_media_archive_coordinator_operation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    active_operation_id: Mapped[UUID | None] = mapped_column(nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class MediaArchiveSpaceReservation(Base):
    """Reserva persistente de bytes para o staging por volume e operação."""

    __tablename__ = "media_archive_space_reservation"
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "operation_id", "volume_key", name="uq_media_archive_space_reservation",
        ),
        ForeignKeyConstraint(
            ["operation_id", "tenant_id"], ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_space_reservation_operation_tenant",
        ),
        CheckConstraint("reserved_bytes >= 0", name="ck_media_archive_space_reservation_bytes"),
        CheckConstraint("status IN ('active', 'released')", name="ck_media_archive_space_reservation_status"),
        CheckConstraint("length(volume_key) = 64", name="ck_media_archive_space_reservation_volume_key"),
        Index("ix_media_archive_space_reservation_volume_status", "volume_key", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    operation_id: Mapped[UUID] = mapped_column(index=True)
    volume_key: Mapped[str] = mapped_column(String(64))
    reserved_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GalleryAccessCapability(Base):
    """Capacidade opaca de acesso; somente o hash do token é persistido."""

    __tablename__ = "gallery_access_capability"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_gallery_access_capability_token_hash"),
        CheckConstraint(
            "scope IN ('public_gallery', 'parent_invite', 'private_invite', "
            "'private_gallery_link', 'private_client_invite')",
            name="ck_gallery_access_capability_scope",
        ),
        CheckConstraint(
            "token_mode IN ('legacy_random', 'signed_v1')",
            name="ck_gallery_access_capability_token_mode",
        ),
        CheckConstraint(
            "token_version >= 1",
            name="ck_gallery_access_capability_token_version",
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
            "(scope IN ('private_invite', 'private_client_invite') "
            "AND client_id IS NOT NULL AND derived_gallery_id IS NOT NULL) OR "
            "(scope = 'private_gallery_link' AND client_id IS NULL "
            "AND derived_gallery_id IS NOT NULL)",
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
        Index(
            "uq_gallery_access_capability_active_private_link",
            "derived_gallery_id",
            unique=True,
            sqlite_where=text("scope = 'private_gallery_link' AND status = 'active'"),
            postgresql_where=text("scope = 'private_gallery_link' AND status = 'active'"),
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
    token_mode: Mapped[str] = mapped_column(String(24), default="legacy_random")
    token_version: Mapped[int] = mapped_column(Integer, default=1)
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
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
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

    pending_totp = [
        admin for admin in session.new.union(session.dirty)
        if isinstance(admin, AdminUser)
        and getattr(admin, "_totp_secret_needs_encryption", False)
    ]
    if pending_totp:
        cipher = TotpSecretCipher.from_environment()
        for admin in pending_totp:
            if admin.id is None:
                admin.id = uuid4()
            plaintext = admin.totp_secret
            admin._totp_secret_envelope = cipher.encrypt(plaintext, admin_id=admin.id)
            admin._totp_secret_legacy = (
                plaintext if legacy_totp_dual_write_enabled() else None
            )
            admin._totp_secret_needs_encryption = False

    for record in session.new:
        if isinstance(record, SaleOrder):
            client = session.get(Client, record.client_id)
            if not record.tenant_id or not client or client.tenant_id != record.tenant_id:
                raise ValueError("Pedido sem proprietário coerente.")
            if record.derived_gallery_id is not None and record.parent_gallery_id is not None:
                raise ValueError("Pedido não pode pertencer a duas galerias operacionais.")
            if record.parent_gallery_id is not None:
                parent = session.get(ParentGallery, record.parent_gallery_id)
                if not parent or parent.tenant_id != record.tenant_id:
                    raise ValueError("Não foi possível materializar o snapshot da galeria.")
                record.parent_gallery_id_snapshot = record.parent_gallery_id_snapshot or parent.id
                record.parent_gallery_name_snapshot = (
                    record.parent_gallery_name_snapshot or parent.name
                )
                # A coluna de nome legado continua preenchida até a camada histórica migrar.
                record.derived_gallery_name_snapshot = (
                    record.derived_gallery_name_snapshot or parent.name
                )
                client = session.get(Client, record.client_id)
                if client:
                    record.client_name_snapshot = record.client_name_snapshot or client.full_name
                    record.client_phone_snapshot = record.client_phone_snapshot or client.phone_e164
                continue
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
            if (not gallery or not parent or gallery.tenant_id != record.tenant_id
                    or parent.tenant_id != record.tenant_id):
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
            order = session.get(SaleOrder, record.sale_order_id)
            if not record.tenant_id or not order or order.tenant_id != record.tenant_id:
                raise ValueError("Item sem proprietário coerente.")
            if record.photo_asset_id is None:
                if not record.photo_asset_id_snapshot:
                    raise ValueError("Item sem foto operacional exige snapshot do identificador.")
                continue
            photo = session.get(PhotoAsset, record.photo_asset_id)
            if not photo or photo.tenant_id != record.tenant_id:
                raise ValueError("Não foi possível materializar o snapshot da foto.")
            record.photo_asset_id_snapshot = record.photo_asset_id_snapshot or photo.id
            record.filename_snapshot = (
                record.filename_snapshot or photo.display_name or photo.filename
            )


class PriceRule(Base):
    __tablename__ = "price_rule"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
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
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint(
            "input_type IS NULL OR input_type IN ('br_code', 'cpf', 'phone', 'email')"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id"), unique=True, index=True
    )
    copy_paste: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_code_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pix_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    receiver_name: Mapped[str | None] = mapped_column(String(25), nullable=True)
    receiver_city: Mapped[str | None] = mapped_column(String(15), nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class GlobalPixSettings(Base):
    """PIX único do fotógrafo; pedidos conservam a versão efetiva em snapshot."""

    __tablename__ = "global_pix_settings"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint("status IN ('active', 'unconfigured', 'review_required')"),
        CheckConstraint("version >= 0"),
        CheckConstraint("singleton = 1"),
        CheckConstraint("status != 'active' OR copy_paste IS NOT NULL"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    singleton: Mapped[int] = mapped_column(Integer, unique=True, default=1)
    admin_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"), unique=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="unconfigured")
    input_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pix_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    copy_paste: Mapped[str | None] = mapped_column(Text, nullable=True)
    receiver_name: Mapped[str | None] = mapped_column(String(25), nullable=True)
    receiver_city: Mapped[str | None] = mapped_column(String(15), nullable=True)
    instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    legacy_group_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PaymentCommunication(Base):
    __tablename__ = "payment_communication"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("sale_order_id", "idempotency_key"),
        CheckConstraint("status IN ('pending_review', 'confirmed', 'refused')"),
        ForeignKeyConstraint(["payment_group_id", "client_id"],
                             ["payment_group.id", "payment_group.client_id"],
                             name="fk_payment_communication_group_owner"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sale_order_id: Mapped[UUID] = mapped_column(ForeignKey("sale_order.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    payment_group_id: Mapped[UUID | None] = mapped_column(nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending_review", index=True)
    decided_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_user.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PaymentConfirmationCorrection(Base):
    """Registro append-only de uma decisão financeira corrigida pelo admin."""

    __tablename__ = "payment_confirmation_correction"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint(
            "payment_communication_id",
            "idempotency_key",
            name="uq_payment_confirmation_correction_idempotency",
        ),
        Index(
            "ix_payment_confirmation_correction_order_created",
            "sale_order_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_communication_id: Mapped[UUID] = mapped_column(
        ForeignKey("payment_communication.id"), nullable=False, index=True
    )
    sale_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("sale_order.id"), nullable=False, index=True
    )
    actor_admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("admin_user.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128))
    previous_communication_status: Mapped[str] = mapped_column(String(20))
    previous_order_status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PaymentMessageTemplate(Base):
    __tablename__ = "payment_message_template"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (UniqueConstraint("kind"), CheckConstraint("kind IN ('confirmed', 'refused')"))
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(16))
    body: Mapped[str] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PaymentNotificationOutbox(Base):
    __tablename__ = "payment_notification_outbox"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
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
    rendered_body_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class GalleryReopeningRequest(Base):
    """Pedido idempotente de reabertura individual, inclusive do legado."""

    __tablename__ = "gallery_reopening_request"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint(
            "derived_gallery_id",
            "idempotency_key",
            name="uq_gallery_reopening_request_idempotency",
        ),
        UniqueConstraint(
            "parent_gallery_id", "requested_by_client_id", "idempotency_key",
            name="uq_gallery_reopening_canonical_idempotency",
        ),
        UniqueConstraint(
            "photo_folder_id", "requested_by_client_id", "idempotency_key",
            name="uq_gallery_reopening_folder_idempotency",
        ),
        ForeignKeyConstraint(
            ["parent_gallery_id", "requested_by_client_id"],
            ["gallery_client_state.parent_gallery_id", "gallery_client_state.client_id"],
            name="fk_gallery_reopening_canonical_state",
        ),
        ForeignKeyConstraint(
            ["photo_folder_id", "parent_gallery_id", "tenant_id"],
            ["photo_folder.id", "photo_folder.parent_gallery_id", "photo_folder.tenant_id"],
            name="fk_gallery_reopening_folder_scope",
        ),
        ForeignKeyConstraint(
            ["photo_folder_id", "derived_gallery_id", "tenant_id"],
            ["photo_folder.id", "photo_folder.derived_gallery_id", "photo_folder.tenant_id"],
            name="fk_gallery_reopening_derived_folder_scope",
        ),
        CheckConstraint(
            "(derived_gallery_id IS NOT NULL) <> (parent_gallery_id IS NOT NULL)",
            name="ck_gallery_reopening_single_scope",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'refused')",
            name="ck_gallery_reopening_request_status",
        ),
        CheckConstraint(
            "approved_duration_days IS NULL OR approved_duration_days >= 1",
            name="ck_gallery_reopening_approved_duration_days",
        ),
        CheckConstraint(
            "photo_folder_id IS NULL OR status != 'approved' OR approved_duration_days IS NOT NULL",
            name="ck_gallery_reopening_folder_approval_duration",
        ),
        Index(
            "uq_gallery_reopening_request_pending",
            "tenant_id",
            "derived_gallery_id",
            unique=True,
            sqlite_where=text("photo_folder_id IS NULL AND status = 'pending'"),
            postgresql_where=text("photo_folder_id IS NULL AND status = 'pending'"),
        ),
        Index(
            "uq_gallery_reopening_canonical_pending",
            "tenant_id",
            "parent_gallery_id", "requested_by_client_id", unique=True,
            sqlite_where=text("parent_gallery_id IS NOT NULL AND photo_folder_id IS NULL AND status = 'pending'"),
            postgresql_where=text("parent_gallery_id IS NOT NULL AND photo_folder_id IS NULL AND status = 'pending'"),
        ),
        Index(
            "uq_gallery_reopening_folder_pending_client",
            "tenant_id", "photo_folder_id", "requested_by_client_id", unique=True,
            sqlite_where=text("photo_folder_id IS NOT NULL AND status = 'pending'"),
            postgresql_where=text("photo_folder_id IS NOT NULL AND status = 'pending'"),
        ),
        Index(
            "ix_gallery_reopening_folder_approved_until",
            "tenant_id", "photo_folder_id", "status", "approved_until",
        ),
        Index(
            "ix_gallery_reopening_request_status_created",
            "status",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="CASCADE"), nullable=True, index=True
    )
    parent_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parent_gallery.id", ondelete="CASCADE"), nullable=True, index=True
    )
    photo_folder_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("photo_folder.id", ondelete="CASCADE"), nullable=True, index=True
    )
    requested_by_client_id: Mapped[UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    decided_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_user.id"), nullable=True, index=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class GalleryReopeningNotificationOutbox(Base):
    """Aviso assíncrono ao fotógrafo, independente da solicitação persistida."""

    __tablename__ = "gallery_reopening_notification_outbox"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("gallery_reopening_request_id"),
        Index("ix_reopening_notice_request", "gallery_reopening_request_id"),
        CheckConstraint(
            "status IN ('skipped', 'queued', 'processing', 'sent', 'failed')",
            name="ck_gallery_reopening_notification_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_gallery_reopening_notification_attempts"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gallery_reopening_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("gallery_reopening_request.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="skipped", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class ProgressivePricingPreset(Base):
    __tablename__ = "progressive_pricing_preset"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("code", name="uq_progressive_pricing_preset_code"),
        CheckConstraint("version >= 1", name="ck_progressive_pricing_preset_version"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class ProgressivePricingTier(Base):
    __tablename__ = "progressive_pricing_tier"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint(
            "preset_id",
            "minimum_quantity",
            name="uq_progressive_pricing_tier_minimum",
        ),
        CheckConstraint("minimum_quantity >= 1", name="ck_progressive_tier_minimum"),
        CheckConstraint(
            "maximum_quantity IS NULL OR maximum_quantity >= minimum_quantity",
            name="ck_progressive_tier_maximum",
        ),
        CheckConstraint("unit_price_cents >= 0", name="ck_progressive_tier_price"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    preset_id: Mapped[UUID] = mapped_column(
        ForeignKey("progressive_pricing_preset.id", ondelete="CASCADE"), index=True
    )
    minimum_quantity: Mapped[int] = mapped_column(Integer)
    maximum_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_price_cents: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GalleryMembershipNotificationOutbox(Base):
    """Evento administrativo e outbox externa de galerias privadas/membros."""

    __tablename__ = "gallery_membership_notification_outbox"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("event_key"),
        CheckConstraint(
            "event_type IN ('private_created', 'member_joined', 'member_blocked', "
            "'member_unblocked', 'member_unlinked', 'client_logged_in')",
            name="ck_gallery_membership_notification_type",
        ),
        CheckConstraint(
            "admin_status IN ('unread', 'read')",
            name="ck_gallery_membership_notification_admin_status",
        ),
        CheckConstraint(
            "external_status IN ('skipped', 'queued', 'processing', 'sent', 'failed')",
            name="ck_gallery_membership_notification_external_status",
        ),
        CheckConstraint(
            "attempts >= 0",
            name="ck_gallery_membership_notification_attempts",
        ),
        Index(
            "ix_gallery_membership_notification_admin_created",
            "admin_status",
            "created_at",
        ),
        Index(
            "ix_gallery_membership_notification_external_next",
            "external_status",
            "next_attempt_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_key: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    parent_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parent_gallery.id", ondelete="SET NULL"), nullable=True, index=True
    )
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("client.id", ondelete="SET NULL"), nullable=True, index=True
    )
    parent_name_snapshot: Mapped[str] = mapped_column(String(200))
    derived_name_snapshot: Mapped[str] = mapped_column(String(200))
    client_name_snapshot: Mapped[str | None] = mapped_column(String(200), nullable=True)
    admin_status: Mapped[str] = mapped_column(String(16), default="unread", index=True)
    external_status: Mapped[str] = mapped_column(String(16), default="skipped", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(120), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class WhatsAppChannelSettings(Base):
    """Estado operacional não secreto do canal WhatsApp por ambiente."""

    __tablename__ = "whatsapp_channel_settings"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "environment", name="uq_scope_whatsapp_channel_settings_environment"),
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


class WhatsAppTenantCredential(Base):
    """Credencial de webhook isolada por tenant; segredos ficam cifrados."""

    __tablename__ = "whatsapp_tenant_credential"
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    __table_args__ = (
        UniqueConstraint("tenant_id", "environment", name="uq_whatsapp_tenant_credential_scope"),
        UniqueConstraint("environment", "instance_name", name="uq_whatsapp_tenant_instance"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    environment: Mapped[str] = mapped_column(String(32), index=True)
    instance_name: Mapped[str] = mapped_column(String(80), nullable=False)
    webhook_secret_envelope: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class WhatsAppDelivery(Base):
    """Entrega genérica; conteúdo sensível nunca é persistido em texto puro."""

    __tablename__ = "whatsapp_delivery"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
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
    idempotency_key: Mapped[str] = mapped_column(String(160))
    encrypted_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    external_message_id: Mapped[str | None] = mapped_column(String(192), nullable=True)
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
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
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
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (UniqueConstraint("fingerprint"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    fingerprint: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(64))
    external_message_id: Mapped[str | None] = mapped_column(String(192), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MediaDerivative(Base):
    """Derivado local de uma foto; paths nunca são recebidos do navegador."""

    __tablename__ = "media_derivative"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
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
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
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


class PreviewAdjustmentSettings(Base):
    """Configuração legada; preservada desligada após migração por galeria."""

    __tablename__ = "preview_adjustment_settings"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True, primary_key=True,
    )
    __table_args__ = (
        CheckConstraint("id = 1"),
        CheckConstraint("generation >= 1"),
        CheckConstraint("strength BETWEEN 10 AND 100", name="ck_preview_adjustment_strength"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    generation: Mapped[int] = mapped_column(Integer, default=1)
    strength: Mapped[int] = mapped_column(Integer, default=50)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GalleryPreviewSettings(Base):
    """Controles do módulo isolados pela galeria de origem."""

    __tablename__ = "gallery_preview_settings"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint("generation >= 1"),
        CheckConstraint("strength BETWEEN 10 AND 100", name="ck_gallery_preview_strength"),
        CheckConstraint("exposure_tenths BETWEEN -20 AND 20"),
    )
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id", ondelete="CASCADE"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    generation: Mapped[int] = mapped_column(Integer, default=1)
    strength: Mapped[int] = mapped_column(Integer, default=50)
    exposure_tenths: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FolderProcessingSettings(Base):
    """Configuração isolada de processamento por pasta."""

    __tablename__ = "folder_processing_settings"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint("preview_mode IN ('inherit', 'custom', 'off')"),
        CheckConstraint("facial_mode IN ('inherit', 'on', 'off')"),
        CheckConstraint("preview_strength BETWEEN 10 AND 100", name="ck_folder_preview_strength"),
        CheckConstraint("preview_exposure_tenths BETWEEN -20 AND 20"),
        CheckConstraint("revision >= 1"),
    )
    folder_id: Mapped[UUID] = mapped_column(
        ForeignKey("photo_folder.id", ondelete="CASCADE"), primary_key=True
    )
    preview_mode: Mapped[str] = mapped_column(String(16), default="custom", server_default="custom")
    facial_mode: Mapped[str] = mapped_column(String(16), default="on", server_default="on")
    preview_strength: Mapped[int] = mapped_column(Integer, default=50, server_default="50")
    preview_exposure_tenths: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PreviewAdjustment(Base):
    """Fila e resultado substituíveis, sem alterar derivados convencionais."""

    __tablename__ = "preview_adjustment"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'processing', 'ready', 'failed', 'cancelled')"),
        CheckConstraint("attempts >= 0"),
        Index("ix_preview_adjustment_queue", "status", "updated_at"),
    )
    photo_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("photo_asset.id", ondelete="CASCADE"), primary_key=True
    )
    generation: Mapped[int] = mapped_column(Integer)
    fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    claim_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    relative_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(240), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GalleryFacialPolicy(Base):
    """Gate versionado de processamento facial por Galeria pública."""

    __tablename__ = "gallery_facial_policy"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("parent_gallery_id", name="uq_gallery_facial_policy_parent"),
        CheckConstraint(
            "status IN ('disabled', 'pending', 'active', 'suspended')",
            name="ck_gallery_facial_policy_status",
        ),
        CheckConstraint(
            "similarity_threshold_milli BETWEEN 0 AND 1000",
            name="ck_gallery_facial_policy_threshold",
        ),
        CheckConstraint("index_generation >= 0", name="ck_gallery_facial_policy_generation"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="disabled", index=True)
    legal_notice_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    legal_basis_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    retention_policy_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    minor_policy_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model_version: Mapped[str] = mapped_column(String(120))
    quality_version: Mapped[str] = mapped_column(String(120))
    calibration_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    similarity_threshold_milli: Mapped[int] = mapped_column(Integer, default=750)
    index_generation: Mapped[int] = mapped_column(Integer, default=0)
    actor_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_user.id"), nullable=True, index=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class FacialRollout(Base):
    """Escopo persistente e auditável de rollout facial por ambiente/galeria."""

    __tablename__ = "facial_rollout"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint(
            "environment",
            "parent_gallery_id",
            name="uq_facial_rollout_environment_gallery",
        ),
        CheckConstraint(
            "environment IN ('local', 'development', 'test', 'homolog', "
            "'staging', 'prod', 'production')",
            name="ck_facial_rollout_environment",
        ),
        CheckConstraint(
            "status IN ('prepared', 'active', 'suspended', 'revoked')",
            name="ck_facial_rollout_status",
        ),
        CheckConstraint(
            "stage IN ('dark', 'canary', 'limited', 'general')",
            name="ck_facial_rollout_stage",
        ),
        Index(
            "ix_facial_rollout_environment_status",
            "environment",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    environment: Mapped[str] = mapped_column(String(24), index=True)
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="prepared", index=True)
    stage: Mapped[str] = mapped_column(String(16), default="dark", index=True)
    model_version: Mapped[str] = mapped_column(String(120))
    quality_version: Mapped[str] = mapped_column(String(120))
    calibration_version: Mapped[str] = mapped_column(String(120))
    legal_notice_version: Mapped[str] = mapped_column(String(80))
    consent_version: Mapped[str] = mapped_column(String(80))
    legal_basis_reference: Mapped[str] = mapped_column(String(200))
    retention_policy_version: Mapped[str] = mapped_column(String(80))
    approval_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approved_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_user.id"), nullable=True, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class FacialCalibrationApproval(Base):
    """Aprovação humana agregada do limiar e dos grupos avaliados."""

    __tablename__ = "facial_calibration_approval"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint(
            "environment IN ('prod', 'production')",
            name="ck_facial_calibration_environment",
        ),
        CheckConstraint(
            "status IN ('approved', 'revoked')",
            name="ck_facial_calibration_status",
        ),
        CheckConstraint(
            "similarity_threshold_milli BETWEEN 0 AND 1000",
            name="ck_facial_calibration_threshold",
        ),
        CheckConstraint(
            "relevant_group_count > 0 AND approved_group_count = relevant_group_count",
            name="ck_facial_calibration_groups",
        ),
        Index(
            "ix_facial_calibration_effective",
            "environment",
            "model_version",
            "quality_version",
            "calibration_version",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    environment: Mapped[str] = mapped_column(String(24), index=True)
    model_version: Mapped[str] = mapped_column(String(120))
    quality_version: Mapped[str] = mapped_column(String(120))
    calibration_version: Mapped[str] = mapped_column(String(120))
    similarity_threshold_milli: Mapped[int] = mapped_column(Integer)
    criteria_version: Mapped[str] = mapped_column(String(80))
    corpus_reference: Mapped[str] = mapped_column(String(200))
    approval_reference: Mapped[str] = mapped_column(String(200))
    relevant_group_count: Mapped[int] = mapped_column(Integer)
    approved_group_count: Mapped[int] = mapped_column(Integer)
    approved_by_admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("admin_user.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="approved", index=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class FacialRolloutOperation(Base):
    """Recibo agregado da operação protegida, sem conteúdo dos gates."""

    __tablename__ = "facial_rollout_operation"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint(
            "environment IN ('local', 'development', 'test', 'homolog', "
            "'staging', 'prod', 'production')",
            name="ck_facial_rollout_operation_environment",
        ),
        CheckConstraint(
            "action IN ('activate', 'suspend')",
            name="ck_facial_rollout_operation_action",
        ),
        CheckConstraint(
            "stage IN ('dark', 'canary', 'limited', 'general')",
            name="ck_facial_rollout_operation_stage",
        ),
        CheckConstraint(
            "allowlist_count > 0",
            name="ck_facial_rollout_operation_allowlist",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    environment: Mapped[str] = mapped_column(String(24), index=True)
    action: Mapped[str] = mapped_column(String(16), index=True)
    stage: Mapped[str] = mapped_column(String(16), index=True)
    deployment_sha: Mapped[str] = mapped_column(String(40))
    inventory_reference: Mapped[str] = mapped_column(String(200))
    backup_reference: Mapped[str] = mapped_column(String(200))
    gate_set_version: Mapped[str] = mapped_column(String(80))
    allowlist_digest: Mapped[str] = mapped_column(String(64))
    allowlist_count: Mapped[int] = mapped_column(Integer)
    approved_by_admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("admin_user.id"), nullable=False, index=True
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FacialLegalRepresentation(Base):
    """Prova não biométrica e minimizada de representação para consulta infantil."""

    __tablename__ = "facial_legal_representation"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_facial_legal_representation_status",
        ),
        CheckConstraint(
            "authority_kind IN ('parent', 'legal_guardian', 'court_order')",
            name="ck_facial_legal_representation_authority",
        ),
        CheckConstraint(
            "verification_method IN ('admin_attestation', 'trusted_provider')",
            name="ck_facial_legal_representation_verification",
        ),
        CheckConstraint(
            "expires_at > valid_from",
            name="ck_facial_legal_representation_validity",
        ),
        Index(
            "ix_facial_representation_scope_validity",
            "client_id",
            "parent_gallery_id",
            "expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_scope_reference: Mapped[str] = mapped_column(String(200))
    authority_kind: Mapped[str] = mapped_column(String(24))
    verification_method: Mapped[str] = mapped_column(String(32))
    terms_version: Mapped[str] = mapped_column(String(80))
    evidence_reference: Mapped[str] = mapped_column(String(200))
    verified_by_admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("admin_user.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class PhotoAnalysis(Base):
    """Lifecycle da fonte temporária; ausência da linha identifica o legado."""

    __tablename__ = "photo_analysis"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        CheckConstraint("state IN ('receiving', 'pending', 'ready', 'failed', 'reupload_required')",
                        name="ck_photo_analysis_state"),
        CheckConstraint("width > 0 AND height > 0 AND source_bytes >= 0",
                        name="ck_photo_analysis_dimensions"),
    )
    photo_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("photo_asset.id", ondelete="CASCADE"), primary_key=True
    )
    source_fingerprint: Mapped[str] = mapped_column(String(64))
    source_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    pipeline_version: Mapped[str] = mapped_column(String(80), default="highres-v1")
    state: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PhotoFaceEmbedding(Base):
    """Envelope cifrado de uma face indexada e sua qualidade técnica."""

    __tablename__ = "photo_face_embedding"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["photo_asset_id", "parent_gallery_id"],
            ["photo_asset.id", "photo_asset.parent_gallery_id"],
            name="fk_face_embedding_photo_parent",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "photo_asset_id",
            "face_ordinal",
            "model_version",
            "quality_version",
            "preview_fingerprint",
            name="uq_face_embedding_versioned_photo_face",
        ),
        CheckConstraint("face_ordinal >= 0", name="ck_face_embedding_ordinal"),
        CheckConstraint(
            "(bbox_x IS NULL AND bbox_y IS NULL AND bbox_width IS NULL AND bbox_height IS NULL)"
            " OR (bbox_x IS NOT NULL AND bbox_y IS NOT NULL"
            " AND bbox_width IS NOT NULL AND bbox_height IS NOT NULL"
            " AND bbox_x >= 0 AND bbox_y >= 0 AND bbox_width > 0 AND bbox_height > 0"
            " AND bbox_x + bbox_width <= 1 AND bbox_y + bbox_height <= 1)",
            name="ck_face_region_bounds",
        ),
        CheckConstraint(
            "quality_band IN ('best', 'other')", name="ck_face_embedding_quality_band"
        ),
        Index(
            "ix_face_embedding_gallery_model",
            "parent_gallery_id",
            "model_version",
            "quality_version",
        ),
        Index(
            "ix_face_embedding_private_model",
            "derived_gallery_id",
            "model_version",
            "quality_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id"), nullable=False, index=True
    )
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="CASCADE"), nullable=True, index=True
    )
    photo_asset_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    face_ordinal: Mapped[int] = mapped_column(Integer)
    model_id: Mapped[str] = mapped_column(String(80), default="opencv-yunet-sface")
    embedding_dimension: Mapped[int] = mapped_column(Integer, default=128)
    pipeline_version: Mapped[str] = mapped_column(String(80), default="legacy-preview-v1")
    detection_pass: Mapped[str | None] = mapped_column(String(80), nullable=True)
    detection_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_height: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(120))
    quality_version: Mapped[str] = mapped_column(String(120))
    preview_fingerprint: Mapped[str] = mapped_column(String(64))
    quality_band: Mapped[str] = mapped_column(String(16), default="other")
    payload_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    payload_nonce: Mapped[bytes] = mapped_column(LargeBinary)
    key_id: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class FacialSearchRequest(Base):
    """Consulta durável; a referência fica em armazenamento temporário cifrado."""

    __tablename__ = "facial_search_request"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    # Sem FK: reindexação pode remover a região; o worker falha fechado pelo UUID obsoleto.
    reference_region_id: Mapped[UUID | None] = mapped_column(nullable=True)
    reference_source: Mapped[str] = mapped_column(String(24), default="upload", server_default="upload")
    authorization_method: Mapped[str] = mapped_column(String(32), default="legacy", server_default="legacy")
    __table_args__ = (
        CheckConstraint("reference_source IN ('upload', 'indexed_region', 'legacy_unknown')", name="ck_facial_search_source"),
        CheckConstraint("authorization_method IN ('legacy', 'explicit_consent', 'direct_region')", name="ck_facial_search_authorization"),
        CheckConstraint(
            "(authorization_method = 'legacy' AND consent_version IS NOT NULL AND subject_declaration IS NOT NULL) OR "
            "(authorization_method = 'explicit_consent' AND reference_source = 'upload' AND reference_region_id IS NULL "
            "AND consent_version IS NOT NULL AND subject_declaration IS NOT NULL AND representation_reference IS NULL) OR "
            "(authorization_method = 'direct_region' AND reference_source = 'indexed_region' AND (reference_region_id IS NOT NULL OR status IN ('ready', 'no_face', 'multiple_faces', 'low_quality', 'index_incomplete', 'no_candidates', 'cancelled', 'expired', 'failed')) "
            "AND consent_version IS NULL AND subject_declaration IS NULL AND representation_reference IS NULL)",
            name="ck_facial_search_authorization_fields",
        ),
        UniqueConstraint(
            "id", "parent_gallery_id", "client_id", name="uq_facial_search_scope"
        ),
        CheckConstraint(
            "status IN ('queued', 'waiting_index', 'validating_reference', 'searching', "
            "'ranking', 'ready', 'no_face', 'multiple_faces', 'low_quality', "
            "'index_incomplete', 'no_candidates', 'cancelled', 'expired', 'failed')",
            name="ck_facial_search_status",
        ),
        CheckConstraint(
            "subject_declaration IN ('adult', 'minor', 'conditional')",
            name="ck_facial_search_subject_declaration",
        ),
        CheckConstraint(
            "snapshot_total >= 0 AND snapshot_ready >= 0 AND snapshot_ready <= snapshot_total",
            name="ck_facial_search_snapshot_progress",
        ),
        CheckConstraint(
            "compare_total >= 0 AND compare_done >= 0 AND compare_done <= compare_total",
            name="ck_facial_search_compare_progress",
        ),
        Index("ix_facial_search_client_gallery_expiry", "client_id", "parent_gallery_id", "expires_at"),
        # O schema implantado 0089 mantém engines históricos; a aplicação cria
        # novas buscas exclusivamente com SFace e o worker recusa outras engines.
        CheckConstraint(
            "search_engine IN ('opencv-yunet-sface', 'google-embeddinggemma-2')",
            name="ck_facial_search_engine",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id"), nullable=False, index=True
    )
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), nullable=False, index=True)
    policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("gallery_facial_policy.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    consent_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    legal_notice_version: Mapped[str] = mapped_column(String(80))
    subject_declaration: Mapped[str | None] = mapped_column(String(16), nullable=True)
    representation_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model_version: Mapped[str] = mapped_column(String(120))
    search_engine: Mapped[str] = mapped_column(
        String(64), default="opencv-yunet-sface", server_default="opencv-yunet-sface"
    )
    quality_version: Mapped[str] = mapped_column(String(120))
    index_generation: Mapped[int] = mapped_column(Integer)
    snapshot_total: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_ready: Mapped[int] = mapped_column(Integer, default=0)
    compare_total: Mapped[int] = mapped_column(Integer, default=0)
    compare_done: Mapped[int] = mapped_column(Integer, default=0)
    reference_locator_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    reference_locator_nonce: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    reference_key_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reference_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class FacialSearchConsentProof(Base):
    """Comprovante mínimo preservado quando a busca facial operacional é removida."""

    __tablename__ = "facial_search_consent_proof"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "source_search_request_id",
            name="uq_facial_consent_proof_request",
        ),
        CheckConstraint(
            "authorization_method IN ('legacy', 'explicit_consent', 'direct_region')",
            name="ck_facial_consent_proof_method",
        ),
        CheckConstraint(
            "subject_declaration IS NULL OR subject_declaration IN ('adult', 'minor', 'conditional')",
            name="ck_facial_consent_proof_subject",
        ),
        CheckConstraint(
            "consent_version IS NOT NULL OR authorization_method IN ('legacy', 'direct_region')",
            name="ck_facial_consent_proof_consent_method",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    source_search_request_id: Mapped[UUID] = mapped_column()
    parent_gallery_id: Mapped[UUID] = mapped_column()
    client_id: Mapped[UUID] = mapped_column()
    authorization_method: Mapped[str] = mapped_column(String(32))
    consent_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    legal_notice_version: Mapped[str] = mapped_column(String(80))
    subject_declaration: Mapped[str | None] = mapped_column(String(16), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FacialSearchSnapshotItem(Base):
    """Foto/fingerprint congelados no início da consulta, sem inferência."""

    __tablename__ = "facial_search_snapshot_item"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["search_request_id", "parent_gallery_id", "client_id"],
            [
                "facial_search_request.id",
                "facial_search_request.parent_gallery_id",
                "facial_search_request.client_id",
            ],
            name="fk_facial_snapshot_search_scope",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["photo_asset_id", "parent_gallery_id"],
            ["photo_asset.id", "photo_asset.parent_gallery_id"],
            name="fk_facial_snapshot_photo_parent",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "search_request_id", "photo_asset_id", name="uq_facial_snapshot_photo"
        ),
        CheckConstraint(
            "status IN ('pending', 'ready', 'excluded')",
            name="ck_facial_snapshot_status",
        ),
        Index("ix_facial_snapshot_request_status", "search_request_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    search_request_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    parent_gallery_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    client_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    photo_asset_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    preview_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class FacialSearchCandidate(Base):
    """Foto autorizada e ordenada, sem persistir similaridade ou identidade."""

    __tablename__ = "facial_search_candidate"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    match_class: Mapped[str] = mapped_column(String(16), default="matched")
    __table_args__ = (
        ForeignKeyConstraint(
            ["search_request_id", "parent_gallery_id", "client_id"],
            [
                "facial_search_request.id",
                "facial_search_request.parent_gallery_id",
                "facial_search_request.client_id",
            ],
            name="fk_facial_candidate_search_scope",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["photo_asset_id", "parent_gallery_id"],
            ["photo_asset.id", "photo_asset.parent_gallery_id"],
            name="fk_facial_candidate_photo_parent",
            ondelete="CASCADE",
        ),
        UniqueConstraint("search_request_id", "photo_asset_id", name="uq_facial_candidate_photo"),
        CheckConstraint("rank >= 1", name="ck_facial_candidate_rank"),
        CheckConstraint(
            "quality_band IN ('best', 'other')", name="ck_facial_candidate_quality_band"
        ),
        Index("ix_facial_candidate_request_rank", "search_request_id", "rank"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    search_request_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    parent_gallery_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    client_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    photo_asset_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer)
    quality_band: Mapped[str] = mapped_column(String(16))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FacialJob(Base):
    """Job facial com lease, prioridade e idempotência persistentes."""

    __tablename__ = "facial_job"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_facial_job_idempotency"),
        # Preservado conforme schema 0089 para ler jobs legados sem reprocessá-los.
        CheckConstraint(
            "kind IN ('index', 'index_gemma', 'purge', 'search', 'search_gemma', 'cleanup')", name="ck_facial_job_kind"
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_facial_job_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_facial_job_attempts"),
        CheckConstraint("priority >= 0", name="ck_facial_job_priority"),
        CheckConstraint(
            "progress_total >= 0 AND progress_done >= 0 AND progress_done <= progress_total",
            name="ck_facial_job_progress",
        ),
        Index("ix_facial_job_pending", "status", "priority", "available_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    idempotency_key: Mapped[str] = mapped_column(String(240), unique=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id"), nullable=False, index=True
    )
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="CASCADE"), nullable=True, index=True
    )
    photo_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("photo_asset.id"), nullable=True, index=True
    )
    search_request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("facial_search_request.id"), nullable=True, index=True
    )
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    quality_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preview_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    progress_done: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class FacialSearchNotificationOutbox(Base):
    """Mensagem transacional cifrada, neutra e idempotente por consulta."""

    __tablename__ = "facial_search_notification_outbox"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["search_request_id", "parent_gallery_id", "client_id"],
            [
                "facial_search_request.id",
                "facial_search_request.parent_gallery_id",
                "facial_search_request.client_id",
            ],
            name="fk_facial_notification_search_scope",
            ondelete="CASCADE",
        ),
        UniqueConstraint("idempotency_key", name="uq_facial_notification_idempotency"),
        CheckConstraint(
            "result_kind IN ('ready', 'no_candidates', 'failed')",
            name="ck_facial_notification_result_kind",
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'sent', 'failed', 'cancelled')",
            name="ck_facial_notification_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_facial_notification_attempts"),
        Index("ix_facial_notification_pending", "status", "available_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    search_request_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    parent_gallery_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    client_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    result_kind: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    idempotency_key: Mapped[str] = mapped_column(String(240), unique=True)
    payload_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    payload_nonce: Mapped[bytes] = mapped_column(LargeBinary)
    key_id: Mapped[str] = mapped_column(String(80))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(192), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class AuthChallenge(Base):
    __tablename__ = "auth_challenge"
    tenant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True,
    )
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
    __table_args__ = (
        CheckConstraint("kind != 'client_otp' OR tenant_id IS NOT NULL",
                        name="ck_auth_challenge_client_context"),
    )


class NotificationSetting(Base):
    __tablename__ = "notification_setting"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True, primary_key=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    whatsapp_disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    push_disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    whatsapp_body: Mapped[str] = mapped_column(String(500))
    push_title: Mapped[str] = mapped_column(String(60))
    push_body: Mapped[str] = mapped_column(String(140))
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("version >= 1"),)


class NotificationMilestone(Base):
    """Marco canônico persistente, independente de seleção/carrinho atuais."""
    __tablename__ = "notification_milestone"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    parent_gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("parent_gallery.id", ondelete="CASCADE"), primary_key=True
    )
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("client.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(24), primary_key=True)
    baseline: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("kind IN ('first_access', 'first_selection')"),)


class PushSubscription(Base):
    """Endpoint e chaves exclusivamente cifrados; fingerprint não reversível."""
    __tablename__ = "push_subscription"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    endpoint_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    installation_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    encrypted_subscription: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16))
    subject_id: Mapped[UUID] = mapped_column(index=True)
    client_subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("client.id"), nullable=True)
    admin_subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("admin_user.id"), nullable=True)
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("auth_session.id", ondelete="SET NULL"), nullable=True
    )
    generation: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'client')"),
        CheckConstraint(
            "(role = 'client' AND client_subject_id IS NOT NULL "
            "AND client_subject_id = subject_id AND admin_subject_id IS NULL) OR "
            "(role = 'admin' AND admin_subject_id IS NOT NULL "
            "AND admin_subject_id = subject_id AND client_subject_id IS NULL)",
            name="ck_push_subscription_typed_subject",
        ),
        CheckConstraint("generation >= 1"),
        Index("ix_push_subscription_owner_active", "role", "subject_id", "active"),
    )


class NotificationEvent(Base):
    __tablename__ = "notification_event"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_key: Mapped[str] = mapped_column(String(192), unique=True)
    event_type: Mapped[str] = mapped_column(String(32))
    parent_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parent_gallery.id", ondelete="CASCADE"), nullable=True
    )
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="CASCADE"), nullable=True
    )
    client_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("client.id", ondelete="CASCADE"), nullable=True
    )
    sale_order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sale_order.id", ondelete="CASCADE"), nullable=True
    )
    template_version: Mapped[int] = mapped_column(Integer)
    push_title: Mapped[str] = mapped_column(String(60))
    push_body: Mapped[str] = mapped_column(String(140))
    whatsapp_body: Mapped[str] = mapped_column(String(500))
    target_path: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class NotificationDelivery(Base):
    __tablename__ = "notification_delivery"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("notification_event.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(16))
    recipient_role: Mapped[str] = mapped_column(String(16))
    recipient_id: Mapped[UUID] = mapped_column(index=True)
    client_recipient_id: Mapped[UUID | None] = mapped_column(ForeignKey("client.id"), nullable=True)
    admin_recipient_id: Mapped[UUID | None] = mapped_column(ForeignKey("admin_user.id"), nullable=True)
    device_key: Mapped[str] = mapped_column(String(64), default="whatsapp")
    subscription_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("push_subscription.id", ondelete="CASCADE"), nullable=True
    )
    subscription_generation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_token: Mapped[UUID | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        UniqueConstraint("event_id", "channel", "recipient_role", "recipient_id", "device_key"),
        CheckConstraint("channel IN ('push', 'whatsapp')"),
        CheckConstraint("recipient_role IN ('admin', 'client')"),
        CheckConstraint(
            "(recipient_role = 'client' AND client_recipient_id IS NOT NULL "
            "AND client_recipient_id = recipient_id AND admin_recipient_id IS NULL) OR "
            "(recipient_role = 'admin' AND admin_recipient_id IS NOT NULL "
            "AND admin_recipient_id = recipient_id AND client_recipient_id IS NULL)",
            name="ck_notification_delivery_typed_recipient",
        ),
        CheckConstraint("attempts >= 0"),
        CheckConstraint("status IN ('queued', 'processing', 'accepted', 'failed', "
                        "'unknown', 'expired', 'cancelled')"),
        Index("ix_notification_delivery_ready", "channel", "status", "next_attempt_at"),
    )


class PrivateUploadBatch(Base):
    __tablename__ = "private_upload_batch"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("derived_gallery.id", ondelete="CASCADE"), index=True, nullable=True
    )
    parent_gallery_id: Mapped[UUID | None] = mapped_column(
        index=True, nullable=True
    )
    folder_id: Mapped[UUID | None] = mapped_column(
        index=True, nullable=True
    )
    actor_admin_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"))
    status: Mapped[str] = mapped_column(String(16), default="open")
    recipient_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    announced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("status IN ('open', 'closed', 'completed')"),
        ForeignKeyConstraint(
            ["parent_gallery_id", "tenant_id"],
            ["parent_gallery.id", "parent_gallery.tenant_id"],
            name="fk_private_upload_batch_parent_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["folder_id", "parent_gallery_id", "tenant_id"],
            ["photo_folder.id", "photo_folder.parent_gallery_id", "photo_folder.tenant_id"],
            name="fk_private_upload_batch_folder_parent_tenant",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "(derived_gallery_id IS NOT NULL AND parent_gallery_id IS NULL AND folder_id IS NULL) OR "
            "(derived_gallery_id IS NULL AND parent_gallery_id IS NOT NULL AND folder_id IS NOT NULL)",
            name="ck_private_upload_batch_scope",
        ),
    )


class PrivateUploadBatchAsset(Base):
    __tablename__ = "private_upload_batch_asset"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id"), index=True,
    )
    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("private_upload_batch.id", ondelete="CASCADE"), primary_key=True
    )
    photo_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("photo_asset.id", ondelete="CASCADE"), primary_key=True
    )


class AuthSession(Base):
    __tablename__ = "auth_session"
    tenant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True,
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16), index=True)
    subject_id: Mapped[UUID] = mapped_column(index=True)
    client_subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("client.id"), nullable=True)
    admin_subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("admin_user.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'client')", name="ck_auth_session_role"),
        CheckConstraint(
            "revoked_at IS NOT NULL OR (tenant_id IS NOT NULL AND "
            "((role = 'client' AND client_subject_id IS NOT NULL "
            "AND client_subject_id = subject_id AND admin_subject_id IS NULL) OR "
            "(role = 'admin' AND admin_subject_id IS NOT NULL "
            "AND admin_subject_id = subject_id AND client_subject_id IS NULL)))",
            name="ck_auth_session_typed_context",
        ),
    )


class AuditEvent(Base):
    __tablename__ = "audit_event"
    tenant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True,
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event: Mapped[str] = mapped_column(String(80), index=True)
    subject: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PlatformAdminEvent(Base):
    """Auditoria global sanitizada, sem payload livre nem retenção automática."""
    __tablename__ = "platform_admin_event"
    __table_args__ = (
        CheckConstraint("result IN ('success','denied')", name="ck_platform_admin_result"),
        CheckConstraint("origin = 'web_console'", name="ck_platform_admin_origin"),
        CheckConstraint("action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied','photographer.totp_revoked','photographer.totp_revoke_denied','tenant.host_ready','tenant.host_activation_denied','media_archive.recovery_pricing_updated','tenant.reopened','tenant.media_deletion_requested','tenant.media_deletion_retry','tenant.profile_reduced','credit.granted','credit.revoked','credit.package_created','credit.package_updated','credit.purchase_reviewed')", name="ck_platform_admin_action"),
        CheckConstraint(
            "action != 'tenant.profile_reduced' OR (result = 'success' AND tenant_id IS NOT NULL "
            "AND object_id IS NOT NULL AND previous_status IS NOT NULL AND next_status IS NOT NULL "
            "AND previous_status = 'retained' AND next_status = 'reduced')",
            name="ck_platform_admin_profile_reduced_context",
        ),
        CheckConstraint(
            "action NOT IN ('tenant.media_deletion_requested','tenant.media_deletion_retry') OR "
            "(result = 'success' AND tenant_id IS NOT NULL AND object_id IS NOT NULL "
            "AND previous_status IS NOT NULL AND next_status IS NOT NULL)",
            name="ck_platform_admin_media_deletion_context",
        ),
        CheckConstraint("evidence_sha256 IS NULL OR length(evidence_sha256) = 64", name="ck_platform_admin_evidence_sha256"),
        CheckConstraint("action != 'tenant.host_ready' OR (result = 'success' AND tenant_id IS NOT NULL AND object_id IS NOT NULL AND previous_status IS NOT NULL AND previous_status = 'reserved' AND next_status IS NOT NULL AND next_status = 'ready' AND evidence_sha256 IS NOT NULL)", name="ck_platform_admin_host_ready_context"),
        CheckConstraint("action != 'tenant.reopened' OR (result = 'success' AND tenant_id IS NOT NULL AND object_id IS NOT NULL AND previous_status = 'closed' AND next_status = 'open')", name="ck_platform_admin_tenant_reopened_context"),
        CheckConstraint("reason_code IS NULL OR reason_code IN ('lost_device','authenticator_unavailable','assisted_recovery')", name="ck_platform_admin_reason"),
        CheckConstraint("target_version IS NULL OR length(target_version) = 64", name="ck_platform_admin_support_version"),
        CheckConstraint("action NOT IN ('photographer.totp_revoked','photographer.totp_revoke_denied') OR (reason_code IS NOT NULL AND target_version IS NOT NULL AND object_id IS NOT NULL AND (action != 'photographer.totp_revoked' OR tenant_id IS NOT NULL))", name="ck_platform_admin_support_context"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[UUID | None] = mapped_column(unique=True, nullable=True)
    actor_admin_id: Mapped[UUID] = mapped_column(ForeignKey("admin_user.id"))
    object_id: Mapped[UUID | None] = mapped_column(nullable=True)
    tenant_id: Mapped[UUID | None] = mapped_column(ForeignKey("tenant.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40))
    reason_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    next_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result: Mapped[str] = mapped_column(String(16))
    origin: Mapped[str] = mapped_column(String(24), default="web_console")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


@event.listens_for(PlatformAdminEvent, "before_update")
@event.listens_for(PlatformAdminEvent, "before_delete")
def _protect_platform_admin_event(_mapper, _connection, _target):
    raise RuntimeError("Auditoria global é append-only.")


# Carteira de créditos do fotógrafo. O saldo permanece reconstruível do ledger;
# nenhum campo de saldo editável é armazenado nesta configuração.
class TenantCreditWallet(Base):
    __tablename__ = "tenant_credit_wallet"
    __table_args__ = (
        CheckConstraint("mode IN ('finite', 'unmetered')", name="ck_tenant_credit_wallet_mode"),
        Index(
            "uq_tenant_credit_wallet_single_unmetered", "mode", unique=True,
            postgresql_where=text("mode = 'unmetered'"),
            sqlite_where=text("mode = 'unmetered'"),
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16), default="finite", server_default=text("'finite'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now, server_default=text("CURRENT_TIMESTAMP"),
    )


class PhotographerCreditPackage(Base):
    """Catálogo comercial global administrado somente pelo proprietário persistido."""

    __tablename__ = "photographer_credit_package"
    __table_args__ = (
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 120", name="ck_credit_package_name"),
        CheckConstraint("credit_quantity > 0", name="ck_credit_package_quantity"),
        CheckConstraint(
            "(price_cents IS NULL AND currency_code IS NULL) OR "
            "(price_cents > 0 AND currency_code IS NOT NULL "
            "AND length(currency_code) = 3 AND currency_code = upper(currency_code))",
            name="ck_credit_package_price_currency",
        ),
        CheckConstraint(
            "active = false OR (price_cents IS NOT NULL AND currency_code IS NOT NULL)",
            name="ck_credit_package_active_price",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    credit_quantity: Mapped[int] = mapped_column(Integer)
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_by_admin_id: Mapped[UUID] = mapped_column(ForeignKey("platform_owner.admin_user_id"))
    updated_by_admin_id: Mapped[UUID] = mapped_column(ForeignKey("platform_owner.admin_user_id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now, server_default=text("CURRENT_TIMESTAMP"),
    )


class PhotoCreditOperation(Base):
    """Reserva idempotente por tenant e identidade persistente do PhotoAsset."""

    __tablename__ = "photo_credit_operation"
    __table_args__ = (
        ForeignKeyConstraint(
            ["photo_asset_id", "tenant_id"], ["photo_asset.id", "photo_asset.tenant_id"],
            name="fk_credit_operation_photo_tenant",
        ),
        UniqueConstraint(
            "tenant_id", "photo_asset_id_snapshot", name="uq_credit_operation_asset_snapshot",
        ),
        CheckConstraint(
            "photo_asset_id IS NULL OR photo_asset_id = photo_asset_id_snapshot",
            name="ck_credit_operation_photo_snapshot",
        ),
        CheckConstraint("length(payload_fingerprint) = 64", name="ck_credit_operation_fingerprint"),
        CheckConstraint("quantity = 1", name="ck_credit_operation_quantity"),
        CheckConstraint(
            "status IN ('reserved', 'consumed', 'released', 'reconciliation_required')",
            name="ck_credit_operation_status",
        ),
        Index("ix_credit_operation_reconcile", "tenant_id", "status", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    photo_asset_id: Mapped[UUID | None] = mapped_column(nullable=True)
    photo_asset_id_snapshot: Mapped[UUID] = mapped_column()
    storage_key_snapshot: Mapped[str] = mapped_column(String(1024))
    payload_fingerprint: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    status: Mapped[str] = mapped_column(
        String(32), default="reserved", server_default=text("'reserved'"), index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now, server_default=text("CURRENT_TIMESTAMP"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PhotographerCreditEntry(Base):
    """Movimento imutável; delta e referências permitem reconstruir o saldo."""

    __tablename__ = "photographer_credit_entry"
    __table_args__ = (
        ForeignKeyConstraint(
            ["operation_id", "tenant_id"],
            ["photo_credit_operation.id", "photo_credit_operation.tenant_id"],
            name="fk_credit_entry_operation_tenant",
        ),
        ForeignKeyConstraint(
            ["archive_operation_id", "tenant_id"],
            ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_credit_entry_archive_operation_tenant",
        ),
        ForeignKeyConstraint(
            ["source_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_credit_entry_source_tenant",
        ),
        CheckConstraint(
            "entry_type IN ('owner_grant', 'grant_revocation', 'purchase', "
            "'upload_consumption', 'archive_recovery', 'purchase_reversal', 'correction')",
            name="ck_credit_entry_type",
        ),
        CheckConstraint(
            "(entry_type IN ('owner_grant', 'purchase') AND delta > 0) OR "
            "(entry_type IN ('grant_revocation', 'upload_consumption', 'archive_recovery', 'purchase_reversal') AND delta < 0) OR "
            "(entry_type = 'correction' AND delta <> 0)",
            name="ck_credit_entry_delta",
        ),
        CheckConstraint(
            "entry_type <> 'upload_consumption' OR (operation_id IS NOT NULL AND delta = -1)",
            name="ck_credit_entry_upload_operation",
        ),
        CheckConstraint(
            "(entry_type = 'archive_recovery' AND archive_operation_id IS NOT NULL "
            "AND operation_id IS NULL AND delta < 0) OR "
            "(entry_type <> 'archive_recovery' AND archive_operation_id IS NULL)",
            name="ck_credit_entry_archive_operation",
        ),
        CheckConstraint(
            "entry_type <> 'purchase' OR package_id IS NOT NULL",
            name="ck_credit_entry_purchase_package",
        ),
        CheckConstraint(
            "entry_type NOT IN ('grant_revocation', 'purchase_reversal', 'upload_consumption') "
            "OR source_entry_id IS NOT NULL",
            name="ck_credit_entry_source_required",
        ),
        CheckConstraint(
            "entry_type NOT IN ('owner_grant', 'grant_revocation') "
            "OR global_owner_admin_id IS NOT NULL",
            name="ck_credit_entry_owner_authority",
        ),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_credit_entry_idempotency"),
        Index(
            "uq_credit_entry_operation_consumption", "tenant_id", "operation_id", unique=True,
            postgresql_where=text("entry_type = 'upload_consumption' AND operation_id IS NOT NULL"),
            sqlite_where=text("entry_type = 'upload_consumption' AND operation_id IS NOT NULL"),
        ),
        Index(
            "uq_credit_entry_archive_operation_consumption",
            "tenant_id", "archive_operation_id", unique=True,
            postgresql_where=text("entry_type = 'archive_recovery' AND archive_operation_id IS NOT NULL"),
            sqlite_where=text("entry_type = 'archive_recovery' AND archive_operation_id IS NOT NULL"),
        ),
        Index("ix_credit_entry_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    entry_type: Mapped[str] = mapped_column(String(32))
    delta: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(240))
    operation_id: Mapped[UUID | None] = mapped_column(nullable=True)
    archive_operation_id: Mapped[UUID | None] = mapped_column(nullable=True)
    source_entry_id: Mapped[UUID | None] = mapped_column(nullable=True)
    package_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("photographer_credit_package.id"), nullable=True,
    )
    actor_admin_id: Mapped[UUID | None] = mapped_column(ForeignKey("admin_user.id"), nullable=True)
    global_owner_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_owner.admin_user_id"), nullable=True,
    )
    source_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, server_default=text("CURRENT_TIMESTAMP"),
    )


class MercadoPagoCreditPurchase(Base):
    """Compra Orders: pagador tenant-bound, recebedor vinculado ao proprietário."""

    __tablename__ = "mercadopago_credit_purchase"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "buyer_admin_id"],
            ["tenant_admin.tenant_id", "tenant_admin.admin_user_id"],
            name="fk_credit_purchase_buyer_membership",
        ),
        ForeignKeyConstraint(
            ["receiver_account_id", "receiver_tenant_id"],
            ["mercadopago_account.id", "mercadopago_account.tenant_id"],
            name="fk_credit_purchase_receiver_account_tenant",
        ),
        ForeignKeyConstraint(
            ["ledger_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_credit_purchase_ledger_tenant",
        ),
        UniqueConstraint("id", "tenant_id", name="uq_credit_purchase_id_tenant"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_credit_purchase_idempotency"),
        UniqueConstraint("receiver_account_id", "external_reference", name="uq_credit_purchase_external_reference"),
        UniqueConstraint("receiver_account_id", "provider_order_id", name="uq_credit_purchase_provider_order"),
        UniqueConstraint("ledger_entry_id", name="uq_credit_purchase_ledger_entry"),
        CheckConstraint("credit_quantity > 0", name="ck_credit_purchase_quantity"),
        CheckConstraint("total_cents > 0", name="ck_credit_purchase_total"),
        CheckConstraint("currency_code = 'BRL'", name="ck_credit_purchase_currency"),
        CheckConstraint(
            "method IS NULL OR method IN ('credit_card', 'pix')", name="ck_credit_purchase_method",
        ),
        CheckConstraint(
            "state IN ('prepared', 'submitting', 'initiated', 'pending', 'processing', 'confirmed', "
            "'rejected', 'canceled', 'expired', 'refunded', 'partially_refunded', 'charged_back', "
            "'verification_required', 'abandoned')",
            name="ck_credit_purchase_state",
        ),
        CheckConstraint(
            "state <> 'confirmed' OR (provider_order_id IS NOT NULL AND provider_payment_id IS NOT NULL "
            "AND confirmed_at IS NOT NULL AND ledger_entry_id IS NOT NULL)",
            name="ck_credit_purchase_confirmed",
        ),
        CheckConstraint(
            "review_status IN ('none', 'pending', 'released', 'restricted')",
            name="ck_credit_purchase_review_status",
        ),
        CheckConstraint(
            "(review_status IN ('none', 'pending') AND reviewed_by_admin_id IS NULL "
            "AND reviewed_at IS NULL AND review_note IS NULL) OR "
            "(review_status IN ('released', 'restricted') AND reviewed_by_admin_id IS NOT NULL "
            "AND reviewed_at IS NOT NULL AND review_note IS NOT NULL)",
            name="ck_credit_purchase_review_resolution",
        ),
        Index("ix_credit_purchase_active", "tenant_id", "active", "created_at"),
        Index("ix_credit_purchase_reconcile", "active", "next_check_at"),
        Index("ix_credit_purchase_review_state", "tenant_id", "review_status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    buyer_admin_id: Mapped[UUID] = mapped_column()
    owner_admin_id: Mapped[UUID] = mapped_column(ForeignKey("platform_owner.admin_user_id"))
    receiver_tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"))
    # A FK composta abaixo vincula a conta ao tenant recebedor, não ao comprador.
    receiver_account_id: Mapped[UUID] = mapped_column()
    package_id: Mapped[UUID] = mapped_column(ForeignKey("photographer_credit_package.id"))
    package_name: Mapped[str] = mapped_column(String(120))
    credit_quantity: Mapped[int] = mapped_column(Integer)
    total_cents: Mapped[int] = mapped_column(Integer)
    currency_code: Mapped[str] = mapped_column(String(3), default="BRL", server_default=text("'BRL'"))
    idempotency_key: Mapped[str] = mapped_column(String(160))
    external_reference: Mapped[str] = mapped_column(String(64))
    method: Mapped[str | None] = mapped_column(String(24), nullable=True)
    state: Mapped[str] = mapped_column(String(32), default="prepared", server_default=text("'prepared'"))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    provider_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    order_detail: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transaction_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transaction_detail: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pix_copy_paste: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(48), nullable=True)
    check_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    next_check_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ledger_entry_id: Mapped[UUID | None] = mapped_column(nullable=True)
    review_status: Mapped[str] = mapped_column(String(16), default="none", server_default=text("'none'"))
    reviewed_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_owner.admin_user_id"), nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now, server_default=text("CURRENT_TIMESTAMP"),
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MercadoPagoCreditPurchaseEvent(Base):
    """Histórico financeiro append-only e limitado a mudanças da compra."""

    __tablename__ = "mercadopago_credit_purchase_event"
    __table_args__ = (
        ForeignKeyConstraint(
            ["purchase_id", "tenant_id"],
            ["mercadopago_credit_purchase.id", "mercadopago_credit_purchase.tenant_id"],
            name="fk_credit_purchase_event_scope",
        ),
        UniqueConstraint("id", "tenant_id", name="uq_credit_purchase_event_id_tenant"),
        UniqueConstraint("purchase_id", "event_key", name="uq_credit_purchase_event_key"),
        CheckConstraint(
            "event_type IN ('prepared', 'submission_started', 'provider_updated', 'initiated', "
            "'pending', 'processing', 'confirmed', 'rejected', 'canceled', 'expired', "
            "'refunded', 'partially_refunded', 'charged_back', 'verification_required', "
            "'abandoned', 'owner_reviewed')",
            name="ck_credit_purchase_event_type",
        ),
        Index("ix_credit_purchase_event_history", "tenant_id", "purchase_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    purchase_id: Mapped[UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(32))
    event_key: Mapped[str] = mapped_column(String(240))
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, server_default=text("CURRENT_TIMESTAMP"),
    )


class PhotographerCreditAllocationEvent(Base):
    """Alocação append-only entre uma origem de crédito e seu uso/reserva."""

    __tablename__ = "photographer_credit_allocation_event"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_credit_allocation_source_tenant",
        ),
        ForeignKeyConstraint(
            ["operation_id", "tenant_id"],
            ["photo_credit_operation.id", "photo_credit_operation.tenant_id"],
            name="fk_credit_allocation_operation_tenant",
        ),
        ForeignKeyConstraint(
            ["credit_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_credit_allocation_entry_tenant",
        ),
        CheckConstraint(
            "event_type IN ('reserved', 'consumed', 'released', 'revoked')",
            name="ck_credit_allocation_event_type",
        ),
        CheckConstraint("quantity > 0", name="ck_credit_allocation_quantity"),
        CheckConstraint(
            "(event_type IN ('reserved', 'released') AND operation_id IS NOT NULL AND credit_entry_id IS NULL) OR "
            "(event_type = 'consumed' AND operation_id IS NOT NULL AND credit_entry_id IS NOT NULL) OR "
            "(event_type = 'revoked' AND operation_id IS NULL AND credit_entry_id IS NOT NULL)",
            name="ck_credit_allocation_event_context",
        ),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_credit_allocation_idempotency"),
        Index("ix_credit_allocation_source_history", "tenant_id", "source_entry_id", "occurred_at"),
        Index("ix_credit_allocation_operation_history", "tenant_id", "operation_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    source_entry_id: Mapped[UUID] = mapped_column(nullable=False)
    operation_id: Mapped[UUID | None] = mapped_column(nullable=True)
    credit_entry_id: Mapped[UUID | None] = mapped_column(nullable=True)
    event_type: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(240))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, server_default=text("CURRENT_TIMESTAMP"),
    )


class MediaArchiveRecoveryCreditAllocationEvent(Base):
    """Alocação imutável de créditos de origem para um pull de arquivo frio."""

    __tablename__ = "media_archive_recovery_credit_allocation_event"
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id", name="fk_media_archive_credit_allocation_tenant"), index=True,
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_media_archive_credit_allocation_source_tenant",
        ),
        ForeignKeyConstraint(
            ["operation_id", "tenant_id"],
            ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_credit_allocation_operation_tenant",
        ),
        ForeignKeyConstraint(
            ["credit_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_media_archive_credit_allocation_entry_tenant",
        ),
        CheckConstraint(
            "event_type IN ('reserved', 'consumed', 'released')",
            name="ck_media_archive_credit_allocation_event_type",
        ),
        CheckConstraint("quantity > 0", name="ck_media_archive_credit_allocation_quantity"),
        CheckConstraint(
            "(event_type IN ('reserved', 'released') AND credit_entry_id IS NULL) OR "
            "(event_type = 'consumed' AND credit_entry_id IS NOT NULL)",
            name="ck_media_archive_credit_allocation_event_context",
        ),
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_media_archive_credit_allocation_idempotency",
        ),
        Index(
            "ix_media_archive_credit_allocation_source_history",
            "tenant_id", "source_entry_id", "occurred_at",
        ),
        Index(
            "ix_media_archive_credit_allocation_operation_history",
            "tenant_id", "operation_id", "occurred_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    operation_id: Mapped[UUID] = mapped_column(index=True)
    source_entry_id: Mapped[UUID] = mapped_column(nullable=False)
    credit_entry_id: Mapped[UUID | None] = mapped_column(nullable=True)
    event_type: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(240))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, server_default=text("CURRENT_TIMESTAMP"),
    )


class PhotoCreditOperationEvent(Base):
    """Evento append-only de recuperação e transição da operação de upload."""

    __tablename__ = "photo_credit_operation_event"
    __table_args__ = (
        ForeignKeyConstraint(
            ["operation_id", "tenant_id"],
            ["photo_credit_operation.id", "photo_credit_operation.tenant_id"],
            name="fk_credit_operation_event_scope",
        ),
        CheckConstraint(
            "event_type IN ('reserved', 'upload_attempted', 'source_durable', 'consumed', "
            "'released', 'reconciliation_required', 'reconciled_consumed', 'reconciled_released')",
            name="ck_credit_operation_event_type",
        ),
        Index("ix_credit_operation_event_history", "tenant_id", "operation_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    operation_id: Mapped[UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(32))
    actor_admin_id: Mapped[UUID | None] = mapped_column(ForeignKey("admin_user.id"), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, server_default=text("CURRENT_TIMESTAMP"),
    )


# Registra o modelo global antes de resolver as FKs do catálogo e do ledger.
from app.system_monitor import models as _system_monitor_models  # noqa: F401

apply_ownership_constraints(Base.metadata)


@event.listens_for(MediaArchiveRecoveryCreditAllocationEvent, "before_update")
@event.listens_for(MediaArchiveRecoveryCreditAllocationEvent, "before_delete")
def _protect_media_archive_recovery_credit_allocation_event(_mapper, _connection, _target):
    raise RuntimeError("Alocações de recuperação são append-only.")


@event.listens_for(MediaArchiveRecoveryRequest, "before_update")
@event.listens_for(MediaArchiveRecoveryRequest, "before_delete")
def _protect_media_archive_recovery_request(_mapper, _connection, _target):
    raise RuntimeError("Pedidos de recuperação são imutáveis.")


@event.listens_for(MediaArchiveRecoveryCreditReservation, "before_update")
def _protect_media_archive_recovery_reservation_identity(_mapper, _connection, target):
    from sqlalchemy import inspect as sa_inspect

    state = sa_inspect(target)
    immutable_fields = (
        "id", "tenant_id", "operation_id", "reserved_credits", "created_at",
    )
    if any(state.attrs[name].history.has_changes() for name in immutable_fields):
        raise RuntimeError("A identidade da reserva de recuperação é imutável.")


@event.listens_for(MediaArchiveRecoveryCreditReservation, "before_delete")
def _protect_media_archive_recovery_reservation_delete(_mapper, _connection, _target):
    raise RuntimeError("Reservas de recuperação são históricas e não podem ser removidas.")


class ClientChallengeInput(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=200)
    phone: str = Field(min_length=8, max_length=32)


class ChallengeVerification(BaseModel):
    challenge_id: UUID
    code: str = Field(pattern=r"^\d{6}$")
    access_token: str | None = Field(default=None, min_length=32, max_length=256)
    parent_gallery_id: UUID | None = None


class AdminTotpVerification(BaseModel):
    challenge_id: UUID
    code: str = Field(min_length=6, max_length=64)

    @field_validator("code")
    @classmethod
    def code_is_totp_or_recovery(cls, value: str) -> str:
        if re.fullmatch(r"\d{6}|[A-Za-z0-9_-]{24}", value) is None:
            raise ValueError("Código inválido.")
        return value


class AdminTotpRecoveryCodesInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    second_factor_code: str = Field(min_length=6, max_length=64)

    @field_validator("second_factor_code")
    @classmethod
    def code_is_totp_or_recovery(cls, value: str) -> str:
        if re.fullmatch(r"\d{6}|[A-Za-z0-9_-]{24}", value) is None:
            raise ValueError("Código inválido.")
        return value


class ChallengeResendInput(BaseModel):
    challenge_id: UUID
    access_token: str | None = Field(default=None, min_length=32, max_length=256)
    parent_gallery_id: UUID | None = None


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


def audit(db: Session, event: str, subject: str, *, tenant_id: UUID | None = None) -> None:
    db.add(AuditEvent(tenant_id=tenant_id, event=event, subject=subject))


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
    db: Session, kind: str, subject: str, code: str | None = None,
    *, tenant_id: UUID | None = None, parent_gallery_id: UUID | None = None,
    gallery_capability_id: UUID | None = None, client_name: str | None = None,
    return_to: str | None = None,
) -> tuple[AuthChallenge, str]:
    if kind == "client_otp":
        require_client_auth_tenant(db, tenant_id)
        require_client_channel(db, tenant_id)
    code = code or f"{secrets.randbelow(1_000_000):06d}"
    challenge = AuthChallenge(
        tenant_id=tenant_id,
        kind=kind,
        subject=subject,
        subject_fingerprint=pii_fingerprint(subject) if kind == "client_otp" else None,
        secret_hash=token_hash(code),
        expires_at=now() + timedelta(minutes=10),
        parent_gallery_id=parent_gallery_id,
        gallery_capability_id=gallery_capability_id,
        client_name=client_name,
        return_to=return_to,
    )
    db.add(challenge)
    audit(
        db,
        f"{kind}.requested",
        challenge.subject_fingerprint if kind == "client_otp" else subject,
        tenant_id=tenant_id,
    )
    db.commit()
    return challenge, code


def enqueue_client_otp_delivery(
    db: Session, challenge: AuthChallenge, code: str
) -> WhatsAppDelivery:
    """Persiste uma entrega OTP sem depender da rede ou guardar o código aberto."""
    require_client_auth_tenant(db, challenge.tenant_id)
    binding = require_client_channel(db, challenge.tenant_id)
    key = f"otp:{challenge.id}:{challenge.resend_count}"
    existing = db.scalar(select(WhatsAppDelivery).where(
        WhatsAppDelivery.tenant_id == challenge.tenant_id,
        WhatsAppDelivery.idempotency_key == key,
    ))
    if existing:
        return existing
    delivery = WhatsAppDelivery(
        tenant_id=challenge.tenant_id,
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
        if binding.name == "sandbox":
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
    audit(db, "client_otp.delivery_queued", str(challenge.id), tenant_id=challenge.tenant_id)
    db.commit()
    return delivery


def require_client_channel(db: Session, tenant_id: UUID):
    from app.whatsapp_binding import resolve_binding
    try:
        return resolve_binding(db, tenant_id)
    except WhatsAppConfigurationError:
        raise HTTPException(status_code=503, detail="Autenticação temporariamente indisponível.") from None


def require_client_auth_tenant(db: Session, tenant_id: UUID | None) -> Tenant:
    tenant = db.get(Tenant, tenant_id, populate_existing=True) if tenant_id else None
    if tenant is None or tenant.status != "active" or tenant.lifecycle == "closed":
        raise neutral_error()
    from app.tenancy import bind_domain_owner

    bind_domain_owner(db, tenant.id)
    return tenant


def client_auth_rate_limit(
    db: Session, scope: str, fingerprint: str, ip_address: str, *, tenant_id: UUID,
) -> None:
    require_client_auth_tenant(db, tenant_id)
    enforce_rate_limit(db, scope, fingerprint, ip_address)
    enforce_rate_limit(db, f"{scope}.context", f"{tenant_id}:{fingerprint}", ip_address)


def resend_client_challenge(
    db: Session, challenge_id: UUID, ip_address: str, *, tenant_id: UUID,
    deliver: bool = True,
) -> AuthChallenge:
    require_client_auth_tenant(db, tenant_id)
    require_client_channel(db, tenant_id)
    challenge = db.scalar(select(AuthChallenge).where(
        AuthChallenge.id == challenge_id, AuthChallenge.tenant_id == tenant_id,
    ).with_for_update())
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
    client_auth_rate_limit(db, "client_otp.resend", fingerprint, ip_address, tenant_id=tenant_id)
    code = f"{secrets.randbelow(1_000_000):06d}" if deliver else secrets.token_urlsafe(32)
    for delivery in db.scalars(
        select(WhatsAppDelivery).where(
            WhatsAppDelivery.tenant_id == challenge.tenant_id,
            WhatsAppDelivery.kind == "otp",
            WhatsAppDelivery.source_type == "auth_challenge",
            WhatsAppDelivery.source_id == str(challenge.id),
            WhatsAppDelivery.status.in_(("queued", "processing", "unknown")),
        )
    ):
        delivery.status = "expired"
        delivery.encrypted_payload = None
        delivery.updated_at = now()
    challenge.secret_hash = token_hash(code)
    challenge.resend_count += 1
    audit(db, "client_otp.resent" if deliver else "client_otp.resend_suppressed",
          fingerprint, tenant_id=tenant_id)
    db.commit()
    if deliver:
        enqueue_client_otp_delivery(db, challenge, code)
    return challenge


def consume_challenge(
    db: Session, challenge_id: UUID, kind: str, code: str, *, tenant_id: UUID | None = None,
) -> AuthChallenge:
    query = select(AuthChallenge).where(AuthChallenge.id == challenge_id)
    if kind == "client_otp":
        require_client_auth_tenant(db, tenant_id)
        query = query.where(AuthChallenge.tenant_id == tenant_id)
    challenge = db.scalar(query.with_for_update())
    if (
        not challenge
        or challenge.kind != kind
        or challenge.used_at
        or expired(challenge.expires_at)
        or challenge.attempts >= 5
    ):
        audit(db, f"{kind}.rejected", str(challenge_id), tenant_id=tenant_id)
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
            tenant_id=challenge.tenant_id,
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
        tenant_id=challenge.tenant_id,
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
            WhatsAppDelivery.tenant_id == challenge.tenant_id,
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


def cleanup_expired_client_otp_pii(db: Session, *, tenant_id: UUID, current_time: datetime | None = None) -> int:
    """Minimiza desafios abandonados após a janela curta configurada."""

    from app.acervo_context import require_active_owner
    require_active_owner(db, tenant_id)
    instant = current_time or now()
    retention = timedelta(minutes=max(0, int(os.getenv("AUTH_OTP_PII_RETENTION_MINUTES", "60"))))
    cutoff = instant - retention
    challenges = list(
        db.scalars(
            select(AuthChallenge).where(
                AuthChallenge.tenant_id == tenant_id,
                AuthChallenge.kind == "client_otp",
                AuthChallenge.subject.is_not(None),
                AuthChallenge.expires_at <= cutoff,
            )
        )
    )
    for challenge in challenges:
        require_active_owner(db, tenant_id)
        minimize_client_challenge_pii(db, challenge)
    if challenges:
        audit(db, "client_otp.pii_cleanup", f"count:{len(challenges)}", tenant_id=tenant_id)
        db.commit()
    return len(challenges)


def create_session(
    db: Session, response: Response, role: Role, subject_id: UUID,
    *, tenant_id: UUID | None = None, platform_scope: bool = False,
) -> str:
    from app.tenancy import TenantContextError, require_admin_tenant

    try:
        if role == Role.ADMIN:
            tenant = require_admin_tenant(db, subject_id, platform_scope=platform_scope)
            admin = db.get(AdminUser, subject_id, populate_existing=True)
            if not admin or not admin.email_verified:
                raise TenantContextError("Acesso negado.")
            if tenant_id is not None and tenant.id != tenant_id:
                raise TenantContextError("Acesso negado.")
            tenant_id = tenant.id
        elif role == Role.CLIENT:
            require_client_auth_tenant(db, tenant_id)
            if not db.scalar(select(Client.id).where(Client.id == subject_id, Client.tenant_id == tenant_id)):
                raise neutral_error()
        else:
            raise neutral_error()
    except TenantContextError as exc:
        raise HTTPException(status_code=403, detail="Acesso negado.") from exc
    raw_token = secrets.token_urlsafe(48)
    active_sessions = db.scalars(
        select(AuthSession).where(
            AuthSession.role == role.value,
            AuthSession.tenant_id == tenant_id,
            AuthSession.subject_id == subject_id,
            AuthSession.revoked_at.is_(None),
        )
    )
    for active_session in active_sessions:
        active_session.revoked_at = now()
        audit(db, "session.rotated", str(subject_id), tenant_id=tenant_id)
    session = AuthSession(
        tenant_id=tenant_id,
        token_hash=token_hash(raw_token),
        role=role.value,
        subject_id=subject_id,
        client_subject_id=subject_id if role == Role.CLIENT else None,
        admin_subject_id=subject_id if role == Role.ADMIN else None,
        expires_at=now() + timedelta(days=int(os.getenv("SESSION_DAYS", "7"))),
    )
    db.add(session)
    audit(db, "session.created", str(subject_id), tenant_id=tenant_id)
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


def current_session(
    request: Request, required_role: Role | None = None, *, invalid_session_status: int = 403,
    platform_scope: bool = False,
) -> AuthSession:
    from app.tenancy import TenantContextError, require_admin_tenant

    token = request.cookies.get(os.getenv("SESSION_COOKIE_NAME", "markina_session"))
    if not token:
        raise HTTPException(status_code=invalid_session_status, detail="Acesso negado.")
    with SessionLocal() as db:
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        if (
            not session
            or session.revoked_at
            or expired(session.expires_at)
        ):
            raise HTTPException(status_code=invalid_session_status, detail="Acesso negado.")
        if required_role and session.role != required_role.value:
            raise HTTPException(status_code=403, detail="Acesso negado.")
        try:
            if session.role == Role.ADMIN.value:
                tenant = require_admin_tenant(db, session.subject_id, platform_scope=platform_scope)
                admin = db.get(AdminUser, session.subject_id, populate_existing=True)
                if not admin or not admin.email_verified:
                    raise TenantContextError("Acesso negado.")
                if session.tenant_id != tenant.id or session.admin_subject_id != session.subject_id:
                    raise TenantContextError("Acesso negado.")
            elif session.role == Role.CLIENT.value:
                require_client_auth_tenant(db, session.tenant_id)
                tenant = db.get(Tenant, session.tenant_id, populate_existing=True)
                if tenant:
                    from app.tenant_hosts import (
                        CanonicalHostError,
                        canonical_host_for_tenant,
                        request_hostname,
                    )
                    try:
                        canonical_host = canonical_host_for_tenant(db, tenant)
                        if canonical_host and request_hostname(request.headers.get("host")) != canonical_host:
                            raise TenantContextError("Acesso negado.")
                    except CanonicalHostError as exc:
                        raise TenantContextError("Acesso negado.") from exc
                if session.client_subject_id != session.subject_id or not db.scalar(select(Client.id).where(
                    Client.id == session.subject_id, Client.tenant_id == session.tenant_id,
                )):
                    raise TenantContextError("Acesso negado.")
            else:
                raise TenantContextError("Acesso negado.")
        except (TenantContextError, HTTPException) as exc:
            raise HTTPException(status_code=403, detail="Acesso negado.") from exc
        db.expunge(session)
        return session


def revoke_subject_sessions(db: Session, role: str, subject_id: UUID) -> None:
    for subscription in db.scalars(select(PushSubscription).where(
        PushSubscription.role == role, PushSubscription.subject_id == subject_id,
        PushSubscription.active,
    )):
        subscription.active = False
        subscription.generation += 1
        subscription.updated_at = now()
    for session in db.scalars(
        select(AuthSession).where(
            AuthSession.role == role,
            AuthSession.subject_id == subject_id,
            AuthSession.revoked_at.is_(None),
        )
    ):
        session.revoked_at = now()
    audit(db, "session.revoke_all", str(subject_id))


class GlobalPostgreSQLBackupRun(Base):
    """Recibo sanitizado de uma tentativa diária de backup PostgreSQL global."""

    __tablename__ = "global_postgresql_backup_run"
    __table_args__ = (
        UniqueConstraint("scheduled_day", name="uq_global_postgresql_backup_run_day"),
        CheckConstraint(
            "status IN ('running', 'validated', 'failed', 'unknown')",
            name="ck_global_postgresql_backup_run_status",
        ),
        CheckConstraint(
            "retention_status IN ('unknown', 'pending', 'complete', 'failed')",
            name="ck_global_postgresql_backup_run_retention_status",
        ),
        CheckConstraint(
            "dump_size_bytes IS NULL OR dump_size_bytes >= 0",
            name="ck_global_postgresql_backup_run_dump_size",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_global_postgresql_backup_run_duration",
        ),
        CheckConstraint(
            "status != 'validated' OR "
            "(verified = true AND snapshot_id IS NOT NULL AND finished_at IS NOT NULL)",
            name="ck_global_postgresql_backup_run_verified",
        ),
        CheckConstraint(
            "verified = false OR status = 'validated'",
            name="ck_global_postgresql_backup_run_no_unverified_success",
        ),
        Index("ix_global_postgresql_backup_run_status_day", "status", "scheduled_day"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    scheduled_day: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dump_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retention_status: Mapped[str] = mapped_column(
        String(12), nullable=False, default="unknown", server_default="unknown"
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
