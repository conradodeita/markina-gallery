"""Preparação sintética 2 × 3; não executa jornadas nem toca banco operacional."""

import argparse
import json
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from PIL import Image, ImageDraw
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app import auth
from app.messaging import SandboxWhatsAppProvider, WhatsAppDeliveryResult
from app.provision_installation_operator import provision_operator
from app.provision_photographer import provision_photographer

SYNTHETIC_PASSWORD = "Synthetic!Pilot2026.NoRealAccount"
SYNTHETIC_TOTP = "JBSWY3DPEHPK3PXP"


@dataclass(frozen=True)
class PilotAccount:
    tenant_id: UUID
    admin_id: UUID
    parent_id: UUID
    folder_ids: tuple[UUID, UUID]
    client_ids: tuple[UUID, ...]
    photo_ids: tuple[UUID, ...]
    access_token: str


class RecordingWhatsApp(SandboxWhatsAppProvider):
    """Mesmo contrato do adaptador, sem entrega ou armazenamento de dados reais."""

    def __init__(self):
        self.calls = []

    def send_transactional(self, phone_e164, message, *, idempotency_key):
        self.calls.append((phone_e164, message, idempotency_key))
        return WhatsAppDeliveryResult(sha256(idempotency_key.encode()).hexdigest(), phone_e164, "accepted")


