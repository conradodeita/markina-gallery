from datetime import UTC, datetime

import pyotp
import pytest

from app.totp_verification import matching_unused_totp_step


@pytest.mark.parametrize("code", ["١٢٣٤٥٦", "１２３４５６", "12345", "1234567", "abcdef", None])
def test_malformed_codes_are_rejected_without_comparison_errors(code):
    assert matching_unused_totp_step("JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP", code, None) is None


def test_valid_totp_step_is_returned_once_and_replay_is_rejected():
    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    at = datetime.fromtimestamp(1_800_000_000, UTC)
    totp = pyotp.TOTP(secret)
    current = totp.timecode(at)
    code = totp.at(current * totp.interval)

    assert matching_unused_totp_step(secret, code, None, at=at) == current
    assert matching_unused_totp_step(secret, code, current, at=at) is None


def test_window_and_previous_consumed_step_are_respected():
    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    at = datetime.fromtimestamp(1_800_000_000, UTC)
    totp = pyotp.TOTP(secret)
    current = totp.timecode(at)
    previous_code = totp.at((current - 1) * totp.interval)
    current_code = totp.at(current * totp.interval)

    assert matching_unused_totp_step(secret, previous_code, None, at=at) == current - 1
    assert matching_unused_totp_step(secret, current_code, current - 1, at=at) == current
    assert matching_unused_totp_step(secret, previous_code, current - 1, at=at) is None
