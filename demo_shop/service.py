"""Asynchronous order service for the demo shop."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import OrderItemRecord, OrderRecord, ProductRecord
from .logic import calculate_discount, calculate_line_total, calculate_order_total, validate_stock
from .models import OrderCreateRequest, OrderLineResult, OrderResult, normalize_money


async def create_order(session: AsyncSession, payload: OrderCreateRequest) -> OrderResult:
    """Create an order, persist it and decrement catalog inventory."""

    requested_skus = [item.sku for item in payload.items]
    product_result = await session.execute(
        select(ProductRecord).where(ProductRecord.sku.in_(requested_skus))
    )
    products = {
        product.sku: product
        for product in product_result.scalars().all()
    }

    missing_skus = [sku for sku in requested_skus if sku not in products]
    if missing_skus:
        raise ValueError(f"unknown products requested: {', '.join(sorted(missing_skus))}")

    subtotal = Decimal("0.00")
    line_items: list[OrderLineResult] = []
    order_record = OrderRecord(
        customer_email=payload.customer_email,
        promo_code=payload.promo_code,
        subtotal=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        total=Decimal("0.00"),
    )
    session.add(order_record)
    await session.flush()

    for requested_item in payload.items:
        product = products[requested_item.sku]
        validate_stock(product.stock, requested_item.quantity)

        line_total = calculate_line_total(product.unit_price, requested_item.quantity)
        subtotal += line_total
        product.stock -= requested_item.quantity

        order_item = OrderItemRecord(
            order_id=order_record.id,
            product_id=product.id,
            sku=product.sku,
            quantity=requested_item.quantity,
            unit_price=normalize_money(product.unit_price),
            line_total=line_total,
        )
        session.add(order_item)

        line_items.append(
            OrderLineResult(
                sku=product.sku,
                quantity=requested_item.quantity,
                unit_price=normalize_money(product.unit_price),
                line_total=line_total,
            )
        )

    discount_total = calculate_discount(subtotal, payload.promo_code)
    total = calculate_order_total(subtotal, discount_total)

    order_record.subtotal = normalize_money(subtotal)
    order_record.discount_total = discount_total
    order_record.total = total

    await session.commit()
    await session.refresh(order_record)

    return OrderResult(
        order_id=order_record.id,
        customer_email=order_record.customer_email,
        promo_code=order_record.promo_code,
        subtotal=order_record.subtotal,
        discount_total=order_record.discount_total,
        total=order_record.total,
        items=tuple(line_items),
    )
