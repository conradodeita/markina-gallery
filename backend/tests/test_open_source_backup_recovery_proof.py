"""Prova opt-in do fluxo SaaS com PostgreSQL e Rclone crypt locais sintéticos."""

from __future__ import annotations

import base64
import configparser
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.orm import Session

pytest.importorskip(
    "mercadopago",
    reason="Dependência da aplicação ausente no ambiente de prova; não usar stub.",
)

from app import media_archive_billing as recovery_billing
from app import photographer_credits
from app.auth import (
    AdminUser,
    Base,
    Client,
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveObject,
    MediaArchiveOperation,
    MediaArchiveRecoveryCreditReservation,
    MediaArchiveRecoveryPricing,
    PhotoAsset,
    PhotoFolder,
    PhotographerCreditEntry,
    PhotoSelection,
    Tenant,
    TenantAdmin,
    TenantCreditWallet,
    now,
)
from app.folder_access import folder_media_is_local
from app.media_archive_executor import (
    MediaArchiveExecutionResult,
    execute_archive_operation,
    execute_restore_operation,
)
from app.media_archive_staging import VolumeCapacity
from app.media_archive_storage import (
    ArchiveDownloadReceipt,
    ArchiveRemoteObject,
)
from app.media_archive_worker import claim_next_operation
from tests.test_photographer_credits import create_accounts, create_photo
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


_UNSAFE_RCLONE_PROOF_CONFIG = "Unsafe Rclone proof configuration"
_RCLONE_PROOF_READ_ERROR = "Rclone synthetic proof object read failed"


def validate_rclone_proof_config(
    *,
    config_path: str | Path,
    remote_name: str,
    proof_root: str | Path,
) -> Path:
    """Aceita somente crypt → local dentro da raiz TEMP dedicada da prova."""
    try:
        root = Path(proof_root).expanduser().resolve(strict=True)
        temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
        config_file = Path(config_path).expanduser().resolve(strict=True)
        if (
            not root.is_dir()
            or root == temp_root
            or not root.is_relative_to(temp_root)
            or not root.name.casefold().startswith("pyp-open-source-proof-")
            or not config_file.is_file()
            or not config_file.is_relative_to(root)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", remote_name)
        ):
            raise ValueError

        config = configparser.ConfigParser(interpolation=None, strict=True)
        with config_file.open(encoding="utf-8") as stream:
            config.read_file(stream)
        if config.defaults() or len(config.sections()) != 2 or remote_name not in config:
            raise ValueError

        crypt = config[remote_name]
        if crypt.get("type", "").casefold() != "crypt":
            raise ValueError
        base_spec = crypt.get("remote", "").strip()
        base_name, separator, base_path_text = base_spec.partition(":")
        if (
            not separator
            or not base_name
            or base_name == remote_name
            or base_name not in config
            or set(config.sections()) != {remote_name, base_name}
        ):
            raise ValueError

        local = config[base_name]
        if local.get("type", "").casefold() != "local":
            raise ValueError
        local_path = Path(base_path_text).expanduser()
        if not local_path.is_absolute():
            raise ValueError
        resolved_local_path = local_path.resolve(strict=False)
        if (
            resolved_local_path == root
            or not resolved_local_path.is_relative_to(root)
        ):
            raise ValueError
        return config_file
    except (configparser.Error, OSError, RuntimeError, TypeError, ValueError):
        raise ValueError(_UNSAFE_RCLONE_PROOF_CONFIG) from None


def _rclone_proof_environment() -> dict[str, str]:
    """Remove overrides that could redirect validated config sections."""
    return {
        name: value
        for name, value in os.environ.items()
        if not name.upper().startswith("RCLONE_")
    }


def _run_rclone(
    binary: str,
    arguments: list[str],
    *,
    config_path: Path,
    input_data: bytes | None = None,
):
    result = subprocess.run(
        [binary, "--config", str(config_path), *arguments],
        input=input_data,
        capture_output=True,
        check=False,
        env=_rclone_proof_environment(),
    )
    if result.returncode:
        raise RuntimeError("Rclone synthetic proof operation failed")
    return result.stdout


