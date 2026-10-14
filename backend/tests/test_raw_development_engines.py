from pathlib import Path

import pytest
from PIL import Image

from app.raw_development.engines import (
    LightCraftRawEngine,
    RawEngineError,
    RawTherapeeRawEngine,
    normalize_rendered_jpeg,
)


def _write_rendered_jpeg(path: Path):
    image = Image.new("RGB", (120, 80), (80, 120, 160))
    exif = Image.Exif()
    exif[271] = "SONY"
    exif[272] = "ILCE-7M4"
    exif[274] = 6  # rotate 90 degrees clockwise on display
    image.save(path, format="JPEG", exif=exif)


@pytest.mark.parametrize(
    ("engine_type", "engine_name"),
    [(RawTherapeeRawEngine, "rawtherapee"), (LightCraftRawEngine, "lightcraft")],
)
def test_file_engine_renders_auto_profile_and_normalizes_orientation(
    tmp_path, monkeypatch, engine_type, engine_name
):
    source = tmp_path / "camera-source.raw"
    source_bytes = b"opaque test input"
    source.write_bytes(source_bytes)
    engine_output = tmp_path / "engine-output.jpg"
    clean_output = tmp_path / "normalized.jpg"
    calls = []

    def mock_run(args, **kwargs):
        calls.append((args, kwargs))
        _write_rendered_jpeg(engine_output)

    monkeypatch.setattr("app.raw_development.engines.subprocess.run", mock_run)
    rendered = engine_type(binary="engine-cli", version="1.2.3")
    rendered.render(source, engine_output)
    metadata = normalize_rendered_jpeg(engine_output, clean_output)

    assert rendered.version == "1.2.3"
    assert metadata.camera_make == "SONY"
    assert metadata.camera_model == "ILCE-7M4"
    assert (metadata.width, metadata.height) == (80, 120)
    assert source.read_bytes() == source_bytes
    assert clean_output.is_file()
    with Image.open(clean_output) as image:
        assert image.size == (80, 120)
        assert not image.getexif()
        pixel = image.getpixel((image.width // 2, image.height // 2))
        assert all(abs(channel - expected) <= 4 for channel, expected in zip(pixel, (80, 120, 160)))
    args, kwargs = calls[0]
    assert kwargs["check"] is True
    assert "shell" not in kwargs
    if engine_name == "lightcraft":
        assert args[1:5] == ["run", "--import", str(source), "develop.auto"]
        assert kwargs["env"]["RAYON_NUM_THREADS"] == "1"
        assert not Path(kwargs["env"]["HOME"]).exists()
    else:
        assert args[0] == "engine-cli"
        assert "-a" in args
        assert kwargs["env"]["RT_SETTINGS"] == str(tmp_path / ".camera-source.rawtherapee-settings")
        assert not Path(kwargs["env"]["RT_SETTINGS"]).exists()


def test_engine_failure_is_sanitized(monkeypatch, tmp_path):
    source = tmp_path / "source.arw"
    output = tmp_path / "output.jpg"
    source.touch()

    def failed(*_args, **_kwargs):
        raise FileNotFoundError("private executable path")

    monkeypatch.setattr("app.raw_development.engines.subprocess.run", failed)
    with pytest.raises(RawEngineError, match="não conseguiu desenvolver") as error:
        LightCraftRawEngine(binary="missing-lightcraft").render(source, output)
    assert "private executable path" not in str(error.value)


def test_non_jpeg_engine_output_is_rejected(tmp_path):
    rendered = tmp_path / "rendered.png"
    output = tmp_path / "clean.jpg"
    Image.new("RGB", (80, 40)).save(rendered)
    with pytest.raises(RawEngineError, match="JPEG válido"):
        normalize_rendered_jpeg(rendered, output)
