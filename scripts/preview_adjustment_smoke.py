"""Smoke sintético do motor real. Rodar no worker, com diretório /out temporário."""

import hashlib
import json
import subprocess
from pathlib import Path
from time import monotonic

from app.preview_adjustment.engine import RawTherapeeEngine
from PIL import Image, ImageChops, ImageDraw

output = Path("/out")
output.mkdir(exist_ok=True)
version = subprocess.run(
    ["rawtherapee-cli", "-v"],
    text=True,
    capture_output=True,
    check=False,
).stdout.splitlines()
report = {"engine": version[0] if version else "versão indisponível", "samples": []}
sheet = Image.new("RGB", (1280, 3 * 460), "white")
draw = ImageDraw.Draw(sheet)
for index, (name, low, high) in enumerate(
    [
        ("subexposta", 10, 100),
        ("equilibrada", 15, 230),
        ("baixo-contraste", 90, 155),
    ]
):
    image = Image.new("RGB", (640, 420))
    for x in range(image.width):
        level = round(low + (high - low) * x / (image.width - 1))
        ImageDraw.Draw(image).line((x, 0, x, image.height), fill=(level, level, level))
    painter = ImageDraw.Draw(image)
    for position, color in enumerate([(90, 35, 25), (35, 95, 40), (30, 40, 120), (145, 100, 70)]):
        painter.rectangle((40 + 145 * position, 140, 150 + 145 * position, 300), fill=color)
    before_hash = hashlib.sha256(image.tobytes()).hexdigest()
    started = monotonic()
    result = RawTherapeeEngine().render(image, 50)
    duration = round(monotonic() - started, 3)
    assert result.size == image.size and result.mode == "RGB"
    assert hashlib.sha256(image.tobytes()).hexdigest() == before_hash
    changed = ImageChops.difference(image, result).getbbox() is not None
    assert changed, "O perfil automático não produziu alteração observável."
    sheet.paste(image, (0, index * 460 + 30))
    sheet.paste(result, (640, index * 460 + 30))
    draw.text((10, index * 460 + 8), f"{name} - antes", fill="black")
    draw.text((650, index * 460 + 8), f"depois - {duration}s", fill="black")
    report["samples"].append({"name": name, "elapsed_seconds": duration, "changed": changed})
sheet.save(output / "comparison.jpg")
print(json.dumps(report, ensure_ascii=False))
