"""Tests for fail-closed discovery of shared Compose references."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from retirement_host_references import find_container_references, find_references


class HostReferenceScanTests(unittest.TestCase):
    def test_finds_deep_compose_references_by_absolute_path_or_binding_name(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "a" / "b" / "c" / "d" / "e"
            nested.mkdir(parents=True)
            target = "/opt/markina-gallery/docker/.env.infinitepay-bindings"
            full = nested / "compose.yml"
            full.write_text(f"env_file: {target}\n", encoding="utf-8")
            relative = root / "docker-compose.other.yaml"
            relative.write_text("env_file: ../../markina-gallery/docker/.env.infinitepay-bindings\n", encoding="utf-8")
            self.assertEqual(find_references(target, [root]), sorted([str(full), str(relative)]))

    def test_ignores_non_compose_files_and_unrelated_configs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "notes.txt").write_text(".env.infinitepay-bindings", encoding="utf-8")
            (root / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
            self.assertEqual(find_references("/opt/markina-gallery/docker/.env.infinitepay-bindings", [root]), [])

    def test_follows_symlink_directories_and_stops_cycles(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "scan-root"
            root.mkdir()
            target_dir = base / "external-configs"
            target_dir.mkdir()
            compose_file = target_dir / "docker-compose.external.yml"
            target = "/opt/markina-gallery/docker/.env.infinitepay-bindings"
            compose_file.write_text(f"env_file: {target}\n", encoding="utf-8")
            try:
                (root / "external").symlink_to(target_dir, target_is_directory=True)
                (target_dir / "cycle").symlink_to(root, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")
            self.assertEqual(
                find_references(target, [root]),
                [str(root / "external" / compose_file.name)],
            )

    def test_aborts_when_a_configuration_root_cannot_be_scanned(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("retirement_host_references.os.walk", side_effect=PermissionError("denied")):
                with self.assertRaises(PermissionError):
                    find_references("/opt/markina-gallery/docker/.env.infinitepay-bindings", [Path(temp)])

    def test_finds_external_bind_mounts_and_ignores_markina_runtime(self):
        target = "/opt/markina-gallery/docker/.env.infinitepay-bindings"
        records = [
            {"name": "/markina-api", "project": "markina-gallery", "mounts": [{"Type": "bind", "Source": target}]},
            {"name": "/other-worker", "project": "other-project", "mounts": [{"Type": "bind", "Source": target}]},
            {"name": "/unrelated", "project": "other-project", "mounts": [{"Type": "volume", "Name": "data"}]},
        ]
        self.assertEqual(find_container_references(target, records), ["container:other-worker"])

    def test_aborts_on_incomplete_container_inspection(self):
        with self.assertRaises(ValueError):
            find_container_references("/target", [{"name": "/broken", "project": "other", "mounts": [{"Type": "bind"}]}])


if __name__ == "__main__":
    unittest.main()
