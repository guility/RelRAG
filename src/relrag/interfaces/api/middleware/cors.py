"""CORS middleware - adds Access-Control-Allow-Origin headers."""

import falcon.asgi


class CORSMiddleware:
    """Middleware that adds CORS headers and handles OPTIONS preflight."""

    def __init__(self, origins: list[str]) -> None:
        self._origins = origins

    def _set_cors_headers(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """Set CORS headers on response."""
        origin = req.get_header("Origin")
        if origin and origin in self._origins:
            resp.set_header("Access-Control-Allow-Origin", origin)
        elif self._origins:
            resp.set_header("Access-Control-Allow-Origin", self._origins[0])
        resp.set_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        resp.set_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        resp.set_header("Access-Control-Max-Age", "86400")

    async def process_request(
        self, req: falcon.asgi.Request, resp: falcon.asgi.Response
    ) -> None:
        """Handle OPTIONS preflight; add CORS headers to all responses."""
        self._set_cors_headers(req, resp)
        if req.method == "OPTIONS":
            resp.status = falcon.HTTP_200
            resp.media = {}
            resp.complete = True

    async def process_response(
        self, req: falcon.asgi.Request, resp: falcon.asgi.Response, resource, req_succeeded
    ) -> None:
        """Ensure CORS headers on response (in case process_request was short-circuited)."""
        self._set_cors_headers(req, resp)

