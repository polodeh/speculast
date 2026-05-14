"""Demo e-commerce application used by speculast."""

from .logic import (
    calculate_discount,
    calculate_line_total,
    calculate_order_total,
    validate_stock,
)
from .models import OrderCreateRequest, OrderItemRequest, OrderResult, Product
from .service import create_order

__all__ = [
    "OrderCreateRequest",
    "OrderItemRequest",
    "OrderResult",
    "Product",
    "calculate_discount",
    "calculate_line_total",
    "calculate_order_total",
    "create_order",
    "validate_stock",
]
