"""Medição agregada e segura das raízes fotográficas da Markina Gallery."""

from __future__ import annotations

import stat
from dataclasses import dataclass
from os import walk
from pathlib import Path
from threading import Lock
from time import monotonic

from app.historical_media import history_root
from app.media import derivatives_root, source_root

CACHE_TTL_SECONDS = 30.0


@dataclass(frozen=True)
class PhotoStorageMeasurement:
    bytes: int | None
    available: bool


_cache_lock = Lock()
_cache: tuple[float, tuple[str, ...], PhotoStorageMeasurement] | None = None


def clear_storage_usage_cache() -> None:
    """Descarta a memória curta; usado após mutações e por testes focados."""
    global _cache
    with _cache_lock:
        _cache = None


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
