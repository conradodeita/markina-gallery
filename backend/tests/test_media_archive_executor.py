"""Executor de arquivo frio exercitado somente com storage sintético local."""

from __future__ import annotations

import hashlib
import re
from contextlib import contextmanager
from datetime import timedelta, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
import sqlalchemy as sa
from pydantic import SecretStr
from sqlalchemy import event
from sqlalchemy.orm import Session

from app import media_archive_billing as recovery_billing
from app import photographer_credits
from app.auth import (
    Base,
    Client,
    CommercialHistoryMedia,
    GalleryClientState,
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveEvent,
    MediaArchiveObject,
    MediaArchiveOperation,
    MediaArchiveRecoveryCreditReservation,
    MediaArchiveRecoveryPricing,
    MediaJob,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PhotographerCreditEntry,
    PhotoSelection,
    SaleOrder,
    SaleOrderItem,
    Tenant,
    now,
)
from app.folder_access import folder_media_is_local, gallery_media_writes_allowed
from app.google_drive_media_archive_storage import (
    DRIVE_FILES_URL,
    DRIVE_FOLDER_MIME,
    MEDIA_NAMESPACE,
    GoogleDriveMediaArchiveError,
    GoogleDriveMediaArchiveStorage,
)
from app.google_drive_storage import UPLOAD_ENDPOINT
from app.media_archive_executor import (
    MediaArchiveExecutionResult,
    execute_archive_operation,
    execute_restore_operation,
)
from app.media_archive_storage import (
    ArchiveDownloadReceipt,
    ArchiveRemoteObject,
)
from app.media_archive_worker import MediaArchiveClaim, claim_next_operation
from tests.test_photographer_credits import create_accounts, create_photo


class InMemoryArchiveStorage:
    """Adapter determinístico; nada é enviado para um provedor externo."""

    def __init__(self, *, corrupt_readback: bool = False):
        self.corrupt_readback = corrupt_readback
        self.by_key: dict[str, str] = {}
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.upload_keys: list[str] = []

    def upload_object(
        self,
        *,
        object_key: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        stream,
    ) -> ArchiveRemoteObject:
        payload = stream.read()
        assert len(payload) == size_bytes
        assert hashlib.sha256(payload).hexdigest() == sha256
        self.upload_keys.append(object_key)
        remote_id = self.by_key.get(object_key)
        if remote_id:
            previous, previous_mime = self.objects[remote_id]
            if previous != payload or previous_mime != mime_type:
                raise ValueError("idempotency key has different content")
        else:
            remote_id = f"remote_{len(self.objects) + 1}"
            self.by_key[object_key] = remote_id
            self.objects[remote_id] = (payload, mime_type)
        return ArchiveRemoteObject(remote_id, size_bytes, mime_type)

    def read_object(self, *, remote_id: str) -> ArchiveRemoteObject | None:
        stored = self.objects.get(remote_id)
        if stored is None:
            return None
        payload, mime_type = stored
        return ArchiveRemoteObject(remote_id, len(payload), mime_type)

    def download_object(self, *, remote_id: str, destination) -> ArchiveDownloadReceipt:
        payload, _mime_type = self.objects[remote_id]
        if self.corrupt_readback:
            payload += b"corrupt"
        destination.write(payload)
        return ArchiveDownloadReceipt(len(payload), sha256(payload).hexdigest())

    def delete_object(self, *, remote_id: str) -> None:
        self.objects.pop(remote_id, None)


