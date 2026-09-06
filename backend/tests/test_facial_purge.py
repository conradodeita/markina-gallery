"""Purge facial remove inferências sem apagar mídia ou histórico comercial."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    Client,
    FacialJob,
    FacialSearchCandidate,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFaceEmbedding,
    PhotoFolder,
    now,
)
from app.facial.jobs import FacialJobRepository
from app.facial.purge import (
    enqueue_gallery_purge,
    enqueue_photo_purge,
    facial_cleanup_proof,
    purge_gallery_records,
    purge_photo_records,
    reconcile_invalid_facial_records,
)
from app.facial.worker import process_claimed_purge_job


def _fixture(db: Session):
    parent = ParentGallery(id=uuid4(), name="Evento preservado")
    client = Client(id=uuid4(), full_name="Cliente sintética", phone_e164="+5511999999999")
    folder = PhotoFolder(
        id=uuid4(),
        parent_gallery_id=parent.id,
        name="Fotos",
        status="released",
        purpose="content",
    )
    photo = PhotoAsset(
        id=uuid4(),
        parent_gallery_id=parent.id,
        folder_id=folder.id,
        filename="foto.jpg",
        storage_key=f"{parent.id}/foto.jpg",
        available=True,
    )
    derivative = MediaDerivative(
        photo_asset_id=photo.id,
        variant="client_preview",
        status="ready",
        relative_path=f"{photo.id}/client_preview.jpg",
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
    )
    request = FacialSearchRequest(
        id=uuid4(),
        parent_gallery_id=parent.id,
        client_id=client.id,
        policy_id=policy.id,
        status="searching",
        consent_version="consent-v1",
        legal_notice_version="notice-v1",
        subject_declaration="adult",
        model_version="model-v1",
        quality_version="quality-v1",
        index_generation=0,
        snapshot_total=1,
        snapshot_ready=1,
        compare_total=1,
        compare_done=0,
        reference_locator_ciphertext=b"locator",
        reference_locator_nonce=b"nonce",
        reference_key_id="test",
        expires_at=now() + timedelta(minutes=15),
    )
    embedding = PhotoFaceEmbedding(
        parent_gallery_id=parent.id,
        photo_asset_id=photo.id,
        face_ordinal=0,
        model_version="model-v1",
        quality_version="quality-v1",
        preview_fingerprint="a" * 64,
        quality_band="best",
        payload_ciphertext=b"ciphertext",
        payload_nonce=b"nonce-value-1",
        key_id="test",
    )
    candidate = FacialSearchCandidate(
        search_request_id=request.id,
        parent_gallery_id=parent.id,
        client_id=client.id,
        photo_asset_id=photo.id,
        rank=1,
        quality_band="best",
        expires_at=now() + timedelta(hours=24),
    )
    job = FacialJob(
        kind="index",
        status="queued",
        idempotency_key=f"index:{photo.id}",
        parent_gallery_id=parent.id,
        photo_asset_id=photo.id,
        available_at=now(),
    )
    notification = FacialSearchNotificationOutbox(
        search_request_id=request.id,
        parent_gallery_id=parent.id,
        client_id=client.id,
        result_kind="ready",
        status="queued",
        idempotency_key=f"notification:{request.id}",
        payload_ciphertext=b"payload",
        payload_nonce=b"nonce-value-2",
        key_id="test",
        available_at=now(),
    )
    db.add_all(
        (
            parent,
            client,
            folder,
            photo,
            derivative,
            policy,
            request,
            embedding,
            candidate,
            job,
            notification,
        )
    )
    db.commit()
    return parent, photo, request, job, notification


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_photo_purge_is_prioritized_idempotent_and_preserves_media() -> None:
    db = _db()
    parent, photo, _request, job, _notification = _fixture(db)

    first = enqueue_photo_purge(
        db,
        parent_gallery_id=parent.id,
        photo_asset_id=photo.id,
        reason="photo-deleted",
    )
    second = enqueue_photo_purge(
        db,
        parent_gallery_id=parent.id,
        photo_asset_id=photo.id,
        reason="photo-deleted",
    )
    db.commit()
    assert first.id == second.id and first.priority == 0

    report = purge_photo_records(
        db, parent_gallery_id=parent.id, photo_asset_id=photo.id
    )
    repeated = purge_photo_records(
        db, parent_gallery_id=parent.id, photo_asset_id=photo.id
    )
    db.commit()

    assert (report.embeddings, report.candidates) == (1, 1)
    assert (repeated.embeddings, repeated.candidates) == (0, 0)
    assert db.get(PhotoAsset, photo.id) is not None
    assert db.scalar(
        select(func.count()).select_from(MediaDerivative).where(
            MediaDerivative.photo_asset_id == photo.id
        )
    ) == 1
    assert db.get(FacialJob, job.id).photo_asset_id is None


def test_gallery_purge_cancels_requests_notifications_and_keeps_origin(
    tmp_path,
) -> None:
    db = _db()
    parent, photo, request, _job, notification = _fixture(db)
    reference = tmp_path / f"{request.id}.reference"
    reference.write_bytes(b"encrypted-reference")
    purge = enqueue_gallery_purge(
        db, parent_gallery_id=parent.id, reason="policy-suspended"
    )
    db.commit()
    assert purge.priority == 0

    assert facial_cleanup_proof(db, parent_gallery_id=parent.id)["clean"] is False
    report = purge_gallery_records(
        db, parent_gallery_id=parent.id, reference_root=tmp_path
    )
    repeated = purge_gallery_records(
        db, parent_gallery_id=parent.id, reference_root=tmp_path
    )
    db.commit()

    assert report.embeddings == 1 and report.candidates == 1
    assert report.requests_cancelled == 1
    assert report.notifications_cancelled == 1
    assert repeated.embeddings == 0 and repeated.candidates == 0
    assert db.get(ParentGallery, parent.id) is not None
    assert db.get(PhotoAsset, photo.id) is not None
    request = db.get(FacialSearchRequest, request.id)
    assert request.status == "cancelled"
    assert request.reference_locator_ciphertext is None
    assert request.reference_deleted_at is not None
    assert not reference.exists()
    notification = db.get(FacialSearchNotificationOutbox, notification.id)
    assert notification.status == "cancelled"
    assert notification.payload_ciphertext == b""
    proof = facial_cleanup_proof(db, parent_gallery_id=parent.id)
    assert proof == {
        "clean": True,
        "embeddings": 0,
        "candidates": 0,
        "references": 0,
        "pending_notifications": 0,
    }


def test_claimed_purge_job_completes_without_cancelling_its_own_lease() -> None:
    db = _db()
    parent, photo, _request, _job, _notification = _fixture(db)
    repository = FacialJobRepository()
    purge = enqueue_photo_purge(
        db,
        parent_gallery_id=parent.id,
        photo_asset_id=photo.id,
        reason="worker-test",
        repository=repository,
    )
    db.commit()
    claim = repository.claim_next(db, lease_seconds=60)
    assert claim is not None and claim.id == purge.id

    completed = process_claimed_purge_job(db, claim, repository=repository)

    assert completed.status == "completed"
    assert completed.lease_token is None
    assert db.scalar(select(func.count()).select_from(PhotoFaceEmbedding)) == 0


def test_reconciler_removes_only_invalid_inference_records() -> None:
    db = _db()
    _parent, photo, _request, _job, _notification = _fixture(db)
    photo.available = False
    db.commit()

    report = reconcile_invalid_facial_records(db)
    repeated = reconcile_invalid_facial_records(db)
    db.commit()

    assert (report.embeddings, report.candidates) == (1, 1)
    assert (repeated.embeddings, repeated.candidates) == (0, 0)
    assert db.get(PhotoAsset, photo.id) is not None
