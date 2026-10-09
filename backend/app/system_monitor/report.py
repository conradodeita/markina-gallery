"""Projeção explícita: nenhuma identidade da árvore integra métricas ou exportação."""
import json
import os
import re
from datetime import timedelta

from sqlalchemy import Float, cast, func, select

from app.capacity_observability.contracts import CapacitySnapshot
from app.system_monitor.config import Settings, enabled, utc
from app.system_monitor.host import HostSnapshot
from app.system_monitor.incidents import incident_rows
from app.system_monitor.models import MonitorIncident, MonitorSample
from app.system_monitor.sanitize import number, timestamp
from app.system_monitor.store import http_history, operation_summary

KINDS = {"media", "preview_adjustment", "facial", "index", "search", "maintenance", "general", "whatsapp", "email"}
STATES = {"queued", "processing", "completed", "failed", "cancelled", "ready", "open", "closed"}


def counts(rows):
    if not isinstance(rows, list):
        return None
    return [{key: row[key] for key in ("kind", "state", "count") if key in row}
            for row in rows if row.get("kind", "media") in KINDS and row.get("state") in STATES
            and type(row.get("count")) is int and row["count"] >= 0]


def safe_sample(payload):
    result = {"capacity": None, "host": {"status": "not_collected", "data": None},
              "jobs": None, "workers": [], "storage": {}, "database_waits": None,
              "quality": {}}
    try:
        result["capacity"] = CapacitySnapshot.model_validate(payload.get("capacity")).model_dump(mode="json")
    except (ValueError, TypeError):
        # JSON timestamps require JSON validation in strict Pydantic contracts.
        try:
            result["capacity"] = CapacitySnapshot.model_validate_json(json.dumps(payload.get("capacity"))).model_dump(mode="json")
        except (ValueError, TypeError):
            pass
    host = payload.get("host", {})
    try:
        result["host"] = {"status": host["status"] if host["status"] in {"observed", "stale"} else "unavailable",
                          "data": HostSnapshot.model_validate_json(json.dumps(host["data"])).model_dump(mode="json")}
    except (KeyError, ValueError, TypeError):
        reason = host.get("reason")
        result["host"]["reason"] = reason if reason in {"host_source_not_configured", "permission_denied", "host_source_unavailable"} else "source_unavailable"
        result["host"]["status"] = "permission_denied" if reason == "permission_denied" else "not_collected" if reason == "host_source_not_configured" else "unavailable"
    jobs = payload.get("jobs", {})
    result["jobs"] = {"window_seconds": 300, "counts": counts(jobs.get("counts"))}
    result["integrations"] = counts(payload.get("integrations"))
    result["uploads"] = counts(payload.get("uploads"))
    for row in payload.get("workers", []) if isinstance(payload.get("workers"), list) else []:
        if row.get("kind") not in KINDS:
            continue
        result["workers"].append({"kind": row["kind"],
            "observed_instances": number(row.get("observed_instances")),
            "recent_instances": number(row.get("recent_instances")),
            "last_cycle_at": timestamp(row.get("last_cycle_at")),
            "last_progress_at": timestamp(row.get("last_progress_at")),
            "status": row.get("status") if row.get("status") in {"observed", "stale"} else "unavailable"})
    for section, fields in (("storage", ("registered_photos", "registered_file_bytes", "verified_file_bytes_lower_bound", "files_checked", "files_unavailable", "provisioned_bytes", "verified_quota_bytes")),
                            ("database_waits", ("lock_waiters", "idle_transactions", "unknown_states")),
                            ("quality", ("lost_observations", "collection_failures"))):
        original = payload.get(section, {})
        result[section] = {key: number(original.get(key)) for key in fields}
    result["storage"]["inventory_complete"] = payload.get("storage", {}).get("inventory_complete") is True
    result["storage"]["inventory_at"] = timestamp(payload.get("storage", {}).get("inventory_at"))
    return result


