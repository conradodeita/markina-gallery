"""Seleção owner-only de uma pasta Drive usando OAuth mínimo drive.file."""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx
from argon2.exceptions import InvalidHashError
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select

from app.admin_account import AdminAccountError, reauthenticate_admin
from app.auth import AdminUser, GoogleDriveConnection, SessionLocal, audit, enforce_rate_limit
from app.google_drive_client import SCOPE, TOKEN_ENDPOINT, DriveTransport, HttpxDriveTransport
from app.integration_secrets import IntegrationSecretError, SecretEnvelope
from app.mercadopago_api import SensitiveRoute
from app.platform_backup.runtime_config import DESTINATION_MARKER
from app.system_monitor.access import is_owner
from app.system_monitor.store import bounded
from app.totp_crypto import TotpSecretError
from app.totp_verification import matching_unused_totp_step

router = APIRouter(prefix="/admin/platform/drive", route_class=SensitiveRoute)
HEADERS = {"Cache-Control": "private, no-store"}
GOOGLE_DRIVE_PICKER_CONFIG_PATH = Path("/run/secrets/google-drive-picker-config.json")
FILES_ENDPOINT = "https://www.googleapis.com/drive/v3/files"
GLOBAL_FOLDER_NAME = "Pick-your-Pic Global"
_FOLDER_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_PROJECT_NUMBER = re.compile(r"[1-9][0-9]{0,23}\Z")
_API_KEY = re.compile(r"[A-Za-z0-9_-]{20,256}\Z")
_MAX_CONFIG_BYTES = 2048
_MAX_ACCESS_TOKEN_LENGTH = 8192


@dataclass(frozen=True, repr=False)
class PickerConfig:
    developer_key: str
    project_number: str
    expected_parent_folder_id: str


class PickerOwnerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr
    totp_code: SecretStr


class PickerSelectionInput(PickerOwnerInput):
    folder_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def _config_metadata_is_safe(metadata, *, posix: bool) -> bool:
    return (
        stat.S_ISREG(metadata.st_mode)
        and (not posix or (
            metadata.st_uid == 0 and metadata.st_gid == 0
            and stat.S_IMODE(metadata.st_mode) == 0o400 and metadata.st_nlink == 1
        ))
        and 0 < metadata.st_size <= _MAX_CONFIG_BYTES
    )


def _picker_config() -> PickerConfig:
    if os.getenv("APP_ENV", "development") != "production":
        raise HTTPException(503, "Seletor Google Drive ainda não configurado.", headers=HEADERS)
    descriptor = None
    try:
        descriptor = os.open(
            GOOGLE_DRIVE_PICKER_CONFIG_PATH,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
        )
        metadata = os.fstat(descriptor)
        if not _config_metadata_is_safe(metadata, posix=os.name == "posix"):
            raise ValueError()
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            raw = stream.read(_MAX_CONFIG_BYTES + 1)
        config = json.loads(raw, object_pairs_hook=_unique)
        if (not isinstance(config, dict)
                or set(config) != {"developer_key", "project_number", "expected_parent_folder_id"}
                or not isinstance(config["developer_key"], str)
                or not _API_KEY.fullmatch(config["developer_key"])
                or not isinstance(config["project_number"], str)
                or not _PROJECT_NUMBER.fullmatch(config["project_number"])
                or not isinstance(config["expected_parent_folder_id"], str)
                or not _FOLDER_ID.fullmatch(config["expected_parent_folder_id"])):
            raise ValueError()
        return PickerConfig(config["developer_key"], config["project_number"],
                            config["expected_parent_folder_id"])
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError, RecursionError):
        raise HTTPException(503, "Seletor Google Drive ainda não configurado.", headers=HEADERS) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _step_up(db, session, payload: PickerOwnerInput) -> None:
    try:
        admin = db.scalar(select(AdminUser).where(
            AdminUser.id == session.subject_id).with_for_update())
    except TotpSecretError:
        raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
    code = payload.totp_code.get_secret_value()
    if not admin or len(code) != 6:
        raise HTTPException(403, "Credencial inválida.", headers=HEADERS)
    try:
        reauthenticate_admin(admin, payload.current_password.get_secret_value())
        step = matching_unused_totp_step(admin.totp_secret, code, admin.totp_last_used_step)
    except TotpSecretError:
        raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
    except (AdminAccountError, InvalidHashError):
        raise HTTPException(403, "Credencial inválida.", headers=HEADERS) from None
    if step is None:
        raise HTTPException(403, "Credencial inválida.", headers=HEADERS)
    admin.totp_last_used_step = step


