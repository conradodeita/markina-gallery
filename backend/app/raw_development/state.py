"""Contratos determinísticos do ciclo de vida da conversão RAW."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select

from app.auth import MediaJob, PhotoAsset, RawDevelopmentJob, RawDevelopmentSettings, expired, now


def staging_root() -> Path:
    return Path(os.getenv("RAW_DEVELOPMENT_ROOT", "./media/raw-staging")).resolve()


def raw_staging_path(key: str) -> Path:
    root = staging_root()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or Path(key).name != key:
        raise RawDevelopmentStateError("Caminho temporário inválido.")
    return path


def engine_formats(engine: str) -> set[str]:
    from app.raw_development.settings import _engine_formats

    return set(_engine_formats(engine))


def pending_raw_photo_ids(db, folder_id, *, tenant_id, exclude_photo_id=None) -> set:
    """RAWs registrados, em conversão ou sem derivados prontos impedem liberar a pasta."""
    rows = db.execute(
        select(
            PhotoAsset.id,
            PhotoAsset.filename,
            RawDevelopmentJob.status,
            MediaJob.status,
        )
        .outerjoin(RawDevelopmentJob, (RawDevelopmentJob.photo_asset_id == PhotoAsset.id) &
                   (RawDevelopmentJob.tenant_id == PhotoAsset.tenant_id))
        .outerjoin(MediaJob, (MediaJob.photo_asset_id == PhotoAsset.id) &
                   (MediaJob.tenant_id == PhotoAsset.tenant_id))
        .where(PhotoAsset.tenant_id == tenant_id, PhotoAsset.folder_id == folder_id)
    )
    pending = set()
    for photo_id, filename, raw_status, media_status in rows:
        if photo_id == exclude_photo_id or Path(filename or "").suffix.lower() not in RAW_SUFFIXES:
            continue
        if (
            raw_status is None
            or raw_status in {"receiving", "queued", "processing"}
            or (raw_status == "ready" and media_status != "completed")
        ):
            pending.add(photo_id)
    return pending


async def receive_raw_upload(db, photo, request):
    """Admite um RAW em staging privado com quota e gravação atômica."""
    from app.raw_development.probe import validate_raw_signature

    tenant_id = photo.tenant_id
    setting = db.scalar(select(RawDevelopmentSettings).where(
        RawDevelopmentSettings.tenant_id == tenant_id, RawDevelopmentSettings.id == 1).with_for_update())
    if not setting or not setting.enabled:
        raise RawDevelopmentStateError("Envio RAW não está habilitado.")
    formats = engine_formats(setting.selected_engine)
    content_length = request.headers.get("content-length")
    declared_bytes = int(content_length) if content_length and content_length.isdigit() else 0
    suffix = Path(photo.filename).suffix.lower()
    if suffix not in formats:
        raise RawDevelopmentStateError("Formato RAW não habilitado para o motor selecionado.")
    if declared_bytes > RAW_MAX_UPLOAD_BYTES:
        raise RawDevelopmentStateError("Arquivo RAW excede o limite permitido.")

    existing = db.scalar(select(RawDevelopmentJob).where(
        RawDevelopmentJob.photo_asset_id == photo.id,
        RawDevelopmentJob.tenant_id == tenant_id).with_for_update())
    reprocess = request.headers.get("x-raw-reprocess") == "true"
    if existing and existing.status in {"receiving", "queued", "processing"}:
        return {"status": existing.status}
    if existing and existing.status == "ready" and not reprocess:
        return {"status": "ready"}

    count, total = db.execute(select(
        func.count(RawDevelopmentJob.photo_asset_id),
        func.coalesce(func.sum(RawDevelopmentJob.input_bytes), 0),
    ).where(RawDevelopmentJob.tenant_id == tenant_id,
            RawDevelopmentJob.status.in_(("receiving", "queued", "processing")))).one()
    reserved_bytes = max(declared_bytes, RAW_MAX_UPLOAD_BYTES)
    if count >= RAW_MAX_FILES or total + reserved_bytes > RAW_MAX_TOTAL_BYTES:
        raise RawDevelopmentStateError("Fila RAW temporariamente cheia.")

    key = f"{uuid4()}{suffix}"
    target = raw_staging_path(key)
    temporary = target.with_suffix(target.suffix + ".part")
    from app.raw_development.settings import _installed_versions

    version = _installed_versions().get(setting.selected_engine)
    if not version:
        raise RawDevelopmentStateError("O motor RAW não está instalado.")
    if existing:
        existing.status = "receiving"
        existing.last_error = None
        existing.staging_key = key
        existing.source_format = suffix[1:]
        existing.input_fingerprint = "0" * 64
        existing.input_bytes = RAW_MAX_UPLOAD_BYTES
        existing.engine = setting.selected_engine
        existing.engine_version = version
        existing.profile_version = "auto-v1"
        existing.attempts = 0
        existing.expires_at = now() + timedelta(seconds=RAW_TTL_SECONDS)
        existing.updated_at = now()
    else:
        existing = RawDevelopmentJob(
            photo_asset_id=photo.id,
            tenant_id=tenant_id,
            input_fingerprint="0" * 64,
            input_bytes=RAW_MAX_UPLOAD_BYTES,
            source_format=suffix[1:],
            staging_key=key,
            engine=setting.selected_engine,
            engine_version=version,
            profile_version="auto-v1",
            status="receiving",
            attempts=0,
            expires_at=now() + timedelta(seconds=RAW_TTL_SECONDS),
        )
        db.add(existing)
    db.commit()

    digest = sha256()
    size = 0
    header = bytearray()
    try:
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name != "nt":
            os.chmod(target.parent, 0o700)
        with temporary.open("xb") as stream:
            if os.name != "nt":
                os.chmod(temporary, 0o600)
            async_iterator = request.stream()
            async for chunk in async_iterator:
                if not chunk:
                    continue
                size += len(chunk)
                if size > RAW_MAX_UPLOAD_BYTES or total + size > RAW_MAX_TOTAL_BYTES:
                    raise RawDevelopmentStateError("Arquivo RAW excede o limite permitido.")
                digest.update(chunk)
                if len(header) < 32:
                    header.extend(chunk[:32 - len(header)])
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        if size == 0:
            raise RawDevelopmentStateError("Arquivo RAW vazio.")
        validate_raw_signature(photo.filename, bytes(header), supported_suffixes=formats)
        db.refresh(existing)
        if existing.status != "receiving" or existing.staging_key != key or expired(existing.expires_at):
            raise RawDevelopmentStateError("A reserva do envio RAW expirou.")
        temporary.replace(target)
        existing.input_fingerprint = digest.hexdigest()
        existing.input_bytes = size
        existing.status = "queued"
        existing.updated_at = now()
        db.commit()
        return {"status": "queued"}
    except Exception:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        db.rollback()
        failed = db.get(RawDevelopmentJob, (photo.id, tenant_id))
        if failed:
            failed.status = "failed"
            failed.last_error = "upload_invalid"
            failed.updated_at = now()
            db.commit()
        raise

RAW_SUFFIXES = frozenset({
    ".arw", ".cr2", ".cr3", ".dng", ".nef", ".nrw", ".raf", ".rw2", ".rwl", ".pef", ".orf",
})
RAW_MAX_UPLOAD_BYTES = 256 * 1024 * 1024
RAW_MAX_FILES = 64
RAW_MAX_TOTAL_BYTES = 2_000_000_000
RAW_TTL_SECONDS = 24 * 60 * 60
RAW_MAX_ATTEMPTS = 2
RAW_PROCESS_TIMEOUT_SECONDS = 15 * 60
RAW_MAX_OUTPUT_PIXELS = 40_000_000

RAW_STATES = frozenset({"receiving", "queued", "processing", "ready", "failed", "reupload_required"})
_TRANSITIONS = {
    "receiving": frozenset({"queued", "failed", "reupload_required"}),
    "queued": frozenset({"processing", "failed", "reupload_required"}),
    "processing": frozenset({"queued", "ready", "failed", "reupload_required"}),
    "ready": frozenset({"queued"}),  # novo reenvio explícito para desenvolver outra vez
    "failed": frozenset({"queued", "reupload_required"}),
    "reupload_required": frozenset({"queued"}),
}


class RawDevelopmentStateError(ValueError):
    pass


def require_raw_upload(filename: str, payload_bytes: int, *, supported_suffixes=None) -> None:
    """Valida o formato RAW anunciado pelo motor e o limite antes de reservar o upload."""
    from pathlib import PurePath

    suffixes = RAW_SUFFIXES if supported_suffixes is None else frozenset(supported_suffixes)
    if PurePath(filename).suffix.lower() not in suffixes:
        raise RawDevelopmentStateError("Formato RAW não habilitado.")
    if payload_bytes <= 0 or payload_bytes > RAW_MAX_UPLOAD_BYTES:
        raise RawDevelopmentStateError("Arquivo RAW excede o limite permitido.")


def require_transition(current: str, target: str) -> None:
    if current not in RAW_STATES or target not in _TRANSITIONS.get(current, frozenset()):
        raise RawDevelopmentStateError("Transição de desenvolvimento inválida.")


@dataclass(frozen=True)
class RawAdmission:
    engine: str
    engine_version: str
    profile_version: str
    attempts: int = 0

    def __post_init__(self) -> None:
        if self.engine not in {"rawtherapee", "lightcraft"}:
            raise RawDevelopmentStateError("Motor de desenvolvimento inválido.")
        if not self.engine_version or not self.profile_version:
            raise RawDevelopmentStateError("Versão do motor e perfil são obrigatórios.")
        if not 0 <= self.attempts <= RAW_MAX_ATTEMPTS:
            raise RawDevelopmentStateError("Limite de tentativas excedido.")
