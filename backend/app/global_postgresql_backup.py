"""Fixed, secret-safe execution of a PostgreSQL global backup snapshot.

This module is deliberately not wired to an API, scheduler, or worker yet. Its
caller must supply private runtime configuration; no user-controlled command,
path, repository option, or retention operation is accepted here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL, make_url

PINNED_POSTGRESQL_MAJOR = 17
PINNED_RESTIC_VERSION = "0.20.0"
PINNED_RCLONE_VERSION = "1.76.0"
ARCHIVE_FILENAME = "global-postgresql.dump"
SNAPSHOT_TAG = "global-postgresql"

_REMOTE_PATTERN = re.compile(r"^rclone:([A-Za-z0-9_.-]+):([A-Za-z0-9_./-]+)$")
_VERSION_PATTERN = re.compile(r"\b[vV]?(\d+)\.(\d+)(?:\.(\d+))?\b")
_SAFE_LIBPQ_QUERY_KEYS = frozenset(
    {
        "application_name",
        "connect_timeout",
        "sslcert",
        "sslkey",
        "sslmode",
        "sslrootcert",
        "target_session_attrs",
    }
)


class GlobalPostgreSQLBackupError(RuntimeError):
    """Static error codes only; subprocess output and credentials are omitted."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GlobalPostgreSQLBackupConfig:
    repository: str
    restic_password_file: Path
    rclone_config_file: Path
    repository_root: Path
    pg_dump_executable: str = "pg_dump"
    pg_restore_executable: str = "pg_restore"
    restic_executable: str = "restic"
    rclone_executable: str = "rclone"


@dataclass(frozen=True)
class GlobalPostgreSQLBackupReceipt:
    snapshot_id: str
    dump_size_bytes: int
    verified: bool


def _resolved_external_file(path: Path, repository_root: Path) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
        root = repository_root.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise GlobalPostgreSQLBackupError("configuration_invalid") from None
    if not resolved.is_file() or resolved.is_relative_to(root):
        raise GlobalPostgreSQLBackupError("configuration_invalid")
    try:
        mode = stat.S_IMODE(resolved.stat().st_mode)
    except OSError:
        raise GlobalPostgreSQLBackupError("configuration_invalid") from None
    if os.name == "posix" and mode & 0o077:
        raise GlobalPostgreSQLBackupError("configuration_invalid")
    return resolved


def _validate_config(config: GlobalPostgreSQLBackupConfig) -> tuple[Path, Path]:
    match = _REMOTE_PATTERN.fullmatch(config.repository)
    if (
        match is None
        or match.group(2).startswith("/")
        or any(part in {"", ".", ".."} for part in match.group(2).split("/"))
    ):
        raise GlobalPostgreSQLBackupError("configuration_invalid")
    if not config.repository_root.exists() or not config.repository_root.is_dir():
        raise GlobalPostgreSQLBackupError("configuration_invalid")
    password_file = _resolved_external_file(config.restic_password_file, config.repository_root)
    rclone_config = _resolved_external_file(config.rclone_config_file, config.repository_root)
    if password_file.stat().st_size == 0 or rclone_config.stat().st_size == 0:
        raise GlobalPostgreSQLBackupError("configuration_invalid")
    return password_file, rclone_config