class RcloneCryptProofStorage:
    """Storage de teste sobre um remote crypt temporário, sem rede externa."""

    def __init__(
        self,
        *,
        binary: str,
        remote: str,
        prefix: str,
        config_path: str | Path,
        proof_root: str | Path,
    ):
        self.binary = binary
        self.remote = remote.rstrip(":")
        self.prefix = prefix.strip("/")
        self.config_path = validate_rclone_proof_config(
            config_path=config_path,
            remote_name=self.remote,
            proof_root=proof_root,
        )
        self.mime_by_id: dict[str, str] = {}
        self.created = False
        self.events: list[str] = []
        self.last_read_status = "not_run"
        self.last_object_size: int | None = None
        self.last_object_mime: str | None = None

    def _run(self, arguments: list[str], *, input_data: bytes | None = None) -> bytes:
        return _run_rclone(
            self.binary,
            arguments,
            config_path=self.config_path,
            input_data=input_data,
        )

    @staticmethod
    def _object_key(remote_id: str) -> str:
        try:
            key = base64.urlsafe_b64decode(
                remote_id + "=" * (-len(remote_id) % 4),
            ).decode("ascii")
            parts = key.split("/")
            if len(parts) != 5 or any(str(UUID(part)) != part for part in parts):
                raise ValueError
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("synthetic remote object ID is invalid") from exc
        return key

    def _path(self, remote_id: str) -> str:
        return f"{self.remote}:{self.prefix}/{self._object_key(remote_id)}"

    @staticmethod
    def _remote_id(object_key: str) -> str:
        return base64.urlsafe_b64encode(object_key.encode("ascii")).decode("ascii").rstrip("=")

    def start(self) -> None:
        self.events.append("mkdir")
        self._run(["mkdir", f"{self.remote}:{self.prefix}"])
        self.created = True

    def upload_object(
        self,
        *,
        object_key: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        stream,
    ) -> ArchiveRemoteObject:
        self.events.append("upload")
        remote_id = self._remote_id(object_key)
        payload = stream.read()
        if len(payload) != size_bytes or hashlib.sha256(payload).hexdigest() != sha256:
            raise ValueError("synthetic proof upload input failed its declared checksum")
        existing = self.read_object(remote_id=remote_id)
        if existing is not None:
            destination = BytesIO()
            receipt = self.download_object(remote_id=remote_id, destination=destination)
            if receipt.size_bytes != size_bytes or receipt.sha256 != sha256:
                raise ValueError("synthetic proof idempotency key has different content")
            return existing
        self._run(["rcat", self._path(remote_id)], input_data=payload)
        self.mime_by_id[remote_id] = mime_type
        stored = self.read_object(remote_id=remote_id)
        if stored is None:
            raise RuntimeError("Rclone crypt readback did not find the uploaded object")
        return stored

    def read_object(self, *, remote_id: str) -> ArchiveRemoteObject | None:
        self.events.append("lsjson")
        self.last_read_status = "error"
        self.last_object_size = None
        self.last_object_mime = None
        try:
            result = subprocess.run(
                [
                    self.binary,
                    "--config",
                    str(self.config_path),
                    "lsjson",
                    f"{self.remote}:{self.prefix}",
                    "--recursive",
                ],
                capture_output=True,
                check=False,
                env=_rclone_proof_environment(),
            )
            if result.returncode:
                raise ValueError

            listing = json.loads(result.stdout.decode("utf-8"))
            if not isinstance(listing, list):
                raise TypeError

            object_key = self._object_key(remote_id)
            matches = []
            for entry in listing:
                if not isinstance(entry, dict):
                    raise TypeError
                entry_path = entry.get("Path")
                is_directory = entry.get("IsDir")
                if not isinstance(entry_path, str) or not isinstance(is_directory, bool):
                    raise TypeError
                if entry_path != object_key:
                    continue
                if is_directory:
                    raise ValueError
                size_bytes = entry.get("Size")
                if not isinstance(size_bytes, int) or isinstance(size_bytes, bool):
                    raise TypeError
                if size_bytes < 0:
                    raise ValueError
                matches.append(entry)

            if len(matches) > 1:
                raise ValueError
            if not matches:
                # Só uma listagem completa e válida, sem o caminho exato,
                # comprova a ausência no remote crypt local desta prova.
                self.last_read_status = "not_found"
                return None
            item = matches[0]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            self.last_read_status = "error"
            raise RuntimeError(_RCLONE_PROOF_READ_ERROR) from None

        # O backend local do Rclone pode informar application/octet-stream para
        # IDs opacos; o MIME original continua no catálogo existente e é espelhado
        # aqui a partir do upload, sem criar um catálogo remoto paralelo.
        mime_type = self.mime_by_id.get(remote_id) or item.get(
            "MimeType", "application/octet-stream",
        )
        self.last_read_status = "ok"
        self.last_object_size = int(item["Size"])
        self.last_object_mime = mime_type
        return ArchiveRemoteObject(remote_id, self.last_object_size, mime_type)

    def download_object(self, *, remote_id: str, destination) -> ArchiveDownloadReceipt:
        self.events.append("cat")
        payload = self._run(["cat", self._path(remote_id)])
        destination.write(payload)
        return ArchiveDownloadReceipt(len(payload), sha256(payload).hexdigest())

    def delete_object(self, *, remote_id: str) -> None:
        self.events.append("deletefile")
        result = subprocess.run(
            [
                self.binary,
                "--config",
                str(self.config_path),
                "deletefile",
                self._path(remote_id),
            ],
            capture_output=True,
            check=False,
            env=_rclone_proof_environment(),
        )
        if result.returncode and self.read_object(remote_id=remote_id) is not None:
            raise RuntimeError("Rclone crypt per-object deletion failed")

    def cleanup(self) -> None:
        if self.created:
            self.events.append("purge")
            self._run(["purge", f"{self.remote}:{self.prefix}"])
            self.created = False


