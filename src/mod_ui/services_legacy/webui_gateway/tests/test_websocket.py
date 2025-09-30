"""
Unit tests for WebSocket functionality
"""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket, WebSocketDisconnect

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


class TestWebSocketFunctionality:
    """Test cases for WebSocket endpoint functionality"""

    @pytest.mark.asyncio
    async def test_websocket_connection_success(self, mock_services):
        """Test successful WebSocket connection"""
        with (
            patch(
                "mod_ui.services.websocket_gateway.main.connection_manager",
                mock_services["connection_manager"],
            ),
            patch(
                "mod_ui.services.websocket_gateway.main.event_router",
                mock_services["event_router"],
            ),
        ):
            # Mock WebSocket
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.accept = AsyncMock()
            mock_websocket.receive_text = AsyncMock(
                side_effect=[
                    '{"type": "subscribe", "event_type": "test_event"}',
                    WebSocketDisconnect(code=1000),
                ]
            )
            mock_websocket.close = AsyncMock()

            # Import the websocket endpoint function
            from mod_ui.services.websocket_gateway.main import websocket_endpoint

            # Call the websocket endpoint
            try:
                await websocket_endpoint(mock_websocket)
            except WebSocketDisconnect:
                pass  # Expected disconnection

            # Verify connection was added
            mock_services["connection_manager"].add_connection.assert_called_once_with(
                mock_websocket
            )

            # Verify initial status was sent
            mock_services["event_router"].send_initial_status.assert_called_once()

            # Verify connection was removed on disconnect
            mock_services["connection_manager"].remove_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_services_unavailable(self):
        """Test WebSocket connection when services are unavailable"""
        with (
            patch("mod_ui.services.websocket_gateway.main.connection_manager", None),
            patch("mod_ui.services.websocket_gateway.main.event_router", None),
        ):
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.close = AsyncMock()

            from mod_ui.services.websocket_gateway.main import websocket_endpoint

            await websocket_endpoint(mock_websocket)

            # Verify WebSocket was closed with error code
            mock_websocket.close.assert_called_once_with(
                code=1011, reason="Gateway services not available"
            )

    @pytest.mark.asyncio
    async def test_websocket_message_handling(self, mock_services):
        """Test WebSocket message handling"""
        with (
            patch(
                "mod_ui.services.websocket_gateway.main.connection_manager",
                mock_services["connection_manager"],
            ),
            patch(
                "mod_ui.services.websocket_gateway.main.event_router",
                mock_services["event_router"],
            ),
        ):
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.accept = AsyncMock()
            mock_websocket.receive_text = AsyncMock(
                side_effect=[
                    '{"type": "test_message", "data": {"key": "value"}}',
                    WebSocketDisconnect(code=1000),
                ]
            )
            mock_websocket.close = AsyncMock()

            from mod_ui.services.websocket_gateway.main import websocket_endpoint

            try:
                await websocket_endpoint(mock_websocket)
            except WebSocketDisconnect:
                pass

            # Verify message was handled
            mock_services["event_router"].handle_client_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, mock_services):
        """Test WebSocket error handling"""
        with (
            patch(
                "mod_ui.services.websocket_gateway.main.connection_manager",
                mock_services["connection_manager"],
            ),
            patch(
                "mod_ui.services.websocket_gateway.main.event_router",
                mock_services["event_router"],
            ),
        ):
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.accept = AsyncMock()
            mock_websocket.receive_text = AsyncMock(
                side_effect=[
                    '{"invalid": json}',  # This will cause JSON decode error
                    WebSocketDisconnect(code=1000),
                ]
            )
            mock_websocket.close = AsyncMock()

            from mod_ui.services.websocket_gateway.main import websocket_endpoint

            try:
                await websocket_endpoint(mock_websocket)
            except WebSocketDisconnect:
                pass

            # Verify error message was sent to client
            mock_services["connection_manager"].send_to_client.assert_called()

    def test_websocket_route_exists(self, client):
        """Test that WebSocket route is properly registered"""
        # Check that the WebSocket route exists in the app
        websocket_routes = [
            route
            for route in app.routes
            if hasattr(route, "endpoint") and "websocket" in str(route.endpoint).lower()
        ]
        assert len(websocket_routes) == 1

        route = websocket_routes[0]
        assert route.path == "/ws"
        assert hasattr(route, "endpoint")


class TestWebSocketClientSimulation:
    """Test WebSocket client simulation using test client"""

    def test_websocket_upgrade_attempt(self, client):
        """Test WebSocket upgrade request (will fail but should not crash)"""
        # Note: TestClient doesn't support WebSocket connections directly
        # This test verifies the endpoint exists and handles the request appropriately
        response = client.get("/ws", headers={"upgrade": "websocket"})
        # FastAPI will return 403 Forbidden for WebSocket upgrade attempts via HTTP client
        assert response.status_code in [403, 426]  # 426 = Upgrade Required


class TestEventTypes:
    """Test event type handling"""

    def test_event_type_enum_import(self):
        """Test that EventType enum can be imported"""
        from mod_ui.services.websocket_gateway.utils.event_types import EventType

        # Verify some expected event types exist
        assert hasattr(EventType, "EFFECT_ADDED")
        assert hasattr(EventType, "PEDALBOARD_LOADED")
        assert hasattr(EventType, "CONNECTION_UPDATED")

        # Verify event types are strings
        assert isinstance(EventType.EFFECT_ADDED.value, str)

    def test_event_type_validation(self, client, mock_services):
        """Test event type validation in broadcast endpoint"""
        with patch(
            "mod_ui.services.websocket_gateway.main.event_router",
            mock_services["event_router"],
        ):
            # Test valid event type
            response = client.post(
                "/api/broadcast/broadcast/effect_added", json={"data": "test"}
            )
            assert response.status_code == 200

            # Test invalid event type
            response = client.post(
                "/api/broadcast/broadcast/invalid_event_type", json={"data": "test"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert "Invalid event type" in data["error"]


if __name__ == "__main__":
    pytest.main([__file__])
