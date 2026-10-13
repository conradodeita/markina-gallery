import asyncio
from datetime import timedelta
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import RawDevelopmentJob, RawDevelopmentSettings, now
from app.raw_development.probe import validate_raw_signature
from app.raw_development.state import (
    RAW_MAX_UPLOAD_BYTES,
    RAW_SUFFIXES,
    RawAdmission,
    RawDevelopmentStateError,
    receive_raw_upload,
    require_raw_upload,
    require_transition,
)

TENANT_ID = uuid4()


def test_raw_contract_accepts_supported_engine_formats_with_size_bounds():
    assert ".arw" in RAW_SUFFIXES
    assert ".nef" in RAW_SUFFIXES
    require_raw_upload("evento-01.ARW", RAW_MAX_UPLOAD_BYTES)
    require_raw_upload("evento-02.NEF", 1024, supported_suffixes={".nef"})

    for filename, size in (("foto.tiff", 1024), ("foto.arw", 0), ("foto.arw", RAW_MAX_UPLOAD_BYTES + 1)):
        with pytest.raises(RawDevelopmentStateError):
            require_raw_upload(filename, size)
    with pytest.raises(RawDevelopmentStateError):
        require_raw_upload("foto.nef", 1024, supported_suffixes={".arw"})


@pytest.mark.parametrize(
    ("filename", "header"),
    [
        ("foto.ARW", b"II*\x00" + b"\x00" * 12),
        ("foto.NEF", b"MM\x00*" + b"\x00" * 12),
        ("foto.RAF", b"FUJIFILMCCD-RAW " + b"\x00" * 4),
        ("foto.CR3", b"\x00\x00\x00\x18ftypcrx " + b"\x00" * 4),
        ("foto.ORF", b"IIRO" + b"\x00" * 8),
    ],
)
def test_raw_container_probe_accepts_signatures_for_multiple_camera_formats(filename, header):
    assert validate_raw_signature(filename, header, supported_suffixes=RAW_SUFFIXES)


def test_raw_container_probe_rejects_mime_or_extension_spoofing():
    with pytest.raises(RawDevelopmentStateError, match="Assinatura"):
        validate_raw_signature("foto.ARW", b"\xff\xd8\xff\xe0" + b"\x00" * 8, supported_suffixes=RAW_SUFFIXES)


