"""SQLAlchemy models and helpers for the demo shop."""

from __future__ import annotations

import os
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


DEFAULT_DATABASE_URL = "postgresql+asyncpg://app:app@127.0.0.1:55432/app"


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base."""


class ProductRecord(Base):
    """Catalog inventory row."""

    __tablename__ = "shop_products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column()


class OrderRecord(Base):
    """Order header row."""

    __tablename__ = "shop_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_email: Mapped[str] = mapped_column(String(255), index=True)
    promo_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    items: Mapped[list["OrderItemRecord"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItemRecord(Base):
    """Order line row."""

    __tablename__ = "shop_order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("shop_orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("shop_products.id"))
    sku: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[int] = mapped_column()
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[OrderRecord] = relationship(back_populates="items")


def resolve_database_url() -> str:
    """Return the connection string used by integration tests and services."""

    return os.getenv("DEMO_SHOP_DATABASE_URL", DEFAULT_DATABASE_URL)


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """Build an async SQLAlchemy engine."""

    return create_async_engine(
        database_url or resolve_database_url(),
        future=True,
        connect_args={"ssl": False},
    )


def create_session_factory(database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    """Build a reusable async session factory."""

    return async_sessionmaker(
        create_engine(database_url),
        class_=AsyncSession,
        expire_on_commit=False,
    )
