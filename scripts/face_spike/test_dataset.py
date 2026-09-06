import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from scripts.face_spike.dataset import (
    MARKER_NAME,
    build_dataset,
    clean_dataset,
    verify_dataset,
)


def _sheet(path: Path, *, angled: bool) -> None:
    canvas = Image.new("RGB", (800, 800), "gray")
    draw = ImageDraw.Draw(canvas)
    for index in range(16):
        column, row = index % 4, index // 4
        left, top = column * 200, row * 200
        shift = 10 if angled else 0
        draw.ellipse((left + 40 + shift, top + 25, left + 160 + shift, top + 175), fill=(80 + index * 5, 90, 110))
    canvas.save(path)


def test_build_verify_and_safe_cleanup(tmp_path: Path) -> None:
    front = tmp_path / "front.png"
    angle = tmp_path / "angle.png"
    output = tmp_path / "markina-face-spike-run"
    _sheet(front, angled=False)
    _sheet(angle, angled=True)

    summary = build_dataset(front, angle, output)

    assert summary == {
        "synthetic_only": True,
        "event_a_images": 504,
        "event_b_images": 4,
        "query_images": 32,
        "total_jpegs": 540,
        "identities": 16,
        "expected_event_a_faces": 544,
    }
    assert verify_dataset(output) == summary
    clean_dataset(output)
    assert not output.exists()


def test_cleanup_refuses_unmarked_directory(tmp_path: Path) -> None:
    output = tmp_path / "do-not-remove"
    output.mkdir()
    retained = output / "retained.txt"
    retained.write_text("preservar", encoding="utf-8")

    with pytest.raises(ValueError, match="Marcador"):
        clean_dataset(output)

    assert retained.read_text(encoding="utf-8") == "preservar"


def test_verify_rejects_tampered_file(tmp_path: Path) -> None:
    output = tmp_path / "markina-face-spike-tampered"
    output.mkdir()
    (output / MARKER_NAME).write_text(
        json.dumps(
            {
                "kind": "markina-face-spike",
                "schema_version": 1,
                "synthetic_only": True,
            }
        ),
        encoding="utf-8",
    )
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "synthetic_only": True,
                "events": {
                    "event-a": [
                        {
                            "path": "event-a/tampered.jpg",
                            "sha256": "0" * 64,
                            "expected_faces": 0,
                        }
                    ],
                    "event-b": [],
                },
                "queries": [],
                "identities": [],
            }
        ),
        encoding="utf-8",
    )
    image = output / "event-a" / "tampered.jpg"
    image.parent.mkdir()
    Image.new("RGB", (20, 20)).save(image)

    with pytest.raises(ValueError, match="Hash divergente"):
        verify_dataset(output)
