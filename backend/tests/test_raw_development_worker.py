from datetime import timedelta
from hashlib import sha256
from types import SimpleNamespace

import pytest
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import (
    Base,
    ParentGallery,
    PhotoAnalysis,
    PhotoAsset,
    PhotoFolder,
    RawDevelopmentJob,
    Tenant,
    now,
)
from app.media import safe_source_path
from app.raw_development.engines import normalize_rendered_jpeg
from app.raw_development.state import RAW_MAX_ATTEMPTS
from app.raw_development.worker import process_next_raw_job


def _worker_database(tmp_path, monkeypatch):
    tmp_path.mkdir(parents=True, exist_ok=True)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    monkeypatch.setenv("RAW_DEVELOPMENT_ROOT", str(tmp_path))
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "media-source"))
    return engine, factory


def _queued_job(factory, tmp_path, *, status="queued", attempts=0, updated_at=None, purpose="content"):
    source_bytes = b"II*\x00camera-raw-payload"
    with factory() as db:
        tenant = Tenant()
        db.add(tenant)
        db.flush()
        parent = ParentGallery(tenant_id=tenant.id, name="Evento RAW")
        db.add(parent)
        db.flush()
        folder = PhotoFolder(tenant_id=tenant.id, parent_gallery_id=parent.id, name="Pasta RAW", purpose=purpose)
        db.add(folder)
        db.flush()
        photo = PhotoAsset(
            tenant_id=tenant.id,
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="IMG_0001.ARW",
            storage_key="opaque-working-source.jpg",
            available=False,
        )
        db.add(photo)
        db.flush()
        job = RawDevelopmentJob(
            photo_asset_id=photo.id,
            tenant_id=tenant.id,
            input_fingerprint=sha256(source_bytes).hexdigest(),
            input_bytes=len(source_bytes),
            source_format="arw",
            staging_key="opaque-staged-source.arw",
            engine="lightcraft",
            engine_version="0.6.0",
            profile_version="auto-v1",
            status=status,
            attempts=attempts,
            expires_at=now() + timedelta(hours=1),
            updated_at=updated_at or now(),
        )
        db.add(job)
        db.commit()
        photo_id = photo.id
        tenant_id = tenant.id
    (tmp_path / "opaque-staged-source.arw").write_bytes(source_bytes)
    return photo_id, tenant_id, source_bytes


def test_worker_retries_conversion_failure_without_leaking_details_or_source(
    tmp_path, monkeypatch
):
    engine, factory = _worker_database(tmp_path, monkeypatch)
    try:
        photo_id, tenant_id, source_bytes = _queued_job(factory, tmp_path)

        class FailingEngine:
            def render(self, *_args, **_kwargs):
                raise RuntimeError("private /srv/secret path")

        monkeypatch.setattr("app.raw_development.worker.engine_for", lambda *_args, **_kwargs: FailingEngine())
        assert process_next_raw_job(factory)

        with factory() as db:
            job = db.get(RawDevelopmentJob, (photo_id, tenant_id))
            assert job.status == "queued"
            assert job.attempts == 1
            assert job.last_error == "render_failed"
            assert "secret" not in (job.last_error or "")
        assert (tmp_path / "opaque-staged-source.arw").read_bytes() == source_bytes
    finally:
        engine.dispose()


@pytest.mark.parametrize("with_facial_analysis", [False, True])
def test_worker_hands_clean_jpeg_to_derivative_pipeline_and_discards_raw(
    tmp_path, monkeypatch, with_facial_analysis
):
    engine, factory = _worker_database(tmp_path / "staging", monkeypatch)
    source_root = tmp_path / "media-source"
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("FACIAL_HIGHRES_ENABLED", str(with_facial_analysis).lower())
    try:
        photo_id, tenant_id, _ = _queued_job(factory, tmp_path / "staging")

        class SyntheticEngine:
            def render(self, _source, output, **_kwargs):
                stages.append("render")
                output.parent.mkdir(parents=True, exist_ok=True)
                exif = Image.Exif()
                exif[274] = 6
                Image.new("RGB", (160, 80), (80, 120, 160)).save(output, format="JPEG", exif=exif)

        written_payloads = []
        derivative_handoffs = []
        stages = []

        def write_source(path, payload, **_kwargs):
            stages.append("write_source")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            written_payloads.append(payload)

        def enqueue(_db, photo):
            stages.append("enqueue_derivatives")
            derivative_handoffs.append(photo.id)
            return SimpleNamespace(status="queued")

        def normalize(rendered, output):
            result = normalize_rendered_jpeg(rendered, output)
            stages.append("normalize")
            return result

        def admit(*_args, **_kwargs):
            stages.append("admit_source")
            if not with_facial_analysis:
                return None
            db, photo, payload = _args
            analysis = PhotoAnalysis(
                tenant_id=tenant_id,
                photo_asset_id=photo.id,
                source_fingerprint=sha256(payload).hexdigest(),
                source_bytes=len(payload),
                width=80,
                height=160,
                state="receiving",
                expires_at=now() + timedelta(hours=1),
            )
            db.add(analysis)
            db.flush()
            return analysis

        def finalize(db, photo):
            stages.append("finalize_source")
            db.get(PhotoAnalysis, photo.id).state = "pending"

        monkeypatch.setattr("app.raw_development.worker.engine_for", lambda *_args, **_kwargs: SyntheticEngine())
        monkeypatch.setattr("app.raw_development.worker.normalize_rendered_jpeg", normalize)
        monkeypatch.setattr("app.raw_development.worker.admit_source", admit)
        monkeypatch.setattr("app.raw_development.worker.finalize_source", finalize)
        monkeypatch.setattr("app.raw_development.worker.write_source", write_source)
        monkeypatch.setattr("app.raw_development.worker.enqueue_derivatives", enqueue)
        assert process_next_raw_job(factory)
        expected_stages = ["render", "normalize", "admit_source", "write_source"]
        if with_facial_analysis:
            expected_stages.append("finalize_source")
        expected_stages.append("enqueue_derivatives")
        assert stages == expected_stages

        with factory() as db:
            job = db.get(RawDevelopmentJob, (photo_id, tenant_id))
            photo = db.get(PhotoAsset, photo_id)
            assert job.status == "ready"
            assert (job.width, job.height) == (80, 160)
            working_source = safe_source_path(photo)
            analysis = db.get(PhotoAnalysis, photo_id)
            assert (analysis.state == "pending") if with_facial_analysis else analysis is None
        assert derivative_handoffs == [photo_id]
        assert len(written_payloads) == 1
        assert working_source.is_file()
        with Image.open(working_source) as image:
            assert image.size == (80, 160)
            assert not image.getexif()
        assert not (tmp_path / "staging" / "opaque-staged-source.arw").exists()
        assert not (tmp_path / "staging" / "opaque-staged-source.arw.rendered.jpg").exists()
        assert not (tmp_path / "staging" / "opaque-staged-source.arw.working.jpg").exists()
    finally:
        engine.dispose()


