"""
Unit tests for WebSocket Gateway Services
"""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "..", "src"),
)

from mod_ui.services.websocket_gateway.services.connection_manager import (
    ConnectionManager,
)
from mod_ui.services.websocket_gateway.services.event_router import EventRouter
from mod_ui.services.websocket_gateway.utils.event_types import EventType


class TestConnectionManager:
    """Test cases for ConnectionManager service"""

    @pytest.fixture
    def connection_manager(self):
        """ConnectionManager instance for testing"""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_add_connection(self, connection_manager):
        """Test adding a WebSocket connection"""
        mock_websocket = Mock()
        client_id = await connection_manager.add_connection(mock_websocket)

        assert client_id is not None
        assert isinstance(client_id, str)

        # Verify connection info
        connections = await connection_manager.get_connection_info()
        assert len(connections) == 1
        assert connections[0]["client_id"] == client_id

    @pytest.mark.asyncio
    async def test_remove_connection(self, connection_manager):
        """Test removing a WebSocket connection"""
        mock_websocket = Mock()
        client_id = await connection_manager.add_connection(mock_websocket)

        # Verify connection exists
        connections = await connection_manager.get_connection_info()
        assert len(connections) == 1

        # Remove connection
        result = await connection_manager.remove_connection(client_id)
        assert result is True

        # Verify connection is removed
        connections = await connection_manager.get_connection_info()
        assert len(connections) == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_connection(self, connection_manager):
        """Test removing a non-existent connection"""
        result = await connection_manager.remove_connection("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, connection_manager):
        """Test broadcasting to all connections"""
        # Add multiple connections
        mock_ws1 = Mock()
        mock_ws1.send_text = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.send_text = AsyncMock()

        await connection_manager.add_connection(mock_ws1)
        await connection_manager.add_connection(mock_ws2)

        # Broadcast message
        count = await connection_manager.broadcast_to_all(
            {"type": "test", "data": "message"}
        )
        assert count == 2

        # Verify both connections received the message
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_client(self, connection_manager):
        """Test sending message to specific client"""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        client_id = await connection_manager.add_connection(mock_websocket)

        # Send message
        result = await connection_manager.send_to_client(client_id, {"type": "test"})
        assert result is True

        # Verify message was sent
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_client(self, connection_manager):
        """Test sending message to non-existent client"""
        result = await connection_manager.send_to_client(
            "nonexistent", {"type": "test"}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_get_stats(self, connection_manager):
        """Test getting connection statistics"""
        # Add some connections
        await connection_manager.add_connection(Mock())
        await connection_manager.add_connection(Mock())

        stats = await connection_manager.get_stats()

        assert hasattr(stats, "total_connections")
        assert hasattr(stats, "active_connections")
        assert hasattr(stats, "total_messages_sent")
        assert hasattr(stats, "total_messages_received")
        assert stats.total_connections == 2
        assert stats.active_connections == 2

    @pytest.mark.asyncio
    async def test_legacy_message_methods(self, connection_manager):
        """Test legacy message sending methods"""
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()
        await connection_manager.add_connection(mock_websocket)

        # Test stats message
        count = await connection_manager.send_stats_message(0.5, 10)
        assert count == 1

        # Test sys stats message
        count = await connection_manager.send_sys_stats_message(0.3, "1000", "50")
        assert count == 1

        # Test transport message
        count = await connection_manager.send_transport_message(
            True, 4.0, 120.0, "internal"
        )
        assert count == 1

        # Test loading messages
        count = await connection_manager.send_loading_start_message(True, False)
        assert count == 1

        count = await connection_manager.send_loading_end_message(1)
        assert count == 1


class TestEventRouter:
    """Test cases for EventRouter service"""

    @pytest.fixture
    def event_router(self):
        """EventRouter instance for testing"""
        connection_manager = Mock()
        return EventRouter(connection_manager)

    @pytest.fixture
    def mock_connection_manager(self):
        """Mock ConnectionManager for EventRouter testing"""
        manager = Mock()
        manager.broadcast_to_all = AsyncMock(return_value=3)
        return manager

    @pytest.mark.asyncio
    async def test_broadcast_to_subscribers(self, mock_connection_manager):
        """Test broadcasting to event subscribers"""
        event_router = EventRouter(mock_connection_manager)

        # Broadcast to subscribers
        count = await event_router.broadcast_to_subscribers(
            EventType.EFFECT_ADDED,
            {"type": "effect_added", "data": {"effect_id": "test"}},
        )

        assert count == 3
        mock_connection_manager.broadcast_to_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting event router statistics"""
        connection_manager = Mock()
        event_router = EventRouter(connection_manager)

        stats = await event_router.get_stats()

        assert hasattr(stats, "events_processed")
        assert hasattr(stats, "active_subscriptions")
        assert stats.events_processed == 0
        assert stats.active_subscriptions == 0

    @pytest.mark.asyncio
    async def test_send_initial_status(self):
        """Test sending initial status to client"""
        connection_manager = Mock()
        connection_manager.send_to_client = AsyncMock(return_value=True)
        event_router = EventRouter(connection_manager)

        await event_router.send_initial_status("test_client")

        # Verify initial status was sent
        connection_manager.send_to_client.assert_called_once_with(
            "test_client",
            pytest.any(dict),  # Initial status message
        )

    @pytest.mark.asyncio
    async def test_handle_client_message(self):
        """Test handling client messages"""
        connection_manager = Mock()
        event_router = EventRouter(connection_manager)

        # Test subscribe message
        message = '{"type": "subscribe", "event_type": "effect_added"}'
        await event_router.handle_client_message("test_client", message)

        # Test unsubscribe message
        message = '{"type": "unsubscribe", "event_type": "effect_added"}'
        await event_router.handle_client_message("test_client", message)

        # Test invalid message
        message = '{"type": "invalid"}'
        await event_router.handle_client_message("test_client", message)

        # Should not crash on invalid JSON
        await event_router.handle_client_message("test_client", "invalid json")


class TestRedisEventSubscriber:
    """Test cases for RedisEventSubscriber service"""

    @pytest.fixture
    def redis_subscriber(self):
        """RedisEventSubscriber instance for testing"""
        from mod_ui.services.websocket_gateway.services.redis_subscriber import (
            RedisEventSubscriber,
        )

        event_router = Mock()
        return RedisEventSubscriber(event_router)

    def test_initialization(self, redis_subscriber):
        """Test Redis subscriber initialization"""
        assert redis_subscriber is not None
        assert hasattr(redis_subscriber, "start")
        assert hasattr(redis_subscriber, "stop")
        assert hasattr(redis_subscriber, "is_connected")

    def test_is_connected_default(self, redis_subscriber):
        """Test default connection status"""
        # Should return False when not connected
        assert redis_subscriber.is_connected() is False

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, redis_subscriber):
        """Test start/stop lifecycle"""
        # These should not crash even without Redis
        await redis_subscriber.start()
        await redis_subscriber.stop()


if __name__ == "__main__":
    pytest.main([__file__])
