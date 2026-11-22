"""Contratos sintéticos do adapter privado de backup Google Workspace."""

from __future__ import annotations

import hashlib
import io
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.auth import GoogleDriveConnection, now
from app.google_drive_client import SCOPE, TOKEN_ENDPOINT
from app.google_drive_storage import DriveUploadError, DriveUploadReceipt
from app.integration_secrets import IntegrationCipher
from app.platform_backup.archive import ArchiveReceipt, BackupContext, seal_archive
from app.platform_backup.catalog import BackupCatalog
from app.platform_backup.filesystem import BackupStorageError
from app.platform_backup.payload import build_payload
from app.platform_backup.remote_copy import copy_workspace_backup, restore_workspace_backup
from app.platform_backup.restore import RestoreTargetState
from app.platform_backup.workspace_credentials import create_workspace_backup_store
from app.platform_backup.workspace_store import (
    BACKUP_MIME_TYPE,
    FILES_ENDPOINT,
    WorkspaceDriveBackupStore,
)
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


class SyntheticDrive:
    def __init__(self) -> None:
        self.folder_id = "synthetic_private_folder_01"
        self.files: list[dict[str, object]] = []
        self.bodies: dict[str, bytes] = {}
        self.pending: dict[str, object] | None = None
        self.list_status = 200
        self.list_error_payload: dict[str, object] | None = None
        self.incomplete_search = False
        self.delete_status = 204
        self.upload_starts = 0
        self.stream_reads = 0
        self.last_query: dict[str, str] = {}
        self.token = "synthetic-access-token"

    def post(self, url: str, **kwargs) -> httpx.Response:
        assert url == "https://www.googleapis.com/upload/drive/v3/files"
        assert kwargs["headers"]["Authorization"] == f"Bearer {self.token}"
        self.pending = kwargs["json"]
        self.upload_starts += 1
        return httpx.Response(
            200,
            headers={"Location": url + "?upload_id=synthetic-session"},
        )

    def put(self, url: str, **kwargs) -> httpx.Response:
        assert url.endswith("?upload_id=synthetic-session")
        assert kwargs["headers"]["Authorization"] == f"Bearer {self.token}"
        assert self.pending is not None
        content = kwargs["content"]
        file_id = f"synthetic_file_{self.upload_starts}"
        metadata = {
            "id": file_id,
            "name": self.pending["name"],
            "mimeType": self.pending["mimeType"],
            "size": str(len(content)),
            "md5Checksum": hashlib.md5(content, usedforsecurity=False).hexdigest(),
            "parents": [self.pending["parents"][0]],
        }
        self.files.append(metadata)
        self.bodies[file_id] = content
        return httpx.Response(201, json=metadata)

    def get(self, url: str, **kwargs) -> httpx.Response:
        assert kwargs["headers"]["Authorization"] == f"Bearer {self.token}"
        if url.startswith(FILES_ENDPOINT + "/"):
            file_id = url.rsplit("/", 1)[1]
            item = next((value for value in self.files if value["id"] == file_id), None)
            return httpx.Response(404) if item is None else httpx.Response(200, json=item)
        assert url == FILES_ENDPOINT
        self.last_query = kwargs["params"]
        if self.list_status != 200:
            return httpx.Response(self.list_status, json=self.list_error_payload or {
                "error": {"message": "sensitive-provider-error"}
            })
        name = self.last_query["q"].split("'", 2)[1]
        parent = self.last_query["q"].split("'")[3]
        matched = [item for item in self.files
                   if item["name"] == name and parent in item["parents"]]
        return httpx.Response(200, json={
            "files": matched,
            "incompleteSearch": self.incomplete_search,
        })

    def delete(self, url: str, **kwargs) -> httpx.Response:
        assert url.startswith(FILES_ENDPOINT + "/")
        assert kwargs["headers"]["Authorization"] == f"Bearer {self.token}"
        if self.delete_status not in {200, 204}:
            return httpx.Response(self.delete_status)
        file_id = url.rsplit("/", 1)[1]
        self.files = [item for item in self.files if item["id"] != file_id]
        self.bodies.pop(file_id, None)
        return httpx.Response(self.delete_status)

    @contextmanager
    def stream_get(self, url: str, **kwargs):
        assert kwargs["params"]["alt"] == "media"
        assert kwargs["headers"]["Authorization"] == f"Bearer {self.token}"
        file_id = url.rsplit("/", 1)[1]
        self.stream_reads += 1
        yield httpx.Response(200, content=self.bodies[file_id])


