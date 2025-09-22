# 🔄 Session Service Rewrite Plan

**Status**: Planning Phase  
**Priority**: High (for real-time audio features)  
**Complexity**: Major Architectural Rewrite  
**Timeline**: 2-4 weeks of focused development

## 🎯 Executive Summary

The current session service is built on legacy Tornado architecture and cannot be modernized with simple fixes. It requires a **complete rewrite** using modern FastAPI/AsyncIO patterns to support real-time audio processing, WebSocket communication, and state management in a cloud-native environment.

---

## 🚨 Why Rewrite is Necessary

### **Current Architecture Problems**

1. **🏗️ Tornado Dependency Hell**
   - Legacy `mod.session.Session` class deeply integrated with Tornado IOLoop
   - Uses deprecated `tornado.gen.Task` and old-style generators  
   - Cannot bridge cleanly with AsyncIO event loops
   - Serial library compatibility issues (`writeTimeout` parameter removed)

2. **🔄 Protocol System Conflicts**
   - `ValueError: Command b is already registered` - protocol system not designed for multiple instantiation
   - Callback-based architecture incompatible with modern async/await
   - State management scattered across multiple legacy classes

3. **🎛️ Monolithic Design**
   - Single class handles WebSockets, audio engine, HMI, pedalboards, plugins
   - Hard to test, scale, or deploy independently
   - No clear separation of concerns

### **What the Legacy Session Actually Does**

```python
# Current mod/session.py responsibilities:
class Session(object):
    # 🎵 Audio Engine Coordination
    - Manages JACK audio connections
    - Handles plugin loading/unloading
    - Coordinates pedalboard state changes
    
    # 🔌 Hardware Interface Management  
    - HMI (Human Machine Interface) communication
    - Control Chain device management
    - Hardware parameter addressing
    
    # 🌐 Real-time Communication
    - WebSocket client management
    - Real-time parameter updates
    - Live pedalboard collaboration
    
    # 💾 State Persistence
    - Pedalboard save/load operations
    - User preferences management
    - Session recording/playback
    
    # 📸 Media Generation
    - Screenshot generation
    - Audio recording coordination
    - Pedalboard thumbnails
```

---

## 🏗️ Modern Architecture Design

### **🎯 Core Principles**

1. **Microservice Architecture**: Each responsibility gets its own service
2. **Event-Driven Communication**: Services communicate via events/messages
3. **Cloud-Native**: Docker-first, horizontally scalable
4. **API-First**: REST + WebSocket APIs for all functionality
5. **Modern Async**: Pure AsyncIO, no Tornado dependencies

### **🧩 Service Breakdown**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Audio Engine  │    │  State Manager  │    │ WebSocket Hub   │
│    Service      │    │    Service      │    │    Service      │
│                 │    │                 │    │                 │
│ • JACK Control  │    │ • Pedalboards   │    │ • Real-time     │
│ • Plugin Mgmt   │    │ • User Prefs    │    │ • Broadcasting  │
│ • Connections   │    │ • Session State │    │ • Client Mgmt   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
              ┌─────────────────────────────────────┐
              │         Event Bus / Message Queue    │
              │           (Redis/RabbitMQ)          │
              └─────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Hardware Mgmt   │    │ Media Generator │    │  Session API    │
│   Service       │    │    Service      │    │   Gateway       │
│                 │    │                 │    │                 │
│ • HMI Control   │    │ • Screenshots   │    │ • HTTP Routes   │
│ • Control Chain │    │ • Recordings    │    │ • WebSocket     │
│ • Device Mgmt   │    │ • Thumbnails    │    │ • Orchestration │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🛠️ Implementation Strategy

### **Phase 1: Foundation Services**

#### **1.1 State Manager Service**
```python
# Priority: HIGH - Core state management
class StateManagerService:
    """
    Centralized state management for pedalboards, plugins, user preferences
    
    Responsibilities:
    - Pedalboard CRUD operations
    - Plugin state management  
    - User preference persistence
    - Session state coordination
    """
    
    async def save_pedalboard(self, pedalboard: PedalboardModel) -> str
    async def load_pedalboard(self, bundle_path: str) -> PedalboardModel
    async def get_current_state(self) -> SessionState
    async def broadcast_state_change(self, event: StateChangeEvent)
```

