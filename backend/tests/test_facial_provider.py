"""Contrato isolado do provider YuNet/SFace."""

import math
from pathlib import Path

import pytest

from app.facial.provider import (
    FaceObservation,
    FacialProviderError,
    OpenCvSFaceProvider,
    analyze_query,
    normalize_embedding,
)


class FakeImage:
    shape = (480, 640, 3)


class LargeFakeImage:
    shape = (4000, 6000, 3)


class ResizedFakeImage:
    def __init__(self, width: int, height: int) -> None:
        self.shape = (height, width, 3)


class FakeVariance:
    def var(self) -> float:
        return 64.0


class FakeDetector:
    def __init__(self, faces) -> None:
        self.faces = faces
        self.input_size = None

    def setInputSize(self, size) -> None:
        self.input_size = size

    def detect(self, _image):
        return None, self.faces


class FakeRecognizer:
    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions

    def alignCrop(self, image, _face):
        return image

    def feature(self, _aligned):
        return [1.0] * self.dimensions


class Factory:
    def __init__(self, value) -> None:
        self.value = value

    def create(self, *_args):
        return self.value


class FakeCv2:
    COLOR_BGR2GRAY = 1
    CV_64F = 2
    INTER_AREA = 3

    def __init__(self, faces, *, dimensions: int = 128) -> None:
        self.detector = FakeDetector(faces)
        self.recognizer = FakeRecognizer(dimensions)
        self.FaceDetectorYN = Factory(self.detector)
        self.FaceRecognizerSF = Factory(self.recognizer)
        self.resize_calls = []

    def resize(self, _image, size, *, interpolation):
        self.resize_calls.append((size, interpolation))
        return ResizedFakeImage(*size)

    @staticmethod
    def cvtColor(image, _conversion):
        return image

    @staticmethod
    def Laplacian(_image, _depth):
        return FakeVariance()


def _face(*, blur: float = 64.0, confidence: float = 0.99, size: int = 120):
    return FaceObservation(
        embedding=normalize_embedding([1.0] * 128),
        detection_confidence=confidence,
        box=(10, 20, size, size),
        landmarks=((1.0, 1.0),) * 5,
        blur_variance=blur,
    )


def _model_files(tmp_path: Path) -> tuple[Path, Path]:
    yunet = tmp_path / "yunet.onnx"
    sface = tmp_path / "sface.onnx"
    yunet.write_bytes(b"model")
    sface.write_bytes(b"model")
    return yunet, sface


def test_provider_detects_zero_or_more_faces_and_normalizes_embedding(
    tmp_path: Path,
) -> None:
    row = [10, 20, 120, 100, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0.98]
    cv2 = FakeCv2([row])
    provider = OpenCvSFaceProvider(*_model_files(tmp_path), cv2_module=cv2)

    observations = provider.observe_image(FakeImage())

    assert cv2.detector.input_size == (640, 480)
    assert len(observations) == 1
    assert len(observations[0].embedding) == 128
    assert math.isclose(sum(value * value for value in observations[0].embedding), 1.0)
    assert observations[0].box == (10, 20, 120, 100)
    assert len(observations[0].landmarks) == 5

    empty = OpenCvSFaceProvider(
        *_model_files(tmp_path), cv2_module=FakeCv2(None)
    )
    assert empty.observe_image(FakeImage()) == []


def test_provider_rejects_wrong_embedding_dimensions_and_sanitizes_failure(
    tmp_path: Path,
) -> None:
    row = [10, 20, 120, 100, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0.98]
    provider = OpenCvSFaceProvider(
        *_model_files(tmp_path), cv2_module=FakeCv2([row], dimensions=127)
    )
    with pytest.raises(FacialProviderError, match="Dimensão"):
        provider.observe_image(FakeImage())
    with pytest.raises(FacialProviderError, match="não pôde ser lida"):
        provider.observe_image(None)


def test_provider_bounds_high_resolution_detection_without_changing_contract(
    tmp_path: Path,
) -> None:
    cv2 = FakeCv2(None)
    provider = OpenCvSFaceProvider(*_model_files(tmp_path), cv2_module=cv2)

    assert provider.observe_image(LargeFakeImage()) == []

    assert len(cv2.resize_calls) == 1
    (width, height), interpolation = cv2.resize_calls[0]
    assert interpolation == cv2.INTER_AREA
    assert width / height == pytest.approx(1.5, rel=0.01)
    assert max(width, height) <= 1600
    assert width * height <= 2_000_000
    assert cv2.detector.input_size == (width, height)


def test_query_requires_exactly_one_technically_usable_face() -> None:
    assert analyze_query([]).status == "no_face"
    assert analyze_query([_face(), _face()]).status == "multiple_faces"
    assert analyze_query([_face(blur=2.0)]).status == "low_quality"
    assert analyze_query([_face(confidence=0.5)]).status == "low_quality"
    assert analyze_query([_face(size=50)]).status == "low_quality"
    ready = analyze_query([_face()])
    assert ready.status == "ready"
    assert ready.observation is not None
