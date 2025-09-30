# Microservice Communication Library

A flexible, high-performance microservice communication library built on Redis pub/sub with automatic service discovery, event broadcasting, and performance optimizations.

## Features

- ✅ **Dynamic Request Types** - No hardcoded enums, services define their own request types
- 🔍 **Service Discovery** - Automatic service registration and discovery
- 📡 **Event Broadcasting** - Pub/sub events without request/response overhead  
- ⚡ **High Performance** - Connection pooling, batching, caching, streaming
- 📊 **Monitoring** - Built-in metrics and health checks
- 🛠️ **Developer Friendly** - Type hints, easy testing, hot reloading

## ServiceBus

A flexible, high-performance service communication library built on Redis pub/sub with automatic service discovery, event broadcasting, and performance optimizations.

*Originally forked from MOD-UI project, enhanced and modified by Nicolas.*

## 🚀 Quick Start

```python
from servicebus import Service

# Create a service that can both handle requests and call other services
service = Service("my-service")

# Register request handlers
service.register_handler("get_data", my_handler)

# Start the service 
await service.start()

# Call other services
response = await service.call("other-service", "get_config")
```

## 📦 Installation

```bash
# Install from source
cd servicebus
pip install -e .

# Or install specific version
pip install servicebus==0.1.0
```

## Installation

```bash
pip install -e .
```

## Requirements

- Python 3.8+
- Redis 6.0+
- pydantic 2.0+
- redis-py (async)

## ZeroMQ implementation

This library ships a lightweight ZeroMQ-based implementation that can be used
instead of Redis for local or containerized deployments where a broker is not
desirable. The ZeroMQ implementation exposes the same `Service` API and supports
RPC (REQ/REP) and events (PUB/SUB).

Configuration (environment variables)
- COMM_ZEROMQ_BASE_PORT: base port used for deterministic port allocation (default 5555)
- COMM_ZEROMQ_BIND_ADDRESS: address to bind ZeroMQ sockets to (default 127.0.0.1)
- COMM_ZEROMQ_RCV_TIMEOUT_MS: socket receive timeout in milliseconds (default 5000)
- COMM_ZEROMQ_SND_TIMEOUT_MS: socket send timeout in milliseconds (default 5000)
- COMM_ZEROMQ_HASH_MODULUS: number of buckets used to map service name to ports (default 1000)

Port mapping
- RPC (REQ/REP): base_port + (crc32(service_name) % hash_modulus)
- PUB: base_port + hash_modulus + (crc32(service_name) % hash_modulus)
- SUB: base_port + 2*hash_modulus + (crc32(service_name) % hash_modulus)

Health check
- The ZeroMQ `Service` exposes a `health` RPC method by convention. Call
	`service.call("<service_name>", "health")` to get a `ServiceHealth`-like
	payload describing service status, bound ports, and registered handlers.

Notes
- PUB/SUB delivery is ephemeral. Subscribers must be connected prior to the
	publisher emitting important events if you need reliable delivery.

## 📄 Credits

**Author:** Nicolas  
**Based on:** MOD-UI project (original work by MOD team)  
**License:** MIT  

This library was developed as part of enhancements to the MOD-UI project. While the original MOD-UI was created by the MOD team, this ServiceBus library and all its features (unified Service class, performance optimizations, service discovery, event system, metrics collection) were designed and implemented by Nicolas.