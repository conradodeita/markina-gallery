#!/usr/bin/env bash
# Release manual web-only. Suporte carregado do SHA aprovado, nunca do checkout legado.
set -Eeuo pipefail
umask 077
export GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 PYTHONDONTWRITEBYTECODE=1

readonly RELEASE_STATE_BLOB="9ce3c7b70f7b1b8e8381f6c778458ca39c72a100"
readonly RELEASE_LOCK_BLOB="b95712afefc977e3aa8afe95a879c908103a6f79"
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


MODE="" TARGET_SHA="" APPROVAL_CODE="" ACTIVE_SHA="" ACTIVE_IMAGE=""
EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:-}"
CHECKOUT_SHA="" WEB_CONTAINER="" WEB_CONFIG_HASH="" TARGET_CONFIG_HASH=""
WEB_STATUS="" WEB_IMAGE_ID="" CURRENT_RECORD="" RESTORE_RECORD="" NON_WEB=""
RECOVERY_IMAGE="" RECOVERY_SHA="" RECOVERY_CONFIG="" RECOVERY_CHECKOUT=""
API_VERSION="" RUNTIME_REF="" NON_WEB_BEFORE=""
COMPOSE_DIGEST=""

fail() { echo "deploy-prod-web: $*" >&2; exit 1; }

compose() {
  local files=(--env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE") file
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do files+=(-f "$file"); done
  APP_VERSION="$API_VERSION" docker compose "${files[@]}" --profile facial --profile preview-adjustment "$@" </dev/null
}

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    [[ $# -ge 2 ]] || fail 'argumento sem valor'
    case "$1" in
      --mode) MODE="$2";;
      --sha) TARGET_SHA="$2";;
      --approval-code) APPROVAL_CODE="$2";;
      --active-sha) ACTIVE_SHA="$2";;
      --active-image) ACTIVE_IMAGE="$2";;
      *) fail "argumento não permitido: $1";;
    esac
    shift 2
  done
  case "$MODE" in inventory|release|rollback-inventory|rollback|recover-inventory|recover|reconcile-inventory|reconcile) ;;
    *) fail 'modo não permitido';;
  esac
  [[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] || fail 'SHA alvo inválido'
  case "$MODE" in release|rollback|recover|reconcile)
    [[ "$APPROVAL_CODE" =~ ^[0-9a-f]{64}$ ]] || fail 'approval-code obrigatório';;
  esac
  case "$MODE" in reconcile*)
    [[ "$ACTIVE_SHA" =~ ^[0-9a-f]{40}$ && "$ACTIVE_IMAGE" =~ ^sha256:[0-9a-f]{64}$ ]] || fail 'adoção exige SHA/ID explícitos e evidência externa';;
    *) [[ -z "$ACTIVE_SHA$ACTIVE_IMAGE" ]] || fail 'identidade explícita só é aceita na adoção';;
  esac
}

verify_repository() {
  local file api_id origin
  [[ "$(pwd -P)" == "$PROJECT_ROOT" && "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] || fail 'checkout incorreto'
  [[ -d "$STATE_DIR" && ! -L "$STATE_DIR" && -f "$ENV_FILE" ]] || fail 'estado/ambiente ausente ou inseguro'
  for file in "$COMPOSE_FILE" "${COMPOSE_EXTRA_FILES[@]}"; do [[ -f "$file" ]] || fail "Compose ausente: $file"; done
  COMPOSE_DIGEST="$(sha256sum "$COMPOSE_FILE" "${COMPOSE_EXTRA_FILES[@]}")"
  [[ -n "$EXPECTED_REPOSITORY" ]] || fail 'repositório esperado obrigatório'
  origin="$(git remote get-url origin)"
  case "$origin" in "https://github.com/$EXPECTED_REPOSITORY"|"https://github.com/$EXPECTED_REPOSITORY.git"|"git@github.com:$EXPECTED_REPOSITORY.git") ;; *) fail 'origin diverge';; esac
  [[ "$TARGET_SHA" == "$(git rev-parse origin/main)" ]] || fail 'alvo não é main'
  if [[ "$MODE" != recover* && "$MODE" != rollback* ]]; then
    [[ "$TARGET_SHA" == "$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')" ]] || fail 'main mudou'
  fi
  git cat-file -e "$TARGET_SHA^{commit}" || fail 'alvo ausente; preparação necessária'
  git check-ignore -q "$ENV_FILE" || fail 'ambiente não ignorado'
  [[ -z "$(git status --porcelain)" ]] || fail 'checkout sujo'
  CHECKOUT_SHA="$(git rev-parse HEAD)"
  git merge-base --is-ancestor "$CHECKOUT_SHA" "$TARGET_SHA" || fail 'checkout não ancestral do alvo'
  api_id="$(compose ps -q api)"
  [[ -n "$api_id" && "$api_id" != *$'\n'* ]] || fail 'API ausente ou duplicada'
  API_VERSION="$(docker inspect --format '{{json .Config.Env}}' "$api_id" | python3 -c 'import json,sys; print(next((v.split("=",1)[1] for v in json.load(sys.stdin) if v.startswith("APP_VERSION=")), ""))')"
  [[ "$API_VERSION" =~ ^[0-9a-f]{40}$ ]] || fail 'API sem versão verificável'
  git diff --quiet "$API_VERSION" "$CHECKOUT_SHA" -- backend/ || fail 'backend ativo diverge do checkout'
  compose config --quiet || fail 'Compose inválido'
  TARGET_CONFIG_HASH="$(compose config --hash web | awk '$1 == "web" {print $2}')"
  TARGET_CONFIG_HASH="${TARGET_CONFIG_HASH#sha256:}"
  [[ "$TARGET_CONFIG_HASH" =~ ^[0-9a-f]{64}$ ]] || fail 'hash Compose inválido'
}

