"""Provider YuNet/SFace mínimo, isolado das ferramentas de benchmark."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

EXPECTED_EMBEDDING_DIMENSIONS = 128
MAX_DETECTION_SIDE = 1600
MAX_DETECTION_PIXELS = 2_000_000


class FacialProviderError(RuntimeError):
    """Falha técnica sanitizada no runtime facial."""


@dataclass(frozen=True)
class FaceObservation:
    embedding: tuple[float, ...]
    detection_confidence: float
    box: tuple[int, int, int, int]
    landmarks: tuple[tuple[float, float], ...]
    blur_variance: float


@dataclass(frozen=True)
class QueryAnalysis:
    status: Literal["ready", "no_face", "multiple_faces", "low_quality"]
    observation: FaceObservation | None = None


def normalize_embedding(values: Any) -> tuple[float, ...]:
    flattened = values.reshape(-1) if hasattr(values, "reshape") else values
    if hasattr(flattened, "tolist"):
        flattened = flattened.tolist()
    vector = tuple(float(value) for value in flattened)
    if len(vector) != EXPECTED_EMBEDDING_DIMENSIONS or not all(
        math.isfinite(value) for value in vector
    ):
        raise FacialProviderError("Dimensão de embedding facial inválida.")
    norm = math.sqrt(sum(value * value for value in vector))
    if not math.isfinite(norm) or norm <= 0:
        raise FacialProviderError("Embedding facial inválido.")
    return tuple(value / norm for value in vector)


def analyze_query(
    observations: list[FaceObservation],
    *,
    minimum_face_pixels: int = 72,
    minimum_blur_variance: float = 18.0,
    minimum_detection_confidence: float = 0.80,
) -> QueryAnalysis:
    if not observations:
        return QueryAnalysis(status="no_face")
    if len(observations) != 1:
        return QueryAnalysis(status="multiple_faces")
    face = observations[0]
    if (
        min(face.box[2:]) < minimum_face_pixels
        or face.blur_variance < minimum_blur_variance
        or face.detection_confidence < minimum_detection_confidence
    ):
        return QueryAnalysis(status="low_quality")
    return QueryAnalysis(status="ready", observation=face)


class OpenCvSFaceProvider:
    model_id = "opencv-yunet-sface"
    model_version = "yunet-2023mar+sface-2021dec"

    def __init__(
        self,
        yunet_path: Path,
        sface_path: Path,
        *,
        cv2_module: Any | None = None,
        detection_threshold: float = 0.75,
    ) -> None:
        if not yunet_path.is_file() or not sface_path.is_file():
            raise FacialProviderError("Modelos faciais verificados não estão disponíveis.")
        if cv2_module is None:
            try:
                import cv2 as cv2_module
            except ImportError as exc:
                raise FacialProviderError("Runtime facial indisponível.") from exc
        try:
            self._cv2 = cv2_module
            self._detector = cv2_module.FaceDetectorYN.create(
                str(yunet_path), "", (320, 320), detection_threshold, 0.3, 5000
            )
            self._recognizer = cv2_module.FaceRecognizerSF.create(str(sface_path), "")
        except Exception as exc:
            raise FacialProviderError("Modelos faciais não puderam ser carregados.") from exc

    def observe_path(self, image_path: Path) -> list[FaceObservation]:
        try:
            image = self._cv2.imread(str(image_path))
        except Exception as exc:
            raise FacialProviderError("Imagem facial não pôde ser lida.") from exc
        return self.observe_image(image)

    def observe_bytes(self, payload: bytes) -> list[FaceObservation]:
        if not payload:
            raise FacialProviderError("Imagem facial não pôde ser lida.")
        try:
            import numpy as np

            image = self._cv2.imdecode(
                np.frombuffer(payload, dtype=np.uint8), self._cv2.IMREAD_COLOR
            )
        except (ImportError, Exception) as exc:
            raise FacialProviderError("Imagem facial não pôde ser lida.") from exc
        return self.observe_image(image)

    def observe_image(self, image: Any) -> list[FaceObservation]:
        if image is None or not hasattr(image, "shape") or len(image.shape) < 2:
            raise FacialProviderError("Imagem facial não pôde ser lida.")
        height, width = int(image.shape[0]), int(image.shape[1])
        if height < 1 or width < 1:
            raise FacialProviderError("Imagem facial não pôde ser lida.")
        try:
            image = self._bounded_detection_image(image, width=width, height=height)
            height, width = int(image.shape[0]), int(image.shape[1])
            self._detector.setInputSize((width, height))
            _, detected = self._detector.detect(image)
            if detected is None:
                return []
            observations: list[FaceObservation] = []
            for face in detected:
                aligned = self._recognizer.alignCrop(image, face)
                embedding = normalize_embedding(self._recognizer.feature(aligned))
                gray = self._cv2.cvtColor(aligned, self._cv2.COLOR_BGR2GRAY)
                blur = float(self._cv2.Laplacian(gray, self._cv2.CV_64F).var())
                observations.append(
                    FaceObservation(
                        embedding=embedding,
                        detection_confidence=float(face[-1]),
                        box=tuple(round(float(value)) for value in face[:4]),
                        landmarks=tuple(
                            (float(face[offset]), float(face[offset + 1]))
                            for offset in range(4, 14, 2)
                        ),
                        blur_variance=blur,
                    )
                )
            return observations
        except FacialProviderError:
            raise
        except Exception as exc:
            raise FacialProviderError("Processamento facial falhou.") from exc

    def _bounded_detection_image(
        self, image: Any, *, width: int, height: int
    ) -> Any:
        side_scale = MAX_DETECTION_SIDE / max(width, height)
        pixel_scale = math.sqrt(MAX_DETECTION_PIXELS / (width * height))
        scale = min(1.0, side_scale, pixel_scale)
        if scale >= 1.0:
            return image
        target_width = max(1, math.floor(width * scale))
        target_height = max(1, math.floor(height * scale))
        return self._cv2.resize(
            image,
            (target_width, target_height),
            interpolation=self._cv2.INTER_AREA,
        )