def _write_rclone_proof_config(
    root: Path,
    *,
    crypt_type: str = "crypt",
    local_type: str = "local",
    local_path: Path | None = None,
    extra_remote: bool = False,
    config_outside_root: bool = False,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    store_path = local_path or (root / "rclone-media-store")
    config = configparser.ConfigParser(interpolation=None)
    config["media"] = {
        "type": crypt_type,
        "remote": f"proof-store:{store_path}",
        "filename_encryption": "standard",
        "directory_name_encryption": "true",
        "password": "synthetic-key-for-unit-test",
        "password2": "synthetic-salt-for-unit-test",
    }
    config["proof-store"] = {"type": local_type}
    if extra_remote:
        config["unrelated"] = {"type": "local"}
    config_path = (
        root.parent / "outside-rclone.conf"
        if config_outside_root
        else root / "rclone.conf"
    )
    with config_path.open("w", encoding="utf-8") as stream:
        config.write(stream)
    return config_path


def test_rclone_proof_config_guard_accepts_only_temp_crypt_over_local(tmp_path):
    root = tmp_path / "pyp-open-source-proof-guard-valid"
    config_path = _write_rclone_proof_config(root)

    assert validate_rclone_proof_config(
        config_path=config_path,
        remote_name="media",
        proof_root=root,
    ) == config_path.resolve()


def _rclone_read_test_storage(tmp_path):
    root = tmp_path / "pyp-open-source-proof-read-tests"
    config_path = _write_rclone_proof_config(root)
    storage = RcloneCryptProofStorage(
        binary="rclone",
        remote="media",
        prefix="proofs/read-tests",
        config_path=config_path,
        proof_root=root,
    )
    object_key = "/".join(str(uuid4()) for _ in range(5))
    return storage, object_key, storage._remote_id(object_key)


def _rclone_result(args, *, returncode=0, stdout=b"[]"):
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=b"synthetic failure detail")


def test_rclone_proof_read_object_marks_only_valid_listing_omission_not_found(
    monkeypatch,
    tmp_path,
):
    storage, _object_key, remote_id = _rclone_read_test_storage(tmp_path)
    storage.last_object_size = 7
    storage.last_object_mime = "text/plain"
    monkeypatch.setattr(subprocess, "run", lambda args, **_kwargs: _rclone_result(args))

    assert storage.read_object(remote_id=remote_id) is None

    assert storage.last_read_status == "not_found"
    assert storage.last_object_size is None
    assert storage.last_object_mime is None


