from pathlib import Path

import numpy as np
import pytest

from app.facial.gemma_assets import MARKER_NAME, GemmaAssetError, verify_gemma_model
from app.facial.gemma_provider import (
    GEMMA_MODEL_ID,
    GEMMA_MODEL_REPO_ID,
    GEMMA_MODEL_REVISION,
    GemmaFaceEmbeddingProvider,
)
from app.facial.provider import FaceObservation, FacialProviderError


class FakeCv2:
    COLOR_BGR2RGB = 1

    @staticmethod
    def cvtColor(image, _code):
        return image[:, :, ::-1]


class FakeDetector:
    _cv2 = FakeCv2()


class FakeModel:
    def __init__(self):
        self.calls = []

    def encode(self, value, **kwargs):
        self.calls.append((value, kwargs))
        return np.ones((1, 768), dtype=np.float32)


def test_gemma_encodes_aligned_face_as_normalized_768d_image_embedding():
    model = FakeModel()
    provider = GemmaFaceEmbeddingProvider(FakeDetector(), model_path=Path("unused"), model=model)

    result = provider.embed_aligned(np.zeros((16, 16, 3), dtype=np.uint8))

    assert len(result) == 768
    assert sum(value * value for value in result) == pytest.approx(1.0)
    image_payload, options = model.calls[0]
    assert set(image_payload) == {"image"}
    assert image_payload["image"].mode == "RGB"
    assert options == {"normalize_embeddings": True, "show_progress_bar": False}


def test_gemma_observations_drop_temporary_aligned_pixels_after_embedding():
    provider = GemmaFaceEmbeddingProvider(
        FakeDetector(), model_path=Path("unused"), model=FakeModel()
    )
    source = FaceObservation(
        embedding=(1.0,), detection_confidence=0.9, box=(0, 0, 40, 40),
        landmarks=(), blur_variance=50, aligned_image=np.zeros((16, 16, 3), dtype=np.uint8),
    )
    provider._detector.observe_path = lambda _path, **_kwargs: [source]

    result = provider.observe_path(Path("face.jpg"))

    assert result[0].embedding == pytest.approx((1 / (768**0.5),) * 768)
    assert result[0].aligned_image is None


def test_gemma_asset_marker_must_match_pinned_model_revision(tmp_path: Path):
    (tmp_path / MARKER_NAME).write_text(
        '{"model_id":"google/embeddinggemma-2","revision":"wrong"}', encoding="utf-8"
    )
    (tmp_path / "modules.json").write_text("[]", encoding="utf-8")
    (tmp_path / "model.safetensors").write_bytes(b"placeholder")

    with pytest.raises(GemmaAssetError):
        verify_gemma_model(tmp_path)

    assert GEMMA_MODEL_ID == "google-embeddinggemma-2"
    assert GEMMA_MODEL_REPO_ID == "google/embeddinggemma-2"
    assert len(GEMMA_MODEL_REVISION) == 40


def test_gemma_model_errors_are_sanitized():
    class FailingModel:
        def encode(self, *_args, **_kwargs):
            raise RuntimeError("raw input contains private data")

    provider = GemmaFaceEmbeddingProvider(
        FakeDetector(), model_path=Path("unused"), model=FailingModel()
    )
    with pytest.raises(FacialProviderError, match="não processou") as raised:
        provider.embed_aligned(np.zeros((16, 16, 3), dtype=np.uint8))
    assert "private data" not in str(raised.value)
