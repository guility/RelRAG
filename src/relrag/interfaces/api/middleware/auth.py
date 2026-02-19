"""Auth middleware - extracts user from JWT or allows anonymous."""

from dataclasses import dataclass

import falcon.asgi


@dataclass
class RequestUser:
    """User from request context."""

    user_id: str
    email: str | None = None
    username: str | None = None


class AuthMiddleware:
    """Middleware that validates JWT and sets req.context.user."""

    def __init__(self, keycloak_provider=None) -> None:
        self._keycloak = keycloak_provider

    async def process_request(
        self, req: falcon.asgi.Request, resp: falcon.asgi.Response, resource, params
    ) -> None:
        """Extract user from Authorization header."""
        auth = req.get_header("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:]
            if self._keycloak:
                user = self._keycloak.decode_token(token)
                if user:
                    req.context.user = RequestUser(
                        user_id=user.user_id,
                        email=user.email,
                        username=user.username,
                    )
                    return
            req.context.user = None
        else:
            req.context.user = RequestUser(user_id="anonymous")
