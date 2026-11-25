"""Entrada da rotina agendada e do acionamento manual da plataforma."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone

from pydantic import SecretStr

from app.google_drive_client import HttpxDriveTransport

from . import filesystem as fs
from .filesystem import BackupStorageError
from .runtime_config import CONFIG_ROOT, RuntimeConfig, _private_root, load_runtime_config
from .runtime_config import bind_selected_destination as bind_folder_id
from .runtime_source import (
    SourceConfig,
    _attest_database,
    _docker,
    attest_container,
    load_source_config,
    prepare_source_config,
    snapshot,
)
from .runtime_worker import WORK_ROOT, RuntimeResult, _attest_destination, run_due
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

_SELECTED_FOLDER_PROVIDER = """
import json
import os
import re
import sys
from datetime import timedelta
from sqlalchemy import select, text
from app.auth import AuditEvent, GoogleDriveConnection, SessionLocal, now
from app.google_drive_client import SCOPE
from app.system_monitor.models import PlatformOwner

try:
    if os.getenv("APP_ENV") != "production" or os.getenv("APP_VERSION") != sys.argv[1]:
        raise ValueError
    with SessionLocal() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        tenants = db.scalars(select(GoogleDriveConnection.tenant_id).join(
            PlatformOwner, PlatformOwner.admin_user_id == GoogleDriveConnection.connected_by_admin_id
        ).where(GoogleDriveConnection.state == "connected",
                GoogleDriveConnection.revoked_at.is_(None),
                GoogleDriveConnection.scopes == SCOPE)).all()
        if len(tenants) != 1:
            raise ValueError
        selection = db.scalar(select(AuditEvent).where(
            AuditEvent.tenant_id == tenants[0],
            AuditEvent.event == "google_drive.backup_folder_selected",
            AuditEvent.created_at >= now() - timedelta(minutes=15),
        ).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(1))
        if (selection is None or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", selection.subject)):
            raise ValueError
        print(json.dumps({"folder_id": selection.subject}))
except Exception:
    sys.exit(1)
"""

_REHEARSAL_MARKER = re.compile(r"[0-9a-f]{32}\Z")
_REHEARSAL_FILE_ID = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")
_REHEARSAL_JOURNAL = re.compile(r"synthetic-rehearsal-[0-9a-f]{32}\.json\Z")


def _assert_backup_units_inert() -> None:
    for unit in ("pyp-platform-backup.service", "pyp-platform-backup.timer"):
        result = subprocess.run(
            ["/usr/bin/systemctl", "show", "--property=LoadState,UnitFileState,ActiveState", unit],
            capture_output=True, check=False, text=True, timeout=10,
        )
        if result.returncode:
            raise BackupStorageError("unsafe")
        fields: dict[str, str] = {}
        for line in result.stdout.splitlines():
            name, separator, value = line.partition("=")
            if not separator or name in fields:
                raise BackupStorageError("unsafe")
            fields[name] = value
        if set(fields) != {"LoadState", "UnitFileState", "ActiveState"}:
            raise BackupStorageError("unsafe")
        load_state, enabled_state, active_state = (
            fields["LoadState"], fields["UnitFileState"], fields["ActiveState"],
        )
        if active_state != "inactive":
            raise BackupStorageError("unsafe")
        if load_state == "not-found":
            if enabled_state not in {"", "unknown"}:
                raise BackupStorageError("unsafe")
        elif load_state == "loaded":
            allowed = {"disabled", "static"} if unit.endswith(".service") else {"disabled"}
            if enabled_state not in allowed:
                raise BackupStorageError("unsafe")
        else:
            raise BackupStorageError("unsafe")


def _journal_document(marker: str, *, state: str, content: bytes,
                      file_id: str | None = None) -> dict[str, object]:
    if (not _REHEARSAL_MARKER.fullmatch(marker)
            or state not in {"upload_pending", "created", "verified", "cleanup_pending"}
            or not isinstance(content, bytes) or not 0 < len(content) <= 4096
            or (file_id is not None and not _REHEARSAL_FILE_ID.fullmatch(file_id))):
        raise BackupStorageError("unsafe")
    document: dict[str, object] = {
        "schema_version": 1,
        "marker": marker,
        "name": f"pyp-backup-rehearsal-{marker}.txt",
        "state": state,
        "size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    if file_id is not None:
        document["file_id"] = file_id
    return document


def _journal_bytes(document: dict[str, object]) -> bytes:
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _pending_rehearsal_journals() -> list[str]:
    try:
        with fs._directory(CONFIG_ROOT) as directory:
            return sorted(name for name in os.listdir(directory) if _REHEARSAL_JOURNAL.fullmatch(name))
    except BackupStorageError:
        raise
    except OSError:
        raise BackupStorageError("unsafe") from None


def _read_rehearsal_journal(name: str) -> dict[str, object]:
    if not isinstance(name, str) or not _REHEARSAL_JOURNAL.fullmatch(name):
        raise BackupStorageError("unsafe")
    try:
        with fs._directory(CONFIG_ROOT) as directory:
            descriptor = fs.open_file(directory, name, os.O_RDONLY)
            with os.fdopen(descriptor, "rb") as stream:
                raw = stream.read(8193)
    except (OSError, BackupStorageError):
        raise BackupStorageError("unsafe") from None
    if not 0 < len(raw) <= 8192:
        raise BackupStorageError("unsafe")
    try:
        def unique(items: list[tuple[str, object]]) -> dict[str, object]:
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError
                result[key] = value
            return result
        document = json.loads(raw, object_pairs_hook=unique)
        marker = name.removeprefix("synthetic-rehearsal-").removesuffix(".json")
        if (not isinstance(document, dict)
                or set(document) not in (
                    {"schema_version", "marker", "name", "state", "size", "sha256"},
                    {"schema_version", "marker", "name", "state", "size", "sha256", "file_id"},
                )
                or document.get("schema_version") != 1 or document.get("marker") != marker
                or document.get("name") != f"pyp-backup-rehearsal-{marker}.txt"
                or document.get("state") not in {"upload_pending", "created", "verified", "cleanup_pending"}
                or type(document.get("size")) is not int or not 0 < document["size"] <= 4096
                or not isinstance(document.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", document["sha256"])
                or ("file_id" in document and (not isinstance(document["file_id"], str)
                    or not _REHEARSAL_FILE_ID.fullmatch(document["file_id"])) )):
            raise ValueError
        return document
    except (UnicodeError, TypeError, ValueError, RecursionError):
        raise BackupStorageError("unsafe") from None


def _save_rehearsal_journal(document: dict[str, object], *, create: bool) -> str:
    marker = document.get("marker")
    if not isinstance(marker, str) or not _REHEARSAL_MARKER.fullmatch(marker):
        raise BackupStorageError("unsafe")
    name = f"synthetic-rehearsal-{marker}.json"
    raw = _journal_bytes(document)
    try:
        with fs._directory(CONFIG_ROOT) as directory:
            if create:
                descriptor = fs.open_file(directory, name, os.O_WRONLY | os.O_EXCL, create=True)
                with os.fdopen(descriptor, "wb") as stream:
                    fs.write_all(stream.fileno(), raw)
                    os.fsync(stream.fileno())
            else:
                existing = _read_rehearsal_journal(name)
                if existing.get("marker") != marker:
                    raise BackupStorageError("unsafe")
                temporary = f"synthetic-rehearsal-tmp-{marker}.json"
                descriptor = fs.open_file(directory, temporary, os.O_WRONLY | os.O_EXCL, create=True)
                with os.fdopen(descriptor, "wb") as stream:
                    fs.write_all(stream.fileno(), raw)
                    os.fsync(stream.fileno())
                os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
        return name
    except BackupStorageError:
        raise
    except OSError:
        raise BackupStorageError("io") from None


def _remove_rehearsal_journal(name: str, marker: str) -> None:
    document = _read_rehearsal_journal(name)
    if document.get("marker") != marker:
        raise BackupStorageError("unsafe")
    try:
        with fs._directory(CONFIG_ROOT) as directory:
            os.unlink(name, dir_fd=directory)
            os.fsync(directory)
    except (OSError, BackupStorageError):
        raise BackupStorageError("io") from None


def _synthetic_payload(marker: str) -> bytes:
    if not _REHEARSAL_MARKER.fullmatch(marker):
        raise BackupStorageError("unsafe")
    return f"Pick-your-Pic synthetic destination rehearsal\n{marker}\n".encode("ascii")


def _reconcile_synthetic_journal(store: WorkspaceDriveBackupStore, name: str,
                                 document: dict[str, object]) -> bool:
    marker = document["marker"]
    content = _synthetic_payload(marker)
    if len(content) != document["size"] or hashlib.sha256(content).hexdigest() != document["sha256"]:
        raise BackupStorageError("unsafe")
    file_id = document.get("file_id")
    if file_id is None:
        file_id = store.find_rehearsal_item(name=document["name"])
        if file_id is None:
            # A lost upload response is ambiguous. Preserve the marker so a later
            # operator reconciliation can repeat the exact scoped lookup.
            raise BackupStorageError("conflict")
        observed = store.read_rehearsal_item(file_id=file_id, name=document["name"])
        if observed != content:
            raise BackupStorageError("conflict")
        document = _journal_document(marker, state="cleanup_pending", content=content, file_id=file_id)
        _save_rehearsal_journal(document, create=False)
    if not store.delete_rehearsal_item(file_id=file_id, name=document["name"]):
        raise BackupStorageError("io")
    _remove_rehearsal_journal(name, marker)
    return True


def _run_synthetic_destination_rehearsal() -> RuntimeResult:
    config = load_runtime_config()
    if config.enabled:
        raise BackupStorageError("unsafe")
    _assert_backup_units_inert()
    pending = _pending_rehearsal_journals()
    if pending:
        raise BackupStorageError("conflict")
    source = load_source_config()
    store = _workspace(source, config)
    _attest_destination(config, store)
    marker = secrets.token_hex(16)
    content = _synthetic_payload(marker)
    document = _journal_document(marker, state="upload_pending", content=content)
    name = _save_rehearsal_journal(document, create=True)
    file_id = None
    try:
        uploaded = store.upload_rehearsal_item(name=document["name"], content=content)
        file_id = uploaded.file_id
        document = _journal_document(marker, state="created", content=content, file_id=file_id)
        _save_rehearsal_journal(document, create=False)
        downloaded = store.read_rehearsal_item(file_id=file_id, name=document["name"])
        if (len(downloaded) != len(content) or hashlib.sha256(downloaded).hexdigest() != document["sha256"]
                or downloaded != content):
            raise BackupStorageError("checksum")
        document = _journal_document(marker, state="verified", content=content, file_id=file_id)
        _save_rehearsal_journal(document, create=False)
        if not store.delete_rehearsal_item(file_id=file_id, name=document["name"]):
            raise BackupStorageError("io")
        _remove_rehearsal_journal(name, marker)
        return RuntimeResult("destination_synthetic_verified", artifact_sha256=document["sha256"],
                             size_bytes=document["size"])
    except BackupStorageError as error:
        if file_id is not None:
            try:
                if store.delete_rehearsal_item(file_id=file_id, name=document["name"]):
                    _remove_rehearsal_journal(name, marker)
                else:
                    pending_document = _journal_document(marker, state="cleanup_pending", content=content,
                                                         file_id=file_id)
                    _save_rehearsal_journal(pending_document, create=False)
                    return RuntimeResult("failed", error="cleanup")
            except BackupStorageError:
                pending_document = _journal_document(marker, state="cleanup_pending", content=content,
                                                     file_id=file_id)
                try:
                    _save_rehearsal_journal(pending_document, create=False)
                except BackupStorageError:
                    pass
                return RuntimeResult("failed", error="cleanup")
        # With no acknowledged ID, preserve the marker journal: an upload can have
        # reached Drive even when the client lost the response.
        return RuntimeResult("failed", error=error.code)


def _reconcile_synthetic_destination() -> RuntimeResult:
    config = load_runtime_config()
    if config.enabled:
        raise BackupStorageError("unsafe")
    _assert_backup_units_inert()
    pending = _pending_rehearsal_journals()
    if not pending:
        return RuntimeResult("destination_synthetic_reconciled")
    if len(pending) != 1:
        raise BackupStorageError("conflict")
    source = load_source_config()
    store = _workspace(source, config)
    _attest_destination(config, store)
    document = _read_rehearsal_journal(pending[0])
    _reconcile_synthetic_journal(store, pending[0], document)
    return RuntimeResult("destination_synthetic_reconciled")


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


def _bind_selected_destination() -> RuntimeResult:
    config = load_runtime_config()
    if config.enabled:
        raise BackupStorageError("unsafe")
    _assert_backup_units_inert()
    source = load_source_config()
    attest_container(source.api_container, source.api_image, service="api")
    try:
        raw = _docker("exec", source.api_container, "python", "-B", "-c",
                      _SELECTED_FOLDER_PROVIDER, source.configuration["APP_RELEASE"])
        if not 0 < len(raw) <= 1_000:
            raise ValueError
        result = json.loads(raw)
        folder_id = result.get("folder_id") if isinstance(result, dict) else None
        if (set(result) != {"folder_id"} or not isinstance(folder_id, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", folder_id)):
            raise ValueError
        candidate = RuntimeConfig(config.keyring, config.destination_id, folder_id, False)
        store = _workspace(source, candidate)
        _attest_destination(candidate, store)
        bind_folder_id(folder_id)
        bound = load_runtime_config()
        if (bound.enabled or bound.parent_folder_id != folder_id
                or bound.destination_id != config.destination_id
                or bound.keyring.installation_id != config.keyring.installation_id):
            raise BackupStorageError("unsafe")
        return RuntimeResult("destination_bound")
    except BackupStorageError:
        raise
    except (ValueError, TypeError, KeyError, OSError):
        raise BackupStorageError("authorization") from None


def _prepare_source() -> RuntimeResult:
    if load_runtime_config().enabled:
        raise BackupStorageError("unsafe")
    _assert_backup_units_inert()
    if _pending_rehearsal_journals():
        raise BackupStorageError("conflict")
    raw = sys.stdin.buffer.read(4097)
    if not 0 < len(raw) <= 4096:
        raise BackupStorageError("unsafe")
    try:
        witness = json.loads(raw)
    except (ValueError, RecursionError):
        raise BackupStorageError("unsafe") from None
    prepare_source_config(witness)
    return RuntimeResult("source_prepared")


def _prepare_work_directories() -> None:
    directory = _private_root(WORK_ROOT)
    try:
        missing = []
        for name in ("catalog", "artifacts"):
            try:
                info = os.stat(name, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                missing.append(name)
                continue
            if (not stat.S_ISDIR(info.st_mode) or (info.st_uid, info.st_gid) != (0, 0)
                    or stat.S_IMODE(info.st_mode) != 0o700):
                raise BackupStorageError("unsafe")
        for name in missing:
            os.mkdir(name, mode=0o700, dir_fd=directory)
        if missing:
            os.fsync(directory)
    finally:
        os.close(directory)


def main() -> int:
    if sys.argv[1:] == ["--prepare-source"]:
        try:
            report = _prepare_source()
        except BackupStorageError as error:
            report = RuntimeResult("failed", error=error.code)
        except Exception:  # noqa: BLE001 -- a saída não reflete dados da configuração.
            report = RuntimeResult("failed", error="io")
        print(json.dumps(asdict(report), default=str, sort_keys=True))
        return 0 if report.status == "source_prepared" else 1
    if sys.argv[1:] == ["--synthetic-destination-rehearsal"]:
        try:
            report = _run_synthetic_destination_rehearsal()
        except BackupStorageError as error:
            report = RuntimeResult("failed", error=error.code)
        except Exception:  # noqa: BLE001 -- a saída do operador não reflete dados do Drive ou da configuração.
            report = RuntimeResult("failed", error="io")
        print(json.dumps(asdict(report), default=str, sort_keys=True))
        return 0 if report.status == "destination_synthetic_verified" else 1
    if sys.argv[1:] == ["--reconcile-synthetic-destination"]:
        try:
            report = _reconcile_synthetic_destination()
        except BackupStorageError as error:
            report = RuntimeResult("failed", error=error.code)
        except Exception:  # noqa: BLE001 -- a saída do operador não reflete dados do Drive ou da configuração.
            report = RuntimeResult("failed", error="io")
        print(json.dumps(asdict(report), default=str, sort_keys=True))
        return 0 if report.status == "destination_synthetic_reconciled" else 1
    if sys.argv[1:] == ["--bind-selected-destination"]:
        try:
            report = _bind_selected_destination()
        except BackupStorageError as error:
            report = RuntimeResult("failed", error=error.code)
        except Exception:  # noqa: BLE001 -- o journal recebe apenas estado técnico sanitizado.
            report = RuntimeResult("failed", error="io")
        print(json.dumps(asdict(report), default=str, sort_keys=True))
        return 0 if report.status == "destination_bound" else 1
    if sys.argv[1:]:
        print(json.dumps(asdict(RuntimeResult("failed", error="unsafe")), sort_keys=True))
        return 1
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
            _prepare_work_directories()
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
