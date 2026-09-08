"""Gates administrativos da política facial."""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import AdminUser, AuditEvent, Base, FacialJob, ParentGallery
from app.facial.config import FacialSettings
from app.facial.policy import (
    FacialPolicyDraft,
    FacialPolicyError,
    activate_policy,
    activation_inventory,
    ensure_automatic_policy,
    prepare_policy,
    revoke_policy,
    suspend_policy,
)
from app.main import app


def _settings(tmp_path: Path, *, enabled: bool) -> FacialSettings:
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


def _draft(**changes) -> FacialPolicyDraft:
    values = {
        "legal_notice_version": "notice-v1",
        "legal_basis_reference": "synthetic-only",
        "retention_policy_version": "retention-v1",
        "minor_policy_version": "minor-disabled-v1",
        "model_version": "model-v1",
        "quality_version": "quality-v1",
        "calibration_version": "calibration-v1",
        "similarity_threshold_milli": 750,
    }
    values.update(changes)
    return FacialPolicyDraft(**values)


def _fixture():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    parent = ParentGallery(id=uuid4(), name="Evento sintético")
    admin = AdminUser(
        id=uuid4(),
        email="admin@example.test",
        password_hash="not-used",
        totp_secret="not-used",
    )
    db.add_all((parent, admin))
    db.commit()
    return db, parent, admin


def test_policy_prepares_but_activation_fails_closed_until_global_gate(
    tmp_path: Path,
) -> None:
    db, parent, admin = _fixture()
    policy = prepare_policy(
        db,
        parent_gallery_id=parent.id,
        actor_admin_id=admin.id,
        draft=_draft(),
    )
    db.commit()
    assert policy.status == "pending"
    assert "kill_switch" in activation_inventory(policy, _settings(tmp_path, enabled=False))
    with pytest.raises(FacialPolicyError, match="kill_switch"):
        activate_policy(
            db,
            parent_gallery_id=parent.id,
            actor_admin_id=admin.id,
            settings=_settings(tmp_path, enabled=False),
        )

    activated = activate_policy(
        db,
        parent_gallery_id=parent.id,
        actor_admin_id=admin.id,
        settings=_settings(tmp_path, enabled=True),
    )
    db.commit()
    assert activated.status == "active" and activated.index_generation == 1
    assert activation_inventory(activated, _settings(tmp_path, enabled=True)) == []


def test_automatic_policy_is_created_once_without_admin_actor(tmp_path: Path) -> None:
    db, parent, _admin = _fixture()
    settings = _settings(tmp_path, enabled=True)

    first, first_changed = ensure_automatic_policy(
        db,
        parent_gallery_id=parent.id,
        settings=settings,
    )
    second, second_changed = ensure_automatic_policy(
        db,
        parent_gallery_id=parent.id,
        settings=settings,
    )
    db.commit()

    assert first.id == second.id
    assert first.status == "active"
    assert first.actor_admin_id is None
    assert first.index_generation == 1
    assert first_changed is True
    assert second_changed is False
    assert db.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(AuditEvent.event == "facial.policy_activated_automatically")
    ) == 1


def test_suspend_and_active_version_change_enqueue_idempotent_purge() -> None:
    db, parent, admin = _fixture()
    settings = _settings(Path("."), enabled=True)
    prepare_policy(
        db,
        parent_gallery_id=parent.id,
        actor_admin_id=admin.id,
        draft=_draft(),
    )
    activate_policy(
        db,
        parent_gallery_id=parent.id,
        actor_admin_id=admin.id,
        settings=settings,
    )
    db.commit()

    suspended = suspend_policy(
        db, parent_gallery_id=parent.id, actor_admin_id=admin.id
    )
    suspend_policy(db, parent_gallery_id=parent.id, actor_admin_id=admin.id)
    db.commit()
    assert suspended.status == "suspended"
    assert db.scalar(
        select(func.count()).select_from(FacialJob).where(FacialJob.kind == "purge")
    ) == 1

    activate_policy(
        db,
        parent_gallery_id=parent.id,
        actor_admin_id=admin.id,
        settings=settings,
    )
    prepare_policy(
        db,
        parent_gallery_id=parent.id,
        actor_admin_id=admin.id,
        draft=_draft(model_version="model-v2"),
    )
    db.commit()
    assert db.scalar(
        select(func.count()).select_from(FacialJob).where(FacialJob.kind == "purge")
    ) == 2
    subjects = list(db.scalars(select(AuditEvent.subject)))
    assert all("embedding" not in subject and "phone" not in subject for subject in subjects)


def test_facial_policy_admin_routes_reject_anonymous_access() -> None:
    client = TestClient(app)
    gallery_id = uuid4()
    assert client.get(
        f"/admin/parent-galleries/{gallery_id}/facial-policy"
    ).status_code == 403
    assert client.put(
        f"/admin/parent-galleries/{gallery_id}/facial-policy",
        json={
            "legal_notice_version": "notice-v1",
            "legal_basis_reference": "synthetic-only",
            "retention_policy_version": "retention-v1",
            "minor_policy_version": "minor-disabled-v1",
            "model_version": "model-v1",
            "quality_version": "quality-v1",
            "calibration_version": "calibration-v1",
            "similarity_threshold_milli": 750,
        },
    ).status_code == 403
    assert client.post(
        f"/admin/parent-galleries/{gallery_id}/facial-index/reprocess"
    ).status_code == 403


def test_revoke_is_idempotent_and_keeps_policy_disabled() -> None:
    db, parent, admin = _fixture()
    settings = _settings(Path("."), enabled=True)
    prepare_policy(
        db,
        parent_gallery_id=parent.id,
        actor_admin_id=admin.id,
        draft=_draft(),
    )
    activate_policy(
        db,
        parent_gallery_id=parent.id,
        actor_admin_id=admin.id,
        settings=settings,
    )
    db.commit()

    revoked = revoke_policy(
        db, parent_gallery_id=parent.id, actor_admin_id=admin.id
    )
    revoke_policy(db, parent_gallery_id=parent.id, actor_admin_id=admin.id)
    db.commit()

    assert revoked.status == "disabled"
    assert db.scalar(
        select(func.count()).select_from(FacialJob).where(FacialJob.kind == "purge")
    ) == 1
