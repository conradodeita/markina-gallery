"""Transições e auditoria do rollout facial persistente."""
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    AuditEvent,
    Base,
    FacialCalibrationApproval,
    FacialRollout,
    ParentGallery,
    Tenant,
)
from app.facial.calibration import approve_calibration
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
from tests.tenant_fixtures import FIXTURE_TENANT_ID, fixture_admin


def _settings(
    *, enabled: bool = True, environment: str = "test", require_explicit_rollout: bool = False
) -> FacialSettings:
    return FacialSettings(
        enabled=enabled,
        require_explicit_rollout=require_explicit_rollout,
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
    if db.get(Tenant, FIXTURE_TENANT_ID) is None:
        db.add(Tenant(id=FIXTURE_TENANT_ID, status="active"))
        db.flush()
    gallery = ParentGallery(tenant_id=FIXTURE_TENANT_ID, id=uuid4(), name="Evento rollout")
    admin = fixture_admin(AdminUser(
        id=uuid4(),
        email="admin@example.test",
        password_hash="unused",
        totp_secret="unused",
    ))
    db.add_all((gallery, admin))
    db.commit()
    return db, gallery, admin


def test_explicit_restore_bypasses_only_calibration_without_inventing_approval() -> None:
    db, gallery, _admin = _fixture()
    strict = _settings(environment="production")
    assert not rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID,
                                 settings=strict, parent_gallery_id=gallery.id)
    restored = replace(strict, require_production_calibration=False)
    assert rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID,
                             settings=restored, parent_gallery_id=gallery.id)
    assert db.scalar(select(func.count(FacialCalibrationApproval.id))) == 0
    assert not rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID,
                                 settings=replace(restored, enabled=False), parent_gallery_id=gallery.id)
    assert not rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID,
                                 settings=restored, parent_gallery_id=uuid4())
    gallery.active = False
    assert not rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID,
                                 settings=restored, parent_gallery_id=gallery.id)
    db.close()


def test_explicit_rollout_is_still_required_when_calibration_is_waived() -> None:
    db, gallery, _admin = _fixture()
    settings = replace(_settings(environment="production"),
                       require_production_calibration=False, require_explicit_rollout=True)
    assert not rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID,
                                 settings=settings, parent_gallery_id=gallery.id)
    db.close()


def test_prepare_and_activate_require_matching_enabled_environment() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    rollout = prepare_rollout(
        db,
        tenant_id=FIXTURE_TENANT_ID, environment="test",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    db.commit()
    assert rollout.status == "prepared" and rollout.stage == "dark"
    assert rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id) is False

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
    assert rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id) is True


def test_missing_rollout_uses_general_availability_only_for_eligible_gallery() -> None:
    db, gallery, _admin = _fixture()

    assert rollout_is_active(
        db,
        tenant_id=FIXTURE_TENANT_ID, settings=_settings(),
        parent_gallery_id=gallery.id,
    ) is True
    assert rollout_is_active(
        db,
        tenant_id=FIXTURE_TENANT_ID, settings=_settings(enabled=False),
        parent_gallery_id=gallery.id,
    ) is False
    assert rollout_is_active(
        db,
        tenant_id=FIXTURE_TENANT_ID, settings=_settings(environment="production"),
        parent_gallery_id=gallery.id,
    ) is False

    gallery.active = False
    db.commit()
    assert rollout_is_active(
        db,
        tenant_id=FIXTURE_TENANT_ID, settings=_settings(),
        parent_gallery_id=gallery.id,
    ) is False


