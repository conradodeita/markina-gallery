"""Provisiona e verifica os pesos locais fixados do EmbeddingGemma 2."""

from __future__ import annotations

import json
from pathlib import Path

from app.facial.gemma_provider import GEMMA_MODEL_REPO_ID, GEMMA_MODEL_REVISION

MARKER_NAME = ".markina-embeddinggemma.json"


class GemmaAssetError(RuntimeError):
    """Os pesos locais não correspondem ao modelo experimental fixado."""


def verify_gemma_model(model_path: Path) -> None:
    root = model_path.resolve()
    if root == Path(root.anchor) or not root.is_dir():
        raise GemmaAssetError("Diretório local do EmbeddingGemma indisponível.")
    try:
        marker = json.loads((root / MARKER_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GemmaAssetError("Marcador dos pesos EmbeddingGemma ausente ou inválido.") from exc
    if (
        not isinstance(marker, dict)
        or marker.get("model_id") != GEMMA_MODEL_REPO_ID
        or marker.get("revision") != GEMMA_MODEL_REVISION
        or not (root / "modules.json").is_file()
        or not (root / "chat_template.jinja").is_file()
        or not any(root.glob("*.safetensors"))
    ):
        raise GemmaAssetError("Pesos locais não correspondem à revisão fixada do EmbeddingGemma.")


def prepare_gemma_model(model_path: Path) -> None:
    root = model_path.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        try:
            verify_gemma_model(root)
            return
        except GemmaAssetError as exc:
            raise GemmaAssetError("Cache EmbeddingGemma existente não verificado.") from exc
    try:
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=GEMMA_MODEL_REPO_ID,
            revision=GEMMA_MODEL_REVISION,
            local_dir=str(root),
            allow_patterns=[
                "*.json",
                "*.jinja",
                "*.safetensors",
                "*.model",
                "*.txt",
                "*.py",
                "*.md",
            ],
        )
        (root / MARKER_NAME).write_text(
            json.dumps(
                {"model_id": GEMMA_MODEL_REPO_ID, "revision": GEMMA_MODEL_REVISION},
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        verify_gemma_model(root)
    except GemmaAssetError:
        raise
    except Exception as exc:
        raise GemmaAssetError("Não foi possível provisionar os pesos EmbeddingGemma fixados.") from exc
