"""Etapas concretas e idempotentes de limpeza operacional de galerias."""

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import (
    AuditEvent,
    AuthChallenge,
    DerivedGallery,
    DerivedGalleryMembership,
    GalleryAccess,
    GalleryAccessCapability,
    GalleryLifecycleOperation,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoComment,
    PhotoFavorite,
    PhotoFolder,
    PhotoSelection,
    PhotoView,
    minimize_client_challenge_pii,
)
from app.commercial_removal import apply_commercial_removal_policy
from app.media import derivatives_root, source_root


def prepare_lifecycle_history(db: Session, operation: GalleryLifecycleOperation) -> None:
    """Preserva histórico conforme o tipo de operação antes da etapa destrutiva."""

    if operation.operation_type == "unlink_client":
        private_id = db.scalar(
            select(DerivedGalleryMembership.derived_gallery_id).where(
                DerivedGalleryMembership.parent_gallery_id
                == operation.target_parent_gallery_id,
                DerivedGalleryMembership.client_id == operation.target_client_id,
            )
        )
        if private_id is None:
            private_id = db.scalar(
                select(DerivedGallery.id).where(
                    DerivedGallery.parent_gallery_id
                    == operation.target_parent_gallery_id,
                    DerivedGallery.client_id == operation.target_client_id,
                )
            )
        report = apply_commercial_removal_policy(
            db,
            parent_gallery_id=operation.target_parent_gallery_id,
            client_id=operation.target_client_id,
            derived_gallery_id=private_id,
        )
        manifest = dict(operation.manifest or {})
        manifest["history_preparation"] = {
            "confirmed_orders": report.confirmed_orders,
            "cancelled_pending_orders": report.cancelled_pending_orders,
        }
        operation.manifest = manifest
        return

    from app.asset_removal import preserve_asset_history
    preserve_asset_history(db, operation.target_parent_gallery_id)
    manifest = dict(operation.manifest or {})
    manifest["history_policy"] = "text-only-v1"
    operation.manifest = manifest


def _delete_count(db: Session, model, *criteria) -> int:
    result = db.execute(delete(model).where(*criteria).execution_options(synchronize_session=False))
    return result.rowcount or 0


def _manifest_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Manifesto contém caminho operacional inválido.") from exc
    return candidate


def remove_operational_storage(_db: Session, operation: GalleryLifecycleOperation) -> None:
    """Remove somente arquivos operacionais congelados no manifesto da operação."""

    manifest = dict(operation.manifest or {})
    storage_manifest = manifest.get("operational_storage")
    if not isinstance(storage_manifest, dict):
        raise TypeError("Manifesto de armazenamento operacional ausente.")
    source_entries = storage_manifest.get("sources", [])
    derivative_entries = storage_manifest.get("derivatives", [])
    paths: list[Path] = []
    source_base = source_root()
    derivative_base = derivatives_root()
    for entry in source_entries:
        paths.append(_manifest_path(source_base, entry["storage_key"]))
    for entry in derivative_entries:
        paths.append(_manifest_path(derivative_base, entry["relative_path"]))

    from app.historical_media import historical_media_path
    paths.extend(historical_media_path(entry["relative_path"]) for entry in storage_manifest.get("history", []))

    removed_files = 0
    missing_files = 0
    for path in paths:
        if path.is_file():
            path.unlink()
            removed_files += 1
        elif path.exists():
            raise ValueError("Manifesto operacional aponta para item não regular.")
        else:
            missing_files += 1
    manifest["storage_cleanup"] = {
        "expected_files": len(paths),
        "removed_files": removed_files,
        "missing_files": missing_files,
    }
    operation.manifest = manifest


