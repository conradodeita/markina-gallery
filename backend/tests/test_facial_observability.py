"""Métricas faciais agregadas, SLOs e rejeição de payload sensível."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    Base,
    FacialJob,
    FacialSearchCandidate,
    FacialSearchRequest,
    ParentGallery,
    Role,
    SessionLocal,
    create_session,
    engine,
    password_hasher,
)
from app.facial.observability import (
    ALLOWED_DIMENSIONS,
    FACIAL_ADMISSION_COUNTER,
    FACIAL_SLO_LIMITS,
    FacialAdmissionSnapshot,
    FacialMetricSample,
    collect_facial_metrics,
    evaluate_facial_alerts,
    validate_observability_record,
)
from app.main import app


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def _metric(samples, name: str, metric_type: str, state: str):
    return next(
        sample
        for sample in samples
        if sample.name == name
        and sample.dimensions["type"] == metric_type
        and sample.dimensions["state"] == state
    )


def test_slo_limits_are_explicit_and_match_retention_contract() -> None:
    assert FACIAL_SLO_LIMITS.admission_availability_percent == 99.0
    assert FACIAL_SLO_LIMITS.search_p95_seconds == 120
    assert FACIAL_SLO_LIMITS.queue_oldest_seconds == 300
    assert FACIAL_SLO_LIMITS.terminal_failure_percent == 5.0
    assert FACIAL_SLO_LIMITS.reference_purge_seconds == 900
    assert FACIAL_SLO_LIMITS.candidate_purge_seconds == 86_400
    assert FACIAL_SLO_LIMITS.cpu_percent_by_class == {
        "search": 75,
        "index": 85,
        "maintenance": 75,
    }
    assert FACIAL_SLO_LIMITS.memory_mib_by_class == {
        "search": 460,
        "index": 690,
        "maintenance": 230,
    }


def test_collects_worker_admission_retention_and_runtime_metrics(db: Session) -> None:
    instant = datetime(2026, 9, 8, 15, 0, tzinfo=UTC)
    gallery_id = uuid4()
    db.add(ParentGallery(id=gallery_id, name="Evento sintético"))
    jobs = [
        FacialJob(
            kind="search",
            status="queued",
            idempotency_key="search-queued",
            parent_gallery_id=gallery_id,
            created_at=instant - timedelta(seconds=601),
            updated_at=instant - timedelta(seconds=601),
        ),
        FacialJob(
            kind="index",
            status="completed",
            idempotency_key="index-completed",
            parent_gallery_id=gallery_id,
            created_at=instant - timedelta(seconds=210),
            updated_at=instant,
        ),
        FacialJob(
            kind="index",
            status="failed",
            idempotency_key="index-failed",
            parent_gallery_id=gallery_id,
            created_at=instant - timedelta(seconds=90),
            updated_at=instant,
        ),
        FacialJob(
            kind="cleanup",
            status="failed",
            idempotency_key="maintenance-failed",
            parent_gallery_id=gallery_id,
            created_at=instant - timedelta(seconds=30),
            updated_at=instant,
        ),
    ]
    request = FacialSearchRequest(
        parent_gallery_id=gallery_id,
        client_id=uuid4(),
        policy_id=uuid4(),
        status="ready",
        consent_version="consent-v1",
        legal_notice_version="notice-v1",
        subject_declaration="adult",
        model_version="model-v1",
        quality_version="quality-v1",
        index_generation=1,
        reference_locator_ciphertext=b"ciphertext",
        reference_locator_nonce=b"nonce",
        reference_key_id="key-v1",
        created_at=instant - timedelta(seconds=130),
        completed_at=instant,
        expires_at=instant - timedelta(seconds=1),
    )
    db.add_all([*jobs, request])
    db.flush()
    db.add(
        FacialSearchCandidate(
            search_request_id=request.id,
            parent_gallery_id=gallery_id,
            client_id=request.client_id,
            photo_asset_id=uuid4(),
            rank=1,
            quality_band="best",
            expires_at=instant - timedelta(seconds=1),
        )
    )
    db.commit()

    samples = collect_facial_metrics(
        db,
        environment="test",
        enabled=True,
        admissions=FacialAdmissionSnapshot(accepted=99, refused=1),
        cpu_percent_by_class={"search": 80, "index": 70, "maintenance": 60},
        memory_mib_by_class={"search": 470, "index": 600, "maintenance": 200},
        instant=instant,
    )

    assert _metric(samples, "facial_runtime_enabled", "runtime", "enabled").value == 1
    assert _metric(
        samples, "facial_admission_availability_percent", "admission", "availability"
    ).value == 99
    assert _metric(samples, "facial_queue_oldest_seconds", "search", "pending").value == 601
    assert _metric(samples, "facial_terminal_failure_percent", "index", "terminal").value == 50
    assert _metric(samples, "facial_job_p95_seconds", "index", "terminal").value == 210
    assert _metric(samples, "facial_search_p95_seconds", "search", "terminal").value == 130
    assert _metric(
        samples, "facial_retention_overdue_total", "reference", "overdue"
    ).value == 1
    assert _metric(
        samples, "facial_retention_overdue_total", "candidate", "overdue"
    ).value == 1
    assert all(set(sample.dimensions) == ALLOWED_DIMENSIONS for sample in samples)

    alerts = evaluate_facial_alerts(samples, expected_enabled=True)
    alert_names_and_types = {(alert.name, alert.dimensions["type"]) for alert in alerts}
    assert ("facial_queue_oldest_seconds_alert", "search") in alert_names_and_types
    assert ("facial_terminal_failure_percent_alert", "index") in alert_names_and_types
    assert ("facial_search_p95_seconds_alert", "search") in alert_names_and_types
    assert ("facial_retention_overdue_alert", "reference") in alert_names_and_types
    assert ("facial_cpu_percent_alert", "search") in alert_names_and_types
    assert ("facial_memory_mib_alert", "search") in alert_names_and_types
    assert all(set(alert.dimensions) == ALLOWED_DIMENSIONS for alert in alerts)


def test_kill_switch_divergence_and_admission_slo_raise_alerts(db: Session) -> None:
    samples = collect_facial_metrics(
        db,
        environment="production",
        enabled=False,
        admissions=FacialAdmissionSnapshot(accepted=98, refused=2),
    )
    alerts = evaluate_facial_alerts(samples, expected_enabled=True)
    assert {alert.name for alert in alerts} >= {
        "facial_runtime_state_alert",
        "facial_admission_availability_alert",
    }


def test_process_counter_keeps_only_aggregate_admission_states() -> None:
    FACIAL_ADMISSION_COUNTER.reset()
    FACIAL_ADMISSION_COUNTER.record("accepted")
    FACIAL_ADMISSION_COUNTER.record("refused")
    assert FACIAL_ADMISSION_COUNTER.snapshot() == FacialAdmissionSnapshot(1, 1)
    with pytest.raises(ValueError, match="Estado"):
        FACIAL_ADMISSION_COUNTER.record("client_id:secret")
    FACIAL_ADMISSION_COUNTER.reset()


@pytest.mark.parametrize(
    "prohibited_name",
    [
        "facial_image_total",
        "facial_photo_total",
        "facial_embedding_total",
        "facial_vector_total",
        "facial_score_total",
        "facial_landmarks_total",
        "facial_bounding_box_total",
        "facial_inferred_name_total",
        "facial_phone_total",
    ],
)
def test_rejects_sensitive_or_biometric_metric_names(prohibited_name: str) -> None:
    with pytest.raises(ValueError, match="dado proibido"):
        validate_observability_record(
            FacialMetricSample(
                name=prohibited_name,
                value=1,
                dimensions={
                    "environment": "test",
                    "type": "search",
                    "state": "completed",
                },
            )
        )


def test_rejects_business_scope_dimension_and_non_numeric_payload() -> None:
    with pytest.raises(ValueError, match="não permitida"):
        validate_observability_record(
            FacialMetricSample(
                name="facial_jobs_total",
                value=1,
                dimensions={
                    "environment": "test",
                    "type": "search",
                    "state": "completed",
                    "gallery_id": str(uuid4()),
                },
            )
        )
    with pytest.raises(ValueError, match="numérico"):
        validate_observability_record(
            FacialMetricSample(
                name="facial_jobs_total",
                value=b"not-an-aggregate",  # type: ignore[arg-type]
                dimensions={
                    "environment": "test",
                    "type": "search",
                    "state": "completed",
                },
            )
        )


def test_admin_endpoint_is_authenticated_and_exports_only_aggregates() -> None:
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(connection)
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
    Base.metadata.create_all(engine)
    FACIAL_ADMISSION_COUNTER.reset()
    FACIAL_ADMISSION_COUNTER.record("accepted")
    with TestClient(app) as client:
        assert client.get("/admin/facial-observability").status_code == 403
        with SessionLocal() as session:
            admin = AdminUser(
                email="observability@markina.test",
                email_verified=True,
                password_hash=password_hasher.hash("Senha-observabilidade-2026"),
                totp_secret="JBSWY3DPEHPK3PXP",
            )
            session.add(admin)
            session.flush()
            cookie = create_session(session, Response(), Role.ADMIN, admin.id)
            session.commit()
        client.cookies.set("markina_session", cookie)
        response = client.get(
            "/admin/facial-observability", params={"expected_enabled": "false"}
        )
    FACIAL_ADMISSION_COUNTER.reset()

    assert response.status_code == 200
    payload = response.json()
    assert payload["alerts"] == []
    assert payload["metrics"]
    for record in payload["metrics"]:
        assert set(record) == {"name", "value", "dimensions"}
        assert set(record["dimensions"]) == ALLOWED_DIMENSIONS
        assert isinstance(record["value"], int | float)
    serialized = response.text.lower()
    assert "gallery_id" not in serialized
    assert "client_id" not in serialized
    assert "request_id" not in serialized
    assert "embedding" not in serialized
    assert "bounding_box" not in serialized