def receipt(data: bytes, backup_id=None) -> ArchiveReceipt:
    return ArchiveReceipt(backup_id or uuid4(), len(data), hashlib.sha256(data).hexdigest())


def make_store(drive: SyntheticDrive) -> WorkspaceDriveBackupStore:
    return WorkspaceDriveBackupStore(
        destination_id=uuid4(),
        parent_folder_id=drive.folder_id,
        access_token=SecretStr(drive.token),
        transport=drive,
    )


class MemoryCatalog(BackupCatalog):
    def __init__(self) -> None:
        super().__init__(Path("."), bytes(range(32)))
        object.__setattr__(self, "records", [])

    def events(self, backup_id):
        return list(self.records)

    def append(self, backup_id, event, *, at, **values):
        data = {key: str(value) if isinstance(value, UUID) else value
                for key, value in values.items()}
        record = {"payload": {"event": event, "at": at.isoformat(), "data": data}}
        self.records.append(record)
        return record


def encrypted_artifact():
    key = bytes(range(32))
    context = BackupContext(
        uuid4(), uuid4(), "20261106_0106", "test", datetime(2026, 11, 6, 12, tzinfo=UTC)
    )
    package = io.BytesIO()
    build_payload(io.BytesIO(b"PGDMP-synthetic-global-dump"),
                  {"SYNTHETIC_CONFIG": "must-stay-encrypted"}, package, context=context)
    package.seek(0)
    ciphertext = io.BytesIO()
    receipt = seal_archive(package, ciphertext, key=key, context=context)
    ciphertext.seek(0)
    return key, context, ciphertext, receipt


class SyntheticRestoreTarget:
    def __init__(self, schema_revision: str) -> None:
        self.state = RestoreTargetState(uuid4(), "test", True, True, True)
        self.schema_revision = schema_revision
        self.dump = b""

    def inspect(self) -> RestoreTargetState:
        return self.state

    def restore(self, dump) -> None:
        self.dump = dump.read()

    def verify(self, schema_revision: str) -> bool:
        return schema_revision == self.schema_revision and self.dump.startswith(b"PGDMP-")


def test_upload_and_streaming_readback_use_only_ciphertext_and_redact_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    store = make_store(drive)
    ciphertext = b"PYPBACK1-synthetic-ciphertext" * 100
    artifact = receipt(ciphertext)

    copied = store.upload(io.BytesIO(ciphertext), artifact)
    with store.open(artifact.backup_id) as remote:
        assert remote.read() == ciphertext

    assert copied.backup_id == artifact.backup_id
    assert copied.size_bytes == len(ciphertext)
    assert copied.sha256 == artifact.sha256
    assert drive.bodies == {"synthetic_file_1": ciphertext}
    assert drive.upload_starts == drive.stream_reads == 1
    assert drive.last_query["supportsAllDrives"] == "true"
    assert "webViewLink" not in drive.last_query["fields"]
    assert BACKUP_MIME_TYPE == drive.files[0]["mimeType"]
    assert drive.files[0]["name"] == f"{artifact.backup_id}.pypb"
    assert drive.folder_id not in repr(store)
    assert drive.token not in repr(store)


def test_synthetic_destination_item_is_read_back_and_deleted_by_exact_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    store = make_store(drive)
    name = "pyp-backup-rehearsal-" + "a" * 32 + ".txt"
    content = b"Pick-your-Pic synthetic destination rehearsal\n" + b"a" * 32 + b"\n"

    uploaded = store.upload_rehearsal_item(name=name, content=content)
    assert uploaded.size_bytes == len(content)
    assert uploaded.sha256 == hashlib.sha256(content).hexdigest()
    assert store.read_rehearsal_item(file_id=uploaded.file_id, name=name) == content
    assert store.delete_rehearsal_item(file_id=uploaded.file_id, name=name) is True

    assert drive.files == []
    assert drive.bodies == {}


def test_synthetic_delete_refuses_an_object_outside_the_bound_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    store = make_store(drive)
    name = "pyp-backup-rehearsal-" + "b" * 32 + ".txt"
    content = b"synthetic payload"
    uploaded = store.upload_rehearsal_item(name=name, content=content)
    drive.files[0]["parents"] = ["another-folder"]

    with pytest.raises(BackupStorageError) as error:
        store.delete_rehearsal_item(file_id=uploaded.file_id, name=name)

    assert error.value.code == "conflict"
    assert drive.delete_status == 204
    assert len(drive.files) == 1


