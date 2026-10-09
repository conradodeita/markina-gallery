from uuid import UUID

import pytest

from app import remote_test_otp
from app.remote_test_otp import RemoteTestOtpError
from app.whatsapp_delivery import decrypt_otp

TENANT_A = UUID("7f1f8b5a-905c-4c35-9cd8-87759af31c01")
TENANT_B = UUID("b67d881d-d577-40d8-af5e-0a4368ea6002")
CHALLENGE = UUID("8132cd52-0b15-43b9-85b7-920e18d4e64f")
RESEND_COUNT = 1
OTP_KEY = b"k" * 32
RUNNER_SECRET = "runner-secret-for-synthetic-otp-tests-only"


class MemoryRedis:
    values = {}
    calls = []

    @classmethod
    def from_url(cls, url, **kwargs):
        cls.calls.append((url, kwargs))
        return cls()

    def set(self, key, value, *, ex, nx):
        if nx and key in self.values:
            return None
        self.values[key] = value
        self.calls.append(("set", key, ex, nx))
        return True

    def getdel(self, key):
        self.calls.append(("getdel", key))
        return self.values.pop(key, None)

    def delete(self, key):
        self.calls.append(("delete", key))
        return int(self.values.pop(key, None) is not None)


def enable_sink(monkeypatch):
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("PYP_REMOTE_TEST_OTP_ENABLED", "1")
    monkeypatch.setenv("PYP_REMOTE_TEST_OTP_SECRET", RUNNER_SECRET)
    monkeypatch.setenv("PYP_REMOTE_TEST_OTP_TENANTS", f"{TENANT_A},{TENANT_B}")
    monkeypatch.setattr(remote_test_otp, "Redis", MemoryRedis)
    monkeypatch.setattr(remote_test_otp, "otp_encryption_key", lambda: OTP_KEY)
    MemoryRedis.values.clear()
    MemoryRedis.calls.clear()


def test_sink_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("PYP_REMOTE_TEST_OTP_ENABLED", raising=False)
    monkeypatch.delenv("PYP_REMOTE_TEST_OTP_SECRET", raising=False)
    monkeypatch.delenv("PYP_REMOTE_TEST_OTP_TENANTS", raising=False)

    assert not remote_test_otp.is_remote_test_otp_tenant(TENANT_A)
    assert not remote_test_otp.authorize_remote_test_otp(TENANT_A, RUNNER_SECRET)


def test_sink_refuses_non_homolog_environment(monkeypatch):
    enable_sink(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(RemoteTestOtpError):
        remote_test_otp.is_remote_test_otp_tenant(TENANT_A)


def test_invalid_configuration_fails_closed(monkeypatch):
    enable_sink(monkeypatch)
    monkeypatch.setenv("PYP_REMOTE_TEST_OTP_SECRET", "short")

    with pytest.raises(RemoteTestOtpError):
        remote_test_otp.is_remote_test_otp_tenant(TENANT_A)


def test_publish_is_encrypted_tenant_scoped_and_expires(monkeypatch):
    enable_sink(monkeypatch)
    otp = "731904"

    remote_test_otp.publish_remote_test_otp(TENANT_A, CHALLENGE, RESEND_COUNT, otp)

    key = remote_test_otp._key(TENANT_A, CHALLENGE, RESEND_COUNT)
    ciphertext = MemoryRedis.values[key]
    assert ciphertext != otp
    assert decrypt_otp(
        ciphertext,
        key=OTP_KEY,
        context=f"remote-test-otp:{TENANT_A}:{CHALLENGE}",
    ) == otp
    assert ("set", key, 600, True) in MemoryRedis.calls
    with pytest.raises(RemoteTestOtpError):
        remote_test_otp.publish_remote_test_otp(UUID(int=0), CHALLENGE, RESEND_COUNT, otp)


def test_consume_requires_exact_secret_and_is_one_time(monkeypatch):
    enable_sink(monkeypatch)
    remote_test_otp.publish_remote_test_otp(TENANT_A, CHALLENGE, RESEND_COUNT, "083275")

    assert not remote_test_otp.authorize_remote_test_otp(TENANT_A, "wrong-secret")
    assert not remote_test_otp.authorize_remote_test_otp(TENANT_B, "wrong-secret")
    assert remote_test_otp.authorize_remote_test_otp(TENANT_A, RUNNER_SECRET)
    assert remote_test_otp.consume_remote_test_otp(TENANT_A, CHALLENGE, RESEND_COUNT) == "083275"
    assert remote_test_otp.consume_remote_test_otp(TENANT_A, CHALLENGE, RESEND_COUNT) is None
    reads = [call for call in MemoryRedis.calls if call[0] == "getdel"]
    assert reads == [
        ("getdel", remote_test_otp._key(TENANT_A, CHALLENGE, RESEND_COUNT)),
        ("getdel", remote_test_otp._key(TENANT_A, CHALLENGE, RESEND_COUNT)),
    ]


def test_resend_replaces_the_prior_encrypted_generation(monkeypatch):
    enable_sink(monkeypatch)
    remote_test_otp.publish_remote_test_otp(TENANT_A, CHALLENGE, 0, "731904")

    remote_test_otp.publish_remote_test_otp(TENANT_A, CHALLENGE, 1, "083275")

    assert remote_test_otp._key(TENANT_A, CHALLENGE, 0) not in MemoryRedis.values
    assert remote_test_otp.consume_remote_test_otp(TENANT_A, CHALLENGE, 0) is None
    assert remote_test_otp.consume_remote_test_otp(TENANT_A, CHALLENGE, 1) == "083275"
