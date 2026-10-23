#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/deploy-prod-infinitepay-retirement.sh"

calls=()
inventory() { calls+=(inventory); }
release() { calls+=(release); }

main --mode release --sha "$(printf 'a%.0s' {1..40})" \
  --approval-fingerprint "$(printf 'b%.0s' {1..64})"
[[ "${calls[*]}" == "release" ]] || { echo "modo release não chamou release()" >&2; exit 1; }

calls=()
main --mode inventory --sha "$(printf 'c%.0s' {1..40})"
[[ "${calls[*]}" == "inventory" ]] || { echo "modo inventory não chamou inventory()" >&2; exit 1; }

if ( main --mode unexpected --sha "$(printf 'd%.0s' {1..40})" ) >/dev/null 2>&1; then
  echo "modo desconhecido foi aceito" >&2
  exit 1
fi

echo "retirement deployment dispatch: ok"
