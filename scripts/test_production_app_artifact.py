from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import production_app_artifact as artifact

TARGET_SHA = "a" * 40
API_ID = "sha256:" + "1" * 64
WEB_ID = "sha256:" + "2" * 64
BASE_ID = "sha256:" + "3" * 64


class ProductionAppArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.images = self.root / "images.tar.gz"
        self.images.write_bytes(b"synthetic docker archive\x00with bytes\n")
        self.bundle = self.root / "bundle.bin"

    def tearDown(self):
        self.temp.cleanup()

    def create(self):
        return artifact.create_bundle(self.images, self.bundle, TARGET_SHA, BASE_ID, API_ID, WEB_ID)

    def rewrite_manifest(self, update):
        raw = self.bundle.read_bytes()
        offset = len(artifact.MAGIC)
        length = artifact.LENGTH.unpack(raw[offset:offset + artifact.LENGTH.size])[0]
        start = offset + artifact.LENGTH.size
        manifest = json.loads(raw[start:start + length])
        update(manifest)
        encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        self.bundle.write_bytes(
            artifact.MAGIC + artifact.LENGTH.pack(len(encoded)) + encoded + raw[start + length:]
        )
        return hashlib.sha256(self.bundle.read_bytes()).hexdigest()

    def test_round_trip_preserves_bundle_and_image_archive_bytes(self):
        digest = self.create()
        manifest, extracted = artifact.verify_bundle(
            self.bundle, TARGET_SHA, digest, expected_api_base_image_id=BASE_ID,
            extract_dir=self.root,
        )
        self.assertEqual(manifest["api_base_image_id"], BASE_ID)
        self.assertEqual(manifest["api_image_id"], API_ID)
        self.assertEqual(manifest["web_image_id"], WEB_ID)
        self.assertEqual(manifest["platform"], "linux/arm64")
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted.read_bytes(), self.images.read_bytes())
        self.assertEqual(hashlib.sha256(self.bundle.read_bytes()).hexdigest(), digest)

    def test_rejects_bundle_digest_mismatch(self):
        digest = self.create()
        self.bundle.write_bytes(self.bundle.read_bytes() + b"changed")
        with self.assertRaisesRegex(artifact.ArtifactError, "SHA-256 do bundle diverge"):
            artifact.verify_bundle(self.bundle, TARGET_SHA, digest)

    def test_rejects_wrong_target_sha_before_image_extraction(self):
        digest = self.create()
        with self.assertRaisesRegex(artifact.ArtifactError, "outro SHA"):
            artifact.verify_bundle(self.bundle, "b" * 40, digest)

    def test_rejects_api_base_that_differs_from_preflight_inventory(self):
        digest = self.create()
        with self.assertRaisesRegex(artifact.ArtifactError, "ID-base API diverge"):
            artifact.verify_bundle(self.bundle, TARGET_SHA, digest, "sha256:" + "4" * 64)

    def test_cli_create_and_verify_bind_the_api_base_id(self):
        create = subprocess.run(
            [sys.executable, str(Path(artifact.__file__)), "create", "--images", str(self.images),
             "--output", str(self.bundle), "--target-sha", TARGET_SHA,
             "--api-base-image-id", BASE_ID, "--api-image-id", API_ID, "--web-image-id", WEB_ID],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(create.returncode, 0, create.stderr)
        digest = next(line.split("=", 1)[1] for line in create.stdout.splitlines()
                      if line.startswith("bundle_sha256="))
        verify = subprocess.run(
            [sys.executable, str(Path(artifact.__file__)), "verify", "--bundle", str(self.bundle),
             "--target-sha", TARGET_SHA, "--bundle-sha256", digest,
             "--api-base-image-id", BASE_ID],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(verify.returncode, 0, verify.stderr)
        self.assertIn(f"api_base_image_id={BASE_ID}", verify.stdout)

    def test_rejects_wrong_platform_even_if_outer_digest_matches(self):
        self.create()
        digest = self.rewrite_manifest(lambda manifest: manifest.update(platform="linux/amd64"))
        with self.assertRaisesRegex(artifact.ArtifactError, "não é linux/arm64"):
            artifact.verify_bundle(self.bundle, TARGET_SHA, digest)

    def test_rejects_changed_image_archive_even_if_outer_digest_matches(self):
        digest = self.create()
        data = bytearray(self.bundle.read_bytes())
        data[-1] ^= 1
        self.bundle.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        with self.assertRaisesRegex(artifact.ArtifactError, "SHA-256 do arquivo de imagens diverge"):
            artifact.verify_bundle(self.bundle, TARGET_SHA, digest)

    def test_rejects_duplicate_manifest_keys(self):
        self.create()
        raw = self.bundle.read_bytes()
        offset = len(artifact.MAGIC)
        length = artifact.LENGTH.unpack(raw[offset:offset + artifact.LENGTH.size])[0]
        start = offset + artifact.LENGTH.size
        manifest = raw[start:start + length].decode()
        manifest = manifest[:-1] + ',"schema_version":1}'
        encoded = manifest.encode()
        self.bundle.write_bytes(
            artifact.MAGIC + artifact.LENGTH.pack(len(encoded)) + encoded + raw[start + length:]
        )
        digest = hashlib.sha256(self.bundle.read_bytes()).hexdigest()
        with self.assertRaisesRegex(artifact.ArtifactError, "chave duplicada"):
            artifact.verify_bundle(self.bundle, TARGET_SHA, digest)

    def test_create_rejects_same_or_malformed_image_ids(self):
        with self.assertRaisesRegex(artifact.ArtifactError, "mesmo ID"):
            artifact.create_bundle(self.images, self.bundle, TARGET_SHA, BASE_ID, API_ID, API_ID)
        with self.assertRaisesRegex(artifact.ArtifactError, "ID imutável"):
            artifact.create_bundle(self.images, self.bundle, TARGET_SHA, BASE_ID, "latest", WEB_ID)

    def test_rejects_symlink_bundle(self):
        digest = self.create()
        link = self.root / "link.bundle"
        try:
            link.symlink_to(self.bundle)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable")
        with self.assertRaises(artifact.ArtifactError):
            artifact.verify_bundle(link, TARGET_SHA, digest)


if __name__ == "__main__":
    unittest.main()
