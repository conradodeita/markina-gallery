#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly SCRIPT="$ROOT/scripts/deploy-prod-app.sh"
output="$(mktemp)"
log="$(mktemp)"
trap 'rm -f "$output" "$log"' EXIT

lock_dir="$(mktemp -d)"
trap 'rm -f "$output" "$log" "$lock_dir/production-release.lock" "$lock_dir/web-in-flight.sha" "$lock_dir/app-in-flight.sha" "$lock_dir/state/valid.sha" "$lock_dir/state/invalid.sha"; rmdir "$lock_dir/state" 2>/dev/null || true; rmdir "$lock_dir" 2>/dev/null || true' EXIT
MARKINA_DEPLOY_LOCK_LIB="$ROOT/scripts/deploy-prod-lock.sh" MARKINA_LOCK_TEST_DIR="$lock_dir" bash -c '
  source "$MARKINA_DEPLOY_LOCK_LIB"
  command() { [[ "${1:-}" == -v && "${2:-}" == flock ]]; }
  flock() { [[ "${MARKINA_TEST_LOCK_BUSY:-0}" == 0 ]]; }
  acquire_production_deploy_lock "$MARKINA_LOCK_TEST_DIR" app
  [[ -f "$MARKINA_LOCK_TEST_DIR/production-release.lock" ]]
  if MARKINA_TEST_LOCK_BUSY=1 acquire_production_deploy_lock "$MARKINA_LOCK_TEST_DIR" web 2>/dev/null; then exit 10; fi
  : > "$MARKINA_LOCK_TEST_DIR/web-in-flight.sha"
  if acquire_production_deploy_lock "$MARKINA_LOCK_TEST_DIR" app 2>/dev/null; then exit 11; fi
  rm -f "$MARKINA_LOCK_TEST_DIR/web-in-flight.sha"
  : > "$MARKINA_LOCK_TEST_DIR/app-in-flight.sha"
  if acquire_production_deploy_lock "$MARKINA_LOCK_TEST_DIR" web 2>/dev/null; then exit 12; fi
'

MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  TARGET_SHA=1111111111111111111111111111111111111111
  git() {
    case "$1 $2" in
      "cat-file -e") return "${MARKINA_SHA_PRESENT:-0}" ;;
      "merge-base --is-ancestor") return "${MARKINA_SHA_ON_MAIN:-0}" ;;
      "diff --name-only") printf "%s\n" "${MARKINA_CHANGED_PATHS:-frontend/app/page.tsx}" ;;
      "status --porcelain") printf "%s" "${MARKINA_TEST_DIRTY:-}" ;;
      *) return 1 ;;
    esac
  }
  validate_target_history
  validate_checkout_clean
  MARKINA_TEST_DIRTY=" M frontend/app/page.tsx"
  if validate_checkout_clean 2>/dev/null; then exit 23; fi
  MARKINA_TEST_DIRTY=""
  ACTIVE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  validate_release_diff_paths
  MARKINA_CHANGED_PATHS=backend/migrations/20261018_0001_add_column.py
  if validate_release_diff_paths 2>/dev/null; then exit 20; fi
  MARKINA_CHANGED_PATHS=docker/docker-compose.yml
  if validate_release_diff_paths 2>/dev/null; then exit 21; fi
  MARKINA_SHA_ON_MAIN=1
  if validate_target_history 2>/dev/null; then exit 22; fi
  MARKINA_SHA_PRESENT=1
  MARKINA_SHA_ON_MAIN=0
  if validate_target_history 2>/dev/null; then exit 24; fi
'

mkdir "$lock_dir/state"
printf '%s\n' aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa > "$lock_dir/state/valid.sha"
printf '%s\n' invalid > "$lock_dir/state/invalid.sha"
MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_TEST_STATE_DIR="$lock_dir/state" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  [[ "$(read_state_sha "$MARKINA_TEST_STATE_DIR/valid.sha")" == aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa ]]
  if read_state_sha "$MARKINA_TEST_STATE_DIR/missing.sha" 2>/dev/null; then exit 25; fi
  if read_state_sha "$MARKINA_TEST_STATE_DIR/invalid.sha" 2>/dev/null; then exit 26; fi
'

MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  API_IMAGE_ID=api-current; WEB_IMAGE_ID=web-current
  docker() {
    if [[ "$1 $2" == "info --format" ]]; then printf /var/lib/docker; return 0; fi
    if [[ "$1 $2" == "image inspect" && "$5" == api-current ]]; then printf 1024; return 0; fi
    if [[ "$1 $2" == "image inspect" && "$5" == web-current ]]; then printf 1024; return 0; fi
    return 1
  }
  df() { printf "Filesystem 1024-blocks Used Available Capacity Mounted on\nmock 100 50 %s 50%% /var/lib/docker\n" "$MARKINA_DF_FREE_KB"; }
  MARKINA_DF_FREE_KB=2
  validate_build_space
  MARKINA_DF_FREE_KB=1
  if validate_build_space 2>/dev/null; then exit 29; fi
'

MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  MODE=release
  date() { printf 2026-10-18T12:00:00Z; }
  record="$(failure_record 7 cccccccccccccccccccccccccccccccccccccccc api)"
  [[ "$record" == "2026-10-18T12:00:00Z mode=release target=cccccccccccccccccccccccccccccccccccccccc failed_service=api exit=7" ]]
'

if bash "$SCRIPT" --mode deploy --sha 1111111111111111111111111111111111111111 >"$output" 2>&1; then
  echo "modo não permitido foi aceito" >&2; exit 1
fi
grep -Fq -- "--mode deve ser inventory, release, rollback-inventory, rollback, baseline-inventory ou baseline" "$output"

if bash "$SCRIPT" --mode release --sha 1111111111111111111111111111111111111111 >"$output" 2>&1; then
  echo "release sem código de aprovação foi aceito" >&2; exit 1
fi
grep -Fq -- "--approval-code deve conter o código de 64 caracteres" "$output"

if bash "$SCRIPT" --mode baseline --sha 1111111111111111111111111111111111111111 >"$output" 2>&1; then
  echo "registro inicial sem aprovação foi aceito" >&2; exit 1
fi
grep -Fq -- "--approval-code deve conter o código de 64 caracteres" "$output"

: > "$log"
MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_DEPLOY_TEST_LOG="$log" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  record() { printf "%s\n" "$*" >> "$MARKINA_DEPLOY_TEST_LOG"; }
  MODE=baseline; APPROVAL_CODE=wrong
  inventory() { record inventory; }
  approval_fingerprint() { printf expected; }
  write_state() { record "state:$1"; }
  if verify_approval 2>/dev/null; then exit 28; fi
' >"$output" 2>&1
if grep -Fq 'state:' "$log"; then
  echo "aprovação divergente gravou baseline" >&2; exit 1
fi

: > "$log"
MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_DEPLOY_TEST_LOG="$log" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  record() { printf "%s\n" "$*" >> "$MARKINA_DEPLOY_TEST_LOG"; }
  verify_approval() { API_IMAGE_ID=api-active; WEB_IMAGE_ID=web-active; record approval; }
  date() { printf 20261018T120000Z; }
  docker() {
    if [[ "$1 $2" == "image inspect" ]]; then return 1; fi
    if [[ "$1 $2" == "image tag" ]]; then record "tag:$3:$4"; return 0; fi
    return 1
  }
  write_state() { record "state:$1:$2"; }
  append_history() { record history; }
  TARGET_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  execute_baseline
' >"$output" 2>&1
grep -Fq 'state:app-last-healthy.sha:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' "$log"
grep -Fq 'state:app-last-healthy.snapshot:20261018T120000Z-aaaaaaaaaaaa-' "$log"
if grep -Eq 'compose up|recreate_service' "$log"; then
  echo "registro inicial recriou serviços" >&2; exit 1
fi

: > "$log"
MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_DEPLOY_TEST_LOG="$log" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  TARGET_SHA=cccccccccccccccccccccccccccccccccccccccc
  TARGET_SNAPSHOT=20261018T120000Z-cccccccccccc-1
  compose() { printf "compose %s\n" "$*" >> "$MARKINA_DEPLOY_TEST_LOG"; }
  docker() {
    if [[ "$1 $2" == "image inspect" && "$3" == --format && "$5" == markina-gallery-api ]]; then printf "sha256:%064d\n" 1; return 0; fi
    if [[ "$1 $2" == "image inspect" && "$3" == --format && "$5" == markina-gallery-web ]]; then printf "sha256:%064d\n" 2; return 0; fi
    if [[ "$1 $2" == "image inspect" && "$3" == markina-gallery-api*production-app-* ]]; then return 1; fi
    if [[ "$1 $2" == "image inspect" && "$3" == markina-gallery-web*production-app-* ]]; then return 1; fi
    if [[ "$1 $2" == "image tag" ]]; then printf "tag %s %s\n" "$3" "$4" >> "$MARKINA_DEPLOY_TEST_LOG"; return 0; fi
    return 1
  }
  build_target_images
