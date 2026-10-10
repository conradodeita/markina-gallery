"""Operações administrativas de processamento limitadas a uma pasta de conteúdo."""

from uuid import UUID

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.acervo_context import owned_record
from app.auth import ParentGallery, PhotoAsset, PhotoFolder, PreviewAdjustment, audit
from app.facial.config import FacialConfigurationError, facial_settings_from_environment
from app.facial.indexing import enqueue_gallery_backfill_page
from app.facial.rollout import rollout_is_active
from app.facial.status import gallery_index_status, retry_all_failed_index_jobs
from app.folder_processing import (
    configure_folder,
    effective_preview,
    facial_processing_allowed,
    folder_settings,
)
from app.media import derivatives_root
from app.preview_adjustment.service import adjusted_path
from app.preview_adjustment.service import enqueue as enqueue_preview


class FolderProcessingInput(BaseModel):
    preview_mode: str = Field(pattern="^(inherit|custom|off)$")
    facial_mode: str = Field(pattern="^(inherit|on|off)$")
    preview_strength: int = Field(ge=10, le=75, strict=True)
    preview_exposure_tenths: int = Field(ge=-20, le=20, strict=True)


def register_routes(app, *, db_session, require_admin, require_same_origin, tenant_context):
    dependency = Depends(db_session)

    def folder_or_404(db: Session, folder_id: UUID, *, tenant_id: UUID) -> PhotoFolder:
        folder = owned_record(db, PhotoFolder, folder_id, tenant_id=tenant_id)
        if not folder or folder.purpose != "content" or folder.derived_gallery_id is not None:
            raise HTTPException(404, "Pasta de conteúdo não encontrada.")
        gallery = db.get(ParentGallery, folder.parent_gallery_id)
        if not gallery or not gallery.active or gallery.lifecycle_status != "active":
            raise HTTPException(409, "Galeria indisponível para processamento.")
        return folder

    @app.get("/admin/photo-folders/{folder_id}/processing")
    def configuration(folder_id: UUID, request: Request, db: Session = dependency):
        tenant_id = tenant_context(db, request)
        require_admin(request)
        folder = folder_or_404(db, folder_id, tenant_id=tenant_id)
        row = folder_settings(db, folder_id, tenant_id=tenant_id)
        effective = effective_preview(db, folder)
        total = db.scalar(select(func.count(PhotoAsset.id)).where(PhotoAsset.tenant_id == tenant_id).where(PhotoAsset.folder_id == folder_id,
                                                                  PhotoAsset.available.is_(True))) or 0
        preview_counts = dict(db.execute(select(PreviewAdjustment.status, func.count()).where(PreviewAdjustment.tenant_id == tenant_id)
                                         .join(PhotoAsset, PhotoAsset.id == PreviewAdjustment.photo_asset_id)
                                         .where(PhotoAsset.folder_id == folder_id)
                                         .group_by(PreviewAdjustment.status)).all())
        comparison_photo_id = None
        for photo_id in db.scalars(select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id).join(
            PreviewAdjustment, PreviewAdjustment.photo_asset_id == PhotoAsset.id)
            .where(PhotoAsset.folder_id == folder_id, PreviewAdjustment.status == "ready")
            .order_by(PhotoAsset.id).limit(10)):
            if adjusted_path(db, photo_id, tenant_id=tenant_id):
                comparison_photo_id = str(photo_id)
                break
        try:
            settings = facial_settings_from_environment(verify_runtime_assets=False)
            facial_available = bool(settings.enabled and rollout_is_active(
                db, settings=settings, parent_gallery_id=folder.parent_gallery_id, tenant_id=tenant_id))
        except Exception:  # noqa: BLE001 -- estado administrativo não deve quebrar o painel
            facial_available = False
        facial_status = gallery_index_status(db, parent_gallery_id=folder.parent_gallery_id,
                                             folder_id=folder_id, processing_enabled=facial_available, tenant_id=tenant_id)
        return {
            "folder_id": str(folder_id), "folder_name": folder.name,
            "private_folder": folder.audience_scope == "selected",
            "preview_mode": "custom" if folder.audience_scope == "selected" else row.preview_mode if row else "inherit",
            "facial_mode": "on" if folder.audience_scope == "selected" else row.facial_mode if row else "inherit",
            "preview_strength": effective.strength if folder.audience_scope == "selected" else row.preview_strength if row else 50,
            "preview_exposure_tenths": effective.exposure_tenths if folder.audience_scope == "selected" else row.preview_exposure_tenths if row else 0,
            "effective_preview": {"mode": effective.mode, "enabled": effective.enabled,
                                  "strength": effective.strength,
                                  "exposure_tenths": effective.exposure_tenths},
            "facial_available": facial_available,
            "facial_allowed": facial_processing_allowed(db, folder_id, tenant_id=tenant_id),
            "total_photos": total,
            "comparison_photo_id": comparison_photo_id,
            "preview_counts": {key: preview_counts.get(key, 0) for key in
                               ("queued", "processing", "ready", "failed", "cancelled")},
            "facial_counts": {"queued": facial_status.queued, "processing": facial_status.processing,
                              "completed": facial_status.ready, "failed": facial_status.failed},
        }

    @app.patch("/admin/photo-folders/{folder_id}/processing")
    def save(folder_id: UUID, payload: FolderProcessingInput, request: Request, db: Session = dependency):
        require_same_origin(request)
        tenant_id = tenant_context(db, request)
        require_admin(request)
        folder_or_404(db, folder_id, tenant_id=tenant_id)
        try:
            configure_folder(db, folder_id, tenant_id=tenant_id, preview_mode=payload.preview_mode,
                             facial_mode=payload.facial_mode, strength=payload.preview_strength,
                             exposure_tenths=payload.preview_exposure_tenths)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(409, str(exc)) from exc
        audit(db, "folder.processing_configured", str(folder_id), tenant_id=tenant_id)
        db.commit()
        return configuration(folder_id, request, db)

    @app.post("/admin/photo-folders/{folder_id}/processing/preview/enqueue")
    def enqueue_folder_preview(folder_id: UUID, request: Request, after: UUID | None = None,
                               db: Session = dependency):
        require_same_origin(request)
        tenant_id = tenant_context(db, request)
        require_admin(request)
        folder = folder_or_404(db, folder_id, tenant_id=tenant_id)
        if not effective_preview(db, folder).enabled:
            raise HTTPException(409, "Ative o ajuste desta pasta primeiro.")
        query = select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id).where(PhotoAsset.folder_id == folder_id,
                                            PhotoAsset.available.is_(True)).order_by(PhotoAsset.id).limit(101)
        if after:
            query = query.where(PhotoAsset.id > after)
        ids = list(db.scalars(query))
        queued = sum(enqueue_preview(db, photo_id, tenant_id=tenant_id, retry=True) for photo_id in ids[:100])
        audit(db, "folder.preview_enqueued", str(folder_id), tenant_id=tenant_id)
        db.commit()
        return {"queued": queued, "scanned": len(ids[:100]),
                "next_cursor": str(ids[99]) if len(ids) > 100 else None}

    @app.post("/admin/photo-folders/{folder_id}/processing/facial/reprocess")
    def reprocess_folder_facial(folder_id: UUID, request: Request, after: UUID | None = None,
                                db: Session = dependency):
        require_same_origin(request)
        tenant_id = tenant_context(db, request)
        require_admin(request)
        folder = folder_or_404(db, folder_id, tenant_id=tenant_id)
        if not facial_processing_allowed(db, folder_id, tenant_id=tenant_id):
            raise HTTPException(409, "Novos trabalhos faciais estão pausados nesta pasta.")
        try:
            settings = facial_settings_from_environment(verify_runtime_assets=False)
        except FacialConfigurationError as exc:
            raise HTTPException(409, "Reconhecimento facial indisponível no ambiente.") from exc
        if not settings.enabled or not rollout_is_active(db, settings=settings,
                                                          parent_gallery_id=folder.parent_gallery_id, tenant_id=tenant_id):
            raise HTTPException(409, "Reconhecimento facial indisponível para esta galeria.")
        query = select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id).where(PhotoAsset.folder_id == folder_id).order_by(PhotoAsset.id).limit(101)
        if after:
            query = query.where(PhotoAsset.id > after)
        ids = list(db.scalars(query))
        page_ids = ids[:100]
        page = enqueue_gallery_backfill_page(db, parent_gallery_id=folder.parent_gallery_id,
                                             folder_id=folder_id, derivatives_root=derivatives_root(),
                                             cursor=after, end_cursor=page_ids[-1] if page_ids else None,
                                             limit=100, settings=settings, tenant_id=tenant_id) if page_ids else None
        retried = retry_all_failed_index_jobs(db, parent_gallery_id=folder.parent_gallery_id,
                                              folder_id=folder_id, photo_ids=set(page_ids), tenant_id=tenant_id) if page_ids else 0
        audit(db, "folder.facial_reprocess_requested", str(folder_id), tenant_id=tenant_id)
        db.commit()
        return {"queued": page.queued if page else 0, "scanned": len(page_ids), "retried": retried,
                "next_cursor": str(ids[99]) if len(ids) > 100 else None}
