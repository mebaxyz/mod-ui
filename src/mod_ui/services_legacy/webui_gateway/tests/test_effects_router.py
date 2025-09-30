"""
Unit tests for Effects API Router
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


class TestEffectsRouter:
    """Test cases for Effects API endpoints"""

    def test_list_effects(self, client):
        """Test GET /api/effects/effect/list"""
        response = client.get("/api/effects/effect/list")
        assert response.status_code == 200
        data = response.json()
        assert "effects" in data
        assert isinstance(data["effects"], list)

    def test_get_effect(self, client):
        """Test GET /api/effects/effect/get"""
        response = client.get("/api/effects/effect/get?uri=test_uri")
        assert response.status_code == 200
        data = response.json()
        assert "effect" in data
        assert data["effect"]["uri"] == "test_uri"

    def test_install_effect(self, client):
        """Test POST /api/effects/effect/install"""
        response = client.post("/api/effects/effect/install", json={"uri": "test_uri"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "installed" in data

    def test_add_effect(self, client):
        """Test POST /api/effects/effect/add/{instance}"""
        response = client.post(
            "/api/effects/effect/add/test_instance",
            json={"uri": "test_uri", "x": 100, "y": 200},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["instance"] == "test_instance"

    def test_remove_effect(self, client):
        """Test POST /api/effects/effect/remove/{instance}"""
        response = client.post("/api/effects/effect/remove/test_instance")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["instance"] == "test_instance"

    def test_connect_effects(self, client):
        """Test POST /api/effects/effect/connect/{port_from}/{port_to}"""
        response = client.post("/api/effects/effect/connect/port1/port2")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["connection"] == "port1 -> port2"

    def test_disconnect_effects(self, client):
        """Test POST /api/effects/effect/disconnect/{port_from}/{port_to}"""
        response = client.post("/api/effects/effect/disconnect/port1/port2")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["disconnection"] == "port1 -> port2"

    def test_load_preset(self, client):
        """Test POST /api/effects/effect/preset/load/{instance}"""
        response = client.post(
            "/api/effects/effect/preset/load/test_instance", json={"uri": "preset_uri"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["instance"] == "test_instance"

    def test_save_new_preset(self, client):
        """Test POST /api/effects/effect/preset/save_new/{instance}"""
        response = client.post(
            "/api/effects/effect/preset/save_new/test_instance",
            json={"name": "New Preset"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["instance"] == "test_instance"

    def test_save_replace_preset(self, client):
        """Test POST /api/effects/effect/preset/save_replace/{instance}"""
        response = client.post(
            "/api/effects/effect/preset/save_replace/test_instance",
            json={"uri": "preset_uri"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["instance"] == "test_instance"

    def test_delete_preset(self, client):
        """Test POST /api/effects/effect/preset/delete/{instance}"""
        response = client.post(
            "/api/effects/effect/preset/delete/test_instance",
            json={"uri": "preset_uri"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["instance"] == "test_instance"

    def test_get_non_cached(self, client):
        """Test GET /api/effects/effect/get_non_cached"""
        response = client.get("/api/effects/effect/get_non_cached")
        assert response.status_code == 200
        data = response.json()
        assert "effects" in data
        assert isinstance(data["effects"], list)

    def test_parameter_address(self, client):
        """Test GET /api/effects/effect/parameter/address/{port}"""
        response = client.get("/api/effects/effect/parameter/address/test_port")
        assert response.status_code == 200
        data = response.json()
        assert "address" in data
        assert data["port"] == "test_port"

    def test_set_parameter(self, client):
        """Test POST /api/effects/effect/parameter/set"""
        response = client.post(
            "/api/effects/effect/parameter/set",
            json={"instance": "test_instance", "port": "test_port", "value": 0.5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["instance"] == "test_instance"

    def test_effect_resource(self, client):
        """Test GET /api/effects/effect/resource/{path}"""
        response = client.get("/api/effects/effect/resource/test/path")
        assert response.status_code == 200
        data = response.json()
        assert "resource" in data
        assert data["path"] == "test/path"

    def test_effect_image(self, client):
        """Test GET /api/effects/effect/image/{image}"""
        response = client.get("/api/effects/effect/image/test_image")
        assert response.status_code == 200
        data = response.json()
        assert "image" in data
        assert data["image_id"] == "test_image"

    def test_effect_file(self, client):
        """Test GET /api/effects/effect/file/{prop}"""
        response = client.get("/api/effects/effect/file/test_prop")
        assert response.status_code == 200
        data = response.json()
        assert "file" in data
        assert data["property"] == "test_prop"


if __name__ == "__main__":
    pytest.main([__file__])