def test_rclone_proof_read_object_returns_verified_object_metadata(monkeypatch, tmp_path):
    storage, object_key, remote_id = _rclone_read_test_storage(tmp_path)
    listing = [{
        "Path": object_key,
        "Name": object_key.rsplit("/", 1)[-1],
        "IsDir": False,
        "Size": 31,
        "MimeType": "image/jpeg",
    }]
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **_kwargs: _rclone_result(args, stdout=json.dumps(listing).encode()),
    )

    assert storage.read_object(remote_id=remote_id) == ArchiveRemoteObject(
        remote_id,
        31,
        "image/jpeg",
    )
    assert storage.last_read_status == "ok"


@pytest.mark.parametrize("returncode", [1, 3, 4, 5])
def test_rclone_proof_read_object_fails_closed_on_command_errors(
    monkeypatch,
    tmp_path,
    returncode,
):
    storage, _object_key, remote_id = _rclone_read_test_storage(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **_kwargs: _rclone_result(args, returncode=returncode),
    )

    with pytest.raises(RuntimeError, match=f"^{_RCLONE_PROOF_READ_ERROR}$"):
        storage.read_object(remote_id=remote_id)

    assert storage.last_read_status == "error"


@pytest.mark.parametrize("stdout", [
    b"not-json",
    b"{}",
    b"[null]",
])
def test_rclone_proof_read_object_fails_closed_on_malformed_listing(
    monkeypatch,
    tmp_path,
    stdout,
):
    storage, _object_key, remote_id = _rclone_read_test_storage(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **_kwargs: _rclone_result(args, stdout=stdout),
    )

    with pytest.raises(RuntimeError, match=f"^{_RCLONE_PROOF_READ_ERROR}$"):
        storage.read_object(remote_id=remote_id)

    assert storage.last_read_status == "error"


@pytest.mark.parametrize("size", [None, "31", -1, True])
def test_rclone_proof_read_object_fails_closed_on_missing_or_invalid_size(
    monkeypatch,
    tmp_path,
    size,
):
    storage, object_key, remote_id = _rclone_read_test_storage(tmp_path)
    entry = {"Path": object_key, "IsDir": False}
    if size is not None:
        entry["Size"] = size
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **_kwargs: _rclone_result(
            args,
            stdout=json.dumps([entry]).encode(),
        ),
    )

    with pytest.raises(RuntimeError, match=f"^{_RCLONE_PROOF_READ_ERROR}$"):
        storage.read_object(remote_id=remote_id)

    assert storage.last_read_status == "error"


def test_rclone_proof_read_object_sanitizes_subprocess_io_failures(
    monkeypatch,
    tmp_path,
):
    storage, _object_key, remote_id = _rclone_read_test_storage(tmp_path)

    def fail_io(*_args, **_kwargs):
        raise OSError("synthetic local configuration path leaked")

    monkeypatch.setattr(subprocess, "run", fail_io)

    with pytest.raises(RuntimeError, match=f"^{_RCLONE_PROOF_READ_ERROR}$") as captured:
        storage.read_object(remote_id=remote_id)

    assert str(captured.value) == _RCLONE_PROOF_READ_ERROR
    assert storage.last_read_status == "error"


def test_rclone_proof_commands_ignore_environment_overrides(monkeypatch):
    monkeypatch.setenv("RCLONE_CONFIG", "outside-config.ini")
    monkeypatch.setenv("RCLONE_CONFIG_MEDIA_REMOTE", "drive:customer-data")
    monkeypatch.setenv("RCLONE_CONFIG_PROOF_STORE_TYPE", "drive")
    monkeypatch.setenv("RCLONE_CONFIG_PASS", "synthetic-config-password")

    environment = _rclone_proof_environment()

    assert not any(name.upper().startswith("RCLONE_") for name in environment)


