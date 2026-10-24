#!/usr/bin/env bash
# Inventário remoto somente-leitura anterior à aposentadoria InfinitePay.
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/opt/markina-gallery"
readonly EXPECTED_HOST="clearbudget-vnic"
readonly PROJECT_NAME="markina-gallery"
readonly COMPOSE_FILE="docker/docker-compose.yml"
readonly COMPOSE_FILE_LABEL="/opt/markina-gallery/docker/docker-compose.yml,/var/lib/markina-gallery/deploy-state/branding.compose.yml,/opt/markina-gallery/docker/docker-compose.raw-development.yml,/opt/markina-gallery/docker/docker-compose.preview-adjustment.yml,/opt/markina-gallery/docker/docker-compose.system-monitor.yml,/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml"
readonly ENV_FILE="docker/.env.homolog"
readonly STATE_DIR="/var/lib/markina-gallery/deploy-state"
readonly BACKUP_DIR="/var/lib/markina-gallery/backups"
readonly ACTIVE_IMAGES_OVERLAY="/var/lib/markina-gallery/deploy-state/payments0086-active-images.compose.json"
readonly ACTIVE_IMAGES_OVERLAY_SHA256="899df26fa54fbdd369d66aa0f446340853591e9163a27ae5963564961f0d8e60"
readonly PUBLIC_URL="https://markina.pickyourpic.com.br"
readonly HOST_REFERENCES_SCRIPT_BLOB_SHA="acd38067afccc3476a80f8804b8cda8f5a09b27d"
readonly COMPOSE_EXTRA_FILES=(
  "/var/lib/markina-gallery/deploy-state/branding.compose.yml"
  "docker/docker-compose.raw-development.yml"
  "docker/docker-compose.preview-adjustment.yml"
  "docker/docker-compose.system-monitor.yml"
  "/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml"
)

