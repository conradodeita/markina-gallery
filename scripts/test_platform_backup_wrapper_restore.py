"""Contract tests for the protected platform backup wrapper restore."""

from __future__ import annotations

import contextlib
import hashlib
import io
import os
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

import platform_backup_wrapper_restore as restore

SUPPORT_SHA = "a" * 40
TARGET_SUPPORT_SHA = "c" * 40
APPROVAL_FINGERPRINT = "b" * 64
STAMP = "20261122T120000Z"
ACTIVE_CONTENT = b"#!/bin/sh\n# active wrapper fixture\nexit 1\n"
TARGET_CONTENT = b"#!/bin/sh\n# target wrapper fixture\nexit 1\n"


class RestoreWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="wrapper-restore-test-")
        self.root = Path(self.temporary.name)
        self.backup_dir = self.root / "backups"
        self.wrapper_dir = self.root / "sbin"
        self.backup_dir.mkdir(mode=0o700)
        self.wrapper_dir.mkdir(mode=0o700)
        self.wrapper = self.wrapper_dir / "markina-gallery-preflight-ssh-wrapper"
        self.wrapper.write_bytes(ACTIVE_CONTENT)
        self.wrapper.chmod(0o755)
        self.target_name = f"preflight-ssh-wrapper-{STAMP}-platform-backup-{TARGET_SUPPORT_SHA[:12]}"
        self.target_backup = self.backup_dir / self.target_name
        self.target_backup.write_bytes(TARGET_CONTENT)
        self.target_backup.chmod(0o600)
        self.paths = restore.RestorePaths(
            backup_dir=self.backup_dir,
            wrapper=self.wrapper,
            project_root=self.root,
        )
        self.expected_uid = os.getuid() if hasattr(os, "getuid") else None
        self.expected_gid = os.getgid() if hasattr(os, "getgid") else None
        self.strict_mode = os.name != "nt"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def sha(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def validator(
        self,
        *,
        reject_restored_target: bool = False,
        reject_compensated_active: bool = False,
    ) -> Callable[..., None]:
        state = {"target_failed": False, "active_checks": 0}

        def validate(
            path: Path,
            expected_sha256: str,
            *,
            expected_uid: int | None,
            expected_gid: int | None,
            strict_mode: bool,
            expected_mode: int = 0o755,
        ) -> None:
            metadata = path.lstat()
            self.assertFalse(path.is_symlink())
            self.assertTrue(path.is_file())
            self.assertEqual(metadata.st_nlink, 1)
            if expected_uid is not None:
                self.assertEqual(metadata.st_uid, expected_uid)
            if expected_gid is not None:
                self.assertEqual(metadata.st_gid, expected_gid)
            if strict_mode:
                self.assertEqual(metadata.st_mode & 0o777, expected_mode)
            content = path.read_bytes()
            self.assertEqual(self.sha(content), expected_sha256)
            if path == self.wrapper and content == ACTIVE_CONTENT:
                state["active_checks"] += 1
                if reject_compensated_active and state["active_checks"] > 1:
                    raise restore.RestoreFailure("wrapper_restore_wrapper_validation_failed")
            if path == self.wrapper and content == TARGET_CONTENT and reject_restored_target:
                state["target_failed"] = True
                raise restore.RestoreFailure("wrapper_restore_wrapper_validation_failed")

        return validate

    def run_restore(
        self,
        *,
        validator: Callable[..., None] | None = None,
        snapshots: list[str] | None = None,
        atomic_replace: Callable[[Path, Path], None] = os.replace,
    ) -> tuple[str, str]:
        snapshot_values = snapshots if snapshots is not None else ["stable", "stable", "stable"]
        calls = {"count": 0}

        def snapshot(_: restore.RestorePaths) -> str:
            index = min(calls["count"], len(snapshot_values) - 1)
            calls["count"] += 1
            return snapshot_values[index]

        return restore.restore_wrapper(
            self.sha(TARGET_CONTENT),
            SUPPORT_SHA,
            APPROVAL_FINGERPRINT,
            paths=self.paths,
            expected_uid=self.expected_uid,
            expected_gid=self.expected_gid,
            strict_mode=self.strict_mode,
            fingerprint_probe=lambda _paths, _sha: APPROVAL_FINGERPRINT,
            container_snapshot=snapshot,
            wrapper_validator=validator or self.validator(),
            atomic_replace=atomic_replace,
            utc_stamp=STAMP,
        )

    def test_restores_unique_root_only_copy_and_preserves_active_version(self) -> None:
        restored_sha, preserved_sha = self.run_restore()

        self.assertEqual(restored_sha, self.sha(TARGET_CONTENT))
        self.assertEqual(preserved_sha, self.sha(ACTIVE_CONTENT))
        self.assertEqual(self.wrapper.read_bytes(), TARGET_CONTENT)
        preserved = self.backup_dir / f"preflight-ssh-wrapper-{STAMP}-platform-backup-{SUPPORT_SHA[:12]}"
        self.assertEqual(preserved.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(preserved.stat().st_nlink, 1)
        self.assertFalse(list(self.wrapper_dir.glob("*.restore.new")))

    def test_missing_copy_aborts_before_preserving_or_swapping(self) -> None:
        self.target_backup.unlink()

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore()

        self.assertEqual(error.exception.code, "wrapper_restore_copy_not_found")
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(list(self.backup_dir.iterdir()), [])

    def test_ambiguous_matching_copies_abort_before_mutation(self) -> None:
        duplicate = self.backup_dir / f"preflight-ssh-wrapper-20261122T120001Z-platform-backup-{TARGET_SUPPORT_SHA[:12]}"
        duplicate.write_bytes(TARGET_CONTENT)
        duplicate.chmod(0o600)

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore()

        self.assertEqual(error.exception.code, "wrapper_restore_copy_ambiguous")
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(len(list(self.backup_dir.iterdir())), 2)

    def test_tampered_copy_does_not_match_receipt_hash(self) -> None:
        self.target_backup.write_bytes(b"tampered")
        self.target_backup.chmod(0o600)

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore()

        self.assertEqual(error.exception.code, "wrapper_restore_copy_not_found")
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)

    def test_unsafe_copy_metadata_aborts_before_mutation(self) -> None:
        if not self.strict_mode:
            self.skipTest("Windows não oferece semântica POSIX para modo 0600")
        self.target_backup.chmod(0o644)

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore()

        self.assertEqual(error.exception.code, "wrapper_restore_copy_metadata_invalid")
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)

    def test_fingerprint_divergence_aborts_before_mutation(self) -> None:
        with self.assertRaises(restore.RestoreFailure) as error:
            restore.restore_wrapper(
                self.sha(TARGET_CONTENT),
                SUPPORT_SHA,
                APPROVAL_FINGERPRINT,
                paths=self.paths,
                expected_uid=self.expected_uid,
                expected_gid=self.expected_gid,
                strict_mode=self.strict_mode,
                fingerprint_probe=lambda _paths, _sha: "c" * 64,
                container_snapshot=lambda _paths: "stable",
                wrapper_validator=self.validator(),
                utc_stamp=STAMP,
            )

        self.assertEqual(error.exception.code, "wrapper_restore_fingerprint_mismatch")
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(len(list(self.backup_dir.iterdir())), 1)

    def test_post_swap_validation_failure_compensates_once_and_preserves_versions(self) -> None:
        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore(validator=self.validator(reject_restored_target=True))

        self.assertEqual(error.exception.code, "wrapper_restore_validation_failed_recovered")
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(len(list(self.backup_dir.iterdir())), 2)
        self.assertFalse(list(self.wrapper_dir.glob("*.restore.rollback")))

    def test_missing_target_after_atomic_swap_compensates_to_active(self) -> None:
        replace_calls = {"count": 0}

        def remove_after_swap(source: Path, target: Path) -> None:
            replace_calls["count"] += 1
            os.replace(source, target)
            if replace_calls["count"] == 1:
                target.unlink()

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore(atomic_replace=remove_after_swap)

        self.assertEqual(error.exception.code, "wrapper_restore_validation_failed_recovered")
        self.assertEqual(replace_calls["count"], 2)
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(len(list(self.backup_dir.iterdir())), 2)
        self.assertFalse(list(self.wrapper_dir.glob("*.restore.rollback")))

    def test_unexpected_target_hash_after_atomic_swap_compensates(self) -> None:
        replace_calls = {"count": 0}

        def replace_with_unexpected_hash(source: Path, target: Path) -> None:
            replace_calls["count"] += 1
            os.replace(source, target)
            if replace_calls["count"] == 1:
                target.write_bytes(b"unexpected forced command")
                target.chmod(0o755)

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore(atomic_replace=replace_with_unexpected_hash)

        self.assertEqual(error.exception.code, "wrapper_restore_validation_failed_recovered")
        self.assertEqual(replace_calls["count"], 2)
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(len(list(self.backup_dir.iterdir())), 2)

    def test_unexpected_target_metadata_after_atomic_swap_compensates(self) -> None:
        if not self.strict_mode:
            self.skipTest("Windows não oferece semântica POSIX para modos de arquivo")
        replace_calls = {"count": 0}

        def replace_with_unexpected_mode(source: Path, target: Path) -> None:
            replace_calls["count"] += 1
            os.replace(source, target)
            if replace_calls["count"] == 1:
                target.chmod(0o744)

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore(atomic_replace=replace_with_unexpected_mode)

        self.assertEqual(error.exception.code, "wrapper_restore_validation_failed_recovered")
        self.assertEqual(replace_calls["count"], 2)
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(self.wrapper.stat().st_mode & 0o777, 0o755)

    def test_failed_compensation_after_missing_target_preserves_observed_state(self) -> None:
        replace_calls = {"count": 0}

        def fail_after_missing_target(source: Path, target: Path) -> None:
            replace_calls["count"] += 1
            if replace_calls["count"] == 1:
                os.replace(source, target)
                target.unlink()
                return
            raise OSError("synthetic compensation failure")

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore(atomic_replace=fail_after_missing_target)

        self.assertEqual(error.exception.code, "wrapper_restore_fallback_unverified")
        self.assertEqual(replace_calls["count"], 2)
        self.assertFalse(self.wrapper.exists())
        self.assertEqual(len(list(self.backup_dir.iterdir())), 2)
        self.assertEqual(len(list(self.wrapper_dir.glob("*.restore.rollback"))), 1)

    def test_failed_compensation_stops_and_preserves_staging_and_copies(self) -> None:
        replace_calls = {"count": 0}

        def fail_compensation(source: Path, target: Path) -> None:
            replace_calls["count"] += 1
            if replace_calls["count"] == 2:
                raise OSError("synthetic compensation failure")
            os.replace(source, target)

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore(
                validator=self.validator(reject_restored_target=True),
                atomic_replace=fail_compensation,
            )

        self.assertEqual(error.exception.code, "wrapper_restore_fallback_unverified")
        self.assertEqual(replace_calls["count"], 2)
        self.assertEqual(self.wrapper.read_bytes(), TARGET_CONTENT)
        self.assertEqual(len(list(self.backup_dir.iterdir())), 2)
        self.assertEqual(len(list(self.wrapper_dir.glob("*.restore.rollback"))), 1)

    def test_unverifiable_container_invariance_fails_closed_after_compensation(self) -> None:
        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore(
                snapshots=["before", "after", "after"],
                validator=self.validator(),
            )

        self.assertEqual(error.exception.code, "wrapper_restore_fallback_unverified")
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(len(list(self.backup_dir.iterdir())), 2)

    def test_preexisting_staging_is_preserved_and_blocks_before_mutation(self) -> None:
        restore_key = f"{SUPPORT_SHA}.{self.sha(TARGET_CONTENT)[:12]}"
        staging = self.wrapper_dir / f".{self.wrapper.name}.{restore_key}.restore.new"
        staging.write_bytes(b"preserve prior recovery evidence")
        prior_staging = staging.read_bytes()

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore()

        self.assertEqual(error.exception.code, "wrapper_restore_staging_exists")
        self.assertEqual(staging.read_bytes(), prior_staging)
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(list(self.backup_dir.iterdir()), [self.target_backup])

    def test_preexisting_compensation_staging_is_preserved_and_blocks(self) -> None:
        restore_key = f"{SUPPORT_SHA}.{self.sha(TARGET_CONTENT)[:12]}"
        staging = self.wrapper_dir / f".{self.wrapper.name}.{restore_key}.restore.rollback"
        staging.write_bytes(b"preserve prior compensation evidence")
        prior_staging = staging.read_bytes()

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore()

        self.assertEqual(error.exception.code, "wrapper_restore_staging_exists")
        self.assertEqual(staging.read_bytes(), prior_staging)
        self.assertEqual(self.wrapper.read_bytes(), ACTIVE_CONTENT)
        self.assertEqual(list(self.backup_dir.iterdir()), [self.target_backup])

    def test_active_target_is_rejected_without_a_second_swap(self) -> None:
        self.wrapper.write_bytes(TARGET_CONTENT)
        self.wrapper.chmod(0o755)

        with self.assertRaises(restore.RestoreFailure) as error:
            self.run_restore()

        self.assertEqual(error.exception.code, "wrapper_restore_already_active")
        self.assertEqual(self.wrapper.read_bytes(), TARGET_CONTENT)
        self.assertEqual(len(list(self.backup_dir.iterdir())), 1)

    def test_cli_exposes_no_arbitrary_backup_path(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
            restore._main([
                "--support-sha", SUPPORT_SHA,
                "--receipt-backup-sha256", self.sha(TARGET_CONTENT),
                "--approval-fingerprint", APPROVAL_FINGERPRINT,
                "--backup-path", str(self.target_backup),
            ])

        self.assertNotEqual(error.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
