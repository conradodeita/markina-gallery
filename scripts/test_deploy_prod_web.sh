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

# Bootstrap a partir de git show também deve executar a mesma validação.
if bash -s -- --mode deploy --sha 1111111111111111111111111111111111111111 < "$SCRIPT" > "$output" 2>&1; then
  echo "entrada por stdin não validou os argumentos" >&2
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
  verify_runtime_web > "$MARKINA_COMMAND_LOG" 2>&1
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

# A identidade do nginx também faz parte do inventário aprovado.
for ports in '{"80/tcp":[{"HostIp":"127.0.0.1","HostPort":"8080"}]}' '{"80/tcp":[{"HostIp":"0.0.0.0","HostPort":"8080"}]}'; do
  status=0
  MARKINA_TEST_PORTS="$ports" MARKINA_DEPLOY_SCRIPT_PATH="$SCRIPT" bash -c '
    source "$MARKINA_DEPLOY_SCRIPT_PATH"
    MODE=inventory
    TARGET_CONFIG_HASH=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    compose() {
      case "$*" in
        "ps -q web") echo web-container ;;
        "ps -q nginx") echo nginx-container ;;
        *) exit 92 ;;
      esac
    }
    docker() {
      case "$3" in
        *project.working_dir*) echo "$COMPOSE_WORKING_DIR" ;;
        *project.config_files*) echo "$COMPOSE_FILE_LABEL" ;;
        *compose.project*) echo "$PROJECT_NAME" ;;
        *compose.service*) echo web ;;
        *config-hash*) echo "$TARGET_CONFIG_HASH" ;;
        *State.Health*) echo healthy ;;
        *NetworkSettings.Ports*) echo "$MARKINA_TEST_PORTS" ;;
        "{{.Image}}") echo sha256:image ;;
        *) exit 93 ;;
      esac
    }
    verify_runtime_web
    previous="$(approval_fingerprint release 1111111111111111111111111111111111111111)"
    NGINX_PORTS=changed
    [[ "$previous" != "$(approval_fingerprint release 1111111111111111111111111111111111111111)" ]]
  ' > "$output" 2>&1 || status=$?
  if [[ "$ports" == *127.0.0.1* ]]; then
    [[ "$status" == 0 ]] || { cat "$output"; exit 1; }
  else
    [[ "$status" != 0 ]]
    grep -Fq 'portas do nginx divergem' "$output"
  fi
done

python3 "$ROOT/scripts/test_deploy_prod_web_policy.py"
echo "deploy-prod-web shell: ok"
