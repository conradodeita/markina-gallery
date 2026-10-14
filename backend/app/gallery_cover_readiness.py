"""Prontidão da capa configurada para o fluxo administrativo de Detalhes."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import owned_record
from app.auth import MediaDerivative, MediaJob, ParentGallery, PhotoAsset, PhotoFolder
from app.media import safe_derivative_path


def gallery_cover_readiness(db: Session, gallery: ParentGallery) -> dict[str, str]:
    missing = {
        "status": "missing",
        "message": "Defina uma imagem de capa para salvar Detalhes e concluir a galeria.",
    }
    photo = (
        owned_record(db, PhotoAsset, gallery.cover_photo_id, tenant_id=gallery.tenant_id)
        if gallery.cover_photo_id else None
    )
    if not photo or photo.parent_gallery_id != gallery.id:
        return missing
    folder = owned_record(db, PhotoFolder, photo.folder_id, tenant_id=gallery.tenant_id)
    if not folder or folder.parent_gallery_id != gallery.id:
        return missing
    derivative = db.scalar(select(MediaDerivative).where(
        MediaDerivative.tenant_id == gallery.tenant_id,
        MediaDerivative.photo_asset_id == photo.id,
        MediaDerivative.variant == "admin_preview",
    ))
    failed = {
        "status": "failed",
        "message": "Não foi possível preparar a capa. Envie novamente ou escolha outro JPEG.",
    }
    if derivative and derivative.status == "ready":
        try:
            safe_derivative_path(derivative)
        except ValueError:
            return failed
        return {"status": "ready", "message": "Capa pronta para apresentação."}
    job = db.scalar(select(MediaJob).where(
        MediaJob.tenant_id == gallery.tenant_id,
        MediaJob.photo_asset_id == photo.id,
        MediaJob.kind == "generate_derivatives",
    ))
    if (derivative and derivative.status == "failed") or (job and job.status == "failed"):
        return failed
    return {
        "status": "processing",
        "message": "A capa está sendo preparada. Aguarde a prévia ficar pronta.",
    }
