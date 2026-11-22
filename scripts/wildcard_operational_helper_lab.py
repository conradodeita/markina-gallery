"""Prova do entrypoint interno somente no NPM sintético já inicializado."""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from scripts.test_wildcard_certificate_custody import synthetic_bundle, synthetic_ca
from scripts.wildcard_operational_bundle import validate_bundle
from scripts.wildcard_operational_gateway import FILES


def run():
    if (
        os.environ.get("PYP_WILDCARD_LAB") != "synthetic-network-none"
        or os.getuid() != 0
    ):
        raise RuntimeError("lab_only")
    if any(
        line.split()[1] == "00000000"
        for line in Path("/proc/net/route").read_text().splitlines()[1:]
    ):
        raise RuntimeError("network_not_isolated")
    root = Path("/data/pyp-wildcard-certificates")
    if (root / ".pyp-wildcard-lab").read_text() != "pyp-wildcard-synthetic-only-v1":
        raise RuntimeError("laboratory_marker_missing")
    db = sqlite3.connect("file:/data/database.sqlite?mode=ro", uri=True)
    assert db.execute("SELECT email FROM user").fetchall() == [
        ("synthetic@example.test",)
    ]
    rows = db.execute(
        "SELECT id,domain_names FROM proxy_host WHERE is_deleted=0"
    ).fetchall()
    assert len(rows) == 3
    assert {json.loads(domains)[0] for _, domains in rows} == {
        "*.pickyourpic.com.br",
        "pickyourpic.com.br",
        "markina.pickyourpic.com.br",
    }

    def api(path, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(
            "http://127.0.0.1:81/api" + path,
            None if body is None else json.dumps(body).encode(),
            headers=headers,
        )
        if path.startswith("/nginx/proxy-hosts/") and body is not None:
            request.method = "PUT"
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.load(response)

    token = api(
        "/tokens",
        {"identity": "synthetic@example.test", "secret": "SyntheticLabPassword!2026"},
    )["token"]
    root_id = next(
        i for i, domains in rows if json.loads(domains) == ["pickyourpic.com.br"]
    )
    record = api("/nginx/proxy-hosts/" + str(root_id), token=token)
    fields = (
        "domain_names",
        "forward_scheme",
        "forward_host",
        "forward_port",
        "access_list_id",
        "certificate_id",
        "ssl_forced",
        "caching_enabled",
        "block_exploits",
        "allow_websocket_upgrade",
        "http2_support",
        "hsts_enabled",
        "hsts_subdomains",
        "advanced_config",
        "locations",
        "meta",
    )
    update = {name: record[name] for name in fields}
    update["advanced_config"] = update["advanced_config"].replace(
        "return 200 ", "return 404 "
    )
    api("/nginx/proxy-hosts/" + str(root_id), update, token)
    helper = Path("/data/pyp-wildcard-helper")
    if helper.exists():
        metadata = helper.stat(follow_symlinks=False)
        if (
            not helper.is_dir()
            or metadata.st_uid != 0
            or metadata.st_mode & 0o777 != 0o700
        ):
            raise RuntimeError("helper_state_invalid")
    else:
        helper.mkdir(mode=0o700)
    for name in FILES:
        if name in {"trust.pem", "runtime-manifest.json"}:
            continue
        target = helper / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path("/lab") / name, target)
    dependency_manifest = json.loads(
        Path("/lab/helper-dependency-manifest.json").read_text()
    )
    runtime_hashes = {}
    library = helper / "lib"
    library.mkdir(mode=0o755, exist_ok=True)
    for package in dependency_manifest["packages"]:
        wheel = Path("/lab/helper-wheels") / Path(package["url"]).name
        if hashlib.sha256(wheel.read_bytes()).hexdigest() != package["sha256"]:
            raise RuntimeError("helper_wheel_hash_invalid")
        with ZipFile(wheel) as archive:
            for entry in archive.infolist():
                relative = PurePosixPath(entry.filename)
                mode = entry.external_attr >> 16
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or not relative.parts
                    or (mode & 0o170000) == 0o120000
                ):
                    raise RuntimeError("helper_wheel_path_invalid")
                target = library.joinpath(*relative.parts)
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                expected_bytes = archive.read(entry)
                if target.exists():
                    if (
                        not target.is_file()
                        or target.is_symlink()
                        or target.read_bytes() != expected_bytes
                    ):
                        raise RuntimeError("helper_runtime_changed")
                else:
                    with target.open("xb") as output:
                        output.write(expected_bytes)
                target.chmod(0o555 if mode & 0o111 else 0o444)
                runtime_hashes[target.relative_to(helper).as_posix()] = hashlib.sha256(
                    target.read_bytes()
                ).hexdigest()
    (helper / "runtime-manifest.json").write_text(
        json.dumps(runtime_hashes, sort_keys=True, separators=(",", ":"))
    )
    (helper / "runtime-manifest.json").chmod(0o600)
    for directory, _, _ in os.walk(library, topdown=False):
        Path(directory).chmod(0o555)
    reference_roots = [
        x509.load_pem_x509_certificates(
            (root / f"reference-{index}/fullchain.pem").read_bytes()
        )[-1]
        for index in (0, 1)
    ]
    if any(
        cert.public_bytes(serialization.Encoding.DER)
        != reference_roots[0].public_bytes(serialization.Encoding.DER)
        for cert in reference_roots[1:]
    ):
        raise RuntimeError("reference_roots_changed")
    # The reference hosts retain this CA when repeated helper tests rotate the
    # synthetic wildcard bundle through unrelated test CAs.
    reference_root = reference_roots[0]
    key, ca = synthetic_ca()
    trust = reference_root.public_bytes(serialization.Encoding.PEM) + ca.public_bytes(
        serialization.Encoding.PEM
    )
    (helper / "trust.pem").write_bytes(trust)
    (helper / "trust.pem").chmod(0o600)
    chain, private = synthetic_bundle(key, ca)
    expected = validate_bundle(chain, private, trust)
    payload = json.dumps(
        {"v": 1, "fullchain": chain.decode(), "private_key": private.decode()}
    ).encode()
    args = [
        "/opt/certbot/bin/python3",
        "-B",
        str(helper / "scripts/wildcard_operational_npm_helper.py"),
    ]
    receipt = json.loads(
        subprocess.run(
            args, input=payload, capture_output=True, check=True, timeout=90
        ).stdout
    )
    assert receipt == {"fingerprint": expected, "replayed": False}
    replay = json.loads(
        subprocess.run(
            args, input=payload, capture_output=True, check=True, timeout=90
        ).stdout
    )
    assert replay == {"fingerprint": expected, "replayed": True}
    assert db.execute("SELECT count(*) FROM certificate").fetchone()[0] == 0
    assert not (root / "pending.json").exists()
    for file in Path("/data").glob("database.sqlite*"):
        assert b"PRIVATE KEY" not in file.read_bytes()
    print(
        json.dumps(
            {
                "result": "passed",
                "real_helper_process": True,
                "tls_verified": True,
                "replay_verified": True,
                "reference_hosts_verified": True,
                "certificate_db_rows": 0,
                "isolated_cryptography": "50.0.0",
                "external_network": False,
            }
        )
    )


if __name__ == "__main__":
    run()
