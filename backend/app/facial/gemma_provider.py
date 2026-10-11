"""Provider local EmbeddingGemma 2 para índice e consultas no namespace experimental."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from app.facial.provider import (
    FaceObservation,
    FacialProviderError,
    OpenCvSFaceProvider,
    normalize_embedding,
)

GEMMA_MODEL_ID = "google-embeddinggemma-2"
GEMMA_MODEL_REPO_ID = "google/embeddinggemma-2"
GEMMA_MODEL_REVISION = "914f7f89142e33e77833254d9c9b90c3cef7303b"
GEMMA_MODEL_VERSION = f"embeddinggemma-2-{GEMMA_MODEL_REVISION[:12]}-face-crop-768"
GEMMA_EMBEDDING_DIMENSION = 768


class GemmaFaceEmbeddingProvider:
    """Usa YuNet/SFace somente para detecção/alinhamento e Gemma para o vetor de imagem."""

    model_id = GEMMA_MODEL_ID
    model_version = GEMMA_MODEL_VERSION
    embedding_dimension = GEMMA_EMBEDDING_DIMENSION

    def __init__(
        self,
        detector: OpenCvSFaceProvider,
        *,
        model_path: Path,
        model: Any | None = None,
    ) -> None:
        self._detector = detector
        self._model_path = model_path
        self._model = model
        self.last_metrics: dict[str, Any] = {}

    def embed_aligned(self, image: Any) -> tuple[float, ...]:
        if self._model is None:
            self._model = self._load_model()
        try:
            from PIL import Image

            rgb = self._detector._cv2.cvtColor(image, self._detector._cv2.COLOR_BGR2RGB)
            encoded = self._model.encode(
                {"image": Image.fromarray(rgb)},
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return normalize_embedding(encoded, self.embedding_dimension)
        except FacialProviderError:
            raise
        except Exception as exc:
            raise FacialProviderError("EmbeddingGemma não processou o recorte facial.") from exc

    def observe_path(self, image_path: Path) -> list[FaceObservation]:
        return self._embed_observations(
            self._detector.observe_path(image_path, include_embedding=False)
        )

    def observe_bytes(self, payload: bytes) -> list[FaceObservation]:
        if not payload:
            raise FacialProviderError("Imagem facial não pôde ser lida.")
        try:
            import numpy as np

            image = self._detector._cv2.imdecode(
                np.frombuffer(payload, dtype=np.uint8), self._detector._cv2.IMREAD_COLOR
            )
        except Exception as exc:
            raise FacialProviderError("Imagem facial não pôde ser lida.") from exc
        return self._embed_observations(
            self._detector.observe_image(image, include_embedding=False)
        )

    def observe_highres_path(self, image_path: Path, *, config=None) -> list[FaceObservation]:
        return self._embed_observations(
            self._detector.observe_highres_path(
                image_path, config=config, include_embedding=False
            )
        )

    def _embed_observations(
        self, observations: list[FaceObservation]
    ) -> list[FaceObservation]:
        started = perf_counter()
        embedded: list[FaceObservation] = []
        for observation in observations:
            if observation.aligned_image is None:
                raise FacialProviderError("Recorte facial alinhado indisponível para Gemma.")
            embedded.append(
                FaceObservation(
                    embedding=self.embed_aligned(observation.aligned_image),
                    detection_confidence=observation.detection_confidence,
                    box=observation.box,
                    landmarks=observation.landmarks,
                    blur_variance=observation.blur_variance,
                    detection_pass=observation.detection_pass,
                    image_width=observation.image_width,
                    image_height=observation.image_height,
                )
            )
        self.last_metrics = dict(getattr(self._detector, "last_metrics", {}))
        self.last_metrics.update(
            embedding_engine=self.model_id,
            embedding_faces=len(embedded),
            embedding_elapsed_ms=round((perf_counter() - started) * 1000),
        )
        return embedded

    def _load_model(self):
        if not self._model_path.is_dir() or not any(self._model_path.iterdir()):
            raise FacialProviderError("Pesos Gemma locais não estão provisionados.")
        try:
            import torch
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer(
                str(self._model_path),
                device="cpu",
                local_files_only=True,
                model_kwargs={"torch_dtype": torch.float32},
            )
        except Exception as exc:
            raise FacialProviderError("Runtime local EmbeddingGemma indisponível.") from exc
