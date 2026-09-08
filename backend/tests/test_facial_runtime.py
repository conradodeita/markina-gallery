"""Espera bloqueante, descarga ociosa e limite do processo facial."""

from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import Base, ParentGallery
from app.facial.config import FacialSettings
from app.facial.jobs import FacialJobRepository
from app.facial.runtime import BlockingFacialWorker


def _settings(tmp_path: Path, *, max_jobs: int = 2, idle: int = 30) -> FacialSettings:
    return FacialSettings(
        enabled=True,
        environment="test",
        credential_environment="test",
        manifest_path=tmp_path / "manifest.json",
        model_root=tmp_path / "models",
        reference_root=tmp_path / "references",
        model_version="model-v1",
        quality_version="quality-v1",
        calibration_version="calibration-v1",
        legal_notice_version="notice-v1",
        consent_version="consent-v1",
        legal_basis_reference="synthetic-only",
        retention_policy_version="retention-v1",
        minor_policy_version="minor-disabled-v1",
        similarity_threshold_milli=750,
        active_key_id="test",
        aead_keys={"test": b"k" * 32},
        reference_retention_seconds=900,
        candidate_retention_seconds=86400,
        queue_name="markina:facial:jobs",
        worker_concurrency=1,
        max_jobs_per_process=max_jobs,
        model_idle_seconds=idle,
        job_lease_seconds=120,
        queue_block_seconds=10,
        max_reference_bytes=10_485_760,
        max_reference_pixels=25_000_000,
    )


class WakeSource:
    def __init__(self, clock) -> None:
        self.clock = clock
        self.calls = []

    def brpop(self, queue_name: str, timeout: int):
        self.calls.append((queue_name, timeout))
        self.clock[0] += timeout


class UnavailableWakeSource:
    def brpop(self, _queue_name: str, timeout: int):
        _ = timeout
        raise ConnectionError("redis sintético indisponível")


def _database(tmp_path: Path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'runtime.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as db:
        parent = ParentGallery(id=uuid4(), name="Evento")
        db.add(parent)
        db.commit()
        parent_id = parent.id
    return factory, parent_id


def test_empty_queue_blocks_without_loading_or_reprocessing(tmp_path: Path) -> None:
    factory, _parent_id = _database(tmp_path)
    clock = [0.0]
    wake = WakeSource(clock)
    loads = []
    worker = BlockingFacialWorker(
        settings=_settings(tmp_path),
        job_class="search",
        session_factory=factory,
        wake_source=wake,
        provider_loader=lambda: loads.append("loaded"),
        processor=lambda _db, _claim, _provider: None,
        clock=lambda: clock[0],
    )

    assert worker.run_cycle() is False
    assert wake.calls == [("markina:facial:jobs:search", 10)]
    assert loads == []
    assert worker.processed_jobs == 0


def test_cleanup_job_does_not_load_models(tmp_path: Path) -> None:
    factory, parent_id = _database(tmp_path)
    repository = FacialJobRepository()
    loads = []
    with factory() as db:
        repository.enqueue(
            db,
            kind="cleanup",
            idempotency_key="cleanup-without-model",
            parent_gallery_id=parent_id,
        )
        db.commit()
    worker = BlockingFacialWorker(
        settings=_settings(tmp_path),
        job_class="maintenance",
        session_factory=factory,
        wake_source=WakeSource([0.0]),
        provider_loader=lambda: loads.append("loaded"),
        provider_required=lambda _claim: False,
        processor=lambda db, claim, provider: (
            provider is None and repository.complete(db, claim)
        ),
        repository=repository,
    )

    assert worker.run_cycle() is True
    assert loads == []
    assert worker.model_loaded is False


def test_redis_failure_falls_back_to_paused_database_poll(tmp_path: Path) -> None:
    factory, _parent_id = _database(tmp_path)
    pauses = []
    worker = BlockingFacialWorker(
        settings=_settings(tmp_path),
        job_class="search",
        session_factory=factory,
        wake_source=UnavailableWakeSource(),
        provider_loader=lambda: object(),
        processor=lambda _db, _claim, _provider: None,
        sleeper=pauses.append,
    )

    assert worker.run_cycle() is False
    assert pauses == [10]


def test_provider_startup_failure_is_delegated_without_losing_claim(
    tmp_path: Path,
) -> None:
    factory, parent_id = _database(tmp_path)
    repository = FacialJobRepository()
    with factory() as db:
        job, _created = repository.enqueue(
            db,
            kind="index",
            idempotency_key="provider-failure",
            parent_gallery_id=parent_id,
            photo_asset_id=uuid4(),
            model_version="model-v1",
            quality_version="quality-v1",
            preview_fingerprint="a" * 64,
        )
        db.commit()
        job_id = job.id
    failures = []
    worker = BlockingFacialWorker(
        settings=_settings(tmp_path),
        job_class="index",
        session_factory=factory,
        wake_source=WakeSource([0.0]),
        provider_loader=lambda: (_ for _ in ()).throw(RuntimeError("detalhe")),
        provider_failure=lambda claim, error: failures.append((claim, type(error))),
        processor=lambda _db, _claim, _provider: None,
        repository=repository,
    )

    assert worker.run_cycle() is True
    assert failures[0][0].id == job_id
    assert failures[0][0].lease_token
    assert failures[0][1] is RuntimeError
    assert worker.processed_jobs == 1


def test_model_unloads_after_idle_and_loads_again_for_new_work(tmp_path: Path) -> None:
    factory, parent_id = _database(tmp_path)
    repository = FacialJobRepository()
    clock = [0.0]
    wake = WakeSource(clock)
    loads, unloads, processed = [], [], []

    def loader():
        provider = object()
        loads.append(provider)
        return provider

    def processor(db, claim, provider):
        processed.append((claim.id, provider))
        repository.complete(db, claim)

    worker = BlockingFacialWorker(
        settings=_settings(tmp_path, idle=10),
        job_class="index",
        session_factory=factory,
        wake_source=wake,
        provider_loader=loader,
        processor=processor,
        repository=repository,
        clock=lambda: clock[0],
        provider_unloader=unloads.append,
    )
    with factory() as db:
        repository.enqueue(
            db,
            kind="index",
            idempotency_key="first",
            parent_gallery_id=parent_id,
            photo_asset_id=uuid4(),
            model_version="model-v1",
            quality_version="quality-v1",
            preview_fingerprint="b" * 64,
        )
        db.commit()
    assert worker.run_cycle() is True
    assert worker.model_loaded is True

    assert worker.run_cycle() is False
    assert worker.model_loaded is False
    assert unloads == [loads[0]]

    with factory() as db:
        repository.enqueue(
            db,
            kind="index",
            idempotency_key="second",
            parent_gallery_id=parent_id,
            photo_asset_id=uuid4(),
            model_version="model-v1",
            quality_version="quality-v1",
            preview_fingerprint="c" * 64,
        )
        db.commit()
    assert worker.run_cycle() is True
    assert len(loads) == 2 and len(processed) == 2
    assert worker.model_loaded is False  # limite de dois jobs força reciclagem