def _activate_test_rollout(db, gallery, admin, settings):
    prepare_rollout(
        db,
        tenant_id=FIXTURE_TENANT_ID,
        environment=settings.environment,
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    rollout = activate_rollout(
        db,
        environment=settings.environment,
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
        approval_reference="synthetic-explicit-rollout-approval",
        stage="canary",
        settings=settings,
    )
    db.commit()
    return rollout


def test_explicit_rollout_mode_refuses_legacy_fallback() -> None:
    db, gallery, _admin = _fixture()
    assert rollout_is_active(
        db, tenant_id=FIXTURE_TENANT_ID, settings=_settings(), parent_gallery_id=gallery.id
    ) is True
    assert rollout_is_active(
        db, tenant_id=FIXTURE_TENANT_ID,
        settings=_settings(require_explicit_rollout=True), parent_gallery_id=gallery.id,
    ) is False
    assert db.scalar(select(func.count()).select_from(FacialRollout)) == 0


def test_explicit_canary_does_not_admit_a_new_gallery_or_another_tenant() -> None:
    db, gallery, admin = _fixture()
    settings = _settings(require_explicit_rollout=True)
    _activate_test_rollout(db, gallery, admin, settings)
    created_later = ParentGallery(
        tenant_id=FIXTURE_TENANT_ID, name="Nova galeria depois do canary"
    )
    other_tenant = Tenant(status="active")
    db.add_all((created_later, other_tenant))
    db.commit()

    assert rollout_is_active(
        db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id
    ) is True
    assert rollout_is_active(
        db, tenant_id=FIXTURE_TENANT_ID, settings=settings,
        parent_gallery_id=created_later.id,
    ) is False
    assert rollout_is_active(
        db, tenant_id=other_tenant.id, settings=settings, parent_gallery_id=gallery.id
    ) is False
    assert db.scalar(select(func.count()).select_from(FacialRollout)) == 1


@pytest.mark.parametrize("version_field", [
    "model_version", "quality_version", "calibration_version", "legal_notice_version",
    "consent_version", "legal_basis_reference", "retention_policy_version",
])
def test_explicit_rollout_preserves_version_gates(version_field: str) -> None:
    db, gallery, admin = _fixture()
    settings = _settings(require_explicit_rollout=True)
    _activate_test_rollout(db, gallery, admin, settings)
    assert rollout_is_active(
        db, tenant_id=FIXTURE_TENANT_ID,
        settings=replace(settings, **{version_field: "different-version"}),
        parent_gallery_id=gallery.id,
    ) is False


def test_explicit_production_rollout_keeps_calibration_flag_and_environment_gates() -> None:
    db, gallery, admin = _fixture()
    settings = _settings(environment="production", require_explicit_rollout=True)
    prepare_rollout(
        db, tenant_id=FIXTURE_TENANT_ID, environment="production",
        parent_gallery_id=gallery.id, draft=draft_from_settings(settings),
    )
    with pytest.raises(FacialRolloutError, match="Calibração"):
        activate_rollout(
            db, environment="production", parent_gallery_id=gallery.id,
            actor_admin_id=admin.id, approval_reference="synthetic-no-calibration",
            stage="canary", settings=settings,
        )
    approval = approve_calibration(
        db, settings=settings, criteria_version="synthetic-criteria-v1",
        corpus_reference="synthetic-corpus-v1", approval_reference="synthetic-calibration-v1",
        relevant_group_count=1, approved_group_count=1, actor_admin_id=admin.id,
    )
    rollout = _activate_test_rollout(db, gallery, admin, settings)
    assert rollout_is_active(
        db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id
    ) is True
    assert rollout_is_active(
        db, tenant_id=FIXTURE_TENANT_ID, settings=replace(settings, enabled=False),
        parent_gallery_id=gallery.id,
    ) is False

    # Um registro do contexto anterior não vale como rollout da produção atual.
    rollout.environment = "staging"
    db.commit()
    assert rollout_is_active(
        db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id
    ) is False
    rollout.environment = "production"
    approval.status = "revoked"
    db.commit()
    assert rollout_is_active(
        db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id
    ) is False


def test_explicit_non_active_rollout_overrides_general_availability() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    rollout = prepare_rollout(
        db,
        tenant_id=FIXTURE_TENANT_ID, environment="test",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    assert rollout.status == "prepared"
    assert rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id) is False

    activate_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
        approval_reference="explicit-general-override",
        stage="general",
        settings=settings,
    )
    assert rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id) is True

    suspend_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
    )
    assert rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id) is False

    revoke_rollout(
        db,
        environment="test",
        parent_gallery_id=gallery.id,
        actor_admin_id=admin.id,
    )
    assert rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id) is False


def test_transitions_are_strict_and_revocation_is_idempotent() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    prepare_rollout(
        db,
        tenant_id=FIXTURE_TENANT_ID, environment="test",
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
    assert rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID, settings=settings, parent_gallery_id=gallery.id) is False
    assert db.scalar(select(func.count()).select_from(FacialRollout)) == 1


def test_prepare_reuses_single_scope_and_audit_is_minimized() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    first = prepare_rollout(
        db,
        tenant_id=FIXTURE_TENANT_ID, environment="test",
        parent_gallery_id=gallery.id,
        draft=draft_from_settings(settings),
    )
    second = prepare_rollout(
        db,
        tenant_id=FIXTURE_TENANT_ID, environment="test",
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
        tenant_id=FIXTURE_TENANT_ID, environment="test",
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
    assert rollout_is_active(db, tenant_id=FIXTURE_TENANT_ID, settings=drift, parent_gallery_id=gallery.id) is False
    assert rollout_is_active(
        db,
        tenant_id=FIXTURE_TENANT_ID, settings=_settings(environment="development"),
        parent_gallery_id=gallery.id,
    ) is False


def test_homologation_runtime_reads_canonical_homolog_rollout() -> None:
    db, gallery, admin = _fixture()
    runtime_settings = _settings(environment="homologation")
    prepare_rollout(
        db,
        tenant_id=FIXTURE_TENANT_ID, environment="homolog",
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
        tenant_id=FIXTURE_TENANT_ID, settings=runtime_settings,
        parent_gallery_id=gallery.id,
    ) is True


def test_admin_payload_exposes_only_operational_rollout_state() -> None:
    db, gallery, admin = _fixture()
    settings = _settings()
    rollout = prepare_rollout(
        db,
        tenant_id=FIXTURE_TENANT_ID, environment="test",
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
