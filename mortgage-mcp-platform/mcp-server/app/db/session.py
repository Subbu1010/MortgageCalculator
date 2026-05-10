"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """Create (or return) the global async engine and session factory."""
    global _engine, _session_factory
    settings = settings or get_settings()
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url_async,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            echo=False,
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False, autoflush=False)
    assert _session_factory is not None
    return _session_factory


async def dispose_engine() -> None:
    """Dispose pooled connections on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional session (for FastAPI dependency)."""
    factory = init_engine()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory for scripts and background tasks."""
    return init_engine()
