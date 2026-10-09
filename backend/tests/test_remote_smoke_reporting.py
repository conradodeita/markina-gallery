from datetime import datetime, timezone
import json

import pytest

from tests.remote_smoke_reporting import (
    CHECKS,
    SmokeReportError,
    build_smoke_report,
    record_smoke_check,
    write_smoke_report,
)


@pytest.fixture
def smoke_report_directory(tmp_path, monkeypatch):
    runner_temp = tmp_path / "runner-temp"
    report_dir = runner_temp / "pyp-smoke-report"
    report_dir.mkdir(parents=True)
    monkeypatch.setenv("RUNNER_TEMP", str(runner_temp))
    monkeypatch.setenv("PYP_SMOKE_REPORT_DIR", str(report_dir))
    return report_dir


def test_record_accepts_only_allowlisted_scalar_fields(smoke_report_directory):
    record_smoke_check(
        check="vitest_api_health",
        outcome="passed",
        duration_ms=25.1255,
        request_duration_ms=24.1255,
        request_count=1,
        http_status=200,
    )
    record = json.loads((smoke_report_directory / "vitest_api_health.json").read_text())
    assert record == {
        "check": "vitest_api_health",
        "outcome": "passed",
        "duration_ms": 25.125,
        "request_duration_ms": 24.125,
        "request_count": 1,
        "http_status": 200,
        "target": "https://markina-homolog.duckdns.org",
    }


def test_record_rejects_sensitive_fields_invalid_checks_and_non_scalar_limits(smoke_report_directory):
    with pytest.raises(SmokeReportError, match="smoke_check_record_invalid"):
        record_smoke_check(
            check="unknown", outcome="passed", duration_ms=1, request_duration_ms=1,
            request_count=1, http_status=200
        )
    for request_count, status in ((2, 200), (0, 99)):
        with pytest.raises(SmokeReportError):
            record_smoke_check(
                check="vitest_api_health",
                outcome="passed",
                duration_ms=1,
                request_duration_ms=1 if request_count else None,
                request_count=request_count,
                http_status=status,
            )


def test_report_aggregates_requests_and_marks_missing_checks_and_server_metrics(
    smoke_report_directory,
):
    record_smoke_check(
        check="vitest_api_health", outcome="passed", duration_ms=30,
        request_duration_ms=20, request_count=1, http_status=200
    )
    record_smoke_check(
        check="playwright_api_health", outcome="failed", duration_ms=100,
        request_duration_ms=40, request_count=1, http_status=503
    )
    started = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    report = build_smoke_report(
        source_revision="a" * 40,
        started_at=started,
        finished_at=datetime(2026, 10, 8, 12, 0, 10, tzinfo=timezone.utc),
    )
    assert report["actual_requests"] == 2
    assert report["operations_per_second"] == 0.2
    assert report["latency_ms"] == {"p50": 20.0, "p95": 40.0, "p99": 40.0}
    assert report["recommendation"].startswith("Diagnose failed")
    assert report["errors"] == {
        "failed_checks": ["playwright_api_health"],
        "missing_checks": ["pytest_backend_health"],
        "count": 2,
    }
    assert set(report["server_metrics"].values()) == {"unavailable_not_collected"}
    assert len(report["functional_checks"]) == len(CHECKS)


def test_report_fails_closed_on_unrecognized_record_or_directory_escape(
    smoke_report_directory, monkeypatch, tmp_path
):
    (smoke_report_directory / "unexpected.json").write_text("{}")
    with pytest.raises(SmokeReportError, match="smoke_report_entry_invalid"):
        build_smoke_report(source_revision="deadbeef", started_at=datetime.now(timezone.utc))

    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setenv("PYP_SMOKE_REPORT_DIR", str(outside))
    with pytest.raises(SmokeReportError, match="smoke_report_directory_not_confined"):
        build_smoke_report(source_revision="deadbeef", started_at=datetime.now(timezone.utc))


def test_final_report_is_created_once_with_reproducible_name(smoke_report_directory):
    report_path = write_smoke_report(
        source_revision="revision-123",
        started_at=datetime.now(timezone.utc),
    )
    assert report_path.name == "remote-smoke-report.json"
    with pytest.raises(SmokeReportError, match="smoke_report_already_exists"):
        write_smoke_report(source_revision="revision-123", started_at=datetime.now(timezone.utc))
