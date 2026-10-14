#!/usr/bin/env bash
# Inventário somente leitura do projeto Markina Gallery em homologação.

set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly ENV_FILE="docker/.env.homolog"

EXPECTED_SHA=""

fail() {
  echo "inventory-homolog-readonly: $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --expected-sha) EXPECTED_SHA="${2:-}"; shift 2 ;;
    *) fail "argumento não permitido: $1" ;;
  esac
done

[[ "$EXPECTED_SHA" =~ ^[0-9a-fA-F]{40}$ ]] || fail "SHA integral esperado inválido"
EXPECTED_SHA="${EXPECTED_SHA,,}"
[[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "execução permitida somente em $PROJECT_ROOT"
[[ -d .git ]] || fail "checkout Git da Markina ausente"

DEPLOYED_SHA="$(git rev-parse HEAD)"
[[ "$DEPLOYED_SHA" == "$EXPECTED_SHA" ]] || \
  fail "HEAD implantado diverge do SHA esperado; nenhuma consulta foi executada"
[[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" ]] || fail "Compose ou ambiente homolog da Markina ausente"

compose() {
  docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@" </dev/null
}

# Esta validação recebe a configuração renderizada em pipe, mas imprime apenas
# identidade/topologia não secreta. Não registra valores de ambiente ou URLs do banco.
topology="$(compose config --format json | python3 -c '
import json, sys
from urllib.parse import urlsplit

config = json.load(sys.stdin)
services = config.get("services", {})
def check(condition, label):
    if not condition:
        raise SystemExit(f"guarda de topologia divergente: {label}")

check(config.get("name") == "markina-gallery", "projeto Compose")
for service in ("nginx", "api", "db", "redis"):
    check(service in services, f"serviço {service}")
api_environment = services["api"].get("environment", {})
check(api_environment.get("APP_ENV") in ("staging", "homolog", "homologation"), "ambiente")
database = urlsplit(api_environment.get("DATABASE_URL", ""))
db_environment = services["db"].get("environment", {})
check(database.hostname == "db", "host do banco")
check(database.path.lstrip("/") == db_environment.get("POSTGRES_DB", ""), "nome do banco")
origin = urlsplit(api_environment.get("PUBLIC_APP_ORIGIN", ""))
check(origin.scheme == "https" and origin.hostname == "markina-homolog.duckdns.org"
      and origin.path in ("", "/") and not origin.query and not origin.fragment
      and not origin.username and not origin.password, "subdomínio público")
ports = services["nginx"].get("ports", [])
check(any(str(port.get("published")) == "8080" and port.get("host_ip") == "127.0.0.1"
          for port in ports), "porta local")
for name, service in services.items():
    if name != "nginx":
        check(not service.get("ports"), f"portas publicadas de {name}")

volumes = config.get("volumes", {})
def check_volume(service_name, target, source):
    mounts = [item for item in services[service_name].get("volumes", [])
              if item.get("target") == target]
    check(len(mounts) == 1 and mounts[0].get("type") == "volume"
          and mounts[0].get("source") == source, f"mount de {service_name}:{target}")
    check(volumes.get(source, {}).get("name") == f"markina-gallery_{source}",
          f"volume exclusivo {source}")
    check(not volumes.get(source, {}).get("external", False), f"volume não externo {source}")

for target, source in {
    "/var/lib/markina/source": "media-source",
    "/var/lib/markina/derivatives": "media-derivatives",
    "/var/lib/markina/history": "media-history",
    "/var/lib/markina/facial-references": "facial-references",
    "/var/lib/markina/branding": "branding-assets",
}.items():
    check_volume("api", target, source)
check_volume("db", "/var/lib/postgresql/data", "pgdata")
check_volume("redis", "/data", "redisdata")
print("projeto=markina-gallery ambiente=homolog entrada=127.0.0.1:8080 "
      "subdomínio=markina-homolog.duckdns.org banco/redis=internos volumes=exclusivos")
')" || fail "configuração Compose inválida ou fora do escopo homolog"

printf 'versão implantada: %s\n' "$DEPLOYED_SHA"
printf 'topologia: %s\n' "$topology"
unset topology

echo "serviços e health checks (somente projeto markina-gallery):"
compose ps --all

echo "revisão Alembic, contagens agregadas e jobs duráveis (um container transitório):"
compose run --rm --no-deps -e APP_ENV=homolog api python -c '
import json
from sqlalchemy import func, select, text
from app.auth import FacialJob, MediaJob, PreviewAdjustment, SessionLocal
from app.homolog_cleanup import inventory

models = (("media", MediaJob), ("facial", FacialJob), ("preview_adjustment", PreviewAdjustment))
with SessionLocal() as db:
    revisions = db.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num")).scalars().all()
    print("alembic_revision=" + (",".join(revisions) if revisions else "none"))
    print("database_media_counts=" + json.dumps(inventory(db), ensure_ascii=False, sort_keys=True))
    for label, model in models:
        queued = db.scalar(select(func.count()).select_from(model).where(model.status == "queued")) or 0
        processing = db.scalar(select(func.count()).select_from(model).where(model.status == "processing")) or 0
        failed = db.scalar(select(func.count()).select_from(model).where(model.status == "failed")) or 0
        total = db.scalar(select(func.count()).select_from(model)) or 0
        print(f"jobs_{label}: queued={queued} processing={processing} failed={failed} total={total}")
'

disk_stats="$(df -Pk "$PROJECT_ROOT" | awk 'NR == 2 { print "total_kib=" $2 " used_kib=" $3 " available_kib=" $4 " used=" $5 }')"
[[ -n "$disk_stats" ]] || fail "não foi possível ler capacidade do filesystem do projeto"
printf 'capacidade do filesystem do projeto: %s\n' "$disk_stats"

echo "inventário concluído; nenhuma migration, alteração persistente ou ação de deploy foi executada"
