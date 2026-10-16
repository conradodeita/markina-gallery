"""Verifica a separação entre preflight somente-leitura e gate de produção."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
WRAPPER = (ROOT / "scripts/production-preflight-ssh-wrapper.sh").read_text(
    encoding="utf-8"
)
INVENTORY_SCRIPT = (ROOT / "scripts/deploy-prod-facial-services.sh").read_bytes()


def require(fragment: str, label: str, content: str) -> None:
    if fragment not in content:
        raise AssertionError(f"ausente: {label}")


def main() -> None:
    preflight = WORKFLOW.split("  production-preflight:", 1)[1].split(
        "  production-release:", 1
    )[0]
    release = WORKFLOW.split("  production-release:", 1)[1]

    require("environment: production-preflight", "environment sem revisor para preflight", preflight)
    require("environment: production", "environment protegido no release", release)
    require(
        "secrets.PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY",
        "chave dedicada de preflight",
        preflight,
    )
    require(
        "secrets.PRODUCTION_PREFLIGHT_SSH_KNOWN_HOSTS",
        "known_hosts dedicado de preflight",
        preflight,
    )
    require('"MARKINA_TARGET_SHA=$GITHUB_SHA" </dev/null', "comando restrito sem stdin controlado pelo runner", preflight)
    if "< scripts/deploy-prod-facial-services.sh" in preflight or "bash -s" in preflight:
        raise AssertionError("preflight não pode executar script enviado pelo runner")

    require('^MARKINA_TARGET_SHA=([0-9a-f]{40})$', "comando SSH validado por regex estrita", WRAPPER)
    require("--mode inventory", "wrapper fixa modo somente-leitura", WRAPPER)
    blob_header = f"blob {len(INVENTORY_SCRIPT)}\0".encode()
    blob_sha = hashlib.sha1(blob_header + INVENTORY_SCRIPT).hexdigest()
    require(
        f'INVENTORY_SCRIPT_BLOB_SHA="{blob_sha}"',
        "wrapper fixa o conteúdo exato do script somente-leitura",
        WRAPPER,
    )
    require(
        'https://raw.githubusercontent.com/$EXPECTED_REPOSITORY/$target_sha/scripts/deploy-prod-facial-services.sh',
        "script buscado por SHA imutável após merge",
        WRAPPER,
    )
    require('git hash-object "$script_file"', "integridade do script conferida sem gravá-lo no Git", WRAPPER)
    if "--mode release" in WRAPPER or '"$SSH_ORIGINAL_COMMAND"' in WRAPPER:
        raise AssertionError("wrapper não pode encaminhar comando arbitrário nem release")
    if "bash -s" in WRAPPER or "git fetch" in WRAPPER:
        raise AssertionError("wrapper não executa stdin nem altera refs locais do checkout")

    print("production release workflow policy: ok")


if __name__ == "__main__":
    main()
