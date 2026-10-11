"""Comparação offline SFace/Gemma. Nenhum banco, API, fila ou índice do produto.

Manifesto privado: synthetic, authorization e photos [{path, split:
gallery|validation|test, faces: [{subject: pseudônimo, box: [x,y,w,h]}]}].
Somente agregados saem do processo. Imagens e vetores permanecem em memória.
Execução real requer referência humana por execução e workspace cifrado atestado.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, process_time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from face_benchmark import match_boxes

DIMENSIONS = (768, 512, 256, 128)
STRATEGIES = ("aligned", "context", "whole_image")


def comparison_load(gallery, queries, *, concurrency: int) -> dict:
    """Carga só da comparação vetorial; não simula sessões nem fairness do produto."""
    if concurrency not in (1, 2, 4, 8):
        raise ValueError("Concorrência deve ser 1, 2, 4 ou 8.")
    if not gallery or not queries:
        return {"status": "insufficient_samples"}
    matrix = np.asarray([row[1] for row in gallery], dtype=np.float32)
    selected = queries[:2048]
    before = perf_counter()
    def compare(item):
        queued_at, vector = item
        started = perf_counter()
        _ = matrix @ np.asarray(vector, dtype=np.float32)
        finished = perf_counter()
        return (finished - started) * 1000, (finished - queued_at) * 1000
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        timings = list(pool.map(compare, [(perf_counter(), row[1]) for row in selected]))
    elapsed = perf_counter() - before
    return {
        "scope": "in_memory_vector_comparison; excludes embedding, auth, DB, tenant quotas",
        "concurrency": concurrency, "queries": len(selected), "seconds": elapsed,
        "queries_per_second": len(selected) / elapsed,
        "comparison_ms": {label: float(np.quantile([t[0] for t in timings], quantile))
                          for label, quantile in (("p50", .5), ("p95", .95), ("p99", .99))},
        "including_queue_ms": {label: float(np.quantile([t[1] for t in timings], quantile))
                               for label, quantile in (("p50", .5), ("p95", .95), ("p99", .99))},
    }


def load_manifest(path: Path, authorization_reference: str | None = None) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if type(manifest.get("synthetic")) is not bool:
        raise ValueError("Informe synthetic explicitamente.")
    if not manifest["synthetic"]:
        auth = manifest.get("authorization", {})
        if not all(auth.get(key) for key in (
            "origin", "purpose", "reference", "expires_at", "deletion_plan",
        )) or auth.get("encrypted_workspace") is not True:
            raise ValueError("Corpus real requer autorização, origem, finalidade, cifra e exclusão.")
        if not authorization_reference or authorization_reference != auth["reference"]:
            raise ValueError("A execução requer referência de autorização humana correspondente.")
        expiry = datetime.fromisoformat(auth["expires_at"])
        if expiry.tzinfo is None or expiry <= datetime.now(UTC):
            raise ValueError("Autorização expirada.")
    photos = manifest.get("photos")
    if not isinstance(photos, list) or not 1 <= len(photos) <= 10000:
        raise ValueError("Lote deve conter de 1 a 10000 fotos explícitas.")
    root, splits = path.parent.resolve(), {}
    for item in photos:
        candidate = (root / item["path"]).resolve()
        candidate.relative_to(root)
        if not candidate.is_file() or item.get("split") not in {"gallery", "validation", "test"}:
            raise ValueError("Amostra ou partição inválida.")
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if splits.setdefault(digest, item["split"]) != item["split"]:
            raise ValueError("A mesma imagem não pode atravessar partições.")
        for face in item["faces"]:
            x, y, w, h = face["box"]
            if not isinstance(face.get("subject"), str) or not face["subject"].strip():
                raise ValueError("Ground truth requer pseudônimo local.")
            if not all(np.isfinite(v) for v in (x, y, w, h)) or not (
                0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0 and x + w <= 1 and y + h <= 1
            ):
                raise ValueError("Caixa de ground truth inválida.")
    if {item["split"] for item in photos} != {"gallery", "validation", "test"}:
        raise ValueError("Separe acervo, validação e teste final.")
    return manifest


def normalized_matrix(vectors, dimension: int) -> np.ndarray:
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] < dimension or not np.isfinite(matrix).all():
        raise ValueError("Vetores incompatíveis.")
    matrix = matrix[:, :dimension].copy()
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if (norms <= 0).any():
        raise ValueError("Vetor nulo após truncamento.")
    return matrix / norms


def identification_metrics(gallery, queries, *, threshold: float, margin: float = 0.0) -> dict:
    """Identificação aberta; FAR usa consultas desconhecidas, FRR usa conhecidas."""
    if not gallery or not queries:
        return {"status": "insufficient_samples"}
    matrix = np.asarray([row[1] for row in gallery], dtype=np.float32)
    identities = list(dict.fromkeys(row[0] for row in gallery))
    positions = [[i for i, row in enumerate(gallery) if row[0] == identity] for identity in identities]
    known = unknown = correct = false_accept = false_reject = wrong = top1 = top5 = 0
    for subject, query in queries:
        similarities = matrix @ np.asarray(query, dtype=np.float32)
        scores = [float(similarities[indices].max()) for indices in positions]
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        gap = scores[order[0]] - scores[order[1]] if len(order) > 1 else 2.0
        accepted = scores[order[0]] >= threshold and gap >= margin
        if subject in identities:
            known += 1
            top1 += identities[order[0]] == subject
            top5 += subject in [identities[i] for i in order[:5]]
            if not accepted:
                false_reject += 1
            elif identities[order[0]] == subject:
                correct += 1
            else:
                wrong += 1
        else:
            unknown += 1
            false_accept += accepted
    accepted_total = correct + wrong + false_accept
    return {
        "status": "measured", "known_queries": known, "unknown_queries": unknown,
        "correct_identifications": correct, "wrong_identifications": wrong,
        "false_acceptances": false_accept, "false_rejections": false_reject,
        "correct_unknown_rejections": unknown - false_accept,
        "precision": correct / accepted_total if accepted_total else None,
        "recall": correct / known if known else None,
        "far": false_accept / unknown if unknown else None,
        "frr": false_reject / known if known else None,
        "top1": top1 / known if known else None, "top5": top5 / known if known else None,
    }


def calibrated_comparison(gallery, validation, test) -> dict:
    """Escolhe somente em validação; teste final nunca define limiar/margem."""
    if not gallery or not validation or not test:
        return {"status": "insufficient_partitions"}
    curve = []
    for threshold in np.linspace(-1, 1, 101):
        for margin in (0.0, 0.05, 0.1):
            metrics = identification_metrics(gallery, validation, threshold=float(threshold), margin=margin)
            curve.append({"threshold": float(threshold), "margin": margin, **metrics})
    if not curve[0]["known_queries"] or not curve[0]["unknown_queries"]:
        return {"status": "insufficient_known_or_unknown_validation"}
    selected = min(curve, key=lambda row: (
        row["false_acceptances"] + row["wrong_identifications"],
        -row["correct_identifications"], -row["threshold"], -row["margin"],
    ))
    return {
        "status": "measured", "calibration_partition": "validation",
        "threshold": selected["threshold"], "margin": selected["margin"],
        "validation_curve": curve,
        "test": identification_metrics(gallery, test, threshold=selected["threshold"], margin=selected["margin"]),
    }


def crop_inputs(image, observation) -> dict:
    """Contexto 25% por lado, limitado à mesma imagem orientada do detector."""
    height, width = image.shape[:2]
    x, y, w, h = observation.box
    left, top = max(0, int(x - w * .25)), max(0, int(y - h * .25))
    right, bottom = min(width, int(x + w * 1.25)), min(height, int(y + h * 1.25))
    if observation.aligned_image is None or right <= left or bottom <= top:
        raise ValueError("Recorte indisponível.")
    return {"aligned": observation.aligned_image, "context": image[top:bottom, left:right], "whole_image": image}


def benchmark(manifest_path: Path, *, detector, gemma, authorization_reference=None) -> dict:
    """Providers locais injetados; relatório sem caminhos, sujeitos ou vetores."""
    from PIL import Image, ImageOps

    manifest = load_manifest(manifest_path, authorization_reference)
    records = {name: {split: [] for split in ("gallery", "validation", "test")}
               for name in ("sface", *STRATEGIES)}
    latencies = {name: [] for name in records}
    ground_truth = detected = 0
    start, cpu_start = perf_counter(), process_time()
    from threading import Event, Thread

    import psutil

    process = psutil.Process()
    peak = [process.memory_info().rss]
    stop = Event()
    def sample_memory():
        while not stop.wait(.05):
            peak[0] = max(peak[0], process.memory_info().rss)
    sampler = Thread(target=sample_memory, daemon=True)
    sampler.start()
    try:
        for item in manifest["photos"]:
            path = manifest_path.parent / item["path"]
            observations = detector.observe_highres_path(path, include_embedding=False)
            boxes = [(f.box[0] / f.image_width, f.box[1] / f.image_height,
                      f.box[2] / f.image_width, f.box[3] / f.image_height) for f in observations]
            matches = match_boxes([face["box"] for face in item["faces"]], boxes)
            ground_truth += len(item["faces"])
            detected += len(matches)
            with Image.open(path) as opened:
                image = np.asarray(ImageOps.exif_transpose(opened).convert("RGB"))[:, :, ::-1].copy()
            for truth_id, detection_id in matches.items():
                face, subject = observations[detection_id], item["faces"][truth_id]["subject"]
                inputs = crop_inputs(image, face)
                for name in records:
                    before = perf_counter()
                    vector = detector.embed_aligned(inputs["aligned"]) if name == "sface" else gemma.embed_aligned(inputs[name])
                    latencies[name].append((perf_counter() - before) * 1000)
                    records[name][item["split"]].append((subject, vector))
                if sum(len(rows) for rows in records["sface"].values()) > 20000:
                    raise ValueError("Limite de 20000 faces anotadas atingido.")
            del observations, image
        results = {}
        for name, partitions in records.items():
            results[name] = {"embedding_latency_ms": {
                label: float(np.quantile(latencies[name], quantile)) if latencies[name] else None
                for label, quantile in (("p50", .5), ("p95", .95), ("p99", .99))
            }, "dimensions": {}}
            for dimension in ((128,) if name == "sface" else DIMENSIONS):
                normalized = {}
                for split, rows in partitions.items():
                    vectors = normalized_matrix([row[1] for row in rows], dimension) if rows else []
                    normalized[split] = [(row[0], vector) for row, vector in zip(rows, vectors, strict=True)]
                results[name]["dimensions"][str(dimension)] = {
                    "index_bytes_float32": len(partitions["gallery"]) * dimension * 4,
                    **calibrated_comparison(normalized["gallery"], normalized["validation"], normalized["test"]),
                    "comparison_load": [comparison_load(normalized["gallery"], normalized["test"], concurrency=count)
                                        for count in (1, 2, 4, 8)],
                }
        return {
            "synthetic": manifest["synthetic"], "architecture": platform.machine(),
            "scope": "offline_matched_detections; excludes product queues, ciphertext and tenant fairness",
            "ground_truth_faces": ground_truth, "detected_truth_faces": detected,
            "seconds": perf_counter() - start, "cpu_seconds": process_time() - cpu_start,
            "peak_process_rss_bytes": max(peak[0], process.memory_info().rss),
            "vram": {"status": "not_measured", "reason": "cpu_only_protocol"},
            "model_revision": gemma.model_version, "results": results,
        }
    finally:
        stop.set()
        sampler.join(timeout=1)
        for partitions in records.values():
            for rows in partitions.values():
                rows.clear()  # Nenhum vetor é exportado ou persistido.


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sface-model-root", type=Path, required=True)
    parser.add_argument("--gemma-model-root", type=Path, required=True)
    parser.add_argument("--authorization-reference")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    load_manifest(args.manifest, args.authorization_reference)
    # Relatório agregado fora do corpus, nunca sobrescreve amostras/manifesto.
    if args.output.resolve().is_relative_to(args.manifest.parent.resolve()):
        raise ValueError("Grave o relatório fora do diretório privado do corpus.")
    from app.facial.gemma_assets import verify_gemma_model
    from app.facial.gemma_provider import GemmaFaceEmbeddingProvider
    from app.facial.model_assets import verify_models
    from app.facial.provider import OpenCvSFaceProvider

    verify_gemma_model(args.gemma_model_root)
    models = verify_models(Path(__file__).resolve().parents[1] / "backend/facial-assets/model-manifest.json", args.sface_model_root)
    detector = OpenCvSFaceProvider(models["yunet"], models["sface"])
    gemma = GemmaFaceEmbeddingProvider(detector, model_path=args.gemma_model_root)
    report = benchmark(args.manifest, detector=detector, gemma=gemma,
                       authorization_reference=args.authorization_reference)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 -- Fronteira CLI não publica paths nem conteúdo do corpus.
        raise SystemExit("Benchmark não concluído: verifique manifesto, autorização e runtime local.") from None