#### **1.2 WebSocket Hub Service**
```python  
# Priority: HIGH - Real-time communication
class WebSocketHubService:
    """
    Modern FastAPI WebSocket management with broadcasting
    
    Responsibilities:
    - Client connection management
    - Real-time message broadcasting
    - Event subscription/filtering
    - Connection health monitoring
    """
    
    async def broadcast_to_all(self, message: dict)
    async def broadcast_to_group(self, group: str, message: dict)  
    async def handle_client_message(self, websocket: WebSocket, message: dict)
    async def manage_subscriptions(self, client_id: str, subscriptions: List[str])
```

#### **1.3 Session API Gateway**
```python
# Priority: HIGH - Main API coordination  
class SessionAPIGateway:
    """
    FastAPI service coordinating all session operations
    
    Responsibilities:
    - HTTP REST endpoints
    - WebSocket endpoint management
    - Service orchestration  
    - Authentication/authorization
    """
    
    @app.post("/pedalboard/save")
    async def save_pedalboard(self, request: SavePedalboardRequest)
    
    @app.websocket("/session/realtime")
    async def websocket_endpoint(self, websocket: WebSocket)
    
    @app.get("/session/state")
    async def get_session_state(self) -> SessionStateResponse
```

### **Phase 2: Audio Engine Integration**

#### **2.1 Audio Engine Service**
```python
# Priority: MEDIUM - Audio processing coordination
class AudioEngineService:
    """
    Modern JACK audio engine integration
    
    Responsibilities:
    - Plugin loading/unloading
    - Audio connection management
    - Parameter value updates
    - Audio processing coordination
    """
    
    async def load_plugin(self, plugin_uri: str, instance_id: str)
    async def connect_ports(self, source: str, destination: str)
    async def set_parameter(self, instance: str, parameter: str, value: float)
    async def get_audio_stats(self) -> AudioEngineStats
```

#### **2.2 Hardware Management Service** (Already Started)
```python
# Priority: MEDIUM - Already partially implemented
class HardwareManagementService:
    """
    Hardware interface coordination (HMI, Control Chain)
    
    Current Status: Partially implemented, needs integration
    """
    
    # Expand existing hardware service to integrate with session
    async def sync_hardware_state(self, session_state: SessionState)
    async def handle_hardware_events(self, event: HardwareEvent)
```

### **Phase 3: Advanced Features**

#### **3.1 Media Generator Service**
```python
# Priority: LOW - Non-critical features
class MediaGeneratorService:
    """
    Screenshot, recording, and thumbnail generation
    
    Responsibilities:
    - Pedalboard screenshots
    - Audio recording coordination
    - Thumbnail generation
    - Media file management
    """
    
    async def generate_screenshot(self, pedalboard_id: str) -> str
    async def start_recording(self, session_id: str) -> str
    async def generate_thumbnail(self, pedalboard_id: str) -> str
```

---

## 🔧 Technical Implementation Details

### **Technology Stack**

#### **Core Framework**
- **FastAPI**: Modern async web framework
- **AsyncIO**: Native Python async/await
- **Pydantic**: Data validation and serialization
- **SQLAlchemy + Alembic**: Database ORM and migrations

#### **Real-time Communication**
- **FastAPI WebSockets**: Native WebSocket support
- **Redis**: Message queue and session storage
- **Server-Sent Events**: Alternative to WebSockets for some clients

#### **Audio Processing**
- **python-jack-client**: Modern JACK audio integration
- **pylv2**: LV2 plugin management (if available)
- **Direct C library integration**: For performance-critical operations

#### **State Management**
- **PostgreSQL/SQLite**: Persistent data storage
- **Redis**: Fast session state and caching
- **File system**: Pedalboard bundles and media files

### **Data Models**