def _connection_for_owner(db, tenant_id):
    row = db.scalar(select(GoogleDriveConnection).where(
        GoogleDriveConnection.tenant_id == tenant_id).with_for_update())
    if (not row or row.state != "connected" or row.revoked_at is not None
            or row.scopes != SCOPE or not isinstance(row.refresh_token_envelope, dict)
            or not is_owner(db, row.connected_by_admin_id)):
        raise HTTPException(409, "Drive ainda não está conectado.", headers=HEADERS)
    return row


def _access_token(*, transport: DriveTransport, client_id: str, client_secret: str,
                  refresh_token: str) -> tuple[str, int]:
    try:
        response = transport.post(TOKEN_ENDPOINT, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise ValueError()
        data = response.json()
        token = data.get("access_token") if isinstance(data, dict) else None
        expires = data.get("expires_in") if isinstance(data, dict) else None
        token_type = data.get("token_type") if isinstance(data, dict) else None
        scope = data.get("scope") if isinstance(data, dict) else None
        if (not isinstance(token, str) or not 1 <= len(token) <= _MAX_ACCESS_TOKEN_LENGTH
                or any(not 0x21 <= ord(char) <= 0x7E for char in token)
                or type(expires) is not int or not 0 < expires <= 3600
                or not isinstance(token_type, str) or token_type.casefold() != "bearer"
                or (scope is not None and
                    (not isinstance(scope, str) or set(scope.split()) != {SCOPE}))):
            raise ValueError()
        return token, expires
    except (httpx.HTTPError, AttributeError, KeyError, TypeError, ValueError):
        raise HTTPException(503, "Não foi possível renovar o acesso temporário ao Drive.",
                            headers=HEADERS) from None


def _folder_matches(data: object, *, folder_id: str, config: PickerConfig) -> bool:
    if not isinstance(data, dict):
        return False
    capabilities = data.get("capabilities")
    parents = data.get("parents")
    return (
        data.get("id") == folder_id
        and data.get("name") == GLOBAL_FOLDER_NAME
        and data.get("mimeType") == "application/vnd.google-apps.folder"
        and data.get("trashed") is False
        and data.get("driveId") is None
        and data.get("ownedByMe") is True
        and data.get("isAppAuthorized") is True
        and isinstance(parents, list)
        and parents == [config.expected_parent_folder_id]
        and isinstance(capabilities, dict)
        and capabilities.get("canAddChildren") is True
    )


def _get_folder(*, transport: DriveTransport, token: str, folder_id: str,
                config: PickerConfig) -> dict:
    if not _FOLDER_ID.fullmatch(folder_id):
        raise HTTPException(422, "Pasta inválida.", headers=HEADERS)
    try:
        response = transport.get(
            f"{FILES_ENDPOINT}/{quote(folder_id, safe='')}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params={"supportsAllDrives": "true",
                    "fields": "id,name,mimeType,parents,driveId,ownedByMe,isAppAuthorized,trashed,"
                              "capabilities(canAddChildren),appProperties"},
        )
        if response.status_code != 200:
            raise ValueError()
        data = response.json()
        if not _folder_matches(data, folder_id=folder_id, config=config):
            raise HTTPException(409, "Selecione a pasta global privada esperada.", headers=HEADERS)
        return data
    except HTTPException:
        raise
    except (httpx.HTTPError, AttributeError, KeyError, TypeError, ValueError):
        raise HTTPException(503, "Não foi possível validar a pasta selecionada.", headers=HEADERS) from None


