# MOD UI Original Code Archive

This directory contains the **original MOD UI codebase** that has been preserved during the migration to a microservices architecture.

## 📁 Contents

### Core Files
- **`host.py`** (291KB, 7013+ lines) - The original monolithic audio engine
- **`webserver.py`** - Original web server implementation  
- **`session.py`** - Session management functionality
- **`addressings.py`** - Plugin parameter addressing system
- **`control_chain.py`** - Control Chain hardware communication
- **`hardware_*.py`** - Hardware communication modules

### Supporting Components  
- **`modtools/`** - Original MOD utilities and tools
- **`html/`** - Web UI assets and templates
- **`communication/`** - Protocol communication modules
- **`old/`** - Legacy code components

## 🔄 Migration Status

| Component | Status | New Location |
|-----------|--------|--------------|
| **Audio Engine** | ✅ **Migrated** | `src/mod_ui/services/audio_engine/` |
| **ServiceBus** | ✅ **Implemented** | `libraries/servicebus/` |
| **Web Server** | ⚠️ **In Progress** | `src/mod_ui/services/web/` |
| **Session Service** | ⚠️ **Partial** | `src/mod_ui/services/session/` |
| **Hardware Service** | 📋 **Planned** | `src/mod_ui/services/hardware/` |

## 🏗️ Microservices Architecture

The original monolithic approach has been replaced with:

```
NEW: Microservices (src/mod_ui/services/)
├── audio_engine/     # JACK + LV2 + mod-host communication
├── session/          # State management and persistence  
├── hardware/         # Hardware communication (planned)
└── web/              # Web UI and HTTP endpoints (planned)

COMMUNICATION: ServiceBus (libraries/servicebus/)
├── Redis pub/sub messaging
├── Service discovery
└── Load balancing
```

## 🎯 Key Improvements

### Original Challenges (host.py)
- **291KB single file** - Massive, hard to maintain
- **7013+ lines** - Complex interdependencies  
- **Monolithic** - All functionality tightly coupled
- **Limited scalability** - Single process bottleneck
- **Testing difficulties** - Hard to unit test components

### New Architecture Benefits
- **✅ Modular services** - Clear separation of concerns
- **✅ ServiceBus communication** - Scalable Redis pub/sub
- **✅ Docker containerization** - Production deployment
- **✅ Development friendly** - venv with fallbacks
- **✅ JACK/LV2 integration** - Enhanced audio capabilities
- **✅ Comprehensive testing** - Unit and integration tests

## 📖 Usage

### Reference Only
This code is **preserved for reference** during the migration process. 

**⚠️ Do not run this code directly** - use the new microservices instead:

```bash
# NEW: Use microservices
cd /home/nicolas/project/madeline/mod-ui
source venv/bin/activate
./run-audio-engine-venv.sh

# OR: Docker deployment  
docker compose -f docker/docker-compose.dev.yml up
```

### Code Analysis
Use this archive to:
- **Compare implementations** - Old vs new approaches
- **Reference algorithms** - Original logic for complex features  
- **Migration planning** - Identify remaining components to migrate
- **Documentation** - Understanding original design decisions

## 🔍 Key Files Analysis

### `host.py` (The Beast: 291KB)
```python
# Original monolithic structure:
class Host:
    def __init__(self):
        # Audio engine management
        # Plugin loading/management  
        # JACK connections
        # Transport control
        # Parameter handling
        # Preset management
        # Session state
        # Hardware communication
        # WebSocket events
        # ... and much more
```

**Migrated to:**
- `src/mod_ui/services/audio_engine/` - Clean, focused audio service
- **JACK integration** - Dedicated `jack_lv2_utils.py`
- **ServiceBus communication** - Pure pub/sub messaging
- **Fallback implementations** - Development-friendly

### `webserver.py`
- Original Tornado-based HTTP server
- Mixed HTML generation and API endpoints
- **Migration target:** `src/mod_ui/services/web/`

### `session.py`  
- Session state management
- Pedalboard loading/saving
- **Partial migration:** `src/mod_ui/services/session/`

## 🎓 Learning from the Original

The original MOD UI code represents **years of domain expertise** in:
- **Audio plugin management** - LV2 ecosystem integration
- **Hardware communication** - MOD device protocols
- **Real-time audio** - JACK audio system integration  
- **Web interface design** - Musical instrument UI/UX
- **Session management** - Complex state persistence

While the architecture was monolithic, the **domain knowledge is invaluable** and has been carefully preserved in the new microservices design.

## 🚀 Future

As the microservices architecture matures:
1. **Complete migration** of remaining components
2. **Remove this archive** once all functionality is migrated
3. **Performance optimization** of new architecture
4. **Feature enhancement** leveraging modular design

This archive serves as both a **historical record** and a **migration reference** for the evolution of MOD UI from monolithic to microservices architecture.

---

*Last Updated: September 28, 2025*  
*Migration Phase: Audio Engine Complete, Web Server In Progress*