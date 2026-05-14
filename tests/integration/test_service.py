"""Sample-project integration checks for the bundled service layer."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.sample_project import load_sample_module


database_module = load_sample_module("database")
models_module = load_sample_module("models")
service_module = load_sample_module("service")

OrderItemRecord = database_module.OrderItemRecord
OrderRecord = database_module.OrderRecord
ProductRecord = database_module.ProductRecord
OrderCreateRequest = models_module.OrderCreateRequest
OrderItemRequest = models_module.OrderItemRequest
create_order = service_module.create_order


@pytest.mark.asyncio
async def test_create_order_persists_in_db(
    db_session: AsyncSession,
    seeded_catalog: None,
) -> None:
    payload = OrderCreateRequest(
        customer_email="buyer@example.com",
        promo_code="WELCOME10",
        items=(
            OrderItemRequest(sku="SKU-RED-CHAIR", quantity=1),
            OrderItemRequest(sku="SKU-OAK-DESK", quantity=1),
        ),
    )

    result = await create_order(db_session, payload)

    stored_order = (
        await db_session.execute(
            select(OrderRecord).where(OrderRecord.id == result.order_id)
        )
    ).scalar_one()
    item_count = (
        await db_session.execute(
            select(func.count(OrderItemRecord.id)).where(OrderItemRecord.order_id == result.order_id)
        )
    ).scalar_one()

    assert stored_order.customer_email == "buyer@example.com"
    assert result.subtotal == Decimal("999.00")
    assert result.discount_total == Decimal("99.90")
    assert result.total == Decimal("899.10")
    assert item_count == 2


@pytest.mark.asyncio
async def test_create_order_decrements_stock(
    db_session: AsyncSession,
    seeded_catalog: None,
) -> None:
    payload = OrderCreateRequest(
        customer_email="repeat@example.com",
        promo_code=None,
        items=(OrderItemRequest(sku="SKU-RED-CHAIR", quantity=2),),
    )

    result = await create_order(db_session, payload)

    updated_product = (
        await db_session.execute(
            select(ProductRecord).where(ProductRecord.sku == "SKU-RED-CHAIR")
        )
    ).scalar_one()

    assert result.total == Decimal("398.00")
    assert updated_product.stock == 3


