#!/usr/bin/env bash
# Release coordenado da aplicação de produção: somente api e web.
set -Eeuo pipefail
umask 077

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/deploy-prod-lock.sh"

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly COMPOSE_WORKING_DIR="/opt/markina-gallery/docker"
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

MODE=""
TARGET_SHA=""
APPROVAL_CODE=""
EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:-}"
CHECKOUT_SHA=""
ACTIVE_SHA=""
ACTIVE_SNAPSHOT=""
PREVIOUS_SNAPSHOT=""
TARGET_SNAPSHOT=""
IN_FLIGHT_SHA=""
IN_FLIGHT_SNAPSHOT=""
IN_FLIGHT_MODE=""
ROLLBACK_RETURN_SHA=""
ROLLBACK_RETURN_SNAPSHOT=""
API_CONTAINER=""
WEB_CONTAINER=""
API_STATUS=""
WEB_STATUS=""
API_IMAGE_ID=""
WEB_IMAGE_ID=""
TARGET_API_IMAGE_ID=""
TARGET_WEB_IMAGE_ID=""
SAVED_API_IMAGE_ID=""
SAVED_WEB_IMAGE_ID=""
API_CONFIG_HASH=""
WEB_CONFIG_HASH=""
TARGET_API_CONFIG_HASH=""
TARGET_WEB_CONFIG_HASH=""
AVAILABLE_BUILD_KB=""
REQUIRED_BUILD_KB=""
CURRENT_SERVICE=""
MUTATION_STARTED=0

fail() { echo "deploy-prod-app: $*" >&2; return 1; }

usage() {
  cat >&2 <<'EOF'
Uso:
  MARKINA_EXPECTED_REPOSITORY=owner/repo bash scripts/deploy-prod-app.sh --mode baseline-inventory --sha <sha-da-api-comprovado>
  MARKINA_EXPECTED_REPOSITORY=owner/repo bash scripts/deploy-prod-app.sh --mode baseline --sha <sha-da-api-comprovado> --approval-code <codigo-do-inventario>
  MARKINA_EXPECTED_REPOSITORY=owner/repo bash scripts/deploy-prod-app.sh --mode inventory --sha <sha-completo>
  MARKINA_EXPECTED_REPOSITORY=owner/repo bash scripts/deploy-prod-app.sh --mode release --sha <sha-completo> --approval-code <codigo-do-inventario>
  MARKINA_EXPECTED_REPOSITORY=owner/repo bash scripts/deploy-prod-app.sh --mode rollback-inventory --sha <sha-anterior>
  MARKINA_EXPECTED_REPOSITORY=owner/repo bash scripts/deploy-prod-app.sh --mode rollback --sha <sha-anterior> --approval-code <codigo-do-inventario>
EOF
}

compose() {
  local files=(--env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE") file
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do files+=(-f "$file"); done
  docker compose "${files[@]}" --profile facial --profile preview-adjustment "$@"
}

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode) MODE="${2:-}"; shift 2 ;;
      --sha) TARGET_SHA="${2:-}"; shift 2 ;;
      --approval-code) APPROVAL_CODE="${2:-}"; shift 2 ;;
      *) usage; fail "argumento não permitido: $1" ;;
    esac
  done
  [[ "$MODE" == inventory || "$MODE" == release || "$MODE" == rollback-inventory || "$MODE" == rollback || "$MODE" == baseline-inventory || "$MODE" == baseline ]] \
    || fail "--mode deve ser inventory, release, rollback-inventory, rollback, baseline-inventory ou baseline"
  [[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "--sha deve conter 40 caracteres hexadecimais minúsculos"
  if [[ "$MODE" == release || "$MODE" == rollback || "$MODE" == baseline ]]; then
    [[ "$APPROVAL_CODE" =~ ^[0-9a-f]{64}$ ]] || fail "--approval-code deve conter o código de 64 caracteres exibido pelo inventário"
  fi
}

read_state_sha() {
  local path="$1" value
  [[ -f "$path" ]] || return 1
  value="$(<"$path")"
  if [[ ! "$value" =~ ^[0-9a-f]{40}$ ]]; then
    fail "registro de SHA inválido em $path"
    return 1
  fi
  printf '%s\n' "$value"
}

read_snapshot() {
  local path="$1" value
  [[ -f "$path" ]] || return 1
  value="$(<"$path")"
  if [[ ! "$value" =~ ^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}-[0-9]+$ ]]; then
    fail "registro de snapshot inválido em $path"
    return 1
  fi
  printf '%s\n' "$value"
}

