#!/usr/bin/env bash
set -Eeuo pipefail

script="$(cat scripts/deploy-prod-app-services.sh)"
require() { [[ "$script" == *"$1"* ]] || { echo "trecho de release ausente: $1" >&2; exit 1; }; }
require 'readonly SERVICES=(api web)'
require 'readonly EXPECTED_DATABASE_REVISION="20261017_0084"'
require 'GIT_WORK_TREE="$PROJECT_ROOT"'
require 'verify_readonly_target_ancestry'
require '--filter=blob:none'
require 'scripts/check_prod_app_release_scope.py'
require 'git diff --quiet "$CHECKOUT_SHA" "$TARGET_SHA" -- docker/ backend/migrations/'
require 'compose up -d --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"'
require 'compose exec -T nginx nginx -t'
require 'compose exec -T nginx nginx -s reload'
require 'approval_fingerprint=%s'
require 'runtime_snapshot'
require 'database_revision'
require 'rollback_inventory()'
require 'rollback()'
require '--no-build --no-deps --force-recreate --wait --wait-timeout 120'
require 'app-previous.sha'
require 'app-$service-rollback-image'
for forbidden in 'alembic upgrade' 'compose run' 'face-search-worker' 'worker)' 'docker compose down' 'docker system prune'; do
  if [[ "$script" == *"$forbidden"* ]]; then echo "operação proibida no release app: $forbidden" >&2; exit 1; fi
done
if [[ "$script" == *"--no-write-fetch-head"* ]]; then
  echo 'inventário depende de opção Git indisponível no host' >&2; exit 1
fi

# Exercise release and rollback sequencing with an isolated script copy and
# mocked Git, Compose, Docker, curl, and inventory boundaries.
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
mkdir -p "$tmpdir/state"
sed "s|^readonly STATE_DIR=.*|readonly STATE_DIR=\"$tmpdir/state\"|" \
  scripts/deploy-prod-app-services.sh > "$tmpdir/deploy.sh"
source "$tmpdir/deploy.sh"

# Verify target ancestry in a temporary bare partial clone without changing
# the active checkout's refs, FETCH_HEAD, worktree, or HEAD.
history_source="$tmpdir/history-source"
history_origin="$tmpdir/history-origin.git"
history_active="$tmpdir/history-active"
git init --quiet "$history_source"
git -C "$history_source" symbolic-ref HEAD refs/heads/main
git -C "$history_source" config user.name "Release test"
git -C "$history_source" config user.email "release-test@example.invalid"
printf 'base\n' > "$history_source/history.txt"
git -C "$history_source" add history.txt
git -C "$history_source" commit --quiet -m base
history_checkout_sha="$(git -C "$history_source" rev-parse HEAD)"
git clone --quiet --bare "$history_source" "$history_origin"
git -C "$history_origin" config uploadpack.allowFilter true
printf 'candidate\n' >> "$history_source/history.txt"
git -C "$history_source" commit --quiet -am candidate
git -C "$history_source" push --quiet "$history_origin" main
history_target_sha="$(git -C "$history_origin" rev-parse refs/heads/main)"
git clone --quiet "$history_origin" "$history_active"
git -C "$history_active" checkout --quiet --detach "$history_checkout_sha"
history_refs_before="$(git -C "$history_active" for-each-ref --format='%(refname) %(objectname)')"
history_status_before="$(git -C "$history_active" status --porcelain)"
history_fetch_head_before="$(cat "$history_active/.git/FETCH_HEAD" 2>/dev/null || true)"
if [[ -e "$tmpdir/FETCH_HEAD" ]]; then history_temp_fetch_head=present; else history_temp_fetch_head=absent; fi
(
  cd "$history_active"
  TMPDIR="$tmpdir" verify_readonly_target_ancestry "$history_origin" "$history_checkout_sha" "$history_target_sha"
)
[[ "$(git -C "$history_active" rev-parse HEAD)" == "$history_checkout_sha" ]]
[[ "$(git -C "$history_active" for-each-ref --format='%(refname) %(objectname)')" == "$history_refs_before" ]]
[[ "$(git -C "$history_active" status --porcelain)" == "$history_status_before" ]]
[[ "$(cat "$history_active/.git/FETCH_HEAD" 2>/dev/null || true)" == "$history_fetch_head_before" ]]
if [[ "$history_temp_fetch_head" == absent ]]; then [[ ! -e "$tmpdir/FETCH_HEAD" ]]; fi
[[ -z "$(find "$tmpdir" -maxdepth 1 -type d -name 'markina-app-history.*' -print -quit)" ]]
if (
  cd "$history_active"
  TMPDIR="$tmpdir" verify_readonly_target_ancestry "$history_origin" "$history_checkout_sha" "$history_checkout_sha"
) > "$tmpdir/ancestry-divergence.out" 2>&1; then
  echo 'inventário aceitou SHA diferente do HEAD remoto' >&2; exit 1
fi
grep -q 'HEAD de main mudou durante o inventário' "$tmpdir/ancestry-divergence.out"
[[ -z "$(find "$tmpdir" -maxdepth 1 -type d -name 'markina-app-history.*' -print -quit)" ]]

CALL_LOG="$tmpdir/calls"
CHECKOUT_SHA="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
ACTIVE_SHA="$CHECKOUT_SHA"
TARGET_SHA="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
ROLLBACK_SHA="$CHECKOUT_SHA"
EXPECTED_URL="https://markina.pickyourpic.com.br"
DATABASE_REVISION="20261017_0084"
TEST_DATABASE_REVISION="20261017_0084"
COMPOSE_APP_VERSION="$CHECKOUT_SHA"
APPROVAL_FINGERPRINT="$(printf 'f%.0s' {1..64})"
INVENTORY_FINGERPRINT="$APPROVAL_FINGERPRINT"

