"""Build and verify the immutable, offline Pick-your-Pic backup runtime bundle."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from collections.abc import Iterable
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = "scripts/backup_runtime/requirements-py310-arm64.lock"
SERVICE_PATHS = {
    "scripts/backup_runtime/pyp-platform-backup.service",
    "scripts/backup_runtime/pyp-platform-backup.timer",
}
MAX_BUNDLE_BYTES = 768 * 1024 * 1024
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_FILE_COUNT = 10_000
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
LOCK_LINE = re.compile(
    r"(?P<name>[A-Za-z0-9][A-Za-z0-9_.-]*)==(?P<version>[A-Za-z0-9][A-Za-z0-9.!+_-]*) "
    r"--hash=sha256:(?P<sha256>[0-9a-f]{64})\Z"
)


class ArtifactError(ValueError):
    """Sanitized error for an invalid package or artifact input."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def parse_lock(data: bytes) -> dict[str, tuple[str, str]]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ArtifactError("lock_not_utf8") from exc
    packages: dict[str, tuple[str, str]] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = LOCK_LINE.fullmatch(stripped)
        _require(match is not None, "lock_line_invalid")
        name = _normalize_name(match["name"])
        _require(name not in packages, "lock_package_duplicate")
        packages[name] = (match["version"], match["sha256"])
    _require(bool(packages), "lock_empty")
    return packages


def _wheel_identity(filename: str) -> tuple[str, str, str, str, str]:
    _require(filename.endswith(".whl") and Path(filename).name == filename, "wheel_name_invalid")
    parts = filename[:-4].split("-")
    _require(len(parts) in {5, 6}, "wheel_name_invalid")
    if len(parts) == 5:
        distribution, version, python_tag, abi_tag, platform_tag = parts
    else:
        distribution, version, _build_tag, python_tag, abi_tag, platform_tag = parts
    _require(bool(distribution and version and python_tag and abi_tag and platform_tag), "wheel_name_invalid")
    py_tags, abi_tags, platform_tags = python_tag.split("."), abi_tag.split("."), platform_tag.split(".")
    _require(set(py_tags) <= {"cp310", "cp39", "cp38", "cp37", "py3"}, "wheel_python_tag_invalid")
    _require(set(abi_tags) <= {"cp310", "abi3", "none"}, "wheel_abi_tag_invalid")
    _require(all(tag == "any" or (tag.startswith("manylinux") and tag.endswith("_aarch64"))
                for tag in platform_tags), "wheel_platform_tag_invalid")
    _require("any" not in platform_tags or platform_tags == ["any"], "wheel_platform_tag_invalid")
    return _normalize_name(distribution), version, python_tag, abi_tag, platform_tag


def _source_paths(repository: Path, source_sha: str) -> list[str]:
    _require(bool(GIT_SHA.fullmatch(source_sha)), "source_sha_invalid")
    commit = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", f"{source_sha}^{{commit}}"],
        check=False, capture_output=True, text=True, timeout=20,
    )
    _require(commit.returncode == 0 and commit.stdout.strip() == source_sha, "source_commit_unavailable")
    result = subprocess.run(
        ["git", "-C", str(repository), "ls-tree", "-r", "--format=%(objectmode)%x09%(path)", source_sha, "--",
         "backend/app", "scripts/backup_runtime"],
        check=False, capture_output=True, text=True, timeout=20,
    )
    _require(result.returncode == 0, "source_tree_unavailable")
    paths = []
    for raw in result.stdout.splitlines():
        try:
            mode, path = raw.split("\t", 1)
        except ValueError as exc:
            raise ArtifactError("source_tree_entry_invalid") from exc
        path = path.replace("\\", "/")
        if ((path.startswith("backend/app/") and path.endswith(".py"))
                or path == LOCK_PATH or path in SERVICE_PATHS):
            _require(mode in {"100644", "100755"}, "source_file_type_invalid")
            paths.append(path)
    _require(LOCK_PATH in paths and SERVICE_PATHS <= set(paths), "source_runtime_files_missing")
    _require(len(paths) <= MAX_FILE_COUNT, "source_file_count_exceeded")
    return sorted(set(paths))


def _git_blob(repository: Path, source_sha: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), "show", f"{source_sha}:{path}"],
        check=False, capture_output=True, timeout=20,
    )
    _require(result.returncode == 0 and len(result.stdout) <= MAX_FILE_BYTES, "source_blob_invalid")
    return result.stdout


