"""Configurações A/B sintéticas, com PostgreSQL, cookies e OTP reais sem envio."""

import asyncio
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, Response
from PIL import Image
from sqlalchemy import func, select

from app import admin_account, auth, main
from app.auth import (
    AdminSecurityChallenge,
    BrandingSettings,
    MediaJob,
    PriceRule,
    Role,
    TenantAdmin,
)
from app.branding_context import technical_branding
from app.folder_processing import configure_folder, effective_preview
from app.preview_adjustment.service import configure as configure_preview
from tests.test_tenant_client_auth import client_db as _client_db
from tests.test_tenant_client_auth import graph as _graph
from tests.test_tenant_client_auth import links as _links
from tests.test_tenant_client_auth import request
from tests.test_tenant_client_navigation import cookie

client_db = _client_db
graph = _graph
links = _links
PASSWORD = "Isolated-Configuration-2026!"


@pytest.fixture
def configured(client_db, graph, links):
    for row in graph:
        row["admin"].email_verified = True
        row["admin"].password_hash = auth.password_hasher.hash(PASSWORD)
    client_db.commit()
    for row in graph:
        row["admin_request"] = request(cookie(client_db, row, Role.ADMIN))
        row["customer_request"] = request(cookie(client_db, row, Role.CLIENT))
    return graph


def brand_input(label):
    return main.BrandingSettingsInput(login_title=f"Marca {label}", login_intro=f"Intro {label}",
                                     login_helper=f"Ajuda {label}")


def preset_input(label):
    return main.ProgressivePricingPresetInput(code="SAME", name=f"Preços {label}",
        tiers=[main.PriceTierInput(minimum_quantity=1, unit_price_cents=700)])


def test_conta_nova_nao_herda_marca_pix_templates_ou_tabelas(client_db, configured):
    first, second = configured
    main.update_admin_branding(brand_input("A"), first["admin_request"], client_db)
    main.save_payment_template("confirmed", main.PaymentTemplateInput(body="Apenas A {{cliente}}"),
                              first["admin_request"], client_db)
    main.create_progressive_pricing_preset(preset_input("A"), first["admin_request"], client_db)
    assert main.admin_branding(second["admin_request"], client_db)["login_title"] == technical_branding()["login_title"]
    assert main.admin_global_pix(second["admin_request"], client_db)["status"] == "unconfigured"
    assert "Apenas A" not in str(main.list_payment_templates(second["admin_request"], client_db))
    assert main.list_progressive_pricing_presets(second["admin_request"], False, client_db) == {"presets": []}
    main.update_admin_branding(brand_input("B"), second["admin_request"], client_db)
    assert main.admin_branding(first["admin_request"], client_db)["login_title"] == "Marca A"
    assert client_db.scalar(select(func.count()).select_from(BrandingSettings)) == 2


def test_branding_generico_e_link_invalido_nao_caem_na_conta_da_sessao(client_db, configured, links):
    for row, label in zip(configured, ("A", "B"), strict=True):
        main.update_admin_branding(brand_input(label), row["admin_request"], client_db)
    response = Response()
    assert main.public_branding(request(), response, None, client_db) == technical_branding()
    assert response.headers["cache-control"] == "private, no-store"
    first = configured[0]
    assert main.public_branding(first["customer_request"], Response(), "invalid", client_db) == technical_branding()
    assert main.public_branding(first["customer_request"], Response(), None, client_db)["login_title"] == "Marca A"
    assert main.public_branding(request(), Response(), links[1][0], client_db)["login_title"] == "Marca B"
    configured[1]["tenant"].status = "suspended"
    client_db.commit()
    assert main.public_branding(request(), Response(), links[1][0], client_db) == technical_branding()


def test_assets_marca_namespace_own_legacy_e_cache_privado(client_db, configured, links, tmp_path, monkeypatch):
    monkeypatch.setenv("BRANDING_ASSETS_ROOT", str(tmp_path))
    paths = []
    for index, row in enumerate(configured):
        output = BytesIO()
        Image.new("RGB", (32, 32), (index*100, 50, 100)).save(output, format="PNG")
        incoming = request(row["admin_request"].headers["cookie"].split("=", 1)[1])
        incoming.scope["headers"].append((b"content-type", b"image/png"))
        incoming._body = output.getvalue()
        result = asyncio.run(main.upload_branding_asset("logo", incoming, client_db))
        assert result["logo_url"] == "/branding/logo"
        setting = client_db.scalar(select(BrandingSettings).where(BrandingSettings.tenant_id == row["tenant"].id))
        assert setting.logo_key.startswith(f"tenants/{row['tenant'].id}/branding/")
        response = main.public_branding_asset("logo", row["customer_request"], None, None, client_db)
        assert response.headers["cache-control"] == "private, no-store"
        paths.append(response.path)
    assert paths[0] != paths[1]
    for candidate in (None, "invalid"):
        with pytest.raises(HTTPException) as exc:
            main.public_branding_asset("logo", request(), None, candidate, client_db)
        assert exc.value.status_code == 404
    first = configured[0]
    setting = client_db.scalar(select(BrandingSettings).where(BrandingSettings.tenant_id == first["tenant"].id))
    setting.logo_key = "logo.png"
    (tmp_path / "logo.png").write_bytes(b"synthetic-legacy")
    client_db.commit()
    assert main.public_branding_asset("logo", first["customer_request"], None, None, client_db).path == tmp_path / "logo.png"
    public = main.public_branding(request(), Response(), links[0][0], client_db)
    assert "access_token=" in public["logo_url"]


