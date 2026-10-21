"""Build and homologate an ARM64 API candidate without replacing services."""
from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

PINS = {"aiohttp": "3.14.4", "multidict": "6.9.1", "urllib3": "2.8.0", "yarl": "1.25.1"}
METADATA = "import importlib.metadata as m,json,platform;print(json.dumps({'python':platform.python_version(),'packages':{d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions()}}))"
STARTUP = """
from app.auth import Base,engine
Base.metadata.create_all(engine)
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    assert client.get('/health').status_code == 200
    assert client.get('/admin/clients').status_code == 403
print('synthetic_api_startup=passed')
"""


def maintenance_configuration(server):
    if server.count("server {") != 1:
        raise ValueError("expected single project server")
    guarded = server.replace("server {", 'server {\n    if ($uri !~ "^/(healthz|api/health|api/infinitepay/return)$") { return 503; }', 1)
    return "worker_processes auto;\nevents { worker_connections 1024; }\nhttp {\n" + guarded + "\n}\n"


def maintenance(mode, sha, backup):
    container = "markina-gallery-nginx-1"
    marker = backup.with_suffix(".active")
    if mode == "finish":
        if not marker.exists():
            return
        subprocess.run(["docker", "cp", str(backup), container + ":/etc/nginx/nginx.conf"], check=True)
        subprocess.run(["docker", "exec", container, "nginx", "-t"], check=True)
        subprocess.run(["docker", "exec", container, "nginx", "-s", "reload"], check=True)
        marker.unlink()
        print("maintenance=finished")
        return
    if backup.exists() or marker.exists():
        raise ValueError("maintenance backup already exists; inspect before retry")
    source = output("git", "show", sha + ":docker/nginx/nginx.conf")
    config = maintenance_configuration(source)
    subprocess.run(["docker", "cp", container + ":/etc/nginx/nginx.conf", str(backup)], check=True)
    try:
        subprocess.run(["docker", "exec", "-i", container, "sh", "-c", "cat > /etc/nginx/nginx.conf"],
                       input=config.encode(), check=True)
        subprocess.run(["docker", "exec", container, "nginx", "-t"], check=True)
        subprocess.run(["docker", "exec", container, "nginx", "-s", "reload"], check=True)
        for _ in range(20):
            status = output("curl", "--silent", "--max-time", "2", "--output", "/dev/null",
                            "--write-out", "%{http_code}", "http://127.0.0.1:8080/admin")
            if status == "503":
                break
            time.sleep(0.1)
        else:
            raise ValueError("maintenance ingress did not return 503")
        marker.write_text(sha, encoding="utf-8")
        print("maintenance=started financial_return=preserved other_ingress=503")
    except (subprocess.CalledProcessError, ValueError):
        subprocess.run(["docker", "cp", str(backup), container + ":/etc/nginx/nginx.conf"], check=True)
        subprocess.run(["docker", "exec", container, "nginx", "-t"], check=True)
        subprocess.run(["docker", "exec", container, "nginx", "-s", "reload"], check=True)
        raise


def validate_packages(before, after):
    if before["python"] != "3.13.16" or after["python"] != before["python"]:
        raise ValueError("Python base changed")
    expected = {**before["packages"], **PINS}
    if after["packages"] != expected:
        raise ValueError("distribution drift outside four approved pins")


def output(*args):
    return subprocess.check_output(list(args), text=True).strip()


def isolated(image, code):
    return output("docker", "run", "--rm", "--platform", "linux/arm64", "--network", "none",
                  "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                  "--memory", "1g", "--cpus", "1", "--pids-limit", "128",
                  "--tmpfs", "/tmp:rw,nosuid,size=256m", "-e", "PYTHONDONTWRITEBYTECODE=1",
                  "-e", "APP_ENV=test", "-e", "DATABASE_URL=sqlite:////tmp/startup.sqlite",
                  "-e", "GALLERY_CAPABILITY_SIGNING_KEY=synthetic-only-capability-key-32-bytes-long",
                  "--entrypoint", "python", image, "-B", "-c", code)


def extract_source(archive, root):
    """Git-only regular files; compatible with the host's Python 3.8."""
    with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
        for member in contents:
            if member.isdir():
                continue
            path = Path(member.name)
            if (not member.isfile() or path.is_absolute() or ".." in path.parts
                    or not (member.name.startswith("backend/app/") or member.name == "backend/requirements-push.txt")):
                raise ValueError("source archive contains an unapproved path")
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents.extractfile(member).read())


def prepare(previous, sha, receipt):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", previous) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("immutable identity required")
    if output("git", "rev-parse", "HEAD") != sha or output("git", "status", "--porcelain"):
        raise ValueError("approved clean checkout required")
    if output("docker", "image", "inspect", "--format", "{{.Architecture}}", previous) != "arm64":
        raise ValueError("ARM64 baseline required")
    before = json.loads(isolated(previous, METADATA))
    base_tag = "markina-gallery-emergency-base:" + previous[7:]
    tag = "markina-gallery-emergency-api:" + sha
    subprocess.run(["docker", "image", "tag", previous, base_tag], check=True)
    archive = subprocess.check_output(["git", "archive", sha, "backend/app", "backend/requirements-push.txt"])
    with tempfile.TemporaryDirectory(prefix="pyp-emergency-api-") as folder:
        root = Path(folder)
        extract_source(archive, root)
        pins = " ".join(p + "==" + v for p, v in PINS.items())
        (root / "Dockerfile").write_text(
            "FROM " + base_tag + "\nRUN python -m pip install --no-cache-dir --no-deps --only-binary=:all: "
            + pins + "\nCOPY backend/app /app/app\nCOPY backend/requirements-push.txt /app/requirements-push.txt\n",
            encoding="utf-8")
        subprocess.run(["docker", "build", "--platform", "linux/arm64", "-t", tag, folder], check=True)
    candidate = output("docker", "image", "inspect", "--format", "{{.Id}}", tag)
    after = json.loads(isolated(candidate, METADATA))
    validate_packages(before, after)
    isolated(candidate, "import subprocess;subprocess.run(['python','-m','pip','check'],check=True)")
    isolated(candidate, STARTUP)
    receipt.write_text(json.dumps({"sha": sha, "previous": previous, "candidate": candidate,
                                  "python": after["python"], "pins": PINS,
                                  "distribution_comparison": "passed", "arm64_startup": "passed"}), encoding="utf-8")
    # Update the Compose image reference only after every validation passed.
    subprocess.run(["docker", "image", "tag", candidate, "markina-gallery-api"], check=True)
    print("api_candidate_homologated=" + candidate)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous")
    parser.add_argument("--sha", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--maintenance", choices=("start", "finish"))
    args = parser.parse_args()
    if args.maintenance:
        maintenance(args.maintenance, args.sha, args.receipt)
    else:
        prepare(args.previous, args.sha, args.receipt)
