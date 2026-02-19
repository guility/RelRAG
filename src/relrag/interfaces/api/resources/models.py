"""Models API - list available embedding models from embedding API."""

import json
import ssl
from urllib.request import Request, urlopen

import falcon.asgi

from relrag.config import get_settings

# Default dimensions for known models (fallback when API doesn't provide)
DEFAULT_MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "evraz-gte-qwen2-embed": 1024,
}


def _fetch_models_sync(settings) -> list[dict]:
    """Fetch models from embedding API (sync, run in executor)."""
    models: list[dict] = []
    url = f"{settings.embedding_api_url.rstrip('/')}/models"
    headers = {"Accept": "application/json"}
    if settings.embedding_api_key:
        headers["Authorization"] = f"Bearer {settings.embedding_api_key}"
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10, context=ssl.create_default_context()) as r:
            data = json.loads(r.read().decode())
            for m in data.get("data", []):
                mid = m.get("id", "")
                if "embed" in mid.lower():
                    dim = m.get("dimensions") or DEFAULT_MODEL_DIMENSIONS.get(mid, 1536)
                    models.append({"id": mid, "dimensions": dim})
    except Exception:
        pass
    return models


class ModelsResource:
    """GET /v1/models - list embedding models from embedding API."""

    async def on_get(self, req, resp) -> None:
        """Return available embedding models with dimensions."""
        import asyncio

        settings = get_settings()
        loop = asyncio.get_event_loop()
        models = await loop.run_in_executor(None, _fetch_models_sync, settings)

        if not models:
            for mid, dim in DEFAULT_MODEL_DIMENSIONS.items():
                models.append({"id": mid, "dimensions": dim})
            if settings.embedding_model and not any(
                m["id"] == settings.embedding_model for m in models
            ):
                models.insert(
                    0,
                    {
                        "id": settings.embedding_model,
                        "dimensions": DEFAULT_MODEL_DIMENSIONS.get(
                            settings.embedding_model, 1536
                        ),
                    },
                )

        resp.media = {"items": models}
        resp.status = falcon.HTTP_200
