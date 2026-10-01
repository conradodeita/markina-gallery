"""Processamento durável de consultas faciais sobre um snapshot congelado."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
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
from app.facial.rollout import rollout_is_active
from app.public_gallery_access import (
    PublicGalleryAccessDenied,
    authorized_canonical_photos,
    require_public_gallery_browsing,
)

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

    job = repository._leased(db, claim)
    if job is None or job.kind != "search" or job.search_request_id is None:
        raise FacialJobError("Job facial não pode ser executado.")
    request = owned_record(db, FacialSearchRequest, job.search_request_id, tenant_id=claim.tenant_id)
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
        # Uma morte abrupta (por exemplo, OOM do processo) não atravessa a
        # fronteira de exceção abaixo. O próximo claim incrementa `attempts`;
        # depois do orçamento normal, ele encerra e higieniza a consulta sem
        # executar novamente o trecho que derrubou o consumidor anterior.
        if job.attempts > max_attempts:
            _finish_request(
                db,
                request,
                status="failed",
                store=store,
                cipher=cipher,
                settings=settings,
            )
            return repository.fail(
                db,
                claim,
                TimeoutError("Worker interrompido durante tentativas anteriores."),
                max_attempts=max_attempts,
                retry_delay_seconds=retry_delay_seconds,
            )
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

        repository._leased(db, claim)
        request.status = "validating_reference"
        db.commit()
        if request.reference_region_id:
            from app.facial.regions import authorized_region, region_embedding
            region = authorized_region(db, gallery_id=request.parent_gallery_id, client_id=request.client_id,
                                       region_id=request.reference_region_id, settings=settings)
            query_embedding = region_embedding(db, region, cipher, settings, tenant_id=claim.tenant_id)
        else:
            repository._leased(db, claim)
            payload = store.load(
                request_id=request.id,
                gallery_id=request.parent_gallery_id,
                model_version=request.model_version,
                data_version=request.consent_version,
                locator=_reference_locator(request),
            )
            analysis = analyze_query(provider.observe_bytes(payload))
            if analysis.status != "ready" or analysis.observation is None:
                _finish_request(db, request, status=analysis.status, store=store, cipher=cipher, settings=settings)
                return repository.complete(db, claim)
            query_embedding = analysis.observation.embedding

        repository._leased(db, claim)
        _refresh_snapshot(db, request)
        request.status = "searching"
        db.commit()
        fingerprints = {
            item.photo_asset_id: item.preview_fingerprint
            for item in _snapshot_items(db, request.id, tenant_id=request.tenant_id)
            if item.status == "ready" and item.preview_fingerprint is not None
        }

        def authorize_comparison(photo_id):
            repository._leased(db, claim)
            if not _request_is_authorized(db, request, settings):
                raise FacialJobError("Consulta facial indisponível.")
            _refresh_snapshot(db, request)
            return any(item.photo_asset_id == photo_id and item.status == "ready"
                       for item in _snapshot_items(db, request.id, tenant_id=request.tenant_id))

        matches = search_gallery_index(
            db,
            gallery_id=request.parent_gallery_id,
            tenant_id=claim.tenant_id,
            query_embedding=query_embedding,
            cipher=cipher,
            settings=settings,
            threshold_milli=settings.similarity_threshold_milli,
            allowed_fingerprints=fingerprints,
            ambiguous_threshold_milli=settings.ambiguous_threshold_milli,
            authorize=authorize_comparison,
        )
        repository._leased(db, claim)
        if not _request_is_authorized(db, request, settings):
            raise FacialJobError("Consulta facial indisponível.")
        request.compare_done = request.compare_total
        request.status = "ranking"
        db.commit()

        db.execute(
            delete(FacialSearchCandidate).where(
                FacialSearchCandidate.tenant_id == request.tenant_id,
                    FacialSearchCandidate.search_request_id == request.id
            )
        )
        candidate_expiry = now() + timedelta(
            seconds=settings.candidate_retention_seconds
        )
        db.add_all(
            FacialSearchCandidate(
                tenant_id=claim.tenant_id,
                search_request_id=request.id,
                parent_gallery_id=request.parent_gallery_id,
                client_id=request.client_id,
                photo_asset_id=match.photo_id,
                rank=rank,
                quality_band=match.quality_band,
                match_class=match.match_class,
                expires_at=candidate_expiry,
            )
            for rank, match in enumerate(matches, start=1)
        )
        if matches:
            repository.enqueue(
                db,
                kind="cleanup",
                tenant_id=request.tenant_id,
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
    except HTTPException:
        repository.release_denied(db, claim)
        return db.get(FacialJob, claim.id)
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
        request = owned_record(db, FacialSearchRequest, job.search_request_id, tenant_id=claim.tenant_id)
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
    require_active_owner(db, request.tenant_id)
    try:
        require_public_gallery_browsing(db, parent_gallery_id=request.parent_gallery_id, client_id=request.client_id)
    except PublicGalleryAccessDenied:
        return False
    if request.status in {"cancelled", "expired"}:
        return False
    if request.authorization_method != "direct_region" and request.consent_version != settings.consent_version:
        return False
    if request.subject_declaration == "minor" and request.authorization_method == "legacy":
        from app.facial.representation import (
            FacialLegalRepresentationError,
            require_valid_legal_representation,
        )
        try:
            require_valid_legal_representation(db, representation_reference=request.representation_reference,
                client_id=request.client_id, parent_gallery_id=request.parent_gallery_id,
                terms_version=settings.minor_policy_version)
        except FacialLegalRepresentationError:
            return False
    gallery = owned_record(db, ParentGallery, request.parent_gallery_id, tenant_id=request.tenant_id)
    registration = db.scalar(
        select(ParentGalleryRegistration.id).where(
            ParentGalleryRegistration.tenant_id == request.tenant_id,
                    ParentGalleryRegistration.parent_gallery_id == request.parent_gallery_id,
            ParentGalleryRegistration.client_id == request.client_id,
            ParentGalleryRegistration.status == "active",
        )
    )
    policy = owned_record(db, GalleryFacialPolicy, request.policy_id, tenant_id=request.tenant_id)
    return bool(
        gallery
        and gallery.active
        and gallery.lifecycle_status == "active"
        and registration
        and policy
        and policy.parent_gallery_id == request.parent_gallery_id
        and policy.status == "active"
        and request.legal_notice_version == policy.legal_notice_version
        and rollout_is_active(
            db,
            settings=settings,
            parent_gallery_id=request.parent_gallery_id,
            tenant_id=request.tenant_id,
        )
        and request.model_version == settings.model_version == policy.model_version
        and request.quality_version
        == settings.quality_version
        == policy.quality_version
        and request.index_generation == policy.index_generation
    )


def _refresh_snapshot(db: Session, request: FacialSearchRequest) -> bool:
    items = _snapshot_items(db, request.id, tenant_id=request.tenant_id)
    pending_items = [item for item in items if item.status in {"pending", "ready"}]
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
                    PhotoAsset.tenant_id == request.tenant_id,
                    PhotoAsset.id.in_(photo_ids),
                    PhotoAsset.id.in_(authorized_canonical_photos(request.parent_gallery_id, request.client_id).with_only_columns(PhotoAsset.id)),
                    PhotoAsset.parent_gallery_id == request.parent_gallery_id,
                    PhotoAsset.derived_gallery_id.is_(None),
                    PhotoAsset.available.is_(True),
                    MediaDerivative.tenant_id == request.tenant_id,
                    MediaDerivative.variant == "client_preview",
                    MediaDerivative.status == "ready",
                )
            )
        )
        latest_by_photo: dict[UUID, FacialJob] = {}
        index_jobs = db.scalars(
            select(FacialJob)
            .where(
                FacialJob.kind == "index",
                FacialJob.tenant_id == request.tenant_id,
                    FacialJob.parent_gallery_id == request.parent_gallery_id,
                FacialJob.photo_asset_id.in_(photo_ids),
                FacialJob.model_version == request.model_version,
                FacialJob.quality_version == request.quality_version,
            )
            .order_by(FacialJob.created_at.desc(), FacialJob.id.desc())
        )
        for index_job in index_jobs:
            latest_by_photo.setdefault(index_job.photo_asset_id, index_job)
        for item in pending_items:
            if item.photo_asset_id not in eligible:
                item.status = "excluded"
                continue
            index_job = latest_by_photo.get(item.photo_asset_id)
            if index_job is not None and index_job.status in {"failed", "cancelled"}:
                item.status = "excluded"
                continue
            if (
                index_job is not None
                and index_job.status == "completed"
                and index_job.preview_fingerprint
            ):
                item.status = "ready"
                item.preview_fingerprint = index_job.preview_fingerprint

    request.snapshot_ready = sum(item.status == "ready" for item in items)
    request.compare_total = request.snapshot_ready
    request.updated_at = now()
    db.commit()
    return any(item.status == "pending" for item in items)


def _snapshot_items(
    db: Session, request_id: UUID, *, tenant_id: UUID
) -> list[FacialSearchSnapshotItem]:
    request = owned_record(db, FacialSearchRequest, request_id, tenant_id=tenant_id)
    if request is None:
        raise FacialJobError("Snapshot facial indisponível.")
    items = list(
        db.scalars(
            select(FacialSearchSnapshotItem)
            .where(FacialSearchSnapshotItem.tenant_id == tenant_id, FacialSearchSnapshotItem.search_request_id == request_id)
            .order_by(FacialSearchSnapshotItem.created_at, FacialSearchSnapshotItem.id)
        )
    )
    if any(item.parent_gallery_id != request.parent_gallery_id or item.client_id != request.client_id for item in items):
        raise FacialJobError("Snapshot facial indisponível.")
    return items


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
    require_active_owner(db, request.tenant_id)
    with db.no_autoflush:
        current_status = db.scalar(select(FacialSearchRequest.status).where(
            FacialSearchRequest.id == request.id, FacialSearchRequest.tenant_id == request.tenant_id,
        ))
    if current_status is None:
        raise FacialJobError("Consulta facial indisponível.")
    if current_status in {"cancelled", "expired"}:
        status = current_status
        db.execute(delete(FacialSearchCandidate).where(
            FacialSearchCandidate.tenant_id == request.tenant_id,
            FacialSearchCandidate.search_request_id == request.id,
        ))
    _delete_reference(request, store)
    request.status = status
    request.reference_region_id = None
    request.completed_at = now()
    request.updated_at = now()
    db.add(
        AuditEvent(
            tenant_id=request.tenant_id,
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
