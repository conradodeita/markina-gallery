"""Comprova diretórios estruturais de mounts sem extrair a camada do container."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tarfile


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_export(stream, mounts, changes):
    allowed = set()
    for destination in mounts:
        if not destination.startswith("/") or ".." in destination.split("/"):
            raise ValueError("mount_invalido")
        path = destination.rstrip("/")
        while path:
            allowed.add(path)
            path = path.rsplit("/", 1)[0]
    expected = set()
    for line in changes:
        kind, separator, path = line.partition(" ")
        if not separator or kind not in {"A", "C"} or path not in allowed or path in expected:
            raise ValueError("alteracao_fora_de_mount")
        expected.add(path)
    found = set()
    entries, total = 0, 0
    with tarfile.open(fileobj=stream, mode="r|") as archive:
        for member in archive:
            entries += 1
            total += member.size
            if entries > 500_000 or total > 2_000_000_000:
                raise ValueError("export_excessivo")
            path = "/" + member.name.removeprefix("./").lstrip("/").rstrip("/")
            if ".." in path.split("/"):
                raise ValueError("caminho_invalido")
            relevant = path in expected or path in mounts or any(
                path.startswith(destination.rstrip("/") + "/") for destination in mounts
            )
            if relevant and not member.isdir():
                raise ValueError("conteudo_subjacente_nao_preservado")
            if path in expected:
                if path in found:
                    raise ValueError("entrada_duplicada")
                found.add(path)
    if found != expected:
        raise ValueError("diretorio_nao_comprovado")


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"[0-9a-f]{64}", sys.argv[1]):
        raise ValueError("container_invalido")
    container_id = sys.argv[1]
    request = json.load(sys.stdin)

    def snapshot():
        info = json.loads(subprocess.check_output(["docker", "inspect", container_id]))
        if len(info) != 1 or info[0]["Id"] != container_id:
            raise ValueError("container_divergente")
        return {
            "id": container_id,
            "image": info[0]["Image"],
            "mounts": sorted(m["Destination"] for m in info[0]["Mounts"]),
            "changes": sorted(subprocess.check_output(
                ["docker", "diff", container_id], text=True).splitlines()),
        }

    before = snapshot()
    if before["mounts"] != sorted(request["mounts"]) or before["changes"] != sorted(request["changes"]):
        raise ValueError("snapshot_divergente")
    process = subprocess.Popen(["docker", "export", container_id], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    try:
        verify_export(process.stdout, before["mounts"], before["changes"])
        if process.wait(timeout=10) != 0 or snapshot() != before:
            raise ValueError("export_ou_snapshot_divergente")
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
    print(json.dumps({"safe": True, "proof_sha256": fingerprint(before)}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, tarfile.TarError, subprocess.SubprocessError):
        raise SystemExit("facial-restore: camada nao comprovada") from None
