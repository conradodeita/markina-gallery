"""Sanitized, bounded report writer for the three-request homolog smoke."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path


ORIGIN = "https://markina-homolog.duckdns.org"
CHECKS = {
    "vitest_api_health",
    "playwright_api_health",
    "pytest_backend_health",
}
OUTCOMES = {"passed", "failed", "not_run"}
SERVER_METRICS = {
    "api_pool": "unavailable_not_collected",
    "postgres_connections": "unavailable_not_collected",
    "queues": "unavailable_not_collected",
    "host_cpu_memory_disk": "unavailable_not_collected",
}


class SmokeReportError(ValueError):
    """Raised when a report path or record fails its safe schema."""


def _report_directory() -> Path:
    runner_temp = os.environ.get("RUNNER_TEMP", "")
    report_dir = os.environ.get("PYP_SMOKE_REPORT_DIR", "")
    if not runner_temp or not report_dir:
        raise SmokeReportError("smoke_report_directory_missing")
    if Path(runner_temp).is_symlink() or Path(report_dir).is_symlink():
        raise SmokeReportError("smoke_report_directory_not_confined")
    try:
        base = Path(runner_temp).resolve(strict=True)
        target = Path(report_dir).resolve(strict=True)
    except OSError as exc:
        raise SmokeReportError("smoke_report_directory_unavailable") from exc
    if not base.is_dir() or not target.is_dir() or base not in target.parents:
        raise SmokeReportError("smoke_report_directory_not_confined")
    return target


def record_smoke_check(
    *,
    check: str,
    outcome: str,
    duration_ms: float,
    request_duration_ms: float | None,
    request_count: int,
    http_status: int | None,
) -> None:
    """Write only allowlisted scalar fields; never accept body, URL, or headers."""
    if not isinstance(check, str) or check not in CHECKS:
        raise SmokeReportError("smoke_check_record_invalid")
    if not isinstance(outcome, str) or outcome not in OUTCOMES:
        raise SmokeReportError("smoke_check_record_invalid")
    if (
        isinstance(duration_ms, bool)
        or not isinstance(duration_ms, (int, float))
        or not math.isfinite(duration_ms)
        or duration_ms < 0
    ):
        raise SmokeReportError("smoke_duration_invalid")
    if isinstance(request_count, bool) or not isinstance(request_count, int) or request_count not in (0, 1):
        raise SmokeReportError("smoke_request_count_invalid")
    if request_count == 0 and request_duration_ms is not None:
        raise SmokeReportError("smoke_request_timing_invalid")
    if request_duration_ms is not None and (
        isinstance(request_duration_ms, bool)
        or not isinstance(request_duration_ms, (int, float))
        or not math.isfinite(request_duration_ms)
        or request_duration_ms < 0
    ):
        raise SmokeReportError("smoke_request_timing_invalid")
    if http_status is not None and (
        isinstance(http_status, bool)
        or not isinstance(http_status, int)
        or not 100 <= http_status <= 599
    ):
        raise SmokeReportError("smoke_http_status_invalid")

    directory = _report_directory()
    record = {
        "check": check,
        "outcome": outcome,
        "duration_ms": round(duration_ms, 3),
        "request_duration_ms": (
            round(request_duration_ms, 3) if request_duration_ms is not None else None
        ),
        "request_count": request_count,
        "http_status": http_status,
        "target": ORIGIN,
    }
    destination = directory / f"{check}.json"
    try:
        with destination.open("x", encoding="utf-8") as output:
            output.write(json.dumps(record, sort_keys=True))
            output.write("\n")
        try:
            destination.chmod(0o600)
        except OSError:
            pass
    except FileExistsError as exc:
        raise SmokeReportError("smoke_check_record_already_exists") from exc
    except OSError as exc:
        raise SmokeReportError("smoke_check_record_write_failed") from exc


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 3)


def _read_record(path: Path) -> dict[str, object]:
    if path.is_symlink() or path.name not in {f"{name}.json" for name in CHECKS}:
        raise SmokeReportError("smoke_report_entry_invalid")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SmokeReportError("smoke_report_record_unreadable") from exc
    if (
        not isinstance(record, dict)
        or set(record)
        != {
            "check",
            "outcome",
            "duration_ms",
            "request_duration_ms",
            "request_count",
            "http_status",
            "target",
        }
        or not isinstance(record["check"], str)
        or record["check"] != path.stem
        or record["check"] not in CHECKS
        or not isinstance(record["outcome"], str)
        or record["outcome"] not in OUTCOMES
        or record["target"] != ORIGIN
        or isinstance(record["duration_ms"], bool)
        or not isinstance(record["duration_ms"], (int, float))
        or not math.isfinite(record["duration_ms"])
        or record["duration_ms"] < 0
        or isinstance(record["request_count"], bool)
        or not isinstance(record["request_count"], int)
        or record["request_count"] not in (0, 1)
        or (
            record["request_duration_ms"] is not None
            and (
                isinstance(record["request_duration_ms"], bool)
                or not isinstance(record["request_duration_ms"], (int, float))
                or not math.isfinite(record["request_duration_ms"])
                or record["request_duration_ms"] < 0
            )
        )
        or (record["request_count"] == 0 and record["request_duration_ms"] is not None)
        or (
            record["http_status"] is not None
            and (
                isinstance(record["http_status"], bool)
                or not isinstance(record["http_status"], int)
                or not 100 <= record["http_status"] <= 599
            )
        )
    ):
        raise SmokeReportError("smoke_report_record_invalid")
    return record


def build_smoke_report(
    *,
    source_revision: str,
    started_at: datetime,
    finished_at: datetime | None = None,
) -> dict[str, object]:
    """Aggregate present check records and mark missing checks/metrics explicitly."""
    directory = _report_directory()
    finished = finished_at or datetime.now(timezone.utc)
    if started_at.tzinfo is None or finished.tzinfo is None or finished < started_at:
        raise SmokeReportError("smoke_time_window_invalid")
    if not isinstance(source_revision, str):
        raise SmokeReportError("smoke_source_revision_invalid")
    revision = source_revision.strip()
    if not revision or len(revision) > 80 or any(char.isspace() for char in revision):
        raise SmokeReportError("smoke_source_revision_invalid")

    records = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "remote-smoke-report.json":
            continue
        records.append(_read_record(path))
    by_check = {record["check"]: record for record in records}
    if len(by_check) != len(records):
        raise SmokeReportError("smoke_report_duplicate_check")
    missing = sorted(CHECKS - set(by_check))
    actual_requests = sum(int(record["request_count"]) for record in records)
    latencies = [
        float(record["request_duration_ms"])
        for record in records
        if record["request_duration_ms"] is not None
    ]
    failed_checks = sorted(
        name for name, record in by_check.items() if record["outcome"] != "passed"
    )
    duration_seconds = round((finished - started_at).total_seconds(), 3)
    checks = []
    for name in sorted(CHECKS):
        record = by_check.get(name)
        checks.append(
            {
                "name": name,
                "outcome": record["outcome"] if record else "not_run",
                "request_count": record["request_count"] if record else 0,
                "http_status": record["http_status"] if record else None,
                "duration_ms": record["duration_ms"] if record else None,
                "request_duration_ms": record["request_duration_ms"] if record else None,
            }
        )

    return {
        "schema": "pyp-remote-test-report/v1",
        "source_revision": revision,
        "environment": "homolog",
        "target": ORIGIN,
        "profile": "smoke",
        "started_at": started_at.astimezone(timezone.utc).isoformat(),
        "finished_at": finished.astimezone(timezone.utc).isoformat(),
        "duration_seconds": duration_seconds,
        "virtual_users": 1,
        "planned_requests_max": 3,
        "actual_requests": actual_requests,
        "operations_per_second": round(actual_requests / duration_seconds, 4) if duration_seconds else None,
        "latency_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "p99": _percentile(latencies, 0.99),
        },
        "errors": {"failed_checks": failed_checks, "missing_checks": missing, "count": len(failed_checks) + len(missing)},
        "functional_checks": checks,
        "server_metrics": SERVER_METRICS,
        "limitations": [
            "Health endpoints only; no authenticated or multi-tenant capacity was measured.",
            "Latency percentiles use only the duration measured around each HTTP request.",
        ],
        "recommendation": (
            "Diagnose failed or missing checks; do not advance the profile until they pass."
            if failed_checks or missing
            else "Health smoke passed only; obtain the remaining operational gates before authenticated or capacity runs."
        ),
    }


def write_smoke_report(*, source_revision: str, started_at: datetime) -> Path:
    directory = _report_directory()
    report = build_smoke_report(source_revision=source_revision, started_at=started_at)
    destination = directory / "remote-smoke-report.json"
    try:
        with destination.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2, sort_keys=True)
            output.write("\n")
        try:
            destination.chmod(0o600)
        except OSError:
            pass
    except FileExistsError as exc:
        raise SmokeReportError("smoke_report_already_exists") from exc
    except OSError as exc:
        raise SmokeReportError("smoke_report_write_failed") from exc
    return destination
