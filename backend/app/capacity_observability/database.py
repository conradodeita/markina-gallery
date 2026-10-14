"""Agregados sanitizados de conexões PostgreSQL sem ler identidades ou SQL."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime

from sqlalchemy import text

from app.capacity_observability.contracts import (
    ConnectionStates,
    DatabaseSnapshot,
    Evidence,
    MetricValue,
    Scope,
    Source,
    UnavailableReason,
    Unit,
    unavailable,
)

CONNECTIONS_QUERY = text("""
SELECT
  count(*) FILTER (WHERE datname = current_database())::integer AS db_total,
  count(*) FILTER (WHERE datname = current_database() AND state = 'active')::integer AS db_active,
  count(*) FILTER (WHERE datname = current_database() AND state = 'idle')::integer AS db_idle,
  count(*) FILTER (WHERE datname = current_database() AND state = 'idle in transaction')::integer AS db_idle_tx,
  count(*) FILTER (WHERE datname = current_database() AND state IS NOT NULL
                    AND state NOT IN ('active', 'idle', 'idle in transaction'))::integer AS db_other,
  count(*) FILTER (WHERE datname = current_database() AND state IS NULL)::integer AS db_unknown,
  count(*)::integer AS server_total,
  count(*) FILTER (WHERE state = 'active')::integer AS server_active,
  count(*) FILTER (WHERE state = 'idle')::integer AS server_idle,
  count(*) FILTER (WHERE state = 'idle in transaction')::integer AS server_idle_tx,
  count(*) FILTER (WHERE state IS NOT NULL
                    AND state NOT IN ('active', 'idle', 'idle in transaction'))::integer AS server_other,
  count(*) FILTER (WHERE state IS NULL)::integer AS server_unknown
FROM pg_stat_activity
WHERE backend_type = 'client backend'
""")

SETTINGS_QUERY = text("""
SELECT
  max(setting::integer) FILTER (WHERE name = 'max_connections') AS max_connections,
  max(setting::integer) FILTER (WHERE name = 'superuser_reserved_connections') AS superuser_reserved,
  max(setting::integer) FILTER (WHERE name = 'reserved_connections') AS reserved
FROM pg_settings
WHERE name IN ('max_connections', 'superuser_reserved_connections', 'reserved_connections')
""")


ReadQuery = Callable[[object], Mapping[str, object]]


def _metric(
    value: int | None,
    *,
    unit: Unit,
    scope: Scope,
    source: Source,
    instant: datetime,
    missing_reason: UnavailableReason = UnavailableReason.FIELD_UNAVAILABLE,
) -> MetricValue:
    if value is None:
        return unavailable(
            unit=unit,
            scope=scope,
            collected_at=instant,
            reason=missing_reason,
        )
    return MetricValue(
        value=int(value),
        unit=unit,
        evidence=Evidence.OBSERVED,
        scope=scope,
        source=source,
        collected_at=instant.astimezone(UTC),
    )


def _connection_states(
    row: Mapping[str, object], *, prefix: str, scope: Scope, instant: datetime
) -> ConnectionStates:
    names = {
        "active": f"{prefix}_active",
        "idle": f"{prefix}_idle",
        "idle_in_transaction": f"{prefix}_idle_tx",
        "other": f"{prefix}_other",
        "unknown": f"{prefix}_unknown",
    }
    return ConnectionStates(
        **{
            name: _metric(
                row.get(column),
                unit=Unit.CONNECTIONS,
                scope=scope,
                source=Source.PG_STAT_ACTIVITY,
                instant=instant,
            )
            for name, column in names.items()
        }
    )


def read_postgres_snapshot(
    read_query: ReadQuery, *, dialect_name: str, instant: datetime
) -> DatabaseSnapshot:
    """Lê duas agregações; o chamador fornece sessão/transação somente leitura."""
    if dialect_name != "postgresql":
        reason = UnavailableReason.UNSUPPORTED_BACKEND
        return DatabaseSnapshot(
            database_client_connections=_unavailable_states(
                Scope.APPLICATION_DATABASE, instant, reason
            ),
            server_client_connections=_unavailable_states(
                Scope.POSTGRESQL_SERVER, instant, reason
            ),
            max_connections=_unavailable_metric(Unit.CONNECTIONS, instant, reason),
            superuser_reserved_connections=_unavailable_metric(Unit.CONNECTIONS, instant, reason),
            reserved_connections=_unavailable_metric(Unit.CONNECTIONS, instant, reason),
        )

    connection_row = read_query(CONNECTIONS_QUERY)
    settings_row = read_query(SETTINGS_QUERY)
    return DatabaseSnapshot(
        database_client_connections=_connection_states(
            connection_row, prefix="db", scope=Scope.APPLICATION_DATABASE, instant=instant
        ),
        server_client_connections=_connection_states(
            connection_row, prefix="server", scope=Scope.POSTGRESQL_SERVER, instant=instant
        ),
        max_connections=_metric(
            settings_row.get("max_connections"),
            unit=Unit.CONNECTIONS,
            scope=Scope.POSTGRESQL_SERVER,
            source=Source.PG_SETTINGS,
            instant=instant,
        ),
        superuser_reserved_connections=_metric(
            settings_row.get("superuser_reserved"),
            unit=Unit.CONNECTIONS,
            scope=Scope.POSTGRESQL_SERVER,
            source=Source.PG_SETTINGS,
            instant=instant,
        ),
        reserved_connections=_metric(
            settings_row.get("reserved"),
            unit=Unit.CONNECTIONS,
            scope=Scope.POSTGRESQL_SERVER,
            source=Source.PG_SETTINGS,
            instant=instant,
        ),
    )


def _unavailable_metric(
    unit: Unit, instant: datetime, reason: UnavailableReason
) -> MetricValue:
    return unavailable(
        unit=unit,
        scope=Scope.POSTGRESQL_SERVER,
        collected_at=instant,
        reason=reason,
    )


def _unavailable_states(
    scope: Scope, instant: datetime, reason: UnavailableReason
) -> ConnectionStates:
    def item() -> MetricValue:
        return unavailable(
            unit=Unit.CONNECTIONS,
            scope=scope,
            collected_at=instant,
            reason=reason,
        )

    return ConnectionStates(
        active=item(),
        idle=item(),
        idle_in_transaction=item(),
        other=item(),
        unknown=item(),
    )
