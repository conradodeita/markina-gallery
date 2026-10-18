#!/usr/bin/env bash
# Fixtures sintéticas: configuração resolvida deve corresponder aos labels,
# sem emitir seus valores; diferenças reais e saúde ruim devem ser recusadas.
set -Eeuo pipefail
source "$(dirname "$0")/deploy-prod-facial-services.sh"

readonly WEB_HASH="$(printf 'a%.0s' {1..64})"
readonly API_HASH="$(printf 'b%.0s' {1..64})"
readonly WORKER_HASH="$(printf 'c%.0s' {1..64})"
readonly SYNTHETIC_CONFIG='{"services":{"api":{"environment":{"TOKEN":"synthetic-sensitive-$literal"}}}}'
BAD_SERVICE=""
UNHEALTHY_SERVICE=""
FACIAL_RUNTIME=true

compose() {
  case "$*" in
    'config --quiet') return 0 ;;
    'config --format json')
      if [[ -n "${EXPECTED_PRIMARY_YAML:-}" ]]; then
        [[ "${COMPOSE_PRIMARY_YAML:-}" == "$EXPECTED_PRIMARY_YAML" && "$COMPOSE_APP_VERSION" == "$ACTIVE_SHA" ]] || return 1
      fi
      printf '%s\n' "$SYNTHETIC_CONFIG" ;;
    'ps -q web') echo web ;;
    'ps -q api') echo api ;;
    'ps -q face-search-worker') echo face-search-worker ;;
    'ps -q nginx') echo nginx ;;
    *) echo 'chamada Compose inesperada na fixture' >&2; return 1 ;;
  esac
}

docker() {
  if [[ "$1" == compose ]]; then
    [[ "$*" == 'compose -p markina-gallery -f - --profile facial --profile preview-adjustment config --no-interpolate --hash web,api,face-search-worker' ]] || return 1
    local payload
    payload="$(cat)"
    [[ "$payload" == "$SYNTHETIC_CONFIG" ]] || return 1
    printf 'api %s\nface-search-worker %s\nweb %s\n' "$API_HASH" "$WORKER_HASH" "$WEB_HASH"
    return 0
  fi
  [[ "$1" == inspect && "$2" == --format ]] || return 1
  local format="$3" service="$4"
  case "$format" in
    '{{json .Config.Env}}') printf '["FACIAL_PROCESSING_ENABLED=%s"]\n' "$FACIAL_RUNTIME" ;;
    *com.docker.compose.project.config_files*) echo "$COMPOSE_FILE_LABEL" ;;
    *com.docker.compose.project.working_dir*) echo /opt/markina-gallery/docker ;;
    *com.docker.compose.project*) echo markina-gallery ;;
    *com.docker.compose.service*) echo "$service" ;;
    *com.docker.compose.config-hash*)
      if [[ "$service" == "$BAD_SERVICE" ]]; then printf 'd%.0s' {1..64}; echo
      elif [[ "$service" == web ]]; then echo "$WEB_HASH"
      elif [[ "$service" == api ]]; then echo "$API_HASH"
      else echo "$WORKER_HASH"; fi ;;
    *State.Health*)
      if [[ "$service" == "$UNHEALTHY_SERVICE" ]]; then echo unhealthy; else echo healthy; fi ;;
    '{{.Image}}') echo "sha256:synthetic-$service" ;;
    '{{json .NetworkSettings.Ports}}') echo '{"80/tcp":[{"HostIp":"127.0.0.1","HostPort":"8080"}]}' ;;
    *) echo 'inspect inesperado na fixture' >&2; return 1 ;;
  esac
}

output="$(mktemp)"
baseline_file="$(mktemp)"
scope_repo="$(mktemp -d)"
trap 'rm -f "$output" "$baseline_file"; rm -rf -- "$scope_repo"' EXIT
runtime_snapshot >"$output"
grep -q '^api|api|sha256:synthetic-api|' "$output"
grep -q '^face-search-worker|face-search-worker|' "$output"
grep -q '^compose_config=[0-9a-f]\{64\}$' "$output"
if grep -q 'synthetic-sensitive' "$output"; then echo 'configuração vazou na saída' >&2; exit 1; fi

