export type PriceTier = {
  minimum_quantity: number;
  maximum_quantity: number | null;
  unit_price_cents: number;
};

export function hasDownwardJump(tiers: PriceTier[]) {
  return tiers.some((tier, index) => {
    const next = tiers[index + 1];
    return next !== undefined
      && tier.maximum_quantity !== null
      && next.minimum_quantity * next.unit_price_cents
        < tier.maximum_quantity * tier.unit_price_cents;
  });
}

export function appendContiguousTier(tiers: PriceTier[]) {
  const previous = tiers.at(-1);
  if (!previous) return [{ minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 0 }];
  const previousEnd = previous.maximum_quantity ?? previous.minimum_quantity;
  return [
    ...tiers.slice(0, -1),
    { ...previous, maximum_quantity: previousEnd },
    {
      minimum_quantity: previousEnd + 1,
      maximum_quantity: null,
      unit_price_cents: previous.unit_price_cents,
    },
  ];
}

export function removeContiguousTier(tiers: PriceTier[], removeIndex: number) {
  if (tiers.length <= 1) return tiers;
  const remaining = tiers.filter((_, index) => index !== removeIndex);
  return remaining.map((tier, index) => ({
    ...tier,
    minimum_quantity: index === 0
      ? 1
      : (remaining[index - 1].maximum_quantity ?? tier.minimum_quantity - 1) + 1,
  }));
}
