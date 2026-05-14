"""Pydantic business models for the demo e-commerce application."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict, Field, field_validator


TWOPLACES = Decimal("0.01")


def normalize_money(value: Decimal) -> Decimal:
    """Normalize Decimal values to currency precision."""

    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


class ShopModel(BaseModel):
    """Strict base model for demo shop payloads."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
    )


class Product(ShopModel):
    """Catalog item exposed to the order workflow."""

    sku: str = Field(min_length=3)
    title: str = Field(min_length=2)
    unit_price: Decimal = Field(gt=0)
    stock: int = Field(ge=0)

    @field_validator("unit_price")
    @classmethod
    def validate_unit_price(cls, value: Decimal) -> Decimal:
        return normalize_money(value)


class OrderItemRequest(ShopModel):
    """Requested item in a checkout command."""

    sku: str = Field(min_length=3)
    quantity: int = Field(gt=0, le=100)


class OrderCreateRequest(ShopModel):
    """Incoming command for creating an order."""

    customer_email: str = Field(min_length=5)
    promo_code: str | None = Field(default=None, min_length=4)
    items: tuple[OrderItemRequest, ...] = Field(min_length=1)

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.rsplit("@", maxsplit=1)[-1]:
            raise ValueError("customer_email must look like an email address")
        return value.lower()


class OrderLineResult(ShopModel):
    """Persisted line item returned by the service layer."""

    sku: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    line_total: Decimal = Field(gt=0)

    @field_validator("unit_price", "line_total")
    @classmethod
    def validate_money(cls, value: Decimal) -> Decimal:
        return normalize_money(value)


class OrderResult(ShopModel):
    """Checkout result returned to API or workflow clients."""

    order_id: int = Field(gt=0)
    customer_email: str
    promo_code: str | None = None
    subtotal: Decimal = Field(ge=0)
    discount_total: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)
    items: tuple[OrderLineResult, ...] = Field(min_length=1)

    @field_validator("subtotal", "discount_total", "total")
    @classmethod
    def validate_money(cls, value: Decimal) -> Decimal:
        return normalize_money(value)
