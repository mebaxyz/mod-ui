# Host.py Migration Strategy

## Overview
The `host.py` file (7013 lines) is the most complex component in the MOD UI system. It handles:

1. **Audio Engine Communication** - Socket-based communication with mod-host
2. **Plugin Management** - LV2 plugin lifecycle, parameters, connections
3. **Transport Control** - BPM, BPB, playback state
4. **Pedalboard Management** - Load, save, snapshots
5. **Hardware Integration** - HMI protocol, addressing system
6. **JACK Audio** - Audio routing and connection management
7. **Real-time Messaging** - WebSocket communication with browser

## Current Architecture Issues
- **Monolithic Design**: Single class handling all audio engine concerns
- **Tight Coupling**: Direct socket communication mixed with business logic
- **State Management**: Complex internal state without proper separation
- **Error Handling**: Limited recovery mechanisms for connection failures
- **Testing Difficulty**: Hard to unit test due to socket dependencies

## Proposed Microservices Architecture

### 1. Audio Engine Service (`audio-engine`)
**Purpose**: Direct communication with mod-host process
**Responsibilities**:
- Socket connection management (read/write sockets)
- Protocol translation (mod-host commands)
- Connection recovery and health monitoring
- Low-level audio engine state

**Key Components**:
```python
# Models
class AudioEngineCommand(BaseModel):
    command: str
    parameters: Dict[str, Any]
    callback_id: Optional[str] = None

class AudioEngineResponse(BaseModel):
    status: str
    data: Optional[str] = None
    error: Optional[str] = None

# Service
class AudioEngineService:
    def __init__(self):
        self.connection_manager = ModHostConnectionManager()
        self.command_queue = asyncio.Queue()
    
    async def send_command(self, command: AudioEngineCommand) -> AudioEngineResponse
    async def start_connection(self)
    async def close_connection(self)
```

### 2. Plugin Management Service (`plugin-manager`)
**Purpose**: High-level plugin lifecycle and state management
**Responsibilities**:
- Plugin instance management
- Parameter control and monitoring
- Plugin metadata and capabilities
- Audio routing between plugins

**Key Components**:
```python
# Models
class PluginInstance(BaseModel):
    instance_id: str
    plugin_uri: str
    x: float
    y: float
    ports: Dict[str, float]
    designations: Dict[str, Optional[str]]
    preset_uri: Optional[str] = None

class PluginConnection(BaseModel):
    from_port: str
    to_port: str
    connection_id: Optional[str] = None

# Service
class PluginService:
    async def add_plugin(self, uri: str, x: float, y: float) -> PluginInstance
    async def remove_plugin(self, instance_id: str)
    async def set_parameter(self, instance_id: str, symbol: str, value: float)
    async def connect_ports(self, from_port: str, to_port: str)
    async def disconnect_ports(self, from_port: str, to_port: str)
```

### 3. Transport Service (`transport`)
**Purpose**: Playback control and timing synchronization
**Responsibilities**:
- BPM/BPB management
- Transport state (play/stop/pause)
- Tempo synchronization
- MIDI clock generation

**Key Components**:
```python
# Models
class TransportState(BaseModel):
    rolling: bool = False
    bpm: float = 120.0
    bpb: float = 4.0
    sync_mode: str = "none"
    speed: float = 1.0

# Service
class TransportService:
    async def set_bpm(self, bpm: float)
    async def set_bpb(self, bpb: float)
    async def set_rolling(self, rolling: bool)
    async def get_state(self) -> TransportState
```

### 4. Pedalboard Service (`pedalboard-manager`)
**Purpose**: Pedalboard lifecycle and persistence
**Responsibilities**:
- Pedalboard loading and saving
- Snapshot management
- Preset handling
- Bank organization

**Integration**: This would extend your existing session_v2 service with pedalboard-specific functionality.

### 5. Hardware Interface Service (`hardware-interface`)
**Purpose**: Hardware abstraction and addressing
**Responsibilities**:
- HMI protocol communication
- Addressing system management
- Hardware capability detection
- Control surface mapping

### 6. Audio Routing Service (`audio-routing`)
**Purpose**: JACK audio connection management
**Responsibilities**:
- System audio port management
- External connection handling
- Monitoring and metering
- Audio device configuration

## Migration Steps

### Phase 1: Extract Audio Engine Communication
1. **Create Audio Engine Service** with basic mod-host socket communication
2. **Implement Command/Response Protocol** for async communication
3. **Add Connection Management** with reconnection logic
4. **Test Basic Commands** (add_plugin, remove_plugin, set_param)

### Phase 2: Plugin Management Abstraction
1. **Create Plugin Service** with high-level plugin operations
2. **Migrate Plugin State Management** from Host class
3. **Implement Plugin Discovery** and metadata handling
4. **Add Parameter Monitoring** and change notifications

### Phase 3: Transport and Timing
1. **Extract Transport Logic** into dedicated service
2. **Implement BPM/BPB Synchronization** across services
3. **Add MIDI Clock Generation** if needed
4. **Test Tempo Changes** and transport control

### Phase 4: Integration and Testing
1. **Update Session Service** to orchestrate other services
2. **Implement Service Discovery** and health checks
3. **Add Comprehensive Testing** for each service
4. **Performance Testing** to ensure real-time requirements

## Communication Patterns

### Service-to-Service Communication
- **ServiceBus**: Use existing Redis pub/sub for service coordination
- **Direct HTTP**: For synchronous operations needing immediate response
- **WebSocket Broadcast**: For real-time state updates to UI

### Audio Engine Communication
```python
# Via ServiceBus
await servicebus_client.call(
    "audio-engine",
    "send_command",
    {"command": "add_plugin", "uri": plugin_uri, "instance": instance_id}
)

# Direct async communication
audio_service = AudioEngineService()
response = await audio_service.send_command(
    AudioEngineCommand(command="add_plugin", parameters={...})
)
```

## Backwards Compatibility

### Gradual Migration
1. **Keep Original Host Class** as a facade during transition
2. **Delegate Operations** to new services incrementally
3. **Maintain WebSocket API** for frontend compatibility
4. **Test Extensively** at each migration step

### Integration Points
- **Session Service**: Main orchestrator for pedalboard operations
- **WebSocket Gateway**: Maintains existing browser API
- **Hardware Service**: Continues HMI protocol handling

## Benefits of This Architecture

1. **Separation of Concerns**: Each service has a clear, focused responsibility
2. **Testability**: Services can be unit tested independently
3. **Scalability**: Services can be scaled independently based on load
4. **Reliability**: Failure in one service doesn't crash the entire system
5. **Maintainability**: Smaller, focused codebases are easier to maintain
6. **Real-time Performance**: Dedicated audio engine service for low-latency operations

## Risk Mitigation

1. **Performance**: Audio operations must maintain real-time performance
2. **Complexity**: Service coordination adds architectural complexity
3. **State Consistency**: Distributed state requires careful synchronization
4. **Migration Risk**: Large refactoring could introduce bugs

## Next Steps

Would you like me to:
1. **Start with Audio Engine Service** - Create the foundational mod-host communication layer
2. **Begin Plugin Service** - Extract plugin management logic
3. **Create Transport Service** - Handle BPM/transport control
4. **Design Service Integration** - Plan how services will communicate

The audio engine service would be the logical starting point since it's the foundation for all other audio operations.