image_tag() { printf '%s-%s:production-app-%s' "$PROJECT_NAME" "$1" "$2"; }

verify_repository() {
  local origin_url
  [[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "execução permitida somente em $PROJECT_ROOT"
  [[ "$(git rev-parse --show-toplevel 2>/dev/null)" == "$PROJECT_ROOT" ]] || fail "diretório não é o checkout esperado"
  [[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" ]] || fail "Compose ou arquivo de ambiente aprovado não encontrado"
  local file
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do [[ -f "$file" ]] || fail "arquivo Compose ativo não encontrado: $file"; done
  [[ -d "$STATE_DIR" ]] || fail "diretório de estado de deploy não existe; reconciliação humana necessária"
  git check-ignore -q "$ENV_FILE" || fail "arquivo de ambiente não está protegido pelo ignore do Git"
  [[ -n "$EXPECTED_REPOSITORY" ]] || fail "MARKINA_EXPECTED_REPOSITORY é obrigatório"
  validate_checkout_clean
  origin_url="$(git remote get-url origin 2>/dev/null)" || fail "não foi possível verificar o origin Git"
  [[ "$origin_url" =~ github\.com[:/]${EXPECTED_REPOSITORY//\//\/}(\.git)?$ ]] || fail "origin não corresponde ao repositório aprovado"
  git show-ref --verify --quiet refs/remotes/origin/main || fail "origin/main ausente; atualize referências antes do inventário"
  validate_target_history

  if [[ "$MODE" == baseline-inventory || "$MODE" == baseline ]]; then
    [[ ! -e "$STATE_DIR/app-last-healthy.sha" && ! -e "$STATE_DIR/app-last-healthy.snapshot" ]] \
      || fail "baseline já existe ou está parcial; use inventory e reconcilie inconsistências manualmente"
    [[ ! -e "$STATE_DIR/app-in-flight.sha" ]] || fail "há tentativa interrompida; reconciliação humana necessária"
    ACTIVE_SHA=""
    ACTIVE_SNAPSHOT=""
  else
    ACTIVE_SHA="$(read_state_sha "$STATE_DIR/app-last-healthy.sha")" || fail "baseline coordenado ausente; use baseline-inventory e baseline após comprovar a origem da API"
    ACTIVE_SNAPSHOT="$(read_snapshot "$STATE_DIR/app-last-healthy.snapshot")" || fail "snapshot conjunto ausente; reconciliação humana necessária"
  fi
  if [[ -f "$STATE_DIR/app-in-flight.sha" ]]; then
    IN_FLIGHT_SHA="$(read_state_sha "$STATE_DIR/app-in-flight.sha")"
    IN_FLIGHT_SNAPSHOT="$(read_snapshot "$STATE_DIR/app-in-flight.snapshot")"
    IN_FLIGHT_MODE="$(<"$STATE_DIR/app-in-flight.mode")"
    [[ "$IN_FLIGHT_MODE" == release || "$IN_FLIGHT_MODE" == rollback ]] || fail "modo de tentativa interrompida inválido"
  fi
  if [[ "$MODE" == release ]]; then
    [[ "$TARGET_SHA" != "$ACTIVE_SHA" ]] || fail "SHA alvo já é a versão coordenada saudável"
    git merge-base --is-ancestor "$ACTIVE_SHA" "$TARGET_SHA" || fail "SHA alvo não é descendente do baseline coordenado"
    validate_release_diff_paths
  elif [[ "$MODE" == rollback-inventory || "$MODE" == rollback ]]; then
    local previous_sha
    previous_sha="$(read_state_sha "$STATE_DIR/app-previous.sha")" || fail "não há SHA anterior coordenado registrado para rollback"
    [[ "$TARGET_SHA" == "$previous_sha" ]] || fail "rollback aceita somente o SHA anterior registrado: $previous_sha"
    TARGET_SNAPSHOT="$(read_snapshot "$STATE_DIR/app-previous.snapshot")" || fail "snapshot de rollback ausente"
  fi
  if [[ -f "$STATE_DIR/app-in-flight.sha" && "$MODE" != rollback-inventory && "$MODE" != rollback ]]; then
    fail "release coordenado sem validação conclusiva; faça inventário e rollback aprovado"
  fi

  compose config --quiet || fail "configuração Compose inválida para o ambiente aprovado"
  TARGET_API_CONFIG_HASH="$(compose config --hash api | awk '$1 == "api" {print $2}')"
  TARGET_WEB_CONFIG_HASH="$(compose config --hash web | awk '$1 == "web" {print $2}')"
  TARGET_API_CONFIG_HASH="${TARGET_API_CONFIG_HASH#sha256:}"
  TARGET_WEB_CONFIG_HASH="${TARGET_WEB_CONFIG_HASH#sha256:}"
  [[ "$TARGET_API_CONFIG_HASH" =~ ^[0-9a-f]{64}$ && "$TARGET_WEB_CONFIG_HASH" =~ ^[0-9a-f]{64}$ ]] \
    || fail "não foi possível calcular hashes de configuração para API e web"
}

validate_checkout_clean() {
  [[ -z "$(git status --porcelain)" ]] || fail "checkout possui alterações locais; nenhuma ação foi executada"
}

validate_target_history() {
  if ! git cat-file -e "${TARGET_SHA}^{commit}" 2>/dev/null; then
    fail "SHA alvo não existe neste checkout"
    return 1
  fi
  if ! git merge-base --is-ancestor "$TARGET_SHA" origin/main; then
    fail "SHA alvo não pertence à história atual de origin/main"
    return 1
  fi
}

validate_release_diff_paths() {
  local changed_path
  while IFS= read -r changed_path; do
    case "$changed_path" in
      backend/migrations/*|docker/*|docker-compose*.yml|docker-compose*.yaml|.env*)
        fail "o intervalo de commits inclui migration ou configuração de infraestrutura: $changed_path"
        return 1 ;;
    esac
  done < <(git diff --name-only "$ACTIVE_SHA" "$TARGET_SHA")
}

inspect_label() { docker inspect --format "{{ index .Config.Labels \"$2\" }}" "$1"; }

service_runtime() {
  local service="$1" container project_label service_label working_dir config_files runtime_hash status image_id
  [[ "$service" == api || "$service" == web ]] || fail "serviço fora do escopo: $service"
  container="$(compose ps -q "$service")"
  [[ -n "$container" && "$(wc -l <<<"$container" | tr -d ' ')" == 1 ]] || fail "deve existir exatamente um contêiner $service no projeto aprovado"
  project_label="$(inspect_label "$container" com.docker.compose.project)"
  service_label="$(inspect_label "$container" com.docker.compose.service)"
  working_dir="$(inspect_label "$container" com.docker.compose.project.working_dir)"
  config_files="$(inspect_label "$container" com.docker.compose.project.config_files)"
  runtime_hash="$(inspect_label "$container" com.docker.compose.config-hash)"
  status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
  image_id="$(docker inspect --format '{{.Image}}' "$container")"
  [[ "$project_label" == "$PROJECT_NAME" && "$service_label" == "$service" ]] || fail "$service ativo não pertence ao projeto/serviço esperado"
  [[ "$working_dir" == "$COMPOSE_WORKING_DIR" && "$config_files" == "$COMPOSE_FILE_LABEL" ]] || fail "manifesto Compose ativo de $service diverge do inventário"
  if [[ "$MODE" != rollback-inventory && "$MODE" != rollback && "$status" != healthy ]]; then
    fail "$service não está saudável antes da operação: $status"
  fi
  if [[ "$service" == api ]]; then
    [[ "$runtime_hash" == "$TARGET_API_CONFIG_HASH" ]] || fail "configuração efetiva da API diverge do Compose aprovado"
    API_CONTAINER="$container" API_STATUS="$status" API_IMAGE_ID="$image_id" API_CONFIG_HASH="$runtime_hash"
  else
    [[ "$runtime_hash" == "$TARGET_WEB_CONFIG_HASH" ]] || fail "configuração efetiva do web diverge do Compose aprovado"
    WEB_CONTAINER="$container" WEB_STATUS="$status" WEB_IMAGE_ID="$image_id" WEB_CONFIG_HASH="$runtime_hash"
  fi
}

verify_runtime_pair() {
  local nginx_id ports
  service_runtime api
  service_runtime web
  nginx_id="$(compose ps -q nginx)"
  [[ -n "$nginx_id" ]] || fail "nginx da Markina não está ativo para confirmar a porta local"
  ports="$(docker inspect --format '{{json .NetworkSettings.Ports}}' "$nginx_id")"
  echo "Portas publicadas pelo nginx Markina (metadados Docker): $ports"
  if [[ "$MODE" == inventory || "$MODE" == release ]]; then
    validate_build_space
  else
    AVAILABLE_BUILD_KB=0
    REQUIRED_BUILD_KB=0
  fi
  if [[ "$MODE" == rollback-inventory || "$MODE" == rollback ]]; then
    SAVED_API_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$(image_tag api "$TARGET_SNAPSHOT")")" || fail "imagem preservada ausente para API/snapshot $TARGET_SNAPSHOT"
    SAVED_WEB_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$(image_tag web "$TARGET_SNAPSHOT")")" || fail "imagem preservada ausente para web/snapshot $TARGET_SNAPSHOT"
  fi
}

validate_build_space() {
  local docker_root api_size web_size
  docker_root="$(docker info --format '{{.DockerRootDir}}')"
  AVAILABLE_BUILD_KB="$(df -Pk "$docker_root" | awk 'NR == 2 {print $4}')"
  api_size="$(docker image inspect --format '{{.Size}}' "$API_IMAGE_ID")"
  web_size="$(docker image inspect --format '{{.Size}}' "$WEB_IMAGE_ID")"
  [[ "$AVAILABLE_BUILD_KB" =~ ^[0-9]+$ && "$api_size" =~ ^[0-9]+$ && "$web_size" =~ ^[0-9]+$ ]] \
    || fail "não foi possível verificar espaço e tamanho das imagens atuais"
  REQUIRED_BUILD_KB="$(((api_size + web_size) / 1024))"
  (( AVAILABLE_BUILD_KB >= REQUIRED_BUILD_KB )) || fail "espaço livre no filesystem Docker é inferior ao tamanho combinado das imagens atuais"
}

approval_fingerprint() {
  local approval_mode=release
  [[ "$MODE" == rollback-inventory || "$MODE" == rollback ]] && approval_mode=rollback
  [[ "$MODE" == baseline-inventory || "$MODE" == baseline ]] && approval_mode=baseline
  printf '%s\n' "$approval_mode" "$TARGET_SHA" "$ACTIVE_SHA" "$CHECKOUT_SHA" \
    "$API_CONTAINER" "$API_STATUS" "$API_IMAGE_ID" "$API_CONFIG_HASH" \
    "$WEB_CONTAINER" "$WEB_STATUS" "$WEB_IMAGE_ID" "$WEB_CONFIG_HASH" \
    "$TARGET_API_CONFIG_HASH" "$TARGET_WEB_CONFIG_HASH" "$ACTIVE_SNAPSHOT" "$TARGET_SNAPSHOT" "$SAVED_API_IMAGE_ID" "$SAVED_WEB_IMAGE_ID" "$AVAILABLE_BUILD_KB" "$REQUIRED_BUILD_KB" "$ENV_FILE" "$PUBLIC_URL" \
    | sha256sum | awk '{print $1}'
}

inventory() {
  local code
  verify_repository
  CHECKOUT_SHA="$(git rev-parse HEAD)"
  verify_runtime_pair
  code="$(approval_fingerprint)"
  echo "Inventário somente-leitura da aplicação Pick-your-Pic"
  echo "modo=$MODE"
  echo "host=$(hostname) project=$PROJECT_NAME"
  echo "compose=$PROJECT_ROOT/$COMPOSE_FILE compose_files=$COMPOSE_FILE_LABEL"
  echo "arquivo_ambiente=$PROJECT_ROOT/$ENV_FILE (valores omitidos)"
  echo "containers_do_projeto (somente leitura):"
  docker ps --filter "label=com.docker.compose.project=$PROJECT_NAME" --format '{{.Names}}|{{.Status}}|{{.Ports}}'
  echo "api_container=$API_CONTAINER status=$API_STATUS image_id=$API_IMAGE_ID config_hash=$API_CONFIG_HASH"
  echo "web_container=$WEB_CONTAINER status=$WEB_STATUS image_id=$WEB_IMAGE_ID config_hash=$WEB_CONFIG_HASH"
  if [[ "$MODE" == rollback-inventory || "$MODE" == rollback ]]; then
    echo "rollback_api_image_id=$SAVED_API_IMAGE_ID rollback_web_image_id=$SAVED_WEB_IMAGE_ID"
  fi
  echo "checkout_sha=$CHECKOUT_SHA baseline_coordenado=$ACTIVE_SHA sha_alvo=$TARGET_SHA"
  echo "ultimo_snapshot_coordenado=$ACTIVE_SNAPSHOT${TARGET_SNAPSHOT:+ snapshot_rollback=$TARGET_SNAPSHOT}"
  echo "target_api_config_hash=$TARGET_API_CONFIG_HASH target_web_config_hash=$TARGET_WEB_CONFIG_HASH"
  echo "docker_space_available_kb=$AVAILABLE_BUILD_KB minimum_current_image_space_kb=$REQUIRED_BUILD_KB"
  echo "subdominio=$PUBLIC_URL"
  echo "escopo=api e web somente; db redis worker nginx e recursos compartilhados preservados"
  echo "impacto=troca sequencial pode causar interrupção breve; sem garantia de zero downtime"
  echo "rollback_sha=$( [[ "$MODE" == rollback-inventory ]] && echo 'não aplicável' || echo "$(read_state_sha "$STATE_DIR/app-previous.sha" 2>/dev/null || echo "$ACTIVE_SHA")" )"
  echo "approval_code=$code"
}

verify_approval() {
  local expected
  inventory >/dev/null
  expected="$(approval_fingerprint)"
  [[ "$APPROVAL_CODE" == "$expected" ]] || fail "inventário mudou ou código de aprovação não corresponde; gere novo inventário"
}

write_state() {
  local name="$1" value="$2" temp
  temp="$(mktemp "$STATE_DIR/.${name}.XXXXXX")"
  printf '%s\n' "$value" > "$temp"
  chmod 600 "$temp"
  mv "$temp" "$STATE_DIR/$name"
}

clear_in_flight() {
  rm -f "$STATE_DIR/app-in-flight.sha" "$STATE_DIR/app-in-flight.snapshot" "$STATE_DIR/app-in-flight.mode" \
    "$STATE_DIR/app-rollback-return.sha" "$STATE_DIR/app-rollback-return.snapshot"
}

append_history() {
  printf '%s %s %s %s api=%s web=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" "$3" "$4" "$5" \
    >> "$STATE_DIR/app-history.log"
}

failure_record() {
  printf '%s mode=%s target=%s failed_service=%s exit=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$MODE" "$2" "$3" "$1"
}

handle_operation_error() {
  local status="$1"
  trap - ERR
  if (( MUTATION_STARTED == 1 )) && [[ -f "$STATE_DIR/app-in-flight.sha" ]]; then
    failure_record "$status" "$(<"$STATE_DIR/app-in-flight.sha")" "${CURRENT_SERVICE:-unknown}" >> "$STATE_DIR/app-history.log"
    chmod 600 "$STATE_DIR/app-history.log"
  fi
  exit "$status"
}

execute_baseline() {
  verify_approval
  TARGET_SNAPSHOT="$(date -u +%Y%m%dT%H%M%SZ)-${TARGET_SHA:0:12}-$$"
  local api_tag web_tag
  api_tag="$(image_tag api "$TARGET_SNAPSHOT")"
  web_tag="$(image_tag web "$TARGET_SNAPSHOT")"
  if docker image inspect "$api_tag" >/dev/null 2>&1 || docker image inspect "$web_tag" >/dev/null 2>&1; then
    fail "tag de snapshot de baseline já existe; gere novo inventário após reconciliação"
    return 1
  fi
  docker image tag "$API_IMAGE_ID" "$api_tag"
  docker image tag "$WEB_IMAGE_ID" "$web_tag"
  write_state "app-last-healthy.sha" "$TARGET_SHA"
  write_state "app-last-healthy.snapshot" "$TARGET_SNAPSHOT"
  append_history "none" baseline "$TARGET_SHA" "$API_IMAGE_ID" "$WEB_IMAGE_ID"
  echo "baseline registrado sem recriar serviços: api=$API_IMAGE_ID web=$WEB_IMAGE_ID sha_api=$TARGET_SHA snapshot=$TARGET_SNAPSHOT"
}

preserve_active_images() {
  docker image tag "$API_IMAGE_ID" "$(image_tag api "$PREVIOUS_SNAPSHOT")"
  docker image tag "$WEB_IMAGE_ID" "$(image_tag web "$PREVIOUS_SNAPSHOT")"
}

build_target_images() {
  local api_target web_target
  api_target="$(image_tag api "$TARGET_SNAPSHOT")"
  web_target="$(image_tag web "$TARGET_SNAPSHOT")"
  if docker image inspect "$api_target" >/dev/null 2>&1 || docker image inspect "$web_target" >/dev/null 2>&1; then
    fail "já existem imagens imutáveis para o snapshot alvo; reconciliação manual necessária"
    return 1
  fi
  compose build api web
  TARGET_API_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$PROJECT_NAME-api")"
  TARGET_WEB_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$PROJECT_NAME-web")"
  [[ "$TARGET_API_IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "build não produziu uma imagem de API identificável"
  [[ "$TARGET_WEB_IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "build não produziu uma imagem web identificável"
  docker image tag "$TARGET_API_IMAGE_ID" "$api_target"
  docker image tag "$TARGET_WEB_IMAGE_ID" "$web_target"
}

tag_for_default() {
  local service="$1" sha="$2" target
  target="$(image_tag "$service" "$sha")"
  docker image inspect "$target" >/dev/null 2>&1 || fail "imagem preservada ausente para $service/$sha"
  docker image tag "$target" "$PROJECT_NAME-$service"
}

recreate_service() {
  local service="$1"
  compose up -d --no-deps --no-build "$service"
}

wait_service_healthy() {
  local service="$1" container status attempt
  for attempt in $(seq 1 30); do
    container="$(compose ps -q "$service")"
    [[ -n "$container" ]] || { sleep 2; continue; }
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$status" == healthy ]] && return 0
    sleep 2
  done
  fail "$service não ficou saudável após a operação: ${status:-ausente}"
}

smoke_check_pair() {
  curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_URL/api/health" >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_URL/healthz" >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_URL/" >/dev/null
}

execute_release() {
  verify_approval
  switch_to_target "$CHECKOUT_SHA"
  local snapshot_time
  snapshot_time="$(date -u +%Y%m%dT%H%M%SZ)"
  PREVIOUS_SNAPSHOT="$snapshot_time-${ACTIVE_SHA:0:12}-$$"
  TARGET_SNAPSHOT="$snapshot_time-${TARGET_SHA:0:12}-$$"
  preserve_active_images
  build_target_images
  write_state "app-previous.sha" "$ACTIVE_SHA"
  write_state "app-previous.snapshot" "$PREVIOUS_SNAPSHOT"
  write_state "app-in-flight.sha" "$TARGET_SHA"
  write_state "app-in-flight.snapshot" "$TARGET_SNAPSHOT"
  write_state "app-in-flight.mode" release
  MUTATION_STARTED=1
  tag_for_default api "$TARGET_SNAPSHOT"
  tag_for_default web "$TARGET_SNAPSHOT"
  CURRENT_SERVICE=api
  recreate_service api
  wait_service_healthy api
  CURRENT_SERVICE=web
  recreate_service web
  wait_service_healthy web
  CURRENT_SERVICE=api+web-smoke
  smoke_check_pair
  CURRENT_SERVICE=""
  write_state "app-last-healthy.sha" "$TARGET_SHA"
  write_state "app-last-healthy.snapshot" "$TARGET_SNAPSHOT"
  clear_in_flight
  append_history "$ACTIVE_SHA" release-app "$TARGET_SHA" "$TARGET_API_IMAGE_ID" "$TARGET_WEB_IMAGE_ID"
  echo "release coordenado saudável: $TARGET_SHA; API, web e smoke checks HTTPS concluídos"
}

switch_to_target() {
  local checkout="$1"
  git switch --detach "$TARGET_SHA" >/dev/null || fail "não foi possível selecionar o SHA aprovado"
  local api_hash web_hash
  api_hash="$(compose config --hash api | awk '$1 == "api" {print $2}')"; api_hash="${api_hash#sha256:}"
  web_hash="$(compose config --hash web | awk '$1 == "web" {print $2}')"; web_hash="${web_hash#sha256:}"
  if [[ "$api_hash" != "$API_CONFIG_HASH" || "$web_hash" != "$WEB_CONFIG_HASH" ]]; then
    git switch --detach "$checkout" >/dev/null || true
    fail "o SHA alvo altera configuração de API/web; release coordenado aceita somente mudanças de código"
  fi
}

execute_rollback() {
  verify_approval
  if [[ "$IN_FLIGHT_MODE" == rollback ]]; then
    ROLLBACK_RETURN_SHA="$(read_state_sha "$STATE_DIR/app-rollback-return.sha")" || fail "estado de retorno de rollback interrompido ausente"
    ROLLBACK_RETURN_SNAPSHOT="$(read_snapshot "$STATE_DIR/app-rollback-return.snapshot")" || fail "snapshot de retorno de rollback interrompido ausente"
  elif [[ "$IN_FLIGHT_MODE" == release ]]; then
    ROLLBACK_RETURN_SHA="$IN_FLIGHT_SHA"
    ROLLBACK_RETURN_SNAPSHOT="$IN_FLIGHT_SNAPSHOT"
    write_state "app-rollback-return.sha" "$ROLLBACK_RETURN_SHA"
    write_state "app-rollback-return.snapshot" "$ROLLBACK_RETURN_SNAPSHOT"
  else
    local snapshot_time
    snapshot_time="$(date -u +%Y%m%dT%H%M%SZ)"
    PREVIOUS_SNAPSHOT="$snapshot_time-${ACTIVE_SHA:0:12}-$$"
    preserve_active_images
    ROLLBACK_RETURN_SHA="$ACTIVE_SHA"
    ROLLBACK_RETURN_SNAPSHOT="$PREVIOUS_SNAPSHOT"
    write_state "app-rollback-return.sha" "$ROLLBACK_RETURN_SHA"
    write_state "app-rollback-return.snapshot" "$ROLLBACK_RETURN_SNAPSHOT"
  fi
  tag_for_default api "$TARGET_SNAPSHOT"
  tag_for_default web "$TARGET_SNAPSHOT"
  write_state "app-in-flight.sha" "$TARGET_SHA"
  write_state "app-in-flight.snapshot" "$TARGET_SNAPSHOT"
  write_state "app-in-flight.mode" rollback
  MUTATION_STARTED=1
  CURRENT_SERVICE=api
  recreate_service api
  wait_service_healthy api
  CURRENT_SERVICE=web
  recreate_service web
  wait_service_healthy web
  CURRENT_SERVICE=api+web-smoke
  smoke_check_pair
  CURRENT_SERVICE=""
  write_state "app-last-healthy.sha" "$TARGET_SHA"
  write_state "app-last-healthy.snapshot" "$TARGET_SNAPSHOT"
  write_state "app-previous.sha" "$ROLLBACK_RETURN_SHA"
  write_state "app-previous.snapshot" "$ROLLBACK_RETURN_SNAPSHOT"
  clear_in_flight
  append_history "$ACTIVE_SHA" rollback-app "$TARGET_SHA" "$SAVED_API_IMAGE_ID" "$SAVED_WEB_IMAGE_ID"
  echo "rollback coordenado saudável: $TARGET_SHA; API, web e smoke checks HTTPS concluídos"
}

main() {
  parse_arguments "$@"
  acquire_production_deploy_lock "$STATE_DIR" app || fail "não foi possível obter o lock compartilhado de produção"
  trap 'handle_operation_error "$?"' ERR
  case "$MODE" in
    baseline) execute_baseline ;;
    release) execute_release ;;
    rollback) execute_rollback ;;
    inventory|rollback-inventory|baseline-inventory) inventory ;;
  esac
}

if [[ "${BASH_SOURCE[0]-$0}" == "$0" ]]; then main "$@"; fi
