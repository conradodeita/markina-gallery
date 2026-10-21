"""Worker local para desenvolvimento RAW; não expõe endpoints nem arquivos-fonte."""

from __future__ import annotations

import os
import time
from datetime import timedelta
from hashlib import sha256

from sqlalchemy import select

from app.acervo_context import require_active_owner
from app.auth import (
    MediaJob,
    ParentGallery,
    PhotoAnalysis,
    PhotoAsset,
    PhotoFolder,
    RawDevelopmentJob,
    SessionLocal,
    Tenant,
    expired,
    now,
)
from app.facial.lifecycle import admit_source, finalize_source, write_source
from app.maintenance_control import MaintenanceBusy, shared_operation
from app.media import enqueue_derivatives, safe_source_path
from app.raw_development.engines import RawEngineError, engine_for, normalize_rendered_jpeg
from app.raw_development.state import (
    RAW_MAX_ATTEMPTS,
    RAW_TTL_SECONDS,
    raw_staging_path,
    staging_root,
)


def _remove_job_files(job: RawDevelopmentJob) -> None:
    raw_staging_path(job.staging_key).unlink(missing_ok=True)
    raw_staging_path(job.staging_key + ".rendered.jpg").unlink(missing_ok=True)
    raw_staging_path(job.staging_key + ".working.jpg").unlink(missing_ok=True)


def _cleanup_expired(db) -> None:
    stale_ready = list(db.scalars(select(RawDevelopmentJob).where(
        RawDevelopmentJob.status == "ready",
        RawDevelopmentJob.updated_at < now() - timedelta(minutes=5),
    ).order_by(RawDevelopmentJob.updated_at).limit(64)))
    for job in stale_ready:
        _remove_job_files(job)
        media_job = db.scalar(select(MediaJob).where(
            MediaJob.photo_asset_id == job.photo_asset_id, MediaJob.tenant_id == job.tenant_id))
        analysis = db.scalar(select(PhotoAnalysis).where(
            PhotoAnalysis.photo_asset_id == job.photo_asset_id, PhotoAnalysis.tenant_id == job.tenant_id))
        photo = db.scalar(select(PhotoAsset).where(
            PhotoAsset.id == job.photo_asset_id, PhotoAsset.tenant_id == job.tenant_id))
        if media_job and media_job.status == "completed" and not analysis and photo:
            safe_source_path(photo).unlink(missing_ok=True)
        job.updated_at = now()
    expired_jobs = list(db.scalars(select(RawDevelopmentJob).where(
        RawDevelopmentJob.expires_at <= now(),
        RawDevelopmentJob.status.in_(("receiving", "queued", "processing", "failed")),
    ).with_for_update(skip_locked=True).limit(64)))
    for job in expired_jobs:
        _remove_job_files(job)
        job.status = "reupload_required"
        job.last_error = "source_expired"
        job.updated_at = now()
    # Upload reservations from an interrupted HTTP request never reach the worker queue.
    cutoff = now() - timedelta(seconds=RAW_TTL_SECONDS)
    abandoned = list(staging_root().iterdir()) if staging_root().exists() else []
    for path in abandoned[:64]:
        try:
            if path.is_symlink() or path.stat().st_mtime >= cutoff.timestamp():
                continue
            if path.is_dir():
                import shutil

                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        except OSError:
            continue


def process_next_raw_job(session_factory=SessionLocal) -> bool:
    try:
        with shared_operation(SessionLocal.kw["bind"], service="raw-development-worker"):
            return _process_next_raw_job(session_factory)
    except MaintenanceBusy:
        return False


