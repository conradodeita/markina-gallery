from pathlib import Path

SCRIPT = Path(__file__).with_name("resume-homolog.sh").read_text(encoding="utf-8")
RUNBOOK = Path(__file__).parents[1].joinpath("docs/DEPLOY-CONTINUO-HOMOLOGACAO.md").read_text(encoding="utf-8")


def require(fragment: str, reason: str) -> None:
    if fragment not in SCRIPT:
        raise SystemExit(f"faltou {reason}: {fragment}")


def forbid(fragment: str, reason: str) -> None:
    if fragment in SCRIPT:
        raise SystemExit(f"operação proibida no fluxo de retomada ({reason}): {fragment}")


require('readonly PROJECT_ROOT="/opt/markina-gallery"', "raiz restrita")
require('readonly PROJECT_NAME="markina-gallery"', "projeto Compose restrito")
require('readonly COMPOSE_FILE="docker/docker-compose.yml"', "arquivo Compose explícito")
require("compose up -d --no-deps --no-recreate", "start sem dependências nem recriação")
require("readonly REQUIRED_SERVICES=(api web worker nginx)", "lista base delimitada")
require("readonly FACIAL_SERVICES=(face-search-worker face-index-worker face-maintenance-worker)", "lista facial delimitada")
require("preview-adjustment-worker", "suporte ao worker opcional de prévia")
require('[[ "$PWD" == "$PROJECT_ROOT" ]]', "bloqueio de execução fora do projeto")
require("LOCAL_PUBLIC_BASE_URL/healthz", "healthcheck local")
require("PUBLIC_BASE_URL/healthz", "healthcheck público")
require("verify_schema_revision", "verificação de schema no preflight")
require("assert_homolog_schema_head.py", "comparação da revisão DB com o head do checkout")
require("require_healthy_dependency db", "preflight de saúde do DB")
require("require_healthy_dependency redis", "preflight de saúde do Redis")

forbidden = {
    "compose start": "atalho que pode seguir dependências one-shot antigas",
    "compose run": "execução de serviço one-shot",
    "alembic upgrade": "migration implícita",
    "service migrate": "inclusão do serviço one-shot",
    "docker compose down": "parada ampla do projeto",
    "docker system prune": "remoção global de recursos Docker",
    "redis-cli FLUSH": "limpeza de filas/dados",
}
for fragment, reason in forbidden.items():
    forbid(fragment, reason)

for fragment in (
    "bash scripts/resume-homolog.sh --public-base-url https://markina-homolog.duckdns.org",
    "--no-deps --no-recreate",
    "não faz deploy, rebuild, recriação, limpeza nem alteração de banco",
    "Evolution",
):
    if fragment not in RUNBOOK:
        raise SystemExit(f"runbook não documenta a retomada segura: {fragment}")
resume_section = RUNBOOK.split("### Retomada dos serviços sem deploy ou migration", 1)[-1]
resume_command = resume_section.split("```", 2)[1]
if "docker compose start" in resume_command:
    raise SystemExit("o comando de retomada documentado não pode usar docker compose start")

print("política de retomada aprovada")
