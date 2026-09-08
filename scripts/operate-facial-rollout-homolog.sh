#!/usr/bin/env bash
# Inventário e operação persistente do rollout facial de uma galeria em homologação.

set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly ENV_FILE="docker/.env.homolog"
readonly BACKUP_DIR="/var/lib/markina-gallery/backups"
readonly REQUIRED_GATES="security,privacy,legal_basis,calibration,capacity,recovery,human_approval"
readonly PUBLIC_BASE_URL="https://markina-homolog.duckdns.org"

ACTION=""
GALLERY_ID=""
STAGE="canary"
EXPECTED_SHA=""
CONFIRMATION=""
ACTOR_ADMIN_ID=""
RUN_REFERENCE=""

fail() {
  echo "operate-facial-rollout-homolog: $*" >&2
  return 1
}

compose() {
  docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@" </dev/null
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --action) ACTION="${2:-}"; shift 2 ;;
    --gallery-id) GALLERY_ID="${2:-}"; shift 2 ;;
    --stage) STAGE="${2:-}"; shift 2 ;;
    --expected-sha) EXPECTED_SHA="${2:-}"; shift 2 ;;
    --confirmation) CONFIRMATION="${2:-}"; shift 2 ;;
    --actor-admin-id) ACTOR_ADMIN_ID="${2:-}"; shift 2 ;;
    --run-reference) RUN_REFERENCE="${2:-}"; shift 2 ;;
    *) fail "argumento não permitido: $1" ;;
  esac
done

[[ "$ACTION" == "inventory" || "$ACTION" == "activate" || "$ACTION" == "suspend" ]] \
  || fail "ação deve ser inventory, activate ou suspend"
[[ "$STAGE" == "canary" || "$STAGE" == "limited" || "$STAGE" == "general" ]] \
  || fail "etapa deve ser canary, limited ou general"
