#!/usr/bin/env bash
# Release manual do serviço web na produção Pick-your-Pic.
# Não substitui deploy-homolog.sh e nunca altera outros serviços.
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly EXPECTED_HOST="clearbudget-vnic"
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
WEB_CONTAINER=""
WEB_CONFIG_HASH=""
TARGET_CONFIG_HASH=""
WEB_STATUS=""
WEB_IMAGE_ID=""
NGINX_CONTAINER=""
NGINX_PORTS=""

fail() {
  echo "deploy-prod-web: $*" >&2
  return 1
}

usage() {
  cat >&2 <<'EOF'
Uso:
  MARKINA_EXPECTED_REPOSITORY=owner/repo bash scripts/deploy-prod-web.sh --mode inventory --sha <sha-completo>
  MARKINA_EXPECTED_REPOSITORY=owner/repo bash scripts/deploy-prod-web.sh --mode release --sha <sha-completo> --approval-code <codigo-do-inventario>
  MARKINA_EXPECTED_REPOSITORY=owner/repo bash scripts/deploy-prod-web.sh --mode rollback-inventory --sha <sha-anterior>
  MARKINA_EXPECTED_REPOSITORY=owner/repo bash scripts/deploy-prod-web.sh --mode rollback --sha <sha-anterior> --approval-code <codigo-do-inventario>
EOF
}

