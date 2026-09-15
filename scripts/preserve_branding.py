"""Conservative branding backup/transfer. No secrets, SQL writes or source deletion."""

import argparse
import base64
import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PROJECT = "markina-gallery"
VOLUME = "markina-gallery_branding-assets"
ROOT = "/var/lib/markina/branding"
BACKUPS = Path("/var/lib/markina-gallery/backups")
STATE = Path("/var/lib/markina-gallery/deploy-state")
ALLOWED = {
    **{f"logo.{ext}": 2 * 1024 * 1024 for ext in ("png", "jpg", "webp")},
    **{f"app-icon.{ext}": 1024 * 1024 for ext in ("png", "jpg", "webp", "ico")},
    **{f"favicon.{ext}": 512 * 1024 for ext in ("png", "ico")},
}
OVERRIDE = """services:
  api:
    environment:
      BRANDING_ASSETS_ROOT: /var/lib/markina/branding
    volumes:
      - branding-assets:/var/lib/markina/branding
volumes:
  branding-assets:
    external: true
    name: markina-gallery_branding-assets
"""


def key_valid(key):
    if key not in ALLOWED:
        raise ValueError("invalid branding key")
    return key


def digest(body):
    return hashlib.sha256(body).hexdigest()


def safe_directory(path):
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError("symlink directory refused")
    return path


def read_asset(path, key):
    key_valid(key)
    safe_directory(path.parent)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= ALLOWED[key]:
        raise ValueError("invalid branding file")
    return path.read_bytes()


def transfer(backup, destination):
    """Validate everything first, then exclusive atomic publication; never overwrite."""
    backup, destination = safe_directory(backup), safe_directory(destination)
    manifest = json.loads((backup / "manifest.json").read_text())
    pending = []
    for key, expected in manifest["files"].items():
        body = read_asset(backup / key, key)
        if digest(body) != expected:
            raise ValueError("backup integrity failure")
        target = destination / key
        if target.exists() or target.is_symlink():
            if digest(read_asset(target, key)) != expected:
                raise ValueError("destination conflict; no files overwritten")
        else:
            pending.append((key, body))
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    for key, body in pending:
        fd, temporary = tempfile.mkstemp(prefix=".branding-", dir=destination)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            # link is atomic and refuses an existing path (including symlinks).
            os.link(temporary, destination / key)
        finally:
            Path(temporary).unlink(missing_ok=True)
    for key, expected in manifest["files"].items():
        if digest(read_asset(destination / key, key)) != expected:
            raise ValueError("transfer verification failed")


def docker(*args, input_data=None, check=True):
    result = subprocess.run(
        ["docker", *args], input=input_data, capture_output=True, check=False,
        timeout=120,
    )
    if check and result.returncode:
        # Do not disclose inspect env, SQL credentials or arbitrary daemon output.
        raise RuntimeError(f"docker {args[0]} failed")
    return result


def container(service):
    ids = docker("ps", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}",
                 "--filter", f"label=com.docker.compose.service={service}").stdout.split()
    if len(ids) != 1:
        raise ValueError(f"expected exactly one running {service}")
    identifier = ids[0].decode()
    info = json.loads(docker("inspect", identifier).stdout)[0]
    labels = info["Config"]["Labels"]
    if labels.get("com.docker.compose.project") != PROJECT or labels.get(
        "com.docker.compose.service"
    ) != service:
        raise ValueError("container ownership mismatch")
    return identifier, info


def extract_asset(archive, key):
    key_valid(key)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        members = source.getmembers()
        if len(members) != 1:
            raise ValueError("unexpected archive entries")
        entry = members[0]
        if entry.name != key or not entry.isfile() or not 0 < entry.size <= ALLOWED[key]:
            raise ValueError("invalid archived asset")
        return source.extractfile(entry).read()


def receive_backup(destination):
    """Receive only validated branding bytes, never mount private host directories."""
    payload = json.loads(sys.stdin.buffer.read(24 * 1024 * 1024 + 1))
    manifest = payload["manifest"]
    if set(payload["files"]) != set(manifest["files"]):
        raise ValueError("backup entries mismatch")
    with tempfile.TemporaryDirectory(prefix="branding-receive-") as directory:
        backup = Path(directory)
        for key, encoded in payload["files"].items():
            key_valid(key)
            body = base64.b64decode(encoded, validate=True)
            if not 0 < len(body) <= ALLOWED[key]:
                raise ValueError("invalid branding size")
            (backup / key).write_bytes(body)
        (backup / "manifest.json").write_text(json.dumps(manifest))
        transfer(backup, destination)


