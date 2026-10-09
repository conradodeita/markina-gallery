from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.capacity_observability.contracts import (
    CapacitySnapshot,
    Evidence,
    MetricValue,
    PoolSnapshot,
    Scope,
    Source,
    UnavailableReason,
    Unit,
    unavailable,
)

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def test_metric_value_distinguishes_observed_and_unavailable() -> None:
    observed = MetricValue(
        value=0,
        unit=Unit.JOBS,
        evidence=Evidence.OBSERVED,
        scope=Scope.APPLICATION_DATABASE,
        source=Source.FACIAL_JOB,
        collected_at=NOW,
    )
    missing = unavailable(
        unit=Unit.CONNECTIONS,
        scope=Scope.POSTGRESQL_SERVER,
        collected_at=NOW,
        reason=UnavailableReason.PERMISSION_DENIED,
    )
    assert observed.value == 0
    assert observed.evidence is Evidence.OBSERVED
    assert missing.value is None
    assert missing.evidence is Evidence.UNAVAILABLE
    assert missing.reason is UnavailableReason.PERMISSION_DENIED


def test_contract_rejects_naive_timestamps_unknown_fields_and_nonfinite_numbers() -> None:
    with pytest.raises(ValidationError):
        MetricValue(
            value=1,
            unit=Unit.JOBS,
            evidence=Evidence.OBSERVED,
            scope=Scope.APPLICATION_DATABASE,
            source=Source.FACIAL_JOB,
            collected_at=datetime.fromisoformat("2026-09-30"),
        )
    with pytest.raises(ValidationError):
        MetricValue(
            value=float("nan"),
            unit=Unit.SECONDS,
            evidence=Evidence.OBSERVED,
            scope=Scope.APPLICATION_DATABASE,
            source=Source.FACIAL_JOB,
            collected_at=NOW,
        )
    with pytest.raises(ValidationError):
        MetricValue(
            value=None,
            unit=Unit.JOBS,
            evidence=Evidence.OBSERVED,
            scope=Scope.APPLICATION_DATABASE,
            source=Source.FACIAL_JOB,
            collected_at=NOW,
        )
    with pytest.raises(ValidationError):
        MetricValue(
            value=1,
            unit=Unit.JOBS,
            evidence=Evidence.OBSERVED,
            scope=Scope.APPLICATION_DATABASE,
            source=Source.FACIAL_JOB,
            collected_at=NOW,
            extra_sensitive_field="phone",
        )


def test_pool_schema_keeps_wait_and_timeout_unavailable() -> None:
    unavailable_count = unavailable(
        unit=Unit.CONNECTIONS,
        scope=Scope.RESPONDING_API_PROCESS,
        collected_at=NOW,
        reason=UnavailableReason.FIELD_UNAVAILABLE,
    )
    unavailable_wait = unavailable(
        unit=Unit.SECONDS,
        scope=Scope.RESPONDING_API_PROCESS,
        collected_at=NOW,
        reason=UnavailableReason.FIELD_UNAVAILABLE,
    )
    pool = PoolSnapshot(
        pool_class="queue_pool",
        finite_limit=True,
        unbounded_overflow=False,
        base_size=MetricValue(value=5, unit=Unit.CONNECTIONS, evidence=Evidence.OBSERVED,
                              scope=Scope.RESPONDING_API_PROCESS, source=Source.SQLALCHEMY_POOL,
                              collected_at=NOW),
        max_overflow=MetricValue(value=10, unit=Unit.CONNECTIONS, evidence=Evidence.OBSERVED,
                                 scope=Scope.RESPONDING_API_PROCESS, source=Source.SQLALCHEMY_POOL,
                                 collected_at=NOW),
        potential_max=MetricValue(value=15, unit=Unit.CONNECTIONS, evidence=Evidence.CALCULATED,
                                  scope=Scope.RESPONDING_API_PROCESS, source=Source.SQLALCHEMY_POOL,
                                  collected_at=NOW),
        acquisition_timeout_seconds=MetricValue(value=30, unit=Unit.SECONDS, evidence=Evidence.OBSERVED,
                                                scope=Scope.RESPONDING_API_PROCESS, source=Source.SQLALCHEMY_POOL,
                                                collected_at=NOW),
        checked_in=MetricValue(value=0, unit=Unit.CONNECTIONS, evidence=Evidence.OBSERVED,
                               scope=Scope.RESPONDING_API_PROCESS, source=Source.SQLALCHEMY_POOL,
                               collected_at=NOW),
        checked_out=MetricValue(value=0, unit=Unit.CONNECTIONS, evidence=Evidence.OBSERVED,
                                scope=Scope.RESPONDING_API_PROCESS, source=Source.SQLALCHEMY_POOL,
                                collected_at=NOW),
        open_connections_estimate=MetricValue(value=0, unit=Unit.CONNECTIONS,
                                              evidence=Evidence.CALCULATED,
                                              scope=Scope.RESPONDING_API_PROCESS,
                                              source=Source.SQLALCHEMY_POOL, collected_at=NOW),
        wait_seconds=unavailable_wait,
        timeout_count=unavailable_count,
    )
    assert pool.potential_max.value == pool.base_size.value + pool.max_overflow.value
    assert pool.wait_seconds.value is None


def test_closed_snapshot_rejects_negative_duration_window() -> None:
    with pytest.raises(ValidationError):
        CapacitySnapshot.model_validate({
            "schema_version": 1,
            "collection_started_at": NOW,
            "collection_finished_at": datetime(2026, 9, 30, 11, 0, tzinfo=UTC),
            "cached": False,
            "database": {},
            "pool": {},
            "queues": [],
            "connection_budget": {},
            "coverage": [],
            "limitations": [],
        })
