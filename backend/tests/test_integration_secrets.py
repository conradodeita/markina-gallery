import base64
import json
import os
import secrets
from dataclasses import replace
from uuid import uuid4

import pytest

from app.integration_secrets import IntegrationCipher, IntegrationSecretError, SecretEnvelope


@pytest.fixture
def secret_keyring(monkeypatch):
    keys = {name: base64.b64encode(secrets.token_bytes(32)).decode() for name in ("old", "new")}
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("INTEGRATION_SECRET_ENV", "development")
    monkeypatch.setenv("INTEGRATION_SECRET_ACTIVE_KEY_ID", "old")
    monkeypatch.setenv("INTEGRATION_SECRET_KEYS", json.dumps(keys))
    return keys


def test_aead_roundtrip_random_nonce_and_external_key_rotation(secret_keyring, monkeypatch):
    tenant, credential = uuid4(), uuid4()
    cipher = IntegrationCipher()
    value = "synthetic-integration-credential"
    first = cipher.encrypt(value, tenant_id=tenant, credential_id=credential)
    second = cipher.encrypt(value, tenant_id=tenant, credential_id=credential)
    assert first.ciphertext != second.ciphertext and first.nonce != second.nonce
    assert value.encode() not in first.ciphertext and value not in repr(first)
    assert SecretEnvelope.from_payload(first.payload()) == first
    monkeypatch.setenv("INTEGRATION_SECRET_ACTIVE_KEY_ID", "new")
    rotated = IntegrationCipher().rotate(first, tenant_id=tenant, credential_id=credential)
    assert rotated.key_id == "new" and rotated.ciphertext != first.ciphertext
    assert IntegrationCipher().decrypt(rotated, tenant_id=tenant, credential_id=credential) == value
    monkeypatch.setenv("INTEGRATION_SECRET_KEYS", json.dumps({"new": secret_keyring["new"]}))
    with pytest.raises(IntegrationSecretError):
        IntegrationCipher().decrypt(first, tenant_id=tenant, credential_id=credential)
    assert IntegrationCipher().decrypt(rotated, tenant_id=tenant, credential_id=credential) == value


@pytest.mark.parametrize("changed", ["tenant", "credential", "environment", "ciphertext", "nonce", "key_id"])
def test_aead_rejects_transplant_and_tampering(secret_keyring, changed):
    tenant, credential = uuid4(), uuid4()
    cipher = IntegrationCipher()
    envelope = cipher.encrypt("synthetic-key", tenant_id=tenant, credential_id=credential)
    if changed == "tenant":
        tenant = uuid4()
    elif changed == "credential":
        credential = uuid4()
    else:
        envelope = replace(envelope, **{changed: {"environment": "production", "key_id": "missing",
            "nonce": b"bad", "ciphertext": b"x" * len(envelope.ciphertext)}[changed]})
    with pytest.raises(IntegrationSecretError, match="temporariamente indisponível"):
        cipher.decrypt(envelope, tenant_id=tenant, credential_id=credential)


@pytest.mark.parametrize("variable,value", [
    ("INTEGRATION_SECRET_KEYS", "{}"), ("INTEGRATION_SECRET_KEYS", '{"a":"x","a":"y"}'),
    ("INTEGRATION_SECRET_KEYS", '{"old":"invalid"}'), ("INTEGRATION_SECRET_ENV", "production"),
    ("INTEGRATION_SECRET_ACTIVE_KEY_ID", "absent"), ("INTEGRATION_SECRET_KEYS", "[]"),
])
def test_keyring_fails_closed(secret_keyring, monkeypatch, variable, value):
    monkeypatch.setenv(variable, value)
    with pytest.raises(IntegrationSecretError):
        IntegrationCipher()


def test_no_master_key_has_no_default(monkeypatch):
    monkeypatch.delenv("INTEGRATION_SECRET_KEYS", raising=False)
    with pytest.raises(IntegrationSecretError):
        IntegrationCipher()


def test_wrong_master_material_fails_and_restored_keyring_recovers(secret_keyring, monkeypatch):
    tenant, credential = uuid4(), uuid4()
    envelope = IntegrationCipher().encrypt("synthetic-restore-value", tenant_id=tenant, credential_id=credential)
    wrong = {**secret_keyring, "old": base64.b64encode(secrets.token_bytes(32)).decode()}
    monkeypatch.setenv("INTEGRATION_SECRET_KEYS", json.dumps(wrong))
    with pytest.raises(IntegrationSecretError) as failure:
        IntegrationCipher().decrypt(envelope, tenant_id=tenant, credential_id=credential)
    assert "synthetic-restore-value" not in str(failure.value)
    monkeypatch.setenv("INTEGRATION_SECRET_KEYS", json.dumps(secret_keyring))
    assert IntegrationCipher().decrypt(envelope, tenant_id=tenant, credential_id=credential) == "synthetic-restore-value"


def test_explicit_contexts_reencrypt_without_mutating_process_environment(secret_keyring, monkeypatch):
    tenant, credential = uuid4(), uuid4()
    monkeypatch.setenv("APP_ENV", "test-process")
    monkeypatch.setenv("INTEGRATION_SECRET_ENV", "test-process")
    before = {
        name: os.environ.get(name)
        for name in ("APP_ENV", "INTEGRATION_SECRET_ENV", "INTEGRATION_SECRET_ACTIVE_KEY_ID",
                     "INTEGRATION_SECRET_KEYS")
    }
    keys = {name: base64.b64decode(value, validate=True) for name, value in secret_keyring.items()}
    source = IntegrationCipher.from_explicit_context(
        environment="staging", secret_environment="staging", active_key_id="old", keys=keys)
    destination = source.for_environment("production")
    original = source.encrypt("synthetic-mp-token", tenant_id=tenant, credential_id=credential)

    with pytest.raises(IntegrationSecretError):
        destination.decrypt(original, tenant_id=tenant, credential_id=credential)
    plaintext = source.decrypt(original, tenant_id=tenant, credential_id=credential)
    migrated = destination.encrypt(plaintext, tenant_id=tenant, credential_id=credential)
    assert migrated.environment == "production"
    assert migrated.key_id == original.key_id
    assert destination.decrypt(migrated, tenant_id=tenant, credential_id=credential) == plaintext
    with pytest.raises(IntegrationSecretError):
        source.decrypt(migrated, tenant_id=tenant, credential_id=credential)
    assert {
        name: os.environ.get(name)
        for name in before
    } == before


@pytest.mark.parametrize("environment,secret_environment,active_key_id,keys", [
    ("staging", "production", "old", {"old": b"x" * 32}),
    ("staging", "staging", "missing", {"old": b"x" * 32}),
    ("staging", "staging", "old", {"old": b"short"}),
    (" staging", " staging", "old", {"old": b"x" * 32}),
])
def test_explicit_context_rejects_mismatched_or_invalid_keyrings(
    environment, secret_environment, active_key_id, keys,
):
    with pytest.raises(IntegrationSecretError, match="temporariamente indisponível"):
        IntegrationCipher.from_explicit_context(
            environment=environment,
            secret_environment=secret_environment,
            active_key_id=active_key_id,
            keys=keys,
        )
