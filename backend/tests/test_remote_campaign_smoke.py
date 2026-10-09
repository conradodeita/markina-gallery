"""One-request API smoke against the allowlisted server; never starts services."""

import os
from time import perf_counter

import httpx
import pytest

from tests.remote_campaign_policy import (
    CampaignPolicyError,
    validate_smoke_preflight,
    validate_smoke_request,
)
from tests.remote_smoke_reporting import record_smoke_check


pytestmark = pytest.mark.skipif(
    os.getenv("PYP_REMOTE_CAMPAIGN") != "1",
    reason="Remote smoke is opt-in and must run from the approved external runner.",
)


def smoke_target() -> str:
    try:
        return validate_smoke_preflight(
            base_url=os.environ.get("PYP_REMOTE_TARGET_URL", ""),
            environment=os.environ.get("PYP_REMOTE_ENVIRONMENT", ""),
            smoke_authorized=os.environ.get("PYP_SMOKE_AUTHORIZED") == "1",
            authorization_reference=os.environ.get("PYP_SMOKE_AUTHORIZATION_REFERENCE", ""),
            ab_test_closed=os.environ.get("PYP_AB_TEST_CLOSED") == "1",
            max_requests=int(os.environ.get("PYP_SMOKE_MAX_REQUESTS", "0")),
        )
    except (CampaignPolicyError, ValueError) as exc:
        # Error categories are safe; never echo environment values or response bodies.
        raise RuntimeError("remote_smoke_preflight_failed") from exc


def test_remote_homolog_health_read_only():
    started = perf_counter()
    outcome = "failed"
    request_count = 0
    status = None
    request_duration = None
    try:
        target = smoke_target()
        method, path = validate_smoke_request("GET", "/healthz")
        request_count = 1
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            request_started = perf_counter()
            response = client.request(method, f"{target}{path}")
            request_duration = (perf_counter() - request_started) * 1000
            status = response.status_code
            assert response.url.host == "markina-homolog.duckdns.org"
            assert status == 200, f"healthcheck_failed:{path}:{status}"
        outcome = "passed"
    finally:
        record_smoke_check(
            check="pytest_backend_health",
            outcome=outcome,
            duration_ms=(perf_counter() - started) * 1000,
            request_duration_ms=request_duration,
            request_count=request_count,
            http_status=status,
        )