fail() { echo "deploy-prod-infinitepay-retirement: $*" >&2; exit 1; }
MODE=""
TARGET_SHA=""
APPROVAL_FINGERPRINT=""
EXPECTED_REPOSITORY="${MARKINA_EXPECTED_REPOSITORY:-}"
EXPECTED_URL="${MARKINA_PUBLIC_BASE_URL:-$PUBLIC_URL}"
TARGET_COMPOSE=""
CHECKOUT_SHA=""
ACTIVE_SHA=""
INVENTORY_JSON=""
MIGRATION_STARTED=false
API_STOPPED=false
WORKER_STOPPED=false
ROLLBACK_API_CONTAINER=""
ROLLBACK_WORKER_CONTAINER=""
COMPOSE_INCLUDE_ACTIVE_IMAGES_OVERLAY=false
ALLOW_LEGACY_WORKER_INTERRUPTION=false

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode) MODE="${2:-}"; shift 2 ;;
      --sha) TARGET_SHA="${2:-}"; shift 2 ;;
      --approval-fingerprint) APPROVAL_FINGERPRINT="${2:-}"; shift 2 ;;
      --allow-legacy-worker-interruption) ALLOW_LEGACY_WORKER_INTERRUPTION=true; shift ;;
      *) fail "argumento não permitido: $1" ;;
    esac
  done
  [[ "$MODE" == inventory || "$MODE" == release ]] || fail "modo deve ser inventory ou release"
  [[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA alvo inválido"
  if [[ "$MODE" == release ]]; then
    [[ "$APPROVAL_FINGERPRINT" =~ ^[0-9a-f]{64}$ ]] || fail "fingerprint obrigatório"
  fi
}

compose_command() {
  local files=(--env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE") file
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do files+=(-f "$file"); done
  if [[ "$COMPOSE_INCLUDE_ACTIVE_IMAGES_OVERLAY" == true ]]; then
    files+=(-f "$ACTIVE_IMAGES_OVERLAY")
  fi
  APP_VERSION="$ACTIVE_SHA" docker compose "${files[@]}" --profile facial --profile preview-adjustment "$@"
}

compose() { compose_command "$@" </dev/null; }

compose_with_stdin() { compose_command "$@"; }

compose_label_for_service() {
  local service="$1"
  if [[ "$COMPOSE_INCLUDE_ACTIVE_IMAGES_OVERLAY" == true && ( "$service" == api || "$service" == web ) ]]; then
    printf '%s,%s\n' "$COMPOSE_FILE_LABEL" "$ACTIVE_IMAGES_OVERLAY"
  else
    printf '%s\n' "$COMPOSE_FILE_LABEL"
  fi
}

wait_for_healthy_container() {
  local id="$1" status attempt
  for ((attempt=0; attempt<60; attempt++)); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id")" \
      || return 1
    [[ "$status" == healthy ]] && return 0
    [[ "$status" == unhealthy || "$status" == exited || "$status" == dead ]] && return 1
    sleep 2
  done
  return 1
}

database_revision() {
  local output revisions
  output="$(compose exec -T -e PYTHONDONTWRITEBYTECODE=1 api python -B -m alembic current 2>/dev/null)" \
    || fail "consulta somente-leitura de schema falhou"
  revisions="$(sed -nE 's/^([0-9]{8}_[0-9]{4})( .*)?$/\1/p' <<<"$output")"
  [[ "$(wc -l <<<"$revisions" | tr -d ' ')" == 1 && "$revisions" =~ ^[0-9]{8}_[0-9]{4}$ ]] \
    || fail "schema sem revisão única"
  printf '%s\n' "$revisions"
}

active_sha() {
  local ids value
  ids="$(compose ps -q api)"
  [[ "$(wc -l <<<"$ids" | tr -d ' ')" == 1 ]] || fail "API Markina ausente ou duplicada"
  value="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$ids" \
    | sed -nE 's/^APP_VERSION=([0-9a-f]{40})$/\1/p')"
  [[ "$(wc -l <<<"$value" | tr -d ' ')" == 1 ]] || fail "APP_VERSION ativa ausente ou ambígua"
  printf '%s\n' "$value"
}

resolved_hashes() {
  compose config --format json 2>/dev/null \
    | docker compose -p "$PROJECT_NAME" -f - --profile facial --profile preview-adjustment \
      config --no-interpolate --hash api,web,worker 2>/dev/null \
    || fail "não foi possível calcular hash Compose sem exibir configuração"
}

compose_binding_metadata() {
  # `config` resolves env_file contents by default and removes their source
  # paths. Read only the interpolation value for this path, then keep the raw
  # Compose model on the pipe and emit metadata only.
  local binding_path_override
  binding_path_override="$(compose config --environment 2>/dev/null \
    | sed -nE 's/^INFINITEPAY_BINDINGS_ENV_FILE=(.*)$/\1/p' | tail -n1)" \
    || fail "não foi possível resolver o caminho do binding"
  compose config --no-env-resolution --no-interpolate --no-path-resolution --no-normalize --format json 2>/dev/null \
    | MARKINA_RETIREMENT_BINDING_PATH_OVERRIDE="$binding_path_override" \
      MARKINA_RETIREMENT_COMPOSE_DIR="$PROJECT_ROOT/docker" python3 -c '
import json, os, pathlib, stat, sys
data=json.load(sys.stdin)
matches=[]
compose_dir=os.environ["MARKINA_RETIREMENT_COMPOSE_DIR"]
override=os.environ.get("MARKINA_RETIREMENT_BINDING_PATH_OVERRIDE", "")
default_expression="${INFINITEPAY_BINDINGS_ENV_FILE:-.env.infinitepay-bindings}"
required_expression="${INFINITEPAY_BINDINGS_ENV_FILE}"
def resolve_path(value):
    if value == default_expression:
        value=override or ".env.infinitepay-bindings"
    elif value == required_expression:
        value=override
    elif "$" in value:
        raise SystemExit("interpolação de caminho de binding não suportada")
    if not value or "$" in value or "\n" in value or "\r" in value:
        raise SystemExit("caminho de binding inválido")
    return os.path.abspath(value if os.path.isabs(value) else os.path.join(compose_dir, value))
for service, config in data.get("services", {}).items():
    for item in config.get("env_file", []):
        original=item if isinstance(item, str) else item.get("path", "")
        if "infinitepay" not in pathlib.Path(original).name.lower():
            continue
        resolved=resolve_path(original)
        if "infinitepay" in pathlib.Path(resolved).name.lower():
            matches.append((service, resolved, original))
if len(matches) != 1:
    raise SystemExit("binding ausente ou ambíguo")
service, resolved, original=matches[0]
info=os.lstat(resolved)
references=[]
if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
    kind="symlink" if stat.S_ISLNK(info.st_mode) else "not_regular"
else:
    kind="regular_file"
print(json.dumps({"path":resolved,"type":kind,"symlink":stat.S_ISLNK(info.st_mode),
 "mode":format(stat.S_IMODE(info.st_mode),"04o"),"size_bytes":info.st_size,"link_count":info.st_nlink,
 "mtime_ns":info.st_mtime_ns,"inode":info.st_ino,"device":info.st_dev,"uid":info.st_uid,
 "compose_consumers":["markina-gallery/"+service],"original_path":original},separators=(",",":")))
'
}

outside_references() {
  local target="$1" file_refs container_refs container_ids container_id container_data host_references_source host_references_sha raw_url
  raw_url="https://raw.githubusercontent.com/$EXPECTED_REPOSITORY/$TARGET_SHA/scripts/retirement_host_references.py"
  host_references_source="$(curl --location --fail --silent --show-error --proto '=https' --proto-redir '=https' \
    --tlsv1.2 --max-time 20 "$raw_url")" || fail "scanner de referências versionado indisponível"
  host_references_sha="$(printf '%s\n' "$host_references_source" | git hash-object --stdin)" \
    || fail "não foi possível verificar o scanner de referências"
  [[ "$host_references_sha" == "$HOST_REFERENCES_SCRIPT_BLOB_SHA" ]] \
    || fail "scanner de referências diverge do blob revisado"
  if [[ "$EUID" -eq 0 ]]; then
    file_refs="$(python3 -c "$host_references_source" --target "$target" \
      --roots /opt /home /srv /etc /root /mnt /var/lib/markina-gallery/deploy-state)" || fail "varredura de arquivos de configuração incompleta"
  else
    file_refs="$(sudo -n python3 -c "$host_references_source" --target "$target" \
      --roots /opt /home /srv /etc /root /mnt /var/lib/markina-gallery/deploy-state)" || fail "varredura privilegiada de arquivos de configuração indisponível ou incompleta"
  fi
  container_ids="$(docker ps -aq)" || fail "inventário de containers Docker indisponível"
  if [[ -n "$container_ids" ]]; then
    container_data="$(while IFS= read -r container_id; do
      [[ -n "$container_id" ]] || continue
      docker inspect --format '{{json .Mounts}}|{{.Name}}|{{index .Config.Labels "com.docker.compose.project"}}' "$container_id" \
        || exit 1
    done <<<"$container_ids")" || fail "inspeção de mounts Docker incompleta"
    container_refs="$(printf '%s\n' "$container_data" | python3 -c "$host_references_source" \
      --target "$target" --container-inspect)" || fail "varredura de mounts Docker incompleta"
  else
    container_refs=""
  fi
  printf '%s\n%s\n' "$file_refs" "$container_refs" | sed '/^$/d' | sort -u
}

