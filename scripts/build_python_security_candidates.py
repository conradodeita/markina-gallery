"""Local ARM64 overlay preparation. Never contacts SSH or a production daemon."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

if __package__:
    from .python_security_release import (
        ORDER,
        PINS,
        Blocked,
        image_id,
        validate_candidate,
    )
else:
    from python_security_release import (
        ORDER,
        PINS,
        Blocked,
        image_id,
        validate_candidate,
    )

DOCKER = ["docker", "--context", "desktop-linux"]
RESERVE = 2 * 1024**3
METADATA = "import importlib.metadata as m,json,platform;from pathlib import Path;pins=dict(line.split('==',1) for line in Path('/app/requirements-push.txt').read_text().splitlines() if '==' in line);print(json.dumps({'python':platform.python_version(),'packages':{d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions()},'embedded_pins':{p:pins.get(p) for p in ['aiohttp','multidict','urllib3','yarl']}}))"


def run(*args):
    return subprocess.check_output([*DOCKER, *args], text=True).strip()


def isolated(image, *command):
    return run("run", "--rm", "--platform", "linux/arm64", "--network", "none", "--read-only", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges", "--memory", "1g", "--cpus", "1",
               "--pids-limit", "128", "--tmpfs", "/tmp:rw,nosuid,size=64m",
               "-e", "PYTHONDONTWRITEBYTECODE=1", "--entrypoint", "python", image, *command)


def ensure_local_daemon():
    endpoint = run("context", "inspect", "desktop-linux", "--format", '{{(index .Endpoints "docker").Host}}')
    if not endpoint.startswith(("npipe://", "unix://")):
        raise Blocked("candidate builds require a local Docker socket")


def imported_baseline(baseline):
    """Docker classic uses config IDs; containerd may expose a manifest ID.

    Verify the opaque config's hash from a local export, never its environment.
    Only inspect/export local candidates with the exact inventoried layer list.
    """
    for candidate in set(run("image", "ls", "--all", "--no-trunc", "--format", "{{.ID}}").splitlines()):
        layers = json.loads(run("image", "inspect", "--format", "{{json .RootFS.Layers}}", candidate))
        if layers != baseline["layers"]:
            continue
        if candidate == baseline["image_id"]:
            return candidate
        process = subprocess.Popen([*DOCKER, "image", "save", candidate], stdout=subprocess.PIPE)
        hashes, manifest = {}, None
        try:
            with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
                for member in archive:
                    if member.name == "manifest.json":
                        manifest = json.loads(archive.extractfile(member).read())
                    elif member.isfile() and member.size < 4 * 1024**2:
                        # No decoding or printing of image config or application files.
                        hashes[member.name] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
            code = process.wait()
        finally:
            process.stdout.close()
        if code == 0 and manifest and any("sha256:" + hashes.get(item["Config"], "") == baseline["image_id"] for item in manifest):
            return candidate
    raise Blocked("exact baseline config not imported into local daemon")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baselines", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--services", nargs="+", choices=ORDER, required=True)
    args = parser.parse_args()
    ensure_local_daemon()
    baselines = json.loads(args.baselines.read_text())
    result = json.loads(args.output.read_text()) if args.output.exists() else {}
    for service in args.services:
        baseline = baselines[service]
        previous = image_id(baseline["image_id"])
        try:
            if shutil.disk_usage(args.output.parent).free < RESERVE + 256 * 1024**2:
                raise Blocked("local disk reserve would be exhausted")
            local_base = imported_baseline(baseline)
            existing = json.loads(run("image", "inspect", "--format", "{{json .RootFS.Layers}}", local_base))
            if existing != baseline["layers"]:
                raise Blocked("imported baseline layers differ")
            tag = "markina-gallery-python-validation:" + service + "-" + previous[7:19]
            base_tag = "markina-gallery-python-baseline:" + previous[7:]
            run("image", "tag", local_base, base_tag)
            with tempfile.TemporaryDirectory(prefix="pyp-python-security-") as folder:
                pins = " ".join(p + "==" + v for p, v in PINS.items())
                root = Path(__file__).resolve().parents[1]
                manifest = subprocess.check_output(["git", "show", "HEAD:backend/requirements-push.txt"], cwd=root)
                if not all((p + "==" + v).encode() in manifest.splitlines() for p, v in PINS.items()):
                    raise Blocked("approved embedded manifest has different pins")
                Path(folder, "approved-requirements-push.txt").write_bytes(manifest)
                Path(folder, "Dockerfile").write_text(
                    "FROM " + base_tag + "\nRUN python -m pip install --no-cache-dir --no-deps --only-binary=:all: " + pins + "\nCOPY approved-requirements-push.txt /app/requirements-push.txt\n",
                    encoding="utf-8",
                )
                subprocess.run([*DOCKER, "build", "--platform", "linux/arm64", "-t", tag, folder], check=True)
            image = image_id(run("image", "inspect", "--format", "{{.Id}}", tag))
            info = json.loads(isolated(image, "-B", "-c", METADATA))
            info.update(image_id=image, architecture=run("image", "inspect", "--format", "{{.Architecture}}", image),
                        layers=json.loads(run("image", "inspect", "--format", "{{json .RootFS.Layers}}", image)))
            isolated(image, "-B", "-m", "pip", "check")
            info["pip_check"] = 0
            validate_candidate(baseline, info)
            isolated(image, "-B", "-c", "import aiohttp,multidict,urllib3,yarl; assert str(yarl.URL('https://example.invalid/a').with_query(k='synthetic')).endswith('?k=synthetic')")
            result[service] = {**info, "base_image_id": previous, "imported_local_image_id": local_base,
                               "validated": True, "local_only": True,
                               "startup_homologated": False, "operationally_available_in_oracle": False}
        except (Blocked, subprocess.CalledProcessError, OSError, tarfile.TarError) as error:
            result[service] = {"validated": False, "base_image_id": previous, "blocker": str(error)}
        args.output.write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")
    return 0 if all(result[s]["validated"] for s in args.services) else 1


if __name__ == "__main__":
    raise SystemExit(main())
