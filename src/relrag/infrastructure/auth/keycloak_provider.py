"""Keycloak OIDC provider for JWT validation."""

from dataclasses import dataclass

from keycloak import KeycloakOpenID


@dataclass
class OIDCUser:
    """Authenticated user from OIDC token."""

    user_id: str
    email: str | None
    username: str | None
    realm_roles: list[str]


class KeycloakProvider:
    """Keycloak OIDC - validates JWT and extracts user info."""

    def __init__(
        self,
        server_url: str,
        realm: str,
        client_id: str,
        client_secret: str = "",
    ) -> None:
        self._keycloak = KeycloakOpenID(
            server_url=server_url,
            realm_name=realm,
            client_id=client_id,
            client_secret_key=client_secret,
        )

    def decode_token(self, token: str) -> OIDCUser | None:
        """Decode and validate JWT, return user info or None."""
        try:
            token_info = self._keycloak.introspect(token)
            if not token_info.get("active"):
                return None
            return OIDCUser(
                user_id=token_info.get("sub", ""),
                email=token_info.get("email"),
                username=token_info.get("preferred_username"),
                realm_roles=token_info.get("realm_access", {}).get("roles", []),
            )
        except Exception:
            return None