financial_evidence() {
  local source
  source="$(git show "$TARGET_SHA:scripts/retirement_financial_evidence.py")" \
    || fail "coletor de evidência financeira ausente no SHA aprovado"
  printf '%s\n' "$source" | compose_with_stdin run --rm --no-deps -T api python -
}

pix_evidence() {
  local source
  source="$(git show "$TARGET_SHA:scripts/retirement_pix_evidence.py")" \
    || fail "verificador do PIX próprio ausente no SHA aprovado"
  printf '%s\n' "$source" | compose_with_stdin run --rm --no-deps -T api python -
}

create_backup() {
  local timestamp stem partial archive manifest free_bytes database_bytes checksum directory_mode
  [[ -d "$BACKUP_DIR" && ! -L "$BACKUP_DIR" && -w "$BACKUP_DIR" ]] || fail "diretório exclusivo de backup indisponível"
  directory_mode="$(stat -c '%a' "$BACKUP_DIR")"
  [[ "$directory_mode" =~ ^[0-7]{3,4}$ ]] || fail "metadados do diretório de backup inválidos"
  (( (8#$directory_mode & 0022) == 0 )) || fail "diretório de backup gravável por grupo/outros"
  database_bytes="$(compose exec -T db sh -ceu 'psql -X -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT pg_database_size(current_database())"')" \
    || fail "não mediu o tamanho do banco da Markina"
  [[ "$database_bytes" =~ ^[0-9]+$ && "$database_bytes" -gt 0 ]] || fail "tamanho do banco inválido"
  free_bytes="$(df -Pk "$BACKUP_DIR" | awk 'NR == 2 {print $4 * 1024}')"
  [[ "$free_bytes" =~ ^[0-9]+$ ]] || fail "espaço livre do backup inválido"
  (( free_bytes > database_bytes * 2 )) || fail "espaço livre insuficiente para dump e margem de recuperação"
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  stem="infinitepay-retirement-${timestamp}-${TARGET_SHA:0:12}"
  partial="$BACKUP_DIR/.${stem}.partial"
  archive="$BACKUP_DIR/${stem}.dump"
  manifest="$BACKUP_DIR/${stem}.manifest"
  [[ ! -e "$partial" && ! -e "$archive" && ! -e "$manifest" ]] || fail "nome de backup já existe"
  compose exec -T db sh -ceu 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$partial" \
    || { rm -f -- "$partial"; fail "pg_dump falhou"; }
  chmod 0600 "$partial"
  [[ -s "$partial" ]] || { rm -f -- "$partial"; fail "pg_dump vazio"; }
  compose_with_stdin exec -T db pg_restore --list < "$partial" >/dev/null 2>&1 \
    || { rm -f -- "$partial"; fail "arquivo de backup não passou pg_restore --list"; }
  checksum="$(sha256sum "$partial" | awk '{print $1}')"
  [[ "$checksum" =~ ^[0-9a-f]{64}$ ]] || { rm -f -- "$partial"; fail "checksum do backup inválido"; }
  mv -- "$partial" "$archive"
  chmod 0600 "$archive"
  printf 'format=pg_dump_custom\nschema=20261021_0086\ntarget_sha=%s\nsha256=%s\nbytes=%s\ncreated_at_utc=%s\n' \
    "$TARGET_SHA" "$checksum" "$(stat -c '%s' "$archive")" "$timestamp" > "$manifest"
  chmod 0600 "$manifest"
  sync -f "$archive"
  sync -f "$manifest"
  printf 'backup_arquivo=%s\nbackup_sha256=%s\nbackup_bytes=%s\n' "$archive" "$checksum" "$(stat -c '%s' "$archive")"
}

remove_binding_after_health() {
  local inventory_json="$1" binding_path compose_consumers host_refs target_refs services_json health_ok target_compose
  [[ "$(database_revision)" == "20261022_0087" ]] || fail "schema final não foi confirmado antes da limpeza"
  for service in api web worker; do
    local id state
    id="$(compose ps -q "$service")"
    [[ -n "$id" && "$(wc -l <<<"$id" | tr -d ' ')" == 1 ]] || fail "$service ausente/duplicado antes da limpeza"
    state="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id")"
    [[ "$state" == healthy ]] || fail "$service não está saudável antes da limpeza"
  done
  binding_path="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["binding"]["path"])' <<<"$inventory_json")"
  [[ "$binding_path" != *$'\n'* && "$binding_path" != *$'\r'* ]] || fail "caminho binding inválido"
  compose_consumers="$(compose config --format json 2>/dev/null | python3 -c '
import json,os,pathlib,sys
target=sys.argv[1]; data=json.load(sys.stdin); found=[]
for service, config in data.get("services",{}).items():
    for item in config.get("env_file",[]):
        value=item if isinstance(item,str) else item.get("path","")
        path=os.path.abspath(value if os.path.isabs(value) else os.path.join("/opt/markina-gallery/docker",value))
        if path==target: found.append("markina-gallery/"+service)
print(json.dumps(sorted(set(found)),separators=(",",":")))
' "$binding_path")" || fail "não confirmou consumers Compose"
  host_refs="$(outside_references "$binding_path")"
  target_compose="$(git show "$TARGET_SHA:$COMPOSE_FILE")" || fail "Compose alvo indisponível após release"
  target_refs="[]"
  if grep -Fq -- "$binding_path" <<<"$target_compose" || grep -q 'INFINITEPAY_BINDINGS_ENV_FILE' <<<"$target_compose"; then
    target_refs="[\"$COMPOSE_FILE\"]"
  fi
  services_json="$(services_health | python3 -c 'import json,sys; d={}; [d.update([line.rstrip("\n").split("=",1)]) for line in sys.stdin if "=" in line]; print(json.dumps(d,separators=(",",":")))')"
  health_ok="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print("true" if all(d.get(x)=="healthy" for x in ("api","web","worker")) else "false")' "$services_json")"
  [[ "$health_ok" == true ]] || fail "API/web/worker não estão saudáveis no inventário final"
  python3 scripts/retirement_binding_removal.py --runtime-healthy \
    --compose-consumers-json "$compose_consumers" \
    --host-references-json "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1].splitlines() if sys.argv[1] else [],separators=(",",":"))' "$host_refs")" \
    --target-references-json "$target_refs" <<<"$inventory_json" || fail "binding mudou, compartilhado ou ainda referenciado"
}

services_health() {
  local services service id health active_hash expected_hash hashes
  services="$(compose config --services 2>/dev/null)" || fail "serviços Compose indisponíveis"
  hashes="$(resolved_hashes)"
  while IFS= read -r service; do
    [[ -n "$service" ]] || continue
    id="$(compose ps -q "$service")"
    [[ -n "$id" ]] || continue
    [[ "$(wc -l <<<"$id" | tr -d ' ')" == 1 ]] || fail "container duplicado: $service"
    [[ "$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$id")" == "$PROJECT_NAME" ]] \
      || fail "container fora do projeto: $service"
    if [[ "$service" == api || "$service" == web || "$service" == nginx ]]; then
      [[ "$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' "$id")" == "/opt/markina-gallery/docker" \
        && "$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' "$id")" == "$(compose_label_for_service "$service")" ]] \
        || fail "origem Compose de $service diverge"
    fi
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id")"
    if [[ "$service" == api || "$service" == web || "$service" == worker ]]; then
      expected_hash="$(awk -v name="$service" '$1 == name {sub(/^sha256:/,"",$2); print $2}' <<<"$hashes")"
      active_hash="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.config-hash" }}' "$id")"
      [[ "$active_hash" == "$expected_hash" ]] || fail "Compose ativo diverge para $service"
    fi
    printf '%s=%s\n' "$service" "$health"
  done <<<"$services"
}

inventory() {
  local checkout main active schema hashes api_hash web_hash worker_hash nginx_id ports binding path refs health_json target_refs origin git_dir fetched_sha
  COMPOSE_INCLUDE_ACTIVE_IMAGES_OVERLAY=true
  [[ "$(hostname)" == "$EXPECTED_HOST" ]] || fail "host diverge do alvo registrado"
  [[ "$(pwd -P)" == "$PROJECT_ROOT" && "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] \
    || fail "checkout Markina ausente"
  [[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" && -d "$STATE_DIR" ]] || fail "Compose, env ou estado ausente"
  for file in "${COMPOSE_EXTRA_FILES[@]}"; do [[ -f "$file" ]] || fail "Compose auxiliar ausente"; done
  [[ -f "$ACTIVE_IMAGES_OVERLAY" && ! -L "$ACTIVE_IMAGES_OVERLAY" ]] || fail "overlay de imagens ativas ausente ou inválido"
  [[ "$(sha256sum "$ACTIVE_IMAGES_OVERLAY" | awk '{print $1}')" == "$ACTIVE_IMAGES_OVERLAY_SHA256" ]] \
    || fail "overlay de imagens ativas diverge da publicação 0086 registrada"
  [[ -n "$EXPECTED_REPOSITORY" ]] || fail "repositório esperado ausente"
  [[ -z "$(git status --porcelain)" ]] || fail "checkout contém alterações locais"
  case "$(git remote get-url origin)" in
    "https://github.com/$EXPECTED_REPOSITORY"|"https://github.com/$EXPECTED_REPOSITORY.git"|"git@github.com:$EXPECTED_REPOSITORY.git") ;;
    *) fail "origin diverge do repositório esperado" ;;
  esac
  checkout="$(git rev-parse HEAD)"
  CHECKOUT_SHA="$checkout"
  origin="$(git remote get-url origin)"
  main="$(git ls-remote "$origin" refs/heads/main | awk 'NR == 1 {print $1}')"
  [[ "$main" == "$TARGET_SHA" ]] || fail "alvo não é o HEAD atual de main"
  git_dir="$(mktemp -d "${TMPDIR:-/tmp}/markina-retirement-preflight.XXXXXX")" || fail "não criou banco Git temporário"
  trap 'rm -rf -- "$git_dir"' RETURN
  git init --bare --quiet "$git_dir" || fail "banco Git temporário inválido"
  git -C "$git_dir" remote add origin "$origin" || fail "origin temporário inválido"
  git -C "$git_dir" config extensions.partialClone origin || fail "partial clone indisponível"
  git -C "$git_dir" config remote.origin.promisor true || fail "promisor Git indisponível"
  git -C "$git_dir" config remote.origin.partialclonefilter blob:none || fail "filtro Git indisponível"
  git -C "$git_dir" fetch --quiet --no-tags --filter=blob:none origin refs/heads/main || fail "fetch temporário da main falhou"
  fetched_sha="$(git -C "$git_dir" rev-parse 'FETCH_HEAD^{commit}')" || fail "SHA temporário ausente"
  [[ "$fetched_sha" == "$TARGET_SHA" ]] || fail "main mudou após leitura"
  git -C "$git_dir" merge-base --is-ancestor "$checkout" "$TARGET_SHA" || fail "alvo não descende do checkout"
  TARGET_COMPOSE="$(git -C "$git_dir" show "$TARGET_SHA:$COMPOSE_FILE")" || fail "Compose do alvo ausente"
  rm -rf -- "$git_dir"
  trap - RETURN
  ACTIVE_SHA="$(active_sha)"
  [[ "$checkout" == "$ACTIVE_SHA" ]] || fail "checkout não corresponde à versão ativa"
  schema="$(database_revision)"
  [[ "$schema" == "20261021_0086" ]] || fail "schema diverge da revisão anterior aprovada"
  hashes="$(resolved_hashes)"
  api_hash="$(awk '$1 == "api" {sub(/^sha256:/,"",$2); print $2}' <<<"$hashes")"
  web_hash="$(awk '$1 == "web" {sub(/^sha256:/,"",$2); print $2}' <<<"$hashes")"
  worker_hash="$(awk '$1 == "worker" {sub(/^sha256:/,"",$2); print $2}' <<<"$hashes")"
  [[ "$api_hash" =~ ^[0-9a-f]{64}$ && "$web_hash" =~ ^[0-9a-f]{64}$ && "$worker_hash" =~ ^[0-9a-f]{64}$ ]] || fail "hash Compose inválido"
  nginx_id="$(compose ps -q nginx)"
  [[ -n "$nginx_id" ]] || fail "nginx Markina ausente"
  ports="$(docker inspect --format '{{json .NetworkSettings.Ports}}' "$nginx_id")"
  [[ "$ports" == '{"80/tcp":[{"HostIp":"127.0.0.1","HostPort":"8080"}]}' ]] || fail "bind nginx diverge"
  binding="$(compose_binding_metadata)" || fail "binding ausente ou metadados indisponíveis"
  path="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["path"])' <<<"$binding")"
  refs="$(outside_references "$path")"
  target_refs=""
  if grep -Fq -- "$path" <<<"$TARGET_COMPOSE" || grep -q 'INFINITEPAY_BINDINGS_ENV_FILE' <<<"$TARGET_COMPOSE"; then
    target_refs="$COMPOSE_FILE"
  fi
  health_json="$(services_health | python3 -c 'import json,sys; d={}; [d.update([line.rstrip("\n").split("=",1)]) for line in sys.stdin if "=" in line]; print(json.dumps(d,separators=(",",":")))')"
  for endpoint in /healthz /api/health /; do
    curl -fsS --max-time 10 "$EXPECTED_URL$endpoint" -o /dev/null || fail "smoke HTTPS falhou"
  done
  local binding_json
  binding_json="$(python3 -c 'import json,sys; d=json.load(sys.stdin); d.pop("original_path",None); d["host_references"]=sys.argv[1].splitlines() if sys.argv[1] else []; d["target_references"]=sys.argv[2].splitlines() if sys.argv[2] else []; print(json.dumps(d,separators=(",",":")))' "$refs" "$target_refs" <<<"$binding")"
  INVENTORY_JSON="$(python3 - "$TARGET_SHA" "$main" "$checkout" "$ACTIVE_SHA" "$schema" "$EXPECTED_URL" \
      "$api_hash" "$web_hash" "$worker_hash" "$ports" "$health_json" "$binding_json" <<'PY'
import json,sys
target,main,checkout,active,schema,url,api,web,worker,ports,health,binding=sys.argv[1:]
inventory={"host":"clearbudget-vnic","project":"markina-gallery","root":"/opt/markina-gallery",
 "target_sha":target,"main_sha":main,"checkout_sha":checkout,"active_sha":active,
 "database_revision":schema,"public_url":url,"nginx_bind":"127.0.0.1:8080->80/tcp",
 "services":json.loads(health),"compose_hashes":{"api":api,"web":web,"worker":worker},
 "binding":json.loads(binding),"https_health":{"healthz":True,"api_health":True,"web":True}}
print(json.dumps(inventory,sort_keys=True,separators=(",",":")))
PY
  )"
  [[ -n "$INVENTORY_JSON" ]] || fail "não foi possível serializar o inventário sanitizado"
  COMPOSE_INCLUDE_ACTIVE_IMAGES_OVERLAY=false
  printf 'retirement_inventory_json=%s\n' "$INVENTORY_JSON"
  echo "nenhuma mutação foi executada"
}

verify_restore_receipt() {
  local receipt="$STATE_DIR/infinitepay-retirement-restore-test.json"
  [[ -f "$receipt" && ! -L "$receipt" && "$(stat -c '%a' "$receipt")" == "600" \
    && "$(stat -c '%u' "$receipt")" == "0" ]] \
    || fail "falta recibo 0600 de restauração previamente testada em ambiente isolado"
  sudo -n python3 - "$receipt" "$BACKUP_DIR" <<'PY' || fail "recibo de restauração inválido ou backup testado divergente"
import datetime,hashlib,json,os,pathlib,stat,sys
receipt=pathlib.Path(sys.argv[1]); backup_root=pathlib.Path(sys.argv[2]).resolve()
fd=os.open(receipt, os.O_RDONLY | getattr(os,"O_NOFOLLOW",0))
with os.fdopen(fd,"r",encoding="utf-8") as stream:
    info=os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or stat.S_IMODE(info.st_mode)!=0o600:
        raise SystemExit(1)
    data=json.load(stream)
required={"result","database_revision","backup_file","backup_sha256","tested_at","isolated"}
if set(data)!=required or data["result"]!="passed" or data["database_revision"]!="20261021_0086" or data["isolated"] is not True:
    raise SystemExit(1)
backup=pathlib.Path(data["backup_file"])
if not backup.is_absolute() or backup.is_symlink() or backup.resolve().parent!=backup_root or not backup.is_file():
    raise SystemExit(1)
if not isinstance(data["backup_sha256"],str) or len(data["backup_sha256"])!=64 or any(c not in "0123456789abcdef" for c in data["backup_sha256"]):
    raise SystemExit(1)
digest=hashlib.sha256()
with backup.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024*1024), b""):
        digest.update(chunk)
actual=digest.hexdigest()
if actual!=data["backup_sha256"]:
    raise SystemExit(1)
if not isinstance(data["tested_at"],str) or not data["tested_at"].endswith("Z"):
    raise SystemExit(1)
try:
    parsed=datetime.datetime.fromisoformat(data["tested_at"].replace("Z","+00:00"))
except ValueError:
    raise SystemExit(1)
if parsed.utcoffset()!=datetime.timedelta(0):
    raise SystemExit(1)
PY
}

