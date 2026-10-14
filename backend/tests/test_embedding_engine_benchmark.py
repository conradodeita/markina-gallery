"""Contratos do comparador isolado com vetores e JPEGs sintéticos."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from embedding_engine_benchmark import (
    benchmark,
    calibrated_comparison,
    comparison_load,
    identification_metrics,
    load_manifest,
    normalized_matrix,
)


def test_truncation_renormalizes_and_rejects_zero_vectors():
    result = normalized_matrix([[3, 4, 99]], 2)
    assert result.tolist()[0] == pytest.approx([.6, .8])
    with pytest.raises(ValueError, match="nulo"):
        normalized_matrix([[0, 0, 99]], 2)


def test_open_set_identification_counts_unknown_and_wrong_separately():
    gallery = [("a", [1, 0]), ("b", [0, 1])]
    result = identification_metrics(gallery, [("a", [1, 0]), ("a", [0, 1]), ("c", [-1, 0])], threshold=.75)
    assert result["correct_identifications"] == 1
    assert result["wrong_identifications"] == 1
    assert result["correct_unknown_rejections"] == 1
    assert result["precision"] == .5 and result["far"] == 0


def test_final_test_does_not_influence_calibration():
    gallery = [("a", [1, 0]), ("b", [0, 1])]
    validation = [("a", [1, 0]), ("c", [-1, 0])]
    good = calibrated_comparison(gallery, validation, [("b", [0, 1])])
    bad = calibrated_comparison(gallery, validation, [("b", [1, 0])])
    assert (good["threshold"], good["margin"]) == (bad["threshold"], bad["margin"])
    assert good["test"]["correct_identifications"] == 1
    assert bad["test"]["wrong_identifications"] == 1
    assert calibrated_comparison(gallery, [("a", [1, 0])], [("b", [0, 1])])["status"] == "insufficient_known_or_unknown_validation"


def test_real_execution_requires_explicit_authorization_before_reading_photos(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"synthetic": False, "photos": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="autorização"):
        load_manifest(path)


def test_identical_image_cannot_leak_across_partitions(tmp_path):
    for name in ("a.jpg", "b.jpg"):
        (tmp_path / name).write_bytes(b"same-image")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"synthetic": True, "photos": [
        {"path": "a.jpg", "split": "gallery", "faces": []},
        {"path": "b.jpg", "split": "test", "faces": []},
    ]}), encoding="utf-8")
    with pytest.raises(ValueError, match="atravessar"):
        load_manifest(path)


def test_harness_compares_same_detections_and_exports_only_aggregates(tmp_path):
    records = []
    for i, (split, subject) in enumerate([
        ("gallery", "private-a"), ("gallery", "private-b"),
        ("validation", "private-a"), ("validation", "private-unknown"),
        ("test", "private-b"), ("test", "private-unknown"),
    ]):
        color = {"private-a": 20, "private-b": 80, "private-unknown": 140}[subject]
        image = Image.new("RGB", (32, 32), (color, color, color))
        image.putpixel((0, 0), (i * 20, 255, 0))
        name = f"private-file-{i}.jpg"
        image.save(tmp_path / name)
        records.append({"path": name, "split": split, "faces": [{"subject": subject, "box": [.25, .25, .5, .5]}]})
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"synthetic": True, "photos": records}), encoding="utf-8")
    observed = []
    def vector(image, dimension):
        result = [0.] * dimension
        result[min(2, int(float(np.median(image)) // 60))] = 1
        return result
    class Detector:
        def observe_highres_path(self, path, *, include_embedding):
            assert not include_embedding
            observed.append(path.name)
            with Image.open(path) as image:
                aligned = np.asarray(image)[8:24, 8:24].copy()
            return [SimpleNamespace(box=(8, 8, 16, 16), image_width=32, image_height=32, aligned_image=aligned)]
        def embed_aligned(self, image):
            return vector(image, 128)
    class Gemma:
        model_version = "synthetic-gemma-version"
        def embed_aligned(self, image):
            return vector(image, 768)
    result = benchmark(path, detector=Detector(), gemma=Gemma())
    assert len(observed) == 6  # Uma detecção para todos os motores/estratégias.
    assert result["detected_truth_faces"] == result["ground_truth_faces"] == 6
    assert set(result["results"]) == {"sface", "aligned", "context", "whole_image"}
    assert set(result["results"]["aligned"]["dimensions"]) == {"768", "512", "256", "128"}
    assert result["results"]["aligned"]["dimensions"]["768"]["test"]["correct_identifications"] == 1
    assert "private-" not in json.dumps(result)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(["manifest.json", *observed])


def test_comparison_load_is_bounded_and_does_not_export_vectors():
    gallery = [("private-person", [1, 0])]
    result = comparison_load(gallery, gallery, concurrency=2)
    assert result["queries"] == 1 and result["concurrency"] == 2
    assert result["comparison_ms"]["p99"] >= 0
    assert result["including_queue_ms"]["p50"] >= result["comparison_ms"]["p50"]
    assert "private-person" not in json.dumps(result)
    with pytest.raises(ValueError, match="Concorrência"):
        comparison_load(gallery, gallery, concurrency=100)