def _version_text(executable: str, args: tuple[str, ...]) -> str:
    resolved = shutil.which(executable)
    if not resolved:
        raise GlobalPostgreSQLBackupError("tool_unavailable")
    try:
        result = subprocess.run(
            [resolved, *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
            env=_base_environment(),
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise GlobalPostgreSQLBackupError("tool_version_unverified") from None
    return result.stdout


def _first_version(value: str) -> tuple[int, int, int]:
    match = _VERSION_PATTERN.search(value)
    if match is None:
        raise GlobalPostgreSQLBackupError("tool_version_unverified")
    return tuple(int(item or 0) for item in match.groups())


def _validate_tool_versions(config: GlobalPostgreSQLBackupConfig) -> None:
    pg_dump_version = _first_version(_version_text(config.pg_dump_executable, ("--version",)))
    pg_restore_version = _first_version(_version_text(config.pg_restore_executable, ("--version",)))
    restic_version = _first_version(_version_text(config.restic_executable, ("version",)))
    rclone_version = _first_version(_version_text(config.rclone_executable, ("version",)))
    if (
        pg_dump_version[0] != PINNED_POSTGRESQL_MAJOR
        or pg_restore_version[0] != PINNED_POSTGRESQL_MAJOR
        or ".".join(str(part) for part in restic_version) != PINNED_RESTIC_VERSION
        or ".".join(str(part) for part in rclone_version) != PINNED_RCLONE_VERSION
    ):
        raise GlobalPostgreSQLBackupError("tool_version_mismatch")


def _database_url_without_password(value: str) -> tuple[URL, URL]:
    try:
        database_url = make_url(value)
    except (TypeError, ValueError):
        raise GlobalPostgreSQLBackupError("database_configuration_invalid") from None
    if (
        database_url.get_backend_name() != "postgresql"
        or not database_url.database
        or not database_url.username
        or any(key not in _SAFE_LIBPQ_QUERY_KEYS for key in database_url.query)
    ):
        raise GlobalPostgreSQLBackupError("database_configuration_invalid")
    try:
        libpq_url = URL.create(
            drivername="postgresql",
            username=database_url.username,
            password=None,
            host=database_url.host,
            port=database_url.port,
            database=database_url.database,
            query=dict(database_url.query),
        )
        # Rendering is safe after removing the password and rejecting unknown
        # query parameters, which could otherwise carry secret material.
        libpq_url.render_as_string(hide_password=False)
    except (TypeError, ValueError):
        raise GlobalPostgreSQLBackupError("database_configuration_invalid") from None
    return database_url, libpq_url


def _pgpass_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:")


def _pgpass_line(database_url: URL) -> bytes:
    fields = (
        database_url.host or "*",
        str(database_url.port) if database_url.port is not None else "*",
        str(database_url.database or "*"),
        str(database_url.username or "*"),
        str(database_url.password),
    )
    if any("\n" in field or "\r" in field for field in fields):
        raise GlobalPostgreSQLBackupError("database_configuration_invalid")
    return ":".join(_pgpass_escape(field) for field in fields).encode("utf-8")


@contextmanager
def _temporary_pgpass(database_url: URL) -> Iterator[Path | None]:
    if database_url.password is None:
        yield None
        return
    if os.name != "posix":
        raise GlobalPostgreSQLBackupError("database_credentials_permissions_unverified")
    payload = _pgpass_line(database_url)
    descriptor = -1
    path: Path | None = None
    try:
        descriptor, filename = tempfile.mkstemp(prefix="pyp-global-backup-", suffix=".pgpass")
        path = Path(filename)
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
    except OSError:
        if descriptor >= 0:
            os.close(descriptor)
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise GlobalPostgreSQLBackupError("database_configuration_invalid") from None
    try:
        yield path
    finally:
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                raise GlobalPostgreSQLBackupError("database_configuration_cleanup_failed") from None


def _base_environment() -> dict[str, str]:
    return {
        name: value
        for name, value in os.environ.items()
        if name
        in {
            "PATH",
            "HOME",
            "TMP",
            "TEMP",
            "TMPDIR",
            "LANG",
            "LC_ALL",
            "APPDATA",
            "LOCALAPPDATA",
            "USERPROFILE",
            "SYSTEMROOT",
            "WINDIR",
        }
    }


def _command_environment(
    password_file: Path,
    rclone_config: Path,
    *,
    pgpass_file: Path | None,
) -> tuple[dict[str, str], dict[str, str]]:
    base = _base_environment()
    restic_env = base.copy()
    restic_env["RESTIC_PASSWORD_FILE"] = str(password_file)
    restic_env["RCLONE_CONFIG"] = str(rclone_config)
    pg_env = base.copy()
    if pgpass_file is not None:
        pg_env["PGPASSFILE"] = str(pgpass_file)
    return pg_env, restic_env


def _snapshot_id(stdout: bytes) -> str:
    try:
        messages = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise GlobalPostgreSQLBackupError("snapshot_create_failed") from None
    for message in reversed(messages):
        if not isinstance(message, dict):
            raise GlobalPostgreSQLBackupError("snapshot_create_failed")
        if message.get("message_type") == "summary":
            value = message.get("snapshot_id")
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{8,64}", value):
                return value
    raise GlobalPostgreSQLBackupError("snapshot_create_failed")


def _start(
    args: list[str],
    *,
    stdin: int | object = subprocess.DEVNULL,
    stdout: int | object = subprocess.DEVNULL,
    env: dict[str, str],
) -> subprocess.Popen[bytes]:
    try:
        return subprocess.Popen(
            args,
            stdin=stdin,
            stdout=stdout,
            stderr=subprocess.DEVNULL,
            env=env,
            shell=False,
        )
    except OSError:
        raise GlobalPostgreSQLBackupError("backup_execution_failed") from None


def create_global_postgresql_backup(
    database_url_value: str,
    config: GlobalPostgreSQLBackupConfig,
) -> GlobalPostgreSQLBackupReceipt:
    """Create and read back one encrypted PostgreSQL dump snapshot.

    This operation never initializes or prunes the repository. The snapshot is
    only reported as verified after the decrypted readback hash matches the
    streamed dump and `pg_restore --list` accepts the archive.
    """

    password_file, rclone_config = _validate_config(config)
    _validate_tool_versions(config)
    database_url, libpq_url = _database_url_without_password(database_url_value)
    libpq_connection = libpq_url.render_as_string(hide_password=False)

    with _temporary_pgpass(database_url) as pgpass_file:
        pg_env, restic_env = _command_environment(
            password_file,
            rclone_config,
            pgpass_file=pgpass_file,
        )
        restic = _start(
            [
                shutil.which(config.restic_executable) or config.restic_executable,
                "-r",
                config.repository,
                "backup",
                "--json",
                "--stdin",
                "--stdin-filename",
                ARCHIVE_FILENAME,
                "--tag",
                SNAPSHOT_TAG,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=restic_env,
        )
        try:
            dump = _start(
                [
                    shutil.which(config.pg_dump_executable) or config.pg_dump_executable,
                    "--format=custom",
                    "--no-password",
                    "--dbname",
                    libpq_connection,
                ],
                stdout=subprocess.PIPE,
                env=pg_env,
            )
        except GlobalPostgreSQLBackupError:
            if restic.poll() is None:
                restic.terminate()
            restic.wait()
            raise
        if dump.stdout is None or restic.stdin is None or restic.stdout is None:
            raise GlobalPostgreSQLBackupError("backup_execution_failed")

        dump_digest = hashlib.sha256()
        dump_size = 0
        try:
            while chunk := dump.stdout.read(1024 * 1024):
                dump_digest.update(chunk)
                dump_size += len(chunk)
                restic.stdin.write(chunk)
            restic.stdin.close()
            dump.stdout.close()
            restic_output = restic.stdout.read()
            restic.stdout.close()
            dump_status = dump.wait()
            restic_status = restic.wait()
        except (BrokenPipeError, OSError):
            for process in (dump, restic):
                if process.poll() is None:
                    process.terminate()
            for process in (dump, restic):
                process.wait()
            raise GlobalPostgreSQLBackupError("backup_execution_failed") from None

        if dump_status != 0:
            raise GlobalPostgreSQLBackupError("pg_dump_failed")
        if restic_status != 0 or dump_size == 0:
            raise GlobalPostgreSQLBackupError("snapshot_create_failed")
        snapshot_id = _snapshot_id(restic_output)

        restored_hash, restored_size, restore_status = _readback_archive(
            config=config,
            restic_env=restic_env,
            snapshot_id=snapshot_id,
        )
        if (
            restore_status != 0
            or restored_size != dump_size
            or restored_hash != dump_digest.hexdigest()
        ):
            raise GlobalPostgreSQLBackupError("snapshot_readback_failed")

    return GlobalPostgreSQLBackupReceipt(
        snapshot_id=snapshot_id,
        dump_size_bytes=dump_size,
        verified=True,
    )


def _readback_archive(
    *,
    config: GlobalPostgreSQLBackupConfig,
    restic_env: dict[str, str],
    snapshot_id: str,
) -> tuple[str, int, int]:
    restic_dump = _start(
        [
            shutil.which(config.restic_executable) or config.restic_executable,
            "-r",
            config.repository,
            "dump",
            snapshot_id,
            ARCHIVE_FILENAME,
        ],
        stdout=subprocess.PIPE,
        env=restic_env,
    )
    restore_env = _base_environment()
    try:
        pg_restore = _start(
            [
                shutil.which(config.pg_restore_executable) or config.pg_restore_executable,
                "--list",
            ],
            stdin=subprocess.PIPE,
            env=restore_env,
        )
    except GlobalPostgreSQLBackupError:
        if restic_dump.poll() is None:
            restic_dump.terminate()
        restic_dump.wait()
        raise
    if restic_dump.stdout is None or pg_restore.stdin is None:
        raise GlobalPostgreSQLBackupError("snapshot_readback_failed")
    digest = hashlib.sha256()
    size = 0
    try:
        while chunk := restic_dump.stdout.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
            pg_restore.stdin.write(chunk)
        pg_restore.stdin.close()
        restic_dump.stdout.close()
        restic_status = restic_dump.wait()
        restore_status = pg_restore.wait()
    except (BrokenPipeError, OSError):
        for process in (restic_dump, pg_restore):
            if process.poll() is None:
                process.terminate()
        for process in (restic_dump, pg_restore):
            process.wait()
        raise GlobalPostgreSQLBackupError("snapshot_readback_failed") from None
    if restic_status != 0:
        raise GlobalPostgreSQLBackupError("snapshot_readback_failed")
    return digest.hexdigest(), size, restore_status
