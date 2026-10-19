#!/usr/bin/env bash
# Inventário e release API/web isolados do fluxo de manutenção facial.
set -Eeuo pipefail
umask 077
export GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 PYTHONDONTWRITEBYTECODE=1

readonly RELEASE_STATE_BLOB="06f1d15937da53f55362a86780d013e4096f27bf"
readonly RELEASE_LOCK_BLOB="b95712afefc977e3aa8afe95a879c908103a6f79"
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
  acquire_production_deploy_lock "$STATE_DIR" app || fail "outro release ou tentativa pendente; lock indisponível"
}

verify_database_revision() {
  [[ "$1" == "$EXPECTED_DATABASE_REVISION" ]] || fail "revisão de banco diverge do inventário aprovado"
}

verify_readonly_target_ancestry() {
  local origin="$1" checkout_sha="$2" target_sha="$3" current_sha
  git cat-file -e "$target_sha^{commit}" 2>/dev/null || fail "objeto alvo ausente; preparação autorizada necessária"
  [[ "$(git rev-parse origin/main)" == "$target_sha" ]] || fail "main local desatualizada"
  git merge-base --is-ancestor "$checkout_sha" "$target_sha" || fail "SHA alvo não descende do checkout"
  current_sha="$(git ls-remote "$origin" refs/heads/main | awk 'NR == 1 {print $1}')"
  [[ "$current_sha" == "$target_sha" ]] || fail "HEAD de main mudou durante o inventário"
}

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
  output="$(compose exec -T -e PYTHONDONTWRITEBYTECODE=1 api python -B -m alembic current 2>/dev/null)" || fail "consulta de schema falhou"
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
  verify_readonly_target_ancestry "$origin" "$CHECKOUT_SHA" "$TARGET_SHA"
  APP_INTERRUPTED=false
  if [[ "$MODE" == rollback* ]]; then
    local pending
    for pending in app-in-flight.sha app-rollback-in-flight.sha; do
      if [[ -f "$STATE_DIR/$pending" ]]; then
        [[ "$(cat "$STATE_DIR/$pending")" == "$TARGET_SHA" ]] || fail "tentativa app pertence a outro SHA"
        APP_INTERRUPTED=true
      fi
    done
  fi
  if [[ "$MODE" == inventory || "$MODE" == release ]]; then
    release_assert_no_pending || fail "tentativa interrompida; investigar/recuperar"
  fi
  if [[ "$MODE" == "release" ]]; then
    git diff --quiet "$CHECKOUT_SHA" "$TARGET_SHA" -- docker/ backend/migrations/ \
      || fail "Docker/Compose ou migrations fora do escopo"
    # Verificador/manifesto do alvo por memória/pipe: sem arquivos temporários.
    GIT_DIR="$PROJECT_ROOT/.git" GIT_WORK_TREE="$PROJECT_ROOT" \
      python3 -c 'import sys; p=sys.argv.pop(1); code=sys.argv.pop(1); exec(compile(code,p,"exec"),{"__file__":p,"__name__":"__main__"})' \
      "$PROJECT_ROOT/scripts/check_prod_app_release_scope.py" "$(git show "$TARGET_SHA:scripts/check_prod_app_release_scope.py")" \
      --base "$CHECKOUT_SHA" --target "$TARGET_SHA" \
      --manifest <(git show "$TARGET_SHA:openspec/changes/add-production-app-release-workflow/runtime-gates.json") \
      || fail "escopo ou blobs API/web não aprovados"
  fi
  if [[ "$MODE" == "rollback-inventory" || "$MODE" == "rollback" ]]; then
    [[ -f "$STATE_DIR/app-previous.sha" ]] || fail "SHA anterior de API/web ausente"
    ROLLBACK_SHA="$(cat "$STATE_DIR/app-previous.sha")"
    [[ "$ROLLBACK_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA anterior inválido"
    git merge-base --is-ancestor "$ROLLBACK_SHA" "$CHECKOUT_SHA" \
      || fail "SHA anterior não é ancestral do runtime atual"
    APP_RESTORE_WEB="$(release_read_identity "$STATE_DIR/app-web-rollback.identity")" || fail "recibo web anterior ausente"
    APP_RESTORE_API_VERSION="$(cat "$STATE_DIR/app-api-rollback.version")"
    [[ "$APP_RESTORE_API_VERSION" =~ ^[0-9a-f]{40}$ ]] || fail "versão API anterior inválida"
    for service in "${SERVICES[@]}"; do
      [[ -s "$STATE_DIR/app-$service-rollback-image" && -s "$STATE_DIR/app-$service-image-ref" ]] \
        || fail "imagem anterior de $service não está preservada"
      local saved_id expected_id saved_ref
      saved_id="$(release_image_id "$(cat "$STATE_DIR/app-$service-rollback-image")")" || fail "imagem anterior ausente"
      expected_id="$(cat "$STATE_DIR/app-$service-rollback-id")"
      saved_ref="$(cat "$STATE_DIR/app-$service-image-ref")"
      [[ "$expected_id" =~ ^sha256:[0-9a-f]{64}$ && "$saved_id" == "$expected_id" ]] || fail "tag de recuperação diverge do ID"
      [[ "$saved_ref" == "$PROJECT_NAME-$service" || "$saved_ref" == "$PROJECT_NAME-$service:latest" ]] || fail "referência de imagem fora do projeto"
      if [[ "$service" == web ]]; then
        [[ "$(awk '{print $2}' <<< "$APP_RESTORE_WEB")" == "$saved_id" ]] || fail "recibo web anterior diverge"
      fi
    done
  fi
  ACTIVE_SHA="$CHECKOUT_SHA"
  api_id="$(compose ps -q api)"
  [[ -n "$api_id" && "$(wc -l <<<"$api_id" | tr -d ' ')" == 1 ]] || fail "API ativa ausente ou duplicada"
  api_version="$(docker inspect --format '{{json .Config.Env}}' "$api_id" \
    | python3 -c 'import json,sys; values=json.load(sys.stdin); print(next((v.split("=",1)[1] for v in values if v.startswith("APP_VERSION=")), ""))')"
  [[ "$api_version" =~ ^[0-9a-f]{40}$ ]] || fail "APP_VERSION inválido"
  if [[ "$APP_INTERRUPTED" == true ]]; then
    local actual_api expected_api
    actual_api="$(docker inspect --format '{{.Image}}' "$api_id")"
    expected_api="$(cat "$STATE_DIR/app-api-rollback-id")"
    if [[ "$actual_api" == "$expected_api" ]]; then
      [[ "$api_version" == "$APP_RESTORE_API_VERSION" ]] || fail "versão API anterior não corresponde ao recibo"
    else
      [[ "$actual_api" == "$(cat "$STATE_DIR/app-api-target-id")" && "$api_version" == "$TARGET_SHA" ]] || fail "API não pertence à tentativa aprovada"
    fi
  else
    git diff --quiet "$api_version" "$CHECKOUT_SHA" -- backend/ || fail "API diverge do checkout"
  fi
  # Web-only pode ter avançado o checkout mantendo o backend idêntico.
  local web_id web_image web_hash
  web_id="$(compose ps -q web)"
  [[ -n "$web_id" && "$web_id" != *$'\n'* ]] || fail "web ausente/duplicado"
  web_image="$(docker inspect --format '{{.Image}}' "$web_id")"
  web_hash="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.config-hash"}}' "$web_id")"
  if [[ "$APP_INTERRUPTED" == false ]]; then
    APP_WEB_IDENTITY="$(release_assert_web_identity "$web_image" "$web_hash")" || fail "identidade web não comprovada"
  fi
  if [[ "$MODE" == release ]]; then
    local current_image current_tag tag_id ref
    for service in "${SERVICES[@]}"; do
      ref="$(docker inspect --format '{{.Config.Image}}' "$(compose ps -q "$service")")"
      [[ "$ref" == "$PROJECT_NAME-$service" || "$ref" == "$PROJECT_NAME-$service:latest" ]] || fail "referência ativa inesperada"
      current_image="$(docker inspect --format '{{.Image}}' "$(compose ps -q "$service")")"
      [[ "$(release_image_id "$current_image")" == "$current_image" ]] || fail "imagem ativa não disponível"
      current_tag="$PROJECT_NAME-app-rollback-$service-${current_image#sha256:}"
      if tag_id="$(release_image_id "$current_tag")"; then [[ "$tag_id" == "$current_image" ]] || fail "tag anterior em conflito"; fi
    done
  fi
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
    if [[ "$APP_INTERRUPTED" == true && "$MODE" == rollback* ]]; then
      local previous_id target_id
      previous_id="$(cat "$STATE_DIR/app-$service-rollback-id")"
      target_id="$(cat "$STATE_DIR/app-$service-target-id" 2>/dev/null || true)"
      [[ "$image" == "$previous_id" || ( "$target_id" =~ ^sha256:[0-9a-f]{64}$ && "$image" == "$target_id" ) ]] || fail "imagem não pertence à tentativa interrompida"
    else
      [[ "$health" == healthy ]] || fail "container $service não está saudável"
    fi
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
  local snapshot recovery="" service
  if [[ "$MODE" == rollback* ]]; then
    for service in "${SERVICES[@]}"; do
      recovery+="$(cat "$STATE_DIR/app-$service-rollback-id")|$(cat "$STATE_DIR/app-$service-image-ref")|"
    done
  fi
  snapshot="$(runtime_snapshot)" || return 1
  printf '%s\n' "$fingerprint_mode" "$TARGET_SHA" "$ROLLBACK_SHA" "$ACTIVE_SHA" "$CHECKOUT_SHA" "$EXPECTED_URL" \
    "database_revision=$DATABASE_REVISION" "$COMPOSE_APP_VERSION" "${APP_WEB_IDENTITY:-}" "${APP_RESTORE_WEB:-}" "${APP_RESTORE_API_VERSION:-}" "$recovery" "$snapshot" \
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
  local current_fp service id image tag ref api_before expected_api expected_web
  verify_repository
  current_fp="$(fingerprint)"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "fingerprint mudou; nada foi alterado"
  printf '%s\n' "$TARGET_SHA" > "$STATE_DIR/app-in-flight.sha"
  release_write_file app-web-rollback.identity "$APP_WEB_IDENTITY" || fail "recibo anterior não salvo"
  release_write_file app-api-rollback.version "$COMPOSE_APP_VERSION" || fail "versão API anterior não salva"
  for service in "${SERVICES[@]}"; do
    id="$(compose ps -q "$service")"
    image="$(docker inspect --format '{{.Image}}' "$id")"
    ref="$(docker inspect --format '{{.Config.Image}}' "$id")"
    tag="$PROJECT_NAME-app-rollback-$service-${image#sha256:}"
    local existing
    if existing="$(release_image_id "$tag")"; then [[ "$existing" == "$image" ]] || fail "tag de recuperação já aponta a outro ID"; fi
    docker image tag "$image" "$tag"
    [[ "$(release_image_id "$tag")" == "$image" ]] || fail "preservação de imagem não confirmada"
    printf '%s\n' "$image" > "$STATE_DIR/app-$service-rollback-id"
    printf '%s\n' "$tag" > "$STATE_DIR/app-$service-rollback-image"
    printf '%s\n' "$ref" > "$STATE_DIR/app-$service-image-ref"
  done
  printf '%s\n' "$ACTIVE_SHA" > "$STATE_DIR/app-previous.sha"
  printf '%s\n' "$TARGET_SHA" > "$STATE_DIR/app-in-flight.sha"
  git switch --detach "$TARGET_SHA" >/dev/null
  api_before="$COMPOSE_APP_VERSION"
  COMPOSE_APP_VERSION="$TARGET_SHA"
  compose config --quiet || fail "Compose alvo inválido"
  compose build "${SERVICES[@]}"
  current_fp="$(COMPOSE_APP_VERSION="$api_before" fingerprint)"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "runtime mudou durante build; containers preservados"
  [[ "$(COMPOSE_APP_VERSION="$api_before" database_revision)" == "$EXPECTED_DATABASE_REVISION" ]] \
    || fail "revisão do banco mudou; release abortado"
  for service in "${SERVICES[@]}"; do
    [[ "$(release_image_id "$(cat "$STATE_DIR/app-$service-rollback-image")")" == "$(cat "$STATE_DIR/app-$service-rollback-id")" ]] || fail "backup mudou durante build"
  done
  expected_api="$(release_image_id "$PROJECT_NAME-api")" || fail "build API sem ID"
  expected_web="$(release_image_id "$PROJECT_NAME-web")" || fail "build web sem ID"
  release_write_file app-api-target-id "$expected_api" || fail "não registrou ID construído da API"
  release_write_file app-web-target-id "$expected_web" || fail "não registrou ID construído do web"
  compose up -d --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"
  runtime_snapshot
  [[ "$(docker inspect --format '{{.Image}}' "$(compose ps -q api)")" == "$expected_api" \
    && "$(docker inspect --format '{{.Image}}' "$(compose ps -q web)")" == "$expected_web" ]] || fail "runtime não usa IDs construídos"
  compose exec -T nginx nginx -t || fail "configuração nginx Markina inválida"
  compose exec -T nginx nginx -s reload || fail "reload nginx Markina falhou"
  for path in /healthz /api/health /; do
    curl -fsS --retry 5 --retry-delay 2 --retry-max-time 40 --max-time 5 "$EXPECTED_URL$path" -o /dev/null \
      || fail "smoke HTTPS falhou em $path"
  done
  local web_hash
  web_hash="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.config-hash"}}' "$(compose ps -q web)")"
  release_write_file web-current.identity "$TARGET_SHA $expected_web $web_hash $TARGET_SHA" || fail "identidade web não salva"
  # Histórico web-only anterior não é rollback válido depois de trocar a API.
  rm -f "$STATE_DIR/web-previous.identity" "$STATE_DIR/web-previous.services" "$STATE_DIR/web-previous.compose"
  printf '%s\n' "$TARGET_SHA" > "$STATE_DIR/app-last-healthy.sha"
  rm -f "$STATE_DIR/app-in-flight.sha"
  printf '%s %s release-app-services %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ACTIVE_SHA" "$TARGET_SHA" >> "$STATE_DIR/app-history.log"
  echo "release saudável: $TARGET_SHA; serviços=api,web; migrations=nenhuma"
}

