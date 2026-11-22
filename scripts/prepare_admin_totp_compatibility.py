"""Prepara artefato local TOTP compatível; não publica nem acessa serviços."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_FIELDS = '''    _totp_secret_legacy: Mapped[str | None] = mapped_column(
        "totp_secret", String(128), nullable=True,
    )
    _totp_secret_envelope: Mapped[str | None] = mapped_column(
        "totp_secret_envelope", String(768), nullable=True,
    )
    totp_last_used_step: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def totp_secret(self) -> str:
        if "_totp_secret_envelope" in _totp_bridge_inspect(self).expired_attributes:
            _ = self._totp_secret_envelope
        value = getattr(self, "_totp_secret_value", None)
        if not value:
            raise _totp_bridge_error()
        if (_totp_bridge_inspect(self).persistent
                and getattr(self, "_totp_secret_needs_encryption", False)):
            _totp_bridge_flag_modified(self, "_totp_secret_envelope")
        return value

    @totp_secret.setter
    def totp_secret(self, value: str) -> None:
        self._totp_secret_value = value
        self._totp_secret_needs_encryption = True
        self._totp_secret_envelope = "pending-encryption"
'''
BRIDGE_IMPORTS = '''from sqlalchemy import event as _totp_bridge_event
from sqlalchemy import inspect as _totp_bridge_inspect
from sqlalchemy.orm.attributes import flag_modified as _totp_bridge_flag_modified
from app.totp_crypto import TotpSecretCipher as _totp_bridge_cipher
from app.totp_crypto import TotpSecretError as _totp_bridge_error
from app.totp_crypto import legacy_totp_dual_write_enabled as _totp_bridge_dual_write
'''
BRIDGE_SUPPORT = '''

def _totp_bridge_decode(admin):
    legacy = admin._totp_secret_legacy
    envelope = admin._totp_secret_envelope
    if envelope is not None and not _totp_bridge_cipher.is_envelope(envelope):
        raise _totp_bridge_error()
    if (_totp_bridge_dual_write() and isinstance(legacy, str)
            and legacy and len(legacy) <= 128):
        needs_encryption = True
        if envelope is not None:
            current = _totp_bridge_cipher.from_environment().decrypt(envelope, admin_id=admin.id)
            needs_encryption = current != legacy
        admin._totp_secret_value = legacy
        admin._totp_secret_needs_encryption = needs_encryption
        if needs_encryption:
            _totp_bridge_flag_modified(admin, "_totp_secret_envelope")
        return
    if envelope is not None:
        admin._totp_secret_value = _totp_bridge_cipher.from_environment().decrypt(
            envelope, admin_id=admin.id,
        )
        admin._totp_secret_needs_encryption = False
        return
    if isinstance(legacy, str) and legacy and len(legacy) <= 128:
        admin._totp_secret_value = legacy
        admin._totp_secret_needs_encryption = True
        _totp_bridge_flag_modified(admin, "_totp_secret_envelope")
        return
    raise _totp_bridge_error()


@_totp_bridge_event.listens_for(AdminUser, "load")
def _totp_bridge_load(admin, _context):
    _totp_bridge_decode(admin)


@_totp_bridge_event.listens_for(AdminUser, "refresh")
def _totp_bridge_refresh(admin, _context, attrs):
    if (attrs is None or "_totp_secret_envelope" in attrs
            or "_totp_secret_legacy" in attrs):
        _totp_bridge_decode(admin)


@_totp_bridge_event.listens_for(Session, "before_flush")
def _totp_bridge_flush(session, _flush_context, _instances):
    pending = [admin for admin in session.new.union(session.dirty)
               if isinstance(admin, AdminUser)
               and getattr(admin, "_totp_secret_needs_encryption", False)]
    if not pending:
        return
    cipher = _totp_bridge_cipher.from_environment()
    for admin in pending:
        if admin.id is None:
            admin.id = uuid4()
        secret = admin.totp_secret
        admin._totp_secret_envelope = cipher.encrypt(secret, admin_id=admin.id)
        admin._totp_secret_legacy = secret if _totp_bridge_dual_write() else None
        admin._totp_secret_needs_encryption = False
'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compatibility_source(source: bytes, *, expected_sha256: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or sha256(source) != expected_sha256:
        raise ValueError("hash do módulo legado diverge do inventário")
    text = source.decode("utf-8")
    tree = ast.parse(text)
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "AdminUser"]
    if len(classes) != 1:
        raise ValueError("AdminUser legado ausente ou ambíguo")
    admin = classes[0]
    fields = [node for node in admin.body if isinstance(node, ast.AnnAssign)
              and isinstance(node.target, ast.Name) and node.target.id == "totp_secret"]
    if len(fields) != 1:
        raise ValueError("mapeamento TOTP legado ausente ou ambíguo")
    field = fields[0]
    if (field.col_offset != 4 or not isinstance(field.value, ast.Call)
            or not isinstance(field.value.func, ast.Name) or field.value.func.id != "mapped_column"
            or len(field.value.args) != 1
            or ast.unparse(field.value.args[0]) != "String(128)"
            or field.value.keywords):
        raise ValueError("formato do mapeamento TOTP legado não reconhecido")
    assigned = {node.target.id for node in admin.body if isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)}
    if assigned.intersection({"_totp_secret_legacy", "_totp_secret_envelope", "totp_last_used_step"}):
        raise ValueError("modelo já contém campos de compatibilidade")
    if any(isinstance(node, ast.Name) and node.id.startswith("_totp_bridge")
           for node in ast.walk(tree)):
        raise ValueError("namespace de compatibilidade já existe")
    future = [node for node in tree.body if isinstance(node, ast.ImportFrom)
              and node.module == "__future__"]
    if not future:
        raise ValueError("módulo legado sem import future esperado")
    lines = text.splitlines(keepends=True)
    newline = "\r\n" if "\r\n" in text else "\n"
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits = [
        (offsets[field.lineno - 1], offsets[field.end_lineno], BRIDGE_FIELDS.replace("\n", newline)),
        (offsets[future[-1].end_lineno], offsets[future[-1].end_lineno],
         BRIDGE_IMPORTS.replace("\n", newline)),
    ]
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    text += newline + BRIDGE_SUPPORT.replace("\n", newline)
    ast.parse(text)
    return text.encode("utf-8")


def prepare_package(source_path: Path, output: Path, *, expected_sha256: str,
                    baseline_image: str, cipher_path: Path | None = None) -> dict:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", baseline_image):
        raise ValueError("image ID de base inválido")
    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError("origem deve ser arquivo regular")
    original = source_path.read_bytes()
    transformed = compatibility_source(original, expected_sha256=expected_sha256)
    cipher_path = cipher_path or ROOT / "backend/app/totp_crypto.py"
    if cipher_path.is_symlink() or not cipher_path.is_file():
        raise ValueError("cipher deve ser arquivo regular")
    cipher = cipher_path.read_bytes()
    compile(cipher, str(cipher_path), "exec")
    if output.exists() or output.is_symlink():
        raise ValueError("diretório de saída deve ser novo")
    manifest = {
        "format": 1,
        "purpose": "admin-totp-compatibility-preparation",
        "baseline_image_id": baseline_image,
        "baseline_tag": "pyp-totp-compat-base:" + baseline_image.split(":", 1)[1],
        "source_auth_sha256": sha256(original),
        "auth_sha256": sha256(transformed),
        "cipher_sha256": sha256(cipher),
        "external_operations_performed": False,
    }
    dockerfile = (
        "FROM " + manifest["baseline_tag"] + "\n"
        "COPY auth.py /app/app/auth.py\n"
        "COPY totp_crypto.py /app/app/totp_crypto.py\n"
        'LABEL io.pickyourpic.totp-compatibility="true"\n'
    ).encode()
    output.mkdir(mode=0o700)
    for name, data in {"auth.py": transformed, "totp_crypto.py": cipher,
                       "Dockerfile": dockerfile,
                       "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode()}.items():
        fd = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as target:
            target.write(data)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-auth", type=Path, required=True)
    parser.add_argument("--expected-auth-sha256", required=True)
    parser.add_argument("--baseline-image", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = prepare_package(args.source_auth, args.output_dir,
                                   expected_sha256=args.expected_auth_sha256,
                                   baseline_image=args.baseline_image)
    except (OSError, ValueError, SyntaxError) as error:
        parser.error(str(error))
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
