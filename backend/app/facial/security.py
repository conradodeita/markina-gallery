"""Controles de abuso sem persistir identidade ou endereço de rede em claro."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.auth import enforce_rate_limit, pii_fingerprint


def enforce_facial_search_rate_limit(
    db: Session,
    *,
    client_id: UUID,
    parent_gallery_id: UUID,
    ip_address: str,
) -> None:
    """Limita cada vínculo+rede e persiste somente fingerprints não reversíveis."""

    subject_fingerprint = pii_fingerprint(
        f"facial-search:{client_id}:{parent_gallery_id}"
    )
    network_fingerprint = pii_fingerprint(ip_address or "unknown")
    enforce_rate_limit(
        db,
        "facial_search_admission",
        subject_fingerprint,
        network_fingerprint,
    )
    # A tentativa precisa sobreviver a recusas posteriores de payload/capacidade;
    # a sessão não possui mutações de negócio antes deste ponto.
    db.commit()
