"""Operação interna de upload Drive. Não define rotas nem escolhe destino."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import BinaryIO
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr

from app.google_drive_client import DriveTransport, HttpxDriveTransport

UPLOAD_ENDPOINT = "https://www.googleapis.com/upload/drive/v3/files"
UPLOAD_FIELDS = "id,name,mimeType,size,md5Checksum,parents"
CHUNK_ALIGNMENT = 256 * 1024
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
MAX_CHUNK_SIZE = 64 * 1024 * 1024
MAX_FILE_SIZE = 5 * 1024**4


class DriveUploadError(ValueError):
    """Erro de upload sem corpo, URL de sessão ou credencial do provedor."""

    def __init__(self, message: str, *, code: str = "io") -> None:
        super().__init__(message)
        self.code = code if code in {"io", "quota", "authorization", "conflict"} else "io"


def provider_failure_code(response: object) -> str:
    """Classifica respostas sem preservar nem refletir o texto bruto do Google."""
    status = getattr(response, "status_code", None)
    if status == 429:
        return "quota"
    if status == 409:
        return "conflict"
    if status not in {401, 403}:
        return "io"
    try:
        body = getattr(response, "content", b"")
        if not isinstance(body, bytes) or len(body) > 8192:
            return "authorization"
        payload = json.loads(body) if body else {}
        error = payload.get("error") if isinstance(payload, dict) else None
        details = error.get("errors", []) if isinstance(error, dict) else []
        reasons = {
            item.get("reason") for item in details
            if isinstance(item, dict) and isinstance(item.get("reason"), str)
        } if isinstance(details, list) else set()
        if reasons & {"storageQuotaExceeded", "rateLimitExceeded", "userRateLimitExceeded"}:
            return "quota"
    except (AttributeError, TypeError, ValueError):
        pass
    return "authorization"


@dataclass(frozen=True)
class DriveUploadReceipt:
    file_id: str
    size_bytes: int
    sha256: str


def _session_url(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 8192:
        raise DriveUploadError("O Google Drive não iniciou o upload.")
    try:
        parsed = urlsplit(value)
        valid_port = parsed.port in (None, 443)
    except ValueError:
        valid_port = False
        parsed = None
    if (
        parsed is None
        or parsed.scheme != "https"
        or parsed.hostname != "www.googleapis.com"
        or not valid_port
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != "/upload/drive/v3/files"
        or not parsed.query
        or parsed.fragment
        or any(char.isspace() or ord(char) < 0x20 for char in value)
    ):
        raise DriveUploadError("O Google Drive não iniciou o upload.")
    return value


def _read_exact(stream: BinaryIO, count: int) -> bytes:
    parts: list[bytes] = []
    remaining = count
    while remaining:
        try:
            part = stream.read(min(remaining, 1024 * 1024))
        except (OSError, ValueError):
            raise DriveUploadError("Não foi possível ler o arquivo para envio.") from None
        if not isinstance(part, (bytes, bytearray, memoryview)) or not part:
            raise DriveUploadError("O tamanho do arquivo não corresponde ao declarado.")
        data = bytes(part)
        if len(data) > remaining:
            raise DriveUploadError("O stream do arquivo retornou um bloco inválido.")
        parts.append(data)
        remaining -= len(data)
    return b"".join(parts)


def _metadata(response: object, *, name: str, mime_type: str, parent_id: str,
              size_bytes: int, md5_hex: str) -> tuple[str, int]:
    try:
        resource = response.json()  # type: ignore[attr-defined]
    except (AttributeError, TypeError, ValueError):
        raise DriveUploadError("O Google Drive retornou uma confirmação inválida.") from None
    if not isinstance(resource, dict):
        raise DriveUploadError("O Google Drive retornou uma confirmação inválida.")
    file_id = resource.get("id")
    parents = resource.get("parents")
    remote_size = resource.get("size")
    remote_md5 = resource.get("md5Checksum")
    if (
        not isinstance(file_id, str)
        or not file_id
        or len(file_id) > 256
        or any(ord(char) < 0x20 for char in file_id)
        or resource.get("name") != name
        or resource.get("mimeType") != mime_type
        or not isinstance(remote_size, str)
        or not remote_size.isdigit()
        or int(remote_size) != size_bytes
        or not isinstance(parents, list)
        or parent_id not in parents
        or not isinstance(remote_md5, str)
        or not re.fullmatch(r"[0-9a-fA-F]{32}", remote_md5)
        or remote_md5.lower() != md5_hex
    ):
        raise DriveUploadError("A confirmação do Google Drive não corresponde ao arquivo enviado.")
    return file_id, size_bytes


def upload_drive_file(*, access_token: SecretStr, parent_folder_id: str, name: str,
                      mime_type: str, size_bytes: int, stream: BinaryIO,
                      transport: DriveTransport | None = None,
                      chunk_size: int = DEFAULT_CHUNK_SIZE) -> DriveUploadReceipt:
    """Envia um arquivo em sessão retomável; o chamador valida tenant e objeto."""
    if os.getenv("APP_ENV", "development") != "production":
        raise DriveUploadError("Upload real do Drive habilitado somente em produção.")
    if not isinstance(access_token, SecretStr):
        raise DriveUploadError("Os dados do upload são inválidos ou incompletos.")
    token = access_token.get_secret_value()
    if (
        not token
        or len(token) > 8192
        or any(not 0x21 <= ord(char) <= 0x7E for char in token)
        or not isinstance(parent_folder_id, str)
        or not parent_folder_id
        or len(parent_folder_id) > 512
        or any(ord(char) < 0x20 for char in parent_folder_id)
        or not isinstance(name, str)
        or not name
        or len(name) > 255
        or any(ord(char) < 0x20 or ord(char) == 0x7F for char in name)
        or not isinstance(mime_type, str)
        or not re.fullmatch(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+", mime_type)
        or type(size_bytes) is not int
        or not 0 < size_bytes <= MAX_FILE_SIZE
        or type(chunk_size) is not int
        or not CHUNK_ALIGNMENT <= chunk_size <= MAX_CHUNK_SIZE
        or chunk_size % CHUNK_ALIGNMENT != 0
    ):
        raise DriveUploadError("Os dados do upload são inválidos ou incompletos.")
    try:
        if not stream.seekable():
            raise DriveUploadError("O stream do arquivo precisa permitir leitura desde o início.")
        stream.seek(0)
    except (AttributeError, OSError, ValueError):
        raise DriveUploadError("O stream do arquivo precisa permitir leitura desde o início.") from None

    md5_digest = hashlib.md5(usedforsecurity=False)  # checksum de integridade exigido pelo Drive.
    sha256_digest = hashlib.sha256()
    adapter = transport or HttpxDriveTransport()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": mime_type,
        "X-Upload-Content-Length": str(size_bytes),
    }
    try:
        started = adapter.post(
            UPLOAD_ENDPOINT,
            params={"uploadType": "resumable", "supportsAllDrives": "true", "fields": UPLOAD_FIELDS},
            headers=headers,
            json={"name": name, "mimeType": mime_type, "parents": [parent_folder_id]},
        )
    except httpx.HTTPError:
        raise DriveUploadError("Não foi possível iniciar o upload no Google Drive.") from None
    if started.status_code not in {200, 201}:
        raise DriveUploadError("Não foi possível iniciar o upload no Google Drive.",
                               code=provider_failure_code(started))
    session_uri = _session_url(started.headers.get("Location", ""))

    offset = 0
    while offset < size_bytes:
        count = min(chunk_size, size_bytes - offset)
        chunk = _read_exact(stream, count)
        final_chunk = offset + count == size_bytes
        if final_chunk:
            try:
                extra = stream.read(1)
            except (OSError, ValueError):
                raise DriveUploadError("Não foi possível ler o arquivo para envio.") from None
            if extra:
                raise DriveUploadError("O tamanho do arquivo não corresponde ao declarado.")
        md5_digest.update(chunk)
        sha256_digest.update(chunk)
        end = offset + count - 1
        try:
            result = adapter.put(
                session_uri,
                content=chunk,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": mime_type,
                    "Content-Range": f"bytes {offset}-{end}/{size_bytes}",
                },
                timeout=httpx.Timeout(120.0, connect=3.0),
            )
        except httpx.HTTPError:
            raise DriveUploadError("Não foi possível transferir o arquivo ao Google Drive.") from None

        if final_chunk:
            if result.status_code not in {200, 201}:
                raise DriveUploadError("O Google Drive não confirmou a conclusão do upload.",
                                       code=provider_failure_code(result))
            file_id, verified_size = _metadata(
                result,
                name=name,
                mime_type=mime_type,
                parent_id=parent_folder_id,
                size_bytes=size_bytes,
                md5_hex=md5_digest.hexdigest(),
            )
            return DriveUploadReceipt(
                file_id=file_id,
                size_bytes=verified_size,
                sha256=sha256_digest.hexdigest(),
            )

        expected_range = f"bytes=0-{end}"
        if result.status_code != 308 or result.headers.get("Range") != expected_range:
            raise DriveUploadError("O Google Drive não confirmou o bloco enviado.",
                                   code=provider_failure_code(result))
        offset += count

    raise DriveUploadError("O Google Drive não confirmou a conclusão do upload.")