def _process_next_raw_job(session_factory=SessionLocal) -> bool:
    with session_factory() as db:
        _cleanup_expired(db)
        stale = list(db.scalars(select(RawDevelopmentJob).where(
            RawDevelopmentJob.status == "processing",
            RawDevelopmentJob.updated_at < now() - timedelta(minutes=20),
            RawDevelopmentJob.attempts < RAW_MAX_ATTEMPTS,
        ).with_for_update(skip_locked=True).limit(16)))
        for item in stale:
            item.status = "queued"
        exhausted = list(db.scalars(select(RawDevelopmentJob).where(
            RawDevelopmentJob.status == "processing",
            RawDevelopmentJob.updated_at < now() - timedelta(minutes=20),
            RawDevelopmentJob.attempts >= RAW_MAX_ATTEMPTS,
        ).with_for_update(skip_locked=True).limit(16)))
        for item in exhausted:
            _remove_job_files(item)
            item.status = "reupload_required"
            item.last_error = "worker_interrupted"
            item.updated_at = now()
        job = db.scalar(select(RawDevelopmentJob).where(
            RawDevelopmentJob.status == "queued",
        ).order_by(RawDevelopmentJob.created_at).limit(1).with_for_update(skip_locked=True))
        if not job:
            db.commit()
            return False
        job.status = "processing"
        job.attempts += 1
        job.updated_at = now()
        db.commit()
        photo_id = job.photo_asset_id
        tenant_id = job.tenant_id
        staging_key = job.staging_key
        engine_name = job.engine
        engine_version = job.engine_version

    try:
        with session_factory() as db:
            job = db.get(RawDevelopmentJob, (photo_id, tenant_id))
            tenant = db.get(Tenant, tenant_id)
            photo = db.scalar(select(PhotoAsset).where(
                PhotoAsset.id == photo_id, PhotoAsset.tenant_id == tenant_id))
            folder = db.get(PhotoFolder, photo.folder_id) if photo and photo.tenant_id == tenant_id else None
            if not job:
                raise RawEngineError("Origem indisponível.")
            if tenant is None or tenant.status != "active":
                _remove_job_files(job)
                job.status = "reupload_required"
                job.last_error = "tenant_inactive"
                job.updated_at = now()
                db.commit()
                return True
            if not photo or not folder or folder.tenant_id != tenant_id:
                raise RawEngineError("Origem indisponível.")
            source = raw_staging_path(staging_key)
            rendered = raw_staging_path(staging_key + ".rendered.jpg")
            if not source.is_file():
                raise RawEngineError("Fonte temporária indisponível.")
            input_digest = sha256()
            input_size = 0
            with source.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    input_size += len(chunk)
                    input_digest.update(chunk)
            if input_size != job.input_bytes or input_digest.hexdigest() != job.input_fingerprint:
                raise RawEngineError("A fonte temporária não passou na verificação de integridade.")
            engine_for(engine_name, version=engine_version).render(source, rendered)
            output = raw_staging_path(staging_key + ".working.jpg")
            result = normalize_rendered_jpeg(rendered, output)
            if folder.purpose == "cover_assets" and result.width <= result.height:
                output.unlink(missing_ok=True)
                raise RawEngineError("A capa deve ser horizontal.")
            if output.stat().st_size <= 0 or output.stat().st_size > 160 * 1024 * 1024:
                output.unlink(missing_ok=True)
                raise RawEngineError("O JPEG desenvolvido excede o limite permitido.")
            payload = output.read_bytes()
            analysis = None
            if folder.purpose == "content":
                analysis = admit_source(db, photo, payload)
                if analysis and analysis.state != "receiving":
                    enqueue_derivatives(db, photo)
                    output.unlink(missing_ok=True)
                    _remove_job_files(job)
                    job.status = "ready"
                    job.camera_make = result.camera_make
                    job.camera_model = result.camera_model
                    job.width = result.width
                    job.height = result.height
                    job.updated_at = now()
                    db.commit()
                    return True
                if analysis:
                    db.commit()
                    analysis = db.get(type(analysis), photo.id)
            write_source(
                safe_source_path(photo), payload, tenant_id=tenant_id,
                authorize=lambda: require_active_owner(db, tenant_id),
            )
            if analysis:
                finalize_source(db, photo)
            media_job = enqueue_derivatives(db, photo)
            if folder.purpose == "cover_assets":
                gallery = db.scalar(select(ParentGallery).where(
                    ParentGallery.id == photo.parent_gallery_id,
                    ParentGallery.tenant_id == tenant_id,
                ))
                if gallery:
                    gallery.cover_photo_id = photo.id
            job = db.get(RawDevelopmentJob, (photo_id, tenant_id))
            job.camera_make = result.camera_make
            job.camera_model = result.camera_model
            job.width = result.width
            job.height = result.height
            job.status = "ready"
            job.last_error = None
            job.updated_at = now()
            db.commit()
            _remove_job_files(job)
            output.unlink(missing_ok=True)
            # Prevent a duplicate derivative enqueue from re-entering processing.
            if media_job.status == "failed":
                media_job.status = "queued"
            return True
    except Exception:  # noqa: BLE001 -- sanitized categories only
        with session_factory() as db:
            job = db.get(RawDevelopmentJob, (photo_id, tenant_id))
            if job:
                if job.attempts < RAW_MAX_ATTEMPTS and not expired(job.expires_at):
                    job.status = "queued"
                else:
                    job.status = "failed"
                    _remove_job_files(job)
                job.last_error = "render_failed"
                job.updated_at = now()
                db.commit()
        return True


def main() -> None:
    while True:
        try:
            worked = process_next_raw_job()
        except Exception:  # noqa: BLE001 -- keep the isolated worker alive
            worked = False
        if not worked:
            time.sleep(max(1, min(30, int(os.getenv("RAW_WORKER_POLL_SECONDS", "5")))))


if __name__ == "__main__":
    main()
