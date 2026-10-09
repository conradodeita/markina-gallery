"""Persistência atômica e consultas agregadas, sem eventos HTTP individuais."""
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.system_monitor.config import Settings, utc
from app.system_monitor.models import (
    MonitorActivity,
    MonitorBucket,
    MonitorIncident,
    MonitorSample,
    MonitorTransition,
    MonitorWorker,
)
from app.system_monitor.telemetry import OPERATIONS, percentiles


def bounded(db, *, readonly=False):
    if db.bind.dialect.name == "postgresql":
        if readonly:
            db.execute(text("SET TRANSACTION READ ONLY"))
        db.execute(text("SET LOCAL statement_timeout = '500ms'"))
        db.execute(text("SET LOCAL lock_timeout = '100ms'"))


def insert(db, model):
    return (pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert)(model)


def save_buckets(db, buckets):
    rows = []
    for (minute, operation, latency_bin), values in buckets.items():
        if operation not in OPERATIONS:
            continue
        rows.append({"minute": minute, "operation": operation, "latency_bin": latency_bin,
                     "count": values[0], "errors": values[1], "rejected": values[2], "total_ms": values[3],
                     "timeouts": values[4] if len(values) > 4 else 0})
    for offset in range(0, len(rows), 100):
        statement = insert(db, MonitorBucket).values(rows[offset:offset + 100])
        db.execute(statement.on_conflict_do_update(
            index_elements=["minute", "operation", "latency_bin"],
            set_={name: getattr(MonitorBucket, name) + getattr(statement.excluded, name)
                  for name in ("count", "errors", "rejected", "total_ms", "timeouts")},
        ))


def operation_summary(db, start, end):
    rows = db.execute(select(
        MonitorBucket.operation, MonitorBucket.latency_bin,
        func.sum(MonitorBucket.count), func.sum(MonitorBucket.errors),
        func.sum(MonitorBucket.rejected), func.sum(MonitorBucket.total_ms),
        func.sum(MonitorBucket.timeouts),
    ).where(MonitorBucket.minute >= start, MonitorBucket.minute < end,
            MonitorBucket.operation.in_(OPERATIONS))
      .group_by(MonitorBucket.operation, MonitorBucket.latency_bin)).all()
    summaries = {}
    histograms = defaultdict(dict)
    for operation, bucket, count, errors, rejected, total_ms, timeouts in rows:
        row = summaries.setdefault(operation, {
            "operation": operation, "count": 0, "errors": 0, "rejected": 0, "total_ms": 0, "timeouts": 0,
        })
        for field, value in (("count", count), ("errors", errors), ("rejected", rejected), ("total_ms", total_ms), ("timeouts", timeouts)):
            row[field] += value
        histograms[operation][bucket] = count
    seconds = max(1, (end - start).total_seconds())
    for operation, row in summaries.items():
        row["rate_per_second"] = row["count"] / seconds
        row["error_percent"] = 100 * row["errors"] / row["count"]
        row["mean_ms"] = row.pop("total_ms") / row["count"]
        row["latency"] = percentiles(histograms[operation])
    return [summaries[key] for key in sorted(summaries)]


def http_history(db, start, end):
    # SQL reduces to <=1440 rows; response rolls up to five-minute points.
    rows = db.execute(select(
        MonitorBucket.minute, func.sum(MonitorBucket.count),
        func.sum(MonitorBucket.errors), func.sum(MonitorBucket.total_ms),
    ).where(MonitorBucket.minute >= start, MonitorBucket.minute < end,
            MonitorBucket.operation.in_([key for key in OPERATIONS if key.startswith("http.")]))
      .group_by(MonitorBucket.minute).order_by(MonitorBucket.minute).limit(1441)).all()
    points = {}
    for minute, count, errors, total_ms in rows:
        minute = utc(minute).replace(minute=minute.minute // 5 * 5)
        row = points.setdefault(minute, [0, 0, 0.0])
        row[0] += count
        row[1] += errors
        row[2] += total_ms
    return [{"at": at.isoformat(), "count": row[0], "errors": row[1],
             "mean_ms": row[2] / row[0], "window_seconds": 300}
            for at, row in sorted(points.items())]


def prune(db, instant, settings: Settings):
    # Bounded batches only; a backlog is removed across subsequent cycles.
    cutoff = instant - timedelta(days=settings.retention_days)
    for model, column, age in (
        (MonitorSample, MonitorSample.minute, cutoff),
        (MonitorTransition, MonitorTransition.occurred_at, cutoff),
        (MonitorWorker, MonitorWorker.last_seen, instant - timedelta(days=1)),
        (MonitorActivity, MonitorActivity.last_activity, instant - timedelta(days=1)),
    ):
        key = next(iter(model.__table__.primary_key.columns))
        expired = select(key).where(column < age).limit(1000)
        db.execute(delete(model).where(key.in_(expired)))
    # Composite-key deletion by a bounded minute window.
    minutes = select(MonitorBucket.minute).where(MonitorBucket.minute < cutoff).distinct().order_by(MonitorBucket.minute).limit(10)
    db.execute(delete(MonitorBucket).where(MonitorBucket.minute.in_(minutes)))
    db.execute(delete(MonitorIncident).where(
        MonitorIncident.state == "resolved", MonitorIncident.updated_at < cutoff,
    ))