def remove_operational_records(db: Session, operation: GalleryLifecycleOperation) -> None:
    """Remove o grafo operacional da origem; histórico e cliente ficam fora do alvo."""

    if operation.operation_type == "unlink_client":
        _remove_client_link_records(db, operation)
        return
    if operation.operation_type != "delete_parent_gallery":
        raise ValueError("Tipo de operação de ciclo de vida inválido.")
    parent_id = operation.target_parent_gallery_id
    from app.asset_removal import (
        delete_private_records,
        enqueue_file_cleanup,
        historical_paths,
        preserve_asset_history,
        process_file_cleanup,
    )
    from app.facial.purge import purge_gallery_records
    from app.main import _delete_photo_records

    # Idempotente também na retomada de uma operação anterior à nova política.
    preserve_asset_history(db, parent_id)
    purge_gallery_records(db, parent_gallery_id=parent_id)
    private_ids = list(db.scalars(select(DerivedGallery.id).where(DerivedGallery.parent_gallery_id == parent_id)))
    photos = list(db.scalars(select(PhotoAsset).where(PhotoAsset.parent_gallery_id == parent_id)
                            .order_by(PhotoAsset.id).with_for_update()))
    paths = historical_paths(db, parent_id=parent_id)
    for photo in photos:
        paths.extend(_delete_photo_records(db, photo))
    db.flush()
    delete_private_records(db, private_ids)
    removed_folders = _delete_count(db, PhotoFolder, PhotoFolder.parent_gallery_id == parent_id)
    _delete_count(db, GalleryAccessCapability, GalleryAccessCapability.parent_gallery_id == parent_id)
    _delete_count(db, ParentGalleryRegistration, ParentGalleryRegistration.parent_gallery_id == parent_id)
    for challenge in db.scalars(select(AuthChallenge).where(AuthChallenge.parent_gallery_id == parent_id)):
        if challenge.kind == "client_otp":
            minimize_client_challenge_pii(db, challenge)
    _delete_count(db, AuthChallenge, AuthChallenge.parent_gallery_id == parent_id)
    parent = db.get(ParentGallery, parent_id)
    if parent:
        parent.active, parent.lifecycle_status, parent.cover_photo_id = False, "deleted", None
    cleanup = enqueue_file_cleanup(db, paths)
    if not process_file_cleanup(db, cleanup, commit=False):
        raise OSError("Não foi possível concluir a limpeza física do acervo.")
    manifest = dict(operation.manifest or {})
    manifest["file_cleanup_id"] = str(cleanup.id)
    manifest["removed_records"] = {"photos": len(photos), "folders": removed_folders,
                                   "private_galleries": len(private_ids), "public_origins": int(parent is not None)}
    operation.manifest = manifest
    db.add(AuditEvent(event="parent_gallery.operational_records_removed", subject=f"operation_id:{operation.id}"))


def _remove_client_link_records(db: Session, operation: GalleryLifecycleOperation) -> None:
    parent_id = operation.target_parent_gallery_id
    client_id = operation.target_client_id
    if not client_id:
        raise ValueError("Operação de desvinculação sem cliente alvo.")
    membership = db.scalar(
        select(DerivedGalleryMembership).where(
            DerivedGalleryMembership.parent_gallery_id == parent_id,
            DerivedGalleryMembership.client_id == client_id,
        )
    )
    private_ids = [membership.derived_gallery_id] if membership else list(
        db.scalars(
            select(DerivedGallery.id).where(
                DerivedGallery.parent_gallery_id == parent_id,
                DerivedGallery.client_id == client_id,
            )
        )
    )
    removed: dict[str, int] = {}
    for name, model in (
        ("comments", PhotoComment),
        ("favorites", PhotoFavorite),
        ("views", PhotoView),
        ("selections", PhotoSelection),
    ):
        removed[name] = (
            _delete_count(
                db,
                model,
                model.derived_gallery_id.in_(private_ids),
                model.client_id == client_id,
            )
            if private_ids
            else 0
        )
    # Preço e PIX pertencem à Galeria pública e não ao vínculo removido.
    removed["price_rules"] = 0
    removed["pix_settings"] = 0
    removed["available_references"] = 0
    removed["legacy_access"] = (
        _delete_count(
            db,
            GalleryAccess,
            GalleryAccess.gallery_id.in_(private_ids),
            GalleryAccess.client_id == client_id,
        )
        if private_ids
        else 0
    )
    removed["private_capabilities"] = (
        _delete_count(
            db,
            GalleryAccessCapability,
            GalleryAccessCapability.derived_gallery_id.in_(private_ids),
            GalleryAccessCapability.client_id == client_id,
        )
        if private_ids
        else 0
    )
    removed["registrations"] = _delete_count(
        db,
        ParentGalleryRegistration,
        ParentGalleryRegistration.parent_gallery_id == parent_id,
        ParentGalleryRegistration.client_id == client_id,
    )
    removed["private_galleries"] = 0
    removed["memberships_unlinked"] = 0
    if membership and membership.status != "unlinked":
        membership.status = "unlinked"
        membership.unlinked_at = operation.updated_at
        removed["memberships_unlinked"] = 1
    manifest = dict(operation.manifest or {})
    manifest["removed_records"] = removed
    operation.manifest = manifest
    db.add(
        AuditEvent(
            event="parent_gallery.client_unlinked",
            subject=f"operation_id:{operation.id}",
        )
    )
