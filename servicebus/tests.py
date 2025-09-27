import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from servicebus import ServiceClient, ServiceServer, ServiceDiscovery, EventBus
from servicebus.models import ServiceRequest, ServiceResponse, ServiceEvent
from servicebus.config import CommConfig


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    mock = AsyncMock()
    mock.publish = AsyncMock(return_value=1)
    mock.get = AsyncMock(return_value=None)
    mock.keys = AsyncMock(return_value=[])
    mock.setex = AsyncMock()
    mock.delete = AsyncMock()
    mock.close = AsyncMock()

    # Mock pubsub
    mock_pubsub = AsyncMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.listen = AsyncMock()
    mock_pubsub.close = AsyncMock()
    mock.pubsub.return_value = mock_pubsub

    return mock


@pytest.fixture
def test_config():
    """Test configuration"""
    return CommConfig(
        redis_url="redis://localhost:6379",
        default_timeout=1.0,
        enable_metrics=True,
        debug_mode=True,
    )


class TestServiceClient:
    """Test ServiceClient functionality"""

    @pytest.mark.asyncio
    async def test_client_creation(self, mock_redis, test_config):
        """Test client creation"""
        client = ServiceClient("test-service", mock_redis)
        assert client.service_name == "test-service"
        await client.close()

    @pytest.mark.asyncio
    async def test_successful_call(self, mock_redis, test_config):
        """Test successful service call"""
        # Mock response
        response_data = ServiceResponse(
            id="test-123", success=True, data={"result": "success"}
        )

        # Mock pubsub listen to return our response
        async def mock_listen():
            yield {"type": "message", "data": response_data.json()}

        mock_redis.pubsub().listen = mock_listen

        client = ServiceClient("test-service", mock_redis)

        try:
            result = await client.call(
                target_service="target-service",
                request_type="test_request",
                data={"test": "data"},
            )

            assert result == {"result": "success"}

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_failed_call(self, mock_redis, test_config):
        """Test failed service call"""
        # Mock error response
        response_data = ServiceResponse(
            id="test-123", success=False, error="Test error", data={}
        )

        async def mock_listen():
            yield {"type": "message", "data": response_data.json()}

        mock_redis.pubsub().listen = mock_listen

        client = ServiceClient("test-service", mock_redis)

        try:
            with pytest.raises(RuntimeError, match="Test error"):
                await client.call(
                    target_service="target-service", request_type="test_request"
                )

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_timeout(self, mock_redis, test_config):
        """Test request timeout"""

        # Mock pubsub that never returns a message
        async def mock_listen():
            # Simulate no messages
            if False:
                yield None

        mock_redis.pubsub().listen = mock_listen

        client = ServiceClient("test-service", mock_redis)

        try:
            with pytest.raises(TimeoutError):
                await client.call(
                    target_service="target-service",
                    request_type="test_request",
                    timeout=0.1,  # Very short timeout
                )

        finally:
            await client.close()


class TestServiceServer:
    """Test ServiceServer functionality"""

    @pytest.mark.asyncio
    async def test_server_creation(self, mock_redis, test_config):
        """Test server creation"""
        server = ServiceServer("test-service", mock_redis)
        assert server.service_name == "test-service"
        assert len(server._handlers) == 0

    @pytest.mark.asyncio
    async def test_handler_registration(self, mock_redis, test_config):
        """Test handler registration"""
        server = ServiceServer("test-service", mock_redis)

        async def test_handler(data):
            return {"handled": True}

        server.register_handler("test_type", test_handler, "Test handler")

        assert "test_type" in server._handlers
        assert len(server._capabilities) == 1
        assert server._capabilities[0].request_type == "test_type"

    @pytest.mark.asyncio
    async def test_request_handling(self, mock_redis, test_config):
        """Test request handling"""
        server = ServiceServer("test-service", mock_redis)

        async def test_handler(data):
            return {"result": data.get("input", "") + "_processed"}

        server.register_handler("process", test_handler, "Process data")

        # Create a test request
        request = ServiceRequest(
            id="test-123",
            source_service="client-service",
            target_service="test-service",
            request_type="process",
            data={"input": "test_data"},
        )

        # Handle the request
        await server._handle_request(request)

        # Verify response was sent
        mock_redis.publish.assert_called_once()

        # Check the response content
        call_args = mock_redis.publish.call_args
        channel = call_args[0][0]
        response_json = call_args[0][1]

        assert channel == "service:client-service:responses:test-123"
        response = ServiceResponse.parse_raw(response_json)
        assert response.success
        assert response.data["result"] == "test_data_processed"


