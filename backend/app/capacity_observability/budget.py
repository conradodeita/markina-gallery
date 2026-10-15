"""Orçamento potencial: indisponível até inventário global aprovado."""

from datetime import datetime

from app.capacity_observability.contracts import (
    ConnectionBudgetSnapshot,
    Scope,
    UnavailableReason,
    Unit,
    unavailable,
)

BUDGET_LIMITATIONS = [
    UnavailableReason.PROCESS_INVENTORY_MISSING,
    UnavailableReason.EXTERNAL_CONSUMERS_UNKNOWN,
    UnavailableReason.OPERATIONAL_RESERVE_UNAPPROVED,
]


def unavailable_connection_budget(instant: datetime) -> ConnectionBudgetSnapshot:
    """Não estima o orçamento a partir de um processo ou de limites do servidor."""
    return ConnectionBudgetSnapshot(
        status="unavailable",
        potential_connections=unavailable(
            unit=Unit.CONNECTIONS,
            scope=Scope.POSTGRESQL_SERVER,
            collected_at=instant,
            reason=UnavailableReason.PROCESS_INVENTORY_MISSING,
        ),
        budget_headroom=unavailable(
            unit=Unit.CONNECTIONS,
            scope=Scope.POSTGRESQL_SERVER,
            collected_at=instant,
            reason=UnavailableReason.PROCESS_INVENTORY_MISSING,
        ),
        limitations=list(BUDGET_LIMITATIONS),
    )
