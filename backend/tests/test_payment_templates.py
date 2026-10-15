import pytest

from app.payment_templates import (
    DEFAULT_PAYMENT_TEMPLATES,
    preview_payment_template_migration,
    render_template,
    validate_template,
)


def test_payment_template_allows_only_controlled_variables() -> None:
    body = "Olá {{cliente}}, pedido {{pedido}} da galeria {{galeria}}."
    assert render_template(body, cliente="Ana", pedido="123", galeria="Evento") == "Olá Ana, pedido 123 da galeria Evento."
    with pytest.raises(ValueError):
        validate_template("<b>texto</b>")
    with pytest.raises(ValueError):
        validate_template("{{segredo}}")
    with pytest.raises(ValueError):
        validate_template("{{cliente")
    with pytest.raises(ValueError):
        validate_template("Acesse https://exemplo.invalid/comprovante")
    with pytest.raises(ValueError):
        validate_template("texto } solto")


def test_payment_template_accepts_spacing_without_arbitrary_interpolation() -> None:
    assert render_template(
        "Olá {{ cliente }}, pedido {{pedido}} da galeria {{ galeria }}.",
        cliente="Ana",
        pedido="abc123",
        galeria="Formatura",
    ) == "Olá Ana, pedido abc123 da galeria Formatura."


def test_grouped_and_individual_context_render_with_existing_reference():
    body = DEFAULT_PAYMENT_TEMPLATES["confirmed"]
    assert render_template(body, cliente="Ana", pedido="bebb98d7", galeria="sua compra",
                           contexto_pagamento="da compra bebb98d7") == (
        "Olá Ana, confirmamos o pagamento da compra bebb98d7. Suas fotos seguirão para edição."
    )
    assert render_template(body, cliente="Ana", pedido="1b55d2b5", galeria="Formatura",
                           contexto_pagamento="do pedido 1b55d2b5 da galeria Formatura") == (
        "Olá Ana, confirmamos o pagamento do pedido 1b55d2b5 da galeria Formatura. "
        "Suas fotos seguirão para edição."
    )


def test_legacy_template_migration_preview_is_narrow_reversible_and_idempotent():
    source = {
        "confirmed": "Olá {{cliente}}, confirmamos o pagamento do pedido {{pedido}} da galeria {{galeria}}. Obrigado!",
        "payment_reported.whatsapp_body": "{{cliente}} informou pagamento do pedido {{pedido}}.",
        "custom": "Aviso {{cliente}}: seu pedido {{pedido}} está em revisão.",
    }
    preview = preview_payment_template_migration(source)
    assert preview["confirmed"] == {
        "before": source["confirmed"],
        "after": "Olá {{cliente}}, confirmamos o pagamento {{contexto_pagamento}}. Obrigado!",
        "changed": True,
        "recognized": True,
    }
    assert preview["custom"]["before"] == preview["custom"]["after"] == source["custom"]
    assert preview["custom"]["changed"] is False and preview["custom"]["recognized"] is False
    assert preview["payment_reported.whatsapp_body"]["after"] == (
        "{{cliente}} informou pagamento {{contexto_pagamento}}."
    )
    assert preview_payment_template_migration({"confirmed": preview["confirmed"]["after"]})[
        "confirmed"]["changed"] is False
