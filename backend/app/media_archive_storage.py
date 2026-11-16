"""Contrato de armazenamento externo para adapters de arquivo frio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class ArchiveRemoteObject:
    """Identidade e metadados mínimos retornados pelo armazenamento remoto."""

    remote_id: str
    size_bytes: int
    mime_type: str


@dataclass(frozen=True)
class ArchiveDownloadReceipt:
    """Resultado calculado enquanto o adapter grava bytes no destino privado."""

    size_bytes: int
    sha256: str


class MediaArchiveStorage(Protocol):
    """Contrato injetável; nenhuma credencial ou implementação é descoberta aqui.

    Implementações devem retornar falhas sanitizadas, nunca guardar bytes fora do
    namespace privado configurado e tratar `delete_object` de forma idempotente.
    `upload_object` também deve ser idempotente por `object_key`: conteúdo repetido
    retorna o mesmo objeto; bytes divergentes para a mesma chave são recusados.
    """

    def upload_object(
        self,
        *,
        object_key: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        stream: BinaryIO,
    ) -> ArchiveRemoteObject: ...

    def read_object(self, *, remote_id: str) -> ArchiveRemoteObject | None: ...

    def download_object(
        self,
        *,
        remote_id: str,
        destination: BinaryIO,
    ) -> ArchiveDownloadReceipt: ...

    def delete_object(self, *, remote_id: str) -> None: ...
