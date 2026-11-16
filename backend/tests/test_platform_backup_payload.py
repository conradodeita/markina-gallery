"""Manifesto e membros são sintéticos e não acessam banco/serviços."""

import io
import json
import stat
import zipfile
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.platform_backup.archive import BackupArchiveError, BackupContext
from app.platform_backup.payload import BackupPayloadError, build_payload, open_payload


@pytest.fixture
def context():
    return BackupContext(uuid4(), uuid4(), "20261105_0106", "test", datetime.now(UTC))


def package(context):
    output = io.BytesIO()
    build_payload(io.BytesIO(b"PGDMP-synthetic-global-dump"), {"KEY": "synthetic-private"},
                  output, context=context)
    return output.getvalue()


def rewrite(value, mutate):
    with zipfile.ZipFile(io.BytesIO(value)) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        mutate(members, archive)
    return target.getvalue()


def test_payload_checks_all_members_and_closes_private_views(context):
    with open_payload(io.BytesIO(package(context)), expected=context) as payload:
        stream = payload.dump
        assert stream.read() == b"PGDMP-synthetic-global-dump"
        assert payload.configuration["KEY"] == "synthetic-private"
        assert "synthetic-private" not in repr(payload)
        with pytest.raises(TypeError):
            payload.configuration["KEY"] = "changed"
    assert stream.closed


@pytest.mark.parametrize("mutation", ["dump", "config", "manifest", "foreign_context"])
def test_payload_rejects_mismatch_before_yield(context, mutation):
    def change(members, archive):
        if mutation == "dump":
            members["database.dump"] += b"unexpected"
        elif mutation == "config":
            members["runtime-config.json"] = b'{"KEY":"changed"}'
        else:
            manifest = json.loads(members["manifest.json"])
            if mutation == "manifest":
                manifest["members"]["database.dump"]["sha256"] = "a" * 64
            else:
                manifest["context"]["instance_id"] = str(uuid4())
            members["manifest.json"] = json.dumps(manifest, sort_keys=True,
                                                  separators=(",", ":")).encode()
        for name, content in members.items():
            archive.writestr(name, content)

    modified = rewrite(package(context), change)
    with pytest.raises(BackupPayloadError), open_payload(io.BytesIO(modified), expected=context):
        pytest.fail("Manifesto inválido foi cedido ao restaurador")


@pytest.mark.parametrize("unsafe", ["path", "symlink", "duplicate", "compression"])
def test_payload_refuses_unexpected_zip_members(context, unsafe):
    def change(members, archive):
        for name, content in members.items():
            if unsafe == "symlink" and name == "database.dump":
                info = zipfile.ZipInfo(name)
                info.external_attr = (stat.S_IFLNK | 0o600) << 16
                archive.writestr(info, content)
            else:
                archive.writestr(name, content, compress_type=(
                    zipfile.ZIP_DEFLATED if unsafe == "compression" else zipfile.ZIP_STORED))
        if unsafe == "path":
            archive.writestr("../peer", b"must-not-extract")
        elif unsafe == "duplicate":
            with pytest.warns(UserWarning):
                archive.writestr("database.dump", b"duplicate")

    modified = rewrite(package(context), change)
    with pytest.raises(BackupPayloadError), open_payload(io.BytesIO(modified), expected=context):
        pytest.fail("Conteúdo não permitido foi aceito")


def test_payload_source_schema_and_runtime_gates(context, monkeypatch):
    with pytest.raises(BackupPayloadError):
        build_payload(io.BytesIO(b"plain SQL is not custom dump"), {}, io.BytesIO(), context=context)
    with pytest.raises(BackupPayloadError):
        build_payload(io.BytesIO(b"PGDMP-data"), {"../secret": "no"}, io.BytesIO(), context=context)
    expected = replace(context, schema_revision="20261103_0097")
    with pytest.raises(BackupPayloadError), open_payload(io.BytesIO(package(context)), expected=expected):
        pytest.fail("Schema errado foi aceito")
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(BackupArchiveError):
        build_payload(None, {}, None, context=context)
