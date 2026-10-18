#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
for file in scripts/deploy-prod-web.sh scripts/deploy-prod-lock.sh scripts/deploy-prod-state.sh; do bash -n "$file"; done
# Parse inválido deve abortar antes de carregar suporte ou tocar o host.
if bash scripts/deploy-prod-web.sh --mode invalid --sha 1111111111111111111111111111111111111111 >/dev/null 2>&1; then
  echo 'modo inválido aceito' >&2; exit 1
fi
python3 scripts/test_deploy_prod_web_policy.py
python3 scripts/test_prod_release_state.py
printf 'deploy-prod-web shell: ok\n'
