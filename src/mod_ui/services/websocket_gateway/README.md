# WebSocket Gateway Service

A dedicated microservice for managing real-time WebSocket connections and event distribution across all MOD UI services.

## Overview

The WebSocket Gateway Service acts as a central hub for real-time communication, providing:

- **Centralized WebSocket Management**: Single point for all client WebSocket connections
- **Event Distribution**: Routes events from Redis to subscribed WebSocket clients  
- **Subscription Management**: Clients can subscribe/unsubscribe to specific event types
- **Scalable Architecture**: Handles multiple concurrent connections efficiently
- **Backward Compatibility**: Supports legacy WebSocket message formats

## Architecture

```
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────┐
│   Web Clients   │    │  WebSocket Gateway  │    │  Other Services │
│                 │    │                     │    │                 │
│  ┌─────────────┐│    │  ┌─────────────────┐│    │  ┌─────────────┐│
│  │   Browser   ││◄──►│  │ Connection Mgr  ││    │  │  Session v2 ││
│  │ WebSocket   ││    │  │                 ││    │  │             ││
│  └─────────────┘│    │  └─────────────────┘│    │  └─────────────┘│
│                 │    │  ┌─────────────────┐│    │  ┌─────────────┐│
│  ┌─────────────┐│    │  │  Event Router   ││◄──►│  │  Hardware   ││
│  │   Mobile    ││◄──►│  │                 ││    │  │             ││
│  │    App      ││    │  └─────────────────┘│    │  └─────────────┘│
│  └─────────────┘│    │  ┌─────────────────┐│    │  ┌─────────────┐│
│                 │    │  │ Redis Subscriber││    │  │System Stats ││
└─────────────────┘    │  │                 ││    │  │             ││
                       │  └─────────────────┘│    │  └─────────────┘│
                       └─────────────────────┘    └─────────────────┘
                                 ▲                          │
                                 │                          │
                       ┌─────────▼─────────┐                │
                       │                   │◄───────────────┘
                       │      Redis        │
                       │   (Event Bus)     │
                       │                   │
                       └───────────────────┘
```

## Features

### Connection Management
- WebSocket connection lifecycle management
- Client identification and tracking
- Connection health monitoring and cleanup
- Rate limiting and connection limits
- Heartbeat/ping-pong for connection validation

### Event Routing  
- Redis pub/sub event subscription
- Event filtering and transformation
- Priority-based event processing
- Batch processing for efficiency
- Event type validation and routing

### Subscription System
- Per-client event type subscriptions
- Dynamic subscribe/unsubscribe operations
- Event group subscriptions (e.g., "session", "hardware")
- Wildcard subscriptions (subscribe to all events)
- Subscription confirmation and management

### Real-time Communication
- Immediate event delivery to subscribed clients
- Broadcast capabilities for system-wide events
- Targeted messaging to specific clients
- Message queuing for offline clients
- WebSocket message type standardization

## API Endpoints

### HTTP Endpoints

