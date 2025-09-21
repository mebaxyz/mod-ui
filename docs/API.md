# MOD UI API Documentation

## Overview

MOD UI provides a comprehensive REST API for controlling the MOD Duo effects processor. The API allows programmatic access to all functionality available through the web interface.

## Base URL
```
http://localhost:8888
```

## Authentication
Currently, no authentication is required as MOD UI runs on local networks. Future versions may include API key authentication.

## Response Format
All responses are in JSON format with consistent error handling.

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

## API Endpoints

### System Information

#### GET /system/info
Get system information and status.

**Response:**
```json
{
  "success": true,
  "data": {
    "version": "1.12.0",
    "hardware": "MOD Duo",
    "uptime": 3600,
    "cpu_usage": 15.5,
    "memory_usage": 234.5
  }
}
```

#### GET /system/status
Get current system status.

**Response:**
```json
{
  "success": true,
  "data": {
    "state": "running",
    "pedalboard_loaded": true,
    "audio_running": true,
    "hardware_connected": true
  }
}
```

### Pedalboard Management

#### GET /pedalboard/list
List all available pedalboards.

**Response:**
```json
{
  "success": true,
  "data": {
    "pedalboards": [
      {
        "id": "default",
        "title": "Default Pedalboard",
        "modified": "2023-09-21T10:00:00Z"
      }
    ]
  }
}
```

