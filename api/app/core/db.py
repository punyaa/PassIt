from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    if settings.database_null_pool:
        return create_async_engine(settings.database_url, poolclass=NullPool)
    return create_async_engine(
        settings.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request. Handlers commit explicitly."""
    async with get_sessionmaker()() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
