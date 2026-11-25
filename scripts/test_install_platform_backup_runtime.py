"""Installer transaction contracts on temporary synthetic roots only."""

from __future__ import annotations

import copy
import hashlib
import io
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import install_platform_backup_runtime as installer
import platform_backup_runtime_artifact as artifact


class RuntimeInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pyp-backup-install-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.python_executable = self.root / "synthetic-python"
        self.python_executable.write_bytes(b"synthetic interpreter")
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self._git("init", "--quiet")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "Synthetic Test")
        wheel_stream = io.BytesIO()
        with zipfile.ZipFile(wheel_stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("demo/__init__.py", "VALUE = 1\n")
            archive.writestr("demo-1.0.dist-info/METADATA", "Metadata-Version: 2.1\nName: demo\nVersion: 1.0\n")
            archive.writestr("demo-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
            archive.writestr("demo-1.0.dist-info/RECORD", "demo/__init__.py,,\n")
        wheel = wheel_stream.getvalue()
        digest = hashlib.sha256(wheel).hexdigest()
        self._write("backend/app/__init__.py", b"")
        self._write("backend/app/platform_backup/production_cli.py", b"# synthetic cli\n")
        self.lock = f"demo==1.0 --hash=sha256:{digest}\n".encode()
        self._write(artifact.LOCK_PATH, self.lock)
        runtime_dir = artifact.REPOSITORY_ROOT / "scripts/backup_runtime"
        for name in ("pyp-platform-backup.service", "pyp-platform-backup.timer"):
            target = self.repo / "scripts/backup_runtime" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((runtime_dir / name).read_bytes())
        self._git("add", ".")
        self._git("commit", "--quiet", "-m", "synthetic backup runtime")
        self.sha = self._git("rev-parse", "HEAD").stdout.strip()
        wheelhouse = self.root / "wheelhouse"
        wheelhouse.mkdir()
        (wheelhouse / "demo-1.0-cp310-cp310-manylinux_2_17_aarch64.whl").write_bytes(wheel)
        self.bundle_path = self.root / "bundle.tar.gz"
        self.bundle_sha = artifact.build_bundle(self.repo, self.sha, wheelhouse, self.bundle_path)
        self.bundle = self.bundle_path.read_bytes()
        self.fingerprint = "b" * 64
        self.install_root = self.root / "opt/pyp-backup-runtime"
        self.install_root.parent.mkdir(mode=0o700)
        os.chmod(self.install_root.parent, 0o700)
        self.systemd_root = self.root / "etc/systemd/system"
        self.systemd_root.mkdir(parents=True, mode=0o700)
        self.config_root = self.root / "etc/pyp-backup"
        self.lock_path = self.root / "deploy-state/production-release.lock"
        self.lock_path.parent.mkdir(mode=0o700)
        self.lock_path.write_bytes(b"")
        os.chmod(self.lock_path, 0o600)
        self.lock_owner = (os.geteuid(), os.getegid()) if os.name == "posix" else None
        self.inventory_result = {
            "fingerprint": self.fingerprint,
            "approval_fingerprint": self.fingerprint,
            "approval_fingerprint_version": 2,
            "runtime_fingerprint": "c" * 64,
            "inventory": {
                "containers": {name: {"running": True, "health": "healthy"}
                               for name in ("api", "web", "db")},
                "database_schema": "20261113_0126",
                "disk_var_lib": {
                    "filesystem_binding": "d" * 64, "total_kib": 100000,
                    "used_kib": 50000, "available_kib": 50000, "use_percent": 50,
                },
                "disk_install_root": {
                    "filesystem_binding": "e" * 64, "total_kib": 100000,
                    "used_kib": 50000, "available_kib": 50000, "use_percent": 50,
                },
                "disk_systemd_root": {
                    "filesystem_binding": "f" * 64, "total_kib": 100000,
                    "used_kib": 50000, "available_kib": 50000, "use_percent": 50,
                },
                "units": {name: {"load": "not-found", "enabled": "unknown", "active": "inactive"}
                          for name in ("service", "timer")},
                "paths": {
                    "config_directory": {"present": False}, "source": {"present": False},
                    "keyring": {"present": False}, "destination": {"present": False},
                    "picker_config_directory": {"present": False}, "picker_config": {"present": False},
                    "install_root": {"present": False}, "release_directory": {"present": False},
                    "current_release": {"present": False},
                },
            },
        }

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                              check=True, text=True, timeout=20)

    def _write(self, relative: str, data: bytes) -> None:
        path = self.repo / Path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def _install(self, *, runner=None, fingerprint: str | None = None, inventory_provider=None):
        def fake_wheels(stage, files, _runner, _python):
            python = stage / "venv/bin/python"
            python.parent.mkdir(parents=True, mode=0o700)
            python.write_bytes(b"synthetic interpreter")
            python.chmod(0o700)

        if runner is None:
            def runner(argv, **kwargs):
                if argv[:2] == ["/usr/bin/systemctl", "show"]:
                    unit = argv[-1]
                    state = "disabled" if unit.endswith("timer") else "static"
                    return subprocess.CompletedProcess(
                        argv, 0, f"ActiveState=inactive\nLoadState=loaded\nUnitFileState={state}\n", "",
                    )
                return subprocess.CompletedProcess(argv, 0, "", "")
        with (patch.object(installer, "_install_wheels", side_effect=fake_wheels),
              patch.object(installer, "_filesystem_block_size", return_value=4096)):
            return installer.install_verified_bundle(
                self.bundle, source_sha=self.sha, bundle_sha256=self.bundle_sha,
                approval_fingerprint=fingerprint or self.fingerprint,
                inventory_provider=inventory_provider or (lambda: self.inventory_result),
                runner=runner or (lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, "", "")),
                install_root=self.install_root, systemd_root=self.systemd_root, config_root=self.config_root,
                python_executable=str(self.python_executable),
                lock_path=self.lock_path, lock_owner=self.lock_owner,
                require_root=(os.name == "posix" and getattr(os, "geteuid", lambda: -1)() == 0),
            )

    def test_inert_check_requires_inactive_units_and_explicit_missing_phase(self) -> None:
        def absent(argv):
            return subprocess.CompletedProcess(
                argv, 0, "ActiveState=inactive\nLoadState=not-found\nUnitFileState=\n", "",
            )

        def active(argv):
            return subprocess.CompletedProcess(
                argv, 0, "ActiveState=active\nLoadState=loaded\nUnitFileState=static\n", "",
            )

        installer._assert_units_inert(absent, allow_missing=True)
        with self.assertRaisesRegex(installer.InstallError, "^systemd_unit_not_inert$"):
            installer._assert_units_inert(absent)
        with self.assertRaisesRegex(installer.InstallError, "^systemd_unit_not_inert$"):
            installer._assert_units_inert(active, allow_missing=True)

    def test_cli_binds_every_inventory_read_to_approved_source_sha(self) -> None:
        inventory_result = {"sentinel": "synthetic"}
        with patch.object(installer, "collect_inventory", return_value=inventory_result) as collect, \
                patch.object(installer, "install_verified_bundle", return_value={"status": "installed_inert"}) as install, \
                patch.object(installer, "_read_stdin", return_value=self.bundle), \
                patch("builtins.print"):
            status = installer.main([
                "--sha", self.sha,
                "--bundle-sha256", self.bundle_sha,
                "--approval-fingerprint", self.fingerprint,
            ])

        self.assertEqual(status, 0)
        install.assert_called_once()
        self.assertEqual(install.call_args.kwargs["source_sha"], self.sha)
        self.assertEqual(install.call_args.kwargs["bundle_sha256"], self.bundle_sha)
        inventory_provider = install.call_args.kwargs["inventory_provider"]
        self.assertIs(inventory_provider(), inventory_result)
        self.assertIs(inventory_provider(), inventory_result)
        self.assertEqual(collect.call_count, 2)
        collect.assert_called_with(bridge_sha=self.sha)

    def test_verified_install_is_versioned_inert_and_keeps_rollback_receipt(self) -> None:
        if os.name != "posix":
            self.skipTest("systemd-style filesystem transaction requires POSIX")
        receipt = self._install()
        release = self.install_root / "releases" / self.sha
        self.assertEqual(receipt["status"], "installed_inert")
        self.assertEqual(receipt["approval_fingerprint_version"], 2)
        self.assertEqual(receipt["approval_fingerprint"], self.fingerprint)
        self.assertEqual(receipt["current_release"], f"releases/{self.sha}")
        self.assertFalse(receipt["service_enabled"])
        self.assertFalse(receipt["timer_enabled"])
        self.assertFalse(receipt["destination_enabled"])
        self.assertEqual(os.readlink(self.install_root / "current"), f"releases/{self.sha}")
        self.assertTrue((release / "install-receipt.json").is_file())
        rollback = self.install_root / "rollback" / f"{self.sha}.json"
        self.assertTrue(rollback.is_file())
        self.assertFalse((self.config_root / "destination.json").exists())
        service = (self.systemd_root / "pyp-platform-backup.service").read_text(encoding="utf-8")
        timer = (self.systemd_root / "pyp-platform-backup.timer").read_text(encoding="utf-8")
        self.assertIn("ExecStart=/opt/pyp-backup-runtime/current/venv/bin/python", service)
        self.assertIn("OnCalendar=*-*-* 08:30:00 UTC", timer)
        self.assertFalse((release / "wheelhouse").exists())

    def test_fingerprint_mismatch_aborts_before_any_persistent_write(self) -> None:
        with self.assertRaisesRegex(installer.InstallError, "inventory_fingerprint_mismatch"):
            self._install(fingerprint="a" * 64)
        self.assertFalse(self.install_root.exists())
        self.assertEqual(list(self.systemd_root.iterdir()), [])

    def test_capacity_bound_uses_verified_wheel_contents_and_stage_payload(self) -> None:
        files = installer._read_bundle_files(self.bundle)
        requirement = installer._installation_capacity_requirements(
            files, python_executable=str(self.python_executable),
            install_block_size=4096, systemd_block_size=4096,
        )
        self.assertGreater(requirement["disk_install_root"], sum(map(len, files.values())))
        self.assertGreater(requirement["disk_systemd_root"], 0)

    def test_capacity_bound_rejects_unreadable_wheel(self) -> None:
        files = installer._read_bundle_files(self.bundle)
        wheel_path = next(name for name in files if name.startswith("wheelhouse/"))
        files[wheel_path] = b"not a wheel archive"
        with self.assertRaisesRegex(installer.InstallError, "^install_capacity_bound_invalid$"):
            installer._installation_capacity_requirements(
                files, python_executable=str(self.python_executable),
                install_block_size=4096, systemd_block_size=4096,
            )

    def test_capacity_bound_rejects_wheel_expansion_over_fixed_limit(self) -> None:
        class LargeWheel:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            @staticmethod
            def infolist():
                return [SimpleNamespace(
                    filename="demo/module.py", external_attr=0,
                    file_size=installer.MAX_WHEEL_EXPANDED_BYTES + 1,
                    is_dir=lambda: False,
                )]

        with patch.object(installer.zipfile, "ZipFile", return_value=LargeWheel()), \
                self.assertRaisesRegex(installer.InstallError, "^install_capacity_bound_invalid$"):
            installer._wheel_install_size_bound({"wheelhouse/demo.whl": b"synthetic"}, 4096)

    def test_capacity_guard_requires_space_and_projected_usage_below_75_percent(self) -> None:
        installer._assert_install_capacity(self.inventory_result["inventory"], {
            "disk_install_root": 1024 * 1024, "disk_systemd_root": 64 * 1024,
        })
        low_space = self.inventory_result["inventory"]
        original_available = low_space["disk_install_root"]["available_kib"]
        low_space["disk_install_root"]["available_kib"] = 1
        with self.assertRaisesRegex(installer.InstallError, "^install_capacity_insufficient$"):
            installer._assert_install_capacity(low_space, {"disk_install_root": 2 * 1024})
        low_space["disk_install_root"]["available_kib"] = original_available

        near_limit = self.inventory_result["inventory"]
        near_limit["disk_install_root"]["used_kib"] = 74000
        near_limit["disk_install_root"]["available_kib"] = 26000
        with self.assertRaisesRegex(installer.InstallError, "^install_capacity_limit_exceeded$"):
            installer._assert_install_capacity(near_limit, {"disk_install_root": 1024 * 1024})

    def test_capacity_guard_sums_destinations_sharing_one_filesystem(self) -> None:
        shared = self.inventory_result["inventory"]
        shared["disk_install_root"]["used_kib"] = 70000
        shared["disk_install_root"]["available_kib"] = 30000
        shared["disk_systemd_root"]["filesystem_binding"] = shared["disk_install_root"]["filesystem_binding"]
        shared["disk_systemd_root"]["total_kib"] = 100000
        shared["disk_systemd_root"]["used_kib"] = 70000
        shared["disk_systemd_root"]["available_kib"] = 30000
        with self.assertRaisesRegex(installer.InstallError, "^install_capacity_limit_exceeded$"):
            installer._assert_install_capacity(shared, {
                "disk_install_root": 3 * 1024 * 1024,
                "disk_systemd_root": 3 * 1024 * 1024,
            })

    def test_capacity_filesystem_binding_and_total_must_remain_approved(self) -> None:
        approved = self.inventory_result["inventory"]
        changed = copy.deepcopy(approved)
        changed["disk_install_root"]["filesystem_binding"] = "0" * 64
        with self.assertRaisesRegex(installer.InstallError, "^install_capacity_filesystem_changed$"):
            installer._assert_capacity_filesystems_unchanged(approved, changed)
        changed = copy.deepcopy(approved)
        changed["disk_systemd_root"]["total_kib"] += 1
        with self.assertRaisesRegex(installer.InstallError, "^install_capacity_filesystem_changed$"):
            installer._assert_capacity_filesystems_unchanged(approved, changed)

    def test_capacity_filesystem_change_aborts_before_first_write(self) -> None:
        calls = 0

        def inventory_provider():
            nonlocal calls
            calls += 1
            snapshot = copy.deepcopy(self.inventory_result)
            if calls >= 2:
                snapshot["inventory"]["disk_install_root"]["filesystem_binding"] = "0" * 64
            return snapshot

        with patch.object(installer, "_filesystem_block_size", return_value=4096), \
                self.assertRaisesRegex(installer.InstallError, "^install_capacity_filesystem_changed$"):
            self._install(inventory_provider=inventory_provider)
        self.assertEqual(calls, 2)
        self.assertFalse(self.install_root.exists())
        self.assertEqual(list(self.systemd_root.iterdir()), [])

    def test_insufficient_capacity_aborts_before_install_root_creation(self) -> None:
        self.inventory_result["inventory"]["disk_install_root"]["available_kib"] = 1
        with patch.object(installer, "_filesystem_block_size", return_value=4096), \
                self.assertRaisesRegex(installer.InstallError, "^install_capacity_insufficient$"):
            self._install()
        self.assertFalse(self.install_root.exists())
        self.assertEqual(list(self.systemd_root.iterdir()), [])

    def test_capacity_reduction_after_staging_aborts_before_active_swap(self) -> None:
        if os.name != "posix":
            self.skipTest("systemd-style filesystem transaction requires POSIX")
        calls = 0

        def inventory_provider():
            nonlocal calls
            calls += 1
            snapshot = copy.deepcopy(self.inventory_result)
            if calls >= 3:
                snapshot["inventory"]["disk_install_root"]["available_kib"] = 1
            return snapshot

        with self.assertRaisesRegex(installer.InstallError, "^install_capacity_insufficient$"):
            self._install(inventory_provider=inventory_provider)
        self.assertEqual(calls, 3)
        self.assertFalse(self.install_root.exists())
        self.assertEqual(list(self.systemd_root.iterdir()), [])

    def test_inventory_without_versioned_approval_fingerprint_aborts_before_write(self) -> None:
        self.inventory_result.pop("approval_fingerprint")
        with self.assertRaisesRegex(installer.InstallError, "inventory_fingerprint_mismatch"):
            self._install()
        self.assertFalse(self.install_root.exists())
        self.assertEqual(list(self.systemd_root.iterdir()), [])

    def test_failed_daemon_reload_restores_pointer_and_units_and_leaves_journal(self) -> None:
        if os.name != "posix":
            self.skipTest("systemd-style filesystem transaction requires POSIX")
        calls = []
        def fail_reload(argv, **kwargs):
            if argv[:2] == ["/usr/bin/systemctl", "show"]:
                unit = argv[-1]
                state = "disabled" if unit.endswith("timer") else "static"
                return subprocess.CompletedProcess(
                    argv, 0, f"ActiveState=inactive\nLoadState=loaded\nUnitFileState={state}\n", "",
                )
            calls.append(argv)
            status = 1 if len(calls) == 1 else 0
            return subprocess.CompletedProcess(argv, status, "", "")
        with self.assertRaisesRegex(installer.InstallError, "systemd_reload_failed"):
            self._install(runner=fail_reload)
        self.assertFalse((self.install_root / "current").exists())
        self.assertFalse((self.systemd_root / "pyp-platform-backup.service").exists())
        self.assertTrue((self.install_root / "install-journal.json").is_file())
        self.assertEqual(len(calls), 2)

    def test_runtime_change_after_artifact_staging_rolls_back_inert_install(self) -> None:
        if os.name != "posix":
            self.skipTest("systemd-style filesystem transaction requires POSIX")
        calls = 0
        def inventory_provider():
            nonlocal calls
            calls += 1
            result = dict(self.inventory_result)
            result["runtime_fingerprint"] = "d" * 64 if calls > 2 else "c" * 64
            return result
        # The only inventory recheck is made after artifact preparation.
        with patch.object(installer, "_install_wheels") as fake_wheels, \
                patch.object(installer, "_filesystem_block_size", return_value=4096), \
                self.assertRaisesRegex(installer.InstallError, "runtime_changed_during_install"):
            installer.install_verified_bundle(
                self.bundle, source_sha=self.sha, bundle_sha256=self.bundle_sha,
                approval_fingerprint=self.fingerprint, inventory_provider=inventory_provider,
                runner=lambda argv, **kwargs: subprocess.CompletedProcess(
                    argv, 0, "ActiveState=inactive\nLoadState=loaded\nUnitFileState=disabled\n", "",
                ) if argv[:2] == ["/usr/bin/systemctl", "show"]
                    else subprocess.CompletedProcess(argv, 0, "", ""),
                install_root=self.install_root, systemd_root=self.systemd_root,
                config_root=self.config_root, lock_path=self.lock_path, lock_owner=self.lock_owner,
                python_executable=str(self.python_executable),
                require_root=(os.name == "posix" and getattr(os, "geteuid", lambda: -1)() == 0),
            )
        self.assertEqual(calls, 3)
        self.assertFalse((self.install_root / "current").exists())
        self.assertFalse((self.systemd_root / "pyp-platform-backup.service").exists())
        self.assertFalse((self.install_root / "install-journal.json").exists())
        self.assertTrue(fake_wheels.called)

    def test_common_release_lock_busy_blocks_before_inventory_or_writes(self) -> None:
        if installer.fcntl is None:
            self.skipTest("flock requires POSIX")
        descriptor = os.open(self.lock_path, os.O_RDONLY)
        try:
            installer.fcntl.flock(descriptor, installer.fcntl.LOCK_EX | installer.fcntl.LOCK_NB)
            with self.assertRaisesRegex(installer.InstallError, "production_release_lock_busy"):
                installer.install_verified_bundle(
                    self.bundle, source_sha=self.sha, bundle_sha256=self.bundle_sha,
                    approval_fingerprint=self.fingerprint,
                    inventory_provider=lambda: self.fail("inventory must not run while lock is busy"),
                    install_root=self.install_root, systemd_root=self.systemd_root,
                    config_root=self.config_root, lock_path=self.lock_path, lock_owner=self.lock_owner,
                    require_root=(os.name == "posix" and getattr(os, "geteuid", lambda: -1)() == 0),
                )
        finally:
            installer.fcntl.flock(descriptor, installer.fcntl.LOCK_UN)
            os.close(descriptor)
        self.assertFalse(self.install_root.exists())


if __name__ == "__main__":
    unittest.main()
