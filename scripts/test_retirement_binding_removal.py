"""Tests for the narrowly scoped post-release binding removal."""

import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from retirement_binding_removal import remove_binding
from test_retirement_inventory_policy import RetirementInventoryTests


class BindingRemovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.expected_root_patch = patch("retirement_inventory_policy.EXPECTED_ROOT", str(self.root))
        self.expected_root_patch.start()
        self.addCleanup(self.expected_root_patch.stop)
        docker = self.root / "docker"
        docker.mkdir()
        self.binding = docker / ".env.infinitepay-bindings"
        self.binding.write_bytes(b"opaque-test-fixture")
        self.binding.chmod(0o600)
        metadata = os.lstat(self.binding)
        self.inventory = RetirementInventoryTests().valid_inventory()
        self.inventory["root"] = str(self.root)
        self.inventory["binding"].update({
            "path": str(self.binding),
            "mode": "0600",
            "size_bytes": metadata.st_size,
            "link_count": metadata.st_nlink,
            "mtime_ns": metadata.st_mtime_ns,
            "inode": metadata.st_ino,
            "device": metadata.st_dev,
            "uid": metadata.st_uid,
        })

    def call_remove(self, *, healthy=True, consumers=None, host_refs=None, target_refs=None):
        args = {
            "runtime_healthy": healthy,
            "compose_consumers": consumers or [],
            "host_references": host_refs or [],
            "target_references": target_refs or [],
            "project_root": self.root,
        }
        if os.name == "nt":
            approved = self.inventory["binding"]
            fake = SimpleNamespace(
                st_mode=stat.S_IFREG | 0o600,
                st_size=approved["size_bytes"],
                st_nlink=approved["link_count"],
                st_mtime_ns=approved["mtime_ns"],
                st_ino=approved["inode"],
                st_dev=approved["device"],
                st_uid=approved["uid"],
            )
            with patch("retirement_binding_removal.os.lstat", return_value=fake):
                return remove_binding(self.inventory, **args)
        return remove_binding(self.inventory, **args)

    def test_removes_only_the_approved_regular_file_after_health(self):
        self.assertEqual(self.call_remove(), (True, "binding_exclusivo_removido"))
        self.assertFalse(self.binding.exists())

    def test_refuses_before_health_or_while_referenced(self):
        self.assertEqual(self.call_remove(healthy=False)[1], "runtime_nao_saudavel")
        self.assertEqual(self.call_remove(consumers=["markina-gallery/api"])[1], "binding_ainda_referenciado")
        self.assertTrue(self.binding.exists())

    def test_refuses_symlink_or_changed_metadata(self):
        self.binding.unlink()
        outside = self.root / "outside"
        outside.write_bytes(b"do-not-touch")
        try:
            self.binding.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"criação de symlink indisponível neste Windows: {exc}")
        self.assertEqual(self.call_remove()[1], "binding_ou_diretorio_com_link_simbolico")
        self.assertEqual(outside.read_bytes(), b"do-not-touch")

    def test_refuses_binding_outside_exact_project_docker_directory(self):
        self.inventory["binding"]["path"] = str(self.root / "other" / "binding")
        (self.root / "other").mkdir()
        (self.root / "other" / "binding").write_bytes(b"opaque-test-fixture")
        self.assertEqual(self.call_remove()[1], "binding_fora_do_diretorio_aprovado")


if __name__ == "__main__":
    unittest.main()
