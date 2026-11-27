from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_worker_security_journal import DurableJournal, JournalError


class DurableJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        if os.name == "posix":
            self.root.chmod(0o700)
        self.journal = DurableJournal(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def begin(self):
        self.journal.begin(
            fingerprint="a" * 64,
            previous_image_id="sha256:" + "1" * 64,
            candidate_image_id="sha256:" + "2" * 64,
        )

    def test_begin_and_atomic_phase_update(self):
        self.begin()
        self.assertEqual(self.journal.read()["phase"], "approved")
        self.journal.write({"format": 1, "phase": "maintenance"})
        self.assertEqual(self.journal.read(), {"format": 1, "phase": "maintenance"})
        self.assertFalse(self.journal.temp_path.exists())
        if os.name == "posix":
            self.assertEqual(self.journal.path.stat().st_mode & 0o777, 0o600)

    def test_existing_journal_blocks_new_run(self):
        self.begin()
        with self.assertRaisesRegex(JournalError, "previous_journal_requires_recovery"):
            self.begin()

    def test_interrupted_temp_file_is_not_overwritten(self):
        self.journal.temp_path.write_text("partial", encoding="utf-8")
        with self.assertRaisesRegex(JournalError, "previous_journal_requires_recovery"):
            self.begin()
        self.assertEqual(self.journal.temp_path.read_text(encoding="utf-8"), "partial")

    def test_finish_requires_complete_phase(self):
        self.begin()
        with self.assertRaisesRegex(JournalError, "journal_not_complete"):
            self.journal.finish()
        self.assertTrue(self.journal.path.exists())

    def test_finish_removes_only_completed_inflight_journal(self):
        self.begin()
        self.journal.write({"format": 1, "phase": "complete"})
        self.journal.finish()
        self.assertFalse(self.journal.path.exists())

    def test_unsafe_directory_permissions_block_on_posix(self):
        if os.name != "posix":
            self.skipTest("permissions POSIX")
        self.root.chmod(0o777)
        with self.assertRaisesRegex(
            JournalError, "journal_state_directory_permissions_unsafe"
        ):
            self.begin()

    def test_privileged_operator_can_validate_private_directory_of_deploy_owner(self):
        if os.name != "posix":
            self.skipTest("permissions POSIX")
        with patch("os.geteuid", return_value=0):
            self.journal._check_directory()
        with (
            patch("os.geteuid", return_value=self.root.stat().st_uid + 1),
            self.assertRaisesRegex(
                JournalError, "journal_state_directory_owner_mismatch"
            ),
        ):
            self.journal._check_directory()
        self.root.chmod(0o770)
        with (
            patch("os.geteuid", return_value=0),
            self.assertRaisesRegex(
                JournalError, "journal_state_directory_permissions_unsafe"
            ),
        ):
            self.journal._check_directory()


if __name__ == "__main__":
    unittest.main()
