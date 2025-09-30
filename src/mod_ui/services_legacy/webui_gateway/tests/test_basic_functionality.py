"""
Simple unit tests for WebSocket Gateway Service - Basic functionality only
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "..", "src"),
)

from mod_ui.services.websocket_gateway.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


class TestBasicFunctionality:
    """Basic tests to verify the service works"""

    def test_app_creation(self):
        """Test that FastAPI app is created correctly"""
        assert app.title == "Madeline Web UI Gateway"
        assert app.version == "1.0.0"
        assert len(app.routes) >= 80  # Should have many routes

    def test_health_endpoints(self, client):
        """Test basic health check endpoints"""
        # Test /ping
        response = client.get("/api/health/ping")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

        # Test /health
        response = client.get("/api/health/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_utilities_endpoints(self, client):
        """Test utilities endpoints"""
        # Test ping utility
        response = client.get("/api/utilities/ping")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

        # Test hello utility
        response = client.get("/api/utilities/hello")
        assert response.status_code == 200
        data = response.json()
        assert "online" in data
        assert data["online"] is True

    def test_effects_endpoints(self, client):
        """Test effects endpoints"""
        # Test list effects
        response = client.get("/api/effects/effect/list")
        assert response.status_code == 200
        data = response.json()
        assert "effects" in data
        assert isinstance(data["effects"], list)

        # Test get effect (should fail with 404 for non-existent)
        response = client.get("/api/effects/effect/get?uri=nonexistent")
        assert response.status_code == 404

        # Test get effect (should work with mock data)
        response = client.get(
            "/api/effects/effect/get?uri=http://lv2plug.in/plugins/eg-amp"
        )
        assert response.status_code == 200
        data = response.json()
        assert "uri" in data
        assert data["uri"] == "http://lv2plug.in/plugins/eg-amp"

    def test_favorites_endpoints(self, client):
        """Test favorites endpoints"""
        # Test list favorites
        response = client.get("/api/favorites/favorites/list")
        assert response.status_code == 200
        data = response.json()
        assert "favorites" in data
        assert isinstance(data["favorites"], list)

    def test_snapshots_endpoints(self, client):
        """Test snapshots endpoints"""
        # Test list snapshots
        response = client.get("/api/snapshots/snapshot/list")
        assert response.status_code == 200
        data = response.json()
        # The response is a dict with snapshot IDs as keys
        assert isinstance(data, dict)
        assert len(data) > 0  # Should have some snapshots

    def test_pedalboard_endpoints(self, client):
        """Test pedalboard endpoints"""
        # Test list pedalboards
        response = client.get("/api/pedalboard/pedalboard/list")
        assert response.status_code == 200
        data = response.json()
        # The actual response format may vary, just check it returns data
        assert isinstance(data, (list, dict))

    def test_system_endpoints(self, client):
        """Test system endpoints"""
        # Test system info
        response = client.get("/api/system/system/info")
        assert response.status_code == 200
        data = response.json()
        # The actual response format may vary, just check it returns data
        assert isinstance(data, dict)

    def test_lv2_endpoints(self, client):
        """Test LV2 endpoints"""
        # Test list plugins
        response = client.get("/api/lv2/lv2/plugins")
        assert response.status_code == 200
        data = response.json()
        # The actual response format may vary, just check it returns data
        assert isinstance(data, (list, dict))

    def test_router_integration(self, client):
        """Test that all routers are properly integrated"""
        # Count routes by prefix to verify routers are included
        routes = [route.path for route in app.routes if hasattr(route, "path")]

        # Check that we have routes for each router
        effects_routes = [r for r in routes if r.startswith("/api/effects")]
        assert len(effects_routes) > 0

        favorites_routes = [r for r in routes if r.startswith("/api/favorites")]
        assert len(favorites_routes) > 0

        snapshots_routes = [r for r in routes if r.startswith("/api/snapshots")]
        assert len(snapshots_routes) > 0

        pedalboard_routes = [r for r in routes if r.startswith("/api/pedalboard")]
        assert len(pedalboard_routes) > 0

        banks_routes = [r for r in routes if r.startswith("/api/banks")]
        assert len(banks_routes) > 0

        system_routes = [r for r in routes if r.startswith("/api/system")]
        assert len(system_routes) > 0

        updates_routes = [r for r in routes if r.startswith("/api/updates")]
        assert len(updates_routes) > 0

        utilities_routes = [r for r in routes if r.startswith("/api/utilities")]
        assert len(utilities_routes) > 0

        lv2_routes = [r for r in routes if r.startswith("/api/lv2")]
        assert len(lv2_routes) > 0


if __name__ == "__main__":
    pytest.main([__file__])
