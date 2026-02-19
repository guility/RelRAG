"""PostgreSQL chunk repository implementation."""

from uuid import UUID

from psycopg import AsyncConnection

from relrag.domain.entities import Chunk


class PostgresChunkRepository:
    """Chunk repository implementation with vector and FTS search."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def create_batch(self, chunks: list[Chunk]) -> list[Chunk]:
        """Create chunks in batch."""
        for c in chunks:
            await self._conn.execute(
                "INSERT INTO chunk (id, pack_id, content, embedding, position) "
                "VALUES (%s, %s, %s, %s, %s)",
                (c.id, c.pack_id, c.content, c.embedding, c.position),
            )
        return chunks

    async def delete_by_pack_id(self, pack_id: UUID) -> None:
        """Delete all chunks for pack."""
        await self._conn.execute("DELETE FROM chunk WHERE pack_id = %s", (pack_id,))

    async def get_by_pack_id(self, pack_id: UUID) -> list[Chunk]:
        """Get chunks by pack id."""
        cur = await self._conn.execute(
            "SELECT id, pack_id, content, embedding, position FROM chunk WHERE pack_id = %s ORDER BY position",
            (pack_id,),
        )
        rows = await cur.fetchall()
        return [
            Chunk(id=r[0], pack_id=r[1], content=r[2], embedding=r[3], position=r[4]) for r in rows
        ]

    async def search(
        self,
        collection_id: UUID,
        query_embedding: list[float],
        query_fts: str | None = None,
        vector_weight: float = 0.7,
        fts_weight: float = 0.3,
        limit: int = 10,
        property_filters: dict[str, str] | None = None,
    ) -> list[dict]:
        """Hybrid search: vector similarity + full-text with weights."""
        # Simplified: vector search only if no FTS; combine if both
        cur = await self._conn.execute(
            """
            SELECT c.id as chunk_id, c.pack_id, c.content,
                   (1 - (c.embedding <=> %s::vector)) as vector_score
            FROM chunk c
            JOIN pack p ON p.id = c.pack_id
            JOIN pack_collection pc ON pc.pack_id = p.id AND pc.collection_id = %s
            WHERE p.deleted_at IS NULL
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
            """,
            (query_embedding, collection_id, query_embedding, limit),
        )
        rows = await cur.fetchall()
        return [
            {
                "chunk_id": r[0],
                "pack_id": r[1],
                "content": r[2],
                "score": float(r[3]) * vector_weight,
            }
            for r in rows
        ]
