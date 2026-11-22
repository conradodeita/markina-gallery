from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from io import BytesIO
from uuid import UUID

import pytest
from pydantic import SecretStr

from app.google_drive_media_archive_storage import (
    DRIVE_FILES_URL,
    DRIVE_FOLDER_MIME,
    MEDIA_NAMESPACE,
    GoogleDriveMediaArchiveError,
    GoogleDriveMediaArchiveStorage,
)
from app.google_drive_storage import DriveUploadError, upload_drive_file

TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")
OBJECT_KEY = (
    "11111111-1111-4111-8111-111111111111/"
    "22222222-2222-4222-8222-222222222222/"
    "33333333-3333-4333-8333-333333333333/"
    "44444444-4444-4444-8444-444444444444/"
    "55555555-5555-4555-8555-555555555555"
)
ROOT_ID = "synthetic-media-root"
TENANT_FOLDER_ID = "synthetic-tenant-folder"
GALLERY_FOLDER_ID = "synthetic-gallery-folder"
CONTENT_FOLDER_ID = "synthetic-content-folder"
CYCLE_FOLDER_ID = "synthetic-cycle-folder"
FILE_ID = "synthetic-media-file"
GALLERY_ID, FOLDER_ID, CYCLE_ID = OBJECT_KEY.split("/")[1:4]


class FakeResponse:
    def __init__(self, status_code: int, payload=None, *, headers=None, chunks=()):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload
        self._chunks = tuple(chunks)
        self.content = json.dumps(payload or {}).encode("utf-8")

    def json(self):
        return self._payload

    def iter_bytes(self, chunk_size=65536):
        del chunk_size
        yield from self._chunks


