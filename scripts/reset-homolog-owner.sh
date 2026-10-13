#!/usr/bin/env bash
# Operação exclusiva da Markina; não modifica checkout, schema ou credenciais.
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT=/opt/markina-gallery
readonly PROJECT_NAME=markina-gallery
readonly STATE_ROOT=/var/lib/markina-gallery/owner-reset
readonly BACKUP_ROOT=/var/lib/markina-gallery/backups
readonly CONFIRMATION_TOKEN=RESET_HOMOLOG_TO_OWNER_AND_DELETE_164_DUMPS_WITHOUT_BACKUP
readonly RESET_CONFIRMATION_TOKEN=RESET_HOMOLOG_TO_OWNER_WITHOUT_BACKUP
readonly APPROVED_DUMP_COUNT=164
readonly APPROVED_DUMP_BYTES=2077111921
COMPOSE_ARGS=(--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml)
WRITER_IDS=()
MODE="" OWNER_EMAIL="" EXPECTED_SHA="" CONFIRMATION="" PAYLOAD_FILE=""

fail() { echo "owner-reset: $*" >&2; exit 1; }
compose() { docker compose "${COMPOSE_ARGS[@]}" "$@" </dev/null; }
check_state_root() {
  local root="${1:-$STATE_ROOT}"
  [[ -d "$root" && ! -L "$root" && "$(realpath "$root")" == "$root" ]] || fail "diretório privado de retomada ausente ou inseguro"
  [[ "$(stat -c %u "$root")" == "$(id -u)" && "$(stat -c %a "$root")" == 700 && -w "$root" && -x "$root" ]] || fail "diretório de retomada sem dono/permissões privados do operador"
}
is_writer() {
  case "$1" in
    api|worker|face-index-worker|face-search-worker|face-maintenance-worker|face-gemma-index-worker|preview-adjustment-worker|raw-development-worker) return 0 ;;
    *) return 1 ;;
  esac
}
classify_service() {
  if is_writer "$1"; then return 0; fi
  case "$1" in nginx|web|db|redis|evolution-api|evolution-db|evolution-redis) return 0 ;;
    *) fail "serviço Markina não classificado; execução recusada" ;;
  esac
}

verify_writer_id() {
  local identity="$1" project service
  [[ "$identity" =~ ^[0-9a-f]{12,64}$ ]] || fail "identificador de contêiner inválido"
  project="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$identity")"
  service="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' "$identity")"
  [[ "$project" == "$PROJECT_NAME" ]] && is_writer "$service" || fail "writer fora da lista Markina"
}

stop_writers() {
  local identity service listed
  for identity in "${WRITER_IDS[@]}"; do verify_writer_id "$identity" || return 1; done
  docker stop "${WRITER_IDS[@]}" >/dev/null || return 1
  for identity in "${WRITER_IDS[@]}"; do
    [[ "$(docker inspect --format '{{.State.Running}}' "$identity")" == false ]] || fail "writer ainda ativo"
  done
  listed="$(docker ps --filter label=com.docker.compose.project=markina-gallery --format '{{.ID}} {{.Label "com.docker.compose.service"}}')" || fail "listagem de writers não pôde ser conferida"
  while read -r identity service; do
    [[ -n "$identity" ]] || continue
    classify_service "$service"
    if is_writer "$service"; then fail "writer ativo fora da pausa conferida"; fi
  done <<< "$listed"
}

restore_writers() {
  local identity status attempt
  for identity in "${WRITER_IDS[@]}"; do verify_writer_id "$identity" || return 1; done
  docker start "${WRITER_IDS[@]}" >/dev/null || return 1
  for identity in "${WRITER_IDS[@]}"; do
    status=unknown
    for attempt in $(seq 1 30); do
      status="$(docker inspect --format '{{with index .State "Health"}}{{.Status}}{{else}}{{.State.Status}}{{end}}' "$identity")" || fail "estado do writer não pôde ser inspecionado"
      [[ "$status" == healthy ]] && break
      sleep 2
    done
    [[ "$status" == healthy ]] || fail "writer não retomou saudável"
  done
  curl --fail --silent --show-error --max-time 15 http://127.0.0.1:8080/api/health >/dev/null
}

