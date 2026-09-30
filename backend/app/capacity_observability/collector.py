"""Coleta local, autorizada e limitada do diagnóstico de capacidade."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.auth import SessionLocal, engine
from app.capacity_observability.budget import unavailable_connection_budget
from app.capacity_observability.contracts import (
    CapacitySnapshot,
    ConnectionStates,
    DatabaseSnapshot,
    MetricValue,
    QueueSnapshot,
    Scope,
    UnavailableReason,
    Unit,
    unavailable,
)
from app.capacity_observability.database import read_postgres_snapshot
from app.capacity_observability.pool import describe_pool
from app.capacity_observability.queues import (
    QUEUE_CLASSES,
    collect_adjustment_queue,
    collect_facial_queues,
    collect_media_queue,
)

CACHE_TTL_SECONDS = 30.0
COLLECTION_BUDGET_SECONDS = 2.0
STATEMENT_LIMIT_MS = 500
LOCK_LIMIT_MS = 100
_cache_lock = threading.Lock()
_cached: tuple[float, CapacitySnapshot] | None = None
_collecting = False


class CollectionBusy(Exception):
    """Há uma coleta em andamento e nenhum snapshot ainda válido."""


def _unavailable_metric(unit: Unit, scope: Scope, instant: datetime, reason: UnavailableReason) -> MetricValue:
    return unavailable(unit=unit, scope=scope, collected_at=instant, reason=reason)


def _unavailable_database(instant: datetime, reason: UnavailableReason) -> DatabaseSnapshot:
    def states(scope: Scope) -> ConnectionStates:
        def metric() -> MetricValue:
            return _unavailable_metric(Unit.CONNECTIONS, scope, instant, reason)

        return ConnectionStates(
            active=metric(), idle=metric(), idle_in_transaction=metric(),
            other=metric(), unknown=metric(),
        )

    return DatabaseSnapshot(
        database_client_connections=states(Scope.APPLICATION_DATABASE),
        server_client_connections=states(Scope.POSTGRESQL_SERVER),
        max_connections=_unavailable_metric(Unit.CONNECTIONS, Scope.POSTGRESQL_SERVER, instant, reason),
        superuser_reserved_connections=_unavailable_metric(Unit.CONNECTIONS, Scope.POSTGRESQL_SERVER, instant, reason),
        reserved_connections=_unavailable_metric(Unit.CONNECTIONS, Scope.POSTGRESQL_SERVER, instant, reason),
    )


def _unavailable_queue(queue_class: str, instant: datetime, reason: UnavailableReason) -> QueueSnapshot:
    def metric(unit: Unit = Unit.JOBS) -> MetricValue:
        return _unavailable_metric(unit, Scope.APPLICATION_DATABASE, instant, reason)

    return QueueSnapshot(
        queue_class=queue_class,
        queued_total=metric(), scheduled_total=metric(), claim_candidates_total=metric(),
        processing_total=metric(), blocked_dependency_total=metric(), reclaimable_total=metric(),
        oldest_record_age_seconds=metric(Unit.SECONDS), oldest_due_age_seconds=metric(Unit.SECONDS),
        oldest_updated_age_seconds=metric(Unit.SECONDS), wait_semantics="exact_wait_unavailable",
    )


def _reason(error: BaseException) -> UnavailableReason:
    """Classifica sem propagar mensagem, SQL, parâmetros ou dados do driver."""
    original = error.orig if isinstance(error, DBAPIError) else error
    code = getattr(original, "pgcode", None) or getattr(original, "sqlstate", None)
    if code == "42501":
        return UnavailableReason.PERMISSION_DENIED
    if code in {"57014", "55P03"}:
        return UnavailableReason.QUERY_TIMEOUT
    return UnavailableReason.SOURCE_UNAVAILABLE


def _timeout_error() -> RuntimeError:
    return RuntimeError("diagnostic_deadline")


@contextmanager
def _read_session(on_connection: Callable[[], None] | None = None) -> Iterator[Session]:
    with SessionLocal() as db:
        if engine.dialect.name == "postgresql":
            db.connection()  # acquire using the existing pool before starting the collection budget
            if on_connection is not None:
                on_connection()
            db.execute(text("SET TRANSACTION READ ONLY"))
            db.execute(text(f"SET LOCAL lock_timeout = '{LOCK_LIMIT_MS}ms'"))
            db.execute(text(f"SET LOCAL statement_timeout = '{STATEMENT_LIMIT_MS}ms'"))
        yield db
        db.rollback()


def _collect_once() -> CapacitySnapshot:
    started = datetime.now(UTC)
    deadline: list[float | None] = [None]

    def start_budget() -> None:
        if deadline[0] is None:
            deadline[0] = time.monotonic() + COLLECTION_BUDGET_SECONDS

    def remaining_ms() -> int:
        start_budget()
        return int((deadline[0] - time.monotonic()) * 1000)

    instant = started
    limitations: list[UnavailableReason] = []
    pool = describe_pool(engine.pool, instant)
    database = _unavailable_database(instant, UnavailableReason.UNSUPPORTED_BACKEND)
    queue_snapshots = {name: _unavailable_queue(name, instant, UnavailableReason.SOURCE_UNAVAILABLE) for name in QUEUE_CLASSES}

    if engine.dialect.name == "postgresql":
        try:
            with _read_session(start_budget) as db:
                def read_query(statement: object):
                    remaining = remaining_ms()
                    if remaining <= 0:
                        raise _timeout_error()
                    db.execute(text(f"SET LOCAL statement_timeout = '{min(STATEMENT_LIMIT_MS, remaining)}ms'"))
                    return db.execute(statement).mappings().one()

                database = read_postgres_snapshot(read_query, dialect_name=engine.dialect.name, instant=instant)
        # Section boundaries intentionally sanitize failures instead of logging driver text.
        except Exception as exc:  # noqa: BLE001
            reason = UnavailableReason.QUERY_TIMEOUT if str(exc) == "diagnostic_deadline" else _reason(exc)
            if deadline[0] is None:
                deadline[0] = time.monotonic()
            database = _unavailable_database(instant, reason)
            limitations.append(reason)
    else:
        database = read_postgres_snapshot(lambda _query: {}, dialect_name=engine.dialect.name, instant=instant)
        limitations.append(UnavailableReason.UNSUPPORTED_BACKEND)
        start_budget()

    for section in ("facial", "media", "adjustment"):
        if deadline[0] is not None and time.monotonic() >= deadline[0]:
            reason = UnavailableReason.QUERY_TIMEOUT
            limitations.append(reason)
            break
        try:
            with _read_session(start_budget) as db:
                # Each section owns a short transaction, so a failed section cannot poison the next one.
                if engine.dialect.name == "postgresql":
                    remaining = remaining_ms()
                    if remaining <= 0:
                        raise _timeout_error()
                    db.execute(text(f"SET LOCAL statement_timeout = '{min(STATEMENT_LIMIT_MS, remaining)}ms'"))
                names = {
                    "facial": ("search", "index", "maintenance"),
                    "media": ("media",),
                    "adjustment": ("preview_adjustment",),
                }[section]
                if section == "facial":
                    rows = collect_facial_queues(db, instant=instant)
                elif section == "media":
                    rows = [collect_media_queue(db, instant=instant)]
                else:
                    rows = [collect_adjustment_queue(db, instant=instant)]
                queue_snapshots.update({item.queue_class: item for item in rows})
        # Section boundaries intentionally sanitize failures instead of logging driver text.
        except Exception as exc:  # noqa: BLE001
            reason = UnavailableReason.QUERY_TIMEOUT if str(exc) == "diagnostic_deadline" else _reason(exc)
            names = {
                "facial": ("search", "index", "maintenance"),
                "media": ("media",),
                "adjustment": ("preview_adjustment",),
            }[section]
            queue_snapshots.update({name: _unavailable_queue(name, instant, reason) for name in names})
            limitations.append(reason)
            # Continue only with independent sections while there is time.

    finished = datetime.now(UTC)
    return CapacitySnapshot(
        collection_started_at=started,
        collection_finished_at=finished,
        cached=False,
        database=database,
        pool=pool,
        queues=[queue_snapshots[name] for name in QUEUE_CLASSES],
        connection_budget=unavailable_connection_budget(finished),
        coverage=list(QUEUE_CLASSES),
        limitations=list(dict.fromkeys(limitations)),
    )


def get_capacity_snapshot() -> CapacitySnapshot:
    """Retorna cache fresco ou inicia no máximo uma coleta neste processo."""
    global _cached, _collecting
    now_mono = time.monotonic()
    with _cache_lock:
        if _cached is not None and now_mono - _cached[0] < CACHE_TTL_SECONDS:
            return _cached[1].model_copy(update={"cached": True})
        if _collecting:
            raise CollectionBusy
        _collecting = True
    try:
        snapshot = _collect_once()
        with _cache_lock:
            _cached = (time.monotonic(), snapshot)
        return snapshot
    finally:
        with _cache_lock:
            _collecting = False


def reset_cache_for_tests() -> None:
    global _cached, _collecting
    with _cache_lock:
        _cached = None
        _collecting = False
