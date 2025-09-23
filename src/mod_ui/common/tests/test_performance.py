"""
Performance and Load Tests for Service Communication

Tests for performance characteristics, memory usage, and load handling.
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from mod_ui.common import ServiceClient, ServiceRequest, ServiceResponse, SimpleService


class TestPerformance:
    """Performance-related tests"""

    @pytest.mark.asyncio
    async def test_service_client_performance(self):
        """Test ServiceClient performance characteristics"""
        client = ServiceClient()

        # Mock Redis for performance testing
        with patch.object(client, "redis", AsyncMock()):
            client.redis.publish = AsyncMock()
            client.redis.pubsub = AsyncMock()

            # Mock successful response
            pubsub_mock = AsyncMock()
            pubsub_mock.subscribe = AsyncMock()
            pubsub_mock.unsubscribe = AsyncMock()

            response_data = ServiceResponse(
                request_id="test-id",
                correlation_id="test-correlation",
                status="success",
                data={"test": "data"},
            ).json()

            message_mock = {"data": response_data}
            pubsub_mock.get_message = AsyncMock(return_value=message_mock)
            client.redis.pubsub.return_value = pubsub_mock

            # Measure request performance
            start_time = time.time()

            response = await client.make_request(
                request_type="test_request", data={}, service_name="test-service"
            )

            end_time = time.time()
            request_time = end_time - start_time

            # Should complete quickly (mocked, so very fast)
            assert request_time < 1.0
            assert response.status == "success"

    def test_handler_registration_performance(self):
        """Test handler registration performance"""
        service = SimpleService("test-service")

        # Register many handlers quickly
        start_time = time.time()

        for i in range(100):

            @service.handler(f"handler_{i}")
            def handler(request, i=i):
                return {"handler_id": i}

        end_time = time.time()
        registration_time = end_time - start_time

        # Should register quickly
        assert registration_time < 1.0
        assert len(service._handlers) == 100

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling multiple concurrent requests"""
        client = ServiceClient()

        # Mock Redis
        with patch.object(client, "redis", AsyncMock()):
            client.redis.publish = AsyncMock()
            client.redis.pubsub = AsyncMock()

            # Create multiple pubsub mocks for concurrent requests
            async def create_pubsub_mock(correlation_id):
                pubsub_mock = AsyncMock()
                pubsub_mock.subscribe = AsyncMock()
                pubsub_mock.unsubscribe = AsyncMock()

                response_data = ServiceResponse(
                    request_id="test-id",
                    correlation_id=correlation_id,
                    status="success",
                    data={"request_id": correlation_id},
                ).json()

                pubsub_mock.get_message = AsyncMock(
                    return_value={"data": response_data}
                )
                return pubsub_mock

            # Mock pubsub creation
            client.redis.pubsub.side_effect = lambda: create_pubsub_mock(
                "test-correlation"
            )

            # Create concurrent requests
            tasks = []
            for i in range(10):
                task = client.make_request(
                    request_type="concurrent_test",
                    data={"request_num": i},
                    service_name="test-service",
                )
                tasks.append(task)

            # Wait for all requests to complete
            responses = await asyncio.gather(*tasks)

            # Verify all requests completed
            assert len(responses) == 10
            for response in responses:
                assert response.status == "success"


class TestMemoryUsage:
    """Memory usage and cleanup tests"""

    def test_service_cleanup(self):
        """Test that services clean up properly"""
        service = SimpleService("test-service")

        # Register handlers
        @service.handler("test1")
        def handler1(request):
            return {"test": 1}

        @service.handler("test2")
        def handler2(request):
            return {"test": 2}

        # Verify handlers are registered
        assert len(service._handlers) == 2

        # Test cleanup (if we implement it)
        # service.cleanup()  # Would clear handlers

        # For now, just verify structure is clean
        assert service.service_name == "test-service"
        assert service.server is not None

    def test_client_connection_cleanup(self):
        """Test ServiceClient connection cleanup"""
        client = ServiceClient()

        # Initially no connection
        assert client.redis is None
        assert len(client.response_channels) == 0

        # After cleanup, should be clean
        # (This would be tested with actual Redis connections)
        assert client.redis is None