def test_raw_upload_is_staged_atomically_and_fingerprinted(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE photo_asset (id CHAR(32), tenant_id CHAR(32), PRIMARY KEY (id), UNIQUE (id, tenant_id))")
    RawDevelopmentSettings.__table__.create(engine)
    RawDevelopmentJob.__table__.create(engine)
    monkeypatch.setenv("RAW_DEVELOPMENT_ROOT", str(tmp_path))
    monkeypatch.setenv("RAW_DEVELOPMENT_LIGHTCRAFT_VERSION", "0.6.0")
    monkeypatch.setenv("RAW_DEVELOPMENT_LIGHTCRAFT_FORMATS", ".arw")
    payload = b"II*\x00" + b"camera-raw-data"

    class Request:
        def __init__(self, content=payload, *, interrupted=False):
            self.content = content
            self.interrupted = interrupted
            self.headers = {"content-length": str(len(content))}

        async def stream(self):
            yield self.content[:6]
            if self.interrupted:
                raise OSError("simulated disconnect")
            yield self.content[6:]

    try:
        with Session(engine) as session:
            session.add(RawDevelopmentSettings(tenant_id=TENANT_ID, id=1, enabled=True, selected_engine="lightcraft"))
            session.commit()
            photo = SimpleNamespace(id=uuid4(), tenant_id=TENANT_ID, filename="event.ARW")
            result = asyncio.run(receive_raw_upload(session, photo, Request()))
            assert result == {"status": "queued"}
            job = session.get(RawDevelopmentJob, (photo.id, TENANT_ID))
            assert job.status == "queued"
            assert job.input_bytes == len(payload)
            assert job.input_fingerprint == sha256(payload).hexdigest()
            assert (tmp_path / job.staging_key).read_bytes() == payload
            monkeypatch.setattr("app.raw_development.state.RAW_MAX_FILES", 1)
            saturated_photo = SimpleNamespace(id=uuid4(), tenant_id=TENANT_ID, filename="another.ARW")
            with pytest.raises(RawDevelopmentStateError, match="[Ff]ila"):
                asyncio.run(receive_raw_upload(session, saturated_photo, Request()))
            monkeypatch.setattr("app.raw_development.state.RAW_MAX_FILES", 64)
            assert asyncio.run(receive_raw_upload(session, photo, Request())) == {"status": "queued"}

            invalid_photo = SimpleNamespace(id=uuid4(), tenant_id=TENANT_ID, filename="invalid.ARW")
            spoofed = b"\xff\xd8\xff\xe0" + b"not-a-raw-file"
            with pytest.raises(RawDevelopmentStateError, match="Assinatura"):
                asyncio.run(receive_raw_upload(session, invalid_photo, Request(spoofed)))
            failed = session.get(RawDevelopmentJob, (invalid_photo.id, TENANT_ID))
            assert failed.status == "failed"
            assert list(tmp_path.iterdir()) == [tmp_path / job.staging_key]

            assert asyncio.run(receive_raw_upload(session, invalid_photo, Request(payload))) == {"status": "queued"}
            reuploaded = session.get(RawDevelopmentJob, (invalid_photo.id, TENANT_ID))
            assert reuploaded.status == "queued"
            assert reuploaded.input_fingerprint == sha256(payload).hexdigest()

            interrupted_photo = SimpleNamespace(id=uuid4(), tenant_id=TENANT_ID, filename="interrupted.ARW")
            with pytest.raises(OSError, match="simulated disconnect"):
                asyncio.run(receive_raw_upload(session, interrupted_photo, Request(interrupted=True)))
            interrupted = session.get(RawDevelopmentJob, (interrupted_photo.id, TENANT_ID))
            assert interrupted.status == "failed"
            assert not (tmp_path / interrupted.staging_key).exists()

            from app.raw_development.worker import _cleanup_expired

            job.expires_at = now() - timedelta(minutes=1)
            session.commit()
            _cleanup_expired(session)
            assert job.status == "reupload_required"
            assert not (tmp_path / job.staging_key).exists()
    finally:
        RawDevelopmentJob.__table__.drop(engine)
        RawDevelopmentSettings.__table__.drop(engine)
        engine.dispose()


def test_raw_upload_reserves_full_quota_when_content_length_is_missing(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE photo_asset (id CHAR(32), tenant_id CHAR(32), PRIMARY KEY (id), UNIQUE (id, tenant_id))")
    RawDevelopmentSettings.__table__.create(engine)
    RawDevelopmentJob.__table__.create(engine)
    monkeypatch.setenv("RAW_DEVELOPMENT_ROOT", str(tmp_path))
    monkeypatch.setenv("RAW_DEVELOPMENT_LIGHTCRAFT_VERSION", "0.6.0")
    monkeypatch.setenv("RAW_DEVELOPMENT_LIGHTCRAFT_FORMATS", ".arw")
    monkeypatch.setattr("app.raw_development.state.RAW_MAX_TOTAL_BYTES", RAW_MAX_UPLOAD_BYTES * 1.5)
    payload = b"II*\x00camera-raw-data"

    class Request:
        def __init__(self, *, during_stream=None):
            self.headers = {}
            self.during_stream = during_stream

        async def stream(self):
            if self.during_stream:
                await self.during_stream()
            yield payload

    try:
        with Session(engine) as session:
            session.add(RawDevelopmentSettings(tenant_id=TENANT_ID, id=1, enabled=True, selected_engine="lightcraft"))
            session.commit()
            photo = SimpleNamespace(id=uuid4(), tenant_id=TENANT_ID, filename="first.ARW")
            second_photo = SimpleNamespace(id=uuid4(), tenant_id=TENANT_ID, filename="second.ARW")

            async def second_upload_is_rejected():
                with pytest.raises(RawDevelopmentStateError, match="[Ff]ila"):
                    await receive_raw_upload(session, second_photo, Request())

            assert asyncio.run(
                receive_raw_upload(session, photo, Request(during_stream=second_upload_is_rejected))
            ) == {"status": "queued"}
            job = session.get(RawDevelopmentJob, (photo.id, TENANT_ID))
            assert job.input_bytes == len(payload)
            tenant_two = uuid4()
            session.add(RawDevelopmentSettings(tenant_id=tenant_two, id=1, enabled=True, selected_engine="lightcraft"))
            session.commit()
            isolated_photo = SimpleNamespace(id=uuid4(), tenant_id=tenant_two, filename="isolated.ARW")
            assert asyncio.run(receive_raw_upload(session, isolated_photo, Request())) == {"status": "queued"}
    finally:
        RawDevelopmentJob.__table__.drop(engine)
        RawDevelopmentSettings.__table__.drop(engine)
        engine.dispose()


def test_raw_upload_accepts_files_above_47_mib(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE photo_asset (id CHAR(32), tenant_id CHAR(32), PRIMARY KEY (id), UNIQUE (id, tenant_id))")
    RawDevelopmentSettings.__table__.create(engine)
    RawDevelopmentJob.__table__.create(engine)
    monkeypatch.setenv("RAW_DEVELOPMENT_ROOT", str(tmp_path))
    monkeypatch.setenv("RAW_DEVELOPMENT_LIGHTCRAFT_VERSION", "0.6.0")
    monkeypatch.setenv("RAW_DEVELOPMENT_LIGHTCRAFT_FORMATS", ".arw")
    file_bytes = 48 * 1024 * 1024 + 12

    class Request:
        def __init__(self):
            self.headers = {"content-length": str(file_bytes)}

        async def stream(self):
            yield b"II*\x00" + b"\x00" * 8
            chunk = b"x" * (1024 * 1024)
            for _ in range(48):
                yield chunk

    try:
        with Session(engine) as session:
            session.add(RawDevelopmentSettings(tenant_id=TENANT_ID, id=1, enabled=True, selected_engine="lightcraft"))
            session.commit()
            photo = SimpleNamespace(id=uuid4(), tenant_id=TENANT_ID, filename="camera-large.ARW")
            assert asyncio.run(receive_raw_upload(session, photo, Request())) == {"status": "queued"}
            job = session.get(RawDevelopmentJob, (photo.id, TENANT_ID))
            assert job.input_bytes == file_bytes
            assert (tmp_path / job.staging_key).stat().st_size == file_bytes
    finally:
        RawDevelopmentJob.__table__.drop(engine)
        RawDevelopmentSettings.__table__.drop(engine)
        engine.dispose()


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("receiving", "queued"),
        ("receiving", "failed"),
        ("queued", "processing"),
        ("processing", "ready"),
        ("processing", "queued"),
        ("processing", "reupload_required"),
        ("ready", "queued"),
        ("failed", "queued"),
    ],
)
def test_raw_state_contract_accepts_only_documented_progress(current, target):
    require_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [("queued", "ready"), ("ready", "processing"), ("failed", "ready"), ("unknown", "queued")],
)
def test_raw_state_contract_rejects_skipped_or_unknown_transitions(current, target):
    with pytest.raises(RawDevelopmentStateError):
        require_transition(current, target)


