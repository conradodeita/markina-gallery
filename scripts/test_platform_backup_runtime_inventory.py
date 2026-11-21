"""Read-only inventory contracts; all command results and filesystem inputs are synthetic."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import platform_backup_runtime_inventory as inventory


class InventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pyp-backup-inventory-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "etc").mkdir()
        (self.root / "etc/machine-id").write_text("abcdef0123456789abcdef0123456789\n", encoding="ascii")

    @staticmethod
    def _result(argv: list[str], stdout: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, returncode, stdout, "synthetic stderr")

    def _runner(self, *, timer_enabled: str = "unknown", third_party_image: str = "8"):
        def run(argv):
            if argv[0] == "/usr/bin/git" and argv[1] == "-C" and list(argv[-2:]) == ["rev-parse", "HEAD"]:
                return self._result(list(argv), "a" * 40 + "\n")
            if "container" in argv and "inspect" in argv:
                template = argv[argv.index("--format") + 1]
                if template == inventory.SHARED_CONTAINER_INSPECT:
                    shared = {
                        "c" * 64: "sha256:" + "a" * 64 + "|running|2026-11-20T00:00:00Z",
                        "e" * 64: "sha256:" + "b" * 64 + "|running|2026-11-20T00:00:00Z",
                        "d" * 64: "sha256:" + "f" * 64 + "|running|2026-11-20T00:00:00Z",
                        "9" * 64: "sha256:" + third_party_image * 64 + "|exited|2026-11-19T00:00:00Z",
                    }
                    return self._result(list(argv), "".join(f"{key}|{value}\n" for key, value in shared.items()))
                name = argv[-1]
                service = {"markina-gallery-api-1": "api", "markina-gallery-web-1": "web",
                           "markina-gallery-db-1": "db"}[name]
                health = "none" if service == "db" else "healthy"
                container_id = {"api": "c" * 64, "web": "e" * 64, "db": "d" * 64}[service]
                image_id = {"api": "a" * 64, "web": "b" * 64, "db": "f" * 64}[service]
                value = f"{container_id}|sha256:{image_id}|running|true|2026-11-20T00:00:00Z|markina-gallery|{service}|{health}\n"
                return self._result(list(argv), value)
            if "container" in argv and "ls" in argv:
                return self._result(list(argv), "\n".join(["c" * 64, "e" * 64, "d" * 64, "9" * 64]) + "\n")
            if " exec " in " ".join(argv):
                return self._result(list(argv), "20261113_0126\n")
            if argv[:3] == ["/usr/bin/df", "-P", "-k"]:
                return self._result(list(argv), "Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 100000 50000 50000 50% /var/lib\n")
            if argv[0] == "/usr/bin/systemctl":
                if argv[-1] == "pyp-platform-backup.timer":
                    return self._result(list(argv), f"not-found\n{timer_enabled}\ninactive\n")
                return self._result(list(argv), "not-found\nunknown\ninactive\n")
            raise AssertionError(f"unexpected command class: {argv[0]}")
        return run

    def test_inventory_is_sanitized_and_fingerprint_binds_host_and_runtime(self) -> None:
        result = inventory.collect_inventory(self._runner(), root=self.root)
        serialized = str(result)
        self.assertNotIn("abcdef0123456789abcdef0123456789", serialized)
        self.assertEqual(result["inventory"]["checkout_sha"], "a" * 40)
        self.assertEqual(result["inventory"]["database_schema"], "20261113_0126")
        self.assertEqual(result["inventory"]["containers"]["api"]["health"], "healthy")
        self.assertEqual(result["inventory"]["shared_containers"]["count"], 4)
        self.assertNotIn("9" * 64, serialized)
        self.assertEqual(len(result["fingerprint"]), 64)
        self.assertEqual(len(result["runtime_fingerprint"]), 64)
        self.assertTrue(inventory.install_preconditions(result["inventory"]))

    def test_fingerprint_changes_when_machine_identity_changes(self) -> None:
        first = inventory.collect_inventory(self._runner(), root=self.root)["fingerprint"]
        (self.root / "etc/machine-id").write_text("0123456789abcdef0123456789abcdef\n", encoding="ascii")
        second = inventory.collect_inventory(self._runner(), root=self.root)["fingerprint"]
        self.assertNotEqual(first, second)

    def test_enabled_backup_timer_blocks_install(self) -> None:
        result = inventory.collect_inventory(self._runner(timer_enabled="enabled"), root=self.root)
        self.assertFalse(inventory.install_preconditions(result["inventory"]))

    def test_runtime_fingerprint_binds_shared_container_invariance(self) -> None:
        first = inventory.collect_inventory(self._runner(), root=self.root)
        second = inventory.collect_inventory(self._runner(third_party_image="7"), root=self.root)
        self.assertNotEqual(first["runtime_fingerprint"], second["runtime_fingerprint"])

    def test_fixed_inventory_rejects_wrong_container_identity_or_schema(self) -> None:
        base = self._runner()
        def wrong(argv):
            result = base(argv)
            if "container" in argv and argv[-1] == "markina-gallery-api-1":
                return self._result(list(argv), "f" * 64 + "|sha256:" + "a" * 64 +
                                    "|running|true|now|other-project|api|healthy\n")
            if "exec" in argv:
                return self._result(list(argv), "unknown schema\n")
            return result
        with self.assertRaises(inventory.InventoryError):
            inventory.collect_inventory(wrong, root=self.root)

    def test_inventory_failure_logs_only_allowlisted_code(self) -> None:
        for code in ("container_inspect_failed", "shared_container_list_empty"):
            with self.subTest(code=code):
                output = io.StringIO()
                error = inventory.InventoryError(code)
                with (mock.patch.object(inventory, "collect_inventory", side_effect=error),
                      contextlib.redirect_stdout(output)):
                    result = inventory.main()
                self.assertEqual(result, 1)
                self.assertEqual(output.getvalue(),
                                 f"platform-backup-runtime: inventory failed ({code})\n")

    def test_inventory_failure_never_logs_untrusted_exception_text(self) -> None:
        failures = (
            (inventory.InventoryError("/etc/pyp-backup/source.json: secret"), "inventory_error"),
            (OSError("/etc/pyp-backup/keyring.json: secret"), "inventory_io_failed"),
            (subprocess.TimeoutExpired("docker", 20, stderr="private output"),
             "inventory_command_failed"),
        )
        for error, expected in failures:
            with self.subTest(expected=expected):
                output = io.StringIO()
                with (mock.patch.object(inventory, "collect_inventory", side_effect=error),
                      contextlib.redirect_stdout(output)):
                    result = inventory.main()
                self.assertEqual(result, 1)
                self.assertEqual(output.getvalue(),
                                 f"platform-backup-runtime: inventory failed ({expected})\n")
                self.assertNotIn("/etc", output.getvalue())
                self.assertNotIn("secret", output.getvalue())
                self.assertNotIn("private output", output.getvalue())

    def test_installed_release_requires_matching_root_owned_receipts(self) -> None:
        if os.name != "posix" or os.geteuid() != 0:
            self.skipTest("root-only release evidence requires POSIX root")
        sha = "a" * 40
        bundle_sha = "b" * 64
        install = self.root / "opt/pyp-backup-runtime"
        release = install / "releases" / sha
        rollback_root = install / "rollback"
        release.mkdir(parents=True, mode=0o700)
        rollback_root.mkdir(mode=0o700)
        os.chmod(install, 0o700)
        os.chmod(install / "releases", 0o700)
        rollback_data = b'{"schema_version":1,"source_sha":"' + sha.encode() + b'"}\n'
        rollback_path = rollback_root / f"{sha}.json"
        rollback_path.write_bytes(rollback_data)
        os.chmod(rollback_root, 0o700)
        os.chmod(rollback_path, 0o600)
        os.symlink(f"releases/{sha}", install / "current")
        manifest = {"schema_version": 1, "source_sha": sha, "files": []}
        (release / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        os.chmod(release / "manifest.json", 0o400)
        receipt = {
            "schema_version": 1, "status": "installed_inert", "source_sha": sha,
            "bundle_sha256": bundle_sha, "approval_fingerprint": "c" * 64,
            "current_release": f"releases/{sha}", "previous_release": None,
            "rollback_receipt_sha256": hashlib.sha256(rollback_data).hexdigest(),
            "service_enabled": False, "service_active": False,
            "timer_enabled": False, "timer_active": False, "destination_enabled": False,
        }
        (release / "install-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        os.chmod(release / "install-receipt.json", 0o600)
        os.chmod(release, 0o700)
        verified = inventory.verify_installed_release(sha, bundle_sha, install)
        self.assertEqual(verified, {"source_sha": sha, "bundle_sha256": bundle_sha, "status": "installed_inert"})
        with self.assertRaisesRegex(inventory.InventoryError, "installed_release_current_mismatch"):
            inventory.verify_installed_release("d" * 40, bundle_sha, install)
        rollback_path.write_bytes(b"changed")
        with self.assertRaisesRegex(inventory.InventoryError, "installed_release_rollback_mismatch"):
            inventory.verify_installed_release(sha, bundle_sha, install)


if __name__ == "__main__":
    unittest.main()
