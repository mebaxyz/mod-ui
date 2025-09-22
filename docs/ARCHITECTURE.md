# MOD UI Architecture

## Overview

MOD UI is a complex system that bridges web-based user interfaces with professional audio processing hardware. The architecture is designed to provide real-time control of audio effects while maintaining stability and performance.

## Core Components

### 1. Web Server (`webserver.py`)

**Purpose**: HTTP server handling web interface and API requests

**Responsibilities**:
- Serve static web files (HTML, CSS, JS)
- Handle REST API endpoints
- Manage WebSocket connections for real-time updates
- Template rendering with Jinja2

**Technology**: Currently Tornado, planned migration to FastAPI

### 2. Session Manager (`session.py`)

**Purpose**: Central coordinator managing the application lifecycle

**Responsibilities**:
- Initialize and coordinate HMI, Host, and Web components
- Manage application state and configuration
- Handle WebSocket communication
- Coordinate parameter addressing between components

**Key Classes**:
- `Session`: Main session management
- `WebSocketHandler`: WebSocket connection management

### 3. HMI (Human-Machine Interface) (`hmi.py`)

**Purpose**: Hardware abstraction layer for MOD Duo communication

**Responsibilities**:
- Serial communication with MOD Duo hardware
- Hardware state management
- Footswitch and control input handling
- Parameter value synchronization

**Communication Protocol**:
- Custom binary protocol over serial
- Real-time parameter updates
- Hardware status monitoring

### 4. Host (`host.py`)

**Purpose**: Audio processing host managing LV2 plugins and JACK connections

**Responsibilities**:
- JACK audio system integration
- LV2 plugin lifecycle management
- Audio routing and connections
- Plugin parameter control
- MIDI processing

**Integration**:
- Direct JACK client
- LV2 plugin hosting
- Real-time audio processing

## Data Flow

```
Web Browser ←→ Web Server ←→ Session Manager ←→ HMI ←→ Hardware
                    ↓
              WebSocket Server
                    ↓
              Real-time Updates
                    ↓
              Parameter Changes
                    ↓
         Host ←→ JACK ←→ LV2 Plugins ←→ Audio Processing
```

## Communication Patterns

### Synchronous Communication
- HTTP REST API calls
- Direct method calls between components

### Asynchronous Communication
- WebSocket messages for real-time UI updates
- Hardware event callbacks
- JACK audio processing callbacks

### State Management
- Centralized state in Session Manager
- Distributed state synchronization
- Parameter addressing system

## Key Design Patterns

### Observer Pattern
Components register callbacks for state changes and hardware events.

### Factory Pattern
Plugin and hardware interface creation based on configuration.

### State Machine
Application lifecycle managed through defined states (init, running, shutdown).

### Bridge Pattern
Abstraction layers between web interface and hardware/audio systems.

## Performance Considerations

### Real-time Requirements
- Audio processing: <10ms latency
- UI updates: <100ms response time
- Hardware communication: <50ms round-trip

### Memory Management
- Efficient plugin loading/unloading
- Minimal memory footprint for embedded deployment
- Resource cleanup on shutdown

### Threading Model
- Main thread: Web server and coordination
- Audio thread: JACK processing (real-time)
- Hardware thread: Serial communication
- Worker threads: Background tasks

## Security Considerations

### Network Security
- Local network deployment (no internet exposure)
- Basic authentication for administrative access
- Input validation on all API endpoints

### Hardware Security
- Direct hardware access through serial interface
- Firmware update mechanisms
- Safe parameter ranges enforcement

## Extensibility

### Plugin System
- LV2 plugin support
- Custom MOD plugin format
- Runtime plugin discovery

### Hardware Abstraction
- Generic HMI interface
- Hardware-specific implementations
- Future hardware support

### API Extensions
- RESTful API design
- Versioned endpoints
- Backward compatibility

## Deployment Architecture

### Single Binary Deployment
- All components in single Python package
- C++ utilities compiled into shared libraries
- Self-contained installation

### Microservices Migration (In Progress)
- ✅ Separate Hardware service (FastAPI)
- 🔄 Separate API service (FastAPI) 
- 📋 Separate Web service (static file server)
- ✅ Containerized deployment with Docker

#### Hardware Service Architecture

**Overview**: The hardware service has been extracted into a standalone FastAPI microservice that handles all physical device interactions, providing isolation and fault tolerance.

**Components**:
- **Hardware Service** (`src/mod_ui/services/hardware/main.py`): Standalone FastAPI service
- **Hardware Client** (`mod/hardware_client.py`): HTTP client for service communication
- **Hardware Adapter** (`mod/hardware_adapter.py`): Backward compatibility layer
- **Redis Event Bus**: Pub/sub system for cross-service communication

**Service Endpoints**:
```http
GET  /health                          # Service health check
GET  /hardware/status                 # Current hardware status
POST /hardware/scan                   # Scan for devices
POST /hardware/hmi/ping              # Ping HMI device
POST /hardware/hmi/reset_eeprom      # Reset HMI EEPROM
POST /hardware/control_chain/scan    # Scan Control Chain devices
```

**Event Architecture**:
- Hardware events published to Redis with UUID keys
- Event types: `hardware_status_updated`, `control_chain_device_added`, `hmi_connected`
- Structured event data with timestamps and source service identification
- Cross-service event consumption via Redis pub/sub patterns

**Deployment**:
```yaml
# docker/docker-compose.dev.yml
services:
  mod-hardware:
    build:
      context: .
      dockerfile: docker/hardware/Dockerfile
    ports:
      - "8003:8003"
    privileged: true  # Required for hardware access
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Integration Patterns**:
- **Backward Compatibility**: Existing `get_hardware_descriptor()` functions seamlessly use service when `MOD_USE_HARDWARE_SERVICE=1`
- **Graceful Degradation**: Falls back to file-based descriptors when service unavailable
- **Error Isolation**: Hardware service failures don't crash main application
- **Service Discovery**: Automatic health checking and service recovery

**Migration Benefits**:
- **Fault Isolation**: Hardware issues don't affect main UI
- **Independent Scaling**: Hardware service can be scaled separately
- **Development**: Hardware service can be developed/tested independently
- **Maintenance**: Hardware updates don't require full system restart

## Monitoring and Debugging

### Logging
- Structured logging with levels
- Component-specific loggers
- Debug information for troubleshooting

### Profiling
- Performance monitoring hooks
- Audio latency measurements
- Memory usage tracking

### Testing
- Unit tests for individual components
- Integration tests for component interaction
- Hardware simulation for testing

## Future Evolution

### FastAPI Migration
- Replace Tornado with FastAPI for better async support
- Improved API documentation with OpenAPI
- Better type safety with Pydantic

### Microservices Architecture
- Independent service deployment
- Better scalability and maintainability
- Container orchestration with Docker Compose

### Modern Frontend
- React/Vue.js replacement for jQuery
- Progressive Web App features
- Mobile-responsive design</content>
<parameter name="filePath">/home/nicolas/project/madeline/mod-ui/docs/ARCHITECTURE.md