"""Provisionamento com fronteira Hugging Face falsa, sem download de pesos."""
import json
import sys
from types import SimpleNamespace

import pytest

from app.facial.gemma_assets import (
    MARKER_NAME,
    GemmaAssetError,
    prepare_gemma_model,
    verify_gemma_model,
)
from app.facial.gemma_provider import GEMMA_MODEL_REPO_ID, GEMMA_MODEL_REVISION


@pytest.mark.parametrize("marker", [[], {}, {"model_id": GEMMA_MODEL_REPO_ID, "revision": "wrong"}])
def test_invalid_revision_marker_is_rejected(tmp_path, marker):
    (tmp_path / MARKER_NAME).write_text(json.dumps(marker), encoding="utf-8")
    (tmp_path / "modules.json").write_text("[]", encoding="utf-8")
    (tmp_path / "model.safetensors").write_bytes(b"synthetic")
    with pytest.raises(GemmaAssetError):
        verify_gemma_model(tmp_path)


def test_prepare_pins_revision_and_never_replaces_unverified_cache(tmp_path, monkeypatch):
    calls = []
    def download(**kwargs):
        calls.append(kwargs)
        (tmp_path / "modules.json").write_text("[]", encoding="utf-8")
        (tmp_path / "model.safetensors").write_bytes(b"synthetic")
        (tmp_path / "chat_template.jinja").write_text("synthetic-template", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(snapshot_download=download))
    prepare_gemma_model(tmp_path)
    verify_gemma_model(tmp_path)
    assert calls[0]["repo_id"] == GEMMA_MODEL_REPO_ID and calls[0]["revision"] == GEMMA_MODEL_REVISION
    assert "*.jinja" in calls[0]["allow_patterns"]
    prepare_gemma_model(tmp_path)
    assert len(calls) == 1
    (tmp_path / MARKER_NAME).write_text("{}", encoding="utf-8")
    with pytest.raises(GemmaAssetError, match="Cache"):
        prepare_gemma_model(tmp_path)
    assert len(calls) == 1 and (tmp_path / "model.safetensors").read_bytes() == b"synthetic"


def test_incomplete_pinned_cache_without_image_template_is_rejected(tmp_path):
    (tmp_path / MARKER_NAME).write_text(json.dumps({
        "model_id": GEMMA_MODEL_REPO_ID, "revision": GEMMA_MODEL_REVISION,
    }), encoding="utf-8")
    (tmp_path / "modules.json").write_text("[]", encoding="utf-8")
    (tmp_path / "model.safetensors").write_bytes(b"synthetic")
    with pytest.raises(GemmaAssetError):
        verify_gemma_model(tmp_path)
