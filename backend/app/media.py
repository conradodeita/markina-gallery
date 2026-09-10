"""Processamento local de derivados privados da Markina Gallery."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import BrandingSettings, MediaDerivative, MediaJob, PhotoAsset, PhotoFolder, now

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


def watermark(image: Image.Image, settings: BrandingSettings | None = None) -> Image.Image:
    """Incorpora uma marca textual e a grade opcional sem alterar a foto."""
    marked = image.convert("RGBA")
    text = (settings.watermark_text if settings else None) or os.getenv("MEDIA_WATERMARK_TEXT", "MARKINA • PRÉVIA")
    direction = (settings.watermark_direction if settings else None) or "diagonal"
    color = (settings.watermark_color if settings else None) or "#FFFFFF"
    try:
        rgb = tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))
    except (ValueError, IndexError):
        rgb = (255, 255, 255)
    angle = {"horizontal": 0, "vertical": 90, "diagonal": 35}.get(direction, 35)
    size = max(10, min(96, (settings.watermark_size if settings else None) or 24))
    opacity = max(
        10, min(100, (settings.watermark_opacity if settings else None) or 42)
    )
    alpha = round(255 * opacity / 100)
    position = (settings.watermark_position if settings else None) or "middle-center"
    shadow = settings.watermark_shadow if settings else True
    security_lines = settings.watermark_security_lines if settings else False
    font_name = (settings.watermark_font if settings else None) or "sans-serif"
    font_file = {
        "sans-serif": "DejaVuSans.ttf",
        "serif": "DejaVuSerif.ttf",
        "monospace": "DejaVuSansMono.ttf",
        "DejaVuSans": "DejaVuSans.ttf",
        "DejaVuSerif": "DejaVuSerif.ttf",
    }.get(font_name, "DejaVuSans.ttf")
    try:
        font = ImageFont.truetype(font_file, size=size)
    except OSError:
        font = ImageFont.load_default()
    probe = Image.new("RGBA", (1, 1))
    probe_draw = ImageDraw.Draw(probe)
    left, top, right, bottom = probe_draw.textbbox((0, 0), text, font=font, stroke_width=1)
    if security_lines:
        grid = Image.new("RGBA", marked.size, (0, 0, 0, 0))
        grid_draw = ImageDraw.Draw(grid)
        spacing = max(90, size * 5)
        line_alpha = max(24, round(alpha * 0.42))
        line_width = max(1, size // 18)
        for offset in range(-marked.height, marked.width + marked.height, spacing):
            grid_draw.line(
                (offset, 0, offset + marked.height, marked.height),
                fill=(*rgb, line_alpha),
                width=line_width,
            )
            grid_draw.line(
                (offset, marked.height, offset + marked.height, 0),
                fill=(*rgb, line_alpha),
                width=line_width,
            )
        marked.alpha_composite(grid)

    layer_size = (max(1, right - left + 12), max(1, bottom - top + 12))
    layer = Image.new("RGBA", layer_size, (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    if shadow:
        layer_draw.text(
            (7 - left, 7 - top),
            text,
            font=font,
            fill=(0, 0, 0, min(190, alpha)),
        )
    layer_draw.text((5 - left, 5 - top), text, font=font, fill=(*rgb, alpha))
    if angle:
        layer = layer.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)

    horizontal, vertical = position.split("-", maxsplit=1)
    raw_anchor_x = {
        "left": 12,
        "center": (marked.width - layer.width) // 2,
        "right": marked.width - layer.width - 12,
    }.get(vertical, (marked.width - layer.width) // 2)
    raw_anchor_y = {
        "top": 20,
        "middle": (marked.height - layer.height) // 2,
        "bottom": marked.height - layer.height - 20,
    }.get(horizontal, (marked.height - layer.height) // 2)
    anchor_x = min(max(0, raw_anchor_x), max(0, marked.width - layer.width))
    anchor_y = min(max(0, raw_anchor_y), max(0, marked.height - layer.height))
    marked.alpha_composite(layer, (anchor_x, anchor_y))
    return marked.convert("RGB")


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
    db: Session,
    photo: PhotoAsset,
    job: MediaJob | None = None,
    *,
    variants: set[str] | None = None,
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
        # Serializa a geração com alterações globais. Se uma geração começou
        # antes, a atualização aguardará o commit e a reenfileirará em seguida.
        settings = db.scalar(select(BrandingSettings).limit(1).with_for_update())
        with Image.open(source) as opened:
            original = ImageOps.exif_transpose(opened).convert("RGB")
            derivatives: list[MediaDerivative] = []
            selected_variants = set(VARIANTS) if variants is None else variants
            if not selected_variants or not selected_variants.issubset(VARIANTS):
                raise ValueError("Variantes de mídia inválidas.")
            for variant, (max_width, protected) in VARIANTS.items():
                if variant not in selected_variants:
                    continue
                rendered = original.copy()
                rendered.thumbnail((max_width, max_width * 2), Image.Resampling.LANCZOS)
                if protected:
                    rendered = watermark(rendered, settings)
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
        folder = db.get(PhotoFolder, photo.folder_id)
        if folder and folder.purpose == "content":
            photo.available = True
            if folder.status == "preparing":
                folder.status = "released"
                folder.released_at = now()
        facial_analysis_preview = next(
            (
                derivative
                for derivative in derivatives
                if derivative.variant == "admin_preview"
            ),
            None,
        )
        if facial_analysis_preview:
            from app.facial.indexing import enqueue_photo_index_if_eligible

            enqueue_photo_index_if_eligible(
                db,
                photo,
                facial_analysis_preview,
                derivative_path=safe_derivative_path(facial_analysis_preview),
            )
        db.commit()
        return derivatives
    except Exception:
        job.status = "failed"
        job.last_error = "Falha ao gerar derivados."
        job.updated_at = now()
        db.commit()
        raise