#### `GET /ping`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "websocket-gateway"
}
```

#### `GET /status`
Detailed service status and statistics.

**Response:**
```json
{
  "service": "websocket-gateway",
  "version": "1.0.0", 
  "status": "running",
  "timestamp": "2024-01-15T10:30:00Z",
  "total_connections": 5,
  "active_connections": 3,
  "total_messages_sent": 1250,
  "total_messages_received": 890,
  "events_processed": 2140,
  "active_subscriptions": 45,
  "redis_connected": true
}
```

#### `GET /connections`
List all active WebSocket connections.

**Response:**
```json
{
  "success": true,
  "connections": [
    {
      "client_id": "uuid-123",
      "connected_at": 1642234800.0,
      "subscriptions": ["session_transport_changed", "pedalboard_loaded"],
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0..."
    }
  ],
  "count": 1
}
```

#### `POST /broadcast`
Broadcast message to all connected clients.

**Request:**
```json
{
  "type": "announcement",
  "message": "System maintenance in 10 minutes",
  "priority": "high"
}
```

#### `POST /broadcast/{event_type}`
Broadcast message to clients subscribed to specific event type.

**Request:**
```json
{
  "data": {
    "session_id": "session_123",
    "transport_state": "rolling"
  },
  "timestamp": 1642234800.0
}
```

### WebSocket Endpoint

#### `WS /ws`
Main WebSocket endpoint for client connections.

## WebSocket Message Protocol

### Client → Gateway Messages

#### Subscribe to Events
```json
{
  "type": "subscribe",
  "event_types": ["session_transport_changed", "pedalboard_loaded"],
  "timestamp": 1642234800.0
}
```

#### Unsubscribe from Events
```json
{
  "type": "unsubscribe", 
  "event_types": ["system_stats_updated"],
  "timestamp": 1642234800.0
}
```

#### Ping
```json
{
  "type": "ping",
  "timestamp": 1642234800.0
}
```

#### Request Status
```json
{
  "type": "request_status",
  "timestamp": 1642234800.0
}
```

### Gateway → Client Messages

#### Welcome Message
```json
{
  "type": "welcome",
  "client_id": "uuid-123",
  "server_time": 1642234800.0,
  "supported_events": ["session_started", "pedalboard_loaded", "..."],
  "default_subscriptions": ["session_transport_changed", "pedalboard_loaded"],
  "heartbeat_interval": 30
}
```

#### Event Message
```json
{
  "type": "event", 
  "event_type": "session_transport_changed",
  "data": {
    "session_id": "session_123",
    "transport_state": "rolling",
    "bpm": 120.0
  },
  "timestamp": 1642234800.0
}
```

#### Subscription Confirmed
```json
{
  "type": "subscription_confirmed",
  "event_types": ["session_transport_changed", "pedalboard_loaded"],
  "timestamp": 1642234800.0
}
```

#### Error Message
```json
{
  "type": "error",
  "error": "Invalid event type: invalid_event",
  "timestamp": 1642234800.0
}
```

## Event Types

The gateway supports routing for all MOD UI event types:

### Session Events
- `session_started`, `session_stopped`, `session_reset`
- `session_transport_changed`, `session_config_changed`
- `session_stats_updated`

### Pedalboard Events  
- `pedalboard_loaded`, `pedalboard_saved`, `pedalboard_changed`
- `pedalboard_cleared`, `pedalboard_size_changed`

### Plugin Events
- `plugin_added`, `plugin_removed`, `plugin_moved` 
- `plugin_enabled`, `plugin_disabled`
- `plugin_preset_changed`, `plugin_parameter_changed`

### Hardware Events
- `hardware_connected`, `hardware_disconnected`
- `hardware_device_added`, `hardware_device_removed`
- `hardware_status_updated`

### System Events
- `system_stats_updated`, `system_cpu_load_changed`
- `system_memory_changed`, `system_temperature_changed`

### Special Events
- `*` - Subscribe to all events
- `ping` / `pong` - Connection health check

## Configuration

The service is configured via environment variables:

### Service Settings
- `WEBSOCKET_GATEWAY_HOST` (default: "0.0.0.0")
- `WEBSOCKET_GATEWAY_PORT` (default: 8081)
- `DEBUG` (default: false)

### Redis Settings
- `REDIS_HOST` (default: "localhost")
- `REDIS_PORT` (default: 6379)
- `REDIS_DB` (default: 0)
- `REDIS_PASSWORD` (optional)
- `REDIS_CHANNEL_PREFIX` (default: "mod_ui")

### WebSocket Settings
- `WEBSOCKET_HEARTBEAT_INTERVAL` (default: 30 seconds)
- `WEBSOCKET_TIMEOUT` (default: 300 seconds)
- `MAX_CONNECTIONS` (default: 100)
- `MAX_MESSAGE_SIZE` (default: 10MB)

### Performance Settings
- `EVENT_BUFFER_SIZE` (default: 1000)
- `EVENT_BATCH_SIZE` (default: 10)
- `EVENT_BATCH_TIMEOUT` (default: 0.1 seconds)
- `MESSAGE_QUEUE_SIZE` (default: 1000)

## Docker Deployment

### Build Image
```bash
docker build -f docker/websocket_gateway/Dockerfile -t mod-ui-websocket-gateway .
```

### Run with Docker Compose
```bash
docker-compose -f docker/docker-compose.dev.yml up mod-websocket-gateway
```

The service will be available at `ws://localhost:8081/ws`

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install redis websockets

# Set environment variables
export REDIS_HOST=localhost
export REDIS_PORT=6379
export DEBUG=true

# Run the service
python -m src.mod_ui.services.websocket_gateway.main
```

### Testing
```bash
# Run integration test client
python tests/websocket_gateway_test.py

# Or connect to custom gateway URL
python tests/websocket_gateway_test.py ws://localhost:8081/ws
```

### Integration with Other Services

Other MOD UI services can send events through Redis:

```python
import redis
import json

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Publish event
event_data = {
    "event_type": "session_transport_changed",
    "data": {
        "session_id": "session_123", 
        "transport_state": "rolling",
        "bpm": 120.0
    },
    "timestamp": time.time()
}

redis_client.publish("mod_ui:events", json.dumps(event_data))
```

## Monitoring and Observability

### Health Checks
- HTTP health check endpoint at `/ping`
- Docker health check configured
- Redis connection monitoring
- WebSocket connection health tracking

### Metrics
- Connection counts and statistics  
- Message throughput (sent/received per second)
- Event processing statistics
- Redis subscription status
- Error rates and connection failures

### Logging
- Structured logging with configurable levels
- Connection lifecycle events
- Event processing information
- Error tracking and debugging

## Security Considerations

### Connection Security
- CORS configuration for web browsers
- Connection rate limiting
- Message size limits
- Client timeout management

### Event Security  
- Event type validation
- Message schema validation
- Rate limiting on subscriptions
- Redis channel isolation

## Backward Compatibility

The WebSocket Gateway maintains compatibility with existing MOD UI WebSocket clients by:

- Supporting legacy message formats
- Providing default event subscriptions
- Maintaining existing WebSocket paths
- Event format translation

## Future Enhancements

- **Authentication**: JWT-based client authentication
- **Authorization**: Role-based event subscription permissions  
- **Metrics Export**: Prometheus metrics endpoint
- **Event Replay**: Ability to replay missed events
- **Client Groups**: Group-based event distribution
- **Event Filtering**: Server-side event filtering by criteria
- **WebSocket Clustering**: Multi-instance deployment support