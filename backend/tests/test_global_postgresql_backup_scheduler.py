from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import global_postgresql_backup_scheduler as scheduler
from app.auth import Base, GlobalPostgreSQLBackupRun
from app.global_postgresql_backup import (
    GlobalPostgreSQLBackupConfig,
    GlobalPostgreSQLBackupError,
    GlobalPostgreSQLBackupReceipt,
    GlobalPostgreSQLBackupRetentionReceipt,
)

_NOW = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
_CONFIG = GlobalPostgreSQLBackupConfig(
    repository="rclone:local:synthetic/global",
    restic_password_file=Path("/synthetic/restic-password"),
    rclone_config_file=Path("/synthetic/rclone.conf"),
    repository_root=Path("/repo"),
)


@pytest.fixture
def store(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'backup-state.sqlite3'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine, tables=[GlobalPostgreSQLBackupRun.__table__])
    yield engine, sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@contextmanager
def _available_lock(_engine):
    yield True


def _process(store, runner, *, at=_NOW, **kwargs):
    engine, session_factory = store
    return scheduler.process_scheduled_global_postgresql_backup(
        session_factory=session_factory,
        database_engine=engine,
        enabled=True,
        instant=at,
        clock=lambda: at + timedelta(seconds=2),
        config_loader=lambda: _CONFIG,
        database_url_loader=lambda: "postgresql://synthetic@app-db:5432/synthetic",
        backup_runner=runner,
        retention_runner=kwargs.get(
            "retention_runner",
            lambda _config, snapshot_id: GlobalPostgreSQLBackupRetentionReceipt(
                snapshot_id, 0
            ),
        ),
        snapshot_presence_checker=kwargs.get("snapshot_presence_checker", lambda *_: True),
        lock_provider=kwargs.get("lock_provider", _available_lock),
    )


def _rows(session_factory):
    with session_factory() as db:
        return list(db.scalars(select(GlobalPostgreSQLBackupRun)))


def test_disabled_gate_never_claims_or_calls_backup(store):
    engine, session_factory = store
    calls = []
    assert (
        scheduler.process_scheduled_global_postgresql_backup(
            session_factory=session_factory,
            database_engine=engine,
            enabled=False,
            backup_runner=lambda *_: calls.append("called"),
        )
        is False
    )
    assert calls == []
    assert _rows(session_factory) == []


def test_missing_environment_gate_is_disabled_by_default(store, monkeypatch):
    engine, session_factory = store
    calls = []
    monkeypatch.delenv("GLOBAL_POSTGRESQL_BACKUP_ENABLED", raising=False)

    assert (
        scheduler.process_scheduled_global_postgresql_backup(
            session_factory=session_factory,
            database_engine=engine,
            backup_runner=lambda *_: calls.append("called"),
        )
        is False
    )
    assert calls == []
    assert _rows(session_factory) == []


def test_success_is_persisted_once_per_utc_day_and_status_is_local(store, monkeypatch):
    _engine, session_factory = store
    calls = []
    receipt = GlobalPostgreSQLBackupReceipt("a" * 32, 1234, True)
    runner = lambda *_: calls.append("called") or receipt

    assert _process(store, runner) is True
    assert _process(store, runner) is False
    assert calls == ["called"]
    row = _rows(session_factory)[0]
    assert (row.scheduled_day, row.status, row.snapshot_id) == (
        date(2026, 11, 27),
        "validated",
        "a" * 32,
    )
    assert row.verified is True
    assert row.dump_size_bytes == 1234
    assert row.error_code is None
    assert row.retention_status == "complete"

    def no_execution(*_args, **_kwargs):
        raise AssertionError("status read attempted backup coordination")

    monkeypatch.setattr(scheduler, "_postgres_advisory_lock", no_execution)
    monkeypatch.setattr(scheduler, "_config_from_environment", no_execution)
    status = scheduler.read_global_postgresql_backup_status(session_factory=session_factory)
    assert status["status"] == "validated"
    assert status["snapshot_id"] == "a" * 32
    assert status["verified"] is True
    assert status["retention_status"] == "complete"


def test_retention_pending_is_persisted_before_runner_and_failure_keeps_verified_backup(store):
    _, session_factory = store
    receipt = GlobalPostgreSQLBackupReceipt("a" * 32, 1234, True)

    def fail_retention(_config, _snapshot_id):
        row = _rows(session_factory)[0]
        assert row.status == "validated"
        assert row.verified is True
        assert row.retention_status == "pending"
        raise GlobalPostgreSQLBackupError("retention_prune_failed")

    assert _process(
        store,
        lambda *_: receipt,
        retention_runner=fail_retention,
        snapshot_presence_checker=lambda _config, snapshot_id: snapshot_id == receipt.snapshot_id,
    )

    row = _rows(session_factory)[0]
    assert row.status == "validated"
    assert row.verified is True
    assert row.snapshot_id == receipt.snapshot_id
    assert row.retention_status == "failed"
    assert row.error_code == "retention_failed"


