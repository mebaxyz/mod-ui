"""
WebSocket Gateway Service Tests

Unit tests for the WebSocket Gateway service, organized by component:

- test_basic_functionality.py: Core functionality and integration tests
- test_websocket_gateway.py: Main FastAPI application tests
- test_effects_router.py: Effects/Plugins API router tests
- test_pedalboard_router.py: Pedalboard management API router tests
- test_other_routers.py: Tests for favorites, snapshots, banks, system, updates, utilities, LV2 routers
- test_websocket.py: WebSocket connection and messaging tests
- test_services.py: Core service layer tests (ConnectionManager, EventRouter, etc.)
- conftest.py: Shared fixtures and pytest configuration

Run tests with:
    python run_tests.py --file test_basic_functionality.py
    python run_tests.py  # Run all tests
"""
