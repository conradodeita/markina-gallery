"""Cria a conta administrativa inicial somente por variáveis externas ao Git."""

from __future__ import annotations

import os

import pyotp
from sqlalchemy import select

from app.auth import AdminUser, SessionLocal, password_hasher, validate_admin_password


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"A variável {name} é obrigatória para criar o administrador inicial.")
    return value


def seed_admin() -> None:
    """Cria uma única conta verificada; nunca sobrescreve uma conta existente."""
    email = required_setting("ADMIN_SEED_EMAIL").lower()
    password = required_setting("ADMIN_SEED_PASSWORD")
    totp_secret = required_setting("ADMIN_SEED_TOTP_SECRET").replace(" ", "").upper()
    try:
        validate_admin_password(password, email=email)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    if not pyotp.TOTP(totp_secret).now():
        raise RuntimeError("ADMIN_SEED_TOTP_SECRET não é uma chave TOTP válida.")
    with SessionLocal() as db:
        existing = db.scalar(select(AdminUser).where(AdminUser.email == email))
        if existing:
            return
        if db.scalar(select(AdminUser.id)):
            raise RuntimeError("Já existe outro administrador; seed inicial interrompido.")
        db.add(
            AdminUser(
                email=email,
                password_hash=password_hasher.hash(password),
                email_verified=True,
                totp_secret=totp_secret,
            )
        )
        db.commit()


if __name__ == "__main__":
    seed_admin()
