"""Embedding provider port - OpenAI compatible API."""

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Port for generating text embeddings."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
