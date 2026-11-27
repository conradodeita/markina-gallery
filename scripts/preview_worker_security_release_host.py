"""Linux host adapter for the preview-worker security maintenance contract.

The module is intentionally not a CLI. Calling the mutating methods requires
constructing this adapter; this implementation has not been run against Oracle.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import time
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    import fcntl
except ImportError:  # pragma: no cover - production target is Linux
    fcntl = None

from preview_worker_maintenance_flow import Approval, MaintenanceError
from preview_worker_security_inventory import (
    PROJECT,
    ROOT,
    STATE,
    InventoryError,
    PreviewWorkerInventory,
    fingerprint,
)
from preview_worker_security_journal import DurableJournal, JournalError

PRODUCERS = ("api", "worker")
PUBLIC_URL = "https://markina.pickyourpic.com.br"
REQUIRED_PYTHON = {
    "aiohttp": "3.14.4",
    "multidict": "6.9.1",
    "urllib3": "2.8.0",
    "yarl": "1.25.1",
}
MAINTENANCE_CONFIRM_TIMEOUT = 15
MAINTENANCE_CONFIRM_INTERVAL = 0.25
RAWTHERAPEE_VERSION_PROBE = (
    "set +e; output=$(rawtherapee-cli --version 2>&1); status=$?; "
    "printf '%s\\n' \"$output\"; "
    'case "$status" in 0|2) exit 0;; *) exit "$status";; esac'
)


class HostError(MaintenanceError):
    pass


Command = Callable[[Sequence[str], bytes | None, int], bytes]


class PreviewWorkerSecurityHost:
    """Explicit Markina-scoped adapter; all external commands are allowlisted."""

    def __init__(
        self,
        *,
        expected_sha: str,
        candidate_image_id: str,
        callback_policy: str,
        window_approved: bool,
        root: Path = ROOT,
        state: Path = STATE,
        project: str = PROJECT,
        expected_compose_version: str = "2.35.1",
        maintenance_url: str = "http://127.0.0.1:8080",
        public_base_url: str = PUBLIC_URL,
        command: Command | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.root = root
        self.state = state
        self.project = project
        self.expected_compose_version = expected_compose_version
        self.maintenance_url = maintenance_url.rstrip("/")
        self.public_base_url = public_base_url.rstrip("/")
        maintenance_parsed = urlsplit(self.maintenance_url)
        public_parsed = urlsplit(self.public_base_url)
        self.smoke_protocol = public_parsed.scheme
        loopback_hosts = {"127.0.0.1", "localhost", "::1"}
        if not re.fullmatch(
            r"markina-gallery|pyp-preview-rehearsal-[0-9a-f]{10}", project
        ):
            raise HostError("projeto_compose_fora_da_allowlist")
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", expected_compose_version):
            raise HostError("compose_version_invalid")
        if (
            maintenance_parsed.scheme != "http"
            or maintenance_parsed.hostname not in loopback_hosts
            or public_parsed.username
            or public_parsed.password
            or not (
                self.smoke_protocol == "https"
                and public_parsed.hostname == "markina.pickyourpic.com.br"
                or self.smoke_protocol == "http"
                and public_parsed.hostname in loopback_hosts
            )
            or maintenance_parsed.path not in {"", "/"}
            or maintenance_parsed.query
            or maintenance_parsed.fragment
            or public_parsed.path not in {"", "/"}
            or public_parsed.query
            or public_parsed.fragment
        ):
            raise HostError("smoke_url_protocol_invalid")
        self.expected_sha = expected_sha
        self.candidate_image_id = candidate_image_id
        self.callback_policy = callback_policy
        self.window_approved = window_approved
        self.command = command or self._command
        self.sleeper = sleeper
        self.monotonic = monotonic
        self.inventory_data: dict[str, Any] | None = None
        self.approval: Approval | None = None
        self.fingerprint: str | None = None
        self.journal_store = DurableJournal(state)
        self.barrier_active = False

    def _command(
        self, args: Sequence[str], input_data: bytes | None, timeout: int
    ) -> bytes:
        try:
            result = subprocess.run(
                list(args),
                cwd=self.root,
                input=input_data,
                capture_output=True,
                timeout=timeout,
                check=True,
                env={
                    **os.environ,
                    "COMPOSE_REMOVE_ORPHANS": "false",
                    "COMPOSE_IGNORE_ORPHANS": "true",
                    "GIT_OPTIONAL_LOCKS": "0",
                },
            )
            return result.stdout
        except (OSError, subprocess.SubprocessError):
            raise HostError(
                "comando_operacional_falhou; consulte journal privado"
            ) from None

    def _run(self, *args: str, data: bytes | None = None, timeout: int = 60) -> str:
        return (
            self._run_bytes(*args, data=data, timeout=timeout).decode("utf-8").strip()
        )

    def _run_bytes(
        self, *args: str, data: bytes | None = None, timeout: int = 60
    ) -> bytes:
        try:
            output = self.command(args, data, timeout)
            if not isinstance(output, bytes):
                raise TypeError
            return output
        except HostError:
            raise
        except (OSError, TypeError, subprocess.SubprocessError):
            raise HostError(
                "comando_operacional_falhou; consulte journal privado"
            ) from None
        except UnicodeDecodeError:
            raise HostError("resposta_operacional_invalida") from None

    @contextmanager
    def lock(self):
        lock_path = self.state / "production-release.lock"
        try:
            if fcntl is None:
                raise HostError("lock_flock_disponivel_somente_em_linux")
            info = lock_path.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or stat.S_ISLNK(info.st_mode)
                or stat.S_IMODE(info.st_mode) & 0o022
            ):
                raise HostError("lock_compartilhado_inseguro")
            if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
                state_info = self.state.lstat()
                if not (
                    os.geteuid() == 0
                    and stat.S_ISDIR(state_info.st_mode)
                    and not stat.S_ISLNK(state_info.st_mode)
                    and not stat.S_IMODE(state_info.st_mode) & 0o077
                    and info.st_uid == state_info.st_uid
                ):
                    raise HostError("lock_compartilhado_owner_divergente")
            with lock_path.open("r+") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield
        except HostError:
            raise
        except BlockingIOError:
            raise HostError("outro_release_em_andamento") from None
        except (ImportError, OSError):
            raise HostError("lock_compartilhado_indisponivel") from None

    def _collector(self) -> PreviewWorkerInventory:
        def run(args: Sequence[str], timeout: int) -> bytes:
            return self.command(args, None, timeout)

        return PreviewWorkerInventory(
            root=self.root,
            state=self.state,
            project=self.project,
            expected_compose_version=self.expected_compose_version,
            runner=run,
        )

    def preflight(self) -> dict[str, Any]:
        try:
            inventory = self._collector().collect(
                expected_sha=self.expected_sha,
                candidate_image_id=self.candidate_image_id,
            )
        except InventoryError as exc:
            raise HostError(str(exc)) from None
        self.inventory_data = inventory
        self._assert_compose_runtime_matches(inventory)
        if inventory["candidate_platform"] != "linux/arm64":
            raise HostError("arquitetura_candidata_nao_arm64")
        if inventory["pending_markers"]:
            raise HostError("operacao_anterior_necessita_reconciliacao")
        if inventory["optional_writers_active"]:
            raise HostError("produtor_opcional_ativo")
        if (
            inventory["preview_queue"]["queued"] < 0
            or inventory["preview_queue"]["processing"] < 0
        ):
            raise HostError("contagem_fila_invalida")
        callback_policy = self.callback_policy
        approved = self.window_approved
        digest = fingerprint(
            {
                "inventory": inventory,
                "callback_policy": callback_policy,
                "window_open": approved,
            }
        )
        self.fingerprint = digest
        self.approval = Approval(digest, callback_policy, approved)
        return {
            "fingerprint": digest,
            "callback_policy": callback_policy,
            "window_open": approved,
            "checkout_clean": inventory["checkout_clean"],
            "compose_provenance_valid": all(
                service["compose_files"] and service["compose_config_hash"]
                for service in inventory["services"].values()
                if service["status"] == "running"
            ),
            "services_healthy": all(
                service["status"] == "running" and service["health"] == "healthy"
                for name, service in inventory["services"].items()
                if name
                in {
                    "api",
                    "web",
                    "worker",
                    "db",
                    "redis",
                    "nginx",
                    "preview-adjustment-worker",
                }
            ),
            "candidate_identity_valid": inventory["candidate_image_id"]
            == self.candidate_image_id,
            "previous_image_preserved": inventory[
                "preview_worker_previous_image_id"
            ].startswith("sha256:"),
            "no_concurrent_release": True,
            "optional_writers_stopped": not inventory["optional_writers_active"],
            "schema_unchanged": bool(inventory["database_revision"]),
            "previous_image_id": inventory["preview_worker_previous_image_id"],
            "candidate_image_id": inventory["candidate_image_id"],
            "inventory": inventory,
        }

    def journal(self, phase: str, **details: Any) -> None:
        if not self.fingerprint or not self.inventory_data:
            raise HostError("journal_sem_preflight")
        value = {
            "format": 1,
            "phase": phase,
            "fingerprint": self.fingerprint,
            "expected_sha": self.expected_sha,
            "callback_policy": self.callback_policy,
            "window_approved": self.window_approved,
            "previous_image_id": self.inventory_data[
                "preview_worker_previous_image_id"
            ],
            "candidate_image_id": self.candidate_image_id,
            "inventory": self.inventory_data,
            **details,
        }
        try:
            if self.journal_store.path.exists():
                self.journal_store.write(value)
            else:
                self.journal_store.begin(
                    fingerprint=self.fingerprint,
                    previous_image_id=value["previous_image_id"],
                    candidate_image_id=self.candidate_image_id,
                )
                self.journal_store.write(value)
        except JournalError as exc:
            raise HostError(str(exc)) from None

    def _inspect_id(self, ident: str) -> dict[str, Any]:
        try:
            result = json.loads(self._run("docker", "inspect", ident, timeout=30))
            if (
                not isinstance(result, list)
                or len(result) != 1
                or not isinstance(result[0], dict)
            ):
                raise ValueError
            return result[0]
        except (ValueError, TypeError):
            raise HostError("docker_inspect_invalido") from None

    def _container(self, service: str) -> dict[str, Any]:
        if (
            self.inventory_data is None
            or service not in self.inventory_data["services"]
        ):
            raise HostError("servico_fora_do_inventario")
        return self._inspect_id(
            self.inventory_data["services"][service]["container_id"]
        )

    def _compose(self, service: str, overlay: Path | None = None) -> list[str]:
        if (
            self.inventory_data is None
            or service not in self.inventory_data["services"]
        ):
            raise HostError("servico_compose_fora_do_inventario")
        files = self.inventory_data["services"][service]["compose_files"]
        if not files:
            raise HostError("compose_provenance_ausente")
        args = [
            "docker",
            "compose",
            "--project-directory",
            str(self.root / "docker"),
            "-p",
            self.project,
            "--profile",
            "*",
        ]
        for entry in files:
            relative = entry["path"]
            path = (
                (self.state / relative.removeprefix("deploy-state/"))
                if relative.startswith("deploy-state/")
                else self.root / relative
            )
            args += ["-f", str(path)]
        if overlay is not None:
            args += ["-f", str(overlay)]
        return args

    def _assert_compose_runtime_matches(self, inventory: dict[str, Any]) -> None:
        for service, item in inventory["services"].items():
            if item["status"] != "running":
                continue
            result = self._run(*self._compose(service), "config", "--hash", service)
            if result.split() != [service, item["compose_config_hash"]]:
                raise HostError("compose_config_nao_reproduz_runtime_ativo")

    def _assert_overlay_scope(self, overlay: Path) -> None:
        for service, item in self.inventory_data["services"].items():
            if service == "preview-adjustment-worker" or item["status"] != "running":
                continue
            result = self._run(
                *self._compose(service, overlay), "config", "--hash", service
            )
            if result.split() != [service, item["compose_config_hash"]]:
                raise HostError("overlay_altera_servico_fora_do_escopo")

    def _record_file(self, path: Path, data: bytes) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            raise HostError("recibo_privado_nao_persistido") from None

    @staticmethod
    def _maintenance_config(server: str) -> bytes:
        if server.count("server {") != 1:
            raise HostError("nginx_server_config_ambiguo")
        guarded = server.replace(
            "server {",
            'server {\n    if ($uri !~ "^/(healthz|api/health)$") { return 503; }',
            1,
        )
        return (
            "user nginx;\nworker_processes auto;\nevents { worker_connections 1024; }\nhttp {\n"
            + guarded
            + "\n}\n"
        ).encode()

    def _install_nginx(self, config: bytes) -> None:
        nginx = self.inventory_data["services"]["nginx"]["container_id"]
        self._run(
            "docker",
            "exec",
            "-i",
            nginx,
            "sh",
            "-ceu",
            "cat > /etc/nginx/nginx.conf",
            data=config,
        )
        self._run("docker", "exec", nginx, "nginx", "-t")
        self._run("docker", "exec", nginx, "nginx", "-s", "reload")

    def enable_maintenance(self) -> None:
        backup = self._nginx_backup_path()
        if not backup.exists() and not backup.is_symlink():
            nginx = self.inventory_data["services"]["nginx"]["container_id"]
            main = self._run_bytes(
                "docker", "exec", nginx, "cat", "/etc/nginx/nginx.conf"
            )
            server = self._run_bytes(
                "docker", "exec", nginx, "cat", "/etc/nginx/conf.d/default.conf"
            ).decode("utf-8")
            if (
                hashlib.sha256(main).hexdigest()
                != self.inventory_data["nginx_config_sha256"]
            ):
                raise HostError("nginx_config_mudou_apos_inventario")
            if (
                hashlib.sha256(server.encode()).hexdigest()
                != self.inventory_data["nginx_site_sha256"]
            ):
                raise HostError("nginx_site_mudou_apos_inventario")
            self._record_file(backup, main)
        else:
            try:
                info = backup.lstat()
                if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                    raise HostError("backup_nginx_inseguro")
                if info.st_size == 0 or (
                    os.name == "posix" and stat.S_IMODE(info.st_mode) != 0o600
                ):
                    raise HostError("backup_nginx_inseguro")
                main = backup.read_bytes()
                if (
                    hashlib.sha256(main).hexdigest()
                    != self.inventory_data["nginx_config_sha256"]
                ):
                    raise HostError("backup_nginx_diverge_do_inventario")
                nginx = self.inventory_data["services"]["nginx"]["container_id"]
                server = self._run_bytes(
                    "docker", "exec", nginx, "cat", "/etc/nginx/conf.d/default.conf"
                ).decode("utf-8")
            except HostError:
                raise
            except OSError:
                raise HostError("backup_nginx_ausente") from None
            if (
                hashlib.sha256(server.encode()).hexdigest()
                != self.inventory_data["nginx_site_sha256"]
            ):
                raise HostError("nginx_site_mudou_durante_recuperacao")
        self._install_nginx(self._maintenance_config(server))
        self._confirm_maintenance_barrier()

    def _confirm_maintenance_barrier(self) -> None:
        deadline = self.monotonic() + MAINTENANCE_CONFIRM_TIMEOUT
        while True:
            try:
                status = self._run(
                    "curl",
                    "--silent",
                    "--max-time",
                    "5",
                    "--output",
                    "/dev/null",
                    "--write-out",
                    "%{http_code}",
                    self.maintenance_url + "/",
                )
            except HostError:
                status = ""
            if status == "503":
                self.barrier_active = True
                return
            if self.monotonic() >= deadline:
                raise HostError("barreira_de_ingress_nao_confirmada")
            self.sleeper(MAINTENANCE_CONFIRM_INTERVAL)

    def disable_maintenance(self) -> None:
        backup = self._nginx_backup_path()
        try:
            info = backup.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                raise HostError("backup_nginx_inseguro")
            config = backup.read_bytes()
        except HostError:
            raise
        except OSError:
            raise HostError("backup_nginx_ausente") from None
        self._install_nginx(config)
        nginx = self.inventory_data["services"]["nginx"]["container_id"]
        restored = self._run_bytes(
            "docker", "exec", nginx, "cat", "/etc/nginx/nginx.conf"
        )
        if (
            hashlib.sha256(restored).hexdigest()
            != self.inventory_data["nginx_config_sha256"]
        ):
            raise HostError("nginx_config_restaurado_divergente")
        self.barrier_active = False

    def verify_restored_runtime(
        self, expected_worker_image_id: str | None = None
    ) -> None:
        expected_worker_image_id = expected_worker_image_id or self.candidate_image_id
        current = self._collector().collect(
            expected_sha=self.expected_sha,
            candidate_image_id=self.candidate_image_id,
        )
        for name, before in self.inventory_data["services"].items():
            after = current["services"].get(name)
            if after is None:
                raise HostError("servico_ausente_apos_release")
            fields = ("status", "health", "restart_policy")
            if name != "preview-adjustment-worker":
                fields += ("compose_config_hash",)
            if any(after.get(field) != before.get(field) for field in fields):
                raise HostError("config_servico_divergente_apos_release")
            if name != "preview-adjustment-worker" and any(
                after.get(field) != before.get(field)
                for field in ("container_id", "image_id")
            ):
                raise HostError("identidade_fora_do_escopo_divergente")
        target = current["services"]["preview-adjustment-worker"]
        if (
            target["image_id"] != expected_worker_image_id
            or target["status"] != "running"
        ):
            raise HostError("worker_esperado_nao_confirmado")
        original_target = self.inventory_data["services"]["preview-adjustment-worker"]
        if target["container_id"] == original_target["container_id"]:
            if target["compose_config_hash"] != original_target["compose_config_hash"]:
                raise HostError("compose_hash_worker_original_divergente")
        else:
            expected_target_hash = self._run(
                *self._compose(
                    "preview-adjustment-worker",
                    self._overlay(expected_worker_image_id),
                ),
                "config",
                "--hash",
                "preview-adjustment-worker",
            ).split()
            if (
                len(expected_target_hash) != 2
                or expected_target_hash[0] != "preview-adjustment-worker"
                or target["compose_config_hash"] != expected_target_hash[1]
            ):
                raise HostError("compose_hash_worker_diverge_do_overlay")
        if current["database_revision"] != self.inventory_data["database_revision"]:
            raise HostError("schema_database_alterado")
        if any(
            current.get(key) != self.inventory_data.get(key)
            for key in ("nginx_config_sha256", "nginx_site_sha256")
        ):
            raise HostError("nginx_config_nao_restaurado")
        for path in ("/healthz", "/api/health", "/"):
            curl_args = [
                "curl",
                "--proto",
                "=" + self.smoke_protocol,
                "--silent",
                "--show-error",
                "--max-time",
                "15",
                "--output",
                "/dev/null",
                "--write-out",
                "%{http_code}",
                self.public_base_url + path,
            ]
            if self.smoke_protocol == "https":
                curl_args.insert(3, "--tlsv1.2")
            status = self._run(
                *curl_args,
                timeout=20,
            )
            if status != "200":
                raise HostError("smoke_http_falhou")

    def _stop(
        self,
        service: str,
        signal_name: str,
        allowed: set[int],
        *,
        allow_restart_disabled: bool = False,
    ) -> None:
        item = self.inventory_data["services"][service]
        ident = item["container_id"]
        current = self._container(service)
        if current.get("Image") != item["image_id"]:
            raise HostError("container_image_mudou_apos_inventario")
        self._assert_restart_policy(
            service, current, allow_restart_disabled=allow_restart_disabled
        )
        if current.get("State", {}).get("Status") != "running":
            raise HostError("producer_nao_esta_running")
        self._run("docker", "update", "--restart=no", ident)
        self._run("docker", "kill", "--signal=" + signal_name, ident)
        deadline = self.monotonic() + 120
        while True:
            state = self._container(service)["State"]
            if state.get("Status") == "exited":
                if state.get("ExitCode") not in allowed:
                    raise HostError("processo_nao_encerrou_graciosamente")
                return
            if state.get("Status") != "running" or self.monotonic() >= deadline:
                raise HostError("timeout_parada_graciosa_sem_sigkill")
            self.sleeper(0.5)

    def pause_producers(self) -> None:
        for service in PRODUCERS:
            self._stop(service, "SIGTERM", {0, 143})

    def pause_producers_for_recovery(self) -> None:
        for service in PRODUCERS:
            item = self.inventory_data["services"][service]
            current = self._container(service)
            if current.get("Image") != item["image_id"]:
                raise HostError("producer_image_mudou_durante_recovery")
            self._assert_restart_policy(service, current, allow_restart_disabled=True)
            if current.get("State", {}).get("Status") == "running":
                self._stop(
                    service,
                    "SIGTERM",
                    {0, 143},
                    allow_restart_disabled=True,
                )
            elif current.get("State", {}).get("Status") != "exited":
                raise HostError("producer_estado_desconhecido_durante_recovery")
            self._run("docker", "update", "--restart=no", item["container_id"])

    def drain_preview_queue(self, timeout_seconds: int) -> bool:
        deadline = self.monotonic() + timeout_seconds
        db_id = self.inventory_data["services"]["db"]["container_id"]
        query = (
            "BEGIN READ ONLY; SET LOCAL statement_timeout='5s'; "
            "SELECT count(*) FILTER (WHERE status='queued'), "
            "count(*) FILTER (WHERE status='processing') FROM preview_adjustment; ROLLBACK;"
        )
        while self.monotonic() < deadline:
            raw = self._run(
                "docker",
                "exec",
                db_id,
                "sh",
                "-ceu",
                'exec psql -X -q -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" '
                '-d "$POSTGRES_DB" -F \'|\' -c "' + query + '"',
                timeout=15,
            )
            parts = raw.split("|")
            if len(parts) != 2 or not all(value.isdigit() for value in parts):
                return False
            if parts == ["0", "0"]:
                return True
            self.sleeper(1)
        return False

    def stop_legacy_worker(self) -> int:
        worker = self.inventory_data["services"]["preview-adjustment-worker"]
        ident = worker["container_id"]
        current = self._container("preview-adjustment-worker")
        if current.get("Image") != worker["image_id"]:
            raise HostError("imagem_worker_legado_mudou_apos_inventario")
        self._assert_restart_policy("preview-adjustment-worker", current)
        self._run("docker", "update", "--restart=no", ident)
        self._run("docker", "kill", "--signal=SIGINT", ident)
        deadline = self.monotonic() + 120
        while self.monotonic() < deadline:
            current = self._container("preview-adjustment-worker")["State"]
            if current.get("Status") == "exited":
                return current.get("ExitCode", -1)
            if current.get("Status") != "running":
                return -1
            self.sleeper(0.5)
        return -1

    def _overlay(self, image_id: str) -> Path:
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            raise HostError("image_id_invalido")
        path = self._overlay_path(image_id)
        content = json.dumps(
            {
                "services": {
                    "preview-adjustment-worker": {
                        "image": image_id,
                    }
                }
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
                raise HostError("overlay_compose_preexistente_divergente")
            return path
        self._record_file(path, content)
        return path

    def _up_worker(self, image_id: str) -> None:
        overlay = self._overlay(image_id)
        self._assert_compose_runtime_matches(self.inventory_data)
        self._assert_overlay_scope(overlay)
        command = self._compose("preview-adjustment-worker", overlay)
        self._run(
            *command,
            "up",
            "-d",
            "--no-deps",
            "--no-build",
            "--pull",
            "never",
            "preview-adjustment-worker",
            timeout=600,
        )

    def replace_preview_worker(self) -> None:
        self._up_worker(self.candidate_image_id)

    def _active_id(self, service: str) -> str:
        ids = self._run(
            "docker",
            "ps",
            "-q",
            "--filter",
            "label=com.docker.compose.project=" + self.project,
            "--filter",
            "label=com.docker.compose.service=" + service,
        ).split()
        if len(ids) != 1:
            raise HostError("runtime_ausente_ou_duplicado")
        return ids[0]

    def _wait_healthy(self, ident: str, timeout: int = 120) -> dict:
        deadline = self.monotonic() + timeout
        while self.monotonic() < deadline:
            value = self._inspect_id(ident)
            state = value.get("State", {})
            if state.get("Status") != "running":
                raise HostError("runtime_parou_durante_healthcheck")
            health = state.get("Health", {}).get("Status")
            if health == "healthy":
                return value
            if health not in {"starting", "unhealthy"}:
                raise HostError("healthcheck_ausente_ou_desconhecido")
            self.sleeper(1)
        raise HostError("runtime_nao_retornou_saudavel")

    def verify_candidate(self) -> None:
        ident = self._active_id("preview-adjustment-worker")
        current = self._wait_healthy(ident)
        if current.get("Image") != self.candidate_image_id:
            raise HostError("imagem_candidata_nao_ativa")
        code = (
            "from importlib.metadata import version; "
            "expected=" + repr(REQUIRED_PYTHON) + "; "
            "actual={name:version(name) for name in expected}; "
            "assert actual==expected, (actual,expected); "
            "print('dependencies-ok')"
        )
        self._run("docker", "exec", ident, "python", "-B", "-c", code, timeout=30)
        python_version = self._run(
            "docker", "exec", ident, "python", "--version", timeout=30
        )
        if python_version != "Python 3.13.16":
            raise HostError("python_runtime_divergente")
        self._run(
            "docker", "exec", ident, "python", "-B", "-m", "pip", "check", timeout=60
        )
        self._verify_rawtherapee_version(ident)
        after = self._collector().collect(
            expected_sha=self.expected_sha,
            candidate_image_id=self.candidate_image_id,
            allow_paused_producers=True,
        )
        before_services = self.inventory_data["services"]
        for name, before in before_services.items():
            if name in {"api", "worker", "preview-adjustment-worker"}:
                continue
            current_service = after["services"].get(name)
            if current_service is None or any(
                current_service.get(key) != before.get(key)
                for key in (
                    "container_id",
                    "image_id",
                    "compose_config_hash",
                    "restart_policy",
                )
            ):
                raise HostError("servico_fora_do_escopo_divergente")
        if after["database_revision"] != self.inventory_data["database_revision"]:
            raise HostError("schema_database_alterado")

    def _verify_rawtherapee_version(self, ident: str) -> None:
        rawtherapee_version = self._run(
            "docker",
            "exec",
            ident,
            "sh",
            "-c",
            RAWTHERAPEE_VERSION_PROBE,
            timeout=30,
        )
        if "RawTherapee, version 5.13, command line." not in rawtherapee_version:
            raise HostError("rawtherapee_runtime_divergente")

    def resume_producers(self) -> None:
        for service in reversed(PRODUCERS):
            item = self.inventory_data["services"][service]
            ident = item["container_id"]
            if self._container(service).get("Image") != item["image_id"]:
                raise HostError("producer_image_mudou_antes_de_retomar")
            restart_spec = self._restart_spec(item["restart_policy"])
            self._run("docker", "update", "--restart=" + restart_spec, ident)
            if self._container(service)["State"].get("Status") != "running":
                self._run("docker", "start", ident)
            self._wait_healthy(ident)

    def _assert_restart_policy(
        self,
        service: str,
        container: dict[str, Any],
        *,
        allow_restart_disabled: bool = False,
    ) -> None:
        expected = self.inventory_data["services"][service]["restart_policy"]
        actual = container.get("HostConfig", {}).get("RestartPolicy") or {}
        matches_inventory = (
            actual.get("Name") == expected["name"]
            and actual.get("MaximumRetryCount") == expected["maximum_retry_count"]
        )
        temporarily_disabled = (
            allow_restart_disabled
            and actual.get("Name") == "no"
            and actual.get("MaximumRetryCount") == 0
        )
        if not matches_inventory and not temporarily_disabled:
            raise HostError("restart_policy_mudou_apos_inventario")

    @staticmethod
    def _restart_spec(policy: dict[str, Any]) -> str:
        name = policy.get("name")
        retry_count = policy.get("maximum_retry_count")
        if (
            name not in {"no", "always", "unless-stopped", "on-failure"}
            or type(retry_count) is not int
            or retry_count < 0
            or (name != "on-failure" and retry_count != 0)
        ):
            raise HostError("restart_policy_invalida")
        if name == "on-failure" and retry_count > 0:
            return f"on-failure:{retry_count}"
        return name

    def write_success_receipt(self) -> None:
        if not self.inventory_data or not self.fingerprint:
            raise HostError("recibo_sem_inventario")
        receipt = {
            "format": 1,
            "result": "success",
            "fingerprint": self.fingerprint,
            "source_sha": self.expected_sha,
            "previous_image_id": self.inventory_data[
                "preview_worker_previous_image_id"
            ],
            "candidate_image_id": self.candidate_image_id,
            "database_revision": self.inventory_data["database_revision"],
        }
        path = self._receipt_path("success")
        self._write_idempotent_receipt(path, receipt)

    def recover(self, phase: str, previous_image_id: str) -> None:
        if not self.barrier_active:
            self.enable_maintenance()
        current_ids = self._run(
            "docker",
            "ps",
            "-q",
            "--filter",
            "label=com.docker.compose.project=" + self.project,
            "--filter",
            "label=com.docker.compose.service=preview-adjustment-worker",
        ).split()
        if len(current_ids) > 1:
            raise HostError("rollback_runtime_ambiguo")
        current_id = current_ids[0] if current_ids else None
        current = self._inspect_id(current_id) if current_id else None
        if current is not None and current.get("Image") not in {
            previous_image_id,
            self.candidate_image_id,
        }:
            raise HostError("rollback_runtime_imagem_nao_classificada")
        if current is None or current.get("Image") != previous_image_id:
            self.pause_producers_for_recovery()
            if current_id:
                if not self.drain_preview_queue(120):
                    raise HostError("rollback_fila_candidato_nao_drenada")
                state = current.get("State", {})
                if state.get("Status") == "running":
                    self._run("docker", "update", "--restart=no", current_id)
                    self._run("docker", "kill", "--signal=SIGINT", current_id)
                    deadline = self.monotonic() + 120
                    while self.monotonic() < deadline:
                        state = self._inspect_id(current_id).get("State", {})
                        if state.get("Status") == "exited":
                            if state.get("ExitCode") != 130:
                                raise HostError("candidato_nao_encerrou_graciosamente")
                            break
                        if state.get("Status") != "running":
                            raise HostError("candidato_estado_desconhecido")
                        self.sleeper(0.5)
                    else:
                        raise HostError("timeout_parada_candidato_sem_sigkill")
                elif state.get("Status") != "exited":
                    raise HostError("candidato_estado_desconhecido")
            if not self.drain_preview_queue(120):
                raise HostError("rollback_fila_candidato_nao_drenada")
            self._up_worker(previous_image_id)
            restored_id = self._active_id("preview-adjustment-worker")
            restored = self._wait_healthy(restored_id)
            if restored.get("Image") != previous_image_id:
                raise HostError("rollback_imagem_anterior_nao_confirmada")
        self.resume_producers()
        self.disable_maintenance()
        self.verify_restored_runtime(previous_image_id)
        self.journal("recovered", failed_phase=phase)

    def recover_inflight(self) -> None:
        """Resume only a journaled recovery; never start a new release."""
        try:
            current = self.journal_store.read()
        except JournalError as exc:
            raise HostError(str(exc)) from None
        required = {
            "format",
            "phase",
            "fingerprint",
            "expected_sha",
            "callback_policy",
            "window_approved",
            "previous_image_id",
            "candidate_image_id",
            "inventory",
        }
        if not required.issubset(current) or current.get("format") != 1:
            raise HostError("journal_inflight_invalido")
        phases = {
            "approved",
            "maintenance_starting",
            "maintenance_active",
            "producers_pausing",
            "producers_paused",
            "draining_queue",
            "queue_drained",
            "legacy_stopping",
            "legacy_stopped",
            "candidate_starting",
            "candidate_started",
            "candidate_verifying",
            "candidate_verified",
            "producers_resuming",
            "producers_resumed",
            "maintenance_disabling",
            "traffic_restored",
            "final_runtime_verifying",
            "final_runtime_verified",
            "success_receipt_writing",
            "recovery-started",
            "recovered",
            "complete",
        }
        inventory = current.get("inventory")
        callback_policy = current.get("callback_policy")
        window_approved = current.get("window_approved")
        previous_image_id = current.get("previous_image_id")
        candidate_image_id = current.get("candidate_image_id")
        expected_sha = current.get("expected_sha")
        if (
            current.get("phase") not in phases
            or not isinstance(inventory, dict)
            or not re.fullmatch(r"[0-9a-f]{64}", current.get("fingerprint", ""))
            or not re.fullmatch(r"[0-9a-f]{40}", expected_sha or "")
            or callback_policy
            not in {"provider_retry_proven", "callback_outage_accepted"}
            or window_approved is not True
            or not isinstance(previous_image_id, str)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", previous_image_id)
            or not isinstance(candidate_image_id, str)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", candidate_image_id)
            or previous_image_id == candidate_image_id
            or inventory.get("expected_sha") != expected_sha
            or inventory.get("candidate_image_id") != candidate_image_id
            or inventory.get("preview_worker_previous_image_id") != previous_image_id
            or fingerprint(
                {
                    "inventory": inventory,
                    "callback_policy": callback_policy,
                    "window_open": window_approved,
                }
            )
            != current.get("fingerprint")
        ):
            raise HostError("journal_inflight_invalido")
        self.fingerprint = current["fingerprint"]
        self.expected_sha = current["expected_sha"]
        self.callback_policy = current["callback_policy"]
        self.window_approved = current["window_approved"] is True
        self.candidate_image_id = current["candidate_image_id"]
        self.inventory_data = current["inventory"]
        phase = current["phase"]
        if phase == "complete":
            self.finish_journal()
            return
        previous = current["previous_image_id"]
        self.journal("recovery-started", failed_phase=phase)
        self.recover(phase, previous)
        self.write_recovery_receipt(phase)
        self.journal("complete", result="recovered", failed_phase=phase)
        self.finish_journal()

    def write_recovery_receipt(self, failed_phase: str) -> None:
        receipt = {
            "format": 1,
            "result": "recovered",
            "fingerprint": self.fingerprint,
            "source_sha": self.expected_sha,
            "failed_phase": failed_phase,
            "restored_image_id": self.inventory_data[
                "preview_worker_previous_image_id"
            ],
        }
        path = self._receipt_path("recovery")
        self._write_idempotent_receipt(path, receipt)

    def _write_idempotent_receipt(self, path: Path, receipt: dict[str, Any]) -> None:
        content = (
            json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        try:
            info = path.lstat()
        except FileNotFoundError:
            self._record_file(path, content)
            return
        except OSError:
            raise HostError("recibo_privado_nao_persistido") from None
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_ISLNK(info.st_mode)
            or (os.name == "posix" and stat.S_IMODE(info.st_mode) != 0o600)
            or path.read_bytes() != content
        ):
            raise HostError("recibo_preexistente_divergente")

    def finish_journal(self) -> None:
        current = self.journal_store.read()
        if current.get("phase") != "complete":
            raise HostError("journal_nao_completo")
        kind = "recovery" if current.get("result") == "recovered" else "success"
        receipt = self._receipt_path(kind)
        if kind == "recovery":
            expected_receipt = {
                "format": 1,
                "result": "recovered",
                "fingerprint": current.get("fingerprint"),
                "source_sha": current.get("expected_sha"),
                "failed_phase": current.get("failed_phase"),
                "restored_image_id": current.get("previous_image_id"),
            }
        else:
            inventory = current.get("inventory") or {}
            expected_receipt = {
                "format": 1,
                "result": "success",
                "fingerprint": current.get("fingerprint"),
                "source_sha": current.get("expected_sha"),
                "previous_image_id": current.get("previous_image_id"),
                "candidate_image_id": current.get("candidate_image_id"),
                "database_revision": inventory.get("database_revision"),
            }
        expected_bytes = (
            json.dumps(expected_receipt, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        try:
            info = receipt.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or stat.S_ISLNK(info.st_mode)
                or (os.name == "posix" and stat.S_IMODE(info.st_mode) != 0o600)
                or (
                    os.name == "posix"
                    and hasattr(os, "geteuid")
                    and info.st_uid != os.geteuid()
                )
                or receipt.read_bytes() != expected_bytes
            ):
                raise HostError("recibo_final_inseguro")
        except HostError:
            raise
        except OSError:
            raise HostError("recibo_final_ausente") from None
        overlay_images = {
            current.get("candidate_image_id"),
            current.get("previous_image_id"),
        }
        transient_paths = [self._nginx_backup_path()]
        transient_paths.extend(
            self._overlay_path(image_id)
            for image_id in overlay_images
            if isinstance(image_id, str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", image_id)
        )
        for path in transient_paths:
            try:
                if path.exists() or path.is_symlink():
                    info = path.lstat()
                    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                        raise HostError("transient_release_file_inseguro")
                    path.unlink()
            except HostError:
                raise
            except OSError:
                raise HostError("transient_release_file_cleanup_failed") from None
        self.journal_store.finish()

    def _nginx_backup_path(self) -> Path:
        if not self.fingerprint:
            raise HostError("backup_sem_fingerprint")
        return (
            self.state
            / f"preview-worker-security-{self.fingerprint}.nginx-original.conf"
        )

    def _overlay_path(self, image_id: str | None = None) -> Path:
        image_id = image_id or self.candidate_image_id
        suffix = hashlib.sha256(image_id.encode()).hexdigest()
        return self.state / f"preview-worker-security-{suffix}.compose.json"

    def _receipt_path(self, kind: str) -> Path:
        if not self.fingerprint:
            raise HostError("recibo_sem_fingerprint")
        return self.state / f"preview-worker-security-{self.fingerprint}-{kind}.json"
