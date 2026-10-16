#!/usr/bin/env bash
# Inventário e release protegidos para web, API e worker de busca facial.
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly EXPECTED_HOST="clearbudget-vnic"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly ENV_FILE="docker/.env.homolog"
readonly STATE_DIR="/var/lib/markina-gallery/deploy-state"
readonly PUBLIC_URL="https://markina.pickyourpic.com.br"
readonly COMPOSE_FILE_LABEL="/opt/markina-gallery/docker/docker-compose.yml,/var/lib/markina-gallery/deploy-state/branding.compose.yml,/opt/markina-gallery/docker/docker-compose.raw-development.yml,/opt/markina-gallery/docker/docker-compose.preview-adjustment.yml,/opt/markina-gallery/docker/docker-compose.system-monitor.yml,/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml"
readonly COMPOSE_EXTRA_FILES=(
  "/var/lib/markina-gallery/deploy-state/branding.compose.yml"
  "docker/docker-compose.raw-development.yml"
  "docker/docker-compose.preview-adjustment.yml"
  "docker/docker-compose.system-monitor.yml"
  "/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml"
)
readonly SERVICES=(web api face-search-worker)
readonly MAINTENANCE_BASELINE_SHA="d9c8d3b118fc367af26cfa2b47772d7bff1ccd47"
readonly EXPECTED_DATABASE_REVISION="20261014_0081"
readonly TARGET_DATABASE_REVISION="20261016_0082"

MODE=""
TARGET_SHA=""
APPROVAL_FINGERPRINT=""
EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:-}"
EXPECTED_URL="${MARKINA_PUBLIC_BASE_URL:-$PUBLIC_URL}"
ACTIVE_SHA=""
CHECKOUT_SHA=""
INVENTORY_FINGERPRINT=""
COMPOSE_APP_VERSION=""
DATABASE_REVISION=""

