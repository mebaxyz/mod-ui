# MOD UI - Consolidated Architecture Implementation

This document describes the implementation of the consolidated MOD UI architecture, which consolidates the original 8+ microservices into 4 optimized services for embedded device deployment.

## 🏗️ Architecture Overview

The consolidated architecture consists of 4 main services:

### 1. **Client Interface Service** (Port 8080)
- **Purpose**: Web UI, API endpoints, WebSocket communication
- **Consolidates**: webui_gateway, api_service
- **Key Features**:
  - Main web interface serving
  - RESTful API endpoints
  - Real-time WebSocket communication
  - Static file serving
  - CORS handling

### 2. **System & Resource Management Service** (Port 8081)  
- **Purpose**: System control, monitoring, file management, configuration
- **Consolidates**: config_service, system_stats + new file management
- **Key Features**:
  - System monitoring (CPU, memory, disk)
  - File management (pedalboards, backups)
  - Configuration management (preferences, banks)
  - System commands execution
  - Resource monitoring and alerts

### 3. **Audio Processing Service** (Port 8082)
- **Purpose**: Audio engine, plugin management, session management
- **Consolidates**: audio_engine, plugin_manager, session_service + mod-host integration
- **Key Features**:
  - mod-host bridge integration
  - Plugin loading and management
  - Audio parameter control
  - Session state management
  - Audio routing and connections

### 4. **Hardware Interface Service** (Port 8083)
- **Purpose**: Physical controls, MIDI I/O, display management
- **Consolidates**: hardware_service + enhanced capabilities
- **Key Features**:
  - Physical control handling (encoders, buttons, footswitches)
  - MIDI input/output processing
  - Display management
  - Hardware simulation for development
  - Control assignment management

## 🚀 Quick Start

### Prerequisites

1. **Redis Server** (for inter-service communication)
```bash
# Install Redis
sudo apt-get install redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:7-alpine
```

2. **Python 3.13+** with required dependencies
```bash
# Install system dependencies
sudo apt-get install python3.13 python3-pip libjack-jackd2-dev libasound2-dev

# Install Python dependencies (done automatically by start script)
```

3. **Audio System** (for audio processing)
```bash
# Install JACK (for audio processing)
sudo apt-get install jackd2
```

### Starting the Services

#### Option 1: Automatic Startup (Recommended)
```bash
# Start all services with automatic dependency management
./start-consolidated.sh
```

This will:
- Check and start Redis if needed
- Start all 4 services in proper order
- Perform health checks
- Display service URLs and status

#### Option 2: Manual Service Startup
```bash
# Start each service individually
cd src/mod_ui/services/system_resource_management && ./start.sh &
cd src/mod_ui/services/audio_processing && ./start.sh &
cd src/mod_ui/services/hardware_interface && ./start.sh &
cd src/mod_ui/services/client_interface && ./start.sh &
```

#### Option 3: Docker Compose
```bash
# Start with Docker
docker-compose -f docker-compose.consolidated.yml up -d
```

### Accessing the Services

Once started, the services are available at:

- **🌐 Main UI**: http://localhost:8080
- **🖥️ System Management**: http://localhost:8081/health
- **🎵 Audio Processing**: http://localhost:8082/health  
- **🎛️ Hardware Interface**: http://localhost:8083/health
- **📊 Redis**: localhost:6379

### Stopping the Services

```bash
# Stop all services
./stop-consolidated.sh

# Stop services and Redis
./stop-consolidated.sh --stop-redis

# Stop services and clean logs
./stop-consolidated.sh --clean
```

## 📁 Project Structure

```
src/mod_ui/services/
├── client_interface/           # Web UI and API service
│   ├── main.py                # FastAPI application
│   ├── start.sh              # Service startup script
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile           # Container configuration
├── system_resource_management/ # System and file management
│   ├── main.py              # System monitoring and control
│   ├── start.sh            # Service startup script
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile         # Container configuration
├── audio_processing/        # Audio engine and plugins
│   ├── main.py            # Audio processing service
│   ├── start.sh          # Service startup script
│   ├── requirements.txt  # Python dependencies
│   └── Dockerfile       # Container configuration
├── hardware_interface/    # Hardware controls and MIDI
│   ├── main.py          # Hardware interface service
│   ├── start.sh        # Service startup script
│   ├── requirements.txt # Python dependencies
│   └── Dockerfile      # Container configuration
└── mod-host/           # Audio processing engine (git submodule)
    └── ...            # C/C++ mod-host implementation
```

