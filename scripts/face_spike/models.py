"""Download, verify and safely remove model files for the isolated facial spike."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import urllib.request
from pathlib import Path
from typing import Any

MARKER_NAME = ".markina-face-spike-models.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_root(path: Path) -> Path:
    root = path.resolve()
    if root == Path(root.anchor) or root == Path.home().resolve():
        raise ValueError("O cache de modelos não pode ser a raiz nem o diretório pessoal.")
    return root


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not manifest.get("models"):
        raise ValueError("Manifesto de modelos inválido.")
    return manifest


def prepare_models(manifest_path: Path, model_root: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    root = _safe_root(model_root)
    root.mkdir(parents=True, exist_ok=True)
    marker_path = root / MARKER_NAME
    if marker_path.exists():
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if marker.get("kind") != "markina-face-spike-models":
            raise ValueError("Marcador do cache de modelos inválido.")
    elif any(root.iterdir()):
        raise FileExistsError("O cache deve estar vazio antes da primeira preparação.")
    marker_path.write_text(
        json.dumps({"kind": "markina-face-spike-models", "schema_version": 1}, indent=2),
        encoding="utf-8",
    )

    verified: dict[str, Any] = {}
    for model_id, expected in manifest["models"].items():
        target = root / expected["filename"]
        if not target.exists():
            partial = target.with_suffix(target.suffix + ".part")
            try:
                with (
                    urllib.request.urlopen(expected["url"], timeout=120) as response,
                    partial.open("wb") as handle,
                ):
                    shutil.copyfileobj(response, handle)
                os.replace(partial, target)
            finally:
                partial.unlink(missing_ok=True)
        actual_size = target.stat().st_size
        actual_hash = _sha256(target)
        if actual_size != expected["bytes"] or actual_hash != expected["sha256"]:
            target.unlink(missing_ok=True)
            raise ValueError(f"Integridade inválida para o modelo {model_id}.")
        verified[model_id] = {
            "path": str(target),
            "bytes": actual_size,
            "sha256": actual_hash,
            "license": expected["license"],
        }
    return verified


def verify_models(manifest_path: Path, model_root: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    root = _safe_root(model_root)
    marker_path = root / MARKER_NAME
    if not marker_path.is_file():
        raise ValueError("Marcador do cache de modelos ausente.")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker != {"kind": "markina-face-spike-models", "schema_version": 1}:
        raise ValueError("Marcador do cache de modelos inválido.")
    result: dict[str, Any] = {}
    for model_id, expected in manifest["models"].items():
        target = root / expected["filename"]
        if not target.is_file():
            raise ValueError(f"Modelo ausente: {model_id}.")
        actual_hash = _sha256(target)
        if target.stat().st_size != expected["bytes"] or actual_hash != expected["sha256"]:
            raise ValueError(f"Integridade inválida para o modelo {model_id}.")
        result[model_id] = {
            "path": str(target),
            "bytes": target.stat().st_size,
            "sha256": actual_hash,
            "license": expected["license"],
        }
    return result


def clean_models(model_root: Path) -> None:
    root = _safe_root(model_root)
    marker_path = root / MARKER_NAME
    if not marker_path.is_file():
        raise ValueError("Marcador do cache de modelos ausente.")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker != {"kind": "markina-face-spike-models", "schema_version": 1}:
        raise ValueError("Marcador do cache de modelos inválido.")
    shutil.rmtree(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify", "clean"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare_models(args.manifest, args.model_root)
    elif args.command == "verify":
        result = verify_models(args.manifest, args.model_root)
    else:
        clean_models(args.model_root)
        result = {"removed": str(args.model_root.resolve())}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
