"""Fronteira do PostgreSQL de produção. Só identifica e lê a origem aprovada."""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field

from .archive import CHUNK_SIZE
from .filesystem import BackupStorageError, write_all
from .runtime_config import CONFIG_ROOT, _object, _private_root, _read
from .worker import GlobalSnapshot

_DOCKER = ("/usr/bin/docker", "--host", "unix:///var/run/docker.sock")
_ID = re.compile(r"[0-9a-f]{64}\Z")
_NAME = re.compile(r"[a-z_][a-z0-9_]{0,62}\Z")
_SCHEMA = re.compile(r"[A-Za-z0-9_]{1,64}\Z")
_CONFIG_ITEMS = {
    "APP_RELEASE", "PRODUCT_DOMAIN", "POSTGRES_SERVER_VERSION", "RECOVERY_CREDENTIAL_REFERENCES",
}
_RECOVERY_REFERENCES = "totp-keyring,google-oauth-client,integration-keyring"
_MAX_BYTES = 8 * 1024 ** 3
_MANAGED_API_PROJECT = re.compile(r"markina-gallery-app-[0-9a-f]{32}\Z")
_SOURCE_DUMP_LIMIT = 1024 ** 3
_SOURCE_QUERY = (
    "SELECT concat_ws('|',current_database(),current_setting('transaction_read_only'),"
    "current_setting('server_version_num'),system_identifier::text,"
    "(SELECT version_num FROM public.alembic_version)) FROM pg_control_system()"
)
_API_SOURCE_PROVIDER = """
import json, os, sys
from sqlalchemy import text
from app.auth import SessionLocal

try:
    if os.getenv("APP_ENV") != "production":
        raise ValueError
    with SessionLocal() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        db.execute(text("SET LOCAL statement_timeout = 8000"))
        db.execute(text("SET LOCAL lock_timeout = 2000"))
        witness = db.execute(text(sys.argv[1])).scalar_one()
    print(json.dumps({"release": os.getenv("APP_VERSION"), "witness": witness}))
except Exception:
    sys.exit(1)
"""

_PG_OPTIONS = "-c default_transaction_read_only=on -c lock_timeout=2000 -c statement_timeout=600000"


@dataclass(frozen=True, repr=False)
class SourceConfig:
    database_container: str
    database_image: str
    api_container: str
    api_image: str
    database_name: str
    schema_revision: str
    system_identifier: str
    max_dump_bytes: int
    configuration: dict[str, str] = field(repr=False)


def _parse_source_config(raw: bytes) -> SourceConfig:
    source = _object(raw, {
        "version", "database_container", "database_image", "api_container", "api_image",
        "database_name", "schema_revision", "system_identifier", "max_dump_bytes", "configuration",
    })
    for role in ("database", "api"):
        if not _ID.fullmatch(source[role + "_container"]) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", source[role + "_image"]
        ):
            raise ValueError
    items = source["configuration"]
    if (source["database_container"] == source["api_container"]
            or not _NAME.fullmatch(source["database_name"])
            or not _SCHEMA.fullmatch(source["schema_revision"])
            or not re.fullmatch(r"[1-9][0-9]{0,19}", source["system_identifier"])
            or type(source["max_dump_bytes"]) is not int or not 0 < source["max_dump_bytes"] <= _MAX_BYTES
            or not isinstance(items, dict) or set(items) != _CONFIG_ITEMS
            or any(not isinstance(v, str) or not 0 < len(v) <= 1024 for v in items.values())
            or items["PRODUCT_DOMAIN"] != "markina.pickyourpic.com.br"
            or not re.fullmatch(r"[0-9a-f]{40}", items["APP_RELEASE"])
            or items["RECOVERY_CREDENTIAL_REFERENCES"] != _RECOVERY_REFERENCES
            or not re.fullmatch(r"[0-9]{6}", items["POSTGRES_SERVER_VERSION"])):
        raise ValueError
    values = {key: value for key, value in source.items() if key != "version"}
    return SourceConfig(**values)


def load_source_config() -> SourceConfig:
    if os.getenv("APP_ENV") != "production":
        raise BackupStorageError("unsafe")
    try:
        descriptor = _private_root(CONFIG_ROOT)
        try:
            return _parse_source_config(_read(descriptor, "source.json"))
        finally:
            os.close(descriptor)
    except (OSError, TypeError, ValueError, RecursionError):
        raise BackupStorageError("unsafe") from None


def _docker(*args: str) -> bytes:
    result = subprocess.run([*_DOCKER, *args], capture_output=True, check=False, timeout=20)
    if result.returncode:
        raise BackupStorageError("io")
    return result.stdout


def attest_container(container: str, image: str, *, service: str) -> None:
    if service not in {"api", "db"} or not _ID.fullmatch(container) or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", image,
    ):
        raise BackupStorageError("unsafe")
    # O template nunca extrai env, mounts ou a configuração secreta do container.
    template = ('{{.Id}}|{{.Image}}|{{.Name}}|{{.State.Running}}|'
                '{{index .Config.Labels "com.docker.compose.project"}}|'
                '{{index .Config.Labels "com.docker.compose.service"}}')
    fields = _docker("container", "inspect", "--format", template, container).decode().strip().split("|")
    if (len(fields) != 6 or fields[:2] != [container, image]
            or fields[3] != "true" or fields[5] != service):
        raise BackupStorageError("unsafe")
    name, project = fields[2], fields[4]
    if service == "api" and _MANAGED_API_PROJECT.fullmatch(project):
        return
    if project != "markina-gallery" or name != f"/markina-gallery-{service}-1":
        raise BackupStorageError("unsafe")


