"""Templates controlados para notificações de pagamento."""

from __future__ import annotations

import re

ALLOWED_VARIABLES = {"cliente", "pedido", "galeria"}
DEFAULT_PAYMENT_TEMPLATES = {
    "confirmed": (
        "Olá {{cliente}}, confirmamos o pagamento do pedido {{pedido}} "
        "da galeria {{galeria}}. Suas fotos seguirão para edição."
    ),
    "refused": (
        "Olá {{cliente}}, não localizamos o pagamento do pedido {{pedido}} "
        "da galeria {{galeria}}. Revise os dados antes de comunicar novamente."
    ),
}
PLACEHOLDER = re.compile(r"{{\s*([a-z_]+)\s*}}")
FORBIDDEN_URL = re.compile(r"(?:https?://|www\.|data:)", re.IGNORECASE)


def validate_template(body: str) -> str:
    normalized = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ValueError("Informe um texto para a mensagem.")
    if len(normalized) > 500:
        raise ValueError("A mensagem deve ter no máximo 500 caracteres.")
    if "<" in normalized or ">" in normalized:
        raise ValueError("Use apenas texto simples.")
    if FORBIDDEN_URL.search(normalized):
        raise ValueError("URLs não são permitidas neste template.")
    variables = set(PLACEHOLDER.findall(normalized))
    if not variables.issubset(ALLOWED_VARIABLES):
        raise ValueError("Variável não permitida.")
    without_placeholders = PLACEHOLDER.sub("", normalized)
    if "{" in without_placeholders or "}" in without_placeholders:
        raise ValueError("Use somente as variáveis permitidas no formato {{variavel}}.")
    if any(ord(character) < 32 and character not in {"\n", "\t"} for character in normalized):
        raise ValueError("A mensagem contém caracteres de controle não permitidos.")
    return normalized


def render_template(body: str, *, cliente: str, pedido: str, galeria: str) -> str:
    values = {"cliente": cliente, "pedido": pedido, "galeria": galeria}
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], validate_template(body))
