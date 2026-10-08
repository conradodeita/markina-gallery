import pytest

from app.pricing import (
    PriceTier,
    PricingRuleError,
    has_downward_jump,
    quote,
    validate_tiers,
)


def test_quote_uses_one_tier_for_the_entire_quantity():
    tiers = [PriceTier(1, 30, 700), PriceTier(31, None, 600)]
    tier, total = quote(31, tiers)
    assert tier.unit_price_cents == 600
    assert total == 18600


def test_tiers_must_be_contiguous_from_one():
    with pytest.raises(PricingRuleError):
        validate_tiers([PriceTier(2, None, 500)])


@pytest.mark.parametrize(
    "tiers",
    [
        [PriceTier(1, 10, 700), PriceTier(12, None, 600)],
        [PriceTier(1, None, 700), PriceTier(2, None, 600)],
        [PriceTier(1, 10, -1), PriceTier(11, None, 600)],
        [PriceTier(1, 10, 700), PriceTier(11, 10, 600)],
    ],
)
def test_tiers_reject_gaps_overlaps_and_invalid_values(tiers):
    with pytest.raises(PricingRuleError):
        validate_tiers(tiers)


def test_detects_downward_commercial_jump():
    assert has_downward_jump([PriceTier(1, 30, 700), PriceTier(31, None, 600)])


def test_does_not_alert_when_next_tier_keeps_or_increases_total():
    assert not has_downward_jump([PriceTier(1, 10, 500), PriceTier(11, None, 500)])
