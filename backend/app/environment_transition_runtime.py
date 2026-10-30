"""Runner interno do corte, invocado somente pelo coordenador de host revisado."""

import argparse
import json
import os
import re
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.auth import Client, MercadoPagoAccount, PaymentPreferences
from app.environment_transition_bundle import (
    apply_bundle,
    inspect_bundle,
    load_bundle,
    prepare_bundle,
    recover_bundle,
)
from app.environment_transition_channels import inspect_channel_continuity
from app.facial.config import _keys
from app.facial.crypto import FacialCryptoContext, FacialCryptoContextPair
from app.integration_secrets import IntegrationCipher, SecretEnvelope

STATE = Path("/var/lib/markina-gallery/deploy-state/environment-cutover")
PACKAGES = STATE / "packages"
KEYS = STATE / "keys"


def eligibility_matrix(connection):
    from app.mercadopago_settings import can_create, test_customer_allowed
    cipher = IntegrationCipher()
    result = {"preference_tenants": 0, "pix_enabled": 0, "mercadopago_enabled": 0,
              "production_accounts_enabled": 0, "sandbox_accounts_enabled": 0,
              "unavailable_accounts": 0}
    pairs = json.loads(os.environ["MERCADOPAGO_TEST_CUSTOMERS"])
    if not isinstance(pairs, list) or len(pairs) != 1:
        raise ValueError
    with (Session(bind=connection, join_transaction_mode="create_savepoint") as session,
          session.begin()):
        for account in session.scalars(select(MercadoPagoAccount)):
            cipher.decrypt(SecretEnvelope.from_payload(account.access_token_envelope),
                           tenant_id=account.tenant_id, credential_id=account.id)
            cipher.decrypt(SecretEnvelope.from_payload(account.webhook_secret_envelope),
                           tenant_id=account.tenant_id, credential_id=account.id)
        for pref in session.scalars(select(PaymentPreferences)):
            result["preference_tenants"] += 1
            result["pix_enabled"] += int(pref.pix_enabled)
            result["mercadopago_enabled"] += int(pref.mercadopago_enabled)
            account = session.scalar(select(MercadoPagoAccount).where(
                MercadoPagoAccount.id == pref.account_id, MercadoPagoAccount.tenant_id == pref.tenant_id))
            if pref.mercadopago_enabled:
                if not can_create(account):
                    result["unavailable_accounts"] += 1
                elif account.test_account:
                    result["sandbox_accounts_enabled"] += 1
                    from uuid import UUID, uuid4
                    matched = [pair for pair in pairs if UUID(pair["tenant_id"]) == account.tenant_id]
                    if not matched or not test_customer_allowed(account, UUID(matched[0]["client_id"])):
                        raise ValueError
                    if test_customer_allowed(account, uuid4()):
                        raise ValueError
                    if session.scalar(select(Client.id).where(Client.id == UUID(matched[0]["client_id"]),
                                                             Client.tenant_id == account.tenant_id)) is None:
                        raise ValueError
                else:
                    result["production_accounts_enabled"] += 1
    return {**result, "live_gate": os.environ["MERCADOPAGO_ALLOW_LIVE_PAYMENTS"] == "true",
            "sandbox_pairs": len(pairs), "vault_verified": True}


def contexts_for(source_environment):
    if source_environment not in {"development", "staging", "homolog", "homologation", "test"}:
        raise ValueError
    keys = _keys()
    active = os.environ["FACIAL_AEAD_ACTIVE_KEY_ID"].strip()
    contexts = FacialCryptoContextPair(
        FacialCryptoContext.from_keyring(environment=source_environment, active_key_id=active, keys=keys),
        FacialCryptoContext.from_keyring(environment="production", active_key_id=active, keys=keys),
    )
    cipher = IntegrationCipher()
    return contexts, cipher.for_environment(source_environment), cipher.for_environment("production")


def require_reference_store_empty():
    root = Path(os.environ.get("FACIAL_REFERENCE_ROOT", "./media/facial-references"))
    if root.is_symlink() or (root.exists() and (not root.is_dir() or next(root.iterdir(), None) is not None)):
        raise ValueError