evolution_snapshot() {
  local identity row service count=0
  local -a identities rows
  local listed
  listed="$(docker ps -aq --filter label=com.docker.compose.project=markina-gallery)" || fail "lista de containers Evolution não pôde ser inspecionada"
  identities=()
  [[ -z "$listed" ]] || mapfile -t identities <<< "$listed"
  for identity in "${identities[@]}"; do
    row="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}|{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.State.Status}}|{{with index .State "Health"}}{{.Status}}{{else}}none{{end}}' "$identity")" || fail "container do snapshot Evolution não pôde ser inspecionado"
    service="${row%%|*}"
    case "$service" in
      evolution-api|evolution-db|evolution-redis)
        [[ "${row##*|}" == healthy || "${row##*|}" == none ]] || fail "serviço Evolution não está saudável"
        [[ "$(cut -d '|' -f5 <<< "$row")" == running ]] || fail "serviço Evolution não está ativo"
        rows+=("$row"); count=$((count + 1)) ;;
    esac
  done
  [[ "$count" -eq 3 ]] || fail "inventário Evolution ausente ou ambíguo"
  printf '%s\n' "${rows[@]}" | sort
}

run_payload() {
  local requested_mode="$1" payload_confirmation=""
  [[ "$requested_mode" != execute ]] || payload_confirmation="$RESET_CONFIRMATION_TOKEN"
  compose run --rm -T --no-deps --pull never -v "$PAYLOAD_FILE:/tmp/owner-reset.py:ro" \
    -e APP_ENV=homolog -e PYTHONPATH=/app api python /tmp/owner-reset.py --mode "$requested_mode" \
    --owner-email "$OWNER_EMAIL" --confirmation "$payload_confirmation"
}

complete_reset() {
  # Qualquer falha após iniciar execute conserva os writers pausados. Não existe
  # restauração automática de dados nem retomada que esconda um commit parcial.
  run_payload execute || { fail "reset parcial ou recusado; writers mantidos pausados para inspeção/retomada"; return 1; }
  purge_approved_dumps || { fail "reset concluído, mas a exclusão conferida dos dumps falhou; writers mantidos pausados"; return 1; }
  compose exec -T redis redis-cli FLUSHDB >/dev/null || { fail "limpeza de fila pendente; writers mantidos pausados"; return 1; }
  restore_writers || { fail "retomada incompleta; metadados de recuperação preservados"; return 1; }
}