def _wheelhouse_files(wheelhouse: Path, lock: dict[str, tuple[str, str]]) -> dict[str, bytes]:
    _require(wheelhouse.is_dir() and not wheelhouse.is_symlink(), "wheelhouse_invalid")
    wheels: dict[str, bytes] = {}
    for path in sorted(wheelhouse.iterdir(), key=lambda item: item.name):
        _require(path.is_file() and not path.is_symlink(), "wheelhouse_entry_invalid")
        name, version, *_ = _wheel_identity(path.name)
        _require(name in lock and name not in wheels, "wheel_not_locked_or_duplicate")
        expected_version, expected_digest = lock[name]
        data = path.read_bytes()
        _require(0 < len(data) <= MAX_FILE_BYTES, "wheel_size_invalid")
        _require(version == expected_version and _sha256(data) == expected_digest, "wheel_hash_mismatch")
        wheels[name] = data
    _require(set(wheels) == set(lock), "wheelhouse_incomplete")
    return {next(path.name for path in wheelhouse.iterdir()
                 if _normalize_name(_wheel_identity(path.name)[0]) == package): data
            for package, data in wheels.items()}


def _manifest(source_sha: str, lock_data: bytes, files: dict[str, bytes]) -> bytes:
    document = {
        "schema_version": 1,
        "source_sha": source_sha,
        "lock_sha256": _sha256(lock_data),
        "files": [
            {"path": name, "size": len(data), "sha256": _sha256(data)}
            for name, data in sorted(files.items())
        ],
    }
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _unit_sections(data: bytes) -> dict[str, list[str]]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ArtifactError("unit_file_encoding_invalid") from exc
    sections: dict[str, list[str]] = {}
    active = None
    for line in lines:
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if value.startswith("[") and value.endswith("]"):
            active = value[1:-1]
            _require(active not in sections, "unit_section_duplicate")
            sections[active] = []
            continue
        _require(active is not None and "=" in value, "unit_directive_invalid")
        sections[active].append(value)
    return sections


def _validate_unit_files(files: dict[str, bytes]) -> None:
    service = _unit_sections(files["scripts/backup_runtime/pyp-platform-backup.service"])
    timer = _unit_sections(files["scripts/backup_runtime/pyp-platform-backup.timer"])
    expected_service = {
        "Unit": ["Description=Backup global cifrado do Pick-your-Pic", "Wants=network-online.target",
                 "After=network-online.target docker.service",
                 "ConditionPathExists=/etc/pyp-backup/keyring.json",
                 "ConditionPathExists=/etc/pyp-backup/destination.json"],
        "Service": ["Type=oneshot", "User=root", "Group=root",
                    "WorkingDirectory=/opt/pyp-backup-runtime/current", "Environment=APP_ENV=production",
                    "Environment=PYTHONPATH=/opt/pyp-backup-runtime/current/backend",
                    "Environment=PYTHONDONTWRITEBYTECODE=1",
                    "ExecStart=/opt/pyp-backup-runtime/current/venv/bin/python -m app.platform_backup.production_cli",
                    "UMask=0077", "NoNewPrivileges=true", "PrivateTmp=true", "ProtectSystem=strict",
                    "ProtectHome=true", "StateDirectory=pyp-backup", "StateDirectoryMode=0700",
                    "CPUQuota=35%", "MemoryMax=512M", "TimeoutStartSec=20min"],
    }
    expected_timer = {
        "Unit": ["Description=Agenda diária do backup global Pick-your-Pic"],
        "Timer": ["OnCalendar=*-*-* 08:30:00 UTC", "Persistent=true", "Unit=pyp-platform-backup.service"],
        "Install": ["WantedBy=timers.target"],
    }
    _require(service == expected_service and timer == expected_timer, "systemd_unit_contract_invalid")