def test_synthetic_delete_failure_is_not_reported_as_cleaned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    store = make_store(drive)
    name = "pyp-backup-rehearsal-" + "c" * 32 + ".txt"
    uploaded = store.upload_rehearsal_item(name=name, content=b"synthetic payload")
    drive.delete_status = 500

    with pytest.raises(BackupStorageError) as error:
        store.delete_rehearsal_item(file_id=uploaded.file_id, name=name)

    assert error.value.code == "io"
    assert len(drive.files) == 1


def test_store_without_explicit_transport_fails_closed_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    store = WorkspaceDriveBackupStore(
        destination_id=uuid4(),
        parent_folder_id="synthetic_private_folder_01",
        access_token=SecretStr("synthetic-access-token"),
    )

    with pytest.raises(BackupStorageError) as error, store.open(uuid4()):
        pass

    assert error.value.code == "unsafe"


def test_retry_is_idempotent_and_conflicting_ciphertext_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    store = make_store(drive)
    backup_id = uuid4()
    original = b"opaque-ciphertext-one"
    first_receipt = receipt(original, backup_id)

    store.upload(io.BytesIO(original), first_receipt)
    store.upload(io.BytesIO(original), first_receipt)

    changed = b"opaque-ciphertext-two"
    with pytest.raises(BackupStorageError) as error:
        store.upload(io.BytesIO(changed), receipt(changed, backup_id))

    assert error.value.code == "conflict"
    assert drive.upload_starts == 1
    assert drive.bodies["synthetic_file_1"] == original


def test_duplicate_remote_objects_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    store = make_store(drive)
    backup_id = uuid4()
    data = b"opaque-ciphertext"
    store.upload(io.BytesIO(data), receipt(data, backup_id))
    duplicate = dict(drive.files[0], id="synthetic_file_duplicate")
    drive.files.append(duplicate)
    drive.bodies["synthetic_file_duplicate"] = data

    with pytest.raises(BackupStorageError) as error, store.open(backup_id):
        pass

    assert error.value.code == "conflict"
    assert drive.upload_starts == 1


def test_readback_checksum_mismatch_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    store = make_store(drive)
    data = b"verified-ciphertext"
    artifact = receipt(data)
    store.upload(io.BytesIO(data), artifact)
    drive.bodies["synthetic_file_1"] = b"altered-ciphertext"

    with pytest.raises(BackupStorageError) as error, store.open(artifact.backup_id):
        pass

    assert error.value.code == "checksum"


