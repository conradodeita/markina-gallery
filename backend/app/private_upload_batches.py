"""Lotes explícitos e recuperáveis; uma pasta pode receber mais de um lote."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    MediaDerivative,
    MediaJob,
    PhotoAsset,
    PhotoFolder,
    PrivateUploadBatch,
    PrivateUploadBatchAsset,
    now,
)
from app.notification_settings import enqueue_event
from app.private_membership import client_has_operational_membership


def batch_for(db: Session, batch_id: UUID, gallery_id: UUID, *, open_only=False):
    batch = db.scalar(select(PrivateUploadBatch).where(
        PrivateUploadBatch.id == batch_id,
        PrivateUploadBatch.derived_gallery_id == gallery_id,
    ).with_for_update())
    if not batch or (open_only and batch.status != "open"):
        raise ValueError("Lote indisponível para novos arquivos.")
    return batch


def batch_payload(db: Session, batch: PrivateUploadBatch) -> dict:
    assets = list(db.execute(select(PhotoAsset.id, PhotoAsset.filename, PhotoAsset.storage_key,
                                   MediaJob.status).join(
        PrivateUploadBatchAsset, PrivateUploadBatchAsset.photo_asset_id == PhotoAsset.id
    ).outerjoin(MediaJob, MediaJob.photo_asset_id == PhotoAsset.id).where(
        PrivateUploadBatchAsset.batch_id == batch.id,
    )))
    return {"id": str(batch.id), "status": batch.status, "count": len(assets),
            "assets": [{"id": str(asset.id), "filename": asset.filename,
                        "storage_key": asset.storage_key, "status": asset.status or "not_imported"}
                       for asset in assets]}


def create_batch(db: Session, gallery: DerivedGallery, admin_id: UUID) -> PrivateUploadBatch:
    batch = PrivateUploadBatch(derived_gallery_id=gallery.id, actor_admin_id=admin_id)
    db.add(batch)
    db.flush()
    return batch


def close_batch(db: Session, batch_id: UUID, gallery_id: UUID) -> PrivateUploadBatch:
    batch = batch_for(db, batch_id, gallery_id)
    if batch.status == "open":
        batch.status = "closed"
        batch.closed_at = now()
        members = list(db.scalars(select(DerivedGalleryMembership).where(
            DerivedGalleryMembership.derived_gallery_id == gallery_id)))
        gallery = db.get(DerivedGallery, gallery_id)
        batch.recipient_ids = [str(member.client_id) for member in members if member.status == "active"] \
            if members else [str(gallery.client_id)]
    return batch


def process_ready_batches(db: Session) -> bool:
    """Encerra um lote terminal; nenhuma chamada de transporte e nenhuma espera facial."""
    pending_job = select(MediaJob.id).join(
        PrivateUploadBatchAsset, PrivateUploadBatchAsset.photo_asset_id == MediaJob.photo_asset_id
    ).where(PrivateUploadBatchAsset.batch_id == PrivateUploadBatch.id,
            MediaJob.status.in_(["queued", "processing"])).exists()
    for batch in db.scalars(select(PrivateUploadBatch).where(
        PrivateUploadBatch.status == "closed",
        ~pending_job,
    ).order_by(PrivateUploadBatch.closed_at).with_for_update(skip_locked=True).limit(100)):
        asset_ids = select(PrivateUploadBatchAsset.photo_asset_id).where(
            PrivateUploadBatchAsset.batch_id == batch.id)
        if db.scalar(select(MediaJob.id).where(MediaJob.photo_asset_id.in_(asset_ids),
                                               MediaJob.status.in_(["queued", "processing"]))):
            continue
        ready_count = len(list(db.scalars(select(PhotoAsset.id).join(
            MediaDerivative, MediaDerivative.photo_asset_id == PhotoAsset.id,
        ).join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id).where(
            PhotoAsset.id.in_(asset_ids), PhotoAsset.derived_gallery_id == batch.derived_gallery_id,
            PhotoAsset.available, PhotoFolder.purpose == "content", PhotoFolder.status == "released",
            MediaDerivative.variant == "client_preview", MediaDerivative.status == "ready",
            MediaDerivative.relative_path.is_not(None),
        ))))
        gallery = db.get(DerivedGallery, batch.derived_gallery_id)
        if ready_count and gallery and gallery.access_enabled:
            for raw_id in batch.recipient_ids:
                client_id = UUID(raw_id)
                if not client_has_operational_membership(db, gallery=gallery, client_id=client_id):
                    continue
                enqueue_event(db, event_type="private_photos_ready",
                              event_key=f"private_photos_ready:{batch.id}:{client_id}",
                              values={"galeria": gallery.name, "cliente": db.get(Client, client_id).full_name},
                              target_path=f"/gallery/{gallery.id}", recipients=[client_id],
                              parent_gallery_id=gallery.parent_gallery_id,
                              derived_gallery_id=gallery.id, client_id=client_id)
            batch.announced_at = now()
        batch.status = "completed"
        db.commit()
        return True
    db.rollback()
    return False