dump_manifest() {
  python3 - "${1:-$BACKUP_ROOT}" <<'PY'
import os, stat, sys
root=sys.argv[1]
if os.path.realpath(root) != root or os.path.islink(root) or not os.path.isdir(root):
    raise SystemExit("diretório fixo de backups ausente ou inseguro")
if not os.access(root, os.W_OK | os.X_OK):
    raise SystemExit("diretório de backups sem permissão para excluir; nenhum reset pode começar")
count=0; total=0
with os.scandir(root) as entries:
    for entry in entries:
        if not entry.name.endswith(".dump"):
            continue
        info=entry.stat(follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            raise SystemExit("item .dump não regular; inventário recusado")
        count += 1; total += info.st_size
print(f"{count} {total}")
PY
}

purge_approved_dumps() {
  local root="${1:-$BACKUP_ROOT}" expected_count="${2:-$APPROVED_DUMP_COUNT}" expected_bytes="${3:-$APPROVED_DUMP_BYTES}"
  local manifest current_count current_bytes after_count after_bytes
  manifest="$(dump_manifest "$root")" || return 1
  read -r current_count current_bytes <<< "$manifest"
  if [[ "$current_count" == 0 && "$current_bytes" == 0 ]]; then
    echo "dumps Markina autorizados já removidos; demais tipos preservados"
    return 0
  fi
  [[ "$current_count" == "$expected_count" && "$current_bytes" == "$expected_bytes" ]] || {
    echo "owner-reset: manifesto dos dumps divergiu do inventário autorizado; nenhum dump removido" >&2
    return 1
  }
  python3 - "$root" "$expected_count" "$expected_bytes" <<'PY'
import os, stat, sys
root=sys.argv[1]; expected_count=int(sys.argv[2]); expected_bytes=int(sys.argv[3])
if os.path.realpath(root) != root or os.path.islink(root) or not os.path.isdir(root):
    raise SystemExit("diretório fixo de backups ausente ou inseguro")
fd=os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
try:
    with os.scandir(fd) as entries:
        files=[]; total=0
        for entry in entries:
            if entry.name.endswith(".dump"):
                info=entry.stat(follow_symlinks=False)
                if not stat.S_ISREG(info.st_mode):
                    raise SystemExit("item .dump não regular; exclusão recusada")
                files.append((entry.name, info.st_dev, info.st_ino, info.st_size)); total += info.st_size
    if len(files) != expected_count or total != expected_bytes:
        raise SystemExit("manifesto dos dumps divergiu; nenhum dump removido")
    for name, device, inode, size in files:
        current=os.stat(name, dir_fd=fd, follow_symlinks=False)
        if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino, current.st_size) != (device, inode, size):
            raise SystemExit("arquivo .dump mudou durante a validação; exclusão interrompida")
    for name, _, _, _ in files:
        os.unlink(name, dir_fd=fd)
finally:
    os.close(fd)
PY
  manifest="$(dump_manifest "$root")" || return 1
  read -r after_count after_bytes <<< "$manifest"
  [[ "$after_count" == 0 && "$after_bytes" == 0 ]] || return 1
  echo "dumps Markina autorizados removidos: $expected_count arquivos, $expected_bytes bytes; demais tipos preservados"
}

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode) MODE="${2:-}"; shift 2 ;;
      --owner-email) OWNER_EMAIL="${2:-}"; shift 2 ;;
      --expected-sha) EXPECTED_SHA="${2:-}"; shift 2 ;;
      --confirmation) CONFIRMATION="${2:-}"; shift 2 ;;
      *) fail "argumento não permitido" ;;
    esac
  done
  [[ "$MODE" == inventory || "$MODE" == execute ]] || fail "modo inválido"
  [[ "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ && -n "$OWNER_EMAIL" ]] || fail "identidade ou SHA ausente"
  [[ "$MODE" != execute || "$CONFIRMATION" == "$CONFIRMATION_TOKEN" ]] || fail "confirmação sem backup inválida"
  [[ "$MODE" != inventory || -z "$CONFIRMATION" ]] || fail "inventário não aceita confirmação de exclusão"
  [[ "$(pwd -P)" == "$PROJECT_ROOT" ]] || fail "execução permitida somente no checkout Markina"
  [[ "$(git rev-parse HEAD)" == "$EXPECTED_SHA" ]] || fail "SHA publicado diverge do inventário"
  [[ -z "$(git status --porcelain)" ]] || fail "checkout remoto alterado"
  [[ "$(git remote get-url origin)" =~ ^(https://github\.com/conradodeita/markina-gallery(\.git)?|git@github\.com:conradodeita/markina-gallery(\.git)?|ssh://git@github\.com/conradodeita/markina-gallery(\.git)?)$ ]] || fail "repositório divergente"

  local api_id raw_mount identity service pending_ids active_ids active_rows evolution_before evolution_after
  mapfile -t api_ids < <(docker ps -aq --filter label=com.docker.compose.project=markina-gallery --filter label=com.docker.compose.service=api)
  [[ "${#api_ids[@]}" -eq 1 ]] || fail "API ausente ou ambígua"
  api_id="${api_ids[0]}"
  raw_mount="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/markina/raw-staging"}}{{.Name}}{{end}}{{end}}' "$api_id")"
  if [[ -n "$raw_mount" ]]; then
    [[ "$raw_mount" == markina-gallery_media-raw-staging && -f docker/docker-compose.raw-development.yml ]] || fail "volume RAW divergente"
    COMPOSE_ARGS+=(-f docker/docker-compose.raw-development.yml)
  fi

  # A configuração contém segredos: somente a política recebe o JSON, nada do
  # documento original é impresso. Compara também com a API publicada real.
  MARKINA_RESET_API_ID="$api_id"; export MARKINA_RESET_API_ID
  compose --profile whatsapp-real config --format json | python3 -c '
import json, os, subprocess, sys
from urllib.parse import urlsplit
cfg=json.load(sys.stdin)
actual=json.loads(subprocess.check_output(["docker","inspect",os.environ["MARKINA_RESET_API_ID"]]))[0]
services=cfg["services"]; api=services["api"]["environment"]
running_env=dict(v.split("=",1) for v in actual["Config"]["Env"] if "=" in v)
def check(ok,label):
    if not ok: raise SystemExit("topologia divergente: "+label)
check(cfg["name"]=="markina-gallery", "projeto")
check(actual["Config"]["Labels"].get("com.docker.compose.project")=="markina-gallery", "API real")
image=services["api"].get("image", "markina-gallery-api")
check(json.loads(subprocess.check_output(["docker","image","inspect",image]))[0]["Id"]==actual["Image"], "imagem API publicada")
check(api["APP_ENV"] in ("staging","homolog","homologation"), "ambiente")
check(api["DATABASE_URL"]==running_env.get("DATABASE_URL"), "banco publicado")
db=urlsplit(api["DATABASE_URL"])
check(db.hostname=="db" and db.path.lstrip("/")==services["db"]["environment"]["POSTGRES_DB"], "banco exclusivo")
check(api.get("PUBLIC_APP_ORIGIN")=="https://markina.pickyourpic.com.br"
      and running_env.get("PUBLIC_APP_ORIGIN")==api["PUBLIC_APP_ORIGIN"], "origem HTTPS")
check(urlsplit(api.get("REDIS_URL", "redis://redis:6379/0")).hostname=="redis", "Redis exclusivo")
check(any(str(p.get("published"))=="8080" and p.get("host_ip")=="127.0.0.1" for p in services["nginx"].get("ports",[])), "porta")
for name in ("db","redis","evolution-db","evolution-redis"):
    check(not services[name].get("ports"), "portas internas")
mounts={m["target"]:m["source"] for m in services["api"]["volumes"]}
actual_mounts={m["Destination"]:m.get("Name") for m in actual["Mounts"]}
expected={"source":"media-source","derivatives":"media-derivatives","history":"media-history",
          "facial-references":"facial-references","branding":"branding-assets"}
if "/var/lib/markina/raw-staging" in actual_mounts: expected["raw-staging"]="media-raw-staging"
for target,source in expected.items():
    path="/var/lib/markina/"+target; volume="markina-gallery_"+source
    check(mounts.get(path)==source and cfg["volumes"][source].get("name")==volume
          and actual_mounts.get(path)==volume, "volume "+target)
print("topologia conferida: Markina/homolog/127.0.0.1:8080/markina.pickyourpic.com.br")
' || fail "topologia recusada antes da operação"

  active_ids=()
  active_rows="$(docker ps --filter label=com.docker.compose.project=markina-gallery --format '{{.ID}} {{.Label "com.docker.compose.service"}}')" || fail "listagem inicial de writers não pôde ser conferida"
  while read -r identity service; do
    [[ -n "$identity" ]] || continue
    classify_service "$service" || return 1
    if is_writer "$service"; then active_ids+=("$identity"); fi
  done <<< "$active_rows"
  evolution_before="$(evolution_snapshot)" || fail "estado Evolution inicial não pôde ser confirmado"
  check_state_root || return 1

  [[ -n "${MARKINA_RESET_SCRIPT_BASE64:-}" && "${MARKINA_RESET_SCRIPT_SHA256:-}" =~ ^[0-9a-f]{64}$ ]] || fail "payload revisado ausente"
  PAYLOAD_FILE="$(mktemp /tmp/markina-owner-reset.XXXXXX.py)"
  trap 'rm -f -- "$PAYLOAD_FILE"' EXIT
  printf '%s' "$MARKINA_RESET_SCRIPT_BASE64" | base64 --decode > "$PAYLOAD_FILE"
  [[ "$(sha256sum "$PAYLOAD_FILE" | cut -d " " -f 1)" == "$MARKINA_RESET_SCRIPT_SHA256" ]] || fail "integridade do payload divergente"
  unset MARKINA_RESET_SCRIPT_BASE64
  run_payload inventory || fail "inventário proprietário recusado"
  local dump_summary
  dump_summary="$(dump_manifest)" || fail "inventário de dumps antigos recusado"
  read -r dump_count dump_bytes <<< "$dump_summary"
  echo "backups Markina: $dump_count arquivos .dump, $dump_bytes bytes; somente esses arquivos estão no escopo de exclusão autorizado"
  [[ "$MODE" == execute ]] || return 0

  check_state_root || return 1
  exec 9>"$STATE_ROOT/operation.lock"
  flock -n 9 || fail "outra manutenção proprietária está em andamento"
  local state_file="$STATE_ROOT/pending.json"
  export MARKINA_RESET_EXPECTED_SHA="$EXPECTED_SHA" MARKINA_RESET_OWNER_EMAIL="$OWNER_EMAIL"
  if [[ -f "$state_file" ]]; then
    [[ ! -L "$state_file" ]] || fail "estado de retomada inseguro"
    pending_ids="$(python3 -c '
import json,os,sys
s=json.load(open(sys.argv[1]))
if s["sha"]!=os.environ["MARKINA_RESET_EXPECTED_SHA"] or s["owner"]!=os.environ["MARKINA_RESET_OWNER_EMAIL"]:
    raise SystemExit("estado pendente de outra operação")
print(" ".join(s["writers"]))
' "$state_file")" || fail "retomada incompatível"
    read -r -a WRITER_IDS <<< "$pending_ids"
    for identity in "${active_ids[@]}"; do [[ " $pending_ids " == *" $identity "* ]] || fail "novo writer fora da operação pendente"; done
  else
    WRITER_IDS=("${active_ids[@]}")
    [[ "${#WRITER_IDS[@]}" -gt 0 && " ${WRITER_IDS[*]} " == *" ${api_id:0:12} "* ]] || fail "API não está ativa para iniciar manutenção"
    export MARKINA_RESET_WRITERS="${WRITER_IDS[*]}"
    python3 -c 'import json,os,sys; json.dump({"sha":os.environ["MARKINA_RESET_EXPECTED_SHA"],"owner":os.environ["MARKINA_RESET_OWNER_EMAIL"],"writers":os.environ["MARKINA_RESET_WRITERS"].split()},open(sys.argv[1],"x"))' "$state_file"
  fi
  [[ "${#WRITER_IDS[@]}" -gt 0 ]] || fail "estado de writers vazio"
  stop_writers || { fail "pausa incompleta; executar inspeção/retomada com o estado preservado"; return 1; }
  echo "writers Markina pausados e conferidos; iniciando reset sem dump"
  complete_reset || return 1
  evolution_after="$(evolution_snapshot)" || fail "estado Evolution posterior não pôde ser confirmado"
  [[ "$evolution_after" == "$evolution_before" ]] || fail "Evolution mudou durante a manutenção; inspeção necessária"
  [[ "$(git rev-parse HEAD)" == "$EXPECTED_SHA" ]] || fail "checkout mudou durante manutenção"
  rm -f -- "$state_file"
  echo "reset proprietário concluído; containers originais retomados; nenhuma imagem/volume/credencial alterada"
}

if [[ "${BASH_SOURCE[0]:-}" == "$0" || -z "${BASH_SOURCE[0]:-}" ]]; then main "$@"; fi
