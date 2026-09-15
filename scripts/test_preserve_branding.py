"""Focused safety and real-container regression for branding persistence."""

import base64
import importlib.util
import io
import json
import os
import struct
import subprocess
import tarfile
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

SPEC = importlib.util.spec_from_file_location("preserve", Path(__file__).with_name("preserve_branding.py"))
branding = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(branding)


class BrandingTransferTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="pick-branding-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.backup = self.root / "backup"
        self.backup.mkdir()
        self.destination = self.root / "destination"
        self.files = {"logo.png": b"logo", "app-icon.png": b"icon", "favicon.ico": b"favicon"}
        for key, body in self.files.items():
            (self.backup / key).write_bytes(body)
        self.manifest = {"files": {key: branding.digest(body) for key, body in self.files.items()},
                         "missing": []}
        self.write_manifest()

    def write_manifest(self):
        (self.backup / "manifest.json").write_text(json.dumps(self.manifest))

    def test_restore_and_repeat_preserve_bytes_and_sources(self):
        for _ in range(2):
            branding.transfer(self.backup, self.destination)
        for key, body in self.files.items():
            self.assertEqual((self.destination / key).read_bytes(), body)
            self.assertEqual((self.backup / key).read_bytes(), body)

    def test_conflict_detected_before_any_new_file(self):
        self.destination.mkdir()
        (self.destination / "favicon.ico").write_bytes(b"different")
        with self.assertRaisesRegex(ValueError, "conflict"):
            branding.transfer(self.backup, self.destination)
        self.assertEqual(list(self.destination.iterdir()), [self.destination / "favicon.ico"])

    def test_corrupt_backup_rejected(self):
        (self.backup / "logo.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "integrity"):
            branding.transfer(self.backup, self.destination)
        self.assertFalse(self.destination.exists())

    def test_missing_report_does_not_require_fake_file(self):
        self.manifest = {"files": {}, "missing": ["logo.png"]}
        self.write_manifest()
        branding.transfer(self.backup, self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_invalid_key_rejected(self):
        self.manifest["files"]["../outside"] = "bad"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "key"):
            branding.transfer(self.backup, self.destination)

    def test_symlink_refused(self):
        self.destination.mkdir()
        try:
            (self.destination / "logo.png").symlink_to(self.backup / "logo.png")
        except OSError:
            self.skipTest("local symlink privilege unavailable; tar symlink test still runs")
        with self.assertRaisesRegex(ValueError, "file"):
            branding.transfer(self.backup, self.destination)

    def test_copy_failure_keeps_sources_and_no_partial_destination(self):
        with patch.object(branding.os, "link", side_effect=OSError("synthetic copy error")), \
             self.assertRaises(OSError):
            branding.transfer(self.backup, self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertEqual((self.backup / "logo.png").read_bytes(), b"logo")

    def test_archive_only_accepts_single_regular_asset(self):
        for kind in (tarfile.REGTYPE, tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE):
            output = io.BytesIO()
            with tarfile.open(fileobj=output, mode="w") as archive:
                entry = tarfile.TarInfo("logo.png")
                entry.type = kind
                entry.size = 4 if kind == tarfile.REGTYPE else 0
                entry.linkname = "/outside"
                archive.addfile(entry, io.BytesIO(b"logo") if kind == tarfile.REGTYPE else None)
            if kind == tarfile.REGTYPE:
                self.assertEqual(branding.extract_asset(output.getvalue(), "logo.png"), b"logo")
            else:
                with self.assertRaises(ValueError):
                    branding.extract_asset(output.getvalue(), "logo.png")

    def fake_docker(self, *args, **kwargs):
        self.calls.append(args)
        output = b""
        code = 0
        if args[:2] == ("volume", "inspect"):
            output = json.dumps([{"Labels": {"com.docker.compose.project": branding.PROJECT,
                "com.docker.compose.volume": "branding-assets"}, "Driver": "local"}]).encode()
        if args[:2] == ("exec", "-i"):
            output = b'["logo.png",null,null]\n'
        if args[0] == "cp":
            if self.copy_failure:
                return subprocess.CompletedProcess(args, 1, b"", b"permission denied")
            if self.valid_source:
                output = io.BytesIO()
                with tarfile.open(fileobj=output, mode="w") as archive:
                    entry = tarfile.TarInfo("logo.png")
                    entry.size = 4
                    archive.addfile(entry, io.BytesIO(b"logo"))
                return subprocess.CompletedProcess(args, 0, output.getvalue(), b"")
            return subprocess.CompletedProcess(args, 1, b"", b"Could not find the file logo.png")
        if args[0] == "run" and self.restore_failure:
            raise RuntimeError("copy failed")
        return subprocess.CompletedProcess(args, code, output, b"")

    def run_preserve(self, copy_failure=False, restore_failure=False, valid_source=False):
        self.calls = []
        self.copy_failure, self.restore_failure = copy_failure, restore_failure
        self.valid_source = valid_source
        info = {"Config": {"Env": []}, "Image": "sha256:fixture"}
        with patch.object(Path, "cwd", return_value=Path("/opt/markina-gallery")), \
             patch.object(Path, "resolve", lambda value: value), \
             patch.object(branding, "container", side_effect=[("own-api", info), ("own-db", {})]), \
             patch.object(branding, "docker", side_effect=self.fake_docker), \
             patch.object(branding, "BACKUPS", self.root / "backups"), \
             patch.object(branding, "STATE", self.root / "state"):
            branding.preserve()

    def test_absent_legacy_reported_and_override_preserves_rollback(self):
        self.run_preserve()
        self.assertNotIn(("start", "own-api"), self.calls)
        self.assertEqual((self.root / "state" / "branding.compose.yml").read_text(), branding.OVERRIDE)
        manifest = json.loads(next((self.root / "backups").glob("*/manifest.json")).read_text())
        self.assertEqual(manifest["missing"], ["logo.png"])

    def test_valid_legacy_is_backed_up_before_transfer(self):
        self.run_preserve(valid_source=True)
        backup = next((self.root / "backups").glob("branding-*"))
        self.assertEqual((backup / "logo.png").read_bytes(), b"logo")
        manifest = json.loads((backup / "manifest.json").read_text())
        self.assertEqual(manifest["files"], {"logo.png": branding.digest(b"logo")})
        operations = [args[0] for args in self.calls]
        self.assertLess(operations.index("stop"), operations.index("cp"))
        self.assertLess(operations.index("cp"), operations.index("run"))

    def test_transfer_uses_stdin_without_host_mount_or_added_capabilities(self):
        self.backup.chmod(0o700)
        for path in self.backup.iterdir():
            path.chmod(0o600)
        with patch.object(branding, "docker") as run:
            branding.restore_volume(self.backup, "fixture-image")
        args = run.call_args.args
        self.assertIn("ALL", args)
        self.assertIn("--read-only", args)
        self.assertNotIn("--cap-add", args)
        self.assertFalse(any("type=bind" in arg for arg in args))
        payload = json.loads(run.call_args.kwargs["input_data"])
        self.assertEqual(payload["manifest"], self.manifest)
        self.assertEqual(set(payload["files"]), set(self.files))

    def test_receiver_validates_payload_and_hash_before_publication(self):
        payload = {"manifest": self.manifest, "files": {
            key: base64.b64encode(body).decode() for key, body in self.files.items()
        }}
        for corrupt in (True, False):
            candidate = json.loads(json.dumps(payload))
            if corrupt:
                candidate["files"]["logo.png"] = base64.b64encode(b"wrong").decode()
            with patch.object(branding.sys, "stdin") as stdin:
                stdin.buffer = io.BytesIO(json.dumps(candidate).encode())
                if corrupt:
                    with self.assertRaisesRegex(ValueError, "integrity"):
                        branding.receive_backup(self.destination)
                    self.assertFalse(self.destination.exists())
                else:
                    branding.receive_backup(self.destination)
        self.assertEqual((self.destination / "logo.png").read_bytes(), b"logo")

    def test_any_copy_failure_restarts_old_api_and_does_not_enable_recreation(self):
        for kwargs in ({"copy_failure": True}, {"restore_failure": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(RuntimeError):
                self.run_preserve(**kwargs)
            self.assertIn(("start", "own-api"), self.calls)
            self.assertFalse((self.root / "state" / "branding.compose.yml").exists())

    @unittest.skipUnless(os.getenv("BRANDING_DOCKER_TEST") == "1", "explicit local Docker fixture")
    def test_real_container_recreation_retains_all_three_hashes(self):
        def chunk(kind, data):
            return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data))

        # Valid 64x64 PNGs, created only inside the temporary fixture.
        png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!2I5B", 64, 64, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\xcc\0" * 64) * 64)) + chunk(b"IEND", b""))
        self.manifest = {"files": {}, "missing": []}
        for key in ("logo.png", "app-icon.png", "favicon.png"):
            (self.backup / key).write_bytes(png)
            self.manifest["files"][key] = branding.digest(png)
        self.write_manifest()
        volume = "pick-branding-test-" + uuid4().hex
        branding.docker("volume", "create", "--label", "pick.branding.fixture=true", volume)
        try:
            for _ in range(2):
                # --rm removes each isolated container; the same volume survives both runs.
                branding.restore_volume(self.backup, "python:3.12-slim", volume)
            result = branding.docker("run", "--rm", "--network", "none", "--read-only",
                "--mount", f"type=volume,source={volume},target=/branding,readonly",
                "python:3.12-slim", "python", "-c",
                "import pathlib,hashlib,json; print(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() "
                "for p in pathlib.Path('/branding').iterdir()}))")
            self.assertEqual(json.loads(result.stdout), self.manifest["files"])
        finally:
            # Only the exact newly-created synthetic fixture, never a Compose/project volume.
            if volume.startswith("pick-branding-test-") and len(volume) == 51:
                branding.docker("volume", "rm", volume)


if __name__ == "__main__":
    unittest.main()
