"""OAuth server-side do Google Drive; clientes e transporte real ficam gated por configuração."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import stat
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

import httpx
from argon2.exceptions import InvalidHashError
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, SecretStr
from sqlalchemy import select

from app.admin_account import AdminAccountError, reauthenticate_admin
from app.auth import (
    AdminUser,
    GoogleDriveConnection,
    GoogleDriveOAuthAttempt,
    Role,
    SessionLocal,
    current_session,
    enforce_rate_limit,
    now,
)
from app.google_drive_client import (
    AUTH_ENDPOINT,
    REVOKE_ENDPOINT,
    SCOPE,
    TOKEN_ENDPOINT,
    DriveTransport,
    HttpxDriveTransport,
)
from app.integration_secrets import (
    IntegrationCipher,
    IntegrationSecretError,
    SecretEnvelope,
)
from app.mercadopago_api import SensitiveRoute
from app.system_monitor.access import is_owner
from app.system_monitor.store import bounded
from app.tenancy import TenantContextError, require_admin_tenant
from app.totp_crypto import TotpSecretError
from app.totp_verification import matching_unused_totp_step

router = APIRouter(prefix="/admin/platform/drive", route_class=SensitiveRoute)
HEADERS = {"Cache-Control": "private, no-store"}
GOOGLE_DRIVE_CLIENT_CONFIG_PATH = Path("/run/secrets/google-drive-oauth-client.json")
GOOGLE_DRIVE_EXPECTED_REDIRECT_URI = (
    "https://markina.pickyourpic.com.br/api/admin/platform/drive/oauth/callback"
)


class ConnectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr
    totp_code: SecretStr


def _config():
    if os.getenv("APP_ENV", "development") != "production":
        raise HTTPException(503, "OAuth real do Drive é habilitado somente em produção.", headers=HEADERS)

    descriptor = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(GOOGLE_DRIVE_CLIENT_CONFIG_PATH, flags)
        metadata = os.fstat(descriptor)
        if (not stat.S_ISREG(metadata.st_mode)
                or (os.name == "posix" and stat.S_IMODE(metadata.st_mode) != 0o400)
                or metadata.st_size <= 0 or metadata.st_size > 16_384):
            raise ValueError()
        with os.fdopen(descriptor, "r", encoding="utf-8") as client_file:
            descriptor = None
            document = json.load(client_file)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError, RecursionError):
        raise HTTPException(503, "Conexão Drive ainda não configurada.", headers=HEADERS) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)

    web = document.get("web") if isinstance(document, dict) and set(document) == {"web"} else None
    client_id = web.get("client_id") if isinstance(web, dict) else None
    client_secret = web.get("client_secret") if isinstance(web, dict) else None
    redirect_uris = web.get("redirect_uris") if isinstance(web, dict) else None
    if (not isinstance(client_id, str) or not client_id or len(client_id) > 256
            or any(not 0x21 <= ord(char) <= 0x7E for char in client_id)
            or not isinstance(client_secret, str) or not client_secret or len(client_secret) > 512
            or any(not 0x21 <= ord(char) <= 0x7E for char in client_secret)
            or not isinstance(redirect_uris, list) or len(redirect_uris) != 1
            or not isinstance(redirect_uris[0], str)):
        raise HTTPException(503, "Conexão Drive ainda não configurada.", headers=HEADERS)
    redirect_uri = redirect_uris[0]
    try:
        parsed_redirect = urlsplit(redirect_uri)
        valid_redirect = (redirect_uri == GOOGLE_DRIVE_EXPECTED_REDIRECT_URI
                          and parsed_redirect.scheme == "https" and bool(parsed_redirect.hostname)
                          and parsed_redirect.port in (None, 443)
                          and parsed_redirect.username is None and parsed_redirect.password is None
                          and not parsed_redirect.query and not parsed_redirect.fragment
                          and not any(ord(char) < 0x21 or ord(char) == 0x7F for char in redirect_uri))
    except ValueError:
        valid_redirect = False
    if not valid_redirect:
        raise HTTPException(503, "Conexão Drive ainda não configurada.", headers=HEADERS)
    return client_id, client_secret, redirect_uri


def _is_production() -> bool:
    return os.getenv("APP_ENV", "development") == "production"


def _owner(request: Request):
    session = current_session(request, Role.ADMIN)
    with SessionLocal() as db:
        bounded(db)
        if not is_owner(db, session.subject_id):
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        try:
            tenant = require_admin_tenant(db, session.subject_id)
        except TenantContextError:
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS) from None
        if tenant.id != session.tenant_id:
            raise HTTPException(403, "Acesso não autorizado.", headers=HEADERS)
        return session, tenant.id


def _cipher():
    try:
        return IntegrationCipher()
    except IntegrationSecretError:
        raise HTTPException(503, "Conexão Drive ainda não configurada.", headers=HEADERS) from None


def _expired(expires_at) -> bool:
    current = now()
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=current.tzinfo)
    return expires_at <= current


@router.get("/status")
def status(request: Request, response: Response):
    response.headers.update(HEADERS)
    _session, tenant_id = _owner(request)
    with SessionLocal() as db:
        bounded(db)
        row = db.scalar(select(GoogleDriveConnection).where(GoogleDriveConnection.tenant_id == tenant_id))
        return {"state": row.state if row else "unknown", "scope": row.scopes if row else None,
                "connected_at": row.connected_at if row and row.state == "connected" else None,
                "quota_limit": row.quota_limit if row and row.state == "connected" else None,
                "quota_usage": row.quota_usage if row and row.state == "connected" else None,
                "quota_observed_at": row.quota_observed_at if row and row.state == "connected" else None}


def observe_storage_quota(*, refresh_token: str, client_id: str, client_secret: str,
                          transport: DriveTransport | None = None) -> tuple[str | None, str | None]:
    """Observação mínima da quota, chamada somente pelo fluxo explícito de produção."""
    if os.getenv("APP_ENV", "development") != "production":
        raise ValueError()
    adapter = transport or HttpxDriveTransport()
    token_response = adapter.post(TOKEN_ENDPOINT, data={"client_id": client_id,
        "client_secret": client_secret, "refresh_token": refresh_token,
        "grant_type": "refresh_token"}, headers={"Accept": "application/json"})
    if token_response.status_code != 200:
        raise ValueError()
    token_data = token_response.json()
    if not isinstance(token_data, dict):
        raise TypeError()
    access_token = token_data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise ValueError()
    about = adapter.get("https://www.googleapis.com/drive/v3/about",
        params={"fields": "storageQuota(limit,usage)"},
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"})
    if about.status_code != 200:
        raise ValueError()
    about_data = about.json()
    if not isinstance(about_data, dict):
        raise TypeError()
    quota = about_data.get("storageQuota")
    if quota is None:
        quota = {}
    if not isinstance(quota, dict):
        raise TypeError()
    limit = quota.get("limit")
    usage = quota.get("usage")
    if limit is not None and (not isinstance(limit, str) or not limit.isdigit()):
        raise ValueError()
    if usage is not None and (not isinstance(usage, str) or not usage.isdigit()):
        raise ValueError()
    return limit, usage


@router.post("/observe-quota")
def observe_quota(request: Request, response: Response):
    from app.main import require_same_origin
    require_same_origin(request)
    _session, tenant_id = _owner(request)
    if os.getenv("APP_ENV", "development") != "production":
        raise HTTPException(503, "Consulta real de quota habilitada somente em produção.", headers=HEADERS)
    client_id, client_secret, _ = _config()
    try:
        cipher = _cipher()
        with SessionLocal() as db:
            bounded(db)
            row = db.scalar(select(GoogleDriveConnection).where(
                GoogleDriveConnection.tenant_id == tenant_id,
                GoogleDriveConnection.state == "connected").with_for_update())
            if not row or not row.refresh_token_envelope:
                raise HTTPException(409, "Drive ainda não está conectado.", headers=HEADERS)
            refresh = cipher.decrypt(SecretEnvelope.from_payload(row.refresh_token_envelope),
                                     tenant_id=tenant_id, credential_id=row.id)
            limit, usage = observe_storage_quota(refresh_token=refresh, client_id=client_id,
                                                 client_secret=client_secret)
            row.quota_limit, row.quota_usage, row.quota_observed_at, row.updated_at = limit, usage, now(), now()
            db.commit()
            response.headers.update(HEADERS)
            return {"state": "connected", "quota_limit": limit, "quota_usage": usage,
                    "quota_observed_at": row.quota_observed_at}
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, TypeError, IntegrationSecretError):
        raise HTTPException(503, "Não foi possível observar a quota do Google Drive.", headers=HEADERS) from None


@router.post("/connect")
def connect(payload: ConnectInput, request: Request):
    from app.main import require_same_origin
    require_same_origin(request)
    session, tenant_id = _owner(request)
    client_id, _, redirect_uri = _config()
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode().rstrip("=")
    attempt_id = uuid4()
    with SessionLocal() as db:
        bounded(db)
        existing = db.scalar(select(GoogleDriveConnection).where(
            GoogleDriveConnection.tenant_id == tenant_id, GoogleDriveConnection.state == "connected"))
        if existing:
            raise HTTPException(409, "Revogue a conexão atual antes de autorizar novamente.", headers=HEADERS)
        enforce_rate_limit(db, "google_drive_connect", str(session.subject_id),
                           request.client.host if request.client else "unknown")
        db.commit()
        try:
            admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id).with_for_update())
        except TotpSecretError:
            raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
        if not admin or len(payload.totp_code.get_secret_value()) != 6:
            raise HTTPException(403, "Credencial inválida.", headers=HEADERS)
        try:
            reauthenticate_admin(admin, payload.current_password.get_secret_value())
            step = matching_unused_totp_step(admin.totp_secret, payload.totp_code.get_secret_value(),
                                             admin.totp_last_used_step)
            if step is None:
                raise AdminAccountError("Credencial inválida.")
        except (AdminAccountError, InvalidHashError):
            raise HTTPException(403, "Credencial inválida.", headers=HEADERS) from None
        cipher = _cipher()
        try:
            envelope = cipher.encrypt(verifier, tenant_id=tenant_id, credential_id=attempt_id).payload()
        except IntegrationSecretError:
            raise HTTPException(503, "Conexão Drive temporariamente indisponível.", headers=HEADERS) from None
        admin.totp_last_used_step = step
        db.add(GoogleDriveOAuthAttempt(id=attempt_id, actor_admin_id=admin.id, auth_session_id=session.id, tenant_id=tenant_id,
               state_digest=hashlib.sha256(state.encode()).hexdigest(), verifier_envelope=envelope,
               expires_at=now() + timedelta(minutes=10)))
        from app.auth import audit
        audit(db, "google_drive.oauth_started", str(attempt_id), tenant_id=tenant_id)
        db.commit()
    params = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
              "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
              "code_challenge": challenge, "code_challenge_method": "S256"}
    return RedirectResponse(AUTH_ENDPOINT + "?" + urlencode(params), status_code=303, headers=HEADERS)


@router.get("/oauth/callback")
def callback(request: Request, state: str = "", code: str = "", error: str = ""):
    session, tenant_id = _owner(request)
    if not state or len(state) > 256 or len(code) > 4096:
        raise HTTPException(400, "Não foi possível conectar ao Google Drive.", headers=HEADERS)
    digest = hashlib.sha256(state.encode()).hexdigest()
    with SessionLocal() as db:
        bounded(db)
        attempt = db.scalar(select(GoogleDriveOAuthAttempt).where(
            GoogleDriveOAuthAttempt.state_digest == digest).with_for_update())
        if (not attempt or attempt.actor_admin_id != session.subject_id or attempt.auth_session_id != session.id
                or attempt.tenant_id != tenant_id
                or attempt.consumed_at or _expired(attempt.expires_at)):
            raise HTTPException(400, "Não foi possível conectar ao Google Drive.", headers=HEADERS)
        verifier = _cipher().decrypt(SecretEnvelope.from_payload(attempt.verifier_envelope),
                                     tenant_id=tenant_id, credential_id=attempt.id)
        attempt.consumed_at = now()
        db.commit()
    if error or not code:
        raise HTTPException(400, "Não foi possível conectar ao Google Drive.", headers=HEADERS)
    client_id, client_secret, redirect_uri = _config()
    try:
        result = HttpxDriveTransport().post(TOKEN_ENDPOINT, data={"code": code, "client_id": client_id,
            "client_secret": client_secret, "redirect_uri": redirect_uri, "grant_type": "authorization_code",
            "code_verifier": verifier}, headers={"Accept": "application/json"})
        if result.status_code != 200:
            raise ValueError()
        token_data = result.json()
        if not isinstance(token_data, dict):
            raise TypeError()
        refresh = token_data.get("refresh_token")
        scope_value = token_data.get("scope")
        if not isinstance(scope_value, str):
            raise TypeError()
        scopes = set(scope_value.split())
        if not isinstance(refresh, str) or not refresh or scopes != {SCOPE}:
            raise ValueError()
        connection_id = uuid4()
        envelope = _cipher().encrypt(refresh, tenant_id=tenant_id, credential_id=connection_id).payload()
    except (httpx.HTTPError, ValueError, TypeError, IntegrationSecretError):
        raise HTTPException(400, "Não foi possível conectar ao Google Drive.", headers=HEADERS) from None
    with SessionLocal() as db:
        bounded(db)
        row = db.scalar(select(GoogleDriveConnection).where(GoogleDriveConnection.tenant_id == tenant_id).with_for_update())
        if row:
            row.id, row.connected_by_admin_id, row.refresh_token_envelope = connection_id, session.subject_id, envelope
            row.scopes, row.state, row.connected_at, row.updated_at, row.revoked_at = SCOPE, "connected", now(), now(), None
        else:
            db.add(GoogleDriveConnection(id=connection_id, tenant_id=tenant_id,
                connected_by_admin_id=session.subject_id, refresh_token_envelope=envelope,
                scopes=SCOPE, state="connected", connected_at=now(), updated_at=now()))
        from app.auth import audit
        audit(db, "google_drive.connected", str(connection_id), tenant_id=tenant_id)
        db.commit()
    return RedirectResponse("/admin/platform?drive=connected", status_code=303, headers=HEADERS)


@router.post("/revoke")
def revoke(payload: ConnectInput, request: Request):
    from app.main import require_same_origin
    require_same_origin(request)
    session, tenant_id = _owner(request)
    if not _is_production():
        raise HTTPException(503, "Revogação real do Drive é habilitada somente em produção.", headers=HEADERS)
    with SessionLocal() as db:
        bounded(db)
        row = db.scalar(select(GoogleDriveConnection).where(GoogleDriveConnection.tenant_id == tenant_id).with_for_update())
        if not row or row.state != "connected":
            return {"state": "unknown"}
        enforce_rate_limit(db, "google_drive_revoke", str(session.subject_id),
                           request.client.host if request.client else "unknown")
        db.commit()
        try:
            admin = db.scalar(select(AdminUser).where(AdminUser.id == session.subject_id).with_for_update())
        except TotpSecretError:
            raise HTTPException(503, "Autenticador temporariamente indisponível.", headers=HEADERS) from None
        row = db.scalar(select(GoogleDriveConnection).where(
            GoogleDriveConnection.tenant_id == tenant_id).with_for_update())
        if not row or row.state != "connected":
            return {"state": "unknown"}
        if not admin or len(payload.totp_code.get_secret_value()) != 6:
            raise HTTPException(403, "Credencial inválida.", headers=HEADERS)
        try:
            reauthenticate_admin(admin, payload.current_password.get_secret_value())
            step = matching_unused_totp_step(admin.totp_secret, payload.totp_code.get_secret_value(),
                                             admin.totp_last_used_step)
            if step is None:
                raise AdminAccountError()
            token = _cipher().decrypt(SecretEnvelope.from_payload(row.refresh_token_envelope),
                                      tenant_id=tenant_id, credential_id=row.id)
        except (AdminAccountError, InvalidHashError, IntegrationSecretError):
            raise HTTPException(403, "Credencial inválida.", headers=HEADERS) from None
        admin.totp_last_used_step = step
        try:
            response = HttpxDriveTransport().post(REVOKE_ENDPOINT, data={"token": token})
            if response.status_code != 200:
                raise HTTPException(503, "Não foi possível revogar a conexão Drive.", headers=HEADERS)
        except httpx.HTTPError:
            raise HTTPException(503, "Não foi possível revogar a conexão Drive.", headers=HEADERS) from None
        row.state, row.refresh_token_envelope, row.revoked_at, row.updated_at = "revoked", {}, now(), now()
        from app.auth import audit
        audit(db, "google_drive.revoked", str(row.id), tenant_id=tenant_id)
        db.commit()
    return {"state": "revoked"}
