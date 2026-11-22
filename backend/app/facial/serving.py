"""Contrato único de engine facial servido pelo produto."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.facial.config import FacialSettings

SFACE_MODEL_ID = "opencv-yunet-sface"


def gallery_search_engine(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID, settings: FacialSettings
) -> str:
    """Todas as consultas novas usam o índice SFace autorizado da galeria."""
    del db, parent_gallery_id, client_id, settings
    return SFACE_MODEL_ID
