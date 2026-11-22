"""Testes sintéticos do provider owner-only de credenciais Workspace."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.auth import GoogleDriveConnection, now
from app.google_drive_client import SCOPE, TOKEN_ENDPOINT
from app.integration_secrets import IntegrationCipher
from app.platform_backup.filesystem import BackupStorageError
from app.platform_backup.workspace_credentials import create_workspace_backup_store
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


class SyntheticTokenTransport:
    def __init__(self, *, status=200, payload=None):
        self.status = status
        self.payload = payload or {
            "access_token": "synthetic-short-lived-access-token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": SCOPE,
        }
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return SimpleNamespace(status_code=self.status, json=lambda: self.payload)


class SyntheticDriveTransport:
    def get(self, *_args, **_kwargs):
        raise AssertionError("transporte Drive não deve ser chamado ao montar o store")

    def post(self, *_args, **_kwargs):
        raise AssertionError("transporte Drive não deve ser chamado ao montar o store")

    def put(self, *_args, **_kwargs):
        raise AssertionError("transporte Drive não deve ser chamado ao montar o store")

    def stream_get(self, *_args, **_kwargs):
        raise AssertionError("transporte Drive não deve ser chamado ao montar o store")


def add_connection(db, *, tenant_id, admin_id, cipher, state="connected",
                   scopes=SCOPE, revoked_at=None):
    connection_id = uuid4()
    envelope = cipher.encrypt(
        "synthetic-refresh-token",
        tenant_id=tenant_id,
        credential_id=connection_id,
    ).payload()
    connection = GoogleDriveConnection(
        id=connection_id,
        tenant_id=tenant_id,
        connected_by_admin_id=admin_id,
        refresh_token_envelope=envelope,
        scopes=scopes,
        state=state,
        connected_at=now(),
        updated_at=now(),
        revoked_at=revoked_at,
    )
    db.add(connection)
    db.commit()
    return connection


def create_store(db, *, tenant_id, cipher, token_transport, drive_transport=None):
    return create_workspace_backup_store(
        db,
        tenant_id=tenant_id,
        destination_id=uuid4(),
        parent_folder_id="synthetic-folder-id",
        client_id="synthetic-client-id",
        client_secret=SecretStr("synthetic-client-secret"),
        cipher=cipher,
        token_transport=token_transport,
        drive_transport=drive_transport or SyntheticDriveTransport(),
    )


def test_creates_store_from_owner_connection_with_ephemeral_redacted_access_token(
    client_db,
):
    owner_tenant, _tenant, owner, _photographer = create_accounts(client_db)
    cipher = IntegrationCipher()
    connection = add_connection(
        client_db, tenant_id=owner_tenant.id, admin_id=owner.id, cipher=cipher,
    )
    token_transport = SyntheticTokenTransport()
    drive_transport = SyntheticDriveTransport()

    store = create_store(
        client_db,
        tenant_id=owner_tenant.id,
        cipher=cipher,
        token_transport=token_transport,
        drive_transport=drive_transport,
    )

    assert store.access_token.get_secret_value() == "synthetic-short-lived-access-token"
    assert store.transport is drive_transport
    assert "synthetic-short-lived-access-token" not in repr(store)
    assert "synthetic-refresh-token" not in str(connection.refresh_token_envelope)
    assert len(token_transport.calls) == 1
    url, request = token_transport.calls[0]
    assert url == TOKEN_ENDPOINT
    assert request["data"] == {
        "client_id": "synthetic-client-id",
        "client_secret": "synthetic-client-secret",
        "refresh_token": "synthetic-refresh-token",
        "grant_type": "refresh_token",
    }
    assert request["headers"] == {"Accept": "application/json"}


@pytest.mark.parametrize(
    ("state", "scopes", "owner_connection", "revoked"),
    [
        ("revoked", SCOPE, True, False),
        ("connected", SCOPE + " https://www.googleapis.com/auth/drive", True, False),
        ("connected", SCOPE, False, False),
        ("connected", SCOPE, True, True),
    ],
)
def test_rejects_invalid_or_non_owner_connection_before_token_exchange(
    client_db, state, scopes, owner_connection, revoked
):
    owner_tenant, _tenant, owner, photographer = create_accounts(client_db)
    cipher = IntegrationCipher()
    add_connection(
        client_db,
        tenant_id=owner_tenant.id,
        admin_id=owner.id if owner_connection else photographer.id,
        cipher=cipher,
        state=state,
        scopes=scopes,
        revoked_at=now() if revoked else None,
    )
    token_transport = SyntheticTokenTransport()

    with pytest.raises(BackupStorageError) as rejected:
        create_store(
            client_db,
            tenant_id=owner_tenant.id,
            cipher=cipher,
            token_transport=token_transport,
        )

    assert rejected.value.code == "authorization"
    assert token_transport.calls == []


def test_connection_from_another_tenant_is_not_used(client_db):
    owner_tenant, tenant, owner, _photographer = create_accounts(client_db)
    cipher = IntegrationCipher()
    add_connection(client_db, tenant_id=owner_tenant.id, admin_id=owner.id, cipher=cipher)
    token_transport = SyntheticTokenTransport()

    with pytest.raises(BackupStorageError) as rejected:
        create_store(
            client_db,
            tenant_id=tenant.id,
            cipher=cipher,
            token_transport=token_transport,
        )

    assert rejected.value.code == "authorization"
    assert token_transport.calls == []


@pytest.mark.parametrize(
    ("status", "payload"),
    [
        (401, {"error": "invalid_grant", "error_description": "private token detail"}),
        (200, {
            "access_token": "synthetic-access",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": SCOPE + " https://www.googleapis.com/auth/drive",
        }),
    ],
)
def test_refresh_rejects_provider_failure_or_non_exact_token_scope(
    client_db, status, payload
):
    owner_tenant, _tenant, owner, _photographer = create_accounts(client_db)
    cipher = IntegrationCipher()
    add_connection(client_db, tenant_id=owner_tenant.id, admin_id=owner.id, cipher=cipher)
    token_transport = SyntheticTokenTransport(status=status, payload=payload)

    with pytest.raises(BackupStorageError) as rejected:
        create_store(
            client_db,
            tenant_id=owner_tenant.id,
            cipher=cipher,
            token_transport=token_transport,
        )

    assert rejected.value.code == "authorization"
    assert "private token detail" not in str(rejected.value)


def test_refresh_accepts_omitted_scope_from_exact_persisted_grant(client_db):
    owner_tenant, _tenant, owner, _photographer = create_accounts(client_db)
    cipher = IntegrationCipher()
    add_connection(client_db, tenant_id=owner_tenant.id, admin_id=owner.id, cipher=cipher)
    token_transport = SyntheticTokenTransport(payload={
        "access_token": "synthetic-short-lived-access-token",
        "expires_in": 3600,
        "token_type": "Bearer",
    })

    store = create_store(
        client_db,
        tenant_id=owner_tenant.id,
        cipher=cipher,
        token_transport=token_transport,
    )

    assert store.access_token.get_secret_value() == "synthetic-short-lived-access-token"


def test_store_creation_requires_explicit_transports(client_db):
    owner_tenant, _tenant, owner, _photographer = create_accounts(client_db)
    cipher = IntegrationCipher()
    add_connection(client_db, tenant_id=owner_tenant.id, admin_id=owner.id, cipher=cipher)

    with pytest.raises(BackupStorageError) as rejected:
        create_workspace_backup_store(
            client_db,
            tenant_id=owner_tenant.id,
            destination_id=uuid4(),
            parent_folder_id="synthetic-folder-id",
            client_id="synthetic-client-id",
            client_secret=SecretStr("synthetic-client-secret"),
            cipher=cipher,
            token_transport=None,
            drive_transport=SyntheticDriveTransport(),
        )

    assert rejected.value.code == "unsafe"
