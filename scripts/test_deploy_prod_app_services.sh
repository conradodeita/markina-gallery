#!/usr/bin/env bash
set -Eeuo pipefail

script="$(cat scripts/deploy-prod-app-services.sh)"
require() { [[ "$script" == *"$1"* ]] || { echo "trecho de release ausente: $1" >&2; exit 1; }; }
require 'readonly SERVICES=(api web)'
require 'GIT_WORK_TREE="$PROJECT_ROOT"'
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
echo 'production API/web release policy: ok'
