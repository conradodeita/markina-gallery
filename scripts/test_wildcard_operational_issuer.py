"""Contrato do wrapper sem invocar ACME/DNS ou processo Certbot."""

import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wildcard_operational_issuer import (
    EXECUTABLE,
    SERVER,
    CertbotIssuer,
    IssuanceError,
)


@unittest.skipUnless(os.name == "posix", "Exige POSIX para lock e permissões")
class IssuerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        for name in ("state", "runtime", "credential"):
            (self.base / name).mkdir(mode=0o700)
        self.credential = self.base / "credential/cloudflare.ini"
        self.credential.write_text("dns_cloudflare_api_token = synthetic-token\n")
        self.credential.chmod(0o600)
        self.calls = []

    def issuer(self, runner=None):
        return CertbotIssuer(
            self.base / "state",
            self.base / "runtime",
            "a" * 32,
            runner=runner
            or (lambda command, **kwargs: self.calls.append((command, kwargs))),
        )

    def test_arguments_and_environment_are_fixed_and_work_is_removed(self):
        for _ in range(2):
            result = self.issuer().issue(self.credential)
            self.assertEqual(result, self.base / "state/live/pyp-tenant-wildcard")
        command, options = self.calls[-1]
        self.assertEqual(command[0], EXECUTABLE)
        self.assertEqual(command[command.index("--server") + 1], SERVER)
        self.assertEqual(command[command.index("-d") + 1], "*.pickyourpic.com.br")
        self.assertNotIn("synthetic-token", str(command) + str(options))
        self.assertNotIn("--agree-tos", command)
        self.assertNotIn("--register-unsafely-without-email", command)
        self.assertEqual(options["env"], {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
        self.assertEqual(options["timeout"], 300)
        self.assertEqual(options["umask"], 0o077)
        self.assertIs(options["stdout"], subprocess.DEVNULL)
        self.assertIs(options["stderr"], subprocess.DEVNULL)
        self.assertEqual(list((self.base / "runtime").iterdir()), [])

    def test_failure_and_timeout_are_sanitized_and_remove_work(self):
        for error in (
            subprocess.TimeoutExpired("synthetic-token", 300),
            subprocess.CalledProcessError(1, "synthetic-token"),
            OSError("synthetic-token"),
        ):

            def fail(*args, error=error, **kwargs):
                raise error

            with self.assertRaisesRegex(IssuanceError, "^issuance_failed$"):
                self.issuer(fail).issue(self.credential)
            self.assertEqual(list((self.base / "runtime").iterdir()), [])

    def test_concurrent_issue_is_rejected(self):
        entered, release = threading.Event(), threading.Event()
        errors = []

        def wait(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise TimeoutError()

        def issue():
            try:
                self.issuer(wait).issue(self.credential)
            except IssuanceError as error:
                errors.append(str(error))

        worker = threading.Thread(target=issue)
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            with self.assertRaisesRegex(IssuanceError, "^issuance_failed$"):
                self.issuer().issue(self.credential)
        finally:
            release.set()
            worker.join(5)
        self.assertEqual(errors, [])
        self.assertEqual(self.calls, [])

    def test_unsafe_account_file_and_config_are_rejected_before_execution(self):
        with self.assertRaises(IssuanceError):
            CertbotIssuer(self.base / "state", self.base / "runtime", "../free-choice")
        self.credential.write_text(
            "dns_cloudflare_api_token = synthetic-token\nunsafe = yes\n"
        )
        with self.assertRaises(IssuanceError):
            self.issuer().issue(self.credential)

    def test_core_dump_policy_blocks_before_creating_work_or_execution(self):
        with (
            patch("resource.getrlimit", return_value=(1, 1)),
            self.assertRaisesRegex(IssuanceError, "^issuer_core_dump_policy_invalid$"),
        ):
            self.issuer().issue(self.credential)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.calls, [])
        self.credential.unlink()
        self.credential.symlink_to(self.base / "outside")
        with self.assertRaises(IssuanceError):
            self.issuer().issue(self.credential)


if __name__ == "__main__":
    unittest.main()
