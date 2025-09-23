# MOD UI Common Service Examples

This directory contains examples demonstrating how to use the MOD UI Common Service Communication Package.

## Examples Overview

### 1. **example.py** - Basic Client Usage
Demonstrates how to use `ServiceClient` to make requests to backend services.

```bash
python examples/example.py
```

### 2. **example_server.py** - Original Server Implementation
Shows the original (more verbose) way to create a service using `ServiceServer` directly.

```bash
python examples/example_server.py
```

### 3. **simple_example.py** - Simplified Server API ⭐
Demonstrates the new simplified API using `SimpleService` and decorators.

```bash
python examples/simple_example.py
```

### 4. **multi_service_example.py** - Multiple Services
Shows how to run multiple services in one application using `ServiceRegistry`.

```bash
python examples/multi_service_example.py
```

### 5. **auto_example.py** - Auto-Registration
Demonstrates auto-registration of handlers using decorators.

```bash
python examples/auto_example.py
```

## Running the Examples

### Prerequisites
- Redis server running on localhost:6379
- MOD UI environment set up

### Client-Server Testing

1. **Start a server example:**
   ```bash
   cd /path/to/mod-ui
   python -m mod_ui.common.examples.simple_example
   ```

2. **In another terminal, run the client:**
   ```bash
   python -m mod_ui.common.examples.example
   ```

### Quick Test
To quickly test without Redis, just run the syntax check:
```bash
python -m py_compile examples/*.py
```

## Progression of Complexity

1. **example.py** - Learn client basics
2. **simple_example.py** - Learn simple server creation  
3. **multi_service_example.py** - Learn multi-service patterns
4. **auto_example.py** - Learn advanced auto-registration
5. **example_server.py** - See the original verbose API (for comparison)

## Key Patterns Demonstrated

- **Request-Response Communication**: How services talk to each other
- **Decorator-Based Handlers**: Clean, Pythonic service creation
- **Error Handling**: Automatic exception handling and logging
- **Multi-Service Architecture**: Running multiple services together
- **Auto-Discovery**: Automatic handler registration
- **Type Safety**: Using enums vs strings for request types

Each example is fully documented and can be run independently!