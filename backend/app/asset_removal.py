"""Exclusão de acervo com metadados comerciais e limpeza física duráveis."""

from pathlib import Path

from sqlalchemy import delete, func, select, update

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    AssetFileCleanup,
    Client,
    CommercialHistoryMedia,
    DerivedGallery,
    DerivedGalleryPhoto,
    DerivedGalleryPhotoOrigin,
    GalleryAccess,
    MediaDerivative,
    ParentGallery,
    PaymentGroup,
    PhotoAsset,
    PhotoComment,
    PhotoFavorite,
    PhotoFolder,
    PhotoSelection,
    PhotoView,
    RemovedPhotoMovement,
    SaleOrder,
    SaleOrderItem,
    now,
)
from app.commercial_history import materialize_commercial_history
from app.historical_media import historical_media_path, history_root
from app.media import derivatives_root, source_root

MOVEMENTS = (("selected", PhotoSelection), ("favorited", PhotoFavorite),
             ("viewed", PhotoView), ("commented", PhotoComment))


def lock_removal_clients(db, parent_id, *, tenant_id):
    """Mesmo primeiro lock que checkout, antes de pasta/foto/galeria."""
    if not owned_record(db, ParentGallery, parent_id, tenant_id=tenant_id):
        raise ValueError("Galeria indisponível.")
    ids = select(DerivedGallery.client_id).where(DerivedGallery.tenant_id == tenant_id).where(DerivedGallery.parent_gallery_id == parent_id)
    from app.auth import DerivedGalleryMembership
    members = select(DerivedGalleryMembership.client_id).where(DerivedGalleryMembership.tenant_id == tenant_id).where(
        DerivedGalleryMembership.parent_gallery_id == parent_id)
    orders = select(SaleOrder.client_id).where(SaleOrder.tenant_id == tenant_id).where(SaleOrder.parent_gallery_id_snapshot == parent_id)
    list(db.scalars(select(Client).where(Client.tenant_id == tenant_id).where(Client.id.in_(ids.union(members, orders)))
                    .order_by(Client.id).with_for_update()))


