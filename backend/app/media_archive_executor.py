"""Executor retomável de arquivamento; storage é sempre injetado pelo chamador."""

from __future__ import annotations

import os
import re
import stat
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import historical_media
from app import media as media_storage
from app.auth import (
    MediaArchiveCycle,
    MediaArchiveObject,
    MediaArchiveOperation,
    MediaArchiveSpaceReservation,
)
from app.media_archive_manifest import (
    ArchiveSource,
    MediaArchiveManifestError,
    MediaArchiveSourceError,
    build_archive_manifest,
    resolve_archive_source_ref,
    resolve_archive_target_path,
    snapshot_archive_objects,
    validate_stored_archive_manifest,
)
from app.media_archive_staging import (
    MediaArchiveStagingError,
    cleanup_restore_staging,
    reserve_restore_space,
    staging_object_path,
    validate_restore_catalog,
)
from app.media_archive_storage import (
    ArchiveDownloadReceipt,
    ArchiveRemoteObject,
    MediaArchiveStorage,
)
from app.media_archive_worker import (
    _DELETE_STAGES,
    MediaArchiveClaim,
    MediaArchiveLeaseConflict,
    MediaArchivePreflightError,
    MediaArchiveTransitionError,
    begin_archive_cleanup,
    begin_archive_copy,
    begin_delete_operation,
    begin_restore_operation,
    checkpoint_operation,
    complete_archive_operation,
    complete_delete_operation,
    complete_restore_operation,
    fail_operation,
    mark_remote_object_deleted,
    renew_operation_lease,
)

_REMOTE_ID = re.compile(r"[A-Za-z0-9_-]{1,256}")
_MANIFEST_SOURCE_REF = "manifest:v1"
_BLOCK_BYTES = 1024 * 1024


class MediaArchiveExecutorError(RuntimeError):
    """Falha sanitizada no fluxo local de arquivamento."""


class MediaArchiveDeletionResultUnknown(MediaArchiveExecutorError):
    """O readback da exclusão diverge ou não pode ser determinado."""


@dataclass(frozen=True)
class MediaArchiveExecutionResult:
    operation_id: UUID
    status: str
    error_code: str | None = None


class _DigestingReader:
    def __init__(self, stream: BinaryIO, *, renew):
        self._stream = stream
        self._renew = renew
        self._digest = sha256()
        self.size_bytes = 0

    def seekable(self) -> bool:
        seekable = getattr(self._stream, "seekable", None)
        if not callable(seekable):
            return False
        try:
            return bool(seekable())
        except (OSError, TypeError, ValueError):
            return False

    def seek(self, offset: int, whence: int = 0) -> int:
        if offset != 0 or whence != 0 or not self.seekable():
            raise OSError("O leitor só permite reposicionamento ao início.")
        position = self._stream.seek(0, 0)
        self._digest = sha256()
        self.size_bytes = 0
        return position if isinstance(position, int) else 0

    def read(self, size: int = -1) -> bytes:
        self._renew()
        payload = self._stream.read(size)
        if payload:
            self._digest.update(payload)
            self.size_bytes += len(payload)
        return payload

    @property
    def sha256(self) -> str:
        return self._digest.hexdigest()


class _DigestingSink:
    def __init__(self, *, renew):
        self._renew = renew
        self._digest = sha256()
        self.size_bytes = 0

    def write(self, payload: bytes) -> int:
        if not isinstance(payload, bytes):
            payload = bytes(payload)
        self._renew()
        self._digest.update(payload)
        self.size_bytes += len(payload)
        return len(payload)

    @property
    def sha256(self) -> str:
        return self._digest.hexdigest()


