"""Fonte high-res temporária. Ausência de PhotoAnalysis preserva o legado."""

from __future__ import annotations

import hashlib
import os
import shutil
import time
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from PIL import Image, ImageOps
from sqlalchemy import func, select, text

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    FacialJob,
    MediaDerivative,
    MediaJob,
    PhotoAnalysis,
    PhotoAsset,
    PhotoFolder,
    Tenant,
    expired,
    now,
)
from app.facial.config import _boolean, _integer, facial_settings_from_environment
from app.facial.jobs import FacialJobRepository
from app.facial.policy import ensure_automatic_policy
from app.facial.rollout import rollout_is_active
from app.tenancy import TenantContextError, require_single_tenant

PIPELINE_VERSION = "highres-v1"


class SourceCapacityError(ValueError):
    pass


def analysis_for(db, photo_id, *, tenant_id, lock=False):
    require_active_owner(db, tenant_id)
    query = select(PhotoAnalysis).where(PhotoAnalysis.tenant_id == tenant_id, PhotoAnalysis.photo_asset_id == photo_id)
    if lock:
        query = query.with_for_update()
    return db.scalar(query.execution_options(populate_existing=True))


def admit_source(db, photo, payload: bytes, *, settings=None, reindex=False):
    """Chamado antes da escrita. Serializa quota global e bloqueia substituição ativa."""
    photo = owned_record(db, PhotoAsset, photo.id, tenant_id=photo.tenant_id)
    if photo is None:
        raise ValueError("Foto indisponível.")
    existing = analysis_for(db, photo.id, tenant_id=photo.tenant_id, lock=True)
    from app.folder_processing import facial_processing_allowed

    if not facial_processing_allowed(db, photo.folder_id, tenant_id=photo.tenant_id):
        if reindex:
            raise SourceCapacityError("Novos trabalhos faciais estão pausados nesta pasta.")
        if not existing:
            return None
    if not existing and not _boolean("FACIAL_HIGHRES_ENABLED"):
        return None
    if not existing and db.scalar(select(MediaJob.id).where(MediaJob.tenant_id == photo.tenant_id, MediaJob.photo_asset_id == photo.id)):
        return None  # fontes legadas não mudam de política por reenvio implícito
    active = settings or facial_settings_from_environment(verify_runtime_assets=False)
    if not active.enabled or not rollout_is_active(
        db, settings=active, parent_gallery_id=photo.parent_gallery_id
    , tenant_id=photo.tenant_id):
        if existing:
            raise SourceCapacityError(
                "Processamento temporariamente indisponível. Tente novamente."
            )
        return None
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(718394051)"))
    digest = hashlib.sha256(payload).hexdigest()
    if existing:
        if existing.source_fingerprint == digest:
            if existing.state == "receiving" and not existing.deleted_at:
                _require_source_capacity(db, len(payload), exclude_photo_id=photo.id)
            if existing.deleted_at and (existing.state == "reupload_required" or reindex):
                _require_source_capacity(db, len(payload))
                existing.deleted_at = None
                existing.state = "receiving"
                existing.metrics = {}
                existing.expires_at = now() + timedelta(
                    seconds=_integer(
                        "FACIAL_SOURCE_TTL_SECONDS", 86400, minimum=300, maximum=604800
                    )
                )
            return existing  # reenvio não renova retenção nem recria regiões
        raise SourceCapacityError("Esta foto já possui processamento. Envie como uma nova foto.")
    _require_source_capacity(db, len(payload))
    with Image.open(BytesIO(payload)) as opened:
        if opened.format != "JPEG" or opened.width * opened.height > 40_000_000:
            raise ValueError("JPEG excede a resolução permitida.")
        visual = ImageOps.exif_transpose(opened)
        visual.load()
        width, height = visual.size
    ensure_automatic_policy(db, parent_gallery_id=photo.parent_gallery_id, tenant_id=photo.tenant_id, settings=active)
    row = PhotoAnalysis(
        tenant_id=photo.tenant_id,
        photo_asset_id=photo.id,
        source_fingerprint=digest,
        source_bytes=len(payload),
        width=width,
        height=height,
        pipeline_version=PIPELINE_VERSION,
        state="receiving",
        expires_at=now()
        + timedelta(
            seconds=_integer("FACIAL_SOURCE_TTL_SECONDS", 86400, minimum=300, maximum=604800)
        ),
        metrics={},
    )
    db.add(row)
    db.flush()
    return row


