#!/usr/bin/env bash
# Read-only export of the exact API image observed by production preflight.
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly EXPECTED_HOST="clearbudget-vnic"
EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:-}"
MODE=""
TARGET_SHA=""
EXPECTED_IMAGE_ID=""

fail() { echo "production-app-base-image: $*" >&2; exit 1; }

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode) MODE="${2:-}"; shift 2 ;;
      --sha) TARGET_SHA="${2:-}"; shift 2 ;;
      --expected-image-id) EXPECTED_IMAGE_ID="${2:-}"; shift 2 ;;
      *) fail "argumento não permitido: $1" ;;
    esac
  done
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

  container_ids="$(docker ps --quiet --filter 'label=com.docker.compose.project=markina-gallery' \
    --filter 'label=com.docker.compose.service=api')" || fail "consulta de container API falhou"
  [[ -n "$container_ids" && "$(wc -l <<< "$container_ids" | tr -d ' ')" == 1 ]] \
    || fail "container API ausente ou duplicado"
  container_id="$container_ids"
  project="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$container_id")" \
    || fail "projeto API indisponível"
  service="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$container_id")" \
    || fail "serviço API indisponível"
  image_id="$(docker inspect --format '{{.Image}}' "$container_id")" || fail "imagem API indisponível"
  [[ "$project" == markina-gallery && "$service" == api && "$image_id" == "$EXPECTED_IMAGE_ID" ]] \
    || fail "imagem API mudou desde o inventário"
  platform="$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$image_id")" \
    || fail "arquitetura da imagem API indisponível"
  [[ "$platform" == linux/arm64 ]] || fail "imagem-base API não é linux/arm64"

  # Output is a compressed Docker image archive only. No container data, env,
  # volume, filesystem mount, service mutation, or local host file is read/written.
  docker image save "$image_id" | gzip -1
}

main() {
  parse_arguments "$@"
  export_api_base_image
}

main "$@"
