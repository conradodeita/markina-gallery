from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from app.facial.model_assets import (
    MARKER_NAME,
    FacialModelConfigurationError,
    FacialModelIntegrityError,
    load_manifest,
    prepare_models,
    verify_models,
)


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def _manifest(tmp_path: Path, *, license_name: str = "MIT") -> tuple[Path, dict[str, bytes]]:
    payloads = {"yunet": b"synthetic-yunet", "sface": b"synthetic-sface"}
    revision = "a" * 40
    models = {}
    for model_id, payload in payloads.items():
        models[model_id] = {
            "filename": f"{model_id}.onnx",
            "url": (
                "https://raw.githubusercontent.com/opencv/opencv_zoo/"
                f"{revision}/models/{model_id}/{model_id}.onnx"
            ),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "license": license_name if model_id == "yunet" else "Apache-2.0",
            "license_url": "https://example.invalid/license",
        }
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "model_version": "synthetic-v1",
                "architectures": ["amd64", "arm64"],
                "models": models,
            }
        ),
        encoding="utf-8",
    )
    return path, payloads


def test_prepare_and_verify_models_with_pinned_manifest(tmp_path: Path) -> None:
    manifest, payloads = _manifest(tmp_path)

    def opener(url: str, **_kwargs):
        model_id = "yunet" if "/yunet/" in url else "sface"
        return _Response(payloads[model_id])

    root = tmp_path / "models"
    prepared = prepare_models(manifest, root, architecture="aarch64", opener=opener)

    assert set(prepared) == {"yunet", "sface"}
    assert verify_models(manifest, root, architecture="arm64") == prepared
    assert (root / MARKER_NAME).is_file()


def test_manifest_fails_closed_for_license_architecture_and_unpinned_url(
    tmp_path: Path,
) -> None:
    manifest, _ = _manifest(tmp_path, license_name="non-commercial")
    with pytest.raises(FacialModelConfigurationError, match="Licença"):
        load_manifest(manifest, architecture="amd64")

    manifest, _ = _manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["architectures"] = ["amd64"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FacialModelConfigurationError, match="Arquiteturas"):
        load_manifest(manifest, architecture="arm64")

    manifest, _ = _manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["models"]["yunet"]["url"] = "https://example.invalid/model.onnx"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FacialModelConfigurationError, match="Origem"):
        load_manifest(manifest, architecture="amd64")


def test_verify_fails_closed_for_tampered_bytes_or_manifest(tmp_path: Path) -> None:
    manifest, payloads = _manifest(tmp_path)

    def opener(url: str, **_kwargs):
        model_id = "yunet" if "/yunet/" in url else "sface"
        return _Response(payloads[model_id])

    root = tmp_path / "models"
    prepared = prepare_models(manifest, root, architecture="amd64", opener=opener)
    prepared["yunet"].write_bytes(b"tampered")
    with pytest.raises(FacialModelIntegrityError, match="Tamanho|Integridade"):
        verify_models(manifest, root, architecture="amd64")

    prepared["yunet"].write_bytes(payloads["yunet"])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["model_version"] = "synthetic-v2"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FacialModelConfigurationError, match="outro manifesto"):
        verify_models(manifest, root, architecture="amd64")
