"""PostgreSQL property repository implementation."""

from uuid import UUID

from psycopg import AsyncConnection

from relrag.application.ports.repositories.property_repository import (
    PropertySchemaItem,
)
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

    async def list_schema_by_collection(
        self, collection_id: UUID
    ) -> list[PropertySchemaItem]:
        """List distinct property keys and types in collection, with sample values for string/bool."""
        cur = await self._conn.execute(
            """
            SELECT DISTINCT p.key, p.property_type
            FROM property p
            JOIN document d ON d.id = p.document_id
            JOIN pack pk ON pk.document_id = d.id
            JOIN pack_collection pc ON pc.pack_id = pk.id AND pc.collection_id = %s
            WHERE pk.deleted_at IS NULL AND d.deleted_at IS NULL
            ORDER BY p.key
            """,
            (collection_id,),
        )
        rows = await cur.fetchall()
        result: list[PropertySchemaItem] = []
        for key, ptype_str in rows:
            ptype = PropertyType(ptype_str)
            values: list[str] = []
            if ptype in (PropertyType.STRING, PropertyType.BOOL):
                cur2 = await self._conn.execute(
                    """
                    SELECT DISTINCT p.value FROM property p
                    JOIN document d ON d.id = p.document_id
                    JOIN pack pk ON pk.document_id = d.id
                    JOIN pack_collection pc ON pc.pack_id = pk.id AND pc.collection_id = %s
                    WHERE pk.deleted_at IS NULL AND d.deleted_at IS NULL AND p.key = %s
                    ORDER BY p.value
                    LIMIT 500
                    """,
                    (collection_id, key),
                )
                values = [r[0] for r in await cur2.fetchall()]
            result.append(PropertySchemaItem(key=key, property_type=ptype, values=values))
        return result