def restore_volume(backup, image, volume=VOLUME):
    manifest = json.loads((backup / "manifest.json").read_text())
    files = {}
    for key, expected in manifest["files"].items():
        body = read_asset(backup / key, key)
        if digest(body) != expected:
            raise ValueError("backup integrity failure")
        files[key] = base64.b64encode(body).decode("ascii")
    # The host owner reads its 0700/0600 backup. Bytes go through stdin, not argv,
    # logs, permissive chmod or a bind mount inaccessible to root with cap-drop ALL.
    docker("run", "--rm", "-i", "--network", "none", "--read-only", "--cap-drop", "ALL",
           "--security-opt", "no-new-privileges", "--entrypoint", "python",
           "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m,mode=1777",
           "--mount", f"type=volume,source={volume},target={ROOT}",
           image, "-c", Path(__file__).read_text(), "receive", ROOT,
           input_data=json.dumps({"manifest": manifest, "files": files}).encode())


def preserve():
    if Path.cwd().resolve() != Path("/opt/markina-gallery"):
        raise ValueError("unexpected checkout")
    api, info = container("api")
    db, _ = container("db")
    settings = dict(item.split("=", 1) for item in info["Config"]["Env"] if "=" in item)
    root = settings.get("BRANDING_ASSETS_ROOT", "/app/media/branding")
    if root == "media/branding":
        root = "/app/media/branding"
    if root not in {"/app/media/branding", ROOT}:
        raise ValueError("unexpected branding root; manual review required")
    # App only replaces files; it never changes these directory ancestors.
    docker("exec", api, "python", "-c",
           "from pathlib import Path; import sys; p=Path(sys.argv[1]); "
           "assert all(not q.is_symlink() for q in (p,*p.parents))", root)
    volume = docker("volume", "inspect", VOLUME, check=False)
    if volume.returncode:
        # Distinguish absence from daemon failure before creating the exact own volume.
        names = docker("volume", "ls", "--format", "{{.Name}}").stdout.decode().splitlines()
        if VOLUME in names:
            raise ValueError("volume cannot be inspected")
        docker("volume", "create", "--label", f"com.docker.compose.project={PROJECT}",
               "--label", "com.docker.compose.volume=branding-assets", VOLUME)
    volume_info = json.loads(docker("volume", "inspect", VOLUME).stdout)[0]
    labels = volume_info.get("Labels") or {}
    if labels.get("com.docker.compose.project") != PROJECT or labels.get(
        "com.docker.compose.volume"
    ) != "branding-assets" or volume_info.get("Driver") != "local" or volume_info.get("Options"):
        raise ValueError("unexpected volume ownership/driver/options")
    safe_directory(BACKUPS).mkdir(parents=True, exist_ok=True, mode=0o700)
    safe_directory(STATE).mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = Path(tempfile.mkdtemp(prefix="branding-", dir=BACKUPS))
    stopped = False
    try:
        stopped = True
        docker("stop", "--time", "30", api)
        sql = "SELECT json_build_array(logo_key,app_icon_key,favicon_key) FROM branding_settings;"
        raw = docker("exec", "-i", db, "sh", "-ceu",
                     'exec psql -XAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"',
                     input_data=sql.encode()).stdout.decode().splitlines()
        if len(raw) > 1:
            raise ValueError("ambiguous branding settings")
        keys = [key_valid(key) for key in (json.loads(raw[0]) if raw else []) if key]
        manifest = {"files": {}, "missing": []}
        for key in keys:
            result = docker("cp", f"{api}:{root}/{key}", "-", check=False)
            if result.returncode:
                # Docker reports missing paths explicitly; never treat generic copy failure as absence.
                error = result.stderr.decode(errors="replace")
                if "Could not find the file" not in error and "no such file or directory" not in error:
                    raise RuntimeError("branding copy failed")
                manifest["missing"].append(key)
                continue
            body = extract_asset(result.stdout, key)
            with (backup / key).open("xb") as stream:
                stream.write(body)
            manifest["files"][key] = digest(body)
        (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
        restore_volume(backup, info["Image"])
        override = STATE / "branding.compose.yml"
        if override.is_symlink():
            raise ValueError("override symlink refused")
        if override.exists():
            if override.read_text() != OVERRIDE:
                raise ValueError("unexpected rollback override")
        else:
            with override.open("x") as stream:
                stream.write(OVERRIDE)
        print(f"branding: backup={backup}; preserved={len(manifest['files'])}; "
              f"missing={','.join(manifest['missing']) or 'none'}; API stopped until recreation")
    except BaseException:
        if stopped:
            docker("start", api)
        raise


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preserve")
    receive = sub.add_parser("receive")
    receive.add_argument("destination", type=Path)
    restore = sub.add_parser("restore")
    restore.add_argument("backup", type=Path)
    restore.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.command == "preserve":
        preserve()
    elif args.command == "receive":
        receive_backup(args.destination)
    else:
        transfer(args.backup, args.destination)


if __name__ == "__main__":
    main()
