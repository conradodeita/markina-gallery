"""Decodificação e detecção limitada da referência enviada pela cliente."""

from __future__ import annotations

import math
import warnings
from io import BytesIO
from time import perf_counter
from typing import Any

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.facial.detection import (
    Detection,
    DetectionConfig,
    deduplicate,
    difficulty,
    iou,
    restore,
    tiles,
)
from app.facial.provider import (
    MAX_DETECTION_PIXELS,
    FaceObservation,
    FacialProviderError,
)


def reference_candidates(detections: list[Detection], *, width: int, height: int,
                         nms_iou: float) -> list[Detection]:
    """Consolida escalas e escolhe apenas um retrato geometricamente dominante."""
    kept: list[Detection] = []
    for candidate in sorted(deduplicate(detections, nms_iou),
                            key=lambda item: (-item.row[-1], item.row[:4])):
        duplicate = False
        for other in kept:
            tolerance = 0.15 * min(*candidate.row[2:4], *other.row[2:4])
            if iou(candidate.row, other.row) >= 0.20 and all(
                math.hypot(candidate.row[i] - other.row[i],
                           candidate.row[i + 1] - other.row[i + 1]) <= tolerance
                for i in range(4, 14, 2)
            ):
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    kept.sort(key=lambda item: (-item.row[2] * item.row[3], -item.row[-1], item.row[:4]))
    if len(kept) > 1:
        largest, second = kept[:2]
        if (largest.row[-1] >= 0.85
                and min(largest.row[2:4]) >= 0.18 * max(width, height)
                and largest.row[2] * largest.row[3] >= 4 * second.row[2] * second.row[3]):
            return [largest]
    return kept


def decode_reference_bytes(payload: bytes, *, max_pixels: int) -> np.ndarray:
    """Decodifica JPEG autorizado em memória e aplica sua orientação EXIF."""
    if not payload or max_pixels < 1:
        raise FacialProviderError("Imagem facial não pôde ser lida.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as opened:
                if opened.format != "JPEG" or opened.width * opened.height > max_pixels:
                    raise FacialProviderError("Resolução facial inválida.")
                opened.load()
                return np.asarray(
                    ImageOps.exif_transpose(opened).convert("RGB")
                )[:, :, ::-1].copy()
    except FacialProviderError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        UnidentifiedImageError,
        ValueError,
    ) as exc:
        raise FacialProviderError("Imagem facial não pôde ser lida.") from exc


