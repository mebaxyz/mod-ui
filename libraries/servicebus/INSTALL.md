# ServiceBus Installation Guide

## 🚀 Automatic Dependency Installation

The `pyproject.toml` file defines all dependencies, so you can install everything automatically:

### Method 1: Install in Development Mode (Recommended)
```bash
cd libraries/servicebus
pip install -e .
```

### Method 2: Install with Existing Virtual Environment  
```bash
# Using your project's virtual environment
/path/to/your/venv/bin/pip install -e ./libraries/servicebus
```

### Method 3: Install from Project Root
```bash
# From the mod-ui project root
pip install -e ./libraries/servicebus
```

## 🔧 Dependencies Installed Automatically

- **redis[hiredis] >= 5.0.0** - Redis client with fast C parser
- **pydantic >= 2.0.0** - Data validation and settings management  
- **typing-extensions >= 4.0.0** - Type hints compatibility

## ✅ Verify Installation

```python
from servicebus import Service

# Quick test
service = Service("test-service")
print("ServiceBus installed successfully!")
```

## 📋 Usage

```python
from servicebus import Service

# Create service
service = Service("my-service")

# Register handlers
service.register_handler("ping", lambda data: {"pong": True})

# Start service
await service.start()

# Call other services
response = await service.call("other-service", "get_data")
```

## 🏗️ For Development

If you're developing the servicebus package itself:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests.py -v

# Run examples
python examples_unified.py
```