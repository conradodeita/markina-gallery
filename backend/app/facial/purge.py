"""Purge facial prioritário sem remover mídia ou histórico comercial."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.auth import (
    AuditEvent,
    FacialJob,
    FacialSearchCandidate,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    GalleryFacialPolicy,
    PhotoAsset,
    PhotoFaceEmbedding,
    now,
)
from app.facial.jobs import FacialJobRepository
from app.facial.reference_store import delete_reference_file


@dataclass(frozen=True)
class FacialPurgeReport:
    embeddings: int
    candidates: int
    requests_cancelled: int
    notifications_cancelled: int
    jobs_cancelled: int


def facial_cleanup_proof(
    db: Session, *, parent_gallery_id: UUID
) -> dict[str, int | bool]:
    def count(model, criterion) -> int:
        return int(
            db.scalar(select(func.count()).select_from(model).where(criterion)) or 0
        )

    embeddings = count(
        PhotoFaceEmbedding,
        PhotoFaceEmbedding.parent_gallery_id == parent_gallery_id,
    )
    candidates = count(
        FacialSearchCandidate,
        FacialSearchCandidate.parent_gallery_id == parent_gallery_id,
    )
    references = count(
        FacialSearchRequest,
        (FacialSearchRequest.parent_gallery_id == parent_gallery_id)
        & (FacialSearchRequest.reference_locator_ciphertext.is_not(None)),
    )
    notifications = count(
        FacialSearchNotificationOutbox,
        (FacialSearchNotificationOutbox.parent_gallery_id == parent_gallery_id)
        & FacialSearchNotificationOutbox.status.in_(("queued", "processing")),
    )
    return {
        "clean": embeddings == candidates == references == notifications == 0,
        "embeddings": embeddings,
        "candidates": candidates,
        "references": references,
        "pending_notifications": notifications,
    }


def reconcile_invalid_facial_records(db: Session) -> FacialPurgeReport:
    """Remove inferências cuja finalidade/origem deixou de estar operacional."""

    valid_gallery_ids = select(GalleryFacialPolicy.parent_gallery_id).where(
        GalleryFacialPolicy.status == "active"
    )
    valid_photo_ids = select(PhotoAsset.id).where(PhotoAsset.available.is_(True))
    embeddings = _delete_count(
        db,
        PhotoFaceEmbedding,
        PhotoFaceEmbedding.parent_gallery_id.not_in(valid_gallery_ids),
    )
    embeddings += _delete_count(
        db,
        PhotoFaceEmbedding,
        PhotoFaceEmbedding.photo_asset_id.not_in(valid_photo_ids),
    )
    candidates = _delete_count(
        db,
        FacialSearchCandidate,
        FacialSearchCandidate.parent_gallery_id.not_in(valid_gallery_ids),
    )
    candidates += _delete_count(
        db,
        FacialSearchCandidate,
        FacialSearchCandidate.photo_asset_id.not_in(valid_photo_ids),
    )
    return FacialPurgeReport(embeddings, candidates, 0, 0, 0)


def enqueue_gallery_purge(
    db: Session,
    *,
    parent_gallery_id: UUID,
    reason: str,
    repository: FacialJobRepository | None = None,
) -> FacialJob:
    digest = hashlib.sha256(reason.encode("utf-8")).hexdigest()[:24]
    item, _created = (repository or FacialJobRepository()).enqueue(
        db,
        kind="purge",
        idempotency_key=f"facial-purge:gallery:{parent_gallery_id}:{digest}",
        parent_gallery_id=parent_gallery_id,
        priority=0,
    )
    return item


def enqueue_photo_purge(
    db: Session,
    *,
    parent_gallery_id: UUID,
    photo_asset_id: UUID,
    reason: str,
    repository: FacialJobRepository | None = None,
) -> FacialJob:
    digest = hashlib.sha256(reason.encode("utf-8")).hexdigest()[:24]
    item, _created = (repository or FacialJobRepository()).enqueue(
        db,
        kind="purge",
        idempotency_key=f"facial-purge:photo:{photo_asset_id}:{digest}",
        parent_gallery_id=parent_gallery_id,
        photo_asset_id=photo_asset_id,
        priority=0,
    )
    return item


def purge_photo_records(
    db: Session,
    *,
    parent_gallery_id: UUID,
    photo_asset_id: UUID,
    exclude_job_id: UUID | None = None,
) -> FacialPurgeReport:
    candidates = _delete_count(
        db,
        FacialSearchCandidate,
        FacialSearchCandidate.parent_gallery_id == parent_gallery_id,
        FacialSearchCandidate.photo_asset_id == photo_asset_id,
    )
    embeddings = _delete_count(
        db,
        PhotoFaceEmbedding,
        PhotoFaceEmbedding.parent_gallery_id == parent_gallery_id,
        PhotoFaceEmbedding.photo_asset_id == photo_asset_id,
    )
    jobs = _cancel_and_detach_jobs(
        db,
        FacialJob.parent_gallery_id == parent_gallery_id,
        FacialJob.photo_asset_id == photo_asset_id,
        exclude_job_id=exclude_job_id,
    )
    db.add(
        AuditEvent(
            event="facial.photo_purged",
            subject=(
                f"gallery_id:{parent_gallery_id};photo_id:{photo_asset_id};"
                f"embeddings:{embeddings};candidates:{candidates}"
            ),
        )
    )
    return FacialPurgeReport(embeddings, candidates, 0, 0, jobs)


def purge_gallery_records(
    db: Session,
    *,
    parent_gallery_id: UUID,
    exclude_job_id: UUID | None = None,
    reference_root: Path | None = None,
) -> FacialPurgeReport:
    instant = now()
    notification_result = db.execute(
        update(FacialSearchNotificationOutbox)
        .where(
            FacialSearchNotificationOutbox.parent_gallery_id == parent_gallery_id,
            FacialSearchNotificationOutbox.status.in_(("queued", "processing")),
        )
        .values(
            status="cancelled",
            payload_ciphertext=b"",
            payload_nonce=b"",
            last_error_category="purpose_revoked",
            updated_at=instant,
        )
        .execution_options(synchronize_session=False)
    )
    notifications = notification_result.rowcount or 0
    candidates = _delete_count(
        db,
        FacialSearchCandidate,
        FacialSearchCandidate.parent_gallery_id == parent_gallery_id,
    )
    embeddings = _delete_count(
        db,
        PhotoFaceEmbedding,
        PhotoFaceEmbedding.parent_gallery_id == parent_gallery_id,
    )
    requests_with_reference = list(
        db.scalars(
            select(FacialSearchRequest).where(
                FacialSearchRequest.parent_gallery_id == parent_gallery_id,
                FacialSearchRequest.reference_locator_ciphertext.is_not(None),
            )
        )
    )
    root = reference_root or Path(
        os.getenv("FACIAL_REFERENCE_ROOT", "./media/facial-references")
    )
    for request in requests_with_reference:
        delete_reference_file(root, request.id)
    request_result = db.execute(
        update(FacialSearchRequest)
        .where(
            FacialSearchRequest.parent_gallery_id == parent_gallery_id,
            FacialSearchRequest.status.not_in(("cancelled", "expired")),
        )
        .values(
            status="cancelled",
            reference_locator_ciphertext=None,
            reference_locator_nonce=None,
            reference_key_id=None,
            reference_deleted_at=instant,
            completed_at=instant,
            updated_at=instant,
        )
        .execution_options(synchronize_session=False)
    )
    requests = request_result.rowcount or 0
    jobs = _cancel_and_detach_jobs(
        db,
        FacialJob.parent_gallery_id == parent_gallery_id,
        exclude_job_id=exclude_job_id,
    )
    db.add(
        AuditEvent(
            event="facial.gallery_purged",
            subject=(
                f"gallery_id:{parent_gallery_id};embeddings:{embeddings};"
                f"candidates:{candidates};requests:{requests}"
            ),
        )
    )
    return FacialPurgeReport(embeddings, candidates, requests, notifications, jobs)


def _cancel_and_detach_jobs(
    db: Session, *criteria, exclude_job_id: UUID | None = None
) -> int:
    all_criteria = list(criteria)
    if exclude_job_id is not None:
        all_criteria.append(FacialJob.id != exclude_job_id)
    result = db.execute(
        update(FacialJob)
        .where(*all_criteria, FacialJob.status.in_(("queued", "processing")))
        .values(
            status="cancelled",
            lease_token=None,
            lease_expires_at=None,
            last_error_category="purpose_revoked",
            updated_at=now(),
        )
        .execution_options(synchronize_session=False)
    )
    changed = result.rowcount or 0
    db.execute(
        update(FacialJob)
        .where(*all_criteria)
        .values(photo_asset_id=None)
        .execution_options(synchronize_session=False)
    )
    return changed


def _delete_count(db: Session, model, *criteria) -> int:
    result = db.execute(
        delete(model).where(*criteria).execution_options(synchronize_session=False)
    )
    return result.rowcount or 0
