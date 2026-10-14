"""Planejamento e consolidação determinísticos, independentes do modelo de embedding."""

import json
import math
import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DetectionConfig:
    # Hipóteses de homologação versionadas; não são parâmetros calibrados de produção.
    global_side: int = 1600
    multiscale_side: int = 2400
    tile_side: int = 1024
    overlap: float = 0.25
    nms_iou: float = 0.4
    max_tiles: int = 64
    max_candidates: int = 2048
    max_faces: int = 256
    confidence: float = 0.75
    difficult_confidence: float = 0.85
    group_count: int = 4
    small_face_fraction: float = 0.06
    large_face_fraction: float = 0.18

    def __post_init__(self):
        if not (
            256 <= self.global_side <= 1600
            and self.global_side <= self.multiscale_side <= 3200
            and 256 <= self.tile_side <= 1600
            and 0.1 <= self.overlap <= 0.5
            and 0.1 <= self.nms_iou <= 0.8
            and 1 <= self.max_tiles <= 128
            and 1 <= self.max_faces <= self.max_candidates <= 4096
            and 0 < self.confidence <= self.difficult_confidence <= 1
            and 1 <= self.group_count <= 100
            and 0 < self.small_face_fraction < self.large_face_fraction < 1
        ):
            raise ValueError("Parâmetros de detecção inválidos.")

    @classmethod
    def from_environment(cls):
        return cls(**json.loads(os.getenv("FACIAL_DETECTION_CONFIG_JSON") or "{}"))

    def metadata(self):
        return asdict(self)


@dataclass(frozen=True)
class Detection:
    row: tuple[float, ...]  # x,y,w,h + 5 landmarks + confidence no espaço orientado
    provenance: str


def axis_starts(length, side, overlap):
    if length <= side:
        return [0]
    step = max(1, int(side * (1 - overlap)))
    return list(dict.fromkeys([*range(0, length - side, step), length - side]))


def tiles(width, height, config):
    return [
        (x, y, min(config.tile_side, width - x), min(config.tile_side, height - y))
        for y in axis_starts(height, config.tile_side, config.overlap)
        for x in axis_starts(width, config.tile_side, config.overlap)
    ]


def restore(row, *, scale_x=1.0, scale_y=1.0, offset_x=0, offset_y=0):
    values = [float(v) for v in row]
    if len(values) != 15 or not all(math.isfinite(v) for v in values):
        raise ValueError("Geometria facial inválida.")
    values[0], values[1] = values[0] / scale_x + offset_x, values[1] / scale_y + offset_y
    values[2], values[3] = values[2] / scale_x, values[3] / scale_y
    for offset in range(4, 14, 2):
        values[offset] = values[offset] / scale_x + offset_x
        values[offset + 1] = values[offset + 1] / scale_y + offset_y
    return tuple(values)


def iou(a, b):
    x, y = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    area = max(0, right - x) * max(0, bottom - y)
    union = a[2] * a[3] + b[2] * b[3] - area
    return area / union if union > 0 else 0.0


def deduplicate(detections, threshold):
    ordered = sorted(detections, key=lambda d: (-d.row[-1], d.row[:4], d.provenance))
    kept = []
    for detection in ordered:
        if detection.row[2] <= 0 or detection.row[3] <= 0:
            continue
        if not any(iou(detection.row, other.row) >= threshold for other in kept):
            kept.append(detection)
    return sorted(kept, key=lambda d: (d.row[1], d.row[0], d.provenance))


def difficulty(width, height, detections, config):
    if max(width, height) <= config.global_side:
        return []
    reasons = []
    if not detections:
        reasons.append("global_empty")
    if len(detections) >= config.group_count:
        reasons.append("group")
    for item in detections:
        x, y, w, h = item.row[:4]
        if min(w, h) / max(width, height) < config.small_face_fraction:
            reasons.append("small_face")
        if item.row[-1] < config.difficult_confidence:
            reasons.append("confidence")
        if x < w * 0.2 or y < h * 0.2 or x + w * 1.2 > width or y + h * 1.2 > height:
            reasons.append("border")
    if width * height > 8_000_000 and not (
        len(detections) == 1
        and min(detections[0].row[2:4]) / max(width, height) >= config.large_face_fraction
    ):
        reasons.append("resolution")
    return sorted(set(reasons))


def normalized_box(box, width, height):
    x, y, w, h = box
    left, top = max(0.0, x / width), max(0.0, y / height)
    right, bottom = min(1.0, (x + w) / width), min(1.0, (y + h) / height)
    if right <= left or bottom <= top:
        raise ValueError("Caixa fora da geometria.")
    return left, top, right - left, bottom - top