for bad in api face-search-worker; do
  if ( BAD_SERVICE="$bad"; runtime_snapshot ) >"$output" 2>&1; then
    echo 'hash divergente não foi recusado' >&2; exit 1
  fi
  grep -q "configuração ativa de $bad diverge do Compose" "$output"
done
if ( UNHEALTHY_SERVICE=api; runtime_snapshot ) >"$output" 2>&1; then
  echo 'serviço sem saúde não foi recusado' >&2; exit 1
fi
grep -q 'container api não está saudável' "$output"
if ( FACIAL_RUNTIME=false; runtime_snapshot ) >"$output" 2>&1; then
  echo 'manutenção não pode ativar runtime desligado' >&2; exit 1
fi
grep -q 'manutenção exige runtime facial já ativo' "$output"
if grep -q 'synthetic-sensitive' "$output"; then echo 'configuração vazou no erro' >&2; exit 1; fi

CHECKOUT_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$CHECKOUT_SHA" > "$baseline_file"
verify_maintenance_baseline "$baseline_file"
printf '%s\n' "$(git rev-parse HEAD^)" > "$baseline_file"
verify_maintenance_baseline "$baseline_file"
printf '%s\n' "$(printf '0%.0s' {1..40})" > "$baseline_file"
if ( verify_maintenance_baseline "$baseline_file" ) >"$output" 2>&1; then
  echo 'baseline facial não ancestral foi aceito' >&2; exit 1
fi
printf 'invalid\n' > "$baseline_file"
if ( verify_maintenance_baseline "$baseline_file" ) >"$output" 2>&1; then
  echo 'marcador facial malformado foi aceito' >&2; exit 1
fi
if ( verify_maintenance_baseline "$baseline_file.missing" ) >"$output" 2>&1; then
  echo 'marcador facial ausente foi aceito' >&2; exit 1
fi
printf '%s\n%s\n' "$(git rev-parse HEAD^)" "$CHECKOUT_SHA" > "$baseline_file"
if ( verify_maintenance_baseline "$baseline_file" ) >"$output" 2>&1; then
  echo 'marcador facial com mais de uma revisão foi aceito' >&2; exit 1
fi

ACTIVE_SHA="$CHECKOUT_SHA"
TARGET_SHA="$CHECKOUT_SHA"
COMPOSE_APP_VERSION="$ACTIVE_SHA"
baseline_fp="$(fingerprint)"
EXPECTED_PRIMARY_YAML='synthetic previous Compose'
[[ "$(fingerprint_with_baseline_compose "$EXPECTED_PRIMARY_YAML")" == "$baseline_fp" ]] || { echo 'fingerprint anterior mudou com Compose alvo' >&2; exit 1; }
unset EXPECTED_PRIMARY_YAML

# Histórico isolado: a única exceção Docker exige autorização e blob exatos.
git -C "$scope_repo" init -q
mkdir -p "$scope_repo/docker" "$scope_repo/openspec/changes/improve-client-face-reference-capture"
printf 'baseline\n' > "$scope_repo/docker/docker-compose.yml"
scope_commit() {
  git -C "$scope_repo" add -- docker openspec
  git -C "$scope_repo" -c user.name=Fixture -c user.email=fixture@example.invalid commit -qm 'synthetic fixture'
}
scope_manifest() {
  python3 - "$scope_repo" "$1" <<'PY'
import base64, json, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1])
blob = subprocess.check_output(["git", "-C", str(root), "hash-object", "docker/docker-compose.yml"], text=True).strip()
encoded = base64.b64encode(bytes.fromhex(blob)).decode()
payload = {"maintenance_release": {"authorized": sys.argv[2] == "true", "scope": "existing_facial_runtime",
    "runtime_blobs": {"docker/docker-compose.yml": [encoded[i:i+7] for i in range(0, len(encoded), 7)]}}}
