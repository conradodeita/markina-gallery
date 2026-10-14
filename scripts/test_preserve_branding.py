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
            self.settings_reads += 1
            if self.settings_changed and self.settings_reads == 2:
                return subprocess.CompletedProcess(args, 0, b"", b"")
            output = "\n".join(json.dumps(row) for row in self.rows).encode()
        if args[:3] == ("exec", "own-api", "python") and self.unsafe_source and args[-1].startswith("["):
            raise RuntimeError("source ancestor symlink")
        if args[0] == "cp":
            if self.copy_failure:
                return subprocess.CompletedProcess(args, 1, b"", b"permission denied")
            if self.valid_source:
                key = args[1].split("/branding/", 1)[1]
                body = self.asset_bytes.get(key, b"logo")
                output = io.BytesIO()
                with tarfile.open(fileobj=output, mode="w") as archive:
                    entry = tarfile.TarInfo(Path(key).name)
                    entry.size = len(body)
                    archive.addfile(entry, io.BytesIO(body))
                return subprocess.CompletedProcess(args, 0, output.getvalue(), b"")
            return subprocess.CompletedProcess(args, 1, b"", b"Could not find the file logo.png")
        if args[0] == "run" and self.restore_failure:
            raise RuntimeError("copy failed")
        return subprocess.CompletedProcess(args, code, output, b"")

    def run_preserve(self, copy_failure=False, restore_failure=False, valid_source=False, rows=None,
                     asset_bytes=None, settings_changed=False, unsafe_source=False):
        self.calls = []
        self.rows = rows if rows is not None else [{"tenant_id": None, "keys": ["logo.png", None, None]}]
        self.asset_bytes = asset_bytes or {}
        self.settings_reads = 0
        self.settings_changed, self.unsafe_source = settings_changed, unsafe_source
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

    def test_settings_change_after_stop_aborts_copy_and_restarts_old_api(self):
        with self.assertRaisesRegex(ValueError, "settings changed"):
            self.run_preserve(settings_changed=True)
        self.assertIn(("start", "own-api"), self.calls)
        self.assertFalse(any(call[0] in {"cp", "run"} for call in self.calls))

    def test_unsafe_source_ancestor_is_refused_before_api_stop(self):
        with self.assertRaisesRegex(RuntimeError, "ancestor symlink"):
            self.run_preserve(unsafe_source=True)
        self.assertFalse(any(call[0] in {"stop", "cp", "run"} for call in self.calls))

    def test_three_owners_preserve_scoped_and_legacy_assets(self):
        owners = [str(uuid4()) for _ in range(3)]
        files = {"logo.png": b"logo"}
        rows = [{"tenant_id": owners[0], "keys": ["logo.png", None, None]}]
        for owner, body in zip(owners[1:], (b"brand-b", b"brand-c")):
            key = f"tenants/{owner}/branding/logo-{branding.digest(body)}.png"
            files[key] = body
            rows.append({"tenant_id": owner, "keys": [key, None, None]})
        self.run_preserve(valid_source=True, rows=rows, asset_bytes=files)
        backup = next((self.root / "backups").glob("branding-*"))
        branding.transfer(backup, self.destination)
        for key, body in files.items():
            self.assertEqual((backup / key).read_bytes(), body)
            self.assertEqual((self.destination / key).read_bytes(), body)
        manifest = json.loads((backup / "manifest.json").read_text())
        self.assertEqual(manifest["files"], {key: branding.digest(body) for key, body in files.items()})
        self.assertNotIn(("start", "own-api"), self.calls)
        with patch.object(branding, "docker") as run:
            branding.restore_volume(backup, "fixture-image")
        payload = run.call_args.kwargs["input_data"]
        with patch.object(branding.sys, "stdin") as stdin:
            stdin.buffer = io.BytesIO(payload)
            branding.receive_backup(self.root / "receiver")
        for key, body in files.items():
            self.assertEqual((self.root / "receiver" / key).read_bytes(), body)

    def test_ambiguous_owner_or_cross_owner_key_never_stops_old_api(self):
        owner, other = str(uuid4()), str(uuid4())
        scoped = f"tenants/{other}/branding/logo-{'a' * 64}.png"
        candidates = [
            [{"tenant_id": owner, "keys": []}, {"tenant_id": owner, "keys": []}],
            [{"tenant_id": None, "keys": []}, {"tenant_id": other, "keys": []}],
            [{"tenant_id": owner, "keys": [scoped]}],
            [{"tenant_id": owner, "keys": ["logo.png"]}, {"tenant_id": other, "keys": ["logo.png"]}],
        ]
        for rows in candidates:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.run_preserve(rows=rows)
            self.assertFalse(any(call[0] == "stop" for call in self.calls))
            self.assertFalse(any(call[0] == "run" for call in self.calls))

    def test_scoped_paths_refuse_traversal_and_wrong_digest_before_transfer(self):
        owner = str(uuid4())
        for key in (f"tenants/{owner}/branding/../logo.png", f"tenants/{owner}/branding/logo-{'a' * 64}.png"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_preserve(valid_source=True, rows=[{"tenant_id": owner, "keys": [key]}])
            if "/../" in key:
                self.assertFalse(any(call[0] == "stop" for call in self.calls))
            else:
                self.assertIn(("start", "own-api"), self.calls)
            self.assertFalse(any(call[0] == "run" for call in self.calls))

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

    def test_transport_limit_is_checked_before_receiver_or_container(self):
        with patch.object(branding, "MAX_PAYLOAD_BYTES", 1), patch.object(branding, "docker") as run:
            with self.assertRaisesRegex(ValueError, "transport limit"):
                branding.restore_volume(self.backup, "fixture-image")
            run.assert_not_called()
            with patch.object(branding.sys, "stdin") as stdin:
                stdin.buffer = io.BytesIO(b"{}")
                with self.assertRaisesRegex(ValueError, "transport limit"):
                    branding.receive_backup(self.destination)
        self.assertFalse(self.destination.exists())

    def test_nested_conflict_is_detected_before_any_new_asset(self):
        body = b"brand-b"
        key = f"tenants/{uuid4()}/branding/logo-{branding.digest(body)}.png"
        path = self.backup / key
        path.parent.mkdir(parents=True)
        path.write_bytes(body)
        self.manifest["files"][key] = branding.digest(body)
        self.write_manifest()
        target = self.destination / key
        target.parent.mkdir(parents=True)
        target.write_bytes(b"conflicting")
        with self.assertRaises(ValueError):
            branding.transfer(self.backup, self.destination)
        self.assertFalse((self.destination / "logo.png").exists())
        self.assertEqual(target.read_bytes(), b"conflicting")

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
