"""File-to-file RAW adapters. They run only inside the isolated development worker."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import ExifTags, Image, ImageOps

from app.raw_development.state import RAW_MAX_OUTPUT_PIXELS, RAW_PROCESS_TIMEOUT_SECONDS

PROFILE_VERSION = "auto-v1"
_RAWTHERAPEE_PROFILE = Path(__file__).resolve().parents[1] / "preview_adjustment" / "natural.pp3"
_EXIF_IDS = {name: identifier for identifier, name in ExifTags.TAGS.items()}


class RawEngineError(RuntimeError):
    """Sanitized engine failure; details from executables are never returned to users."""


@dataclass(frozen=True)
class RenderedRaw:
    width: int
    height: int
    camera_make: str | None
    camera_model: str | None
    profile_version: str = PROFILE_VERSION


class RawEngine:
    name: str
    version: str

    def render(self, source: Path, output: Path, *, timeout: int = RAW_PROCESS_TIMEOUT_SECONDS) -> None:
        raise NotImplementedError


class RawTherapeeRawEngine(RawEngine):
    name = "rawtherapee"

    def __init__(self, binary: str | None = None, version: str | None = None):
        self.binary = binary or os.getenv("RAWTHERAPEE_CLI", "rawtherapee-cli")
        self.version = version or os.getenv("RAW_DEVELOPMENT_RAWTHERAPEE_VERSION", "unknown")

    def render(self, source: Path, output: Path, *, timeout: int = RAW_PROCESS_TIMEOUT_SECONDS) -> None:
        settings_dir = source.parent / f".{source.stem}.rawtherapee-settings"
        settings_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._run(
                [
                    self.binary,
                    "-o", str(output),
                    "-p", str(_RAWTHERAPEE_PROFILE),
                    "-b8", "-n", "-a", "-c", str(source),
                ],
                timeout,
                settings_dir=settings_dir,
            )
        finally:
            shutil.rmtree(settings_dir, ignore_errors=True)

    @staticmethod
    def _run(args: list[str], timeout: int, *, settings_dir: Path) -> None:
        try:
            subprocess.run(
                args,
                check=True,
                timeout=timeout,
                env={**os.environ, "OMP_NUM_THREADS": "1", "RT_SETTINGS": str(settings_dir)},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RawEngineError("O motor RawTherapee não conseguiu desenvolver este arquivo.") from exc


class LightCraftRawEngine(RawEngine):
    name = "lightcraft"

    def __init__(self, binary: str | None = None, version: str | None = None):
        self.binary = binary or os.getenv("LIGHTCRAFT_CLI", "lightcraft-cli")
        self.version = version or os.getenv("RAW_DEVELOPMENT_LIGHTCRAFT_VERSION", "unknown")

    def render(self, source: Path, output: Path, *, timeout: int = RAW_PROCESS_TIMEOUT_SECONDS) -> None:
        home = source.parent / f".{source.stem}.lightcraft-home"
        home.mkdir(parents=True, exist_ok=True)
        try:
            self._run(
                [
                    self.binary,
                    "run", "--import", str(source),
                    "develop.auto",
                    "app.export", f"path={output}",
                ],
                timeout,
                home=home,
            )
        finally:
            shutil.rmtree(home, ignore_errors=True)

    @staticmethod
    def _run(args: list[str], timeout: int, *, home: Path) -> None:
        try:
            subprocess.run(
                args,
                check=True,
                timeout=timeout,
                env={
                    **os.environ,
                    "RAYON_NUM_THREADS": "1",
                    "OMP_NUM_THREADS": "1",
                    "HOME": str(home),
                    "XDG_CONFIG_HOME": str(home / "config"),
                    "XDG_CACHE_HOME": str(home / "cache"),
                    "XDG_DATA_HOME": str(home / "data"),
                },
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RawEngineError("O motor LightCraft não conseguiu desenvolver este arquivo.") from exc


def normalize_rendered_jpeg(rendered: Path, output: Path) -> RenderedRaw:
    """Validate dimensions/orientation and create an EXIF-free working JPEG atomically."""
    try:
        with Image.open(rendered) as image:
            if image.format != "JPEG":
                raise RawEngineError("O motor não produziu um JPEG válido.")
            if image.width <= 0 or image.height <= 0 or image.width * image.height > RAW_MAX_OUTPUT_PIXELS:
                raise RawEngineError("A resolução desenvolvida excede o limite permitido.")
            exif = image.getexif()
            camera_make = str(exif.get(_EXIF_IDS.get("Make", -1), "")).strip()[:64] or None
            camera_model = str(exif.get(_EXIF_IDS.get("Model", -1), "")).strip()[:96] or None
            visual = ImageOps.exif_transpose(image)
            visual.load()
            width, height = visual.size
            if width <= 0 or height <= 0 or width * height > RAW_MAX_OUTPUT_PIXELS:
                raise RawEngineError("A resolução desenvolvida excede o limite permitido.")
            clean = visual.convert("RGB")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".part")
        if os.name != "nt":
            os.chmod(output.parent, 0o700)
        clean.save(temporary, format="JPEG", quality=95, optimize=True)
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        temporary.replace(output)
        return RenderedRaw(width, height, camera_make, camera_model)
    except RawEngineError:
        raise
    except (OSError, ValueError) as exc:
        raise RawEngineError("O motor não produziu um JPEG utilizável.") from exc


def engine_for(name: str, *, version: str | None = None) -> RawEngine:
    if name == "lightcraft":
        return LightCraftRawEngine(version=version)
    if name == "rawtherapee":
        return RawTherapeeRawEngine(version=version)
    raise RawEngineError("Motor RAW indisponível.")
