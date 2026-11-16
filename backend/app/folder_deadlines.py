"""Regras de prazo inicial de acesso por pasta de conteúdo."""

from datetime import datetime, timedelta

from app.auth import PhotoFolder, now
from app.folder_access import REOPENING_WINDOW


def validate_access_duration_days(value: int) -> int:
    """Recusa prazo que não comporte expiração e janela de arquivo em datetime."""
    try:
        _ = now() + timedelta(days=value) + REOPENING_WINDOW
    except OverflowError:
        raise ValueError("Informe uma duração válida em dias.") from None
    return value


def start_folder_access_deadline(folder: PhotoFolder, released_at: datetime | None = None) -> None:
    """Inicia o prazo configurado quando a primeira prévia fica disponível."""
    if folder.released_at is not None:
        return
    release_time = released_at or now()
    folder.released_at = release_time
    if folder.access_duration_days is not None:
        folder.access_expires_at = release_time + timedelta(days=folder.access_duration_days)
