"""PostgreSQL configuration repository implementation."""

from uuid import UUID

from psycopg import AsyncConnection

from relrag.domain.entities import Configuration
from relrag.domain.value_objects import ChunkingStrategy


class PostgresConfigurationRepository:
    """Configuration repository implementation."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def get_by_id(self, configuration_id: UUID) -> Configuration | None:
        """Get configuration by id."""
        cur = await self._conn.execute(
            "SELECT id, chunking_strategy, embedding_model, embedding_dimensions, "
            "chunk_size, chunk_overlap, name FROM configuration WHERE id = %s",
            (configuration_id,),
        )
        r = await cur.fetchone()
        if not r:
            return None
        return Configuration(
            id=r[0],
            chunking_strategy=ChunkingStrategy(r[1]),
            embedding_model=r[2],
            embedding_dimensions=r[3],
            chunk_size=r[4],
            chunk_overlap=r[5],
            name=r[6],
        )

    async def list(
        self,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Configuration], str | None]:
        """List configurations with cursor pagination."""
        conditions = []
        _params: list[object] = []
        if cursor:
            conditions.append("id > %s")
            _params.append(UUID(cursor))
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        params = tuple(_params) + (limit + 1,)
        q = (
            "SELECT id, chunking_strategy, embedding_model, embedding_dimensions, "
            f"chunk_size, chunk_overlap, name FROM configuration{where} ORDER BY id LIMIT %s"
        )
        cur = await self._conn.execute(q, params)
        rows = await cur.fetchall()
        configs = [
            Configuration(
                id=r[0],
                chunking_strategy=ChunkingStrategy(r[1]),
                embedding_model=r[2],
                embedding_dimensions=r[3],
                chunk_size=r[4],
                chunk_overlap=r[5],
                name=r[6],
            )
            for r in rows[:limit]
        ]
        next_cursor = str(rows[limit][0]) if len(rows) > limit else None
        return configs, next_cursor

    async def get_by_collection_id(self, collection_id: UUID) -> Configuration | None:
        """Get configuration for collection."""
        cur = await self._conn.execute(
            "SELECT c.id, c.chunking_strategy, c.embedding_model, c.embedding_dimensions, "
            "c.chunk_size, c.chunk_overlap, c.name FROM configuration c "
            "JOIN collection col ON col.configuration_id = c.id WHERE col.id = %s",
            (collection_id,),
        )
        r = await cur.fetchone()
        if not r:
            return None
        return Configuration(
            id=r[0],
            chunking_strategy=ChunkingStrategy(r[1]),
            embedding_model=r[2],
            embedding_dimensions=r[3],
            chunk_size=r[4],
            chunk_overlap=r[5],
            name=r[6],
        )

    async def create(self, configuration: Configuration) -> Configuration:
        """Create configuration."""
        await self._conn.execute(
            "INSERT INTO configuration (id, chunking_strategy, embedding_model, "
            "embedding_dimensions, chunk_size, chunk_overlap, name) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                configuration.id,
                configuration.chunking_strategy.value,
                configuration.embedding_model,
                configuration.embedding_dimensions,
                configuration.chunk_size,
                configuration.chunk_overlap,
                configuration.name,
            ),
        )
        return configuration