## 🔧 Configuration

### Environment Variables

Each service can be configured via environment variables:

#### Global Configuration
- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)

#### Client Interface Service
- `CLIENT_INTERFACE_PORT`: Service port (default: `8080`)

#### System & Resource Management Service
- `SYSTEM_RESOURCE_PORT`: Service port (default: `8081`)

#### Audio Processing Service
- `AUDIO_PROCESSING_PORT`: Service port (default: `8082`)
- `JACK_SAMPLE_RATE`: Audio sample rate (default: `48000`)
- `JACK_BUFFER_SIZE`: Audio buffer size (default: `256`)

#### Hardware Interface Service
- `HARDWARE_INTERFACE_PORT`: Service port (default: `8083`)
- `SIMULATE_HARDWARE`: Enable hardware simulation (default: `true`)

### Service Configuration Files

Configuration is managed through:
- `data/prefs.json`: User preferences
- `data/banks.json`: Bank configurations
- `data/favorites.json`: Favorite plugins/settings

## 🔌 API Reference

### Client Interface Service (Port 8080)

#### Pedalboard Management
- `GET /api/pedalboards` - List all pedalboards
- `POST /api/pedalboards` - Create new pedalboard
- `GET /api/pedalboards/{id}` - Get pedalboard details
- `PUT /api/pedalboards/{id}` - Update pedalboard
- `DELETE /api/pedalboards/{id}` - Delete pedalboard

#### Plugin Management
- `GET /api/plugins` - List available plugins
- `POST /api/plugins` - Add plugin to pedalboard
- `DELETE /api/plugins/{instance_id}` - Remove plugin

#### Parameter Control
- `PUT /api/parameters` - Update plugin parameter

#### WebSocket Communication
- `WS /ws` - Real-time communication endpoint

### System & Resource Management Service (Port 8081)

#### System Monitoring
- `GET /api/system/status` - Get system status
- `GET /api/system/processes` - Get running processes
- `POST /api/system/command` - Execute system command

#### File Management
- `GET /api/files/pedalboards` - List pedalboard files
- `GET /api/files/pedalboards/{id}` - Get pedalboard file info
- `DELETE /api/files/pedalboards/{id}` - Delete pedalboard files
- `POST /api/files/operations` - File operations (copy, move, delete)

#### Configuration Management
- `GET /api/config/preferences` - Get user preferences
- `PUT /api/config/preferences` - Update preference
- `GET /api/config/banks` - Get bank configuration
- `PUT /api/config/banks` - Update bank configuration

### Audio Processing Service (Port 8082)

#### Plugin Management
- `GET /api/plugins/available` - Get available plugins
- `POST /api/plugins` - Add plugin to current pedalboard
- `DELETE /api/plugins/{instance_id}` - Remove plugin
- `GET /api/plugins/{instance_id}` - Get plugin info

#### Parameter Control
- `PUT /api/parameters` - Update plugin parameter
- `GET /api/parameters/{instance_id}/{parameter}` - Get parameter value

#### Connection Management
- `POST /api/connections` - Create audio connection
- `DELETE /api/connections/{connection_id}` - Remove connection

#### Session Management
- `GET /api/session` - Get session state
- `PUT /api/session/transport/{action}` - Transport control (play/stop/pause)

### Hardware Interface Service (Port 8083)

#### Hardware Controls
- `GET /api/hardware/controls` - Get all hardware controls
- `GET /api/hardware/controls/{control_id}` - Get control info
- `POST /api/hardware/assignments` - Assign control to parameter
- `DELETE /api/hardware/assignments/{control_id}` - Remove assignment

#### MIDI Management
- `GET /api/midi/devices` - Get MIDI devices
- `PUT /api/midi/config` - Update MIDI configuration
- `POST /api/midi/send` - Send MIDI message

