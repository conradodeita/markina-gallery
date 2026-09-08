"""Substituição atômica e busca vetorizada isolada por galeria."""

from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFaceEmbedding,
    PhotoFolder,
)
from app.facial.config import FacialSettings
from app.facial.crypto import FacialCipher, FacialCryptoError
from app.facial.engine import replace_photo_index, search_gallery_index
from app.facial.jobs import FacialJobRepository
from app.facial.provider import FaceObservation, normalize_embedding
from app.facial.worker import process_claimed_index_job


def _vector(first: float, second: float = 0.0) -> tuple[float, ...]:
    return normalize_embedding([first, second, *([0.0] * 126)])


def _face(vector, *, blur: float = 100.0) -> FaceObservation:
    return FaceObservation(
        embedding=vector,
        detection_confidence=0.99,
        box=(100, 80, 180, 180),
        landmarks=((130, 125), (210, 125), (170, 160), (145, 200), (195, 200)),
        blur_variance=blur,
    )


def _invalid_face(vector) -> FaceObservation:
    return FaceObservation(
        embedding=vector,
        detection_confidence=0.99,
        box=(100, 80, 180, 180),
        landmarks=((130, 125), (130, 125), (170, 160), (145, 200), (195, 200)),
        blur_variance=100.0,
    )


class Provider:
    def __init__(self, by_name) -> None:
        self.by_name = by_name

    def observe_path(self, path: Path):
        return self.by_name[path.parent.name]


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
        minor_search_enabled=False,
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


def _gallery(db: Session, root: Path, *, photos: int):
    parent = ParentGallery(id=uuid4(), name="Evento sintético")
    folder = PhotoFolder(
        id=uuid4(),
        parent_gallery_id=parent.id,
        name="Fotos",
        status="released",
        purpose="content",
    )
    policy = GalleryFacialPolicy(
        parent_gallery_id=parent.id,
        status="active",
        legal_notice_version="notice-v1",
        legal_basis_reference="synthetic-only",
        retention_policy_version="retention-v1",
        minor_policy_version="minor-disabled-v1",
        model_version="model-v1",
        quality_version="quality-v1",
        calibration_version="calibration-v1",
    )
    db.add_all((parent, folder, policy))
    created = []
    for index in range(photos):
        photo = PhotoAsset(
            id=uuid4(),
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename=f"foto-{index}.jpg",
            storage_key=f"{parent.id}/foto-{index}.jpg",
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
        path = root / derivative.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"preview-{parent.id}-{index}".encode())
        db.add_all((photo, protected_derivative, derivative))
        created.append(photo)
    db.commit()
    return parent, created


def test_index_replaces_all_faces_atomically_and_keeps_ciphertext_only(
    tmp_path: Path,
) -> None:
    db = Session(create_engine("sqlite:///:memory:"))
    Base.metadata.create_all(db.bind)
    _parent, photos = _gallery(db, tmp_path, photos=1)
    photo = photos[0]
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    settings = _settings(tmp_path)
    provider = Provider({str(photo.id): [_face(_vector(1.0))]})

    assert replace_photo_index(
        db,
        photo_id=photo.id,
        derivatives_root=tmp_path,
        provider=provider,
        cipher=cipher,
        settings=settings,
    ) == 1
    db.commit()
    original = db.scalar(
        select(PhotoFaceEmbedding).where(PhotoFaceEmbedding.photo_asset_id == photo.id)
    )
    assert original is not None
    assert b"embedding" not in original.payload_ciphertext

    provider.by_name[str(photo.id)] = [_face(_vector(1.0)), _face(_vector(0.9, 0.1))]
    assert replace_photo_index(
        db,
        photo_id=photo.id,
        derivatives_root=tmp_path,
        provider=provider,
        cipher=cipher,
        settings=settings,
    ) == 2
    db.commit()
    assert db.scalar(
        select(func.count())
        .select_from(PhotoFaceEmbedding)
        .where(PhotoFaceEmbedding.photo_asset_id == photo.id)
    ) == 2

    class FailingCipher:
        calls = 0

        def encrypt(self, payload, *, scope):
            self.calls += 1
            if self.calls == 2:
                raise FacialCryptoError("falha sintética")
            return cipher.encrypt(payload, scope=scope)

    provider.by_name[str(photo.id)] = [_face(_vector(1.0)), _face(_vector(0.8, 0.2))]
    try:
        replace_photo_index(
            db,
            photo_id=photo.id,
            derivatives_root=tmp_path,
            provider=provider,
            cipher=FailingCipher(),
            settings=settings,
        )
    except FacialCryptoError:
        db.rollback()
    assert db.scalar(
        select(func.count())
        .select_from(PhotoFaceEmbedding)
        .where(PhotoFaceEmbedding.photo_asset_id == photo.id)
    ) == 2


