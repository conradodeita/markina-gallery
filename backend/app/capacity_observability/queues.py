"""Consultas agregadas de filas duráveis cobertas pelo diagnóstico inicial."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.auth import FacialJob, MediaJob, PhotoAnalysis, PreviewAdjustment
from app.capacity_observability.contracts import (
    Evidence,
    MetricValue,
    QueueSnapshot,
    Scope,
    Source,
    UnavailableReason,
    Unit,
    unavailable,
)
from app.facial.jobs import FACIAL_JOB_KINDS_BY_CLASS

QUEUE_CLASSES = ("media", "preview_adjustment", "search", "index", "maintenance")


def _value(
    amount: float,
    *,
    source: Source,
    instant: datetime,
    unit: Unit = Unit.JOBS,
    evidence: Evidence = Evidence.OBSERVED,
    reason: UnavailableReason | None = None,
) -> MetricValue:
    return MetricValue(
        value=amount,
        unit=unit,
        evidence=evidence,
        scope=Scope.APPLICATION_DATABASE,
        source=source,
        collected_at=instant.astimezone(UTC),
        reason=reason,
    )


def _age(
    timestamp: Any,
    *,
    source: Source,
    instant: datetime,
    evidence: Evidence,
) -> MetricValue:
    if timestamp is None:
        return unavailable(
            unit=Unit.SECONDS,
            scope=Scope.APPLICATION_DATABASE,
            collected_at=instant,
            reason=UnavailableReason.EMPTY_QUEUE,
        )
    observed = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
    seconds = (instant.astimezone(UTC) - observed.astimezone(UTC)).total_seconds()
    if seconds < 0:
        return unavailable(
            unit=Unit.SECONDS,
            scope=Scope.APPLICATION_DATABASE,
            collected_at=instant,
            reason=UnavailableReason.INCONSISTENT_TIMESTAMP,
        )
    return _value(seconds, source=source, instant=instant, unit=Unit.SECONDS, evidence=evidence)


def _unavailable(
    unit: Unit, source: Source, instant: datetime, reason: UnavailableReason
) -> MetricValue:
    del source
    return unavailable(
        unit=unit,
        scope=Scope.APPLICATION_DATABASE,
        collected_at=instant,
        reason=reason,
    )


def _queue(
    *,
    queue_class: str,
    source: Source,
    instant: datetime,
    queued: int,
    scheduled: int = 0,
    candidates: int | None = None,
    processing: int = 0,
    blocked: int | None = None,
    reclaimable: int = 0,
    oldest_created: Any = None,
    oldest_due: Any = None,
    oldest_updated: Any = None,
    wait_semantics: str,
) -> QueueSnapshot:
    return QueueSnapshot(
        queue_class=queue_class,
        queued_total=_value(queued, source=source, instant=instant),
        scheduled_total=_value(scheduled, source=source, instant=instant),
        claim_candidates_total=(
            _unavailable(Unit.JOBS, source, instant, UnavailableReason.FIELD_UNAVAILABLE)
            if candidates is None
            else _value(candidates, source=source, instant=instant)
        ),
        processing_total=_value(processing, source=source, instant=instant),
        blocked_dependency_total=(
            _unavailable(Unit.JOBS, source, instant, UnavailableReason.FIELD_UNAVAILABLE)
            if blocked is None
            else _value(blocked, source=source, instant=instant)
        ),
        reclaimable_total=_value(reclaimable, source=source, instant=instant),
        oldest_record_age_seconds=_age(
            oldest_created,
            source=source,
            instant=instant,
            evidence=Evidence.CALCULATED,
        ),
        oldest_due_age_seconds=_age(
            oldest_due,
            source=source,
            instant=instant,
            evidence=Evidence.ESTIMATED,
        ),
        oldest_updated_age_seconds=_age(
            oldest_updated,
            source=source,
            instant=instant,
            evidence=Evidence.ESTIMATED,
        ),
        wait_semantics=wait_semantics,
    )


def collect_facial_queues(db: Session, *, instant: datetime) -> list[QueueSnapshot]:
    current = instant.astimezone(UTC)
    job_class = case(
        (FacialJob.kind == "search", "search"),
        (FacialJob.kind == "index", "index"),
        (FacialJob.kind.in_(FACIAL_JOB_KINDS_BY_CLASS["maintenance"]), "maintenance"),
        else_=None,
    ).label("queue_class")
    queued = FacialJob.status == "queued"
    due = queued & (FacialJob.available_at <= current)
    processing = FacialJob.status == "processing"
    reclaimable = processing & (FacialJob.lease_expires_at <= current) & (
        FacialJob.available_at <= current
    )
    statement = (
        select(
            job_class,
            func.count().filter(queued).label("queued_total"),
            func.count().filter(queued & (FacialJob.available_at > current)).label("scheduled_total"),
            func.count().filter(due).label("claim_candidates_total"),
            func.count().filter(processing).label("processing_total"),
            func.count().filter(reclaimable).label("reclaimable_total"),
            func.min(FacialJob.created_at).filter(due).label("oldest_created"),
            func.min(FacialJob.available_at).filter(due).label("oldest_due"),
        )
        .where(FacialJob.kind.in_(
            FACIAL_JOB_KINDS_BY_CLASS["search"]
            | FACIAL_JOB_KINDS_BY_CLASS["index"]
            | FACIAL_JOB_KINDS_BY_CLASS["maintenance"]
        ))
        .group_by(job_class)
    )
    rows = {row.queue_class: row for row in db.execute(statement)}
    results = []
    for name in ("search", "index", "maintenance"):
        row = rows.get(name)
        results.append(
            _queue(
                queue_class=name,
                source=Source.FACIAL_JOB,
                instant=instant,
                queued=row.queued_total if row else 0,
                scheduled=row.scheduled_total if row else 0,
                candidates=row.claim_candidates_total if row else 0,
                processing=row.processing_total if row else 0,
                blocked=0,
                reclaimable=row.reclaimable_total if row else 0,
                oldest_created=row.oldest_created if row else None,
                oldest_due=row.oldest_due if row else None,
                wait_semantics="available_at_age_estimate",
            )
        )
    return results


def collect_media_queue(db: Session, *, instant: datetime) -> QueueSnapshot:
    blocked_dependency = (
        select(PhotoAnalysis.photo_asset_id)
        .where(
            PhotoAnalysis.photo_asset_id == MediaJob.photo_asset_id,
            PhotoAnalysis.state.in_(("pending", "receiving")),
        )
        .exists()
    )
    queued = MediaJob.status == "queued"
    blocked = queued & blocked_dependency.correlate(MediaJob)
    claimable = queued & ~blocked_dependency.correlate(MediaJob)
    statement = select(
        func.count().filter(queued).label("queued_total"),
        func.count().filter(blocked).label("blocked_total"),
        func.count().filter(claimable).label("claimable_total"),
        func.count().filter(MediaJob.status == "processing").label("processing_total"),
        func.min(MediaJob.created_at).filter(claimable).label("oldest_created"),
    ).where(MediaJob.kind == "generate_derivatives")
    row = db.execute(statement).one()
    return _queue(
        queue_class="media",
        source=Source.MEDIA_JOB,
        instant=instant,
        queued=row.queued_total,
        candidates=row.claimable_total,
        processing=row.processing_total,
        blocked=row.blocked_total,
        oldest_created=row.oldest_created,
        wait_semantics="created_age_estimate",
    )


def collect_adjustment_queue(db: Session, *, instant: datetime) -> QueueSnapshot:
    queued = PreviewAdjustment.status == "queued"
    statement = select(
        func.count().filter(queued).label("queued_total"),
        func.count().filter(PreviewAdjustment.status == "processing").label("processing_total"),
        func.min(PreviewAdjustment.updated_at).filter(queued).label("oldest_updated"),
    )
    row = db.execute(statement).one()
    return _queue(
        queue_class="preview_adjustment",
        source=Source.PREVIEW_ADJUSTMENT,
        instant=instant,
        queued=row.queued_total,
        candidates=None,
        processing=row.processing_total,
        blocked=None,
        oldest_updated=row.oldest_updated,
        wait_semantics="updated_age_estimate",
    )


def collect_all_queues(db: Session, *, instant: datetime) -> list[QueueSnapshot]:
    """Cinco SELECTs no total: três classes faciais em uma agregação."""
    facial = collect_facial_queues(db, instant=instant)
    media = collect_media_queue(db, instant=instant)
    adjustment = collect_adjustment_queue(db, instant=instant)
    return [media, adjustment, *facial]
