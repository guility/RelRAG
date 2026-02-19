"""CORS middleware: add headers from configured origins and handle OPTIONS preflight."""

import falcon.asgi


class CORSMiddleware:
    """Add CORS headers using configured origins; respond to OPTIONS with 200."""

    def __init__(self, origins: list[str]) -> None:
        self._origins = origins

    def _set_headers(
        self, req: falcon.asgi.Request, resp: falcon.asgi.Response
    ) -> None:
        origin = req.get_header("Origin")
        if origin and origin in self._origins:
            resp.set_header("Access-Control-Allow-Origin", origin)
        elif self._origins:
            resp.set_header("Access-Control-Allow-Origin", self._origins[0])
        resp.set_header(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        )
        resp.set_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type, Accept",
        )
        resp.set_header("Access-Control-Max-Age", "86400")

    async def process_request(
        self, req: falcon.asgi.Request, resp: falcon.asgi.Response
    ) -> None:
        self._set_headers(req, resp)
        if req.method == "OPTIONS":
            resp.status = falcon.HTTP_200
            resp.media = {}
            resp.complete = True

    async def process_response(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        resource: object,
        req_succeeded: bool,
    ) -> None:
        self._set_headers(req, resp)
