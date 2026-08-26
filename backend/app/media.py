"""Processamento local de derivados privados da Markina Gallery."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import MediaDerivative, MediaJob, PhotoAsset, now

VARIANTS = {
    "thumbnail": (480, False),
    "client_preview": (1600, True),
    "admin_preview": (2000, False),
}


def source_root() -> Path:
    return Path(os.getenv("MEDIA_SOURCE_ROOT", "./media/source")).resolve()


def derivatives_root() -> Path:
    return Path(os.getenv("MEDIA_DERIVATIVES_ROOT", "./media/derivatives")).resolve()


def safe_source_path(photo: PhotoAsset) -> Path:
    candidate = (source_root() / photo.storage_key).resolve()
    try:
        candidate.relative_to(source_root())
    except ValueError as exc:
        raise ValueError("Caminho de mídia inválido.") from exc
    return candidate


def watermark(image: Image.Image) -> Image.Image:
    """Incorpora uma marca simples no bitmap que será entregue ao cliente."""
    marked = image.copy()
    draw = ImageDraw.Draw(marked, "RGBA")
    text = os.getenv("MEDIA_WATERMARK_TEXT", "MARKINA • PRÉVIA")
    for y in range(20, marked.height, 180):
        for x in range(12, marked.width, 280):
            draw.text((x, y), text, fill=(255, 255, 255, 105), stroke_width=1, stroke_fill=(0, 0, 0, 80))
    return marked


def enqueue_derivatives(db: Session, photo: PhotoAsset) -> MediaJob:
    job = db.scalar(
        select(MediaJob).where(
            MediaJob.photo_asset_id == photo.id, MediaJob.kind == "generate_derivatives"
        )
    )
    if not job:
        job = MediaJob(photo_asset_id=photo.id, status="queued", attempts=0)
        db.add(job)
    elif job.status in {"completed", "failed"}:
        job.status = "queued"
        job.last_error = None
    return job


def generate_derivatives(db: Session, photo: PhotoAsset) -> list[MediaDerivative]:
    """Gera variantes JPEG sem EXIF; segura para reexecução da mesma foto."""
    job = enqueue_derivatives(db, photo)
    job.status = "processing"
    job.attempts += 1
    job.updated_at = now()
    source = safe_source_path(photo)
    if not source.is_file():
        job.status = "failed"
        job.last_error = "Arquivo de origem indisponível."
        db.commit()
        raise FileNotFoundError("Arquivo de origem indisponível.")
    try:
        with Image.open(source) as opened:
            original = ImageOps.exif_transpose(opened).convert("RGB")
            derivatives: list[MediaDerivative] = []
            for variant, (max_width, protected) in VARIANTS.items():
                rendered = original.copy()
                rendered.thumbnail((max_width, max_width * 2), Image.Resampling.LANCZOS)
                if protected:
                    rendered = watermark(rendered)
                destination = derivatives_root() / str(photo.id) / f"{variant}.jpg"
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_suffix(".tmp")
                rendered.save(temporary, format="JPEG", quality=85, optimize=True)
                temporary.replace(destination)
                derivative = db.scalar(
                    select(MediaDerivative).where(
                        MediaDerivative.photo_asset_id == photo.id,
                        MediaDerivative.variant == variant,
                    )
                )
                if not derivative:
                    derivative = MediaDerivative(photo_asset_id=photo.id, variant=variant)
                    db.add(derivative)
                derivative.relative_path = destination.relative_to(derivatives_root()).as_posix()
                derivative.status = "ready"
                derivative.width, derivative.height = rendered.size
                derivative.updated_at = now()
                derivatives.append(derivative)
        job.status = "completed"
        job.last_error = None
        job.updated_at = now()
        db.commit()
        return derivatives
    except Exception as exc:
        job.status = "failed"
        job.last_error = "Falha ao gerar derivados."
        job.updated_at = now()
        db.commit()
        raise exc
