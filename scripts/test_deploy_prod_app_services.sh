#!/usr/bin/env bash
set -Eeuo pipefail
script="$(cat scripts/deploy-prod-app-services.sh)"
for required in 'readonly SERVICES=(api web)' 'readonly EXPECTED_DATABASE_REVISION="20261113_0126"' \
  'verify_readonly_target_ancestry' 'GIT_WORK_TREE="$PROJECT_ROOT"' 'scripts/check_prod_app_release_scope.py' \
  'git diff --quiet "$CHECKOUT_SHA" "$TARGET_SHA" -- backend/migrations/' \
  'require_facial_processing_enabled_in_config' 'FACIAL_PROCESSING_ENABLED=true' \
  'readonly APP_COMPOSE_BRIDGE="/usr/local/sbin/markina-gallery-app-compose-bridge"' \
  '--artifact-sha256' 'verify_candidate_artifact' 'production_app_artifact.py verify' \
  'docker load --input "$CANDIDATE_IMAGE_ARCHIVE"' '--api-base-image-id' \
  'linux/arm64' '--no-build --no-deps' \
  'sudo -n "$APP_COMPOSE_BRIDGE"' 'bridge_call snapshot' 'bridge_call sources-fingerprint' \
  'compose up -d --no-build --no-deps --force-recreate --wait --wait-timeout 120 "${SERVICES[@]}"' \
  'compose exec -T nginx nginx -t' 'compose exec -T nginx nginx -s reload' 'runtime_snapshot' \
  'app-web-rollback.identity' 'app-api-rollback.version' 'web-current.identity' 'app-$service-rollback-id' \
  'bridge_call service-hash' 'bridge_call web-identity'; do
  [[ "$script" == *"$required"* ]] || { echo "gate app ausente: $required" >&2; exit 1; }
done
for forbidden in 'alembic upgrade' 'git fetch' 'mktemp' 'compose run' 'face-search-worker' 'docker compose down' \
  'docker system prune' 'docker/docker-compose.raw-development.yml' 'compose build' 'docker build'; do
  [[ "$script" != *"$forbidden"* ]] || { echo "operação app proibida: $forbidden" >&2; exit 1; }
done
bash -n scripts/deploy-prod-app-services.sh
python3 scripts/test_prod_release_state.py \
  ReleaseContracts.test_app_inventory_no_temporary_fetch_or_writes \
  ReleaseContracts.test_app_then_web_and_web_then_app \
  ReleaseContracts.test_web_then_app_inventory_preserves_api_version \
  ReleaseContracts.test_app_failed_artifact_or_health_preserves_recovery_identity \
  ReleaseContracts.test_orders_wrapper_runs_only_pinned_python_inventory_with_exact_sha \
  ReleaseContracts.test_wrapper_validates_body_in_memory_and_rejects_tampering \
  ReleaseContracts.test_fingerprint_cannot_hide_runtime_failure
printf 'production API/web release policy: ok\n'
