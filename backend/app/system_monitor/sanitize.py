"""Projeções fechadas compartilhadas por snapshots e exportação."""
from datetime import datetime
from math import isfinite


def number(value):
    return value if type(value) in {int, float} and isfinite(value) and value >= 0 else None


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.isoformat() if parsed.tzinfo else None
    except ValueError:
        return None
