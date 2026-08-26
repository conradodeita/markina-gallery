"""API de autenticação unificada da Markina Gallery."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pyotp
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    AdminPasswordInput,
    AdminUser,
    AuthChallenge,
    ChallengeResendInput,
    ChallengeVerification,
    Client,
    ClientChallengeInput,
    DerivedGallery,
    DerivedGalleryPhoto,
    GalleryAccess,
    ParentGallery,
    PhotoAsset,
    Role,
    SessionLocal,
    audit,
    consume_challenge,
    create_challenge,
    create_session,
    current_session,
    enforce_rate_limit,
    expired,
    neutral_error,
    normalize_e164,
    now,
    password_hasher,
    resend_client_challenge,
    revoke_subject_sessions,
    whatsapp_provider,
)

app = FastAPI(title="Markina Gallery API", version="0.2.0")


class ParentGalleryInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    event_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5_000)


class PhotoAssetInput(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    display_name: str | None = Field(default=None, max_length=512)
    storage_key: str = Field(min_length=1, max_length=1_024)


class DerivedGalleryInput(BaseModel):
    parent_gallery_id: UUID
    client_id: UUID
    name: str = Field(min_length=1, max_length=200)
    photo_ids: list[UUID] = Field(min_length=1)
    custom_message: str | None = Field(default=None, max_length=5_000)
    selection_expires_at: datetime | None = None
    access_enabled: bool = True
    favorites_enabled: bool = False
    comments_enabled: bool = False


class DerivedGallerySettingsInput(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    custom_message: str | None = Field(default=None, max_length=5_000)
    selection_expires_at: datetime | None = None
    access_enabled: bool | None = None
    favorites_enabled: bool | None = None
    comments_enabled: bool | None = None


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(request: Request) -> None:
    current_session(request, Role.ADMIN)


def derived_gallery_for_client(
    db: Session, gallery_id: UUID, client_id: UUID, *, require_access_enabled: bool = True
) -> DerivedGallery:
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery or gallery.client_id != client_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    access = db.scalar(
        select(GalleryAccess).where(
            GalleryAccess.gallery_id == gallery_id,
            GalleryAccess.client_id == client_id,
            GalleryAccess.active,
        )
    )
    if not access or (require_access_enabled and not gallery.access_enabled):
        raise HTTPException(status_code=403, detail="Acesso negado.")
    return gallery


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.post("/auth/client/challenge", status_code=status.HTTP_202_ACCEPTED)
def client_challenge(
    payload: ClientChallengeInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    phone = normalize_e164(payload.phone)
    enforce_rate_limit(
        db, "client_otp.challenge", phone, request.client.host if request.client else "unknown"
    )
    challenge, code = create_challenge(db, "client_otp", phone)
    whatsapp_provider.send_otp(phone, code)
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
    client = db.scalar(select(Client).where(Client.phone_e164 == challenge.subject))
    if not client:
        audit(db, "client_otp.failed", challenge.subject)
        db.commit()
        raise neutral_error()
    gallery_ids = list(
        db.scalars(
            select(GalleryAccess.gallery_id).where(
                GalleryAccess.client_id == client.id, GalleryAccess.active
            )
        )
    )
    create_session(db, response, Role.CLIENT, client.id)
    destination = f"/gallery/{gallery_ids[0]}" if len(gallery_ids) == 1 else "/library"
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
        except Exception:
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


@app.get("/auth/destination")
def destination(request: Request) -> dict[str, str]:
    session = current_session(request)
    if session.role == Role.ADMIN.value:
        return {"destination": "/admin"}
    with SessionLocal() as db:
        galleries = list(
            db.scalars(
                select(GalleryAccess.gallery_id).where(
                    GalleryAccess.client_id == session.subject_id, GalleryAccess.active
                )
            )
        )
    return {"destination": f"/gallery/{galleries[0]}" if len(galleries) == 1 else "/library"}


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


@app.post("/admin/parent-galleries", status_code=status.HTTP_201_CREATED)
def create_parent_gallery(
    payload: ParentGalleryInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    require_admin(request)
    gallery = ParentGallery(**payload.model_dump())
    db.add(gallery)
    db.flush()
    audit(db, "parent_gallery.created", str(gallery.id))
    db.commit()
    return {"id": str(gallery.id)}


@app.post("/admin/parent-galleries/{parent_gallery_id}/photos", status_code=status.HTTP_201_CREATED)
def register_photo_asset(
    parent_gallery_id: UUID,
    payload: PhotoAssetInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_admin(request)
    if not db.get(ParentGallery, parent_gallery_id):
        raise HTTPException(status_code=404, detail="Acervo não encontrado.")
    asset = PhotoAsset(parent_gallery_id=parent_gallery_id, **payload.model_dump())
    db.add(asset)
    db.flush()
    audit(db, "photo_asset.registered", str(asset.id))
    db.commit()
    return {"id": str(asset.id)}


@app.post("/admin/derived-galleries", status_code=status.HTTP_201_CREATED)
def create_derived_gallery(
    payload: DerivedGalleryInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    require_admin(request)
    if not db.get(ParentGallery, payload.parent_gallery_id) or not db.get(Client, payload.client_id):
        raise HTTPException(status_code=404, detail="Acervo ou cliente não encontrado.")
    requested_photo_ids = set(payload.photo_ids)
    photos = list(
        db.scalars(
            select(PhotoAsset).where(
                PhotoAsset.parent_gallery_id == payload.parent_gallery_id,
                PhotoAsset.id.in_(requested_photo_ids),
            )
        )
    )
    if len(photos) != len(requested_photo_ids):
        raise HTTPException(status_code=422, detail="Todas as fotos devem pertencer ao acervo informado.")
    gallery = DerivedGallery(**payload.model_dump(exclude={"photo_ids"}))
    db.add(gallery)
    db.flush()
    db.add(GalleryAccess(client_id=payload.client_id, gallery_id=gallery.id, active=payload.access_enabled))
    db.add_all(
        [DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=photo.id) for photo in photos]
    )
    audit(db, "derived_gallery.created", str(gallery.id))
    db.commit()
    return {"id": str(gallery.id)}


@app.patch("/admin/derived-galleries/{gallery_id}")
def update_derived_gallery(
    gallery_id: UUID,
    payload: DerivedGallerySettingsInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    for field in payload.model_fields_set:
        setattr(gallery, field, getattr(payload, field))
    if "access_enabled" in payload.model_fields_set:
        access = db.scalar(
            select(GalleryAccess).where(
                GalleryAccess.gallery_id == gallery.id, GalleryAccess.client_id == gallery.client_id
            )
        )
        if access:
            access.active = gallery.access_enabled
    audit(db, "derived_gallery.updated", str(gallery.id))
    db.commit()
    return {"id": str(gallery.id)}


@app.get("/library")
def client_library(request: Request, db: Session = Depends(db_session)) -> dict[str, list[dict[str, str]]]:
    session = current_session(request, Role.CLIENT)
    galleries = db.scalars(
        select(DerivedGallery)
        .join(GalleryAccess, GalleryAccess.gallery_id == DerivedGallery.id)
        .where(
            DerivedGallery.client_id == session.subject_id,
            DerivedGallery.access_enabled,
            GalleryAccess.client_id == session.subject_id,
            GalleryAccess.active,
        )
        .order_by(DerivedGallery.created_at.desc())
    )
    return {
        "galleries": [
            {"id": str(gallery.id), "name": gallery.name, "message": gallery.custom_message or ""}
            for gallery in galleries
        ]
    }


@app.get("/gallery/{gallery_id}")
def gallery_area(gallery_id: UUID, request: Request) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    with SessionLocal() as db:
        derived = db.get(DerivedGallery, gallery_id)
        if derived:
            derived_gallery_for_client(db, gallery_id, session.subject_id)
            return {"status": "authorized"}
        authorized = db.scalar(
            select(GalleryAccess).where(
                GalleryAccess.client_id == session.subject_id,
                GalleryAccess.gallery_id == gallery_id,
                GalleryAccess.active,
            )
        )
        if not authorized:
            audit(db, "gallery.access_denied", str(session.subject_id))
            db.commit()
            raise HTTPException(status_code=403, detail="Acesso negado.")
    return {"status": "authorized"}
