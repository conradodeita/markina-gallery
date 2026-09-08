"""Disponibilidade, consentimento e criação da busca facial da cliente."""

from datetime import UTC, datetime, timedelta
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
    FacialSearchRequest,
    FacialSearchSnapshotItem,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFolder,
)
from app.facial.config import FacialSettings
from app.facial.search import (
    FacialSearchError,
    create_search_request,
    read_latest_search_result,
    search_availability,
    search_request_payload,
)


def _jpeg() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (160, 120), (40, 50, 60)).save(stream, format="JPEG")
    return stream.getvalue()


def _settings(
    tmp_path: Path, *, enabled: bool = True, minor_search_enabled: bool = False
) -> FacialSettings:
    return FacialSettings(
        enabled=enabled,
        environment="staging" if minor_search_enabled else "test",
        credential_environment="staging" if minor_search_enabled else "test",
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
        minor_search_enabled=minor_search_enabled,
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
        private_homologation_enabled=minor_search_enabled,
        homolog_batch_id="minor-client-test" if minor_search_enabled else "",
        homolog_origin_ref="event-origin-test" if minor_search_enabled else "",
        homolog_authorization_ref="approval-test" if minor_search_enabled else "",
        homolog_operator_ref="photographer-test" if minor_search_enabled else "",
        homolog_expected_count=500 if minor_search_enabled else 0,
        homolog_retention_hours=24 if minor_search_enabled else 0,
        homolog_contains_minors=minor_search_enabled,
        homolog_window_expires_at=(
            datetime.now(UTC) + timedelta(hours=1)
            if minor_search_enabled
            else None
        ),
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
    registration = ParentGalleryRegistration(
        parent_gallery_id=parent.id,
        client_id=client.id,
        status="active",
    )
    db.add_all((parent, client, registration, folder, photo, protected_derivative, derivative, policy))
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
    assert available["index"] == {"state": "processing", "ready": 0, "total": 1}
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
    restored, _candidates = read_latest_search_result(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
    )
    assert restored.id == item.id


def test_accepts_one_hundred_isolated_durable_client_searches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    db, parent, first_client = _fixture(tmp_path, index_ready=True)
    clients = [first_client]
    for index in range(1, 100):
        client = Client(
            id=uuid4(),
            full_name=f"Cliente {index}",
            phone_e164=f"+55119{index:08d}",
        )
        clients.append(client)
        db.add_all(
            (
                client,
                ParentGalleryRegistration(
                    parent_gallery_id=parent.id,
                    client_id=client.id,
                    status="active",
                ),
            )
        )
    db.commit()

    request_ids = {
        create_search_request(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
            consent_version="consent-v1",
            subject_declaration="adult",
            representation_reference=None,
            payload=_jpeg(),
            settings=_settings(tmp_path),
        ).id
        for client in clients
    }
    db.commit()

    assert len(request_ids) == 100
    assert db.scalar(select(func.count()).select_from(FacialSearchRequest)) == 100
    assert db.scalar(
        select(func.count()).select_from(FacialJob).where(FacialJob.kind == "search")
    ) == 100


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


def test_authorized_minor_reference_requires_guardian_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    db, parent, client = _fixture(tmp_path, index_ready=True)
    settings = _settings(tmp_path, minor_search_enabled=True)

    available = search_availability(
        db, parent_gallery_id=parent.id, settings=settings
    )
    assert available["minor_search_available"] is True

    with pytest.raises(FacialSearchError, match="responsável"):
        create_search_request(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
            consent_version="consent-v1",
            subject_declaration="minor",
            representation_reference=None,
            payload=_jpeg(),
            settings=settings,
        )

    item = create_search_request(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        consent_version="consent-v1",
        subject_declaration="minor",
        representation_reference="guardian-self-declaration-v1",
        payload=_jpeg(),
        settings=settings,
    )
    db.commit()

    assert item.status == "queued"
    assert item.subject_declaration == "minor"
    assert item.representation_reference == "guardian-self-declaration-v1"


def test_terminal_index_failure_is_excluded_without_blocking_client_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    db, parent, client = _fixture(tmp_path, index_ready=False)
    photo = db.scalar(select(PhotoAsset))
    assert photo is not None
    db.add(
        FacialJob(
            kind="index",
            status="failed",
            idempotency_key=f"failed-index:{photo.id}",
            parent_gallery_id=parent.id,
            photo_asset_id=photo.id,
            model_version="model-v1",
            quality_version="quality-v1",
            preview_fingerprint="f" * 64,
            last_error_category="provider_unavailable",
        )
    )
    db.commit()

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

    snapshot = db.scalar(
        select(FacialSearchSnapshotItem).where(
            FacialSearchSnapshotItem.search_request_id == item.id
        )
    )
    assert item.status == "queued"
    assert snapshot is not None and snapshot.status == "excluded"
