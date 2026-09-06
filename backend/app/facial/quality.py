"""Avaliação técnica, objetiva e versionada da face correspondente."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Literal

from app.facial.provider import FaceObservation

QUALITY_VERSION = "opencv-technical-v1"


class FacialQualityError(RuntimeError):
    """Entrada geométrica inválida para a avaliação técnica."""


@dataclass(frozen=True)
class QualityAssessment:
    version: str
    band: Literal["best", "other"]
    sharp_enough: bool
    fully_framed: bool
    large_enough: bool
    prominent_enough: bool
    pose_usable: bool
    blur_variance: float
    face_area_ratio_milli: int
    relative_prominence_milli: int
    roll_degrees_milli: int
    yaw_proxy_milli: int

    def encrypted_indicators(self) -> dict[str, bool | int | str]:
        """Payload técnico destinado somente ao envelope cifrado do índice."""

        payload = asdict(self)
        payload.pop("band")
        payload["blur_variance_milli"] = round(payload.pop("blur_variance") * 1000)
        return payload


def assess_face_quality(
    face: FaceObservation,
    *,
    image_width: int,
    image_height: int,
    largest_face_area: int | None = None,
) -> QualityAssessment:
    if image_width < 1 or image_height < 1:
        raise FacialQualityError("Dimensões da imagem inválidas.")
    x, y, width, height = face.box
    if width < 1 or height < 1 or len(face.landmarks) != 5:
        raise FacialQualityError("Geometria facial inválida.")
    image_area = image_width * image_height
    face_area = width * height
    largest = largest_face_area if largest_face_area is not None else face_area
    if largest < face_area or largest < 1:
        raise FacialQualityError("Contexto de proeminência inválido.")

    fully_framed = x > 1 and y > 1 and x + width < image_width - 1 and y + height < image_height - 1
    face_area_ratio = face_area / image_area
    relative_prominence = face_area / largest
    large_enough = min(width, height) >= 96 and face_area_ratio >= 0.02
    prominent_enough = relative_prominence >= 0.65
    sharp_enough = math.isfinite(face.blur_variance) and face.blur_variance >= 45.0

    first_eye, second_eye, nose, first_mouth, second_mouth = face.landmarks
    eye_dx = second_eye[0] - first_eye[0]
    eye_dy = second_eye[1] - first_eye[1]
    eye_distance = math.hypot(eye_dx, eye_dy)
    if eye_distance < 1:
        raise FacialQualityError("Landmarks faciais inválidos.")
    eye_mid_x = (first_eye[0] + second_eye[0]) / 2
    mouth_mid_x = (first_mouth[0] + second_mouth[0]) / 2
    face_axis_x = (eye_mid_x + mouth_mid_x) / 2
    yaw_proxy = abs(nose[0] - face_axis_x) / eye_distance
    roll_degrees = abs(math.degrees(math.atan2(eye_dy, eye_dx)))
    if roll_degrees > 90:
        roll_degrees = abs(180 - roll_degrees)
    pose_usable = yaw_proxy <= 0.30 and roll_degrees <= 15.0

    best = all(
        (sharp_enough, fully_framed, large_enough, prominent_enough, pose_usable)
    )
    return QualityAssessment(
        version=QUALITY_VERSION,
        band="best" if best else "other",
        sharp_enough=sharp_enough,
        fully_framed=fully_framed,
        large_enough=large_enough,
        prominent_enough=prominent_enough,
        pose_usable=pose_usable,
        blur_variance=face.blur_variance,
        face_area_ratio_milli=round(face_area_ratio * 1000),
        relative_prominence_milli=round(relative_prominence * 1000),
        roll_degrees_milli=round(roll_degrees * 1000),
        yaw_proxy_milli=round(yaw_proxy * 1000),
    )