def test_preset_mesmo_codigo_por_conta_e_operacoes_estrangeiras_neutras(client_db, configured):
    presets = [main.create_progressive_pricing_preset(preset_input(label), row["admin_request"], client_db)
               for row, label in zip(configured, ("A", "B"), strict=True)]
    first = configured[0]
    for operation in (main.update_progressive_pricing_preset, main.deactivate_progressive_pricing_preset,
                      main.activate_progressive_pricing_preset, main.simulate_progressive_pricing_preset):
        errors = []
        for candidate in (UUID(presets[1]["id"]), uuid4()):
            args = {"preset_id": candidate, "request": first["admin_request"], "db": client_db}
            if operation is main.update_progressive_pricing_preset:
                args["payload"] = preset_input("alterado")
            if operation is main.simulate_progressive_pricing_preset:
                args["quantity"] = 2
            with pytest.raises(HTTPException) as exc:
                operation(**args)
            errors.append((exc.value.status_code, exc.value.detail))
        assert errors[0] == errors[1]
    result = main.update_progressive_pricing_preset(UUID(presets[0]["id"]), preset_input("novo A"), first["admin_request"], client_db)
    assert result["version"] == 2
    assert main.list_progressive_pricing_presets(configured[1]["admin_request"], False, client_db)["presets"][0]["version"] == 1
    with pytest.raises(HTTPException):
        main.save_admin_parent_gallery_pricing(first["parent"].id,
            main.GalleryPricingInput(pricing_mode="progressive", progressive_pricing_preset_id=presets[1]["id"]),
            first["admin_request"], client_db)
    assert first["parent"].progressive_pricing_preset_id is None


def test_preferencias_templates_e_protecao_alteram_somente_A(client_db, configured):
    first, second = configured
    before = main.list_notification_settings(second["admin_request"], client_db)
    setting = main.list_notification_settings(first["admin_request"], client_db)["settings"][0]
    fields = {key: setting[key] for key in main.NotificationSettingInput.model_fields}
    fields["whatsapp_enabled"] = not fields["whatsapp_enabled"]
    updated = main.update_notification_setting(setting["event_type"], main.NotificationSettingInput(**fields),
        first["admin_request"], client_db)
    assert updated["whatsapp_enabled"] == fields["whatsapp_enabled"]
    main.save_payment_template("confirmed", main.PaymentTemplateInput(body="Só A {{cliente}}"), first["admin_request"], client_db)
    assert main.list_notification_settings(second["admin_request"], client_db) == before
    main.update_visual_protection(main.VisualProtectionSettingsInput(watermark_text="Marca A", watermark_font="sans-serif",
        watermark_color="#FFFFFF", watermark_size=32, watermark_direction="diagonal"), first["admin_request"], client_db)
    jobs = list(client_db.scalars(select(MediaJob)))
    assert len(jobs) == 1 and jobs[0].tenant_id == first["tenant"].id
    assert main.admin_branding(second["admin_request"], client_db)["watermark_text"] != "Marca A"


def test_processamento_heranca_e_override_nao_alteram_B(client_db, configured):
    first, second = configured
    configure_preview(client_db, first["parent"].id, True, 65, 1, tenant_id=first["tenant"].id)
    client_db.commit()
    assert effective_preview(client_db, first["folder"]).strength == 65
    assert effective_preview(client_db, second["folder"]).enabled is False
    configure_folder(client_db, first["folder"].id, tenant_id=first["tenant"].id,
        preview_mode="custom", facial_mode="off", strength=30, exposure_tenths=-2)
    client_db.commit()
    assert effective_preview(client_db, first["folder"]).strength == 30
    assert effective_preview(client_db, second["folder"]).mode == "inherit"
    with pytest.raises(ValueError):
        configure_folder(client_db, second["folder"].id, tenant_id=first["tenant"].id,
            preview_mode="off", facial_mode="off", strength=30, exposure_tenths=0)
    with pytest.raises(ValueError):
        configure_preview(client_db, second["parent"].id, True, 60, tenant_id=first["tenant"].id)