def _as_utc(value: datetime) -> datetime:
    """Interpreta valores SQLite sem tzinfo como UTC para o contrato canônico."""
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
    return value.astimezone(timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.


def _lease_refresher(db: Session, claim: MediaArchiveClaim):
    last = time.monotonic()

    def renew_if_due() -> None:
        nonlocal last
        if time.monotonic() - last >= 20:
            renew_operation_lease(
                db, operation_id=claim.operation_id, lease_token=claim.lease_token,
            )
            last = time.monotonic()

    return renew_if_due


def _load_operation_scope(
    db: Session, claim: MediaArchiveClaim,
) -> tuple[MediaArchiveOperation, MediaArchiveCycle]:
    operation = db.scalar(select(MediaArchiveOperation).where(
        MediaArchiveOperation.id == claim.operation_id,
        MediaArchiveOperation.tenant_id == claim.tenant_id,
    ))
    cycle = db.scalar(select(MediaArchiveCycle).where(
        MediaArchiveCycle.id == operation.cycle_id,
        MediaArchiveCycle.tenant_id == claim.tenant_id,
    )) if operation else None
    if (
        not operation or not cycle or operation.operation_type != "archive"
        or operation.status != "processing" or operation.lease_token != claim.lease_token
    ):
        raise MediaArchiveTransitionError("A operação não pertence ao lease ativo.")
    return operation, cycle


def _object_rows(
    db: Session, *, tenant_id: UUID, cycle_id: UUID,
) -> list[MediaArchiveObject]:
    return list(db.scalars(
        select(MediaArchiveObject)
        .where(
            MediaArchiveObject.tenant_id == tenant_id,
            MediaArchiveObject.cycle_id == cycle_id,
        )
        .order_by(MediaArchiveObject.id)
    ))


def _object_key(
    *, tenant_id: UUID, parent_gallery_id: UUID, folder_id: UUID,
    cycle_id: UUID, object_id: UUID,
) -> str:
    return f"{tenant_id}/{parent_gallery_id}/{folder_id}/{cycle_id}/{object_id}"


def _validate_receipt(
    receipt: ArchiveRemoteObject,
    *,
    expected_size: int,
    expected_mime: str,
) -> None:
    if (
        not isinstance(receipt, ArchiveRemoteObject)
        or not isinstance(receipt.remote_id, str)
        or not _REMOTE_ID.fullmatch(receipt.remote_id)
        or type(receipt.size_bytes) is not int
        or receipt.size_bytes != expected_size
        or receipt.mime_type != expected_mime
    ):
        raise MediaArchiveExecutorError("Metadados remotos divergentes.")


def _safe_source_stream(source: ArchiveSource) -> BinaryIO:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(source.path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != source.size_bytes:
            os.close(descriptor)
            raise MediaArchiveSourceError("Fonte local mudou antes do upload.")
        return os.fdopen(descriptor, "rb", closefd=True)
    except MediaArchiveSourceError:
        raise
    except OSError as exc:
        raise MediaArchiveSourceError("Fonte local indisponível para upload.") from exc


def _verify_remote_object(
    storage: MediaArchiveStorage,
    *,
    remote_id: str,
    size_bytes: int,
    mime_type: str,
    sha256_hex: str,
    renew,
) -> None:
    metadata = storage.read_object(remote_id=remote_id)
    if metadata is None or metadata.remote_id != remote_id:
        raise MediaArchiveExecutorError("Objeto remoto não encontrado no readback.")
    _validate_receipt(metadata, expected_size=size_bytes, expected_mime=mime_type)
    sink = _DigestingSink(renew=renew)
    receipt = storage.download_object(remote_id=remote_id, destination=sink)
    if (
        not isinstance(receipt, ArchiveDownloadReceipt)
        or type(receipt.size_bytes) is not int
        or not isinstance(receipt.sha256, str)
        or sink.size_bytes != size_bytes
        or sink.sha256 != sha256_hex
        or receipt.size_bytes != sink.size_bytes
        or receipt.sha256 != sink.sha256
    ):
        raise MediaArchiveExecutorError("Readback remoto não corresponde ao manifesto.")


class _DigestingFileWriter:
    """Escreve o pull em staging privado e mede os bytes recebidos."""

    def __init__(self, stream: BinaryIO, *, renew):
        self._stream = stream
        self._renew = renew
        self._digest = sha256()
        self.size_bytes = 0

    def write(self, payload: bytes) -> int:
        if not isinstance(payload, bytes):
            payload = bytes(payload)
        self._renew()
        written = self._stream.write(payload)
        if written != len(payload):
            raise OSError("Escrita incompleta em staging.")
        self._digest.update(payload)
        self.size_bytes += written
        return written

    @property
    def sha256(self) -> str:
        return self._digest.hexdigest()


def _local_file_digest(path: Path, *, renew) -> tuple[int, str] | None:
    """Lê somente arquivo regular e rejeita symlinks/reparse points."""
    try:
        path_info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MediaArchiveSourceError("Arquivo local indisponível para validação.") from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if (
        not stat.S_ISREG(path_info.st_mode)
        or stat.S_ISLNK(path_info.st_mode)
        or (reparse_flag and getattr(path_info, "st_file_attributes", 0) & reparse_flag)
    ):
        raise MediaArchiveSourceError("Destino local não é um arquivo regular.")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MediaArchiveSourceError("Arquivo local indisponível para validação.") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise MediaArchiveSourceError("Destino local não é um arquivo regular.")
        digest_state, byte_count = sha256(), 0
        while True:
            renew()
            chunk = os.read(descriptor, _BLOCK_BYTES)
            if not chunk:
                break
            digest_state.update(chunk)
            byte_count += len(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or byte_count != after.st_size
        ):
            raise MediaArchiveSourceError("Arquivo local mudou durante a validação.")
        return byte_count, digest_state.hexdigest()
    finally:
        os.close(descriptor)


def _matches_local_object(path: Path, *, size_bytes: int, digest: str, renew) -> bool:
    actual = _local_file_digest(path, renew=renew)
    return actual == (size_bytes, digest)


def _safe_unlink_staging_file(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_ISLNK(info.st_mode)
        or (reparse_flag and getattr(info, "st_file_attributes", 0) & reparse_flag)
    ):
        raise MediaArchiveStagingError("O objeto de staging não é um arquivo regular.")
    path.unlink()


@contextmanager
def _exclusive_private_file(path: Path):
    flags = (
        os.O_WRONLY | os.O_CREAT | os.O_EXCL
        | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise MediaArchiveStagingError("Não foi possível criar arquivo privado de staging.") from exc
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = -1
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _download_verified_object(
    storage: MediaArchiveStorage,
    *,
    row: MediaArchiveObject,
    destination: Path,
    renew,
) -> None:
    if not row.remote_object_id or not _REMOTE_ID.fullmatch(row.remote_object_id):
        raise MediaArchiveExecutorError("Objeto sem identidade remota válida.")
    metadata = storage.read_object(remote_id=row.remote_object_id)
    if metadata is None or metadata.remote_id != row.remote_object_id:
        raise MediaArchiveExecutorError("Objeto remoto não encontrado no readback.")
    _validate_receipt(metadata, expected_size=row.size_bytes, expected_mime=row.mime_type)

    existing = _local_file_digest(destination, renew=renew)
    if existing == (row.size_bytes, row.sha256):
        return
    if existing is not None:
        _safe_unlink_staging_file(destination)

    with _exclusive_private_file(destination) as stream:
        writer = _DigestingFileWriter(stream, renew=renew)
        receipt = storage.download_object(
            remote_id=row.remote_object_id,
            destination=writer,
        )
        stream.flush()
        os.fsync(stream.fileno())
        if (
            not isinstance(receipt, ArchiveDownloadReceipt)
            or type(receipt.size_bytes) is not int
            or not isinstance(receipt.sha256, str)
            or writer.size_bytes != row.size_bytes
            or writer.sha256 != row.sha256
            or receipt.size_bytes != writer.size_bytes
            or receipt.sha256 != writer.sha256
        ):
            raise MediaArchiveExecutorError("Pull remoto diverge do manifesto.")

    if not _matches_local_object(
        destination, size_bytes=row.size_bytes, digest=row.sha256, renew=renew,
    ):
        raise MediaArchiveExecutorError("Objeto em staging diverge do manifesto.")


def _ensure_target_parent(root: Path, parent: Path) -> None:
    root = root.resolve()
    try:
        relative = parent.relative_to(root)
    except ValueError as exc:
        raise MediaArchiveSourceError("Destino local fora da raiz permitida.") from exc
    current = root
    if not current.exists():
        current.mkdir(parents=True, exist_ok=True)
    for part in relative.parts:
        current = current / part
        try:
            current.mkdir()
        except FileExistsError:
            pass
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise MediaArchiveSourceError("Diretório local indisponível.") from exc
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or (os.name == "nt" and reparse_flag and getattr(metadata, "st_file_attributes", 0) & reparse_flag)
        ):
            raise MediaArchiveSourceError("Diretório local contém caminho simbólico.")


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError as exc:
        raise MediaArchiveSourceError("Diretório de destino indisponível para sincronização.") from exc
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise MediaArchiveSourceError("Promoção local não foi sincronizada no destino.") from exc
    finally:
        os.close(descriptor)


def _promote_verified_object(
    *,
    source: Path,
    target: Path,
    root: Path,
    operation_id: UUID,
    object_id: UUID,
    size_bytes: int,
    digest: str,
    renew,
) -> None:
    temporary = target.parent / f".restore-{operation_id}-{object_id}.tmp"
    if _matches_local_object(target, size_bytes=size_bytes, digest=digest, renew=renew):
        _safe_unlink_staging_file(temporary)
        return
    existing = _local_file_digest(target, renew=renew)
    if existing is not None:
        raise MediaArchiveSourceError("Destino local diverge do objeto arquivado.")

    _ensure_target_parent(root, target.parent)
    if not _matches_local_object(source, size_bytes=size_bytes, digest=digest, renew=renew):
        raise MediaArchiveStagingError("Objeto verificado de staging foi alterado.")
    existing_temporary = _local_file_digest(temporary, renew=renew)
    if existing_temporary != (size_bytes, digest):
        if existing_temporary is not None:
            _safe_unlink_staging_file(temporary)
        with _exclusive_private_file(temporary) as output:
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            source_fd = os.open(source, flags)
            try:
                before = os.fstat(source_fd)
                if not stat.S_ISREG(before.st_mode) or before.st_size != size_bytes:
                    raise MediaArchiveStagingError("Objeto de staging mudou antes da promoção.")
                digest_state, byte_count = sha256(), 0
                while True:
                    renew()
                    chunk = os.read(source_fd, _BLOCK_BYTES)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest_state.update(chunk)
                    byte_count += len(chunk)
                after = os.fstat(source_fd)
                if (
                    byte_count != size_bytes
                    or digest_state.hexdigest() != digest
                    or before.st_ino != after.st_ino
                    or before.st_mtime_ns != after.st_mtime_ns
                ):
                    raise MediaArchiveStagingError("Objeto de staging diverge durante a promoção.")
            finally:
                os.close(source_fd)

    if not _matches_local_object(temporary, size_bytes=size_bytes, digest=digest, renew=renew):
        raise MediaArchiveStagingError("Arquivo temporário de promoção diverge do manifesto.")
    try:
        # Linkar o temporário validado publica o nome final atomicamente sem
        # sobrescrever arquivo inesperado; ambos apontam ao mesmo inode.
        os.link(temporary, target)
        _fsync_directory(target.parent)
    except FileExistsError:
        if not _matches_local_object(target, size_bytes=size_bytes, digest=digest, renew=renew):
            raise MediaArchiveSourceError("Destino local diverge do objeto arquivado.")
    finally:
        _safe_unlink_staging_file(temporary)
        _fsync_directory(target.parent)
    if not _matches_local_object(target, size_bytes=size_bytes, digest=digest, renew=renew):
        raise MediaArchiveSourceError("Promoção local não passou pela verificação final.")


def _target_root(object_type: str) -> Path:
    roots = {
        "source": media_storage.source_root(),
        "cover_asset": media_storage.source_root(),
        "derivative": media_storage.derivatives_root(),
        "cover_thumbnail": media_storage.derivatives_root(),
        "commercial_media": historical_media.history_root(),
    }
    try:
        return roots[object_type]
    except KeyError as exc:
        raise MediaArchiveSourceError("Tipo de destino local não permitido.") from exc


def _unlink_verified_windows(
    target: Path, *, size_bytes: int, digest: str,
) -> bool:
    """Verifica e remove pelo handle, sem reabrir a janela de troca do caminho."""
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class _FileTime(ctypes.Structure):
        _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("attributes", wintypes.DWORD),
            ("creation_time", _FileTime),
            ("last_access_time", _FileTime),
            ("last_write_time", _FileTime),
            ("volume_serial_number", wintypes.DWORD),
            ("file_size_high", wintypes.DWORD),
            ("file_size_low", wintypes.DWORD),
            ("number_of_links", wintypes.DWORD),
            ("file_index_high", wintypes.DWORD),
            ("file_index_low", wintypes.DWORD),
        ]

    class _FileDispositionInfo(ctypes.Structure):
        _fields_ = [("delete_file", wintypes.BOOLEAN)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    get_information = kernel32.GetFileInformationByHandle
    get_information.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_ByHandleFileInformation),
    ]
    get_information.restype = wintypes.BOOL
    set_information = kernel32.SetFileInformationByHandle
    set_information.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
    ]
    set_information.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    generic_read = 0x80000000
    delete_access = 0x00010000
    share_read = 0x00000001
    share_delete = 0x00000004
    open_existing = 3
    open_reparse_point = 0x00200000
    sequential_scan = 0x08000000
    handle = create_file(
        str(target), generic_read | delete_access, share_read | share_delete,
        None, open_existing, open_reparse_point | sequential_scan, None,
    )
    if handle == wintypes.HANDLE(-1).value:
        raise OSError(ctypes.get_last_error(), "Não foi possível abrir o arquivo para cleanup.")

    file_descriptor = None
    try:
        info = _ByHandleFileInformation()
        if not get_information(handle, ctypes.byref(info)):
            raise OSError(ctypes.get_last_error(), "Não foi possível validar o arquivo local.")
        is_reparse = bool(info.attributes & 0x00000400)
        is_directory = bool(info.attributes & 0x00000010)
        actual_size = (info.file_size_high << 32) | info.file_size_low
        if is_reparse or is_directory or actual_size != size_bytes:
            raise MediaArchiveSourceError("Arquivo local diverge do snapshot verificado.")

        file_descriptor = msvcrt.open_osfhandle(
            handle, os.O_RDONLY | os.O_BINARY,
        )
        handle = None
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size != size_bytes:
            raise MediaArchiveSourceError("Arquivo local diverge do snapshot verificado.")
        digest_state, byte_count = sha256(), 0
        while True:
            chunk = os.read(file_descriptor, _BLOCK_BYTES)
            if not chunk:
                break
            digest_state.update(chunk)
            byte_count += len(chunk)
        after = os.fstat(file_descriptor)
        if (
            byte_count != size_bytes or digest_state.hexdigest() != digest
            or before.st_ino != after.st_ino or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
        ):
            raise MediaArchiveSourceError("Arquivo local diverge do snapshot verificado.")

        disposition = _FileDispositionInfo(True)
        file_handle = msvcrt.get_osfhandle(file_descriptor)
        if not set_information(
            wintypes.HANDLE(file_handle), 4, ctypes.byref(disposition),
            ctypes.sizeof(disposition),
        ):
            raise OSError(ctypes.get_last_error(), "Não foi possível concluir o cleanup local.")
        return True
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        elif handle is not None:
            close_handle(handle)


