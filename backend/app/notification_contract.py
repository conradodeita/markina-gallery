"""Contrato estático da matriz; sem banco, transporte ou credenciais."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationDefinition:
    label: str
    recipient: str
    title: str
    body: str
    variables: tuple[str, ...]
    whatsapp_body: str | None = None
    whatsapp_extra_variables: tuple[str, ...] = ()


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
        "{{cliente}} informou pagamento do pedido {{pedido}}.",
        ("cliente", "galeria", "pedido"),
    ),
    "payment_confirmed": NotificationDefinition(
        "Pagamento confirmado", "client", "Pagamento confirmado",
        "Confirmamos o pagamento do seu pedido.", ("cliente", "galeria", "pedido"),
    ),
    "payment_refused": NotificationDefinition(
        "Pagamento recusado", "client", "Pagamento não localizado",
        "Não localizamos seu pagamento. Confira seu pedido.",
        ("cliente", "galeria", "pedido"),
    ),
    "order_delivery_ready": NotificationDefinition(
        "Fotos disponíveis", "client", "Fotos disponíveis",
        "Suas fotos estão prontas! Acesse Compras para abrir seu álbum.",
        ("cliente", "galeria", "pedido"),
        "Suas fotos estão prontas! Acesse {{link_compras}} para abrir seu álbum.",
        ("link_compras",),
    ),
}


TRANSACTIONAL_WHATSAPP_GATED_EVENTS = frozenset({
    "first_access",
    "first_selection",
    "private_photos_ready",
})


def whatsapp_event_gate_open(event_type: str, *, global_gate_enabled: bool) -> bool:
    """Apply the rollout gate only to the three newer notification events."""
    if event_type.startswith("payment_") or event_type == "order_delivery_ready":
        return True
    return event_type in TRANSACTIONAL_WHATSAPP_GATED_EVENTS and global_gate_enabled
