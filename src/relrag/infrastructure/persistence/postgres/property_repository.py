"""PostgreSQL property repository implementation."""

from uuid import UUID

from psycopg import AsyncConnection

from relrag.domain.entities import Property
from relrag.domain.value_objects import PropertyType


class PostgresPropertyRepository:
    """Property repository implementation."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def list_by_document(self, document_id: UUID) -> list[Property]:
        """List properties for document."""
        cur = await self._conn.execute(
            "SELECT document_id, key, value, property_type FROM property WHERE document_id = %s",
            (document_id,),
        )
        rows = await cur.fetchall()
        return [
            Property(
                document_id=r[0],
                key=r[1],
                value=r[2],
                property_type=PropertyType(r[3]),
            )
            for r in rows
        ]

    async def create_batch(self, properties: list[Property]) -> None:
        """Create properties in batch."""
        for p in properties:
            await self._conn.execute(
                "INSERT INTO property (document_id, key, value, property_type) VALUES (%s, %s, %s, %s)",
                (p.document_id, p.key, p.value, p.property_type.value),
            )

    async def delete_by_document(self, document_id: UUID) -> None:
        """Delete all properties for document."""
        await self._conn.execute(
            "DELETE FROM property WHERE document_id = %s",
            (document_id,),
        )