acquire_retirement_lock() {
  [[ -f "$STATE_DIR/production-release.lock" && ! -L "$STATE_DIR/production-release.lock" ]] \
    || fail "lock compartilhado de produção ausente"
  exec 9<"$STATE_DIR/production-release.lock"
  flock -n 9 || fail "outro release está em andamento"
  for marker in app-in-flight.sha app-rollback-in-flight.sha web-in-flight.sha web-pending.identity; do
    [[ ! -e "$STATE_DIR/$marker" ]] || fail "operação de release pendente: $marker"
  done
}

interrupt_approved_legacy_worker() {
  local id="$1" image source_hash pending idle state attempt
  [[ "$ALLOW_LEGACY_WORKER_INTERRUPTION" == true && "$API_STOPPED" == true ]] \
    || fail "interrupção do worker legado não autorizada ou API ainda ativa"
  image="$(docker inspect --format '{{.Image}}' "$id")"
  [[ "$image" == sha256:25067618cf99f3b662f9096fc2f7aa88bcf272da5b2ea62dd91d9de9bd8d3b21 ]] \
    || fail "imagem do worker legado diverge do inventário"
  source_hash="$(docker exec "$id" python -B -c 'import hashlib,pathlib; print(hashlib.sha256(pathlib.Path("/app/app/worker.py").read_bytes()).hexdigest())')"
  [[ "$source_hash" == 2731fb50695ea6cac2df54b85994bf2f4162dbf5e811a3adc97f7b4668dbfc8a ]] \
    || fail "source do worker legado diverge do inventário"
  pending="$(compose_with_stdin exec -T db sh -ceu 'exec psql -X -q -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT
 (SELECT count(*) FROM media_job WHERE status IN ('queued','processing')) +
 (SELECT count(*) FROM whatsapp_delivery WHERE status IN ('queued','processing','unknown')) +
 (SELECT count(*) FROM email_delivery WHERE status IN ('queued','processing')) +
 (SELECT count(*) FROM notification_delivery WHERE status IN ('queued','processing')) +
 (SELECT count(*) FROM gallery_lifecycle_operation WHERE status NOT IN ('completed','failed')) +
 (SELECT count(*) FROM asset_file_cleanup WHERE status IN ('pending','processing'));
ROLLBACK;
SQL
  )" || fail "não confirmou filas antes da interrupção do legado"
  [[ "$pending" == 0 ]] || fail "há trabalho elegível/ativo; worker legado não será interrompido"
  idle="$(docker exec "$id" python -B -c 'import pathlib; print(pathlib.Path("/proc/1/wchan").read_text().strip())')"
  [[ "$idle" == hrtimer_nanosleep ]] || fail "worker legado não está na espera ociosa inventariada"
  docker kill --signal=SIGINT "$id" >/dev/null || fail "SIGINT do worker legado falhou"
  WORKER_STOPPED=true
  for ((attempt=0; attempt<20; attempt++)); do
    state="$(docker inspect --format '{{.State.Status}}:{{.State.ExitCode}}' "$id")"
    if [[ "$state" == exited:130 ]]; then
      echo "worker_legado=interrompido_com_autorizacao exit_code=130 filas_ativas=0"
      return 0
    fi
    [[ "$state" == running:* || "$state" == stopping:* ]] || fail "saída inesperada do worker legado: $state"
    sleep 0.5
  done
  fail "worker legado não concluiu SIGINT; migration não será aplicada"
}

