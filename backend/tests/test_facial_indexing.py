"""Indexação facial nasce somente de eventos explícitos e elegíveis."""

from pathlib import Path
from uuid import uuid4

from PIL import Image
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    FacialJob,
    FacialRollout,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
)
from app.facial.config import FacialSettings
from app.facial.indexing import (
    enqueue_gallery_backfill_page,
    enqueue_photo_index_if_eligible,
    reconcile_automatic_gallery_policies,
)
from app.media import generate_derivatives


def _settings(tmp_path: Path, *, enabled: bool = True) -> FacialSettings:
    return FacialSettings(
        enabled=enabled,
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


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _eligible_photo(
    db: Session,
    tmp_path: Path,
    *,
    status: str = "active",
    include_policy: bool = True,
):
    parent_id, folder_id, photo_id = uuid4(), uuid4(), uuid4()
    folder = PhotoFolder(
        id=folder_id,
        parent_gallery_id=parent_id,
        name="Fotos",
        status="released",
        purpose="content",
    )
    photo = PhotoAsset(
        id=photo_id,
        parent_gallery_id=parent_id,
        folder_id=folder_id,
        filename="foto.jpg",
        storage_key="event/foto.jpg",
        available=True,
    )
    protected_derivative = MediaDerivative(
        photo_asset_id=photo_id,
        variant="client_preview",
        status="ready",
        relative_path=f"{photo_id}/client_preview.jpg",
    )
    derivative = MediaDerivative(
        photo_asset_id=photo_id,
        variant="admin_preview",
        status="ready",
        relative_path=f"{photo_id}/admin_preview.jpg",
    )
    policy = GalleryFacialPolicy(
        parent_gallery_id=parent_id,
        status=status,
        legal_notice_version="notice-v1",
        legal_basis_reference="synthetic-only",
        retention_policy_version="retention-v1",
        minor_policy_version="minor-disabled-v1",
        model_version="model-v1",
        quality_version="quality-v1",
        calibration_version="calibration-v1",
    )
    db.add(ParentGallery(id=parent_id, name="Evento sintético"))
    db.add_all(
        (
            folder,
            photo,
            protected_derivative,
            derivative,
            FacialRollout(
                environment="test",
                parent_gallery_id=parent_id,
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
    if include_policy:
        db.add(policy)
    db.commit()
    path = tmp_path / derivative.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"protected-preview")
    return photo, derivative, path


def test_ready_preview_enqueues_once_and_activates_internal_policy_automatically(
    tmp_path: Path,
) -> None:
    db = _session()
    photo, derivative, path = _eligible_photo(db, tmp_path)
    settings = _settings(tmp_path)

    first = enqueue_photo_index_if_eligible(
        db, photo, derivative, derivative_path=path, settings=settings
    )
    second = enqueue_photo_index_if_eligible(
        db, photo, derivative, derivative_path=path, settings=settings
    )
    db.commit()

    assert first is not None and second is not None and first.id == second.id
    assert db.scalar(select(func.count()).select_from(FacialJob)) == 1
    assert first.status == "queued"

    other_db = _session()
    other_photo, other_derivative, other_path = _eligible_photo(
        other_db, tmp_path / "inactive", status="pending"
    )
    queued = enqueue_photo_index_if_eligible(
        other_db,
        other_photo,
        other_derivative,
        derivative_path=other_path,
        settings=settings,
    )
    other_db.commit()
    automatic_policy = other_db.scalar(
        select(GalleryFacialPolicy).where(
            GalleryFacialPolicy.parent_gallery_id == other_photo.parent_gallery_id
        )
    )
    assert queued is not None
    assert automatic_policy is not None
    assert automatic_policy.status == "active"
    assert automatic_policy.actor_admin_id is None


def test_disabled_global_gate_neither_creates_policy_nor_job(tmp_path: Path) -> None:
    db = _session()
    photo, derivative, path = _eligible_photo(
        db, tmp_path, include_policy=False
    )

    queued = enqueue_photo_index_if_eligible(
        db,
        photo,
        derivative,
        derivative_path=path,
        settings=_settings(tmp_path, enabled=False),
    )
    db.commit()

    assert queued is None
    assert db.scalar(select(func.count()).select_from(GalleryFacialPolicy)) == 0
    assert db.scalar(select(func.count()).select_from(FacialJob)) == 0


def test_rollout_allowlist_and_versions_fail_closed_before_enqueue(
    tmp_path: Path,
) -> None:
    db = _session()
    photo, derivative, path = _eligible_photo(
        db, tmp_path, include_policy=False
    )
    rollout = db.scalar(select(FacialRollout))
    assert rollout is not None
    rollout.status = "prepared"
    db.commit()

    assert (
        enqueue_photo_index_if_eligible(
            db,
            photo,
            derivative,
            derivative_path=path,
            settings=_settings(tmp_path),
        )
        is None
    )
    assert db.scalar(select(func.count()).select_from(GalleryFacialPolicy)) == 0
    assert db.scalar(select(func.count()).select_from(FacialJob)) == 0

    rollout.status = "active"
    rollout.quality_version = "quality-not-approved"
    db.commit()
    assert (
        enqueue_photo_index_if_eligible(
            db,
            photo,
            derivative,
            derivative_path=path,
            settings=_settings(tmp_path),
        )
        is None
    )
    assert db.scalar(select(func.count()).select_from(FacialJob)) == 0


def test_backfill_is_explicit_paginated_and_idempotent(tmp_path: Path) -> None:
    db = _session()
    first, _derivative, _path = _eligible_photo(db, tmp_path)
    settings = _settings(tmp_path)
    parent_id = first.parent_gallery_id
    folder_id = first.folder_id
    for index in range(3):
        photo = PhotoAsset(
            id=uuid4(),
            parent_gallery_id=parent_id,
            folder_id=folder_id,
            filename=f"foto-{index}.jpg",
            storage_key=f"event/foto-{index}.jpg",
            available=True,
        )
        protected_derivative = MediaDerivative(
            photo_asset_id=photo.id,
            variant="client_preview",
            status="ready",
            relative_path=f"{photo.id}/client_preview.jpg",
        )
        derivative = MediaDerivative(
            photo_asset_id=photo.id,
            variant="admin_preview",
            status="ready",
            relative_path=f"{photo.id}/admin_preview.jpg",
        )
        db.add_all((photo, protected_derivative, derivative))
        path = tmp_path / derivative.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"preview-{index}".encode())
    db.commit()

    first_page = enqueue_gallery_backfill_page(
        db,
        parent_gallery_id=parent_id,
        derivatives_root=tmp_path,
        limit=2,
        settings=settings,
    )
    db.commit()
    second_page = enqueue_gallery_backfill_page(
        db,
        parent_gallery_id=parent_id,
        derivatives_root=tmp_path,
        cursor=first_page.next_cursor,
        limit=2,
        settings=settings,
    )
    db.commit()

    assert (first_page.scanned, first_page.completed) == (2, False)
    assert (second_page.scanned, second_page.completed) == (2, True)
    assert db.scalar(select(func.count()).select_from(FacialJob)) == 4

    repeated = enqueue_gallery_backfill_page(
        db,
        parent_gallery_id=parent_id,
        derivatives_root=tmp_path,
        limit=500,
        settings=settings,
    )
    db.commit()
    assert repeated.scanned == 4
    assert db.scalar(select(func.count()).select_from(FacialJob)) == 4


def test_startup_reconciliation_backfills_only_new_or_divergent_galleries(
    tmp_path: Path,
) -> None:
    db = _session()
    photo, _derivative, _path = _eligible_photo(
        db, tmp_path, include_policy=False
    )
    settings = _settings(tmp_path)

    first = reconcile_automatic_gallery_policies(
        db,
        derivatives_root=tmp_path,
        settings=settings,
    )
    db.commit()
    second = reconcile_automatic_gallery_policies(
        db,
        derivatives_root=tmp_path,
        settings=settings,
    )
    db.commit()

    policy = db.scalar(
        select(GalleryFacialPolicy).where(
            GalleryFacialPolicy.parent_gallery_id == photo.parent_gallery_id
        )
    )
    assert (
        first.galleries_scanned,
        first.galleries_changed,
        first.photos_scanned,
        first.jobs_queued,
    ) == (1, 1, 1, 1)
    assert (
        second.galleries_scanned,
        second.galleries_changed,
        second.photos_scanned,
        second.jobs_queued,
    ) == (1, 0, 0, 0)
    assert policy is not None and policy.status == "active"
    assert db.scalar(select(func.count()).select_from(FacialJob)) == 1

    policy.model_version = "obsolete-model"
    db.commit()
    third = reconcile_automatic_gallery_policies(
        db,
        derivatives_root=tmp_path,
        settings=settings,
    )
    db.commit()
    assert third.galleries_changed == 1
    assert third.jobs_queued == 1
    assert db.scalar(
        select(func.count()).select_from(FacialJob).where(FacialJob.kind == "purge")
    ) == 1
    assert db.scalar(
        select(func.count()).select_from(FacialJob).where(FacialJob.kind == "index")
    ) == 2


def test_media_remains_available_when_facial_configuration_is_invalid(
    tmp_path: Path, monkeypatch
) -> None:
    db = _session()
    from app.auth import MediaJob, ParentGallery

    parent_id, folder_id, photo_id = uuid4(), uuid4(), uuid4()
    folder = PhotoFolder(
        id=folder_id,
        parent_gallery_id=parent_id,
        name="Upload",
        status="preparing",
        purpose="content",
    )
    photo = PhotoAsset(
        id=photo_id,
        parent_gallery_id=parent_id,
        folder_id=folder_id,
        filename="foto.jpg",
        storage_key="event/foto.jpg",
        available=False,
    )
    media_job = MediaJob(photo_asset_id=photo_id, status="queued", attempts=0)
    db.add_all((ParentGallery(id=parent_id, name="Evento"), folder, photo, media_job))
    db.commit()
    source_root = tmp_path / "source"
    derivatives_root = tmp_path / "derivatives"
    source_path = source_root / photo.storage_key
    source_path.parent.mkdir(parents=True)
    Image.new("RGB", (120, 80), (10, 20, 30)).save(source_path, format="JPEG")
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    monkeypatch.setenv("FACIAL_PROCESSING_ENABLED", "true")
    monkeypatch.delenv("FACIAL_CREDENTIAL_ENV", raising=False)

    generated = generate_derivatives(db, photo, media_job)

    assert len(generated) == 3
    assert photo.available is True
    assert folder.status == "released"
    assert media_job.status == "completed"
    assert db.scalar(select(func.count()).select_from(FacialJob)) == 0


def test_media_dispatches_clean_admin_preview_to_facial_index(
    tmp_path: Path, monkeypatch
) -> None:
    db = _session()
    from app.auth import MediaJob, ParentGallery

    parent_id, folder_id, photo_id = uuid4(), uuid4(), uuid4()
    folder = PhotoFolder(
        id=folder_id,
        parent_gallery_id=parent_id,
        name="Upload",
        status="preparing",
        purpose="content",
    )
    photo = PhotoAsset(
        id=photo_id,
        parent_gallery_id=parent_id,
        folder_id=folder_id,
        filename="foto.jpg",
        storage_key="event/foto.jpg",
        available=False,
    )
    media_job = MediaJob(photo_asset_id=photo_id, status="queued", attempts=0)
    db.add_all((ParentGallery(id=parent_id, name="Evento"), folder, photo, media_job))
    db.commit()
    source_root = tmp_path / "source"
    derivatives_root = tmp_path / "derivatives"
    source_path = source_root / photo.storage_key
    source_path.parent.mkdir(parents=True)
    Image.new("RGB", (320, 240), (80, 90, 100)).save(source_path, format="JPEG")
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    observed: dict[str, object] = {}

    def capture(_db, _photo, derivative, *, derivative_path):
        observed["variant"] = derivative.variant
        observed["path"] = derivative_path

    monkeypatch.setattr(
        "app.facial.indexing.enqueue_photo_index_if_eligible", capture
    )

    generate_derivatives(db, photo, media_job)

    admin_path = derivatives_root / str(photo_id) / "admin_preview.jpg"
    protected_path = derivatives_root / str(photo_id) / "client_preview.jpg"
    assert observed == {"variant": "admin_preview", "path": admin_path.resolve()}
    assert admin_path.read_bytes() != protected_path.read_bytes()
