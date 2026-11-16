import base64
import json
from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.totp_crypto import (
    TotpSecretCipher,
    TotpSecretError,
    legacy_totp_dual_write_enabled,
)


def cipher(environment="test", key_id="one", keys=None):
    return TotpSecretCipher(environment=environment, active_key_id=key_id,
                            keys=keys or {key_id: b"1" * 32})


def test_envelope_round_trip_is_versioned_and_bound_to_admin_and_environment():
    admin_id = uuid4()
    encrypted = cipher().encrypt("JBSWY3DPEHPK3PXP", admin_id=admin_id)

    assert encrypted.startswith("totp:v1:one:")
    assert "JBSWY3DPEHPK3PXP" not in encrypted
    assert cipher().decrypt(encrypted, admin_id=admin_id) == "JBSWY3DPEHPK3PXP"
    with pytest.raises(TotpSecretError):
        cipher().decrypt(encrypted, admin_id=uuid4())
    with pytest.raises(TotpSecretError):
        cipher(environment="production").decrypt(encrypted, admin_id=admin_id)


def test_tampered_unknown_key_and_malformed_envelopes_fail_sanitized():
    admin_id = uuid4()
    encrypted = cipher().encrypt("synthetic-secret", admin_id=admin_id)
    parts = encrypted.split(":")
    parts[4] = ("A" if parts[4][0] != "A" else "B") + parts[4][1:]
    for candidate in (
        "totp:v2:one:n:c", "totp:v1:missing:AA:AAAA", ":".join(parts),
        "totp:v1:one:!@#$:!!invalid!!",
    ):
        with pytest.raises(TotpSecretError) as exc:
            cipher().decrypt(candidate, admin_id=admin_id)
        assert "synthetic-secret" not in str(exc.value)


def test_optional_context_binds_temporary_material_and_survives_key_rotation():
    admin_id = uuid4()
    context = f"enrollment:{uuid4()}:{uuid4()}:{uuid4()}"
    encrypted = cipher().encrypt("synthetic-secret", admin_id=admin_id, context=context)
    assert cipher().decrypt(encrypted, admin_id=admin_id, context=context) == "synthetic-secret"
    for different in (None, "another-enrollment"):
        with pytest.raises(TotpSecretError):
            cipher().decrypt(encrypted, admin_id=admin_id, context=different)
    rotated_cipher = cipher(key_id="two", keys={"one": b"1"*32, "two": b"2"*32})
    rotated = rotated_cipher.rotate(encrypted, admin_id=admin_id, context=context)
    assert rotated_cipher.decrypt(rotated, admin_id=admin_id, context=context) == "synthetic-secret"


def test_active_factor_wire_format_remains_compatible_with_previous_aad():
    admin_id = UUID("00000000-0000-0000-0000-000000000001")
    aad = b'{"admin_id":"00000000-0000-0000-0000-000000000001","environment":"test","key_id":"one","purpose":"admin-totp","v":1}'
    nonce = b"0"*12
    encrypted = AESGCM(b"1"*32).encrypt(nonce, b"synthetic-secret", aad)
    legacy = "totp:v1:one:" + base64.urlsafe_b64encode(nonce).decode().rstrip("=") + ":" + base64.urlsafe_b64encode(encrypted).decode().rstrip("=")
    assert cipher().decrypt(legacy, admin_id=admin_id) == "synthetic-secret"
    written = cipher().encrypt("synthetic-secret", admin_id=admin_id).split(":")
    decoded = [base64.urlsafe_b64decode(part + "="*(-len(part)%4)) for part in written[3:]]
    assert AESGCM(b"1"*32).decrypt(decoded[0], decoded[1], aad) == b"synthetic-secret"


def test_rotation_keeps_legacy_key_readable_until_all_envelopes_are_reprotected():
    admin_id = uuid4()
    old = cipher()
    new = cipher(key_id="two", keys={"one": b"1" * 32, "two": b"2" * 32})
    encrypted = old.encrypt("synthetic-secret", admin_id=admin_id)
    rotated = new.rotate(encrypted, admin_id=admin_id)

    assert rotated.startswith("totp:v1:two:")
    assert new.decrypt(rotated, admin_id=admin_id) == "synthetic-secret"
    assert new.rotate(rotated, admin_id=admin_id) == rotated


def test_keyring_configuration_fails_closed():
    with pytest.raises(TotpSecretError):
        TotpSecretCipher(environment="development", active_key_id="missing", keys={"old": b"1" * 32})
    with pytest.raises(TotpSecretError):
        TotpSecretCipher(environment="production", active_key_id="new", keys={"new": b"short"})


def test_environment_keyring_is_dedicated_and_bound_to_app_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ADMIN_TOTP_SECRET_ENV", raising=False)
    monkeypatch.setenv("ADMIN_TOTP_ACTIVE_KEY_ID", "current")
    monkeypatch.setenv("ADMIN_TOTP_KEYS", json.dumps({
        "current": base64.b64encode(b"k" * 32).decode("ascii"),
    }))
    with pytest.raises(TotpSecretError):
        TotpSecretCipher.from_environment()

    monkeypatch.setenv("ADMIN_TOTP_SECRET_ENV", "production")
    with pytest.raises(TotpSecretError):
        TotpSecretCipher.from_environment()

    monkeypatch.setenv("ADMIN_TOTP_SECRET_ENV", "development")
    monkeypatch.setenv("ADMIN_TOTP_KEYS", '{"current":"broken","current":"duplicate"}')
    with pytest.raises(TotpSecretError):
        TotpSecretCipher.from_environment()

    monkeypatch.setenv("ADMIN_TOTP_KEYS", json.dumps({
        "current": base64.b64encode(b"k" * 32).decode("ascii"),
    }))
    assert TotpSecretCipher.from_environment().active_key_id == "current"


def test_legacy_dual_write_requires_an_explicit_valid_boolean(monkeypatch):
    monkeypatch.delenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", raising=False)
    assert legacy_totp_dual_write_enabled() is False
    monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "true")
    assert legacy_totp_dual_write_enabled() is True
    monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "yes")
    with pytest.raises(TotpSecretError):
        legacy_totp_dual_write_enabled()