def test_worker_rejects_portrait_raw_cover_without_publishing_it(tmp_path, monkeypatch):
    engine, factory = _worker_database(tmp_path, monkeypatch)
    try:
        photo_id, tenant_id, _ = _queued_job(factory, tmp_path, purpose="cover_assets")

        class PortraitEngine:
            def render(self, _source, output, **_kwargs):
                Image.new("RGB", (80, 160), (80, 120, 160)).save(output, format="JPEG")

        monkeypatch.setattr("app.raw_development.worker.engine_for", lambda *_args, **_kwargs: PortraitEngine())
        monkeypatch.setattr(
            "app.raw_development.worker.admit_source",
            lambda *_args, **_kwargs: pytest.fail("capas não entram na análise facial"),
        )
        assert process_next_raw_job(factory)

        with factory() as db:
            job = db.get(RawDevelopmentJob, (photo_id, tenant_id))
            photo = db.get(PhotoAsset, photo_id)
            assert job.status == "queued"
            assert job.last_error == "render_failed"
            assert job.width is None and job.height is None
            assert photo.available is False
            assert db.get(PhotoAnalysis, photo_id) is None
        assert not safe_source_path(photo).exists()
    finally:
        engine.dispose()


def test_worker_activates_horizontal_raw_cover_after_successful_development(tmp_path, monkeypatch):
    engine, factory = _worker_database(tmp_path, monkeypatch)
    try:
        photo_id, tenant_id, _ = _queued_job(factory, tmp_path, purpose="cover_assets")

        class LandscapeEngine:
            def render(self, _source, output, **_kwargs):
                Image.new("RGB", (160, 80), (80, 120, 160)).save(output, format="JPEG")

        monkeypatch.setattr("app.raw_development.worker.engine_for", lambda *_args, **_kwargs: LandscapeEngine())
        monkeypatch.setattr("app.raw_development.worker.enqueue_derivatives", lambda *_args: SimpleNamespace(status="queued"))
        assert process_next_raw_job(factory)
        with factory() as db:
            gallery = db.scalar(select(ParentGallery).where(ParentGallery.tenant_id == tenant_id))
            job = db.get(RawDevelopmentJob, (photo_id, tenant_id))
            assert job.status == "ready"
            assert gallery.cover_photo_id == photo_id
    finally:
        engine.dispose()


def test_worker_restart_exhaustion_discards_source_and_requires_reupload(tmp_path, monkeypatch):
    engine, factory = _worker_database(tmp_path, monkeypatch)
    try:
        photo_id, tenant_id, _ = _queued_job(
            factory,
            tmp_path,
            status="processing",
            attempts=RAW_MAX_ATTEMPTS,
            updated_at=now() - timedelta(minutes=21),
        )
        assert not process_next_raw_job(factory)

        with factory() as db:
            job = db.get(RawDevelopmentJob, (photo_id, tenant_id))
            assert job.status == "reupload_required"
            assert job.last_error == "worker_interrupted"
        assert not (tmp_path / "opaque-staged-source.arw").exists()
    finally:
        engine.dispose()


def test_worker_discards_staging_when_owner_tenant_is_suspended(tmp_path, monkeypatch):
    engine, factory = _worker_database(tmp_path, monkeypatch)
    try:
        photo_id, tenant_id, _ = _queued_job(factory, tmp_path)
        with factory() as db:
            tenant = db.get(Tenant, tenant_id)
            tenant.status = "suspended"
            db.commit()
        assert process_next_raw_job(factory)
        with factory() as db:
            job = db.get(RawDevelopmentJob, (photo_id, tenant_id))
            assert job.status == "reupload_required"
            assert job.last_error == "tenant_inactive"
        assert not (tmp_path / "opaque-staged-source.arw").exists()
    finally:
        engine.dispose()