verify_runtime_web() {
  local label expected nginx ports
  WEB_CONTAINER="$(compose ps -a -q web)"
  if [[ -z "$WEB_CONTAINER" && "$MODE" == recover* ]]; then
    WEB_STATUS=missing WEB_IMAGE_ID=missing WEB_CONFIG_HASH="$TARGET_CONFIG_HASH" RUNTIME_REF="$PROJECT_NAME-web"
  else
    [[ -n "$WEB_CONTAINER" && "$WEB_CONTAINER" != *$'\n'* ]] || fail 'web ausente ou duplicado'
    for label in project service project.working_dir project.config_files config-hash; do
      case "$label" in
        project) expected="$PROJECT_NAME";; service) expected=web;; project.working_dir) expected="$COMPOSE_WORKING_DIR";;
        project.config_files) expected="$COMPOSE_FILE_LABEL";; config-hash) expected="$TARGET_CONFIG_HASH";;
      esac
      [[ "$(docker inspect --format "{{index .Config.Labels \"com.docker.compose.$label\"}}" "$WEB_CONTAINER")" == "$expected" ]] || fail "identidade/configuração web diverge: $label"
    done
    WEB_STATUS="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$WEB_CONTAINER")"
    WEB_IMAGE_ID="$(docker inspect --format '{{.Image}}' "$WEB_CONTAINER")"
    RUNTIME_REF="$(docker inspect --format '{{.Config.Image}}' "$WEB_CONTAINER")"
    [[ "$RUNTIME_REF" == "$PROJECT_NAME-web" || "$RUNTIME_REF" == "$PROJECT_NAME-web:latest" ]] || fail 'referência web inesperada'
    WEB_CONFIG_HASH="$TARGET_CONFIG_HASH"
    if [[ "$MODE" != recover* ]]; then [[ "$WEB_STATUS" == healthy ]] || fail 'web não saudável'; fi
  fi
  nginx="$(compose ps -q nginx)"
  [[ -n "$nginx" && "$nginx" != *$'\n'* ]] || fail 'nginx ausente/duplicado'
  ports="$(docker inspect --format '{{json .NetworkSettings.Ports}}' "$nginx")"
  [[ "$ports" == '{"80/tcp":[{"HostIp":"127.0.0.1","HostPort":"8080"}]}' ]] || fail 'bind nginx diverge'
}

verify_scope() {
  local from="$1" to="$2"
  git diff --quiet "$from" "$to" -- backend/ docker/ frontend/Dockerfile frontend/.dockerignore || fail 'intervalo altera API/Compose/build fora do escopo web'
}

prepare_inventory() {
  local sha image config checkout
  verify_repository
  verify_runtime_web
  NON_WEB="$(release_non_web_snapshot | LC_ALL=C sort)"
  [[ -n "$NON_WEB" ]] || fail 'snapshot não-web vazio'
  case "$MODE" in
    reconcile*)
      release_assert_no_pending || fail 'há tentativa pendente'
      [[ ! -e "$STATE_DIR/web-current.identity" ]] || fail 'adoção só aceita identidade ausente'
      [[ "$ACTIVE_IMAGE" == "$WEB_IMAGE_ID" ]] || fail 'ID explícito diverge do runtime'
      git merge-base --is-ancestor "$ACTIVE_SHA" "$TARGET_SHA" || fail 'origem não ancestral'
      verify_scope "$ACTIVE_SHA" "$CHECKOUT_SHA"
      CURRENT_RECORD="$ACTIVE_SHA $WEB_IMAGE_ID $WEB_CONFIG_HASH $CHECKOUT_SHA"
      release_check_image "$WEB_IMAGE_ID" || fail 'imagem corrente não preservável'
      ;;
    recover*)
      [[ ! -e "$STATE_DIR/app-in-flight.sha" && ! -e "$STATE_DIR/app-rollback-in-flight.sha" ]] || fail 'tentativa app pendente'
      RESTORE_RECORD="$(release_read_identity "$STATE_DIR/web-pending.identity")" || fail 'recuperação sem recibo'
      [[ -f "$STATE_DIR/web-pending.target" && "$(cat "$STATE_DIR/web-pending.target")" == "$TARGET_SHA" ]] || fail 'SHA do procedimento diverge da tentativa aprovada'
      [[ -f "$STATE_DIR/web-pending.services" && ! -L "$STATE_DIR/web-pending.services" ]] || fail 'snapshot de recuperação ausente'
      [[ "$NON_WEB" == "$(cat "$STATE_DIR/web-pending.services")" ]] || fail 'outros serviços mudaram; não recuperar automaticamente'
      [[ -f "$STATE_DIR/web-pending.compose" && "$COMPOSE_DIGEST" == "$(cat "$STATE_DIR/web-pending.compose")" ]] || fail 'Compose mudou desde a tentativa'
      CURRENT_RECORD="$(release_read_identity "$STATE_DIR/web-current.identity")" || fail 'identidade corrente inválida'
      ;;
    *)
      release_assert_no_pending || fail 'tentativa não concluída'
      CURRENT_RECORD="$(release_assert_web_identity "$WEB_IMAGE_ID" "$WEB_CONFIG_HASH")" || fail 'identidade web não comprovada'
      read -r sha image config checkout <<< "$CURRENT_RECORD"
      ACTIVE_SHA="$sha"
      verify_scope "$ACTIVE_SHA" "$CHECKOUT_SHA"
      if [[ "$MODE" == rollback* ]]; then
        RESTORE_RECORD="$(release_read_identity "$STATE_DIR/web-previous.identity")" || fail 'rollback sem identidade anterior'
        [[ -f "$STATE_DIR/web-previous.services" && "$NON_WEB" == "$(cat "$STATE_DIR/web-previous.services")" ]] || fail 'outros serviços divergiram do rollback'
        [[ -f "$STATE_DIR/web-previous.compose" && "$COMPOSE_DIGEST" == "$(cat "$STATE_DIR/web-previous.compose")" ]] || fail 'Compose divergiu do rollback'
      else
        verify_scope "$ACTIVE_SHA" "$TARGET_SHA"
        release_check_image "$WEB_IMAGE_ID" || fail 'imagem corrente não preservável'
      fi
      ;;
  esac
  if [[ -n "$RESTORE_RECORD" ]]; then
    read -r RECOVERY_SHA RECOVERY_IMAGE RECOVERY_CONFIG RECOVERY_CHECKOUT <<< "$RESTORE_RECORD"
    [[ "$RECOVERY_CONFIG" == "$WEB_CONFIG_HASH" ]] || fail 'configuração de recuperação diverge'
    git cat-file -e "$RECOVERY_CHECKOUT^{commit}" || fail 'checkout de recuperação ausente'
    git merge-base --is-ancestor "$RECOVERY_CHECKOUT" "$TARGET_SHA" || fail 'recuperação fora da história aprovada'
    verify_scope "$RECOVERY_SHA" "$CHECKOUT_SHA"
    verify_scope "$RECOVERY_CHECKOUT" "$CHECKOUT_SHA"
    release_check_image "$RECOVERY_IMAGE" true || fail 'imagem de recuperação indisponível/divergente'
  fi
}

