"""CORS middleware: add headers to all responses and handle OPTIONS preflight."""

import falcon.asgi


class CORSMiddleware:
    """Add CORS headers to every response and respond to OPTIONS with 200."""

    def _set_headers(self, resp: falcon.asgi.Response) -> None:
        resp.set_header("Access-Control-Allow-Origin", "*")
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
        self._set_headers(resp)
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
        self._set_headers(resp)
