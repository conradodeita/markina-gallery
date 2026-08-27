"""API de autenticação unificada da Markina Gallery."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from io import BytesIO
from os import getenv
from typing import Annotated
from uuid import UUID

import pyotp
from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from starlette.responses import FileResponse, PlainTextResponse

from app.auth import (
    AdminPasswordInput,
    AdminUser,
    AuditEvent,
    AuthChallenge,
    ChallengeResendInput,
    ChallengeVerification,
    Client,
    ClientChallengeInput,
    ClientPhone,
    DerivedGallery,
    DerivedGalleryPhoto,
    MediaDerivative,
    MediaJob,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoComment,
    PhotoFavorite,
    PhotoFolder,
    PhotoSelection,
    PhotoView,
    Role,
    SaleOrder,
    SaleOrderItem,
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
from app.media import enqueue_derivatives, safe_derivative_path, safe_source_path

app = FastAPI(title="Markina Gallery API", version="0.2.0")


class ParentGalleryInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    event_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5_000)


class ClientInput(BaseModel):
    full_name: str = Field(min_length=3, max_length=200)
    phone_e164: str = Field(min_length=8, max_length=32)


class PhotoAssetInput(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    display_name: str | None = Field(default=None, max_length=512)
    storage_key: str = Field(min_length=1, max_length=1_024)


class PhotoFolderInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class PhotoFolderRenameInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class PhotoFolderReleaseInput(BaseModel):
    gallery_ids: list[UUID] = Field(min_length=1, max_length=100)


class DerivedGalleryInput(BaseModel):
    parent_gallery_id: UUID
    client_id: UUID
    name: str = Field(min_length=1, max_length=200)
    photo_ids: list[UUID] = Field(default_factory=list)
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


class GalleryRenewalInput(BaseModel):
    selection_expires_at: datetime


class ClientLinkChallengeInput(ClientChallengeInput):
    parent_gallery_id: UUID | None = None


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


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DatabaseSession = Annotated[Session, Depends(db_session)]


def require_admin(request: Request) -> None:
    current_session(request, Role.ADMIN)


def derived_gallery_for_client(
    db: Session, gallery_id: UUID, client_id: UUID, *, require_access_enabled: bool = True
) -> DerivedGallery:
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery or gallery.client_id != client_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    if require_access_enabled and not gallery.access_enabled:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    return gallery


def assigned_photo_for_gallery(db: Session, gallery_id: UUID, photo_id: UUID) -> None:
    assigned = db.scalar(
        select(DerivedGalleryPhoto)
        .join(PhotoAsset, PhotoAsset.id == DerivedGalleryPhoto.photo_asset_id)
        .outerjoin(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(
            DerivedGalleryPhoto.derived_gallery_id == gallery_id,
            DerivedGalleryPhoto.photo_asset_id == photo_id,
            or_(PhotoAsset.folder_id.is_(None), PhotoFolder.status == "released"),
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
        gallery_query = gallery_query.where(DerivedGallery.client_id == client_id)
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
        for item in db.scalars(select(SaleOrderItem).where(SaleOrderItem.sale_order_id.in_(order_ids))):
            purchased_by_photo.setdefault(item.photo_asset_id, item.filename_snapshot)

    selections_query = select(PhotoSelection).where(PhotoSelection.derived_gallery_id.in_(gallery_ids))
    if starts_at:
        selections_query = selections_query.where(PhotoSelection.created_at >= starts_at)
    if ends_at:
        selections_query = selections_query.where(PhotoSelection.created_at <= ends_at)
    selected_ids = set(db.scalars(selections_query.with_only_columns(PhotoSelection.photo_asset_id)))
    selected_not_purchased_ids = selected_ids - set(purchased_by_photo)
    selected_names: dict[UUID, str] = {}
    if selected_not_purchased_ids:
        for photo in db.scalars(select(PhotoAsset).where(PhotoAsset.id.in_(selected_not_purchased_ids))):
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


@app.post("/auth/client/challenge", status_code=status.HTTP_202_ACCEPTED)
def client_challenge(
    payload: ClientLinkChallengeInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    phone = normalize_e164(payload.phone)
    enforce_rate_limit(
        db, "client_otp.challenge", phone, request.client.host if request.client else "unknown"
    )
    challenge, code = create_challenge(db, "client_otp", phone)
    if payload.parent_gallery_id:
        if not db.get(ParentGallery, payload.parent_gallery_id):
            audit(db, "client_otp.gallery_context_rejected", phone)
            db.commit()
            raise neutral_error()
        challenge.parent_gallery_id = payload.parent_gallery_id
        db.commit()
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
    phone = db.scalar(
        select(ClientPhone).where(ClientPhone.phone_e164 == challenge.subject, ClientPhone.active)
    )
    client = db.get(Client, phone.client_id) if phone else db.scalar(
        select(Client).where(Client.phone_e164 == challenge.subject)
    )
    if not client:
        audit(db, "client_otp.failed", challenge.subject)
        db.commit()
        raise neutral_error()
    gallery_ids = list(db.scalars(select(DerivedGallery.id).where(
        DerivedGallery.client_id == client.id, DerivedGallery.access_enabled
    )))
    if challenge.parent_gallery_id:
        registration = db.scalar(select(ParentGalleryRegistration).where(
            ParentGalleryRegistration.parent_gallery_id == challenge.parent_gallery_id,
            ParentGalleryRegistration.client_id == client.id,
        ))
        if not registration:
            registration = ParentGalleryRegistration(
                parent_gallery_id=challenge.parent_gallery_id, client_id=client.id, status="pending"
            )
            db.add(registration)
        audit(db, "parent_gallery.registration_completed", str(registration.id))
        private_gallery = db.scalar(select(DerivedGallery.id).where(
            DerivedGallery.parent_gallery_id == challenge.parent_gallery_id,
            DerivedGallery.client_id == client.id,
            DerivedGallery.access_enabled,
        ))
        destination = f"/gallery/{private_gallery}" if private_gallery else "/library?registration=pending"
    else:
        destination = f"/gallery/{gallery_ids[0]}" if len(gallery_ids) == 1 else "/library"
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


@app.get("/auth/destination")
def destination(request: Request) -> dict[str, str]:
    session = current_session(request)
    if session.role == Role.ADMIN.value:
        return {"destination": "/admin"}
    with SessionLocal() as db:
        galleries = list(db.scalars(select(DerivedGallery.id).where(
            DerivedGallery.client_id == session.subject_id, DerivedGallery.access_enabled
        )))
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


@app.get("/admin/validation-summary")
def admin_validation_summary(request: Request, db: Session = Depends(db_session)) -> dict[str, object]:
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
            "parent_galleries": len(list(db.scalars(select(ParentGallery.id)))),
            "derived_galleries": len(galleries),
            "imports": dict(job_states),
            "folders_preparing": len(list(db.scalars(select(PhotoFolder.id).where(PhotoFolder.status == "preparing")))),
            "folders_released": len(list(db.scalars(select(PhotoFolder.id).where(PhotoFolder.status == "released")))),
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
def admin_clients(request: Request, db: Session = Depends(db_session)) -> dict[str, list[dict[str, str]]]:
    require_admin(request)
    clients = db.scalars(select(Client).order_by(Client.full_name))
    return {"clients": [{"id": str(item.id), "name": item.full_name} for item in clients]}


@app.post("/admin/clients", status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    require_admin(request)
    phone = normalize_e164(payload.phone_e164)
    if db.scalar(select(Client).where(Client.phone_e164 == phone)):
        raise HTTPException(status_code=409, detail="Já existe cliente com este WhatsApp.")
    client = Client(full_name=payload.full_name.strip(), phone_e164=phone)
    db.add(client)
    db.flush()
    db.add(ClientPhone(client_id=client.id, phone_e164=phone, verified_at=now()))
    audit(db, "client.created_by_admin", str(client.id))
    db.commit()
    return {"id": str(client.id)}


@app.get("/admin/parent-galleries")
def admin_parent_galleries(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    require_admin(request)
    galleries = db.scalars(select(ParentGallery).order_by(ParentGallery.created_at.desc()))
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
    """Catálogo operacional do acervo-fonte, sem servir fotos a clientes."""
    require_admin(request)
    search = query.casefold() if query else ""
    rows = []
    for parent in db.scalars(select(ParentGallery).order_by(ParentGallery.created_at.desc())):
        galleries = list(db.scalars(select(DerivedGallery).where(
            DerivedGallery.parent_gallery_id == parent.id
        )))
        registrations = list(db.scalars(select(ParentGalleryRegistration).where(
            ParentGalleryRegistration.parent_gallery_id == parent.id
        )))
        owners = [db.get(Client, gallery.client_id) for gallery in galleries]
        if search and not (
            search in parent.name.casefold()
            or (parent.event_name and search in parent.event_name.casefold())
            or any(owner and (search in owner.full_name.casefold() or search in owner.phone_e164) for owner in owners)
        ):
            continue
        frozen = sum(bool(gallery.selection_expires_at and expired(gallery.selection_expires_at)) for gallery in galleries)
        rows.append({"id": str(parent.id), "name": parent.name, "event_name": parent.event_name or "", "active": parent.active, "private_gallery_count": len(galleries), "registration_count": len(registrations), "frozen_gallery_count": frozen})
    return {"total": len(rows), "parent_galleries": rows[offset : offset + limit]}


@app.get("/admin/parent-galleries/{parent_gallery_id}/photos")
def admin_parent_gallery_photos(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    require_admin(request)
    if not db.get(ParentGallery, parent_gallery_id):
        raise HTTPException(status_code=404, detail="Acervo não encontrado.")
    photos = db.scalars(
        select(PhotoAsset)
        .where(PhotoAsset.parent_gallery_id == parent_gallery_id)
        .order_by(PhotoAsset.filename)
    )
    return {"photos": [{"id": str(item.id), "name": item.display_name or item.filename} for item in photos]}


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
        raise HTTPException(status_code=404, detail="Acervo não encontrado.")
    folders = list(db.scalars(select(PhotoFolder).where(
        PhotoFolder.parent_gallery_id == parent_gallery_id
    ).order_by(PhotoFolder.position, PhotoFolder.created_at)))
    rows = []
    for folder in folders:
        count = db.scalar(select(func.count()).select_from(PhotoAsset).where(PhotoAsset.folder_id == folder.id)) or 0
        rows.append({"id": str(folder.id), "name": folder.name, "status": folder.status, "position": folder.position, "photo_count": count, "released_at": folder.released_at.isoformat() if folder.released_at else None})
    return {"total": len(rows), "folders": rows[offset : offset + limit]}


@app.post("/admin/parent-galleries/{parent_gallery_id}/folders", status_code=status.HTTP_201_CREATED)
def create_photo_folder(
    parent_gallery_id: UUID, payload: PhotoFolderInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    if not db.get(ParentGallery, parent_gallery_id):
        raise HTTPException(status_code=404, detail="Acervo não encontrado.")
    position = (db.scalar(select(func.max(PhotoFolder.position)).where(
        PhotoFolder.parent_gallery_id == parent_gallery_id
    )) or -1) + 1
    folder = PhotoFolder(parent_gallery_id=parent_gallery_id, name=payload.name.strip(), position=position)
    db.add(folder)
    db.flush()
    audit(db, "photo_folder.created", str(folder.id))
    db.commit()
    return {"id": str(folder.id), "status": folder.status, "position": folder.position}


@app.patch("/admin/photo-folders/{folder_id}")
def rename_photo_folder(
    folder_id: UUID, payload: PhotoFolderRenameInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    require_admin(request)
    folder = db.get(PhotoFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if folder.status == "released":
        raise HTTPException(status_code=409, detail="Uma pasta liberada não pode ser renomeada.")
    folder.name = payload.name.strip()
    audit(db, "photo_folder.renamed", str(folder.id))
    db.commit()
    return {"id": str(folder.id), "name": folder.name}


@app.delete("/admin/photo-folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo_folder(folder_id: UUID, request: Request, db: Session = Depends(db_session)) -> Response:
    require_admin(request)
    folder = db.get(PhotoFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if folder.status == "released" or db.scalar(select(PhotoAsset.id).where(PhotoAsset.folder_id == folder.id)):
        raise HTTPException(status_code=409, detail="Apenas pasta vazia em preparação pode ser excluída.")
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
    if not (folder := db.get(PhotoFolder, folder_id)):
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    photos = db.scalars(
        select(PhotoAsset).where(PhotoAsset.folder_id == folder.id).order_by(PhotoAsset.filename)
    )
    rows = []
    for photo in photos:
        job = db.scalar(select(MediaJob).where(MediaJob.photo_asset_id == photo.id))
        rows.append(
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "preview_url": f"/admin/photo-assets/{photo.id}/preview" if job and job.status == "completed" else None,
                "status": job.status if job else "not_imported",
                "error": job.last_error if job else None,
            }
        )
    return {"folder": {"id": str(folder.id), "status": folder.status}, "total": len(rows), "photos": rows}


@app.post("/admin/photo-folders/{folder_id}/photos", status_code=status.HTTP_201_CREATED)
def register_folder_photo_asset(
    folder_id: UUID,
    payload: PhotoAssetInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    """Registra uma foto exclusivamente dentro de uma pasta ainda em preparação."""
    require_admin(request)
    folder = db.get(PhotoFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if folder.status != "preparing":
        raise HTTPException(status_code=409, detail="A pasta não aceita novas fotos.")
    asset = PhotoAsset(parent_gallery_id=folder.parent_gallery_id, folder_id=folder.id, **payload.model_dump())
    db.add(asset)
    db.flush()
    audit(db, "photo_asset.registered_in_folder", str(asset.id))
    db.commit()
    return {"id": str(asset.id)}


@app.post("/admin/photo-folders/{folder_id}/release")
def release_photo_folder(
    folder_id: UUID,
    payload: PhotoFolderReleaseInput,
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, object]:
    """Disponibiliza um lote concluído apenas nas galerias privadas indicadas."""
    require_admin(request)
    folder = db.get(PhotoFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    gallery_ids = set(payload.gallery_ids)
    galleries = list(db.scalars(select(DerivedGallery).where(DerivedGallery.id.in_(gallery_ids))))
    if len(galleries) != len(gallery_ids) or any(
        gallery.parent_gallery_id != folder.parent_gallery_id or not gallery.access_enabled
        for gallery in galleries
    ):
        raise HTTPException(status_code=422, detail="Cada destino deve ser uma galeria privada ativa deste acervo.")
    photos = list(db.scalars(select(PhotoAsset).where(PhotoAsset.folder_id == folder.id)))
    new_links = 0
    for gallery in galleries:
        existing_ids = set(db.scalars(select(DerivedGalleryPhoto.photo_asset_id).where(
            DerivedGalleryPhoto.derived_gallery_id == gallery.id,
            DerivedGalleryPhoto.photo_asset_id.in_([photo.id for photo in photos]),
        ))) if photos else set()
        for photo in photos:
            if photo.id not in existing_ids:
                db.add(DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=photo.id))
                new_links += 1
    if folder.status == "preparing":
        folder.status = "released"
        folder.released_at = now()
        audit(db, "photo_folder.released", str(folder.id))
    elif folder.status != "released":
        raise HTTPException(status_code=409, detail="A pasta não pode ser liberada.")
    db.commit()
    return {
        "id": str(folder.id),
        "status": folder.status,
        "photo_count": len(photos),
        "new_gallery_photo_links": new_links,
    }


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


@app.post("/admin/derived-galleries/{gallery_id}/clone", status_code=status.HTTP_201_CREATED)
def clone_derived_gallery(
    gallery_id: UUID, payload: CloneGalleryInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    """Cria galeria privada independente, copiando apenas referências de fotos."""
    require_admin(request)
    source = db.get(DerivedGallery, gallery_id)
    if not source or not db.get(Client, payload.client_id):
        raise HTTPException(status_code=404, detail="Galeria ou cliente não encontrado.")
    audit_key = f"derived_gallery.clone:{gallery_id}:{payload.client_id}:{payload.idempotency_key}"
    duplicate = db.scalar(select(AuditEvent).where(AuditEvent.event == audit_key))
    if duplicate:
        return {"id": duplicate.subject}
    gallery = DerivedGallery(
        parent_gallery_id=source.parent_gallery_id,
        client_id=payload.client_id,
        name=payload.name or source.name,
        custom_message=source.custom_message,
        selection_expires_at=source.selection_expires_at,
        access_enabled=source.access_enabled,
        favorites_enabled=source.favorites_enabled,
        comments_enabled=source.comments_enabled,
    )
    db.add(gallery)
    db.flush()
    photo_ids = db.scalars(select(DerivedGalleryPhoto.photo_asset_id).where(
        DerivedGalleryPhoto.derived_gallery_id == source.id
    ))
    db.add_all([DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=photo_id) for photo_id in photo_ids])
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
        raise neutral_error()
    existing = db.scalar(select(ClientPhone).where(ClientPhone.phone_e164 == phone, ClientPhone.active))
    if existing and existing.client_id != client_id:
        raise HTTPException(status_code=409, detail="Este WhatsApp já pertence a outra cliente.")
    for old_phone in db.scalars(select(ClientPhone).where(ClientPhone.client_id == client_id, ClientPhone.active)):
        old_phone.active = False
        old_phone.retired_at = now()
    if not existing:
        db.add(ClientPhone(client_id=client_id, phone_e164=phone, verified_at=now()))
    client.phone_e164 = phone
    audit(db, "client.phone_changed", str(client_id))
    db.commit()
    return {"id": str(client_id)}


@app.get("/admin/parent-galleries/{parent_gallery_id}/clients")
def parent_gallery_clients(
    parent_gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    if not db.get(ParentGallery, parent_gallery_id):
        raise HTTPException(status_code=404, detail="Acervo não encontrado.")
    registrations = list(db.scalars(select(ParentGalleryRegistration).where(
        ParentGalleryRegistration.parent_gallery_id == parent_gallery_id
    )))
    galleries = list(db.scalars(select(DerivedGallery).where(
        DerivedGallery.parent_gallery_id == parent_gallery_id
    )))
    client_ids = {item.client_id for item in registrations} | {item.client_id for item in galleries}
    rows = []
    for client_id in client_ids:
        client = db.get(Client, client_id)
        gallery = next((item for item in galleries if item.client_id == client_id), None)
        registration = next((item for item in registrations if item.client_id == client_id), None)
        rows.append({"client_id": str(client_id), "name": client.full_name if client else "Cliente", "phone": client.phone_e164 if client else "", "registration_status": registration.status if registration else None, "derived_gallery_id": str(gallery.id) if gallery else None})
    return {"parent_gallery_id": str(parent_gallery_id), "clients": sorted(rows, key=lambda item: item["name"])}


@app.get("/admin/derived-galleries/{gallery_id}/selection")
def selection_detail(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    owner = db.get(Client, gallery.client_id)
    selected = list(db.scalars(select(PhotoSelection).where(
        PhotoSelection.derived_gallery_id == gallery_id, PhotoSelection.client_id == gallery.client_id
    )))
    orders = list(db.scalars(select(SaleOrder).where(
        SaleOrder.derived_gallery_id == gallery_id, SaleOrder.client_id == gallery.client_id
    )))
    confirmed_items = list(db.scalars(
        select(SaleOrderItem).join(SaleOrder).where(
            SaleOrder.derived_gallery_id == gallery_id, SaleOrder.payment_status == "confirmed"
        )
    ))
    sales_by_photo: dict[UUID, int] = {}
    for item in confirmed_items:
        sales_by_photo[item.photo_asset_id] = sales_by_photo.get(item.photo_asset_id, 0) + 1
    photos = []
    for selection in selected:
        photo = db.get(PhotoAsset, selection.photo_asset_id)
        if photo:
            photos.append({"id": str(photo.id), "filename": photo.filename, "preview_url": f"/admin/photo-assets/{photo.id}/preview", "sales_count": sales_by_photo.get(photo.id, 0)})
    return {"gallery": {"id": str(gallery.id), "name": gallery.name, "selection_expires_at": gallery.selection_expires_at.isoformat() if gallery.selection_expires_at else None}, "client": {"id": str(owner.id), "name": owner.full_name, "phone": owner.phone_e164} if owner else None, "selection_count": len(photos), "payment_status": next((order.payment_status for order in orders), "pending"), "photos": photos}


@app.get("/admin/derived-galleries/{gallery_id}/selection/export.{format}")
def export_selection(
    gallery_id: UUID, format: str, request: Request, db: Session = Depends(db_session)
) -> PlainTextResponse:
    require_admin(request)
    if format not in {"txt", "csv"}:
        raise HTTPException(status_code=404, detail="Formato não suportado.")
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    rows = []
    for selection in db.scalars(select(PhotoSelection).where(
        PhotoSelection.derived_gallery_id == gallery_id, PhotoSelection.client_id == gallery.client_id
    )):
        photo = db.get(PhotoAsset, selection.photo_asset_id)
        if photo:
            rows.append((str(photo.id), photo.filename))
    separator = "\t" if format == "txt" else ","
    content = "".join(f"{identifier}{separator}{filename}\n" for identifier, filename in rows)
    audit(db, "selection.exported", str(gallery_id))
    db.commit()
    return PlainTextResponse(content, media_type="text/plain" if format == "txt" else "text/csv", headers={"Content-Disposition": f'attachment; filename="selecao.{format}"'})


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
    if photo.folder_id:
        folder = db.get(PhotoFolder, photo.folder_id)
        if not folder or folder.status != "preparing":
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


@app.get("/admin/purchases")
def admin_purchase_history(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, object]]]:
    """Histórico confirmado para conferência exclusiva do fotógrafo."""
    require_admin(request)
    orders = db.scalars(
        select(SaleOrder)
        .where(SaleOrder.payment_status == "confirmed")
        .order_by(SaleOrder.confirmed_at.desc(), SaleOrder.created_at.desc())
    )
    result: list[dict[str, object]] = []
    for order in orders:
        client = db.get(Client, order.client_id)
        gallery = db.get(DerivedGallery, order.derived_gallery_id)
        items = db.scalars(
            select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id)
        )
        result.append(
            {
                "id": str(order.id),
                "client_name": client.full_name if client else "Cliente removido",
                "gallery_name": gallery.name if gallery else "Galeria removida",
                "total_cents": order.total_cents,
                "items": [
                    {
                        "photo_id": str(item.photo_asset_id),
                        "name": item.filename_snapshot,
                        "preview_url": f"/admin/photo-assets/{item.photo_asset_id}/preview",
                    }
                    for item in items
                ],
            }
        )
    return {"orders": result}


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
    if any(
        photo.folder_id
        and (not (folder := db.get(PhotoFolder, photo.folder_id)) or folder.status != "released")
        for photo in photos
    ):
        raise HTTPException(status_code=409, detail="Fotos de pasta em preparação não podem ser distribuídas.")
    gallery = DerivedGallery(**payload.model_dump(exclude={"photo_ids"}))
    db.add(gallery)
    db.flush()
    db.add_all(
        [DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=photo.id) for photo in photos]
    )
    audit(db, "derived_gallery.created", str(gallery.id))
    db.commit()
    return {"id": str(gallery.id)}


@app.delete("/admin/derived-galleries/{gallery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_derived_gallery(gallery_id: UUID, request: Request, db: Session = Depends(db_session)) -> Response:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    has_photos = db.scalar(select(DerivedGalleryPhoto.id).where(DerivedGalleryPhoto.derived_gallery_id == gallery.id))
    has_selections = db.scalar(select(PhotoSelection.id).where(PhotoSelection.derived_gallery_id == gallery.id))
    has_orders = db.scalar(select(SaleOrder.id).where(SaleOrder.derived_gallery_id == gallery.id))
    if has_photos or has_selections or has_orders:
        raise HTTPException(status_code=409, detail="Esta galeria possui histórico e deve ser congelada ou bloqueada.")
    audit(db, "derived_gallery.deleted", str(gallery.id))
    db.delete(gallery)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def gallery_operational_status(db: Session, gallery: DerivedGallery) -> dict[str, object]:
    selections = list(db.scalars(select(PhotoSelection).where(PhotoSelection.derived_gallery_id == gallery.id)))
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
    state: str | None = Query(default=None, pattern="^(selection_finalized|payment_pending|blocked|selection_in_progress)$"),
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
            matches = gallery.name.casefold().find(search) >= 0 or bool(owner and (
                owner.full_name.casefold().find(search) >= 0 or owner.phone_e164 == normalized
            ))
            if not matches:
                continue
        if state and not status_data[state]:
            continue
        cover = db.scalar(select(DerivedGalleryPhoto.photo_asset_id).where(DerivedGalleryPhoto.derived_gallery_id == gallery.id).limit(1))
        entries.append({
            "id": str(gallery.id), "name": gallery.name,
            "parent_gallery_id": str(gallery.parent_gallery_id),
            "selection_expires_at": gallery.selection_expires_at.isoformat() if gallery.selection_expires_at else None,
            "cover_preview_url": f"/admin/photo-assets/{cover}/preview" if cover else None,
            "responsible_count": 1,
            **status_data,
        })
    return {"total": len(entries), "galleries": entries[offset : offset + limit]}


@app.get("/admin/derived-galleries/{gallery_id}")
def derived_gallery_detail(gallery_id: UUID, request: Request, db: Session = Depends(db_session)) -> dict[str, object]:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
    status_data = gallery_operational_status(db, gallery)
    cover = db.scalar(select(DerivedGalleryPhoto.photo_asset_id).where(DerivedGalleryPhoto.derived_gallery_id == gallery.id).limit(1))
    owner = db.get(Client, gallery.client_id)
    selected_count = db.scalar(select(func.count()).select_from(PhotoSelection).where(PhotoSelection.derived_gallery_id == gallery.id, PhotoSelection.client_id == gallery.client_id)) or 0
    orders = list(db.scalars(select(SaleOrder).where(SaleOrder.derived_gallery_id == gallery.id, SaleOrder.client_id == gallery.client_id)))
    responsible = {"id": str(owner.id), "name": owner.full_name, "phone": owner.phone_e164, "active": gallery.access_enabled, "selected_count": selected_count, "payment_pending": any(order.payment_status == "pending" for order in orders), "confirmed_order_count": sum(order.payment_status == "confirmed" for order in orders)} if owner else None
    return {"id": str(gallery.id), "parent_gallery_id": str(gallery.parent_gallery_id), "name": gallery.name, "link": f"/?parent_gallery_id={gallery.parent_gallery_id}", "custom_message": gallery.custom_message or "", "favorites_enabled": gallery.favorites_enabled, "comments_enabled": gallery.comments_enabled, "selection_expires_at": gallery.selection_expires_at.isoformat() if gallery.selection_expires_at else None, "cover_preview_url": f"/admin/photo-assets/{cover}/preview" if cover else None, "responsible": responsible, **status_data}


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
    audit(db, "derived_gallery.updated", str(gallery.id))
    db.commit()
    return {"id": str(gallery.id)}


@app.post("/admin/derived-galleries/{gallery_id}/renew")
def renew_gallery_selection(
    gallery_id: UUID, payload: GalleryRenewalInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    require_admin(request)
    gallery = db.get(DerivedGallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Galeria não encontrada.")
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
    parents = list(db.scalars(select(ParentGallery).order_by(ParentGallery.name)))
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
def client_library(request: Request, db: Session = Depends(db_session)) -> dict[str, list[dict[str, object]]]:
    session = current_session(request, Role.CLIENT)
    galleries = db.scalars(
        select(DerivedGallery)
        .where(
            DerivedGallery.access_enabled,
            DerivedGallery.client_id == session.subject_id,
        )
        .order_by(DerivedGallery.created_at.desc())
    )
    rows: list[dict[str, object]] = []
    for gallery in galleries:
        folders = list(db.scalars(
            select(PhotoFolder)
            .join(PhotoAsset, PhotoAsset.folder_id == PhotoFolder.id)
            .join(DerivedGalleryPhoto, DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id)
            .where(DerivedGalleryPhoto.derived_gallery_id == gallery.id, PhotoFolder.status == "released")
            .distinct()
            .order_by(PhotoFolder.position, PhotoFolder.created_at)
        ))
        rows.append({
            "id": str(gallery.id),
            "name": gallery.name,
            "message": gallery.custom_message or "",
            "selection_expires_at": gallery.selection_expires_at.isoformat() if gallery.selection_expires_at else None,
            "folders": [{"id": str(folder.id), "name": folder.name} for folder in folders],
        })
    return {"galleries": rows}


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
        gallery = db.get(DerivedGallery, order.derived_gallery_id)
        items = db.scalars(
            select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id)
        )
        result.append(
            {
                "id": str(order.id),
                "gallery_name": gallery.name if gallery else "Galeria",
                "items": [
                    {
                        "photo_id": str(item.photo_asset_id),
                        "name": item.filename_snapshot,
                        "preview_url": f"/gallery/{order.derived_gallery_id}/photos/{item.photo_asset_id}/preview",
                    }
                    for item in items
                ],
            }
        )
    return {"orders": result}


@app.get("/gallery/{gallery_id}")
def gallery_area(gallery_id: UUID, request: Request) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    with SessionLocal() as db:
        derived_gallery_for_client(db, gallery_id, session.subject_id)
    return {"status": "authorized"}


@app.get("/gallery/{gallery_id}/photos")
def gallery_photos(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, str]]]:
    """Lista somente os identificadores e nomes atribuídos à galeria privada."""
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id)
    photos = db.scalars(
        select(PhotoAsset)
        .join(DerivedGalleryPhoto, DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id)
        .outerjoin(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(
            DerivedGalleryPhoto.derived_gallery_id == gallery_id,
            or_(PhotoAsset.folder_id.is_(None), PhotoFolder.status == "released"),
        )
        .order_by(PhotoAsset.created_at, PhotoAsset.filename)
    )
    return {
        "photos": [
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "preview_url": f"/gallery/{gallery_id}/photos/{photo.id}/preview",
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
    derived_gallery_for_client(db, gallery_id, session.subject_id)
    folders = db.scalars(
        select(PhotoFolder)
        .join(PhotoAsset, PhotoAsset.folder_id == PhotoFolder.id)
        .join(DerivedGalleryPhoto, DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id)
        .where(DerivedGalleryPhoto.derived_gallery_id == gallery_id, PhotoFolder.status == "released")
        .distinct()
        .order_by(PhotoFolder.position, PhotoFolder.created_at)
    )
    rows = []
    for folder in folders:
        count = db.scalar(
            select(func.count())
            .select_from(PhotoAsset)
            .join(DerivedGalleryPhoto, DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id)
            .where(DerivedGalleryPhoto.derived_gallery_id == gallery_id, PhotoAsset.folder_id == folder.id)
        ) or 0
        rows.append({"id": str(folder.id), "name": folder.name, "position": folder.position, "photo_count": count})
    return {"total": len(rows), "folders": rows}


@app.get("/gallery/{gallery_id}/review")
def gallery_review(
    gallery_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, object]:
    """Estado privado de revisão para cliente, incluindo permissões e interações próprias."""
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id)
    photos = list(
        db.scalars(
            select(PhotoAsset)
            .join(DerivedGalleryPhoto, DerivedGalleryPhoto.photo_asset_id == PhotoAsset.id)
            .where(DerivedGalleryPhoto.derived_gallery_id == gallery_id)
            .order_by(PhotoAsset.created_at, PhotoAsset.filename)
        )
    )
    photo_ids = {photo.id for photo in photos}
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
    viewed = set(db.scalars(select(PhotoView.photo_asset_id).where(
        PhotoView.derived_gallery_id == gallery_id, PhotoView.client_id == session.subject_id
    )))
    purchased = set(db.scalars(
        select(SaleOrderItem.photo_asset_id)
        .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
        .where(SaleOrder.derived_gallery_id == gallery_id, SaleOrder.client_id == session.subject_id,
               SaleOrder.payment_status == "confirmed")
    ))
    return {
        "gallery": {
            "name": gallery.name,
            "message": gallery.custom_message or "",
            "selection_expires_at": (
                gallery.selection_expires_at.isoformat() if gallery.selection_expires_at else None
            ),
            "selection_open": not gallery.selection_expires_at
            or not expired(gallery.selection_expires_at),
            "favorites_enabled": gallery.favorites_enabled,
            "comments_enabled": gallery.comments_enabled,
        },
        "photos": [
            {
                "id": str(photo.id),
                "name": photo.display_name or photo.filename,
                "preview_url": f"/gallery/{gallery_id}/photos/{photo.id}/preview",
                "selected": photo.id in selections,
                "favorited": photo.id in favorites,
                "purchase_state": "já comprada" if photo.id in purchased else (
                    "visualizada mas não comprada" if photo.id in viewed else "nova"
                ),
            }
            for photo in photos
            if photo.id in photo_ids
        ],
    }


@app.get("/gallery/{gallery_id}/photos/{photo_id}/preview")
def client_photo_preview(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> FileResponse:
    """Entrega somente o derivado com marca à cliente autorizada na galeria privada."""
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id)
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
    viewed = db.scalar(select(PhotoView).where(
        PhotoView.derived_gallery_id == gallery_id,
        PhotoView.client_id == session.subject_id,
        PhotoView.photo_asset_id == photo_id,
    ))
    if viewed:
        viewed.last_viewed_at = now()
    else:
        db.add(PhotoView(derived_gallery_id=gallery_id, client_id=session.subject_id, photo_asset_id=photo_id))
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
    existing = db.scalar(
        select(PhotoSelection).where(
            PhotoSelection.derived_gallery_id == gallery_id,
            PhotoSelection.photo_asset_id == photo_id,
            PhotoSelection.client_id == session.subject_id,
        )
    )
    if not existing:
        db.add(
            PhotoSelection(
                derived_gallery_id=gallery_id, photo_asset_id=photo_id, client_id=session.subject_id
            )
        )
        audit(db, "photo_selection.created", str(gallery_id))
        db.commit()
    return {"status": "selected"}


@app.delete("/gallery/{gallery_id}/photos/{photo_id}/selection", status_code=status.HTTP_204_NO_CONTENT)
def unselect_photo(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> Response:
    session = current_session(request, Role.CLIENT)
    derived_gallery_for_client(db, gallery_id, session.subject_id)
    selection = db.scalar(
        select(PhotoSelection).where(
            PhotoSelection.derived_gallery_id == gallery_id,
            PhotoSelection.photo_asset_id == photo_id,
            PhotoSelection.client_id == session.subject_id,
        )
    )
    if selection:
        db.delete(selection)
        audit(db, "photo_selection.removed", str(gallery_id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/gallery/{gallery_id}/photos/{photo_id}/favorite", status_code=status.HTTP_201_CREATED)
def favorite_photo(
    gallery_id: UUID, photo_id: UUID, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    gallery = derived_gallery_for_client(db, gallery_id, session.subject_id)
    if not gallery.favorites_enabled:
        raise HTTPException(status_code=403, detail="Favoritos não estão habilitados nesta galeria.")
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


@app.delete("/gallery/{gallery_id}/photos/{photo_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
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
    if not gallery.comments_enabled:
        raise HTTPException(status_code=403, detail="Comentários não estão habilitados nesta galeria.")
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
    derived_gallery_for_client(db, gallery_id, session.subject_id)
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
    "/admin/derived-galleries/{gallery_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT
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
    comment.removed_at = now()
    audit(db, "photo_comment.removed_by_admin", str(comment.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
