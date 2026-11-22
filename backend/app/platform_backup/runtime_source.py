"""Fronteira do PostgreSQL de produção. Só identifica e lê a origem aprovada."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field

from .archive import CHUNK_SIZE
from .filesystem import BackupStorageError
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


def load_source_config() -> SourceConfig:
    if os.getenv("APP_ENV") != "production":
        raise BackupStorageError("unsafe")
    try:
        descriptor = _private_root(CONFIG_ROOT)
        try:
            source = _object(_read(descriptor, "source.json"), {
                "version", "database_container", "database_image", "api_container", "api_image",
                "database_name", "schema_revision", "system_identifier", "max_dump_bytes", "configuration",
            })
        finally:
            os.close(descriptor)
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
    except (OSError, TypeError, ValueError, RecursionError):
        raise BackupStorageError("unsafe") from None


def _docker(*args: str) -> bytes:
    result = subprocess.run([*_DOCKER, *args], capture_output=True, check=False, timeout=20)
    if result.returncode:
        raise BackupStorageError("io")
    return result.stdout


def attest_container(container: str, image: str, *, service: str) -> None:
    # O template nunca extrai env, mounts ou a configuração secreta do container.
    template = ('{{.Id}}|{{.Image}}|{{.Name}}|{{.State.Running}}|'
                '{{index .Config.Labels "com.docker.compose.project"}}|'
                '{{index .Config.Labels "com.docker.compose.service"}}')
    expected = f"{container}|{image}|/markina-gallery-{service}-1|true|markina-gallery|{service}"
    observed = _docker("container", "inspect", "--format", template, container).decode().strip()
    if observed != expected:
        raise BackupStorageError("unsafe")


def _pg(connection: SourceConfig, *args: str) -> tuple[str, ...]:
    return (*_DOCKER, "exec", "--env", "PGOPTIONS=" + _PG_OPTIONS, "--env", "PGAPPNAME=pyp-global-backup",
            connection.database_container, "sh", "-ceu",
            'test "$POSTGRES_DB" = "$1"; shift; exec "$@" --no-password -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
            "pyp-backup", connection.database_name, *args)


def _attest_database(source: SourceConfig) -> None:
    attest_container(source.database_container, source.database_image, service="db")
    sql = (
        "SELECT concat_ws('|',current_database(),current_setting('transaction_read_only'),"
        "current_setting('server_version_num'),system_identifier::text,"
        "(SELECT version_num FROM public.alembic_version)) FROM pg_control_system()"
    )
    result = subprocess.run(_pg(source, "psql", "-X", "-Atq", "-v", "ON_ERROR_STOP=1", "-c", sql),
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
