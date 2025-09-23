"""
Unit tests for remaining API Routers (Favorites, Snapshots, Banks, System, Updates, Utilities, LV2)
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


class TestFavoritesRouter:
    """Test cases for Favorites API endpoints"""

    def test_add_favorite(self, client):
        """Test POST /api/favorites/favorites/add"""
        response = client.post(
            "/api/favorites/favorites/add",
            json={"uri": "test_uri", "label": "Test Favorite"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["uri"] == "test_uri"

    def test_remove_favorite(self, client):
        """Test POST /api/favorites/favorites/remove"""
        response = client.post(
            "/api/favorites/favorites/remove", json={"uri": "test_uri"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["removed"] == "test_uri"

    def test_list_favorites(self, client):
        """Test GET /api/favorites/favorites/list"""
        response = client.get("/api/favorites/favorites/list")
        assert response.status_code == 200
        data = response.json()
        assert "favorites" in data
        assert isinstance(data["favorites"], list)


class TestSnapshotsRouter:
    """Test cases for Snapshots API endpoints"""

    def test_get_snapshot_name(self, client):
        """Test GET /api/snapshots/snapshot/name"""
        response = client.get("/api/snapshots/snapshot/name?index=0")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["index"] == 0

    def test_save_snapshot(self, client):
        """Test POST /api/snapshots/snapshot/save"""
        response = client.post(
            "/api/snapshots/snapshot/save", json={"index": 0, "name": "Test Snapshot"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["index"] == 0

    def test_saveas_snapshot(self, client):
        """Test POST /api/snapshots/snapshot/saveas"""
        response = client.post(
            "/api/snapshots/snapshot/saveas", json={"name": "New Snapshot"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "index" in data

    def test_rename_snapshot(self, client):
        """Test POST /api/snapshots/snapshot/rename"""
        response = client.post(
            "/api/snapshots/snapshot/rename",
            json={"index": 0, "name": "Renamed Snapshot"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["index"] == 0

    def test_remove_snapshot(self, client):
        """Test POST /api/snapshots/snapshot/remove"""
        response = client.post("/api/snapshots/snapshot/remove", json={"index": 0})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["index"] == 0

    def test_list_snapshots(self, client):
        """Test GET /api/snapshots/snapshot/list"""
        response = client.get("/api/snapshots/snapshot/list")
        assert response.status_code == 200
        data = response.json()
        assert "snapshots" in data
        assert isinstance(data["snapshots"], list)

    def test_load_snapshot(self, client):
        """Test POST /api/snapshots/snapshot/load"""
        response = client.post("/api/snapshots/snapshot/load", json={"index": 0})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["index"] == 0


class TestBanksRouter:
    """Test cases for Banks API endpoints"""

    def test_load_bank(self, client):
        """Test POST /api/banks/bank/load"""
        response = client.post("/api/banks/bank/load", json={"uri": "test_bank_uri"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["uri"] == "test_bank_uri"

    def test_save_bank(self, client):
        """Test POST /api/banks/bank/save"""
        response = client.post(
            "/api/banks/bank/save",
            json={"uri": "test_bank_uri", "data": {"pedalboards": []}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["uri"] == "test_bank_uri"


class TestSystemRouter:
    """Test cases for System API endpoints"""

    def test_system_info(self, client):
        """Test GET /api/system/system/info"""
        response = client.get("/api/system/system/info")
        assert response.status_code == 200
        data = response.json()
        assert "info" in data
        assert "version" in data["info"]

    def test_system_preferences(self, client):
        """Test GET /api/system/system/preferences"""
        response = client.get("/api/system/system/preferences")
        assert response.status_code == 200
        data = response.json()
        assert "preferences" in data

    def test_execute_command(self, client):
        """Test POST /api/system/system/exe"""
        response = client.post(
            "/api/system/system/exe",
            json={"command": "test_command", "args": ["arg1", "arg2"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["command"] == "test_command"

    def test_cleanup_system(self, client):
        """Test POST /api/system/system/cleanup"""
        response = client.post("/api/system/system/cleanup")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cleanup" in data


class TestUpdatesRouter:
    """Test cases for Updates API endpoints"""

    def test_download_update(self, client):
        """Test POST /api/updates/update/download"""
        response = client.post(
            "/api/updates/update/download", json={"version": "1.0.1"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["version"] == "1.0.1"

    def test_begin_update(self, client):
        """Test POST /api/updates/update/begin"""
        response = client.post("/api/updates/update/begin")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "update" in data

    def test_download_cc(self, client):
        """Test POST /api/updates/cc/download"""
        response = client.post(
            "/api/updates/cc/download", json={"url": "http://example.com/cc"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "download" in data

    def test_cancel_cc_download(self, client):
        """Test POST /api/updates/cc/cancel"""
        response = client.post("/api/updates/cc/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cancelled" in data


class TestUtilitiesRouter:
    """Test cases for Utilities API endpoints"""

    def test_ping_utility(self, client):
        """Test GET /api/utilities/ping"""
        response = client.get("/api/utilities/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["pong"] is True

    def test_hello_utility(self, client):
        """Test GET /api/utilities/hello"""
        response = client.get("/api/utilities/hello")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Hello" in data["message"]

    def test_truebypass(self, client):
        """Test POST /api/utilities/truebypass/{channel}/{state}"""
        response = client.post("/api/utilities/truebypass/1/true")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["channel"] == 1
        assert data["state"] is True

    def test_buffersize(self, client):
        """Test POST /api/utilities/buffersize/{size}"""
        response = client.post("/api/utilities/buffersize/512")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["buffersize"] == 512

    def test_reset_xruns(self, client):
        """Test POST /api/utilities/xruns/reset"""
        response = client.post("/api/utilities/xruns/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "reset" in data

    def test_cpu_freq_switch(self, client):
        """Test POST /api/utilities/cpu/freq/switch"""
        response = client.post(
            "/api/utilities/cpu/freq/switch", json={"frequency": "performance"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["frequency"] == "performance"

    def test_save_config(self, client):
        """Test POST /api/utilities/config/save"""
        response = client.post("/api/utilities/config/save")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "saved" in data

    def test_save_user_data(self, client):
        """Test POST /api/utilities/user/save"""
        response = client.post("/api/utilities/user/save")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "saved" in data

    def test_clean_dashboard(self, client):
        """Test POST /api/utilities/dashboard/clean"""
        response = client.post("/api/utilities/dashboard/clean")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cleaned" in data


class TestLV2Router:
    """Test cases for LV2 API endpoints"""

    def test_get_lv2_bundle(self, client):
        """Test GET /api/lv2/lv2/bundles/{bundle_id}"""
        response = client.get("/api/lv2/lv2/bundles/test_bundle")
        assert response.status_code == 200
        data = response.json()
        assert "bundle" in data
        assert data["bundle_id"] == "test_bundle"

    def test_list_lv2_plugins(self, client):
        """Test GET /api/lv2/lv2/plugins"""
        response = client.get("/api/lv2/lv2/plugins")
        assert response.status_code == 200
        data = response.json()
        assert "plugins" in data
        assert isinstance(data["plugins"], list)


if __name__ == "__main__":
    pytest.main([__file__])
