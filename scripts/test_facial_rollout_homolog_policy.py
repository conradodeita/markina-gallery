"""Verificações estruturais da ponte persistente de rollout em homologação."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts/operate-facial-rollout-homolog.sh").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/facial-rollout-homolog.yml").read_text(encoding="utf-8")


def require(fragment: str, label: str, content: str) -> None:
    if fragment not in content:
        raise AssertionError(f"ausente: {label}")


def main() -> None:
    require('PROJECT_NAME="markina-gallery"', "projeto Compose fixo", SCRIPT)
    require('PROJECT_ROOT="/opt/markina-gallery"', "checkout remoto fixo", SCRIPT)
    require("--expected-sha", "SHA publicado", SCRIPT)
    require("escopo_galerias=1", "allowlist unitária", SCRIPT)
    require("pg_dump -Fc", "backup lógico anterior", SCRIPT)
    require("python -m app.facial.manage_rollout", "operação persistente", SCRIPT)
    require("python -m app.facial.reconcile_gallery", "backfill explícito", SCRIPT)
    require("compose restart face-index-worker", "backfill pós-ativação", SCRIPT)
    require("rollout suspenso como contenção", "contenção de falha", SCRIPT)
    require('PUBLIC_BASE_URL="https://markina-homolog.duckdns.org"', "healthcheck externo", SCRIPT)
    require("environment: homolog", "Environment protegido", WORKFLOW)
    require("ACTIVATE_FACIAL_HOMOLOG_CANARY", "confirmação vinculada", WORKFLOW)
    require("persist-credentials: false", "credencial Git não persistida", WORKFLOW)
    for forbidden in (
        "docker system prune",
        "docker compose down",
        "activate-private",
        "benchmark-homolog-facial",
    ):
        if forbidden in SCRIPT or forbidden in WORKFLOW:
            raise AssertionError(f"operação proibida encontrada: {forbidden}")
    print("facial rollout homolog policy: ok")


if __name__ == "__main__":
    main()
