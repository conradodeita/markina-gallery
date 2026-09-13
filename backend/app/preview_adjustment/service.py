"""Fila e resolução de prévias opcionais, independentes dos jobs convencionais."""

import hashlib
import json
import logging
from datetime import timedelta
from pathlib import Path
from time import monotonic
from uuid import UUID, uuid4

from PIL import Image
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.auth import (
    BrandingSettings,
    DerivedGallery,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PreviewAdjustment,
    PreviewAdjustmentSettings,
    now,
)
from app.media import derivatives_root, safe_derivative_path, watermark
from app.preview_adjustment.engine import ENGINE_VERSION, AdjustmentEngine, RawTherapeeEngine

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


def settings(db: Session, *, lock: bool = False) -> PreviewAdjustmentSettings | None:
    query = select(PreviewAdjustmentSettings).where(PreviewAdjustmentSettings.id == 1)
    if lock:
        query = query.with_for_update()
    return db.scalar(query.execution_options(populate_existing=True))


def configure(db: Session, enabled: bool, strength: int) -> PreviewAdjustmentSettings:
    config = settings(db, lock=True)
    if config is None:
        config = PreviewAdjustmentSettings(id=1, enabled=False, generation=1, strength=50)
        db.add(config)
        db.flush()
    if (config.enabled, config.strength) != (enabled, strength):
        config.enabled, config.strength = enabled, strength
        config.generation += 1
        config.updated_at = now()
        db.execute(
            update(PreviewAdjustment)
            .where(PreviewAdjustment.status.in_(("queued", "processing")))
            .values(status="cancelled", claim_token=None, updated_at=now())
        )
    return config


