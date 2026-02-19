"""OpenAI-compatible embedding provider."""

from openai import AsyncOpenAI


class OpenAIEmbeddingProvider:
    """Embedding provider using OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
    ) -> None:
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [d.embedding for d in response.data]
