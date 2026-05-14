"""Shared pytest fixtures for the bundled sample project."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from tests.support.sample_project import load_sample_module

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(
    (candidate for candidate in CURRENT_FILE.parents if (candidate / "tests").is_dir()),
    CURRENT_FILE.parent.parent,
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform.startswith("win") and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

database_module = load_sample_module("database")
Base = database_module.Base
OrderItemRecord = database_module.OrderItemRecord
OrderRecord = database_module.OrderRecord
ProductRecord = database_module.ProductRecord
create_engine = database_module.create_engine


@pytest_asyncio.fixture()
async def db_engine() -> AsyncEngine:
    engine = create_engine()
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
    except Exception as error:
        await engine.dispose()
        pytest.skip(f"Sample project database is unavailable: {error}")
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
