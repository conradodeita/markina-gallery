"""Purge facial prioritário sem remover mídia ou histórico comercial."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    AuditEvent,
    FacialJob,
    FacialSearchCandidate,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    GalleryFacialPolicy,
    MediaJob,
    ParentGallery,
    PhotoAnalysis,
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


def invalidate_gallery_searches(
    db: Session,
    *,
    parent_gallery_id: UUID,
    tenant_id: UUID,
) -> FacialPurgeReport:
    """Invalida resultados e jobs de busca antes do purge físico assíncrono."""

    if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
        raise ValueError("Galeria indisponível.")
    instant = now()
    notification_result = db.execute(
        update(FacialSearchNotificationOutbox)
        .where(
            FacialSearchNotificationOutbox.tenant_id == tenant_id, FacialSearchNotificationOutbox.parent_gallery_id == parent_gallery_id,
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
    candidate_result = db.execute(
        delete(FacialSearchCandidate)
        .where(FacialSearchCandidate.tenant_id == tenant_id, FacialSearchCandidate.parent_gallery_id == parent_gallery_id)
        .execution_options(synchronize_session=False)
    )
    request_result = db.execute(
        update(FacialSearchRequest)
        .where(
            FacialSearchRequest.tenant_id == tenant_id, FacialSearchRequest.parent_gallery_id == parent_gallery_id,
            FacialSearchRequest.status.not_in(("cancelled", "expired")),
        )
        .values(
            status="cancelled",
            completed_at=instant,
            updated_at=instant,
        )
        .execution_options(synchronize_session=False)
    )
    job_result = db.execute(
        update(FacialJob)
        .where(
            FacialJob.tenant_id == tenant_id, FacialJob.parent_gallery_id == parent_gallery_id,
            FacialJob.kind == "search",
            FacialJob.status.in_(("queued", "processing")),
        )
        .values(
            status="cancelled",
            lease_token=None,
            lease_expires_at=None,
            last_error_category="purpose_revoked",
            updated_at=instant,
        )
        .execution_options(synchronize_session=False)
    )
    report = FacialPurgeReport(
        embeddings=0,
        candidates=candidate_result.rowcount or 0,
        requests_cancelled=request_result.rowcount or 0,
        notifications_cancelled=notification_result.rowcount or 0,
        jobs_cancelled=job_result.rowcount or 0,
    )
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            event="facial.search_scope_invalidated",
            subject=(
                f"gallery_id:{parent_gallery_id};candidates:{report.candidates};"
                f"requests:{report.requests_cancelled};jobs:{report.jobs_cancelled}"
            ),
        )
    )
    return report


def facial_cleanup_proof(
    db: Session, *, parent_gallery_id: UUID, tenant_id: UUID
) -> dict[str, int | bool]:
    if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
        raise ValueError("Galeria indisponível.")
    def count(model, criterion) -> int:
        return int(
            db.scalar(select(func.count()).select_from(model).where(model.tenant_id == tenant_id, criterion)) or 0
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
        & ((FacialSearchRequest.reference_locator_ciphertext.is_not(None))
           | (FacialSearchRequest.reference_region_id.is_not(None))),
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


def reconcile_invalid_facial_records(db: Session, *, tenant_id: UUID) -> FacialPurgeReport:
    """Remove inferências cuja finalidade/origem deixou de estar operacional."""

    require_active_owner(db, tenant_id)
    valid_gallery_ids = select(GalleryFacialPolicy.parent_gallery_id).where(
        GalleryFacialPolicy.tenant_id == tenant_id, GalleryFacialPolicy.status == "active"
    )
    valid_photo_ids = select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id, PhotoAsset.available.is_(True))
    valid_index_photo_ids = select(PhotoAsset.id).where(
        PhotoAsset.tenant_id == tenant_id, PhotoAsset.available.is_(True) | select(PhotoAnalysis.photo_asset_id).where(
            PhotoAnalysis.tenant_id == tenant_id, PhotoAsset.tenant_id == tenant_id, PhotoAnalysis.photo_asset_id == PhotoAsset.id,
            PhotoAnalysis.state.in_(("pending", "ready")),
            PhotoAnalysis.deleted_at.is_(None), PhotoAnalysis.expires_at > now(),
            select(MediaJob.id).where(MediaJob.tenant_id == tenant_id, PhotoAsset.tenant_id == tenant_id, MediaJob.photo_asset_id == PhotoAsset.id,
                MediaJob.status.in_(("queued", "processing"))).correlate(PhotoAsset).exists(),
        ).exists())
    embeddings = _delete_count(
        db,
        PhotoFaceEmbedding,
        PhotoFaceEmbedding.parent_gallery_id.not_in(valid_gallery_ids),
     tenant_id=tenant_id)
    embeddings += _delete_count(
        db,
        PhotoFaceEmbedding,
        PhotoFaceEmbedding.photo_asset_id.not_in(valid_index_photo_ids),
     tenant_id=tenant_id)
    candidates = _delete_count(
        db,
        FacialSearchCandidate,
        FacialSearchCandidate.parent_gallery_id.not_in(valid_gallery_ids),
     tenant_id=tenant_id)
    candidates += _delete_count(
        db,
        FacialSearchCandidate,
        FacialSearchCandidate.photo_asset_id.not_in(valid_photo_ids),
     tenant_id=tenant_id)
    return FacialPurgeReport(embeddings, candidates, 0, 0, 0)


def enqueue_gallery_purge(
    db: Session,
    *,
    parent_gallery_id: UUID,
    tenant_id: UUID,
    reason: str,
    repository: FacialJobRepository | None = None,
) -> FacialJob:
    digest = hashlib.sha256(reason.encode("utf-8")).hexdigest()[:24]
    item, _created = (repository or FacialJobRepository()).enqueue(
        db,
        kind="purge",
        tenant_id=tenant_id,
        idempotency_key=f"facial-purge:gallery:{parent_gallery_id}:{digest}",
        parent_gallery_id=parent_gallery_id,
        priority=0,
    )
    return item


def enqueue_photo_purge(
    db: Session,
    *,
    parent_gallery_id: UUID,
    tenant_id: UUID,
    photo_asset_id: UUID,
    reason: str,
    repository: FacialJobRepository | None = None,
) -> FacialJob:
    digest = hashlib.sha256(reason.encode("utf-8")).hexdigest()[:24]
    item, _created = (repository or FacialJobRepository()).enqueue(
        db,
        kind="purge",
        tenant_id=tenant_id,
        idempotency_key=f"facial-purge:photo:{photo_asset_id}:{digest}",
        parent_gallery_id=parent_gallery_id,
        photo_asset_id=photo_asset_id,
        priority=0,
    )
    return item


def purge_photo_records(
    db: Session,
    *,
    tenant_id: UUID,
    parent_gallery_id: UUID,
    photo_asset_id: UUID,
    exclude_job_id: UUID | None = None,
) -> FacialPurgeReport:
    parent = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
    if not parent:
        raise ValueError("Galeria indisponível.")
    photo = owned_record(db, PhotoAsset, photo_asset_id, tenant_id=tenant_id)
    if photo is not None and photo.parent_gallery_id != parent.id:
        raise ValueError("Foto indisponível.")
    db.execute(update(FacialSearchRequest).where(
        FacialSearchRequest.tenant_id == tenant_id, FacialSearchRequest.parent_gallery_id == parent_gallery_id,
        FacialSearchRequest.reference_region_id.in_(select(PhotoFaceEmbedding.id).where(
            PhotoFaceEmbedding.tenant_id == tenant_id, PhotoFaceEmbedding.photo_asset_id == photo_asset_id,
            PhotoFaceEmbedding.parent_gallery_id == parent_gallery_id)),
    ).values(reference_region_id=None, status="cancelled", completed_at=now()))
    candidates = _delete_count(
        db,
        FacialSearchCandidate,
        FacialSearchCandidate.parent_gallery_id == parent_gallery_id,
        FacialSearchCandidate.photo_asset_id == photo_asset_id,
     tenant_id=tenant_id)
    embeddings = _delete_count(
        db,
        PhotoFaceEmbedding,
        PhotoFaceEmbedding.parent_gallery_id == parent_gallery_id,
        PhotoFaceEmbedding.photo_asset_id == photo_asset_id,
     tenant_id=tenant_id)
    jobs = _cancel_and_detach_jobs(
        db,
        FacialJob.parent_gallery_id == parent_gallery_id,
        FacialJob.photo_asset_id == photo_asset_id,
        exclude_job_id=exclude_job_id,
     tenant_id=tenant_id)
    db.add(
        AuditEvent(
            event="facial.photo_purged",
            tenant_id=tenant_id,
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
    tenant_id: UUID,
    exclude_job_id: UUID | None = None,
    reference_root: Path | None = None,
) -> FacialPurgeReport:
    if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
        raise ValueError("Galeria indisponível.")
    instant = now()
    notification_result = db.execute(
        update(FacialSearchNotificationOutbox)
        .where(
            FacialSearchNotificationOutbox.tenant_id == tenant_id,
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
        FacialSearchCandidate.tenant_id == tenant_id,
        FacialSearchCandidate.parent_gallery_id == parent_gallery_id,
     tenant_id=tenant_id)
    embeddings = _delete_count(
        db,
        PhotoFaceEmbedding,
        PhotoFaceEmbedding.tenant_id == tenant_id,
        PhotoFaceEmbedding.parent_gallery_id == parent_gallery_id,
     tenant_id=tenant_id)
    requests_with_reference = list(
        db.scalars(
            select(FacialSearchRequest).where(
                FacialSearchRequest.tenant_id == tenant_id,
            FacialSearchRequest.parent_gallery_id == parent_gallery_id,
                FacialSearchRequest.reference_locator_ciphertext.is_not(None),
            )
        )
    )
    root = reference_root or Path(
        os.getenv("FACIAL_REFERENCE_ROOT", "./media/facial-references")
    )
    for request in requests_with_reference:
        require_active_owner(db, tenant_id)
        delete_reference_file(root, request.id)
    request_result = db.execute(
        update(FacialSearchRequest)
        .where(
            FacialSearchRequest.tenant_id == tenant_id,
            FacialSearchRequest.parent_gallery_id == parent_gallery_id,
            FacialSearchRequest.status.not_in(("cancelled", "expired")),
        )
        .values(
            status="cancelled",
            completed_at=instant,
            updated_at=instant,
        )
        .execution_options(synchronize_session=False)
    )
    requests = request_result.rowcount or 0
    db.execute(update(FacialSearchRequest).where(
        FacialSearchRequest.tenant_id == tenant_id,
            FacialSearchRequest.parent_gallery_id == parent_gallery_id
    ).values(reference_region_id=None))
    db.execute(
        update(FacialSearchRequest)
        .where(
            FacialSearchRequest.tenant_id == tenant_id,
            FacialSearchRequest.parent_gallery_id == parent_gallery_id,
            FacialSearchRequest.reference_locator_ciphertext.is_not(None),
        )
        .values(
            reference_locator_ciphertext=None,
            reference_locator_nonce=None,
            reference_key_id=None,
            reference_deleted_at=instant,
            updated_at=instant,
        )
        .execution_options(synchronize_session=False)
    )
    jobs = _cancel_and_detach_jobs(
        db,
        FacialJob.tenant_id == tenant_id,
        FacialJob.parent_gallery_id == parent_gallery_id,
        exclude_job_id=exclude_job_id,
     tenant_id=tenant_id)
    db.add(
        AuditEvent(
            event="facial.gallery_purged",
            tenant_id=tenant_id,
            subject=(
                f"gallery_id:{parent_gallery_id};embeddings:{embeddings};"
                f"candidates:{candidates};requests:{requests}"
            ),
        )
    )
    return FacialPurgeReport(embeddings, candidates, requests, notifications, jobs)


def _cancel_and_detach_jobs(
    db: Session, *criteria, tenant_id: UUID, exclude_job_id: UUID | None = None
) -> int:
    require_active_owner(db, tenant_id)
    all_criteria = [*criteria]
    if exclude_job_id is not None:
        all_criteria.append(FacialJob.id != exclude_job_id)
    result = db.execute(
        update(FacialJob)
        .where(FacialJob.tenant_id == tenant_id, *all_criteria, FacialJob.status.in_(("queued", "processing")))
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
    db.execute(update(PhotoAnalysis).where(
        PhotoAnalysis.tenant_id == tenant_id, PhotoAnalysis.photo_asset_id.in_(select(FacialJob.photo_asset_id).where(*all_criteria)),
        PhotoAnalysis.state.in_(("pending", "receiving")),
    ).values(state="failed"))
    db.execute(
        update(FacialJob)
        .where(*all_criteria)
        .values(photo_asset_id=None)
        .execution_options(synchronize_session=False)
    )
    return changed


def _delete_count(db: Session, model, *criteria, tenant_id) -> int:
    result = db.execute(
        delete(model).where(model.tenant_id == tenant_id, *criteria).execution_options(synchronize_session=False)
    )
    return result.rowcount or 0
