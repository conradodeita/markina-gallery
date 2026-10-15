"""Executor isolado dos jobs faciais; o loop bloqueante é configurado separadamente."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import FacialJob, GalleryFacialPolicy, PhotoAsset, PhotoFolder
from app.facial.config import FacialSettings
from app.facial.crypto import FacialCipher
from app.facial.engine import replace_photo_index
from app.facial.jobs import ClaimedFacialJob, FacialJobError, FacialJobRepository
from app.facial.provider import OpenCvSFaceProvider
from app.facial.purge import purge_gallery_records, purge_photo_records
from app.facial.rollout import rollout_is_active

logger = logging.getLogger(__name__)


def process_claimed_index_job(
    db: Session,
    claim: ClaimedFacialJob,
    *,
    repository: FacialJobRepository,
    provider: OpenCvSFaceProvider,
    cipher: FacialCipher,
    settings: FacialSettings,
    derivatives_root: Path,
) -> FacialJob:
    job = repository._leased(db, claim)
    if (
        job is None
        or job.kind not in {"index", "index_gemma"}
        or job.photo_asset_id is None
        or job.parent_gallery_id is None
    ):
        raise FacialJobError("Job facial não pode ser executado.")
    if not rollout_is_active(
        db,
        settings=settings,
        parent_gallery_id=job.parent_gallery_id,
     tenant_id=job.tenant_id):
        from app.facial.lifecycle import analysis_for
        analysis = analysis_for(db, job.photo_asset_id, lock=job.kind == "index", tenant_id=job.tenant_id)
        if analysis and job.kind == "index":
            analysis.state = "failed"
        return repository.cancel(db, claim)
    # Lease é exclusivo do job. Só SFace serializa PhotoAnalysis: Gemma não
    # mantém lock dessa linha durante a inferência e revalida a fonte ao terminar.
    repository._leased(db, claim)
    from app.facial.lifecycle import analysis_for, source_job_key
    analysis = analysis_for(db, job.photo_asset_id, lock=job.kind == "index", tenant_id=job.tenant_id)
    policy = db.scalar(select(GalleryFacialPolicy).where(
        GalleryFacialPolicy.tenant_id == job.tenant_id,
        GalleryFacialPolicy.parent_gallery_id == job.parent_gallery_id))
    if (
        analysis and policy
        and job.idempotency_key != source_job_key(job.photo_asset_id, analysis, policy, model_version=job.model_version)
    ):
        return repository.cancel(db, claim)  # um reupload já possui outra geração durável
    if job.kind == "index_gemma":
        from app.auth import FacialEmbeddingExperimentSetting

        setting = db.get(FacialEmbeddingExperimentSetting, 1, populate_existing=True)
        from app.facial.gemma_provider import GEMMA_MODEL_REVISION

        if (
            settings.environment.lower() in {"prod", "production"}
            or setting is None
            or not setting.enabled
            or setting.mode != "shadow"
            or setting.model_revision != GEMMA_MODEL_REVISION
        ):
            return repository.cancel(db, claim)
        from app.auth import ParentGallery

        gallery = db.get(ParentGallery, job.parent_gallery_id)
        if (
            gallery is None
            or setting.enabled_since is None
            or gallery.created_at is None
            or gallery.created_at <= setting.enabled_since
        ):
            return repository.cancel(db, claim)
    if job.attempts > 3:
        return repository.fail(db, claim, TimeoutError("Orçamento de tentativas excedido."),
                               max_attempts=3, retry_delay_seconds=5)
    indexed = replace_photo_index(
        db,
        photo_id=job.photo_asset_id,
        tenant_id=claim.tenant_id,
        authorize=lambda: repository._leased(db, claim),
        derivatives_root=derivatives_root,
        provider=provider,
        cipher=cipher,
        settings=settings,
    )
    if analysis and job.kind == "index":
        analysis.metrics = {**analysis.metrics, "attempts": job.attempts}
    repository.progress(
        db,
        claim,
        done=indexed,
        total=indexed,
        lease_seconds=settings.job_lease_seconds,
    )
    completed = repository.complete(db, claim)
    photo = db.get(PhotoAsset, completed.photo_asset_id) if completed.photo_asset_id else None
    folder = db.get(PhotoFolder, photo.folder_id) if photo else None
    if completed.kind == "index" and folder and folder.audience_scope == "selected":
        try:
            # Savepoint isolates this optional queue from the completed facial job.
            db.flush()
            with db.begin_nested():
                from app.preview_adjustment.service import enqueue

                enqueue(db, photo.id, tenant_id=completed.tenant_id, retry=True)
        except Exception:  # noqa: BLE001 -- O ajuste não pode reverter o índice facial concluído.
            logger.warning("preview_adjustment.enqueue_after_private_facial_failed",
                           extra={"photo_id": str(photo.id)})
    return completed


def process_claimed_purge_job(
    db: Session,
    claim: ClaimedFacialJob,
    *,
    repository: FacialJobRepository,
    reference_root: Path | None = None,
) -> FacialJob:
    job = repository._leased(db, claim)
    if job is None or job.kind != "purge":
        raise FacialJobError("Job facial não pode ser executado.")
    if job.photo_asset_id is not None:
        report = purge_photo_records(
            db,
            tenant_id=job.tenant_id,
            parent_gallery_id=job.parent_gallery_id,
            photo_asset_id=job.photo_asset_id,
            exclude_job_id=job.id,
        )
    else:
        report = purge_gallery_records(
            db,
            tenant_id=job.tenant_id,
            parent_gallery_id=job.parent_gallery_id,
            exclude_job_id=job.id,
            reference_root=reference_root,
        )
    removed = report.embeddings + report.candidates
    repository.progress(
        db, claim, done=removed, total=removed, lease_seconds=120
    )
    return repository.complete(db, claim)
