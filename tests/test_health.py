"""Health endpoint tests."""

import pytest
from falcon.asgi import App
from falcon.testing import TestClient

from relrag.interfaces.api.resources.health import HealthResource


@pytest.fixture
def client() -> TestClient:
    """Create test client with health endpoints."""
    app = App()
    health = HealthResource()
    app.add_route("/v1/health", health)
    app.add_route("/v1/health/ready", health, suffix="ready")
    return TestClient(app)


def test_health_liveness(client: TestClient) -> None:
    """GET /v1/health returns 200."""
    result = client.simulate_get("/v1/health")
    assert result.status_code == 200
    assert result.json["status"] == "ok"


def test_health_ready(client: TestClient) -> None:
    """GET /v1/health/ready returns 200."""
    result = client.simulate_get("/v1/health/ready")
    assert result.status_code == 200
    assert result.json["status"] == "ready"