class TestServiceDiscovery:
    """Test ServiceDiscovery functionality"""

    @pytest.mark.asyncio
    async def test_discovery_creation(self, mock_redis, test_config):
        """Test discovery service creation"""
        discovery = ServiceDiscovery(mock_redis)
        await discovery.close()

    @pytest.mark.asyncio
    async def test_discover_services_empty(self, mock_redis, test_config):
        """Test discovering services when none exist"""
        mock_redis.keys.return_value = []

        discovery = ServiceDiscovery(mock_redis)

        try:
            services = await discovery.discover_services()
            assert services == {}

        finally:
            await discovery.close()

    @pytest.mark.asyncio
    async def test_discover_services_with_data(self, mock_redis, test_config):
        """Test discovering services with registered services"""
        from servicebus.models import (
            ServiceRegistration,
            ServiceHealth,
            ServiceCapability,
        )

        # Mock service registration
        health = ServiceHealth(
            service_name="test-service", status="healthy", timestamp=datetime.utcnow()
        )

        capability = ServiceCapability(
            request_type="test_request", description="Test request"
        )

        registration = ServiceRegistration(
            service_name="test-service", capabilities=[capability], health=health
        )

        mock_redis.keys.return_value = ["service_registry:test-service"]
        mock_redis.get.return_value = registration.json()

        discovery = ServiceDiscovery(mock_redis)

        try:
            services = await discovery.discover_services()

            assert len(services) == 1
            assert "test-service" in services
            assert services["test-service"].service_name == "test-service"
            assert services["test-service"].health.status == "healthy"

        finally:
            await discovery.close()


class TestEventBus:
    """Test EventBus functionality"""

    @pytest.mark.asyncio
    async def test_event_bus_creation(self, mock_redis, test_config):
        """Test event bus creation"""
        event_bus = EventBus(mock_redis)
        await event_bus.close()

    @pytest.mark.asyncio
    async def test_publish_event(self, mock_redis, test_config):
        """Test publishing an event"""
        event = ServiceEvent(
            event_type="test.event",
            source_service="test-service",
            timestamp=datetime.utcnow(),
            data={"test": "data"},
        )

        mock_redis.publish.return_value = 2  # 2 subscribers

        event_bus = EventBus(mock_redis)

        try:
            subscribers = await event_bus.publish(event)

            assert subscribers == 2
            assert mock_redis.publish.call_count == 2  # event channel + wildcard

        finally:
            await event_bus.close()

    @pytest.mark.asyncio
    async def test_subscribe_and_handle(self, mock_redis, test_config):
        """Test subscribing to events and handling them"""
        handled_events = []

        async def test_handler(event):
            handled_events.append(event)

        event_bus = EventBus(mock_redis)
        event_bus.subscribe("test.event", test_handler)

        # Create test event
        test_event = ServiceEvent(
            event_type="test.event",
            source_service="test-service",
            timestamp=datetime.utcnow(),
            data={"test": "data"},
        )

        # Handle the event directly (simulating received event)
        await event_bus._handle_event(test_event)

        assert len(handled_events) == 1
        assert handled_events[0].event_type == "test.event"

        await event_bus.close()


class TestModels:
    """Test data models"""

    def test_service_request_creation(self):
        """Test ServiceRequest model creation"""
        request = ServiceRequest(
            id="test-123",
            source_service="client",
            target_service="server",
            request_type="test_request",
            data={"key": "value"},
        )

        assert request.id == "test-123"
        assert request.source_service == "client"
        assert request.target_service == "server"
        assert request.request_type == "test_request"
        assert request.data == {"key": "value"}

    def test_service_response_success_property(self):
        """Test ServiceResponse success property"""
        # Successful response
        success_response = ServiceResponse(
            id="test-123", success=True, data={"result": "ok"}
        )

        assert success_response.success
        assert success_response.error is None

        # Failed response
        error_response = ServiceResponse(
            id="test-123", success=False, error="Something went wrong", data={}
        )

        assert not error_response.success
        assert error_response.error == "Something went wrong"

    def test_service_event_creation(self):
        """Test ServiceEvent model creation"""
        event = ServiceEvent(
            event_type="user.created",
            source_service="user-service",
            timestamp=datetime.utcnow(),
            data={"user_id": "123", "username": "testuser"},
        )

        assert event.event_type == "user.created"
        assert event.source_service == "user-service"
        assert isinstance(event.timestamp, datetime)
        assert event.data["user_id"] == "123"


class TestConfiguration:
    """Test configuration management"""

    def test_default_config(self):
        """Test default configuration values"""
        config = CommConfig()

        assert config.redis_url == "redis://localhost:6379"
        assert config.default_timeout == 5.0
        assert config.max_retries == 3
        assert config.enable_connection_pooling is True
        assert config.enable_metrics is True

    def test_config_from_env(self, monkeypatch):
        """Test configuration from environment variables"""
        # Set environment variables
        monkeypatch.setenv("REDIS_HOST", "test-redis")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("COMM_DEFAULT_TIMEOUT", "10.0")
        monkeypatch.setenv("COMM_MAX_RETRIES", "5")
        monkeypatch.setenv("COMM_DEBUG", "true")

        config = CommConfig.from_env()

        assert config.redis_url == "redis://test-redis:6380/0"
        assert config.default_timeout == 10.0
        assert config.max_retries == 5
        assert config.debug_mode is True


# Integration Tests
class TestIntegration:
    """Integration tests combining multiple components"""

    @pytest.mark.asyncio
    async def test_full_request_response_cycle(self, mock_redis):
        """Test complete request-response cycle"""
        # This would be a more complex integration test
        # that sets up both client and server and tests
        # the full communication cycle
        pass


if __name__ == "__main__":
    # Run tests with: python -m pytest tests.py -v
    pytest.main([__file__, "-v"])
