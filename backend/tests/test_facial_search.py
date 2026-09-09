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
    AdminUser,
    AuditEvent,
    Base,
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    FacialJob,
    FacialRollout,
    FacialSearchRequest,
    FacialSearchSnapshotItem,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFolder,
    now,
)
from app.facial.capacity import FacialSearchCapacityError, measure_search_queue
from app.facial.config import FacialSettings
from app.facial.representation import create_legal_representation
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
        max_reference_bytes=31_457_280,
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
    rollouts = tuple(
        FacialRollout(
            environment=environment,
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
        for environment in ("test", "staging")
    )
    db.add_all(
        (
            parent,
            client,
            registration,
            folder,
            photo,
            protected_derivative,
            derivative,
            policy,
            *rollouts,
        )
    )
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
        db, parent_gallery_id=parent.id, client_id=_client.id, settings=settings
    )
    unavailable = search_availability(
        db,
        parent_gallery_id=parent.id,
        client_id=_client.id,
        settings=_settings(tmp_path, enabled=False),
    )

    assert available["state"] == "consent_required"
    assert available["index"] == {"state": "processing", "ready": 0, "total": 1}
    assert available["consent_version"] == "consent-v1"
    assert available["max_reference_bytes"] == 31_457_280
    assert available["minor_search_available"] is False
    assert unavailable == {
        "state": "unavailable",
        "manual_selection_available": True,
        "minor_search_available": False,
        "max_reference_bytes": 31_457_280,
    }


def test_search_admission_requires_gallery_in_active_rollout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    db, parent, client = _fixture(tmp_path, index_ready=True)
    rollout = db.scalar(
        select(FacialRollout).where(
            FacialRollout.parent_gallery_id == parent.id,
            FacialRollout.environment == "test",
        )
    )
    assert rollout is not None
    rollout.status = "prepared"
    db.commit()

    assert search_availability(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        settings=_settings(tmp_path),
    )["state"] == "unavailable"
    with pytest.raises(FacialSearchError, match="indisponível"):
        create_search_request(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
            consent_version="consent-v1",
            subject_declaration="adult",
            representation_reference=None,
            payload=_jpeg(),
            settings=_settings(tmp_path),
        )
    assert not (tmp_path / "references").exists()
    assert db.scalar(select(func.count()).select_from(FacialSearchRequest)) == 0


