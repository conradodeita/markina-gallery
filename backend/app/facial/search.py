"""Disponibilidade e criação segura de consultas faciais da cliente."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.auth import (
    AuditEvent,
    FacialJob,
    FacialSearchCandidate,
    FacialSearchRequest,
    FacialSearchSnapshotItem,
    MediaDerivative,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    expired,
    now,
)
from app.facial.capacity import require_search_capacity
from app.facial.config import FacialSettings
from app.facial.crypto import FacialCipher, FacialEnvelope
from app.facial.jobs import FacialJobRepository
from app.facial.notifications import cancel_pending_search_notifications
from app.facial.policy import activation_inventory, read_policy
from app.facial.reference_store import FacialReferenceStore
from app.facial.representation import (
    FacialLegalRepresentationError,
    find_valid_legal_representation,
    require_valid_legal_representation,
)
from app.facial.rollout import rollout_is_active
from app.facial.status import gallery_index_status


class FacialSearchError(RuntimeError):
    """Consulta facial não pode ser criada sem revelar o recurso protegido."""


_TERMINAL_SEARCH_STATES = frozenset(
    {
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
)
_POLL_AFTER_MS = {
    "queued": 2000,
    "waiting_index": 5000,
    "validating_reference": 1500,
    "searching": 1500,
    "ranking": 1000,
}


def search_availability(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    settings: FacialSettings,
) -> dict[str, object]:
    policy = read_policy(db, parent_gallery_id)
    if (
        not rollout_is_active(
            db,
            settings=settings,
            parent_gallery_id=parent_gallery_id,
        )
        or policy is None
        or policy.status != "active"
        or activation_inventory(policy, settings)
    ):
        return {
            "state": "unavailable",
            "manual_selection_available": True,
            "minor_search_available": False,
            "max_reference_bytes": settings.max_reference_bytes,
        }
    index = gallery_index_status(
        db,
        parent_gallery_id=parent_gallery_id,
        processing_enabled=settings.enabled,
    )
    minor_representation = find_valid_legal_representation(
        db,
        client_id=client_id,
        parent_gallery_id=parent_gallery_id,
        terms_version=settings.minor_policy_version,
    )
    return {
        "state": "consent_required",
        "manual_selection_available": True,
        "minor_search_available": minor_representation is not None,
        "minor_representation_reference": (
            str(minor_representation.id) if minor_representation else None
        ),
        "consent_version": settings.consent_version,
        "legal_notice_version": policy.legal_notice_version,
        "reference_retention_seconds": settings.reference_retention_seconds,
        "candidate_retention_seconds": settings.candidate_retention_seconds,
        "max_reference_bytes": settings.max_reference_bytes,
        "index": {
            "state": index.state,
            "ready": index.ready,
            "total": index.total,
        },
    }


def create_search_request(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    consent_version: str,
    subject_declaration: str,
    representation_reference: str | None,
    payload: bytes,
    settings: FacialSettings,
    reference_store: FacialReferenceStore | None = None,
    repository: FacialJobRepository | None = None,
) -> FacialSearchRequest:
    policy = read_policy(db, parent_gallery_id)
    if (
        not rollout_is_active(
            db,
            settings=settings,
            parent_gallery_id=parent_gallery_id,
        )
        or policy is None
        or policy.status != "active"
        or activation_inventory(policy, settings)
    ):
        raise FacialSearchError("Busca facial indisponível.")
    if consent_version != settings.consent_version:
        raise FacialSearchError("O consentimento facial precisa ser revisto.")
    if subject_declaration not in {"adult", "minor"}:
        raise FacialSearchError("Declaração do sujeito inválida.")
    if subject_declaration == "minor":
        try:
            representation = require_valid_legal_representation(
                db,
                representation_reference=representation_reference,
                client_id=client_id,
                parent_gallery_id=parent_gallery_id,
                terms_version=settings.minor_policy_version,
            )
        except FacialLegalRepresentationError as exc:
            raise FacialSearchError(
                "A representação legal vigente é obrigatória para esta busca."
            ) from exc
        representation_reference = str(representation.id)
    elif representation_reference:
        raise FacialSearchError("Representação não é aplicável a uma consulta adulta.")
    require_search_capacity(db, settings)

    request_id = uuid4()
    snapshot = _build_snapshot(
        db,
        request_id=request_id,
        parent_gallery_id=parent_gallery_id,
        client_id=client_id,
        model_version=policy.model_version,
        quality_version=policy.quality_version,
    )
    snapshot_ready = sum(item.status == "ready" for item in snapshot)
    snapshot_pending = any(item.status == "pending" for item in snapshot)
    item = FacialSearchRequest(
        id=request_id,
        parent_gallery_id=parent_gallery_id,
        client_id=client_id,
        policy_id=policy.id,
        status="waiting_index" if snapshot_pending else "queued",
        consent_version=consent_version,
        legal_notice_version=policy.legal_notice_version or "",
        subject_declaration=subject_declaration,
        representation_reference=representation_reference,
        model_version=policy.model_version,
        quality_version=policy.quality_version,
        index_generation=policy.index_generation,
        snapshot_total=len(snapshot),
        snapshot_ready=snapshot_ready,
        compare_total=snapshot_ready,
        compare_done=0,
        expires_at=now() + timedelta(seconds=settings.reference_retention_seconds),
    )
    cipher = FacialCipher(
        active_key_id=settings.active_key_id, keys=settings.aead_keys
    )
    store = reference_store or FacialReferenceStore(
        settings.reference_root,
        cipher,
        max_bytes=settings.max_reference_bytes,
        max_pixels=settings.max_reference_pixels,
    )
    stored = store.store(
        request_id=item.id,
        gallery_id=parent_gallery_id,
        model_version=item.model_version,
        data_version=item.consent_version,
        payload=payload,
    )
    item.reference_locator_ciphertext = stored.locator.ciphertext
    item.reference_locator_nonce = stored.locator.nonce
    item.reference_key_id = stored.locator.key_id
    try:
        _retire_prior_searches(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=client_id,
            store=store,
        )
        db.add(item)
        db.add_all(snapshot)
        db.flush()
        job_repository = repository or FacialJobRepository()
        job_repository.enqueue(
            db,
            kind="search",
            idempotency_key=f"facial-search:{item.id}",
            parent_gallery_id=parent_gallery_id,
            search_request_id=item.id,
            model_version=item.model_version,
            quality_version=item.quality_version,
        )
        job_repository.enqueue(
            db,
            kind="cleanup",
            idempotency_key=f"facial-search-reference-cleanup:{item.id}",
            parent_gallery_id=parent_gallery_id,
            search_request_id=item.id,
            priority=20,
            available_at=item.expires_at,
        )
        db.add(
            AuditEvent(
                event="facial.search_consented",
                subject=(
                    f"gallery_id:{parent_gallery_id};client_id:{client_id};"
                    f"request_id:{item.id};notice:{item.legal_notice_version};"
                    f"subject:{subject_declaration}"
                ),
            )
        )
        db.flush()
    except Exception:
        store.delete(
            request_id=item.id,
            gallery_id=parent_gallery_id,
            model_version=item.model_version,
            data_version=item.consent_version,
            locator=stored.locator,
        )
        raise
    return item


def _build_snapshot(
    db: Session,
    *,
    request_id: UUID,
    parent_gallery_id: UUID,
    client_id: UUID,
    model_version: str,
    quality_version: str,
) -> list[FacialSearchSnapshotItem]:
    """Congela apenas os IDs elegíveis e o fingerprint já pronto no início."""

    photo_ids = list(
        db.scalars(
            select(PhotoAsset.id)
            .join(
                MediaDerivative,
                MediaDerivative.photo_asset_id == PhotoAsset.id,
            )
            .where(
                PhotoAsset.parent_gallery_id == parent_gallery_id,
                PhotoAsset.derived_gallery_id.is_(None),
                PhotoAsset.available.is_(True),
                MediaDerivative.variant == "client_preview",
                MediaDerivative.status == "ready",
            )
            .order_by(PhotoAsset.created_at, PhotoAsset.id)
        )
    )
    if not photo_ids:
        return []

    latest_by_photo: dict[UUID, FacialJob] = {}
    jobs = db.scalars(
        select(FacialJob)
        .where(
            FacialJob.kind == "index",
            FacialJob.parent_gallery_id == parent_gallery_id,
            FacialJob.photo_asset_id.in_(photo_ids),
            FacialJob.model_version == model_version,
            FacialJob.quality_version == quality_version,
        )
        .order_by(FacialJob.created_at.desc(), FacialJob.id.desc())
    )
    for job in jobs:
        if job.photo_asset_id is not None:
            latest_by_photo.setdefault(job.photo_asset_id, job)

    return [
        FacialSearchSnapshotItem(
            search_request_id=request_id,
            parent_gallery_id=parent_gallery_id,
            client_id=client_id,
            photo_asset_id=photo_id,
            preview_fingerprint=(
                job.preview_fingerprint
                if (job := latest_by_photo.get(photo_id)) is not None
                and job.status == "completed"
                else None
            ),
            status=(
                "ready"
                if job is not None and job.status == "completed"
                else "excluded"
                if job is not None and job.status in {"failed", "cancelled"}
                else "pending"
            ),
        )
        for photo_id in photo_ids
    ]


def _retire_prior_searches(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    store: FacialReferenceStore,
) -> None:
    prior_requests = list(
        db.scalars(
            select(FacialSearchRequest).where(
                FacialSearchRequest.parent_gallery_id == parent_gallery_id,
                FacialSearchRequest.client_id == client_id,
                FacialSearchRequest.status != "cancelled",
            )
        )
    )
    for prior in prior_requests:
        if prior.reference_deleted_at is None:
            store.delete(
                request_id=prior.id,
                gallery_id=prior.parent_gallery_id,
                model_version=prior.model_version,
                data_version=prior.consent_version,
                locator=_reference_locator(prior),
            )
            prior.reference_locator_ciphertext = None
            prior.reference_locator_nonce = None
            prior.reference_key_id = None
            prior.reference_deleted_at = now()
        prior.status = "cancelled"
        prior.completed_at = prior.completed_at or now()
        prior.updated_at = now()
        db.execute(
            delete(FacialSearchCandidate).where(
                FacialSearchCandidate.search_request_id == prior.id
            )
        )
        for job in db.scalars(
            select(FacialJob).where(
                FacialJob.search_request_id == prior.id,
                FacialJob.status.in_(("queued", "processing")),
            )
        ):
            job.status = "cancelled"
            job.lease_token = None
            job.lease_expires_at = None
        cancel_pending_search_notifications(db, request_id=prior.id)
        db.add(
            AuditEvent(
                event="facial.search_replaced",
                subject=(
                    f"gallery_id:{parent_gallery_id};client_id:{client_id};"
                    f"request_id:{prior.id}"
                ),
            )
        )


def search_request_payload(item: FacialSearchRequest) -> dict[str, object]:
    waiting_for_index = item.status == "waiting_index"
    remaining_items = max(
        0,
        (item.snapshot_total - item.snapshot_ready)
        if waiting_for_index
        else (item.compare_total - item.compare_done),
    )
    return {
        "id": str(item.id),
        "gallery_id": str(item.parent_gallery_id),
        "status": item.status,
        "progress": {
            "index": {"ready": item.snapshot_ready, "total": item.snapshot_total},
            "comparison": {"done": item.compare_done, "total": item.compare_total},
        },
        "reference_deleted": item.reference_deleted_at is not None,
        "expires_at": item.expires_at.isoformat(),
        "poll_after_ms": (
            None
            if item.status in _TERMINAL_SEARCH_STATES
            else _POLL_AFTER_MS.get(item.status, 2000)
        ),
        "estimate": {
            "remaining_items": remaining_items,
            "seconds": None,
            "confidence": "unavailable",
        },
    }


def read_search_result(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    request_id: UUID,
) -> tuple[FacialSearchRequest, list[FacialSearchCandidate]]:
    item = _authorized_search_request(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=client_id,
        request_id=request_id,
    )
    candidates = list(
        db.scalars(
            select(FacialSearchCandidate)
            .join(PhotoAsset, PhotoAsset.id == FacialSearchCandidate.photo_asset_id)
            .where(
                FacialSearchCandidate.search_request_id == item.id,
                FacialSearchCandidate.parent_gallery_id == parent_gallery_id,
                FacialSearchCandidate.client_id == client_id,
                FacialSearchCandidate.rejected_at.is_(None),
                FacialSearchCandidate.expires_at > now(),
                PhotoAsset.parent_gallery_id == parent_gallery_id,
                PhotoAsset.derived_gallery_id.is_(None),
                PhotoAsset.available.is_(True),
            )
            .order_by(FacialSearchCandidate.rank)
        )
    )
    return item, candidates


def read_latest_search_result(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
) -> tuple[FacialSearchRequest, list[FacialSearchCandidate]]:
    """Recupera somente a consulta mais recente do vínculo autenticado."""

    item = db.scalar(
        select(FacialSearchRequest)
        .join(
            ParentGalleryRegistration,
            (ParentGalleryRegistration.parent_gallery_id == parent_gallery_id)
            & (ParentGalleryRegistration.client_id == client_id),
        )
        .join(ParentGallery, ParentGallery.id == parent_gallery_id)
        .where(
            FacialSearchRequest.parent_gallery_id == parent_gallery_id,
            FacialSearchRequest.client_id == client_id,
            FacialSearchRequest.status.not_in(("cancelled", "expired")),
            or_(
                FacialSearchRequest.status.in_(("ready", "no_candidates")),
                FacialSearchRequest.expires_at > now(),
            ),
            ParentGalleryRegistration.status == "active",
            ParentGallery.active.is_(True),
            ParentGallery.lifecycle_status == "active",
        )
        .order_by(FacialSearchRequest.created_at.desc(), FacialSearchRequest.id.desc())
        .limit(1)
    )
    if item is None:
        raise FacialSearchError("Consulta facial indisponível.")
    return read_search_result(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=client_id,
        request_id=item.id,
    )


def cancel_search_request(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    request_id: UUID,
    settings: FacialSettings,
    reference_store: FacialReferenceStore | None = None,
) -> FacialSearchRequest:
    item = _authorized_search_request(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=client_id,
        request_id=request_id,
    )
    was_cancelled = item.status == "cancelled"
    if item.reference_deleted_at is None:
        locator = _reference_locator(item)
        store = reference_store or FacialReferenceStore(
            settings.reference_root,
            FacialCipher(active_key_id=settings.active_key_id, keys=settings.aead_keys),
            max_bytes=settings.max_reference_bytes,
            max_pixels=settings.max_reference_pixels,
        )
        store.delete(
            request_id=item.id,
            gallery_id=item.parent_gallery_id,
            model_version=item.model_version,
            data_version=item.consent_version,
            locator=locator,
        )
        item.reference_locator_ciphertext = None
        item.reference_locator_nonce = None
        item.reference_key_id = None
        item.reference_deleted_at = now()
    item.status = "cancelled"
    item.completed_at = item.completed_at or now()
    item.updated_at = now()
    db.execute(
        delete(FacialSearchCandidate).where(
            FacialSearchCandidate.search_request_id == item.id
        )
    )
    for job in db.scalars(
        select(FacialJob).where(
            FacialJob.search_request_id == item.id,
            FacialJob.status.in_(("queued", "processing")),
        )
    ):
        job.status = "cancelled"
        job.lease_token = None
        job.lease_expires_at = None
    cancel_pending_search_notifications(db, request_id=item.id)
    if not was_cancelled:
        db.add(
            AuditEvent(
                event="facial.search_cancelled",
                subject=(
                    f"gallery_id:{parent_gallery_id};client_id:{client_id};"
                    f"request_id:{item.id}"
                ),
            )
        )
    db.flush()
    return item


def reject_search_candidate(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    request_id: UUID,
    photo_id: UUID,
) -> FacialSearchCandidate:
    item = _authorized_search_request(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=client_id,
        request_id=request_id,
    )
    candidate = db.scalar(
        select(FacialSearchCandidate).where(
            FacialSearchCandidate.search_request_id == item.id,
            FacialSearchCandidate.parent_gallery_id == parent_gallery_id,
            FacialSearchCandidate.client_id == client_id,
            FacialSearchCandidate.photo_asset_id == photo_id,
            FacialSearchCandidate.expires_at > now(),
        )
    )
    if candidate is None:
        raise FacialSearchError("Resultado facial indisponível.")
    if candidate.rejected_at is None:
        candidate.rejected_at = now()
        db.add(
            AuditEvent(
                event="facial.candidate_rejected",
                subject=(
                    f"gallery_id:{parent_gallery_id};client_id:{client_id};"
                    f"request_id:{item.id};photo_id:{photo_id}"
                ),
            )
        )
    db.flush()
    return candidate


def authorize_search_candidate_selection(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    request_id: UUID,
    photo_id: UUID,
) -> FacialSearchCandidate:
    item = _authorized_search_request(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=client_id,
        request_id=request_id,
    )
    if item.status != "ready":
        raise FacialSearchError("Resultado facial indisponível.")
    candidate = db.scalar(
        select(FacialSearchCandidate)
        .join(PhotoAsset, PhotoAsset.id == FacialSearchCandidate.photo_asset_id)
        .where(
            FacialSearchCandidate.search_request_id == item.id,
            FacialSearchCandidate.parent_gallery_id == parent_gallery_id,
            FacialSearchCandidate.client_id == client_id,
            FacialSearchCandidate.photo_asset_id == photo_id,
            FacialSearchCandidate.rejected_at.is_(None),
            FacialSearchCandidate.expires_at > now(),
            PhotoAsset.parent_gallery_id == parent_gallery_id,
            PhotoAsset.derived_gallery_id.is_(None),
            PhotoAsset.available.is_(True),
        )
    )
    if candidate is None:
        raise FacialSearchError("Resultado facial indisponível.")
    return candidate


def search_result_payload(
    item: FacialSearchRequest, candidates: list[FacialSearchCandidate]
) -> dict[str, object]:
    payload = search_request_payload(item)
    payload["candidates"] = [
        {
            "photo_id": str(candidate.photo_asset_id),
            "rank": candidate.rank,
            "quality_band": candidate.quality_band,
        }
        for candidate in candidates
    ]
    return payload


def _authorized_search_request(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    request_id: UUID,
) -> FacialSearchRequest:
    item = db.scalar(
        select(FacialSearchRequest)
        .join(
            ParentGalleryRegistration,
            (ParentGalleryRegistration.parent_gallery_id == parent_gallery_id)
            & (ParentGalleryRegistration.client_id == client_id),
        )
        .join(ParentGallery, ParentGallery.id == parent_gallery_id)
        .where(
            FacialSearchRequest.id == request_id,
            FacialSearchRequest.parent_gallery_id == parent_gallery_id,
            FacialSearchRequest.client_id == client_id,
            ParentGalleryRegistration.status == "active",
            ParentGallery.active.is_(True),
            ParentGallery.lifecycle_status == "active",
        )
    )
    if item is None or (item.status not in {"ready", "no_candidates"} and expired(item.expires_at)):
        raise FacialSearchError("Consulta facial indisponível.")
    return item


def _reference_locator(item: FacialSearchRequest) -> FacialEnvelope:
    if not all(
        (
            item.reference_locator_ciphertext,
            item.reference_locator_nonce,
            item.reference_key_id,
        )
    ):
        raise FacialSearchError("Referência facial indisponível.")
    return FacialEnvelope(
        ciphertext=item.reference_locator_ciphertext,
        nonce=item.reference_locator_nonce,
        key_id=item.reference_key_id,
    )
