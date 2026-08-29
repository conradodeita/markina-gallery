#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DEPLOY_SCRIPT="$SCRIPT_DIR/deploy-homolog.sh"

output="$(mktemp)"
trap 'rm -f "$output"' EXIT

if MARKINA_EXPECTED_REPOSITORY="owner/repository" bash "$DEPLOY_SCRIPT" --sha 0000000000000000000000000000000000000000 >"$output" 2>&1; then
  echo "o deploy aceitou execução fora de /opt/markina-gallery" >&2
  exit 1
fi

grep -Fq 'o deploy só pode executar em /opt/markina-gallery' "$output"
python3 "$SCRIPT_DIR/test_deploy_homolog_policy.py"
echo "deploy-homolog shell: ok"