def snapshot_history(db, start, end):
    # Select <=120 snapshots in SQL, never fetch all historical JSON payloads.
    seconds = max(60, int((end - start).total_seconds() / 119) + 1)
    epoch = func.extract("epoch", MonitorSample.minute) if db.bind.dialect.name == "postgresql" else cast(func.strftime("%s", MonitorSample.minute), Float)
    maxima = select(func.max(MonitorSample.minute).label("minute")).where(
        MonitorSample.minute >= start, MonitorSample.minute < end,
    ).group_by(func.floor(epoch / seconds)).subquery()
    rows = db.scalars(select(MonitorSample).join(maxima, maxima.c.minute == MonitorSample.minute)
                      .order_by(MonitorSample.minute).limit(120)).all()
    result = []
    for row in rows:
        sample = safe_sample(row.payload)
        capacity = sample["capacity"] or {}
        result.append({"at": utc(row.minute).isoformat(), "host": sample["host"],
                       "queues": [{"kind": q["queue_class"], "queued": q["queued_total"]["value"],
                                   "processing": q["processing_total"]["value"]} for q in capacity.get("queues", [])]})
    return result


def sufficient_coverage(sample, operations):
    if not sample:
        return False
    host = sample["host"].get("data") or {}
    return (
        sample["host"]["status"] == "observed" and host.get("scope") == "host"
        and all(host.get(key) is not None for key in (
            "cpu_percent", "memory_available_bytes", "memory_total_bytes", "disk_free_bytes", "disk_total_bytes"))
        and sample["jobs"]["counts"] is not None
        and sample["integrations"] is not None and sample["uploads"] is not None
        and sample["database_waits"].get("lock_waiters") is not None
        and bool(sample["workers"]) and all(w["status"] == "observed" for w in sample["workers"])
        and sample["quality"].get("lost_observations") == 0
        and sample["quality"].get("collection_failures") == 0
        and any(op["operation"].startswith("http.") for op in operations)
        and bool(sample["capacity"]) and not sample["capacity"]["limitations"]
    )


def build_report(db, instant, minutes=60, *, include_incidents=False):
    settings = Settings.read()
    end = instant.replace(second=0, microsecond=0)
    start = end - timedelta(minutes=minutes)
    latest = db.scalar(select(MonitorSample).order_by(MonitorSample.minute.desc()).limit(1))
    age = (instant - utc(latest.minute)).total_seconds() if latest else None
    active_alerts = db.scalar(select(func.count()).select_from(MonitorIncident).where(MonitorIncident.state == "active")) or 0
    version = os.getenv("APP_VERSION", "")
    environment = os.getenv("APP_ENV", "")
    operations = operation_summary(db, start, end)
    status = "unknown" if not latest or age < 0 else "stale" if age > settings.stale_seconds else "attention" if active_alerts else "partial"
    sample = safe_sample(latest.payload) if latest else None
    if status == "attention":
        known = incident_rows(db, start, end)["active"]
        if any(row["evidence"]["severity"] == "critical" for row in known):
            status = "critical"
    if status == "partial" and enabled() and sufficient_coverage(sample, operations):
        status = "healthy"
    result = {
        "schema_version": 1, "generated_at": instant.isoformat(),
        "environment": environment if environment in {"production", "staging", "development", "test"} else None,
        "version": version if re.fullmatch(r"[a-fA-F0-9]{7,40}", version) else None,
        "collection_enabled": enabled(), "state": status,
        "last_collected_at": utc(latest.minute).isoformat() if latest else None,
        "age_seconds": age, "stale_seconds": settings.stale_seconds, "active_alerts": active_alerts,
        "interval": {"start": start.isoformat(), "end": end.isoformat(), "minutes": minutes},
        "operations": operations, "http_history": http_history(db, start, end),
        "latest": sample, "history": snapshot_history(db, start, end),
        "incidents": incident_rows(db, start, end) if include_incidents else None,
        "limitations": ["histogram_percentiles_are_upper_bounds", "process_buffers_may_lose_data_on_crash",
                        "pool_sample_is_one_api_process", "job_states_are_not_attempt_throughput",
                        "server_metrics_require_configured_source", "oci_quota_not_verified",
                        "file_inventory_hourly_bounded_1000_registered_paths", "historical_staging_and_biometrics_excluded_from_file_inventory", "capacity_not_established"],
    }
    if not latest or age > settings.stale_seconds:
        result["limitations"].append("collection_not_current")
    return result


def export_report(report, format="json"):
    content = json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2)
    if format == "text":
        content = "Diagnóstico Pick-your-Pic — schema 1\nDados ausentes são null.\n\n" + content
    if len(content.encode("utf-8")) > 1048576:
        raise ValueError("report_size_limit")
    return content
