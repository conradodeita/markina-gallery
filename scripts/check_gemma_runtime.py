"""Valida runtime Gemma offline com pixels sintéticos; não lê fotografias."""

import json
import math
import platform
import resource
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import cv2
import numpy as np
from app.facial.gemma_assets import verify_gemma_model
from app.facial.gemma_provider import GemmaFaceEmbeddingProvider


def main():
    root = Path("/opt/markina-embeddinggemma-2")
    verify_gemma_model(root)
    provider = GemmaFaceEmbeddingProvider(SimpleNamespace(_cv2=cv2), model_path=root)
    image = np.zeros((112, 112, 3), dtype=np.uint8)
    started = perf_counter()
    first = provider.embed_aligned(image)
    cold = perf_counter() - started
    started = perf_counter()
    second = provider.embed_aligned(image)
    warm = perf_counter() - started
    assert len(first) == 768 and all(math.isfinite(x) for x in first)
    assert abs(sum(x * x for x in first) - 1) < 1e-5
    assert np.allclose(first, second, atol=1e-5)
    print(json.dumps({
        "architecture": platform.machine(), "dimension": len(first),
        "norm": round(sum(x * x for x in first), 6),
        "cold_seconds": round(cold, 3), "warm_seconds": round(warm, 3),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "synthetic": True,
    }))


if __name__ == "__main__":
    main()
