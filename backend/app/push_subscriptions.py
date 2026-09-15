"""Adesão explícita por instalação, com credenciais cifradas e isolamento de conta."""

import base64
import hashlib
import json
import os
import re
import secrets
from urllib.parse import urlsplit
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import AdminUser, AuthSession, Client, PushSubscription, now

INSTALLATION_COOKIE = "pick_push_installation"
MAX_DEVICES = 10


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def cipher() -> Fernet:
    try:
        return Fernet(os.environ["PUSH_SUBSCRIPTION_ENCRYPTION_KEY"].encode())
    except (KeyError, ValueError):
        raise ValueError("Configuração segura de push indisponível.") from None


def push_enabled() -> bool:
    return os.getenv("WEB_PUSH_ENABLED", "false").lower() == "true"


def validate_endpoint(endpoint: str) -> str:
    if not isinstance(endpoint, str) or len(endpoint) > 4096:
        raise ValueError("Endpoint push inválido.")
    try:
        parsed = urlsplit(endpoint)
        host = parsed.hostname or ""
        supported = host in {"fcm.googleapis.com", "updates.push.services.mozilla.com"} or bool(
            re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.push\.apple\.com", host)
            or re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.notify\.windows\.com", host))
        if (parsed.scheme != "https" or not supported or parsed.port not in {None, 443}
            or parsed.username or parsed.password or parsed.fragment or not parsed.path
            or any(ord(char) < 33 or ord(char) > 126 for char in endpoint) or "\\" in endpoint):
            raise ValueError
    except ValueError:
        raise ValueError("Provedor push não permitido.") from None
    return endpoint


def decode_key(value: str, length: int) -> bytes:
    if not isinstance(value, str) or len(value) > 128 or not re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", value):
        raise ValueError("Inscrição push inválida.")
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if len(raw) != length:
        raise ValueError("Inscrição push inválida.")
    return raw


def validate_subscription(payload: dict) -> dict:
    if set(payload) - {"endpoint", "keys", "expirationTime"} or not isinstance(payload.get("keys"), dict):
        raise ValueError("Inscrição push inválida.")
    keys = payload["keys"]
    if set(keys) != {"auth", "p256dh"}:
        raise ValueError("Inscrição push inválida.")
    try:
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), decode_key(keys["p256dh"], 65))
        decode_key(keys["auth"], 16)
    except (ValueError, TypeError):
        raise ValueError("Inscrição push inválida.") from None
    return {"endpoint": validate_endpoint(payload.get("endpoint")), "keys": keys}


def installation_key(request: Request, response: Response) -> str:
    raw = request.cookies.get(INSTALLATION_COOKIE, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", raw):
        raw = secrets.token_urlsafe(32)
        response.set_cookie(INSTALLATION_COOKIE, raw, httponly=True,
                            secure=os.getenv("APP_ENV", "development") != "development",
                            samesite="strict", max_age=365 * 86400, path="/")
    return fingerprint(raw)


def revoke_installation(db: Session, installation: str, session: AuthSession) -> None:
    for item in db.scalars(select(PushSubscription).where(
        PushSubscription.installation_fingerprint == installation,
        PushSubscription.role == session.role, PushSubscription.subject_id == session.subject_id,
    ).with_for_update()):
        item.active = False
        item.generation += 1
        item.updated_at = now()


def detach_previous_identity(db: Session, request: Request, role: str, subject_id) -> None:
    raw = request.cookies.get(INSTALLATION_COOKIE)
    if not raw:
        return
    for item in db.scalars(select(PushSubscription).where(
        PushSubscription.installation_fingerprint == fingerprint(raw),
    ).with_for_update()):
        if item.role != role or item.subject_id != subject_id:
            item.active = False
            item.generation += 1
            item.updated_at = now()


def subscribe(db: Session, session: AuthSession, installation: str, payload: dict) -> PushSubscription:
    owner_model = AdminUser if session.role == "admin" else Client
    if not db.scalar(select(owner_model).where(owner_model.id == session.subject_id).with_for_update()):
        raise HTTPException(status_code=403, detail="Acesso negado.")
    data = validate_subscription(payload)
    endpoint_fp = fingerprint(data["endpoint"])
    item = db.scalar(select(PushSubscription).where(
        PushSubscription.endpoint_fingerprint == endpoint_fp).with_for_update())
    if item and item.installation_fingerprint != installation:
        raise ValueError("Inscrição pertence a outra instalação. Reative no dispositivo.")
    others = list(db.scalars(select(PushSubscription).where(
        PushSubscription.installation_fingerprint == installation).with_for_update()))
    for other in others:
        if not item or other.id != item.id:
            other.active = False
            other.generation += 1
            other.installation_fingerprint = None
    count = db.scalar(select(func.count(PushSubscription.id)).where(
        PushSubscription.role == session.role, PushSubscription.subject_id == session.subject_id,
        PushSubscription.active, PushSubscription.id != (item.id if item else uuid4()),
    ))
    if count >= MAX_DEVICES:
        raise ValueError("Limite de dispositivos atingido. Desative um dispositivo primeiro.")
    if not item:
        item = PushSubscription(id=uuid4(), endpoint_fingerprint=endpoint_fp,
                                installation_fingerprint=installation, generation=1)
        db.add(item)
    else:
        item.generation += 1
    item.role, item.subject_id, item.session_id = session.role, session.subject_id, session.id
    item.active = True
    item.updated_at = now()
    item.encrypted_subscription = cipher().encrypt(json.dumps({
        "id": str(item.id), "role": item.role, "subject_id": str(item.subject_id),
        "generation": item.generation, "subscription": data,
    }).encode()).decode()
    db.flush()
    return item


def decrypt_subscription(item: PushSubscription) -> dict:
    try:
        envelope = json.loads(cipher().decrypt(item.encrypted_subscription.encode()))
        if (envelope["id"] != str(item.id) or envelope["role"] != item.role
            or envelope["subject_id"] != str(item.subject_id) or envelope["generation"] != item.generation):
            raise ValueError
        data = validate_subscription(envelope["subscription"])
        if fingerprint(data["endpoint"]) != item.endpoint_fingerprint:
            raise ValueError
        return data
    except (InvalidToken, KeyError, ValueError, TypeError):
        raise ValueError("Inscrição push indisponível.") from None
