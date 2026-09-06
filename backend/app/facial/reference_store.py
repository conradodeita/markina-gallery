"""Armazenamento temporário cifrado e estritamente delimitado por request."""

from __future__ import annotations

import base64
import json
import os
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from app.facial.crypto import FacialCipher, FacialCryptoError, FacialEnvelope, FacialScope


class FacialReferenceError(RuntimeError):
    """Falha sanitizada de validação ou armazenamento da referência."""


def delete_reference_file(root: Path, request_id: UUID) -> bool:
    """Remove pelo ID conhecido durante purge, sem depender da chave já revogada."""

    resolved = root.resolve()
    if resolved == Path(resolved.anchor) or resolved == Path.home().resolve():
        raise FacialReferenceError("Diretório temporário facial inseguro.")
    target = (resolved / f"{request_id}.reference").resolve()
    if target.parent != resolved or target.is_symlink():
        raise FacialReferenceError("Destino temporário facial inválido.")
    try:
        target.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise FacialReferenceError("Referência facial não pôde ser eliminada.") from exc


@dataclass(frozen=True)
class StoredReference:
    locator: FacialEnvelope
    width: int
    height: int
    byte_count: int


class FacialReferenceStore:
    def __init__(
        self,
        root: Path,
        cipher: FacialCipher,
        *,
        max_bytes: int,
        max_pixels: int,
    ) -> None:
        resolved = root.resolve()
        if resolved == Path(resolved.anchor) or resolved == Path.home().resolve():
            raise FacialReferenceError("Diretório temporário facial inseguro.")
        if max_bytes < 1 or max_pixels < 1:
            raise FacialReferenceError("Limites da referência facial inválidos.")
        self._root = resolved
        self._cipher = cipher
        self._max_bytes = max_bytes
        self._max_pixels = max_pixels

    def store(
        self,
        *,
        request_id: UUID,
        gallery_id: UUID,
        model_version: str,
        data_version: str,
        payload: bytes,
    ) -> StoredReference:
        width, height = self._validate_jpeg(payload)
        self._root.mkdir(parents=True, exist_ok=True)
        target = self._target(request_id)
        if target.is_symlink():
            raise FacialReferenceError("Destino temporário facial inválido.")
        image_scope = self._scope(
            request_id=request_id,
            gallery_id=gallery_id,
            model_version=model_version,
            data_version=data_version,
            purpose="reference_image",
        )
        envelope = self._cipher.encrypt(payload, scope=image_scope)
        serialized = json.dumps(
            {
                "ciphertext": base64.urlsafe_b64encode(envelope.ciphertext).decode("ascii"),
                "key_id": envelope.key_id,
                "nonce": base64.urlsafe_b64encode(envelope.nonce).decode("ascii"),
                "version": envelope.version,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        partial = target.with_suffix(".part")
        try:
            partial.write_bytes(serialized)
            partial.chmod(0o600)
            os.replace(partial, target)
        except OSError as exc:
            raise FacialReferenceError("Referência facial não pôde ser armazenada.") from exc
        finally:
            partial.unlink(missing_ok=True)

        locator_scope = self._scope(
            request_id=request_id,
            gallery_id=gallery_id,
            model_version=model_version,
            data_version=data_version,
            purpose="reference_locator",
        )
        locator = self._cipher.encrypt(target.name.encode("ascii"), scope=locator_scope)
        return StoredReference(
            locator=locator,
            width=width,
            height=height,
            byte_count=len(payload),
        )

    def load(
        self,
        *,
        request_id: UUID,
        gallery_id: UUID,
        model_version: str,
        data_version: str,
        locator: FacialEnvelope,
    ) -> bytes:
        target = self._resolve_locator(
            request_id=request_id,
            gallery_id=gallery_id,
            model_version=model_version,
            data_version=data_version,
            locator=locator,
        )
        try:
            record = json.loads(target.read_text(encoding="ascii"))
            envelope = FacialEnvelope(
                ciphertext=base64.b64decode(
                    record["ciphertext"], altchars=b"-_", validate=True
                ),
                nonce=base64.b64decode(record["nonce"], altchars=b"-_", validate=True),
                key_id=record["key_id"],
                version=record["version"],
            )
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise FacialReferenceError("Referência facial indisponível ou inválida.") from exc
        image_scope = self._scope(
            request_id=request_id,
            gallery_id=gallery_id,
            model_version=model_version,
            data_version=data_version,
            purpose="reference_image",
        )
        try:
            return self._cipher.decrypt(envelope, scope=image_scope)
        except FacialCryptoError as exc:
            raise FacialReferenceError("Referência facial indisponível ou inválida.") from exc

    def delete(
        self,
        *,
        request_id: UUID,
        gallery_id: UUID,
        model_version: str,
        data_version: str,
        locator: FacialEnvelope | None = None,
    ) -> bool:
        if locator is None:
            target = self._target(request_id)
        else:
            target = self._resolve_locator(
                request_id=request_id,
                gallery_id=gallery_id,
                model_version=model_version,
                data_version=data_version,
                locator=locator,
            )
        if target.is_symlink():
            raise FacialReferenceError("Destino temporário facial inválido.")
        try:
            target.unlink()
            return True
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise FacialReferenceError("Referência facial não pôde ser eliminada.") from exc

    def _validate_jpeg(self, payload: bytes) -> tuple[int, int]:
        if not payload or len(payload) > self._max_bytes:
            raise FacialReferenceError("Imagem de referência excede o limite permitido.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(payload)) as image:
                    if image.format != "JPEG":
                        raise FacialReferenceError(
                            "A imagem de referência deve estar em formato JPEG."
                        )
                    width, height = image.size
                    if width < 1 or height < 1 or width * height > self._max_pixels:
                        raise FacialReferenceError(
                            "Imagem de referência excede o limite de pixels."
                        )
                    image.verify()
        except FacialReferenceError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise FacialReferenceError(
                "Imagem de referência excede o limite seguro."
            ) from exc
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            raise FacialReferenceError("Imagem de referência inválida.") from exc
        return width, height

    def _target(self, request_id: UUID) -> Path:
        target = (self._root / f"{request_id}.reference").resolve()
        if target.parent != self._root:
            raise FacialReferenceError("Destino temporário facial inválido.")
        return target

    def _resolve_locator(
        self,
        *,
        request_id: UUID,
        gallery_id: UUID,
        model_version: str,
        data_version: str,
        locator: FacialEnvelope,
    ) -> Path:
        scope = self._scope(
            request_id=request_id,
            gallery_id=gallery_id,
            model_version=model_version,
            data_version=data_version,
            purpose="reference_locator",
        )
        try:
            name = self._cipher.decrypt(locator, scope=scope).decode("ascii")
        except (FacialCryptoError, UnicodeError) as exc:
            raise FacialReferenceError("Localizador facial inválido.") from exc
        if name != f"{request_id}.reference" or Path(name).name != name:
            raise FacialReferenceError("Localizador facial inválido.")
        return self._target(request_id)

    @staticmethod
    def _scope(
        *,
        request_id: UUID,
        gallery_id: UUID,
        model_version: str,
        data_version: str,
        purpose,
    ) -> FacialScope:
        return FacialScope(
            environment=os.getenv("APP_ENV", "development").strip(),
            gallery_id=gallery_id,
            object_kind="request",
            object_id=request_id,
            purpose=purpose,
            model_version=model_version,
            data_version=data_version,
        )
