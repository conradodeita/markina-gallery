"""Guarda estrutural do release coordenado de produção."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "deploy-prod-app.sh").read_text(encoding="utf-8")
LOCK = (ROOT / "scripts" / "deploy-prod-lock.sh").read_text(encoding="utf-8")
RUNBOOK = (ROOT / "docs" / "DEPLOY-PROD-APP.md").read_text(encoding="utf-8")


def require(value: str, description: str) -> None:
    if value not in SCRIPT:
        raise AssertionError(f"ausente: {description}")


def forbid(pattern: str, description: str) -> None:
    if re.search(pattern, SCRIPT, flags=re.MULTILINE):
        raise AssertionError(f"proibido: {description}")


def main() -> None:
    for value, description in (
        ('readonly PROJECT_ROOT="/opt/markina-gallery"', "raiz do projeto fixa"),
        ('readonly PROJECT_NAME="markina-gallery"', "projeto Compose fixo"),
        ('readonly ENV_FILE="docker/.env.homolog"', "ambiente efetivo identificado"),
        ('readonly PUBLIC_URL="https://markina.pickyourpic.com.br"', "domínio documentado"),
        ('source "$SCRIPT_DIR/deploy-prod-lock.sh"', "lock compartilhado"),
        ('acquire_production_deploy_lock "$STATE_DIR" app', "lock antes de qualquer modo"),
        ('app-last-healthy.sha', "baseline coordenado obrigatório"),
        ("baseline-inventory", "inventário do baseline inicial"),
        ("execute_baseline", "registro aprovado do baseline"),
        ("failure_record", "registro de falha com serviço e status"),
        ("validate_checkout_clean", "recusa de checkout sujo"),
        ('git diff --name-only "$ACTIVE_SHA" "$TARGET_SHA"', "diff desde baseline"),
        ('backend/migrations/*|docker/*|docker-compose*.yml|docker-compose*.yaml|.env*', "recusa de migration/infra"),
        ("compose config --quiet", "configuração sem revelar segredos"),
        ("com.docker.compose.config-hash", "hash do runtime comparado"),
        ("compose build api web", "ambos os builds antes da troca"),
        ("docker image inspect --format '{{.Id}}' \"$PROJECT_NAME-api\"", "id da imagem recém-construída de API"),
        ("docker image inspect --format '{{.Id}}' \"$PROJECT_NAME-web\"", "id da imagem recém-construída de web"),
        ("AVAILABLE_BUILD_KB >= REQUIRED_BUILD_KB", "espaço livre comparado às imagens atuais"),
        ('compose up -d --no-deps --no-build "$service"', "recriação sem dependências"),
        ('[[ "$service" == api || "$service" == web ]]', "lista fechada de serviços"),
        ("app-in-flight.sha", "tentativa interrompida rastreável"),
        ("production-app-%s", "imagens imutáveis por snapshot e serviço"),
        ("curl --fail --silent --show-error --retry 5", "smoke tests HTTPS"),
        ("$PUBLIC_URL/api/health", "rota de saúde API"),
        ("$PUBLIC_URL/healthz", "rota de saúde nginx"),
        ("$PUBLIC_URL/", "rota do frontend"),
    ):
        require(value, description)

    if 'production-release.lock' not in LOCK or 'flock -n' not in LOCK:
        raise AssertionError("lock do host não é exclusivo/não bloqueante")
    if 'web-in-flight.sha' not in LOCK or 'app-in-flight.sha' not in LOCK:
        raise AssertionError("lock não protege tentativas interrompidas dos dois fluxos")
    for value in (
        "baseline-inventory", "--mode baseline", "--mode inventory", "--mode release",
        "--mode rollback-inventory", "--mode rollback", "approval_code", "valores nunca devem ser exibidos",
        "não há garantia de zero downtime", "app-in-flight.sha", "reconciliação inicial",
    ):
        if value not in RUNBOOK:
            raise AssertionError(f"runbook incompleto: {value}")

    mutations = re.findall(r"compose\s+(build|up)\s+([^\n]+)", SCRIPT)
    if ("build", "api web") not in mutations:
        raise AssertionError("build fora do par API/web")
    if any(action == "up" and args.strip() != '-d --no-deps --no-build "$service"' for action, args in mutations):
        raise AssertionError(f"mutação Compose fora do helper de serviço restrito: {mutations}")
    baseline_body = SCRIPT.split("execute_baseline() {", 1)[1].split("\n}\n", 1)[0]
    if "compose up" in baseline_body or "recreate_service" in baseline_body:
        raise AssertionError("registro inicial do baseline recria um serviço")

    forbid(r"\bdocker\s+system\s+prune\b", "docker system prune")
    forbid(r"\bcompose\s+down\b", "docker compose down")
    forbid(r"\bcompose\s+(?:up|build)\s+[^\n]*(?:\bworker\b|\bnginx\b|\bdb\b|\bredis\b)",
           "mutação de serviços fora de API/web")
    forbid(r"\b(?:sed\s+-i|tee\s+-a?)\b.*\.env", "alteração do ambiente")
    forbid(r"alembic\s+upgrade", "execução de migrations")

    print("deploy-prod-app policy: ok")


if __name__ == "__main__":
    main()
