"""
Integration Tests for Service Communication

These tests require a running Redis instance and test the full request-response flow.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import redis.asyncio as redis

from mod_ui.common import RequestType, ServiceClient, ServiceServer, SimpleService


class TestServiceIntegration:
    """Integration tests that would require Redis"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires Redis server")
    async def test_full_request_response_flow(self):
        """Test complete request-response flow between client and server"""
        # This would test actual Redis communication
        pass

    @pytest.mark.asyncio
    async def test_service_client_timeout(self):
        """Test ServiceClient timeout behavior"""
        client = ServiceClient(default_timeout=0.1)

        # Mock Redis to simulate no response
        with patch.object(client, "redis", AsyncMock()):
            client.redis.publish = AsyncMock()
            client.redis.pubsub = AsyncMock()

            pubsub_mock = AsyncMock()
            pubsub_mock.subscribe = AsyncMock()
            pubsub_mock.get_message = AsyncMock(return_value=None)
            pubsub_mock.unsubscribe = AsyncMock()
            client.redis.pubsub.return_value = pubsub_mock

            with pytest.raises(asyncio.TimeoutError):
                await client.make_request(
                    request_type="test_request",
                    data={},
                    service_name="test-service",
                    timeout=0.1,
                )

    @pytest.mark.asyncio
    async def test_service_server_error_handling(self):
        """Test ServiceServer error handling"""
        server = ServiceServer("test-service")

        # Register a handler that raises an exception
        async def failing_handler(request):
            raise ValueError("Test error")

        server.register_handler("failing_request", failing_handler)

        # Mock the response sending
        server._send_error_response = AsyncMock()

        # Create a mock request
        from mod_ui.common.models import ServiceRequest

        request = ServiceRequest(
            request_type="failing_request", data={}, source_service="test"
        )

        # Test that error is handled properly
        await server._handle_message(request.json().encode())

        # Verify error response was sent
        server._send_error_response.assert_called_once()


class TestSimpleServiceIntegration:
    """Integration tests for SimpleService"""

    @pytest.mark.asyncio
    async def test_simple_service_handler_execution(self):
        """Test SimpleService handler execution"""
        service = SimpleService("test-service")

        @service.handler("test_request")
        async def test_handler(request):
            return {"test": "success"}

        # Mock the underlying server
        service.server._send_success_response = AsyncMock()

        # Create mock request
        from mod_ui.common.models import ServiceRequest

        request = ServiceRequest(
            request_type="test_request", data={}, source_service="test"
        )

        # Execute handler directly
        result = await service._handlers["test_request"](request)
        assert result == {"test": "success"}

    def test_simple_service_sync_handler(self):
        """Test SimpleService with synchronous handler"""
        service = SimpleService("test-service")

        @service.handler("sync_request")
        def sync_handler(request):
            return "simple result"

        # Verify handler is registered
        assert "sync_request" in service._handlers

        # The sync handler should be wrapped properly
        handler = service._handlers["sync_request"]
        assert callable(handler)
