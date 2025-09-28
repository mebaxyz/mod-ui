# MOD UI - Virtual Environment Setup

## Overview
The MOD UI project now supports both **venv (local development)** and **Docker (deployment)** environments. The venv setup provides a development-friendly environment with fallback implementations for MOD-specific hardware utilities.

## Quick Start with venv

### 1. Activate Virtual Environment
```bash
cd /home/nicolas/project/madeline/mod-ui
source venv/bin/activate
```

### 2. Install Dependencies
```bash
# Install ServiceBus library
pip install -e libraries/servicebus/

# Verify installation
pip list | grep -E "(redis|pydantic|servicebus)"
```

### 3. Run Audio Engine Service
```bash
# Easy way (using runner script)
./run-audio-engine-venv.sh

# Manual way
export PYTHONPATH="$PWD/src:$PYTHONPATH"
python src/mod_ui/services/audio_engine/main.py
```

## Environment Comparison

| Feature | venv (Development) | Docker (Deployment) |
|---------|-------------------|---------------------|
| **JACK Audio** | ✅ Fallback mode | ✅ Full system |
| **LV2 Plugins** | ✅ Fallback mode | ✅ Full discovery |
| **MOD Utilities** | ⚠️ Graceful fallback | ✅ Native support |
| **ServiceBus** | ✅ Full support | ✅ Full support |
| **Development** | 🎯 **Ideal** | ⚙️ Production-ready |
| **Hardware Deps** | ❌ None required | ✅ MOD hardware |

## Fallback Behavior in venv

### JACK Integration
- **Sample Rate**: Returns 48000.0Hz (typical)
- **Buffer Size**: Returns 512 (common default)
- **CPU Load**: Returns 0.0% (simulation)
- **Hardware Ports**: Returns empty list (no hardware)
- **Connections**: Simulates success for testing

### LV2 Plugin System
- **Plugin Discovery**: Scans system LV2 paths
- **Plugin Count**: Returns actual installed plugins
- **Bundle Operations**: Graceful no-op for development
- **Plugin Info**: Uses lilv library if available

## Testing in venv

### Run Test Suite
```bash
source venv/bin/activate
python test_audio_engine_extended.py --venv
```

### Test ServiceBus Communication
```bash
# Requires Redis running
source venv/bin/activate

# Test direct service
python -c "
import asyncio
import sys, os
sys.path.insert(0, 'src')

async def test():
    from mod_ui.services.audio_engine.service import AudioEngineService
    service = AudioEngineService()
    jack_data = await service.get_jack_data()
    print(f'JACK: {jack_data.sample_rate}Hz, {jack_data.buffer_size} buffer')

asyncio.run(test())
"
```

## Development Workflow

### 1. Code Changes
- Edit files in `src/mod_ui/services/audio_engine/`
- All changes immediately available (no rebuild needed)

### 2. Test Changes
```bash
source venv/bin/activate
python test_audio_engine_extended.py --venv
```

### 3. Verify ServiceBus Integration
```bash
# Start Redis (if not running)
redis-server &

# Run audio engine service
./run-audio-engine-venv.sh

# In another terminal, test ServiceBus calls
source venv/bin/activate
python -c "
import asyncio
from servicebus.client import ServiceClient

async def test():
    client = ServiceClient('dev-test')
    response = await client.call('audio-engine', 'health_check', {})
    print('Health:', response)
    await client.close()

asyncio.run(test())
"
```

## File Structure for venv

```
mod-ui/
├── venv/                              # Virtual environment
├── src/mod_ui/services/audio_engine/  # Audio engine service
│   ├── main.py                        # ServiceBus server
│   ├── service.py                     # Core service logic
│   ├── jack_lv2_utils.py             # JACK/LV2 with fallbacks
│   └── models.py                      # Data models
├── libraries/servicebus/              # ServiceBus library
├── test_audio_engine_extended.py      # Test suite
└── run-audio-engine-venv.sh          # Easy runner
```

## Advantages of venv Setup

### ✅ **Development Speed**
- No Docker build times
- Instant code changes
- Direct debugging
- Native Python tools

### ✅ **Hardware Independence** 
- No MOD device required
- Works on any Linux system
- Fallback implementations
- Safe for development

### ✅ **Full Feature Support**
- Complete ServiceBus integration
- All JACK functionality (simulated)
- LV2 plugin system (real or fallback)
- Same API as production

### ✅ **Easy Testing**
- Comprehensive test suite
- Fallback validation
- ServiceBus communication tests
- Integration testing ready

## Production Deployment

When ready for production:

```bash
# Switch to Docker deployment
docker compose -f docker/docker-compose.dev.yml up mod-audio-engine
```

The same code runs in both environments with automatic detection of available utilities and graceful fallback behavior.

## Troubleshooting

### Python Path Issues
```bash
export PYTHONPATH="$PWD/src:$PYTHONPATH"
```

### Missing Dependencies
```bash
source venv/bin/activate
pip install -e libraries/servicebus/
pip install -r requirements.txt
```

### JACK/ALSA Warnings
These are expected in development environment - the service gracefully falls back to simulation mode.

### ServiceBus Connection
Ensure Redis is running:
```bash
# Check if Redis is running
redis-cli ping

# Start Redis if needed
redis-server &
```