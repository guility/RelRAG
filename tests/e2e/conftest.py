"""E2E test fixtures. Requires: docker compose up -d (API, frontend, Keycloak)."""

import pytest


@pytest.fixture(scope="session")
def base_url():
    """Frontend base URL."""
    return "http://localhost:8081"


@pytest.fixture(scope="session")
def api_url():
    """API base URL."""
    return "http://localhost:8000"
