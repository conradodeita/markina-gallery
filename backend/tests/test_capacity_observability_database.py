from datetime import UTC, datetime

from sqlalchemy import TextClause

from app.capacity_observability.contracts import Scope, UnavailableReason
from app.capacity_observability.database import read_postgres_snapshot

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def test_postgres_snapshot_separates_database_and_server_scopes_and_reservations() -> None:
    statements: list[TextClause] = []

    def read(query: TextClause):
        statements.append(query)
        if "pg_stat_activity" in str(query):
            return {
                "db_total": 3,
                "db_active": 1,
                "db_idle": 1,
                "db_idle_tx": 0,
                "db_other": 0,
                "db_unknown": 1,
                "server_total": 8,
                "server_active": 2,
                "server_idle": 4,
                "server_idle_tx": 1,
                "server_other": 0,
                "server_unknown": 1,
            }
        return {"max_connections": 100, "superuser_reserved": 3, "reserved": 2}

    snapshot = read_postgres_snapshot(read, dialect_name="postgresql", instant=NOW)
    assert len(statements) == 2
    assert snapshot.database_client_connections.unknown.value == 1
    assert snapshot.server_client_connections.active.value == 2
    assert snapshot.database_client_connections.active.scope is Scope.APPLICATION_DATABASE
    assert snapshot.server_client_connections.active.scope is Scope.POSTGRESQL_SERVER
    assert snapshot.max_connections.value == 100
    assert snapshot.superuser_reserved_connections.value == 3
    assert snapshot.reserved_connections.value == 2


def test_missing_server_reserved_setting_is_unavailable_not_zero() -> None:
    def read(query: TextClause):
        if "pg_stat_activity" in str(query):
            return {"db_active": 0, "server_active": 0}
        return {"max_connections": 100, "superuser_reserved": 3, "reserved": None}

    snapshot = read_postgres_snapshot(read, dialect_name="postgresql", instant=NOW)
    assert snapshot.database_client_connections.active.value == 0
    assert snapshot.database_client_connections.idle.value is None
    assert snapshot.database_client_connections.idle.reason is UnavailableReason.FIELD_UNAVAILABLE
    assert snapshot.reserved_connections.value is None
    assert snapshot.reserved_connections.reason is UnavailableReason.FIELD_UNAVAILABLE


def test_non_postgresql_backend_is_unavailable_without_running_queries() -> None:
    called = False

    def read(_query):
        nonlocal called
        called = True
        raise AssertionError("não deve consultar backend não suportado")

    snapshot = read_postgres_snapshot(read, dialect_name="sqlite", instant=NOW)
    assert called is False
    assert snapshot.database_client_connections.active.reason is UnavailableReason.UNSUPPORTED_BACKEND
    assert snapshot.max_connections.value is None
