"""Executor isolado dos jobs faciais; o loop bloqueante é configurado separadamente."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.auth import FacialJob
from app.facial.config import FacialSettings
from app.facial.crypto import FacialCipher
from app.facial.engine import replace_photo_index
from app.facial.jobs import ClaimedFacialJob, FacialJobError, FacialJobRepository
from app.facial.provider import OpenCvSFaceProvider
from app.facial.purge import purge_gallery_records, purge_photo_records


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
    job = db.get(FacialJob, claim.id)
    if (
        job is None
        or job.kind != "index"
        or job.photo_asset_id is None
        or job.parent_gallery_id is None
    ):
        raise FacialJobError("Job facial não pode ser executado.")
    indexed = replace_photo_index(
        db,
        photo_id=job.photo_asset_id,
        derivatives_root=derivatives_root,
        provider=provider,
        cipher=cipher,
        settings=settings,
    )
    repository.progress(
        db,
        claim,
        done=indexed,
        total=indexed,
        lease_seconds=settings.job_lease_seconds,
    )
    return repository.complete(db, claim)


def process_claimed_purge_job(
    db: Session,
    claim: ClaimedFacialJob,
    *,
    repository: FacialJobRepository,
    reference_root: Path | None = None,
) -> FacialJob:
    job = db.get(FacialJob, claim.id)
    if job is None or job.kind != "purge":
        raise FacialJobError("Job facial não pode ser executado.")
    if job.photo_asset_id is not None:
        report = purge_photo_records(
            db,
            parent_gallery_id=job.parent_gallery_id,
            photo_asset_id=job.photo_asset_id,
            exclude_job_id=job.id,
        )
    else:
        report = purge_gallery_records(
            db,
            parent_gallery_id=job.parent_gallery_id,
            exclude_job_id=job.id,
            reference_root=reference_root,
        )
    removed = report.embeddings + report.candidates
    repository.progress(
        db, claim, done=removed, total=removed, lease_seconds=120
    )
    return repository.complete(db, claim)
