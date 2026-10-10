"""Fila e resolução de prévias opcionais, independentes dos jobs convencionais."""

import hashlib
import json
import logging
from datetime import timedelta
from pathlib import Path
from time import monotonic
from uuid import UUID, uuid4

from fastapi import HTTPException
from PIL import Image
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    BrandingSettings,
    DerivedGallery,
    FacialJob,
    FolderProcessingSettings,
    GalleryPreviewSettings,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PreviewAdjustment,
    Tenant,
    now,
)
from app.folder_processing import EffectivePreview, effective_preview
from app.media import derivatives_root, safe_derivative_path, watermark
from app.preview_adjustment.engine import (
    ENGINE_VERSION,
    AdjustmentEngine,
    RawTherapeeEngine,
    compensate_exposure,
)
from app.system_monitor.telemetry import observe_work

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
LEASE_SECONDS = 180
PROTECTION_FIELDS = (
    "watermark_text",
    "watermark_font",
    "watermark_color",
    "watermark_size",
    "watermark_direction",
    "watermark_opacity",
    "watermark_position",
    "watermark_shadow",
    "watermark_security_lines",
)


def settings(db: Session, gallery_id: UUID, *, tenant_id: UUID, lock: bool = False) -> GalleryPreviewSettings | None:
    require_active_owner(db, tenant_id)
    query = select(GalleryPreviewSettings).where(
        GalleryPreviewSettings.tenant_id == tenant_id,
        GalleryPreviewSettings.parent_gallery_id == gallery_id
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query.execution_options(populate_existing=True))


def configure(
    db: Session, gallery_id: UUID, enabled: bool, strength: int, exposure_tenths: int = 0,
    *, tenant_id: UUID,
) -> GalleryPreviewSettings:
    require_active_owner(db, tenant_id)
    # Serializa inclusive a primeira criação da configuração.
    gallery = db.scalar(
        select(ParentGallery).where(ParentGallery.id == gallery_id, ParentGallery.tenant_id == tenant_id).with_for_update()
    )
    if not gallery:
        raise ValueError("Galeria não encontrada.")
    config = settings(db, gallery_id, tenant_id=tenant_id, lock=True)
    if config is None:
        config = GalleryPreviewSettings(
            tenant_id=gallery.tenant_id,
            parent_gallery_id=gallery_id,
            enabled=False,
            generation=1,
            strength=50,
            exposure_tenths=0,
        )
        db.add(config)
        db.flush()
    if (config.enabled, config.strength, config.exposure_tenths) != (
        enabled,
        strength,
        exposure_tenths,
    ):
        config.enabled, config.strength, config.exposure_tenths = enabled, strength, exposure_tenths
        config.generation += 1
        config.updated_at = now()
        db.execute(
            update(PreviewAdjustment)
            .where(
                PreviewAdjustment.tenant_id == tenant_id,
                PreviewAdjustment.status.in_(("queued", "processing")),
                PreviewAdjustment.photo_asset_id.in_(
                    select(PhotoAsset.id).join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
                    .outerjoin(FolderProcessingSettings, FolderProcessingSettings.folder_id == PhotoFolder.id)
                    .where(PhotoAsset.tenant_id == tenant_id, PhotoAsset.parent_gallery_id == gallery_id,
                           or_(FolderProcessingSettings.folder_id.is_(None),
                               FolderProcessingSettings.preview_mode == "inherit"))
                ),
            )
            .values(status="cancelled", claim_token=None, updated_at=now())
        )
    return config


def effective_fingerprint(source_fingerprint: str, config: EffectivePreview) -> str:
    if config.mode == "inherit":
        return source_fingerprint  # compatibilidade com resultados legados da galeria
    return hashlib.sha256(f"{source_fingerprint}:{config.revision_key}".encode()).hexdigest()


def inputs(db: Session, photo_id: UUID, *, tenant_id: UUID):
    photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
    if not photo:
        return None
    require_active_owner(db, photo.tenant_id)
    derivatives = {
        row.variant: row
        for row in db.scalars(
            select(MediaDerivative)
            .where(
                MediaDerivative.tenant_id == photo.tenant_id,
                MediaDerivative.photo_asset_id == photo_id,
                MediaDerivative.variant.in_(("admin_preview", "client_preview")),
                MediaDerivative.status == "ready",
            )
            .execution_options(populate_existing=True)
        )
    }
    if len(derivatives) != 2:
        return None
    branding = db.scalar(
        select(BrandingSettings).where(BrandingSettings.tenant_id == photo.tenant_id).execution_options(populate_existing=True)
    )
    protection = {key: getattr(branding, key) for key in PROTECTION_FIELDS} if branding else {}
    values = [
        ENGINE_VERSION,
        protection,
        [
            (variant, str(row.id), row.updated_at.isoformat(), row.relative_path)
            for variant, row in sorted(derivatives.items())
        ],
    ]
    fingerprint = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
    return derivatives["admin_preview"], branding, fingerprint


