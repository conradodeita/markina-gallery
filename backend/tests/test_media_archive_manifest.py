"""Snapshot, resolução segura e canonicalização V1 em mídia sintética local."""

import hashlib
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app import media as media_storage
from app.auth import (
    Base,
    Client,
    CommercialHistoryMedia,
    GalleryClientState,
    MediaArchiveCycle,
    MediaArchiveObject,
    MediaArchiveOperation,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PreviewAdjustment,
    SaleOrder,
    SaleOrderItem,
    Tenant,
)
from app.media_archive_manifest import (
    MediaArchiveManifestError,
    MediaArchiveSourceError,
    build_archive_manifest,
    canonical_manifest_bytes,
    parse_canonical_manifest,
    resolve_archive_source_ref,
    resolve_archive_sources,
    resolve_archive_target_path,
    snapshot_archive_objects,
    validate_stored_archive_manifest,
)
from tests.tenant_fixtures import FIXTURE_TENANT_ID


def _session():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    db = Session(engine, expire_on_commit=False)
    return engine, db


def _write(root: Path, key: str, data: bytes) -> Path:
    path = root.joinpath(*key.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _fixture(db: Session, tmp_path: Path, monkeypatch):
    tenant_id = FIXTURE_TENANT_ID
    tenant = db.get(Tenant, tenant_id)
    assert tenant and tenant.status == "active"
    source_root = (tmp_path / "source").resolve()
    derivatives_root = (tmp_path / "derivatives").resolve()
    history_root = (tmp_path / "history").resolve()
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))

    gallery = ParentGallery(tenant_id=tenant_id, name="Galeria sintética")
    db.add(gallery)
    db.flush()
    now = datetime.now(UTC)
    first_folder = PhotoFolder(
        tenant_id=tenant_id, parent_gallery_id=gallery.id, name="Pasta antiga",
        purpose="content", status="released", position=1, access_duration_days=30,
        released_at=now - timedelta(days=50), access_expires_at=now - timedelta(days=20),
    )
    last_folder = PhotoFolder(
        tenant_id=tenant_id, parent_gallery_id=gallery.id, name="Pasta final",
        purpose="content", status="released", position=2, access_duration_days=30,
        released_at=now - timedelta(days=50), access_expires_at=now - timedelta(days=20),
    )
    cover_folder = PhotoFolder(
        tenant_id=tenant_id, parent_gallery_id=gallery.id, name="Capas técnicas",
        purpose="cover_assets", status="released", position=3,
    )
    db.add_all([first_folder, last_folder, cover_folder])
    db.flush()

    cover_photo = PhotoAsset(
        tenant_id=tenant_id, parent_gallery_id=gallery.id, folder_id=first_folder.id,
        filename="CLIENTE-PRIVADO-CAPA.jpg",
        storage_key=f"tenants/{tenant_id}/photos/cover/original.jpg",
    )
    last_photo = PhotoAsset(
        tenant_id=tenant_id, parent_gallery_id=gallery.id, folder_id=last_folder.id,
        filename="CLIENTE-PRIVADO-PASTA.jpg",
        storage_key=f"tenants/{tenant_id}/photos/final/original.jpg",
    )
    technical_cover = PhotoAsset(
        tenant_id=tenant_id, parent_gallery_id=gallery.id, folder_id=cover_folder.id,
        filename="CLIENTE-PRIVADO-TECNICA.jpg",
        storage_key=f"tenants/{tenant_id}/photos/technical/original.jpg",
    )
    db.add_all([cover_photo, last_photo, technical_cover])
    db.flush()
    gallery.cover_photo_id = cover_photo.id

    photo_payloads = {
        cover_photo.id: b"jpeg-cover-source",
        last_photo.id: b"jpeg-last-source",
        technical_cover.id: b"jpeg-technical-source",
    }
    for photo, payload in (
        (cover_photo, photo_payloads[cover_photo.id]),
        (last_photo, photo_payloads[last_photo.id]),
        (technical_cover, photo_payloads[technical_cover.id]),
    ):
        _write(source_root, photo.storage_key, payload)
        for variant in ("thumbnail", "client_preview", "admin_preview"):
            key = f"tenants/{tenant_id}/photos/{photo.id}/{variant}.jpg"
            _write(derivatives_root, key, f"{photo.id}-{variant}".encode())
            db.add(MediaDerivative(
                tenant_id=tenant_id, photo_asset_id=photo.id, variant=variant,
                relative_path=key, status="ready",
            ))

    claim = uuid4()
    adjustment_key = (
        f"tenants/{tenant_id}/photos/{last_photo.id}/preview-adjustment/{claim}.jpg"
    )
    adjustment_path = _write(derivatives_root, adjustment_key, b"jpeg-adjusted-preview")
    db.add(PreviewAdjustment(
        tenant_id=tenant_id, photo_asset_id=last_photo.id, generation=1,
        fingerprint="a" * 64, status="ready", relative_path=adjustment_key,
    ))

    client = Client(
        tenant_id=tenant_id, full_name="Cliente sintética", phone_e164="+15555550123",
    )
    db.add(client)
    db.flush()
    db.add(GalleryClientState(
        tenant_id=tenant_id, parent_gallery_id=gallery.id, client_id=client.id,
    ))
    db.flush()
    order = SaleOrder(
        tenant_id=tenant_id, client_id=client.id,
        parent_gallery_id=gallery.id, derived_gallery_id=None,
        parent_gallery_id_snapshot=gallery.id,
        parent_gallery_name_snapshot=gallery.name,
        derived_gallery_name_snapshot="",
        payment_status="confirmed", total_cents=1000,
    )
    db.add(order)
    db.flush()
    item = SaleOrderItem(
        tenant_id=tenant_id, sale_order_id=order.id, photo_asset_id=last_photo.id,
        photo_asset_id_snapshot=last_photo.id, filename_snapshot=last_photo.filename,
        folder_id_snapshot=last_folder.id, folder_name_snapshot=last_folder.name,
        checksum_sha256_snapshot=hashlib.sha256(photo_payloads[last_photo.id]).hexdigest(),
        unit_price_cents=1000,
    )
    db.add(item)
    db.flush()
    preview_key = f"tenants/{tenant_id}/items/{item.id}/preview.jpg"
    delivery_key = f"tenants/{tenant_id}/items/{item.id}/delivery.jpg"
    preview_bytes = b"jpeg-commercial-preview"
    delivery_bytes = photo_payloads[last_photo.id]
    _write(history_root, preview_key, preview_bytes)
    _write(history_root, delivery_key, delivery_bytes)
    history = CommercialHistoryMedia(
        tenant_id=tenant_id, sale_order_item_id=item.id,
        preview_storage_key=preview_key, delivery_storage_key=delivery_key,
        checksum_sha256=hashlib.sha256(preview_bytes).hexdigest(),
        media_type="image/jpeg", size_bytes=len(preview_bytes) + len(delivery_bytes),
        status="ready",
    )
    db.add(history)
    db.flush()

    cycle = MediaArchiveCycle(
        tenant_id=tenant_id, parent_gallery_id=gallery.id, folder_id=last_folder.id,
        cycle_number=1, state="local",
    )
    db.add(cycle)
    db.flush()
    operation = MediaArchiveOperation(
        tenant_id=tenant_id, cycle_id=cycle.id, operation_type="archive",
        idempotency_key="archive-final-folder-once",
    )
    db.add(operation)
    db.flush()
    return {
        "tenant_id": tenant_id,
        "gallery": gallery,
        "first_folder": first_folder,
        "last_folder": last_folder,
        "cover_folder": cover_folder,
        "cover_photo": cover_photo,
        "last_photo": last_photo,
        "technical_cover": technical_cover,
        "claim": claim,
        "adjustment_path": adjustment_path,
        "history": history,
        "item": item,
        "cycle": cycle,
        "operation": operation,
    }


