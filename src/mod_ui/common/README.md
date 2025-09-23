# MOD UI Common Service Communication Package

This package provides reusable components for inter-service communication across MOD UI microservices.

## Features

- **Service Communication Models**: Standardized request/response models for service interactions
- **Service Client**: Async Redis-based client for making requests to backend services
- **Service Server**: Async Redis-based server for handling incoming requests from other services
- **Request-Response Pattern**: Correlation ID-based communication with timeout handling

## Usage

### Basic Usage

#### Making Requests (Client Side)

```python
from mod_ui.common import ServiceClient, RequestType

async with ServiceClient() as client:
    response = await client.make_request(
        request_type=RequestType.GET_SYSTEM_INFO,
        data={},
        service_name="system-service"
    )

    if response.status == "success":
        print("System info:", response.data)
    else:
        print("Error:", response.error_message)
```

#### Handling Requests (Server Side)

```python
from mod_ui.common import ServiceServer, ServiceRequest, RequestType

async def handle_system_info(request: ServiceRequest) -> dict:
    """Handle system info requests"""
    return {
        "hwname": "MOD Device",
        "architecture": "armv7l",
        "python": {"version": "3.11.2"}
    }

async def main():
    server = ServiceServer(service_name="system-service")
    server.register_handler(RequestType.GET_SYSTEM_INFO, handle_system_info)
    
    async with server:
        # Service is now listening for requests
        while True:
            await asyncio.sleep(1)
```

### Service Request Types

The package includes predefined request types:

- `GET_SYSTEM_INFO`: Get system hardware/software information
- `GET_SYSTEM_STATS`: Get system performance statistics
- `GET_HARDWARE_STATUS`: Get hardware status
- `LOAD_PEDALBOARD`: Load a pedalboard configuration
- `SAVE_PEDALBOARD`: Save a pedalboard configuration
- `GET_PLUGIN_INFO`: Get plugin information
- `EXECUTE_COMMAND`: Execute a system command
- `GET_SESSION_STATE`: Get current session state
- `UPDATE_SESSION_STATE`: Update session state
- `GET_AUDIO_STATUS`: Get audio system status
- `CONTROL_TRANSPORT`: Control audio transport (play/pause/stop)

### Custom Request Types

You can also use custom request types by passing strings:

```python
response = await client.make_request(
    request_type="custom_action",
    data={"param": "value"},
    service_name="my-service"
)
```

## Architecture

The communication uses Redis pub/sub with the following pattern:

1. **Request Channel**: `service:{service_name}:requests`
2. **Response Channel**: `responses:{correlation_id}`

Each request gets a unique correlation ID for tracking responses. The client handles timeouts and automatically cleans up response channels.

## Dependencies

- `pydantic`: For data validation and serialization
- `redis`: For Redis async client

## Error Handling

The client handles common error scenarios:

- **Timeout**: Request exceeds the specified timeout
- **Service Unavailable**: Target service is not responding
- **Parse Errors**: Invalid response format
- **Connection Errors**: Redis connection issues

All errors are logged and raised as appropriate exceptions.

## Examples

The `examples/` directory contains comprehensive examples demonstrating different usage patterns:

- **examples/example.py** - Basic client usage
- **examples/simple_example.py** - Simplified server with decorators ⭐
- **examples/multi_service_example.py** - Multiple services in one app
- **examples/auto_example.py** - Auto-registration patterns
- **examples/example_server.py** - Original verbose API (for comparison)

See `examples/README.md` for detailed documentation and running instructions.