rollback() {
  local current_fp service id image ref tag current_web current_api restore_web restore_api_version
  local -A restore_ids restore_refs next_ids next_refs next_tags
  verify_repository
  current_fp="$(fingerprint)"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "inventário de rollback mudou; nada foi alterado"
  restore_web="$APP_RESTORE_WEB" restore_api_version="$APP_RESTORE_API_VERSION"
  for service in "${SERVICES[@]}"; do
    restore_ids[$service]="$(cat "$STATE_DIR/app-$service-rollback-id")"
    restore_refs[$service]="$(cat "$STATE_DIR/app-$service-image-ref")"
  done
  # Não substituir recibos de recuperação durante a troca: retry usa os mesmos IDs.
  if [[ ! -f "$STATE_DIR/app-rollback-in-flight.sha" ]]; then
    current_web="$(release_read_identity "$STATE_DIR/web-current.identity")" || fail "identidade atual inválida"
    current_api="$COMPOSE_APP_VERSION"
    release_write_file app-rollback-next.identity "$current_web" || fail "não salvou recibo atual"
    release_write_file app-rollback-next.version "$current_api" || fail "não salvou versão atual"
    for service in "${SERVICES[@]}"; do
      id="$(compose ps -q "$service")"
      image="$(docker inspect --format '{{.Image}}' "$id")"
      ref="$(docker inspect --format '{{.Config.Image}}' "$id")"
      tag="$PROJECT_NAME-app-rollback-$service-${image#sha256:}"
      local existing
      if existing="$(release_image_id "$tag")"; then [[ "$existing" == "$image" ]] || fail "tag de preservação em conflito"; fi
      docker image tag "$image" "$tag"
      [[ "$(release_image_id "$tag")" == "$image" ]] || fail "preservação não confirmada"
      release_write_file "app-rollback-next-$service-id" "$image" || fail "não salvou ID atual"
      release_write_file "app-rollback-next-$service-ref" "$ref" || fail "não salvou referência atual"
      release_write_file "app-rollback-next-$service-tag" "$tag" || fail "não salvou tag atual"
    done
    release_write_file app-rollback-in-flight.sha "$TARGET_SHA" || fail "não registrou tentativa"
  fi
  current_web="$(release_read_identity "$STATE_DIR/app-rollback-next.identity")" || fail "recibo contingencial ausente"
  current_api="$(cat "$STATE_DIR/app-rollback-next.version")"
  for service in "${SERVICES[@]}"; do
    next_ids[$service]="$(cat "$STATE_DIR/app-rollback-next-$service-id")"
    next_refs[$service]="$(cat "$STATE_DIR/app-rollback-next-$service-ref")"
    next_tags[$service]="$(cat "$STATE_DIR/app-rollback-next-$service-tag")"
    [[ "$(release_image_id "${next_tags[$service]}")" == "${next_ids[$service]}" ]] || fail "imagem substituída não preservada"
    docker image tag "${restore_ids[$service]}" "${restore_refs[$service]}"
    [[ "$(release_image_id "${restore_refs[$service]}")" == "${restore_ids[$service]}" ]] || fail "tag restaurada incorreta"
  done
  git switch --detach "$ROLLBACK_SHA" >/dev/null
  COMPOSE_APP_VERSION="$restore_api_version"
  compose up -d --no-build --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"
  runtime_snapshot
  for service in "${SERVICES[@]}"; do
    id="$(compose ps -q "$service")"
    [[ "$(docker inspect --format '{{.Image}}' "$id")" == "${restore_ids[$service]}" ]] || fail "rollback restaurou ID incorreto"
    [[ "$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id")" == healthy ]] || fail "rollback não saudável"
  done
  compose exec -T nginx nginx -t || fail "configuração nginx Markina inválida"
  compose exec -T nginx nginx -s reload || fail "reload nginx Markina falhou"
  for path in /healthz /api/health /; do
    curl -fsS --retry 5 --retry-delay 2 --retry-max-time 40 --max-time 5 "$EXPECTED_URL$path" -o /dev/null || fail "smoke HTTPS de rollback falhou em $path"
  done
  release_write_file web-current.identity "$restore_web" || fail "recibo web restaurado não salvo"
  release_write_file app-web-rollback.identity "$current_web" || fail "não salvou web substituído"
  release_write_file app-api-rollback.version "$current_api" || fail "não salvou versão API substituída"
  for service in "${SERVICES[@]}"; do
    release_write_file "app-$service-rollback-id" "${next_ids[$service]}" || fail "não salvou ID substituído"
    release_write_file "app-$service-rollback-image" "${next_tags[$service]}" || fail "não salvou tag substituída"
    release_write_file "app-$service-image-ref" "${next_refs[$service]}" || fail "não salvou referência substituída"
  done
  rm -f "$STATE_DIR/web-previous.identity" "$STATE_DIR/web-previous.services" "$STATE_DIR/web-previous.compose"
  release_write_file app-last-healthy.sha "$ROLLBACK_SHA" || fail "não salvou versão saudável"
  release_write_file app-previous.sha "$CHECKOUT_SHA" || fail "não salvou checkout anterior"
  printf '%s %s rollback-app-services %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$CHECKOUT_SHA" "$ROLLBACK_SHA" >> "$STATE_DIR/app-history.log"
  rm -f "$STATE_DIR/app-in-flight.sha" "$STATE_DIR/app-rollback-in-flight.sha"
  echo "rollback saudável: $ROLLBACK_SHA; serviços=api,web; migrations=nenhuma"
}

release_load_support() {
  # O operador fornece o SHA da main aprovada, inclusive em recuperação.
  # Usa objetos já locais; nenhum fetch, arquivo temporário ou source do checkout antigo.
  local origin remote helper path expected
  [[ "$(pwd -P)" == "$PROJECT_ROOT" && "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] || return 1
  origin="$(git remote get-url origin)" || return 1
  case "$origin" in
    "https://github.com/$EXPECTED_REPOSITORY"|"https://github.com/$EXPECTED_REPOSITORY.git"|"git@github.com:$EXPECTED_REPOSITORY.git") ;;
    *) echo 'origin diverge' >&2; return 1 ;;
  esac
  [[ "$TARGET_SHA" == "$(git rev-parse origin/main)" ]] || { echo 'SHA não é a main local aprovada; preparação necessária' >&2; return 1; }
  if [[ "$MODE" != recover* && "$MODE" != rollback* ]]; then
    remote="$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')" || return 1
    [[ "$remote" == "$TARGET_SHA" ]] || { echo 'HEAD remoto de main mudou' >&2; return 1; }
  fi
  for path in scripts/deploy-prod-lock.sh scripts/deploy-prod-state.sh; do
    if [[ "$path" == scripts/deploy-prod-lock.sh ]]; then expected="$RELEASE_LOCK_BLOB"; else expected="$RELEASE_STATE_BLOB"; fi
    [[ "$(git rev-parse "$TARGET_SHA:$path")" == "$expected" ]] || { echo 'suporte diverge do blob revisado' >&2; return 1; }
    helper="$(git show "$TARGET_SHA:$path")" || return 1
    source <(printf '%s\n' "$helper") || return 1
  done
}

main() {
  parse_arguments "$@"
  [[ "$EXPECTED_URL" == "$PUBLIC_URL" ]] || fail "domínio diverge do alvo"
  release_load_support || fail "suporte não verificável; preparação autorizada necessária"
  if [[ "$MODE" == release || "$MODE" == rollback ]]; then acquire_app_deploy_lock; fi
  case "$MODE" in
    inventory) inventory ;;
    release) release ;;
    rollback-inventory) rollback_inventory ;;
    rollback) rollback ;;
  esac
}

if [[ "${BASH_SOURCE[0]:-$0}" == "$0" ]]; then main "$@"; fi
