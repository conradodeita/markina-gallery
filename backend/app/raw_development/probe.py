"""Cheap container-signature checks before expensive engine decoding."""

from __future__ import annotations

from pathlib import PurePath

from app.raw_development.state import RawDevelopmentStateError

_TIFF_SIGNATURES = {b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+", b"IIU\x00"}


def validate_raw_signature(filename: str, header: bytes, *, supported_suffixes: set[str]) -> str:
    suffix = PurePath(filename).suffix.lower()
    if suffix not in supported_suffixes:
        raise RawDevelopmentStateError("Formato RAW não suportado pelo motor selecionado.")
    if len(header) < 12:
        raise RawDevelopmentStateError("Cabeçalho RAW inválido.")
    if suffix == ".raf":
        valid = header.startswith(b"FUJIFILMCCD-RAW ")
    elif suffix == ".cr3":
        valid = header[4:8] == b"ftyp" and header[8:12] in {b"crx ", b"CRX "}
    elif suffix == ".orf":
        valid = header[:2] in {b"II", b"MM"} and header[2:4] in {b"RO", b"RS"}
    else:
        valid = header[:4] in _TIFF_SIGNATURES
    if not valid:
        raise RawDevelopmentStateError("Assinatura do arquivo não corresponde ao formato declarado.")
    return suffix[1:]