def preservation_metadata_verified(connection):
    result = connection.execute(text("""SELECT count(*) AS total,
        count(*) FILTER (WHERE a.id IS NOT NULL AND g.id IS NOT NULL AND p.id IS NOT NULL
            AND p.status='active' AND p.suspended_at IS NULL
            AND length(btrim(p.legal_notice_version))>0
            AND length(btrim(p.legal_basis_reference))>0
            AND length(btrim(p.retention_policy_version))>0) AS verified
        FROM photo_face_embedding e
        LEFT JOIN photo_asset a ON a.id=e.photo_asset_id AND a.parent_gallery_id=e.parent_gallery_id
            AND a.tenant_id=e.tenant_id
        LEFT JOIN parent_gallery g ON g.id=e.parent_gallery_id AND g.tenant_id=e.tenant_id
        LEFT JOIN gallery_facial_policy p ON p.parent_gallery_id=e.parent_gallery_id AND p.tenant_id=e.tenant_id
        """)).mappings().one()
    if result["total"] != result["verified"]:
        raise ValueError


def run_runtime(mode: str, operation: str, *, inventory: str | None, plan: str | None,
                paused: bool, network_checks: bool):
    if (os.environ.get("FACIAL_PROCESSING_ENABLED") != "false"
            or (mode != "eligibility" and os.environ.get("MERCADOPAGO_ALLOW_LIVE_PAYMENTS") != "false")):
        raise ValueError
    if mode in {"apply", "recover"} and not paused:
        raise ValueError
    require_reference_store_empty()
    source_environment = os.environ["APP_ENV"].strip()
    content = None
    if mode not in {"prepare", "preflight"}:
        content, _ = load_bundle(PACKAGES, KEYS, operation)
        source_environment = content["source_environment"]
    contexts, source_cipher, target_cipher = contexts_for(source_environment)
    engine = create_engine(os.environ["DATABASE_URL"], echo=False, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            if mode in {"prepare", "preflight", "verify", "channels", "eligibility"}:
                connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            connection.exec_driver_sql("SET LOCAL statement_timeout='120s'")
            schema = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
            if schema != ["20261026_0090"]:
                raise ValueError
            preservation_metadata_verified(connection)
            if mode == "preflight":
                from app.environment_transition_bundle import persist_profile
                result = persist_profile(connection, package_root=PACKAGES, key_root=KEYS,
                    operation=operation, continuity=inspect_channel_continuity(connection,
                        network_checks=network_checks), inventory=inventory, plan=plan)
            elif mode == "prepare":
                if not inventory or not plan:
                    raise ValueError
                continuity = inspect_channel_continuity(connection, network_checks=network_checks)
                result = prepare_bundle(connection, contexts=contexts, source_cipher=source_cipher,
                    target_cipher=target_cipher, inventory=inventory, plan=plan, operation=operation,
                    package_root=PACKAGES, key_root=KEYS, continuity=continuity)
            else:
                arguments = {"package_root": PACKAGES, "key_root": KEYS, "operation": operation,
                    "contexts": contexts, "source_cipher": source_cipher, "target_cipher": target_cipher,
                    "app_environment": os.environ["APP_ENV"].strip()}
                if mode == "apply":
                    if content["inventory"] != inventory or content["plan"] != plan:
                        raise ValueError
                    result = apply_bundle(connection, **arguments)
                elif mode == "recover":
                    result = recover_bundle(connection, **arguments)
                elif mode == "verify":
                    result = inspect_bundle(connection, **arguments)
                elif mode == "channels":
                    continuity = inspect_channel_continuity(connection, network_checks=network_checks)
                    if continuity != content["continuity"]:
                        raise ValueError
                    result = {"channels_verified": True}
                elif mode == "eligibility":
                    if os.environ["APP_ENV"] != "production":
                        raise ValueError
                    result = eligibility_matrix(connection)
                else:
                    raise ValueError
        return {"phase": mode, "status": "success", **result}
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "prepare", "apply", "verify", "recover", "channels", "eligibility"))
    parser.add_argument("--operation", required=True)
    parser.add_argument("--inventory")
    parser.add_argument("--plan")
    parser.add_argument("--paused", action="store_true")
    parser.add_argument("--network-checks", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,53}", args.operation):
        raise ValueError
    for value in (args.inventory, args.plan):
        if value is not None and not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError
    print(json.dumps(run_runtime(args.mode, args.operation, inventory=args.inventory, plan=args.plan,
        paused=args.paused, network_checks=args.network_checks), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - não expor SQL, URL, credenciais ou payloads em traceback
        print('{"status":"blocked","category":"runtime_precondition_or_verification_failed"}')
        raise SystemExit(2) from None
