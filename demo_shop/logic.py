"""Business logic for pricing, discounts and stock validation."""

from __future__ import annotations

from decimal import Decimal

from .models import normalize_money


PROMO_DISCOUNTS: dict[str, Decimal] = {
    "WELCOME10": Decimal("0.10"),
    "VIP15": Decimal("0.15"),
}


def calculate_line_total(unit_price: Decimal, quantity: int) -> Decimal:
    """Calculate line total for a product quantity."""

    if quantity <= 0:
        raise ValueError("quantity must be positive")
    return normalize_money(unit_price * quantity)


def calculate_discount(subtotal: Decimal, promo_code: str | None = None) -> Decimal:
    """Calculate discount amount for a subtotal and optional promo."""

    normalized_subtotal = normalize_money(subtotal)
    if normalized_subtotal <= 0:
        return Decimal("0.00")

    discount_rate = PROMO_DISCOUNTS.get((promo_code or "").upper(), Decimal("0.00"))
    return normalize_money(normalized_subtotal * discount_rate)


def calculate_order_total(subtotal: Decimal, discount_total: Decimal) -> Decimal:
    """Calculate final order total after discounts."""

    total = normalize_money(subtotal) - normalize_money(discount_total)
    if total < 0:
        raise ValueError("discount_total cannot exceed subtotal")
    return normalize_money(total)


def validate_stock(available_quantity: int, requested_quantity: int) -> None:
    """Ensure enough stock exists for a requested purchase."""

    if requested_quantity <= 0:
        raise ValueError("requested_quantity must be positive")
    if available_quantity < requested_quantity:
        raise ValueError("insufficient stock for requested quantity")
