"""Cadastro automatizado; prova isolada local, publicação pública permanece fechada."""

import hmac
import os
import secrets
from datetime import timedelta
from typing import Annotated, Protocol
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.admin_account import AdminAccountError, issue_password_reset_link, normalize_admin_email
from app.admin_security import AdminSecurityConfigurationError
from app.auth import (
    AdminUser,
    AuditEvent,
    EmailDelivery,
    PhotographerSignup,
    Role,
    SessionLocal,
    Tenant,
    TenantAdmin,
    TenantCreditWallet,
    audit,
    create_session,
    enforce_rate_limit,
    expired,
    now,
    password_hasher,
    pii_fingerprint,
    token_hash,
    validate_admin_password,
)
from app.email_delivery import (
    EmailConfigurationError,
    email_channel_payload,
    enqueue_email,
)
from app.mercadopago_api import SensitiveRoute
from app.photographer_turnstile import (
    TurnstileSettings,
    TurnstileUnavailable,
    TurnstileVerifier,
)
from app.photographer_turnstile import (
    settings_from_environment as turnstile_settings_from_environment,
)
from app.system_monitor.store import bounded
from app.totp_crypto import TotpSecretError

HEADERS = {"Cache-Control": "private, no-store"}
SETUP_COOKIE = "pyp_signup_setup"


def local_proof_gate():
    # Não é um interruptor de produção: a prova sintética foi autorizada só localmente.
    if os.getenv("APP_ENV", "development") not in {"development", "test"} or os.getenv("PHOTOGRAPHER_SIGNUP_LOCAL_PROOF_ENABLED") != "true":
        raise HTTPException(404, "Recurso indisponível.", headers=HEADERS)


class SignupServices(Protocol):
    def verify_bot(self, proof: str, address: str) -> bool: ...
    def send_code(self, db: Session, signup: PhotographerSignup, code: str) -> None: ...


class SignupServiceError(RuntimeError):
    """Adapters externos devem normalizar falhas sem dados privados."""


class TurnstileSignupServices:
    def __init__(self, settings: TurnstileSettings) -> None:
        self._verifier = TurnstileVerifier(settings)

    def verify_bot(self, proof: str, _address: str) -> bool:
        try:
            return self._verifier.verify(proof)
        except TurnstileUnavailable:
            raise SignupServiceError("Validação anti-bot indisponível.") from None

    def send_code(self, db: Session, signup: PhotographerSignup, code: str) -> None:
        if not signup.otp_expires_at or not signup.public_request_id:
            raise SignupServiceError("Candidatura indisponível para envio.")
        try:
            enqueue_email(
                db,
                kind="email_verification",
                source_type="photographer_signup",
                source_id=str(signup.id),
                recipient=signup.email,
                subject="Confirme seu e-mail · Pick-your-Pic",
                text_body=(
                    f"Seu código para criar a conta de fotógrafo é {code}. "
                    "Ele expira em 10 minutos e só pode ser usado uma vez. "
                    "Se você não iniciou o cadastro, ignore esta mensagem."
                ),
                idempotency_key=(
                    f"email:photographer-signup:{signup.id}:{signup.public_request_id}"
                ),
                expires_at=signup.otp_expires_at,
            )
        except (AdminSecurityConfigurationError, EmailConfigurationError, OSError, ValueError):
            raise SignupServiceError("Entrega de e-mail indisponível.") from None


def signup_services() -> SignupServices:
    try:
        settings = turnstile_settings_from_environment()
    except (RuntimeError, ValueError):
        raise HTTPException(503, "Cadastro temporariamente indisponível.", headers=HEADERS) from None
    if (
        settings is None
        or os.getenv("PHOTOGRAPHER_SIGNUP_EMAIL_DELIVERY_ENABLED", "false").strip().lower() != "true"
        or email_channel_payload()["status"] != "ready"
    ):
        raise HTTPException(503, "Cadastro temporariamente indisponível.", headers=HEADERS)
    return TurnstileSignupServices(settings)


def database():
    with SessionLocal() as db:
        try:
            bounded(db)
            yield db
        except (SQLAlchemyError, TotpSecretError):
            db.rollback()
            raise HTTPException(503, "Cadastro temporariamente indisponível.", headers=HEADERS) from None


