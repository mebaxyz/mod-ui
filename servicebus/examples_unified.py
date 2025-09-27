"""
Updated examples demonstrating the unified MicroService class
"""

import asyncio
from typing import Dict, Any
from datetime import datetime

# Import the unified service class
from servicebus import (
    Service,
    handler,
    event_handler,
    get_config,
    set_config,
    CommConfig,
)


class ExampleEffectsService:
    """Example implementation using the unified MicroService class"""

    def __init__(self):
        # Create a unified service (combines client + server)
        self.service = Service("effects-service")

        # Some sample data
        self.plugins = [
            {
                "uri": "http://example.com/plugin1",
                "name": "Reverb",
                "category": "Delay",
            },
            {
                "uri": "http://example.com/plugin2",
                "name": "Distortion",
                "category": "Distortion",
            },
        ]

        # Register our handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register request handlers"""
        self.service.register_handler(
            "get_plugins", self.get_plugins, "Get all available plugins"
        )
        self.service.register_handler(
            "get_plugin_info", self.get_plugin_info, "Get info for a specific plugin"
        )
        self.service.register_handler("load_plugin", self.load_plugin, "Load a plugin")

        # Register event handlers
        self.service.subscribe_to_event("system.shutdown", self.handle_shutdown_event)

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

    async def load_plugin(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle load_plugin request"""
        plugin_uri = data.get("uri")

        # Simulate loading a plugin
        await asyncio.sleep(0.1)

        # Publish an event when plugin is loaded
        await self.service.publish_event(
            "plugin.loaded",
            {"uri": plugin_uri, "timestamp": datetime.utcnow().isoformat()},
        )

        return {"loaded": True, "uri": plugin_uri}

    async def handle_shutdown_event(self, event):
        """Handle system shutdown event"""
        print(f"Effects service received shutdown event: {event.data}")

    async def start(self):
        """Start the service"""
        await self.service.start()

    async def stop(self):
        """Stop the service"""
        await self.service.stop()


class ExampleWebUIGateway:
    """Example WebUI Gateway using the unified MicroService class"""

    def __init__(self):
        # Create unified service (can both serve AND call other services)
        self.service = Service("webui-gateway")

        # Register our HTTP-like handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register request handlers that act like HTTP endpoints"""
        self.service.register_handler(
            "api_effect_list", self.api_effect_list, "API: Get effects list"
        )
        self.service.register_handler(
            "api_effect_info", self.api_effect_info, "API: Get effect info"
        )
        self.service.register_handler(
            "api_effect_load", self.api_effect_load, "API: Load effect"
        )

        # Subscribe to plugin events
        self.service.subscribe_to_event("plugin.loaded", self.handle_plugin_loaded)

    async def api_effect_list(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API request for effects list - calls effects service"""
        try:
            # This service both handles requests AND calls other services!
            response = await self.service.call(
                target_service="effects-service",
                request_type="get_plugins",
                timeout=5.0,
            )
            return response
        except Exception as e:
            return {"error": str(e), "plugins": []}

    async def api_effect_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API request for effect info"""
        plugin_uri = data.get("uri")
        if not plugin_uri:
            return {"error": "Missing uri parameter"}

        try:
            response = await self.service.call(
                target_service="effects-service",
                request_type="get_plugin_info",
                data={"uri": plugin_uri},
                timeout=5.0,
            )
            return response
        except Exception as e:
            return {"error": str(e), "plugin": None}

    async def api_effect_load(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API request to load effect"""
        plugin_uri = data.get("uri")
        if not plugin_uri:
            return {"error": "Missing uri parameter"}

        try:
            response = await self.service.call(
                target_service="effects-service",
                request_type="load_plugin",
                data={"uri": plugin_uri},
                timeout=10.0,
            )
            return response
        except Exception as e:
            return {"error": str(e), "loaded": False}

    async def handle_plugin_loaded(self, event):
        """Handle plugin loaded events"""
        print(f"Gateway: Plugin loaded - {event.data}")

    async def discover_services(self) -> Dict[str, Any]:
        """Discover available services"""
        return await self.service.discover_services()

    async def start(self):
        """Start the service"""
        await self.service.start()

    async def stop(self):
        """Stop the service"""
        await self.service.stop()


class ExampleWithDecorators:
    """Example service using decorators with the unified class"""

    def __init__(self):
        self.service = Service("calculator-service")

        # Auto-register handlers using decorators
        self.service.register_handlers_from_class(self)

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

        # Publish calculation event
        await self.service.publish_event(
            "calculation.performed",
            {"operation": operation, "a": a, "b": b, "result": result},
        )

        return {"result": result}

    @handler("batch_calculate", "Perform batch calculations")
    async def batch_calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform multiple calculations"""
        calculations = data.get("calculations", [])
        results = []

        for calc in calculations:
            try:
                # Call our own handler locally
                result = await self.calculate(calc)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})

        return {"results": results}

    @event_handler("calculation.requested")
    async def handle_calculation_event(self, event):
        """Handle calculation requested event"""
        print(f"Calculation requested: {event.data}")

    async def start(self):
        """Start the service"""
        await self.service.start()

    async def stop(self):
        """Stop the service"""
        await self.service.stop()


async def run_unified_example():
    """Run the unified service example"""
    print("=== Unified Service Example ===")

    # Start both services
    effects_service = ExampleEffectsService()
    gateway = ExampleWebUIGateway()

    await effects_service.start()
    await gateway.start()

    # Give services time to register
    await asyncio.sleep(1)

    try:
        # Now gateway can make calls to effects service
        # This simulates HTTP requests to the gateway

        # Discover services first
        services = await gateway.discover_services()
        print(f"Discovered services: {list(services.keys())}")

        # Get effects list (gateway calls effects service)
        effects_response = await gateway.service.call(
            target_service="webui-gateway",  # Call gateway's API handler
            request_type="api_effect_list",
        )
        print(f"Effects list: {effects_response}")

        # Get specific effect info
        if effects_response.get("plugins"):
            first_plugin = effects_response["plugins"][0]
            info_response = await gateway.service.call(
                target_service="webui-gateway",
                request_type="api_effect_info",
                data={"uri": first_plugin["uri"]},
            )
            print(f"Plugin info: {info_response}")

            # Load the plugin (triggers event)
            load_response = await gateway.service.call(
                target_service="webui-gateway",
                request_type="api_effect_load",
                data={"uri": first_plugin["uri"]},
            )
            print(f"Plugin load: {load_response}")

        # Wait for events to propagate
        await asyncio.sleep(0.5)

        # Check metrics
        effects_metrics = await effects_service.service.get_metrics()
        gateway_metrics = await gateway.service.get_metrics()
        print(f"Effects service metrics: {effects_metrics}")
        print(f"Gateway metrics: {gateway_metrics}")

    finally:
        await effects_service.stop()
        await gateway.stop()


async def run_decorator_example():
    """Run the decorator example with unified service"""
    print("\\n=== Decorator Example with Unified Service ===")

    # Start calculator service
    calc_service = ExampleWithDecorators()
    await calc_service.start()

    # Give service time to register
    await asyncio.sleep(1)

    try:
        # Perform individual calculations
        operations = [
            {"operation": "add", "a": 10, "b": 5},
            {"operation": "multiply", "a": 7, "b": 8},
            {"operation": "divide", "a": 20, "b": 4},
        ]

        for op in operations:
            result = await calc_service.service.call(
                target_service="calculator-service", request_type="calculate", data=op
            )
            print(f"{op['a']} {op['operation']} {op['b']} = {result['result']}")

        # Perform batch calculations
        batch_result = await calc_service.service.call(
            target_service="calculator-service",
            request_type="batch_calculate",
            data={"calculations": operations},
        )
        print(f"Batch results: {batch_result}")

    finally:
        await calc_service.stop()


async def run_context_manager_example():
    """Example using the service as an async context manager"""
    print("\\n=== Context Manager Example ===")

    # Use service as context manager
    async with Service("temp-service") as service:
        # Register a simple handler
        service.register_handler("ping", lambda data: {"pong": True})

        # The service is automatically started when entering context
        result = await service.call("temp-service", "ping")
        print(f"Ping result: {result}")

        # Service will be automatically stopped when exiting context


async def run_smart_call_example():
    """Example of smart calling (local vs remote)"""
    print("\\n=== Smart Call Example ===")

    # Create a service that can handle requests locally and remotely
    service = Service("smart-service")

    # Register a local handler
    service.register_handler(
        "greet", lambda data: {"message": f"Hello, {data.get('name', 'World')}!"}
    )

    await service.start()
    await asyncio.sleep(0.5)

    try:
        # Smart call will use local handler first
        result1 = await service.smart_call(
            "greet", {"name": "Alice"}, prefer_local=True
        )
        print(f"Local call result: {result1}")

        # If we had another service with the same handler, we could call it remotely too

    finally:
        await service.stop()


async def main():
    """Run all unified examples"""
    print("Unified Service Examples")
    print("========================")  # Set up configuration
    config = CommConfig()
    config.debug_mode = True
    config.log_level = "INFO"
    set_config(config)

    try:
        await run_unified_example()
        await run_decorator_example()
        await run_context_manager_example()
        await run_smart_call_example()

        print("\\n=== All Unified Examples Completed Successfully ===")

    except Exception as e:
        print(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
