from pathlib import Path

import numpy as np

from scripts.face_spike.harness import (
    FaceObservation,
    IndexedPhoto,
    analyze_query,
    index_event,
    search_event,
)


def _face(vector: tuple[float, float], *, blur: float = 100.0) -> FaceObservation:
    embedding = np.asarray(vector, dtype=np.float32)
    embedding /= np.linalg.norm(embedding)
    return FaceObservation(
        embedding=embedding,
        detection_score=0.99,
        box=(0, 0, 120, 120),
        blur_variance=blur,
    )


class FakeProvider:
    model_id = "fake"
    model_version = "1"

    def __init__(self, observations):
        self.observations = observations

    def observe(self, image_path: Path):
        result = self.observations[image_path.name]
        if isinstance(result, Exception):
            raise result
        return result


def test_query_states_are_explicit() -> None:
    provider = FakeProvider(
        {
            "none.jpg": [],
            "many.jpg": [_face((1, 0)), _face((0, 1))],
            "blur.jpg": [_face((1, 0), blur=2.0)],
            "ready.jpg": [_face((1, 0))],
            "failed.jpg": ValueError("imagem inválida"),
        }
    )

    assert analyze_query(provider, Path("none.jpg"))["status"] == "no_face"
    assert analyze_query(provider, Path("many.jpg"))["status"] == "multiple_faces"
    assert analyze_query(provider, Path("blur.jpg"))["status"] == "low_quality"
    assert analyze_query(provider, Path("ready.jpg"))["status"] == "ready"
    failure = analyze_query(provider, Path("failed.jpg"))
    assert failure == {"status": "technical_failure", "error_type": "ValueError"}


def test_search_is_event_scoped_and_returns_only_filter_contract() -> None:
    query = _face((1, 0))
    index = [
        IndexedPhoto("event-a", "event-a/a.jpg", ("person-a",), "clean", (_face((1, 0)),)),
        IndexedPhoto("event-a", "event-a/b.jpg", ("person-b",), "clean", (_face((0, 1)),)),
        IndexedPhoto("event-b", "event-b/a.jpg", ("person-a",), "clean", (_face((1, 0)),)),
    ]

    candidates = search_event(query, index, event_id="event-a", threshold=0.5)

    assert [candidate["photo_path"] for candidate in candidates] == ["event-a/a.jpg"]
    assert all(candidate["event_id"] == "event-a" for candidate in candidates)
    assert not ({"derived_gallery", "selection", "membership", "authorization"} & candidates[0].keys())
    assert search_event(query, index, event_id="event-a", threshold=1.1) == []


def test_index_failure_is_partial_and_does_not_block_other_photos(tmp_path: Path) -> None:
    provider = FakeProvider(
        {
            "ready.jpg": [_face((1, 0))],
            "failed.jpg": ValueError("falha facial"),
        }
    )
    entries = [
        {
            "path": "ready.jpg",
            "identities": ["person-a"],
            "scenario": "clean",
            "expected_faces": 1,
        },
        {
            "path": "failed.jpg",
            "identities": ["person-b"],
            "scenario": "clean",
            "expected_faces": 1,
        },
    ]

    indexed, metrics = index_event(provider, tmp_path, "event-a", entries)

    assert len(indexed) == 2
    assert len(indexed[0].faces) == 1
    assert indexed[1].faces == ()
    assert metrics["state"] == "partial"
    assert metrics["failures"] == 1