#### Display Management
- `GET /api/display` - Get display content
- `PUT /api/display` - Update display content

#### Development/Simulation
- `POST /api/simulate/control` - Simulate control change (dev mode)

## 🛠️ Development

### Hardware Simulation

For development without physical hardware:

```bash
export SIMULATE_HARDWARE=true
./start-consolidated.sh
```

This enables:
- Virtual controls (encoders, buttons, footswitches)
- Simulated MIDI devices
- Mock display interface
- Control simulation endpoints

### Service Bus Communication

Services communicate via Redis pub/sub using the `ResilientServiceBus`:

```python
# Request/Response
response = await service_bus.request("audio_processing", "add_plugin", data)

# Publish/Subscribe
await service_bus.publish("parameter_changed", data)
await service_bus.subscribe("system_alerts", callback)

# Service Discovery
services = await service_bus.discover_services()
```

### Adding New Endpoints

To add new functionality:

1. **Add endpoint to appropriate service**
2. **Update service API documentation**
3. **Add inter-service communication if needed**
4. **Update WebSocket messages for real-time updates**

### Testing

```bash
# Run health checks
curl http://localhost:8080/health
curl http://localhost:8081/health
curl http://localhost:8082/health
curl http://localhost:8083/health

# Test WebSocket connection
# Use websocket_test.html or your preferred WebSocket client

# Test API endpoints
curl -X GET http://localhost:8080/api/pedalboards
curl -X GET http://localhost:8081/api/system/status
```

## 🚀 Deployment

### Development Deployment
Use the startup scripts for local development:
```bash
./start-consolidated.sh
```

### Production Deployment with Docker
```bash
docker-compose -f docker-compose.consolidated.yml up -d
```

### Raspberry Pi Deployment
1. Install dependencies:
```bash
sudo apt-get install redis-server python3.13 libjack-jackd2-dev
```

2. Configure audio system:
```bash
# Configure JACK for low-latency audio
sudo usermod -a -G audio $USER
```

3. Start services:
```bash
export SIMULATE_HARDWARE=false  # Enable real hardware
./start-consolidated.sh
```

## 📊 Monitoring and Logging

### Log Files
Service logs are stored in `logs/`:
- `logs/client_interface.log`
- `logs/system_resource_management.log`
- `logs/audio_processing.log`
- `logs/hardware_interface.log`

### Health Monitoring
Each service provides health endpoints at `/health` with:
- Service status
- Key metrics
- Dependency status
- Resource usage

### System Monitoring
The System & Resource Management service provides:
- CPU, memory, disk usage
- Process monitoring
- Service status
- System alerts

## 🔍 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Start Redis if needed
   redis-server --daemonize yes
   ```

2. **Service Won't Start**
   ```bash
   # Check port availability
   lsof -ti:8080
   
   # Check service logs
   tail -f logs/client_interface.log
   ```

3. **Audio Issues**
   ```bash
   # Check JACK status
   jack_control status
   
   # Check mod-host binary
   ls -la src/mod_ui/services/mod-host/mod-host
   ```

4. **Hardware Interface Issues**
   ```bash
   # Enable simulation mode
   export SIMULATE_HARDWARE=true
   
   # Check MIDI devices
   aconnect -l
   ```

### Service Recovery

Services include automatic recovery mechanisms:
- Health monitoring
- Automatic reconnection to Redis
- Service restart on failure
- Graceful degradation

## 📈 Performance Optimization

### Resource Usage (Typical)
- **Total RAM**: ~150-200MB (vs 400-500MB for microservices)
- **CPU**: 5-15% on Raspberry Pi 4
- **Network**: Minimal inter-service overhead
- **Startup Time**: ~10-15 seconds (vs 30-45 seconds)

### Optimization Tips
1. **Adjust buffer sizes** for your audio hardware
2. **Enable hardware acceleration** where available
3. **Use appropriate Redis persistence** settings
4. **Monitor resource usage** via system management service

## 🤝 Contributing

1. Follow the existing service patterns
2. Update API documentation
3. Add appropriate error handling
4. Include health check updates
5. Test with both simulated and real hardware

## 📄 License

This implementation follows the same license as the original MOD UI project.