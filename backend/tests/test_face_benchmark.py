"""Ground truth um-a-um e recuperação separados do recall de detecção."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.face_benchmark import load_corpus, match_boxes, retrieval_metrics


def test_matching_does_not_count_duplicate_faces_twice():
    truth = [(0, 0, 0.2, 0.2), (0.4, 0, 0.2, 0.2)]
    assert len(match_boxes(truth, [truth[0], truth[0], truth[1]])) == 2
    assert len(match_boxes(truth, [truth[0]])) == 1


def test_retrieval_uses_detected_ground_truth_only():
    records = [
        (0, "a", (1.0, 0.0)),
        (1, "a", (1.0, 0.0)),
        (2, "b", (0.0, 1.0)),
        (3, "b", (0.0, 1.0)),
    ]
    report = retrieval_metrics(records)
    assert report["positive_pairs"] == 2
    assert report["negative_pairs"] == 4
    assert report["top_k"]["1"] == 1
    assert report["thresholds"][75]["false_positives"] == 0
    assert report["thresholds"][75]["false_negatives"] == 0


def test_real_manifest_requires_provenance_and_expiry(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"synthetic": False, "photos": []}))
    with pytest.raises(ValueError, match="origem"):
        load_corpus(path)


def test_identical_image_cannot_leak_across_calibration_and_validation(tmp_path):
    (tmp_path / "one.jpg").write_bytes(b"synthetic-image")
    (tmp_path / "two.jpg").write_bytes(b"synthetic-image")
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "synthetic": True,
                "photos": [
                    {"path": "one.jpg", "split": "calibration", "faces": []},
                    {"path": "two.jpg", "split": "validation", "faces": []},
                ],
            }
        )
    )
    with pytest.raises(ValueError, match="mesma imagem"):
        load_corpus(path)
