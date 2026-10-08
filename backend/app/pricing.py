"""Regras comerciais determinísticas para preço por faixas."""

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


def validate_tiers(tiers: Iterable[PriceTier]) -> list[PriceTier]:
    ordered = sorted(tiers, key=lambda tier: tier.minimum_quantity)
    if not ordered:
        raise PricingRuleError("Ao menos uma faixa de preço é obrigatória.")
    expected_minimum = 1
    for index, tier in enumerate(ordered):
        if tier.minimum_quantity != expected_minimum or tier.unit_price_cents < 0:
            raise PricingRuleError("As faixas devem ser contíguas, iniciar em 1 e usar centavos válidos.")
        if tier.maximum_quantity is None:
            if index != len(ordered) - 1:
                raise PricingRuleError("Somente a última faixa pode não ter limite máximo.")
            continue
        if tier.maximum_quantity < tier.minimum_quantity:
            raise PricingRuleError("O limite máximo não pode ser menor que o mínimo.")
        expected_minimum = tier.maximum_quantity + 1
    return ordered


def quote(quantity: int, tiers: Iterable[PriceTier]) -> tuple[PriceTier, int]:
    if quantity < 1:
        raise PricingRuleError("A seleção precisa ter ao menos uma foto.")
    for tier in validate_tiers(tiers):
        if quantity >= tier.minimum_quantity and (tier.maximum_quantity is None or quantity <= tier.maximum_quantity):
            return tier, quantity * tier.unit_price_cents
    raise PricingRuleError("Nenhuma faixa atende a quantidade selecionada.")


def has_downward_jump(tiers: Iterable[PriceTier]) -> bool:
    ordered = validate_tiers(tiers)
    for previous, current in pairwise(ordered):
        _, before_total = quote((previous.maximum_quantity or current.minimum_quantity - 1), ordered)
        _, after_total = quote(current.minimum_quantity, ordered)
        if after_total < before_total:
            return True
    return False
