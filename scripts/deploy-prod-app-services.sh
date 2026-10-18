#!/usr/bin/env bash
# Inventário e release API/web isolados do fluxo de manutenção facial.
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
readonly SERVICES=(api web)
readonly EXPECTED_DATABASE_REVISION="20261017_0084"

MODE=""
TARGET_SHA=""
APPROVAL_FINGERPRINT=""
ROLLBACK_SHA=""
EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:-}"
EXPECTED_URL="${MARKINA_PUBLIC_BASE_URL:-$PUBLIC_URL}"
CHECKOUT_SHA=""
ACTIVE_SHA=""
COMPOSE_APP_VERSION=""
DATABASE_REVISION=""
production_deploy_lock_fd=9

fail() { echo "deploy-prod-app-services: $*" >&2; exit 1; }

acquire_app_deploy_lock() {
  [[ -d "$STATE_DIR" ]] || fail "diretório de estado ausente; nenhuma operação foi executada"
  command -v flock >/dev/null 2>&1 || fail "flock indisponível; nenhuma operação foi executada"
  exec {production_deploy_lock_fd}>"$STATE_DIR/production-release.lock"
  flock -n "$production_deploy_lock_fd" || fail "outro inventário ou release de produção está em andamento"
  [[ ! -e "$STATE_DIR/web-in-flight.sha" ]] \
    || fail "tentativa web-only sem conclusão; reconciliação pelo fluxo correspondente é necessária"
}

verify_database_revision() {
  [[ "$1" == "$EXPECTED_DATABASE_REVISION" ]] || fail "revisão de banco diverge do inventário aprovado"
}

