"""Sample-project regression checks for arithmetic business rules."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.support.sample_project import load_sample_module


logic_module = load_sample_module("logic")
calculate_discount = logic_module.calculate_discount
calculate_line_total = logic_module.calculate_line_total
calculate_order_total = logic_module.calculate_order_total
validate_stock = logic_module.validate_stock


def test_calculate_line_total_multiplies_price_by_quantity() -> None:
    assert calculate_line_total(Decimal("19.99"), 3) == Decimal("59.97")


def test_calculate_discount_valid_total() -> None:
    assert calculate_discount(Decimal("200.00"), "WELCOME10") == Decimal("20.00")


def test_calculate_discount_unknown_code_returns_zero() -> None:
    assert calculate_discount(Decimal("200.00"), "NOPE") == Decimal("0.00")


def test_calculate_order_total_applies_discount() -> None:
    assert calculate_order_total(Decimal("120.00"), Decimal("18.00")) == Decimal("102.00")


def test_validate_stock_rejects_insufficient_inventory() -> None:
    with pytest.raises(ValueError, match="insufficient stock"):
        validate_stock(available_quantity=1, requested_quantity=2)


