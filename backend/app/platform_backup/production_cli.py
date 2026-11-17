"""Entrada da rotina agendada e do acionamento manual da plataforma."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict
from datetime import datetime, timezone

from pydantic import SecretStr

from app.google_drive_client import HttpxDriveTransport

from .filesystem import BackupStorageError
from .runtime_config import RuntimeConfig, load_runtime_config
from .runtime_source import (
    SourceConfig,
    _attest_database,
    _docker,
    attest_container,
    load_source_config,
    snapshot,
)
from .runtime_worker import WORK_ROOT, RuntimeResult, run_due
from .workspace_store import WorkspaceDriveBackupStore

# A credencial OAuth duradoura permanece no processo da API. O operador recebe
# somente o token efêmero no pipe privado e nunca o inclui em uma mensagem.
_TOKEN_PROVIDER = """
import json
import os
import sys
from uuid import UUID
from pydantic import SecretStr
from sqlalchemy import select, text
from app.auth import GoogleDriveConnection, SessionLocal
from app.google_drive_client import HttpxDriveTransport
from app.google_drive_oauth import SCOPE, _cipher, _config
from app.platform_backup.workspace_credentials import create_workspace_backup_store
from app.system_monitor.models import PlatformOwner

try:
    if os.getenv("APP_ENV") != "production" or os.getenv("APP_VERSION") != sys.argv[3]:
        raise ValueError
    with SessionLocal() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        tenant_id = db.scalars(select(GoogleDriveConnection.tenant_id).join(
            PlatformOwner, PlatformOwner.admin_user_id == GoogleDriveConnection.connected_by_admin_id
        ).where(GoogleDriveConnection.state == "connected", GoogleDriveConnection.revoked_at.is_(None),
                GoogleDriveConnection.scopes == SCOPE)).one()
        cid, secret, _ = _config()
        adapter = HttpxDriveTransport()
        store = create_workspace_backup_store(
            db, tenant_id=tenant_id, destination_id=UUID(sys.argv[1]), parent_folder_id=sys.argv[2],
            client_id=cid, client_secret=SecretStr(secret), cipher=_cipher(),
            token_transport=adapter, drive_transport=adapter,
        )
    print(json.dumps({"access_token": store.access_token.get_secret_value()}))
except Exception:
    sys.exit(1)
"""


def _workspace(source: SourceConfig, config: RuntimeConfig) -> WorkspaceDriveBackupStore:
    attest_container(source.api_container, source.api_image, service="api")
    try:
        raw = _docker("exec", source.api_container, "python", "-B", "-c", _TOKEN_PROVIDER,
                      str(config.destination_id), config.parent_folder_id, source.configuration["APP_RELEASE"])
        if not 0 < len(raw) <= 9_000:
            raise ValueError
        reply = json.loads(raw)
        token = reply["access_token"]
        if (set(reply) != {"access_token"} or not isinstance(token, str)
                or not re.fullmatch(r"[!-~]{1,8192}", token)):
            raise ValueError
        return WorkspaceDriveBackupStore(config.destination_id, config.parent_folder_id, SecretStr(token),
                                         transport=HttpxDriveTransport())
    except (BackupStorageError, ValueError, TypeError, KeyError):
        raise BackupStorageError("authorization") from None


def main() -> int:
    try:
        config = load_runtime_config()
        if not config.enabled:
            report = RuntimeResult("disabled")
        else:
            source = load_source_config()
            _attest_database(source)
            # Política conservadora para dump, embalagem, ciphertext e leitura de retorno.
            if shutil.disk_usage(WORK_ROOT).free < 4 * source.max_dump_bytes:
                raise BackupStorageError("quota")
            report = run_due(schema_revision=source.schema_revision,
                             at=datetime.now(timezone.utc),  # noqa: UP017 -- host Python 3.10
                             snapshot=lambda revision: snapshot(source, revision),
                             workspace=lambda runtime: _workspace(source, runtime))
    except BackupStorageError as error:
        report = RuntimeResult("failed", error=error.code)
    except Exception:  # noqa: BLE001 -- o journal recebe apenas estado técnico sanitizado.
        report = RuntimeResult("failed", error="io")
    print(json.dumps(asdict(report), default=str, sort_keys=True))
    return 0 if report.status in {"disabled", "copies_verified"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