verify_readonly_target_ancestry() (
  set -Eeuo pipefail
  local origin="$1" checkout_sha="$2" target_sha="$3" temp_root temp_repo fetched_sha current_sha
  temp_root="$(mktemp -d "${TMPDIR:-/tmp}/markina-app-history.XXXXXX")" \
    || fail "não foi possível criar repositório temporário de ancestralidade"
  trap 'rm -rf -- "$temp_root"' EXIT
  temp_repo="$temp_root/repository.git"
  git init --quiet --bare "$temp_repo" || fail "não foi possível inicializar repositório temporário"
  git -C "$temp_repo" config remote.origin.url "$origin"
  git -C "$temp_repo" config remote.origin.promisor true
  git -C "$temp_repo" config remote.origin.partialclonefilter blob:none
  git -C "$temp_repo" fetch --quiet --filter=blob:none --no-tags origin \
    refs/heads/main:refs/remotes/origin/main \
    || fail "não foi possível obter histórico filtrado de main"
  fetched_sha="$(git -C "$temp_repo" rev-parse refs/remotes/origin/main)"
  [[ "$fetched_sha" == "$target_sha" ]] || fail "HEAD de main mudou durante o inventário"
  git -C "$temp_repo" merge-base --is-ancestor "$checkout_sha" refs/remotes/origin/main \
    || fail "SHA alvo não descende do runtime ativo"
  current_sha="$(git ls-remote "$origin" refs/heads/main | awk 'NR == 1 {print $1}')"
  [[ "$current_sha" == "$target_sha" ]] || fail "HEAD de main mudou durante o inventário"
)

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode) MODE="${2:-}"; shift 2 ;;
      --sha) TARGET_SHA="${2:-}"; shift 2 ;;
      --approval-fingerprint) APPROVAL_FINGERPRINT="${2:-}"; shift 2 ;;
      *) fail "argumento não permitido: $1" ;;
    esac
  done
  [[ "$MODE" == "inventory" || "$MODE" == "release" || "$MODE" == "rollback-inventory" || "$MODE" == "rollback" ]] \
    || fail "modo deve ser inventory, release, rollback-inventory ou rollback"
  [[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA alvo inválido"
  if [[ "$MODE" == "release" || "$MODE" == "rollback" ]]; then
    [[ "$APPROVAL_FINGERPRINT" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint obrigatório"
  fi
}

compose() {
  local files=(--env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE") file
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do files+=(-f "$file"); done
  APP_VERSION="$COMPOSE_APP_VERSION" docker compose "${files[@]}" --profile facial --profile preview-adjustment "$@" </dev/null
}

resolved_hashes() {
  compose config --format json 2>/dev/null \
    | docker compose -p "$PROJECT_NAME" -f - --profile facial --profile preview-adjustment \
      config --no-interpolate --hash api,web 2>/dev/null \
    || fail "não foi possível calcular hashes Compose resolvidos"
}

database_revision() {
  local output revisions
  output="$(compose exec -T api python -m alembic current 2>/dev/null)" || fail "consulta de schema falhou"
  revisions="$(sed -nE 's/^([0-9]{8}_[0-9]{4})( .*)?$/\1/p' <<<"$output")"
  [[ "$(wc -l <<<"$revisions" | tr -d ' ')" == 1 && "$revisions" =~ ^[0-9]{8}_[0-9]{4}$ ]] \
    || fail "schema sem revisão única"
  printf '%s\n' "$revisions"
}

verify_repository() {
  local origin remote_sha api_id api_version service
  [[ "$(hostname)" == "$EXPECTED_HOST" ]] || fail "host diverge do alvo"
  [[ "$(pwd -P)" == "$PROJECT_ROOT" && "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] || fail "checkout Markina ausente"
  [[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" && -d "$STATE_DIR" ]] || fail "Compose, ambiente ou estado ausente"
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do [[ -f "$file" ]] || fail "manifesto Compose ativo ausente"; done
  git check-ignore -q "$ENV_FILE" || fail "arquivo de ambiente não está ignorado"
  [[ -n "$EXPECTED_REPOSITORY" ]] || fail "repositório esperado ausente"
  [[ -z "$(git status --porcelain)" ]] || fail "checkout contém alterações locais"
  origin="$(git remote get-url origin)"
  case "$origin" in
    "https://github.com/$EXPECTED_REPOSITORY"|"https://github.com/$EXPECTED_REPOSITORY.git"|"git@github.com:$EXPECTED_REPOSITORY.git") ;;
    *) fail "origin Git diverge do repositório esperado" ;;
  esac
  CHECKOUT_SHA="$(git rev-parse HEAD)"
  remote_sha="$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')"
  [[ "$remote_sha" == "$TARGET_SHA" ]] || fail "SHA alvo não é o HEAD atual de origin/main"
  if [[ "$MODE" == release || "$MODE" == rollback ]]; then
    git fetch --quiet origin main
    git merge-base --is-ancestor "$CHECKOUT_SHA" "$TARGET_SHA" \
      || fail "alvo não descende do runtime ativo"
  else
    verify_readonly_target_ancestry "$origin" "$CHECKOUT_SHA" "$TARGET_SHA"
  fi
  if [[ "$MODE" == "release" ]]; then
    git diff --quiet "$CHECKOUT_SHA" "$TARGET_SHA" -- docker/ backend/migrations/ \
      || fail "Docker/Compose ou migrations fora do escopo"
    local scope_script scope_manifest
    scope_script="$(mktemp "${TMPDIR:-/tmp}/markina-app-scope.XXXXXX.py")"
    scope_manifest="$(mktemp "${TMPDIR:-/tmp}/markina-app-manifest.XXXXXX.json")"
    trap 'rm -f "$scope_script" "$scope_manifest"' RETURN
    git show "$TARGET_SHA:scripts/check_prod_app_release_scope.py" > "$scope_script" \
      || fail "verificador de escopo ausente no alvo"
    git show "$TARGET_SHA:openspec/changes/add-production-app-release-workflow/runtime-gates.json" > "$scope_manifest" \
      || fail "manifesto de runtime app ausente no alvo"
    GIT_DIR="$PROJECT_ROOT/.git" GIT_WORK_TREE="$PROJECT_ROOT" \
      python3 "$scope_script" --base "$CHECKOUT_SHA" --target "$TARGET_SHA" --manifest "$scope_manifest" \
      || fail "escopo ou blobs API/web não aprovados"
    trap - RETURN
    rm -f "$scope_script" "$scope_manifest"
  fi
  if [[ "$MODE" == "rollback-inventory" || "$MODE" == "rollback" ]]; then
    [[ -f "$STATE_DIR/app-previous.sha" ]] || fail "SHA anterior de API/web ausente"
    ROLLBACK_SHA="$(cat "$STATE_DIR/app-previous.sha")"
    [[ "$ROLLBACK_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA anterior inválido"
    git merge-base --is-ancestor "$ROLLBACK_SHA" "$CHECKOUT_SHA" \
      || fail "SHA anterior não é ancestral do runtime atual"
    for service in "${SERVICES[@]}"; do
      [[ -s "$STATE_DIR/app-$service-rollback-image" && -s "$STATE_DIR/app-$service-image-ref" ]] \
        || fail "imagem anterior de $service não está preservada"
      docker image inspect "$(cat "$STATE_DIR/app-$service-rollback-image")" >/dev/null \
        || fail "imagem anterior de $service não está disponível"
    done
  fi
  ACTIVE_SHA="$CHECKOUT_SHA"
  api_id="$(compose ps -q api)"
  [[ -n "$api_id" && "$(wc -l <<<"$api_id" | tr -d ' ')" == 1 ]] || fail "API ativa ausente ou duplicada"
  api_version="$(docker inspect --format '{{json .Config.Env}}' "$api_id" \
    | python3 -c 'import json,sys; values=json.load(sys.stdin); print(next((v.split("=",1)[1] for v in values if v.startswith("APP_VERSION=")), ""))')"
  [[ "$api_version" == "$CHECKOUT_SHA" ]] || fail "APP_VERSION da API diverge do checkout"
  COMPOSE_APP_VERSION="$api_version"
  DATABASE_REVISION="$(database_revision)"
  verify_database_revision "$DATABASE_REVISION"
}

runtime_snapshot() {
  local hashes config_hash service id project actual_service workdir files hash health image expected
  compose config --quiet 2>/dev/null || fail "configuração Compose inválida"
  hashes="$(resolved_hashes)"
  config_hash="$(printf '%s\n' "$hashes" | LC_ALL=C sort | sha256sum | awk '{print $1}')"
  for service in "${SERVICES[@]}"; do
    id="$(compose ps -q "$service")"
    [[ -n "$id" && "$(wc -l <<<"$id" | tr -d ' ')" == 1 ]] || fail "container $service ausente ou duplicado"
    project="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$id")"
    actual_service="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$id")"
    workdir="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' "$id")"
    files="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' "$id")"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id")"
    image="$(docker inspect --format '{{.Image}}' "$id")"
    hash="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.config-hash" }}' "$id")"
    [[ "$project" == "$PROJECT_NAME" && "$actual_service" == "$service" \
      && "$workdir" == "/opt/markina-gallery/docker" && "$files" == "$COMPOSE_FILE_LABEL" ]] \
      || fail "identidade do container $service diverge"
    expected="$(awk -v service="$service" '$1 == service {print $2}' <<<"$hashes")"
    expected="${expected#sha256:}"
    [[ "$expected" =~ ^[0-9a-f]{64}$ && "$hash" == "$expected" ]] || fail "hash Compose de $service diverge"
    [[ "$health" == healthy ]] || fail "container $service não está saudável"
    printf '%s|%s|%s|%s|%s\n' "$service" "$id" "$image" "$hash" "$health"
  done
  local nginx_id ports
  nginx_id="$(compose ps -q nginx)"
  [[ -n "$nginx_id" ]] || fail "nginx Markina ausente"
  ports="$(docker inspect --format '{{json .NetworkSettings.Ports}}' "$nginx_id")"
  [[ "$ports" == '{"80/tcp":[{"HostIp":"127.0.0.1","HostPort":"8080"}]}' ]] || fail "bind nginx diverge"
  printf 'nginx_bind=%s\ncompose_config=%s\n' "$ports" "$config_hash"
}

fingerprint() {
  local fingerprint_mode="$MODE"
  [[ "$MODE" == release ]] && fingerprint_mode=inventory
  [[ "$MODE" == rollback ]] && fingerprint_mode=rollback-inventory
  { printf '%s\n' "$fingerprint_mode" "$TARGET_SHA" "$ROLLBACK_SHA" "$ACTIVE_SHA" "$CHECKOUT_SHA" "$EXPECTED_URL" "database_revision=$DATABASE_REVISION"; runtime_snapshot; } \
    | sha256sum | awk '{print $1}'
}

inventory() {
  verify_repository
  echo "Inventário de release API/web Pick-your-Pic"
  printf 'host=%s projeto=%s domínio=%s checkout_sha=%s target_sha=%s\n' \
    "$(hostname)" "$PROJECT_NAME" "$EXPECTED_URL" "$CHECKOUT_SHA" "$TARGET_SHA"
  printf 'serviços=api,web revisão_schema=%s portas=nginx:127.0.0.1:8080\n' "$DATABASE_REVISION"
  runtime_snapshot
  for path in /healthz /api/health /; do curl -fsS --max-time 10 "$EXPECTED_URL$path" -o /dev/null || fail "healthcheck HTTPS falhou em $path"; done
  printf 'healthchecks_https=healthz,api-health,web:200\n'
  printf 'approval_fingerprint=%s\n' "$(fingerprint)"
  echo "impacto=api,web; sem migrations; breve interrupção da API pode afetar temporariamente todas as rotas, inclusive o Monitor; implementação e dados do Monitor permanecem intocados"
  echo "rollback=imagens anteriores e SHA ativo preservados; novo inventário e aprovação antes de qualquer restauração"
  echo "nenhum comando mutável foi executado"
}

rollback_inventory() {
  verify_repository
  runtime_snapshot
  for path in /healthz /api/health /; do curl -fsS --max-time 10 "$EXPECTED_URL$path" -o /dev/null || fail "healthcheck HTTPS falhou em $path"; done
  printf 'Inventário de rollback API/web host=%s domínio=%s\n' "$(hostname)" "$EXPECTED_URL"
  printf 'checkout_sha=%s rollback_sha=%s schema=%s serviços=api,web\n' "$CHECKOUT_SHA" "$ROLLBACK_SHA" "$DATABASE_REVISION"
  printf 'approval_fingerprint=%s\n' "$(fingerprint)"
  echo "impacto=api,web; sem migrations; breve interrupção da API pode afetar todas as rotas, inclusive o Monitor"
  echo "rollback=restaurar somente imagens API/web preservadas e checkout indicado, sem dependências"
  echo "nenhum comando mutável foi executado"
}

release() {
  local current_fp service id image tag ref
  verify_repository
  current_fp="$(fingerprint)"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "fingerprint mudou; nada foi alterado"
  for service in "${SERVICES[@]}"; do
    id="$(compose ps -q "$service")"
    image="$(docker inspect --format '{{.Image}}' "$id")"
    ref="$(docker inspect --format '{{.Config.Image}}' "$id")"
    tag="$PROJECT_NAME-app-rollback-$service-$ACTIVE_SHA"
    docker image tag "$image" "$tag"
    printf '%s\n' "$tag" > "$STATE_DIR/app-$service-rollback-image"
    printf '%s\n' "$ref" > "$STATE_DIR/app-$service-image-ref"
  done
  printf '%s\n' "$ACTIVE_SHA" > "$STATE_DIR/app-previous.sha"
  printf '%s\n' "$TARGET_SHA" > "$STATE_DIR/app-in-flight.sha"
  git switch --detach "$TARGET_SHA" >/dev/null
  COMPOSE_APP_VERSION="$TARGET_SHA"
  compose config --quiet || fail "Compose alvo inválido"
  compose build "${SERVICES[@]}"
  current_fp="$(COMPOSE_APP_VERSION="$ACTIVE_SHA" fingerprint)"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "runtime mudou durante build; containers preservados"
  [[ "$(COMPOSE_APP_VERSION="$ACTIVE_SHA" database_revision)" == "$EXPECTED_DATABASE_REVISION" ]] \
    || fail "revisão do banco mudou; release abortado"
  compose up -d --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"
  runtime_snapshot
  compose exec -T nginx nginx -t || fail "configuração nginx Markina inválida"
  compose exec -T nginx nginx -s reload || fail "reload nginx Markina falhou"
  for path in /healthz /api/health /; do
    curl -fsS --retry 5 --retry-delay 2 --retry-max-time 40 --max-time 5 "$EXPECTED_URL$path" -o /dev/null \
      || fail "smoke HTTPS falhou em $path"
  done
  printf '%s\n' "$TARGET_SHA" > "$STATE_DIR/app-last-healthy.sha"
  rm -f "$STATE_DIR/app-in-flight.sha"
  printf '%s %s release-app-services %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ACTIVE_SHA" "$TARGET_SHA" >> "$STATE_DIR/app-history.log"
  echo "release saudável: $TARGET_SHA; serviços=api,web; migrations=nenhuma"
}

rollback() {
  local current_fp service old_tag old_ref id image image_ref current_tag
  verify_repository
  current_fp="$(fingerprint)"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "inventário de rollback mudou; nada foi alterado"
  for service in "${SERVICES[@]}"; do
    old_tag="$(cat "$STATE_DIR/app-$service-rollback-image")"
    old_ref="$(cat "$STATE_DIR/app-$service-image-ref")"
    id="$(compose ps -q "$service")"
    image="$(docker inspect --format '{{.Image}}' "$id")"
    image_ref="$(docker inspect --format '{{.Config.Image}}' "$id")"
    current_tag="$PROJECT_NAME-app-rollback-$service-$CHECKOUT_SHA"
    docker image tag "$image" "$current_tag"
    printf '%s\n' "$current_tag" > "$STATE_DIR/app-$service-rollback-image"
    printf '%s\n' "$image_ref" > "$STATE_DIR/app-$service-image-ref"
    docker image tag "$old_tag" "$old_ref"
  done
  printf '%s\n' "$CHECKOUT_SHA" > "$STATE_DIR/app-rollback-in-flight.sha"
  git switch --detach "$ROLLBACK_SHA" >/dev/null
  COMPOSE_APP_VERSION="$ROLLBACK_SHA"
  compose up -d --no-build --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"
  runtime_snapshot
  compose exec -T nginx nginx -t || fail "configuração nginx Markina inválida"
  compose exec -T nginx nginx -s reload || fail "reload nginx Markina falhou"
  for path in /healthz /api/health /; do
    curl -fsS --retry 5 --retry-delay 2 --retry-max-time 40 --max-time 5 "$EXPECTED_URL$path" -o /dev/null \
      || fail "smoke HTTPS de rollback falhou em $path"
  done
  printf '%s\n' "$ROLLBACK_SHA" > "$STATE_DIR/app-last-healthy.sha"
  printf '%s\n' "$CHECKOUT_SHA" > "$STATE_DIR/app-previous.sha"
  rm -f "$STATE_DIR/app-in-flight.sha" "$STATE_DIR/app-rollback-in-flight.sha"
  printf '%s %s rollback-app-services %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$CHECKOUT_SHA" "$ROLLBACK_SHA" >> "$STATE_DIR/app-history.log"
  echo "rollback saudável: $ROLLBACK_SHA; serviços=api,web; migrations=nenhuma"
}

main() {
  parse_arguments "$@"
  [[ "$EXPECTED_URL" == "$PUBLIC_URL" ]] || fail "domínio diverge do alvo"
  if [[ "$MODE" == release || "$MODE" == rollback ]]; then acquire_app_deploy_lock; fi
  case "$MODE" in
    inventory) inventory ;;
    release) release ;;
    rollback-inventory) rollback_inventory ;;
    rollback) rollback ;;
  esac
}

if [[ "${BASH_SOURCE[0]:-$0}" == "$0" ]]; then main "$@"; fi