@router.post("/picker/session")
def picker_session(payload: PickerOwnerInput, request: Request, response: Response):
    from app.main import require_same_origin
    require_same_origin(request)
    from app.google_drive_oauth import _cipher, _config, _is_production, _owner

    session, tenant_id = _owner(request)
    if not _is_production():
        raise HTTPException(503, "Seletor Google Drive habilitado somente em produção.", headers=HEADERS)
    picker = _picker_config()
    client_id, client_secret, _ = _config()
    try:
        with SessionLocal() as db:
            bounded(db)
            enforce_rate_limit(db, "google_drive_picker_session", str(session.subject_id),
                               request.client.host if request.client else "unknown")
            db.commit()
            connection = _connection_for_owner(db, tenant_id)
            _step_up(db, session, payload)
            refresh_token = _cipher().decrypt(
                SecretEnvelope.from_payload(connection.refresh_token_envelope),
                tenant_id=tenant_id, credential_id=connection.id,
            )
            token, expires = _access_token(transport=HttpxDriveTransport(), client_id=client_id,
                                           client_secret=client_secret, refresh_token=refresh_token)
            audit(db, "google_drive.picker_session_issued", str(session.subject_id), tenant_id=tenant_id)
            db.commit()
    except HTTPException:
        raise
    except (IntegrationSecretError, httpx.HTTPError, ValueError, TypeError):
        raise HTTPException(503, "Não foi possível iniciar a seleção da pasta.", headers=HEADERS) from None
    response.headers.update(HEADERS)
    return {
        "access_token": token,
        "scope": SCOPE,
        "expires_in": expires,
        "developer_key": picker.developer_key,
        "project_number": picker.project_number,
        "expected_parent_folder_id": picker.expected_parent_folder_id,
    }


@router.post("/picker/authorize")
def authorize_picker_folder(payload: PickerSelectionInput, request: Request, response: Response):
    from app.main import require_same_origin
    require_same_origin(request)
    from app.google_drive_oauth import _cipher, _config, _is_production, _owner

    session, tenant_id = _owner(request)
    if not _is_production():
        raise HTTPException(503, "Vínculo real do Drive habilitado somente em produção.", headers=HEADERS)
    picker = _picker_config()
    client_id, client_secret, _ = _config()
    try:
        with SessionLocal() as db:
            bounded(db)
            enforce_rate_limit(db, "google_drive_picker_authorize", str(session.subject_id),
                               request.client.host if request.client else "unknown")
            db.commit()
            connection = _connection_for_owner(db, tenant_id)
            _step_up(db, session, payload)
            refresh_token = _cipher().decrypt(
                SecretEnvelope.from_payload(connection.refresh_token_envelope),
                tenant_id=tenant_id, credential_id=connection.id,
            )
            transport = HttpxDriveTransport()
            token, _expires = _access_token(transport=transport, client_id=client_id,
                                            client_secret=client_secret, refresh_token=refresh_token)
            folder = _get_folder(transport=transport, token=token, folder_id=payload.folder_id,
                                 config=picker)
            marker = dict(DESTINATION_MARKER)
            properties = folder.get("appProperties")
            if properties != marker:
                if properties not in (None, {}):
                    raise HTTPException(409, "A pasta tem uma marca de aplicativo incompatível.", headers=HEADERS)
                updated = transport.patch(
                    f"{FILES_ENDPOINT}/{quote(payload.folder_id, safe='')}",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                             "Content-Type": "application/json"},
                    params={"supportsAllDrives": "true",
                            "fields": "id,name,mimeType,parents,driveId,ownedByMe,isAppAuthorized,trashed,"
                                      "capabilities(canAddChildren),appProperties"},
                    json={"appProperties": marker},
                )
                if updated.status_code != 200 or not _folder_matches(
                        updated.json(), folder_id=payload.folder_id, config=picker):
                    raise HTTPException(503, "Não foi possível marcar o destino selecionado.", headers=HEADERS)
                updated_data = updated.json()
                if updated_data.get("appProperties") != marker:
                    raise HTTPException(503, "Não foi possível confirmar o destino selecionado.", headers=HEADERS)
                folder = updated_data
            audit(db, "google_drive.backup_folder_selected", payload.folder_id, tenant_id=tenant_id)
            db.commit()
    except HTTPException:
        raise
    except (IntegrationSecretError, httpx.HTTPError, AttributeError, ValueError, TypeError, KeyError):
        raise HTTPException(503, "Não foi possível autorizar a pasta selecionada.", headers=HEADERS) from None
    response.headers.update(HEADERS)
    return {"state": "selected", "folder_name": folder["name"], "folder_id": payload.folder_id}
