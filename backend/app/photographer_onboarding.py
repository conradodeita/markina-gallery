"""Perfil progressivo e gates operacionais do fotógrafo autenticado."""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    PhotoAsset,
    PhotoCreditOperation,
    PhotographerBusinessProfile,
    PhotographerSignup,
    PhotographerTermsAcceptance,
    Role,
    SessionLocal,
    Tenant,
    TenantAdmin,
    TenantCreditWallet,
    audit,
    current_session,
    now,
)
from app.global_pix import global_pix_settings
from app.mercadopago_api import PayerAddressInput, SensitiveRoute
from app.messaging import WhatsAppConfigurationError
from app.photographer_cpf import (
    PhotographerCpfFingerprintError,
    active_cpf_fingerprint,
    cpf_matches_tenant,
    normalize_cpf,
)
from app.photographer_subdomain import AddressInput, address_status, reserve_address
from app.photographer_terms import latest_published, render_terms
from app.private_fields import (
    PrivateFieldError,
    decrypt_private_document,
    decrypt_private_field,
    encrypt_private_document,
    encrypt_private_field,
)
from app.whatsapp_channel import channel_settings


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cpf: SecretStr
    address: PayerAddressInput

    @field_validator("cpf")
    @classmethod
    def validate_cpf_shape(cls, value: SecretStr) -> SecretStr:
        if not re.fullmatch(r"[0-9.\-/ ]{11,20}", value.get_secret_value()):
            raise ValueError("Informe um CPF válido.")
        return value


class TestTermsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: bool


class TermsAcceptanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=80)
    accepted: Literal[True]


def database():
    with SessionLocal() as db:
        yield db


Database = Annotated[Session, Depends(database)]
router = APIRouter(prefix="/admin/onboarding", route_class=SensitiveRoute)


def _context(request: Request, db: Session):
    session = current_session(request, Role.ADMIN)
    admin = db.get(AdminUser, session.subject_id)
    membership = db.scalar(select(TenantAdmin).where(
        TenantAdmin.admin_user_id == session.subject_id,
        TenantAdmin.tenant_id == session.tenant_id,
        TenantAdmin.active.is_(True),
    ))
    signup = db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.reserved_admin_id == session.subject_id,
        PhotographerSignup.activated_tenant_id == session.tenant_id,
        PhotographerSignup.state == "active",
    ))
    if not admin or not admin.email_verified or not membership or not signup:
        raise HTTPException(403, "Acesso negado.")
    return session, admin, signup


def _valid_cpf(value: str) -> str:
    try:
        return normalize_cpf(value)
    except PhotographerCpfFingerprintError:
        raise HTTPException(422, "Informe um CPF válido.") from None


def _terms_version(db: Session | None = None):
    published = latest_published(db) if db is not None else None
    if published:
        identity = f"{published.provider_legal_name}; {published.provider_contact_email}"
        return (published.terms_version, published.template_text, identity, False,
                published.provider_legal_name, published.provider_contact_email)
    if os.getenv("APP_ENV", "development") in {"development", "test"}:
        if os.getenv("PHOTOGRAPHER_TEST_TERMS_ENABLED") != "true":
            return None
        return (
            "local-test-v1",
            "Termos de teste local do Pick-your-Pic. Documento sintético sem validade para contratação ou uso em produção.",
            "Provedor Pick-your-Pic (identidade sintética de teste)", True, "", "",
        )
    return None  # Termos reais dependem de aprovação e identidade do provedor.


