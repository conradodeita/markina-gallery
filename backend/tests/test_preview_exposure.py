import pytest
from PIL import Image

from app.preview_adjustment.engine import compensate_exposure


def test_exposure_zero_signs_limits_and_input_preserved():
    image = Image.new("RGB", (10, 10), (80, 120, 160))
    original = image.tobytes()
    assert compensate_exposure(image, 0).tobytes() == original
    brighter = compensate_exposure(image, 10).getpixel((0, 0))
    darker = compensate_exposure(image, -10).getpixel((0, 0))
    assert all(d < o < b for d, o, b in zip(darker, (80, 120, 160), brighter))
    assert compensate_exposure(Image.new("RGB", (1, 1), "white"), 20).getpixel((0, 0)) == (
        255,
        255,
        255,
    )
    assert image.tobytes() == original
    with pytest.raises(ValueError):
        compensate_exposure(image, 21)


def test_exposure_in_linear_light():
    # 128 sRGB é ~0.216 em luz linear: +1 EV resulta em ~175, não 256.
    image = Image.new("RGB", (1, 1), (128, 128, 128))
    assert compensate_exposure(image, 10).getpixel((0, 0)) == (176, 176, 176)
