import { PricingTier } from "../types";

export const DEFAULT_PRICING_TIERS: PricingTier[] = [
  {
    id: "tier-1",
    minQty: 1,
    maxQty: 4,
    unitPrice: 25.0,
    discountPercent: 0,
    label: "1 a 4 fotos",
    badge: "Preço Avulso",
  },
  {
    id: "tier-2",
    minQty: 5,
    maxQty: 9,
    unitPrice: 20.0,
    discountPercent: 20,
    label: "5 a 9 fotos",
    badge: "20% OFF",
  },
  {
    id: "tier-3",
    minQty: 10,
    maxQty: 19,
    unitPrice: 16.0,
    discountPercent: 36,
    label: "10 a 19 fotos",
    badge: "36% OFF • Mais Popular",
  },
  {
    id: "tier-4",
    minQty: 20,
    maxQty: null,
    unitPrice: 12.0,
    discountPercent: 52,
    label: "20 ou mais fotos",
    badge: "52% OFF • Super Desconto",
  },
];

export interface PriceCalculationResult {
  totalPhotos: number;
  unitPrice: number;
  totalAmount: number;
  originalAmount: number;
  savings: number;
  currentTier: PricingTier;
  nextTier: PricingTier | null;
  photosNeededForNextTier: number;
  nextTierUnitPrice: number;
}

export function calculateProgressivePrice(
  qty: number,
  tiers: PricingTier[] = DEFAULT_PRICING_TIERS,
  baseUnitPrice = 25.0,
): PriceCalculationResult {
  if (qty <= 0) {
    return {
      totalPhotos: 0,
      unitPrice: baseUnitPrice,
      totalAmount: 0,
      originalAmount: 0,
      savings: 0,
      currentTier: tiers[0],
      nextTier: tiers[1] || null,
      photosNeededForNextTier: tiers[1] ? tiers[1].minQty : 0,
      nextTierUnitPrice: tiers[1] ? tiers[1].unitPrice : baseUnitPrice,
    };
  }

  // Find active tier
  let activeTier = tiers[0];
  for (const tier of tiers) {
    if (qty >= tier.minQty && (tier.maxQty === null || qty <= tier.maxQty)) {
      activeTier = tier;
      break;
    }
  }

  const effectiveUnitPrice = activeTier.unitPrice;
  const totalAmount = qty * effectiveUnitPrice;
  const originalAmount = qty * baseUnitPrice;
  const savings = Math.max(0, originalAmount - totalAmount);

  // Find next tier if available
  const currentTierIndex = tiers.findIndex((t) => t.id === activeTier.id);
  const nextTier =
    currentTierIndex >= 0 && currentTierIndex < tiers.length - 1
      ? tiers[currentTierIndex + 1]
      : null;

  const photosNeededForNextTier = nextTier
    ? Math.max(0, nextTier.minQty - qty)
    : 0;
  const nextTierUnitPrice = nextTier ? nextTier.unitPrice : effectiveUnitPrice;

  return {
    totalPhotos: qty,
    unitPrice: effectiveUnitPrice,
    totalAmount,
    originalAmount,
    savings,
    currentTier: activeTier,
    nextTier,
    photosNeededForNextTier,
    nextTierUnitPrice,
  };
}

export function formatCurrencyBRL(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

export function generateMockPixCode(orderId: string, amount: number): string {
  const cleanAmount = amount.toFixed(2);
  return `00020126580014br.gov.bcb.pix0136pix@markinagallery.com.br520400005303986540${cleanAmount.length.toString().padStart(2, "0")}${cleanAmount}5802BR5925MARKINA STUDIOS FOTOGRAF6009SAO PAULO62170513${orderId}6304`;
}
