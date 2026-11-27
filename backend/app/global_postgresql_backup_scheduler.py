"""Agendamento diário e estado sanitizado do backup PostgreSQL global."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import (
    GlobalPostgreSQLBackupRun,
    SessionLocal,
    database_url,
    engine,
    now,
)
from app.global_postgresql_backup import (
    GlobalPostgreSQLBackupConfig,
    GlobalPostgreSQLBackupError,
    GlobalPostgreSQLBackupReceipt,
    create_global_postgresql_backup,
)

_LOGGER = logging.getLogger("app.global_postgresql_backup")
_ADVISORY_LOCK_KEY = 5_795_187_095_217_168_897
_SAFE_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PREFLIGHT_FAILURES = frozenset(
    {
        "configuration_invalid",
        "tool_unavailable",
        "tool_version_unverified",
        "tool_version_mismatch",
        "database_configuration_invalid",
        "database_credentials_permissions_unverified",
    }
)


def _safe_error_code(value: object) -> str:
    return (
        value
        if isinstance(value, str) and _SAFE_ERROR_CODE.fullmatch(value)
        else "backup_operation_failed"
    )


def _enabled_from_environment() -> bool:
    return os.getenv("GLOBAL_POSTGRESQL_BACKUP_ENABLED", "false").strip().lower() == "true"


def _config_from_environment() -> GlobalPostgreSQLBackupConfig:
    names = (
        "GLOBAL_POSTGRESQL_BACKUP_REPOSITORY",
        "GLOBAL_POSTGRESQL_BACKUP_RESTIC_PASSWORD_FILE",
        "GLOBAL_POSTGRESQL_BACKUP_RCLONE_CONFIG_FILE",
        "GLOBAL_POSTGRESQL_BACKUP_CODE_ROOT",
    )
    values = {name: os.getenv(name) for name in names}
    if any(not value for value in values.values()):
        raise GlobalPostgreSQLBackupError("configuration_invalid")
    return GlobalPostgreSQLBackupConfig(
        repository=values[names[0]],
        restic_password_file=Path(values[names[1]]),
        rclone_config_file=Path(values[names[2]]),
        repository_root=Path(values[names[3]]),
    )


@contextmanager
def _postgres_advisory_lock(database_engine: Engine) -> Iterator[bool]:
    """Mantém um lock de sessão enquanto o backup chama processos externos."""
    if database_engine.dialect.name != "postgresql":
        yield False
        return

    connection = database_engine.connect()
    acquired = False
    try:
        acquired = bool(
            connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_key)"),
                {"lock_key": _ADVISORY_LOCK_KEY},
            ).scalar_one()
        )
        connection.commit()
        yield acquired
    finally:
        if acquired:
            try:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": _ADVISORY_LOCK_KEY},
                ).scalar_one()
                connection.commit()
            except SQLAlchemyError:
                _LOGGER.warning("Global backup advisory lock release was not confirmed.")
        connection.close()


def _recover_interrupted_runs(session_factory, *, current_day: date, instant: datetime) -> bool:
    """Marca execuções deixadas abertas; devolve True se hoje já foi tentado."""
    with session_factory() as db:
        running = list(
            db.scalars(
                select(GlobalPostgreSQLBackupRun).where(
                    GlobalPostgreSQLBackupRun.status == "running",
                )
            )
        )
        current_day_was_running = False
        for run in running:
            current_day_was_running |= run.scheduled_day == current_day
            run.status = "unknown"
            run.verified = False
            run.error_code = "worker_interrupted"
            run.finished_at = instant
            run.duration_ms = max(
                int((instant - _as_utc(run.started_at)).total_seconds() * 1000),
                0,
            )
        if running:
            db.commit()
        return current_day_was_running


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _claim_daily_run(session_factory, *, scheduled_day: date, instant: datetime) -> UUID | None:
    if _recover_interrupted_runs(session_factory, current_day=scheduled_day, instant=instant):
        return None

    run = GlobalPostgreSQLBackupRun(
        scheduled_day=scheduled_day,
        status="running",
        started_at=instant,
        verified=False,
    )
    with session_factory() as db:
        existing = db.scalar(
            select(GlobalPostgreSQLBackupRun.id).where(
                GlobalPostgreSQLBackupRun.scheduled_day == scheduled_day,
            )
        )
        if existing is not None:
            return None
        db.add(run)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return None
        return run.id


def _finish_run(
    session_factory,
    *,
    run_id: UUID,
    instant: datetime,
    started_at: datetime,
    status: str,
    error_code: str | None = None,
    receipt: GlobalPostgreSQLBackupReceipt | None = None,
) -> None:
    values: dict[str, Any] = {
        "status": status,
        "finished_at": instant,
        "duration_ms": max(int((instant - started_at).total_seconds() * 1000), 0),
        "verified": bool(receipt and receipt.verified and status == "validated"),
        "error_code": _safe_error_code(error_code) if error_code else None,
        "snapshot_id": receipt.snapshot_id if receipt and status == "validated" else None,
        "dump_size_bytes": receipt.dump_size_bytes if receipt and status == "validated" else None,
    }
    with session_factory() as db:
        result = db.execute(
            update(GlobalPostgreSQLBackupRun)
            .where(
                GlobalPostgreSQLBackupRun.id == run_id,
                GlobalPostgreSQLBackupRun.status == "running",
            )
            .values(**values)
        )
        if result.rowcount == 1:
            db.commit()
        else:
            db.rollback()


def process_scheduled_global_postgresql_backup(
    *,
    session_factory=SessionLocal,
    database_engine: Engine = engine,
    enabled: bool | None = None,
    instant: datetime | None = None,
    clock: Callable[[], datetime] = now,
    config_loader: Callable[[], GlobalPostgreSQLBackupConfig] = _config_from_environment,
    database_url_loader: Callable[[], str] = database_url,
    backup_runner: Callable[
        [str, GlobalPostgreSQLBackupConfig], GlobalPostgreSQLBackupReceipt
    ] = create_global_postgresql_backup,
    lock_provider=_postgres_advisory_lock,
) -> bool:
    """Executa no máximo um backup diário e registra somente metadados sanitizados."""
    if not (_enabled_from_environment() if enabled is None else enabled is True):
        return False

    observed_at = _as_utc(instant or clock())
    scheduled_day = observed_at.date()
    try:
        with lock_provider(database_engine) as lock_acquired:
            if not lock_acquired:
                return False
            run_id = _claim_daily_run(
                session_factory,
                scheduled_day=scheduled_day,
                instant=observed_at,
            )
            if run_id is None:
                return False

            try:
                config = config_loader()
                database = database_url_loader()
            except GlobalPostgreSQLBackupError as exc:
                _finish_run(
                    session_factory,
                    run_id=run_id,
                    instant=_as_utc(clock()),
                    started_at=observed_at,
                    status="failed",
                    error_code=exc.code,
                )
                return True
            except Exception:  # noqa: BLE001 - config-stage errors precede any remote side effect
                _finish_run(
                    session_factory,
                    run_id=run_id,
                    instant=_as_utc(clock()),
                    started_at=observed_at,
                    status="failed",
                    error_code="configuration_invalid",
                )
                return True

            try:
                receipt = backup_runner(database, config)
            except GlobalPostgreSQLBackupError as exc:
                safe_code = _safe_error_code(exc.code)
                status = "failed" if safe_code in _PREFLIGHT_FAILURES else "unknown"
                _finish_run(
                    session_factory,
                    run_id=run_id,
                    instant=_as_utc(clock()),
                    started_at=observed_at,
                    status=status,
                    error_code=safe_code,
                )
                return True
            except Exception:  # noqa: BLE001 - unexpected post-start errors have an uncertain remote result
                _finish_run(
                    session_factory,
                    run_id=run_id,
                    instant=_as_utc(clock()),
                    started_at=observed_at,
                    status="unknown",
                    error_code="backup_operation_failed",
                )
                return True

            if (
                not receipt.verified
                or not re.fullmatch(r"[0-9a-f]{8,64}", receipt.snapshot_id)
                or receipt.dump_size_bytes <= 0
            ):
                _finish_run(
                    session_factory,
                    run_id=run_id,
                    instant=_as_utc(clock()),
                    started_at=observed_at,
                    status="unknown",
                    error_code="backup_receipt_invalid",
                )
                return True

            _finish_run(
                session_factory,
                run_id=run_id,
                instant=_as_utc(clock()),
                started_at=observed_at,
                status="validated",
                receipt=receipt,
            )
            return True
    except SQLAlchemyError:
        _LOGGER.warning("Global PostgreSQL backup scheduler could not claim or persist state.")
        return False


def _backup_run_summary(run: GlobalPostgreSQLBackupRun | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return {
        "status": run.status,
        "scheduled_day": run.scheduled_day.isoformat(),
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "snapshot_id": run.snapshot_id,
        "dump_size_bytes": run.dump_size_bytes,
        "duration_ms": run.duration_ms,
        "verified": run.verified,
        "error_code": run.error_code,
    }


def _read_global_postgresql_backup_status(db: Session) -> dict[str, Any]:
    latest = db.scalar(
        select(GlobalPostgreSQLBackupRun)
        .order_by(GlobalPostgreSQLBackupRun.scheduled_day.desc())
        .limit(1)
    )
    last_validated = db.scalar(
        select(GlobalPostgreSQLBackupRun)
        .where(
            GlobalPostgreSQLBackupRun.status == "validated",
            GlobalPostgreSQLBackupRun.verified.is_(True),
            GlobalPostgreSQLBackupRun.snapshot_id.is_not(None),
            GlobalPostgreSQLBackupRun.finished_at.is_not(None),
            GlobalPostgreSQLBackupRun.dump_size_bytes > 0,
        )
        .order_by(GlobalPostgreSQLBackupRun.scheduled_day.desc())
        .limit(1)
    )
    latest_summary = _backup_run_summary(latest) or {
        "status": "unknown",
        "scheduled_day": None,
        "started_at": None,
        "finished_at": None,
        "snapshot_id": None,
        "dump_size_bytes": None,
        "duration_ms": None,
        "verified": False,
        "error_code": None,
    }
    return {**latest_summary, "last_validated": _backup_run_summary(last_validated)}


def read_global_postgresql_backup_status(
    *, db: Session | None = None, session_factory=SessionLocal
) -> dict[str, Any]:
    """Lê recibos locais; deliberadamente não executa nem consulta Restic/Rclone."""
    if db is not None:
        return _read_global_postgresql_backup_status(db)
    with session_factory() as session:
        return _read_global_postgresql_backup_status(session)