def onboarding_status(db: Session, *, admin: AdminUser, tenant_id: UUID, signup: PhotographerSignup) -> dict:
    profile = db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.admin_user_id == admin.id,
        PhotographerBusinessProfile.tenant_id == tenant_id,
    ))
    terms = _terms_version(db)
    acceptance = db.scalar(select(PhotographerTermsAcceptance).where(
        PhotographerTermsAcceptance.admin_user_id == admin.id,
        PhotographerTermsAcceptance.tenant_id == tenant_id,
        PhotographerTermsAcceptance.terms_version == (terms[0] if terms else "__unavailable__"),
    )) if terms else None
    pix = global_pix_settings(db, tenant_id=tenant_id)
    wallet = db.get(TenantCreditWallet, tenant_id)
    credit_snapshot = None
    if wallet:
        from app.photographer_credits import wallet_snapshot
        credit_snapshot = wallet_snapshot(db, tenant_id)
    credits_available = bool(credit_snapshot and credit_snapshot.get("available_credits") is not None
                             and credit_snapshot["available_credits"] > 0)
    try:
        whatsapp = channel_settings(db, tenant_id=tenant_id)
        whatsapp_ready = whatsapp.status == "ready" or (
            whatsapp.status == "sandbox" and os.getenv("APP_ENV", "development") in {"development", "test"}
        )
    except (WhatsAppConfigurationError, HTTPException):
        whatsapp_ready = False
    profile_complete = bool(profile and profile.cpf_envelope and profile.address_envelope)
    purchase_ready = bool(profile_complete and admin.email_verified)
    upload_ready = bool(purchase_ready and acceptance)
    return {
        "exploratory": True,
        "email_verified": bool(admin.email_verified),
        "profile_complete": profile_complete,
        "terms_accepted": bool(acceptance),
        "terms_available": terms is not None,
        "can_buy_credits": purchase_ready,
        "pix_configured": bool(pix and pix.status == "active"),
        "whatsapp_configured": whatsapp_ready,
        "credits_available": credits_available,
        "mercado_pago_optional": True,
        "can_upload": upload_ready and bool(pix and pix.status == "active") and whatsapp_ready and credits_available,
        "steps": [
            {"id": "profile", "required": True, "complete": profile_complete},
            {"id": "terms", "required": True, "complete": bool(acceptance), "available": terms is not None},
            {"id": "pix", "required": True, "complete": bool(pix and pix.status == "active")},
            {"id": "whatsapp", "required": True, "complete": whatsapp_ready},
            {"id": "credits", "required": True, "complete": credits_available},
            {"id": "mercado_pago", "required": False, "complete": False},
            {"id": "totp", "required": False, "complete": bool(admin.totp_enabled)},
        ],
    }


def _signup_identity(db: Session, tenant_id: UUID, admin_id: UUID):
    return db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.reserved_admin_id == admin_id,
        PhotographerSignup.activated_tenant_id == tenant_id,
        PhotographerSignup.state == "active",
    ))


def require_credit_purchase_ready(db: Session, *, tenant_id: UUID, admin_id: UUID) -> None:
    signup = _signup_identity(db, tenant_id, admin_id)
    if not signup:
        return  # contas legadas seguem seu contrato atual
    admin = db.get(AdminUser, admin_id)
    state = onboarding_status(db, admin=admin, tenant_id=tenant_id, signup=signup)
    if not state["can_buy_credits"]:
        raise HTTPException(409, detail={"code": "photographer_onboarding_required",
            "settings_url": "/admin/settings", "profile_complete": state["profile_complete"],
            "terms_accepted": state["terms_accepted"]})


def require_upload_ready(
    db: Session, *, tenant_id: UUID, admin_id: UUID, require_credit: bool = False,
    accepted_photo: PhotoAsset | None = None,
) -> None:
    from app.tenant_closure import require_new_work

    require_new_work(db, tenant_id)
    signup = _signup_identity(db, tenant_id, admin_id)
    if not signup:
        return
    if accepted_photo is not None and accepted_photo.tenant_id == tenant_id:
        from app.photographer_credits import fingerprint_from_storage_key

        fingerprint = fingerprint_from_storage_key(accepted_photo.storage_key)
        if fingerprint is not None:
            operation = db.scalar(select(PhotoCreditOperation).where(
                PhotoCreditOperation.tenant_id == tenant_id,
                PhotoCreditOperation.photo_asset_id_snapshot == accepted_photo.id,
                PhotoCreditOperation.storage_key_snapshot == accepted_photo.storage_key,
                PhotoCreditOperation.payload_fingerprint == fingerprint,
                PhotoCreditOperation.status.in_(
                    ("reserved", "reconciliation_required", "consumed")
                ),
            ))
            if operation is not None:
                # A reserva durável prova que este envio já passou pelo gate.
                # Mudanças posteriores de perfil/canal não podem interromper replay
                # nem reconciliação; identidades novas continuam gateadas abaixo.
                return
    admin = db.get(AdminUser, admin_id)
    state = onboarding_status(db, admin=admin, tenant_id=tenant_id, signup=signup)
    if (not state["email_verified"] or not state["profile_complete"] or not state["terms_accepted"]
            or not state["pix_configured"] or not state["whatsapp_configured"]
            or (require_credit and not state["credits_available"])):
        raise HTTPException(409, detail={"code": "photographer_onboarding_required",
            "settings_url": "/admin/settings", "profile_complete": state["profile_complete"],
            "terms_accepted": state["terms_accepted"], "pix_configured": state["pix_configured"],
            "whatsapp_configured": state["whatsapp_configured"],
            "credits_available": state["credits_available"]})


