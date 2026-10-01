import os
import time
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.capacity_observability import collector
from app.capacity_observability.contracts import UnavailableReason
from app.capacity_observability.database import read_postgres_snapshot


def _database_url() -> str:
    database_url = os.environ.get("PHOTOGRAPHER_TEST_DATABASE_URL") or os.environ.get("TENANT_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("URL PostgreSQL sintética ausente; não procurar servidores alternativos.")

    parsed = make_url(database_url)
    if (
        parsed.host not in {"127.0.0.1", "localhost", "::1"}
        or (parsed.port, parsed.database) not in {(55469, "pyp_tenant_test"), (15470, "pyp_photographer_test")}
    ):
        pytest.fail("Integração recusa conexão fora do PostgreSQL sintético local dedicado.")
    return database_url


@pytest.fixture
def postgres_engine():
    admin_engine = create_engine(_database_url(), isolation_level="AUTOCOMMIT", poolclass=NullPool)
    database = "capacity_" + uuid4().hex
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}"'))
    engine = create_engine(make_url(_database_url()).set(database=database), pool_size=1, max_overflow=0)
    statements = [
        """CREATE TABLE media_job (
            photo_asset_id uuid NOT NULL, kind varchar(32) NOT NULL,
            status varchar(16) NOT NULL, created_at timestamptz NOT NULL)""",
        "CREATE INDEX ix_capacity_media_job ON media_job (kind, status, created_at)",
        """CREATE TABLE photo_analysis (
            photo_asset_id uuid PRIMARY KEY, state varchar(24) NOT NULL)""",
        "CREATE INDEX ix_capacity_photo_analysis ON photo_analysis (photo_asset_id, state)",
        """CREATE TABLE preview_adjustment (
            photo_asset_id uuid PRIMARY KEY, status varchar(16) NOT NULL,
            updated_at timestamptz NOT NULL)""",
        "CREATE INDEX ix_capacity_preview_adjustment ON preview_adjustment (status, updated_at)",
        """CREATE TABLE facial_job (
            kind varchar(16) NOT NULL, status varchar(16) NOT NULL,
            available_at timestamptz NOT NULL, lease_expires_at timestamptz,
            created_at timestamptz NOT NULL)""",
        "CREATE INDEX ix_capacity_facial_job ON facial_job (kind, status, available_at)",
        "CREATE TABLE capacity_lock_probe (id integer PRIMARY KEY)",
        "INSERT INTO capacity_lock_probe VALUES (1)",
        """INSERT INTO media_job
            SELECT lpad(to_hex(gs), 32, '0')::uuid, 'generate_derivatives',
                   CASE WHEN gs % 7 = 0 THEN 'processing' ELSE 'queued' END,
                   now() - make_interval(secs => gs)
            FROM generate_series(1, 320) AS gs""",
        """INSERT INTO photo_analysis
            SELECT lpad(to_hex(gs), 32, '0')::uuid,
                   CASE WHEN gs % 10 = 0 THEN 'receiving' ELSE 'pending' END
            FROM generate_series(10, 320, 10) AS gs""",
        """INSERT INTO preview_adjustment
            SELECT lpad(to_hex(gs + 1000), 32, '0')::uuid,
                   CASE WHEN gs % 6 = 0 THEN 'processing' ELSE 'queued' END,
                   now() - make_interval(secs => gs)
            FROM generate_series(1, 240) AS gs""",
        """INSERT INTO facial_job
            SELECT CASE WHEN gs % 4 = 0 THEN 'cleanup'
                        WHEN gs % 3 = 0 THEN 'index' ELSE 'search' END,
                   CASE WHEN gs % 8 = 0 THEN 'processing' ELSE 'queued' END,
                   now() + make_interval(secs => CASE WHEN gs % 5 = 0 THEN gs ELSE -gs END),
                   CASE WHEN gs % 8 = 0 THEN now() - interval '1 second' ELSE NULL END,
                   now() - make_interval(secs => gs)
            FROM generate_series(1, 480) AS gs""",
    ]
    statements.extend([
        "CREATE TABLE tenant (id uuid PRIMARY KEY, status varchar(16) NOT NULL)",
        "INSERT INTO tenant VALUES ('00000000-0000-4000-8000-000000000001', 'active')",
    ])
    for table_name in ("media_job", "photo_analysis", "facial_job"):
        statements.extend([
            f"ALTER TABLE {table_name} ADD COLUMN tenant_id uuid",
            f"UPDATE {table_name} SET tenant_id='00000000-0000-4000-8000-000000000001'",
            f"ALTER TABLE {table_name} ALTER COLUMN tenant_id SET NOT NULL",
        ])
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    try:
        yield engine
    finally:
        with engine.begin() as connection:
            connection.execute(text(
                "DROP TABLE IF EXISTS capacity_lock_probe, facial_job, preview_adjustment, "
                "photo_analysis, media_job, tenant CASCADE"
            ))
        engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{database}"'))
        admin_engine.dispose()


