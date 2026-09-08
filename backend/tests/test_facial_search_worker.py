"""Execução retomável da busca facial sem depender da tela aberta."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth import (
    AuditEvent,
    Base,
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    FacialJob,
    FacialRollout,
    FacialSearchCandidate,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    FacialSearchSnapshotItem,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFaceEmbedding,
    PhotoFolder,
    PhotoSelection,
    now,
)
from app.facial.capacity import FacialSearchCapacityError
from app.facial.config import FacialSettings
from app.facial.crypto import FacialCipher
from app.facial.engine import replace_photo_index
from app.facial.jobs import FacialJobRepository
from app.facial.notifications import (
    enqueue_search_notification,
    process_next_search_notification,
)
from app.facial.provider import FaceObservation, normalize_embedding
from app.facial.retention import process_claimed_cleanup_job
from app.facial.search import (
    FacialSearchError,
    authorize_search_candidate_selection,
    cancel_search_request,
    create_search_request,
    read_search_result,
    reject_search_candidate,
)
from app.facial.search_worker import process_claimed_search_job
from app.messaging import WhatsAppDeliveryError, WhatsAppDeliveryResult
from app.private_derivation import derive_client_selection


def _vector(first: float, second: float = 0.0) -> tuple[float, ...]:
    return normalize_embedding([first, second, *([0.0] * 126)])


def _face(
    vector: tuple[float, ...], *, blur: float = 100.0
) -> FaceObservation:
    return FaceObservation(
        embedding=vector,
        detection_confidence=0.99,
        box=(100, 80, 180, 180),
        landmarks=((130, 125), (210, 125), (170, 160), (145, 200), (195, 200)),
        blur_variance=blur,
    )


def _jpeg() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (320, 240), (100, 110, 120)).save(stream, format="JPEG")
    return stream.getvalue()


class Provider:
    def __init__(self, query_observations, *, fail_query: bool = False) -> None:
        self.query_observations = query_observations
        self.fail_query = fail_query

    def observe_path(self, _path: Path):
        return [_face(_vector(1.0))]

    def observe_bytes(self, _payload: bytes):
        if self.fail_query:
            raise RuntimeError("detalhe sensível que não deve persistir")
        return self.query_observations


class Messenger:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls = []

    def send_transactional(self, phone_e164, message, *, idempotency_key):
        self.calls.append((phone_e164, message, idempotency_key))
        if self.failure:
            raise self.failure
        return WhatsAppDeliveryResult("external-1", phone_e164, "accepted")


def _settings(tmp_path: Path) -> FacialSettings:
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
        max_jobs_per_process=100,
        model_idle_seconds=300,
        job_lease_seconds=120,
        queue_block_seconds=10,
        max_reference_bytes=10_485_760,
        max_reference_pixels=25_000_000,
    )


def _base(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'worker.db'}")
    Base.metadata.create_all(engine)
    db = Session(engine)
    parent = ParentGallery(id=uuid4(), name="Evento sintético")
    client = Client(id=uuid4(), full_name="Cliente", phone_e164="+5511999999998")
    registration = ParentGalleryRegistration(
        parent_gallery_id=parent.id, client_id=client.id, status="active"
    )
    folder = PhotoFolder(
        id=uuid4(),
        parent_gallery_id=parent.id,
        name="Fotos",
        status="released",
        purpose="content",
    )
    policy = GalleryFacialPolicy(
        id=uuid4(),
        parent_gallery_id=parent.id,
        status="active",
        legal_notice_version="notice-v1",
        legal_basis_reference="synthetic-only",
        retention_policy_version="retention-v1",
        minor_policy_version="minor-disabled-v1",
        model_version="model-v1",
        quality_version="quality-v1",
        calibration_version="calibration-v1",
        index_generation=1,
    )
    rollout = FacialRollout(
        environment="test",
        parent_gallery_id=parent.id,
        status="active",
        stage="canary",
        model_version="model-v1",
        quality_version="quality-v1",
        calibration_version="calibration-v1",
        legal_notice_version="notice-v1",
        consent_version="consent-v1",
        legal_basis_reference="synthetic-only",
        retention_policy_version="retention-v1",
    )
    db.add_all((parent, client, registration, folder, policy, rollout))
    db.commit()
    return engine, db, parent, client, folder


def _add_photo(db: Session, parent, folder, root: Path) -> PhotoAsset:
    photo = PhotoAsset(
        id=uuid4(),
        parent_gallery_id=parent.id,
        folder_id=folder.id,
        filename="foto.jpg",
        storage_key=f"{parent.id}/{uuid4()}.jpg",
        available=True,
    )
    protected_derivative = MediaDerivative(
        photo_asset_id=photo.id,
        variant="client_preview",
        status="ready",
        relative_path=f"{photo.id}/client_preview.jpg",
        width=640,
        height=480,
    )
    derivative = MediaDerivative(
        photo_asset_id=photo.id,
        variant="admin_preview",
        status="ready",
        relative_path=f"{photo.id}/admin_preview.jpg",
        width=640,
        height=480,
    )
    protected_path = root / protected_derivative.relative_path
    protected_path.parent.mkdir(parents=True, exist_ok=True)
    protected_path.write_bytes(b"protected-synthetic-preview")
    path = root / derivative.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"synthetic-preview")
    db.add_all((photo, protected_derivative, derivative))
    db.commit()
    return photo


def _index_photo(
    db: Session,
    photo: PhotoAsset,
    root: Path,
    settings: FacialSettings,
    cipher: FacialCipher,
) -> None:
    replace_photo_index(
        db,
        photo_id=photo.id,
        derivatives_root=root,
        provider=Provider([]),
        cipher=cipher,
        settings=settings,
    )
    embedding = db.scalar(
        select(PhotoFaceEmbedding).where(PhotoFaceEmbedding.photo_asset_id == photo.id)
    )
    assert embedding is not None
    db.add(
        FacialJob(
            kind="index",
            status="completed",
            idempotency_key=f"index:{photo.id}:{embedding.preview_fingerprint}",
            parent_gallery_id=photo.parent_gallery_id,
            photo_asset_id=photo.id,
            model_version=settings.model_version,
            quality_version=settings.quality_version,
            preview_fingerprint=embedding.preview_fingerprint,
        )
    )
    db.commit()


def _create_request(db, parent, client, settings):
    item = create_search_request(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        consent_version="consent-v1",
        subject_declaration="adult",
        representation_reference=None,
        payload=_jpeg(),
        settings=settings,
    )
    db.commit()
    return item


def test_one_hundred_concurrent_searches_survive_backpressure_and_worker_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    database_path = tmp_path / "concurrent-load.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"timeout": 60},
        poolclass=NullPool,
    )
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")
        connection.exec_driver_sql("PRAGMA busy_timeout=60000")
        connection.commit()
    Base.metadata.create_all(engine)
    settings = replace(
        _settings(tmp_path),
        reference_root=tmp_path / "concurrent-references",
        search_queue_max_depth=100,
    )
    galleries = [
        ParentGallery(id=uuid4(), name=f"Evento sintético {index}")
        for index in range(2)
    ]
    gallery_ids = [gallery.id for gallery in galleries]
    with Session(engine) as setup:
        setup.add_all(galleries)
        for gallery in galleries:
            setup.add_all(
                (
                    GalleryFacialPolicy(
                        id=uuid4(),
                        parent_gallery_id=gallery.id,
                        status="active",
                        legal_notice_version="notice-v1",
                        legal_basis_reference="synthetic-only",
                        retention_policy_version="retention-v1",
                        minor_policy_version="minor-disabled-v1",
                        model_version="model-v1",
                        quality_version="quality-v1",
                        calibration_version="calibration-v1",
                        index_generation=1,
                    ),
                    FacialRollout(
                        environment="test",
                        parent_gallery_id=gallery.id,
                        status="active",
                        stage="canary",
                        model_version="model-v1",
                        quality_version="quality-v1",
                        calibration_version="calibration-v1",
                        legal_notice_version="notice-v1",
                        consent_version="consent-v1",
                        legal_basis_reference="synthetic-only",
                        retention_policy_version="retention-v1",
                    ),
                )
            )
        clients = []
        for index in range(100):
            gallery = galleries[index % len(galleries)]
            client = Client(
                id=uuid4(),
                full_name=f"Cliente sintética {index}",
                phone_e164=f"+55118{index:08d}",
            )
            clients.append((client.id, gallery.id))
            setup.add_all(
                (
                    client,
                    ParentGalleryRegistration(
                        parent_gallery_id=gallery.id,
                        client_id=client.id,
                        status="active",
                    ),
                )
            )
        setup.commit()

    barrier = Barrier(100)
    payload = _jpeg()

    def admit(scope: tuple) -> tuple:
        client_id, gallery_id = scope
        with Session(engine) as session:
            barrier.wait(timeout=30)
            item = create_search_request(
                session,
                parent_gallery_id=gallery_id,
                client_id=client_id,
                consent_version="consent-v1",
                subject_declaration="adult",
                representation_reference=None,
                payload=payload,
                settings=settings,
            )
            session.commit()
            return item.id, client_id, gallery_id

    with ThreadPoolExecutor(max_workers=100) as executor:
        accepted = list(executor.map(admit, clients))
    expected_scope = {
        request_id: (client_id, gallery_id)
        for request_id, client_id, gallery_id in accepted
    }

    assert len(expected_scope) == 100
    assert len(list(settings.reference_root.glob("*.reference"))) == 100
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(FacialSearchRequest)) == 100
        assert session.scalar(
            select(func.count())
            .select_from(FacialJob)
            .where(FacialJob.kind == "search", FacialJob.status == "queued")
        ) == 100
        client_id, gallery_id = clients[0]
        with pytest.raises(FacialSearchCapacityError):
            create_search_request(
                session,
                parent_gallery_id=gallery_id,
                client_id=client_id,
                consent_version="consent-v1",
                subject_declaration="adult",
                representation_reference=None,
                payload=payload,
                settings=settings,
            )
        session.rollback()
    assert len(list(settings.reference_root.glob("*.reference"))) == 100

    repository = FacialJobRepository()
    first_session = Session(engine)
    stale_claim = repository.claim_next(
        first_session, lease_seconds=60, job_class="search"
    )
    assert stale_claim is not None
    claimed_job = first_session.get(FacialJob, stale_claim.id)
    assert claimed_job is not None
    claimed_job.lease_expires_at = now() - timedelta(seconds=1)
    first_session.commit()
    first_session.close()

    with Session(engine) as resumed_session:
        resumed_claim = repository.claim_next(
            resumed_session, lease_seconds=60, job_class="search"
        )
        assert resumed_claim is not None and resumed_claim.id == stale_claim.id
        assert resumed_claim.lease_token != stale_claim.lease_token
        process_claimed_search_job(
            resumed_session,
            resumed_claim,
            repository=repository,
            provider=Provider([]),
            cipher=FacialCipher(active_key_id="test", keys={"test": b"k" * 32}),
            settings=settings,
        )
        processed = 1
        while claim := repository.claim_next(
            resumed_session, lease_seconds=60, job_class="search"
        ):
            process_claimed_search_job(
                resumed_session,
                claim,
                repository=repository,
                provider=Provider([]),
                cipher=FacialCipher(
                    active_key_id="test", keys={"test": b"k" * 32}
                ),
                settings=settings,
            )
            processed += 1

        assert processed == 100
        assert resumed_session.scalar(
            select(func.count())
            .select_from(FacialJob)
            .where(FacialJob.kind == "search", FacialJob.status == "completed")
        ) == 100
        assert resumed_session.scalar(
            select(func.count())
            .select_from(FacialSearchRequest)
            .where(FacialSearchRequest.status == "no_face")
        ) == 100
        for request_id, (client_id, gallery_id) in expected_scope.items():
            request, candidates = read_search_result(
                resumed_session,
                parent_gallery_id=gallery_id,
                client_id=client_id,
                request_id=request_id,
            )
            assert (request.client_id, request.parent_gallery_id) == (
                client_id,
                gallery_id,
            )
            assert candidates == []
        first_request_id, (first_client_id, first_gallery_id) = next(
            iter(expected_scope.items())
        )
        with pytest.raises(FacialSearchError):
            read_search_result(
                resumed_session,
                parent_gallery_id=(
                    gallery_ids[1]
                    if first_gallery_id == gallery_ids[0]
                    else gallery_ids[0]
                ),
                client_id=first_client_id,
                request_id=first_request_id,
            )
    assert list(settings.reference_root.glob("*.reference")) == []
    engine.dispose()


def test_claimed_search_is_cancelled_if_rollout_is_suspended(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    _engine, db, parent, client, _folder = _base(tmp_path)
    settings = _settings(tmp_path)
    repository = FacialJobRepository()
    request = _create_request(db, parent, client, settings)
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None and claim.kind == "search"
    rollout = db.scalar(
        select(FacialRollout).where(
            FacialRollout.parent_gallery_id == parent.id,
            FacialRollout.environment == settings.environment,
        )
    )
    assert rollout is not None
    rollout.status = "suspended"
    db.commit()

    completed = process_claimed_search_job(
        db,
        claim,
        repository=repository,
        provider=Provider([_face(_vector(1.0))]),
        cipher=FacialCipher(active_key_id="test", keys={"test": b"k" * 32}),
        settings=settings,
    )

    db.refresh(request)
    assert completed.status == "completed"
    assert request.status == "cancelled"
    assert request.reference_deleted_at is not None
    assert request.reference_locator_ciphertext is None


def test_worker_resumes_in_another_session_and_persists_only_rank_and_band(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    photo = _add_photo(db, parent, folder, tmp_path)
    photo_id = photo.id
    _index_photo(db, photo, tmp_path, settings, cipher)
    request = _create_request(db, parent, client, settings)
    request_id = request.id
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None
    db.close()

    resumed = Session(engine)
    completed = process_claimed_search_job(
        resumed,
        claim,
        repository=repository,
        provider=Provider([_face(_vector(1.0))]),
        cipher=cipher,
        settings=settings,
    )
    request = resumed.get(FacialSearchRequest, request_id)
    candidate = resumed.scalar(select(FacialSearchCandidate))

    assert completed.status == "completed"
    assert request is not None and request.status == "ready"
    assert request.reference_deleted_at is not None
    assert request.reference_locator_ciphertext is None
    assert (request.compare_done, request.compare_total) == (1, 1)
    assert candidate is not None
    assert (candidate.photo_asset_id, candidate.rank, candidate.quality_band) == (
        photo_id,
        1,
        "best",
    )
    assert not hasattr(candidate, "similarity")
    assert resumed.scalar(select(func.count()).select_from(DerivedGallery)) == 0
    assert resumed.scalar(select(func.count()).select_from(DerivedGalleryMembership)) == 0


@pytest.mark.parametrize(
    ("observations", "expected"),
    [
        ([], "no_face"),
        ([_face(_vector(1.0)), _face(_vector(1.0))], "multiple_faces"),
        ([_face(_vector(1.0), blur=1.0)], "low_quality"),
        ([_face(_vector(0.0, 1.0))], "no_candidates"),
    ],
)
def test_worker_terminal_outcomes_delete_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observations,
    expected: str,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    _engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    photo = _add_photo(db, parent, folder, tmp_path)
    _index_photo(db, photo, tmp_path, settings, cipher)
    request = _create_request(db, parent, client, settings)
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None

    process_claimed_search_job(
        db,
        claim,
        repository=repository,
        provider=Provider(observations),
        cipher=cipher,
        settings=settings,
    )

    db.refresh(request)
    assert request.status == expected
    assert request.reference_deleted_at is not None
    assert not settings.reference_root.joinpath(f"{request.id}.reference").exists()


def test_waiting_index_uses_frozen_photo_set_and_completes_after_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    _engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    original = _add_photo(db, parent, folder, tmp_path)
    request = _create_request(db, parent, client, settings)
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None
    deferred = process_claimed_search_job(
        db,
        claim,
        repository=repository,
        provider=Provider([_face(_vector(1.0))]),
        cipher=cipher,
        settings=settings,
        retry_delay_seconds=0,
    )
    assert deferred.status == "queued"
    assert request.status == "waiting_index"

    later = _add_photo(db, parent, folder, tmp_path)
    _index_photo(db, original, tmp_path, settings, cipher)
    _index_photo(db, later, tmp_path, settings, cipher)
    resumed = repository.claim_next(db, lease_seconds=60)
    assert resumed is not None
    process_claimed_search_job(
        db,
        resumed,
        repository=repository,
        provider=Provider([_face(_vector(1.0))]),
        cipher=cipher,
        settings=settings,
    )

    assert db.scalar(select(func.count()).select_from(FacialSearchSnapshotItem)) == 1
    assert db.scalar(select(func.count()).select_from(FacialSearchCandidate)) == 1
    candidate = db.scalar(select(FacialSearchCandidate))
    assert candidate is not None and candidate.photo_asset_id == original.id


def test_incomplete_index_and_terminal_technical_failure_are_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    _engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    _add_photo(db, parent, folder, tmp_path)
    request = _create_request(db, parent, client, settings)
    request.expires_at = now() - timedelta(seconds=1)
    db.commit()
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None
    process_claimed_search_job(
        db,
        claim,
        repository=repository,
        provider=Provider([]),
        cipher=cipher,
        settings=settings,
    )
    db.refresh(request)
    assert request.status == "index_incomplete"

    # Uma nova consulta pronta falha tecnicamente e termina sem persistir detalhe.
    request2 = _create_request(db, parent, client, settings)
    snapshot = db.scalar(
        select(FacialSearchSnapshotItem).where(
            FacialSearchSnapshotItem.search_request_id == request2.id
        )
    )
    assert snapshot is not None
    snapshot.status = "ready"
    snapshot.preview_fingerprint = "a" * 64
    request2.snapshot_ready = request2.snapshot_total
    request2.compare_total = request2.snapshot_ready
    db.commit()
    claim2 = repository.claim_next(db, lease_seconds=60)
    assert claim2 is not None
    failed = process_claimed_search_job(
        db,
        claim2,
        repository=repository,
        provider=Provider([], fail_query=True),
        cipher=cipher,
        settings=settings,
        max_attempts=1,
    )
    db.refresh(request2)
    assert failed.status == "failed"
    assert failed.last_error_category == "internal_failure"
    assert "sensível" not in failed.last_error_category
    assert request2.status == "failed"
    assert request2.reference_deleted_at is not None


def test_read_reject_and_cancel_repeat_full_client_gallery_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    _engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    photo = _add_photo(db, parent, folder, tmp_path)
    _index_photo(db, photo, tmp_path, settings, cipher)
    request = _create_request(db, parent, client, settings)
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None
    process_claimed_search_job(
        db,
        claim,
        repository=repository,
        provider=Provider([_face(_vector(1.0))]),
        cipher=cipher,
        settings=settings,
    )

    visible_request, candidates = read_search_result(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        request_id=request.id,
    )
    assert visible_request.id == request.id
    assert [candidate.photo_asset_id for candidate in candidates] == [photo.id]
    assert db.scalar(select(func.count()).select_from(DerivedGallery)) == 0
    authorize_search_candidate_selection(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        request_id=request.id,
        photo_id=photo.id,
    )
    selected = derive_client_selection(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        photo_id=photo.id,
    )
    repeated = derive_client_selection(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        photo_id=photo.id,
    )
    db.commit()
    assert selected.gallery.id == repeated.gallery.id
    assert selected.selection_created is True
    assert repeated.selection_created is False
    assert db.scalar(select(func.count()).select_from(DerivedGallery)) == 1
    assert db.scalar(select(func.count()).select_from(DerivedGalleryMembership)) == 1
    assert db.scalar(select(func.count()).select_from(PhotoSelection)) == 1

    other_parent = ParentGallery(id=uuid4(), name="Outro evento sintético")
    other_client = Client(
        id=uuid4(), full_name="Outra cliente sintética", phone_e164="+5511888888888"
    )
    db.add_all(
        (
            other_parent,
            other_client,
            ParentGalleryRegistration(
                parent_gallery_id=other_parent.id,
                client_id=other_client.id,
                status="active",
            ),
        )
    )
    db.commit()
    other_photo = _add_photo(db, parent, folder, tmp_path)

    for wrong_scope in (
        {"parent_gallery_id": other_parent.id, "client_id": client.id, "request_id": request.id},
        {"parent_gallery_id": parent.id, "client_id": other_client.id, "request_id": request.id},
        {"parent_gallery_id": parent.id, "client_id": client.id, "request_id": uuid4()},
    ):
        with pytest.raises(FacialSearchError, match="indisponível"):
            read_search_result(db, **wrong_scope)
    with pytest.raises(FacialSearchError, match="indisponível"):
        reject_search_candidate(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
            request_id=request.id,
            photo_id=other_photo.id,
        )

    rejected = reject_search_candidate(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        request_id=request.id,
        photo_id=photo.id,
    )
    db.commit()
    assert rejected.rejected_at is not None
    assert read_search_result(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        request_id=request.id,
    )[1] == []

    queued = _create_request(db, parent, client, settings)
    with pytest.raises(FacialSearchError, match="indisponível"):
        authorize_search_candidate_selection(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
            request_id=queued.id,
            photo_id=photo.id,
        )
    cancelled = cancel_search_request(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        request_id=queued.id,
        settings=settings,
    )
    db.commit()
    assert cancelled.status == "cancelled"
    assert cancelled.reference_deleted_at is not None
    search_job = db.scalar(
        select(FacialJob).where(FacialJob.search_request_id == queued.id)
    )
    assert search_job is not None and search_job.status == "cancelled"
    notification = db.scalar(
        select(FacialSearchNotificationOutbox).where(
            FacialSearchNotificationOutbox.search_request_id == queued.id
        )
    )
    assert notification is None
    assert cancel_search_request(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        request_id=queued.id,
        settings=settings,
    ).status == "cancelled"
    audit_records = list(
        db.scalars(select(AuditEvent).where(AuditEvent.event.like("facial.%")))
    )
    assert {
        "facial.search_consented",
        "facial.search_completed",
        "facial.candidate_rejected",
        "facial.search_cancelled",
    }.issubset({record.event for record in audit_records})
    forbidden = (
        "embedding",
        "vector",
        "score",
        "landmark",
        "bounding_box",
        client.phone_e164,
        client.full_name,
    )
    assert all(
        not any(value.lower() in record.subject.lower() for value in forbidden)
        for record in audit_records
    )


def test_cleanup_recovers_after_external_reference_delete_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    _engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    _add_photo(db, parent, folder, tmp_path)
    request = _create_request(db, parent, client, settings)
    request.expires_at = now() - timedelta(seconds=1)
    cleanup = db.scalar(
        select(FacialJob).where(
            FacialJob.search_request_id == request.id,
            FacialJob.idempotency_key.like("facial-search-reference-cleanup:%"),
        )
    )
    assert cleanup is not None
    cleanup.available_at = now() - timedelta(seconds=1)
    # Simula queda depois de apagar o arquivo, mas antes de gravar a prova no banco.
    settings.reference_root.joinpath(f"{request.id}.reference").unlink()
    db.commit()
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None and claim.id == cleanup.id

    completed = process_claimed_cleanup_job(
        db,
        claim,
        repository=repository,
        settings=settings,
    )
    db.refresh(request)
    search_job = db.scalar(
        select(FacialJob).where(
            FacialJob.search_request_id == request.id,
            FacialJob.kind == "search",
        )
    )
    assert completed.status == "completed"
    assert request.status == "index_incomplete"
    assert request.reference_deleted_at is not None
    assert search_job is not None and search_job.status == "cancelled"

    repeated, _ = repository.enqueue(
        db,
        kind="cleanup",
        idempotency_key=f"cleanup-repeat:{request.id}",
        parent_gallery_id=parent.id,
        search_request_id=request.id,
        priority=20,
    )
    db.commit()
    repeated_claim = repository.claim_next(db, lease_seconds=60)
    assert repeated_claim is not None and repeated_claim.id == repeated.id
    assert process_claimed_cleanup_job(
        db,
        repeated_claim,
        repository=repository,
        settings=settings,
    ).status == "completed"


def test_candidate_cleanup_physically_removes_expired_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    _engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    photo = _add_photo(db, parent, folder, tmp_path)
    _index_photo(db, photo, tmp_path, settings, cipher)
    request = _create_request(db, parent, client, settings)
    repository = FacialJobRepository()
    search_claim = repository.claim_next(db, lease_seconds=60)
    assert search_claim is not None
    process_claimed_search_job(
        db,
        search_claim,
        repository=repository,
        provider=Provider([_face(_vector(1.0))]),
        cipher=cipher,
        settings=settings,
    )
    candidate = db.scalar(select(FacialSearchCandidate))
    cleanup = db.scalar(
        select(FacialJob).where(
            FacialJob.search_request_id == request.id,
            FacialJob.idempotency_key.like("facial-search-candidate-cleanup:%"),
        )
    )
    assert candidate is not None and cleanup is not None
    candidate.expires_at = now() - timedelta(seconds=1)
    cleanup.available_at = now() - timedelta(seconds=1)
    db.commit()
    cleanup_claim = repository.claim_next(db, lease_seconds=60)
    assert cleanup_claim is not None and cleanup_claim.id == cleanup.id

    process_claimed_cleanup_job(
        db,
        cleanup_claim,
        repository=repository,
        settings=settings,
    )

    assert db.scalar(select(func.count()).select_from(FacialSearchCandidate)) == 0


def test_completion_notification_is_encrypted_idempotent_and_sent_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv("MARKINA_PUBLIC_URL", "https://gallery.example.test")
    _engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    photo = _add_photo(db, parent, folder, tmp_path)
    _index_photo(db, photo, tmp_path, settings, cipher)
    request = _create_request(db, parent, client, settings)
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None
    process_claimed_search_job(
        db,
        claim,
        repository=repository,
        provider=Provider([_face(_vector(1.0))]),
        cipher=cipher,
        settings=settings,
    )
    notification = db.scalar(select(FacialSearchNotificationOutbox))
    assert notification is not None and notification.status == "queued"
    assert b"public-galleries" not in notification.payload_ciphertext
    assert not hasattr(notification, "recipient_phone")
    repeated = enqueue_search_notification(
        db,
        request=request,
        result_status="ready",
        cipher=cipher,
        settings=settings,
    )
    assert repeated is not None and repeated.id == notification.id

    messenger = Messenger()
    assert process_next_search_notification(
        db,
        provider=messenger,
        cipher=cipher,
        settings=settings,
    )
    assert len(messenger.calls) == 1
    recipient, message, key = messenger.calls[0]
    assert recipient == client.phone_e164
    assert key == notification.idempotency_key
    assert message.endswith(f"/public-galleries/{parent.id}")
    assert all(word not in message.lower() for word in ("score", "rosto", "identidade", "quantidade"))
    db.refresh(notification)
    assert notification.status == "sent"
    assert notification.payload_ciphertext == b""
    assert process_next_search_notification(
        db,
        provider=messenger,
        cipher=cipher,
        settings=settings,
    ) is False
    assert len(messenger.calls) == 1


def test_unavailable_channel_retries_without_changing_result_and_stale_send_is_not_repeated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv("MARKINA_PUBLIC_URL", "https://gallery.example.test")
    _engine, db, parent, client, folder = _base(tmp_path)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    photo = _add_photo(db, parent, folder, tmp_path)
    _index_photo(db, photo, tmp_path, settings, cipher)
    request = _create_request(db, parent, client, settings)
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None
    process_claimed_search_job(
        db,
        claim,
        repository=repository,
        provider=Provider([_face(_vector(0.0, 1.0))]),
        cipher=cipher,
        settings=settings,
    )
    notification = db.scalar(select(FacialSearchNotificationOutbox))
    assert notification is not None and notification.result_kind == "no_candidates"
    unavailable = Messenger(
        failure=WhatsAppDeliveryError("offline", transient=True)
    )
    assert process_next_search_notification(
        db,
        provider=unavailable,
        cipher=cipher,
        settings=settings,
    )
    db.refresh(notification)
    assert request.status == "no_candidates"
    assert notification.status == "queued"
    assert notification.last_error_category == "delivery_unavailable"

    # Estado ambíguo após queda nunca é reenviado automaticamente.
    notification.status = "processing"
    notification.lease_expires_at = now() - timedelta(seconds=1)
    db.commit()
    fresh = Messenger()
    assert process_next_search_notification(
        db,
        provider=fresh,
        cipher=cipher,
        settings=settings,
    )
    db.refresh(notification)
    assert notification.status == "failed"
    assert notification.last_error_category == "ambiguous_delivery"
    assert fresh.calls == []