def _require_source_capacity(db, payload_bytes, *, exclude_photo_id=None):
    from app.media import source_root

    root = source_root()
    root.mkdir(parents=True, exist_ok=True)
    quota = select(func.count(), func.coalesce(func.sum(PhotoAnalysis.source_bytes), 0)).where(
        PhotoAnalysis.deleted_at.is_(None)
    )
    if exclude_photo_id:
        quota = quota.where(PhotoAnalysis.photo_asset_id != exclude_photo_id)
    count, total = db.execute(quota).one()
    fragments = [*(root / ".pyp-uploading").glob("*.part"), *(root / "tenants").glob("*/.pyp-uploading/*.part")]
    for fragment in fragments:
        try:
            if fragment.is_file() and not fragment.is_symlink():
                count += 1
                total += fragment.stat().st_size
        except FileNotFoundError:
            continue  # cleanup pode concluir entre listagem e stat
    limit_count = _integer("FACIAL_SOURCE_MAX_FILES", 64, minimum=1, maximum=10000)
    limit_bytes = _integer(
        "FACIAL_SOURCE_MAX_BYTES", 2_000_000_000, minimum=1_000_000, maximum=100_000_000_000
    )
    disk = shutil.disk_usage(root)
    if (
        count >= limit_count
        or total + payload_bytes > limit_bytes
        or disk.free - payload_bytes < disk.total * 0.25
    ):
        raise SourceCapacityError(
            "Processamento ocupado. Aguarde a liberação de espaço e tente novamente."
        )


def source_job_key(photo_id, row, policy):
    # Normaliza timezone: o SQLite pode devolver o mesmo timestamp sem tzinfo.
    from datetime import UTC

    expiry = (
        row.expires_at.replace(tzinfo=UTC)
        if row.expires_at.tzinfo is None
        else row.expires_at.astimezone(UTC)
    )
    key = hashlib.sha256(
        f"{photo_id}:{row.source_fingerprint}:{policy.model_version}:{policy.quality_version}:{policy.index_generation}:{expiry.isoformat()}".encode()
    ).hexdigest()
    return f"highres:{key}"


def finalize_source(db, photo, *, settings=None):
    active = settings or facial_settings_from_environment(verify_runtime_assets=False)
    row = analysis_for(db, photo.id, tenant_id=photo.tenant_id, lock=True)
    if row is None or row.state != "receiving":
        return
    policy, _ = ensure_automatic_policy(
        db,
        tenant_id=photo.tenant_id, parent_gallery_id=photo.parent_gallery_id, settings=active
    )
    digest = row.source_fingerprint
    FacialJobRepository().enqueue(
        db,
        kind="index",
                tenant_id=photo.tenant_id,
        idempotency_key=source_job_key(photo.id, row, policy),
        parent_gallery_id=photo.parent_gallery_id,
        derived_gallery_id=photo.derived_gallery_id,
        photo_asset_id=photo.id,
        model_version=policy.model_version,
        quality_version=policy.quality_version,
        preview_fingerprint=digest,
    )
    row.state = "pending"
    db.flush()


def write_source(path: Path, payload: bytes, *, tenant_id, authorize):
    from app.media import media_namespace, source_root
    media_namespace(path.relative_to(source_root()).as_posix(), tenant_id)
    authorize()

    path.parent.mkdir(parents=True, exist_ok=True)
    staging = source_root() / "tenants" / str(tenant_id) / ".pyp-uploading"
    staging.mkdir(parents=True, exist_ok=True)
    if staging.resolve() != staging:
        raise ValueError("Armazenamento temporário indisponível.")
    authorize()
    temporary = staging / f"{uuid4()}.part"
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        authorize()
        media_namespace(path.resolve().relative_to(source_root()).as_posix(), tenant_id)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def media_can_proceed(db, photo_id, *, tenant_id):
    row = analysis_for(db, photo_id, tenant_id=tenant_id, lock=True)
    if row and row.state == "receiving":
        return False
    if not row or row.state != "pending":
        return True
    latest = db.scalar(
        select(FacialJob)
        .where(FacialJob.tenant_id == tenant_id, FacialJob.photo_asset_id == photo_id, FacialJob.kind == "index")
        .order_by(FacialJob.created_at.desc(), FacialJob.id.desc())
        .limit(1)
    )
    if latest and latest.status in {"failed", "cancelled"}:
        row.state = "failed"
        row.metrics = {**row.metrics, "final_error": latest.last_error_category or "cancelled"}
        return True
    return False


