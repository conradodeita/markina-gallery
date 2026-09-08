"""Impede controles do benchmark encerrado de voltarem ao caminho de produto."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REMOVED_PATHS = (
    ".github/workflows/facial-homolog.yml",
    "scripts/manage-homolog-facial.sh",
    "scripts/benchmark-homolog-facial.py",
    "scripts/test_manage_homolog_facial.sh",
    "scripts/test_manage_homolog_facial_policy.py",
    "scripts/test_benchmark_homolog_facial_policy.py",
)
PRODUCT_PATHS = (
    ".github/workflows/ci.yml",
    ".env.example",
    "backend/app/facial/config.py",
    "backend/app/facial/face_worker.py",
    "docker/docker-compose.yml",
    "scripts/deploy-homolog.sh",
)
BANNED_MARKERS = (
    "FACIAL_HOMOLOG_",
    "Homolog-Facial:",
    "activate-private",
    "reconcile-private",
    "resume-private",
    "retry-failed-private",
    "close-private",
    "manage-homolog-facial",
    "benchmark-homolog-facial",
)


def main() -> None:
    for relative_path in REMOVED_PATHS:
        assert not (ROOT / relative_path).exists(), relative_path
    for relative_path in PRODUCT_PATHS:
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        for marker in BANNED_MARKERS:
            assert marker not in content, f"{marker} reapareceu em {relative_path}"
    for relative_path in (
        "backend/app/facial/observability.py",
        "scripts/face_spike/harness.py",
        "scripts/deploy-homolog.sh",
    ):
        assert (ROOT / relative_path).is_file(), relative_path
    environment_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "FACIAL_PROCESSING_ENABLED=false" in environment_example
    assert "FACIAL_AEAD_KEYS_JSON=\n" in environment_example
    governance = (
        ROOT / "docs/GOVERNANCA-E-INCIDENTE-BUSCA-FACIAL.md"
    ).read_text(encoding="utf-8")
    for heading in (
        "## RIPD — registro e aprovação",
        "## Matriz controlador/operador",
        "## Direitos e revogação",
        "## Resposta a incidente",
        "## Recuperação e encerramento",
    ):
        assert heading in governance
    operation = (ROOT / "docs/OPERACAO-BUSCA-FACIAL-PRODUCAO.md").read_text(
        encoding="utf-8"
    )
    for stage in ("`dark`", "`canary`", "`limited`", "`general`"):
        assert stage in operation
    inventory = (
        ROOT / "docs/PRODUCAO-FACIAL-INVENTARIO-E-PLANO.md"
    ).read_text(encoding="utf-8")
    for heading in (
        "## Projeto, serviços e isolamento",
        "## Portas, domínio e healthchecks",
        "## Backup e migrations",
        "## Gates antes do canary",
        "## Canary proposto",
        "## Rollback de impacto zero",
    ):
        assert heading in inventory
    assert "FACIAL_PROCESSING_ENABLED=false" in inventory
    assert "2 CPU e 1.536 MiB" in inventory
    print("facial production policy: ok")


if __name__ == "__main__":
    main()
