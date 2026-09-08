"""Verificações estruturais do observador de desempenho facial."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "benchmark-homolog-facial.py").read_text(encoding="utf-8")


def require(fragment: str, label: str) -> None:
    if fragment not in SCRIPT:
        raise AssertionError(f"ausente: {label}")


def forbid(pattern: str, label: str) -> None:
    if re.search(pattern, SCRIPT, flags=re.MULTILINE | re.IGNORECASE):
        raise AssertionError(f"proibido: {label}")


def test_observer_is_scoped_read_only_and_privacy_minimized() -> None:
    require('PROJECT_ROOT = Path("/opt/markina-gallery")', "checkout remoto fixo")
    require('PROJECT_NAME = "markina-gallery"', "projeto Compose fixo")
    require('CONFIRMATION = "BENCHMARK_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG"', "confirmação privada autorizada")
    require('not in {"aarch64", "arm64"}', "gate ARM64")
    require("SHA publicado diverge", "vínculo ao SHA")
    require("s.enabled", "gate facial")
    require("s.private_homologation_active", "gate privado não expirado")
    require("s.homolog_batch_id", "vínculo ao lote")
    require("s.homolog_authorization_ref", "vínculo à autorização")
    require("s.homolog_expected_count", "vínculo à quantidade")
    require("s.homolog_contains_minors", "inventário de menores vinculado ao lote")
    require("'client_minor_search':s.minor_search_enabled", "gate infantil separado da indexação")
    require('"client_minor_search": options.contains_minors', "consulta infantil separada e escopada ao lote")
    require('photos != expected_count', "estabilização exige quantidade exata")
    require('photos > options.expected_count', "recusa excesso do lote")
    require('== options.expected_count', "sucesso exige quantidade exata")
    require('SERVICES = ("api", "worker", "face-worker", "db")', "containers limitados")
    require("docker\", \"stats", "métrica agregada de containers")
    require("COUNT(*)", "consultas agregadas")
    require("facial_throughput_photos_per_second", "throughput calculado")
    require("resource_maxima", "máximas de recursos")
    require("used_delta_bytes", "variação de disco")
    require("--scope-from-manifest", "escopo retomado explícito")
    require('STATE_DIR = Path("/var/lib/markina-gallery/deploy-state")', "manifesto operacional restrito")
    require('payload["recorded_at"]', "início original do lote")
    require('payload.get("scope_expires_at"', "fim imutável do lote original")
    require("manifesto diverge do lote autorizado", "vínculo do manifesto retomado")
    require("continuation_completed", "progresso medido na retomada")
    require("continuation_throughput_photos_per_second", "throughput da continuação")
    for forbidden, label in (
        (r"\b(delete|update|insert|truncate)\s+", "SQL mutável"),
        (r"\bdocker\s+(rm|rmi|stop|restart|kill|system\s+prune)\b", "mutação Docker"),
        (r"\bcompose\([^\n]*(up|down|stop|restart|build|pull)", "mutação Compose"),
        (r"select[^\n]*(filename|display_name|storage_key|payload_ciphertext|phone)", "PII ou artefato"),
    ):
        forbid(forbidden, label)


if __name__ == "__main__":
    test_observer_is_scoped_read_only_and_privacy_minimized()
    print("benchmark-homolog-facial policy: ok")