def _unlink_verified(target: Path, *, root: Path, size_bytes: int, digest: str) -> bool:
    """Remove um único arquivo regular somente se seus bytes ainda conferem."""
    root = root.resolve()
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise MediaArchiveSourceError("Destino local fora da raiz permitida.") from exc
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise MediaArchiveSourceError("Destino local inválido.")

    if os.name == "nt":
        current = root
        for part in relative.parts[:-1]:
            current = current / part
            try:
                metadata = current.lstat()
            except FileNotFoundError:
                return False
            if stat.S_ISLNK(metadata.st_mode) or (
                metadata.st_file_attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            ):
                raise MediaArchiveSourceError("Destino simbólico não permitido no cleanup.")
        try:
            return _unlink_verified_windows(
                target, size_bytes=size_bytes, digest=digest,
            )
        except FileNotFoundError:
            return False

    if os.name != "nt" and os.open in getattr(os, "supports_dir_fd", set()):
        directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        directory_fd = os.open(root, directory_flags)
        try:
            for part in relative.parts[:-1]:
                next_fd = os.open(part, directory_flags, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = next_fd
            filename = relative.parts[-1]
            try:
                file_fd = os.open(filename, file_flags, dir_fd=directory_fd)
            except FileNotFoundError:
                return False
            try:
                before = os.fstat(file_fd)
                if not stat.S_ISREG(before.st_mode) or before.st_size != size_bytes:
                    raise MediaArchiveSourceError("Arquivo local diverge do snapshot verificado.")
                digest_state = sha256()
                byte_count = 0
                while True:
                    chunk = os.read(file_fd, _BLOCK_BYTES)
                    if not chunk:
                        break
                    digest_state.update(chunk)
                    byte_count += len(chunk)
                after = os.fstat(file_fd)
                if (
                    byte_count != size_bytes
                    or digest_state.hexdigest() != digest
                    or before.st_size != after.st_size
                    or before.st_mtime_ns != after.st_mtime_ns
                ):
                    raise MediaArchiveSourceError("Arquivo local diverge do snapshot verificado.")
                current = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(current.st_mode)
                    or current.st_dev != before.st_dev
                    or current.st_ino != before.st_ino
                ):
                    raise MediaArchiveSourceError("Destino local mudou durante o cleanup.")
                os.unlink(filename, dir_fd=directory_fd)
                return True
            finally:
                os.close(file_fd)
        finally:
            os.close(directory_fd)

    current = root
    for part in relative.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            return False
        if stat.S_ISLNK(metadata.st_mode) or (
            os.name == "nt"
            and metadata.st_file_attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise MediaArchiveSourceError("Destino simbólico não permitido no cleanup.")
    target = current
    try:
        file_fd = os.open(target, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return False
    try:
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size != size_bytes:
            raise MediaArchiveSourceError("Arquivo local diverge do snapshot verificado.")
        digest_state, byte_count = sha256(), 0
        while True:
            chunk = os.read(file_fd, _BLOCK_BYTES)
            if not chunk:
                break
            digest_state.update(chunk)
            byte_count += len(chunk)
        current = target.lstat()
        if (
            byte_count != size_bytes or digest_state.hexdigest() != digest
            or current.st_ino != before.st_ino or current.st_size != size_bytes
            or current.st_mtime_ns != before.st_mtime_ns
        ):
            raise MediaArchiveSourceError("Arquivo local diverge do snapshot verificado.")
        target.unlink()
        return True
    finally:
        os.close(file_fd)


def execute_archive_operation(
    db: Session,
    claim: MediaArchiveClaim,
    *,
    storage: MediaArchiveStorage,
) -> MediaArchiveExecutionResult:
    """Executa um ciclo sem descobrir credenciais ou escolher provider concreto."""
    remote_write_started = False
    cleanup_started = False
    error_code = "archive_failed"
    renew = _lease_refresher(db, claim)
    try:
        operation, cycle = _load_operation_scope(db, claim)
        stages = (
            "snapshot", "uploading", "reading_back", "manifest_upload",
            "manifest_readback", "local_cleanup",
        )
        current_stage = operation.stage
        current_rank = stages.index(current_stage) if current_stage in stages else -1

        def checkpoint(stage: str, details_patch: dict | None = None) -> None:
            nonlocal current_rank, current_stage
            rank = stages.index(stage)
            if rank < current_rank:
                return
            checkpoint_operation(
                db,
                operation_id=claim.operation_id,
                lease_token=claim.lease_token,
                stage=stage,
                details_patch=details_patch,
            )
            current_rank, current_stage = rank, stage

        begin_archive_copy(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        renew_operation_lease(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        operation, cycle = _load_operation_scope(db, claim)
        if current_stage != "local_cleanup":
            checkpoint("snapshot")
            rows = snapshot_archive_objects(db, cycle=cycle, operation=operation)
            db.commit()
            checkpoint("snapshot", {"snapshot_object_count": len(rows)})
            checkpoint("uploading")

            rows = _object_rows(db, tenant_id=claim.tenant_id, cycle_id=cycle.id)
            for row in rows:
                if row.object_type == "manifest" or row.remote_object_id:
                    continue
                source = resolve_archive_source_ref(
                    db,
                    tenant_id=claim.tenant_id,
                    parent_gallery_id=cycle.parent_gallery_id,
                    folder_id=cycle.folder_id,
                    source_ref=row.source_ref,
                )
                if (
                    source.object_type != row.object_type
                    or source.size_bytes != row.size_bytes
                    or source.sha256 != row.sha256
                ):
                    raise MediaArchiveSourceError("Fonte divergente do snapshot congelado.")
                with _safe_source_stream(source) as stream:
                    reader = _DigestingReader(stream, renew=renew)
                    renew_operation_lease(
                        db, operation_id=claim.operation_id, lease_token=claim.lease_token,
                    )
                    remote_write_started = True
                    receipt = storage.upload_object(
                        object_key=_object_key(
                            tenant_id=claim.tenant_id,
                            parent_gallery_id=cycle.parent_gallery_id,
                            folder_id=cycle.folder_id,
                            cycle_id=cycle.id,
                            object_id=row.id,
                        ),
                        mime_type=row.mime_type,
                        size_bytes=row.size_bytes,
                        sha256=row.sha256,
                        stream=reader,
                    )
                    if reader.size_bytes != row.size_bytes or reader.sha256 != row.sha256:
                        raise MediaArchiveExecutorError("Upload não consumiu os bytes do snapshot.")
                _validate_receipt(
                    receipt, expected_size=row.size_bytes, expected_mime=row.mime_type,
                )
                row.remote_object_id = receipt.remote_id
                db.commit()
                renew_operation_lease(
                    db, operation_id=claim.operation_id, lease_token=claim.lease_token,
                )

            checkpoint("reading_back")
            rows = _object_rows(db, tenant_id=claim.tenant_id, cycle_id=cycle.id)
            verified_count = 0
            for row in rows:
                if row.object_type == "manifest":
                    continue
                if not row.remote_object_id:
                    raise MediaArchiveExecutorError("Objeto sem identidade remota no catálogo.")
                renew()
                _verify_remote_object(
                    storage,
                    remote_id=row.remote_object_id,
                    size_bytes=row.size_bytes,
                    mime_type=row.mime_type,
                    sha256_hex=row.sha256,
                    renew=renew,
                )
                verified_count += 1

            checkpoint("manifest_upload", {"verified_object_count": verified_count})
            operation, cycle = _load_operation_scope(db, claim)
            media_rows = [row for row in _object_rows(
                db, tenant_id=claim.tenant_id, cycle_id=cycle.id,
            ) if row.object_type != "manifest"]
            previous_manifest_state = None
            manifest_operation_id = operation.id
            manifest_created_at = _as_utc(operation.created_at)
            previous_manifest = None
            previous_manifest_bytes = None
            if cycle.manifest:
                previous_manifest, previous_manifest_bytes = validate_stored_archive_manifest(cycle)
                try:
                    manifest_operation_id = UUID(previous_manifest["operation_id"])
                    manifest_created_at = datetime.strptime(
                        previous_manifest["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ",
                    ).replace(tzinfo=timezone.utc)  # noqa: UP017 -- Keep Python 3.10 runtime compatibility.
                except (KeyError, TypeError, ValueError) as exc:
                    raise MediaArchiveManifestError(
                        "Identidade original do manifesto inválida.",
                    ) from exc
                previous_manifest_state = (
                    cycle.manifest_version,
                    cycle.manifest,
                    cycle.manifest_sha256,
                    cycle.object_count,
                    cycle.total_bytes,
                )
            manifest, manifest_bytes, manifest_hash = build_archive_manifest(
                cycle=cycle, operation=operation, objects=media_rows,
                manifest_operation_id=manifest_operation_id,
                created_at=manifest_created_at,
            )
            if previous_manifest is not None and (
                manifest != previous_manifest or manifest_bytes != previous_manifest_bytes
            ):
                assert previous_manifest_state is not None
                (
                    cycle.manifest_version,
                    cycle.manifest,
                    cycle.manifest_sha256,
                    cycle.object_count,
                    cycle.total_bytes,
                ) = previous_manifest_state
                raise MediaArchiveManifestError(
                    "Snapshot atual diverge do manifesto imutável do ciclo.",
                )
            manifest_row = db.scalar(select(MediaArchiveObject).where(
                MediaArchiveObject.tenant_id == claim.tenant_id,
                MediaArchiveObject.cycle_id == cycle.id,
                MediaArchiveObject.source_ref == _MANIFEST_SOURCE_REF,
            ))
            if manifest_row is None:
                manifest_row = MediaArchiveObject(
                    id=uuid4(), tenant_id=claim.tenant_id, cycle_id=cycle.id,
                    source_ref=_MANIFEST_SOURCE_REF, object_type="manifest",
                    mime_type="application/json", size_bytes=len(manifest_bytes),
                    sha256=manifest_hash,
                )
                db.add(manifest_row)
            elif (
                manifest_row.object_type != "manifest"
                or manifest_row.mime_type != "application/json"
                or manifest_row.size_bytes != len(manifest_bytes)
                or manifest_row.sha256 != manifest_hash
            ):
                raise MediaArchiveManifestError("Manifesto diverge do objeto persistido.")
            db.commit()

            if not manifest_row.remote_object_id:
                renew_operation_lease(
                    db, operation_id=claim.operation_id, lease_token=claim.lease_token,
                )
                remote_write_started = True
                receipt = storage.upload_object(
                    object_key=_object_key(
                        tenant_id=claim.tenant_id,
                        parent_gallery_id=cycle.parent_gallery_id,
                        folder_id=cycle.folder_id,
                        cycle_id=cycle.id,
                        object_id=manifest_row.id,
                    ),
                    mime_type="application/json",
                    size_bytes=len(manifest_bytes),
                    sha256=manifest_hash,
                    stream=BytesIO(manifest_bytes),
                )
                _validate_receipt(
                    receipt, expected_size=len(manifest_bytes),
                    expected_mime="application/json",
                )
                manifest_row.remote_object_id = receipt.remote_id
                db.commit()
            checkpoint("manifest_readback")
            if not manifest_row.remote_object_id:
                raise MediaArchiveExecutorError("Manifesto sem identidade remota no catálogo.")
            renew()
            _verify_remote_object(
                storage,
                remote_id=manifest_row.remote_object_id,
                size_bytes=manifest_row.size_bytes,
                mime_type=manifest_row.mime_type,
                sha256_hex=manifest_row.sha256,
                renew=renew,
            )
            stored_manifest, stored_bytes = validate_stored_archive_manifest(cycle)
            if stored_bytes != manifest_bytes or stored_manifest != manifest:
                raise MediaArchiveManifestError("Manifesto persistido diverge do conteúdo enviado.")
            checkpoint("manifest_readback", {
                "readback_verified": True,
                "manifest_readback_verified": True,
                "verified_object_count": verified_count,
            })
            begin_archive_cleanup(
                db, operation_id=claim.operation_id, lease_token=claim.lease_token,
            )
        else:
            details = dict(operation.details or {})
            if (
                cycle.state != "archived"
                or details.get("readback_verified") is not True
                or details.get("manifest_readback_verified") is not True
                or details.get("cleanup_started") is not True
            ):
                raise MediaArchiveTransitionError("O cleanup retomado não possui prova íntegra.")

        cleanup_started = True
        operation, cycle = _load_operation_scope(db, claim)
        rows = _object_rows(db, tenant_id=claim.tenant_id, cycle_id=cycle.id)
        _cleanup_local_media(
            db, tenant_id=claim.tenant_id, cycle=cycle, rows=rows,
            operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        operation, cycle = _load_operation_scope(db, claim)
        details = dict(operation.details or {})
        details["local_cleanup_complete"] = True
        operation.details = details
        db.commit()
        complete_archive_operation(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        return MediaArchiveExecutionResult(claim.operation_id, "completed")
    except MediaArchivePreflightError as exc:
        error_code = exc.code
        outcome = "proven_failure"
    except MediaArchiveLeaseConflict:
        raise
    except MediaArchiveTransitionError:
        raise
    except Exception:  # noqa: BLE001 -- Adapter externo é não confiável; guardar só código fixo.
        outcome = "unknown" if remote_write_started or cleanup_started else "proven_failure"
        if outcome == "unknown":
            error_code = "archive_result_unknown"
    fail_operation(
        db,
        operation_id=claim.operation_id,
        lease_token=claim.lease_token,
        outcome=outcome,
        error_code=error_code,
    )
    return MediaArchiveExecutionResult(
        claim.operation_id,
        "reconciliation_required" if outcome == "unknown" else "failed",
        error_code,
    )


def _cleanup_local_media(
    db: Session,
    *,
    tenant_id: UUID,
    cycle: MediaArchiveCycle,
    rows: list[MediaArchiveObject],
    operation_id: UUID,
    lease_token: str,
) -> None:
    for row in rows:
        if row.object_type == "manifest":
            continue
        renew_operation_lease(
            db, operation_id=operation_id, lease_token=lease_token,
        )
        target = resolve_archive_target_path(
            db,
            tenant_id=tenant_id,
            parent_gallery_id=cycle.parent_gallery_id,
            folder_id=cycle.folder_id,
            source_ref=row.source_ref,
            object_type=row.object_type,
        )
        _unlink_verified(
            target,
            root=_target_root(row.object_type),
            size_bytes=row.size_bytes,
            digest=row.sha256,
        )


def _verify_restore_manifest(
    storage: MediaArchiveStorage,
    *,
    cycle: MediaArchiveCycle,
    rows: list[MediaArchiveObject],
    renew,
) -> None:
    manifest, manifest_bytes = validate_stored_archive_manifest(cycle)
    manifest_rows = [row for row in rows if row.object_type == "manifest"]
    if len(manifest_rows) != 1:
        raise MediaArchiveManifestError("O ciclo não contém um manifesto único.")
    row = manifest_rows[0]
    manifest_digest = sha256(manifest_bytes).hexdigest()
    if (
        not row.remote_object_id
        or not _REMOTE_ID.fullmatch(row.remote_object_id)
        or row.mime_type != "application/json"
        or row.size_bytes != len(manifest_bytes)
        or row.sha256 != manifest_digest
        or cycle.manifest_sha256 != manifest_digest
        or manifest.get("object_count") != cycle.object_count
    ):
        raise MediaArchiveManifestError("O catálogo do manifesto diverge do ciclo.")
    _verify_remote_object(
        storage,
        remote_id=row.remote_object_id,
        size_bytes=row.size_bytes,
        mime_type=row.mime_type,
        sha256_hex=row.sha256,
        renew=renew,
    )


def _restore_targets(
    db: Session,
    *,
    tenant_id: UUID,
    cycle: MediaArchiveCycle,
    rows: list[MediaArchiveObject],
) -> dict[UUID, Path]:
    media_rows = [row for row in rows if row.object_type != "manifest"]
    if len(media_rows) != cycle.object_count or not media_rows:
        raise MediaArchiveManifestError("A quantidade de objetos não corresponde ao ciclo.")
    return {
        row.id: resolve_archive_target_path(
            db,
            tenant_id=tenant_id,
            parent_gallery_id=cycle.parent_gallery_id,
            folder_id=cycle.folder_id,
            source_ref=row.source_ref,
            object_type=row.object_type,
        )
        for row in media_rows
    }


def _assert_existing_targets_match(
    rows: list[MediaArchiveObject],
    *,
    targets: dict[UUID, Path],
    renew,
    require_all: bool,
) -> None:
    for row in rows:
        if row.object_type == "manifest":
            continue
        actual = _local_file_digest(targets[row.id], renew=renew)
        if actual is None:
            if require_all:
                raise MediaArchiveSourceError("Objeto promovido está ausente no destino local.")
            continue
        if actual != (row.size_bytes, row.sha256):
            raise MediaArchiveSourceError("Destino local diverge do objeto arquivado.")


def _assert_restore_space_is_reserved(
    db: Session,
    *,
    tenant_id: UUID,
    operation_id: UUID,
) -> None:
    reservations = list(db.scalars(select(MediaArchiveSpaceReservation).where(
        MediaArchiveSpaceReservation.tenant_id == tenant_id,
        MediaArchiveSpaceReservation.operation_id == operation_id,
        MediaArchiveSpaceReservation.status == "active",
    )))
    if not reservations:
        raise MediaArchiveStagingError(
            "A capacidade da recuperação não está mais reservada.",
            code="space_reservation_missing",
        )


def execute_restore_operation(
    db: Session,
    claim: MediaArchiveClaim,
    *,
    storage: MediaArchiveStorage,
    staging_root: Path | str | None = None,
    capacity_provider=None,
) -> MediaArchiveExecutionResult:
    """Puxa, verifica e promove mídia sem expor ciclo ou cobrar antes do fim."""
    begun = False
    current_stage: str | None = None
    promotion_started = False
    rows: list[MediaArchiveObject] = []
    error_code = "restore_failed"
    renew = _lease_refresher(db, claim)
    try:
        begin_restore_operation(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        begun = True
        renew_operation_lease(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        cycle, operation, rows = validate_restore_catalog(
            db, tenant_id=claim.tenant_id, operation_id=claim.operation_id,
        )
        current_stage = operation.stage
        promotion_started = current_stage in {"promoting", "verified_promoted"}
        targets = _restore_targets(
            db, tenant_id=claim.tenant_id, cycle=cycle, rows=rows,
        )

        def checkpoint(stage: str, details_patch: dict | None = None) -> None:
            nonlocal current_stage
            stages = ("preflight", "downloading", "verifying", "promoting", "verified_promoted")
            current_rank = stages.index(current_stage) if current_stage in stages else -1
            next_rank = stages.index(stage)
            if next_rank < current_rank:
                return
            checkpoint_operation(
                db,
                operation_id=claim.operation_id,
                lease_token=claim.lease_token,
                stage=stage,
                details_patch=details_patch,
            )
            current_stage = stage

        details = dict(operation.details or {})
        if current_stage == "preflight" and details.get("restore_space_reserved") is not True:
            if capacity_provider is None:
                reservations = reserve_restore_space(
                    db,
                    tenant_id=claim.tenant_id,
                    operation_id=claim.operation_id,
                    staging_root=staging_root,
                )
            else:
                reservations = reserve_restore_space(
                    db,
                    tenant_id=claim.tenant_id,
                    operation_id=claim.operation_id,
                    staging_root=staging_root,
                    capacity_provider=capacity_provider,
                )
            checkpoint("preflight", {
                "restore_space_reserved": True,
                "restore_reserved_volume_count": len(reservations),
            })
        else:
            _assert_restore_space_is_reserved(
                db, tenant_id=claim.tenant_id, operation_id=claim.operation_id,
            )

        renew_operation_lease(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        operation = db.scalar(select(MediaArchiveOperation).where(
            MediaArchiveOperation.id == claim.operation_id,
            MediaArchiveOperation.tenant_id == claim.tenant_id,
            MediaArchiveOperation.operation_type == "restore",
            MediaArchiveOperation.status == "processing",
        ))
        cycle = db.scalar(select(MediaArchiveCycle).where(
            MediaArchiveCycle.id == operation.cycle_id,
            MediaArchiveCycle.tenant_id == claim.tenant_id,
        )) if operation else None
        if operation is None or cycle is None:
            raise MediaArchiveTransitionError("A operação de recuperação não está mais ativa.")
        details = dict(operation.details or {})
        media_rows = [row for row in rows if row.object_type != "manifest"]

        if current_stage == "verified_promoted":
            if (
                details.get("restore_readback_verified") is not True
                or details.get("restore_manifest_verified") is not True
                or details.get("restored_object_count") != cycle.object_count
                or details.get("promoted_object_count") != cycle.object_count
            ):
                raise MediaArchiveTransitionError("A retomada final não tem prova completa de integridade.")
            _assert_existing_targets_match(
                rows, targets=targets, renew=renew, require_all=True,
            )
        else:
            _verify_restore_manifest(storage, cycle=cycle, rows=rows, renew=renew)
            checkpoint("downloading")
            for row in media_rows:
                destination = staging_object_path(
                    claim.tenant_id, claim.operation_id, row.id, root=staging_root,
                )
                renew_operation_lease(
                    db, operation_id=claim.operation_id, lease_token=claim.lease_token,
                )
                _download_verified_object(
                    storage, row=row, destination=destination, renew=renew,
                )

            checkpoint("verifying", {
                "restore_readback_verified": True,
                "restore_manifest_verified": True,
                "restored_object_count": len(media_rows),
            })
            _assert_existing_targets_match(
                rows, targets=targets, renew=renew, require_all=False,
            )
            for row in media_rows:
                staged = staging_object_path(
                    claim.tenant_id, claim.operation_id, row.id, root=staging_root,
                )
                if not _matches_local_object(
                    staged, size_bytes=row.size_bytes, digest=row.sha256, renew=renew,
                ):
                    raise MediaArchiveStagingError("Staging não contém o objeto íntegro esperado.")

            checkpoint("promoting")
            promotion_started = True
            for row in media_rows:
                staged = staging_object_path(
                    claim.tenant_id, claim.operation_id, row.id, root=staging_root,
                )
                _promote_verified_object(
                    source=staged,
                    target=targets[row.id],
                    root=_target_root(row.object_type),
                    operation_id=claim.operation_id,
                    object_id=row.id,
                    size_bytes=row.size_bytes,
                    digest=row.sha256,
                    renew=renew,
                )
            _assert_existing_targets_match(
                rows, targets=targets, renew=renew, require_all=True,
            )
            checkpoint("verified_promoted", {
                "restore_readback_verified": True,
                "restore_manifest_verified": True,
                "restored_object_count": len(media_rows),
                "promoted_object_count": len(media_rows),
            })

        cleanup_restore_staging(
            claim.tenant_id,
            claim.operation_id,
            [row.id for row in media_rows],
            root=staging_root,
        )
        complete_restore_operation(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        return MediaArchiveExecutionResult(claim.operation_id, "completed")
    except MediaArchiveLeaseConflict:
        raise
    except MediaArchiveTransitionError:
        raise
    except MediaArchiveStagingError as exc:
        error_code = exc.code
        outcome = "unknown" if promotion_started else "proven_failure"
    except MediaArchiveSourceError:
        error_code = "restore_target_invalid"
        outcome = "unknown" if promotion_started else "proven_failure"
    except Exception as exc:  # noqa: BLE001 -- Nunca persistir mensagem/traceback do adapter.
        outcome = "unknown" if promotion_started else "proven_failure"
        class_name = type(exc).__name__
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,22}", class_name):
            error_code = f"restore_{class_name.lower()}"
        else:
            error_code = "restore_result_unknown" if outcome == "unknown" else "restore_failed"

    if not begun:
        raise MediaArchiveTransitionError("A recuperação não iniciou uma transição segura.")
    db.rollback()
    if outcome == "proven_failure":
        try:
            cleanup_restore_staging(
                claim.tenant_id,
                claim.operation_id,
                [row.id for row in rows if row.object_type != "manifest"],
                root=staging_root,
            )
        except MediaArchiveStagingError:
            outcome = "unknown"
            error_code = "restore_cleanup_unknown"
    fail_operation(
        db,
        operation_id=claim.operation_id,
        lease_token=claim.lease_token,
        outcome=outcome,
        error_code=error_code,
    )
    return MediaArchiveExecutionResult(
        claim.operation_id,
        "reconciliation_required" if outcome == "unknown" else "failed",
        error_code,
    )


def _load_delete_operation_scope(
    db: Session,
    claim: MediaArchiveClaim,
) -> tuple[MediaArchiveOperation, MediaArchiveCycle]:
    operation = db.scalar(select(MediaArchiveOperation).where(
        MediaArchiveOperation.id == claim.operation_id,
        MediaArchiveOperation.tenant_id == claim.tenant_id,
        MediaArchiveOperation.operation_type == "delete_remote",
        MediaArchiveOperation.status == "processing",
        MediaArchiveOperation.lease_token == claim.lease_token,
    ))
    cycle = db.scalar(select(MediaArchiveCycle).where(
        MediaArchiveCycle.id == operation.cycle_id,
        MediaArchiveCycle.tenant_id == claim.tenant_id,
    )) if operation else None
    if operation is None or cycle is None or cycle.state != "deleting":
        raise MediaArchiveTransitionError("A exclusão não pertence ao lease ou ciclo ativo.")
    return operation, cycle


def execute_delete_operation(
    db: Session,
    claim: MediaArchiveClaim,
    *,
    storage: MediaArchiveStorage,
) -> MediaArchiveExecutionResult:
    """Remove mídia somente após conferir manifesto e conteúdo; storage é injetado."""
    from app.tenant_media_deletion import validate_cycle_catalog_for_deletion

    begun = False
    delete_call_inflight = False
    remote_state_uncertain = False
    error_code = "deletion_failed"
    renew = _lease_refresher(db, claim)
    try:
        begin_delete_operation(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        begun = True
        renew_operation_lease(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        operation, cycle = _load_delete_operation_scope(db, claim)
        rows = _object_rows(db, tenant_id=claim.tenant_id, cycle_id=cycle.id)
        catalog_error = validate_cycle_catalog_for_deletion(cycle, tuple(rows))
        if catalog_error:
            error_code = catalog_error
            raise MediaArchiveExecutorError("O catálogo de exclusão diverge do manifesto.")

        stages = _DELETE_STAGES
        current_stage = operation.stage
        current_rank = stages.index(current_stage) if current_stage in stages else -1

        def checkpoint(stage: str, details_patch: dict | None = None) -> None:
            nonlocal current_rank, current_stage
            rank = stages.index(stage)
            if rank < current_rank:
                return
            checkpoint_operation(
                db,
                operation_id=claim.operation_id,
                lease_token=claim.lease_token,
                stage=stage,
                details_patch=details_patch,
            )
            current_rank, current_stage = rank, stage

        checkpoint("manifest_verified", {"manifest_catalog_verified": True})
        manifest_rows = [row for row in rows if row.object_type == "manifest"]
        media_rows = [row for row in rows if row.object_type != "manifest"]
        if len(manifest_rows) != 1 or len(media_rows) != cycle.object_count:
            error_code = "catalog_incomplete"
            raise MediaArchiveExecutorError("O manifesto não descreve o catálogo arquivado.")

        ordered_rows = [*media_rows, *manifest_rows]
        if not media_rows:
            # Mantém a sequência de checkpoints antes de excluir o manifesto.
            checkpoint("objects_deleting")
        for row in ordered_rows:
            renew()
            if row.object_type == "manifest":
                if any(item.remote_deleted_at is None for item in media_rows):
                    error_code = "media_objects_pending"
                    raise MediaArchiveExecutorError("O manifesto não pode ser removido antes da mídia.")
                checkpoint("manifest_deleting")
            else:
                checkpoint("objects_deleting")

            if not row.remote_object_id or not _REMOTE_ID.fullmatch(row.remote_object_id):
                error_code = "remote_identity_unavailable"
                raise MediaArchiveExecutorError("Objeto sem identidade remota validada.")

            remote_state_uncertain = True
            metadata = storage.read_object(remote_id=row.remote_object_id)
            remote_state_uncertain = False
            if row.remote_deleted_at is not None:
                if metadata is not None:
                    error_code = "remote_object_reappeared"
                    raise MediaArchiveDeletionResultUnknown("Um objeto já confirmado reapareceu.")
                continue

            if metadata is None:
                mark_remote_object_deleted(
                    db,
                    operation_id=claim.operation_id,
                    lease_token=claim.lease_token,
                    object_id=row.id,
                )
                continue
            _validate_receipt(
                metadata,
                expected_size=row.size_bytes,
                expected_mime=row.mime_type,
            )
            try:
                _verify_remote_object(
                    storage,
                    remote_id=row.remote_object_id,
                    size_bytes=row.size_bytes,
                    mime_type=row.mime_type,
                    sha256_hex=row.sha256,
                    renew=renew,
                )
            except MediaArchiveExecutorError:
                error_code = "remote_content_unverified"
                raise

            delete_call_inflight = True
            storage.delete_object(remote_id=row.remote_object_id)
            remote_state_uncertain = True
            readback = storage.read_object(remote_id=row.remote_object_id)
            remote_state_uncertain = False
            if readback is not None:
                delete_call_inflight = False
                error_code = "remote_delete_not_verified"
                raise MediaArchiveExecutorError("O objeto permaneceu no storage após a exclusão.")
            mark_remote_object_deleted(
                db,
                operation_id=claim.operation_id,
                lease_token=claim.lease_token,
                object_id=row.id,
            )
            delete_call_inflight = False

        for row in rows:
            if row.remote_deleted_at is None:
                error_code = "deletion_checkpoint_incomplete"
                raise MediaArchiveExecutorError("Falta checkpoint remoto para um objeto.")
            remote_state_uncertain = True
            readback = storage.read_object(remote_id=row.remote_object_id or "")
            remote_state_uncertain = False
            if readback is not None:
                error_code = "remote_object_reappeared"
                raise MediaArchiveDeletionResultUnknown("Um objeto excluído reapareceu no readback final.")
            renew()

        checkpoint("objects_verified", {
            "final_readback_verified": True,
            "verified_deleted_object_count": len(rows),
        })
        completed = complete_delete_operation(
            db, operation_id=claim.operation_id, lease_token=claim.lease_token,
        )
        if not completed:
            return MediaArchiveExecutionResult(claim.operation_id, "failed", "inventory_changed")
        return MediaArchiveExecutionResult(claim.operation_id, "completed")
    except MediaArchiveLeaseConflict:
        raise
    except MediaArchiveTransitionError:
        raise
    except MediaArchiveDeletionResultUnknown:
        outcome = "unknown"
    except MediaArchiveExecutorError:
        outcome = "unknown" if remote_state_uncertain or delete_call_inflight else "proven_failure"
    except Exception as exc:  # noqa: BLE001 -- Nunca salvar mensagens ou detalhes do adapter.
        outcome = "unknown" if remote_state_uncertain or delete_call_inflight else "proven_failure"
        if error_code == "deletion_failed":
            class_name = type(exc).__name__
            error_code = (
                f"deletion_{class_name.lower()}"
                if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,20}", class_name)
                else "deletion_adapter_error"
            )[:32]

    if not begun:
        raise MediaArchiveTransitionError("A exclusão não passou pelo início protegido.")
    db.rollback()
    fail_operation(
        db,
        operation_id=claim.operation_id,
        lease_token=claim.lease_token,
        outcome=outcome,
        error_code=error_code,
    )
    return MediaArchiveExecutionResult(
        claim.operation_id,
        "reconciliation_required" if outcome == "unknown" else "failed",
        error_code,
    )
