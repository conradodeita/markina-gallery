#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DEPLOY_SCRIPT="$SCRIPT_DIR/deploy-homolog.sh"

output="$(mktemp)"
err_probe="$(mktemp)"
trap 'rm -f "$output" "$err_probe"' EXIT

if MARKINA_EXPECTED_REPOSITORY="owner/repository" bash "$DEPLOY_SCRIPT" --sha 0000000000000000000000000000000000000000 >"$output" 2>&1; then
  echo "o deploy aceitou execução fora de /opt/markina-gallery" >&2
  exit 1
fi

grep -Fq 'o deploy só pode executar em /opt/markina-gallery' "$output"

set +e
MARKINA_DEPLOY_SCRIPT_PATH="$DEPLOY_SCRIPT" \
  MARKINA_EXPECTED_REPOSITORY="owner/repository" \
  ERR_PROBE="$err_probe" \
  bash -c '
  source "$MARKINA_DEPLOY_SCRIPT_PATH"
  trap '\''printf "%s\n" trapped > "$ERR_PROBE"'\'' ERR
  fail "falha sintética pós-switch"
' >"$output" 2>&1
fail_status=$?
set -e
[[ "$fail_status" -ne 0 ]]
grep -Fq 'deploy-homolog: falha sintética pós-switch' "$output"
grep -Fq 'trapped' "$err_probe"

python3 "$SCRIPT_DIR/test_deploy_homolog_policy.py"
echo "deploy-homolog shell: ok"
