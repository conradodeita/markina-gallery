"""Autenticação precede inspeção/escrita; alvo sintético sem conexão externa."""

import io
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.platform_backup.archive import BackupContext, seal_archive
from app.platform_backup.payload import build_payload
from app.platform_backup.restore import (
    BackupRestoreError,
    RestoreTargetState,
    restore_global,
)


@pytest.fixture
def prepared():
    context = BackupContext(uuid4(), uuid4(), "20261105_0106", "test", datetime.now(UTC))
    clear, encrypted, key = io.BytesIO(), io.BytesIO(), bytes(range(32))
    build_payload(io.BytesIO(b"PGDMP-synthetic-dump"), {"KEY": "never-apply-secret"},
                  clear, context=context)
    clear.seek(0)
    artifact = seal_archive(clear, encrypted, key=key, context=context)
    return context, key, artifact, encrypted.getvalue()


class Target:
    def __init__(self):
        self.state = RestoreTargetState(uuid4(), "test", True, True, True)
        self.inspections, self.writes = 0, 0
        self.schema_matches = True

    def inspect(self):
        self.inspections += 1
        return self.state

    def restore(self, dump):
        assert dump.read() == b"PGDMP-synthetic-dump"
        self.writes += 1

    def verify(self, schema_revision):
        return self.schema_matches


def execute(prepared, target, **changes):
    context, key, artifact, encrypted = prepared
    parameters = {"key": key, "expected": context, "artifact": artifact, "target": target,
                  "at": datetime.now(UTC)}
    parameters.update(changes)
    return restore_global(io.BytesIO(encrypted), **parameters)


def test_restore_receipt_is_separate_from_upload_and_never_applies_configuration(prepared):
    target = Target()
    receipt = execute(prepared, target)
    assert target.writes == 1
    assert receipt.backup_id == prepared[0].backup_id
    assert receipt.schema_revision == prepared[0].schema_revision
    assert receipt.target_instance_id == target.state.instance_id
    assert receipt.configuration_items_checked == 1
    assert "never-apply-secret" not in repr(receipt)
    assert receipt.elapsed_seconds >= 0


@pytest.mark.parametrize("failure", ["key", "schema", "hash", "truncation"])
def test_invalid_archive_never_even_inspects_target(prepared, failure):
    target = Target()
    context, key, artifact, encrypted = prepared
    if failure == "key":
        prepared = context, b"z" * 32, artifact, encrypted
    elif failure == "schema":
        prepared = replace(context, schema_revision="other_schema"), key, artifact, encrypted
    elif failure == "hash":
        prepared = context, key, replace(artifact, sha256="a" * 64), encrypted
    else:
        prepared = context, key, artifact, encrypted[:-1]
    with pytest.raises(BackupRestoreError):
        execute(prepared, target)
    assert target.inspections == target.writes == 0


@pytest.mark.parametrize("failure", ["source", "protected", "persistent", "not_empty", "not_atomic"])
def test_unsafe_target_receives_no_write(prepared, failure):
    target = Target()
    changes = {
        "source": {"instance_id": prepared[0].instance_id},
        "protected": {"environment": "production"},
        "persistent": {"disposable": False},
        "not_empty": {"empty": False},
        "not_atomic": {"atomic": False},
    }
    target.state = replace(target.state, **changes[failure])
    with pytest.raises(BackupRestoreError):
        execute(prepared, target)
    assert target.writes == 0


def test_failed_verification_does_not_produce_receipt(prepared):
    target = Target()
    target.schema_matches = False
    with pytest.raises(BackupRestoreError):
        execute(prepared, target)
    assert target.writes == 1


def test_adapter_error_is_sanitized(prepared):
    class Broken(Target):
        def restore(self, dump):
            raise RuntimeError("DATABASE_URL=private;token=never-log")

    with pytest.raises(BackupRestoreError) as caught:
        execute(prepared, Broken())
    assert "private" not in str(caught.value)
    assert "never-log" not in str(caught.value)


def test_oversized_receipt_is_refused_before_read(prepared):
    context, key, artifact, _ = prepared

    class Forbidden:
        def __getattr__(self, name):
            pytest.fail("Recibo fora do limite iniciou IO")

    with pytest.raises(BackupRestoreError):
        restore_global(Forbidden(), key=key, expected=context,
                       artifact=replace(artifact, size_bytes=10**15), target=Target(),
                       at=datetime.now(UTC))
