"""Contrato isolado do provider YuNet/SFace."""

import math
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.facial.detection import Detection
from app.facial.provider import (
    FaceObservation,
    FacialProviderError,
    OpenCvSFaceProvider,
    analyze_query,
    normalize_embedding,
)
from app.facial.reference import (
    decode_reference_bytes,
    observe_reference_image,
    reference_candidates,
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

    def setScoreThreshold(self, threshold) -> None:
        self.score_threshold = threshold

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


def test_reference_detection_embeds_only_two_faces_before_multiple_face_rejection(
    tmp_path: Path,
) -> None:
    rows = [
        [x, 20, 120, 120, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, confidence]
        for x, confidence in ((20, 0.99), (200, 0.98), (400, 0.97))
    ]
    provider = OpenCvSFaceProvider(*_model_files(tmp_path), cv2_module=FakeCv2(rows))

    observations = observe_reference_image(provider, FakeImage())

    assert len(observations) == 2
    assert analyze_query(observations).status == "multiple_faces"
    assert provider.last_metrics["embedding_successes"] == 2


def test_reference_bytes_preserve_exif_orientation_and_reject_pixel_budget() -> None:
    image = Image.new("RGB", (120, 60), "white")
    exif = image.getexif()
    exif[274] = 6
    payload = BytesIO()
    image.save(payload, format="JPEG", exif=exif.tobytes())

    with Image.open(BytesIO(payload.getvalue())) as opened:
        assert opened.getexif()[274] == 6

    decoded = decode_reference_bytes(payload.getvalue(), max_pixels=10_000)
    # EXIF orientation 6 rotates 90 degrees clockwise: PIL dimensions become
    # 60x120, represented by NumPy as height x width.
    assert decoded.shape == (120, 60, 3)

    with pytest.raises(FacialProviderError, match="Resolução facial inválida"):
        decode_reference_bytes(payload.getvalue(), max_pixels=100)


def test_query_requires_exactly_one_technically_usable_face() -> None:
    assert analyze_query([]).status == "no_face"
    assert analyze_query([_face(), _face()]).status == "multiple_faces"
    assert analyze_query([_face(blur=2.0)]).status == "low_quality"
    assert analyze_query([_face(confidence=0.5)]).status == "low_quality"
    assert analyze_query([_face(size=50)]).status == "low_quality"
    ready = analyze_query([_face()])
    assert ready.status == "ready"
    assert ready.observation is not None


def _portrait_row(x, y, size, confidence=0.99):
    return (x, y, size, size,
            x + size * .3, y + size * .35,
            x + size * .7, y + size * .35,
            x + size * .5, y + size * .55,
            x + size * .35, y + size * .75,
            x + size * .65, y + size * .75, confidence)


def test_reference_aligns_dominant_portrait_in_original_pixels(tmp_path):
    # O fundo tem confiança maior, mas um quarto da área do retrato.
    main = _portrait_row(30, 40, 240, .90)
    background = _portrait_row(400, 40, 120, .99)
    cv2 = FakeCv2([background, main])
    aligned_inputs = []

    def align_original(image, row):
        aligned_inputs.append((image, row))
        return image

    cv2.recognizer.alignCrop = align_original
    provider = OpenCvSFaceProvider(*_model_files(tmp_path), cv2_module=cv2)
    image = FakeImage()
    observations = observe_reference_image(provider, image)
    assert len(observations) == 1
    assert observations[0].box == (30, 40, 240, 240)
    assert analyze_query(observations).status == "ready"
    assert len(aligned_inputs) == 1
    assert aligned_inputs[0][0] is image


def test_reference_consolidates_same_landmarks_across_different_scale_boxes():
    main = _portrait_row(100, 100, 200)
    # IoU 0.25 é menor que NMS 0.4, mas são os mesmos landmarks no espaço original.
    duplicate = (150, 150, 100, 100, *main[4:14], .95)
    result = reference_candidates([Detection(main, "global"), Detection(duplicate, "tile:0")],
                                  width=800, height=600, nms_iou=.4)
    assert len(result) == 1
    assert result[0].row == main


def test_reference_consolidates_same_landmarks_when_scale_boxes_have_low_iou():
    main = _portrait_row(100, 100, 200)
    # Mesmo rosto detectado em outra escala: landmarks iguais, mas a caixa menor
    # tem IoU abaixo do limiar NMS por causa da diferença de tamanho.
    duplicate = (160, 160, 80, 80, *main[4:14], .95)
    result = reference_candidates([Detection(main, "global"), Detection(duplicate, "tile:0")],
                                  width=800, height=600, nms_iou=.4)
    assert len(result) == 1
    assert result[0].row == main


@pytest.mark.parametrize("main_size,background_size,confidence", [
    (240, 180, .99),  # rostos comparáveis
    (120, 40, .99),   # retrato não ocupa 18% do lado maior
    (240, 80, .84),   # dominância não pode compensar baixa confiança
])
def test_reference_keeps_ambiguous_candidates(main_size, background_size, confidence):
    detections = [Detection(_portrait_row(10, 10, main_size, confidence), "global"),
                  Detection(_portrait_row(500, 10, background_size), "global")]
    assert len(reference_candidates(detections, width=800, height=600, nms_iou=.4)) == 2