@pytest.mark.parametrize(
    ("case", "expected_remote"),
    [
        ("wrong_crypt_type", "media"),
        ("wrong_local_type", "media"),
        ("outside_local_path", "media"),
        ("relative_local_path", "media"),
        ("extra_remote", "media"),
        ("config_outside_root", "media"),
        ("missing_remote", "missing"),
        ("not_dedicated_temp_root", "media"),
    ],
)
def test_rclone_proof_config_guard_rejects_unsafe_configuration(
    tmp_path,
    case,
    expected_remote,
):
    root = tmp_path / "pyp-open-source-proof-guard-invalid"
    options = {}
    proof_root = root
    if case == "wrong_crypt_type":
        options["crypt_type"] = "drive"
    elif case == "wrong_local_type":
        options["local_type"] = "drive"
    elif case == "outside_local_path":
        options["local_path"] = tmp_path / "outside-store"
    elif case == "relative_local_path":
        options["local_path"] = Path("relative-store")
    elif case == "extra_remote":
        options["extra_remote"] = True
    elif case == "config_outside_root":
        options["config_outside_root"] = True
    elif case == "not_dedicated_temp_root":
        proof_root = tmp_path
    config_path = _write_rclone_proof_config(root, **options)

    with pytest.raises(ValueError, match=f"^{_UNSAFE_RCLONE_PROOF_CONFIG}$") as captured:
        validate_rclone_proof_config(
            config_path=config_path,
            remote_name=expected_remote,
            proof_root=proof_root,
        )
    assert "synthetic-key-for-unit-test" not in str(captured.value)


def _prepare_photographer(
    db: Session,
    *,
    tenant_id,
    photographer_id,
    slot: int,
    source_root: Path,
    instant,
):
    photo = create_photo(db, tenant_id)
    folder = db.get(PhotoFolder, photo.folder_id)
    assert folder is not None
    folder.status = "released"
    folder.released_at = instant - timedelta(days=90)
    folder.access_duration_days = 30
    folder.access_expires_at = instant - timedelta(days=60)

    payload = f"synthetic-photo-bytes-photographer-{slot}".encode("ascii")
    source_path = source_root.joinpath(*photo.storage_key.split("/"))
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(payload)

    client = Client(
        tenant_id=tenant_id,
        full_name=f"Cliente sintético {slot}",
        phone_e164=f"+551199999000{slot}",
    )
    db.add(client)
    db.flush()
    selection = PhotoSelection(
        tenant_id=tenant_id,
        parent_gallery_id=photo.parent_gallery_id,
        photo_asset_id=photo.id,
        client_id=client.id,
    )
    cycle_id = uuid4()
    archive_operation_id = uuid4()
    cycle = MediaArchiveCycle(
        id=cycle_id,
        tenant_id=tenant_id,
        parent_gallery_id=photo.parent_gallery_id,
        folder_id=folder.id,
        cycle_number=1,
        state="local",
    )
    operation = MediaArchiveOperation(
        id=archive_operation_id,
        tenant_id=tenant_id,
        cycle_id=cycle_id,
        operation_type="archive",
        status="queued",
        idempotency_key=f"open-source-proof-archive-{slot}-{uuid4()}",
        actor_type="system",
        created_at=instant + timedelta(seconds=slot),
    )
    db.add_all([selection, cycle, operation])
    db.flush()
    return {
        "tenant_id": tenant_id,
        "photographer_id": photographer_id,
        "photo_id": photo.id,
        "photo_ids": {photo.id},
        "selection_id": selection.id,
        "selection_ids": {selection.id},
        "gallery_id": photo.parent_gallery_id,
        "folder_id": folder.id,
        "cycle_id": cycle_id,
        "archive_operation_id": archive_operation_id,
        "source_path": source_path,
        "payload": payload,
    }


