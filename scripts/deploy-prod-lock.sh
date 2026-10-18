#!/usr/bin/env bash
# Lock comum dos procedimentos de produção da Pick-your-Pic.

production_deploy_lock_fd=9

acquire_production_deploy_lock() {
  local state_dir="$1" flow="$2" other_in_flight
  [[ "$flow" == "web" || "$flow" == "app" ]] || {
    echo "deploy-prod-lock: fluxo inválido" >&2
    return 1
  }
  [[ -d "$state_dir" ]] || {
    echo "deploy-prod-lock: diretório de estado ausente; inventário/reconciliação humana necessária" >&2
    return 1
  }
  command -v flock >/dev/null 2>&1 || {
    echo "deploy-prod-lock: flock indisponível; nenhuma operação foi executada" >&2
    return 1
  }
  exec {production_deploy_lock_fd}>"$state_dir/production-release.lock"
  if ! flock -n "$production_deploy_lock_fd"; then
    echo "deploy-prod-lock: outro inventário ou release está em andamento" >&2
    return 1
  fi

  if [[ "$flow" == "web" ]]; then
    other_in_flight="$state_dir/app-in-flight.sha"
  else
    other_in_flight="$state_dir/web-in-flight.sha"
  fi
  if [[ -e "$other_in_flight" ]]; then
    echo "deploy-prod-lock: tentativa do outro fluxo sem conclusão; reconciliação/rollback pelo fluxo correspondente é necessária" >&2
    return 1
  fi
}
