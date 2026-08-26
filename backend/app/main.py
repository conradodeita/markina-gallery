"""API de autenticação unificada da Markina Gallery."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from io import BytesIO
from typing import Annotated
from uuid import UUID

import pyotp
from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import FileResponse, PlainTextResponse

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
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoComment,
    PhotoFavorite,
    PhotoSelection,
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


def assigned_photo_for_gallery(db: Session, gallery_id: UUID, photo_id: UUID) -> None:
    assigned = db.scalar(
        select(DerivedGalleryPhoto).where(
            DerivedGalleryPhoto.derived_gallery_id == gallery_id,
            DerivedGalleryPhoto.photo_asset_id == photo_id,
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
    destination = safe_source_path(photo)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(body)
    enqueue_derivatives(db, photo)
    audit(db, "photo_asset.imported", str(photo.id))
    db.commit()
    return {"status": "queued"}


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


@app.get("/library/purchases")
def client_purchase_history(
    request: Request, db: Session = Depends(db_session)
) -> dict[str, list[dict[str, object]]]:
    """Histórico confirmado da própria cliente, sem variante administrativa."""
    session = current_session(request, Role.CLIENT)
    orders = db.scalars(
        select(SaleOrder)
        .join(GalleryAccess, GalleryAccess.gallery_id == SaleOrder.derived_gallery_id)
        .where(
            SaleOrder.client_id == session.subject_id,
            SaleOrder.payment_status == "confirmed",
            GalleryAccess.client_id == session.subject_id,
            GalleryAccess.active,
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
        .where(DerivedGalleryPhoto.derived_gallery_id == gallery_id)
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
