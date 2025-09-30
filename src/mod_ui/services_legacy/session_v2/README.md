# MOD UI Session Service v2

Modern FastAPI-based session management service for the MOD Audio Platform, replacing the legacy Tornado-based session system with a fully async, event-driven architecture.

## Architecture Overview

The Session Service v2 is built with modern Python async/await patterns and provides:

- **FastAPI REST API** with automatic OpenAPI documentation
- **WebSocket support** for real-time client communication  
- **Event-driven architecture** with pluggable event bus (in-memory or Redis)
- **Pydantic data models** for type safety and validation
- **Modular service design** with clear separation of concerns
- **Docker containerization** with health checks and proper resource management

## Key Components

### Core Services

- **StateManagerService**: Manages pedalboard state, plugin configurations, and session persistence
- **WebSocketHubService**: Handles WebSocket connections and real-time message broadcasting
- **EventBus**: Publishes and routes events between services (in-memory or Redis backends)

### Data Models

- **PedalboardModel**: Complete pedalboard representation with plugins and connections
- **PluginModel**: Individual plugin instances with parameters and positioning
- **SessionState**: Session-level configuration and transport state
- **Event**: Structured event messages for inter-service communication

### API Routers

- **Pedalboard Router** (`/api/pedalboard`): CRUD operations for pedalboards and plugins
- **Session Router** (`/api/session`): Transport controls and system configuration
- **Realtime Router** (`/api/realtime`): WebSocket management and event streaming

## API Endpoints

### Pedalboard Management

```
GET    /api/pedalboard/list              - List all pedalboards
GET    /api/pedalboard/current           - Get current pedalboard
POST   /api/pedalboard/create            - Create new pedalboard
POST   /api/pedalboard/load/{path}       - Load pedalboard from file
POST   /api/pedalboard/save              - Save current pedalboard

POST   /api/pedalboard/plugin/add        - Add plugin to pedalboard
DELETE /api/pedalboard/plugin/{id}       - Remove plugin
PATCH  /api/pedalboard/plugin/{id}/move  - Move plugin position
PATCH  /api/pedalboard/plugin/{id}/parameter/{symbol} - Set parameter

POST   /api/pedalboard/connection/add    - Add connection
DELETE /api/pedalboard/connection/remove - Remove connection
GET    /api/pedalboard/connections       - List connections
```

### Session Control

```
GET    /api/session/status               - Get session status
POST   /api/session/reset                - Reset session state

POST   /api/session/transport/play       - Start playback
POST   /api/session/transport/stop       - Stop playback  
POST   /api/session/transport/pause      - Pause playback
POST   /api/session/transport/rewind     - Rewind to start

GET    /api/session/tempo                - Get current tempo
POST   /api/session/tempo                - Set tempo (BPM)

GET    /api/session/config               - Get system configuration
POST   /api/session/config               - Update system config
GET    /api/session/stats                - Get performance stats
```

### Real-time Communication

```
WebSocket: /ws                           - WebSocket connection endpoint

GET    /api/realtime/events/types        - List event types
GET    /api/realtime/events/recent       - Get recent events
POST   /api/realtime/events/publish      - Publish event

GET    /api/realtime/clients             - List connected clients
GET    /api/realtime/clients/{id}        - Get client info
POST   /api/realtime/clients/{id}/disconnect - Disconnect client

POST   /api/realtime/broadcast           - Broadcast to all clients
POST   /api/realtime/clients/{id}/send   - Send to specific client
```

## WebSocket Protocol

WebSocket connections support bidirectional communication with structured JSON messages:

### Client → Server Messages

```json
{
  "type": "subscribe",
  "event_types": ["plugin", "transport", "pedalboard"],
  "client_id": "web-client-123"
}

{
  "type": "unsubscribe", 
  "event_types": ["plugin"],
  "client_id": "web-client-123"
}

{
  "type": "ping",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Server → Client Messages

```json
{
  "type": "event",
  "event_type": "plugin",
  "data": {
    "instance_id": "plugin_1",
    "parameter": "gain", 
    "value": 0.75
  },
  "timestamp": "2024-01-01T12:00:00Z"
}

{
  "type": "pong",
  "timestamp": "2024-01-01T12:00:00Z"
}

