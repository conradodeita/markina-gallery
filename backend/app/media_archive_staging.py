"""Staging privado e pré-flight de espaço para recuperação de mídia fria."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import historical_media
from app import media as media_storage
from app.acervo_context import require_active_owner
from app.auth import (
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveObject,
    MediaArchiveOperation,
    MediaArchiveSpaceReservation,
    now,
)
from app.media_archive_manifest import MediaArchiveManifestError, validate_stored_archive_manifest

GIB = 1024**3
MINIMUM_FREE_BYTES = 10 * GIB
MINIMUM_FREE_PERCENT = 15


class MediaArchiveStagingError(RuntimeError):
    """Erro operacional sem texto de sistema de arquivos, segredo ou dado de cliente."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class VolumeCapacity:
    volume_key: str
    total_bytes: int
    free_bytes: int


@dataclass(frozen=True)
class VolumeSpaceNeed:
    volume_key: str
    total_bytes: int
    free_bytes: int
    required_bytes: int
    minimum_free_bytes: int


def _volume_key(device: int) -> str:
    return hashlib.sha256(f"device:{device}".encode("ascii")).hexdigest()


def volume_capacity(path: Path) -> VolumeCapacity:
    """Mede o volume sem armazenar o caminho físico no catálogo."""
    try:
        probe = path
        while not probe.exists():
            parent = probe.parent
            if parent == probe:
                raise OSError
            probe = parent
        device = probe.stat().st_dev
        usage = shutil.disk_usage(probe)
    except (OSError, ValueError) as exc:
        raise MediaArchiveStagingError(
            "Não foi possível confirmar o espaço disponível.", code="capacity_unavailable",
        ) from exc
    if usage.total <= 0 or usage.free < 0 or usage.free > usage.total:
        raise MediaArchiveStagingError(
            "A medição de espaço retornou valores inválidos.", code="capacity_unavailable",
        )
    return VolumeCapacity(_volume_key(device), usage.total, usage.free)


def _is_link_or_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and getattr(info, "st_file_attributes", 0) & reparse_flag)


def _assert_no_link_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if _is_link_or_reparse(current):
            raise MediaArchiveStagingError("O staging contém um caminho simbólico não permitido.")


