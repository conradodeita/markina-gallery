"""Configuração PIX global, proposta canônica e snapshot de pagamento."""

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import GlobalPixSettings
from app.pix import (
    PixCodeError,
    normalize_pix_configuration,
    normalize_pix_copy_paste,
    pix_qr_data_url,
)


def normalize_configuration(configuration: dict | None) -> dict:
    if configuration is None:
        return {
            "status": "unconfigured",
            "input_type": None,
            "pix_key": None,
            "copy_paste": None,
            "receiver_name": None,
            "receiver_city": None,
            "instructions": None,
        }
    normalized = normalize_pix_configuration(
        configuration.get("copy_paste"),
        receiver_name=configuration.get("receiver_name"),
        receiver_city=configuration.get("receiver_city"),
    )
    if not normalized:
        raise PixCodeError("Informe uma chave PIX ou copia e cola, ou escolha remover o PIX.")
    # Nome/cidade do BR Code pertencem ao próprio código, nunca a campos concorrentes.
    fields = {}
    position = 0
    while position < len(normalized.copy_paste):
        size = int(normalized.copy_paste[position + 2 : position + 4])
        fields[normalized.copy_paste[position : position + 2]] = normalized.copy_paste[
            position + 4 : position + 4 + size
        ]
        position += 4 + size
    if not fields.get("59") or len(fields["59"]) > 25:
        raise PixCodeError("Confira o nome do recebedor no código PIX (até 25 caracteres).")
    if not fields.get("60") or len(fields["60"]) > 15:
        raise PixCodeError("Confira a cidade do recebedor no código PIX (até 15 caracteres).")
    return {
        "status": "active",
        "input_type": normalized.input_type,
        "pix_key": normalized.input_value if normalized.input_type != "br_code" else None,
        "copy_paste": normalized.copy_paste,
        "receiver_name": fields.get("59"),
        "receiver_city": fields.get("60"),
        "instructions": (configuration.get("instructions") or "").strip() or None,
    }


def canonical_proposal(configuration: dict | None, version: int) -> str:
    return json.dumps(
        {"configuration": normalize_configuration(configuration), "version": version},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def global_pix_settings(db: Session) -> GlobalPixSettings | None:
    return db.scalar(select(GlobalPixSettings).where(GlobalPixSettings.singleton == 1))


def pix_payload(settings: GlobalPixSettings | None, *, editable: bool = False) -> dict:
    status = settings.status if settings else "unconfigured"
    qr = None
    if settings and status == "active":
        try:
            qr = pix_qr_data_url(settings.copy_paste)
        except (PixCodeError, TypeError):
            status = "review_required"
    active = status == "active"
    result = {
        "status": status,
        "version": settings.version if settings else 0,
        "scope": "global",
        "checkout_available": active,
        "review_required": status == "review_required",
        "qr_png_data_url": qr,
        "receiver_name": settings.receiver_name if settings and active else None,
        "receiver_city": settings.receiver_city if settings and active else None,
        "instructions": settings.instructions if settings and active else None,
        "settings_url": "/admin/settings#pix",
    }
    if editable:
        result.update(
            {
                "copy_paste": (settings.pix_key or settings.copy_paste)
                if settings and active
                else None,
                "input_type": settings.input_type if settings and active else None,
            }
        )
    return result


def apply_configuration(db: Session, *, admin_id: UUID, proposed: dict) -> GlobalPixSettings:
    settings = global_pix_settings(db)
    version = settings.version if settings else 0
    if version != proposed["version"]:
        raise PixCodeError("O PIX foi alterado em outra sessão. Recarregue e confirme novamente.")
    if not settings:
        settings = GlobalPixSettings(admin_user_id=admin_id)
        db.add(settings)
    elif settings.admin_user_id != admin_id:
        raise PixCodeError("Configuração indisponível para esta conta.")
    for key, value in proposed["configuration"].items():
        setattr(settings, key, value)
    settings.version = version + 1
    settings.legacy_group_count = 0
    db.flush()
    return settings


def proposal_preview(target: str) -> dict:
    """Prévia canônica da proposta; não persiste nem expõe o envelope sensível."""
    proposed = json.loads(target)
    return pix_payload(GlobalPixSettings(
        version=proposed["version"] + 1, **proposed["configuration"]
    ))


def checkout_pix(db: Session) -> GlobalPixSettings:
    settings = global_pix_settings(db)
    if not settings or settings.status != "active" or not settings.copy_paste:
        raise PixCodeError(
            "O pagamento PIX está temporariamente indisponível. Sua seleção foi mantida."
        )
    try:
        normalize_pix_copy_paste(settings.copy_paste)
    except PixCodeError:
        raise PixCodeError(
            "O pagamento PIX está temporariamente indisponível. Sua seleção foi mantida."
        ) from None
    return settings