def _patch_collector(monkeypatch, engine) -> None:
    monkeypatch.setattr(collector, "engine", engine)
    monkeypatch.setattr(collector, "SessionLocal", sessionmaker(bind=engine))
    collector.reset_cache_for_tests()


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)


def test_postgres_aggregates_execute_only_on_the_local_synthetic_ci_database(
    postgres_engine,
) -> None:
    engine = postgres_engine

    try:
        with engine.connect() as connection, connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SET LOCAL lock_timeout = '100ms'"))
            connection.execute(text("SET LOCAL statement_timeout = '500ms'"))
            result = read_postgres_snapshot(
                lambda statement: connection.execute(statement).mappings().one(),
                dialect_name=engine.dialect.name,
                instant=datetime.now(UTC),
            )
            assert result.database_client_connections.active.value is not None
            assert result.server_client_connections.active.value is not None
            assert result.max_connections.value is not None
            assert result.database_client_connections.active.value <= (
                result.server_client_connections.active.value
                + result.server_client_connections.idle.value
                + result.server_client_connections.idle_in_transaction.value
                + result.server_client_connections.other.value
                + result.server_client_connections.unknown.value
            )
            assert result.reserved_connections.value is not None
    finally:
        assert engine.pool.checkedout() == 0


def test_collector_uses_protected_fixed_queries_and_plans_on_synthetic_corpus(
    postgres_engine, monkeypatch,
) -> None:
    _patch_collector(monkeypatch, postgres_engine)
    trace: list[tuple[int, str, object]] = []

    def connection_id(connection) -> int:
        return id(connection.connection.driver_connection)

    def record_statement(connection, _cursor, statement, parameters, _context, _many):
        copied = dict(parameters) if isinstance(parameters, dict) else parameters
        trace.append((connection_id(connection), statement, copied))

    def record_begin(connection):
        trace.append((connection_id(connection), "<BEGIN>", None))

    def record_rollback(connection):
        trace.append((connection_id(connection), "<ROLLBACK>", None))

    event.listen(postgres_engine, "before_cursor_execute", record_statement)
    event.listen(postgres_engine, "begin", record_begin)
    event.listen(postgres_engine, "rollback", record_rollback)
    started = time.perf_counter()
    try:
        result = collector._collect_once()
    finally:
        elapsed = time.perf_counter() - started
        event.remove(postgres_engine, "before_cursor_execute", record_statement)
        event.remove(postgres_engine, "begin", record_begin)
        event.remove(postgres_engine, "rollback", record_rollback)

    selects = [item for item in trace if item[1].lstrip().upper().startswith("SELECT")]
    assert len(selects) == 5
    assert len(selects) <= 8
    assert len(result.queues) == 5
    assert {queue.queue_class for queue in result.queues} == {
        "media", "preview_adjustment", "search", "index", "maintenance"
    }
    assert result.database.database_client_connections.active.value is not None
    assert result.queues[0].queued_total.value > 0
    assert result.queues[1].queued_total.value > 0
    assert all("SELECT *" not in statement.upper() for _, statement, _ in selects)

    for position, (conn_id, statement, _parameters) in enumerate(trace):
        if not statement.lstrip().upper().startswith("SELECT"):
            continue
        last_begin = max(
            index for index in range(position + 1)
            if trace[index][0] == conn_id and trace[index][1] == "<BEGIN>"
        )
        transaction_statements = [
            item[1].upper() for item in trace[last_begin:position]
            if item[0] == conn_id
        ]
        assert any("SET TRANSACTION READ ONLY" in item for item in transaction_statements)
        assert any("SET LOCAL LOCK_TIMEOUT" in item for item in transaction_statements)
        assert any("SET LOCAL STATEMENT_TIMEOUT" in item for item in transaction_statements)

    raw = postgres_engine.raw_connection()
    try:
        cursor = raw.cursor()
        plans = []
        for _conn_id, statement, parameters in selects:
            cursor.execute("EXPLAIN (FORMAT JSON) " + statement, parameters)
            plan = cursor.fetchone()[0]
            assert isinstance(plan, list) and "Plan" in plan[0]
            plans.append(plan[0]["Plan"]["Node Type"])
        assert len(plans) == 5
    finally:
        raw.rollback()
        raw.close()

    assert postgres_engine.pool.checkedout() == 0
    assert elapsed < collector.COLLECTION_BUDGET_SECONDS
    print(f"capacity_postgres_synthetic_collection_seconds={elapsed:.6f}")


