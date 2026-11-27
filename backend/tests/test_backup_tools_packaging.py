from __future__ import annotations

import hashlib
import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read_lock() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / "backend" / "backup-tools.lock").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, raw_value = line.split("=", maxsplit=1)
        assert re.fullmatch(r"[A-Z][A-Z0-9_]*", name)
        assert name not in values
        parsed = shlex.split(raw_value)
        assert len(parsed) == 1
        values[name] = parsed[0]
    return values


def test_backup_tool_lock_pins_official_releases_for_supported_architectures() -> None:
    lock = _read_lock()
    assert lock["RESTIC_VERSION"] == "0.20.0"
    assert lock["RESTIC_LICENSE"] == "BSD-2-Clause"
    assert lock["RESTIC_RELEASE_BASE"] == (
        "https://github.com/restic/restic/releases/download/v0.20.0"
    )
    assert lock["RESTIC_LICENSE_SOURCE"] == (
        "https://github.com/restic/restic/blob/v0.20.0/LICENSE"
    )
    assert lock["RESTIC_LINUX_AMD64_ASSET"] == "restic_0.20.0_linux_amd64.bz2"
    assert lock["RESTIC_LINUX_AMD64_SHA256"] == (
        "0ccd9fa7885074a24603b051e01bf9bd8b5e45d6a1791e9d9887e9e9372107f7"
    )
    assert lock["RESTIC_LINUX_ARM64_ASSET"] == "restic_0.20.0_linux_arm64.bz2"
    assert lock["RESTIC_LINUX_ARM64_SHA256"] == (
        "1188daded239bccb5952a01d2ad33e77a0d3dc34f9d9fc1e7fdda618d44938ef"
    )

    assert lock["RCLONE_VERSION"] == "1.76.0"
    assert lock["RCLONE_LICENSE"] == "MIT"
    assert lock["RCLONE_RELEASE_BASE"] == (
        "https://github.com/rclone/rclone/releases/download/v1.76.0"
    )
    assert lock["RCLONE_LICENSE_SOURCE"] == (
        "https://github.com/rclone/rclone/blob/v1.76.0/COPYING"
    )
    assert lock["RCLONE_LINUX_AMD64_ASSET"] == "rclone-v1.76.0-linux-amd64.zip"
    assert lock["RCLONE_LINUX_AMD64_SHA256"] == (
        "b00f00b3266c3764413afe599d3ec316f6f43b3e0ea8a0bc1d186d2133e46df7"
    )
    assert lock["RCLONE_LINUX_ARM64_ASSET"] == "rclone-v1.76.0-linux-arm64.zip"
    assert lock["RCLONE_LINUX_ARM64_SHA256"] == (
        "ee169016675e23a69d77240565133ff7dbc9b33d16fa8f7053d4af39f1eaeb78"
    )
    assert lock["POSTGRESQL_CLIENT_PACKAGE"] == "postgresql-client-17"
    assert lock["POSTGRESQL_CLIENT_VERSION"] == "17.12"
    assert lock["POSTGRESQL_CLIENT_PACKAGE_VERSION"] == "17.12-1.pgdg13+1"
    assert lock["POSTGRESQL_CLIENT_LICENSE"] == "PostgreSQL License"
    assert lock["POSTGRESQL_CLIENT_LICENSE_SOURCE"] == ("https://www.postgresql.org/about/licence/")
    assert lock["POSTGRESQL_CLIENT_AMD64_SHA256"] == (
        "4a8a530be4a549753bd82bec2a5032e91233c6a60ebeb1ca5311717866de4059"
    )
    assert lock["POSTGRESQL_CLIENT_ARM64_SHA256"] == (
        "b048ca8930a7e386ced747f2635ad950edcfc2e70b5584de66e1dc9e31e53636"
    )
    assert lock["PGDG_REPOSITORY"] == "https://apt.postgresql.org/pub/repos/apt"
    assert lock["PGDG_SUITE"] == "trixie-pgdg"
    assert lock["PGDG_DEBIAN_CODENAME"] == "trixie"
    assert lock["PGDG_KEY_FINGERPRINT"] == "B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8"
    assert re.fullmatch(r"[0-9a-f]{64}", lock["PGDG_KEY_SHA256"])

    for name, value in lock.items():
        if name.endswith("SHA256"):
            assert re.fullmatch(r"[0-9a-f]{64}", value)


def test_backup_tool_license_notices_match_the_versioned_source_files() -> None:
    licenses = {
        "restic-LICENSE": "6f08a01a9fab5b24e139a09f15cc24a73087c7bc09e3bacf099fdf2d767bf897",
        "rclone-COPYING": "9266eae9c6a441de0f6847f19ac8f09b280d55612b079eca03b3d49b822c1a71",
    }
    for name, expected in licenses.items():
        path = ROOT / "backend" / "licenses" / "backup-tools" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def test_only_the_worker_target_receives_backup_tools() -> None:
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text()
    compose = (ROOT / "docker" / "docker-compose.yml").read_text()
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    smoke = (ROOT / "scripts" / "smoke_backup_worker_tools.sh").read_text()

    assert "FROM python:3.13-slim AS backup-tools-build" in dockerfile
    assert "FROM backend-runtime-base AS backup-worker" in dockerfile
    assert 'LABEL com.markina-gallery.build-target="backup-worker"' in dockerfile
    assert "postgresql_client_unsupported_architecture" in dockerfile
    assert (
        'apt-get download "$POSTGRESQL_CLIENT_PACKAGE=$POSTGRESQL_CLIENT_PACKAGE_VERSION"'
        in dockerfile
    )
    assert "POSTGRESQL_CLIENT_AMD64_SHA256" in dockerfile
    assert "POSTGRESQL_CLIENT_ARM64_SHA256" in dockerfile
    assert 'case "$pg_dump_version" in' in dockerfile
    assert 'case "$pg_restore_version" in' in dockerfile
    assert "postgresql_client_pg_dump_version_mismatch" in dockerfile
    assert "postgresql_client_pg_restore_version_mismatch" in dockerfile
    assert "COPY --from=backup-tools-build /usr/local/bin/restic" in dockerfile
    assert "COPY --from=backup-tools-build /usr/local/bin/rclone" in dockerfile
    assert dockerfile.rfind("FROM backend-runtime-base AS api-runtime") > dockerfile.index(
        "FROM backend-runtime-base AS backup-worker"
    )

    worker = re.search(r"(?ms)^  worker:\n(.*?)(?=^  [a-z0-9_-]+:\n|\Z)", compose)
    api = re.search(r"(?ms)^  api:\n(.*?)(?=^  [a-z0-9_-]+:\n|\Z)", compose)
    migrate = re.search(r"(?ms)^  migrate:\n(.*?)(?=^  [a-z0-9_-]+:\n|\Z)", compose)
    assert worker is not None and "target: backup-worker" in worker.group(1)
    assert api is not None and "target:" not in api.group(1)
    assert migrate is not None and "target:" not in migrate.group(1)
    assert "--target backup-worker" in workflow
    assert "--network none --read-only" in workflow
    assert ". /usr/share/doc/pyp-backup-tools/backup-tools.lock" in smoke
    assert "pg_dump --version" in smoke and "pg_restore --version" in smoke
    assert "restic init" in smoke and "restic check --read-data" in smoke