' >"$output" 2>&1
grep -Fxq 'compose build api web' "$log"
grep -Fxq "tag sha256:$(printf '%064d' 1) markina-gallery-api:production-app-20261018T120000Z-cccccccccccc-1" "$log"
grep -Fxq "tag sha256:$(printf '%064d' 2) markina-gallery-web:production-app-20261018T120000Z-cccccccccccc-1" "$log"

: > "$log"
MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_DEPLOY_TEST_LOG="$log" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  TARGET_SNAPSHOT=20261018T120000Z-cccccccccccc-1
  compose() { printf "build %s\n" "$*" >> "$MARKINA_DEPLOY_TEST_LOG"; }
  docker() {
    if [[ "$1 $2" == "image inspect" && "$3" == markina-gallery-api:production-app-* ]]; then return 0; fi
    return 1
  }
  if build_target_images; then exit 27; fi
' >"$output" 2>&1
if grep -Fq 'build api web' "$log"; then
  echo "tag de snapshot já ocupado iniciou build" >&2; exit 1
fi

: > "$log"
if MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_DEPLOY_TEST_LOG="$log" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  record() { printf "%s\n" "$*" >> "$MARKINA_DEPLOY_TEST_LOG"; }
  verify_approval() { ACTIVE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; CHECKOUT_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb; record approval; }
  switch_to_target() { record switch; }
  preserve_active_images() { record preserve; }
  build_target_images() { record build; return 1; }
  write_state() { record "state:$1"; }
  recreate_service() { record "up:$1"; }
  execute_release
' >"$output" 2>&1; then
  echo "falha de build foi ignorada" >&2; exit 1
fi
grep -Fxq approval "$log"
grep -Fxq build "$log"
if grep -Eq '^state:|^up:' "$log"; then
  echo "falha de build avançou para gravação de release ou troca de contêiner" >&2; exit 1
fi

: > "$log"
MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_DEPLOY_TEST_LOG="$log" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  record() { printf "%s\n" "$*" >> "$MARKINA_DEPLOY_TEST_LOG"; }
  verify_approval() { ACTIVE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; CHECKOUT_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb; API_IMAGE_ID=api-old; WEB_IMAGE_ID=web-old; record approval; }
  switch_to_target() { record switch; }
  preserve_active_images() { record preserve; }
  build_target_images() { record build; }
  write_state() { record "state:$1"; }
  tag_for_default() { record "tag:$1:$2"; }
  recreate_service() { record "up:$1"; }
  wait_service_healthy() { record "healthy:$1"; }
  smoke_check_pair() { record smoke; }
  clear_in_flight() { record clear; }
  append_history() { record history; }
  TARGET_SHA=cccccccccccccccccccccccccccccccccccccccc
  execute_release
' >"$output" 2>&1

assert_before() {
  local first second first_line second_line
  first_line="$(grep -n -m1 -F "$1" "$log" | cut -d: -f1)"
  second_line="$(grep -n -m1 -F "$2" "$log" | cut -d: -f1)"
  [[ "$first_line" -lt "$second_line" ]] || { echo "ordem inválida: $1 antes de $2" >&2; exit 1; }
}
assert_before switch build
assert_before build 'state:app-previous.sha'
assert_before 'tag:api:' 'up:api'
assert_before 'up:api' healthy:api
assert_before healthy:api 'up:web'
assert_before healthy:web smoke

: > "$log"
if MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_DEPLOY_TEST_LOG="$log" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  record() { printf "%s\n" "$*" >> "$MARKINA_DEPLOY_TEST_LOG"; }
  verify_approval() { ACTIVE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; CHECKOUT_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb; record approval; }
  switch_to_target() { record switch; }
  preserve_active_images() { record preserve; }
  build_target_images() { record build; }
  write_state() { record "state:$1"; }
  tag_for_default() { record "tag:$1"; }
  recreate_service() { record "up:$1"; }
  wait_service_healthy() { record "health:$1"; [[ "$1" != api ]]; }
  smoke_check_pair() { record smoke; }
  clear_in_flight() { record clear; }
  append_history() { record history; }
  TARGET_SHA=cccccccccccccccccccccccccccccccccccccccc
  execute_release
