"""Cotação autoritativa da configuração comercial materializada na galeria."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import ParentGallery, PriceRule
from app.pricing import PriceTier, PricingRuleError, ProgressiveQuote, progressive_quote


class GalleryPricingError(ValueError):
    pass


@dataclass(frozen=True)
class GalleryQuote:
    quote: ProgressiveQuote
    snapshot: dict[str, object]


def quote_parent_gallery(
    db: Session, *, gallery: ParentGallery, quantity: int
) -> GalleryQuote:
    if gallery.pricing_mode == "legacy_volume" or gallery.pricing_review_required:
        raise GalleryPricingError(
            "A configuração comercial desta galeria precisa ser revisada antes de novas compras."
        )
    rules = list(
        db.scalars(
            select(PriceRule)
            .where(PriceRule.parent_gallery_id == gallery.id)
            .order_by(PriceRule.minimum_quantity)
        )
    )
    tiers = [
        PriceTier(rule.minimum_quantity, rule.maximum_quantity, rule.unit_price_cents)
        for rule in rules
    ]
    try:
        result = progressive_quote(quantity, tiers)
    except PricingRuleError as exc:
        raise GalleryPricingError("As regras de preço desta galeria não estão prontas.") from exc

    configured = gallery.pricing_snapshot or {}
    snapshot: dict[str, object] = {
        "mode": gallery.pricing_mode,
        "preset_id": configured.get("preset_id"),
        "preset_code": configured.get("preset_code"),
        "preset_name": configured.get("preset_name"),
        "preset_version": configured.get("preset_version"),
        "tiers": [
            {
                "minimum_quantity": tier.minimum_quantity,
                "maximum_quantity": tier.maximum_quantity,
                "unit_price_cents": tier.unit_price_cents,
            }
            for tier in tiers
        ],
        "parcels": [
            {
                "minimum_quantity": parcel.minimum_quantity,
                "maximum_quantity": parcel.maximum_quantity,
                "quantity": parcel.quantity,
                "unit_price_cents": parcel.unit_price_cents,
                "subtotal_cents": parcel.subtotal_cents,
            }
            for parcel in result.parcels
        ],
        "quantity": result.quantity,
        "base_total_cents": result.base_total_cents,
        "savings_cents": result.savings_cents,
        "total_cents": result.total_cents,
    }
    if gallery.pricing_mode == "fixed":
        snapshot["minimum_quantity"] = 1
        snapshot["maximum_quantity"] = None
        snapshot["unit_price_cents"] = result.active_tier.unit_price_cents
    return GalleryQuote(quote=result, snapshot=snapshot)
