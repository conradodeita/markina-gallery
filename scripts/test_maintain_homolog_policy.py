"""Verificações estruturais da limpeza isolada de homologação."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "maintain-homolog-data.sh").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
MODULE = (ROOT / "backend" / "app" / "homolog_cleanup.py").read_text(encoding="utf-8")


def require(fragment: str, label: str, content: str) -> None:
    if fragment not in content:
        raise AssertionError(f"ausente: {label}")


def main() -> None:
    require('PROJECT_NAME="markina-gallery"', "projeto Compose fixo", SCRIPT)
    require('PROJECT_ROOT="/opt/markina-gallery"', "checkout remoto fixo", SCRIPT)
    require("DELETE_HOMOLOG_GALLERIES_AND_CLIENTS", "confirmação literal", SCRIPT)
    require("-e APP_ENV=homolog api", "ambiente explícito do container efêmero", SCRIPT)
    require("pg_dump -Fc", "backup lógico", SCRIPT)
    require("compose stop api worker", "pausa restrita", SCRIPT)
    require("redis-cli FLUSHDB", "fila exclusiva limpa", SCRIPT)
    require("environment: homolog", "Environment protegido", WORKFLOW)
    require("Homolog-Cleanup: galleries-and-clients", "sinalização exata", WORKFLOW)
    require("ALLOWED_ENVIRONMENTS", "gate APP_ENV", MODULE)
    require('TRUNCATE TABLE parent_gallery, client CASCADE', "raízes operacionais", MODULE)
    for forbidden in ("docker system prune", "docker compose down", "rm -rf"):
        if forbidden in SCRIPT:
            raise AssertionError(f"operação proibida encontrada: {forbidden}")
    print("maintain-homolog policy: ok")


if __name__ == "__main__":
    main()
