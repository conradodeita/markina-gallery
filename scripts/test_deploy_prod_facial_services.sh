#!/usr/bin/env bash
# Fixtures sintéticas: configuração resolvida deve corresponder aos labels,
# sem emitir seus valores; diferenças reais e saúde ruim devem ser recusadas.
set -Eeuo pipefail
source "$(dirname "$0")/deploy-prod-facial-services.sh"

readonly WEB_HASH="$(printf 'a%.0s' {1..64})"
readonly API_HASH="$(printf 'b%.0s' {1..64})"
readonly WORKER_HASH="$(printf 'c%.0s' {1..64})"
readonly SYNTHETIC_CONFIG='{"services":{"api":{"environment":{"TOKEN":"synthetic-sensitive-$literal"}}}}'
BAD_SERVICE=""
UNHEALTHY_SERVICE=""
FACIAL_RUNTIME=true

compose() {
  case "$*" in
    'config --quiet') return 0 ;;
    'config --format json') printf '%s\n' "$SYNTHETIC_CONFIG" ;;
    'ps -q web') echo web ;;
    'ps -q api') echo api ;;
    'ps -q face-search-worker') echo face-search-worker ;;
    'ps -q nginx') echo nginx ;;
    *) echo 'chamada Compose inesperada na fixture' >&2; return 1 ;;
  esac
}

docker() {
  if [[ "$1" == compose ]]; then
    [[ "$*" == 'compose -p markina-gallery -f - --profile facial --profile preview-adjustment config --no-interpolate --hash web,api,face-search-worker' ]] || return 1
    local payload
    payload="$(cat)"
    [[ "$payload" == "$SYNTHETIC_CONFIG" ]] || return 1
    printf 'api %s\nface-search-worker %s\nweb %s\n' "$API_HASH" "$WORKER_HASH" "$WEB_HASH"
    return 0
  fi
  [[ "$1" == inspect && "$2" == --format ]] || return 1
  local format="$3" service="$4"
  case "$format" in
    '{{json .Config.Env}}') printf '["FACIAL_PROCESSING_ENABLED=%s"]\n' "$FACIAL_RUNTIME" ;;
    *com.docker.compose.project.config_files*) echo "$COMPOSE_FILE_LABEL" ;;
    *com.docker.compose.project.working_dir*) echo /opt/markina-gallery/docker ;;
    *com.docker.compose.project*) echo markina-gallery ;;
    *com.docker.compose.service*) echo "$service" ;;
    *com.docker.compose.config-hash*)
      if [[ "$service" == "$BAD_SERVICE" ]]; then printf 'd%.0s' {1..64}; echo
      elif [[ "$service" == web ]]; then echo "$WEB_HASH"
      elif [[ "$service" == api ]]; then echo "$API_HASH"
      else echo "$WORKER_HASH"; fi ;;
    *State.Health*)
      if [[ "$service" == "$UNHEALTHY_SERVICE" ]]; then echo unhealthy; else echo healthy; fi ;;
    '{{.Image}}') echo "sha256:synthetic-$service" ;;
    '{{json .NetworkSettings.Ports}}') echo '{"80/tcp":[{"HostIp":"127.0.0.1","HostPort":"8080"}]}' ;;
    *) echo 'inspect inesperado na fixture' >&2; return 1 ;;
  esac
}

output="$(mktemp)"
trap 'rm -f "$output"' EXIT
runtime_snapshot >"$output"
grep -q '^api|api|sha256:synthetic-api|' "$output"
grep -q '^face-search-worker|face-search-worker|' "$output"
grep -q '^compose_config=[0-9a-f]\{64\}$' "$output"
if grep -q 'synthetic-sensitive' "$output"; then echo 'configuração vazou na saída' >&2; exit 1; fi

for bad in api face-search-worker; do
  if ( BAD_SERVICE="$bad"; runtime_snapshot ) >"$output" 2>&1; then
    echo 'hash divergente não foi recusado' >&2; exit 1
  fi
  grep -q "configuração ativa de $bad diverge do Compose" "$output"
done
if ( UNHEALTHY_SERVICE=api; runtime_snapshot ) >"$output" 2>&1; then
  echo 'serviço sem saúde não foi recusado' >&2; exit 1
fi
grep -q 'container api não está saudável' "$output"
if ( FACIAL_RUNTIME=false; runtime_snapshot ) >"$output" 2>&1; then
  echo 'manutenção não pode ativar runtime desligado' >&2; exit 1
fi
grep -q 'manutenção exige runtime facial já ativo' "$output"
if grep -q 'synthetic-sensitive' "$output"; then echo 'configuração vazou no erro' >&2; exit 1; fi
echo 'production resolved inventory: ok'
