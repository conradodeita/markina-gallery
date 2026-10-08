import pytest

from app.payment_templates import render_template, validate_template


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
