"""Verificações estruturais da janela facial privada em homologação."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "manage-homolog-facial.sh").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "facial-homolog.yml").read_text(
    encoding="utf-8"
)
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
COMPOSE = (ROOT / "docker" / "docker-compose.yml").read_text(encoding="utf-8")


def require(text: str, description: str, source: str) -> None:
    if text not in source:
        raise AssertionError(f"ausente: {description}")


def forbid(pattern: str, description: str, source: str) -> None:
    if re.search(pattern, source, flags=re.MULTILINE):
        raise AssertionError(f"proibido: {description}")


def main() -> int:
    for text, description in (
        ('readonly PROJECT_ROOT="/opt/markina-gallery"', "diretório fixo"),
        ('readonly PROJECT_NAME="markina-gallery"', "projeto Compose fixo"),
        ('readonly ENV_FILE="docker/.env.homolog"', "ambiente fixo"),
        ('[[ "$(pwd -P)" == "$PROJECT_ROOT" ]]', "recusa de diretório inesperado"),
        ("git status --porcelain", "recusa de checkout remoto sujo"),
        ("o SHA publicado diverge do SHA autorizado", "vínculo ao SHA"),
        ("activate-private", "ativação privada"),
        ("pause-legacy-for-private-upgrade", "transição legada"),
        ("close-private", "fechamento privado"),
        ("reconcile-private", "reconciliação privada"),
        ("resume-private", "retomada privada"),
        ("ENABLE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "token de ativação"),
        ("PAUSE_LEGACY_FACIAL_FOR_PRIVATE_UPGRADE", "token de transição legada"),
        ("CLOSE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "token de fechamento"),
        ("RECONCILE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "token de reconciliação"),
        ("RESUME_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "token de retomada"),
        ("FACIAL_HOMOLOG_BATCH_ID", "vínculo ao lote"),
        ("FACIAL_HOMOLOG_ORIGIN_REF", "origem documentada"),
        ("FACIAL_HOMOLOG_AUTHORIZATION_REF", "autorização documentada"),
        ("FACIAL_HOMOLOG_OPERATOR_REF", "operador documentado"),
        ("EXPECTED_COUNT >= 500", "piso do lote"),
        ("EXPECTED_COUNT <= 1000", "teto do lote"),
        ("RETENTION_HOURS <= 72", "retenção limitada"),
        ("WINDOW_MINUTES <= 240", "janela limitada"),
        ("secrets.token_bytes(32)", "chave AEAD gerada no host"),
        ('chmod 600 "$ENV_FILE"', "permissão restrita"),
        ("compose_facial up -d --build --no-deps face-worker", "subida isolada"),
        ("compose_facial stop face-worker", "parada isolada"),
        ("wait_for_media_worker_idle", "proteção do job de mídia em andamento"),
        ("compose up -d --no-deps --force-recreate api worker", "recarga dos processos persistentes"),
        ("PhotoAsset.created_at >= started_at", "escopo temporal do lote"),
        ("len(photo_ids) != expected_count", "contagem exata antes do backfill"),
        ("count_correction", "correção auditada da contagem registrada"),
        ("observed_persisted_batch_count", "motivo fixo da correção de contagem"),
        ("enqueue_photo_index_if_eligible", "backfill pela idempotência normal"),
        ("purge_gallery_records", "purga síncrona"),
        ("photo_face_embedding", "prova agregada de embeddings"),
        ("facial_search_candidate", "prova agregada de candidatos"),
        ("reference_locator_ciphertext IS NOT NULL", "prova de referências"),
        ("closed-and-purged", "manifesto de fechamento"),
        ('"FACIAL_HOMOLOG_PRIVATE_MODE": "false"', "restauração do gate"),
        ('"FACIAL_MINOR_SEARCH_ENABLED": "false"', "restauração do gate de menores"),
        ("reload_reverse_proxy", "recarga do proxy"),
        ("rollback_pause", "rollback da pausa"),
        ("rollback_resume", "rollback da retomada"),
        ("retomada exige uma janela anterior válida e já expirada", "recusa de janela ainda vigente"),
        ("fila pendente diverge do lote", "prova exata da fila pendente"),
        ('payload.setdefault("resumptions", [])', "histórico de retomadas no manifesto"),
        ('"window_minutes": int(os.environ["FACIAL_WINDOW_MINUTES"])', "janela retomada auditada"),
        ('cp --preserve=mode "$ENV_BACKUP" "$ENV_FILE"', "restauração do backup de ambiente"),
        ("s.private_homologation_active", "validação fail-closed"),
        ('[[ "$(read_env_value FACIAL_HOMOLOG_PRIVATE_MODE)" != "true" ]]', "recusa de gate privado na transição legada"),
        ('[[ "${facial_enabled,,}" == "true" ]]', "exigência de flag ativa na pausa"),
    ):
        require(text, description, SCRIPT)

    for pattern, description in (
        (r"\bdocker\s+system\s+prune\b", "docker system prune"),
        (r"\bcompose(?:_facial)?\s+down\b", "docker compose down"),
        (r"\bgit\s+(?:reset|checkout)\b", "descarte Git"),
        (r"\bdocker\s+(?:rm|rmi)\b", "remoção de containers ou imagens"),
        (r"echo\s+.*FACIAL_AEAD_KEYS_JSON", "impressão de chave facial"),
        (r"activate-synthetic|pause-synthetic", "modo sintético legado"),
    ):
        forbid(pattern, description, SCRIPT)

    for text, description in (
        ("workflow_dispatch", "operação exclusivamente manual"),
        ("environment: homolog", "Environment protegido"),
        ("ref: ${{ inputs.sha }}", "scripts vinculados ao SHA publicado"),
        ("origin_ref", "entrada de origem"),
        ("authorization_ref", "entrada de autorização"),
        ("operator_ref", "entrada de operador"),
        ("expected_count", "quantidade esperada"),
        ("contains_minors", "declaração de menores"),
        ("ENABLE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "confirmação da ativação"),
        ("RECONCILE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "confirmação da reconciliação"),
        ("RESUME_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "confirmação da retomada"),
        ("BENCHMARK_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "confirmação do benchmark"),
        ("CLOSE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "confirmação do fechamento"),
        ("StrictHostKeyChecking=yes", "host SSH verificado"),
        ("< scripts/manage-homolog-facial.sh", "operador auditado por stdin"),
        ("< scripts/benchmark-homolog-facial.py", "observador auditado por stdin"),
        ("actions/upload-artifact@v4", "evidência agregada"),
        ("retention-days: 7", "retenção curta da evidência"),
    ):
        require(text, description, WORKFLOW)

    forbid(r"activate-synthetic-facial-homolog", "ativação automática legada", CI)
    forbid(r"Homolog-Facial: activate", "ativação por commit", CI)
    require(
        "Homolog-Facial: pause-legacy-for-private-upgrade",
        "trailer de transição legada",
        CI,
    )
    require(
        "PAUSE_LEGACY_FACIAL_FOR_PRIVATE_UPGRADE",
        "confirmação da transição legada no CI",
        CI,
    )
    for text, description in (
        ("reconcile-facial-homolog", "job corretivo isolado"),
        ("!contains(github.event.head_commit.message, 'Homolog-Facial: reconcile-private')", "deploy comum excluído da reconciliação"),
        ("grep -Fxq 'Homolog-Facial: reconcile-private'", "trailer exato da reconciliação"),
        ("Facial-Deployed-SHA", "vínculo corretivo ao SHA publicado"),
        ("Facial-Batch", "vínculo corretivo ao lote"),
        ("Facial-Authorization", "vínculo corretivo à autorização"),
        ("Facial-Expected-Count", "vínculo corretivo à quantidade"),
        ("Facial-Recorded-Count", "vínculo à quantidade originalmente registrada"),
        ("Facial-Contains-Minors", "vínculo corretivo à declaração de menores"),
        ("RECONCILE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "token corretivo"),
        ("resume-facial-homolog", "job protegido de retomada"),
        ("Homolog-Facial: resume-private", "trailer exato de retomada"),
        ("Facial-Window-Minutes", "janela limitada da retomada"),
        ("RESUME_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG", "token de retomada no CI"),
        ("--scope-from-manifest", "benchmark retomado no lote original"),
    ):
        require(text, description, CI)
    require(
        "worker:\n    build: ../backend\n    command: [\"python\", \"-m\", \"app.worker\"]\n    environment:\n      <<: *facial-environment",
        "worker de mídia recebe o mesmo gate facial",
        COMPOSE,
    )
    forbid(r"password\s*[:=]\s*[\"']?[^${\s]", "senha literal", WORKFLOW)

    print("manage-homolog-facial policy: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
