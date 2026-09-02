"""Emissão e resolução de capacidades opacas de acesso a galerias."""

import base64
import hmac
import os
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import GalleryAccessCapability, expired, now


class GalleryCapabilityConfigurationError(RuntimeError):
    """O segredo dedicado de capacidades está ausente ou inseguro."""


def capability_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def validate_gallery_capability_signing_configuration() -> bytes:
    raw = os.getenv("GALLERY_CAPABILITY_SIGNING_KEY", "")
    if not raw and os.getenv("APP_ENV", "development").strip() == "development":
        raw = "markina-development-gallery-capability-key-only"
    if len(raw.encode("utf-8")) < 32:
        raise GalleryCapabilityConfigurationError(
            "GALLERY_CAPABILITY_SIGNING_KEY deve possuir ao menos 32 bytes."
        )
    otp_secret = os.getenv("AUTH_PII_FINGERPRINT_SALT", "")
    if otp_secret and hmac.compare_digest(raw, otp_secret):
        raise GalleryCapabilityConfigurationError(
            "A chave de capacidades deve ser dedicada e diferente do segredo de OTP."
        )
    return raw.encode("utf-8")


def validate_gallery_capability_runtime_configuration() -> None:
    if os.getenv("APP_ENV", "development").strip() != "development":
        validate_gallery_capability_signing_configuration()


def _signed_payload(capability: GalleryAccessCapability) -> bytes:
    target = capability.derived_gallery_id or "-"
    client = capability.client_id or "-"
    return (
        f"gc1:{capability.id}:{capability.token_version}:{capability.scope}:"
        f"{capability.parent_gallery_id}:{target}:{client}"
    ).encode()


def reconstruct_gallery_capability_token(capability: GalleryAccessCapability) -> str:
    if capability.token_mode != "signed_v1":
        raise ValueError("A capacidade legada não pode ser reconstruída.")
    signature = hmac.new(
        validate_gallery_capability_signing_configuration(),
        _signed_payload(capability),
        sha256,
    ).digest()
    encoded = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"gc1.{capability.id}.{capability.token_version}.{encoded}"


def issue_gallery_capability(
    db: Session,
    *,
    parent_gallery_id: UUID,
    scope: str,
    client_id: UUID | None = None,
    derived_gallery_id: UUID | None = None,
    expires_at=None,
    actor_admin_id: UUID | None = None,
    rotated_from_id: UUID | None = None,
    reconstructible: bool = False,
    token_version: int = 1,
) -> tuple[GalleryAccessCapability, str]:
    """Retorna o segredo somente na emissão e persiste exclusivamente seu hash."""

    capability_id = uuid4()
    capability = GalleryAccessCapability(
        id=capability_id,
        parent_gallery_id=parent_gallery_id,
        derived_gallery_id=derived_gallery_id,
        client_id=client_id,
        scope=scope,
        token_hash="0" * 64,
        token_mode="signed_v1" if reconstructible else "legacy_random",
        token_version=token_version,
        status="active",
        expires_at=expires_at,
        actor_admin_id=actor_admin_id,
        rotated_from_id=rotated_from_id,
    )
    db.add(capability)
    db.flush()
    token = (
        reconstruct_gallery_capability_token(capability)
        if reconstructible
        else token_urlsafe(32)
    )
    capability.token_hash = capability_hash(token)
    db.flush()
    return capability, token


def resolve_gallery_capability(
    db: Session, token: str
) -> GalleryAccessCapability | None:
    capability = None
    if token.startswith("gc1."):
        try:
            prefix, raw_id, raw_version, _signature = token.split(".", 3)
            capability_id = UUID(raw_id)
            token_version = int(raw_version)
        except (TypeError, ValueError):
            return None
        if prefix != "gc1" or token_version < 1:
            return None
        candidate = db.get(GalleryAccessCapability, capability_id)
        if (
            candidate
            and candidate.token_mode == "signed_v1"
            and candidate.token_version == token_version
        ):
            expected = reconstruct_gallery_capability_token(candidate)
            if hmac.compare_digest(token, expected) and hmac.compare_digest(
                candidate.token_hash,
                capability_hash(token),
            ):
                capability = candidate
    else:
        capability = db.scalar(
            select(GalleryAccessCapability).where(
                GalleryAccessCapability.token_hash == capability_hash(token)
            )
        )
    if not capability or capability.status != "active":
        return None
    if capability.expires_at and expired(capability.expires_at):
        capability.status = "expired"
        return None
    capability.last_used_at = now()
    return capability


def revoke_gallery_capability(capability: GalleryAccessCapability) -> None:
    if capability.status == "active":
        capability.status = "revoked"
        capability.revoked_at = now()


def consume_gallery_capability(capability: GalleryAccessCapability) -> None:
    """Consome convites individuais somente depois da validação OTP completa."""

    if capability.scope in {"public_gallery", "private_gallery_link"}:
        return
    if capability.status != "active":
        raise ValueError("Somente um convite ativo pode ser consumido.")
    capability.status = "consumed"
    capability.consumed_at = now()


def rotate_gallery_capability(
    db: Session,
    capability: GalleryAccessCapability,
    *,
    actor_admin_id: UUID | None = None,
    reconstructible: bool | None = None,
) -> tuple[GalleryAccessCapability, str]:
    if capability.status != "active":
        raise ValueError("Somente uma capacidade ativa pode ser rotacionada.")
    capability.status = "rotated"
    capability.revoked_at = now()
    db.flush()
    return issue_gallery_capability(
        db,
        parent_gallery_id=capability.parent_gallery_id,
        derived_gallery_id=capability.derived_gallery_id,
        client_id=capability.client_id,
        scope=capability.scope,
        expires_at=capability.expires_at,
        actor_admin_id=actor_admin_id,
        rotated_from_id=capability.id,
        reconstructible=(
            capability.token_mode == "signed_v1"
            if reconstructible is None
            else reconstructible
        ),
        token_version=capability.token_version + 1,
    )
