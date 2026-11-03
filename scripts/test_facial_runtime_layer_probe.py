"""Fronteira entre diretórios de mount e conteúdo que seria perdido na troca."""
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facial_runtime_layer_probe import verify_export
from facial_runtime_restoration import RestorationError, digest
from facial_runtime_restoration_host import RestorationHost

MOUNT = "/var/lib/markina/source"
PATHS = ["/var", "/var/lib", "/var/lib/markina", MOUNT]
CHANGES = ["C /var", "C /var/lib", "A /var/lib/markina", "A " + MOUNT]


def archive(extra=None, missing=None):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as output:
        for name in PATHS:
            if name == missing:
                continue
            item = tarfile.TarInfo(name.lstrip("/"))
            item.type = tarfile.DIRTYPE
            output.addfile(item)
        if extra:
            item = tarfile.TarInfo(extra[0].lstrip("/"))
            item.type = extra[1]
            if extra[1] in {tarfile.SYMTYPE, tarfile.LNKTYPE}:
                item.linkname = "/private/data"
            output.addfile(item)
    buffer.seek(0)
    return buffer


def test_empty_mount_directories_are_preservable():
    verify_export(archive(), [MOUNT], CHANGES)


@pytest.mark.parametrize("kind", [tarfile.REGTYPE, tarfile.SYMTYPE, tarfile.LNKTYPE])
def test_hidden_file_or_link_below_mount_is_rejected(kind):
    with pytest.raises(ValueError, match="conteudo_subjacente"):
        verify_export(archive((MOUNT + "/hidden", kind)), [MOUNT], CHANGES)


def test_unrelated_change_remains_blocked():
    with pytest.raises(ValueError, match="alteracao_fora"):
        verify_export(archive(), [MOUNT], CHANGES + ["A /app/unpublished.py"])


def test_missing_directory_is_not_proof():
    with pytest.raises(ValueError, match="diretorio_nao_comprovado"):
        verify_export(archive(missing=MOUNT), [MOUNT], CHANGES)


@pytest.mark.parametrize("mismatch", [False, True])
def test_host_requires_export_proof_bound_to_container_image_mounts_and_diff(mismatch):
    item = {"Id": "a" * 64, "Image": "sha256:" + "b" * 64,
            "Mounts": [{"Destination": MOUNT}]}
    snapshot = {"id": item["Id"], "image": item["Image"],
                "mounts": [MOUNT], "changes": sorted(CHANGES)}
    calls = []

    def command(args, data, timeout):
        calls.append(args)
        if args[:2] == ("docker", "diff"):
            return "\n".join(CHANGES).encode()
        assert args[0] == sys.executable and args[-1] == item["Id"]
        assert json.loads(data) == {"mounts": [MOUNT], "changes": sorted(CHANGES)}
        proof = {"safe": True, "proof_sha256": "0" * 64 if mismatch else digest(snapshot)}
        return json.dumps(proof).encode()

    host = RestorationHost(support_sha="c" * 40, command=command)
    if mismatch:
        with pytest.raises(RestorationError, match="camada_gravavel"):
            host._assert_preserved_layer(item)
    else:
        host._assert_preserved_layer(item)
    assert len(calls) == 2
