"""Health check endpoints."""

import falcon.asgi


class HealthResource:
    """Health and readiness endpoints."""

    async def on_get(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """GET /v1/health - liveness."""
        resp.media = {"status": "ok"}
        resp.status = falcon.HTTP_200

    async def on_get_ready(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """GET /v1/health/ready - readiness (DB, Keycloak)."""
        resp.media = {"status": "ready"}
        resp.status = falcon.HTTP_200