(root / "openspec/changes/improve-client-face-reference-capture/production-gates.json").write_text(json.dumps(payload))
PY
}
scope_manifest true
scope_commit
CHECKOUT_SHA="$(git -C "$scope_repo" rev-parse HEAD)"
printf 'reviewed candidate\n' > "$scope_repo/docker/docker-compose.yml"
scope_manifest true
scope_commit
TARGET_SHA="$(git -C "$scope_repo" rev-parse HEAD)"
verify_reviewed_docker_changes "$scope_repo"
printf 'unreviewed candidate\n' > "$scope_repo/docker/docker-compose.yml"
scope_commit
TARGET_SHA="$(git -C "$scope_repo" rev-parse HEAD)"
if ( verify_reviewed_docker_changes "$scope_repo" ) >"$output" 2>&1; then echo 'Compose sem blob revisado foi aceito' >&2; exit 1; fi
grep -q 'Compose diverge do blob autorizado' "$output"
scope_manifest false
scope_commit
TARGET_SHA="$(git -C "$scope_repo" rev-parse HEAD)"
if ( verify_reviewed_docker_changes "$scope_repo" ) >"$output" 2>&1; then echo 'Compose sem autorização foi aceito' >&2; exit 1; fi
grep -q 'Compose sem manifesto autorizado válido' "$output"
printf '%s\n' '{"maintenance_release":{"authorized":true,"scope":"existing_facial_runtime","runtime_blobs":{"docker/docker-compose.yml":["invalid"]}}}' > "$scope_repo/openspec/changes/improve-client-face-reference-capture/production-gates.json"
scope_commit
TARGET_SHA="$(git -C "$scope_repo" rev-parse HEAD)"
if ( verify_reviewed_docker_changes "$scope_repo" ) >"$output" 2>&1; then echo 'manifesto Compose inválido foi aceito' >&2; exit 1; fi
grep -q 'Compose sem manifesto autorizado válido' "$output"
scope_manifest true
scope_commit
TARGET_SHA="$(git -C "$scope_repo" rev-parse HEAD)"
verify_reviewed_docker_changes "$scope_repo"
printf 'unapproved Docker file\n' > "$scope_repo/docker/unapproved.yml"
scope_commit
TARGET_SHA="$(git -C "$scope_repo" rev-parse HEAD)"
if ( verify_reviewed_docker_changes "$scope_repo" ) >"$output" 2>&1; then echo 'Docker fora do escopo foi aceito' >&2; exit 1; fi
grep -q 'arquivo Docker fora do escopo revisado' "$output"

# Configuração via stdin conserva diretório-base, env_file raw e binds relativos.
# Somente `config`: nenhuma imagem, container, volume ou rede é criado.
config_dir="$scope_repo/config"
mkdir -p "$config_dir/media"
printf 'TOKEN=synthetic-sensitive-$literal\n' > "$config_dir/synthetic.env"
cat > "$config_dir/compose.yml" <<'YAML'
services:
  web:
    image: alpine:3.22
    env_file:
      - path: ./synthetic.env
        format: raw
    volumes:
      - ./media:/media:ro
  api:
    image: alpine:3.22
  face-search-worker:
    image: alpine:3.22
YAML
command docker compose -p markina-gallery -f "$config_dir/compose.yml" config --format json \
  | command docker compose -p markina-gallery -f - config --no-interpolate --hash web,api,face-search-worker > "$output"
file_hashes="$(cat "$output")"
command docker compose --project-directory "$config_dir" -p markina-gallery -f - config --format json < "$config_dir/compose.yml" \
  | command docker compose -p markina-gallery -f - config --no-interpolate --hash web,api,face-search-worker > "$output"
[[ "$(cat "$output")" == "$file_hashes" ]] || { echo 'Compose por stdin mudou o fingerprint da configuração anterior' >&2; exit 1; }
if grep -q 'synthetic-sensitive' "$output"; then echo 'configuração vazou na equivalência por stdin' >&2; exit 1; fi

echo 'production resolved inventory: ok'