@pytest.mark.skipif(
    os.getenv("PYP_OPEN_SOURCE_PROOF") != "1",
    reason="Prova integrada opt-in; requer PostgreSQL sintético e Rclone crypt local.",
)
def test_postgres_two_photographers_rclone_crypt_media_flow(
    postgres_schema, tmp_path, monkeypatch,
):
    remote = os.getenv("PYP_PROOF_MEDIA_REMOTE")
    binary = os.getenv("PYP_PROOF_RCLONE_BINARY")
    rclone_config = os.getenv("RCLONE_CONFIG")
    proof_root = os.getenv("PYP_OPEN_SOURCE_PROOF_ROOT")
    if not remote or not binary or not rclone_config or not proof_root:
        pytest.fail(
            "Defina remote, binário Rclone, config e raiz TEMP dedicada da prova",
        )

    engine = postgres_schema
    Base.metadata.create_all(engine)
    source_root = (tmp_path / "media-source").resolve()
    staging_root = (tmp_path / "media-staging").resolve()
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "media-derivatives"))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(tmp_path / "media-history"))

    prefix = f"proofs/{uuid4().hex}"
    storage = RcloneCryptProofStorage(
        binary=binary,
        remote=remote,
        prefix=prefix,
        config_path=rclone_config,
        proof_root=proof_root,
    )
    storage.start()
    try:
        with Session(engine, expire_on_commit=False) as db:
            _root_tenant, tenant_a, owner, photographer_a = create_accounts(db)
            tenant_b = Tenant()
            db.add(tenant_b)
            db.flush()
            photographer_b = AdminUser(
                email="photographer-b@example.test",
                password_hash="synthetic",
                totp_secret="synthetic",
                email_verified=True,
            )
            photographer_b.tenant_memberships.append(
                TenantAdmin(tenant_id=tenant_b.id),
            )
            db.add(photographer_b)
            db.flush()
            db.add(TenantCreditWallet(tenant_id=tenant_b.id, mode="finite"))
            db.add(MediaArchiveCoordinator(id=1))
            db.add(MediaArchiveRecoveryPricing(
                id=1, recovery_fee_credits=2, updated_by_admin_id=owner.id,
            ))
            photographer_credits.grant_credits(
                db, owner.id, tenant_a.id, 5, "open-source-proof-a", "synthetic",
            )
            photographer_credits.grant_credits(
                db, owner.id, tenant_b.id, 5, "open-source-proof-b", "synthetic",
            )

            instant = now()
            first = _prepare_photographer(
                db,
                tenant_id=tenant_a.id,
                photographer_id=photographer_a.id,
                slot=1,
                source_root=source_root,
                instant=instant,
            )
            second = _prepare_photographer(
                db,
                tenant_id=tenant_b.id,
                photographer_id=photographer_b.id,
                slot=2,
                source_root=source_root,
                instant=instant,
            )
            db.commit()

            for item in (first, second):
                claim = claim_next_operation(db)
                assert claim is not None
                assert claim.operation_id == item["archive_operation_id"]
                result = execute_archive_operation(db, claim, storage=storage)
                operation = db.get(MediaArchiveOperation, item["archive_operation_id"])
                remote_count = db.scalar(sa.select(sa.func.count()).select_from(
                    MediaArchiveObject,
                ).where(
                    MediaArchiveObject.tenant_id == item["tenant_id"],
                    MediaArchiveObject.cycle_id == item["cycle_id"],
                    MediaArchiveObject.remote_object_id.is_not(None),
                ))
                assert result == MediaArchiveExecutionResult(
                    item["archive_operation_id"], "completed",
                ), (
                    f"sanitized archive failure: status={result.status}; "
                    f"code={result.error_code}; stage={operation.stage if operation else None}; "
                        f"remote_objects={remote_count}; adapter_calls={storage.events[-8:]}; "
                        f"read={storage.last_read_status}; size={storage.last_object_size}; "
                        f"mime={storage.last_object_mime}"
                )
                db.commit()

            for item in (first, second):
                cycle = db.get(MediaArchiveCycle, item["cycle_id"])
                assert cycle is not None and cycle.state == "archived"
                assert not item["source_path"].exists()
                rows = list(db.scalars(sa.select(MediaArchiveObject).where(
                    MediaArchiveObject.tenant_id == item["tenant_id"],
                    MediaArchiveObject.cycle_id == item["cycle_id"],
                )))
                assert len(rows) >= 2
                assert all(row.remote_object_id for row in rows)

            request_key = f"open-source-proof-recovery-{uuid4()}"
            request = recovery_billing.request_recovery(
                db,
                tenant_id=tenant_a.id,
                actor_admin_id=photographer_a.id,
                cycle_id=first["cycle_id"],
                duration_days=14,
                idempotency_key=request_key,
            )
            duplicate = recovery_billing.request_recovery(
                db,
                tenant_id=tenant_a.id,
                actor_admin_id=photographer_a.id,
                cycle_id=first["cycle_id"],
                duration_days=14,
                idempotency_key=request_key,
            )
            restore_operation_id = UUID(request["operation_id"])
            assert UUID(duplicate["operation_id"]) == restore_operation_id

            with pytest.raises(HTTPException) as cross_tenant:
                recovery_billing.request_recovery(
                    db,
                    tenant_id=tenant_a.id,
                    actor_admin_id=photographer_a.id,
                    cycle_id=second["cycle_id"],
                    duration_days=14,
                    idempotency_key=f"open-source-proof-cross-{uuid4()}",
                )
            assert cross_tenant.value.status_code == 404
            db.commit()

            claim = claim_next_operation(db)
            assert claim is not None and claim.operation_id == restore_operation_id
            before_photo_ids = set(db.scalars(sa.select(PhotoAsset.id)))
            before_selection_ids = set(db.scalars(sa.select(PhotoSelection.id)))
            before_operation_count = db.scalar(
                sa.select(sa.func.count()).select_from(MediaArchiveOperation),
            )
            result = execute_restore_operation(
                db,
                claim,
                storage=storage,
                staging_root=staging_root,
                capacity_provider=lambda _path: VolumeCapacity(
                    "d" * 64, 100 * 1024**3, 90 * 1024**3,
                ),
            )
            assert result == MediaArchiveExecutionResult(
                restore_operation_id, "completed",
            )

            for item in (first, second):
                folder = db.get(PhotoFolder, item["folder_id"])
                cycle = db.get(MediaArchiveCycle, item["cycle_id"])
                assert folder is not None and cycle is not None
                assert folder_media_is_local(db, folder) is (item is first)
                assert cycle.state == ("local" if item is first else "archived")
                assert item["source_path"].exists() is (item is first)
                if item is first:
                    assert item["source_path"].read_bytes() == item["payload"]
                    assert folder.access_duration_days == 14

            assert set(db.scalars(sa.select(PhotoAsset.id))) == before_photo_ids
            assert set(db.scalars(sa.select(PhotoSelection.id))) == before_selection_ids
            assert len(before_photo_ids) == 2 and len(before_selection_ids) == 2
            assert db.scalar(
                sa.select(sa.func.count()).select_from(MediaArchiveOperation),
            ) == before_operation_count
            ledger = list(db.scalars(sa.select(PhotographerCreditEntry).where(
                PhotographerCreditEntry.tenant_id == tenant_a.id,
                PhotographerCreditEntry.entry_type == "archive_recovery",
                PhotographerCreditEntry.archive_operation_id == restore_operation_id,
            )))
            assert len(ledger) == 1 and ledger[0].delta == -2
            reservation = db.scalar(sa.select(MediaArchiveRecoveryCreditReservation).where(
                MediaArchiveRecoveryCreditReservation.tenant_id == tenant_a.id,
                MediaArchiveRecoveryCreditReservation.operation_id == restore_operation_id,
            ))
            assert reservation is not None and reservation.status == "consumed"

        canary_key = "/".join(str(uuid4()) for _ in range(5))
        canary = b"synthetic per-object deletion canary"
        uploaded = storage.upload_object(
            object_key=canary_key,
            mime_type="text/plain",
            size_bytes=len(canary),
            sha256=sha256(canary).hexdigest(),
            stream=BytesIO(canary),
        )
        assert storage.read_object(remote_id=uploaded.remote_id) is not None
        storage.delete_object(remote_id=uploaded.remote_id)
        assert storage.read_object(remote_id=uploaded.remote_id) is None
        assert storage.last_read_status == "not_found"
    finally:
        storage.cleanup()
