#!/usr/bin/env bash
# Read-only export of the exact active API/web image proved by production preflight.
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly EXPECTED_HOST="clearbudget-vnic"
readonly APP_COMPOSE_BRIDGE="/usr/local/sbin/markina-gallery-app-compose-bridge"
EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:-}"
MODE=""
TARGET_SHA=""
EXPECTED_IMAGE_ID=""
SERVICE="api"

fail() { echo "production-app-base-image: $*" >&2; exit 1; }

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode) MODE="${2:-}"; shift 2 ;;
      --sha) TARGET_SHA="${2:-}"; shift 2 ;;
      --service) SERVICE="${2:-}"; shift 2 ;;
      --expected-image-id) EXPECTED_IMAGE_ID="${2:-}"; shift 2 ;;
      *) fail "argumento não permitido: $1" ;;
    esac
  done
  [[ "$SERVICE" == api || "$SERVICE" == web ]] || fail "serviço inválido"
  [[ "$MODE" == "export" ]] || fail "modo deve ser export"
  [[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA alvo inválido"
  [[ "$EXPECTED_IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "ID-base inválido"
  [[ -n "$EXPECTED_REPOSITORY" ]] || fail "repositório esperado ausente"
}

export_api_base_image() {
  local origin remote_sha checkout_sha container_ids container_id project service image_id platform
  [[ "$(hostname)" == "$EXPECTED_HOST" ]] || fail "host diverge do alvo"
  [[ "$(pwd -P)" == "$PROJECT_ROOT" && "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] \
    || fail "checkout Markina ausente"
  [[ -z "$(git status --porcelain)" ]] || fail "checkout contém alterações locais"
  origin="$(git remote get-url origin)"
  case "$origin" in
    "https://github.com/$EXPECTED_REPOSITORY"|"https://github.com/$EXPECTED_REPOSITORY.git"|"git@github.com:$EXPECTED_REPOSITORY.git") ;;
    *) fail "origin Git diverge do repositório esperado" ;;
  esac
  checkout_sha="$(git rev-parse HEAD)"
  [[ "$checkout_sha" =~ ^[0-9a-f]{40}$ ]] || fail "checkout SHA inválido"
  git merge-base --is-ancestor "$checkout_sha" "$TARGET_SHA" \
    || fail "checkout não é ancestral do alvo"
  remote_sha="$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')"
  [[ "$remote_sha" == "$TARGET_SHA" ]] || fail "SHA alvo não é HEAD atual de origin/main"

  [[ "$(git rev-parse origin/main)" == "$TARGET_SHA" \
    && "$(git hash-object -- "$APP_COMPOSE_BRIDGE")" == "$(git rev-parse "$TARGET_SHA:scripts/production_app_compose_bridge.py")" ]] \
    || fail "ponte root-only diverge da main revisada"
  container_ids="$(sudo -n "$APP_COMPOSE_BRIDGE" --mode inventory --sha "$TARGET_SHA" compose -- ps -q "$SERVICE")" \
    || fail "seleção comprovada de API indisponível"
  [[ -n "$container_ids" && "$(wc -l <<< "$container_ids" | tr -d ' ')" == 1 ]] \
    || fail "container API ausente ou duplicado"
  container_id="$container_ids"
  project="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$container_id")" \
    || fail "projeto API indisponível"
  service="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$container_id")" \
    || fail "serviço API indisponível"
  image_id="$(docker inspect --format '{{.Image}}' "$container_id")" || fail "imagem API indisponível"
  local expected_project
  expected_project="$(sudo -n "$APP_COMPOSE_BRIDGE" --mode inventory --sha "$TARGET_SHA" service-project -- "$SERVICE")" \
    || fail "projeto API comprovado indisponível"
  [[ -n "$expected_project" && "$project" == "$expected_project" && "$service" == "$SERVICE" && "$image_id" == "$EXPECTED_IMAGE_ID" ]] \
    || fail "imagem API mudou desde o inventário"
  platform="$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$image_id")" \
    || fail "arquitetura da imagem API indisponível"
  [[ "$platform" == linux/arm64 ]] || fail "imagem-base API não é linux/arm64"

  # The bridge proves the registered runtime privately. Output contains only
  # the compressed image archive; no env, container data or volume is exported.
  docker image save "$image_id" | gzip -1
}

main() {
  parse_arguments "$@"
  export_api_base_image
}

main "$@"
