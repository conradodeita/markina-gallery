"""Prepara e verifica os modelos faciais fixados pelo manifesto do runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO

MANIFEST_SCHEMA_VERSION = 1
MARKER_NAME = ".markina-face-models.json"
EXPECTED_MODEL_IDS = frozenset({"yunet", "sface"})
ALLOWED_LICENSES = frozenset({"MIT", "Apache-2.0"})
SUPPORTED_ARCHITECTURES = frozenset({"amd64", "arm64"})
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PINNED_OPENCV_URL = re.compile(
    r"^https://(?:raw\.githubusercontent\.com/opencv/opencv_zoo|"
    r"media\.githubusercontent\.com/media/opencv/opencv_zoo)/"
    r"[0-9a-f]{40}/models/[^?#]+\.onnx$"
)


class FacialModelConfigurationError(RuntimeError):
    """Configuração do modelo não pode ser aceita com segurança."""


class FacialModelIntegrityError(RuntimeError):
    """Bytes do modelo divergem do manifesto fixado."""


def normalize_architecture(value: str | None = None) -> str:
    raw = (value or platform.machine()).strip().lower()
    aliases = {
        "x86_64": "amd64",
        "x64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    normalized = aliases.get(raw)
    if not normalized:
        raise FacialModelConfigurationError("Arquitetura facial não suportada.")
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_digest(path: Path) -> str:
    return sha256_file(path)


def _safe_root(path: Path) -> Path:
    root = path.resolve()
    if root == Path(root.anchor) or root == Path.home().resolve():
        raise FacialModelConfigurationError("Diretório de modelos facial inseguro.")
    return root


def load_manifest(path: Path, *, architecture: str | None = None) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FacialModelConfigurationError("Manifesto facial ilegível.") from exc
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise FacialModelConfigurationError("Schema do manifesto facial divergente.")
    if not isinstance(manifest.get("model_version"), str) or not manifest["model_version"]:
        raise FacialModelConfigurationError("Versão facial ausente.")
    supported = set(manifest.get("architectures") or [])
    if supported != SUPPORTED_ARCHITECTURES:
        raise FacialModelConfigurationError("Arquiteturas do manifesto facial divergentes.")
    if normalize_architecture(architecture) not in supported:
        raise FacialModelConfigurationError("Arquitetura não autorizada pelo manifesto facial.")
    models = manifest.get("models")
    if not isinstance(models, dict) or set(models) != EXPECTED_MODEL_IDS:
        raise FacialModelConfigurationError("Conjunto de modelos facial divergente.")
    for model_id, expected in models.items():
        filename = expected.get("filename")
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise FacialModelConfigurationError(f"Nome de arquivo inválido para {model_id}.")
        if not PINNED_OPENCV_URL.fullmatch(str(expected.get("url", ""))):
            raise FacialModelConfigurationError(f"Origem não fixada para {model_id}.")
        if expected.get("license") not in ALLOWED_LICENSES:
            raise FacialModelConfigurationError(f"Licença não permitida para {model_id}.")
        if not isinstance(expected.get("bytes"), int) or expected["bytes"] <= 0:
            raise FacialModelConfigurationError(f"Tamanho inválido para {model_id}.")
        if not SHA256_PATTERN.fullmatch(str(expected.get("sha256", ""))):
            raise FacialModelConfigurationError(f"SHA-256 inválido para {model_id}.")
    return manifest


def _read_marker(root: Path) -> dict[str, Any]:
    marker_path = root / MARKER_NAME
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FacialModelConfigurationError("Marcador do cache facial ausente ou inválido.") from exc
    if marker.get("kind") != "markina-face-models":
        raise FacialModelConfigurationError("Marcador do cache facial divergente.")
    return marker


def _verify_file(target: Path, expected: dict[str, Any], model_id: str) -> None:
    if not target.is_file():
        raise FacialModelIntegrityError(f"Modelo facial ausente: {model_id}.")
    if target.stat().st_size != expected["bytes"]:
        raise FacialModelIntegrityError(f"Tamanho facial divergente: {model_id}.")
    if sha256_file(target) != expected["sha256"]:
        raise FacialModelIntegrityError(f"Integridade facial divergente: {model_id}.")


def verify_models(
    manifest_path: Path,
    model_root: Path,
    *,
    architecture: str | None = None,
) -> dict[str, Path]:
    manifest = load_manifest(manifest_path, architecture=architecture)
    root = _safe_root(model_root)
    marker = _read_marker(root)
    if marker.get("manifest_sha256") != _manifest_digest(manifest_path):
        raise FacialModelConfigurationError("Cache facial pertence a outro manifesto.")
    if marker.get("model_version") != manifest["model_version"]:
        raise FacialModelConfigurationError("Versão do cache facial divergente.")
    verified: dict[str, Path] = {}
    for model_id, expected in manifest["models"].items():
        target = root / expected["filename"]
        _verify_file(target, expected, model_id)
        verified[model_id] = target
    return verified


def prepare_models(
    manifest_path: Path,
    model_root: Path,
    *,
    architecture: str | None = None,
    opener: Callable[..., BinaryIO] = urllib.request.urlopen,
) -> dict[str, Path]:
    manifest = load_manifest(manifest_path, architecture=architecture)
    root = _safe_root(model_root)
    root.mkdir(parents=True, exist_ok=True)
    marker_path = root / MARKER_NAME
    if marker_path.exists():
        _read_marker(root)
    elif any(root.iterdir()):
        raise FacialModelConfigurationError("Cache facial não marcado deve estar vazio.")

    for model_id, expected in manifest["models"].items():
        target = root / expected["filename"]
        if target.exists():
            _verify_file(target, expected, model_id)
            continue
        partial = target.with_suffix(target.suffix + ".part")
        try:
            with opener(expected["url"], timeout=120) as response, partial.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            _verify_file(partial, expected, model_id)
            os.replace(partial, target)
        finally:
            partial.unlink(missing_ok=True)

    marker_path.write_text(
        json.dumps(
            {
                "kind": "markina-face-models",
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "manifest_sha256": _manifest_digest(manifest_path),
                "model_version": manifest["model_version"],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return verify_models(manifest_path, root, architecture=architecture)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--architecture")
    args = parser.parse_args()
    operation = prepare_models if args.command == "prepare" else verify_models
    result = operation(
        args.manifest,
        args.model_root,
        architecture=args.architecture,
    )
    print(json.dumps({key: str(value) for key, value in result.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