def test_PIX_OTP_vinculado_owner_e_confirmacao_estrangeira_nao_consumida(client_db, configured, monkeypatch):
    # Adaptador de destinatário sintético; emissão persiste outbox sem enviar pela rede.
    monkeypatch.setattr(admin_account, "_admin_whatsapp_phone", lambda _db, *, tenant_id: "+5511999990010")
    challenges = []
    for row, label in zip(configured, ("A", "B"), strict=True):
        result = main.admin_global_pix_challenge(main.GlobalPixChallengeInput(current_password=PASSWORD,
            configuration=main.PixCheckoutSettingsInput(copy_paste=f"synthetic-{label}@example.test",
                receiver_name=f"SINTETICO {label}", receiver_city="SAO PAULO")), row["admin_request"], client_db)
        challenge = client_db.get(AdminSecurityChallenge, UUID(result["challenge_id"]))
        assert challenge.tenant_id == row["tenant"].id and challenge.secret_hash != "123456"
        challenges.append(challenge)
    first, second = configured
    with pytest.raises(HTTPException) as exc:
        main.admin_global_pix_confirm(main.GlobalPixConfirmInput(challenge_id=challenges[1].id, code="123456"),
            first["admin_request"], client_db)
    assert exc.value.status_code == 401 and challenges[1].used_at is None and challenges[1].attempts == 0
    for row, challenge, label in zip(configured, challenges, ("A", "B"), strict=True):
        result = main.admin_global_pix_confirm(main.GlobalPixConfirmInput(challenge_id=challenge.id, code="123456"), row["admin_request"], client_db)
        assert result["receiver_name"] == f"SINTETICO {label}"
    assert main.admin_global_pix(second["admin_request"], client_db)["receiver_name"] == "SINTETICO B"


def test_tabela_propria_aplicada_sem_alterar_preco_B(client_db, configured):
    first, second = configured
    preset = main.create_progressive_pricing_preset(preset_input("A"), first["admin_request"], client_db)
    result = main.save_admin_parent_gallery_pricing(first["parent"].id,
        main.GalleryPricingInput(pricing_mode="progressive", progressive_pricing_preset_id=preset["id"]),
        first["admin_request"], client_db)
    assert result["pricing_mode"] == "progressive"
    rules = list(client_db.scalars(select(PriceRule)))
    assert len(rules) == 1 and rules[0].tenant_id == first["tenant"].id
    assert rules[0].unit_price_cents == 700
    assert second["parent"].progressive_pricing_preset_id is None


@pytest.mark.parametrize("action", ["verify", "resend"])
def test_PIX_vinculo_revogado_recusa_antes_de_consumir_ou_reenviar(client_db, configured, monkeypatch, action):
    first = configured[0]
    monkeypatch.setattr(admin_account, "_admin_whatsapp_phone", lambda _db, *, tenant_id: "+5511999990010")
    challenge, code, _ = admin_account.create_security_challenge(client_db, purpose="change_pix_otp",
        subject_fingerprint="synthetic-only", admin=first["admin"], tenant_id=first["tenant"].id)
    link = client_db.scalar(select(TenantAdmin).where(TenantAdmin.tenant_id == first["tenant"].id,
        TenantAdmin.admin_user_id == first["admin"].id))
    link.active = False
    client_db.commit()
    args = {"challenge_id": challenge.id, "purpose": "change_pix_otp", "tenant_id": first["tenant"].id}
    if action == "verify":
        args["code"] = code
    operation = getattr(admin_account, f"{action}_security_challenge")
    with pytest.raises(admin_account.AdminAccountError):
        operation(client_db, **args)
    assert challenge.used_at is None and challenge.attempts == 0 and challenge.resend_count == 0


def test_caminhos_marca_rejeitam_namespace_alheio_e_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("BRANDING_ASSETS_ROOT", str(tmp_path))
    owner = uuid4()
    for key in (f"tenants/{uuid4()}/branding/logo.png", "../logo.png", "folder/logo.png", "folder\\logo.png"):
        with pytest.raises(ValueError):
            main.branding_asset_path(key, tenant_id=owner)
    assert main.branding_asset_path("legacy.png", tenant_id=owner) == tmp_path / "legacy.png"


def test_marca_convite_privado_revalida_escopo_e_acesso(client_db, configured, links):
    record = configured[1]
    main.update_admin_branding(brand_input("B"), record["admin_request"], client_db)
    cap = links[1][1]
    with client_db.no_autoflush:
        cap.scope = "private_gallery_link"
        cap.derived_gallery_id = record["gallery"].id
    client_db.commit()
    assert main.public_branding(request(), Response(), links[1][0], client_db)["login_title"] == "Marca B"
    record["gallery"].access_enabled = False
    client_db.commit()
    assert main.public_branding(request(), Response(), links[1][0], client_db) == technical_branding()
