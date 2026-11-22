"""Fila durável de jobs faciais com wake-up Redis opcional."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from secrets import token_hex
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    DerivedGallery,
    FacialJob,
    FacialSearchRequest,
    ParentGallery,
    PhotoAsset,
    Tenant,
    TenantClosureRequest,
    expired,
    now,
)
from app.facial.closure_gate import (
    FacialCleanupInProgress,
    biometric_cleanup_started,
    lock_facial_tenant,
    require_facial_queue_write_allowed,
)
from app.facial.crypto import FacialCryptoError
from app.facial.provider import FacialProviderError
from app.facial.reference_store import FacialReferenceError

FACIAL_JOB_KINDS_BY_CLASS = {
    "search": frozenset({"search"}),
    "index": frozenset({"index"}),
    "maintenance": frozenset({"purge", "cleanup"}),
}


class FacialJobError(RuntimeError):
    """Operação inválida ou lease perdido na fila facial."""


class FacialQueueNotificationError(RuntimeError):
    """Falha transitória já sanitizada pelo adaptador da fila."""


def facial_job_class(kind: str) -> str:
    for job_class, kinds in FACIAL_JOB_KINDS_BY_CLASS.items():
        if kind in kinds:
            return job_class
    raise FacialJobError("Tipo de job facial inválido.")


def facial_queue_name(base_name: str, job_class: str) -> str:
    if job_class not in FACIAL_JOB_KINDS_BY_CLASS:
        raise FacialJobError("Classe de worker facial inválida.")
    return f"{base_name}:{job_class}"


class QueueNotifier(Protocol):
    def lpush(self, queue_name: str, value: str) -> object: ...


@dataclass(frozen=True)
class ClaimedFacialJob:
    id: UUID
    lease_token: str
    tenant_id: UUID
    kind: str | None = None


def sanitized_job_error(error: Exception) -> str:
    if isinstance(error, FacialProviderError):
        return "provider_unavailable"
    if isinstance(error, FacialCryptoError):
        return "crypto_unavailable"
    if isinstance(error, FacialReferenceError):
        return "reference_unavailable"
    if isinstance(error, TimeoutError):
        return "timeout"
    return "internal_failure"


class FacialJobRepository:
    def enqueue(
        self,
        db: Session,
        *,
        kind: str,
        idempotency_key: str,
        parent_gallery_id: UUID,
        tenant_id: UUID,
        derived_gallery_id: UUID | None = None,
        priority: int = 100,
        photo_asset_id: UUID | None = None,
        search_request_id: UUID | None = None,
        model_version: str | None = None,
        quality_version: str | None = None,
        preview_fingerprint: str | None = None,
        available_at: datetime | None = None,
    ) -> tuple[FacialJob, bool]:
        if kind not in {"index", "purge", "search", "cleanup"}:
            raise FacialJobError("Tipo de job facial inválido.")
        if not idempotency_key or len(idempotency_key) > 240 or priority < 0:
            raise FacialJobError("Identidade do job facial inválida.")
        if kind == "index" and photo_asset_id is None:
            raise FacialJobError("Job de índice facial sem foto.")
        if kind == "index" and not all(
            (model_version, quality_version, preview_fingerprint)
        ):
            raise FacialJobError("Job de índice facial sem versão ou fingerprint.")
        if kind == "search" and search_request_id is None:
            raise FacialJobError("Job de consulta facial sem request.")
        try:
            require_facial_queue_write_allowed(db, tenant_id)
        except FacialCleanupInProgress as exc:
            raise FacialJobError("Fila facial indisponível durante o encerramento.") from exc
        self.require_origin(db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id,
                            derived_gallery_id=derived_gallery_id, photo_asset_id=photo_asset_id,
                            search_request_id=search_request_id)
        existing = db.scalar(
            select(FacialJob).where(FacialJob.tenant_id == tenant_id, FacialJob.idempotency_key == idempotency_key)
        )
        if existing:
            return existing, False
        item = FacialJob(
            tenant_id=tenant_id,
            kind=kind,
            status="queued",
            idempotency_key=idempotency_key,
            priority=priority,
            parent_gallery_id=parent_gallery_id,
            derived_gallery_id=derived_gallery_id,
            photo_asset_id=photo_asset_id,
            search_request_id=search_request_id,
            model_version=model_version,
            quality_version=quality_version,
            preview_fingerprint=preview_fingerprint,
            available_at=available_at or now(),
        )
        try:
            with db.begin_nested():
                db.add(item)
                db.flush()
        except IntegrityError:
            existing = db.scalar(
                select(FacialJob).where(FacialJob.tenant_id == tenant_id, FacialJob.idempotency_key == idempotency_key)
            )
            if existing:
                return existing, False
            raise
        return item, True

    def claim_next(
        self,
        db: Session,
        *,
        lease_seconds: int,
        instant: datetime | None = None,
        job_class: str | None = None,
    ) -> ClaimedFacialJob | None:
        current = instant or now()
        eligible_job = or_(
            FacialJob.status == "queued",
            (
                (FacialJob.status == "processing")
                & (FacialJob.lease_expires_at <= current)
            ),
        )
        cleanup_started = select(TenantClosureRequest.id).where(
            TenantClosureRequest.tenant_id == FacialJob.tenant_id,
            TenantClosureRequest.state == "closing",
            TenantClosureRequest.biometric_cleanup_started_at.is_not(None),
        ).exists()
        tenant_query = select(
            FacialJob.tenant_id,
            func.min(FacialJob.priority).label("priority"),
            func.min(FacialJob.available_at).label("available_at"),
        ).join(Tenant, Tenant.id == FacialJob.tenant_id).where(
            Tenant.status == "active", Tenant.lifecycle != "closed",
            FacialJob.available_at <= current, eligible_job, ~cleanup_started,
        ).group_by(FacialJob.tenant_id)
        if job_class is not None:
            kinds = FACIAL_JOB_KINDS_BY_CLASS.get(job_class)
            if kinds is None:
                raise FacialJobError("Classe de worker facial inválida.")
            tenant_query = tenant_query.where(FacialJob.kind.in_(kinds))
        candidate_tenants = db.execute(
            tenant_query.order_by("priority", "available_at").limit(64)
        ).all()
        for tenant_id, _priority, _available_at in candidate_tenants:
            tenant = lock_facial_tenant(db, tenant_id, skip_locked=True)
            if (
                tenant is None
                or tenant.status != "active"
                or tenant.lifecycle == "closed"
                or biometric_cleanup_started(db, tenant_id)
            ):
                continue
            item_query = select(FacialJob).where(
                FacialJob.tenant_id == tenant_id,
                FacialJob.available_at <= current,
                eligible_job,
            )
            if job_class is not None:
                item_query = item_query.where(FacialJob.kind.in_(kinds))
            item = db.scalar(
                item_query
                .order_by(FacialJob.priority, FacialJob.available_at, FacialJob.created_at)
                .limit(1)
                .with_for_update(skip_locked=True, of=FacialJob)
            )
            if item is None:
                continue
            self.require_origin(db, tenant_id=item.tenant_id, parent_gallery_id=item.parent_gallery_id,
                                derived_gallery_id=item.derived_gallery_id, photo_asset_id=item.photo_asset_id,
                                search_request_id=item.search_request_id)
            lease_token = token_hex(24)
            item.status = "processing"
            item.lease_token = lease_token
            item.lease_expires_at = current + timedelta(seconds=lease_seconds)
            item.attempts += 1
            item.updated_at = current
            db.commit()
            return ClaimedFacialJob(
                id=item.id, tenant_id=item.tenant_id, lease_token=lease_token, kind=item.kind
            )
        return None

    def progress(
        self,
        db: Session,
        claim: ClaimedFacialJob,
        *,
        done: int,
        total: int,
        lease_seconds: int,
    ) -> FacialJob:
        item = self._leased(db, claim)
        if total < 0 or done < 0 or done > total:
            raise FacialJobError("Progresso facial inválido.")
        current = now()
        item.progress_done = done
        item.progress_total = total
        item.lease_expires_at = current + timedelta(seconds=lease_seconds)
        item.updated_at = current
        db.commit()
        return item

    def complete(self, db: Session, claim: ClaimedFacialJob) -> FacialJob:
        item = self._leased(db, claim)
        item.status = "completed"
        item.progress_done = item.progress_total
        item.lease_token = None
        item.lease_expires_at = None
        item.last_error_category = None
        item.updated_at = now()
        db.commit()
        return item

    def cancel(self, db: Session, claim: ClaimedFacialJob) -> FacialJob:
        """Encerra sem retentativa um job cujo escopo deixou de ser autorizado."""

        item = self._leased(db, claim)
        item.status = "cancelled"
        item.lease_token = None
        item.lease_expires_at = None
        item.last_error_category = None
        item.updated_at = now()
        db.commit()
        return item

    def defer(
        self,
        db: Session,
        claim: ClaimedFacialJob,
        *,
        delay_seconds: int,
    ) -> FacialJob:
        """Libera o lease sem tratar uma dependência ainda pendente como falha."""

        if delay_seconds < 0:
            raise FacialJobError("Atraso facial inválido.")
        item = self._leased(db, claim)
        item.status = "queued"
        item.available_at = now() + timedelta(seconds=delay_seconds)
        item.lease_token = None
        item.lease_expires_at = None
        item.updated_at = now()
        db.commit()
        return item

    def fail(
        self,
        db: Session,
        claim: ClaimedFacialJob,
        error: Exception,
        *,
        max_attempts: int,
        retry_delay_seconds: int,
    ) -> FacialJob:
        item = self._leased(db, claim)
        item.last_error_category = sanitized_job_error(error)
        item.lease_token = None
        item.lease_expires_at = None
        current = now()
        if item.kind == "index" and item.photo_asset_id:
            from app.facial.analysis_metrics import safe_attempt_metrics
            from app.facial.lifecycle import analysis_for
            from app.facial.provider import FacialProviderError

            analysis = analysis_for(db, item.photo_asset_id, lock=True, tenant_id=item.tenant_id)
            if analysis:
                metrics = safe_attempt_metrics(error.metrics) if isinstance(error, FacialProviderError) else {}
                analysis.metrics = {**metrics, "attempts": item.attempts,
                                    "last_error": item.last_error_category,
                                    "quality_version": item.quality_version}
        if item.attempts >= max_attempts:
            item.status = "failed"
            if item.kind == "index" and item.photo_asset_id:
                from app.facial.lifecycle import analysis_for
                analysis = analysis_for(db, item.photo_asset_id, lock=True, tenant_id=item.tenant_id)
                if analysis:
                    analysis.state = "failed"
                    analysis.metrics = {**analysis.metrics, "final_error": item.last_error_category,
                                        "attempts": item.attempts}
        else:
            item.status = "queued"
            item.available_at = current + timedelta(seconds=retry_delay_seconds)
        item.updated_at = current
        db.commit()
        return item

    @staticmethod
    def require_origin(db: Session, *, tenant_id: UUID, parent_gallery_id: UUID,
                       derived_gallery_id: UUID | None = None, photo_asset_id: UUID | None = None,
                       search_request_id: UUID | None = None) -> None:
        if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
            raise FacialJobError("Origem facial indisponível.")
        for model, resource_id in ((DerivedGallery, derived_gallery_id), (PhotoAsset, photo_asset_id),
                                   (FacialSearchRequest, search_request_id)):
            if resource_id:
                resource = owned_record(db, model, resource_id, tenant_id=tenant_id)
                if resource is None or resource.parent_gallery_id != parent_gallery_id:
                    raise FacialJobError("Origem facial indisponível.")

    @staticmethod
    def _leased(db: Session, claim: ClaimedFacialJob) -> FacialJob:
        require_active_owner(db, claim.tenant_id)
        item = db.scalar(
            select(FacialJob).where(FacialJob.tenant_id == claim.tenant_id, FacialJob.id == claim.id)
            .with_for_update().execution_options(populate_existing=True)
        )
        if (
            item is None
            or item.status != "processing"
            or item.lease_token != claim.lease_token
            or item.lease_expires_at is None
            or expired(item.lease_expires_at)
        ):
            raise FacialJobError("Lease facial inválido ou expirado.")
        FacialJobRepository.require_origin(db, tenant_id=item.tenant_id, parent_gallery_id=item.parent_gallery_id,
                                          derived_gallery_id=item.derived_gallery_id, photo_asset_id=item.photo_asset_id,
                                          search_request_id=item.search_request_id)
        return item

    @staticmethod
    def release_denied(db: Session, claim: ClaimedFacialJob) -> None:
        """Preserva trabalho suspenso; só libera o lease durável deste consumidor."""
        db.rollback()
        item = db.scalar(select(FacialJob).where(FacialJob.id == claim.id, FacialJob.tenant_id == claim.tenant_id,
            FacialJob.lease_token == claim.lease_token).with_for_update())
        if item:
            item.status = "queued"
            item.lease_token = None
            item.lease_expires_at = None
            item.attempts = max(0, item.attempts - 1)
            db.commit()


class FacialJobDispatcher:
    def __init__(
        self,
        repository: FacialJobRepository,
        *,
        queue_name: str,
        notifier: QueueNotifier | None = None,
    ) -> None:
        self._repository = repository
        self._queue_name = queue_name
        self._notifier = notifier

    def dispatch(self, db: Session, **job) -> tuple[FacialJob, bool]:
        item, created = self._repository.enqueue(db, **job)
        db.commit()
        if created and self._notifier is not None:
            try:
                self._notifier.lpush(
                    facial_queue_name(
                        self._queue_name,
                        facial_job_class(str(job.get("kind", ""))),
                    ),
                    str(item.id),
                )
            except (
                ConnectionError,
                TimeoutError,
                OSError,
                FacialQueueNotificationError,
            ):
                # O banco é a fonte durável; Redis serve apenas para acordar o worker.
                pass
        return item, created