def test_raw_admission_captures_engine_and_profile_versions():
    accepted = RawAdmission("lightcraft", "0.6.0", "auto-v1")
    assert (accepted.engine, accepted.engine_version, accepted.profile_version) == (
        "lightcraft",
        "0.6.0",
        "auto-v1",
    )
    with pytest.raises(RawDevelopmentStateError):
        RawAdmission("unknown", "0.6.0", "auto-v1")


def test_raw_settings_database_constraints_keep_singleton_and_known_engines():
    engine = create_engine("sqlite://")
    RawDevelopmentSettings.__table__.create(engine)
    try:
        with Session(engine) as session:
            session.add(RawDevelopmentSettings(tenant_id=TENANT_ID, id=1, selected_engine="lightcraft"))
            session.commit()
        with Session(engine) as session:
            session.add(RawDevelopmentSettings(tenant_id=TENANT_ID, id=2, selected_engine="lightcraft"))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
        with Session(engine) as session:
            session.add(RawDevelopmentSettings(tenant_id=TENANT_ID, id=1, selected_engine="custom"))
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        RawDevelopmentSettings.__table__.drop(engine)
        engine.dispose()


def test_raw_job_database_constraints_reject_invalid_status_and_empty_provenance():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE photo_asset (id CHAR(32), tenant_id CHAR(32), PRIMARY KEY (id), UNIQUE (id, tenant_id))")
    RawDevelopmentJob.__table__.create(engine)
    try:
        with Session(engine) as session:
            session.add(
                RawDevelopmentJob(
                    photo_asset_id=uuid4(),
                    tenant_id=TENANT_ID,
                    input_fingerprint="a" * 64,
                    input_bytes=1024,
                    source_format="arw",
                    staging_key="opaque-key",
                    engine="lightcraft",
                    engine_version="0.6.0",
                    profile_version="auto-v1",
                    status="ready",
                    expires_at=now(),
                )
            )
            session.commit()
        with Session(engine) as session:
            session.add(
                RawDevelopmentJob(
                    photo_asset_id=uuid4(),
                    tenant_id=TENANT_ID,
                    input_fingerprint="b" * 64,
                    input_bytes=1024,
                    source_format="nef",
                    staging_key="opaque-key-2",
                    engine="lightcraft",
                    engine_version="0.6.0",
                    profile_version="auto-v1",
                    status="published",
                    expires_at=now(),
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        RawDevelopmentJob.__table__.drop(engine)
        engine.dispose()
