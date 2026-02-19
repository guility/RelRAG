"""Configuration API resources."""

from uuid import uuid4

import falcon.asgi

from relrag.domain.entities import Configuration
from relrag.domain.value_objects import ChunkingStrategy


class ConfigurationsResource:
    """GET/POST /v1/configurations - list and create configurations."""

    def __init__(self, unit_of_work_factory: type) -> None:
        self._uow_factory = unit_of_work_factory

    async def on_get(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """List configurations with cursor pagination."""
        cursor = req.get_param("cursor")
        limit = req.get_param_as_int("limit") or 20
        limit = min(max(limit, 1), 100)

        async with self._uow_factory() as uow:
            configs, next_cursor = await uow.configurations.list(
                cursor=cursor,
                limit=limit,
            )

        resp.media = {
            "items": [
                {
                    "id": str(c.id),
                    "chunking_strategy": c.chunking_strategy.value,
                    "embedding_model": c.embedding_model,
                    "embedding_dimensions": c.embedding_dimensions,
                    "chunk_size": c.chunk_size,
                    "chunk_overlap": c.chunk_overlap,
                }
                for c in configs
            ],
            "next_cursor": next_cursor,
        }
        resp.status = falcon.HTTP_200

    async def on_post(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """Create configuration for collections."""
        try:
            body = await req.get_media()
            chunking_strategy = ChunkingStrategy(body.get("chunking_strategy", "recursive"))
            embedding_model = body.get("embedding_model", "text-embedding-3-small")
            embedding_dimensions = body.get("embedding_dimensions", 1536)
            chunk_size = body.get("chunk_size", 512)
            chunk_overlap = body.get("chunk_overlap", 50)
        except (KeyError, ValueError) as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": str(e)}
            return

        config = Configuration(
            id=uuid4(),
            chunking_strategy=chunking_strategy,
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimensions,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        async with self._uow_factory() as uow:
            await uow.configurations.create(config)

        resp.media = {
            "id": str(config.id),
            "chunking_strategy": config.chunking_strategy.value,
            "embedding_model": config.embedding_model,
            "embedding_dimensions": config.embedding_dimensions,
            "chunk_size": config.chunk_size,
            "chunk_overlap": config.chunk_overlap,
        }
        resp.status = falcon.HTTP_201