@router.get("")
def status(request: Request, db: Database):
    session, admin, signup = _context(request, db)
    return onboarding_status(db, admin=admin, tenant_id=session.tenant_id, signup=signup)


def _address_context(request: Request, db: Session):
    from app.system_monitor.models import PlatformOwner

    session, admin, _signup = _context(request, db)
    if db.scalar(select(PlatformOwner.admin_user_id).where(PlatformOwner.admin_user_id == admin.id)):
        raise HTTPException(403, "Acesso negado.")
    tenant = db.get(Tenant, session.tenant_id, populate_existing=True)
    if not tenant or tenant.status != "active":
        raise HTTPException(403, "Acesso negado.")
    return session, admin, tenant


@router.get("/address")
def photographer_address(request: Request, response: Response, db: Database):
    _session, _admin, tenant = _address_context(request, db)
    response.headers["Cache-Control"] = "private, no-store"
    return address_status(tenant, tenant.photographer_name or "")


@router.put("/address")
def reserve_photographer_address(payload: AddressInput, request: Request, response: Response, db: Database):
    from app.main import require_same_origin
    from app.tenancy import TenantContextError

    require_same_origin(request)
    session, admin, tenant = _address_context(request, db)
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return reserve_address(db, tenant_id=session.tenant_id, admin_id=admin.id,
                               prefix=payload.prefix, name=tenant.photographer_name or "")
    except TenantContextError:
        db.rollback()
        raise HTTPException(403, "Acesso negado.") from None


@router.get("/terms")
def terms(request: Request, db: Database):
    _session, _admin, _signup = _context(request, db)
    configured = _terms_version(db)
    if not configured:
        raise HTTPException(503, "Os termos operacionais ainda não estão disponíveis.")
    if configured[3]:
        return {"version": configured[0], "text": configured[1], "test_only": True}
    try:
        text = render_terms(configured[1], provider_legal_name=configured[4],
                            provider_contact_email=configured[5],
                            photographer_name=_signup.photographer_name, photographer_verified_email=_admin.email)
    except ValueError:
        raise HTTPException(503, "Os termos operacionais ainda não estão disponíveis.") from None
    return {"version": configured[0], "text": text, "test_only": False}


@router.get("/checkout-identity")
def checkout_identity(request: Request, db: Database):
    session, admin, _signup = _context(request, db)
    profile = db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.admin_user_id == admin.id,
        PhotographerBusinessProfile.tenant_id == session.tenant_id,
    ))
    if not profile or not profile.cpf_envelope or not profile.address_envelope:
        raise HTTPException(409, "Complete seu perfil antes da compra de créditos.")
    try:
        cpf = decrypt_private_field(profile.cpf_envelope, tenant_id=session.tenant_id,
                                    field="photographer-cpf")
        address = json.loads(decrypt_private_document(
            profile.address_envelope, tenant_id=session.tenant_id, field="photographer-address"))
    except PrivateFieldError:
        raise HTTPException(503, "Os dados do perfil estão temporariamente indisponíveis.") from None
    return {"name": profile.full_name, "email": admin.email, "identification_number": cpf,
            "address": address}


