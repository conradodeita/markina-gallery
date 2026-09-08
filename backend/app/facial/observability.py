"""SLOs, métricas e alertas agregados do runtime facial."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import FacialJob, FacialSearchCandidate, FacialSearchRequest, now
from app.facial.jobs import FACIAL_JOB_KINDS_BY_CLASS, facial_job_class

ALLOWED_DIMENSIONS = frozenset({"environment", "type", "state"})
ALLOWED_DIMENSION_VALUES = {
    "environment": frozenset(
        {"development", "test", "homolog", "homologation", "staging", "production"}
    ),
    "type": frozenset(
        {
            "runtime",
            "admission",
            "search",
            "index",
            "maintenance",
            "reference",
            "candidate",
        }
    ),
    "state": frozenset(
        {
            "enabled",
            "disabled",
            "accepted",
            "refused",
            "availability",
            "queued",
            "processing",
            "completed",
            "failed",
            "cancelled",
            "pending",
            "terminal",
            "observed",
            "overdue",
            "firing",
        }
    ),
}
FORBIDDEN_OBSERVABILITY_TERMS = frozenset(
    {
        "image",
        "photo",
        "embedding",
        "vector",
        "score",
        "landmark",
        "bounding_box",
        "name",
        "phone",
        "inferred_name",
        "face_box",
        "facial_box",
        "imagem",
        "foto",
        "nome",
        "telefone",
        "gallery_id",
        "client_id",
        "request_id",
    }
)


@dataclass(frozen=True)
class FacialSloLimits:
    admission_availability_percent: float = 99.0
    search_p95_seconds: int = 120
    queue_oldest_seconds: int = 300
    terminal_failure_percent: float = 5.0
    reference_purge_seconds: int = 900
    candidate_purge_seconds: int = 86_400
    cpu_percent_by_class: Mapping[str, int] | None = None
    memory_mib_by_class: Mapping[str, int] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cpu_percent_by_class",
            self.cpu_percent_by_class
            or {"search": 75, "index": 85, "maintenance": 75},
        )
        object.__setattr__(
            self,
            "memory_mib_by_class",
            self.memory_mib_by_class
            or {"search": 460, "index": 690, "maintenance": 230},
        )


FACIAL_SLO_LIMITS = FacialSloLimits()


@dataclass(frozen=True)
class FacialMetricSample:
    name: str
    value: float
    dimensions: dict[str, str]


@dataclass(frozen=True)
class FacialAlert:
    name: str
    observed: float
    threshold: float
    dimensions: dict[str, str]


@dataclass(frozen=True)
class FacialAdmissionSnapshot:
    accepted: int
    refused: int


class FacialAdmissionCounter:
    """Contadores agregados do processo API, sem escopo de negócio."""

    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._lock = Lock()

    def record(self, state: str) -> None:
        if state not in {"accepted", "refused"}:
            raise ValueError("Estado de admissão facial inválido.")
        with self._lock:
            self._counts[state] += 1

    def snapshot(self) -> FacialAdmissionSnapshot:
        with self._lock:
            return FacialAdmissionSnapshot(
                accepted=self._counts["accepted"],
                refused=self._counts["refused"],
            )

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


FACIAL_ADMISSION_COUNTER = FacialAdmissionCounter()


def validate_observability_record(record: FacialMetricSample | FacialAlert) -> None:
    if set(record.dimensions) - ALLOWED_DIMENSIONS:
        raise ValueError("Dimensão facial não permitida.")
    if set(record.dimensions) != ALLOWED_DIMENSIONS:
        raise ValueError("Dimensões faciais incompletas.")
    for dimension, value in record.dimensions.items():
        if value not in ALLOWED_DIMENSION_VALUES[dimension]:
            raise ValueError("Valor de dimensão facial não permitido.")
    serialized = " ".join(
        (record.name, *record.dimensions.keys(), *record.dimensions.values())
    ).lower()
    if any(term in serialized for term in FORBIDDEN_OBSERVABILITY_TERMS):
        raise ValueError("Métrica facial contém dado proibido.")
    if not all(isinstance(value, str) for value in record.dimensions.values()):
        raise ValueError("Dimensão facial inválida.")
    numeric = record.value if isinstance(record, FacialMetricSample) else record.observed
    if not isinstance(numeric, (int, float)) or not math.isfinite(float(numeric)):
        raise ValueError("Valor facial precisa ser numérico e agregado.")


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _nearest_rank_p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def collect_facial_metrics(
    db: Session,
    *,
    environment: str,
    enabled: bool,
    cpu_percent_by_class: Mapping[str, float] | None = None,
    memory_mib_by_class: Mapping[str, float] | None = None,
    admissions: FacialAdmissionSnapshot | None = None,
    instant: datetime | None = None,
) -> list[FacialMetricSample]:
    observed_at = instant or now()
    samples: list[FacialMetricSample] = [
        FacialMetricSample(
            name="facial_runtime_enabled",
            value=float(enabled),
            dimensions={"environment": environment, "type": "runtime", "state": "enabled" if enabled else "disabled"},
        )
    ]
    admission_snapshot = admissions or FACIAL_ADMISSION_COUNTER.snapshot()
    admission_total = admission_snapshot.accepted + admission_snapshot.refused
    admission_availability = (
        100.0 * admission_snapshot.accepted / admission_total
        if admission_total
        else (100.0 if enabled else 0.0)
    )
    for state, value in (
        ("accepted", admission_snapshot.accepted),
        ("refused", admission_snapshot.refused),
        ("availability", admission_availability),
    ):
        samples.append(
            FacialMetricSample(
                name=(
                    "facial_admission_availability_percent"
                    if state == "availability"
                    else "facial_admissions_total"
                ),
                value=float(value),
                dimensions={
                    "environment": environment,
                    "type": "admission",
                    "state": state,
                },
            )
        )
    jobs = list(db.scalars(select(FacialJob)))
    for job_class in sorted(FACIAL_JOB_KINDS_BY_CLASS):
        class_jobs = [job for job in jobs if facial_job_class(job.kind) == job_class]
        for status in ("queued", "processing", "completed", "failed", "cancelled"):
            samples.append(
                FacialMetricSample(
                    name="facial_jobs_total",
                    value=float(sum(job.status == status for job in class_jobs)),
                    dimensions={"environment": environment, "type": job_class, "state": status},
                )
            )
        pending = [job for job in class_jobs if job.status in {"queued", "processing"}]
        oldest_age = max(
            (observed_at - _utc(job.created_at)).total_seconds() for job in pending
        ) if pending else 0.0
        samples.append(
            FacialMetricSample(
                name="facial_queue_oldest_seconds",
                value=max(0.0, oldest_age),
                dimensions={"environment": environment, "type": job_class, "state": "pending"},
            )
        )
        terminal = [job for job in class_jobs if job.status in {"completed", "failed"}]
        failure_percent = (
            100.0 * sum(job.status == "failed" for job in terminal) / len(terminal)
            if terminal
            else 0.0
        )
        samples.append(
            FacialMetricSample(
                name="facial_terminal_failure_percent",
                value=failure_percent,
                dimensions={"environment": environment, "type": job_class, "state": "terminal"},
            )
        )
        terminal_durations = [
            max(0.0, (_utc(job.updated_at) - _utc(job.created_at)).total_seconds())
            for job in terminal
        ]
        samples.append(
            FacialMetricSample(
                name="facial_job_p95_seconds",
                value=_nearest_rank_p95(terminal_durations),
                dimensions={
                    "environment": environment,
                    "type": job_class,
                    "state": "terminal",
                },
            )
        )
        if cpu_percent_by_class and job_class in cpu_percent_by_class:
            samples.append(
                FacialMetricSample(
                    name="facial_cpu_percent",
                    value=float(cpu_percent_by_class[job_class]),
                    dimensions={"environment": environment, "type": job_class, "state": "observed"},
                )
            )
        if memory_mib_by_class and job_class in memory_mib_by_class:
            samples.append(
                FacialMetricSample(
                    name="facial_memory_mib",
                    value=float(memory_mib_by_class[job_class]),
                    dimensions={"environment": environment, "type": job_class, "state": "observed"},
                )
            )

    completed_searches = list(
        db.scalars(
            select(FacialSearchRequest).where(
                FacialSearchRequest.completed_at.is_not(None)
            )
        )
    )
    durations = [
        max(0.0, (_utc(item.completed_at) - _utc(item.created_at)).total_seconds())
        for item in completed_searches
        if item.completed_at is not None
    ]
    samples.append(
        FacialMetricSample(
            name="facial_search_p95_seconds",
            value=_nearest_rank_p95(durations),
            dimensions={"environment": environment, "type": "search", "state": "terminal"},
        )
    )
    overdue_references = int(
        db.scalar(
            select(func.count())
            .select_from(FacialSearchRequest)
            .where(
                FacialSearchRequest.reference_locator_ciphertext.is_not(None),
                FacialSearchRequest.expires_at <= observed_at,
            )
        )
        or 0
    )
    overdue_candidates = int(
        db.scalar(
            select(func.count())
            .select_from(FacialSearchCandidate)
            .where(FacialSearchCandidate.expires_at <= observed_at)
        )
        or 0
    )
    for metric_type, value in (
        ("reference", overdue_references),
        ("candidate", overdue_candidates),
    ):
        samples.append(
            FacialMetricSample(
                name="facial_retention_overdue_total",
                value=float(value),
                dimensions={"environment": environment, "type": metric_type, "state": "overdue"},
            )
        )
    for sample in samples:
        validate_observability_record(sample)
    return samples


def evaluate_facial_alerts(
    samples: list[FacialMetricSample],
    *,
    limits: FacialSloLimits = FACIAL_SLO_LIMITS,
    expected_enabled: bool | None = None,
) -> list[FacialAlert]:
    alerts: list[FacialAlert] = []
    for sample in samples:
        threshold: float | None = None
        if sample.name == "facial_queue_oldest_seconds":
            threshold = float(limits.queue_oldest_seconds)
        elif sample.name == "facial_admission_availability_percent":
            if sample.value < limits.admission_availability_percent:
                alert = FacialAlert(
                    name="facial_admission_availability_alert",
                    observed=sample.value,
                    threshold=limits.admission_availability_percent,
                    dimensions={**sample.dimensions, "state": "firing"},
                )
                validate_observability_record(alert)
                alerts.append(alert)
            continue
        elif sample.name == "facial_terminal_failure_percent":
            threshold = limits.terminal_failure_percent
        elif sample.name == "facial_search_p95_seconds":
            threshold = float(limits.search_p95_seconds)
        elif sample.name == "facial_retention_overdue_total":
            threshold = 0.0
        elif sample.name == "facial_cpu_percent":
            threshold = float(limits.cpu_percent_by_class[sample.dimensions["type"]])
        elif sample.name == "facial_memory_mib":
            threshold = float(limits.memory_mib_by_class[sample.dimensions["type"]])
        if threshold is not None and sample.value > threshold:
            alert = FacialAlert(
                name=sample.name.removesuffix("_total") + "_alert",
                observed=sample.value,
                threshold=threshold,
                dimensions={**sample.dimensions, "state": "firing"},
            )
            validate_observability_record(alert)
            alerts.append(alert)
    if expected_enabled is not None:
        runtime = next(
            (sample for sample in samples if sample.name == "facial_runtime_enabled"),
            None,
        )
        expected_value = float(expected_enabled)
        if runtime is None or runtime.value != expected_value:
            alert = FacialAlert(
                name="facial_runtime_state_alert",
                observed=runtime.value if runtime else -1.0,
                threshold=expected_value,
                dimensions=(
                    {**runtime.dimensions, "state": "firing"}
                    if runtime
                    else {
                        "environment": "development",
                        "type": "runtime",
                        "state": "firing",
                    }
                ),
            )
            validate_observability_record(alert)
            alerts.append(alert)
    return alerts