approval_fingerprint() {
  local mode="${MODE%-inventory}"
  [[ "$mode" == inventory ]] && mode=release
  printf '%s\n' "$mode" "$TARGET_SHA" "$CHECKOUT_SHA" "$API_VERSION" "$CURRENT_RECORD" "$RESTORE_RECORD" \
    "$WEB_CONTAINER" "$WEB_IMAGE_ID" "$WEB_STATUS" "$WEB_CONFIG_HASH" "$COMPOSE_DIGEST" "$NON_WEB" "$PUBLIC_URL" | sha256sum | awk '{print $1}'
}

inventory() {
  prepare_inventory
  printf 'project=%s target_sha=%s checkout_sha=%s\n' "$PROJECT_NAME" "$TARGET_SHA" "$CHECKOUT_SHA"
  printf 'web_image=%s health=%s identity=%s\n' "$WEB_IMAGE_ID" "$WEB_STATUS" "$CURRENT_RECORD"
  printf 'restore_identity=%s\nnon_web_snapshot_sha256=%s\n' "$RESTORE_RECORD" "$(printf '%s' "$NON_WEB" | sha256sum | awk '{print $1}')"
  printf 'compose_files_sha256:\n%s\n' "$COMPOSE_DIGEST"
  printf 'approval_code=%s\n' "$(approval_fingerprint)"
  echo 'escopo=web; possível breve interrupção; inventário é snapshot sem escrita'
}

