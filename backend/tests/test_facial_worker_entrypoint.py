import threading
from types import SimpleNamespace

import pytest

from app.facial import face_worker


def test_sigterm_request_finishes_current_cycle_without_starting_another() -> None:
    stop_requested = threading.Event()
    cycles: list[str] = []

    class FakeWorker:
        processed_jobs = 0

        def run_cycle(self) -> None:
            cycles.append("cycle")
            self.processed_jobs += 1
            stop_requested.set()

    face_worker.run_worker_until_stopped(
        worker=FakeWorker(),
        active_class="maintenance",
        settings=SimpleNamespace(max_jobs_per_process=1, queue_block_seconds=1),
        cipher=object(),
        session_factory=lambda: None,
        stop_requested=stop_requested,
    )

    assert cycles == ["cycle"]


class _MaintenanceDrainComplete(RuntimeError):
    pass


def test_maintenance_worker_does_not_recycle_during_large_backlog(monkeypatch) -> None:
    cycles: list[int] = []

    class FakeWorker:
        processed_jobs = 0

        def run_cycle(self) -> None:
            cycles.append(len(cycles) + 1)
            self.processed_jobs += 1
            if len(cycles) == 2:
                raise _MaintenanceDrainComplete

    settings = SimpleNamespace(
        enabled=True,
        max_jobs_per_process=1,
        queue_block_seconds=1,
        active_key_id="key",
        aead_keys={"key": b"0" * 32},
    )
    monkeypatch.setattr(
        face_worker,
        "facial_settings_from_environment",
        lambda **_kwargs: settings,
    )
    monkeypatch.setattr(face_worker, "FacialCipher", lambda **_kwargs: object())
    monkeypatch.setattr(face_worker, "FacialJobRepository", lambda: object())
    monkeypatch.setattr(face_worker.Redis, "from_url", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(face_worker, "BlockingFacialWorker", lambda **_kwargs: FakeWorker())

    with pytest.raises(_MaintenanceDrainComplete):
        face_worker.main("maintenance")

    assert cycles == [1, 2]
