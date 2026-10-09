"""Sink OTP efêmero e exclusivo da campanha remota de homologação."""

from __future__ import annotations

import hmac
import os
from uuid import UUID

from redis import Redis

from app.whatsapp_delivery import decrypt_otp, encrypt_otp, otp_encryption_key

_TTL_SECONDS = 600
_KEY_PREFIX = "pyp:remote-test-otp:v1"


class RemoteTestOtpError(RuntimeError):
    """Falha sanitizada do sink remoto de OTP."""


def _configuration() -> tuple[str, frozenset[UUID]] | None:
    if os.getenv("PYP_REMOTE_TEST_OTP_ENABLED", "").strip() != "1":
        return None
    if os.getenv("APP_ENV", "development").strip().lower() != "homolog":
        raise RemoteTestOtpError("Sink de OTP indisponível.")
    secret = os.getenv("PYP_REMOTE_TEST_OTP_SECRET", "").strip()
    raw_tenants = os.getenv("PYP_REMOTE_TEST_OTP_TENANTS", "").strip()
    if len(secret) < 32 or not raw_tenants:
        raise RemoteTestOtpError("Sink de OTP indisponível.")
    try:
        tenant_ids = frozenset(UUID(item.strip()) for item in raw_tenants.split(","))
    except (ValueError, AttributeError):
        raise RemoteTestOtpError("Sink de OTP indisponível.") from None
    if not tenant_ids or any(str(tenant_id) not in {item.strip() for item in raw_tenants.split(",")} for tenant_id in tenant_ids):
        raise RemoteTestOtpError("Sink de OTP indisponível.")
    return secret, tenant_ids


def is_remote_test_otp_tenant(tenant_id: UUID | None) -> bool:
    config = _configuration()
    return bool(config and tenant_id and tenant_id in config[1])


def authorize_remote_test_otp(tenant_id: UUID, presented_secret: str) -> bool:
    config = _configuration()
    return bool(
        config
        and tenant_id in config[1]
        and presented_secret
        and presented_secret.isascii()
        and hmac.compare_digest(config[0], presented_secret)
    )


def _redis() -> Redis:
    url = os.getenv("FACIAL_REDIS_URL", "redis://redis:6379/0").strip()
    try:
        return Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    except (TypeError, ValueError):
        raise RemoteTestOtpError("Sink de OTP indisponível.") from None


def _key(tenant_id: UUID, challenge_id: UUID, resend_count: int) -> str:
    return f"{_KEY_PREFIX}:{tenant_id}:{challenge_id}:{resend_count}"


def publish_remote_test_otp(
    tenant_id: UUID, challenge_id: UUID, resend_count: int, code: str
) -> None:
    if not is_remote_test_otp_tenant(tenant_id):
        raise RemoteTestOtpError("Sink de OTP indisponível.")
    context = f"remote-test-otp:{tenant_id}:{challenge_id}"
    try:
        encrypted = encrypt_otp(code, key=otp_encryption_key(), context=context)
        redis_client = _redis()
        if resend_count > 0:
            redis_client.delete(_key(tenant_id, challenge_id, resend_count - 1))
        if not redis_client.set(
            _key(tenant_id, challenge_id, resend_count), encrypted,
            ex=_TTL_SECONDS, nx=True,
        ):
            raise RemoteTestOtpError("Sink de OTP indisponível.")
    except RemoteTestOtpError:
        raise
    except Exception:
        raise RemoteTestOtpError("Sink de OTP indisponível.") from None


def consume_remote_test_otp(
    tenant_id: UUID, challenge_id: UUID, resend_count: int
) -> str | None:
    if not is_remote_test_otp_tenant(tenant_id):
        return None
    context = f"remote-test-otp:{tenant_id}:{challenge_id}"
    try:
        encrypted = _redis().getdel(_key(tenant_id, challenge_id, resend_count))
        if not encrypted:
            return None
        return decrypt_otp(encrypted, key=otp_encryption_key(), context=context)
    except Exception:
        raise RemoteTestOtpError("Sink de OTP indisponível.") from None
