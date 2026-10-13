#!/usr/bin/env bash
set -Eeuo pipefail
export OWNER_RESET_HOST_SCRIPT="$(cd "$(dirname "$0")" && pwd -P)/reset-homolog-owner.sh"
output="$(mktemp)"
temp_root="$(mktemp -d)"
trap 'rm -f -- "$output"; rm -rf -- "$temp_root"' EXIT

if bash -c 'source "$OWNER_RESET_HOST_SCRIPT"; classify_service unknown-writer' >"$output" 2>&1; then
  echo "writer desconhecido aceito" >&2; exit 1
fi
grep -Fq 'serviço Markina não classificado' "$output"

if bash -c '
  source "$OWNER_RESET_HOST_SCRIPT"
  WRITER_IDS=(abcdef123456)
  docker() {
    if [[ "$1" == inspect && "$*" == *com.docker.compose.project* ]]; then echo other-project; return 0; fi
    if [[ "$1" == inspect ]]; then echo api; return 0; fi
    echo UNEXPECTED-MUTATION
  }
  stop_writers
' >"$output" 2>&1; then echo "writer vizinho aceito" >&2; exit 1; fi
grep -Fq 'writer fora da lista Markina' "$output"
if grep -Fq UNEXPECTED-MUTATION "$output"; then exit 1; fi

if bash -c '
  source "$OWNER_RESET_HOST_SCRIPT"
  WRITER_IDS=(abcdef123456)
  docker() {
    if [[ "$1" == inspect && "$*" == *com.docker.compose.project* ]]; then echo markina-gallery; return 0; fi
    if [[ "$1" == inspect && "$*" == *com.docker.compose.service* ]]; then echo api; return 0; fi
    if [[ "$1" == inspect ]]; then echo true; return 0; fi
    if [[ "$1" == stop ]]; then return 0; fi
    echo UNEXPECTED-MUTATION
  }
  stop_writers
  echo UNEXPECTED-RESET
' >"$output" 2>&1; then echo "writer ativo aceito" >&2; exit 1; fi
grep -Fq 'writer ainda ativo' "$output"
if grep -Eq 'UNEXPECTED-(RESET|MUTATION)' "$output"; then exit 1; fi

if bash -c '
  source "$OWNER_RESET_HOST_SCRIPT"
  WRITER_IDS=(abcdef123456)
  docker() {
    if [[ "$1" == inspect && "$*" == *com.docker.compose.project* ]]; then echo markina-gallery; return 0; fi
    if [[ "$1" == inspect && "$*" == *com.docker.compose.service* ]]; then echo api; return 0; fi
    if [[ "$1" == inspect ]]; then echo false; return 0; fi
    if [[ "$1" == stop ]]; then return 0; fi
    if [[ "$1" == ps ]]; then echo "abcdef654321 raw-development-worker"; return 0; fi
    echo UNEXPECTED-MUTATION
  }
  stop_writers
  echo UNEXPECTED-RESET
' >"$output" 2>&1; then echo "writer novo aceito" >&2; exit 1; fi
grep -Fq 'writer ativo fora da pausa conferida' "$output"
if grep -Eq 'UNEXPECTED-(RESET|MUTATION)' "$output"; then exit 1; fi

if bash -c '
  source "$OWNER_RESET_HOST_SCRIPT"
  run_payload() { echo attempted-reset; return 1; }
  compose() { echo UNEXPECTED-QUEUE-CLEAR; }
  restore_writers() { echo UNEXPECTED-RESUME; }
  complete_reset
' >"$output" 2>&1; then echo "falha de reset aceita" >&2; exit 1; fi
grep -Fq 'writers mantidos pausados' "$output"
if grep -Fq UNEXPECTED "$output"; then exit 1; fi

bash -c '
  source "$OWNER_RESET_HOST_SCRIPT"
  root="$0"
  mkdir -p "$root"
  for index in $(seq 1 164); do printf x >"$root/file-$index.dump"; done
  printf brand >"$root/brand.png"
  [[ "$(dump_manifest "$root")" == "164 164" ]]
  purge_approved_dumps "$root" 164 164
  [[ "$(dump_manifest "$root")" == "0 0" && -f "$root/brand.png" ]]
' "$temp_root/approved" >"$output" 2>&1
grep -Fq '164 arquivos, 164 bytes' "$output"

if bash -c '
  source "$OWNER_RESET_HOST_SCRIPT"
  root="$0"
  mkdir -p "$root"
  printf x >"$root/file.dump"
  purge_approved_dumps "$root" 164 164
' "$temp_root/drift" >"$output" 2>&1; then echo "manifesto divergente aceito" >&2; exit 1; fi
grep -Fq 'manifesto dos dumps divergiu' "$output"
[[ -f "$temp_root/drift/file.dump" ]]

if bash -c '
  source "$OWNER_RESET_HOST_SCRIPT"
  root="$0"
  mkdir -p "$root"
  printf protected >"$root/outside.bin"
  ln -s outside.bin "$root/link.dump"
  purge_approved_dumps "$root" 1 9
' "$temp_root/symlink" >"$output" 2>&1; then echo "symlink aceito como dump" >&2; exit 1; fi
grep -Fq 'item .dump não regular' "$output"
[[ -f "$temp_root/symlink/outside.bin" && -L "$temp_root/symlink/link.dump" ]]

bash -c '
  source "$OWNER_RESET_HOST_SCRIPT"
  run_payload() { echo "database-and-media-verified"; }
  purge_approved_dumps() { echo "approved-dumps-removed"; }
  compose() { [[ "$*" == "exec -T redis redis-cli FLUSHDB" ]] || exit 1; }
  restore_writers() { echo "original-writers-restored"; }
  complete_reset
' >"$output" 2>&1
grep -Fxq database-and-media-verified "$output"
grep -Fxq approved-dumps-removed "$output"
grep -Fxq original-writers-restored "$output"

if bash -c '
  source "$OWNER_RESET_HOST_SCRIPT"
  docker() { echo UNEXPECTED-MUTATION; }
  main --mode execute --owner-email owner@example.test --expected-sha invalid --confirmation RESET_HOMOLOG_TO_OWNER_WITHOUT_BACKUP
' >"$output" 2>&1; then echo "SHA inválido aceito" >&2; exit 1; fi
grep -Fq 'identidade ou SHA ausente' "$output"
if grep -Fq UNEXPECTED-MUTATION "$output"; then exit 1; fi
echo "owner-reset shell: ok"
