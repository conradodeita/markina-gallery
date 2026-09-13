"""Endpoints administrativos do módulo; a entrega cliente mantém a autorização original."""

from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import (
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PreviewAdjustment,
    audit,
)
from app.media import safe_derivative_path
from app.preview_adjustment.engine import ENGINE_VERSION
from app.preview_adjustment.service import adjusted_path, configure, enqueue, settings


class ConfigurationInput(BaseModel):
    enabled: bool
    strength: int = Field(default=50, ge=10, le=75)


def register_routes(app, *, db_session, require_admin, preview_response):
    database_dependency = Depends(db_session)

    @app.get("/admin/preview-adjustment")
    def configuration(request: Request, db: Session = database_dependency):
        require_admin(request)
        config = settings(db)
        return {
            "enabled": bool(config and config.enabled),
            "strength": config.strength if config else 50,
            "generation": config.generation if config else 1,
            "engine": ENGINE_VERSION,
        }

    @app.patch("/admin/preview-adjustment")
    def save_configuration(
        payload: ConfigurationInput, request: Request, db: Session = database_dependency
    ):
        require_admin(request)
        configure(db, payload.enabled, payload.strength)
        audit(db, "preview_adjustment.configured", f"enabled:{payload.enabled}")
        db.commit()
        return configuration(request, db)

    @app.get("/admin/preview-adjustment/galleries")
    def galleries(
        request: Request,
        search: str = Query(default="", max_length=120),
        db: Session = database_dependency,
    ):
        require_admin(request)
        rows = db.execute(
            select(ParentGallery.id, ParentGallery.name)
            .where(
                ParentGallery.active.is_(True),
                ParentGallery.name.icontains(search, autoescape=True),
            )
            .order_by(ParentGallery.name, ParentGallery.id)
            .limit(100)
        )
        return [{"id": str(row.id), "name": row.name} for row in rows]

    @app.get("/admin/preview-adjustment/galleries/{gallery_id}")
    def gallery_progress(
        gallery_id: UUID,
        request: Request,
        after: UUID | None = None,
        db: Session = database_dependency,
    ):
        require_admin(request)
        if not db.get(ParentGallery, gallery_id):
            raise HTTPException(404, "Galeria não encontrada.")
        config = settings(db)
        query = (
            select(PreviewAdjustment.status, func.count())
            .join(PhotoAsset)
            .where(
                PhotoAsset.parent_gallery_id == gallery_id,
                PreviewAdjustment.generation == (config.generation if config else 1),
            )
            .group_by(PreviewAdjustment.status)
        )
        counts = {"queued": 0, "processing": 0, "ready": 0, "failed": 0, "cancelled": 0}
        counts.update(dict(db.execute(query).all()))
        photos = (
            select(PhotoAsset.id, PhotoAsset.filename)
            .join(PreviewAdjustment)
            .where(
                PhotoAsset.parent_gallery_id == gallery_id,
                PreviewAdjustment.generation == (config.generation if config else 1),
                PreviewAdjustment.status == "ready",
            )
            .order_by(PhotoAsset.id)
            .limit(41)
        )
        if after:
            photos = photos.where(PhotoAsset.id > after)
        rows = db.execute(photos).all()
        return {
            "counts": counts,
            "photos": [{"id": str(row.id), "filename": row.filename} for row in rows[:40]],
            "next_cursor": str(rows[39].id) if len(rows) > 40 else None,
        }

    @app.post("/admin/preview-adjustment/galleries/{gallery_id}/enqueue")
    def enqueue_gallery(
        gallery_id: UUID,
        request: Request,
        after: UUID | None = None,
        db: Session = database_dependency,
    ):
        require_admin(request)
        gallery = db.get(ParentGallery, gallery_id)
        if not gallery or not gallery.active or gallery.lifecycle_status != "active":
            raise HTTPException(409, "Galeria indisponível para processamento.")
        config = settings(db)
        if not config or not config.enabled:
            raise HTTPException(409, "Ative o ajuste de prévias primeiro.")
        query = (
            select(PhotoAsset.id)
            .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
            .where(
                PhotoAsset.parent_gallery_id == gallery_id,
                PhotoFolder.purpose == "content",
                PhotoAsset.available.is_(True),
            )
            .order_by(PhotoAsset.id)
            .limit(101)
        )
        if after:
            query = query.where(PhotoAsset.id > after)
        ids = list(db.scalars(query))
        queued = sum(enqueue(db, photo_id, retry=True) for photo_id in ids[:100])
        audit(db, "preview_adjustment.gallery_enqueued", str(gallery_id))
        db.commit()
        return {
            "queued": queued,
            "scanned": len(ids[:100]),
            "next_cursor": str(ids[99]) if len(ids) > 100 else None,
        }

    @app.get("/admin/preview-adjustment/photos/{photo_id}/{version}")
    def compare(photo_id: UUID, version: str, request: Request, db: Session = database_dependency):
        require_admin(request)
        if version not in {"before", "after"} or not db.get(PhotoAsset, photo_id):
            raise HTTPException(404, "Prévia indisponível.")
        if version == "after":
            path = adjusted_path(db, photo_id)
        else:
            derivative = db.scalar(
                select(MediaDerivative).where(
                    MediaDerivative.photo_asset_id == photo_id,
                    MediaDerivative.variant == "client_preview",
                    MediaDerivative.status == "ready",
                )
            )
            try:
                path = safe_derivative_path(derivative) if derivative else None
            except ValueError as exc:
                raise HTTPException(404, "Prévia indisponível.") from exc
        if not path:
            raise HTTPException(404, "Prévia indisponível.")
        return preview_response(path, f"previa-{photo_id}.jpg")
