"""Credenciais efêmeras para cópia interna ao Google Workspace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

import httpx
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import GoogleDriveConnection
from app.google_drive_client import SCOPE, TOKEN_ENDPOINT, DriveTransport
from app.integration_secrets import IntegrationCipher, IntegrationSecretError, SecretEnvelope
from app.system_monitor.access import is_owner

from .filesystem import BackupStorageError
from .workspace_store import (
    StreamingDriveTransport,
    WorkspaceDriveBackupStore,
    is_drive_identifier,
)

_MAX_ACCESS_TOKEN_LENGTH = 8192


def create_workspace_backup_store(
    db: Session,
    *,
    tenant_id: UUID,
    destination_id: UUID,
    parent_folder_id: str,
    client_id: str,
    client_secret: SecretStr,
    cipher: IntegrationCipher,
    token_transport: DriveTransport | None,
    drive_transport: StreamingDriveTransport | None,
    shared_drive_id: str | None = None,
    uploader: Callable[..., Any] | None = None,
) -> WorkspaceDriveBackupStore:
    """Monta store somente após validar e trocar a credencial owner-only.

    Este helper não cria transporte HTTP, não registra tokens e não é chamado por
    rotas ou workers de produção nesta change. O chamador deve fornecer ambos os
    transportes e a configuração obtida do cofre seguro do servidor.
    """
    if (
        not isinstance(db, Session)
        or not isinstance(tenant_id, UUID)
        or not isinstance(destination_id, UUID)
        or not is_drive_identifier(parent_folder_id)
        or (shared_drive_id is not None
            and not is_drive_identifier(shared_drive_id))
        or not isinstance(client_id, str)
        or not 1 <= len(client_id) <= 256
        or any(not 0x21 <= ord(char) <= 0x7E for char in client_id)
        or not isinstance(client_secret, SecretStr)
        or not client_secret.get_secret_value()
        or len(client_secret.get_secret_value()) > 512
        or any(not 0x21 <= ord(char) <= 0x7E
               for char in client_secret.get_secret_value())
        or not isinstance(cipher, IntegrationCipher)
        or token_transport is None
        or not callable(getattr(token_transport, "post", None))
        or drive_transport is None
        or not all(callable(getattr(drive_transport, name, None))
                   for name in ("get", "post", "put", "stream_get"))
        or (uploader is not None and not callable(uploader))
    ):
        raise BackupStorageError("unsafe")

    connection = db.scalar(select(GoogleDriveConnection).where(
        GoogleDriveConnection.tenant_id == tenant_id,
    ))
    if (
        connection is None
        or connection.state != "connected"
        or connection.revoked_at is not None
        or connection.scopes != SCOPE
        or not isinstance(connection.refresh_token_envelope, dict)
        or not is_owner(db, connection.connected_by_admin_id)
    ):
        raise BackupStorageError("authorization")

    try:
        refresh_token = cipher.decrypt(
            SecretEnvelope.from_payload(connection.refresh_token_envelope),
            tenant_id=tenant_id,
            credential_id=connection.id,
        )
        response = token_transport.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": client_id,
                "client_secret": client_secret.get_secret_value(),
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
        )
        if getattr(response, "status_code", None) != 200:
            raise BackupStorageError("authorization")
        token_data = response.json()
        if not isinstance(token_data, dict):
            raise BackupStorageError("authorization")
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in")
        token_type = token_data.get("token_type")
        granted_scope = token_data.get("scope")
        if (
            not isinstance(access_token, str)
            or not 1 <= len(access_token) <= _MAX_ACCESS_TOKEN_LENGTH
            or any(not 0x21 <= ord(char) <= 0x7E for char in access_token)
            or type(expires_in) is not int
            or not 0 < expires_in <= 86400
            or not isinstance(token_type, str)
            or token_type.casefold() != "bearer"
            or (granted_scope is not None
                and (not isinstance(granted_scope, str)
                     or set(granted_scope.split()) != {SCOPE}))
        ):
            raise BackupStorageError("authorization")
    except BackupStorageError:
        raise
    except (httpx.HTTPError, AttributeError, KeyError, TypeError, ValueError,
            IntegrationSecretError):
        raise BackupStorageError("authorization") from None

    return WorkspaceDriveBackupStore(
        destination_id=destination_id,
        parent_folder_id=parent_folder_id,
        access_token=SecretStr(access_token),
        shared_drive_id=shared_drive_id,
        transport=drive_transport,
        uploader=uploader,
    )
