from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts/production-app-artifact-ssh-wrapper.sh"
if os.name == "nt":
    _git_bash = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git/bin/bash.exe"
    BASH = str(_git_bash) if _git_bash.is_file() else shutil.which("bash")
else:
    BASH = shutil.which("bash")
TARGET_SHA = "a" * 40


@unittest.skipUnless(BASH and os.name != "nt", "requires a POSIX shell and filesystem")
class ArtifactSshWrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.spool = self.root / "spool"
        source = WRAPPER.read_text(encoding="utf-8")
        source = source.replace(
            'readonly MAX_BUNDLE_BYTES=4294967296',
            'readonly MAX_BUNDLE_BYTES=8',
        )
        spool_path = self.spool.as_posix()
        if os.name == "nt":
            spool_path = subprocess.check_output(
                [BASH, "-lc", 'cygpath -u "$1"', "bash", spool_path], text=True
            ).strip()
        source = source.replace(
            'readonly artifact_dir="/tmp/markina-gallery-app-artifacts-${UID}"',
            f'readonly artifact_dir="{spool_path}"',
        )
        self.script = self.root / "artifact-wrapper.sh"
        self.script.write_text(source, encoding="utf-8", newline="\n")

    def tearDown(self):
        self.temp.cleanup()

    def run_wrapper(self, data=b"", command=None, *args):
        env = os.environ.copy()
        env["SSH_ORIGINAL_COMMAND"] = command or (
            f"MARKINA_APP_ARTIFACT_UPLOAD_SHA={TARGET_SHA}_BUNDLE_SHA256="
            + hashlib.sha256(data).hexdigest()
        )
        return subprocess.run(
            [BASH, str(self.script), *args], input=data, capture_output=True,
            text=False, env=env, timeout=20, check=False,
        )

    def test_receives_only_digest_verified_bundle_and_replaces_atomically(self):
        # The test wrapper uses a small limit; keep this payload within it.
        payload = b"bundle"
        result = self.run_wrapper(payload)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        saved = self.spool / f"{TARGET_SHA}.bundle"
        self.assertEqual(saved.read_bytes(), payload)
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertIn(hashlib.sha256(payload).hexdigest().encode(), result.stdout)
        self.assertFalse(list(self.spool.glob("*.upload-*")))

    def test_rejects_hash_mismatch_without_replacing_existing_bundle(self):
        self.spool.mkdir()
        saved = self.spool / f"{TARGET_SHA}.bundle"
        saved.write_bytes(b"previous")
        result = self.run_wrapper(b"other", f"MARKINA_APP_ARTIFACT_UPLOAD_SHA={TARGET_SHA}_BUNDLE_SHA256={'0' * 64}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"SHA-256 do bundle diverge", result.stderr)
        self.assertEqual(saved.read_bytes(), b"previous")
        self.assertFalse(list(self.spool.glob(".*.upload-*")))

    def test_rejects_empty_or_oversize_bundle(self):
        empty = self.run_wrapper(b"")
        self.assertNotEqual(empty.returncode, 0)
        oversized = self.run_wrapper(b"123456789")
        self.assertNotEqual(oversized.returncode, 0)
        self.assertIn(b"limite", oversized.stderr)
        self.assertFalse((self.spool / f"{TARGET_SHA}.bundle").exists())

    def test_rejects_arbitrary_or_malformed_commands(self):
        for command in (
            "bash -i",
            f"MARKINA_APP_ARTIFACT_UPLOAD_SHA={TARGET_SHA}_BUNDLE_SHA256={'z' * 64}",
            f"MARKINA_APP_ARTIFACT_UPLOAD_SHA={TARGET_SHA}_BUNDLE_SHA256={'0' * 64}\nextra",
        ):
            with self.subTest(command=command):
                result = self.run_wrapper(b"payload", command)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.spool.exists())

    def test_rejects_extra_command_arguments(self):
        result = self.run_wrapper(b"payload", *["MARKINA_APP_ARTIFACT_UPLOAD_SHA=" + TARGET_SHA
                                                   + "_BUNDLE_SHA256=" + hashlib.sha256(b"payload").hexdigest()], "extra")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"argumentos adicionais", result.stderr)


if __name__ == "__main__":
    unittest.main()
