"""API de autenticação unificada da Markina Gallery."""

from __future__ import annotations

from uuid import UUID

import pyotp
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    AdminPasswordInput,
    AdminUser,
    AuthChallenge,
    ChallengeResendInput,
    ChallengeVerification,
    Client,
    ClientChallengeInput,
    GalleryAccess,
    Role,
    SessionLocal,
    audit,
    consume_challenge,
    create_challenge,
    create_session,
    current_session,
    enforce_rate_limit,
    expired,
    neutral_error,
    normalize_e164,
    now,
    password_hasher,
    resend_client_challenge,
    revoke_subject_sessions,
    whatsapp_provider,
)

app = FastAPI(title="Markina Gallery API", version="0.2.0")


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.post("/auth/client/challenge", status_code=status.HTTP_202_ACCEPTED)
def client_challenge(
    payload: ClientChallengeInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    phone = normalize_e164(payload.phone)
    enforce_rate_limit(
        db, "client_otp.challenge", phone, request.client.host if request.client else "unknown"
    )
    challenge, code = create_challenge(db, "client_otp", phone)
    whatsapp_provider.send_otp(phone, code)
    return {
        "challenge_id": str(challenge.id),
        "message": "Se os dados puderem receber acesso, enviaremos um código.",
    }


@app.post("/auth/client/resend", status_code=status.HTTP_202_ACCEPTED)
def client_resend(
    payload: ChallengeResendInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    resend_client_challenge(
        db, payload.challenge_id, request.client.host if request.client else "unknown"
    )
    return {"message": "Se os dados puderem receber acesso, enviaremos um novo código."}


@app.post("/auth/client/verify")
def client_verify(
    payload: ChallengeVerification, response: Response, db: Session = Depends(db_session)
) -> dict[str, str]:
    challenge = consume_challenge(db, payload.challenge_id, "client_otp", payload.code)
    client = db.scalar(select(Client).where(Client.phone_e164 == challenge.subject))
    if not client:
        audit(db, "client_otp.failed", challenge.subject)
        db.commit()
        raise neutral_error()
    gallery_ids = list(
        db.scalars(
            select(GalleryAccess.gallery_id).where(
                GalleryAccess.client_id == client.id, GalleryAccess.active
            )
        )
    )
    create_session(db, response, Role.CLIENT, client.id)
    destination = f"/gallery/{gallery_ids[0]}" if len(gallery_ids) == 1 else "/library"
    audit(db, "client.redirected", str(client.id))
    db.commit()
    return {"destination": destination}


@app.post("/auth/admin/password", status_code=status.HTTP_202_ACCEPTED)
def admin_password(
    payload: AdminPasswordInput, request: Request, db: Session = Depends(db_session)
) -> dict[str, str]:
    email = payload.email.strip().lower()
    enforce_rate_limit(
        db, "admin_password", email, request.client.host if request.client else "unknown"
    )
    admin = db.scalar(select(AdminUser).where(AdminUser.email == email))
    valid = False
    if admin and admin.email_verified:
        try:
            valid = password_hasher.verify(admin.password_hash, payload.password)
        except Exception:
            valid = False
    if not valid:
        audit(db, "admin_password.failed", email)
        db.commit()
        raise neutral_error()
    challenge, _ = create_challenge(db, "admin_totp", str(admin.id))
    return {"challenge_id": str(challenge.id), "message": "Continue com o código do autenticador."}


@app.post("/auth/admin/totp")
def admin_totp(
    payload: ChallengeVerification,
    request: Request,
    response: Response,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    challenge = db.get(AuthChallenge, payload.challenge_id)
    if not challenge or challenge.kind != "admin_totp":
        raise neutral_error()
    admin = db.get(AdminUser, UUID(challenge.subject))
    enforce_rate_limit(
        db, "admin_totp", challenge.subject, request.client.host if request.client else "unknown"
    )
    if not admin or not pyotp.TOTP(admin.totp_secret).verify(payload.code, valid_window=1):
        challenge.attempts += 1
        audit(db, "admin_totp.failed", challenge.subject)
        db.commit()
        raise neutral_error()
    if challenge.used_at or expired(challenge.expires_at) or challenge.attempts >= 5:
        raise neutral_error()
    challenge.used_at = now()
    audit(db, "admin_totp.validated", challenge.subject)
    create_session(db, response, Role.ADMIN, admin.id)
    audit(db, "admin.redirected", str(admin.id))
    db.commit()
    return {"destination": "/admin"}


@app.get("/auth/destination")
def destination(request: Request) -> dict[str, str]:
    session = current_session(request)
    if session.role == Role.ADMIN.value:
        return {"destination": "/admin"}
    with SessionLocal() as db:
        galleries = list(
            db.scalars(
                select(GalleryAccess.gallery_id).where(
                    GalleryAccess.client_id == session.subject_id, GalleryAccess.active
                )
            )
        )
    return {"destination": f"/gallery/{galleries[0]}" if len(galleries) == 1 else "/library"}


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> Response:
    session = current_session(request)
    with SessionLocal() as db:
        stored = db.get(type(session), session.id)
        stored.revoked_at = now()
        audit(db, "session.revoked", str(session.subject_id))
        db.commit()
    response.delete_cookie("markina_session", path="/")
    return response


@app.post("/auth/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all(request: Request, response: Response) -> Response:
    session = current_session(request)
    with SessionLocal() as db:
        revoke_subject_sessions(db, session.role, session.subject_id)
        db.commit()
    response.delete_cookie("markina_session", path="/")
    return response


@app.get("/admin")
def admin_area(request: Request) -> dict[str, str]:
    current_session(request, Role.ADMIN)
    return {"status": "authorized"}


@app.get("/gallery/{gallery_id}")
def gallery_area(gallery_id: UUID, request: Request) -> dict[str, str]:
    session = current_session(request, Role.CLIENT)
    with SessionLocal() as db:
        authorized = db.scalar(
            select(GalleryAccess).where(
                GalleryAccess.client_id == session.subject_id,
                GalleryAccess.gallery_id == gallery_id,
                GalleryAccess.active,
            )
        )
        if not authorized:
            audit(db, "gallery.access_denied", str(session.subject_id))
            db.commit()
            raise HTTPException(status_code=403, detail="Acesso negado.")
    return {"status": "authorized"}
