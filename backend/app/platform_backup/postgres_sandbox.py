"""Adapter exclusivo de PostgreSQL sintético em Docker Desktop local, sem rede."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import BinaryIO
from uuid import UUID

from .archive import CHUNK_SIZE, BackupContext, _local_runtime
from .restore import RestoreTargetState
from .worker import GlobalSnapshot

_USER = "pyp_backup_test"
_INSPECT = ('{"id":{{json .Id}},"name":{{json .Name}},"labels":{{json .Config.Labels}},'
            '"running":{{json .State.Running}},"network":{{json .HostConfig.NetworkMode}},'
            '"ports":{{json .HostConfig.PortBindings}}}')


class PostgresSandboxError(RuntimeError):
    pass


def local_docker_base() -> list[str]:
    _local_runtime()
    try:
        result = subprocess.run(["docker", "context", "inspect", "desktop-linux", "--format",
                                 "{{.Endpoints.docker.Host}}"], capture_output=True, text=True,
                                timeout=15, check=False)
        endpoint = result.stdout.strip()
        if result.returncode or not endpoint.startswith(("npipe:////./pipe/", "unix:///")):
            raise ValueError
        return ["docker", "--host", endpoint]
    except (OSError, ValueError, subprocess.SubprocessError):
        raise PostgresSandboxError("Daemon local de ensaio indisponível.") from None


@dataclass(frozen=True, repr=False)
class DockerPostgresSandbox:
    container_id: str = field(repr=False)
    run_id: UUID
    instance_id: UUID
    role: str
    database: str = field(repr=False)
    configuration: dict[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        prefix = "source" if self.role == "backup-source" else "target" if self.role == "restore-target" else None
        if (prefix is None or not isinstance(self.container_id, str)
                or not re.fullmatch(r"[0-9a-f]{64}", self.container_id)
                or not isinstance(self.run_id, UUID) or not isinstance(self.instance_id, UUID)
                or not re.fullmatch(r"pyp_backup_" + prefix + r"_[0-9a-f]{12}", self.database)):
            raise PostgresSandboxError("Identidade de ensaio inválida.")

    def __repr__(self) -> str:
        return "DockerPostgresSandbox(<redacted>)"

    def _attest(self) -> list[str]:
        base = local_docker_base()
        try:
            result = subprocess.run(base + ["inspect", "--format", _INSPECT, self.container_id],
                                    capture_output=True, text=True, timeout=15, check=False)
            data = json.loads(result.stdout)
            labels = data.get("labels") or {}
            if (result.returncode or data.get("id") != self.container_id
                    or not data.get("name", "").startswith("/pyp-backup-")
                    or data.get("running") is not True or data.get("network") != "none"
                    or data.get("ports") not in ({}, None)
                    or labels.get("pyp.scope") != "backup-restore-synthetic"
                    or labels.get("pyp.backup.run") != str(self.run_id)
                    or labels.get("pyp.backup.instance") != str(self.instance_id)
                    or labels.get("pyp.backup.role") != self.role):
                raise ValueError
            return base
        except (OSError, ValueError, TypeError, subprocess.SubprocessError):
            raise PostgresSandboxError("Container não autorizado para ensaio.") from None

    def _query(self, sql: str) -> str:
        base = self._attest()
        result = subprocess.run(base + ["exec", self.container_id, "psql", "-X", "-A", "-t",
                                "--no-password", "-v", "ON_ERROR_STOP=1", "-U", _USER,
                                "-d", self.database, "-c", sql],
                                capture_output=True, text=True, timeout=20, check=False)
        if result.returncode:
            raise PostgresSandboxError("Consulta de ensaio não confirmada.")
        return result.stdout.strip()

    @contextmanager
    def snapshot(self, context: BackupContext):
        if self.role != "backup-source" or context.instance_id != self.instance_id:
            raise PostgresSandboxError("Origem de ensaio incompatível.")
        if self._query("SELECT version_num FROM public.alembic_version") != context.schema_revision:
            raise PostgresSandboxError("Schema da origem de ensaio divergente.")
        base = self._attest()
        with tempfile.TemporaryFile(mode="w+b") as dump, tempfile.TemporaryFile() as errors:
            result = subprocess.run(base + ["exec", self.container_id, "pg_dump", "-Fc",
                                    "--no-password", "-U", _USER, "-d", self.database],
                                    stdout=dump, stderr=errors, timeout=120, check=False)
            if result.returncode:
                raise PostgresSandboxError("Dump sintético não confirmado.")
            dump.seek(0)
            configuration = dict(self.configuration)
            configuration["ROLE_METADATA"] = self._query(
                "SELECT json_build_object('role',current_user,'database_owner',"
                "pg_get_userbyid(datdba)) FROM pg_database WHERE datname=current_database()")
            yield GlobalSnapshot(dump, configuration)

    def inspect(self) -> RestoreTargetState:
        if self.role != "restore-target":
            raise PostgresSandboxError("Destino de ensaio inválido.")
        empty = self._query(
            "SELECT (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema') + "
            "(SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema') + "
            "(SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace "
            "WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema') + "
            "(SELECT count(*) FROM pg_namespace WHERE nspname !~ '^pg_' "
            "AND nspname NOT IN ('public','information_schema')) + "
            "(SELECT count(*) FROM pg_event_trigger) + "
            "(SELECT count(*) FROM pg_extension WHERE extname<>'plpgsql') + "
            "(SELECT count(*) FROM pg_foreign_server) + "
            "(SELECT count(*) FROM pg_publication) + "
            "(SELECT count(*) FROM pg_subscription) + "
            "(SELECT count(*) FROM pg_default_acl)") == "0"
        owner = self._query("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()")
        return RestoreTargetState(self.instance_id, "test", owner == _USER, empty, True)

    def restore(self, dump: BinaryIO) -> None:
        state = self.inspect()
        if not state.disposable or not state.empty:
            raise PostgresSandboxError("Destino de ensaio não está vazio.")
        base = self._attest()
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(base + ["exec", "-i", self.container_id, "pg_restore",
                "--exit-on-error", "--single-transaction", "--no-password", "-U", _USER,
                "-d", self.database], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                stderr=errors)
            try:
                while part := dump.read(CHUNK_SIZE):
                    if not isinstance(part, bytes) or len(part) > CHUNK_SIZE:
                        raise ValueError
                    process.stdin.write(part)
                process.stdin.close()
                if process.wait(timeout=120):
                    raise ValueError
            except (OSError, ValueError, subprocess.SubprocessError):
                raise PostgresSandboxError("Restore sintético não confirmado.") from None
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                if process.stdin is not None and not process.stdin.closed:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass

    def verify(self, schema_revision: str) -> bool:
        if self.role != "restore-target":
            return False
        return (self._query("SELECT version_num FROM public.alembic_version") == schema_revision
                and self._query("SELECT count(*) FROM pg_class c JOIN pg_namespace n "
                    "ON n.oid=c.relnamespace WHERE n.nspname='public' AND "
                    "pg_get_userbyid(c.relowner)<>current_user") == "0")
