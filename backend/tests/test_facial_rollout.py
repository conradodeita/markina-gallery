"""Transições e auditoria do rollout facial persistente."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import AdminUser, AuditEvent, Base, FacialRollout, ParentGallery
from app.facial.config import FacialSettings
from app.facial.rollout import (
    FacialRolloutError,
    activate_rollout,
    draft_from_settings,
    prepare_rollout,
    revoke_rollout,
    rollout_is_active,
    rollout_status_payload,
    suspend_rollout,
)


def _settings(*, enabled: bool = True, environment: str = "test") -> FacialSettings:
    return FacialSettings(
        enabled=enabled,
        environment=environment,
        credential_environment=environment,
        manifest_path=Path("manifest.json"),
        model_root=Path("models"),
        reference_root=Path("references"),
        model_version="model-v1",
        quality_version="quality-v1",
        calibration_version="calibration-v1",
        legal_notice_version="notice-v1",
        consent_version="consent-v1",
        legal_basis_reference="legal-basis-v1",
        retention_policy_version="retention-v1",
        minor_policy_version="minor-v1",
        similarity_threshold_milli=750,
        active_key_id="key-v1",
        aead_keys={"key-v1": b"k" * 32},
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


def _fixture() -> tuple[Session, ParentGallery, AdminUser]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    gallery = ParentGallery(id=uuid4(), name="Evento rollout")
    admin = AdminUser(
        id=uuid4(),
        email="admin@example.test",
        password_hash="unused",
        totp_secret="unused",
    )
    db.add_all((gallery, admin))
    db.commit()
    return db, gallery, admin


def test_prepare_and_activate_require_matching_enabled_environment() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    rollout = prepare_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    db.commit()
    assert rollout.status == "prepared" and rollout.stage == "dark"
    assert rollout_is_active(db, settings=settings, parent_gallery_id=gallery.id) is False

    with pytest.raises(FacialRolloutError, match="kill switch"):
        activate_rollout(
            db,
            environment="test",
            parent_gallery_id=gallery.id,
            actor_admin_id=admin.id,
            approval_reference="approval-rollout-1",
            stage="canary",
            settings=_settings(enabled=False),
        )
    activated = activate_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
        approval_reference="approval-rollout-1",
        stage="canary",
        settings=settings,
    )
    db.commit()
    assert activated.status == "active" and activated.stage == "canary"
    assert rollout_is_active(db, settings=settings, parent_gallery_id=gallery.id) is True


def test_missing_rollout_uses_general_availability_only_for_eligible_gallery() -> None:
    db, gallery, _admin = _fixture()

    assert rollout_is_active(
        db,
        settings=_settings(),
        parent_gallery_id=gallery.id,
    ) is True
    assert rollout_is_active(
        db,
        settings=_settings(enabled=False),
        parent_gallery_id=gallery.id,
    ) is False
    assert rollout_is_active(
        db,
        settings=_settings(environment="production"),
        parent_gallery_id=gallery.id,
    ) is False

    gallery.active = False
    db.commit()
    assert rollout_is_active(
        db,
        settings=_settings(),
        parent_gallery_id=gallery.id,
    ) is False


def test_explicit_non_active_rollout_overrides_general_availability() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    rollout = prepare_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    assert rollout.status == "prepared"
    assert rollout_is_active(db, settings=settings, parent_gallery_id=gallery.id) is False

    activate_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
        approval_reference="explicit-general-override",
        stage="general",
        settings=settings,
    )
    assert rollout_is_active(db, settings=settings, parent_gallery_id=gallery.id) is True

    suspend_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
    )
    assert rollout_is_active(db, settings=settings, parent_gallery_id=gallery.id) is False

    revoke_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
    )
    assert rollout_is_active(db, settings=settings, parent_gallery_id=gallery.id) is False


def test_transitions_are_strict_and_revocation_is_idempotent() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    prepare_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    with pytest.raises(FacialRolloutError, match="Somente rollout ativo"):
        suspend_rollout(
            db,
            environment="test",
            parent_gallery_id=gallery.id,
            actor_admin_id=admin.id,
        )
    activate_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
        approval_reference="approval-rollout-2",
        stage="limited",
        settings=settings,
    )
    first = suspend_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
    )
    second = suspend_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
    )
    assert first.id == second.id and second.status == "suspended"
    revoke_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
    )
    revoke_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
    )
    db.commit()
    assert rollout_is_active(db, settings=settings, parent_gallery_id=gallery.id) is False
    assert db.scalar(select(func.count()).select_from(FacialRollout)) == 1


def test_prepare_reuses_single_scope_and_audit_is_minimized() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    first = prepare_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    second = prepare_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    activate_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
        approval_reference="opaque-approval-reference",
        stage="canary",
        settings=settings,
    )
    db.commit()
    assert first.id == second.id
    assert db.scalar(select(func.count()).select_from(FacialRollout)) == 1
    audit = " ".join(db.scalars(select(AuditEvent.subject)))
    assert "opaque-approval-reference" not in audit
    for forbidden in ("embedding", "score", "phone", "image", "secret"):
        assert forbidden not in audit.lower()


def test_active_rollout_fails_closed_for_version_or_environment_drift() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    prepare_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    activate_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
        approval_reference="approval-rollout-3",
        stage="general",
        settings=settings,
    )
    db.commit()
    drift = _settings()
    object.__setattr__(drift, "model_version", "model-v2")
    assert rollout_is_active(db, settings=drift, parent_gallery_id=gallery.id) is False
    assert rollout_is_active(
        db,
        settings=_settings(environment="development"),
        parent_gallery_id=gallery.id,
    ) is False


def test_homologation_runtime_reads_canonical_homolog_rollout() -> None:
    db, gallery, admin = _fixture()
    runtime_settings = _settings(environment="homologation")
    prepare_rollout(
        db,
        environment="homolog",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(runtime_settings),
    )
    activate_rollout(
        db,
        environment="homolog",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
        approval_reference="approval-homolog-alias",
        stage="canary",
        settings=runtime_settings,
    )
    db.commit()

    assert rollout_is_active(
        db,
        settings=runtime_settings,
        parent_gallery_id=gallery.id,
    ) is True


def test_admin_payload_exposes_only_operational_rollout_state() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    rollout = prepare_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    activate_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
        approval_reference="opaque-admin-payload",
        stage="canary",
        settings=settings,
    )

    assert rollout_status_payload(rollout, available=True) == {
        "status": "active",
        "stage": "canary",
        "available": True,
    }
    assert rollout_status_payload(None, available=False) == {
        "status": "unavailable",
        "stage": None,
        "available": False,
    }
    assert rollout_status_payload(None, available=True) == {
        "status": "active",
        "stage": "general",
        "available": True,
    }
