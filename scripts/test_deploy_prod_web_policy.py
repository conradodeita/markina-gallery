"""Guarda estrutural para impedir que o release de produção amplie seu escopo."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "deploy-prod-web.sh").read_text(encoding="utf-8")
APP_SCRIPT = (ROOT / "scripts" / "deploy-prod-app-services.sh").read_text(encoding="utf-8")
LOCK = (ROOT / "scripts" / "deploy-prod-lock.sh").read_text(encoding="utf-8")


def require(value: str, description: str) -> None:
    if value not in SCRIPT:
        raise AssertionError(f"ausente: {description}")


def forbid(pattern: str, description: str) -> None:
    if re.search(pattern, SCRIPT, flags=re.MULTILINE):
        raise AssertionError(f"proibido: {description}")


def main() -> None:
    if 'production-release.lock' not in APP_SCRIPT or 'production-release.lock' not in LOCK:
        raise AssertionError("API/web e web-only devem usar o mesmo arquivo de lock")
    if 'flock -n "$production_deploy_lock_fd"' not in APP_SCRIPT:
        raise AssertionError("release API/web deve falhar fechado quando o lock está ocupado")
    if 'web-in-flight.sha' not in APP_SCRIPT or 'app-in-flight.sha' not in LOCK:
        raise AssertionError("cada fluxo deve recusar tentativa pendente do outro fluxo")
    if 'if [[ "$MODE" == release || "$MODE" == rollback ]]; then acquire_app_deploy_lock; fi' not in APP_SCRIPT:
        raise AssertionError("API/web adquire lock apenas antes de release/rollback mutável")
    require('source "$SCRIPT_DIR/deploy-prod-lock.sh"', "lock compartilhado com release coordenado")
    require('acquire_production_deploy_lock "$STATE_DIR" web', "lock antes do fluxo web-only")
    require('git diff --quiet "$ACTIVE_SHA" "$TARGET_SHA" -- backend/',
            "recusa intervalo com mudanças de API no fluxo web-only")
    require('readonly PROJECT_ROOT="/opt/markina-gallery"', "raiz fixa do projeto")
    require('readonly PROJECT_NAME="markina-gallery"', "projeto Compose fixo")
    require('readonly COMPOSE_FILE="docker/docker-compose.yml"', "Compose fixo")
    require('readonly ENV_FILE="docker/.env.homolog"', "ambiente efetivo atual identificado")
    require('readonly PUBLIC_URL="https://markina.pickyourpic.com.br"', "domínio de produção fixo")
    require('docker compose "${files[@]}" --profile facial --profile preview-adjustment "$@"',
            "mesmo conjunto de Compose do runtime, com perfis explícitos")
    require('readonly COMPOSE_FILE_LABEL="/opt/markina-gallery/docker/docker-compose.yml,',
            "manifesto fixo dos arquivos Compose observados")
    require('compose build web', "build somente do web")
    require('compose up -d --no-deps --no-build web', "recriação somente do web sem dependências")
    require('git merge-base --is-ancestor "$TARGET_SHA" origin/main', "SHA aprovado de main")
    require('git status --porcelain', "recusa de checkout sujo")
    require('com.docker.compose.config-hash', "configuração do runtime comparada antes da troca")
    require('approval_fingerprint', "aprovação vinculada ao inventário observado")
    require('compose config --quiet', "validação de configuração sem imprimir segredos")
    require('web-last-healthy.sha', "estado independente do deploy de homologação")
    require('web-previous.sha', "rollback somente para versão web registrada")
    require('docker image tag "$WEB_IMAGE_ID" "$PROJECT_NAME-web:production-web-$ACTIVE_SHA"',
            "imagem web anterior preservada com tag por SHA")
    require('docker image tag "$saved_image" "$PROJECT_NAME-web"', "rollback restaura imagem web preservada")
    require('web-in-flight.sha', "tentativa interrompida identificável para rollback")
    require('curl --fail --silent --show-error --retry 5', "smoke tests HTTPS")

    # Comandos Compose capazes de alterar estado ficam encapsulados nas duas funções abaixo.
    for match in re.finditer(r"compose\s+(build|up)\s+([^\n]+)", SCRIPT):
        action, arguments = match.groups()
        if action == "build" and arguments.strip() != "web":
            raise AssertionError(f"build fora do escopo web: {arguments}")
        if action == "up" and arguments.strip() != "-d --no-deps --no-build web":
            raise AssertionError(f"up fora do escopo web: {arguments}")

    forbid(r"\bdocker\s+system\s+prune\b", "docker system prune")
    forbid(r"\bcompose\s+down\b", "docker compose down")
    forbid(r"\bcompose\s+(?:up|build)\s+[^\n]*(?:\bapi\b|\bworker\b|\bnginx\b|\bdb\b|\bredis\b)",
           "mutação de serviço não-web")
    forbid(r"\b(?:rm|rmdir)\s+-[A-Za-z]*r", "remoção recursiva")
    forbid(r"\b(?:sed\s+-i|tee\s+-a?)\b.*\.env", "alteração de arquivo de ambiente")

    print("deploy-prod-web policy: ok")


if __name__ == "__main__":
    main()
