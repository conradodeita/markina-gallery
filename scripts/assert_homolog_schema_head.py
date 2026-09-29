#!/usr/bin/env python3
"""Confere que a revisão do banco corresponde ao único head Alembic do checkout."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def migration_heads(directory: Path) -> set[str]:
    revisions: dict[str, set[str]] = {}
    for migration in sorted(directory.glob("*.py")):
        if migration.name == "__init__.py":
            continue
        tree = ast.parse(migration.read_text(encoding="utf-8"), filename=str(migration))
        values: dict[str, object] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
            else:
                continue
            if any(name in {"revision", "down_revision"} for name in names):
                name = next(name for name in names if name in {"revision", "down_revision"})
                values[name] = ast.literal_eval(node.value)

        revision = values.get("revision")
        if not isinstance(revision, str) or not revision:
            raise ValueError(f"revision ausente ou inválida em {migration.name}")
        if revision in revisions:
            raise ValueError(f"revision duplicada: {revision}")
        down_revision = values.get("down_revision")
        if down_revision is None:
            parents: set[str] = set()
        elif isinstance(down_revision, str):
            parents = {down_revision}
        elif isinstance(down_revision, (tuple, list)) and all(
            isinstance(parent, str) for parent in down_revision
        ):
            parents = set(down_revision)
        else:
            raise ValueError(f"down_revision inválida em {migration.name}")
        revisions[revision] = parents

    if not revisions:
        raise ValueError("nenhuma migration encontrada")
    missing = {parent for parents in revisions.values() for parent in parents} - revisions.keys()
    if missing:
        raise ValueError(f"ancestrais de migration ausentes: {', '.join(sorted(missing))}")
    parents = {parent for ancestry in revisions.values() for parent in ancestry}
    return revisions.keys() - parents


def validate_database_revision(directory: Path, database_revision: str) -> str:
    heads = migration_heads(directory)
    if len(heads) != 1:
        raise ValueError(f"esperado um único head Alembic; encontrados {len(heads)}")
    head = next(iter(heads))
    if database_revision != head:
        raise ValueError(f"schema incompatível: banco={database_revision} checkout={head}")
    return head


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    try:
        head = validate_database_revision(args.directory, args.revision.strip())
    except (OSError, SyntaxError, ValueError) as exc:
        print(f"resume-homolog: {exc}", file=sys.stderr)
        return 1
    print(f"revisão Alembic compatível: {head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
