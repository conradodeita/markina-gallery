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
readonly ENV_FILE="docker/.env.homolog"
readonly STATE_DIR="/var/lib/markina-gallery/deploy-state"
readonly ARTIFACT_DIR="/tmp/markina-gallery-app-artifacts-${UID}"
readonly APP_COMPOSE_BRIDGE="/usr/local/sbin/markina-gallery-app-compose-bridge"
readonly APP_COMPOSE_BRIDGE_BLOB="cfef0a8d798842e2e5b237472cb00f8348229be8"
readonly PUBLIC_URL="https://markina.pickyourpic.com.br"
readonly SERVICES=(api web)
readonly EXPECTED_DATABASE_REVISION="20261113_0126"

MODE=""
TARGET_SHA=""
APPROVAL_FINGERPRINT=""
ARTIFACT_SHA256=""
ROLLBACK_SHA=""
EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:-}"
EXPECTED_URL="${MARKINA_PUBLIC_BASE_URL:-$PUBLIC_URL}"
CHECKOUT_SHA=""
ACTIVE_SHA=""
COMPOSE_APP_VERSION=""
BRIDGE_SOURCE_FINGERPRINT=""
DATABASE_REVISION=""
CANDIDATE_API_IMAGE_ID=""
CANDIDATE_WEB_IMAGE_ID=""
CANDIDATE_IMAGE_ARCHIVE=""
API_BASE_IMAGE_ID=""
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
      --artifact-sha256) ARTIFACT_SHA256="${2:-}"; shift 2 ;;
      --api-base-image-id) API_BASE_IMAGE_ID="${2:-}"; shift 2 ;;
      --candidate-api-id) CANDIDATE_API_IMAGE_ID="${2:-}"; shift 2 ;;
      --candidate-web-id) CANDIDATE_WEB_IMAGE_ID="${2:-}"; shift 2 ;;
      *) fail "argumento não permitido: $1" ;;
    esac
  done
  case "$MODE" in
    inventory|adoption-inventory|adopt|release|rollback-inventory|rollback|handoff-inventory|handoff-release|handoff-witness-inventory|handoff-witness-register|handoff-legacy-recovery-inventory|handoff-legacy-recover|handoff-recovery-inventory|handoff-recover) ;;
    *) fail "modo inválido" ;;
  esac
  [[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA alvo inválido"
  if [[ "$MODE" == "release" || "$MODE" == "rollback" || "$MODE" == "adopt" || "$MODE" == handoff-release || "$MODE" == handoff-witness-register || "$MODE" == handoff-*-recover || "$MODE" == handoff-recover ]]; then
    [[ "$APPROVAL_FINGERPRINT" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint obrigatório"
  fi
  if [[ "$MODE" == release || "$MODE" == handoff-release || "$MODE" == handoff-inventory ]]; then
    [[ "$ARTIFACT_SHA256" =~ ^[0-9a-f]{64}$ ]] || fail "digest do bundle obrigatório para release"
  elif [[ -n "$ARTIFACT_SHA256" ]]; then
    fail "digest do bundle fora dos modos de candidato"
  fi
  if [[ "$MODE" == handoff-inventory || "$MODE" == handoff-release ]]; then
    [[ "$API_BASE_IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ \
      && "$CANDIDATE_API_IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ \
      && "$CANDIDATE_WEB_IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ \
      && "$CANDIDATE_API_IMAGE_ID" != "$CANDIDATE_WEB_IMAGE_ID" ]] || fail "identidade do artifact obrigatória"
  elif [[ -n "$API_BASE_IMAGE_ID$CANDIDATE_API_IMAGE_ID$CANDIDATE_WEB_IMAGE_ID" ]]; then
    fail "IDs do artifact fora dos modos de candidato"
  fi
}

adopt_runtime_base() {
  [[ "$(hostname)" == "$EXPECTED_HOST" && "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "alvo de adoção diverge"
  [[ -z "$(git status --porcelain)" && "$(git rev-parse origin/main)" == "$TARGET_SHA" ]] || fail "main/checkout diverge"
  [[ "$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')" == "$TARGET_SHA" ]] || fail "main mudou"
  acquire_app_deploy_lock
  bridge_call adopt || fail "fingerprint de adoção divergiu; base anterior preservada"
  echo "base privada do runtime API/web adotada; serviços sem alterações"
}

bridge_call() {
  local operation="$1" bridge_mode="$MODE" bridge_approval="$APPROVAL_FINGERPRINT"
  shift
  # Ordinary reads keep their original closed vocabulary during a handoff.
  if [[ "$MODE" == handoff-* ]]; then bridge_mode=inventory; bridge_approval=""; fi
  [[ "$(git hash-object -- "$APP_COMPOSE_BRIDGE")" == "$APP_COMPOSE_BRIDGE_BLOB" ]] || fail "ponte root-only diverge do blob revisado"
  sudo -n "$APP_COMPOSE_BRIDGE" --mode "$bridge_mode" --sha "$TARGET_SHA" \
    --app-version "$COMPOSE_APP_VERSION" --approval-fingerprint "$bridge_approval" \
    --source-fingerprint "$BRIDGE_SOURCE_FINGERPRINT" \
    "$operation" -- "$@"
}

handoff_bridge() {
  local operation="$1" bridge_mode
  local -a arguments=()
  case "$operation" in
    handoff-inventory|handoff-witness-inventory) bridge_mode=inventory ;;
    handoff-prepare|handoff-apply|handoff-proxy|handoff-witness-register) bridge_mode=release ;;
    handoff-recovery-inventory|handoff-legacy-recovery-inventory) bridge_mode=rollback-inventory ;;
    handoff-recovery-prepare|handoff-recovery-apply|handoff-legacy-recovery-prepare|handoff-legacy-recovery-finalize|handoff-legacy-recovery-proxy) bridge_mode=rollback ;;
    *) fail "operação handoff não permitida" ;;
  esac
  [[ "$(git hash-object -- "$APP_COMPOSE_BRIDGE")" == "$APP_COMPOSE_BRIDGE_BLOB" ]] || fail "ponte root-only diverge do blob revisado"
  if [[ "$bridge_mode" == release || "$bridge_mode" == rollback ]]; then
    arguments+=(--approval-fingerprint "$APPROVAL_FINGERPRINT")
  fi
  if [[ "$operation" == handoff-inventory || "$operation" == handoff-prepare || "$operation" == handoff-apply ]]; then
    arguments+=(--artifact-sha256 "$ARTIFACT_SHA256" --api-base-image-id "$API_BASE_IMAGE_ID"
      --candidate-api-id "$CANDIDATE_API_IMAGE_ID" --candidate-web-id "$CANDIDATE_WEB_IMAGE_ID")
  fi
  sudo -n "$APP_COMPOSE_BRIDGE" --mode "$bridge_mode" --sha "$TARGET_SHA" "${arguments[@]}" "$operation"
}

compose() {
  bridge_call compose "$@"
}

resolved_hashes() {
  bridge_call hashes || fail "não foi possível calcular hashes Compose resolvidos"
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
  [[ -f "$ENV_FILE" && -d "$STATE_DIR" ]] || fail "ambiente ou estado ausente"
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
  if [[ "$MODE" == inventory || "$MODE" == release || "$MODE" == handoff-inventory || "$MODE" == handoff-release ]]; then
    release_assert_no_pending || fail "tentativa interrompida; investigar/recuperar"
  fi
  if [[ "$MODE" == "release" || "$MODE" == handoff-release || "$MODE" == handoff-inventory ]]; then
    git diff --quiet "$CHECKOUT_SHA" "$TARGET_SHA" -- backend/migrations/ \
      || fail "migrations fora do escopo"
    # Verificador/manifesto do alvo por memória/pipe: sem arquivos temporários.
    GIT_DIR="$PROJECT_ROOT/.git" GIT_WORK_TREE="$PROJECT_ROOT" \
      python3 -c 'import sys; p=sys.argv.pop(1); code=sys.argv.pop(1); exec(compile(code,p,"exec"),{"__file__":p,"__name__":"__main__"})' \
      "$PROJECT_ROOT/scripts/check_prod_app_release_scope.py" "$(git show "$TARGET_SHA:scripts/check_prod_app_release_scope.py")" \
      --base "$CHECKOUT_SHA" --target "$TARGET_SHA" \
      --manifest <(git show "$TARGET_SHA:openspec/changes/add-production-app-release-workflow/runtime-gates.json") \
      || fail "escopo ou blobs API/web não aprovados"
    [[ "$(git show "$TARGET_SHA:openspec/changes/add-production-app-release-workflow/runtime-gates.json" \
      | python3 -c 'import json,sys; print("yes" if json.load(sys.stdin).get("emergency_api") else "no")')" == no ]] \
      || fail "manifesto emergency_api não é suportado no release por artifact"
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
  docker inspect --format '{{json .Config.Env}}' "$api_id" \
    | python3 -c 'import json,sys; values=json.load(sys.stdin); sys.exit(0 if "FACIAL_PROCESSING_ENABLED=true" in values else 1)' \
    || fail "runtime ativo da API não tem FACIAL_PROCESSING_ENABLED=true"
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
    local approved_api_base
    approved_api_base="$(git show "$TARGET_SHA:openspec/changes/add-production-app-release-workflow/runtime-gates.json" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin).get("emergency_api",{}).get("baseline_sha",""))')"
    if [[ "$approved_api_base" == "$api_version" ]]; then
      git diff --quiet "$api_version" "$CHECKOUT_SHA" -- backend/app/ backend/migrations/ backend/Dockerfile \
        backend/requirements.txt backend/face-requirements.txt backend/gemma-requirements.txt \
        || fail "API diverge dos inputs ativos aprovados"
      local approved_api_image
      approved_api_image="$(git show "$TARGET_SHA:openspec/changes/add-production-app-release-workflow/runtime-gates.json" \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["emergency_api"]["baseline_image"])')"
      [[ "$(docker inspect --format '{{.Image}}' "$api_id")" == "$approved_api_image" ]] || fail "imagem API diverge da baseline"
    else
      git diff --quiet "$api_version" "$CHECKOUT_SHA" -- backend/ || fail "API diverge do checkout"
    fi
  fi
  # Web-only pode ter avançado o checkout mantendo o backend idêntico.
  local web_id web_image web_hash
  web_id="$(compose ps -q web)"
  [[ -n "$web_id" && "$web_id" != *$'\n'* ]] || fail "web ausente/duplicado"
  web_image="$(docker inspect --format '{{.Image}}' "$web_id")"
  web_hash="$(bridge_call service-hash web)" || fail "identidade semântica web indisponível"
  if [[ "$APP_INTERRUPTED" == false ]]; then
    APP_WEB_IDENTITY="$(bridge_call web-identity)" || fail "identidade web não comprovada"
    [[ "$APP_WEB_IDENTITY" == *" $web_image $web_hash "* ]] || fail "recibo web semântico diverge"
  fi
  if [[ "$MODE" == release || "$MODE" == handoff-release ]]; then
    local current_image current_tag tag_id ref
    for service in "${SERVICES[@]}"; do
      ref="$(docker inspect --format '{{.Config.Image}}' "$(compose ps -q "$service")")"
      [[ "$ref" == "$PROJECT_NAME-$service" || "$ref" == "$PROJECT_NAME-$service:latest" || "$ref" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "referência ativa inesperada"
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

require_facial_processing_enabled_in_config() {
  bridge_call assert-facial || fail "APP_ENV=production e FACIAL_PROCESSING_ENABLED=true devem permanecer ativos"
}

runtime_snapshot() {
  local hashes config_hash service id project actual_service hash health image expected
  compose config --quiet 2>/dev/null || fail "configuração Compose inválida"
  require_facial_processing_enabled_in_config
  hashes="$(resolved_hashes)"
  config_hash="$(printf '%s\n' "$hashes" | LC_ALL=C sort | sha256sum | awk '{print $1}')"
  for service in "${SERVICES[@]}"; do
    id="$(compose ps -q "$service")"
    [[ -n "$id" && "$(wc -l <<<"$id" | tr -d ' ')" == 1 ]] || fail "container $service ausente ou duplicado"
    project="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$id")"
    actual_service="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$id")"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id")"
    image="$(docker inspect --format '{{.Image}}' "$id")"
    hash="$(bridge_call service-hash "$service")" || fail "prova semântica do serviço falhou"
    [[ "$project" == "$(bridge_call service-project "$service")" && "$actual_service" == "$service" ]] \
      || fail "identidade do container $service diverge"
    expected="$(awk -v service="$service" '$1 == service {print $2}' <<<"$hashes")"
    expected="${expected#sha256:}"
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || fail "hash Compose esperado inválido"
    [[ "$hash" =~ ^[0-9a-f]{64}$ ]] || fail "hash Compose ativo inválido"
    if [[ "$hash" != "$expected" ]]; then
      if [[ "$APP_INTERRUPTED" == true && "$MODE" == rollback* ]]; then
        local saved_hash saved_target_hash saved_previous saved_target
        saved_hash="$(cat "$STATE_DIR/app-$service-rollback-hash" 2>/dev/null || true)"
        saved_target_hash="$(cat "$STATE_DIR/app-$service-target-hash" 2>/dev/null || true)"
        saved_previous="$(cat "$STATE_DIR/app-$service-rollback-id" 2>/dev/null || true)"
        saved_target="$(cat "$STATE_DIR/app-$service-target-id" 2>/dev/null || true)"
        [[ ( "$image" == "$saved_previous" && "$hash" == "$saved_hash" ) \
          || ( "$image" == "$saved_target" && "$hash" == "$saved_target_hash" ) ]] || fail "hash fora da tentativa aprovada"
      else
        fail "hash Compose de $service diverge"
      fi
    fi
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
  local source_fingerprint
  source_fingerprint="$(bridge_call sources-fingerprint)" || fail "fingerprint das fontes Compose indisponível"
  [[ "$source_fingerprint" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint das fontes Compose inválido"
  printf 'nginx_bind=%s\ncompose_config=%s\ncompose_sources=%s\n' "$ports" "$config_hash" "$source_fingerprint"
}

fingerprint() {
  local fingerprint_mode="$MODE"
  [[ "$MODE" == release ]] && fingerprint_mode=inventory
  [[ "$MODE" == rollback ]] && fingerprint_mode=rollback-inventory
  local snapshot="${1:-}" recovery="" service
  if [[ "$MODE" == rollback* ]]; then
    for service in "${SERVICES[@]}"; do
      recovery+="$(cat "$STATE_DIR/app-$service-rollback-id")|$(cat "$STATE_DIR/app-$service-image-ref")|"
    done
  fi
  [[ -n "$snapshot" ]] || snapshot="$(runtime_snapshot)" || return 1
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

adoption_inventory() {
  [[ "$(hostname)" == "$EXPECTED_HOST" && "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "alvo de adoção diverge"
  [[ -z "$(git status --porcelain)" ]] || fail "checkout contém alterações locais"
  [[ "$(git rev-parse origin/main)" == "$TARGET_SHA" ]] || fail "SHA de adoção não é main local"
  [[ "$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')" == "$TARGET_SHA" ]] || fail "main mudou"
  [[ "$(git hash-object -- "$APP_COMPOSE_BRIDGE")" == "$APP_COMPOSE_BRIDGE_BLOB" ]] || fail "ponte diverge"
  sudo -n "$APP_COMPOSE_BRIDGE" --mode inventory --sha "$TARGET_SHA" adoption-inventory
  echo "impacto=read-only; nenhum serviço ou arquivo persistente alterado"
}

rollback_inventory() {
  verify_repository
  runtime_snapshot
  if [[ -f "$STATE_DIR/app-nginx-maintenance.active" ]]; then
    curl -fsS --max-time 10 "$EXPECTED_URL/healthz" -o /dev/null || fail "nginx de manutenção indisponível"
    echo "maintenance=active; saúde API/web não presumida; recuperação vinculada aos IDs da tentativa"
  else
    for path in /healthz /api/health /; do curl -fsS --max-time 10 "$EXPECTED_URL$path" -o /dev/null || fail "healthcheck HTTPS falhou em $path"; done
  fi
  printf 'Inventário de rollback API/web host=%s domínio=%s\n' "$(hostname)" "$EXPECTED_URL"
  printf 'checkout_sha=%s rollback_sha=%s schema=%s serviços=api,web\n' "$CHECKOUT_SHA" "$ROLLBACK_SHA" "$DATABASE_REVISION"
  printf 'approval_fingerprint=%s\n' "$(fingerprint)"
  echo "impacto=api,web; sem migrations; breve interrupção da API pode afetar todas as rotas, inclusive o Monitor"
  echo "rollback=restaurar somente imagens API/web preservadas e checkout indicado, sem dependências"
  echo "nenhum comando mutável foi executado"
}

verify_candidate_artifact() {
  local expected_api_base="$1" bundle verify_output candidate_archive
  [[ -d "$ARTIFACT_DIR" && ! -L "$ARTIFACT_DIR" ]] || fail "diretório privado do artifact ausente/inválido"
  [[ "$(stat -c '%u' -- "$ARTIFACT_DIR")" == "$UID" && "$(stat -c '%a' -- "$ARTIFACT_DIR")" == 700 ]] \
    || fail "diretório privado do artifact não pertence ao usuário ou não está em modo 0700"
  bundle="$ARTIFACT_DIR/$TARGET_SHA.bundle"
  [[ -f "$bundle" && ! -L "$bundle" && "$(stat -c '%u' -- "$bundle")" == "$UID" \
    && "$(stat -c '%a' -- "$bundle")" == 600 ]] || fail "bundle ausente ou permissões inválidas"
  verify_output="$(candidate_artifact_tool verify --bundle "$bundle" \
    --target-sha "$TARGET_SHA" --bundle-sha256 "$ARTIFACT_SHA256" \
    --api-base-image-id "$expected_api_base" --extract-dir "$ARTIFACT_DIR")" \
    || fail "bundle não corresponde ao SHA, digest ou imagem API base inventariada"
  CANDIDATE_API_IMAGE_ID="$(sed -n 's/^api_image_id=//p' <<<"$verify_output")"
  CANDIDATE_WEB_IMAGE_ID="$(sed -n 's/^web_image_id=//p' <<<"$verify_output")"
  candidate_archive="$(sed -n 's/^image_archive=//p' <<<"$verify_output")"
  [[ "$CANDIDATE_API_IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ \
    && "$CANDIDATE_WEB_IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ \
    && "$CANDIDATE_API_IMAGE_ID" != "$CANDIDATE_WEB_IMAGE_ID" \
    && "$candidate_archive" == "$ARTIFACT_DIR"/.images-* \
    && -f "$candidate_archive" && ! -L "$candidate_archive" ]] \
    || fail "manifesto do bundle não contém imagens API/web válidas"
  CANDIDATE_IMAGE_ARCHIVE="$candidate_archive"
}

candidate_artifact_tool() {
  # Before the checkout change, use only the reviewed target's verifier.
  if [[ "$MODE" == handoff-release ]]; then
    python3 -c 'import sys; p=sys.argv.pop(1); code=sys.argv.pop(1); exec(compile(code,p,"exec"),{"__file__":p,"__name__":"__main__"})' \
      "$PROJECT_ROOT/scripts/production_app_artifact.py" "$(git show "$TARGET_SHA:scripts/production_app_artifact.py")" "$@"
  else
    python3 scripts/production_app_artifact.py "$@"
  fi
}

load_candidate_artifact() {
  local api_actual web_actual api_platform web_platform
  docker load --input "$CANDIDATE_IMAGE_ARCHIVE" >/dev/null || fail "não foi possível carregar o bundle validado"
  api_actual="$(release_image_id "$PROJECT_NAME-api")" || fail "imagem API do bundle ausente"
  web_actual="$(release_image_id "$PROJECT_NAME-web")" || fail "imagem web do bundle ausente"
  [[ "$api_actual" == "$CANDIDATE_API_IMAGE_ID" && "$web_actual" == "$CANDIDATE_WEB_IMAGE_ID" ]] \
    || fail "tags carregadas não correspondem aos IDs fixados no bundle"
  api_platform="$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$api_actual")" \
    || fail "arquitetura da imagem API não comprovada"
  web_platform="$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$web_actual")" \
    || fail "arquitetura da imagem web não comprovada"
  [[ "$api_platform" == linux/arm64 && "$web_platform" == linux/arm64 ]] \
    || fail "bundle não contém somente imagens linux/arm64"
  rm -f -- "$CANDIDATE_IMAGE_ARCHIVE"
  CANDIDATE_IMAGE_ARCHIVE=""
}

cleanup_candidate_artifact() {
  rm -f -- "$ARTIFACT_DIR/$TARGET_SHA.bundle"
  [[ -z "$CANDIDATE_IMAGE_ARCHIVE" ]] || rm -f -- "$CANDIDATE_IMAGE_ARCHIVE"
}

handoff_host_guard() {
  [[ "$(hostname)" == "$EXPECTED_HOST" && "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "alvo handoff diverge"
  [[ -d "$STATE_DIR" && -f "$ENV_FILE" && -z "$(git status --porcelain)" ]] || fail "checkout/estado inválido"
  [[ "$(git rev-parse origin/main)" == "$TARGET_SHA" \
    && "$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')" == "$TARGET_SHA" ]] || fail "main mudou"
}

handoff_https() {
  if [[ "$MODE" == handoff-legacy-recover ]]; then
    handoff_bridge handoff-legacy-recovery-proxy || fail "prova/reload nginx Markina falhou"
  else
    handoff_bridge handoff-proxy || fail "prova/reload nginx Markina falhou"
  fi
  local path
  for path in /healthz /api/health /; do
    curl -fsS --retry 5 --retry-delay 2 --retry-max-time 40 --max-time 5 "$EXPECTED_URL$path" -o /dev/null \
      || fail "smoke HTTPS falhou em $path"
  done
}

handoff_receipt_value() {
  local receipt="$1" key="$2" value
  value="$(sed -n "s/^$key=//p" <<<"$receipt")"
  [[ -n "$value" && "$value" != *$'\n'* ]] || fail "recibo handoff ausente/duplicado"
  printf '%s\n' "$value"
}

handoff_save_receipt() {
  local receipt="$1" checkout api_version web_version web_image web_hash
  checkout="$(handoff_receipt_value "$receipt" checkout_sha)"
  api_version="$(handoff_receipt_value "$receipt" api_version)"
  web_version="$(handoff_receipt_value "$receipt" web_version)"
  web_image="$(handoff_receipt_value "$receipt" web_image_id)"
  web_hash="$(handoff_receipt_value "$receipt" web_semantic_hash)"
  [[ "$checkout" =~ ^[0-9a-f]{40}$ && "$api_version" =~ ^[0-9a-f]{40}$ && "$web_version" =~ ^[0-9a-f]{40}$ \
    && "$web_image" =~ ^sha256:[0-9a-f]{64}$ && "$web_hash" =~ ^[0-9a-f]{64}$ ]] || fail "recibo handoff inválido"
  [[ "$(git rev-parse HEAD)" == "$checkout" ]] || fail "checkout diverge do recibo"
  release_write_file web-current.identity "$web_version $web_image $web_hash $checkout" || fail "recibo web não salvo"
  release_write_file app-last-healthy.sha "$checkout" || fail "recibo saudável não salvo"
  # Preserve old receipts as historical evidence; they cannot authorize an app rollback.
}

handoff_clear_markers() {
  local interrupted="$1" marker
  [[ "$interrupted" =~ ^[0-9a-f]{40}$ ]] || fail "SHA da tentativa inválido"
  for marker in app-in-flight.sha app-rollback-in-flight.sha; do
    if [[ -e "$STATE_DIR/$marker" ]]; then
      [[ ! -L "$STATE_DIR/$marker" && "$(cat "$STATE_DIR/$marker")" == "$interrupted" ]] || fail "marcador de outra tentativa"
    fi
  done
  for marker in app-in-flight.sha app-rollback-in-flight.sha; do
    [[ ! -e "$STATE_DIR/$marker" ]] || rm -- "$STATE_DIR/$marker"
  done
}

handoff_inventory() {
  verify_repository
  runtime_snapshot
  handoff_bridge handoff-inventory
  echo 'serviços=api,web; impacto=breve interrupção HTTP; migrations=nenhuma; workers=preservados'
}

handoff_release() {
  local declared_api="$CANDIDATE_API_IMAGE_ID" declared_web="$CANDIDATE_WEB_IMAGE_ID" service id image tag receipt
  trap cleanup_candidate_artifact EXIT
  verify_repository
  runtime_snapshot
  [[ "$(docker inspect --format '{{.Image}}' "$(compose ps -q api)")" == "$API_BASE_IMAGE_ID" ]] || fail "base API mudou"
  verify_candidate_artifact "$API_BASE_IMAGE_ID"
  [[ "$CANDIDATE_API_IMAGE_ID" == "$declared_api" && "$CANDIDATE_WEB_IMAGE_ID" == "$declared_web" ]] || fail "IDs divergem do inventário final"
  # Recompute the approved fingerprint and persist the private journal before effects.
  handoff_bridge handoff-prepare
  release_write_file app-web-rollback.identity "$APP_WEB_IDENTITY" || fail "recibo anterior não salvo"
  release_write_file app-api-rollback.version "$COMPOSE_APP_VERSION" || fail "versão anterior não salva"
  for service in "${SERVICES[@]}"; do
    id="$(compose ps -q "$service")"
    image="$(docker inspect --format '{{.Image}}' "$id")"
    tag="$PROJECT_NAME-app-rollback-$service-${image#sha256:}"
    if release_image_id "$tag" >/dev/null; then
      [[ "$(release_image_id "$tag")" == "$image" ]] || fail "tag de recuperação em conflito"
    fi
    docker image tag "$image" "$tag"
    [[ "$(release_image_id "$tag")" == "$image" ]] || fail "preservação de imagem não confirmada"
    release_write_file "app-$service-rollback-id" "$image" || fail "ID anterior não salvo"
    release_write_file "app-$service-rollback-image" "$tag" || fail "imagem anterior não salva"
  done
  release_write_file app-previous.sha "$CHECKOUT_SHA" || fail "checkout anterior não salvo"
  release_write_file app-api-target-id "$CANDIDATE_API_IMAGE_ID" || fail "ID candidato não salvo"
  release_write_file app-web-target-id "$CANDIDATE_WEB_IMAGE_ID" || fail "ID candidato não salvo"
  release_write_file app-in-flight.sha "$TARGET_SHA" || fail "marcador não salvo"
  git switch --detach "$TARGET_SHA" >/dev/null
  load_candidate_artifact
  receipt="$(handoff_bridge handoff-apply)" || fail "troca interrompida; inventário próprio de recuperação necessário"
  [[ "$(handoff_receipt_value "$receipt" handoff_status)" == healthy ]] || fail "troca sem recibo saudável"
  COMPOSE_APP_VERSION="$TARGET_SHA"
  runtime_snapshot
  handoff_https
  handoff_save_receipt "$receipt"
  handoff_clear_markers "$TARGET_SHA"
  printf '%s %s handoff-app-services %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$CHECKOUT_SHA" "$TARGET_SHA" >> "$STATE_DIR/app-history.log"
  echo "release saudável: $TARGET_SHA; serviços=api,web; anteriores preservados"
}

handoff_recover() {
  local preparation receipt checkout interrupted
  handoff_host_guard
  preparation="$(handoff_bridge handoff-recovery-prepare)" || fail "inventário de recuperação mudou"
  interrupted="$(handoff_receipt_value "$preparation" interrupted_sha)"
  [[ "$interrupted" =~ ^[0-9a-f]{40}$ ]] || fail "tentativa interrompida inválida"
  local marker
  for marker in app-in-flight.sha app-rollback-in-flight.sha; do
    [[ ! -e "$STATE_DIR/$marker" || ( ! -L "$STATE_DIR/$marker" && "$(cat "$STATE_DIR/$marker")" == "$interrupted" ) ]] || fail "marcador de outra tentativa"
  done
  release_write_file app-rollback-in-flight.sha "$interrupted" || fail "marcador de recuperação não salvo"
  receipt="$(handoff_bridge handoff-recovery-apply)" || fail "recuperação interrompida; novo inventário necessário"
  [[ "$(handoff_receipt_value "$receipt" handoff_status)" == healthy ]] || fail "recuperação sem recibo saudável"
  checkout="$(handoff_receipt_value "$receipt" checkout_sha)"
  [[ "$checkout" =~ ^[0-9a-f]{40}$ ]] || fail "checkout de recuperação inválido"
  git switch --detach "$checkout" >/dev/null
  COMPOSE_APP_VERSION="$(handoff_receipt_value "$receipt" api_version)"
  runtime_snapshot
  handoff_https
  handoff_save_receipt "$receipt"
  handoff_clear_markers "$interrupted"
  printf '%s %s recover-app-handoff %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interrupted" "$checkout" >> "$STATE_DIR/app-history.log"
  echo "recuperação saudável: $checkout; candidatos preservados"
}

handoff_legacy_recover() {
  local preparation checkout marker receipt
  handoff_host_guard
  preparation="$(handoff_bridge handoff-legacy-recovery-prepare)" || fail "inventário legado mudou"
  checkout="$(handoff_receipt_value "$preparation" checkout_sha)"
  [[ "$checkout" =~ ^[0-9a-f]{40}$ ]] || fail "checkout legado inválido"
  marker="$(cat "$STATE_DIR/app-in-flight.sha")"
  [[ "$marker" =~ ^[0-9a-f]{40}$ ]] || fail "marcador legado inválido"
  git switch --detach "$checkout" >/dev/null
  runtime_snapshot
  handoff_https
  # Root re-proves all originals and sources before clearing this exact marker.
  receipt="$(handoff_bridge handoff-legacy-recovery-finalize)" || fail "reconciliação não comprovada"
  [[ "$(handoff_receipt_value "$receipt" legacy_recovery_status)" == healthy ]] || fail "recibo legado inválido"
  release_write_file app-last-healthy.sha "$checkout" || fail "recibo saudável não salvo"
  printf '%s %s recover-legacy-handoff %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$marker" "$checkout" >> "$STATE_DIR/app-history.log"
  echo "tentativa legada reconciliada: $checkout; containers intactos"
}

release() {
  local current_fp source_fingerprint service id image tag ref api_before expected_api expected_web target_hashes approval_snapshot
  trap cleanup_candidate_artifact EXIT
  verify_repository
  approval_snapshot="$(runtime_snapshot)" || fail "runtime Compose não foi inventariado"
  current_fp="$(fingerprint "$approval_snapshot")"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "fingerprint mudou; nada foi alterado"
  source_fingerprint="$(sed -n 's/^compose_sources=//p' <<<"$approval_snapshot")"
  [[ "$source_fingerprint" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint das fontes Compose inválido"
  BRIDGE_SOURCE_FINGERPRINT="$source_fingerprint"
  printf '%s\n' "$TARGET_SHA" > "$STATE_DIR/app-in-flight.sha"
  release_write_file app-web-rollback.identity "$APP_WEB_IDENTITY" || fail "recibo anterior não salvo"
  release_write_file app-api-rollback.version "$COMPOSE_APP_VERSION" || fail "versão API anterior não salva"
  for service in "${SERVICES[@]}"; do
    id="$(compose ps -q "$service")"
    image="$(docker inspect --format '{{.Image}}' "$id")"
    ref="$PROJECT_NAME-$service"
    tag="$PROJECT_NAME-app-rollback-$service-${image#sha256:}"
    local existing
    if existing="$(release_image_id "$tag")"; then [[ "$existing" == "$image" ]] || fail "tag de recuperação já aponta a outro ID"; fi
    docker image tag "$image" "$tag"
    [[ "$(release_image_id "$tag")" == "$image" ]] || fail "preservação de imagem não confirmada"
    printf '%s\n' "$image" > "$STATE_DIR/app-$service-rollback-id"
    printf '%s\n' "$tag" > "$STATE_DIR/app-$service-rollback-image"
    printf '%s\n' "$ref" > "$STATE_DIR/app-$service-image-ref"
    bridge_call service-hash "$service" > "$STATE_DIR/app-$service-rollback-hash"
  done
  printf '%s\n' "$ACTIVE_SHA" > "$STATE_DIR/app-previous.sha"
  printf '%s\n' "$TARGET_SHA" > "$STATE_DIR/app-in-flight.sha"
  bridge_call snapshot || fail "snapshots Compose ativos não foram preservados"
  git switch --detach "$TARGET_SHA" >/dev/null
  api_before="$COMPOSE_APP_VERSION"
  COMPOSE_APP_VERSION="$TARGET_SHA"
  compose config --quiet || fail "Compose alvo inválido"
  require_facial_processing_enabled_in_config
  target_hashes="$(resolved_hashes)" || fail "hashes Compose alvo indisponíveis"
  for service in "${SERVICES[@]}"; do
    awk -v service="$service" '$1 == service {sub(/^sha256:/,"",$2); print $2}' <<<"$target_hashes" > "$STATE_DIR/app-$service-target-hash"
  done
  # Compare the original live configuration against its own checkout. The
  # reviewed API-only env_file changes the target's resolved Compose hash.
  git switch --detach "$CHECKOUT_SHA" >/dev/null
  current_fp="$(COMPOSE_APP_VERSION="$api_before" fingerprint)"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "runtime mudou durante build; containers preservados"
  [[ "$(COMPOSE_APP_VERSION="$api_before" database_revision)" == "$EXPECTED_DATABASE_REVISION" ]] \
    || fail "revisão do banco mudou; release abortado"
  git switch --detach "$TARGET_SHA" >/dev/null
  [[ "$(resolved_hashes)" == "$target_hashes" ]] || fail "configuração alvo mudou durante build"
  for service in "${SERVICES[@]}"; do
    [[ "$(release_image_id "$(cat "$STATE_DIR/app-$service-rollback-image")")" == "$(cat "$STATE_DIR/app-$service-rollback-id")" ]] || fail "backup mudou durante release"
  done
  verify_candidate_artifact "$(cat "$STATE_DIR/app-api-rollback-id")"
  load_candidate_artifact
  expected_api="$CANDIDATE_API_IMAGE_ID"
  expected_web="$CANDIDATE_WEB_IMAGE_ID"
  release_write_file app-api-target-id "$expected_api" || fail "não registrou ID construído da API"
  release_write_file app-web-target-id "$expected_web" || fail "não registrou ID construído do web"
  compose up -d --no-build --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"
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
  web_hash="$(bridge_call service-hash web)"
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
  local source_fingerprint approval_snapshot
  local -A restore_ids restore_refs next_ids next_refs next_tags
  verify_repository
  approval_snapshot="$(runtime_snapshot)" || fail "runtime Compose não foi inventariado para rollback"
  current_fp="$(fingerprint "$approval_snapshot")"
  [[ "$current_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "inventário de rollback mudou; nada foi alterado"
  source_fingerprint="$(sed -n 's/^compose_sources=//p' <<<"$approval_snapshot")"
  [[ "$source_fingerprint" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint das fontes Compose inválido"
  BRIDGE_SOURCE_FINGERPRINT="$source_fingerprint"
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
      ref="$PROJECT_NAME-$service"
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
  bridge_call snapshot || fail "snapshots Compose atuais não foram preservados para rollback"
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
  compose config --quiet || fail "Compose de rollback inválido"
  require_facial_processing_enabled_in_config
  compose up -d --no-build --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"
  runtime_snapshot
  for service in "${SERVICES[@]}"; do
    id="$(compose ps -q "$service")"
    [[ "$(docker inspect --format '{{.Image}}' "$id")" == "${restore_ids[$service]}" ]] || fail "rollback restaurou ID incorreto"
    [[ "$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id")" == healthy ]] || fail "rollback não saudável"
  done
  compose exec -T nginx nginx -t || fail "configuração nginx Markina inválida"
  compose exec -T nginx nginx -s reload || fail "reload nginx Markina falhou"
  if [[ -f "$STATE_DIR/app-nginx-maintenance.active" ]]; then emergency_maintenance finish || fail "reabertura rollback falhou"; fi
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

emergency_maintenance() {
  local code
  code="$(git show "$TARGET_SHA:scripts/prepare_emergency_api_image.py")" || return 1
  python3 -c 'import sys; p=sys.argv.pop(1); code=sys.argv.pop(1); exec(compile(code,p,"exec"),{"__file__":p,"__name__":"__main__"})' \
    "$PROJECT_ROOT/scripts/prepare_emergency_api_image.py" "$code" --sha "$TARGET_SHA" \
    --maintenance "$1" --receipt "$STATE_DIR/app-nginx-maintenance.conf"
}

python_security_preparation() {
  # Separate scope in the existing executor. Never fall through to api/web.
  local arg previous="" target="" policy origin
  for arg in "$@"; do
    [[ "$previous" != --sha ]] || target="$arg"
    previous="$arg"
  done
  [[ "$target" =~ ^[0-9a-f]{40}$ && -n "$EXPECTED_REPOSITORY" ]] || fail 'SHA/repositório obrigatório'
  [[ "$(pwd -P)" == "$PROJECT_ROOT" && "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] || fail 'checkout incorreto'
  origin="$(git remote get-url origin)"
  case "$origin" in "https://github.com/$EXPECTED_REPOSITORY"|"https://github.com/$EXPECTED_REPOSITORY.git"|"git@github.com:$EXPECTED_REPOSITORY.git") ;; *) fail 'origin diverge';; esac
  [[ "$target" == "$(git rev-parse origin/main)" && "$target" == "$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')" ]] || fail 'SHA não é main aprovada'
  policy="$(git show "$target:scripts/python_security_release.py")" || fail 'política Python ausente'
  python3 -c 'import sys; p=sys.argv.pop(1); code=sys.argv.pop(1); exec(compile(code,p,"exec"),{"__file__":p,"__name__":"__main__"})' \
    "$PROJECT_ROOT/scripts/python_security_release.py" "$policy" "$@"
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
  if [[ "${1:-}" == --scope && "${2:-}" == python-security ]]; then
    shift 2
    python_security_preparation "$@"
    return
  fi
  parse_arguments "$@"
  [[ "$EXPECTED_URL" == "$PUBLIC_URL" ]] || fail "domínio diverge do alvo"
  release_load_support || fail "suporte não verificável; preparação autorizada necessária"
  if [[ "$MODE" == release || "$MODE" == rollback || "$MODE" == handoff-release || "$MODE" == handoff-witness-register || "$MODE" == handoff-legacy-recover || "$MODE" == handoff-recover ]]; then acquire_app_deploy_lock; fi
  case "$MODE" in
    inventory) inventory ;;
    adoption-inventory) adoption_inventory ;;
    adopt) adopt_runtime_base ;;
    release) release ;;
    rollback-inventory) rollback_inventory ;;
    rollback) rollback ;;
    handoff-inventory) handoff_inventory ;;
    handoff-release) handoff_release ;;
    handoff-recover) handoff_recover ;;
    handoff-legacy-recover) handoff_legacy_recover ;;
    handoff-witness-inventory|handoff-witness-register|handoff-legacy-recovery-inventory|handoff-recovery-inventory)
      handoff_host_guard
      handoff_bridge "$MODE"
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]:-$0}" == "$0" ]]; then main "$@"; fi
