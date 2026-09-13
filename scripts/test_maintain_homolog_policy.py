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
    require(
        "DELETE_HOMOLOG_GALLERIES_AND_CLIENTS_WITHOUT_BACKUP",
        "confirmação literal exclusiva sem backup",
        SCRIPT,
    )
    require("--without-backup", "flag exclusiva sem backup", SCRIPT)
    require('"$@" </dev/null', "stdin isolada dos subprocessos Compose", SCRIPT)
    require("-e APP_ENV=homolog api", "ambiente explícito do container efêmero", SCRIPT)
    require("pg_dump -Fc", "backup lógico", SCRIPT)
    require("paused_services=(api worker)", "pausa restrita", SCRIPT)
    require('compose stop "${paused_services[@]}"', "pausa somente serviços selecionados", SCRIPT)
    require("compose restart nginx", "recarga do proxy após recriar API", SCRIPT)
    require(
        "http://127.0.0.1:8080/api/health",
        "healthcheck HTTP após manutenção",
        SCRIPT,
    )
    require("redis-cli FLUSHDB", "fila exclusiva limpa", SCRIPT)
    require('before["preserved"] != after["preserved"]', "preservação verificada", SCRIPT)
    require("environment: homolog", "Environment protegido", WORKFLOW)
    require("Homolog-Cleanup: galleries-and-clients", "sinalização exata", WORKFLOW)
    no_backup_trailer = "Homolog-Cleanup: galleries-and-clients-without-backup"
    require(no_backup_trailer, "sinalização exata sem backup", WORKFLOW)
    require("maintenance_without_backup", "propagação do modo sem backup", WORKFLOW)
    require(
        'maintenance_confirmation="DELETE_HOMOLOG_GALLERIES_AND_CLIENTS_WITHOUT_BACKUP"',
        "token e trailer sem backup selecionados juntos",
        WORKFLOW,
    )
    require(
        'maintenance_without_backup="--without-backup"',
        "flag e trailer sem backup selecionados juntos",
        WORKFLOW,
    )
    if WORKFLOW.index(no_backup_trailer) > WORKFLOW.index(
        "Homolog-Cleanup: galleries-and-clients'"
    ):
        raise AssertionError("o trailer sem backup deve ser testado antes do trailer legado")
    require("ALLOWED_ENVIRONMENTS", "gate APP_ENV", MODULE)
    require('TRUNCATE TABLE parent_gallery, client CASCADE', "raízes operacionais", MODULE)
    for forbidden in ("docker system prune", "docker compose down", "rm -rf"):
        if forbidden in SCRIPT:
            raise AssertionError(f"operação proibida encontrada: {forbidden}")
    print("maintain-homolog policy: ok")


if __name__ == "__main__":
    main()
