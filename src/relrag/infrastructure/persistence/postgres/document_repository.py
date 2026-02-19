"""PostgreSQL document repository implementation."""

from uuid import UUID

from psycopg import AsyncConnection

from relrag.domain.entities import Document


class PostgresDocumentRepository:
    """Document repository implementation."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def get_by_id(self, document_id: UUID, include_deleted: bool = False) -> Document | None:
        """Get document by id."""
        q = "SELECT id, content, source_hash, created_at, updated_at, deleted_at FROM document WHERE id = %s"
        if not include_deleted:
            q += " AND deleted_at IS NULL"
        cur = await self._conn.execute(q, (document_id,))
        r = await cur.fetchone()
        if not r:
            return None
        return Document(
            id=r[0],
            content=r[1],
            source_hash=r[2],
            created_at=r[3],
            updated_at=r[4],
            deleted_at=r[5],
        )

    async def get_by_source_hash(self, source_hash: bytes) -> Document | None:
        """Get document by source hash."""
        cur = await self._conn.execute(
            "SELECT id, content, source_hash, created_at, updated_at, deleted_at "
            "FROM document WHERE source_hash = %s AND deleted_at IS NULL",
            (source_hash,),
        )
        r = await cur.fetchone()
        if not r:
            return None
        return Document(
            id=r[0],
            content=r[1],
            source_hash=r[2],
            created_at=r[3],
            updated_at=r[4],
            deleted_at=r[5],
        )

    async def list(
        self,
        *,
        cursor: str | None = None,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[Document], str | None]:
        """List documents with cursor pagination."""
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
            "SELECT id, content, source_hash, created_at, updated_at, deleted_at "
            f"FROM document{where} ORDER BY id LIMIT %s"
        )
        cur = await self._conn.execute(q, params)
        rows = await cur.fetchall()
        docs = [
            Document(
                id=r[0],
                content=r[1],
                source_hash=r[2],
                created_at=r[3],
                updated_at=r[4],
                deleted_at=r[5],
            )
            for r in rows[:limit]
        ]
        next_cursor = str(rows[limit][0]) if len(rows) > limit else None
        return docs, next_cursor

    async def create(self, document: Document) -> Document:
        """Create document."""
        await self._conn.execute(
            "INSERT INTO document (id, content, source_hash, created_at, updated_at, deleted_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                document.id,
                document.content,
                document.source_hash,
                document.created_at,
                document.updated_at,
                document.deleted_at,
            ),
        )
        return document

    async def update(self, document: Document) -> Document:
        """Update document."""
        await self._conn.execute(
            "UPDATE document SET content=%s, source_hash=%s, updated_at=%s WHERE id=%s",
            (document.content, document.source_hash, document.updated_at, document.id),
        )
        return document

    async def soft_delete(self, document_id: UUID) -> None:
        """Soft delete document."""
        await self._conn.execute(
            "UPDATE document SET deleted_at = NOW() WHERE id = %s",
            (document_id,),
        )

    async def hard_delete(self, document_id: UUID) -> None:
        """Hard delete document."""
        await self._conn.execute("DELETE FROM document WHERE id = %s", (document_id,))