restore_pre_migration_runtime() {
  local status="$?"
  if [[ "$status" -ne 0 && "$MIGRATION_STARTED" == false ]]; then
    echo "falha pré-migration; restaurando checkout e runtime Markina anteriores" >&2
    if [[ "$(git rev-parse HEAD 2>/dev/null || true)" != "$CHECKOUT_SHA" ]] \
        && ! git switch --detach "$CHECKOUT_SHA" >/dev/null 2>&1; then
      echo "ATENÇÃO: checkout anterior não foi restaurado automaticamente" >&2
    elif [[ "$API_STOPPED" == true || "$WORKER_STOPPED" == true ]]; then
      ACTIVE_SHA="$CHECKOUT_SHA"
      if [[ -n "$ROLLBACK_API_CONTAINER" && -n "$ROLLBACK_WORKER_CONTAINER" ]]; then
        if docker start "$ROLLBACK_API_CONTAINER" "$ROLLBACK_WORKER_CONTAINER" >/dev/null 2>&1 \
          && wait_for_healthy_container "$ROLLBACK_API_CONTAINER" \
          && wait_for_healthy_container "$ROLLBACK_WORKER_CONTAINER"; then
          echo "runtime anterior reiniciado e saudável" >&2
        else
          echo "ATENÇÃO: recuperação pré-migration dos containers anteriores requer intervenção" >&2
        fi
      else
        echo "ATENÇÃO: IDs dos containers anteriores incompletos; recuperação requer intervenção" >&2
      fi
    fi
  elif [[ "$status" -ne 0 && "$MIGRATION_STARTED" == true ]]; then
    echo "falha após início da migration; não executar downgrade; recuperar com backup e versão anterior" >&2
  fi
  return "$status"
}