@router.put("/profile")
def save_profile(payload: ProfileInput, request: Request, db: Database):
    from app.main import require_same_origin
    require_same_origin(request)
    session, admin, signup = _context(request, db)
    full_name = " ".join(signup.photographer_name.split())
    if len(full_name) < 2 or any(ord(char) < 32 for char in full_name):
        raise HTTPException(422, "O nome do cadastro está indisponível.")
    cpf = _valid_cpf(payload.cpf.get_secret_value())
    row = db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.admin_user_id == admin.id,
        PhotographerBusinessProfile.tenant_id == session.tenant_id,
    ).with_for_update())
    try:
        if row and row.cpf_envelope is None and row.cpf_fingerprint and not cpf_matches_tenant(db, session.tenant_id, cpf):
            raise HTTPException(409, "Informe o CPF correspondente ao cadastro para completar o perfil.")
        fingerprint_version, fingerprint, duplicate = active_cpf_fingerprint(
            db, cpf, exclude_profile_id=row.id if row else None,
        )
    except PhotographerCpfFingerprintError:
        raise HTTPException(503, "A proteção dos dados do perfil está temporariamente indisponível.") from None
    if duplicate:
        raise HTTPException(409, "Não foi possível salvar este perfil. Confira os dados e tente novamente.")
    try:
        envelope = encrypt_private_field(cpf, tenant_id=session.tenant_id, field="photographer-cpf")
    except PrivateFieldError:
        raise HTTPException(503, "Não foi possível proteger os dados do perfil.") from None
    address = payload.address.model_dump()
    address["zip_code"] = re.sub(r"\D", "", address["zip_code"])
    address["state"] = address["state"].upper()
    if address["street_number"].upper() not in {"S/N", "SN"} and not address["street_number"].isdigit():
        raise HTTPException(422, "Informe o número do endereço ou S/N.")
    if address["street_number"].upper() == "SN":
        address["street_number"] = "S/N"
    try:
        address_envelope = encrypt_private_document(
            json.dumps(address, ensure_ascii=False, separators=(",", ":")),
            tenant_id=session.tenant_id, field="photographer-address")
    except PrivateFieldError:
        raise HTTPException(503, "Não foi possível proteger os dados do endereço.") from None
    row = row or PhotographerBusinessProfile(admin_user_id=admin.id, tenant_id=session.tenant_id,
        full_name=full_name, cpf_envelope=envelope, cpf_fingerprint=fingerprint)
    row.cpf_envelope, row.cpf_fingerprint = envelope, fingerprint
    row.cpf_fingerprint_key_version = fingerprint_version
    row.address_envelope = address_envelope
    db.add(row)
    audit(db, "photographer_onboarding.profile_saved", str(admin.id), tenant_id=session.tenant_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Não foi possível salvar este perfil. Confira os dados e tente novamente.") from None
    return {"profile_complete": True}


@router.post("/terms/test-acceptance")
def accept_local_test_terms(payload: TestTermsInput, request: Request, db: Database):
    from app.main import require_same_origin
    require_same_origin(request)
    session, admin, signup = _context(request, db)
    terms = _terms_version(db)
    if not terms or not terms[3] or not payload.accepted:
        raise HTTPException(409, "Os termos não estão disponíveis para aceite.")
    profile = db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.admin_user_id == admin.id,
        PhotographerBusinessProfile.tenant_id == session.tenant_id,
    ).with_for_update())
    if not profile or not profile.cpf_envelope or not profile.address_envelope:
        raise HTTPException(409, "Complete o perfil antes do aceite.")
    existing = db.scalar(select(PhotographerTermsAcceptance.id).where(
        PhotographerTermsAcceptance.admin_user_id == admin.id,
        PhotographerTermsAcceptance.tenant_id == session.tenant_id,
        PhotographerTermsAcceptance.terms_version == terms[0],
    ))
    if existing:
        return {"terms_accepted": True, "test_only": True}
    photographer_identity = f"{profile.full_name}; {admin.email}; CPF cadastrado protegido"
    row = PhotographerTermsAcceptance(
        admin_user_id=admin.id, tenant_id=session.tenant_id, terms_version=terms[0],
        terms_text=terms[1], terms_sha256=hashlib.sha256(terms[1].encode()).hexdigest(),
        provider_identity=terms[2], photographer_identity=photographer_identity,
        accepted_at=now(), environment=os.getenv("APP_ENV", "development"),
    )
    db.add(row)
    audit(db, "photographer_onboarding.test_terms_accepted", str(signup.id), tenant_id=session.tenant_id)
    db.commit()
    return {"terms_accepted": True, "test_only": True}


