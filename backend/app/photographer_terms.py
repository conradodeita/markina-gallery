"""Editor do proprietário e publicação versionada dos Termos do fotógrafo."""

import hashlib
import re
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin_account import AdminAccountError, normalize_admin_email
from app.auth import (
    AdminUser,
    PhotographerTermsAcceptance,
    PhotographerTermsDraft,
    PhotographerTermsVersion,
    audit,
    now,
)
from app.mercadopago_api import SensitiveRoute
from app.platform_console import (
    authorized,
    reauthenticate_console_owner,
    revalidate_owner_before_commit,
)
from app.totp_crypto import TotpSecretError

router = APIRouter(prefix="/admin/platform/terms", route_class=SensitiveRoute)
HEADERS = {"Cache-Control": "private, no-store"}
TOKENS = {
    "provider_legal_name",
    "provider_contact_email",
    "photographer_name",
    "photographer_verified_email",
}
DEFAULT_TEMPLATE = Path(__file__).with_name("photographer_terms_default.md")
DEFAULT_PROVIDER_LEGAL_NAME = ""


class DraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: UUID | None = None
    template_text: str = Field(min_length=1, max_length=50_000)
    provider_legal_name: str = Field(default="", max_length=160)
    provider_contact_email: str = Field(default="", max_length=320)


class PublishInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: UUID
    confirm_publication: Literal[True]
    current_password: SecretStr
    totp_code: SecretStr


def validate_template(value: str) -> str:
    template = value.strip()
    if not template:
        raise HTTPException(422, "O texto dos Termos está vazio.", headers=HEADERS)
    found = set(re.findall(r"\{\{([a-z_]+)\}\}", template))
    malformed = re.search(r"\{\{[^{}]*\}\}", re.sub(r"\{\{[a-z_]+\}\}", "", template))
    if found != TOKENS or malformed:
        raise HTTPException(422, "O modelo precisa manter os quatro campos dinâmicos oficiais.", headers=HEADERS)
    return template


def _draft_payload(row: PhotographerTermsDraft | None):
    if row:
        return {
            "revision": str(row.revision), "template_text": row.template_text,
            "provider_legal_name": row.provider_legal_name or "",
            "provider_contact_email": row.provider_contact_email or "",
            "updated_at": row.updated_at,
        }
    try:
        template = DEFAULT_TEMPLATE.read_text(encoding="utf-8-sig")
    except OSError:
        raise HTTPException(503, "Modelo inicial dos Termos indisponível.", headers=HEADERS) from None
    return {"revision": None, "template_text": template,
            "provider_legal_name": DEFAULT_PROVIDER_LEGAL_NAME,
            "provider_contact_email": "", "updated_at": None}


@router.get("/draft")
def get_draft(request: Request, response: Response):
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        row = db.get(PhotographerTermsDraft, 1)
        draft = _draft_payload(row)
        if not row:
            owner = db.get(AdminUser, session.subject_id)
            draft["provider_contact_email"] = owner.email if owner else ""
        return draft


@router.put("/draft")
def save_draft(payload: DraftInput, request: Request, response: Response):
    from app.main import require_same_origin
    require_same_origin(request)
    response.headers.update(HEADERS)
    template = validate_template(payload.template_text)
    provider_name = " ".join(payload.provider_legal_name.split())
    provider_email = payload.provider_contact_email.strip()
    if provider_email:
        try:
            provider_email = normalize_admin_email(provider_email)
        except AdminAccountError:
            raise HTTPException(422, "Informe um e-mail de contato válido.", headers=HEADERS) from None
    with authorized(request) as (db, session):
        row = db.scalar(select(PhotographerTermsDraft).where(
            PhotographerTermsDraft.id == 1,
        ).with_for_update())
        if row is None:
            if payload.revision is not None:
                raise HTTPException(409, "O rascunho mudou. Atualize a tela antes de salvar.", headers=HEADERS)
            row = PhotographerTermsDraft(id=1, revision=uuid4(), template_text=template)
            db.add(row)
        elif payload.revision != row.revision:
            raise HTTPException(409, "O rascunho mudou. Atualize a tela antes de salvar.", headers=HEADERS)
        row.revision = uuid4()
        row.template_text = template
        row.provider_legal_name = provider_name or None
        row.provider_contact_email = provider_email or None
        row.updated_by_admin_id = session.subject_id
        row.updated_at = now()
        audit(db, "photographer_terms.draft_saved", str(row.revision), tenant_id=session.tenant_id)
        try:
            revalidate_owner_before_commit(db, request, session)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "O rascunho mudou. Atualize a tela antes de salvar.", headers=HEADERS) from None
        return _draft_payload(row)


