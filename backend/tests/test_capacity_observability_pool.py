from datetime import UTC, datetime

from sqlalchemy.pool import NullPool, QueuePool, StaticPool

from app.capacity_observability.contracts import Evidence, UnavailableReason
from app.capacity_observability.pool import describe_pool

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


class RawConnection:
    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


def _queue_pool(*, size: int = 2, max_overflow: int = 3) -> QueuePool:
    return QueuePool(lambda: RawConnection(), pool_size=size, max_overflow=max_overflow, timeout=7)


def test_finite_queue_pool_reports_limit_and_current_occupancy_without_checkout() -> None:
    pool = _queue_pool()
    snapshot = describe_pool(pool, NOW)
    assert snapshot.pool_class == "queue_pool"
    assert snapshot.finite_limit is True
    assert snapshot.unbounded_overflow is False
    assert snapshot.base_size.value == 2
    assert snapshot.max_overflow.value == 3
    assert snapshot.potential_max.value == 5
    assert snapshot.acquisition_timeout_seconds.value == 7
    assert snapshot.checked_in.value == 0
    assert snapshot.checked_out.value == 0
    assert snapshot.open_connections_estimate.value == 0
    assert snapshot.wait_seconds.reason is UnavailableReason.FIELD_UNAVAILABLE
    assert pool.checkedout() == 0


def test_queue_pool_occupancy_is_sampled_and_released() -> None:
    pool = _queue_pool(size=1, max_overflow=0)
    connection = pool.connect()
    try:
        snapshot = describe_pool(pool, NOW)
        assert snapshot.checked_out.value == 1
        assert snapshot.open_connections_estimate.value == 1
        assert snapshot.open_connections_estimate.evidence is Evidence.CALCULATED
    finally:
        connection.close()


def test_unlimited_overflow_has_no_finite_potential_maximum() -> None:
    snapshot = describe_pool(_queue_pool(max_overflow=-1), NOW)
    assert snapshot.finite_limit is False
    assert snapshot.unbounded_overflow is True
    assert snapshot.max_overflow.value is None
    assert snapshot.potential_max.value is None


def test_zero_size_pool_and_unsupported_pool_kinds_are_explicit() -> None:
    zero = describe_pool(_queue_pool(size=0, max_overflow=2), NOW)
    assert zero.base_size.value == 0
    assert zero.finite_limit is False
    assert zero.unbounded_overflow is True
    assert zero.potential_max.value is None

    no_pool = describe_pool(NullPool(lambda: RawConnection()), NOW)
    assert no_pool.pool_class == "null_pool"
    assert no_pool.potential_max.value is None

    other = describe_pool(StaticPool(lambda: RawConnection()), NOW)
    assert other.pool_class == "other"
    assert other.potential_max.value is None


def test_missing_pool_configuration_is_reported_without_inventing_limit() -> None:
    pool = _queue_pool()
    pool._max_overflow = None
    snapshot = describe_pool(pool, NOW)
    assert snapshot.pool_class == "queue_pool"
    assert snapshot.checked_out.value == 0
    assert snapshot.potential_max.value is None
    assert snapshot.finite_limit is False