def test_retention_failure_without_proven_target_downgrades_backup_to_unknown(store):
    receipt = GlobalPostgreSQLBackupReceipt("b" * 32, 987, True)
    assert _process(
        store,
        lambda *_: receipt,
        retention_runner=lambda *_: (_ for _ in ()).throw(
            GlobalPostgreSQLBackupError("retention_result_unverified")
        ),
        snapshot_presence_checker=lambda *_: False,
    )
    row = _rows(store[1])[0]
    assert row.status == "unknown"
    assert row.verified is False
    assert row.snapshot_id is None
    assert row.dump_size_bytes is None
    assert row.retention_status == "failed"
    assert row.error_code == "retention_failed"
    assert scheduler.read_global_postgresql_backup_status(session_factory=store[1])[
        "last_validated"
    ] is None


def test_retention_failure_requires_boolean_presence_proof(store):
    receipt = GlobalPostgreSQLBackupReceipt("c" * 32, 456, True)
    assert _process(
        store,
        lambda *_: receipt,
        retention_runner=lambda *_: (_ for _ in ()).throw(
            GlobalPostgreSQLBackupError("retention_result_unverified")
        ),
        snapshot_presence_checker=lambda *_: "present",
    )

    row = _rows(store[1])[0]
    assert row.status == "unknown"
    assert row.verified is False
    assert row.snapshot_id is None
    assert row.retention_status == "failed"


def test_status_retains_latest_validated_receipt_after_a_later_failed_attempt(store):
    _, session_factory = store
    previous_day = _NOW.date() - timedelta(days=1)
    with session_factory() as db:
        db.add_all(
            [
                GlobalPostgreSQLBackupRun(
                    scheduled_day=previous_day,
                    status="validated",
                    started_at=_NOW - timedelta(days=1, seconds=2),
                    finished_at=_NOW - timedelta(days=1),
                    snapshot_id="e" * 32,
                    dump_size_bytes=2048,
                    duration_ms=2000,
                    verified=True,
                ),
                GlobalPostgreSQLBackupRun(
                    scheduled_day=_NOW.date(),
                    status="failed",
                    started_at=_NOW,
                    finished_at=_NOW,
                    verified=False,
                    error_code="tool_unavailable",
                ),
            ]
        )
        db.commit()

    status = scheduler.read_global_postgresql_backup_status(session_factory=session_factory)

    assert status["status"] == "failed"
    receipt = status["last_validated"]
    assert receipt["status"] == "validated"
    assert receipt["scheduled_day"] == previous_day.isoformat()
    assert datetime.fromisoformat(receipt["started_at"]).replace(tzinfo=UTC) == (
        _NOW - timedelta(days=1, seconds=2)
    )
    assert datetime.fromisoformat(receipt["finished_at"]).replace(tzinfo=UTC) == (
        _NOW - timedelta(days=1)
    )
    assert receipt["snapshot_id"] == "e" * 32
    assert receipt["dump_size_bytes"] == 2048
    assert receipt["duration_ms"] == 2000
    assert receipt["verified"] is True


def test_preflight_failure_is_failed_and_error_is_sanitized(store):
    def fail_before_remote(_database, _config):
        raise GlobalPostgreSQLBackupError("tool_version_mismatch")

    assert _process(store, fail_before_remote) is True
    row = _rows(store[1])[0]
    assert row.status == "failed"
    assert row.error_code == "tool_version_mismatch"
    assert row.snapshot_id is None
    assert row.verified is False


def test_post_start_uncertainty_is_not_retried_in_same_day(store):
    calls = []

    def uncertain(_database, _config):
        calls.append("called")
        raise GlobalPostgreSQLBackupError("snapshot_readback_failed")

    assert _process(store, uncertain) is True
    assert _process(store, uncertain) is False
    row = _rows(store[1])[0]
    assert calls == ["called"]
    assert row.status == "unknown"
    assert row.error_code == "snapshot_readback_failed"
    assert row.verified is False


