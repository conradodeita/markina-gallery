"""Verificações estruturais da ativação facial sintética em homologação."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "manage-homolog-facial.sh").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def require(text: str, description: str, source: str) -> None:
    if text not in source:
        raise AssertionError(f"ausente: {description}")


def forbid(pattern: str, description: str, source: str) -> None:
    if re.search(pattern, source, flags=re.MULTILINE):
        raise AssertionError(f"proibido: {description}")


def main() -> int:
    require('readonly PROJECT_ROOT="/opt/markina-gallery"', "diretório fixo Markina", SCRIPT)
    require('readonly PROJECT_NAME="markina-gallery"', "projeto Compose fixo", SCRIPT)
    require('readonly ENV_FILE="docker/.env.homolog"', "ambiente fixo de homologação", SCRIPT)
    require('[[ "$(pwd -P)" == "$PROJECT_ROOT" ]]', "recusa de diretório inesperado", SCRIPT)
    require('git status --porcelain', "recusa de checkout remoto sujo", SCRIPT)
    require('o SHA publicado diverge do SHA autorizado', "vínculo ao SHA autorizado", SCRIPT)
    require('record_inventory', "inventário imediatamente anterior", SCRIPT)
    require('architecture=%s cpus=%s', "inventário de arquitetura e CPUs", SCRIPT)
    require('MemTotal', "inventário de memória", SCRIPT)
    require('docker ps \\', "inventário de containers", SCRIPT)
    require('label=com.docker.compose.project=$PROJECT_NAME', "escopo exclusivo do projeto", SCRIPT)
    require('ENABLE_SYNTHETIC_ADULT_FACIAL_HOMOLOG', "confirmação forte", SCRIPT)
    require('aarch64', "gate ARM64", SCRIPT)
    require('FACIAL_PROCESSING_ENABLED": "true"', "ativação explícita", SCRIPT)
    require('homolog-synthetic-only-no-real-data-v1', "escopo apenas sintético", SCRIPT)
    require('FACIAL_MINOR_SEARCH_ENABLED": "false"', "menores bloqueados", SCRIPT)
    require('secrets.token_bytes(32)', "chave AEAD gerada no host", SCRIPT)
    require('chmod 600 "$ENV_FILE"', "permissão restrita da configuração", SCRIPT)
    require('facial-env-preactivate-', "backup restrito antes da alteração", SCRIPT)
    require('compose_facial up -d --build --no-deps face-worker', "subida isolada do worker", SCRIPT)
    require('compose up -d --no-deps --force-recreate api', "recriação limitada da API", SCRIPT)
    require('target_environment="$(grep \'^APP_ENV=\' "$ENV_FILE"', "ambiente herdado do host", SCRIPT)
    require('$target_environment" == "staging"', "identificador staging permitido", SCRIPT)
    require('settings.credential_environment == settings.environment', "credencial vinculada ao ambiente", SCRIPT)
    require('logs --no-color --tail 80 face-worker', "diagnóstico sanitizado do worker", SCRIPT)
    require('settings.worker_concurrency == 1', "concorrência unitária", SCRIPT)
    require('unexpected_ports', "verificação de portas do worker", SCRIPT)
    require('rollback_activation', "rollback de configuração", SCRIPT)
    require('compose_facial stop face-worker', "rollback limitado ao worker facial", SCRIPT)
    forbid(r'\bdocker\s+system\s+prune\b', "docker system prune", SCRIPT)
    forbid(r'\bcompose(?:_facial)?\s+down\b', "docker compose down", SCRIPT)
    forbid(r'\bgit\s+(?:reset|checkout)\b', "descarte Git", SCRIPT)
    forbid(r'\bdocker\s+(?:rm|rmi)\b', "remoção de containers ou imagens", SCRIPT)
    forbid(r'echo\s+.*FACIAL_AEAD_KEYS_JSON', "impressão de chave facial", SCRIPT)

    require('activate-synthetic-facial-homolog:', "job facial dedicado", WORKFLOW)
    require('needs: [deploy-homolog]', "ativação somente após deploy verde", WORKFLOW)
    require('environment: homolog', "Environment protegido", WORKFLOW)
    require('Homolog-Facial: activate-synthetic-adults', "trailer explícito", WORKFLOW)
    require('ENABLE_SYNTHETIC_ADULT_FACIAL_HOMOLOG', "token de confirmação no job", WORKFLOW)
    require('secrets.HOMOLOG_SSH_PRIVATE_KEY', "SSH por secret", WORKFLOW)
    require('StrictHostKeyChecking=yes', "host SSH verificado", WORKFLOW)
    require('cd /opt/markina-gallery && env MARKINA_EXPECTED_REPOSITORY=', "diretório remoto fixo", WORKFLOW)
    require('< scripts/manage-homolog-facial.sh', "script auditado enviado por stdin", WORKFLOW)
    forbid(r'password\s*[:=]\s*["\']?[^${\s]', "senha literal", WORKFLOW)

    print("manage-homolog-facial policy: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