def photo_active(db: Session, photo: PhotoAsset | None) -> bool:
    if not photo or not owned_record(db, PhotoAsset, photo.id, tenant_id=photo.tenant_id):
        return False
    parent = owned_record(db, ParentGallery, photo.parent_gallery_id, tenant_id=photo.tenant_id)
    if not parent or not parent.active or parent.lifecycle_status != "active":
        return False
    if photo.derived_gallery_id:
        gallery = owned_record(db, DerivedGallery, photo.derived_gallery_id, tenant_id=photo.tenant_id)
        return bool(gallery)
    return True


def adjustment_for(db: Session, photo_id: UUID, *, tenant_id: UUID) -> PreviewAdjustment | None:
    require_active_owner(db, tenant_id)
    return db.scalar(select(PreviewAdjustment).where(
        PreviewAdjustment.photo_asset_id == photo_id, PreviewAdjustment.tenant_id == tenant_id
    ).execution_options(populate_existing=True))


def private_facial_job_completed(db: Session, photo: PhotoAsset, folder: PhotoFolder) -> bool:
    if folder.audience_scope != "selected":
        return True
    latest_status = db.scalar(
        select(FacialJob.status)
        .where(
            FacialJob.tenant_id == photo.tenant_id,
            FacialJob.photo_asset_id == photo.id,
            FacialJob.kind == "index",
        )
        .order_by(FacialJob.created_at.desc(), FacialJob.id.desc())
        .limit(1)
    )
    return latest_status == "completed"


def enqueue(db: Session, photo_id: UUID, *, tenant_id: UUID, retry: bool = False) -> bool:
    from app.facial.lifecycle import media_can_proceed
    require_active_owner(db, tenant_id)
    photo = db.scalar(select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id, PhotoAsset.id == photo_id).with_for_update())
    if not photo or not media_can_proceed(db, photo_id, tenant_id=tenant_id):
        return False
    folder = owned_record(db, PhotoFolder, photo.folder_id, tenant_id=tenant_id) if photo else None
    config = effective_preview(db, folder, lock=True) if folder else None
    if (
        not config
        or not config.enabled
        or not photo_active(db, photo)
        or not folder
        or folder.purpose != "content"
    ):
        return False
    if not private_facial_job_completed(db, photo, folder):
        return False
    source = inputs(db, photo_id, tenant_id=tenant_id)
    if not source:
        return False
    fingerprint = effective_fingerprint(source[2], config)
    row = adjustment_for(db, photo_id, tenant_id=tenant_id)
    if row and row.generation == config.generation and row.fingerprint == fingerprint:
        if row.status in {"queued", "processing"}:
            return False
        if row.status == "ready" and existing_result(row):
            return False
        if not retry:
            return False
    if row is None:
        row = PreviewAdjustment(tenant_id=tenant_id, photo_asset_id=photo_id)
        db.add(row)
    row.generation, row.fingerprint = config.generation, fingerprint
    row.status, row.attempts, row.claim_token = "queued", 0, None
    row.last_error, row.elapsed_ms, row.updated_at = None, None, now()
    return True


def enqueue_after_derivatives(db: Session, photo_id: UUID, *, tenant_id: UUID) -> None:
    """Executar só após commit convencional; rollback afeta somente o módulo."""
    try:
        enqueue(db, photo_id, tenant_id=tenant_id)
        db.commit()
    except Exception:  # noqa: BLE001 -- Fronteira opcional: nunca reverter a importação concluída.
        db.rollback()
        logger.warning("preview_adjustment.enqueue_failed", extra={"photo_id": str(photo_id)})


def result_path(photo_id: UUID, claim: str, *, tenant_id: UUID, legacy: bool = False) -> Path:
    # UUIDs e namespace fixo; nunca aceitar caminho arbitrário do cliente/banco.
    token = UUID(claim)
    root = derivatives_root()
    prefix = root if legacy else root / "tenants" / str(tenant_id) / "photos"
    candidate = prefix / str(photo_id) / "preview-adjustment" / f"{token}.jpg"
    if (
        candidate.is_symlink()
        or candidate.parent.is_symlink()
        or candidate.parent.parent.is_symlink()
    ):
        raise ValueError("Caminho do ajuste inválido.")
    candidate.resolve().relative_to(root)
    if candidate.resolve().parent != candidate.parent:
        raise ValueError("Caminho do ajuste inválido.")
    return candidate


