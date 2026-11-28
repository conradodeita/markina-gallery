from __future__ import annotations

import io
import json
import os
import subprocess
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app import global_postgresql_backup as backup


class _CaptureInput:
    def __init__(self) -> None:
        self.parts: list[bytes] = []
        self.closed = False

    def write(self, value: bytes) -> int:
        self.parts.append(value)
        return len(value)

    def close(self) -> None:
        self.closed = True

    def getvalue(self) -> bytes:
        return b"".join(self.parts)


class _FakeProcess:
    def __init__(
        self,
        *,
        stdout: bytes = b"",
        returncode: int = 0,
        has_stdin: bool = False,
    ) -> None:
        self.stdout = io.BytesIO(stdout)
        self.stdin = _CaptureInput() if has_stdin else None
        self.returncode = returncode
        self.terminated = False

    def wait(self) -> int:
        return self.returncode

    def poll(self) -> int | None:
        return self.returncode if not self.terminated else -15

    def terminate(self) -> None:
        self.terminated = True


def _make_config(tmp_path: Path) -> backup.GlobalPostgreSQLBackupConfig:
    repository_root = tmp_path / "checkout"
    repository_root.mkdir()
    private = tmp_path / "private"
    private.mkdir()
    password = private / "restic-password"
    rclone = private / "rclone.conf"
    password.write_text("fixture-only", encoding="utf-8")
    rclone.write_text("[local]\ntype = local\n", encoding="utf-8")
    if os.name == "posix":
        password.chmod(0o600)
        rclone.chmod(0o600)
    return backup.GlobalPostgreSQLBackupConfig(
        repository="rclone:local:synthetic-global-backup",
        restic_password_file=password,
        rclone_config_file=rclone,
        repository_root=repository_root,
    )


