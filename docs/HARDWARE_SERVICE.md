# Hardware Service Documentation

## Overview

The MOD UI Hardware Service is a standalone FastAPI microservice that manages all interactions with physical MOD devices, including HMI (Human Machine Interface) controls, Control Chain devices, and hardware descriptors.

## Architecture

### Service Design

The hardware service follows a microservices architecture pattern with the following key characteristics:

- **Standalone Process**: Runs independently from the main MOD UI application
- **REST API**: Provides HTTP endpoints for hardware operations
- **Event-Driven**: Publishes hardware events to Redis for real-time notifications
- **Fault Tolerant**: Service failures don't crash the main application
- **Docker Ready**: Containerized with privileged access for hardware communication

### Components

```
src/mod_ui/services/hardware/
├── main.py                    # FastAPI application and hardware service
├── models/
│   └── hardware_events.py     # Pydantic models for events
└── utils/
    └── device_scanner.py      # Hardware device detection utilities
```

## API Endpoints

### Health Check
```http
GET /health
```
Returns service health status and basic hardware connectivity information.

**Response:**
```json
{
  "status": "healthy",
  "device_connected": false,
  "timestamp": "2025-09-22T14:42:35.589187"
}
```

### Hardware Status
```http
GET /hardware/status
```
Returns detailed hardware status including connected devices and system state.

**Response:**
```json
{
  "device_connected": false,
  "device_type": "",
  "serial_port": null,
  "hmi_version": null,
  "control_chain_devices": [],
  "last_heartbeat": "2025-09-22T14:26:17.687543"
}
```

### Device Scanning
```http
POST /hardware/scan
```
Triggers a scan for connected MOD devices and returns discovered hardware.

**Response:**
```json
[
  {
    "device_type": "mod-duo",
    "serial_port": "/dev/ttyUSB0",
    "version": "1.2.3"
  }
]
```

### HMI Operations

#### Ping HMI
```http
POST /hardware/hmi/ping
```
Sends a ping to the HMI device to test connectivity.

**Response:**
```json
{
  "success": true,
  "response_time_ms": 45
}
```

#### Reset HMI EEPROM
```http
POST /hardware/hmi/reset_eeprom
```
Resets the HMI EEPROM to factory defaults.

**Response:**
```json
{
  "success": true,
  "message": "EEPROM reset completed"
}
```

### Control Chain Operations

#### Scan Control Chain Devices
```http
POST /hardware/control_chain/scan
```
Scans for Control Chain devices and returns discovered hardware.

**Response:**
```json
[
  {
    "device_id": 1,
    "label": "MOD Footswitch",
    "actuators": [...]
  }
]
```

## Event System

### Event Types

The hardware service publishes the following event types to Redis:

- `hardware_status_updated`: Device connection status changes
- `hardware_device_added`: New device detected
- `hardware_device_removed`: Device disconnected
- `control_chain_device_added`: Control Chain device connected
- `control_chain_device_removed`: Control Chain device disconnected
- `hmi_connected`: HMI device connected
- `hmi_disconnected`: HMI device disconnected

### Event Structure

All events follow a consistent structure:

```json
{
  "event_id": "uuid-string",
  "event_type": "hardware_status_updated",
  "source_service": "hardware_standalone",
  "session_id": null,
  "timestamp": "2025-09-22T14:42:35.589187",
  "priority": "normal",
  "data": {
    "device_connected": false,
    "device_type": "mod-duo",
    "previous_status": "connected"
  },
  "target_clients": null
}
```

### Redis Integration

Events are published to Redis with the following patterns:

- **Event Storage**: `event:{uuid}` - Individual event data
- **Pub/Sub**: `mod_ui:event:{session_id}:{event_type}` - Event notifications

## Client Integration

### Hardware Client

The `mod/hardware_client.py` module provides a Python client for communicating with the hardware service:

```python
from mod.hardware_client import get_hardware_client

client = get_hardware_client()

# Check service health
health = client.health_check()
print(health['status'])  # 'healthy'

# Get hardware status
status = client.get_hardware_status()
print(status['device_connected'])  # False

# Scan for devices
devices = client.scan_devices()
```

### Hardware Adapter

The `mod/hardware_adapter.py` module provides backward compatibility with existing MOD UI code:

```python
from mod.hardware_adapter import get_hardware_adapter

adapter = get_hardware_adapter()

# Get hardware descriptor (with service fallback)
descriptor = adapter.get_hardware_descriptor()

# Check service health
healthy = adapter.is_service_healthy()
```

