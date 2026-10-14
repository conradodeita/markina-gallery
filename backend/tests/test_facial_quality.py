"""Bandas técnicas por face correspondente, sem julgamento estético."""

import pytest

from app.facial.provider import FaceObservation, normalize_embedding
from app.facial.quality import QUALITY_VERSION, FacialQualityError, assess_face_quality


def _face(
    *,
    box=(100, 80, 180, 180),
    blur=100.0,
    landmarks=((130, 125), (210, 125), (170, 160), (145, 200), (195, 200)),
) -> FaceObservation:
    return FaceObservation(
        embedding=normalize_embedding([1.0] * 128),
        detection_confidence=0.99,
        box=box,
        landmarks=landmarks,
        blur_variance=blur,
    )


def test_technically_strong_corresponding_face_is_best() -> None:
    result = assess_face_quality(
        _face(), image_width=640, image_height=480, largest_face_area=180 * 180
    )
    assert result.version == QUALITY_VERSION
    assert result.band == "best"
    assert all(
        (
            result.sharp_enough,
            result.fully_framed,
            result.large_enough,
            result.prominent_enough,
            result.pose_usable,
        )
    )
    assert "band" not in result.encrypted_indicators()


@pytest.mark.parametrize(
    "face,largest_area,failed_signal",
    (
        (_face(blur=5.0), 180 * 180, "sharp_enough"),
        (_face(box=(0, 80, 180, 180)), 180 * 180, "fully_framed"),
        (_face(box=(100, 80, 60, 60)), 60 * 60, "large_enough"),
        (_face(), 300 * 300, "prominent_enough"),
        (
            _face(
                landmarks=((130, 125), (210, 125), (230, 160), (145, 200), (195, 200))
            ),
            180 * 180,
            "pose_usable",
        ),
    ),
)
def test_blur_crop_size_group_prominence_and_pose_fall_into_other(
    face: FaceObservation, largest_area: int, failed_signal: str
) -> None:
    result = assess_face_quality(
        face, image_width=640, image_height=480, largest_face_area=largest_area
    )
    assert result.band == "other"
    assert getattr(result, failed_signal) is False


def test_quality_rejects_invalid_geometry_without_inferred_attributes() -> None:
    with pytest.raises(FacialQualityError, match="Dimensões"):
        assess_face_quality(_face(), image_width=0, image_height=480)
    with pytest.raises(FacialQualityError, match="proeminência"):
        assess_face_quality(
            _face(), image_width=640, image_height=480, largest_face_area=1
        )
    with pytest.raises(FacialQualityError, match="Métricas"):
        assess_face_quality(
            _face(blur=float("nan")), image_width=640, image_height=480
        )
    with pytest.raises(FacialQualityError, match="Métricas"):
        assess_face_quality(
            _face(
                landmarks=(
                    (float("nan"), 125),
                    (210, 125),
                    (170, 160),
                    (145, 200),
                    (195, 200),
                )
            ),
            image_width=640,
            image_height=480,
        )
    assert {
        "age",
        "gender",
        "emotion",
        "beauty",
        "identity",
        "skin_tone",
    }.isdisjoint(assess_face_quality.__annotations__)
