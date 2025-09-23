"""
Unit tests for WebSocket Gateway Service
"""

import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "..", "src"),
)

from mod_ui.services.websocket_gateway.main import app
from mod_ui.services.websocket_gateway.services.connection_manager import (
    ConnectionManager,
)
from mod_ui.services.websocket_gateway.services.event_router import EventRouter
from mod_ui.services.websocket_gateway.services.redis_subscriber import (
    RedisEventSubscriber,
)


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_services():
    """Mock service instances"""
    connection_manager = Mock(spec=ConnectionManager)
    event_router = Mock(spec=EventRouter)
    redis_subscriber = Mock(spec=RedisEventSubscriber)

    return {
        "connection_manager": connection_manager,
        "event_router": event_router,
        "redis_subscriber": redis_subscriber,
    }


class TestWebSocketGateway:
    """Test cases for WebSocket Gateway main functionality"""

    def test_app_creation(self):
        """Test that FastAPI app is created correctly"""
        assert app.title == "Madeline Web UI Gateway"
        assert app.version == "1.0.0"
        assert len(app.routes) == 93  # Total routes including all routers

    def test_health_endpoints(self, client):
        """Test health check endpoints"""
        # Test /ping
        response = client.get("/api/health/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "websocket-gateway"}

        # Test /health
        response = client.get("/api/health/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["health"] == "healthy"
        assert "services" in data
        assert "timestamp" in data

    def test_status_endpoint(self, client, mock_services):
        """Test status endpoint"""
        with patch(
            "mod_ui.services.websocket_gateway.main.connection_manager",
            mock_services["connection_manager"],
        ), patch(
            "mod_ui.services.websocket_gateway.main.event_router",
            mock_services["event_router"],
        ), patch(
            "mod_ui.services.websocket_gateway.main.redis_subscriber",
            mock_services["redis_subscriber"],
        ):

            # Mock stats
            mock_stats = Mock()
            mock_stats.total_connections = 10
            mock_stats.active_connections = 5
            mock_stats.total_messages_sent = 100
            mock_stats.total_messages_received = 80
            mock_services["connection_manager"].get_stats.return_value = mock_stats

            mock_router_stats = Mock()
            mock_router_stats.events_processed = 50
            mock_router_stats.active_subscriptions = 3
            mock_services["event_router"].get_stats.return_value = mock_router_stats

            mock_services["redis_subscriber"].is_connected.return_value = True

            response = client.get("/api/health/status")
            assert response.status_code == 200
            data = response.json()

            assert data["service"] == "websocket-gateway"
            assert data["version"] == "1.0.0"
            assert data["status"] == "running"
            assert data["total_connections"] == 10
            assert data["active_connections"] == 5
            assert data["events_processed"] == 50
            assert data["redis_connected"] is True

    def test_connections_endpoint(self, client, mock_services):
        """Test connections listing endpoint"""
        with patch(
            "mod_ui.services.websocket_gateway.main.connection_manager",
            mock_services["connection_manager"],
        ):
            mock_connections = [
                {
                    "client_id": "client1",
                    "connected_at": 1234567890,
                    "last_activity": 1234567890,
                    "messages_sent": 10,
                    "messages_received": 5,
                    "subscriptions": [],
                }
            ]
            mock_services["connection_manager"].get_connection_info.return_value = (
                mock_connections
            )

            response = client.get("/api/connections/connections")
            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert len(data["connections"]) == 1
            assert data["count"] == 1

    def test_broadcast_endpoints(self, client, mock_services):
        """Test broadcast endpoints"""
        with patch(
            "mod_ui.services.websocket_gateway.main.connection_manager",
            mock_services["connection_manager"],
        ), patch(
            "mod_ui.services.websocket_gateway.main.event_router",
            mock_services["event_router"],
        ):

            # Test general broadcast
            mock_services["connection_manager"].broadcast_to_all.return_value = 3

            response = client.post("/api/broadcast/broadcast", json={"message": "test"})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["clients_reached"] == 3

            # Test event-specific broadcast
            mock_services["event_router"].broadcast_to_subscribers.return_value = 2

            response = client.post(
                "/api/broadcast/broadcast/test_event", json={"data": "test"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["clients_reached"] == 2

    def test_client_management_endpoints(self, client, mock_services):
        """Test client management endpoints"""
        with patch(
            "mod_ui.services.websocket_gateway.main.connection_manager",
            mock_services["connection_manager"],
        ):
            # Test list clients
            mock_connections = [
                {
                    "client_id": "client1",
                    "connected_at": 1234567890,
                    "last_activity": 1234567890,
                    "messages_sent": 10,
                    "messages_received": 5,
                    "subscriptions": [],
                }
            ]
            mock_services["connection_manager"].get_connection_info.return_value = (
                mock_connections
            )

            response = client.get("/api/connections/clients")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["clients"]) == 1

            # Test get specific client
            response = client.get("/api/connections/clients/client1")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["client"]["client_id"] == "client1"

            # Test disconnect client
            mock_services["connection_manager"].remove_connection.return_value = True

            response = client.post("/api/connections/clients/client1/disconnect")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Test send message to client
            mock_services["connection_manager"].send_to_client.return_value = True

            response = client.post(
                "/api/connections/clients/client1/send", json={"message": "test"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_event_endpoints(self, client, mock_services):
        """Test event management endpoints"""
        with patch(
            "mod_ui.services.websocket_gateway.main.event_router",
            mock_services["event_router"],
        ):
            # Test list event types
            response = client.get("/api/broadcast/events/types")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "event_types" in data
            assert "count" in data

            # Test publish event
            response = client.post(
                "/api/broadcast/events/publish",
                json={"event_type": "test_event", "data": {"key": "value"}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["event_type"] == "test_event"

    def test_legacy_endpoints(self, client, mock_services):
        """Test legacy message endpoints"""
        with patch(
            "mod_ui.services.websocket_gateway.main.connection_manager",
            mock_services["connection_manager"],
        ):
            # Test legacy stats
            mock_services["connection_manager"].send_stats_message.return_value = 2

            response = client.post(
                "/api/legacy/stats", json={"cpu_load": 0.5, "xruns": 10}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["clients_reached"] == 2

            # Test legacy transport
            mock_services["connection_manager"].send_transport_message.return_value = 3

            response = client.post(
                "/api/legacy/transport",
                json={"rolling": True, "bpb": 4.0, "bpm": 120.0, "sync": "internal"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["clients_reached"] == 3

    def test_error_handling(self, client):
        """Test error handling when services are unavailable"""
        # Test with no connection manager
        with patch("mod_ui.services.websocket_gateway.main.connection_manager", None):
            response = client.get("/api/connections/connections")
            assert response.status_code == 200
            data = response.json()
            assert "error" in data

        # Test with no event router
        with patch("mod_ui.services.websocket_gateway.main.event_router", None):
            response = client.post(
                "/api/broadcast/broadcast/test_event", json={"data": "test"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "error" in data

    def test_invalid_event_type(self, client, mock_services):
        """Test invalid event type handling"""
        with patch(
            "mod_ui.services.websocket_gateway.main.event_router",
            mock_services["event_router"],
        ):
            response = client.post(
                "/api/broadcast/broadcast/invalid_event", json={"data": "test"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert "Invalid event type" in data["error"]


if __name__ == "__main__":
    pytest.main([__file__])
