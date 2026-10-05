"""Conservative branding backup/transfer. No secrets, SQL writes or source deletion."""

import argparse
import base64
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from uuid import UUID

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
MAX_PAYLOAD_BYTES = 24 * 1024 * 1024
SCOPED_KEY = re.compile(
    r"tenants/([0-9a-f-]{36})/branding/(logo|app-icon|favicon)-([0-9a-f]{64})\.(png|jpg|webp|ico)"
)
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
    if isinstance(key, str) and key in ALLOWED:
        return key
    match = SCOPED_KEY.fullmatch(key) if isinstance(key, str) else None
    if not match or str(UUID(match[1])) != match[1] or f"{match[2]}.{match[4]}" not in ALLOWED:
        raise ValueError("invalid branding key")
    return key


def asset_limit(key):
    key_valid(key)
    match = SCOPED_KEY.fullmatch(key)
    return ALLOWED[f"{match[2]}.{match[4]}" if match else key]


def validate_body(key, body):
    if not 0 < len(body) <= asset_limit(key):
        raise ValueError("invalid branding size")
    match = SCOPED_KEY.fullmatch(key)
    if match and digest(body) != match[3]:
        raise ValueError("scoped branding integrity failure")
    return body


def settings_keys(rows):
    owners, keys = set(), []
    for row in rows:
        owner = row["tenant_id"]
        if owner is None:
            if len(rows) != 1:
                raise ValueError("ambiguous legacy branding settings")
        elif not isinstance(owner, str) or str(UUID(owner)) != owner:
            raise ValueError("invalid branding owner")
        if owner in owners:
            raise ValueError("ambiguous branding owner")
        owners.add(owner)
        for key in row["keys"]:
            if key is None:
                continue
            key_valid(key)
            match = SCOPED_KEY.fullmatch(key)
            if (match and match[1] != owner) or key in keys:
                raise ValueError("ambiguous branding key ownership")
            keys.append(key)
    return keys


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
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= asset_limit(key):
        raise ValueError("invalid branding file")
    return validate_body(key, path.read_bytes())


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
        safe_directory(target.parent)
        if target.exists() or target.is_symlink():
            if digest(read_asset(target, key)) != expected:
                raise ValueError("destination conflict; no files overwritten")
        else:
            pending.append((key, body))
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    for key, body in pending:
        parent = safe_directory((destination / key).parent)
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix=".branding-", dir=parent)
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
        if entry.name != Path(key).name or not entry.isfile() or not 0 < entry.size <= asset_limit(key):
            raise ValueError("invalid archived asset")
        return validate_body(key, source.extractfile(entry).read())


def receive_backup(destination):
    """Receive only validated branding bytes, never mount private host directories."""
    raw = sys.stdin.buffer.read(MAX_PAYLOAD_BYTES + 1)
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise ValueError("branding transport limit exceeded")
    payload = json.loads(raw)
    manifest = payload["manifest"]
    if set(payload["files"]) != set(manifest["files"]):
        raise ValueError("backup entries mismatch")
    with tempfile.TemporaryDirectory(prefix="branding-receive-") as directory:
        backup = Path(directory)
        for key, encoded in payload["files"].items():
            key_valid(key)
            body = base64.b64decode(encoded, validate=True)
            validate_body(key, body)
            (backup / key).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
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
    payload = json.dumps({"manifest": manifest, "files": files}).encode()
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("branding transport limit exceeded")
    docker("run", "--rm", "-i", "--network", "none", "--read-only", "--cap-drop", "ALL",
           "--security-opt", "no-new-privileges", "--entrypoint", "python",
           "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m,mode=1777",
           "--mount", f"type=volume,source={volume},target={ROOT}",
           image, "-c", Path(__file__).read_text(), "receive", ROOT,
           input_data=payload)


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
        sql = (
            "SELECT json_build_object('tenant_id',to_jsonb(settings)->>'tenant_id',"
            "'keys',json_build_array(logo_key,app_icon_key,favicon_key)) "
            "FROM branding_settings settings ORDER BY id;"
        )
        def read_settings():
            return docker("exec", "-i", db, "sh", "-ceu",
                          'exec psql -XAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"',
                          input_data=sql.encode()).stdout.decode().splitlines()

        raw = read_settings()
        keys = settings_keys([json.loads(row) for row in raw])
        docker("exec", api, "python", "-c",
               "from pathlib import Path; import json,sys; root=Path(sys.argv[1]); "
               "assert all(not parent.is_symlink() for key in json.loads(sys.argv[2]) "
               "for parent in (root/key,*(root/key).parents))", root, json.dumps(keys))
        stopped = True
        docker("stop", "--time", "30", api)
        if read_settings() != raw:
            raise ValueError("branding settings changed during preservation")
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
            (backup / key).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
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