router = APIRouter(prefix="/auth/photographer-signup", route_class=SensitiveRoute,
                   dependencies=[Depends(local_proof_gate)])
Database = Annotated[Session, Depends(database)]
Services = Annotated[SignupServices, Depends(signup_services)]


class StartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    photographer_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    adult_attested: StrictBool
    anti_bot_proof: SecretStr


class EmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    code: SecretStr


class CompleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr


class RecoveryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)


@router.get("/config")
def signup_public_config(response: Response):
    response.headers.update(HEADERS)
    try:
        settings = turnstile_settings_from_environment()
    except (RuntimeError, ValueError):
        raise HTTPException(503, "Cadastro temporariamente indisponível.", headers=HEADERS) from None
    enabled = bool(
        settings
        and os.getenv("PHOTOGRAPHER_SIGNUP_EMAIL_DELIVERY_ENABLED", "false").strip().lower() == "true"
        and email_channel_payload()["status"] == "ready"
    )
    return {
        "turnstile_enabled": enabled,
        "turnstile_site_key": settings.site_key if enabled and settings else None,
    }


def _error():
    return HTTPException(400, "Não foi possível concluir esta etapa. Confira os dados ou reinicie o cadastro.", headers=HEADERS)


def _ip(request):
    return request.client.host if request.client else "unknown"


def _origin(request):
    from app.main import require_same_origin
    require_same_origin(request)


def _otp_digest(signup_id, code):
    return pii_fingerprint(f"photographer-signup:{signup_id}:{code}")


def _lock_signup_identities(db):
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        schema = db.connection().get_execution_options().get("schema_translate_map", {}).get(None)
        quote = db.connection().dialect.identifier_preparer
        prefix = quote.quote_schema(schema) + "." if schema else ""
        db.execute(text("LOCK TABLE " + ", ".join(prefix + quote.quote(name) for name in ("admin_user", "photographer_signup")) + " IN SHARE ROW EXCLUSIVE MODE"))


@router.post("/recovery/email-link", status_code=202)
def request_email_recovery(payload: RecoveryInput, request: Request, db: Database):
    _origin(request)
    try:
        email = normalize_admin_email(payload.email)
    except AdminAccountError:
        email = payload.email.strip().casefold()
    enforce_rate_limit(db, "signup_recovery_email", pii_fingerprint(email), _ip(request))
    db.commit()
    admin = db.scalar(select(AdminUser).where(AdminUser.email == email, AdminUser.email_verified))
    signup = db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.reserved_admin_id == admin.id,
        PhotographerSignup.state == "active",
    )) if admin else None
    eligible = bool(signup and signup.activated_tenant_id and db.scalar(select(Tenant.id).join(
        TenantAdmin, TenantAdmin.tenant_id == Tenant.id,
    ).where(Tenant.id == signup.activated_tenant_id, Tenant.status == "active",
            TenantAdmin.admin_user_id == admin.id, TenantAdmin.active.is_(True))))
    if eligible and email_channel_payload()["status"] in {"ready", "sandbox"}:
        try:
            issue_password_reset_link(db, admin)
        except (AdminAccountError, AdminSecurityConfigurationError, EmailConfigurationError, OSError, ValueError):
            db.rollback()
    return {"message": "Se a conta estiver apta, enviaremos um link de uso único ao e-mail informado."}


