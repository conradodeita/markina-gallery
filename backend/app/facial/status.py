"""Progresso agregado e retentativa seletiva do índice facial."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import FacialJob, GalleryFacialPolicy, MediaDerivative, PhotoAsset, now


class FacialStatusError(RuntimeError):
    """Consulta ou retentativa administrativa inválida."""


@dataclass(frozen=True)
class FacialIndexStatus:
    state: str
    total: int
    ready: int
    queued: int
    processing: int
    failed: int
    unindexed: int
    failures: tuple[dict[str, object], ...]
    page: int
    page_size: int
    failure_total: int


def gallery_index_status(
    db: Session,
    *,
    parent_gallery_id: UUID,
    page: int = 1,
    page_size: int = 50,
) -> FacialIndexStatus:
    if page < 1 or not 1 <= page_size <= 100:
        raise FacialStatusError("Paginação facial inválida.")
    policy = db.scalar(
        select(GalleryFacialPolicy).where(
            GalleryFacialPolicy.parent_gallery_id == parent_gallery_id
        )
    )
    photo_ids = list(
        db.scalars(
            select(PhotoAsset.id)
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
        )
    )
    latest: dict[UUID, FacialJob] = {}
    if photo_ids and policy:
        for job in db.scalars(
            select(FacialJob)
            .where(
                FacialJob.parent_gallery_id == parent_gallery_id,
                FacialJob.photo_asset_id.in_(photo_ids),
                FacialJob.kind == "index",
                FacialJob.model_version == policy.model_version,
                FacialJob.quality_version == policy.quality_version,
            )
            .order_by(FacialJob.created_at, FacialJob.id)
        ):
            assert job.photo_asset_id is not None
            latest[job.photo_asset_id] = job
    counts = {state: 0 for state in ("completed", "queued", "processing", "failed")}
    for job in latest.values():
        if job.status in counts:
            counts[job.status] += 1
    failed_jobs = sorted(
        (job for job in latest.values() if job.status == "failed"),
        key=lambda job: (job.updated_at, str(job.id)),
        reverse=True,
    )
    start = (page - 1) * page_size
    failures = tuple(
        {
            "job_id": str(job.id),
            "photo_id": str(job.photo_asset_id),
            "attempts": job.attempts,
            "error_category": job.last_error_category or "unknown",
        }
        for job in failed_jobs[start : start + page_size]
    )
    total = len(photo_ids)
    ready = counts["completed"]
    unindexed = max(0, total - len(latest))
    state = _aggregate_state(
        policy_status=policy.status if policy else "disabled",
        total=total,
        ready=ready,
        queued=counts["queued"],
        processing=counts["processing"],
        failed=counts["failed"],
        unindexed=unindexed,
    )
    return FacialIndexStatus(
        state=state,
        total=total,
        ready=ready,
        queued=counts["queued"],
        processing=counts["processing"],
        failed=counts["failed"],
        unindexed=unindexed,
        failures=failures,
        page=page,
        page_size=page_size,
        failure_total=len(failed_jobs),
    )


def retry_failed_index_jobs(
    db: Session,
    *,
    parent_gallery_id: UUID,
    job_ids: set[UUID],
) -> int:
    if not job_ids or len(job_ids) > 100:
        raise FacialStatusError("Seleção de retentativa facial inválida.")
    jobs = list(
        db.scalars(
            select(FacialJob)
            .where(
                FacialJob.id.in_(job_ids),
                FacialJob.parent_gallery_id == parent_gallery_id,
                FacialJob.kind == "index",
            )
            .with_for_update()
        )
    )
    if len(jobs) != len(job_ids):
        raise FacialStatusError("Job facial não encontrado nesta galeria.")
    changed = 0
    for job in jobs:
        if job.status != "failed":
            continue
        job.status = "queued"
        job.attempts = 0
        job.available_at = now()
        job.lease_token = None
        job.lease_expires_at = None
        job.last_error_category = None
        job.updated_at = now()
        changed += 1
    db.flush()
    return changed


def _aggregate_state(
    *,
    policy_status: str,
    total: int,
    ready: int,
    queued: int,
    processing: int,
    failed: int,
    unindexed: int,
) -> str:
    if policy_status not in {"active", "pending"}:
        return "disabled"
    if total == 0:
        return "empty"
    if ready == total:
        return "ready"
    if failed and not (ready or queued or processing or unindexed):
        return "failed"
    if ready or failed:
        return "partial"
    return "pending"
