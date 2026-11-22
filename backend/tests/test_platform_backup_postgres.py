"""Opt-in: cria e remove somente dois containers PostgreSQL sintéticos próprios."""

import io
import json
import os
import subprocess
import tempfile
import time
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.platform_backup.archive import BackupContext, seal_archive
from app.platform_backup.payload import build_payload
from app.platform_backup.postgres_sandbox import DockerPostgresSandbox, local_docker_base
from app.platform_backup.restore import BackupRestoreError, restore_global
from app.platform_backup.runtime_source import SourceConfig
from app.platform_backup.runtime_source import snapshot as production_snapshot

pytestmark = pytest.mark.skipif(os.getenv("PYP_BACKUP_POSTGRES_TEST") != "1",
                                reason="PostgreSQL descartável exige opt-in local")
_USER = "pyp_backup_test"


@pytest.fixture
def sandboxes():
    base, run_id = local_docker_base(), uuid4()
    owned = []

    def command(args, *, data=None):
        result = subprocess.run(base + args, input=data, capture_output=True, timeout=60, check=False)
        assert result.returncode == 0, "Comando do ensaio sintético falhou"
        return result.stdout

    def sql(box, value, *, database=None):
        box._attest()
        return command(["exec", "-i", box.container_id, "psql", "-X", "-A", "-t", "-v",
                        "ON_ERROR_STOP=1", "-U", _USER, "-d", database or box.database],
                       data=value.encode()).decode().strip()

    try:
        for role, suffix in (("backup-source", "source"), ("restore-target", "target")):
            instance = uuid4()
            database = f"pyp_backup_{suffix}_{run_id.hex[:12]}"
            identifier = command([
                "run", "-d", "--pull", "never", "--name", f"pyp-backup-{suffix}-{run_id.hex[:12]}",
                "--label", "pyp.scope=backup-restore-synthetic", "--label", f"pyp.backup.run={run_id}",
                "--label", f"pyp.backup.instance={instance}", "--label", f"pyp.backup.role={role}",
                "--network", "none", "--pids-limit", "128", "--memory", "512m",
                "--tmpfs", "/var/lib/postgresql/data:rw,nosuid,size=256m",
                "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "-e", f"POSTGRES_USER={_USER}",
                "-e", f"POSTGRES_DB={database}", "postgres:17.11-alpine",
                "-c", "shared_buffers=32MB", "-c", "max_connections=15",
            ]).decode().strip()
            box = DockerPostgresSandbox(identifier, run_id, instance, role, database,
                                        {"SYNTHETIC_SECRET": "never-real-credential"})
            owned.append(box)
            ready = False
            for _ in range(80):
                result = subprocess.run(base + ["exec", identifier, "pg_isready", "-U", _USER,
                                                "-d", database], capture_output=True, timeout=5,
                                        check=False)
                if result.returncode == 0:
                    ready = True
                    break
                time.sleep(0.2)
            assert ready, "PostgreSQL sintético não ficou pronto"
            box._attest()
        source, target = owned
        sql(source, """
            CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY);
            INSERT INTO alembic_version VALUES ('20261105_0106');
            CREATE TABLE tenant (id integer PRIMARY KEY, name text NOT NULL);
            INSERT INTO tenant VALUES (1,'Tenant sintético A'),(2,'Tenant sintético B');
            CREATE TABLE ledger (tenant_id integer REFERENCES tenant(id), amount_cents bigint);
            INSERT INTO ledger VALUES (1,10001),(2,20002),(1,-123);
            CREATE TABLE biometric_envelope (tenant_id integer REFERENCES tenant(id), payload bytea);
            INSERT INTO biometric_envelope VALUES (1,decode('abcd','hex')),(2,decode('1234','hex'));
        """)
        peer = "pyp_backup_peer_" + run_id.hex[:12]
        sql(target, f"CREATE DATABASE {peer};")
        sql(target, "CREATE TABLE sentinel (value text); INSERT INTO sentinel VALUES ('preserve-me');",
            database=peer)
        yield source, target, sql, peer
    finally:
        for box in reversed(owned):
            # Atesta IDs/labels de criação, sem selecionar nomes por padrão ou wildcard.
            labels = json.loads(command(["inspect", "--format", "{{json .Config.Labels}}",
                                         box.container_id]))
            assert labels.get("pyp.scope") == "backup-restore-synthetic"
            assert labels.get("pyp.backup.run") == str(run_id)
            assert labels.get("pyp.backup.instance") == str(box.instance_id)
            assert labels.get("pyp.backup.role") == box.role
            command(["rm", "--force", box.container_id])


