#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly SCRIPT="$ROOT/scripts/deploy-prod-web.sh"
output="$(mktemp)"
command_log="$(mktemp)"
trap 'rm -f "$output" "$command_log"' EXIT

if bash "$SCRIPT" --mode deploy --sha 1111111111111111111111111111111111111111 >"$output" 2>&1; then
  echo "modo não permitido foi aceito" >&2
  exit 1
fi
grep -Fq -- "--mode deve ser inventory, release, rollback-inventory ou rollback" "$output"

if bash "$SCRIPT" --mode release --sha 1111111111111111111111111111111111111111 >"$output" 2>&1; then
  echo "release sem código de aprovação foi aceito" >&2
  exit 1
fi
grep -Fq -- "--approval-code deve ser o código de 64 caracteres" "$output"

if bash "$SCRIPT" --mode inventory --sha 1111111111111111111111111111111111111111 --env-file docker/.env.prod >"$output" 2>&1; then
  echo "argumento para substituir ambiente foi aceito" >&2
  exit 1
fi
grep -Fq -- "argumento não permitido: --env-file" "$output"

: > "$output"
MARKINA_DEPLOY_SCRIPT_PATH="$SCRIPT" MARKINA_COMMAND_LOG="$output" bash -c '
  source "$MARKINA_DEPLOY_SCRIPT_PATH"
  compose() { printf "%s\n" "$*" >> "$MARKINA_COMMAND_LOG"; }
  build_web_image
  recreate_web_only
'

grep -Fxq 'build web' "$output"
grep -Fxq 'up -d --no-deps --no-build web' "$output"
[[ "$(wc -l < "$output" | tr -d ' ')" == "2" ]]

: > "$output"
if MARKINA_DEPLOY_SCRIPT_PATH="$SCRIPT" MARKINA_COMMAND_LOG="$output" bash -c '
  source "$MARKINA_DEPLOY_SCRIPT_PATH"
  MODE=inventory
  TARGET_CONFIG_HASH=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  compose() {
    case "$*" in
      "ps -q web") printf "web-container\n" ;;
      "ps -q nginx") printf "nginx-container\n" ;;
      build*|up*) printf "mutation %s\n" "$*" >> "$MARKINA_COMMAND_LOG" ;;
    esac
  }
  docker() {
    case "$3" in
      *project.working_dir*) printf "/opt/markina-gallery/docker\n" ;;
      *project.config_files*) printf "/opt/markina-gallery/docker/docker-compose.yml,/var/lib/markina-gallery/deploy-state/branding.compose.yml,/opt/markina-gallery/docker/docker-compose.raw-development.yml,/opt/markina-gallery/docker/docker-compose.preview-adjustment.yml,/opt/markina-gallery/docker/docker-compose.system-monitor.yml,/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml\n" ;;
      *compose.project*) printf "markina-gallery\n" ;;
      *compose.service*) printf "web\n" ;;
      *config-hash*) printf "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n" ;;
      *State.Health*) printf "healthy\n" ;;
      *NetworkSettings.Ports*) printf "{}\n" ;;
    esac
  }
  if verify_runtime_web > "$MARKINA_COMMAND_LOG" 2>&1; then exit 9; fi
'; then
  echo "configuração divergente foi aceita" >&2
  exit 1
fi
grep -Fq 'configuração efetiva diverge' "$output"
if grep -Fq 'mutation ' "$output"; then
  echo "divergência permitiu mutação" >&2
  exit 1
fi

: > "$output"
if MARKINA_DEPLOY_SCRIPT_PATH="$SCRIPT" MARKINA_COMMAND_LOG="$output" bash -c '
  source "$MARKINA_DEPLOY_SCRIPT_PATH"
  ACTIVE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  TARGET_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
  git() {
    if [[ "$1 $2" == "diff --quiet" ]]; then return 1; fi
    if [[ "$1" == switch ]]; then printf "switch %s\n" "$*" >> "$MARKINA_COMMAND_LOG"; return 0; fi
    return 1
  }
  switch_to_target
' >"$command_log" 2>&1; then
  echo "release web-only aceitou intervalo com mudanças de API" >&2
  exit 1
fi
if grep -Fq 'switch ' "$command_log"; then
  echo "intervalo incompatível selecionou SHA antes de abortar" >&2
  exit 1
fi

: > "$output"
: > "$command_log"
if MARKINA_DEPLOY_SCRIPT_PATH="$SCRIPT" MARKINA_COMMAND_LOG="$command_log" bash -c '
  source "$MARKINA_DEPLOY_SCRIPT_PATH"
  MODE=release
  TARGET_SHA=1111111111111111111111111111111111111111
  APPROVAL_CODE=0000000000000000000000000000000000000000000000000000000000000000
  inventory() { :; }
  approval_fingerprint() { printf "%064d" 1; }
  write_sha() { echo write >> "$MARKINA_COMMAND_LOG"; }
  switch_to_target() { echo switch >> "$MARKINA_COMMAND_LOG"; }
  build_web_image() { echo build >> "$MARKINA_COMMAND_LOG"; }
  recreate_web_only() { echo recreate >> "$MARKINA_COMMAND_LOG"; }
  check_web_after_change() { :; }
  execute_release
' > "$output" 2>&1; then
  echo "aprovação divergente foi aceita" >&2
  exit 1
fi
grep -Fq 'inventário mudou ou código de aprovação' "$output"
[[ ! -s "$command_log" ]]

python3 "$ROOT/scripts/test_deploy_prod_web_policy.py"
echo "deploy-prod-web shell: ok"