def test_saturated_search_queue_refuses_before_storing_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    db, parent, client = _fixture(tmp_path, index_ready=True)
    settings = _settings(tmp_path)
    object.__setattr__(settings, "search_queue_max_depth", 1)
    object.__setattr__(settings, "search_queue_max_age_seconds", 30)
    object.__setattr__(settings, "search_retry_after_seconds", 17)
    db.add(
        FacialJob(
            kind="search",
            status="queued",
            idempotency_key="saturated-search-queue",
            parent_gallery_id=parent.id,
            search_request_id=uuid4(),
            available_at=datetime.now(UTC),
            created_at=datetime.now(UTC) - timedelta(seconds=45),
        )
    )
    db.commit()

    pressure = measure_search_queue(db)
    assert pressure.depth == 1
    assert pressure.oldest_age_seconds >= 30
    with pytest.raises(FacialSearchCapacityError) as refused:
        create_search_request(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
            consent_version="consent-v1",
            subject_declaration="adult",
            representation_reference=None,
            payload=_jpeg(),
            settings=settings,
        )

    assert refused.value.retry_after_seconds == 17
    assert not (tmp_path / "references").exists()
    assert db.scalar(select(func.count()).select_from(FacialSearchRequest)) == 0


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
        "poll_after_ms",
        "estimate",
    }
    assert payload["poll_after_ms"] == 2000
    assert payload["estimate"] == {
        "remaining_items": 1,
        "seconds": None,
        "confidence": "unavailable",
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


def test_latest_search_repeats_client_gallery_authorization_and_expiry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    db, parent, client = _fixture(tmp_path, index_ready=True)
    request = create_search_request(
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

    with pytest.raises(FacialSearchError, match="indisponível"):
        read_latest_search_result(
            db,
            parent_gallery_id=uuid4(),
            client_id=client.id,
        )
    with pytest.raises(FacialSearchError, match="indisponível"):
        read_latest_search_result(
            db,
            parent_gallery_id=parent.id,
            client_id=uuid4(),
        )

    registration = db.scalar(
        select(ParentGalleryRegistration).where(
            ParentGalleryRegistration.parent_gallery_id == parent.id,
            ParentGalleryRegistration.client_id == client.id,
        )
    )
    assert registration is not None
    registration.status = "unlinked"
    db.commit()
    with pytest.raises(FacialSearchError, match="indisponível"):
        read_latest_search_result(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
        )

    registration.status = "active"
    request.status = "queued"
    request.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    with pytest.raises(FacialSearchError, match="indisponível"):
        read_latest_search_result(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
        )


def test_latest_search_isolated_between_two_concurrent_galleries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    db, first_parent, client = _fixture(tmp_path, index_ready=True)
    second_parent = ParentGallery(id=uuid4(), name="Segundo evento")
    second_folder = PhotoFolder(
        id=uuid4(),
        parent_gallery_id=second_parent.id,
        name="Fotos",
        status="released",
        purpose="content",
    )
    second_photo = PhotoAsset(
        id=uuid4(),
        parent_gallery_id=second_parent.id,
        folder_id=second_folder.id,
        filename="segunda.jpg",
        storage_key=f"{second_parent.id}/segunda.jpg",
        available=True,
    )
    second_policy = GalleryFacialPolicy(
        id=uuid4(),
        parent_gallery_id=second_parent.id,
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
    db.add_all(
        (
            second_parent,
            second_folder,
            second_photo,
            MediaDerivative(
                photo_asset_id=second_photo.id,
                variant="client_preview",
                status="ready",
                relative_path=f"{second_photo.id}/client_preview.jpg",
            ),
            MediaDerivative(
                photo_asset_id=second_photo.id,
                variant="admin_preview",
                status="ready",
                relative_path=f"{second_photo.id}/admin_preview.jpg",
            ),
            second_policy,
            ParentGalleryRegistration(
                parent_gallery_id=second_parent.id,
                client_id=client.id,
                status="active",
            ),
            FacialRollout(
                environment="test",
                parent_gallery_id=second_parent.id,
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
            FacialJob(
                kind="index",
                status="completed",
                idempotency_key=f"index:{second_photo.id}",
                parent_gallery_id=second_parent.id,
                photo_asset_id=second_photo.id,
                model_version="model-v1",
                quality_version="quality-v1",
                preview_fingerprint="b" * 64,
            ),
        )
    )
    db.commit()

    first = create_search_request(
        db,
        parent_gallery_id=first_parent.id,
        client_id=client.id,
        consent_version="consent-v1",
        subject_declaration="adult",
        representation_reference=None,
        payload=_jpeg(),
        settings=_settings(tmp_path),
    )
    second = create_search_request(
        db,
        parent_gallery_id=second_parent.id,
        client_id=client.id,
        consent_version="consent-v1",
        subject_declaration="adult",
        representation_reference=None,
        payload=_jpeg(),
        settings=_settings(tmp_path),
    )
    db.commit()

    restored_first, _ = read_latest_search_result(
        db,
        parent_gallery_id=first_parent.id,
        client_id=client.id,
    )
    restored_second, _ = read_latest_search_result(
        db,
        parent_gallery_id=second_parent.id,
        client_id=client.id,
    )
    assert restored_first.id == first.id
    assert restored_second.id == second.id
    assert restored_first.id != restored_second.id


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
    with pytest.raises(FacialSearchError, match="representação legal"):
        create_search_request(
            consent_version="consent-v1",
            subject_declaration="minor",
            **common,
        )
    assert not (tmp_path / "references").exists()


def test_authorized_minor_reference_requires_guardian_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    db, parent, client = _fixture(tmp_path, index_ready=True)
    settings = _settings(tmp_path)

    unavailable_without_proof = search_availability(
        db, parent_gallery_id=parent.id, client_id=client.id, settings=settings
    )
    assert unavailable_without_proof["minor_search_available"] is False
    assert unavailable_without_proof["minor_representation_reference"] is None
    admin = AdminUser(
        id=uuid4(),
        email="minor-proof-admin@example.test",
        password_hash="unused",
        totp_secret="unused",
    )
    db.add(admin)
    db.flush()
    proof = create_legal_representation(
        db,
        client_id=client.id,
        parent_gallery_id=parent.id,
        subject_scope_reference="minor-subject-scope-opaque",
        authority_kind="parent",
        verification_method="admin_attestation",
        terms_version=settings.minor_policy_version,
        evidence_reference="minor-evidence-opaque",
        verified_by_admin_id=admin.id,
        expires_at=now() + timedelta(days=30),
    )
    db.commit()

    available = search_availability(
        db, parent_gallery_id=parent.id, client_id=client.id, settings=settings
    )
    assert available["minor_search_available"] is True
    assert available["minor_representation_reference"] == str(proof.id)

    with pytest.raises(FacialSearchError, match="representação legal"):
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
        representation_reference=str(proof.id),
        payload=_jpeg(),
        settings=settings,
    )
    db.commit()

    assert item.status == "queued"
    assert item.subject_declaration == "minor"
    assert item.representation_reference == str(proof.id)


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
