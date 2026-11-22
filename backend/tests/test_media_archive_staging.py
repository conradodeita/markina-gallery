"""Staging, pré-flight de capacidade e contrato sintético do arquivo frio."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveObject,
    MediaArchiveOperation,
    MediaArchiveSpaceReservation,
    ParentGallery,
    PhotoFolder,
    Tenant,
)
from app.media_archive_manifest import build_archive_manifest
from app.media_archive_staging import (
    GIB,
    MediaArchiveStagingError,
    VolumeCapacity,
    minimum_free_bytes,
    plan_restore_space,
    release_restore_space,
    reserve_restore_space,
    staging_directory,
    staging_object_path,
)
from app.media_archive_storage import (
    ArchiveDownloadReceipt,
    ArchiveRemoteObject,
    MediaArchiveStorage,
)


def _session():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    db = Session(engine, expire_on_commit=False)
    return engine, db


def _set_roots(monkeypatch, root: Path):
    source = (root / "served-source").resolve()
    derivatives = (root / "served-derivatives").resolve()
    history = (root / "served-history").resolve()
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history))
    return source, derivatives, history


def _restore_rows(db: Session):
    tenant = Tenant(id=uuid4(), status="active")
    db.add(tenant)
    db.flush()
    gallery = ParentGallery(tenant_id=tenant.id, name="Galeria sintética")
    db.add(gallery)
    db.flush()
    folder = PhotoFolder(
        tenant_id=tenant.id,
        parent_gallery_id=gallery.id,
        name="Pasta sintética",
        purpose="content",
        status="released",
        position=1,
    )
    db.add(folder)
    db.flush()
    cycle = MediaArchiveCycle(
        tenant_id=tenant.id,
        parent_gallery_id=gallery.id,
        folder_id=folder.id,
        cycle_number=1,
        state="archived",
    )
    db.add(cycle)
    db.flush()
    lease_token = "synthetic-lease-token"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    archive_operation = MediaArchiveOperation(
        tenant_id=tenant.id,
        cycle_id=cycle.id,
        operation_type="archive",
        status="completed",
        idempotency_key=f"archive-{uuid4()}",
    )
    db.add(archive_operation)
    db.flush()
    object_row = MediaArchiveObject(
        tenant_id=tenant.id,
        cycle_id=cycle.id,
        source_ref=f"photo:{uuid4()}:original",
        object_type="source",
        mime_type="image/jpeg",
        size_bytes=100,
        sha256=hashlib.sha256(b"x" * 100).hexdigest(),
        remote_object_id="synthetic_remote_1",
    )
    db.add(object_row)
    db.flush()
    build_archive_manifest(cycle=cycle, operation=archive_operation, objects=[object_row])
    cycle.state = "restoring"

    operation = MediaArchiveOperation(
        tenant_id=tenant.id,
        cycle_id=cycle.id,
        operation_type="restore",
        status="processing",
        idempotency_key=f"restore-{uuid4()}",
        lease_token=lease_token,
        lease_expires_at=expires_at,
    )
    db.add(operation)
    db.flush()
    db.add(MediaArchiveCoordinator(
        id=1,
        active_operation_id=operation.id,
        lease_token=lease_token,
        lease_expires_at=expires_at,
    ))
    db.flush()
    return tenant, gallery, folder, cycle, operation, object_row


class SyntheticArchiveStorage:
    """In-memory adapter exclusivo dos testes; não abre rede nem lê credenciais."""

    def __init__(self):
        self._by_id: dict[str, tuple[str, str, bytes]] = {}
        self._by_key: dict[str, str] = {}

    def upload_object(
        self,
        *,
        object_key: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        stream: BytesIO,
    ) -> ArchiveRemoteObject:
        payload = stream.read()
        if len(payload) != size_bytes or hashlib.sha256(payload).hexdigest() != sha256:
            raise ValueError("Fonte sintética inválida")
        existing = self._by_key.get(object_key)
        if existing:
            saved_type, saved_digest, saved_payload = self._by_id[existing]
            if saved_type != mime_type or saved_digest != sha256 or saved_payload != payload:
                raise ValueError("Chave sintética reutilizada com bytes diferentes")
            remote_id = existing
        else:
            remote_id = hashlib.sha256(object_key.encode()).hexdigest()
            self._by_id[remote_id] = (mime_type, sha256, payload)
            self._by_key[object_key] = remote_id
        return ArchiveRemoteObject(remote_id, size_bytes, mime_type)

    def read_object(self, *, remote_id: str) -> ArchiveRemoteObject | None:
        value = self._by_id.get(remote_id)
        if value is None:
            return None
        mime_type, _digest, payload = value
        return ArchiveRemoteObject(remote_id, len(payload), mime_type)

    def download_object(self, *, remote_id: str, destination: BytesIO) -> ArchiveDownloadReceipt:
        value = self._by_id.get(remote_id)
        if value is None:
            raise FileNotFoundError("Objeto sintético ausente")
        payload = value[2]
        digest = hashlib.sha256()
        count = 0
        for offset in range(0, len(payload), 7):
            block = payload[offset : offset + 7]
            destination.write(block)
            digest.update(block)
            count += len(block)
        return ArchiveDownloadReceipt(count, digest.hexdigest())

    def delete_object(self, *, remote_id: str) -> None:
        stored = self._by_id.pop(remote_id, None)
        if stored:
            for key, candidate in list(self._by_key.items()):
                if candidate == remote_id:
                    del self._by_key[key]


def test_staging_is_private_and_scoped_by_tenant_operation_object(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    staging_root = tmp_path / "private-staging"
    tenant_id, other_tenant_id, operation_id, object_id = uuid4(), uuid4(), uuid4(), uuid4()

    first = staging_directory(tenant_id, operation_id, root=staging_root)
    other_operation = staging_directory(tenant_id, uuid4(), root=staging_root)
    other_tenant = staging_directory(other_tenant_id, operation_id, root=staging_root)
    object_path = staging_object_path(tenant_id, operation_id, object_id, root=staging_root)

    assert first != other_operation != other_tenant
    assert object_path == first / "objects" / f"{object_id}.part"
    assert not object_path.exists()
    for served_root in _set_roots(monkeypatch, tmp_path):
        assert not first.is_relative_to(served_root)
        assert not served_root.is_relative_to(first)
    if os.name != "nt":
        assert first.stat().st_mode & 0o077 == 0
        assert (first.parent).stat().st_mode & 0o077 == 0

    with pytest.raises(MediaArchiveStagingError):
        staging_directory(str(tenant_id), operation_id, root=staging_root)


def test_staging_root_cannot_overlap_a_served_media_root(tmp_path, monkeypatch):
    source, _derivatives, _history = _set_roots(monkeypatch, tmp_path)
    with pytest.raises(MediaArchiveStagingError, match="fora das raízes"):
        staging_directory(uuid4(), uuid4(), root=source / "archive-staging")


def test_staging_rejects_symlink_component_when_host_allows_it(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    target = tmp_path / "real-staging"
    target.mkdir()
    link = tmp_path / "staging-link"
    try:
        os.symlink(target, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Este Windows não permite criar symlinks sem privilégio adicional.")
    with pytest.raises(MediaArchiveStagingError, match="simbólico"):
        staging_directory(uuid4(), uuid4(), root=link / "nested")


def test_restore_space_plan_accounts_for_stage_and_each_target_volume(tmp_path, monkeypatch):
    source, derivatives, _history = _set_roots(monkeypatch, tmp_path)
    stage = tmp_path / "private-staging"
    objects = [
        MediaArchiveObject(
            id=uuid4(), tenant_id=uuid4(), cycle_id=uuid4(), source_ref="photo:one:original",
            object_type="source", mime_type="image/jpeg", size_bytes=100, sha256="a" * 64,
            remote_object_id="remote-source",
        ),
        MediaArchiveObject(
            id=uuid4(), tenant_id=uuid4(), cycle_id=uuid4(), source_ref="derivative:one",
            object_type="derivative", mime_type="image/jpeg", size_bytes=50, sha256="b" * 64,
            remote_object_id="remote-derivative",
        ),
    ]
    capacities = {
        stage: VolumeCapacity("1" * 64, 100 * GIB, 30 * GIB),
        source: VolumeCapacity("1" * 64, 100 * GIB, 30 * GIB),
        derivatives: VolumeCapacity("2" * 64, 100 * GIB, 20 * GIB),
    }
    plan = plan_restore_space(objects, staging_root=stage, capacity_provider=capacities.__getitem__)

    assert [(item.volume_key, item.required_bytes) for item in plan] == [
        ("1" * 64, 250),
        ("2" * 64, 50),
    ]
    assert all(item.minimum_free_bytes == 15 * GIB for item in plan)
    assert minimum_free_bytes(50 * GIB) == 10 * GIB


def test_restore_space_reservations_are_idempotent_and_release_only_on_known_outcomes(
    tmp_path, monkeypatch,
):
    _set_roots(monkeypatch, tmp_path)
    engine, db = _session()
    tenant, _gallery, _folder, _cycle, operation, _object = _restore_rows(db)
    stage = tmp_path / "private-staging"
    capacity = VolumeCapacity("3" * 64, 100 * GIB, 30 * GIB)
    provider = lambda _path: capacity

    previous_operation = MediaArchiveOperation(
        tenant_id=tenant.id,
        cycle_id=operation.cycle_id,
        operation_type="restore",
        status="failed",
        idempotency_key=f"previous-restore-{uuid4()}",
    )
    db.add(previous_operation)
    db.flush()
    previous_reservation = MediaArchiveSpaceReservation(
        tenant_id=tenant.id,
        operation_id=previous_operation.id,
        volume_key=capacity.volume_key,
        reserved_bytes=16 * GIB,
        status="active",
    )
    db.add(previous_reservation)
    db.flush()
    with pytest.raises(MediaArchiveStagingError, match="Espaço insuficiente"):
        reserve_restore_space(
            db, tenant_id=tenant.id, operation_id=operation.id,
            staging_root=stage, capacity_provider=provider,
        )
    previous_reservation.status = "released"
    previous_reservation.released_at = datetime.now(timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    db.flush()

    first = reserve_restore_space(
        db, tenant_id=tenant.id, operation_id=operation.id,
        staging_root=stage, capacity_provider=provider,
    )
    second = reserve_restore_space(
        db, tenant_id=tenant.id, operation_id=operation.id,
        staging_root=stage, capacity_provider=provider,
    )
    assert len(first) == len(second) == 1
    assert first[0].id == second[0].id
    assert first[0].reserved_bytes == 200

    operation.status = "completed"
    assert release_restore_space(
        db, tenant_id=tenant.id, operation_id=operation.id, outcome="completed",
    ) == 1
    assert first[0].status == "released"
    assert first[0].released_at is not None
    with pytest.raises(MediaArchiveStagingError, match="resultado não permite"):
        release_restore_space(
            db, tenant_id=tenant.id, operation_id=operation.id, outcome="unknown",
        )
    db.close()
    engine.dispose()


def test_restore_space_preflight_fails_closed_below_approved_margin(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    engine, db = _session()
    tenant, _gallery, _folder, _cycle, operation, _object = _restore_rows(db)
    insufficient = VolumeCapacity("4" * 64, 100 * GIB, 15 * GIB + 99)

    with pytest.raises(MediaArchiveStagingError, match="Espaço insuficiente") as exc:
        reserve_restore_space(
            db, tenant_id=tenant.id, operation_id=operation.id,
            staging_root=tmp_path / "private-staging", capacity_provider=lambda _path: insufficient,
        )
    assert exc.value.code == "insufficient_space"
    assert not list(db.query(MediaArchiveSpaceReservation))
    db.close()
    engine.dispose()


def test_synthetic_storage_adapter_upload_readback_download_and_delete_are_repeatable():
    adapter: MediaArchiveStorage = SyntheticArchiveStorage()
    payload = b"synthetic archive object bytes"
    expected_hash = hashlib.sha256(payload).hexdigest()
    receipt = adapter.upload_object(
        object_key="tenant-uuid/operation-uuid/object-uuid",
        mime_type="image/jpeg",
        size_bytes=len(payload),
        sha256=expected_hash,
        stream=BytesIO(payload),
    )
    repeated = adapter.upload_object(
        object_key="tenant-uuid/operation-uuid/object-uuid",
        mime_type="image/jpeg",
        size_bytes=len(payload),
        sha256=expected_hash,
        stream=BytesIO(payload),
    )
    assert repeated == receipt
    assert receipt.size_bytes == len(payload)
    assert adapter.read_object(remote_id=receipt.remote_id) == receipt

    downloaded = BytesIO()
    result = adapter.download_object(remote_id=receipt.remote_id, destination=downloaded)
    assert downloaded.getvalue() == payload
    assert result == ArchiveDownloadReceipt(len(payload), expected_hash)

    adapter.delete_object(remote_id=receipt.remote_id)
    adapter.delete_object(remote_id=receipt.remote_id)
    assert adapter.read_object(remote_id=receipt.remote_id) is None
