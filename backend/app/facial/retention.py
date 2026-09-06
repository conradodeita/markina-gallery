"""Retenção física de referências temporárias e candidatas faciais."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.auth import (
    AuditEvent,
    FacialJob,
    FacialSearchCandidate,
    FacialSearchRequest,
    FacialSearchSnapshotItem,
    now,
)
from app.facial.config import FacialSettings
from app.facial.crypto import FacialCipher, FacialEnvelope
from app.facial.jobs import ClaimedFacialJob, FacialJobError, FacialJobRepository
from app.facial.reference_store import FacialReferenceError, FacialReferenceStore


def process_claimed_cleanup_job(
    db: Session,
    claim: ClaimedFacialJob,
    *,
    repository: FacialJobRepository,
    settings: FacialSettings,
    reference_store: FacialReferenceStore | None = None,
    instant: datetime | None = None,
) -> FacialJob:
    job = db.get(FacialJob, claim.id)
    if job is None or job.kind != "cleanup" or job.search_request_id is None:
        raise FacialJobError("Job facial não pode ser executado.")
    request = db.get(FacialSearchRequest, job.search_request_id)
    if request is None:
        return repository.complete(db, claim)
    current = _utc(instant or now())
    store = reference_store or FacialReferenceStore(
        settings.reference_root,
        FacialCipher(active_key_id=settings.active_key_id, keys=settings.aead_keys),
        max_bytes=settings.max_reference_bytes,
        max_pixels=settings.max_reference_pixels,
    )
    removed = 0
    if request.reference_deleted_at is None and _utc(request.expires_at) <= current:
        _delete_reference(request, store)
        removed += 1
        if request.status not in {
            "ready",
            "no_face",
            "multiple_faces",
            "low_quality",
            "no_candidates",
            "cancelled",
            "expired",
            "failed",
        }:
            pending = db.scalar(
                select(func.count())
                .select_from(FacialSearchSnapshotItem)
                .where(
                    FacialSearchSnapshotItem.search_request_id == request.id,
                    FacialSearchSnapshotItem.status == "pending",
                )
            )
            request.status = "index_incomplete" if pending else "expired"
            request.completed_at = current
            db.execute(
                update(FacialJob)
                .where(
                    FacialJob.search_request_id == request.id,
                    FacialJob.kind == "search",
                    FacialJob.status.in_(("queued", "processing")),
                )
                .values(status="cancelled", lease_token=None, lease_expires_at=None)
            )

    candidate_result = db.execute(
        delete(FacialSearchCandidate).where(
            FacialSearchCandidate.search_request_id == request.id,
            FacialSearchCandidate.expires_at <= current,
        )
    )
    removed += max(candidate_result.rowcount or 0, 0)
    if removed:
        db.add(
            AuditEvent(
                event="facial.retention_cleaned",
                subject=(
                    f"gallery_id:{request.parent_gallery_id};request_id:{request.id};"
                    f"records:{removed}"
                ),
            )
        )
    db.commit()

    next_expiry = (
        db.scalar(
            select(func.min(FacialSearchCandidate.expires_at)).where(
                FacialSearchCandidate.search_request_id == request.id
            )
        )
        if job.idempotency_key.startswith("facial-search-candidate-cleanup:")
        else None
    )
    if request.reference_deleted_at is None:
        next_expiry = min(
            _utc(request.expires_at),
            _utc(next_expiry) if next_expiry else _utc(request.expires_at),
        )
    if next_expiry and _utc(next_expiry) > current:
        delay = max(1, int((_utc(next_expiry) - current).total_seconds()))
        return repository.defer(db, claim, delay_seconds=delay)
    repository.progress(
        db,
        claim,
        done=removed,
        total=removed,
        lease_seconds=settings.job_lease_seconds,
    )
    return repository.complete(db, claim)


def _delete_reference(
    request: FacialSearchRequest, store: FacialReferenceStore
) -> None:
    if not all(
        (
            request.reference_locator_ciphertext,
            request.reference_locator_nonce,
            request.reference_key_id,
        )
    ):
        raise FacialReferenceError("Referência facial não está disponível.")
    store.delete(
        request_id=request.id,
        gallery_id=request.parent_gallery_id,
        model_version=request.model_version,
        data_version=request.consent_version,
        locator=FacialEnvelope(
            ciphertext=request.reference_locator_ciphertext,
            nonce=request.reference_locator_nonce,
            key_id=request.reference_key_id,
        ),
    )
    request.reference_locator_ciphertext = None
    request.reference_locator_nonce = None
    request.reference_key_id = None
    request.reference_deleted_at = now()


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)
