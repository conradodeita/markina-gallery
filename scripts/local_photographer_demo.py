"""Opt-in loopback demo for the synthetic photographer signup flow."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
from pathlib import Path
from threading import Lock
from uuid import uuid4

from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, make_url, text
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
ORIGIN = "http://127.0.0.1:3039"
TARGET = ("postgresql", "127.0.0.1", 15472, "pyp_ui_demo")
REVISION = "20261113_0126"


def reject_postgres_routing_overrides(environment: dict[str, str]) -> None:
    """Reject libpq defaults that could redirect a loopback URL elsewhere."""
    if environment.get("PGSERVICE"):
        raise ValueError("demonstração não aceita serviços PostgreSQL herdados")
    hostaddr = environment.get("PGHOSTADDR")
    if hostaddr and hostaddr != "127.0.0.1":
        raise ValueError("demonstração aceita somente endereço PostgreSQL de loopback")


def validate_target(environment: dict[str, str]) -> str:
    if environment.get("APP_ENV") != "development" or environment.get("PUBLIC_APP_ORIGIN") != ORIGIN:
        raise ValueError("demonstração restrita ao ambiente local e à origem de teste")
    raw = environment.get("DATABASE_URL", "")
    try:
        url = make_url(raw)
    except ValueError:
        raise ValueError("URL de banco inválida para a demonstração") from None
    reject_postgres_routing_overrides(environment)
    if url.query or (url.get_backend_name(), url.host, url.port, url.database) != TARGET:
        raise ValueError("demonstração restrita ao PostgreSQL descartável local exclusivo")
    return raw


def require_empty_database(raw_url: str) -> None:
    engine = create_engine(raw_url)
    try:
        with engine.connect() as connection:
            if inspect(connection).get_table_names() or any(
                name not in {"public", "information_schema"} and not name.startswith("pg_")
                for name in inspect(connection).get_schema_names()
            ):
                raise ValueError("banco da demonstração já contém dados ou schemas")
    finally:
        engine.dispose()


def require_current_schema(raw_url: str) -> None:
    engine = create_engine(raw_url)
    try:
        with engine.connect() as connection:
            if tuple(MigrationContext.configure(connection).get_current_heads()) != (REVISION,):
                raise ValueError("revisão inesperada no banco de demonstração")
    finally:
        engine.dispose()


def configure_synthetic_environment(seed: bytes | None = None) -> None:
    material = seed or secrets.token_bytes(32)

    def key(purpose: str) -> str:
        return base64.urlsafe_b64encode(hmac.new(
            material, f"pyp-disposable-demo-v1:{purpose}".encode(), hashlib.sha256,
        ).digest()).decode()

    os.environ.update({
        "PHOTOGRAPHER_SIGNUP_LOCAL_PROOF_ENABLED": "true",
        "SYSTEM_MONITOR_ENABLED": "false",
        "EMAIL_PROVIDER": "sandbox",
        "SECRET_KEY": key("session"),
        "AUTH_PII_FINGERPRINT_SALT": key("pii-fingerprint"),
        "ADMIN_PRIVATE_FIELD_KEY": key("private-field"),
        "PHOTOGRAPHER_TEST_TERMS_ENABLED": "true",
        "PHOTOGRAPHER_TEST_WHATSAPP_SANDBOX": "true",
        "GALLERY_CAPABILITY_SIGNING_KEY": key("gallery-capability"),
        "ADMIN_TOTP_SECRET_ENV": "development",
        "ADMIN_TOTP_ACTIVE_KEY_ID": "local-demo",
        "ADMIN_TOTP_KEYS": json.dumps({"local-demo": base64.b64encode(base64.urlsafe_b64decode(key("totp"))).decode()}),
        "INTEGRATION_SECRET_ENV": "development",
        "INTEGRATION_SECRET_ACTIVE_KEY_ID": "local-demo",
        "INTEGRATION_SECRET_KEYS": json.dumps({"local-demo": base64.b64encode(base64.urlsafe_b64decode(key("integration"))).decode()}),
    })


def refresh_disabled_synthetic_owner(raw_url: str) -> None:
    """Mantém somente a identidade de bootstrap sem login utilizável."""
    import pyotp
    from app.totp_crypto import TotpSecretCipher

    engine = create_engine(raw_url)
    try:
        with engine.begin() as connection:
            rows = connection.execute(text(
                "SELECT a.id, a.email, a.password_hash, p.authorization_reference "
                "FROM admin_user a JOIN platform_owner p ON p.admin_user_id=a.id"
            )).all()
            if len(rows) != 1 or rows[0][1:] != (
                "owner.local-demo@example.test", "disabled-local-demo-login", "synthetic-local-ui-demo",
            ):
                raise ValueError("proprietário não corresponde à identidade sintética de bootstrap")
            envelope = TotpSecretCipher.from_environment().encrypt(pyotp.random_base32(), admin_id=rows[0][0])
            connection.execute(text(
                "UPDATE admin_user SET totp_secret=NULL,totp_secret_envelope=:envelope,totp_enabled=true WHERE id=:id"
            ), {"id": rows[0][0], "envelope": envelope})
    finally:
        engine.dispose()


def create_synthetic_owner(raw_url: str) -> None:
    """Satisfy 0094's real owner precondition without a usable owner login."""
    import pyotp

    engine = create_engine(raw_url)
    try:
        with engine.begin() as connection:
            tenants = connection.execute(text("SELECT id FROM tenant ORDER BY id")).scalars().all()
            if len(tenants) != 1 or connection.scalar(text("SELECT count(*) FROM platform_owner")) != 0:
                raise ValueError("baseline local inesperado para proprietário sintético")
            admin_id = uuid4()
            secret = pyotp.random_base32()
            columns = {item["name"] for item in inspect(connection).get_columns("admin_user")}
            if "totp_secret_envelope" in columns:
                from app.totp_crypto import TotpSecretCipher
                envelope = TotpSecretCipher.from_environment().encrypt(secret, admin_id=admin_id)
                connection.execute(text("""
                    INSERT INTO admin_user (id, email, password_hash, email_verified, totp_secret_envelope)
                    VALUES (:admin_id, 'owner.local-demo@example.test', 'disabled-local-demo-login', true, :envelope)
                """), {"admin_id": admin_id, "envelope": envelope})
            else:
                connection.execute(text("""
                    INSERT INTO admin_user (id, email, password_hash, email_verified, totp_secret)
                    VALUES (:admin_id, 'owner.local-demo@example.test', 'disabled-local-demo-login', true, :secret)
                """), {"admin_id": admin_id, "secret": secret})
            connection.execute(text("""
                INSERT INTO tenant_admin (id, tenant_id, admin_user_id, active, created_at)
                VALUES (:membership_id, :tenant_id, :admin_id, true, CURRENT_TIMESTAMP)
            """), {"membership_id": uuid4(), "tenant_id": tenants[0], "admin_id": admin_id})
            connection.execute(text("""
                INSERT INTO platform_owner (singleton, admin_user_id, authorization_reference, established_at)
                VALUES (1, :admin_id, 'synthetic-local-ui-demo', CURRENT_TIMESTAMP)
            """), {"admin_id": admin_id})
    finally:
        engine.dispose()


