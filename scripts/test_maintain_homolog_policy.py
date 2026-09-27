"""Verificações estruturais da limpeza isolada de homologação."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "maintain-homolog-data.sh").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
MODULE = (ROOT / "backend" / "app" / "homolog_cleanup.py").read_text(encoding="utf-8")


def require(fragment: str, label: str, content: str) -> None:
    if fragment not in content:
        raise AssertionError(f"ausente: {label}")


def test_topology_guard() -> None:
    policy = SCRIPT.split("compose --profile whatsapp-real config --format json | python3 -c '\n", 1)[1].split(
        "\n' || fail", 1
    )[0]
    mounts = {
        "source": "media-source", "derivatives": "media-derivatives",
        "history": "media-history", "facial-references": "facial-references",
        "branding": "branding-assets",
    }
    config = {
        "name": "markina-gallery",
        "volumes": {
            source: {"name": f"markina-gallery_{source}"}
            for source in mounts.values()
        },
        "services": {
            "api": {
                "environment": {
                    "APP_ENV": "staging",
                    "DATABASE_URL": "postgresql+psycopg://synthetic@db:5432/markina_gallery",
                    "MARKINA_PUBLIC_URL": "http://localhost:3000",
                    "PUBLIC_APP_ORIGIN": "https://markina-homolog.duckdns.org",
                },
                "volumes": [
                    {"target": f"/var/lib/markina/{target}", "source": source}
                    for target, source in mounts.items()
                ],
            },
            "db": {"environment": {"POSTGRES_DB": "markina_gallery"}},
            "redis": {}, "evolution-db": {}, "evolution-redis": {},
            "nginx": {"ports": [{"published": "8080", "host_ip": "127.0.0.1"}]},
        },
    }

    def accepted(payload: dict) -> bool:
        result = subprocess.run(
            [sys.executable, "-c", policy], input=json.dumps(payload), text=True,
            capture_output=True, check=False,
        )
        return result.returncode == 0

    assert accepted(config)
    for mutation in (
        lambda value: value.update(name="another-project"),
        lambda value: value["services"]["api"]["environment"].update(APP_ENV="production"),
        lambda value: value["services"]["api"]["environment"].update(
            DATABASE_URL="postgresql+psycopg://synthetic@evolution-db:5432/markina_gallery"
        ),
        lambda value: value["services"]["api"]["environment"].update(
            PUBLIC_APP_ORIGIN="https://example.test"
        ),
        lambda value: value["services"]["api"]["environment"].update(
            PUBLIC_APP_ORIGIN="http://markina-homolog.duckdns.org"
        ),
        lambda value: value["services"]["api"]["environment"].pop("PUBLIC_APP_ORIGIN"),
        lambda value: value["services"]["nginx"]["ports"][0].update(host_ip="0.0.0.0"),
        lambda value: value["services"]["api"]["volumes"][0].update(source="evolution-instances"),
        lambda value: value["services"]["api"]["volumes"][0].update(
            source="another-project_media-source"
        ),
        lambda value: value["volumes"]["media-source"].update(
            name="another-project_media-source"
        ),
    ):
        changed = json.loads(json.dumps(config))
        mutation(changed)
        assert not accepted(changed)

    if shutil.which("docker"):
        environment = os.environ.copy()
        environment.update({
            "APP_ENV": "staging",
            "DATABASE_URL": "postgresql+psycopg://synthetic@db:5432/markina_gallery",
            "POSTGRES_DB": "markina_gallery",
            "MARKINA_GALLERY_PORT": "127.0.0.1:8080",
            "MARKINA_PUBLIC_URL": "http://localhost:3000",
            "PUBLIC_APP_ORIGIN": "https://markina-homolog.duckdns.org",
        })
        resolved = subprocess.run(
            ["docker", "compose", "--profile", "whatsapp-real", "-p", "markina-gallery", "-f",
             str(ROOT / "docker" / "docker-compose.yml"), "config", "--format", "json"],
            cwd=ROOT, env=environment, text=True, capture_output=True, check=False,
        )
        assert resolved.returncode == 0, "Compose de teste não resolveu a topologia"
        actual = subprocess.run(
            [sys.executable, "-c", policy], input=resolved.stdout, text=True,
            capture_output=True, check=False,
        )
        assert actual.returncode == 0, (
            f"guarda recusou o Compose real da Markina: {actual.stderr.strip()}"
        )


def main() -> None:
    test_topology_guard()
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
    require("face-index-worker face-search-worker face-maintenance-worker", "writers faciais", SCRIPT)
    require("preview_compose stop preview-adjustment-worker", "pausa do ajuste de prévia", SCRIPT)
    require("preview_compose up -d --no-deps preview-adjustment-worker", "retomada do ajuste de prévia", SCRIPT)
    require('compose --profile whatsapp-real config --format json | python3 -c', "topologia resolvida", SCRIPT)
    require('com.docker.compose.project', "rótulo do projeto exclusivo", SCRIPT)
    require('markina-homolog.duckdns.org', "subdomínio de homologação", SCRIPT)
    require('facial-references', "volume de referência facial", SCRIPT)
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
    require('TRUNCATE TABLE {tables} RESTRICT', "tabelas operacionais com FK restrita", MODULE)
    require('require_known_schema(db)', "bloqueio de tabela desconhecida", MODULE)
    require('require_exclusive_media_roots(roots)', "raízes de mídia fixas", MODULE)
    if 'TRUNCATE TABLE parent_gallery, client CASCADE' in MODULE:
        raise AssertionError("TRUNCATE CASCADE amplo não é permitido")
    for forbidden in ("docker system prune", "docker compose down", "rm -rf"):
        if forbidden in SCRIPT:
            raise AssertionError(f"operação proibida encontrada: {forbidden}")
    print("maintain-homolog policy: ok")


if __name__ == "__main__":
    main()
