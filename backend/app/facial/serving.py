"""Escolha fail-closed do engine para uma galeria autorizada."""

from __future__ import annotations

from datetime import UTC, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import client_tenant_id, owned_record
from app.auth import (
    FacialEmbeddingExperimentSetting,
    FacialJob,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    PhotoAnalysis,
    PhotoAsset,
    now,
)
from app.facial.config import FacialSettings
from app.facial.gemma_provider import (
    GEMMA_MODEL_ID,
    GEMMA_MODEL_REVISION,
    GEMMA_MODEL_VERSION,
)
from app.facial.indexing import index_idempotency_key


def gallery_search_engine(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID, settings: FacialSettings
) -> str:
    """Cobertura integral da galeria; a consulta mantém seu escopo autorizado."""
    tenant_id = client_tenant_id(db, client_id)
    gallery = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
    setting = db.get(FacialEmbeddingExperimentSetting, 1)
    if (
        settings.environment.lower() in {"prod", "production"}
        or gallery is None
        or setting is None
        or not setting.enabled
        or setting.mode != "shadow"
        or setting.enabled_since is None
        or setting.model_revision != GEMMA_MODEL_REVISION
        or setting.worker_last_seen_at is None
        or now()
        - (
            setting.worker_last_seen_at.replace(tzinfo=UTC)
            if setting.worker_last_seen_at.tzinfo is None
            else setting.worker_last_seen_at
        )
        > timedelta(seconds=45)
        or gallery.created_at is None
        or _utc(gallery.created_at) <= _utc(setting.enabled_since)
        or _utc(setting.worker_last_seen_at) > now()
    ):
        return "opencv-yunet-sface"

    photo_ids = list(
        db.scalars(
            select(PhotoAsset.id)
            .join(MediaDerivative, MediaDerivative.photo_asset_id == PhotoAsset.id)
            .where(
                PhotoAsset.tenant_id == tenant_id,
                PhotoAsset.parent_gallery_id == parent_gallery_id,
                PhotoAsset.derived_gallery_id.is_(None),
                PhotoAsset.available.is_(True),
                MediaDerivative.tenant_id == tenant_id,
                MediaDerivative.variant == "client_preview",
                MediaDerivative.status == "ready",
            )
            .order_by(PhotoAsset.created_at, PhotoAsset.id)
        )
    )
    if not photo_ids:
        return "opencv-yunet-sface"

    policy = db.scalar(
        select(GalleryFacialPolicy).where(
            GalleryFacialPolicy.tenant_id == tenant_id,
            GalleryFacialPolicy.parent_gallery_id == parent_gallery_id,
            GalleryFacialPolicy.status == "active",
        )
    )
    if policy is None:
        return "opencv-yunet-sface"

    latest: dict[UUID, FacialJob] = {}
    for job in db.scalars(
        select(FacialJob)
        .where(
            FacialJob.tenant_id == tenant_id,
            FacialJob.parent_gallery_id == parent_gallery_id,
            FacialJob.kind == "index_gemma",
            FacialJob.photo_asset_id.in_(photo_ids),
            FacialJob.model_version == GEMMA_MODEL_VERSION,
            FacialJob.quality_version == policy.quality_version,
        )
        .order_by(FacialJob.created_at.desc(), FacialJob.id.desc())
    ):
        if job.photo_asset_id is not None:
            latest.setdefault(job.photo_asset_id, job)
    if len(latest) != len(photo_ids) or any(
        latest[photo_id].status != "completed"
        or not latest[photo_id].preview_fingerprint
        for photo_id in photo_ids
    ):
        return "opencv-yunet-sface"
    from app.facial.lifecycle import source_job_key

    analyses = {row.photo_asset_id: row for row in db.scalars(select(PhotoAnalysis).where(
        PhotoAnalysis.tenant_id == tenant_id, PhotoAnalysis.photo_asset_id.in_(photo_ids),
    ))}
    previews = {row.photo_asset_id: row for row in db.scalars(select(MediaDerivative).where(
        MediaDerivative.tenant_id == tenant_id, MediaDerivative.photo_asset_id.in_(photo_ids),
        MediaDerivative.variant == "admin_preview", MediaDerivative.status == "ready",
    ))}
    for photo_id in photo_ids:
        job = latest[photo_id]
        source = analyses.get(photo_id)
        if source:
            expected_key = source_job_key(photo_id, source, policy, model_version=GEMMA_MODEL_VERSION)
            if job.preview_fingerprint != source.source_fingerprint:
                return "opencv-yunet-sface"
        else:
            preview = previews.get(photo_id)
            if preview is None or _utc(preview.updated_at) > _utc(job.created_at):
                return "opencv-yunet-sface"
            expected_key = index_idempotency_key(
                environment=settings.environment, gallery_id=parent_gallery_id, photo_id=photo_id,
                model_version=GEMMA_MODEL_VERSION, quality_version=policy.quality_version,
                index_generation=policy.index_generation, fingerprint=job.preview_fingerprint,
            )
        if job.idempotency_key != expected_key:
            return "opencv-yunet-sface"
    return GEMMA_MODEL_ID


def _utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
