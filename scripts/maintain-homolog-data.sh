#!/usr/bin/env bash
# Inventário/limpeza restritos ao banco e volumes da Markina Gallery em homologação.

set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly ENV_FILE="docker/.env.homolog"
readonly BACKUP_DIR="/var/lib/markina-gallery/backups"
readonly WITHOUT_BACKUP_CONFIRMATION="DELETE_HOMOLOG_GALLERIES_AND_CLIENTS_WITHOUT_BACKUP"

MODE=""
CONFIRMATION=""
WITHOUT_BACKUP=false

fail() {
  echo "maintain-homolog-data: $*" >&2
  return 1
}

compose() {
  # O script chega ao host por `bash -s`; nenhum subprocesso pode consumir
  # o restante da própria rotina pela entrada padrão compartilhada.
  docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@" </dev/null
}

preview_compose() {
  docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" \
    -f "$COMPOSE_FILE" -f docker/docker-compose.preview-adjustment.yml \
    --profile preview-adjustment "$@" </dev/null
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --confirmation) CONFIRMATION="${2:-}"; shift 2 ;;
    --without-backup) WITHOUT_BACKUP=true; shift ;;
    *) fail "argumento não permitido: $1" ;;
  esac
done

[[ "$MODE" == "inventory" || "$MODE" == "execute" ]] || fail "modo deve ser inventory ou execute"
[[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "execução permitida somente em $PROJECT_ROOT"
[[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" ]] || fail "configuração exclusiva da Markina ausente"
compose config --quiet

# O override APP_ENV no contêiner efêmero não prova que o host/volumes são de
# homologação. Confere a configuração resolvida sem imprimir credenciais.
compose config --format json | python3 -c '
import json, sys
from urllib.parse import urlsplit
config = json.load(sys.stdin)
services = config["services"]
def check(condition):
    if not condition:
        raise SystemExit(1)
check(config["name"] == "markina-gallery")
check(services["api"]["environment"]["APP_ENV"] in ("staging", "homolog", "homologation"))
api_url = urlsplit(services["api"]["environment"]["DATABASE_URL"])
check(api_url.hostname == "db")
check(api_url.path.lstrip("/") == services["db"]["environment"]["POSTGRES_DB"])
public_url = urlsplit(services["api"]["environment"]["MARKINA_PUBLIC_URL"])
check(public_url.hostname == "markina-homolog.duckdns.org")
check(any(str(port.get("published")) == "8080" and port.get("host_ip") == "127.0.0.1"
          for port in services["nginx"].get("ports", [])))
for service in ("db", "redis", "evolution-db", "evolution-redis"):
    check(not services[service].get("ports"))
mounts = {item["target"]: item["source"] for item in services["api"]["volumes"]}
for target, source in {
    "/var/lib/markina/source": "media-source",
    "/var/lib/markina/derivatives": "media-derivatives",
    "/var/lib/markina/history": "media-history",
    "/var/lib/markina/facial-references": "facial-references",
}.items():
    check(mounts[target].split("_")[-1] == source)
check(mounts["/var/lib/markina/branding"].split("_")[-1] == "branding-assets")
' || fail "topologia de homologação não corresponde ao projeto/porta/domínio/banco/volumes esperados"
for service in api db redis; do
  container="$(compose ps -q "$service")"
  [[ -n "$container" ]] || fail "contêiner da Markina ausente: $service"
  [[ "$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$container")" == "$PROJECT_NAME" ]] || \
    fail "contêiner fora do projeto Markina: $service"
done
echo "topologia: projeto=$PROJECT_NAME entrada=127.0.0.1:8080 subdomínio=markina-homolog.duckdns.org"
compose ps

if [[ "$MODE" == "inventory" ]]; then
  [[ "$WITHOUT_BACKUP" == "false" && -z "$CONFIRMATION" ]] || \
    fail "inventário não aceita confirmação nem modo sem backup"
  compose run --rm --no-deps -e APP_ENV=homolog api \
    python -m app.homolog_cleanup --mode inventory
  exit 0
fi

if [[ "$WITHOUT_BACKUP" == "true" ]]; then
  [[ "$CONFIRMATION" == "$WITHOUT_BACKUP_CONFIRMATION" ]] || \
    fail "confirmação literal inválida para limpeza sem backup"
else
  [[ "$CONFIRMATION" == "DELETE_HOMOLOG_GALLERIES_AND_CLIENTS" ]] || \
    fail "confirmação literal inválida"
fi

while IFS= read -r service; do
  case "$service" in
    nginx|web|api|worker|db|redis|evolution-api|evolution-db|evolution-redis|\
    face-index-worker|face-search-worker|face-maintenance-worker|preview-adjustment-worker) ;;
    *) fail "serviço ativo desconhecido no projeto Markina: $service" ;;
  esac
done < <(docker ps --filter "label=com.docker.compose.project=$PROJECT_NAME" \
  --format '{{index .Config.Labels "com.docker.compose.service"}}')

paused_services=(api worker)
for service in face-index-worker face-search-worker face-maintenance-worker; do
  container="$(compose ps -q "$service")"
  if [[ -n "$container" && "$(docker inspect --format '{{.State.Running}}' "$container")" == "true" ]]; then
    paused_services+=("$service")
  fi
done
preview_container="$(docker ps -q \
  --filter "label=com.docker.compose.project=$PROJECT_NAME" \
  --filter "label=com.docker.compose.service=preview-adjustment-worker")"
preview_running=false
if [[ -n "$preview_container" ]]; then
  [[ -f docker/docker-compose.preview-adjustment.yml ]] || \
    fail "worker de ajuste de prévia ativo sem override conhecido"
  preview_compose config --quiet
  preview_running=true
fi

restore_services() {
  compose up -d --no-deps "${paused_services[@]}" >/dev/null
  if [[ "$preview_running" == "true" ]]; then
    preview_compose up -d --no-deps preview-adjustment-worker >/dev/null
  fi
}
trap restore_services EXIT
compose stop "${paused_services[@]}"
if [[ "$preview_running" == "true" ]]; then
  preview_compose stop preview-adjustment-worker
fi
pre_inventory="$(compose run --rm --no-deps -e APP_ENV=homolog api \
  python -m app.homolog_cleanup --mode inventory)"
printf 'inventário anterior: %s\n' "$pre_inventory"

if [[ "$WITHOUT_BACKUP" == "true" ]]; then
  echo "limpeza sem novo backup autorizada pelo token exclusivo"
else
  mkdir -p "$BACKUP_DIR"
  backup_file="$BACKUP_DIR/pre-cleanup-$(date -u +%Y%m%dT%H%M%SZ).dump"
  compose exec -T db sh -ceu 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$backup_file"
  echo "backup lógico exclusivo da Markina criado antes da limpeza"
fi

compose run --rm --no-deps -e APP_ENV=homolog api python -m app.homolog_cleanup \
  --mode execute --confirmation "$CONFIRMATION"
compose exec -T redis redis-cli FLUSHDB >/dev/null
restore_services
trap - EXIT
compose restart nginx >/dev/null
services_to_check=(nginx web "${paused_services[@]}")
for service in "${services_to_check[@]}"; do
  container="$(compose ps -q "$service")"
  [[ -n "$container" ]] || fail "serviço Markina ausente após limpeza: $service"
  status="unknown"
  for _attempt in $(seq 1 30); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$status" == "healthy" ]] && break
    sleep 2
  done
  [[ "$status" == "healthy" ]] || fail "serviço Markina não ficou saudável: $service ($status)"
done
if [[ "$preview_running" == "true" ]]; then
  container="$(preview_compose ps -q preview-adjustment-worker)"
  [[ -n "$container" ]] || fail "worker de ajuste de prévia ausente após limpeza"
  status="unknown"
  for _attempt in $(seq 1 30); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$status" == "healthy" ]] && break
    sleep 2
  done
  [[ "$status" == "healthy" ]] || fail "worker de ajuste de prévia não ficou saudável: $status"
fi
curl --fail --silent --show-error --max-time 15 \
  http://127.0.0.1:8080/api/health >/dev/null || \
  fail "rota HTTP da Markina não ficou saudável após a manutenção"
post_inventory="$(compose run --rm --no-deps -e APP_ENV=homolog api \
  python -m app.homolog_cleanup --mode inventory)"
printf 'inventário posterior: %s\n' "$post_inventory"
PRE_INVENTORY="$pre_inventory" POST_INVENTORY="$post_inventory" python3 - <<'PY'
import json
import os

before = json.loads(os.environ["PRE_INVENTORY"])
after = json.loads(os.environ["POST_INVENTORY"])
if any(after["database"].values()):
    raise SystemExit("contagens operacionais não foram zeradas")
if any(value for root in after["media"].values() for value in root.values()):
    raise SystemExit("mídia operacional não foi zerada")
if before["preserved"] != after["preserved"]:
    raise SystemExit("admin, sessões/fatores ou preferências não foram preservados")
print("preservação administrativa e preferências: verificada")
PY
facial_flag="$(sed -n 's/^FACIAL_PROCESSING_ENABLED=//p' "$ENV_FILE" | tail -n 1)"
[[ "$facial_flag" == "true" || "$facial_flag" == "false" ]] || \
  fail "FACIAL_PROCESSING_ENABLED ausente ou inválido"
echo "coerência facial: FACIAL_PROCESSING_ENABLED=$facial_flag"
echo "limpeza de dados sintéticos da Markina concluída"