verify_repository() {
  CHECKOUT_SHA="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  ACTIVE_SHA="$CHECKOUT_SHA"
  DATABASE_REVISION="$TEST_DATABASE_REVISION"
  verify_database_revision "$DATABASE_REVISION"
  printf 'verify\n' >> "$CALL_LOG"
}
hostname() { printf 'clearbudget-vnic\n'; }
fingerprint() { printf '%s\n' "$INVENTORY_FINGERPRINT"; }
database_revision() { printf '%s\n' "$TEST_DATABASE_REVISION"; }
runtime_snapshot() {
  printf 'runtime_snapshot\n' >> "$CALL_LOG"
  printf 'api|container-api|sha256:api|%064d|healthy\n' 0
  printf 'web|container-web|sha256:web|%064d|healthy\n' 0
  printf 'nginx_bind=127.0.0.1:8080\ncompose_config=%064d\n' 0
}
compose() {
  printf 'compose %s\n' "$*" >> "$CALL_LOG"
  if [[ "$1" == ps && "$2" == -q ]]; then printf 'container-%s\n' "$3"; fi
}
docker() {
  printf 'docker %s\n' "$*" >> "$CALL_LOG"
  case "$*" in
    'inspect --format {{.Image}} container-api') printf 'sha256:old-api\n' ;;
    'inspect --format {{.Image}} container-web') printf 'sha256:old-web\n' ;;
    'inspect --format {{.Config.Image}} container-api') printf 'markina-api:old\n' ;;
    'inspect --format {{.Config.Image}} container-web') printf 'markina-web:old\n' ;;
    *) ;;
  esac
}
git() { printf 'git %s\n' "$*" >> "$CALL_LOG"; }
curl() { printf 'curl %s\n' "$*" >> "$CALL_LOG"; }

MODE="inventory"
inventory > "$tmpdir/inventory.out"
grep -q '^host=clearbudget-vnic projeto=markina-gallery domínio=https://markina.pickyourpic.com.br' "$tmpdir/inventory.out"
grep -q '^serviços=api,web revisão_schema=20261017_0084 portas=nginx:127.0.0.1:8080$' "$tmpdir/inventory.out"
grep -q '^approval_fingerprint=' "$tmpdir/inventory.out"
for endpoint in /healthz /api/health /; do grep -Fq "curl -fsS --max-time 10 https://markina.pickyourpic.com.br$endpoint" "$CALL_LOG"; done
if grep -Eq '^compose (build|up)|^docker image tag|^git switch' "$CALL_LOG"; then
  echo 'inventário executou operação mutável' >&2; exit 1
fi

MODE="release"
: > "$CALL_LOG"
release
grep -Fq 'compose build api web' "$CALL_LOG"
grep -Fq 'compose up -d --no-deps --force-recreate --wait --wait-timeout 120 api web' "$CALL_LOG"
if grep -Eq 'face-search-worker|alembic upgrade|compose run|docker compose down' "$CALL_LOG"; then
  echo 'release app simulou serviço ou migration fora do escopo' >&2; exit 1
fi

: > "$CALL_LOG"
TEST_DATABASE_REVISION="20261017_0083"
if ( release ) >"$tmpdir/schema-divergence.out" 2>&1; then
  echo 'schema divergente foi aceito pelo release app' >&2; exit 1
fi
if grep -Eq '^docker |^compose (build|up)|^git switch' "$CALL_LOG"; then
  echo 'schema divergente alterou serviço ou imagem antes de abortar' >&2; exit 1
fi
TEST_DATABASE_REVISION="20261017_0084"

: > "$CALL_LOG"
MODE="inventory"
TEST_DATABASE_REVISION="20261017_0083"
if ( inventory ) >"$tmpdir/inventory-schema-divergence.out" 2>&1; then
  echo 'inventário aceitou schema divergente' >&2; exit 1
fi
if grep -Eq '^docker |^compose (build|up)|^git switch' "$CALL_LOG"; then
  echo 'inventário divergente alterou serviço ou imagem' >&2; exit 1
fi
TEST_DATABASE_REVISION="20261017_0084"
MODE="release"

: > "$CALL_LOG"
INVENTORY_FINGERPRINT="$(printf 'e%.0s' {1..64})"
if ( release ) >"$tmpdir/divergent.out" 2>&1; then
  echo 'fingerprint divergente foi aceito' >&2; exit 1
fi
if grep -q '^docker ' "$CALL_LOG"; then echo 'fingerprint divergente alterou imagens' >&2; exit 1; fi

: > "$CALL_LOG"
INVENTORY_FINGERPRINT="$APPROVAL_FINGERPRINT"
MODE="rollback"
CHECKOUT_SHA="$TARGET_SHA"
ACTIVE_SHA="$CHECKOUT_SHA"
ROLLBACK_SHA="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
rollback
grep -Fq 'compose up -d --no-build --no-deps --force-recreate --wait --wait-timeout 120 api web' "$CALL_LOG"
if grep -Eq 'face-search-worker|alembic upgrade|compose run|docker compose down' "$CALL_LOG"; then
  echo 'rollback app simulou serviço ou migration fora do escopo' >&2; exit 1
fi
echo 'production API/web release policy: ok'