def cleanup_source(db, photo_id, *, tenant_id):
    """Lock compartilhado com leitores da fonte. TTL não interrompe um lease ativo."""
    from app.folder_processing import effective_preview
    from app.media import safe_derivative_path, safe_source_path
    from app.preview_adjustment.service import adjusted_path

    row = analysis_for(db, photo_id, tenant_id=tenant_id, lock=True)
    if not row or row.deleted_at:
        return False
    photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
    if not photo:
        return False
    active = db.scalar(
        select(FacialJob.id).where(
            FacialJob.tenant_id == tenant_id,
            FacialJob.photo_asset_id == photo_id,
            FacialJob.kind == "index",
            FacialJob.status == "processing",
            FacialJob.lease_expires_at > now(),
        )
    )
    if active:
        return False
    is_expired = expired(row.expires_at)
    derivatives = list(
        db.scalars(
            select(MediaDerivative).where(
                MediaDerivative.tenant_id == tenant_id,
                MediaDerivative.photo_asset_id == photo_id,
                MediaDerivative.variant.in_(("thumbnail", "admin_preview", "client_preview")),
                MediaDerivative.status == "ready",
            )
        )
    )
    if not is_expired:
        if row.state != "ready":
            return False
        if len(derivatives) != 3:
            return False
        for derivative in derivatives:
            path = safe_derivative_path(derivative)
            if not path.is_file():
                return False
            with Image.open(path) as image:
                image.load()
        folder = owned_record(db, PhotoFolder, photo.folder_id, tenant_id=tenant_id)
        config = effective_preview(db, folder) if folder else None
        if config and config.enabled and not adjusted_path(db, photo_id, tenant_id=photo.tenant_id):
            return False
    if is_expired and (
        row.state != "ready"
        or len(derivatives) != 3
        or any(not safe_derivative_path(item).is_file() for item in derivatives)
    ):
        row.state = "reupload_required"
    require_active_owner(db, tenant_id)
    safe_source_path(photo).unlink(missing_ok=True)
    row.deleted_at = now()
    db.flush()
    return True


def cleanup_sources(db, *, limit=64):
    ids = list(
        db.execute(
            select(PhotoAnalysis.photo_asset_id, PhotoAnalysis.tenant_id)
            .join(Tenant, Tenant.id == PhotoAnalysis.tenant_id)
            .where(Tenant.status == "active")
            .where(PhotoAnalysis.deleted_at.is_(None))
            .where(
                (PhotoAnalysis.expires_at <= now())
                | (PhotoAnalysis.state.in_(("ready", "pending")))
            )
            .order_by(PhotoAnalysis.updated_at)
            .limit(limit)
            .with_for_update(skip_locked=True, of=PhotoAnalysis)
        )
    )
    removed = 0
    for photo_id, tenant_id in ids:
        try:
            with db.begin_nested():
                # Cancelamento/falha terminal também libera a mídia após restart do worker facial.
                media_can_proceed(db, photo_id, tenant_id=tenant_id)
                removed += int(cleanup_source(db, photo_id, tenant_id=tenant_id))
                row = analysis_for(db, photo_id, tenant_id=tenant_id)
                if row:
                    row.updated_at = now()  # rodada justa mesmo quando a quota excede o lote
        except HTTPException as exc:
            if exc.status_code != 403:
                raise
            continue
        except (OSError, ValueError):
            row = analysis_for(db, photo_id, tenant_id=tenant_id, lock=True)
            if row:
                row.updated_at = now()
                row.metrics = {**row.metrics, "cleanup_error": "artifact_unavailable"}
    db.commit()
    cleanup_upload_fragments(limit=limit, db=db)
    return removed


def cleanup_upload_fragments(*, limit=64, db):
    """Fragmentos novos têm owner; legado ambíguo permanece sem exclusão."""
    from app.media import source_root

    root = source_root()
    cutoff = time.time() - _integer("FACIAL_SOURCE_TTL_SECONDS", 86400, minimum=300, maximum=604800)
    removed = 0
    paths = []
    for owner in db.scalars(select(Tenant.id).where(Tenant.status == "active")):
        staging = root / "tenants" / str(owner) / ".pyp-uploading"
        paths.extend((path, owner, staging.resolve()) for path in staging.glob("*.part"))
    try:
        legacy_owner = require_single_tenant(db).id
    except TenantContextError:
        legacy_owner = None
    if legacy_owner:
        staging = root / ".pyp-uploading"
        paths.extend((path, legacy_owner, staging.resolve()) for path in staging.glob("*.part"))
    for path, tenant_id, staging in paths:
        if removed >= limit:
            break
        try:
            if path.is_symlink() or path.resolve().parent != staging or path.stat().st_mtime >= cutoff:
                continue
            UUID(path.stem)  # apenas nomes produzidos pela escrita atômica
            require_active_owner(db, tenant_id)
            if staging != (root / ".pyp-uploading").resolve() and staging != (root / "tenants" / str(tenant_id) / ".pyp-uploading"):
                continue  # symlink de diretório não escolhe outra conta
            if legacy_owner == tenant_id and path.parent == root / ".pyp-uploading":
                require_single_tenant(db)
            path.unlink(missing_ok=True)
            removed += 1
        except (OSError, ValueError, HTTPException):
            continue
    return removed
