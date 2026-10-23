"""The emergency image may change four distributions and no other package."""
import io
import re
import tarfile
import tempfile
import unittest
from pathlib import Path

from prepare_emergency_api_image import (
    PINS,
    extract_source,
    maintenance_configuration,
    validate_packages,
)


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.before = {"python": "3.13.16", "packages": {"aiohttp": "3.14.3", "multidict": "6.8.0",
                       "urllib3": "2.7.0", "yarl": "1.24.5", "fastapi": "0.142.2"}}
        self.after = {"python": "3.13.16", "packages": {**self.before["packages"], **PINS}}

    def test_four_pins_only(self):
        validate_packages(self.before, self.after)

    def test_other_distribution_or_python_drift_is_refused(self):
        for key, value in (("fastapi", "0.999"), ("extra-package", "1.0"), ("aiohttp", "3.14.3")):
            with self.subTest(key=key):
                altered = {**self.after, "packages": {**self.after["packages"], key: value}}
                with self.assertRaises(ValueError):
                    validate_packages(self.before, altered)
        with self.assertRaises(ValueError):
            validate_packages(self.before, {**self.after, "python": "3.13.17"})

    def test_removed_distribution_is_refused(self):
        del self.after["packages"]["fastapi"]
        with self.assertRaises(ValueError):
            validate_packages(self.before, self.after)

    def test_source_extraction_rejects_traversal_links_and_unapproved_files(self):
        for name, kind in (("../outside", tarfile.REGTYPE), ("backend/app/link", tarfile.SYMTYPE),
                           ("backend/requirements.txt", tarfile.REGTYPE)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode="w") as archive:
                    entry = tarfile.TarInfo(name)
                    entry.type = kind
                    archive.addfile(entry, io.BytesIO())
                with self.assertRaises(ValueError):
                    extract_source(stream.getvalue(), Path(folder))

    def test_git_source_regular_file_is_extracted(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            entry = tarfile.TarInfo("backend/app/example.py")
            entry.size = 3
            archive.addfile(entry, io.BytesIO(b"ok\n"))
        with tempfile.TemporaryDirectory() as folder:
            extract_source(stream.getvalue(), Path(folder))
            self.assertEqual((Path(folder) / "backend/app/example.py").read_bytes(), b"ok\n")

    def test_maintenance_preserves_only_health(self):
        result = maintenance_configuration("server {\n location / { proxy_pass http://web; }\n}\n")
        allowed = re.search(r'\$uri !~ "([^"]+)"', result).group(1)
        for path in ("/healthz", "/api/health"):
            self.assertRegex(path, allowed)
        for path in ("/", "/admin", "/api/admin/settings", "/api/client/checkout"):
            self.assertIsNone(re.search(allowed, path))
        self.assertIn("return 503", result)


if __name__ == "__main__":
    unittest.main()
