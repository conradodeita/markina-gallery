"""Contracts for immutable ARM64 backup-runtime packages; no production access."""

from __future__ import annotations

import gzip
import hashlib
import io
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

import platform_backup_runtime_artifact as artifact


class RuntimeArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pyp-backup-artifact-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self._git("init", "--quiet")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "Synthetic Test")
        wheel = b"synthetic ARM64 wheel bytes"
        self.wheel_digest = hashlib.sha256(wheel).hexdigest()
        self.lock = (f"demo==1.0 --hash=sha256:{self.wheel_digest}\n").encode()
        self._write("backend/app/__init__.py", b"")
        self._write("backend/app/platform_backup/production_cli.py", b"# committed runtime source\n")
        self._write(artifact.LOCK_PATH, self.lock)
        runtime_dir = artifact.REPOSITORY_ROOT / "scripts/backup_runtime"
        for name in ("pyp-platform-backup.service", "pyp-platform-backup.timer"):
            target = self.repo / "scripts/backup_runtime" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(runtime_dir / name, target)
        self._git("add", ".")
        self._git("commit", "--quiet", "-m", "synthetic runtime source")
        self.sha = self._git("rev-parse", "HEAD").stdout.strip()
        self.wheelhouse = self.root / "wheelhouse"
        self.wheelhouse.mkdir()
        (self.wheelhouse / "demo-1.0-cp310-cp310-manylinux_2_17_aarch64.whl").write_bytes(wheel)

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                              check=True, text=True, timeout=20)

    def _write(self, relative: str, data: bytes) -> None:
        path = self.repo / Path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def _build(self, output: Path | None = None) -> tuple[Path, str]:
        bundle = output or (self.root / "runtime.tar.gz")
        digest = artifact.build_bundle(self.repo, self.sha, self.wheelhouse, bundle)
        return bundle, digest

    def test_build_is_sha_bound_deterministic_and_verifiable(self) -> None:
        committed = self.repo / "backend/app/platform_backup/production_cli.py"
        committed.write_text("# dirty working tree must not enter bundle\n", encoding="utf-8")
        first, first_digest = self._build(self.root / "one.tar.gz")
        second, second_digest = self._build(self.root / "two.tar.gz")
        self.assertEqual(first_digest, second_digest)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        manifest = artifact.verify_bundle(first.read_bytes(), self.sha, first_digest)
        self.assertEqual(manifest["source_sha"], self.sha)
        self.assertTrue(any(item["path"] == "backend/app/platform_backup/production_cli.py"
                            for item in manifest["files"]))
        self.assertNotIn(b"dirty working tree", first.read_bytes())

    def test_bundle_rejects_wrong_sha_digest_and_wheel_lock_divergence(self) -> None:
        bundle, digest = self._build()
        with self.assertRaisesRegex(artifact.ArtifactError, "bundle_digest_mismatch"):
            artifact.verify_bundle(bundle.read_bytes(), self.sha, "f" * 64)
        with self.assertRaisesRegex(artifact.ArtifactError, "source_sha_invalid"):
            artifact.verify_bundle(bundle.read_bytes(), "bad", digest)
        (self.wheelhouse / "demo-1.0-cp310-cp310-manylinux_2_17_aarch64.whl").write_bytes(b"changed")
        with self.assertRaisesRegex(artifact.ArtifactError, "wheel_hash_mismatch"):
            self._build(self.root / "invalid.tar.gz")

    def test_bundle_rejects_path_traversal_even_with_matching_digest(self) -> None:
        malicious = self._tar({"../outside": b"no", "manifest.json": b"{}\n"})
        with self.assertRaisesRegex(artifact.ArtifactError, "bundle_path_invalid"):
            artifact.verify_bundle(malicious, self.sha, hashlib.sha256(malicious).hexdigest())

    def test_bundle_rejects_symlink_tar_members(self) -> None:
        output = io.BytesIO()
        with (gzip.GzipFile(fileobj=output, mode="wb", mtime=0) as compressed,
              tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive):
            member = tarfile.TarInfo("manifest.json")
            member.type = tarfile.SYMTYPE
            member.linkname = "../secret"
            archive.addfile(member)
        malicious = output.getvalue()
        with self.assertRaisesRegex(artifact.ArtifactError, "bundle_entry_type_invalid"):
            artifact.verify_bundle(malicious, self.sha, hashlib.sha256(malicious).hexdigest())

    @staticmethod
    def _tar(files: dict[str, bytes]) -> bytes:
        output = io.BytesIO()
        with (gzip.GzipFile(fileobj=output, mode="wb", mtime=0) as compressed,
              tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive):
            for name, data in files.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        return output.getvalue()


if __name__ == "__main__":
    unittest.main()
