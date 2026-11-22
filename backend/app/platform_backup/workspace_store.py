"""Adapter Google Drive para artefatos globais que já foram cifrados."""

from __future__ import annotations

import hashlib
import io
import re
import tempfile
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from typing import BinaryIO, Protocol
from urllib.parse import quote
from uuid import UUID

import httpx
from pydantic import SecretStr

from app.google_drive_client import DriveTransport
from app.google_drive_storage import (
    MAX_FILE_SIZE,
    DriveUploadError,
    DriveUploadReceipt,
    provider_failure_code,
    upload_drive_file,
)

from .archive import MAX_HEADER_BYTES, MAX_PLAINTEXT_BYTES, ArchiveReceipt
from .filesystem import BackupStorageError
from .storage import CopyReceipt

FILES_ENDPOINT = "https://www.googleapis.com/drive/v3/files"
BACKUP_MIME_TYPE = "application/octet-stream"
CHUNK_SIZE = 1024 * 1024
MAX_BACKUP_SIZE = MAX_PLAINTEXT_BYTES + MAX_HEADER_BYTES + 64
_DRIVE_IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")
_HEX_MD5 = re.compile(r"[0-9a-f]{32}\Z")
_REHEARSAL_NAME = re.compile(r"pyp-backup-rehearsal-[0-9a-f]{32}\.txt\Z")


def is_drive_identifier(value: object) -> bool:
    return isinstance(value, str) and _DRIVE_IDENTIFIER.fullmatch(value) is not None


class StreamingDriveTransport(DriveTransport, Protocol):
    def stream_get(self, url: str, **kwargs) -> AbstractContextManager[httpx.Response]: ...