compose() {
  local files=(--env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE")
  local file
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do
    files+=(-f "$file")
  done
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
  [[ "$MODE" == "inventory" || "$MODE" == "release" || "$MODE" == "rollback-inventory" || "$MODE" == "rollback" ]] || fail "--mode deve ser inventory, release, rollback-inventory ou rollback"
  [[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "--sha deve conter 40 caracteres hexadecimais minúsculos"
  if [[ "$MODE" == "release" || "$MODE" == "rollback" ]]; then
    [[ "$APPROVAL_CODE" =~ ^[0-9a-f]{64}$ ]] || fail "--approval-code deve ser o código de 64 caracteres exibido pelo inventário"
  fi
}

read_state_sha() {
  local path="$1" value
  [[ -f "$path" ]] || return 1
  value="$(<"$path")"
  [[ "$value" =~ ^[0-9a-f]{40}$ ]] || fail "registro de SHA inválido em $path"
  printf '%s\n' "$value"
}

active_web_sha() {
  local value
  value="$(read_state_sha "$STATE_DIR/web-in-flight.sha" 2>/dev/null || read_state_sha "$STATE_DIR/web-last-healthy.sha" 2>/dev/null || read_state_sha "$STATE_DIR/last-healthy.sha")" \
    || fail "não há SHA saudável registrado para identificar a versão atualmente servida"
  printf '%s\n' "$value"
}

verify_repository() {
  local origin_url
  [[ "$(hostname)" == "$EXPECTED_HOST" ]] || fail "host diverge do inventário aprovado"
  [[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "execução permitida somente em $PROJECT_ROOT"
  [[ "$(git rev-parse --show-toplevel 2>/dev/null)" == "$PROJECT_ROOT" ]] || fail "diretório não é o checkout esperado"
  [[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" ]] || fail "Compose ou arquivo de ambiente aprovado não encontrado"
  local file
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do
    [[ -f "$file" ]] || fail "arquivo Compose ativo do inventário não encontrado: $file"
  done
  [[ -d "$STATE_DIR" ]] || fail "diretório de estado de deploy não existe; bootstrap requer revisão humana"
  git check-ignore -q "$ENV_FILE" || fail "arquivo de ambiente não está protegido pelo ignore do Git"
  [[ -n "$EXPECTED_REPOSITORY" ]] || fail "MARKINA_EXPECTED_REPOSITORY é obrigatório"
  [[ -z "$(git status --porcelain)" ]] || fail "checkout possui alterações locais; nenhuma ação foi executada"

  origin_url="$(git remote get-url origin 2>/dev/null)" || fail "não foi possível verificar o origin Git"
  case "$origin_url" in
    "https://github.com/$EXPECTED_REPOSITORY"|"https://github.com/$EXPECTED_REPOSITORY.git"|"git@github.com:$EXPECTED_REPOSITORY.git") ;;
    *) fail "origin não corresponde ao repositório aprovado" ;;
  esac
  git show-ref --verify --quiet refs/remotes/origin/main || fail "origin/main ausente; atualize as referências antes do inventário"
  git cat-file -e "${TARGET_SHA}^{commit}" 2>/dev/null || fail "SHA alvo não existe neste checkout"
  git merge-base --is-ancestor "$TARGET_SHA" origin/main || fail "SHA alvo não pertence à história atual de origin/main"
  CHECKOUT_SHA="$(git rev-parse HEAD)"
  git diff --quiet "$CHECKOUT_SHA" "$TARGET_SHA" -- docker/ \
    || fail "SHA alvo altera arquivos Docker/Compose; este release aceita somente código web"
  ACTIVE_SHA="$(active_web_sha)"
  if [[ -f "$STATE_DIR/web-in-flight.sha" && "$MODE" != "rollback-inventory" && "$MODE" != "rollback" ]]; then
    fail "release anterior sem validação conclusiva; faça inventário e rollback do SHA web anterior"
  fi

  # A configuração resolvida é validada sem imprimir a saída, que poderia conter valores do ambiente.
  compose config --quiet || fail "configuração Compose inválida para o ambiente aprovado"
  TARGET_CONFIG_HASH="$(compose config --hash web | awk '$1 == "web" {print $2}')"
  TARGET_CONFIG_HASH="${TARGET_CONFIG_HASH#sha256:}"
  [[ "$TARGET_CONFIG_HASH" =~ ^[0-9a-f]{64}$ ]] || fail "não foi possível calcular a impressão digital da configuração do web"
}

verify_runtime_web() {
  local project_label service_label working_dir config_files runtime_hash nginx_id ports
  WEB_CONTAINER="$(compose ps -q web)"
  [[ -n "$WEB_CONTAINER" && "$(wc -l <<<"$WEB_CONTAINER" | tr -d ' ')" == "1" ]] \
    || fail "deve existir exatamente um contêiner web no projeto aprovado"
  project_label="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$WEB_CONTAINER")"
  service_label="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$WEB_CONTAINER")"
  working_dir="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' "$WEB_CONTAINER")"
  config_files="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' "$WEB_CONTAINER")"
  runtime_hash="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.config-hash" }}' "$WEB_CONTAINER")"
  WEB_STATUS="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$WEB_CONTAINER")"
  WEB_IMAGE_ID="$(docker inspect --format '{{.Image}}' "$WEB_CONTAINER")"

  [[ "$project_label" == "$PROJECT_NAME" && "$service_label" == "web" ]] || fail "contêiner ativo não pertence ao serviço web do projeto esperado"
  [[ "$working_dir" == "$COMPOSE_WORKING_DIR" ]] || fail "diretório Compose do runtime diverge do inventário esperado"
  [[ "$config_files" == "$COMPOSE_FILE_LABEL" ]] || fail "conjunto de arquivos Compose ativos diverge; revisão humana necessária"
  [[ "$runtime_hash" == "$TARGET_CONFIG_HASH" ]] || fail "configuração efetiva diverge da configuração ativa do web; nenhuma alteração foi executada"
  if [[ "$MODE" != "rollback-inventory" && "$MODE" != "rollback" && "$WEB_STATUS" != "healthy" ]]; then
    fail "web não está saudável antes do release: $WEB_STATUS"
  fi

  WEB_CONFIG_HASH="$runtime_hash"
  nginx_id="$(compose ps -q nginx)"
  [[ -n "$nginx_id" ]] || fail "nginx da Markina não está ativo para confirmar a porta local"
  ports="$(docker inspect --format '{{json .NetworkSettings.Ports}}' "$nginx_id")"
  [[ "$ports" == '{"80/tcp":[{"HostIp":"127.0.0.1","HostPort":"8080"}]}' ]] \
    || fail "portas do nginx divergem do inventário aprovado"
  NGINX_CONTAINER="$nginx_id"
  NGINX_PORTS="$ports"
  echo "Portas publicadas pelo nginx Markina (metadados Docker): $ports"
}

