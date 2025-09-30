"""
Pytest configuration and shared fixtures for WebSocket Gateway tests
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock

# Add src to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_connection_manager():
    """Mock ConnectionManager for testing"""
    manager = Mock()
    manager.add_connection = AsyncMock(return_value="test_client_id")
    manager.remove_connection = AsyncMock(return_value=True)
    manager.get_connection_info = AsyncMock(return_value=[])
    manager.broadcast_to_all = AsyncMock(return_value=5)
    manager.send_to_client = AsyncMock(return_value=True)
    manager.get_stats = AsyncMock(
        return_value=Mock(
            total_connections=10,
            active_connections=5,
            total_messages_sent=100,
            total_messages_received=80,
        )
    )
    return manager


@pytest.fixture
def mock_event_router():
    """Mock EventRouter for testing"""
    router = Mock()
    router.broadcast_to_subscribers = AsyncMock(return_value=3)
    router.get_stats = AsyncMock(
        return_value=Mock(events_processed=50, active_subscriptions=3)
    )
    router.send_initial_status = AsyncMock()
    router.handle_client_message = AsyncMock()
    return router


@pytest.fixture
def mock_redis_subscriber():
    """Mock RedisEventSubscriber for testing"""
    subscriber = Mock()
    subscriber.start = AsyncMock()
    subscriber.stop = AsyncMock()
    subscriber.is_connected = Mock(return_value=True)
    return subscriber


@pytest.fixture
def mock_services(mock_connection_manager, mock_event_router, mock_redis_subscriber):
    """Combined mock services fixture"""
    return {
        "connection_manager": mock_connection_manager,
        "event_router": mock_event_router,
        "redis_subscriber": mock_redis_subscriber,
    }


# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location"""
    for item in items:
        # Mark all tests in tests/ as unit tests by default
        if "test_" in item.name and not any(
            mark.name in ["integration", "slow"] for mark in item.own_markers
        ):
            item.add_marker(pytest.mark.unit)