@dataclass(frozen=True, repr=False)
class WorkspaceDriveBackupStore:
    """Acesso a uma pasta Workspace sem persistir token ou URL de sessão."""

    destination_id: UUID
    parent_folder_id: str = field(repr=False)
    access_token: SecretStr = field(repr=False)
    shared_drive_id: str | None = field(default=None, repr=False)
    transport: StreamingDriveTransport | None = field(default=None, repr=False, compare=False)
    uploader: Callable[..., DriveUploadReceipt] | None = field(default=None, repr=False,
                                                               compare=False)

    def __post_init__(self) -> None:
        if (not isinstance(self.destination_id, UUID)
                or not is_drive_identifier(self.parent_folder_id)
                or not isinstance(self.access_token, SecretStr)
                or not self.access_token.get_secret_value()
                or len(self.access_token.get_secret_value()) > 8192
                or any(not 0x21 <= ord(char) <= 0x7E
                       for char in self.access_token.get_secret_value())
                or (self.shared_drive_id is not None
                    and not is_drive_identifier(self.shared_drive_id))):
            raise BackupStorageError("unsafe")

    @property
    def failure_domain(self) -> str:
        return "google-workspace"

    def __repr__(self) -> str:
        return "WorkspaceDriveBackupStore(<redacted>)"

    @staticmethod
    def _error_for_response(response: object) -> BackupStorageError:
        code = provider_failure_code(response)
        if getattr(response, "status_code", None) == 404:
            code = "authorization"
        return BackupStorageError(code)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + self.access_token.get_secret_value(),
            "Accept": "application/json",
        }

    def _find(self, backup_id: UUID) -> dict[str, object] | None:
        if not isinstance(backup_id, UUID):
            raise BackupStorageError("unsafe")
        name = f"{backup_id}.pypb"
        query = f"name='{name}' and '{self.parent_folder_id}' in parents and trashed=false"
        params = {
            "q": query,
            "pageSize": 2,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "fields": "files(id,name,mimeType,size,md5Checksum,parents,trashed),nextPageToken,incompleteSearch",
        }
        if self.shared_drive_id is None:
            params["corpora"] = "user"
        else:
            params.update({"corpora": "drive", "driveId": self.shared_drive_id})
        transport = self.transport
        if transport is None:
            raise BackupStorageError("unsafe")
        try:
            response = transport.get(
                FILES_ENDPOINT,
                params=params,
                headers=self._headers(),
            )
        except httpx.HTTPError:
            raise BackupStorageError("io") from None
        if response.status_code != 200:
            raise self._error_for_response(response)
        try:
            payload = response.json()
            files = payload.get("files") if isinstance(payload, dict) else None
            next_page = payload.get("nextPageToken") if isinstance(payload, dict) else None
            incomplete_search = payload.get("incompleteSearch", False) if isinstance(payload, dict) else None
        except (AttributeError, TypeError, ValueError):
            raise BackupStorageError("io") from None
        if (not isinstance(files, list) or next_page is not None
                or incomplete_search is not False):
            raise BackupStorageError("conflict")
        if not files:
            return None
        if len(files) != 1:
            raise BackupStorageError("conflict")
        item = files[0]
        if not isinstance(item, dict):
            raise BackupStorageError("conflict")
        file_id = item.get("id")
        parents = item.get("parents")
        size = item.get("size")
        md5 = item.get("md5Checksum")
        if (
            not isinstance(file_id, str)
            or not _DRIVE_IDENTIFIER.fullmatch(file_id)
            or item.get("name") != name
            or item.get("mimeType") != BACKUP_MIME_TYPE
            or ("trashed" in item and item["trashed"] is not False)
            or not isinstance(parents, list)
            or self.parent_folder_id not in parents
            or not isinstance(size, str)
            or not size.isdigit()
            or not 0 < int(size) <= min(MAX_BACKUP_SIZE, MAX_FILE_SIZE)
            or not isinstance(md5, str)
            or not _HEX_MD5.fullmatch(md5.lower())
        ):
            raise BackupStorageError("conflict")
        return {
            "id": file_id,
            "size": int(size),
            "md5": md5.lower(),
        }

    @contextmanager
    def _download(self, remote: dict[str, object]) -> Iterator[BinaryIO]:
        file_id = remote.get("id")
        expected_size = remote.get("size")
        expected_md5 = remote.get("md5")
        if (not isinstance(file_id, str) or not _DRIVE_IDENTIFIER.fullmatch(file_id)
                or type(expected_size) is not int or not isinstance(expected_md5, str)
                or not _HEX_MD5.fullmatch(expected_md5)):
            raise BackupStorageError("conflict")
        url = FILES_ENDPOINT + "/" + quote(file_id, safe="")
        digest, size = hashlib.md5(usedforsecurity=False), 0
        transport = self.transport
        if transport is None:
            raise BackupStorageError("unsafe")
        try:
            target = tempfile.TemporaryFile(mode="w+b")  # noqa: SIM115 -- o handle é fechado pelo `with target` abaixo.
        except OSError:
            raise BackupStorageError("io") from None
        with target:
            try:
                with transport.stream_get(
                    url,
                    params={"alt": "media", "supportsAllDrives": "true"},
                    headers={
                        "Authorization": "Bearer " + self.access_token.get_secret_value(),
                        "Accept": "application/octet-stream",
                    },
                ) as response:
                    if response.status_code != 200:
                        raise self._error_for_response(response)
                    for part in response.iter_bytes(chunk_size=CHUNK_SIZE):
                        if not isinstance(part, bytes):
                            raise BackupStorageError("checksum")
                        if not part:
                            continue
                        size += len(part)
                        if size > expected_size or size > MAX_BACKUP_SIZE:
                            raise BackupStorageError("checksum")
                        digest.update(part)
                        if target.write(part) != len(part):
                            raise BackupStorageError("io")
                if size != expected_size or digest.hexdigest() != expected_md5:
                    raise BackupStorageError("checksum")
            except BackupStorageError:
                raise
            except (httpx.HTTPError, OSError, TypeError, ValueError):
                raise BackupStorageError("io") from None
            target.seek(0)
            yield target

    @contextmanager
    def open(self, backup_id: UUID):
        """Lê o objeto binário em arquivo temporário e verifica size/MD5 do Drive."""
        remote = self._find(backup_id)
        if remote is None:
            raise BackupStorageError("io")
        with self._download(remote) as source:
            yield source

    def upload(self, source: BinaryIO, receipt: ArchiveReceipt) -> CopyReceipt:
        if (
            not isinstance(receipt, ArchiveReceipt)
            or not isinstance(receipt.backup_id, UUID)
            or type(receipt.size_bytes) is not int
            or not 0 < receipt.size_bytes <= MAX_BACKUP_SIZE
            or not isinstance(receipt.sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", receipt.sha256)
        ):
            raise BackupStorageError("checksum")

        existing = self._find(receipt.backup_id)
        if existing is not None:
            with self._download(existing) as current:
                digest, size = hashlib.sha256(), 0
                while part := current.read(CHUNK_SIZE):
                    size += len(part)
                    digest.update(part)
                if size != receipt.size_bytes or digest.hexdigest() != receipt.sha256:
                    raise BackupStorageError("conflict")
            return CopyReceipt(self.destination_id, receipt.backup_id,
                               receipt.size_bytes, receipt.sha256)

        uploader = self.uploader or upload_drive_file
        transport = self.transport
        if transport is None:
            raise BackupStorageError("unsafe")
        try:
            uploaded = uploader(
                access_token=self.access_token,
                parent_folder_id=self.parent_folder_id,
                name=f"{receipt.backup_id}.pypb",
                mime_type=BACKUP_MIME_TYPE,
                size_bytes=receipt.size_bytes,
                stream=source,
                transport=transport,
            )
        except DriveUploadError as error:
            raise BackupStorageError(error.code) from None
        except (httpx.HTTPError, OSError, ValueError):
            raise BackupStorageError("io") from None
        if (not isinstance(uploaded, DriveUploadReceipt)
                or uploaded.size_bytes != receipt.size_bytes
                or uploaded.sha256 != receipt.sha256):
            raise BackupStorageError("conflict")
        return CopyReceipt(self.destination_id, receipt.backup_id,
                           receipt.size_bytes, receipt.sha256)

    def upload_rehearsal_item(self, *, name: str, content: bytes) -> DriveUploadReceipt:
        """Upload only a small uniquely named synthetic item into the bound folder."""
        if (not isinstance(name, str) or not _REHEARSAL_NAME.fullmatch(name)
                or not isinstance(content, bytes) or not 0 < len(content) <= 4096):
            raise BackupStorageError("unsafe")
        transport = self.transport
        if transport is None:
            raise BackupStorageError("unsafe")
        uploader = self.uploader or upload_drive_file
        try:
            receipt = uploader(
                access_token=self.access_token,
                parent_folder_id=self.parent_folder_id,
                name=name,
                mime_type="text/plain",
                size_bytes=len(content),
                stream=io.BytesIO(content),
                transport=transport,
            )
        except DriveUploadError as error:
            raise BackupStorageError(error.code) from None
        except (httpx.HTTPError, OSError, ValueError):
            raise BackupStorageError("io") from None
        if (not isinstance(receipt, DriveUploadReceipt)
                or not _DRIVE_IDENTIFIER.fullmatch(receipt.file_id)
                or receipt.size_bytes != len(content)
                or receipt.sha256 != hashlib.sha256(content).hexdigest()):
            raise BackupStorageError("conflict")
        return receipt

    def _rehearsal_metadata(self, file_id: str, name: str) -> dict[str, object] | None:
        if (not isinstance(file_id, str) or not _DRIVE_IDENTIFIER.fullmatch(file_id)
                or not isinstance(name, str) or not _REHEARSAL_NAME.fullmatch(name)):
            raise BackupStorageError("unsafe")
        transport = self.transport
        if transport is None:
            raise BackupStorageError("unsafe")
        url = FILES_ENDPOINT + "/" + quote(file_id, safe="")
        try:
            response = transport.get(url, params={
                "supportsAllDrives": "true",
                "fields": "id,name,mimeType,size,md5Checksum,parents,trashed",
            }, headers=self._headers())
        except httpx.HTTPError:
            raise BackupStorageError("io") from None
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise self._error_for_response(response)
        try:
            item = response.json()
            size = item.get("size") if isinstance(item, dict) else None
            parents = item.get("parents") if isinstance(item, dict) else None
            md5 = item.get("md5Checksum") if isinstance(item, dict) else None
            if (not isinstance(item, dict) or item.get("id") != file_id or item.get("name") != name
                    or item.get("mimeType") != "text/plain" or item.get("trashed") not in (False, None)
                    or not isinstance(parents, list) or self.parent_folder_id not in parents
                    or not isinstance(size, str) or not size.isdigit() or not 0 < int(size) <= 4096
                    or not isinstance(md5, str) or not _HEX_MD5.fullmatch(md5.lower())):
                raise ValueError
        except (AttributeError, TypeError, ValueError):
            raise BackupStorageError("conflict") from None
        return {"id": file_id, "name": name, "size": int(size), "md5": md5.lower()}

    def read_rehearsal_item(self, *, file_id: str, name: str) -> bytes:
        """Read an exact rehearsal object and verify its metadata and MD5."""
        remote = self._rehearsal_metadata(file_id, name)
        if remote is None:
            raise BackupStorageError("authorization")
        transport = self.transport
        assert transport is not None
        url = FILES_ENDPOINT + "/" + quote(file_id, safe="")
        chunks = bytearray()
        try:
            with transport.stream_get(url, params={
                "alt": "media", "supportsAllDrives": "true",
            }, headers={"Authorization": self._headers()["Authorization"],
                        "Accept": "text/plain"}) as response:
                if response.status_code != 200:
                    raise self._error_for_response(response)
                for part in response.iter_bytes(chunk_size=CHUNK_SIZE):
                    if not isinstance(part, bytes):
                        raise BackupStorageError("checksum")
                    chunks.extend(part)
                    if len(chunks) > 4096:
                        raise BackupStorageError("checksum")
        except BackupStorageError:
            raise
        except (httpx.HTTPError, OSError, TypeError, ValueError):
            raise BackupStorageError("io") from None
        content = bytes(chunks)
        if (len(content) != remote["size"]
                or hashlib.md5(content, usedforsecurity=False).hexdigest() != remote["md5"]):
            raise BackupStorageError("checksum")
        return content

    def find_rehearsal_item(self, *, name: str) -> str | None:
        """Find only one exact random rehearsal name in the already bound folder."""
        if not isinstance(name, str) or not _REHEARSAL_NAME.fullmatch(name):
            raise BackupStorageError("unsafe")
        transport = self.transport
        if transport is None:
            raise BackupStorageError("unsafe")
        query = f"name='{name}' and '{self.parent_folder_id}' in parents and trashed=false"
        try:
            response = transport.get(FILES_ENDPOINT, params={
                "q": query, "pageSize": 2, "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "fields": "files(id,name,mimeType,size,md5Checksum,parents,trashed),nextPageToken,incompleteSearch",
                "corpora": "user",
            }, headers=self._headers())
        except httpx.HTTPError:
            raise BackupStorageError("io") from None
        if response.status_code != 200:
            raise self._error_for_response(response)
        try:
            document = response.json()
            items = document.get("files") if isinstance(document, dict) else None
            if (not isinstance(items, list) or len(items) > 1
                    or document.get("nextPageToken") is not None
                    or document.get("incompleteSearch", False) is not False):
                raise ValueError
            if not items:
                return None
            item = items[0]
            file_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(file_id, str) or not _DRIVE_IDENTIFIER.fullmatch(file_id):
                raise ValueError
        except (AttributeError, TypeError, ValueError):
            raise BackupStorageError("conflict") from None
        if self._rehearsal_metadata(file_id, name) is None:
            return None
        return file_id

    def delete_rehearsal_item(self, *, file_id: str, name: str) -> bool:
        """Delete only an exact rehearsal ID after reattesting name and parent."""
        remote = self._rehearsal_metadata(file_id, name)
        if remote is None:
            return True
        transport = self.transport
        assert transport is not None
        url = FILES_ENDPOINT + "/" + quote(file_id, safe="")
        try:
            response = transport.delete(url, params={"supportsAllDrives": "true"}, headers=self._headers())
        except httpx.HTTPError:
            raise BackupStorageError("io") from None
        if response.status_code not in {200, 204, 404}:
            raise self._error_for_response(response)
        return self._rehearsal_metadata(file_id, name) is None
