"""Verify that the isolated OpenCV provider runs in an ARM64 environment."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

from scripts.face_spike.harness import OpenCvSFaceProvider


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--query", type=Path, required=True)
    args = parser.parse_args()
    provider = OpenCvSFaceProvider(
        args.model_root / "face_detection_yunet_2023mar.onnx",
        args.model_root / "face_recognition_sface_2021dec.onnx",
    )
    faces = provider.observe(args.query)
    print(
        json.dumps(
            {
                "machine": platform.machine(),
                "provider": provider.model_id,
                "detected_faces": len(faces),
                "embedding_dimensions": int(faces[0].embedding.shape[0]) if faces else 0,
                "model_disk_bytes": provider.model_disk_bytes,
                "contains_embedding": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
