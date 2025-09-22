# Session Service v2 Documentation

## Overview

The Session Service v2 is a modern FastAPI-based service that provides comprehensive session management for MOD UI. This service handles all aspects of session state, pedalboard management, transport control, and real-time communication with clients.

## Architecture

### Service Design

The Session Service v2 follows a modular microservices architecture:

- **FastAPI Framework**: Modern async/await web framework with automatic API documentation
- **WebSocket Hub**: Real-time bidirectional communication with web clients
- **Event Bus System**: Redis-based pub/sub for inter-service communication
- **State Manager**: Central session state management with persistence
- **HTTP Client/Adapter**: Backward compatibility layer for existing MOD UI integration

### Key Features

- **Async/Await Throughout**: Non-blocking I/O for high performance
- **Real-time WebSocket Communication**: Live session state updates
- **Event-Driven Architecture**: Loose coupling between services
- **Backward Compatibility**: Seamless integration with existing MOD UI
- **Type Safety**: Pydantic models for data validation
- **Health Monitoring**: Comprehensive service health checks
- **Docker Ready**: Containerized deployment with orchestration

## API Documentation

### Base URL

```
http://localhost:8002
```

### Health Endpoints

#### GET /ping
Quick health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "session-v2"
}
```

#### GET /status
Detailed service status information.

**Response:**
```json
{
  "service": "session-v2",
  "version": "2.0.0",
  "status": "running",
  "state_manager": "active",
  "websocket_clients": 2,
  "event_bus": "active"
}
```

### Session Management

#### GET /api/session/status
Get current session status and configuration.

**Response:**
```json
{
  "success": true,
  "session": {
    "transport_state": "stopped",
    "tempo_bpm": 120.0,
    "sample_rate": 48000,
    "buffer_size": 256,
    "audio_driver": "jack",
    "cpu_load": 12.5,
    "xrun_count": 0,
    "uptime_seconds": 3600,
    "created_at": "2025-09-22T10:30:00Z",
    "modified_at": "2025-09-22T10:45:00Z"
  }
}
```

#### POST /api/session/reset
Reset session to initial state.

**Response:**
```json
{
  "success": true,
  "message": "Session reset successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Transport Control

#### POST /api/session/transport/play
Start transport playback.

**Response:**
```json
{
  "success": true,
  "transport_state": "playing",
  "message": "Transport started"
}
```

#### POST /api/session/transport/stop
Stop transport playback.

#### POST /api/session/transport/pause
Pause transport playback.

#### POST /api/session/tempo
Set session tempo.

**Request Body:**
```json
{
  "bpm": 140.0
}
```

**Response:**
```json
{
  "success": true,
  "tempo_bpm": 140.0,
  "message": "Tempo set to 140.0 BPM"
}
```

### Pedalboard Management

#### GET /api/pedalboard/list
List all available pedalboards.

**Response:**
```json
{
  "success": true,
  "pedalboards": [
    {
      "bundle_path": "/app/data/pedalboards/my_board.pedalboard",
      "title": "My Board",
      "description": "A sample pedalboard",
      "author": "User",
      "plugin_count": 3,
      "connection_count": 2,
      "created_at": "2025-09-22T10:00:00Z",
      "modified_at": "2025-09-22T10:30:00Z"
    }
  ],
  "count": 1
}
```

#### GET /api/pedalboard/current
Get currently loaded pedalboard.

#### POST /api/pedalboard/create
Create a new empty pedalboard.

**Request Body:**
```json
{
  "title": "New Pedalboard",
  "description": "Optional description"
}
```

#### POST /api/pedalboard/load/{bundle_path}
Load a pedalboard from file system.

#### POST /api/pedalboard/save
Save current pedalboard.

### Plugin Management

#### POST /api/pedalboard/plugin/add
Add a plugin to the current pedalboard.

**Request Body:**
```json
{
  "instance_id": "plugin_1",
  "plugin_uri": "http://example.com/plugins/reverb",
  "x": 100.0,
  "y": 200.0,
  "enabled": true
}
```

#### DELETE /api/pedalboard/plugin/{instance_id}
Remove a plugin from the current pedalboard.

#### PATCH /api/pedalboard/plugin/{instance_id}/parameter/{parameter_symbol}
Set a plugin parameter value.

**Request Body:**
```json
{
  "value": 0.75
}
```

### Connection Management

#### POST /api/pedalboard/connection/add
Add a connection between plugin ports.

**Request Body:**
```json
{
  "source_port": "plugin_1/output",
  "destination_port": "plugin_2/input"
}
```

#### DELETE /api/pedalboard/connection/remove
Remove a connection between plugin ports.

### WebSocket Communication

#### WebSocket: /ws
Real-time bidirectional communication endpoint.

**Connection Flow:**
1. Client connects to WebSocket endpoint
2. Server sends initialization sequence
3. Client can subscribe to event types
4. Server broadcasts events to subscribed clients

**Message Types:**

**Subscribe to Events:**
```json
{
  "type": "subscribe",
  "event_types": ["plugin_added", "parameter_changed"]
}
```

**Event Broadcast:**
```json
{
  "type": "event",
  "event": {
    "event_id": "uuid",
    "event_type": "plugin_added",
    "source_service": "state_manager",
    "session_id": "session-uuid",
    "timestamp": "2025-09-22T10:30:00Z",
    "data": {
      "instance_id": "plugin_1",
      "plugin_uri": "http://example.com/plugins/reverb"
    }
  }
}
```

## Deployment

### Docker Deployment

The Session Service v2 is designed for containerized deployment using Docker Compose.

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_SERVICE_HOST` | `0.0.0.0` | Service bind address |
| `SESSION_SERVICE_PORT` | `8002` | Service port |
| `EVENT_BUS_TYPE` | `inmemory` | Event bus type (`inmemory` or `redis`) |
| `REDIS_HOST` | `localhost` | Redis server host |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_DB` | `0` | Redis database number |
| `MOD_DATA_DIR` | `/app/data` | Data directory for persistence |

#### Docker Compose

```yaml
services:
  mod-session-v2:
    build:
      context: ..
      dockerfile: docker/session_v2/Dockerfile
    container_name: mod-ui-session-v2
    restart: unless-stopped
    ports:
      - "8002:8002"
    volumes:
      - mod-data:/app/data
    environment:
      - EVENT_BUS_TYPE=redis
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/ping"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Development Setup

1. **Install Dependencies:**
   ```bash
   pip install fastapi uvicorn websockets redis pydantic
   ```

2. **Start Redis (if using Redis event bus):**
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

3. **Run Service:**
   ```bash
   cd /path/to/mod-ui
   export PYTHONPATH=/path/to/mod-ui/src:/path/to/mod-ui
   python -m src.mod_ui.services.session_v2.main
   ```

4. **Access API Documentation:**
   - Open http://localhost:8002/docs for Swagger UI
   - Open http://localhost:8002/redoc for ReDoc

## Integration

### MOD UI Integration

The Session Service v2 integrates with existing MOD UI through the session adapter pattern:

#### Using the Session Adapter

```python
from mod.session_adapter import get_session_adapter

# Get adapter instance
adapter = get_session_adapter()

# Check if service is available
if adapter.is_service_available():
    # Use modern service
    result = adapter.get_session_status()
else:
    # Falls back to legacy implementation
    pass
```

#### Environment Configuration

Enable session service integration:

```bash
export MOD_USE_SESSION_SERVICE=1
export MOD_SESSION_SERVICE_URL=http://localhost:8002
```

### HTTP Client Usage

```python
from mod.session_client import get_session_client

client = get_session_client()

# Check service health
if client.is_service_healthy():
    # Perform operations
    status = client.get_session_status()
    client.set_tempo(140.0)
    client.transport_play()
```

## Event System

### Event Types

The service publishes various event types through the event bus:

- **Session Events**: `session_started`, `session_reset`, `session_transport_changed`
- **Pedalboard Events**: `pedalboard_loaded`, `pedalboard_saved`, `pedalboard_changed`
- **Plugin Events**: `plugin_added`, `plugin_removed`, `parameter_changed`
- **Connection Events**: `connection_added`, `connection_removed`
- **Client Events**: `client_connected`, `client_disconnected`

### Event Structure

All events follow a consistent structure:

```python
{
    "event_id": "uuid",
    "event_type": "event_name",
    "source_service": "service_name",
    "session_id": "session_uuid",
    "timestamp": "ISO8601_timestamp",
    "priority": "normal",
    "data": {
        # Event-specific data
    },
    "target_clients": ["client_id"]  # Optional, None = broadcast
}
```

## Monitoring and Debugging

### Health Checks

The service provides comprehensive health monitoring:

- **Service Health**: `/ping` and `/status` endpoints
- **Component Status**: State manager, WebSocket hub, event bus status
- **Client Monitoring**: Connected WebSocket client count
- **Docker Health Checks**: Automated container health monitoring

### Logging

The service uses Python's logging framework with configurable levels:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Log categories:
- `session_v2.main`: Service startup/shutdown
- `session_v2.state_manager`: Session state operations
- `session_v2.websocket_hub`: WebSocket communication
- `session_v2.event_bus`: Event publishing/subscription

### Performance Monitoring

Monitor key metrics:
- WebSocket client count
- Event processing latency
- Memory usage for session state
- Redis connection health (if using Redis event bus)

## Troubleshooting

### Common Issues

#### Service Won't Start

1. Check port availability: `netstat -an | grep 8002`
2. Verify Python dependencies: `pip list | grep fastapi`
3. Check Redis connectivity (if using Redis event bus)
4. Review logs for error messages

#### WebSocket Connection Failures

1. Verify service is running: `curl http://localhost:8002/ping`
2. Check client WebSocket URL
3. Review browser console for WebSocket errors
4. Monitor WebSocket client count in service logs

#### Event Bus Issues

1. **In-Memory Event Bus**: Check for memory leaks in long-running processes
2. **Redis Event Bus**: Verify Redis server connectivity and version compatibility

#### Backward Compatibility Problems

1. Verify adapter configuration: `MOD_USE_SESSION_SERVICE=1`
2. Check service URL configuration
3. Test fallback behavior when service is unavailable

### Development Tips

1. **Use Development Mode**: Set `MOD_DEV_ENVIRONMENT=1` for detailed logging
2. **API Documentation**: Access `/docs` endpoint for interactive API testing
3. **WebSocket Testing**: Use browser developer tools or WebSocket client tools
4. **Event Monitoring**: Subscribe to all events for debugging: `{"type": "subscribe", "event_types": ["*"]}`

## API Reference

For complete API documentation with interactive testing, visit:
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

The FastAPI framework automatically generates comprehensive API documentation based on the service implementation.