@pytest.mark.parametrize("latest_state", ["archived", "local"])
def test_shared_cover_uses_chronology_across_folders_not_folder_cycle_number(
    tmp_path, monkeypatch, latest_state,
):
    from app.main import _cover_preview_url, _local_cover_thumbnail_parent_ids

    engine, db = _session()
    try:
        data = _fixture(db, tmp_path, monkeypatch)
        at = datetime.now(UTC)
        old = MediaArchiveCycle(
            tenant_id=data["tenant_id"], parent_gallery_id=data["gallery"].id,
            folder_id=data["first_folder"].id, cycle_number=5,
            state="local" if latest_state == "archived" else "archived",
            created_at=at - timedelta(days=3),
        )
        later_source_cycle = MediaArchiveCycle(
            tenant_id=data["tenant_id"], parent_gallery_id=data["gallery"].id,
            folder_id=data["first_folder"].id, cycle_number=6, state="archived",
            created_at=at - timedelta(days=2),
        )
        latest = MediaArchiveCycle(
            tenant_id=data["tenant_id"], parent_gallery_id=data["gallery"].id,
            folder_id=data["last_folder"].id, cycle_number=2, state=latest_state,
            created_at=at - timedelta(days=1),
        )
        db.add_all([old, later_source_cycle, latest])
        db.flush()
        for cycle in (old, latest):
            db.add(MediaArchiveObject(
                tenant_id=data["tenant_id"], cycle_id=cycle.id,
                source_ref=f"cover:{data['cover_photo'].id}:admin_preview",
                object_type="cover_thumbnail", mime_type="image/jpeg", size_bytes=1,
                sha256="a" * 64, remote_object_id=f"synthetic_{cycle.id}",
            ))
        db.commit()

        # O ciclo 6 da origem não contém a miniatura compartilhada. O estado
        # que rege a capa é o ciclo 2 mais recente da outra pasta, não o 5 antigo.
        expected_local = latest_state == "local"
        assert (_cover_preview_url(db, data["gallery"]) is not None) is expected_local
        local_parents = _local_cover_thumbnail_parent_ids(
            db, tenant_id=data["tenant_id"], parent_ids={data["gallery"].id},
        )
        assert (data["gallery"].id in local_parents) is expected_local
    finally:
        db.close()
        engine.dispose()