def test_read_session_enforces_timeouts_rolls_back_and_does_not_leak_settings(
    postgres_engine, monkeypatch,
) -> None:
    _patch_collector(monkeypatch, postgres_engine)

    started = time.perf_counter()
    with (
        pytest.raises(DBAPIError) as statement_failure,
        collector._read_session() as session,
    ):
        session.execute(text("SELECT pg_sleep(1)"))
    statement_elapsed = time.perf_counter() - started
    assert _sqlstate(statement_failure.value) == "57014"
    assert statement_elapsed < 1
    assert postgres_engine.pool.checkedout() == 0

    blocker_engine = create_engine(postgres_engine.url, poolclass=NullPool)
    try:
        with blocker_engine.connect() as blocker:
            transaction = blocker.begin()
            blocker.execute(text("LOCK TABLE capacity_lock_probe IN ACCESS EXCLUSIVE MODE"))
            started = time.perf_counter()
            with (
                pytest.raises(DBAPIError) as lock_failure,
                collector._read_session() as session,
            ):
                session.execute(text("SELECT count(*) FROM capacity_lock_probe"))
            lock_elapsed = time.perf_counter() - started
            transaction.rollback()
        assert _sqlstate(lock_failure.value) == "55P03"
        assert lock_elapsed < 1
    finally:
        blocker_engine.dispose()

    assert postgres_engine.pool.checkedout() == 0
    with postgres_engine.connect() as connection:
        settings = connection.execute(text("""
            SELECT current_setting('transaction_read_only'),
                   current_setting('lock_timeout'),
                   current_setting('statement_timeout')
        """)).one()
    assert tuple(settings) == ("off", "0", "0")


def test_permission_denial_is_sanitized_while_queue_sections_survive(
    postgres_engine, monkeypatch,
) -> None:
    role = "capacity_limited_" + uuid4().hex
    limited_url = postgres_engine.url.set(username=role, password="capacity-limited-only")
    with postgres_engine.begin() as connection:
        connection.execute(text(f"DROP ROLE IF EXISTS {role}"))
        connection.execute(text(
            f"CREATE ROLE {role} LOGIN PASSWORD 'capacity-limited-only'"
        ))
        connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        connection.execute(text(
            f"GRANT SELECT ON media_job, photo_analysis, preview_adjustment, facial_job, tenant TO {role}"
        ))
        connection.execute(text("REVOKE SELECT ON pg_catalog.pg_settings FROM PUBLIC"))

    limited_engine = create_engine(limited_url, pool_size=1, max_overflow=0)
    try:
        _patch_collector(monkeypatch, limited_engine)
        result = collector._collect_once()
        assert result.database.max_connections.value is None
        assert result.database.max_connections.reason is UnavailableReason.PERMISSION_DENIED
        assert result.queues[0].queued_total.value > 0
        assert result.queues[1].queued_total.value > 0
        assert UnavailableReason.PERMISSION_DENIED in result.limitations
        assert limited_engine.pool.checkedout() == 0
    finally:
        limited_engine.dispose()
        with postgres_engine.begin() as connection:
            connection.execute(text("GRANT SELECT ON pg_catalog.pg_settings TO PUBLIC"))
            connection.execute(text(f"DROP OWNED BY {role}"))
            connection.execute(text(f"DROP ROLE IF EXISTS {role}"))