release() {
  local inventory_output actual_fp pre_evidence post_evidence pre_pix post_pix old_api old_web old_worker
  local tag_api tag_web tag_worker migrated target_api target_web target_worker
  inventory_output="$(inventory)"
  INVENTORY_JSON="$(sed -n 's/^retirement_inventory_json=//p' <<<"$inventory_output" | tail -n1)"
  [[ -n "$INVENTORY_JSON" ]] || fail "inventário de release ausente"
  actual_fp="$(printf '%s' "$INVENTORY_JSON" | python3 -c 'import hashlib,json,sys; d=json.load(sys.stdin); raw=json.dumps(d,sort_keys=True,separators=(",",":" )).encode(); print(hashlib.sha256(raw).hexdigest())')"
  [[ "$actual_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "inventário mudou desde a aprovação; nada foi alterado"
  acquire_retirement_lock
  inventory_output="$(inventory)"
  INVENTORY_JSON="$(sed -n 's/^retirement_inventory_json=//p' <<<"$inventory_output" | tail -n1)"
  actual_fp="$(printf '%s' "$INVENTORY_JSON" | python3 -c 'import hashlib,json,sys; d=json.load(sys.stdin); raw=json.dumps(d,sort_keys=True,separators=(",",":" )).encode(); print(hashlib.sha256(raw).hexdigest())')"
  [[ "$actual_fp" == "$APPROVAL_FINGERPRINT" ]] || fail "inventário mudou durante a aprovação; nada foi alterado"
  CHECKOUT_SHA="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["checkout_sha"])' <<<"$INVENTORY_JSON")"
  [[ "$CHECKOUT_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA anterior ausente no inventário aprovado"
  ACTIVE_SHA="$CHECKOUT_SHA"
  verify_restore_receipt
  trap restore_pre_migration_runtime EXIT
  git fetch --quiet --no-tags origin main || fail "fetch da main aprovada falhou"
  [[ "$(git rev-parse origin/main)" == "$TARGET_SHA" ]] || fail "main mudou antes do release"
  old_api="$(docker inspect --format '{{.Image}}' "$(compose ps -q api)")"
  old_web="$(docker inspect --format '{{.Image}}' "$(compose ps -q web)")"
  old_worker="$(docker inspect --format '{{.Image}}' "$(compose ps -q worker)")"
  ROLLBACK_API_CONTAINER="$(compose ps -q api)"
  ROLLBACK_WORKER_CONTAINER="$(compose ps -q worker)"
  [[ "$old_api" =~ ^sha256:[0-9a-f]{64}$ && "$old_web" =~ ^sha256:[0-9a-f]{64}$ \
    && "$old_worker" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || fail "imagens anteriores API/web/worker incompletas"
  tag_api="$PROJECT_NAME-retirement-rollback-api-${old_api#sha256:}"
  tag_web="$PROJECT_NAME-retirement-rollback-web-${old_web#sha256:}"
  tag_worker="$PROJECT_NAME-retirement-rollback-worker-${old_worker#sha256:}"
  docker image tag "$old_api" "$tag_api" || fail "não preservou imagem API anterior"
  docker image tag "$old_web" "$tag_web" || fail "não preservou imagem web anterior"
  docker image tag "$old_worker" "$tag_worker" || fail "não preservou imagem worker anterior"
  git switch --detach "$TARGET_SHA" >/dev/null || fail "não selecionou SHA aprovado"
  ACTIVE_SHA="$TARGET_SHA"
  compose config --quiet || fail "Compose de destino inválido"
  compose build api web worker || fail "build API/web/worker falhou"
  [[ "$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')" == "$TARGET_SHA" ]] \
    || fail "main mudou durante build; nenhum serviço foi parado"
  target_api="$(docker image inspect --format '{{.Id}}' "$PROJECT_NAME-api")" || fail "imagem candidata API ausente"
  target_web="$(docker image inspect --format '{{.Id}}' "$PROJECT_NAME-web")" || fail "imagem candidata web ausente"
  target_worker="$(docker image inspect --format '{{.Id}}' "$PROJECT_NAME-worker")" || fail "imagem candidata worker ausente"
  compose stop api || fail "não foi possível pausar a API antes da migration"
  API_STOPPED=true
  local worker_container worker_exit
  worker_container="$(compose ps -q worker)"
  [[ -n "$worker_container" ]] || fail "worker Markina ausente antes da migration"
  if [[ "$ALLOW_LEGACY_WORKER_INTERRUPTION" == true ]]; then
    interrupt_approved_legacy_worker "$worker_container"
  else
    compose stop --timeout 180 worker || fail "não foi possível pausar o worker antes da migration"
    WORKER_STOPPED=true
    worker_exit="$(docker inspect --format '{{.State.Status}}:{{.State.ExitCode}}' "$worker_container")"
    [[ "$worker_exit" == exited:0 ]] || fail "worker não concluiu parada graciosa; migration não será aplicada"
  fi
  create_backup
  pre_evidence="$(financial_evidence)" || fail "snapshot financeiro pré-migration falhou"
  [[ "$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("confirmed_infinitepay_count",-1))' <<<"$pre_evidence")" == 2 ]] \
    || fail "histórico não contém exatamente duas compras InfinitePay confirmadas; nada será removido"
  pre_pix="$(pix_evidence)" || fail "verificação do PIX próprio falhou antes da migration"
  [[ "$(python3 -c 'import json,sys; d=json.load(sys.stdin); print("ok" if d.get("tenant_count")==1 and d.get("all_tenants_pix_available") is True and d.get("card_available_count")==0 else "no")' <<<"$pre_pix")" == ok ]] \
    || fail "PIX próprio indisponível ou fotógrafo único divergente; migration não será aplicada"
  printf '%s\n' "$TARGET_SHA" > "$STATE_DIR/infinitepay-retirement-in-flight.sha"
  MIGRATION_STARTED=true
  compose run --rm --no-deps api python -B -m alembic upgrade 20261022_0087 \
    || fail "migration de aposentadoria falhou; recuperação manual pelo backup"
  compose up -d --no-deps --force-recreate --wait --wait-timeout 120 api web worker \
    || fail "API/web/worker não ficaram saudáveis após migration"
  API_STOPPED=false
  WORKER_STOPPED=false
  [[ "$(docker inspect --format '{{.Image}}' "$(compose ps -q api)")" == "$target_api" \
      && "$(docker inspect --format '{{.Image}}' "$(compose ps -q web)")" == "$target_web" \
      && "$(docker inspect --format '{{.Image}}' "$(compose ps -q worker)")" == "$target_worker" ]] \
    || fail "runtime API/web/worker não está usando as imagens construídas para o SHA aprovado"
  migrated="$(database_revision)"
  [[ "$migrated" == "20261022_0087" ]] || fail "revisão final diverge de 20261022_0087"
  for endpoint in /healthz /api/health /; do
    curl -fsS --retry 5 --retry-delay 2 --retry-max-time 40 --max-time 5 "$EXPECTED_URL$endpoint" -o /dev/null \
      || fail "smoke HTTPS pós-release falhou"
  done
  post_evidence="$(financial_evidence)" || fail "snapshot financeiro pós-migration falhou"
  [[ "$pre_evidence" == "$post_evidence" ]] || fail "contagens/digests financeiros divergiram; release inconclusivo"
  post_pix="$(pix_evidence)" || fail "verificação do PIX próprio falhou após a migration"
  [[ "$pre_pix" == "$post_pix" ]] || fail "disponibilidade agregada do PIX divergiu; release inconclusivo"
  remove_binding_after_health "$INVENTORY_JSON" || fail "binding não pôde ser removido com segurança"
  rm -f -- "$STATE_DIR/infinitepay-retirement-in-flight.sha"
  trap - EXIT
  printf 'release=saudavel sha=%s schema=%s backup_preservado=true historico_financeiro=preservado\n' "$TARGET_SHA" "$migrated"
}

main() {
  parse_arguments "$@"
  [[ "$EXPECTED_URL" == "$PUBLIC_URL" ]] || fail "domínio diverge do alvo"
  if [[ "$MODE" == inventory ]]; then
    inventory
  else
    release
  fi
}

if [[ "${BASH_SOURCE[0]:-$0}" == "$0" ]]; then main "$@"; fi