### Integration Modes

The system supports multiple integration modes:

#### Legacy Mode (Default)
```bash
# Uses file-based hardware descriptors
python mod_ui_app.py
```

#### Service Mode
```bash
# Uses hardware service for all hardware operations
MOD_USE_HARDWARE_SERVICE=1 python mod_ui_app.py
```

## Configuration

### Environment Variables

- `MOD_HARDWARE_SERVICE_URL`: Service URL (default: `http://localhost:8003`)
- `MOD_REDIS_HOST`: Redis hostname (default: `localhost`)
- `MOD_REDIS_PORT`: Redis port (default: `6379`)
- `MOD_USE_HARDWARE_SERVICE`: Enable service mode (`1` or `true`)

### Docker Configuration

```yaml
services:
  mod-hardware:
    build:
      context: .
      dockerfile: docker/hardware/Dockerfile
    ports:
      - "8003:8003"
    privileged: true  # Required for /dev access
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379
      - MOD_LOG=1  # Enable debug logging
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - /dev:/dev  # Device access
```

## Deployment

### Development Environment

```bash
# Start services
docker compose -f docker/docker-compose.dev.yml up -d

# Check service status
curl http://localhost:8003/health

# View logs
docker logs mod-ui-hardware
```

### Production Deployment

For production deployment, ensure:

1. **Privileged Access**: Container needs privileged mode for hardware access
2. **Device Mounting**: Mount `/dev` directory for serial port access
3. **Network Access**: Ensure Redis connectivity
4. **Health Checks**: Configure proper health check intervals
5. **Logging**: Set appropriate log levels

## Error Handling

### Service Failures

The system is designed to handle service failures gracefully:

1. **Connection Failures**: Timeout after 5-10 seconds and return error
2. **Service Down**: Fall back to file-based hardware descriptors
3. **Partial Failures**: Individual endpoint failures don't affect others
4. **Recovery**: Automatic reconnection when service comes back online

### Error Responses

All API endpoints return consistent error structures:

```json
{
  "error": "Connection timeout",
  "details": "Hardware service unreachable",
  "timestamp": "2025-09-22T14:42:35.589187"
}
```

## Monitoring

### Health Checks

- **Docker Health Check**: Automated container health monitoring
- **API Health Endpoint**: `/health` endpoint for service status
- **Redis Event Health**: Monitor event publishing frequency

### Logging

The service provides structured logging:

```
2025-09-22 14:29:48,080 - __main__.HardwareService - INFO - Scanning for MOD devices...
2025-09-22 14:29:48,089 - __main__.HardwareService - WARNING - No MOD devices detected
INFO:     172.22.0.1:34870 - "GET /health HTTP/1.1" 200 OK
```

### Metrics

Key metrics to monitor:

- Service uptime and response times
- Hardware device connection status
- Event publishing rate
- Error rates and types

## Testing

### Unit Tests

```bash
# Run hardware service tests
python -m pytest src/mod_ui/services/hardware/tests/
```

### Integration Tests

```bash
# Test with running service
MOD_USE_HARDWARE_SERVICE=1 python -c "
from mod.hardware_adapter import get_hardware_adapter
adapter = get_hardware_adapter()
assert adapter.is_service_healthy()
print('Hardware service integration test passed')
"
```

### Development Testing

```bash
# Test service isolation
docker stop mod-ui-hardware
# Main application should continue working

# Test service recovery
docker start mod-ui-hardware
# Service should reconnect automatically
```

## Troubleshooting

### Common Issues

1. **Service Won't Start**
   - Check Docker privileged mode
   - Verify Redis connectivity
   - Check port availability (8003)

2. **Hardware Not Detected**
   - Verify device connections
   - Check `/dev` directory mounting
   - Review hardware permissions

3. **Events Not Publishing**
   - Verify Redis connection
   - Check Redis event keys: `docker exec redis redis-cli keys "event:*"`
   - Monitor service logs

### Debug Commands

```bash
# Check service health
curl http://localhost:8003/health

# View service logs
docker logs mod-ui-hardware --tail 50

# Check Redis events
docker exec mod-ui-redis redis-cli keys "event:*"

# Test hardware client
python3 -c "
from mod.hardware_client import get_hardware_client
client = get_hardware_client()
print(client.health_check())
"
```