def test_vector_search_is_gallery_scoped_and_orders_best_before_other(
    tmp_path: Path,
) -> None:
    db = Session(create_engine("sqlite:///:memory:"))
    Base.metadata.create_all(db.bind)
    first_gallery, photos = _gallery(db, tmp_path, photos=2)
    other_gallery, sentinel = _gallery(db, tmp_path, photos=1)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    settings = _settings(tmp_path)
    provider = Provider(
        {
            str(photos[0].id): [_face(_vector(0.98, 0.02), blur=100.0)],
            str(photos[1].id): [_face(_vector(1.0), blur=5.0)],
            str(sentinel[0].id): [_face(_vector(1.0), blur=100.0)],
        }
    )
    for photo in (*photos, *sentinel):
        replace_photo_index(
            db,
            photo_id=photo.id,
            derivatives_root=tmp_path,
            provider=provider,
            cipher=cipher,
            settings=settings,
        )
    db.commit()

    matches = search_gallery_index(
        db,
        gallery_id=first_gallery.id,
        query_embedding=_vector(1.0),
        cipher=cipher,
        settings=settings,
        threshold_milli=750,
    )

    assert [match.photo_id for match in matches] == [photos[0].id, photos[1].id]
    assert [match.quality_band for match in matches] == ["best", "other"]
    assert sentinel[0].id not in {match.photo_id for match in matches}
    assert "similarity" not in repr(matches[0])
    assert other_gallery.id != first_gallery.id


def test_index_skips_only_invalid_face_observations_and_can_finish_empty(
    tmp_path: Path,
) -> None:
    db = Session(create_engine("sqlite:///:memory:"))
    Base.metadata.create_all(db.bind)
    parent, photos = _gallery(db, tmp_path, photos=2)
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    provider = Provider(
        {
            str(photos[0].id): [
                _invalid_face(_vector(0.9, 0.1)),
                _face(_vector(1.0)),
            ],
            str(photos[1].id): [_invalid_face(_vector(1.0))],
        }
    )

    assert (
        replace_photo_index(
            db,
            photo_id=photos[0].id,
            derivatives_root=tmp_path,
            provider=provider,
            cipher=cipher,
            settings=settings,
        )
        == 1
    )
    repository = FacialJobRepository()
    job, _created = repository.enqueue(
        db,
        kind="index",
        idempotency_key="worker-index-invalid-observation",
        parent_gallery_id=parent.id,
        photo_asset_id=photos[1].id,
        model_version="model-v1",
        quality_version="quality-v1",
        preview_fingerprint="b" * 64,
    )
    db.commit()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None and claim.id == job.id

    completed = process_claimed_index_job(
        db,
        claim,
        repository=repository,
        provider=provider,
        cipher=cipher,
        settings=settings,
        derivatives_root=tmp_path,
    )

    assert completed.status == "completed"
    assert (completed.progress_done, completed.progress_total) == (0, 0)
    rows = list(db.scalars(select(PhotoFaceEmbedding)))
    assert [(row.photo_asset_id, row.face_ordinal) for row in rows] == [
        (photos[0].id, 1)
    ]


def test_claimed_index_job_runs_in_worker_and_finishes_durably(tmp_path: Path) -> None:
    db = Session(create_engine("sqlite:///:memory:"))
    Base.metadata.create_all(db.bind)
    parent, photos = _gallery(db, tmp_path, photos=1)
    photo = photos[0]
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    provider = Provider({str(photo.id): [_face(_vector(1.0))]})
    repository = FacialJobRepository()
    job, _created = repository.enqueue(
        db,
        kind="index",
        idempotency_key="worker-index-synthetic",
        parent_gallery_id=parent.id,
        photo_asset_id=photo.id,
        model_version="model-v1",
        quality_version="quality-v1",
        preview_fingerprint="a" * 64,
    )
    db.commit()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None and claim.id == job.id

    completed = process_claimed_index_job(
        db,
        claim,
        repository=repository,
        provider=provider,
        cipher=cipher,
        settings=settings,
        derivatives_root=tmp_path,
    )

    assert completed.status == "completed"
    assert completed.lease_token is None
    assert (completed.progress_done, completed.progress_total) == (1, 1)
    assert db.scalar(
        select(func.count()).select_from(PhotoFaceEmbedding)
    ) == 1
