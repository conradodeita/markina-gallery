"""Motor fotográfico externo opcional; sem shell, rede ou escrita na entrada."""

import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from PIL import Image

ENGINE_VERSION = "rawtherapee-natural-v1"
TIMEOUT_SECONDS = 90


class AdjustmentEngine(Protocol):
    def render(self, image: Image.Image, strength: int) -> Image.Image: ...


class RawTherapeeEngine:
    def render(self, image: Image.Image, strength: int) -> Image.Image:
        with TemporaryDirectory(prefix="markina-preview-adjustment-") as directory:
            root = Path(directory)
            source, output = root / "input.png", root / "output.png"
            image.save(source, format="PNG")
            env = {**os.environ, "OMP_NUM_THREADS": "1", "RT_SETTINGS": str(root / "settings")}
            subprocess.run(
                [
                    "rawtherapee-cli",
                    "-o",
                    str(output),
                    "-p",
                    str(Path(__file__).with_name("natural.pp3")),
                    "-b8",
                    "-n",
                    "-a",
                    "-c",
                    str(source),
                ],
                check=True,
                timeout=TIMEOUT_SECONDS,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            with Image.open(output) as opened:
                if opened.size != image.size:
                    raise ValueError("O motor alterou as dimensões da prévia.")
                corrected = opened.convert("RGB")
            return Image.blend(image.convert("RGB"), corrected, strength / 100)
