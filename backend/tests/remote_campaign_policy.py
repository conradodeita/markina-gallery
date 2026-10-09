"""Fail-closed policy for the remote-only functional/load campaign."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


ALLOWED_BASE_URL = "https://markina-homolog.duckdns.org"
PROFILES = {"smoke", "expected", "peak", "stress", "soak"}
HIGH_IMPACT_PROFILES = {"stress", "soak"}
SMOKE_ALLOWED_REQUESTS = {("GET", "/healthz"), ("GET", "/api/health")}
REQUIRED_LIMITS = {
    "max_vus",
    "max_rps",
    "duration_seconds",
    "ramp_up_seconds",
    "ramp_down_seconds",
    "thresholds",
}


class CampaignPolicyError(ValueError):
    """Raised when a run is missing an explicit safety prerequisite."""


@dataclass(frozen=True)
class ApprovedProfile:
    name: str
    max_vus: int
    max_rps: float
    duration_seconds: int
    ramp_up_seconds: int
    ramp_down_seconds: int
    thresholds: dict[str, str]
    authorization_reference: str
    approved_by_owner: bool
    high_impact_authorized: bool
    environment: str
    ab_test_closed: bool
    test_credentials_configured: bool
    synthetic_otp_ready: bool


def validate_target(base_url: str) -> str:
    """Accept only the documented HTTPS homologation origin."""
    if not isinstance(base_url, str) or not base_url:
        raise CampaignPolicyError("target_missing")

    parsed = urlsplit(base_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise CampaignPolicyError("target_invalid_port") from exc

    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "markina-homolog.duckdns.org"
        or parsed.hostname != "markina-homolog.duckdns.org"
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise CampaignPolicyError("target_not_allowlisted")
    return ALLOWED_BASE_URL


def validate_smoke_preflight(
    *,
    base_url: str,
    environment: str,
    smoke_authorized: bool,
    authorization_reference: str,
    ab_test_closed: bool,
    max_requests: int,
) -> str:
    """Validate the fixed three-request cross-runner smoke before host access."""
    target = validate_target(base_url)
    if environment != "homolog":
        raise CampaignPolicyError("environment_not_allowed")
    if not smoke_authorized or not authorization_reference.strip():
        raise CampaignPolicyError("smoke_not_approved")
    if not ab_test_closed:
        raise CampaignPolicyError("ab_exercise_still_active")
    if max_requests != 3:
        raise CampaignPolicyError("smoke_request_limit_invalid")
    return target


def validate_smoke_request(method: str, path: str) -> tuple[str, str]:
    """Allow only the two fixed, read-only health requests in smoke workflows."""
    request = (method.upper(), path)
    if request not in SMOKE_ALLOWED_REQUESTS:
        raise CampaignPolicyError("smoke_operation_not_allowlisted")
    return request


def validate_smoke_url(method: str, url: str) -> tuple[str, str]:
    """Validate full request URL so a permitted path cannot hide a query/host change."""
    if not isinstance(url, str) or not url:
        raise CampaignPolicyError("smoke_url_invalid")
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise CampaignPolicyError("smoke_url_invalid") from exc
    if (
        parsed.scheme != "https"
        or parsed.netloc != "markina-homolog.duckdns.org"
        or parsed.hostname != "markina-homolog.duckdns.org"
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise CampaignPolicyError("smoke_url_not_allowlisted")
    return validate_smoke_request(method, parsed.path)


def validate_profile(profile: ApprovedProfile) -> ApprovedProfile:
    """Require owner-approved bounds and all non-interactive auth prerequisites."""
    if profile.name not in PROFILES:
        raise CampaignPolicyError("profile_unknown")
    if profile.environment != "homolog":
        raise CampaignPolicyError("environment_not_allowed")
    if not profile.approved_by_owner or not profile.authorization_reference.strip():
        raise CampaignPolicyError("profile_not_approved")
    if not profile.ab_test_closed:
        raise CampaignPolicyError("ab_exercise_still_active")
    if not profile.test_credentials_configured:
        raise CampaignPolicyError("test_credentials_missing")
    if not profile.synthetic_otp_ready:
        raise CampaignPolicyError("synthetic_otp_unavailable")
    if profile.max_vus < 1 or profile.max_rps <= 0:
        raise CampaignPolicyError("load_limits_invalid")
    if profile.duration_seconds < 1:
        raise CampaignPolicyError("duration_invalid")
    if profile.ramp_up_seconds < 0 or profile.ramp_down_seconds < 0:
        raise CampaignPolicyError("ramp_invalid")
    if not profile.thresholds or any(
        not isinstance(name, str) or not name.strip() or not isinstance(value, str) or not value.strip()
        for name, value in profile.thresholds.items()
    ):
        raise CampaignPolicyError("thresholds_missing")
    if profile.name in HIGH_IMPACT_PROFILES and not profile.high_impact_authorized:
        raise CampaignPolicyError("high_impact_profile_not_approved")
    return profile