def existing_result(row: PreviewAdjustment) -> Path | None:
    if not row.relative_path:
        return None
    try:
        candidate = result_path(row.photo_asset_id, Path(row.relative_path).stem,
            tenant_id=row.tenant_id, legacy=not row.relative_path.startswith("tenants/"))
        if candidate.relative_to(derivatives_root()).as_posix() != row.relative_path:
            return None
        return candidate if candidate.is_file() else None
    except (ValueError, OSError):
        return None


def adjusted_path(db: Session, photo_id: UUID, *, tenant_id: UUID) -> Path | None:
    photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
    folder = owned_record(db, PhotoFolder, photo.folder_id, tenant_id=tenant_id) if photo else None
    config = effective_preview(db, folder) if folder else None
    if not config or not config.enabled:
        return None
    row = adjustment_for(db, photo_id, tenant_id=tenant_id)
    if not row or row.status != "ready" or row.generation != config.generation:
        return None
    source = inputs(db, photo_id, tenant_id=tenant_id)
    if not source or row.fingerprint != effective_fingerprint(source[2], config):
        return None
    return existing_result(row)


def presentation_path(db: Session, derivative: MediaDerivative) -> Path:
    if not owned_record(db, PhotoAsset, derivative.photo_asset_id, tenant_id=derivative.tenant_id):
        raise ValueError("Prévia indisponível.")
    conventional = safe_derivative_path(derivative)
    try:
        # O savepoint também permite fallback durante indisponibilidade das tabelas opcionais.
        with db.begin_nested():
            resolved = adjusted_path(db, derivative.photo_asset_id, tenant_id=derivative.tenant_id) or conventional
            require_active_owner(db, derivative.tenant_id)
            return resolved
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 -- Falha opcional não impede a prévia convencional autorizada.
        logger.warning("preview_adjustment.resolve_failed")
        require_active_owner(db, derivative.tenant_id)
        return conventional


