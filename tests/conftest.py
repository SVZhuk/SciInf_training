"""Shared fixtures: a per-test Postgres transaction, rolled back after each test."""

import os
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.models import Base
from app.repository import SqlAlchemySampleRepository

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5433/lab_samples_test"
)


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def sample_repository(
    test_engine: AsyncEngine,
) -> AsyncIterator[SqlAlchemySampleRepository]:
    async with test_engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield SqlAlchemySampleRepository(session)
        finally:
            await session.close()
            await conn.rollback()
