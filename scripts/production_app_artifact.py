#!/usr/bin/env python3
"""Cria e valida o bundle imutável de imagens API/web produzido pela CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import struct
import tempfile
from pathlib import Path
from typing import BinaryIO

MAGIC = b"PYP-APP-IMAGE-BUNDLE\0v1\n"
LENGTH = struct.Struct(">I")
MAX_MANIFEST_BYTES = 64 * 1024
MAX_BUNDLE_BYTES = 4 * 1024 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024
MANIFEST_KEYS = {
    "schema_version",
    "target_sha",
    "platform",
    "api_image_ref",
    "web_image_ref",
    "api_base_image_id",
    "api_image_id",
    "web_image_id",
    "image_archive_size",
    "image_archive_sha256",
}


class ArtifactError(ValueError):
    """Bundle ausente, ambíguo ou inconsistente."""


def _sha256(value: str, label: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ArtifactError(f"{label} deve ser SHA-256 hexadecimal completo")
    return value


def _image_id(value: str, label: str) -> str:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ArtifactError(f"ID imutável de {label} inválido")
    return value


def _open_regular(path: Path) -> BinaryIO:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ArtifactError(f"arquivo não pode ser aberto com segurança: {path.name}") from exc
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        os.close(fd)
        raise ArtifactError(f"arquivo não é regular: {path.name}")
    return os.fdopen(fd, "rb")


def _hash_stream(stream: BinaryIO) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while True:
        chunk = stream.read(CHUNK_BYTES)
        if not chunk:
            break
        size += len(chunk)
        digest.update(chunk)
    return digest.hexdigest(), size


def _pairs_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactError("manifesto possui chave duplicada")
        result[key] = value
    return result


def _validate_manifest(value: object, expected_sha: str | None = None) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != MANIFEST_KEYS:
        raise ArtifactError("manifesto ausente, incompleto ou com campos extras")
    manifest = value
    if manifest["schema_version"] != 1 or isinstance(manifest["schema_version"], bool):
        raise ArtifactError("versão de manifesto desconhecida")
    target_sha = manifest["target_sha"]
    if not isinstance(target_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", target_sha):
        raise ArtifactError("SHA de origem inválido")
    if expected_sha is not None and target_sha != expected_sha:
        raise ArtifactError("bundle pertence a outro SHA")
    if manifest["platform"] != "linux/arm64":
        raise ArtifactError("bundle não é linux/arm64")
    if manifest["api_image_ref"] != "markina-gallery-api:latest":
        raise ArtifactError("referência da imagem API diverge")
    if manifest["web_image_ref"] != "markina-gallery-web:latest":
        raise ArtifactError("referência da imagem web diverge")
    api_id = manifest["api_image_id"]
    web_id = manifest["web_image_id"]
    base_id = manifest["api_base_image_id"]
    if not isinstance(base_id, str):
        raise ArtifactError("ID-base API inválido")
    _image_id(base_id, "base API")
    if not isinstance(api_id, str):
        raise ArtifactError("ID da imagem API inválido")
    if not isinstance(web_id, str):
        raise ArtifactError("ID da imagem web inválido")
    _image_id(api_id, "API")
    _image_id(web_id, "web")
    if api_id == web_id:
        raise ArtifactError("imagens API e web não podem ter o mesmo ID")
    archive_size = manifest["image_archive_size"]
    if not isinstance(archive_size, int) or isinstance(archive_size, bool) or archive_size <= 0:
        raise ArtifactError("tamanho do arquivo de imagens inválido")
    if archive_size > MAX_BUNDLE_BYTES:
        raise ArtifactError("arquivo de imagens excede o limite")
    archive_hash = manifest["image_archive_sha256"]
    if not isinstance(archive_hash, str):
        raise ArtifactError("hash do arquivo de imagens inválido")
    _sha256(archive_hash, "hash do arquivo de imagens")
    return manifest


def create_bundle(
    images_path: Path,
    output_path: Path,
    target_sha: str,
    api_base_image_id: str,
    api_image_id: str,
    web_image_id: str,
) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", target_sha):
        raise ArtifactError("SHA alvo inválido")
    _image_id(api_base_image_id, "base API")
    _image_id(api_image_id, "API")
    _image_id(web_image_id, "web")
    if api_image_id == web_image_id:
        raise ArtifactError("imagens API e web não podem ter o mesmo ID")
    with _open_regular(images_path) as images:
        image_hash, image_size = _hash_stream(images)
        if not image_size or image_size > MAX_BUNDLE_BYTES:
            raise ArtifactError("arquivo de imagens vazio ou acima do limite")
        manifest = {
            "schema_version": 1,
            "target_sha": target_sha,
            "platform": "linux/arm64",
            "api_image_ref": "markina-gallery-api:latest",
            "web_image_ref": "markina-gallery-web:latest",
            "api_base_image_id": api_base_image_id,
            "api_image_id": api_image_id,
            "web_image_id": web_image_id,
            "image_archive_size": image_size,
            "image_archive_sha256": image_hash,
        }
        manifest_bytes = json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        if len(manifest_bytes) > MAX_MANIFEST_BYTES:
            raise ArtifactError("manifesto excede o limite")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".app-bundle-", dir=output_path.parent)
        try:
            with os.fdopen(fd, "wb") as bundle:
                bundle.write(MAGIC)
                bundle.write(LENGTH.pack(len(manifest_bytes)))
                bundle.write(manifest_bytes)
                images.seek(0)
                while True:
                    chunk = images.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    bundle.write(chunk)
                bundle.flush()
                os.fsync(bundle.fileno())
            os.replace(temporary, output_path)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
    with _open_regular(output_path) as bundle:
        digest, size = _hash_stream(bundle)
    if size > MAX_BUNDLE_BYTES:
        output_path.unlink(missing_ok=True)
        raise ArtifactError("bundle excede o limite")
    return digest


def verify_bundle(
    bundle_path: Path,
    expected_sha: str,
    expected_bundle_sha256: str,
    expected_api_base_image_id: str | None = None,
    extract_dir: Path | None = None,
) -> tuple[dict[str, object], Path | None]:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise ArtifactError("SHA alvo inválido")
    _sha256(expected_bundle_sha256, "hash do bundle")
    extracted_path: Path | None = None
    with _open_regular(bundle_path) as bundle:
        info = os.fstat(bundle.fileno())
        if info.st_size > MAX_BUNDLE_BYTES:
            raise ArtifactError("bundle excede o limite")
        outer_hash, outer_size = _hash_stream(bundle)
        if outer_hash != expected_bundle_sha256:
            raise ArtifactError("SHA-256 do bundle diverge")
        if outer_size < len(MAGIC) + LENGTH.size:
            raise ArtifactError("bundle truncado")
        bundle.seek(0)
        if bundle.read(len(MAGIC)) != MAGIC:
            raise ArtifactError("formato de bundle desconhecido")
        encoded_length = bundle.read(LENGTH.size)
        if len(encoded_length) != LENGTH.size:
            raise ArtifactError("comprimento do manifesto truncado")
        manifest_length = LENGTH.unpack(encoded_length)[0]
        if not 1 <= manifest_length <= MAX_MANIFEST_BYTES:
            raise ArtifactError("comprimento do manifesto inválido")
        manifest_bytes = bundle.read(manifest_length)
        if len(manifest_bytes) != manifest_length:
            raise ArtifactError("manifesto truncado")
        try:
            value = json.loads(manifest_bytes, object_pairs_hook=_pairs_without_duplicates)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArtifactError("manifesto JSON inválido") from exc
        manifest = _validate_manifest(value, expected_sha)
        if expected_api_base_image_id is not None:
            _image_id(expected_api_base_image_id, "base API esperado")
            if manifest["api_base_image_id"] != expected_api_base_image_id:
                raise ArtifactError("ID-base API diverge do inventário")
        payload_offset = bundle.tell()
        payload_size = outer_size - payload_offset
        if payload_size != manifest["image_archive_size"]:
            raise ArtifactError("tamanho do arquivo de imagens diverge")

        extracted = None
        extracted_digest = hashlib.sha256()
        if extract_dir is not None:
            if not extract_dir.is_dir() or extract_dir.is_symlink():
                raise ArtifactError("diretório de extração não é confiável")
            fd, name = tempfile.mkstemp(prefix=".images-", suffix=".tar.gz", dir=extract_dir)
            extracted = Path(name)
            extracted_path = extracted
            out = os.fdopen(fd, "wb")
        else:
            out = None
        try:
            image_size = 0
            while True:
                chunk = bundle.read(CHUNK_BYTES)
                if not chunk:
                    break
                image_size += len(chunk)
                extracted_digest.update(chunk)
                if out is not None:
                    out.write(chunk)
            if out is not None:
                out.flush()
                os.fsync(out.fileno())
            if image_size != manifest["image_archive_size"]:
                raise ArtifactError("arquivo de imagens truncado")
            if extracted_digest.hexdigest() != manifest["image_archive_sha256"]:
                raise ArtifactError("SHA-256 do arquivo de imagens diverge")
        except BaseException:
            if out is not None:
                out.close()
            if extracted_path is not None:
                extracted_path.unlink(missing_ok=True)
            raise
        if out is not None:
            out.close()
    return manifest, extracted_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--images", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--target-sha", required=True)
    create.add_argument("--api-base-image-id", required=True)
    create.add_argument("--api-image-id", required=True)
    create.add_argument("--web-image-id", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--target-sha", required=True)
    verify.add_argument("--bundle-sha256", required=True)
    verify.add_argument("--api-base-image-id")
    verify.add_argument("--extract-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "create":
            digest = create_bundle(
                args.images, args.output, args.target_sha, args.api_base_image_id,
                args.api_image_id, args.web_image_id,
            )
            print(f"bundle_sha256={digest}")
            print(f"bundle_size={args.output.stat().st_size}")
            return 0
        manifest, extracted = verify_bundle(
            args.bundle, args.target_sha, args.bundle_sha256,
            args.api_base_image_id, args.extract_dir,
        )
        print(f"bundle_sha256={args.bundle_sha256}")
        print(f"api_base_image_id={manifest['api_base_image_id']}")
        print(f"api_image_id={manifest['api_image_id']}")
        print(f"web_image_id={manifest['web_image_id']}")
        print(f"api_image_ref={manifest['api_image_ref']}")
        print(f"web_image_ref={manifest['web_image_ref']}")
        print(f"platform={manifest['platform']}")
        if extracted is not None:
            print(f"image_archive={extracted}")
        return 0
    except (ArtifactError, OSError) as exc:
        parser.exit(1, f"artifact inválido: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
