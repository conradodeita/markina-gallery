"""Progresso real e retentativa seletiva do índice facial."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    FacialJob,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFaceEmbedding,
    PhotoFolder,
    now,
)
from app.facial.status import (
    FacialStatusError,
    gallery_index_status,
    retry_failed_index_jobs,
)


def _fixture():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    parent = ParentGallery(id=uuid4(), name="Evento")
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
    photos = []
    for index in range(6):
        photo = PhotoAsset(
            id=uuid4(),
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename=f"foto-{index}.jpg",
            storage_key=f"{parent.id}/foto-{index}.jpg",
            available=True,
        )
        db.add_all(
            (
                photo,
                MediaDerivative(
                    photo_asset_id=photo.id,
                    variant="client_preview",
                    status="ready",
                    relative_path=f"{photo.id}/client_preview.jpg",
                ),
                MediaDerivative(
                    photo_asset_id=photo.id,
                    variant="admin_preview",
                    status="ready",
                    relative_path=f"{photo.id}/admin_preview.jpg",
                ),
            )
        )
        photos.append(photo)
    db.flush()
    instant = now()
    jobs = []
    for index, state in enumerate(("completed", "queued", "processing", "failed", "failed")):
        job = FacialJob(
            kind="index",
            status=state,
            idempotency_key=f"status-{index}",
            parent_gallery_id=parent.id,
            photo_asset_id=photos[index].id,
            model_version="model-v1",
            quality_version="quality-v1",
            preview_fingerprint=f"{index}" * 64,
            attempts=2 if state == "failed" else 1,
            last_error_category="provider_unavailable" if state == "failed" else None,
            available_at=instant,
            created_at=instant + timedelta(seconds=index),
            updated_at=instant + timedelta(seconds=index),
        )
        db.add(job)
        jobs.append(job)
    db.add_all(
        (
            PhotoFaceEmbedding(
                parent_gallery_id=parent.id,
                photo_asset_id=photos[0].id,
                face_ordinal=0,
                model_version="model-v1",
                quality_version="quality-v1",
                preview_fingerprint="0" * 64,
                quality_band="best",
                payload_ciphertext=b"cipher-1",
                payload_nonce=b"nonce-1",
                key_id="test",
            ),
            PhotoFaceEmbedding(
                parent_gallery_id=parent.id,
                photo_asset_id=photos[0].id,
                face_ordinal=1,
                model_version="model-v1",
                quality_version="quality-v1",
                preview_fingerprint="0" * 64,
                quality_band="other",
                payload_ciphertext=b"cipher-2",
                payload_nonce=b"nonce-2",
                key_id="test",
            ),
        )
    )
    db.commit()
    return db, parent, photos, jobs


def test_status_reports_real_latest_counts_and_paginated_sanitized_failures() -> None:
    db, parent, _photos, _jobs = _fixture()

    first = gallery_index_status(
        db,
        parent_gallery_id=parent.id,
        page=1,
        page_size=1,
        processing_enabled=True,
    )
    second = gallery_index_status(
        db,
        parent_gallery_id=parent.id,
        page=2,
        page_size=1,
        processing_enabled=True,
    )

    assert first.state == "processing"
    assert (first.ready, first.total, first.unindexed) == (1, 6, 1)
    assert (first.queued, first.processing, first.failed) == (1, 1, 2)
    assert (first.photos_with_faces, first.detected_faces) == (1, 2)
    assert first.failure_total == 2
    assert len(first.failures) == len(second.failures) == 1
    assert first.failures[0]["job_id"] != second.failures[0]["job_id"]
    assert set(first.failures[0]) == {
        "job_id",
        "photo_id",
        "attempts",
        "error_category",
    }


def test_retry_is_scoped_and_idempotent() -> None:
    db, parent, _photos, jobs = _fixture()
    failed_id = jobs[3].id

    assert retry_failed_index_jobs(
        db, parent_gallery_id=parent.id, job_ids={failed_id}
    ) == 1
    db.commit()
    assert jobs[3].status == "queued"
    assert jobs[3].attempts == 0 and jobs[3].last_error_category is None
    assert retry_failed_index_jobs(
        db, parent_gallery_id=parent.id, job_ids={failed_id}
    ) == 0
    with pytest.raises(FacialStatusError, match="não encontrado"):
        retry_failed_index_jobs(
            db, parent_gallery_id=uuid4(), job_ids={jobs[4].id}
        )


def test_stale_completed_version_does_not_count_as_ready() -> None:
    db, parent, photos, _jobs = _fixture()
    db.add(
        FacialJob(
            kind="index",
            status="completed",
            idempotency_key="stale-completed",
            parent_gallery_id=parent.id,
            photo_asset_id=photos[5].id,
            model_version="old-model",
            quality_version="quality-v1",
            preview_fingerprint="f" * 64,
            available_at=now(),
        )
    )
    db.commit()

    report = gallery_index_status(db, parent_gallery_id=parent.id)

    assert report.ready == 1
    assert report.unindexed == 1


def test_status_counts_uploaded_photos_across_folders_before_previews() -> None:
    db, parent, _photos, _jobs = _fixture()
    second_folder = PhotoFolder(
        id=uuid4(),
        parent_gallery_id=parent.id,
        name="Outra pasta",
        status="preparing",
        purpose="content",
        position=1,
    )
    waiting_photo = PhotoAsset(
        id=uuid4(),
        parent_gallery_id=parent.id,
        folder_id=second_folder.id,
        filename="aguardando.jpg",
        storage_key=f"{parent.id}/aguardando.jpg",
        available=False,
    )
    cover_folder = PhotoFolder(
        id=uuid4(),
        parent_gallery_id=parent.id,
        name="Capas",
        status="preparing",
        purpose="cover_assets",
        position=2,
    )
    cover_photo = PhotoAsset(
        id=uuid4(),
        parent_gallery_id=parent.id,
        folder_id=cover_folder.id,
        filename="capa.jpg",
        storage_key=f"covers/{parent.id}/capa.jpg",
        available=False,
    )
    db.add_all((second_folder, waiting_photo, cover_folder, cover_photo))
    db.commit()

    report = gallery_index_status(db, parent_gallery_id=parent.id)

    assert report.total == 7
    assert report.ready == 1
    assert report.waiting_previews == 1
    assert report.unindexed == 1


def test_enabled_environment_reports_processing_before_automatic_policy_exists() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    parent = ParentGallery(id=uuid4(), name="Evento novo")
    folder = PhotoFolder(
        id=uuid4(),
        parent_gallery_id=parent.id,
        name="Uploads",
        status="preparing",
        purpose="content",
    )
    photo = PhotoAsset(
        id=uuid4(),
        parent_gallery_id=parent.id,
        folder_id=folder.id,
        filename="recebida.jpg",
        storage_key=f"{parent.id}/recebida.jpg",
        available=False,
    )
    db.add_all((parent, folder, photo))
    db.commit()

    report = gallery_index_status(
        db,
        parent_gallery_id=parent.id,
        processing_enabled=True,
    )

    assert report.state == "processing"
    assert report.total == 1
    assert report.ready == 0
    assert report.waiting_previews == 1
    assert report.unindexed == 0


def test_status_exposes_only_completed_or_failed_terminal_states() -> None:
    db, parent, photos, jobs = _fixture()
    for job in jobs:
        job.status = "completed"
        job.last_error_category = None
    db.add(
        FacialJob(
            kind="index",
            status="completed",
            idempotency_key="completed-sixth",
            parent_gallery_id=parent.id,
            photo_asset_id=photos[5].id,
            model_version="model-v1",
            quality_version="quality-v1",
            preview_fingerprint="6" * 64,
            available_at=now(),
        )
    )
    db.commit()

    completed = gallery_index_status(
        db, parent_gallery_id=parent.id, processing_enabled=True
    )
    assert completed.state == "completed"

    jobs[4].status = "failed"
    jobs[4].last_error_category = "provider_unavailable"
    db.commit()
    failed = gallery_index_status(
        db, parent_gallery_id=parent.id, processing_enabled=True
    )
    assert failed.state == "failed"
