"""Contratos high-res com JPEGs sintéticos, sem alegação de precisão biométrica."""

from dataclasses import replace
from datetime import timedelta
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from test_facial_engine import _face, _gallery, _settings, _vector

from app.auth import Base, FacialJob, PhotoAnalysis, PhotoFaceEmbedding, now
from app.facial.crypto import FacialCipher
from app.facial.detection import (
    Detection,
    DetectionConfig,
    deduplicate,
    difficulty,
    normalized_box,
    restore,
    tiles,
)
from app.facial.engine import FacialEngineError, replace_photo_index, search_gallery_index
from app.facial.lifecycle import (
    SourceCapacityError,
    admit_source,
    cleanup_source,
    finalize_source,
    media_can_proceed,
)
from app.media import generate_derivatives, safe_source_path


@pytest.fixture
def scene(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    monkeypatch.setenv("FACIAL_HIGHRES_ENABLED", "true")
    monkeypatch.setattr(
        "app.facial.lifecycle.shutil.disk_usage",
        lambda path: type("Usage", (), {"free": 80_000_000_000, "total": 100_000_000_000})(),
    )
    db = Session(create_engine("sqlite:///:memory:"))
    Base.metadata.create_all(db.bind)
    parent, photos = _gallery(db, tmp_path / "derivatives", photos=1)
    yield db, parent, photos[0], _settings(tmp_path), tmp_path
    db.close()


def jpeg():
    buffer = BytesIO()
    Image.new("RGB", (2400, 1600), "gray").save(buffer, "JPEG")
    return buffer.getvalue()


class HighresProvider:
    model_id = "opencv-yunet-sface"
    embedding_dimension = 128

    @property
    def last_metrics(self):
        return {"passes": [{"pass": "global"}], "embedding_successes": 1}

    def observe_highres_path(self, path):
        assert path.is_file()
        return [replace(_face(_vector(1)), image_width=2400, image_height=1600)]

    def observe_path(self, path):
        raise AssertionError("Prévia nunca pode ser reescaneada")


def prepare(scene):
    db, _, photo, settings, _ = scene
    row = admit_source(db, photo, jpeg(), settings=settings)
    path = safe_source_path(photo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(jpeg())
    finalize_source(db, photo, settings=settings)
    db.commit()
    return row, path


def test_lifecycle_analyzes_before_media_then_removes_and_never_rescans(scene, monkeypatch):
    db, _, photo, settings, tmp = scene
    _row, path = prepare(scene)
    assert not media_can_proceed(db, photo.id)
    assert not cleanup_source(db, photo.id)
    with pytest.raises(ValueError, match="Análise"):
        generate_derivatives(db, photo)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    args = {
        "photo_id": photo.id,
        "derivatives_root": tmp / "derivatives",
        "provider": HighresProvider(),
        "cipher": cipher,
        "settings": settings,
    }
    assert replace_photo_index(db, **args) == 1
    assert replace_photo_index(db, **args) == 1
    db.commit()
    regions = list(db.scalars(select(PhotoFaceEmbedding)))
    assert len(regions) == 1
    assert regions[0].bbox_x == pytest.approx(100 / 2400)
    assert regions[0].bbox_width == pytest.approx(180 / 2400)
    assert regions[0].pipeline_version == "highres-v1"
    generate_derivatives(db, photo)
    assert not path.exists()
    assert db.get(PhotoAnalysis, photo.id).deleted_at
    assert not cleanup_source(db, photo.id)
    monkeypatch.setenv("FACIAL_HIGHRES_ENABLED", "false")
    generate_derivatives(db, photo, variants={"client_preview"})
    assert len(list(db.scalars(select(PhotoFaceEmbedding)))) == 1
    with pytest.raises(FacialEngineError, match="Reenvie"):
        replace_photo_index(db, **args)


def test_retry_ttl_and_idempotent_admission(scene):
    db, _, photo, settings, _ = scene
    row, path = prepare(scene)
    assert admit_source(db, photo, jpeg(), settings=settings) is row
    assert len(list(db.scalars(select(FacialJob)))) == 1
    row.state = "failed"
    assert not cleanup_source(db, photo.id)
    assert path.exists()
    row.expires_at = now() - timedelta(seconds=1)
    db.commit()
    assert cleanup_source(db, photo.id)
    assert row.state == "reupload_required"
    assert not path.exists()


def test_old_job_cannot_consume_new_upload_generation(scene):
    from app.facial.jobs import FacialJobRepository
    from app.facial.worker import process_claimed_index_job

    db, _, photo, settings, tmp = scene
    row, _ = prepare(scene)
    row.expires_at = now() - timedelta(seconds=1)
    assert cleanup_source(db, photo.id)
    db.commit()
    prepare(scene)  # nova retenção e novo job; job anterior ainda estava na fila
    repository = FacialJobRepository()
    claim = repository.claim_next(db, lease_seconds=120, job_class="index")
    result = process_claimed_index_job(
        db,
        claim,
        repository=repository,
        provider=None,
        cipher=FacialCipher(active_key_id="test", keys={"test": b"k" * 32}),
        settings=settings,
        derivatives_root=tmp,
    )
    assert result.status == "cancelled"
    assert db.get(PhotoAnalysis, photo.id).state == "pending"
    assert safe_source_path(photo).exists()


def test_quota_rejects_before_persisting(scene, monkeypatch):
    db, _, photo, settings, _ = scene
    monkeypatch.setattr(
        "app.facial.lifecycle.shutil.disk_usage",
        lambda path: type("Usage", (), {"free": 10, "total": 100})(),
    )
    with pytest.raises(SourceCapacityError):
        admit_source(db, photo, jpeg(), settings=settings)
    assert db.get(PhotoAnalysis, photo.id) is None
    assert not safe_source_path(photo).exists()


def test_reupload_rechecks_quota_and_job_key_is_bounded(scene, monkeypatch):
    db, _, photo, settings, _ = scene
    row, _ = prepare(scene)
    assert len(db.scalar(select(FacialJob)).idempotency_key) < 100
    row.expires_at = now() - timedelta(seconds=1)
    assert cleanup_source(db, photo.id)
    db.commit()
    monkeypatch.setattr(
        "app.facial.lifecycle.shutil.disk_usage",
        lambda path: type("Usage", (), {"free": 10, "total": 100})(),
    )
    with pytest.raises(SourceCapacityError):
        admit_source(db, photo, jpeg(), settings=settings, reindex=True)
    assert row.deleted_at is not None


def test_disabled_admission_does_not_load_facial_credentials(scene, monkeypatch):
    db, _, photo, _, _ = scene
    monkeypatch.setenv("FACIAL_HIGHRES_ENABLED", "false")

    def forbidden(**kwargs):
        raise AssertionError("Legado não depende de credenciais faciais")

    monkeypatch.setattr("app.facial.lifecycle.facial_settings_from_environment", forbidden)
    assert admit_source(db, photo, jpeg()) is None


def test_admin_metrics_do_not_expose_arbitrary_payloads(scene, monkeypatch):
    from starlette.requests import Request

    from app.main import admin_parent_gallery_facial_index, admin_photo_facial_analysis

    db, parent, photo, _, _ = scene
    row, _ = prepare(scene)
    row.metrics = {"faces_accepted": 3, "embedding": [1, 0], "source_path": "/private"}
    db.commit()
    monkeypatch.setattr("app.main.require_admin", lambda request: None)
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    result = admin_photo_facial_analysis(photo.id, request, db)
    assert result["metrics"] == {"faces_accepted": 3}
    assert result["state"] == "pending"
    aggregate = admin_parent_gallery_facial_index(parent.id, request, page=1, page_size=50, db=db)[
        "analysis"
    ]
    assert aggregate["photos_total"] == 1 and aggregate["faces_accepted"] == 3
    assert {"embedding", "source_path"}.isdisjoint(aggregate)


def test_upload_handler_recovers_committed_reservation_without_duplicate_jobs(scene, monkeypatch):
    import asyncio

    from starlette.requests import Request

    from app.auth import MediaJob
    from app.facial import lifecycle
    from app.main import import_photo_source

    db, _, photo, settings, _ = scene
    monkeypatch.setattr("app.main.require_admin", lambda request: None)
    monkeypatch.setattr(lifecycle, "facial_settings_from_environment", lambda **kwargs: settings)
    real_write = lifecycle.write_source
    attempts = []

    def interrupted_write(path, payload):
        with Session(db.bind) as reader:
            reservation = reader.get(PhotoAnalysis, photo.id)
            assert reservation is not None and reservation.state == "receiving"
        attempts.append(1)
        if len(attempts) == 1:
            raise OSError("synthetic interrupted write")
        real_write(path, payload)

    monkeypatch.setattr(lifecycle, "write_source", interrupted_write)

    def request():
        async def receive():
            return {"type": "http.request", "body": jpeg(), "more_body": False}

        return Request(
            {
                "type": "http",
                "method": "PUT",
                "path": "/",
                "headers": [(b"content-type", b"image/jpeg")],
                "query_string": b"",
            },
            receive,
        )

    with pytest.raises(OSError):
        asyncio.run(import_photo_source(photo.id, request(), db))
    db.rollback()
    assert db.get(PhotoAnalysis, photo.id).state == "receiving"
    assert not safe_source_path(photo).exists()
    assert asyncio.run(import_photo_source(photo.id, request(), db)) == {"status": "queued"}
    assert asyncio.run(import_photo_source(photo.id, request(), db)) == {"status": "queued"}
    assert len(attempts) == 2  # replay não grava novamente
    assert safe_source_path(photo).read_bytes() == jpeg()
    assert db.get(PhotoAnalysis, photo.id).state == "pending"
    assert len(list(db.scalars(select(FacialJob)))) == 1
    assert len(list(db.scalars(select(MediaJob)))) == 1


def test_orphan_cleanup_only_removes_expired_owned_fragments(scene):
    import os
    import time

    from app.facial.lifecycle import cleanup_upload_fragments, write_source
    from app.media import source_root

    _, _, photo, _, _ = scene
    path = safe_source_path(photo)
    write_source(path, jpeg())
    orphan = source_root() / ".pyp-uploading" / "synthetic.part"
    orphan.write_bytes(b"partial")
    os.utime(orphan, (time.time() - 90000,) * 2)
    recent = orphan.with_name("recent.part")
    recent.write_bytes(b"active")
    unrelated = path.with_name("other.tmp")
    unrelated.write_bytes(b"unrelated")
    assert cleanup_upload_fragments() == 1
    assert not orphan.exists()
    assert recent.exists() and unrelated.exists() and path.exists()


def test_adjustment_must_complete_before_cleanup_and_never_reindexes(scene):
    from sqlalchemy.orm import sessionmaker
    from test_preview_adjustment import BrightEngine

    from app.preview_adjustment.service import configure, process_one

    db, parent, photo, settings, tmp = scene
    _, path = prepare(scene)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    replace_photo_index(
        db,
        photo_id=photo.id,
        derivatives_root=tmp,
        provider=HighresProvider(),
        cipher=cipher,
        settings=settings,
    )
    configure(db, parent.id, True, 50)
    db.commit()
    generate_derivatives(db, photo)
    before = db.scalar(select(PhotoFaceEmbedding)).id
    assert path.exists() and not cleanup_source(db, photo.id)
    db.commit()
    assert process_one(sessionmaker(db.bind), BrightEngine())
    db.expire_all()
    assert cleanup_source(db, photo.id)
    db.commit()
    assert not path.exists()
    assert db.scalar(select(PhotoFaceEmbedding)).id == before
    assert len(list(db.scalars(select(FacialJob)))) == 1


def test_maintenance_preserves_index_between_analysis_and_media(scene):
    from app.facial.purge import purge_photo_records, reconcile_invalid_facial_records
    from app.media import enqueue_derivatives

    db, parent, photo, settings, tmp = scene
    prepare(scene)
    enqueue_derivatives(db, photo)
    photo.available = False
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    replace_photo_index(
        db,
        photo_id=photo.id,
        derivatives_root=tmp,
        provider=HighresProvider(),
        cipher=cipher,
        settings=settings,
    )
    db.commit()
    assert reconcile_invalid_facial_records(db).embeddings == 0
    assert db.scalar(select(PhotoFaceEmbedding)) is not None
    assert (
        purge_photo_records(db, parent_gallery_id=parent.id, photo_asset_id=photo.id).embeddings
        == 1
    )


def test_media_worker_recovers_interruption_with_bounded_attempts(scene, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    from app.auth import MediaJob
    from app.worker import process_next_media_job

    db, _, photo, _, _ = scene
    row, path = prepare(scene)
    row.state = "failed"
    job = MediaJob(
        photo_asset_id=photo.id,
        status="processing",
        attempts=1,
        updated_at=now() - timedelta(minutes=11),
    )
    db.add(job)
    db.commit()
    monkeypatch.setattr("app.worker.SessionLocal", sessionmaker(db.bind))
    assert process_next_media_job()
    db.expire_all()
    assert job.status == "completed" and job.attempts == 2
    assert path.exists()  # falha facial ainda permite retry antes do TTL
    job.status = "failed"
    job.attempts = 3
    job.updated_at = now() - timedelta(minutes=11)
    db.commit()
    assert not process_next_media_job()
    assert job.status == "failed"


def test_tiles_cover_edges_overlap_and_stay_bounded():
    config = DetectionConfig(tile_side=1024)
    plan = tiles(6000, 4000, config)
    assert plan[0] == (0, 0, 1024, 1024)
    assert plan[-1][0] + plan[-1][2] == 6000
    assert plan[-1][1] + plan[-1][3] == 4000
    assert plan[1][0] < plan[0][0] + plan[0][2]
    assert all(x >= 0 and y >= 0 and x + w <= 6000 and y + h <= 4000 for x, y, w, h in plan)


def test_coordinate_restoration_dedup_and_selective_plan():
    row = (10, 20, 100, 120, 20, 40, 40, 40, 30, 60, 20, 80, 40, 80, 0.99)
    mapped = restore(row, scale_x=0.5, scale_y=0.5, offset_x=100, offset_y=200)
    assert mapped[:4] == (120, 240, 200, 240)
    assert mapped[4:6] == (140, 280)
    assert normalized_box(mapped[:4], 1000, 1000) == pytest.approx((0.12, 0.24, 0.2, 0.24))
    items = [Detection(mapped, "tile:0"), Detection(mapped, "global")]
    assert len(deduplicate(items, 0.4)) == 1
    adjacent = (400, *mapped[1:])
    assert len(deduplicate([*items, Detection(adjacent, "tile:1")], 0.4)) == 2
    big = Detection((1200, 900, 1500, 1500, *row[4:]), "global")
    assert difficulty(6000, 4000, [big], DetectionConfig()) == []
    assert "global_empty" in difficulty(6000, 4000, [], DetectionConfig())


def test_similarity_classes_and_model_isolation(scene):
    db, parent, photo, settings, tmp = scene
    prepare(scene)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    replace_photo_index(
        db,
        photo_id=photo.id,
        derivatives_root=tmp,
        provider=HighresProvider(),
        cipher=cipher,
        settings=settings,
    )
    args = {
        "gallery_id": parent.id,
        "query_embedding": _vector(0.7, 0.714142842),
        "cipher": cipher,
        "settings": settings,
        "threshold_milli": 750,
        "ambiguous_threshold_milli": 650,
    }
    assert search_gallery_index(db, **args)[0].match_class == "ambiguous"
    row = db.scalar(select(PhotoFaceEmbedding))
    row.model_id = "edgeface"
    db.flush()
    assert search_gallery_index(db, **args) == []


@pytest.mark.parametrize("deepen", [False, True])
@pytest.mark.parametrize("failure", [None, "embedding", "detection"])
def test_provider_orients_before_detection_and_aligns_original_pixels(tmp_path, deepen, failure):
    import cv2
    import numpy as np

    from app.facial.provider import FacialProviderError, OpenCvSFaceProvider

    path = tmp_path / "oriented.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (2400, 1600), "gray").save(path, exif=exif)
    shapes = []

    class Detector:
        calls = 0

        def setScoreThreshold(self, value):
            pass

        def setInputSize(self, value):
            self.size = value

        def detect(self, image):
            if failure == "detection":
                raise RuntimeError("fixture")
            self.calls += 1
            if self.calls > 2:
                return None, None  # primeiro tile não contém outra região na fixture
            w, h = self.size
            return None, np.array(
                [
                    [
                        w * 0.3,
                        h * 0.3,
                        w * 0.35,
                        h * 0.35,
                        w * 0.4,
                        h * 0.4,
                        w * 0.5,
                        h * 0.4,
                        w * 0.45,
                        h * 0.5,
                        w * 0.4,
                        h * 0.55,
                        w * 0.5,
                        h * 0.55,
                        0.99,
                    ]
                ]
            )

    class Recognizer:
        def alignCrop(self, image, face):
            shapes.append(image.shape)
            assert face[0] == pytest.approx(480, abs=1)
            return image[:112, :112]

        def feature(self, image):
            if failure == "embedding":
                raise RuntimeError("fixture")
            return np.ones(128)

    provider = object.__new__(OpenCvSFaceProvider)
    provider._cv2 = cv2
    provider._detector = Detector()
    provider._recognizer = Recognizer()
    provider._detection_threshold = 0.75
    provider.last_metrics = {"previous_photo": "must disappear"}
    if failure:
        with pytest.raises(FacialProviderError) as raised:
            provider.observe_highres_path(
                path, config=DetectionConfig(group_count=1, max_tiles=1) if deepen else None
            )
        metrics = raised.value.metrics
        assert "previous_photo" not in metrics
        assert metrics["detection_failures"] == int(failure == "detection")
        assert metrics["elapsed_ms"] >= 0
        if failure == "embedding":
            assert metrics["embedding_failures"] == 1
            assert metrics["embedding_successes"] == 0
            assert metrics["deduplicated"] == 1
        return
    faces = provider.observe_highres_path(
        path, config=DetectionConfig(group_count=1, max_tiles=1) if deepen else None
    )
    assert shapes == [(2400, 1600, 3)]
    assert (faces[0].image_width, faces[0].image_height) == (1600, 2400)
    assert len(provider.last_metrics["passes"]) == (3 if deepen else 1)
    assert provider.last_metrics["raw_detections"] == (2 if deepen else 1)
    assert provider.last_metrics["deduplicated"] == 1
    assert provider.last_metrics["budget_exhausted"] == deepen


def test_failed_attempt_metrics_survive_rollback_and_retry_without_double_counting(scene):
    from app.facial.analysis_metrics import gallery_analysis_metrics
    from app.facial.jobs import FacialJobRepository
    from app.facial.provider import FacialProviderError
    from app.facial.worker import process_claimed_index_job

    db, parent, photo, settings, tmp = scene
    _, path = prepare(scene)
    repository = FacialJobRepository()
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})

    class BrokenProvider:
        def observe_highres_path(self, path):
            raise FacialProviderError(
                "fixture",
                metrics={
                    "embedding_failures": 1,
                    "deduplicated": 2,
                    "elapsed_ms": 42,
                    "embedding": [1, 0],
                    "tiles": float("nan"),
                    "raw_detections": "secret",
                },
            )

    claim = repository.claim_next(db, lease_seconds=120, job_class="index")
    args = {
        "repository": repository,
        "cipher": cipher,
        "settings": settings,
        "derivatives_root": tmp,
    }
    with pytest.raises(FacialProviderError) as raised:
        process_claimed_index_job(db, claim, provider=BrokenProvider(), **args)
    db.rollback()
    repository.fail(db, claim, raised.value, max_attempts=3, retry_delay_seconds=0)
    row = db.get(PhotoAnalysis, photo.id)
    assert row.state == "pending" and path.exists()
    assert row.metrics["embedding_failures"] == 1
    assert row.metrics["attempts"] == 1
    assert {"embedding", "tiles", "raw_detections"}.isdisjoint(row.metrics)
    summary = gallery_analysis_metrics(db, parent_gallery_id=parent.id)
    assert summary["embedding_failures"] == 1 and summary["queue_depth"] == 1
    assert summary["photos_processed"] == 0
    assert summary["oldest_job_age_seconds"] >= 0
    claim = repository.claim_next(db, lease_seconds=120, job_class="index")
    process_claimed_index_job(db, claim, provider=HighresProvider(), **args)
    summary = gallery_analysis_metrics(db, parent_gallery_id=parent.id)
    assert summary["photos_processed"] == summary["photos_with_faces"] == 1
    assert summary["faces_per_processed_photo"] == 1
    assert summary["embedding_failures"] == summary["queue_depth"] == 0
    assert db.get(PhotoAnalysis, photo.id).metrics["attempts"] == 2
    other, _ = _gallery(db, tmp / "other", photos=1)
    assert gallery_analysis_metrics(db, parent_gallery_id=other.id)["photos_total"] == 0


def test_upload_index_media_region_query_and_purge_integrated(scene):
    from app.auth import Client, ParentGalleryRegistration
    from app.facial.jobs import FacialJobRepository
    from app.facial.purge import facial_cleanup_proof, purge_gallery_records
    from app.facial.regions import photo_regions
    from app.facial.search import create_search_request, read_search_result
    from app.facial.search_worker import process_claimed_search_job
    from app.facial.worker import process_claimed_index_job

    db, parent, photo, settings, tmp = scene
    _, path = prepare(scene)
    repository = FacialJobRepository()
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    claim = repository.claim_next(db, lease_seconds=120, job_class="index")
    process_claimed_index_job(
        db,
        claim,
        repository=repository,
        provider=HighresProvider(),
        cipher=cipher,
        settings=settings,
        derivatives_root=tmp,
    )
    generate_derivatives(db, photo)
    assert not path.exists()
    client = Client(full_name="Pessoa sintética", phone_e164="+5511999999901")
    db.add(client)
    db.flush()
    db.add(
        ParentGalleryRegistration(parent_gallery_id=parent.id, client_id=client.id, status="active")
    )
    db.commit()
    regions = photo_regions(
        db, gallery_id=parent.id, client_id=client.id, photo_id=photo.id, settings=settings
    )
    from uuid import UUID

    request = create_search_request(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        consent_version=settings.consent_version,
        subject_declaration="adult",
        representation_reference=None,
        payload=b"",
        reference_region_id=UUID(regions[0]["id"]),
        settings=settings,
    )
    db.commit()
    claim = repository.claim_next(db, lease_seconds=120, job_class="search")
    process_claimed_search_job(
        db, claim, repository=repository, provider=None, cipher=cipher, settings=settings
    )
    result, candidates = read_search_result(
        db, parent_gallery_id=parent.id, client_id=client.id, request_id=request.id
    )
    assert result.status == "ready" and candidates[0].photo_asset_id == photo.id
    purge_gallery_records(db, parent_gallery_id=parent.id)
    db.commit()
    assert facial_cleanup_proof(db, parent_gallery_id=parent.id)["clean"]
