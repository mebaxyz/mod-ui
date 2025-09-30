"""
Unit tests for Pedalboard API Router
"""

import os
import sys
from unittest.mock import Mock, patch

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


class TestPedalboardRouter:
    """Test cases for Pedalboard API endpoints"""

    def test_save_pedalboard(self, client):
        """Test POST /api/pedalboard/pedalboard/save"""
        response = client.post(
            "/api/pedalboard/pedalboard/save",
            json={"title": "Test Pedalboard", "data": {"effects": []}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "pedalboard" in data

    def test_load_bundle(self, client):
        """Test POST /api/pedalboard/pedalboard/load_bundle"""
        response = client.post(
            "/api/pedalboard/pedalboard/load_bundle",
            json={"bundle": "test_bundle_data"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "loaded" in data

    def test_remove_pedalboard(self, client):
        """Test POST /api/pedalboard/pedalboard/remove"""
        response = client.post(
            "/api/pedalboard/pedalboard/remove", json={"uri": "test_uri"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["removed"] == "test_uri"

    def test_pedalboard_info(self, client):
        """Test GET /api/pedalboard/pedalboard/info"""
        response = client.get("/api/pedalboard/pedalboard/info?uri=test_uri")
        assert response.status_code == 200
        data = response.json()
        assert "info" in data
        assert data["uri"] == "test_uri"

    def test_factory_copy(self, client):
        """Test POST /api/pedalboard/pedalboard/factory_copy"""
        response = client.post(
            "/api/pedalboard/pedalboard/factory_copy",
            json={"uri": "test_uri", "title": "Factory Copy"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "copy" in data

    def test_list_pedalboards(self, client):
        """Test GET /api/pedalboard/pedalboard/list"""
        response = client.get("/api/pedalboard/pedalboard/list")
        assert response.status_code == 200
        data = response.json()
        assert "pedalboards" in data
        assert isinstance(data["pedalboards"], list)

    def test_pack_bundle(self, client):
        """Test POST /api/pedalboard/pedalboard/pack_bundle"""
        response = client.post(
            "/api/pedalboard/pedalboard/pack_bundle", json={"uri": "test_uri"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "bundle" in data

    def test_load_remote_pedalboard(self, client):
        """Test GET /api/pedalboard/pedalboard/load_remote/{pedalboard_id}"""
        response = client.get("/api/pedalboard/pedalboard/load_remote/test_id")
        assert response.status_code == 200
        data = response.json()
        assert "pedalboard" in data
        assert data["id"] == "test_id"

    def test_load_web_pedalboard(self, client):
        """Test POST /api/pedalboard/pedalboard/load_web"""
        response = client.post(
            "/api/pedalboard/pedalboard/load_web",
            json={"url": "http://example.com/pedalboard"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "loaded" in data

    def test_pedalboard_image(self, client):
        """Test GET /api/pedalboard/pedalboard/image/{image}"""
        response = client.get("/api/pedalboard/pedalboard/image/test_image")
        assert response.status_code == 200
        data = response.json()
        assert "image" in data
        assert data["image_id"] == "test_image"

    def test_generate_image(self, client):
        """Test POST /api/pedalboard/pedalboard/image/generate"""
        response = client.post(
            "/api/pedalboard/pedalboard/image/generate",
            json={"pedalboard_uri": "test_uri"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "generation_id" in data

    def test_check_image_generation(self, client):
        """Test GET /api/pedalboard/pedalboard/image/check"""
        response = client.get(
            "/api/pedalboard/pedalboard/image/check?generation_id=test_id"
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["generation_id"] == "test_id"

    def test_wait_for_image(self, client):
        """Test GET /api/pedalboard/pedalboard/image/wait"""
        response = client.get(
            "/api/pedalboard/pedalboard/image/wait?generation_id=test_id"
        )
        assert response.status_code == 200
        data = response.json()
        assert "image" in data
        assert data["generation_id"] == "test_id"

    def test_add_cv_addressing(self, client):
        """Test POST /api/pedalboard/pedalboard/cv_addressing/plugin_port/add"""
        response = client.post(
            "/api/pedalboard/pedalboard/cv_addressing/plugin_port/add",
            json={
                "plugin_uri": "test_plugin",
                "port_symbol": "test_port",
                "addressing": {"type": "linear", "minimum": 0, "maximum": 1},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "addressing" in data

    def test_remove_cv_addressing(self, client):
        """Test POST /api/pedalboard/pedalboard/cv_addressing/plugin_port/remove"""
        response = client.post(
            "/api/pedalboard/pedalboard/cv_addressing/plugin_port/remove",
            json={"plugin_uri": "test_plugin", "port_symbol": "test_port"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "removed" in data

    def test_set_sync_mode(self, client):
        """Test POST /api/pedalboard/pedalboard/transport/set_sync_mode/{mode}"""
        response = client.post(
            "/api/pedalboard/pedalboard/transport/set_sync_mode/internal"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["sync_mode"] == "internal"


if __name__ == "__main__":
    pytest.main([__file__])
