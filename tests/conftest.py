"""Shared pytest fixtures for the bundled sample project."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import time
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

if (
    sys.platform.startswith("win")
    and sys.version_info < (3, 14)
    and hasattr(asyncio, "WindowsSelectorEventLoopPolicy")
):
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
SAMPLE_DB_CONTAINER_NAME = "speculast-test-postgres"


def _run_docker_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _cleanup_sample_database_container() -> None:
    _run_docker_command("rm", "-f", SAMPLE_DB_CONTAINER_NAME)


def _start_sample_database_container() -> str | None:
    if os.getenv("DEMO_SHOP_DATABASE_URL"):
        return "automatic bootstrap is disabled when DEMO_SHOP_DATABASE_URL is set"

    if shutil.which("docker") is None:
        return "docker is unavailable in the current environment"

    _cleanup_sample_database_container()
    result = _run_docker_command(
        "run",
        "-d",
        "--name",
        SAMPLE_DB_CONTAINER_NAME,
        "--health-cmd",
        "pg_isready -U app -d app",
        "--health-interval",
        "2s",
        "--health-timeout",
        "5s",
        "--health-retries",
        "30",
        "-e",
        "POSTGRES_USER=app",
        "-e",
        "POSTGRES_PASSWORD=app",
        "-e",
        "POSTGRES_DB=app",
        "-p",
        "55432:5432",
        "postgres:16-alpine",
    )
    if result.returncode == 0:
        return None

    message = result.stderr.strip() or result.stdout.strip()
    return message or "docker failed to start the sample PostgreSQL container"


async def _reset_sample_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session")
def sample_database_service() -> dict[str, bool]:
    state = {"launched": False}
    try:
        yield state
    finally:
        if state["launched"]:
            _cleanup_sample_database_container()


@pytest_asyncio.fixture()
async def db_engine(sample_database_service: dict[str, bool]) -> AsyncEngine:
    engine = create_engine()
    try:
        await _reset_sample_database(engine)
    except Exception as error:
        await engine.dispose()
        bootstrap_error = None
        if not sample_database_service["launched"]:
            bootstrap_error = _start_sample_database_container()
            if bootstrap_error is None:
                sample_database_service["launched"] = True

        if sample_database_service["launched"]:
            last_error = error
            for _ in range(30):
                await asyncio.sleep(2)
                engine = create_engine()
                try:
                    await _reset_sample_database(engine)
                    break
                except Exception as retry_error:
                    last_error = retry_error
                    await engine.dispose()
            else:
                pytest.skip(
                    f"Sample project database is unavailable after automatic bootstrap: {last_error}"
                )
        else:
            suffix = f"; bootstrap failed: {bootstrap_error}" if bootstrap_error else ""
            pytest.skip(f"Sample project database is unavailable: {error}{suffix}")
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
