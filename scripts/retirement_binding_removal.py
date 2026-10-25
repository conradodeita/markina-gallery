"""Remove one approved, exclusive InfinitePay binding after the release is healthy."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from retirement_inventory_policy import binding_removal_allowed


def remove_binding(
    approved_inventory: dict[str, Any],
    *,
    runtime_healthy: bool,
    compose_consumers: list[str],
    host_references: list[str],
    target_references: list[str],
    project_root: Path = Path("/opt/markina-gallery"),
) -> tuple[bool, str]:
    approved = approved_inventory.get("binding", {})
    raw_path = approved.get("path")
    if not isinstance(raw_path, str) or "\n" in raw_path or "\r" in raw_path:
        return False, "caminho_binding_invalido"
    path = Path(raw_path)
    root = project_root.resolve()
    try:
        if path.resolve(strict=True) != path or path.parent.resolve(strict=True) != path.parent:
            return False, "binding_ou_diretorio_com_link_simbolico"
        if path.parent != root / "docker" or not path.is_absolute():
            return False, "binding_fora_do_diretorio_aprovado"
        metadata = os.lstat(path)
    except (OSError, RuntimeError):
        return False, "binding_ausente_ou_inacessivel"
    current = {
        "path": str(path),
        "type": "regular_file" if stat.S_ISREG(metadata.st_mode) else "not_regular",
        "symlink": stat.S_ISLNK(metadata.st_mode),
        "mode": format(stat.S_IMODE(metadata.st_mode), "04o"),
        "size_bytes": metadata.st_size,
        "link_count": metadata.st_nlink,
        "mtime_ns": metadata.st_mtime_ns,
        "inode": metadata.st_ino,
        "device": metadata.st_dev,
        "uid": metadata.st_uid,
        "compose_consumers": compose_consumers,
        "host_references": host_references,
        "target_references": target_references,
    }
    allowed, reason = binding_removal_allowed(
        approved_inventory,
        current,
        runtime_healthy=runtime_healthy,
        compose_consumers=compose_consumers,
        host_references=host_references,
        target_references=target_references,
    )
    if not allowed:
        return False, reason
    # Re-read the inode immediately before unlink. The operation removes one
    # directory entry only; it never follows or recursively removes a path.
    try:
        latest = os.lstat(path)
        if (latest.st_dev, latest.st_ino) != (metadata.st_dev, metadata.st_ino):
            return False, "binding_trocado_antes_da_remocao"
        os.unlink(path)
    except OSError:
        return False, "falha_ao_remover_binding"
    if path.exists() or path.is_symlink():
        return False, "binding_ainda_existe_apos_remocao"
    return True, "binding_exclusivo_removido"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-healthy", action="store_true")
    parser.add_argument("--compose-consumers-json", required=True)
    parser.add_argument("--host-references-json", required=True)
    parser.add_argument("--target-references-json", required=True)
    args = parser.parse_args()
    try:
        inventory = json.load(sys.stdin)
        consumers = json.loads(args.compose_consumers_json)
        host_refs = json.loads(args.host_references_json)
        target_refs = json.loads(args.target_references_json)
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("binding_removal=false criterio=json_invalido")
        return 1
    if not all(isinstance(value, list) and all(isinstance(item, str) for item in value)
               for value in (consumers, host_refs, target_refs)):
        print("binding_removal=false criterio=referencias_invalidas")
        return 1
    allowed, reason = remove_binding(
        inventory,
        runtime_healthy=args.runtime_healthy,
        compose_consumers=consumers,
        host_references=host_refs,
        target_references=target_refs,
    )
    print(f"binding_removal={'true' if allowed else 'false'} criterio={reason}")
    return 0 if allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
