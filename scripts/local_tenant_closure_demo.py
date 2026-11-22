"""Runner opt-in de encerramento: banco vazio e identidades sintéticas locais."""

import os
import sys
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import local_photographer_demo as signup_demo
from sqlalchemy import create_engine, make_url, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
REVISION = "20261113_0126"
ORIGIN = "http://127.0.0.1:3039"
TARGET = ("postgresql", "127.0.0.1", 15478, "pyp_closure_ui")


def validate_target(environment):
    if (environment.get("APP_ENV") != "development"
            or environment.get("PUBLIC_APP_ORIGIN") != ORIGIN):
        raise ValueError("Ensaio restrito ao desenvolvimento local.")
    signup_demo.reject_postgres_routing_overrides(environment)
    raw = environment.get("DATABASE_URL", "")
    url = make_url(raw)
    if url.query or (url.get_backend_name(), url.host, url.port, url.database) != TARGET:
        raise ValueError("Banco não corresponde ao destino sintético exclusivo.")
    if not environment.get("PYP_CLOSURE_DEMO_PASSWORD") or not environment.get("PYP_CLOSURE_DEMO_TOTP"):
        raise ValueError("Credenciais sintéticas externas obrigatórias.")
    return raw


def seed_accounts(raw_url):
    from app.auth import (
        AdminUser,
        ParentGallery,
        PhotoFolder,
        PhotographerBusinessProfile,
        PhotographerSignup,
        PhotographerTermsAcceptance,
        Tenant,
        TenantAdmin,
        TenantClosureRequest,
        TenantCreditWallet,
        now,
        password_hasher,
        validate_admin_password,
    )
    from app.photographer_cpf import active_cpf_fingerprint
    from app.private_fields import encrypt_private_document, encrypt_private_field
    from app.system_monitor.models import PlatformOwner

    password = os.environ["PYP_CLOSURE_DEMO_PASSWORD"]
    secret = os.environ["PYP_CLOSURE_DEMO_TOTP"]
    validate_admin_password(password, email="owner.closure-demo@example.test")
    engine = create_engine(raw_url)
    try:
        with Session(engine) as db:
            owner_id = db.scalar(select(PlatformOwner.admin_user_id))
            owner = db.get(AdminUser, owner_id)
            if (not owner or owner.email != "owner.local-demo@example.test"
                    or owner.password_hash != "disabled-local-demo-login"):
                raise ValueError("Bootstrap sintético não confirmado.")
            owner.email = "owner.closure-demo@example.test"
            owner.password_hash = password_hasher.hash(password)
            owner.totp_secret = secret
            owner.totp_enabled = True
            owner_tenant_id = db.scalar(select(TenantAdmin.tenant_id).where(TenantAdmin.admin_user_id == owner.id))
            db.get(Tenant, owner_tenant_id).photographer_name = "Proprietário — demonstração"

            tenant = Tenant(photographer_name="Fotógrafa — demonstração")
            db.add(tenant)
            db.flush()
            photographer = AdminUser(
                email="photographer.closure-demo@example.test", password_hash=password_hasher.hash(password),
                email_verified=True, totp_enabled=False,
            )
            db.add(photographer)
            db.flush()
            db.add_all([
                TenantAdmin(tenant_id=tenant.id, admin_user_id=photographer.id),
                TenantCreditWallet(tenant_id=tenant.id, mode="finite"),
            ])
            db.flush()
            db.add_all([
                PhotographerSignup(
                    photographer_name=tenant.photographer_name, email=photographer.email, state="active",
                    otp_expires_at=now(), reserved_admin_id=photographer.id, reserved_tenant_id=tenant.id,
                    activated_tenant_id=tenant.id, activated_at=now(), adult_attested_at=now(),
                ),
                PhotographerTermsAcceptance(
                    tenant_id=tenant.id, admin_user_id=photographer.id, terms_version="local-test-v1",
                    terms_text="Termos sintéticos da revisão visual.",
                    terms_sha256=sha256("Termos sintéticos da revisão visual.".encode()).hexdigest(),
                    provider_identity="Provedor sintético", photographer_identity="Fotógrafa sintética",
                    environment="development",
                ),
            ])
            gallery = ParentGallery(tenant_id=tenant.id, name="Galeria com prazo em andamento")
            db.add(gallery)
            db.flush()
            db.add(PhotoFolder(
                tenant_id=tenant.id, parent_gallery_id=gallery.id, name="Pasta de demonstração",
                status="released", released_at=now(), access_duration_days=14,
                access_expires_at=now() + timedelta(days=14),
            ))
            closed = Tenant(photographer_name="Conta encerrada — demonstração", lifecycle="closed")
            db.add(closed)
            db.flush()
            closed_admin = AdminUser(
                email="closed.closure-demo@example.test", password_hash="disabled-closed-demo-login",
                email_verified=True, totp_enabled=False,
            )
            db.add(closed_admin)
            db.flush()
            db.add(TenantAdmin(tenant_id=closed.id, admin_user_id=closed_admin.id))
            db.add(TenantCreditWallet(tenant_id=closed.id, mode="finite"))
            db.flush()
            cpf = "52998224725"
            version, fingerprint, duplicate = active_cpf_fingerprint(db, cpf)
            if duplicate:
                raise ValueError("CPF sintético já utilizado.")
            db.add(PhotographerBusinessProfile(
                tenant_id=closed.id, admin_user_id=closed_admin.id, full_name=closed.photographer_name,
                cpf_envelope=encrypt_private_field(cpf, tenant_id=closed.id, field="photographer-cpf"),
                address_envelope=encrypt_private_document("synthetic address", tenant_id=closed.id, field="photographer-address"),
                cpf_fingerprint=fingerprint, cpf_fingerprint_key_version=version,
            ))
            db.add(TenantClosureRequest(
                tenant_id=closed.id, request_id=uuid4(), requested_by=closed_admin.id, state="closed",
                requested_at=now() - timedelta(days=4001), closed_at=now() - timedelta(days=4000),
                terms_version="local-test-v1", terms_sha256="a" * 64,
                balance_snapshot=0, balance_acknowledged=True,
            ))
            db.commit()
    finally:
        engine.dispose()


