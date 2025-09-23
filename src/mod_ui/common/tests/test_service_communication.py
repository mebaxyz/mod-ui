"""
Tests for the Common Service Communication Package
"""

import pytest
from mod_ui.common.models import (
    RequestType,
    ResponseStatus,
    ServiceRequest,
    ServiceResponse,
    ServiceConfig,
)


class TestServiceModels:
    """Test the service communication models"""

    def test_request_type_enum(self):
        """Test RequestType enum values"""
        assert RequestType.GET_SYSTEM_INFO == "get_system_info"
        assert RequestType.GET_SESSION_STATE == "get_session_state"
        assert RequestType.CONTROL_TRANSPORT == "control_transport"

    def test_response_status_enum(self):
        """Test ResponseStatus enum values"""
        assert ResponseStatus.SUCCESS == "success"
        assert ResponseStatus.ERROR == "error"
        assert ResponseStatus.TIMEOUT == "timeout"

    def test_service_request_creation(self):
        """Test ServiceRequest model creation"""
        request = ServiceRequest(
            request_type=RequestType.GET_SYSTEM_INFO,
            data={"test": "data"},
            source_service="test-service"
        )

        assert request.request_type == RequestType.GET_SYSTEM_INFO
        assert request.data == {"test": "data"}
        assert request.source_service == "test-service"
        assert request.request_id is not None
        assert request.correlation_id is not None

    def test_service_response_creation(self):
        """Test ServiceResponse model creation"""
        response = ServiceResponse(
            request_id="test-request-id",
            correlation_id="test-correlation-id",
            status=ResponseStatus.SUCCESS,
            data={"result": "success"}
        )

        assert response.request_id == "test-request-id"
        assert response.correlation_id == "test-correlation-id"
        assert response.status == ResponseStatus.SUCCESS
        assert response.data == {"result": "success"}

    def test_service_config_creation(self):
        """Test ServiceConfig model creation"""
        config = ServiceConfig(
            service_name="test-service",
            request_channel="service:test-service:requests"
        )

        assert config.service_name == "test-service"
        assert config.request_channel == "service:test-service:requests"
        assert config.response_timeout == 5.0
        assert config.retry_attempts == 1
        assert config.enabled is True


class TestServiceClient:
    """Test the ServiceClient (basic functionality)"""

    @pytest.mark.asyncio
    async def test_client_creation(self):
        """Test ServiceClient can be created"""
        from mod_ui.common.client import ServiceClient

        client = ServiceClient()
        assert client.redis_url == "redis://localhost:6379"
        assert client.default_timeout == 5.0
        assert client.max_retries == 1
        assert client.redis is None

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test ServiceClient can be used as context manager"""
        from mod_ui.common.client import ServiceClient

        async with ServiceClient() as client:
            assert client is not None
            # Note: We don't test actual Redis connection here
            # as it would require a running Redis instance


class TestServiceServer:
    """Test the ServiceServer (basic functionality)"""

    @pytest.mark.asyncio
    async def test_server_creation(self):
        """Test ServiceServer can be created"""
        from mod_ui.common.server import ServiceServer

        server = ServiceServer(service_name="test-service")
        assert server.service_name == "test-service"
        assert server.redis_url == "redis://localhost:6379"
        assert server.redis is None
        assert server.running is False
        assert len(server.handlers) == 0

    @pytest.mark.asyncio
    async def test_handler_registration(self):
        """Test handler registration"""
        from mod_ui.common.server import ServiceServer

        async def dummy_handler(request):
            return {"result": "test"}

        server = ServiceServer(service_name="test-service")
        server.register_handler("test_request", dummy_handler)
        
        assert "test_request" in server.handlers
        assert server.handlers["test_request"] == dummy_handler

    @pytest.mark.asyncio
    async def test_server_context_manager(self):
        """Test ServiceServer can be used as context manager"""
        from mod_ui.common.server import ServiceServer

        server = ServiceServer(service_name="test-service")
        
        # Note: We don't actually start the server here as it would
        # require a running Redis instance, but we can test the structure
        assert server is not None


class TestSimplifiedAPI:
    """Test the simplified API components"""

    def test_simple_service_creation(self):
        """Test SimpleService can be created"""
        from mod_ui.common.decorators import SimpleService

        service = SimpleService("test-service")
        assert service.service_name == "test-service"
        assert len(service._handlers) == 0

    def test_handler_decorator(self):
        """Test handler decorator registration"""
        from mod_ui.common.decorators import SimpleService

        service = SimpleService("test-service")
        
        @service.handler("test_request")
        async def test_handler(request):
            return {"result": "test"}

        assert "test_request" in service._handlers
        assert service._handlers["test_request"] == test_handler

    def test_service_registry(self):
        """Test ServiceRegistry functionality"""
        from mod_ui.common.decorators import ServiceRegistry

        registry = ServiceRegistry()
        assert len(registry.services) == 0

        service = registry.create_service("test-service")
        assert len(registry.services) == 1
        assert "test-service" in registry.services

    def test_service_handler_decorator(self):
        """Test standalone service_handler decorator"""
        from mod_ui.common.decorators import service_handler

        @service_handler("test_type")
        def handler_func(request):
            return {"test": True}

        assert hasattr(handler_func, '_service_handler')
        assert handler_func._request_type == "test_type"