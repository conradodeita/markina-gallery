#!/usr/bin/env bash
# Contrato comum de identidade web. Só funções; source não altera estado.

release_read_identity() {
  local path="$1" value sha image config checkout extra
  [[ -f "$path" && ! -L "$path" ]] || { echo "identidade ausente/insegura: $path" >&2; return 1; }
  value="$(cat "$path")" || return 1
  read -r sha image config checkout extra <<< "$value"
  [[ "$sha" =~ ^[0-9a-f]{40}$ && "$image" =~ ^sha256:[0-9a-f]{64}$ \
    && "$config" =~ ^[0-9a-f]{64}$ && "$checkout" =~ ^[0-9a-f]{40}$ && -z "$extra" \
    && "$value" == "$sha $image $config $checkout" ]] \
    || { echo "identidade inválida: $path" >&2; return 1; }
  printf '%s\n' "$value"
}

release_write_file() {
  local name="$1" value="$2" temp
  [[ "$name" =~ ^(web|app)-[a-z.-]+$ && -d "$STATE_DIR" && ! -L "$STATE_DIR/$name" ]] || return 1
  temp="$(mktemp "$STATE_DIR/.$name.XXXXXX")" || return 1
  if ! printf '%s\n' "$value" > "$temp" || ! chmod 600 "$temp" || ! mv -f "$temp" "$STATE_DIR/$name"; then
    rm -f "$temp"
    return 1
  fi
}

release_image_id() {
  local id
  id="$(docker image inspect --format '{{.Id}}' "$1" 2>/dev/null)" || return 1
  [[ "$id" =~ ^sha256:[0-9a-f]{64}$ ]] || return 1
  printf '%s\n' "$id"
}

release_saved_tag() {
  [[ "$1" =~ ^sha256:[0-9a-f]{64}$ ]] || return 1
  printf '%s-web:rollback-%s\n' "$PROJECT_NAME" "${1#sha256:}"
}

release_check_image() {
  local image="$1" saved="${2:-false}" tag actual
  [[ "$(release_image_id "$image")" == "$image" ]] || { echo 'imagem por ID ausente' >&2; return 1; }
  tag="$(release_saved_tag "$image")" || return 1
  if actual="$(release_image_id "$tag")"; then
    [[ "$actual" == "$image" ]] || { echo 'tag de recuperação diverge do ID' >&2; return 1; }
  elif [[ "$saved" == true ]]; then
    echo 'referência de recuperação ausente' >&2; return 1
  fi
}

release_preserve_image() {
  local image="$1" tag
  release_check_image "$image" || return 1
  tag="$(release_saved_tag "$image")" || return 1
  docker image tag "$image" "$tag" || return 1
  [[ "$(release_image_id "$tag")" == "$image" ]]
}

release_assert_web_identity() {
  local image="$1" config="$2" record sha saved hash checkout
  record="$(release_read_identity "$STATE_DIR/web-current.identity")" || return 1
  read -r sha saved hash checkout <<< "$record"
  [[ "$saved" == "$image" && "$hash" == "$config" ]] \
    || { echo 'identidade web diverge do runtime; não usar marcadores legados' >&2; return 1; }
  git cat-file -e "$sha^{commit}" 2>/dev/null || return 1
  git merge-base --is-ancestor "$sha" "$TARGET_SHA" || return 1
  release_check_image "$image" || return 1
  printf '%s\n' "$record"
}

release_non_web_snapshot() {
  local id service ids
  ids="$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT_NAME")" || return 1
  while IFS= read -r id; do
    [[ -n "$id" ]] || continue
    service="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' "$id")" || return 1
    [[ "$service" == web ]] && continue
    docker inspect --format '{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.State.Status}}|{{with index .State "Health"}}{{with index . "Status"}}{{.}}{{end}}{{end}}|{{index .Config.Labels "com.docker.compose.config-hash"}}' "$id" || return 1
  done <<< "$ids"
}

release_assert_no_pending() {
  local name
  for name in web-in-flight.sha app-in-flight.sha app-rollback-in-flight.sha web-pending.identity; do
    [[ ! -e "$STATE_DIR/$name" ]] || { echo "tentativa pendente: $name; recuperação/reconciliação necessária" >&2; return 1; }
  done
}

release_load_support() {
  # O operador fornece o SHA da main aprovada, inclusive em recuperação.
  # Usa objetos já locais; nenhum fetch, arquivo temporário ou source do checkout antigo.
  local origin remote helper path expected
  [[ "$(pwd -P)" == "$PROJECT_ROOT" && "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] || return 1
  origin="$(git remote get-url origin)" || return 1
  case "$origin" in
    "https://github.com/$EXPECTED_REPOSITORY"|"https://github.com/$EXPECTED_REPOSITORY.git"|"git@github.com:$EXPECTED_REPOSITORY.git") ;;
    *) echo 'origin diverge' >&2; return 1 ;;
  esac
  [[ "$TARGET_SHA" == "$(git rev-parse origin/main)" ]] || { echo 'SHA não é a main local aprovada; preparação necessária' >&2; return 1; }
  if [[ "$MODE" != recover* && "$MODE" != rollback* ]]; then
    remote="$(git ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')" || return 1
    [[ "$remote" == "$TARGET_SHA" ]] || { echo 'HEAD remoto de main mudou' >&2; return 1; }
  fi
  for path in scripts/deploy-prod-lock.sh scripts/deploy-prod-state.sh; do
    if [[ "$path" == scripts/deploy-prod-lock.sh ]]; then expected="$RELEASE_LOCK_BLOB"; else expected="$RELEASE_STATE_BLOB"; fi
    [[ "$(git rev-parse "$TARGET_SHA:$path")" == "$expected" ]] || { echo 'suporte diverge do blob revisado' >&2; return 1; }
    helper="$(git show "$TARGET_SHA:$path")" || return 1
    source <(printf '%s\n' "$helper") || return 1
  done
}
