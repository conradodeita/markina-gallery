"""Normaliza archives Docker/OCI locais sem modificar config ou layers.

Docker clássico identifica imagens pelo config; o store containerd pode expor o
manifest OCI como Id. A prova abaixo vincula os dois digests por bytes e reconstrói
manifests OCI ausentes somente a partir do config e dos layers autenticados do
manifest clássico. Igualdade de RootFS isolada nunca identifica uma imagem.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import re
import stat
import tarfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
BLOB = re.compile(r"blobs/sha256/[0-9a-f]{64}\Z")
MANIFEST_TYPE = "application/vnd.oci.image.manifest.v1+json"
LAYER_TYPE = "application/vnd.oci.image.layer.v1.tar"


class ImageImportError(RuntimeError):
    """Archive/config local divergente ou incompleto."""


def require(value: bool, message: str) -> None:
    if not value:
        raise ImageImportError(message)


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "JSON com campo duplicado.")
        result[key] = value
    return result


def _json(data: bytes):
    try:
        return json.loads(data, object_pairs_hook=_unique)
    except (ValueError, UnicodeError) as exc:
        raise ImageImportError("JSON de imagem inválido.") from exc


@dataclass(frozen=True)
class ImageBinding:
    """Prova pequena; blobs privados ficam fora de repr e dos recibos públicos."""

    source_image: str
    manifest_blob: bytes = field(repr=False)
    config_blob: bytes = field(repr=False)

    @property
    def local_image(self) -> str:
        return digest(self.manifest_blob)

    @property
    def local_tag(self) -> str:
        return "pyp-facial-restore-import:" + self.source_image.removeprefix("sha256:")

    def validate(self) -> None:
        require(bool(ID.fullmatch(self.source_image))
                and digest(self.config_blob) == self.source_image,
                "Config não corresponde à identidade original esperada.")
        manifest, config = _json(self.manifest_blob), _json(self.config_blob)
        require(manifest.get("schemaVersion") == 2
                and manifest.get("mediaType") == MANIFEST_TYPE
                and manifest.get("config", {}).get("digest") == self.source_image
                and manifest["config"].get("size") == len(self.config_blob),
                "Manifest OCI não autentica o config original.")
        require(config.get("architecture") == "arm64" and config.get("os") == "linux"
                and config.get("rootfs", {}).get("type") == "layers",
                "Config não pertence ao runtime Linux ARM64 esperado.")
        layers = manifest.get("layers", [])
        require(bool(layers) and all(x.get("mediaType") == LAYER_TYPE
                                    and ID.fullmatch(x.get("digest", "")) for x in layers)
                and [x["digest"] for x in layers] == config["rootfs"].get("diff_ids"),
                "Layers OCI não correspondem ao RootFS original.")

    def verify_inspect(self, observation: Mapping) -> None:
        """Confere conteúdo/configuração, além do Id devolvido pelo daemon."""
        self.validate()
        config = _json(self.config_blob)
        local_id = observation.get("Id")
        require(local_id in {self.source_image, self.local_image}, "Imagem local não corresponde à prova.")
        if local_id == self.local_image:
            require(observation.get("Descriptor", {}).get("digest") == self.local_image,
                    "Descriptor local não corresponde ao manifest comprovado.")
        require(observation.get("Architecture") == config["architecture"]
                and observation.get("Os") == config["os"]
                and observation.get("Created") == config.get("created")
                and observation.get("Config") == config.get("config")
                and observation.get("RootFS", {}).get("Type") == "layers"
                and observation["RootFS"].get("Layers") == config["rootfs"]["diff_ids"],
                "Config, plataforma ou RootFS local diverge dos bytes originais.")

    def public_record(self) -> dict:
        self.validate()
        return {"source_config_id": self.source_image, "local_manifest_id": self.local_image,
                "local_tag": self.local_tag,
                "layer_count": len(_json(self.manifest_blob)["layers"])}


def normalize_archive(source: Path, destination: Path,
                      expected_config_ids: set[str]) -> dict[str, ImageBinding]:
    """Normaliza nomes locais e completa o índice OCI usando configs/layers provados.

    Nenhum arquivo é extraído e Docker não é invocado. expected_config_ids vem do
    inventário remoto revisado. Um archive não vira evidência confiável apenas
    por declarar IDs esperados: os bytes são conferidos contra esses digests.
    """
    require(bool(expected_config_ids) and all(ID.fullmatch(x) for x in expected_config_ids),
            "Conjunto exato de configs esperados é obrigatório.")
    meta = source.lstat()
    require(stat.S_ISREG(meta.st_mode) and meta.st_nlink == 1,
            "Archive de origem precisa ser arquivo regular exclusivo.")
    require(not destination.exists() and not destination.is_symlink(), "Destino de archive já existe.")
    require(all(not p.is_symlink() and not getattr(p, "is_junction", lambda: False)()
                for p in destination.parents), "Destino atravessa link/junction.")
    with os.fdopen(os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)), "rb") as raw:
        opened = os.fstat(raw.fileno())
        require((meta.st_ino, meta.st_dev) == (opened.st_ino, opened.st_dev), "Archive foi substituído.")
        with tarfile.open(fileobj=raw, mode="r:*") as archive:
            members = archive.getmembers()
            by_name = {m.name: m for m in members}
            require(len(by_name) == len(members), "Archive contém caminhos duplicados.")
            for member in members:
                require(member.isfile() or member.isdir(), "Archive contém link ou entrada especial.")
                require(member.name in {"blobs", "blobs/sha256", "index.json", "manifest.json", "oci-layout"}
                        or bool(BLOB.fullmatch(member.name)), "Archive contém caminho fora do layout OCI.")

            def read_json(name: str) -> bytes:
                member = by_name.get(name)
                require(member is not None and member.isfile() and member.size <= 1_000_000,
                        "Metadata OCI ausente ou excessiva.")
                return archive.extractfile(member).read()

            require(_json(read_json("oci-layout")) == {"imageLayoutVersion": "1.0.0"},
                    "Layout OCI não suportado.")
            index = _json(read_json("index.json"))
            legacy = _json(read_json("manifest.json"))
            require(index.get("schemaVersion") == 2 and isinstance(index.get("manifests"), list)
                    and isinstance(legacy, list) and legacy, "Índice de archive inválido.")
            existing_by_config, descriptors_by_config = {}, {}
            for descriptor in index["manifests"]:
                reference = descriptor.get("digest", "")
                require(bool(ID.fullmatch(reference)) and descriptor.get("mediaType") == MANIFEST_TYPE,
                        "Descriptor OCI inválido.")
                manifest_bytes = read_json("blobs/" + reference.replace(":", "/"))
                require(digest(manifest_bytes) == reference and len(manifest_bytes) == descriptor.get("size"),
                        "Digest/tamanho do manifest OCI divergente.")
                manifest = _json(manifest_bytes)
                config_id = manifest.get("config", {}).get("digest", "")
                require(bool(ID.fullmatch(config_id)) and config_id in expected_config_ids
                        and config_id not in existing_by_config,
                        "Config OCI inválido ou duplicado.")
                config_path = "blobs/" + config_id.replace(":", "/")
                binding = ImageBinding(config_id, manifest_bytes, read_json(config_path))
                binding.validate()
                existing_by_config[config_id] = binding
                descriptors_by_config[config_id] = descriptor

            bindings, by_config_path, seen = {}, {}, set()
            for item in legacy:
                path = item.get("Config")
                require(isinstance(path, str) and BLOB.fullmatch(path) and path not in seen,
                        "Config clássico divergente ou repetido.")
                config_id = "sha256:" + path.rsplit("/", 1)[-1]
                require(config_id in expected_config_ids, "Archive contém config fora da allowlist.")
                config_blob = read_json(path)
                require(digest(config_blob) == config_id, "Digest do config clássico diverge.")
                config = _json(config_blob)
                diff_ids = config.get("rootfs", {}).get("diff_ids")
                layer_paths = item.get("Layers")
                require(isinstance(diff_ids, list) and isinstance(layer_paths, list)
                        and bool(layer_paths) and len(diff_ids) == len(layer_paths),
                        "Layers clássicas não correspondem ao config.")
                layer_descriptors = []
                for layer_path, diff_id in zip(layer_paths, diff_ids, strict=True):
                    require(isinstance(layer_path, str) and BLOB.fullmatch(layer_path)
                            and diff_id == "sha256:" + layer_path.rsplit("/", 1)[-1],
                            "Digest de layer clássico diverge do diff_id do config.")
                    member = by_name.get(layer_path)
                    require(member is not None and member.isfile(), "Layer clássica ausente.")
                    layer_descriptors.append({
                        "mediaType": LAYER_TYPE,
                        "digest": diff_id,
                        "size": member.size,
                    })

                existing = existing_by_config.get(config_id)
                if existing is None:
                    manifest = {
                        "schemaVersion": 2,
                        "mediaType": MANIFEST_TYPE,
                        "config": {
                            "mediaType": "application/vnd.oci.image.config.v1+json",
                            "digest": config_id,
                            "size": len(config_blob),
                        },
                        "layers": layer_descriptors,
                    }
                    manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode()
                    manifest_id = digest(manifest_bytes)
                    manifest_path = "blobs/" + manifest_id.replace(":", "/")
                    prior = by_name.get(manifest_path)
                    if prior is not None:
                        require(prior.isfile()
                                and archive.extractfile(prior).read() == manifest_bytes,
                                "Blob de manifest reconstruído colide com conteúdo existente.")
                else:
                    binding_manifest = _json(existing.manifest_blob)
                    require(item.get("Layers") == [
                        "blobs/" + x["digest"].replace(":", "/")
                        for x in binding_manifest.get("layers", [])
                    ] and binding_manifest["layers"] == layer_descriptors,
                        "Layers clássicas divergem do manifest OCI.")
                    manifest_bytes = existing.manifest_blob

                binding = ImageBinding(config_id, manifest_bytes, config_blob)
                binding.validate()
                bindings[config_id] = binding
                by_config_path[path] = binding
                seen.add(path)
                item["RepoTags"] = [binding.local_tag]
            require(set(bindings) == expected_config_ids,
                    "Archive não contém o conjunto exato de configs esperado.")
            require(set(existing_by_config).issubset(bindings),
                    "Índice OCI referencia config sem manifesto clássico correspondente.")

            normalized_descriptors = []
            for config_id, binding in sorted(bindings.items()):
                descriptor = descriptors_by_config.get(config_id, {
                    "mediaType": MANIFEST_TYPE,
                    "digest": binding.local_image,
                    "size": len(binding.manifest_blob),
                    "platform": {"architecture": "arm64", "os": "linux"},
                })
                require(descriptor.get("digest") == binding.local_image,
                        "Digest do descriptor OCI não corresponde ao manifest.")
                annotations = descriptor.get("annotations")
                if not isinstance(annotations, dict):
                    annotations = {}
                    descriptor["annotations"] = annotations
                annotations.update({
                    "io.containerd.image.name": "docker.io/library/" + binding.local_tag,
                    "org.opencontainers.image.ref.name": binding.local_tag,
                })
                normalized_descriptors.append(descriptor)
            index["manifests"] = normalized_descriptors

            # Verificar todos os blobs, inclusive os não usados diretamente.
            for member in members:
                if not member.isfile() or not BLOB.fullmatch(member.name):
                    continue
                h = hashlib.sha256()
                handle = archive.extractfile(member)
                while chunk := handle.read(1_048_576):
                    h.update(chunk)
                require(h.hexdigest() == member.name.rsplit("/", 1)[1], "Blob corrompido no archive.")
            for binding in bindings.values():
                for layer in _json(binding.manifest_blob)["layers"]:
                    member = by_name.get("blobs/" + layer["digest"].replace(":", "/"))
                    require(member is not None and member.size == layer["size"], "Layer ausente ou truncada.")
            replacements = {
                "index.json": json.dumps(index, separators=(",", ":")).encode(),
                "manifest.json": json.dumps(legacy, separators=(",", ":")).encode(),
            }
            new_blobs = {}
            for binding in bindings.values():
                manifest_path = "blobs/" + binding.local_image.replace(":", "/")
                if manifest_path not in by_name:
                    new_blobs[manifest_path] = binding.manifest_blob
            # Arquivo exclusivo 0600; não sobrescrever outro pacote/backup.
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            with os.fdopen(os.open(destination, flags, 0o600), "wb") as output:
                with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as target:
                    for member in members:
                        header = copy.copy(member)
                        if member.name in replacements:
                            data = replacements[member.name]
                            header.size = len(data)
                            target.addfile(header, io.BytesIO(data))
                        else:
                            target.addfile(header, archive.extractfile(member) if member.isfile() else None)
                    for name, data in new_blobs.items():
                        header = tarfile.TarInfo(name)
                        header.size = len(data)
                        header.mode = 0o644
                        target.addfile(header, io.BytesIO(data))
                output.flush()
                os.fsync(output.fileno())
    after = source.lstat()
    require((meta.st_dev, meta.st_ino, meta.st_size, meta.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            "Archive de origem mudou durante a normalização.")
    return bindings
