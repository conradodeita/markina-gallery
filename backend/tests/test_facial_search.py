"""Disponibilidade, consentimento e criação da busca facial da cliente."""

from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import (
    AuditEvent,
    Base,
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    FacialJob,
    FacialSearchSnapshotItem,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
)
from app.facial.config import FacialSettings
from app.facial.search import (
    FacialSearchError,
    create_search_request,
    search_availability,
    search_request_payload,
)


def _jpeg() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (160, 120), (40, 50, 60)).save(stream, format="JPEG")
    return stream.getvalue()


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


def _fixture(tmp_path: Path, *, index_ready: bool):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    parent = ParentGallery(id=uuid4(), name="Evento")
    client = Client(id=uuid4(), full_name="Cliente", phone_e164="+5511999999998")
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
        index_generation=1,
    )
    db.add_all((parent, client, folder, photo, derivative, policy))
    if index_ready:
        db.add(
            FacialJob(
                kind="index",
                status="completed",
                idempotency_key=f"index:{photo.id}",
                parent_gallery_id=parent.id,
                photo_asset_id=photo.id,
                model_version="model-v1",
                quality_version="quality-v1",
                preview_fingerprint="a" * 64,
            )
        )
    db.commit()
    return db, parent, client


def test_availability_exposes_versions_and_real_index_progress(tmp_path: Path) -> None:
    db, parent, _client = _fixture(tmp_path, index_ready=False)
    settings = _settings(tmp_path)

    available = search_availability(
        db, parent_gallery_id=parent.id, settings=settings
    )
    unavailable = search_availability(
        db, parent_gallery_id=parent.id, settings=_settings(tmp_path, enabled=False)
    )

    assert available["state"] == "consent_required"
    assert available["index"] == {"state": "pending", "ready": 0, "total": 1}
    assert available["consent_version"] == "consent-v1"
    assert available["minor_search_available"] is False
    assert unavailable == {
        "state": "unavailable",
        "manual_selection_available": True,
        "minor_search_available": False,
    }


def test_adult_consent_creates_durable_request_without_private_gallery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    db, parent, client = _fixture(tmp_path, index_ready=True)
    item = create_search_request(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        consent_version="consent-v1",
        subject_declaration="adult",
        representation_reference=None,
        payload=_jpeg(),
        settings=_settings(tmp_path),
    )
    db.commit()

    assert item.status == "queued"
    assert (item.snapshot_ready, item.snapshot_total) == (1, 1)
    assert item.reference_locator_ciphertext is not None
    assert db.scalar(select(func.count()).select_from(FacialJob).where(FacialJob.kind == "search")) == 1
    snapshot = db.scalar(select(FacialSearchSnapshotItem))
    assert snapshot is not None
    assert snapshot.photo_asset_id is not None
    assert snapshot.status == "ready"
    assert snapshot.preview_fingerprint == "a" * 64
    assert db.scalar(select(func.count()).select_from(DerivedGallery)) == 0
    assert db.scalar(select(func.count()).select_from(DerivedGalleryMembership)) == 0
    payload = search_request_payload(item)
    assert set(payload) == {
        "id",
        "gallery_id",
        "status",
        "progress",
        "reference_deleted",
        "expires_at",
    }
    audit_subject = db.scalar(
        select(AuditEvent.subject).where(AuditEvent.event == "facial.search_consented")
    )
    assert "phone" not in audit_subject and "image" not in audit_subject


def test_stale_consent_and_minor_search_fail_before_persisting_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    db, parent, client = _fixture(tmp_path, index_ready=True)
    common = {
        "db": db,
        "parent_gallery_id": parent.id,
        "client_id": client.id,
        "representation_reference": None,
        "payload": _jpeg(),
        "settings": _settings(tmp_path),
    }
    with pytest.raises(FacialSearchError, match="revisto"):
        create_search_request(
            consent_version="old-consent",
            subject_declaration="adult",
            **common,
        )
    with pytest.raises(FacialSearchError, match="infantil"):
        create_search_request(
            consent_version="consent-v1",
            subject_declaration="minor",
            **common,
        )
    assert not (tmp_path / "references").exists()
