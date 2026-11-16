"""Adaptador Certbot de operação fixa; sem CLI e sem criação de conta ACME."""

from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

from scripts.wildcard_operational_custody import (
    CredentialError,
    _private_directory,
    _read,
)

SERVER = "https://acme-v02.api.letsencrypt.org/directory"
CERT_NAME = "pyp-tenant-wildcard"
EXECUTABLE = "/opt/pyp-acme-issuer/bin/certbot"


class IssuanceError(RuntimeError):
    """Nunca inclui stdout, stderr, segredo ou exceção original."""


class CertbotIssuer:
    """Configuração fixada pelo operador confiável, não por uma requisição.

    Não registra conta nem aceita termos da CA automaticamente. As autorizações
    externas e o pin do executável/configuração são gates do pacote operacional.
    Tests injetam runner sintético; o runner padrão tem alcance de rede real.
    """

    def __init__(
        self, state: Path, runtime: Path, account: str, *, runner=subprocess.run
    ):
        if not re.fullmatch(r"[0-9a-f]{32}", account):
            raise IssuanceError("issuer_configuration_invalid")
        self.state, self.runtime, self.account, self.runner = (
            state,
            runtime,
            account,
            runner,
        )

    def issue(self, credential: Path):
        import fcntl
        import resource

        lock = None
        try:
            if resource.getrlimit(resource.RLIMIT_CORE) != (0, 0):
                raise IssuanceError("issuer_core_dump_policy_invalid")
            state_fd = _private_directory(self.state)
            try:
                lock = os.open(
                    ".issuance.lock",
                    os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                    0o600,
                    dir_fd=state_fd,
                )
            finally:
                os.close(state_fd)
            info = os.fstat(lock)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
            ):
                raise ValueError()
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            credential_fd = _private_directory(credential.parent)
            try:
                # Só validar a forma; o subprocesso recebe o caminho, não o valor.
                value = _read(credential_fd, "cloudflare.ini", 512)
                if credential.name != "cloudflare.ini" or not re.fullmatch(
                    rb"dns_cloudflare_api_token = [A-Za-z0-9_-]{1,256}\n", value
                ):
                    raise ValueError()
            finally:
                os.close(credential_fd)
            runtime_fd = _private_directory(self.runtime)
            os.close(runtime_fd)
            with tempfile.TemporaryDirectory(
                prefix="issuance-", dir=self.runtime
            ) as temporary:
                work = Path(temporary)
                command = [
                    EXECUTABLE,
                    "certonly",
                    "--non-interactive",
                    "--config",
                    "/dev/null",
                    "--account",
                    self.account,
                    "--server",
                    SERVER,
                    "--config-dir",
                    str(self.state),
                    "--work-dir",
                    str(work / "work"),
                    "--logs-dir",
                    str(work / "logs"),
                    "--no-directory-hooks",
                    "--dns-cloudflare",
                    "--dns-cloudflare-credentials",
                    str(credential),
                    "--dns-cloudflare-propagation-seconds",
                    "60",
                    "--cert-name",
                    CERT_NAME,
                    "-d",
                    "*.pickyourpic.com.br",
                    "--keep-until-expiring",
                ]
                self.runner(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
                    cwd=work,
                    check=True,
                    timeout=300,
                    start_new_session=True,
                    umask=0o077,
                )
            # O próximo estágio lê e valida o bundle do estado fixo. Nenhum PEM sai em logs.
            return self.state / "live" / CERT_NAME
        except (
            OSError,
            ValueError,
            TypeError,
            CredentialError,
            subprocess.SubprocessError,
        ):
            raise IssuanceError("issuance_failed") from None
        finally:
            if lock is not None:
                os.close(lock)