class SyntheticDriveTransport:
    """Implementa localmente os endpoints usados pelo adapter de mídia."""

    def __init__(self):
        self.files: dict[str, dict] = {}
        self.contents: dict[str, bytes] = {}
        self.sessions: dict[str, dict] = {}
        self.calls: list[tuple[str, str, dict]] = []
        self._next_id = 1
        self.lose_next_upload_confirmation = False

    def _new_id(self) -> str:
        file_id = f"synthetic-drive-{self._next_id}"
        self._next_id += 1
        return file_id

    def _response(self, status_code: int, payload=None, *, headers=None):
        return httpx.Response(status_code, json=payload, headers=headers)

    def get(self, url: str, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if url == DRIVE_FILES_URL:
            query = kwargs["params"]["q"]
            parent_match = re.search(r"'([^']+)' in parents", query)
            assert parent_match is not None
            parent_id = parent_match.group(1)
            resources = [
                resource.copy() for resource in self.files.values()
                if parent_id in resource.get("parents", [])
            ]
            name_match = re.search(r"name = '([^']+)'", query)
            object_hash_match = re.search(
                r"key='pyp_media_object' and value='([^']+)'", query,
            )
            if "or appProperties has" in query and name_match and object_hash_match:
                resources = [
                    item for item in resources
                    if item.get("name") == name_match.group(1)
                    or item.get("appProperties", {}).get("pyp_media_object")
                    == object_hash_match.group(1)
                ]
            elif name_match:
                resources = [item for item in resources if item.get("name") == name_match.group(1)]
            mime_match = re.search(r"mimeType = '([^']+)'", query)
            if mime_match:
                resources = [item for item in resources if item.get("mimeType") == mime_match.group(1)]
            return self._response(200, {"incompleteSearch": False, "files": resources})

        file_id = url.rsplit("/", 1)[-1]
        resource = self.files.get(file_id)
        return self._response(200, resource.copy()) if resource else self._response(404, {})

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url, kwargs))
        payload = kwargs["json"]
        if url == DRIVE_FILES_URL:
            resource = {
                "id": self._new_id(),
                "name": payload["name"],
                "mimeType": payload["mimeType"],
                "parents": list(payload["parents"]),
                "appProperties": dict(payload["appProperties"]),
                "trashed": False,
            }
            self.files[resource["id"]] = resource
            return self._response(200, resource)

        assert url == UPLOAD_ENDPOINT
        session_uri = f"https://www.googleapis.com/upload/drive/v3/files?upload_id={self._next_id}"
        self.sessions[session_uri] = dict(payload)
        return self._response(200, {}, headers={"Location": session_uri})

    def put(self, url: str, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        payload = self.sessions[url]
        content = kwargs["content"]
        file_id = self._new_id()
        resource = {
            "id": file_id,
            "name": payload["name"],
            "mimeType": payload["mimeType"],
            "size": str(len(content)),
            "md5Checksum": hashlib.md5(content, usedforsecurity=False).hexdigest(),
            "parents": list(payload["parents"]),
            "appProperties": dict(payload["appProperties"]),
            "trashed": False,
        }
        self.files[file_id] = resource
        self.contents[file_id] = content
        if self.lose_next_upload_confirmation:
            self.lose_next_upload_confirmation = False
            raise httpx.ReadError("synthetic response lost")
        return self._response(200, resource)

    def delete(self, url: str, **kwargs):
        self.calls.append(("DELETE", url, kwargs))
        file_id = url.rsplit("/", 1)[-1]
        self.files.pop(file_id, None)
        self.contents.pop(file_id, None)
        return httpx.Response(204)

    @contextmanager
    def stream_get(self, url: str, **kwargs):
        self.calls.append(("STREAM_GET", url, kwargs))
        file_id = url.rsplit("/", 1)[-1]
        if file_id not in self.contents:
            yield httpx.Response(404, content=b"")
            return
        yield httpx.Response(200, content=self.contents[file_id])


class SimulatedWorkerTermination(BaseException):
    """Representa o processo encerrado sem executar o tratamento de erro."""


def _google_drive_media_storage(transport, tenant_id):
    return GoogleDriveMediaArchiveStorage(
        access_token=SecretStr("synthetic-access-token"),
        media_root_id="synthetic-media-root",
        tenant_id=tenant_id,
        transport=transport,
    )


def _archive_fixture(tmp_path: Path, monkeypatch, *, photo_count: int = 1):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    source_root = (tmp_path / "sources").resolve()
    derivatives_root = (tmp_path / "derivatives").resolve()
    history_root = (tmp_path / "history").resolve()
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))
    tenant_id, gallery_id, folder_id = uuid4(), uuid4(), uuid4()
    cycle_id, operation_id = uuid4(), uuid4()
    instant = now()
    source_paths = []

    with Session(engine, expire_on_commit=False) as db:
        db.add(Tenant(id=tenant_id))
        db.flush()
        gallery = ParentGallery(
            id=gallery_id, tenant_id=tenant_id, name="Galeria sintética",
        )
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(
            id=folder_id,
            tenant_id=tenant_id,
            parent_gallery_id=gallery_id,
            name="Pasta sintética",
            purpose="content",
            status="released",
            position=1,
            released_at=instant - timedelta(days=90),
            access_duration_days=30,
            access_expires_at=instant - timedelta(days=61),
        )
        db.add(folder)
        db.flush()

        for index in range(photo_count):
            photo_id = uuid4()
            storage_key = f"tenants/{tenant_id}/photos/{photo_id}/original.jpg"
            photo = PhotoAsset(
                id=photo_id,
                tenant_id=tenant_id,
                parent_gallery_id=gallery_id,
                folder_id=folder_id,
                filename=f"synthetic-{index + 1}.jpg",
                storage_key=storage_key,
            )
            db.add(photo)
            source_path = source_root.joinpath(*storage_key.split("/"))
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_bytes(f"synthetic-jpeg-{index + 1}".encode())
            source_paths.append(source_path)

        db.add(MediaArchiveCycle(
            id=cycle_id,
            tenant_id=tenant_id,
            parent_gallery_id=gallery_id,
            folder_id=folder_id,
            cycle_number=1,
            state="local",
        ))
        db.flush()
        db.add_all([
            MediaArchiveOperation(
                id=operation_id,
                tenant_id=tenant_id,
                cycle_id=cycle_id,
                operation_type="archive",
                status="queued",
                idempotency_key=f"executor-test-{operation_id}",
                actor_type="system",
                created_at=instant,
            ),
            MediaArchiveCoordinator(id=1),
        ])
        db.commit()

    return engine, tenant_id, gallery_id, folder_id, cycle_id, operation_id, source_paths


def _claim(db: Session) -> MediaArchiveClaim:
    claim = claim_next_operation(db)
    assert claim is not None
    return claim