@observe_work("preview_adjustment")
def process_one(session_factory, engine: AdjustmentEngine | None = None) -> bool:
    claim, photo_id = str(uuid4()), None
    with session_factory() as db:
        stale = now() - timedelta(seconds=LEASE_SECONDS)
        eligible = or_(
            PreviewAdjustment.status == "queued",
            (PreviewAdjustment.status == "processing") & (PreviewAdjustment.updated_at < stale),
        )
        candidate = db.execute(
            select(PreviewAdjustment.photo_asset_id, PreviewAdjustment.tenant_id, PhotoAsset.folder_id)
            .join(PhotoAsset, PhotoAsset.id == PreviewAdjustment.photo_asset_id)
            .join(Tenant, Tenant.id == PreviewAdjustment.tenant_id)
            .where(eligible, Tenant.status == "active", PhotoAsset.tenant_id == PreviewAdjustment.tenant_id)
            .order_by(PreviewAdjustment.updated_at, PreviewAdjustment.photo_asset_id)
            .limit(1)
        ).first()
        if not candidate:
            return False
        tenant_id = candidate.tenant_id
        require_active_owner(db, tenant_id)
        folder = owned_record(db, PhotoFolder, candidate.folder_id, tenant_id=tenant_id)
        config = effective_preview(db, folder, lock=True) if folder else None
        row = db.scalar(
            select(PreviewAdjustment)
            .where(
                PreviewAdjustment.tenant_id == tenant_id,
                PreviewAdjustment.photo_asset_id == candidate.photo_asset_id,
                eligible,
            )
            .order_by(PreviewAdjustment.updated_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not row:
            return False
        if not config or not config.enabled or row.generation != config.generation:
            row.status, row.claim_token, row.updated_at = "cancelled", None, now()
            db.commit()
            return True
        photo = owned_record(db, PhotoAsset, candidate.photo_asset_id, tenant_id=tenant_id)
        if photo and not private_facial_job_completed(db, photo, folder):
            row.status, row.claim_token, row.updated_at = "cancelled", None, now()
            db.commit()
            return True
        if row.attempts >= MAX_ATTEMPTS:
            row.status, row.last_error = "failed", "Processamento interrompido. Tente novamente."
            row.updated_at = now()
            db.commit()
            return True
        source = inputs(db, row.photo_asset_id, tenant_id=tenant_id)
        if not source or effective_fingerprint(source[2], config) != row.fingerprint:
            row.status, row.updated_at = "cancelled", now()
            db.commit()
            return True
        photo_id, generation, fingerprint = row.photo_asset_id, row.generation, row.fingerprint
        strength = config.strength
        exposure_tenths = config.exposure_tenths
        branding = (
            BrandingSettings(tenant_id=tenant_id, **{key: getattr(source[1], key) for key in PROTECTION_FIELDS})
            if source[1]
            else None
        )
        try:
            input_path = safe_derivative_path(source[0])
        except ValueError:
            row.status, row.last_error = "failed", "Prévia de entrada indisponível."
            row.updated_at = now()
            db.commit()
            return True
        row.status, row.claim_token, row.updated_at = "processing", claim, now()
        row.attempts += 1
        from app.facial.lifecycle import analysis_for
        highres = analysis_for(db, photo_id, tenant_id=tenant_id) is not None
        db.commit()

    started, output = monotonic(), None
    try:
        with Image.open(input_path) as opened:
            image = opened.convert("RGB")
            image.thumbnail((1980, 1980) if highres else (1600, 3200), Image.Resampling.LANCZOS)
        adjusted = (engine or RawTherapeeEngine()).render(image, strength)
        if adjusted.size != image.size:
            raise ValueError("Dimensões inválidas.")
        protected = watermark(compensate_exposure(adjusted, exposure_tenths), branding)
        # Nunca manter lock de banco durante o subprocesso.
        with session_factory() as db:
            require_active_owner(db, tenant_id)
            parent_id = db.scalar(
                select(PhotoAsset.parent_gallery_id).where(PhotoAsset.tenant_id == tenant_id, PhotoAsset.id == photo_id)
            )
            if parent_id:
                # Mesmo lock usado ao congelar o manifesto de exclusão da galeria.
                db.scalar(
                    select(ParentGallery).where(ParentGallery.tenant_id == tenant_id, ParentGallery.id == parent_id).with_for_update()
                )
            photo = db.scalar(select(PhotoAsset).where(PhotoAsset.tenant_id == tenant_id, PhotoAsset.id == photo_id).with_for_update())
            folder = owned_record(db, PhotoFolder, photo.folder_id, tenant_id=tenant_id) if photo else None
            config = effective_preview(db, folder, lock=True) if folder else None
            row = adjustment_for(db, photo_id, tenant_id=tenant_id)
            source = inputs(db, photo_id, tenant_id=tenant_id) if photo else None
            if (
                not config
                or not config.enabled
                or config.generation != generation
                or not row
                or row.claim_token != claim
                or row.status != "processing"
                or not source
                or effective_fingerprint(source[2], config) != fingerprint
                or not photo_active(db, photo)
                or (photo and folder and not private_facial_job_completed(db, photo, folder))
            ):
                if row and row.claim_token == claim:
                    row.status, row.claim_token = "cancelled", None
                    db.commit()
                return True
            require_active_owner(db, tenant_id)
            output = result_path(photo_id, claim, tenant_id=tenant_id)
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_suffix(".tmp")
            if highres:
                from app.media import save_presentation_jpeg
                save_presentation_jpeg(protected, temporary)
            else:
                protected.save(temporary, format="JPEG", quality=85, optimize=True, exif=b"")
            require_active_owner(db, tenant_id)
            temporary.replace(output)
            previous = existing_result(row)
            row.relative_path = output.relative_to(derivatives_root()).as_posix()
            row.status, row.last_error = "ready", None
            row.elapsed_ms, row.updated_at = int((monotonic() - started) * 1000), now()
            db.commit()
            # O worker de mídia possui o volume da fonte e reconcilia o descarte.
            # Este worker opcional conhece somente derivados, nunca o original.
            if previous and previous != output:
                try:
                    require_active_owner(db, tenant_id)
                    previous.unlink(missing_ok=True)
                except (OSError, HTTPException):
                    logger.warning("preview_adjustment.old_result_cleanup_failed")
        return True
    except Exception:  # noqa: BLE001 -- Motor substituível: sanitizar falhas e preservar o worker.
        if output:
            try:
                output.with_suffix(".tmp").unlink(missing_ok=True)
                output.unlink(missing_ok=True)
            except OSError:
                logger.warning("preview_adjustment.failed_result_cleanup_failed")
        with session_factory() as db:
            db.execute(
                update(PreviewAdjustment)
                .where(
                    PreviewAdjustment.tenant_id == tenant_id,
                    PreviewAdjustment.photo_asset_id == photo_id,
                    PreviewAdjustment.claim_token == claim,
                    PreviewAdjustment.status == "processing",
                )
                .values(
                    status="failed",
                    last_error="Não foi possível ajustar a prévia. Tente novamente.",
                    elapsed_ms=int((monotonic() - started) * 1000),
                    updated_at=now(),
                )
            )
            db.commit()
        logger.warning("preview_adjustment.render_failed", extra={"photo_id": str(photo_id)})
        return True