approval_fingerprint() {
  local mode="$1" sha="$2"
  printf '%s\n' \
    "$mode" "$sha" "$ACTIVE_SHA" "$CHECKOUT_SHA" "$WEB_CONTAINER" "$WEB_STATUS" \
    "$WEB_IMAGE_ID" "$WEB_CONFIG_HASH" "$TARGET_CONFIG_HASH" "$ENV_FILE" "$PUBLIC_URL" \
    "$EXPECTED_HOST" "$COMPOSE_FILE_LABEL" "$NGINX_CONTAINER" "$NGINX_PORTS" \
    | sha256sum | awk '{print $1}'
}

inventory() {
  local code approval_mode
  verify_repository
  verify_runtime_web
  if [[ "$MODE" == "rollback-inventory" || "$MODE" == "rollback" ]]; then
    local expected_previous
    expected_previous="$(read_state_sha "$STATE_DIR/web-previous.sha")" || fail "não há SHA anterior de web registrado para rollback"
    [[ "$TARGET_SHA" == "$expected_previous" ]] || fail "rollback só aceita o SHA anterior registrado: $expected_previous"
  fi
  approval_mode="release"
  [[ "$MODE" == "rollback-inventory" || "$MODE" == "rollback" ]] && approval_mode="rollback"
  code="$(approval_fingerprint "$approval_mode" "$TARGET_SHA")"

  echo "Inventário somente-leitura da Pick-your-Pic"
  echo "host=$(hostname)"
  echo "project=$PROJECT_NAME"
  echo "compose=$PROJECT_ROOT/$COMPOSE_FILE"
  echo "compose_files=$COMPOSE_FILE_LABEL"
  echo "arquivo_ambiente=$PROJECT_ROOT/$ENV_FILE (valores omitidos; rótulo homolog confirmado em uso real pelo proprietário)"
  echo "containers_do_projeto (somente leitura):"
  docker ps --filter "label=com.docker.compose.project=$PROJECT_NAME" --format '{{.Names}}|{{.Status}}|{{.Ports}}'
  echo "web_container=$WEB_CONTAINER status=$WEB_STATUS image_id=$WEB_IMAGE_ID"
  echo "checkout_sha=$CHECKOUT_SHA sha_web_ultimo_saudavel=$ACTIVE_SHA sha_alvo=$TARGET_SHA"
  echo "commit_alvo=$TARGET_SHA"
  echo "web_config_hash=$WEB_CONFIG_HASH subdominio=$(printf '%s' "$PUBLIC_URL" | sed 's#https://##')"
  echo "sha_web_versao_conhecida=$ACTIVE_SHA"
  if [[ -f "$STATE_DIR/web-in-flight.sha" ]]; then
    echo "sha_web_tentativa=$(<"$STATE_DIR/web-in-flight.sha")"
  fi
  echo "escopo=serviço web somente; api db redis worker nginx e recursos compartilhados preservados"
  echo "impacto=breve interrupção pode ocorrer durante a recriação; sem garantia de zero downtime"
  if [[ "$MODE" == "rollback-inventory" || "$MODE" == "rollback" ]]; then
    echo "rollback_sha=não aplicável"
  else
    echo "rollback_sha=$ACTIVE_SHA"
  fi
  echo "approval_code=$code"
}

verify_approval() {
  local expected approval_mode="release"
  [[ "$MODE" == "rollback" ]] && approval_mode="rollback"
  inventory >/dev/null
  expected="$(approval_fingerprint "$approval_mode" "$TARGET_SHA")"
  [[ "$APPROVAL_CODE" == "$expected" ]] || fail "inventário mudou ou código de aprovação não corresponde; gere novo inventário"
}

