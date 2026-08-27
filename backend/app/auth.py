"""Autenticação e autorização da Markina Gallery.

O módulo mantém autorização no servidor; o browser recebe apenas um cookie opaco.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from fastapi import HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


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


class AdminUser(Base):
    __tablename__ = "admin_user"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_secret: Mapped[str] = mapped_column(String(128))


class Client(Base):
    __tablename__ = "client"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String(200))
    phone_e164: Mapped[str] = mapped_column(String(16), unique=True, index=True)


class ClientPhone(Base):
    __tablename__ = "client_phone"
    __table_args__ = (UniqueConstraint("phone_e164", "active"),)
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
    """Acervo-mãe privado, administrado exclusivamente pelo fotógrafo."""

    __tablename__ = "parent_gallery"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    event_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
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
    """Arquivo pertencente ao acervo-mãe; nunca é duplicado para o cliente."""

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
    """Galeria privada pertencente a uma única cliente/responsável."""

    __tablename__ = "derived_gallery"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("parent_gallery.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    custom_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    selection_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    favorites_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    comments_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DerivedGalleryPhoto(Base):
    """Referência de uma foto do acervo-mãe atribuída à galeria derivada."""

    __tablename__ = "derived_gallery_photo"
    __table_args__ = (UniqueConstraint("derived_gallery_id", "photo_asset_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("derived_gallery.id"), index=True)
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoSelection(Base):
    __tablename__ = "photo_selection"
    __table_args__ = (UniqueConstraint("derived_gallery_id", "photo_asset_id", "client_id"),)

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
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    derived_gallery_id: Mapped[UUID] = mapped_column(ForeignKey("derived_gallery.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    payment_status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    total_cents: Mapped[int] = mapped_column(Integer)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_name_snapshot: Mapped[str | None] = mapped_column(String(200), nullable=True)
    client_phone_snapshot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SaleOrderItem(Base):
    __tablename__ = "sale_order_item"
    __table_args__ = (UniqueConstraint("sale_order_id", "photo_asset_id"), CheckConstraint("unit_price_cents >= 0"))

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sale_order_id: Mapped[UUID] = mapped_column(ForeignKey("sale_order.id"), index=True)
    photo_asset_id: Mapped[UUID] = mapped_column(ForeignKey("photo_asset.id"), index=True)
    filename_snapshot: Mapped[str] = mapped_column(String(512))
    unit_price_cents: Mapped[int] = mapped_column(Integer)


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
    subject: Mapped[str] = mapped_column(String(320), index=True)
    secret_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    resend_count: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_gallery_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)


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


class WhatsAppProvider(ABC):
    """Porta de envio; provedores reais permanecem fora desta mudança."""

    @abstractmethod
    def send_otp(self, phone_e164: str, code: str) -> None: ...


class SandboxWhatsAppProvider(WhatsAppProvider):
    """Adaptador sem efeitos externos e sem registrar o código em logs."""

    def send_otp(self, phone_e164: str, code: str) -> None:
        del phone_e164, code


whatsapp_provider: WhatsAppProvider = SandboxWhatsAppProvider()


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
        secret_hash=token_hash(code),
        expires_at=now() + timedelta(minutes=10),
    )
    db.add(challenge)
    audit(db, f"{kind}.requested", subject)
    db.commit()
    return challenge, code


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
    enforce_rate_limit(db, "client_otp.resend", challenge.subject, ip_address)
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge.secret_hash = token_hash(code)
    challenge.resend_count += 1
    audit(db, "client_otp.resent", challenge.subject)
    whatsapp_provider.send_otp(challenge.subject, code)
    db.commit()
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
        audit(db, f"{kind}.failed", challenge.subject)
        db.commit()
        raise neutral_error()
    challenge.used_at = now()
    audit(db, f"{kind}.validated", challenge.subject)
    return challenge


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