def _is_related(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _served_roots() -> tuple[Path, ...]:
    return tuple(dict.fromkeys((
        media_storage.source_root(),
        media_storage.derivatives_root(),
        historical_media.history_root(),
    )))


def _normalized_staging_root(root: Path | str | None) -> Path:
    raw_value = root if root is not None else os.getenv("MEDIA_ARCHIVE_STAGING_ROOT")
    if not raw_value:
        raise MediaArchiveStagingError("O staging de arquivo frio não está configurado.")
    raw = Path(os.path.expandvars(os.path.expanduser(os.fspath(raw_value))))
    if not raw.is_absolute() or any(part in {".", ".."} for part in raw.parts[1:]):
        raise MediaArchiveStagingError("O staging precisa de uma raiz absoluta segura.")
    _assert_no_link_components(raw)
    normalized = raw.resolve(strict=False)
    _assert_no_link_components(normalized)
    if any(_is_related(normalized, served.resolve(strict=False)) for served in _served_roots()):
        raise MediaArchiveStagingError("O staging deve ficar fora das raízes de mídia servidas.")
    return normalized


def configured_staging_root(root: Path | str | None = None) -> Path:
    """Valida e retorna a raiz configurada sem criar arquivos ou diretórios."""
    return _normalized_staging_root(root)


def _ensure_private_directory(path: Path) -> None:
    _assert_no_link_components(path)
    if not path.exists():
        missing: list[Path] = []
        current = path
        while not current.exists():
            missing.append(current)
            parent = current.parent
            if parent == current:
                raise MediaArchiveStagingError("Não foi possível criar o staging privado.")
            current = parent
        _assert_no_link_components(current)
        for directory in reversed(missing):
            try:
                directory.mkdir(mode=0o700)
            except FileExistsError:
                pass
            except OSError as exc:
                raise MediaArchiveStagingError("Não foi possível criar o staging privado.") from exc
            _assert_no_link_components(directory)
    try:
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or _is_link_or_reparse(path):
            raise MediaArchiveStagingError("O staging não é um diretório privado válido.")
        if os.name != "nt":
            os.chmod(path, 0o700)
            if stat.S_IMODE(path.stat().st_mode) & 0o077:
                raise MediaArchiveStagingError("As permissões do staging não são privadas.")
    except MediaArchiveStagingError:
        raise
    except OSError as exc:
        raise MediaArchiveStagingError("Não foi possível proteger o staging privado.") from exc


def staging_directory(
    tenant_id: UUID,
    operation_id: UUID,
    *,
    root: Path | str | None = None,
) -> Path:
    """Cria/retorna `<raiz>/<tenant UUID>/<operação UUID>` sem aceitar caminhos."""
    if not isinstance(tenant_id, UUID) or not isinstance(operation_id, UUID):
        raise MediaArchiveStagingError("Identificadores de staging inválidos.")
    base = _normalized_staging_root(root)
    tenant_directory = base / str(tenant_id)
    operation_directory = tenant_directory / str(operation_id)
    _ensure_private_directory(base)
    _ensure_private_directory(tenant_directory)
    _ensure_private_directory(operation_directory)
    return operation_directory


def staging_object_path(
    tenant_id: UUID,
    operation_id: UUID,
    object_id: UUID,
    *,
    root: Path | str | None = None,
) -> Path:
    """Deriva caminho de objeto opaco; o chamador nunca escolhe filename ou extensão."""
    if not isinstance(object_id, UUID):
        raise MediaArchiveStagingError("Identificador de objeto de staging inválido.")
    directory = staging_directory(tenant_id, operation_id, root=root)
    objects_directory = directory / "objects"
    _ensure_private_directory(objects_directory)
    target = objects_directory / f"{object_id}.part"
    if _is_link_or_reparse(target):
        raise MediaArchiveStagingError("O objeto de staging contém um caminho simbólico não permitido.")
    return target


def minimum_free_bytes(total_bytes: int) -> int:
    if type(total_bytes) is not int or total_bytes <= 0:
        raise MediaArchiveStagingError("A capacidade do volume é inválida.", code="capacity_unavailable")
    percentage = (total_bytes * MINIMUM_FREE_PERCENT + 99) // 100
    return max(MINIMUM_FREE_BYTES, percentage)


def plan_restore_space(
    objects: Sequence[MediaArchiveObject],
    *,
    staging_root: Path,
    capacity_provider: Callable[[Path], VolumeCapacity] = volume_capacity,
) -> list[VolumeSpaceNeed]:
    """Calcula bytes temporários/finais por volume, sem alterar o banco ou arquivos."""
    roots = {
        "source": media_storage.source_root(),
        "cover_asset": media_storage.source_root(),
        "derivative": media_storage.derivatives_root(),
        "cover_thumbnail": media_storage.derivatives_root(),
        "commercial_media": historical_media.history_root(),
    }
    media_objects = [row for row in objects if row.object_type != "manifest"]
    stage_bytes = 0
    target_bytes: dict[str, int] = defaultdict(int)
    capacities: dict[str, VolumeCapacity] = {}

    def observe(path: Path) -> VolumeCapacity:
        capacity = capacity_provider(path)
        if (
            not isinstance(capacity.volume_key, str)
            or len(capacity.volume_key) != 64
            or type(capacity.total_bytes) is not int
            or type(capacity.free_bytes) is not int
            or capacity.total_bytes <= 0
            or capacity.free_bytes < 0
            or capacity.free_bytes > capacity.total_bytes
        ):
            raise MediaArchiveStagingError(
                "A medição de espaço retornou valores inválidos.", code="capacity_unavailable",
            )
        previous = capacities.setdefault(capacity.volume_key, capacity)
        if previous.total_bytes != capacity.total_bytes:
            raise MediaArchiveStagingError(
                "A medição do volume ficou inconsistente.", code="capacity_unavailable",
            )
        return previous

    staging_capacity = observe(staging_root)
    for row in media_objects:
        if type(row.size_bytes) is not int or row.size_bytes <= 0:
            raise MediaArchiveStagingError("O tamanho do pacote é inválido.")
        target_root = roots.get(row.object_type)
        if target_root is None:
            raise MediaArchiveStagingError("O tipo de objeto não pode ser restaurado.")
        target_capacity = observe(target_root)
        target_bytes[target_capacity.volume_key] += row.size_bytes
        stage_bytes += row.size_bytes

    # O staging permanece íntegro até a promoção completa. Se ele e o destino
    # compartilham volume, a capacidade precisa cobrir as duas cópias ao mesmo
    # tempo; usar max() subestimava o pico físico durante a recuperação.
    required: dict[str, int] = {staging_capacity.volume_key: stage_bytes}
    for key, size in target_bytes.items():
        required[key] = required.get(key, 0) + size
    return [
        VolumeSpaceNeed(
            volume_key=key,
            total_bytes=capacities[key].total_bytes,
            free_bytes=capacities[key].free_bytes,
            required_bytes=size,
            minimum_free_bytes=minimum_free_bytes(capacities[key].total_bytes),
        )
        for key, size in sorted(required.items())
    ]


def validate_restore_catalog(
    db: Session,
    *,
    tenant_id: UUID,
    operation_id: UUID,
) -> tuple[MediaArchiveCycle, MediaArchiveOperation, list[MediaArchiveObject]]:
    """Carrega e valida a cópia congelada antes de cada pull ou retomada."""
    operation = db.scalar(select(MediaArchiveOperation).where(
        MediaArchiveOperation.id == operation_id,
        MediaArchiveOperation.tenant_id == tenant_id,
        MediaArchiveOperation.operation_type == "restore",
        MediaArchiveOperation.status == "processing",
    ))
    if operation is None:
        raise MediaArchiveStagingError("A operação de recuperação não está ativa.")
    cycle = db.scalar(select(MediaArchiveCycle).where(
        MediaArchiveCycle.id == operation.cycle_id,
        MediaArchiveCycle.tenant_id == tenant_id,
        MediaArchiveCycle.state == "restoring",
    ))
    if cycle is None:
        raise MediaArchiveStagingError("O ciclo não está em recuperação.")
    objects = list(db.scalars(select(MediaArchiveObject).where(
        MediaArchiveObject.cycle_id == cycle.id,
        MediaArchiveObject.tenant_id == tenant_id,
    ).order_by(MediaArchiveObject.id)))
    _assert_manifest_matches_catalog(db, cycle, operation, objects)
    return cycle, operation, objects


def _same_instant(left: datetime | None, right: datetime) -> bool:
    if left is None:
        return False
    if left.tzinfo is None or left.utcoffset() is None:
        left = left.replace(tzinfo=timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    return left > right


def _assert_manifest_matches_catalog(
    db: Session,
    cycle: MediaArchiveCycle,
    operation: MediaArchiveOperation,
    objects: Sequence[MediaArchiveObject],
) -> None:
    try:
        manifest, _ = validate_stored_archive_manifest(cycle)
    except MediaArchiveManifestError as exc:
        raise MediaArchiveStagingError("O manifesto do ciclo não passou na validação.") from exc
    try:
        archive_operation_id = UUID(manifest["operation_id"])
    except (TypeError, ValueError) as exc:
        raise MediaArchiveStagingError("O manifesto não identifica o arquivamento original.") from exc
    archive_operation = db.scalar(select(MediaArchiveOperation).where(
        MediaArchiveOperation.id == archive_operation_id,
        MediaArchiveOperation.tenant_id == operation.tenant_id,
        MediaArchiveOperation.cycle_id == cycle.id,
        MediaArchiveOperation.operation_type == "archive",
        MediaArchiveOperation.status == "completed",
    ))
    if not archive_operation:
        raise MediaArchiveStagingError("O manifesto não identifica um arquivamento concluído.")
    expected = {
        item["object_id"]: (
            item["source_ref"], item["object_type"], item["mime_type"],
            item["size_bytes"], item["sha256"], item["remote_object_id"],
        )
        for item in manifest["objects"]
    }
    actual_rows = [row for row in objects if row.object_type != "manifest"]
    actual = {
        str(row.id): (
            row.source_ref, row.object_type, row.mime_type, row.size_bytes,
            row.sha256, row.remote_object_id,
        )
        for row in actual_rows
    }
    if actual != expected or any(not row.remote_object_id for row in actual_rows):
        raise MediaArchiveStagingError("O catálogo de objetos diverge do manifesto do ciclo.")


def reserve_restore_space(
    db: Session,
    *,
    tenant_id: UUID,
    operation_id: UUID,
    staging_root: Path | str | None = None,
    capacity_provider: Callable[[Path], VolumeCapacity] = volume_capacity,
) -> list[MediaArchiveSpaceReservation]:
    """Reserva capacidade em uma transação serializada pela lease global.

    O chamador mantém a transação aberta até confirmar a transição de estado da
    operação; `FOR UPDATE` na linha coordenadora serializa também os pré-flights.
    """
    if not isinstance(tenant_id, UUID) or not isinstance(operation_id, UUID):
        raise MediaArchiveStagingError("Identificadores da operação são inválidos.")
    root = _normalized_staging_root(staging_root)
    require_active_owner(db, tenant_id)

    coordinator = db.scalar(select(MediaArchiveCoordinator).where(
        MediaArchiveCoordinator.id == 1,
    ).with_for_update())
    if not coordinator:
        raise MediaArchiveStagingError("A coordenação global não está pronta.", code="lease_unavailable")

    operation = db.scalar(select(MediaArchiveOperation).where(
        MediaArchiveOperation.id == operation_id,
        MediaArchiveOperation.tenant_id == tenant_id,
    ).with_for_update())
    if (
        not operation or operation.operation_type != "restore"
        or operation.status != "processing" or not operation.lease_token
        or not _same_instant(operation.lease_expires_at, datetime.now(timezone.utc))  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
        or coordinator.active_operation_id != operation.id
        or coordinator.lease_token != operation.lease_token
        or not _same_instant(coordinator.lease_expires_at, datetime.now(timezone.utc))  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    ):
        raise MediaArchiveStagingError("A lease global não autoriza este pré-flight.", code="lease_unavailable")

    cycle = db.scalar(select(MediaArchiveCycle).where(
        MediaArchiveCycle.id == operation.cycle_id,
        MediaArchiveCycle.tenant_id == tenant_id,
    ).with_for_update())
    if not cycle or cycle.state != "restoring":
        raise MediaArchiveStagingError("O ciclo não está em restauração.")
    objects = list(db.scalars(select(MediaArchiveObject).where(
        MediaArchiveObject.cycle_id == cycle.id,
        MediaArchiveObject.tenant_id == tenant_id,
    ).with_for_update()))
    _assert_manifest_matches_catalog(db, cycle, operation, objects)
    plan = plan_restore_space(objects, staging_root=root, capacity_provider=capacity_provider)

    all_reservations = list(db.scalars(select(MediaArchiveSpaceReservation).where(
        MediaArchiveSpaceReservation.status == "active",
    ).with_for_update()))
    own_reservations = list(db.scalars(select(MediaArchiveSpaceReservation).where(
        MediaArchiveSpaceReservation.operation_id == operation.id,
        MediaArchiveSpaceReservation.tenant_id == tenant_id,
    ).with_for_update()))
    own_by_volume = {row.volume_key: row for row in own_reservations}
    required_by_volume = {item.volume_key: item.required_bytes for item in plan}
    existing_active = {row.volume_key: row.reserved_bytes for row in own_reservations if row.status == "active"}
    if existing_active and existing_active != required_by_volume:
        raise MediaArchiveStagingError("A reserva da operação diverge do plano calculado.")

    for item in plan:
        reserved_elsewhere = sum(
            row.reserved_bytes for row in all_reservations
            if row.volume_key == item.volume_key and row.operation_id != operation.id
        )
        available_after_reservations = item.free_bytes - reserved_elsewhere
        if available_after_reservations - item.required_bytes < item.minimum_free_bytes:
            raise MediaArchiveStagingError(
                "Espaço insuficiente para recuperar a pasta agora.", code="insufficient_space",
            )

    output: list[MediaArchiveSpaceReservation] = []
    for item in plan:
        row = own_by_volume.get(item.volume_key)
        if row is None:
            row = MediaArchiveSpaceReservation(
                tenant_id=tenant_id,
                operation_id=operation.id,
                volume_key=item.volume_key,
                reserved_bytes=item.required_bytes,
                status="active",
            )
            db.add(row)
        elif row.status == "released":
            row.reserved_bytes = item.required_bytes
            row.status = "active"
            row.released_at = None
        output.append(row)
    db.flush()
    return output


def release_restore_space(
    db: Session,
    *,
    tenant_id: UUID,
    operation_id: UUID,
    outcome: str,
) -> int:
    """Libera reservas somente para sucesso ou falha comprovada, nunca incerteza."""
    if outcome not in {"completed", "proven_failure"}:
        raise MediaArchiveStagingError("O resultado não permite liberar espaço.")
    operation = db.scalar(select(MediaArchiveOperation).where(
        MediaArchiveOperation.id == operation_id,
        MediaArchiveOperation.tenant_id == tenant_id,
    ).with_for_update())
    expected_status = "completed" if outcome == "completed" else "failed"
    if not operation or operation.operation_type != "restore" or operation.status != expected_status:
        raise MediaArchiveStagingError("O estado da operação não permite liberar espaço.")
    rows = list(db.scalars(select(MediaArchiveSpaceReservation).where(
        MediaArchiveSpaceReservation.operation_id == operation.id,
        MediaArchiveSpaceReservation.tenant_id == tenant_id,
        MediaArchiveSpaceReservation.status == "active",
    ).with_for_update()))
    released_at = now()
    for row in rows:
        row.status = "released"
        row.released_at = released_at
    db.flush()
    return len(rows)


def cleanup_restore_staging(
    tenant_id: UUID,
    operation_id: UUID,
    object_ids: Sequence[UUID],
    *,
    root: Path | str | None = None,
) -> None:
    """Remove apenas os objetos UUID conhecidos de uma operação privada concluída."""
    if not isinstance(tenant_id, UUID) or not isinstance(operation_id, UUID):
        raise MediaArchiveStagingError("Identificadores de staging inválidos.")
    base = _normalized_staging_root(root)
    tenant_directory = base / str(tenant_id)
    operation_directory = tenant_directory / str(operation_id)
    _assert_no_link_components(operation_directory)
    if not operation_directory.exists():
        return
    try:
        info = operation_directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or _is_link_or_reparse(operation_directory):
            raise MediaArchiveStagingError("Diretório de staging não é seguro.")
        if operation_directory.resolve().parent != tenant_directory.resolve():
            raise MediaArchiveStagingError("Diretório de staging fora do tenant esperado.")

        objects_directory = operation_directory / "objects"
        if objects_directory.exists():
            object_info = objects_directory.lstat()
            if not stat.S_ISDIR(object_info.st_mode) or _is_link_or_reparse(objects_directory):
                raise MediaArchiveStagingError("Diretório de objetos de staging não é seguro.")
            expected_names = {f"{object_id}.part" for object_id in object_ids}
            entries = list(objects_directory.iterdir())
            if any(entry.name not in expected_names for entry in entries):
                raise MediaArchiveStagingError("Staging contém objetos não reconhecidos.")
            for entry in entries:
                entry_info = entry.lstat()
                if not stat.S_ISREG(entry_info.st_mode) or _is_link_or_reparse(entry):
                    raise MediaArchiveStagingError("Objeto de staging não é um arquivo regular.")
                entry.unlink()
            objects_directory.rmdir()
        if any(operation_directory.iterdir()):
            raise MediaArchiveStagingError("Diretório de operação contém itens não reconhecidos.")
        operation_directory.rmdir()
    except MediaArchiveStagingError:
        raise
    except OSError as exc:
        raise MediaArchiveStagingError("Não foi possível limpar o staging da recuperação.") from exc