def main() -> int:
    mode = sys.argv[1:]
    if mode not in (["--initialize-disposable-db-and-serve"], ["--serve-existing-disposable-db"]):
        print("Uso: local_photographer_demo.py --initialize-disposable-db-and-serve | --serve-existing-disposable-db")
        return 2
    try:
        raw_url = validate_target(os.environ)
        if mode == ["--initialize-disposable-db-and-serve"]:
            require_empty_database(raw_url)
        else:
            require_current_schema(raw_url)
    except (SQLAlchemyError, ValueError):
        print("Demonstração recusada: confirme ambiente, origem e banco descartável vazio.")
        return 1

    configure_synthetic_environment(seed=(make_url(raw_url).password or "").encode())
    sys.path.insert(0, str(BACKEND))
    from alembic import command
    from alembic.config import Config

    if mode == ["--initialize-disposable-db-and-serve"]:
        config = Config(str(BACKEND / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND / "migrations"))
        try:
            command.upgrade(config, "20261026_0090")
            create_synthetic_owner(raw_url)
            command.upgrade(config, REVISION)
        except (SQLAlchemyError, RuntimeError, ValueError):
            print("Migration do banco sintético falhou; demonstração não iniciada.")
            return 1

    try:
        refresh_disabled_synthetic_owner(raw_url)
    except (SQLAlchemyError, ValueError):
        print("Bootstrap sintético não confirmado; demonstração não iniciada.")
        return 1

    import uvicorn
    from app import main as application
    from app import photographer_signup
    from app.auth import (
        GlobalPixSettings,
        PhotographerSignup,
        Role,
        SessionLocal,
        current_session,
    )
    from app.photographer_signup import SignupServiceError
    from app.system_monitor.models import PlatformOwner
    from fastapi import HTTPException, Request, Response
    from sqlalchemy import select

    codes: dict[str, str] = {}
    lock = Lock()

    class SyntheticSignupServices:
        def verify_bot(self, proof: str, address: str) -> bool:
            return proof == "" and address in {"127.0.0.1", "::1"}

        def send_code(self, _db, signup_row, code: str) -> None:
            email = signup_row.email
            if not email.endswith("@example.test"):
                raise SignupServiceError("somente endereços sintéticos")
            with lock:
                codes[email] = code

    application.app.dependency_overrides[photographer_signup.signup_services] = SyntheticSignupServices

    @application.app.get("/local-demo/mailbox")
    def local_mailbox(request: Request, response: Response) -> dict[str, dict[str, str]]:
        if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
            raise HTTPException(404)
        response.headers["Cache-Control"] = "no-store"
        with lock:
            return {"synthetic_codes": dict(codes)}

    def local_request(request: Request, db):
        if (os.getenv("APP_ENV") != "development"
                or os.getenv("PHOTOGRAPHER_SIGNUP_LOCAL_PROOF_ENABLED") != "true"
                or not request.client or request.client.host not in {"127.0.0.1", "::1"}):
            raise HTTPException(404)
        application.require_same_origin(request)
        session = current_session(request, Role.ADMIN)
        signup = db.scalar(select(PhotographerSignup).where(
            PhotographerSignup.reserved_admin_id == session.subject_id,
            PhotographerSignup.activated_tenant_id == session.tenant_id,
            PhotographerSignup.state == "active",
        ))
        if not signup:
            raise HTTPException(404)
        return session, signup

    @application.app.post("/local-demo/simulate-credit-purchase")
    def simulate_credit_purchase(request: Request):
        from app.photographer_credits import grant_credits

        with SessionLocal() as db:
            session, signup = local_request(request, db)
            owner_id = db.scalar(select(PlatformOwner.admin_user_id).where(PlatformOwner.singleton == 1))
            if not owner_id:
                raise HTTPException(503, "Demonstração indisponível.")
            grant_credits(
                db, owner_id, session.tenant_id, 25,
                f"local-demo-purchase:{session.tenant_id}",
                f"Compra simulada local para candidatura {signup.id}",
            )
            db.commit()
        return {"simulated": True, "credits_added": 25, "charged": False}

    @application.app.post("/local-demo/configure-upload-prerequisites")
    def configure_upload_prerequisites(request: Request):
        from app.global_pix import apply_configuration, normalize_configuration
        from app.photographer_credits import wallet_snapshot
        from app.whatsapp_channel import channel_settings

        with SessionLocal() as db:
            session, _signup = local_request(request, db)
            wallet = wallet_snapshot(db, session.tenant_id)
            if not wallet.get("available_credits"):
                raise HTTPException(409, "Simule primeiro a compra de créditos.")
            existing = db.scalar(select(GlobalPixSettings).where(
                GlobalPixSettings.tenant_id == session.tenant_id,
                GlobalPixSettings.singleton == 1,
            ))
            configuration = normalize_configuration({
                "copy_paste": "demonstracao@example.test",
                "receiver_name": "PYP TESTE",
                "receiver_city": "SAO PAULO",
            })
            apply_configuration(
                db, admin_id=session.subject_id, tenant_id=session.tenant_id,
                proposed={"version": existing.version if existing else 0,
                          "configuration": configuration},
            )
            channel = channel_settings(db, tenant_id=session.tenant_id)
            if channel.status != "sandbox":
                raise HTTPException(503, "Sandbox do WhatsApp indisponível.")
            db.commit()
        return {"pix_test_configured": True, "whatsapp": "sandbox", "external_messages": False}

    print("API sintética pronta em 127.0.0.1:8000; caixa local em http://127.0.0.1:3039/api/local-demo/mailbox", flush=True)
    uvicorn.run(application.app, host="127.0.0.1", port=8000, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
