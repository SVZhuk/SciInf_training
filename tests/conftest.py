"""Shared fixtures: a per-test Postgres transaction, rolled back after each test."""

import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.models import Base
from app.repository import SqlAlchemySampleRepository

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5433/lab_samples_test"
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def ensure_test_db() -> None:
    subprocess.run(
        ["docker", "compose", "up", "-d", "test_db", "--wait"],
        cwd=REPO_ROOT,
        check=True,
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if exitstatus == 0:
        subprocess.run(["docker", "compose", "stop", "test_db"], cwd=REPO_ROOT, check=True)


@pytest_asyncio.fixture(scope="session")
async def test_engine(ensure_test_db: None) -> AsyncIterator[AsyncEngine]:
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
