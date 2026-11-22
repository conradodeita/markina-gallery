"""Find local Compose references to the retired binding without exposing file contents."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path


COMPOSE_NAMES = ("docker-compose", "compose")
COMPOSE_SUFFIXES = (".yml", ".yaml")


def _is_compose_file(name: str) -> bool:
    lowered = name.lower()
    return any(lowered.startswith(prefix) for prefix in COMPOSE_NAMES) and lowered.endswith(COMPOSE_SUFFIXES)


def find_references(target: str, roots: list[Path]) -> list[str]:
    """Return matching config paths; abort on any incomplete scan."""
    target_bytes = os.fsencode(target)
    basename_bytes = os.fsencode(Path(target).name)
    variable_bytes = b"INFINITEPAY_BINDINGS_ENV_FILE"
    references: list[str] = []
    visited_directories: set[tuple[int, int]] = set()

    def onerror(error: OSError) -> None:
        raise error

    for root in roots:
        try:
            root.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise OSError(f"não foi possível verificar raiz de configuração: {root}") from error
        if root.is_symlink() or not root.is_dir() or not os.access(root, os.R_OK | os.X_OK):
            raise PermissionError(f"raiz de configuração inacessível: {root}")
        for directory, directories, names in os.walk(root, onerror=onerror, followlinks=True):
            current = Path(directory)
            try:
                info = current.stat()
            except OSError as error:
                raise OSError(f"não foi possível verificar diretório: {current}") from error
            identity = (info.st_dev, info.st_ino)
            if identity in visited_directories:
                directories[:] = []
                continue
            visited_directories.add(identity)
            for name in directories[:]:
                child = current / name
                try:
                    child_info = child.stat()
                except OSError as error:
                    raise OSError(f"não foi possível verificar diretório: {child}") from error
                if not stat.S_ISDIR(child_info.st_mode):
                    directories.remove(name)
                    continue
                if (child_info.st_dev, child_info.st_ino) in visited_directories:
                    directories.remove(name)
            for name in names:
                if not _is_compose_file(name):
                    continue
                path = Path(directory) / name
                try:
                    content = path.read_bytes()
                except OSError as error:
                    raise OSError(f"não foi possível verificar configuração: {path}") from error
                if target_bytes in content or basename_bytes in content or variable_bytes in content:
                    references.append(str(path))
    return sorted(set(references))


def find_container_references(target: str, records: list[dict[str, object]]) -> list[str]:
    """Return non-Markina containers with an exact bind mount source."""
    references: list[str] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {"name", "project", "mounts"}:
            raise ValueError("inspeção Docker incompleta")
        name, project, mounts = record["name"], record["project"], record["mounts"]
        if not isinstance(name, str) or not isinstance(project, str) or not isinstance(mounts, list):
            raise ValueError("metadados Docker inválidos")
        if project == "markina-gallery":
            continue
        for mount in mounts:
            if not isinstance(mount, dict) or not isinstance(mount.get("Type"), str):
                raise ValueError("mount Docker inválido")
            if mount["Type"] == "bind":
                source = mount.get("Source")
                if not isinstance(source, str):
                    raise ValueError("origem de mount bind ausente")
                if source == target:
                    references.append(f"container:{name.lstrip('/')}")
                    break
    return sorted(set(references))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--roots", nargs="*")
    parser.add_argument("--container-inspect", action="store_true")
    args = parser.parse_args()
    try:
        if args.container_inspect:
            records = []
            for line in sys.stdin:
                mounts, name, project = line.rstrip("\n").split("|", 2)
                records.append({"mounts": json.loads(mounts), "name": name, "project": project})
            references = find_container_references(args.target, records)
        else:
            if not args.roots:
                raise ValueError("raízes de configuração não informadas")
            references = find_references(args.target, [Path(root) for root in args.roots])
    except OSError as error:
        print(f"varredura_de_referencias_incompleta: {error}", file=sys.stderr)
        return 2
    except (ValueError, json.JSONDecodeError) as error:
        print(f"inspecao_docker_incompleta: {error}", file=sys.stderr)
        return 2
    for reference in references:
        print(reference)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
