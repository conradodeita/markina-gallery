import os
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image

from app.facial.crypto import (
    FacialCryptoContext,
    FacialCryptoContextPair,
    FacialCryptoError,
)
from app.facial.reference_store import FacialReferenceError, FacialReferenceStore


def _context(environment: str) -> FacialCryptoContext:
    return FacialCryptoContext.from_keyring(
        environment=environment,
        active_key_id="synthetic-key",
        keys={"synthetic-key": b"k" * 32},
    )


def _jpeg() -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 2), color=(20, 40, 60)).save(output, format="JPEG")
    return output.getvalue()


def _store(root, context: FacialCryptoContext) -> FacialReferenceStore:
    return FacialReferenceStore(
        root,
        context.cipher,
        max_bytes=100_000,
        max_pixels=100,
        environment_context=context,
    )


def test_context_pair_keeps_distinct_source_and_destination_without_environment_write(
    monkeypatch,
):
    monkeypatch.setenv("APP_ENV", "test")
    before = os.environ["APP_ENV"]

    pair = FacialCryptoContextPair(
        source=_context("staging"), destination=_context("production")
    )

    assert pair.source.environment == "staging"
    assert pair.destination.environment == "production"
    assert os.environ["APP_ENV"] == before


@pytest.mark.parametrize("environment", ["", " staging", "staging ", "unknown!", "A"])
def test_invalid_environment_context_fails_closed(environment):
    with pytest.raises(FacialCryptoError, match="Contexto criptográfico facial inválido"):
        _context(environment)


def test_equal_environments_are_not_a_migration_pair():
    with pytest.raises(FacialCryptoError, match="devem ser distintos"):
        FacialCryptoContextPair(
            source=_context("staging"), destination=_context("staging")
        )


@pytest.mark.parametrize(
    ("active_key_id", "keys"),
    [
        ("missing", {"synthetic-key": b"k" * 32}),
        ("synthetic-key", {"synthetic-key": b"k" * 31}),
        ("synthetic-key", {"synthetic-key": "k" * 32}),
        ("synthetic-key", None),
    ],
)
def test_invalid_keyring_fails_before_any_reference_path_is_created(
    tmp_path, active_key_id, keys
):
    root = tmp_path / "not-written"

    with pytest.raises(FacialCryptoError, match="Chave criptográfica facial indisponível"):
        FacialCryptoContext.from_keyring(
            environment="staging",
            active_key_id=active_key_id,
            keys=keys,
        )

    assert not root.exists()


def test_explicit_reference_context_ignores_app_env_value_and_roundtrips(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("APP_ENV", "production")
    before = os.environ["APP_ENV"]
    context = _context("staging")
    root = tmp_path / "references"
    store = _store(root, context)
    request_id = uuid4()
    gallery_id = uuid4()
    payload = _jpeg()

    stored = store.store(
        request_id=request_id,
        gallery_id=gallery_id,
        model_version="synthetic-model-v1",
        data_version="synthetic-consent-v1",
        payload=payload,
    )
    loaded = store.load(
        request_id=request_id,
        gallery_id=gallery_id,
        model_version="synthetic-model-v1",
        data_version="synthetic-consent-v1",
        locator=stored.locator,
    )

    assert loaded == payload
    assert store._scope(
        request_id=request_id,
        gallery_id=gallery_id,
        model_version="synthetic-model-v1",
        data_version="synthetic-consent-v1",
        purpose="reference_image",
    ).environment == "staging"
    assert os.environ["APP_ENV"] == before


def test_invalid_reference_scope_fails_before_first_filesystem_write(tmp_path):
    root = tmp_path / "not-written"
    context = _context("staging")
    store = _store(root, context)

    with pytest.raises(FacialCryptoError, match="Escopo criptográfico facial inválido"):
        store.store(
            request_id=uuid4(),
            gallery_id=uuid4(),
            model_version="",
            data_version="synthetic-consent-v1",
            payload=_jpeg(),
        )

    assert not root.exists()


def test_reference_store_rejects_unvalidated_context_before_write(tmp_path):
    root = tmp_path / "not-written"
    cipher_context = _context("staging")

    with pytest.raises(FacialReferenceError, match="Contexto da referência facial inválido"):
        FacialReferenceStore(
            root,
            cipher_context.cipher,
            max_bytes=100_000,
            max_pixels=100,
            environment_context=object(),  # type: ignore[arg-type]
        )

    assert not root.exists()
