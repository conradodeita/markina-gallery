"""Isolated benchmark harness for event-scoped facial filtering."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np


@dataclass(frozen=True)
class FaceObservation:
    embedding: np.ndarray
    detection_score: float
    box: tuple[int, int, int, int]
    blur_variance: float


@dataclass(frozen=True)
class IndexedPhoto:
    event_id: str
    path: str
    identities: tuple[str, ...]
    scenario: str
    faces: tuple[FaceObservation, ...]


class FaceProvider(Protocol):
    model_id: str
    model_version: str

    def observe(self, image_path: Path) -> list[FaceObservation]: ...


class OpenCvSFaceProvider:
    model_id = "opencv-yunet-sface"
    model_version = "yunet-2023mar+sface-2021dec"

    def __init__(self, yunet_path: Path, sface_path: Path) -> None:
        import cv2

        self.cv2 = cv2
        self.detector = cv2.FaceDetectorYN.create(
            str(yunet_path), "", (320, 320), 0.75, 0.3, 5000
        )
        self.recognizer = cv2.FaceRecognizerSF.create(str(sface_path), "")
        self.model_disk_bytes = yunet_path.stat().st_size + sface_path.stat().st_size

    def observe(self, image_path: Path) -> list[FaceObservation]:
        image = self.cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"JPEG ilegível: {image_path}")
        height, width = image.shape[:2]
        self.detector.setInputSize((width, height))
        _, detected = self.detector.detect(image)
        if detected is None:
            return []
        observations: list[FaceObservation] = []
        for face in detected:
            aligned = self.recognizer.alignCrop(image, face)
            feature = self.recognizer.feature(aligned).reshape(-1).astype(np.float32)
            norm = float(np.linalg.norm(feature))
            if not norm:
                continue
            gray = self.cv2.cvtColor(aligned, self.cv2.COLOR_BGR2GRAY)
            blur_variance = float(self.cv2.Laplacian(gray, self.cv2.CV_64F).var())
            observations.append(
                FaceObservation(
                    embedding=feature / norm,
                    detection_score=float(face[-1]),
                    box=tuple(round(value) for value in face[:4]),
                    blur_variance=blur_variance,
                )
            )
        return observations


def _rss_bytes() -> int:
    try:
        import psutil

        return int(psutil.Process(os.getpid()).memory_info().rss)
    except ImportError:
        return 0


def load_dataset_manifest(dataset_root: Path) -> dict[str, Any]:
    manifest = json.loads((dataset_root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("synthetic_only") is not True:
        raise ValueError("O harness aceita somente corpus declarado como sintético.")
    return manifest


def index_event(
    provider: FaceProvider,
    dataset_root: Path,
    event_id: str,
    entries: list[dict[str, Any]],
) -> tuple[list[IndexedPhoto], dict[str, Any]]:
    started = time.perf_counter()
    cpu_started = time.process_time()
    rss_started = _rss_bytes()
    indexed: list[IndexedPhoto] = []
    detected_faces = 0
    expected_faces = 0
    failures = 0
    scenario_counts: dict[str, dict[str, int]] = {}
    for entry in entries:
        expected_faces += int(entry["expected_faces"])
        scenario = entry["scenario"]
        bucket = scenario_counts.setdefault(scenario, {"images": 0, "expected": 0, "detected": 0})
        bucket["images"] += 1
        bucket["expected"] += int(entry["expected_faces"])
        try:
            faces = tuple(provider.observe(dataset_root / entry["path"]))
        except (OSError, ValueError):
            failures += 1
            faces = ()
        detected_faces += len(faces)
        bucket["detected"] += len(faces)
        indexed.append(
            IndexedPhoto(
                event_id=event_id,
                path=entry["path"],
                identities=tuple(entry["identities"]),
                scenario=scenario,
                faces=faces,
            )
        )
    elapsed = time.perf_counter() - started
    cpu_seconds = time.process_time() - cpu_started
    rss_end = _rss_bytes()
    metrics = {
        "event_id": event_id,
        "images": len(entries),
        "expected_faces": expected_faces,
        "detected_faces": detected_faces,
        "face_coverage": detected_faces / expected_faces if expected_faces else 1.0,
        "failures": failures,
        "state": (
            "failed"
            if failures == len(entries)
            else "partial"
            if failures or detected_faces < expected_faces
            else "ready"
        ),
        "elapsed_seconds": elapsed,
        "cpu_seconds": cpu_seconds,
        "cpu_to_wall_ratio": cpu_seconds / elapsed if elapsed else 0.0,
        "images_per_second": len(entries) / elapsed if elapsed else 0.0,
        "rss_start_bytes": rss_started,
        "rss_end_bytes": rss_end,
        "rss_delta_bytes": max(0, rss_end - rss_started),
        "embedding_count": detected_faces,
        "estimated_embedding_bytes": sum(
            face.embedding.nbytes for photo in indexed for face in photo.faces
        ),
        "scenarios": scenario_counts,
    }
    return indexed, metrics


def analyze_query(provider: FaceProvider, query_path: Path) -> dict[str, Any]:
    try:
        observations = provider.observe(query_path)
    except (OSError, ValueError) as exc:
        return {"status": "technical_failure", "error_type": type(exc).__name__}
    if not observations:
        return {"status": "no_face"}
    if len(observations) > 1:
        return {"status": "multiple_faces", "detected_faces": len(observations)}
    face = observations[0]
    if min(face.box[2:]) < 72 or face.blur_variance < 18.0 or face.detection_score < 0.80:
        return {
            "status": "low_quality",
            "detection_score": face.detection_score,
            "blur_variance": face.blur_variance,
        }
    return {"status": "ready", "observation": face}


def search_event(
    query: FaceObservation,
    index: list[IndexedPhoto],
    *,
    event_id: str,
    threshold: float,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for photo in index:
        if photo.event_id != event_id:
            continue
        if not photo.faces:
            continue
        similarity = max(float(np.dot(query.embedding, face.embedding)) for face in photo.faces)
        if similarity >= threshold:
            candidates.append(
                {
                    "event_id": event_id,
                    "photo_path": photo.path,
                    "similarity": similarity,
                    "expected_identities": photo.identities,
                    "scenario": photo.scenario,
                }
            )
    return sorted(candidates, key=lambda item: item["similarity"], reverse=True)


def _evaluate_threshold(
    query_results: list[tuple[str, list[dict[str, Any]], float]],
    relevant_by_identity: dict[str, set[str]],
    scenario_by_path: dict[str, str],
) -> dict[str, Any]:
    true_positive = false_positive = false_negative = top1_correct = 0
    top5_true_positive = 0
    query_count = len(query_results)
    latencies: list[float] = []
    empty_result_queries = 0
    scenario_counts: dict[str, dict[str, int]] = {}
    for identity, candidates, query_seconds in query_results:
        relevant = relevant_by_identity[identity]
        returned = {candidate["photo_path"] for candidate in candidates}
        true_positive_paths = returned & relevant
        false_positive_paths = returned - relevant
        false_negative_paths = relevant - returned
        true_positive += len(true_positive_paths)
        false_positive += len(false_positive_paths)
        false_negative += len(false_negative_paths)
        top5_true_positive += len(
            {candidate["photo_path"] for candidate in candidates[:5]} & relevant
        )
        if candidates and candidates[0]["photo_path"] in relevant:
            top1_correct += 1
        if not candidates:
            empty_result_queries += 1
        for metric, paths in (
            ("true_positive", true_positive_paths),
            ("false_positive", false_positive_paths),
            ("false_negative", false_negative_paths),
        ):
            for path in paths:
                scenario = scenario_by_path[path]
                bucket = scenario_counts.setdefault(
                    scenario,
                    {"true_positive": 0, "false_positive": 0, "false_negative": 0},
                )
                bucket[metric] += 1
        latencies.append(query_seconds)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    scenario_metrics = {}
    for scenario, counts in scenario_counts.items():
        positive = counts["true_positive"] + counts["false_positive"]
        relevant = counts["true_positive"] + counts["false_negative"]
        scenario_metrics[scenario] = {
            **counts,
            "precision": counts["true_positive"] / positive if positive else 1.0,
            "recall": counts["true_positive"] / relevant if relevant else 0.0,
        }
    return {
        "queries": query_count,
        "true_positive_photos": true_positive,
        "false_positive_photos": false_positive,
        "false_negative_photos": false_negative,
        "precision": precision,
        "recall": recall,
        "recall_at_5": (
            top5_true_positive / min(5 * query_count, true_positive + false_negative)
            if query_count and true_positive + false_negative
            else 0.0
        ),
        "top1_accuracy": top1_correct / query_count if query_count else 0.0,
        "empty_result_queries": empty_result_queries,
        "median_query_seconds": statistics.median(latencies) if latencies else 0.0,
        "scenarios": scenario_metrics,
    }


def run_benchmark(
    provider: FaceProvider,
    dataset_root: Path,
    thresholds: tuple[float, ...],
) -> dict[str, Any]:
    manifest = load_dataset_manifest(dataset_root)
    indexes: dict[str, list[IndexedPhoto]] = {}
    index_metrics: dict[str, Any] = {}
    for event_id, entries in manifest["events"].items():
        indexes[event_id], index_metrics[event_id] = index_event(
            provider, dataset_root, event_id, entries
        )
    relevant_by_identity = {
        identity: {
            entry["path"]
            for entry in manifest["events"]["event-a"]
            if identity in entry["identities"]
        }
        for identity in manifest["identities"]
    }
    scenario_by_path = {
        entry["path"]: entry["scenario"]
        for entry in manifest["events"]["event-a"]
    }
    ready_queries: list[tuple[str, FaceObservation]] = []
    query_states: dict[str, int] = {}
    for query in manifest["queries"]:
        analyzed = analyze_query(provider, dataset_root / query["path"])
        status = analyzed["status"]
        query_states[status] = query_states.get(status, 0) + 1
        if status == "ready":
            ready_queries.append((query["identity"], analyzed["observation"]))

    threshold_metrics: dict[str, Any] = {}
    isolation_violations = 0
    for threshold in thresholds:
        results: list[tuple[str, list[dict[str, Any]], float]] = []
        for identity, observation in ready_queries:
            started = time.perf_counter()
            candidates = search_event(
                observation, indexes["event-a"], event_id="event-a", threshold=threshold
            )
            elapsed = time.perf_counter() - started
            isolation_violations += sum(
                candidate["event_id"] != "event-a" for candidate in candidates
            )
            results.append((identity, candidates, elapsed))
        threshold_metrics[f"{threshold:.3f}"] = _evaluate_threshold(
            results, relevant_by_identity, scenario_by_path
        )

    return {
        "schema_version": 1,
        "synthetic_only": True,
        "model": {"id": provider.model_id, "version": provider.model_version},
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "dataset": {
            "event_a_images": len(manifest["events"]["event-a"]),
            "event_b_images": len(manifest["events"]["event-b"]),
            "queries": len(manifest["queries"]),
            "identities": len(manifest["identities"]),
            "jpeg_disk_bytes": sum(
                (dataset_root / entry["path"]).stat().st_size
                for entries in manifest["events"].values()
                for entry in entries
            )
            + sum(
                (dataset_root / query["path"]).stat().st_size
                for query in manifest["queries"]
            ),
        },
        "model_disk_bytes": getattr(provider, "model_disk_bytes", None),
        "indexing": index_metrics,
        "query_states": query_states,
        "thresholds": threshold_metrics,
        "isolation_violations": isolation_violations,
        "created_commercial_entities": 0,
        "contains_embeddings": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--yunet", type=Path, required=True)
    parser.add_argument("--sface", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--thresholds",
        default="0.300,0.363,0.500,0.600,0.650,0.700,0.750,0.800,0.850,0.900,0.950",
    )
    args = parser.parse_args()
    provider = OpenCvSFaceProvider(args.yunet, args.sface)
    thresholds = tuple(float(value) for value in args.thresholds.split(","))
    report = run_benchmark(provider, args.dataset_root, thresholds)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