def test_sources_are_tenant_resolved_and_cover_assets_wait_for_last_local_folder(
    tmp_path, monkeypatch,
):
    engine, db = _session()
    data = _fixture(db, tmp_path, monkeypatch)
    tenant_id = data["tenant_id"]

    first_sources = resolve_archive_sources(
        db, tenant_id=tenant_id, parent_gallery_id=data["gallery"].id,
        folder_id=data["first_folder"].id,
    )
    first_refs = {source.source_ref for source in first_sources}
    assert f"photo:{data['cover_photo'].id}:original" in first_refs
    assert f"cover:{data['cover_photo'].id}:admin_preview" not in first_refs
    assert f"photo:{data['technical_cover'].id}:original" not in first_refs
    assert not any("CLIENTE-PRIVADO" in source.source_ref for source in first_sources)

    first_cycle = MediaArchiveCycle(
        tenant_id=tenant_id, parent_gallery_id=data["gallery"].id,
        folder_id=data["first_folder"].id, cycle_number=1, state="archived",
    )
    db.add(first_cycle)
    db.flush()

    final_sources = resolve_archive_sources(
        db, tenant_id=tenant_id, parent_gallery_id=data["gallery"].id,
        folder_id=data["last_folder"].id,
    )
    final_refs = {source.source_ref for source in final_sources}
    assert f"photo:{data['technical_cover'].id}:original" in final_refs
    assert f"cover:{data['cover_photo'].id}:admin_preview" in final_refs
    assert f"adjustment:{data['last_photo'].id}:{data['claim']}:tenant" in final_refs
    assert f"commercial:{data['history'].id}:preview" in final_refs
    assert f"commercial:{data['history'].id}:delivery" in final_refs
    assert sum(source.size_bytes for source in final_sources) == sum(
        source.path.stat().st_size for source in final_sources
    )

    cover_source = resolve_archive_source_ref(
        db, tenant_id=tenant_id, parent_gallery_id=data["gallery"].id,
        folder_id=data["last_folder"].id,
        source_ref=f"cover:{data['cover_photo'].id}:admin_preview",
    )
    assert cover_source.object_type == "cover_thumbnail"
    with pytest.raises(MediaArchiveManifestError):
        resolve_archive_source_ref(
            db, tenant_id=tenant_id, parent_gallery_id=data["gallery"].id,
            folder_id=data["last_folder"].id,
            source_ref=f"photo:{uuid4()}:../../outside.jpg",
        )
    db.close()
    engine.dispose()


def test_archive_snapshot_is_idempotent_and_manifest_is_canonical(tmp_path, monkeypatch):
    engine, db = _session()
    data = _fixture(db, tmp_path, monkeypatch)
    cycle, operation = data["cycle"], data["operation"]

    first = snapshot_archive_objects(db, cycle=cycle, operation=operation)
    second = snapshot_archive_objects(db, cycle=cycle, operation=operation)
    assert len(first) == len(second)
    assert len(list(db.scalars(select(MediaArchiveObject).where(
        MediaArchiveObject.cycle_id == cycle.id,
    )))) == len(first)

    for index, row in enumerate(first):
        row.remote_object_id = f"drive_file_{index:03d}"
    timestamp = datetime(2026, 11, 8, 12, 30, tzinfo=UTC)
    manifest, encoded, checksum = build_archive_manifest(
        cycle=cycle, operation=operation, objects=first, created_at=timestamp,
    )
    parsed, parsed_checksum = parse_canonical_manifest(encoded)
    assert parsed == manifest
    assert parsed_checksum == checksum == cycle.manifest_sha256
    assert cycle.object_count == len(first)
    assert cycle.total_bytes == sum(row.size_bytes for row in first)
    assert b"CLIENTE-PRIVADO" not in encoded
    assert str(data["last_photo"].storage_key).encode() not in encoded
    assert validate_stored_archive_manifest(cycle)[1] == encoded

    with pytest.raises(MediaArchiveManifestError, match="Total de bytes"):
        changed = dict(manifest)
        changed["total_bytes"] += 1
        canonical_manifest_bytes(changed)
    with pytest.raises(MediaArchiveManifestError, match="Chave JSON duplicada"):
        parse_canonical_manifest(b'{"schema_version":1,"schema_version":1}')

    db.close()
    engine.dispose()