```python
# Modern Pydantic models for type safety
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class PluginModel(BaseModel):
    instance_id: str
    plugin_uri: str
    x: float
    y: float
    parameters: Dict[str, float]
    enabled: bool = True

class ConnectionModel(BaseModel):
    source_port: str
    destination_port: str
    
class PedalboardModel(BaseModel):
    bundle_path: str
    title: str
    plugins: List[PluginModel]
    connections: List[ConnectionModel]
    screenshot_path: Optional[str] = None
    created_at: datetime
    modified_at: datetime

class SessionState(BaseModel):
    current_pedalboard: Optional[PedalboardModel]
    websocket_clients: int
    audio_engine_status: str
    hardware_connected: bool
    last_activity: datetime
```

### **Event System Design**

```python
# Event-driven architecture for loose coupling
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict

class EventType(Enum):
    PEDALBOARD_CHANGED = "pedalboard_changed"
    PLUGIN_ADDED = "plugin_added"
    PLUGIN_REMOVED = "plugin_removed"
    PARAMETER_CHANGED = "parameter_changed"
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"
    HARDWARE_EVENT = "hardware_event"

@dataclass
class SessionEvent:
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    source_service: str
    session_id: Optional[str] = None

# Event bus for service communication
class EventBus:
    async def publish(self, event: SessionEvent)
    async def subscribe(self, event_type: EventType, handler: callable)
    async def broadcast(self, event: SessionEvent)
```

---

## 📁 File Structure

```
src/mod_ui/services/session/
├── __init__.py
├── main.py                 # FastAPI application entry point
├── models/
│   ├── __init__.py
│   ├── pedalboard.py       # Pedalboard data models
│   ├── plugin.py           # Plugin data models  
│   ├── session.py          # Session state models
│   └── events.py           # Event system models
├── services/
│   ├── __init__.py
│   ├── state_manager.py    # State management service
│   ├── websocket_hub.py    # WebSocket management
│   ├── audio_engine.py     # Audio processing coordination
│   ├── hardware_sync.py    # Hardware integration
│   └── media_generator.py  # Screenshot/recording service
├── routers/
│   ├── __init__.py
│   ├── pedalboard.py       # Pedalboard CRUD endpoints
│   ├── session.py          # Session management endpoints
│   ├── realtime.py         # WebSocket endpoints
│   └── media.py            # Media generation endpoints
├── utils/
│   ├── __init__.py
│   ├── event_bus.py        # Event system implementation
│   ├── audio_utils.py      # Audio processing utilities
│   └── validation.py       # Data validation helpers
├── database/
│   ├── __init__.py
│   ├── models.py           # SQLAlchemy database models
│   ├── session.py          # Database session management
│   └── migrations/         # Alembic migration files
└── tests/
    ├── __init__.py
    ├── test_state_manager.py
    ├── test_websocket_hub.py
    ├── test_audio_engine.py
    └── test_integration.py
```

---

## 🧪 Testing Strategy

### **Unit Testing**
```python
# Test individual service components
import pytest
from fastapi.testclient import TestClient

class TestStateManagerService:
    @pytest.fixture
    def state_manager(self):
        return StateManagerService()
    
    async def test_save_pedalboard(self, state_manager):
        pedalboard = PedalboardModel(...)
        bundle_path = await state_manager.save_pedalboard(pedalboard)
        assert bundle_path.endswith('.pedalboard')
    
    async def test_load_pedalboard(self, state_manager):
        loaded = await state_manager.load_pedalboard("test.pedalboard")
        assert isinstance(loaded, PedalboardModel)
```

### **Integration Testing**
```python
# Test service interactions
class TestSessionIntegration:
    async def test_pedalboard_change_workflow(self):
        # 1. Save pedalboard via API
        # 2. Verify WebSocket clients receive update
        # 3. Verify audio engine gets updated
        # 4. Verify hardware sync occurs
        pass
    
    async def test_realtime_parameter_updates(self):
        # Test WebSocket -> Audio Engine -> Hardware pipeline
        pass
```

### **Load Testing**
```python
# Test WebSocket scalability
import asyncio
import websockets

async def test_websocket_scalability():
    """Test 100+ concurrent WebSocket connections"""
    connections = []
    for i in range(100):
        ws = await websockets.connect("ws://localhost:8888/session/realtime")
        connections.append(ws)
    
    # Test broadcasting to all connections
    # Measure latency and throughput
```

