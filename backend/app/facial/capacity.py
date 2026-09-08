"""Backpressure da busca facial medido sobre a fila durável."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import FacialJob, now
from app.facial.config import FacialSettings


@dataclass(frozen=True)
class FacialQueuePressure:
    depth: int
    oldest_age_seconds: int


class FacialSearchCapacityError(RuntimeError):
    """Admissão temporariamente recusada antes de persistir a referência."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Busca facial temporariamente indisponível; tente novamente.")
        self.retry_after_seconds = retry_after_seconds


def measure_search_queue(
    db: Session,
    *,
    instant: datetime | None = None,
) -> FacialQueuePressure:
    depth, oldest = db.execute(
        select(func.count(), func.min(FacialJob.created_at)).where(
            FacialJob.kind == "search",
            FacialJob.status.in_(("queued", "processing")),
        )
    ).one()
    current = instant or now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    if oldest is not None and oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=UTC)
    age = max(0, int((current - oldest).total_seconds())) if oldest else 0
    return FacialQueuePressure(depth=int(depth or 0), oldest_age_seconds=age)


def require_search_capacity(db: Session, settings: FacialSettings) -> FacialQueuePressure:
    pressure = measure_search_queue(db)
    if (
        pressure.depth >= settings.search_queue_max_depth
        or pressure.oldest_age_seconds >= settings.search_queue_max_age_seconds
    ):
        raise FacialSearchCapacityError(settings.search_retry_after_seconds)
    return pressure