class SyntheticDriveTransport:
    """Fila de respostas HTTP sintéticas; nunca abre rede."""

    def __init__(self):
        self.calls = []
        self.responses = {method: [] for method in ("GET", "POST", "PUT", "DELETE", "STREAM_GET")}

    def respond(self, method: str, response: FakeResponse):
        self.responses[method].append(response)

    def _take(self, method: str, url: str, kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses[method]:
            raise AssertionError(f"Resposta sintética ausente para {method} {url}")
        return self.responses[method].pop(0)

    def get(self, url: str, **kwargs):
        return self._take("GET", url, kwargs)

    def post(self, url: str, **kwargs):
        return self._take("POST", url, kwargs)

    def put(self, url: str, **kwargs):
        return self._take("PUT", url, kwargs)

    def delete(self, url: str, **kwargs):
        return self._take("DELETE", url, kwargs)

    @contextmanager
    def stream_get(self, url: str, **kwargs):
        yield self._take("STREAM_GET", url, kwargs)


def adapter(transport: SyntheticDriveTransport) -> GoogleDriveMediaArchiveStorage:
    return GoogleDriveMediaArchiveStorage(
        access_token=SecretStr("synthetic-access-token"),
        media_root_id=ROOT_ID,
        tenant_id=TENANT_ID,
        transport=transport,
    )


def tenant_folder_resource():
    return {
        "id": TENANT_FOLDER_ID,
        "name": str(TENANT_ID),
        "mimeType": DRIVE_FOLDER_MIME,
        "parents": [ROOT_ID],
        "trashed": False,
        "appProperties": {
            "pyp_media_namespace": MEDIA_NAMESPACE,
            "pyp_media_tenant": str(TENANT_ID),
            "pyp_media_kind": "tenant",
        },
    }


def gallery_folder_resource():
    return {
        "id": GALLERY_FOLDER_ID,
        "name": GALLERY_ID,
        "mimeType": DRIVE_FOLDER_MIME,
        "parents": [TENANT_FOLDER_ID],
        "trashed": False,
        "appProperties": {
            "pyp_media_namespace": MEDIA_NAMESPACE,
            "pyp_media_tenant": str(TENANT_ID),
            "pyp_media_kind": "gallery",
            "pyp_media_gallery": GALLERY_ID,
        },
    }


def content_folder_resource():
    return {
        "id": CONTENT_FOLDER_ID,
        "name": FOLDER_ID,
        "mimeType": DRIVE_FOLDER_MIME,
        "parents": [GALLERY_FOLDER_ID],
        "trashed": False,
        "appProperties": {
            "pyp_media_namespace": MEDIA_NAMESPACE,
            "pyp_media_tenant": str(TENANT_ID),
            "pyp_media_kind": "folder",
            "pyp_media_gallery": GALLERY_ID,
            "pyp_media_folder": FOLDER_ID,
        },
    }


def cycle_folder_resource():
    return {
        "id": CYCLE_FOLDER_ID,
        "name": CYCLE_ID,
        "mimeType": DRIVE_FOLDER_MIME,
        "parents": [CONTENT_FOLDER_ID],
        "trashed": False,
        "appProperties": {
            "pyp_media_namespace": MEDIA_NAMESPACE,
            "pyp_media_tenant": str(TENANT_ID),
            "pyp_media_kind": "cycle",
            "pyp_media_gallery": GALLERY_ID,
            "pyp_media_folder": FOLDER_ID,
            "pyp_media_cycle": CYCLE_ID,
        },
    }


def file_resource(payload: bytes, *, parent_folder_id=CYCLE_FOLDER_ID, object_key=OBJECT_KEY):
    key_hash = hashlib.sha256(object_key.encode("ascii")).hexdigest()
    return {
        "id": FILE_ID,
        "name": key_hash,
        "mimeType": "image/jpeg",
        "size": str(len(payload)),
        "parents": [parent_folder_id],
        "trashed": False,
        "md5Checksum": hashlib.md5(payload, usedforsecurity=False).hexdigest(),
        "appProperties": {
            "pyp_media_namespace": MEDIA_NAMESPACE,
            "pyp_media_tenant": str(TENANT_ID),
            "pyp_media_kind": "object",
            "pyp_media_gallery": GALLERY_ID,
            "pyp_media_folder": FOLDER_ID,
            "pyp_media_cycle": CYCLE_ID,
            "pyp_media_object": key_hash,
            "pyp_media_sha256": hashlib.sha256(payload).hexdigest(),
        },
    }


def queue_folder_lookup(transport: SyntheticDriveTransport, resource=None):
    transport.respond(
        "GET",
        FakeResponse(200, {"incompleteSearch": False, "files": [resource] if resource else []}),
    )


def queue_existing_path(transport: SyntheticDriveTransport):
    for resource in (
        tenant_folder_resource(),
        gallery_folder_resource(),
        content_folder_resource(),
        cycle_folder_resource(),
    ):
        queue_folder_lookup(transport, resource)


def queue_new_path(transport: SyntheticDriveTransport):
    resources = (
        tenant_folder_resource(),
        gallery_folder_resource(),
        content_folder_resource(),
        cycle_folder_resource(),
    )
    for _ in resources:
        queue_folder_lookup(transport)
    for resource in resources:
        transport.respond("POST", FakeResponse(200, resource))


def queue_owned_file_lookup(transport: SyntheticDriveTransport, resource):
    transport.respond("GET", FakeResponse(200, resource))
    queue_existing_path(transport)


def test_upload_builds_private_media_hierarchy_and_hash_properties(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    payload = b"synthetic media bytes"
    digest = hashlib.sha256(payload).hexdigest()
    transport = SyntheticDriveTransport()
    queue_new_path(transport)
    queue_folder_lookup(transport)
    transport.respond(
        "POST",
        FakeResponse(
            200,
            headers={"Location": "https://www.googleapis.com/upload/drive/v3/files?upload_id=synthetic"},
        ),
    )
    transport.respond("PUT", FakeResponse(200, file_resource(payload)))

    result = adapter(transport).upload_object(
        object_key=OBJECT_KEY,
        mime_type="image/jpeg",
        size_bytes=len(payload),
        sha256=digest,
        stream=BytesIO(payload),
    )

    assert (result.remote_id, result.size_bytes, result.mime_type) == (FILE_ID, len(payload), "image/jpeg")
    folder_create = next(call for call in transport.calls if call[0] == "POST" and call[1] == DRIVE_FILES_URL)
    assert folder_create[2]["json"]["name"] == str(TENANT_ID)
    assert folder_create[2]["json"]["parents"] == [ROOT_ID]
    upload_start = next(call for call in transport.calls if call[1].startswith("https://www.googleapis.com/upload/"))
    properties = upload_start[2]["json"]["appProperties"]
    assert properties["pyp_media_namespace"] == MEDIA_NAMESPACE
    assert properties["pyp_media_tenant"] == str(TENANT_ID)
    assert properties["pyp_media_kind"] == "object"
    assert properties["pyp_media_gallery"] == GALLERY_ID
    assert properties["pyp_media_folder"] == FOLDER_ID
    assert properties["pyp_media_cycle"] == CYCLE_ID
    assert properties["pyp_media_object"] == hashlib.sha256(OBJECT_KEY.encode("ascii")).hexdigest()
    assert properties["pyp_media_sha256"] == digest
    assert OBJECT_KEY not in repr(upload_start[2]["json"])
    assert upload_start[2]["json"]["parents"] == [CYCLE_FOLDER_ID]
    assert [call[2]["json"]["name"] for call in transport.calls if call[0] == "POST" and call[1] == DRIVE_FILES_URL] == [
        str(TENANT_ID), GALLERY_ID, FOLDER_ID, CYCLE_ID,
    ]
    assert all(call[2]["headers"]["Authorization"] == "Bearer synthetic-access-token" for call in transport.calls)


def test_idempotent_retry_returns_same_file_and_rejects_changed_content(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    original = b"original synthetic bytes"
    transport = SyntheticDriveTransport()
    queue_existing_path(transport)
    queue_folder_lookup(transport, file_resource(original))

    result = adapter(transport).upload_object(
        object_key=OBJECT_KEY,
        mime_type="image/jpeg",
        size_bytes=len(original),
        sha256=hashlib.sha256(original).hexdigest(),
        stream=BytesIO(original),
    )
    assert result.remote_id == FILE_ID
    assert all(call[0] not in {"POST", "PUT"} for call in transport.calls)

    changed = b"different synthetic content"
    changed_transport = SyntheticDriveTransport()
    queue_existing_path(changed_transport)
    changed_resource = file_resource(original)
    changed_resource["size"] = str(len(changed))
    queue_folder_lookup(changed_transport, changed_resource)
    with pytest.raises(GoogleDriveMediaArchiveError) as error:
        adapter(changed_transport).upload_object(
            object_key=OBJECT_KEY,
            mime_type="image/jpeg",
            size_bytes=len(changed),
            sha256=hashlib.sha256(changed).hexdigest(),
            stream=BytesIO(changed),
        )
    assert error.value.code == "conflict"
    assert all(call[0] not in {"POST", "PUT"} for call in changed_transport.calls)


def test_duplicate_tenant_folder_or_object_fails_closed():
    duplicate_folder = SyntheticDriveTransport()
    folder = tenant_folder_resource()
    duplicate_folder.respond("GET", FakeResponse(200, file_resource(b"owned")))
    duplicate_folder.respond(
        "GET",
        FakeResponse(200, {"incompleteSearch": False, "files": [folder, folder]}),
    )
    with pytest.raises(GoogleDriveMediaArchiveError) as folder_error:
        adapter(duplicate_folder).read_object(remote_id=FILE_ID)
    assert folder_error.value.code == "conflict"

    duplicate_object = SyntheticDriveTransport()
    queue_existing_path(duplicate_object)
    resource = file_resource(b"duplicate")
    duplicate_object.respond(
        "GET", FakeResponse(200, {"incompleteSearch": False, "files": [resource, resource]}),
    )
    with pytest.raises(GoogleDriveMediaArchiveError) as object_error:
        adapter(duplicate_object).upload_object(
            object_key=OBJECT_KEY,
            mime_type="image/jpeg",
            size_bytes=len(b"duplicate"),
            sha256=hashlib.sha256(b"duplicate").hexdigest(),
            stream=BytesIO(b"duplicate"),
        )
    assert object_error.value.code == "conflict"
    assert all(call[0] not in {"POST", "PUT"} for call in duplicate_object.calls)


@pytest.mark.parametrize(
    "response_payload",
    [
        {"incompleteSearch": True, "files": []},
        {"incompleteSearch": False, "files": [], "nextPageToken": "synthetic-next"},
        {"files": []},
    ],
)
@pytest.mark.parametrize("object_search", [False, True])
def test_incomplete_or_paginated_search_never_authorizes_write(response_payload, object_search):
    transport = SyntheticDriveTransport()
    if object_search:
        queue_existing_path(transport)
    transport.respond("GET", FakeResponse(200, response_payload))

    with pytest.raises(GoogleDriveMediaArchiveError) as error:
        adapter(transport).upload_object(
            object_key=OBJECT_KEY,
            mime_type="image/jpeg",
            size_bytes=len(b"synthetic"),
            sha256=hashlib.sha256(b"synthetic").hexdigest(),
            stream=BytesIO(b"synthetic"),
        )

    assert error.value.code == "conflict"
    assert all(call[0] not in {"POST", "PUT"} for call in transport.calls)
    list_call = next(call for call in transport.calls if call[0] == "GET")
    assert "incompleteSearch" in list_call[2]["params"]["fields"]


@pytest.mark.parametrize("operation", ["read", "delete"])
def test_incomplete_hierarchy_search_never_attests_ownership_or_deletes(operation):
    transport = SyntheticDriveTransport()
    transport.respond("GET", FakeResponse(200, file_resource(b"owned")))
    transport.respond("GET", FakeResponse(200, {"incompleteSearch": True, "files": []}))

    with pytest.raises(GoogleDriveMediaArchiveError) as error:
        if operation == "read":
            adapter(transport).read_object(remote_id=FILE_ID)
        else:
            adapter(transport).delete_object(remote_id=FILE_ID)

    assert error.value.code == "conflict"
    assert all(call[0] != "DELETE" for call in transport.calls)


def test_folder_with_incompatible_properties_is_not_adopted_or_duplicated():
    transport = SyntheticDriveTransport()
    foreign_folder = tenant_folder_resource()
    foreign_folder["appProperties"]["pyp_media_tenant"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    queue_folder_lookup(transport, foreign_folder)

    with pytest.raises(GoogleDriveMediaArchiveError) as error:
        adapter(transport).upload_object(
            object_key=OBJECT_KEY,
            mime_type="image/jpeg",
            size_bytes=1,
            sha256=hashlib.sha256(b"x").hexdigest(),
            stream=BytesIO(b"x"),
        )

    assert error.value.code == "authorization"
    assert all(call[0] not in {"POST", "PUT"} for call in transport.calls)


def test_object_with_incompatible_path_properties_is_not_reused():
    payload = b"synthetic existing object"
    resource = file_resource(payload)
    resource["appProperties"]["pyp_media_cycle"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    transport = SyntheticDriveTransport()
    queue_existing_path(transport)
    queue_folder_lookup(transport, resource)

    with pytest.raises(GoogleDriveMediaArchiveError) as error:
        adapter(transport).upload_object(
            object_key=OBJECT_KEY,
            mime_type="image/jpeg",
            size_bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            stream=BytesIO(payload),
        )

    assert error.value.code == "authorization"
    assert all(call[0] not in {"POST", "PUT"} for call in transport.calls)


def test_upload_rejects_cross_tenant_key_and_mismatched_local_source_without_http():
    other_tenant_key = OBJECT_KEY.replace(str(TENANT_ID), "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", 1)
    transport = SyntheticDriveTransport()
    with pytest.raises(GoogleDriveMediaArchiveError, match="não pertence"):
        adapter(transport).upload_object(
            object_key=other_tenant_key,
            mime_type="image/jpeg",
            size_bytes=1,
            sha256=hashlib.sha256(b"x").hexdigest(),
            stream=BytesIO(b"x"),
        )
    with pytest.raises(GoogleDriveMediaArchiveError, match="não corresponde"):
        adapter(transport).upload_object(
            object_key=OBJECT_KEY,
            mime_type="image/jpeg",
            size_bytes=1,
            sha256="0" * 64,
            stream=BytesIO(b"x"),
        )
    assert transport.calls == []


def test_upload_rejects_source_without_seekable_contract_with_sanitized_error():
    class ReaderWithoutSeekable:
        def read(self, _size=-1):
            return b"x"

    transport = SyntheticDriveTransport()
    with pytest.raises(GoogleDriveMediaArchiveError, match="permitir releitura"):
        adapter(transport).upload_object(
            object_key=OBJECT_KEY,
            mime_type="image/jpeg",
            size_bytes=1,
            sha256=hashlib.sha256(b"x").hexdigest(),
            stream=ReaderWithoutSeekable(),
        )
    assert transport.calls == []


def test_read_and_download_stream_only_owned_bytes_and_check_digest():
    payload = b"synthetic download contents"
    resource = file_resource(payload)
    transport = SyntheticDriveTransport()
    queue_owned_file_lookup(transport, resource)
    assert adapter(transport).read_object(remote_id=FILE_ID).size_bytes == len(payload)

    transport = SyntheticDriveTransport()
    queue_owned_file_lookup(transport, resource)
    transport.respond("STREAM_GET", FakeResponse(200, chunks=[payload[:9], payload[9:]]))
    destination = BytesIO()
    receipt = adapter(transport).download_object(remote_id=FILE_ID, destination=destination)
    assert destination.getvalue() == payload
    assert receipt.size_bytes == len(payload)
    assert receipt.sha256 == hashlib.sha256(payload).hexdigest()
    assert any(call[0] == "STREAM_GET" for call in transport.calls)

    corrupted = SyntheticDriveTransport()
    queue_owned_file_lookup(corrupted, resource)
    corrupted.respond("STREAM_GET", FakeResponse(200, chunks=[payload + b"corrupt"]))
    destination = BytesIO()
    with pytest.raises(GoogleDriveMediaArchiveError, match="excede|não corresponde"):
        adapter(corrupted).download_object(remote_id=FILE_ID, destination=destination)
    assert destination.getvalue() == b""

    truncated = SyntheticDriveTransport()
    queue_owned_file_lookup(truncated, resource)
    truncated.respond("STREAM_GET", FakeResponse(200, chunks=[payload[:-1]]))
    destination = BytesIO()
    with pytest.raises(GoogleDriveMediaArchiveError, match="não corresponde"):
        adapter(truncated).download_object(remote_id=FILE_ID, destination=destination)
    assert destination.getvalue() == payload[:-1]


def test_delete_refuses_foreign_parent_and_is_idempotent_for_missing_file():
    foreign = file_resource(b"foreign", parent_folder_id="another-tenant-folder")
    transport = SyntheticDriveTransport()
    queue_owned_file_lookup(transport, foreign)
    with pytest.raises(GoogleDriveMediaArchiveError) as error:
        adapter(transport).delete_object(remote_id=FILE_ID)
    assert error.value.code == "authorization"
    assert all(call[0] != "DELETE" for call in transport.calls)

    missing = SyntheticDriveTransport()
    missing.respond("GET", FakeResponse(404, {"error": {"message": "private detail"}}))
    adapter(missing).delete_object(remote_id=FILE_ID)
    assert all(call[0] != "DELETE" for call in missing.calls)

    present = SyntheticDriveTransport()
    queue_owned_file_lookup(present, file_resource(b"owned"))
    present.respond("DELETE", FakeResponse(204))
    adapter(present).delete_object(remote_id=FILE_ID)
    delete_calls = [call for call in present.calls if call[0] == "DELETE"]
    assert len(delete_calls) == 1
    assert delete_calls[0][1] == f"{DRIVE_FILES_URL}/{FILE_ID}"


def test_api_quota_errors_are_sanitized():
    transport = SyntheticDriveTransport()
    transport.respond(
        "GET",
        FakeResponse(403, {"error": {"errors": [{"reason": "storageQuotaExceeded"}],
                                      "message": "private-provider-secret"}}),
    )
    with pytest.raises(GoogleDriveMediaArchiveError) as error:
        adapter(transport).read_object(remote_id=FILE_ID)
    assert error.value.code == "quota"
    assert "private-provider-secret" not in str(error.value)
    assert "storageQuotaExceeded" not in str(error.value)


def test_upload_helper_bounds_private_property_values_before_transport(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    transport = SyntheticDriveTransport()
    with pytest.raises(DriveUploadError, match="propriedades privadas"):
        upload_drive_file(
            access_token=SecretStr("synthetic-access-token"),
            parent_folder_id=TENANT_FOLDER_ID,
            name="synthetic-object",
            mime_type="image/jpeg",
            size_bytes=1,
            stream=BytesIO(b"x"),
            transport=transport,
            app_properties={"pyp_media_sha256": "a" * 120},
        )
    assert transport.calls == []