verify_approval() {
  prepare_inventory
  [[ "$APPROVAL_CODE" == "$(approval_fingerprint)" ]] || fail 'inventário mudou ou código de aprovação diverge'
}

check_web_after_change() {
  local expected_image="$1" attempt status container code
  container="$(compose ps -q web)"
  [[ -n "$container" && "$container" != *$'\n'* ]] || fail 'web ausente/duplicado após operação'
  [[ "$(docker inspect --format '{{.Image}}' "$container")" == "$expected_image" ]] || fail 'ID executado diverge da imagem aprovada'
  [[ "$(docker inspect --format '{{index .Config.Labels "com.docker.compose.config-hash"}}' "$container")" == "$WEB_CONFIG_HASH" ]] || fail 'hash web mudou'
  for attempt in $(seq 1 30); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$status" == healthy ]] && break
    sleep 2
  done
  [[ "$status" == healthy ]] || fail 'web não ficou saudável'
  for path in /healthz /api/health / /admin/payments; do
    curl --fail --silent --show-error --max-time 10 --retry 5 --retry-delay 2 "$PUBLIC_URL$path" >/dev/null || fail "HTTPS falhou: $path"
  done
  code="$(curl --silent --show-error --max-time 10 --output /dev/null --write-out '%{http_code}' "$PUBLIC_URL/admin/statistics")"
  [[ "$code" == 404 ]] || fail 'Estatísticas voltou ou resposta inesperada'
  [[ "$(release_non_web_snapshot | LC_ALL=C sort)" == "$NON_WEB_BEFORE" ]] || fail 'estado não-web mudou'
}

build_web_image() { compose build web; }
recreate_web_only() { compose up -d --no-deps --no-build --force-recreate web; }

begin_attempt() {
  local previous="$1"
  release_preserve_image "$WEB_IMAGE_ID" || fail 'não foi possível preservar ID atual'
  release_write_file web-pending.services "$NON_WEB" || fail 'não salvou snapshot'
  release_write_file web-pending.compose "$COMPOSE_DIGEST" || fail 'não salvou configuração'
  release_write_file web-pending.target "$TARGET_SHA" || fail 'não salvou SHA do procedimento'
  release_write_file web-pending.identity "$previous" || fail 'não salvou recibo de recuperação'
}

finish_attempt() {
  local record="$1" event="$2"
  release_write_file web-current.identity "$record" || fail 'não salvou identidade saudável'
  release_write_file web-last-healthy.sha "${record%% *}" || fail 'não salvou marcador histórico'
  printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$event" "$record" >> "$STATE_DIR/web-history.log"
  rm -f "$STATE_DIR/web-in-flight.sha" "$STATE_DIR/web-pending.identity" "$STATE_DIR/web-pending.services" "$STATE_DIR/web-pending.target" "$STATE_DIR/web-pending.compose"
}