@router.post("/terms/accept")
def accept_published_terms(payload: TermsAcceptanceInput, request: Request, db: Database):
    from app.main import require_same_origin
    require_same_origin(request)
    session, admin, signup = _context(request, db)
    published = latest_published(db)
    if not published or published.terms_version != payload.version:
        raise HTTPException(409, "Os termos mudaram. Atualize o documento antes de aceitar.")
    profile = db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.admin_user_id == admin.id,
        PhotographerBusinessProfile.tenant_id == session.tenant_id,
    ).with_for_update())
    if not profile or not profile.cpf_envelope or not profile.address_envelope:
        raise HTTPException(409, "Complete o perfil antes do aceite.")
    existing = db.scalar(select(PhotographerTermsAcceptance.id).where(
        PhotographerTermsAcceptance.admin_user_id == admin.id,
        PhotographerTermsAcceptance.tenant_id == session.tenant_id,
        PhotographerTermsAcceptance.terms_version == published.terms_version,
    ))
    if existing:
        return {"terms_accepted": True, "version": published.terms_version}
    try:
        text = render_terms(published.template_text,
                            provider_legal_name=published.provider_legal_name,
                            provider_contact_email=published.provider_contact_email,
                            photographer_name=signup.photographer_name,
                            photographer_verified_email=admin.email)
    except ValueError:
        raise HTTPException(503, "Os termos operacionais ainda não estão disponíveis.") from None
    photographer_identity = f"{profile.full_name}; {admin.email}; CPF cadastrado protegido"
    row = PhotographerTermsAcceptance(
        admin_user_id=admin.id, tenant_id=session.tenant_id, terms_version=published.terms_version,
        terms_text=text, terms_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        provider_identity=f"{published.provider_legal_name}; {published.provider_contact_email}",
        photographer_identity=photographer_identity, accepted_at=now(),
        environment=os.getenv("APP_ENV", "development"),
    )
    db.add(row)
    audit(db, "photographer_onboarding.terms_accepted", str(signup.id), tenant_id=session.tenant_id)
    db.commit()
    return {"terms_accepted": True, "version": published.terms_version}


@router.get("/terms/acceptances")
def own_term_acceptances(request: Request, db: Database):
    session, admin, _signup = _context(request, db)
    rows = db.scalars(select(PhotographerTermsAcceptance).where(
        PhotographerTermsAcceptance.admin_user_id == admin.id,
        PhotographerTermsAcceptance.tenant_id == session.tenant_id,
    ).order_by(PhotographerTermsAcceptance.accepted_at.desc()))
    return {"items": [{
        "id": str(row.id), "version": row.terms_version, "accepted_at": row.accepted_at,
    } for row in rows]}


@router.get("/terms/acceptances/{acceptance_id}/copy")
def download_own_term_acceptance(acceptance_id: UUID, request: Request, db: Database):
    session, admin, _signup = _context(request, db)
    row = db.scalar(select(PhotographerTermsAcceptance).where(
        PhotographerTermsAcceptance.id == acceptance_id,
        PhotographerTermsAcceptance.admin_user_id == admin.id,
        PhotographerTermsAcceptance.tenant_id == session.tenant_id,
    ))
    if not row:
        raise HTTPException(404, "Cópia do aceite não encontrada.")
    safe_version = re.sub(r"[^A-Za-z0-9._-]", "_", row.terms_version)
    protocol = (
        f"Pick-your-Pic — Protocolo de aceite dos Termos\n"
        f"Versão: {row.terms_version}\n"
        f"Aceito em (UTC): {row.accepted_at.isoformat()}\n"
        f"SHA-256: {row.terms_sha256}\n"
        f"Provedor: {row.provider_identity}\n"
        f"Fotógrafo: {row.photographer_identity}\n\n"
        f"--- Texto integral aceito ---\n\n{row.terms_text}\n"
    )
    return Response(content=protocol, media_type="text/plain", headers={
        "Cache-Control": "private, no-store",
        "Content-Disposition": f'attachment; filename="termos-pick-your-pic-{safe_version}.txt"',
        "X-Content-Type-Options": "nosniff",
    })
