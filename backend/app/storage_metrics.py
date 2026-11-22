"""Medição agregada e segura das raízes fotográficas do Pick-your-Pic."""

from __future__ import annotations

import stat
from collections import OrderedDict
from dataclasses import dataclass, field
from os import walk
from pathlib import Path
from threading import Lock
from time import monotonic
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import require_active_owner
from app.auth import CommercialHistoryMedia, MediaDerivative, PhotoAsset
from app.historical_media import history_root
from app.media import derivatives_root, media_namespace, source_root

CACHE_TTL_SECONDS = 30.0
OWNED_CACHE_MAX_ENTRIES = 128


@dataclass(frozen=True)
class PhotoStorageMeasurement:
    bytes: int | None
    available: bool


_cache_lock = Lock()
_cache: tuple[float, tuple[str, ...], PhotoStorageMeasurement] | None = None


@dataclass
class _OwnedCacheEntry:
    lock: Lock = field(default_factory=Lock)
    measured_at: float = 0.0
    measurement: PhotoStorageMeasurement | None = None


_owned_cache: OrderedDict[tuple[object, UUID, tuple[Path, ...]], _OwnedCacheEntry] = OrderedDict()


def clear_storage_usage_cache() -> None:
    """Descarta a memória curta; usado após mutações e por testes focados."""
    global _cache
    with _cache_lock:
        _cache = None
        _owned_cache.clear()


def _configured_roots() -> tuple[Path, ...]:
    return tuple(dict.fromkeys((source_root(), derivatives_root(), history_root())))


def _scan_regular_files(root: Path) -> int:
    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        return 0
    if not stat.S_ISDIR(root_stat.st_mode):
        raise OSError("A raiz fotográfica configurada não é um diretório seguro.")

    total = 0

    def raise_walk_error(error: OSError) -> None:
        raise error

    for current, directory_names, file_names in walk(
        root, topdown=True, onerror=raise_walk_error, followlinks=False
    ):
        current_path = Path(current)
        directory_names[:] = [
            name for name in directory_names if not (current_path / name).is_symlink()
        ]
        for name in file_names:
            file_path = current_path / name
            file_stat = file_path.lstat()
            if stat.S_ISREG(file_stat.st_mode):
                total += file_stat.st_size
    return total


def measure_photo_storage() -> PhotoStorageMeasurement:
    """Soma arquivos regulares sem publicar totais parciais em caso de falha."""
    global _cache
    roots = _configured_roots()
    cache_key = tuple(str(root) for root in roots)
    measured_at = monotonic()
    with _cache_lock:
        cached = _cache
        if (
            cached is not None
            and cached[1] == cache_key
            and measured_at - cached[0] < CACHE_TTL_SECONDS
        ):
            return cached[2]

    try:
        measurement = PhotoStorageMeasurement(
            bytes=sum(_scan_regular_files(root) for root in roots),
            available=True,
        )
    except OSError:
        measurement = PhotoStorageMeasurement(bytes=None, available=False)

    with _cache_lock:
        _cache = (measured_at, cache_key, measurement)
    return measurement


def _owned_path(root: Path, key: str, tenant_id: UUID, *, item_id: UUID | None = None) -> Path:
    """Valida a chave original e o destino físico dentro da mesma raiz/conta/item."""
    media_namespace(key, tenant_id)
    resolved = (root / key).resolve()
    resolved_key = resolved.relative_to(root).as_posix()
    media_namespace(resolved_key, tenant_id)
    if item_id is not None:
        prefixes = (f"items/{item_id}/", f"tenants/{tenant_id}/items/{item_id}/")
        if not key.startswith(prefixes) or not resolved_key.startswith(prefixes):
            raise ValueError("Caminho de histórico inválido.")
    return resolved


def _measure_owned_photo_storage(
    db: Session, tenant_id: UUID, roots: tuple[Path, ...],
) -> PhotoStorageMeasurement:
    from app.preview_adjustment.cleanup import photo_files

    source, derivatives, history = roots
    paths: set[tuple[Path, str, UUID | None]] = set()
    try:
        for photo_id, key in db.execute(select(PhotoAsset.id, PhotoAsset.storage_key).where(
            PhotoAsset.tenant_id == tenant_id,
        )):
            paths.add((source, key, None))
            paths.update((derivatives, path.relative_to(derivatives).as_posix(), None)
                         for path in photo_files(photo_id, tenant_id=tenant_id))
        for key in db.scalars(select(MediaDerivative.relative_path).where(
            MediaDerivative.tenant_id == tenant_id, MediaDerivative.relative_path.is_not(None)
        )):
            paths.add((derivatives, key, None))
        for item_id, preview_key, delivery_key in db.execute(select(
            CommercialHistoryMedia.sale_order_item_id,
            CommercialHistoryMedia.preview_storage_key,
            CommercialHistoryMedia.delivery_storage_key,
        ).where(CommercialHistoryMedia.tenant_id == tenant_id)):
            paths.update((history, key, item_id) for key in (preview_key, delivery_key) if key)
        total = 0
        seen: set[Path] = set()
        for root, key, item_id in paths:
            resolved = _owned_path(root, key, tenant_id, item_id=item_id)
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                info = resolved.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode):
                raise OSError("Arquivo fotográfico não regular.")
            total += info.st_size
        return PhotoStorageMeasurement(bytes=total, available=True)
    except (OSError, ValueError):
        return PhotoStorageMeasurement(bytes=None, available=False)


def measure_owned_photo_storage(db: Session, *, tenant_id: UUID) -> PhotoStorageMeasurement:
    """Snapshot curto próprio; autoriza inclusive cache hit e revalida antes de responder."""
    require_active_owner(db, tenant_id)
    try:
        roots = (source_root(), derivatives_root(), history_root())
    except (OSError, ValueError):
        require_active_owner(db, tenant_id)
        return PhotoStorageMeasurement(bytes=None, available=False)
    key = (db.get_bind(), tenant_id, roots)
    with _cache_lock:
        entry = _owned_cache.get(key)
        if entry is None:
            entry = _OwnedCacheEntry()
            _owned_cache[key] = entry
            if len(_owned_cache) > OWNED_CACHE_MAX_ENTRIES:
                _owned_cache.popitem(last=False)
        _owned_cache.move_to_end(key)
    # A coleta não mantém o lock global nem reutiliza Session de outra chamada.
    with entry.lock:
        measured_at = monotonic()
        if entry.measurement is not None and measured_at - entry.measured_at < CACHE_TTL_SECONDS:
            measurement = entry.measurement
        else:
            measurement = _measure_owned_photo_storage(db, tenant_id, roots)
        require_active_owner(db, tenant_id)
        if measurement.available:
            if measurement is not entry.measurement:
                entry.measured_at = measured_at
                entry.measurement = measurement
        else:
            entry.measurement = None
        return measurement
