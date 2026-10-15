"""Contrato estático da matriz; sem banco, transporte ou credenciais."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationDefinition:
    label: str
    recipient: str
    title: str
    body: str
    variables: tuple[str, ...]


DEFINITIONS = {
    "first_access": NotificationDefinition(
        "Primeiro acesso à galeria", "admin", "Primeiro acesso",
        "{{cliente}} acessou {{galeria}}.", ("cliente", "galeria"),
    ),
    "first_selection": NotificationDefinition(
        "Primeira foto selecionada", "admin", "Seleção iniciada",
        "{{cliente}} começou a escolher em {{galeria}}.", ("cliente", "galeria"),
    ),
    "private_photos_ready": NotificationDefinition(
        "Novas fotos privadas", "client", "Novas fotos",
        "Novas fotos disponíveis na sua galeria.", ("cliente", "galeria"),
    ),
    "payment_reported": NotificationDefinition(
        "Pagamento informado", "admin", "Pagamento informado",
        "{{cliente}} informou pagamento {{contexto_pagamento}}.",
        ("cliente", "galeria", "pedido", "contexto_pagamento"),
    ),
    "payment_confirmed": NotificationDefinition(
        "Pagamento confirmado", "client", "Pagamento confirmado",
        "Confirmamos o pagamento {{contexto_pagamento}}.",
        ("cliente", "galeria", "pedido", "contexto_pagamento"),
    ),
    "payment_refused": NotificationDefinition(
        "Pagamento recusado", "client", "Pagamento não localizado",
        "Não localizamos o pagamento {{contexto_pagamento}}. Confira os dados.",
        ("cliente", "galeria", "pedido", "contexto_pagamento"),
    ),
    "order_delivery_ready": NotificationDefinition(
        "Fotos disponíveis", "client", "Fotos disponíveis",
        "Suas fotos estão prontas! Acesse Compras para abrir seu álbum.",
        ("cliente", "galeria", "pedido"),
    ),
}