fail() { echo "deploy-prod-facial-services: $*" >&2; exit 1; }

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode) MODE="${2:-}"; shift 2 ;;
      --sha) TARGET_SHA="${2:-}"; shift 2 ;;
      --approval-fingerprint) APPROVAL_FINGERPRINT="${2:-}"; shift 2 ;;
      *) fail "argumento não permitido: $1" ;;
    esac
  done
  [[ "$MODE" == "inventory" || "$MODE" == "release" ]] || fail "modo deve ser inventory ou release"
  [[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA alvo inválido"
  if [[ "$MODE" == "release" ]]; then
    [[ "$APPROVAL_FINGERPRINT" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint de inventário obrigatório"
  fi
}

compose() {
  local files=(--env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE") file
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do files+=(-f "$file"); done
  APP_VERSION="$COMPOSE_APP_VERSION" docker compose "${files[@]}" --profile facial --profile preview-adjustment "$@" </dev/null
}

resolved_compose_hashes() {
  # Compose 2.35.1 não resolve env_file no --hash direto. O JSON pode conter
  # segredos: trafega apenas pelo pipe, sem arquivo, log ou interpolação nova.
  compose config --format json 2>/dev/null \
    | docker compose -p "$PROJECT_NAME" -f - --profile facial --profile preview-adjustment \
      config --no-interpolate --hash web,api,face-search-worker 2>/dev/null \
    || fail "não foi possível calcular hashes da configuração resolvida"
}

database_revision() {
  local output revisions count
  output="$(compose exec -T api python -m alembic current 2>/dev/null)" \
    || fail "não foi possível consultar a revisão do banco"
  revisions="$(sed -nE 's/^([0-9]{8}_[0-9]{4})( .*)?$/\1/p' <<<"$output")"
  count="$(wc -l <<<"$revisions" | tr -d ' ')"
  [[ "$count" == "1" && "$revisions" =~ ^[0-9]{8}_[0-9]{4}$ ]] \
    || fail "banco sem revisão única ou com múltiplas cabeças"
  printf '%s\n' "$revisions"
}

require_existing_facial_runtime() {
  local service id
  for service in api face-search-worker; do
    id="$(compose ps -q "$service")"
    [[ -n "$id" && "$(wc -l <<<"$id" | tr -d ' ')" == "1" ]] || fail "runtime ativo de $service ausente"
    docker inspect --format '{{json .Config.Env}}' "$id" \
      | python3 -c 'import json,sys; values=json.load(sys.stdin); sys.exit(0 if "FACIAL_PROCESSING_ENABLED=true" in values else 1)' \
      || fail "manutenção exige runtime facial já ativo em $service"
  done
}

verify_repository() {
  local origin
  [[ "$(hostname)" == "$EXPECTED_HOST" ]] || fail "host diverge do alvo aprovado"
  [[ "$(pwd -P)" == "$PROJECT_ROOT" && "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] || fail "checkout Markina esperado ausente"
  [[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" && -d "$STATE_DIR" ]] || fail "Compose, ambiente ou estado de deploy ausente"
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do [[ -f "$file" ]] || fail "manifesto Compose ativo ausente"; done
  git check-ignore -q "$ENV_FILE" || fail "arquivo de ambiente não está ignorado pelo Git"
  [[ -n "$EXPECTED_REPOSITORY" ]] || fail "repositório esperado ausente"
  [[ -z "$(git status --porcelain)" ]] || fail "checkout contém alterações locais"
  origin="$(git remote get-url origin)"
  case "$origin" in
    "https://github.com/$EXPECTED_REPOSITORY"|"https://github.com/$EXPECTED_REPOSITORY.git"|"git@github.com:$EXPECTED_REPOSITORY.git") ;;
    *) fail "origin Git diverge do repositório esperado" ;;
  esac
  CHECKOUT_SHA="$(git rev-parse HEAD)"
  [[ "$CHECKOUT_SHA" == "$MAINTENANCE_BASELINE_SHA" ]] || fail "baseline ativo diverge da manutenção autorizada"
  if [[ "$MODE" == "inventory" ]]; then
    local remote_sha
    remote_sha="$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')"
    [[ "$remote_sha" == "$TARGET_SHA" ]] || fail "SHA alvo não é o HEAD atual de origin/main"
  else
    git fetch --quiet origin main
    git merge-base --is-ancestor "$TARGET_SHA" origin/main || fail "SHA alvo não pertence à main atual"
    git diff --quiet "$CHECKOUT_SHA" "$TARGET_SHA" -- docker/ || fail "alteração de Compose/Docker exige outro plano"
    local migration_paths
    migration_paths="$(git diff --name-only "$CHECKOUT_SHA" "$TARGET_SHA" -- backend/migrations/)"
    [[ -z "$migration_paths" || "$migration_paths" == "backend/migrations/versions/20261016_0082_facial_conditional_consent.py" ]] \
      || fail "migration fora do escopo aprovado"
  fi
  ACTIVE_SHA="$CHECKOUT_SHA"
  local api_id api_version
  api_id="$(compose ps -q api)"
  [[ -n "$api_id" && "$(wc -l <<<"$api_id" | tr -d ' ')" == "1" ]] || fail "API ativa não é única"
  api_version="$(docker inspect --format '{{json .Config.Env}}' "$api_id" \
    | python3 -c 'import json,sys; values=json.load(sys.stdin); print(next((v.split("=",1)[1] for v in values if v.startswith("APP_VERSION=")), ""))')"
  [[ "$api_version" =~ ^[0-9a-f]{40}$ && "$api_version" == "$CHECKOUT_SHA" ]] \
    || fail "metadado de versão da API diverge do checkout"
  COMPOSE_APP_VERSION="$api_version"
  DATABASE_REVISION="$(database_revision)"
  [[ "$MODE" != "release" || "$DATABASE_REVISION" == "$EXPECTED_DATABASE_REVISION" ]] \
    || fail "revisão do banco diverge do preflight aprovado"
}

runtime_snapshot() {
  local service id project actual_service workdir files hash health image config_hash hashes
  require_existing_facial_runtime
  compose config --quiet 2>/dev/null || fail "configuração Compose inválida"
  hashes="$(resolved_compose_hashes)"
  config_hash="$(printf '%s\n' "$hashes" | LC_ALL=C sort | sha256sum | awk '{print $1}')"
  for service in "${SERVICES[@]}"; do
    id="$(compose ps -q "$service")"
    [[ -n "$id" && "$(wc -l <<<"$id" | tr -d ' ')" == "1" ]] || fail "deve haver exatamente um container $service"
    project="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$id")"
    actual_service="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$id")"
    workdir="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' "$id")"
    files="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' "$id")"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id")"
    image="$(docker inspect --format '{{.Image}}' "$id")"
    hash="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.config-hash" }}' "$id")"
    [[ "$project" == "$PROJECT_NAME" && "$actual_service" == "$service" && "$workdir" == "/opt/markina-gallery/docker" && "$files" == "$COMPOSE_FILE_LABEL" ]] || fail "identidade do container $service diverge do inventário"
    local expected_hash
    expected_hash="$(awk -v service="$service" '$1 == service {print $2}' <<<"$hashes")"
    expected_hash="${expected_hash#sha256:}"
    [[ "$expected_hash" =~ ^[0-9a-f]{64}$ ]] || fail "hash resolvido de $service inválido"
    [[ "$hash" == "$expected_hash" ]] || fail "configuração ativa de $service diverge do Compose"
    [[ "$health" == "healthy" ]] || fail "container $service não está saudável"
    printf '%s|%s|%s|%s|%s\n' "$service" "$id" "$image" "$hash" "$health"
  done
  local nginx_id nginx_ports
  nginx_id="$(compose ps -q nginx)"
  [[ -n "$nginx_id" ]] || fail "nginx do projeto não está ativo"
  nginx_ports="$(docker inspect --format '{{json .NetworkSettings.Ports}}' "$nginx_id")"
  [[ "$nginx_ports" == '{"80/tcp":[{"HostIp":"127.0.0.1","HostPort":"8080"}]}' ]] || fail "bind do nginx diverge do inventário aprovado"
  echo "nginx=$nginx_id ports=$nginx_ports"
  printf 'compose_config=%s\n' "$config_hash"
}

fingerprint() {
  { printf '%s\n' "inventory" "$TARGET_SHA" "$ACTIVE_SHA" "$CHECKOUT_SHA" "$EXPECTED_URL" "database_revision=$DATABASE_REVISION"; runtime_snapshot; } | sha256sum | awk '{print $1}'
}

inventory() {
  verify_repository
  compose config --quiet || fail "configuração Compose inválida"
  echo "Inventário somente leitura Pick-your-Pic"
  echo "host=$(hostname) projeto=$PROJECT_NAME domínio=$EXPECTED_URL bind_nginx=verificado_por_container"
  echo "checkout_sha=$CHECKOUT_SHA target_sha=$TARGET_SHA"
  printf 'database_revision=%s target_database_revision=%s\n' "$DATABASE_REVISION" "$TARGET_DATABASE_REVISION"
  runtime_snapshot
  printf 'capacidade_host='
  awk '/MemTotal|MemAvailable/ {printf "%s=%s%s ", $1, $2, $3} END {print ""}' /proc/meminfo
  df -Pk /var/lib/docker | awk 'NR == 2 {print "disco_docker_kib_livre=" $4 " uso=" $5}'
  for path in /healthz /api/health /; do curl -fsS --max-time 10 "$EXPECTED_URL$path" -o /dev/null || fail "healthcheck HTTPS falhou em $path"; done
  echo "healthchecks_https=healthz,api-health,web:200"
  local fp
  fp="$(fingerprint)"
  printf 'approval_fingerprint=%s\n' "$fp"
  echo "impacto=web,api,face-search-worker; migration aditiva facial 20261014_0081 -> 20261016_0082; pode haver breve indisponibilidade e atraso de fila"
  echo "rollback=tags de imagem e SHA anterior preservados; restaurar somente os três serviços após novo inventário/aprovação"
  echo "nenhum comando de mutação foi executado"
}

release() {
  local current_fp service id image ref tag
  verify_repository
  current_fp="$(fingerprint)"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "inventário mudou desde a aprovação; nada foi alterado"
  for service in "${SERVICES[@]}"; do
    id="$(compose ps -q "$service")"
    image="$(docker inspect --format '{{.Image}}' "$id")"
    ref="$(docker inspect --format '{{.Config.Image}}' "$id")"
    tag="$PROJECT_NAME-rollback-$service-$ACTIVE_SHA"
    docker image tag "$image" "$tag"
    printf '%s\n' "$tag" > "$STATE_DIR/facial-$service-rollback-image"
    printf '%s\n' "$ref" > "$STATE_DIR/facial-$service-image-ref"
  done
  printf '%s\n' "$ACTIVE_SHA" > "$STATE_DIR/facial-previous.sha"
  printf '%s\n' "$TARGET_SHA" > "$STATE_DIR/facial-in-flight.sha"
  git switch --detach "$TARGET_SHA" >/dev/null
  COMPOSE_APP_VERSION="$TARGET_SHA"
  compose config --quiet || fail "configuração Compose alvo inválida"
  compose build "${SERVICES[@]}"
  # O build pode ser longo: recusa mudança de containers/ambiente ocorrida
  # desde o inventário aprovado, mantendo a versão ativa na comparação.
  current_fp="$(COMPOSE_APP_VERSION="$ACTIVE_SHA" fingerprint)"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "inventário mudou durante o build; serviços preservados"
  [[ "$(COMPOSE_APP_VERSION="$ACTIVE_SHA" database_revision)" == "$EXPECTED_DATABASE_REVISION" ]] \
    || fail "revisão do banco mudou após inventário; migration não aplicada"
  compose run --rm --no-deps api python -m alembic upgrade "$TARGET_DATABASE_REVISION"
  local migrated_revision migration_output migration_revisions
  migration_output="$(compose run --rm --no-deps api python -m alembic current 2>/dev/null)" \
    || fail "não foi possível confirmar revisão após migration"
  migration_revisions="$(sed -nE 's/^([0-9]{8}_[0-9]{4})( .*)?$/\1/p' <<<"$migration_output")"
  [[ "$(wc -l <<<"$migration_revisions" | tr -d ' ')" == "1" ]] || fail "migration deixou revisões ambíguas"
  migrated_revision="$migration_revisions"
  [[ "$migrated_revision" == "$TARGET_DATABASE_REVISION" ]] || fail "migration aprovada não foi confirmada"
  compose up -d --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"
  runtime_snapshot
  compose exec -T nginx nginx -t || fail "configuração do nginx Markina inválida"
  compose exec -T nginx nginx -s reload || fail "reload do nginx Markina falhou"
  for path in /healthz /api/health /; do curl -fsS --max-time 15 "$EXPECTED_URL$path" -o /dev/null || fail "smoke HTTPS falhou em $path"; done
  printf '%s\n' "$TARGET_SHA" > "$STATE_DIR/facial-last-healthy.sha"
  rm -f "$STATE_DIR/facial-in-flight.sha"
  printf '%s %s release-facial-services %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ACTIVE_SHA" "$TARGET_SHA" >> "$STATE_DIR/facial-history.log"
  echo "release saudável: $TARGET_SHA; serviços=web,api,face-search-worker"
}

main() {
  parse_arguments "$@"
  [[ "$EXPECTED_URL" == "$PUBLIC_URL" ]] || fail "domínio diverge do inventário aprovado"
  if [[ "$MODE" == "inventory" ]]; then inventory; else release; fi
}

if [[ "${BASH_SOURCE[0]:-$0}" == "$0" ]]; then main "$@"; fi
