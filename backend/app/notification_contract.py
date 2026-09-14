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
}