@router.post("", status_code=202)
def start(payload: StartInput, request: Request, response: Response, db: Database, services: Services):
    _origin(request)
    response.headers.update(HEADERS)
    if not payload.adult_attested:
        raise _error()
    try:
        email = normalize_admin_email(payload.email)
    except AdminAccountError:
        raise _error() from None
    name = " ".join(payload.photographer_name.split())
    if not name or any(ord(char) < 32 for char in name):
        raise _error()
    try:
        verified_bot = services.verify_bot(payload.anti_bot_proof.get_secret_value(), _ip(request))
    except (SignupServiceError, OSError):
        raise HTTPException(503, "Cadastro temporariamente indisponível.", headers=HEADERS) from None
    if not verified_bot:
        raise _error()
    enforce_rate_limit(db, "signup_start", "public", _ip(request))
    enforce_rate_limit(db, "signup_email", pii_fingerprint(email), _ip(request))
    # Locks de tabela evitam corrida entre criação pública e provisionamento CLI.
    # Guard exclusivo de DB local; não consulta nem altera contas operacionais.
    _lock_signup_identities(db)
    existing = db.scalar(select(AdminUser.id).where(func.lower(AdminUser.email) == email))
    row = db.scalar(select(PhotographerSignup).where(PhotographerSignup.email == email).with_for_update())
    identity = uuid4()
    if not existing and (row is None or row.state != "active"):
        if row is None:
            row = PhotographerSignup(id=identity, photographer_name=name, email=email,
                                     otp_expires_at=now() + timedelta(minutes=10))
            db.add(row)
        row.photographer_name, row.state, row.attempts = name, "email_pending", 0
        row.adult_attested_at = now()
        row.public_request_id = identity
        row.setup_digest, row.setup_expires_at, row.totp_envelope = None, None, None
        code = f"{secrets.randbelow(1_000_000):06d}"
        row.otp_digest, row.otp_expires_at = _otp_digest(row.id, code), now() + timedelta(minutes=10)
        db.flush()
        try:
            services.send_code(db, row, code)
        except (SignupServiceError, OSError):
            db.rollback()
            raise HTTPException(503, "Cadastro temporariamente indisponível.", headers=HEADERS) from None
        audit(db, "photographer_signup.email_requested", str(row.id))
    db.commit()
    return {"request_id": str(identity), "message": "Se o cadastro puder prosseguir, enviaremos um código ao e-mail informado."}


@router.post("/verify-email")
def verify_email(payload: EmailInput, request: Request, response: Response, db: Database):
    _origin(request)
    response.headers.update(HEADERS)
    enforce_rate_limit(db, "signup_verify", "public", _ip(request))
    row = db.scalar(select(PhotographerSignup).where(PhotographerSignup.public_request_id == payload.request_id).with_for_update())
    code = payload.code.get_secret_value()
    valid = row and row.state == "email_pending" and row.attempts < 5 and not expired(row.otp_expires_at)
    valid = valid and len(code) == 6 and code.isdigit() and hmac.compare_digest(row.otp_digest or "", _otp_digest(row.id, code))
    if not valid:
        if row and row.state == "email_pending":
            row.attempts = min(5, row.attempts + 1)
            if expired(row.otp_expires_at):
                row.state, row.otp_digest = "expired", None
        db.commit()
        raise _error()
    token = secrets.token_urlsafe(32)
    row.state, row.otp_digest = "credentials_pending", None
    row.setup_digest, row.setup_expires_at = token_hash(token), now() + timedelta(minutes=15)
    row.totp_envelope = None
    audit(db, "photographer_signup.email_verified", str(row.id))
    db.commit()
    response.set_cookie(SETUP_COOKIE, token, httponly=True, secure=request.url.scheme == "https",
                        samesite="strict", max_age=900, path="/api/auth/photographer-signup")
    return {"state": "credentials_pending"}


def _setup(db, request):
    token = request.cookies.get(SETUP_COOKIE, "")
    if not token or len(token) > 100:
        raise _error()
    row = db.scalar(select(PhotographerSignup).where(PhotographerSignup.setup_digest == token_hash(token)).with_for_update())
    if row and row.state == "credentials_pending" and row.setup_expires_at and expired(row.setup_expires_at):
        row.state, row.totp_envelope, row.setup_digest = "expired", None, None
        db.commit()
        raise _error()
    if not row or row.state != "credentials_pending" or not row.setup_expires_at:
        raise _error()
    return row


@router.get("/setup")
def setup(request: Request, response: Response, db: Database):
    response.headers.update(HEADERS)
    row = _setup(db, request)
    return {"photographer_name": row.photographer_name, "email": row.email}


