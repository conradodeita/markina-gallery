"""Armazenamento temporário cifrado da foto de referência."""

from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from app.facial.crypto import FacialCipher
from app.facial.reference_store import FacialReferenceError, FacialReferenceStore


def _jpeg(width: int = 40, height: int = 30) -> bytes:
    stream = BytesIO()
    Image.new("RGB", (width, height), (120, 100, 80)).save(stream, format="JPEG")
    return stream.getvalue()


def _png() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (20, 20), (120, 100, 80)).save(stream, format="PNG")
    return stream.getvalue()


def _store(tmp_path: Path, *, max_bytes: int = 100_000, max_pixels: int = 10_000):
    return FacialReferenceStore(
        tmp_path / "facial-temporary",
        FacialCipher(active_key_id="test", keys={"test": b"k" * 32}),
        max_bytes=max_bytes,
        max_pixels=max_pixels,
    )


def test_reference_is_ciphered_round_trips_and_deletes_idempotently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    store = _store(tmp_path)
    request_id, gallery_id = uuid4(), uuid4()
    payload = _jpeg()

    stored = store.store(
        request_id=request_id,
        gallery_id=gallery_id,
        model_version="model-v1",
        data_version="reference-v1",
        payload=payload,
    )

    disk = (tmp_path / "facial-temporary" / f"{request_id}.reference").read_bytes()
    assert payload not in disk
    assert stored.width == 40 and stored.height == 30
    assert store.load(
        request_id=request_id,
        gallery_id=gallery_id,
        model_version="model-v1",
        data_version="reference-v1",
        locator=stored.locator,
    ) == payload
    assert store.delete(
        request_id=request_id,
        gallery_id=gallery_id,
        model_version="model-v1",
        data_version="reference-v1",
        locator=stored.locator,
    ) is True
    assert store.delete(
        request_id=request_id,
        gallery_id=gallery_id,
        model_version="model-v1",
        data_version="reference-v1",
    ) is False


def test_reference_rejects_format_bytes_pixels_and_decompression_bomb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request_id, gallery_id = uuid4(), uuid4()
    arguments = {
        "request_id": request_id,
        "gallery_id": gallery_id,
        "model_version": "model-v1",
        "data_version": "reference-v1",
    }
    with pytest.raises(FacialReferenceError, match="JPEG"):
        _store(tmp_path).store(payload=_png(), **arguments)
    with pytest.raises(FacialReferenceError, match="bytes|limite"):
        _store(tmp_path, max_bytes=10).store(payload=_jpeg(), **arguments)
    with pytest.raises(FacialReferenceError, match="pixels"):
        _store(tmp_path, max_pixels=100).store(payload=_jpeg(20, 20), **arguments)

    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(FacialReferenceError, match="seguro"):
        _store(tmp_path, max_pixels=10_000).store(payload=_jpeg(20, 20), **arguments)


def test_reference_locator_cannot_cross_request_gallery_or_escape_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    store = _store(tmp_path)
    request_id, gallery_id = uuid4(), uuid4()
    stored = store.store(
        request_id=request_id,
        gallery_id=gallery_id,
        model_version="model-v1",
        data_version="reference-v1",
        payload=_jpeg(),
    )
    for changed_request, changed_gallery in (
        (uuid4(), gallery_id),
        (request_id, uuid4()),
    ):
        with pytest.raises(FacialReferenceError, match="Localizador"):
            store.load(
                request_id=changed_request,
                gallery_id=changed_gallery,
                model_version="model-v1",
                data_version="reference-v1",
                locator=stored.locator,
            )

    outside = tmp_path / "outside.reference"
    outside.write_text("preservar", encoding="utf-8")
    assert store.delete(
        request_id=uuid4(),
        gallery_id=gallery_id,
        model_version="model-v1",
        data_version="reference-v1",
    ) is False
    assert outside.read_text(encoding="utf-8") == "preservar"
