"""Máquina de estados: evidência ausente não resolve nem prova indisponibilidade."""
from datetime import datetime, timedelta

from sqlalchemy import select

from app.system_monitor.config import Settings, utc
from app.system_monitor.models import MonitorIncident, MonitorTransition
from app.system_monitor.sanitize import number
from app.system_monitor.telemetry import OPERATIONS, WORKERS

CODES = {f"{prefix}.{op}" for prefix in ("errors", "latency", "rejected") for op in OPERATIONS}
CODES |= {f"{prefix}.{kind}" for prefix in ("queue", "worker", "progress", "failed") for kind in WORKERS}
CODES |= {"pool.occupancy", "disk.used_percent", "host.stale", "failed.facial", "failed.upload", "failed.whatsapp", "failed.email"}
CODES |= {"cpu.percent", "memory.used_percent"}


def evidence_for(code, value, threshold):
    kind = "confirmed_failures" if code.startswith(("errors.", "failed.")) else "data_gap" if code.startswith(("host.", "worker.")) else "preventive_alert"
    return {"observed": number(value), "threshold": number(threshold), "kind": kind,
            "severity": "critical" if code.startswith("errors.http.") and number(value) is not None and value >= 50 else "attention"}


def evaluate(db, signals: dict[str, tuple[float | None, float]], instant, settings: Settings):
    for code, (value, threshold) in signals.items():
        if code not in CODES or value is None:
            continue
        incident = db.get(MonitorIncident, code)
        breached = value >= threshold
        evidence = evidence_for(code, value, threshold)
        changed = False
        if breached:
            if incident is None:
                incident = MonitorIncident(code=code, state="pending", first_seen=instant,
                                           updated_at=instant, evidence=evidence)
                db.add(incident)
            elif incident.state == "resolved" or instant - utc(incident.updated_at) > timedelta(seconds=settings.stale_seconds):
                incident.state = "pending"
                incident.first_seen = instant
            elif incident.state == "pending" and (instant - utc(incident.first_seen)).total_seconds() >= settings.minimum_alert_seconds:
                incident.state = "active"
                changed = True
        elif incident is not None and incident.state != "resolved":
            changed = incident.state == "active"
            incident.state = "resolved"
        if incident is not None:
            incident.evidence = evidence
            incident.updated_at = instant
            if changed:
                db.add(MonitorTransition(code=code, state=incident.state,
                                         occurred_at=instant, evidence=evidence))


def signals_for(sample, operations, settings):
    signals = {}
    for row in operations:
        if row["count"] >= 20:
            signals[f"errors.{row['operation']}"] = (row["error_percent"], settings.error_percent)
            signals[f"latency.{row['operation']}"] = (row["latency"]["p95"], settings.latency_ms)
            if row["operation"] == "http.auth":
                signals["rejected.http.auth"] = (100 * row["rejected"] / row["count"], settings.error_percent)
    capacity = sample.get("capacity") or {}
    for queue in capacity.get("queues", []):
        age = queue["oldest_record_age_seconds"]["value"]
        if queue["queued_total"]["value"] == 0:
            age = 0
        signals[f"queue.{queue['queue_class']}"] = (age, settings.queue_age_seconds)
    pool = capacity.get("pool", {})
    used, maximum = pool.get("checked_out", {}).get("value"), pool.get("potential_max", {}).get("value")
    signals["pool.occupancy"] = (100 * used / maximum if used is not None and maximum else None, settings.pool_percent)
    host = sample.get("host", {})
    signals["host.stale"] = (1 if host.get("status") == "stale" else 0 if host.get("status") == "observed" else None, 1)
    if host.get("status") == "observed":
        data = host["data"]
        free, total = data.get("disk_free_bytes"), data.get("disk_total_bytes")
        signals["disk.used_percent"] = (100 * (1 - free / total) if free is not None and total else None,
                                        100 - settings.disk_free_percent)
        signals["cpu.percent"] = (data.get("cpu_percent"), settings.cpu_percent)
        available, memory = data.get("memory_available_bytes"), data.get("memory_total_bytes")
        signals["memory.used_percent"] = (100 * (1 - available / memory) if available is not None and memory else None,
                                          100 - settings.memory_free_percent)
    for worker in sample.get("workers", []) if isinstance(sample.get("workers"), list) else []:
        kind = worker["kind"]
        signals[f"worker.{kind}"] = (0 if worker["recent_instances"] else 1, 1)
        queue = next((q for q in capacity.get("queues", []) if q["queue_class"] == kind), None)
        if queue and queue["queued_total"]["value"] is not None:
            progress = worker.get("last_progress_at")
            observed_at = sample.get("collected_at")
            age = (datetime.fromisoformat(observed_at) - datetime.fromisoformat(progress)).total_seconds() if progress and observed_at else None
            signals[f"progress.{kind}"] = (age if queue["queued_total"]["value"] else 0, settings.queue_age_seconds)
    for row in (sample.get("jobs") or {}).get("counts", []):
        if row["state"] == "failed":
            signals[f"failed.{row['kind']}"] = (row["count"], settings.failure_count)
    for section, fallback in (("uploads", "upload"), ("integrations", "")):
        rows = sample.get(section)
        if isinstance(rows, list):
            for row in rows:
                if row["state"] == "failed":
                    signals[f"failed.{row.get('kind', fallback)}"] = (row["count"], settings.failure_count)
    # A missing failure group in a successful aggregation is an observed zero.
    for kind in ("media", "preview_adjustment", "search", "index", "maintenance"):
        if isinstance((sample.get("jobs") or {}).get("counts"), list):
            signals.setdefault(f"failed.{kind}", (0, settings.failure_count))
    for section, kinds in (("uploads", ("upload",)), ("integrations", ("whatsapp", "email"))):
        if isinstance(sample.get(section), list):
            for kind in kinds:
                signals.setdefault(f"failed.{kind}", (0, settings.failure_count))
    return signals


def incident_rows(db, start, end):
    active = db.scalars(select(MonitorIncident).where(MonitorIncident.state == "active", MonitorIncident.code.in_(CODES))
                        .order_by(MonitorIncident.updated_at.desc()).limit(100)).all()
    transitions = db.scalars(select(MonitorTransition).where(
        MonitorTransition.occurred_at >= start, MonitorTransition.occurred_at < end,
        MonitorTransition.code.in_(CODES), MonitorTransition.state.in_(("active", "resolved")),
    ).order_by(MonitorTransition.occurred_at.desc()).limit(201)).all()
    return {
        "active": [{"code": row.code, "state": row.state, "started_at": utc(row.first_seen).isoformat(),
                    "updated_at": utc(row.updated_at).isoformat(), "evidence": evidence_for(row.code, row.evidence.get("observed"), row.evidence.get("threshold"))} for row in active],
        "history": [{"code": row.code, "state": row.state, "at": utc(row.occurred_at).isoformat(),
                     "evidence": evidence_for(row.code, row.evidence.get("observed"), row.evidence.get("threshold"))} for row in transitions[:200]],
        "history_truncated": len(transitions) > 200,
    }
