"""Verifica a separação entre preflight somente-leitura e gate de produção."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
WRAPPER = (ROOT / "scripts/production-preflight-ssh-wrapper.sh").read_text(
    encoding="utf-8"
)


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
    if "--mode release" in WRAPPER or '"$SSH_ORIGINAL_COMMAND"' in WRAPPER:
        raise AssertionError("wrapper não pode encaminhar comando arbitrário nem release")

    print("production release workflow policy: ok")


if __name__ == "__main__":
    main()
