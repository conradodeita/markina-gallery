import pytest

from app.pricing import (
    PriceTier,
    PricingRuleError,
    has_downward_jump,
    progressive_quote,
    quote,
    validate_tiers,
)


def test_quote_charges_each_progressive_parcel():
    tiers = [PriceTier(1, 30, 700), PriceTier(31, None, 600)]
    tier, total = quote(31, tiers)
    assert tier.unit_price_cents == 600
    assert total == 21600


def test_progressive_quote_details_parcels_and_savings():
    result = progressive_quote(
        60,
        [PriceTier(1, 30, 700), PriceTier(31, None, 600)],
    )

    assert result.total_cents == 39000
    assert result.base_total_cents == 42000
    assert result.savings_cents == 3000
    assert [parcel.quantity for parcel in result.parcels] == [30, 30]
    assert [parcel.subtotal_cents for parcel in result.parcels] == [21000, 18000]


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
        [PriceTier(1, 10, 600), PriceTier(11, None, 700)],
    ],
)
def test_tiers_reject_gaps_overlaps_and_invalid_values(tiers):
    with pytest.raises(PricingRuleError):
        validate_tiers(tiers)


def test_progressive_calculation_never_has_a_downward_jump():
    assert not has_downward_jump([PriceTier(1, 30, 700), PriceTier(31, None, 600)])


def test_does_not_alert_when_next_tier_keeps_or_increases_total():
    assert not has_downward_jump([PriceTier(1, 10, 500), PriceTier(11, None, 500)])
