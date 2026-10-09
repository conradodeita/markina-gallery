"""Agregações de estado, nunca listas completas de jobs ou payloads de domínio."""
from datetime import timedelta

from sqlalchemy import case, func, select, text

from app.auth import (
    EmailDelivery,
    FacialJob,
    MediaJob,
    PhotoAsset,
    PreviewAdjustment,
    PrivateUploadBatch,
    WhatsAppDelivery,
)
from app.system_monitor.config import Settings, utc
from app.system_monitor.models import MonitorWorker
from app.system_monitor.storage import file_inventory
from app.system_monitor.store import bounded


def job_counts(db, instant):
    result = []
    for name, model in (("media", MediaJob), ("preview_adjustment", PreviewAdjustment),
                        ("facial", FacialJob)):
        groups = [model.status]
        if model is FacialJob:
            kind = case((FacialJob.kind == "search", "search"),
                        (FacialJob.kind == "index", "index"), else_="maintenance")
            groups.insert(0, kind)
        rows = db.execute(select(*groups, func.count()).where(
            model.updated_at >= instant - timedelta(minutes=5),
            model.updated_at <= instant,
        ).group_by(*groups)).all()
        for row in rows:
            group = row[0] if model is FacialJob else name
            result.append({"kind": group, "state": row[-2], "count": row[-1]})
    return {"window_seconds": 300, "semantics": "current_states_updated_in_window", "counts": result}


def integrations(db, instant):
    result = []
    for name, model in (("whatsapp", WhatsAppDelivery), ("email", EmailDelivery)):
        # Queue state only; does not read payloads, providers or recipients.
        rows = db.execute(select(model.status, func.count()).where(
            model.status.in_(("queued", "processing", "failed")),
        ).group_by(model.status)).all()
        result.extend({"kind": name, "state": status, "count": count} for status, count in rows)
    return result


def workers(db, instant):
    rows = db.execute(select(
        MonitorWorker.kind, func.count(), func.max(MonitorWorker.last_seen),
        func.max(MonitorWorker.last_progress),
        func.count().filter(MonitorWorker.last_seen >= instant - timedelta(seconds=Settings.read().stale_seconds)),
    ).where(MonitorWorker.last_seen >= instant - timedelta(days=1)).group_by(MonitorWorker.kind)).all()
    return [{"kind": kind, "observed_instances": count, "recent_instances": recent,
             "last_cycle_at": utc(seen).isoformat(),
             "last_progress_at": utc(progress).isoformat() if progress else None,
             "status": "observed" if recent else "stale"}
            for kind, count, seen, progress, recent in rows]


def database_waits(db):
    if db.bind.dialect.name != "postgresql":
        return {"status": "unavailable", "reason": "unsupported_backend"}
    row = db.execute(text("""
        SELECT count(*) FILTER (WHERE wait_event_type = 'Lock') AS lock_waiters,
               count(*) FILTER (WHERE state = 'idle in transaction') AS idle_transactions,
               count(*) FILTER (WHERE state IS NULL) AS unknown_states
        FROM pg_stat_activity
        WHERE backend_type = 'client backend' AND datname = current_database()
    """)).mappings().one()
    return {"status": "observed", "scope": "application_database", **dict(row)}


def collect_sections(factory, instant):
    result = {}
    # Independent short transactions; failed query does not poison following sections.
    for name, collect in (("jobs", lambda db: job_counts(db, instant)),
                          ("integrations", lambda db: integrations(db, instant)),
                          ("workers", lambda db: workers(db, instant)),
                          ("database_waits", database_waits),
                          ("uploads", lambda db: [{"state": status, "count": count} for status, count
                              in db.execute(select(PrivateUploadBatch.status, func.count())
                                  .group_by(PrivateUploadBatch.status)).all()]),
                          ("storage", lambda db: {
                              "registered_photos": db.scalar(select(func.count()).select_from(PhotoAsset)),
                              **file_inventory(db),
                              "provisioned_bytes": None, "verified_quota_bytes": None,
                          })):
        try:
            with factory() as db:
                bounded(db, readonly=True)
                result[name] = collect(db)
        except Exception:  # noqa: BLE001 -- Fonte opcional isolada, sem mensagem de exceção.
            result[name] = {"status": "unavailable", "reason": "source_unavailable"}
    return result
