"""Regras comerciais determinísticas para preço fixo e progressivo."""

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise


class PricingRuleError(ValueError):
    pass


@dataclass(frozen=True)
class PriceTier:
    minimum_quantity: int
    maximum_quantity: int | None
    unit_price_cents: int


@dataclass(frozen=True)
class PriceParcel:
    minimum_quantity: int
    maximum_quantity: int | None
    quantity: int
    unit_price_cents: int
    subtotal_cents: int


@dataclass(frozen=True)
class ProgressiveQuote:
    active_tier: PriceTier
    quantity: int
    parcels: tuple[PriceParcel, ...]
    total_cents: int
    base_total_cents: int
    savings_cents: int


def validate_tiers(tiers: Iterable[PriceTier]) -> list[PriceTier]:
    ordered = sorted(tiers, key=lambda tier: tier.minimum_quantity)
    if not ordered:
        raise PricingRuleError("Ao menos uma faixa de preço é obrigatória.")
    expected_minimum = 1
    previous_price: int | None = None
    for index, tier in enumerate(ordered):
        if tier.minimum_quantity != expected_minimum or tier.unit_price_cents < 0:
            raise PricingRuleError("As faixas devem ser contíguas, iniciar em 1 e usar centavos válidos.")
        if tier.maximum_quantity is None:
            if index != len(ordered) - 1:
                raise PricingRuleError("Somente a última faixa pode não ter limite máximo.")
        else:
            if tier.maximum_quantity < tier.minimum_quantity:
                raise PricingRuleError("O limite máximo não pode ser menor que o mínimo.")
            expected_minimum = tier.maximum_quantity + 1
        if previous_price is not None and tier.unit_price_cents > previous_price:
            raise PricingRuleError(
                "O preço unitário não pode aumentar nas faixas progressivas."
            )
        previous_price = tier.unit_price_cents
    return ordered


def progressive_quote(quantity: int, tiers: Iterable[PriceTier]) -> ProgressiveQuote:
    if quantity < 1:
        raise PricingRuleError("A seleção precisa ter ao menos uma foto.")
    ordered = validate_tiers(tiers)
    parcels: list[PriceParcel] = []
    active_tier: PriceTier | None = None
    for tier in ordered:
        if quantity < tier.minimum_quantity:
            break
        upper_bound = quantity
        if tier.maximum_quantity is not None:
            upper_bound = min(quantity, tier.maximum_quantity)
        parcel_quantity = upper_bound - tier.minimum_quantity + 1
        if parcel_quantity < 1:
            continue
        parcels.append(
            PriceParcel(
                minimum_quantity=tier.minimum_quantity,
                maximum_quantity=tier.maximum_quantity,
                quantity=parcel_quantity,
                unit_price_cents=tier.unit_price_cents,
                subtotal_cents=parcel_quantity * tier.unit_price_cents,
            )
        )
        active_tier = tier
        if upper_bound == quantity:
            break
    if active_tier is None or sum(parcel.quantity for parcel in parcels) != quantity:
        raise PricingRuleError("Nenhuma faixa atende a quantidade selecionada.")
    total_cents = sum(parcel.subtotal_cents for parcel in parcels)
    base_total_cents = quantity * ordered[0].unit_price_cents
    return ProgressiveQuote(
        active_tier=active_tier,
        quantity=quantity,
        parcels=tuple(parcels),
        total_cents=total_cents,
        base_total_cents=base_total_cents,
        savings_cents=max(0, base_total_cents - total_cents),
    )


def quote(quantity: int, tiers: Iterable[PriceTier]) -> tuple[PriceTier, int]:
    result = progressive_quote(quantity, tiers)
    return result.active_tier, result.total_cents


def has_downward_jump(tiers: Iterable[PriceTier]) -> bool:
    ordered = validate_tiers(tiers)
    for previous, current in pairwise(ordered):
        before_quantity = previous.maximum_quantity or current.minimum_quantity - 1
        _, before_total = quote(before_quantity, ordered)
        _, after_total = quote(current.minimum_quantity, ordered)
        if after_total < before_total:
            return True
    return False
