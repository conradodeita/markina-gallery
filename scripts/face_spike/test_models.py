import hashlib
import json
from pathlib import Path

import pytest

from scripts.face_spike.models import clean_models, prepare_models, verify_models


def test_model_cache_verifies_hash_and_cleans_only_marked_root(tmp_path: Path) -> None:
    source = tmp_path / "source.onnx"
    source.write_bytes(b"synthetic-model-for-test")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "models": {
                    "test": {
                        "filename": "test.onnx",
                        "url": source.as_uri(),
                        "bytes": source.stat().st_size,
                        "sha256": digest,
                        "license": "test-only",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    model_root = tmp_path / "markina-face-spike-models"

    prepared = prepare_models(manifest, model_root)

    assert prepared["test"]["sha256"] == digest
    assert verify_models(manifest, model_root) == prepared
    clean_models(model_root)
    assert not model_root.exists()


def test_model_cleanup_refuses_unmarked_directory(tmp_path: Path) -> None:
    model_root = tmp_path / "unmarked"
    model_root.mkdir()
    retained = model_root / "keep.txt"
    retained.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="Marcador"):
        clean_models(model_root)

    assert retained.is_file()
