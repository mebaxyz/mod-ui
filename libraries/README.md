# Libraries

This folder contains reusable libraries and packages developed by Nicolas for the MOD-UI project.

*Originally forked from MOD-UI by the MOD team, all modifications and enhancements by Nicolas.*

## 📦 Available Libraries

### **ServiceBus** (`servicebus/`)
A flexible, high-performance service communication library built on Redis pub/sub with automatic service discovery, event broadcasting, and performance optimizations.

**Quick Install:**
```bash
cd libraries/servicebus
pip install -e .
```

**Quick Usage:**
```python
from servicebus import Service

service = Service("my-service")
service.register_handler("ping", lambda data: {"pong": True})
await service.start()
```

**Features:**
- 🚀 Unified Service class (client + server in one)
- ⚡ High-performance Redis pub/sub (CPU optimized)
- 🔍 Automatic service discovery
- 📡 Event-driven architecture
- 📊 Built-in metrics collection
- 🔧 Connection pooling & caching
- 🎯 Type-safe models with Pydantic

## 🏗️ Development

Each library is self-contained with its own:
- `pyproject.toml` - Package configuration and dependencies
- `README.md` - Library-specific documentation
- `tests.py` - Test suite
- `examples.py` - Usage examples

## 📋 Installation Patterns

### Install a specific library:
```bash
# Install in development mode
cd libraries/[library-name]
pip install -e .

# Or install from anywhere
pip install -e ./libraries/[library-name]
```

### Install with project virtual environment:
```bash
# Using project's venv
/path/to/project/venv/bin/pip install -e ./libraries/[library-name]
```

## 🔄 Adding New Libraries

When adding new libraries:

1. Create a new folder: `libraries/mylibrary/`
2. Add `pyproject.toml` with package configuration
3. Create the library code structure
4. Add tests and examples
5. Update this README

## 📁 Recommended Structure

```
libraries/
├── README.md                    # This file
├── servicebus/                  # Service communication library
│   ├── pyproject.toml
│   ├── README.md
│   ├── servicebus/              # Main package code
│   ├── examples.py
│   ├── tests.py
│   └── ...
└── [future-library]/            # Future libraries go here
    ├── pyproject.toml
    ├── README.md
    └── ...
```