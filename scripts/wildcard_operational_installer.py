"""Instalador durável com destino ligado pelo operador; sem Docker ou shell."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path

from scripts.wildcard_operational_bundle import BundleError, validate_bundle
from scripts.wildcard_operational_custody import (
    CredentialError,
    _private_directory,
    _read,
    _write,
)

RELEASE = re.compile(r"release-[0-9a-f]{64}")


class InstallationError(RuntimeError):
    pass


class DurableInstaller:
    """Callbacks fixos de check/reload/probe são ligados por código confiável.

    Não é um helper privilegiado pronto para produção. Probe(None) verifica
    retirada de um primeiro bundle sem predecessor; não pode afirmar saúde de
    wildcard sem rota. Cada transição pendente retorna à referência anterior
    após um crash, antes de aceitar nova instalação.
    """

    def __init__(self, root: Path, trust: bytes, check, reload_service, probe):
        self.root, self.trust = root, trust
        self.check_config, self.reload_service, self.probe = (
            check,
            reload_service,
            probe,
        )

    def _target(self, fd, name):
        try:
            value = os.readlink(name, dir_fd=fd)
        except FileNotFoundError:
            return None
        if not RELEASE.fullmatch(value):
            raise InstallationError("unsafe_pointer")
        release_fd = _private_directory(self.root / value)
        os.close(release_fd)
        return value

    def _point(self, fd, target):
        if target is None:
            try:
                os.unlink("current", dir_fd=fd)
            except FileNotFoundError:
                pass
        else:
            # Limpar somente este nome temporário fixo, no diretório privado.
            try:
                os.unlink(".current-next", dir_fd=fd)
            except FileNotFoundError:
                pass
            os.symlink(target, ".current-next", dir_fd=fd)
            os.replace(".current-next", "current", src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)

    def _journal(self, fd, previous, target):
        try:
            os.unlink(".pending-next", dir_fd=fd)
        except FileNotFoundError:
            pass
        _write(
            fd,
            ".pending-next",
            json.dumps({"previous": previous, "target": target}).encode(),
        )
        os.replace(".pending-next", "pending.json", src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)

    def _healthy(self, target):
        self.check_config()
        self.reload_service()
        self.probe(target.removeprefix("release-") if target else None)

    def _recover(self, fd):
        try:
            pending = json.loads(_read(fd, "pending.json", 512))
        except FileNotFoundError:
            return
        if (
            not isinstance(pending, dict)
            or set(pending) != {"previous", "target"}
            or not isinstance(pending["target"], str)
            or not RELEASE.fullmatch(pending["target"])
            or (
                pending["previous"] is not None
                and (
                    not isinstance(pending["previous"], str)
                    or not RELEASE.fullmatch(pending["previous"])
                )
            )
        ):
            raise InstallationError("recovery_failed")
        previous = pending["previous"]
        if previous:
            release_fd = _private_directory(self.root / previous)
            try:
                chain, key = (
                    _read(release_fd, "fullchain.pem", 65536),
                    _read(release_fd, "privkey.pem", 16384),
                )
            finally:
                os.close(release_fd)
            if "release-" + validate_bundle(chain, key, self.trust) != previous:
                raise InstallationError("recovery_failed")
        try:
            self._point(fd, previous)
            self._healthy(previous)
        except Exception:  # noqa: BLE001 — recuperar antes de divulgar somente código sanitizado.
            raise InstallationError("recovery_failed") from None
        os.unlink("pending.json", dir_fd=fd)
        os.fsync(fd)

    def install(self, chain: bytes, key: bytes):
        import fcntl

        fd = lock = None
        try:
            fd = _private_directory(self.root)
            lock = os.open(
                ".install.lock",
                os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=fd,
            )
            info = os.fstat(lock)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
            ):
                raise InstallationError("unsafe_lock")
            fcntl.flock(lock, fcntl.LOCK_EX)
            self._recover(fd)
            fingerprint = validate_bundle(chain, key, self.trust)
            target = "release-" + fingerprint
            previous = self._target(fd, "current")
            try:
                os.mkdir(target, 0o700, dir_fd=fd)
            except FileExistsError:
                pass
            release_fd = _private_directory(self.root / target)
            try:
                for name, content, limit in (
                    ("fullchain.pem", chain, 65536),
                    ("privkey.pem", key, 16384),
                ):
                    try:
                        existing = _read(release_fd, name, limit)
                    except FileNotFoundError:
                        _write(release_fd, name, content)
                    else:
                        if existing != content:
                            raise InstallationError("release_invalid")
            finally:
                os.close(release_fd)
            os.fsync(fd)
            if previous == target:
                try:
                    self.probe(fingerprint)
                except Exception:  # noqa: BLE001 — replay também deve sanitizar falhas do probe.
                    raise InstallationError("installation_failed") from None
                return {"fingerprint": fingerprint, "replayed": True}
            self._journal(fd, previous, target)
            self._point(fd, target)
            try:
                self._healthy(target)
            except Exception:  # noqa: BLE001 — fronteira de callbacks, restaura antes de falhar.
                self._recover(fd)
                raise InstallationError("installation_failed") from None
            os.unlink("pending.json", dir_fd=fd)
            os.fsync(fd)
            return {"fingerprint": fingerprint, "replayed": False}
        except InstallationError:
            raise
        except (OSError, ValueError, TypeError, CredentialError, BundleError):
            raise InstallationError("installation_failed") from None
        finally:
            if lock is not None:
                os.close(lock)
            if fd is not None:
                os.close(fd)