@router.post("/complete")
def complete(payload: CompleteInput, request: Request, response: Response, db: Database):
    _origin(request)
    response.headers.update(HEADERS)
    enforce_rate_limit(db, "signup_complete", "public", _ip(request))
    _lock_signup_identities(db)
    row = _setup(db, request)
    password = payload.password.get_secret_value()
    try:
        validate_admin_password(password, email=row.email)
    except (ValueError, TypeError):
        db.commit()
        raise _error() from None
    if db.scalar(select(AdminUser.id).where(func.lower(AdminUser.email) == row.email)):
        db.commit()
        raise _error()
    try:
        tenant = Tenant(id=row.reserved_tenant_id, photographer_name=row.photographer_name)
        db.add(tenant)
        db.flush()
        admin = AdminUser(id=row.reserved_admin_id, email=row.email, email_verified=True,
                          password_hash=password_hasher.hash(password), totp_enabled=False)
        admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
        db.add_all([admin, TenantCreditWallet(tenant_id=tenant.id, mode="finite")])
        db.flush()
        row.state, row.activated_at, row.activated_tenant_id = "active", now(), tenant.id
        row.totp_envelope, row.setup_digest = None, None
        create_session(db, response, Role.ADMIN, admin.id, tenant_id=tenant.id)
        audit(db, "photographer_signup.activated", str(row.id), tenant_id=tenant.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _error() from None
    response.delete_cookie(SETUP_COOKIE, path="/api/auth/photographer-signup")
    return {"state": "active", "redirect_to": "/admin"}


@router.post("/cancel")
def cancel(request: Request, response: Response, db: Database):
    _origin(request)
    row = _setup(db, request)
    row.state, row.totp_envelope, row.setup_digest, row.otp_digest = "cancelled", None, None, None
    audit(db, "photographer_signup.cancelled", str(row.id))
    db.commit()
    response.delete_cookie(SETUP_COOKIE, path="/api/auth/photographer-signup")
    return {"state": "cancelled"}


def expire_signup_material(db: Session) -> bool:
    """Expira fatores e elimina candidaturas não verificadas após 30 dias."""
    instant = now()
    rows = list(db.scalars(select(PhotographerSignup).where(or_(
        and_(PhotographerSignup.state == "email_pending", PhotographerSignup.otp_expires_at < instant),
        and_(PhotographerSignup.state == "credentials_pending", PhotographerSignup.setup_expires_at < instant),
    )).order_by(PhotographerSignup.created_at).with_for_update(skip_locked=True).limit(100)))
    for row in rows:
        row.state, row.otp_digest, row.setup_digest, row.totp_envelope = "expired", None, None, None
    if rows:
        audit(db, "photographer_signup.material_expired", f"count:{len(rows)}")

    retention_before = instant - timedelta(days=30)
    candidates = list(db.scalars(select(PhotographerSignup).where(
        PhotographerSignup.state.in_(("email_pending", "expired", "cancelled")),
        PhotographerSignup.created_at <= retention_before,
    ).order_by(PhotographerSignup.created_at).with_for_update(skip_locked=True).limit(100)))
    erased = 0
    for candidate in candidates:
        verified = db.scalar(select(AuditEvent.id).where(
            AuditEvent.event == "photographer_signup.email_verified",
            AuditEvent.subject == str(candidate.id),
        ).limit(1))
        if verified:
            continue
        deliveries = db.scalars(select(EmailDelivery).where(
            EmailDelivery.source_type == "photographer_signup",
            EmailDelivery.source_id == str(candidate.id),
        ).with_for_update())
        for delivery in deliveries:
            delivery.encrypted_payload = None
            delivery.recipient_fingerprint = "0" * 64
            if delivery.status in {"queued", "processing"}:
                delivery.status = "expired"
        db.delete(candidate)
        erased += 1
    if erased:
        audit(db, "photographer_signup.pii_expired", f"count:{erased}")
    return bool(rows or erased)


def process_signup_expiry(*, session_factory=None) -> bool:
    local_proof = (os.getenv("APP_ENV", "development") in {"development", "test"}
                   and os.getenv("PHOTOGRAPHER_SIGNUP_LOCAL_PROOF_ENABLED") == "true")
    retention_enabled = os.getenv("PHOTOGRAPHER_SIGNUP_RETENTION_ENABLED", "false").strip().lower() == "true"
    if not local_proof and not retention_enabled:
        return False
    with (session_factory or SessionLocal)() as db:
        bounded(db)
        changed = expire_signup_material(db)
        db.commit()
        return changed
