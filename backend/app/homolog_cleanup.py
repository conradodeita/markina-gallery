"""Inventário e limpeza explícita dos dados sintéticos de homologação.

Não é uma API. O módulo só executa dentro do container Markina com APP_ENV de
homologação e exige uma confirmação literal para a fase destrutiva.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.auth import (
    AuthChallenge,
    AuthSession,
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    GalleryLifecycleOperation,
    ParentGallery,
    ParentGalleryRegistration,
    PaymentCommunication,
    PhotoAsset,
    PhotoSelection,
    Role,
    SaleOrder,
    SessionLocal,
    WhatsAppDelivery,
    WhatsAppDeliveryAttempt,
)
from app.media import derivatives_root, source_root

CONFIRMATION = "DELETE_HOMOLOG_GALLERIES_AND_CLIENTS"
ALLOWED_ENVIRONMENTS = {"homolog", "homologation"}


def require_homolog_environment() -> str:
    environment = os.getenv("APP_ENV", "").strip().lower()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise RuntimeError("A limpeza só pode executar com APP_ENV de homologação.")
    return environment


def _count(db: Session, model, *criteria) -> int:
    statement = select(func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    return int(db.scalar(statement) or 0)


def _media_inventory(root: Path) -> dict[str, int]:
    resolved = root.resolve()
    files = [path for path in resolved.rglob("*") if path.is_file() or path.is_symlink()]
    return {
        "files": len(files),
        "bytes": sum(path.stat().st_size for path in files if path.is_file()),
    }


def inventory(db: Session) -> dict[str, object]:
    return {
        "environment": require_homolog_environment(),
        "database": {
            "clients": _count(db, Client),
            "parent_galleries": _count(db, ParentGallery),
            "derived_galleries": _count(db, DerivedGallery),
            "public_registrations": _count(db, ParentGalleryRegistration),
            "private_memberships": _count(db, DerivedGalleryMembership),
            "photos": _count(db, PhotoAsset),
            "selections": _count(db, PhotoSelection),
            "orders": _count(db, SaleOrder),
            "payment_communications": _count(db, PaymentCommunication),
            "client_sessions": _count(db, AuthSession, AuthSession.role == Role.CLIENT.value),
            "client_otp_challenges": _count(
                db, AuthChallenge, AuthChallenge.kind == "client_otp"
            ),
            "whatsapp_deliveries": _count(db, WhatsAppDelivery),
            "lifecycle_operations": _count(db, GalleryLifecycleOperation),
        },
        "media": {
            "source": _media_inventory(source_root()),
            "derivatives": _media_inventory(derivatives_root()),
            "history": _media_inventory(
                Path(os.getenv("MEDIA_HISTORY_ROOT", "/var/lib/markina/history"))
            ),
        },
    }


def _clear_media_root(root: Path) -> None:
    resolved = root.resolve()
    allowed_root = Path("/var/lib/markina").resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise RuntimeError("Raiz de mídia fora do volume exclusivo da Markina.") from exc
    if not resolved.is_dir():
        return
    entries = sorted(resolved.rglob("*"), key=lambda item: len(item.parts), reverse=True)
    for entry in entries:
        if entry.is_file() or entry.is_symlink():
            entry.unlink()
        elif entry.is_dir():
            entry.rmdir()


def execute(db: Session, confirmation: str) -> dict[str, object]:
    require_homolog_environment()
    if confirmation != CONFIRMATION:
        raise RuntimeError("Confirmação literal inválida; nenhuma alteração foi aplicada.")
    if db.bind is None or db.bind.dialect.name != "postgresql":
        raise RuntimeError("A limpeza homologada exige o PostgreSQL exclusivo da Markina.")

    delivery_ids = select(WhatsAppDelivery.id)
    db.execute(
        delete(WhatsAppDeliveryAttempt).where(
            WhatsAppDeliveryAttempt.delivery_id.in_(delivery_ids)
        )
    )
    db.execute(delete(WhatsAppDelivery))
    db.execute(delete(AuthChallenge).where(AuthChallenge.kind == "client_otp"))
    db.execute(delete(AuthSession).where(AuthSession.role == Role.CLIENT.value))
    db.execute(delete(GalleryLifecycleOperation))
    # O banco é exclusivo da Markina. CASCADE alcança somente tabelas que
    # referenciam as duas raízes operacionais, preservando admin/configurações.
    db.execute(text("TRUNCATE TABLE parent_gallery, client CASCADE"))
    db.commit()

    _clear_media_root(source_root())
    _clear_media_root(derivatives_root())
    _clear_media_root(Path(os.getenv("MEDIA_HISTORY_ROOT", "/var/lib/markina/history")))
    return inventory(db)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("inventory", "execute"), required=True)
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args()
    with SessionLocal() as db:
        result = (
            inventory(db)
            if args.mode == "inventory"
            else execute(db, args.confirmation)
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
