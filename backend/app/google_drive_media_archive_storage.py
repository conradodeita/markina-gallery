"""Adaptador Google Drive para o contrato de arquivo frio de mídia.

Não carrega credenciais nem seleciona uma raiz. A aplicação só deve construir
esta classe no fluxo operacional protegido; o desenvolvimento local continua
usando o adapter sintético.
"""

from __future__ import annotations

import hashlib
import os
import re
from contextlib import AbstractContextManager
from typing import Any, BinaryIO, Protocol
from urllib.parse import quote
from uuid import UUID

import httpx
from pydantic import SecretStr

from app.google_drive_client import DriveTransport
from app.google_drive_storage import (
    MAX_FILE_SIZE,
    DriveUploadError,
    provider_failure_code,
    upload_drive_file,
)
from app.media_archive_storage import ArchiveDownloadReceipt, ArchiveRemoteObject

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
MEDIA_NAMESPACE = "gallery-media-v1"

_DRIVE_ID = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MIME_TYPE = re.compile(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+\Z")
_METADATA_FIELDS = "id,name,mimeType,size,parents,appProperties,trashed"
_LIST_FIELDS = f"incompleteSearch,nextPageToken,files({_METADATA_FIELDS})"


class StreamingDriveTransport(DriveTransport, Protocol):
    """Transporte com leitura de conteúdo em streaming, substituível nos testes."""

    def stream_get(self, url: str, **kwargs: Any) -> AbstractContextManager[httpx.Response]: ...


class GoogleDriveMediaArchiveError(ValueError):
    """Falha de mídia sem corpo bruto, URL, token ou dados do provedor."""

    def __init__(self, message: str, *, code: str = "io") -> None:
        super().__init__(message)
        self.code = code if code in {"io", "quota", "authorization", "conflict"} else "io"


class GoogleDriveMediaArchiveStorage:
    """Drive privado, preso a uma raiz e a um único tenant injetados."""

    def __init__(
        self,
        *,
        access_token: SecretStr,
        media_root_id: str,
        tenant_id: UUID,
        transport: StreamingDriveTransport,
    ) -> None:
        if (
            not isinstance(access_token, SecretStr)
            or not access_token.get_secret_value()
            or len(access_token.get_secret_value()) > 8192
            or any(not 0x21 <= ord(char) <= 0x7E for char in access_token.get_secret_value())
            or not isinstance(media_root_id, str)
            or not _DRIVE_ID.fullmatch(media_root_id)
            or not isinstance(tenant_id, UUID)
        ):
            raise GoogleDriveMediaArchiveError("A configuração protegida do Drive é inválida.")
        self._access_token = access_token
        self._media_root_id = media_root_id
        self._tenant_id = tenant_id
        self._transport = transport

    def upload_object(
        self,
        *,
        object_key: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        stream: BinaryIO,
    ) -> ArchiveRemoteObject:
        self._require_production_environment()
        key_hash, gallery_id, folder_id, cycle_id = self._validate_object_key(object_key)
        if (
            not isinstance(mime_type, str)
            or not _MIME_TYPE.fullmatch(mime_type)
            or type(size_bytes) is not int
            or not 0 < size_bytes <= MAX_FILE_SIZE
            or not isinstance(sha256, str)
            or not _SHA256.fullmatch(sha256)
        ):
            raise GoogleDriveMediaArchiveError("Os dados do objeto de mídia são inválidos.")

        self._verify_source(stream, size_bytes=size_bytes, expected_sha256=sha256)
        cycle_folder_id = self._media_folder_path(
            gallery_id=gallery_id,
            folder_id=folder_id,
            cycle_id=cycle_id,
            create=True,
        )
        if cycle_folder_id is None:
            raise GoogleDriveMediaArchiveError("A pasta do ciclo de mídia não ficou disponível.")
        existing = self._find_object(
            cycle_folder_id,
            key_hash,
            gallery_id=gallery_id,
            folder_id=folder_id,
            cycle_id=cycle_id,
        )
        if existing:
            return self._validate_object_resource(
                existing,
                cycle_folder_id=cycle_folder_id,
                gallery_id=gallery_id,
                folder_id=folder_id,
                cycle_id=cycle_id,
                key_hash=key_hash,
                expected_size=size_bytes,
                expected_mime=mime_type,
                expected_sha256=sha256,
            )[0]

        app_properties = {
            "pyp_media_namespace": MEDIA_NAMESPACE,
            "pyp_media_tenant": str(self._tenant_id),
            "pyp_media_kind": "object",
            "pyp_media_gallery": gallery_id,
            "pyp_media_folder": folder_id,
            "pyp_media_cycle": cycle_id,
            "pyp_media_object": key_hash,
            "pyp_media_sha256": sha256,
        }
        try:
            receipt = upload_drive_file(
                access_token=self._access_token,
                parent_folder_id=cycle_folder_id,
                name=key_hash,
                mime_type=mime_type,
                size_bytes=size_bytes,
                stream=stream,
                transport=self._transport,
                app_properties=app_properties,
            )
        except DriveUploadError as exc:
            raise GoogleDriveMediaArchiveError(
                "Não foi possível enviar o objeto de mídia ao Drive.", code=exc.code,
            ) from None
        except (httpx.HTTPError, OSError, TypeError, ValueError):
            raise GoogleDriveMediaArchiveError("Não foi possível enviar o objeto de mídia ao Drive.") from None
        if not _DRIVE_ID.fullmatch(receipt.file_id) or receipt.sha256 != sha256:
            raise GoogleDriveMediaArchiveError(
                "A confirmação do upload não corresponde ao manifesto.", code="conflict",
            )
        return ArchiveRemoteObject(receipt.file_id, receipt.size_bytes, mime_type)

    def read_object(self, *, remote_id: str) -> ArchiveRemoteObject | None:
        self._require_production_environment()
        verified = self._owned_object(remote_id)
        return verified[0] if verified else None

    def download_object(
        self,
        *,
        remote_id: str,
        destination: BinaryIO,
    ) -> ArchiveDownloadReceipt:
        self._require_production_environment()
        verified = self._owned_object(remote_id)
        if verified is None:
            raise GoogleDriveMediaArchiveError("Objeto de mídia remoto não encontrado.")
        remote, expected_sha256 = verified
        digest = hashlib.sha256()
        total = 0
        url = f"{DRIVE_FILES_URL}/{quote(remote_id, safe='')}"
        try:
            with self._transport.stream_get(
                url,
                params={"alt": "media", "supportsAllDrives": "true"},
                headers=self._auth_headers(accept="application/octet-stream"),
            ) as response:
                if response.status_code != 200:
                    if response.status_code == 404:
                        raise GoogleDriveMediaArchiveError("Objeto de mídia remoto não encontrado.")
                    raise self._response_error(response, "Não foi possível baixar o objeto de mídia.")
                for chunk in response.iter_bytes(1024 * 1024):
                    if not isinstance(chunk, bytes) or not chunk:
                        continue
                    if total + len(chunk) > remote.size_bytes:
                        raise GoogleDriveMediaArchiveError(
                            "O conteúdo baixado excede o tamanho protegido.", code="conflict",
                        )
                    written = destination.write(chunk)
                    if written is not None and written != len(chunk):
                        raise GoogleDriveMediaArchiveError("Não foi possível gravar o staging privado.")
                    digest.update(chunk)
                    total += len(chunk)
        except GoogleDriveMediaArchiveError:
            raise
        except (httpx.HTTPError, OSError, TypeError, ValueError):
            raise GoogleDriveMediaArchiveError("Não foi possível baixar o objeto de mídia.") from None

        sha256 = digest.hexdigest()
        if total != remote.size_bytes or sha256 != expected_sha256:
            raise GoogleDriveMediaArchiveError(
                "O conteúdo baixado não corresponde aos metadados protegidos.", code="conflict",
            )
        return ArchiveDownloadReceipt(total, sha256)

    def delete_object(self, *, remote_id: str) -> None:
        self._require_production_environment()
        verified = self._owned_object(remote_id)
        if verified is None:
            return
        url = f"{DRIVE_FILES_URL}/{quote(remote_id, safe='')}"
        try:
            response = self._transport.delete(
                url,
                params={"supportsAllDrives": "true"},
                headers=self._auth_headers(),
            )
        except (httpx.HTTPError, OSError, TypeError, ValueError):
            raise GoogleDriveMediaArchiveError("Não foi possível excluir o objeto de mídia.") from None
        if response.status_code == 404 or 200 <= response.status_code < 300:
            return
        raise self._response_error(response, "Não foi possível excluir o objeto de mídia.")

    @staticmethod
    def _require_production_environment() -> None:
        if os.getenv("APP_ENV", "development") != "production":
            raise GoogleDriveMediaArchiveError(
                "Operações do adaptador Google Drive estão habilitadas somente em produção.",
                code="authorization",
            )

    def _validate_object_key(self, object_key: str) -> tuple[str, str, str, str]:
        if not isinstance(object_key, str) or len(object_key) != 184:
            raise GoogleDriveMediaArchiveError("A chave do objeto de mídia é inválida.")
        parts = object_key.split("/")
        if len(parts) != 5:
            raise GoogleDriveMediaArchiveError("A chave do objeto de mídia é inválida.")
        try:
            ids = [UUID(part) for part in parts]
        except (ValueError, AttributeError):
            raise GoogleDriveMediaArchiveError("A chave do objeto de mídia é inválida.") from None
        if any(str(value) != raw for value, raw in zip(ids, parts, strict=True)):
            raise GoogleDriveMediaArchiveError("A chave do objeto de mídia é inválida.")
        if ids[0] != self._tenant_id:
            raise GoogleDriveMediaArchiveError(
                "A chave do objeto não pertence ao tenant configurado.", code="authorization",
            )
        return (
            hashlib.sha256(object_key.encode("ascii")).hexdigest(),
            str(ids[1]),
            str(ids[2]),
            str(ids[3]),
        )

    @staticmethod
    def _verify_source(stream: BinaryIO, *, size_bytes: int, expected_sha256: str) -> None:
        try:
            seekable = getattr(stream, "seekable", None)
            if not callable(seekable) or not seekable():
                raise GoogleDriveMediaArchiveError("A fonte de mídia precisa permitir releitura.")
            stream.seek(0)
            digest = hashlib.sha256()
            total = 0
            while True:
                chunk = stream.read(1024 * 1024)
                if not isinstance(chunk, (bytes, bytearray, memoryview)):
                    raise GoogleDriveMediaArchiveError("A fonte de mídia retornou bytes inválidos.")
                if not chunk:
                    break
                data = bytes(chunk)
                total += len(data)
                if total > size_bytes:
                    raise GoogleDriveMediaArchiveError("O tamanho da fonte não corresponde ao manifesto.")
                digest.update(data)
        except GoogleDriveMediaArchiveError:
            raise
        except (AttributeError, OSError, TypeError, ValueError):
            raise GoogleDriveMediaArchiveError("Não foi possível conferir a fonte de mídia.") from None
        if total != size_bytes or digest.hexdigest() != expected_sha256:
            raise GoogleDriveMediaArchiveError(
                "A fonte de mídia não corresponde ao manifesto.", code="conflict",
            )

    def _folder_properties(
        self,
        *,
        kind: str,
        gallery_id: str | None = None,
        folder_id: str | None = None,
        cycle_id: str | None = None,
    ) -> dict[str, str]:
        properties = {
            "pyp_media_namespace": MEDIA_NAMESPACE,
            "pyp_media_tenant": str(self._tenant_id),
            "pyp_media_kind": kind,
        }
        if gallery_id is not None:
            properties["pyp_media_gallery"] = gallery_id
        if folder_id is not None:
            properties["pyp_media_folder"] = folder_id
        if cycle_id is not None:
            properties["pyp_media_cycle"] = cycle_id
        return properties

    def _ensure_folder(
        self,
        *,
        parent_id: str,
        name: str,
        properties: dict[str, str],
        create: bool,
    ) -> str | None:
        query = (
            f"'{parent_id}' in parents and mimeType = '{DRIVE_FOLDER_MIME}' "
            f"and name = '{name}' and trashed = false"
        )
        files = self._list_files(query)
        if len(files) > 1:
            raise GoogleDriveMediaArchiveError(
                "Há mais de uma pasta remota para o caminho; reconciliação necessária.",
                code="conflict",
            )
        if files:
            return self._validate_folder(
                files[0],
                parent_id=parent_id,
                name=name,
                properties=properties,
            )
        if not create:
            return None

        payload = {
            "name": name,
            "mimeType": DRIVE_FOLDER_MIME,
            "parents": [parent_id],
            "appProperties": properties,
        }
        try:
            response = self._transport.post(
                DRIVE_FILES_URL,
                params={"supportsAllDrives": "true", "fields": _METADATA_FIELDS},
                headers=self._auth_headers(),
                json=payload,
            )
        except (httpx.HTTPError, OSError, TypeError, ValueError):
            raise GoogleDriveMediaArchiveError("Não foi possível preparar a pasta de mídia.") from None
        if response.status_code not in {200, 201}:
            raise self._response_error(response, "Não foi possível preparar a pasta de mídia.")
        resource = self._json_resource(response)
        return self._validate_folder(
            resource,
            parent_id=parent_id,
            name=name,
            properties=properties,
        )

    def _tenant_folder(self, *, create: bool) -> str | None:
        return self._ensure_folder(
            parent_id=self._media_root_id,
            name=str(self._tenant_id),
            properties=self._folder_properties(kind="tenant"),
            create=create,
        )

    def _media_folder_path(
        self,
        *,
        gallery_id: str,
        folder_id: str,
        cycle_id: str,
        create: bool,
    ) -> str | None:
        tenant_folder_id = self._tenant_folder(create=create)
        if tenant_folder_id is None:
            return None
        gallery_folder_id = self._ensure_folder(
            parent_id=tenant_folder_id,
            name=gallery_id,
            properties=self._folder_properties(kind="gallery", gallery_id=gallery_id),
            create=create,
        )
        if gallery_folder_id is None:
            return None
        content_folder_id = self._ensure_folder(
            parent_id=gallery_folder_id,
            name=folder_id,
            properties=self._folder_properties(
                kind="folder", gallery_id=gallery_id, folder_id=folder_id,
            ),
            create=create,
        )
        if content_folder_id is None:
            return None
        return self._ensure_folder(
            parent_id=content_folder_id,
            name=cycle_id,
            properties=self._folder_properties(
                kind="cycle", gallery_id=gallery_id, folder_id=folder_id,
                cycle_id=cycle_id,
            ),
            create=create,
        )

    def _validate_folder(
        self,
        resource: dict[str, Any],
        *,
        parent_id: str,
        name: str,
        properties: dict[str, str],
    ) -> str:
        folder_id = resource.get("id")
        app_properties = resource.get("appProperties")
        if (
            not isinstance(folder_id, str)
            or not _DRIVE_ID.fullmatch(folder_id)
            or resource.get("name") != name
            or resource.get("mimeType") != DRIVE_FOLDER_MIME
            or resource.get("parents") != [parent_id]
            or resource.get("trashed") is not False
            or not isinstance(app_properties, dict)
            or any(app_properties.get(key) != value for key, value in properties.items())
        ):
            raise GoogleDriveMediaArchiveError(
                "A pasta remota não corresponde à hierarquia autorizada.",
                code="authorization",
            )
        return folder_id

    def _find_object(
        self,
        cycle_folder_id: str,
        key_hash: str,
        *,
        gallery_id: str,
        folder_id: str,
        cycle_id: str,
    ) -> dict[str, Any] | None:
        query = (
            f"'{cycle_folder_id}' in parents and trashed = false and "
            f"(name = '{key_hash}' or appProperties has "
            f"{{ key='pyp_media_object' and value='{key_hash}' }})"
        )
        files = self._list_files(query)
        matches = [
            item for item in files
            if item.get("name") == key_hash
            or (
                isinstance(item.get("appProperties"), dict)
                and item["appProperties"].get("pyp_media_object") == key_hash
            )
        ]
        if len(matches) > 1:
            raise GoogleDriveMediaArchiveError(
                "Há mais de um objeto remoto para a chave; reconciliação necessária.", code="conflict",
            )
        if not matches:
            return None
        self._validate_object_resource(
            matches[0],
            cycle_folder_id=cycle_folder_id,
            gallery_id=gallery_id,
            folder_id=folder_id,
            cycle_id=cycle_id,
            key_hash=key_hash,
        )
        return matches[0]

    def _owned_object(self, remote_id: str) -> tuple[ArchiveRemoteObject, str] | None:
        if not isinstance(remote_id, str) or not _DRIVE_ID.fullmatch(remote_id):
            raise GoogleDriveMediaArchiveError("O identificador remoto é inválido.")
        url = f"{DRIVE_FILES_URL}/{quote(remote_id, safe='')}"
        try:
            response = self._transport.get(
                url,
                params={"supportsAllDrives": "true", "fields": _METADATA_FIELDS},
                headers=self._auth_headers(),
            )
        except (httpx.HTTPError, OSError, TypeError, ValueError):
            raise GoogleDriveMediaArchiveError("Não foi possível consultar o objeto de mídia.") from None
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise self._response_error(response, "Não foi possível consultar o objeto de mídia.")
        resource = self._json_resource(response)
        app_properties = resource.get("appProperties")
        if (
            not isinstance(app_properties, dict)
            or app_properties.get("pyp_media_namespace") != MEDIA_NAMESPACE
            or app_properties.get("pyp_media_tenant") != str(self._tenant_id)
        ):
            raise GoogleDriveMediaArchiveError(
                "O objeto remoto não corresponde ao namespace do tenant.", code="authorization",
            )
        gallery_id = self._uuid_property(app_properties, "pyp_media_gallery")
        folder_id = self._uuid_property(app_properties, "pyp_media_folder")
        cycle_id = self._uuid_property(app_properties, "pyp_media_cycle")
        cycle_folder_id = self._media_folder_path(
            gallery_id=gallery_id,
            folder_id=folder_id,
            cycle_id=cycle_id,
            create=False,
        )
        if cycle_folder_id is None:
            raise GoogleDriveMediaArchiveError(
                "A hierarquia remota do objeto não está completa.", code="authorization",
            )
        return self._validate_object_resource(
            resource,
            cycle_folder_id=cycle_folder_id,
            gallery_id=gallery_id,
            folder_id=folder_id,
            cycle_id=cycle_id,
        )

    def _validate_object_resource(
        self,
        resource: dict[str, Any],
        *,
        cycle_folder_id: str,
        gallery_id: str,
        folder_id: str,
        cycle_id: str,
        key_hash: str | None = None,
        expected_size: int | None = None,
        expected_mime: str | None = None,
        expected_sha256: str | None = None,
    ) -> tuple[ArchiveRemoteObject, str]:
        app_properties = resource.get("appProperties")
        file_id = resource.get("id")
        name = resource.get("name")
        remote_size = resource.get("size")
        mime_type = resource.get("mimeType")
        object_hash = app_properties.get("pyp_media_object") if isinstance(app_properties, dict) else None
        content_sha256 = app_properties.get("pyp_media_sha256") if isinstance(app_properties, dict) else None
        owned = (
            isinstance(file_id, str)
            and _DRIVE_ID.fullmatch(file_id)
            and resource.get("parents") == [cycle_folder_id]
            and resource.get("trashed") is False
            and isinstance(app_properties, dict)
            and app_properties.get("pyp_media_namespace") == MEDIA_NAMESPACE
            and app_properties.get("pyp_media_tenant") == str(self._tenant_id)
            and app_properties.get("pyp_media_kind") == "object"
            and app_properties.get("pyp_media_gallery") == gallery_id
            and app_properties.get("pyp_media_folder") == folder_id
            and app_properties.get("pyp_media_cycle") == cycle_id
        )
        if not owned:
            raise GoogleDriveMediaArchiveError(
                "O objeto remoto não corresponde ao namespace do tenant.", code="authorization",
            )
        content_matches = (
            isinstance(name, str)
            and _SHA256.fullmatch(name)
            and name == object_hash
            and (key_hash is None or object_hash == key_hash)
            and isinstance(remote_size, str)
            and remote_size.isdigit()
            and 0 < int(remote_size) <= MAX_FILE_SIZE
            and isinstance(mime_type, str)
            and _MIME_TYPE.fullmatch(mime_type)
            and (expected_size is None or int(remote_size) == expected_size)
            and (expected_mime is None or mime_type == expected_mime)
            and isinstance(content_sha256, str)
            and _SHA256.fullmatch(content_sha256)
            and (expected_sha256 is None or content_sha256 == expected_sha256)
        )
        if not content_matches:
            raise GoogleDriveMediaArchiveError(
                "O conteúdo remoto diverge da chave ou do manifesto.", code="conflict",
            )
        return ArchiveRemoteObject(file_id, int(remote_size), mime_type), content_sha256

    def _list_files(self, query: str) -> list[dict[str, Any]]:
        try:
            response = self._transport.get(
                DRIVE_FILES_URL,
                params={
                    "q": query,
                    "pageSize": "2",
                    "spaces": "drive",
                    "supportsAllDrives": "true",
                    "includeItemsFromAllDrives": "true",
                    "fields": _LIST_FIELDS,
                },
                headers=self._auth_headers(),
            )
        except (httpx.HTTPError, OSError, TypeError, ValueError):
            raise GoogleDriveMediaArchiveError("Não foi possível consultar o catálogo de mídia.") from None
        if response.status_code != 200:
            raise self._response_error(response, "Não foi possível consultar o catálogo de mídia.")
        resource = self._json_resource(response)
        files = resource.get("files")
        if (
            resource.get("incompleteSearch") is not False
            or not isinstance(files, list)
            or any(not isinstance(item, dict) for item in files)
            or len(files) > 2
            or resource.get("nextPageToken") not in (None, "")
        ):
            raise GoogleDriveMediaArchiveError(
                "A consulta do catálogo de mídia foi ambígua.", code="conflict",
            )
        return files

    @staticmethod
    def _uuid_property(app_properties: dict[str, Any], key: str) -> str:
        value = app_properties.get(key)
        try:
            parsed = UUID(value) if isinstance(value, str) else None
        except (AttributeError, ValueError):
            parsed = None
        if parsed is None or str(parsed) != value:
            raise GoogleDriveMediaArchiveError(
                "O objeto remoto não identifica um caminho de mídia válido.",
                code="authorization",
            )
        return value

    @staticmethod
    def _json_resource(response: object) -> dict[str, Any]:
        try:
            resource = response.json()  # type: ignore[attr-defined]
        except (AttributeError, TypeError, ValueError):
            raise GoogleDriveMediaArchiveError("O Drive retornou metadados inválidos.") from None
        if not isinstance(resource, dict):
            raise GoogleDriveMediaArchiveError("O Drive retornou metadados inválidos.")
        return resource

    @staticmethod
    def _response_error(response: object, message: str) -> GoogleDriveMediaArchiveError:
        code = provider_failure_code(response)
        if code == "quota":
            message = "A quota do Drive não permite concluir a operação."
        elif code == "authorization":
            message = "A autorização do Drive não permite concluir a operação."
        elif code == "conflict":
            message = "O Drive recusou a operação por conflito."
        return GoogleDriveMediaArchiveError(message, code=code)

    def _auth_headers(self, *, accept: str = "application/json") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token.get_secret_value()}",
            "Accept": accept,
        }
