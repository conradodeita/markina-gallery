"""Gatilhos explícitos e idempotentes de indexação facial."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import (
    FacialJob,
    GalleryFacialPolicy,
    MediaDerivative,
    PhotoAsset,
)
from app.facial.config import (
    FacialConfigurationError,
    FacialSettings,
    facial_settings_from_environment,
)
from app.facial.jobs import FacialJobError, FacialJobRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackfillPage:
    queued: int
    scanned: int
    next_cursor: UUID | None
    completed: bool


def preview_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise FacialJobError("Prévia facial indisponível.") from exc
    return digest.hexdigest()


def index_idempotency_key(
    *,
    environment: str,
    gallery_id: UUID,
    photo_id: UUID,
    model_version: str,
    quality_version: str,
    fingerprint: str,
) -> str:
    canonical = ":".join(
        (
            environment,
            str(gallery_id),
            str(photo_id),
            model_version,
            quality_version,
            fingerprint,
        )
    )
    return f"facial-index:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def enqueue_photo_index_if_eligible(
    db: Session,
    photo: PhotoAsset,
    derivative: MediaDerivative,
    *,
    derivative_path: Path,
    settings: FacialSettings | None = None,
    repository: FacialJobRepository | None = None,
) -> FacialJob | None:
    """Enfileira um único evento; jamais torna a prévia dependente da face."""

    try:
        active = settings or facial_settings_from_environment(
            verify_runtime_assets=False
        )
        if not active.enabled or derivative.variant != "client_preview":
            return None
        if derivative.status != "ready" or not photo.available:
            return None
        policy = db.scalar(
            select(GalleryFacialPolicy).where(
                GalleryFacialPolicy.parent_gallery_id == photo.parent_gallery_id,
                GalleryFacialPolicy.status == "active",
            )
        )
        if not policy or not _policy_matches_settings(policy, active):
            return None
        fingerprint = preview_fingerprint(derivative_path)
        with db.begin_nested():
            item, _created = (repository or FacialJobRepository()).enqueue(
                db,
                kind="index",
                idempotency_key=index_idempotency_key(
                    environment=active.environment,
                    gallery_id=photo.parent_gallery_id,
                    photo_id=photo.id,
                    model_version=policy.model_version,
                    quality_version=policy.quality_version,
                    fingerprint=fingerprint,
                ),
                parent_gallery_id=photo.parent_gallery_id,
                photo_asset_id=photo.id,
                model_version=policy.model_version,
                quality_version=policy.quality_version,
                preview_fingerprint=fingerprint,
            )
        return item
    except (FacialConfigurationError, FacialJobError, OSError, SQLAlchemyError) as error:
        logger.warning("Indexação facial ignorada: %s", type(error).__name__)
        return None


def enqueue_gallery_backfill_page(
    db: Session,
    *,
    parent_gallery_id: UUID,
    derivatives_root: Path,
    cursor: UUID | None = None,
    limit: int = 100,
    settings: FacialSettings | None = None,
    repository: FacialJobRepository | None = None,
) -> BackfillPage:
    """Varre uma página somente quando chamada por ativação/retentativa explícita."""

    if not 1 <= limit <= 500:
        raise FacialJobError("Página de backfill facial inválida.")
    query = (
        select(PhotoAsset, MediaDerivative)
        .join(
            MediaDerivative,
            (MediaDerivative.photo_asset_id == PhotoAsset.id)
            & (MediaDerivative.variant == "client_preview")
            & (MediaDerivative.status == "ready"),
        )
        .where(
            PhotoAsset.parent_gallery_id == parent_gallery_id,
            PhotoAsset.available.is_(True),
        )
        .order_by(PhotoAsset.id)
        .limit(limit + 1)
    )
    if cursor is not None:
        query = query.where(PhotoAsset.id > cursor)
    rows = list(db.execute(query))
    page = rows[:limit]
    queued = 0
    safe_root = derivatives_root.resolve()
    for photo, derivative in page:
        if not derivative.relative_path:
            continue
        derivative_path = (safe_root / derivative.relative_path).resolve()
        try:
            derivative_path.relative_to(safe_root)
        except ValueError:
            logger.warning("Indexação facial ignorada: caminho de prévia inválido")
            continue
        item = enqueue_photo_index_if_eligible(
            db,
            photo,
            derivative,
            derivative_path=derivative_path,
            settings=settings,
            repository=repository,
        )
        queued += item is not None
    return BackfillPage(
        queued=queued,
        scanned=len(page),
        next_cursor=page[-1][0].id if len(rows) > limit else None,
        completed=len(rows) <= limit,
    )


def _policy_matches_settings(
    policy: GalleryFacialPolicy, settings: FacialSettings
) -> bool:
    return all(
        (
            policy.model_version == settings.model_version,
            policy.quality_version == settings.quality_version,
            policy.calibration_version == settings.calibration_version,
            policy.legal_notice_version == settings.legal_notice_version,
            policy.legal_basis_reference == settings.legal_basis_reference,
            policy.retention_policy_version == settings.retention_policy_version,
            policy.minor_policy_version == settings.minor_policy_version,
        )
    )