def main():
    if sys.argv[1:] != ["--initialize-disposable-db-and-serve"]:
        return 2
    phase = "target"
    try:
        raw_url = validate_target(os.environ)
        phase = "empty_database"
        signup_demo.require_empty_database(raw_url)
        phase = "synthetic_environment"
        signup_demo.configure_synthetic_environment(seed=(make_url(raw_url).password or "").encode())
        os.environ["PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON"] = ""
        os.environ["PHOTOGRAPHER_CPF_FINGERPRINT_ACTIVE_KEY_VERSION"] = "legacy-v0"
        sys.path.insert(0, str(BACKEND))
        from alembic import command
        from alembic.config import Config

        config = Config(str(BACKEND / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND / "migrations"))
        phase = "baseline_migration"
        command.upgrade(config, "20261026_0090")
        phase = "bootstrap"
        signup_demo.create_synthetic_owner(raw_url)
        phase = "current_migration"
        command.upgrade(config, REVISION)
        phase = "seed_accounts"
        seed_accounts(raw_url)
    except Exception as exc:  # noqa: BLE001 -- Não imprimir URL, credenciais ou dados do fixture.
        diagnostic = getattr(getattr(exc, "orig", None), "diag", None)
        identifiers = [getattr(diagnostic, key, None) for key in ("constraint_name", "table_name", "column_name")]
        safe_identifiers = [value for value in identifiers if isinstance(value, str) and value.isidentifier()]
        print(f"Ensaio recusado: etapa={phase}; categoria={type(exc).__name__}; schema={safe_identifiers}.", flush=True)
        return 1
    import uvicorn
    from app.main import app

    print("API de revisão sintética pronta em 127.0.0.1:8000.", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