def observe_reference_image(
    provider: Any, image: np.ndarray, *, config: DetectionConfig | None = None
) -> list[FaceObservation]:
    """Detecta em escalas/tile limitados e alinha no espaço original da foto."""
    config = config or DetectionConfig.from_environment()
    started = perf_counter()
    detector = provider._detector
    recognizer = provider._recognizer
    cv2 = provider._cv2
    previous_threshold = provider._detection_threshold
    phase = "detection"
    metrics: dict[str, Any] = {}
    try:
        if image is None or not hasattr(image, "shape") or len(image.shape) < 2:
            raise FacialProviderError("Imagem facial não pôde ser lida.")
        height, width = image.shape[:2]
        if height < 1 or width < 1:
            raise FacialProviderError("Imagem facial não pôde ser lida.")

        detector.setScoreThreshold(config.confidence)
        detections: list[Detection] = []
        passes: list[dict[str, Any]] = []
        raw_count = 0

        def detect(view, name: str, side: int, offset_x: int = 0, offset_y: int = 0):
            nonlocal raw_count
            view_height, view_width = view.shape[:2]
            scale = min(1.0, side / max(view_width, view_height))
            if name == "global":
                scale = min(
                    scale,
                    math.sqrt(
                        MAX_DETECTION_PIXELS / (view_width * view_height)
                    ),
                )
            target = (
                max(1, int(view_width * scale)),
                max(1, int(view_height * scale)),
            )
            bounded = (
                view
                if scale == 1
                else cv2.resize(view, target, interpolation=cv2.INTER_AREA)
            )
            detector.setInputSize(target)
            _, rows = detector.detect(bounded)
            passes.append(
                {
                    "pass": name,
                    "width": target[0],
                    "height": target[1],
                    "scale": scale,
                }
            )
            for row in (() if rows is None else rows):
                raw_count += 1
                detections.append(
                    Detection(
                        restore(
                            row,
                            scale_x=target[0] / view_width,
                            scale_y=target[1] / view_height,
                            offset_x=offset_x,
                            offset_y=offset_y,
                        ),
                        name,
                    )
                )
            detections.sort(
                key=lambda item: (
                    -item.row[-1],
                    item.row[:4],
                    item.provenance,
                )
            )
            del detections[config.max_candidates :]

        detect(image, "global", config.global_side)
        reasons = difficulty(width, height, detections, config)
        tile_plan = []
        if reasons:
            detect(image, "multiscale", config.multiscale_side)
            tile_plan = tiles(width, height, config)
            for index, (x, y, tile_width, tile_height) in enumerate(
                tile_plan[: config.max_tiles]
            ):
                detect(
                    image[y : y + tile_height, x : x + tile_width],
                    f"tile:{index}",
                    config.tile_side,
                    x,
                    y,
                )

        kept = reference_candidates(detections, width=width, height=height,
                                    nms_iou=config.nms_iou)
        deduplicated_count = len(kept)
        # Dois candidatos bastam para recusar ambiguidade, mesmo se o índice
        # estiver configurado para extrair apenas um rosto por foto.
        embedding_limit = 2
        kept = kept[:embedding_limit]
        observations = []
        failures = 0
        phase = "embedding"
        for detection in kept:
            try:
                aligned = recognizer.alignCrop(
                    image, np.asarray(detection.row, dtype=np.float32)
                )
                embedding = provider.embed_aligned(aligned)
                gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
                observations.append(
                    FaceObservation(
                        embedding=embedding,
                        detection_confidence=float(detection.row[-1]),
                        box=tuple(round(value) for value in detection.row[:4]),
                        landmarks=tuple(
                            (detection.row[offset], detection.row[offset + 1])
                            for offset in range(4, 14, 2)
                        ),
                        blur_variance=float(
                            cv2.Laplacian(gray, cv2.CV_64F).var()
                        ),
                        detection_pass=detection.provenance,
                        image_width=width,
                        image_height=height,
                    )
                )
            except Exception:  # noqa: BLE001 -- sanitiza falhas do runtime facial
                failures += 1

        metrics = {
            "width": width,
            "height": height,
            "megapixels": width * height / 1_000_000,
            "elapsed_ms": round((perf_counter() - started) * 1000),
            "passes": passes,
            "reasons": reasons,
            "tiles": min(len(tile_plan), config.max_tiles),
            "budget_exhausted": (
                len(tile_plan) > config.max_tiles
                or raw_count > config.max_candidates
                or deduplicated_count > embedding_limit
            ),
            "raw_detections": raw_count,
            "deduplicated": deduplicated_count,
            "embedding_successes": len(observations),
            "embedding_failures": failures,
            "detection_failures": 0,
            "config": config.metadata(),
            "model": provider.model_id,
            "model_version": provider.model_version,
        }
        provider.last_metrics = metrics
        if failures:
            raise FacialProviderError(
                "Falha ao extrair embeddings da referência; tente outra imagem.",
                metrics=metrics.copy(),
            )
        return observations
    except FacialProviderError as exc:
        metrics.update(
            elapsed_ms=round((perf_counter() - started) * 1000),
            detection_failures=int(phase == "detection"),
        )
        provider.last_metrics = metrics
        exc.metrics = metrics.copy()
        raise
    except Exception as exc:
        metrics.update(
            elapsed_ms=round((perf_counter() - started) * 1000),
            detection_failures=int(phase == "detection"),
        )
        provider.last_metrics = metrics
        raise FacialProviderError(
            "Análise da referência facial falhou.", metrics=metrics.copy()
        ) from exc
    finally:
        detector.setScoreThreshold(previous_threshold)
