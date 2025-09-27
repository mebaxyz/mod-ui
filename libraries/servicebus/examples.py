"""
Examples demonstrating how to use the servicebus package
"""

import asyncio
from typing import Dict, Any
from datetime import datetime

# Import the microservice_comm package
from servicebus import (
    ServiceClient, ServiceServer, ServiceDiscovery, EventBus,
    ServiceEvent, MetricsCollector, get_config, set_config, CommConfig
)
from servicebus.server import handler, event_handler


class ExampleEffectsService:
    """Example implementation of an effects service"""
    
    def __init__(self):
        self.server = ServiceServer("effects-service")
        self.plugins = [
            {"uri": "http://example.com/plugin1", "name": "Reverb", "category": "Delay"},
            {"uri": "http://example.com/plugin2", "name": "Distortion", "category": "Distortion"},
        ]
    
    async def start(self):
        """Start the effects service"""
        # Register handlers
        self.server.register_handler("get_plugins", self.get_plugins, "Get all available plugins")
        self.server.register_handler("get_plugin_info", self.get_plugin_info, "Get info for a specific plugin")
        
        # Start the server
        await self.server.start()
    
    async def get_plugins(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_plugins request"""
        return {"plugins": self.plugins}
    
    async def get_plugin_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_plugin_info request"""
        plugin_uri = data.get("uri")
        for plugin in self.plugins:
            if plugin["uri"] == plugin_uri:
                return {"plugin": plugin}
        
        raise ValueError(f"Plugin not found: {plugin_uri}")
    
    async def stop(self):
        """Stop the effects service"""
        await self.server.stop()


class ExampleWebUIGateway:
    """Example implementation of a WebUI Gateway that calls other services"""
    
    def __init__(self):
        self.client = ServiceClient("webui-gateway")
        self.discovery = ServiceDiscovery()
    
    async def get_all_plugins(self) -> Dict[str, Any]:
        """Get plugins from effects service"""
        try:
            response = await self.client.call(
                target_service="effects-service",
                request_type="get_plugins",
                timeout=5.0
            )
            return response
        except Exception as e:
            return {"error": str(e), "plugins": []}
    
    async def get_plugin_details(self, plugin_uri: str) -> Dict[str, Any]:
        """Get details for a specific plugin"""
        try:
            response = await self.client.call(
                target_service="effects-service",
                request_type="get_plugin_info",
                data={"uri": plugin_uri},
                timeout=5.0
            )
            return response
        except Exception as e:
            return {"error": str(e), "plugin": None}
    
    async def discover_services(self) -> Dict[str, Any]:
        """Discover available services"""
        services = await self.discovery.discover_services()
        return {
            "services": {
                name: {
                    "status": reg.health.status,
                    "capabilities": [cap.request_type for cap in reg.capabilities]
                }
                for name, reg in services.items()
            }
        }
    
    async def close(self):
        """Close connections"""
        await self.client.close()
        await self.discovery.close()


class ExampleEventService:
    """Example service that publishes and subscribes to events"""
    
    def __init__(self):
        self.server = ServiceServer("event-service")
        self.event_bus = EventBus()
        self.processed_events = []
    
    async def start(self):
        """Start the event service"""
        # Register request handlers
        self.server.register_handler("trigger_event", self.trigger_event, "Trigger a custom event")
        self.server.register_handler("get_processed_events", self.get_processed_events, "Get list of processed events")
        
        # Register event handlers
        self.event_bus.subscribe("user.created", self.handle_user_created)
        self.event_bus.subscribe("plugin.activated", self.handle_plugin_activated)
        self.event_bus.subscribe("*", self.handle_all_events)  # Wildcard handler
        
        # Start listening for events
        await self.event_bus.start_listening()
        
        # Start the server
        await self.server.start()
    
    async def trigger_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a custom event"""
        event = ServiceEvent(
            event_type=data.get("event_type", "custom.event"),
            source_service="event-service",
            timestamp=datetime.utcnow(),
            data=data.get("event_data", {})
        )
        
        subscribers = await self.event_bus.publish(event)
        return {"event_published": True, "subscribers": subscribers}
    
    async def get_processed_events(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of processed events"""
        return {"processed_events": self.processed_events}
    
    async def handle_user_created(self, event: ServiceEvent):
        """Handle user created event"""
        self.processed_events.append({
            "type": "user_created",
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.data.get("user_id")
        })
        print(f"User created: {event.data.get('user_id')}")
    
    async def handle_plugin_activated(self, event: ServiceEvent):
        """Handle plugin activated event"""
        self.processed_events.append({
            "type": "plugin_activated", 
            "timestamp": event.timestamp.isoformat(),
            "plugin_uri": event.data.get("plugin_uri")
        })
        print(f"Plugin activated: {event.data.get('plugin_uri')}")
    
    async def handle_all_events(self, event: ServiceEvent):
        """Handle all events (wildcard handler)"""
        print(f"Received event: {event.event_type} from {event.source_service}")
    
    async def stop(self):
        """Stop the event service"""
        await self.event_bus.close()
        await self.server.stop()


class ExampleWithDecorators:
    """Example service using decorators for handlers"""
    
    def __init__(self):
        from servicebus.server import ServiceServerBuilder
        
        self.builder = ServiceServerBuilder("decorator-service")
        self.server = self.builder.register_handlers_from_class(self).build()
    
    @handler("calculate", "Perform mathematical calculations")
    async def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate mathematical expressions"""
        operation = data.get("operation", "add")
        a = data.get("a", 0)
        b = data.get("b", 0)
        
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Cannot divide by zero")
            result = a / b
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        return {"result": result}
    
    @event_handler("calculation.requested")
    async def handle_calculation_event(self, event: ServiceEvent):
        """Handle calculation requested event"""
        print(f"Calculation requested: {event.data}")
    
    async def start(self):
        """Start the decorated service"""
        await self.server.start()
    
    async def stop(self):
        """Stop the decorated service"""
        await self.server.stop()


async def run_basic_example():
    """Run a basic client-server example"""
    print("=== Basic Client-Server Example ===")
    
    # Start effects service
    effects_service = ExampleEffectsService()
    await effects_service.start()
    
    # Give service time to register
    await asyncio.sleep(1)
    
    # Create gateway and make requests
    gateway = ExampleWebUIGateway()
    
    try:
        # Get all plugins
        plugins_response = await gateway.get_all_plugins()
        print(f"Plugins response: {plugins_response}")
        
        # Get specific plugin info
        if plugins_response.get("plugins"):
            first_plugin = plugins_response["plugins"][0]
            plugin_info = await gateway.get_plugin_details(first_plugin["uri"])
            print(f"Plugin info: {plugin_info}")
        
        # Discover services
        services = await gateway.discover_services()
        print(f"Discovered services: {services}")
        
    finally:
        await gateway.close()
        await effects_service.stop()


async def run_event_example():
    """Run an event-driven example"""
    print("\\n=== Event-Driven Example ===")
    
    # Start event service
    event_service = ExampleEventService()
    await event_service.start()
    
    # Give service time to start
    await asyncio.sleep(1)
    
    # Create client to trigger events
    client = ServiceClient("test-client")
    
    try:
        # Trigger a user creation event
        await client.call(
            target_service="event-service",
            request_type="trigger_event",
            data={
                "event_type": "user.created",
                "event_data": {"user_id": "user123", "username": "testuser"}
            }
        )
        
        # Trigger a plugin activation event
        await client.call(
            target_service="event-service",
            request_type="trigger_event",
            data={
                "event_type": "plugin.activated",
                "event_data": {"plugin_uri": "http://example.com/plugin1"}
            }
        )
        
        # Give events time to process
        await asyncio.sleep(1)
        
        # Get processed events
        processed = await client.call(
            target_service="event-service",
            request_type="get_processed_events"
        )
        print(f"Processed events: {processed}")
        
    finally:
        await client.close()
        await event_service.stop()


async def run_decorator_example():
    """Run an example using decorators"""
    print("\\n=== Decorator Example ===")
    
    # Start decorated service
    calc_service = ExampleWithDecorators()
    await calc_service.start()
    
    # Give service time to register
    await asyncio.sleep(1)
    
    # Create client for calculations
    client = ServiceClient("calc-client")
    
    try:
        # Perform calculations
        operations = [
            {"operation": "add", "a": 10, "b": 5},
            {"operation": "multiply", "a": 7, "b": 8},
            {"operation": "divide", "a": 20, "b": 4},
        ]
        
        for op in operations:
            result = await client.call(
                target_service="decorator-service",
                request_type="calculate",
                data=op
            )
            print(f"{op['a']} {op['operation']} {op['b']} = {result['result']}")
        
    finally:
        await client.close()
        await calc_service.stop()


async def run_metrics_example():
    """Run a metrics collection example"""
    print("\\n=== Metrics Example ===")
    
    # Configure metrics
    config = CommConfig()
    config.enable_metrics = True
    config.metrics_retention_seconds = 300  # 5 minutes
    set_config(config)
    
    # Start metrics collector
    metrics = MetricsCollector()
    await metrics.start_collecting()
    
    # Start a simple service
    effects_service = ExampleEffectsService()
    await effects_service.start()
    
    # Give service time to register
    await asyncio.sleep(1)
    
    # Make several requests to generate metrics
    client = ServiceClient("metrics-test-client")
    
    try:
        for i in range(10):
            await client.call(
                target_service="effects-service",
                request_type="get_plugins",
                timeout=2.0
            )
            await asyncio.sleep(0.1)
        
        # Get service metrics
        service_metrics = await metrics.get_service_metrics("effects-service")
        print(f"Effects service metrics: {service_metrics}")
        
        # Get system metrics
        system_metrics = await metrics.get_system_metrics()
        print(f"System metrics: {system_metrics}")
        
        # Export metrics in different formats
        json_metrics = await metrics.export_metrics("json")
        print(f"JSON metrics (first 200 chars): {json_metrics[:200]}...")
        
    finally:
        await client.close()
        await effects_service.stop()
        await metrics.close()


async def main():
    """Run all examples"""
    print("ServiceBus Package Examples")
    print("==============================")
    
    # Set up configuration
    config = CommConfig()
    config.debug_mode = True
    config.log_level = "INFO"
    set_config(config)
    
    try:
        await run_basic_example()
        await run_event_example()
        await run_decorator_example()
        await run_metrics_example()
        
        print("\\n=== All Examples Completed Successfully ===")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())