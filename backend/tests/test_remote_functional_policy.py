import pytest

from tests.remote_campaign_policy import CampaignPolicyError
from tests.remote_functional_policy import validate_functional_request


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("GET", "https://markina-homolog.duckdns.org/"),
        ("GET", "https://markina-homolog.duckdns.org/api/public-galleries/11111111-1111-4111-8111-111111111111/photos"),
        ("POST", "https://markina-homolog.duckdns.org/api/auth/client/challenge"),
        ("POST", "https://markina-homolog.duckdns.org/api/auth/test/client-otp/consume"),
        ("POST", "https://markina-homolog.duckdns.org/api/public-galleries/11111111-1111-4111-8111-111111111111/photos/22222222-2222-4222-8222-222222222222/selection"),
        ("DELETE", "https://markina-homolog.duckdns.org/api/public-galleries/11111111-1111-4111-8111-111111111111/photos/22222222-2222-4222-8222-222222222222/selection"),
    ],
)
def test_permits_targeted_remote_journey_operations(method, url):
    assert validate_functional_request(method, url).startswith("https://markina-homolog.duckdns.org/")


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("GET", "http://markina-homolog.duckdns.org/"),
        ("GET", "https://production.example/api/health"),
        ("POST", "https://markina-homolog.duckdns.org/api/payment/confirm"),
        ("POST", "https://markina-homolog.duckdns.org/api/auth/client/resend"),
        ("DELETE", "https://markina-homolog.duckdns.org/api/admin/clients/11111111-1111-4111-8111-111111111111"),
        ("PATCH", "https://markina-homolog.duckdns.org/api/admin/settings"),
    ],
)
def test_rejects_external_and_unapproved_mutations(method, url):
    with pytest.raises(CampaignPolicyError):
        validate_functional_request(method, url)
