"""Provider YuNet/SFace mínimo, isolado das ferramentas de benchmark."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

EXPECTED_EMBEDDING_DIMENSIONS = 128
MAX_DETECTION_SIDE = 1600
MAX_DETECTION_PIXELS = 2_000_000


class FacialProviderError(RuntimeError):
    """Falha técnica sanitizada no runtime facial."""

    def __init__(self, message: str, *, metrics: dict | None = None):
        super().__init__(message)
        self.metrics = metrics or {}


@dataclass(frozen=True)
class FaceObservation:
    embedding: tuple[float, ...]
    detection_confidence: float
    box: tuple[int, int, int, int]
    landmarks: tuple[tuple[float, float], ...]
    blur_variance: float
    detection_pass: str = "global"
    image_width: int | None = None
    image_height: int | None = None


@dataclass(frozen=True)
class QueryAnalysis:
    status: Literal["ready", "no_face", "multiple_faces", "low_quality"]
    observation: FaceObservation | None = None


def normalize_embedding(values: Any, dimension: int = EXPECTED_EMBEDDING_DIMENSIONS) -> tuple[float, ...]:
    flattened = values.reshape(-1) if hasattr(values, "reshape") else values
    if hasattr(flattened, "tolist"):
        flattened = flattened.tolist()
    vector = tuple(float(value) for value in flattened)
    if len(vector) != dimension or not all(
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


class FaceEmbeddingProvider(Protocol):
    model_id: str
    model_version: str
    embedding_dimension: int

    def embed_aligned(self, image: Any) -> tuple[float, ...]: ...


class OpenCvSFaceProvider:
    model_id = "opencv-yunet-sface"
    model_version = "yunet-2023mar+sface-2021dec"
    embedding_dimension = 128

    def embed_aligned(self, image: Any) -> tuple[float, ...]:
        return normalize_embedding(self._recognizer.feature(image), self.embedding_dimension)

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
            self._detection_threshold = detection_threshold
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
                        image_width=width,
                        image_height=height,
                    )
                )
            return observations
        except FacialProviderError:
            raise
        except Exception as exc:
            raise FacialProviderError("Processamento facial falhou.") from exc

    def observe_highres_path(self, image_path: Path, *, config=None):
        """Pixels orientados pelo mesmo Pillow dos derivados; nenhum crop é persistido."""
        from time import perf_counter

        import numpy as np
        from PIL import Image, ImageOps

        from app.facial.detection import (
            Detection,
            DetectionConfig,
            deduplicate,
            difficulty,
            restore,
            tiles,
        )

        config = config or DetectionConfig.from_environment()
        started = perf_counter()
        self.last_metrics = {}  # o provider é reutilizado entre fotos
        phase = "detection"
        try:
            with Image.open(image_path) as opened:
                if opened.format != "JPEG" or opened.width * opened.height > 40_000_000:
                    raise FacialProviderError("Resolução facial inválida.")
                image = np.asarray(ImageOps.exif_transpose(opened).convert("RGB"))[:, :, ::-1].copy()
            height, width = image.shape[:2]
            detections, passes = [], []
            raw_count = 0
            self._detector.setScoreThreshold(config.confidence)

            def detect(view, name, side, x=0, y=0):
                nonlocal raw_count
                vh, vw = view.shape[:2]
                scale = min(1.0, side / max(vw, vh))
                if name == "global":
                    scale = min(scale, math.sqrt(MAX_DETECTION_PIXELS / (vw * vh)))
                target = (max(1, int(vw * scale)), max(1, int(vh * scale)))
                bounded = view if scale == 1 else self._cv2.resize(view, target, interpolation=self._cv2.INTER_AREA)
                self._detector.setInputSize(target)
                _, rows = self._detector.detect(bounded)
                passes.append({"pass": name, "width": target[0], "height": target[1], "scale": scale})
                for row in (() if rows is None else rows):
                    raw_count += 1
                    detections.append(Detection(restore(row, scale_x=target[0]/vw, scale_y=target[1]/vh,
                                                        offset_x=x, offset_y=y), name))
                detections.sort(key=lambda item: (-item.row[-1], item.row[:4], item.provenance))
                del detections[config.max_candidates:]

            detect(image, "global", config.global_side)
            reasons = difficulty(width, height, detections, config)
            tile_plan = []
            if reasons:
                detect(image, "multiscale", config.multiscale_side)
                tile_plan = tiles(width, height, config)
                for index, (x, y, w, h) in enumerate(tile_plan[:config.max_tiles]):
                    detect(image[y:y+h, x:x+w], f"tile:{index}", config.tile_side, x, y)
            kept = deduplicate(detections, config.nms_iou)
            consolidated_count = len(kept)
            kept = sorted(kept, key=lambda item: -item.row[-1])[:config.max_faces]
            observations = []
            failures = 0
            phase = "embedding"
            for detection in kept:
                try:
                    aligned = self._recognizer.alignCrop(image, np.asarray(detection.row, dtype=np.float32))
                    embedding = self.embed_aligned(aligned)
                    gray = self._cv2.cvtColor(aligned, self._cv2.COLOR_BGR2GRAY)
                    observations.append(FaceObservation(
                        embedding=embedding, detection_confidence=detection.row[-1],
                        box=tuple(round(v) for v in detection.row[:4]),
                        landmarks=tuple((detection.row[i], detection.row[i+1]) for i in range(4, 14, 2)),
                        blur_variance=float(self._cv2.Laplacian(gray, self._cv2.CV_64F).var()),
                        detection_pass=detection.provenance, image_width=width, image_height=height))
                except Exception:  # noqa: BLE001 -- qualquer falha do runtime preserva a fonte para retry
                    failures += 1
            self.last_metrics = {"width": width, "height": height, "megapixels": width*height/1e6,
                "elapsed_ms": round((perf_counter()-started)*1000), "passes": passes, "reasons": reasons,
                "tiles": min(len(tile_plan), config.max_tiles), "budget_exhausted": len(tile_plan)>config.max_tiles or raw_count>config.max_candidates or consolidated_count>config.max_faces,
                "raw_detections": raw_count, "deduplicated": consolidated_count,
                "embedding_successes": len(observations), "embedding_failures": failures,
                "detection_failures": 0,
                "config": config.metadata(), "model": self.model_id, "model_version": self.model_version}
            if failures:
                # Falha operacional preserva fonte e diagnóstico para retry.
                raise FacialProviderError("Falha ao extrair embeddings; fonte preservada para nova tentativa.")
            return observations
        except FacialProviderError as exc:
            self.last_metrics.update(elapsed_ms=round((perf_counter()-started)*1000),
                                     detection_failures=int(phase == "detection"))
            exc.metrics = self.last_metrics.copy()
            raise
        except Exception as exc:
            self.last_metrics.update(elapsed_ms=round((perf_counter()-started)*1000),
                                     detection_failures=int(phase == "detection"))
            raise FacialProviderError("Análise high-res falhou.", metrics=self.last_metrics.copy()) from exc
        finally:
            self._detector.setScoreThreshold(self._detection_threshold)

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
