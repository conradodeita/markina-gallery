"""Fail-closed request policy for authenticated remote browser journeys."""

from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

from tests.remote_campaign_policy import ALLOWED_BASE_URL, CampaignPolicyError

_ALLOWED_POSTS = {
    "/api/auth/admin/password",
    "/api/auth/admin/totp",
    "/api/auth/client/challenge",
    "/api/auth/client/verify",
    "/api/auth/test/client-otp/consume",
    "/api/auth/logout",
}


def validate_functional_request(method: str, url: str) -> str:
    """Permit same-origin reads and only login/selection/session operations."""
    if not isinstance(method, str) or not isinstance(url, str) or not url:
        raise CampaignPolicyError("functional_request_invalid")
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise CampaignPolicyError("functional_request_invalid") from exc
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "markina-homolog.duckdns.org"
        or parsed.hostname != "markina-homolog.duckdns.org"
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise CampaignPolicyError("functional_target_not_allowlisted")

    verb = method.upper()
    path = parsed.path
    if verb in {"GET", "HEAD"}:
        return ALLOWED_BASE_URL + path
    if verb == "POST" and (path in _ALLOWED_POSTS or _is_selection(path)):
        return ALLOWED_BASE_URL + path
    if verb == "DELETE" and _is_selection(path):
        return ALLOWED_BASE_URL + path
    raise CampaignPolicyError("functional_operation_not_allowlisted")


def _is_selection(path: str) -> bool:
    parts = path.strip("/").split("/")
    if len(parts) != 6 or parts[0:2] != ["api", "public-galleries"]:
        return False
    if parts[3] != "photos" or parts[5] != "selection":
        return False
    try:
        UUID(parts[2])
        UUID(parts[4])
    except ValueError:
        return False
    return True