def _restore_fixture(tmp_path: Path, monkeypatch, *, photo_count: int = 2):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    source_root = (tmp_path / "restore-sources").resolve()
    derivatives_root = (tmp_path / "restore-derivatives").resolve()
    history_root = (tmp_path / "restore-history").resolve()
    staging_root = (tmp_path / "restore-staging").resolve()
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))

    storage = InMemoryArchiveStorage()
    payload_by_photo: dict[UUID, bytes] = {}
    tenant_id = cycle_id = restore_operation_id = None
    with Session(engine, expire_on_commit=False) as db:
        _owner_tenant, tenant, owner, photographer = create_accounts(db)
        tenant_id = tenant.id
        first_photo = create_photo(db, tenant.id)
        folder = db.get(PhotoFolder, first_photo.folder_id)
        assert folder is not None
        instant = now()
        folder.status = "released"
        folder.released_at = instant - timedelta(days=90)
        folder.access_duration_days = 30
        folder.access_expires_at = instant - timedelta(days=60)

        photos = [first_photo]
        for index in range(1, photo_count):
            photo = PhotoAsset(
                tenant_id=tenant.id,
                parent_gallery_id=first_photo.parent_gallery_id,
                folder_id=first_photo.folder_id,
                filename=f"synthetic-{index + 1}.jpg",
                storage_key=(
                    f"tenants/{tenant.id}/{first_photo.parent_gallery_id}/"
                    f"{first_photo.folder_id}/{uuid4()}.jpg"
                ),
            )
            db.add(photo)
            db.flush()
            photos.append(photo)

        for index, photo in enumerate(photos, start=1):
            payload = f"synthetic-photo-bytes-{index}".encode("ascii")
            target = source_root.joinpath(*photo.storage_key.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            payload_by_photo[photo.id] = payload

        client = Client(
            tenant_id=tenant.id,
            full_name="Cliente sintética de seleção",
            phone_e164="+5511999990001",
        )
        db.add(client)
        db.flush()
        selections = [PhotoSelection(
            tenant_id=tenant.id,
            parent_gallery_id=first_photo.parent_gallery_id,
            photo_asset_id=photo.id,
            client_id=client.id,
        ) for photo in photos]
        db.add_all(selections)

        cycle_id = uuid4()
        archive_operation_id = uuid4()
        db.add(MediaArchiveCycle(
            id=cycle_id,
            tenant_id=tenant.id,
            parent_gallery_id=first_photo.parent_gallery_id,
            folder_id=folder.id,
            cycle_number=1,
            state="local",
        ))
        db.add_all([
            MediaArchiveOperation(
                id=archive_operation_id,
                tenant_id=tenant.id,
                cycle_id=cycle_id,
                operation_type="archive",
                status="queued",
                idempotency_key=f"restore-fixture-archive-{uuid4()}",
                actor_type="system",
                created_at=instant,
            ),
            MediaArchiveCoordinator(id=1),
            MediaArchiveRecoveryPricing(
                id=1, recovery_fee_credits=2, updated_by_admin_id=owner.id,
            ),
        ])
        photographer_credits.grant_credits(
            db, owner.id, tenant.id, 5, "restore-fixture-credit", "synthetic",
        )
        db.commit()

        archive_claim = claim_next_operation(db)
        assert archive_claim is not None
        archive_result = execute_archive_operation(db, archive_claim, storage=storage)
        assert archive_result.status == "completed"
        assert all(not source_root.joinpath(*photo.storage_key.split("/")).exists() for photo in photos)

        request = recovery_billing.request_recovery(
            db,
            tenant_id=tenant.id,
            actor_admin_id=photographer.id,
            cycle_id=cycle_id,
            duration_days=30,
            idempotency_key=f"restore-fixture-request-{uuid4()}",
        )
        restore_operation_id = UUID(request["operation_id"])
        db.commit()
        restore_claim = claim_next_operation(db)
        assert restore_claim is not None and restore_claim.operation_id == restore_operation_id

    return (
        engine, tenant_id, first_photo.parent_gallery_id, folder.id, cycle_id,
        archive_operation_id, restore_operation_id, [item.id for item in selections],
        [photo.id for photo in photos], payload_by_photo, source_root, staging_root,
        storage, restore_claim,
    )


def test_executor_archives_only_after_full_readback_and_then_hides_before_cleanup(
    tmp_path, monkeypatch,
):
    engine, tenant_id, _gallery_id, folder_id, cycle_id, operation_id, source_paths = (
        _archive_fixture(tmp_path, monkeypatch)
    )
    storage = InMemoryArchiveStorage()
    from app import media_archive_executor as executor

    original_unlink = executor._unlink_verified
    cleanup_visibility = []

    def observe_visibility(target, *, root, size_bytes, digest):
        with Session(engine, expire_on_commit=False) as db:
            folder = db.get(PhotoFolder, folder_id)
            cleanup_visibility.append(not folder_media_is_local(db, folder))
        return original_unlink(
            target, root=root, size_bytes=size_bytes, digest=digest,
        )

    monkeypatch.setattr(executor, "_unlink_verified", observe_visibility)
    with Session(engine, expire_on_commit=False) as db:
        claim = _claim(db)
        result = execute_archive_operation(db, claim, storage=storage)
        assert result == MediaArchiveExecutionResult(operation_id, "completed")
        operation = db.get(MediaArchiveOperation, operation_id)
        cycle = db.get(MediaArchiveCycle, cycle_id)
        objects = list(db.scalars(sa.select(MediaArchiveObject).where(
            MediaArchiveObject.tenant_id == tenant_id,
            MediaArchiveObject.cycle_id == cycle_id,
        )))
        assert operation.status == "completed"
        assert cycle.state == "archived"
        assert operation.details["readback_verified"] is True
        assert operation.details["manifest_readback_verified"] is True
        assert operation.details["local_cleanup_complete"] is True
        assert sum(row.object_type != "manifest" for row in objects) == 1
        assert sum(row.object_type == "manifest" for row in objects) == 1
        assert all(row.remote_object_id for row in objects)

    assert cleanup_visibility == [True]
    assert all(not path.exists() for path in source_paths)
    assert len(storage.objects) == 2
    engine.dispose()


def test_executor_composes_with_google_drive_media_adapter_using_synthetic_transport(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("APP_ENV", "production")
    engine, tenant_id, gallery_id, folder_id, cycle_id, operation_id, source_paths = (
        _archive_fixture(tmp_path, monkeypatch)
    )
    transport = SyntheticDriveTransport()
    storage = _google_drive_media_storage(transport, tenant_id)

    with Session(engine, expire_on_commit=False) as db:
        result = execute_archive_operation(db, _claim(db), storage=storage)
        operation = db.get(MediaArchiveOperation, operation_id)
        cycle = db.get(MediaArchiveCycle, cycle_id)
        assert result == MediaArchiveExecutionResult(operation_id, "completed")
        assert operation.status == "completed"
        assert cycle.state == "archived"
        assert operation.details["readback_verified"] is True
        assert operation.details["manifest_readback_verified"] is True

    folders = {
        resource["appProperties"]["pyp_media_kind"]: resource
        for resource in transport.files.values()
        if resource.get("mimeType") == DRIVE_FOLDER_MIME
    }
    assert set(folders) == {"tenant", "gallery", "folder", "cycle"}
    assert folders["tenant"]["parents"] == ["synthetic-media-root"]
    assert folders["gallery"]["parents"] == [folders["tenant"]["id"]]
    assert folders["folder"]["parents"] == [folders["gallery"]["id"]]
    assert folders["cycle"]["parents"] == [folders["folder"]["id"]]
    assert folders["gallery"]["appProperties"]["pyp_media_gallery"] == str(gallery_id)
    assert folders["folder"]["appProperties"]["pyp_media_folder"] == str(folder_id)
    assert folders["cycle"]["appProperties"]["pyp_media_cycle"] == str(cycle_id)

    archived_objects = [
        resource for resource in transport.files.values()
        if resource.get("appProperties", {}).get("pyp_media_kind") == "object"
    ]
    assert len(archived_objects) == 2
    assert all(resource["parents"] == [folders["cycle"]["id"]] for resource in archived_objects)
    assert all(
        resource["appProperties"]["pyp_media_namespace"] == MEDIA_NAMESPACE
        and resource["appProperties"]["pyp_media_tenant"] == str(tenant_id)
        and resource["appProperties"]["pyp_media_gallery"] == str(gallery_id)
        and resource["appProperties"]["pyp_media_folder"] == str(folder_id)
        and resource["appProperties"]["pyp_media_cycle"] == str(cycle_id)
        for resource in archived_objects
    )
    assert all(
        "incompleteSearch" in kwargs["params"]["fields"]
        for method, url, kwargs in transport.calls
        if method == "GET" and url == DRIVE_FILES_URL
    )
    assert all(not path.exists() for path in source_paths)
    engine.dispose()


def test_lost_upload_confirmation_retry_reuses_verified_remote_object(monkeypatch):
    from app.media_archive_executor import _DigestingReader

    monkeypatch.setenv("APP_ENV", "production")
    transport = SyntheticDriveTransport()
    tenant_id = UUID("11111111-1111-4111-8111-111111111111")
    gallery_id = UUID("22222222-2222-4222-8222-222222222222")
    folder_id = UUID("33333333-3333-4333-8333-333333333333")
    cycle_id = UUID("44444444-4444-4444-8444-444444444444")
    object_id = UUID("55555555-5555-4555-8555-555555555555")
    storage = _google_drive_media_storage(transport, tenant_id)
    object_key = f"{tenant_id}/{gallery_id}/{folder_id}/{cycle_id}/{object_id}"
    payload = b"retry-after-lost-confirmation"
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    renewals = []

    first_reader = _DigestingReader(BytesIO(payload), renew=lambda: renewals.append("renew"))
    transport.lose_next_upload_confirmation = True
    with pytest.raises(GoogleDriveMediaArchiveError) as error:
        storage.upload_object(
            object_key=object_key,
            mime_type="image/jpeg",
            size_bytes=len(payload),
            sha256=expected_sha256,
            stream=first_reader,
        )
    assert "synthetic response lost" not in str(error.value)
    assert first_reader.size_bytes == len(payload)
    assert first_reader.sha256 == expected_sha256

    stored_before_retry = [
        resource for resource in transport.files.values()
        if resource.get("appProperties", {}).get("pyp_media_kind") == "object"
    ]
    assert len(stored_before_retry) == 1
    previous_id = stored_before_retry[0]["id"]

    retry_reader = _DigestingReader(BytesIO(payload), renew=lambda: renewals.append("renew"))
    receipt = storage.upload_object(
        object_key=object_key,
        mime_type="image/jpeg",
        size_bytes=len(payload),
        sha256=expected_sha256,
        stream=retry_reader,
    )
    assert receipt.remote_id == previous_id
    assert retry_reader.size_bytes == len(payload)
    assert retry_reader.sha256 == expected_sha256
    assert len(renewals) >= 6
    assert sum(method == "PUT" for method, _url, _kwargs in transport.calls) == 1
    assert sum(url == UPLOAD_ENDPOINT for _method, url, _kwargs in transport.calls) == 1
    assert sum(
        resource.get("appProperties", {}).get("pyp_media_kind") == "object"
        for resource in transport.files.values()
    ) == 1


def test_archive_is_blocked_by_an_open_frozen_order_and_preserves_local_media(
    tmp_path, monkeypatch,
):
    engine, tenant_id, gallery_id, folder_id, cycle_id, operation_id, source_paths = (
        _archive_fixture(tmp_path, monkeypatch)
    )
    with Session(engine, expire_on_commit=False) as db:
        gallery = db.get(ParentGallery, gallery_id)
        folder = db.get(PhotoFolder, folder_id)
        photo = db.scalar(sa.select(PhotoAsset).where(
            PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.folder_id == folder_id,
        ))
        client = Client(
            tenant_id=tenant_id,
            full_name="Cliente com pedido pendente",
            phone_e164="+5511999990011",
        )
        db.add(client)
        db.flush()
        db.add(GalleryClientState(
            tenant_id=tenant_id,
            parent_gallery_id=gallery_id,
            client_id=client.id,
        ))
        db.flush()
        order = SaleOrder(
            tenant_id=tenant_id,
            parent_gallery_id=gallery_id,
            client_id=client.id,
            parent_gallery_id_snapshot=gallery_id,
            parent_gallery_name_snapshot=gallery.name,
            derived_gallery_name_snapshot="Galeria principal",
            payment_status="pending",
            total_cents=100,
            frozen_at=now(),
            checkout_key=f"open-archive-blocker-{uuid4()}",
        )
        db.add(order)
        db.flush()
        db.add(SaleOrderItem(
            tenant_id=tenant_id,
            sale_order_id=order.id,
            photo_asset_id=photo.id,
            photo_asset_id_snapshot=photo.id,
            filename_snapshot=photo.filename,
            folder_id_snapshot=folder_id,
            folder_name_snapshot=folder.name,
            unit_price_cents=100,
        ))
        db.commit()

        result = execute_archive_operation(db, _claim(db), storage=InMemoryArchiveStorage())
        operation = db.get(MediaArchiveOperation, operation_id)
        cycle = db.get(MediaArchiveCycle, cycle_id)
        assert result.status == "failed"
        assert result.error_code == "open_order"
        assert operation.status == "failed"
        assert cycle.state == "local"
        assert folder_media_is_local(db, folder)
    assert all(path.is_file() for path in source_paths)
    engine.dispose()


def test_archive_revalidates_editable_checkout_before_local_cleanup(
    tmp_path, monkeypatch,
):
    engine, tenant_id, gallery_id, folder_id, cycle_id, operation_id, source_paths = (
        _archive_fixture(tmp_path, monkeypatch)
    )
    storage = InMemoryArchiveStorage()
    from app import media_archive_executor as executor

    with Session(engine, expire_on_commit=False) as db:
        photo = db.scalar(sa.select(PhotoAsset).where(
            PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.folder_id == folder_id,
        ))
        assert photo is not None

    original_begin_cleanup = executor.begin_archive_cleanup
    injected_order = False

    def create_checkout_before_cleanup(db, *, operation_id, lease_token, at=None):
        nonlocal injected_order
        if not injected_order:
            injected_order = True
            client = Client(
                tenant_id=tenant_id,
                full_name="Cliente com checkout pendente",
                phone_e164="+5511999990012",
            )
            db.add(client)
            db.flush()
            db.add(GalleryClientState(
                tenant_id=tenant_id,
                parent_gallery_id=gallery_id,
                client_id=client.id,
            ))
            db.flush()
            order = SaleOrder(
                tenant_id=tenant_id,
                parent_gallery_id=gallery_id,
                client_id=client.id,
                parent_gallery_id_snapshot=gallery_id,
                parent_gallery_name_snapshot="Galeria sintética",
                derived_gallery_name_snapshot="Galeria principal",
                payment_status="pending",
                total_cents=100,
                frozen_at=None,
                checkout_key=f"editable-checkout-{uuid4()}",
                created_at=now() - timedelta(days=46),
            )
            db.add(order)
            db.flush()
            db.add(SaleOrderItem(
                tenant_id=tenant_id,
                sale_order_id=order.id,
                photo_asset_id=photo.id,
                photo_asset_id_snapshot=photo.id,
                filename_snapshot=photo.filename,
                folder_id_snapshot=folder_id,
                folder_name_snapshot="Pasta sintética",
                unit_price_cents=100,
            ))
            db.flush()
        return original_begin_cleanup(
            db, operation_id=operation_id, lease_token=lease_token, at=at,
        )

    monkeypatch.setattr(executor, "begin_archive_cleanup", create_checkout_before_cleanup)
    with Session(engine, expire_on_commit=False) as db:
        result = execute_archive_operation(db, _claim(db), storage=storage)
        operation = db.get(MediaArchiveOperation, operation_id)
        cycle = db.get(MediaArchiveCycle, cycle_id)
        assert injected_order
        assert result.status == "failed"
        assert result.error_code == "open_order"
        assert operation.status == "failed"
        assert cycle.state == "local"
        assert folder_media_is_local(db, db.get(PhotoFolder, folder_id))

    assert all(path.is_file() for path in source_paths)
    engine.dispose()


def test_failed_remote_readback_keeps_local_sources_and_requires_reconciliation(
    tmp_path, monkeypatch,
):
    engine, _tenant_id, _gallery_id, _folder_id, cycle_id, operation_id, source_paths = (
        _archive_fixture(tmp_path, monkeypatch)
    )
    storage = InMemoryArchiveStorage(corrupt_readback=True)
    with Session(engine, expire_on_commit=False) as db:
        from app.auth import Tenant
        from app.tenant_closure_obligations import evaluate_closure
        db.get(Tenant, _tenant_id).lifecycle = "closing"
        db.commit()
        claim = _claim(db)
        result = execute_archive_operation(db, claim, storage=storage)
        assert result.status == "reconciliation_required"
        assert result.error_code == "archive_result_unknown"
        operation = db.get(MediaArchiveOperation, operation_id)
        cycle = db.get(MediaArchiveCycle, cycle_id)
        assert operation.status == "reconciliation_required"
        assert cycle.state == "reconciliation_required"
        assert operation.last_error == "Resultado externo incerto; reconciliação necessária."
        observation = evaluate_closure(db, _tenant_id)
        assert observation["ready"] is False
        assert "media_not_archived" in observation["blockers"]
    assert all(path.is_file() for path in source_paths)
    engine.dispose()


def test_interrupted_partial_cleanup_reclaims_same_operation_without_reupload(
    tmp_path, monkeypatch,
):
    engine, _tenant_id, _gallery_id, folder_id, cycle_id, operation_id, source_paths = (
        _archive_fixture(tmp_path, monkeypatch, photo_count=2)
    )
    storage = InMemoryArchiveStorage()
    from app import media_archive_executor as executor

    original_unlink = executor._unlink_verified
    cleanup_calls = 0

    def interrupt_after_one_unlink(target, *, root, size_bytes, digest):
        nonlocal cleanup_calls
        cleanup_calls += 1
        if cleanup_calls == 2:
            raise SimulatedWorkerTermination()
        return original_unlink(
            target, root=root, size_bytes=size_bytes, digest=digest,
        )

    monkeypatch.setattr(executor, "_unlink_verified", interrupt_after_one_unlink)
    with Session(engine, expire_on_commit=False) as db:
        first_claim = _claim(db)
        with pytest.raises(SimulatedWorkerTermination):
            execute_archive_operation(db, first_claim, storage=storage)
        db.rollback()
        operation = db.get(MediaArchiveOperation, operation_id)
        cycle = db.get(MediaArchiveCycle, cycle_id)
        assert operation.status == "processing"
        assert operation.stage == "local_cleanup"
        assert cycle.state == "archived"
        assert sum(path.exists() for path in source_paths) == 1
        assert not folder_media_is_local(db, db.get(PhotoFolder, folder_id))

        retry_claim = claim_next_operation(
            db, at=first_claim.lease_expires_at + timedelta(seconds=1),
        )
        assert retry_claim is not None
        assert retry_claim.operation_id == operation_id
        assert retry_claim.lease_token != first_claim.lease_token
        monkeypatch.setattr(executor, "_unlink_verified", original_unlink)
        result = execute_archive_operation(db, retry_claim, storage=storage)
        assert result == MediaArchiveExecutionResult(operation_id, "completed")
        assert db.get(MediaArchiveOperation, operation_id).status == "completed"

    assert all(not path.exists() for path in source_paths)
    assert len(storage.objects) == 3
    assert len(storage.upload_keys) == 3
    engine.dispose()


def test_new_attempt_reuses_the_immutable_manifest_from_a_proven_failed_attempt(
    tmp_path, monkeypatch,
):
    engine, tenant_id, _gallery_id, folder_id, cycle_id, first_operation_id, source_paths = (
        _archive_fixture(tmp_path, monkeypatch)
    )
    storage = InMemoryArchiveStorage()
    from app import media_archive_executor as executor

    photo_id = None
    with Session(engine, expire_on_commit=False) as db:
        photo_id = db.scalar(sa.select(PhotoAsset.id).where(
            PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.folder_id == folder_id,
        ))
    assert photo_id is not None

    original_begin_cleanup = executor.begin_archive_cleanup
    injected_job = False

    def block_cleanup_once(db, *, operation_id, lease_token, at=None):
        nonlocal injected_job
        if not injected_job:
            injected_job = True
            db.add(MediaJob(
                tenant_id=tenant_id,
                photo_asset_id=photo_id,
                kind="generate_derivatives",
                status="queued",
            ))
        return original_begin_cleanup(
            db, operation_id=operation_id, lease_token=lease_token, at=at,
        )

    monkeypatch.setattr(executor, "begin_archive_cleanup", block_cleanup_once)
    with Session(engine, expire_on_commit=False) as db:
        first_claim = _claim(db)
        first_result = execute_archive_operation(db, first_claim, storage=storage)
        assert first_result.status == "failed"
        assert injected_job
        assert all(path.is_file() for path in source_paths)

        first_operation = db.get(MediaArchiveOperation, first_operation_id)
        cycle = db.get(MediaArchiveCycle, cycle_id)
        assert first_operation.status == "failed"
        assert cycle.state == "local"
        first_manifest = dict(cycle.manifest)
        first_upload_count = len(storage.upload_keys)
        first_remote_object_count = len(storage.objects)
        assert first_manifest["operation_id"] == str(first_operation_id)

        retry_operation_id = uuid4()
        db.add(MediaArchiveOperation(
            id=retry_operation_id,
            tenant_id=tenant_id,
            cycle_id=cycle_id,
            operation_type="archive",
            status="queued",
            idempotency_key=f"executor-retry-{retry_operation_id}",
            actor_type="system",
            created_at=now() + timedelta(seconds=1),
        ))
        db.commit()

        retry_claim = _claim(db)
        assert retry_claim.operation_id == retry_operation_id
        retry_result = execute_archive_operation(db, retry_claim, storage=storage)
        assert retry_result == MediaArchiveExecutionResult(retry_operation_id, "completed")
        cycle = db.get(MediaArchiveCycle, cycle_id)
        assert cycle.state == "archived"
        assert cycle.manifest == first_manifest
        assert db.get(MediaArchiveOperation, retry_operation_id).status == "completed"

    assert len(storage.upload_keys) == first_upload_count
    assert len(storage.objects) == first_remote_object_count
    assert all(not path.exists() for path in source_paths)
    engine.dispose()


def test_shared_cover_assets_stay_write_blocked_until_their_cycle_is_local(
    tmp_path, monkeypatch,
):
    engine, tenant_id, gallery_id, _folder_id, cycle_id, _operation_id, _paths = (
        _archive_fixture(tmp_path, monkeypatch)
    )
    with Session(engine, expire_on_commit=False) as db:
        cycle = db.get(MediaArchiveCycle, cycle_id)
        cycle.state = "archived"
        db.add(MediaArchiveObject(
            tenant_id=tenant_id,
            cycle_id=cycle_id,
            source_ref=f"photo:{uuid4()}:original",
            object_type="cover_asset",
            mime_type="image/jpeg",
            size_bytes=1,
            sha256="a" * 64,
            remote_object_id="remote_cover",
        ))
        db.commit()
        assert not gallery_media_writes_allowed(
            db, tenant_id=tenant_id, parent_gallery_id=gallery_id,
        )

        cycle.state = "local"
        db.commit()
        assert gallery_media_writes_allowed(
            db, tenant_id=tenant_id, parent_gallery_id=gallery_id,
        )
    engine.dispose()


def test_readback_rejects_metadata_for_a_different_remote_object(monkeypatch):
    from app.media_archive_executor import MediaArchiveExecutorError, _verify_remote_object

    storage = InMemoryArchiveStorage()
    storage.objects["remote_1"] = (b"synthetic", "image/jpeg")
    monkeypatch.setattr(
        storage,
        "read_object",
        lambda *, remote_id: ArchiveRemoteObject(
            "remote_other", len(storage.objects[remote_id][0]), "image/jpeg",
        ),
    )

    with pytest.raises(MediaArchiveExecutorError):
        _verify_remote_object(
            storage,
            remote_id="remote_1",
            size_bytes=len(b"synthetic"),
            mime_type="image/jpeg",
            sha256_hex=sha256(b"synthetic").hexdigest(),
            renew=lambda: None,
        )


def test_restore_pulls_verifies_promotes_and_charges_once_without_recreating_records(
    tmp_path, monkeypatch,
):
    from app import media_archive_executor
    from app.media_archive_billing import list_tenant_recoveries
    from app.media_archive_staging import VolumeCapacity

    (
        engine, tenant_id, _gallery_id, folder_id, cycle_id, _archive_operation_id,
        restore_operation_id, selection_ids, photo_ids, payload_by_photo,
        source_root, staging_root, storage, claim,
    ) = _restore_fixture(tmp_path, monkeypatch)

    def ample_capacity(_path):
        return VolumeCapacity("a" * 64, 100 * 1024**3, 90 * 1024**3)

    original_download = storage.download_object
    original_promote = media_archive_executor._promote_verified_object
    observed_counts = []
    observed_finalization = []

    def progress_before_debit():
        with Session(engine) as read_db:
            (item,) = list_tenant_recoveries(read_db, tenant_id)
            assert read_db.scalar(sa.select(PhotographerCreditEntry.id).where(
                PhotographerCreditEntry.archive_operation_id == restore_operation_id,
            )) is None
            return item["progress"]

    def inspect_download(**kwargs):
        progress = progress_before_debit()
        if progress["stage"] == "downloading":
            observed_counts.append(progress["verified_objects"])
        return original_download(**kwargs)

    def inspect_promotion(**kwargs):
        progress = progress_before_debit()
        assert progress["stage"] == "finishing"
        assert progress["verified_objects"] == progress["total_objects"]
        observed_finalization.append(progress["verified_objects"])
        return original_promote(**kwargs)

    monkeypatch.setattr(storage, "download_object", inspect_download)
    monkeypatch.setattr(media_archive_executor, "_promote_verified_object", inspect_promotion)

    try:
        with Session(engine, expire_on_commit=False) as db:
            before_photo_ids = set(db.scalars(sa.select(PhotoAsset.id)))
            before_selection_ids = set(db.scalars(sa.select(PhotoSelection.id)))
            before_object_ids = set(db.scalars(sa.select(MediaArchiveObject.id)))
            before_history_count = db.scalar(sa.select(sa.func.count()).select_from(CommercialHistoryMedia))
            before_operation_count = db.scalar(sa.select(sa.func.count()).select_from(MediaArchiveOperation))
            result = execute_restore_operation(
                db, claim, storage=storage, staging_root=staging_root,
                capacity_provider=ample_capacity,
            )
            assert result == MediaArchiveExecutionResult(restore_operation_id, "completed")

            cycle = db.get(MediaArchiveCycle, cycle_id)
            folder = db.get(PhotoFolder, folder_id)
            operation = db.get(MediaArchiveOperation, restore_operation_id)
            assert cycle.state == "local"
            assert operation.status == "completed"
            assert observed_counts == list(range(cycle.object_count))
            assert observed_finalization == [cycle.object_count] * cycle.object_count
            assert "progress" not in list_tenant_recoveries(db, tenant_id)[0]
            assert folder.access_duration_days == 30
            expires_at = folder.access_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
            assert expires_at > now()
            assert folder_media_is_local(db, folder)
            assert set(db.scalars(sa.select(PhotoAsset.id))) == before_photo_ids
            assert set(db.scalars(sa.select(PhotoSelection.id))) == before_selection_ids == set(selection_ids)
            assert set(db.scalars(sa.select(MediaArchiveObject.id))) == before_object_ids
            assert db.scalar(sa.select(sa.func.count()).select_from(CommercialHistoryMedia)) == before_history_count
            assert db.scalar(sa.select(sa.func.count()).select_from(MediaArchiveOperation)) == before_operation_count
            ledger = list(db.scalars(sa.select(PhotographerCreditEntry).where(
                PhotographerCreditEntry.tenant_id == tenant_id,
                PhotographerCreditEntry.entry_type == "archive_recovery",
                PhotographerCreditEntry.archive_operation_id == restore_operation_id,
            )))
            assert len(ledger) == 1 and ledger[0].delta == -2
            reservation = db.scalar(sa.select(MediaArchiveRecoveryCreditReservation).where(
                MediaArchiveRecoveryCreditReservation.tenant_id == tenant_id,
                MediaArchiveRecoveryCreditReservation.operation_id == restore_operation_id,
            ))
            assert reservation.status == "consumed"
            events = list(db.scalars(sa.select(MediaArchiveEvent).where(
                MediaArchiveEvent.tenant_id == tenant_id,
                MediaArchiveEvent.cycle_id == cycle_id,
                MediaArchiveEvent.operation_id == restore_operation_id,
            )))
            assert any(event.event_type == "recovery_started" for event in events)
            completed = next(event for event in events if event.event_type == "recovery_completed")
            assert completed.details["duration_days"] == 30

        with Session(engine) as db:
            photos = list(db.scalars(sa.select(PhotoAsset).where(
                PhotoAsset.tenant_id == tenant_id,
                PhotoAsset.id.in_(photo_ids),
            )))
            assert len(photos) == len(photo_ids)
            for photo in photos:
                assert source_root.joinpath(*photo.storage_key.split("/")).read_bytes() == payload_by_photo[photo.id]
        assert not (staging_root / str(tenant_id) / str(restore_operation_id)).exists()
    finally:
        engine.dispose()


def test_restore_resumes_after_interrupted_partial_promotion_without_double_charge(
    tmp_path, monkeypatch,
):
    from app import media_archive_executor as executor
    from app.media_archive_staging import VolumeCapacity

    (
        engine, tenant_id, _gallery_id, folder_id, cycle_id, _archive_operation_id,
        restore_operation_id, selection_ids, photo_ids, payload_by_photo,
        source_root, staging_root, storage, first_claim,
    ) = _restore_fixture(tmp_path, monkeypatch)

    def ample_capacity(_path):
        return VolumeCapacity("b" * 64, 100 * 1024**3, 90 * 1024**3)

    original_promote = executor._promote_verified_object
    promoted = 0

    def interrupt_after_first(**kwargs):
        nonlocal promoted
        original_promote(**kwargs)
        promoted += 1
        if promoted == 1:
            raise SimulatedWorkerTermination()

    monkeypatch.setattr(executor, "_promote_verified_object", interrupt_after_first)
    try:
        with Session(engine, expire_on_commit=False) as db:
            with pytest.raises(SimulatedWorkerTermination):
                execute_restore_operation(
                    db, first_claim, storage=storage, staging_root=staging_root,
                    capacity_provider=ample_capacity,
                )
            db.rollback()
            operation = db.get(MediaArchiveOperation, restore_operation_id)
            cycle = db.get(MediaArchiveCycle, cycle_id)
            folder = db.get(PhotoFolder, folder_id)
            assert operation.status == "processing" and operation.stage == "promoting"
            assert cycle.state == "restoring"
            assert not folder_media_is_local(db, folder)
            reservation = db.scalar(sa.select(MediaArchiveRecoveryCreditReservation).where(
                MediaArchiveRecoveryCreditReservation.operation_id == restore_operation_id,
            ))
            assert reservation.status == "reserved"
            assert db.scalar(sa.select(PhotographerCreditEntry.id).where(
                PhotographerCreditEntry.archive_operation_id == restore_operation_id,
                PhotographerCreditEntry.entry_type == "archive_recovery",
            )) is None
            expires = operation.lease_expires_at
            if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.

            retry_claim = claim_next_operation(db, at=expires + timedelta(seconds=1))
            assert retry_claim is not None and retry_claim.operation_id == restore_operation_id
            monkeypatch.setattr(executor, "_promote_verified_object", original_promote)
            retry_result = execute_restore_operation(
                db, retry_claim, storage=storage, staging_root=staging_root,
                capacity_provider=ample_capacity,
            )
            assert retry_result == MediaArchiveExecutionResult(restore_operation_id, "completed")
            assert db.get(MediaArchiveCycle, cycle_id).state == "local"
            assert folder_media_is_local(db, db.get(PhotoFolder, folder_id))
            assert set(db.scalars(sa.select(PhotoSelection.id))) == set(selection_ids)
            assert db.scalar(sa.select(sa.func.count()).select_from(PhotoAsset).where(
                PhotoAsset.id.in_(photo_ids),
            )) == len(photo_ids)
            ledger = list(db.scalars(sa.select(PhotographerCreditEntry).where(
                PhotographerCreditEntry.archive_operation_id == restore_operation_id,
                PhotographerCreditEntry.entry_type == "archive_recovery",
            )))
            assert len(ledger) == 1 and ledger[0].delta == -2

        with Session(engine) as db:
            for photo in db.scalars(sa.select(PhotoAsset).where(PhotoAsset.id.in_(photo_ids))):
                assert source_root.joinpath(*photo.storage_key.split("/")).read_bytes() == payload_by_photo[photo.id]
        assert not (staging_root / str(tenant_id) / str(restore_operation_id)).exists()
    finally:
        engine.dispose()


def test_restore_checksum_failure_releases_reservation_without_exposing_or_charging(
    tmp_path, monkeypatch,
):
    from app.media_archive_staging import VolumeCapacity

    (
        engine, tenant_id, _gallery_id, folder_id, cycle_id, _archive_operation_id,
        restore_operation_id, selection_ids, photo_ids, _payload_by_photo,
        source_root, staging_root, storage, claim,
    ) = _restore_fixture(tmp_path, monkeypatch)

    def ample_capacity(_path):
        return VolumeCapacity("c" * 64, 100 * 1024**3, 90 * 1024**3)

    with Session(engine, expire_on_commit=False) as db:
        media_row = db.scalar(sa.select(MediaArchiveObject).where(
            MediaArchiveObject.cycle_id == cycle_id,
            MediaArchiveObject.object_type != "manifest",
        ))
        assert media_row is not None and media_row.remote_object_id
        corrupt_id = media_row.remote_object_id
        original_download = storage.download_object

        def corrupt_one_object(*, remote_id, destination):
            if remote_id == corrupt_id:
                payload, _mime = storage.objects[remote_id]
                payload += b"corrupt"
                destination.write(payload)
                return ArchiveDownloadReceipt(len(payload), sha256(payload).hexdigest())
            return original_download(remote_id=remote_id, destination=destination)

        monkeypatch.setattr(storage, "download_object", corrupt_one_object)
        result = execute_restore_operation(
            db, claim, storage=storage, staging_root=staging_root,
            capacity_provider=ample_capacity,
        )
        assert result.status == "failed"
        assert result.error_code == "restore_failed"
        operation = db.get(MediaArchiveOperation, restore_operation_id)
        cycle = db.get(MediaArchiveCycle, cycle_id)
        folder = db.get(PhotoFolder, folder_id)
        assert operation.status == "failed"
        assert operation.last_error == "Falha comprovada na operação; mídia preservada."
        assert cycle.state == "archived"
        assert not folder_media_is_local(db, folder)
        assert set(db.scalars(sa.select(PhotoSelection.id))) == set(selection_ids)
        assert db.scalar(sa.select(sa.func.count()).select_from(PhotographerCreditEntry).where(
            PhotographerCreditEntry.archive_operation_id == restore_operation_id,
            PhotographerCreditEntry.entry_type == "archive_recovery",
        )) == 0
        reservation = db.scalar(sa.select(MediaArchiveRecoveryCreditReservation).where(
            MediaArchiveRecoveryCreditReservation.tenant_id == tenant_id,
            MediaArchiveRecoveryCreditReservation.operation_id == restore_operation_id,
        ))
        assert reservation.status == "released"
        assert set(db.scalars(sa.select(PhotoAsset.id).where(PhotoAsset.id.in_(photo_ids)))) == set(photo_ids)
        assert all(not source_root.joinpath(*photo.storage_key.split("/")).exists() for photo in db.scalars(
            sa.select(PhotoAsset).where(PhotoAsset.id.in_(photo_ids)),
        ))
    assert not (staging_root / str(tenant_id) / str(restore_operation_id)).exists()
    engine.dispose()


def test_restore_adapter_exception_details_are_sanitized_from_operation_and_audit(
    tmp_path, monkeypatch,
):
    from app.media_archive_staging import VolumeCapacity

    (
        engine, _tenant_id, _gallery_id, _folder_id, cycle_id, _archive_operation_id,
        restore_operation_id, _selection_ids, _photo_ids, _payload_by_photo,
        _source_root, staging_root, storage, claim,
    ) = _restore_fixture(tmp_path, monkeypatch)

    def ample_capacity(_path):
        return VolumeCapacity("f" * 64, 100 * 1024**3, 90 * 1024**3)

    with Session(engine, expire_on_commit=False) as db:
        def raise_sensitive_error(*, remote_id, destination):
            raise RuntimeError("credential=synthetic-secret path=C:/private/customer.jpg")

        monkeypatch.setattr(storage, "download_object", raise_sensitive_error)
        result = execute_restore_operation(
            db, claim, storage=storage, staging_root=staging_root,
            capacity_provider=ample_capacity,
        )
        operation = db.get(MediaArchiveOperation, restore_operation_id)
        events = list(db.scalars(sa.select(MediaArchiveEvent).where(
            MediaArchiveEvent.operation_id == restore_operation_id,
        )))
        assert result.status == "failed"
        assert result.error_code == "restore_runtimeerror"
        assert operation.last_error == "Falha comprovada na operação; mídia preservada."
        assert operation.last_error_code == "restore_runtimeerror"
        assert db.get(MediaArchiveCycle, cycle_id).state == "archived"
        assert all("synthetic-secret" not in repr(event.details) for event in events)
        assert all("C:/private/customer.jpg" not in repr(event.details) for event in events)
        assert all("synthetic-secret" not in event.last_error for event in [operation])

    assert not (staging_root / str(claim.tenant_id) / str(restore_operation_id)).exists()
    engine.dispose()


def test_restore_preflight_capacity_failure_releases_credit_and_downloads_nothing(
    tmp_path, monkeypatch,
):
    from app.media_archive_staging import VolumeCapacity

    (
        engine, tenant_id, _gallery_id, folder_id, cycle_id, _archive_operation_id,
        restore_operation_id, _selection_ids, _photo_ids, _payload_by_photo,
        _source_root, staging_root, storage, claim,
    ) = _restore_fixture(tmp_path, monkeypatch)

    def nearly_full_volume(_path):
        return VolumeCapacity("d" * 64, 100 * 1024**3, 15 * 1024**3)

    try:
        with Session(engine, expire_on_commit=False) as db:
            result = execute_restore_operation(
                db, claim, storage=storage, staging_root=staging_root,
                capacity_provider=nearly_full_volume,
            )
            assert result.status == "failed"
            assert result.error_code == "insufficient_space"
            operation = db.get(MediaArchiveOperation, restore_operation_id)
            cycle = db.get(MediaArchiveCycle, cycle_id)
            folder = db.get(PhotoFolder, folder_id)
            assert operation.status == "failed"
            assert cycle.state == "archived"
            assert not folder_media_is_local(db, folder)
            reservation = db.scalar(sa.select(MediaArchiveRecoveryCreditReservation).where(
                MediaArchiveRecoveryCreditReservation.tenant_id == tenant_id,
                MediaArchiveRecoveryCreditReservation.operation_id == restore_operation_id,
            ))
            assert reservation.status == "released"
            assert db.scalar(sa.select(sa.func.count()).select_from(PhotographerCreditEntry).where(
                PhotographerCreditEntry.archive_operation_id == restore_operation_id,
                PhotographerCreditEntry.entry_type == "archive_recovery",
            )) == 0
            assert photographer_credits.wallet_snapshot(db, tenant_id)["available_credits"] == 5
            assert db.scalar(sa.select(sa.func.count()).select_from(MediaArchiveRecoveryCreditReservation).where(
                MediaArchiveRecoveryCreditReservation.operation_id == restore_operation_id,
                MediaArchiveRecoveryCreditReservation.status == "reserved",
            )) == 0
        assert not (staging_root / str(tenant_id) / str(restore_operation_id)).exists()
        assert len(storage.objects) == 3  # manifesto e originais continuam somente remotos
    finally:
        engine.dispose()


def test_restore_never_overwrites_a_divergent_existing_destination(
    tmp_path, monkeypatch,
):
    from app.media_archive_staging import VolumeCapacity

    (
        engine, tenant_id, _gallery_id, folder_id, cycle_id, _archive_operation_id,
        restore_operation_id, _selection_ids, photo_ids, _payload_by_photo,
        source_root, staging_root, storage, claim,
    ) = _restore_fixture(tmp_path, monkeypatch)

    def ample_capacity(_path):
        return VolumeCapacity("e" * 64, 100 * 1024**3, 90 * 1024**3)

    unexpected_bytes = b"pre-existing unrelated local file"
    with Session(engine, expire_on_commit=False) as db:
        photo = db.get(PhotoAsset, photo_ids[0])
        destination = source_root.joinpath(*photo.storage_key.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(unexpected_bytes)
        result = execute_restore_operation(
            db, claim, storage=storage, staging_root=staging_root,
            capacity_provider=ample_capacity,
        )
        assert result.status == "failed"
        assert result.error_code == "restore_target_invalid"
        assert destination.read_bytes() == unexpected_bytes
        assert db.get(MediaArchiveCycle, cycle_id).state == "archived"
        assert not folder_media_is_local(db, db.get(PhotoFolder, folder_id))
        assert db.scalar(sa.select(sa.func.count()).select_from(PhotographerCreditEntry).where(
            PhotographerCreditEntry.archive_operation_id == restore_operation_id,
            PhotographerCreditEntry.entry_type == "archive_recovery",
        )) == 0
        reservation = db.scalar(sa.select(MediaArchiveRecoveryCreditReservation).where(
            MediaArchiveRecoveryCreditReservation.operation_id == restore_operation_id,
        ))
        assert reservation.status == "released"
    assert not (staging_root / str(tenant_id) / str(restore_operation_id)).exists()
    engine.dispose()
