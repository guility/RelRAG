"""Pool lifespan middleware - opens pool on startup, closes on shutdown."""

from typing import Any

from psycopg_pool import AsyncConnectionPool


class PoolLifespanMiddleware:
    """Middleware that opens the connection pool on startup and closes on shutdown."""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def process_startup(
        self, scope: dict[str, Any], event: dict[str, Any]
    ) -> None:
        """Open pool when ASGI server starts."""
        await self._pool.open()

    async def process_shutdown(
        self, scope: dict[str, Any], event: dict[str, Any]
    ) -> None:
        """Close pool when ASGI server shuts down."""
        await self._pool.close()
