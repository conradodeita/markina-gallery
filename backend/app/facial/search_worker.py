"""Processamento durável de consultas faciais sobre um snapshot congelado."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import (
    AuditEvent,
    FacialJob,
    FacialSearchCandidate,
    FacialSearchRequest,
    FacialSearchSnapshotItem,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    expired,
    now,
)
from app.facial.config import FacialSettings
from app.facial.crypto import FacialCipher, FacialEnvelope
from app.facial.engine import search_gallery_index
from app.facial.jobs import ClaimedFacialJob, FacialJobError, FacialJobRepository
from app.facial.notifications import enqueue_search_notification
from app.facial.provider import OpenCvSFaceProvider, analyze_query
from app.facial.reference_store import FacialReferenceError, FacialReferenceStore

_TERMINAL_STATES = {
    "ready",
    "no_face",
    "multiple_faces",
    "low_quality",
    "index_incomplete",
    "no_candidates",
    "cancelled",
    "expired",
    "failed",
}


def process_claimed_search_job(
    db: Session,
    claim: ClaimedFacialJob,
    *,
    repository: FacialJobRepository,
    provider: OpenCvSFaceProvider,
    cipher: FacialCipher,
    settings: FacialSettings,
    reference_store: FacialReferenceStore | None = None,
    retry_delay_seconds: int = 5,
    max_attempts: int = 3,
) -> FacialJob:
    """Executa ou retoma a consulta sem depender da presença da cliente na UI."""

    job = db.get(FacialJob, claim.id)
    if job is None or job.kind != "search" or job.search_request_id is None:
        raise FacialJobError("Job facial não pode ser executado.")
    request = db.get(FacialSearchRequest, job.search_request_id)
    if request is None or request.parent_gallery_id != job.parent_gallery_id:
        raise FacialJobError("Consulta facial não pode ser executada.")
    store = reference_store or FacialReferenceStore(
        settings.reference_root,
        cipher,
        max_bytes=settings.max_reference_bytes,
        max_pixels=settings.max_reference_pixels,
    )
    try:
        if request.status in _TERMINAL_STATES:
            _delete_reference(request, store)
            db.commit()
            return repository.complete(db, claim)
        if not _request_is_authorized(db, request, settings):
            _finish_request(
                db,
                request,
                status="cancelled",
                store=store,
                cipher=cipher,
                settings=settings,
            )
            return repository.complete(db, claim)
        pending = _refresh_snapshot(db, request)
        repository.progress(
            db,
            claim,
            done=request.snapshot_ready,
            total=request.snapshot_total,
            lease_seconds=settings.job_lease_seconds,
        )
        if pending:
            if expired(request.expires_at):
                _finish_request(
                    db,
                    request,
                    status="index_incomplete",
                    store=store,
                    cipher=cipher,
                    settings=settings,
                )
                return repository.complete(db, claim)
            request.status = "waiting_index"
            db.commit()
            return repository.defer(
                db, claim, delay_seconds=max(0, retry_delay_seconds)
            )
        if expired(request.expires_at):
            _finish_request(
                db,
                request,
                status="expired",
                store=store,
                cipher=cipher,
                settings=settings,
            )
            return repository.complete(db, claim)

        request.status = "validating_reference"
        db.commit()
        payload = store.load(
            request_id=request.id,
            gallery_id=request.parent_gallery_id,
            model_version=request.model_version,
            data_version=request.consent_version,
            locator=_reference_locator(request),
        )
        analysis = analyze_query(provider.observe_bytes(payload))
        if analysis.status != "ready" or analysis.observation is None:
            _finish_request(
                db,
                request,
                status=analysis.status,
                store=store,
                cipher=cipher,
                settings=settings,
            )
            return repository.complete(db, claim)

        request.status = "searching"
        db.commit()
        fingerprints = {
            item.photo_asset_id: item.preview_fingerprint
            for item in _snapshot_items(db, request.id)
            if item.status == "ready" and item.preview_fingerprint is not None
        }
        matches = search_gallery_index(
            db,
            gallery_id=request.parent_gallery_id,
            query_embedding=analysis.observation.embedding,
            cipher=cipher,
            settings=settings,
            threshold_milli=settings.similarity_threshold_milli,
            allowed_fingerprints=fingerprints,
        )
        request.compare_done = request.compare_total
        request.status = "ranking"
        db.commit()

        db.execute(
            delete(FacialSearchCandidate).where(
                FacialSearchCandidate.search_request_id == request.id
            )
        )
        candidate_expiry = now() + timedelta(
            seconds=settings.candidate_retention_seconds
        )
        db.add_all(
            FacialSearchCandidate(
                search_request_id=request.id,
                parent_gallery_id=request.parent_gallery_id,
                client_id=request.client_id,
                photo_asset_id=match.photo_id,
                rank=rank,
                quality_band=match.quality_band,
                expires_at=candidate_expiry,
            )
            for rank, match in enumerate(matches, start=1)
        )
        if matches:
            repository.enqueue(
                db,
                kind="cleanup",
                idempotency_key=f"facial-search-candidate-cleanup:{request.id}",
                parent_gallery_id=request.parent_gallery_id,
                search_request_id=request.id,
                priority=20,
                available_at=candidate_expiry,
            )
        _finish_request(
            db,
            request,
            status="ready" if matches else "no_candidates",
            store=store,
            cipher=cipher,
            settings=settings,
        )
        repository.progress(
            db,
            claim,
            done=request.compare_done,
            total=request.compare_total,
            lease_seconds=settings.job_lease_seconds,
        )
        return repository.complete(db, claim)
    except FacialJobError:
        raise
    # A fronteira do worker transforma qualquer falha inesperada em categoria
    # sanitizada; detalhes nunca são persistidos nem devolvidos à cliente.
    except Exception as error:  # noqa: BLE001
        db.rollback()
        failed_job = repository.fail(
            db,
            claim,
            error,
            max_attempts=max_attempts,
            retry_delay_seconds=retry_delay_seconds,
        )
        request = db.get(FacialSearchRequest, job.search_request_id)
        if request is not None:
            if failed_job.status == "failed":
                _finish_request(
                    db,
                    request,
                    status="failed",
                    store=store,
                    cipher=cipher,
                    settings=settings,
                )
            else:
                request.status = "queued"
                db.commit()
        return failed_job


def _request_is_authorized(
    db: Session, request: FacialSearchRequest, settings: FacialSettings
) -> bool:
    gallery = db.get(ParentGallery, request.parent_gallery_id)
    registration = db.scalar(
        select(ParentGalleryRegistration.id).where(
            ParentGalleryRegistration.parent_gallery_id == request.parent_gallery_id,
            ParentGalleryRegistration.client_id == request.client_id,
            ParentGalleryRegistration.status == "active",
        )
    )
    policy = db.get(GalleryFacialPolicy, request.policy_id)
    return bool(
        gallery
        and gallery.active
        and gallery.lifecycle_status == "active"
        and registration
        and policy
        and policy.parent_gallery_id == request.parent_gallery_id
        and policy.status == "active"
        and settings.enabled
        and request.model_version == settings.model_version == policy.model_version
        and request.quality_version
        == settings.quality_version
        == policy.quality_version
        and request.index_generation == policy.index_generation
    )


def _refresh_snapshot(db: Session, request: FacialSearchRequest) -> bool:
    items = _snapshot_items(db, request.id)
    pending_items = [item for item in items if item.status == "pending"]
    if pending_items:
        photo_ids = [item.photo_asset_id for item in pending_items]
        eligible = set(
            db.scalars(
                select(PhotoAsset.id)
                .join(
                    MediaDerivative,
                    MediaDerivative.photo_asset_id == PhotoAsset.id,
                )
                .where(
                    PhotoAsset.id.in_(photo_ids),
                    PhotoAsset.parent_gallery_id == request.parent_gallery_id,
                    PhotoAsset.available.is_(True),
                    MediaDerivative.variant == "client_preview",
                    MediaDerivative.status == "ready",
                )
            )
        )
        completed_by_photo: dict[UUID, FacialJob] = {}
        completed_jobs = db.scalars(
            select(FacialJob)
            .where(
                FacialJob.kind == "index",
                FacialJob.status == "completed",
                FacialJob.parent_gallery_id == request.parent_gallery_id,
                FacialJob.photo_asset_id.in_(photo_ids),
                FacialJob.model_version == request.model_version,
                FacialJob.quality_version == request.quality_version,
            )
            .order_by(FacialJob.created_at.desc(), FacialJob.id.desc())
        )
        for completed in completed_jobs:
            completed_by_photo.setdefault(completed.photo_asset_id, completed)
        for item in pending_items:
            if item.photo_asset_id not in eligible:
                item.status = "excluded"
                continue
            completed = completed_by_photo.get(item.photo_asset_id)
            if completed is not None and completed.preview_fingerprint:
                item.status = "ready"
                item.preview_fingerprint = completed.preview_fingerprint

    request.snapshot_ready = sum(item.status == "ready" for item in items)
    request.compare_total = request.snapshot_ready
    request.updated_at = now()
    db.commit()
    return any(item.status == "pending" for item in items)


def _snapshot_items(
    db: Session, request_id: UUID
) -> list[FacialSearchSnapshotItem]:
    return list(
        db.scalars(
            select(FacialSearchSnapshotItem)
            .where(FacialSearchSnapshotItem.search_request_id == request_id)
            .order_by(FacialSearchSnapshotItem.created_at, FacialSearchSnapshotItem.id)
        )
    )


def _reference_locator(request: FacialSearchRequest) -> FacialEnvelope:
    if not all(
        (
            request.reference_locator_ciphertext,
            request.reference_locator_nonce,
            request.reference_key_id,
        )
    ):
        raise FacialReferenceError("Referência facial não está disponível.")
    return FacialEnvelope(
        ciphertext=request.reference_locator_ciphertext,
        nonce=request.reference_locator_nonce,
        key_id=request.reference_key_id,
    )


def _delete_reference(
    request: FacialSearchRequest, store: FacialReferenceStore
) -> None:
    if request.reference_deleted_at is not None:
        return
    locator = _reference_locator(request)
    store.delete(
        request_id=request.id,
        gallery_id=request.parent_gallery_id,
        model_version=request.model_version,
        data_version=request.consent_version,
        locator=locator,
    )
    request.reference_locator_ciphertext = None
    request.reference_locator_nonce = None
    request.reference_key_id = None
    request.reference_deleted_at = now()


def _finish_request(
    db: Session,
    request: FacialSearchRequest,
    *,
    status: str,
    store: FacialReferenceStore,
    cipher: FacialCipher,
    settings: FacialSettings,
) -> None:
    _delete_reference(request, store)
    request.status = status
    request.completed_at = now()
    request.updated_at = now()
    db.add(
        AuditEvent(
            event="facial.search_completed",
            subject=(
                f"gallery_id:{request.parent_gallery_id};client_id:{request.client_id};"
                f"request_id:{request.id};result:{status}"
            ),
        )
    )
    enqueue_search_notification(
        db,
        request=request,
        result_status=status,
        cipher=cipher,
        settings=settings,
    )
    db.commit()
