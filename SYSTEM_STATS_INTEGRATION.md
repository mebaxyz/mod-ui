# System Stats Service Integration

This document explains how the System Stats Service has been updated to use the new simplified service communication package.

## Architecture

The system now consists of:

1. **System Stats Service** (`src/mod_ui/services/system_stats/main.py`)
   - Uses the new `SimpleService` from `mod_ui.common`
   - Handles `GET_SYSTEM_INFO` and `get_system_stats` requests
   - Provides hardware info and real-time system statistics

2. **WebSocket Gateway** (`src/mod_ui/services/websocket_gateway/routers/system.py`)
   - Uses `ServiceClient` to communicate with the system stats service
   - Exposes REST endpoints: `/api/system/info` and `/api/system/stats`
   - Falls back to mock data if the service is unavailable

## Service Communication

### System Info Request
```python
# WebSocket Gateway makes this request:
response = await service_client.make_request(
    request_type=RequestType.GET_SYSTEM_INFO,
    data={},
    service_name="system-stats-service",
    timeout=5.0
)
```

### System Stats Request
```python
# WebSocket Gateway makes this request:
response = await service_client.make_request(
    request_type="get_system_stats", 
    data={},
    service_name="system-stats-service",
    timeout=5.0
)
```

## Available Endpoints

### GET /api/system/info
Returns comprehensive system information:
```json
{
  "hwname": "MOD Duo",
  "architecture": "armv7l", 
  "cpu": "ARM Cortex-A7",
  "platform": "modduo",
  "bin_compat": "arm-linux-gnueabihf",
  "model": "modduo",
  "sysdate": "2024-01-01",
  "python": {"version": "3.11.2"},
  "uname": {
    "machine": "armv7l",
    "release": "5.10.0", 
    "sysname": "Linux",
    "version": "#1 SMP PREEMPT"
  }
}
```

### GET /api/system/stats
Returns real-time system statistics:
```json
{
  "cpu_load": 25.5,
  "mem_usage": 45.2,
  "cpu_frequency": "1000000000",
  "cpu_temperature": "45000",
  "uptime": "12345",
  "disk_usage": 35.8,
  "timestamp": "2024-01-01T00:00:00"
}
```

## Running the Services

### Start System Stats Service
```bash
cd /home/nicolas/project/madeline/mod-ui
python -m src.mod_ui.services.system_stats.main
```

### Start WebSocket Gateway
```bash
cd /home/nicolas/project/madeline/mod-ui
python -m src.mod_ui.services.websocket_gateway.main
```

### Test the Integration
```bash
cd /home/nicolas/project/madeline/mod-ui
python test_system_stats.py
```

## Key Improvements

1. **Simplified Service Creation**: Using `SimpleService` with decorators
2. **Automatic Request Handling**: Service methods are automatically registered
3. **Type Safety**: Using `RequestType` enum and proper typing
4. **Error Handling**: Graceful fallbacks when services are unavailable
5. **Unified Communication**: All services use the same communication pattern

## Handler Methods

The system stats service provides these handlers:

- `@service.enum_handler(RequestType.GET_SYSTEM_INFO)` - System hardware info
- `@service.handler("get_system_stats")` - Real-time system statistics

Both methods are automatically registered and handle requests from other services.