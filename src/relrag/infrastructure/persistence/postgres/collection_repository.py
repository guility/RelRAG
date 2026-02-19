"""PostgreSQL collection repository implementation."""

from uuid import UUID

from psycopg import AsyncConnection

from relrag.domain.entities import Collection


class PostgresCollectionRepository:
    """Collection repository implementation."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def get_by_id(
        self, collection_id: UUID, include_deleted: bool = False
    ) -> Collection | None:
        """Get collection by id."""
        q = "SELECT id, configuration_id, created_at, updated_at, deleted_at, name FROM collection WHERE id = %s"
        if not include_deleted:
            q += " AND deleted_at IS NULL"
        cur = await self._conn.execute(q, (collection_id,))
        r = await cur.fetchone()
        if not r:
            return None
        return Collection(
            id=r[0],
            configuration_id=r[1],
            created_at=r[2],
            updated_at=r[3],
            deleted_at=r[4],
            name=r[5],
        )

    async def list(
        self,
        *,
        cursor: str | None = None,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[Collection], str | None]:
        """List collections with cursor pagination."""
        conditions = []
        _params: list[object] = []
        if not include_deleted:
            conditions.append("deleted_at IS NULL")
        if cursor:
            conditions.append("id > %s")
            _params.append(UUID(cursor))
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        params = tuple(_params) + (limit + 1,)
        q = (
            "SELECT id, configuration_id, created_at, updated_at, deleted_at, name "
            f"FROM collection{where} ORDER BY id LIMIT %s"
        )
        cur = await self._conn.execute(q, params)
        rows = await cur.fetchall()
        colls = [
            Collection(
                id=r[0],
                configuration_id=r[1],
                created_at=r[2],
                updated_at=r[3],
                deleted_at=r[4],
                name=r[5],
            )
            for r in rows[:limit]
        ]
        next_cursor = str(rows[limit][0]) if len(rows) > limit else None
        return colls, next_cursor

    async def list_by_subject(
        self,
        subject: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Collection], str | None]:
        """List collections where subject has permission, with cursor pagination."""
        conditions = ["c.deleted_at IS NULL", "p.subject = %s"]
        _params: list[object] = [subject]
        if cursor:
            conditions.append("c.id > %s")
            _params.append(UUID(cursor))
        where = " AND ".join(conditions)
        params = tuple(_params) + (limit + 1,)
        q = (
            "SELECT DISTINCT c.id, c.configuration_id, c.created_at, c.updated_at, c.deleted_at, c.name "
            "FROM collection c JOIN permission p ON p.collection_id = c.id "
            f"WHERE {where} ORDER BY c.id LIMIT %s"
        )
        cur = await self._conn.execute(q, params)
        rows = await cur.fetchall()
        colls = [
            Collection(
                id=r[0],
                configuration_id=r[1],
                created_at=r[2],
                updated_at=r[3],
                deleted_at=r[4],
                name=r[5],
            )
            for r in rows[:limit]
        ]
        next_cursor = str(rows[limit][0]) if len(rows) > limit else None
        return colls, next_cursor

    async def create(self, collection: Collection) -> Collection:
        """Create collection."""
        await self._conn.execute(
            "INSERT INTO collection (id, configuration_id, created_at, updated_at, deleted_at, name) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                collection.id,
                collection.configuration_id,
                collection.created_at,
                collection.updated_at,
                collection.deleted_at,
                collection.name,
            ),
        )
        return collection

    async def update(self, collection: Collection) -> None:
        """Update collection."""
        await self._conn.execute(
            "UPDATE collection SET configuration_id=%s, updated_at=%s, name=%s WHERE id=%s",
            (collection.configuration_id, collection.updated_at, collection.name, collection.id),
        )

    async def soft_delete(self, collection_id: UUID) -> None:
        """Soft delete collection."""
        await self._conn.execute(
            "UPDATE collection SET deleted_at = NOW() WHERE id = %s",
            (collection_id,),
        )

    async def hard_delete(self, collection_id: UUID) -> None:
        """Hard delete collection."""
        await self._conn.execute(
            "DELETE FROM collection WHERE id = %s",
            (collection_id,),
        )