execute_release() {
  local previous built_image old_container old_image old_non_web old_compose
  verify_approval
  NON_WEB_BEFORE="$NON_WEB"
  old_container="$WEB_CONTAINER" old_image="$WEB_IMAGE_ID" old_non_web="$NON_WEB"
  old_compose="$COMPOSE_DIGEST"
  previous="${CURRENT_RECORD% *} $CHECKOUT_SHA"
  begin_attempt "$previous"
  git switch --detach "$TARGET_SHA" >/dev/null || fail 'checkout falhou; executar recuperação'
  build_web_image || fail 'build falhou; runtime anterior preservado, recuperação necessária'
  built_image="$(release_image_id "$PROJECT_NAME-web")" || fail 'build sem ID verificável'
  verify_repository
  verify_runtime_web
  [[ "$COMPOSE_DIGEST" == "$old_compose" ]] || fail 'arquivos Compose mudaram durante build'
  [[ "$(compose ps -a -q web)" == "$old_container" \
    && "$(docker inspect --format '{{.Image}}' "$old_container")" == "$old_image" \
    && "$(release_non_web_snapshot | LC_ALL=C sort)" == "$old_non_web" ]] || fail 'runtime mudou durante build; não recriar'
  [[ "$TARGET_SHA" == "$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')" ]] || fail 'main mudou durante build'
  release_check_image "$old_image" true || fail 'backup perdido durante build'
  release_write_file web-in-flight.sha "$TARGET_SHA" || fail 'não registrou tentativa'
  recreate_web_only || fail 'recriação falhou; recuperação necessária'
  check_web_after_change "$built_image"
  release_write_file web-previous.identity "$previous" || fail 'não salvou identidade anterior'
  release_write_file web-previous.services "$NON_WEB_BEFORE" || fail 'não salvou serviços anteriores'
  release_write_file web-previous.compose "$old_compose" || fail 'não salvou configuração anterior'
  finish_attempt "$TARGET_SHA $built_image $WEB_CONFIG_HASH $TARGET_SHA" release-web
  echo "release web saudável: $TARGET_SHA"
}

execute_restore() {
  local previous="$CURRENT_RECORD" event=rollback-web
  verify_approval
  previous="${CURRENT_RECORD% *} $CHECKOUT_SHA"
  NON_WEB_BEFORE="$NON_WEB"
  if [[ "$MODE" == rollback ]]; then begin_attempt "$previous"; else event=recover-web; fi
  # ID e tag já foram conferidos no inventário, antes de qualquer checkout.
  docker image tag "$RECOVERY_IMAGE" "$PROJECT_NAME-web" || fail 'restauração da referência falhou'
  [[ "$(release_image_id "$PROJECT_NAME-web")" == "$RECOVERY_IMAGE" ]] || fail 'referência restaurada incorreta'
  git switch --detach "$RECOVERY_CHECKOUT" >/dev/null || fail 'checkout de recuperação falhou'
  # Build falho pode ter deixado o container anterior intacto: não o recriar nesse caso.
  if [[ "$WEB_IMAGE_ID" != "$RECOVERY_IMAGE" || "$WEB_STATUS" != healthy ]]; then
    recreate_web_only || fail 'recuperação falhou; recibo pendente preservado'
  fi
  check_web_after_change "$RECOVERY_IMAGE"
  if [[ "$MODE" == rollback ]]; then
    release_write_file web-previous.identity "$previous" || fail 'não salvou versão substituída'
    release_write_file web-previous.services "$NON_WEB_BEFORE" || fail 'não salvou serviços'
    release_write_file web-previous.compose "$COMPOSE_DIGEST" || fail 'não salvou configuração'
  fi
  finish_attempt "$RESTORE_RECORD" "$event"
}

execute_reconcile() {
  verify_approval
  release_preserve_image "$WEB_IMAGE_ID" || fail 'preservação da imagem falhou'
  release_write_file web-current.identity "$CURRENT_RECORD" || fail 'adoção falhou'
  printf '%s reconcile-web %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$CURRENT_RECORD" >> "$STATE_DIR/web-history.log"
  echo 'adoção auditável concluída; marcadores históricos não foram copiados'
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
  release_load_support || fail 'suporte/target não verificável; preparação autorizada necessária'
  case "$MODE" in
    release|rollback|recover|reconcile)
      acquire_production_deploy_lock "$STATE_DIR" web || fail 'lock compartilhado indisponível'
      case "$MODE" in release) execute_release;; rollback|recover) execute_restore;; reconcile) execute_reconcile;; esac
      ;;
    *) inventory;;
  esac
}
if [[ "${BASH_SOURCE[0]-$0}" == "$0" ]]; then main "$@"; fi
