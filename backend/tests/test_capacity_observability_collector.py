from __future__ import annotations

import threading
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.auth import Base, MediaJob
from app.capacity_observability import collector
from app.capacity_observability.contracts import UnavailableReason


@pytest.fixture
def isolated_collector(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    monkeypatch.setattr(collector, "engine", test_engine)
    monkeypatch.setattr(collector, "SessionLocal", sessionmaker(bind=test_engine))
    collector.reset_cache_for_tests()
    yield test_engine
    collector.reset_cache_for_tests()
    test_engine.dispose()


def test_collects_fixed_aggregates_and_marks_postgres_unavailable(isolated_collector):
    statements = []

    def record_select(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(isolated_collector, "before_cursor_execute", record_select)
    result = collector._collect_once()
    event.remove(isolated_collector, "before_cursor_execute", record_select)

    assert len(statements) == 3
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    assert all("SELECT *" not in statement.upper() for statement in statements)
    assert len(result.queues) == 5
    assert result.database.max_connections.reason is UnavailableReason.UNSUPPORTED_BACKEND
    assert {queue.queue_class for queue in result.queues} == {
        "media", "preview_adjustment", "search", "index", "maintenance"
    }
    assert result.connection_budget.potential_connections.value is None


def test_record_sentinels_are_not_projected_or_logged(isolated_collector, caplog):
    sentinel = "private-name phone token SELECT /secret biometric"
    job_id = uuid4()
    with collector.SessionLocal() as db:
        db.add(MediaJob(id=job_id, photo_asset_id=uuid4(), status="queued", attempts=2, last_error=sentinel))
        db.commit()
        before = db.get(MediaJob, job_id)
        before_state = (before.status, before.attempts, before.last_error)

    result = collector._collect_once()
    with collector.SessionLocal() as db:
        after = db.get(MediaJob, job_id)
        after_state = (after.status, after.attempts, after.last_error)
    assert result.queues[0].queued_total.value == 1
    assert after_state == before_state
    assert sentinel not in result.model_dump_json()
    assert sentinel not in caplog.text


def test_partial_source_error_is_sanitized_and_other_sections_survive(isolated_collector, monkeypatch, caplog):
    sentinel = "private-name phone token SELECT /secret biometric"

    def fail(_db, *, instant):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(collector, "collect_media_queue", fail)
    result = collector._collect_once()

    assert result.queues[0].queue_class == "media"
    assert result.queues[0].queued_total.reason is UnavailableReason.SOURCE_UNAVAILABLE
    assert result.queues[1].queued_total.value == 0
    assert sentinel not in result.model_dump_json()
    assert sentinel not in caplog.text


def test_cache_returns_fresh_copy_expires_and_marks_only_cached_copy(monkeypatch):
    first = Mock()
    first.model_copy.return_value = "cached"
    second = Mock()
    collect = Mock(side_effect=[first, second])
    monkeypatch.setattr(collector, "_collect_once", collect)
    ticks = iter([100.0, 100.0, 101.0, 132.0, 132.0])
    monkeypatch.setattr(collector.time, "monotonic", lambda: next(ticks))
    collector.reset_cache_for_tests()

    assert collector.get_capacity_snapshot() is first
    assert collector.get_capacity_snapshot() == "cached"
    assert collector.get_capacity_snapshot() is second
    assert collect.call_count == 2


def test_cache_is_lost_when_process_local_state_is_reset(isolated_collector):
    first = collector.get_capacity_snapshot()
    cached = collector.get_capacity_snapshot()
    assert cached.cached is True
    assert cached.collection_started_at == first.collection_started_at

    collector.reset_cache_for_tests()
    fresh = collector.get_capacity_snapshot()
    assert fresh.cached is False
    assert fresh.collection_started_at >= first.collection_started_at


def test_driver_codes_map_to_sanitized_allowlisted_reasons():
    class DriverFailure(Exception):
        def __init__(self, code):
            self.sqlstate = code

    assert collector._reason(DriverFailure("42501")) is UnavailableReason.PERMISSION_DENIED
    assert collector._reason(DriverFailure("57014")) is UnavailableReason.QUERY_TIMEOUT
    assert collector._reason(DriverFailure("55P03")) is UnavailableReason.QUERY_TIMEOUT
    assert collector._reason(DriverFailure("sentinel-private-text")) is UnavailableReason.SOURCE_UNAVAILABLE


def test_expired_cache_reports_busy_while_collection_runs(monkeypatch):
    first = Mock()
    first.model_copy.return_value = "cached"
    started = threading.Event()
    release = threading.Event()

    def slow_collection():
        started.set()
        assert release.wait(timeout=2)
        return first

    monkeypatch.setattr(collector, "_collect_once", slow_collection)
    monkeypatch.setattr(collector.time, "monotonic", lambda: 500.0)
    collector.reset_cache_for_tests()
    output = []
    thread = threading.Thread(target=lambda: output.append(collector.get_capacity_snapshot()))
    thread.start()
    assert started.wait(timeout=2)
    with pytest.raises(collector.CollectionBusy):
        collector.get_capacity_snapshot()
    release.set()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert output == [first]


def test_endpoint_authorizes_before_accessing_a_prefilled_cache(monkeypatch):
    forbidden = Mock()

    def deny(_request):
        raise HTTPException(status_code=403, detail="not authorized")

    monkeypatch.setattr(main, "require_admin", deny)
    monkeypatch.setattr(main, "get_capacity_snapshot", forbidden)
    response = Response()
    request = Request({"type": "http", "method": "GET", "path": "/admin/capacity-observability", "headers": [], "query_string": b"", "server": ("testserver", 80), "scheme": "http", "client": ("testclient", 12345), "root_path": ""})
    with pytest.raises(HTTPException) as denied:
        main.admin_capacity_observability(request, response)

    assert denied.value.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    forbidden.assert_not_called()


def test_authorized_endpoint_serializes_snapshot_without_storing(isolated_collector, monkeypatch):
    monkeypatch.setattr(main, "require_admin", lambda _request: object())
    monkeypatch.setattr(main, "get_capacity_snapshot", collector._collect_once)
    response = Response()
    request = Request({"type": "http", "method": "GET", "path": "/admin/capacity-observability", "headers": [], "query_string": b"", "server": ("testserver", 80), "scheme": "http", "client": ("testclient", 12345), "root_path": ""})
    snapshot = main.admin_capacity_observability(request, response)
    payload = jsonable_encoder(snapshot)

    assert response.headers["cache-control"] == "no-store"
    assert len(payload["queues"]) == 5
    assert payload["database"]["max_connections"]["value"] is None