@router.get("/versions")
def list_versions(request: Request, response: Response):
    response.headers.update(HEADERS)
    with authorized(request) as (db, _session):
        rows = db.scalars(select(PhotographerTermsVersion).order_by(
            PhotographerTermsVersion.version_number.desc(),
        ).limit(20))
        return {"items": [{
            "version": row.terms_version, "template_sha256": row.template_sha256,
            "published_at": row.published_at, "provider_legal_name": row.provider_legal_name,
            "provider_contact_email": row.provider_contact_email,
        } for row in rows]}


@router.get("/acceptances/{tenant_id}")
def list_tenant_acceptances(tenant_id: UUID, request: Request, response: Response):
    response.headers.update(HEADERS)
    with authorized(request) as (db, _session):
        rows = db.scalars(select(PhotographerTermsAcceptance).where(
            PhotographerTermsAcceptance.tenant_id == tenant_id,
        ).order_by(PhotographerTermsAcceptance.accepted_at.desc()))
        return {"items": [{
            "id": str(row.id), "version": row.terms_version, "text": row.terms_text,
            "sha256": row.terms_sha256, "provider_identity": row.provider_identity,
            "photographer_identity": row.photographer_identity, "accepted_at": row.accepted_at,
            "environment": row.environment,
        } for row in rows]}


@router.post("/publish")
def publish(payload: PublishInput, request: Request, response: Response):
    from app.main import require_same_origin
    require_same_origin(request)
    response.headers.update(HEADERS)
    with authorized(request) as (db, session):
        draft = db.scalar(select(PhotographerTermsDraft).where(
            PhotographerTermsDraft.id == 1,
        ).with_for_update())
        if not draft or draft.revision != payload.expected_revision:
            raise HTTPException(409, "O rascunho mudou ou não foi salvo. Atualize antes de publicar.", headers=HEADERS)
        if not draft.provider_legal_name or not draft.provider_contact_email:
            raise HTTPException(409, "Informe a identidade e o contato do provedor antes de publicar.", headers=HEADERS)
        template = validate_template(draft.template_text)
        admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id).with_for_update())
        if not admin or not admin.totp_enabled:
            raise HTTPException(403, "A publicação exige autenticador habilitado.", headers=HEADERS)
        try:
            step = reauthenticate_console_owner(admin, payload)
        except (AdminAccountError, TotpSecretError, ValueError):
            raise HTTPException(403, "Credencial inválida.", headers=HEADERS) from None
        if step is None:
            raise HTTPException(403, "Credencial inválida.", headers=HEADERS)
        previous = db.scalar(select(PhotographerTermsVersion).order_by(
            PhotographerTermsVersion.version_number.desc(),
        ).limit(1))
        template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
        if previous and previous.template_sha256 == template_hash \
                and previous.provider_legal_name == draft.provider_legal_name \
                and previous.provider_contact_email == draft.provider_contact_email:
            return {"version": previous.terms_version, "template_sha256": previous.template_sha256,
                    "published_at": previous.published_at, "already_current": True}
        version_number = (previous.version_number if previous else 0) + 1
        row = PhotographerTermsVersion(
            version_number=version_number, terms_version=f"v{version_number}",
            template_text=template, template_sha256=template_hash,
            provider_legal_name=draft.provider_legal_name,
            provider_contact_email=draft.provider_contact_email,
            published_by_admin_id=session.subject_id, published_at=now(),
        )
        admin.totp_last_used_step = step
        db.add(row)
        audit(db, "photographer_terms.published", row.terms_version, tenant_id=session.tenant_id)
        try:
            revalidate_owner_before_commit(db, request, session)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Não foi possível publicar esta versão. Atualize e tente novamente.", headers=HEADERS) from None
        return {"version": row.terms_version, "template_sha256": row.template_sha256,
                "published_at": row.published_at, "already_current": False}


def latest_published(db: Session) -> PhotographerTermsVersion | None:
    return db.scalar(select(PhotographerTermsVersion).order_by(
        PhotographerTermsVersion.version_number.desc(),
    ).limit(1))


def render_terms(template: str, *, provider_legal_name: str, provider_contact_email: str,
                 photographer_name: str, photographer_verified_email: str) -> str:
    values = {
        "provider_legal_name": provider_legal_name,
        "provider_contact_email": provider_contact_email,
        "photographer_name": photographer_name,
        "photographer_verified_email": photographer_verified_email,
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    if "{{" in rendered or "}}" in rendered:
        raise ValueError("Unresolved terms template placeholder")
    return rendered
