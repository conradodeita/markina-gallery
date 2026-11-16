"""Confere o runtime privado do helper usando apenas a biblioteca padrão."""

import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

from scripts.wildcard_operational_files import _directory, _private_directory, _read


def load_runtime(root: Path):
    directory = _private_directory(root)
    try:
        manifest = json.loads(_read(directory, "runtime-manifest.json", 262144))
    finally:
        os.close(directory)
    if (
        not isinstance(manifest, dict)
        or not 1 <= len(manifest) <= 1024
        or any(
            not isinstance(path, str)
            or not path.startswith("lib/")
            or not re.fullmatch(r"[A-Za-z0-9_./-]+", path)
            or ".." in PurePosixPath(path).parts
            or "//" in path
            or not isinstance(value, str)
            or not re.fullmatch("[0-9a-f]{64}", value)
            for path, value in manifest.items()
        )
    ):
        raise RuntimeError("runtime_manifest_invalid")
    actual = set()
    for directory, dirs, files in os.walk(root / "lib", followlinks=False):
        for name in dirs:
            if (Path(directory) / name).is_symlink():
                raise RuntimeError("runtime_link_invalid")
        for name in files:
            actual.add((Path(directory) / name).relative_to(root).as_posix())
    if actual != set(manifest):
        raise RuntimeError("runtime_inventory_changed")
    for name, expected in manifest.items():
        path = root / name
        fd = _directory(path.parent)
        try:
            content = _read(fd, path.name, 20971520, public=True, allow_empty=True)
        finally:
            os.close(fd)
        if hashlib.sha256(content).hexdigest() != expected:
            raise RuntimeError("runtime_changed")
    sys.path.insert(0, str(root / "lib"))
