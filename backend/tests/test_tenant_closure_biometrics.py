"""Limpeza facial no encerramento preserva apenas prova mínima e isolamento."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    FacialJob,
    FacialSearchCandidate,
    FacialSearchConsentProof,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    FacialSearchSnapshotItem,
    GalleryFacialPolicy,
    ParentGallery,
    PhotoFaceEmbedding,
    Tenant,
    TenantClosureRequest,
    now,
)
from app.facial import closure_cleanup
from app.facial.jobs import FacialJobError, FacialJobRepository
from app.tenant_closure import finalize_closure, request_closure
from tests.test_media_archive_scheduler import _engine_with_schema
from tests.test_photographer_credits import create_photo
from tests.test_tenant_closure import prepare


@pytest.fixture
def context():
    engine = _engine_with_schema()
    try:
        with Session(engine, expire_on_commit=False) as db:
            session, payload, tenant = prepare(db)
            request_closure(db, session, payload)
            db.commit()
            yield db, tenant
    finally:
        engine.dispose()


def _add_facial_records(db, tenant_id, *, prefix, reference_root):
    photo = create_photo(db, tenant_id)
    client = Client(
        tenant_id=tenant_id,
        full_name=f"Cliente {prefix}",
        phone_e164="+5511999990001",
    )
    policy = GalleryFacialPolicy(
        tenant_id=tenant_id,
        parent_gallery_id=photo.parent_gallery_id,
        status="active",
        index_generation=7,
        model_version="synthetic-model-v1",
        quality_version="synthetic-quality-v1",
        legal_notice_version="synthetic-notice-v1",
    )
    db.add_all([client, policy])
    db.flush()

    request = FacialSearchRequest(
        tenant_id=tenant_id,
        parent_gallery_id=photo.parent_gallery_id,
        client_id=client.id,
        policy_id=policy.id,
        status="ready",
        reference_source="upload",
        authorization_method="explicit_consent",
        consent_version="synthetic-consent-v1",
        legal_notice_version="synthetic-notice-v1",
        subject_declaration="conditional",
        model_version="synthetic-model-v1",
        quality_version="synthetic-quality-v1",
        index_generation=7,
        reference_locator_ciphertext=b"encrypted-locator",
        reference_locator_nonce=b"synthetic-nonce",
        reference_key_id="synthetic-key",
        expires_at=now() + timedelta(days=1),
    )
    db.add(request)
    db.flush()
    db.add_all(
        [
            FacialSearchSnapshotItem(
                tenant_id=tenant_id,
                search_request_id=request.id,
                parent_gallery_id=photo.parent_gallery_id,
                client_id=client.id,
                photo_asset_id=photo.id,
                preview_fingerprint="a" * 64,
            ),
            FacialSearchCandidate(
                tenant_id=tenant_id,
                search_request_id=request.id,
                parent_gallery_id=photo.parent_gallery_id,
                client_id=client.id,
                photo_asset_id=photo.id,
                rank=1,
                quality_band="best",
                expires_at=now() + timedelta(days=1),
            ),
            PhotoFaceEmbedding(
                tenant_id=tenant_id,
                parent_gallery_id=photo.parent_gallery_id,
                photo_asset_id=photo.id,
                face_ordinal=0,
                model_version="synthetic-model-v1",
                quality_version="synthetic-quality-v1",
                preview_fingerprint="b" * 64,
                payload_ciphertext=b"encrypted-embedding",
                payload_nonce=b"synthetic-embedding-nonce",
                key_id="synthetic-key",
            ),
            FacialJob(
                tenant_id=tenant_id,
                kind="search",
                status="queued",
                idempotency_key=f"{prefix}-search-job",
                parent_gallery_id=photo.parent_gallery_id,
                search_request_id=request.id,
            ),
            FacialSearchNotificationOutbox(
                tenant_id=tenant_id,
                search_request_id=request.id,
                parent_gallery_id=photo.parent_gallery_id,
                client_id=client.id,
                result_kind="ready",
                status="queued",
                idempotency_key=f"{prefix}-notification",
                payload_ciphertext=b"encrypted-notification",
                payload_nonce=b"synthetic-notification-nonce",
                key_id="synthetic-key",
            ),
        ]
    )
    reference_root.mkdir(parents=True, exist_ok=True)
    (reference_root / f"{request.id}.reference").write_bytes(b"encrypted-reference")
    (reference_root / f"{request.id}.part").write_bytes(b"partial-encrypted-reference")
    return photo, client, policy, request


def _count(db, model, tenant_id):
    return db.scalar(
        select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
    )


def test_cleanup_is_tenant_scoped_idempotent_and_retries_file_failure(
    context, tmp_path, monkeypatch
):
    db, tenant = context
    closure = db.scalar(
        select(TenantClosureRequest).where(TenantClosureRequest.tenant_id == tenant.id)
    )
    other_tenant = Tenant()
    db.add(other_tenant)
    db.flush()
    reference_root = tmp_path / "references"
    _photo_a, _client_a, policy_a, request_a = _add_facial_records(
        db, tenant.id, prefix="tenant-a", reference_root=reference_root
    )
    _photo_b, _client_b, policy_b, request_b = _add_facial_records(
        db, other_tenant.id, prefix="tenant-b", reference_root=reference_root
    )
    db.commit()

    assert not closure_cleanup.cleanup_tenant_biometrics(
        db,
        tenant_id=tenant.id,
        closure=closure,
        reference_root=reference_root,
    )
    db.commit()

    original_delete = closure_cleanup.delete_reference_file

    def fail_a(root, request_id):
        if request_id == request_a.id:
            raise closure_cleanup.FacialReferenceError("synthetic unlink failure")
        return original_delete(root, request_id)

    monkeypatch.setattr(closure_cleanup, "delete_reference_file", fail_a)
    assert not closure_cleanup.cleanup_tenant_biometrics(
        db,
        tenant_id=tenant.id,
        closure=closure,
        reference_root=reference_root,
    )
    db.commit()

    assert closure.biometric_cleanup_started_at is not None
    assert closure.biometric_cleanup_completed_at is None
    assert policy_a.status == "disabled" and policy_a.index_generation == 8
    assert policy_b.status == "active" and policy_b.index_generation == 7
    assert _count(db, FacialSearchRequest, tenant.id) == 1
    assert _count(db, FacialSearchConsentProof, tenant.id) == 0

    monkeypatch.setattr(closure_cleanup, "delete_reference_file", original_delete)
    assert closure_cleanup.cleanup_tenant_biometrics(
        db,
        tenant_id=tenant.id,
        closure=closure,
        reference_root=reference_root,
    )
    db.commit()

    assert closure.biometric_cleanup_completed_at is not None
    assert _count(db, FacialSearchRequest, tenant.id) == 0
    assert _count(db, FacialSearchSnapshotItem, tenant.id) == 0
    assert _count(db, FacialSearchCandidate, tenant.id) == 0
    assert _count(db, FacialJob, tenant.id) == 0
    assert _count(db, FacialSearchNotificationOutbox, tenant.id) == 0
    assert _count(db, PhotoFaceEmbedding, tenant.id) == 0
    proof = db.scalar(
        select(FacialSearchConsentProof).where(
            FacialSearchConsentProof.tenant_id == tenant.id,
            FacialSearchConsentProof.source_search_request_id == request_a.id,
        )
    )
    assert proof is not None
    assert proof.consent_version == "synthetic-consent-v1"
    assert proof.authorization_method == "explicit_consent"
    assert not hasattr(proof, "reference_locator_ciphertext")
    assert not (reference_root / f"{request_a.id}.reference").exists()
    assert not (reference_root / f"{request_a.id}.part").exists()

    assert _count(db, FacialSearchRequest, other_tenant.id) == 1
    assert _count(db, FacialSearchSnapshotItem, other_tenant.id) == 1
    assert _count(db, FacialSearchCandidate, other_tenant.id) == 1
    assert _count(db, FacialJob, other_tenant.id) == 1
    assert _count(db, FacialSearchNotificationOutbox, other_tenant.id) == 1
    assert _count(db, PhotoFaceEmbedding, other_tenant.id) == 1
    assert db.get(FacialSearchRequest, request_b.id) is not None
    assert (reference_root / f"{request_b.id}.reference").exists()
    assert (reference_root / f"{request_b.id}.part").exists()


def test_finalize_waits_for_active_lease_and_blocks_new_facial_work(
    context, tmp_path, monkeypatch,
):
    from app.system_monitor.models import PlatformOwner
    from app.tenant_closure_recovery import reopen_account

    db, tenant = context

    gallery = ParentGallery(tenant_id=tenant.id, name="Galeria sintética")
    db.add(gallery)
    db.flush()
    policy = GalleryFacialPolicy(
        tenant_id=tenant.id,
        parent_gallery_id=gallery.id,
        status="active",
        index_generation=3,
        model_version="synthetic-model-v1",
        quality_version="synthetic-quality-v1",
    )
    db.add(policy)
    db.flush()
    client = Client(
        tenant_id=tenant.id,
        full_name="Cliente sintético de reabertura",
        phone_e164="+5511999990009",
    )
    db.add(client)
    db.flush()
    request = FacialSearchRequest(
        tenant_id=tenant.id,
        parent_gallery_id=gallery.id,
        client_id=client.id,
        policy_id=policy.id,
        status="ready",
        reference_source="upload",
        authorization_method="explicit_consent",
        consent_version="synthetic-consent-v1",
        legal_notice_version="synthetic-notice-v1",
        subject_declaration="conditional",
        model_version="synthetic-model-v1",
        quality_version="synthetic-quality-v1",
        index_generation=3,
        expires_at=now() + timedelta(days=1),
    )
    db.add(request)
    db.flush()
    reference_root = tmp_path / "facial-references"
    reference_root.mkdir()
    (reference_root / f"{request.id}.reference").write_bytes(b"synthetic-encrypted-reference")
    (reference_root / f"{request.id}.part").write_bytes(b"synthetic-partial-reference")
    monkeypatch.setenv("FACIAL_REFERENCE_ROOT", str(reference_root))
    active = FacialJob(
        tenant_id=tenant.id,
        kind="cleanup",
        status="processing",
        idempotency_key="active-face-job",
        parent_gallery_id=gallery.id,
        lease_token="active-synthetic-lease",
        lease_expires_at=now() + timedelta(minutes=5),
    )
    queued = FacialJob(
        tenant_id=tenant.id,
        kind="cleanup",
        status="queued",
        idempotency_key="queued-face-job",
        parent_gallery_id=gallery.id,
    )
    db.add_all([active, queued])
    db.commit()

    first = finalize_closure(db, tenant.id)
    db.commit()
    closure = db.scalar(
        select(TenantClosureRequest).where(TenantClosureRequest.tenant_id == tenant.id)
    )
    assert first["ready"] is False
    assert first["blockers"] == ["biometric_cleanup_pending"]
    assert tenant.lifecycle == "closing"
    assert closure.biometric_cleanup_started_at is not None
    assert closure.biometric_cleanup_completed_at is None
    assert policy.status == "disabled" and policy.index_generation == 4
    assert active.status == "processing"
    assert queued.status == "queued"
    assert FacialJobRepository().claim_next(db, lease_seconds=30) is None
    with pytest.raises(FacialJobError, match="encerramento"):
        FacialJobRepository().enqueue(
            db,
            tenant_id=tenant.id,
            kind="cleanup",
            idempotency_key="post-marker-job",
            parent_gallery_id=gallery.id,
        )
    db.rollback()

    second = finalize_closure(db, tenant.id)
    db.commit()
    db.refresh(queued)
    assert second["ready"] is False
    assert queued.status == "cancelled"

    active.status = "completed"
    active.lease_token = None
    active.lease_expires_at = None
    db.commit()
    assert finalize_closure(db, tenant.id)["ready"] is True
    db.commit()
    db.refresh(tenant)
    db.refresh(closure)
    assert tenant.lifecycle == "closed"
    assert closure.biometric_cleanup_completed_at is not None
    assert _count(db, FacialJob, tenant.id) == 0
    assert _count(db, FacialSearchRequest, tenant.id) == 0
    assert _count(db, FacialSearchConsentProof, tenant.id) == 1
    assert not (reference_root / f"{request.id}.reference").exists()
    assert not (reference_root / f"{request.id}.part").exists()

    owner_id = db.scalar(select(PlatformOwner.admin_user_id))
    reopened = reopen_account(
        db,
        owner_id=owner_id,
        tenant_id=tenant.id,
        request_id=uuid4(),
    )
    db.commit()
    assert reopened["lifecycle"] == "open"
    assert tenant.lifecycle == "open"
    assert _count(db, FacialSearchRequest, tenant.id) == 0
    assert _count(db, FacialSearchConsentProof, tenant.id) == 1