[[ "$GALLERY_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] \
  || fail "UUID público da Galeria pública é obrigatório"
[[ "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA integral publicado é obrigatório"
[[ "$RUN_REFERENCE" =~ ^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$ ]] \
  || fail "referência opaca da execução é obrigatória"
if [[ -n "$ACTOR_ADMIN_ID" ]]; then
  [[ "$ACTOR_ADMIN_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] \
    || fail "UUID do administrador é inválido"
fi
if [[ "$ACTION" == "inventory" ]]; then
  [[ -z "$CONFIRMATION" ]] || fail "inventário não aceita confirmação de mutação"
else
  expected_confirmation="${ACTION^^}_FACIAL_HOMOLOG_${STAGE^^}"
  [[ "$CONFIRMATION" == "$expected_confirmation" ]] || fail "confirmação literal inválida"
fi

[[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "execução permitida somente em $PROJECT_ROOT"
[[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" ]] || fail "configuração exclusiva da Markina ausente"
compose config --quiet

deployed_sha="$(git rev-parse HEAD)"
[[ "$deployed_sha" == "$EXPECTED_SHA" ]] || fail "SHA publicado diverge do escopo aprovado"
[[ -z "$(git status --porcelain)" ]] || fail "checkout remoto possui alterações locais"

echo "topologia: projeto=$PROJECT_NAME entrada=127.0.0.1:8080 subdomínio=markina-homolog.duckdns.org"
topology="$(docker ps --filter "label=com.docker.compose.project=$PROJECT_NAME" --format '{{.Names}}|{{.Status}}|{{.Ports}}')"
[[ -n "$topology" ]] || fail "containers Markina ausentes"
if grep -Eq '(^|[|,[:space:]])(0\.0\.0\.0|::):[0-9]+->' <<<"$topology"; then
  fail "porta pública inesperada no projeto Markina"
fi
printf '%s\n' "$topology"

for service in api web worker nginx face-search-worker face-index-worker face-maintenance-worker; do
  container="$(compose ps -q "$service")"
  [[ -n "$container" ]] || fail "serviço Markina ausente: $service"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
  [[ "$health" == "healthy" ]] || fail "serviço Markina não saudável: $service ($health)"
done
curl --fail --silent --show-error --retry 3 --retry-delay 2 http://127.0.0.1:8080/healthz >/dev/null
curl --fail --silent --show-error --retry 3 --retry-delay 2 http://127.0.0.1:8080/api/health >/dev/null
curl --fail --silent --show-error --retry 3 --retry-delay 2 "$PUBLIC_BASE_URL/healthz" >/dev/null
curl --fail --silent --show-error --retry 3 --retry-delay 2 "$PUBLIC_BASE_URL/api/health" >/dev/null

revision="$(compose run --rm --no-deps migrate alembic current 2>/dev/null | tr -d '\r' | tail -n 1)"
[[ -n "$revision" && "$revision" == *"(head)"* ]] || fail "migration não está no head publicado"

runtime_state="$(compose exec -T api python -c '
from app.facial.config import facial_settings_from_environment
s = facial_settings_from_environment(verify_runtime_assets=False)
assert s.enabled and s.environment in {"homolog", "homologation"}
assert all((s.model_version, s.quality_version, s.calibration_version,
            s.legal_notice_version, s.consent_version,
            s.legal_basis_reference, s.retention_policy_version))
print("enabled")
')"
[[ "$runtime_state" == "enabled" ]] || fail "runtime facial de homologação não está habilitado"

scope_state="$(
  compose exec -T \
    -e MARKINA_GALLERY_ID="$GALLERY_ID" \
    -e MARKINA_ACTOR_ADMIN_ID="$ACTOR_ADMIN_ID" \
    api python -c '
import os
from uuid import UUID
from sqlalchemy import select
from app.auth import AdminUser, ParentGallery, SessionLocal

gallery_id = UUID(os.environ["MARKINA_GALLERY_ID"])
requested_actor = os.environ.get("MARKINA_ACTOR_ADMIN_ID", "").strip()
with SessionLocal() as db:
    gallery = db.get(ParentGallery, gallery_id)
    if gallery is None or not gallery.active or gallery.lifecycle_status != "active":
        raise SystemExit("Galeria pública ativa não encontrada.")
    admins = list(db.scalars(select(AdminUser.id).order_by(AdminUser.id)))
    if requested_actor:
        actor_id = UUID(requested_actor)
        if actor_id not in admins:
            raise SystemExit("Administrador aprovador não encontrado.")
    else:
        if len(admins) != 1:
            raise SystemExit("Informe o administrador quando homologação não possuir exatamente um.")
        actor_id = admins[0]
    print(actor_id)
'
)"
[[ "$scope_state" =~ ^[0-9a-f-]{36}$ ]] || fail "escopo administrativo não pôde ser resolvido"
resolved_actor_id="$scope_state"
unset scope_state

echo "inventário aprovado: sha=$deployed_sha migration=$revision facial=enabled escopo_galerias=1"
echo "referência opaca do inventário: ${RUN_REFERENCE}:inventory"

if [[ "$ACTION" == "inventory" ]]; then
  echo "inventário facial de homologação concluído sem mutação"
  exit 0
fi

mkdir -p "$BACKUP_DIR"
backup_file="$BACKUP_DIR/pre-facial-rollout-$(date -u +%Y%m%dT%H%M%SZ)-${EXPECTED_SHA:0:12}.dump"
compose exec -T db sh -ceu 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$backup_file"
[[ -s "$backup_file" ]] || fail "backup lógico não foi criado"
echo "backup lógico exclusivo da Markina criado antes da mutação"

compose exec -T api python -m app.facial.manage_rollout \
  --action "$ACTION" \
  --environment homolog \
  --stage "$STAGE" \
  --sha "$EXPECTED_SHA" \
  --inventory-ref "${RUN_REFERENCE}:inventory" \
  --backup-ref "${RUN_REFERENCE}:backup" \
  --gate-set-version "homolog-product-gates-v1" \
  --approved-gates "$REQUIRED_GATES" \
  --allowlist "$GALLERY_ID" \
  --confirmation "$CONFIRMATION" \
  --actor-admin-id "$resolved_actor_id"

if [[ "$ACTION" == "activate" ]]; then
  if ! compose exec -T api python -m app.facial.reconcile_gallery \
    --gallery-id "$GALLERY_ID" --page-size 100; then
    compose exec -T api python -m app.facial.manage_rollout \
      --action suspend --environment homolog --stage "$STAGE" --sha "$EXPECTED_SHA" \
      --inventory-ref "${RUN_REFERENCE}:inventory" --backup-ref "${RUN_REFERENCE}:backup" \
      --gate-set-version "homolog-product-gates-v1" --approved-gates "$REQUIRED_GATES" \
      --allowlist "$GALLERY_ID" --confirmation "SUSPEND_FACIAL_HOMOLOG_${STAGE^^}" \
      --actor-admin-id "$resolved_actor_id" \
      || fail "reconciliação falhou e a contenção não foi confirmada"
    fail "reconciliação falhou; rollout suspenso como contenção"
  fi
  compose restart face-index-worker >/dev/null
  container="$(compose ps -q face-index-worker)"
  for _attempt in $(seq 1 30); do
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")"
    [[ "$health" == "healthy" ]] && break
    sleep 2
  done
  if [[ "$health" != "healthy" ]]; then
    compose exec -T api python -m app.facial.manage_rollout \
      --action suspend --environment homolog --stage "$STAGE" --sha "$EXPECTED_SHA" \
      --inventory-ref "${RUN_REFERENCE}:inventory" --backup-ref "${RUN_REFERENCE}:backup" \
      --gate-set-version "homolog-product-gates-v1" --approved-gates "$REQUIRED_GATES" \
      --allowlist "$GALLERY_ID" --confirmation "SUSPEND_FACIAL_HOMOLOG_${STAGE^^}" \
      --actor-admin-id "$resolved_actor_id" \
      || fail "worker não voltou saudável e a contenção não foi confirmada"
    fail "worker de índice não voltou saudável; rollout suspenso como contenção"
  fi
  echo "rollout persistente ativo; reconciliação do índice iniciada"
else
  echo "rollout persistente suspenso; novas admissões bloqueadas"
fi
unset resolved_actor_id
