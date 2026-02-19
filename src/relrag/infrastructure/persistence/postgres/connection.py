"""PostgreSQL async connection pool."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg_pool import AsyncConnectionPool


def create_pool(conninfo: str, min_size: int = 2, max_size: int = 10) -> AsyncConnectionPool:
    """Create async connection pool.

    Pool is created with open=False. Caller must call await pool.open()
    before use (e.g. via PoolLifespanMiddleware in ASGI lifespan).
    """
    return AsyncConnectionPool(
        conninfo=conninfo,
        min_size=min_size,
        max_size=max_size,
        open=False,
    )


@asynccontextmanager
async def get_connection(pool: AsyncConnectionPool) -> AsyncIterator:
    """Get connection from pool (context manager)."""
    async with pool.connection() as conn:
        yield conn
