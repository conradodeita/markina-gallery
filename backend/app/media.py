"""Processamento local de derivados privados da Markina Gallery."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import MediaDerivative, MediaJob, ParentGallery, PhotoAsset, now

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


def safe_derivative_path(derivative: MediaDerivative) -> Path:
    """Resolve um derivado persistido sem aceitar caminhos vindos do browser."""
    if not derivative.relative_path:
        raise ValueError("Prévia indisponível.")
    candidate = (derivatives_root() / derivative.relative_path).resolve()
    try:
        candidate.relative_to(derivatives_root())
    except ValueError as exc:
        raise ValueError("Caminho de mídia inválido.") from exc
    return candidate


def watermark(image: Image.Image, gallery: ParentGallery | None = None) -> Image.Image:
    """Incorpora uma marca simples no bitmap que será entregue ao cliente."""
    marked = image.copy()
    draw = ImageDraw.Draw(marked, "RGBA")
    text = (gallery.watermark_text if gallery else None) or os.getenv("MEDIA_WATERMARK_TEXT", "MARKINA • PRÉVIA")
    direction = gallery.watermark_direction if gallery else "diagonal"
    color = gallery.watermark_color if gallery else "#FFFFFF"
    try:
        rgb = tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))
    except (ValueError, IndexError):
        rgb = (255, 255, 255)
    angle = {"horizontal": 0, "vertical": 90, "diagonal": 35}.get(direction, 35)
    size = max(10, min(96, gallery.watermark_size if gallery else 24))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        font = ImageFont.load_default()
    for y in range(20, marked.height, 180):
        for x in range(12, marked.width, 280):
            draw.text((x, y), text, font=font, fill=(*rgb, 105), stroke_width=1, stroke_fill=(0, 0, 0, 80), anchor=None)
    if angle:
        marked = marked.rotate(angle, expand=False, resample=Image.Resampling.BICUBIC)
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


def generate_derivatives(
    db: Session, photo: PhotoAsset, job: MediaJob | None = None
) -> list[MediaDerivative]:
    """Gera variantes JPEG sem EXIF; segura para reexecução da mesma foto."""
    job = job or enqueue_derivatives(db, photo)
    if job.status != "processing":
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
        gallery = db.get(ParentGallery, photo.parent_gallery_id)
        with Image.open(source) as opened:
            original = ImageOps.exif_transpose(opened).convert("RGB")
            derivatives: list[MediaDerivative] = []
            for variant, (max_width, protected) in VARIANTS.items():
                rendered = original.copy()
                rendered.thumbnail((max_width, max_width * 2), Image.Resampling.LANCZOS)
                if protected:
                    rendered = watermark(rendered, gallery)
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
    except Exception:
        job.status = "failed"
        job.last_error = "Falha ao gerar derivados."
        job.updated_at = now()
        db.commit()
        raise