#### GET /pedalboard/current
Get information about the currently loaded pedalboard.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "default",
    "title": "Default Pedalboard",
    "plugins": [
      {
        "id": "amp",
        "uri": "http://moddevices.com/plugins/mod-devel/amp",
        "x": 100,
        "y": 200,
        "parameters": {
          "gain": 0.5,
          "volume": 0.8
        }
      }
    ],
    "connections": [
      {
        "source": "system:capture_1",
        "target": "amp:input"
      }
    ]
  }
}
```

#### POST /pedalboard/load
Load a pedalboard by ID.

**Request:**
```json
{
  "id": "my_pedalboard"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Pedalboard loaded successfully"
}
```

#### POST /pedalboard/save
Save the current pedalboard.

**Request:**
```json
{
  "title": "My Custom Pedalboard"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "my_custom_pedalboard"
  }
}
```

### Plugin Management

#### GET /plugins
List all available plugins.

**Response:**
```json
{
  "success": true,
  "data": {
    "plugins": [
      {
        "uri": "http://moddevices.com/plugins/mod-devel/amp",
        "name": "MOD Amp",
        "category": "Amplifier",
        "author": "MOD Team",
        "version": "1.0.0"
      }
    ]
  }
}
```

#### GET /plugins/{uri}
Get detailed information about a specific plugin.

**Parameters:**
- `uri`: Plugin URI

**Response:**
```json
{
  "success": true,
  "data": {
    "uri": "http://moddevices.com/plugins/mod-devel/amp",
    "name": "MOD Amp",
    "description": "Guitar amplifier simulation",
    "ports": [
      {
        "symbol": "input",
        "name": "Input",
        "type": "audio",
        "direction": "input"
      },
      {
        "symbol": "gain",
        "name": "Gain",
        "type": "control",
        "direction": "input",
        "minimum": 0.0,
        "maximum": 1.0,
        "default": 0.5
      }
    ]
  }
}
```

#### POST /pedalboard/plugin/add
Add a plugin to the current pedalboard.

**Request:**
```json
{
  "uri": "http://moddevices.com/plugins/mod-devel/amp",
  "x": 100,
  "y": 200
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "instance_id": "amp_1"
  }
}
```

#### DELETE /pedalboard/plugin/{instance_id}
Remove a plugin from the current pedalboard.

**Parameters:**
- `instance_id`: Plugin instance ID

**Response:**
```json
{
  "success": true,
  "message": "Plugin removed successfully"
}
```

### Parameter Control

#### GET /pedalboard/plugin/{instance_id}/parameters
Get all parameters for a plugin instance.

**Parameters:**
- `instance_id`: Plugin instance ID

**Response:**
```json
{
  "success": true,
  "data": {
    "parameters": {
      "gain": 0.5,
      "volume": 0.8,
      "tone": 0.6
    }
  }
}
```

#### PUT /pedalboard/plugin/{instance_id}/parameter/{symbol}
Set a parameter value.

**Parameters:**
- `instance_id`: Plugin instance ID
- `symbol`: Parameter symbol

**Request:**
```json
{
  "value": 0.7
}
```

**Response:**
```json
{
  "success": true,
  "message": "Parameter updated"
}
```

#### POST /pedalboard/connection/add
Add an audio/MIDI connection between ports.

**Request:**
```json
{
  "source": "system:capture_1",
  "target": "amp:input"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection added"
}
```

#### DELETE /pedalboard/connection/remove
Remove a connection.

**Request:**
```json
{
  "source": "system:capture_1",
  "target": "amp:input"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection removed"
}
```

### Hardware Control

#### GET /hardware/status
Get hardware status and information.

**Response:**
```json
{
  "success": true,
  "data": {
    "connected": true,
    "firmware_version": "1.12.0",
    "temperature": 45.2,
    "footswitches": [
      {
        "id": 1,
        "pressed": false
      }
    ]
  }
}
```

#### PUT /hardware/footswitch/{id}
Control a footswitch (for testing or automation).

**Parameters:**
- `id`: Footswitch ID

**Request:**
```json
{
  "action": "press"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Footswitch activated"
}
```

### Presets and Banks

#### GET /banks
List all banks.

**Response:**
```json
{
  "success": true,
  "data": {
    "banks": [
      {
        "id": "bank_1",
        "name": "Rock Tones",
        "pedalboards": ["pedalboard_1", "pedalboard_2"]
      }
    ]
  }
}
```

#### POST /bank/create
Create a new bank.

**Request:**
```json
{
  "name": "My Bank"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "bank_3"
  }
}
```

### Monitoring and Diagnostics

#### GET /monitoring/cpu
Get CPU usage information.

**Response:**
```json
{
  "success": true,
  "data": {
    "usage_percent": 15.5,
    "load_average": [1.2, 1.1, 1.0]
  }
}
```

#### GET /monitoring/memory
Get memory usage information.

**Response:**
```json
{
  "success": true,
  "data": {
    "total": 2048,
    "used": 1024,
    "free": 1024,
    "usage_percent": 50.0
  }
}
```

#### GET /monitoring/audio
Get audio system information.

**Response:**
```json
{
  "success": true,
  "data": {
    "jack_running": true,
    "sample_rate": 48000,
    "buffer_size": 128,
    "latency": 5.33
  }
}
```

## WebSocket API

MOD UI provides real-time updates via WebSocket for immediate UI synchronization.

### Connection
```
ws://localhost:8888/ws
```

### Messages

#### Parameter Changes
```json
{
  "type": "parameter_changed",
  "data": {
    "instance_id": "amp_1",
    "symbol": "gain",
    "value": 0.7
  }
}
```

#### Pedalboard Changes
```json
{
  "type": "pedalboard_changed",
  "data": {
    "action": "plugin_added",
    "plugin": {
      "instance_id": "delay_1",
      "uri": "http://moddevices.com/plugins/mod-devel/delay"
    }
  }
}
```

#### Hardware Events
```json
{
  "type": "hardware_event",
  "data": {
    "event": "footswitch_pressed",
    "footswitch_id": 1
  }
}
```

#### System Status
```json
{
  "type": "status_update",
  "data": {
    "cpu_usage": 12.3,
    "memory_usage": 45.6
  }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_REQUEST` | Malformed request data |
| `NOT_FOUND` | Resource not found |
| `HARDWARE_ERROR` | Hardware communication error |
| `AUDIO_ERROR` | Audio system error |
| `VALIDATION_ERROR` | Input validation failed |
| `INTERNAL_ERROR` | Internal server error |

## Rate Limiting

Currently, no rate limiting is implemented. Future versions may include rate limiting for API protection.

## Versioning

API endpoints include versioning in the path (`/api/v1/`). Future API versions will be added as needed while maintaining backward compatibility.

## SDKs and Libraries

### Python Client
```python
import requests

class ModUIClient:
    def __init__(self, base_url="http://localhost:8888"):
        self.base_url = base_url

    def get_system_info(self):
        response = requests.get(f"{self.base_url}/system/info")
        return response.json()

    def load_pedalboard(self, pedalboard_id):
        response = requests.post(
            f"{self.base_url}/pedalboard/load",
            json={"id": pedalboard_id}
        )
        return response.json()
```

### JavaScript Client
```javascript
class ModUIWebSocket {
    constructor(url = 'ws://localhost:8888/ws') {
        this.ws = new WebSocket(url);
        this.ws.onmessage = this.handleMessage.bind(this);
    }

    handleMessage(event) {
        const message = JSON.parse(event.data);
        switch (message.type) {
            case 'parameter_changed':
                this.onParameterChanged(message.data);
                break;
            case 'pedalboard_changed':
                this.onPedalboardChanged(message.data);
                break;
        }
    }

    onParameterChanged(data) {
        console.log('Parameter changed:', data);
    }

    onPedalboardChanged(data) {
        console.log('Pedalboard changed:', data);
    }
}
```

## Best Practices

### Error Handling
Always check the `success` field in responses and handle errors appropriately.

### Connection Management
Implement reconnection logic for WebSocket connections.

### Parameter Validation
Validate parameter values against plugin specifications before sending.

### Resource Cleanup
Properly clean up connections and resources when done.

## Future Enhancements

- OpenAPI/Swagger documentation
- API key authentication
- Rate limiting
- GraphQL API
- Webhook notifications
- Bulk operations
- Advanced filtering and pagination</content>
<parameter name="filePath">/home/nicolas/project/madeline/mod-ui/docs/API.md