def test_rejects_non_rclone_or_traversal_repository(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    for repository in (
        "local:C:/outside",
        "rclone:local:/absolute/path",
        "rclone:local:synthetic/../outside",
        "rclone:local:synthetic//backup",
    ):
        with pytest.raises(backup.GlobalPostgreSQLBackupError) as error:
            backup._validate_config(
                config.__class__(**{**config.__dict__, "repository": repository})
            )
        assert str(error.value) == "configuration_invalid"


def test_rejects_secret_files_inside_checkout_or_with_broad_posix_mode(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)
    internal = config.repository_root / "secret"
    internal.write_text("fixture-only", encoding="utf-8")
    if os.name == "posix":
        internal.chmod(0o600)
    with pytest.raises(backup.GlobalPostgreSQLBackupError) as error:
        backup._resolved_external_file(internal, config.repository_root)
    assert str(error.value) == "configuration_invalid"

    if os.name == "posix":
        config.rclone_config_file.chmod(0o644)
        with pytest.raises(backup.GlobalPostgreSQLBackupError) as error:
            backup._validate_config(config)
        assert str(error.value) == "configuration_invalid"


def test_connection_url_omits_password_and_rejects_unknown_query_parameters() -> None:
    database_url, libpq_url = backup._database_url_without_password(
        "postgresql+psycopg://fixture_user:fixture-only@db.local/testdb?sslmode=require"
    )
    assert database_url.password == "fixture-only"
    assert libpq_url.drivername == "postgresql"
    assert "fixture-only" not in libpq_url.render_as_string(hide_password=False)

    with pytest.raises(backup.GlobalPostgreSQLBackupError) as error:
        backup._database_url_without_password(
            "postgresql://fixture_user:fixture-only@db.local/testdb?password=leak"
        )
    assert str(error.value) == "database_configuration_invalid"


def test_child_environment_preserves_platform_paths_but_omits_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", "C:/synthetic/app-data")
    monkeypatch.setenv("RESTIC_PASSWORD", "fixture-only")
    child_environment = backup._base_environment()
    assert child_environment["LOCALAPPDATA"] == "C:/synthetic/app-data"
    assert "RESTIC_PASSWORD" not in child_environment


def test_validates_exact_pinned_tool_versions() -> None:
    config = backup.GlobalPostgreSQLBackupConfig(
        repository="rclone:local:synthetic-global-backup",
        restic_password_file=Path("password"),
        rclone_config_file=Path("rclone.conf"),
        repository_root=Path("."),
    )
    outputs = {
        ("pg_dump", "--version"): "pg_dump (PostgreSQL) 17.11",
        ("pg_restore", "--version"): "pg_restore (PostgreSQL) 17.11",
        ("restic", "version"): "restic 0.20.0 compiled with go1.24.1",
        ("rclone", "version"): "rclone v1.76.0",
    }

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        executable = Path(args[0]).name
        key = (executable, *args[1:])
        return subprocess.CompletedProcess(args, 0, outputs[key], "")

    with (
        patch.object(backup.shutil, "which", side_effect=lambda value: value),
        patch.object(backup.subprocess, "run", side_effect=fake_run),
    ):
        backup._validate_tool_versions(config)


def test_tool_version_error_is_sanitized() -> None:
    config = backup.GlobalPostgreSQLBackupConfig(
        repository="rclone:local:synthetic-global-backup",
        restic_password_file=Path("password"),
        rclone_config_file=Path("rclone.conf"),
        repository_root=Path("."),
    )
    failure = subprocess.CalledProcessError(1, "restic", stderr="fixture-only leaked text")
    with (
        patch.object(backup.shutil, "which", return_value="restic.exe"),
        patch.object(backup.subprocess, "run", side_effect=failure),
        pytest.raises(backup.GlobalPostgreSQLBackupError) as error,
    ):
        backup._validate_tool_versions(config)
    assert str(error.value) == "tool_version_unverified"
    assert "fixture-only" not in str(error.value)


def test_password_file_uses_owner_only_permissions_and_is_removed() -> None:
    if os.name != "posix":
        pytest.skip("permissões POSIX do runtime Linux não estão disponíveis no Windows")
    database_url, _ = backup._database_url_without_password(
        "postgresql://fixture_user:fixture-only@db.local/testdb"
    )
    with backup._temporary_pgpass(database_url) as path:
        assert path is not None
        assert path.exists()
        assert path.stat().st_mode & 0o077 == 0
    assert path is not None and not path.exists()


def test_pgpass_keeps_host_and_port_wildcards_and_escapes_delimiters() -> None:
    database_url, _ = backup._database_url_without_password(
        "postgresql://fixture_user:fixture-only@db.local/testdb"
    )
    assert backup._pgpass_line(database_url) == b"db.local:*:testdb:fixture_user:fixture-only"
    assert backup._pgpass_escape("value:*\\tail") == "value\\:*\\\\tail"


def test_pgpass_rejects_line_breaks_in_database_credentials() -> None:
    database_url, _ = backup._database_url_without_password(
        "postgresql://fixture_user:line%0Abreak@db.local/testdb"
    )
    with pytest.raises(backup.GlobalPostgreSQLBackupError) as error:
        backup._pgpass_line(database_url)
    assert str(error.value) == "database_configuration_invalid"


@pytest.mark.parametrize("stdout", [b"[]\n", b"null\n", b'"summary"\n'])
def test_snapshot_id_rejects_non_object_json_sanitized(stdout: bytes) -> None:
    with pytest.raises(backup.GlobalPostgreSQLBackupError) as error:
        backup._snapshot_id(stdout)
    assert str(error.value) == "snapshot_create_failed"


def test_backup_streams_dump_and_checks_decrypted_readback(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    archive = b"synthetic custom PostgreSQL archive"
    snapshot = b'{"message_type":"summary","snapshot_id":"abcdef0123456789"}\n'
    dump_process = _FakeProcess(stdout=archive)
    backup_process = _FakeProcess(stdout=snapshot, has_stdin=True)
    readback_process = _FakeProcess(stdout=archive)
    restore_process = _FakeProcess(has_stdin=True)
    processes = [backup_process, dump_process, readback_process, restore_process]
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_start(args: list[str], **kwargs: object) -> _FakeProcess:
        calls.append((args, kwargs))
        return processes.pop(0)

    database_url = "postgresql+psycopg://fixture_user:fixture-only@db.local/testdb?sslmode=require"
    with (
        patch.object(backup, "_validate_tool_versions"),
        patch.object(backup, "_temporary_pgpass", return_value=nullcontext(None)),
        patch.object(backup, "_start", side_effect=fake_start),
    ):
        receipt = backup.create_global_postgresql_backup(database_url, config)

    assert receipt.snapshot_id == "abcdef0123456789"
    assert receipt.dump_size_bytes == len(archive)
    assert receipt.verified is True
    assert backup_process.stdin is not None
    assert backup_process.stdin.closed
    assert backup_process.stdin.getvalue() == archive
    assert restore_process.stdin is not None
    assert restore_process.stdin.getvalue() == archive

    restic_args, restic_kwargs = calls[0]
    pg_dump_args, pg_dump_kwargs = calls[1]
    assert "fixture-only" not in " ".join(pg_dump_args)
    assert "--format=custom" in pg_dump_args
    assert "PGPASSFILE" not in pg_dump_kwargs["env"]

    assert restic_args[restic_args.index("-r") + 1] == config.repository
    assert "--stdin" in restic_args
    assert "--stdin-filename" in restic_args
    assert "--tag" in restic_args
    restic_env = restic_kwargs["env"]
    assert restic_env["RESTIC_PASSWORD_FILE"] == str(config.restic_password_file)
    assert restic_env["RCLONE_CONFIG"] == str(config.rclone_config_file)
    assert "DATABASE_URL" not in restic_env
    assert "PGPASSFILE" not in restic_env


def test_readback_mismatch_is_not_reported_as_verified(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    dump_process = _FakeProcess(stdout=b"original archive")
    backup_process = _FakeProcess(
        stdout=b'{"message_type":"summary","snapshot_id":"abcdef0123456789"}\n',
        has_stdin=True,
    )
    readback_process = _FakeProcess(stdout=b"different archive")
    restore_process = _FakeProcess(has_stdin=True)
    processes = [backup_process, dump_process, readback_process, restore_process]

    with (
        patch.object(backup, "_validate_tool_versions"),
        patch.object(backup, "_start", side_effect=processes),
        pytest.raises(backup.GlobalPostgreSQLBackupError) as error,
    ):
        backup.create_global_postgresql_backup("postgresql://fixture_user@db.local/testdb", config)

    assert str(error.value) == "snapshot_readback_failed"


def test_backup_failure_returns_only_static_sanitized_code(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    dump_process = _FakeProcess(stdout=b"partial dump", returncode=7)
    backup_process = _FakeProcess(stdout=b"", has_stdin=True)
    with (
        patch.object(backup, "_validate_tool_versions"),
        patch.object(
            backup,
            "_start",
            side_effect=[backup_process, dump_process],
        ),
        pytest.raises(backup.GlobalPostgreSQLBackupError) as error,
    ):
        backup.create_global_postgresql_backup("postgresql://fixture_user@db.local/testdb", config)
    assert str(error.value) == "pg_dump_failed"


def _snapshot(snapshot_id: str, *, time: str, tags: list[str] | None = None) -> dict[str, object]:
    return {
        "id": snapshot_id,
        "time": time,
        "tags": tags if tags is not None else [backup.SNAPSHOT_TAG],
    }


def test_retention_forgets_only_older_global_ids_then_prunes_and_verifies(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)
    old = "1" * 64
    current = "2" * 64
    snapshots = [
        json.dumps(
            [
                _snapshot(old, time="2026-11-26T10:00:00Z"),
                _snapshot(current, time="2026-11-27T10:00:00Z"),
            ]
        ),
        json.dumps([_snapshot(current, time="2026-11-27T10:00:00Z")]),
        json.dumps([_snapshot(current, time="2026-11-27T10:00:00Z")]),
    ]
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(args)
        if "snapshots" in args:
            return SimpleNamespace(returncode=0, stdout=snapshots.pop(0))
        return SimpleNamespace(returncode=0, stdout="")

    with (
        patch.object(backup, "_validate_restic_rclone_versions"),
        patch.object(backup.subprocess, "run", side_effect=fake_run),
    ):
        receipt = backup.apply_global_postgresql_backup_retention(config, current[:16])

    assert receipt.snapshot_id == current
    assert receipt.removed_snapshot_count == 1
    assert [call[3] for call in calls] == ["snapshots", "forget", "snapshots", "prune", "snapshots"]
    forget_call = calls[1]
    assert old in forget_call
    assert current not in forget_call
    assert snapshots == []


@pytest.mark.parametrize(
    ("inventory", "expected_code"),
    [
        (
            [
                _snapshot("1" * 64, time="2026-11-26T10:00:00Z", tags=["media-archive"]),
                _snapshot("2" * 64, time="2026-11-27T10:00:00Z"),
            ],
            "retention_scope_ambiguous",
        ),
        (
            [
                _snapshot("1" * 64, time="2026-11-28T10:00:00Z"),
                _snapshot("2" * 64, time="2026-11-27T10:00:00Z"),
            ],
            "retention_target_not_latest",
        ),
        (
            [{"id": "truncated", "time": "bad", "tags": [backup.SNAPSHOT_TAG]}],
            "retention_inventory_invalid",
        ),
    ],
)
def test_retention_rejects_ambiguous_inventory_before_mutation(
    tmp_path: Path,
    inventory: list[dict[str, object]],
    expected_code: str,
) -> None:
    config = _make_config(tmp_path)
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=json.dumps(inventory))

    with (
        patch.object(backup, "_validate_restic_rclone_versions"),
        patch.object(backup.subprocess, "run", side_effect=fake_run),
        pytest.raises(backup.GlobalPostgreSQLBackupError) as error,
    ):
        backup.apply_global_postgresql_backup_retention(config, "2" * 16)

    assert str(error.value) == expected_code
    assert all("forget" not in call and "prune" not in call for call in calls)


def test_retention_failure_never_passes_current_snapshot_to_forget(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    old = "1" * 64
    current = "2" * 64
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(args)
        if "snapshots" in args:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    [
                        _snapshot(old, time="2026-11-26T10:00:00Z"),
                        _snapshot(current, time="2026-11-27T10:00:00Z"),
                    ]
                ),
            )
        return SimpleNamespace(returncode=1, stdout="")

    with (
        patch.object(backup, "_validate_restic_rclone_versions"),
        patch.object(backup.subprocess, "run", side_effect=fake_run),
        pytest.raises(backup.GlobalPostgreSQLBackupError) as error,
    ):
        backup.apply_global_postgresql_backup_retention(config, current)

    assert str(error.value) == "retention_forget_failed"
    assert old in calls[1]
    assert current not in calls[1]


def test_retention_snapshot_presence_check_is_tagged_and_sanitized(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    current = "2" * 64
    result = SimpleNamespace(
        returncode=0,
        stdout=json.dumps([_snapshot(current, time="2026-11-27T10:00:00Z")]),
    )
    with (
        patch.object(backup, "_validate_restic_rclone_versions"),
        patch.object(backup.subprocess, "run", return_value=result),
    ):
        assert backup.global_postgresql_backup_snapshot_is_present(config, current[:16])
        assert not backup.global_postgresql_backup_snapshot_is_present(config, "3" * 16)