def build_bundle(repository: Path, source_sha: str, wheelhouse: Path, output: Path) -> str:
    paths = _source_paths(repository, source_sha)
    files = {path: _git_blob(repository, source_sha, path) for path in paths}
    lock_data = files[LOCK_PATH]
    lock = parse_lock(lock_data)
    wheels = _wheelhouse_files(wheelhouse, lock)
    for filename, data in wheels.items():
        files[f"wheelhouse/{filename}"] = data
    manifest = _manifest(source_sha, lock_data, files)
    _require(len(files) + 1 <= MAX_FILE_COUNT, "bundle_file_count_exceeded")
    output.parent.mkdir(parents=True, exist_ok=True)
    with (output.open("wb") as raw,
          gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=9) as compressed,
          tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive):
        for name, data in sorted({**files, "manifest.json": manifest}.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o444
            archive.addfile(info, io.BytesIO(data))
    size = output.stat().st_size
    _require(0 < size <= MAX_BUNDLE_BYTES, "bundle_size_exceeded")
    return _sha256(output.read_bytes())


def verify_bundle(data: bytes, source_sha: str, expected_bundle_sha256: str) -> dict[str, object]:
    _require(len(data) <= MAX_BUNDLE_BYTES and len(data) > 0, "bundle_size_invalid")
    _require(bool(GIT_SHA.fullmatch(source_sha)), "source_sha_invalid")
    _require(bool(SHA256.fullmatch(expected_bundle_sha256)), "bundle_digest_invalid")
    _require(_sha256(data) == expected_bundle_sha256, "bundle_digest_mismatch")
    content: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            members = archive.getmembers()
            _require(0 < len(members) <= MAX_FILE_COUNT, "bundle_file_count_invalid")
            for member in members:
                path = member.name
                _require(path not in content and not member.isdir() and member.isfile(), "bundle_entry_type_invalid")
                _require(path and not path.startswith("/") and ".." not in Path(path).parts
                         and "\\" not in path, "bundle_path_invalid")
                _require(member.size <= MAX_FILE_BYTES, "bundle_file_size_invalid")
                stream = archive.extractfile(member)
                _require(stream is not None, "bundle_entry_unreadable")
                raw = stream.read(MAX_FILE_BYTES + 1)
                _require(len(raw) == member.size and len(raw) <= MAX_FILE_BYTES, "bundle_entry_size_mismatch")
                content[path] = raw
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise ArtifactError("bundle_archive_invalid") from exc
    manifest_raw = content.get("manifest.json")
    _require(manifest_raw is not None and len(manifest_raw) <= 2_000_000, "bundle_manifest_missing")
    try:
        manifest = json.loads(manifest_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactError("bundle_manifest_invalid") from exc
    _require(isinstance(manifest, dict) and set(manifest) == {"schema_version", "source_sha", "lock_sha256", "files"}
             and manifest.get("schema_version") == 1 and manifest.get("source_sha") == source_sha
             and isinstance(manifest.get("lock_sha256"), str) and SHA256.fullmatch(manifest["lock_sha256"])
             and isinstance(manifest.get("files"), list), "bundle_manifest_invalid")
    expected_files: dict[str, tuple[int, str]] = {}
    for entry in manifest["files"]:
        _require(isinstance(entry, dict) and set(entry) == {"path", "size", "sha256"}
                 and isinstance(entry.get("path"), str) and type(entry.get("size")) is int
                 and entry["size"] >= 0 and isinstance(entry.get("sha256"), str)
                 and SHA256.fullmatch(entry["sha256"]), "bundle_manifest_entry_invalid")
        path = entry["path"]
        _require(path not in expected_files and ((path.startswith("backend/app/") and path.endswith(".py"))
                 or path == LOCK_PATH or path in SERVICE_PATHS or path.startswith("wheelhouse/")),
                 "bundle_manifest_path_invalid")
        expected_files[path] = (entry["size"], entry["sha256"])
    _require(set(content) == set(expected_files) | {"manifest.json"}, "bundle_file_set_mismatch")
    for path, (size, digest) in expected_files.items():
        _require(len(content[path]) == size and _sha256(content[path]) == digest, "bundle_file_hash_mismatch")
    lock_data = content.get(LOCK_PATH)
    _require(lock_data is not None and _sha256(lock_data) == manifest["lock_sha256"], "bundle_lock_hash_mismatch")
    lock = parse_lock(lock_data)
    wheel_paths = {name.removeprefix("wheelhouse/"): raw for name, raw in content.items()
                   if name.startswith("wheelhouse/")}
    wheel_lock: dict[str, bytes] = {}
    for filename, raw in wheel_paths.items():
        name, version, *_ = _wheel_identity(filename)
        _require(name in lock and name not in wheel_lock, "bundle_wheel_invalid")
        locked_version, locked_sha = lock[name]
        _require(version == locked_version and _sha256(raw) == locked_sha, "bundle_wheel_hash_mismatch")
        wheel_lock[name] = raw
    _require(set(wheel_lock) == set(lock), "bundle_wheelhouse_incomplete")
    _require(SERVICE_PATHS <= set(content), "bundle_service_files_missing")
    _validate_unit_files(content)
    return manifest


def _main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--sha", required=True)
    build.add_argument("--wheelhouse", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--sha", required=True)
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--bundle-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == "build":
            digest = build_bundle(REPOSITORY_ROOT, args.sha, args.wheelhouse, args.output)
            print(json.dumps({"source_sha": args.sha, "bundle_sha256": digest}, sort_keys=True))
        else:
            manifest = verify_bundle(args.bundle.read_bytes(), args.sha, args.bundle_sha256)
            print(json.dumps({"source_sha": manifest["source_sha"],
                              "bundle_sha256": _sha256(args.bundle.read_bytes()),
                              "file_count": len(manifest["files"])}, sort_keys=True))
        return 0
    except (ArtifactError, OSError, subprocess.SubprocessError):
        print("platform-backup-runtime: artifact operation failed", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
