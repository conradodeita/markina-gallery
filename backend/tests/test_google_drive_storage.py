"""Upload Drive usa somente respostas e transportes sintéticos nestes testes."""

from __future__ import annotations

import hashlib
import json
from io import BytesIO

import pytest
from pydantic import SecretStr

from app import google_drive_storage as storage
from app.google_drive_oauth import HttpxDriveTransport


class FakeResponse:
    def __init__(self, status_code, *, headers=None, payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.payload = payload

    def json(self):
        return self.payload

    @property
    def content(self):
        return json.dumps(self.payload or {}).encode()


class SyntheticTransport:
    def __init__(self, content: bytes, *, location="https://www.googleapis.com/upload/drive/v3/files?upload_id=synthetic"):
        self.content = content
        self.location = location
        self.calls = []
        self.responses = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse(200, headers={"Location": self.location})

    def put(self, url, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        response = self.responses.pop(0)
        return response


def final_payload(content: bytes, *, parent="synthetic-folder", name="synthetic.jpg",
                  mime_type="image/jpeg"):
    return {
        "id": "synthetic-file-id",
        "name": name,
        "mimeType": mime_type,
        "size": str(len(content)),
        "md5Checksum": hashlib.md5(content, usedforsecurity=False).hexdigest(),
        "parents": [parent],
    }


def upload(transport, content: bytes, *, parent="synthetic-folder", name="synthetic.jpg",
           mime_type="image/jpeg", chunk_size=storage.DEFAULT_CHUNK_SIZE):
    return storage.upload_drive_file(
        access_token=SecretStr("synthetic-access-token"),
        parent_folder_id=parent,
        name=name,
        mime_type=mime_type,
        size_bytes=len(content),
        stream=BytesIO(content),
        transport=transport,
        chunk_size=chunk_size,
    )


def test_upload_sends_private_resumable_file_and_returns_only_verified_receipt(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    content = b"synthetic image bytes"
    transport = SyntheticTransport(content)
    transport.responses.append(FakeResponse(200, payload=final_payload(content)))

    receipt = upload(transport, content)

    assert receipt.file_id == "synthetic-file-id"
    assert receipt.size_bytes == len(content)
    assert receipt.sha256 == hashlib.sha256(content).hexdigest()
    assert not hasattr(receipt, "session_uri")
    start = transport.calls[0]
    assert start[0] == "POST"
    assert start[1] == storage.UPLOAD_ENDPOINT
    assert start[2]["params"] == {
        "uploadType": "resumable",
        "supportsAllDrives": "true",
        "fields": storage.UPLOAD_FIELDS,
    }
    assert start[2]["json"] == {
        "name": "synthetic.jpg",
        "mimeType": "image/jpeg",
        "parents": ["synthetic-folder"],
    }
    put = transport.calls[1]
    assert put[0] == "PUT"
    assert put[1] == transport.location
    assert put[2]["headers"]["Content-Range"] == f"bytes 0-{len(content) - 1}/{len(content)}"
    assert put[2]["content"] == content
    assert "synthetic-access-token" not in repr(receipt)


def test_upload_transmits_aligned_chunks_and_requires_exact_resume_ack(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    chunk_size = storage.CHUNK_ALIGNMENT
    content = b"a" * (chunk_size + 37)
    transport = SyntheticTransport(content)
    transport.responses.extend([
        FakeResponse(308, headers={"Range": f"bytes=0-{chunk_size - 1}"}),
        FakeResponse(200, payload=final_payload(content)),
    ])

    receipt = upload(transport, content, chunk_size=chunk_size)

    puts = [call for call in transport.calls if call[0] == "PUT"]
    assert [call[2]["headers"]["Content-Range"] for call in puts] == [
        f"bytes 0-{chunk_size - 1}/{len(content)}",
        f"bytes {chunk_size}-{len(content) - 1}/{len(content)}",
    ]
    assert [len(call[2]["content"]) for call in puts] == [chunk_size, 37]
    assert receipt.sha256 == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize("environment", ["development", "test", ""])
def test_real_transport_is_gated_to_production(monkeypatch, environment):
    monkeypatch.setenv("APP_ENV", environment)
    transport = SyntheticTransport(b"x")

    with pytest.raises(storage.DriveUploadError, match="somente em produção"):
        upload(transport, b"x")
    assert transport.calls == []


def test_missing_parent_fails_before_any_remote_request(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    transport = SyntheticTransport(b"x")

    with pytest.raises(storage.DriveUploadError):
        upload(transport, b"x", parent="")
    assert transport.calls == []


@pytest.mark.parametrize(
    "location",
    [
        "http://www.googleapis.com/upload/drive/v3/files?upload_id=x",
        "https://evil.example/upload/drive/v3/files?upload_id=x",
        "https://www.googleapis.com.evil.example/upload/drive/v3/files?upload_id=x",
        "https://www.googleapis.com/other?upload_id=x",
        "https://user@www.googleapis.com/upload/drive/v3/files?upload_id=x",
        "https://www.googleapis.com/upload/drive/v3/files",
    ],
)
def test_invalid_session_url_fails_without_put_or_reflecting_location(monkeypatch, location):
    monkeypatch.setenv("APP_ENV", "production")
    transport = SyntheticTransport(b"x", location=location)

    with pytest.raises(storage.DriveUploadError) as error:
        upload(transport, b"x")

    assert len(transport.calls) == 1
    assert "evil" not in str(error.value)
    assert location not in str(error.value)


def test_upload_sanitizes_provider_error_and_does_not_retry_writes(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    transport = SyntheticTransport(b"x")
    transport.responses.append(FakeResponse(503, payload={"private": "synthetic-provider-detail"}))

    with pytest.raises(storage.DriveUploadError) as error:
        upload(transport, b"x")

    assert len([call for call in transport.calls if call[0] == "PUT"]) == 1
    assert "synthetic-provider-detail" not in str(error.value)


def test_upload_classifies_drive_storage_quota_without_reflecting_provider_body(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    transport = SyntheticTransport(b"x")
    transport.responses.append(FakeResponse(403, payload={
        "error": {"errors": [{"reason": "storageQuotaExceeded"}],
                  "message": "private synthetic detail"}
    }))

    with pytest.raises(storage.DriveUploadError) as error:
        upload(transport, b"x")

    assert error.value.code == "quota"
    assert "private synthetic detail" not in str(error.value)
    assert "storageQuotaExceeded" not in str(error.value)


def test_http_put_transport_does_not_retry_and_uses_bounded_upload_timeout(monkeypatch):
    adapter = HttpxDriveTransport()
    calls = []

    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return FakeResponse(503)

    monkeypatch.setattr(adapter, "_request", request)
    response = adapter.put(
        "https://www.googleapis.com/upload/drive/v3/files?upload_id=synthetic",
        content=b"synthetic",
    )

    assert response.status_code == 503
    assert len(calls) == 1
    assert calls[0][0] == "PUT"
    assert calls[0][2]["timeout"].read == 120.0
    assert calls[0][2]["timeout"].connect == 3.0


def test_upload_fails_closed_on_metadata_or_checksum_mismatch(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    content = b"synthetic bytes"
    transport = SyntheticTransport(content)
    payload = final_payload(content)
    payload["md5Checksum"] = "0" * 32
    transport.responses.append(FakeResponse(200, payload=payload))

    with pytest.raises(storage.DriveUploadError, match="não corresponde"):
        upload(transport, content)


def test_upload_detects_declared_size_mismatch_before_finishing_session(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    content = b"short"
    transport = SyntheticTransport(content)

    with pytest.raises(storage.DriveUploadError, match="tamanho"):
        storage.upload_drive_file(
            access_token=SecretStr("synthetic-access-token"),
            parent_folder_id="synthetic-folder",
            name="synthetic.jpg",
            mime_type="image/jpeg",
            size_bytes=len(content) + 1,
            stream=BytesIO(content),
            transport=transport,
        )
    assert len(transport.calls) == 1