def test_invalid_receipt_never_becomes_validated(store):
    invalid = GlobalPostgreSQLBackupReceipt("../unexpected", 12, True)
    assert _process(store, lambda *_: invalid) is True
    row = _rows(store[1])[0]
    assert row.status == "unknown"
    assert row.error_code == "backup_receipt_invalid"
    assert row.snapshot_id is None


def test_interrupted_same_day_run_becomes_unknown_without_retry(store):
    _, session_factory = store
    with session_factory() as db:
        db.add(
            GlobalPostgreSQLBackupRun(
                scheduled_day=_NOW.date(),
                status="running",
                started_at=_NOW - timedelta(minutes=4),
                verified=False,
            )
        )
        db.commit()

    calls = []
    assert _process(store, lambda *_: calls.append("called")) is False
    row = _rows(session_factory)[0]
    assert calls == []
    assert row.status == "unknown"
    assert row.error_code == "worker_interrupted"
    assert row.finished_at is not None


def test_interrupted_previous_day_is_reconciled_before_current_daily_claim(store):
    _, session_factory = store
    previous_day = _NOW.date() - timedelta(days=1)
    with session_factory() as db:
        db.add(
            GlobalPostgreSQLBackupRun(
                scheduled_day=previous_day,
                status="running",
                started_at=_NOW - timedelta(days=1),
                verified=False,
            )
        )
        db.commit()

    receipt = GlobalPostgreSQLBackupReceipt("b" * 32, 5678, True)
    assert _process(store, lambda *_: receipt) is True
    rows = sorted(_rows(session_factory), key=lambda row: row.scheduled_day)
    assert [(row.scheduled_day, row.status) for row in rows] == [
        (previous_day, "unknown"),
        (_NOW.date(), "validated"),
    ]
    assert rows[0].error_code == "worker_interrupted"


def test_concurrent_workers_claim_only_one_daily_backup(store):
    _, session_factory = store
    gate = threading.Lock()
    ready = threading.Barrier(2)
    calls = []
    outcomes = []

    @contextmanager
    def concurrent_lock(_engine):
        ready.wait(timeout=5)
        acquired = gate.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                gate.release()

    def runner(_database, _config):
        calls.append(threading.get_ident())
        time.sleep(0.05)
        return GlobalPostgreSQLBackupReceipt("c" * 32, 42, True)

    def invoke():
        outcomes.append(_process(store, runner, lock_provider=concurrent_lock))

    threads = [threading.Thread(target=invoke) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(outcomes) == [False, True]
    assert len(calls) == 1
    assert len(_rows(session_factory)) == 1
    assert _rows(session_factory)[0].status == "validated"


def test_state_constraint_rejects_unverified_success(store):
    _, session_factory = store
    with session_factory() as db:
        db.add(
            GlobalPostgreSQLBackupRun(
                scheduled_day=_NOW.date(),
                status="validated",
                started_at=_NOW,
                finished_at=_NOW,
                verified=False,
                snapshot_id="d" * 32,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_state_constraint_rejects_unknown_retention_status(store):
    _, session_factory = store
    with session_factory() as db:
        db.add(
            GlobalPostgreSQLBackupRun(
                scheduled_day=_NOW.date(),
                status="failed",
                started_at=_NOW,
                finished_at=_NOW,
                verified=False,
                retention_status="prune_everything",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_postgres_advisory_lock_holds_session_and_releases_fixed_key():
    class Result:
        def __init__(self, value):
            self.value = value

        def scalar_one(self):
            return self.value

    class Connection:
        def __init__(self):
            self.statements = []
            self.commits = 0
            self.closed = False

        def execute(self, statement, parameters):
            sql = str(statement)
            self.statements.append((sql, parameters))
            return Result("pg_try_advisory_lock" in sql or "pg_advisory_unlock" in sql)

        def commit(self):
            self.commits += 1

        def close(self):
            self.closed = True

    class Engine:
        dialect = type("Dialect", (), {"name": "postgresql"})()

        def __init__(self):
            self.connection = Connection()

        def connect(self):
            return self.connection

    database_engine = Engine()
    with scheduler._postgres_advisory_lock(database_engine) as acquired:
        assert acquired is True
        assert database_engine.connection.closed is False
        assert len(database_engine.connection.statements) == 1

    connection = database_engine.connection
    assert connection.closed is True
    assert connection.commits == 2
    assert [statement for statement, _ in connection.statements] == [
        "SELECT pg_try_advisory_lock(:lock_key)",
        "SELECT pg_advisory_unlock(:lock_key)",
    ]
    assert all(
        parameters == {"lock_key": scheduler._ADVISORY_LOCK_KEY}
        for _, parameters in connection.statements
    )
