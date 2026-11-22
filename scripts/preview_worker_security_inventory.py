"""Read-only inventory primitives for preview-worker security maintenance.

No Compose, Docker, Git, database, or filesystem mutation is performed here.
The production paths are fixed; tests inject a temporary root and runner.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

ROOT = Path("/opt/markina-gallery")
STATE = Path("/var/lib/markina-gallery/deploy-state")
PROJECT = "markina-gallery"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
SERVICES = {
    "api",
    "web",
    "worker",
    "db",
    "redis",
    "nginx",
    "migrate",
    "seed-admin",
    "evolution-api",
    "evolution-db",
    "evolution-redis",
    "face-search-worker",
    "face-index-worker",
    "face-maintenance-worker",
    "face-gemma-index-worker",
    "preview-adjustment-worker",
    "raw-development-worker",
    "system-monitor",
}
REQUIRED_ACTIVE = {
    "api",
    "web",
    "worker",
    "db",
    "redis",
    "nginx",
    "preview-adjustment-worker",
}
OPTIONAL_WRITERS = {
    "face-search-worker",
    "face-index-worker",
    "face-maintenance-worker",
    "face-gemma-index-worker",
    "raw-development-worker",
}
HEALTH_STATES = {"healthy", "none"}


class InventoryError(RuntimeError):
    """Sanitized, stable inventory failure."""


Runner = Callable[[Sequence[str], int], bytes]


def _sha(value: object) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _image(value: object) -> bool:
    return isinstance(value, str) and IMAGE_ID.fullmatch(value) is not None


def _safe_compose_paths(raw: object, root: Path, state: Path) -> list[dict[str, str]]:
    if not isinstance(raw, str) or not raw or len(raw) > 8192:
        raise InventoryError("compose_provenance_ausente")
    values = raw.split(",")
    if len(values) > 16 or len(set(values)) != len(values):
        raise InventoryError("compose_provenance_ambiguo")
    result = []
    for value in values:
        path = Path(value)
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                raise InventoryError("compose_manifesto_inseguro")
            resolved = path.resolve(strict=True)
            try:
                label = resolved.relative_to(root.resolve(strict=True)).as_posix()
            except ValueError:
                resolved.relative_to(state.resolve(strict=True))
                label = (
                    "deploy-state/"
                    + resolved.relative_to(state.resolve(strict=True)).as_posix()
                )
            digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        except InventoryError:
            raise
        except (OSError, ValueError):
            raise InventoryError("compose_path_fora_das_raizes_ou_ausente") from None
        result.append({"path": label, "sha256": digest})
    return result


class PreviewWorkerInventory:
    def __init__(
        self,
        *,
        root: Path = ROOT,
        state: Path = STATE,
        project: str = PROJECT,
        expected_compose_version: str = "2.35.1",
        runner: Runner | None = None,
    ):
        self.root = root
        self.state = state
        self.project = project
        self.expected_compose_version = expected_compose_version
        if not re.fullmatch(
            r"markina-gallery|pyp-preview-rehearsal-[0-9a-f]{10}", project
        ):
            raise InventoryError("projeto_compose_fora_da_allowlist")
        self.runner = runner or self._run

    def _run(self, args: Sequence[str], timeout: int) -> bytes:
        try:
            result = subprocess.run(
                list(args),
                cwd=self.root,
                capture_output=True,
                timeout=timeout,
                check=True,
                env={
                    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                },
            )
            return result.stdout
        except (OSError, subprocess.SubprocessError):
            raise InventoryError("consulta_read_only_falhou") from None

    def _text(self, *args: str, timeout: int = 30) -> str:
        try:
            value = self.runner(args, timeout).decode("utf-8").strip()
        except (UnicodeDecodeError, AttributeError):
            raise InventoryError("resposta_read_only_invalida") from None
        return value

    def _raw_bytes(self, *args: str, timeout: int = 30) -> bytes:
        try:
            value = self.runner(args, timeout)
        except (OSError, subprocess.SubprocessError):
            raise InventoryError("consulta_read_only_falhou") from None
        if not isinstance(value, bytes):
            raise InventoryError("resposta_read_only_invalida")
        return value

    def _inspect(self, ident: str) -> dict:
        raw = self._text("docker", "inspect", ident, timeout=30)
        try:
            values = json.loads(raw)
        except ValueError:
            raise InventoryError("docker_inspect_invalido") from None
        if (
            not isinstance(values, list)
            or len(values) != 1
            or not isinstance(values[0], dict)
        ):
            raise InventoryError("docker_inspect_ambiguo")
        return values[0]

    def _image_info(self, ident: str) -> dict:
        raw = self._text("docker", "image", "inspect", ident, timeout=30)
        try:
            values = json.loads(raw)
            if (
                not isinstance(values, list)
                or len(values) != 1
                or not isinstance(values[0], dict)
            ):
                raise ValueError
            return values[0]
        except ValueError:
            raise InventoryError("imagem_inspect_invalida") from None

    def _service(self, container: dict) -> dict:
        labels = container.get("Config", {}).get("Labels") or {}
        service = labels.get("com.docker.compose.service")
        if (
            labels.get("com.docker.compose.project") != self.project
            or service not in SERVICES
        ):
            raise InventoryError("container_fora_do_escopo_ou_servico_desconhecido")
        ident, image = container.get("Id"), container.get("Image")
        state = container.get("State") or {}
        status = state.get("Status")
        health = state.get("Health", {}).get("Status", "none")
        restart = container.get("HostConfig", {}).get("RestartPolicy") or {}
        config_hash = labels.get("com.docker.compose.config-hash")
        oneoff = labels.get("com.docker.compose.oneoff", "False")
        if not _sha(ident) or not _image(image):
            raise InventoryError("identidade_container_invalida")
        if status not in {
            "running",
            "exited",
            "created",
            "restarting",
            "paused",
            "dead",
        }:
            raise InventoryError("estado_container_desconhecido")
        if health not in HEALTH_STATES | {"starting", "unhealthy"}:
            raise InventoryError("health_container_desconhecido")
        if restart.get("Name") not in {"no", "always", "unless-stopped", "on-failure"}:
            raise InventoryError("restart_policy_desconhecida")
        retry_count = restart.get("MaximumRetryCount")
        if type(retry_count) is not int or retry_count < 0:
            raise InventoryError("restart_policy_incompleta")
        if oneoff not in {"False", "false"} and status == "running":
            raise InventoryError("container_oneoff_ativo")
        if not _sha(config_hash):
            raise InventoryError("compose_config_hash_ausente")
        compose = _safe_compose_paths(
            labels.get("com.docker.compose.project.config_files"), self.root, self.state
        )
        return {
            "service": service,
            "container_id": ident,
            "image_id": image,
            "status": status,
            "health": health,
            "restart_policy": {
                "name": restart["Name"],
                "maximum_retry_count": retry_count,
            },
            "compose_config_hash": config_hash,
            "compose_files": compose,
            "started_at": state.get("StartedAt")
            if isinstance(state.get("StartedAt"), str)
            else None,
        }

    def collect(
        self,
        *,
        expected_sha: str,
        candidate_image_id: str,
        allow_paused_producers: bool = False,
    ) -> dict:
        if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
            raise InventoryError("sha_alvo_invalido")
        if not _image(candidate_image_id):
            raise InventoryError("imagem_candidata_invalida")
        checkout_sha = self._text("git", "rev-parse", "HEAD")
        dirty = self._text("git", "status", "--porcelain")
        ids = self._text(
            "docker",
            "ps",
            "-aq",
            "--filter",
            "label=com.docker.compose.project=" + self.project,
        ).split()
        compose_version = self._text("docker", "compose", "version", "--short")
        compose_version = compose_version.lstrip("v")
        if compose_version != self.expected_compose_version:
            raise InventoryError("compose_version_nao_validada")
        if checkout_sha != expected_sha or dirty:
            raise InventoryError("checkout_diverge_ou_sujo")
        if len(ids) > 100 or len(ids) < len(REQUIRED_ACTIVE):
            raise InventoryError("contagem_containers_markina_invalida")
        try:
            candidate_info = self._image_info(candidate_image_id)
            candidate_os = candidate_info["Os"]
            candidate_arch = candidate_info["Architecture"]
        except (IndexError, KeyError, TypeError):
            raise InventoryError("imagem_candidata_inspect_invalida") from None
        if (
            candidate_info.get("Id") != candidate_image_id
            or candidate_os != "linux"
            or candidate_arch not in {"arm64", "amd64"}
        ):
            raise InventoryError("imagem_candidata_identidade_ou_arquitetura_invalida")
        services: dict[str, dict] = {}
        for ident in ids:
            item = self._service(self._inspect(ident))
            name = item["service"]
            # Multiple exited one-off tasks are not runtime identities. More
            # than one running instance is ambiguous and always blocks.
            if (
                name in services
                and item["status"] == "running"
                and services[name]["status"] == "running"
            ):
                raise InventoryError("servico_ativo_duplicado")
            if name not in services or item["status"] == "running":
                services[name] = item
        if not REQUIRED_ACTIVE.issubset(services):
            raise InventoryError("servicos_necessarios_ausentes")
        for name in REQUIRED_ACTIVE:
            item = services[name]
            if allow_paused_producers and name in {"api", "worker"}:
                if item["status"] != "exited":
                    raise InventoryError("produtor_nao_pausado")
                continue
            if item["status"] != "running" or item["health"] != "healthy":
                raise InventoryError("servico_necessario_nao_saudavel")
        worker = services["preview-adjustment-worker"]
        previous_info = self._image_info(worker["image_id"])
        if (
            previous_info.get("Os") != candidate_os
            or previous_info.get("Architecture") != candidate_arch
        ):
            raise InventoryError("arquitetura_candidata_divergente_do_worker")
        optional_active = sorted(
            name
            for name in OPTIONAL_WRITERS
            if name in services and services[name]["status"] == "running"
        )
        if self.state.is_symlink() or not self.state.is_dir():
            raise InventoryError("deploy_state_ausente_ou_inseguro")
        db_container = services["db"]["container_id"]
        db_snapshot = self._text(
            "docker",
            "exec",
            db_container,
            "sh",
            "-ceu",
            'exec psql -X -q -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" '
            '-d "$POSTGRES_DB" -F \'|\' -c "BEGIN READ ONLY; '
            "SET LOCAL statement_timeout='5s'; "
            "SELECT (SELECT string_agg(version_num, ',') FROM alembic_version), "
            "count(*) FILTER (WHERE status='queued'), "
            "count(*) FILTER (WHERE status='processing') FROM preview_adjustment; "
            'ROLLBACK;"',
            timeout=15,
        )
        parts = db_snapshot.split("|")
        if (
            len(parts) != 3
            or not re.fullmatch(r"[0-9]{8}_[0-9]{4}", parts[0])
            or not all(part.isdigit() for part in parts[1:])
        ):
            raise InventoryError("snapshot_queue_ou_schema_invalido")
        nginx_id = services["nginx"]["container_id"]
        nginx_main = self._raw_bytes(
            "docker", "exec", nginx_id, "cat", "/etc/nginx/nginx.conf", timeout=15
        )
        nginx_site = self._raw_bytes(
            "docker",
            "exec",
            nginx_id,
            "cat",
            "/etc/nginx/conf.d/default.conf",
            timeout=15,
        )
        marker_names = []
        for path in self.state.iterdir():
            if (
                "in-flight" in path.name
                or "in_flight" in path.name
                or "recovery-required" in path.name
                or path.name.endswith(".tmp")
                or (
                    path.name.startswith("preview-worker-security-")
                    and (
                        path.name.endswith(".compose.json")
                        or path.name.endswith(".nginx-original.conf")
                    )
                )
            ):
                marker_names.append(path.name)
        return {
            "format": 1,
            "expected_sha": expected_sha,
            "checkout_clean": True,
            "compose_version": compose_version,
            "candidate_image_id": candidate_image_id,
            "candidate_platform": f"{candidate_os}/{candidate_arch}",
            "services": services,
            "preview_worker_previous_image_id": worker["image_id"],
            "optional_writers_active": optional_active,
            "database_revision": parts[0],
            "preview_queue": {"queued": int(parts[1]), "processing": int(parts[2])},
            "nginx_config_sha256": hashlib.sha256(nginx_main).hexdigest(),
            "nginx_site_sha256": hashlib.sha256(nginx_site).hexdigest(),
            "pending_markers": sorted(marker_names),
        }


def fingerprint(inventory: dict) -> str:
    return hashlib.sha256(
        json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