def inputs(db: Session, photo_id: UUID):
    derivatives = {
        row.variant: row
        for row in db.scalars(
            select(MediaDerivative)
            .where(
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
        select(BrandingSettings).limit(1).execution_options(populate_existing=True)
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
    if not photo:
        return False
    if photo.derived_gallery_id:
        gallery = db.get(DerivedGallery, photo.derived_gallery_id, populate_existing=True)
        return bool(gallery and gallery.lifecycle_status == "active")
    gallery = db.get(ParentGallery, photo.parent_gallery_id, populate_existing=True)
    return bool(gallery and gallery.active and gallery.lifecycle_status == "active")


def enqueue(db: Session, photo_id: UUID, *, retry: bool = False) -> bool:
    photo = db.scalar(select(PhotoAsset).where(PhotoAsset.id == photo_id).with_for_update())
    config = settings(db, lock=True)
    folder = db.get(PhotoFolder, photo.folder_id) if photo else None
    if (
        not config
        or not config.enabled
        or not photo_active(db, photo)
        or not folder
        or folder.purpose != "content"
    ):
        return False
    source = inputs(db, photo_id)
    if not source:
        return False
    row = db.get(PreviewAdjustment, photo_id)
    if row and row.generation == config.generation and row.fingerprint == source[2]:
        if row.status in {"queued", "processing"}:
            return False
        if row.status == "ready" and existing_result(row):
            return False
        if not retry:
            return False
    if row is None:
        row = PreviewAdjustment(photo_asset_id=photo_id)
        db.add(row)
    row.generation, row.fingerprint = config.generation, source[2]
    row.status, row.attempts, row.claim_token = "queued", 0, None
    row.last_error, row.elapsed_ms, row.updated_at = None, None, now()
    return True


def enqueue_after_derivatives(db: Session, photo_id: UUID) -> None:
    """Executar só após commit convencional; rollback afeta somente o módulo."""
    try:
        enqueue(db, photo_id)
        db.commit()
    except Exception:  # noqa: BLE001 -- Fronteira opcional: nunca reverter a importação concluída.
        db.rollback()
        logger.warning("preview_adjustment.enqueue_failed", extra={"photo_id": str(photo_id)})


def result_path(photo_id: UUID, claim: str) -> Path:
    # UUIDs e namespace fixo; nunca aceitar caminho arbitrário do cliente/banco.
    token = UUID(claim)
    root = derivatives_root()
    candidate = root / str(photo_id) / "preview-adjustment" / f"{token}.jpg"
    if (
        candidate.is_symlink()
        or candidate.parent.is_symlink()
        or candidate.parent.parent.is_symlink()
    ):
        raise ValueError("Caminho do ajuste inválido.")
    candidate.resolve().relative_to(root)
    return candidate


def existing_result(row: PreviewAdjustment) -> Path | None:
    if not row.relative_path:
        return None
    try:
        candidate = result_path(row.photo_asset_id, Path(row.relative_path).stem)
        if candidate.relative_to(derivatives_root()).as_posix() != row.relative_path:
            return None
        return candidate if candidate.is_file() else None
    except (ValueError, OSError):
        return None


def adjusted_path(db: Session, photo_id: UUID) -> Path | None:
    config = settings(db)
    if not config or not config.enabled:
        return None
    row = db.get(PreviewAdjustment, photo_id, populate_existing=True)
    if not row or row.status != "ready" or row.generation != config.generation:
        return None
    source = inputs(db, photo_id)
    if not source or row.fingerprint != source[2]:
        return None
    return existing_result(row)


def presentation_path(db: Session, derivative: MediaDerivative) -> Path:
    conventional = safe_derivative_path(derivative)
    try:
        # O savepoint também permite fallback durante indisponibilidade das tabelas opcionais.
        with db.begin_nested():
            return adjusted_path(db, derivative.photo_asset_id) or conventional
    except Exception:  # noqa: BLE001 -- Falha opcional não impede a prévia convencional autorizada.
        logger.warning("preview_adjustment.resolve_failed")
        return conventional


def process_one(session_factory, engine: AdjustmentEngine | None = None) -> bool:
    claim, photo_id = str(uuid4()), None
    with session_factory() as db:
        config = settings(db, lock=True)
        if not config or not config.enabled:
            return False
        stale = now() - timedelta(seconds=LEASE_SECONDS)
        row = db.scalar(
            select(PreviewAdjustment)
            .where(
                PreviewAdjustment.generation == config.generation,
                or_(
                    PreviewAdjustment.status == "queued",
                    (PreviewAdjustment.status == "processing")
                    & (PreviewAdjustment.updated_at < stale),
                ),
            )
            .order_by(PreviewAdjustment.updated_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not row:
            return False
        if row.attempts >= MAX_ATTEMPTS:
            row.status, row.last_error = "failed", "Processamento interrompido. Tente novamente."
            row.updated_at = now()
            db.commit()
            return True
        source = inputs(db, row.photo_asset_id)
        if not source or source[2] != row.fingerprint:
            row.status, row.updated_at = "cancelled", now()
            db.commit()
            return True
        photo_id, generation, fingerprint = row.photo_asset_id, row.generation, row.fingerprint
        strength = config.strength
        branding = (
            BrandingSettings(**{key: getattr(source[1], key) for key in PROTECTION_FIELDS})
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
        db.commit()

    started, output = monotonic(), None
    try:
        with Image.open(input_path) as opened:
            image = opened.convert("RGB")
            image.thumbnail((1600, 3200), Image.Resampling.LANCZOS)
        adjusted = (engine or RawTherapeeEngine()).render(image, strength)
        if adjusted.size != image.size:
            raise ValueError("Dimensões inválidas.")
        protected = watermark(adjusted, branding)
        # Nunca manter lock de banco durante o subprocesso.
        with session_factory() as db:
            parent_id = db.scalar(
                select(PhotoAsset.parent_gallery_id).where(PhotoAsset.id == photo_id)
            )
            if parent_id:
                # Mesmo lock usado ao congelar o manifesto de exclusão da galeria.
                db.scalar(
                    select(ParentGallery).where(ParentGallery.id == parent_id).with_for_update()
                )
            photo = db.scalar(select(PhotoAsset).where(PhotoAsset.id == photo_id).with_for_update())
            config = settings(db, lock=True)
            row = db.get(PreviewAdjustment, photo_id, populate_existing=True)
            source = inputs(db, photo_id) if photo else None
            if (
                not config
                or not config.enabled
                or config.generation != generation
                or not row
                or row.claim_token != claim
                or row.status != "processing"
                or not source
                or source[2] != fingerprint
                or not photo_active(db, photo)
            ):
                if row and row.claim_token == claim:
                    row.status, row.claim_token = "cancelled", None
                    db.commit()
                return True
            output = result_path(photo_id, claim)
            output.parent.mkdir(parents=True, exist_ok=True)
            protected.save(output, format="JPEG", quality=85, optimize=True, exif=b"")
            previous = existing_result(row)
            row.relative_path = output.relative_to(derivatives_root()).as_posix()
            row.status, row.last_error = "ready", None
            row.elapsed_ms, row.updated_at = int((monotonic() - started) * 1000), now()
            db.commit()
            if previous and previous != output:
                try:
                    previous.unlink(missing_ok=True)
                except OSError:
                    logger.warning("preview_adjustment.old_result_cleanup_failed")
        return True
    except Exception:  # noqa: BLE001 -- Motor substituível: sanitizar falhas e preservar o worker.
        if output:
            try:
                output.unlink(missing_ok=True)
            except OSError:
                logger.warning("preview_adjustment.failed_result_cleanup_failed")
        with session_factory() as db:
            db.execute(
                update(PreviewAdjustment)
                .where(
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
