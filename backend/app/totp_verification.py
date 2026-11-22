"""Verificação one-time de um passo TOTP dentro da janela contratada."""

from __future__ import annotations

import hmac
from datetime import UTC, datetime

import pyotp


def matching_unused_totp_step(
    secret: str,
    submitted_code: str,
    last_used_step: int | None,
    *,
    at: datetime | None = None,
    valid_window: int = 1,
) -> int | None:
    if (not isinstance(submitted_code, str) or len(submitted_code) != 6
            or not submitted_code.isascii() or not submitted_code.isdigit()):
        return None
    totp = pyotp.TOTP(secret)
    current = totp.timecode(at or datetime.now(UTC))
    steps = [current, *[current + offset for offset in range(-valid_window, valid_window + 1)
                         if offset != 0]]
    for step in steps:
        if step < 0 or (last_used_step is not None and step <= last_used_step):
            continue
        expected = totp.at(step * totp.interval)
        if hmac.compare_digest(expected, submitted_code):
            return step
    return None
