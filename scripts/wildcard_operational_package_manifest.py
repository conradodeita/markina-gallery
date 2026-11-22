"""Gera manifesto local de arquivos e fronteiras do pacote wildcard."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.wildcard_operational_gateway import FILES as HELPER_FILES
from scripts.wildcard_operational_gateway import IMAGE as NPM_IMAGE_ID

OUTPUT = ROOT / "scripts/wildcard_issuer/operational-manifest.json"
FILES = (
    "scripts/wildcard_operational_bundle.py",
    "scripts/wildcard_operational_custody.py",
    "scripts/wildcard_operational_files.py",
    "scripts/wildcard_operational_gateway.py",
    "scripts/wildcard_operational_installer.py",
    "scripts/wildcard_operational_issuer.py",
    "scripts/wildcard_operational_npm_helper.py",
    "scripts/wildcard_operational_protocol.py",
    "scripts/wildcard_operational_runtime.py",
    "scripts/wildcard_operational_service.py",
    "backend/app/integration_secrets.py",
    "scripts/wildcard_issuer/OPERACAO.md",
    "scripts/wildcard_issuer/dependency-manifest.json",
    "scripts/wildcard_issuer/helper-dependency-manifest.json",
    "scripts/wildcard_issuer/requirements-linux-arm64.lock",
    "scripts/wildcard_issuer/requirements-helper-arm64.lock",
    "scripts/wildcard_issuer/templates/pyp-acme-issuer.service",
    "scripts/wildcard_issuer/templates/pyp-acme-installer.service",
    "scripts/wildcard_issuer/templates/pyp-acme-installer.socket",
    "scripts/wildcard_issuer/templates/pyp-acme-issuer.timer",
    "openspec/changes/archive/2026-11-08-prepare-operational-wildcard-certificate-issuer/dependency-advisories-fixed.json",
    "openspec/changes/archive/2026-11-08-prepare-operational-wildcard-certificate-issuer/dependency-inventory.md",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    files = {}
    for relative in FILES:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"package_file_invalid: {relative}")
        files[relative] = {
            "sha256": sha256(path),
            "size": path.stat().st_size,
            "unix_mode": "0644",
        }
    unit_files = [
        ROOT / "scripts/wildcard_issuer/templates" / name
        for name in (
            "pyp-acme-issuer.service",
            "pyp-acme-installer.service",
            "pyp-acme-installer.socket",
            "pyp-acme-issuer.timer",
        )
    ]
    if any(
        re.search(r"(?m)^\[Install\]\s*$", path.read_text(encoding="utf-8"))
        for path in unit_files
    ):
        raise SystemExit("unit_template_must_remain_inactive")
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).date().isoformat(),
        "status": "candidato local; sem autorizacao de instalacao externa",
        "identity": {
            "issuer": "pyp-acme:pyp-acme; UID nao fixado ate inventario remoto",
            "installer": "root:pyp-acme; acionado somente pelo socket restrito",
            "socket_mode": "0660",
            "issuer_in_docker_group": False,
        },
        "fixed_paths": {
            "config": "/etc/pyp-acme-issuer",
            "source_key": "/etc/pyp-acme-issuer/private/envelope-key",
            "vault": "/var/lib/pyp-acme-issuer/vault",
            "runtime": "/run/pyp-acme-issuer",
            "installer_socket": "/run/pyp-acme-installer/installer.sock",
            "npm_helper": "/data/pyp-wildcard-helper",
            "npm_certificates": "/data/pyp-wildcard-certificates",
        },
        "unix_permissions": {
            "unit_files": "0644 root:root",
            "source_key_directory": "0700 root:root",
            "source_key": "0400 root:root",
            "vault_and_runtime": "0700 pyp-acme:pyp-acme",
            "temporary_token_ini": "0600 pyp-acme:pyp-acme",
            "npm_helper_directory": "0700 root:root inside approved NPM data mount",
            "installer_socket": "0660 root:pyp-acme",
        },
        "fixed_executables": {
            "certbot": "/opt/pyp-acme-issuer/bin/certbot",
            "certbot_arguments": [
                "certonly",
                "--non-interactive",
                "--config",
                "/dev/null",
                "--account",
                "<account-id-from-approved-config>",
                "--server",
                "https://acme-v02.api.letsencrypt.org/directory",
                "--config-dir",
                "/var/lib/pyp-acme-issuer",
                "--work-dir",
                "<private-temporary-directory>",
                "--logs-dir",
                "<private-temporary-directory>",
                "--no-directory-hooks",
                "--dns-cloudflare",
                "--dns-cloudflare-credentials",
                "<temporary-token-ini-path>",
                "--dns-cloudflare-propagation-seconds",
                "60",
                "--cert-name",
                "pyp-tenant-wildcard",
                "-d",
                "*.pickyourpic.com.br",
                "--keep-until-expiring",
            ],
            "docker": "/usr/bin/docker",
            "docker_host": "unix:///var/run/docker.sock",
            "nginx_inside_npm": "/usr/sbin/nginx",
            "nginx_commands": [["-t"], ["-s", "reload"]],
            "docker_operation_shapes": [
                [
                    "inspect",
                    "--format",
                    "<fixed-target-metadata>",
                    "<approved-container-id>",
                ],
                [
                    "exec",
                    "<approved-container-id>",
                    "sha256sum",
                    "<fixed-helper-files>",
                ],
                [
                    "exec",
                    "-i",
                    "<approved-container-id>",
                    "<fixed-python>",
                    "-B",
                    "<fixed-helper-script>",
                ],
            ],
        },
        "npm_approval": {
            "repo_digest": "jc21/nginx-proxy-manager@sha256:52b2c59994f3d36acfcf70a1626f29734df0ed8c71bacc0269f78b6f939858bb",
            "image_id": NPM_IMAGE_ID,
            "container_name": "/nginx-proxy-manager",
            "fixed_helper_files": list(HELPER_FILES),
            "runtime_manifest_sha256": "generated_from_verified_helper_wheels_at_install_time",
        },
        "activation": {
            "services_enabled": False,
            "socket_enabled": False,
            "timer_enabled": False,
            "unit_templates_have_install_section": False,
            "real_acme_or_dns_calls_performed": False,
        },
        "dependencies": {
            "issuer": "scripts/wildcard_issuer/dependency-manifest.json",
            "helper": "scripts/wildcard_issuer/helper-dependency-manifest.json",
            "advisory_report": "openspec/changes/archive/2026-11-08-prepare-operational-wildcard-certificate-issuer/dependency-advisories-fixed.json",
        },
        "files": files,
    }
    OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    OUTPUT.chmod(0o644)
    print(OUTPUT.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