def _collect_source(witness: object) -> bytes:
    """Deriva a configuração somente das identidades do wrapper e metadados atestados."""
    if not isinstance(witness, dict) or set(witness) != {"api", "db", "schema_revision"}:
        raise ValueError
    for role in ("api", "db"):
        item = witness[role]
        if (not isinstance(item, dict) or set(item) != {"id", "image"}
                or not all(isinstance(value, str) for value in item.values())):
            raise ValueError
        attest_container(item["id"], item["image"], service=role)
    if witness["api"]["id"] == witness["db"]["id"]:
        raise ValueError
    api = witness["api"]
    db = witness["db"]
    database = _docker(
        "exec", "--env", "PGOPTIONS=-c default_transaction_read_only=on -c lock_timeout=2000 -c statement_timeout=8000",
        db["id"], "sh", "-ceu",
        'exec psql -X -Atq --no-password -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$1"',
        "pyp-backup-source", _SOURCE_QUERY,
    ).decode("ascii").strip()
    database_name, read_only, version, system_identifier, schema = database.split("|")
    if read_only != "on" or schema != witness["schema_revision"]:
        raise ValueError
    observed = _docker("exec", api["id"], "python", "-B", "-c", _API_SOURCE_PROVIDER, _SOURCE_QUERY)
    if not 0 < len(observed) <= 4096:
        raise ValueError
    proof = json.loads(observed)
    if not isinstance(proof, dict) or set(proof) != {"release", "witness"} or proof["witness"] != database:
        raise ValueError
    for role in ("api", "db"):
        item = witness[role]
        attest_container(item["id"], item["image"], service=role)
    return (json.dumps({
        "version": 1,
        "database_container": db["id"],
        "database_image": db["image"],
        "api_container": api["id"],
        "api_image": api["image"],
        "database_name": database_name,
        "schema_revision": schema,
        "system_identifier": system_identifier,
        "max_dump_bytes": _SOURCE_DUMP_LIMIT,
        "configuration": {
            "APP_RELEASE": proof["release"],
            "PRODUCT_DOMAIN": "markina.pickyourpic.com.br",
            "POSTGRES_SERVER_VERSION": version,
            "RECOVERY_CREDENTIAL_REFERENCES": _RECOVERY_REFERENCES,
        },
    }, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _create_source(directory: int, raw: bytes) -> None:
    temporary = f".source-{secrets.token_hex(16)}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                         dir_fd=directory)
    try:
        try:
            write_all(descriptor, raw)
            os.fchmod(descriptor, 0o400)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        # O link publica atomicamente, com recusa se source.json já existir.
        os.link(temporary, "source.json", src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
    finally:
        os.unlink(temporary, dir_fd=directory)
    os.fsync(directory)


def prepare_source_config(witness: object, *, root=CONFIG_ROOT) -> None:
    if os.getenv("APP_ENV") != "production":
        raise BackupStorageError("unsafe")
    try:
        directory = _private_root(root)
        try:
            raw = _collect_source(witness)
            expected = _parse_source_config(raw)
            try:
                observed = _read(directory, "source.json")
            except FileNotFoundError:
                _create_source(directory, raw)
                observed = _read(directory, "source.json")
            if _parse_source_config(observed) != expected:
                raise BackupStorageError("conflict")
        finally:
            os.close(directory)
    except (OSError, TypeError, ValueError, RecursionError, subprocess.SubprocessError):
        raise BackupStorageError("unsafe") from None


def _pg(connection: SourceConfig, *args: str) -> tuple[str, ...]:
    return (*_DOCKER, "exec", "--env", "PGOPTIONS=" + _PG_OPTIONS, "--env", "PGAPPNAME=pyp-global-backup",
            connection.database_container, "sh", "-ceu",
            'test "$POSTGRES_DB" = "$1"; shift; exec "$@" --no-password -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
            "pyp-backup", connection.database_name, *args)


def _attest_database(source: SourceConfig) -> None:
    attest_container(source.database_container, source.database_image, service="db")
    result = subprocess.run(_pg(source, "psql", "-X", "-Atq", "-v", "ON_ERROR_STOP=1", "-c", _SOURCE_QUERY),
                            capture_output=True, check=False, timeout=20)
    expected = "|".join((source.database_name, "on", source.configuration["POSTGRES_SERVER_VERSION"],
                         source.system_identifier, source.schema_revision))
    if result.returncode or result.stdout.decode().strip() != expected:
        raise BackupStorageError("unsafe")


@contextmanager
def snapshot(source: SourceConfig, schema_revision: str):
    if schema_revision != source.schema_revision:
        raise BackupStorageError("unsafe")
    _attest_database(source)
    with tempfile.TemporaryFile(mode="w+b") as dump:
        args = _pg(source, "timeout", "-k", "10", "600", "pg_dump", "-Fc", "--lock-wait-timeout=2s")
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
            try:
                size = 0
                while chunk := process.stdout.read(CHUNK_SIZE):
                    size += len(chunk)
                    if size > source.max_dump_bytes:
                        raise BackupStorageError("quota")
                    dump.write(chunk)
                if process.wait(timeout=30) or size == 0:
                    raise BackupStorageError("io")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=15)
        _attest_database(source)
        dump.seek(0)
        yield GlobalSnapshot(dump, source.configuration)