---

## 🚀 Migration Strategy

### **Step 1: Parallel Development**
- Build new session service alongside current system
- Use feature flags to gradually migrate functionality  
- Keep legacy session for critical production features

### **Step 2: API Compatibility Layer**
```python
# Provide backward compatibility during transition
class LegacyCompatibilityRouter:
    """Maintains compatibility with existing API calls"""
    
    @app.post("/legacy/web_add")
    async def web_add_plugin(self, request: LegacyAddPluginRequest):
        # Translate legacy request to modern service calls
        modern_request = self._translate_legacy_request(request)
        return await self.modern_session_service.add_plugin(modern_request)
```

### **Step 3: Gradual Feature Migration**
1. **Phase 1**: WebSocket management + State persistence
2. **Phase 2**: Audio engine coordination  
3. **Phase 3**: Hardware integration
4. **Phase 4**: Media generation features
5. **Phase 5**: Remove legacy session service

---

## 📋 Development Checklist

### **Foundation (Week 1)**
- [ ] Set up FastAPI session service project structure
- [ ] Implement basic Pydantic models
- [ ] Create StateManagerService with file-based persistence
- [ ] Implement WebSocketHubService with basic broadcasting
- [ ] Add Session API Gateway with health check endpoints

### **Core Features (Week 2)**  
- [ ] Implement pedalboard CRUD operations
- [ ] Add WebSocket real-time communication
- [ ] Create event bus system for service communication
- [ ] Add database persistence (SQLAlchemy + PostgreSQL/SQLite)
- [ ] Implement basic audio engine integration

### **Integration (Week 3)**
- [ ] Integrate with existing hardware service
- [ ] Add screenshot/media generation service
- [ ] Implement backward compatibility layer
- [ ] Add comprehensive error handling
- [ ] Create monitoring and logging

### **Production Ready (Week 4)**
- [ ] Add authentication/authorization
- [ ] Implement rate limiting and security measures
- [ ] Add comprehensive test suite
- [ ] Create deployment documentation
- [ ] Performance optimization and load testing

---

## 🔍 Success Metrics

### **Performance Targets**
- **WebSocket Latency**: < 10ms for parameter updates
- **Concurrent Connections**: Support 100+ WebSocket clients
- **Pedalboard Load Time**: < 500ms for complex pedalboards
- **API Response Time**: < 100ms for state queries

### **Reliability Targets**
- **Uptime**: 99.9% availability
- **Error Rate**: < 0.1% of requests fail
- **Recovery Time**: < 5 seconds for service restart
- **Data Integrity**: 100% session state consistency

---

## 💡 Future Enhancements

### **Advanced Features**
- **Multi-user Sessions**: Collaborative pedalboard editing
- **Cloud Sync**: Pedalboard synchronization across devices
- **Plugin Marketplace**: Direct plugin installation/management
- **AI Assistance**: Intelligent pedalboard suggestions

### **Scalability Features**
- **Horizontal Scaling**: Multiple session service instances
- **Load Balancing**: Smart WebSocket connection distribution
- **Caching**: Redis-based performance optimization
- **CDN Integration**: Fast media file delivery

---

## 📚 References

### **Technical Documentation**
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [AsyncIO Best Practices](https://docs.python.org/3/library/asyncio.html)
- [JACK Audio Connection Kit](https://jackaudio.org/)
- [LV2 Plugin Specification](https://lv2plug.in/)

### **Architecture Patterns**
- [Microservices Patterns](https://microservices.io/patterns/)
- [Event-Driven Architecture](https://microservices.io/patterns/data/event-driven-architecture.html)
- [CQRS Pattern](https://microservices.io/patterns/data/cqrs.html)

---

**Document Status**: ✅ Complete  
**Next Action**: Begin Phase 1 implementation when ready for session service modernization  
**Estimated Effort**: 2-4 weeks of focused development  
**Business Impact**: Enables real-time collaboration, cloud deployment, and advanced audio features