def preserve_asset_history(db, parent_id, *, tenant_id, photo_ids=None, gallery_ids=None):
    """Snapshot idempotente, sem substituir o estado financeiro ou consumir mídia."""
    lock_removal_clients(db, parent_id, tenant_id=tenant_id)
    parent = owned_record(db, ParentGallery, parent_id, tenant_id=tenant_id)
    galleries = {g.id: g for g in db.scalars(select(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id).where(
        DerivedGallery.parent_gallery_id == parent_id))}
    scope_ids = list(gallery_ids) if gallery_ids is not None else list(galleries)
    for kind, model in MOVEMENTS:
        query = select(model).where(model.tenant_id == tenant_id).where(model.derived_gallery_id.in_(scope_ids))
        if photo_ids is not None:
            query = query.where(model.photo_asset_id.in_(photo_ids))
        for movement in db.scalars(query):
            if db.scalar(select(RemovedPhotoMovement.id).where(RemovedPhotoMovement.tenant_id == tenant_id).where(
                RemovedPhotoMovement.kind == kind, RemovedPhotoMovement.source_id == movement.id)):
                continue
            photo = owned_record(db, PhotoAsset, movement.photo_asset_id, tenant_id=tenant_id)
            gallery = galleries.get(movement.derived_gallery_id)
            if not photo or not gallery or not parent:
                raise ValueError("Movimento sem contexto textual para preservação.")
            folder = owned_record(db, PhotoFolder, photo.folder_id, tenant_id=tenant_id)
            db.add(RemovedPhotoMovement(
                tenant_id=tenant_id,
                source_id=movement.id, kind=kind, client_id=movement.client_id,
                parent_gallery_id=parent_id, derived_gallery_id=gallery.id, photo_id=photo.id,
                parent_gallery_name=parent.name, gallery_name=gallery.name,
                folder_name=folder.name if folder else "Pasta removida",
                filename=photo.display_name or photo.filename,
                occurred_at=movement.first_viewed_at if kind == "viewed" else movement.created_at))
    order_query = select(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(SaleOrder.parent_gallery_id_snapshot == parent_id)
    if gallery_ids is not None:
        order_query = order_query.where(SaleOrder.derived_gallery_id_snapshot.in_(scope_ids))
    if photo_ids is not None:
        order_query = order_query.where(SaleOrder.id.in_(select(SaleOrderItem.sale_order_id).where(SaleOrderItem.tenant_id == tenant_id).where(
            SaleOrderItem.photo_asset_id_snapshot.in_(photo_ids))))
    orders = list(db.scalars(order_query.order_by(SaleOrder.id).with_for_update()))
    # A materialização preenche apenas campos ausentes, preservando todo snapshot existente.
    for order in orders:
        materialize_commercial_history(db, parent_gallery_id=parent_id, client_id=order.client_id)
        order.assets_removed_at = order.assets_removed_at or now()
        if order.payment_group_id:
            group = owned_record(db, PaymentGroup, order.payment_group_id, tenant_id=tenant_id)
            if group and group.state == "draft":
                group.state = "unavailable"
                for member in db.scalars(select(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(
                    SaleOrder.payment_group_id == group.id).order_by(SaleOrder.id).with_for_update()):
                    member.assets_removed_at = member.assets_removed_at or now()
    db.flush()


def historical_paths(db, photo_ids=None, *, tenant_id, gallery_ids=None, parent_id=None):
    require_active_owner(db, tenant_id)
    if photo_ids is None and gallery_ids is None and parent_id is None:
        raise ValueError("Alvo de limpeza obrigatório.")
    paths = []
    items = select(SaleOrderItem.id).where(SaleOrderItem.tenant_id == tenant_id)
    if photo_ids is not None:
        items = items.where(SaleOrderItem.photo_asset_id_snapshot.in_(photo_ids))
    if gallery_ids is not None:
        items = items.where(SaleOrderItem.sale_order_id.in_(select(SaleOrder.id).where(SaleOrder.tenant_id == tenant_id).where(
            SaleOrder.derived_gallery_id_snapshot.in_(gallery_ids))))
    if parent_id is not None:
        items = items.where(SaleOrderItem.sale_order_id.in_(select(SaleOrder.id).where(SaleOrder.tenant_id == tenant_id).where(
            SaleOrder.parent_gallery_id_snapshot == parent_id)))
    for media in db.scalars(select(CommercialHistoryMedia).where(CommercialHistoryMedia.tenant_id == tenant_id).where(
        CommercialHistoryMedia.sale_order_item_id.in_(items))):
        for key in (media.preview_storage_key, media.delivery_storage_key):
            if key:
                paths.append(historical_media_path(key, tenant_id=tenant_id, item_id=media.sale_order_item_id))
        media.status = "purged"
        media.preview_storage_key = None
        media.delivery_storage_key = None
        media.purged_at = now()
    return paths


def enqueue_file_cleanup(db, paths, *, tenant_id):
    require_active_owner(db, tenant_id)
    roots = {"source": source_root(), "derivatives": derivatives_root(), "history": history_root()}
    entries = set()
    for raw in paths:
        path = Path(raw).resolve()
        for kind, root in roots.items():
            if path.is_relative_to(root) and path != root:
                relative = path.relative_to(root).as_posix()
                if relative.startswith("tenants/") and not relative.startswith(f"tenants/{tenant_id}/"):
                    raise ValueError("Caminho de exclusão fora do armazenamento autorizado.")
                entries.add((kind, relative))
                break
        else:
            raise ValueError("Caminho de exclusão fora do armazenamento autorizado.")
    job = AssetFileCleanup(tenant_id=tenant_id, paths=[{"root": kind, "path": path} for kind, path in sorted(entries)])
    db.add(job)
    db.flush()
    return job


def validate_cleanup_paths(db, paths, *, tenant_id):
    """Preflight integral: legado não pode colidir com referência viva de B."""
    require_active_owner(db, tenant_id)
    roots = {"source": source_root(), "derivatives": derivatives_root(), "history": history_root()}
    foreign_columns = {
        "source": [(PhotoAsset, PhotoAsset.storage_key)],
        "derivatives": [(MediaDerivative, MediaDerivative.relative_path)],
        "history": [(CommercialHistoryMedia, CommercialHistoryMedia.preview_storage_key),
                    (CommercialHistoryMedia, CommercialHistoryMedia.delivery_storage_key)],
    }
    targets = {Path(path).resolve() for path in paths}
    for path in targets:
        for root in roots.values():
            if path.is_relative_to(root) and path != root:
                relative = path.relative_to(root).as_posix()
                if relative.startswith("tenants/") and not relative.startswith(f"tenants/{tenant_id}/"):
                    raise ValueError("Caminho inválido")
                break
        else:
            raise ValueError("Caminho inválido")
    for kind, columns in foreign_columns.items():
        root = roots[kind]
        if not any(path.is_relative_to(root) for path in targets):
            continue
        for model, column in columns:
            for key in db.scalars(select(column).where(model.tenant_id != tenant_id, column.is_not(None))):
                if (root / key).resolve() in targets:
                    raise ValueError("Caminho inválido")


def process_file_cleanup(db, job, *, commit=True):
    current = owned_record(db, AssetFileCleanup, job.id, tenant_id=job.tenant_id)
    if not current:
        raise ValueError("Limpeza indisponível.")
    job = current
    roots = {"source": source_root(), "derivatives": derivatives_root(), "history": history_root()}
    job.attempts += 1
    try:
        paths = []
        for entry in job.paths:
            if entry["path"].startswith("tenants/") and not entry["path"].startswith(f"tenants/{job.tenant_id}/"):
                raise ValueError("Caminho inválido")
            root = roots[entry["root"]]
            path = (root / entry["path"]).resolve()
            if not path.is_relative_to(root) or path == root:
                raise ValueError("Caminho inválido")
            if path.relative_to(root).as_posix().startswith("tenants/") and not path.relative_to(root).as_posix().startswith(f"tenants/{job.tenant_id}/"):
                raise ValueError("Caminho inválido")
            paths.append(path)
        validate_cleanup_paths(db, paths, tenant_id=job.tenant_id)
        for path in paths:
            require_active_owner(db, job.tenant_id)
            path.unlink(missing_ok=True)
        job.status, job.last_error, job.completed_at = "completed", None, now()
    except (OSError, ValueError, KeyError):
        job.status = "failed"
        job.last_error = "Limpeza de arquivos pendente; será repetida pelo worker."
    if commit:
        db.commit()
    return job.status == "completed"


def delete_private_records(db, gallery_ids, *, tenant_id):
    """Somente vínculos; uploads próprios devem ser removidos antes desta etapa."""
    require_active_owner(db, tenant_id)
    for _kind, model in MOVEMENTS:
        db.execute(delete(model).where(model.tenant_id == tenant_id).where(model.derived_gallery_id.in_(gallery_ids)))
    refs = select(DerivedGalleryPhoto.id).where(DerivedGalleryPhoto.tenant_id == tenant_id).where(DerivedGalleryPhoto.derived_gallery_id.in_(gallery_ids))
    db.execute(delete(DerivedGalleryPhotoOrigin).where(DerivedGalleryPhotoOrigin.tenant_id == tenant_id).where(
        DerivedGalleryPhotoOrigin.derived_gallery_photo_id.in_(refs)))
    db.execute(delete(DerivedGalleryPhoto).where(DerivedGalleryPhoto.tenant_id == tenant_id).where(DerivedGalleryPhoto.derived_gallery_id.in_(gallery_ids)))
    db.execute(delete(GalleryAccess).where(GalleryAccess.tenant_id == tenant_id).where(GalleryAccess.gallery_id.in_(gallery_ids)))
    # Também funciona em fixtures SQLite sem ações referenciais ativadas.
    db.execute(update(SaleOrder).where(SaleOrder.tenant_id == tenant_id).where(SaleOrder.derived_gallery_id.in_(gallery_ids))
               .values(derived_gallery_id=None))
    from app.auth import DerivedGalleryMembership, GalleryAccessCapability, NotificationEvent
    # Financeiro/notificações não podem desaparecer por CASCADE da galeria.
    db.execute(update(NotificationEvent).where(NotificationEvent.tenant_id == tenant_id).where(NotificationEvent.derived_gallery_id.in_(gallery_ids))
               .values(derived_gallery_id=None))
    db.execute(delete(GalleryAccessCapability).where(GalleryAccessCapability.tenant_id == tenant_id).where(GalleryAccessCapability.derived_gallery_id.in_(gallery_ids)))
    db.execute(delete(DerivedGalleryMembership).where(DerivedGalleryMembership.tenant_id == tenant_id).where(DerivedGalleryMembership.derived_gallery_id.in_(gallery_ids)))
    db.execute(delete(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id).where(PhotoFolder.derived_gallery_id.in_(gallery_ids)))
    db.execute(delete(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id).where(DerivedGallery.id.in_(gallery_ids)))


def removed_movements_payload(db, *, tenant_id, client_id=None, parent_gallery_id=None, query=None,
                             created_from=None, created_to=None, limit=None, offset=0,
                             include_identity=False):
    require_active_owner(db, tenant_id)
    statement = select(RemovedPhotoMovement, Client.full_name).join(
        Client, (Client.id == RemovedPhotoMovement.client_id) & (Client.tenant_id == tenant_id),
    ).where(RemovedPhotoMovement.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(RemovedPhotoMovement.client_id == client_id)
    if parent_gallery_id:
        statement = statement.where(RemovedPhotoMovement.parent_gallery_id == parent_gallery_id)
    if query:
        statement = statement.where(func.lower(Client.full_name).contains(query.strip().lower()))
    if created_from:
        statement = statement.where(RemovedPhotoMovement.occurred_at >= created_from)
    if created_to:
        statement = statement.where(RemovedPhotoMovement.occurred_at <= created_to)
    statement = statement.order_by(RemovedPhotoMovement.occurred_at.desc(), RemovedPhotoMovement.id)
    if limit is not None:
        statement = statement.limit(limit).offset(offset)
    return [{"id": str(row.id), "kind": row.kind, "client_name": name,
             **({"client_id": str(row.client_id), "parent_gallery_id": str(row.parent_gallery_id)}
                if include_identity else {}),
             "gallery_name": row.gallery_name, "parent_gallery_name": row.parent_gallery_name,
             "folder_name": row.folder_name, "filename": row.filename,
             "occurred_at": row.occurred_at.isoformat(), "removed_at": row.removed_at.isoformat()}
            for row, name in db.execute(statement)]


def removed_movements_page(db, *, tenant_id, limit=25, offset=0, **filters):
    items = removed_movements_payload(db, tenant_id=tenant_id, limit=limit + 1, offset=offset,
                                     include_identity=True, **filters)
    galleries = db.execute(select(RemovedPhotoMovement.parent_gallery_id,
        func.min(RemovedPhotoMovement.parent_gallery_name).label("name"))
        .where(RemovedPhotoMovement.tenant_id == tenant_id)
        .group_by(RemovedPhotoMovement.parent_gallery_id).order_by("name", RemovedPhotoMovement.parent_gallery_id))
    return {"items": items[:limit], "page": {"offset": offset, "limit": limit, "has_more": len(items) > limit},
            "galleries": [{"id": str(gallery_id), "name": name} for gallery_id, name in galleries]}
