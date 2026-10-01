"""Configuração efetiva da pasta; overrides nunca se somam ao padrão."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    FolderProcessingSettings,
    GalleryPreviewSettings,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PreviewAdjustment,
    now,
)


@dataclass(frozen=True)
class EffectivePreview:
    mode: str
    enabled: bool
    strength: int
    exposure_tenths: int
    generation: int
    revision_key: str


def folder_settings(db: Session, folder_id: UUID, *, tenant_id: UUID, lock: bool = False) -> FolderProcessingSettings | None:
    require_active_owner(db, tenant_id)
    query = select(FolderProcessingSettings).where(FolderProcessingSettings.folder_id == folder_id,
                                                FolderProcessingSettings.tenant_id == tenant_id)
    if lock:
        query = query.with_for_update()
    return db.scalar(query.execution_options(populate_existing=True))


def effective_preview(db: Session, folder: PhotoFolder, *, lock: bool = False) -> EffectivePreview:
    override = folder_settings(db, folder.id, tenant_id=folder.tenant_id, lock=lock)
    if override and override.preview_mode == "custom":
        return EffectivePreview("custom", True, override.preview_strength,
                                override.preview_exposure_tenths, override.revision,
                                f"folder:{folder.id}:{override.revision}")
    if override and override.preview_mode == "off":
        return EffectivePreview("off", False, 50, 0, override.revision,
                                f"folder-off:{folder.id}:{override.revision}")
    query = select(GalleryPreviewSettings).where(GalleryPreviewSettings.parent_gallery_id == folder.parent_gallery_id, GalleryPreviewSettings.tenant_id == folder.tenant_id)
    if lock:
        query = query.with_for_update()
    gallery = db.scalar(query.execution_options(populate_existing=True))
    return EffectivePreview("inherit", bool(gallery and gallery.enabled),
                            gallery.strength if gallery else 50,
                            gallery.exposure_tenths if gallery else 0,
                            gallery.generation if gallery else 1,
                            f"gallery:{folder.parent_gallery_id}:{gallery.generation if gallery else 1}")


def facial_processing_allowed(db: Session, folder_id: UUID, *, tenant_id: UUID) -> bool:
    override = folder_settings(db, folder_id, tenant_id=tenant_id)
    return not override or override.facial_mode != "off"


def configure_folder(db: Session, folder_id: UUID, *, tenant_id: UUID, preview_mode: str,
                     facial_mode: str, strength: int, exposure_tenths: int) -> FolderProcessingSettings:
    folder = owned_record(db, PhotoFolder, folder_id, tenant_id=tenant_id)
    if not folder or folder.purpose != "content" or folder.derived_gallery_id is not None:
        raise ValueError("Pasta de conteúdo não encontrada.")
    gallery = db.scalar(select(ParentGallery).where(ParentGallery.id == folder.parent_gallery_id, ParentGallery.tenant_id == tenant_id)
                        .with_for_update().execution_options(populate_existing=True))
    if not gallery or not gallery.active or gallery.lifecycle_status != "active":
        raise ValueError("Galeria indisponível para processamento.")
    if (preview_mode not in {"inherit", "custom", "off"}
            or facial_mode not in {"inherit", "on", "off"}
            or not 10 <= strength <= 75 or not -20 <= exposure_tenths <= 20):
        raise ValueError("Configuração de processamento inválida.")
    row = folder_settings(db, folder_id, tenant_id=tenant_id, lock=True)
    if row is None:
        row = FolderProcessingSettings(tenant_id=folder.tenant_id, folder_id=folder_id)
        db.add(row)
        db.flush()
    changed = (row.preview_mode, row.preview_strength, row.preview_exposure_tenths) != (
        preview_mode, strength, exposure_tenths)
    if changed:
        row.preview_mode, row.preview_strength, row.preview_exposure_tenths = (
            preview_mode, strength, exposure_tenths)
        row.revision += 1
        db.execute(update(PreviewAdjustment).where(
            PreviewAdjustment.tenant_id == tenant_id,
            PreviewAdjustment.photo_asset_id.in_(select(PhotoAsset.id).where(PhotoAsset.folder_id == folder_id, PhotoAsset.tenant_id == tenant_id)),
            PreviewAdjustment.status.in_(("queued", "processing")),
        ).values(status="cancelled", claim_token=None, updated_at=now()))
    row.facial_mode = facial_mode
    row.updated_at = now()
    return row
