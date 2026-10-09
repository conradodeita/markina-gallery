from dataclasses import replace

import pytest

from tests.remote_campaign_policy import (
    ApprovedProfile,
    CampaignPolicyError,
    validate_profile,
    validate_smoke_preflight,
    validate_smoke_request,
    validate_smoke_url,
    validate_target,
)


def approved_profile(**overrides):
    values = ApprovedProfile(
        name="smoke",
        max_vus=1,
        max_rps=1.0,
        duration_seconds=30,
        ramp_up_seconds=0,
        ramp_down_seconds=0,
        thresholds={"http_req_failed": "rate<0.01", "http_req_duration": "p(95)<1000"},
        authorization_reference="owner-approval-reference",
        approved_by_owner=True,
        high_impact_authorized=False,
        environment="homolog",
        ab_test_closed=True,
        test_credentials_configured=True,
        synthetic_otp_ready=True,
    )
    return replace(values, **overrides)


def test_target_accepts_only_exact_homolog_origin():
    assert validate_target("https://markina-homolog.duckdns.org/") == (
        "https://markina-homolog.duckdns.org"
    )


@pytest.mark.parametrize(
    "target",
    [
        "http://markina-homolog.duckdns.org",
        "https://markina-homolog.duckdns.org.attacker.invalid",
        "https://markina-homolog.duckdns.org/admin",
        "https://markina-homolog.duckdns.org?next=https://example.invalid",
        "https://user@markina-homolog.duckdns.org",
        "https://127.0.0.1",
        "http://localhost:8000",
        "https://markina-homolog.duckdns.org:444",
    ],
)
def test_target_rejects_non_allowlisted_origins(target):
    with pytest.raises(CampaignPolicyError):
        validate_target(target)


def test_profile_requires_explicit_limits_and_all_safety_gates():
    assert validate_profile(approved_profile()).max_vus == 1

    cases = [
        replace(approved_profile(), approved_by_owner=False),
        replace(approved_profile(), authorization_reference=""),
        replace(approved_profile(), environment="production"),
        replace(approved_profile(), ab_test_closed=False),
        replace(approved_profile(), test_credentials_configured=False),
        replace(approved_profile(), synthetic_otp_ready=False),
        replace(approved_profile(), max_vus=0),
        replace(approved_profile(), max_rps=0),
        replace(approved_profile(), duration_seconds=0),
        replace(approved_profile(), thresholds={}),
        replace(approved_profile(), ramp_up_seconds=-1),
    ]
    for profile in cases:
        with pytest.raises(CampaignPolicyError):
            validate_profile(profile)


def test_stress_and_soak_are_distinct_profiles_and_need_owner_approval():
    for name in ("stress", "soak"):
        stress_or_soak = replace(approved_profile(), name=name)
        with pytest.raises(CampaignPolicyError, match="high_impact_profile_not_approved"):
            validate_profile(stress_or_soak)
        explicitly_authorized = replace(stress_or_soak, high_impact_authorized=True)
        assert validate_profile(explicitly_authorized).name == name


def test_unknown_profiles_are_rejected():
    with pytest.raises(CampaignPolicyError, match="profile_unknown"):
        validate_profile(replace(approved_profile(), name="unbounded"))


def test_smoke_preflight_requires_all_gates_and_exactly_three_requests():
    args = {
        "base_url": "https://markina-homolog.duckdns.org",
        "environment": "homolog",
        "smoke_authorized": True,
        "authorization_reference": "owner-reference",
        "ab_test_closed": True,
        "max_requests": 3,
    }
    assert validate_smoke_preflight(**args) == "https://markina-homolog.duckdns.org"

    for override, expected in (
        ({"environment": "production"}, "environment_not_allowed"),
        ({"smoke_authorized": False}, "smoke_not_approved"),
        ({"authorization_reference": " "}, "smoke_not_approved"),
        ({"ab_test_closed": False}, "ab_exercise_still_active"),
        ({"max_requests": 4}, "smoke_request_limit_invalid"),
        ({"base_url": "http://localhost:8000"}, "target_not_allowlisted"),
    ):
        with pytest.raises(CampaignPolicyError, match=expected):
            validate_smoke_preflight(**(args | override))


def test_smoke_operation_allowlist_blocks_mutations_auth_and_other_reads():
    assert validate_smoke_request("GET", "/healthz") == ("GET", "/healthz")
    assert validate_smoke_request("get", "/api/health") == ("GET", "/api/health")
    for method, path in (
        ("POST", "/api/auth/client/challenge"),
        ("POST", "/api/payments"),
        ("DELETE", "/api/admin/parent-galleries/test"),
        ("PATCH", "/api/admin/settings"),
        ("GET", "/api/facial-search"),
        ("GET", "/api/health?next=/admin"),
    ):
        with pytest.raises(CampaignPolicyError, match="smoke_operation_not_allowlisted"):
            validate_smoke_request(method, path)


def test_smoke_full_url_rejects_query_fragment_and_origin_variants():
    assert validate_smoke_url(
        "GET", "https://markina-homolog.duckdns.org/api/health"
    ) == ("GET", "/api/health")
    for url in (
        "https://markina-homolog.duckdns.org/api/health?next=/admin",
        "https://markina-homolog.duckdns.org/api/health#fragment",
        "https://markina-homolog.duckdns.org.attacker.invalid/api/health",
        "http://markina-homolog.duckdns.org/api/health",
        "https://user@markina-homolog.duckdns.org/api/health",
    ):
        with pytest.raises(CampaignPolicyError):
            validate_smoke_url("GET", url)
