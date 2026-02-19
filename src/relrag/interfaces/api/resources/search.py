"""Search API resource."""

from uuid import UUID

import falcon.asgi

from relrag.application.use_cases.search.hybrid_search import (
    HybridSearchInput,
    HybridSearchUseCase,
)
from relrag.domain.exceptions import PermissionDenied


class SearchResource:
    """POST /v1/collections/{id}/search - hybrid search."""

    def __init__(self, hybrid_search: HybridSearchUseCase) -> None:
        self._hybrid_search = hybrid_search

    async def on_post(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        collection_id: str,
    ) -> None:
        """Execute hybrid search."""
        user = getattr(req.context, "user", None)
        if not user:
            resp.status = falcon.HTTP_401
            resp.media = {"error": "Unauthorized"}
            return

        try:
            body = await req.get_media()
            query = body.get("query", "")
            vector_weight = body.get("vector_weight", 0.7)
            fts_weight = body.get("fts_weight", 0.3)
            limit = body.get("limit", 10)
            filters = body.get("filters")
        except Exception:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "Invalid request body"}
            return

        try:
            coll_id = UUID(collection_id)
        except ValueError:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "Invalid collection ID"}
            return

        try:
            results = await self._hybrid_search.execute(
                user.user_id,
                HybridSearchInput(
                    collection_id=coll_id,
                    query=query,
                    vector_weight=vector_weight,
                    fts_weight=fts_weight,
                    limit=limit,
                    filters=filters if isinstance(filters, dict) else None,
                ),
            )
            resp.media = {
                "results": [
                    {
                        "chunk_id": str(r.chunk_id),
                        "pack_id": str(r.pack_id),
                        "document_id": str(r.document_id),
                        "content": r.content,
                        "vector_score": round(r.vector_score, 6),
                        "fts_score": round(r.fts_score, 6),
                        "score": round(r.score, 6),
                        "document_title": r.document_title,
                        "metadata": r.metadata,
                    }
                    for r in results
                ],
            }
            resp.status = falcon.HTTP_200
        except PermissionDenied:
            resp.status = falcon.HTTP_403
            resp.media = {"error": "Permission denied"}
