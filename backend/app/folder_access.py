"""Política de acesso, checkout e reabertura normal por pasta."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.auth import (
    GalleryReopeningRequest,
    MediaArchiveCycle,
    MediaArchiveObject,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    now,
)

REOPENING_WINDOW = timedelta(days=30)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)  # noqa: UP017


def _latest_reopening_expiry(
    db: Session,
    folder: PhotoFolder,
    *,
    client_id: UUID | None,
    include_all_clients: bool = False,
) -> datetime | None:
    query = select(GalleryReopeningRequest.approved_until).where(
        GalleryReopeningRequest.tenant_id == folder.tenant_id,
        GalleryReopeningRequest.photo_folder_id == folder.id,
        GalleryReopeningRequest.status == "approved",
        GalleryReopeningRequest.approved_until.is_not(None),
    )
    if not include_all_clients and (
        folder.derived_gallery_id is not None or folder.audience_scope == "selected"
    ):
        if client_id is None:
            return None
        query = query.where(GalleryReopeningRequest.requested_by_client_id == client_id)
    result = db.scalar(query.order_by(GalleryReopeningRequest.approved_until.desc()).limit(1))
    return result


def folder_effective_expiry(
    db: Session,
    folder: PhotoFolder,
    *,
    client_id: UUID | None,
    include_all_clients: bool = False,
) -> datetime | None:
    """Retorna o maior prazo base/reaberto, individual em pasta privada."""
    deadlines = [value for value in (
        folder.access_expires_at,
        _latest_reopening_expiry(
            db,
            folder,
            client_id=client_id,
            include_all_clients=include_all_clients,
        ),
    ) if value is not None]
    return max((_utc(value) for value in deadlines), default=None)


def latest_private_reopening_expiry(db: Session, folder: PhotoFolder) -> datetime | None:
    """Prazo privado mais recente entre todas as clientes, para elegibilidade física."""
    return _latest_reopening_expiry(
        db, folder, client_id=None, include_all_clients=True
    )


def folder_archive_eligible_at(db: Session, folder: PhotoFolder) -> datetime | None:
    """Instante após o qual termina a janela de reabertura normal da pasta."""
    expiry = folder_effective_expiry(
        db, folder, client_id=None, include_all_clients=True
    )
    if expiry is None:
        return None
    return expiry + REOPENING_WINDOW


def folder_reopening_allowed(
    db: Session,
    folder: PhotoFolder,
    *,
    client_id: UUID,
    at: datetime | None = None,
) -> bool:
    if folder.status != "released" or folder.purpose != "content" or not folder_media_is_local(db, folder):
        return False
    expiry = folder_effective_expiry(db, folder, client_id=client_id)
    current = _utc(at or now())
    if expiry is None:
        return False
    expiry = _utc(expiry)
    return expiry <= current <= expiry + REOPENING_WINDOW


def folder_selection_window_allows(
    *,
    expiry: datetime | None,
    selected_at: datetime | None,
    existing_order_created_at: datetime | None = None,
    existing_order_open: bool = False,
    at: datetime | None = None,
) -> bool:
    """Aplica a janela de checkout e prévia da seleção depois do vencimento."""
    current = _utc(at or now())
    if expiry is None:
        return True
    deadline = _utc(expiry)
    grace_ends_at = deadline + REOPENING_WINDOW
    if selected_at is not None:
        if _utc(selected_at) > deadline:
            return False
        if current <= grace_ends_at:
            return True
    if existing_order_created_at is None or _utc(existing_order_created_at) > grace_ends_at:
        return False
    return current <= grace_ends_at or existing_order_open


def folder_selected_media_preview_allowed(
    *,
    media_state: str,
    expiry: datetime | None,
    selected_at: datetime | None,
    existing_order_created_at: datetime | None = None,
    existing_order_open: bool = False,
    at: datetime | None = None,
) -> bool:
    """Só libera prévias com mídia local e prova de seleção ou pedido válido."""
    current = _utc(at or now())
    if media_state != "available":
        return False
    if expiry is None or _utc(expiry) >= current:
        return True
    return folder_selection_window_allows(
        expiry=expiry,
        selected_at=selected_at,
        existing_order_created_at=existing_order_created_at,
        existing_order_open=existing_order_open,
        at=current,
    )


def folder_selection_checkout_allowed(
    db: Session,
    folder: PhotoFolder,
    *,
    client_id: UUID,
    selected_at: datetime,
    existing_order_created_at: datetime | None = None,
    at: datetime | None = None,
) -> bool:
    """Mantém checkout somente de seleções anteriores ao vencimento, por 30 dias."""
    expiry = folder_effective_expiry(db, folder, client_id=client_id)
    return folder_selection_window_allows(
        expiry=expiry,
        selected_at=selected_at,
        existing_order_created_at=existing_order_created_at,
        existing_order_open=existing_order_created_at is not None,
        at=at,
    )


def public_folder_deadline_renewable(
    db: Session,
    folder: PhotoFolder,
    *,
    at: datetime | None = None,
    media_state: str | None = None,
) -> bool:
    """Renovação coletiva somente para pasta pública vencida e ainda disponível."""
    if (
        folder.purpose != "content" or folder.status != "released"
        or folder.released_at is None or folder.derived_gallery_id is not None
        or folder.audience_scope not in (None, "all")
    ):
        return False
    if (media_state if media_state is not None else folder_media_state(db, folder)) != "available":
        return False
    expiry = folder_effective_expiry(db, folder, client_id=None)
    if expiry is None:
        return False
    current = _utc(at or now())
    return expiry <= current <= expiry + REOPENING_WINDOW


def folder_media_is_local(db: Session, folder: PhotoFolder) -> bool:
    """Mídia arquivada, em restauração ou em reconciliação não pode ser servida."""
    return folder_media_state(db, folder) in {"available", "archiving"}


def folder_media_state(db: Session, folder: PhotoFolder) -> str:
    """Estado do ciclo mais recente sem transformar referências em inexistentes."""
    cycle = db.scalar(
        select(MediaArchiveCycle.state)
        .where(
            MediaArchiveCycle.tenant_id == folder.tenant_id,
            MediaArchiveCycle.folder_id == folder.id,
        )
        .order_by(MediaArchiveCycle.cycle_number.desc())
        .limit(1)
    )
    return "available" if cycle in (None, "local") else str(cycle)


def folder_media_state_by_id(
    db: Session, *, folder_id: UUID | None, tenant_id: UUID
) -> str:
    """Resolve estado por ID somente dentro do tenant informado."""
    if folder_id is None:
        return "unavailable"
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == folder_id,
        PhotoFolder.tenant_id == tenant_id,
        PhotoFolder.purpose == "content",
    ))
    return folder_media_state(db, folder) if folder else "unavailable"


def historical_folder_media_state_by_id(
    db: Session, *, folder_id: UUID | None, tenant_id: UUID,
) -> str:
    """Histórico local independe da pasta removida; catálogo frio segue vinculante."""
    if folder_id is None:
        return "available"
    state = db.scalar(select(MediaArchiveCycle.state).where(
        MediaArchiveCycle.tenant_id == tenant_id,
        MediaArchiveCycle.folder_id == folder_id,
    ).order_by(MediaArchiveCycle.cycle_number.desc()).limit(1))
    return "available" if state in (None, "local") else str(state)


def folder_media_states_by_id(
    db: Session, *, folder_ids: set[UUID], tenant_id: UUID
) -> dict[UUID, str]:
    """Resolve vários estados em uma consulta, mantendo ownership por tenant."""
    if not folder_ids:
        return {}
    latest_state = _latest_media_state_subquery(tenant_id)
    rows = db.execute(
        select(PhotoFolder.id, latest_state).where(
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.purpose == "content",
            PhotoFolder.id.in_(folder_ids),
        )
    )
    return {
        folder_id: "available" if state in (None, "local") else str(state)
        for folder_id, state in rows
    }


def _latest_media_state_subquery(tenant_id: UUID):
    return (
        select(MediaArchiveCycle.state)
        .where(
            MediaArchiveCycle.tenant_id == tenant_id,
            MediaArchiveCycle.folder_id == PhotoFolder.id,
        )
        .order_by(MediaArchiveCycle.cycle_number.desc())
        .limit(1)
        .correlate(PhotoFolder)
        .scalar_subquery()
    )


def _client_reopening_expiry_subquery(client_id: UUID):
    return (
        select(func.max(GalleryReopeningRequest.approved_until))
        .where(
            GalleryReopeningRequest.tenant_id == PhotoFolder.tenant_id,
            GalleryReopeningRequest.photo_folder_id == PhotoFolder.id,
            GalleryReopeningRequest.status == "approved",
            GalleryReopeningRequest.approved_until.is_not(None),
            or_(
                and_(
                    PhotoFolder.derived_gallery_id.is_not(None),
                    GalleryReopeningRequest.requested_by_client_id == client_id,
                ),
                and_(
                    PhotoFolder.derived_gallery_id.is_(None),
                    PhotoFolder.audience_scope == "selected",
                    GalleryReopeningRequest.requested_by_client_id == client_id,
                ),
                and_(
                    PhotoFolder.derived_gallery_id.is_(None),
                    or_(PhotoFolder.audience_scope.is_(None), PhotoFolder.audience_scope != "selected"),
                ),
            ),
        )
        .correlate(PhotoFolder)
        .scalar_subquery()
    )


def _effective_expiry(base_expiry: datetime | None, reopened_expiry: datetime | None) -> datetime | None:
    return max(
        (_utc(value) for value in (base_expiry, reopened_expiry) if value is not None),
        default=None,
    )


def folder_media_access_by_id(
    db: Session,
    *,
    folder_ids: set[UUID],
    tenant_id: UUID,
    client_id: UUID,
) -> dict[UUID, tuple[str, datetime | None]]:
    """Resolve estado e prazo de várias pastas em uma consulta tenant-scoped."""
    if not folder_ids:
        return {}
    rows = db.execute(
        select(
            PhotoFolder.id,
            _latest_media_state_subquery(tenant_id),
            PhotoFolder.access_expires_at,
            _client_reopening_expiry_subquery(client_id),
        ).where(
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.purpose == "content",
            PhotoFolder.id.in_(folder_ids),
        )
    )
    return {
        folder_id: (
            "available" if state in (None, "local") else str(state),
            _effective_expiry(base_expiry, reopened_expiry),
        )
        for folder_id, state, base_expiry, reopened_expiry in rows
    }


def photos_with_folder_media_access_by_id(
    db: Session,
    *,
    photo_ids: set[UUID],
    tenant_id: UUID,
    client_id: UUID,
) -> dict[UUID, tuple[PhotoAsset, str, datetime | None]]:
    """Carrega fotos e estado/prazo das pastas numa única consulta tenant-scoped."""
    if not photo_ids:
        return {}
    folder_match = and_(
        PhotoFolder.id == PhotoAsset.folder_id,
        PhotoFolder.tenant_id == tenant_id,
        PhotoFolder.purpose == "content",
    )
    rows = db.execute(
        select(
            PhotoAsset,
            PhotoFolder.id,
            _latest_media_state_subquery(tenant_id),
            PhotoFolder.access_expires_at,
            _client_reopening_expiry_subquery(client_id),
        )
        .outerjoin(PhotoFolder, folder_match)
        .where(PhotoAsset.tenant_id == tenant_id, PhotoAsset.id.in_(photo_ids))
    )
    result: dict[UUID, tuple[PhotoAsset, str, datetime | None]] = {}
    for photo, matched_folder_id, state, base_expiry, reopened_expiry in rows:
        if photo.folder_id is None:
            media_state, expiry = "available", None
        elif matched_folder_id is None:
            media_state, expiry = "unavailable", None
        else:
            media_state = "available" if state in (None, "local") else str(state)
            expiry = _effective_expiry(base_expiry, reopened_expiry)
        result[photo.id] = (photo, media_state, expiry)
    return result


def folder_effective_expiries_by_id(
    db: Session,
    *,
    folder_ids: set[UUID],
    tenant_id: UUID,
    client_id: UUID,
) -> dict[UUID, datetime | None]:
    """Resolve prazo base e reabertura aplicável para várias pastas em uma consulta."""
    if not folder_ids:
        return {}
    reopening_expiry = _client_reopening_expiry_subquery(client_id)
    rows = db.execute(
        select(PhotoFolder.id, PhotoFolder.access_expires_at, reopening_expiry).where(
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.purpose == "content",
            PhotoFolder.id.in_(folder_ids),
        )
    )
    return {
        folder_id: _effective_expiry(base_expiry, reopened_expiry)
        for folder_id, base_expiry, reopened_expiry in rows
    }


def folder_media_writes_allowed(db: Session, folder: PhotoFolder) -> bool:
    """Bloqueia mutações enquanto o snapshot ou a mídia estão fora do estado local."""
    if folder.purpose == "content":
        cycle = db.scalar(
            select(MediaArchiveCycle.state)
            .where(
                MediaArchiveCycle.tenant_id == folder.tenant_id,
                MediaArchiveCycle.folder_id == folder.id,
            )
            .order_by(MediaArchiveCycle.cycle_number.desc())
            .limit(1)
        )
        return cycle is None or cycle == "local"
    if folder.purpose == "cover_assets":
        return gallery_media_writes_allowed(
            db, tenant_id=folder.tenant_id, parent_gallery_id=folder.parent_gallery_id,
        )
    return True


def gallery_media_writes_allowed(db: Session, *, tenant_id: UUID, parent_gallery_id: UUID) -> bool:
    """Serializa alterações da capa com snapshots de conteúdo em andamento."""
    if db.scalar(
        select(MediaArchiveCycle.id)
        .where(
            MediaArchiveCycle.tenant_id == tenant_id,
            MediaArchiveCycle.parent_gallery_id == parent_gallery_id,
            MediaArchiveCycle.state.in_(
                ("archiving", "restoring", "reconciliation_required", "deleting")
            ),
        )
        .limit(1)
    ):
        return False
    latest_shared_cover_state = db.scalar(
        select(MediaArchiveCycle.state)
        .join(
            MediaArchiveObject,
            (MediaArchiveObject.cycle_id == MediaArchiveCycle.id)
            & (MediaArchiveObject.tenant_id == MediaArchiveCycle.tenant_id),
        )
        .where(
            MediaArchiveCycle.tenant_id == tenant_id,
            MediaArchiveCycle.parent_gallery_id == parent_gallery_id,
            MediaArchiveObject.object_type.in_(("cover_asset", "cover_thumbnail")),
        )
        .order_by(MediaArchiveCycle.created_at.desc(), MediaArchiveCycle.id.desc())
        .limit(1)
    )
    return latest_shared_cover_state in {None, "local"}


def lock_selected_content_folders(
    db: Session, *, tenant_id: UUID, client_id: UUID,
) -> list[PhotoFolder]:
    """Trava pastas selecionadas antes de congelar um pedido/seleção no checkout."""
    folder_ids = list(db.scalars(
        select(PhotoFolder.id)
        .join(PhotoAsset, PhotoAsset.folder_id == PhotoFolder.id)
        .join(
            PhotoSelection,
            (PhotoSelection.photo_asset_id == PhotoAsset.id)
            & (PhotoSelection.tenant_id == PhotoAsset.tenant_id),
        )
        .where(
            PhotoFolder.tenant_id == tenant_id,
            PhotoAsset.tenant_id == tenant_id,
            PhotoSelection.tenant_id == tenant_id,
            PhotoSelection.client_id == client_id,
            PhotoFolder.purpose == "content",
        )
        .distinct()
        .order_by(PhotoFolder.id)
    ))
    if not folder_ids:
        return []
    folders = list(db.scalars(
        select(PhotoFolder)
        .where(PhotoFolder.tenant_id == tenant_id, PhotoFolder.id.in_(folder_ids))
        .order_by(PhotoFolder.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ))
    if len(folders) != len(folder_ids) or any(
        not folder_media_is_local(db, folder) for folder in folders
    ):
        raise ValueError("Uma pasta selecionada não está disponível para checkout.")
    return folders


def folder_browsing_clause(client_id: UUID, *, at: datetime | None = None):
    """Condição SQL para navegação e prévias, respeitando reabertura individual."""
    current = at or now()
    public_reopened = select(GalleryReopeningRequest.id).where(
        GalleryReopeningRequest.tenant_id == PhotoFolder.tenant_id,
        GalleryReopeningRequest.photo_folder_id == PhotoFolder.id,
        GalleryReopeningRequest.status == "approved",
        GalleryReopeningRequest.approved_until > current,
        PhotoFolder.derived_gallery_id.is_(None),
        or_(PhotoFolder.audience_scope.is_(None), PhotoFolder.audience_scope == "all"),
    ).exists()
    private_reopened = select(GalleryReopeningRequest.id).where(
        GalleryReopeningRequest.tenant_id == PhotoFolder.tenant_id,
        GalleryReopeningRequest.photo_folder_id == PhotoFolder.id,
        GalleryReopeningRequest.requested_by_client_id == client_id,
        GalleryReopeningRequest.status == "approved",
        GalleryReopeningRequest.approved_until > current,
    ).exists()
    access_window_open = or_(
        PhotoFolder.access_expires_at.is_(None),
        PhotoFolder.access_expires_at > current,
        public_reopened,
        private_reopened,
    )
    latest_cycle_state = (
        select(MediaArchiveCycle.state)
        .where(
            MediaArchiveCycle.tenant_id == PhotoFolder.tenant_id,
            MediaArchiveCycle.folder_id == PhotoFolder.id,
        )
        .order_by(MediaArchiveCycle.cycle_number.desc())
        .limit(1)
        .scalar_subquery()
    )
    media_local = or_(
        latest_cycle_state.is_(None),
        latest_cycle_state.in_(("local", "archiving")),
    )
    return access_window_open & media_local