def test_archive_snapshot_rejects_source_changes_after_snapshot(tmp_path, monkeypatch):
    engine, db = _session()
    data = _fixture(db, tmp_path, monkeypatch)
    cycle, operation = data["cycle"], data["operation"]
    snapshot_archive_objects(db, cycle=cycle, operation=operation)

    # Alterar a fonte depois de congelada não sobrescreve checksum/remote ID.
    photo_path = media_storage.safe_source_path(data["last_photo"])
    photo_path.write_bytes(b"changed-after-snapshot")
    with pytest.raises(MediaArchiveSourceError, match="Fonte mudou"):
        snapshot_archive_objects(db, cycle=cycle, operation=operation)


    db.close()
    engine.dispose()


def test_archive_target_resolution_survives_missing_files_without_storing_paths(
    tmp_path, monkeypatch,
):
    engine, db = _session()
    data = _fixture(db, tmp_path, monkeypatch)
    tenant_id = data["tenant_id"]
    parent_gallery_id = data["gallery"].id
    folder_id = data["last_folder"].id

    original_ref = f"photo:{data['last_photo'].id}:original"
    original_path = media_storage.safe_source_path(data["last_photo"])
    assert resolve_archive_target_path(
        db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id,
        folder_id=folder_id, source_ref=original_ref, object_type="source",
    ) == original_path
    original_path.unlink()
    assert resolve_archive_target_path(
        db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id,
        folder_id=folder_id, source_ref=original_ref, object_type="source",
    ) == original_path

    adjustment_ref = f"adjustment:{data['last_photo'].id}:{data['claim']}:tenant"
    assert resolve_archive_target_path(
        db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id,
        folder_id=folder_id, source_ref=adjustment_ref, object_type="derivative",
    ) == data["adjustment_path"]
    data["adjustment_path"].unlink()
    assert resolve_archive_target_path(
        db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id,
        folder_id=folder_id, source_ref=adjustment_ref, object_type="derivative",
    ) == data["adjustment_path"]

    with pytest.raises(MediaArchiveSourceError):
        resolve_archive_target_path(
            db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id,
            folder_id=uuid4(), source_ref=original_ref, object_type="source",
        )
    db.close()
    engine.dispose()


def test_archive_resolver_rejects_derivative_from_another_photo(tmp_path, monkeypatch):
    engine, db = _session()
    data = _fixture(db, tmp_path, monkeypatch)
    derivative = db.scalar(select(MediaDerivative).where(
        MediaDerivative.photo_asset_id == data["last_photo"].id,
        MediaDerivative.variant == "thumbnail",
    ))
    derivative.relative_path = (
        f"tenants/{data['tenant_id']}/photos/{data['cover_photo'].id}/foreign.jpg"
    )
    with pytest.raises(MediaArchiveSourceError, match="fora do diretório da foto"):
        resolve_archive_sources(
            db, tenant_id=data["tenant_id"], parent_gallery_id=data["gallery"].id,
            folder_id=data["last_folder"].id,
        )
    db.close()
    engine.dispose()


def test_archive_resolver_rejects_symlink_sources(tmp_path, monkeypatch):
    engine, db = _session()
    data = _fixture(db, tmp_path, monkeypatch)
    symlink_key = f"tenants/{data['tenant_id']}/photos/link/symlink.jpg"
    symlink_photo = PhotoAsset(
        tenant_id=data["tenant_id"], parent_gallery_id=data["gallery"].id,
        folder_id=data["last_folder"].id, filename="linked.jpg", storage_key=symlink_key,
    )
    db.add(symlink_photo)
    db.flush()
    target = tmp_path / "outside.jpg"
    target.write_bytes(b"jpeg-outside")
    symlink = media_storage.source_root().joinpath(*symlink_key.split("/"))
    symlink.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, symlink)
    except (OSError, NotImplementedError):
        pytest.skip("Este Windows não permite criar symlinks sem privilégio adicional.")

    with pytest.raises(MediaArchiveSourceError):
        resolve_archive_sources(
            db, tenant_id=data["tenant_id"], parent_gallery_id=data["gallery"].id,
            folder_id=data["last_folder"].id,
        )
    db.close()
    engine.dispose()
