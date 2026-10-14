"""Garantias de escopo e rotação do envelope facial."""

from uuid import uuid4

import pytest

from app.facial.crypto import (
    FacialCipher,
    FacialCryptoError,
    FacialEnvelope,
    FacialScope,
)


def _scope(**changes) -> FacialScope:
    values = {
        "environment": "test",
        "gallery_id": uuid4(),
        "object_kind": "photo",
        "object_id": uuid4(),
        "purpose": "embedding",
        "model_version": "yunet+sface-v1",
        "data_version": "embedding-v1",
    }
    values.update(changes)
    return FacialScope(**values)


def test_facial_envelope_round_trip_and_random_nonce() -> None:
    cipher = FacialCipher(active_key_id="current", keys={"current": b"a" * 32})
    scope = _scope()

    first = cipher.encrypt(b"vetor normalizado", scope=scope)
    second = cipher.encrypt(b"vetor normalizado", scope=scope)

    assert cipher.decrypt(first, scope=scope) == b"vetor normalizado"
    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext


@pytest.mark.parametrize(
    "field,replacement",
    (
        ("environment", "other"),
        ("gallery_id", uuid4()),
        ("object_id", uuid4()),
        ("model_version", "other-model"),
        ("data_version", "other-data"),
    ),
)
def test_facial_envelope_rejects_scope_transplant(field: str, replacement) -> None:
    cipher = FacialCipher(active_key_id="current", keys={"current": b"a" * 32})
    original = _scope()
    envelope = cipher.encrypt(b"restrito", scope=original)
    changed_values = {
        "environment": original.environment,
        "gallery_id": original.gallery_id,
        "object_kind": original.object_kind,
        "object_id": original.object_id,
        "purpose": original.purpose,
        "model_version": original.model_version,
        "data_version": original.data_version,
    }
    changed_values[field] = replacement
    changed = FacialScope(**changed_values)

    with pytest.raises(FacialCryptoError, match="adulterado"):
        cipher.decrypt(envelope, scope=changed)


def test_facial_envelope_rejects_tampering_and_missing_key_without_leaking_ids() -> None:
    cipher = FacialCipher(active_key_id="current", keys={"current": b"a" * 32})
    scope = _scope()
    envelope = cipher.encrypt(b"restrito", scope=scope)
    tampered = FacialEnvelope(
        ciphertext=envelope.ciphertext[:-1] + bytes([envelope.ciphertext[-1] ^ 1]),
        nonce=envelope.nonce,
        key_id=envelope.key_id,
    )
    with pytest.raises(FacialCryptoError, match="adulterado"):
        cipher.decrypt(tampered, scope=scope)

    unknown = FacialEnvelope(
        ciphertext=envelope.ciphertext,
        nonce=envelope.nonce,
        key_id="retired-secret-key-id",
    )
    with pytest.raises(FacialCryptoError) as captured:
        cipher.decrypt(unknown, scope=scope)
    assert "retired-secret-key-id" not in str(captured.value)


def test_facial_envelope_rotates_from_authorized_old_key_only() -> None:
    scope = _scope()
    old_cipher = FacialCipher(active_key_id="old", keys={"old": b"o" * 32})
    old_envelope = old_cipher.encrypt(b"restrito", scope=scope)
    rotating = FacialCipher(
        active_key_id="current", keys={"old": b"o" * 32, "current": b"n" * 32}
    )

    rotated = rotating.rotate(old_envelope, scope=scope)

    assert rotated.key_id == "current"
    assert rotating.decrypt(rotated, scope=scope) == b"restrito"
    with pytest.raises(FacialCryptoError, match="indisponível"):
        FacialCipher(active_key_id="current", keys={"current": b"n" * 32}).decrypt(
            old_envelope, scope=scope
        )
