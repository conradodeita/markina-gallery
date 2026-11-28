"""Prova sintética local da política Restic de retenção PostgreSQL global."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import global_postgresql_backup as backup
from prove_global_postgresql_backup import (
    RUNNER_RCLONE_WINDOWS_ARCHIVE_SHA256,
    RUNNER_RESTIC_WINDOWS_ARCHIVE_SHA256,
    ProofFailure,
    _verify_release_archive_member,
)


def _run(
    arguments: list[str], *, env: dict[str, str], input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            arguments,
            input=input_bytes,
            stdin=None if input_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=180,
            env=env,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        raise ProofFailure("retention_proof_tool_failed") from None
    if result.returncode != 0:
        raise ProofFailure("retention_proof_tool_failed")
    return result


def _create_snapshot(
    *,
    restic: Path,
    repository: str,
    tag: str,
    payload: bytes,
    env: dict[str, str],
    timestamp: str | None = None,
) -> str:
    arguments = [
        str(restic),
        "-r",
        repository,
        "backup",
        "--json",
        "--stdin",
        "--stdin-filename",
        backup.ARCHIVE_FILENAME,
        "--tag",
        tag,
    ]
    if timestamp is not None:
        arguments.extend(("--time", timestamp))
    result = _run(arguments, env=env, input_bytes=payload)
    try:
        return backup._snapshot_id(result.stdout)
    except backup.GlobalPostgreSQLBackupError:
        raise ProofFailure("retention_proof_snapshot_receipt_invalid") from None


def _inventory(*, config, env: dict[str, str]) -> list[backup._ResticSnapshot]:
    try:
        return backup._restic_snapshot_inventory(config=config, restic_environment=env)
    except backup.GlobalPostgreSQLBackupError:
        raise ProofFailure("retention_proof_inventory_failed") from None


def run_proof(
    *,
    temp_root: Path,
    restic_executable: Path,
    rclone_executable: Path,
    restic_archive: Path,
    rclone_archive: Path,
) -> dict[str, object]:
    try:
        resolved_root = temp_root.expanduser().resolve()
        restic = restic_executable.expanduser().resolve(strict=True)
        rclone = rclone_executable.expanduser().resolve(strict=True)
        restic_zip = restic_archive.expanduser().resolve(strict=True)
        rclone_zip = rclone_archive.expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise ProofFailure("retention_proof_path_invalid") from None
    if resolved_root.is_relative_to(ROOT.resolve()):
        raise ProofFailure("retention_proof_temp_root_in_checkout")
    if any(not path.is_file() for path in (restic, rclone, restic_zip, rclone_zip)):
        raise ProofFailure("retention_proof_tool_unavailable")
    _verify_release_archive_member(
        restic_zip,
        restic,
        expected_archive_sha256=RUNNER_RESTIC_WINDOWS_ARCHIVE_SHA256,
    )
    _verify_release_archive_member(
        rclone_zip,
        rclone,
        expected_archive_sha256=RUNNER_RCLONE_WINDOWS_ARCHIVE_SHA256,
    )

    try:
        resolved_root.mkdir(parents=True, exist_ok=True)
        work = Path(
            tempfile.mkdtemp(prefix="pyp-global-backup-retention-", dir=resolved_root)
        ).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise ProofFailure("retention_proof_temp_create_failed") from None
    if not work.is_relative_to(resolved_root) or work == resolved_root:
        raise ProofFailure("retention_proof_temp_identity_invalid")

    previous_cwd = Path.cwd()
    synthetic_password = uuid.uuid4().hex + uuid.uuid4().hex
    try:
        password_file = work / "restic-password"
        rclone_config = work / "rclone.conf"
        password_file.write_text(synthetic_password, encoding="utf-8")
        rclone_config.write_text("[local]\ntype = local\n", encoding="utf-8")
        private_env = {
            **backup._base_environment(),
            "PATH": str(restic.parent) + os.pathsep + str(rclone.parent),
            "HOME": str(work),
            "USERPROFILE": str(work),
            "APPDATA": str(work),
            "LOCALAPPDATA": str(work),
            "TEMP": str(work),
            "TMP": str(work),
            "RCLONE_CONFIG": str(rclone_config),
            "RESTIC_PASSWORD_FILE": str(password_file),
        }
        config = backup.GlobalPostgreSQLBackupConfig(
            repository="rclone:local:global-repository",
            restic_password_file=password_file,
            rclone_config_file=rclone_config,
            repository_root=ROOT,
            restic_executable=str(restic),
            rclone_executable=str(rclone),
        )
        os.chdir(work)
        with patch.dict(os.environ, private_env, clear=True):
            backup._validate_restic_rclone_versions(config)
            _run([str(restic), "-r", config.repository, "init"], env=private_env)

            old_ids = [
                _create_snapshot(
                    restic=restic,
                    repository=config.repository,
                    tag=backup.SNAPSHOT_TAG,
                    payload=b"synthetic-global-postgresql-archive-old-1",
                    env=private_env,
                    timestamp="2001-01-01 00:00:00",
                ),
                _create_snapshot(
                    restic=restic,
                    repository=config.repository,
                    tag=backup.SNAPSHOT_TAG,
                    payload=b"synthetic-global-postgresql-archive-old-2",
                    env=private_env,
                    timestamp="2002-01-01 00:00:00",
                ),
            ]
            latest_id = _create_snapshot(
                restic=restic,
                repository=config.repository,
                tag=backup.SNAPSHOT_TAG,
                payload=b"synthetic-global-postgresql-archive-current",
                env=private_env,
            )
            retained = backup.apply_global_postgresql_backup_retention(
                config, latest_id
            )
            final_inventory = _inventory(config=config, env=private_env)
            if (
                retained.removed_snapshot_count != 2
                or retained.snapshot_id != latest_id
                or len(final_inventory) != 1
                or final_inventory[0].snapshot_id != latest_id
            ):
                raise ProofFailure("retention_proof_latest_snapshot_not_preserved")
            _run(
                [str(restic), "-r", config.repository, "check", "--read-data"],
                env=private_env,
            )

            foreign_config = backup.GlobalPostgreSQLBackupConfig(
                repository="rclone:local:foreign-repository",
                restic_password_file=password_file,
                rclone_config_file=rclone_config,
                repository_root=ROOT,
                restic_executable=str(restic),
                rclone_executable=str(rclone),
            )
            _run(
                [str(restic), "-r", foreign_config.repository, "init"], env=private_env
            )
            _create_snapshot(
                restic=restic,
                repository=foreign_config.repository,
                tag=backup.SNAPSHOT_TAG,
                payload=b"synthetic-global-postgresql-archive-old",
                env=private_env,
                timestamp="2001-01-01 00:00:00",
            )
            _create_snapshot(
                restic=restic,
                repository=foreign_config.repository,
                tag="media-archive",
                payload=b"synthetic-foreign-provider-archive",
                env=private_env,
                timestamp="2002-01-01 00:00:00",
            )
            foreign_latest_id = _create_snapshot(
                restic=restic,
                repository=foreign_config.repository,
                tag=backup.SNAPSHOT_TAG,
                payload=b"synthetic-global-postgresql-archive-current",
                env=private_env,
            )
            before = _inventory(config=foreign_config, env=private_env)
            try:
                backup.apply_global_postgresql_backup_retention(
                    foreign_config, foreign_latest_id
                )
            except backup.GlobalPostgreSQLBackupError as exc:
                if exc.code != "retention_scope_ambiguous":
                    raise ProofFailure(
                        "retention_proof_foreign_tag_error_invalid"
                    ) from None
            else:
                raise ProofFailure("retention_proof_foreign_tag_accepted")
            after = _inventory(config=foreign_config, env=private_env)
            if [item.snapshot_id for item in before] != [
                item.snapshot_id for item in after
            ]:
                raise ProofFailure("retention_proof_foreign_snapshots_changed")

        return {
            "status": "passed",
            "repository_kind": "rclone-local",
            "global_snapshots_before": len(old_ids) + 1,
            "global_snapshots_removed": retained.removed_snapshot_count,
            "global_snapshots_after": len(final_inventory),
            "current_snapshot_preserved": True,
            "foreign_tag_inventory_preserved": len(before) == len(after) == 3,
            "restic_check_read_data": "passed",
        }
    finally:
        os.chdir(previous_cwd)
        resolved_work = work.resolve(strict=True)
        if resolved_work.is_relative_to(
            resolved_root
        ) and resolved_work.name.startswith("pyp-global-backup-retention-"):
            shutil.rmtree(resolved_work)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-root", type=Path, required=True)
    parser.add_argument("--restic-executable", type=Path, required=True)
    parser.add_argument("--rclone-executable", type=Path, required=True)
    parser.add_argument("--restic-archive", type=Path, required=True)
    parser.add_argument("--rclone-archive", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_proof(
            temp_root=args.temp_root,
            restic_executable=args.restic_executable,
            rclone_executable=args.rclone_executable,
            restic_archive=args.restic_archive,
            rclone_archive=args.rclone_archive,
        )
    except ProofFailure as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