def prepare_pilot(db: Session, root: Path, *, initial_tenant_id: UUID | None = None) -> tuple[PilotAccount, PilotAccount]:
    """Repetição reconhece o mesmo grafo, sem regravar credenciais ou criar jobs."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    namespace = uuid5(NAMESPACE_URL, f"synthetic-pyp-pilot:{root}")
    accounts = []
    for index, label in enumerate(("A", "B")):
        key = lambda kind, label=label: uuid5(namespace, f"{label}:{kind}")
        tenant_id, parent_id = (initial_tenant_id if index == 0 and initial_tenant_id else key("tenant")), key("parent")
        email = f"synthetic-pilot-{label.lower()}@example.test"
        provision_photographer(db, tenant_id, email, create_tenant=True, apply=True,
                               password=SYNTHETIC_PASSWORD, totp_secret=SYNTHETIC_TOTP)
        admin = db.scalar(select(auth.AdminUser).where(auth.AdminUser.email == email))
        if db.get(auth.ParentGallery, parent_id) is None:
            db.add(auth.ParentGallery(id=parent_id, tenant_id=tenant_id,
                                      name=f"Piloto abstrato {label}", access_mode="standard"))
            db.flush()
        client_ids = tuple(key(f"client-{number}") for number in range(3))
        for number, client_id in enumerate(client_ids):
            if db.get(auth.Client, client_id) is None:
                # Primeiro telefone se repete entre A/B; demais são próprios.
                phone = "+5511999990001" if number == 0 else f"+5511999990{index}{number}0"
                db.add(auth.Client(id=client_id, tenant_id=tenant_id,
                                   full_name=f"Sintética {label}{number}", phone_e164=phone))
                db.flush()
                db.add_all([
                    auth.ClientPhone(tenant_id=tenant_id, client_id=client_id,
                                     phone_e164=phone, verified_at=auth.now()),
                    auth.GalleryClientState(tenant_id=tenant_id, parent_gallery_id=parent_id, client_id=client_id),
                    auth.ParentGalleryRegistration(tenant_id=tenant_id, parent_gallery_id=parent_id,
                                                   client_id=client_id, status="active"),
                ])
        folder_ids = (key("common-folder"), key("restricted-folder"))
        for position, folder_id in enumerate(folder_ids):
            if db.get(auth.PhotoFolder, folder_id) is None:
                db.add(auth.PhotoFolder(id=folder_id, tenant_id=tenant_id, parent_gallery_id=parent_id,
                    name="Comum" if position == 0 else "Restrita", position=position,
                    audience_scope="all" if position == 0 else "selected", status="released", released_at=auth.now()))
                db.flush()
                if position == 1:
                    db.add(auth.FolderClientGrant(tenant_id=tenant_id, parent_gallery_id=parent_id,
                                                  folder_id=folder_id, client_id=client_ids[0]))
        photo_ids = tuple(key(f"photo-{number}") for number in range(6))
        for number, photo_id in enumerate(photo_ids):
            storage_key = f"tenants/{tenant_id}/photos/{photo_id}/synthetic.jpg"
            if db.get(auth.PhotoAsset, photo_id) is None:
                path = root / "source" / storage_key
                path.parent.mkdir(parents=True, exist_ok=True)
                image = Image.new("RGB", (256, 192), (30 + index * 80, 40 + number * 20, 90))
                ImageDraw.Draw(image).rectangle((32, 32, 120 + number * 8, 150), fill=(190, 150, 80))
                image.save(path, "JPEG", quality=80)
                db.add(auth.PhotoAsset(id=photo_id, tenant_id=tenant_id, parent_gallery_id=parent_id,
                    folder_id=folder_ids[number // 3], filename=f"abstract-{number}.jpg", storage_key=storage_key))
        token = f"synthetic-pilot-{parent_id.hex}" + "x" * 40
        if db.get(auth.GalleryAccessCapability, key("capability")) is None:
            db.add(auth.GalleryAccessCapability(id=key("capability"), tenant_id=tenant_id,
                parent_gallery_id=parent_id, scope="public_gallery", token_hash=auth.token_hash(token), actor_admin_id=admin.id))
        if db.scalar(select(auth.GlobalPixSettings.id).where(auth.GlobalPixSettings.tenant_id == tenant_id)) is None:
            db.add(auth.GlobalPixSettings(tenant_id=tenant_id, admin_user_id=admin.id,
                                         status="active", copy_paste=f"synthetic-no-payment-{label}"))
        db.flush()
        if index == 0:
            provision_operator(db, admin_id=admin.id, action="grant",
                               authorization_reference="synthetic-pilot-local-approval", apply=True)
        accounts.append(PilotAccount(tenant_id, admin.id, parent_id, folder_ids, client_ids, photo_ids, token))
    db.commit()
    return tuple(accounts)


def verify_preparation(db: Session, root: Path, accounts) -> dict[str, int | bool]:
    count = lambda model: db.scalar(select(func.count()).select_from(model))
    assert count(auth.Tenant) == count(auth.AdminUser) == count(auth.TenantAdmin) == 2
    assert count(auth.Client) == count(auth.ClientPhone) == count(auth.GalleryClientState) == 6
    assert count(auth.ParentGallery) == 2 and count(auth.PhotoFolder) == 4
    assert count(auth.PhotoAsset) == 12 and count(auth.FolderClientGrant) == 2
    assert count(auth.InstallationOperator) == 1
    first, second = (db.get(auth.Client, account.client_ids[0]) for account in accounts)
    assert first.id != second.id and first.phone_e164 == second.phone_e164 and first.full_name != second.full_name
    assert count(auth.AuthChallenge) == count(auth.AuthSession) == count(auth.MediaJob) == count(auth.SaleOrder) == 0
    files = list((root / "source").rglob("*.jpg"))
    assert len(files) == 12
    for path in files:
        with Image.open(path) as image:
            assert image.format == "JPEG" and image.size == (256, 192)
    return {"photographers": 2, "clients": 6, "jpeg_files": 12, "max_concurrency": 6,
            "same_phone_independent": True, "journeys_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-preparation", action="store_true", required=True)
    parser.parse_args()
    url = make_url(os.environ["PHOTOGRAPHER_TEST_DATABASE_URL"])
    if url.host != "127.0.0.1" or url.port != 15470 or url.database != "pyp_photographer_test":
        raise SystemExit("Somente banco sintético próprio em loopback 15470 é permitido.")
    control = create_engine(url)
    schema = f"pilot_preparation_{uuid4().hex}"
    with control.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = control.execution_options(schema_translate_map={None: schema})
    try:
        auth.Base.metadata.create_all(engine)
        with TemporaryDirectory(prefix="pyp-pilot-preparation-") as temporary, Session(engine) as db:
            root = Path(temporary)
            accounts = prepare_pilot(db, root)
            repeated = prepare_pilot(db, root)
            assert accounts == repeated
            print(json.dumps(verify_preparation(db, root, accounts), sort_keys=True))
    finally:
        with control.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        control.dispose()


if __name__ == "__main__":
    main()
