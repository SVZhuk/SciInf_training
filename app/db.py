"""Async engine/session lifecycle: FastAPI lifespan + per-request session."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=settings.db_echo, pool_pre_ping=True)
    app.state.sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield
    finally:
        await engine.dispose()


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session: AsyncSession = request.app.state.sessionmaker()
    try:
        yield session
    except BaseException:
        await session.rollback()
        raise
    else:
        await session.commit()
    finally:
        await session.close()
