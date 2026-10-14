"""Revisão executável dos controles de abuso e minimização facial."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth import AuditEvent, Base
from app.facial.security import enforce_facial_search_rate_limit


def test_facial_rate_limit_is_scoped_and_never_audits_raw_identity_or_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "facial-rate-limit-test-salt")
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "2")
    monkeypatch.setenv("AUTH_RATE_LIMIT_WINDOW_MINUTES", "15")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    client_id = uuid4()
    gallery_id = uuid4()
    ip_address = "203.0.113.47"

    with Session(engine) as db:
        enforce_facial_search_rate_limit(
            db,
            client_id=client_id,
            parent_gallery_id=gallery_id,
            ip_address=ip_address,
        )
        enforce_facial_search_rate_limit(
            db,
            client_id=client_id,
            parent_gallery_id=gallery_id,
            ip_address=ip_address,
        )
        with pytest.raises(HTTPException) as captured:
            enforce_facial_search_rate_limit(
                db,
                client_id=client_id,
                parent_gallery_id=gallery_id,
                ip_address=ip_address,
            )
        assert captured.value.status_code == 429
        audit_subjects = list(db.scalars(select(AuditEvent.subject)))

    assert len(audit_subjects) == 3
    serialized = " ".join(audit_subjects)
    assert str(client_id) not in serialized
    assert str(gallery_id) not in serialized
    assert ip_address not in serialized
    assert all(subject.startswith("facial_search_admission:") for subject in audit_subjects)


def test_rate_limit_does_not_mix_distinct_client_gallery_scopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "facial-rate-limit-test-salt")
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "1")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    gallery_id = uuid4()
    with Session(engine) as db:
        for client_id in (uuid4(), uuid4()):
            enforce_facial_search_rate_limit(
                db,
                client_id=client_id,
                parent_gallery_id=gallery_id,
                ip_address="203.0.113.47",
            )

        assert len(list(db.scalars(select(AuditEvent.id)))) == 2
