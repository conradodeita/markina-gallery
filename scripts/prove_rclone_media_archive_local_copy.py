#!/usr/bin/env python3
"""Bounded, local-only Rclone directory-copy interruption proof.

This tool is a disposable characterization harness, not a storage adapter.
It accepts only the pinned Windows amd64 Rclone v1.76.0 executable and runs
fixed `copy`, `lsf`, and `copy` readback commands against a temporary local
crypt remote. Raw child output and the generated synthetic crypt key are never
written to the evidence record or printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import random
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass

PINNED_VERSION = "rclone v1.76.0"
PINNED_BINARY_SHA256 = "acd80683e23151e93bbe0d6ffa74d26e542ec510332f630beecb9944f8d1a623"
MAX_DURATION = "1500ms"
COPY_TIMEOUT_SECONDS = 20
READ_TIMEOUT_SECONDS = 10
FIXTURE_COUNT = 64
FIXTURE_BYTES = 256 * 1024


@dataclass(frozen=True)
class ProcessResult:
    pid: int
    elapsed_ms: int
    returncode: int | None
    timed_out: bool
    terminated: bool
    killed: bool
    reaped: bool
    stdout_bytes: int
    stderr_bytes: int


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _clean_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("RCLONE_")}
    for key in ("SystemRoot", "WINDIR", "TEMP", "TMP"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def _run_child(
    executable: pathlib.Path,
    config_path: pathlib.Path,
    args: Sequence[str],
    *,
    timeout_seconds: int,
) -> tuple[ProcessResult, bytes, bytes]:
    command = [str(executable), "--config", str(config_path), *args]
    started = time.monotonic()
    try:
        child = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_clean_environment(),
            cwd=str(config_path.parent),
        )
    except OSError:
        now = time.monotonic()
        return (
            ProcessResult(0, int((now - started) * 1000), None, False, False, False, True, 0, 0),
            b"",
            b"",
        )

    terminated = False
    killed = False
    timed_out = False
    stdout = b""
    stderr = b""
    try:
        stdout, stderr = child.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        terminated = True
        child.terminate()
        try:
            stdout, stderr = child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            killed = True
            child.kill()
            stdout, stderr = child.communicate(timeout=3)

    elapsed = int((time.monotonic() - started) * 1000)
    result = ProcessResult(
        pid=child.pid,
        elapsed_ms=elapsed,
        returncode=child.returncode,
        timed_out=timed_out,
        terminated=terminated,
        killed=killed,
        reaped=child.poll() is not None,
        stdout_bytes=len(stdout),
        stderr_bytes=len(stderr),
    )
    return result, stdout, stderr


def _obscure(executable: pathlib.Path, config_path: pathlib.Path, value: str) -> str:
    result = subprocess.run(
        [str(executable), "--config", str(config_path), "obscure", value],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        env=_clean_environment(),
        cwd=str(config_path.parent),
        timeout=5,
        check=False,
    )
    encoded = result.stdout.decode("ascii", errors="strict").strip()
    if result.returncode != 0 or not encoded or "\n" in encoded or "\r" in encoded:
        raise RuntimeError("synthetic_config_creation_failed")
    return encoded


def _write_fixture(source_dir: pathlib.Path) -> dict[str, dict[str, int | str]]:
    source_dir.mkdir()
    manifest: dict[str, dict[str, int | str]] = {}
    for index in range(FIXTURE_COUNT):
        name = f"fixture-{index:03d}.bin"
        rng = random.Random(20261127 + index)
        payload = rng.randbytes(FIXTURE_BYTES)
        path = source_dir / name
        path.write_bytes(payload)
        manifest[name] = {"size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    return manifest


def _write_config(executable: pathlib.Path, root: pathlib.Path, config_path: pathlib.Path) -> None:
    backing = (root / "backing").resolve()
    backing.mkdir()
    windows_remote_path = backing.as_posix()
    password = f"synthetic-only-{uuid.uuid4().hex}"
    salt = f"synthetic-salt-{uuid.uuid4().hex}"
    obscured_password = _obscure(executable, config_path, password)
    obscured_salt = _obscure(executable, config_path, salt)
    config_path.write_text(
        "\n".join(
            (
                "[base]",
                "type = local",
                "",
                "[media]",
                "type = crypt",
                f"remote = base:{windows_remote_path}",
                "filename_encryption = standard",
                "directory_name_encryption = true",
                f"password = {obscured_password}",
                f"password2 = {obscured_salt}",
                "",
            )
        ),
        encoding="utf-8",
    )


def _require_local_only_config(config_path: pathlib.Path, temp_root: pathlib.Path) -> None:
    content = config_path.read_text(encoding="utf-8")
    if content.count("[") != 2 or "[base]" not in content or "[media]" not in content:
        raise RuntimeError("config_not_exact_local_crypt")
    if "type = local" not in content or "type = crypt" not in content:
        raise RuntimeError("config_not_exact_local_crypt")
    remote_line = next((line for line in content.splitlines() if line.startswith("remote = base:")), None)
    if remote_line is None:
        raise RuntimeError("config_not_exact_local_crypt")
    backing = pathlib.Path(remote_line.removeprefix("remote = base:")).resolve()
    if not backing.is_relative_to(temp_root.resolve()):
        raise RuntimeError("backing_path_outside_temp")


def _list_files(
    executable: pathlib.Path,
    config_path: pathlib.Path,
    remote_path: str,
) -> tuple[ProcessResult, list[str]]:
    result, stdout, _stderr = _run_child(
        executable,
        config_path,
        ["lsf", remote_path, "--recursive", "--files-only", "--format", "p"],
        timeout_seconds=READ_TIMEOUT_SECONDS,
    )
    if result.returncode != 0 or result.timed_out:
        return result, []
    names = [line.strip().replace("\\", "/") for line in stdout.decode("utf-8", errors="strict").splitlines() if line.strip()]
    return result, names


def _verify_readback(
    executable: pathlib.Path,
    config_path: pathlib.Path,
    remote_root: str,
    destination: pathlib.Path,
    expected: dict[str, dict[str, int | str]],
    names: list[str],
) -> tuple[ProcessResult, dict[str, str]]:
    readback_root = destination / "verified-readback"
    readback_result, _stdout, _stderr = _run_child(
        executable,
        config_path,
        ["copy", f"{remote_root}/", str(readback_root), "--transfers", "1", "--checkers", "1"],
        timeout_seconds=READ_TIMEOUT_SECONDS,
    )
    verified: dict[str, str] = {}
    if readback_result.returncode != 0 or readback_result.timed_out:
        return readback_result, verified
    for name in names:
        if pathlib.PurePosixPath(name).name != name or name not in expected:
            continue
        path = readback_root / name
        if not path.is_file() or path.stat().st_size > FIXTURE_BYTES:
            continue
        digest = _sha256_file(path)
        expected_row = expected[name]
        if path.stat().st_size == expected_row["size_bytes"] and digest == expected_row["sha256"]:
            verified[name] = digest
    return readback_result, verified


def _write_evidence(root: pathlib.Path, evidence: dict[str, object]) -> pathlib.Path:
    path = root / "evidence.json"
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rclone", required=True, help="caminho absoluto do executável Rclone v1.76.0 Windows amd64 já verificado")
    args = parser.parse_args()

    executable = pathlib.Path(args.rclone)
    if not executable.is_absolute() or not executable.is_file():
        print("status=blocked; code=invalid_binary_path")
        return 2
    executable = executable.resolve(strict=True)
    if _sha256_file(executable) != PINNED_BINARY_SHA256:
        print("status=blocked; code=binary_hash_mismatch")
        return 2
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    if executable.is_relative_to(repo_root):
        print("status=blocked; code=binary_must_remain_outside_repository")
        return 2

    version_result = subprocess.run(
        [str(executable), "version"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        env=_clean_environment(),
        timeout=5,
        check=False,
    )
    version = version_result.stdout.decode("utf-8", errors="replace").splitlines()
    if version_result.returncode != 0 or not version or version[0].strip() != PINNED_VERSION:
        print("status=blocked; code=binary_version_mismatch")
        return 2

    temp_base = pathlib.Path(tempfile.gettempdir()).resolve()
    root = pathlib.Path(tempfile.mkdtemp(prefix="pyp-rclone-dir-copy-proof-", dir=temp_base)).resolve()
    if not root.is_relative_to(temp_base):
        print("status=blocked; code=temp_root_outside_system_temp")
        return 2
    root_id = uuid.uuid4().hex
    config_path = root / "synthetic-rclone.conf"
    source_dir = root / "source"
    try:
        _write_config(executable, root, config_path)
        _require_local_only_config(config_path, root)
        expected = _write_fixture(source_dir)
    except (OSError, RuntimeError, subprocess.SubprocessError, UnicodeError):
        print("status=blocked; code=synthetic_setup_failed")
        return 2

    remote_root = f"media:proof-{root_id}"
    copy_args = [
        "--max-duration", MAX_DURATION,
        "--bwlimit", "1M",
        "--transfers", "1",
        "--checkers", "1",
        "--retries", "1",
        "--low-level-retries", "1",
        "copy", str(source_dir), f"{remote_root}/objects",
    ]
    copy_result, _copy_stdout, _copy_stderr = _run_child(
        executable,
        config_path,
        copy_args,
        timeout_seconds=COPY_TIMEOUT_SECONDS,
    )
    list_result, remote_names = _list_files(executable, config_path, f"{remote_root}/objects")
    readback_result, verified = _verify_readback(
        executable,
        config_path,
        remote_root + "/objects",
        root,
        expected,
        remote_names,
    )

    known_remote_names = [name for name in remote_names if pathlib.PurePosixPath(name).name in expected]
    unexpected_count = len(remote_names) - len(known_remote_names)
    source_count = len(expected)
    remote_count = len(known_remote_names)
    partial_batch = 0 < remote_count < source_count
    if copy_result.timed_out:
        outcome = "external_watchdog_timeout_uncertain"
        sanitized_code = "rclone_watchdog_timeout"
    elif copy_result.returncode == 10:
        outcome = "internal_max_duration_exit"
        sanitized_code = "rclone_max_duration"
    elif copy_result.returncode == 0:
        outcome = "completed_before_deadline"
        sanitized_code = None
    else:
        outcome = "nonzero_exit_uncertain"
        sanitized_code = "rclone_copy_failed"

    evidence: dict[str, object] = {
        "schema_version": 1,
        "rclone_version": version[0].strip(),
        "rclone_binary_sha256": PINNED_BINARY_SHA256,
        "config_model": "local_base_plus_crypt_remote_only",
        "rclone_environment_overrides_removed": True,
        "command": "rclone copy <synthetic-directory> media:proof-<opaque>/objects",
        "flags": {
            "max_duration": MAX_DURATION,
            "bwlimit": "1M",
            "transfers": 1,
            "retries": 1,
            "low_level_retries": 1,
            "external_timeout_seconds": COPY_TIMEOUT_SECONDS,
        },
        "fixture": {
            "file_count": source_count,
            "file_size_bytes": FIXTURE_BYTES,
            "total_size_bytes": source_count * FIXTURE_BYTES,
            "sha256_by_file": {name: row["sha256"] for name, row in expected.items()},
        },
        "copy_process": asdict(copy_result),
        "listing_process": asdict(list_result),
        "readback_process": asdict(readback_result),
        "destination": {
            "known_file_count": remote_count,
            "unexpected_entry_count": unexpected_count,
            "partial_batch": partial_batch,
            "verified_complete_file_count": len(verified),
            "verified_names": sorted(verified),
        },
        "outcome": outcome,
        "sanitized_error_code": sanitized_code,
        "raw_stdout_stderr_saved": False,
        "config_and_crypt_key_saved_in_evidence": False,
        "network_drive_database_production_access": False,
        "temp_root_retained_for_review": str(root),
    }
    evidence_path = _write_evidence(root, evidence)
    print(f"status=observed; outcome={outcome}; sanitized_code={sanitized_code or 'none'}")
    print(
        f"copy_pid={copy_result.pid}; exit={copy_result.returncode}; "
        f"timeout={copy_result.timed_out}; terminated={copy_result.terminated}; "
        f"killed={copy_result.killed}; reaped={copy_result.reaped}; "
        f"elapsed_ms={copy_result.elapsed_ms}"
    )
    print(
        f"source_files={source_count}; remote_files={remote_count}; verified_files={len(verified)}; "
        f"partial_batch={partial_batch}; unexpected_entries={unexpected_count}"
    )
    print(f"stdout_stderr_discarded=true; evidence={evidence_path}")

    if not copy_result.reaped or list_result.returncode != 0 or readback_result.returncode != 0:
        return 3
    if outcome != "internal_max_duration_exit" or not partial_batch or len(verified) != remote_count or unexpected_count:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
