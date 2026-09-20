"""Benchmark offline do runtime real: detecção e recuperação têm denominadores separados.

Manifesto privado: {synthetic: bool, authorization: {origin, purpose, expires_at}, photos:
[{path, scenario, split: calibration|validation, faces: [{box: [x,y,w,h], subject: pseudonym}]}]}.
Caixas normalizadas na geometria orientada. Relatório somente agregado; vetores só em RAM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import numpy as np
from app.facial.detection import DetectionConfig, iou
from app.facial.model_assets import verify_models
from app.facial.provider import OpenCvSFaceProvider, analyze_query
from PIL import Image, ImageOps


def match_boxes(truth, predicted, threshold=0.5):
    """Matching bipartido máximo: uma detecção não conta como duas pessoas."""
    neighbors = {
        i: sorted(
            [j for j, box in enumerate(predicted) if iou(expected, box) >= threshold],
            key=lambda j: -iou(expected, predicted[j]),
        )
        for i, expected in enumerate(truth)
    }
    assigned = {}

    def visit(i, seen):
        for j in neighbors[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in assigned or visit(assigned[j], seen):
                assigned[j] = i
                return True
        return False

    for i in neighbors:
        visit(i, set())
    return {i: j for j, i in assigned.items()}


def retrieval_metrics(records):
    # Apenas rostos detectados e associados ao ground truth: recall do detector não entra neste denominador.
    if len(records) < 2:
        return {"status": "insufficient_detected_ground_truth"}
    vectors = np.asarray([row[2] for row in records], dtype=np.float32)
    positives, negatives, ranks = [], [], []
    for index, (photo, subject, _) in enumerate(records):
        similarities = vectors @ vectors[index]
        candidates = [i for i, row in enumerate(records) if row[0] != photo]
        order = sorted(candidates, key=lambda i: -float(similarities[i]))
        positive_ranks = [
            rank + 1 for rank, i in enumerate(order) if records[i][1] == subject
        ]
        if positive_ranks:
            ranks.append(min(positive_ranks))
        for other in candidates:
            if other <= index:
                continue
            scores = positives if subject == records[other][1] else negatives
            if len(scores) < 100_000:
                scores.append(float(similarities[other]))
    if not positives or not negatives:
        return {
            "status": "insufficient_positive_or_negative_pairs",
            "positive_pairs": len(positives),
            "negative_pairs": len(negatives),
        }
    thresholds = []
    for t in range(101):
        fp = sum(v >= t / 100 for v in negatives)
        fn = sum(v < t / 100 for v in positives)
        tp = len(positives) - fn
        thresholds.append(
            {
                "threshold": t / 100,
                "false_positives": fp,
                "false_negatives": fn,
                "precision": tp / (tp + fp) if tp + fp else None,
                "recall": tp / len(positives),
                "false_positive_rate": fp / len(negatives),
            }
        )
    return {
        "status": "measured",
        "positive_pairs": len(positives),
        "negative_pairs": len(negatives),
        "positive_quantiles": np.quantile(positives, [0.05, 0.5, 0.95]).tolist(),
        "negative_quantiles": np.quantile(negatives, [0.05, 0.5, 0.95]).tolist(),
        "top_k": {
            str(k): sum(rank <= k for rank in ranks) / len(ranks) if ranks else None
            for k in (1, 5, 10)
        },
        "eligible_top_k_queries": len(ranks),
        "pair_cap_per_class": 100_000,
        "thresholds": thresholds,
    }


def load_corpus(path):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("synthetic", False), bool):
        raise TypeError("synthetic deve ser booleano.")
    if not manifest.get("synthetic"):
        authorization = manifest.get("authorization", {})
        if not authorization.get("origin") or not authorization.get("purpose"):
            raise ValueError("Corpus real requer origem e finalidade autorizadas.")
        expiry = datetime.fromisoformat(authorization["expires_at"])
        if expiry.tzinfo is None or expiry <= datetime.now(UTC):
            raise ValueError("Autorização do corpus expirada.")
    root = path.parent.resolve()
    splits_by_content = {}
    for item in manifest["photos"]:
        candidate = (root / item["path"]).resolve()
        candidate.relative_to(root)
        if not candidate.is_file() or item.get("split") not in {
            "calibration",
            "validation",
        }:
            raise ValueError("Amostra ou split inválido.")
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        previous = splits_by_content.setdefault(digest, item["split"])
        if previous != item["split"]:
            raise ValueError(
                "A mesma imagem não pode aparecer em calibração e validação."
            )
        for face in item["faces"]:
            if not isinstance(face.get("subject"), str) or not face["subject"].strip():
                raise ValueError("Ground truth requer pseudônimo local.")
            x, y, w, h = face["box"]
            if not (
                0 <= x < 1
                and 0 <= y < 1
                and w > 0
                and h > 0
                and x + w <= 1
                and y + h <= 1
            ):
                raise ValueError("Ground truth inválido.")
    return manifest


def benchmark(
    manifest_path, model_root, *, threads=1, config=None, modes=("legacy", "highres")
):
    from threading import Event, Thread

    import cv2
    import psutil

    manifest = load_corpus(manifest_path)
    model_manifest = (
        Path(__file__).resolve().parents[1]
        / "backend/facial-assets/model-manifest.json"
    )
    models = verify_models(model_manifest, model_root)
    config = config or DetectionConfig()
    cv2.setNumThreads(threads)
    corpus_digest = hashlib.sha256(manifest_path.read_bytes())
    for item in manifest["photos"]:
        corpus_digest.update(
            hashlib.sha256((manifest_path.parent / item["path"]).read_bytes()).digest()
        )
    report = {
        "host": {
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count(),
            "opencv_threads": threads,
        },
        "synthetic": bool(manifest.get("synthetic")),
        "config": config.metadata(),
        "corpus_sha256": corpus_digest.hexdigest(),
        "timing_scope": "legacy: derived JPEG + detector + embeddings; highres: oriented source + detector + embeddings; excludes DB and presentation",
        "models_sha256": hashlib.sha256(model_manifest.read_bytes()).hexdigest(),
        "runs": {},
    }
    for mode in modes:
        provider = OpenCvSFaceProvider(models["yunet"], models["sface"])
        stats = defaultdict(
            lambda: {
                "ground_truth": 0,
                "detected_truth": 0,
                "false_detections": 0,
                "duplicates": 0,
                "photos": 0,
            }
        )
        records = defaultdict(list)
        latencies, photo_metrics = [], []
        peak = [psutil.Process().memory_info().rss]
        stop = Event()

        def sample(stop=stop, peak=peak):
            while not stop.wait(0.01):
                peak[0] = max(peak[0], psutil.Process().memory_info().rss)

        sampler = Thread(target=sample, daemon=True)
        sampler.start()
        start, cpu = time.perf_counter(), time.process_time()
        megapixels = 0
        try:
            for index, item in enumerate(manifest["photos"]):
                path = manifest_path.parent / item["path"]
                instant = time.perf_counter()
                if mode == "legacy":
                    # Reproduz admin_preview JPEG quality=85 e o provider de produção, não o provider do spike antigo.
                    with Image.open(path) as opened:
                        image = ImageOps.exif_transpose(opened).convert("RGB")
                        megapixels += image.width * image.height / 1e6
                        image.thumbnail((2000, 4000), Image.Resampling.LANCZOS)
                        buffer = BytesIO()
                        image.save(buffer, "JPEG", quality=85, optimize=True)
                    observations = provider.observe_bytes(buffer.getvalue())
                else:
                    observations = provider.observe_highres_path(path, config=config)
                    megapixels += provider.last_metrics["megapixels"]
                boxes = [
                    (
                        f.box[0] / f.image_width,
                        f.box[1] / f.image_height,
                        f.box[2] / f.image_width,
                        f.box[3] / f.image_height,
                    )
                    for f in observations
                ]
                truth = [f["box"] for f in item["faces"]]
                matched = match_boxes(truth, boxes)
                values = stats[f"{item['split']}:{item['scenario']}"]
                values["photos"] += 1
                values["ground_truth"] += len(truth)
                values["detected_truth"] += len(matched)
                values["false_detections"] += len(boxes) - len(matched)
                values["duplicates"] += sum(
                    j not in matched.values()
                    and any(iou(box, gt) >= 0.5 for gt in truth)
                    for j, box in enumerate(boxes)
                )
                for gt_index, pred_index in matched.items():
                    records[item["split"]].append(
                        (
                            index,
                            item["faces"][gt_index]["subject"],
                            observations[pred_index].embedding,
                        )
                    )
                elapsed = time.perf_counter() - instant
                latencies.append(elapsed)
                photo_metrics.append(
                    {
                        "sample": index,
                        "seconds": elapsed,
                        "gallery_as_query_diagnostic": analyze_query(
                            observations
                        ).status,
                        **(provider.last_metrics if mode == "highres" else {}),
                    }
                )
        finally:
            stop.set()
            sampler.join()
        elapsed = time.perf_counter() - start
        for values in stats.values():
            values["recall"] = (
                values["detected_truth"] / values["ground_truth"]
                if values["ground_truth"]
                else None
            )
        report["runs"][mode] = {
            "detection": dict(stats),
            "retrieval": {
                split: retrieval_metrics(rows) for split, rows in records.items()
            },
            "seconds": elapsed,
            "cpu_seconds": time.process_time() - cpu,
            "peak_rss_bytes": peak[0],
            "photos_per_minute": len(latencies) * 60 / elapsed,
            "megapixels_per_second": megapixels / elapsed,
            "latency_p50_p95": np.quantile(latencies, [0.5, 0.95]).tolist()
            if latencies
            else [],
            "photos": photo_metrics,
        }
    return report


def numpy_benchmark(regions=8000, repetitions=100):
    rng = np.random.default_rng(42)
    matrix = rng.normal(size=(regions, 128)).astype(np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    query = matrix[0]
    samples = []
    for _ in range(repetitions):
        start = time.perf_counter()
        _ = matrix @ query
        samples.append((time.perf_counter() - start) * 1000)
    return {
        "regions": regions,
        "dimension": 128,
        "matrix_bytes": matrix.nbytes,
        "p50_ms": float(np.median(samples)),
        "p95_ms": float(np.quantile(samples, 0.95)),
        "includes_database_decryption": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--model-root", type=Path)
    parser.add_argument("--threads", type=int, choices=(1, 2, 4), default=1)
    parser.add_argument(
        "--pipeline", choices=("legacy", "highres", "both"), default="both"
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = (
        benchmark(
            args.manifest,
            args.model_root,
            threads=args.threads,
            modes=("legacy", "highres")
            if args.pipeline == "both"
            else (args.pipeline,),
            config=DetectionConfig(**json.loads(args.config.read_text()))
            if args.config
            else None,
        )
        if args.manifest
        else {"numpy": numpy_benchmark()}
    )
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
