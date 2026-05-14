"""Shared pytest fixtures for demo_shop."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform.startswith("win") and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from demo_shop.database import Base, OrderItemRecord, OrderRecord, ProductRecord, create_engine


@pytest_asyncio.fixture()
async def db_engine() -> AsyncEngine:
    engine = create_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine: AsyncEngine) -> AsyncSession:
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                await session.rollback()
            await session.close()


@pytest_asyncio.fixture()
async def seeded_catalog(db_session: AsyncSession) -> None:
    await db_session.execute(delete(OrderItemRecord))
    await db_session.execute(delete(OrderRecord))
    await db_session.execute(delete(ProductRecord))
    db_session.add_all(
        [
            ProductRecord(
                sku="SKU-RED-CHAIR",
                title="Red Lounge Chair",
                unit_price="199.00",
                stock=5,
            ),
            ProductRecord(
                sku="SKU-OAK-DESK",
                title="Oak Writing Desk",
                unit_price="800.00",
                stock=2,
            ),
        ]
    )
    await db_session.commit()
