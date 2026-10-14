from datetime import UTC, datetime

from app.capacity_observability.budget import unavailable_connection_budget
from app.capacity_observability.contracts import UnavailableReason


def test_budget_stays_unavailable_with_all_required_inventory_gaps() -> None:
    snapshot = unavailable_connection_budget(datetime(2026, 9, 30, tzinfo=UTC))
    assert snapshot.status == "unavailable"
    assert snapshot.potential_connections.value is None
    assert snapshot.budget_headroom.value is None
    assert snapshot.limitations == [
        UnavailableReason.PROCESS_INVENTORY_MISSING,
        UnavailableReason.EXTERNAL_CONSUMERS_UNKNOWN,
        UnavailableReason.OPERATIONAL_RESERVE_UNAPPROVED,
    ]