write_sha() {
  local name="$1" value="$2" temp
  temp="$(mktemp "$STATE_DIR/.${name}.XXXXXX")"
  printf '%s\n' "$value" > "$temp"
  chmod 600 "$temp"
  mv "$temp" "$STATE_DIR/$name"
}

preserve_current_web_image() {
  docker image tag "$WEB_IMAGE_ID" "$PROJECT_NAME-web:production-web-$ACTIVE_SHA"
}

restore_saved_web_image() {
  local saved_image="$PROJECT_NAME-web:production-web-$TARGET_SHA"
  docker image inspect "$saved_image" >/dev/null 2>&1 || fail "imagem imutável do SHA de rollback não está disponível: $TARGET_SHA"
  docker image tag "$saved_image" "$PROJECT_NAME-web"
}

switch_to_target() {
  local old_checkout="$CHECKOUT_SHA"
  git switch --detach "$TARGET_SHA" >/dev/null || fail "não foi possível selecionar o SHA aprovado"
  TARGET_CONFIG_HASH="$(compose config --hash web | awk '$1 == "web" {print $2}')"
  TARGET_CONFIG_HASH="${TARGET_CONFIG_HASH#sha256:}"
  if [[ "$TARGET_CONFIG_HASH" != "$WEB_CONFIG_HASH" ]]; then
    git switch --detach "$old_checkout" >/dev/null || true
    fail "o commit alvo altera a configuração do serviço web; este fluxo aceita somente release de código web"
  fi
}

check_web_after_change() {
  local container status attempt
  container="$(compose ps -q web)"
  [[ -n "$container" ]] || fail "contêiner web ausente após a operação"
  for attempt in $(seq 1 30); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$status" == "healthy" ]] && break
    sleep 2
  done
  [[ "$status" == "healthy" ]] || fail "web não ficou saudável após a operação: $status"
  curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_URL/healthz" >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_URL/api/health" >/dev/null
  curl --fail --silent --show-error --retry 5 --retry-delay 2 "$PUBLIC_URL/" >/dev/null
}

build_web_image() {
  compose build web
}

recreate_web_only() {
  compose up -d --no-deps --no-build web
}

execute_release() {
  verify_approval
  write_sha "web-previous.sha" "$ACTIVE_SHA"
  preserve_current_web_image
  switch_to_target
  build_web_image
  write_sha "web-in-flight.sha" "$TARGET_SHA"
  recreate_web_only
  check_web_after_change
  write_sha "web-last-healthy.sha" "$TARGET_SHA"
  rm -f "$STATE_DIR/web-in-flight.sha"
  printf '%s %s release-web %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ACTIVE_SHA" "$TARGET_SHA" >> "$STATE_DIR/web-history.log"
  echo "release web saudável: $TARGET_SHA; smoke tests HTTPS concluídos"
}

execute_rollback() {
  verify_approval
  preserve_current_web_image
  switch_to_target
  restore_saved_web_image
  write_sha "web-in-flight.sha" "$TARGET_SHA"
  recreate_web_only
  check_web_after_change
  write_sha "web-last-healthy.sha" "$TARGET_SHA"
  rm -f "$STATE_DIR/web-in-flight.sha"
  write_sha "web-previous.sha" "$ACTIVE_SHA"
  printf '%s %s rollback-web %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ACTIVE_SHA" "$TARGET_SHA" >> "$STATE_DIR/web-history.log"
  echo "rollback web saudável: $TARGET_SHA; serviços de dados e backend não foram recriados"
}

main() {
  parse_arguments "$@"
  if [[ "$MODE" == "rollback" ]]; then
    execute_rollback
  elif [[ "$MODE" == "release" ]]; then
    execute_release
  elif [[ "$MODE" == "rollback-inventory" ]]; then
    inventory
  else
    inventory
  fi
}

if [[ "${BASH_SOURCE[0]-$0}" == "$0" ]]; then
  main "$@"
fi