{
  "type": "error",
  "message": "Invalid event type",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Event System

The service uses an event-driven architecture for loose coupling between components:

### Event Types

- **PLUGIN**: Plugin parameter changes, enable/disable
- **PEDALBOARD**: Pedalboard load/save, plugin add/remove, connections
- **TRANSPORT**: Play/stop/pause state changes, tempo updates
- **SESSION**: Session reset, configuration changes
- **SYSTEM**: Service health, errors, warnings

### Event Bus Backends

**In-Memory (Default)**
- Fast, low latency
- Single process only
- Good for development and simple deployments

**Redis**
- Distributed event routing
- Persistent event history
- Supports multiple service instances
- Better for production scalability

## Configuration

Environment variables:

```bash
# Service configuration
SESSION_SERVICE_HOST=0.0.0.0
SESSION_SERVICE_PORT=8002

# Event bus configuration  
EVENT_BUS_TYPE=inmemory          # or 'redis'
REDIS_URL=redis://localhost:6379/0

# Development settings
MOD_DEV_ENVIRONMENT=1
MOD_LOG=1
PYTHONPATH=/app/src:/app
```

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- ALSA development libraries
- JACK Audio Connection Kit

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install fastapi uvicorn websockets pydantic redis aiofiles
   ```

2. **Run Service Directly**
   ```bash
   cd src/mod_ui/services/session_v2
   python -m main
   ```

3. **Access API Documentation**
   - OpenAPI docs: http://localhost:8002/docs
   - ReDoc: http://localhost:8002/redoc
   - Health check: http://localhost:8002/ping

### Docker Development

1. **Build and Run Full Stack**
   ```bash
   docker-compose -f docker-compose.session-v2.yml up --build
   ```

2. **Run with Redis Event Bus**
   ```bash
   docker-compose -f docker-compose.session-v2.yml --profile redis up
   ```

3. **Development with Live Reload**
   ```bash
   docker-compose -f docker-compose.session-v2.yml up mod-ui-session-v2
   # Volume mounts enable live code reloading
   ```

## Testing

### Manual Testing

```bash
# Health check
curl http://localhost:8002/ping

# Get session status
curl http://localhost:8002/api/session/status

# List pedalboards
curl http://localhost:8002/api/pedalboard/list

# WebSocket test (using websocat or similar)
websocat ws://localhost:8002/ws
```

### Automated Testing

```bash
# Run unit tests
python -m pytest tests/session_v2/

# Run with coverage
python -m pytest --cov=src.mod_ui.services.session_v2 tests/session_v2/
```

## Deployment

### Production Considerations

1. **Security**
   - Configure CORS origins appropriately
   - Use secure WebSocket connections (WSS)
   - Implement authentication/authorization
   - Validate and sanitize all inputs

2. **Performance**
   - Use Redis event bus for multi-instance deployments
   - Configure appropriate worker counts
   - Monitor memory usage and connection limits
   - Implement rate limiting for WebSocket connections

3. **Monitoring**
   - Health check endpoints enabled
   - Structured logging with correlation IDs
   - Metrics collection (Prometheus compatible)
   - Error tracking and alerting

### Service Discovery

The session service v2 registers itself and can be discovered by other services:

```python
# Service registration example
{
  "service_name": "mod-ui-session-v2",
  "version": "2.0.0", 
  "host": "mod-ui-session-v2",
  "port": 8002,
  "health_endpoint": "/ping",
  "api_docs": "/docs"
}
```

## Migration from Legacy Session Service

### Key Differences

| Legacy (Tornado) | Session v2 (FastAPI) |
|------------------|----------------------|
| Synchronous I/O | Async/await throughout |
| Monolithic design | Modular services |
| Custom WebSocket | Standard WebSocket |
| Manual JSON parsing | Pydantic validation |
| Callback-based events | Event bus architecture |

### Migration Steps

1. **Phase 1**: Deploy session v2 alongside legacy service
2. **Phase 2**: Migrate clients to use new API endpoints
3. **Phase 3**: Update WebSocket connections to new protocol
4. **Phase 4**: Verify functionality and performance
5. **Phase 5**: Decommission legacy session service

### Backward Compatibility

Session v2 maintains API compatibility where possible, but some endpoints have enhanced request/response formats. Clients should be updated to take advantage of new features and improved error handling.

## Troubleshooting

### Common Issues

**Service won't start**
- Check Python path and module imports
- Verify all dependencies are installed
- Ensure ports are available (8002)

**WebSocket connections fail**
- Check CORS configuration
- Verify WebSocket endpoint path
- Monitor connection limits

**Event bus issues**
- For Redis: verify Redis connectivity
- Check event bus configuration
- Monitor event queue sizes

**Performance problems**
- Monitor CPU and memory usage
- Check database connection pools
- Review WebSocket client counts

### Debug Mode

Enable debug logging:

```bash
export MOD_LOG=1
export MOD_DEV_ENVIRONMENT=1
python -m src.mod_ui.services.session_v2.main --log-level debug
```

## Contributing

### Code Structure

```
src/mod_ui/services/session_v2/
├── main.py                 # FastAPI application and startup
├── models/                 # Pydantic data models
│   ├── __init__.py
│   ├── pedalboard.py
│   ├── session.py
│   └── events.py
├── services/               # Core business logic
│   ├── __init__.py
│   ├── state_manager.py
│   └── websocket_hub.py
├── routers/                # API route handlers
│   ├── __init__.py
│   ├── pedalboard.py
│   ├── session.py
│   └── realtime.py
└── utils/                  # Shared utilities
    ├── __init__.py
    └── event_bus.py
```

### Development Guidelines

- Use type hints throughout
- Follow async/await patterns
- Write comprehensive docstrings
- Add unit tests for new features
- Use Pydantic for data validation
- Follow FastAPI best practices

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation
6. Submit pull request with clear description

## License

This project is licensed under the same terms as the main MOD UI project.

## Support

For issues and questions:
- GitHub Issues: [MOD UI Repository](https://github.com/moddevices/mod-ui)
- MOD Community Forum: [forum.mod.audio](https://forum.mod.audio)
- Documentation: [wiki.mod.audio](https://wiki.mod.audio)