"""Integridade do runtime privado; arquivos públicos fictícios e sem crypto real."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wildcard_operational_runtime import load_runtime


@unittest.skipUnless(os.name == "posix", "Exige modos e links POSIX")
class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / "lib").mkdir(mode=0o755)
        self.module = self.root / "lib/fictitious.py"
        self.module.write_bytes(b"# public synthetic fixture\n")
        self.module.chmod(0o644)
        self.manifest = self.root / "runtime-manifest.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "lib/fictitious.py": hashlib.sha256(
                        self.module.read_bytes()
                    ).hexdigest()
                }
            )
        )
        self.manifest.chmod(0o600)

    def test_verified_runtime_path_is_added(self):
        load_runtime(self.root)
        self.addCleanup(sys.path.remove, str(self.root / "lib"))
        self.assertEqual(sys.path[0], str(self.root / "lib"))

    def test_empty_package_marker_is_valid_when_hash_matches(self):
        marker = self.root / "lib/py.typed"
        marker.touch()
        marker.chmod(0o444)
        files = {
            path.relative_to(self.root).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in (self.module, marker)
        }
        self.manifest.write_text(json.dumps(files))
        load_runtime(self.root)
        self.addCleanup(sys.path.remove, str(self.root / "lib"))

    def test_changed_file_is_rejected(self):
        self.module.write_bytes(b"# altered")
        with self.assertRaisesRegex(RuntimeError, "^runtime_changed$"):
            load_runtime(self.root)

    def test_unlisted_bytecode_and_linked_directories_are_rejected(self):
        (self.root / "lib/extra.pyc").write_bytes(b"fake-bytecode")
        with self.assertRaisesRegex(RuntimeError, "^runtime_inventory_changed$"):
            load_runtime(self.root)
        (self.root / "lib/extra.pyc").unlink()
        (self.root / "lib/linked").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "^runtime_link_invalid$"):
            load_runtime(self.root)

    def test_manifest_cannot_escape_library(self):
        self.manifest.write_text(json.dumps({"lib/../../outside": "a" * 64}))
        with self.assertRaisesRegex(RuntimeError, "^runtime_manifest_invalid$"):
            load_runtime(self.root)


if __name__ == "__main__":
    unittest.main()