def encrypted_snapshot(source):
    context = BackupContext(source.instance_id, uuid4(), "20261105_0106", "test",
                             datetime.now(UTC))
    key, encrypted = bytes(range(32)), io.BytesIO()
    with source.snapshot(context) as snapshot, tempfile.TemporaryFile(mode="w+b") as payload:
        build_payload(snapshot.dump, snapshot.configuration, payload, context=context)
        payload.seek(0)
        artifact = seal_archive(payload, encrypted, key=key, context=context)
    return context, key, artifact, encrypted.getvalue()


def test_actual_global_restore_and_failure_rollback_preserve_source_and_peer(sandboxes):
    source, target, sql, peer = sandboxes
    assert sql(source, "SHOW server_version").startswith("17.11")
    baseline_query = """SELECT json_build_object(
        'tenants',(SELECT json_agg(id ORDER BY id) FROM tenant),
        'ledger',(SELECT sum(amount_cents) FROM ledger),
        'biometrics',(SELECT count(*) FROM biometric_envelope))"""
    baseline = json.loads(sql(source, baseline_query))
    context, key, artifact, encrypted = encrypted_snapshot(source)
    receipt = restore_global(io.BytesIO(encrypted), key=key, expected=context, artifact=artifact,
                             target=target, at=datetime.now(UTC))
    assert receipt.backup_id == context.backup_id
    assert receipt.configuration_items_checked == 2
    assert json.loads(sql(target, baseline_query)) == baseline
    assert json.loads(sql(source, baseline_query)) == baseline
    assert sql(target, "SELECT value FROM sentinel", database=peer) == "preserve-me"
    assert target.verify(context.schema_revision)
    with pytest.raises(BackupRestoreError):
        restore_global(io.BytesIO(encrypted), key=key, expected=context, artifact=artifact,
                       target=target, at=datetime.now(UTC))
    assert json.loads(sql(target, baseline_query)) == baseline

    empty_database = "pyp_backup_target_" + uuid4().hex[:12]
    sql(target, f"CREATE DATABASE {empty_database};")
    empty = replace(target, database=empty_database)
    changed = bytearray(encrypted)
    changed[-1] ^= 1
    with pytest.raises(BackupRestoreError):
        restore_global(io.BytesIO(changed), key=key, expected=context, artifact=artifact,
                       target=empty, at=datetime.now(UTC))
    assert empty.inspect().empty

    # Falha de ownership após DDL deve reverter toda a transação do restore.
    sql(source, "CREATE ROLE pyp_missing_owner; CREATE TABLE role_owned (value integer); "
                "ALTER TABLE role_owned OWNER TO pyp_missing_owner;")
    second_context, second_key, second_artifact, second_encrypted = encrypted_snapshot(source)
    with pytest.raises(BackupRestoreError):
        restore_global(io.BytesIO(second_encrypted), key=second_key, expected=second_context,
                       artifact=second_artifact, target=empty, at=datetime.now(UTC))
    assert empty.inspect().empty
    assert json.loads(sql(source, baseline_query)) == baseline
    assert sql(target, "SELECT value FROM sentinel", database=peer) == "preserve-me"
    # Um enum isolado também torna o banco não vazio, mesmo sem tabelas/funções.
    sql(empty, "CREATE TYPE existing_enum AS ENUM ('preserve');")
    assert not empty.inspect().empty
    with pytest.raises(BackupRestoreError):
        restore_global(io.BytesIO(encrypted), key=key, expected=context, artifact=artifact,
                       target=empty, at=datetime.now(UTC))
    assert sql(empty, "SELECT count(*) FROM pg_type WHERE typname='existing_enum'") == "1"


def test_production_snapshot_uses_read_only_postgres_and_keeps_source(sandboxes, monkeypatch):
    source, _, sql, _ = sandboxes
    version = sql(source, "SELECT current_setting('server_version_num');")
    system_identifier = sql(source, "SELECT system_identifier FROM pg_control_system();")
    identity = SourceConfig(source.container_id, "synthetic", "unused", "unused", source.database,
                            "20261105_0106", system_identifier, 1024 * 1024,
                            {"POSTGRES_SERVER_VERSION": version})
    monkeypatch.setattr("app.platform_backup.runtime_source._DOCKER", tuple(local_docker_base()))
    # A infraestrutura de teste tem nomes diferentes; o adapter sintético atesta seu ID e rede none.
    def attest(container, image, *, service):
        assert container == source.container_id and image == "synthetic" and service == "db"
        source._attest()

    monkeypatch.setattr("app.platform_backup.runtime_source.attest_container", attest)
    with production_snapshot(identity, "20261105_0106") as result:
        assert result.dump.read(5) == b"PGDMP"
    assert sql(source, "SELECT sum(amount_cents) FROM ledger;") == "29880"
