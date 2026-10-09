"""Cria um grafo sintético mínimo para a campanha remota de homologação."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import auth
from app.remote_test_otp import is_remote_test_otp_tenant
from tests.synthetic_media import MediaManifest, verify_pilot_media

TARGET_ORIGIN = "https://markina-homolog.duckdns.org"
TENANTS = (
    UUID("7f1f8b5a-905c-4c35-9cd8-87759af31c01"),
    UUID("b67d881d-d577-40d8-af5e-0a4368ea6002"),
)
MEDIA_SHA256 = (
    "418fce7c47cc9dece618904c69c4f945a0e7cc7721498a79d56f6209762e7ae8",
    "1e027185b7933d610e0877db43994bf91cec2b5a140e3a1c4bf2c17d5c7080b1",
    "0c6091bc43a163da7c959316b97cf7f79168e40543430fc18c28b58aaf40fff5",
    "e4a3c57c4e1bd6e5dcc201ba0a4df7d3672987f159b451627899c8e3878dc9ae",
)


def _guard() -> None:
    if (
        os.getenv("APP_ENV", "").strip().lower() not in {"staging", "homolog"}
        or os.getenv("PUBLIC_APP_ORIGIN", "").strip().rstrip("/") != TARGET_ORIGIN
        or os.getenv("PYP_REMOTE_TEST_OTP_ENABLED", "") != "1"
    ):
        raise RuntimeError("remote_campaign_target_rejected")
    if not all(is_remote_test_otp_tenant(tenant_id) for tenant_id in TENANTS):
        raise RuntimeError("remote_campaign_tenant_allowlist_rejected")


def _expected_ids(tenant_id: UUID) -> dict[str, UUID]:
    namespace = uuid5(NAMESPACE_URL, f"pyp-remote-campaign-v1:{tenant_id}")
    return {
        "gallery": uuid5(namespace, "gallery"),
        "folder": uuid5(namespace, "folder"),
        "client_1": uuid5(namespace, "client:1"),
        "client_2": uuid5(namespace, "client:2"),
        "photo_1": uuid5(namespace, "photo:1"),
        "photo_2": uuid5(namespace, "photo:2"),
    }


def _verify_account(db: Session, tenant_id: UUID) -> None:
    tenant = db.get(auth.Tenant, tenant_id)
    if not tenant or tenant.status != "active":
        raise RuntimeError("remote_campaign_account_unavailable")
    admins = list(db.scalars(
        select(auth.AdminUser)
        .join(auth.TenantAdmin, auth.TenantAdmin.admin_user_id == auth.AdminUser.id)
        .where(auth.TenantAdmin.tenant_id == tenant_id, auth.TenantAdmin.active.is_(True))
        .limit(2)
    ))
    if len(admins) != 1:
        raise RuntimeError("remote_campaign_admin_account_ambiguous")


def _ensure_fixture(db: Session, tenant_id: UUID, media_root: Path, manifest: MediaManifest) -> None:
    _verify_account(db, tenant_id)
    ids = _expected_ids(tenant_id)
    media_source = Path(os.environ["MEDIA_SOURCE_ROOT"]).resolve()
    gallery = db.get(auth.ParentGallery, ids["gallery"])
    if gallery is None:
        gallery = auth.ParentGallery(
            id=ids["gallery"], tenant_id=tenant_id,
            name="Galeria sintética da campanha remota",
            access_mode="standard", active=True, lifecycle_status="active",
        )
        db.add(gallery)
        db.flush()
    elif gallery.tenant_id != tenant_id or gallery.name != "Galeria sintética da campanha remota":
        raise RuntimeError("remote_campaign_gallery_conflict")

    folder = db.get(auth.PhotoFolder, ids["folder"])
    if folder is None:
        folder = auth.PhotoFolder(
            id=ids["folder"], tenant_id=tenant_id, parent_gallery_id=gallery.id,
            name="Fotos sintéticas", status="released", purpose="content",
            audience_scope="all", position=0, released_at=auth.now(),
        )
        db.add(folder)
        db.flush()
    elif folder.tenant_id != tenant_id or folder.parent_gallery_id != gallery.id:
        raise RuntimeError("remote_campaign_folder_conflict")

    client_ids = (ids["client_1"], ids["client_2"])
    phones = (
        "+5511999991001" if tenant_id == TENANTS[0] else "+5511999992001",
        "+5511999991002" if tenant_id == TENANTS[0] else "+5511999992002",
    )
    for index, (client_id, phone) in enumerate(zip(client_ids, phones, strict=True), start=1):
        client = db.get(auth.Client, client_id)
        client_name = f"Cliente sintético {tenant_id.hex[:6]} {index}"
        if client is None:
            client = auth.Client(
                id=client_id, tenant_id=tenant_id,
                full_name=client_name, phone_e164=phone,
            )
            db.add(client)
            db.flush()
        elif client.tenant_id != tenant_id or client.full_name != client_name or client.phone_e164 != phone:
            raise RuntimeError("remote_campaign_client_conflict")

        client_phone = db.scalar(select(auth.ClientPhone).where(
            auth.ClientPhone.tenant_id == tenant_id,
            auth.ClientPhone.client_id == client_id,
            auth.ClientPhone.phone_e164 == phone,
        ))
        if client_phone is None:
            db.add(auth.ClientPhone(
                tenant_id=tenant_id, client_id=client_id, phone_e164=phone,
                active=True, verified_at=auth.now(),
            ))
        elif not client_phone.active or client_phone.verified_at is None:
            raise RuntimeError("remote_campaign_client_phone_conflict")

        state = db.scalar(select(auth.GalleryClientState).where(
            auth.GalleryClientState.parent_gallery_id == gallery.id,
            auth.GalleryClientState.client_id == client_id,
        ))
        if state is None:
            db.add(auth.GalleryClientState(
                tenant_id=tenant_id, parent_gallery_id=gallery.id,
                client_id=client_id, status="active",
            ))
        elif state.tenant_id != tenant_id or state.status != "active":
            raise RuntimeError("remote_campaign_client_state_conflict")

        registration = db.scalar(select(auth.ParentGalleryRegistration).where(
            auth.ParentGalleryRegistration.parent_gallery_id == gallery.id,
            auth.ParentGalleryRegistration.client_id == client_id,
        ))
        if registration is None:
            db.add(auth.ParentGalleryRegistration(
                tenant_id=tenant_id, parent_gallery_id=gallery.id,
                client_id=client_id, status="active",
            ))
        elif registration.tenant_id != tenant_id or registration.status != "active":
            raise RuntimeError("remote_campaign_registration_conflict")

    db.flush()
    for index, photo_id in enumerate((ids["photo_1"], ids["photo_2"])):
        verified = manifest.verified[index + (0 if tenant_id == TENANTS[0] else 2)]
        source = (media_root / verified.relative_path).resolve(strict=True)
        if media_root.resolve(strict=True) not in source.parents:
            raise RuntimeError("remote_campaign_media_path_escape")
        content_hash = sha256(source.read_bytes()).hexdigest()
        if content_hash != verified.sha256:
            raise RuntimeError("remote_campaign_media_changed")
        storage_key = f"tenants/{tenant_id}/photos/{photo_id}/remote-campaign.jpg"
        destination = (media_source / storage_key).resolve()
        if media_source not in destination.parents:
            raise RuntimeError("remote_campaign_storage_path_escape")
        photo = db.get(auth.PhotoAsset, photo_id)
        if photo is None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if sha256(destination.read_bytes()).hexdigest() != content_hash:
                    raise RuntimeError("remote_campaign_storage_conflict")
            else:
                shutil.copyfile(source, destination)
            db.add(auth.PhotoAsset(
                id=photo_id, tenant_id=tenant_id, parent_gallery_id=gallery.id,
                folder_id=folder.id, filename=f"remote-campaign-{index + 1}.jpg",
                storage_key=storage_key, available=True,
            ))
        elif (
            photo.tenant_id != tenant_id
            or photo.parent_gallery_id != gallery.id
            or photo.folder_id != folder.id
            or photo.storage_key != storage_key
            or not destination.is_file()
            or sha256(destination.read_bytes()).hexdigest() != content_hash
        ):
            raise RuntimeError("remote_campaign_photo_conflict")
    db.flush()


def provision_fixture(media_root: Path) -> dict[str, object]:
    _guard()
    media_root = media_root.resolve(strict=True)
    manifest = verify_pilot_media(media_root)
    if len(manifest.verified) != len(MEDIA_SHA256) or manifest.rejected_count != 0:
        raise RuntimeError("remote_campaign_media_manifest_mismatch")
    if tuple(item.sha256 for item in manifest.verified) != MEDIA_SHA256:
        raise RuntimeError("remote_campaign_media_manifest_mismatch")
    with auth.SessionLocal() as db:
        revision = db.execute(text("select version_num from alembic_version")).scalar_one()
        if revision != "20261001_0071":
            raise RuntimeError("remote_campaign_schema_mismatch")
        try:
            for tenant_id in TENANTS:
                _ensure_fixture(db, tenant_id, media_root, manifest)
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {
        "schema": "pyp-remote-campaign-fixture/v1",
        "photographers": 2,
        "galleries": 2,
        "clients": 4,
        "photos": 4,
        "source_manifest_sha256": manifest.manifest_sha256,
        "originals_modified": False,
        "payments_configured": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(provision_fixture(args.media_root), sort_keys=True))
    except Exception:
        parser.exit(1, "Provisionamento sintético remoto recusado; nenhum item foi removido.\n")


if __name__ == "__main__":
    main()
