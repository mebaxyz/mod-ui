# MOD Audio System - Consolidated Architecture

## Overview

This document outlines the optimized service architecture for the MOD Audio system, designed specifically for embedded devices like Raspberry Pi. The architecture balances modern microservices principles with resource efficiency.

## Consolidated Service Architecture

```
┌─────────────────────────┐      ┌─────────────────────────┐
│    Client Interface     │      │  System & Resource      │
│    Service              │      │  Management Service     │
│  - WebUI Gateway        │      │  - System Control       │
│  - Client WebSockets    │      │  - System Monitoring    │
│  - API Endpoints        │      │  - File Management      │
│                         │      │  - Resource Management  │
└───────────┬─────────────┘      └───────────┬─────────────┘
            │                                │
            └────────────┬─────────────────────┘
                         │
              ┌──────────┴───────────┐
              │  ResilientServiceBus │
              │    (Redis-based)     │
              └──────────┬───────────┘
                         │
┌─────────────────────────┐      ┌─────────────────────────┐
│  Audio Processing       │      │  Hardware Interface     │
│  Service                │      │  Service                │
│  - Audio Engine         │      │  - Physical Controls    │
│  - Plugin Management    │      │  - Display Interface    │
│  - Session Management   │      │  - MIDI/Control Surface │
│  - mod-host bridge      │      │  - Device Calibration   │
└─────────────────────────┘      └─────────────────────────┘
```

## Service Descriptions

### 1. Client Interface Service

**Components:**
- WebUI Gateway (HTTP/WebSocket server)
- Client communication (synchronization, events)
- API endpoints for client applications

**Responsibilities:**
- Serve web interface and REST API
- Handle client connections and WebSocket communications
- Format and present data for client consumption
- Handle client-side authentication and sessions

**Port:** 8081 (HTTP/WebSocket)

### 2. System & Resource Management Service

**Components:**
- System Control (power, services, configuration)
- System Monitoring (stats, health checks)
- File Management (file operations, path resolution)
- Resource Management (CPU, memory, storage)

**Responsibilities:**
- Manage system power (shutdown, reboot)
- Configure system parameters (audio settings, networking)
- Provide file operations (browse, upload, download)
- Resolve file paths for assets and resources
- Manage file metadata and information
- Monitor system health and resource usage
- Handle system updates and maintenance

**Why File Management belongs here:**
1. Files are a system resource, similar to CPU, memory, and storage
2. File operations are needed by multiple services, not just the client
3. Centralized file management provides consistent access patterns
4. Security and permission management can be handled uniformly
5. Both hardware and software clients need access to the same files

### 3. Audio Processing Service

**Components:**
- Audio Engine (JACK integration)
- Plugin Management (discovery, lifecycle)
- Session Management (pedalboards, presets)
- mod-host Bridge (C++ audio processing)

**Responsibilities:**
- Process audio in real-time
- Manage plugin loading/unloading
- Control plugin parameters
- Handle audio routing and connections
- Manage session state (pedalboards, snapshots)
- Process parameter changes from various sources

### 4. Hardware Interface Service

**Components:**
- Physical Control Interface
- Display Management
- MIDI/Control Surface Integration
- Device Calibration

**Responsibilities:**
- Interface with physical hardware (knobs, buttons)
- Handle hardware control changes
- Manage control mappings
- Provide hardware abstraction layer
- Interface with displays or indicators

## Communication Layer

The ResilientServiceBus provides communication between services with:

- **Auto-reconnection** for network resilience
- **Event publishing/subscription** for notifications
- **Method registration/calling** for service APIs
- **Health monitoring** for service status

Key event types:
- `parameter_change` - Parameter value updates
- `plugin_added`/`plugin_removed` - Plugin lifecycle events
- `pedalboard_loaded` - Session state changes
- `control_changed` - Hardware control updates
- `system_alert` - System status notifications
- `file_changed` - File system updates

## Implementation Considerations

### Resource Optimization

1. **Memory Management**
   - Service-specific memory limits (e.g., 256MB for Audio Processing)
   - Shared memory for large data when possible
   - Careful buffer management in audio paths

2. **CPU Prioritization**
   - Real-time priority for Audio Processing Service
   - Background priority for monitoring tasks
   - Dynamic CPU governor based on system load

3. **Communication Efficiency**
   - Batch updates for non-time-critical data
   - Direct paths for latency-sensitive operations
   - Specialized event formats for different data types

### Development Approach

1. **Component Structure**
   - Services contain multiple logically-grouped components
   - Internal clean interfaces between components
   - Shared data structures within a service

2. **Testing Strategy**
   - Component-level unit tests
   - Service-level integration tests
   - System-level functional tests

3. **Deployment Options**
   - Containerized development environment
   - Direct systemd services for production
   - Resource limit enforcement

## Benefits of Consolidated Architecture

1. **Resource Efficiency**
   - 4 services instead of 8+ (50% reduction in processes)
   - Less memory overhead from duplicate Python runtimes
   - Reduced IPC overhead

2. **Lower Latency**
   - Fewer service boundaries to cross
   - Direct function calls for critical paths
   - Less serialization/deserialization

3. **Simplified Deployment**
   - Fewer processes to manage
   - Clearer service dependencies
   - Easier troubleshooting

4. **Better Reliability**
   - Fewer points of failure
   - Consolidated error handling
   - Less complex state synchronization

5. **Still Maintainable**
   - Logical component separation
   - Clear service responsibilities
   - Focused testing boundaries

## Migration Path

1. **Analysis Phase**
   - Map current service functionalities
   - Identify tight coupling points
   - Define new service boundaries

2. **Consolidation Phase**
   - Merge related services gradually
   - Test thoroughly after each consolidation
   - Validate resource usage improvements

3. **Optimization Phase**
   - Fine-tune resource allocation
   - Optimize critical paths
   - Enhance resilience mechanisms

4. **Deployment Phase**
   - Create optimized container images
   - Establish systemd service files
   - Implement monitoring and alerting

## File Structure

```
src/mod_ui/services/
├── client_interface/           # WebUI Gateway + Client Communication
│   ├── main.py
│   ├── webui_gateway.py
│   ├── connection_manager.py
│   └── routers/
├── system_resource_management/ # System Control + Monitoring + File Management
│   ├── main.py
│   ├── system_control.py
│   ├── system_monitoring.py
│   ├── file_management.py
│   └── resource_management.py
├── audio_processing/          # Audio Engine + Plugins + Session Management
│   ├── main.py
│   ├── audio_engine.py
│   ├── plugin_manager.py
│   ├── session_manager.py
│   └── mod_host_bridge.py
└── hardware_interface/        # Hardware Controls + MIDI + Display
    ├── main.py
    ├── control_interface.py
    ├── midi_manager.py
    └── display_manager.py
```