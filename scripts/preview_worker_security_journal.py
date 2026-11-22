"""Journal atomico privado para o release isolado do worker de previas."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any


class JournalError(RuntimeError):
    """O estado duravel nao pode ser criado, atualizado ou removido com seguranca."""


class DurableJournal:
    def __init__(
        self, state_dir: Path, name: str = "preview-worker-security-in-flight.json"
    ):
        if Path(name).name != name or not name.endswith("-in-flight.json"):
            raise JournalError("journal_name_invalid")
        self.state_dir = state_dir
        self.path = state_dir / name
        self.temp_path = state_dir / (name + ".tmp")

    def _check_directory(self) -> None:
        try:
            info = self.state_dir.lstat()
        except OSError:
            raise JournalError("journal_state_directory_unavailable") from None
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise JournalError("journal_state_directory_unsafe")
        if os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
            raise JournalError("journal_state_directory_permissions_unsafe")
        if (
            os.name == "posix"
            and hasattr(os, "geteuid")
            and info.st_uid != os.geteuid()
        ):
            raise JournalError("journal_state_directory_owner_mismatch")

    def begin(
        self, *, fingerprint: str, previous_image_id: str, candidate_image_id: str
    ) -> None:
        self._check_directory()
        if (
            self.path.exists()
            or self.path.is_symlink()
            or self.temp_path.exists()
            or self.temp_path.is_symlink()
        ):
            raise JournalError("previous_journal_requires_recovery")
        self.write(
            {
                "format": 1,
                "phase": "approved",
                "fingerprint": fingerprint,
                "previous_image_id": previous_image_id,
                "candidate_image_id": candidate_image_id,
            },
            create=True,
        )

    def write(self, value: dict[str, Any], *, create: bool = False) -> None:
        self._check_directory()
        if not isinstance(value, dict) or value.get("format") != 1:
            raise JournalError("journal_payload_invalid")
        if self.temp_path.exists() or self.temp_path.is_symlink():
            raise JournalError("journal_temp_requires_recovery")
        if self.path.exists() or self.path.is_symlink():
            try:
                previous = self.path.lstat()
            except OSError:
                raise JournalError("journal_file_unsafe") from None
            if (
                not stat.S_ISREG(previous.st_mode)
                or stat.S_ISLNK(previous.st_mode)
                or (os.name == "posix" and stat.S_IMODE(previous.st_mode) != 0o600)
            ):
                raise JournalError("journal_file_unsafe")
            if (
                os.name == "posix"
                and hasattr(os, "geteuid")
                and previous.st_uid != os.geteuid()
            ):
                raise JournalError("journal_file_owner_mismatch")
        elif not create:
            raise JournalError("journal_file_missing")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(self.temp_path, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(value, stream, sort_keys=True, separators=(",", ":"))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(self.temp_path, self.path)
            if os.name == "posix":
                os.chmod(self.path, 0o600)
            if os.name == "posix":
                directory_fd = os.open(self.state_dir, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except (OSError, TypeError, ValueError):
            raise JournalError("journal_durable_write_failed") from None

    def read(self) -> dict[str, Any]:
        self._check_directory()
        try:
            info = self.path.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or stat.S_ISLNK(info.st_mode)
                or (os.name == "posix" and stat.S_IMODE(info.st_mode) != 0o600)
                or (
                    os.name == "posix"
                    and hasattr(os, "geteuid")
                    and info.st_uid != os.geteuid()
                )
                or info.st_size > 65536
            ):
                raise JournalError("journal_file_unsafe")
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except JournalError:
            raise
        except (OSError, ValueError, UnicodeDecodeError):
            raise JournalError("journal_read_failed") from None
        if not isinstance(value, dict) or value.get("format") != 1:
            raise JournalError("journal_payload_invalid")
        return value

    def finish(self) -> None:
        self._check_directory()
        try:
            value = self.read()
            if value.get("phase") != "complete":
                raise JournalError("journal_not_complete")
            self.path.unlink()
            if os.name == "posix":
                directory_fd = os.open(self.state_dir, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except JournalError:
            raise
        except OSError:
            raise JournalError("journal_finish_failed") from None
