"""Contrato do intervalo sem cartão: sem rotas InfinitePay e com PIX preservado."""

from app.auth import Base, ProviderPayment
from app.main import app


def test_rotas_de_operacao_infinitepay_nao_estao_registradas():
    paths = set(app.openapi()["paths"])
    assert "/admin/settings/infinitepay" not in paths
    assert "/admin/settings/infinitepay/challenge" not in paths
    assert "/library/cart/prepare-card" not in paths
    assert "/infinitepay/return" not in paths
    assert "/infinitepay/webhook" not in paths
    assert not any("cart-recovery" in path for path in paths)


def test_pix_manual_e_historico_financeiro_continuam_mapeados():
    paths = set(app.openapi()["paths"])
    assert "/library/cart/prepare" in paths
    assert "/library/payments/{group_id}/report" in paths
    assert "infinitepay_settings" not in Base.metadata.tables
    assert "infinitepay_credential" not in Base.metadata.tables
    assert "checkout_url" not in ProviderPayment.__table__.c
    assert {"provider_payment", "provider_payment_attempt", "provider_payment_receipt",
            "provider_payment_correction"} <= Base.metadata.tables.keys()
