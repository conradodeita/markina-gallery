"""Fila durável de jobs faciais com wake-up Redis opcional."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from secrets import token_hex
from typing import Protocol
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import FacialJob, now
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
        existing = db.scalar(
            select(FacialJob).where(FacialJob.idempotency_key == idempotency_key)
        )
        if existing:
            return existing, False
        item = FacialJob(
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
                select(FacialJob).where(FacialJob.idempotency_key == idempotency_key)
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
        query = select(FacialJob).where(
            FacialJob.available_at <= current,
            or_(
                FacialJob.status == "queued",
                (
                    (FacialJob.status == "processing")
                    & (FacialJob.lease_expires_at <= current)
                ),
            ),
        )
        if job_class is not None:
            kinds = FACIAL_JOB_KINDS_BY_CLASS.get(job_class)
            if kinds is None:
                raise FacialJobError("Classe de worker facial inválida.")
            query = query.where(FacialJob.kind.in_(kinds))
        item = db.scalar(
            query
            .order_by(FacialJob.priority, FacialJob.available_at, FacialJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if item is None:
            return None
        lease_token = token_hex(24)
        item.status = "processing"
        item.lease_token = lease_token
        item.lease_expires_at = current + timedelta(seconds=lease_seconds)
        item.attempts += 1
        item.updated_at = current
        db.commit()
        return ClaimedFacialJob(id=item.id, lease_token=lease_token, kind=item.kind)

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
        if item.attempts >= max_attempts:
            item.status = "failed"
        else:
            item.status = "queued"
            item.available_at = current + timedelta(seconds=retry_delay_seconds)
        item.updated_at = current
        db.commit()
        return item

    @staticmethod
    def _leased(db: Session, claim: ClaimedFacialJob) -> FacialJob:
        item = db.scalar(
            select(FacialJob).where(FacialJob.id == claim.id).with_for_update()
        )
        if (
            item is None
            or item.status != "processing"
            or item.lease_token != claim.lease_token
        ):
            raise FacialJobError("Lease facial inválido ou expirado.")
        return item


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
