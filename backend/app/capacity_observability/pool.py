"""Leitura local do pool SQLAlchemy da API; sem criar conexões."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.pool import NullPool, QueuePool

from app.capacity_observability.contracts import (
    Evidence,
    MetricValue,
    PoolSnapshot,
    Scope,
    Source,
    UnavailableReason,
    Unit,
    unavailable,
)


def _observed(value: float, unit: Unit, instant: datetime) -> MetricValue:
    return MetricValue(
        value=value,
        unit=unit,
        evidence=Evidence.OBSERVED,
        scope=Scope.RESPONDING_API_PROCESS,
        source=Source.SQLALCHEMY_POOL,
        collected_at=instant.astimezone(UTC),
    )


def _calculated(value: float, unit: Unit, instant: datetime) -> MetricValue:
    return MetricValue(
        value=value,
        unit=unit,
        evidence=Evidence.CALCULATED,
        scope=Scope.RESPONDING_API_PROCESS,
        source=Source.SQLALCHEMY_POOL,
        collected_at=instant.astimezone(UTC),
    )


def _missing(unit: Unit, instant: datetime) -> MetricValue:
    return unavailable(
        unit=unit,
        scope=Scope.RESPONDING_API_PROCESS,
        collected_at=instant,
        reason=UnavailableReason.UNSUPPORTED_POOL,
    )


def _unavailable_field(unit: Unit, instant: datetime) -> MetricValue:
    return unavailable(
        unit=unit,
        scope=Scope.RESPONDING_API_PROCESS,
        collected_at=instant,
        reason=UnavailableReason.FIELD_UNAVAILABLE,
    )


def describe_pool(pool: Any, instant: datetime) -> PoolSnapshot:
    """Descreve configurações e ocupação atual; nunca adquire uma conexão."""
    unsupported = lambda unit: _missing(unit, instant)
    if isinstance(pool, QueuePool):
        checked_in = pool.checkedin()
        checked_out = pool.checkedout()
        raw_size = pool.size()
        raw_overflow = getattr(pool, "_max_overflow", None)
        raw_timeout = getattr(pool, "_timeout", None)
        if (
            not isinstance(raw_size, int)
            or raw_size < 0
            or not isinstance(raw_overflow, int)
            or not isinstance(raw_timeout, (int, float))
        ):
            return PoolSnapshot(
                pool_class="queue_pool",
                finite_limit=False,
                unbounded_overflow=False,
                base_size=unsupported(Unit.CONNECTIONS),
                max_overflow=unsupported(Unit.CONNECTIONS),
                potential_max=unsupported(Unit.CONNECTIONS),
                acquisition_timeout_seconds=unsupported(Unit.SECONDS),
                checked_in=_observed(checked_in, Unit.CONNECTIONS, instant),
                checked_out=_observed(checked_out, Unit.CONNECTIONS, instant),
                open_connections_estimate=_calculated(
                    checked_in + checked_out, Unit.CONNECTIONS, instant
                ),
                wait_seconds=_unavailable_field(Unit.SECONDS, instant),
                timeout_count=_unavailable_field(Unit.CONNECTIONS, instant),
            )
        unbounded = raw_overflow < 0
        return PoolSnapshot(
            pool_class="queue_pool",
            finite_limit=not unbounded,
            unbounded_overflow=unbounded,
            base_size=_observed(raw_size, Unit.CONNECTIONS, instant),
            max_overflow=(
                _unavailable_field(Unit.CONNECTIONS, instant)
                if unbounded
                else _observed(raw_overflow, Unit.CONNECTIONS, instant)
            ),
            potential_max=(
                _unavailable_field(Unit.CONNECTIONS, instant)
                if unbounded
                else _calculated(raw_size + raw_overflow, Unit.CONNECTIONS, instant)
            ),
            acquisition_timeout_seconds=_observed(
                max(0, raw_timeout), Unit.SECONDS, instant
            ),
            checked_in=_observed(checked_in, Unit.CONNECTIONS, instant),
            checked_out=_observed(checked_out, Unit.CONNECTIONS, instant),
            open_connections_estimate=_calculated(
                checked_in + checked_out, Unit.CONNECTIONS, instant
            ),
            wait_seconds=_unavailable_field(Unit.SECONDS, instant),
            timeout_count=_unavailable_field(Unit.CONNECTIONS, instant),
        )
    if isinstance(pool, NullPool):
        return PoolSnapshot(
            pool_class="null_pool",
            finite_limit=False,
            unbounded_overflow=False,
            base_size=unsupported(Unit.CONNECTIONS),
            max_overflow=unsupported(Unit.CONNECTIONS),
            potential_max=unsupported(Unit.CONNECTIONS),
            acquisition_timeout_seconds=unsupported(Unit.SECONDS),
            checked_in=unsupported(Unit.CONNECTIONS),
            checked_out=unsupported(Unit.CONNECTIONS),
            open_connections_estimate=unsupported(Unit.CONNECTIONS),
            wait_seconds=unsupported(Unit.SECONDS),
            timeout_count=unsupported(Unit.CONNECTIONS),
        )
    return PoolSnapshot(
        pool_class="other",
        finite_limit=False,
        unbounded_overflow=False,
        base_size=unsupported(Unit.CONNECTIONS),
        max_overflow=unsupported(Unit.CONNECTIONS),
        potential_max=unsupported(Unit.CONNECTIONS),
        acquisition_timeout_seconds=unsupported(Unit.SECONDS),
        checked_in=unsupported(Unit.CONNECTIONS),
        checked_out=unsupported(Unit.CONNECTIONS),
        open_connections_estimate=unsupported(Unit.CONNECTIONS),
        wait_seconds=unsupported(Unit.SECONDS),
        timeout_count=unsupported(Unit.CONNECTIONS),
    )
