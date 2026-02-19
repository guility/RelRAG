"""PostgreSQL pack repository implementation."""

from uuid import UUID

from psycopg import AsyncConnection

from relrag.domain.entities import Pack


class PostgresPackRepository:
    """Pack repository implementation."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def get_by_id(self, pack_id: UUID, include_deleted: bool = False) -> Pack | None:
        """Get pack by id."""
        q = "SELECT id, document_id, created_at, updated_at, deleted_at FROM pack WHERE id = %s"
        if not include_deleted:
            q += " AND deleted_at IS NULL"
        cur = await self._conn.execute(q, (pack_id,))
        r = await cur.fetchone()
        if not r:
            return None
        return Pack(
            id=r[0],
            document_id=r[1],
            created_at=r[2],
            updated_at=r[3],
            deleted_at=r[4],
        )

    async def list(
        self,
        *,
        document_id: UUID | None = None,
        collection_id: UUID | None = None,
        cursor: str | None = None,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[Pack], str | None]:
        """List packs with optional filters."""
        conditions = []
        _params: list[object] = []
        if not include_deleted:
            conditions.append("p.deleted_at IS NULL")
        if document_id:
            conditions.append("p.document_id = %s")
            _params.append(document_id)
        if collection_id:
            conditions.append(
                "EXISTS (SELECT 1 FROM pack_collection pc "
                "WHERE pc.pack_id = p.id AND pc.collection_id = %s)"
            )
            _params.append(collection_id)
        if cursor:
            conditions.append("p.id > %s")
            _params.append(UUID(cursor))
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        params = tuple(_params) + (limit + 1,)
        q = (
            "SELECT p.id, p.document_id, p.created_at, p.updated_at, p.deleted_at "
            f"FROM pack p{where} ORDER BY p.id LIMIT %s"
        )
        cur = await self._conn.execute(q, params)
        rows = await cur.fetchall()
        packs = [
            Pack(
                id=r[0],
                document_id=r[1],
                created_at=r[2],
                updated_at=r[3],
                deleted_at=r[4],
            )
            for r in rows[:limit]
        ]
        next_cursor = str(rows[limit][0]) if len(rows) > limit else None
        return packs, next_cursor

    async def create(self, pack: Pack) -> Pack:
        """Create pack."""
        await self._conn.execute(
            "INSERT INTO pack (id, document_id, created_at, updated_at, deleted_at) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                pack.id,
                pack.document_id,
                pack.created_at,
                pack.updated_at,
                pack.deleted_at,
            ),
        )
        return pack

    async def update(self, pack: Pack) -> None:
        """Update pack."""
        await self._conn.execute(
            "UPDATE pack SET updated_at=%s, deleted_at=%s WHERE id=%s",
            (pack.updated_at, pack.deleted_at, pack.id),
        )

    async def soft_delete(self, pack_id: UUID) -> None:
        """Soft delete pack."""
        await self._conn.execute(
            "UPDATE pack SET deleted_at = NOW() WHERE id = %s",
            (pack_id,),
        )

    async def hard_delete(self, pack_id: UUID) -> None:
        """Hard delete pack."""
        await self._conn.execute("DELETE FROM pack WHERE id = %s", (pack_id,))

    async def add_to_collection(self, pack_id: UUID, collection_id: UUID) -> None:
        """Add pack to collection (M:N)."""
        await self._conn.execute(
            "INSERT INTO pack_collection (pack_id, collection_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (pack_id, collection_id),
        )
