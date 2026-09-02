"""Valores visuais controlados e compartilhados pelos contratos de galeria."""

TITLE_FONT_OPTIONS: tuple[dict[str, str], ...] = (
    {
        "token": "system-sans",
        "label": "Sistema",
        "category": "sans",
        "css_family": "var(--font-system-sans)",
    },
    {
        "token": "montserrat",
        "label": "Montserrat",
        "category": "sans",
        "css_family": "var(--font-montserrat)",
    },
    {
        "token": "system-rounded",
        "label": "Arredondada",
        "category": "sans",
        "css_family": "var(--font-system-rounded)",
    },
    {
        "token": "system-serif",
        "label": "Clássica",
        "category": "editorial",
        "css_family": "var(--font-system-serif)",
    },
    {
        "token": "playfair-display",
        "label": "Playfair Display",
        "category": "editorial",
        "css_family": "var(--font-playfair-display)",
    },
    {
        "token": "handwritten-caveat",
        "label": "Caveat",
        "category": "handwritten",
        "css_family": "var(--font-caveat)",
    },
    {
        "token": "handwritten-dancing-script",
        "label": "Dancing Script",
        "category": "handwritten",
        "css_family": "var(--font-dancing-script)",
    },
    {
        "token": "handwritten-personal",
        "label": "Assinatura",
        "category": "handwritten",
        "css_family": "var(--font-handwritten-personal)",
    },
)

TITLE_FONT_TOKENS: frozenset[str] = frozenset(option["token"] for option in TITLE_FONT_OPTIONS)
LEGACY_TITLE_FONT_TOKENS: dict[str, str] = {
    "sans-serif": "system-sans",
    "DejaVuSans": "system-sans",
    "serif": "system-serif",
    "DejaVuSerif": "system-serif",
    "monospace": "system-sans",
}


def normalize_title_font(value: str | None) -> str:
    """Normaliza somente valores persistidos conhecidos; desconhecidos viram fallback seguro."""
    if not value:
        return "system-sans"
    return (
        value if value in TITLE_FONT_TOKENS else LEGACY_TITLE_FONT_TOKENS.get(value, "system-sans")
    )


def validate_title_font(value: str) -> str:
    """Rejeita CSS, URL ou família arbitrária em mutações administrativas."""
    if value not in TITLE_FONT_TOKENS:
        raise ValueError("Selecione uma tipografia de título suportada")
    return value
