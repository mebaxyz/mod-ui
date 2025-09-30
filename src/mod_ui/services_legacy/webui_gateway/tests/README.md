# WebSocket Gateway Service Tests

This directory contains comprehensive unit tests for the WebSocket Gateway service.

## Test Structure

### Core Tests
- **`test_basic_functionality.py`** - Integration tests verifying the service works end-to-end
- **`test_websocket_gateway.py`** - Tests for the main FastAPI application and gateway endpoints

### Router Tests
- **`test_effects_router.py`** - Tests for plugin/effects management API endpoints
- **`test_pedalboard_router.py`** - Tests for pedalboard management API endpoints
- **`test_other_routers.py`** - Tests for favorites, snapshots, banks, system, updates, utilities, and LV2 routers

### Service Layer Tests
- **`test_services.py`** - Tests for core services (ConnectionManager, EventRouter, Redis subscriber)
- **`test_websocket.py`** - Tests for WebSocket connection handling and messaging

### Configuration
- **`conftest.py`** - Shared pytest fixtures and configuration
- **`__init__.py`** - Package initialization

## Running Tests

### Run All Tests
```bash
python run_tests.py
```

### Run Specific Test File
```bash
python run_tests.py --file test_basic_functionality.py
```

### Run With Coverage
```bash
python run_tests.py --coverage
```

### Run Unit Tests Only
```bash
python run_tests.py --unit
```

## Test Coverage

The tests cover:
- ✅ FastAPI application creation and configuration
- ✅ All 9 API router integrations (86 total endpoints)
- ✅ WebSocket connection handling
- ✅ Health check and monitoring endpoints
- ✅ Error handling and validation
- ✅ Mock data responses for development testing
- ✅ Service layer functionality

## Mock vs Real Implementation

All tests currently use mock implementations that return predefined responses. This allows for:
- Fast test execution without external dependencies
- Reliable testing during development
- API contract validation

When the service is connected to real backends, the mock implementations should be replaced with actual service calls.