@pytest.mark.parametrize("status_code", [401, 403, 404])
def test_provider_authorization_errors_are_sanitized(
    monkeypatch: pytest.MonkeyPatch, status_code: int,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    drive.list_status = status_code
    store = make_store(drive)

    with pytest.raises(BackupStorageError) as error, store.open(uuid4()):
        pass

    assert error.value.code == "authorization"
    assert drive.token not in str(error.value)
    assert "sensitive-provider-error" not in str(error.value)


def test_workspace_quota_error_is_classified_without_reflecting_provider_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    drive.list_status = 403
    drive.list_error_payload = {
        "error": {"errors": [{"reason": "storageQuotaExceeded"}],
                  "message": "private synthetic detail"}
    }

    with pytest.raises(BackupStorageError) as error, make_store(drive).open(uuid4()):
        pass

    assert error.value.code == "quota"
    assert "private synthetic detail" not in str(error.value)
    assert "storageQuotaExceeded" not in str(error.value)


def test_shared_drive_lookup_is_narrow_and_incomplete_search_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    store = WorkspaceDriveBackupStore(
        destination_id=uuid4(),
        parent_folder_id=drive.folder_id,
        access_token=SecretStr(drive.token),
        shared_drive_id="synthetic_shared_drive_01",
        transport=drive,
    )
    data = b"opaque-ciphertext"
    artifact = receipt(data)

    store.upload(io.BytesIO(data), artifact)

    assert drive.last_query["corpora"] == "drive"
    assert drive.last_query["driveId"] == "synthetic_shared_drive_01"
    assert drive.last_query["corpora"] != "allDrives"
    drive.incomplete_search = True
    with pytest.raises(BackupStorageError) as error, store.open(artifact.backup_id):
        pass
    assert error.value.code == "conflict"


def test_lost_upload_confirmation_reuses_existing_object_without_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()
    attempts = 0

    def upload_then_lose_confirmation(**kwargs) -> DriveUploadReceipt:
        nonlocal attempts
        attempts += 1
        content = kwargs["stream"].read()
        file_id = "synthetic_file_after_lost_response"
        metadata = {
            "id": file_id,
            "name": kwargs["name"],
            "mimeType": kwargs["mime_type"],
            "size": str(len(content)),
            "md5Checksum": hashlib.md5(content, usedforsecurity=False).hexdigest(),
            "parents": [kwargs["parent_folder_id"]],
        }
        drive.files.append(metadata)
        drive.bodies[file_id] = content
        raise DriveUploadError("synthetic response lost", code="io")

    store = WorkspaceDriveBackupStore(
        destination_id=uuid4(),
        parent_folder_id=drive.folder_id,
        access_token=SecretStr(drive.token),
        transport=drive,
        uploader=upload_then_lose_confirmation,
    )
    data = b"opaque-ciphertext-after-lost-response"
    artifact = receipt(data)

    with pytest.raises(BackupStorageError):
        store.upload(io.BytesIO(data), artifact)
    copied = store.upload(io.BytesIO(data), artifact)

    assert copied.sha256 == artifact.sha256
    assert attempts == 1
    assert len(drive.files) == 1
    assert drive.stream_reads == 1


def test_upload_confirmation_must_match_archive_size_and_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    drive = SyntheticDrive()

    def forged_uploader(**kwargs) -> DriveUploadReceipt:
        return DriveUploadReceipt("synthetic_file_1", kwargs["size_bytes"], "0" * 64)

    store = WorkspaceDriveBackupStore(
        destination_id=uuid4(),
        parent_folder_id=drive.folder_id,
        access_token=SecretStr(drive.token),
        transport=drive,
        uploader=forged_uploader,
    )
    data = b"opaque-ciphertext"

    with pytest.raises(BackupStorageError) as error:
        store.upload(io.BytesIO(data), receipt(data))

    assert error.value.code == "conflict"
    assert drive.upload_starts == 0


def test_workspace_copy_is_verified_before_catalog_marks_it_recoverable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    drive = SyntheticDrive()
    key, context, ciphertext, archive_receipt = encrypted_artifact()

    def synthetic_uploader(**kwargs) -> DriveUploadReceipt:
        stream = kwargs["stream"]
        stream.seek(0)
        body = stream.read()
        assert b"must-stay-encrypted" not in body
        file_id = "synthetic_file_from_uploader"
        metadata = {
            "id": file_id,
            "name": kwargs["name"],
            "mimeType": kwargs["mime_type"],
            "size": str(len(body)),
            "md5Checksum": hashlib.md5(body, usedforsecurity=False).hexdigest(),
            "parents": [kwargs["parent_folder_id"]],
        }
        drive.files.append(metadata)
        drive.bodies[file_id] = body
        return DriveUploadReceipt(file_id, len(body), hashlib.sha256(body).hexdigest())

    store = WorkspaceDriveBackupStore(
        destination_id=uuid4(),
        parent_folder_id=drive.folder_id,
        access_token=SecretStr(drive.token),
        transport=drive,
        uploader=synthetic_uploader,
    )
    catalog = MemoryCatalog()
    now = datetime(2026, 11, 6, 13, tzinfo=UTC)

    copy = copy_workspace_backup(ciphertext, receipt=archive_receipt, context=context,
                                 key=key, store=store, catalog=catalog, at=now)
    target = SyntheticRestoreTarget(context.schema_revision)
    restored = restore_workspace_backup(
        receipt=archive_receipt,
        context=context,
        key=key,
        store=store,
        catalog=catalog,
        target=target,
        at=now + timedelta(minutes=1),
    )

    events = [item["payload"]["event"] for item in catalog.records]
    assert events == ["copy_started", "uploaded", "verified", "restore_verified"]
    assert copy.backup_id == context.backup_id
    assert copy.sha256 == archive_receipt.sha256
    assert restored.target_instance_id == target.state.instance_id
    assert target.dump == b"PGDMP-synthetic-global-dump"
    assert "must-stay-encrypted" not in str(catalog.records)


def test_workspace_copy_with_valid_checksum_but_invalid_gcm_is_not_recoverable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    drive = SyntheticDrive()
    key, context, ciphertext, _original_receipt = encrypted_artifact()
    damaged = bytearray(ciphertext.read())
    damaged[-1] ^= 1
    data = bytes(damaged)
    damaged_receipt = ArchiveReceipt(
        context.backup_id,
        len(data),
        hashlib.sha256(data).hexdigest(),
    )

    def synthetic_uploader(**kwargs) -> DriveUploadReceipt:
        body = kwargs["stream"].read()
        file_id = "synthetic_damaged_ciphertext"
        drive.files.append({
            "id": file_id,
            "name": kwargs["name"],
            "mimeType": kwargs["mime_type"],
            "size": str(len(body)),
            "md5Checksum": hashlib.md5(body, usedforsecurity=False).hexdigest(),
            "parents": [kwargs["parent_folder_id"]],
        })
        drive.bodies[file_id] = body
        return DriveUploadReceipt(file_id, len(body), hashlib.sha256(body).hexdigest())

    store = WorkspaceDriveBackupStore(
        destination_id=uuid4(),
        parent_folder_id=drive.folder_id,
        access_token=SecretStr(drive.token),
        transport=drive,
        uploader=synthetic_uploader,
    )
    catalog = MemoryCatalog()
    now = datetime(2026, 11, 6, 13, tzinfo=UTC)

    with pytest.raises(BackupStorageError) as error:
        copy_workspace_backup(io.BytesIO(data), receipt=damaged_receipt, context=context,
                              key=key, store=store, catalog=catalog, at=now)

    assert error.value.code == "checksum"
    events = [item["payload"]["event"] for item in catalog.records]
    assert events == ["copy_started", "uploaded", "failed"]
    assert catalog.records[-1]["payload"]["data"]["code"] == "checksum"


def test_owner_oauth_credential_provider_composes_with_verified_workspace_copy(client_db):
    owner_tenant, _tenant, owner, _photographer = create_accounts(client_db)
    cipher = IntegrationCipher()
    connection_id = uuid4()
    refresh_envelope = cipher.encrypt(
        "synthetic-refresh-token",
        tenant_id=owner_tenant.id,
        credential_id=connection_id,
    ).payload()
    client_db.add(GoogleDriveConnection(
        id=connection_id,
        tenant_id=owner_tenant.id,
        connected_by_admin_id=owner.id,
        refresh_token_envelope=refresh_envelope,
        scopes=SCOPE,
        state="connected",
        connected_at=now(),
        updated_at=now(),
    ))
    client_db.commit()

    drive = SyntheticDrive()

    class SyntheticTokenTransport:
        def __init__(self):
            self.calls = []

        def post(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return SimpleNamespace(status_code=200, json=lambda: {
                "access_token": drive.token,
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": SCOPE,
            })

    token_transport = SyntheticTokenTransport()

    def synthetic_uploader(**kwargs):
        stream = kwargs["stream"]
        stream.seek(0)
        body = stream.read()
        file_id = "synthetic_oauth_backup_file"
        metadata = {
            "id": file_id,
            "name": kwargs["name"],
            "mimeType": kwargs["mime_type"],
            "size": str(len(body)),
            "md5Checksum": hashlib.md5(body, usedforsecurity=False).hexdigest(),
            "parents": [kwargs["parent_folder_id"]],
        }
        drive.files.append(metadata)
        drive.bodies[file_id] = body
        return DriveUploadReceipt(file_id, len(body), hashlib.sha256(body).hexdigest())

    store = create_workspace_backup_store(
        client_db,
        tenant_id=owner_tenant.id,
        destination_id=uuid4(),
        parent_folder_id=drive.folder_id,
        client_id="synthetic-client-id",
        client_secret=SecretStr("synthetic-client-secret"),
        cipher=cipher,
        token_transport=token_transport,
        drive_transport=drive,
        uploader=synthetic_uploader,
    )
    key, context, ciphertext, archive_receipt = encrypted_artifact()
    catalog = MemoryCatalog()
    copied = copy_workspace_backup(
        ciphertext,
        receipt=archive_receipt,
        context=context,
        key=key,
        store=store,
        catalog=catalog,
        at=datetime(2026, 11, 7, 13, tzinfo=UTC),
    )

    assert copied.backup_id == context.backup_id
    assert [record["payload"]["event"] for record in catalog.records] == [
        "copy_started", "uploaded", "verified",
    ]
    assert token_transport.calls[0][0] == TOKEN_ENDPOINT
    assert token_transport.calls[0][1]["data"]["refresh_token"] == "synthetic-refresh-token"
    assert store.access_token.get_secret_value() == drive.token
    assert "synthetic-refresh-token" not in str(catalog.records)
    assert "synthetic-access-token" not in str(catalog.records)