' >"$output" 2>&1; then
  echo "API sem healthcheck foi promovida" >&2; exit 1
fi
grep -Fxq 'up:api' "$log"
if grep -Eq '^up:web$|^clear$|^history$' "$log"; then
  echo "falha de saúde da API promoveu web ou fechou a tentativa" >&2; exit 1
fi

: > "$log"
if MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_DEPLOY_TEST_LOG="$log" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  record() { printf "%s\n" "$*" >> "$MARKINA_DEPLOY_TEST_LOG"; }
  verify_approval() { ACTIVE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; CHECKOUT_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb; record approval; }
  switch_to_target() { record switch; }
  preserve_active_images() { record preserve; }
  build_target_images() { record build; }
  write_state() { record "state:$1"; }
  tag_for_default() { record "tag:$1"; }
  recreate_service() { record "up:$1"; }
  wait_service_healthy() { record "health:$1"; }
  smoke_check_pair() { record smoke; return 1; }
  clear_in_flight() { record clear; }
  append_history() { record history; }
  TARGET_SHA=cccccccccccccccccccccccccccccccccccccccc
  execute_release
' >"$output" 2>&1; then
  echo "falha de smoke test foi registrada como saudável" >&2; exit 1
fi
grep -Fxq 'state:app-in-flight.sha' "$log"
if grep -Eq '^state:app-last-healthy.sha$|^clear$|^history$' "$log"; then
  echo "falha de smoke test limpou ou validou tentativa" >&2; exit 1
fi

: > "$log"
MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_DEPLOY_TEST_LOG="$log" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  record() { printf "%s\n" "$*" >> "$MARKINA_DEPLOY_TEST_LOG"; }
  verify_approval() { ACTIVE_SHA=cccccccccccccccccccccccccccccccccccccccc; API_IMAGE_ID=api-current; WEB_IMAGE_ID=web-current; record approval; }
  preserve_active_images() { record preserve; }
  tag_for_default() { record "tag:$1:$2"; }
  write_state() { record "state:$1"; }
  recreate_service() { record "up:$1"; }
  wait_service_healthy() { record "healthy:$1"; }
  smoke_check_pair() { record smoke; }
  clear_in_flight() { record clear; }
  append_history() { record history; }
  TARGET_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  TARGET_SNAPSHOT=20261018T120000Z-aaaaaaaaaaaa-1
  execute_rollback
' >"$output" 2>&1
assert_before 'tag:api:20261018T120000Z-aaaaaaaaaaaa-1' 'up:api'
assert_before 'up:api' 'up:web'
assert_before 'up:web' smoke

: > "$log"
if MARKINA_DEPLOY_APP_SCRIPT_PATH="$SCRIPT" MARKINA_DEPLOY_TEST_LOG="$log" bash -c '
  source "$MARKINA_DEPLOY_APP_SCRIPT_PATH"
  record() { printf "%s\n" "$*" >> "$MARKINA_DEPLOY_TEST_LOG"; }
  verify_approval() { ACTIVE_SHA=cccccccccccccccccccccccccccccccccccccccc; record approval; }
  preserve_active_images() { record preserve; }
  tag_for_default() { record "tag:$1"; }
  write_state() { record "state:$1"; }
  recreate_service() { record "up:$1"; }
  wait_service_healthy() { record "health:$1"; [[ "$1" != api ]]; }
  smoke_check_pair() { record smoke; }
  clear_in_flight() { record clear; }
  append_history() { record history; }
  TARGET_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  TARGET_SNAPSHOT=20261018T120000Z-aaaaaaaaaaaa-1
  execute_rollback
' >"$output" 2>&1; then
  echo "rollback com API não saudável foi concluído" >&2; exit 1
fi
grep -Fxq 'up:api' "$log"
if grep -Eq '^up:web$|^clear$|^history$' "$log"; then
  echo "rollback parcial declarou sucesso ou avançou para web" >&2; exit 1
fi
echo "deploy-prod-app shell: ok"
