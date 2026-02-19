"""PostgreSQL chunk repository implementation."""

from uuid import UUID

from psycopg import AsyncConnection

from relrag.domain.entities import Chunk


def _build_property_filter_conditions(
    property_filters: dict[str, object],
) -> tuple[list[str], list[object]]:
    """Build SQL AND conditions and params for property filters. Returns (conditions, params)."""
    conditions: list[str] = []
    params: list[object] = []
    for i, (key, spec) in enumerate(property_filters.items()):
        if spec is None:
            continue
        if isinstance(spec, (bool, int, float, str)):
            spec = {"eq": spec}
        if not isinstance(spec, dict):
            continue
        alias = f"pr{i}"
        if "one_of" in spec:
            vals = spec["one_of"]
            if isinstance(vals, list) and vals:
                conditions.append(
                    f"EXISTS (SELECT 1 FROM property {alias} "
                    f"WHERE {alias}.document_id = p.document_id "
                    f"AND {alias}.key = %s AND {alias}.value = ANY(%s))"
                )
                params.append(key)
                params.append(vals)
        elif "gte" in spec or "lte" in spec:
            gte = spec.get("gte")
            lte = spec.get("lte")
            try:
                if gte is not None:
                    float(gte)
                if lte is not None:
                    float(lte)
                cast = "::numeric"
            except (TypeError, ValueError):
                cast = "::date"
            if gte is not None and lte is not None:
                conditions.append(
                    f"EXISTS (SELECT 1 FROM property {alias} "
                    f"WHERE {alias}.document_id = p.document_id "
                    f"AND {alias}.key = %s "
                    f"AND {alias}.value{cast} >= %s AND {alias}.value{cast} <= %s)"
                )
                params.extend([key, gte, lte])
            elif gte is not None:
                conditions.append(
                    f"EXISTS (SELECT 1 FROM property {alias} "
                    f"WHERE {alias}.document_id = p.document_id "
                    f"AND {alias}.key = %s AND {alias}.value{cast} >= %s)"
                )
                params.extend([key, gte])
            elif lte is not None:
                conditions.append(
                    f"EXISTS (SELECT 1 FROM property {alias} "
                    f"WHERE {alias}.document_id = p.document_id "
                    f"AND {alias}.key = %s AND {alias}.value{cast} <= %s)"
                )
                params.extend([key, lte])
        elif "eq" in spec:
            val = spec["eq"]
            str_val = "true" if val is True else "false" if val is False else str(val)
            conditions.append(
                f"EXISTS (SELECT 1 FROM property {alias} "
                f"WHERE {alias}.document_id = p.document_id "
                f"AND {alias}.key = %s AND {alias}.value = %s)"
            )
            params.extend([key, str_val])
    return conditions, params


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
        property_filters: dict[str, object] | None = None,
    ) -> list[dict]:
        """Hybrid search with optional property filters."""
        where_extra = ""
        full_params: list[object] = []
        if property_filters:
            conds, filter_params = _build_property_filter_conditions(property_filters)
            if conds:
                where_extra = " AND " + " AND ".join(conds)
                full_params.extend(filter_params)
        query_fts_param = query_fts.strip() if (query_fts and isinstance(query_fts, str)) else ""
        full_params = [query_embedding, query_fts_param, query_fts_param, collection_id] + full_params + [vector_weight, fts_weight, vector_weight, fts_weight, limit]
        cur = await self._conn.execute(
            f"""
            WITH scored AS (
                SELECT c.id AS chunk_id, c.pack_id, p.document_id, c.content,
                       (1 - (c.embedding <=> %s::vector)) AS vector_score,
                       CASE WHEN %s != '' THEN ts_rank(to_tsvector('simple', c.content), plainto_tsquery('simple', %s)) ELSE 0 END AS fts_score,
                       pr.doc_props
                FROM chunk c
                JOIN pack p ON p.id = c.pack_id
                JOIN pack_collection pc ON pc.pack_id = p.id AND pc.collection_id = %s
                LEFT JOIN LATERAL (SELECT json_object_agg(key, value) AS doc_props FROM property WHERE document_id = p.document_id) pr ON true
                WHERE p.deleted_at IS NULL{where_extra}
            )
            SELECT chunk_id, pack_id, document_id, content, vector_score, fts_score,
                   (vector_score * %s + fts_score * %s) AS score, doc_props
            FROM scored
            ORDER BY (vector_score * %s + fts_score * %s) DESC
            LIMIT %s
            """,
            full_params,
        )
        rows = await cur.fetchall()
        return [
            {
                "chunk_id": r[0],
                "pack_id": r[1],
                "document_id": r[2],
                "content": r[3],
                "vector_score": float(r[4]),
                "fts_score": float(r[5]),
                "score": float(r[6]),
                "doc_props": r[7],
            }
            for r in rows
        ]
