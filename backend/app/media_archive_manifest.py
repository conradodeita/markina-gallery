"""Manifesto canônico e resolução tenant-scoped de fontes do arquivo frio."""

from __future__ import annotations

import json
import os
import re
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import historical_media
from app import media as media_storage
from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    CommercialHistoryMedia,
    MediaArchiveCycle,
    MediaArchiveObject,
    MediaArchiveOperation,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PreviewAdjustment,
    SaleOrder,
    SaleOrderItem,
)
from app.media_archive_guards import isolated_closure_cover_folder, never_released_closure_folder


class MediaArchiveSourceError(RuntimeError):
    """Uma fonte esperada está ausente, alterada ou fora do namespace permitido."""


class MediaArchiveManifestError(ValueError):
    """O manifesto não corresponde ao contrato canônico V1."""


_UUID_PART = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_SOURCE_REF = re.compile(
    rf"(?:photo:{_UUID_PART}:original|"
    rf"derivative:{_UUID_PART}|"
    rf"cover:{_UUID_PART}:admin_preview|"
    rf"adjustment:{_UUID_PART}:{_UUID_PART}:(?:legacy|tenant)|"
    rf"commercial:{_UUID_PART}:(?:preview|delivery))"
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_REMOTE_ID = re.compile(r"[A-Za-z0-9_-]{1,256}")
_MAX_BIGINT = (2**63) - 1
_OBJECT_TYPES = frozenset({
    "source", "derivative", "commercial_media", "cover_asset", "cover_thumbnail", "manifest",
})
_MANIFEST_KEYS = frozenset({
    "schema_version", "tenant_id", "parent_gallery_id", "folder_id", "cycle_id",
    "operation_id", "created_at", "object_count", "total_bytes", "objects",
})
_OBJECT_KEYS = frozenset({
    "object_id", "source_ref", "object_type", "mime_type", "size_bytes", "sha256",
    "remote_object_id",
})


@dataclass(frozen=True)
class ArchiveSource:
    """Arquivo local resolvido sem incluir seu caminho no manifesto."""

    source_ref: str
    object_type: str
    mime_type: str
    path: Path
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class _SourceCandidate:
    source_ref: str
    object_type: str
    root: Path
    relative_key: str
    validated_path: Path
    expected_sha256: str | None = None


def _canonical_uuid(value: object) -> str:
    if not isinstance(value, str):
        raise MediaArchiveManifestError("UUID inválido no manifesto.")
    try:
        result = str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise MediaArchiveManifestError("UUID inválido no manifesto.") from exc
    if result != value:
        raise MediaArchiveManifestError("UUID não canônico no manifesto.")
    return result


def _validate_source_ref(value: object) -> str:
    if not isinstance(value, str) or len(value) > 255 or not _SOURCE_REF.fullmatch(value):
        raise MediaArchiveManifestError("Referência de origem não permitida.")
    return value


def _utc_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise MediaArchiveManifestError("Timestamp deve estar em UTC canônico.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise MediaArchiveManifestError("Timestamp inválido no manifesto.") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
        raise MediaArchiveManifestError("Timestamp deve estar em UTC canônico.")
    canonical = parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    if canonical != value:
        raise MediaArchiveManifestError("Timestamp não canônico no manifesto.")
    return canonical


def canonical_manifest_bytes(manifest: object) -> tuple[bytes, str]:
    """Valida V1, rejeita campos fora do contrato e devolve JSON canônico + SHA-256."""
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_KEYS:
        raise MediaArchiveManifestError("Formato de manifesto inválido.")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise MediaArchiveManifestError("Versão de manifesto não suportada.")
    for field in ("tenant_id", "parent_gallery_id", "folder_id", "cycle_id", "operation_id"):
        _canonical_uuid(manifest[field])
    _utc_timestamp(manifest["created_at"])
    objects = manifest["objects"]
    if not isinstance(objects, list):
        raise MediaArchiveManifestError("Lista de objetos inválida.")

    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    seen_remote_ids: set[str] = set()
    ordered_ids: list[str] = []
    total_bytes = 0
    for item in objects:
        if not isinstance(item, dict) or set(item) != _OBJECT_KEYS:
            raise MediaArchiveManifestError("Formato de objeto inválido.")
        object_id = _canonical_uuid(item["object_id"])
        source_ref = _validate_source_ref(item["source_ref"])
        if object_id in seen_ids or source_ref in seen_sources:
            raise MediaArchiveManifestError("Objeto duplicado no manifesto.")
        seen_ids.add(object_id)
        seen_sources.add(source_ref)
        ordered_ids.append(object_id)
        object_type = item["object_type"]
        if not isinstance(object_type, str) or object_type not in _OBJECT_TYPES or object_type == "manifest":
            raise MediaArchiveManifestError("Tipo de objeto não permitido no manifesto.")
        if item["mime_type"] != "image/jpeg":
            raise MediaArchiveManifestError("Tipo de mídia não permitido no manifesto.")
        size_bytes = item["size_bytes"]
        if type(size_bytes) is not int or size_bytes <= 0 or size_bytes > _MAX_BIGINT:
            raise MediaArchiveManifestError("Tamanho de objeto inválido.")
        digest = item["sha256"]
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise MediaArchiveManifestError("Checksum de objeto inválido.")
        remote_id = item["remote_object_id"]
        if not isinstance(remote_id, str) or not _REMOTE_ID.fullmatch(remote_id):
            raise MediaArchiveManifestError("Identificador remoto inválido.")
        if remote_id in seen_remote_ids:
            raise MediaArchiveManifestError("Identificador remoto duplicado.")
        seen_remote_ids.add(remote_id)
        total_bytes += size_bytes
        if total_bytes > _MAX_BIGINT:
            raise MediaArchiveManifestError("Total de bytes excede a capacidade do catálogo.")

    if ordered_ids != sorted(ordered_ids):
        raise MediaArchiveManifestError("Objetos fora da ordem canônica.")
    if type(manifest["object_count"]) is not int or manifest["object_count"] != len(objects):
        raise MediaArchiveManifestError("Contagem de objetos divergente.")
    if type(manifest["total_bytes"]) is not int or manifest["total_bytes"] != total_bytes:
        raise MediaArchiveManifestError("Total de bytes divergente.")

    try:
        encoded = json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise MediaArchiveManifestError("Manifesto não pode ser serializado canonicamente.") from exc
    return encoded, sha256(encoded).hexdigest()


def parse_canonical_manifest(raw: bytes) -> tuple[dict, str]:
    """Analisa bytes V1 e exige que a representação recebida já seja canônica."""
    if not isinstance(raw, bytes):
        raise MediaArchiveManifestError("Manifesto deve ser recebido como bytes.")

    def reject_duplicate_keys(pairs):
        parsed = {}
        for key, value in pairs:
            if key in parsed:
                raise MediaArchiveManifestError("Chave JSON duplicada no manifesto.")
            parsed[key] = value
        return parsed

    def reject_nonfinite(_value):
        raise MediaArchiveManifestError("Número não finito no manifesto.")

    try:
        manifest = json.loads(
            raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MediaArchiveManifestError("JSON de manifesto inválido.") from exc
    canonical, digest = canonical_manifest_bytes(manifest)
    if canonical != raw:
        raise MediaArchiveManifestError("Manifesto não está na forma canônica.")
    return manifest, digest


def _ref(prefix: str, identifier: UUID) -> str:
    return f"{prefix}:{identifier}"


def _candidate(
    source_ref: str,
    object_type: str,
    root: Path,
    relative_key: str,
    validated_path: Path,
    *,
    expected_sha256: str | None = None,
) -> _SourceCandidate:
    _validate_source_ref(source_ref)
    if object_type not in _OBJECT_TYPES or object_type == "manifest":
        raise MediaArchiveSourceError("Tipo de fonte não permitido.")
    return _SourceCandidate(
        source_ref=source_ref,
        object_type=object_type,
        root=root.resolve(),
        relative_key=relative_key,
        validated_path=validated_path,
        expected_sha256=expected_sha256,
    )


def _measure(candidate: _SourceCandidate) -> ArchiveSource:
    key = candidate.relative_key
    posix_key = PurePosixPath(key)
    if (
        not key or "\\" in key or posix_key.is_absolute()
        or any(part in {"", ".", ".."} for part in posix_key.parts)
    ):
        raise MediaArchiveSourceError("Fonte fora do armazenamento permitido.")

    root = candidate.root.resolve()
    current = root
    try:
        for part in posix_key.parts:
            current = current / part
            if current.is_symlink():
                raise MediaArchiveSourceError("Fonte com componente simbólico não permitida.")
        path = current.resolve(strict=True)
        path.relative_to(root)
        if path != candidate.validated_path.resolve(strict=True):
            raise MediaArchiveSourceError("Fonte local divergente.")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
    except MediaArchiveSourceError:
        raise
    except (OSError, ValueError) as exc:
        raise MediaArchiveSourceError("Fonte local indisponível ou inválida.") from exc

    digest = sha256()
    byte_count = 0
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise MediaArchiveSourceError("Fonte não é um arquivo regular.")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = -1
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                byte_count += len(block)
            after = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(after.st_mode)
            or byte_count <= 0
            or before.st_size != byte_count
            or after.st_size != byte_count
            or before.st_mtime_ns != after.st_mtime_ns
        ):
            raise MediaArchiveSourceError("Fonte foi alterada durante a leitura.")
    except MediaArchiveSourceError:
        raise
    except OSError as exc:
        raise MediaArchiveSourceError("Falha ao ler fonte local.") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    checksum = digest.hexdigest()
    if candidate.expected_sha256 and checksum != candidate.expected_sha256:
        raise MediaArchiveSourceError("Fonte diverge do checksum comercial registrado.")
    return ArchiveSource(
        source_ref=candidate.source_ref,
        object_type=candidate.object_type,
        mime_type="image/jpeg",
        path=path,
        size_bytes=byte_count,
        sha256=checksum,
    )


def _latest_folder_state(tenant_id: UUID):
    return (
        select(MediaArchiveCycle.state)
        .where(
            MediaArchiveCycle.tenant_id == tenant_id,
            MediaArchiveCycle.folder_id == PhotoFolder.id,
        )
        .order_by(MediaArchiveCycle.cycle_number.desc())
        .limit(1)
        .correlate(PhotoFolder)
        .scalar_subquery()
    )


def _cover_photo(db: Session, gallery: ParentGallery) -> PhotoAsset | None:
    if gallery.cover_photo_id:
        selected = db.scalar(select(PhotoAsset).where(
            PhotoAsset.id == gallery.cover_photo_id,
            PhotoAsset.tenant_id == gallery.tenant_id,
            PhotoAsset.parent_gallery_id == gallery.id,
        ))
        if selected:
            return selected
    return db.scalar(
        select(PhotoAsset)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .join(MediaDerivative, MediaDerivative.photo_asset_id == PhotoAsset.id)
        .where(
            PhotoAsset.tenant_id == gallery.tenant_id,
            PhotoAsset.parent_gallery_id == gallery.id,
            PhotoAsset.derived_gallery_id.is_(None),
            PhotoFolder.tenant_id == gallery.tenant_id,
            PhotoFolder.purpose == "content",
            MediaDerivative.tenant_id == gallery.tenant_id,
            MediaDerivative.variant == "client_preview",
            MediaDerivative.status == "ready",
        )
        .order_by(PhotoFolder.position, PhotoAsset.created_at, PhotoAsset.filename)
        .limit(1)
    )


def _candidate_sources(
    db: Session,
    *,
    tenant_id: UUID,
    parent_gallery_id: UUID,
    folder_id: UUID,
) -> list[_SourceCandidate]:
    require_active_owner(db, tenant_id)
    folder = owned_record(db, PhotoFolder, folder_id, tenant_id=tenant_id)
    gallery = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
    if (
        not folder or not gallery or gallery.lifecycle_status != "active"
        or folder.parent_gallery_id != gallery.id
        or (not isolated_closure_cover_folder(db, folder)
            and (folder.purpose != "content"
                 or (folder.status != "released" and not never_released_closure_folder(db, folder))))
    ):
        raise MediaArchiveSourceError("Pasta de origem indisponível.")

    other_local_folder = db.scalar(
        select(PhotoFolder.id)
        .where(
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.parent_gallery_id == parent_gallery_id,
            PhotoFolder.purpose == "content",
            PhotoFolder.id != folder_id,
            or_(
                _latest_folder_state(tenant_id).is_(None),
                _latest_folder_state(tenant_id).not_in(("archived", "deleted")),
            ),
        )
        .limit(1)
    )
    include_shared_cover_assets = other_local_folder is None
    cover = _cover_photo(db, gallery)

    folder_ids = [folder_id]
    cover_assets_folder = None
    if include_shared_cover_assets:
        cover_assets_folder = db.scalar(select(PhotoFolder).where(
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.parent_gallery_id == parent_gallery_id,
            PhotoFolder.purpose == "cover_assets",
            PhotoFolder.derived_gallery_id.is_(None),
        ))
        if cover_assets_folder:
            folder_ids.append(cover_assets_folder.id)

    photos = list(db.scalars(
        select(PhotoAsset)
        .where(
            PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.parent_gallery_id == parent_gallery_id,
            PhotoAsset.folder_id.in_(folder_ids),
        )
        .order_by(PhotoAsset.id)
    ))
    photo_ids = [photo.id for photo in photos]
    photo_by_id = {photo.id: photo for photo in photos}
    candidates: list[_SourceCandidate] = []

    for photo in photos:
        photo_folder = folder if photo.folder_id == folder.id else cover_assets_folder
        if not photo_folder or photo.parent_gallery_id != photo_folder.parent_gallery_id:
            raise MediaArchiveSourceError("Foto fora da pasta autorizada.")
        try:
            path = media_storage.safe_source_path(photo)
        except (ValueError, OSError) as exc:
            raise MediaArchiveSourceError("Origem JPEG inválida.") from exc
        candidates.append(_candidate(
            _ref("photo", photo.id) + ":original",
            "cover_asset" if photo_folder.purpose == "cover_assets" else "source",
            media_storage.source_root(), photo.storage_key, path,
        ))

    derivatives = list(db.scalars(
        select(MediaDerivative)
        .where(
            MediaDerivative.tenant_id == tenant_id,
            MediaDerivative.photo_asset_id.in_(photo_ids),
            MediaDerivative.relative_path.is_not(None),
        )
        .order_by(MediaDerivative.id)
    )) if photo_ids else []
    selected_cover_derivative_id = None
    if cover and include_shared_cover_assets:
        selected_cover_derivative_id = db.scalar(select(MediaDerivative.id).where(
            MediaDerivative.tenant_id == tenant_id,
            MediaDerivative.photo_asset_id == cover.id,
            MediaDerivative.variant == "admin_preview",
            MediaDerivative.status == "ready",
            MediaDerivative.relative_path.is_not(None),
        ))

    for derivative in derivatives:
        photo = photo_by_id.get(derivative.photo_asset_id)
        if not photo:
            raise MediaArchiveSourceError("Derivado sem foto de origem autorizada.")
        relative_path = derivative.relative_path or ""
        modern_prefix = f"tenants/{tenant_id}/photos/{photo.id}/"
        legacy_prefix = f"{photo.id}/"
        if not relative_path.startswith((modern_prefix, legacy_prefix)):
            raise MediaArchiveSourceError("Derivado fora do diretório da foto autorizada.")
        if cover and photo.id == cover.id and derivative.variant == "admin_preview":
            # A capa configurada é preservada até que a última pasta de conteúdo arquive.
            continue
        try:
            path = media_storage.safe_derivative_path(derivative)
        except (ValueError, OSError) as exc:
            raise MediaArchiveSourceError("Derivado local inválido.") from exc
        candidates.append(_candidate(
            _ref("derivative", derivative.id), "derivative",
            media_storage.derivatives_root(), derivative.relative_path or "", path,
        ))

    from app.preview_adjustment.cleanup import photo_files
    from app.preview_adjustment.service import result_path

    for photo in photos:
        try:
            adjustment_paths = sorted(
                photo_files(photo.id, tenant_id=tenant_id), key=lambda item: item.as_posix(),
            )
        except (ValueError, OSError) as exc:
            raise MediaArchiveSourceError("Derivados de ajuste inválidos.") from exc
        adjustment_sources: set[str] = set()
        root = media_storage.derivatives_root()
        for path in adjustment_paths:
            try:
                relative_key = path.relative_to(root).as_posix()
                token = str(UUID(path.stem))
                legacy = not relative_key.startswith(f"tenants/{tenant_id}/")
                expected_path = result_path(
                    photo.id, token, tenant_id=tenant_id, legacy=legacy,
                )
                if expected_path.resolve(strict=True) != path.resolve(strict=True):
                    raise ValueError
            except (OSError, ValueError) as exc:
                raise MediaArchiveSourceError("Derivado de ajuste fora do formato autorizado.") from exc
            reference = f"adjustment:{photo.id}:{token}:{'legacy' if legacy else 'tenant'}"
            adjustment_sources.add(reference)
            candidates.append(_candidate(
                reference, "derivative", root, relative_key, path,
            ))

        adjustment = db.get(PreviewAdjustment, photo.id)
        if adjustment and adjustment.tenant_id != tenant_id:
            raise MediaArchiveSourceError("Ajuste fora do tenant autorizado.")
        if adjustment and adjustment.relative_path:
            from app.preview_adjustment.service import existing_result

            if existing_result(adjustment) is None:
                raise MediaArchiveSourceError("Ajuste registrado sem arquivo local íntegro.")
            expected_token = str(UUID(Path(adjustment.relative_path).stem))
            legacy = not adjustment.relative_path.startswith(f"tenants/{tenant_id}/")
            expected_ref = f"adjustment:{photo.id}:{expected_token}:{'legacy' if legacy else 'tenant'}"
            if expected_ref not in adjustment_sources:
                raise MediaArchiveSourceError("Ajuste registrado não foi incluído no pacote.")

    history_query = (
        select(CommercialHistoryMedia, SaleOrderItem)
        .join(
            SaleOrderItem,
            (SaleOrderItem.id == CommercialHistoryMedia.sale_order_item_id)
            & (SaleOrderItem.tenant_id == CommercialHistoryMedia.tenant_id),
        )
        .join(
            SaleOrder,
            (SaleOrder.id == SaleOrderItem.sale_order_id)
            & (SaleOrder.tenant_id == SaleOrderItem.tenant_id),
        )
        .where(
            CommercialHistoryMedia.tenant_id == tenant_id,
            SaleOrderItem.tenant_id == tenant_id,
            SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
            or_(
                SaleOrderItem.folder_id_snapshot.in_(folder_ids),
                SaleOrderItem.photo_asset_id_snapshot.in_(photo_ids),
            ),
        )
        .order_by(CommercialHistoryMedia.id)
    ) if folder_ids else None
    for history, item in db.execute(history_query) if history_query is not None else ():
        if history.media_type not in {None, "image/jpeg"}:
            raise MediaArchiveSourceError("Mídia comercial tem tipo não suportado.")
        if history.preview_storage_key:
            try:
                path = historical_media.historical_media_path(
                    history.preview_storage_key, tenant_id=tenant_id, item_id=item.id,
                )
            except (ValueError, OSError) as exc:
                raise MediaArchiveSourceError("Mídia comercial fora do armazenamento autorizado.") from exc
            candidates.append(_candidate(
                f"commercial:{history.id}:preview", "commercial_media",
                historical_media.history_root(), history.preview_storage_key, path,
                expected_sha256=history.checksum_sha256,
            ))
        if history.delivery_storage_key:
            try:
                path = historical_media.historical_media_path(
                    history.delivery_storage_key, tenant_id=tenant_id, item_id=item.id,
                )
            except (ValueError, OSError) as exc:
                raise MediaArchiveSourceError("Mídia comercial fora do armazenamento autorizado.") from exc
            candidates.append(_candidate(
                f"commercial:{history.id}:delivery", "commercial_media",
                historical_media.history_root(), history.delivery_storage_key, path,
                expected_sha256=item.checksum_sha256_snapshot,
            ))

    if include_shared_cover_assets and cover and selected_cover_derivative_id:
        derivative = db.scalar(select(MediaDerivative).where(
            MediaDerivative.id == selected_cover_derivative_id,
            MediaDerivative.tenant_id == tenant_id,
            MediaDerivative.photo_asset_id == cover.id,
        ))
        if derivative and derivative.relative_path:
            try:
                path = media_storage.safe_derivative_path(derivative)
            except (ValueError, OSError) as exc:
                raise MediaArchiveSourceError("Derivada de capa indisponível.") from exc
            candidates.append(_candidate(
                f"cover:{cover.id}:admin_preview", "cover_thumbnail",
                media_storage.derivatives_root(), derivative.relative_path, path,
            ))

    refs = [item.source_ref for item in candidates]
    if len(refs) != len(set(refs)):
        raise MediaArchiveSourceError("Fontes duplicadas no pacote de arquivo.")
    return sorted(candidates, key=lambda item: item.source_ref)


def resolve_archive_sources(
    db: Session,
    *,
    tenant_id: UUID,
    parent_gallery_id: UUID,
    folder_id: UUID,
) -> list[ArchiveSource]:
    """Resolve e mede todas as fontes locais permitidas para o próximo ciclo."""
    candidates = _candidate_sources(
        db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id, folder_id=folder_id,
    )
    return [_measure(item) for item in candidates]


def resolve_archive_source_ref(
    db: Session,
    *,
    tenant_id: UUID,
    parent_gallery_id: UUID,
    folder_id: UUID,
    source_ref: str,
) -> ArchiveSource:
    """Resolve uma referência conhecida sem jamais aceitar caminho do chamador."""
    _validate_source_ref(source_ref)
    candidates = _candidate_sources(
        db, tenant_id=tenant_id, parent_gallery_id=parent_gallery_id, folder_id=folder_id,
    )
    match = next((item for item in candidates if item.source_ref == source_ref), None)
    if not match:
        raise MediaArchiveSourceError("Referência de origem indisponível.")
    return _measure(match)


def resolve_archive_target_path(
    db: Session,
    *,
    tenant_id: UUID,
    parent_gallery_id: UUID,
    folder_id: UUID,
    source_ref: str,
    object_type: str,
) -> Path:
    """Reconstrói destino local a partir do banco e de uma referência enumerada.

    Diferente de `resolve_archive_source_ref`, o destino pode ainda não existir:
    isso permite retomar cleanup parcial sem persistir caminhos absolutos.
    """
    _validate_source_ref(source_ref)
    if object_type not in _OBJECT_TYPES or object_type == "manifest":
        raise MediaArchiveSourceError("Tipo de destino não permitido.")
    folder = owned_record(db, PhotoFolder, folder_id, tenant_id=tenant_id)
    gallery = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
    if (
        not folder or not gallery or gallery.lifecycle_status != "active"
        or folder.parent_gallery_id != gallery.id
        or (folder.purpose != "content" and not isolated_closure_cover_folder(db, folder))
    ):
        raise MediaArchiveSourceError("Pasta de destino indisponível.")

    cover_folder_id = db.scalar(select(PhotoFolder.id).where(
        PhotoFolder.tenant_id == tenant_id,
        PhotoFolder.parent_gallery_id == parent_gallery_id,
        PhotoFolder.purpose == "cover_assets",
        PhotoFolder.derived_gallery_id.is_(None),
    ))
    allowed_folder_ids = {folder_id}
    if cover_folder_id:
        allowed_folder_ids.add(cover_folder_id)

    def _photo(photo_id: UUID) -> PhotoAsset:
        photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
        if (
            not photo or photo.parent_gallery_id != parent_gallery_id
            or photo.folder_id not in allowed_folder_ids
        ):
            raise MediaArchiveSourceError("Foto fora do escopo do ciclo.")
        return photo

    root: Path
    relative_key: str
    photo_match = re.fullmatch(rf"photo:({_UUID_PART}):original", source_ref)
    derivative_match = re.fullmatch(rf"derivative:({_UUID_PART})", source_ref)
    cover_match = re.fullmatch(rf"cover:({_UUID_PART}):admin_preview", source_ref)
    adjustment_match = re.fullmatch(
        rf"adjustment:({_UUID_PART}):({_UUID_PART}):(legacy|tenant)", source_ref,
    )
    commercial_match = re.fullmatch(
        rf"commercial:({_UUID_PART}):(preview|delivery)", source_ref,
    )

    if photo_match:
        photo = _photo(UUID(photo_match.group(1)))
        if object_type == "cover_asset":
            if photo.folder_id != cover_folder_id:
                raise MediaArchiveSourceError("Ativo técnico fora do escopo do ciclo.")
        elif object_type != "source" or photo.folder_id != folder_id:
            raise MediaArchiveSourceError("Original fora do escopo do ciclo.")
        root, relative_key = media_storage.source_root(), photo.storage_key
        media_storage.media_namespace(relative_key, tenant_id)
    elif derivative_match:
        if object_type != "derivative":
            raise MediaArchiveSourceError("Derivado incompatível com a referência.")
        derivative = owned_record(
            db, MediaDerivative, UUID(derivative_match.group(1)), tenant_id=tenant_id,
        )
        if not derivative or not derivative.relative_path:
            raise MediaArchiveSourceError("Derivado indisponível.")
        photo = _photo(derivative.photo_asset_id)
        prefix = (f"tenants/{tenant_id}/photos/{photo.id}/", f"{photo.id}/")
        if not derivative.relative_path.startswith(prefix):
            raise MediaArchiveSourceError("Derivado fora do diretório da foto.")
        root, relative_key = media_storage.derivatives_root(), derivative.relative_path
        media_storage.media_namespace(relative_key, tenant_id)
    elif cover_match:
        if object_type != "cover_thumbnail":
            raise MediaArchiveSourceError("Miniatura incompatível com a referência.")
        cover = _cover_photo(db, gallery)
        if not cover or cover.id != UUID(cover_match.group(1)):
            raise MediaArchiveSourceError("Miniatura não corresponde à capa atual.")
        derivative = db.scalar(select(MediaDerivative).where(
            MediaDerivative.tenant_id == tenant_id,
            MediaDerivative.photo_asset_id == cover.id,
            MediaDerivative.variant == "admin_preview",
            MediaDerivative.status == "ready",
        ))
        if not derivative or not derivative.relative_path:
            raise MediaArchiveSourceError("Miniatura de capa indisponível.")
        root, relative_key = media_storage.derivatives_root(), derivative.relative_path
        media_storage.media_namespace(relative_key, tenant_id)
    elif adjustment_match:
        if object_type != "derivative":
            raise MediaArchiveSourceError("Ajuste incompatível com a referência.")
        photo = _photo(UUID(adjustment_match.group(1)))
        from app.preview_adjustment.service import result_path

        candidate = result_path(
            photo.id,
            adjustment_match.group(2),
            tenant_id=tenant_id,
            legacy=adjustment_match.group(3) == "legacy",
        )
        root = media_storage.derivatives_root()
        relative_key = candidate.relative_to(root).as_posix()
        media_storage.media_namespace(relative_key, tenant_id)
    elif commercial_match:
        if object_type != "commercial_media":
            raise MediaArchiveSourceError("Mídia comercial incompatível com a referência.")
        history = owned_record(
            db, CommercialHistoryMedia, UUID(commercial_match.group(1)), tenant_id=tenant_id,
        )
        if not history:
            raise MediaArchiveSourceError("Mídia comercial fora do escopo do ciclo.")
        item = db.scalar(
            select(SaleOrderItem)
            .join(
                SaleOrder,
                (SaleOrder.id == SaleOrderItem.sale_order_id)
                & (SaleOrder.tenant_id == SaleOrderItem.tenant_id),
            )
            .where(
                SaleOrderItem.id == history.sale_order_item_id,
                SaleOrderItem.tenant_id == tenant_id,
                SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
            )
        )
        if not item:
            raise MediaArchiveSourceError("Mídia comercial fora do escopo do ciclo.")
        photo_ids = set(db.scalars(select(PhotoAsset.id).where(
            PhotoAsset.tenant_id == tenant_id,
            PhotoAsset.parent_gallery_id == parent_gallery_id,
            PhotoAsset.folder_id.in_(allowed_folder_ids),
        )))
        if (
            item.folder_id_snapshot not in allowed_folder_ids
            and item.photo_asset_id_snapshot not in photo_ids
        ):
            raise MediaArchiveSourceError("Item comercial fora do escopo da pasta.")
        relative_key = (
            history.preview_storage_key
            if commercial_match.group(2) == "preview"
            else history.delivery_storage_key
        )
        if not relative_key:
            raise MediaArchiveSourceError("Mídia comercial indisponível.")
        root = historical_media.history_root()
        historical_media.historical_media_path(relative_key, tenant_id=tenant_id, item_id=item.id)
    else:
        raise MediaArchiveSourceError("Referência de destino não permitida.")

    key = PurePosixPath(relative_key)
    if (
        not relative_key or "\\" in relative_key or key.is_absolute()
        or any(part in {"", ".", ".."} for part in key.parts)
    ):
        raise MediaArchiveSourceError("Destino fora do armazenamento permitido.")
    root = root.resolve()
    candidate = root.joinpath(*key.parts)
    current = root
    for part in key.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or (
            os.name == "nt"
            and metadata.st_file_attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise MediaArchiveSourceError("Destino com componente simbólico não permitido.")
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise MediaArchiveSourceError("Destino fora da raiz autorizada.") from exc
    if resolved == root:
        raise MediaArchiveSourceError("Destino aponta para a raiz de armazenamento.")
    if resolved.exists() and not resolved.is_file():
        raise MediaArchiveSourceError("Destino existente não é arquivo regular.")
    return resolved


def snapshot_archive_objects(
    db: Session,
    *,
    cycle: MediaArchiveCycle,
    operation: MediaArchiveOperation,
) -> list[MediaArchiveObject]:
    """Cria o snapshot idempotente; divergência não sobrescreve checksum congelado."""
    if (
        operation.operation_type != "archive"
        or operation.tenant_id != cycle.tenant_id
        or operation.cycle_id != cycle.id
        or cycle.state not in {"local", "archiving"}
    ):
        raise MediaArchiveSourceError("Operação de arquivo inconsistente.")
    sources = resolve_archive_sources(
        db,
        tenant_id=cycle.tenant_id,
        parent_gallery_id=cycle.parent_gallery_id,
        folder_id=cycle.folder_id,
    )
    current_refs = {item.source_ref for item in sources}
    existing = list(db.scalars(select(MediaArchiveObject).where(
        MediaArchiveObject.tenant_id == cycle.tenant_id,
        MediaArchiveObject.cycle_id == cycle.id,
    ).order_by(MediaArchiveObject.source_ref)))
    existing_by_ref = {item.source_ref: item for item in existing if item.object_type != "manifest"}
    if set(existing_by_ref) - current_refs:
        raise MediaArchiveSourceError("O conjunto de fontes diverge do snapshot persistido.")

    rows: list[MediaArchiveObject] = []
    for source in sources:
        row = existing_by_ref.get(source.source_ref)
        if row:
            if (
                row.object_type != source.object_type
                or row.mime_type != source.mime_type
                or row.size_bytes != source.size_bytes
                or row.sha256 != source.sha256
            ):
                raise MediaArchiveSourceError("Fonte mudou após o snapshot do ciclo.")
        else:
            row = MediaArchiveObject(
                id=uuid4(),
                tenant_id=cycle.tenant_id,
                cycle_id=cycle.id,
                source_ref=source.source_ref,
                object_type=source.object_type,
                mime_type=source.mime_type,
                size_bytes=source.size_bytes,
                sha256=source.sha256,
            )
            db.add(row)
        rows.append(row)
    db.flush()
    return rows


def build_archive_manifest(
    *,
    cycle: MediaArchiveCycle,
    operation: MediaArchiveOperation,
    objects: Sequence[MediaArchiveObject],
    manifest_operation_id: UUID | None = None,
    created_at: datetime | None = None,
) -> tuple[dict, bytes, str]:
    """Monta e guarda manifesto V1 depois de todos os uploads terem IDs remotos."""
    if (
        operation.operation_type != "archive"
        or operation.tenant_id != cycle.tenant_id
        or operation.cycle_id != cycle.id
    ):
        raise MediaArchiveManifestError("Operação não corresponde ao ciclo do manifesto.")
    if manifest_operation_id is not None and not isinstance(manifest_operation_id, UUID):
        raise MediaArchiveManifestError("Identidade original da operação do manifesto inválida.")
    if created_at is not None and (
        created_at.tzinfo is None or created_at.utcoffset() is None
    ):
        raise MediaArchiveManifestError("Timestamp deve conter fuso horário UTC.")
    timestamp = (created_at or datetime.now(timezone.utc)).astimezone(timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    items: list[dict] = []
    for row in objects:
        if row.object_type == "manifest":
            continue
        if row.tenant_id != cycle.tenant_id or row.cycle_id != cycle.id:
            raise MediaArchiveManifestError("Objeto de outro ciclo ou tenant.")
        if not row.remote_object_id:
            raise MediaArchiveManifestError("Upload ainda não confirmou ID remoto.")
        items.append({
            "object_id": str(row.id),
            "source_ref": row.source_ref,
            "object_type": row.object_type,
            "mime_type": row.mime_type,
            "size_bytes": row.size_bytes,
            "sha256": row.sha256,
            "remote_object_id": row.remote_object_id,
        })
    items.sort(key=lambda item: item["object_id"])
    manifest = {
        "schema_version": 1,
        "tenant_id": str(cycle.tenant_id),
        "parent_gallery_id": str(cycle.parent_gallery_id),
        "folder_id": str(cycle.folder_id),
        "cycle_id": str(cycle.id),
        "operation_id": str(manifest_operation_id or operation.id),
        "created_at": timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "object_count": len(items),
        "total_bytes": sum(item["size_bytes"] for item in items),
        "objects": items,
    }
    encoded, checksum = canonical_manifest_bytes(manifest)
    cycle.manifest_version = 1
    cycle.manifest = manifest
    cycle.manifest_sha256 = checksum
    cycle.object_count = len(items)
    cycle.total_bytes = manifest["total_bytes"]
    return manifest, encoded, checksum


def validate_stored_archive_manifest(cycle: MediaArchiveCycle) -> tuple[dict, bytes]:
    """Revalida manifesto persistido e confirma contagens/hash do ciclo."""
    encoded, checksum = canonical_manifest_bytes(cycle.manifest)
    manifest = cycle.manifest
    if (
        manifest["schema_version"] != cycle.manifest_version
        or manifest["tenant_id"] != str(cycle.tenant_id)
        or manifest["parent_gallery_id"] != str(cycle.parent_gallery_id)
        or manifest["folder_id"] != str(cycle.folder_id)
        or manifest["cycle_id"] != str(cycle.id)
        or manifest["object_count"] != cycle.object_count
        or manifest["total_bytes"] != cycle.total_bytes
        or checksum != cycle.manifest_sha256
    ):
        raise MediaArchiveManifestError("Manifesto persistido diverge do catálogo.")
    return manifest, encoded
