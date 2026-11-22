"""Recuperação isolada a partir do arquivo e da chave guardados fora do host."""

from __future__ import annotations

import json
import struct
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from .archive import (
    MAGIC,
    MAX_HEADER_BYTES,
    ArchiveReceipt,
    _local_runtime,
    _ProductionContext,
    _read_exact,
)
from .restore import BackupRestoreError, RestoreReceipt, RestoreTarget, _restore_global
from .runtime_config import BackupKeyring, parse_recovery_keyring


def restore_saved_archive(
    source: BinaryIO, *, keyring: BackupKeyring, artifact: ArchiveReceipt,
    expected_schema: str, target: RestoreTarget, at: datetime,
) -> RestoreReceipt:
    """Restaura conteúdo autenticado somente em destino vazio e descartável."""
    _local_runtime()
    try:
        source.seek(0)
        if _read_exact(source, len(MAGIC)) != MAGIC:
            raise ValueError
        length = struct.unpack(">I", _read_exact(source, 4))[0]
        if not 0 < length <= MAX_HEADER_BYTES:
            raise ValueError
        header = _read_exact(source, length)
        meta = json.loads(header)
        context = _ProductionContext(UUID(meta["instance_id"]), UUID(meta["backup_id"]), meta["schema_revision"],
                                     meta["environment"], datetime.fromisoformat(meta["created_at"]), meta["key_id"])
        if (context.instance_id != keyring.installation_id or header != context.header()
                or context.backup_id != artifact.backup_id or context.schema_revision != expected_schema):
            raise ValueError
        key = keyring.key_for(context.key_id)
    except Exception:  # noqa: BLE001 -- uma mídia inválida não é exibida em saída operacional.
        raise BackupRestoreError("Identidade ou chave de recuperação inválida.") from None
    return _restore_global(source, key=key, expected=context, artifact=artifact, target=target, at=at)


def main() -> int:
    """Recuperação manual a partir de arquivo já baixado, em Docker Desktop local."""
    import argparse

    from .postgres_sandbox import DockerPostgresSandbox

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--keyring", type=Path, required=True)
    parser.add_argument("--backup-id", type=UUID, required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--target-container", required=True)
    parser.add_argument("--target-instance", type=UUID, required=True)
    parser.add_argument("--target-database", required=True)
    parser.add_argument("--sandbox-run", type=UUID, required=True)
    args = parser.parse_args()
    try:
        _local_runtime()
        if args.keyring.is_symlink() or not args.keyring.is_file():
            raise BackupRestoreError("Arquivo de recuperação inválido.")
        with args.keyring.open("rb") as f:
            ring = parse_recovery_keyring(f.read(16_385))
        target = DockerPostgresSandbox(args.target_container, args.sandbox_run, args.target_instance,
                                       "restore-target", args.target_database)
        artifact = ArchiveReceipt(args.backup_id, args.size, args.sha256)
        with args.archive.open("rb") as copy:
            receipt = restore_saved_archive(
                copy, keyring=ring, artifact=artifact, expected_schema=args.schema, target=target,
                at=datetime.now(timezone.utc),  # noqa: UP017 -- host Python 3.10
            )
        print(json.dumps({"status": "restore_verified", **asdict(receipt)}, default=str, sort_keys=True))
    except Exception:  # noqa: BLE001 -- somente resultado sanitizado no CLI.
        print(json.dumps({"status": "failed"}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
