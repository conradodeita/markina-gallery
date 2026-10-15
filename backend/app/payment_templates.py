"""Templates controlados para notificações de pagamento."""

from __future__ import annotations

import re

ALLOWED_VARIABLES = {"cliente", "pedido", "galeria", "contexto_pagamento"}
DEFAULT_PAYMENT_TEMPLATES = {
    "confirmed": (
        "Olá {{cliente}}, confirmamos o pagamento {{contexto_pagamento}}. "
        "Suas fotos seguirão para edição."
    ),
    "refused": (
        "Olá {{cliente}}, não localizamos o pagamento {{contexto_pagamento}}. "
        "Revise os dados antes de comunicar novamente."
    ),
}
PLACEHOLDER = re.compile(r"{{\s*([a-z_]+)\s*}}")
FORBIDDEN_URL = re.compile(r"(?:https?://|www\.|data:)", re.IGNORECASE)
LEGACY_PAYMENT_REFERENCES = (
    re.compile(r"do pedido\s+{{\s*pedido\s*}}\s+da galeria\s+{{\s*galeria\s*}}", re.IGNORECASE),
    re.compile(r"informou pagamento do pedido\s+{{\s*pedido\s*}}", re.IGNORECASE),
)


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


def preview_payment_template_migration(templates: dict[str, str]) -> dict[str, dict[str, object]]:
    """Return a reversible before/after preview; callers decide whether to apply it."""
    preview = {}
    for kind, body in templates.items():
        transformed = body
        count = 0
        for pattern in LEGACY_PAYMENT_REFERENCES:
            transformed, replacements = pattern.subn(
                "{{contexto_pagamento}}" if "galeria" in pattern.pattern
                else "informou pagamento {{contexto_pagamento}}",
                transformed,
            )
            count += replacements
        preview[kind] = {
            "before": body,
            "after": transformed,
            "changed": count > 0,
            "recognized": count > 0 or "{{contexto_pagamento}}" in body,
        }
    return preview


def render_template(body: str, *, cliente: str, pedido: str, galeria: str,
                    contexto_pagamento: str | None = None) -> str:
    values = {"cliente": cliente, "pedido": pedido, "galeria": galeria,
              "contexto_pagamento": contexto_pagamento or f"do pedido {pedido} da galeria {galeria}"}
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], validate_template(body))
