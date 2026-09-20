"""Concorrência real opcional; cria somente schema próprio em PostgreSQL descartável."""

import multiprocessing
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session
from test_facial_engine import _settings
from test_highres_pipeline import jpeg

from app.auth import (
    Base,
    FacialJob,
    FacialRollout,
    ParentGallery,
    PhotoAnalysis,
    PhotoAsset,
    PhotoFolder,
    now,
)
from app.facial.lifecycle import admit_source, analysis_for, cleanup_sources, finalize_source
from app.facial.policy import ensure_automatic_policy


def _engine(url, schema):
    return create_engine(
        url, connect_args={"options": f"-c search_path={schema} -c statement_timeout=10000"}
    )


def _admit_process(url, schema, photo_id, root, start, output):
    # Configuração sintética explícita; não depende da capacidade de disco da estação.
    from app.facial import lifecycle

    os.environ["FACIAL_HIGHRES_ENABLED"] = "true"
    os.environ["FACIAL_SOURCE_MAX_FILES"] = "1"
    os.environ["MEDIA_SOURCE_ROOT"] = root
    lifecycle.shutil.disk_usage = lambda path: type(
        "Usage", (), {"free": 80_000_000_000, "total": 100_000_000_000}
    )()
    engine = _engine(url, schema)
    start.wait(10)
    try:
        with Session(engine) as db:
            photo = db.scalar(
                select(PhotoAsset).where(PhotoAsset.id == UUID(photo_id)).with_for_update()
            )
            admit_source(db, photo, jpeg(), settings=_settings(Path(root)))
            finalize_source(db, photo, settings=_settings(Path(root)))
            db.commit()
            output.put("admitted")
    except lifecycle.SourceCapacityError:
        output.put("capacity")
    except Exception as error:  # noqa: BLE001 -- reporta falha do subprocesso sem bloquear a fila de teste
        output.put(type(error).__name__)
    finally:
        engine.dispose()


@pytest.fixture
def postgres_scene(tmp_path, monkeypatch):
    url = os.getenv("HIGHRES_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requer PostgreSQL descartável explícito em HIGHRES_TEST_POSTGRES_URL")
    schema = "highres_test_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = _engine(url, schema)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("FACIAL_HIGHRES_ENABLED", "true")
    monkeypatch.setattr(
        "app.facial.lifecycle.shutil.disk_usage",
        lambda path: type("Usage", (), {"free": 80_000_000_000, "total": 100_000_000_000})(),
    )
    try:
        with Session(engine) as db:
            parent = ParentGallery(name="Concorrência sintética")
            db.add(parent)
            db.flush()
            folder = PhotoFolder(parent_gallery_id=parent.id, name="Fotos")
            db.add(folder)
            db.flush()
            active = _settings(tmp_path)
            ensure_automatic_policy(db, parent_gallery_id=parent.id, settings=active)
            db.add(
                FacialRollout(
                    environment="test",
                    parent_gallery_id=parent.id,
                    status="active",
                    stage="canary",
                    model_version=active.model_version,
                    quality_version=active.quality_version,
                    calibration_version=active.calibration_version,
                    legal_notice_version=active.legal_notice_version,
                    consent_version=active.consent_version,
                    legal_basis_reference=active.legal_basis_reference,
                    retention_policy_version=active.retention_policy_version,
                )
            )
            photos = [
                PhotoAsset(
                    parent_gallery_id=parent.id,
                    folder_id=folder.id,
                    filename=f"synthetic-{i}.jpg",
                    storage_key=f"{parent.id}/{i}.jpg",
                )
                for i in range(2)
            ]
            db.add_all(photos)
            db.commit()
            ids = [photo.id for photo in photos]
        yield url, schema, engine, ids, tmp_path
    finally:
        engine.dispose()
        with admin.begin() as connection:
            # Schema gerado nesta fixture; nunca usa public ou dados preexistentes.
            assert schema.startswith("highres_test_") and len(schema) == 45
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.mark.parametrize("same_photo", [False, True])
def test_postgres_concurrent_admission_does_not_exceed_quota(postgres_scene, same_photo):
    url, schema, engine, ids, root = postgres_scene
    context = multiprocessing.get_context("spawn")
    start, output = context.Event(), context.Queue()
    ids = [ids[0], ids[0]] if same_photo else ids
    processes = [
        context.Process(
            target=_admit_process,
            args=(url, schema, str(photo_id), str(root / "source"), start, output),
        )
        for photo_id in ids
    ]
    for process in processes:
        process.start()
    start.set()
    results = [output.get(timeout=30) for _ in processes]
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0
    assert sorted(results) == (["admitted", "admitted"] if same_photo else ["admitted", "capacity"])
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(PhotoAnalysis)) == 1
        assert db.scalar(select(func.count()).select_from(FacialJob)) == 1


def test_postgres_cleanup_skips_reader_lock_and_recovers_after_release(postgres_scene):
    _, _, engine, ids, root = postgres_scene
    with Session(engine) as db:
        photo = db.get(PhotoAsset, ids[0])
        row = admit_source(db, photo, jpeg(), settings=_settings(root))
        row.expires_at = now() - timedelta(seconds=1)
        db.commit()
    with Session(engine) as reader, Session(engine) as cleaner:
        analysis_for(reader, ids[0], lock=True)
        assert cleanup_sources(cleaner) == 0
        reader.rollback()
        assert cleanup_sources(cleaner) == 1
        assert cleaner.get(PhotoAnalysis, ids[0]).state == "reupload_required"


def test_postgres_migration_upgrade_downgrade_in_separate_schema(postgres_scene):
    url, _, _, _, _ = postgres_scene
    schema = "highres_migration_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        environment = {**os.environ, "DATABASE_URL": url, "PGOPTIONS": f"-c search_path={schema}"}
        root = Path(__file__).resolve().parents[1]
        for action, revision in (
            ("upgrade", "head"),
            ("downgrade", "20260914_0056"),
            ("upgrade", "head"),
        ):
            result = subprocess.run(
                [sys.executable, "-m", "alembic", action, revision],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            assert result.returncode == 0, result.stderr[-4000:]
        with admin.connect() as connection:
            assert (
                connection.scalar(text(f'SELECT version_num FROM "{schema}".alembic_version'))
                == "20260919_0057"
            )
    finally:
        with admin.begin() as connection:
            assert schema.startswith("highres_migration_") and len(schema) == 50
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
